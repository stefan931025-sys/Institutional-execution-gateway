import asyncio
import logging
from database import init_db, load_session_state, update_session_state, persist_order_status

logger = logging.getLogger(__name__)

class FixSocketClient:
    def __init__(self, host: str, port: int, sender_comp_id: str, target_comp_id: str, session_id: str = "DEFAULT_SESSION"):
        self.host = host
        self.port = port
        self.sender_comp_id = sender_comp_id
        self.target_comp_id = target_comp_id
        self.session_id = session_id
        self.in_seq_num = 1
        self.out_seq_num = 1
        self.reader = None
        self.writer = None
        self.is_connected = False

    async def initialize(self):
        """Initialize the database and load the last persisted session state."""
        await init_db()
        self.in_seq_num, self.out_seq_num = await load_session_state(self.session_id)
        logger.info(f"Session initialized from disk. InSeq={self.in_seq_num}, OutSeq={self.out_seq_num}")

    async def connect(self):
        """Establish a real TCP connection and initialize session state first."""
        await self.initialize()
        try:
            self.reader, self.writer = await asyncio.open_connection(self.host, self.port)
            self.is_connected = True
            logger.info(f"Connected to FIX endpoint at {self.host}:{self.port}")
            await self.send_logon()
        except Exception as e:
            logger.error(f"Failed to connect to FIX server: {e}")
            self.is_connected = False

    def _format_fix_message(self, msg_type: str, body_fields: dict) -> bytes:
        """Construct raw FIX message with sequence numbers and checksum."""
        body = f"35={msg_type}|49={self.sender_comp_id}|56={self.target_comp_id}|34={self.out_seq_num}|"
        for tag, val in body_fields.items():
            body += f"{tag}={val}|"
            
        header = f"8=FIX.4.2|9={len(body)}|"
        raw_message = header + body
        
        # Calculate checksum (Tag 10)
        checksum = sum(bytes(raw_message.replace('|', '\x01'), 'ascii')) % 256
        complete_message = raw_message.replace('|', '\x01') + f"10={checksum:03d}\x01"
        
        # Increment outbound sequence number
        self.out_seq_num += 1
        return complete_message.encode('ascii')

    async def send_logon(self):
        """Send FIX Logon message (35=A) and persist updated sequence state."""
        if not self.is_connected:
            return
        logon_fields = {"98": "0", "108": "30"} # EncryptMethod, HeartBtInt
        msg = self._format_fix_message("A", logon_fields)
        self.writer.write(msg)
        await self.writer.drain()
        
        await update_session_state(self.in_seq_num, self.out_seq_num, self.session_id)
        logger.info("Sent FIX Logon request and persisted state.")

    async def send_order(self, symbol: str, side: str, order_qty: float, price: float, cl_ord_id: str):
        """Submit a New Order Single (35=D) to the exchange/sandbox."""
        if not self.is_connected or not self.writer:
            logger.error("Cannot send order: Not connected.")
            return False

        order_fields = {
            "11": cl_ord_id,
            "54": side,                # '1' = Buy, '2' = Sell
            "38": str(order_qty),
            "40": "2",                 # Limit Order
            "44": str(price),
            "55": symbol,
            "60": str(asyncio.get_event_loop().time())
        }

        msg = self._format_fix_message("D", order_fields)
        self.writer.write(msg)
        await self.writer.drain()

        # Persist initial order state locally
        await persist_order_status(
            order_id="PENDING_" + cl_ord_id, 
            cl_ord_id=cl_ord_id, 
            symbol=symbol, 
            side=side, 
            price=price, 
            qty=order_qty, 
            status="NEW"
        )
        
        await update_session_state(self.in_seq_num, self.out_seq_num, self.session_id)
        logger.info(f"New Order Single sent: ClOrdID={cl_ord_id} {side} {order_qty} @ {price}")
        return True

    async def listen_loop(self):
        """Continuously listen for incoming network traffic and parse messages."""
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
        """Parse incoming bytes, increment inbound sequence, and persist reports."""
        fields = dict(item.split('=') for item in raw_message.replace('\x01', '|').strip('|').split('|'))
        
        # Track inbound sequence number from header (Tag 34)
        if "34" in fields:
            self.in_seq_num = int(fields["34"]) + 1
            await update_session_state(self.in_seq_num, self.out_seq_num, self.session_id)

        msg_type = fields.get("35")
        
        if msg_type == "0":
            logger.debug("Received Heartbeat.")
        elif msg_type == "8": # Execution Report
            order_id = fields.get('37', 'UNKNOWN')
            cl_ord_id = fields.get('11', 'UNKNOWN')
            symbol = fields.get('55', 'UNKNOWN')
            side = fields.get('54', 'UNKNOWN')
            price = float(fields.get('44', 0.0))
            qty = float(fields.get('38', 0.0))
            status = fields.get('39', 'UNKNOWN')
            filled_qty = float(fields.get('14', 0.0))
            
            await persist_order_status(order_id, cl_ord_id, symbol, side, price, qty, status, filled_qty)
            logger.info(f"Execution Report processed & saved: OrderID={order_id} Status={status}")

    async def start_heartbeat_loop(self, interval: int = 30):
        """Background task to send periodic heartbeats to maintain the FIX session."""
        while self.is_connected:
            try:
                await asyncio.sleep(interval)
                if self.is_connected and self.writer:
                    msg = self._format_fix_message("0", {}) # Heartbeat (35=0)
                    self.writer.write(msg)
                    await self.writer.drain()
                    await update_session_state(self.in_seq_num, self.out_seq_num, self.session_id)
                    logger.debug("Sent periodic Heartbeat.")
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in heartbeat loop: {e}")
                break
