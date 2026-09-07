from __future__ import annotations

import hashlib
import json
import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from functools import lru_cache
from typing import Any, Protocol

from app.core.config import PROJECT_DIR, get_settings
from app.models.image import Image
from app.services.vikingdb_client import VikingDBClient

logger = logging.getLogger(__name__)

REFERENCE_DIR = PROJECT_DIR / "skills" / "understand-image-search-intent" / "references"
SELLING_POINT_MAP_PATH = REFERENCE_DIR / "selling-point-map.json"
SELLING_POINT_CARDS_PATH = REFERENCE_DIR / "selling-point-decision-cards.json"


class VikingDBIndexClient(Protocol):
    @property
    def configured(self) -> bool: ...

    def upsert_documents(
        self,
        documents: list[dict[str, Any]],
        *,
        async_write: bool = False,
    ) -> object: ...

    def delete_all_documents(self) -> object: ...


@dataclass(frozen=True)
class VikingDBSyncStats:
    scanned: int = 0
    submitted: int = 0
    skipped: int = 0
    batches: int = 0


class VikingDBVectorIndexSync:
    """Best-effort sync for the VikingDB sidecar vector index."""

    def __init__(self, client: VikingDBIndexClient, *, batch_size: int = 100):
        self.client = client
        self.batch_size = max(1, min(batch_size, 100))

    @classmethod
    def disabled(cls) -> "VikingDBVectorIndexSync":
        return cls(
            VikingDBClient(
                base_url="",
                api_key="",
                collection_name="",
            )
        )

    @classmethod
    def from_settings(cls) -> "VikingDBVectorIndexSync":
        settings = get_settings()
        if not settings.vikingdb_enabled:
            return cls.disabled()
        return cls(
            VikingDBClient(
                base_url=settings.vikingdb_base_url,
                api_key=settings.vikingdb_api_key,
                collection_name=settings.vikingdb_collection_name,
                upsert_path=settings.vikingdb_upsert_path,
                search_path=settings.vikingdb_search_path,
                timeout_seconds=settings.vikingdb_timeout_seconds,
            ),
            batch_size=settings.vikingdb_batch_size,
        )

    def upsert_images(
        self,
        images: list[Image],
        *,
        dry_run: bool = False,
        async_write: bool = False,
    ) -> tuple[VikingDBSyncStats, list[dict[str, Any]]]:
        """Retired compatibility shim for the old image_asset sidecar index."""
        _ = dry_run, async_write
        return (
            VikingDBSyncStats(
                scanned=len(images),
                submitted=0,
                skipped=len(images),
                batches=0,
            ),
            [],
        )

    def upsert_knowledge_documents(
        self,
        *,
        dry_run: bool = False,
        async_write: bool = False,
    ) -> tuple[VikingDBSyncStats, list[dict[str, Any]]]:
        documents = build_vikingdb_knowledge_documents()
        return self._upsert_documents(
            documents,
            scanned=len(documents),
            dry_run=dry_run,
            async_write=async_write,
        )

    def rebuild_from_repository(
        self,
        repo: object,
        *,
        dry_run: bool = False,
        async_write: bool = False,
    ) -> tuple[VikingDBSyncStats, list[dict[str, Any]]]:
        _ = repo, dry_run, async_write
        return VikingDBSyncStats(), []

    def best_effort_upsert_image(self, image: Image) -> None:
        logger.debug(
            "skip VikingDB image sync for %s because image_asset documents are retired",
            image.id,
        )

    def reset_to_knowledge_documents(
        self,
        *,
        dry_run: bool = False,
        async_write: bool = False,
    ) -> tuple[VikingDBSyncStats, list[dict[str, Any]]]:
        if dry_run:
            return self.upsert_knowledge_documents(dry_run=True, async_write=async_write)
        self.client.delete_all_documents()
        return self.upsert_knowledge_documents(async_write=async_write)

    def _upsert_documents(
        self,
        documents: list[dict[str, Any]],
        *,
        scanned: int,
        dry_run: bool,
        async_write: bool,
    ) -> tuple[VikingDBSyncStats, list[dict[str, Any]]]:
        documents = [document for document in documents if document["search_text"].strip()]
        if dry_run:
            return (
                VikingDBSyncStats(
                    scanned=scanned,
                    submitted=0,
                    skipped=scanned - len(documents),
                    batches=0,
                ),
                documents,
            )
        if not self.client.configured or not documents:
            return (
                VikingDBSyncStats(
                    scanned=scanned,
                    submitted=0,
                    skipped=scanned - len(documents),
                    batches=0,
                ),
                [],
            )

        submitted = 0
        batches = 0
        for index in range(0, len(documents), self.batch_size):
            batch = documents[index : index + self.batch_size]
            self.client.upsert_documents(batch, async_write=async_write)
            submitted += len(batch)
            batches += 1
        return (
            VikingDBSyncStats(
                scanned=scanned,
                submitted=submitted,
                skipped=scanned - len(documents),
                batches=batches,
            ),
            [],
        )


def build_vikingdb_knowledge_documents() -> list[dict[str, Any]]:
    """Build the stable knowledge layer for system and selling-point routing.

    This intentionally excludes bulk public phrases. Public phrases can be added
    later after each system is reviewed, without changing the first two layers.
    """
    systems = _load_selling_point_systems()
    cards_by_code = _load_selling_point_cards_by_code()
    documents: list[dict[str, Any]] = []
    for system in systems:
        documents.append(_system_to_vikingdb_document(system, cards_by_code))
        for selling_point in system.get("sellingPoints", []):
            if not isinstance(selling_point, dict):
                continue
            card = cards_by_code.get(str(selling_point.get("code", "")).strip())
            if card:
                documents.append(
                    _selling_point_to_vikingdb_document(system, selling_point, card)
                )
    return documents


