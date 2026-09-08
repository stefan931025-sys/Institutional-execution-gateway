class FIXGapFillHandler:
    def __init__(self, archive: OutboundMessageArchive):
        self.archive = archive

    def handle_resend_request(self, fix_msg: dict) -> list:
        """Processes Tag 7 (BeginSeqNo) and Tag 16 (EndSeqNo)."""
        begin_seq = int(fix_msg.get("BeginSeqNo", 0))
        end_seq = int(fix_msg.get("EndSeqNo", 0))
        
        print(f"[GAP FILL] Resend requested for sequence range: {begin_seq} to {end_seq}")
        
        # Retrieve original messages
        raw_messages = self.archive.get_messages_for_range(begin_seq, end_seq)
        
        retransmission_payloads = []
        for msg in raw_messages:
            # In a production FIX engine, administrative messages (like heartbeats/logons) 
            # are replaced with a Sequence Reset (GapFillFlag=Y) rather than re-sending 
            # sensitive execution data. For execution reports, they are re-sent as-is 
            # with PossDupFlag (Tag 43) set to 'Y'.
            modified_msg = self._inject_poss_dup(msg)
            retransmission_payloads.append(modified_msg)
            
        return retransmission_payloads

    def _inject_poss_dup(self, raw_msg: str) -> str:
        """Injects PossDupFlag=Y (Tag 43) into retransmitted messages."""
        # Simple string manipulation stub for FIX field insertion
        if "43=Y" not in raw_msg:
            return raw_msg.replace("\x01", "\x0143=Y\x01", 1)
        return raw_msg
