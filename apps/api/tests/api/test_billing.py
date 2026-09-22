import json

from fastapi.testclient import TestClient

from src.infrastructure.db.models import Plan, PlanEntitlement
from tests.api.conftest import auth_headers, register_user


def _org_id(client: TestClient, headers: dict) -> str:
    return client.get("/api/v1/organizations", headers=headers).json()[0]["id"]


def _create_tight_plan(db_session, *, code: str, max_projects: int) -> Plan:
    plan = Plan(code=code, name="Plano de teste (limite baixo)")
    db_session.add(plan)
    db_session.flush()
    db_session.add(
        PlanEntitlement(
            plan_id=plan.id, key="max_projects", limit_type="numeric", numeric_value=max_projects
        )
    )
    db_session.add(
        PlanEntitlement(
            plan_id=plan.id,
            key="max_ai_jobs_per_period",
            limit_type="numeric",
            numeric_value=50,
        )
    )
    db_session.add(
        PlanEntitlement(
            plan_id=plan.id, key="max_storage_mb", limit_type="numeric", numeric_value=500
        )
    )
    db_session.commit()
    return plan


def test_register_auto_provisions_a_subscription(client: TestClient):
    owner = register_user(client, organization_name="Acme Prints", email="owner@acme.io")
    headers = auth_headers(owner["access_token"])
    org_id = _org_id(client, headers)

    response = client.get(f"/api/v1/organizations/{org_id}/billing/subscription", headers=headers)
    assert response.status_code == 200
    subscription = response.json()
    assert subscription["status"] in ("active", "trialing")
    assert subscription["plan"]["code"] == "dev_unlimited"


def test_list_plans_includes_dev_plan(client: TestClient):
    owner = register_user(client, organization_name="Acme Prints", email="owner@acme.io")
    headers = auth_headers(owner["access_token"])

    response = client.get("/api/v1/billing/plans", headers=headers)
    assert response.status_code == 200
    codes = [p["code"] for p in response.json()]
    assert "dev_unlimited" in codes


def test_usage_reports_zero_for_a_fresh_org(client: TestClient):
    owner = register_user(client, organization_name="Acme Prints", email="owner@acme.io")
    headers = auth_headers(owner["access_token"])
    org_id = _org_id(client, headers)

    response = client.get(f"/api/v1/organizations/{org_id}/billing/usage", headers=headers)
    assert response.status_code == 200
    usage_by_key = {item["key"]: item for item in response.json()}
    assert usage_by_key["max_projects"]["current_usage"] == 0
    assert usage_by_key["max_projects"]["limit"] == 20
    assert usage_by_key["feature.ai_text_to_3d"]["enabled"] is True


def test_usage_increases_as_projects_are_created(client: TestClient):
    owner = register_user(client, organization_name="Acme Prints", email="owner@acme.io")
    headers = auth_headers(owner["access_token"])
    org_id = _org_id(client, headers)

    client.post(f"/api/v1/organizations/{org_id}/projects", json={"name": "P1"}, headers=headers)
    client.post(f"/api/v1/organizations/{org_id}/projects", json={"name": "P2"}, headers=headers)

    response = client.get(f"/api/v1/organizations/{org_id}/billing/usage", headers=headers)
    usage_by_key = {item["key"]: item for item in response.json()}
    assert usage_by_key["max_projects"]["current_usage"] == 2


def test_project_creation_is_blocked_once_the_plan_limit_is_reached(
    client: TestClient, db_session
):
    owner = register_user(client, organization_name="Acme Prints", email="owner@acme.io")
    headers = auth_headers(owner["access_token"])
    org_id = _org_id(client, headers)

    _create_tight_plan(db_session, code="tight_test_plan", max_projects=1)
    response = client.post(
        f"/api/v1/organizations/{org_id}/billing/subscription/change-plan",
        json={"plan_code": "tight_test_plan"},
        headers=headers,
    )
    assert response.status_code == 200, response.text

    ok = client.post(
        f"/api/v1/organizations/{org_id}/projects", json={"name": "P1"}, headers=headers
    )
    assert ok.status_code == 201

    blocked = client.post(
        f"/api/v1/organizations/{org_id}/projects", json={"name": "P2"}, headers=headers
    )
    assert blocked.status_code == 402
    detail = blocked.json()["detail"]
    assert detail["limit_key"] == "max_projects"
    assert detail["current_usage"] == 1
    assert detail["limit"] == 1


def test_owner_can_cancel_subscription_immediately(client: TestClient):
    owner = register_user(client, organization_name="Acme Prints", email="owner@acme.io")
    headers = auth_headers(owner["access_token"])
    org_id = _org_id(client, headers)

    response = client.post(
        f"/api/v1/organizations/{org_id}/billing/subscription/cancel",
        json={"at_period_end": False},
        headers=headers,
    )
    assert response.status_code == 200, response.text
    assert response.json()["status"] == "canceled"
    assert response.json()["canceled_at"] is not None


