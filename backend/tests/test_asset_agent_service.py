import json
from datetime import datetime, timezone
from io import BytesIO

import httpx
import pytest
from PIL import Image as PillowImage

from app.core.errors import NotFoundError
from app.models.asset import AssetConceptLink, AssetGroup, AssetSearchPhrase
from app.models.business_concept import BusinessConcept, ConceptSearchPhrase, ConceptSystemLink
from app.models.image import Image
from app.models.tag import Tag
from app.models.user import User
from app.schemas.asset_agent import AssetAgentChatRequest
from app.services import asset_agent_service
from app.services.asset_agent_service import AssetAgentService
from app.services.asset_agent_temporary_image_service import (
    AssetAgentTemporaryImageService,
)
from app.services.storage_service import LocalStorageProvider
from app.services.volc_ai_search_client import (
    VolcAiSearchChatResult,
    VolcAiSearchClientError,
    VolcAiSearchStreamEvent,
)
from tests.conftest import login


def test_asset_agent_uses_confirmed_asset_context(db_factory):
    with db_factory() as db:
        system = Tag(name="AI 个性化学习", code="ai_personalized_learning")
        concept = BusinessConcept(
            code="ai_learning_plan",
            name="AI定制班",
            definition="根据孩子水平生成专属学习方案。",
            recommendation_text="不是所有孩子学一套，而是因材施教。",
        )
        concept.system_links.append(ConceptSystemLink(system_tag=system))
        concept.search_phrases.append(
            ConceptSearchPhrase(phrase="因材施教", review_status="accepted")
        )
        group = AssetGroup(title="AI定制班主图", created_by="admin")
        image = Image(
            title="定制规划图",
            file_name="plan.png",
            storage_key="plan.png",
            thumbnail_storage_key="plan-thumb.png",
            media_type="image/png",
            size_bytes=100,
            image_summary="页面展示根据水平安排课程。",
            asset_group=group,
        )
        group.primary_image_id = image.id
        group.concept_links.append(
            AssetConceptLink(
                concept=concept,
                relation_role="expresses",
                origin="manual",
                review_status="accepted",
                evidence_reason="画面展示定制学习规划。",
            )
        )
        group.search_phrases.append(
            AssetSearchPhrase(
                phrase="每个孩子都有自己的学习方案",
                origin="manual",
                review_status="accepted",
            )
        )
        user = User(username="agent-user", password_hash="x", role="business")
        db.add_all([system, concept, group, image, user])
        db.commit()

        ai_search = _FakeAiSearchChat()
        response = AssetAgentService(db, ai_search_chat=ai_search).chat(
            user,
            AssetAgentChatRequest(message="这张图怎么跟家长解释？", image_ids=[image.id]),
        )

    assert response.used_model is True
    assert response.session is not None
    assert response.session.title == "定制规划图"
    assert [message.role for message in response.session.messages] == [
        "assistant",
        "system",
        "user",
        "assistant",
    ]
    assert "AI定制班" in ai_search.last_query
    assert "每个孩子都有自己的学习方案" in ai_search.last_query
    assert response.context_cards[0].title == "定制规划图"
    assert response.answer == "这是火山 AI Search 的业务知识回答。"


def test_asset_agent_prefers_ai_search_chat_when_configured(db_factory):
    with db_factory() as db:
        user = User(username="agent-ai-search-user", password_hash="x", role="business")
        db.add(user)
        db.commit()

        ai_search = _FakeAiSearchChat()
        response = AssetAgentService(db, ai_search_chat=ai_search).chat(
            user,
            AssetAgentChatRequest(message="同步考点体系怎么跟家长解释？"),
        )

    assert response.used_model is True
    assert response.answer == "这是火山 AI Search 的业务知识回答。"
    assert response.suggested_questions == ["这个卖点适合什么素材？"]
    assert response.provider_attempts[0]["provider"] == "volc_ai_search_chat"
    assert ai_search.last_query.startswith("同步考点体系怎么跟家长解释？")
    assert "可自由问答的洋葱 Agent" in ai_search.last_query
    assert "不必把普通问题转成卖点判断" in ai_search.last_query


