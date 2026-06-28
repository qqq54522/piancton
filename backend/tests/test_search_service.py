import json

from app.domain.business_intents import BusinessIntent, BusinessIntentCatalog
from app.domain.search_query_expansion import expand_search_terms
from app.models.image import (
    ContentTag,
    Image,
    ImageBusinessLabel,
    ImageEmbedding,
    ImageLevel2Category,
    ImageTag,
)
from app.models.tag import Tag
from app.repositories.image_repository import ImageRepository
from app.schemas.ai import (
    ConfidenceTag,
    ExpandedSearchTag,
    ImageAnalysisResult,
    SearchCategoryMatch,
    SearchUnderstanding,
    SecondaryLabel,
)
from app.services.image_analysis_service import ImageAnalysisService
from app.services.search_models import SearchHit, SearchUnavailable
from app.services.search_service import SearchService
from app.services.semantic_search_clients import RerankResult, SemanticSearchClientError


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


def create_business_intent_image(
    db,
    *,
    system_code: str,
    system_name: str,
    label_code: str,
    label_name: str,
    title: str,
    summary: str,
) -> Image:
    system = Tag(
        code=system_code,
        name=system_name,
        color="#6366F1",
        node_type="system",
        assignable=False,
        status="active",
    )
    business_tag = Tag(
        code=label_code,
        name=label_name,
        color="#818CF8",
        parent=system,
        is_secondary=True,
        node_type="image_label",
        assignable=True,
        status="active",
    )
    image = Image(
        title=title,
        file_name=f"{label_code}.png",
        storage_key=f"{label_code}.png",
        thumbnail_storage_key=f"{label_code}-thumb.jpg",
        media_type="image/png",
        size_bytes=100,
        uploader="admin",
        image_summary=summary,
    )
    image.tag_links.append(ImageTag(tag=business_tag))
    image.business_labels.append(
        ImageBusinessLabel(
            tag=business_tag,
            label_code=label_code,
            origin="manual",
            role="primary",
            review_status="accepted",
            confidence=1.0,
        )
    )
    db.add(image)
    db.commit()
    return image


def create_generic_image(
    db,
    *,
    tag_name: str,
    title: str,
    summary: str,
) -> Image:
    tag = Tag(name=tag_name, color="#94A3B8")
    image = Image(
        title=title,
        file_name=f"{tag_name}.png",
        storage_key=f"{tag_name}.png",
        thumbnail_storage_key=f"{tag_name}-thumb.jpg",
        media_type="image/png",
        size_bytes=100,
        uploader="admin",
        image_summary=summary,
    )
    image.tag_links.append(ImageTag(tag=tag))
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


def test_database_search_treats_image_summary_as_strong_semantic_match(db_factory):
    with db_factory() as db:
        image = Image(
            title="素材 A",
            file_name="planning.png",
            storage_key="planning.png",
            thumbnail_storage_key="planning-thumb.jpg",
            media_type="image/png",
            size_bytes=100,
            uploader="designer",
            image_summary="家长正在查看孩子学习规划进度",
        )
        db.add(image)
        db.commit()

        response = SearchService(db).search(
            "我想找家长正在查看孩子学习规划进度的素材",
            12,
            "precise",
        )

    assert len(response.results) == 1
    assert response.results[0].image.title == "素材 A"
    assert response.results[0].match_level == "A"
    assert response.results[0].final_score == 0.9
    assert "图片摘要匹配" in response.results[0].match_reasons


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


