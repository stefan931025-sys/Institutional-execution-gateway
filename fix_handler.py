import asyncio
import json
import os
import logging
import time
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
        self.heartbeat_interval = 30  # Default seconds
        
        self.reader = None
        self.writer = None
        self.is_connected = False
        self._load_state()

    def _load_state(self):
        """Load persisted sequence numbers from disk to prevent session violations on restart."""
        if os.path.exists(self.state_file):
            try:
                with open(self.state_file, "r") as f:
                    data = json.load(f)
                    self.out_seq_num = data.get("out_seq_num", 1)
                    self.in_seq_num = data.get("in_seq_num", 1)
                    logger.info(f"Loaded session state from {self.state_file}: OutSeq={self.out_seq_num}, InSeq={self.in_seq_num}")
            except Exception as e:
                logger.error(f"Failed to load state file, starting fresh: {e}")
        else:
            logger.info("No existing state file found. Initializing sequence numbers at 1.")
            self._save_state()

    def _save_state(self):
        """Persist current session sequence numbers to disk."""
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
        """Calculate standard FIX checksum (sum of all bytes modulo 256, padded to 3 digits)."""
        checksum = sum(ord(char) for char in message) % 256
        return f"{checksum:03d}"

    def build_message(self, msg_type: str, fields: dict) -> bytes:
        """Construct a standardized FIX message string encapsulated with SOH (\\x01) delimiters."""
        body_parts = []
        for tag, val in fields.items():
            body_parts.append(f"{tag}={val}")
        
        body = "\x01".join(body_parts) + "\x01"
        
        # Standard Header elements
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
        
        # Increment outbound sequence number and persist state
        self.out_seq_num += 1
        self._save_state()
        
        return full_message.encode("ascii")

    async def send_message(self, msg_type: str, fields: dict):
        """Send a raw framed FIX message over the TCP socket."""
        if not self.writer or not self.is_connected:
            logger.error("Cannot send message: Socket is not connected.")
            return
        
        payload = self.build_message(msg_type, fields)
        self.writer.write(payload)
        await self.writer.drain()
        logger.debug(f"Sent FIX [MsgType={msg_type}]: {payload.decode('ascii', errors='replace').replace('\x01', '|')}")

    async def send_heartbeat(self, test_req_id: str = None):
        """Transmit a FIX Heartbeat message (MsgType=0)."""
        fields = {}
        if test_req_id:
            fields["112"] = test_req_id  # TestReqID response mapping
        await self.send_message("0", fields)
        logger.info("Heartbeat sent successfully.")

    async def _heartbeat_loop(self):
        """Background coroutine maintaining regular heartbeat checks."""
        try:
            while self.is_connected:
                await asyncio.sleep(self.heartbeat_interval)
                await self.send_heartbeat()
        except asyncio.CancelledError:
            pass

    def parse_message(self, raw_data: str) -> dict:
        """Parse raw SOH-delimited FIX string into a tag-value dictionary."""
        fields = {}
        pairs = raw_data.split("\x01")
        for pair in pairs:
            if "=" in pair:
                tag, val = pair.split("=", 1)
                fields[int(tag)] = val
        return fields

    async def handle_incoming_message(self, raw_message: str):
        """Process inbound messages, validate sequence numbers, and manage session-level triggers."""
        fields = self.parse_message(raw_message)
        msg_seq_num = int(fields.get(34, 0))
        msg_type = fields.get(35)

        logger.debug(f"Received FIX [MsgType={msg_type}, Seq={msg_seq_num}]")

        # Sequence Gap Validation
        if msg_seq_num > self.in_seq_num:
            logger.warning(f"Sequence gap detected! Expected {self.in_seq_num}, but received {msg_seq_num}.")
            # Production protocols would trigger a ResendRequest (Tag 35=2) here.
        elif msg_seq_num < self.in_seq_num:
            logger.error(f"Low sequence number detected (Duplicate/Reset risk). Expected >= {self.in_seq_num}, got {msg_seq_num}.")
            return

        # Advance inbound sequence expectation
        self.in_seq_num = msg_seq_num + 1
        self._save_state()

        # Handle Protocol-Level Messages
        if msg_type == "0":  # Heartbeat
            logger.info("Received Heartbeat from counterparty.")
        elif msg_type == "1":  # Test Request
            test_req_id = fields.get(112)
            logger.info(f"Received TestRequest with TestReqID={test_req_id}. Responding with Heartbeat.")
            await self.send_heartbeat(test_req_id=test_req_id)
        elif msg_type == "A":  # Logon
            logger.info("Logon successful confirmed by counterparty.")
        elif msg_type == "5":  # Logout
            logger.info("Logout message received from counterparty.")
            self.is_connected = False

    async def connect(self):
        """Establish asynchronous TCP socket connection and initiate session lifecycle."""
        logger.info(f"Connecting to FIX engine at {self.host}:{self.port}...")
        try:
            self.reader, self.writer = await asyncio.open_connection(self.host, self.port)
            self.is_connected = True
            logger.info("TCP Connection established.")

            # Send Logon message (MsgType=A)
            logon_fields = {
                "98": "0",  # EncryptMethod (0 = None)
                "108": str(self.heartbeat_interval)  # HeartBtInt
            }
            await self.send_message("A", logon_fields)

            # Start background heartbeat loop
            hb_task = asyncio.create_task(self._heartbeat_loop())

            try:
                while self.is_connected:
                    data = await self.reader.read(4096)
                    if not data:
                        logger.warning("Connection closed by remote host.")
                        break
                    
                    raw_str = data.decode("ascii", errors="ignore")
                    # Handle potential multi-message chunks split by SOH
                    messages = raw_str.split("10=")
                    for msg in messages[:-1]:
                        full_msg = msg + "10=" + messages[messages.index(msg) + 1][:3] + "\x01"
                        await self.handle_incoming_message(full_msg)

            finally:
                hb_task.cancel()
                await hb_task

        except Exception as e:
            logger.error(f"Socket connection error: {e}")
        finally:
            self.is_connected = False
            if self.writer:
                self.writer.close()
                await self.writer.wait_closed()
            logger.info("Connection terminated and resources cleaned up.")

if __name__ == "__main__":
    # Test runner hook for local validation
    handler = FIXHandler(
        host="127.0.0.1",
        port=9800,
        sender_comp_id="CLIENT_SIM",
        target_comp_id="EXCHANGE_SIM"
    )
    # asyncio.run(handler.connect())
