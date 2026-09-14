import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock
from multileg_router import MultiLegRouter

@pytest.mark.asyncio
async def test_multileg_router_success():
    mock_fix = AsyncMock()
    # Mock both legs filling successfully
    mock_fix.send_order.side_effect = [{"status": "FILLED"}, {"status": "FILLED"}]

    router = MultiLegRouter(mock_fix, timeout_seconds=1.0, max_retries=1)
    
    leg1 = {"symbol": "ELEC_PEAK_L", "qty": 10.0, "price": 50.0}
    leg2 = {"symbol": "ELEC_PEAK_S", "qty": 10.0, "price": 48.0}

    result = await router.execute_spread(leg1, leg2)
    
    assert result["status"] == "FILLED"
    assert mock_fix.send_order.call_count == 2

@pytest.mark.asyncio
async def test_multileg_router_leg1_fails():
    mock_fix = AsyncMock()
    # Leg 1 gets rejected
    mock_fix.send_order.return_value = {"status": "REJECTED"}

    router = MultiLegRouter(mock_fix)
    
    leg1 = {"symbol": "ELEC_PEAK_L", "qty": 10.0, "price": 50.0}
    leg2 = {"symbol": "ELEC_PEAK_S", "qty": 10.0, "price": 48.0}

    result = await router.execute_spread(leg1, leg2)
    
    assert result["status"] == "REJECTED"
    # Should not attempt Leg 2 if Leg 1 failed
    assert mock_fix.send_order.call_count == 1