def test_asset_agent_six_system_question_uses_project_names(db_factory):
    with db_factory() as db:
        user = User(username="agent-six-systems", password_hash="x", role="business")
        db.add(user)
        db.commit()
        ai_search = _FakeAiSearchChat()
        AssetAgentService(db, ai_search_chat=ai_search).chat(
            user,
            AssetAgentChatRequest(message="洋葱的六大体系是什么？"),
        )

    for name in (
        "同步校内体系",
        "同步考点体系",
        "同步培养体系",
        "同步规划体系",
        "同步自学体系",
        "同步伴学体系",
    ):
        assert name in ai_search.last_query
    assert "不要求把其他问题归入这些体系" in ai_search.last_query


def test_asset_agent_ai_search_receives_recent_history_for_manual_followup(db_factory):
    with db_factory() as db:
        user = User(username="agent-history-user", password_hash="x", role="business")
        db.add(user)
        db.commit()

        ai_search = _FakeAiSearchChat()
        service = AssetAgentService(db, ai_search_chat=ai_search)
        session = service.create_session(user)

        first = service.chat_in_session(
            user,
            session.id,
            AssetAgentChatRequest(message="洋葱拍题精学解决什么问题？"),
        )
        frames = list(
            service.chat_in_session_stream(
                user,
                session.id,
                AssetAgentChatRequest(message="那它属于哪个体系？"),
            )
        )
        refreshed = service.list_sessions(user).sessions[0]

    assert first.conversation_id == session.id
    assert refreshed.id == session.id
    assert any(frame.startswith("event: final") for frame in frames)
    assert "以下是同一会话最近几轮对话" in ai_search.last_query
    assert "过去的助手回答也可能有误" in ai_search.last_query
    assert "用户：洋葱拍题精学解决什么问题？" in ai_search.last_query
    assert "助手：这是火山 AI Search 的业务知识回答。" in ai_search.last_query
    assert ai_search.last_query.startswith("那它属于哪个体系？")


def test_asset_agent_never_uses_an_extra_model_when_ai_search_is_unavailable(db_factory):
    with db_factory() as db:
        user = User(username="agent-local-history-user", password_hash="x", role="business")
        db.add(user)
        db.commit()

        service = AssetAgentService(db)
        session = service.create_session(user)
        service.chat_in_session(
            user,
            session.id,
            AssetAgentChatRequest(message="先介绍一下 AI 定制班。"),
        )
        response = service.chat_in_session(
            user,
            session.id,
            AssetAgentChatRequest(message="它和真人督学有什么区别？"),
        )

    assert response.conversation_id == session.id
    assert response.used_model is False
    assert response.provider_attempts == [
        {
            "provider": "volc_ai_search_chat",
            "model": "chat_search",
            "status": "unavailable",
            "duration_ms": None,
            "error": "AI Search chat is not configured",
        }
    ]
    assert "在线问答服务本轮没有生成可靠回答" in response.answer
    assert "不需要先选择体系、卖点或发送图片" in response.answer


def test_asset_agent_stream_timeout_logs_only_safe_diagnostics(db_factory, caplog):
    class ReadTimeoutChat:
        chat_search_configured = True
        calls = 0

        def stream_chat_search(self, *_args, **_kwargs):
            self.calls += 1
            raise VolcAiSearchClientError("AI Search 对话调用超时") from httpx.ReadTimeout(
                "read timed out"
            )

    chat = ReadTimeoutChat()
    with db_factory() as db:
        user = User(username="agent-stream-timeout", password_hash="x", role="business")
        db.add(user)
        db.commit()
        frames = list(
            AssetAgentService(db, ai_search_chat=chat).chat_stream(
                user,
                AssetAgentChatRequest(message="请详细讲解同步规划体系"),
            )
        )

    assert any(frame.startswith("event: final") for frame in frames)
    assert chat.calls == 2
    assert "asset_agent_ai_search_stream_retry" in caplog.text
    assert "kind=ReadTimeout" in caplog.text
    assert "elapsed_ms=" in caplog.text
    assert "请详细讲解同步规划体系" not in caplog.text
    final_frame = next(frame for frame in frames if frame.startswith("event: final"))
    response = json.loads(final_frame.split("data: ", 1)[1])
    assert "AI 搜索引擎这次响应超时了" in response["answer"]


