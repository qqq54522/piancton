from app.api import dependencies
from app.main import app
from app.schemas.image import SearchResponse
from tests.conftest import login


def test_admin_can_create_list_and_revoke_external_api_key(client):
    csrf = login(client, "admin", "admin-password")
    headers = {"X-CSRF-Token": csrf}

    created_response = client.post(
        "/api/admin/api-keys",
        json={"name": "内容项目", "rate_limit_per_minute": 30},
        headers=headers,
    )
    assert created_response.status_code == 201
    created = created_response.json()
    assert created["secret"].startswith("pk_live_")
    assert created["secretPreview"].startswith("pk_live_")

    listed_response = client.get("/api/admin/api-keys")
    assert listed_response.status_code == 200
    listed = listed_response.json()
    assert listed[0]["id"] == created["id"]
    assert "secret" not in listed[0]

    revoked_response = client.post(
        f"/api/admin/api-keys/{created['id']}/revoke",
        headers=headers,
    )
    assert revoked_response.status_code == 200
    assert revoked_response.json()["status"] == "revoked"

    rejected_response = client.post(
        "/api/public/image-search",
        headers={"Authorization": f"Bearer {created['secret']}"},
        json={"query": "官网首屏教育场景图"},
    )
    assert rejected_response.status_code == 401


def test_public_search_requires_bearer_key(client):
    assert client.post(
        "/api/public/image-search", json={"query": "找一张教育场景图"}
    ).status_code == 401


def test_public_search_accepts_key_and_reuses_search_service(client):
    csrf = login(client, "admin", "admin-password")
    created = client.post(
        "/api/admin/api-keys",
        json={"name": "测试调用方"},
        headers={"X-CSRF-Token": csrf},
    ).json()

    class StubSearchService:
        async def search_async(self, *args, **kwargs):
            return SearchResponse(results=[], match_summary="没有找到匹配图片")

    app.dependency_overrides[dependencies.get_search_service] = lambda: StubSearchService()
    try:
        response = client.post(
            "/api/public/image-search",
            headers={"Authorization": f"Bearer {created['secret']}"},
            json={"query": "找一张官网教育场景图", "limit": 4},
        )
    finally:
        app.dependency_overrides.pop(dependencies.get_search_service, None)
    assert response.status_code == 200
    assert response.json()["results"] == []
