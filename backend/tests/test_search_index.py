from sqlalchemy import select

from app.models.image import ContentTag, Image, ImageBusinessLabel, ImageCategory, ImageTag
from app.models.tag import Tag
from app.repositories.image_repository import ImageRepository
from app.services.embedding_index import EmbeddingIndexSync, image_to_embedding_document
from app.services.search_index import image_to_search_document
from app.services.search_index_sync import SearchIndexSync
from scripts.seed_taxonomy import backfill_legacy_image_categories, backfill_manual_business_labels


def test_image_to_search_document_contains_manual_ai_and_content_terms(db_factory):
    with db_factory() as db:
        system = Tag(
            code="sync_school",
            name="同步校内体系",
            color="#6366F1",
            node_type="system",
            assignable=False,
            status="active",
        )
        manual_tag = Tag(
            code="animation_explanation",
            name="动画精讲",
            color="#818CF8",
            parent=system,
            is_secondary=True,
            node_type="image_label",
            assignable=True,
            status="active",
            sort_order=1,
        )
        ai_tag = Tag(
            code="instant_quiz",
            name="课后小测",
            color="#818CF8",
            parent=system,
            is_secondary=True,
            node_type="image_label",
            assignable=True,
            status="active",
            sort_order=2,
        )
        image = Image(
            title="动画课程学习页",
            file_name="lesson-page.png",
            storage_key="lesson-page.png",
            thumbnail_storage_key="lesson-page-thumb.jpg",
            media_type="image/png",
            size_bytes=100,
            uploader="designer",
            image_summary="学生正在观看动画讲解，并看到课后测验入口。",
        )
        image.tag_links.append(ImageTag(tag=manual_tag))
        image.content_tags.append(
            ContentTag(tag_name="学生", confidence=0.9, dimension="人物")
        )
        image.business_labels.append(
            ImageBusinessLabel(
                tag=ai_tag,
                label_code="instant_quiz",
                origin="ai",
                role="secondary",
                review_status="pending",
                confidence=0.82,
                reason="画面出现测验入口。",
            )
        )
        db.add(image)
        db.commit()

        document = image_to_search_document(image)
        image.business_labels[0].review_status = "rejected"
        rejected_document = image_to_search_document(image)

    assert document["manualPrimaryLabelCode"] == "animation_explanation"
    assert document["manualLabelCodes"] == ["animation_explanation"]
    assert document["pendingAiLabelCodes"] == ["instant_quiz"]
    assert document["acceptedAiLabelCodes"] == []
    assert "sync_school" in document["systems"]
    assert "sync_school" in document["ancestorCodes"]
    assert "学生" in document["contentTags"]
    assert "动画讲解" in document["searchableText"]
    assert "画面出现测验入口。" in document["searchableText"]
    assert rejected_document["pendingAiLabelCodes"] == []
    assert "instant_quiz" not in rejected_document["businessLabelCodes"]


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


def test_search_index_sync_upserts_and_deletes_documents(db_factory):
    with db_factory() as db:
        tag = Tag(
            code="animation_explanation",
            name="动画精讲",
            color="#818CF8",
            node_type="image_label",
            assignable=True,
            status="active",
        )
        image = Image(
            title="动画课程学习页",
            file_name="lesson-page.png",
            storage_key="lesson-page.png",
            thumbnail_storage_key="lesson-page-thumb.jpg",
            media_type="image/png",
            size_bytes=100,
            uploader="designer",
        )
        image.tag_links.append(ImageTag(tag=tag))
        db.add(image)
        db.commit()

        client = FakeSearchClient()
        sync = SearchIndexSync(client)
        sync.upsert_image(image)
        sync.delete_image(image.id)

    assert client.configured_count == 1
    assert client.documents[0]["id"] == image.id
    assert client.documents[0]["manualPrimaryLabelCode"] == "animation_explanation"
    assert client.deleted == [image.id]


