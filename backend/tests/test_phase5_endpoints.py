from io import BytesIO

from PIL import Image as PillowImage

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


def test_phase5_non_primary_analysis_cannot_replace_group_ai_phrases(client):
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
            return result["value"]

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
    assert ai_phrases == {"正确主图候选"}


def test_phase5_designer_can_remove_and_restore_asset_search_phrase(
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
    assert added.status_code == 200
    phrase = next(
        item
        for item in added.json()["searchPhrases"]
        if item["phrase"] == "手机课程章节对应课本目录"
    )

    removed = client.delete(
        f"/api/asset-groups/{group_id}/search-phrases/{phrase['id']}",
        headers=headers,
    )
    assert removed.status_code == 200
    removed_phrase = next(
        item for item in removed.json()["searchPhrases"] if item["id"] == phrase["id"]
    )
    assert removed_phrase["reviewStatus"] == "rejected"

    restored = client.post(
        f"/api/asset-groups/{group_id}/search-phrases",
        headers=headers,
        json={"phrase": phrase["phrase"], "weight": 1},
    )
    assert restored.status_code == 200
    restored_phrase = next(
        item for item in restored.json()["searchPhrases"] if item["id"] == phrase["id"]
    )
    assert restored_phrase["reviewStatus"] == "accepted"


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
