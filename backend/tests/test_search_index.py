import json

from app.db.base import Base
from app.domain.runtime_intents import RuntimeIntent, RuntimeIntentCatalog
from app.models.asset import AssetConceptLink, AssetGroup, AssetSearchPhrase
from app.models.business_concept import (
    BusinessConcept,
    ConceptSearchPhrase,
    ConceptSystemLink,
)
from app.models.image import ContentTag, Image
from app.models.tag import Tag
from app.repositories.image_repository import ImageRepository
from app.services.embedding_index import EmbeddingIndexSync, image_to_embedding_document
from app.services.meilisearch_client import MEILISEARCH_SEARCHABLE_ATTRIBUTES
from app.services.search_index import image_to_search_document
from app.services.search_index_sync import SearchIndexSync
from app.services.vikingdb_client import VikingDBClient, VikingDBClientError
from app.services.vikingdb_knowledge_router import VikingDBKnowledgeRouter
from app.services.vikingdb_vector_index import (
    VikingDBVectorIndexSync,
    build_vikingdb_knowledge_documents,
)


def _router_catalog() -> RuntimeIntentCatalog:
    return RuntimeIntentCatalog(
        version="test",
        intents=(
            RuntimeIntent(
                code="photo_guided_learning",
                name="AI拍题精学",
                display_name="同步自学体系 > AI拍题精学",
                phrases=(),
                exact_only_phrases=(),
                interpretation_patterns=(),
                pain_points=(),
                must_have_concepts=(),
                nice_to_have_concepts=(),
                exclude_concepts=(),
            ),
            RuntimeIntent(
                code="transfer_practice",
                name="举一反三",
                display_name="同步考点体系 > 举一反三",
                phrases=(),
                exact_only_phrases=(),
                interpretation_patterns=(),
                pain_points=(),
                must_have_concepts=(),
                nice_to_have_concepts=(),
                exclude_concepts=(),
            ),
            RuntimeIntent(
                code="ai_tutor_qa",
                name="AI私教答疑",
                display_name="同步自学体系 > AI私教答疑",
                phrases=(),
                exact_only_phrases=(),
                interpretation_patterns=(),
                pain_points=(),
                must_have_concepts=(),
                nice_to_have_concepts=(),
                exclude_concepts=(),
            ),
            RuntimeIntent(
                code="focused_excellence",
                name="专项培优",
                display_name="同步考点体系 > 专项培优",
                phrases=(),
                exact_only_phrases=(),
                interpretation_patterns=(),
                pain_points=(),
                must_have_concepts=(),
                nice_to_have_concepts=(),
                exclude_concepts=(),
            ),
            RuntimeIntent(
                code="rapid_preview_review",
                name="极速预习复习",
                display_name="同步校内体系 > 极速预习复习",
                phrases=(),
                exact_only_phrases=(),
                interpretation_patterns=(),
                pain_points=(),
                must_have_concepts=(),
                nice_to_have_concepts=(),
                exclude_concepts=(),
            ),
            RuntimeIntent(
                code="expert_planning",
                name="专家规划",
                display_name="同步培养体系 > 专家规划",
                phrases=(),
                exact_only_phrases=(),
                interpretation_patterns=(),
                pain_points=(),
                must_have_concepts=(),
                nice_to_have_concepts=(),
                exclude_concepts=(),
            ),
        ),
    )


class _FakeVikingSearchClient:
    configured = True

    def __init__(self, matches):
        self.matches = matches

    def search_text(self, *args, **kwargs):
        class Result:
            def __init__(self, matches):
                self.matches = matches

        return Result(self.matches)


def _viking_match(code: str, score: float) -> dict:
    return {
        "id": f"selling_point:{code}",
        "fields": {
            "doc_type": "selling_point",
            "concept_code": code,
            "doc_id": f"selling_point:{code}",
        },
        "score": score,
    }


