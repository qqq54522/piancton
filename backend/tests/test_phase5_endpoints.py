import json
from io import BytesIO
from zipfile import ZipFile

from PIL import Image as PillowImage

from app.ai.contracts import ModelCallResult
from app.api import dependencies
from app.main import app
from app.models.asset import AssetConceptLink, AssetGroup
from app.models.business_concept import BusinessConcept, ConceptSystemLink
from app.models.tag import Tag
from app.schemas.ai import ImageAnalysisResult, ImageSemanticProfile
from app.services.embedding_index import EmbeddingIndexSync
from app.services.search_index_sync import SearchIndexSync
from tests.conftest import login


def png_file(color: str = "blue") -> bytes:
    output = BytesIO()
    PillowImage.new("RGB", (8, 4), color).save(output, format="PNG")
    return output.getvalue()


def test_phase5_designer_can_upload_primary_add_variant_and_replace_it(client, monkeypatch):
    index_events: list[tuple[str, str]] = []
    monkeypatch.setattr(
        SearchIndexSync,
        "upsert_image",
        lambda _self, image: index_events.append(("upsert", image.id)),
    )
    monkeypatch.setattr(
        SearchIndexSync,
        "delete_image",
        lambda _self, image_id: index_events.append(("delete", image_id)),
    )
    csrf = login(client, "admin", "admin-password")
    headers = {"X-CSRF-Token": csrf, "Origin": "http://localhost:5173"}
    uploaded = client.post(
        "/api/images/upload",
        headers=headers,
        files={"file": ("primary.png", png_file(), "image/png")},
        data={
            "title": "只上传主图",
            "channel": "官网、手机端大图",
            "autoAnalyze": "false",
        },
    )
    assert uploaded.status_code == 201
    image = uploaded.json()
    assert "tags" not in image
    assert image["channel"] == "官网、手机端大图"
    group_id = image["assetGroupId"]
    index_events.clear()

    variant = client.post(
        f"/api/asset-groups/{group_id}/images",
        headers=headers,
        files={"file": ("vertical.png", png_file("green"), "image/png")},
        data={
            "title": "竖版延展",
            "assetRole": "derivative",
            "autoAnalyze": "false",
        },
    )
    assert variant.status_code == 201
    assert len(variant.json()["images"]) == 2
    assert variant.json()["primaryImageId"] == image["id"]
    variant_id = next(
        item["id"] for item in variant.json()["images"] if item["id"] != image["id"]
    )
    variant_image = next(
        item for item in variant.json()["images"] if item["id"] == variant_id
    )
    assert variant_image["channel"] == image["channel"]
    assert variant_image["mediaType"] == "image/png"
    assert ("upsert", variant_id) in index_events
    index_events.clear()

    replaced = client.post(
        f"/api/asset-groups/{group_id}/primary-image",
        headers=headers,
        files={"file": ("new-primary.png", png_file("red"), "image/png")},
        data={"title": "新版主图", "autoAnalyze": "false"},
    )
    assert replaced.status_code == 201
    group = replaced.json()
    assert group["primaryImageId"] != image["id"]
    assert group["title"] == "新版主图"
    new_primary = next(
        item for item in group["images"] if item["id"] == group["primaryImageId"]
    )
    assert new_primary["channel"] == image["channel"]
    previous = next(item for item in group["images"] if item["id"] == image["id"])
    assert previous["assetRole"] == "revision"
    assert previous["isCurrent"] is False
    assert any(item["assetRole"] == "derivative" and item["isCurrent"] for item in group["images"])
    assert index_events == [
        ("delete", image["id"]),
        ("upsert", group["primaryImageId"]),
    ]


