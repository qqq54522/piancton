from __future__ import annotations

import json
from collections.abc import Iterator
from datetime import datetime, timedelta, timezone
from typing import Any, cast
from zoneinfo import ZoneInfo

from sqlalchemy.orm import Session

from app.ai.contracts import (
    ModelCallResult,
    ModelProvider,
    ModelProviderError,
    ModelProviderNotConfigured,
    ModelRequest,
)
from app.core.errors import AppError, NotFoundError
from app.models.asset import AssetGroup
from app.models.asset_agent import AssetAgentMessage, AssetAgentSession
from app.models.business_concept import BusinessConcept
from app.models.image import Image
from app.models.user import User
from app.repositories.asset_agent_repository import (
    AssetAgentMessageRepository,
    AssetAgentSessionRepository,
)
from app.repositories.asset_repository import AssetRepository
from app.repositories.business_concept_repository import BusinessConceptRepository
from app.repositories.image_repository import ImageRepository
from app.schemas.ai import SearchUnderstanding
from app.schemas.asset_agent import (
    AssetAgentChatRequest,
    AssetAgentChatResponse,
    AssetAgentContextCard,
    AssetAgentImageContext,
    AssetAgentMessageRead,
    AssetAgentMessageRole,
    AssetAgentModelResponse,
    AssetAgentSessionContextUpdateRequest,
    AssetAgentSessionCreateRequest,
    AssetAgentSessionListResponse,
    AssetAgentSessionRead,
)
from app.services.unit_of_work import UnitOfWork
from app.services.volc_ai_search_client import (
    VolcAiSearchChatResult,
    VolcAiSearchClient,
    VolcAiSearchClientError,
)

MAX_AGENT_SESSIONS = 20
AGENT_RESET_TIMEZONE = ZoneInfo("Asia/Shanghai")
DEFAULT_GREETING = (
    "我是 Piancton Agent。你可以问我图片、卖点、六大体系、素材使用和销售话术；"
    "如果把图片发给我，我会结合已确认的素材信息一起回答。"
)


