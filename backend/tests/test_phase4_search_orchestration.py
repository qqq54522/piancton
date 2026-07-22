import asyncio
import threading
import time

import pytest

from app.core.errors import AppError
from app.models.asset import AssetConceptLink, AssetGroup, AssetSearchPhrase
from app.models.business_concept import BusinessConcept, ConceptSearchPhrase
from app.models.image import Image
from app.schemas.ai import (
    SearchConceptMatch,
    SearchProofPointMatch,
    SearchSystemCandidate,
    SearchSystemRouting,
    SearchUnderstanding,
)
from app.services.search_cache import build_search_caches
from app.services.search_models import SearchHit
from app.services.search_ranking_service import SearchRankingService
from app.services.search_rerank_coordinator import SearchRerankCoordinator
from app.services.search_service import SearchService
from app.services.semantic_search_clients import RerankResult, SemanticSearchClientError


def _image(title: str, file_name: str) -> Image:
    return Image(
        title=title,
        file_name=file_name,
        storage_key=file_name,
        thumbnail_storage_key=f"thumb-{file_name}",
        media_type="image/png",
        size_bytes=100,
        uploader="designer",
    )


def _understanding(query: str) -> SearchUnderstanding:
    return SearchUnderstanding(
        original_query=query,
        normalized_query=query,
        search_intent="并行理解测试",
        query_type="business_intent_search",
        expanded_terms=[],
        matched_business_concepts=[],
        excluded_concepts=[],
        search_strategy="模型理解可超时丢弃",
    )


def test_phase4_external_branches_start_in_parallel(db_factory, monkeypatch):
    barrier = threading.Barrier(3)

    class ParallelEmbedding:
        configured = True
        model_name = "parallel-embedding"

        def embed(self, inputs: list[str]):
            barrier.wait(timeout=1)
            return [[1.0, 0.0]]

    class Provider:
        configured = True

    class ParallelAi:
        provider = Provider()

        def understand_search(self, keyword: str):
            barrier.wait(timeout=1)
            return _understanding(keyword)

    with db_factory() as db:
        service = SearchService(
            db,
            search_backend="meilisearch",
            meilisearch_url="http://search.test",
            embedding_client=ParallelEmbedding(),
            ai_service=ParallelAi(),
            meilisearch_timeout_seconds=1,
            embedding_timeout_seconds=1,
            understanding_timeout_seconds=1,
        )

        def meili(_keyword: str, _limit: int):
            barrier.wait(timeout=1)
            return []

        monkeypatch.setattr(service.meilisearch_recall, "recall_candidates", meili)
        response = service.search("完全未知的复杂搜索句子", 12)

    diagnostics = response.search_diagnostics
    assert diagnostics is not None
    statuses = {item.source: item.status for item in diagnostics.branches}
    assert statuses["meilisearch"] == "ok"
    assert statuses["embedding"] == "ok"
    assert statuses["query_understanding"] == "ok"


def test_phase4_staged_model_uses_independent_layer_budgets(db_factory):
    class Provider:
        configured = True

    class StagedAi:
        provider = Provider()
        knowledge = None

        def route_search_system(self, keyword: str):
            time.sleep(0.02)
            return SearchSystemRouting(
                original_query=keyword,
                route_type="single_system",
                candidate_systems=[
                    SearchSystemCandidate(
                        code="sync_self_study",
                        relation="primary",
                        reason="拍题后分步点拨",
                        weight=0.98,
                    )
                ],
            )

        def routed_system_codes(self, _routing):
            return ("sync_self_study",)

        def understand_search_from_route(self, keyword: str, _routing):
            time.sleep(0.02)
            return SearchUnderstanding(
                original_query=keyword,
                normalized_query="AI拍题精学",
                search_intent="拍题后分步点拨，不直接给答案",
                query_type="business_intent_search",
                matched_business_concepts=[
                    SearchConceptMatch(
                        concept="AI拍题精学",
                        relation="direct",
                        reason="同步自学体系内卖点边界命中",
                        weight=0.98,
                    )
                ],
                search_strategy="只召回已审核 AI 拍题精学素材",
            )

    with db_factory() as db:
        image = _image("拍题精学素材", "guided.png")
        concept = BusinessConcept(code="photo_guided_learning", name="AI拍题精学")
        group = AssetGroup(
            title=image.title,
            created_by="designer",
            images=[image],
            concept_links=[
                AssetConceptLink(
                    concept=concept,
                    relation_role="expresses",
                    origin="manual",
                    review_status="accepted",
                )
            ],
        )
        db.add_all([concept, group])
        db.flush()
        group.primary_image_id = image.id
        db.commit()

        response = SearchService(
            db,
            ai_service=StagedAi(),
            understanding_timeout_seconds=0.025,
            system_routing_timeout_seconds=0.06,
            selling_point_timeout_seconds=0.06,
        ).search("拍一道不会的题，分步告诉我思路", 12)

    assert [item.image.id for item in response.results] == [image.id]
    branch = next(
        item
        for item in response.search_diagnostics.branches
        if item.source == "query_understanding"
    )
    assert branch.status == "ok"
    assert "体系路由" in (branch.detail or "")
    assert "卖点识别" in (branch.detail or "")


def test_phase4_second_layer_timeout_does_not_open_global_recall(
    db_factory,
    monkeypatch,
):
    class Provider:
        configured = True

    class SlowSecondLayerAi:
        provider = Provider()
        knowledge = None

        def route_search_system(self, keyword: str):
            return SearchSystemRouting(
                original_query=keyword,
                route_type="single_system",
                candidate_systems=[
                    SearchSystemCandidate(
                        code="sync_self_study",
                        relation="primary",
                        reason="一键拍照后分步解析",
                        weight=0.97,
                    )
                ],
            )

        def routed_system_codes(self, _routing):
            return ("sync_self_study",)

        def understand_search_from_route(self, _keyword: str, _routing):
            time.sleep(0.08)
            return _understanding(_keyword)

    query = "一键拍照后帮我分析思路，但别直接给最终答案"
    with db_factory() as db:
        unrelated = _image(query, "unrelated.png")
        db.add(unrelated)
        db.commit()
        service = SearchService(
            db,
            search_backend="meilisearch",
            meilisearch_url="http://search.test",
            ai_service=SlowSecondLayerAi(),
            system_routing_timeout_seconds=0.03,
            selling_point_timeout_seconds=0.01,
            understanding_grace_seconds=0,
        )
        monkeypatch.setattr(
            service.meilisearch_recall,
            "recall_candidates",
            lambda _keyword, _limit: [],
        )
        response = service.search(query, 12)

    assert response.results == []
    assert response.fallback is True
    branch = next(
        item
        for item in response.search_diagnostics.branches
        if item.source == "query_understanding"
    )
    assert branch.status == "timed_out"
    assert "精度保护" in (branch.detail or "")


def test_phase4_all_external_failures_keep_database_results(db_factory, monkeypatch):
    class FailingEmbedding:
        configured = True
        model_name = "failing-embedding"

        def embed(self, _inputs: list[str]):
            raise SemanticSearchClientError("embedding down")

    class Provider:
        configured = True

    class FailingAi:
        provider = Provider()

        def understand_search(self, _keyword: str):
            raise AppError("model_down", "understanding down", status_code=502)

    with db_factory() as db:
        image = _image("稳定兜底素材", "fallback.png")
        db.add(image)
        db.commit()
        service = SearchService(
            db,
            search_backend="meilisearch",
            meilisearch_url="http://search.test",
            embedding_client=FailingEmbedding(),
            ai_service=FailingAi(),
        )

        def meili_failure(_keyword: str, _limit: int):
            raise RuntimeError("meilisearch down")

        monkeypatch.setattr(
            service.meilisearch_recall,
            "recall_candidates",
            meili_failure,
        )
        response = service.search("稳定兜底素材", 12)

    assert [item.image.id for item in response.results] == [image.id]
    assert response.fallback is True
    assert response.search_diagnostics is not None
    assert set(response.search_diagnostics.degraded_sources) == {
        "meilisearch",
        "embedding",
        "query_understanding",
    }


def test_phase4_slow_branch_times_out_without_delaying_database(db_factory, monkeypatch):
    with db_factory() as db:
        image = _image("超时兜底素材", "timeout.png")
        db.add(image)
        db.commit()
        service = SearchService(
            db,
            search_backend="meilisearch",
            meilisearch_url="http://search.test",
            meilisearch_timeout_seconds=0.01,
            total_timeout_seconds=0.2,
        )

        def slow_meili(_keyword: str, _limit: int):
            time.sleep(0.08)
            return []

        monkeypatch.setattr(
            service.meilisearch_recall,
            "recall_candidates",
            slow_meili,
        )
        response = service.search("超时兜底素材", 12)

    assert [item.image.id for item in response.results] == [image.id]
    assert response.search_diagnostics is not None
    branch = next(
        item
        for item in response.search_diagnostics.branches
        if item.source == "meilisearch"
    )
    assert branch.status == "timed_out"
    assert response.fallback is True
    assert response.search_diagnostics.total_duration_ms < 200


