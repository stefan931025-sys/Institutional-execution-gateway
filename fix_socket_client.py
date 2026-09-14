import asyncio
import logging
logger = logging.getLogger(__name__)

class FixSocketClient:
    def __init__(self, host: str, port: int, sender_comp_id: str, target_comp_id: str):
        self.host = host
        self.port = port
        self.sender_comp_id = sender_comp_id
        self.target_comp_id = target_comp_id
        self.in_seq_num = 1
        self.out_seq_num = 1
        self.reader = None
        self.writer = None
        self.is_connected = False

    async def connect(self):
        """Establish a real TCP connection to the FIX server/sandbox endpoint."""
        try:
            self.reader, self.writer = await asyncio.open_connection(self.host, self.port)
            self.is_connected = True
            logger.info(f"Connected to FIX endpoint at {self.host}:{self.port}")
            await self.send_logon()
        except Exception as e:
            logger.error(f"Failed to connect to FIX server: {e}")
            self.is_connected = False

    def _format_fix_message(self, msg_type: str, body_fields: dict) -> bytes:
        """Construct a raw FIX message string with proper header, body, and checksum (Tag 10)."""
        # Standard FIX header construction
        body = f"35={msg_type}|49={self.sender_comp_id}|56={self.target_comp_id}|34={self.out_seq_num}|"
        for tag, val in body_fields.items():
            body += f"{tag}={val}|"
            
        # Add body length (Tag 9)
        header = f"8=FIX.4.2|9={len(body)}|"
        raw_message = header + body
        
        # Calculate checksum (Tag 10) - sum of bytes modulo 256
        checksum = sum(bytes(raw_message.replace('|', '\x01'), 'ascii')) % 256
        complete_message = raw_message.replace('|', '\x01') + f"10={checksum:03d}\x01"
        
        self.out_seq_num += 1
        return complete_message.encode('ascii')

    async def send_logon(self):
        """Send FIX Logon message (35=A) to initiate the session."""
        if not self.is_connected:
            return
        logon_fields = {"98": "0", "108": "30"} # EncryptMethod, HeartBtInt (30s)
        msg = self._format_fix_message("A", logon_fields)
        self.writer.write(msg)
        await self.writer.drain()
        logger.info("Sent FIX Logon request.")

    async def listen_loop(self):
        """Asynchronously listen for incoming messages, heartbeats, and execution reports."""
        while self.is_connected:
            try:
                data = await self.reader.read(4096)
                if not data:
                    logger.warning("Connection lost from server.")
                    break
                
                message = data.decode('ascii', errors='ignore')
                await self.handle_incoming_message(message)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in listen loop: {e}")
                break

    async def handle_incoming_message(self, raw_message: str):
        """Parse raw FIX byte strings and route heartbeats or execution updates."""
        fields = dict(item.split('=') for item in raw_message.replace('\x01', '|').strip('|').split('|'))
        msg_type = fields.get("35")
        
        if msg_type == "0": # Heartbeat
            logger.debug("Received Heartbeat.")
        elif msg_type == "1": # Test Request
            await self.send_heartbeat()
        elif msg_type == "8": # Execution Report
            logger.info(f"Execution Report received: OrderID={fields.get('37')} Status={fields.get('39')}")

    async def send_heartbeat(self):
        msg = self._format_fix_message("0", {})
        self.writer.write(msg)
        await self.writer.drain()
