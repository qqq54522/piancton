from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from typing import Any, cast

from sqlalchemy.orm import Session

from app.ai.contracts import (
    ModelProvider,
    ModelProviderError,
    ModelProviderNotConfigured,
    ModelRequest,
    generate_json_with_attempts,
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

MAX_AGENT_SESSIONS = 20
SESSION_TTL_HOURS = 24
DEFAULT_GREETING = (
    "我是素材库 Agent。你可以把图片发给我，"
    "我会按已确认的卖点和素材信息帮你解释。"
)


class AssetAgentService:
    """Small business assistant for explaining image-library assets.

    The assistant is intentionally retrieval-first: it explains images and selling
    points from confirmed project data, then lets the model rewrite the wording.
    """

    def __init__(self, db: Session, provider: ModelProvider):
        self.db = db
        self.provider = provider
        self.last_call_attempts: tuple[dict[str, Any], ...] = ()
        self.sessions = AssetAgentSessionRepository(db)
        self.messages = AssetAgentMessageRepository(db)
        self.images = ImageRepository(db)
        self.assets = AssetRepository(db)
        self.concepts = BusinessConceptRepository(db)
        self.uow = UnitOfWork(db)

    def list_sessions(self, user: User) -> AssetAgentSessionListResponse:
        self._delete_expired()
        sessions = self.sessions.list_for_user(user.id, limit=MAX_AGENT_SESSIONS)
        self.uow.commit()
        return AssetAgentSessionListResponse(
            sessions=[self._session_read(item) for item in sessions]
        )

    def create_session(
        self,
        user: User,
        payload: AssetAgentSessionCreateRequest | None = None,
    ) -> AssetAgentSessionRead:
        self._delete_expired()
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
        self._delete_expired()
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
        self._delete_expired()
        session = self._get_session_or_404(user, session_id)
        self.sessions.delete(session)
        self.uow.commit()

    def chat_in_session(
        self,
        user: User,
        session_id: str,
        payload: AssetAgentChatRequest,
    ) -> AssetAgentChatResponse:
        self._delete_expired()
        self._get_session_or_404(user, session_id)
        payload.conversation_id = session_id
        return self.chat(user, payload)

    def chat(self, user: User, payload: AssetAgentChatRequest) -> AssetAgentChatResponse:
        message = payload.message.strip()
        if not message:
            raise AppError("empty_message", "请输入要问素材库 Agent 的问题", status_code=422)

        self._delete_expired()
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
        prompt = _agent_prompt()
        input_text = "\n\n".join(
            item
            for item in (
                f"用户问题：{message}",
                f"当前对话ID：{session.id}",
                f"已发送图片/素材上下文：\n{context_text}" if context_text else "",
                f"项目启用卖点简表：\n{self._catalog_text(groups)}",
            )
            if item
        )

        answer: str
        suggestions: list[str]
        used_model: bool
        try:
            call = generate_json_with_attempts(
                self.provider,
                ModelRequest(
                    task="asset_agent_chat",
                    prompt=prompt,
                    input_text=input_text,
                    timeout_seconds=30,
                ),
            )
            self.last_call_attempts = call.attempts
            raw = call.value
            result = AssetAgentModelResponse.model_validate(raw)
            answer = result.answer.strip()
            suggestions = _clean_suggestions(result.suggested_questions)
            used_model = True
        except (ModelProviderNotConfigured, ModelProviderError, ValueError) as exc:
            attempts = getattr(exc, "attempts", ())
            self.last_call_attempts = (
                tuple(item for item in attempts if isinstance(item, dict))
                if isinstance(attempts, (list, tuple))
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
            provider_attempts=self._provider_attempts(),
        )

    def _session_for_chat(
        self,
        user: User,
        payload: AssetAgentChatRequest,
    ) -> AssetAgentSession:
        if payload.conversation_id:
            session = self.sessions.get_for_user(user.id, payload.conversation_id)
            if session and not _is_expired(session.expires_at):
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
            expires_at=_now() + timedelta(hours=SESSION_TTL_HOURS),
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
        if not session or _is_expired(session.expires_at):
            if session:
                self.sessions.delete(session)
            raise NotFoundError("asset_agent_session_not_found", "聊天记录不存在或已过期")
        return session

    def _delete_expired(self) -> None:
        self.sessions.delete_expired(_now())

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
                    f"图片摘要：{_clip(image.image_summary, 120)}"
                    if image.image_summary
                    else "",
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
                        f"定义：{_clip(concept.definition, 120)}"
                        if concept.definition
                        else "",
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
                "我现在可以回答素材库/卖点相关问题；如果你把某张图片发送给我，"
                "我会根据素材库里已确认的卖点、搜索话术和图片摘要来解释。"
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

    def _provider_attempts(self) -> list[dict[str, Any]]:
        attempts = self.last_call_attempts
        if not isinstance(attempts, (list, tuple)) or not attempts:
            attempts = getattr(self.provider, "last_attempts", [])
        return [attempt for attempt in attempts if isinstance(attempt, dict)]


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _is_expired(value: datetime) -> bool:
    expires_at = value
    now = _now()
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)
    return expires_at <= now


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
你是“素材库业务解释 Agent”，服务对象是销售、运营和设计。
你要帮助他们理解：某张图对应什么标准卖点、适合怎么跟家长解释、与相近卖点边界在哪里。

规则：
1. 必须优先使用“已发送图片/素材上下文”和“项目启用卖点简表”里的事实。
2. 对素材库没有确认的信息，不要编造；要说“当前素材库未确认”。
3. 如果用户给了家长原话，要先判断家长真实关心点，再给销售可直接复制的话术。
4. 回答要中文、业务口吻、可落地，避免空泛夸张。
5. 只返回 JSON：{"answer":"...","suggestedQuestions":["..."]}。
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
        phrase.phrase
        for phrase in group.search_phrases
        if phrase.review_status == "accepted"
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
        phrase.phrase
        for phrase in concept.search_phrases
        if phrase.review_status == "accepted"
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
            f"当前素材关联原因：{_clip(evidence_reason, 120)}"
            if evidence_reason
            else "",
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
            "这张图适合讲哪个卖点？",
            "帮我用家长能听懂的话解释",
            "它和相近卖点的区别是什么？",
        ]
    return [
        "什么是同步校内？",
        "什么是 AI 拍题精学？",
        "哪些图适合讲考前突击？",
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