def test_phase4_embedding_vector_cache_reuses_common_query(db_factory):
    class CachedEmbedding:
        configured = True
        model_name = "cached-embedding"

        def __init__(self):
            self.calls = 0

        def embed(self, _inputs: list[str]):
            self.calls += 1
            return [[1.0, 0.0]]

    embedding = CachedEmbedding()
    with db_factory() as db:
        service = SearchService(db, embedding_client=embedding)
        first = service.search("重复查询", 12)
        second = service.search("重复查询", 12)

    assert embedding.calls == 1
    assert first.search_diagnostics is not None
    assert second.search_diagnostics is not None
    second_embedding = next(
        item
        for item in second.search_diagnostics.branches
        if item.source == "embedding"
    )
    assert second_embedding.cache_hit is True


def test_phase4_catalog_edit_supersedes_cached_model_understanding(db_factory):
    class Provider:
        configured = True

    class CachedAi:
        provider = Provider()
        knowledge = None

        def __init__(self):
            self.calls = 0

        def understand_search(self, keyword: str):
            self.calls += 1
            return SearchUnderstanding(
                original_query=keyword,
                normalized_query="缓存刷新卖点",
                search_intent="模型旧理解",
                query_type="business_intent_search",
                matched_business_concepts=[],
                search_strategy="测试缓存",
            )

    ai = CachedAi()
    caches = build_search_caches(ttl_seconds=300, max_entries=16)
    with db_factory() as db:
        concept = BusinessConcept(
            code="cache_refresh_concept",
            name="缓存刷新卖点",
            status="active",
        )
        db.add(concept)
        db.commit()

        first = SearchService(db, ai_service=ai, caches=caches).search("独家暗号", 12)
        assert ai.calls == 1
        assert first.search_understanding is not None

        concept.search_phrases.append(
            ConceptSearchPhrase(
                phrase="独家暗号",
                phrase_type="official",
                origin="manual",
                review_status="accepted",
            )
        )
        db.commit()

        second = SearchService(db, ai_service=ai, caches=caches).search("独家暗号", 12)

    assert ai.calls == 1
    assert second.search_understanding is not None
    assert second.search_understanding.normalized_query == "缓存刷新卖点"
    assert second.search_diagnostics is not None
    understanding_branch = next(
        item
        for item in second.search_diagnostics.branches
        if item.source == "query_understanding"
    )
    assert understanding_branch.status == "skipped"
    assert understanding_branch.cache_hit is False
    assert understanding_branch.detail == "本地高置信业务证据已满足，无需模型补充"


def test_phase4_versioned_concept_phrase_recalls_confirmed_asset(db_factory):
    with db_factory() as db:
        image = _image("没有关键词的素材", "concept.png")
        group = AssetGroup(
            title="概念素材组",
            created_by="designer",
            images=[image],
        )
        concept = BusinessConcept(
            code="guided_thinking",
            name="引导式思考",
            concept_type="teaching_method",
            search_phrases=[
                ConceptSearchPhrase(
                    phrase="不是直接告诉答案",
                    phrase_type="pain",
                    origin="manual",
                    review_status="accepted",
                    weight=0.96,
                )
            ],
        )
        group.concept_links.append(
            AssetConceptLink(
                concept=concept,
                relation_role="expresses",
                origin="manual",
                review_status="accepted",
            )
        )
        db.add_all([group, concept])
        db.flush()
        group.primary_image_id = image.id
        db.commit()

        response = SearchService(db).search(
            "不是直接告诉答案",
            12,
        )

    assert [item.image.id for item in response.results] == [image.id]
    assert any(
        "概念搜索表达命中" in reason
        for reason in response.results[0].match_reasons
    )
    assert any(
        "素材主要表达业务概念" in reason
        for reason in response.results[0].match_reasons
    )


def test_phase4_school_alignment_query_recalls_confirmed_asset_locally(db_factory):
    class UnexpectedEmbedding:
        configured = True
        model_name = "unused-for-high-confidence-local-query"

        def embed(self, _inputs: list[str]):
            raise AssertionError("本地高置信概念查询不应等待 Embedding")

    with db_factory() as db:
        image = _image("课程同步", "school-sync.png")
        concept = BusinessConcept(
            code="school_sync",
            name="同步校内",
            concept_type="business_term",
        )
        group = AssetGroup(
            title=image.title,
            created_by="designer",
            images=[image],
            concept_links=[
                AssetConceptLink(
                    concept=concept,
                    relation_role="expresses",
                    origin="manual",
                    review_status="accepted",
                )
            ],
        )
        db.add_all([concept, group])
        db.flush()
        group.primary_image_id = image.id
        db.commit()

        response = SearchService(
            db,
            embedding_client=UnexpectedEmbedding(),
        ).search("和学校课程一致", 12)

    assert response.search_understanding is not None
    assert response.search_understanding.normalized_query == "同步校内"
    assert [item.image.id for item in response.results] == [image.id]
    assert any(
        "素材主要表达业务概念" in reason
        for reason in response.results[0].match_reasons
    )
    assert response.search_diagnostics is not None
    embedding_branch = next(
        item
        for item in response.search_diagnostics.branches
        if item.source == "embedding"
    )
    assert embedding_branch.status == "skipped"
    assert embedding_branch.detail == "本地高置信业务概念已满足"


def test_phase4_objectless_photo_query_opens_guided_and_rapid_candidates(
    db_factory,
):
    # D079：无拍摄对象的拍照入口 + 讲解目的是拍题精学/极速预习复习共享组合，
    # 探索型合并两个卖点的已确认素材；AI 私教、其他卖点和标题巧合仍被排除。
    query = "一键拍照，AI 即刻为你提供思路点拨与详细解析，拒绝直接给答案"
    concept_specs = [
        ("photo_guided_learning", "AI拍题精学"),
        ("rapid_preview_review", "极速预习复习"),
        ("ai_tutor_qa", "AI私教答疑"),
    ]
    with db_factory() as db:
        expected_id_by_code: dict[str, str] = {}
        for code, name in concept_specs:
            image = _image(f"{name}素材", f"{code}.png")
            concept = BusinessConcept(code=code, name=name)
            group = AssetGroup(
                title=image.title,
                created_by="designer",
                images=[image],
                concept_links=[
                    AssetConceptLink(
                        concept=concept,
                        relation_role="expresses",
                        origin="manual",
                        review_status="accepted",
                    )
                ],
            )
            db.add_all([concept, group])
            db.flush()
            group.primary_image_id = image.id
            expected_id_by_code[code] = image.id

        distractor = _image(query, "title-only.png")
        school_image = _image("不应由相邻词误召回", "school.png")
        school_concept = BusinessConcept(
            code="school_sync",
            name="同步校内",
            search_phrases=[
                ConceptSearchPhrase(
                    phrase="预习复习",
                    origin="manual",
                    review_status="accepted",
                )
            ],
        )
        school_group = AssetGroup(
            title=school_image.title,
            created_by="designer",
            images=[school_image],
            concept_links=[
                AssetConceptLink(
                    concept=school_concept,
                    relation_role="expresses",
                    origin="manual",
                    review_status="accepted",
                )
            ],
        )
        db.add_all([distractor, school_concept, school_group])
        db.flush()
        school_group.primary_image_id = school_image.id
        db.commit()

        response = SearchService(db).search(query, 12)

    assert response.search_understanding is not None
    assert (
        response.search_understanding.query_type
        == "exploratory_business_intent_search"
    )
    assert "你可能在找" in response.search_understanding.search_intent
    result_ids = {item.image.id for item in response.results}
    assert result_ids == {
        expected_id_by_code["photo_guided_learning"],
        expected_id_by_code["rapid_preview_review"],
    }
    assert expected_id_by_code["ai_tutor_qa"] not in result_ids
    assert school_image.id not in result_ids
    assert distractor.id not in result_ids
    matched_by_image = {
        item.image.id: {
            match.concept_name for match in item.matched_query_concepts
        }
        for item in response.results
    }
    assert matched_by_image[expected_id_by_code["photo_guided_learning"]] == {
        "AI拍题精学"
    }
    assert matched_by_image[expected_id_by_code["rapid_preview_review"]] == {
        "极速预习复习"
    }


