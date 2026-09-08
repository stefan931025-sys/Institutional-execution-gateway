from enum import Enum, auto
import logging

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
        self.cl_ord_id = cl_ord_id
        self.state = OrderState.PENDING_NEW
        self.cum_qty = 0
        self.leaves_qty = 0

        # Define valid allowed transitions for safety
        self._valid_transitions = {
            OrderState.PENDING_NEW: {OrderState.NEW, OrderState.REJECTED},
            OrderState.NEW: {OrderState.PARTIALLY_FILLED, OrderState.FILLED, OrderState.PENDING_CANCEL, OrderState.CANCELED, OrderState.EXPIRED},
            OrderState.PARTIALLY_FILLED: {OrderState.PARTIALLY_FILLED, OrderState.FILLED, OrderState.PENDING_CANCEL, OrderState.CANCELED},
            OrderState.PENDING_CANCEL: {OrderState.CANCELED, OrderState.NEW, OrderState.PARTIALLY_FILLED}, # Reject cancel can revert to prior state
            OrderState.CANCELED: set(), # Terminal states
            OrderState.FILLED: set(),
            OrderState.REJECTED: set(),
            OrderState.EXPIRED: set()
        }

    def transition_to(self, new_state: OrderState, execution_report: dict = None):
        """Validates and executes a state transition based on incoming FIX execution reports."""
        if new_state not in self._valid_transitions.get(self.state, set()):
            raise InvalidStateTransitionError(
                f"Invalid transition for Order {self.cl_ord_id}: {self.state.name} -> {new_state.name}"
            )
        
        logging.info(f"Order {self.cl_ord_id} transitioning: {self.state.name} -> {new_state.name}")
        self.state = new_state

        if execution_report:
            self._update_quantities(execution_report)

    def _update_quantities(self, report: dict):
        """Tracks cumulative and remaining quantities from FIX tags (CumQty, LeavesQty)."""
        self.cum_qty = report.get('CumQty', self.cum_qty)
        self.leaves_qty = report.get('LeavesQty', self.leaves_qty)
