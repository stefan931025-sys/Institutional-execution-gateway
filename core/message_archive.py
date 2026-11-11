import sqlite3
import logging

logger = logging.getLogger("OutboundMessageArchive")

class OutboundMessageArchive:
    def __init__(self, db_path: str = ":memory:"):
        """
        Persistent outbound message archive backed by SQLite to support
        crash recovery and prevent unbounded memory growth during long trading sessions.
        """
        self.db_path = db_path
        self._init_db()

    def _init_db(self):
        """Initializes the SQLite message archive schema."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS message_archive (
                    seq_num INTEGER PRIMARY KEY,
                    raw_msg TEXT NOT NULL
                )
            """)
            conn.commit()

    def store_message(self, seq_num: int, raw_msg: str):
        """Stores an outbound FIX message mapped by its sequence number."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                "INSERT OR REPLACE INTO message_archive (seq_num, raw_msg) VALUES (?, ?)",
                (seq_num, raw_msg)
            )
            conn.commit()

    def get_messages_for_range(self, start_seq: int, end_seq: int) -> list:
        """Retrieves messages for a gap-fill retransmission range from SQLite."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # If end_seq is 0 or infinity-equivalent, fetch everything from start_seq onwards
            if end_seq <= 0:
                cursor.execute(
                    "SELECT raw_msg FROM message_archive WHERE seq_num >= ? ORDER BY seq_num ASC",
                    (start_seq,)
                )
            else:
                cursor.execute(
                    "SELECT raw_msg FROM message_archive WHERE seq_num BETWEEN ? AND ? ORDER BY seq_num ASC",
                    (start_seq, end_seq)
                )
            rows = cursor.fetchall()
            
        return [row[0] for row in rows]
