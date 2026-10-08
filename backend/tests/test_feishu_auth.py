from __future__ import annotations

from sqlalchemy import select

from app.models.user import User, UserSession
from app.services.feishu_auth_service import FeishuAuthService


class FakeResponse:
    def __init__(self, payload: dict):
        self.payload = payload

    def raise_for_status(self) -> None:
        return None

    def json(self) -> dict:
        return self.payload


class FakeHttpClient:
    def __init__(self, **_kwargs):
        self.calls: list[tuple[str, str]] = []

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return None

    def post(self, path: str, *, json: dict):
        self.calls.append(("POST", path))
        if path.endswith("/access_token"):
            return FakeResponse({"code": 0, "data": {"access_token": "user-token"}})
        return FakeResponse({"code": 0, "data": {"tenant_access_token": "tenant-token"}})

    def get(self, path: str, *, headers: dict, params: dict | None = None):
        self.calls.append(("GET", path))
        if path.endswith("/user_info"):
            return FakeResponse({
                "code": 0,
                "data": {
                    "open_id": "ou_test",
                    "union_id": "on_test",
                    "user_id": "ouser_test",
                    "tenant_key": "tenant_test",
                    "name": "测试用户",
                },
            })
        if "/users/" in path:
            return FakeResponse({"code": 0, "data": {"user": {"department_ids": ["od_test"]}}})
        return FakeResponse({"code": 0, "data": {"department": {"name": "市场部"}}})


def test_feishu_login_provisions_user_and_snapshots_department(db_factory):
    with db_factory() as db:
        service = FeishuAuthService(
            db,
            enabled=True,
            app_id="cli_test",
            app_secret="secret",
            allowed_tenant_key="tenant_test",
            base_url="https://open.feishu.cn",
            timeout_seconds=1,
            http_client_factory=FakeHttpClient,
        )
        result = service.login("auth-code")
        assert result.user.username == "feishu_ouser_test"
        assert result.user.feishu_display_name == "测试用户"
        assert result.user.feishu_department_names == "市场部"
        assert result.user.feishu_open_id == "ou_test"
        assert result.user.role == "business"

        db.expire_all()
        user = db.scalar(select(User).where(User.feishu_open_id == "ou_test"))
        assert user is not None
        assert user.last_feishu_login_at is not None
        assert db.scalar(select(UserSession).where(UserSession.user_id == user.id)) is not None


def test_feishu_login_reuses_existing_identity(db_factory):
    with db_factory() as db:
        first = FeishuAuthService(
            db,
            enabled=True,
            app_id="cli_test",
            app_secret="secret",
            allowed_tenant_key="tenant_test",
            base_url="https://open.feishu.cn",
            timeout_seconds=1,
            http_client_factory=FakeHttpClient,
        ).login("auth-code")
        second = FeishuAuthService(
            db,
            enabled=True,
            app_id="cli_test",
            app_secret="secret",
            allowed_tenant_key="tenant_test",
            base_url="https://open.feishu.cn",
            timeout_seconds=1,
            http_client_factory=FakeHttpClient,
        ).login("auth-code")
        assert second.user.id == first.user.id
        assert len(list(db.scalars(select(User)))) == 1


def test_feishu_authorization_url_contains_oauth_parameters(db_factory):
    with db_factory() as db:
        service = FeishuAuthService(
            db,
            enabled=True,
            app_id="cli_test",
            app_secret="secret",
            allowed_tenant_key="tenant_test",
            base_url="https://open.feishu.cn",
            timeout_seconds=1,
            http_client_factory=FakeHttpClient,
        )
        url = service.authorization_url(
            redirect_uri="http://118.196.150.130/api/auth/feishu/callback",
            state="state-value",
        )
        assert "client_id=cli_test" in url
        assert "response_type=code" in url
        assert "state=state-value" in url
        assert "redirect_uri=http%3A%2F%2F118.196.150.130" in url
