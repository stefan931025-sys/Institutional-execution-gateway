from enum import Enum, auto
import logging

logger = logging.getLogger("OrderStateMachine")

class OrderState(Enum):
    PENDING_NEW = auto()
    NEW = auto()
    PARTIALLY_FILLED = auto()
    FILLED = auto()
    PENDING_CANCEL = auto()
    CANCELED = auto()
    REJECTED = auto()
    EXPIRED = auto()

class InvalidStateTransitionError(Exception):
    """Raised when an illegal FIX order lifecycle transition is attempted."""
    pass

class OrderStateMachine:
    def __init__(self, cl_ord_id: str):
        """
        Manages the order lifecycle state machine for FIX execution reports.
        """
        self.cl_ord_id = cl_ord_id
        self.state = OrderState.PENDING_NEW
        self.cum_qty = 0.0
        self.leaves_qty = 0.0

        # Define strictly allowed state transitions for safety
        self._valid_transitions = {
            OrderState.PENDING_NEW: {OrderState.NEW, OrderState.REJECTED},
            OrderState.NEW: {OrderState.PARTIALLY_FILLED, OrderState.FILLED, OrderState.PENDING_CANCEL, OrderState.CANCELED, OrderState.EXPIRED},
            OrderState.PARTIALLY_FILLED: {OrderState.PARTIALLY_FILLED, OrderState.FILLED, OrderState.PENDING_CANCEL, OrderState.CANCELED},
            OrderState.PENDING_CANCEL: {OrderState.CANCELED, OrderState.NEW, OrderState.PARTIALLY_FILLED}, # Reject cancel can revert to prior state
            OrderState.CANCELED: set(),    # Terminal state
            OrderState.REJECTED: set(),    # Terminal state
            OrderState.EXPIRED: set()      # Terminal state
        }

    def transition_to(self, new_state: OrderState, execution_report: dict = None):
        """Validates and executes a state transition based on incoming FIX execution reports."""
        allowed_targets = self._valid_transitions.get(self.state, set())
        
        if new_state not in allowed_targets:
            raise InvalidStateTransitionError(
                f"Invalid transition for Order {self.cl_ord_id}: {self.state.name} -> {new_state.name}"
            )

        logger.info(f"Order {self.cl_ord_id} transitioning: {self.state.name} -> {new_state.name}")
        self.state = new_state

        if execution_report:
            self._update_quantities(execution_report)

    def _update_quantities(self, report: dict):
        """Tracks cumulative and remaining quantities from FIX tags (CumQty, LeavesQty)."""
        self.cum_qty = report.get("CumQty", self.cum_qty)
        self.leaves_qty = report.get("LeavesQty", self.leaves_qty)
