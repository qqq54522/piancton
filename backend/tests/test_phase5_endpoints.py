from io import BytesIO

from PIL import Image as PillowImage

from app.models.asset import AssetConceptLink, AssetGroup
from app.models.business_concept import BusinessConcept, ConceptSystemLink
from app.models.tag import Tag
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
            "channel": "官网",
            "autoAnalyze": "false",
        },
    )
    assert uploaded.status_code == 201
    image = uploaded.json()
    assert "tags" not in image
    assert image["channel"] == "官网"
    group_id = image["assetGroupId"]
    index_events.clear()

    variant = client.post(
        f"/api/asset-groups/{group_id}/images",
        headers=headers,
        files={"file": ("vertical.png", png_file("green"), "image/png")},
        data={
            "title": "竖版延展",
            "assetRole": "derivative",
            "channel": "朋友圈",
            "autoAnalyze": "false",
        },
    )
    assert variant.status_code == 201
    assert len(variant.json()["images"]) == 2
    assert variant.json()["primaryImageId"] == image["id"]
    variant_id = next(
        item["id"] for item in variant.json()["images"] if item["id"] != image["id"]
    )
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
    previous = next(item for item in group["images"] if item["id"] == image["id"])
    assert previous["assetRole"] == "revision"
    assert previous["isCurrent"] is False
    assert any(item["assetRole"] == "derivative" and item["isCurrent"] for item in group["images"])
    assert index_events == [
        ("delete", image["id"]),
        ("upsert", group["primaryImageId"]),
    ]


def test_phase5_batch_accepts_ai_concept_suggestions(client, db_factory):
    csrf = login(client, "admin", "admin-password")
    headers = {"X-CSRF-Token": csrf, "Origin": "http://localhost:5173"}
    image = client.post(
        "/api/images/upload",
        headers=headers,
        files={"file": ("concept.png", png_file(), "image/png")},
        data={"title": "关系审核", "autoAnalyze": "false"},
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
        data={"title": "体系筛选素材一", "autoAnalyze": "false"},
    ).json()
    client.post(
        "/api/images/upload",
        headers=headers,
        files={"file": ("second.png", png_file("yellow"), "image/png")},
        data={"title": "体系筛选素材二", "autoAnalyze": "false"},
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
