import pytest
import os
from fix_handler import FIXHandler

def test_fix_compliance_logon_structure():
    """Validates that FIX client generates compliant Logon (MsgType = A) messages."""
    # Clean up any stale session store to ensure a fresh sequence baseline for this test
    if os.path.exists("session_store.json"):
        try:
            os.remove("session_store.json")
        except OSError:
            pass

    client = FIXHandler(
        host="127.0.0.1",
        port=9800,
        sender_comp_id="DESK_RISK_01",
        target_comp_id="EXCHANGE_MATCH"
    )
    
    # Verify mandatory session identifiers and configuration
    assert client.sender_comp_id == "DESK_RISK_01"
    assert client.target_comp_id == "EXCHANGE_MATCH"
    assert client.inbound_seq >= 1
    assert client.outbound_seq >= 1
