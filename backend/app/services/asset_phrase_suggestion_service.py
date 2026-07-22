from __future__ import annotations

from typing import BinaryIO

from app.schemas.ai import AssetSearchPhraseSuggestion
from app.services.ai_service import AiService
from app.services.storage_service import StorageProvider


class AssetPhraseSuggestionService:
    """Generate pre-upload phrase candidates without persisting the image or AI output."""

    def __init__(
        self,
        ai: AiService,
        storage: StorageProvider,
        *,
        max_upload_bytes: int,
        max_image_pixels: int,
        thumbnail_max_size: int,
    ):
        self.ai = ai
        self.storage = storage
        self.max_upload_bytes = max_upload_bytes
        self.max_image_pixels = max_image_pixels
        self.thumbnail_max_size = thumbnail_max_size

    def generate(
        self,
        stream: BinaryIO,
        *,
        count: int,
        title: str = "",
        concept_code: str = "",
    ) -> AssetSearchPhraseSuggestion:
        staged = self.storage.stage(
            stream,
            self.max_upload_bytes,
            self.max_image_pixels,
            self.thumbnail_max_size,
        )
        try:
            return self.ai.generate_asset_search_phrases(
                staged.temp_path,
                count=count,
                title=title,
                concept_code=concept_code,
                image_media_type=staged.media_type,
            )
        finally:
            self.storage.discard(staged)
