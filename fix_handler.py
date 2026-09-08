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
    def __init__(self, host: str, port: int, sender_comp_id: str, target_comp_id: str, state_file: str = "fix_state.json"):
        self.host = host
        self.port = port
        self.sender_comp_id = sender_comp_id
        self.target_comp_id = target_comp_id
        self.state_file = state_file

        # Session State
        self.out_seq_num = 1
        self.in_seq_num = 1
        self.heartbeat_interval = 30

        self.reader = None
        self.writer = None
        self.is_connected = False
        self._load_state()

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

    def _calculate_checksum(self, message: str) -> str:
        checksum = sum(ord(char) for char in message) % 256
        return f"{checksum:03d}"

    def build_message(self, msg_type: str, fields: dict) -> bytes:
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
            f"34={self.out_seq_num}\x01"
            f"52={now_utc}\x01"
        )

        raw_msg_without_trailer = header_base + body
        checksum_str = self._calculate_checksum(raw_msg_without_trailer)
        full_message = raw_msg_without_trailer + f"10={checksum_str}\x01"

        self.out_seq_num += 1
        self._save_state()

        return full_message.encode("ascii")

    async def send_message(self, msg_type: str, fields: dict):
        if not self.writer or not self.is_connected:
            return
        payload = self.build_message(msg_type, fields)
        self.writer.write(payload)
        await self.writer.drain()
        formatted_payload = payload.decode('ascii', errors='replace').replace('\x01', '|')
        logger.debug(f"Sent FIX [MsgType={msg_type}]: {formatted_payload}")

    async def send_heartbeat(self, test_req_id: str = None):
        fields = {}
        if test_req_id:
            fields["112"] = test_req_id
        await self.send_message("0", fields)

    async def send_resend_request(self, begin_seq: int, end_seq: int = 0):
        fields = {"7": str(begin_seq), "16": str(end_seq)}
        await self.send_message("2", fields)

    def parse_message(self, raw_data: str) -> dict:
        fields = {}
        pairs = raw_data.split("\x01")
        for pair in pairs:
            if "=" in pair:
                tag, val = pair.split("=", 1)
                fields[int(tag)] = val
        return fields
