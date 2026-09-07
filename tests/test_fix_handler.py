import pytest
import os
import json
from fix_handler import FIXHandler

@pytest.fixture
def fix_client():
    state_file = "test_fix_state.json"
    handler = FIXHandler(
        host="127.0.0.1",
        port=9800,
        sender_comp_id="TEST_SENDER",
        target_comp_id="TEST_TARGET",
        state_file=state_file
    )
    yield handler
    # Cleanup test state file after execution
    if os.path.exists(state_file):
        os.remove(state_file)

def test_checksum_calculation(fix_client):
    """Verify that FIX checksum calculation generates a valid 3-digit numeric string."""
    sample_msg = "8=FIX.4.2\x019=12\x0135=0\x01"
    checksum = fix_client._calculate_checksum(sample_msg)
    assert len(checksum) == 3
    assert checksum.isdigit()
    assert checksum == "156"  # Expected modulo 256 checksum for the sample string

def test_message_building_and_sequencing(fix_client):
    """Verify message framing, sequence incrementing, and state persistence properties."""
    initial_seq = fix_client.out_seq_num
    msg_bytes = fix_client.build_message("0", {})
    
    assert isinstance(msg_bytes, bytes)
    assert b"35=0" in msg_bytes
    assert f"34={initial_seq}".encode("ascii") in msg_bytes
    
    # Verify outbound sequence incremented properly
    assert fix_client.out_seq_num == initial_seq + 1

def test_parse_message(fix_client):
    """Verify that raw SOH-delimited strings are parsed correctly into dictionaries."""
    raw_str = "8=FIX.4.2\x0135=8\x0134=42\x0111=CLORD-123\x01"
    fields = fix_client.parse_message(raw_str)
    
    assert fields[35] == "8"
    assert fields[34] == "42"
    assert fields[11] == "CLORD-123"