def test_phase4_objectless_photo_query_requires_entry_assets_not_socratic_method(
    db_factory,
):
    # D084：主入口“拍照”必须先覆盖拍题精学和极速预习；只有通用的点拨、
    # 解析和不直接给答案时，不能让苏格拉底方法证明图替代入口素材。
    query = "一键拍照，AI 即刻为你提供思路点拨与详细解析，拒绝直接给答案"
    with db_factory() as db:
        photo_guided = BusinessConcept(
            code="photo_guided_learning",
            name="AI拍题精学",
        )
        rapid = BusinessConcept(code="rapid_preview_review", name="极速预习复习")

        photo_entry = _image("拍题精学", "photo-entry.png")
        photo_entry_group = AssetGroup(
            title=photo_entry.title,
            created_by="designer",
            images=[photo_entry],
            concept_links=[
                AssetConceptLink(
                    concept=photo_guided,
                    relation_role="expresses",
                    origin="manual",
                    review_status="accepted",
                )
            ],
        )
        socratic = _image("苏格拉底讲解提问", "socratic.png")
        socratic_group = AssetGroup(
            title=socratic.title,
            created_by="designer",
            images=[socratic],
            concept_links=[
                AssetConceptLink(
                    concept=photo_guided,
                    relation_role="expresses",
                    origin="manual",
                    review_status="accepted",
                )
            ],
            search_phrases=[
                AssetSearchPhrase(
                    phrase=query,
                    origin="manual",
                    review_status="accepted",
                )
            ],
        )
        rapid_entry = _image("极速预习", "rapid-entry.png")
        rapid_entry_group = AssetGroup(
            title=rapid_entry.title,
            created_by="designer",
            images=[rapid_entry],
            concept_links=[
                AssetConceptLink(
                    concept=rapid,
                    relation_role="expresses",
                    origin="manual",
                    review_status="accepted",
                )
            ],
        )
        db.add_all([photo_entry_group, socratic_group, rapid_entry_group])
        db.flush()
        photo_entry_group.primary_image_id = photo_entry.id
        socratic_group.primary_image_id = socratic.id
        rapid_entry_group.primary_image_id = rapid_entry.id
        db.commit()

        response = SearchService(db).search(query, 12)

    assert response.search_understanding is not None
    assert (
        response.search_understanding.query_type
        == "exploratory_business_intent_search"
    )
    assert [item.image.id for item in response.results] == [
        photo_entry.id,
        rapid_entry.id,
    ]
    assert socratic.id not in {item.image.id for item in response.results}


def test_phase4_learning_outcome_visibility_only_keeps_report_shaped_assets(
    db_factory,
):
    query = "随时能看到学习成果"
    with db_factory() as db:
        instant_quiz = BusinessConcept(code="instant_quiz", name="课后小测")
        learning_report = BusinessConcept(
            code="learning_report",
            name="学情报告反馈",
        )

        report = _image("家长看到学习结果", "parent-report.png")
        report_group = AssetGroup(
            title=report.title,
            created_by="designer",
            images=[report],
            concept_links=[
                AssetConceptLink(
                    concept=learning_report,
                    relation_role="expresses",
                    origin="manual",
                    review_status="accepted",
                )
            ],
            search_phrases=[
                AssetSearchPhrase(
                    phrase="找一张家长能看到孩子学习结果和建议的图",
                    origin="manual",
                    review_status="accepted",
                )
            ],
        )
        quiz_report = _image("配套功能学情报告", "quiz-report.png")
        quiz_report_group = AssetGroup(
            title=quiz_report.title,
            created_by="designer",
            images=[quiz_report],
            concept_links=[
                AssetConceptLink(
                    concept=instant_quiz,
                    relation_role="expresses",
                    origin="manual",
                    review_status="accepted",
                )
            ],
            search_phrases=[
                AssetSearchPhrase(
                    phrase="找一张孩子学完马上能看到掌握情况的图",
                    origin="manual",
                    review_status="accepted",
                )
            ],
        )

        rejected_quiz_groups = []
        for index, title in enumerate(
            (
                "学完即练",
                "学练测闭环",
                "配套功能，线上错题自动归纳到错题本",
                "题库支撑",
            )
        ):
            image = _image(title, f"quiz-action-{index}.png")
            group = AssetGroup(
                title=title,
                created_by="designer",
                images=[image],
                concept_links=[
                    AssetConceptLink(
                        concept=instant_quiz,
                        relation_role="expresses",
                        origin="manual",
                        review_status="accepted",
                    )
                ],
            )
            rejected_quiz_groups.append((image, group))

        groups = [
            report_group,
            quiz_report_group,
            *(group for _, group in rejected_quiz_groups),
        ]
        db.add_all([learning_report, instant_quiz, *groups])
        db.flush()
        for group in groups:
            group.primary_image_id = group.images[0].id
        db.commit()

        response = SearchService(db).search(query, 12)

    assert response.search_understanding is not None
    assert (
        response.search_understanding.query_type
        == "exploratory_business_intent_search"
    )
    assert {item.image.id for item in response.results} == {
        report.id,
        quiz_report.id,
    }
    rejected_ids = {image.id for image, _ in rejected_quiz_groups}
    assert rejected_ids.isdisjoint(item.image.id for item in response.results)


def test_phase4_classroom_evidence_query_stays_empty_until_assets_exist(db_factory):
    # D097：证明点素材未制作（二期计划）时，点名该证据的查询必须返回空，
    # 不得用同卖点其他证明点素材补位；素材补齐后自动恢复命中。
    query = "找一张动画精讲的学校落地案例图"
    with db_factory() as db:
        concept = BusinessConcept(
            code="animation_explanation",
            name="动画精讲",
            search_phrases=[
                ConceptSearchPhrase(
                    phrase="动画精讲",
                    origin="manual",
                    review_status="accepted",
                )
            ],
        )
        sibling_groups = []
        for index, (title, phrase) in enumerate(
            (
                ("官方数据规模", "找一张能用海量学习数据证明动画教学有效的图"),
                ("权威背书", "找一张动画精讲获权威认可的图"),
            )
        ):
            image = _image(title, f"animation-sibling-{index}.png")
            sibling_groups.append(
                AssetGroup(
                    title=title,
                    created_by="designer",
                    images=[image],
                    concept_links=[
                        AssetConceptLink(
                            concept=concept,
                            relation_role="expresses",
                            origin="manual",
                            review_status="accepted",
                        )
                    ],
                    search_phrases=[
                        AssetSearchPhrase(
                            phrase=phrase,
                            origin="manual",
                            review_status="accepted",
                        )
                    ],
                )
            )
        db.add_all([concept, *sibling_groups])
        db.flush()
        for group in sibling_groups:
            group.primary_image_id = group.images[0].id
        db.commit()

        empty_response = SearchService(db).search(query, 12)

        school_case = _image("乡村中学课堂案例", "school-case.png")
        school_group = AssetGroup(
            title=school_case.title,
            created_by="designer",
            images=[school_case],
            concept_links=[
                AssetConceptLink(
                    concept=concept,
                    relation_role="expresses",
                    origin="manual",
                    review_status="accepted",
                )
            ],
            search_phrases=[
                AssetSearchPhrase(
                    phrase="找一张动画课在学校课堂真实使用的案例图",
                    origin="manual",
                    review_status="accepted",
                )
            ],
        )
        db.add(school_group)
        db.flush()
        school_group.primary_image_id = school_case.id
        db.commit()

        filled_response = SearchService(db).search(query, 12)

    assert empty_response.results == []
    assert [item.image.id for item in filled_response.results] == [school_case.id]


def test_phase4_explicit_socratic_query_unlocks_method_asset(db_factory):
    query = "通过启发式提问，还原思考过程，帮你从解一题到通一类"
    with db_factory() as db:
        concept = BusinessConcept(
            code="photo_guided_learning",
            name="AI拍题精学",
        )
        socratic = _image("苏格拉底讲解提问", "socratic.png")
        group = AssetGroup(
            title=socratic.title,
            created_by="designer",
            images=[socratic],
            concept_links=[
                AssetConceptLink(
                    concept=concept,
                    relation_role="expresses",
                    origin="manual",
                    review_status="accepted",
                )
            ],
            search_phrases=[
                AssetSearchPhrase(
                    phrase=query,
                    origin="manual",
                    review_status="accepted",
                )
            ],
        )
        db.add(group)
        db.flush()
        group.primary_image_id = socratic.id
        db.commit()

        response = SearchService(db).search(query, 12)

    assert [item.image.id for item in response.results] == [socratic.id]
    assert any(
        "卖点内素材独有话术命中" in reason
        for reason in response.results[0].match_reasons
    )