def create_indexed_image(db) -> Image:
    system = Tag(
        code="sync_school",
        name="同步校内体系",
        color="#6366F1",
        node_type="system",
        assignable=False,
        status="active",
    )
    concept = BusinessConcept(
        code="animation_explanation",
        name="动画精讲",
        system_links=[ConceptSystemLink(system_tag=system)],
        search_phrases=[
            ConceptSearchPhrase(phrase="孩子听不懂老师讲课", review_status="accepted")
        ],
    )
    pending = BusinessConcept(code="instant_quiz", name="课后小测")
    group = AssetGroup(
        title="动画课程学习页",
        created_by="designer",
        search_phrases=[
            AssetSearchPhrase(
                phrase="蓝色平板动画课画面",
                origin="manual",
                review_status="accepted",
            ),
            AssetSearchPhrase(
                phrase="AI自动语义候选",
                origin="ai",
                review_status="pending",
            ),
        ],
        concept_links=[
            AssetConceptLink(
                concept=concept,
                relation_role="expresses",
                origin="manual",
                review_status="accepted",
            ),
            AssetConceptLink(
                concept=pending,
                relation_role="supports",
                origin="ai",
                review_status="pending",
                confidence=0.82,
                evidence_reason="画面出现测验入口。",
            ),
        ],
    )
    image = Image(
        title="动画课程学习页",
        file_name="lesson-page.png",
        storage_key="lesson-page.png",
        thumbnail_storage_key="lesson-page-thumb.jpg",
        media_type="image/png",
        size_bytes=100,
        uploader="designer",
        image_summary="学生正在观看动画讲解。",
        semantic_profile_json=json.dumps(
            {
                "schema_version": 2,
                "visual_facts": ["学生正在观看动画讲解"],
                "ocr_text": ["旧OCR词"],
                "subjects": ["旧主体词"],
                "scenes": ["学习页面"],
                "actions": ["旧动作词"],
                "visual_style": ["旧风格词"],
                "visible_product_features": ["旧可见功能词"],
                "asset_search_phrases": ["AI自动语义候选"],
                "negative_visual_concepts": ["旧排除边界词"],
            },
            ensure_ascii=False,
        ),
        asset_group=group,
    )
    image.content_tags.append(
        ContentTag(tag_name="旧客观内容标签", confidence=0.9, dimension="人物")
    )
    db.add(image)
    db.flush()
    group.primary_image_id = image.id
    db.commit()
    return image


def test_phase6_search_document_uses_only_new_semantic_sources(db_factory):
    with db_factory() as db:
        image = create_indexed_image(db)
        document = image_to_search_document(image)

    assert document["manualConceptCodes"] == ["animation_explanation"]
    assert document["acceptedConceptNames"] == ["动画精讲"]
    assert document["pendingAiConceptCodes"] == ["instant_quiz"]
    # D080: 待审核建议只留 code 供运营过滤，不再产出可搜索的名称字段。
    assert "pendingConceptNames" not in document
    assert "课后小测" not in document["searchableText"]
    assert document["acceptedConceptSystems"] == ["sync_school"]
    assert document["assetSearchPhrases"] == ["蓝色平板动画课画面"]
    assert document["semanticProfileSearchPhrases"] == ["AI自动语义候选"]
    assert document["semanticProfileScenes"] == ["学习页面"]
    assert "孩子听不懂老师讲课" in document["searchableText"]
    assert "蓝色平板动画课画面" in document["searchableText"]
    assert "旧客观内容标签" not in document["searchableText"]
    assert "旧OCR词" not in document["searchableText"]
    assert "旧风格词" not in document["searchableText"]
    assert not {
        "manualLabelCodes",
        "businessLabelCodes",
        "level2Categories",
        "tagIds",
        "contentTags",
        "contentDimensions",
        "semanticProfileOcrText",
        "semanticProfileExclusionBoundaries",
    }.intersection(document)


class FakeSearchClient:
    configured = True

    def __init__(self):
        self.configured_count = 0
        self.documents: list[dict] = []
        self.deleted: list[str] = []

    def configure_index(self):
        self.configured_count += 1
        return "settings-task"

    def add_documents(self, documents: list[dict]):
        self.documents.extend(documents)
        return "documents-task"

    def delete_documents(self, image_ids: list[str]):
        self.deleted.extend(image_ids)
        return "delete-task"


