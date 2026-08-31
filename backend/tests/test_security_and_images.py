from datetime import datetime, timedelta, timezone
from io import BytesIO

from PIL import Image as PillowImage

from app.ai.contracts import ModelCallResult
from app.api import dependencies
from app.core.security import hash_secret
from app.main import app
from app.models.business_concept import BusinessConcept
from app.models.tag import Tag
from app.models.user import LoginThrottle
from app.schemas.ai import ProviderStatus
from app.services.ai_service import AiService
from tests.conftest import ModelProviderStub, login


def png_file(width: int = 8, height: int = 4) -> bytes:
    output = BytesIO()
    PillowImage.new("RGB", (width, height), "red").save(output, format="PNG")
    return output.getvalue()


def admin_headers(client) -> dict[str, str]:
    csrf = login(client, "admin", "admin-password")
    return {"X-CSRF-Token": csrf, "Origin": "http://localhost:5173"}


def designer_headers(client) -> dict[str, str]:
    csrf = login(client, "designer", "designer-password")
    return {"X-CSRF-Token": csrf, "Origin": "http://localhost:5173"}


def upload(client, headers, title: str = "real") -> dict:
    response = client.post(
        "/api/images/upload",
        headers=headers,
        files={"file": (f"{title}.png", png_file(), "image/png")},
        data={"title": title, "channel": "PPT", "autoAnalyze": "false"},
    )
    assert response.status_code == 201
    return response.json()


def test_requires_authentication(client):
    response = client.get("/api/images")
    assert response.status_code == 401
    assert response.json()["code"] == "unauthorized"


def test_expired_login_throttle_does_not_turn_bad_password_into_500(client, db_factory):
    with db_factory() as db:
        db.add(
            LoginThrottle(
                key=hash_secret("business|testclient"),
                attempts=1,
                window_started_at=datetime.now(timezone.utc) - timedelta(hours=2),
            )
        )
        db.commit()

    response = client.post(
        "/api/auth/login",
        json={"username": "business", "password": "wrong-password"},
    )

    assert response.status_code == 401
    assert response.json()["code"] == "unauthorized"


def test_same_forwarded_host_origin_is_trusted_for_csrf(client):
    csrf = login(client, "business", "business-password")

    response = client.post(
        "/api/usage/page-view",
        headers={
            "X-CSRF-Token": csrf,
            "Origin": "http://192.168.1.5",
            "X-Forwarded-Host": "192.168.1.5",
            "X-Forwarded-Proto": "http",
        },
        json={"path": "/", "title": "素材库"},
    )

    assert response.status_code == 204


def test_mismatched_external_origin_is_rejected_for_csrf(client):
    csrf = login(client, "business", "business-password")

    response = client.post(
        "/api/usage/page-view",
        headers={
            "X-CSRF-Token": csrf,
            "Origin": "https://example.invalid",
            "X-Forwarded-Host": "192.168.1.5",
            "X-Forwarded-Proto": "http",
        },
        json={"path": "/", "title": "素材库"},
    )

    assert response.status_code == 403
    assert response.json()["message"] == "请求来源不受信任"


def test_business_cannot_write_and_tag_catalog_is_read_only(client):
    login(client, "business", "business-password")
    assert client.get("/api/admin/users").status_code == 403
    response = client.post(
        "/api/tags",
        headers={"X-CSRF-Token": "invalid", "Origin": "http://localhost:5173"},
        json={"name": "restricted", "color": "#000000"},
    )
    assert response.status_code == 405


