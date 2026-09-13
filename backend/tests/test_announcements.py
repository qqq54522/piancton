from sqlalchemy import select

from app.models.user import AuditLog
from tests.conftest import login


def _write_headers(client, username: str, password: str) -> dict[str, str]:
    csrf = login(client, username, password)
    return {"X-CSRF-Token": csrf, "Origin": "http://localhost:5173"}


def _publish(client, *, title: str, content: str, role: str = "designer") -> dict:
    password = f"{role}-password"
    response = client.post(
        "/api/admin/announcements",
        headers=_write_headers(client, role, password),
        json={"title": title, "content": content},
    )
    assert response.status_code == 201
    return response.json()


def test_business_feed_tracks_read_cursor_without_hiding_newer_messages(
    client,
    db_factory,
):
    first = _publish(client, title="功能更新", content="今天新增了批量上传。")
    second = _publish(client, title="体验优化", content="渠道栏现在支持横向滚动。")

    login(client, "business", "business-password")
    unread = client.get("/api/announcements/unread-count")
    feed = client.get("/api/announcements")
    assert unread.status_code == feed.status_code == 200
    assert unread.json() == {"unreadCount": 2}
    assert [item["id"] for item in feed.json()["items"]] == [second["id"], first["id"]]
    assert feed.json()["unreadCount"] == 2

    third = _publish(client, title="新的公告", content="这条应继续保持未读。", role="admin")
    login(client, "business", "business-password")
    csrf = client.cookies.get("piancton_csrf")
    marked = client.post(
        "/api/announcements/read",
        headers={"X-CSRF-Token": csrf, "Origin": "http://localhost:5173"},
        json={"throughPublishedAt": second["publishedAt"]},
    )
    assert marked.status_code == 200
    assert marked.json() == {"unreadCount": 1}

    feed = client.get("/api/announcements").json()
    assert feed["items"][0]["id"] == third["id"]
    assert feed["unreadCount"] == 1

    marked = client.post(
        "/api/announcements/read",
        headers={"X-CSRF-Token": csrf, "Origin": "http://localhost:5173"},
        json={"throughPublishedAt": "2999-01-01T00:00:00Z"},
    )
    assert marked.json() == {"unreadCount": 0}

    with db_factory() as db:
        audit = db.scalar(select(AuditLog).where(AuditLog.action == "announcement.publish"))
        assert audit is not None
        assert audit.target_type == "announcement"


def test_announcement_permissions_validation_and_new_account_cursor(client):
    _publish(client, title="旧公告", content="新注册用户不应被旧消息打扰。")

    registration = client.post(
        "/api/auth/register",
        json={
            "username": "announcement-new-user",
            "password": "New-user-password-2026!",
            "confirmPassword": "New-user-password-2026!",
        },
    )
    assert registration.status_code == 201
    login(client, "announcement-new-user", "New-user-password-2026!")
    assert client.get("/api/announcements/unread-count").json() == {"unreadCount": 0}

    business_headers = _write_headers(client, "business", "business-password")
    forbidden = client.post(
        "/api/admin/announcements",
        headers=business_headers,
        json={"title": "越权", "content": "不能发布"},
    )
    assert forbidden.status_code == 403

    login(client, "designer", "designer-password")
    assert client.get("/api/announcements").status_code == 403

    no_csrf = client.post(
        "/api/admin/announcements",
        json={"title": "缺少令牌", "content": "不能发布"},
    )
    assert no_csrf.status_code == 403

    invalid = client.post(
        "/api/admin/announcements",
        headers=_write_headers(client, "designer", "designer-password"),
        json={"title": "   ", "content": "有效正文"},
    )
    assert invalid.status_code == 422
