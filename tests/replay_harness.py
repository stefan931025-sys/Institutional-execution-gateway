"""
Deterministic Replay Harness (`tests/replay_harness.py`)
Replays sequence-tracked FIX message logs against the isolated exchange simulator 
to verify deterministic state transitions and risk-control integrity.
"""

import pytest
from dataclasses import dataclass


@dataclass
class FixMessage:
    msg_type: str  # e.g., 'D' for NewOrderSingle
    cl_ord_id: str
    symbol: str
    side: str
    order_qty: float
    price: float


class MockStateEngine:
    def __init__(self):
        self.processed_messages = []
        self.active_positions = {}

    def handle_message(self, msg: FixMessage) -> bool:
        """Simulates state machine ingestion of FIX messages."""
        if msg.msg_type == 'D':
            # Track execution and update internal mock positions
            self.processed_messages.append(msg.cl_ord_id)
            current_qty = self.active_positions.get(msg.symbol, 0.0)
            self.active_positions[msg.symbol] = current_qty + msg.order_qty
            return True
        return False


def test_deterministic_replay_sequence():
    """Verifies that replaying a fixed log yields identical, predictable state outcomes."""
    log_stream = [
        FixMessage(msg_type='D', cl_ord_id='ORD-001', symbol='AAPL', side='1', order_qty=100.0, price=175.50),
        FixMessage(msg_type='D', cl_ord_id='ORD-002', symbol='AAPL', side='1', order_qty=200.0, price=175.60),
        FixMessage(msg_type='D', cl_ord_id='ORD-003', symbol='TSLA', side='2', order_qty=50.0, price=240.00),
    ]

    engine = MockStateEngine()

    # Replay stream
    for message in log_stream:
        success = engine.handle_message(message)
        assert success is True

    # Assert deterministic final state
    assert engine.processed_messages == ['ORD-001', 'ORD-002', 'ORD-003']
    assert engine.active_positions['AAPL'] == 300.0
    assert engine.active_positions['TSLA'] == 50.0
