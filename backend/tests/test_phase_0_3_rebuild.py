from io import BytesIO

from PIL import Image as PillowImage

from app.api import dependencies
from app.domain.search_eval import load_search_eval_cases
from app.models.tag import Tag
from tests.conftest import login


def png_file(width: int = 8, height: int = 4) -> bytes:
    output = BytesIO()
    PillowImage.new("RGB", (width, height), "blue").save(output, format="PNG")
    return output.getvalue()


def test_phase0_eval_catalog_supports_real_asset_bindings():
    catalog = load_search_eval_cases()
    bound = [case for case in catalog.cases if case.strong_relevant_asset_ids]

    assert catalog.dataset_status == "partial"
    assert bound
    assert bound[0].expected_concept_codes == ("animation_explanation",)
    assert bound[0].allow_few_results is True


def test_phase1_concept_can_link_multiple_systems_and_keep_stable_code(
    client, db_factory
):
    with db_factory() as db:
        systems = [
            Tag(
                code=code,
                name=name,
                color="#111111",
                node_type="system",
                assignable=False,
                status="active",
            )
            for code, name in (
                ("sync_school", "同步校内体系"),
                ("sync_self_study", "同步自学体系"),
            )
        ]
        db.add_all(systems)
        db.commit()
        system_ids = [item.id for item in systems]

    csrf = login(client, "admin", "admin-password")
    headers = {"X-CSRF-Token": csrf, "Origin": "http://localhost:5173"}
    created = client.post(
        "/api/business-concepts",
        headers=headers,
        json={
            "code": "cross_system_learning_method",
            "name": "跨体系学习方法",
            "conceptType": "teaching_method",
            "systemLinks": [
                {"systemTagId": system_ids[0], "role": "core"},
                {"systemTagId": system_ids[1], "role": "support", "weight": 0.7},
            ],
        },
    )
    assert created.status_code == 201
    concept = created.json()
    assert len(concept["systemLinks"]) == 2

    renamed = client.patch(
        f"/api/business-concepts/{concept['id']}",
        headers=headers,
        json={"name": "跨体系通用学习方法"},
    )
    assert renamed.status_code == 200
    assert renamed.json()["code"] == "cross_system_learning_method"
    assert renamed.json()["version"] == 2

    retired_phrase_add = client.post(
        f"/api/business-concepts/{concept['id']}/search-phrases",
        headers=headers,
        json={
            "phrase": "课程跟学校进度一致",
            "phraseType": "colloquial",
            "origin": "manual",
        },
    )
    assert retired_phrase_add.status_code == 404

    retired_phrase_update = client.patch(
        f"/api/business-concepts/{concept['id']}/search-phrases/legacy-phrase-id",
        headers=headers,
        json={
            "phrase": "课程内容跟学校进度一致",
            "reviewStatus": "rejected",
            "weight": 0.9,
        },
    )
    assert retired_phrase_update.status_code == 404


def test_phase2_upload_creates_group_and_derivative_search_is_deduplicated(
    client, monkeypatch
):
    monkeypatch.setattr(dependencies.settings, "ai_search_enabled", False)
    csrf = login(client, "admin", "admin-password")
    headers = {"X-CSRF-Token": csrf, "Origin": "http://localhost:5173"}
    uploaded = client.post(
        "/api/images/upload",
        headers=headers,
        files={"file": ("primary.png", png_file(), "image/png")},
        data={
            "title": "素材组去重测试",
            "expectedSearchWords": "蓝色横版素材",
            "channel": "官网",
            "styleLabel": "官网风格",
            "isSceneImage": "true",
        },
    )
    assert uploaded.status_code == 201
    primary = uploaded.json()
    assert primary["assetGroupId"]
    assert primary["width"] == 8
    assert primary["height"] == 4
    assert primary["channel"] == "官网"
    assert primary["styleLabel"] == "官网风格"
    assert primary["isSceneImage"] is True

    variant = client.post(
        f"/api/asset-groups/{primary['assetGroupId']}/images",
        headers=headers,
        files={"file": ("vertical.png", png_file(4, 8), "image/png")},
        data={
            "title": "素材组去重测试",
            "assetRole": "derivative",
            "channel": "朋友圈",
        },
    )
    assert variant.status_code == 201
    group = variant.json()
    assert len(group["images"]) == 2
    assert {item["assetRole"] for item in group["images"]} == {"primary", "derivative"}
    assert group["searchPhrases"] == []
    assert group["styleLabel"] == "官网风格"
    assert group["isSceneImage"] is True

    response = client.post(
        "/api/images/search",
        json={"keyword": "素材组去重测试", "limit": 12},
    )
    assert response.status_code == 200
    assert len(response.json()["results"]) == 1
    result = response.json()["results"][0]
    assert result["image"]["variantCount"] == 2
    assert result["image"]["styleLabel"] == "官网风格"
    assert result["image"]["isSceneImage"] is True
    assert {item["channel"] for item in result["availableVariants"]} == {"官网", "朋友圈"}
