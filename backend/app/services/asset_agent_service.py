from __future__ import annotations

import json
from collections.abc import Iterator
from datetime import datetime, timedelta, timezone
from typing import Any, cast
from urllib.parse import urljoin
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
    "Hi，我是洋葱业务知识助手。\n\n"
    "我可以帮你理解洋葱学园的业务体系、核心卖点、证明点和使用场景，"
    "也可以把这些内容转成销售话术、家长沟通、素材方向、品牌文案、课程介绍或活动说明。\n\n"
    "你可以直接问我：某个卖点是什么意思、家长问题怎么回答、素材适合表达哪个卖点，"
    "或者某个场景该用什么卖点切入。"
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
        ai_search_public_base_url: str = "",
    ):
        self.db = db
        self.provider = provider
        self.knowledge_router = knowledge_router
        self.ai_search_chat = ai_search_chat
        self.ai_search_chat_page_size = max(1, min(ai_search_chat_page_size, 50))
        self.ai_search_public_base_url = ai_search_public_base_url.rstrip("/")
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
            sessions = [self._create_session(user, use_ai_search_opening=True)]
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
            use_ai_search_opening=not bool(payload and payload.context_images),
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
            context_images=context_images,
        )
        if external_chat is not None:
            recommended_cards = self._recommended_image_cards(external_chat.item_ids)
            response_cards = _merge_context_cards(context_cards, recommended_cards)
            suggestions = _clean_suggestions(external_chat.suggestions) or _fallback_suggestions(
                bool(images or groups)
            )
            answer = external_chat.answer.strip()
            session.suggested_questions_json = _json_dump(suggestions)
            self._add_message(
                session,
                role="assistant",
                content=answer,
                used_model=True,
                context_cards=recommended_cards,
            )
            self.sessions.save(session)
            self.sessions.trim_for_user(user.id, keep=MAX_AGENT_SESSIONS)
            self.uow.commit()
            return AssetAgentChatResponse(
                answer=answer,
                conversation_id=session.id,
                session=self._session_read(session),
                suggested_questions=suggestions,
                context_cards=response_cards,
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

                client = self.ai_search_chat
                if client is not None and getattr(client, "chat_search_configured", False):
                    answer_parts: list[str] = []
                    external_suggestions: list[str] = []
                    external_item_ids: list[str] = []
                    announced_steps: set[str] = set()
                    try:
                        self.db.flush()
                        for upstream in client.stream_chat_search(
                            _ai_search_chat_message(message, context_text),
                            session_id=session.id,
                            user_id=user.id,
                            page_size=self.ai_search_chat_page_size,
                            enable_suggestions=True,
                            image_url=_first_image_url(
                                context_images,
                                public_base_url=self.ai_search_public_base_url,
                            ),
                        ):
                            step_text = _visible_ai_search_step(upstream.step)
                            if step_text and step_text not in announced_steps:
                                announced_steps.add(step_text)
                                yield _sse("reasoning_delta", {"text": f"{step_text}\n"})
                            if upstream.content:
                                answer_parts.append(upstream.content)
                                yield _sse("answer_delta", {"text": upstream.content})
                            external_suggestions.extend(upstream.suggestions)
                            new_item_ids = [
                                item_id
                                for item_id in upstream.item_ids
                                if item_id not in external_item_ids
                            ]
                            if new_item_ids:
                                external_item_ids.extend(new_item_ids)
                                live_cards = self._recommended_image_cards(external_item_ids)
                                if live_cards:
                                    yield _sse(
                                        "context_cards",
                                        {
                                            "cards": [
                                                card.model_dump(mode="json", by_alias=True)
                                                for card in live_cards
                                            ]
                                        },
                                    )
                    except VolcAiSearchClientError:
                        if answer_parts:
                            raise
                    answer = "".join(answer_parts).strip()
                    if answer:
                        recommended_cards = self._recommended_image_cards(external_item_ids)
                        response_cards = _merge_context_cards(
                            context_cards,
                            recommended_cards,
                        )
                        suggestions = _clean_suggestions(
                            external_suggestions
                        ) or _fallback_suggestions(bool(images or groups or recommended_cards))
                        session.suggested_questions_json = _json_dump(suggestions)
                        self._add_message(
                            session,
                            role="assistant",
                            content=answer,
                            used_model=True,
                            context_cards=recommended_cards,
                        )
                        self.sessions.save(session)
                        self.sessions.trim_for_user(user.id, keep=MAX_AGENT_SESSIONS)
                        self.uow.commit()
                        response = AssetAgentChatResponse(
                            answer=answer,
                            conversation_id=session.id,
                            session=self._session_read(session),
                            suggested_questions=suggestions,
                            context_cards=response_cards,
                            used_model=True,
                            provider_attempts=[_ai_search_chat_attempt(status="ok")],
                        )
                        yield _sse("final", response.model_dump(mode="json", by_alias=True))
                        return

                yield _sse(
                    "reasoning_delta",
                    {"text": "我先把这个问题归到合适的业务场景，再组织回答。\n"},
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
                                "这句话暂时没有明确落到某一个卖点。"
                                "我会先按当前图片、素材上下文和卖点简表来回答。\n"
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
        use_ai_search_opening: bool = False,
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
        opening = (
            self._try_ai_search_opening(user=user, session=session)
            if use_ai_search_opening and not cleaned_context
            else None
        )
        if opening is not None:
            suggestions = _clean_suggestions(opening.suggestions) or _fallback_suggestions(False)
            recommended_cards = self._recommended_image_cards(opening.item_ids)
            session.suggested_questions_json = _json_dump(suggestions)
            self._add_message(
                session,
                role="assistant",
                content=opening.answer.strip() or DEFAULT_GREETING,
                used_model=True,
                context_cards=recommended_cards,
            )
        else:
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
        context_cards: list[AssetAgentContextCard] | None = None,
    ) -> AssetAgentMessage:
        message = AssetAgentMessage(
            session=session,
            role=role,
            content=content,
            context_cards_json=_json_dump(
                [card.model_dump(mode="json", by_alias=True) for card in context_cards or []]
            ),
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
                image_url=f"/api/images/{image.id}/thumbnail",
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
                    image_url=f"/api/images/{image.id}/thumbnail",
                    download_url=f"/api/images/{image.id}/download",
                    identity_code=image.identity_code,
                    asset_group_id=image.asset_group_id,
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

    def _recommended_image_cards(self, image_ids: list[str]) -> list[AssetAgentContextCard]:
        images = self._load_images(image_ids)
        cards = self._context_cards(images, [])
        return [card for card in cards if card.kind == "image"][:8]

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
            return _fallback_business_answer(message)
        lines = [
            "我先按素材库已有信息给你一个简版判断：",
            f"你的问题：{message}",
        ]
        for group in groups[:3]:
            lines.append(f"\n素材组「{group.title}」")
            lines.extend(f"- {fact}" for fact in _group_facts(group)[:8])
        for image in images[:3]:
            lines.append(f"\n图片「{image.title}」")
            if image.image_summary:
                lines.append(f"- {_clip(image.image_summary, 180)}")
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
        context_images: list[AssetAgentImageContext],
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
                image_url=_first_image_url(
                    context_images,
                    public_base_url=self.ai_search_public_base_url,
                ),
            )
        except VolcAiSearchClientError:
            return None

    def _try_ai_search_opening(
        self,
        *,
        user: User,
        session: AssetAgentSession,
    ) -> VolcAiSearchChatResult | None:
        client = self.ai_search_chat
        opening = getattr(client, "chat_opening", None) if client is not None else None
        if not callable(opening) or not getattr(client, "chat_search_configured", False):
            return None
        try:
            return cast(
                VolcAiSearchChatResult,
                opening(session_id=session.id, user_id=user.id),
            )
        except VolcAiSearchClientError:
            return None


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _ai_search_chat_message(message: str, context_text: str) -> str:
    style_instructions = (
        "以下为内部输出要求，请遵守但不要在回答中复述："
        "像一个自然的业务顾问在聊天，先给清楚判断，再按问题展开；"
        "不要使用固定开场、固定段落模板或“我先判断你现在要做什么”等机械标题；"
        "不要暴露 VikingDB、向量分数、direct/relation、置信度、数据集 ID 等内部实现；"
        "当用户问卖点解释或家长话术时，优先输出：通俗版解释、核心大白话、"
        "它解决的具体问题、日常沟通参考话术、适配素材关键词；"
        "如果生成推荐问题，请给 4 个。"
    )
    if not context_text.strip():
        return "\n\n".join((message, style_instructions))
    return "\n\n".join(
        (
            message,
            style_instructions,
            "当前用户还带了以下素材上下文。请只在确有依据时引用这些素材；"
            "如果问题与素材无关，优先按洋葱业务知识回答。",
            context_text,
        )
    )


def _first_image_url(
    context_images: list[AssetAgentImageContext],
    *,
    public_base_url: str,
) -> str:
    for item in context_images:
        image_url = (item.image_url or f"/api/images/{item.image_id}/thumbnail").strip()
        if not image_url:
            continue
        if image_url.startswith(("http://", "https://")):
            return image_url
        if public_base_url:
            return urljoin(f"{public_base_url}/", image_url.lstrip("/"))
    return ""


def _ai_search_chat_attempt(*, status: str, error: str = "") -> dict[str, Any]:
    return {
        "provider": "volc_ai_search_chat",
        "model": "chat_search",
        "status": status,
        "duration_ms": None,
        "error": error,
    }


def _visible_ai_search_step(step: str) -> str:
    normalized = step.strip().lower().replace("_", " ").replace("-", " ")
    if normalized == "tool call":
        return "正在理解需求并调用素材检索"
    if normalized == "get results":
        return "正在筛选与问题最相关的素材"
    if normalized == "reply":
        return "已完成素材判断，正在组织回答"
    return ""


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
            "这句话还缺少明确的对象、动作或使用场景。\n"
            "所以我不会硬塞进某个卖点；可以先按普通业务问题回答，"
            "也可以请你补一句想找的场景或用途。\n"
        )
    names = "、".join(item.concept for item in concepts)
    lines = [
        f"我先把这句话归到：{names}。\n",
        f"核心判断：{understanding.search_intent}\n",
    ]
    for index, concept in enumerate(concepts, start=1):
        lines.append(
            f"{index}. {concept.concept}：{concept.reason or '和当前卖点定义最接近'}。\n"
        )
    if len(concepts) == 1:
        lines.append(
            "如果你是在找图，下一步就按这个卖点去匹配素材；"
            "如果你是在问话术，我会直接帮你整理成可对外讲的表达。\n"
        )
    else:
        lines.append(
            "这句话里有多个独立信号；如果要找图，最好先确认优先表达哪一个卖点。\n"
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
        image_url = value.get("imageUrl") or value.get("image_url")
        items.append(
            AssetAgentImageContext(
                image_id=image_id,
                asset_group_id=str(asset_group_id).strip() if asset_group_id else None,
                title=_clip(title, 255),
                image_url=_clip(str(image_url).strip(), 1000) if image_url else None,
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
                image_url=_clip(value.image_url.strip(), 1000) if value.image_url else None,
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


def _parse_context_cards(raw: str | None) -> list[AssetAgentContextCard]:
    if not raw:
        return []
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError:
        return []
    if not isinstance(payload, list):
        return []
    cards: list[AssetAgentContextCard] = []
    for item in payload:
        if not isinstance(item, dict):
            continue
        try:
            cards.append(AssetAgentContextCard.model_validate(item))
        except ValueError:
            continue
    return cards[:8]


def _message_read(message: AssetAgentMessage) -> AssetAgentMessageRead:
    role = message.role if message.role in {"user", "assistant", "system"} else "assistant"
    return AssetAgentMessageRead(
        id=message.id,
        role=cast(AssetAgentMessageRole, role),
        content=message.content,
        used_model=message.used_model,
        context_cards=_parse_context_cards(message.context_cards_json),
        created_at=message.created_at,
    )


def _merge_context_cards(
    current: list[AssetAgentContextCard],
    incoming: list[AssetAgentContextCard],
) -> list[AssetAgentContextCard]:
    merged: list[AssetAgentContextCard] = []
    seen: set[tuple[str, str]] = set()
    for card in [*incoming, *current]:
        key = (card.kind, card.id)
        if key in seen:
            continue
        seen.add(key)
        merged.append(card)
    return merged[:12]


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
1. 像一个自然的业务顾问在聊天，不要重复固定开场，不要把每次回答写成同一套模板。
2. 先给一句清楚判断，再按用户问题需要展开；可以解释判断依据，但不要写成内部推理报告。
3. 段落标题可以自拟，也可以不用标题；不要固定使用“我先判断你现在要做什么”等机械标题。
4. 不要暴露内部实现词：VikingDB、向量库、direct/related/fallback、置信度、分数、
   数据集 ID、Prompt、模型任务名。
5. 回答要中文、业务口吻、可落地，重点讲家长/孩子问题、卖点边界、素材适用性和可直接复用的话术。
6. 当用户问“某个卖点怎么讲/怎么跟家长说/转成销售话术”时，优先参考这种形态：
   - 标题：“给家长的「卖点名」通俗版解释”
   - 一句转译：把业务概念换成家长能听懂的日常语言。
   - “核心大白话表达”：给一段可直接对外讲的话。
   - “它能解决孩子/家长最关心的问题”：列 2～4 条具体痛点。
   - “日常沟通参考话术”：给一段销售可直接复制的话术。
   - “适配素材关键词”：给素材搜索关键词。
7. 如果返回 suggestedQuestions，请尽量给 4 个短问题。

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

只返回 JSON：{"answer":"...","suggestedQuestions":["..."]}，suggestedQuestions 尽量给 4 个。
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
            "还有哪些素材可以一起搭配？",
        ]
    return [
        "帮我把“同步考点体系”转成家长能听懂的话术",
        "怎么理解洋葱学园的六大业务体系？",
        "如果家长觉得孩子学习没效果，应该用哪个卖点解释？",
        "某个素材应该怎么判断它对应的核心卖点？",
    ]


def _fallback_business_answer(message: str) -> str:
    normalized = message.strip()
    if "同步考点" in normalized and (
        "家长" in normalized or "话术" in normalized or "听懂" in normalized
    ):
        return (
            "## 给家长的「同步考点体系」通俗版解释\n\n"
            "你可以把它理解成：孩子在学校学到哪，洋葱就跟到哪；考试重点考什么，孩子就围绕什么学、练、巩固。\n\n"
            "## 核心大白话表达\n\n"
            "同步考点体系不是额外给孩子加一套学习任务，而是帮孩子把校内正在学、考试经常考、容易丢分的内容重新讲清楚、练扎实。\n\n"
            "## 它能帮孩子解决 3 个家长最关心的问题\n\n"
            "1. **听课听懂了，但做题不会**：把知识点和典型考法连起来，不只停留在“会听”。\n"
            "2. **复习没有重点**：围绕同步知识和高频考点走，孩子知道先补哪里、练哪里。\n"
            "3. **家长不知道怎么帮**：不用家长重新教一遍，系统会按知识点拆解、讲解和巩固。\n\n"
            "## 日常沟通参考话术\n\n"
            "可以这样跟家长说：洋葱不是让孩子脱离学校另学一套，而是紧跟校内进度，把课堂里的重点、考试里的常见考法，用孩子更容易理解的方式再讲一遍，再配合练习巩固。"
            "孩子哪里没听懂、哪里做题卡住，就回到对应考点一步步补上。\n\n"
            "## 适配素材关键词\n\n"
            "同步校内、考点拆解、课堂重难点、典型题、查漏补缺、课后巩固、考试提分。"
        )
    if "六大业务体系" in normalized:
        return (
            "## 洋葱六大业务体系怎么理解\n\n"
            "可以先把六大体系看成六种不同的业务表达入口：有的负责讲清校内同步，"
            "有的负责解决学习方法，有的强调 AI 个性化，有的强调老师陪伴、规划和结果反馈。\n\n"
            "你在做素材或销售沟通时，不需要一上来背体系名，先判断用户真实问题：是不会学、没效果、没人管、基础弱，还是想更高效提分。再把问题落到对应体系和核心卖点。"
        )
    if "学习没效果" in normalized or "没效果" in normalized:
        return (
            "## 家长觉得学习没效果时怎么切入\n\n"
            "先别急着解释功能，先承认家长的担心：孩子花了时间但没看到变化，通常不是“不努力”，而是问题没有被定位清楚。\n\n"
            "可以优先从学情诊断、同步考点、查漏补缺、错题复盘这类卖点切入：先找出孩子卡在哪里，再给到可执行的学习路径。"
        )
    if "素材" in normalized and (
        "判断" in normalized or "对应" in normalized or "卖点" in normalized
    ):
        return (
            "## 判断素材对应核心卖点的简单方法\n\n"
            "先看素材最想证明什么：如果画面强调孩子跟着题目一步步学懂，"
            "通常靠近同步考点或 AI 拍题精学；如果强调规划、陪伴和反馈，"
            "通常靠近老师督学或学情服务；如果强调一题多解、方法迁移，"
            "就更接近万能解法。\n\n"
            "判断时优先看主表达，不要把一张图硬塞进多个卖点。辅助信息可以作为支持卖点记录下来。"
        )
    return (
        "我先按已有业务知识给你一个可继续展开的方向：\n\n"
        "你可以问某个卖点怎么讲、两个卖点怎么区分，或把家长问题发来让我改成销售话术。"
        "如果你是在找图，我会先帮你确认要表达的卖点，再按这个方向找素材。\n\n"
        "当前没有图片/素材候选上下文，所以我不会编造具体图片。"
    )


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
