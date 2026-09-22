from fastapi.testclient import TestClient

from tests.api.conftest import auth_headers, register_user


def _org_id(client: TestClient, headers: dict) -> str:
    return client.get("/api/v1/organizations", headers=headers).json()[0]["id"]


def _create_customer(client: TestClient, org_id: str, headers: dict) -> dict:
    response = client.post(
        f"/api/v1/organizations/{org_id}/customers",
        json={"name": "Carlos Souza", "email": "carlos@example.com"},
        headers=headers,
    )
    assert response.status_code == 201, response.text
    return response.json()


def _create_cost_profile(client: TestClient, org_id: str, headers: dict) -> dict:
    response = client.post(
        f"/api/v1/organizations/{org_id}/cost-profiles",
        json={
            "name": "Padrão",
            "energy_cost_per_kwh": 0.9,
            "labor_cost_per_hour": 20.0,
            "packaging_cost_flat": 3.0,
            "waste_percentage": 5.0,
            "fees_percentage": 3.0,
            "profit_margin_percentage": 40.0,
            "is_default": True,
        },
        headers=headers,
    )
    assert response.status_code == 201, response.text
    return response.json()


def _create_quote(client: TestClient, org_id: str, headers: dict, *, customer_id: str) -> dict:
    profile = _create_cost_profile(client, org_id, headers)
    response = client.post(
        f"/api/v1/organizations/{org_id}/quotes",
        json={
            "cost_profile_id": profile["id"],
            "customer_id": customer_id,
            "material_cost": 10.0,
            "print_time_hours": 1.0,
            "machine_cost_per_hour": 1.0,
            "energy_kwh": 0.1,
            "labor_hours": 0.2,
        },
        headers=headers,
    )
    assert response.status_code == 201, response.text
    return response.json()


def test_create_order_without_quote(client: TestClient):
    owner = register_user(client, organization_name="Acme Prints", email="owner@acme.io")
    headers = auth_headers(owner["access_token"])
    org_id = _org_id(client, headers)
    customer = _create_customer(client, org_id, headers)

    response = client.post(
        f"/api/v1/organizations/{org_id}/orders",
        json={"customer_id": customer["id"]},
        headers=headers,
    )
    assert response.status_code == 201, response.text
    order = response.json()
    assert order["status"] == "quote"
    assert order["total_amount"] == 0
    assert order["quote_id"] is None


def test_create_order_from_quote_inherits_price_and_marks_quote_accepted(client: TestClient):
    owner = register_user(client, organization_name="Acme Prints", email="owner@acme.io")
    headers = auth_headers(owner["access_token"])
    org_id = _org_id(client, headers)
    customer = _create_customer(client, org_id, headers)
    quote = _create_quote(client, org_id, headers, customer_id=customer["id"])

    response = client.post(
        f"/api/v1/organizations/{org_id}/orders",
        json={"customer_id": customer["id"], "quote_id": quote["id"]},
        headers=headers,
    )
    assert response.status_code == 201, response.text
    order = response.json()
    assert order["total_amount"] == quote["suggested_price"]

    refetched_quote = client.get(
        f"/api/v1/organizations/{org_id}/quotes/{quote['id']}", headers=headers
    ).json()
    assert refetched_quote["status"] == "accepted"


def test_rejects_order_with_unknown_customer(client: TestClient):
    owner = register_user(client, organization_name="Acme Prints", email="owner@acme.io")
    headers = auth_headers(owner["access_token"])
    org_id = _org_id(client, headers)

    response = client.post(
        f"/api/v1/organizations/{org_id}/orders",
        json={"customer_id": "00000000-0000-0000-0000-000000000000"},
        headers=headers,
    )
    assert response.status_code == 404


def test_add_item_recomputes_total_amount(client: TestClient):
    owner = register_user(client, organization_name="Acme Prints", email="owner@acme.io")
    headers = auth_headers(owner["access_token"])
    org_id = _org_id(client, headers)
    customer = _create_customer(client, org_id, headers)
    order = client.post(
        f"/api/v1/organizations/{org_id}/orders",
        json={"customer_id": customer["id"]},
        headers=headers,
    ).json()

    response = client.post(
        f"/api/v1/organizations/{org_id}/orders/{order['id']}/items",
        json={"quantity": 2, "unit_price": 15.0, "unit_cost": 5.0},
        headers=headers,
    )
    assert response.status_code == 201, response.text

    client.post(
        f"/api/v1/organizations/{org_id}/orders/{order['id']}/items",
        json={"quantity": 1, "unit_price": 9.5},
        headers=headers,
    )

    refetched = client.get(
        f"/api/v1/organizations/{org_id}/orders/{order['id']}", headers=headers
    ).json()
    assert refetched["total_amount"] == 39.5

    items = client.get(
        f"/api/v1/organizations/{org_id}/orders/{order['id']}/items", headers=headers
    ).json()
    assert len(items) == 2