def test_search_index_sync_upserts_and_deletes_phase6_documents(db_factory):
    with db_factory() as db:
        image = create_indexed_image(db)
        client = FakeSearchClient()
        sync = SearchIndexSync(client)
        sync.upsert_image(image)
        sync.delete_image(image.id)

    assert client.configured_count == 1
    assert client.documents[0]["id"] == image.id
    assert client.documents[0]["manualConceptCodes"] == ["animation_explanation"]
    assert client.deleted == [image.id]


def test_embedding_index_uses_the_same_phase6_semantic_document(db_factory):
    class FakeEmbeddingClient:
        configured = True
        model_name = "fake-embedding"

        def embed(self, inputs: list[str]):
            assert "已确认业务概念：动画精讲" in inputs[0]
            assert "素材独有搜索表达：蓝色平板动画课画面" in inputs[0]
            assert "素材搜索表达：AI自动语义候选" in inputs[0]
            assert "素材独有搜索表达：AI自动语义候选" not in inputs[0]
            # D080: 待审核概念建议不进入向量/重排文档。
            assert "AI待审核概念" not in inputs[0]
            assert "课后小测" not in inputs[0]
            return [[0.1, 0.2, 0.3]]

    with db_factory() as db:
        image = create_indexed_image(db)
        repo = ImageRepository(db)
        sync = EmbeddingIndexSync(FakeEmbeddingClient())
        sync.upsert_image(repo, image)
        db.commit()

    assert image.embedding is not None
    assert image.embedding.model_name == "fake-embedding"
    assert image.embedding.dimension == 3
    assert image_to_embedding_document(image) == image.embedding.document_text


def test_vikingdb_image_sync_is_retired_and_does_not_write_documents(db_factory):
    class FakeVikingDBClient:
        configured = True

        def __init__(self):
            self.batches: list[list[dict]] = []

        def upsert_documents(self, documents: list[dict], *, async_write: bool = False):
            self.batches.append(list(documents))

    with db_factory() as db:
        image = create_indexed_image(db)
        sync = VikingDBVectorIndexSync(FakeVikingDBClient(), batch_size=1)
        stats, previews = sync.upsert_images([image], dry_run=False)

    assert previews == []
    assert stats.scanned == 1
    assert stats.submitted == 0
    assert stats.skipped == 1
    assert stats.batches == 0
    assert sync.client.batches == []


def test_vikingdb_image_dry_run_no_longer_returns_image_asset_documents(db_factory):
    with db_factory() as db:
        image = create_indexed_image(db)
        sync = VikingDBVectorIndexSync.disabled()
        stats, documents = sync.upsert_images([image], dry_run=True)

    assert stats.scanned == 1
    assert stats.submitted == 0
    assert stats.skipped == 1
    assert documents == []


def test_vikingdb_knowledge_documents_focus_on_systems_and_selling_points():
    documents = build_vikingdb_knowledge_documents()
    doc_types = [document["doc_type"] for document in documents]
    photo_guided = next(
        document
        for document in documents
        if document["doc_id"] == "selling_point:photo_guided_learning"
    )

    assert doc_types.count("system") == 6
    assert doc_types.count("selling_point") == 16
    assert set(doc_types) == {"system", "selling_point"}
    assert photo_guided["concept_code"] == "photo_guided_learning"
    assert "一句话判定" in photo_guided["search_text"]
    assert "背后意思" in photo_guided["search_text"]
    assert "边界逻辑" in photo_guided["search_text"]
    assert "命中一个卖点就回本地数据库取该卖点 accepted 素材" in photo_guided[
        "search_text"
    ]


def test_vikingdb_knowledge_sync_batches_without_images_or_public_phrase_bulk():
    class FakeVikingDBClient:
        configured = True

        def __init__(self):
            self.batches: list[list[dict]] = []

        def upsert_documents(self, documents: list[dict], *, async_write: bool = False):
            self.batches.append(list(documents))

    sync = VikingDBVectorIndexSync(FakeVikingDBClient(), batch_size=10)
    stats, previews = sync.upsert_knowledge_documents()
    submitted_docs = [document for batch in sync.client.batches for document in batch]

    assert previews == []
    assert stats.scanned == 22
    assert stats.submitted == 22
    assert stats.batches == 3
    assert {document["doc_type"] for document in submitted_docs} == {
        "system",
        "selling_point",
    }


