import pytest
from utils import normalize_order_constraints

def test_normalize_order_constraints():
    # Test custom tick size (0.05) and lot size (0.5)
    price, qty = normalize_order_constraints(102.13, 12.37, tick_size=0.05, lot_size=0.5)
    
    assert price == 102.15  # 102.13 rounded to nearest 0.05
    assert qty == 12.5      # 12.37 rounded to nearest 0.5

def test_normalize_default_constraints():
    # Test standard defaults (tick: 0.01, lot: 0.1)
    price, qty = normalize_order_constraints(50.126, 5.24)
    
    assert price == 50.13
    assert qty == 5.2
