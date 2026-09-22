import json

import pytest

from src.domain.billing.ports import PlanRef
from src.domain.shared.exceptions import InvalidWebhookPayloadError
from src.infrastructure.billing_providers.mock import MockBillingProvider

_ORG_ID = "11111111-1111-1111-1111-111111111111"


def test_health_check_reports_healthy():
    provider = MockBillingProvider()
    health = provider.health_check()
    assert health.healthy is True


def test_create_subscription_with_trial_starts_trialing():
    provider = MockBillingProvider()
    ref = provider.create_subscription(
        organization_id=_ORG_ID, plan=PlanRef(code="dev_unlimited"), trial_period_days=14
    )
    assert ref.status == "trialing"
    assert ref.trial_end is not None
    assert ref.trial_end > ref.current_period_start
    assert ref.external_subscription_id is not None
    assert ref.external_customer_id is not None


def test_create_subscription_without_trial_starts_active():
    provider = MockBillingProvider()
    ref = provider.create_subscription(
        organization_id=_ORG_ID, plan=PlanRef(code="dev_unlimited"), trial_period_days=None
    )
    assert ref.status == "active"
    assert ref.trial_end is None


def test_cancel_immediately_sets_canceled():
    provider = MockBillingProvider()
    ref = provider.create_subscription(
        organization_id=_ORG_ID, plan=PlanRef(code="dev_unlimited"), trial_period_days=None
    )
    canceled = provider.cancel_subscription(subscription_ref=ref, at_period_end=False)
    assert canceled.status == "canceled"


def test_cancel_at_period_end_keeps_current_status():
    provider = MockBillingProvider()
    ref = provider.create_subscription(
        organization_id=_ORG_ID, plan=PlanRef(code="dev_unlimited"), trial_period_days=None
    )
    result = provider.cancel_subscription(subscription_ref=ref, at_period_end=True)
    assert result.status == "active"


def test_verify_webhook_signature_accepts_known_secret():
    provider = MockBillingProvider()
    assert provider.verify_webhook_signature(payload=b"{}", signature_header="mock-dev-secret")


def test_verify_webhook_signature_rejects_wrong_secret():
    provider = MockBillingProvider()
    assert not provider.verify_webhook_signature(payload=b"{}", signature_header="wrong")


def test_parse_webhook_event_extracts_fields():
    provider = MockBillingProvider()
    payload = json.dumps(
        {"id": "evt_123", "type": "subscription.updated", "organization_id": _ORG_ID}
    ).encode()
    event = provider.parse_webhook_event(payload=payload)
    assert event.external_event_id == "evt_123"
    assert event.event_type == "subscription.updated"
    assert str(event.organization_id) == _ORG_ID


def test_parse_webhook_event_generates_id_when_missing():
    provider = MockBillingProvider()
    payload = json.dumps({"type": "subscription.created"}).encode()
    event = provider.parse_webhook_event(payload=payload)
    assert event.external_event_id.startswith("mock_evt_")
    assert event.organization_id is None


def test_parse_webhook_event_rejects_malformed_payload():
    provider = MockBillingProvider()
    with pytest.raises(InvalidWebhookPayloadError):
        provider.parse_webhook_event(payload=b"not json")


def test_parse_webhook_event_rejects_missing_type():
    provider = MockBillingProvider()
    with pytest.raises(InvalidWebhookPayloadError):
        provider.parse_webhook_event(payload=json.dumps({"id": "evt_1"}).encode())
