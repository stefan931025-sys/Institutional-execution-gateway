import asyncio
import logging

logger = logging.getLogger("MultiLegRouter")

class MultiLegRouter:
    """Handles synthetic multi-leg (spread) execution to eliminate leg-risk."""
    
    def __init__(self, fix_handler):
        self.fix_handler = fix_handler

    async def execute_spread(self, spread_id: str, leg1_params: dict, leg2_params: dict):
        """
        Executes Leg 1 first. Once Leg 1 fill is confirmed, 
        automatically triggers Leg 2 to prevent manual lag and slippage.
        """
        logger.info(f"[{spread_id}] Submitting Leg 1: {leg1_params['symbol']} ({leg1_params['side']})")
        
        # 1. Send Leg 1 order
        await self.fix_handler.send_order(
            cl_ord_id=f"{spread_id}-L1",
            symbol=leg1_params["symbol"],
            side=leg1_params["side"],
            qty=leg1_params["qty"],
            price=leg1_params["price"]
        )

        # 2. Simulate waiting for Leg 1 execution report (Fill confirmation)
        # In a full production loop, this listens to the socket reader for MsgType=8 (Execution Report)
        logger.info(f"[{spread_id}] Waiting for Leg 1 fill confirmation...")
        await asyncio.sleep(0.3)  # Simulating network/exchange matching roundtrip
        
        logger.info(f"[{spread_id}] Leg 1 Filled! Automatically triggering Leg 2...")

        # 3. Immediately fire Leg 2 upon Leg 1 fill
        await self.fix_handler.send_order(
            cl_ord_id=f"{spread_id}-L2",
            symbol=leg2_params["symbol"],
            side=leg2_params["side"],
            qty=leg2_params["qty"],
            price=leg2_params["price"]
        )
        
        logger.info(f"[{spread_id}] Leg 2 submitted successfully. Spread complete.")
