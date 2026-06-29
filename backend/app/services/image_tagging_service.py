from __future__ import annotations

from app.core.errors import AppError, NotFoundError
from app.models.image import ContentTag, Image, ImageBusinessLabel, ImageTag
from app.models.tag import Tag
from app.repositories.image_repository import ImageRepository
from app.repositories.tag_repository import TagRepository
from app.schemas.image import ImageDetailRead, ImageRead
from app.services.embedding_index import EmbeddingIndexSync
from app.services.related_image_service import RelatedImageService
from app.services.search_index_sync import SearchIndexSync
from app.services.serializers import image_to_detail, image_to_read
from app.services.unit_of_work import UnitOfWork


class ImageTaggingService:
    def __init__(
        self,
        db,
        search_index: SearchIndexSync | None = None,
        embedding_index: EmbeddingIndexSync | None = None,
    ):
        self.images = ImageRepository(db)
        self.tags = TagRepository(db)
        self.uow = UnitOfWork(db)
        self.search_index = search_index or SearchIndexSync.from_settings()
        self.embedding_index = embedding_index or EmbeddingIndexSync.disabled()
        self.related_images = RelatedImageService(self.images)

    def update_tags(
        self,
        image_id: str,
        tag_ids: list[str],
        primary_tag_id: str | None = None,
    ) -> ImageRead:
        image = self._get(image_id)
        tags = self.validate_tags(tag_ids)
        self.images.replace_tags(image, tags)
        image.business_labels[:] = [
            label for label in image.business_labels if label.origin != "manual"
        ]
        image.business_labels.extend(self.manual_business_labels(tags, primary_tag_id))
        self.embedding_index.upsert_image(self.images, image)
        self.images.save(image)
        self.uow.commit()
        self._sync_index(image.id)
        return image_to_read(self._get(image.id))

    def review_business_label(
        self,
        image_id: str,
        label_id: str,
        review_status: str,
    ) -> ImageDetailRead:
        image = self._get(image_id)
        label = self.images.get_business_label(image_id, label_id)
        if not label:
            raise NotFoundError("business_label_not_found", "业务标签建议不存在")
        if label.origin != "ai":
            raise AppError("manual_label_not_reviewable", "人工业务标签不需要审核")
        label.review_status = review_status
        if review_status == "accepted":
            self._promote_ai_label_to_manual(image, label)
        elif review_status == "rejected":
            self._remove_rejected_ai_label_outputs(image, label)
        self.embedding_index.upsert_image(self.images, image)
        self.images.save(image)
        self.uow.commit()
        self._sync_index(image.id)
        return self._detail(image.id)

    def validate_tags(self, tag_ids: list[str]) -> list[Tag]:
        unique_ids = list(dict.fromkeys(tag_ids))
        if not unique_ids:
            raise AppError("image_tag_required", "图片必须至少选择一个可打标标签")
        tags = self.tags.get_many(unique_ids)
        found = {tag.id for tag in tags}
        missing = [tag_id for tag_id in unique_ids if tag_id not in found]
        if missing:
            raise AppError("unknown_tags", "存在无效标签", details=missing)
        non_assignable_ids = self.tags.non_assignable_ids(unique_ids)
        if non_assignable_ids:
            raise AppError(
                "tag_not_assignable",
                "图片只能选择已启用且允许打标的标签",
                details=non_assignable_ids,
            )
        return tags

    def manual_business_labels(
        self,
        tags: list[Tag],
        primary_tag_id: str | None,
    ) -> list[ImageBusinessLabel]:
        if not tags:
            return []
        tags_by_id = {tag.id: tag for tag in tags}
        selected_primary_id = primary_tag_id or tags[0].id
        if selected_primary_id not in tags_by_id:
            raise AppError(
                "primary_tag_required",
                "主业务标签必须来自已选择的标签",
                details={"primaryTagId": selected_primary_id},
            )
        labels: list[ImageBusinessLabel] = []
        for tag in tags:
            labels.append(
                ImageBusinessLabel(
                    tag=tag,
                    label_code=tag.code or tag.id,
                    origin="manual",
                    role="primary" if tag.id == selected_primary_id else "additional",
                    review_status="accepted",
                    confidence=1.0,
                )
            )
        return labels

    def expected_search_word_tags(self, words: list[str]) -> list[ContentTag]:
        content_tags: list[ContentTag] = []
        seen: set[str] = set()
        for word in words:
            name = word.strip()
            if not name or name in seen:
                continue
            seen.add(name)
            content_tags.append(
                ContentTag(
                    tag_name=name[:100],
                    confidence=1.0,
                    dimension="用户预期搜索词",
                )
            )
        return content_tags

    def _promote_ai_label_to_manual(
        self,
        image: Image,
        label: ImageBusinessLabel,
    ) -> None:
        if not any(link.tag_id == label.tag_id for link in image.tag_links):
            image.tag_links.append(ImageTag(tag=label.tag))

        if any(
            item.origin == "manual" and item.tag_id == label.tag_id
            for item in image.business_labels
        ):
            return

        has_manual_primary = any(
            item.origin == "manual" and item.role == "primary"
            for item in image.business_labels
        )
        image.business_labels.append(
            ImageBusinessLabel(
                image=image,
                tag=label.tag,
                label_code=label.label_code,
                origin="manual",
                role="additional" if has_manual_primary else "primary",
                review_status="accepted",
                confidence=1.0,
                evidence_level=label.evidence_level,
                reason=(
                    "设计师接受 AI 建议"
                    + (f"：{label.reason}" if label.reason else "")
                ),
            )
        )

    def _business_label_display_name(self, label: ImageBusinessLabel) -> str:
        if label.tag.parent:
            return f"{label.tag.parent.name} > {label.tag.name}"
        return label.tag.name

    def _remove_rejected_ai_label_outputs(
        self,
        image: Image,
        label: ImageBusinessLabel,
    ) -> None:
        rejected_name = self._business_label_display_name(label)
        image.level2_categories[:] = [
            item for item in image.level2_categories if item.category_name != rejected_name
        ]
        image.business_labels[:] = [
            item
            for item in image.business_labels
            if not (
                item.origin == "manual"
                and item.tag_id == label.tag_id
                and (item.reason or "").startswith("设计师接受 AI 建议")
            )
        ]
        if not any(
            item.origin == "manual" and item.tag_id == label.tag_id
            for item in image.business_labels
        ):
            image.tag_links[:] = [
                link for link in image.tag_links if link.tag_id != label.tag_id
            ]

    def _detail(self, image_id: str) -> ImageDetailRead:
        image = self._get(image_id)
        return image_to_detail(image, self.related_images.related_images(image, 8))

    def _sync_index(self, image_id: str) -> None:
        image = self.images.get(image_id)
        if image:
            self.search_index.upsert_image(image)

    def _get(self, image_id: str) -> Image:
        image = self.images.get(image_id)
        if not image:
            raise NotFoundError("image_not_found", "图片不存在")
        return image
