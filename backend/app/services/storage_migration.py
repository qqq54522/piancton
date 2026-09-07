"""Copy and verify one image before changing its location; retain local sources."""

from __future__ import annotations

import hashlib
import uuid
from pathlib import Path

from app.core.errors import AppError
from app.services.storage_service import LocalStorageProvider
from app.services.tos_storage import REMOTE_PREFIX, TosStorageProvider


def digest(path: Path) -> str:
    result = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            result.update(chunk)
    return result.hexdigest()


class StorageMigrationService:
    def __init__(self, db, remote: TosStorageProvider):
        self.db = db
        self.remote = remote
        self.local = LocalStorageProvider(remote.root)

    def migrate(self, image) -> bool:
        if image.storage_key.startswith(REMOTE_PREFIX):
            return False
        files = [("storage_key", self.local.path_for(image.storage_key), image.media_type, False)]
        if image.thumbnail_storage_key:
            files.append(
                (
                    "thumbnail_storage_key",
                    self.local.thumbnail_path_for(image.thumbnail_storage_key),
                    "image/jpeg",
                    True,
                )
            )
        created = []
        try:
            for field, source, media_type, thumbnail in files:
                key = f"{REMOTE_PREFIX}{uuid.uuid4()}{source.suffix}"
                created.append((key, thumbnail))
                self.remote.upload_file(key, source, media_type, thumbnail=thumbnail)
                fetched = (
                    self.remote.thumbnail_path_for(key) if thumbnail else self.remote.path_for(key)
                )
                try:
                    if digest(source) != digest(fetched):
                        raise AppError("migration_verify_failed", "迁移文件校验不一致")
                finally:
                    self.remote.release(fetched)
                setattr(image, field, key)
            self.db.commit()
            return True
        except Exception:
            self.db.rollback()
            for key, thumbnail in created:
                try:
                    self.remote.delete_key(key, thumbnail=thumbnail)
                except AppError:
                    # Keep the original failure; the CLI reports failed migration.
                    pass
            raise
