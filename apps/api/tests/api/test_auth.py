from fastapi.testclient import TestClient

from tests.api.conftest import auth_headers, register_user


def test_register_creates_org_and_owner(client: TestClient):
    body = register_user(client, organization_name="Acme Prints", email="owner@acme.io")

    assert body["user"]["email"] == "owner@acme.io"
    assert body["access_token"]
    assert "refresh_token" in client.cookies


def test_register_rejects_duplicate_email(client: TestClient):
    register_user(client, organization_name="Acme Prints", email="owner@acme.io")

    response = client.post(
        "/api/v1/auth/register",
        json={
            "organization_name": "Another Org",
            "email": "owner@acme.io",
            "password": "correct-horse-battery",
        },
    )
    assert response.status_code == 409


def test_login_with_valid_credentials(client: TestClient):
    register_user(
        client, organization_name="Acme Prints", email="owner@acme.io", password="s3cret-pass"
    )

    response = client.post(
        "/api/v1/auth/login", json={"email": "owner@acme.io", "password": "s3cret-pass"}
    )
    assert response.status_code == 200
    assert response.json()["access_token"]


def test_login_with_invalid_password_is_rejected(client: TestClient):
    register_user(
        client, organization_name="Acme Prints", email="owner@acme.io", password="s3cret-pass"
    )

    response = client.post(
        "/api/v1/auth/login", json={"email": "owner@acme.io", "password": "wrong-password"}
    )
    assert response.status_code == 401


def test_me_requires_authentication(client: TestClient):
    response = client.get("/api/v1/users/me")
    assert response.status_code == 401


def test_me_returns_user_and_memberships(client: TestClient):
    body = register_user(client, organization_name="Acme Prints", email="owner@acme.io")

    response = client.get("/api/v1/users/me", headers=auth_headers(body["access_token"]))
    assert response.status_code == 200
    payload = response.json()
    assert payload["user"]["email"] == "owner@acme.io"
    assert len(payload["organizations"]) == 1
    assert payload["organizations"][0]["role"] == "OWNER"
    assert payload["organizations"][0]["organization"]["name"] == "Acme Prints"


def test_refresh_rotates_refresh_token_cookie(client: TestClient):
    register_user(client, organization_name="Acme Prints", email="owner@acme.io")
    old_refresh_cookie = client.cookies.get("refresh_token")

    response = client.post("/api/v1/auth/refresh")
    assert response.status_code == 200
    assert response.json()["access_token"]
    assert client.cookies.get("refresh_token") != old_refresh_cookie


def test_refresh_without_cookie_is_rejected(client: TestClient):
    response = client.post("/api/v1/auth/refresh")
    assert response.status_code == 401


def test_logout_revokes_refresh_token(client: TestClient):
    register_user(client, organization_name="Acme Prints", email="owner@acme.io")

    logout_response = client.post("/api/v1/auth/logout")
    assert logout_response.status_code == 204

    refresh_response = client.post("/api/v1/auth/refresh")
    assert refresh_response.status_code == 401
