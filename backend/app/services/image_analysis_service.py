from __future__ import annotations

from app.core.config import get_settings
from app.core.errors import NotFoundError
from app.domain.taxonomy_catalog import load_taxonomy_catalog
from app.models.image import (
    AnalysisRun,
    ContentTag,
    Image,
)
from app.repositories.image_repository import ImageRepository
from app.schemas.ai import ImageAnalysisResult
from app.schemas.image import ImageDetailRead
from app.services.asset_relation_service import AssetRelationService
from app.services.embedding_index import EmbeddingIndexSync
from app.services.image_semantic_profile_service import ImageSemanticProfileService
from app.services.related_image_service import RelatedImageService
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
        self.uow = UnitOfWork(db)
        self.search_index = search_index or SearchIndexSync.from_settings()
        self.embedding_index = embedding_index or EmbeddingIndexSync.disabled()
        self.semantic_profile = ImageSemanticProfileService()
        self.asset_relations = AssetRelationService(db)
        self.related_images = RelatedImageService(self.images)

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
        concept_codes = self._concept_suggestion_codes(result)
        for item, concept_code in zip(result.concept_suggestions, concept_codes):
            if concept_code:
                item.concept_code = concept_code
        content_tags = self._content_tags_from_analysis(result)

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

        self.images.replace_ai_profile(
            image,
            summary=result.image_summary.strip(),
            semantic_profile_json=self.semantic_profile.profile_json_from_analysis(result),
            content_tags=content_tags,
            analysis_run=analysis_run,
        )
        if image.asset_group_id:
            group = self.asset_relations.assets.get(image.asset_group_id)
            if group:
                self.asset_relations.replace_analysis_suggestions(
                    group,
                    result,
                    source_ref=analysis_run.id,
                )
        self.embedding_index.upsert_image(self.images, image)
        self.uow.commit()
        self._sync_index(image.id)
        return self._detail(image.id)

    def _concept_suggestion_codes(self, result: ImageAnalysisResult) -> list[str | None]:
        catalog = load_taxonomy_catalog()
        node_by_name = {
            (catalog.node_by_code[node.parent_code].name, node.name): node.code
            for node in catalog.image_label_nodes
            if node.parent_code
        }
        valid_codes = set(catalog.node_by_code)
        return [
            item.concept_code
            if item.concept_code in valid_codes
            else node_by_name.get((item.system_name.strip(), item.concept_name.strip()))
            for item in result.concept_suggestions
        ]

    def _content_tags_from_analysis(
        self,
        result: ImageAnalysisResult,
    ) -> list[ContentTag]:
        content_tags: list[ContentTag] = []
        seen: set[str] = set()
        for item in result.content_tags:
            name = item.tag.strip()
            if not name or name in seen:
                continue
            seen.add(name)
            content_tags.append(
                ContentTag(
                    tag_name=name,
                    confidence=item.confidence,
                    dimension=item.dimension,
                )
            )

        return content_tags

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

    def _get_analysis_run(self, image_id: str, analysis_run_id: str) -> AnalysisRun:
        analysis_run = self.images.get_analysis_run(image_id, analysis_run_id)
        if not analysis_run:
            raise NotFoundError("analysis_run_not_found", "分析任务不存在")
        return analysis_run