def test_phase4_trusted_method_predicate_skips_wrong_model(db_factory):
    query = "通过启发式提问，还原思考过程，帮你从解一题到通一类"

    class Provider:
        configured = True

    class WrongStagedAi:
        provider = Provider()
        knowledge = None

        def route_search_system(self, keyword: str):
            raise AssertionError("本地方法谓词已形成可信判断，不应再调用模型")

        def routed_system_codes(self, _routing):
            return ("sync_cultivation",)

        def understand_search_from_route(self, keyword: str, _routing):
            return SearchUnderstanding(
                original_query=keyword,
                normalized_query="万能解法",
                search_intent="错误地将结果词当作主意图",
                query_type="business_intent_search",
                matched_business_concepts=[
                    SearchConceptMatch(
                        concept="万能解法",
                        relation="direct",
                        reason="只依据从解一题到通一类",
                        weight=0.93,
                    )
                ],
                search_strategy="错误模型结果",
            )

    with db_factory() as db:
        photo_guided = BusinessConcept(
            code="photo_guided_learning",
            name="AI拍题精学",
        )
        universal = BusinessConcept(code="universal_method", name="万能解法")
        socratic = _image("苏格拉底讲解提问", "socratic-method.png")
        socratic_group = AssetGroup(
            title=socratic.title,
            created_by="designer",
            images=[socratic],
            concept_links=[
                AssetConceptLink(
                    concept=photo_guided,
                    relation_role="expresses",
                    origin="manual",
                    review_status="accepted",
                )
            ],
            search_phrases=[
                AssetSearchPhrase(
                    phrase=query,
                    origin="manual",
                    review_status="accepted",
                )
            ],
        )
        universal_image = _image("一题多解", "universal-method.png")
        universal_group = AssetGroup(
            title=universal_image.title,
            created_by="designer",
            images=[universal_image],
            concept_links=[
                AssetConceptLink(
                    concept=universal,
                    relation_role="expresses",
                    origin="manual",
                    review_status="accepted",
                )
            ],
            search_phrases=[
                AssetSearchPhrase(
                    phrase=query,
                    origin="manual",
                    review_status="accepted",
                )
            ],
        )
        db.add_all([socratic_group, universal_group])
        db.flush()
        socratic_group.primary_image_id = socratic.id
        universal_group.primary_image_id = universal_image.id
        db.commit()

        response = SearchService(db, ai_service=WrongStagedAi()).search(query, 12)

    assert response.search_understanding is not None
    assert response.search_understanding.normalized_query == "AI拍题精学"
    assert [item.image.id for item in response.results] == [socratic.id]
    assert universal_image.id not in {item.image.id for item in response.results}
    understanding_branch = next(
        item
        for item in response.search_diagnostics.branches
        if item.source == "query_understanding"
    )
    assert understanding_branch.status == "skipped"
    assert understanding_branch.detail == "本地高置信业务证据已满足，无需模型补充"


def test_phase4_objectless_photo_explain_query_returns_rapid_assets_not_global(
    db_factory,
):
    # 真实库现状：拍题精学暂无素材，极速预习/复习各有一张人工 accepted 主图。
    # “拍一下，AI马上给你讲解”必须返回这两张，而不是空结果或全库兜底。
    query = "拍一下，AI马上给你讲解"
    with db_factory() as db:
        photo_guided = BusinessConcept(
            code="photo_guided_learning",
            name="AI拍题精学",
        )
        rapid = BusinessConcept(code="rapid_preview_review", name="极速预习复习")
        ai_tutor = BusinessConcept(code="ai_tutor_qa", name="AI私教答疑")

        expected_ids = []
        for title, file_name in (
            ("极速预习", "rapid-preview.png"),
            ("极速复习", "rapid-review.png"),
        ):
            image = _image(title, file_name)
            group = AssetGroup(
                title=image.title,
                created_by="designer",
                images=[image],
                concept_links=[
                    AssetConceptLink(
                        concept=rapid,
                        relation_role="expresses",
                        origin="manual",
                        review_status="accepted",
                    )
                ],
            )
            db.add(group)
            db.flush()
            group.primary_image_id = image.id
            expected_ids.append(image.id)

        tutor = _image("ai私教", "ai-tutor.png")
        tutor_group = AssetGroup(
            title=tutor.title,
            created_by="designer",
            images=[tutor],
            concept_links=[
                AssetConceptLink(
                    concept=ai_tutor,
                    relation_role="expresses",
                    origin="manual",
                    review_status="accepted",
                )
            ],
        )
        unrelated = _image(query, "title-only.png")
        db.add_all([photo_guided, tutor_group, unrelated])
        db.flush()
        tutor_group.primary_image_id = tutor.id
        db.commit()

        response = SearchService(db).search(query, 12)

    assert response.search_understanding is not None
    assert (
        response.search_understanding.query_type
        == "exploratory_business_intent_search"
    )
    result_ids = {item.image.id for item in response.results}
    assert result_ids == set(expected_ids)
    assert tutor.id not in result_ids
    assert unrelated.id not in result_ids


def test_phase4_exploratory_route_excludes_pending_links_even_with_model_related_weights(
    db_factory,
):
    # D080 回归真实线上案例：模型把探索候选标为 related/低权重时，结果仍必须
    # 封闭在候选卖点的人工 accepted 关系内。“考前突击”只有一条 AI 待审核的
    # “表达极速预习复习”建议，未经人工确认不能算数，不得进入探索结果。
    query = "拍一下，AI马上给你讲解"

    class Provider:
        configured = True

    class ExploratoryAi:
        provider = Provider()
        knowledge = None

        def understand_search(self, keyword: str):
            return SearchUnderstanding(
                original_query=keyword,
                normalized_query="拍照后由 AI 立即讲解或点拨",
                search_intent="你可能在找：AI拍题精学、极速预习复习",
                query_type="exploratory_business_intent_search",
                matched_business_concepts=[
                    SearchConceptMatch(
                        concept="同步自学体系 > AI拍题精学",
                        relation="related",
                        reason="可能是拍题讲解，但缺少明确对象",
                        weight=0.7,
                    ),
                    SearchConceptMatch(
                        concept="同步校内体系 > 极速预习复习",
                        relation="related",
                        reason="也可能是拍课本快速梳理",
                        weight=0.66,
                    ),
                ],
                search_strategy="共享入口词命中多个卖点方向，合并展示供二次筛选",
            )

    with db_factory() as db:
        photo_guided = BusinessConcept(
            code="photo_guided_learning",
            name="AI拍题精学",
        )
        rapid = BusinessConcept(code="rapid_preview_review", name="极速预习复习")
        excellence = BusinessConcept(code="focused_excellence", name="专项培优")

        preview = _image("极速预习", "rapid-preview.png")
        preview_group = AssetGroup(
            title=preview.title,
            created_by="designer",
            images=[preview],
            concept_links=[
                AssetConceptLink(
                    concept=rapid,
                    relation_role="expresses",
                    origin="manual",
                    review_status="accepted",
                )
            ],
        )
        exam_rush = _image("考前突击", "exam-rush.png")
        exam_rush_group = AssetGroup(
            title=exam_rush.title,
            created_by="designer",
            images=[exam_rush],
            concept_links=[
                AssetConceptLink(
                    concept=excellence,
                    relation_role="expresses",
                    origin="manual",
                    review_status="accepted",
                ),
                AssetConceptLink(
                    concept=rapid,
                    relation_role="expresses",
                    origin="ai",
                    review_status="pending",
                ),
            ],
        )
        unrelated = _image(query, "title-only.png")
        db.add_all([photo_guided, preview_group, exam_rush_group, unrelated])
        db.flush()
        preview_group.primary_image_id = preview.id
        exam_rush_group.primary_image_id = exam_rush.id
        db.commit()

        response = SearchService(db, ai_service=ExploratoryAi()).search(query, 12)

    assert response.search_understanding is not None
    assert (
        response.search_understanding.query_type
        == "exploratory_business_intent_search"
    )
    result_ids = [item.image.id for item in response.results]
    assert result_ids == [preview.id]
    assert exam_rush.id not in result_ids
    assert unrelated.id not in result_ids


def test_phase4_concept_route_uses_asset_phrase_to_choose_within_selling_point(
    db_factory,
):
    query = "和学校课程一致"
    with db_factory() as db:
        concept = BusinessConcept(
            code="school_sync",
            name="同步校内",
            search_phrases=[
                ConceptSearchPhrase(
                    phrase="学校课程一致",
                    origin="manual",
                    review_status="accepted",
                )
            ],
        )
        exact = _image("章节对照素材", "exact.png")
        exact_group = AssetGroup(
            title=exact.title,
            created_by="designer",
            images=[exact],
            concept_links=[
                AssetConceptLink(
                    concept=concept,
                    relation_role="supports",
                    origin="manual",
                    review_status="accepted",
                )
            ],
            search_phrases=[
                AssetSearchPhrase(
                    phrase=query,
                    origin="manual",
                    review_status="accepted",
                )
            ],
        )
        generic = _image("同步校内通用素材", "generic.png")
        generic_group = AssetGroup(
            title=generic.title,
            created_by="designer",
            images=[generic],
            concept_links=[
                AssetConceptLink(
                    concept=concept,
                    relation_role="expresses",
                    origin="manual",
                    review_status="accepted",
                )
            ],
        )
        title_only = _image(query, "title-only.png")
        db.add_all([concept, exact_group, generic_group, title_only])
        db.flush()
        exact_group.primary_image_id = exact.id
        generic_group.primary_image_id = generic.id
        db.commit()

        response = SearchService(db).search(query, 12)

    assert [item.image.id for item in response.results] == [exact.id, generic.id]
    assert any(
        "卖点内素材独有话术命中" in reason
        for reason in response.results[0].match_reasons
    )
    assert title_only.id not in {item.image.id for item in response.results}


