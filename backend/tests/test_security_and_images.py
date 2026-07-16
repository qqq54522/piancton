from io import BytesIO

from PIL import Image as PillowImage

from app.api import dependencies
from app.main import app
from app.models.business_concept import BusinessConcept
from app.models.tag import Tag
from app.schemas.ai import ProviderStatus
from app.services.ai_service import AiService
from tests.conftest import login


def png_file(width: int = 8, height: int = 4) -> bytes:
    output = BytesIO()
    PillowImage.new("RGB", (width, height), "red").save(output, format="PNG")
    return output.getvalue()


def admin_headers(client) -> dict[str, str]:
    csrf = login(client, "admin", "admin-password")
    return {"X-CSRF-Token": csrf, "Origin": "http://localhost:5173"}


def upload(client, headers, title: str = "real") -> dict:
    response = client.post(
        "/api/images/upload",
        headers=headers,
        files={"file": (f"{title}.png", png_file(), "image/png")},
        data={"title": title, "autoAnalyze": "false"},
    )
    assert response.status_code == 201
    return response.json()


def test_requires_authentication(client):
    response = client.get("/api/images")
    assert response.status_code == 401
    assert response.json()["code"] == "unauthorized"


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
        data={"title": "fake", "autoAnalyze": "false"},
    )
    assert invalid.status_code == 415

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


def test_unified_search_log_has_no_requested_mode(client):
    headers = admin_headers(client)
    upload(client, headers, "搜索运营测试图")

    search = client.post(
        "/api/images/search",
        json={"keyword": "搜索运营测试图", "limit": 12},
    )
    assert search.status_code == 200
    body = search.json()
    assert body["results"]
    assert body["searchLogId"]

    summary = client.get("/api/admin/search-ops/summary")
    assert summary.status_code == 200
    data = summary.json()
    assert data["totalSearches"] == 1
    assert "preciseSearchCount" not in data
    assert "smartSearchCount" not in data
    assert "requestedMode" not in data["recentLogs"][0]
    assert data["recentLogs"][0]["servedMode"] == "fuzzy"


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

    class Provider:
        name = "fake"
        configured = True

        def generate_json(self, _request):
            return {
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
        data={"title": "large", "autoAnalyze": "false"},
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
