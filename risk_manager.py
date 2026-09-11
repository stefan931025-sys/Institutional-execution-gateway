import time
import logging
from dataclasses import dataclass

logger = logging.getLogger("PreTradeRiskManager")

@dataclass
class RiskLimits:
    max_order_size_mw: float = 50.0
    max_notional_value: float = 250000.0  # e.g., in GBP
    max_messages_per_second: int = 10     # Rate limit to prevent spamming
    kill_switch_active: bool = False

class PreTradeRiskEngine:
    def __init__(self, limits: RiskLimits):
        self.limits = limits
        self._message_timestamps = []

    def validate_order(self, symbol: str, volume: float, price: float) -> tuple[bool, str]:
        """
        Validates an outbound order against pre-trade risk checks.
        Returns (is_approved: bool, reason: str)
        """
        # 1. Check Master Kill Switch
        if self.limits.kill_switch_active:
            return False, "REJECTED: Master Kill Switch is actively engaged."

        # 2. Check Order Size (Volume Limit)
        if volume <= 0:
            return False, f"REJECTED: Invalid order volume ({volume}). Must be > 0."
        if volume > self.limits.max_order_size_mw:
            return False, f"REJECTED: Order volume {volume}MW exceeds max limit of {self.limits.max_order_size_mw}MW."

        # 3. Check Notional Exposure
        notional = volume * price
        if notional > self.limits.max_notional_value:
            return False, f"REJECTED: Order notional £{notional:,.2f} exceeds max limit of £{self.limits.max_notional_value:,.2f}."

        # 4. Check Message Rate (Velocity Check / Throttling)
        now = time.time()
        # Prune timestamps older than 1 second
        self._message_timestamps = [t for t in self._message_timestamps if now - t < 1.0]
        
        if len(self._message_timestamps) >= self.limits.max_messages_per_second:
            return False, f"REJECTED: Rate limit hit. Exceeded {self.limits.max_messages_per_second} msgs/sec."

        # Record message timestamp for valid dispatch attempt
        self._message_timestamps.append(now)
        return True, "APPROVED"

    def engage_kill_switch(self):
        """Instantly activates the master emergency kill switch."""
        self.limits.kill_switch_active = True
        logger.critical("MASTER KILL SWITCH ENGAGED. All subsequent outbound orders will be blocked.")
