from app.domain.search_query_expansion import expand_search_terms
from app.models.image import (
    ContentTag,
    Image,
    ImageBusinessLabel,
    ImageLevel2Category,
    ImageTag,
)
from app.models.tag import Tag
from app.repositories.image_repository import ImageRepository
from app.schemas.ai import ExpandedSearchTag, SearchCategoryMatch, SearchUnderstanding
from app.services.search_service import SearchHit, SearchService, SearchUnavailable


def create_searchable_image(db) -> Image:
    manual_tag = Tag(name="动画", color="#3B82F6")
    system = Tag(
        code="sync_school",
        name="同步校内体系",
        color="#6366F1",
        node_type="system",
        assignable=False,
        status="active",
    )
    business_tag = Tag(
        code="animation_explanation",
        name="动画精讲",
        color="#818CF8",
        parent=system,
        is_secondary=True,
        node_type="image_label",
        assignable=True,
        status="active",
    )
    image = Image(
        title="知识点动画讲解",
        file_name="lesson.png",
        storage_key="lesson.png",
        thumbnail_storage_key="lesson-thumb.jpg",
        media_type="image/png",
        size_bytes=100,
        uploader="admin",
        image_summary="一张用于解释同步校内知识点的功能图。",
    )
    image.tag_links.append(ImageTag(tag=manual_tag))
    image.content_tags.append(
        ContentTag(tag_name="知识点", confidence=0.92, dimension="文本")
    )
    image.level2_categories.append(
        ImageLevel2Category(
            category_name="同步校内体系 > 动画精讲",
            confidence=0.91,
            reason="内容指向动画讲解。",
        )
    )
    image.business_labels.append(
        ImageBusinessLabel(
            tag=business_tag,
            label_code="animation_explanation",
            origin="ai",
            role="primary",
            review_status="pending",
            confidence=0.91,
        )
    )
    db.add(image)
    db.commit()
    return image


def test_database_search_matches_business_labels(db_factory):
    with db_factory() as db:
        create_searchable_image(db)
        response = SearchService(db).search("动画精讲", 12)

    assert response.search_mode == "fuzzy"
    assert response.fallback is False
    assert len(response.results) == 1
    assert response.results[0].matched_level2_categories == [
        "同步校内体系 > 动画精讲"
    ]


def test_database_search_expands_natural_language_pain_points(db_factory):
    with db_factory() as db:
        create_searchable_image(db)
        response = SearchService(db).search("孩子听不懂老师讲课", 12)

    assert response.search_mode == "fuzzy"
    assert len(response.results) == 1
    assert response.results[0].match_level == "A"
    assert "语义扩展匹配：动画精讲" in response.results[0].match_reasons


def test_database_search_expands_school_sync_business_language(db_factory):
    with db_factory() as db:
        create_searchable_image(db)
        response = SearchService(db).search("教材对不上", 12)

    assert response.search_mode == "fuzzy"
    assert len(response.results) == 1
    assert "语义扩展匹配：同步校内" in response.results[0].match_reasons


def test_precise_search_matches_when_long_query_contains_title(db_factory):
    with db_factory() as db:
        create_searchable_image(db)
        response = SearchService(db).search(
            "我想找那张知识点动画讲解的同步课堂素材",
            12,
            "precise",
        )

    assert response.search_mode == "fuzzy"
    assert len(response.results) == 1
    assert "标题匹配" in response.results[0].match_reasons


def test_image_list_keyword_uses_expanded_business_terms(db_factory):
    with db_factory() as db:
        image = create_searchable_image(db)
        tag_id = image.tag_links[0].tag_id
        rows = ImageRepository(db).list(
            "孩子听不懂老师讲课",
            [tag_id],
            None,
            None,
            None,
            12,
            "createdAt",
        )

    assert [row.title for row in rows] == ["知识点动画讲解"]


