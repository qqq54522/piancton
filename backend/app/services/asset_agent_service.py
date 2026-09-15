from __future__ import annotations

import json
import logging
import uuid
from collections.abc import Iterator
from datetime import datetime, timezone
from time import monotonic
from typing import Any, cast

import httpx
from sqlalchemy.orm import Session

from app.core.errors import AppError, NotFoundError
from app.domain.image_titles import material_title_family
from app.domain.taxonomy_catalog import load_taxonomy_catalog
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
from app.repositories.channel_folder_repository import ChannelFolderRepository
from app.repositories.image_repository import ImageRepository
from app.schemas.asset_agent import (
    AssetAgentChatRequest,
    AssetAgentChatResponse,
    AssetAgentContextCard,
    AssetAgentImageContext,
    AssetAgentMessageRead,
    AssetAgentMessageRole,
    AssetAgentResponseMode,
    AssetAgentSessionContextUpdateRequest,
    AssetAgentSessionCreateRequest,
    AssetAgentSessionListResponse,
    AssetAgentSessionRead,
)
from app.services.asset_agent_temporary_image_service import (
    AssetAgentTemporaryImageService,
)
from app.services.storage_service import StorageProvider
from app.services.unit_of_work import UnitOfWork
from app.services.volc_ai_search_client import (
    VolcAiSearchChatResult,
    VolcAiSearchClient,
    VolcAiSearchClientError,
    VolcAiSearchStreamEvent,
)

MAX_AGENT_RECOMMENDATION_CARDS = 50
logger = logging.getLogger(__name__)
DEFAULT_GREETING = (
    "Hi，我是洋葱 Agent。你可以像和普通助手聊天一样直接提问。"
    "聊到洋葱的产品、业务体系或素材时，我会结合洋葱知识与素材库回答；"
    "其他问题也可以直接问我。"
)