def test_phase5_asset_version_writes_inherit_primary_channel(client):
    csrf = login(client, "admin", "admin-password")
    headers = {"X-CSRF-Token": csrf, "Origin": "http://localhost:5173"}
    primary = client.post(
        "/api/images/upload",
        headers=headers,
        files={"file": ("primary.png", png_file(), "image/png")},
        data={"title": "主图", "channel": "PPT、手机端大图", "autoAnalyze": "false"},
    ).json()
    group_id = primary["assetGroupId"]

    variant = client.post(
        f"/api/asset-groups/{group_id}/images",
        headers=headers,
        files={"file": ("vertical.png", png_file("green"), "image/png")},
        data={
            "title": "缺渠道延展",
            "assetRole": "derivative",
            "autoAnalyze": "false",
        },
    )
    assert variant.status_code == 201
    variant_image = next(
        item for item in variant.json()["images"] if item["id"] != primary["id"]
    )
    assert variant_image["channel"] == primary["channel"]

    replaced = client.post(
        f"/api/asset-groups/{group_id}/primary-image",
        headers=headers,
        files={"file": ("new-primary.png", png_file("red"), "image/png")},
        data={"title": "缺渠道替换", "autoAnalyze": "false"},
    )
    assert replaced.status_code == 201
    primary_image = next(
        item
        for item in replaced.json()["images"]
        if item["id"] == replaced.json()["primaryImageId"]
    )
    assert primary_image["channel"] == primary["channel"]


def test_phase5_filter_metadata_can_be_changed_after_upload(client, monkeypatch):
    indexed: list[str] = []
    monkeypatch.setattr(
        SearchIndexSync,
        "upsert_image",
        lambda _self, image: indexed.append(image.id),
    )
    csrf = login(client, "admin", "admin-password")
    headers = {"X-CSRF-Token": csrf, "Origin": "http://localhost:5173"}
    primary = client.post(
        "/api/images/upload",
        headers=headers,
        files={"file": ("primary.png", png_file(), "image/png")},
        data={
            "title": "筛选信息可编辑",
            "channel": "PPT",
            "styleLabel": "旧风格",
            "isSceneImage": "false",
            "autoAnalyze": "false",
        },
    ).json()
    variant_group = client.post(
        f"/api/asset-groups/{primary['assetGroupId']}/images",
        headers=headers,
        files={"file": ("vertical.png", png_file("green"), "image/png")},
        data={
            "title": "筛选信息竖版",
            "assetRole": "derivative",
            "autoAnalyze": "false",
        },
    ).json()
    variant_id = next(
        item["id"] for item in variant_group["images"] if item["id"] != primary["id"]
    )
    indexed.clear()

    updated = client.patch(
        f"/api/images/{variant_id}/filter-metadata",
        headers=headers,
        json={
            "channel": "官网大图、手机端大图",
            "styleLabel": "数据卡片",
            "isSceneImage": True,
        },
    )

    assert updated.status_code == 200
    assert updated.json()["channel"] == "官网大图、手机端大图"
    assert updated.json()["styleLabel"] == "数据卡片"
    assert updated.json()["isSceneImage"] is True
    assert set(indexed) == {primary["id"], variant_id}
    group = client.get(
        f"/api/asset-groups/{primary['assetGroupId']}", headers=headers
    ).json()
    assert group["styleLabel"] == "数据卡片"
    assert group["isSceneImage"] is True
    channels = {item["id"]: item["channel"] for item in group["images"]}
    assert channels[primary["id"]] == "PPT"
    assert channels[variant_id] == "官网大图、手机端大图"

    missing_channel = client.patch(
        f"/api/images/{variant_id}/filter-metadata",
        headers=headers,
        json={"channel": " ", "styleLabel": None, "isSceneImage": False},
    )
    assert missing_channel.status_code == 422