def test_smart_search_uses_local_business_intents_without_ai_provider(db_factory):
    with db_factory() as db:
        error_book = create_business_intent_image(
            db,
            system_code="sync_self_study",
            system_name="同步自学体系-错题",
            label_code="ai_error_book",
            label_name="AI错题本",
            title="错题本功能图",
            summary="展示错题上传、错因分析和同类题复习闭环。",
        )
        photo_learning = create_business_intent_image(
            db,
            system_code="sync_self_study_2",
            system_name="同步自学体系-拍题",
            label_code="photo_guided_learning",
            label_name="AI拍题精学",
            title="拍题精学功能图",
            summary="展示拍题后分步讲解解题思路，不直接给最终答案。",
        )
        expert_planning = create_business_intent_image(
            db,
            system_code="sync_cultivation",
            system_name="同步培养体系",
            label_code="expert_planning",
            label_name="专家规划",
            title="专家规划功能图",
            summary="展示命题专家和教研团队设计课程路径。",
        )

        cases = [
            ("整理错题费功夫又容易忘", error_book.id, "同步自学体系 > AI错题本"),
            ("孩子拍题只抄答案考试不会", photo_learning.id, "同步自学体系 > AI拍题精学"),
            ("出卷人编教材的人设计课程", expert_planning.id, "同步培养体系 > 专家规划"),
        ]
        for query, expected_image_id, expected_category in cases:
            response = SearchService(db).search(query, 12, "smart")

            assert response.search_understanding is not None
            assert response.search_understanding.normalized_query in {
                "AI错题本",
                "AI拍题精学",
                "专家规划",
            }
            assert response.search_understanding.matched_level2_categories[0].category == (
                expected_category
            )
            assert response.results[0].image.id == expected_image_id
            assert "AI 意图理解：标准化查询" in response.results[0].match_reasons


def test_strong_business_intent_filters_generic_fallback_results(db_factory):
    with db_factory() as db:
        expected = create_business_intent_image(
            db,
            system_code="sync_self_study",
            system_name="同步自学体系",
            label_code="photo_guided_learning",
            label_name="AI拍题精学",
            title="拍题精学功能图",
            summary="展示拍题后分步讲解解题思路，不是普通答案页，也不直接给最终答案。",
        )
        create_generic_image(
            db,
            tag_name="普通拍题",
            title="普通拍题答案素材",
            summary="孩子拍题后只看到最终答案，没有分步讲解。",
        )

        response = SearchService(db).search(
            "孩子拍题只抄答案考试不会",
            12,
            "smart",
        )

    assert [result.image.id for result in response.results] == [expected.id]
    assert response.results[0].match_level in {"S", "A", "B"}
    assert any(
        "强意图业务话术匹配" in reason
        and "孩子拍题只抄答案考试不会" in reason
        for reason in response.results[0].match_reasons
    )
    assert "强意图主标签匹配：AI拍题精学" in response.results[0].match_reasons
    assert "强意图排除项检查通过" in response.results[0].match_reasons


def test_ai_recommended_search_words_recall_long_business_phrase(db_factory):
    with db_factory() as db:
        system = Tag(
            code="sync_self_study",
            name="同步自学体系",
            color="#6366F1",
            node_type="system",
            assignable=False,
            status="active",
        )
        business_tag = Tag(
            code="photo_guided_learning",
            name="AI拍题精学",
            color="#818CF8",
            parent=system,
            is_secondary=True,
            node_type="image_label",
            assignable=True,
            status="active",
        )
        image = Image(
            title="拍题精学功能图",
            file_name="photo-learning.png",
            storage_key="photo-learning.png",
            thumbnail_storage_key="photo-learning-thumb.jpg",
            media_type="image/png",
            size_bytes=100,
            uploader="designer",
        )
        db.add_all([system, business_tag, image])
        db.commit()

        ImageAnalysisService(db).save_ai_analysis(
            image.id,
            ImageAnalysisResult(
                image_type="function",
                image_summary=(
                    "孩子在拍题学习界面查看分步讲解，突出不只给答案而是讲清思路，"
                    "不是普通答案页。"
                ),
                content_tags=[
                    ConfidenceTag(
                        tag=f"拍题视觉标签{index}",
                        confidence=0.9,
                        dimension="产品功能",
                    )
                    for index in range(20)
                ],
                secondary_labels=[
                    SecondaryLabel(
                        label_code="photo_guided_learning",
                        system="同步自学体系",
                        label="AI拍题精学",
                        confidence=0.93,
                        evidence_level="A",
                        role="primary",
                        reason="画面展示拍题后的分步讲解，适合AI拍题精学，不是普通答案页。",
                    )
                ],
                recommended_search_words=[
                    "拍题",
                    "分步讲解",
                    "讲清思路",
                    "不只给答案",
                    "孩子拍题只抄答案考试不会",
                ],
                negative_tags=["普通答案页", "纯题库"],
            ),
        )

        saved = ImageRepository(db).get(image.id)
        response = SearchService(db).search(
            "孩子拍题只抄答案考试不会",
            12,
            "precise",
        )

    assert saved is not None
    tag_names = [item.tag_name for item in saved.content_tags]
    assert "孩子拍题只抄答案考试不会" in tag_names
    assert "普通答案页" not in tag_names
    assert [result.image.id for result in response.results] == [image.id]
    assert "标签匹配" in response.results[0].match_reasons


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

        monkeypatch.setattr(service.meilisearch_recall, "search", unavailable)
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

        monkeypatch.setattr(service.meilisearch_recall, "search", indexed)
        response = service.search("同步", 12)

    assert response.search_mode == "meilisearch"
    assert response.fallback is False
    assert response.results[0].match_level == "S"
    assert response.results[0].final_score == 0.97


