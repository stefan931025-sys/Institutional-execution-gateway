class OutboundMessageArchive:
    def __init__(self):
        # In-memory archive for speed (can be backed by SQLite or disk log)
        # Maps MsgSeqNum -> Raw FIX Message String
        self.archive = {}

    def store_message(self, seq_num: int, raw_msg: str):
        self.archive[seq_num] = raw_msg

    def get_messages_for_range(self, start_seq: int, end_seq: int) -> list:
        """Retrieves messages for a gap-fill retransmission range."""
        replayed_messages = []
        # If end_seq is 0 (or infinity equivalent in FIX, e.g., 999999), 
        # it means retransmit all from start_seq onwards.
        max_seq = end_seq if end_seq > 0 else max(self.archive.keys(), default=0)
        
        for seq in range(start_seq, max_seq + 1):
            if seq in self.archive:
                replayed_messages.append(self.archive[seq])
        return replayed_messages
