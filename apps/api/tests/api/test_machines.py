from fastapi.testclient import TestClient

from tests.api.conftest import auth_headers, register_user


def _org_id(client: TestClient, headers: dict) -> str:
    return client.get("/api/v1/organizations", headers=headers).json()[0]["id"]


def _create_machine(client: TestClient, org_id: str, headers: dict, **overrides) -> dict:
    payload = {
        "name": "Ender 3",
        "brand": "Creality",
        "technology": "FDM",
        "build_volume_x_mm": 220,
        "build_volume_y_mm": 220,
        "build_volume_z_mm": 250,
        "power_watts": 220,
        "cost_per_hour": 2.5,
    }
    payload.update(overrides)
    response = client.post(
        f"/api/v1/organizations/{org_id}/machines", json=payload, headers=headers
    )
    assert response.status_code == 201, response.text
    return response.json()


def test_create_list_and_get_machine(client: TestClient):
    owner = register_user(client, organization_name="Acme Prints", email="owner@acme.io")
    headers = auth_headers(owner["access_token"])
    org_id = _org_id(client, headers)

    machine = _create_machine(client, org_id, headers)
    assert machine["status"] == "active"

    response = client.get(f"/api/v1/organizations/{org_id}/machines", headers=headers)
    assert response.status_code == 200
    assert len(response.json()) == 1

    response = client.get(
        f"/api/v1/organizations/{org_id}/machines/{machine['id']}", headers=headers
    )
    assert response.status_code == 200
    assert response.json()["name"] == "Ender 3"


def test_update_machine_status(client: TestClient):
    owner = register_user(client, organization_name="Acme Prints", email="owner@acme.io")
    headers = auth_headers(owner["access_token"])
    org_id = _org_id(client, headers)
    machine = _create_machine(client, org_id, headers)

    response = client.patch(
        f"/api/v1/organizations/{org_id}/machines/{machine['id']}",
        json={"status": "maintenance"},
        headers=headers,
    )
    assert response.status_code == 200
    assert response.json()["status"] == "maintenance"
    assert response.json()["name"] == "Ender 3"


def test_order_item_can_reference_a_valid_machine(client: TestClient):
    owner = register_user(client, organization_name="Acme Prints", email="owner@acme.io")
    headers = auth_headers(owner["access_token"])
    org_id = _org_id(client, headers)
    machine = _create_machine(client, org_id, headers)
    customer = client.post(
        f"/api/v1/organizations/{org_id}/customers", json={"name": "Carlos"}, headers=headers
    ).json()
    order = client.post(
        f"/api/v1/organizations/{org_id}/orders",
        json={"customer_id": customer["id"]},
        headers=headers,
    ).json()

    response = client.post(
        f"/api/v1/organizations/{org_id}/orders/{order['id']}/items",
        json={"machine_id": machine["id"], "quantity": 1, "unit_price": 20.0},
        headers=headers,
    )
    assert response.status_code == 201, response.text
    assert response.json()["machine_id"] == machine["id"]


def test_order_item_rejects_unknown_machine(client: TestClient):
    owner = register_user(client, organization_name="Acme Prints", email="owner@acme.io")
    headers = auth_headers(owner["access_token"])
    org_id = _org_id(client, headers)
    customer = client.post(
        f"/api/v1/organizations/{org_id}/customers", json={"name": "Carlos"}, headers=headers
    ).json()
    order = client.post(
        f"/api/v1/organizations/{org_id}/orders",
        json={"customer_id": customer["id"]},
        headers=headers,
    ).json()

    response = client.post(
        f"/api/v1/organizations/{org_id}/orders/{order['id']}/items",
        json={
            "machine_id": "00000000-0000-0000-0000-000000000000",
            "quantity": 1,
            "unit_price": 20.0,
        },
        headers=headers,
    )
    assert response.status_code == 404


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


