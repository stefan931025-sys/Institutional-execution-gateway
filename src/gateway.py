import asyncio
import logging
from fix_handler import FIXHandler
from multileg_router import MultiLegRouter

logger = logging.getLogger("InstitutionalGateway")

class InstitutionalGateway:
    """
    Main institutional gateway class handling connection lifecycle,
    single-order execution, risk checks, and automated multi-leg spread routing.
    """
    
    def __init__(self, host: str, port: int, sender_comp_id: str, target_comp_id: str, store_path: str = "session_store.json"):
        self.host = host
        self.port = port
        self.sender_comp_id = sender_comp_id
        self.target_comp_id = target_comp_id
        self.store_path = store_path

        # Initialize core FIX protocol message handler
        self.fix_handler = FIXHandler(
            host=self.host,
            port=self.port,
            sender_comp_id=self.sender_comp_id,
            target_comp_id=self.target_comp_id,
            store_path=self.store_path
        )

        # Initialize the multi-leg router to eliminate leg-risk on spreads
        self.multileg_router = MultiLegRouter(self.fix_handler)

    async def start(self):
        """Establish asynchronous TCP connection and log into the exchange FIX session."""
        logger.info(f"Starting Institutional Gateway connecting to {self.host}:{self.port}...")
        await self.fix_handler.connect()
        logger.info("Gateway session successfully established and active.")

    async def stop(self):
        """Cleanly close the FIX session and underlying socket connection."""
        logger.info("Shutting down Institutional Gateway...")
        await self.fix_handler.close()
        logger.info("Gateway successfully shut down.")

    async def submit_order(self, cl_ord_id: str, symbol: str, side: str, qty: float, price: float):
        """Submit a standard single-leg order through the FIX handler."""
        logger.info(f"Submitting single order [{cl_ord_id}]: {side} {qty} {symbol} @ {price}")
        await self.fix_handler.send_order(
            cl_ord_id=cl_ord_id,
            symbol=symbol,
            side=side,
            qty=qty,
            price=price
        )

    async def execute_spread_order(self, spread_id: str, leg1: dict, leg2: dict):
        """
        Execute a synthetic multi-leg order (spread). 
        Fires Leg 1, waits for fill confirmation, and immediately triggers Leg 2 
        to eliminate manual intervention lag and market slippage.
        """
        logger.info(f"Initiating multi-leg spread execution [{spread_id}]")
        await self.multileg_router.execute_spread(spread_id, leg1, leg2)
