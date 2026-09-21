from fastapi.testclient import TestClient

from tests.api.conftest import auth_headers, register_user
from tests.fakes.fake_storage import FakeStorageProvider

_FAKE_PNG_BYTES = b"\x89PNG\r\n\x1a\nnot-a-real-decoder-but-good-enough-for-this-test"


def _org_id(client: TestClient, headers: dict) -> str:
    return client.get("/api/v1/organizations", headers=headers).json()[0]["id"]


def _create_project(client: TestClient, org_id: str, headers: dict) -> str:
    return client.post(
        f"/api/v1/organizations/{org_id}/projects", json={"name": "Estátua"}, headers=headers
    ).json()["id"]


def _upload_and_confirm_image(
    client: TestClient,
    fake_storage: FakeStorageProvider,
    *,
    org_id: str,
    project_id: str,
    headers: dict,
    image_bytes: bytes = _FAKE_PNG_BYTES,
    mime_type: str = "image/png",
) -> str:
    upload_info = client.post(
        f"/api/v1/organizations/{org_id}/projects/{project_id}/files/upload-url",
        json={"filename": "cachorro.png", "mime_type": mime_type, "kind": "source_image"},
        headers=headers,
    ).json()
    fake_storage.seed(key=upload_info["storage_key"], data=image_bytes, content_type=mime_type)
    client.post(
        f"/api/v1/organizations/{org_id}/projects/{project_id}/files/{upload_info['file_id']}/confirm",
        headers=headers,
    )
    return upload_info["file_id"]


def test_image_job_completes_with_dev_only_mock_and_creates_version(
    client: TestClient, fake_storage: FakeStorageProvider
):
    owner = register_user(client, organization_name="Acme Prints", email="owner@acme.io")
    headers = auth_headers(owner["access_token"])
    org_id = _org_id(client, headers)
    project_id = _create_project(client, org_id, headers)
    image_file_id = _upload_and_confirm_image(
        client, fake_storage, org_id=org_id, project_id=project_id, headers=headers
    )

    response = client.post(
        f"/api/v1/organizations/{org_id}/ai/jobs",
        json={"image_file_id": image_file_id, "project_id": project_id},
        headers=headers,
    )
    assert response.status_code == 202
    job = response.json()

    assert job["task_type"] == "IMAGE_TO_3D"
    assert job["status"] == "COMPLETED"
    assert job["source_image_file_id"] == image_file_id
    assert job["attempts"][0]["provider_name"] == "mock_image_to_3d"
    assert job["result_metadata"]["development_only"] is True
    assert job["result_metadata"]["placeholder"] is True
    assert job["result_project_version_id"] is not None

    project = client.get(
        f"/api/v1/organizations/{org_id}/projects/{project_id}", headers=headers
    ).json()
    assert project["active_version_id"] == job["result_project_version_id"]

    versions = client.get(
        f"/api/v1/organizations/{org_id}/projects/{project_id}/versions", headers=headers
    ).json()
    assert versions[0]["source_type"] == "image_to_3d"


def test_image_job_can_combine_image_with_text_hints(
    client: TestClient, fake_storage: FakeStorageProvider
):
    owner = register_user(client, organization_name="Acme Prints", email="owner@acme.io")
    headers = auth_headers(owner["access_token"])
    org_id = _org_id(client, headers)
    project_id = _create_project(client, org_id, headers)
    image_file_id = _upload_and_confirm_image(
        client, fake_storage, org_id=org_id, project_id=project_id, headers=headers
    )

    response = client.post(
        f"/api/v1/organizations/{org_id}/ai/jobs",
        json={
            "prompt": "cachorro sentado, PLA branco",
            "image_file_id": image_file_id,
            "project_id": project_id,
        },
        headers=headers,
    )
    assert response.status_code == 202
    assert response.json()["task_type"] == "IMAGE_TO_3D"


def test_rejects_image_job_referencing_unconfirmed_upload(client: TestClient):
    owner = register_user(client, organization_name="Acme Prints", email="owner@acme.io")
    headers = auth_headers(owner["access_token"])
    org_id = _org_id(client, headers)
    project_id = _create_project(client, org_id, headers)

    upload_info = client.post(
        f"/api/v1/organizations/{org_id}/projects/{project_id}/files/upload-url",
        json={"filename": "cachorro.png", "mime_type": "image/png", "kind": "source_image"},
        headers=headers,
    ).json()

    response = client.post(
        f"/api/v1/organizations/{org_id}/ai/jobs",
        json={"image_file_id": upload_info["file_id"], "project_id": project_id},
        headers=headers,
    )
    assert response.status_code == 422


def test_rejects_image_job_referencing_non_image_file(
    client: TestClient, fake_storage: FakeStorageProvider
):
    owner = register_user(client, organization_name="Acme Prints", email="owner@acme.io")
    headers = auth_headers(owner["access_token"])
    org_id = _org_id(client, headers)
    project_id = _create_project(client, org_id, headers)

    upload_info = client.post(
        f"/api/v1/organizations/{org_id}/projects/{project_id}/files/upload-url",
        json={"filename": "modelo.stl", "mime_type": "model/stl", "kind": "model_stl"},
        headers=headers,
    ).json()
    fake_storage.seed(
        key=upload_info["storage_key"], data=b"solid x\nendsolid x\n", content_type="model/stl"
    )
    client.post(
        f"/api/v1/organizations/{org_id}/projects/{project_id}/files/{upload_info['file_id']}/confirm",
        headers=headers,
    )

    response = client.post(
        f"/api/v1/organizations/{org_id}/ai/jobs",
        json={"image_file_id": upload_info["file_id"], "project_id": project_id},
        headers=headers,
    )
    assert response.status_code == 422


def test_rejects_job_with_neither_prompt_nor_image(client: TestClient):
    owner = register_user(client, organization_name="Acme Prints", email="owner@acme.io")
    headers = auth_headers(owner["access_token"])
    org_id = _org_id(client, headers)

    response = client.post(
        f"/api/v1/organizations/{org_id}/ai/jobs", json={}, headers=headers
    )
    assert response.status_code == 422


def test_image_job_is_idempotent(client: TestClient, fake_storage: FakeStorageProvider):
    owner = register_user(client, organization_name="Acme Prints", email="owner@acme.io")
    headers = auth_headers(owner["access_token"])
    org_id = _org_id(client, headers)
    project_id = _create_project(client, org_id, headers)
    image_file_id = _upload_and_confirm_image(
        client, fake_storage, org_id=org_id, project_id=project_id, headers=headers
    )

    body = {"image_file_id": image_file_id, "project_id": project_id}
    first = client.post(
        f"/api/v1/organizations/{org_id}/ai/jobs", json=body, headers=headers
    ).json()
    second = client.post(
        f"/api/v1/organizations/{org_id}/ai/jobs", json=body, headers=headers
    ).json()

    assert first["id"] == second["id"]
