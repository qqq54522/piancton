from io import BytesIO

from PIL import Image as PillowImage

from app.core.security import hash_password
from app.models.usage import AiSearchBehaviorEvent, UserUsageEvent
from app.models.user import User
from app.services.usage_analytics_service import UsageAnalyticsService
from tests.conftest import login


def _png_file() -> bytes:
    output = BytesIO()
    PillowImage.new("RGB", (10, 8), "blue").save(output, format="PNG")
    return output.getvalue()


def _headers(client, username: str, password: str) -> dict[str, str]:
    csrf = login(client, username, password)
    return {"X-CSRF-Token": csrf, "Origin": "http://localhost:5173"}


def _upload(client, title: str = "收藏测试素材") -> dict:
    headers = _headers(client, "admin", "admin-password")
    response = client.post(
        "/api/images/upload",
        headers=headers,
        files={"file": (f"{title}.png", _png_file(), "image/png")},
        data={"title": title, "channel": "PPT", "autoAnalyze": "false"},
    )
    assert response.status_code == 201
    return response.json()


def _context(image: dict, source: str = "home_for_you") -> dict:
    return {
        "imageId": image["id"],
        "source": source,
        "position": 1,
        "keyword": "常用素材",
    }


def _delete_json(client, path: str, *, headers: dict, payload: dict):
    return client.request("DELETE", path, headers=headers, json=payload)


def test_like_and_boards_are_private_persistent_and_deduplicate_behavior_weight(
    client,
    db_factory,
):
    image = _upload(client)
    group_id = image["assetGroupId"]
    headers = _headers(client, "business", "business-password")

    first_like = client.put(
        f"/api/me/asset-collections/likes/{group_id}",
        headers=headers,
        json=_context(image),
    )
    duplicate_like = client.put(
        f"/api/me/asset-collections/likes/{group_id}",
        headers=headers,
        json=_context(image),
    )
    assert first_like.status_code == duplicate_like.status_code == 200
    assert first_like.json()["liked"] is True

    board = client.post(
        "/api/me/asset-collections/boards",
        headers=headers,
        json={"name": " 秋季   家长会 "},
    )
    assert board.status_code == 201
    board_id = board.json()["id"]
    assert board.json()["name"] == "秋季 家长会"

    added = client.put(
        f"/api/me/asset-collections/boards/{board_id}/items/{group_id}",
        headers=headers,
        json=_context(image),
    )
    assert added.status_code == 200
    assert added.json() == {
        "assetGroupId": group_id,
        "liked": True,
        "boardIds": [board_id],
    }

    summary = client.get("/api/me/asset-collections/summary", headers=headers).json()
    likes = client.get("/api/me/asset-collections/likes", headers=headers).json()
    board_items = client.get(
        f"/api/me/asset-collections/boards/{board_id}/items", headers=headers
    ).json()
    assert summary["likedAssetGroupIds"] == [group_id]
    assert summary["likedCount"] == 1
    assert summary["boards"][0]["itemCount"] == 1
    assert likes["items"][0]["image"]["id"] == image["id"]
    assert board_items["items"][0]["assetGroupId"] == group_id

    with db_factory() as db:
        outbox = db.query(AiSearchBehaviorEvent).all()
        assert [(item.event_type, item.item_id) for item in outbox] == [
            ("favorite", image["id"])
        ]

    unliked = _delete_json(
        client,
        f"/api/me/asset-collections/likes/{group_id}",
        headers=headers,
        payload=_context(image),
    )
    assert unliked.status_code == 200
    assert unliked.json()["liked"] is False
    assert unliked.json()["boardIds"] == [board_id]

    removed = _delete_json(
        client,
        f"/api/me/asset-collections/boards/{board_id}/items/{group_id}",
        headers=headers,
        payload=_context(image),
    )
    assert removed.status_code == 200
    assert removed.json()["boardIds"] == []

    with db_factory() as db:
        outbox = db.query(AiSearchBehaviorEvent).order_by(AiSearchBehaviorEvent.created_at).all()
        assert [item.event_type for item in outbox] == ["favorite", "unfavorite"]
        actions = [
            event.details_json
            for event in db.query(UserUsageEvent)
            .filter(UserUsageEvent.event_type == "asset_collection")
            .all()
        ]
        assert len(actions) == 4


def test_board_access_is_scoped_to_current_user(client, db_factory):
    image = _upload(client, "私有画板素材")
    owner_headers = _headers(client, "business", "business-password")
    board = client.post(
        "/api/me/asset-collections/boards",
        headers=owner_headers,
        json={"name": "仅自己可见"},
    ).json()

    with db_factory() as db:
        db.add(
            User(
                username="business-two",
                password_hash=hash_password("business-two-password"),
                role="business",
            )
        )
        db.commit()
    other_headers = _headers(client, "business-two", "business-two-password")

    assert client.get(
        f"/api/me/asset-collections/boards/{board['id']}/items",
        headers=other_headers,
    ).status_code == 404
    assert client.put(
        f"/api/me/asset-collections/boards/{board['id']}/items/{image['assetGroupId']}",
        headers=other_headers,
        json=_context(image),
    ).status_code == 404
    assert client.delete(
        f"/api/me/asset-collections/boards/{board['id']}",
        headers=other_headers,
    ).status_code == 404


def test_internal_account_collection_stays_local_and_export_selection_is_not_favorite(
    client,
    db_factory,
):
    image = _upload(client, "内部收藏测试")
    admin_headers = _headers(client, "admin", "admin-password")
    response = client.put(
        f"/api/me/asset-collections/likes/{image['assetGroupId']}",
        headers=admin_headers,
        json=_context(image, source="library_browse"),
    )
    assert response.status_code == 200

    with db_factory() as db:
        business = db.query(User).filter(User.username == "business").one()
        UsageAnalyticsService(db).record_search_interaction(
            business,
            search_log_id=None,
            keyword="",
            action="add_to_project",
            result_image_id=image["id"],
            asset_group_id=image["assetGroupId"],
            position=1,
        )
        assert db.query(AiSearchBehaviorEvent).count() == 0


def test_duplicate_board_name_is_rejected_per_user(client):
    headers = _headers(client, "business", "business-password")
    first = client.post(
        "/api/me/asset-collections/boards",
        headers=headers,
        json={"name": "常用图"},
    )
    duplicate = client.post(
        "/api/me/asset-collections/boards",
        headers=headers,
        json={"name": " 常用图 "},
    )

    assert first.status_code == 201
    assert duplicate.status_code == 409
    assert duplicate.json()["code"] == "board_name_exists"
