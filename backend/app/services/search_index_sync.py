from __future__ import annotations

import logging
from typing import Protocol

from app.core.config import get_settings
from app.models.image import Image
from app.services.meilisearch_client import MeilisearchClient, MeilisearchClientError
from app.services.search_index import image_to_search_document

logger = logging.getLogger(__name__)


class SearchIndexClient(Protocol):
    @property
    def configured(self) -> bool: ...

    def configure_index(self) -> str | None: ...

    def add_documents(self, documents: list[dict]) -> str | None: ...

    def delete_documents(self, image_ids: list[str]) -> str | None: ...


class SearchIndexSync:
    """Best-effort synchronization for the derived search index.

    The relational database is authoritative. Search synchronization must never
    break upload, edit, restore or AI analysis flows; failures are logged and can
    be repaired with the full rebuild script.
    """

    def __init__(self, client: SearchIndexClient):
        self.client = client

    @classmethod
    def from_settings(cls) -> "SearchIndexSync":
        settings = get_settings()
        return cls(
            MeilisearchClient(
                url=settings.meilisearch_url,
                api_key=settings.meilisearch_api_key,
                index=settings.meilisearch_index,
                timeout_seconds=settings.search_timeout_seconds,
            )
        )

    def upsert_image(self, image: Image) -> None:
        if not self.client.configured:
            return
        try:
            self.client.configure_index()
            self.client.add_documents([image_to_search_document(image)])
        except MeilisearchClientError:
            logger.warning("failed to sync image search document", exc_info=True)

    def delete_image(self, image_id: str) -> None:
        if not self.client.configured:
            return
        try:
            self.client.delete_documents([image_id])
        except MeilisearchClientError:
            logger.warning("failed to delete image search document", exc_info=True)

