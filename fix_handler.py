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
    sample_msg = "8=FIX.4.2\x019=12\x0135=0\x01"
    checksum = fix_client._calculate_checksum(sample_msg)
    assert len(checksum) == 3
    assert checksum.isdigit()
    assert checksum == "207"  # Updated to match the correct modulo 256 sum for the sample string

def test_parse_message(fix_client):
    """Verify that incoming SOH-delimited messages are parsed into tag-value dicts."""
    raw_msg = "8=FIX.4.2\x019=55\x0135=0\x0149=EXCHANGE_SIM\x0156=CLIENT_SIM\x0134=42\x0152=20260101-00:00:00.000\x0110=123\x01"
    parsed = fix_client.parse_message(raw_msg)
    
    assert parsed[8] == "FIX.4.2"
    assert parsed[35] == "0"
    assert parsed[49] == "EXCHANGE_SIM"
    assert parsed[34] == "42"
