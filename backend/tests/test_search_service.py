from __future__ import annotations

from app.models.asset import AssetConceptLink, AssetGroup, AssetSearchPhrase
from app.models.business_concept import (
    BusinessConcept,
    ConceptSearchPhrase,
    ConceptSystemLink,
)
from app.models.image import ContentTag, Image
from app.models.tag import Tag
from app.repositories.business_concept_repository import BusinessConceptRepository
from app.repositories.image_repository import ImageRepository
from app.schemas.ai import SearchConceptMatch, SearchUnderstanding
from app.services.asset_route_ordering import order_routed_assets
from app.services.concept_search_recall import ConceptSearchRecallService
from app.services.database_search_recall import database_match_score
from app.services.related_image_service import RelatedImageService
from app.services.search_models import ConceptMatch, SearchHit
from app.services.search_service import SearchService
from app.services.volc_ai_search_client import VolcAiSearchClient


def create_concept_image(
    db,
    *,
    code: str = "animation_explanation",
    name: str = "动画精讲",
    title: str = "知识点动画讲解",
    summary: str = "一张用于解释同步校内知识点的功能图。",
    phrase: str = "孩子听不懂老师讲课",
    recommendation_text: str | None = None,
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
        recommendation_text=recommendation_text,
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


def create_concept(db, *, code: str, name: str) -> BusinessConcept:
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
                phrase=name,
                phrase_type="business_language",
                review_status="accepted",
            )
        ],
    )
    db.add(concept)
    db.flush()
    return concept


def create_image_for_concept(
    db,
    concept: BusinessConcept,
    *,
    title: str,
    channel: str = "手机端大图",
) -> Image:
    group = AssetGroup(
        title=title,
        created_by="admin",
        concept_links=[
            AssetConceptLink(
                concept=concept,
                relation_role="expresses",
                origin="manual",
                review_status="accepted",
                confidence=0.9,
            )
        ],
    )
    image = Image(
        title=title,
        file_name=f"{title}.png",
        storage_key=f"{title}.png",
        thumbnail_storage_key=f"{title}-thumb.jpg",
        media_type="image/png",
        size_bytes=100,
        uploader="admin",
        channel=channel,
        image_summary=f"{title}业务素材",
        asset_group=group,
    )
    db.add(image)
    db.flush()
    group.primary_image_id = image.id
    return image


class FixedVikingRouter:
    configured = True

    def __init__(self, concept_names: list[str]):
        self.concept_names = concept_names

    def route(self, keyword: str) -> SearchUnderstanding:
        return SearchUnderstanding(
            original_query=keyword,
            normalized_query="、".join(self.concept_names),
            search_intent="火山已命中卖点，回本地图库取全量素材",
            query_type="multi_business_intent_search"
            if len(self.concept_names) > 1
            else "business_intent_search",
            search_strategy="VikingDB 先确定卖点，再回本地数据库取已审核素材",
            matched_business_concepts=[
                SearchConceptMatch(
                    concept=f"测试体系 > {name}",
                    relation="direct",
                    reason="固定测试命中",
                    weight=0.96 - index * 0.01,
                )
                for index, name in enumerate(self.concept_names)
            ],
        )


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


def test_concept_recall_allocates_quota_for_each_matched_selling_point(db_factory):
    with db_factory() as db:
        photo = create_concept(db, code="photo_guided_learning", name="AI拍题精学")
        transfer = create_concept(db, code="transfer_practice", name="举一反三")
        for index in range(8):
            create_image_for_concept(db, photo, title=f"拍题精学-{index}")
        transfer_image = create_image_for_concept(db, transfer, title="举一反三-代表图")
        db.commit()

        recall = ConceptSearchRecallService(
            BusinessConceptRepository(db),
            ImageRepository(db),
        )
        hits = recall.recall(
            [
                ConceptMatch(
                    concept_id=photo.id,
                    code=photo.code,
                    name=photo.name,
                    score=0.96,
                ),
                ConceptMatch(
                    concept_id=transfer.id,
                    code=transfer.code,
                    name=transfer.name,
                    score=0.95,
                ),
            ],
            limit=3,
        )

    assert transfer_image.id in {hit.image.id for hit in hits}


def test_vikingdb_inventory_route_returns_all_matched_selling_point_assets(db_factory):
    with db_factory() as db:
        photo = create_concept(db, code="photo_guided_learning", name="AI拍题精学")
        transfer = create_concept(db, code="transfer_practice", name="举一反三")
        universal = create_concept(db, code="universal_method", name="万能解法")
        images = [
            create_image_for_concept(db, photo, title="苏格拉底讲解提问"),
            create_image_for_concept(db, photo, title="拍题入口图"),
            create_image_for_concept(db, transfer, title="变式训练图"),
            create_image_for_concept(db, universal, title="多种解法图"),
        ]
        db.commit()

        response = SearchService(
            db,
            vikingdb_knowledge_router=FixedVikingRouter(
                ["AI拍题精学", "举一反三", "万能解法"]
            ),
            vikingdb_skill_backup_enabled=False,
            candidate_limit=20,
            ai_service=None,
        ).search("拍题学完一题会一类", 20)

    assert {item.image.id for item in response.results} == {image.id for image in images}
    assert [item.image.title for item in response.results[:3]] == [
        "拍题入口图",
        "变式训练图",
        "多种解法图",
    ]


