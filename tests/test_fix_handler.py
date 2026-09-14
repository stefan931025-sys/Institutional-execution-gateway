import pytest
from fix_handler import FIXHandler

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
    assert checksum == "220"

def test_sequence_gap_and_resend(fix_client):
    """Simulate a dropped packet sequence and verify gap-fill resend handling."""
    fix_client.inbound_seq = 10
    incoming_msg_seq = 15  # Gap detected (expected 11)

    gap_detected = fix_client.check_sequence_gap(incoming_msg_seq)
    assert gap_detected is True, "Engine should flag a sequence gap."

    resend_request = fix_client.generate_resend_request(begin_seq=11, end_seq=14)
    assert "35=2" in resend_request, "Resend Request (MsgType 2) should be generated."
