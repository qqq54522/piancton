from app.models.asset import AssetConceptLink, AssetGroup, AssetSearchPhrase
from app.models.business_concept import (
    BusinessConcept,
    ConceptSearchPhrase,
    ConceptSystemLink,
)
from app.models.image import ContentTag, Image
from app.models.tag import Tag
from app.repositories.image_repository import ImageRepository
from app.services.related_image_service import RelatedImageService
from app.services.search_service import SearchService


def create_concept_image(
    db,
    *,
    code: str = "animation_explanation",
    name: str = "动画精讲",
    title: str = "知识点动画讲解",
    summary: str = "一张用于解释同步校内知识点的功能图。",
    phrase: str = "孩子听不懂老师讲课",
    origin: str = "manual",
    review_status: str = "accepted",
    role: str = "expresses",
) -> Image:
    system = Tag(
        code=f"system_{code}",
        name=f"{name}体系",
        color="#6366F1",
        node_type="system",
        assignable=False,
        status="active",
    )
    concept = BusinessConcept(
        code=code,
        name=name,
        system_links=[ConceptSystemLink(system_tag=system)],
        search_phrases=[
            ConceptSearchPhrase(
                phrase=phrase,
                phrase_type="business_language",
                review_status="accepted",
            )
        ],
    )
    group = AssetGroup(
        title=title,
        created_by="admin",
        concept_links=[
            AssetConceptLink(
                concept=concept,
                relation_role=role,
                origin=origin,
                review_status=review_status,
                confidence=0.9,
            )
        ],
    )
    image = Image(
        title=title,
        file_name=f"{code}.png",
        storage_key=f"{code}.png",
        thumbnail_storage_key=f"{code}-thumb.jpg",
        media_type="image/png",
        size_bytes=100,
        uploader="admin",
        image_summary=summary,
        asset_group=group,
    )
    image.content_tags.append(
        ContentTag(tag_name="知识点", confidence=0.92, dimension="文字")
    )
    db.add(image)
    db.flush()
    group.primary_image_id = image.id
    db.commit()
    return image


def test_database_search_recalls_accepted_business_concept(db_factory):
    with db_factory() as db:
        image = create_concept_image(db)
        response = SearchService(db).search("动画精讲", 12)

    assert response.search_mode == "fuzzy"
    assert response.fallback is False
    assert [item.image.id for item in response.results] == [image.id]
    assert response.results[0].expressed_concepts == ["动画精讲"]


def test_search_reuses_versioned_business_phrase(db_factory):
    with db_factory() as db:
        image = create_concept_image(db)
        response = SearchService(db).search("孩子听不懂老师讲课", 12)

    assert [item.image.id for item in response.results] == [image.id]
    assert any("动画精讲" in reason for reason in response.results[0].match_reasons)


def test_search_uses_objective_content_and_summary_without_old_tags(db_factory):
    with db_factory() as db:
        group = AssetGroup(title="规划页", created_by="designer")
        image = Image(
            title="学习进度页",
            file_name="planning.png",
            storage_key="planning.png",
            thumbnail_storage_key="planning-thumb.jpg",
            media_type="image/png",
            size_bytes=100,
            uploader="designer",
            image_summary="家长正在查看孩子学习规划进度",
            asset_group=group,
            content_tags=[
                ContentTag(tag_name="进度条", confidence=0.9, dimension="物体")
            ],
        )
        db.add(image)
        db.flush()
        group.primary_image_id = image.id
        db.commit()

        summary_response = SearchService(db).search("学习规划进度", 12)
        content_response = SearchService(db).search("进度条", 12)

    assert summary_response.results[0].image.id == image.id
    assert content_response.results[0].image.id == image.id


def test_rejected_or_excluded_concepts_do_not_recall_assets(db_factory):
    with db_factory() as db:
        rejected = create_concept_image(
            db,
            code="rejected_concept",
            name="拒绝概念",
            title="无关标题一",
            summary="无关画面一",
            phrase="拒绝概念搜索语",
            origin="ai",
            review_status="rejected",
        )
        excluded = create_concept_image(
            db,
            code="excluded_concept",
            name="排除概念",
            title="无关标题二",
            summary="无关画面二",
            phrase="排除概念搜索语",
            role="excludes",
        )
        rejected_result = SearchService(db).search("拒绝概念", 12)
        excluded_result = SearchService(db).search("排除概念", 12)

    assert rejected.id not in {item.image.id for item in rejected_result.results}
    assert excluded.id not in {item.image.id for item in excluded_result.results}


def test_asset_specific_phrase_recalls_only_its_group(db_factory):
    with db_factory() as db:
        first = create_concept_image(db, code="first", name="第一概念", phrase="通用词")
        second = create_concept_image(db, code="second", name="第二概念", phrase="另一个通用词")
        first.asset_group.search_phrases.append(
            AssetSearchPhrase(
                phrase="蓝色横版平板素材",
                origin="manual",
                review_status="accepted",
            )
        )
        db.commit()
        response = SearchService(db).search("蓝色横版平板素材", 12)

    ids = [item.image.id for item in response.results]
    assert first.id in ids
    assert second.id not in ids


def test_related_images_prioritize_shared_confirmed_concepts(db_factory):
    with db_factory() as db:
        source = create_concept_image(db, code="shared", name="共同概念", title="源图")
        concept = source.asset_group.concept_links[0].concept
        sibling_group = AssetGroup(
            title="同概念图",
            created_by="admin",
            concept_links=[
                AssetConceptLink(
                    concept=concept,
                    relation_role="supports",
                    origin="manual",
                    review_status="accepted",
                )
            ],
        )
        sibling = Image(
            title="同概念图",
            file_name="sibling.png",
            storage_key="sibling.png",
            thumbnail_storage_key="sibling-thumb.jpg",
            media_type="image/png",
            size_bytes=100,
            uploader="admin",
            asset_group=sibling_group,
        )
        db.add(sibling)
        db.flush()
        sibling_group.primary_image_id = sibling.id
        db.commit()

        related = RelatedImageService(ImageRepository(db)).related_images(source, limit=4)

    assert [item.id for item in related] == [sibling.id]


def test_meilisearch_not_configured_keeps_database_fallback(db_factory):
    with db_factory() as db:
        image = create_concept_image(db)
        response = SearchService(
            db,
            search_backend="meilisearch",
            meilisearch_url="",
        ).search("动画精讲", 12)

    assert [item.image.id for item in response.results] == [image.id]
    assert response.search_mode == "fuzzy"
    assert response.fallback is False
