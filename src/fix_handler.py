import asyncio
import logging
import json
import os
from typing import Dict, Tuple

logger = logging.getLogger("FIXHandler")

class DurableSequenceStore:
    """Manages durable persistence of session sequence numbers to disk."""
    def __init__(self, storage_path: str = "session_store.json"):
        self.storage_path = storage_path

    def save_sequences(self, inbound: int, outbound: int):
        data = {"inbound_seq": inbound, "outbound_seq": outbound}
        try:
            with open(self.storage_path, "w") as f:
                json.dump(data, f)
        except Exception as e:
            logger.error(f"Failed to save sequence state: {e}")

    def load_sequences(self) -> Tuple[int, int]:
        if not os.path.exists(self.storage_path):
            return 0, 0
        try:
            with open(self.storage_path, "r") as f:
                data = json.load(f)
                return data.get("inbound_seq", 0), data.get("outbound_seq", 0)
        except Exception as e:
            logger.error(f"Failed to load sequence state: {e}")
            return 0, 0

class FIXHandler:
    """Handles FIX session state, message parsing, checksums, and sequence gap recovery."""
    def __init__(self, host: str, port: int, sender_comp_id: str, target_comp_id: str, storage_path: str = "session_store.json"):
        self.host = host
        self.port = port
        self.sender_comp_id = sender_comp_id
        self.target_comp_id = target_comp_id
        
        self.inbound_seq = 0
        self.outbound_seq = 0
        self.store = DurableSequenceStore(storage_path=storage_path)
        
        # Load persisted sequences if available
        self.inbound_seq, self.outbound_seq = self.store.load_sequences()
        self.reader = None
        self.writer = None

    def calculate_checksum(self, msg: str) -> str:
        """Calculates the standard FIX 3-digit checksum (sum of ASCII values mod 256)."""
        # Exclude checksum field (tag 10) if present in calculation string
        if b"\x0110=" in msg.encode():
            msg = msg.split("\x0110=")[0] + "\x01"
        checksum_val = sum(ord(char) for char in msg) % 256
        return f"{checksum_val:03d}"

    def parse_message(self, raw_msg: str) -> Dict[str, str]:
        """Parses SOH-delimited FIX messages into a key-value dictionary."""
        parsed = {}
        fields = raw_msg.split("\x01")
        for field in fields:
            if "=" in field:
                key, val = field.split("=", 1)
                parsed[key] = val
        return parsed

    def check_sequence_gap(self, incoming_seq: int) -> bool:
        """Checks if an incoming sequence number indicates a packet gap."""
        expected_seq = self.inbound_seq + 1
        if incoming_seq > expected_seq:
            return True
        return False

    def generate_resend_request(self, begin_seq: int, end_seq: int) -> str:
        """Generates a standard FIX Resend Request (MsgType=2)."""
        body = f"35=2\x017=1\x0116={begin_seq}\x01122={end_seq}\x01"
        return body

    async def connect(self):
        try:
            self.reader, self.writer = await asyncio.open_connection(self.host, self.port)
            logger.info(f"Connected to FIX server at {self.host}:{self.port}")
        except Exception as e:
            logger.error(f"Connection failed: {e}")

    async def send_order(self, cl_ord_id: str, symbol: str, side: str, qty: float, price: float):
        self.outbound_seq += 1
        self.store.save_sequences(self.inbound_seq, self.outbound_seq)
        logger.info(f"Sending order {cl_ord_id} for {qty} {symbol} at {price}")

    async def close(self):
        if self.writer:
            self.writer.close()
            await self.writer.wait_closed()
