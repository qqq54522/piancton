import json
from dataclasses import replace
from datetime import datetime, timezone
from io import BytesIO
from uuid import uuid4

import httpx
import pytest
from PIL import Image as PillowImage

from app.core.errors import AppError, NotFoundError
from app.models.asset import AssetConceptLink, AssetGroup, AssetSearchPhrase
from app.models.business_concept import BusinessConcept, ConceptSearchPhrase, ConceptSystemLink
from app.models.channel_folder import ChannelFolder, ImageChannelPlacement, ManagedChannel
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
    assert ai_search.session_ids == [session.id, session.id]
    assert "用户：洋葱拍题精学解决什么问题？" in ai_search.last_query
    assert "助手：这是火山 AI Search 的业务知识回答。" in ai_search.last_query
    assert ai_search.last_query.startswith("那它属于哪个体系？")


def test_asset_agent_recovers_missing_session_id_and_recaps_saved_prior_chat(db_factory):
    with db_factory() as db:
        user = User(username="agent-recovered-chat", password_hash="x", role="business")
        db.add(user)
        db.commit()
        ai_search = _FakeAiSearchChat()
        service = AssetAgentService(db, ai_search_chat=ai_search)
        earlier = service.create_session(user)
        service.chat_in_session(
            user,
            earlier.id,
            AssetAgentChatRequest(message="帮我找一张王玉龙专家的图片"),
        )
        recovered_id = str(uuid4())
        first = service.chat_in_session(
            user,
            recovered_id,
            AssetAgentChatRequest(message="我们之前都聊了什么呢"),
        )
        second = service.chat_in_session(
            user,
            recovered_id,
            AssetAgentChatRequest(message="那张图片适合什么用途？"),
        )

    assert first.conversation_id == recovered_id
    assert "帮我找一张王玉龙专家的图片" in first.answer
    assert first.used_model is False
    assert second.conversation_id == recovered_id
    assert "我们之前都聊了什么呢" in ai_search.last_query
    assert "助手：你之前在这个账号里依次问过" not in ai_search.last_query


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


def test_asset_agent_keeps_history_without_reporting_a_fake_memory_limit(db_factory):
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

        snapshot = service._session_read(session)

    assert len(snapshot.messages) == 31
    assert "memory-message-0-" in snapshot.messages[1].content
    assert "memory-message-29-" in snapshot.messages[-1].content
    assert "memoryLimitChars" not in snapshot.model_dump(mode="json", by_alias=True)


def test_asset_agent_does_not_delete_older_same_day_conversations(db_factory):
    with db_factory() as db:
        user = User(username="agent-many-sessions-user", password_hash="x", role="business")
        db.add(user)
        db.commit()

        service = AssetAgentService(db)
        first = service.create_session(user)
        for _ in range(24):
            service.create_session(user)
        listed = service.list_sessions(user)

    assert len(listed.sessions) == 25
    assert first.id in {session.id for session in listed.sessions}


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