def test_phase4_asset_phrase_priority_beats_higher_generic_source_score(db_factory):
    query = "自动归类个人错题本"
    with db_factory() as db:
        concept = BusinessConcept(
            code="ai_error_book",
            name="AI错题本",
            search_phrases=[
                ConceptSearchPhrase(
                    phrase="自动归类个人错题本",
                    origin="manual",
                    review_status="accepted",
                )
            ],
        )
        exact = _image("线上错题归档", "exact-error-book.png")
        exact_group = AssetGroup(
            title=exact.title,
            created_by="designer",
            images=[exact],
            concept_links=[
                AssetConceptLink(
                    concept=concept,
                    relation_role="expresses",
                    origin="manual",
                    review_status="accepted",
                )
            ],
            search_phrases=[
                AssetSearchPhrase(
                    phrase=query,
                    origin="manual",
                    review_status="accepted",
                )
            ],
        )
        generic = _image("AI错题本通用流程", "generic-error-book.png")
        generic_group = AssetGroup(
            title=generic.title,
            created_by="designer",
            images=[generic],
            concept_links=[
                AssetConceptLink(
                    concept=concept,
                    relation_role="expresses",
                    origin="manual",
                    review_status="accepted",
                )
            ],
        )
        db.add_all([concept, exact_group, generic_group])
        db.flush()
        exact_group.primary_image_id = exact.id
        generic_group.primary_image_id = generic.id
        db.commit()

        service = SearchService(db)
        generic_hit = SearchHit(
            image=generic,
            score=1.0,
            reasons=("通用外部召回",),
        )
        exact_hit = SearchHit(
            image=exact,
            score=0.65,
            reasons=("卖点内候选",),
        )
        match = service.concept_recall.match(query)[0]
        understanding = _understanding(query).model_copy(
            update={
                "matched_business_concepts": [
                    SearchConceptMatch(
                        concept="AI错题本",
                        relation="direct",
                        reason="错题自动归类",
                        weight=0.98,
                    )
                ]
            }
        )
        routed = service.ranking.route_confirmed_concepts(
            [generic_hit, exact_hit],
            [match],
            keyword=query,
            understanding=understanding,
        )

    assert [item.image.id for item in routed.hits] == [exact.id, generic.id]


def test_phase4_asset_phrases_filter_support_proof_images_with_direct_assets(
    db_factory,
):
    query = "动态组建一个与你水平相匹配的虚拟班级，安排个性化的学习节奏与内容"

    class Provider:
        configured = True

    class MustNotCallAi:
        provider = Provider()
        knowledge = None

        def understand_search(self, keyword: str):
            raise AssertionError(f"可信本地话术不应调用外部模型：{keyword}")

    with db_factory() as db:
        concept = BusinessConcept(code="ai_learning_plan", name="AI定制学习方案")

        direct = _image("ai定制", "ai-plan.png")
        direct_group = AssetGroup(
            title=direct.title,
            created_by="designer",
            images=[direct],
            concept_links=[
                AssetConceptLink(
                    concept=concept,
                    relation_role="expresses",
                    origin="manual",
                    review_status="accepted",
                )
            ],
            search_phrases=[
                AssetSearchPhrase(
                    phrase="找一张突出AI定制班安排专属学习计划的素材",
                    origin="manual",
                    review_status="accepted",
                )
            ],
        )
        planning = _image("ai定制规划", "ai-plan-flow.png")
        planning_group = AssetGroup(
            title=planning.title,
            created_by="designer",
            images=[planning],
            concept_links=[
                AssetConceptLink(
                    concept=concept,
                    relation_role="expresses",
                    origin="manual",
                    review_status="accepted",
                )
            ],
            search_phrases=[
                AssetSearchPhrase(
                    phrase="根据年级和水平定制每天学习计划",
                    origin="manual",
                    review_status="accepted",
                )
            ],
        )
        founder_assets = []
        for title, file_name, phrase in (
            ("创始人理念", "founder-idea.png", "创始人在大会上讲新课标新考法预测"),
            ("创始人宣讲", "founder-talk.png", "考试改革趋势与思维过程评价宣讲"),
        ):
            image = _image(title, file_name)
            group = AssetGroup(
                title=title,
                created_by="designer",
                images=[image],
                concept_links=[
                    AssetConceptLink(
                        concept=concept,
                        relation_role="supports",
                        origin="manual",
                        review_status="accepted",
                    )
                ],
                search_phrases=[
                    AssetSearchPhrase(
                        phrase=phrase,
                        origin="manual",
                        review_status="accepted",
                    )
                ],
            )
            founder_assets.append((image, group))
        groups = [direct_group, planning_group, *(group for _, group in founder_assets)]
        db.add_all([concept, *groups])
        db.flush()
        for group in groups:
            group.primary_image_id = group.images[0].id
        db.commit()

        response = SearchService(db, ai_service=MustNotCallAi()).search(query, 12)

    result_ids = [item.image.id for item in response.results]
    assert set(result_ids) == {direct.id, planning.id}
    assert all(image.id not in result_ids for image, _ in founder_assets)
    assert all(
        "进入卖点主通道：主要表达" in item.match_reasons
        for item in response.results
    )


def test_phase4_explicit_proof_query_keeps_matching_support_asset_only(db_factory):
    query = "找一张创始人宣讲AI定制学习理念的图"

    class Provider:
        configured = True

    class PlanningAi:
        provider = Provider()
        knowledge = None

        def understand_search(self, keyword: str):
            return SearchUnderstanding(
                original_query=keyword,
                normalized_query="AI定制学习方案",
                search_intent="用创始人宣讲素材支撑 AI 个性化学习规划",
                query_type="business_intent_search",
                matched_business_concepts=[
                    SearchConceptMatch(
                        concept="AI定制学习方案",
                        relation="direct",
                        reason="明确要求 AI 定制学习理念",
                        weight=0.96,
                    )
                ],
            )

    with db_factory() as db:
        concept = BusinessConcept(code="ai_learning_plan", name="AI定制学习方案")
        direct = _image("ai定制", "ai-plan.png")
        direct_group = AssetGroup(
            title=direct.title,
            created_by="designer",
            images=[direct],
            concept_links=[
                AssetConceptLink(
                    concept=concept,
                    relation_role="expresses",
                    origin="manual",
                    review_status="accepted",
                )
            ],
        )
        founder = _image("创始人宣讲", "founder-talk.png")
        founder_group = AssetGroup(
            title=founder.title,
            created_by="designer",
            images=[founder],
            concept_links=[
                AssetConceptLink(
                    concept=concept,
                    relation_role="supports",
                    origin="manual",
                    review_status="accepted",
                )
            ],
            search_phrases=[
                AssetSearchPhrase(
                    phrase="考试改革趋势与思维过程评价宣讲",
                    origin="manual",
                    review_status="accepted",
                )
            ],
        )
        db.add_all([concept, direct_group, founder_group])
        db.flush()
        direct_group.primary_image_id = direct.id
        founder_group.primary_image_id = founder.id
        db.commit()

        response = SearchService(db, ai_service=PlanningAi()).search(query, 12)

    result_ids = [item.image.id for item in response.results]
    assert result_ids == [founder.id]
    assert direct.id not in result_ids
    founder_result = response.results[0]
    assert any(
        "图片标题或画面内容辅助匹配：创始人宣讲" in reason
        for reason in founder_result.match_reasons
    )


def test_phase4_animation_course_quality_query_cannot_leak_global_results(
    db_factory,
):
    class Provider:
        configured = True

    class ProgressiveAi:
        provider = Provider()
        knowledge = None

        def understand_search(self, keyword: str):
            return SearchUnderstanding(
                original_query=keyword,
                normalized_query="动画精讲",
                search_intent="体现动画课程质量",
                query_type="business_intent_search",
                matched_business_concepts=[
                    SearchConceptMatch(
                        concept="动画精讲",
                        relation="direct",
                        reason="渐进式 Skill 命中同步校内体系内动画精讲",
                        weight=0.96,
                    )
                ],
                search_strategy="只在已审核动画精讲素材关系内选图",
            )

    query = "体现动画课很好"
    with db_factory() as db:
        animation = BusinessConcept(
            code="animation_explanation",
            name="动画精讲",
            search_phrases=[
                ConceptSearchPhrase(
                    phrase="几分钟就能讲明白一个知识点",
                    phrase_type="business_language",
                    origin="source_document",
                    review_status="accepted",
                    weight=1.0,
                )
            ],
        )
        certificate = _image("官方奖项认可", "certificate.png")
        certificate_group = AssetGroup(
            title=certificate.title,
            created_by="designer",
            images=[certificate],
            concept_links=[
                AssetConceptLink(
                    concept=animation,
                    relation_role="expresses",
                    origin="manual",
                    review_status="accepted",
                )
            ],
        )
        visual = _image("题型可视化", "animation-visual.png")
        visual_group = AssetGroup(
            title=visual.title,
            created_by="designer",
            images=[visual],
            concept_links=[
                AssetConceptLink(
                    concept=animation,
                    relation_role="expresses",
                    origin="manual",
                    review_status="accepted",
                )
            ],
        )
        pending = _image(f"{query}但其实是衔接课", "stage-transition.png")
        pending_group = AssetGroup(
            title="衔接课",
            created_by="designer",
            images=[pending],
            concept_links=[
                AssetConceptLink(
                    concept=animation,
                    relation_role="supports",
                    origin="ai",
                    review_status="pending",
                )
            ],
        )
        unrelated = _image(query, "global-title-match.png")
        db.add_all(
            [
                animation,
                certificate_group,
                visual_group,
                pending_group,
                unrelated,
            ]
        )
        db.flush()
        certificate_group.primary_image_id = certificate.id
        visual_group.primary_image_id = visual.id
        pending_group.primary_image_id = pending.id
        db.commit()

        response = SearchService(db, ai_service=ProgressiveAi()).search(query, 12)

    assert response.search_understanding is not None
    assert response.search_understanding.query_type == "business_intent_search"
    assert [item.image.id for item in response.results] == [certificate.id, visual.id]
    assert all(
        item.matched_query_concepts[0].concept_name == "动画精讲"
        and item.matched_query_concepts[0].relation_role == "expresses"
        for item in response.results
    )
    assert pending.id not in {item.image.id for item in response.results}
    assert unrelated.id not in {item.image.id for item in response.results}
    understanding_branch = next(
        item
        for item in response.search_diagnostics.branches
        if item.source == "query_understanding"
    )
    assert understanding_branch.status == "skipped"
    assert understanding_branch.detail == "本地高置信业务证据已满足，无需模型补充"