def test_vikingdb_reset_deletes_all_then_rebuilds_only_knowledge_documents():
    class FakeVikingDBClient:
        configured = True

        def __init__(self):
            self.deleted = False
            self.batches: list[list[dict]] = []

        def delete_all_documents(self):
            self.deleted = True

        def upsert_documents(self, documents: list[dict], *, async_write: bool = False):
            assert self.deleted is True
            self.batches.append(list(documents))

    sync = VikingDBVectorIndexSync(FakeVikingDBClient(), batch_size=100)
    stats, previews = sync.reset_to_knowledge_documents()
    submitted_docs = [document for batch in sync.client.batches for document in batch]

    assert previews == []
    assert stats.scanned == 22
    assert stats.submitted == 22
    assert sync.client.deleted is True
    assert {document["doc_type"] for document in submitted_docs} == {
        "system",
        "selling_point",
    }


def test_vikingdb_knowledge_router_keeps_single_clear_winner():
    router = VikingDBKnowledgeRouter(
        client=_FakeVikingSearchClient(
            [
                _viking_match("photo_guided_learning", 0.52),
                _viking_match("transfer_practice", 0.43),
                _viking_match("ai_tutor_qa", 0.41),
            ]
        ),
        index_name="piancton_search_assets_idx",
        runtime_catalog=_router_catalog(),
        enabled=True,
    )

    understanding = router.route("拍题精学不是直接抄答案，而是一步步讲题")

    assert understanding is not None
    assert understanding.query_type == "business_intent_search"
    assert [
        item.concept for item in understanding.matched_business_concepts
    ] == ["同步自学体系 > AI拍题精学"]


def test_vikingdb_knowledge_router_allows_close_multi_selling_points():
    router = VikingDBKnowledgeRouter(
        client=_FakeVikingSearchClient(
            [
                _viking_match("photo_guided_learning", 0.57),
                _viking_match("transfer_practice", 0.53),
                _viking_match("ai_tutor_qa", 0.45),
            ]
        ),
        index_name="piancton_search_assets_idx",
        runtime_catalog=_router_catalog(),
        enabled=True,
    )

    understanding = router.route("拍题精学之后还能从一道题带到一类题")

    assert understanding is not None
    assert understanding.query_type == "multi_business_intent_search"
    assert [
        item.concept for item in understanding.matched_business_concepts
    ] == ["同步自学体系 > AI拍题精学", "同步考点体系 > 举一反三"]


def test_vikingdb_knowledge_router_caps_multi_matches_at_three():
    router = VikingDBKnowledgeRouter(
        client=_FakeVikingSearchClient(
            [
                _viking_match("photo_guided_learning", 0.60),
                _viking_match("transfer_practice", 0.58),
                _viking_match("ai_tutor_qa", 0.56),
                _viking_match("focused_excellence", 0.55),
            ]
        ),
        index_name="piancton_search_assets_idx",
        runtime_catalog=_router_catalog(),
        enabled=True,
    )

    understanding = router.route("拍题精学、举一反三、答疑还有专项提升")

    assert understanding is not None
    assert len(understanding.matched_business_concepts) == 3


def test_vikingdb_knowledge_router_overrides_exam_review_to_focused_excellence():
    router = VikingDBKnowledgeRouter(
        client=_FakeVikingSearchClient(
            [
                _viking_match("rapid_preview_review", 0.62),
                _viking_match("focused_excellence", 0.55),
            ]
        ),
        index_name="piancton_search_assets_idx",
        runtime_catalog=_router_catalog(),
        enabled=True,
    )

    understanding = router.route("考前复习")

    assert understanding is not None
    assert understanding.query_type == "business_intent_search"
    assert [
        item.concept for item in understanding.matched_business_concepts
    ] == ["同步考点体系 > 专项培优"]

    typo_understanding = router.route("口前复习")
    assert typo_understanding is not None
    assert [
        item.concept for item in typo_understanding.matched_business_concepts
    ] == ["同步考点体系 > 专项培优"]