def test_reranker_reorders_database_candidates(db_factory):
    class FakeReranker:
        configured = True

        def rerank(self, *, query: str, documents: list[str], top_n: int):
            assert query == "学习规划"
            assert top_n == 2
            assert "语义总结：学习规划" in documents[1]
            return [
                RerankResult(index=1, score=0.96),
                RerankResult(index=0, score=0.55),
            ]

    with db_factory() as db:
        db.add_all(
            [
                Image(
                    title="学习规划标题",
                    file_name="title.png",
                    storage_key="title.png",
                    thumbnail_storage_key="title-thumb.jpg",
                    media_type="image/png",
                    size_bytes=100,
                    uploader="designer",
                    image_summary="普通学习页面",
                ),
                Image(
                    title="普通标题",
                    file_name="summary.png",
                    storage_key="summary.png",
                    thumbnail_storage_key="summary-thumb.jpg",
                    media_type="image/png",
                    size_bytes=100,
                    uploader="designer",
                    image_summary="学习规划",
                ),
            ]
        )
        db.commit()
        response = SearchService(db, reranker=FakeReranker()).search(
            "学习规划",
            2,
            "precise",
        )

    assert [result.image.title for result in response.results] == ["普通标题", "学习规划标题"]
    assert response.results[0].match_level == "S"
    assert "Reranker 语义重排" in response.results[0].match_reasons


def test_reranker_failure_keeps_original_database_order(db_factory):
    class FailingReranker:
        configured = True

        def rerank(self, *, query: str, documents: list[str], top_n: int):
            raise SemanticSearchClientError("temporary failure")

    with db_factory() as db:
        db.add_all(
            [
                Image(
                    title="学习规划标题",
                    file_name="title.png",
                    storage_key="title.png",
                    thumbnail_storage_key="title-thumb.jpg",
                    media_type="image/png",
                    size_bytes=100,
                    uploader="designer",
                    image_summary="普通学习页面",
                ),
                Image(
                    title="普通标题",
                    file_name="summary.png",
                    storage_key="summary.png",
                    thumbnail_storage_key="summary-thumb.jpg",
                    media_type="image/png",
                    size_bytes=100,
                    uploader="designer",
                    image_summary="学习规划",
                ),
            ]
        )
        db.commit()
        response = SearchService(db, reranker=FailingReranker()).search(
            "学习规划",
            2,
            "precise",
        )

    assert [result.image.title for result in response.results] == ["学习规划标题", "普通标题"]
    assert all("Reranker 语义重排" not in result.match_reasons for result in response.results)


