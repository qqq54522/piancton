from __future__ import annotations

from datetime import datetime
from typing import Optional, cast

from sqlalchemy import and_, desc, literal, or_, select
from sqlalchemy.orm import Session, selectinload

from app.domain.search_query_expansion import expand_search_terms
from app.models.asset import AssetConceptLink, AssetGroup, AssetSearchPhrase
from app.models.business_concept import BusinessConcept, ConceptSystemLink
from app.models.image import (
    AnalysisRun,
    ContentTag,
    Image,
    ImageEmbedding,
)

IMAGE_LOAD_OPTIONS = (
    selectinload(Image.content_tags),
    selectinload(Image.embedding),
    selectinload(Image.analysis_runs),
    selectinload(Image.asset_group).selectinload(AssetGroup.images),
    selectinload(Image.asset_group).selectinload(AssetGroup.search_phrases),
    selectinload(Image.asset_group)
    .selectinload(AssetGroup.concept_links)
    .selectinload(AssetConceptLink.concept)
    .selectinload(BusinessConcept.search_phrases),
    selectinload(Image.asset_group)
    .selectinload(AssetGroup.concept_links)
    .selectinload(AssetConceptLink.concept)
    .selectinload(BusinessConcept.system_links)
    .selectinload(ConceptSystemLink.system_tag),
)