def test_cancel_at_period_end_keeps_status_but_sets_flag(client: TestClient):
    owner = register_user(client, organization_name="Acme Prints", email="owner@acme.io")
    headers = auth_headers(owner["access_token"])
    org_id = _org_id(client, headers)

    response = client.post(
        f"/api/v1/organizations/{org_id}/billing/subscription/cancel",
        json={"at_period_end": True},
        headers=headers,
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["status"] == "active"
    assert body["cancel_at_period_end"] is True


def test_cancelling_twice_is_rejected(client: TestClient):
    owner = register_user(client, organization_name="Acme Prints", email="owner@acme.io")
    headers = auth_headers(owner["access_token"])
    org_id = _org_id(client, headers)

    client.post(
        f"/api/v1/organizations/{org_id}/billing/subscription/cancel",
        json={"at_period_end": False},
        headers=headers,
    )
    response = client.post(
        f"/api/v1/organizations/{org_id}/billing/subscription/cancel",
        json={"at_period_end": False},
        headers=headers,
    )
    assert response.status_code == 422


def test_manager_cannot_cancel_subscription_only_owner_can(client: TestClient):
    owner = register_user(client, organization_name="Acme Prints", email="owner@acme.io")
    owner_headers = auth_headers(owner["access_token"])
    org_id = _org_id(client, owner_headers)

    manager = register_user(client, organization_name="Solo Org", email="manager@acme.io")
    client.post(
        f"/api/v1/organizations/{org_id}/members",
        json={"email": "manager@acme.io", "role": "MANAGER"},
        headers=owner_headers,
    )

    response = client.post(
        f"/api/v1/organizations/{org_id}/billing/subscription/cancel",
        json={"at_period_end": False},
        headers=auth_headers(manager["access_token"]),
    )
    assert response.status_code == 403


def test_change_plan_to_unknown_code_is_rejected(client: TestClient):
    owner = register_user(client, organization_name="Acme Prints", email="owner@acme.io")
    headers = auth_headers(owner["access_token"])
    org_id = _org_id(client, headers)

    response = client.post(
        f"/api/v1/organizations/{org_id}/billing/subscription/change-plan",
        json={"plan_code": "does_not_exist"},
        headers=headers,
    )
    assert response.status_code == 404


def test_webhook_updates_subscription_status(client: TestClient):
    owner = register_user(client, organization_name="Acme Prints", email="owner@acme.io")
    headers = auth_headers(owner["access_token"])
    org_id = _org_id(client, headers)

    payload = json.dumps(
        {
            "id": "evt_1",
            "type": "subscription.updated",
            "organization_id": org_id,
            "status": "past_due",
        }
    )
    response = client.post(
        "/api/v1/billing/webhooks/mock_billing",
        content=payload,
        headers={"X-Billing-Signature": "mock-dev-secret"},
    )
    assert response.status_code == 200, response.text
    assert response.json()["status"] == "processed"

    subscription = client.get(
        f"/api/v1/organizations/{org_id}/billing/subscription", headers=headers
    ).json()
    assert subscription["status"] == "past_due"


def test_webhook_retry_is_idempotent(client: TestClient):
    owner = register_user(client, organization_name="Acme Prints", email="owner@acme.io")
    headers = auth_headers(owner["access_token"])
    org_id = _org_id(client, headers)

    payload = json.dumps(
        {
            "id": "evt_retry",
            "type": "subscription.updated",
            "organization_id": org_id,
            "status": "past_due",
        }
    )
    first = client.post(
        "/api/v1/billing/webhooks/mock_billing",
        content=payload,
        headers={"X-Billing-Signature": "mock-dev-secret"},
    )
    second = client.post(
        "/api/v1/billing/webhooks/mock_billing",
        content=payload,
        headers={"X-Billing-Signature": "mock-dev-secret"},
    )
    assert first.status_code == 200
    assert second.status_code == 200
    assert first.json()["id"] == second.json()["id"]

    events = client.get(f"/api/v1/organizations/{org_id}/billing/usage", headers=headers)
    assert events.status_code == 200


def test_webhook_rejects_invalid_signature(client: TestClient):
    payload = json.dumps({"id": "evt_x", "type": "subscription.updated"})
    response = client.post(
        "/api/v1/billing/webhooks/mock_billing",
        content=payload,
        headers={"X-Billing-Signature": "wrong-secret"},
    )
    assert response.status_code == 400


def test_webhook_rejects_malformed_payload(client: TestClient):
    response = client.post(
        "/api/v1/billing/webhooks/mock_billing",
        content=b"not json",
        headers={"X-Billing-Signature": "mock-dev-secret"},
    )
    assert response.status_code == 400
