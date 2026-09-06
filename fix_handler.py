import asyncio
import logging
from typing import Dict, Any

logger = logging.getLogger("FIXHandler")

class AsyncFIXHandler:
    def __init__(self, host: str, port: int, sender_comp_id: str, target_comp_id: str):
        self.host = host
        self.port = port
        self.sender_comp_id = sender_comp_id
        self.target_comp_id = target_comp_id
        self.inbound_seq_num = 1
        self.outbound_seq_num = 1
        self.reader = None
        self.writer = None
        self.is_connected = False

    async def connect(self):
        """Establish persistent TCP connection with the exchange gateway."""
        try:
            self.reader, self.writer = await asyncio.open_connection(self.host, self.port)
            self.is_connected = True
            logger.info(f"Connected to FIX Gateway endpoint at {self.host}:{self.port}")
            await self._send_logon()
        except Exception as e:
            logger.error(f"Failed to connect to FIX endpoint: {e}")
            self.is_connected = False

    def _format_fix_message(self, msg_type: str, fields: Dict[int, Any]) -> bytes:
        """Constructs a raw FIX message payload with standard header, body, and trailer checksum."""
        body_parts = [
            f"35={msg_type}",
            f"49={self.sender_comp_id}",
            f"56={self.target_comp_id}",
            f"34={self.outbound_seq_num}"
        ]
        
        for tag, val in fields.items():
            body_parts.append(f"{tag}={val}")
            
        body = "\x01".join(body_parts) + "\x01"
        
        # Standard header containing FIX version and calculated body length (Tag 9)
        header = f"8=FIX.4.2\x019={len(body)}\x01"
        raw_msg = header + body
        
        # Checksum calculation: sum of all bytes modulo 256, formatted as a 3-digit string
        checksum = sum(raw_msg.encode('ascii')) % 256
        full_message = f"{raw_msg}10={checksum:03d}\x01"
        
        self.outbound_seq_num += 1
        return full_message.encode('ascii')

    async def _send_logon(self):
        """Dispatches the mandatory FIX Logon sequence (MsgType = A)."""
        logon_fields = {
            98: 0,   # EncryptMethod: None/Other
            108: 30  # HeartBtInt: 30 seconds heartbeat interval
        }
        msg = self._format_fix_message("A", logon_fields)
        self.writer.write(msg)
        await self.writer.drain()
        logger.info("Sent FIX Logon sequence.")

    async def send_order(self, symbol: str, side: str, qty: float, price: float):
        """Translates an internal hedge trigger into a FIX New Order - Single (MsgType = D)."""
        side_code = '1' if side.upper() == 'BUY' else '2'
        
        order_fields = {
            11: f"CLORD-{int(asyncio.get_event_loop().time() * 1000)}", # ClOrdID
            55: symbol,                                                 # Symbol
            54: side_code,                                              # Side ('1'=Buy, '2'=Sell)
            38: qty,                                                    # OrderQty
            40: '2',                                                    # OrdType ('2' = Limit)
            44: price,                                                  # Price
            59: '0'                                                     # TimeInForce ('0' = Day)
        }
        
        msg = self._format_fix_message("D", order_fields)
        if self.writer and self.is_connected:
            self.writer.write(msg)
            await self.writer.drain()
            logger.info(f"FIX NewOrderSingle dispatched [Symbol: {symbol}, Side: {side}, Qty: {qty}, Price: {price}]")

    async def listen_loop(self):
        """Asynchronously parses incoming byte stream and handles session messages."""
        buffer = b""
        while self.is_connected:
            try:
                data = await self.reader.read(4096)
                if not data:
                    logger.warning("Connection closed by exchange FIX gateway.")
                    break
                buffer += data
                
                while b"\x01" in buffer:
                    # Basic frame extraction based on SOH delimiter
                    parts = buffer.split(b"\x01")
                    # Advance buffer past parsed segment
                    buffer = b"".join([p + b"\x01" for p in parts[1:]])
                    
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error encountered in FIX listen loop: {e}")
                break

    async def close(self):
        """Closes the network connection cleanly."""
        if self.writer:
            self.writer.close()
            await self.writer.wait_closed()
            self.is_connected = False
            logger.info("FIX session terminated gracefully.")