class AssetAgentService:
    """Small business assistant for explaining image-library assets.

    The assistant is intentionally retrieval-first: it explains images and selling
    points from confirmed project data, then lets the model rewrite the wording.
    """

    def __init__(
        self,
        db: Session,
        provider: ModelProvider,
        *,
        knowledge_router: Any | None = None,
        ai_search_chat: VolcAiSearchClient | None = None,
        ai_search_chat_page_size: int = 10,
    ):
        self.db = db
        self.provider = provider
        self.knowledge_router = knowledge_router
        self.ai_search_chat = ai_search_chat
        self.ai_search_chat_page_size = max(1, min(ai_search_chat_page_size, 50))
        self.sessions = AssetAgentSessionRepository(db)
        self.messages = AssetAgentMessageRepository(db)
        self.images = ImageRepository(db)
        self.assets = AssetRepository(db)
        self.concepts = BusinessConceptRepository(db)
        self.uow = UnitOfWork(db)

    def list_sessions(self, user: User) -> AssetAgentSessionListResponse:
        self._reset_user_sessions_for_today(user)
        sessions = self.sessions.list_for_user(user.id, limit=MAX_AGENT_SESSIONS)
        if not sessions:
            sessions = [self._create_session(user)]
        self.uow.commit()
        return AssetAgentSessionListResponse(
            sessions=[self._session_read(item) for item in sessions]
        )

    def create_session(
        self,
        user: User,
        payload: AssetAgentSessionCreateRequest | None = None,
    ) -> AssetAgentSessionRead:
        self._reset_user_sessions_for_today(user)
        session = self._create_session(
            user,
            title=payload.title if payload else None,
            context_images=payload.context_images if payload else [],
        )
        self.sessions.trim_for_user(user.id, keep=MAX_AGENT_SESSIONS)
        self.uow.commit()
        return self._session_read(session)

    def update_context(
        self,
        user: User,
        session_id: str,
        payload: AssetAgentSessionContextUpdateRequest,
    ) -> AssetAgentSessionRead:
        self._reset_user_sessions_for_today(user)
        session = self._get_session_or_404(user, session_id)
        previous_ids = {item.image_id for item in self._session_context(session)}
        context_images = _clean_context_images(payload.context_images)
        session.context_images_json = _json_dump(
            [item.model_dump(by_alias=True) for item in context_images]
        )
        for item in context_images:
            if item.image_id not in previous_ids:
                self._add_message(
                    session,
                    role="system",
                    content=f"已加入图片上下文：{item.title}",
                )
        if context_images and session.title == "新对话":
            session.title = _title_from_message(context_images[0].title)
        session.updated_at = _now()
        self.sessions.save(session)
        self.uow.commit()
        return self._session_read(session)

    def delete_session(self, user: User, session_id: str) -> None:
        self._reset_user_sessions_for_today(user)
        session = self._get_session_or_404(user, session_id)
        self.sessions.delete(session)
        self.uow.commit()

    def chat_in_session(
        self,
        user: User,
        session_id: str,
        payload: AssetAgentChatRequest,
    ) -> AssetAgentChatResponse:
        session = self.sessions.get(session_id)
        if session and session.user_id != user.id:
            raise NotFoundError("asset_agent_session_not_found", "聊天记录不存在或已过期")
        payload.conversation_id = session_id
        return self.chat(user, payload)

    def chat_in_session_stream(
        self,
        user: User,
        session_id: str,
        payload: AssetAgentChatRequest,
    ) -> Iterator[str]:
        message = payload.message.strip()
        if not message:
            raise AppError("empty_message", "请输入要问 Piancton Agent 的问题", status_code=422)
        session = self.sessions.get(session_id)
        if session and session.user_id != user.id:
            raise NotFoundError("asset_agent_session_not_found", "聊天记录不存在或已过期")
        payload.conversation_id = session_id
        return self.chat_stream(user, payload)

    def chat(self, user: User, payload: AssetAgentChatRequest) -> AssetAgentChatResponse:
        message = payload.message.strip()
        if not message:
            raise AppError("empty_message", "请输入要问 Piancton Agent 的问题", status_code=422)

        self._reset_user_sessions_for_today(user)
        session = self._session_for_chat(user, payload)
        payload_context = self._context_from_ids(payload.image_ids)
        if payload_context:
            session.context_images_json = _json_dump(
                [item.model_dump(by_alias=True) for item in payload_context]
            )
        if session.title == "新对话":
            session.title = _title_from_message(message)
        session.updated_at = _now()
        self._add_message(session, role="user", content=message)

        context_images = self._session_context(session)
        image_ids = [item.image_id for item in context_images]
        group_ids = [
            item.asset_group_id for item in context_images if item.asset_group_id
        ] + payload.asset_group_ids
        images = self._load_images(image_ids)
        groups = self._load_groups(group_ids, images)
        concept_cards = self._concept_cards(groups)
        context_cards = self._context_cards(images, groups) + concept_cards
        context_text = self._context_text(images, groups)

        external_chat = self._try_ai_search_chat(
            user=user,
            session=session,
            message=message,
            context_text=context_text,
        )
        if external_chat is not None:
            suggestions = _clean_suggestions(external_chat.suggestions) or _fallback_suggestions(
                bool(images or groups)
            )
            answer = external_chat.answer.strip()
            session.suggested_questions_json = _json_dump(suggestions)
            self._add_message(session, role="assistant", content=answer, used_model=True)
            self.sessions.save(session)
            self.sessions.trim_for_user(user.id, keep=MAX_AGENT_SESSIONS)
            self.uow.commit()
            return AssetAgentChatResponse(
                answer=answer,
                conversation_id=session.id,
                session=self._session_read(session),
                suggested_questions=suggestions,
                context_cards=context_cards,
                used_model=True,
                provider_attempts=[_ai_search_chat_attempt(status="ok")],
            )

        understanding = self._route_business_understanding(message, images, groups)
        prompt = _agent_prompt()
        input_text = "\n\n".join(
            item
            for item in (
                f"用户问题：{message}",
                f"当前对话ID：{session.id}",
                f"知识库/向量库卖点判断：\n{_understanding_text(understanding)}"
                if understanding
                else "",
                f"已发送图片/素材上下文：\n{context_text}" if context_text else "",
                f"项目启用卖点简表：\n{self._catalog_text(groups)}",
            )
            if item
        )

        answer: str
        suggestions: list[str]
        used_model: bool
        attempts: tuple[dict[str, Any], ...] = ()
        try:
            call: ModelCallResult[dict[str, Any]] = self.provider.generate_json(
                ModelRequest(
                    task="asset_agent_chat",
                    prompt=prompt,
                    input_text=input_text,
                    timeout_seconds=30,
                ),
            )
            attempts = call.attempts
            raw = call.value
            result = AssetAgentModelResponse.model_validate(raw)
            answer = result.answer.strip()
            suggestions = _clean_suggestions(result.suggested_questions)
            used_model = True
        except (ModelProviderNotConfigured, ModelProviderError, ValueError) as exc:
            error_attempts = getattr(exc, "attempts", ())
            attempts = (
                tuple(item for item in error_attempts if isinstance(item, dict))
                if isinstance(error_attempts, (list, tuple))
                else ()
            )
            answer = self._fallback_answer(message, images, groups, error=str(exc))
            suggestions = _fallback_suggestions(bool(images or groups))
            used_model = False

        session.suggested_questions_json = _json_dump(suggestions)
        self._add_message(session, role="assistant", content=answer, used_model=used_model)
        self.sessions.save(session)
        self.sessions.trim_for_user(user.id, keep=MAX_AGENT_SESSIONS)
        self.uow.commit()
        return AssetAgentChatResponse(
            answer=answer,
            conversation_id=session.id,
            session=self._session_read(session),
            suggested_questions=suggestions,
            context_cards=context_cards,
            used_model=used_model,
            provider_attempts=[attempt for attempt in attempts if isinstance(attempt, dict)],
        )

    def chat_stream(
        self,
        user: User,
        payload: AssetAgentChatRequest,
    ) -> Iterator[str]:
        message = payload.message.strip()
        if not message:
            raise AppError("empty_message", "请输入要问 Piancton Agent 的问题", status_code=422)

        def events() -> Iterator[str]:
            session: AssetAgentSession | None = None
            try:
                self._reset_user_sessions_for_today(user)
                session = self._session_for_chat(user, payload)
                payload_context = self._context_from_ids(payload.image_ids)
                if payload_context:
                    session.context_images_json = _json_dump(
                        [item.model_dump(by_alias=True) for item in payload_context]
                    )
                if session.title == "新对话":
                    session.title = _title_from_message(message)
                session.updated_at = _now()
                self._add_message(session, role="user", content=message)

                context_images = self._session_context(session)
                image_ids = [item.image_id for item in context_images]
                group_ids = [
                    item.asset_group_id for item in context_images if item.asset_group_id
                ] + payload.asset_group_ids
                images = self._load_images(image_ids)
                groups = self._load_groups(group_ids, images)
                concept_cards = self._concept_cards(groups)
                context_cards = self._context_cards(images, groups) + concept_cards
                context_text = self._context_text(images, groups)

                yield _sse(
                    "reasoning_delta",
                    {"text": "我会先调用洋葱业务知识问答，基于卖点体系和素材库数据回答。\n"},
                )
                external_chat = self._try_ai_search_chat(
                    user=user,
                    session=session,
                    message=message,
                    context_text=context_text,
                )
                if external_chat is not None:
                    answer = external_chat.answer.strip()
                    suggestions = _clean_suggestions(
                        external_chat.suggestions
                    ) or _fallback_suggestions(bool(images or groups))
                    for chunk in _chunk_text(answer):
                        yield _sse("answer_delta", {"text": chunk})
                    session.suggested_questions_json = _json_dump(suggestions)
                    self._add_message(
                        session,
                        role="assistant",
                        content=answer,
                        used_model=True,
                    )
                    self.sessions.save(session)
                    self.sessions.trim_for_user(user.id, keep=MAX_AGENT_SESSIONS)
                    self.uow.commit()
                    response = AssetAgentChatResponse(
                        answer=answer,
                        conversation_id=session.id,
                        session=self._session_read(session),
                        suggested_questions=suggestions,
                        context_cards=context_cards,
                        used_model=True,
                        provider_attempts=[_ai_search_chat_attempt(status="ok")],
                    )
                    yield _sse("final", response.model_dump(mode="json", by_alias=True))
                    return

                yield _sse(
                    "reasoning_delta",
                    {"text": "我先判断这句话是在找图、问卖点，还是要销售话术。\n"},
                )
                understanding = self._route_business_understanding(message, images, groups)
                if understanding:
                    for chunk in _chunk_text(_visible_reasoning_text(understanding)):
                        yield _sse("reasoning_delta", {"text": chunk})
                else:
                    yield _sse(
                        "reasoning_delta",
                        {
                            "text": (
                                "我没有拿到稳定的知识库/向量库卖点结论，接下来只按当前图片、素材上下文"
                                "和项目卖点简表组织回答。\n"
                            )
                        },
                    )

                prompt = _agent_prompt()
                input_text = "\n\n".join(
                    item
                    for item in (
                        f"用户问题：{message}",
                        f"当前对话ID：{session.id}",
                        f"知识库/向量库卖点判断：\n{_understanding_text(understanding)}"
                        if understanding
                        else "",
                        f"已发送图片/素材上下文：\n{context_text}" if context_text else "",
                        f"项目启用卖点简表：\n{self._catalog_text(groups)}",
                    )
                    if item
                )

                answer: str
                suggestions: list[str]
                used_model: bool
                attempts: tuple[dict[str, Any], ...] = ()
                try:
                    call: ModelCallResult[dict[str, Any]] = self.provider.generate_json(
                        ModelRequest(
                            task="asset_agent_chat",
                            prompt=prompt,
                            input_text=input_text,
                            timeout_seconds=45,
                        ),
                    )
                    attempts = call.attempts
                    result = AssetAgentModelResponse.model_validate(call.value)
                    answer = result.answer.strip()
                    suggestions = _clean_suggestions(result.suggested_questions)
                    used_model = True
                except (ModelProviderNotConfigured, ModelProviderError, ValueError) as exc:
                    error_attempts = getattr(exc, "attempts", ())
                    attempts = (
                        tuple(item for item in error_attempts if isinstance(item, dict))
                        if isinstance(error_attempts, (list, tuple))
                        else ()
                    )
                    answer = self._fallback_answer(message, images, groups, error=str(exc))
                    suggestions = _fallback_suggestions(bool(images or groups))
                    used_model = False

                for chunk in _chunk_text(answer):
                    yield _sse("answer_delta", {"text": chunk})

                session.suggested_questions_json = _json_dump(suggestions)
                self._add_message(
                    session,
                    role="assistant",
                    content=answer,
                    used_model=used_model,
                )
                self.sessions.save(session)
                self.sessions.trim_for_user(user.id, keep=MAX_AGENT_SESSIONS)
                self.uow.commit()
                response = AssetAgentChatResponse(
                    answer=answer,
                    conversation_id=session.id,
                    session=self._session_read(session),
                    suggested_questions=suggestions,
                    context_cards=context_cards,
                    used_model=used_model,
                    provider_attempts=[
                        attempt for attempt in attempts if isinstance(attempt, dict)
                    ],
                )
                yield _sse("final", response.model_dump(mode="json", by_alias=True))
            except Exception as exc:
                self.uow.rollback()
                yield _sse("error", {"message": _clip(str(exc) or exc.__class__.__name__, 200)})

        return events()

    def _session_for_chat(
        self,
        user: User,
        payload: AssetAgentChatRequest,
    ) -> AssetAgentSession:
        if payload.conversation_id:
            session = self.sessions.get_for_user(user.id, payload.conversation_id)
            if session and _is_active_today(session):
                return session
            if session:
                self.sessions.delete(session)
        context_images = self._context_from_ids(payload.image_ids)
        return self._create_session(user, context_images=context_images)

    def _create_session(
        self,
        user: User,
        *,
        title: str | None = None,
        context_images: list[AssetAgentImageContext] | None = None,
    ) -> AssetAgentSession:
        cleaned_context = _clean_context_images(context_images or [])
        session = AssetAgentSession(
            user_id=user.id,
            title=_title_from_message(title or cleaned_context[0].title)
            if title or cleaned_context
            else "新对话",
            context_images_json=_json_dump(
                [item.model_dump(by_alias=True) for item in cleaned_context]
            ),
            suggested_questions_json=_json_dump(_fallback_suggestions(bool(cleaned_context))),
            expires_at=_next_reset_at(),
            created_at=_now(),
            updated_at=_now(),
        )
        self.sessions.add(session)
        self._add_message(session, role="assistant", content=DEFAULT_GREETING)
        for item in cleaned_context:
            self._add_message(session, role="system", content=f"已加入图片上下文：{item.title}")
        return session

    def _get_session_or_404(self, user: User, session_id: str) -> AssetAgentSession:
        session = self.sessions.get_for_user(user.id, session_id)
        if not session or not _is_active_today(session):
            if session:
                self.sessions.delete(session)
            raise NotFoundError("asset_agent_session_not_found", "聊天记录不存在或已过期")
        return session

    def _reset_user_sessions_for_today(self, user: User) -> None:
        now = _now()
        self.sessions.delete_for_user_before_day(
            user.id,
            day_start=_current_day_start(now),
            now=now,
        )

    def _add_message(
        self,
        session: AssetAgentSession,
        *,
        role: AssetAgentMessageRole,
        content: str,
        used_model: bool | None = None,
    ) -> AssetAgentMessage:
        message = AssetAgentMessage(
            session=session,
            role=role,
            content=content,
            used_model=used_model,
            created_at=_now(),
        )
        self.messages.add(message)
        return message

    def _session_context(self, session: AssetAgentSession) -> list[AssetAgentImageContext]:
        return _clean_context_images(_parse_context_images(session.context_images_json))

    def _session_read(self, session: AssetAgentSession) -> AssetAgentSessionRead:
        messages = sorted(
            session.messages,
            key=lambda item: (_datetime_sort_key(item.created_at), item.id),
        )
        return AssetAgentSessionRead(
            id=session.id,
            title=session.title,
            messages=[_message_read(item) for item in messages],
            context_images=self._session_context(session),
            suggested_questions=_parse_string_list(session.suggested_questions_json),
            expires_at=session.expires_at,
            created_at=session.created_at,
            updated_at=session.updated_at,
        )

    def _context_from_ids(self, image_ids: list[str]) -> list[AssetAgentImageContext]:
        images = self._load_images(image_ids)
        return [
            AssetAgentImageContext(
                image_id=image.id,
                asset_group_id=image.asset_group_id,
                title=image.title,
            )
            for image in images[:8]
        ]

    def _load_images(self, image_ids: list[str]) -> list[Image]:
        return self.images.get_many_by_ids(_unique(image_ids)[:10])

    def _load_groups(
        self,
        group_ids: list[str],
        images: list[Image],
    ) -> list[AssetGroup]:
        ordered_group_ids = _unique(
            [
                *group_ids,
                *(image.asset_group_id for image in images if image.asset_group_id),
            ]
        )
        groups: list[AssetGroup] = []
        for group_id in ordered_group_ids[:10]:
            group = self.assets.get(group_id)
            if group:
                groups.append(group)
        return groups

    def _context_cards(
        self,
        images: list[Image],
        groups: list[AssetGroup],
    ) -> list[AssetAgentContextCard]:
        cards: list[AssetAgentContextCard] = []
        for image in images[:6]:
            facts = [
                item
                for item in (
                    f"渠道/尺寸：{image.channel}" if image.channel else "",
                    f"图片摘要：{_clip(image.image_summary, 120)}" if image.image_summary else "",
                    f"素材组：{image.asset_group.title}" if image.asset_group else "",
                )
                if item
            ]
            cards.append(
                AssetAgentContextCard(
                    kind="image",
                    id=image.id,
                    title=image.title,
                    subtitle=image.asset_group.title if image.asset_group else "单张图片",
                    facts=facts,
                )
            )

        for group in groups[:6]:
            cards.append(
                AssetAgentContextCard(
                    kind="asset_group",
                    id=group.id,
                    title=group.title,
                    subtitle="素材组",
                    facts=_group_facts(group)[:6],
                )
            )
        return cards

    def _concept_cards(self, groups: list[AssetGroup]) -> list[AssetAgentContextCard]:
        seen: set[str] = set()
        cards: list[AssetAgentContextCard] = []
        for group in groups:
            for link in group.concept_links:
                if link.review_status == "rejected" or link.relation_role == "excludes":
                    continue
                concept = link.concept
                if not concept or concept.id in seen:
                    continue
                seen.add(concept.id)
                cards.append(
                    AssetAgentContextCard(
                        kind="concept",
                        id=concept.id,
                        title=concept.name,
                        subtitle=f"{link.relation_role} · {link.review_status}",
                        facts=_concept_facts(concept, link.evidence_reason)[:5],
                    )
                )
        return cards[:8]

    def _context_text(self, images: list[Image], groups: list[AssetGroup]) -> str:
        lines: list[str] = []
        for image in images[:6]:
            lines.append(f"【图片】{image.title}（id={image.id}）")
            if image.image_summary:
                lines.append(f"- 图片摘要：{_clip(image.image_summary, 240)}")
            semantic = _semantic_profile_facts(image.semantic_profile_json)
            for fact in semantic[:6]:
                lines.append(f"- {fact}")

        for group in groups[:6]:
            lines.append(f"【素材组】{group.title}（id={group.id}）")
            for fact in _group_facts(group)[:12]:
                lines.append(f"- {fact}")
        return "\n".join(lines)

    def _catalog_text(self, scoped_groups: list[AssetGroup]) -> str:
        scoped_codes = {
            link.concept.code
            for group in scoped_groups
            for link in group.concept_links
            if link.concept
            and link.review_status != "rejected"
            and link.relation_role != "excludes"
        }
        concepts = self.concepts.list()
        prioritized = sorted(
            concepts,
            key=lambda item: (item.code not in scoped_codes, item.name, item.code),
        )
        lines: list[str] = []
        for concept in prioritized[:60]:
            system_names = [
                link.system_tag.name
                for link in concept.system_links
                if link.status == "active" and link.system_tag
            ]
            phrases = [
                phrase.phrase
                for phrase in concept.search_phrases
                if phrase.review_status == "accepted"
            ][:6]
            lines.append(
                " / ".join(
                    item
                    for item in (
                        concept.name,
                        concept.code,
                        f"体系：{'、'.join(system_names)}" if system_names else "",
                        f"定义：{_clip(concept.definition, 120)}" if concept.definition else "",
                        f"搜索话术：{'、'.join(phrases)}" if phrases else "",
                    )
                    if item
                )
            )
        return "\n".join(lines)

    def _fallback_answer(
        self,
        message: str,
        images: list[Image],
        groups: list[AssetGroup],
        *,
        error: str,
    ) -> str:
        if not images and not groups:
            return (
                "这次模型没有成功返回，我先说明当前能做的事：\n\n"
                "我可以先帮你判断一段话更像在找哪个核心卖点；如果你确认，我再继续按这个卖点去素材库找图。"
                "我也可以解释六大体系、核心卖点边界，或帮销售把家长问题改成可直接回复的话术。\n\n"
                "当前没有图片/素材候选上下文，所以我不会编造具体图片。"
                f"\n\n本次模型暂不可用：{_clip(error, 120)}"
            )
        lines = [
            "这次模型没有成功返回，我先按素材库已有信息给你一个简版判断：",
            f"你的问题：{message}",
        ]
        for group in groups[:3]:
            lines.append(f"\n素材组「{group.title}」")
            lines.extend(f"- {fact}" for fact in _group_facts(group)[:8])
        for image in images[:3]:
            lines.append(f"\n图片「{image.title}」")
            if image.image_summary:
                lines.append(f"- {_clip(image.image_summary, 180)}")
        lines.append(f"\n模型暂不可用：{_clip(error, 120)}")
        return "\n".join(lines)

    def _route_business_understanding(
        self,
        message: str,
        images: list[Image],
        groups: list[AssetGroup],
    ) -> SearchUnderstanding | None:
        router = self.knowledge_router
        if router is None or not getattr(router, "configured", False):
            return None
        if not _should_route_agent_message(message, images, groups):
            return None
        try:
            result = router.route(message)
        except Exception:
            return None
        return result if isinstance(result, SearchUnderstanding) else None

    def _try_ai_search_chat(
        self,
        *,
        user: User,
        session: AssetAgentSession,
        message: str,
        context_text: str,
    ) -> VolcAiSearchChatResult | None:
        client = self.ai_search_chat
        if client is None or not getattr(client, "chat_search_configured", False):
            return None
        self.db.flush()
        try:
            return client.chat_search(
                _ai_search_chat_message(message, context_text),
                session_id=session.id,
                user_id=user.id,
                page_size=self.ai_search_chat_page_size,
                enable_suggestions=True,
            )
        except VolcAiSearchClientError:
            return None


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _ai_search_chat_message(message: str, context_text: str) -> str:
    if not context_text.strip():
        return message
    return "\n\n".join(
        (
            message,
            "当前用户还带了以下素材上下文。请只在确有依据时引用这些素材；"
            "如果问题与素材无关，优先按洋葱业务知识回答。",
            context_text,
        )
    )


