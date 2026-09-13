import asyncio
import json
import logging
import os
from typing import Callable, Optional

logger = logging.getLogger("FIXHandler")

class DurableSequenceStore:
    """Manages persistent FIX session sequence numbers to ensure state resilience."""
    def __init__(self, filepath: str = "seq_state.json"):
        self.filepath = filepath
        self.in_cnt, self.out_cnt = self.load_sequences()

    def load_sequences(self) -> tuple:
        if os.path.exists(self.filepath):
            try:
                with open(self.filepath, "r") as f:
                    data = json.load(f)
                    return data.get("in_seq", 1), data.get("out_seq", 1)
            except Exception:
                return 1, 1
        return 1, 1

    def save_sequences(self, in_seq: int, out_seq: int):
        self.in_cnt = in_seq
        self.out_cnt = out_seq
        with open(self.filepath, "w") as f:
            json.dump({"in_seq": in_seq, "out_seq": out_seq}, f)

class FIXHandler:
    def __init__(self, host: str, port: int, sender_comp_id: str, target_comp_id: str):
        self.host = host
        self.port = port
        self.sender_comp_id = sender_comp_id
        self.target_comp_id = target_comp_id
        
        self.store = DurableSequenceStore()
        self.reader: Optional[asyncio.StreamReader] = None
        self.writer: Optional[asyncio.StreamWriter] = None
        self.is_connected = False

    def _generate_checksum(self, msg: str) -> str:
        """Calculates standard FIX checksum (modulo 256 sum of all characters)."""
        return f"{sum(ord(c) for c in msg) % 256:03d}"

    def build_message(self, msg_type: str, fields: dict) -> str:
        """Constructs a standard SOH-delimited FIX message string."""
        self.store.out_cnt += 1
        self.store.save_sequences(self.store.in_cnt, self.store.out_cnt)

        body = [
            "8=FIX.4.2",
            f"9=0",  # Placeholder, computed dynamically if needed
            f"35={msg_type}",
            f"49={self.sender_comp_id}",
            f"56={self.target_comp_id}",
            f"34={self.store.out_cnt}",
            f"52=20260312-00:00:00.000"
        ]

        for tag, val in fields.items():
            body.append(f"{tag}={val}")

        raw_msg = "\x01".join(body) + "\x01"
        body_length = len(raw_msg.encode('ascii'))
        
        # Re-inject correct body length (tag 9)
        raw_msg = raw_msg.replace("9=0", f"9={body_length}")
        
        checksum = self._generate_checksum(raw_msg)
        complete_msg = f"{raw_msg}10={checksum}\x01"
        return complete_msg

    async def connect(self):
        """Establishes TCP connection to the exchange FIX endpoint and logs on."""
        try:
            logger.info(f"Connecting to FIX Gateway at {self.host}:{self.port}...")
            self.reader, self.writer = await asyncio.open_connection(self.host, self.port)
            self.is_connected = True
            logger.info("TCP connection established. Sending FIX Logon...")
            
            logon_msg = self.build_message("A", {"98": "0", "108": "30"})
            self.writer.write(logon_msg.encode('ascii'))
            await self.writer.drain()
            
        except Exception as e:
            logger.error(f"Failed to connect to FIX server: {e}")
            self.is_connected = False

    async def send_order(self, cl_ord_id: str, symbol: str, side: str, order_qty: float, price: float):
        """Dispatches a New Order Single (MsgType=D) over the FIX session."""
        if not self.is_connected or not self.writer:
            logger.error("Cannot send order: FIX session is disconnected.")
            return

        order_msg = self.build_message("D", {
            "11": cl_ord_id,
            "55": symbol,
            "54": side,  # '1' = Buy, '2' = Sell
            "38": str(order_qty),
            "44": str(price),
            "40": "2",   # Limit Order
            "59": "0"    # Day
        })

        self.writer.write(order_msg.encode('ascii'))
        await self.writer.drain()
        logger.info(f"FIX Order Dispatched [ClOrdID: {cl_ord_id}, Symbol: {symbol}, Qty: {order_qty}]")

    async def listen_loop(self, on_fill_callback: Callable):
        """Asynchronous loop listening for incoming FIX messages from the exchange."""
        try:
            while self.is_connected and self.reader:
                data = await self.reader.read(4096)
                if not data:
                    logger.warning("Exchange closed the FIX connection.")
                    break
                
                message = data.decode('ascii', errors='ignore')
                logger.debug(f"Received FIX Message: {message.replace(chr(1), '|')}")
                
                # Simple pattern match check for execution reports (MsgType=8)
                if "35=8" in message:
                    # Trigger fill callback for processing
                    await on_fill_callback("MOCK_CL_ORD_ID", 10.0, 65.00)

        except Exception as e:
            logger.error(f"Error in FIX listen loop: {e}")
        finally:
            self.is_connected = False

    async def close(self):
        """Gracefully shuts down the FIX session."""
        if self.writer:
            self.writer.close()
            await self.writer.wait_closed()
        self.is_connected = False
        logger.info("FIX session closed securely.")