def test_phase5_source_links_are_editor_only(client):
    admin_csrf = login(client, "admin", "admin-password")
    admin_headers = {"X-CSRF-Token": admin_csrf, "Origin": "http://localhost:5173"}
    primary = client.post(
        "/api/images/upload",
        headers=admin_headers,
        files={"file": ("primary.png", png_file(), "image/png")},
        data={"title": "源文件测试主图", "channel": "PPT", "autoAnalyze": "false"},
    ).json()
    group_id = primary["assetGroupId"]

    added = client.post(
        f"/api/asset-groups/{group_id}/source-links",
        headers=admin_headers,
        json={
            "label": "Figma 设计稿",
            "url": "https://www.figma.com/file/source-design",
            "linkType": "figma",
            "note": "设计师修改时优先找这里",
        },
    )
    assert added.status_code == 200
    link = added.json()["sourceLinks"][0]
    assert link["label"] == "Figma 设计稿"
    assert link["linkType"] == "figma"

    updated = client.patch(
        f"/api/asset-groups/{group_id}/source-links/{link['id']}",
        headers=admin_headers,
        json={"label": "最新版 Figma", "note": ""},
    )
    assert updated.status_code == 200
    updated_link = updated.json()["sourceLinks"][0]
    assert updated_link["label"] == "最新版 Figma"
    assert updated_link["note"] is None

    exported = client.get(
        f"/api/asset-groups/{group_id}/export",
        headers=admin_headers,
    )
    assert exported.status_code == 200
    assert exported.headers["content-type"] == "application/zip"
    with ZipFile(BytesIO(exported.content)) as archive:
        names = archive.namelist()
        assert "manifest.json" in names
        assert any(name.startswith("images/") for name in names)
        manifest = archive.read("manifest.json").decode("utf-8")
        assert "最新版 Figma" in manifest

    business_csrf = login(client, "business", "business-password")
    business_headers = {
        "X-CSRF-Token": business_csrf,
        "Origin": "http://localhost:5173",
    }
    business_detail = client.get(
        f"/api/asset-groups/{group_id}",
        headers=business_headers,
    )
    assert business_detail.status_code == 200
    assert business_detail.json()["sourceLinks"] == []
    business_groups = client.get("/api/asset-groups", headers=business_headers)
    assert business_groups.status_code == 200
    assert business_groups.json()[0]["sourceLinks"] == []

    business_export = client.post(
        "/api/asset-groups/export",
        headers=business_headers,
        json={"groupIds": [group_id]},
    )
    assert business_export.status_code == 200
    assert business_export.headers["content-type"] == "application/zip"
    with ZipFile(BytesIO(business_export.content)) as archive:
        names = archive.namelist()
        assert "manifest.json" in names
        group_manifest_name = next(name for name in names if name.endswith("/manifest.json"))
        group_manifest = json.loads(archive.read(group_manifest_name))
        assert group_manifest["sourceLinks"] == []

    blocked = client.post(
        f"/api/asset-groups/{group_id}/source-links",
        headers=business_headers,
        json={
            "label": "业务不可写",
            "url": "https://www.figma.com/file/blocked",
            "linkType": "figma",
        },
    )
    assert blocked.status_code == 403

    admin_csrf = login(client, "admin", "admin-password")
    admin_headers = {"X-CSRF-Token": admin_csrf, "Origin": "http://localhost:5173"}
    removed = client.delete(
        f"/api/asset-groups/{group_id}/source-links/{link['id']}",
        headers=admin_headers,
    )
    assert removed.status_code == 200
    assert removed.json()["sourceLinks"] == []