def test_embedding_search_recalls_semantic_candidates_without_keyword_match(db_factory):
    class FakeEmbeddingClient:
        configured = True
        model_name = "fake-embedding"

        def embed(self, inputs: list[str]):
            assert inputs == ["学习规划"]
            return [[1.0, 0.0]]

    with db_factory() as db:
        closer = Image(
            title="素材 B",
            file_name="b.png",
            storage_key="b.png",
            thumbnail_storage_key="b-thumb.jpg",
            media_type="image/png",
            size_bytes=100,
            uploader="designer",
            image_summary="家长查看孩子进度",
        )
        farther = Image(
            title="素材 C",
            file_name="c.png",
            storage_key="c.png",
            thumbnail_storage_key="c-thumb.jpg",
            media_type="image/png",
            size_bytes=100,
            uploader="designer",
            image_summary="课程动画讲解",
        )
        db.add_all([closer, farther])
        db.flush()
        db.add_all(
            [
                ImageEmbedding(
                    image=closer,
                    model_name="fake-embedding",
                    dimension=2,
                    content_hash="closer",
                    document_text="语义总结：家长查看孩子进度",
                    vector_json=json.dumps([1.0, 0.0]),
                ),
                ImageEmbedding(
                    image=farther,
                    model_name="fake-embedding",
                    dimension=2,
                    content_hash="farther",
                    document_text="语义总结：课程动画讲解",
                    vector_json=json.dumps([0.0, 1.0]),
                ),
            ]
        )
        db.commit()
        response = SearchService(db, embedding_client=FakeEmbeddingClient()).search(
            "学习规划",
            2,
            "precise",
        )

    assert [result.image.title for result in response.results] == ["素材 B"]
    assert response.results[0].match_level == "S"
    assert "Embedding 语义召回" in response.results[0].match_reasons


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

        monkeypatch.setattr(service.meilisearch_recall, "search", indexed)
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


def test_smart_search_uses_ai_when_local_business_intent_is_ambiguous(db_factory):
    class FakeProvider:
        configured = True

    class FakeAiService:
        provider = FakeProvider()

        def understand_search(self, keyword: str) -> SearchUnderstanding:
            assert keyword == "体现规划"
            return SearchUnderstanding(
                original_query=keyword,
                normalized_query="专家规划",
                search_intent="用户在找专家参与课程规划的素材",
                query_type="business_intent_search",
                expanded_level1_tags=[],
                matched_level2_categories=[
                    SearchCategoryMatch(
                        category="同步培养体系 > 专家规划",
                        relation="direct",
                        reason="AI 根据上下文消歧为专家规划",
                        weight=0.91,
                    )
                ],
                exclude_tags=["普通学习规划"],
                search_strategy="按专家规划强意图召回",
            )

    with db_factory() as db:
        create_business_intent_image(
            db,
            system_code="sync_planning",
            system_name="同步规划体系",
            label_code="ai_learning_plan",
            label_name="AI定制学习方案",
            title="AI定制学习方案",
            summary="根据孩子水平生成学习计划。",
        )
        create_business_intent_image(
            db,
            system_code="sync_cultivation",
            system_name="同步培养体系",
            label_code="expert_planning",
            label_name="专家规划",
            title="专家规划",
            summary="命题专家和教材编者参与课程规划。",
        )
        service = SearchService(db, ai_service=FakeAiService())
        service.query_understanding.catalog = BusinessIntentCatalog(
            version="test",
            intents=(
                BusinessIntent(
                    code="plan_intent",
                    name="学习规划",
                    target_system_code="sync_planning",
                    target_label_code="ai_learning_plan",
                    phrases=("规划",),
                    pain_points=(),
                    must_have_concepts=(),
                    nice_to_have_concepts=(),
                    exclude_concepts=(),
                    result_policy="strict_allow_few_results",
                ),
                BusinessIntent(
                    code="expert_intent",
                    name="专家规划",
                    target_system_code="sync_cultivation",
                    target_label_code="expert_planning",
                    phrases=("规划",),
                    pain_points=(),
                    must_have_concepts=(),
                    nice_to_have_concepts=(),
                    exclude_concepts=("普通学习规划",),
                    result_policy="strict_allow_few_results",
                ),
            ),
        )
        response = service.search("体现规划", 12, "smart")

    assert response.search_understanding is not None
    assert response.search_understanding.normalized_query == "专家规划"
    assert [result.image.title for result in response.results] == ["专家规划"]
    assert response.results[0].match_level == "S"