def test_asset_agent_explicit_channel_search_uses_verified_folder_membership(db_factory):
    with db_factory() as db:
        user = User(username="agent-channel-search", password_hash="x", role="business")
        beijing = ChannelFolder(id=str(uuid4()), channel_name="合作案例", name="北京")
        chaoyang = ChannelFolder(
            id=str(uuid4()), channel_name="合作案例", name="朝阳", parent_id=beijing.id
        )
        wangjing = ChannelFolder(
            id=str(uuid4()), channel_name="合作案例", name="望京", parent_id=chaoyang.id
        )
        shanghai = ChannelFolder(id=str(uuid4()), channel_name="合作案例", name="上海")
        beijing_image = Image(
            title="望京学校合作图", channel="PPT、合作案例", file_name="beijing.png",
            storage_key="beijing.png", thumbnail_storage_key="beijing-thumb.png",
            media_type="image/png", size_bytes=100, is_current=True,
        )
        shanghai_image = Image(
            title="上海学校合作图", channel="合作案例", file_name="shanghai.png",
            storage_key="shanghai.png", thumbnail_storage_key="shanghai-thumb.png",
            media_type="image/png", size_bytes=100, is_current=True,
        )
        unrelated = Image(
            title="PPT 公告图", channel="PPT", file_name="unrelated.png",
            storage_key="unrelated.png", thumbnail_storage_key="unrelated-thumb.png",
            media_type="image/png", size_bytes=100, is_current=True,
        )
        db.add_all([
            user, ManagedChannel(name="合作案例"), ManagedChannel(name="PPT"),
            beijing, chaoyang, wangjing, shanghai,
            beijing_image, shanghai_image, unrelated,
        ])
        db.flush()
        db.add_all([
            ImageChannelPlacement(
                image_id=beijing_image.id, channel_name="合作案例", folder_id=wangjing.id
            ),
            ImageChannelPlacement(
                image_id=shanghai_image.id, channel_name="合作案例", folder_id=shanghai.id
            ),
        ])
        db.commit()
        ai_search = _FakeAiSearchChat()
        ai_search.item_ids = [unrelated.id]
        service = AssetAgentService(db, ai_search_chat=ai_search)
        response = service.chat(
            user, AssetAgentChatRequest(message="帮我找合作案例北京的图片")
        )
        session = service.create_session(user)
        frames = list(service.chat_in_session_stream(
            user, session.id, AssetAgentChatRequest(message="搜合作案例朝阳素材")
        ))
        refreshed = service.list_sessions(user).sessions[0]
        search_query = ai_search.last_query
        ai_search.item_ids = []
        general = service.chat(
            user, AssetAgentChatRequest(message="推荐 PPT 的制作方法")
        )

    assert {card.id for card in response.context_cards if card.kind == "image"} == {
        beijing_image.id
    }
    assert unrelated.id not in {card.id for card in response.context_cards}
    assert shanghai_image.id not in {card.id for card in response.context_cards}
    assert "「合作案例」渠道找到 1 张" in response.answer
    assert "业务知识回答" not in response.answer
    assert any(frame.startswith("event: context_cards") for frame in frames)
    assert any(
        "「合作案例」渠道找到 1 张" in frame
        for frame in frames
        if frame.startswith("event: answer_delta")
    )
    assert {card.id for card in refreshed.messages[-1].context_cards} == {beijing_image.id}
    assert search_query.startswith("搜合作案例朝阳素材")
    assert general.answer == "这是火山 AI Search 的业务知识回答。"


def test_asset_agent_named_material_returns_current_local_cards_instead_of_stale_link(
    db_factory,
):
    stale_link = "http://118.196.150.130/image/b87cd76e-db89-4375-adbf-45c87ee15be5"

    class LinkAiSearch(_FakeAiSearchChat):
        def chat_search(self, *args, **kwargs):
            result = super().chat_search(*args, **kwargs)
            return replace(result, answer=f"这里有专家图片：{stale_link}")

        def stream_chat_search(self, *args, **kwargs):
            for event in super().stream_chat_search(*args, **kwargs):
                yield (
                    replace(event, content=f"这里有专家图片：{stale_link}")
                    if event.content else event
                )

    with db_factory() as db:
        user = User(username="agent-named-image", password_hash="x", role="business")
        images = [
            Image(
                title=title, file_name=f"wang-{index}.png",
                storage_key=f"wang-{index}.png",
                thumbnail_storage_key=f"wang-{index}-thumb.png",
                media_type="image/png", size_bytes=100, is_current=True,
            )
            for index, title in enumerate(("王玉龙专家", "王玉龙专家-01"), start=1)
        ]
        db.add_all([user, *images])
        db.commit()
        ai_search = LinkAiSearch()
        ai_search.item_ids = ["b87cd76e-db89-4375-adbf-45c87ee15be5"]
        service = AssetAgentService(db, ai_search_chat=ai_search)
        response = service.chat(
            user, AssetAgentChatRequest(message="帮我找一张王玉龙专家的图片")
        )
        session = service.create_session(user)
        frames = list(service.chat_in_session_stream(
            user, session.id, AssetAgentChatRequest(message="找王玉龙专家图片")
        ))

    expected = {image.id for image in images}
    assert {card.id for card in response.context_cards if card.kind == "image"} == expected
    assert stale_link not in response.answer
    assert "点下面的图片卡" in response.answer
    assert any(frame.startswith("event: context_cards") for frame in frames)
    answer_frames = [frame for frame in frames if frame.startswith("event: answer_delta")]
    assert any("点下面的图片卡" in frame for frame in answer_frames)
    assert not any(stale_link in frame for frame in answer_frames)


