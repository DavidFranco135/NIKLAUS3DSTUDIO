from fastapi.testclient import TestClient

from src.interfaces.http.dependencies import get_storage
from src.main import app
from tests.api.conftest import auth_headers, register_user
from tests.fakes.fake_storage import UnavailableStorageProvider


def _org_id(client: TestClient, headers: dict) -> str:
    return client.get("/api/v1/organizations", headers=headers).json()[0]["id"]


def test_create_list_and_get_project(client: TestClient):
    owner = register_user(client, organization_name="Acme Prints", email="owner@acme.io")
    headers = auth_headers(owner["access_token"])
    org_id = _org_id(client, headers)

    response = client.post(
        f"/api/v1/organizations/{org_id}/projects",
        json={"name": "Chaveiro Carlos", "description": "70x35x4mm"},
        headers=headers,
    )
    assert response.status_code == 201
    project = response.json()
    assert project["status"] == "draft"
    assert project["active_version_id"] is None

    response = client.get(f"/api/v1/organizations/{org_id}/projects", headers=headers)
    assert response.status_code == 200
    assert len(response.json()) == 1

    response = client.get(
        f"/api/v1/organizations/{org_id}/projects/{project['id']}", headers=headers
    )
    assert response.status_code == 200
    assert response.json()["name"] == "Chaveiro Carlos"


def test_update_and_soft_delete_project(client: TestClient):
    owner = register_user(client, organization_name="Acme Prints", email="owner@acme.io")
    headers = auth_headers(owner["access_token"])
    org_id = _org_id(client, headers)
    project_id = client.post(
        f"/api/v1/organizations/{org_id}/projects", json={"name": "P1"}, headers=headers
    ).json()["id"]

    response = client.patch(
        f"/api/v1/organizations/{org_id}/projects/{project_id}",
        json={"status": "in_progress"},
        headers=headers,
    )
    assert response.status_code == 200
    assert response.json()["status"] == "in_progress"

    response = client.delete(
        f"/api/v1/organizations/{org_id}/projects/{project_id}", headers=headers
    )
    assert response.status_code == 204

    response = client.get(f"/api/v1/organizations/{org_id}/projects/{project_id}", headers=headers)
    assert response.status_code == 404


def test_viewer_cannot_create_project(client: TestClient):
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
        f"/api/v1/organizations/{org_id}/projects",
        json={"name": "Not allowed"},
        headers=auth_headers(viewer["access_token"]),
    )
    assert response.status_code == 403


def test_full_upload_and_version_flow(client: TestClient):
    owner = register_user(client, organization_name="Acme Prints", email="owner@acme.io")
    headers = auth_headers(owner["access_token"])
    org_id = _org_id(client, headers)
    project_id = client.post(
        f"/api/v1/organizations/{org_id}/projects",
        json={"name": "Chaveiro Carlos"},
        headers=headers,
    ).json()["id"]

    response = client.post(
        f"/api/v1/organizations/{org_id}/projects/{project_id}/files/upload-url",
        json={"filename": "carlos.stl", "mime_type": "model/stl", "kind": "model_stl"},
        headers=headers,
    )
    assert response.status_code == 201
    upload_info = response.json()
    assert upload_info["upload_url"]
    file_id = upload_info["file_id"]

    response = client.post(
        f"/api/v1/organizations/{org_id}/projects/{project_id}/files/{file_id}/confirm",
        headers=headers,
    )
    assert response.status_code == 200
    assert response.json()["status"] == "uploaded"

    response = client.post(
        f"/api/v1/organizations/{org_id}/projects/{project_id}/versions",
        json={"file_id": file_id, "label": "v1"},
        headers=headers,
    )
    assert response.status_code == 201
    version = response.json()
    assert version["version_number"] == 1

    response = client.get(f"/api/v1/organizations/{org_id}/projects/{project_id}", headers=headers)
    assert response.json()["active_version_id"] == version["id"]

    response = client.get(
        f"/api/v1/organizations/{org_id}/projects/{project_id}/versions", headers=headers
    )
    assert len(response.json()) == 1

    response = client.get(
        f"/api/v1/organizations/{org_id}/projects/{project_id}/files/{file_id}/download-url",
        headers=headers,
    )
    assert response.status_code == 200
    assert response.json()["download_url"]

    response = client.get(
        f"/api/v1/organizations/{org_id}/projects/{project_id}/versions/{version['id']}/files",
        headers=headers,
    )
    assert response.status_code == 200
    assert [f["id"] for f in response.json()] == [file_id]


