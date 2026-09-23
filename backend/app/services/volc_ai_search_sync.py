from __future__ import annotations

import base64
import logging
from datetime import timezone
from typing import Any, Protocol
from urllib.parse import urljoin

from app.models.image import Image
from app.services.image_semantic_profile_service import ImageSemanticProfileService
from app.services.query_expansion_service import unique
from app.services.storage_service import StorageProvider
from app.services.volc_ai_search_client import (
    VolcAiSearchClient,
    VolcAiSearchClientError,
)

logger = logging.getLogger(__name__)


class AiSearchIndexClient(Protocol):
    @property
    def configured(self) -> bool: ...

    def write_documents(self, documents: list[dict[str, Any]]) -> dict[str, Any]: ...

    def delete_documents(self, ids: list[str]) -> dict[str, Any]: ...


class VolcAiSearchIndexSync:
    """Best-effort sync from the authoritative image DB to Volc AI Search."""

    def __init__(
        self,
        client: AiSearchIndexClient,
        *,
        enabled: bool,
        public_base_url: str,
        image_client: AiSearchIndexClient | None = None,
        image_enabled: bool = False,
        image_storage: StorageProvider | None = None,
    ):
        self.client = client
        self.enabled = enabled
        self.public_base_url = public_base_url.rstrip("/")
        self.profile = ImageSemanticProfileService()
        self.image_client = image_client
        self.image_enabled = image_enabled
        self.image_storage = image_storage

    @classmethod
    def disabled(cls) -> "VolcAiSearchIndexSync":
        return cls(
            VolcAiSearchClient(
                base_url="",
                api_key="",
                dataset_id="",
            ),
            enabled=False,
            public_base_url="",
        )

    def upsert_image(self, image: Image) -> None:
        if not (
            (self.enabled and self.client.configured)
            or (self.image_enabled and self.image_client and self.image_client.configured)
        ):
            return
        if image.deleted_at is not None:
            self.delete_image(image.id)
            return
        try:
            if self.enabled and self.client.configured:
                self.client.write_documents([self.document_for_image(image)])
            if self.image_enabled and self.image_client and self.image_client.configured:
                if self._reverse_searchable(image):
                    self.image_client.write_documents([self.reverse_document_for_image(image)])
                else:
                    self.image_client.delete_documents([image.id])
        except VolcAiSearchClientError:
            logger.warning("failed to sync image to Volc AI Search", exc_info=True)

    def delete_image(self, image_id: str) -> None:
        if not (
            (self.enabled and self.client.configured)
            or (self.image_enabled and self.image_client and self.image_client.configured)
        ):
            return
        try:
            if self.enabled and self.client.configured:
                self.client.delete_documents([image_id])
            if self.image_enabled and self.image_client and self.image_client.configured:
                self.image_client.delete_documents([image_id])
        except VolcAiSearchClientError:
            logger.warning("failed to delete image from Volc AI Search", exc_info=True)

    def document_for_image(self, image: Image) -> dict[str, Any]:
        channel = _split_channel_value(image.channel)
        is_scene_image = (
            bool(image.asset_group.is_scene_image)
            if image.asset_group and image.asset_group.is_scene_image is not None
            else False
        )
        return {
            "_id": image.id,
            "doc_id": f"image:{image.id}",
            "image_id": image.id,
            "identity_code": image.identity_code or "",
            "title": image.title,
            "channel": channel,
            "image_url": self._absolute_url(f"/api/images/{image.id}/thumbnail"),
            "thumbnail_url": self._absolute_url(f"/api/images/{image.id}/thumbnail"),
            "detail_url": self._absolute_url(f"/image/{image.id}"),
            "updated_at": _iso_datetime(image.created_at),
            "image_width": int(image.width or 0),
            "image_height": int(image.height or 0),
            "is_scene_image": is_scene_image,
            "status": "published" if image.deleted_at is None else "deleted",
            "search_text": self._search_text(image, channel, is_scene_image),
        }

    def reverse_document_for_image(self, image: Image) -> dict[str, Any]:
        """Minimal image-only document for Viking Image-to-Image Search."""
        visual_image = self._absolute_url(f"/api/images/{image.id}/thumbnail")
        if self.image_storage is not None and image.thumbnail_storage_key:
            try:
                path = self.image_storage.thumbnail_path_for(image.thumbnail_storage_key)
                encoded = base64.b64encode(path.read_bytes()).decode("ascii")
                visual_image = f"data:image/jpeg;base64,{encoded}"
            except (OSError, ValueError):
                logger.warning("failed to encode image thumbnail for reverse index", exc_info=True)
        return {
            "_id": image.id,
            "image_id": image.id,
            "visual_image": visual_image,
            "status": "published" if image.deleted_at is None else "deleted",
        }

    @staticmethod
    def _reverse_searchable(image: Image) -> bool:
        """Keep drafts and superseded versions out of the reverse-search gallery."""
        if image.deleted_at is not None or not image.is_current:
            return False
        return image.asset_group is None or image.asset_group.publish_status == "published"

    def _absolute_url(self, path: str) -> str:
        if not self.public_base_url:
            return path
        return urljoin(f"{self.public_base_url}/", path.lstrip("/"))

    def _search_text(self, image: Image, channel: list[str], is_scene_image: bool) -> str:
        group = image.asset_group
        phrases = []
        concept_lines = []
        proof_lines = []
        if group:
            phrases = [
                item.phrase
                for item in group.search_phrases
                if item.review_status == "accepted" and item.phrase
            ]
            source_notes = [
                item.note
                for item in group.source_links
                if item.note
            ]
            for link in group.concept_links:
                if link.review_status == "rejected" or link.relation_role == "excludes":
                    continue
                concept = link.concept
                if not concept:
                    continue
                concept_lines.extend(
                    [
                        concept.name,
                        concept.code,
                        concept.definition or "",
                        concept.recommendation_text or "",
                    ]
                )
                concept_lines.extend(
                    phrase.phrase
                    for phrase in concept.search_phrases
                    if phrase.review_status == "accepted" and phrase.phrase
                )
            if group.primary_proof_point_code:
                proof_lines.append(f"证明点：{group.primary_proof_point_code}")
            if group.primary_evidence_point_code:
                proof_lines.append(f"证据表达点：{group.primary_evidence_point_code}")

        semantic_terms = self.profile.profile_terms(image)
        lines = [
            f"图片标题：{image.title}",
            f"原始文件名：{image.file_name}",
            f"图片身份码：{image.identity_code or ''}",
            f"使用渠道：{'、'.join(channel)}",
            f"图片类型：{'场景图' if is_scene_image else '非场景图'}",
            f"素材组标题：{group.title if group else image.title}",
            f"图片摘要：{image.image_summary or ''}",
            "素材备注：" + "；".join(source_notes if group else []),
            "素材搜索话术：" + "；".join(phrases),
            "业务卖点：" + "；".join(unique(concept_lines)),
            "画面与场景：" + "；".join(semantic_terms),
            "业务层级：" + "；".join(proof_lines),
        ]
        return "\n".join(line for line in lines if line.strip() and not line.endswith("："))


def _iso_datetime(value) -> str:
    if value is None:
        return ""
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.isoformat()


def _split_channel_value(value: str | None) -> list[str]:
    if not value:
        return []
    normalized = value.replace(",", "、").replace("，", "、").replace("/", "、").replace("／", "、")
    return [
        item.strip()
        for item in normalized.split("、")
        if item.strip()
    ]