def test_asset_agent_selling_point_image_followup_returns_real_clickable_cards(
    db_factory,
):
    class NamesOnlyAiSearch(_FakeAiSearchChat):
        def chat_search(self, *args, **kwargs):
            result = super().chat_search(*args, **kwargs)
            return replace(
                result,
                answer="AI拍题精学和举一反三可以用不存在的官网图。",
            )

        def stream_chat_search(self, *args, **kwargs):
            for event in super().stream_chat_search(*args, **kwargs):
                yield replace(event, content="不存在的官网图") if event.content else event

    with db_factory() as db:
        user = User(username="agent-selling-point-cards", password_hash="x", role="business")
        concepts = [
            BusinessConcept(code="photo_guided_learning", name="AI拍题精学"),
            BusinessConcept(code="transfer_practice", name="举一反三"),
        ]
        real_images = []
        for index, concept in enumerate(concepts):
            group = AssetGroup(title=concept.name, created_by="admin")
            image = Image(
                title=f"{concept.name}主图",
                file_name=f"real-{index}.png",
                storage_key=f"real-{index}.png",
                thumbnail_storage_key=f"real-{index}-thumb.png",
                media_type="image/png",
                size_bytes=100,
                is_current=True,
                asset_group=group,
            )
            group.concept_links.append(AssetConceptLink(
                concept=concept,
                relation_role="expresses",
                origin="manual",
                review_status="accepted",
            ))
            real_images.append(image)
            db.add_all([group, image])
        pending_group = AssetGroup(title="未审核假图", created_by="admin")
        pending_image = Image(
            title="未审核假图", file_name="pending.png", storage_key="pending.png",
            thumbnail_storage_key="pending-thumb.png", media_type="image/png",
            size_bytes=100, is_current=True, asset_group=pending_group,
        )
        pending_group.concept_links.append(AssetConceptLink(
            concept=concepts[0], relation_role="expresses", origin="ai",
            review_status="pending",
        ))
        db.add_all([user, *concepts, pending_group, pending_image])
        db.commit()

        ai_search = NamesOnlyAiSearch()
        service = AssetAgentService(db, ai_search_chat=ai_search)
        first = service.chat(user, AssetAgentChatRequest(
            message="AI拍题精学和举一反三分别解决什么问题？"
        ))
        second = service.chat(user, AssetAgentChatRequest(
            message="把这两个卖点的图片给我找出来", conversation_id=first.session.id
        ))
        frames = list(service.chat_in_session_stream(
            user, first.session.id, AssetAgentChatRequest(message="我要的是素材卡")
        ))
        refreshed = service.sessions.get(first.session.id)

    expected = {image.id for image in real_images}
    assert first.context_cards == []
    assert {card.id for card in second.context_cards if card.kind == "image"} == expected
    assert all(card.image_url and card.download_url for card in second.context_cards)
    assert pending_image.id not in {card.id for card in second.context_cards}
    assert "不存在的官网图" not in second.answer
    assert "点下面的图片卡" in second.answer
    assert {
        card["id"] for card in json.loads(refreshed.messages[-1].context_cards_json)
    } == expected
    assert any(frame.startswith("event: context_cards") for frame in frames)
    answer_frames = [frame for frame in frames if frame.startswith("event: answer_delta")]
    assert any("点下面的图片卡" in frame for frame in answer_frames)
    assert not any("不存在的官网图" in frame for frame in answer_frames)


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
    assert response.session.context_images == []
    assert (
        next(item for item in response.session.messages if item.role == "user").context_cards[0].id
        == image.id
    )
    assert any(frame.startswith("event: final") for frame in frames)
    assert len(ai_search.image_urls) == 2
    assert ai_search.image_urls[0].startswith(
        "http://example.test/api/asset-agent/temporary-images/"
    )
    assert ai_search.image_urls[1] == ""
    assert "/api/images/" not in ai_search.image_urls[0]
    assert "拍题精学讲解图" in ai_search.queries[0]
    assert ai_search.session_ids == [response.session.id, response.session.id]
    with pytest.raises(NotFoundError):
        temporary_images.public_file(ai_search.image_urls[0].rsplit("/", 1)[-1])


