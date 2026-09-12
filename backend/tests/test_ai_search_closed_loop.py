from __future__ import annotations

import json

import pytest

from app.core.config import Settings
from app.models.usage import AiSearchBehaviorEvent
from app.models.user import User
from app.services.ai_search_behavior_sync import (
    AiSearchBehaviorSyncService,
    resolve_ai_search_behavior_api_key,
)
from app.services.usage_analytics_service import UsageAnalyticsService
from app.services.volc_ai_search_client import VolcAiSearchClient


class _StreamResponse:
    def __init__(self, frames: list[dict]):
        self.frames = frames
        self.status_code = 200

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return None

    def raise_for_status(self) -> None:
        return None

    def iter_lines(self):
        return iter(json.dumps(frame, ensure_ascii=False) for frame in self.frames)


class _StreamingHttpClient:
    frames: list[dict] = []

    def __init__(self, **_kwargs):
        pass

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return None

    def stream(self, *_args, **_kwargs):
        return _StreamResponse(self.frames)


class _BehaviorClient:
    def __init__(self):
        self.documents: list[dict] = []

    def write_behavior_events(self, documents: list[dict]):
        self.documents = documents
        return {"submitted": len(documents)}


def test_behavior_sync_prefers_dataset_realtime_key():
    settings = Settings(
        ai_search_api_key="search-key",
        ai_search_behavior_api_key="realtime-key",
    )

    assert resolve_ai_search_behavior_api_key(settings) == "realtime-key"


def test_behavior_sync_falls_back_to_search_key_for_old_deployments():
    settings = Settings(
        ai_search_api_key="search-key",
        ai_search_behavior_api_key="",
    )

    assert resolve_ai_search_behavior_api_key(settings) == "search-key"


def test_chat_search_forwards_native_reply_and_item_citations(monkeypatch):
    _StreamingHttpClient.frames = [
        {"result": {"step_info": {"step": "tool call"}}},
        {
            "result": {
                "payload": {
                    "search_results": [
                        {"_id": "image-before-reply", "display_fields": {"title": "素材"}}
                    ]
                }
            }
        },
        {"result": {"step_info": {"step": "reply"}}},
        {"result": {"content": "这张"}},
        {
            "result": {
                "content": "更合适。",
                "citation": {
                    "type": "item",
                    "dataset_id": "items-1",
                    "_id": "image-cited",
                },
            }
        },
        {"result": {"payload": {"suggestions": ["还想看哪些风格？"]}}},
        {"result": {"stop_reason": "stop"}},
    ]
    monkeypatch.setattr(
        "app.services.volc_ai_search_client.httpx.Client",
        _StreamingHttpClient,
    )
    client = VolcAiSearchClient(
        base_url="https://aisearch.example.com",
        api_key="secret",
        dataset_id="items-1",
        application_id="app-1",
        chat_search_path="/chat_search",
    )

    events = list(client.stream_chat_search("帮我找图", session_id="session-1"))
    result = client.chat_search("帮我找图", session_id="session-1")

    assert "".join(event.content for event in events) == "这张更合适。"
    assert {item for event in events for item in event.item_ids} == {
        "image-before-reply",
        "image-cited",
    }
    assert result.answer == "这张更合适。"
    assert result.item_ids == ["image-before-reply", "image-cited"]
    assert result.suggestions == ["还想看哪些风格？"]


def test_search_interaction_is_durably_synced_to_behavior_dataset(db_factory):
    with db_factory() as db:
        user = User(username="behavior-user", password_hash="x", role="business")
        db.add(user)
        db.commit()
        UsageAnalyticsService(db).record_search_interaction(
            user,
            search_log_id="search-1",
            keyword="拍题精学",
            action="open_detail",
            result_image_id="image-1",
            asset_group_id="asset-1",
            position=2,
        )

        pending = db.query(AiSearchBehaviorEvent).one()
        assert pending.status == "pending"
        assert pending.event_type == "click"
        assert pending.event_scene == "search_results"

        client = _BehaviorClient()
        synced = AiSearchBehaviorSyncService(db, client).sync_once()
        db.refresh(pending)

        assert synced == 1
        assert pending.status == "synced"
        assert pending.attempt_count == 1
        assert client.documents[0] == {
            "event_id": pending.id,
            "user_id": user.id,
            "item_id": "image-1",
            "event_type": "click",
            "event_timestamp": pending.event_timestamp,
            "event_scene": "search_results",
            "source_action": "open_detail",
            "search_log_id": "search-1",
            "position": 2,
        }


@pytest.mark.parametrize("role", ["admin", "designer"])
def test_non_business_interaction_stays_local_and_never_enters_outbox(
    db_factory,
    role,
):
    with db_factory() as db:
        user = User(username=f"{role}-behavior-user", password_hash="x", role=role)
        db.add(user)
        db.commit()

        UsageAnalyticsService(db).record_search_interaction(
            user,
            search_log_id="search-internal",
            keyword="内部验收",
            action="open_detail",
            result_image_id="image-internal",
            asset_group_id="asset-internal",
            position=1,
        )

        assert db.query(AiSearchBehaviorEvent).count() == 0


def test_sync_defensively_skips_legacy_non_business_outbox_rows(db_factory):
    with db_factory() as db:
        business = User(username="business-sync", password_hash="x", role="business")
        admin = User(username="admin-sync", password_hash="x", role="admin")
        db.add_all([business, admin])
        db.flush()
        for index, user in enumerate((business, admin), start=1):
            db.add(
                AiSearchBehaviorEvent(
                    source_event_id=f"source-{index}",
                    user_id=user.id,
                    item_id=f"image-{index}",
                    event_type="click",
                    event_timestamp=index,
                    event_scene="search_results",
                )
            )
        db.commit()

        client = _BehaviorClient()
        synced = AiSearchBehaviorSyncService(db, client).sync_once()

        assert synced == 1
        assert [item["user_id"] for item in client.documents] == [business.id]
        admin_event = (
            db.query(AiSearchBehaviorEvent)
            .filter(AiSearchBehaviorEvent.user_id == admin.id)
            .one()
        )
        assert admin_event.status == "pending"
