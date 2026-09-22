from fastapi.testclient import TestClient

from tests.api.conftest import auth_headers, register_user


def _org_id(client: TestClient, headers: dict) -> str:
    return client.get("/api/v1/organizations", headers=headers).json()[0]["id"]


def _create_material(client: TestClient, org_id: str, headers: dict, **overrides) -> dict:
    payload = {
        "name": "PLA Branco",
        "type": "PLA",
        "color": "branco",
        "density_g_cm3": 1.24,
        "cost_per_kg": 90.0,
        "supplier": "Fornecedor X",
    }
    payload.update(overrides)
    response = client.post(
        f"/api/v1/organizations/{org_id}/materials", json=payload, headers=headers
    )
    assert response.status_code == 201, response.text
    return response.json()


def _create_item(client: TestClient, org_id: str, headers: dict, **overrides) -> dict:
    payload = {
        "name": "Filamento PLA Branco 1kg",
        "category": "filament",
        "unit": "g",
        "minimum_stock": 200,
        "unit_cost": 0.09,
        "initial_quantity": 1000,
    }
    payload.update(overrides)
    response = client.post(
        f"/api/v1/organizations/{org_id}/inventory-items", json=payload, headers=headers
    )
    assert response.status_code == 201, response.text
    return response.json()


def test_create_list_and_get_material(client: TestClient):
    owner = register_user(client, organization_name="Acme Prints", email="owner@acme.io")
    headers = auth_headers(owner["access_token"])
    org_id = _org_id(client, headers)

    material = _create_material(client, org_id, headers)

    response = client.get(f"/api/v1/organizations/{org_id}/materials", headers=headers)
    assert response.status_code == 200
    assert len(response.json()) == 1

    response = client.get(
        f"/api/v1/organizations/{org_id}/materials/{material['id']}", headers=headers
    )
    assert response.status_code == 200
    assert response.json()["name"] == "PLA Branco"


def test_create_inventory_item_linked_to_material(client: TestClient):
    owner = register_user(client, organization_name="Acme Prints", email="owner@acme.io")
    headers = auth_headers(owner["access_token"])
    org_id = _org_id(client, headers)
    material = _create_material(client, org_id, headers)

    item = _create_item(client, org_id, headers, material_id=material["id"])
    assert item["material_id"] == material["id"]
    assert item["quantity_on_hand"] == 1000
    assert item["is_low_stock"] is False


def test_rejects_inventory_item_with_unknown_material(client: TestClient):
    owner = register_user(client, organization_name="Acme Prints", email="owner@acme.io")
    headers = auth_headers(owner["access_token"])
    org_id = _org_id(client, headers)

    response = client.post(
        f"/api/v1/organizations/{org_id}/inventory-items",
        json={
            "material_id": "00000000-0000-0000-0000-000000000000",
            "name": "Item fantasma",
            "category": "filament",
            "unit": "g",
        },
        headers=headers,
    )
    assert response.status_code == 404


def test_entrada_movement_increases_stock(client: TestClient):
    owner = register_user(client, organization_name="Acme Prints", email="owner@acme.io")
    headers = auth_headers(owner["access_token"])
    org_id = _org_id(client, headers)
    item = _create_item(client, org_id, headers, initial_quantity=500)

    response = client.post(
        f"/api/v1/organizations/{org_id}/inventory-items/{item['id']}/movements",
        json={"type": "entrada", "quantity": 250},
        headers=headers,
    )
    assert response.status_code == 201, response.text

    refetched = client.get(
        f"/api/v1/organizations/{org_id}/inventory-items/{item['id']}", headers=headers
    ).json()
    assert refetched["quantity_on_hand"] == 750


def test_saida_movement_decreases_stock_and_flags_low_stock(client: TestClient):
    owner = register_user(client, organization_name="Acme Prints", email="owner@acme.io")
    headers = auth_headers(owner["access_token"])
    org_id = _org_id(client, headers)
    item = _create_item(client, org_id, headers, initial_quantity=500, minimum_stock=100)

    response = client.post(
        f"/api/v1/organizations/{org_id}/inventory-items/{item['id']}/movements",
        json={"type": "saida", "quantity": -450},
        headers=headers,
    )
    assert response.status_code == 201, response.text

    refetched = client.get(
        f"/api/v1/organizations/{org_id}/inventory-items/{item['id']}", headers=headers
    ).json()
    assert refetched["quantity_on_hand"] == 50
    assert refetched["is_low_stock"] is True

    low_stock = client.get(
        f"/api/v1/organizations/{org_id}/inventory-items?low_stock_only=true", headers=headers
    ).json()
    assert [i["id"] for i in low_stock] == [item["id"]]


def test_saida_movement_rejects_insufficient_stock(client: TestClient):
    owner = register_user(client, organization_name="Acme Prints", email="owner@acme.io")
    headers = auth_headers(owner["access_token"])
    org_id = _org_id(client, headers)
    item = _create_item(client, org_id, headers, initial_quantity=100)

    response = client.post(
        f"/api/v1/organizations/{org_id}/inventory-items/{item['id']}/movements",
        json={"type": "saida", "quantity": -200},
        headers=headers,
    )
    assert response.status_code == 409

    refetched = client.get(
        f"/api/v1/organizations/{org_id}/inventory-items/{item['id']}", headers=headers
    ).json()
    assert refetched["quantity_on_hand"] == 100


def test_rejects_wrong_sign_for_movement_type(client: TestClient):
    owner = register_user(client, organization_name="Acme Prints", email="owner@acme.io")
    headers = auth_headers(owner["access_token"])
    org_id = _org_id(client, headers)
    item = _create_item(client, org_id, headers)

    response = client.post(
        f"/api/v1/organizations/{org_id}/inventory-items/{item['id']}/movements",
        json={"type": "entrada", "quantity": -100},
        headers=headers,
    )
    assert response.status_code == 422


def test_movement_history_is_listed_newest_first(client: TestClient):
    owner = register_user(client, organization_name="Acme Prints", email="owner@acme.io")
    headers = auth_headers(owner["access_token"])
    org_id = _org_id(client, headers)
    item = _create_item(client, org_id, headers, initial_quantity=500)

    client.post(
        f"/api/v1/organizations/{org_id}/inventory-items/{item['id']}/movements",
        json={"type": "entrada", "quantity": 100},
        headers=headers,
    )
    client.post(
        f"/api/v1/organizations/{org_id}/inventory-items/{item['id']}/movements",
        json={"type": "saida", "quantity": -50},
        headers=headers,
    )

    response = client.get(
        f"/api/v1/organizations/{org_id}/inventory-items/{item['id']}/movements", headers=headers
    )
    assert response.status_code == 200
    movements = response.json()
    assert len(movements) == 2
    assert movements[0]["type"] == "saida"
    assert movements[1]["type"] == "entrada"


def test_viewer_cannot_create_inventory_item(client: TestClient):
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
        f"/api/v1/organizations/{org_id}/inventory-items",
        json={"name": "Not allowed", "category": "filament", "unit": "g"},
        headers=auth_headers(viewer["access_token"]),
    )
    assert response.status_code == 403