def test_source_link_changes_refresh_ai_search_primary_image(client, monkeypatch):
    class FakeAiSearchIndex:
        configured = True

        def __init__(self):
            self.upserted: list[str] = []
            self.deleted: list[str] = []

        def upsert_image(self, image):
            self.upserted.append(image.id)

        def delete_image(self, image_id):
            self.deleted.append(image_id)

    fake_index = FakeAiSearchIndex()
    csrf = login(client, "admin", "admin-password")
    headers = {"X-CSRF-Token": csrf, "Origin": "http://localhost:5173"}
    primary = client.post(
        "/api/images/upload",
        headers=headers,
        files={"file": ("primary.png", png_file(), "image/png")},
        data={"title": "卖点补充同步图", "channel": "PPT", "autoAnalyze": "false"},
    ).json()
    monkeypatch.setattr(dependencies, "_build_ai_search_index", lambda: fake_index)
    group_id = primary["assetGroupId"]

    added = client.post(
        f"/api/asset-groups/{group_id}/source-links",
        headers=headers,
        json={
            "label": "卖点补充",
            "url": "https://example.com/source",
            "linkType": "other",
            "note": "这张图适合解释 AI 拍题精学的分步引导。",
        },
    )
    assert added.status_code == 200
    link_id = added.json()["sourceLinks"][0]["id"]

    updated = client.patch(
        f"/api/asset-groups/{group_id}/source-links/{link_id}",
        headers=headers,
        json={"note": "改成更适合销售对家长讲解的卖点补充。"},
    )
    assert updated.status_code == 200

    removed = client.delete(
        f"/api/asset-groups/{group_id}/source-links/{link_id}",
        headers=headers,
    )
    assert removed.status_code == 200

    assert fake_index.upserted == [primary["id"], primary["id"], primary["id"]]
    assert fake_index.deleted == []


def test_phase5_derivative_upload_never_queues_ai_analysis(client, monkeypatch):
    from app.api.v1 import assets as assets_api

    queued_image_ids: list[str] = []
    monkeypatch.setattr(
        assets_api,
        "_queue_analysis",
        lambda image_id, **_kwargs: queued_image_ids.append(image_id),
    )
    csrf = login(client, "admin", "admin-password")
    headers = {"X-CSRF-Token": csrf, "Origin": "http://localhost:5173"}
    primary = client.post(
        "/api/images/upload",
        headers=headers,
        files={"file": ("primary.png", png_file(), "image/png")},
        data={"title": "主图", "channel": "PPT", "autoAnalyze": "false"},
    ).json()

    variant = client.post(
        f"/api/asset-groups/{primary['assetGroupId']}/images",
        headers=headers,
        files={"file": ("vertical.png", png_file("green"), "image/png")},
        data={
            "title": "竖版尺寸延展",
            "assetRole": "derivative",
            "autoAnalyze": "true",
        },
    )

    assert variant.status_code == 201
    assert queued_image_ids == []
    variant_id = next(
        item["id"]
        for item in variant.json()["images"]
        if item["id"] != primary["id"]
    )
    manual_analysis = client.post(
        f"/api/ai/images/{variant_id}/analyze",
        headers=headers,
    )
    assert manual_analysis.status_code == 400
    assert manual_analysis.json()["code"] == "derivative_analysis_not_required"


def test_phase5_analysis_does_not_persist_ai_asset_search_phrases(client):
    result = {
        "value": ImageAnalysisResult(
            image_summary="主图画面",
            semantic_profile=ImageSemanticProfile(
                visual_facts=["主图画面"],
                asset_search_phrases=["正确主图候选"],
            ),
            concept_suggestions=[],
        )
    }

    class FakeAiService:
        def analyze_image(self, _path):
            return ModelCallResult(result["value"])

    app.dependency_overrides[dependencies.get_ai_service] = lambda: FakeAiService()
    csrf = login(client, "admin", "admin-password")
    headers = {"X-CSRF-Token": csrf, "Origin": "http://localhost:5173"}
    primary = client.post(
        "/api/images/upload",
        headers=headers,
        files={"file": ("primary.png", png_file(), "image/png")},
        data={"title": "主图", "channel": "PPT", "autoAnalyze": "false"},
    ).json()
    group_id = primary["assetGroupId"]
    analyzed = client.post(f"/api/ai/images/{primary['id']}/analyze", headers=headers)
    assert analyzed.status_code == 200

    variant_group = client.post(
        f"/api/asset-groups/{group_id}/images",
        headers=headers,
        files={"file": ("vertical.png", png_file("green"), "image/png")},
        data={
            "title": "同主题备选图",
            "assetRole": "alternative",
            "autoAnalyze": "false",
        },
    ).json()
    variant_id = next(
        item["id"] for item in variant_group["images"] if item["id"] != primary["id"]
    )

    result["value"] = ImageAnalysisResult(
        image_summary="错误延展画面",
        semantic_profile=ImageSemanticProfile(
            visual_facts=["错误延展画面"],
            asset_search_phrases=["错误延展候选"],
        ),
        concept_suggestions=[],
    )
    alternative_analysis = client.post(
        f"/api/ai/images/{variant_id}/analyze",
        headers=headers,
    )
    assert alternative_analysis.status_code == 200

    phrases = client.get(f"/api/asset-groups/{group_id}", headers=headers).json()[
        "searchPhrases"
    ]
    ai_phrases = {
        item["phrase"]
        for item in phrases
        if item["origin"] == "ai" and item["reviewStatus"] == "pending"
    }
    assert ai_phrases == set()