def _ai_search_chat_attempt(*, status: str, error: str = "") -> dict[str, Any]:
    return {
        "provider": "volc_ai_search_chat",
        "model": "chat_search",
        "status": status,
        "duration_ms": None,
        "error": error,
    }


def _sse(event: str, data: dict[str, Any]) -> str:
    payload = json.dumps(data, ensure_ascii=False, separators=(",", ":"))
    return f"event: {event}\ndata: {payload}\n\n"


def _chunk_text(value: str, *, size: int = 8) -> Iterator[str]:
    if not value:
        return
    for index in range(0, len(value), size):
        yield value[index : index + size]


def _should_route_agent_message(
    message: str,
    images: list[Image],
    groups: list[AssetGroup],
) -> bool:
    query = message.strip()
    if len(query) < 3:
        return False
    route_markers = (
        "找图",
        "找图片",
        "找素材",
        "推荐图片",
        "配图",
        "素材",
        "图片",
        "卖点",
        "体系",
        "属于",
        "判断",
        "匹配",
        "命中",
        "适合",
        "解释",
        "怎么讲",
        "家长",
        "销售",
    )
    if any(marker in query for marker in route_markers):
        return True
    if images or groups:
        return any(marker in query for marker in ("卖点", "体系", "为什么", "适合", "怎么讲"))
    return len(query) >= 6