def test_asset_agent_stream_retries_connection_before_answer_and_keeps_chat(db_factory):
    class ConnectThenReplyChat:
        chat_search_configured = True

        def __init__(self):
            self.calls = 0
            self.page_sizes = []

        def stream_chat_search(self, *_args, **kwargs):
            self.calls += 1
            self.page_sizes.append(kwargs["page_size"])
            if self.calls == 1:
                raise VolcAiSearchClientError("connection failed") from httpx.ConnectError(
                    "connection closed"
                )
            yield VolcAiSearchStreamEvent(step="reply")
            yield VolcAiSearchStreamEvent(content="同步规划体系会根据学情制定计划。")

    chat = ConnectThenReplyChat()
    with db_factory() as db:
        user = User(username="agent-stream-retry", password_hash="x", role="business")
        db.add(user)
        db.commit()
        frames = list(
            AssetAgentService(db, ai_search_chat=chat, ai_search_chat_page_size=10).chat_stream(
                user,
                AssetAgentChatRequest(message="请详细讲解一下同步规划体系"),
            )
        )

    final_frame = next(frame for frame in frames if frame.startswith("event: final"))
    response = json.loads(final_frame.split("data: ", 1)[1])
    assert response["usedModel"] is True
    assert response["answer"] == "同步规划体系会根据学情制定计划。"
    assert chat.calls == 2
    assert chat.page_sizes == [4, 4]


def test_asset_agent_memory_window_keeps_recent_messages_and_reports_full(db_factory):
    with db_factory() as db:
        user = User(username="agent-memory-cap-user", password_hash="x", role="business")
        db.add(user)
        db.commit()

        service = AssetAgentService(db)
        created = service.create_session(user)
        session = service.sessions.get_for_user(user.id, created.id)
        assert session is not None
        for index in range(30):
            service._add_message(
                session,
                role="user" if index % 2 == 0 else "assistant",
                content=f"memory-message-{index}-" + ("记忆" * 300),
            )
        service.uow.commit()

        history = asset_agent_service._conversation_history_text(session.messages)
        snapshot = service._session_read(session)

    assert "memory-message-0-" not in history
    assert "memory-message-29-" in history
    assert len(history) <= asset_agent_service.MAX_AGENT_HISTORY_CHARS
    assert snapshot.memory_used_chars == asset_agent_service.MAX_AGENT_HISTORY_CHARS
    assert snapshot.memory_usage_ratio == 1.0


def test_asset_agent_native_stream_persists_ai_search_image_cards(db_factory):
    with db_factory() as db:
        user = User(username="agent-stream-user", password_hash="x", role="business")
        group = AssetGroup(title="推荐素材组", created_by="admin", publish_status="published")
        image = Image(
            title="同步考点推荐图",
            identity_code="PC-STREAM",
            file_name="stream.png",
            storage_key="stream.png",
            thumbnail_storage_key="stream-thumb.png",
            media_type="image/png",
            size_bytes=100,
            asset_group=group,
            is_current=True,
        )
        db.add_all([user, group, image])
        db.commit()
        ai_search = _FakeAiSearchChat()
        ai_search.item_ids = [image.id]
        service = AssetAgentService(db, ai_search_chat=ai_search)
        session = service.create_session(user)

        frames = list(
            service.chat_in_session_stream(
                user,
                session.id,
                AssetAgentChatRequest(message="给我找一张同步考点的图片"),
            )
        )
        refreshed = service.list_sessions(user).sessions[0]

    assert any(frame.startswith("event: answer_delta") for frame in frames)
    assert any(frame.startswith("event: context_cards") for frame in frames)
    assistant = refreshed.messages[-1]
    assert assistant.context_cards[0].id == image.id
    assert assistant.context_cards[0].identity_code == "PC-STREAM"
    assert assistant.context_cards[0].image_url.endswith(f"/{image.id}/thumbnail")