class AssetAgentService:
    """Business assistant powered only by Viking AI Search's built-in chat."""

    def __init__(
        self,
        db: Session,
        *,
        ai_search_chat: VolcAiSearchClient | None = None,
        ai_search_chat_page_size: int = 10,
        ai_search_public_base_url: str = "",
        temporary_images: AssetAgentTemporaryImageService | None = None,
        storage: StorageProvider | None = None,
    ):
        self.db = db
        self.ai_search_chat = ai_search_chat
        self.ai_search_chat_page_size = max(1, min(ai_search_chat_page_size, 50))
        self.ai_search_public_base_url = ai_search_public_base_url.rstrip("/")
        self.temporary_images = temporary_images
        self.storage = storage
        self.sessions = AssetAgentSessionRepository(db)
        self.messages = AssetAgentMessageRepository(db)
        self.images = ImageRepository(db)
        self.channel_folders = ChannelFolderRepository(db)
        self.assets = AssetRepository(db)
        self.concepts = BusinessConceptRepository(db)
        self.uow = UnitOfWork(db)

    def list_sessions(self, user: User) -> AssetAgentSessionListResponse:
        sessions = self.sessions.list_for_user(user.id)
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
        session = self._create_session(
            user,
            title=payload.title if payload else None,
            context_images=payload.context_images if payload else [],
            use_ai_search_opening=not bool(payload and payload.context_images),
        )
        self.uow.commit()
        return self._session_read(session)

    def update_context(
        self,
        user: User,
        session_id: str,
        payload: AssetAgentSessionContextUpdateRequest,
    ) -> AssetAgentSessionRead:
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
        uploaded_image_url = self._temporary_image_url(user, payload)
        uploaded_image_title = self._temporary_image_title(payload) if uploaded_image_url else ""
        library_image_url = ""
        library_image_token = ""
        if not uploaded_image_url:
            library_image_url, library_image_token = self._library_image_bridge(user, payload)
        try:
            return self._chat(
                user,
                payload,
                visual_image_url=uploaded_image_url or library_image_url,
                has_user_uploaded_image=bool(uploaded_image_url),
                uploaded_image_title=uploaded_image_title,
            )
        finally:
            self._delete_temporary_image(user, payload)
            self._delete_library_image_bridge(user, library_image_token)

    def _chat(
        self,
        user: User,
        payload: AssetAgentChatRequest,
        *,
        visual_image_url: str = "",
        has_user_uploaded_image: bool = False,
        uploaded_image_title: str = "",
    ) -> AssetAgentChatResponse:
        message = payload.message.strip()
        if not message:
            raise AppError("empty_message", "请输入要问 Piancton Agent 的问题", status_code=422)

        session = self._session_for_chat(user, payload)
        recap_answer = self._history_recap_answer(user, message)
        dialogue_context = _saved_dialogue_context(session)
        image_history_context = _sent_image_history_context(session)
        continuation_family_keys = self._continuation_family_keys(session, message)
        selling_point_cards, selling_point_names = self._selling_point_material_cards(
            session, message
        )
        payload_context = self._context_from_ids(payload.image_ids)
        if payload_context:
            session.context_images_json = _json_dump(
                [item.model_dump(by_alias=True) for item in payload_context]
            )
        if session.title == "新对话":
            session.title = _title_from_message(message)
        session.updated_at = _now()
        user_message = self._add_message(session, role="user", content=message)

        context_images = self._session_context(session)
        image_ids = [item.image_id for item in context_images]
        group_ids = [
            item.asset_group_id for item in context_images if item.asset_group_id
        ] + payload.asset_group_ids
        images = self._load_images(image_ids)
        sent_image_cards = self._image_cards(images, limit=8)
        if uploaded_image_title:
            sent_image_cards.append(
                _uploaded_image_card(user_message.id, uploaded_image_title)
            )
        if sent_image_cards:
            user_message.context_cards_json = _json_dump(
                [
                    card.model_dump(mode="json", by_alias=True)
                    for card in sent_image_cards
                ]
            )
        groups = self._load_groups(group_ids, images)
        concept_cards = self._concept_cards(groups)
        context_cards = self._context_cards(images, groups) + concept_cards
        context_text = "\n\n".join(
            item
            for item in (
                dialogue_context,
                self._context_text(images, groups),
                image_history_context,
            )
            if item
        )
        if recap_answer and not (visual_image_url or images):
            return self._save_local_history_answer(session, recap_answer)

        visual_unavailable = bool(images and not visual_image_url and _needs_image_visual(message))
        external_chat = (
            None
            if visual_unavailable
            else self._try_ai_search_chat(
                user=user,
                session=session,
                message=message,
                context_text=context_text,
                recommendation_family_keys=continuation_family_keys,
                visual_image_url=visual_image_url,
                response_mode=payload.response_mode,
            )
        )
        if external_chat is not None:
            title_family = self._explicit_title_material_family(message)
            recommended_cards = self._recommended_image_cards(
                external_chat.item_ids,
                message=message,
                preferred_family_keys=continuation_family_keys,
                title_family=title_family,
            )
            channel_match = self._explicit_channel_material_query(message)
            if channel_match:
                recommended_cards = self._verified_channel_cards(
                    *channel_match,
                    seed_image_ids=external_chat.item_ids,
                    allowed_image_ids=[card.id for card in recommended_cards]
                    if title_family else None,
                )
            elif not title_family and selling_point_cards:
                recommended_cards = selling_point_cards
            response_cards = _merge_context_cards(context_cards, recommended_cards)
            suggestions = _clean_suggestions(external_chat.suggestions) or _fallback_suggestions(
                bool(images or groups)
            )
            answer = _normalize_agent_text(external_chat.answer)
            if channel_match:
                answer = self._channel_result_answer(answer, channel_match[0], recommended_cards)
            elif title_family and recommended_cards:
                answer = self._verified_title_result_answer(recommended_cards)
            elif selling_point_cards and not title_family:
                answer = self._verified_selling_point_result_answer(
                    selling_point_names, recommended_cards
                )
            else:
                answer = self._recommendation_answer(
                    answer,
                    seed_image_ids=external_chat.item_ids,
                    cards=recommended_cards,
                    preferred_family_keys=continuation_family_keys,
                )
            session.suggested_questions_json = _json_dump(suggestions)
            if images and visual_image_url and not has_user_uploaded_image:
                session.context_images_json = "[]"
            self._add_message(
                session,
                role="assistant",
                content=answer,
                used_model=True,
                context_cards=recommended_cards,
            )
            self.sessions.save(session)
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

        answer = _ai_search_unavailable_answer(
            has_image=bool(visual_image_url or images or groups),
            failure_kind="ImageUnavailable" if visual_unavailable else "",
        )
        suggestions = _fallback_suggestions(bool(images or groups))
        attempt_error = (
            "ImageUnavailable"
            if visual_unavailable
            else (
                "AI Search chat is not configured"
                if self.ai_search_chat is None
                or not getattr(self.ai_search_chat, "chat_search_configured", False)
                else "AI Search chat request failed or returned no answer"
            )
        )

        session.suggested_questions_json = _json_dump(suggestions)
        self._add_message(session, role="assistant", content=answer, used_model=False)
        self.sessions.save(session)
        self.uow.commit()
        return AssetAgentChatResponse(
            answer=answer,
            conversation_id=session.id,
            session=self._session_read(session),
            suggested_questions=suggestions,
            context_cards=context_cards,
            used_model=False,
            provider_attempts=[_ai_search_chat_attempt(status="unavailable", error=attempt_error)],
        )

    def chat_stream(
        self,
        user: User,
        payload: AssetAgentChatRequest,
    ) -> Iterator[str]:
        message = payload.message.strip()
        if not message:
            raise AppError("empty_message", "请输入要问 Piancton Agent 的问题", status_code=422)
        uploaded_image_url = self._temporary_image_url(user, payload)
        uploaded_image_title = self._temporary_image_title(payload) if uploaded_image_url else ""
        library_image_url = ""
        library_image_token = ""
        if not uploaded_image_url:
            library_image_url, library_image_token = self._library_image_bridge(user, payload)
        visual_image_url = uploaded_image_url or library_image_url

        def events() -> Iterator[str]:
            session: AssetAgentSession | None = None
            try:
                session = self._session_for_chat(user, payload)
                recap_answer = self._history_recap_answer(user, message)
                dialogue_context = _saved_dialogue_context(session)
                image_history_context = _sent_image_history_context(session)
                continuation_family_keys = self._continuation_family_keys(session, message)
                selling_point_cards, selling_point_names = self._selling_point_material_cards(
                    session, message
                )
                payload_context = self._context_from_ids(payload.image_ids)
                if payload_context:
                    session.context_images_json = _json_dump(
                        [item.model_dump(by_alias=True) for item in payload_context]
                    )
                if session.title == "新对话":
                    session.title = _title_from_message(message)
                session.updated_at = _now()
                user_message = self._add_message(session, role="user", content=message)

                context_images = self._session_context(session)
                image_ids = [item.image_id for item in context_images]
                group_ids = [
                    item.asset_group_id for item in context_images if item.asset_group_id
                ] + payload.asset_group_ids
                images = self._load_images(image_ids)
                sent_image_cards = self._image_cards(images, limit=8)
                if uploaded_image_title:
                    sent_image_cards.append(
                        _uploaded_image_card(user_message.id, uploaded_image_title)
                    )
                if sent_image_cards:
                    user_message.context_cards_json = _json_dump(
                        [
                            card.model_dump(mode="json", by_alias=True)
                            for card in sent_image_cards
                        ]
                    )
                groups = self._load_groups(group_ids, images)
                concept_cards = self._concept_cards(groups)
                context_cards = self._context_cards(images, groups) + concept_cards
                context_text = "\n\n".join(
                    item
                    for item in (
                        dialogue_context,
                        self._context_text(images, groups),
                        image_history_context,
                    )
                    if item
                )

                if recap_answer and not (visual_image_url or images):
                    response = self._save_local_history_answer(session, recap_answer)
                    yield _sse("answer_delta", {"text": recap_answer})
                    yield _sse("final", response.model_dump(mode="json", by_alias=True))
                    return

                client = self.ai_search_chat
                ai_search_error = "AI Search chat is not configured"
                if images and not visual_image_url and _needs_image_visual(message):
                    client = None
                    ai_search_error = "ImageUnavailable"
                if client is not None and getattr(client, "chat_search_configured", False):
                    ai_search_error = ""
                    channel_match = self._explicit_channel_material_query(message)
                    title_family = self._explicit_title_material_family(message)
                    answer_parts: list[str] = []
                    external_suggestions: list[str] = []
                    external_item_ids: list[str] = []
                    announced_steps: set[str] = set()
                    chat_started_at = monotonic()
                    try:
                        self.db.flush()
                        for upstream in _stream_ai_search_chat_with_retry(
                            client,
                            _ai_search_chat_message(
                                message,
                                context_text,
                                response_mode=payload.response_mode,
                                has_visual_image=bool(visual_image_url),
                                recommendation_family_keys=continuation_family_keys,
                            ),
                            session_id=session.id,
                            user_id=user.id,
                            page_size=_chat_page_size(
                                self.ai_search_chat_page_size,
                                payload.response_mode,
                                message=message,
                                has_visual_image=bool(visual_image_url),
                            ),
                            enable_suggestions=True,
                            image_url=visual_image_url,
                        ):
                            step_text = _visible_ai_search_step(upstream.step)
                            if step_text and step_text not in announced_steps:
                                announced_steps.add(step_text)
                                yield _sse("reasoning_delta", {"text": f"{step_text}\n"})
                            if upstream.content:
                                answer_parts.append(upstream.content)
                                if not (channel_match or title_family or selling_point_cards):
                                    yield _sse("answer_delta", {"text": upstream.content})
                            external_suggestions.extend(upstream.suggestions)
                            new_item_ids = [
                                item_id
                                for item_id in upstream.item_ids
                                if item_id not in external_item_ids
                            ]
                            if new_item_ids:
                                external_item_ids.extend(new_item_ids)
                                live_cards = self._recommended_image_cards(
                                    external_item_ids,
                                    message=message,
                                    preferred_family_keys=continuation_family_keys,
                                    title_family=title_family,
                                )
                                if channel_match or title_family or selling_point_cards:
                                    live_cards = []
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
                    except VolcAiSearchClientError as exc:
                        ai_search_error = _ai_search_failure_kind(exc)
                        logger.warning(
                            "asset_agent_ai_search_stream_failed "
                            "kind=%s elapsed_ms=%d answer_started=%s",
                            ai_search_error,
                            round((monotonic() - chat_started_at) * 1000),
                            bool(answer_parts),
                        )
                        if answer_parts:
                            raise
                    answer = _normalize_agent_text("".join(answer_parts))
                    if answer:
                        recommended_cards = self._recommended_image_cards(
                            external_item_ids,
                            message=message,
                            preferred_family_keys=continuation_family_keys,
                            title_family=title_family,
                        )
                        if channel_match:
                            recommended_cards = self._verified_channel_cards(
                                *channel_match,
                                seed_image_ids=external_item_ids,
                                allowed_image_ids=[card.id for card in recommended_cards]
                                if title_family else None,
                            )
                            finalized_answer = self._channel_result_answer(
                                answer, channel_match[0], recommended_cards
                            )
                            if recommended_cards:
                                yield _sse(
                                    "context_cards",
                                    {
                                        "cards": [
                                            card.model_dump(mode="json", by_alias=True)
                                            for card in recommended_cards
                                        ]
                                    },
                                )
                        elif title_family and recommended_cards:
                            finalized_answer = self._verified_title_result_answer(recommended_cards)
                            yield _sse(
                                "context_cards",
                                {
                                    "cards": [
                                        card.model_dump(mode="json", by_alias=True)
                                        for card in recommended_cards
                                    ]
                                },
                            )
                        elif selling_point_cards and not title_family:
                            recommended_cards = selling_point_cards
                            finalized_answer = self._verified_selling_point_result_answer(
                                selling_point_names, recommended_cards
                            )
                            yield _sse(
                                "context_cards",
                                {
                                    "cards": [
                                        card.model_dump(mode="json", by_alias=True)
                                        for card in recommended_cards
                                    ]
                                },
                            )
                        else:
                            finalized_answer = self._recommendation_answer(
                                answer,
                                seed_image_ids=external_item_ids,
                                cards=recommended_cards,
                                preferred_family_keys=continuation_family_keys,
                            )
                        if (
                            channel_match
                            or (title_family and recommended_cards)
                            or (selling_point_cards and not title_family)
                        ):
                            yield _sse("answer_delta", {"text": finalized_answer})
                        elif finalized_answer != answer:
                            yield _sse(
                                "answer_delta",
                                {"text": finalized_answer[len(answer) :]},
                            )
                        answer = finalized_answer
                        response_cards = _merge_context_cards(
                            context_cards,
                            recommended_cards,
                        )
                        suggestions = _clean_suggestions(
                            external_suggestions
                        ) or _fallback_suggestions(bool(images or groups or recommended_cards))
                        session.suggested_questions_json = _json_dump(suggestions)
                        if images and library_image_url:
                            session.context_images_json = "[]"
                        self._add_message(
                            session,
                            role="assistant",
                            content=answer,
                            used_model=True,
                            context_cards=recommended_cards,
                        )
                        self.sessions.save(session)
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

                if client is not None and getattr(client, "chat_search_configured", False):
                    ai_search_error = ai_search_error or (
                        "AI Search chat request returned no usable answer"
                    )
                answer = _ai_search_unavailable_answer(
                    has_image=bool(visual_image_url or images or groups),
                    failure_kind=ai_search_error,
                )
                suggestions = _fallback_suggestions(bool(images or groups))

                for chunk in _chunk_text(answer):
                    yield _sse("answer_delta", {"text": chunk})

                session.suggested_questions_json = _json_dump(suggestions)
                self._add_message(
                    session,
                    role="assistant",
                    content=answer,
                    used_model=False,
                )
                self.sessions.save(session)
                self.uow.commit()
                response = AssetAgentChatResponse(
                    answer=answer,
                    conversation_id=session.id,
                    session=self._session_read(session),
                    suggested_questions=suggestions,
                    context_cards=context_cards,
                    used_model=False,
                    provider_attempts=[
                        _ai_search_chat_attempt(
                            status="unavailable",
                            error=_clip(ai_search_error, 200),
                        )
                    ],
                )
                yield _sse("final", response.model_dump(mode="json", by_alias=True))
            except Exception as exc:
                self.uow.rollback()
                yield _sse("error", {"message": _clip(str(exc) or exc.__class__.__name__, 200)})
            finally:
                self._delete_temporary_image(user, payload)
                self._delete_library_image_bridge(user, library_image_token)

        return events()

    def _session_for_chat(
        self,
        user: User,
        payload: AssetAgentChatRequest,
    ) -> AssetAgentSession:
        if payload.conversation_id:
            session = self.sessions.get_for_user(user.id, payload.conversation_id)
            if session:
                return session
        context_images = self._context_from_ids(payload.image_ids)
        requested_id = ""
        if payload.conversation_id:
            try:
                requested_id = str(uuid.UUID(payload.conversation_id))
            except ValueError:
                pass
        return self._create_session(
            user, context_images=context_images, session_id=requested_id or None
        )

    def _create_session(
        self,
        user: User,
        *,
        title: str | None = None,
        context_images: list[AssetAgentImageContext] | None = None,
        use_ai_search_opening: bool = False,
        session_id: str | None = None,
    ) -> AssetAgentSession:
        cleaned_context = _clean_context_images(context_images or [])
        session = AssetAgentSession(
            id=session_id or str(uuid.uuid4()),
            user_id=user.id,
            title=_title_from_message(title or cleaned_context[0].title)
            if title or cleaned_context
            else "新对话",
            context_images_json=_json_dump(
                [item.model_dump(by_alias=True) for item in cleaned_context]
            ),
            suggested_questions_json=_json_dump(_fallback_suggestions(bool(cleaned_context))),
            expires_at=_agent_legacy_expiry_at(),
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
                content=_normalize_agent_text(opening.answer) or DEFAULT_GREETING,
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
        if not session:
            raise NotFoundError("asset_agent_session_not_found", "聊天记录不存在或已过期")
        return session

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
        cards = self._image_cards(images, limit=6)

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

    def _image_cards(
        self,
        images: list[Image],
        *,
        limit: int,
    ) -> list[AssetAgentContextCard]:
        cards: list[AssetAgentContextCard] = []
        for image in images[:limit]:
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
        return cards

    def _recommended_image_cards(
        self,
        image_ids: list[str],
        *,
        message: str = "",
        preferred_family_keys: list[str] | None = None,
        title_family: str = "",
    ) -> list[AssetAgentContextCard]:
        seed_images = self._load_images(image_ids)
        if title_family:
            seed_images = [
                image for image in seed_images
                if material_title_family(image.title) == title_family
            ]
            siblings = [
                image
                for image in self.images.list_published_current_by_title_prefixes(
                    [title_family], limit=200
                )
                if material_title_family(image.title) == title_family
            ]
            return self._image_cards(
                _unique_images([*seed_images, *siblings]),
                limit=MAX_AGENT_RECOMMENDATION_CARDS,
            )
        preferred = {key for key in preferred_family_keys or [] if _expandable_material_family(key)}
        seed_family_counts: dict[str, int] = {}
        for image in seed_images:
            family = material_title_family(image.title)
            if _expandable_material_family(family):
                seed_family_counts[family] = seed_family_counts.get(family, 0) + 1

        normalized_message = message.casefold()
        expandable = preferred or {
            family
            for family, count in seed_family_counts.items()
            if count >= 2 or family in normalized_message
        }
        if not expandable:
            return self._image_cards(seed_images, limit=MAX_AGENT_RECOMMENDATION_CARDS)

        matching_seeds = (
            [image for image in seed_images if material_title_family(image.title) in expandable]
            if preferred
            else seed_images
        )
        sibling_candidates = self.images.list_published_current_by_title_prefixes(
            list(expandable),
            limit=200,
        )
        siblings = [
            image
            for image in sibling_candidates
            if material_title_family(image.title) in expandable
        ]
        ordered = _unique_images([*matching_seeds, *siblings])
        return self._image_cards(ordered, limit=MAX_AGENT_RECOMMENDATION_CARDS)

    def _selling_point_material_cards(
        self, session: AssetAgentSession, message: str
    ) -> tuple[list[AssetAgentContextCard], list[str]]:
        """Ground explicit selling-point image requests in accepted, published assets."""
        if not _is_material_card_request(message):
            return [], []
        concepts = self.concepts.list()
        mentioned = [concept for concept in concepts if concept.name in message]
        if not mentioned and any(
            phrase in message for phrase in ("这", "那", "上面", "前面", "刚才", "素材卡")
        ):
            previous_answers = (
                item.content
                for item in sorted(
                    session.messages,
                    key=lambda item: (_datetime_sort_key(item.created_at), item.id),
                    reverse=True,
                )
                if item.role == "assistant"
            )
            previous_answer = next(previous_answers, "")
            mentioned = [
                concept for concept in concepts if concept.name in previous_answer
            ]
        if not mentioned or len(mentioned) > 4:
            return [], []

        cards: list[AssetAgentContextCard] = []
        found_names: list[str] = []
        per_concept = max(1, 8 // len(mentioned))
        for concept in mentioned:
            accepted = [
                image
                for image, relation_role in self.concepts.list_assets(concept.id)
                if relation_role == "expresses" and not image.title.startswith("测试占位")
            ]
            if not accepted:
                continue
            selected = _unique_images(accepted)[:per_concept]
            cards.extend(self._image_cards(selected, limit=per_concept))
            found_names.append(concept.name)
        return cards[:8], found_names

    @staticmethod
    def _verified_selling_point_result_answer(
        names: list[str], cards: list[AssetAgentContextCard]
    ) -> str:
        joined = "、".join(f"「{name}」" for name in names)
        return (
            f"当前素材库按已确认的{joined}卖点关系找到 {len(cards)} 张已发布图片。"
            "直接点下面的图片卡可以查看和下载。"
        )

    def _explicit_title_material_family(self, message: str) -> str:
        if not any(phrase in message for phrase in ("找", "搜", "检索", "给我看", "推荐")):
            return ""
        if not any(phrase in message for phrase in ("图", "素材", "照片", "图片")):
            return ""
        candidates = self.images.list_published_current_titles_mentioned_in(message)
        families = [
            family
            for image in candidates
            for family in [material_title_family(image.title)]
            if image.title.casefold() in message.casefold()
            and _expandable_material_family(family)
        ]
        return max(families, key=len, default="")

    def _explicit_channel_material_query(
        self, message: str
    ) -> tuple[str, list[str] | None] | None:
        if not any(
            phrase in message
            for phrase in ("找", "搜", "检索", "给我看", "推荐", "有没有", "展示", "列出")
        ):
            return None
        if not any(phrase in message for phrase in ("图", "素材", "案例", "配图")) and not any(
            phrase in message for phrase in ("找", "搜", "检索", "给我看", "展示")
        ):
            return None
        matches = [
            channel.name
            for channel in self.channel_folders.channels()
            if channel.name and channel.name in message
        ]
        if not matches:
            return None
        channel = max(matches, key=len)
        folders = self.channel_folders.folders(channel)
        by_id = {folder.id: folder for folder in folders}

        def depth(folder_id: str) -> int:
            count = 0
            current = by_id.get(folder_id)
            seen: set[str] = set()
            while current and current.parent_id and current.parent_id not in seen:
                seen.add(current.parent_id)
                current = by_id.get(current.parent_id)
                count += 1
            return count

        named = [folder for folder in folders if folder.name in message]
        if not named:
            return channel, None
        chosen = max(named, key=lambda folder: (depth(folder.id), len(folder.name)))
        descendants = {chosen.id}
        while True:
            expanded = descendants | {
                folder.id for folder in folders if folder.parent_id in descendants
            }
            if expanded == descendants:
                break
            descendants = expanded
        return channel, list(descendants)

    def _verified_channel_cards(
        self,
        channel: str,
        folder_ids: list[str] | None,
        *,
        seed_image_ids: list[str],
        allowed_image_ids: list[str] | None = None,
    ) -> list[AssetAgentContextCard]:
        if allowed_image_ids is not None:
            allowed = self.images.list_published_current_for_channel(
                channel,
                folder_ids=folder_ids,
                image_ids=allowed_image_ids,
                limit=MAX_AGENT_RECOMMENDATION_CARDS,
            ) if allowed_image_ids else []
            return self._image_cards(allowed, limit=MAX_AGENT_RECOMMENDATION_CARDS)
        verified_seeds = self.images.list_published_current_for_channel(
            channel,
            folder_ids=folder_ids,
            image_ids=seed_image_ids,
            limit=MAX_AGENT_RECOMMENDATION_CARDS,
        ) if seed_image_ids else []
        local = self.images.list_published_current_for_channel(
            channel,
            folder_ids=folder_ids,
            limit=MAX_AGENT_RECOMMENDATION_CARDS,
        )
        return self._image_cards(
            _unique_images([*verified_seeds, *local]),
            limit=MAX_AGENT_RECOMMENDATION_CARDS,
        )

    @staticmethod
    def _channel_result_answer(
        answer: str, channel: str, cards: list[AssetAgentContextCard]
    ) -> str:
        if cards:
            return (
                f"本地图库中「{channel}」渠道找到 {len(cards)} 张当前已发布图片，"
                "已列在下面；按实际渠道归属核对。"
            )
        return f"{answer}\n\n本地图库中「{channel}」渠道目前没有匹配的已发布图片。"

    @staticmethod
    def _verified_title_result_answer(cards: list[AssetAgentContextCard]) -> str:
        family = material_title_family(cards[0].title)
        return (
            f"当前素材库找到「{family}」主题的 {len(cards)} 张已发布图片。"
            "直接点下面的图片卡可以查看和下载。"
        )

    def _continuation_family_keys(
        self,
        session: AssetAgentSession,
        message: str,
    ) -> list[str]:
        if not _is_same_material_family_followup(message):
            return []
        ordered_messages = sorted(
            session.messages,
            key=lambda item: (_datetime_sort_key(item.created_at), item.id),
            reverse=True,
        )
        for previous in ordered_messages:
            if previous.role != "assistant":
                continue
            families = list(
                dict.fromkeys(
                    family
                    for card in _parse_context_cards(previous.context_cards_json)
                    if card.kind == "image"
                    for family in [material_title_family(card.title)]
                    if _expandable_material_family(family)
                )
            )
            if families:
                return families
        return []

    def _recommendation_answer(
        self,
        answer: str,
        *,
        seed_image_ids: list[str],
        cards: list[AssetAgentContextCard],
        preferred_family_keys: list[str],
    ) -> str:
        if not cards:
            return answer
        card_family_counts: dict[str, int] = {}
        for card in cards:
            family = material_title_family(card.title)
            if _expandable_material_family(family):
                card_family_counts[family] = card_family_counts.get(family, 0) + 1
        seed_family_counts: dict[str, int] = {}
        for image in self._load_images(seed_image_ids):
            family = material_title_family(image.title)
            if _expandable_material_family(family):
                seed_family_counts[family] = seed_family_counts.get(family, 0) + 1
        if preferred_family_keys:
            names = "、".join(
                f"「{family}」" for family in preferred_family_keys if family in card_family_counts
            )
            return (
                f"已继续为你补齐{names}同一素材主题的当前已发布版本，"
                f"共 {len(cards)} 张；不同尺寸会一起列在下面。"
                "本轮不会混入同一卖点下的其他主题。"
            )
        expanded_families = [
            family
            for family, count in card_family_counts.items()
            if count > seed_family_counts.get(family, 0)
        ]
        if not expanded_families:
            return answer
        names = "、".join(f"「{family}」" for family in expanded_families)
        return (
            f"{answer}\n\n库内结果补充：AI Search 首批命中的数量不代表全部可用版本。"
            f"我已按{names}的同一素材主题补齐当前已发布版本，共 {len(cards)} 张；"
            "不同尺寸会一起列在下面，并以实际返回的图片卡片为准。"
        )

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

    def _history_recap_answer(self, user: User, message: str) -> str:
        normalized = "".join(message.split())
        if not (
            ("聊" in normalized and any(word in normalized for word in ("之前", "以前", "刚才")))
            or ("问" in normalized and any(word in normalized for word in ("之前", "刚才")))
            or "历史聊天" in normalized
        ):
            return ""
        prior: list[tuple[float, str]] = []
        for saved_session in self.sessions.list_for_user(user.id):
            for item in saved_session.messages:
                if item.role == "user" and item.content.strip():
                    prior.append((_datetime_sort_key(item.created_at), item.content.strip()))
        # This method runs before the current user message is persisted, so the
        # list contains only actual earlier questions from this account.
        prior.sort(key=lambda item: item[0])
        if not prior:
            return "目前保存的聊天记录里还没有更早的提问。"
        topics = "\n".join(
            f"{index}. {content}" for index, (_, content) in enumerate(prior, start=1)
        )
        return f"你之前在这个账号里依次问过：\n{topics}"

    def _save_local_history_answer(
        self, session: AssetAgentSession, answer: str
    ) -> AssetAgentChatResponse:
        suggestions = _fallback_suggestions(False)
        session.suggested_questions_json = _json_dump(suggestions)
        self._add_message(session, role="assistant", content=answer, used_model=False)
        self.sessions.save(session)
        self.uow.commit()
        return AssetAgentChatResponse(
            answer=answer,
            conversation_id=session.id,
            session=self._session_read(session),
            suggested_questions=suggestions,
            context_cards=[],
            used_model=False,
            provider_attempts=[],
        )

    def _try_ai_search_chat(
        self,
        *,
        user: User,
        session: AssetAgentSession,
        message: str,
        context_text: str,
        recommendation_family_keys: list[str],
        visual_image_url: str = "",
        response_mode: AssetAgentResponseMode = "balanced",
    ) -> VolcAiSearchChatResult | None:
        client = self.ai_search_chat
        if client is None or not getattr(client, "chat_search_configured", False):
            return None
        self.db.flush()
        chat_started_at = monotonic()
        try:
            return client.chat_search(
                _ai_search_chat_message(
                    message,
                    context_text,
                    response_mode=response_mode,
                    has_visual_image=bool(visual_image_url),
                    recommendation_family_keys=recommendation_family_keys,
                ),
                session_id=session.id,
                user_id=user.id,
                page_size=_chat_page_size(
                    self.ai_search_chat_page_size,
                    response_mode,
                    message=message,
                    has_visual_image=bool(visual_image_url),
                ),
                enable_suggestions=True,
                image_url=visual_image_url,
            )
        except VolcAiSearchClientError as exc:
            logger.warning(
                "asset_agent_ai_search_chat_failed kind=%s elapsed_ms=%d",
                _ai_search_failure_kind(exc),
                round((monotonic() - chat_started_at) * 1000),
            )
            return None

    def _library_image_bridge(
        self,
        user: User,
        payload: AssetAgentChatRequest,
    ) -> tuple[str, str]:
        if self.temporary_images is None or self.storage is None:
            return "", ""
        image_ids = list(payload.image_ids)
        if not image_ids and payload.conversation_id:
            session = self.sessions.get_for_user(user.id, payload.conversation_id)
            if session is not None:
                image_ids = [item.image_id for item in self._session_context(session)]
        images = self._load_images(image_ids)
        if not images:
            return "", ""

        image = images[0]
        path = None
        try:
            if image.thumbnail_storage_key:
                path = self.storage.thumbnail_path_for(image.thumbnail_storage_key)
                filename = f"{image.title}.jpg"
            else:
                path = self.storage.path_for(image.storage_key)
                filename = image.file_name or image.title
            with path.open("rb") as stream:
                bridged = self.temporary_images.create(
                    stream,
                    owner_id=user.id,
                    filename=filename,
                )
            return bridged.preview_url, bridged.token
        except (AppError, OSError):
            logger.warning(
                "asset_agent_library_visual_bridge_failed image_id=%s",
                image.id,
                exc_info=True,
            )
            return "", ""
        finally:
            if path is not None:
                self.storage.release(path)

    def _temporary_image_url(
        self,
        user: User,
        payload: AssetAgentChatRequest,
    ) -> str:
        token = payload.temporary_image_token
        if not token:
            return ""
        if self.temporary_images is None:
            raise AppError(
                "temporary_image_unavailable",
                "临时问图服务暂不可用，请稍后重试",
                status_code=503,
            )
        return self.temporary_images.public_url_for_owner(token, owner_id=user.id)

    def _temporary_image_title(self, payload: AssetAgentChatRequest) -> str:
        token = payload.temporary_image_token
        if not token or self.temporary_images is None:
            return ""
        return self.temporary_images.public_file(token).title

    def _delete_temporary_image(
        self,
        user: User,
        payload: AssetAgentChatRequest,
    ) -> None:
        token = payload.temporary_image_token
        if not token or self.temporary_images is None:
            return
        try:
            self.temporary_images.delete(token, owner_id=user.id)
        except AppError:
            pass

    def _delete_library_image_bridge(self, user: User, token: str) -> None:
        if not token or self.temporary_images is None:
            return
        try:
            self.temporary_images.delete(token, owner_id=user.id)
        except AppError:
            pass

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


def _uploaded_image_card(message_id: str, title: str) -> AssetAgentContextCard:
    return AssetAgentContextCard(
        kind="image",
        id=f"uploaded:{message_id}",
        title=title,
        subtitle="用户上传图片",
    )


def _saved_dialogue_context(session: AssetAgentSession) -> str:
    previous = sorted(
        session.messages,
        key=lambda item: (_datetime_sort_key(item.created_at), item.id),
    )
    lines: list[str] = []
    for item in previous:
        if item.role == "user":
            lines.append(f"用户：{item.content}")
        elif item.role == "assistant" and item.used_model and item.content.strip():
            lines.append(f"助手：{item.content}")
    if not lines:
        return ""
    return (
        "以下是当前同一对话中已经保存的实际聊天内容，按发生顺序排列。"
        "可用于理解追问或回答用户问‘之前聊过什么’；"
        "旧回答不是未经核对的洋葱业务事实，新问题仍以当前知识库为准。\n"
        + "\n".join(lines)
    )


def _sent_image_history_context(session: AssetAgentSession) -> str:
    ordered_messages = sorted(
        session.messages,
        key=lambda item: (_datetime_sort_key(item.created_at), item.id),
    )
    sent_images: list[str] = []
    for index, previous in enumerate(ordered_messages):
        if previous.role != "user":
            continue
        image_cards = [
            card
            for card in _parse_context_cards(previous.context_cards_json)
            if card.kind == "image"
        ]
        if not image_cards:
            continue
        following = next(
            (
                item
                for item in ordered_messages[index + 1 :]
                if item.role in {"user", "assistant"}
            ),
            None,
        )
        answer = (
            following.content.strip()
            if following is not None
            and following.role == "assistant"
            and following.used_model is True
            else "此前没有生成可靠的看图回答，不能根据文件名推断画面。"
        )
        for card in image_cards:
            sent_images.append(
                f"第{len(sent_images) + 1}张：{card.title}；"
                f"当时的问题：{previous.content}；当时的回答：{answer}"
            )
    if not sent_images:
        return ""
    return (
        "以下是本对话此前实际发送过的图片，顺序可供用户用‘第一张’‘前两张’等自然语言回指。"
        "这些是已保存的附件名称与先前回答，不代表本轮重新读取了旧图片像素；"
        "若先前看图失败，不要猜测画面。\n"
        + "\n".join(sent_images)
    )


def _ai_search_chat_message(
    message: str,
    context_text: str,
    *,
    response_mode: AssetAgentResponseMode = "balanced",
    has_visual_image: bool = False,
    recommendation_family_keys: list[str] | None = None,
) -> str:
    assistant_instructions = (
        "你是可自由问答的洋葱 Agent。直接回答用户这次问的问题，不必把普通问题转成"
        "卖点判断、素材检索或销售话术。涉及洋葱内部事实时，以提供的项目知识和检索到的"
        "洋葱知识库内容为依据；不要把外部同名介绍当成洋葱内部体系，资料不足就说明不确定。"
        "其他问题像普通助手一样自然回答，按需要使用 AI Search 可用的检索能力。"
    )
    company_reference = (
        "洋葱项目已确认的六大业务体系依次是："
        + "、".join(node.name for node in load_taxonomy_catalog().system_nodes)
        + "。这只是涉及洋葱业务时的事实参考，不要求把其他问题归入这些体系。"
    )
    mode_instructions = "本轮用户选择简短回答。" if response_mode == "fast" else ""
    image_instructions = (
        "本轮附带图片。回答图片问题时区分可见内容和推测，涉及洋葱业务事实时参考项目知识。"
        if has_visual_image
        else ""
    )
    recommendation_instructions = (
        "用户本轮是在追问上一轮同一素材主题的其他图片。"
        f"只允许继续检索标题属于这些素材主题的图片：{'、'.join(recommendation_family_keys or [])}；"
        "不要扩展到同一卖点下的其他素材主题，并把该主题的不同尺寸/版本尽量完整返回。"
        if recommendation_family_keys
        else ""
    )
    return "\n\n".join(
        item
        for item in (
            message,
            assistant_instructions,
            company_reference,
            mode_instructions,
            image_instructions,
            recommendation_instructions,
            "以下是用户带来的素材上下文；只在与本轮问题相关时使用。"
            if context_text.strip()
            else "",
            context_text if context_text.strip() else "",
        )
        if item
    )


def _chat_page_size(
    configured: int,
    response_mode: AssetAgentResponseMode,
    *,
    message: str = "",
    has_visual_image: bool = False,
) -> int:
    if response_mode == "fast":
        return min(configured, 4)
    if has_visual_image or any(
        phrase in message for phrase in ("找图", "图片", "配图", "素材", "几张图", "发张图")
    ):
        return configured
    return min(configured, 4)


def _stream_ai_search_chat_with_retry(
    client: VolcAiSearchClient,
    query: str,
    *,
    session_id: str,
    user_id: str,
    page_size: int,
    enable_suggestions: bool,
    image_url: str,
) -> Iterator[VolcAiSearchStreamEvent]:
    for attempt in range(2):
        answer_started = False
        try:
            for event in client.stream_chat_search(
                query,
                session_id=session_id,
                user_id=user_id,
                page_size=page_size,
                enable_suggestions=enable_suggestions,
                image_url=image_url,
            ):
                if event.content:
                    answer_started = True
                yield event
            return
        except VolcAiSearchClientError as exc:
            if (
                attempt
                or answer_started
                or not isinstance(
                    exc.__cause__,
                    (
                        httpx.ConnectError,
                        httpx.ConnectTimeout,
                        httpx.ReadTimeout,
                        httpx.RemoteProtocolError,
                    ),
                )
            ):
                raise
            logger.warning(
                "asset_agent_ai_search_stream_retry kind=%s attempt=%d",
                _ai_search_failure_kind(exc),
                attempt + 2,
            )


def _ai_search_chat_attempt(*, status: str, error: str = "") -> dict[str, Any]:
    return {
        "provider": "volc_ai_search_chat",
        "model": "chat_search",
        "status": status,
        "duration_ms": None,
        "error": error,
    }


def _ai_search_failure_kind(exc: VolcAiSearchClientError) -> str:
    cause = exc.__cause__
    if cause is None:
        return type(exc).__name__
    status = getattr(getattr(cause, "response", None), "status_code", None)
    if isinstance(status, int):
        return f"{type(cause).__name__}:{status}"
    return type(cause).__name__


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


def _agent_legacy_expiry_at() -> datetime:
    # The database column remains non-null for compatibility; Agent conversations
    # are retained until the user explicitly deletes them.
    return datetime(9999, 1, 1, tzinfo=timezone.utc)


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
    return cards[:MAX_AGENT_RECOMMENDATION_CARDS]


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
    return merged[:MAX_AGENT_RECOMMENDATION_CARDS]


def _title_from_message(message: str) -> str:
    cleaned = " ".join(message.split()).strip()
    if not cleaned:
        return "新对话"
    return f"{cleaned[:16]}…" if len(cleaned) > 16 else cleaned


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
            "它的核心卖点和体系是什么？",
            "它和相近卖点的区别是什么？",
            "帮我找表达同一卖点的其他素材",
        ]
    return [
        "洋葱都有哪些业务体系？",
        "帮我把这段介绍写得更清楚",
        "帮我找几张适合讲举一反三的图",
        "我发一张图，你帮我看看它讲了什么",
    ]


def _ai_search_unavailable_answer(*, has_image: bool, failure_kind: str = "") -> str:
    if failure_kind == "ImageUnavailable":
        return (
            "图片已加入当前对话，但在线服务这次无法读取它的画面，因此不能根据图片内容回答。"
            "请管理员配置公网可访问的图片服务地址；配置完成后可直接重问，不必重新发送图片。"
        )
    if failure_kind in {"ConnectError", "ConnectTimeout", "RemoteProtocolError"}:
        reason = "这次与 AI 搜索引擎的连接中断了。"
    elif failure_kind == "ReadTimeout":
        reason = "AI 搜索引擎这次响应超时了。"
    else:
        reason = "在线问答服务本轮没有生成可靠回答。"
    if has_image:
        return f"图片已经保留在当前对话中。{reason}请直接重试原问题，不需要重新发送图片。"
    return (
        f"{reason}请直接重试这个问题。"
        "你可以像普通 AI 助手一样提问，不需要先选择体系、卖点或发送图片。"
    )


def _needs_image_visual(message: str) -> bool:
    return any(
        phrase in message
        for phrase in (
            "讲了什么",
            "写了什么",
            "画面内容",
            "看到了什么",
            "图里",
            "图上",
            "图片里",
            "图片上",
            "照片里",
            "画面里",
        )
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


def _unique_images(values: list[Image]) -> list[Image]:
    cleaned: list[Image] = []
    seen: set[str] = set()
    for image in values:
        if image.id in seen:
            continue
        seen.add(image.id)
        cleaned.append(image)
    return cleaned


def _expandable_material_family(value: str) -> bool:
    normalized = value.strip().casefold()
    return len(normalized) >= 3 and normalized not in {
        "图片",
        "素材",
        "大图",
        "小图",
        "banner",
    }


def _is_same_material_family_followup(message: str) -> bool:
    normalized = "".join(message.split()).casefold()
    continuation_markers = (
        "其他",
        "其它",
        "其余",
        "剩下",
        "更多",
        "全部",
        "再找",
        "再给",
        "也给",
        "都找",
    )
    material_markers = ("图", "素材", "张", "找", "推荐", "返回", "返出")
    return any(marker in normalized for marker in continuation_markers) and any(
        marker in normalized for marker in material_markers
    )

def _is_material_card_request(message: str) -> bool:
    normalized = "".join(message.split())
    if "素材卡" in normalized and any(
        marker in normalized for marker in ("要", "给", "看", "找", "展示", "返回")
    ):
        return True
    return any(
        marker in normalized
        for marker in ("找", "搜", "检索", "给我看", "推荐", "展示", "列出", "返回")
    ) and any(marker in normalized for marker in ("图", "素材", "照片", "配图"))


def _normalize_agent_text(value: str) -> str:
    return value.strip().replace("\\r\\n", "\n").replace("\\n", "\n").replace("\\t", "  ")


def _clip(value: str | None, limit: int) -> str:
    if not value:
        return ""
    cleaned = " ".join(str(value).split())
    if len(cleaned) <= limit:
        return cleaned
    return f"{cleaned[:limit]}…"