def test_vikingdb_knowledge_router_allows_exact_short_photo_entry():
    router = VikingDBKnowledgeRouter(
        client=_FakeVikingSearchClient(
            [
                _viking_match("photo_guided_learning", 0.25),
                _viking_match("rapid_preview_review", 0.23),
                _viking_match("ai_error_book", 0.19),
            ]
        ),
        index_name="piancton_search_assets_idx",
        runtime_catalog=_router_catalog(),
        enabled=True,
    )

    understanding = router.route("拍")

    assert understanding is not None
    assert understanding.query_type == "business_intent_search"
    assert [
        item.concept for item in understanding.matched_business_concepts
    ] == ["同步自学体系 > AI拍题精学"]


def test_vikingdb_knowledge_router_allows_direct_expert_entry():
    router = VikingDBKnowledgeRouter(
        client=_FakeVikingSearchClient(
            [
                _viking_match("rapid_preview_review", 0.27),
                _viking_match("expert_planning", 0.25),
            ]
        ),
        index_name="piancton_search_assets_idx",
        runtime_catalog=_router_catalog(),
        enabled=True,
    )

    understanding = router.route("洋葱的专家")

    assert understanding is not None
    assert understanding.query_type == "business_intent_search"
    assert [
        item.concept for item in understanding.matched_business_concepts
    ] == ["同步培养体系 > 专家规划"]

    strength_understanding = router.route("洋葱的专家老师都有实力")
    assert strength_understanding is not None
    assert [
        item.concept for item in strength_understanding.matched_business_concepts
    ] == ["同步培养体系 > 专家规划"]


def test_vikingdb_knowledge_router_rejects_generic_short_words():
    router = VikingDBKnowledgeRouter(
        client=_FakeVikingSearchClient(
            [
                _viking_match("focused_excellence", 0.25),
                _viking_match("photo_guided_learning", 0.23),
            ]
        ),
        index_name="piancton_search_assets_idx",
        runtime_catalog=_router_catalog(),
        enabled=True,
    )

    assert router.route("图") is None
    assert router.route("素材") is None
    assert router.route("标题") is None


def test_vikingdb_client_upsert_payload(monkeypatch):
    requests = []

    class FakeResponse:
        def raise_for_status(self):
            return None

        def json(self):
            return {"code": 0}

    class FakeHttpClient:
        def __init__(self, timeout, trust_env):
            self.timeout = timeout
            self.trust_env = trust_env

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def post(self, url, headers, json):
            requests.append((url, headers, json))
            return FakeResponse()

    monkeypatch.setattr("app.services.vikingdb_client.httpx.Client", FakeHttpClient)
    client = VikingDBClient(
        base_url="https://api-vikingdb.vikingdb.cn-beijing.volces.com",
        api_key="secret",
        collection_name="piancton_search_assets_test",
        timeout_seconds=12,
    )
    result = client.upsert_documents(
        [
            {
                "doc_id": "selling_point:photo_guided_learning",
                "search_text": "卖点：AI拍题精学",
                "doc_type": "selling_point",
            }
        ]
    )

    assert result.submitted == 1
    url, headers, payload = requests[0]
    assert url.endswith("/api/vikingdb/data/upsert")
    assert headers["Authorization"] == "Bearer secret"
    assert payload["collection_name"] == "piancton_search_assets_test"
    assert payload["async"] is False
    assert payload["data"][0]["doc_type"] == "selling_point"
    assert payload["data"][0]["search_text"] == "卖点：AI拍题精学"


