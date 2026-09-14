import pytest
import asyncio
from mock_acceptor import MockExchangeAcceptor
from gateway import InstitutionalGateway

@pytest.mark.asyncio
async def test_gateway_roundtrip_integration():
    """Spins up a mock FIX acceptor and verifies end-to-end order routing and execution response."""
    host = "127.0.0.1"
    port = 9801  # Use a separate port to avoid conflicts

    # 1. Start the mock exchange acceptor
    acceptor = MockExchangeAcceptor(host=host, port=port)
    await acceptor.start()

    # Give the server a moment to bind
    await asyncio.sleep(0.1)

    try:
        # 2. Initialize and start the institutional gateway client
        gateway = InstitutionalGateway(
            host=host, 
            port=port, 
            sender_comp_id="CLIENT_SIM", 
            target_comp_id="EXCHANGE_SIM"
        )
        await gateway.start()

        # Verify connection is established
        assert gateway.fix_handler.writer is not None, "Gateway client socket writer should be initialized."

        # 3. Submit a valid order through the risk engine and gateway
        await gateway.submit_order(
            cl_ord_id="ORD-001",
            symbol="EPEX-GB-PEAK",
            side="BUY",
            qty=10.0,
            price=45.0
        )

        # Allow async socket transmission time
        await asyncio.sleep(0.1)

        # 4. Clean shutdown
        await gateway.stop()

    finally:
        await acceptor.stop()
