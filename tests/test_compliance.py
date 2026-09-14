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

def test_fix_compliance_logon_structure(fix_client):
    """Verify that generated Logon (MsgType=A) messages contain mandatory institutional compliance fields."""
    # Generate a standard logon message using the FIX handler
    logon_msg = fix_client.generate_logon_message(heartbeat_secs=10)
    parsed = fix_client.parse_message(logon_msg)

    # Mandatory FIX compliance checks for session initiation
    assert parsed.get("35") == "A", "Message Type must be Logon (A)."
    assert "98" in parsed, "EncryptedMethod field is mandatory for standard FIX logon."
    
    # Verify HeartBtInt (Tag 108) matches expected configuration value (10 seconds)
    heartbeat_interval = parsed.get("108")
    assert int(heartbeat_interval) == 10, f"Expected Heartbeat interval to be 10, got {heartbeat_interval}"

def test_fix_compliance_header_tags(fix_client):
    """Verify standard administrative header compliance fields."""
    raw_msg = "8=FIX.4.2\x019=45\x0135=0\x0149=CLIENT_SIM\x0156=EXCHANGE_SIM\x0134=1\x0152=20260101-00:00:00.000\x01"
    parsed = fix_client.parse_message(raw_msg)

    assert parsed.get("8") == "FIX.4.2", "BeginString must specify FIX version."
    assert parsed.get("49") == "SenderCompID should match client identifier."
    assert parsed.get("56") == "TargetCompID should match exchange identifier."
    assert "34" in parsed, "MsgSeqNum is mandatory."
    assert "52" in parsed, "SendingTime is mandatory."
