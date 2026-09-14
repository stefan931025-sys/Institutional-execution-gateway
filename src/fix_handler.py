import time
import json
import os
import logging
from typing import Dict, Tuple

logger = logging.getLogger("FIXHandler")

class DurableSequenceStore:
    """Manages persistent storage for inbound and outbound sequence numbers across restarts."""
    def __init__(self, storage_path: str = "session_store.json"):
        self.storage_path = storage_path

    def save_sequences(self, inbound: int, outbound: int):
        data = {"inbound_seq": inbound, "outbound_seq": outbound}
        try:
            with open(self.storage_path, "w") as f:
                json.dump(data, f)
        except Exception as e:
            logger.error(f"Failed to persist sequence numbers: {e}")

    def load_sequences(self) -> Tuple[int, int]:
        if not os.path.exists(self.storage_path):
            return 1, 1
        try:
            with open(self.storage_path, "r") as f:
                data = json.load(f)
                return data.get("inbound_seq", 1), data.get("outbound_seq", 1)
        except Exception as e:
            logger.error(f"Failed to load sequence numbers: {e}")
            return 1, 1


class FIXHandler:
    def __init__(self, host: str, port: int, sender_comp_id: str, target_comp_id: str, store_path: str = "session_store.json"):
        self.host = host
        self.port = port
        self.sender_comp_id = sender_comp_id
        self.target_comp_id = target_comp_id
        
        self.store = DurableSequenceStore(store_path)
        self.inbound_seq, self.outbound_seq = self.store.load_sequences()
        self.reader = None
        self.writer = None

    def calculate_checksum(self, msg: str) -> str:
        """Calculates the standard FIX 3-digit checksum (sum of all bytes modulo 256)."""
        checksum_val = sum(ord(char) for char in msg) % 256
        return f"{checksum_val:03d}"

    def parse_message(self, raw_msg: str) -> Dict[str, str]:
        """Parses an SOH-delimited raw FIX message into a dictionary of tag-value pairs."""
        tags = {}
        fields = raw_msg.split("\x01")
        for field in fields:
            if "=" in field:
                parts = field.split("=", 1)
                tags[parts[0]] = parts[1]
        return tags

    def check_sequence_gap(self, incoming_seq: int) -> bool:
        """Identifies if a sequence gap has occurred based on expected inbound sequence."""
        if incoming_seq > self.inbound_seq:
            return True
        return False

    def generate_resend_request(self, begin_seq: int, end_seq: int) -> str:
        """Generates a FIX Resend Request (MsgType = 2) message string."""
        msg_type = "35=2"
        begin_tag = f"7={begin_seq}"
        end_tag = f"16={end_seq}"
        body = f"{msg_type}\x01{begin_tag}\x01{end_tag}\x01"
        return self._wrap_message(body)

    def generate_logon_message(self, heartbeat_secs: int = 10) -> str:
        """Generates a standard FIX Logon (MsgType = A) message with compliance fields."""
        msg_type = "35=A"
        encrypted_method = "98=0"  # None / Other
        heartbeat_tag = f"108={heartbeat_secs}"
        body = f"{msg_type}\x01{encrypted_method}\x01{heartbeat_tag}\x01"
        return self._wrap_message(body)

    def _wrap_message(self, body: str) -> str:
        """Wraps a FIX body with standard header and trailer (Checksum)."""
        header_base = f"8=FIX.4.2\x019={len(body)}\x0149={self.sender_comp_id}\x0156={self.target_comp_id}\x0134={self.outbound_seq}\x01"
        unsigned_msg = header_base + body
        checksum = self.calculate_checksum(unsigned_msg)
        full_msg = unsigned_msg + f"10={checksum}\x01"
        
        self.outbound_seq += 1
        self.store.save_sequences(self.inbound_seq, self.outbound_seq)
        return full_msg

    async def connect(self):
        """Asynchronously connects to the FIX acceptor endpoint."""
        try:
            self.reader, self.writer = await asyncio.open_connection(self.host, self.port)
            logger.info(f"Connected to FIX endpoint at {self.host}:{self.port}")
        except Exception as e:
            logger.error(f"Connection failed: {e}")
            raise

    async def send_order(self, cl_ord_id: str, symbol: str, side: str, qty: float, price: float):
        """Sends a New Order - Single (MsgType = D) message."""
        side_code = "1" if side.upper() == "BUY" else "2"
        body = f"35=D\x0111={cl_ord_id}\x0155={symbol}\x0154={side_code}\x0138={qty}\x0144={price}\x0140=2\x01"
        msg = self._wrap_message(body)
        
        if self.writer:
            self.writer.write(msg.encode('utf-8'))
            await self.writer.drain()
            logger.info(f"Sent Order {cl_ord_id} for {symbol}")

    async def close(self):
        """Closes the network connection gracefully."""
        if self.writer:
            self.writer.close()
            await self.writer.wait_closed()
            logger.info("FIX connection closed.")