def test_asset_agent_new_session_uses_ai_search_opening_and_local_images(db_factory):
    with db_factory() as db:
        user = User(username="agent-opening-user", password_hash="x", role="business")
        group = AssetGroup(title="开场推荐素材", created_by="admin", publish_status="published")
        image = Image(
            title="开场同步考点图",
            identity_code="PC-OPENING",
            file_name="opening.png",
            storage_key="opening.png",
            thumbnail_storage_key="opening-thumb.png",
            media_type="image/png",
            size_bytes=100,
            asset_group=group,
            is_current=True,
        )
        db.add_all([user, group, image])
        db.commit()
        ai_search = _FakeAiSearchOpening(image.id)

        session = AssetAgentService(
            db,
            ai_search_chat=ai_search,
        ).create_session(user)

    assert ai_search.last_user_id == user.id
    assert session.messages[0].content == "这是火山控制台配置的开场白。"
    assert session.messages[0].used_model is True
    assert session.messages[0].context_cards[0].id == image.id
    assert session.suggested_questions == ["帮我找一张同步考点图"]


def test_asset_agent_bridges_library_image_pixels_into_ai_search_chat(
    db_factory,
    tmp_path,
):
    with db_factory() as db:
        user = User(username="agent-ai-search-image-user", password_hash="x", role="business")
        group = AssetGroup(title="拍题精学图组", created_by="admin")
        image = Image(
            title="拍题精学讲解图",
            file_name="photo.png",
            storage_key="photo.png",
            thumbnail_storage_key="photo-thumb.png",
            media_type="image/png",
            size_bytes=100,
            asset_group=group,
        )
        db.add_all([user, group, image])
        db.commit()

        storage = LocalStorageProvider(tmp_path / "images")
        (storage.thumbnails / "photo-thumb.png").write_bytes(_png_bytes())
        temporary_images = AssetAgentTemporaryImageService(
            tmp_path / "agent-temporary",
            public_base_url="http://example.test",
            max_upload_bytes=20 * 1024 * 1024,
            max_image_pixels=1_000_000,
            max_long_image_pixels=2_000_000,
            long_image_min_aspect_ratio=3.0,
        )
        ai_search = _FakeAiSearchChat()
        service = AssetAgentService(
            db,
            ai_search_chat=ai_search,
            ai_search_public_base_url="http://example.test",
            temporary_images=temporary_images,
            storage=storage,
        )
        response = service.chat(
            user,
            AssetAgentChatRequest(message="讲解这张图", image_ids=[image.id]),
        )
        assert response.session is not None
        frames = list(
            service.chat_in_session_stream(
                user,
                response.session.id,
                AssetAgentChatRequest(message="继续说明它的主要表达"),
            )
        )

    assert response.used_model is True
    assert any(frame.startswith("event: final") for frame in frames)
    assert len(ai_search.image_urls) == 2
    assert all(
        url.startswith("http://example.test/api/asset-agent/temporary-images/")
        for url in ai_search.image_urls
    )
    assert all("/api/images/" not in url for url in ai_search.image_urls)
    assert len(set(ai_search.image_urls)) == 2
    assert "本轮附带图片" in ai_search.last_query
    assert "区分可见内容和推测" in ai_search.last_query
    assert "拍题精学讲解图" in ai_search.last_query
    for url in ai_search.image_urls:
        with pytest.raises(NotFoundError):
            temporary_images.public_file(url.rsplit("/", 1)[-1])


