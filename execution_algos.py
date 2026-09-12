import asyncio
import logging
from typing import AsyncGenerator

logger = logging.getLogger("ExecutionAlgos")

class IcebergSlicer:
    """Splits large parent orders into smaller hidden child slices for execution."""
    def __init__(self, total_volume: float, slice_size: float, interval_seconds: float = 1.0):
        self.total_volume = total_volume
        self.slice_size = slice_size
        self.interval_seconds = interval_seconds
        self.executed_volume = 0.0

    async def slice_order(self) -> AsyncGenerator[float, None]:
        """Async generator yielding individual child order slice sizes over time."""
        logger.info(f"Initializing Iceberg slice execution: Total={self.total_volume}MW, Slice={self.slice_size}MW")
        
        while self.executed_volume < self.total_volume:
            remaining = self.total_volume - self.executed_volume
            current_slice = min(self.slice_size, remaining)
            
            yield current_slice
            self.executed_volume += current_slice
            
            if self.executed_volume < self.total_volume:
                await asyncio.sleep(self.interval_seconds)
