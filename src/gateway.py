import asyncio
import logging
import time
from typing import Tuple
from fix_handler import FIXHandler
from metrics import RISK_REJECTIONS_TOTAL, ORDERS_SENT_TOTAL, SESSION_STATUS, ROUNDTRIP_LATENCY_SECONDS

logger = logging.getLogger("InstitutionalGateway")

class RiskError(Exception):
    """Raised when an order breaches pre-trade risk boundaries."""
    pass

class RiskLimits:
    def __init__(self, max_order_size_mw: float = 50.0, max_notional_value: float = 100000.0, max_messages_per_second: int = 5):
        self.max_order_size_mw = max_order_size_mw
        self.max_notional_value = max_notional_value
        self.max_messages_per_second = max_messages_per_second

class PreTradeRiskEngine:
    def __init__(self, limits: RiskLimits = None):
        self.limits = limits or RiskLimits()
        self.kill_switch = False
        self.message_timestamps = []

    def engage_kill_switch(self):
        self.kill_switch = True
        logger.critical("MASTER KILL SWITCH ENGAGED.")

    def validate_order(self, symbol: str, mw_size: float, price: float) -> Tuple[bool, str]:
        if self.kill_switch:
            reason = "Kill Switch Engaged"
            RISK_REJECTIONS_TOTAL.labels(reason=reason).inc()
            return False, reason

        # Velocity rate-limiting check
        now = time.time()
        self.message_timestamps = [ts for ts in self.message_timestamps if now - ts < 1.0]
        if len(self.message_timestamps) >= self.limits.max_messages_per_second:
            reason = "Rate limit exceeded"
            RISK_REJECTIONS_TOTAL.labels(reason=reason).inc()
            return False, reason
        self.message_timestamps.append(now)

        if mw_size > self.limits.max_order_size_mw:
            reason = "exceeds size limit"
            RISK_REJECTIONS_TOTAL.labels(reason=reason).inc()
            return False, f"{reason}: size {mw_size} > max {self.limits.max_order_size_mw}"

        notional = mw_size * price
        if notional > self.limits.max_notional_value:
            reason = "exceeds notional limit"
            RISK_REJECTIONS_TOTAL.labels(reason=reason).inc()
            return False, f"Notional value {notional} exceeds limit {self.limits.max_notional_value}"

        return True, "APPROVED"

class InstitutionalGateway:
    def __init__(self, host: str, port: int, sender_comp_id: str, target_comp_id: str):
        self.fix_handler = FIXHandler(host, port, sender_comp_id, target_comp_id)
        self.risk_engine = PreTradeRiskEngine()

    async def start(self):
        await self.fix_handler.connect()
        SESSION_STATUS.set(1.0)

    async def submit_order(self, cl_ord_id: str, symbol: str, side: str, qty: float, price: float):
        start_time = time.time()
        approved, reason = self.risk_engine.validate_order(symbol, qty, price)
        if not approved:
            logger.error(f"Order rejected by risk engine: {reason}")
            return
            
        await self.fix_handler.send_order(cl_ord_id, symbol, side, qty, price)
        ORDERS_SENT_TOTAL.labels(symbol=symbol, side=side).inc()
        
        duration = time.time() - start_time
        ROUNDTRIP_LATENCY_SECONDS.observe(duration)

    async def stop(self):
        SESSION_STATUS.set(0.0)
        await self.fix_handler.close()