def test_phase5_asset_search_phrase_mutation_routes_are_retired(
    client, monkeypatch
):
    monkeypatch.setattr(SearchIndexSync, "upsert_image", lambda _self, _image: None)
    monkeypatch.setattr(
        EmbeddingIndexSync,
        "upsert_image",
        lambda _self, _repo, _image: None,
    )
    csrf = login(client, "admin", "admin-password")
    headers = {"X-CSRF-Token": csrf, "Origin": "http://localhost:5173"}
    primary = client.post(
        "/api/images/upload",
        headers=headers,
        files={"file": ("primary.png", png_file(), "image/png")},
        data={"title": "话术删除测试主图", "channel": "PPT", "autoAnalyze": "false"},
    ).json()
    group_id = primary["assetGroupId"]

    added = client.post(
        f"/api/asset-groups/{group_id}/search-phrases",
        headers=headers,
        json={"phrase": "手机课程章节对应课本目录", "weight": 1},
    )
    assert added.status_code == 404

    removed = client.delete(
        f"/api/asset-groups/{group_id}/search-phrases/legacy-phrase-id",
        headers=headers,
    )
    assert removed.status_code == 404

    reviewed = client.patch(
        f"/api/asset-groups/{group_id}/search-phrases/legacy-phrase-id",
        headers=headers,
        json={"reviewStatus": "accepted"},
    )
    assert reviewed.status_code == 404


def test_phase5_designer_can_trash_variant_but_not_primary(client, monkeypatch):
    deleted_from_index: list[str] = []
    restored_to_index: list[str] = []
    monkeypatch.setattr(
        SearchIndexSync,
        "delete_image",
        lambda _self, image_id: deleted_from_index.append(image_id),
    )
    monkeypatch.setattr(
        SearchIndexSync,
        "upsert_image",
        lambda _self, image: restored_to_index.append(image.id),
    )
    csrf = login(client, "admin", "admin-password")
    headers = {"X-CSRF-Token": csrf, "Origin": "http://localhost:5173"}
    primary = client.post(
        "/api/images/upload",
        headers=headers,
        files={"file": ("primary.png", png_file(), "image/png")},
        data={"title": "保留主图", "channel": "PPT", "autoAnalyze": "false"},
    ).json()
    group_id = primary["assetGroupId"]
    variant_group = client.post(
        f"/api/asset-groups/{group_id}/images",
        headers=headers,
        files={"file": ("vertical.png", png_file("green"), "image/png")},
        data={
            "title": "待删除延展",
            "assetRole": "derivative",
            "autoAnalyze": "false",
        },
    ).json()
    variant_id = next(
        item["id"] for item in variant_group["images"] if item["id"] != primary["id"]
    )

    removed = client.delete(
        f"/api/asset-groups/{group_id}/images/{variant_id}",
        headers=headers,
    )
    assert removed.status_code == 200
    assert [item["id"] for item in removed.json()["images"]] == [primary["id"]]
    assert deleted_from_index == [variant_id]
    assert variant_id in {
        item["id"] for item in client.get("/api/images/trash").json()
    }
    refreshed = client.get(f"/api/asset-groups/{group_id}", headers=headers).json()
    assert [item["id"] for item in refreshed["images"]] == [primary["id"]]

    restored_to_index.clear()
    restored = client.post(f"/api/images/{variant_id}/restore", headers=headers)
    assert restored.status_code == 200
    assert restored_to_index == [variant_id]
    restored_group = client.get(
        f"/api/asset-groups/{group_id}", headers=headers
    ).json()
    assert {item["id"] for item in restored_group["images"]} == {
        primary["id"],
        variant_id,
    }

    primary_delete = client.delete(
        f"/api/asset-groups/{group_id}/images/{primary['id']}",
        headers=headers,
    )
    assert primary_delete.status_code == 400
    assert primary_delete.json()["code"] == "cannot_delete_primary_image"


