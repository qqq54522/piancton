from io import BytesIO

from PIL import Image as PillowImage

from app.models.usage import UserUsageEvent
from tests.conftest import login


def png_file(width: int = 8, height: int = 4) -> bytes:
    output = BytesIO()
    PillowImage.new("RGB", (width, height), "green").save(output, format="PNG")
    return output.getvalue()


def headers_for(client, username: str, password: str) -> dict[str, str]:
    csrf = login(client, username, password)
    return {"X-CSRF-Token": csrf, "Origin": "http://localhost:5173"}


def upload(client, headers, title: str = "usage") -> dict:
    response = client.post(
        "/api/images/upload",
        headers=headers,
        files={"file": (f"{title}.png", png_file(), "image/png")},
        data={"title": title, "channel": "PPT", "autoAnalyze": "false"},
    )
    assert response.status_code == 201
    return response.json()


def test_login_page_view_and_download_events_are_aggregated(client, db_factory):
    admin_headers = headers_for(client, "admin", "admin-password")
    image = upload(client, admin_headers)

    page_view = client.post(
        "/api/usage/page-view",
        headers=admin_headers,
        json={"path": "/admin/users", "title": "用户管理"},
    )
    assert page_view.status_code == 204
    assert client.get(image["downloadUrl"]).status_code == 200

    summary = client.get(
        "/api/admin/usage/summary",
        headers=admin_headers,
        params={"days": 1},
    )

    assert summary.status_code == 200
    payload = summary.json()
    assert payload["totals"]["loginCount"] >= 1
    assert payload["totals"]["pageViewCount"] == 1
    assert payload["totals"]["downloadCount"] == 1
    admin_usage = next(item for item in payload["users"] if item["username"] == "admin")
    assert admin_usage["loginCount"] >= 1
    assert admin_usage["pageViewCount"] == 1
    assert admin_usage["downloadCount"] == 1
    assert {item["eventType"] for item in payload["recentEvents"]} >= {
        "login",
        "page_view",
        "download",
    }

    with db_factory() as db:
        events = db.query(UserUsageEvent).all()

    assert {event.event_type for event in events} >= {"login", "page_view", "download"}


def test_usage_summary_is_admin_only(client):
    business_headers = headers_for(client, "business", "business-password")

    response = client.get("/api/admin/usage/summary", headers=business_headers)

    assert response.status_code == 403


def test_for_you_feed_is_business_only_and_falls_back_to_all_channels(client):
    business_headers = headers_for(client, "business", "business-password")

    response = client.get("/api/images/for-you", headers=business_headers)

    assert response.status_code == 200
    payload = response.json()
    assert payload["source"] == "local_fallback"
    assert payload["evaluation"]["strategyMode"] == "learning"

    admin_headers = headers_for(client, "admin", "admin-password")
    forbidden = client.get("/api/images/for-you", headers=admin_headers)
    assert forbidden.status_code == 403


def test_search_interaction_is_linked_to_search_and_user(client):
    business_headers = headers_for(client, "business", "business-password")
    response = client.post(
        "/api/usage/search-interaction",
        headers=business_headers,
        json={
            "searchLogId": "search-log-1",
            "keyword": "拍题精学",
            "action": "open_detail",
            "resultImageId": "image-1",
            "assetGroupId": "asset-1",
            "position": 2,
        },
    )
    assert response.status_code == 204

    admin_headers = headers_for(client, "admin", "admin-password")
    summary = client.get(
        "/api/admin/search-ops/activity-summary",
        headers=admin_headers,
        params={"days": 1},
    )
    assert summary.status_code == 200
    payload = summary.json()
    assert payload["interactionCount"] == 1
    interaction = payload["recentInteractions"][0]
    assert interaction["searchLogId"] == "search-log-1"
    assert interaction["actorUsername"] == "business"
    assert interaction["keyword"] == "拍题精学"
    assert interaction["action"] == "open_detail"
    assert interaction["position"] == 2
    assert payload["recommendationEvaluation"]["strategyMode"] == "learning"
