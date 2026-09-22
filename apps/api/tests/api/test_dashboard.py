from fastapi.testclient import TestClient

from tests.api.conftest import auth_headers, register_user


def _org_id(client: TestClient, headers: dict) -> str:
    return client.get("/api/v1/organizations", headers=headers).json()[0]["id"]


def test_dashboard_on_empty_org_is_all_zeros(client: TestClient):
    owner = register_user(client, organization_name="Acme Prints", email="owner@acme.io")
    headers = auth_headers(owner["access_token"])
    org_id = _org_id(client, headers)

    response = client.get(f"/api/v1/organizations/{org_id}/dashboard", headers=headers)
    assert response.status_code == 200
    dashboard = response.json()
    assert dashboard["orders_by_status"] == {}
    assert dashboard["low_stock_items_count"] == 0
    assert dashboard["customers_count"] == 0
    assert dashboard["projects_count"] == 0
    assert dashboard["financial"]["profit"] == 0.0


def test_dashboard_aggregates_across_modules(client: TestClient):
    owner = register_user(client, organization_name="Acme Prints", email="owner@acme.io")
    headers = auth_headers(owner["access_token"])
    org_id = _org_id(client, headers)

    client.post(
        f"/api/v1/organizations/{org_id}/projects", json={"name": "Chaveiro"}, headers=headers
    )
    customer = client.post(
        f"/api/v1/organizations/{org_id}/customers",
        json={"name": "Carlos Souza"},
        headers=headers,
    ).json()

    order_1 = client.post(
        f"/api/v1/organizations/{org_id}/orders",
        json={"customer_id": customer["id"]},
        headers=headers,
    ).json()
    order_2 = client.post(
        f"/api/v1/organizations/{org_id}/orders",
        json={"customer_id": customer["id"]},
        headers=headers,
    ).json()
    client.post(
        f"/api/v1/organizations/{org_id}/orders/{order_2['id']}/transition",
        json={"status": "paid"},
        headers=headers,
    )

    client.post(
        f"/api/v1/organizations/{org_id}/inventory-items",
        json={
            "name": "Filamento PLA",
            "category": "filament",
            "unit": "g",
            "minimum_stock": 500,
            "initial_quantity": 100,
        },
        headers=headers,
    )

    client.post(
        f"/api/v1/organizations/{org_id}/finance/transactions",
        json={"type": "despesa", "category": "energia", "amount": 50.0, "mark_as_paid": True},
        headers=headers,
    )

    response = client.get(f"/api/v1/organizations/{org_id}/dashboard", headers=headers)
    assert response.status_code == 200
    dashboard = response.json()

    assert dashboard["orders_by_status"] == {"quote": 1, "paid": 1}
    assert dashboard["low_stock_items_count"] == 1
    assert dashboard["customers_count"] == 1
    assert dashboard["projects_count"] == 1
    assert dashboard["financial"]["total_expense"] == 50.0
    assert order_1["status"] == "quote"


def test_viewer_can_read_dashboard(client: TestClient):
    owner = register_user(client, organization_name="Acme Prints", email="owner@acme.io")
    owner_headers = auth_headers(owner["access_token"])
    org_id = _org_id(client, owner_headers)

    viewer = register_user(client, organization_name="Solo Org", email="viewer@acme.io")
    client.post(
        f"/api/v1/organizations/{org_id}/members",
        json={"email": "viewer@acme.io", "role": "VIEWER"},
        headers=owner_headers,
    )

    response = client.get(
        f"/api/v1/organizations/{org_id}/dashboard", headers=auth_headers(viewer["access_token"])
    )
    assert response.status_code == 200