def test_asset_agent_stream_consumes_library_image_after_success(db_factory, tmp_path):
    with db_factory() as db:
        user = User(username="agent-stream-image-user", password_hash="x", role="business")
        image = Image(
            title="望京合作学校图",
            file_name="school.png",
            storage_key="school.png",
            thumbnail_storage_key="school-thumb.png",
            media_type="image/png",
            size_bytes=100,
        )
        db.add_all([user, image])
        db.commit()

        storage = LocalStorageProvider(tmp_path / "images")
        (storage.thumbnails / "school-thumb.png").write_bytes(_png_bytes())
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
        first_frames = list(
            service.chat_stream(
                user,
                AssetAgentChatRequest(message="这张图讲了什么？", image_ids=[image.id]),
            )
        )
        first_final = next(
            json.loads(frame.partition("data: ")[2])
            for frame in first_frames
            if frame.startswith("event: final")
        )
        second_frames = list(
            service.chat_in_session_stream(
                user,
                first_final["conversationId"],
                AssetAgentChatRequest(message="那它适合怎么介绍？"),
            )
        )

    assert first_final["session"]["contextImages"] == []
    assert any(
        card["id"] == image.id
        for item in first_final["session"]["messages"]
        if item["role"] == "user"
        for card in item["contextCards"]
    )
    assert any(frame.startswith("event: final") for frame in second_frames)
    assert ai_search.image_urls[0].startswith(
        "http://example.test/api/asset-agent/temporary-images/"
    )
    assert ai_search.image_urls[1] == ""
    assert "望京合作学校图" in ai_search.queries[0]
    assert "第1张：望京合作学校图" in ai_search.queries[1]
    assert ai_search.session_ids == [first_final["conversationId"]] * 2


def test_asset_agent_remembers_two_sent_images_in_followup(db_factory, tmp_path):
    with db_factory() as db:
        user = User(username="agent-two-image-history", password_hash="x", role="business")
        first_image = Image(
            title="北京合作学校图",
            file_name="beijing.png",
            storage_key="beijing.png",
            thumbnail_storage_key="beijing-thumb.png",
            media_type="image/png",
            size_bytes=100,
        )
        second_image = Image(
            title="上海合作学校图",
            file_name="shanghai.png",
            storage_key="shanghai.png",
            thumbnail_storage_key="shanghai-thumb.png",
            media_type="image/png",
            size_bytes=100,
        )
        db.add_all([user, first_image, second_image])
        db.commit()
        storage = LocalStorageProvider(tmp_path / "images")
        for image in (first_image, second_image):
            (storage.thumbnails / image.thumbnail_storage_key).write_bytes(_png_bytes())
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
            temporary_images=temporary_images,
            storage=storage,
        )
        first = service.chat(
            user,
            AssetAgentChatRequest(message="第一张图讲什么？", image_ids=[first_image.id]),
        )
        assert first.session is not None
        second = service.chat_in_session(
            user,
            first.session.id,
            AssetAgentChatRequest(message="第二张图呢？", image_ids=[second_image.id]),
        )
        assert second.session is not None
        followup = service.chat_in_session(
            user,
            first.session.id,
            AssetAgentChatRequest(message="我前两张发的是什么图片？"),
        )
        assert followup.session is not None

    assert followup.conversation_id == first.session.id
    assert ai_search.session_ids == [first.session.id] * 3
    assert all(
        url.startswith("http://example.test/api/asset-agent/temporary-images/")
        for url in ai_search.image_urls[:2]
    )
    assert ai_search.image_urls[2] == ""
    assert "第1张：北京合作学校图" in ai_search.queries[2]
    assert "第2张：上海合作学校图" in ai_search.queries[2]
    assert "当时的回答：这是火山 AI Search 的业务知识回答" in ai_search.queries[2]
    sent_titles = [
        card.title
        for message in followup.session.messages
        if message.role == "user"
        for card in message.context_cards
        if card.kind == "image"
    ]
    assert sent_titles == ["北京合作学校图", "上海合作学校图"]


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

        service = AssetAgentService(
            db,
            ai_search_chat=ai_search,
            ai_search_chat_page_size=10,
            temporary_images=temporary_images,
        )
        response = service.chat(
            user,
            AssetAgentChatRequest(
                message="这张图表达什么卖点？",
                temporary_image_token=uploaded.token,
                response_mode="fast",
            ),
        )
        assert response.session is not None
        followup = service.chat_in_session(
            user,
            response.session.id,
            AssetAgentChatRequest(message="我刚发的那张图片是什么？"),
        )
        assert followup.session is not None

    assert response.used_model is True
    assert ai_search.image_urls == [uploaded.preview_url, ""]
    assert ai_search.session_ids == [response.session.id] * 2
    assert "本轮用户选择简短回答" in ai_search.queries[0]
    assert "本轮附带图片" in ai_search.queries[0]
    assert "第1张：不会分类的图片" in ai_search.queries[1]
    assert response.session.messages[-2].context_cards[0].subtitle == "用户上传图片"
    with pytest.raises(NotFoundError):
        temporary_images.public_file(uploaded.token)


