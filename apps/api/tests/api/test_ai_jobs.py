from fastapi.testclient import TestClient

from src.infrastructure.storage import s3_storage as storage_module
from tests.api.conftest import auth_headers, register_user
from tests.fakes.fake_storage import UnavailableStorageProvider


def _org_id(client: TestClient, headers: dict) -> str:
    return client.get("/api/v1/organizations", headers=headers).json()[0]["id"]


def _create_project(client: TestClient, org_id: str, headers: dict) -> str:
    return client.post(
        f"/api/v1/organizations/{org_id}/projects",
        json={"name": "Chaveiro Carlos"},
        headers=headers,
    ).json()["id"]


def test_exact_dimensions_are_routed_to_cad_provider_and_complete(client: TestClient):
    owner = register_user(client, organization_name="Acme Prints", email="owner@acme.io")
    headers = auth_headers(owner["access_token"])
    org_id = _org_id(client, headers)
    project_id = _create_project(client, org_id, headers)

    response = client.post(
        f"/api/v1/organizations/{org_id}/ai/jobs",
        json={
            "prompt": "Crie um chaveiro de 70x35x4mm com o nome CARLOS, furo de 5mm, formato STL.",
            "project_id": project_id,
        },
        headers=headers,
    )
    assert response.status_code == 202
    job = response.json()
    assert job["task_type"] == "PARAMETRIC_CAD"
    assert job["status"] == "COMPLETED"
    assert job["result_project_version_id"] is not None
    assert len(job["attempts"]) == 1
    assert job["attempts"][0]["provider_name"] == "mock_box_cad"
    assert job["attempts"][0]["status"] == "SUCCEEDED"

    project = client.get(
        f"/api/v1/organizations/{org_id}/projects/{project_id}", headers=headers
    ).json()
    assert project["active_version_id"] == job["result_project_version_id"]


def test_vague_prompt_falls_back_to_second_generative_provider(client: TestClient):
    owner = register_user(client, organization_name="Acme Prints", email="owner@acme.io")
    headers = auth_headers(owner["access_token"])
    org_id = _org_id(client, headers)

    response = client.post(
        f"/api/v1/organizations/{org_id}/ai/jobs",
        json={"prompt": "Quero uma estátua de um cachorro sentado"},
        headers=headers,
    )
    assert response.status_code == 202
    job = response.json()
    assert job["task_type"] == "TEXT_TO_GENERATIVE_3D"
    assert job["status"] == "COMPLETED"
    assert len(job["attempts"]) == 2
    assert job["attempts"][0]["status"] == "FAILED"
    assert job["attempts"][0]["provider_name"] == "mock_generative_unavailable"
    assert job["attempts"][1]["status"] == "SUCCEEDED"
    assert job["attempts"][1]["provider_name"] == "mock_generative_placeholder"


def test_resubmitting_the_same_prompt_is_idempotent(client: TestClient):
    owner = register_user(client, organization_name="Acme Prints", email="owner@acme.io")
    headers = auth_headers(owner["access_token"])
    org_id = _org_id(client, headers)
    project_id = _create_project(client, org_id, headers)

    first = client.post(
        f"/api/v1/organizations/{org_id}/ai/jobs",
        json={"prompt": "Chaveiro 60x30x4mm nome MARIA", "project_id": project_id},
        headers=headers,
    ).json()
    second = client.post(
        f"/api/v1/organizations/{org_id}/ai/jobs",
        json={"prompt": "Chaveiro 60x30x4mm nome MARIA", "project_id": project_id},
        headers=headers,
    ).json()

    assert first["id"] == second["id"]

    jobs = client.get(f"/api/v1/organizations/{org_id}/ai/jobs", headers=headers).json()
    assert len(jobs) == 1


def test_viewer_cannot_create_ai_job(client: TestClient):
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
        f"/api/v1/organizations/{org_id}/ai/jobs",
        json={"prompt": "Chaveiro 60x30x4mm nome MARIA"},
        headers=auth_headers(viewer["access_token"]),
    )
    assert response.status_code == 403


def test_outsider_cannot_list_ai_jobs(client: TestClient):
    owner = register_user(client, organization_name="Acme Prints", email="owner@acme.io")
    owner_headers = auth_headers(owner["access_token"])
    org_id = _org_id(client, owner_headers)

    outsider = register_user(client, organization_name="Outsider Org", email="outsider@rival.io")

    response = client.get(
        f"/api/v1/organizations/{org_id}/ai/jobs", headers=auth_headers(outsider["access_token"])
    )
    assert response.status_code == 403


def test_job_fails_gracefully_when_storage_is_unreachable(client: TestClient):
    owner = register_user(client, organization_name="Acme Prints", email="owner@acme.io")
    headers = auth_headers(owner["access_token"])
    org_id = _org_id(client, headers)
    project_id = _create_project(client, org_id, headers)

    original_get_storage_provider = storage_module.get_storage_provider
    storage_module.get_storage_provider = lambda: UnavailableStorageProvider()
    try:
        response = client.post(
            f"/api/v1/organizations/{org_id}/ai/jobs",
            json={"prompt": "Chaveiro 70x35x4mm nome PEDRO", "project_id": project_id},
            headers=headers,
        )
    finally:
        storage_module.get_storage_provider = original_get_storage_provider

    assert response.status_code == 202
    job = response.json()
    assert job["status"] == "FAILED"
    assert "Could not connect to storage" in job["error_message"]
    assert job["attempts"][0]["status"] == "SUCCEEDED"
