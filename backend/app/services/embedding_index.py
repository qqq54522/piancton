from __future__ import annotations

import hashlib
import json
import logging
import math
from datetime import datetime, timezone

from app.core.config import get_settings
from app.models.image import Image
from app.repositories.image_repository import ImageRepository
from app.services.semantic_search_clients import EmbeddingClient, SemanticSearchClientError

logger = logging.getLogger(__name__)


class EmbeddingIndexSync:
    """Best-effort synchronization for image semantic embeddings."""

    def __init__(self, client: EmbeddingClient):
        self.client = client

    @classmethod
    def disabled(cls) -> "EmbeddingIndexSync":
        return cls(
            EmbeddingClient(
                base_url="",
                api_key="",
                model_name="",
            )
        )

    @classmethod
    def from_settings(cls) -> "EmbeddingIndexSync":
        settings = get_settings()
        return cls(
            EmbeddingClient(
                base_url=settings.embedding_base_url,
                api_key=settings.embedding_api_key,
                model_name=settings.embedding_model_name,
                timeout_seconds=settings.embedding_timeout_seconds,
            )
        )

    def upsert_image(self, repo: ImageRepository, image: Image) -> None:
        if not self.client.configured:
            return
        document_text = image_to_embedding_document(image)
        if not document_text.strip():
            return
        content_hash = embedding_content_hash(document_text, self.client.model_name)
        if (
            image.embedding
            and image.embedding.model_name == self.client.model_name
            and image.embedding.content_hash == content_hash
        ):
            return
        try:
            vector = self.client.embed([document_text])[0]
            repo.upsert_embedding(
                image,
                model_name=self.client.model_name,
                dimension=len(vector),
                content_hash=content_hash,
                document_text=document_text,
                vector_json=json.dumps(vector, separators=(",", ":")),
                updated_at=datetime.now(timezone.utc),
            )
        except (IndexError, SemanticSearchClientError, TypeError, ValueError):
            logger.warning("failed to sync image embedding", exc_info=True)


def image_to_embedding_document(image: Image) -> str:
    business_labels = [
        label for label in image.business_labels if label.review_status != "rejected"
    ]
    parts = [
        f"标题：{image.title}",
        f"语义总结：{image.image_summary}" if image.image_summary else "",
        "隐形标签：" + "、".join(item.tag_name for item in image.content_tags),
        "业务标签：" + "、".join(_business_label_name(label) for label in business_labels),
        "人工标签：" + "、".join(link.tag.name for link in image.tag_links),
        "分类：" + "、".join(item.name for item in image.categories),
    ]
    return "\n".join(part for part in parts if part.strip() and not part.endswith("："))


def embedding_content_hash(document_text: str, model_name: str) -> str:
    payload = f"{model_name}\n{document_text}".encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def cosine_similarity(left: list[float], right: list[float]) -> float:
    if not left or not right or len(left) != len(right):
        return 0.0
    dot = sum(a * b for a, b in zip(left, right))
    left_norm = math.sqrt(sum(a * a for a in left))
    right_norm = math.sqrt(sum(b * b for b in right))
    if left_norm == 0 or right_norm == 0:
        return 0.0
    return dot / (left_norm * right_norm)


def load_vector(vector_json: str) -> list[float]:
    value = json.loads(vector_json)
    if not isinstance(value, list):
        return []
    return [float(item) for item in value]


def _business_label_name(label) -> str:
    if label.tag.parent:
        return f"{label.tag.parent.name} > {label.tag.name}"
    return label.tag.name