def _understanding_text(understanding: SearchUnderstanding) -> str:
    concepts = "、".join(
        f"{item.concept}（{item.relation}，{item.weight:.2f}）"
        for item in understanding.matched_business_concepts
    )
    proof_points = "、".join(
        f"{item.name}（{item.weight:.2f}）" for item in understanding.matched_proof_points
    )
    return "\n".join(
        item
        for item in (
            f"原话：{understanding.original_query}",
            f"查询状态：{understanding.query_type}",
            f"判断意图：{understanding.search_intent}",
            f"命中卖点：{concepts}" if concepts else "",
            f"命中证明点：{proof_points}" if proof_points else "",
            f"策略：{understanding.search_strategy}" if understanding.search_strategy else "",
        )
        if item
    )


def _visible_reasoning_text(understanding: SearchUnderstanding) -> str:
    concepts = understanding.matched_business_concepts
    if understanding.query_type == "no_reliable_intent_search" or not concepts:
        return (
            "我先走了一遍知识库/向量库判断，但没有得到可靠卖点。\n"
            "所以这句话暂时不能直接进入某个卖点下找图；我会先按普通业务问题回答，"
            "或者请你补充想找的场景、对象和用途。\n"
        )
    names = "、".join(item.concept for item in concepts)
    lines = [
        f"我先把这句话交给知识库/向量库判断，当前更像命中：{names}。\n",
        f"判断状态：{understanding.search_intent}\n",
    ]
    for index, concept in enumerate(concepts, start=1):
        lines.append(
            f"{index}. {concept.concept}：{concept.reason or '由知识库/向量库卖点资料命中'}；"
            f"置信度约 {concept.weight:.0%}。\n"
        )
    if len(concepts) == 1:
        lines.append(
            "如果你是在找图，我会先按这个单一卖点继续组织下一步；"
            "如果你确认，我再去素材库里找最贴合的图片。\n"
        )
    else:
        lines.append(
            "这句话不是单卖点，它同时出现多个独立信号；如果你是在找图，"
            "我会先让你确认优先找哪一个卖点下的素材。\n"
        )
    return "".join(lines)


