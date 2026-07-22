from app.models.asset import AssetConceptLink, AssetGroup, AssetSearchPhrase
from app.models.business_concept import (
    BusinessConcept,
    ConceptSearchPhrase,
    ConceptSystemLink,
)
from app.models.image import ContentTag, Image
from app.models.tag import Tag
from app.repositories.image_repository import ImageRepository
from app.schemas.asset import AssetSearchPhraseCreate, AssetSearchPhraseReview
from app.services.asset_relation_service import AssetRelationService
from app.services.database_search_recall import database_match_score
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


def test_search_uses_summary_but_ignores_legacy_objective_content_tags(db_factory):
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
    assert content_response.results == []


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
        first = create_concept_image(
            db,
            code="first",
            name="第一概念",
            title="第一张知识点动画讲解",
            phrase="通用词",
        )
        second = create_concept_image(
            db,
            code="second",
            name="第二概念",
            title="第二张知识点动画讲解",
            phrase="另一个通用词",
        )
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


def test_pending_ai_asset_phrase_does_not_enter_direct_recall(db_factory):
    with db_factory() as db:
        image = create_concept_image(
            db,
            code="pending-asset-phrase",
            name="无关业务概念",
            title="无关标题",
            summary="无关画面摘要",
            phrase="无关公共话术",
        )
        image.asset_group.search_phrases.append(
            AssetSearchPhrase(
                phrase="待审蓝紫横版几何纹理",
                origin="ai",
                review_status="pending",
            )
        )
        db.commit()

        score = database_match_score(image, "待审蓝紫横版几何纹理")
        response = SearchService(db).search("待审蓝紫横版几何纹理", 12)

    assert score == 0.65
    assert image.id not in {item.image.id for item in response.results}


def test_accepting_ai_asset_phrase_refreshes_derived_indexes(db_factory):
    class RecordingSearchIndex:
        def __init__(self):
            self.image_ids: list[str] = []

        def upsert_image(self, image):
            self.image_ids.append(image.id)

    class RecordingEmbeddingIndex:
        def __init__(self):
            self.image_ids: list[str] = []

        def upsert_image(self, _repo, image):
            self.image_ids.append(image.id)

    with db_factory() as db:
        image = create_concept_image(db, code="reviewed-asset-phrase")
        phrase = AssetSearchPhrase(
            phrase="审核后进入高优先级",
            origin="ai",
            review_status="pending",
        )
        image.asset_group.search_phrases.append(phrase)
        db.commit()
        search_index = RecordingSearchIndex()
        embedding_index = RecordingEmbeddingIndex()
        service = AssetRelationService(
            db,
            search_index=search_index,
            embedding_index=embedding_index,
        )

        service.review_phrase(
            image.asset_group.id,
            phrase.id,
            AssetSearchPhraseReview(review_status="accepted"),
        )

    assert search_index.image_ids == [image.id]
    assert embedding_index.image_ids == [image.id]


def test_removing_accepted_asset_phrase_soft_deletes_and_can_restore(db_factory):
    class RecordingSearchIndex:
        def __init__(self):
            self.image_ids: list[str] = []

        def upsert_image(self, image):
            self.image_ids.append(image.id)

    class RecordingEmbeddingIndex:
        def __init__(self):
            self.image_ids: list[str] = []

        def upsert_image(self, _repo, image):
            self.image_ids.append(image.id)

    with db_factory() as db:
        image = create_concept_image(db, code="removable-asset-phrase")
        phrase = AssetSearchPhrase(
            phrase="手机课程章节对应课本目录",
            origin="manual",
            review_status="accepted",
        )
        image.asset_group.search_phrases.append(phrase)
        db.commit()
        search_index = RecordingSearchIndex()
        embedding_index = RecordingEmbeddingIndex()
        service = AssetRelationService(
            db,
            search_index=search_index,
            embedding_index=embedding_index,
        )

        removed = service.remove_phrase(image.asset_group.id, phrase.id)
        removed_phrase = next(item for item in removed.search_phrases if item.id == phrase.id)
        recalled_after_removal = ImageRepository(db).search(phrase.phrase, 12)

        restored = service.add_phrase(
            image.asset_group.id,
            AssetSearchPhraseCreate(phrase=phrase.phrase, weight=1),
        )
        restored_phrase = next(item for item in restored.search_phrases if item.id == phrase.id)

    assert removed_phrase.review_status == "rejected"
    assert image.id not in {item.id for item in recalled_after_removal}
    assert restored_phrase.review_status == "accepted"
    assert search_index.image_ids == [image.id, image.id]
    assert embedding_index.image_ids == [image.id, image.id]


def test_confirmed_business_language_ignores_legacy_objective_content_tags(db_factory):
    with db_factory() as db:
        image = create_concept_image(
            db,
            phrase="课程跟学校进度一致",
            title="产品功能画面",
            summary="一张用于业务介绍的产品功能图。",
        )
        image.asset_group.search_phrases.append(
            AssetSearchPhrase(
                phrase="手机章节对照课本目录",
                origin="manual",
                review_status="accepted",
            )
        )
        db.commit()

        concept_phrase_score = database_match_score(image, "课程跟学校进度一致")
        asset_phrase_score = database_match_score(image, "手机章节对照课本目录")
        content_tag_score = database_match_score(image, "知识点")

    assert concept_phrase_score == 0.95
    assert asset_phrase_score == 0.9
    assert content_tag_score == 0.65


def test_related_images_prioritize_shared_concepts_and_exclude_same_group_versions(
    db_factory,
):
    with db_factory() as db:
        source = create_concept_image(db, code="shared", name="共同概念", title="源图")
        concept = source.asset_group.concept_links[0].concept
        same_group_variant = Image(
            title="源图延展版本",
            file_name="source-variant.png",
            storage_key="source-variant.png",
            thumbnail_storage_key="source-variant-thumb.jpg",
            media_type="image/png",
            size_bytes=100,
            uploader="admin",
            asset_group=source.asset_group,
            asset_role="derivative",
            version_no=2,
            is_current=True,
        )
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
        db.add_all([same_group_variant, sibling])
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
