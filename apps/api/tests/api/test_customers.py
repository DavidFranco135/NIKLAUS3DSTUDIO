from fastapi.testclient import TestClient

from tests.api.conftest import auth_headers, register_user


def _org_id(client: TestClient, headers: dict) -> str:
    return client.get("/api/v1/organizations", headers=headers).json()[0]["id"]


def _create_customer(client: TestClient, org_id: str, headers: dict, **overrides) -> dict:
    payload = {
        "name": "Carlos Souza",
        "email": "carlos@example.com",
        "phone": "+55 11 99999-0000",
        "document": "123.456.789-00",
        "notes": "Cliente recorrente",
    }
    payload.update(overrides)
    response = client.post(
        f"/api/v1/organizations/{org_id}/customers", json=payload, headers=headers
    )
    assert response.status_code == 201, response.text
    return response.json()


def test_create_list_and_get_customer(client: TestClient):
    owner = register_user(client, organization_name="Acme Prints", email="owner@acme.io")
    headers = auth_headers(owner["access_token"])
    org_id = _org_id(client, headers)

    customer = _create_customer(client, org_id, headers)

    response = client.get(f"/api/v1/organizations/{org_id}/customers", headers=headers)
    assert response.status_code == 200
    assert len(response.json()) == 1

    response = client.get(
        f"/api/v1/organizations/{org_id}/customers/{customer['id']}", headers=headers
    )
    assert response.status_code == 200
    assert response.json()["name"] == "Carlos Souza"


def test_update_customer(client: TestClient):
    owner = register_user(client, organization_name="Acme Prints", email="owner@acme.io")
    headers = auth_headers(owner["access_token"])
    org_id = _org_id(client, headers)
    customer = _create_customer(client, org_id, headers)

    response = client.patch(
        f"/api/v1/organizations/{org_id}/customers/{customer['id']}",
        json={"phone": "+55 11 98888-1111"},
        headers=headers,
    )
    assert response.status_code == 200
    assert response.json()["phone"] == "+55 11 98888-1111"
    assert response.json()["name"] == "Carlos Souza"


def test_soft_deleted_customer_disappears_from_list_and_get(client: TestClient):
    owner = register_user(client, organization_name="Acme Prints", email="owner@acme.io")
    headers = auth_headers(owner["access_token"])
    org_id = _org_id(client, headers)
    customer = _create_customer(client, org_id, headers)

    response = client.delete(
        f"/api/v1/organizations/{org_id}/customers/{customer['id']}", headers=headers
    )
    assert response.status_code == 204

    assert client.get(f"/api/v1/organizations/{org_id}/customers", headers=headers).json() == []
    response = client.get(
        f"/api/v1/organizations/{org_id}/customers/{customer['id']}", headers=headers
    )
    assert response.status_code == 404


def test_project_can_be_linked_to_a_customer(client: TestClient):
    owner = register_user(client, organization_name="Acme Prints", email="owner@acme.io")
    headers = auth_headers(owner["access_token"])
    org_id = _org_id(client, headers)
    customer = _create_customer(client, org_id, headers)

    response = client.post(
        f"/api/v1/organizations/{org_id}/projects",
        json={"name": "Chaveiro Carlos", "customer_id": customer["id"]},
        headers=headers,
    )
    assert response.status_code == 201, response.text
    assert response.json()["customer_id"] == customer["id"]


def test_rejects_project_with_unknown_customer(client: TestClient):
    owner = register_user(client, organization_name="Acme Prints", email="owner@acme.io")
    headers = auth_headers(owner["access_token"])
    org_id = _org_id(client, headers)

    response = client.post(
        f"/api/v1/organizations/{org_id}/projects",
        json={"name": "Sem cliente", "customer_id": "00000000-0000-0000-0000-000000000000"},
        headers=headers,
    )
    assert response.status_code == 404


def test_customer_history_lists_linked_projects_and_quotes(client: TestClient):
    owner = register_user(client, organization_name="Acme Prints", email="owner@acme.io")
    headers = auth_headers(owner["access_token"])
    org_id = _org_id(client, headers)
    customer = _create_customer(client, org_id, headers)

    project = client.post(
        f"/api/v1/organizations/{org_id}/projects",
        json={"name": "Chaveiro Carlos", "customer_id": customer["id"]},
        headers=headers,
    ).json()

    profile = client.post(
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
    ).json()
    quote = client.post(
        f"/api/v1/organizations/{org_id}/quotes",
        json={
            "cost_profile_id": profile["id"],
            "customer_id": customer["id"],
            "material_cost": 10.0,
            "print_time_hours": 1.0,
            "machine_cost_per_hour": 1.0,
            "energy_kwh": 0.1,
            "labor_hours": 0.2,
        },
        headers=headers,
    ).json()

    response = client.get(
        f"/api/v1/organizations/{org_id}/customers/{customer['id']}/history", headers=headers
    )
    assert response.status_code == 200
    history = response.json()
    assert [p["id"] for p in history["projects"]] == [project["id"]]
    assert [q["id"] for q in history["quotes"]] == [quote["id"]]


def test_rejects_quote_with_unknown_customer(client: TestClient):
    owner = register_user(client, organization_name="Acme Prints", email="owner@acme.io")
    headers = auth_headers(owner["access_token"])
    org_id = _org_id(client, headers)
    profile = client.post(
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
    ).json()

    response = client.post(
        f"/api/v1/organizations/{org_id}/quotes",
        json={
            "cost_profile_id": profile["id"],
            "customer_id": "00000000-0000-0000-0000-000000000000",
            "material_cost": 10.0,
            "print_time_hours": 1.0,
            "machine_cost_per_hour": 1.0,
            "energy_kwh": 0.1,
            "labor_hours": 0.2,
        },
        headers=headers,
    )
    assert response.status_code == 404


def test_viewer_cannot_create_customer(client: TestClient):
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
        f"/api/v1/organizations/{org_id}/customers",
        json={"name": "Not allowed"},
        headers=auth_headers(viewer["access_token"]),
    )
    assert response.status_code == 403