def test_phase4_short_animation_micro_lesson_query_only_returns_matching_detail(
    db_factory,
):
    query = "找那种几分钟就能讲明白一个知识点的图"
    with db_factory() as db:
        animation = BusinessConcept(
            code="animation_explanation",
            name="动画精讲",
        )
        short_lesson = _image("5-8分钟讲透知识点，学完就练", "short-lesson.png")
        short_group = AssetGroup(
            title=short_lesson.title,
            created_by="designer",
            images=[short_lesson],
            search_phrases=[
                AssetSearchPhrase(
                    phrase="有没有5到8分钟动画微课讲知识点的图",
                    origin="manual",
                    review_status="accepted",
                    weight=1.0,
                )
            ],
            concept_links=[
                AssetConceptLink(
                    concept=animation,
                    relation_role="expresses",
                    origin="manual",
                    review_status="accepted",
                )
            ],
        )
        generic_visual = _image("抽象题目变为有趣动画", "generic-visual.png")
        generic_group = AssetGroup(
            title=generic_visual.title,
            created_by="designer",
            images=[generic_visual],
            concept_links=[
                AssetConceptLink(
                    concept=animation,
                    relation_role="expresses",
                    origin="manual",
                    review_status="accepted",
                )
            ],
        )
        authority = _image("权威背书", "authority.png")
        authority_group = AssetGroup(
            title=authority.title,
            created_by="designer",
            images=[authority],
            concept_links=[
                AssetConceptLink(
                    concept=animation,
                    relation_role="expresses",
                    origin="manual",
                    review_status="accepted",
                )
            ],
        )
        db.add_all([animation, short_group, generic_group, authority_group])
        db.flush()
        short_group.primary_image_id = short_lesson.id
        generic_group.primary_image_id = generic_visual.id
        authority_group.primary_image_id = authority.id
        db.commit()

        response = SearchService(db).search(query, 12)

    assert [item.image.id for item in response.results] == [short_lesson.id]
    assert response.search_understanding is not None
    assert [
        item.code for item in response.search_understanding.matched_proof_points
    ] == ["pp_animation_pedagogy_design"]
    assert any(
        "证明点匹配：官方产品定位与教研方法论" in reason
        for reason in response.results[0].match_reasons
    )


def test_phase4_unseen_proof_paraphrase_uses_scoped_completion_and_filters_siblings(
    db_factory,
):
    query = "要动画讲解的，别拖太久，每回只消化一个小点"

    class Provider:
        configured = True

    class ScopedProofAi:
        provider = Provider()
        knowledge = None
        proof_calls = 0

        def route_search_system(self, _keyword: str):
            raise AssertionError("可信卖点已确认，证明点补全不应重复调用体系路由")

        def understand_search_from_route(self, keyword: str, routing):
            self.proof_calls += 1
            assert [item.code for item in routing.candidate_systems] == [
                "sync_school"
            ]
            return SearchUnderstanding(
                original_query=keyword,
                normalized_query="动画精讲",
                search_intent="短时、单点讲透",
                query_type="business_intent_search",
                matched_business_concepts=[
                    SearchConceptMatch(
                        concept="animation_explanation",
                        relation="direct",
                        reason="动画讲解",
                        weight=0.98,
                    )
                ],
                matched_proof_points=[
                    SearchProofPointMatch(
                        code="pp_animation_pedagogy_design",
                        concept_code="animation_explanation",
                        name="官方产品定位与教研方法论",
                        reason="别拖太久、每回只消化一个小点",
                        weight=0.96,
                        evidence_terms=["5-8 分钟动画微课"],
                    )
                ],
            )

    ai = ScopedProofAi()
    with db_factory() as db:
        animation = BusinessConcept(
            code="animation_explanation",
            name="动画精讲",
        )
        short_lesson = _image("5-8分钟讲透知识点，学完就练", "short-new.png")
        generic = _image("抽象题目变为有趣动画", "generic-new.png")
        groups = []
        for image, phrases in (
            (short_lesson, ["有没有5到8分钟动画微课讲知识点的图"]),
            (generic, []),
        ):
            group = AssetGroup(
                title=image.title,
                created_by="designer",
                images=[image],
                search_phrases=[
                    AssetSearchPhrase(
                        phrase=phrase,
                        origin="manual",
                        review_status="accepted",
                        weight=1.0,
                    )
                    for phrase in phrases
                ],
                concept_links=[
                    AssetConceptLink(
                        concept=animation,
                        relation_role="expresses",
                        origin="manual",
                        review_status="accepted",
                    )
                ],
            )
            groups.append(group)
        db.add_all([animation, *groups])
        db.flush()
        for group in groups:
            group.primary_image_id = group.images[0].id
        db.commit()

        response = SearchService(
            db,
            ai_service=ai,
            understanding_timeout_seconds=1,
        ).search(query, 12)

    assert ai.proof_calls == 1
    assert [item.image.id for item in response.results] == [short_lesson.id]
    assert response.search_understanding is not None
    assert [
        item.code for item in response.search_understanding.matched_proof_points
    ] == ["pp_animation_pedagogy_design"]
    branch = next(
        item
        for item in response.search_diagnostics.branches
        if item.source == "query_understanding"
    )
    assert branch.status == "ok"
    assert branch.detail == "已确认卖点内证明点补全"


def test_phase4_photo_guided_flow_does_not_route_to_fallback_animation(
    db_factory,
):
    query = "孩子拍一拍不会的题，AI先问步骤、讲思路，不懂再推对应知识点动画课，学会为止"

    class Provider:
        configured = True

    class MustNotCallAi:
        provider = Provider()
        knowledge = None

        def understand_search(self, keyword: str):
            raise AssertionError(f"可信拍题流程不应调用外部模型：{keyword}")

    with db_factory() as db:
        photo_guided = BusinessConcept(
            code="photo_guided_learning",
            name="AI拍题精学",
        )
        animation = BusinessConcept(
            code="animation_explanation",
            name="动画精讲",
        )

        photo = _image("拍题精学", "photo-guided.png")
        photo_group = AssetGroup(
            title=photo.title,
            created_by="designer",
            images=[photo],
            concept_links=[
                AssetConceptLink(
                    concept=photo_guided,
                    relation_role="expresses",
                    origin="manual",
                    review_status="accepted",
                )
            ],
            search_phrases=[
                AssetSearchPhrase(
                    phrase="不会做题拍一下就能讲思路和步骤",
                    origin="manual",
                    review_status="accepted",
                )
            ],
        )
        socratic = _image("苏格拉底讲解提问", "socratic.png")
        socratic_group = AssetGroup(
            title=socratic.title,
            created_by="designer",
            images=[socratic],
            concept_links=[
                AssetConceptLink(
                    concept=photo_guided,
                    relation_role="expresses",
                    origin="manual",
                    review_status="accepted",
                )
            ],
            search_phrases=[
                AssetSearchPhrase(
                    phrase="不会题拍一下后AI先追问思路、不直接给答案",
                    origin="manual",
                    review_status="accepted",
                )
            ],
        )
        animation_image = _image("动画讲解", "animation.png")
        animation_group = AssetGroup(
            title=animation_image.title,
            created_by="designer",
            images=[animation_image],
            concept_links=[
                AssetConceptLink(
                    concept=animation,
                    relation_role="expresses",
                    origin="manual",
                    review_status="accepted",
                )
            ],
            search_phrases=[
                AssetSearchPhrase(
                    phrase="用动画把抽象知识点讲透",
                    origin="manual",
                    review_status="accepted",
                )
            ],
        )
        groups = [photo_group, socratic_group, animation_group]
        db.add_all([photo_guided, animation, *groups])
        db.flush()
        for group in groups:
            group.primary_image_id = group.images[0].id
        db.commit()

        response = SearchService(db, ai_service=MustNotCallAi()).search(query, 12)

    assert response.search_understanding is not None
    assert response.search_understanding.normalized_query == "AI拍题精学"
    result_ids = {item.image.id for item in response.results}
    assert result_ids == {socratic.id}
    assert photo.id not in result_ids
    assert animation_image.id not in result_ids