def test_embedding_index_sync_writes_image_semantic_vector(db_factory):
    class FakeEmbeddingClient:
        configured = True
        model_name = "fake-embedding"

        def embed(self, inputs: list[str]):
            assert "语义总结：学生正在观看动画讲解。" in inputs[0]
            return [[0.1, 0.2, 0.3]]

    with db_factory() as db:
        tag = Tag(
            code="animation_explanation",
            name="动画精讲",
            color="#818CF8",
            node_type="image_label",
            assignable=True,
            status="active",
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
        )
        image.tag_links.append(ImageTag(tag=tag))
        db.add(image)
        db.commit()

        repo = ImageRepository(db)
        sync = EmbeddingIndexSync(FakeEmbeddingClient())
        sync.upsert_image(repo, image)
        db.commit()

    assert image.embedding is not None
    assert image.embedding.model_name == "fake-embedding"
    assert image.embedding.dimension == 3
    assert "动画课程学习页" in image.embedding.document_text
    assert image_to_embedding_document(image) == image.embedding.document_text


def test_embedding_document_uses_title_and_manual_tags_without_ai_summary(db_factory):
    with db_factory() as db:
        tag = Tag(
            code="planning",
            name="学习规划",
            color="#818CF8",
            node_type="image_label",
            assignable=True,
            status="active",
        )
        image = Image(
            title="规划进度页",
            file_name="planning.png",
            storage_key="planning.png",
            thumbnail_storage_key="planning-thumb.jpg",
            media_type="image/png",
            size_bytes=100,
            uploader="designer",
        )
        image.tag_links.append(ImageTag(tag=tag))
        db.add(image)
        db.commit()

        document = image_to_embedding_document(image)

    assert "标题：规划进度页" in document
    assert "人工标签：学习规划" in document
    assert "语义总结：" not in document


def test_seed_backfills_manual_business_labels_from_existing_image_tags(db_factory):
    with db_factory() as db:
        system = Tag(
            code="sync_school",
            name="同步校内体系",
            color="#6366F1",
            node_type="system",
            assignable=False,
            status="active",
        )
        primary = Tag(
            code="animation_explanation",
            name="动画精讲",
            color="#818CF8",
            parent=system,
            is_secondary=True,
            node_type="image_label",
            assignable=True,
            status="active",
            sort_order=1,
        )
        additional = Tag(
            code="instant_quiz",
            name="课后小测",
            color="#818CF8",
            parent=system,
            is_secondary=True,
            node_type="image_label",
            assignable=True,
            status="active",
            sort_order=2,
        )
        image = Image(
            title="动画课程学习页",
            file_name="lesson-page.png",
            storage_key="lesson-page.png",
            thumbnail_storage_key="lesson-page-thumb.jpg",
            media_type="image/png",
            size_bytes=100,
            uploader="designer",
        )
        image.tag_links.extend([ImageTag(tag=additional), ImageTag(tag=primary)])
        db.add(image)
        db.commit()

        created = backfill_manual_business_labels(db)
        db.commit()
        labels = list(db.scalars(select(ImageBusinessLabel)).all())

    assert created == 2
    assert [label.label_code for label in labels] == [
        "animation_explanation",
        "instant_quiz",
    ]
    assert [label.role for label in labels] == ["primary", "additional"]


def test_seed_backfills_function_category_for_legacy_tagged_images(db_factory):
    with db_factory() as db:
        tag = Tag(
            code="stage_transition",
            name="学段衔接",
            color="#F472B6",
            node_type="image_label",
            assignable=True,
            status="active",
        )
        image = Image(
            title="学段衔接旧图",
            file_name="legacy-stage.png",
            storage_key="legacy-stage.png",
            thumbnail_storage_key="legacy-stage-thumb.jpg",
            media_type="image/png",
            size_bytes=100,
            uploader="designer",
        )
        image.tag_links.append(ImageTag(tag=tag))
        already_classified = Image(
            title="已有场景分类",
            file_name="scene.png",
            storage_key="scene.png",
            thumbnail_storage_key="scene-thumb.jpg",
            media_type="image/png",
            size_bytes=100,
            uploader="designer",
            categories=[ImageCategory(name="scene")],
        )
        already_classified.tag_links.append(ImageTag(tag=tag))
        db.add_all([image, already_classified])
        db.commit()

        created = backfill_legacy_image_categories(db)
        db.commit()
        categories = {
            row[0]: row[1]
            for row in db.execute(
                select(Image.title, ImageCategory.name)
                .join(ImageCategory, ImageCategory.image_id == Image.id)
                .order_by(Image.title)
            ).all()
        }

    assert created == 1
    assert categories["学段衔接旧图"] == "function"
    assert categories["已有场景分类"] == "scene"