class ImageRepository:
    def __init__(self, db: Session):
        self.db = db

    def get(self, image_id: str) -> Optional[Image]:
        stmt = (
            select(Image)
            .where(Image.id == image_id, Image.deleted_at.is_(None))
            .options(*IMAGE_LOAD_OPTIONS)
        )
        return self.db.scalar(stmt)

    def get_any(self, image_id: str) -> Optional[Image]:
        return self.db.scalar(
            select(Image).where(Image.id == image_id).options(*IMAGE_LOAD_OPTIONS)
        )

    def list(
        self,
        keyword: Optional[str],
        cursor_value: str | int | datetime | None,
        cursor_id: str | None,
        limit: int,
        sort_by: str,
    ) -> list[Image]:
        stmt = select(Image).where(Image.deleted_at.is_(None)).options(*IMAGE_LOAD_OPTIONS)
        if keyword:
            keyword_terms = expand_search_terms(keyword)[:30]
            patterns = [f"%{term}%" for term in keyword_terms if term.strip()]
            keyword_conditions = []
            for pattern in patterns:
                keyword_conditions.extend(
                    [
                        Image.title.ilike(pattern),
                        literal(keyword).ilike(literal("%") + Image.title + literal("%")),
                        Image.image_summary.ilike(pattern),
                        literal(keyword).ilike(
                            literal("%") + Image.image_summary + literal("%")
                        ),
                        ContentTag.tag_name.ilike(pattern),
                        AssetSearchPhrase.phrase.ilike(pattern),
                    ]
                )
            stmt = (
                stmt.outerjoin(ContentTag, ContentTag.image_id == Image.id)
                .outerjoin(
                    AssetSearchPhrase,
                    and_(
                        AssetSearchPhrase.asset_group_id == Image.asset_group_id,
                        AssetSearchPhrase.review_status == "accepted",
                    ),
                )
                .where(or_(*keyword_conditions))
            )

        if cursor_value is not None and cursor_id:
            if sort_by == "downloadCount":
                value = int(cast("str | int", cursor_value))
                stmt = stmt.where(
                    or_(
                        Image.download_count < value,
                        and_(Image.download_count == value, Image.id < cursor_id),
                    )
                )
            else:
                value = cast(datetime, cursor_value)
                stmt = stmt.where(
                    or_(
                        Image.created_at < value,
                        and_(Image.created_at == value, Image.id < cursor_id),
                    )
                )

        if sort_by == "downloadCount":
            order = (desc(Image.download_count), desc(Image.id))
        else:
            order = (desc(Image.created_at), desc(Image.id))
        return list(self.db.scalars(stmt.distinct().order_by(*order).limit(limit + 1)).all())

    def search(self, keyword: str, limit: int) -> list[Image]:
        pattern = f"%{keyword}%"
        stmt = (
            select(Image)
            .outerjoin(AssetGroup, AssetGroup.id == Image.asset_group_id)
            .outerjoin(ContentTag)
            .outerjoin(
                AssetSearchPhrase,
                and_(
                    AssetSearchPhrase.asset_group_id == Image.asset_group_id,
                    AssetSearchPhrase.review_status == "accepted",
                ),
            )
            .where(
                Image.deleted_at.is_(None),
                or_(
                    Image.asset_group_id.is_(None),
                    and_(
                        AssetGroup.publish_status == "published",
                        Image.is_current.is_(True),
                    ),
                ),
                or_(
                    Image.title.ilike(pattern),
                    literal(keyword).ilike(literal("%") + Image.title + literal("%")),
                    Image.image_summary.ilike(pattern),
                    literal(keyword).ilike(literal("%") + Image.image_summary + literal("%")),
                    ContentTag.tag_name.ilike(pattern),
                    AssetSearchPhrase.phrase.ilike(pattern),
                )
            )
            .options(*IMAGE_LOAD_OPTIONS)
            .distinct()
            .limit(limit)
        )
        return list(self.db.scalars(stmt).all())

    def get_many_by_ids(self, image_ids: list[str]) -> list[Image]:
        if not image_ids:
            return []
        stmt = (
            select(Image)
            .outerjoin(AssetGroup, AssetGroup.id == Image.asset_group_id)
            .where(
                Image.id.in_(image_ids),
                Image.deleted_at.is_(None),
                or_(
                    Image.asset_group_id.is_(None),
                    and_(
                        AssetGroup.publish_status == "published",
                        Image.is_current.is_(True),
                    ),
                ),
            )
            .options(*IMAGE_LOAD_OPTIONS)
        )
        images_by_id = {image.id: image for image in self.db.scalars(stmt).all()}
        return [images_by_id[image_id] for image_id in image_ids if image_id in images_by_id]

    def search_by_concept_ids(
        self,
        concept_ids: list[str],
        *,
        limit: int,
    ) -> list[Image]:
        if not concept_ids:
            return []
        stmt = (
            select(Image)
            .join(AssetGroup, AssetGroup.id == Image.asset_group_id)
            .join(
                AssetConceptLink,
                AssetConceptLink.asset_group_id == AssetGroup.id,
            )
            .where(
                Image.deleted_at.is_(None),
                Image.is_current.is_(True),
                AssetGroup.publish_status == "published",
                AssetConceptLink.concept_id.in_(concept_ids),
                AssetConceptLink.review_status != "rejected",
                AssetConceptLink.relation_role != "excludes",
            )
            .options(*IMAGE_LOAD_OPTIONS)
            .distinct()
            .limit(limit)
        )
        return list(self.db.scalars(stmt).all())

    def list_embeddings(self, *, model_name: str | None = None) -> list[ImageEmbedding]:
        stmt = (
            select(ImageEmbedding)
            .join(Image, Image.id == ImageEmbedding.image_id)
            .outerjoin(AssetGroup, AssetGroup.id == Image.asset_group_id)
            .where(
                Image.deleted_at.is_(None),
                or_(
                    Image.asset_group_id.is_(None),
                    and_(
                        AssetGroup.publish_status == "published",
                        Image.is_current.is_(True),
                    ),
                ),
            )
        )
        if model_name:
            stmt = stmt.where(ImageEmbedding.model_name == model_name)
        return list(self.db.scalars(stmt).all())

    def upsert_embedding(
        self,
        image: Image,
        *,
        model_name: str,
        dimension: int,
        content_hash: str,
        document_text: str,
        vector_json: str,
        updated_at: datetime,
    ) -> ImageEmbedding:
        embedding = image.embedding
        if embedding is None:
            embedding = ImageEmbedding(image=image)
        embedding.model_name = model_name
        embedding.dimension = dimension
        embedding.content_hash = content_hash
        embedding.document_text = document_text
        embedding.vector_json = vector_json
        embedding.updated_at = updated_at
        self.db.add(embedding)
        self.db.flush()
        return embedding

    def get_analysis_run(self, image_id: str, run_id: str) -> Optional[AnalysisRun]:
        return self.db.scalar(
            select(AnalysisRun).where(
                AnalysisRun.id == run_id,
                AnalysisRun.image_id == image_id,
            )
        )

    def list_for_search_index(self, *, offset: int, limit: int) -> list[Image]:
        stmt = (
            select(Image)
            .where(Image.deleted_at.is_(None))
            .options(*IMAGE_LOAD_OPTIONS)
            .order_by(Image.created_at.asc(), Image.id.asc())
            .offset(offset)
            .limit(limit)
        )
        return list(self.db.scalars(stmt).all())

    def list_deleted(self, limit: int = 100) -> list[Image]:
        stmt = (
            select(Image)
            .where(Image.deleted_at.is_not(None))
            .options(*IMAGE_LOAD_OPTIONS)
            .order_by(desc(Image.deleted_at))
            .limit(limit)
        )
        return list(self.db.scalars(stmt).all())

    def add(self, image: Image) -> Image:
        self.db.add(image)
        self.db.flush()
        return image

    def save(self, image: Image) -> Image:
        self.db.add(image)
        self.db.flush()
        return image

    def soft_delete_many(self, image_ids: list[str], deleted_at: datetime) -> int:
        if not image_ids:
            return 0
        rows = list(
            self.db.scalars(
                select(Image).where(
                    Image.id.in_(image_ids),
                    Image.deleted_at.is_(None),
                )
            ).all()
        )
        for image in rows:
            image.deleted_at = deleted_at
            self.db.add(image)
        self.db.flush()
        return len(rows)

    def replace_ai_profile(
        self,
        image: Image,
        *,
        summary: str,
        semantic_profile_json: str | None,
        content_tags: list[ContentTag],
        analysis_run: AnalysisRun | None = None,
    ) -> Image:
        image.image_summary = summary
        image.semantic_profile_json = semantic_profile_json
        image.content_tags.clear()
        image.content_tags.extend(content_tags)
        if analysis_run is not None and all(
            existing.id != analysis_run.id for existing in image.analysis_runs
        ):
            image.analysis_runs.append(analysis_run)
        self.db.flush()
        return image

    def delete(self, image: Image) -> None:
        self.db.delete(image)
        self.db.flush()