def test_multi_selling_point_route_interleaves_each_matched_concept(db_factory):
    with db_factory() as db:
        photo = create_concept(db, code="photo_guided_learning", name="AI拍题精学")
        transfer = create_concept(db, code="transfer_practice", name="举一反三")
        photo_images = [
            create_image_for_concept(db, photo, title=f"拍题精学-{index}")
            for index in range(3)
        ]
        transfer_images = [
            create_image_for_concept(db, transfer, title=f"举一反三-{index}")
            for index in range(2)
        ]
        db.commit()

        understanding = SearchUnderstanding(
            original_query="洋葱的拍题精学让孩子学一题会一类",
            normalized_query="拍题精学 举一反三",
            search_intent="同时查找 AI拍题精学 和 举一反三 素材",
            query_type="multi_business_intent_search",
            matched_business_concepts=[
                SearchConceptMatch(
                    concept="同步自学体系 > AI拍题精学",
                    relation="direct",
                    reason="表达拍题精学",
                    weight=0.96,
                ),
                SearchConceptMatch(
                    concept="同步培优体系 > 举一反三",
                    relation="direct",
                    reason="表达一题会一类",
                    weight=0.95,
                ),
            ],
        )
        ordered = order_routed_assets(
            [
                SearchHit(photo_images[0], score=0.99),
                SearchHit(photo_images[1], score=0.98),
                SearchHit(photo_images[2], score=0.97),
                SearchHit(transfer_images[0], score=0.86),
                SearchHit(transfer_images[1], score=0.85),
            ],
            (
                ConceptMatch(photo.id, photo.code, photo.name, 0.96),
                ConceptMatch(transfer.id, transfer.code, transfer.name, 0.95),
            ),
            understanding,
            {},
        )

    assert [hit.image.title for hit in ordered[:4]] == [
        "拍题精学-0",
        "举一反三-0",
        "拍题精学-1",
        "举一反三-1",
    ]


def test_search_result_concept_match_includes_manual_recommendation_text(db_factory):
    with db_factory() as db:
        image = create_concept_image(
            db,
            code="instant_quiz",
            name="课后小测",
            phrase="课后测完当天看结果",
            recommendation_text="有没有能体现课后小测后当天会不会一眼看出来的图",
        )
        response = SearchService(db).search("课后测完当天看结果", 12)

    assert [item.image.id for item in response.results] == [image.id]
    match = response.results[0].matched_query_concepts[0]
    assert match.concept_name == "课后小测"
    assert match.recommendation_text == "有没有能体现课后小测后当天会不会一眼看出来的图"


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
        sections = RelatedImageService(ImageRepository(db)).recommendation_sections(
            source,
            limit=4,
        )

    assert [item.id for item in related] == [sibling.id]
    assert sections[0].purpose == "same_selling_point"
    assert [item.id for item in sections[0].images] == [sibling.id]


def test_detail_personalization_rehydrates_only_local_published_images(
    db_factory,
    monkeypatch,
):
    with db_factory() as db:
        source = create_concept_image(
            db,
            code="personal-source",
            name="个性化源卖点",
            title="个性化源图",
        )
        candidate_group = AssetGroup(
            title="个性化候选",
            created_by="admin",
            publish_status="published",
        )
        candidate = Image(
            title="个性化候选",
            file_name="personalized.png",
            storage_key="personalized.png",
            thumbnail_storage_key="personalized-thumb.jpg",
            media_type="image/png",
            size_bytes=100,
            uploader="admin",
            asset_group=candidate_group,
        )
        db.add(candidate)
        db.flush()
        candidate_group.primary_image_id = candidate.id
        db.commit()

        client = VolcAiSearchClient(
            base_url="https://aisearch.example.com",
            api_key="secret",
            dataset_id="items-1",
            recommend_path="/api/v1/application/app-1/scene-detail",
        )
        monkeypatch.setattr(
            client,
            "recommend_items",
            lambda **_kwargs: ["remote-orphan", candidate.id],
        )
        sections = RelatedImageService(
            ImageRepository(db),
            ai_search_client=client,
            ai_search_recommend_enabled=True,
        ).recommendation_sections(
            source,
            user_id="business-user",
            personalize=True,
            limit=4,
        )

    personalized = next(
        section for section in sections if section.purpose == "personalized"
    )
    assert personalized.source == "ai_search"
    assert [item.id for item in personalized.images] == [candidate.id]


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