def test_phase4_proof_point_filters_sibling_assets_but_generic_selling_point_does_not(
    db_factory,
):
    with db_factory() as db:
        concept = BusinessConcept(code="ai_error_book", name="AI错题本")
        archive = _image("线上错题自动归纳到错题本", "error-archive.png")
        upload = _image("拍照上传错题", "error-upload.png")
        variant = _image("错题同类题精准强化", "error-variant.png")
        groups = []
        for image, phrase in (
            (archive, "做错的题自动收集归类到错题本"),
            (upload, "拍照上传错题"),
            (variant, "从个人错题推荐同类变式题"),
        ):
            group = AssetGroup(
                title=image.title,
                created_by="designer",
                images=[image],
                concept_links=[
                    AssetConceptLink(
                        concept=concept,
                        relation_role="expresses",
                        origin="manual",
                        review_status="accepted",
                    )
                ],
                search_phrases=[
                    AssetSearchPhrase(
                        phrase=phrase,
                        origin="manual",
                        review_status="accepted",
                    )
                ],
            )
            groups.append(group)
        db.add_all([concept, *groups])
        db.flush()
        for group in groups:
            group.primary_image_id = group.images[0].id
        db.commit()

        specific = SearchService(db).search(
            "做错的题自动收集归类到错题本", 12
        )
        generic = SearchService(db).search("AI错题本", 12)

    assert specific.search_understanding is not None
    assert [
        item.code for item in specific.search_understanding.matched_proof_points
    ] == ["pp_selfstudy_error_photo_capture"]
    assert {item.image.id for item in specific.results} == {archive.id, upload.id}
    assert variant.id not in {item.image.id for item in specific.results}
    assert any(
        reason.startswith("证明点匹配：线下错题拍照上传与归档")
        for item in specific.results
        for reason in item.match_reasons
    )
    assert generic.search_understanding is not None
    assert generic.search_understanding.matched_proof_points == []
    assert {item.image.id for item in generic.results} == {
        archive.id,
        upload.id,
        variant.id,
    }


@pytest.mark.parametrize(
    "query",
    [
        "量身打造一对一AI私教，24小时答疑解惑，精准定位知识薄弱点",
    ],
)
def test_phase4_ai_tutor_queries_only_return_reviewed_ai_tutor_assets(
    db_factory,
    monkeypatch,
    query,
):
    class Provider:
        configured = True

    class ProgressiveAi:
        provider = Provider()
        knowledge = None

        def understand_search(self, keyword: str):
            return SearchUnderstanding(
                original_query=keyword,
                normalized_query="AI私教答疑",
                search_intent="学习过程中随时获得 AI 答疑",
                query_type="business_intent_search",
                matched_business_concepts=[
                    SearchConceptMatch(
                        concept="AI私教答疑",
                        relation="direct",
                        reason="渐进式 Skill 命中同步自学体系内 AI 私教答疑",
                        weight=0.97,
                    )
                ],
                search_strategy="只在已审核 AI 私教素材关系内选图",
            )

    with db_factory() as db:
        ai_tutor = BusinessConcept(code="ai_tutor_qa", name="AI私教答疑")
        animation = BusinessConcept(
            code="animation_explanation",
            name="动画精讲",
        )
        rapid = BusinessConcept(
            code="rapid_preview_review",
            name="极速预习复习",
        )

        tutor = _image("ai私教", "ai-tutor.png")
        tutor_group = AssetGroup(
            title=tutor.title,
            created_by="designer",
            images=[tutor],
            concept_links=[
                AssetConceptLink(
                    concept=ai_tutor,
                    relation_role="expresses",
                    origin="manual",
                    review_status="accepted",
                )
            ],
        )
        visual = _image("题型可视化", "animation-visual.png")
        visual_group = AssetGroup(
            title=visual.title,
            created_by="designer",
            images=[visual],
            concept_links=[
                AssetConceptLink(
                    concept=animation,
                    relation_role="expresses",
                    origin="manual",
                    review_status="accepted",
                ),
                AssetConceptLink(
                    concept=ai_tutor,
                    relation_role="supports",
                    origin="ai",
                    review_status="pending",
                ),
            ],
        )
        preview = _image("极速预习", "rapid-preview.png")
        preview_group = AssetGroup(
            title=preview.title,
            created_by="designer",
            images=[preview],
            concept_links=[
                AssetConceptLink(
                    concept=rapid,
                    relation_role="expresses",
                    origin="manual",
                    review_status="accepted",
                )
            ],
        )
        review = _image("极速复习", "rapid-review.png")
        review_group = AssetGroup(
            title=review.title,
            created_by="designer",
            images=[review],
            concept_links=[
                AssetConceptLink(
                    concept=rapid,
                    relation_role="expresses",
                    origin="manual",
                    review_status="accepted",
                )
            ],
        )
        db.add_all(
            [
                ai_tutor,
                animation,
                rapid,
                tutor_group,
                visual_group,
                preview_group,
                review_group,
            ]
        )
        db.flush()
        tutor_group.primary_image_id = tutor.id
        visual_group.primary_image_id = visual.id
        preview_group.primary_image_id = preview.id
        review_group.primary_image_id = review.id
        db.commit()

        service = SearchService(
            db,
            search_backend="meilisearch",
            meilisearch_url="http://search.test",
            ai_service=ProgressiveAi(),
        )

        def meili_must_not_run(_keyword, _limit):
            raise AssertionError("本地可信卖点已满足时不应调用 Meilisearch")

        monkeypatch.setattr(
            service.meilisearch_recall,
            "recall_candidates",
            meili_must_not_run,
        )
        response = service.search(query, 12)

    assert response.search_understanding is not None
    assert response.search_understanding.query_type == "business_intent_search"
    assert response.search_understanding.normalized_query == "AI私教答疑"
    assert [item.image.id for item in response.results] == [tutor.id]
    assert response.results[0].matched_query_concepts[0].concept_name == "AI私教答疑"
    assert response.results[0].matched_query_concepts[0].relation_role == "expresses"
    assert visual.id not in {item.image.id for item in response.results}
    assert preview.id not in {item.image.id for item in response.results}
    assert review.id not in {item.image.id for item in response.results}
    understanding_branch = next(
        item
        for item in response.search_diagnostics.branches
        if item.source == "query_understanding"
    )
    assert understanding_branch.status == "skipped"
    assert understanding_branch.detail == "本地高置信业务证据已满足，无需模型补充"
    meili_branch = next(
        item
        for item in response.search_diagnostics.branches
        if item.source == "meilisearch"
    )
    assert meili_branch.status == "skipped"
    assert meili_branch.detail == "本地高置信业务概念已满足"


def test_phase4_heuristic_questioning_routes_to_photo_guided_and_exposes_asset_gap(
    db_factory,
):
    # D078：“启发式提问还原思考过程”是拍题精学的方法论话术（覆盖 D072 旧归属）。
    # 没有人工 accepted 拍题精学素材时必须返回空，不得回退 AI 私教素材补位。
    query = "通过启发式提问，还原思考过程，帮你从‘解一题’到‘通一类’"
    with db_factory() as db:
        ai_tutor = BusinessConcept(code="ai_tutor_qa", name="AI私教答疑")
        photo_guided = BusinessConcept(
            code="photo_guided_learning",
            name="AI拍题精学",
        )
        tutor = _image("ai私教", "ai-tutor.png")
        tutor_group = AssetGroup(
            title=tutor.title,
            created_by="designer",
            images=[tutor],
            concept_links=[
                AssetConceptLink(
                    concept=ai_tutor,
                    relation_role="expresses",
                    origin="manual",
                    review_status="accepted",
                )
            ],
        )
        db.add_all([ai_tutor, photo_guided, tutor_group])
        db.flush()
        tutor_group.primary_image_id = tutor.id
        db.commit()

        response = SearchService(db).search(query, 12)

    assert response.search_understanding is not None
    assert response.search_understanding.query_type == "business_intent_search"
    assert response.search_understanding.normalized_query == "AI拍题精学"
    assert [
        item.concept.rsplit(">", 1)[-1].strip()
        for item in response.search_understanding.matched_business_concepts
    ] == ["AI拍题精学"]
    assert response.results == []


def test_phase4_trusted_small_concept_route_skips_optional_reranker(db_factory):
    class RerankerMustNotRun:
        configured = True

        def rerank(self, *, query: str, documents: list[str], top_n: int):
            raise AssertionError("高置信卖点只有两个候选时不应调用 Reranker")

    with db_factory() as db:
        concept = BusinessConcept(code="ai_tutor_qa", name="AI私教答疑")
        groups = []
        images = []
        for index in range(2):
            image = _image(f"AI私教素材{index + 1}", f"ai-tutor-{index + 1}.png")
            group = AssetGroup(
                title=image.title,
                created_by="designer",
                images=[image],
                concept_links=[
                    AssetConceptLink(
                        concept=concept,
                        relation_role="expresses",
                        origin="manual",
                        review_status="accepted",
                    )
                ],
            )
            groups.append(group)
            images.append(image)
        db.add_all([concept, *groups])
        db.flush()
        for group, image in zip(groups, images):
            group.primary_image_id = image.id
        db.commit()

        response = SearchService(db, reranker=RerankerMustNotRun()).search(
            "AI私教",
            12,
        )

    reranker_branch = next(
        item
        for item in response.search_diagnostics.branches
        if item.source == "reranker"
    )
    assert len(response.results) == 2
    assert response.fallback is False
    assert reranker_branch.status == "skipped"
    assert reranker_branch.detail == "高置信业务主通道候选较少，无需重排"


