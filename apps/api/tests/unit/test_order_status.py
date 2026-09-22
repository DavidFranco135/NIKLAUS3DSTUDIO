import pytest

from src.domain.orders.status import validate_transition
from src.domain.shared.exceptions import InvalidOrderTransitionError


def test_can_advance_one_step():
    validate_transition("quote", "order")
    validate_transition("production", "printing")


def test_can_skip_stages_forward():
    validate_transition("quote", "paid")
    validate_transition("order", "delivered")


def test_cannot_go_backward():
    with pytest.raises(InvalidOrderTransitionError):
        validate_transition("printing", "production")


def test_cannot_stay_in_the_same_status():
    with pytest.raises(InvalidOrderTransitionError):
        validate_transition("order", "order")


def test_can_cancel_from_any_non_terminal_stage():
    for stage in ["quote", "order", "paid", "production", "printing", "finishing", "packaging"]:
        validate_transition(stage, "cancelled")


def test_cannot_cancel_a_completed_order():
    with pytest.raises(InvalidOrderTransitionError):
        validate_transition("completed", "cancelled")


def test_cannot_cancel_an_already_cancelled_order():
    with pytest.raises(InvalidOrderTransitionError):
        validate_transition("cancelled", "cancelled")


def test_cancelled_order_cannot_move_anywhere():
    with pytest.raises(InvalidOrderTransitionError):
        validate_transition("cancelled", "order")


def test_completed_order_cannot_advance_further():
    with pytest.raises(InvalidOrderTransitionError):
        validate_transition("completed", "delivered")


def test_rejects_unknown_status_values():
    with pytest.raises(InvalidOrderTransitionError):
        validate_transition("bogus", "order")
    with pytest.raises(InvalidOrderTransitionError):
        validate_transition("quote", "bogus")