def _is_active_today(session: AssetAgentSession) -> bool:
    now = _now()
    created_at = session.created_at
    expires_at = session.expires_at
    if created_at.tzinfo is None:
        created_at = created_at.replace(tzinfo=timezone.utc)
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)
    return created_at >= _current_day_start(now) and expires_at > now


def _current_day_start(now: datetime) -> datetime:
    local_now = now.astimezone(AGENT_RESET_TIMEZONE)
    local_start = local_now.replace(hour=0, minute=0, second=0, microsecond=0)
    return local_start.astimezone(timezone.utc)


def _next_reset_at() -> datetime:
    local_now = _now().astimezone(AGENT_RESET_TIMEZONE)
    tomorrow = local_now.date() + timedelta(days=1)
    local_midnight = datetime.combine(
        tomorrow,
        datetime.min.time(),
        tzinfo=AGENT_RESET_TIMEZONE,
    )
    return local_midnight.astimezone(timezone.utc)


def _datetime_sort_key(value: datetime) -> float:
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.timestamp()


def _json_dump(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"))


def _parse_context_images(raw: str | None) -> list[AssetAgentImageContext]:
    if not raw:
        return []
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError:
        return []
    if not isinstance(payload, list):
        return []
    items: list[AssetAgentImageContext] = []
    for value in payload:
        if not isinstance(value, dict):
            continue
        image_id = str(value.get("imageId") or value.get("image_id") or "").strip()
        title = str(value.get("title") or "").strip()
        if not image_id or not title:
            continue
        asset_group_id = value.get("assetGroupId") or value.get("asset_group_id")
        items.append(
            AssetAgentImageContext(
                image_id=image_id,
                asset_group_id=str(asset_group_id).strip() if asset_group_id else None,
                title=_clip(title, 255),
            )
        )
    return items


def _clean_context_images(
    values: list[AssetAgentImageContext],
) -> list[AssetAgentImageContext]:
    cleaned: list[AssetAgentImageContext] = []
    seen: set[str] = set()
    for value in values:
        image_id = value.image_id.strip()
        title = value.title.strip()
        if not image_id or not title or image_id in seen:
            continue
        seen.add(image_id)
        cleaned.append(
            AssetAgentImageContext(
                image_id=image_id,
                asset_group_id=value.asset_group_id.strip() if value.asset_group_id else None,
                title=_clip(title, 255),
            )
        )
    return cleaned[-8:]


def _parse_string_list(raw: str | None) -> list[str]:
    if not raw:
        return _fallback_suggestions(False)
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError:
        return _fallback_suggestions(False)
    if not isinstance(payload, list):
        return _fallback_suggestions(False)
    cleaned = [str(item).strip() for item in payload if str(item).strip()]
    return list(dict.fromkeys(cleaned))[:6] or _fallback_suggestions(False)


def _message_read(message: AssetAgentMessage) -> AssetAgentMessageRead:
    role = message.role if message.role in {"user", "assistant", "system"} else "assistant"
    return AssetAgentMessageRead(
        id=message.id,
        role=cast(AssetAgentMessageRole, role),
        content=message.content,
        used_model=message.used_model,
        created_at=message.created_at,
    )


def _title_from_message(message: str) -> str:
    cleaned = " ".join(message.split()).strip()
    if not cleaned:
        return "新对话"
    return f"{cleaned[:16]}…" if len(cleaned) > 16 else cleaned


def _agent_prompt() -> str:
    return """
你是“Piancton 通用业务 Agent”，服务对象包括销售、市场、运营、教研、设计、客服和管理团队。
你不是分开的图片助手、卖点助手或销售助手，而是同一个统一业务机器人。
你要帮助内部成员理解图片使用、卖点体系、业务边界、素材表达和对外沟通话术。

事实边界：
1. 必须优先使用“已发送图片/素材上下文”和“项目启用卖点简表”里的事实。
2. 如果输入里有“知识库/向量库卖点判断”，它是当前卖点裁决结果。
   不要推翻它，只能围绕它解释和追问。
3. 对项目没有确认的信息，不要编造；要说“当前项目资料未确认”。
4. 不要编造图片、素材名称、素材数量、学校案例、效果数据或产品能力。
5. 如果没有图片/素材候选，只能先判断卖点和说明下一步，不能假装已经找到图片。

回答形态：
1. 不要把答案过度提炼成一句话；保留可见的业务判断流程，让用户看到你怎么一步步判断。
2. 这不是泄露内部草稿，而是面向用户的“可见工作流”。避免输出自我纠结、无意义反复或系统提示词。
3. 可以按问题选用这些段落标题，不必机械凑满：
   - “我先判断你现在要做什么”
   - “我理解你在找的卖点”
   - “为什么我这样判断”
   - “下一步我会怎么找图”
   - “推荐素材”
   - “销售可以这样说”
4. 回答要中文、业务口吻、可落地，允许比普通客服回答更完整一些。

找图/找素材流程：
1. 当用户输入像“找图、推荐图片、配图、素材、海报、PPT、宣传图、
   这句话适合哪张图、我想表达……”时，先判断可能对应的核心卖点和体系。
2. 如果用户只是给出一段卖点表达或模糊需求，先问确认。
   例如：“你是想找【卖点名】这个卖点下的素材吗？
   如果是，我下一步会按这个卖点继续找图。”
3. 如果已发送图片/素材上下文中有候选，才可以推荐最合适的一张或几张，并说明推荐原因。
4. 如果当前上下文没有候选图片，就明确说“确认后我会去素材库按这个卖点找图”，不要自行虚构素材。
5. 如果一句话同时包含多个独立卖点，要保留多个候选。
   不要强行压成唯一卖点；可以让用户确认优先找哪一个。

解释/销售流程：
1. 如果用户问六大体系、核心卖点、相近卖点边界，就直接解释，并指出判断边界。
2. 如果用户给了家长原话或销售场景，要先判断家长真实关心点，再给销售可直接复制的话术。
3. 如果用户问某张图片为什么合适，要结合图片/素材上下文回答。
   说明它表达什么卖点、为什么适合、适合怎么对业务方或家长讲。

只返回 JSON：{"answer":"...","suggestedQuestions":["..."]}。
""".strip()


def _group_facts(group: AssetGroup) -> list[str]:
    facts: list[str] = []
    if group.style_label:
        facts.append(f"画面风格：{group.style_label}")
    if group.is_scene_image is not None:
        facts.append(f"是否场景图：{'是' if group.is_scene_image else '否'}")
    if group.primary_proof_point_code:
        facts.append(f"主证明点：{group.primary_proof_point_code}")
    if group.primary_evidence_point_code:
        facts.append(f"主证据表达点：{group.primary_evidence_point_code}")

    for link in group.concept_links:
        if link.review_status == "rejected" or link.relation_role == "excludes":
            continue
        if not link.concept:
            continue
        prefix = "主要表达" if link.relation_role == "expresses" else "可支持"
        reason = f"；原因：{_clip(link.evidence_reason, 100)}" if link.evidence_reason else ""
        facts.append(f"{prefix}卖点：{link.concept.name}{reason}")

    phrases = [
        phrase.phrase for phrase in group.search_phrases if phrase.review_status == "accepted"
    ][:10]
    if phrases:
        facts.append(f"已确认搜索话术：{'、'.join(phrases)}")
    return facts


def _concept_facts(concept: BusinessConcept, evidence_reason: str | None) -> list[str]:
    system_names = [
        link.system_tag.name
        for link in concept.system_links
        if link.status == "active" and link.system_tag
    ]
    phrases = [
        phrase.phrase for phrase in concept.search_phrases if phrase.review_status == "accepted"
    ][:8]
    return [
        item
        for item in (
            f"编码：{concept.code}",
            f"所属体系：{'、'.join(system_names)}" if system_names else "",
            f"定义：{_clip(concept.definition, 160)}" if concept.definition else "",
            f"推荐讲法：{_clip(concept.recommendation_text, 160)}"
            if concept.recommendation_text
            else "",
            f"搜索话术：{'、'.join(phrases)}" if phrases else "",
            f"当前素材关联原因：{_clip(evidence_reason, 120)}" if evidence_reason else "",
        )
        if item
    ]


def _semantic_profile_facts(raw: str | None) -> list[str]:
    if not raw:
        return []
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError:
        return []
    if not isinstance(payload, dict):
        return []
    facts: list[str] = []
    for key, label in (
        ("visual_facts", "视觉事实"),
        ("search_phrases", "图片搜索表达"),
        ("negative_constraints", "不适合表达"),
    ):
        values = payload.get(key)
        if isinstance(values, list):
            cleaned = [_clip(str(item), 80) for item in values if str(item).strip()]
            if cleaned:
                facts.append(f"{label}：{'、'.join(cleaned[:6])}")
    return facts


def _clean_suggestions(values: list[str]) -> list[str]:
    cleaned = [item.strip() for item in values if item.strip()]
    if cleaned:
        return list(dict.fromkeys(cleaned))[:6]
    return _fallback_suggestions(True)


def _fallback_suggestions(has_context: bool) -> list[str]:
    if has_context:
        return [
            "这张图适合怎么用？",
            "这个卖点怎么跟家长讲？",
            "它和相近卖点的区别是什么？",
        ]
    return [
        "什么是六大体系？",
        "AI 拍题精学怎么讲？",
        "家长问效果怎么回复？",
    ]


def _unique(values: list[str]) -> list[str]:
    cleaned: list[str] = []
    seen: set[str] = set()
    for value in values:
        item = value.strip()
        if not item or item in seen:
            continue
        seen.add(item)
        cleaned.append(item)
    return cleaned


def _clip(value: str | None, limit: int) -> str:
    if not value:
        return ""
    cleaned = " ".join(str(value).split())
    if len(cleaned) <= limit:
        return cleaned
    return f"{cleaned[:limit]}…"
