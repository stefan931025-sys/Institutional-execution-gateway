import aiosqlite
import logging

logger = logging.getLogger(__name__)

DB_NAME = "gateway_state.db"

async def init_db():
    """Initialize the local SQLite database to persist session state and orders."""
    async with aiosqlite.connect(DB_NAME) as db:
        # Table to track FIX session sequence numbers across restarts
        await db.execute("""
            CREATE TABLE IF NOT EXISTS session_state (
                session_id TEXT PRIMARY KEY,
                in_seq_num INTEGER,
                out_seq_num INTEGER,
                last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        # Table to persist order execution reports and states
        await db.execute("""
            CREATE TABLE IF NOT EXISTS orders (
                order_id TEXT PRIMARY KEY,
                cl_ord_id TEXT,
                symbol TEXT,
                side TEXT,
                price REAL,
                quantity REAL,
                status TEXT,
                filled_qty REAL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        await db.commit()
        logger.info("Database initialized and persistence layer ready.")

async def load_session_state(session_id: str = "DEFAULT_SESSION") -> tuple:
    """Load the last known sequence numbers so we don't violate FIX protocol on restart."""
    async with aiosqlite.connect(DB_NAME) as db:
        async with db.execute(
            "SELECT in_seq_num, out_seq_num FROM session_state WHERE session_id = ?", 
            (session_id,)
        ) as cursor:
            row = await cursor.fetchone()
            if row:
                logger.info(f"Loaded session state: InSeq={row[0]}, OutSeq={row[1]}")
                return row[0], row[1]
            else:
                # Default starting sequence numbers for a new session
                await db.execute(
                    "INSERT INTO session_state (session_id, in_seq_num, out_seq_num) VALUES (?, 1, 1)",
                    (session_id,)
                )
                await db.commit()
                return 1, 1

async def update_session_state(in_seq: int, out_seq: int, session_id: str = "DEFAULT_SESSION"):
    """Persist updated sequence numbers after every message sent/received."""
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute(
            """UPDATE session_state 
               SET in_seq_num = ?, out_seq_num = ?, last_updated = CURRENT_TIMESTAMP 
               WHERE session_id = ?""",
            (in_seq, out_seq, session_id)
        )
        await db.commit()

async def persist_order_status(order_id: str, cl_ord_id: str, symbol: str, side: str, price: float, qty: float, status: str, filled_qty: float = 0.0):
    """Save or update order state in the database."""
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute(
            """INSERT INTO orders (order_id, cl_ord_id, symbol, side, price, quantity, status, filled_qty)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)
               ON CONFLICT(order_id) DO UPDATE SET
               status = excluded.status,
               filled_qty = excluded.filled_qty""",
            (order_id, cl_ord_id, symbol, side, price, qty, status, filled_qty)
        )
        await db.commit()
