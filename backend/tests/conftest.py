from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app import models  # noqa: F401
from app.ai.contracts import ModelCallResult
from app.api.dependencies import get_db
from app.core.security import hash_password
from app.db.base import Base
from app.main import app
from app.models.user import User


@pytest.fixture()
def db_factory():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, expire_on_commit=False)
    try:
        yield factory
    finally:
        Base.metadata.drop_all(engine)


@pytest.fixture()
def client(db_factory, tmp_path: Path, monkeypatch):
    from app.api import dependencies

    storage_dir = tmp_path / "images"
    storage_dir.mkdir()
    monkeypatch.setattr(dependencies.settings, "storage_dir", storage_dir)
    monkeypatch.setattr(dependencies.settings, "search_backend", "database")
    monkeypatch.setattr(dependencies.settings, "meilisearch_url", "")
    monkeypatch.setattr(dependencies.settings, "meilisearch_api_key", "")
    monkeypatch.setattr(dependencies.settings, "embedding_base_url", "")
    monkeypatch.setattr(dependencies.settings, "embedding_api_key", "")
    monkeypatch.setattr(dependencies.settings, "embedding_model_name", "")
    monkeypatch.setattr(dependencies.settings, "reranker_base_url", "")
    monkeypatch.setattr(dependencies.settings, "reranker_api_key", "")
    monkeypatch.setattr(dependencies.settings, "reranker_model_name", "")

    def override_db():
        with db_factory() as db:
            yield db

    with db_factory() as db:
        db.add(
            User(
                username="admin",
                password_hash=hash_password("admin-password"),
                role="admin",
            )
        )
        db.add(
            User(
                username="business",
                password_hash=hash_password("business-password"),
                role="business",
            )
        )
        db.add(
            User(
                username="designer",
                password_hash=hash_password("designer-password"),
                role="designer",
            )
        )
        db.commit()
    app.dependency_overrides[get_db] = override_db
    app.dependency_overrides[dependencies.get_db_session_factory] = lambda: db_factory
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


def login(client: TestClient, username: str, password: str) -> str:
    response = client.post("/api/auth/login", json={"username": username, "password": password})
    assert response.status_code == 200
    return response.json()["csrfToken"]


class ModelProviderStub:
    """Test-only adapter that follows the production Provider contract."""

    name = "test"
    configured = True

    def generate_validated_json(self, request, validator):
        call = self.generate_json(request)
        return ModelCallResult(validator(call.value), call.attempts)
