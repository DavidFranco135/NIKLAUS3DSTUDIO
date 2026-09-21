import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from src.infrastructure.db import models  # noqa: F401  (registers tables on Base.metadata)
from src.infrastructure.db.base import Base
from src.interfaces.http.dependencies import get_db
from src.main import app


@pytest.fixture()
def client() -> TestClient:
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

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


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
