import json

from app.db.base import Base
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
