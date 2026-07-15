from io import BytesIO

from PIL import Image as PillowImage

from app.api import dependencies
from app.domain.search_eval import load_search_eval_cases
from app.main import app
from app.models.business_concept import BusinessConcept
from app.models.tag import Tag
from app.schemas.ai import (
    ConceptSuggestion,
    ConfidenceTag,
    ImageAnalysisResult,
    ImageSemanticProfile,
)
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

    added_phrase = client.post(
        f"/api/business-concepts/{concept['id']}/search-phrases",
        headers=headers,
        json={
            "phrase": "课程跟学校进度一致",
            "phraseType": "colloquial",
            "origin": "manual",
        },
    )
    assert added_phrase.status_code == 200
    phrase = added_phrase.json()["searchPhrases"][0]

    updated_phrase = client.patch(
        f"/api/business-concepts/{concept['id']}/search-phrases/{phrase['id']}",
        headers=headers,
        json={
            "phrase": "课程内容跟学校进度一致",
            "reviewStatus": "rejected",
            "weight": 0.9,
        },
    )
    assert updated_phrase.status_code == 200
    updated = updated_phrase.json()["searchPhrases"][0]
    assert updated["phrase"] == "课程内容跟学校进度一致"
    assert updated["reviewStatus"] == "rejected"
    assert updated["weight"] == 0.9
    assert updated_phrase.json()["version"] == 4

    seeded_phrases = client.post(
        f"/api/business-concepts/{concept['id']}/search-phrases",
        headers=headers,
        json={
            "phrase": "初始资料中的固定说法",
            "phraseType": "official",
            "origin": "source_document",
        },
    ).json()["searchPhrases"]
    seeded_phrase = next(
        item for item in seeded_phrases if item["phrase"] == "初始资料中的固定说法"
    )
    immutable = client.patch(
        f"/api/business-concepts/{concept['id']}/search-phrases/{seeded_phrase['id']}",
        headers=headers,
        json={"phrase": "直接改掉初始资料"},
    )
    assert immutable.status_code == 400


def test_phase2_upload_creates_group_and_derivative_search_is_deduplicated(client):
    csrf = login(client, "admin", "admin-password")
    headers = {"X-CSRF-Token": csrf, "Origin": "http://localhost:5173"}
    uploaded = client.post(
        "/api/images/upload",
        headers=headers,
        files={"file": ("primary.png", png_file(), "image/png")},
        data={
            "title": "素材组去重测试",
            "expectedSearchWords": "蓝色横版素材",
            "autoAnalyze": "false",
        },
    )
    assert uploaded.status_code == 201
    primary = uploaded.json()
    assert primary["assetGroupId"]
    assert primary["width"] == 8
    assert primary["height"] == 4

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
    assert {item["phrase"] for item in group["searchPhrases"]} == {"蓝色横版素材"}

    response = client.post(
        "/api/images/search",
        json={"keyword": "素材组去重测试", "limit": 12},
    )
    assert response.status_code == 200
    assert len(response.json()["results"]) == 1
    assert response.json()["results"][0]["image"]["variantCount"] == 2


def test_phase3_v2_analysis_and_owner_confirmation_survive_rerun(client, db_factory):
    with db_factory() as db:
        system = Tag(
            code="sync_school",
            name="同步校内体系",
            color="#111111",
            node_type="system",
            assignable=False,
            status="active",
        )
        tag = Tag(
            code="animation_explanation",
            name="动画精讲",
            color="#222222",
            parent=system,
            node_type="image_label",
            assignable=True,
            status="active",
        )
        concept = BusinessConcept(
            code="animation_explanation",
            name="动画精讲",
            concept_type="product_function",
        )
        db.add_all([system, tag, concept])
        db.commit()

    class FakeAiService:
        def analyze_image(self, _path):
            return ImageAnalysisResult(
                image_summary="平板界面展示数学动画和分步计算，顶部可见课程标题。",
                semantic_profile=ImageSemanticProfile(
                    visual_facts=["平板学习界面", "数学动画", "分步计算"],
                    ocr_text=["数学精讲", "下一步"],
                    subjects=["平板", "课程界面"],
                    scenes=["居家学习"],
                    actions=["观看动画课程"],
                    visual_style=["蓝色科技风"],
                    visible_product_features=["动画播放", "分步计算"],
                    asset_search_phrases=["蓝色平板动画课画面"],
                    negative_visual_concepts=["真人老师聊天"],
                ),
                content_tags=[
                    ConfidenceTag(tag="平板", confidence=0.95, dimension="物体"),
                    ConfidenceTag(tag="动画播放", confidence=0.92, dimension="产品功能"),
                    ConfidenceTag(tag="数学精讲", confidence=0.9, dimension="文字"),
                ],
                concept_suggestions=[
                    ConceptSuggestion(
                        concept_code="animation_explanation",
                        system_name="同步校内体系",
                        concept_name="动画精讲",
                        confidence=0.94,
                        evidence_level="A",
                        relation_role="expresses",
                        reason="画面展示动画和分步计算，适合动画精讲，不是课后小测。",
                    )
                ],
                recommended_search_words=["平板动画数学课"],
            )

    app.dependency_overrides[dependencies.get_ai_service] = lambda: FakeAiService()
    csrf = login(client, "admin", "admin-password")
    headers = {"X-CSRF-Token": csrf, "Origin": "http://localhost:5173"}
    uploaded = client.post(
        "/api/images/upload",
        headers=headers,
        files={"file": ("analysis.png", png_file(), "image/png")},
        data={
            "title": "V2 分析测试",
            "expectedSearchWords": "负责人手工搜索语",
            "autoAnalyze": "false",
        },
    ).json()

    analyzed = client.post(f"/api/ai/images/{uploaded['id']}/analyze", headers=headers)
    assert analyzed.status_code == 200
    detail = client.get(f"/api/images/{uploaded['id']}").json()
    assert detail["semanticProfile"]["schemaVersion"] == 2
    assert detail["semanticProfile"]["ocrText"] == ["数学精讲", "下一步"]

    group_id = detail["assetGroupId"]
    group = client.get(f"/api/asset-groups/{group_id}").json()
    suggestion = next(item for item in group["conceptLinks"] if item["origin"] == "ai")
    assert suggestion["relationRole"] == "expresses"
    assert suggestion["reviewStatus"] == "pending"

    reviewed = client.patch(
        f"/api/asset-groups/{group_id}/concept-links/{suggestion['id']}",
        headers=headers,
        json={"reviewStatus": "accepted", "relationRole": "expresses"},
    )
    assert reviewed.status_code == 200
    assert any(
        item["origin"] == "manual"
        and item["reviewStatus"] == "accepted"
        and item["conceptCode"] == "animation_explanation"
        for item in reviewed.json()["conceptLinks"]
    )

    rerun = client.post(f"/api/ai/images/{uploaded['id']}/analyze", headers=headers)
    assert rerun.status_code == 200
    after = client.get(f"/api/asset-groups/{group_id}").json()
    assert len(
        [
            item
            for item in after["conceptLinks"]
            if item["origin"] == "manual"
            and item["conceptCode"] == "animation_explanation"
        ]
    ) == 1
    assert "负责人手工搜索语" in {
        item["phrase"]
        for item in after["searchPhrases"]
        if item["origin"] == "manual" and item["reviewStatus"] == "accepted"
    }