def test_phase5_batch_accepts_ai_concept_suggestions(client, db_factory):
    csrf = login(client, "admin", "admin-password")
    headers = {"X-CSRF-Token": csrf, "Origin": "http://localhost:5173"}
    image = client.post(
        "/api/images/upload",
        headers=headers,
        files={"file": ("concept.png", png_file(), "image/png")},
        data={"title": "关系审核", "channel": "PPT", "autoAnalyze": "false"},
    ).json()

    with db_factory() as db:
        group = db.get(AssetGroup, image["assetGroupId"])
        concept = BusinessConcept(code="phase5_concept", name="P5 概念")
        link = AssetConceptLink(
            asset_group=group,
            concept=concept,
            relation_role="supports",
            origin="ai",
            review_status="pending",
            confidence=0.88,
        )
        db.add_all([concept, link])
        db.commit()
        link_id = link.id

    reviewed = client.post(
        f"/api/asset-groups/{image['assetGroupId']}/concept-links/review-batch",
        headers=headers,
        json={"linkIds": [link_id], "reviewStatus": "accepted"},
    )
    assert reviewed.status_code == 200
    links = reviewed.json()["conceptLinks"]
    assert any(item["id"] == link_id and item["reviewStatus"] == "accepted" for item in links)
    assert any(
        item["origin"] == "manual"
        and item["conceptCode"] == "phase5_concept"
        and item["relationRole"] == "supports"
        for item in links
    )


def test_phase5_system_filter_asset_metadata_and_result_feedback(client, db_factory):
    csrf = login(client, "admin", "admin-password")
    headers = {"X-CSRF-Token": csrf, "Origin": "http://localhost:5173"}
    first = client.post(
        "/api/images/upload",
        headers=headers,
        files={"file": ("first.png", png_file(), "image/png")},
        data={"title": "体系筛选素材一", "channel": "PPT", "autoAnalyze": "false"},
    ).json()
    client.post(
        "/api/images/upload",
        headers=headers,
        files={"file": ("second.png", png_file("yellow"), "image/png")},
        data={"title": "体系筛选素材二", "channel": "PPT", "autoAnalyze": "false"},
    )

    with db_factory() as db:
        system = Tag(
            code="sync_school_phase5",
            name="P5 体系",
            color="#2563EB",
            node_type="system",
            assignable=False,
        )
        concept = BusinessConcept(
            code="phase5_filtered_concept",
            name="体系内概念",
            system_links=[ConceptSystemLink(system_tag=system)],
        )
        group = db.get(AssetGroup, first["assetGroupId"])
        group.concept_links.append(
            AssetConceptLink(
                concept=concept,
                relation_role="expresses",
                origin="manual",
                review_status="accepted",
            )
        )
        db.add_all([system, concept, group])
        db.commit()

    search = client.post(
        "/api/images/search",
        json={
            "keyword": "体系筛选素材",
            "limit": 12,
            "systemCode": "sync_school_phase5",
        },
    )
    assert search.status_code == 200
    body = search.json()
    assert [item["image"]["id"] for item in body["results"]] == [first["id"]]
    result = body["results"][0]
    assert result["assetGroupId"] == first["assetGroupId"]
    assert result["expressedConcepts"] == ["体系内概念"]
    assert result["availableVariants"][0]["downloadUrl"].endswith("/download")

    feedback = client.post(
        "/api/search-feedback",
        headers=headers,
        json={
            "searchLogId": body["searchLogId"],
            "keyword": "体系筛选素材",
            "feedbackType": "not_relevant",
            "resultImageId": first["id"],
            "assetGroupId": first["assetGroupId"],
        },
    )
    assert feedback.status_code == 201
    assert feedback.json()["resultImageId"] == first["id"]
    assert feedback.json()["assetGroupId"] == first["assetGroupId"]

    version_feedback = client.post(
        "/api/search-feedback",
        headers=headers,
        json={
            "searchLogId": body["searchLogId"],
            "keyword": "体系筛选素材",
            "feedbackType": "wrong_version",
            "note": "想要手机端小图版本",
            "resultImageId": first["id"],
            "assetGroupId": first["assetGroupId"],
        },
    )
    assert version_feedback.status_code == 201
    assert version_feedback.json()["feedbackType"] == "wrong_version"

    positive_feedback = client.post(
        "/api/search-feedback",
        headers=headers,
        json={
            "searchLogId": body["searchLogId"],
            "keyword": "体系筛选素材",
            "feedbackType": "relevant",
            "resultImageId": first["id"],
            "assetGroupId": first["assetGroupId"],
        },
    )
    assert positive_feedback.status_code == 201
    assert positive_feedback.json()["feedbackType"] == "relevant"