def test_upload_preview_download_and_phase6_detail_contract(client):
    headers = admin_headers(client)
    invalid = client.post(
        "/api/images/upload",
        headers=headers,
        files={"file": ("fake.png", b"not-an-image", "image/png")},
        data={"title": "fake", "channel": "PPT", "autoAnalyze": "false"},
    )
    assert invalid.status_code == 415

    missing_channel = client.post(
        "/api/images/upload",
        headers=headers,
        files={"file": ("missing-channel.png", png_file(), "image/png")},
        data={"title": "missing channel", "autoAnalyze": "false"},
    )
    assert missing_channel.status_code == 422
    assert missing_channel.json()["detail"]["code"] == "channel_required"

    image = upload(client, headers)
    assert image["assetGroupId"]
    assert image["width"] == 8
    assert image["height"] == 4
    assert "tags" not in image
    assert "categories" not in image

    thumbnail = client.get(image["thumbnailUrl"])
    assert thumbnail.status_code == 200
    assert thumbnail.headers["content-type"].startswith("image/jpeg")
    assert client.get(image["contentUrl"]).status_code == 200

    detail = client.get(f"/api/images/{image['id']}").json()
    assert detail["downloadCount"] == 0
    assert "businessLabels" not in detail
    assert "level2Categories" not in detail
    assert "tags" not in detail

    assert client.get(image["downloadUrl"]).status_code == 200
    assert client.get(f"/api/images/{image['id']}").json()["downloadCount"] == 1


def test_global_duplicate_titles_are_previewed_and_numbered_even_in_trash(client):
    headers = admin_headers(client)
    first = upload(client, headers, "AI私教")

    preview = client.get(
        "/api/images/title-resolution",
        params={"title": "AI私教"},
    )
    assert preview.status_code == 200
    assert preview.json() == {
        "requestedTitle": "AI私教",
        "resolvedTitle": "AI私教001",
        "changed": True,
    }

    second = upload(client, headers, "AI私教")
    third = upload(client, headers, "AI私教001")
    different = upload(client, headers, "私教答疑")
    assert second["title"] == "AI私教001"
    assert third["title"] == "AI私教002"
    assert different["title"] == "私教答疑"

    deleted = client.delete(f"/api/images/{third['id']}", headers=headers)
    assert deleted.status_code == 204
    after_delete = client.get(
        "/api/images/title-resolution",
        params={"title": "AI私教"},
    )
    assert after_delete.json()["resolvedTitle"] == "AI私教003"

    purged = client.delete(f"/api/images/{third['id']}/purge", headers=headers)
    assert purged.status_code == 204
    after_purge = client.get(
        "/api/images/title-resolution",
        params={"title": "AI私教"},
    )
    assert after_purge.json()["resolvedTitle"] == "AI私教003"
    assert first["title"] == "AI私教"


def test_renaming_a_primary_image_auto_numbers_and_keeps_group_title_in_sync(client):
    headers = admin_headers(client)
    upload(client, headers, "专家规划")
    image = upload(client, headers, "临时名称")

    renamed = client.patch(
        f"/api/images/{image['id']}/title",
        headers=headers,
        json={"title": "专家规划"},
    )
    assert renamed.status_code == 200
    assert renamed.json()["title"] == "专家规划001"

    group = client.get(f"/api/asset-groups/{image['assetGroupId']}")
    assert group.status_code == 200
    assert group.json()["title"] == "专家规划001"


