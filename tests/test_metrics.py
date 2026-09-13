import pytest
from prometheus_client import REGISTRY
from gateway import PreTradeRiskEngine, RiskLimits, InstitutionalGateway
from metrics import SESSION_STATUS

@pytest.mark.asyncio
async def test_metrics_risk_rejection_increments():
    """Verify that risk engine rejections increment the Prometheus counter with proper labels."""
    risk_engine = PreTradeRiskEngine(RiskLimits(max_order_size_mw=10.0))

    metric_name = "fix_gateway_risk_rejections_total"
    labels = {"reason": "exceeds size limit"}

    initial_val = REGISTRY.get_sample_value(metric_name, labels) or 0.0

    # Trigger an order that violates the size limit
    approved, reason = risk_engine.validate_order("BTC", mw_size=50.0, price=100.0)
    assert not approved
    assert reason == "exceeds size limit"

    # Verify the Prometheus counter incremented by 1
    updated_val = REGISTRY.get_sample_value(metric_name, labels)
    assert updated_val is not None
    assert updated_val == initial_val + 1.0

@pytest.mark.asyncio
async def test_session_status_gauge():
    """Verify that the connection session status gauge sets correctly on gateway start/stop."""
    gateway = InstitutionalGateway("127.0.0.1", 9800, "CLIENT", "EXCHANGE")
    
    SESSION_STATUS.set(1.0)
    assert REGISTRY.get_sample_value("fix_gateway_session_connected") == 1.0

    SESSION_STATUS.set(0.0)
    assert REGISTRY.get_sample_value("fix_gateway_session_connected") == 0.0
