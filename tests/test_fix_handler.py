import pytest
import asyncio
import time
from fix_handler import FIXHandler, DurableSequenceStore
from gateway import PreTradeRiskEngine, RiskLimits

@pytest.fixture
def fix_client():
    return FIXHandler(
        host="127.0.0.1",
        port=9800,
        sender_comp_id="CLIENT_SIM",
        target_comp_id="EXCHANGE_SIM"
    )

def test_checksum_calculation(fix_client):
    """Verify that FIX checksum calculation generates a valid 3-digit numeric string."""
    sample_msg = "8=FIX.4.2\x019=55\x0135=D\x0134=1\x0149=EXCHANGE_SIM\x0156=CLIENT_SIM\x0111=123\x01"
    checksum = fix_client.calculate_checksum(sample_msg)
    assert len(checksum) == 3
    assert checksum.isdigit()
    assert checksum == "207"

def test_parse_message(fix_client):
    """Verify that incoming SOH-delimited messages are parsed into tag-value dicts."""
    raw_msg = "8=FIX.4.2\x019=55\x0135=D\x0149=EXCHANGE_SIM\x0156=CLIENT_SIM\x0134=42\x0152=20260101-00:00:00.000\x01110=123\x01"
    parsed = fix_client.parse_message(raw_msg)

    assert parsed["8"] == "FIX.4.2"
    assert parsed["35"] == "D"
    assert parsed["49"] == "EXCHANGE_SIM"
    assert parsed["34"] == "42"

# --- Institutional Resilience & Sequence Gap Tests ---

def test_sequence_gap_and_resend(fix_client):
    """Simulate a dropped packet sequence and verify gap-fill resend handling."""
    fix_client.inbound_seq = 10
    incoming_msg_seq = 15  # Gap detected (expected 11)

    gap_detected = fix_client.check_sequence_gap(incoming_msg_seq)
    assert gap_detected is True, "Engine should flag a sequence gap."

    resend_request = fix_client.generate_resend_request(begin_seq=11, end_seq=14)
    assert "MsgType=2" in resend_request, "Resend Request (MsgType 2) should be generated."
    assert "BeginSeqNo=11" in resend_request
    assert "EndSeqNo=14" in resend_request

def test_durable_persistence_reload(tmp_path):
    """Test state survival and recovery through the durable sequence store."""
    db_path = tmp_path / "test_session_store.json"
    store = DurableSequenceStore(storage_path=str(db_path))

    # Save active session sequences
    store.save_sequences(inbound=42, outbound=55)

    # Initialize a new store instance pointing to the same file to verify persistence
    new_store = DurableSequenceStore(storage_path=str(db_path))
    inbound, outbound = new_store.load_sequences()

    assert inbound == 42
    assert outbound == 55, "Durable state must persist across restarts."

# --- NEW: Pre-Trade Risk Control Tests ---

def test_risk_engine_valid_order():
    """Verifies that a normal, compliant order passes all risk gates."""
    limits = RiskLimits(max_order_size_mw=50.0, max_notional_value=100000.0, max_messages_per_second=5)
    engine = PreTradeRiskEngine(limits)
    
    approved, reason = engine.validate_order("EPEX-GB-PEAK", 10.0, 65.0)
    assert approved is True
    assert reason == "APPROVED"

def test_risk_engine_exceeds_size_limit():
    """Ensures orders larger than the maximum MW volume slice are rejected."""
    limits = RiskLimits(max_order_size_mw=50.0, max_notional_value=1000000.0)
    engine = PreTradeRiskEngine(limits)
    
    approved, reason = engine.validate_order("EPEX-GB-PEAK", 55.0, 65.0)
    assert approved is False
    assert "exceeds limit" in reason

def test_risk_engine_exceeds_notional_value():
    """Ensures orders exceeding the max monetary notional value are blocked."""
    limits = RiskLimits(max_order_size_mw=100.0, max_notional_value=10000.0)
    engine = PreTradeRiskEngine(limits)
    
    approved, reason = engine.validate_order("EPEX-GB-PEAK", 10.0, 2000.0)
    assert approved is False
    assert "Notional" in reason

def test_risk_engine_kill_switch_engagement():
    """Verifies that engaging the master kill switch instantly rejects all traffic."""
    limits = RiskLimits()
    engine = PreTradeRiskEngine(limits)
    
    engine.engage_kill_switch()
    approved, reason = engine.validate_order("EPEX-GB-PEAK", 5.0, 65.0)
    
    assert approved is False
    assert "Kill Switch" in reason

def test_risk_engine_velocity_rate_limiting():
    """Tests that rapid message floods trigger velocity blocks."""
    limits = RiskLimits(max_order_size_mw=50.0, max_notional_value=100000.0, max_messages_per_second=2)
    engine = PreTradeRiskEngine(limits)
    
    assert engine.validate_order("EPEX-GB-PEAK", 1.0, 10.0)[0] is True
    assert engine.validate_order("EPEX-GB-PEAK", 1.0, 10.0)[0] is True
    
    approved, reason = engine.validate_order("EPEX-GB-PEAK", 1.0, 10.0)
    assert approved is False
    assert "rate limit" in reason.lower()

# --- Performance Profiling Test ---

@pytest.mark.asyncio
async def test_gateway_throughput_benchmark(fix_client):
    """Benchmark parsing throughput to prove low-latency capabilities for hiring managers."""
    iterations = 1000
    start_time = time.perf_counter()

    for _ in range(iterations):
        raw_msg = "8=FIX.4.2\x019=55\x0135=D\x0134=1\x0149=EXCHANGE_SIM\x0156=CLIENT_SIM\x01110=123\x01"
        fix_client.parse_message(raw_msg)

    duration = time.perf_counter() - start_time
    msgs_per_sec = iterations / duration

    # Assert a minimum performance threshold (> 5,000 msgs/sec)
    assert msgs_per_sec > 5000, "Throughput too low."
    print(f"\n[BENCHMARK] Processed {iterations} messages in {duration:.4f}s ({msgs_per_sec:.2f} msgs/sec)")
