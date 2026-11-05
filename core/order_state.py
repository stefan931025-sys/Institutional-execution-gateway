import json
import os

class SessionSequenceStore:
    def __init__(self, session_id: str, storage_path: str = "./session_state.json"):
        self.session_id = session_id
        self.storage_path = storage_path
        self.inbound_seq = 1
        self.outbound_seq = 1
        self.load_state()

    def load_state(self):
        if os.path.exists(self.storage_path):
            try:
                with open(self.storage_path, "r") as f:
                    data = json.load(f)
                    session_data = data.get(self.session_id, {})
                    self.inbound_seq = session_data.get("inbound_seq", 1)
                    self.outbound_seq = session_data.get("outbound_seq", 1)
            except Exception as e:
                print(f"[WARNING] Failed to load session state, defaulting to 1: {e}")

    def save_state(self):
        data = {}
        if os.path.exists(self.storage_path):
            try:
                with open(self.storage_path, "r") as f:
                    data = json.load(f)
            except Exception:
                pass
        
        data[self.session_id] = {
            "inbound_seq": self.inbound_seq,
            "outbound_seq": self.outbound_seq
        }
        
        with open(self.storage_path, "w") as f:
            json.dump(data, f, indent=4)

    def increment_inbound(self):
        self.inbound_seq += 1
        self.save_state()

    def increment_outbound(self) -> int:
        seq = self.outbound_seq
        self.outbound_seq += 1
        self.save_state()
        return seq
