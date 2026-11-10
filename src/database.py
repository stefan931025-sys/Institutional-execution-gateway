import aiosqlite
import logging

logger = logging.getLogger(__name__)

DB_NAME = "fix_gateway.db"

async def init_db():
    """Initialize the SQLite database and create required tables if they don't exist."""
    async with aiosqlite.connect(DB_NAME) as db:
        # Session state table to persist inbound and outbound FIX sequence numbers
        await db.execute("""
            CREATE TABLE IF NOT EXISTS session_state (
                session_id TEXT PRIMARY KEY,
                in_seq_num INTEGER NOT NULL,
                out_seq_num INTEGER NOT NULL,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Order status table to log execution reports and order tracking
        await db.execute("""
            CREATE TABLE IF NOT EXISTS orders (
                order_id TEXT PRIMARY KEY,
                cl_ord_id TEXT NOT NULL,
                symbol TEXT NOT NULL,
                side TEXT NOT NULL,
                price REAL NOT NULL,
                qty REAL NOT NULL,
                status TEXT NOT NULL,
                filled_qty REAL DEFAULT 0.0,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        await db.commit()
        logger.info("Database initialized successfully.")

async def load_session_state(session_id: str = "DEFAULT_SESSION") -> tuple[int, int]:
    """Load the last persisted sequence numbers for the FIX session. Returns (in_seq, out_seq)."""
    async with aiosqlite.connect(DB_NAME) as db:
        async with db.execute(
            "SELECT in_seq_num, out_seq_num FROM session_state WHERE session_id = ?", 
            (session_id,)
        ) as cursor:
            row = await cursor.fetchone()
            if row:
                return row[0], row[1]
            else:
                # Default starting sequence numbers if none exist yet
                await db.execute(
                    "INSERT INTO session_state (session_id, in_seq_num, out_seq_num) VALUES (?, 1, 1)",
                    (session_id,)
                )
                await db.commit()
                return 1, 1

async def update_session_state(in_seq: int, out_seq: int, session_id: str = "DEFAULT_SESSION"):
    """Update and persist the current sequence numbers."""
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute(
            """
            UPDATE session_state 
            SET in_seq_num = ?, out_seq_num = ?, updated_at = CURRENT_TIMESTAMP 
            WHERE session_id = ?
            """,
            (in_seq, out_seq, session_id)
        )
        await db.commit()

async def persist_order_status(
    order_id: str, 
    cl_ord_id: str, 
    symbol: str, 
    side: str, 
    price: float, 
    qty: float, 
    status: str, 
    filled_qty: float = 0.0
):
    """Insert or update an order state based on inbound execution reports."""
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute(
            """
            INSERT INTO orders (order_id, cl_ord_id, symbol, side, price, qty, status, filled_qty, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(order_id) DO UPDATE SET
                status = excluded.status,
                filled_qty = excluded.filled_qty,
                updated_at = CURRENT_TIMESTAMP
            """,
            (order_id, cl_ord_id, symbol, side, price, qty, status, filled_qty)
        )
        await db.commit()
        logger.debug(f"Persisted order state: ClOrdID={cl_ord_id}, Status={status}")
