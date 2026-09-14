import asyncio
import logging

logger = logging.getLogger("InstitutionalGateway")

class MultiLegRouter:
    def __init__(self, fix_handler, timeout_seconds=1.0, max_retries=2):
        self.fix_handler = fix_handler
        self.timeout_seconds = timeout_seconds
        self.max_retries = max_retries

    async def execute_spread(self, leg1_order: dict, leg2_order: dict) -> dict:
        """
        Executes Leg 1, and upon fill, aggressively routes Leg 2 with built-in 
        timeout and failure fallback mechanisms to eliminate naked leg exposure.
        """
        logger.info(f"Routing Leg 1: {leg1_order['symbol']} Qty: {leg1_order['qty']}")
        leg1_status = await self.fix_handler.send_order(leg1_order)

        if not leg1_status or leg1_status.get("status") != "FILLED":
            logger.error("Leg 1 failed or rejected. Aborting spread execution.")
            return {"status": "REJECTED", "reason": "Leg 1 execution failed"}

        logger.info("Leg 1 filled successfully. Routing Leg 2 with strict timeout...")
        
        retries = 0
        leg2_status = None

        while retries < self.max_retries:
            try:
                # Wrap Leg 2 execution in an asyncio timeout to prevent hanging on network lags
                leg2_status = await asyncio.wait_for(
                    self.fix_handler.send_order(leg2_order), 
                    timeout=self.timeout_seconds
                )
                if leg2_status and leg2_status.get("status") == "FILLED":
                    logger.info("Leg 2 filled successfully. Spread complete.")
                    return {"status": "FILLED", "leg1": leg1_status, "leg2": leg2_status}
            except asyncio.TimeoutError:
                retries += 1
                logger.warning(f"Leg 2 timed out (Attempt {retries}/{self.max_retries}). Retrying...")

        # Critical Fallback: If Leg 2 repeatedly fails after Leg 1 is filled
        logger.critical("CRITICAL: Leg 2 failed after max retries while Leg 1 is filled! Initiating emergency mitigation.")
        mitigation_result = await self._handle_naked_leg(leg1_order)
        
        return {
            "status": "PARTIAL_FILL_RISK", 
            "reason": "Leg 2 timeout/failure", 
            "mitigation": mitigation_result
        }

    async def _handle_naked_leg(self, original_leg1: dict) -> str:
        """Emergency offsetting order or alert trigger for unhedged legs."""
        # In a real desk setup, this would fire an immediate counter-order or page risk managers
        logger.error("Executing emergency flattening order for Leg 1 position.")
        flatten_order = original_leg1.copy()
        flatten_order["qty"] = -flatten_order["qty"] # Reverse direction to flatten
        await self.fix_handler.send_order(flatten_order)
        return "FLATTENED"
