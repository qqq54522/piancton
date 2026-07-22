from __future__ import annotations

from typing import Literal, cast

from app.core.errors import AppError, NotFoundError
from app.domain.evidence_points import load_evidence_point_catalog
from app.domain.proof_points import load_proof_point_catalog
from app.models.asset import AssetConceptLink, AssetGroup, AssetSearchPhrase
from app.repositories.asset_repository import AssetRepository
from app.repositories.business_concept_repository import BusinessConceptRepository
from app.repositories.image_repository import ImageRepository
from app.schemas.ai import ImageAnalysisResult
from app.schemas.asset import (
    AssetBusinessClassificationUpdate,
    AssetConceptBatchReview,
    AssetConceptConfirmation,
    AssetConceptReview,
    AssetGroupRead,
    AssetSearchPhraseCreate,
    AssetSearchPhraseReview,
)
from app.services.asset_serializers import asset_group_to_read
from app.services.embedding_index import EmbeddingIndexSync
from app.services.search_index_sync import SearchIndexSync
from app.services.unit_of_work import UnitOfWork


class AssetRelationService:
    """Separates AI suggestions from owner-confirmed business truth."""

    def __init__(
        self,
        db,
        *,
        search_index: SearchIndexSync | None = None,
        embedding_index: EmbeddingIndexSync | None = None,
    ):
        self.assets = AssetRepository(db)
        self.concepts = BusinessConceptRepository(db)
        self.images = ImageRepository(db)
        self.search_index = search_index or SearchIndexSync.from_settings()
        self.embedding_index = embedding_index or EmbeddingIndexSync.disabled()
        self.uow = UnitOfWork(db)

    def replace_analysis_suggestions(
        self,
        group: AssetGroup,
        result: ImageAnalysisResult,
        *,
        source_ref: str | None,
    ) -> None:
        confirmed_concept_ids = self._manual_accepted_concept_ids(group)
        self._reject_shadowed_ai_suggestions(group, confirmed_concept_ids)
        codes = [
            item.concept_code
            for item in result.concept_suggestions
            if item.concept_code
        ]
        concepts = self.concepts.get_many_by_codes(codes)
        by_code = {item.code: item for item in concepts}
        links = []
        for suggestion in result.concept_suggestions:
            concept = by_code.get(suggestion.concept_code or "")
            if not concept or concept.id in confirmed_concept_ids:
                continue
            links.append(
                AssetConceptLink(
                    concept_id=concept.id,
                    relation_role=suggestion.relation_role,
                    origin="ai",
                    review_status="pending",
                    confidence=suggestion.confidence,
                    evidence_reason=suggestion.reason,
                    source_ref=source_ref,
                )
            )
        self.assets.replace_pending_ai_links(group, links)

        phrases = [
            AssetSearchPhrase(
                phrase=phrase,
                origin="ai",
                review_status="pending",
                weight=0.72,
            )
            for phrase in _unique_phrases(
                result.semantic_profile.asset_search_phrases
            )
        ]
        self.assets.replace_pending_ai_phrases(group, phrases)

    def manual_phrases(self, values: list[str]) -> list[AssetSearchPhrase]:
        return [
            AssetSearchPhrase(
                phrase=phrase,
                origin="manual",
                review_status="accepted",
                weight=1.0,
            )
            for phrase in _unique_phrases(values)
        ]

    def confirm(self, group_id: str, payload: AssetConceptConfirmation) -> AssetGroupRead:
        group = self._group(group_id)
        concept = self.concepts.get(payload.concept_id)
        if not concept:
            raise NotFoundError("business_concept_not_found", "业务概念不存在")
        self._upsert_manual_link(
            group,
            concept,
            payload.relation_role,
            payload.evidence_reason,
        )
        self._reject_shadowed_ai_suggestions(group, {concept.id})
        self.assets.save(group)
        self.uow.commit()
        self._sync_primary(group_id)
        return asset_group_to_read(self._group(group_id))

    def update_business_classification(
        self,
        group_id: str,
        payload: AssetBusinessClassificationUpdate,
    ) -> AssetGroupRead:
        group = self._group(group_id)
        evidence = None
        if payload.evidence_point_code:
            evidence = load_evidence_point_catalog().by_code.get(
                payload.evidence_point_code
            )
            if evidence is None:
                raise AppError("invalid_evidence_point", "证据表达点不存在或已失效")
        proof_code = payload.proof_point_code or (
            evidence.proof_point_code if evidence else None
        )
        proof = (
            load_proof_point_catalog().by_code.get(proof_code)
            if proof_code
            else None
        )
        if proof_code and proof is None:
            raise AppError("invalid_proof_point", "证明点不存在或已失效")
        if evidence and proof and evidence.proof_point_code != proof.code:
            raise AppError(
                "evidence_point_parent_mismatch",
                "证据表达点不属于所选证明点",
            )

        concept = None
        if payload.concept_id:
            concept = self.concepts.get(payload.concept_id)
            if not concept:
                raise NotFoundError("business_concept_not_found", "业务概念不存在")
        elif proof:
            concepts = self.concepts.get_many_by_codes([proof.concept_code])
            concept = concepts[0] if concepts else None
        if proof and concept and proof.concept_code != concept.code:
            raise AppError("proof_point_parent_mismatch", "证明点不属于所选卖点")
        if proof and concept is None:
            raise AppError(
                "proof_point_concept_unavailable",
                "证明点对应的卖点当前不可用",
            )
        if concept:
            self._upsert_manual_link(
                group,
                concept,
                "expresses",
                "设计师人工选择业务层级",
            )
            self._reject_shadowed_ai_suggestions(group, {concept.id})

        group.primary_proof_point_code = proof.code if proof else None
        group.primary_evidence_point_code = evidence.code if evidence else None
        self.assets.save(group)
        self.uow.commit()
        self._sync_primary(group_id)
        return asset_group_to_read(self._group(group_id))

    def review_suggestions(
        self,
        group_id: str,
        payload: AssetConceptBatchReview,
    ) -> AssetGroupRead:
        group = self._group(group_id)
        links_by_id = {item.id: item for item in group.concept_links}
        missing = [link_id for link_id in payload.link_ids if link_id not in links_by_id]
        if missing:
            raise NotFoundError(
                "asset_concept_link_not_found",
                "部分素材业务关系不存在",
            )
        confirmed_concept_ids = self._manual_accepted_concept_ids(group)
        for link_id in dict.fromkeys(payload.link_ids):
            link = links_by_id[link_id]
            if link.origin != "ai":
                raise AppError(
                    "manual_relation_not_reviewable",
                    "人工确认关系不需要审核",
                )
            if (
                payload.review_status == "accepted"
                and link.concept_id in confirmed_concept_ids
            ):
                link.review_status = "rejected"
                continue
            link.review_status = payload.review_status
            if payload.review_status == "accepted":
                self._upsert_manual_link(
                    group,
                    link.concept,
                    cast(
                        Literal["expresses", "supports", "visual_related", "excludes"],
                        link.relation_role,
                    ),
                    ("负责人接受 AI 建议：" + (link.evidence_reason or "")).rstrip("："),
                )
                confirmed_concept_ids.add(link.concept_id)
        self._reject_shadowed_ai_suggestions(group, confirmed_concept_ids)
        self.assets.save(group)
        self.uow.commit()
        self._sync_primary(group_id)
        return asset_group_to_read(self._group(group_id))

    def review_suggestion(
        self, group_id: str, link_id: str, payload: AssetConceptReview
    ) -> AssetGroupRead:
        group = self._group(group_id)
        link = self.assets.get_concept_link(group_id, link_id)
        if not link:
            raise NotFoundError("asset_concept_link_not_found", "素材业务关系不存在")
        if link.origin != "ai":
            raise AppError("manual_relation_not_reviewable", "人工确认关系不需要审核")
        confirmed_concept_ids = self._manual_accepted_concept_ids(group)
        if (
            payload.review_status == "accepted"
            and link.concept_id in confirmed_concept_ids
        ):
            link.review_status = "rejected"
            self.assets.save(link)
            self.uow.commit()
            self._sync_primary(group_id)
            return asset_group_to_read(self._group(group_id))
        link.review_status = payload.review_status
        if payload.relation_role:
            link.relation_role = payload.relation_role
        if payload.review_status == "accepted":
            self._upsert_manual_link(
                group,
                link.concept,
                cast(
                    Literal["expresses", "supports", "visual_related", "excludes"],
                    link.relation_role,
                ),
                ("负责人接受 AI 建议：" + (link.evidence_reason or "")).rstrip("："),
            )
            self._reject_shadowed_ai_suggestions(group, {link.concept_id})
            self.assets.save(group)
        self.assets.save(link)
        self.uow.commit()
        self._sync_primary(group_id)
        return asset_group_to_read(self._group(group_id))

    def add_phrase(self, group_id: str, payload: AssetSearchPhraseCreate) -> AssetGroupRead:
        group = self._group(group_id)
        phrase = payload.phrase.strip()
        existing = next(
            (
                item
                for item in group.search_phrases
                if item.phrase == phrase and item.origin == "manual"
            ),
            None,
        )
        if existing:
            existing.weight = payload.weight
            existing.review_status = "accepted"
        else:
            group.search_phrases.append(
                AssetSearchPhrase(
                    phrase=phrase,
                    origin="manual",
                    review_status="accepted",
                    weight=payload.weight,
                )
            )
        self.assets.save(group)
        self.uow.commit()
        self._sync_primary(group_id)
        return asset_group_to_read(self._group(group_id))

    def review_phrase(
        self, group_id: str, phrase_id: str, payload: AssetSearchPhraseReview
    ) -> AssetGroupRead:
        phrase = self.assets.get_search_phrase(group_id, phrase_id)
        if not phrase:
            raise NotFoundError("asset_search_phrase_not_found", "素材搜索表达不存在")
        if phrase.origin == "manual":
            raise AppError("manual_phrase_not_reviewable", "人工搜索表达不需要审核")
        phrase.review_status = payload.review_status
        self.assets.save(phrase)
        self.uow.commit()
        self._sync_primary(group_id)
        return asset_group_to_read(self._group(group_id))

    def remove_phrase(self, group_id: str, phrase_id: str) -> AssetGroupRead:
        phrase = self.assets.get_search_phrase(group_id, phrase_id)
        if not phrase:
            raise NotFoundError("asset_search_phrase_not_found", "素材搜索表达不存在")
        phrase.review_status = "rejected"
        self.assets.save(phrase)
        self.uow.commit()
        self._sync_primary(group_id)
        return asset_group_to_read(self._group(group_id))

    def _sync_primary(self, group_id: str) -> None:
        group = self._group(group_id)
        if not group.primary_image_id:
            return
        image = self.images.get(group.primary_image_id)
        if not image:
            return
        self.search_index.upsert_image(image)
        self.embedding_index.upsert_image(self.images, image)

    def _group(self, group_id: str) -> AssetGroup:
        group = self.assets.get(group_id)
        if not group:
            raise NotFoundError("asset_group_not_found", "素材组不存在")
        return group

    def _upsert_manual_link(
        self,
        group: AssetGroup,
        concept,
        relation_role: Literal["expresses", "supports", "visual_related", "excludes"],
        evidence_reason: str | None,
    ) -> None:
        existing = next(
            (
                item
                for item in group.concept_links
                if item.concept_id == concept.id and item.origin == "manual"
            ),
            None,
        )
        if existing:
            existing.relation_role = relation_role
            existing.review_status = "accepted"
            existing.evidence_reason = evidence_reason
            return
        group.concept_links.append(
            AssetConceptLink(
                concept=concept,
                relation_role=relation_role,
                origin="manual",
                review_status="accepted",
                confidence=1.0,
                evidence_reason=evidence_reason,
            )
        )

    @staticmethod
    def _manual_accepted_concept_ids(group: AssetGroup) -> set[str]:
        return {
            item.concept_id
            for item in group.concept_links
            if item.origin == "manual" and item.review_status == "accepted"
        }

    @staticmethod
    def _reject_shadowed_ai_suggestions(
        group: AssetGroup,
        concept_ids: set[str],
    ) -> None:
        for item in group.concept_links:
            if (
                item.origin == "ai"
                and item.review_status == "pending"
                and item.concept_id in concept_ids
            ):
                item.review_status = "rejected"


def _unique_phrases(values: list[str]) -> list[str]:
    seen: set[str] = set()
    output: list[str] = []
    for value in values:
        phrase = value.strip()[:300]
        if phrase and phrase not in seen:
            seen.add(phrase)
            output.append(phrase)
    return output[:20]