def test_unified_search_log_has_no_requested_mode(client):
    headers = admin_headers(client)
    image = upload(client, headers, "搜索运营测试图")

    search = client.post(
        "/api/images/search",
        json={"keyword": "搜索运营测试图", "limit": 12},
    )
    assert search.status_code == 200
    body = search.json()
    assert body["results"]
    assert body["searchLogId"]
    source_link = client.post(
        f"/api/asset-groups/{body['results'][0]['assetGroupId']}/source-links",
        headers=headers,
        json={
            "label": "Figma 主文件",
            "url": "https://www.figma.com/file/search-ops-test",
            "linkType": "figma",
        },
    )
    assert source_link.status_code == 200

    summary = client.get("/api/admin/search-ops/summary")
    assert summary.status_code == 200
    data = summary.json()
    assert data["totalSearches"] == 1
    assert "preciseSearchCount" not in data
    assert "smartSearchCount" not in data
    assert "requestedMode" not in data["recentLogs"][0]
    assert data["recentLogs"][0]["servedMode"] == "fuzzy"
    assert data["assetOperations"]["assetGroupCount"] == 1
    assert data["assetOperations"]["imageCount"] == 1
    assert data["assetOperations"]["missingSourceLinkCount"] == 0
    assert data["assetOperations"]["missingBusinessRelationCount"] == 1
    assert data["assetOperations"]["missingSearchPhraseCount"] == 1
    assert data["sourceLinkHealth"]["totalLinks"] == 1
    assert data["sourceLinkHealth"]["groupsWithSourceLinks"] == 1
    assert data["sourceLinkHealth"]["recentLinks"][0]["primaryImageId"] == image["id"]
    assert data["searchPerformance"]["sampleCount"] == 1
    assert data["searchPerformance"]["p95DurationMs"] >= 0


def test_search_ops_is_available_to_designer_but_not_business(client):
    designer = designer_headers(client)
    designer_summary = client.get("/api/admin/search-ops/summary", headers=designer)
    assert designer_summary.status_code == 200

    login(client, "business", "business-password")
    business_summary = client.get("/api/admin/search-ops/summary")
    assert business_summary.status_code == 403


def test_ai_not_configured_is_explicit(client):
    from app.ai.placeholder import PlaceholderModelProvider

    app.dependency_overrides[dependencies.get_ai_service] = lambda: AiService(
        PlaceholderModelProvider()
    )
    headers = admin_headers(client)
    image = upload(client, headers)
    response = client.post(f"/api/ai/images/{image['id']}/analyze", headers=headers)
    assert response.status_code == 503
    assert response.json()["code"] == "provider_not_configured"


def test_designer_can_generate_editable_pre_upload_asset_phrases(client):
    captured = {}

    class Provider(ModelProviderStub):
        name = "fake"
        configured = True

        def generate_json(self, request):
            captured["request"] = request
            return ModelCallResult(
                {
                    "phrases": [
                        "找一张能体现和学校教材进度一致的图",
                        "找一张学校学到哪课程就讲到哪的图",
                        "想找一张教材目录和课程目录能对应上的素材",
                        "有没有课外课程不会和学校章节脱节的图",
                    ]
                }
            )

    app.dependency_overrides[
        dependencies.get_asset_phrase_ai_service
    ] = lambda: AiService(Provider())
    headers = admin_headers(client)
    response = client.post(
        "/api/ai/asset-search-phrases",
        headers=headers,
        files={"file": ("course-sync.png", png_file(), "image/png")},
        data={
            "count": "4",
            "title": "课程同步",
            "conceptCode": "school_sync",
        },
    )

    assert response.status_code == 200
    assert response.json()["phrases"] == [
        "找一张能体现和学校教材进度一致的图",
        "找一张学校学到哪课程就讲到哪的图",
        "想找一张教材目录和课程目录能对应上的素材",
        "有没有课外课程不会和学校章节脱节的图",
    ]
    assert captured["request"].task == "asset_search_phrase_generation"
    assert captured["request"].image_media_type == "image/png"
    assert "严格生成数量：4 条" in captured["request"].input_text
    assert "课程版本、章节和学校课堂进度保持一致" in (
        captured["request"].input_text
    )


def test_pre_upload_asset_phrase_count_is_limited_to_two_through_five(client):
    headers = admin_headers(client)
    response = client.post(
        "/api/ai/asset-search-phrases",
        headers=headers,
        files={"file": ("course-sync.png", png_file(), "image/png")},
        data={"count": "1"},
    )

    assert response.status_code == 422


