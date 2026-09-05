import asyncio
import json
import logging
from dataclasses import dataclass, field
from typing import Dict, List, Any

# Configure logging for millisecond-level telemetry tracking
logging.basicConfig(level=logging.INFO, format="%(asctime)s.%(msecs)03d [%(levelname)s] %(message)s", datefmt="%H:%M:%S")
logger = logging.getLogger("ExecutionGateway")

@dataclass
class LegOrder:
    leg_id: str
    contract: str
    target_volume: int
    limit_price: float
    filled_volume: int = 0
    status: str = "PENDING"

@dataclass
class SpreadStrategyConfig:
    strategy_id: str
    max_allowable_spread: float
    emergency_slice_size_mw: int
    legs: List[LegOrder] = field(default_factory=list)

class InstitutionalExecutionGateway:
    def __init__(self, config_path: str):
        self.config = self.load_configuration(config_path)
        self.is_connected = False

    def load_configuration(self, path: str) -> SpreadStrategyConfig:
        """Loads firm-specific execution parameters from configuration file."""
        logger.info(f"Loading execution configuration from {path}...")
        with open(path, "r") as f:
            data = json.load(f)
        
        legs = [
            LegOrder(
                leg_id=leg["leg_id"],
                contract=leg["contract"],
                target_volume=leg["target_volume"],
                limit_price=leg["limit_price"]
            ) for leg in data["legs"]
        ]
        
        return SpreadStrategyConfig(
            strategy_id=data["strategy_id"],
            max_allowable_spread=data["max_allowable_spread"],
            emergency_slice_size_mw=data["emergency_slice_size_mw"],
            legs=legs
        )

    async def handle_partial_fill(self, leg_id: str, executed_vol: int, execution_price: float):
        """
        Triggered instantaneously upon leg execution to recalculate exposure 
        and prevent manual re-pricing delays during system shocks.
        """
        target_leg = next((l for l in self.config.legs if l.leg_id == leg_id), None)
        if not target_leg:
            logger.error(f"Leg {leg_id} not recognized under active configuration.")
            return

        target_leg.filled_volume += executed_vol
        target_leg.status = "FILLED" if target_leg.filled_volume >= target_leg.target_volume else "PARTIAL"
        
        logger.info(f"FILL DETECTED [{leg_id}]: {executed_vol}MW matched at £{execution_price:.2f}. Status: {target_leg.status}")

        # Immediately execute automated risk-offsetting routine
        await self.rebalance_legs(trigger_leg_id=leg_id, filled_delta=executed_vol)

    async def rebalance_legs(self, trigger_leg_id: str, filled_delta: int):
        """Neutralizes leg-risk by aggressively crossing the spread on offsetting contracts."""
        logger.warning(f"Imbalance detected from {trigger_leg_id}. Dispatching automated defensive hedge...")

        for leg in self.config.legs:
            if leg.leg_id != trigger_leg_id and leg.status != "FILLED":
                aggressive_price = leg.limit_price + 0.50  # Cross spread to ensure immediate execution
                logger.info(f"HEDGING ACTION [{leg.leg_id}]: Adjusting size for {filled_delta}MW delta @ Target £{aggressive_price:.2f}")
                
                await asyncio.sleep(0.001)  # Simulate ultra-low latency API drop-copy roundtrip
                leg.status = "FILLED"
                logger.info(f"Offsetting leg {leg.leg_id} successfully secured. Leg-risk neutralized.")

    async def run_simulation(self):
        self.is_connected = True
        logger.info(f"Gateway live for strategy: {self.config.strategy_id}. Monitoring order books...")
        
        # Simulate an asynchronous fill event triggered by an interconnector shock
        await asyncio.sleep(0.5)
        await self.handle_partial_fill(leg_id="LEG_SPOT_BUY", executed_vol=self.config.emergency_slice_size_mw, execution_price=66.25)

if __name__ == "__main__":
    gateway = InstitutionalExecutionGateway("config.json")
    asyncio.run(gateway.run_simulation())
