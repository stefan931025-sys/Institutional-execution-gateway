import asyncio
import logging
from typing import Tuple
from fix_handler import FIXHandler

logger = logging.getLogger("InstitutionalGateway")

class RiskError(Exception):
    """Raised when an order breaches pre-trade risk boundaries."""
    pass

class RiskLimits:
    """Defines structural risk thresholds for pre-trade controls."""
    def __init__(self, max_order_size_mw: float = 50.0, max_notional_value: float = 100000.0, max_messages_per_second: int = 5):
        self.max_order_size_mw = max_order_size_mw
        self.max_notional_value = max_notional_value
        self.max_messages_per_second = max_messages_per_second

class PreTradeRiskEngine:
    """Enforces real-time pre-trade risk checks, rate-limiting, and kill switch logic."""
    def __init__(self, limits: RiskLimits = None):
        self.limits = limits or RiskLimits()
        self.kill_switch = False
        self.message_timestamps = []

    def engage_kill_switch(self):
        """Engages the emergency master kill switch."""
        self.kill_switch = True
        logger.critical("MASTER KILL SWITCH ENGAGED.")

    def validate_order(self, symbol: str, mw_size: float, price: float) -> Tuple[bool, str]:
        """Validates incoming orders against risk limits and returns (approved, reason)."""
        if self.kill_switch:
            return False, "Kill Switch Engaged"

        if mw_size > self.limits.max_order_size_mw:
            return False, f"Exceeds limit: size {mw_size} > max {self.limits.max_order_size_mw}"

        notional = mw_size * price
        if notional > self.limits.max_notional_value:
            return False, f"Notional value {notional} exceeds limit {self.limits.max_notional_value}"

        # Velocity check (messages per second)
        current_time = asyncio.get_event_loop().time() if asyncio.get_event_loop().is_running() else 0
        # Simple count-based rate check mock for testing
        if len(self.message_timestamps) >= self.limits.max_messages_per_second:
            return False, "Rate limit exceeded"
        
        self.message_timestamps.append(current_time)
        return True, "APPROVED"

class InstitutionalGateway:
    """Orchestrates low-latency connectivity, pre-trade risk compliance, and execution routing."""
    def __init__(self, host: str, port: int, sender_comp_id: str, target_comp_id: str):
        self.fix_handler = FIXHandler(host, port, sender_comp_id, target_comp_id)
        self.risk_engine = PreTradeRiskEngine()

    async def start(self):
        await self.fix_handler.connect()

    async def submit_order(self, cl_ord_id: str, symbol: str, side: str, qty: float, price: float):
        approved, reason = self.risk_engine.validate_order(symbol, qty, price)
        if not approved:
            logger.error(f"Order rejected by risk engine: {reason}")
            return
        await self.fix_handler.send_order(cl_ord_id, symbol, side, qty, price)

    async def stop(self):
        await self.fix_handler.close()
