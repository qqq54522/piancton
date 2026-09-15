from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import BinaryIO

from sqlalchemy.orm import Session

from app.core.errors import NotFoundError
from app.models.user import User
from app.schemas.auth import AvatarPreset, UserRead
from app.services.storage_service import StorageProvider

logger = logging.getLogger(__name__)


class UserAvatarService:
    """Account images use the configured private storage, never the asset index."""

    def __init__(self, db: Session, storage: StorageProvider):
        self.db = db
        self.storage = storage

    def upload(self, user: User, stream: BinaryIO) -> UserRead:
        staged = self.storage.stage(
            stream,
            max_bytes=2 * 1024 * 1024,
            max_pixels=4_000_000,
            max_long_image_pixels=4_000_000,
            long_image_min_aspect_ratio=3.0,
            thumbnail_max_size=256,
        )
        old_keys = (user.avatar_storage_key, user.avatar_thumbnail_key)
        try:
            self.storage.finalize(staged)
            user.avatar_storage_key = staged.storage_key
            user.avatar_thumbnail_key = staged.thumbnail_storage_key
            user.avatar_updated_at = datetime.now(timezone.utc)
            self.db.add(user)
            self.db.commit()
        except Exception:
            self.db.rollback()
            self.storage.discard(staged)
            raise
        self._remove_old(old_keys)
        return UserRead.model_validate(user)

    def select_preset(self, user: User, preset_id: AvatarPreset) -> UserRead:
        old_keys = (user.avatar_storage_key, user.avatar_thumbnail_key)
        user.avatar_preset_id = preset_id
        user.avatar_storage_key = None
        user.avatar_thumbnail_key = None
        user.avatar_updated_at = datetime.now(timezone.utc)
        try:
            self.db.add(user)
            self.db.commit()
        except Exception:
            self.db.rollback()
            raise
        self._remove_old(old_keys)
        return UserRead.model_validate(user)

    def thumbnail(self, user: User):
        if not user.avatar_thumbnail_key:
            raise NotFoundError("avatar_missing", "尚未上传自定义头像")
        return self.storage.thumbnail_path_for(user.avatar_thumbnail_key)

    def _remove_old(self, keys: tuple[str | None, str | None]) -> None:
        original, thumbnail = keys
        for key, is_thumbnail in ((original, False), (thumbnail, True)):
            if key:
                try:
                    self.storage.delete_key(key, thumbnail=is_thumbnail)
                except Exception:
                    logger.warning(
                        "old account avatar cleanup failed",
                        extra={"thumbnail": is_thumbnail},
                    )