def test_business_facets_and_asset_classification_support_green_expression_level(
    client, db_factory
):
    csrf = login(client, "admin", "admin-password")
    headers = {"X-CSRF-Token": csrf, "Origin": "http://localhost:5173"}
    image = client.post(
        "/api/images/upload",
        headers=headers,
        files={"file": ("expression.png", png_file(), "image/png")},
        data={"title": "例题后变式训练", "channel": "PPT", "autoAnalyze": "false"},
    ).json()

    with db_factory() as db:
        concept = BusinessConcept(code="transfer_practice", name="举一反三")
        db.add(concept)
        db.commit()
        concept_id = concept.id

    catalog = client.get("/api/business-facets", headers=headers)
    assert catalog.status_code == 200
    assert any(
        item["code"] == "ep_exam_variant_expansion"
        for item in catalog.json()["evidencePoints"]
    )
    transition_point = next(
        item
        for item in catalog.json()["evidencePoints"]
        if item["code"] == "ep_cultivation_transition_course"
    )
    assert transition_point["sourceRef"] == "04-sync-cultivation.png"
    assert transition_point["sourcePaths"][0][-1] == {
        "level": "evidence_expression",
        "label": "小升初、初升高过渡课",
    }
    transfer_logic = next(
        item
        for item in catalog.json()["evidencePoints"]
        if item["code"] == "ep_exam_transfer_logic"
    )
    assert transfer_logic["reviewNotes"] == [
        "2026-07-23 人工确认：AI 拍题精学讲解完成后自动推送几道相似题，"
        "这个后续能力同时证明“举一反三”；该说明是人工校准关系，不冒充原图绿色点。"
    ]

    updated = client.patch(
        f"/api/asset-groups/{image['assetGroupId']}/business-classification",
        headers=headers,
        json={
            "conceptId": concept_id,
            "proofPointCode": "pp_exam_transfer_variant_practice",
            "evidencePointCode": "ep_exam_variant_expansion",
        },
    )
    assert updated.status_code == 200
    body = updated.json()
    assert body["primaryProofPointCode"] == "pp_exam_transfer_variant_practice"
    assert body["primaryEvidencePointCode"] == "ep_exam_variant_expansion"
    assert any(
        item["conceptCode"] == "transfer_practice"
        and item["relationRole"] == "expresses"
        and item["reviewStatus"] == "accepted"
        for item in body["conceptLinks"]
    )


