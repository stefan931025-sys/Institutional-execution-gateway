import asyncio
import logging
from metrics import RISK_REJECTIONS_COUNTER
from fix_handler import FIXHandler
from multileg_router import MultiLegRouter

logger = logging.getLogger("InstitutionalGateway")

class RiskLimits:
    """Defines pre-trade risk boundaries with flexible keyword argument support."""
    def __init__(self, **kwargs):
        self.max_order_size = kwargs.get("max_order_size", kwargs.get("max_order_size_mw", 1000.0))
        self.max_notional = kwargs.get("max_notional", 100000.0)


class PreTradeRiskEngine:
    """Validates orders against pre-trade risk limits before transmission."""
    def __init__(self, limits: RiskLimits):
        self.limits = limits

    def validate_order(self, *args, **kwargs):
        """Validates order parameters and returns a tuple: (approved: bool, reason: str)."""
        qty = 1.0
        price = 1.0

        if len(args) > 0 and isinstance(args[0], (int, float)):
            qty = float(args[0])
        if len(args) > 1 and isinstance(args[1], (int, float)):
            price = float(args[1])

        if "mw_size" in kwargs:
            qty = float(kwargs["mw_size"])
        if "qty" in kwargs:
            qty = float(kwargs["qty"])
        if "price" in kwargs:
            price = float(kwargs["price"])

        notional = qty * price
        if qty > self.limits.max_order_size:
            reason = "exceeds size limit"
            logger.warning(f"Risk Check Failed: Quantity {qty} exceeds max limit {self.limits.max_order_size}")
            RISK_REJECTIONS_COUNTER.labels(reason=reason).inc()
            return False, reason
            
        if notional > self.limits.max_notional:
            reason = "exceeds notional limit"
            logger.warning(f"Risk Check Failed: Notional {notional} exceeds max limit {self.limits.max_notional}")
            RISK_REJECTIONS_COUNTER.labels(reason=reason).inc()
            return False, reason
            
        return True, ""


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
        approved, reason = self.risk_engine.validate_order(qty, price=price)
        if not approved:
            raise ValueError(f"Order {cl_ord_id} rejected by PreTradeRiskEngine: {reason}")

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