def test_confirm_upload_returns_503_when_storage_is_unreachable(client: TestClient):
    owner = register_user(client, organization_name="Acme Prints", email="owner@acme.io")
    headers = auth_headers(owner["access_token"])
    org_id = _org_id(client, headers)
    project_id = client.post(
        f"/api/v1/organizations/{org_id}/projects", json={"name": "P1"}, headers=headers
    ).json()["id"]
    file_id = client.post(
        f"/api/v1/organizations/{org_id}/projects/{project_id}/files/upload-url",
        json={"filename": "carlos.stl", "mime_type": "model/stl", "kind": "model_stl"},
        headers=headers,
    ).json()["file_id"]

    app.dependency_overrides[get_storage] = lambda: UnavailableStorageProvider()
    try:
        response = client.post(
            f"/api/v1/organizations/{org_id}/projects/{project_id}/files/{file_id}/confirm",
            headers=headers,
        )
    finally:
        del app.dependency_overrides[get_storage]

    assert response.status_code == 503


def test_create_version_fails_without_confirmed_upload(client: TestClient):
    owner = register_user(client, organization_name="Acme Prints", email="owner@acme.io")
    headers = auth_headers(owner["access_token"])
    org_id = _org_id(client, headers)
    project_id = client.post(
        f"/api/v1/organizations/{org_id}/projects", json={"name": "P1"}, headers=headers
    ).json()["id"]

    upload_info = client.post(
        f"/api/v1/organizations/{org_id}/projects/{project_id}/files/upload-url",
        json={"filename": "carlos.stl", "mime_type": "model/stl", "kind": "model_stl"},
        headers=headers,
    ).json()

    response = client.post(
        f"/api/v1/organizations/{org_id}/projects/{project_id}/versions",
        json={"file_id": upload_info["file_id"], "label": "v1"},
        headers=headers,
    )
    assert response.status_code == 409


def test_second_version_and_activate_older(client: TestClient):
    owner = register_user(client, organization_name="Acme Prints", email="owner@acme.io")
    headers = auth_headers(owner["access_token"])
    org_id = _org_id(client, headers)
    project_id = client.post(
        f"/api/v1/organizations/{org_id}/projects", json={"name": "P1"}, headers=headers
    ).json()["id"]

    def upload_and_create_version(label: str) -> dict:
        upload_info = client.post(
            f"/api/v1/organizations/{org_id}/projects/{project_id}/files/upload-url",
            json={"filename": f"{label}.stl", "mime_type": "model/stl", "kind": "model_stl"},
            headers=headers,
        ).json()
        client.post(
            f"/api/v1/organizations/{org_id}/projects/{project_id}/files/{upload_info['file_id']}/confirm",
            headers=headers,
        )
        return client.post(
            f"/api/v1/organizations/{org_id}/projects/{project_id}/versions",
            json={"file_id": upload_info["file_id"], "label": label},
            headers=headers,
        ).json()

    version_1 = upload_and_create_version("v1")
    version_2 = upload_and_create_version("v2")
    assert version_2["version_number"] == 2

    response = client.post(
        f"/api/v1/organizations/{org_id}/projects/{project_id}/versions/{version_1['id']}/activate",
        headers=headers,
    )
    assert response.status_code == 200
    assert response.json()["active_version_id"] == version_1["id"]


def test_outsider_cannot_see_or_create_projects(client: TestClient):
    owner = register_user(client, organization_name="Acme Prints", email="owner@acme.io")
    owner_headers = auth_headers(owner["access_token"])
    org_id = _org_id(client, owner_headers)

    outsider = register_user(client, organization_name="Outsider Org", email="outsider@rival.io")
    outsider_headers = auth_headers(outsider["access_token"])

    response = client.get(f"/api/v1/organizations/{org_id}/projects", headers=outsider_headers)
    assert response.status_code == 403

    response = client.post(
        f"/api/v1/organizations/{org_id}/projects",
        json={"name": "Sneaky"},
        headers=outsider_headers,
    )
    assert response.status_code == 403
