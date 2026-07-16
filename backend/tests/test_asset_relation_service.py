from sqlalchemy import select

from app.models.asset import AssetConceptLink, AssetGroup
from app.models.business_concept import BusinessConcept
from app.schemas.ai import ConceptSuggestion, ImageAnalysisResult
from app.schemas.asset import AssetConceptConfirmation
from app.services.asset_relation_service import AssetRelationService
from app.services.asset_serializers import asset_group_to_read


def _analysis_for(concept: BusinessConcept) -> ImageAnalysisResult:
    return ImageAnalysisResult(
        image_summary="教材章节与应用课程对应",
        concept_suggestions=[
            ConceptSuggestion(
                concept_code=concept.code,
                system_name="同步校内体系",
                concept_name=concept.name,
                confidence=0.96,
                evidence_level="A",
                relation_role="expresses",
                reason="画面直接展示教材章节与应用课程对应。",
            )
        ],
    )


def test_manual_confirmation_shadows_ai_suggestions_for_same_concept(db_factory):
    with db_factory() as db:
        concept = BusinessConcept(code="sync_school_test", name="同步校内")
        group = AssetGroup(title="课程同步", created_by="admin")
        group.concept_links.append(
            AssetConceptLink(
                concept=concept,
                relation_role="supports",
                origin="ai",
                review_status="pending",
            )
        )
        db.add_all([concept, group])
        db.commit()

        service = AssetRelationService(db)
        response = service.confirm(
            group.id,
            AssetConceptConfirmation(
                concept_id=concept.id,
                relation_role="expresses",
            ),
        )

        same_concept = [
            item for item in response.concept_links if item.concept_id == concept.id
        ]
        assert any(
            item.origin == "manual" and item.review_status == "accepted"
            for item in same_concept
        )
        assert not any(
            item.origin == "ai" and item.review_status == "pending"
            for item in same_concept
        )

        refreshed = service.assets.get(group.id)
        assert refreshed is not None
        service.replace_analysis_suggestions(
            refreshed,
            _analysis_for(concept),
            source_ref="analysis-rerun",
        )
        service.uow.commit()

        links = list(
            db.scalars(
                select(AssetConceptLink).where(
                    AssetConceptLink.asset_group_id == group.id,
                    AssetConceptLink.concept_id == concept.id,
                )
            ).all()
        )
        assert not any(
            item.origin == "ai" and item.review_status == "pending" for item in links
        )
        assert any(
            item.origin == "ai" and item.review_status == "rejected" for item in links
        )


def test_asset_serializer_hides_stale_ai_pending_covered_by_manual_fact(db_factory):
    with db_factory() as db:
        concept = BusinessConcept(code="sync_school_stale", name="同步校内")
        group = AssetGroup(title="课程同步", created_by="admin")
        group.concept_links.extend(
            [
                AssetConceptLink(
                    concept=concept,
                    relation_role="expresses",
                    origin="manual",
                    review_status="accepted",
                ),
                AssetConceptLink(
                    concept=concept,
                    relation_role="expresses",
                    origin="ai",
                    review_status="pending",
                ),
            ]
        )
        db.add_all([concept, group])
        db.commit()

        stale_group = AssetRelationService(db).assets.get(group.id)
        assert stale_group is not None
        response = asset_group_to_read(stale_group)

        assert [item.origin for item in response.concept_links] == ["manual"]
