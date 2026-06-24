from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app import models  # noqa: F401
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

    dependencies.settings.storage_dir = tmp_path / "images"
    dependencies.settings.storage_dir.mkdir()

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