def _system_to_vikingdb_document(
    system: dict[str, Any],
    cards_by_code: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    code = str(system.get("code", "")).strip()
    name = str(system.get("displayName", code)).strip()
    selling_points = [
        selling_point
        for selling_point in system.get("sellingPoints", [])
        if isinstance(selling_point, dict)
    ]
    search_text = "\n".join(
        [
            f"体系：{name}",
            f"体系 code：{code}",
            "用途：第一层体系路由。只判断用户表达大方向属于哪套业务体系，不下钻证明点，不直接决定图片。",
            "包含卖点："
            + "；".join(
                f"{item.get('displayName', item.get('code'))}({item.get('code')})"
                for item in selling_points
            ),
            "体系判断信号："
            + "；".join(
                _compact_card_signal(cards_by_code.get(str(item.get("code", ""))))
                for item in selling_points
                if cards_by_code.get(str(item.get("code", "")))
            ),
            "边界：如果一句话同时涉及多个体系，保留多个候选体系；如果只有泛化提分、学习好、课程好等表达，不要强行单体系独占。",
        ]
    )
    return _base_knowledge_document(
        doc_id=f"system:{code}",
        doc_type="system",
        source_id=code,
        concept_code="default",
        search_text=search_text,
    )


def _selling_point_to_vikingdb_document(
    system: dict[str, Any],
    selling_point: dict[str, Any],
    card: dict[str, Any],
) -> dict[str, Any]:
    code = str(card.get("code", selling_point.get("code", ""))).strip()
    name = str(card.get("displayName", selling_point.get("displayName", code))).strip()
    system_name = str(system.get("displayName", system.get("code", ""))).strip()
    search_text = "\n".join(
        [
            f"卖点：{name}",
            f"卖点 code：{code}",
            f"所属体系：{system_name}({system.get('code')})",
            f"Skill 名称：{selling_point.get('skillName', '')}",
            f"一句话判定：{card.get('oneSentenceDecision', '')}",
            f"背后意思：{card.get('meaningBehind', '')}",
            f"边界逻辑：{card.get('boundaryLogic', '')}",
            f"本体定义：{card.get('definition', '')}",
            f"核心对象：{_join_items(card.get('object'))}",
            f"主动作：{_join_items(card.get('action'))}",
            f"用户目的：{_join_items(card.get('purpose'))}",
            f"正向信号：{_join_items(card.get('positiveSignals'))}",
            f"排除边界：{_join_items(card.get('boundaries'))}",
            f"易混卖点：{_join_items(card.get('confusesWith'))}",
            f"判定规则：{card.get('decisionRule', '')}",
            "使用方式：第二层卖点路由。命中一个卖点就回本地数据库取该卖点 "
            "accepted 素材；命中多个卖点就按用户原话重点顺序分别取图。",
        ]
    )
    return _base_knowledge_document(
        doc_id=f"selling_point:{code}",
        doc_type="selling_point",
        source_id=code,
        concept_code=code,
        search_text=search_text,
    )


def _base_knowledge_document(
    *,
    doc_id: str,
    doc_type: str,
    source_id: str,
    concept_code: str,
    search_text: str,
) -> dict[str, Any]:
    return {
        "doc_id": doc_id,
        "search_text": search_text,
        "doc_type": doc_type,
        "source_id": source_id,
        "concept_code": concept_code,
        "asset_group_id": "default",
        "image_id": "default",
        "channel": "all",
        "status": "active",
        "content_hash": _content_hash(search_text, "active"),
        "updated_at": _iso(None),
    }


@lru_cache
def _load_selling_point_systems() -> tuple[dict[str, Any], ...]:
    payload = json.loads(SELLING_POINT_MAP_PATH.read_text(encoding="utf-8"))
    systems = payload.get("systems")
    if not isinstance(systems, list):
        raise ValueError("selling-point-map.json 缺少 systems")
    return tuple(system for system in systems if isinstance(system, dict))


@lru_cache
def _load_selling_point_cards_by_code() -> dict[str, dict[str, Any]]:
    payload = json.loads(SELLING_POINT_CARDS_PATH.read_text(encoding="utf-8"))
    systems = payload.get("systems")
    if not isinstance(systems, list):
        raise ValueError("selling-point-decision-cards.json 缺少 systems")
    cards_by_code: dict[str, dict[str, Any]] = {}
    for system in systems:
        if not isinstance(system, dict):
            continue
        cards = system.get("cards")
        if not isinstance(cards, list):
            continue
        for card in cards:
            if not isinstance(card, dict):
                continue
            code = str(card.get("code", "")).strip()
            if code:
                cards_by_code[code] = card
    return cards_by_code


def _compact_card_signal(card: dict[str, Any] | None) -> str:
    if not card:
        return ""
    name = card.get("displayName", card.get("code", ""))
    decision = card.get("oneSentenceDecision", "")
    return f"{name}：{decision}"


def _content_hash(search_text: str, status: str) -> str:
    return hashlib.sha256(f"{status}\n{search_text}".encode("utf-8")).hexdigest()


def _iso(value: datetime | None) -> str:
    resolved = value or datetime.now(timezone.utc)
    return resolved.isoformat()


def _join_items(value: object) -> str:
    if not isinstance(value, list):
        return ""
    return "；".join(str(item).strip() for item in value if str(item).strip())