def test_asset_agent_expands_same_title_family_and_keeps_followup_on_topic(db_factory):
    with db_factory() as db:
        user = User(username="agent-family-user", password_hash="x", role="business")
        report_images: list[Image] = []
        for index, title in enumerate(
            [
                "学情报告01（4-3）",
                "学情报告02（4-3）",
                "学情报告03（4-3）",
                "学情报告04（4-3）",
                "学情报告0002（16-9）",
            ],
            start=1,
        ):
            group = AssetGroup(
                title=f"学情报告素材组{index}",
                created_by="admin",
                publish_status="published",
            )
            image = Image(
                title=title,
                identity_code=f"PC-REPORT-{index}",
                file_name=f"report-{index}.png",
                storage_key=f"report-{index}.png",
                thumbnail_storage_key=f"report-{index}-thumb.png",
                media_type="image/png",
                size_bytes=100,
                asset_group=group,
                is_current=True,
            )
            report_images.append(image)
            db.add_all([group, image])

        other_group = AssetGroup(
            title="辅助学习素材组",
            created_by="admin",
            publish_status="published",
        )
        other_image = Image(
            title="辅助学习03（4-3）",
            identity_code="PC-OTHER",
            file_name="other.png",
            storage_key="other.png",
            thumbnail_storage_key="other-thumb.png",
            media_type="image/png",
            size_bytes=100,
            asset_group=other_group,
            is_current=True,
        )
        db.add_all([user, other_group, other_image])
        db.commit()

        ai_search = _FakeAiSearchChat()
        ai_search.item_ids = [report_images[0].id, report_images[1].id]
        service = AssetAgentService(db, ai_search_chat=ai_search)
        session = service.create_session(user)
        first = service.chat_in_session(
            user,
            session.id,
            AssetAgentChatRequest(message="帮我找学情报告的图片"),
        )

        ai_search.item_ids = [other_image.id]
        second = service.chat_in_session(
            user,
            session.id,
            AssetAgentChatRequest(message="把其他几张也给我找出来"),
        )

    expected_ids = {image.id for image in report_images}
    assert {card.id for card in first.context_cards if card.kind == "image"} == expected_ids
    assert "共 5 张" in first.answer
    assert {card.id for card in second.context_cards if card.kind == "image"} == expected_ids
    assert other_image.id not in {card.id for card in second.context_cards}
    assert "只允许继续检索标题属于这些素材主题的图片：学情报告" in ai_search.last_query
    assert second.answer.startswith("已继续为你补齐「学情报告」")
    assert "辅助学习" not in second.answer


def test_asset_agent_temporary_image_is_used_once_and_fast_mode_is_bounded(
    db_factory,
    tmp_path,
):
    with db_factory() as db:
        user = User(username="agent-temporary-image-user", password_hash="x", role="business")
        db.add(user)
        db.commit()
        temporary_images = AssetAgentTemporaryImageService(
            tmp_path / "agent-temporary",
            public_base_url="http://example.test",
            max_upload_bytes=20 * 1024 * 1024,
            max_image_pixels=1_000_000,
            max_long_image_pixels=2_000_000,
            long_image_min_aspect_ratio=3.0,
        )
        uploaded = temporary_images.create(
            BytesIO(_png_bytes()),
            owner_id=user.id,
            filename="不会分类的图片.png",
        )
        ai_search = _FakeAiSearchChat()

        response = AssetAgentService(
            db,
            ai_search_chat=ai_search,
            ai_search_chat_page_size=10,
            temporary_images=temporary_images,
        ).chat(
            user,
            AssetAgentChatRequest(
                message="这张图表达什么卖点？",
                temporary_image_token=uploaded.token,
                response_mode="fast",
            ),
        )

    assert response.used_model is True
    assert ai_search.last_image_url == uploaded.preview_url
    assert ai_search.last_page_size == 4
    assert "本轮用户选择简短回答" in ai_search.last_query
    assert "本轮附带图片" in ai_search.last_query
    with pytest.raises(NotFoundError):
        temporary_images.public_file(uploaded.token)


