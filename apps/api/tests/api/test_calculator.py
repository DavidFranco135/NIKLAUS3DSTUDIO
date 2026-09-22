from fastapi.testclient import TestClient

from tests.api.conftest import auth_headers, register_user


def _org_id(client: TestClient, headers: dict) -> str:
    return client.get("/api/v1/organizations", headers=headers).json()[0]["id"]


def _create_cost_profile(client: TestClient, org_id: str, headers: dict, **overrides) -> dict:
    payload = {
        "name": "Padrão",
        "energy_cost_per_kwh": 0.9,
        "labor_cost_per_hour": 20.0,
        "packaging_cost_flat": 3.0,
        "waste_percentage": 5.0,
        "fees_percentage": 3.0,
        "profit_margin_percentage": 40.0,
        "tax_percentage": None,
        "is_default": True,
    }
    payload.update(overrides)
    response = client.post(
        f"/api/v1/organizations/{org_id}/cost-profiles", json=payload, headers=headers
    )
    assert response.status_code == 201, response.text
    return response.json()


def test_create_list_and_get_cost_profile(client: TestClient):
    owner = register_user(client, organization_name="Acme Prints", email="owner@acme.io")
    headers = auth_headers(owner["access_token"])
    org_id = _org_id(client, headers)

    profile = _create_cost_profile(client, org_id, headers)
    assert profile["is_default"] is True

    response = client.get(f"/api/v1/organizations/{org_id}/cost-profiles", headers=headers)
    assert response.status_code == 200
    assert len(response.json()) == 1

    response = client.get(
        f"/api/v1/organizations/{org_id}/cost-profiles/{profile['id']}", headers=headers
    )
    assert response.status_code == 200
    assert response.json()["name"] == "Padrão"


def test_creating_a_second_default_profile_clears_the_first(client: TestClient):
    owner = register_user(client, organization_name="Acme Prints", email="owner@acme.io")
    headers = auth_headers(owner["access_token"])
    org_id = _org_id(client, headers)

    first = _create_cost_profile(client, org_id, headers, name="Padrão")
    second = _create_cost_profile(client, org_id, headers, name="Atacado", is_default=True)

    profiles = {
        p["id"]: p
        for p in client.get(
            f"/api/v1/organizations/{org_id}/cost-profiles", headers=headers
        ).json()
    }
    assert profiles[first["id"]]["is_default"] is False
    assert profiles[second["id"]]["is_default"] is True


def test_create_quote_computes_and_snapshots_the_breakdown(client: TestClient):
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
            "machine_cost_per_hour": 1.5,
            "energy_kwh": 0.4,
            "labor_hours": 0.5,
        },
        headers=headers,
    )
    assert response.status_code == 201, response.text
    quote = response.json()
    assert quote["cost_profile_id"] == profile["id"]
    assert quote["status"] == "draft"
    assert quote["production_cost"] == quote["cost_breakdown_snapshot"]["production_cost"]
    assert quote["suggested_price"] > quote["production_cost"]

    response = client.get(f"/api/v1/organizations/{org_id}/quotes", headers=headers)
    assert response.status_code == 200
    assert len(response.json()) == 1

    response = client.get(
        f"/api/v1/organizations/{org_id}/quotes/{quote['id']}", headers=headers
    )
    assert response.status_code == 200
    assert response.json()["id"] == quote["id"]


def test_quote_snapshot_is_unaffected_by_later_profile_changes(client: TestClient):
    """Auditing guarantee from ARCHITECTURE.md §14: if the cost profile

    changes later, past quotes must not change retroactively — the snapshot
    is what's authoritative, not a live recompute against the profile.
    """
    owner = register_user(client, organization_name="Acme Prints", email="owner@acme.io")
    headers = auth_headers(owner["access_token"])
    org_id = _org_id(client, headers)
    profile = _create_cost_profile(client, org_id, headers, profit_margin_percentage=10.0)

    quote = client.post(
        f"/api/v1/organizations/{org_id}/quotes",
        json={
            "cost_profile_id": profile["id"],
            "material_cost": 100.0,
            "print_time_hours": 0.0,
            "machine_cost_per_hour": 0.0,
            "energy_kwh": 0.0,
            "labor_hours": 0.0,
        },
        headers=headers,
    ).json()
    original_price = quote["suggested_price"]

    # A brand new profile (a later "edit" in spirit) with a much higher margin...
    _create_cost_profile(client, org_id, headers, name="Nova", profit_margin_percentage=90.0)

    refetched = client.get(
        f"/api/v1/organizations/{org_id}/quotes/{quote['id']}", headers=headers
    ).json()
    assert refetched["suggested_price"] == original_price


def test_rejects_quote_with_unknown_cost_profile(client: TestClient):
    owner = register_user(client, organization_name="Acme Prints", email="owner@acme.io")
    headers = auth_headers(owner["access_token"])
    org_id = _org_id(client, headers)

    response = client.post(
        f"/api/v1/organizations/{org_id}/quotes",
        json={
            "cost_profile_id": "00000000-0000-0000-0000-000000000000",
            "material_cost": 10.0,
            "print_time_hours": 1.0,
            "machine_cost_per_hour": 1.0,
            "energy_kwh": 0.1,
            "labor_hours": 0.1,
        },
        headers=headers,
    )
    assert response.status_code == 404


def test_rejects_negative_quote_inputs(client: TestClient):
    owner = register_user(client, organization_name="Acme Prints", email="owner@acme.io")
    headers = auth_headers(owner["access_token"])
    org_id = _org_id(client, headers)
    profile = _create_cost_profile(client, org_id, headers)

    response = client.post(
        f"/api/v1/organizations/{org_id}/quotes",
        json={
            "cost_profile_id": profile["id"],
            "material_cost": -5.0,
            "print_time_hours": 1.0,
            "machine_cost_per_hour": 1.0,
            "energy_kwh": 0.1,
            "labor_hours": 0.1,
        },
        headers=headers,
    )
    assert response.status_code == 422


def test_rejects_project_version_id_without_project_id(client: TestClient):
    owner = register_user(client, organization_name="Acme Prints", email="owner@acme.io")
    headers = auth_headers(owner["access_token"])
    org_id = _org_id(client, headers)
    profile = _create_cost_profile(client, org_id, headers)

    response = client.post(
        f"/api/v1/organizations/{org_id}/quotes",
        json={
            "cost_profile_id": profile["id"],
            "project_version_id": "00000000-0000-0000-0000-000000000000",
            "material_cost": 10.0,
            "print_time_hours": 1.0,
            "machine_cost_per_hour": 1.0,
            "energy_kwh": 0.1,
            "labor_hours": 0.1,
        },
        headers=headers,
    )
    assert response.status_code == 422


def test_viewer_cannot_create_cost_profile(client: TestClient):
    owner = register_user(client, organization_name="Acme Prints", email="owner@acme.io")
    owner_headers = auth_headers(owner["access_token"])
    org_id = _org_id(client, owner_headers)

    viewer = register_user(client, organization_name="Solo Org", email="viewer@acme.io")
    client.post(
        f"/api/v1/organizations/{org_id}/members",
        json={"email": "viewer@acme.io", "role": "VIEWER"},
        headers=owner_headers,
    )
    viewer_headers = auth_headers(viewer["access_token"])

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
        },
        headers=viewer_headers,
    )
    assert response.status_code == 403