def test_query_expansion_covers_cross_system_business_language():
    cases = [
        ("换个题就不会", "举一反三"),
        ("家长不知道怎么安排", "AI定制学习方案"),
        ("错题反复错", "AI错题本"),
        ("家长不会教", "AI私教答疑"),
        ("孩子不自律没人管", "真人老师督学"),
        ("不知道孩子学没学", "学情报告反馈"),
    ]

    for query, expected_term in cases:
        assert expected_term in expand_search_terms(query)


def test_meilisearch_failure_falls_back_to_database(db_factory, monkeypatch):
    with db_factory() as db:
        create_searchable_image(db)
        service = SearchService(
            db,
            search_backend="meilisearch",
            meilisearch_url="http://127.0.0.1:7700",
        )

        def unavailable(_keyword: str, _limit: int):
            raise SearchUnavailable("索引未就绪")

        monkeypatch.setattr(service, "_search_meilisearch", unavailable)
        response = service.search("动画", 12)

    assert response.search_mode == "fuzzy"
    assert response.fallback is True
    assert response.fallback_reason == "索引未就绪"
    assert len(response.results) == 1


def test_meilisearch_response_uses_external_score(db_factory, monkeypatch):
    with db_factory() as db:
        image = create_searchable_image(db)
        service = SearchService(
            db,
            search_backend="meilisearch",
            meilisearch_url="http://127.0.0.1:7700",
        )

        def indexed(_keyword: str, _limit: int):
            return [SearchHit(image=image, score=0.97, reasons=("Meilisearch 匹配",))]

        monkeypatch.setattr(service, "_search_meilisearch", indexed)
        response = service.search("同步", 12)

    assert response.search_mode == "meilisearch"
    assert response.fallback is False
    assert response.results[0].match_level == "S"
    assert response.results[0].final_score == 0.97


def test_smart_search_attempts_meilisearch_with_ai_expansion(db_factory, monkeypatch):
    with db_factory() as db:
        image = create_searchable_image(db)
        service = SearchService(db, meilisearch_url="http://127.0.0.1:7700")
        captured = {}

        understanding = SearchUnderstanding(
            original_query="听课费劲",
            normalized_query="动画精讲",
            search_intent="用户在找帮助孩子听懂知识点的图片",
            query_type="pain_point_search",
            expanded_level1_tags=[
                ExpandedSearchTag(
                    tag="孩子听不懂",
                    relation="strong",
                    reason="家长痛点表达",
                    weight=0.82,
                )
            ],
            matched_level2_categories=[
                SearchCategoryMatch(
                    category="同步校内体系 > 动画精讲",
                    relation="direct",
                    reason="对应动画讲解卖点",
                    weight=0.9,
                )
            ],
            exclude_tags=[],
            search_strategy="优先按动画精讲召回",
        )

        monkeypatch.setattr(service, "_understand_search", lambda _keyword: understanding)

        def indexed(keyword: str, _limit: int):
            captured["keyword"] = keyword
            return [SearchHit(image=image, score=0.96, reasons=("Meilisearch 匹配",))]

        monkeypatch.setattr(service, "_search_meilisearch", indexed)
        response = service.search("听课费劲", 12, "smart")

    assert response.search_mode == "meilisearch"
    assert response.search_understanding == understanding
    assert "动画精讲" in captured["keyword"]
    assert response.results[0].match_level == "S"


def test_smart_search_without_meilisearch_uses_ai_expansion_database(db_factory, monkeypatch):
    with db_factory() as db:
        create_searchable_image(db)
        service = SearchService(db)
        understanding = SearchUnderstanding(
            original_query="听课费劲",
            normalized_query="动画精讲",
            search_intent="用户在找帮助孩子听懂知识点的图片",
            query_type="pain_point_search",
            expanded_level1_tags=[],
            matched_level2_categories=[],
            exclude_tags=[],
            search_strategy="使用二级标签兜底",
        )
        monkeypatch.setattr(service, "_understand_search", lambda _keyword: understanding)
        response = service.search("听课费劲", 12, "smart")

    assert response.search_mode == "fuzzy"
    assert response.fallback is True
    assert response.search_understanding == understanding
    assert len(response.results) == 1
    assert "AI 意图理解：标准化查询" in response.results[0].match_reasons
