from datetime import datetime

import pytest
from sqlalchemy import select

from app.core.security import verify_password
from app.models.user import AuditLog, User
from tests.conftest import login


def registration(**overrides):
    return {"username": "new-user", "password": "new-password",
            "confirmPassword": "new-password", **overrides}


def test_register_then_login_with_business_permissions(client, db_factory):
    response = client.post("/api/auth/register", json=registration(username=" new-user "))
    assert response.status_code == 201
    assert response.json()["username"] == "new-user"
    assert response.json()["role"] == "business"
    assert response.json()["isActive"] is True
    assert response.json()["onboardingCompletedAt"] is None
    assert "password" not in response.text.lower()
    assert client.get("/api/auth/me").status_code == 401
    with db_factory() as db:
        user = db.scalar(select(User).where(User.username == "new-user"))
        assert user is not None
        assert user.password_hash != "new-password"
        assert verify_password(user.password_hash, "new-password")
        audit = db.scalar(select(AuditLog).where(AuditLog.action == "auth.register"))
        assert audit is not None
        assert audit.actor_user_id == user.id
    csrf = login(client, "new-user", "new-password")
    me_response = client.get("/api/auth/me")
    assert me_response.status_code == 200
    assert me_response.json()["onboardingCompletedAt"] is None
    assert client.post("/api/auth/onboarding/complete").status_code == 403
    completed = client.post(
        "/api/auth/onboarding/complete",
        headers={"X-CSRF-Token": csrf},
    )
    assert completed.status_code == 200
    assert completed.json()["onboardingCompletedAt"] is not None
    completed_at = completed.json()["onboardingCompletedAt"]
    repeated = client.post(
        "/api/auth/onboarding/complete",
        headers={"X-CSRF-Token": csrf},
    )
    assert repeated.status_code == 200
    completed_datetime = datetime.fromisoformat(completed_at.replace("Z", "+00:00")).replace(
        tzinfo=None
    )
    repeated_datetime = datetime.fromisoformat(
        repeated.json()["onboardingCompletedAt"].replace("Z", "+00:00")
    ).replace(tzinfo=None)
    assert repeated_datetime == completed_datetime
    assert client.get("/api/auth/me").json()["onboardingCompletedAt"] is not None
    assert client.get("/api/images").status_code == 200
    assert client.get("/api/admin/users").status_code == 403
    assert client.post("/api/images/upload", headers={"X-CSRF-Token": csrf}).status_code == 403


def test_duplicate_registration_keeps_original_account(client):
    response = client.post("/api/auth/register", json=registration(username=" admin "))
    assert response.status_code == 409
    assert response.json()["code"] == "username_exists"
    login(client, "admin", "admin-password")
    assert client.get("/api/auth/me").json()["role"] == "admin"


@pytest.mark.parametrize("overrides", [
    {"username": "   "}, {"username": " ab "}, {"username": "x" * 101},
    {"password": "short", "confirmPassword": "short"},
    {"password": " " * 8, "confirmPassword": " " * 8},
    {"password": "x" * 201, "confirmPassword": "x" * 201},
    {"confirmPassword": "different-password"}, {"role": "admin"},
    {"isActive": True},
])
def test_invalid_registration_does_not_create_account(client, db_factory, overrides):
    assert client.post("/api/auth/register", json=registration(**overrides)).status_code == 422
    with db_factory() as db:
        assert len(list(db.scalars(select(User)))) == 3
