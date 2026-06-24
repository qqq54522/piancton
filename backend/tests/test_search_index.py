from sqlalchemy import select

from app.models.image import ContentTag, Image, ImageBusinessLabel, ImageTag
from app.models.tag import Tag
from app.services.search_index import image_to_search_document
from app.services.search_index_sync import SearchIndexSync
from scripts.seed_taxonomy import backfill_manual_business_labels


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