def test_quote_can_use_machine_cost_per_hour_from_a_machine_profile(client: TestClient):
    owner = register_user(client, organization_name="Acme Prints", email="owner@acme.io")
    headers = auth_headers(owner["access_token"])
    org_id = _org_id(client, headers)
    machine = _create_machine(client, org_id, headers, cost_per_hour=4.0)
    profile = _create_cost_profile(client, org_id, headers)

    response = client.post(
        f"/api/v1/organizations/{org_id}/quotes",
        json={
            "cost_profile_id": profile["id"],
            "machine_id": machine["id"],
            "material_cost": 10.0,
            "print_time_hours": 2.0,
            "energy_kwh": 0.1,
            "labor_hours": 0.2,
        },
        headers=headers,
    )
    assert response.status_code == 201, response.text

    manual = client.post(
        f"/api/v1/organizations/{org_id}/quotes",
        json={
            "cost_profile_id": profile["id"],
            "machine_cost_per_hour": 4.0,
            "material_cost": 10.0,
            "print_time_hours": 2.0,
            "energy_kwh": 0.1,
            "labor_hours": 0.2,
        },
        headers=headers,
    )
    assert manual.status_code == 201, manual.text
    assert response.json()["suggested_price"] == manual.json()["suggested_price"]


def test_quote_rejects_both_machine_id_and_manual_cost(client: TestClient):
    owner = register_user(client, organization_name="Acme Prints", email="owner@acme.io")
    headers = auth_headers(owner["access_token"])
    org_id = _org_id(client, headers)
    machine = _create_machine(client, org_id, headers)
    profile = _create_cost_profile(client, org_id, headers)

    response = client.post(
        f"/api/v1/organizations/{org_id}/quotes",
        json={
            "cost_profile_id": profile["id"],
            "machine_id": machine["id"],
            "machine_cost_per_hour": 4.0,
            "material_cost": 10.0,
            "print_time_hours": 2.0,
            "energy_kwh": 0.1,
            "labor_hours": 0.2,
        },
        headers=headers,
    )
    assert response.status_code == 422


def test_quote_rejects_neither_machine_id_nor_manual_cost(client: TestClient):
    owner = register_user(client, organization_name="Acme Prints", email="owner@acme.io")
    headers = auth_headers(owner["access_token"])
    org_id = _org_id(client, headers)
    profile = _create_cost_profile(client, org_id, headers)

    response = client.post(
        f"/api/v1/organizations/{org_id}/quotes",
        json={
            "cost_profile_id": profile["id"],
            "material_cost": 10.0,
            "print_time_hours": 2.0,
            "energy_kwh": 0.1,
            "labor_hours": 0.2,
        },
        headers=headers,
    )
    assert response.status_code == 422


def test_quote_rejects_unknown_machine(client: TestClient):
    owner = register_user(client, organization_name="Acme Prints", email="owner@acme.io")
    headers = auth_headers(owner["access_token"])
    org_id = _org_id(client, headers)
    profile = _create_cost_profile(client, org_id, headers)

    response = client.post(
        f"/api/v1/organizations/{org_id}/quotes",
        json={
            "cost_profile_id": profile["id"],
            "machine_id": "00000000-0000-0000-0000-000000000000",
            "material_cost": 10.0,
            "print_time_hours": 2.0,
            "energy_kwh": 0.1,
            "labor_hours": 0.2,
        },
        headers=headers,
    )
    assert response.status_code == 404


def test_viewer_cannot_create_machine(client: TestClient):
    owner = register_user(client, organization_name="Acme Prints", email="owner@acme.io")
    owner_headers = auth_headers(owner["access_token"])
    org_id = _org_id(client, owner_headers)

    viewer = register_user(client, organization_name="Solo Org", email="viewer@acme.io")
    client.post(
        f"/api/v1/organizations/{org_id}/members",
        json={"email": "viewer@acme.io", "role": "VIEWER"},
        headers=owner_headers,
    )

    response = client.post(
        f"/api/v1/organizations/{org_id}/machines",
        json={"name": "Not allowed", "technology": "FDM"},
        headers=auth_headers(viewer["access_token"]),
    )
    assert response.status_code == 403
