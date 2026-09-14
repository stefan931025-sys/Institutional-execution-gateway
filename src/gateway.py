import asyncio
import logging
from fix_handler import FIXHandler
from multileg_router import MultiLegRouter

logger = logging.getLogger("InstitutionalGateway")

class RiskLimits:
    """Defines pre-trade risk boundaries."""
    def __init__(self, max_order_qty: float = 1000.0, max_notional: float = 100000.0):
        self.max_order_qty = max_order_qty
        self.max_notional = max_notional


class PreTradeRiskEngine:
    """Validates orders against pre-trade risk limits before transmission."""
    def __init__(self, limits: RiskLimits):
        self.limits = limits

    def validate_order(self, qty: float, price: float) -> bool:
        notional = qty * price
        if qty > self.limits.max_order_qty:
            logger.warning(f"Risk Check Failed: Quantity {qty} exceeds max limit {self.limits.max_order_qty}")
            return False
        if notional > self.limits.max_notional:
            logger.warning(f"Risk Check Failed: Notional {notional} exceeds max limit {self.limits.max_notional}")
            return False
        return True


class InstitutionalGateway:
    """
    Main institutional gateway class handling connection lifecycle,
    pre-trade risk checks, single-order execution, and automated multi-leg spread routing.
    """
    
    def __init__(self, host: str, port: int, sender_comp_id: str, target_comp_id: str, store_path: str = "session_store.json"):
        self.host = host
        self.port = port
        self.sender_comp_id = sender_comp_id
        self.target_comp_id = target_comp_id
        self.store_path = store_path

        # Initialize risk management
        self.risk_limits = RiskLimits()
        self.risk_engine = PreTradeRiskEngine(self.risk_limits)

        # Initialize core FIX protocol message handler
        self.fix_handler = FIXHandler(
            host=self.host,
            port=self.port,
            sender_comp_id=self.sender_comp_id,
            target_comp_id=self.target_comp_id,
            store_path=self.store_path
        )

        # Initialize multi-leg spread router
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
        """Run pre-trade risk validation and submit standard single-leg order if approved."""
        if not self.risk_engine.validate_order(qty, price):
            raise ValueError(f"Order {cl_ord_id} rejected by PreTradeRiskEngine.")

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