def test_vikingdb_client_delete_all_payload(monkeypatch):
    requests = []

    class FakeResponse:
        def raise_for_status(self):
            return None

        def json(self):
            return {"code": 0}

    class FakeHttpClient:
        def __init__(self, timeout, trust_env):
            self.timeout = timeout
            self.trust_env = trust_env

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def post(self, url, headers, json):
            requests.append((url, headers, json))
            return FakeResponse()

    monkeypatch.setattr("app.services.vikingdb_client.httpx.Client", FakeHttpClient)
    client = VikingDBClient(
        base_url="https://api-vikingdb.vikingdb.cn-beijing.volces.com",
        api_key="secret",
        collection_name="piancton_search_assets_test",
        timeout_seconds=12,
    )
    result = client.delete_all_documents()

    assert result.response == {"code": 0}
    url, headers, payload = requests[0]
    assert url.endswith("/api/vikingdb/data/delete")
    assert headers["Authorization"] == "Bearer secret"
    assert payload == {
        "collection_name": "piancton_search_assets_test",
        "del_all": True,
    }


def test_vikingdb_client_search_payload(monkeypatch):
    requests = []

    class FakeResponse:
        def raise_for_status(self):
            return None

        def json(self):
            return {
                "result": {
                    "data": [
                        {
                            "id": "selling_point:photo_guided_learning",
                            "fields": {
                                "doc_id": "selling_point:photo_guided_learning",
                                "concept_code": "photo_guided_learning",
                            },
                            "score": 0.92,
                            "ann_score": 0.92,
                        }
                    ]
                }
            }

    class FakeHttpClient:
        def __init__(self, timeout, trust_env):
            self.timeout = timeout
            self.trust_env = trust_env

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def post(self, url, headers, json):
            requests.append((url, headers, json))
            return FakeResponse()

    monkeypatch.setattr("app.services.vikingdb_client.httpx.Client", FakeHttpClient)
    client = VikingDBClient(
        base_url="https://api-vikingdb.vikingdb.cn-beijing.volces.com",
        api_key="secret",
        collection_name="piancton_search_assets_test",
        timeout_seconds=12,
    )
    result = client.search_text(
        "拍题后一步步引导",
        index_name="piancton_search_assets_idx",
        limit=3,
        filter_expression={
            "op": "must",
            "field": "doc_type",
            "conds": ["selling_point"],
        },
    )

    assert result.matches[0]["fields"]["concept_code"] == "photo_guided_learning"
    url, headers, payload = requests[0]
    assert url.endswith("/api/vikingdb/data/search/multi_modal")
    assert headers["Authorization"] == "Bearer secret"
    assert payload["collection_name"] == "piancton_search_assets_test"
    assert payload["index_name"] == "piancton_search_assets_idx"
    assert payload["text"] == "拍题后一步步引导"
    assert payload["instruction"] == {"auto_fill": True}
    assert payload["limit"] == 3
    assert payload["filter"] == {
        "op": "must",
        "field": "doc_type",
        "conds": ["selling_point"],
    }


def test_vikingdb_client_rejects_oversized_batches():
    client = VikingDBClient(
        base_url="https://example.test",
        api_key="secret",
        collection_name="piancton",
    )

    try:
        client.upsert_documents([{"doc_id": str(index)} for index in range(101)])
    except VikingDBClientError as exc:
        assert "最多 100 条" in str(exc)
    else:
        raise AssertionError("expected oversized VikingDB batch to fail")


def test_phase6_metadata_no_longer_declares_legacy_image_semantic_tables():
    assert {
        "image_tags",
        "image_categories",
        "image_level2_categories",
        "image_business_labels",
    }.isdisjoint(Base.metadata.tables)


def test_meilisearch_prioritizes_confirmed_language_over_streamlined_ai_semantics():
    priorities = list(MEILISEARCH_SEARCHABLE_ATTRIBUTES)

    assert priorities.index("acceptedConceptNames") < priorities.index("title")
    assert priorities.index("acceptedConceptPhrases") < priorities.index("title")
    assert priorities.index("acceptedConceptPhrases") < priorities.index("assetSearchPhrases")
    assert priorities.index("assetSearchPhrases") < priorities.index("semanticProfileVisualFacts")
    assert priorities.index("semanticProfileScenes") < priorities.index(
        "semanticProfileSearchPhrases"
    )
    # D080: 待审核概念名称彻底退出可搜索字段。
    assert "pendingConceptNames" not in priorities
    assert "contentTags" not in priorities
