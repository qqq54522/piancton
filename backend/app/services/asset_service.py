from __future__ import annotations

import json
from datetime import datetime, timezone
from io import BytesIO
from pathlib import Path
from typing import BinaryIO
from urllib.parse import urlparse
from zipfile import ZIP_DEFLATED, ZipFile

from app.core.errors import AppError, NotFoundError
from app.models.asset import AssetGroup, AssetSourceLink
from app.models.image import Image
from app.repositories.asset_repository import AssetRepository
from app.repositories.image_repository import ImageRepository
from app.schemas.asset import AssetGroupRead, AssetSourceLinkCreate, AssetSourceLinkUpdate
from app.services.asset_identity_service import AssetIdentityService
from app.services.asset_serializers import asset_group_to_read
from app.services.image_title_service import ImageTitleService
from app.services.search_index_sync import SearchIndexSync
from app.services.storage_service import StorageProvider
from app.services.unit_of_work import UnitOfWork
from app.services.vikingdb_vector_index import VikingDBVectorIndexSync

ASSET_ROLES = {"derivative", "alternative", "revision"}


class AssetService:
    """Owns asset-group composition and delayed image variants."""

    def __init__(
        self,
        db,
        storage: StorageProvider,
        max_upload_bytes: int,
        max_image_pixels: int,
        thumbnail_max_size: int,
        search_index: SearchIndexSync | None = None,
        vector_index: VikingDBVectorIndexSync | None = None,
    ):
        self.assets = AssetRepository(db)
        self.images = ImageRepository(db)
        self.storage = storage
        self.max_upload_bytes = max_upload_bytes
        self.max_image_pixels = max_image_pixels
        self.thumbnail_max_size = thumbnail_max_size
        self.search_index = search_index or SearchIndexSync.from_settings()
        self.vector_index = vector_index or VikingDBVectorIndexSync.disabled()
        self.uow = UnitOfWork(db)
        self.image_titles = ImageTitleService(db)
        self.identities = AssetIdentityService(db)

    def list(self) -> list[AssetGroupRead]:
        return [asset_group_to_read(item) for item in self.assets.list()]

    def get(self, group_id: str, *, include_source_links: bool = False) -> AssetGroupRead:
        return asset_group_to_read(
            self._get(group_id),
            include_source_links=include_source_links,
        )

    def add_variant(
        self,
        group_id: str,
        stream: BinaryIO,
        original_name: str,
        title: str,
        role: str,
        channel: str | None,
        uploader: str,
    ) -> AssetGroupRead:
        group = self._get(group_id)
        if role not in ASSET_ROLES:
            raise AppError("invalid_asset_role", "追加素材只能是延展图、备选图或修订版")
        staged = self.storage.stage(
            stream,
            self.max_upload_bytes,
            self.max_image_pixels,
            self.thumbnail_max_size,
        )
        requested_title = title.strip() or Path(original_name).stem
        resolved_title = self.image_titles.resolve(requested_title)
        version_no = max((image.version_no for image in group.images), default=0) + 1
        resolved_channel = self._resolve_version_channel(group, channel)
        image = Image(
            version_code=self.identities.allocate_version_code(group.asset_code, version_no),
            title=resolved_title,
            file_name=original_name,
            storage_key=staged.storage_key,
            thumbnail_storage_key=staged.thumbnail_storage_key,
            media_type=staged.media_type,
            size_bytes=staged.size_bytes,
            uploader=uploader,
            asset_group=group,
            asset_role=role,
            width=staged.width,
            height=staged.height,
            aspect_ratio=staged.width / staged.height,
            channel=resolved_channel,
            version_no=version_no,
            is_current=True,
        )
        try:
            self.images.add(image)
            self.identities.register_image(image)
            self.storage.finalize(staged)
            self.uow.commit()
        except Exception:
            self.uow.rollback()
            self.storage.discard(staged)
            raise
        self.search_index.upsert_image(image)
        self.vector_index.best_effort_upsert_image(image)
        # Group-level relations and accepted phrases are inherited by reference.
        return asset_group_to_read(self._get(group_id))

    def replace_primary(
        self,
        group_id: str,
        stream: BinaryIO,
        original_name: str,
        title: str,
        channel: str | None,
        uploader: str,
    ) -> AssetGroupRead:
        group = self._get(group_id)
        staged = self.storage.stage(
            stream,
            self.max_upload_bytes,
            self.max_image_pixels,
            self.thumbnail_max_size,
        )
        requested_title = title.strip() or Path(original_name).stem
        resolved_title = self.image_titles.resolve(requested_title)
        version_no = max((image.version_no for image in group.images), default=0) + 1
        previous_primary = next(
            (image for image in group.images if image.id == group.primary_image_id),
            None,
        )
        resolved_channel = self._resolve_version_channel(group, channel, previous_primary)
        if previous_primary:
            previous_primary.asset_role = "revision"
            previous_primary.is_current = False
        image = Image(
            version_code=self.identities.allocate_version_code(group.asset_code, version_no),
            title=resolved_title,
            file_name=original_name,
            storage_key=staged.storage_key,
            thumbnail_storage_key=staged.thumbnail_storage_key,
            media_type=staged.media_type,
            size_bytes=staged.size_bytes,
            uploader=uploader,
            asset_group=group,
            asset_role="primary",
            width=staged.width,
            height=staged.height,
            aspect_ratio=staged.width / staged.height,
            channel=resolved_channel,
            version_no=version_no,
            is_current=True,
        )
        try:
            self.images.add(image)
            group.primary_image_id = image.id
            group.title = image.title
            self.assets.save(group)
            self.identities.register_image(image)
            self.storage.finalize(staged)
            self.uow.commit()
        except Exception:
            self.uow.rollback()
            self.storage.discard(staged)
            raise
        if previous_primary:
            self.search_index.delete_image(previous_primary.id)
            self.vector_index.best_effort_upsert_image(previous_primary)
        self.search_index.upsert_image(image)
        self.vector_index.best_effort_upsert_image(image)
        return asset_group_to_read(self._get(group_id))

    def delete_variant(self, group_id: str, image_id: str) -> AssetGroupRead:
        group = self._get(group_id)
        image = next(
            (
                item
                for item in group.images
                if item.id == image_id and item.deleted_at is None
            ),
            None,
        )
        if not image:
            raise NotFoundError("asset_variant_not_found", "素材组中不存在该版本")
        if image.id == group.primary_image_id:
            raise AppError(
                "cannot_delete_primary_image",
                "正式主图不能作为延展版本删除，请先替换主图",
            )

        image.deleted_at = datetime.now(timezone.utc)
        self.images.save(image)
        self.uow.commit()
        self.search_index.delete_image(image.id)
        self.vector_index.best_effort_upsert_image(image)
        return asset_group_to_read(self._get(group_id))

    def add_source_link(
        self,
        group_id: str,
        payload: AssetSourceLinkCreate,
        actor_username: str,
    ) -> AssetGroupRead:
        group = self._get(group_id)
        link = AssetSourceLink(
            asset_group=group,
            label=payload.label.strip(),
            url=_normalize_source_url(payload.url),
            link_type=payload.link_type,
            note=_clean_optional(payload.note),
            created_by=actor_username,
        )
        self.assets.add(link)
        self.uow.commit()
        return asset_group_to_read(
            self._get(group_id),
            include_source_links=True,
        )

    def update_source_link(
        self,
        group_id: str,
        link_id: str,
        payload: AssetSourceLinkUpdate,
    ) -> AssetGroupRead:
        self._get(group_id)
        link = self.assets.get_source_link(group_id, link_id)
        if not link:
            raise NotFoundError("asset_source_link_not_found", "源文件链接不存在")
        values = payload.model_dump(exclude_unset=True)
        if "label" in values and values["label"] is not None:
            link.label = values["label"].strip()
        if "url" in values and values["url"] is not None:
            link.url = _normalize_source_url(values["url"])
        if "link_type" in values and values["link_type"] is not None:
            link.link_type = values["link_type"]
        if "note" in values:
            link.note = _clean_optional(values["note"])
        self.assets.save(link)
        self.uow.commit()
        return asset_group_to_read(
            self._get(group_id),
            include_source_links=True,
        )

    def delete_source_link(self, group_id: str, link_id: str) -> AssetGroupRead:
        self._get(group_id)
        link = self.assets.get_source_link(group_id, link_id)
        if not link:
            raise NotFoundError("asset_source_link_not_found", "源文件链接不存在")
        self.assets.delete(link)
        self.uow.commit()
        return asset_group_to_read(
            self._get(group_id),
            include_source_links=True,
        )

    def export_bundle(
        self,
        group_id: str,
        *,
        include_source_links: bool = True,
    ) -> tuple[str, bytes]:
        group = self._get(group_id)
        buffer = BytesIO()
        with ZipFile(buffer, "w", compression=ZIP_DEFLATED) as archive:
            self._write_bundle_group(
                archive,
                group,
                folder_prefix="",
                include_source_links=include_source_links,
            )
        return f"{_safe_archive_name(group.title)}.zip", buffer.getvalue()

    def export_bundles(
        self,
        group_ids: list[str],
        *,
        include_source_links: bool,
    ) -> tuple[str, bytes]:
        unique_ids = list(dict.fromkeys(group_ids))
        groups = [self._get(group_id) for group_id in unique_ids]
        buffer = BytesIO()
        root_manifest = {
            "bundleCount": len(groups),
            "includeSourceLinks": include_source_links,
            "groups": [],
        }
        with ZipFile(buffer, "w", compression=ZIP_DEFLATED) as archive:
            for index, group in enumerate(groups, start=1):
                folder_prefix = f"{index:02d}-{_safe_archive_name(group.title)}/"
                group_manifest = self._write_bundle_group(
                    archive,
                    group,
                    folder_prefix=folder_prefix,
                    include_source_links=include_source_links,
                )
                root_manifest["groups"].append(
                    {
                        "id": group.id,
                        "title": group.title,
                        "manifestPath": f"{folder_prefix}manifest.json",
                        "imageCount": len(group_manifest["images"]),
                    }
                )
            archive.writestr(
                "manifest.json",
                json.dumps(root_manifest, ensure_ascii=False, indent=2),
            )
        return "asset-bundles.zip", buffer.getvalue()

    def _write_bundle_group(
        self,
        archive: ZipFile,
        group: AssetGroup,
        *,
        folder_prefix: str,
        include_source_links: bool,
    ) -> dict:
        manifest = {
            "id": group.id,
            "title": group.title,
            "primaryImageId": group.primary_image_id,
            "approvalStatus": group.approval_status,
            "publishStatus": group.publish_status,
            "styleLabel": group.style_label,
            "isSceneImage": group.is_scene_image,
            "sourceLinks": [
                {
                    "label": link.label,
                    "url": link.url,
                    "linkType": link.link_type,
                    "note": link.note,
                }
                for link in group.source_links
            ] if include_source_links else [],
            "searchPhrases": [
                {
                    "phrase": phrase.phrase,
                    "origin": phrase.origin,
                    "reviewStatus": phrase.review_status,
                    "weight": phrase.weight,
                }
                for phrase in group.search_phrases
            ],
            "conceptLinks": [
                {
                    "conceptCode": link.concept.code,
                    "conceptName": link.concept.name,
                    "relationRole": link.relation_role,
                    "origin": link.origin,
                    "reviewStatus": link.review_status,
                    "evidenceReason": link.evidence_reason,
                }
                for link in group.concept_links
            ],
            "images": [],
        }
        for image in sorted(
            (item for item in group.images if item.deleted_at is None),
            key=lambda item: (item.version_no, item.created_at),
        ):
            extension = Path(image.file_name).suffix or Path(image.storage_key).suffix
            safe_name = _safe_archive_name(image.title or image.file_name)
            archive_name = (
                f"{folder_prefix}images/{image.version_no:02d}-"
                f"{image.asset_role}-{safe_name}{extension}"
            )
            manifest["images"].append(
                {
                    "id": image.id,
                    "title": image.title,
                    "fileName": image.file_name,
                    "archivePath": archive_name,
                    "mediaType": image.media_type,
                    "width": image.width,
                    "height": image.height,
                    "channel": image.channel,
                    "assetRole": image.asset_role,
                    "versionNo": image.version_no,
                    "isCurrent": image.is_current,
                }
            )
            archive.write(self.storage.path_for(image.storage_key), archive_name)
        archive.writestr(
            f"{folder_prefix}manifest.json",
            json.dumps(manifest, ensure_ascii=False, indent=2),
        )
        return manifest

    def _get(self, group_id: str) -> AssetGroup:
        group = self.assets.get(group_id)
        if not group:
            raise NotFoundError("asset_group_not_found", "素材组不存在")
        return group

    def _resolve_version_channel(
        self,
        group: AssetGroup,
        channel: str | None,
        primary: Image | None = None,
    ) -> str | None:
        requested = (channel or "").strip()
        if requested:
            return requested
        primary_image = primary or next(
            (image for image in group.images if image.id == group.primary_image_id),
            None,
        )
        if not primary_image:
            return None
        return (primary_image.channel or "").strip() or None


def _normalize_source_url(value: str) -> str:
    url = value.strip()
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise AppError("invalid_source_link_url", "源文件链接必须是 http 或 https 地址")
    return url


def _clean_optional(value: str | None) -> str | None:
    if value is None:
        return None
    cleaned = value.strip()
    return cleaned or None


def _safe_archive_name(value: str) -> str:
    cleaned = "".join(
        char if char.isalnum() or char in {"-", "_", "."} else "_"
        for char in value.strip()
    ).strip("._")
    return cleaned or "asset"