def test_asset_agent_temporary_image_endpoint_is_ephemeral(client):
    csrf = login(client, "business", "business-password")
    headers = {"X-CSRF-Token": csrf, "Origin": "http://localhost:5173"}

    uploaded = client.post(
        "/api/asset-agent/temporary-images",
        files={"file": ("question.png", _png_bytes(), "image/png")},
        headers=headers,
    )

    assert uploaded.status_code == 201
    payload = uploaded.json()
    assert payload["title"] == "question"
    assert payload["previewUrl"].endswith(payload["token"])
    fetched = client.get(f"/api/asset-agent/temporary-images/{payload['token']}")
    assert fetched.status_code == 200
    assert fetched.headers["content-type"] == "image/png"

    deleted = client.delete(
        f"/api/asset-agent/temporary-images/{payload['token']}",
        headers=headers,
    )
    assert deleted.status_code == 204
    assert client.get(f"/api/asset-agent/temporary-images/{payload['token']}").status_code == 404


def test_asset_agent_sessions_are_user_private_even_for_admin(client):
    business_csrf = login(client, "business", "business-password")
    business_headers = {"X-CSRF-Token": business_csrf, "Origin": "http://localhost:5173"}
    created = client.post("/api/asset-agent/sessions", json={}, headers=business_headers)
    assert created.status_code == 200
    session_id = created.json()["id"]

    sent = client.post(
        f"/api/asset-agent/sessions/{session_id}/messages",
        json={"message": "这是业务用户自己的聊天"},
        headers=business_headers,
    )
    assert sent.status_code == 200
    assert sent.json()["conversationId"] == session_id
    assert len(sent.json()["session"]["messages"]) == 3

    listed = client.get("/api/asset-agent/sessions")
    assert listed.status_code == 200
    assert [item["id"] for item in listed.json()["sessions"]] == [session_id]

    admin_csrf = login(client, "admin", "admin-password")
    admin_headers = {"X-CSRF-Token": admin_csrf, "Origin": "http://localhost:5173"}
    admin_listed = client.get("/api/asset-agent/sessions")
    assert admin_listed.status_code == 200
    assert session_id not in [item["id"] for item in admin_listed.json()["sessions"]]

    admin_send = client.post(
        f"/api/asset-agent/sessions/{session_id}/messages",
        json={"message": "管理员不能接着别人的会话聊"},
        headers=admin_headers,
    )
    assert admin_send.status_code == 404

    admin_context = client.patch(
        f"/api/asset-agent/sessions/{session_id}/context",
        json={"contextImages": []},
        headers=admin_headers,
    )
    assert admin_context.status_code == 404

    admin_delete = client.delete(
        f"/api/asset-agent/sessions/{session_id}",
        headers=admin_headers,
    )
    assert admin_delete.status_code == 404

    business_csrf = login(client, "business", "business-password")
    business_headers = {"X-CSRF-Token": business_csrf, "Origin": "http://localhost:5173"}
    still_owned = client.get("/api/asset-agent/sessions", headers=business_headers)
    assert [item["id"] for item in still_owned.json()["sessions"]] == [session_id]


