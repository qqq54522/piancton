from __future__ import annotations

import json

import pytest

from app.core.config import Settings
from app.models.search_feedback import SearchFeedbackEvent
from app.models.usage import AiSearchBehaviorEvent
from app.models.user import User
from app.services.ai_search_behavior_sync import (
    AiSearchBehaviorSyncService,
    resolve_ai_search_behavior_api_key,
)
from app.services.recommendation_strategy_service import RecommendationStrategyService
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
    last_json: dict = {}

    def __init__(self, **_kwargs):
        pass

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return None

    def stream(self, *_args, **kwargs):
        self.__class__.last_json = kwargs.get("json", {})
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


def test_chat_opening_uses_application_configuration_and_keeps_recommended_items(
    monkeypatch,
):
    _StreamingHttpClient.frames = [
        {"result": {"content": "欢迎使用素材助手。"}},
        {
            "result": {
                "payload": {
                    "related_rec_items": [{"_id": "opening-image"}],
                    "suggestions": ["帮我找同步考点的图片"],
                },
                "stop_reason": "stop",
            }
        },
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

    result = client.chat_opening(session_id="session-1", user_id="user-1")

    assert _StreamingHttpClient.last_json == {
        "session_id": "session-1",
        "user": {"_user_id": "user-1"},
        "context": {"location": {}},
        "opening_remarks": True,
    }
    assert result.answer == "欢迎使用素材助手。"
    assert result.suggestions == ["帮我找同步考点的图片"]
    assert result.item_ids == ["opening-image"]


def test_query_recommendations_use_the_existing_search_scene(monkeypatch):
    client = VolcAiSearchClient(
        base_url="https://aisearch.example.com",
        api_key="secret",
        dataset_id="items-1",
        application_id="app-1",
        search_path="/api/v1/application/app-1/search/scene-1",
    )
    request: dict = {}

    def fake_post(path, payload):
        request.update(path=path, payload=payload)
        return {
            "result": {
                "recommendation_queries": [
                    {"query": "同步考点"},
                    {"query": "AI 拍题精学"},
                ]
            }
        }

    monkeypatch.setattr(client, "_post_json", fake_post)

    assert client.query_recommendations(user_id="user-1", page_size=4) == [
        "同步考点",
        "AI 拍题精学",
    ]
    assert request == {
        "path": "/api/v1/application/app-1/search/scene-1/query_recommendation",
        "payload": {"user": {"_user_id": "user-1"}, "page_size": 4},
    }


def test_detail_recommendation_uses_parent_item_and_personalization(monkeypatch):
    client = VolcAiSearchClient(
        base_url="https://aisearch.example.com",
        api_key="secret",
        dataset_id="items-1",
        recommend_path="/api/v1/application/app-1/scene-detail",
    )
    request: dict = {}

    def fake_post(path, payload):
        request.update(path=path, payload=payload)
        return {
            "result": {
                "recommendation_results": [
                    {"item": {"_id": "image-2"}},
                    {"fields": {"image_id": "image-3"}},
                ]
            }
        }

    monkeypatch.setattr(client, "_post_json", fake_post)

    assert client.recommend_items(
        user_id="user-1",
        parent_item_id="image-1",
        page_size=6,
    ) == ["image-2", "image-3"]
    assert request == {
        "path": "/api/v1/application/app-1/scene-detail",
        "payload": {
            "user": {"_user_id": "user-1"},
            "parent_items": [{"_id": "image-1"}],
            "page_size": 6,
            "disable_personalize": False,
            "output_fields": ["image_id", "identity_code"],
        },
    }


def test_homepage_recommendation_uses_user_without_parent_item(monkeypatch):
    client = VolcAiSearchClient(
        base_url="https://aisearch.example.com",
        api_key="secret",
        dataset_id="items-1",
        recommend_path="/api/v1/application/app-1/scene-home",
    )
    request: dict = {}

    def fake_post(path, payload):
        request.update(path=path, payload=payload)
        return {
            "result": {
                "recommendation_results": [
                    {"item": {"_id": "image-2"}},
                    {"fields": {"image_id": "image-3"}},
                ]
            }
        }

    monkeypatch.setattr(client, "_post_json", fake_post)

    assert client.recommend_items(user_id="user-1", page_size=48) == [
        "image-2",
        "image-3",
    ]
    assert request == {
        "path": "/api/v1/application/app-1/scene-home",
        "payload": {
            "user": {"_user_id": "user-1"},
            "page_size": 48,
            "disable_personalize": False,
            "output_fields": ["image_id", "identity_code"],
        },
    }


def test_recommendation_strategy_increases_exploration_after_weak_feedback(db_factory):
    with db_factory() as db:
        user = User(username="recommend-user", password_hash="x", role="business")
        db.add(user)
        db.commit()
        analytics = UsageAnalyticsService(db)
        for index in range(20):
            analytics.record_search_interaction(
                user,
                search_log_id=None,
                keyword="",
                action="exposure",
                result_image_id=f"image-{index}",
                asset_group_id=None,
                position=index + 1,
                source="home_for_you",
            )
        for index in range(5):
            db.add(
                SearchFeedbackEvent(
                    actor_user_id=user.id,
                    keyword=f"query-{index}",
                    feedback_type="not_relevant",
                )
            )
        db.commit()

        evaluation = RecommendationStrategyService(db).evaluate(user_id=user.id)

    assert evaluation.exposure_count == 20
    assert evaluation.feedback_count == 5
    assert evaluation.strategy_mode == "explore"
    assert evaluation.personalized_share == 0.5
    assert evaluation.exploration_interval == 2


def test_recommendation_strategy_ignores_internal_account_activity(db_factory):
    with db_factory() as db:
        admin = User(username="recommend-admin", password_hash="x", role="admin")
        db.add(admin)
        db.commit()
        analytics = UsageAnalyticsService(db)
        for index in range(20):
            analytics.record_search_interaction(
                admin,
                search_log_id=None,
                keyword="",
                action="exposure",
                result_image_id=f"internal-{index}",
                asset_group_id=None,
                position=index + 1,
                source="home_for_you",
            )

        evaluation = RecommendationStrategyService(db).evaluate()

    assert evaluation.exposure_count == 0
    assert evaluation.strategy_mode == "learning"


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


@pytest.mark.parametrize(
    "scene",
    [
        "detail_same_selling_point",
        "detail_visual_similar",
        "detail_same_channel",
        "detail_current_channel",
        "detail_mobile_large",
        "detail_mobile_small",
        "detail_brand_manual",
        "detail_website",
        "detail_ppt",
        "detail_personalized",
        "home_for_you",
    ],
)
def test_detail_recommendation_interaction_keeps_its_scene(db_factory, scene):
    with db_factory() as db:
        user = User(username="detail-rec-user", password_hash="x", role="business")
        db.add(user)
        db.commit()

        UsageAnalyticsService(db).record_search_interaction(
            user,
            search_log_id=None,
            keyword="",
            action="exposure",
            result_image_id="image-2",
            asset_group_id="asset-2",
            position=1,
            source=scene,
        )

        pending = db.query(AiSearchBehaviorEvent).one()

    assert pending.event_type == "exposure"
    assert pending.event_scene == scene


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
            db.query(AiSearchBehaviorEvent).filter(AiSearchBehaviorEvent.user_id == admin.id).one()
        )
        assert admin_event.status == "pending"
