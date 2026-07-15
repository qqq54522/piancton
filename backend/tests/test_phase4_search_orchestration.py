import threading
import time

from app.core.errors import AppError
from app.models.asset import AssetConceptLink, AssetGroup
from app.models.business_concept import BusinessConcept, ConceptSearchPhrase
from app.models.image import Image
from app.schemas.ai import SearchUnderstanding
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
        query_type="ai_search",
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
