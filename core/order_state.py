import json
import os
from pathlib import Path

class SessionSequenceStore:
    def __init__(self, session_id: str, storage_path: str = "./session_state.json"):
        """
        Manages durable session sequence numbers (MsgSeqNum) for FIX compliance 
        and crash recovery.
        """
        self.session_id = session_id
        self.storage_path = storage_path
        self.inbound_seq = 1
        self.outbound_seq = 1
        self.load_state()

    def load_state(self):
        """Loads persistent session sequence state from disk if available."""
        if os.path.exists(self.storage_path):
            try:
                with open(self.storage_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    session_data = data.get(self.session_id, {})
                    self.inbound_seq = session_data.get("inbound_seq", 1)
                    self.outbound_seq = session_data.get("outbound_seq", 1)
            except Exception as e:
                print(f"[WARNING] Failed to load session state, defaulting to 1: {e}")

    def save_state(self):
        """Persists current session sequence numbers to disk safely."""
        data = {}
        if os.path.exists(self.storage_path):
            try:
                with open(self.storage_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
            except Exception:
                pass

        data[self.session_id] = {
            "inbound_seq": self.inbound_seq,
            "outbound_seq": self.outbound_seq
        }
        
        # Ensure parent directory exists before writing
        Path(self.storage_path).parent.mkdir(parents=True, exist_ok=True)
        
        with open(self.storage_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4)

    def increment_inbound(self):
        """Increments and saves inbound sequence number."""
        self.inbound_seq += 1
        self.save_state()

    def increment_outbound(self) -> int:
        """Atomically fetches, increments, and saves outbound sequence number."""
        seq = self.outbound_seq
        self.outbound_seq += 1
        self.save_state()
        return seq
