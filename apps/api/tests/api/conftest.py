import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from src.infrastructure.db import models  # noqa: F401  (registers tables on Base.metadata)
from src.infrastructure.db import session as db_session_module
from src.infrastructure.db.base import Base
from src.infrastructure.storage import s3_storage as storage_module
from src.interfaces.http.dependencies import get_db, get_storage
from src.main import app
from tests.fakes.fake_storage import FakeStorageProvider


@pytest.fixture()
def fake_storage() -> FakeStorageProvider:
    return FakeStorageProvider()


@pytest.fixture()
def client(fake_storage: FakeStorageProvider) -> TestClient:
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    TestSessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)

    def override_get_db():
        db = TestSessionLocal()
        try:
            yield db
        finally:
            db.close()

    # Celery tasks (run synchronously in-process here, via CELERY_TASK_ALWAYS_EAGER)
    # open their own DB session / storage provider outside FastAPI's DI, so they
    # need these two module-level singletons patched directly.
    original_session_local = db_session_module.SessionLocal
    original_get_storage_provider = storage_module.get_storage_provider
    db_session_module.SessionLocal = TestSessionLocal
    storage_module.get_storage_provider = lambda: fake_storage

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_storage] = lambda: fake_storage
    try:
        with TestClient(app) as test_client:
            yield test_client
    finally:
        app.dependency_overrides.clear()
        db_session_module.SessionLocal = original_session_local
        storage_module.get_storage_provider = original_get_storage_provider


def register_user(
    client: TestClient,
    *,
    organization_name: str,
    email: str,
    password: str = "correct-horse-battery",
) -> dict:
    response = client.post(
        "/api/v1/auth/register",
        json={
            "organization_name": organization_name,
            "email": email,
            "password": password,
            "full_name": "Test User",
        },
    )
    assert response.status_code == 201, response.text
    return response.json()


def auth_headers(access_token: str) -> dict:
    return {"Authorization": f"Bearer {access_token}"}