def test_asset_agent_resets_all_user_memory_at_local_midnight(
    db_factory,
    monkeypatch,
):
    before_midnight = datetime(2026, 8, 26, 15, 50, tzinfo=timezone.utc)
    after_midnight = datetime(2026, 8, 26, 16, 1, tzinfo=timezone.utc)

    with db_factory() as db:
        user = User(username="daily-agent-user", password_hash="x", role="business")
        db.add(user)
        db.commit()

        monkeypatch.setattr(asset_agent_service, "_now", lambda: before_midnight)
        ai_search = _FakeAiSearchChat()
        service = AssetAgentService(db, ai_search_chat=ai_search)
        first = service.create_session(user, None)
        first_reply = service.chat_in_session(
            user,
            first.id,
            AssetAgentChatRequest(message="第一个窗口的今日记忆"),
        ).session
        assert first_reply is not None
        assert first_reply.id == first.id
        assert first_reply.memory_used_chars > 0
        assert first_reply.memory_limit_chars == asset_agent_service.MAX_AGENT_HISTORY_CHARS

        second = service.create_session(user, None)
        second_reply = service.chat_in_session(
            user,
            second.id,
            AssetAgentChatRequest(message="第二个窗口的今日记忆"),
        ).session
        assert second_reply is not None
        assert len(service.list_sessions(user).sessions) == 2

        monkeypatch.setattr(asset_agent_service, "_now", lambda: after_midnight)
        fresh = service.list_sessions(user)

        assert len(fresh.sessions) == 1
        assert fresh.sessions[0].id not in {first.id, second.id}
        assert fresh.sessions[0].title == "新对话"
        assert [message.role for message in fresh.sessions[0].messages] == ["assistant"]
        assert fresh.sessions[0].memory_used_chars == 0
        assert fresh.sessions[0].expires_at > after_midnight
        assert service.sessions.get_for_user(user.id, first.id) is None
        assert service.sessions.get_for_user(user.id, second.id) is None

        response = service.chat_in_session(
            user,
            first.id,
            AssetAgentChatRequest(message="新一天第一问"),
        )

        assert response.session is not None
        assert response.conversation_id not in {first.id, second.id}
        assert "第一个窗口的今日记忆" not in ai_search.last_query
        assert "第二个窗口的今日记忆" not in ai_search.last_query


class _FakeAiSearchChat:
    last_query = ""
    last_image_url = ""
    item_ids: list[str] = []
    last_page_size = 0

    def __init__(self):
        self.item_ids = []
        self.image_urls: list[str] = []

    @property
    def chat_search_configured(self) -> bool:
        return True

    def chat_search(
        self,
        query: str,
        *,
        session_id: str,
        user_id: str = "",
        page_size: int = 10,
        enable_suggestions: bool = True,
        image_url: str = "",
    ) -> VolcAiSearchChatResult:
        self.last_query = query
        self.last_image_url = image_url
        self.image_urls.append(image_url)
        self.last_page_size = page_size
        return VolcAiSearchChatResult(
            session_id=session_id,
            query=query,
            answer="这是火山 AI Search 的业务知识回答。",
            response={"answer": "这是火山 AI Search 的业务知识回答。"},
            suggestions=["这个卖点适合什么素材？"],
            item_ids=self.item_ids,
        )

    def stream_chat_search(
        self,
        query: str,
        *,
        session_id: str,
        user_id: str = "",
        page_size: int = 10,
        enable_suggestions: bool = True,
        image_url: str = "",
    ):
        self.last_query = query
        self.last_image_url = image_url
        self.image_urls.append(image_url)
        self.last_page_size = page_size
        yield VolcAiSearchStreamEvent(step="tool call")
        yield VolcAiSearchStreamEvent(step="reply")
        yield VolcAiSearchStreamEvent(content="这是火山 AI Search 的业务知识回答。")
        if self.item_ids:
            yield VolcAiSearchStreamEvent(item_ids=tuple(self.item_ids))
        yield VolcAiSearchStreamEvent(
            suggestions=("这个卖点适合什么素材？",),
            done=True,
        )


class _FakeAiSearchOpening(_FakeAiSearchChat):
    def __init__(self, image_id: str):
        self.image_id = image_id
        self.last_user_id = ""

    def chat_opening(
        self,
        *,
        session_id: str,
        user_id: str = "",
    ) -> VolcAiSearchChatResult:
        self.last_user_id = user_id
        return VolcAiSearchChatResult(
            session_id=session_id,
            query="",
            answer="这是火山控制台配置的开场白。",
            response={},
            suggestions=["帮我找一张同步考点图"],
            item_ids=[self.image_id, "not-in-local-library"],
        )


def _png_bytes() -> bytes:
    output = BytesIO()
    PillowImage.new("RGB", (8, 8), "white").save(output, format="PNG")
    return output.getvalue()
