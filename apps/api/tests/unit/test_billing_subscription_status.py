import pytest

from src.domain.billing.subscription_status import validate_transition
from src.domain.shared.exceptions import InvalidSubscriptionTransitionError


def test_trialing_can_become_active_or_canceled():
    validate_transition("trialing", "active")
    validate_transition("trialing", "canceled")


def test_active_can_become_past_due_or_canceled():
    validate_transition("active", "past_due")
    validate_transition("active", "canceled")


def test_past_due_can_recover_to_active_or_be_canceled():
    validate_transition("past_due", "active")
    validate_transition("past_due", "canceled")


def test_canceled_is_terminal():
    with pytest.raises(InvalidSubscriptionTransitionError):
        validate_transition("canceled", "active")
    with pytest.raises(InvalidSubscriptionTransitionError):
        validate_transition("canceled", "trialing")


def test_trialing_cannot_skip_to_past_due():
    with pytest.raises(InvalidSubscriptionTransitionError):
        validate_transition("trialing", "past_due")


def test_rejects_unknown_status_values():
    with pytest.raises(InvalidSubscriptionTransitionError):
        validate_transition("bogus", "active")
    with pytest.raises(InvalidSubscriptionTransitionError):
        validate_transition("active", "bogus")
