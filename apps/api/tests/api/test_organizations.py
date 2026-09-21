from fastapi.testclient import TestClient

from tests.api.conftest import auth_headers, register_user


def test_create_and_list_organizations(client: TestClient):
    owner = register_user(client, organization_name="Acme Prints", email="owner@acme.io")
    headers = auth_headers(owner["access_token"])

    response = client.post(
        "/api/v1/organizations", json={"name": "Side Hustle Prints"}, headers=headers
    )
    assert response.status_code == 201

    response = client.get("/api/v1/organizations", headers=headers)
    assert response.status_code == 200
    names = {org["name"] for org in response.json()}
    assert names == {"Acme Prints", "Side Hustle Prints"}


def test_add_member_by_email_and_list_members(client: TestClient):
    owner = register_user(client, organization_name="Acme Prints", email="owner@acme.io")
    owner_headers = auth_headers(owner["access_token"])
    org_id = client.get("/api/v1/organizations", headers=owner_headers).json()[0]["id"]

    register_user(client, organization_name="Solo Org", email="member@acme.io")

    response = client.post(
        f"/api/v1/organizations/{org_id}/members",
        json={"email": "member@acme.io", "role": "MANAGER"},
        headers=owner_headers,
    )
    assert response.status_code == 201
    assert response.json()["role"] == "MANAGER"

    response = client.get(f"/api/v1/organizations/{org_id}/members", headers=owner_headers)
    assert response.status_code == 200
    emails = {m["email"] for m in response.json()}
    assert emails == {"owner@acme.io", "member@acme.io"}


def test_add_member_with_unknown_email_returns_404(client: TestClient):
    owner = register_user(client, organization_name="Acme Prints", email="owner@acme.io")
    owner_headers = auth_headers(owner["access_token"])
    org_id = client.get("/api/v1/organizations", headers=owner_headers).json()[0]["id"]

    response = client.post(
        f"/api/v1/organizations/{org_id}/members",
        json={"email": "ghost@nowhere.io", "role": "OPERATOR"},
        headers=owner_headers,
    )
    assert response.status_code == 404


def test_add_member_twice_returns_409(client: TestClient):
    owner = register_user(client, organization_name="Acme Prints", email="owner@acme.io")
    owner_headers = auth_headers(owner["access_token"])
    org_id = client.get("/api/v1/organizations", headers=owner_headers).json()[0]["id"]
    register_user(client, organization_name="Solo Org", email="member@acme.io")

    client.post(
        f"/api/v1/organizations/{org_id}/members",
        json={"email": "member@acme.io", "role": "OPERATOR"},
        headers=owner_headers,
    )
    response = client.post(
        f"/api/v1/organizations/{org_id}/members",
        json={"email": "member@acme.io", "role": "OPERATOR"},
        headers=owner_headers,
    )
    assert response.status_code == 409


def test_manager_cannot_add_members(client: TestClient):
    owner = register_user(client, organization_name="Acme Prints", email="owner@acme.io")
    owner_headers = auth_headers(owner["access_token"])
    org_id = client.get("/api/v1/organizations", headers=owner_headers).json()[0]["id"]

    manager = register_user(client, organization_name="Solo Org", email="manager@acme.io")
    client.post(
        f"/api/v1/organizations/{org_id}/members",
        json={"email": "manager@acme.io", "role": "MANAGER"},
        headers=owner_headers,
    )

    response = client.post(
        f"/api/v1/organizations/{org_id}/members",
        json={"email": "ghost@nowhere.io", "role": "OPERATOR"},
        headers=auth_headers(manager["access_token"]),
    )
    assert response.status_code == 403


def test_cannot_remove_last_owner(client: TestClient):
    owner = register_user(client, organization_name="Acme Prints", email="owner@acme.io")
    owner_headers = auth_headers(owner["access_token"])
    org_id = client.get("/api/v1/organizations", headers=owner_headers).json()[0]["id"]
    owner_user_id = client.get("/api/v1/users/me", headers=owner_headers).json()["user"]["id"]

    response = client.delete(
        f"/api/v1/organizations/{org_id}/members/{owner_user_id}", headers=owner_headers
    )
    assert response.status_code == 409


def test_outsider_cannot_access_another_organization(client: TestClient):
    owner = register_user(client, organization_name="Acme Prints", email="owner@acme.io")
    owner_headers = auth_headers(owner["access_token"])
    org_a_id = client.get("/api/v1/organizations", headers=owner_headers).json()[0]["id"]

    outsider = register_user(client, organization_name="Outsider Org", email="outsider@rival.io")
    outsider_headers = auth_headers(outsider["access_token"])

    response = client.get(f"/api/v1/organizations/{org_a_id}/members", headers=outsider_headers)
    assert response.status_code == 403

    response = client.post(
        f"/api/v1/organizations/{org_a_id}/members",
        json={"email": "outsider@rival.io", "role": "OWNER"},
        headers=outsider_headers,
    )
    assert response.status_code == 403