def test_asset_business_classification_saves_proof_and_evidence_facets(client, db_factory):
    csrf = login(client, "admin", "admin-password")
    headers = {"X-CSRF-Token": csrf, "Origin": "http://localhost:5173"}
    image = client.post(
        "/api/images/upload",
        headers=headers,
        files={"file": ("facet.png", png_file(), "image/png")},
        data={"title": "短时动画课", "channel": "PPT", "autoAnalyze": "false"},
    ).json()
    with db_factory() as db:
        concept = BusinessConcept(code="animation_explanation", name="动画精讲")
        db.add(concept)
        db.commit()
        concept_id = concept.id

    facets = client.get("/api/business-facets", headers=headers)
    assert facets.status_code == 200
    assert any(
        item["code"] == "ep_school_short_animation_lesson"
        for item in facets.json()["evidencePoints"]
    )

    classified = client.patch(
        f"/api/asset-groups/{image['assetGroupId']}/business-classification",
        headers=headers,
        json={
            "conceptId": concept_id,
            "proofPointCode": "pp_animation_pedagogy_design",
            "evidencePointCode": "ep_school_short_animation_lesson",
        },
    )

    assert classified.status_code == 200
    body = classified.json()
    assert body["primaryProofPointCode"] == "pp_animation_pedagogy_design"
    assert body["primaryEvidencePointCode"] == "ep_school_short_animation_lesson"
    assert any(
        item["conceptCode"] == "animation_explanation"
        and item["relationRole"] == "expresses"
        and item["reviewStatus"] == "accepted"
        for item in body["conceptLinks"]
    )


def test_asset_relations_can_be_replaced_in_one_request(client, db_factory):
    csrf = login(client, "admin", "admin-password")
    headers = {"X-CSRF-Token": csrf, "Origin": "http://localhost:5173"}
    image = client.post(
        "/api/images/upload",
        headers=headers,
        files={"file": ("multi-selling-point.png", png_file(), "image/png")},
        data={"title": "多卖点素材", "channel": "PPT", "autoAnalyze": "false"},
    ).json()
    with db_factory() as db:
        primary = BusinessConcept(code="animation_explanation", name="动画精讲")
        first_support = BusinessConcept(code="transfer_practice", name="举一反三")
        second_support = BusinessConcept(code="study_companion", name="督学伴学")
        db.add_all([primary, first_support, second_support])
        db.commit()
        concept_ids = {
            "primary": primary.id,
            "first": first_support.id,
            "second": second_support.id,
        }

    group_url = f"/api/asset-groups/{image['assetGroupId']}/concept-links"
    created = client.put(
        group_url,
        headers=headers,
        json={
            "relations": [
                {"conceptId": concept_ids["primary"], "relationRole": "expresses"},
                {"conceptId": concept_ids["first"], "relationRole": "supports"},
            ]
        },
    )
    assert created.status_code == 200
    assert {
        (item["conceptCode"], item["relationRole"])
        for item in created.json()["conceptLinks"]
        if item["origin"] == "manual"
    } == {
        ("animation_explanation", "expresses"),
        ("transfer_practice", "supports"),
    }

    replaced = client.put(
        group_url,
        headers=headers,
        json={
            "relations": [
                {"conceptId": concept_ids["first"], "relationRole": "expresses"},
                {"conceptId": concept_ids["second"], "relationRole": "supports"},
            ]
        },
    )
    assert replaced.status_code == 200
    assert {
        (item["conceptCode"], item["relationRole"])
        for item in replaced.json()["conceptLinks"]
        if item["origin"] == "manual"
    } == {
        ("transfer_practice", "expresses"),
        ("study_companion", "supports"),
    }

    multiple_primary = client.put(
        group_url,
        headers=headers,
        json={
            "relations": [
                {"conceptId": concept_ids["primary"], "relationRole": "expresses"},
                {"conceptId": concept_ids["first"], "relationRole": "expresses"},
            ]
        },
    )
    assert multiple_primary.status_code == 400
    assert multiple_primary.json()["code"] == "multiple_primary_concepts"