@pytest.mark.parametrize("base_url", ["http://localhost", "http://127.0.0.1", "http://192.168.1.5"])
def test_asset_agent_rejects_local_visual_bridge_urls(tmp_path, base_url):
    temporary_images = AssetAgentTemporaryImageService(
        tmp_path / "agent-temporary",
        public_base_url=base_url,
        max_upload_bytes=20 * 1024 * 1024,
        max_image_pixels=1_000_000,
        max_long_image_pixels=2_000_000,
        long_image_min_aspect_ratio=3.0,
    )
    with pytest.raises(AppError) as error:
        temporary_images.public_url("A" * 32)
    assert error.value.code == "temporary_image_public_url_unreachable"


def test_asset_agent_explains_when_local_library_image_cannot_reach_ai_search(db_factory, tmp_path):
    with db_factory() as db:
        user = User(username="agent-local-visual-user", password_hash="x", role="business")
        image = Image(
            title="押题合集-河北",
            file_name="question.png",
            storage_key="question.png",
            thumbnail_storage_key="question-thumb.png",
            media_type="image/png",
            size_bytes=100,
        )
        db.add_all([user, image])
        db.commit()
        storage = LocalStorageProvider(tmp_path / "images")
        (storage.thumbnails / "question-thumb.png").write_bytes(_png_bytes())
        temporary_images = AssetAgentTemporaryImageService(
            tmp_path / "agent-temporary",
            public_base_url="http://localhost",
            max_upload_bytes=20 * 1024 * 1024,
            max_image_pixels=1_000_000,
            max_long_image_pixels=2_000_000,
            long_image_min_aspect_ratio=3.0,
        )
        ai_search = _FakeAiSearchChat()
        service = AssetAgentService(
            db, ai_search_chat=ai_search, temporary_images=temporary_images, storage=storage
        )
        response = service.chat(
            user,
            AssetAgentChatRequest(message="这张图片讲了什么", image_ids=[image.id]),
        )
        assert response.session is not None
        frames = list(
            service.chat_in_session_stream(
                user,
                response.session.id,
                AssetAgentChatRequest(message="图里写了什么"),
            )
        )

    assert response.used_model is False
    assert "无法读取它的画面" in response.answer
    assert response.provider_attempts[0]["error"] == "ImageUnavailable"
    assert any("无法读取它的画面" in frame for frame in frames)
    assert ai_search.image_urls == []
    assert list((tmp_path / "agent-temporary").iterdir()) == []


def test_asset_agent_temporary_image_endpoint_is_ephemeral(client, monkeypatch):
    from app.api import dependencies

    monkeypatch.setattr(dependencies.settings, "ai_search_public_base_url", "http://example.test")
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


def test_asset_agent_keeps_user_conversation_across_local_midnight(
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
            AssetAgentChatRequest(message="第一个窗口的聊天记录"),
        ).session
        assert first_reply is not None
        assert first_reply.id == first.id

        second = service.create_session(user, None)
        second_reply = service.chat_in_session(
            user,
            second.id,
            AssetAgentChatRequest(message="第二个窗口的聊天记录"),
        ).session
        assert second_reply is not None
        assert len(service.list_sessions(user).sessions) == 2

        monkeypatch.setattr(asset_agent_service, "_now", lambda: after_midnight)
        retained = service.list_sessions(user)

        assert {session.id for session in retained.sessions} == {first.id, second.id}
        assert service.sessions.get_for_user(user.id, first.id) is not None
        assert service.sessions.get_for_user(user.id, second.id) is not None

        response = service.chat_in_session(
            user,
            first.id,
            AssetAgentChatRequest(message="新一天继续追问"),
        )

        assert response.session is not None
        assert response.conversation_id == first.id
        assert "第一个窗口的聊天记录" in ai_search.last_query
        assert "第二个窗口的聊天记录" not in ai_search.last_query


class _FakeAiSearchChat:
    last_query = ""
    last_image_url = ""
    item_ids: list[str] = []
    last_page_size = 0

    def __init__(self):
        self.item_ids = []
        self.image_urls: list[str] = []
        self.queries: list[str] = []
        self.session_ids: list[str] = []

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
        self.queries.append(query)
        self.session_ids.append(session_id)
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
        self.queries.append(query)
        self.session_ids.append(session_id)
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