def test_phase4_optional_timeout_does_not_warn_for_complete_trusted_route(db_factory):
    class SlowReranker:
        configured = True

        def rerank(self, *, query: str, documents: list[str], top_n: int):
            time.sleep(0.08)
            return []

    with db_factory() as db:
        concept = BusinessConcept(code="ai_tutor_qa", name="AI私教答疑")
        groups = []
        images = []
        for index in range(3):
            image = _image(f"AI私教素材{index + 1}", f"slow-ai-tutor-{index + 1}.png")
            group = AssetGroup(
                title=image.title,
                created_by="designer",
                images=[image],
                concept_links=[
                    AssetConceptLink(
                        concept=concept,
                        relation_role="expresses",
                        origin="manual",
                        review_status="accepted",
                    )
                ],
            )
            groups.append(group)
            images.append(image)
        db.add_all([concept, *groups])
        db.flush()
        for group, image in zip(groups, images):
            group.primary_image_id = image.id
        db.commit()

        response = SearchService(
            db,
            reranker=SlowReranker(),
            reranker_timeout_seconds=0.01,
            total_timeout_seconds=0.2,
        ).search("AI私教", 12)

    reranker_branch = next(
        item
        for item in response.search_diagnostics.branches
        if item.source == "reranker"
    )
    assert len(response.results) == 3
    assert response.fallback is False
    assert response.fallback_reason is None
    assert response.search_diagnostics.timed_out is True
    assert reranker_branch.status == "timed_out"


def test_phase4_reranker_skips_when_remaining_budget_cannot_cover_call():
    class RerankerMustNotRun:
        configured = True

        def rerank(self, *, query: str, documents: list[str], top_n: int):
            raise AssertionError("剩余预算不足时不应启动注定超时的 Reranker")

    coordinator = SearchRerankCoordinator(
        SearchRankingService(RerankerMustNotRun(), 20),
        total_timeout_seconds=0.5,
        reranker_timeout_seconds=0.3,
    )
    hits = [
        SearchHit(_image("候选一", "candidate-1.png")),
        SearchHit(_image("候选二", "candidate-2.png")),
    ]

    returned, diagnostic, used, total_timed_out = asyncio.run(
        coordinator.rerank(
            "模糊画面查询",
            hits,
            search_started=time.monotonic() - 0.3,
        )
    )

    assert returned == hits
    assert diagnostic.status == "skipped"
    assert diagnostic.detail == "剩余总预算不足，跳过重排"
    assert used is False
    assert total_timed_out is False


def test_phase4_reranker_budget_starts_after_query_understanding(db_factory):
    class Provider:
        configured = True

    class SlowLegacyAi:
        provider = Provider()
        knowledge = None

        def understand_search(self, keyword: str):
            time.sleep(0.08)
            return _understanding(keyword)

    class CountingReranker:
        configured = True

        def __init__(self):
            self.calls = 0

        def rerank(self, *, query: str, documents: list[str], top_n: int):
            self.calls += 1
            return [
                RerankResult(index=index, score=0.9 - index * 0.1)
                for index in range(min(top_n, len(documents)))
            ]

    reranker = CountingReranker()
    with db_factory() as db:
        images = [
            _image(
                f"同一个模糊画面关键词候选{index + 1}",
                f"candidate-{index}.png",
            )
            for index in range(3)
        ]
        db.add_all(images)
        db.commit()
        response = SearchService(
            db,
            ai_service=SlowLegacyAi(),
            reranker=reranker,
            understanding_timeout_seconds=0.2,
            total_timeout_seconds=0.05,
            reranker_timeout_seconds=0.03,
        ).search("同一个模糊画面关键词", 12)

    assert reranker.calls == 1
    reranker_branch = next(
        item
        for item in response.search_diagnostics.branches
        if item.source == "reranker"
    )
    assert reranker_branch.status == "ok"


def test_phase4_global_recall_remains_when_no_selling_point_is_understood(db_factory):
    with db_factory() as db:
        image = _image("蓝色竖版学习周报", "fallback.png")
        db.add(image)
        db.commit()

        response = SearchService(db).search("蓝色竖版学习周报", 12)

    assert [item.image.id for item in response.results] == [image.id]


def test_phase4_confirmed_selling_point_without_assets_returns_empty(db_factory):
    with db_factory() as db:
        concept = BusinessConcept(
            code="school_sync",
            name="同步校内",
            search_phrases=[
                ConceptSearchPhrase(
                    phrase="学校课程一致",
                    origin="manual",
                    review_status="accepted",
                )
            ],
        )
        fallback = _image("和学校课程一致", "fallback-title.png")
        db.add_all([concept, fallback])
        db.commit()

        response = SearchService(db).search("和学校课程一致", 12)

    assert response.results == []


def test_phase4_explicit_multi_query_cannot_return_unrelated_global_hit(db_factory):
    query = "想要拍题讲解，还要学情报告"
    with db_factory() as db:
        photo = BusinessConcept(
            code="photo_guided_learning",
            name="AI拍题精学",
            search_phrases=[
                ConceptSearchPhrase(
                    phrase="拍题讲解",
                    origin="manual",
                    review_status="accepted",
                )
            ],
        )
        report = BusinessConcept(
            code="learning_report",
            name="学情报告反馈",
            search_phrases=[
                ConceptSearchPhrase(
                    phrase="学情报告",
                    origin="manual",
                    review_status="accepted",
                )
            ],
        )
        unrelated_concept = BusinessConcept(
            code="unrelated_school_sync",
            name="同步校内",
        )
        unrelated = _image(query, "unrelated-school.png")
        unrelated_group = AssetGroup(
            title="课程同步",
            created_by="designer",
            images=[unrelated],
            concept_links=[
                AssetConceptLink(
                    concept=unrelated_concept,
                    relation_role="expresses",
                    origin="manual",
                    review_status="accepted",
                )
            ],
        )
        db.add_all([photo, report, unrelated_group])
        db.flush()
        unrelated_group.primary_image_id = unrelated.id
        db.commit()

        response = SearchService(db).search(query, 12)

    assert response.results == []
    assert response.search_understanding is not None
    assert response.search_understanding.query_type == "multi_business_intent_search"
    assert {
        item.concept.rsplit(">", 1)[-1].strip()
        for item in response.search_understanding.matched_business_concepts
    } == {"AI拍题精学", "学情报告反馈"}


def test_phase4_generic_short_phrase_does_not_cross_match_long_query(db_factory):
    with db_factory() as db:
        image = _image("动画课程素材", "course.png")
        concept = BusinessConcept(
            code="animation_course",
            name="动画课程",
            search_phrases=[
                ConceptSearchPhrase(
                    phrase="课程",
                    origin="manual",
                    review_status="accepted",
                )
            ],
        )
        group = AssetGroup(
            title=image.title,
            created_by="designer",
            images=[image],
            concept_links=[
                AssetConceptLink(
                    concept=concept,
                    relation_role="expresses",
                    origin="manual",
                    review_status="accepted",
                )
            ],
        )
        db.add_all([concept, group])
        db.flush()
        group.primary_image_id = image.id
        db.commit()

        response = SearchService(db).search(
            "出卷人编教材的人设计课程",
            12,
        )

    assert response.results == []


def test_phase4_groups_candidates_before_single_reranker_call(db_factory):
    class CountingReranker:
        configured = True

        def __init__(self):
            self.calls = 0
            self.document_counts: list[int] = []

        def rerank(self, *, query: str, documents: list[str], top_n: int):
            self.calls += 1
            self.document_counts.append(len(documents))
            return [
                RerankResult(index=index, score=0.9 - index * 0.1)
                for index in range(top_n)
            ]

    reranker = CountingReranker()
    with db_factory() as db:
        primary = _image("共用检索词主图", "primary.png")
        derivative = _image("共用检索词延展图", "derivative.png")
        derivative.asset_role = "derivative"
        group = AssetGroup(
            title="第一素材组",
            created_by="designer",
            images=[primary, derivative],
        )
        other = _image("共用检索词第二组", "other.png")
        other_group = AssetGroup(
            title="第二素材组",
            created_by="designer",
            images=[other],
        )
        db.add_all([group, other_group])
        db.flush()
        group.primary_image_id = primary.id
        other_group.primary_image_id = other.id
        db.commit()

        response = SearchService(db, reranker=reranker).search(
            "共用检索词",
            12,
        )

    assert reranker.calls == 1
    assert reranker.document_counts == [2]
    assert len(response.results) == 2
    assert {item.image.asset_group_id for item in response.results} == {
        group.id,
        other_group.id,
    }