def test_ai_analysis_persists_content_and_new_concept_suggestion(client, db_factory):
    with db_factory() as db:
        db.add_all(
            [
                Tag(
                    code="sync_school",
                    name="同步校内体系",
                    color="#6366F1",
                    node_type="system",
                    assignable=False,
                ),
                BusinessConcept(
                    code="animation_explanation",
                    name="动画精讲",
                ),
            ]
        )
        db.commit()

    class Provider(ModelProviderStub):
        name = "fake"
        configured = True

        def generate_json(self, _request):
            return ModelCallResult(
                {
                    "image_summary": "平板界面展示数学动画和分步计算。",
                    "semantic_profile": {
                        "visual_facts": ["平板学习界面", "数学动画"],
                        "scenes": ["居家学习"],
                        "asset_search_phrases": ["蓝色平板动画课画面"],
                    },
                    "concept_suggestions": [
                        {
                            "concept_code": "animation_explanation",
                            "system_name": "同步校内体系",
                            "concept_name": "动画精讲",
                            "confidence": 0.94,
                            "evidence_level": "A",
                            "relation_role": "expresses",
                            "reason": "画面展示动画和分步计算，适合动画精讲，不是课后小测。",
                        }
                    ],
                }
            )

    class FakeAiService(AiService):
        def __init__(self):
            super().__init__(Provider())

        def provider_status(self):
            return ProviderStatus(provider="fake", configured=True, model_name="fake")

    app.dependency_overrides[dependencies.get_ai_service] = lambda: FakeAiService()
    headers = admin_headers(client)
    image = upload(client, headers, "AI分析")
    response = client.post(f"/api/ai/images/{image['id']}/analyze", headers=headers)
    assert response.status_code == 200

    detail = client.get(f"/api/images/{image['id']}").json()
    assert detail["semanticProfile"]["schemaVersion"] == 3
    assert detail["semanticProfile"]["scenes"] == ["居家学习"]
    assert "contentTags" not in detail
    group = client.get(f"/api/asset-groups/{detail['assetGroupId']}").json()
    suggestion = next(item for item in group["conceptLinks"] if item["origin"] == "ai")
    assert suggestion["conceptCode"] == "animation_explanation"
    assert suggestion["reviewStatus"] == "pending"


def test_upload_size_limit(client, monkeypatch):
    headers = admin_headers(client)
    monkeypatch.setattr(dependencies.settings, "max_upload_bytes", 8)
    response = client.post(
        "/api/images/upload",
        headers=headers,
        files={"file": ("large.png", png_file(), "image/png")},
        data={"title": "large", "channel": "PPT", "autoAnalyze": "false"},
    )
    assert response.status_code == 413


def test_cursor_pagination_is_stable_for_both_sorts(client):
    headers = admin_headers(client)
    for index in range(4):
        upload(client, headers, f"page-{index}")

    for sort_by in ("createdAt", "downloadCount"):
        first = client.get("/api/images", params={"limit": 2, "sortBy": sort_by}).json()
        second = client.get(
            "/api/images",
            params={"limit": 2, "sortBy": sort_by, "cursor": first["nextCursor"]},
        ).json()
        assert len(first["items"]) == 2
        assert len(second["items"]) == 2
        assert {item["id"] for item in first["items"]}.isdisjoint(
            item["id"] for item in second["items"]
        )


def test_recycle_bin_restore_and_purge(client):
    headers = admin_headers(client)
    image = upload(client, headers, "trash-me")
    assert client.delete(f"/api/images/{image['id']}", headers=headers).status_code == 204
    assert {item["id"] for item in client.get("/api/images/trash").json()} == {image["id"]}
    assert client.post(f"/api/images/{image['id']}/restore", headers=headers).status_code == 200
    assert client.delete(f"/api/images/{image['id']}", headers=headers).status_code == 204
    assert client.delete(f"/api/images/{image['id']}/purge", headers=headers).status_code == 204
    assert client.get(f"/api/images/{image['id']}").status_code == 404


def test_liveness_and_readiness(client):
    assert client.get("/health/live").status_code == 200
    assert client.get("/health/ready").status_code == 200
