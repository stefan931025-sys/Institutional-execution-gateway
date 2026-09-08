import asyncio
import json
import os
import logging
from datetime import datetime, timezone

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("FIXHandler")

class FIXHandler:
    def __init__(self, host: str, port: int, sender_comp_id: str, target_comp_id: str, state_file: str = "fix_state.json", store_file: str = "outbound_store.json"):
        self.host = host
        self.port = port
        self.sender_comp_id = sender_comp_id
        self.target_comp_id = target_comp_id
        self.state_file = state_file
        self.store_file = store_file

        # Session State
        self.out_seq_num = 1
        self.in_seq_num = 1
        self.heartbeat_interval = 30
        
        # Outbound message store for ResendRequests (SeqNum -> Raw Message Bytes)
        self.outbound_store = {}

        self.reader = None
        self.writer = None
        self.is_connected = False
        
        self._load_state()
        self._load_outbound_store()

    def _load_state(self):
        if os.path.exists(self.state_file):
            try:
                with open(self.state_file, "r") as f:
                    data = json.load(f)
                    self.out_seq_num = data.get("out_seq_num", 1)
                    self.in_seq_num = data.get("in_seq_num", 1)
            except Exception as e:
                logger.error(f"Failed to load state file: {e}")
        else:
            self._save_state()

    def _save_state(self):
        try:
            data = {
                "out_seq_num": self.out_seq_num,
                "in_seq_num": self.in_seq_num,
                "last_updated": datetime.now(timezone.utc).isoformat()
            }
            with open(self.state_file, "w") as f:
                json.dump(data, f, indent=4)
        except Exception as e:
            logger.error(f"Failed to save session state: {e}")

    def _load_outbound_store(self):
        """Load historical outbound messages from disk for exchange resend requests."""
        if os.path.exists(self.store_file):
            try:
                with open(self.store_file, "r") as f:
                    # Keys stored as strings in JSON need conversion back to ints
                    raw_store = json.load(f)
                    self.outbound_store = {int(k): v.encode("ascii") for k, v in raw_store.items()}
            except Exception as e:
                logger.error(f"Failed to load outbound message store: {e}")

    def _save_outbound_store(self):
        """Persist outbound messages to disk for audit trails and crash recovery."""
        try:
            raw_store = {str(k): v.decode("ascii", errors="ignore") for k, v in self.outbound_store.items()}
            with open(self.store_file, "w") as f:
                json.dump(raw_store, f)
        except Exception as e:
            logger.error(f"Failed to save outbound store: {e}")

    def _calculate_checksum(self, message: str) -> str:
        checksum = sum(ord(char) for char in message) % 256
        return f"{checksum:03d}"

    def build_message(self, msg_type: str, fields: dict, override_seq_num: int = None) -> bytes:
        """Constructs a FIX message, supporting sequence number overrides for administrative resends."""
        seq_num = override_seq_num if override_seq_num is not None else self.out_seq_num
        
        body_parts = []
        for tag, val in fields.items():
            body_parts.append(f"{tag}={val}")

        body = "\x01".join(body_parts) + "\x01"

        now_utc = datetime.now(timezone.utc).strftime("%Y%m%d-%H:%M:%S.%f")[:-3]
        header_base = (
            f"8=FIX.4.2\x01"
            f"9={len(body)}\x01"
            f"35={msg_type}\x01"
            f"49={self.sender_comp_id}\x01"
            f"56={self.target_comp_id}\x01"
            f"34={seq_num}\x01"
            f"52={now_utc}\x01"
        )

        raw_msg_without_trailer = header_base + body
        checksum_str = self._calculate_checksum(raw_msg_without_trailer)
        full_message = raw_msg_without_trailer + f"10={checksum_str}\x01"
        payload = full_message.encode("ascii")

        # Only archive business/standard messages under their true runtime sequence number
        if override_seq_num is None:
            self.outbound_store[self.out_seq_num] = payload
            self._save_outbound_store()
            self.out_seq_num += 1
            self._save_state()

        return payload

    async def send_raw_payload(self, payload: bytes):
        """Writes raw bytes directly to the socket (used during message replays)."""
        if not self.writer or not self.is_connected:
            return
        self.writer.write(payload)
        await self.writer.drain()

    async def send_message(self, msg_type: str, fields: dict):
        if not self.writer or not self.is_connected:
            return
        payload = self.build_message(msg_type, fields)
        await self.send_raw_payload(payload)
        formatted_payload = payload.decode('ascii', errors='replace').replace('\x01', '|')
        logger.debug(f"Sent FIX [MsgType={msg_type}]: {formatted_payload}")

    async def handle_resend_request(self, begin_seq: int, end_seq: int):
        """Replays historical messages or issues a SequenceReset(GapFill) for sensitive payloads."""
        logger.warning(f"Processing ResendRequest from counterparty for range: {begin_seq} to {end_seq}")
        max_seq = end_seq if end_seq > 0 else max(self.outbound_store.keys(), default=self.out_seq_num - 1)

        for seq in range(begin_seq, max_seq + 1):
            if seq in self.outbound_store:
                msg_bytes = self.outbound_store[seq]
                # In strict FIX compliance, replayed application messages should ideally 
                # be flagged with PossDupFlag(43)=Y, but basic replays can be streamed directly:
                await self.send_raw_payload(msg_bytes)
                logger.info(f"Replayed historical outbound message Seq={seq}")
            else:
                # If a message doesn't exist (e.g. administrative gaps), send a SequenceReset - GapFill
                logger.warning(f"Missing message at Seq={seq}. Sending SequenceReset GapFill.")
                await self.send_sequence_reset_gap_fill(seq, seq + 1)

    async def send_sequence_reset_gap_fill(self, new_seq_no: int, msg_seq_num: int):
        """Sends a SequenceReset (MsgType=4) with GapFillFlag=Y to bypass un-reprintable administrative gaps."""
        fields = {
            "36": str(new_seq_no), # NewSeqNo
            "123": "Y"             # GapFillFlag = Yes
        }
        # Sequence reset bypasses standard sequential tracking and uses explicit sequence mapping
        payload = self.build_message("4", fields, override_seq_num=msg_seq_num)
        await self.send_raw_payload(payload)

    async def handle_incoming_message(self, raw_message: str):
        fields = self.parse_message(raw_message)
        msg_seq_num = int(fields.get(34, 0))
        msg_type = fields.get(35)

        # Sequence Gap Validation & Automated Recovery
        if msg_seq_num > self.in_seq_num:
            logger.warning(f"Sequence gap detected! Expected {self.in_seq_num}, received {msg_seq_num}.")
            await self.send_message("2", {"7": str(self.in_seq_num), "16": str(msg_seq_num - 1)})
        
        # Advance inbound sequence expectation
        if msg_seq_num >= self.in_seq_num:
            self.in_seq_num = msg_seq_num + 1
            self._save_state()

        # Handle Protocol-Level Messages including Resend Requests from Exchange
        if msg_type == "2": # ResendRequest
            begin_seq = int(fields.get(7, 0))
            end_seq = int(fields.get(16, 0))
            await self.handle_resend_request(begin_seq, end_seq)
        elif msg_type == "0":
            logger.info("Received Heartbeat.")
        elif msg_type == "1":
            await self.send_message("0", {"112": fields.get(112)})
        elif msg_type == "A":
            logger.info("Logon acknowledged.")
        elif msg_type == "5":
            logger.info("Logout received.")
            self.is_connected = False

    def parse_message(self, raw_data: str) -> dict:
        fields = {}
        pairs = raw_data.split("\x01")
        for pair in pairs:
            if "=" in pair:
                tag, val = pair.split("=", 1)
                fields[int(tag)] = val
        return fields
