from __future__ import annotations

from app.core.config import get_settings
from app.core.errors import NotFoundError
from app.domain.taxonomy_catalog import load_taxonomy_catalog
from app.models.image import (
    AnalysisRun,
    ContentTag,
    Image,
    ImageBusinessLabel,
    ImageLevel2Category,
)
from app.repositories.image_repository import ImageRepository
from app.repositories.tag_repository import TagRepository
from app.schemas.ai import ImageAnalysisResult
from app.schemas.image import ImageDetailRead
from app.services.embedding_index import EmbeddingIndexSync
from app.services.search_index_sync import SearchIndexSync
from app.services.serializers import image_to_detail
from app.services.unit_of_work import UnitOfWork


class ImageAnalysisService:
    """Owns image analysis runs and AI analysis persistence."""

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

    def create_analysis_run(self, image_id: str) -> AnalysisRun:
        image = self._get(image_id)
        catalog = load_taxonomy_catalog()
        settings = get_settings()
        analysis_run = AnalysisRun(
            task="image_content_analysis",
            status="queued",
            taxonomy_version=catalog.version,
            model_provider=settings.model_provider,
            model_name=settings.model_name,
        )
        image.analysis_runs.append(analysis_run)
        self.images.save(image)
        self.uow.commit()
        return analysis_run

    def mark_running(self, image_id: str, analysis_run_id: str) -> None:
        analysis_run = self._get_analysis_run(image_id, analysis_run_id)
        analysis_run.status = "running"
        self.uow.commit()

    def mark_failed(self, image_id: str, analysis_run_id: str) -> None:
        analysis_run = self._get_analysis_run(image_id, analysis_run_id)
        analysis_run.status = "failed"
        self.uow.commit()

    def save_ai_analysis(
        self,
        image_id: str,
        result: ImageAnalysisResult,
        analysis_run_id: str | None = None,
    ) -> ImageDetailRead:
        image = self._get(image_id)
        catalog = load_taxonomy_catalog()
        label_codes = self._secondary_label_codes(result)
        rejected_ai_codes = {
            label.label_code
            for label in image.business_labels
            if label.origin == "ai" and label.review_status == "rejected"
        }
        reviewed_ai_codes = {
            label.label_code
            for label in image.business_labels
            if label.origin == "ai" and label.review_status in {"accepted", "rejected"}
        }
        manual_codes = {
            label.label_code
            for label in image.business_labels
            if label.origin == "manual"
        }
        content_tags = [
            ContentTag(
                tag_name=item.tag.strip(),
                confidence=item.confidence,
                dimension=item.dimension,
            )
            for item in result.content_tags
            if item.tag.strip()
        ]
        level2_categories = [
            ImageLevel2Category(
                category_name=(
                    f"{item.system} > {item.label}" if item.system.strip() else item.label
                ),
                confidence=item.confidence,
                reason=item.reason,
            )
            for item, label_code in zip(result.secondary_labels, label_codes)
            if item.label.strip() and label_code not in rejected_ai_codes
        ]

        business_label_inputs = []
        for item, label_code in zip(result.secondary_labels, label_codes):
            if not label_code:
                continue
            if label_code in reviewed_ai_codes or label_code in manual_codes:
                continue
            tag = self.tags.get_by_code(label_code)
            if tag:
                business_label_inputs.append((item, label_code, tag))

        settings = get_settings()
        if analysis_run_id:
            analysis_run = self._get_analysis_run(image_id, analysis_run_id)
            analysis_run.status = "succeeded"
            analysis_run.taxonomy_version = catalog.version
            analysis_run.model_provider = settings.model_provider
            analysis_run.model_name = settings.model_name
        else:
            analysis_run = AnalysisRun(
                task="image_content_analysis",
                status="succeeded",
                taxonomy_version=catalog.version,
                model_provider=settings.model_provider,
                model_name=settings.model_name,
            )

        business_labels: list[ImageBusinessLabel] = []
        for item, label_code, tag in business_label_inputs:
            business_labels.append(
                ImageBusinessLabel(
                    image=image,
                    tag=tag,
                    label_code=label_code,
                    origin="ai",
                    role=item.role,
                    review_status="pending",
                    confidence=item.confidence,
                    evidence_level=item.evidence_level,
                    reason=item.reason,
                    analysis_run=analysis_run,
                )
            )

        self.images.replace_ai_profile(
            image,
            summary=result.image_summary.strip(),
            content_tags=content_tags,
            level2_categories=level2_categories,
            analysis_run=analysis_run,
            business_labels=business_labels,
        )
        self.embedding_index.upsert_image(self.images, image)
        self.uow.commit()
        self._sync_index(image.id)
        return self._detail(image.id)

    def _secondary_label_codes(self, result: ImageAnalysisResult) -> list[str | None]:
        catalog = load_taxonomy_catalog()
        node_by_name = {
            (catalog.node_by_code[node.parent_code].name, node.name): node.code
            for node in catalog.image_label_nodes
            if node.parent_code
        }
        valid_codes = set(catalog.node_by_code)
        return [
            item.label_code
            if item.label_code in valid_codes
            else node_by_name.get((item.system.strip(), item.label.strip()))
            for item in result.secondary_labels
        ]

    def _detail(self, image_id: str) -> ImageDetailRead:
        image = self._get(image_id)
        tag_ids = [link.tag_id for link in image.tag_links]
        related = self.images.list(None, tag_ids, None, None, None, 9, "createdAt")
        return image_to_detail(image, [item for item in related if item.id != image.id][:8])

    def _sync_index(self, image_id: str) -> None:
        image = self.images.get(image_id)
        if image:
            self.search_index.upsert_image(image)

    def _get(self, image_id: str) -> Image:
        image = self.images.get(image_id)
        if not image:
            raise NotFoundError("image_not_found", "图片不存在")
        return image

    def _get_analysis_run(self, image_id: str, analysis_run_id: str) -> AnalysisRun:
        analysis_run = self.images.get_analysis_run(image_id, analysis_run_id)
        if not analysis_run:
            raise NotFoundError("analysis_run_not_found", "分析任务不存在")
        return analysis_run
