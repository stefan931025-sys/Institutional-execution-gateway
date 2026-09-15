import asyncio
import logging
from fix_socket_client import FixSocketClient

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger(__name__)

async def main():
    # Configuration parameters for your FIX endpoint / sandbox
    HOST = "127.0.0.1"  # Replace with sandbox/broker endpoint
    PORT = 9800         # Replace with target port
    SENDER = "MY_FIRM_TRADER"
    TARGET = "EXCHANGE_M"

    client = FixSocketClient(HOST, PORT, SENDER, TARGET)

    # 1. Connect and initialize session state from database
    await client.connect()

    if not client.is_connected:
        logger.error("Failed to establish FIX connection and logon. Exiting.")
        return

    # 2. Start background tasks (listening for fills & sending heartbeats)
    listen_task = asyncio.create_task(client.listen_loop())
    heartbeat_task = asyncio.create_task(client.start_heartbeat_loop(30))

    try:
        # Example: Send a test order after a short pause
        await asyncio.sleep(2)
        await client.send_order(
            symbol="UK-POWER-SPOT", 
            side="1", 
            order_qty=10.0, 
            price=65.50, 
            cl_ord_id="ORD-2026-001"
        )

        # Keep running and wait for tasks
        await asyncio.gather(listen_task, heartbeat_task)
        
    except asyncio.CancelledError:
        logger.info("Gateway shutting down...")
    finally:
        # Ensure background tasks are cleanly cancelled if an error occurs
        listen_task.cancel()
        heartbeat_task.cancel()
        logger.info("Gateway stopped.")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Gateway stopped manually by user.")