def test_order_status_transitions_forward(client: TestClient):
    owner = register_user(client, organization_name="Acme Prints", email="owner@acme.io")
    headers = auth_headers(owner["access_token"])
    org_id = _org_id(client, headers)
    customer = _create_customer(client, org_id, headers)
    order = client.post(
        f"/api/v1/organizations/{org_id}/orders",
        json={"customer_id": customer["id"]},
        headers=headers,
    ).json()

    response = client.post(
        f"/api/v1/organizations/{org_id}/orders/{order['id']}/transition",
        json={"status": "paid"},
        headers=headers,
    )
    assert response.status_code == 200, response.text
    assert response.json()["status"] == "paid"


def test_order_status_cannot_go_backward(client: TestClient):
    owner = register_user(client, organization_name="Acme Prints", email="owner@acme.io")
    headers = auth_headers(owner["access_token"])
    org_id = _org_id(client, headers)
    customer = _create_customer(client, org_id, headers)
    order = client.post(
        f"/api/v1/organizations/{org_id}/orders",
        json={"customer_id": customer["id"]},
        headers=headers,
    ).json()
    client.post(
        f"/api/v1/organizations/{org_id}/orders/{order['id']}/transition",
        json={"status": "production"},
        headers=headers,
    )

    response = client.post(
        f"/api/v1/organizations/{org_id}/orders/{order['id']}/transition",
        json={"status": "order"},
        headers=headers,
    )
    assert response.status_code == 422


def test_completed_order_cannot_be_cancelled(client: TestClient):
    owner = register_user(client, organization_name="Acme Prints", email="owner@acme.io")
    headers = auth_headers(owner["access_token"])
    org_id = _org_id(client, headers)
    customer = _create_customer(client, org_id, headers)
    order = client.post(
        f"/api/v1/organizations/{org_id}/orders",
        json={"customer_id": customer["id"]},
        headers=headers,
    ).json()
    client.post(
        f"/api/v1/organizations/{org_id}/orders/{order['id']}/transition",
        json={"status": "completed"},
        headers=headers,
    )

    response = client.post(
        f"/api/v1/organizations/{org_id}/orders/{order['id']}/transition",
        json={"status": "cancelled"},
        headers=headers,
    )
    assert response.status_code == 422


def test_customer_history_includes_orders(client: TestClient):
    owner = register_user(client, organization_name="Acme Prints", email="owner@acme.io")
    headers = auth_headers(owner["access_token"])
    org_id = _org_id(client, headers)
    customer = _create_customer(client, org_id, headers)
    order = client.post(
        f"/api/v1/organizations/{org_id}/orders",
        json={"customer_id": customer["id"]},
        headers=headers,
    ).json()

    response = client.get(
        f"/api/v1/organizations/{org_id}/customers/{customer['id']}/history", headers=headers
    )
    assert response.status_code == 200
    assert [o["id"] for o in response.json()["orders"]] == [order["id"]]


def test_inventory_movement_can_reference_a_valid_order(client: TestClient):
    owner = register_user(client, organization_name="Acme Prints", email="owner@acme.io")
    headers = auth_headers(owner["access_token"])
    org_id = _org_id(client, headers)
    customer = _create_customer(client, org_id, headers)
    order = client.post(
        f"/api/v1/organizations/{org_id}/orders",
        json={"customer_id": customer["id"]},
        headers=headers,
    ).json()
    item = client.post(
        f"/api/v1/organizations/{org_id}/inventory-items",
        json={
            "name": "Filamento PLA Branco",
            "category": "filament",
            "unit": "g",
            "initial_quantity": 1000,
        },
        headers=headers,
    ).json()

    response = client.post(
        f"/api/v1/organizations/{org_id}/inventory-items/{item['id']}/movements",
        json={"type": "consumo", "quantity": -50, "reference_order_id": order["id"]},
        headers=headers,
    )
    assert response.status_code == 201, response.text
    assert response.json()["reference_order_id"] == order["id"]


def test_inventory_movement_rejects_unknown_order(client: TestClient):
    owner = register_user(client, organization_name="Acme Prints", email="owner@acme.io")
    headers = auth_headers(owner["access_token"])
    org_id = _org_id(client, headers)
    item = client.post(
        f"/api/v1/organizations/{org_id}/inventory-items",
        json={
            "name": "Filamento PLA Branco",
            "category": "filament",
            "unit": "g",
            "initial_quantity": 1000,
        },
        headers=headers,
    ).json()

    response = client.post(
        f"/api/v1/organizations/{org_id}/inventory-items/{item['id']}/movements",
        json={
            "type": "consumo",
            "quantity": -50,
            "reference_order_id": "00000000-0000-0000-0000-000000000000",
        },
        headers=headers,
    )
    assert response.status_code == 404


def test_viewer_cannot_create_order(client: TestClient):
    owner = register_user(client, organization_name="Acme Prints", email="owner@acme.io")
    owner_headers = auth_headers(owner["access_token"])
    org_id = _org_id(client, owner_headers)
    customer = _create_customer(client, org_id, owner_headers)

    viewer = register_user(client, organization_name="Solo Org", email="viewer@acme.io")
    client.post(
        f"/api/v1/organizations/{org_id}/members",
        json={"email": "viewer@acme.io", "role": "VIEWER"},
        headers=owner_headers,
    )

    response = client.post(
        f"/api/v1/organizations/{org_id}/orders",
        json={"customer_id": customer["id"]},
        headers=auth_headers(viewer["access_token"]),
    )
    assert response.status_code == 403
