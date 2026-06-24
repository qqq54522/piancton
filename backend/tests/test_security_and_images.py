from io import BytesIO

from PIL import Image as PillowImage
from sqlalchemy import select

from app.models.image import ImageTag
from app.models.tag import Tag
from tests.conftest import login


def png_file() -> bytes:
    output = BytesIO()
    PillowImage.new("RGB", (4, 4), "red").save(output, format="PNG")
    return output.getvalue()


def create_leaf_tag(client, headers, name: str = "测试标签") -> dict:
    response = client.post(
        "/api/tags",
        headers=headers,
        json={"name": name, "color": "#3B82F6"},
    )
    assert response.status_code == 201
    return response.json()


def test_requires_authentication(client):
    response = client.get("/api/images")
    assert response.status_code == 401
    assert response.json()["code"] == "unauthorized"


def test_business_cannot_write(client):
    csrf = login(client, "business", "business-password")
    admin_read = client.get("/api/admin/users")
    assert admin_read.status_code == 403
    response = client.post(
        "/api/tags",
        headers={"X-CSRF-Token": csrf, "Origin": "http://localhost:5173"},
        json={"name": "restricted", "color": "#000000"},
    )
    assert response.status_code == 403


def test_upload_preview_download_and_validation(client):
    csrf = login(client, "admin", "admin-password")
    headers = {"X-CSRF-Token": csrf, "Origin": "http://localhost:5173"}
    tag = client.post(
        "/api/tags",
        headers=headers,
        json={"name": "产品", "color": "#3B82F6"},
    ).json()
    invalid = client.post(
        "/api/images/upload",
        headers=headers,
        files={"file": ("fake.png", b"not-an-image", "image/png")},
        data={"title": "fake", "tagIds": tag["id"], "categories": "function"},
    )
    assert invalid.status_code == 415
    uploaded = client.post(
        "/api/images/upload",
        headers=headers,
        files={"file": ("real.png", png_file(), "image/png")},
        data={"title": "real", "tagIds": tag["id"], "categories": "function"},
    )
    assert uploaded.status_code == 201
    image = uploaded.json()
    assert "filePath" not in image
    assert image["thumbnailUrl"].endswith("/thumbnail")

    thumbnail = client.get(image["thumbnailUrl"])
    assert thumbnail.status_code == 200
    assert thumbnail.headers["content-type"].startswith("image/jpeg")
    preview = client.get(image["contentUrl"])
    assert preview.status_code == 200
    detail = client.get(f"/api/images/{image['id']}").json()
    assert detail["downloadCount"] == 0
    manual_label = next(
        item for item in detail["businessLabels"] if item["origin"] == "manual"
    )
    assert manual_label["tagId"] == tag["id"]
    assert manual_label["role"] == "primary"
    assert manual_label["reviewStatus"] == "accepted"

    download = client.get(image["downloadUrl"])
    assert download.status_code == 200
    detail = client.get(f"/api/images/{image['id']}").json()
    assert detail["downloadCount"] == 1


def test_ai_not_configured_is_explicit(client):
    from app.ai.placeholder import PlaceholderModelProvider
    from app.api import dependencies
    from app.main import app
    from app.services.ai_service import AiService

    app.dependency_overrides[dependencies.get_ai_service] = lambda: AiService(
        PlaceholderModelProvider()
    )
    csrf = login(client, "admin", "admin-password")
    headers = {"X-CSRF-Token": csrf, "Origin": "http://localhost:5173"}
    tag = client.post(
        "/api/tags",
        headers=headers,
        json={"name": "AI", "color": "#3B82F6"},
    ).json()
    image = client.post(
        "/api/images/upload",
        headers=headers,
        files={"file": ("real.png", png_file(), "image/png")},
        data={"title": "real", "tagIds": tag["id"], "categories": "function"},
    ).json()
    response = client.post(f"/api/ai/images/{image['id']}/analyze", headers=headers)
    assert response.status_code == 503
    assert response.json()["code"] == "provider_not_configured"


def test_upload_starts_backend_ai_analysis(client, db_factory):
    from app.api import dependencies
    from app.main import app
    from app.schemas.ai import ProviderStatus
    from app.services.ai_service import AiService

    class Provider:
        name = "fake"

        @property
        def configured(self):
            return True

        def generate_json(self, _request):
            return {
                "image_type": "功能图",
                "image_summary": "上传后自动分析出的图片语义。",
                "content_tags": [
                    {"tag": f"自动标签{index}", "confidence": 0.9, "dimension": "产品功能"}
                    for index in range(1, 19)
                ],
                "secondary_labels": [
                    {
                        "system": "同步校内体系",
                        "label": "动画精讲",
                        "confidence": 0.91,
                        "evidence_level": "A",
                        "role": "primary",
                        "reason": "图片适合动画讲解知识点。",
                    }
                ],
                "recommended_search_words": [],
                "negative_tags": [],
            }

    class FakeAiService(AiService):
        def __init__(self):
            super().__init__(Provider())

        def provider_status(self):
            return ProviderStatus(provider="fake", configured=True, model_name="fake-model")

    app.dependency_overrides[dependencies.get_ai_service] = lambda: FakeAiService()
    csrf = login(client, "admin", "admin-password")
    headers = {"X-CSRF-Token": csrf, "Origin": "http://localhost:5173"}
    with db_factory() as db:
        system = Tag(
            code="sync_school",
            name="同步校内体系",
            color="#6366F1",
            node_type="system",
            assignable=False,
            status="active",
        )
        db.add(system)
        db.flush()
        db.add(
            Tag(
                code="animation_explanation",
                name="动画精讲",
                color="#818CF8",
                parent_id=system.id,
                is_secondary=True,
                node_type="image_label",
                assignable=True,
                status="active",
            )
        )
        db.commit()

    tag = create_leaf_tag(client, headers, "自动分析")
    uploaded = client.post(
        "/api/images/upload",
        headers=headers,
        files={"file": ("auto.png", png_file(), "image/png")},
        data={"title": "auto", "tagIds": tag["id"], "categories": "function"},
    )
    assert uploaded.status_code == 201
    detail = client.get(f"/api/images/{uploaded.json()['id']}").json()
    assert detail["analysisRuns"][0]["status"] == "succeeded"
    assert detail["imageSummary"] == "上传后自动分析出的图片语义。"
    assert len(detail["contentTags"]) == 18
    assert any(
        item["origin"] == "ai" and item["labelCode"] == "animation_explanation"
        for item in detail["businessLabels"]
    )


def test_ai_analysis_is_persisted_to_image_detail(client, db_factory):
    from app.api import dependencies
    from app.main import app
    from app.schemas.ai import ConfidenceTag, ImageAnalysisResult, SecondaryLabel

    class FakeAiService:
        def analyze_image(self, _path):
            return ImageAnalysisResult(
                image_type="function",
                image_summary="一个展示动画讲解知识点的功能图。",
                content_tags=[
                    ConfidenceTag(tag="动画讲解", confidence=0.92, dimension="产品功能"),
                    ConfidenceTag(tag="知识点", confidence=0.88, dimension="文本"),
                ],
                secondary_labels=[
                    SecondaryLabel(
                        system="同步校内体系",
                        label="动画精讲",
                        confidence=0.91,
                        evidence_level="A",
                        role="primary",
                        reason="图片标题和内容指向动画讲透知识点。",
                    )
                ],
                recommended_search_words=["动画讲解", "知识点"],
                negative_tags=[],
            )

    app.dependency_overrides[dependencies.get_ai_service] = lambda: FakeAiService()
    csrf = login(client, "admin", "admin-password")
    headers = {"X-CSRF-Token": csrf, "Origin": "http://localhost:5173"}
    with db_factory() as db:
        system = Tag(
            code="sync_school",
            name="同步校内体系",
            color="#6366F1",
            node_type="system",
            assignable=False,
            status="active",
        )
        db.add(system)
        db.flush()
        db.add(
            Tag(
                code="animation_explanation",
                name="动画精讲",
                color="#818CF8",
                parent_id=system.id,
                is_secondary=True,
                node_type="image_label",
                assignable=True,
                status="active",
            )
        )
        db.commit()
    tag = create_leaf_tag(client, headers, "AI 持久化")
    image = client.post(
        "/api/images/upload",
        headers=headers,
        files={"file": ("real.png", png_file(), "image/png")},
        data={"title": "real", "tagIds": tag["id"], "categories": "function"},
    ).json()

    response = client.post(f"/api/ai/images/{image['id']}/analyze", headers=headers)
    assert response.status_code == 200
    detail = client.get(f"/api/images/{image['id']}").json()
    assert detail["imageSummary"] == "一个展示动画讲解知识点的功能图。"
    assert [item["tagName"] for item in detail["contentTags"]] == ["动画讲解", "知识点"]
    assert detail["level2Categories"][0]["categoryName"] == "同步校内体系 > 动画精讲"
    ai_label = next(item for item in detail["businessLabels"] if item["origin"] == "ai")
    assert ai_label["labelCode"] == "animation_explanation"
    assert ai_label["reviewStatus"] == "pending"

    accepted = client.patch(
        f"/api/images/{image['id']}/business-labels/{ai_label['id']}",
        headers=headers,
        json={"reviewStatus": "accepted"},
    )
    assert accepted.status_code == 200
    accepted_label = next(
        item for item in accepted.json()["businessLabels"] if item["id"] == ai_label["id"]
    )
    assert accepted_label["reviewStatus"] == "accepted"
    promoted_manual = next(
        item
        for item in accepted.json()["businessLabels"]
        if item["origin"] == "manual" and item["labelCode"] == "animation_explanation"
    )
    assert promoted_manual["role"] == "additional"
    assert promoted_manual["reviewStatus"] == "accepted"
    assert any(tag["name"] == "动画精讲" for tag in accepted.json()["tags"])

    rerun = client.post(f"/api/ai/images/{image['id']}/analyze", headers=headers)
    assert rerun.status_code == 200
    detail_after_rerun = client.get(f"/api/images/{image['id']}").json()
    ai_animation_labels = [
        item
        for item in detail_after_rerun["businessLabels"]
        if item["origin"] == "ai" and item["labelCode"] == "animation_explanation"
    ]
    assert len(ai_animation_labels) == 1
    assert ai_animation_labels[0]["reviewStatus"] == "accepted"
    assert not [
        item
        for item in ai_animation_labels
        if item["reviewStatus"] == "pending"
    ]

    rejected = client.patch(
        f"/api/images/{image['id']}/business-labels/{ai_label['id']}",
        headers=headers,
        json={"reviewStatus": "rejected"},
    )
    assert rejected.status_code == 200
    rejected_label = next(
        item for item in rejected.json()["businessLabels"] if item["id"] == ai_label["id"]
    )
    assert rejected_label["reviewStatus"] == "rejected"

    manual_label = next(
        item for item in rejected.json()["businessLabels"] if item["origin"] == "manual"
    )
    manual_review = client.patch(
        f"/api/images/{image['id']}/business-labels/{manual_label['id']}",
        headers=headers,
        json={"reviewStatus": "rejected"},
    )
    assert manual_review.status_code == 400
    assert manual_review.json()["code"] == "manual_label_not_reviewable"


def test_ai_analysis_accepts_string_secondary_labels(client):
    from app.api import dependencies
    from app.main import app

    class FakeAiService:
        def analyze_image(self, _path):
            from app.services.ai_service import AiService

            class Provider:
                name = "fake"

                @property
                def configured(self):
                    return True

                def generate_json(self, _request):
                    return {
                        "image_type": "功能图",
                        "image_summary": "动画讲解知识点。",
                        "content_tags": [
                            f"动画讲解标签{index}" for index in range(1, 19)
                        ],
                        "secondary_labels": [
                            "同步校内体系 > 动画精讲",
                            "同步培养体系 > 万能解法",
                        ],
                        "recommended_search_words": [],
                        "negative_tags": [],
                    }

            return AiService(Provider()).analyze_image(_path)

    app.dependency_overrides[dependencies.get_ai_service] = lambda: FakeAiService()
    csrf = login(client, "admin", "admin-password")
    headers = {"X-CSRF-Token": csrf, "Origin": "http://localhost:5173"}
    tag = create_leaf_tag(client, headers, "AI 字符串标签")
    image = client.post(
        "/api/images/upload",
        headers=headers,
        files={"file": ("real.png", png_file(), "image/png")},
        data={"title": "real", "tagIds": tag["id"], "categories": "function"},
    ).json()

    response = client.post(f"/api/ai/images/{image['id']}/analyze", headers=headers)
    assert response.status_code == 200
    detail = client.get(f"/api/images/{image['id']}").json()
    assert detail["contentTags"][0]["tagName"] == "动画讲解标签1"
    assert [item["categoryName"] for item in detail["level2Categories"]] == [
        "同步校内体系 > 动画精讲",
        "同步培养体系 > 万能解法",
    ]


def test_upload_size_limit(client, monkeypatch):
    from app.api import dependencies

    csrf = login(client, "admin", "admin-password")
    headers = {"X-CSRF-Token": csrf, "Origin": "http://localhost:5173"}
    tag = create_leaf_tag(client, headers, "上传限制")
    monkeypatch.setattr(dependencies.settings, "max_upload_bytes", 16)
    response = client.post(
        "/api/images/upload",
        headers=headers,
        files={"file": ("large.png", png_file(), "image/png")},
        data={"title": "large", "tagIds": tag["id"], "categories": "function"},
    )
    assert response.status_code == 413
    assert response.json()["code"] == "upload_too_large"


def test_tag_cycle_and_unknown_image_tags_are_rejected(client):
    csrf = login(client, "admin", "admin-password")
    headers = {"X-CSRF-Token": csrf, "Origin": "http://localhost:5173"}
    parent = client.post(
        "/api/tags",
        headers=headers,
        json={"name": "parent", "color": "#111111"},
    ).json()
    child = client.post(
        "/api/tags",
        headers=headers,
        json={"name": "child", "color": "#222222", "parentId": parent["id"]},
    ).json()
    cycle = client.patch(
        f"/api/tags/{parent['id']}",
        headers=headers,
        json={"parentId": child["id"]},
    )
    assert cycle.status_code == 400
    assert cycle.json()["code"] == "tag_cycle"

    upload = client.post(
        "/api/images/upload",
        headers=headers,
        files={"file": ("real.png", png_file(), "image/png")},
        data={"title": "real", "tagIds": "missing-tag", "categories": "function"},
    )
    assert upload.status_code == 400
    assert upload.json()["code"] == "unknown_tags"


def test_assignable_parent_remains_valid_after_children_are_added(client):
    csrf = login(client, "admin", "admin-password")
    headers = {"X-CSRF-Token": csrf, "Origin": "http://localhost:5173"}
    parent = client.post(
        "/api/tags",
        headers=headers,
        json={"name": "体系", "color": "#111111"},
    ).json()
    child = client.post(
        "/api/tags",
        headers=headers,
        json={"name": "叶子标签", "color": "#222222", "parentId": parent["id"]},
    ).json()

    parent_upload = client.post(
        "/api/images/upload",
        headers=headers,
        files={"file": ("parent.png", png_file(), "image/png")},
        data={"title": "parent-image", "tagIds": parent["id"], "categories": "function"},
    )
    assert parent_upload.status_code == 201

    no_tag_upload = client.post(
        "/api/images/upload",
        headers=headers,
        files={"file": ("untagged.png", png_file(), "image/png")},
        data={"title": "untagged", "tagIds": "", "categories": "function"},
    )
    assert no_tag_upload.status_code == 400
    assert no_tag_upload.json()["code"] == "image_tag_required"

    child_upload = client.post(
        "/api/images/upload",
        headers=headers,
        files={"file": ("child.png", png_file(), "image/png")},
        data={"title": "child-image", "tagIds": child["id"], "categories": "function"},
    )
    assert child_upload.status_code == 201
    empty_update = client.patch(
        f"/api/images/{child_upload.json()['id']}/tags",
        headers=headers,
        json={"tagIds": []},
    )
    assert empty_update.status_code == 400
    assert empty_update.json()["code"] == "image_tag_required"

    tags = client.get("/api/tags").json()
    assert next(item for item in tags if item["id"] == child["id"])["imageCount"] == 1
    assert next(item for item in tags if item["id"] == parent["id"])["imageCount"] == 2


def test_deleting_tag_subtree_is_blocked_while_images_still_use_it(client):
    csrf = login(client, "admin", "admin-password")
    headers = {"X-CSRF-Token": csrf, "Origin": "http://localhost:5173"}
    parent = client.post(
        "/api/tags",
        headers=headers,
        json={"name": "父标签", "color": "#111111"},
    ).json()
    child = client.post(
        "/api/tags",
        headers=headers,
        json={"name": "子标签", "color": "#222222", "parentId": parent["id"]},
    ).json()
    child_image = client.post(
        "/api/images/upload",
        headers=headers,
        files={"file": ("child.png", png_file(), "image/png")},
        data={"title": "child-image", "tagIds": child["id"], "categories": "function"},
    ).json()

    impact = client.get(f"/api/tags/{parent['id']}/delete-impact")
    assert impact.status_code == 200
    assert impact.json()["subtreeTagCount"] == 2
    assert impact.json()["directChildCount"] == 1
    assert impact.json()["affectedImageCount"] == 1

    deleted = client.delete(f"/api/tags/{parent['id']}", headers=headers)
    assert deleted.status_code == 409
    assert deleted.json()["code"] == "tag_in_use"
    assert client.get(f"/api/images/{child_image['id']}").status_code == 200
    tag_ids = {item["id"] for item in client.get("/api/tags").json()}
    assert parent["id"] in tag_ids
    assert child["id"] in tag_ids


def test_tag_counts_ignore_deleted_images(client):
    csrf = login(client, "admin", "admin-password")
    headers = {"X-CSRF-Token": csrf, "Origin": "http://localhost:5173"}
    tag = client.post(
        "/api/tags",
        headers=headers,
        json={"name": "计数标签", "color": "#111111"},
    ).json()
    image = client.post(
        "/api/images/upload",
        headers=headers,
        files={"file": ("count.png", png_file(), "image/png")},
        data={"title": "count-image", "tagIds": tag["id"], "categories": "function"},
    ).json()
    tags = client.get("/api/tags").json()
    assert next(item for item in tags if item["id"] == tag["id"])["imageCount"] == 1

    deleted = client.delete(f"/api/images/{image['id']}", headers=headers)
    assert deleted.status_code == 204
    tags = client.get("/api/tags").json()
    assert next(item for item in tags if item["id"] == tag["id"])["imageCount"] == 0


def test_disabling_user_invalidates_existing_session(client):
    business_csrf = login(client, "business", "business-password")
    assert business_csrf
    business_session = client.cookies.get("piancton_session")

    admin_csrf = login(client, "admin", "admin-password")
    headers = {"X-CSRF-Token": admin_csrf, "Origin": "http://localhost:5173"}
    users = client.get("/api/admin/users").json()
    business = next(user for user in users if user["username"] == "business")
    disabled = client.patch(
        f"/api/admin/users/{business['id']}",
        headers=headers,
        json={"isActive": False},
    )
    assert disabled.status_code == 200

    client.cookies.clear()
    client.cookies.set("piancton_session", business_session)
    response = client.get("/api/auth/me")
    assert response.status_code == 401


def test_cursor_pagination_is_stable_for_both_sorts(client):
    csrf = login(client, "admin", "admin-password")
    headers = {"X-CSRF-Token": csrf, "Origin": "http://localhost:5173"}
    tag = create_leaf_tag(client, headers, "分页标签")
    for index in range(5):
        response = client.post(
            "/api/images/upload",
            headers=headers,
            files={"file": (f"{index}.png", png_file(), "image/png")},
            data={
                "title": f"image-{index}",
                "tagIds": tag["id"],
                "categories": "function",
            },
        )
        assert response.status_code == 201

    for sort_by in ("createdAt", "downloadCount"):
        seen: list[str] = []
        cursor = None
        while True:
            response = client.get(
                "/api/images",
                params={"limit": 2, "sortBy": sort_by, "cursor": cursor},
            )
            assert response.status_code == 200
            page = response.json()
            seen.extend(item["id"] for item in page["items"])
            if not page["hasMore"]:
                break
            cursor = page["nextCursor"]
        assert len(seen) == 5
        assert len(set(seen)) == 5


def test_login_rate_limit_and_security_headers(client, monkeypatch):
    from app.api import dependencies

    monkeypatch.setattr(dependencies.settings, "login_max_attempts", 2)
    for _ in range(2):
        response = client.post(
            "/api/auth/login",
            json={"username": "admin", "password": "incorrect-password"},
        )
        assert response.status_code == 401
    limited = client.post(
        "/api/auth/login",
        json={"username": "admin", "password": "incorrect-password"},
    )
    assert limited.status_code == 429
    assert limited.json()["code"] == "login_rate_limited"
    assert limited.headers["x-content-type-options"] == "nosniff"
    assert limited.headers["x-frame-options"] == "DENY"
    assert limited.headers["x-request-id"]


def test_sibling_tag_uniqueness_allows_same_name_in_other_branches(client):
    csrf = login(client, "admin", "admin-password")
    headers = {"X-CSRF-Token": csrf, "Origin": "http://localhost:5173"}
    parent_ids = []
    for name in ("A", "B"):
        parent_ids.append(
            client.post(
                "/api/tags",
                headers=headers,
                json={"name": name, "color": "#111111"},
            ).json()["id"]
        )
    for parent_id in parent_ids:
        response = client.post(
            "/api/tags",
            headers=headers,
            json={"name": "同名子标签", "color": "#222222", "parentId": parent_id},
        )
        assert response.status_code == 201
    duplicate = client.post(
        "/api/tags",
        headers=headers,
        json={"name": "同名子标签", "color": "#333333", "parentId": parent_ids[0]},
    )
    assert duplicate.status_code == 409


def test_recycle_bin_restore_purge_and_audit_log(client):
    csrf = login(client, "admin", "admin-password")
    headers = {"X-CSRF-Token": csrf, "Origin": "http://localhost:5173"}
    tag = create_leaf_tag(client, headers, "回收站标签")
    image = client.post(
        "/api/images/upload",
        headers=headers,
        files={"file": ("real.png", png_file(), "image/png")},
        data={"title": "trash-me", "tagIds": tag["id"], "categories": "function"},
    ).json()

    deleted = client.delete(f"/api/images/{image['id']}", headers=headers)
    assert deleted.status_code == 204
    assert client.get(f"/api/images/{image['id']}").status_code == 404
    trash = client.get("/api/images/trash").json()
    assert [item["id"] for item in trash] == [image["id"]]

    restored = client.post(f"/api/images/{image['id']}/restore", headers=headers)
    assert restored.status_code == 200
    assert client.get(f"/api/images/{image['id']}").status_code == 200

    client.delete(f"/api/images/{image['id']}", headers=headers)
    purged = client.delete(f"/api/images/{image['id']}/purge", headers=headers)
    assert purged.status_code == 204
    assert client.get("/api/images/trash").json() == []

    logs = client.get("/api/admin/users/audit-logs").json()
    actions = {entry["action"] for entry in logs}
    assert {"auth.login", "image.upload", "image.trash", "image.restore", "image.purge"} <= actions


def test_restore_prunes_legacy_non_leaf_tag_links(client, db_factory):
    csrf = login(client, "admin", "admin-password")
    headers = {"X-CSRF-Token": csrf, "Origin": "http://localhost:5173"}
    parent = client.post(
        "/api/tags",
        headers=headers,
        json={"name": "旧体系", "color": "#111111"},
    ).json()
    child = client.post(
        "/api/tags",
        headers=headers,
        json={"name": "旧叶子", "color": "#222222", "parentId": parent["id"]},
    ).json()
    image = client.post(
        "/api/images/upload",
        headers=headers,
        files={"file": ("real.png", png_file(), "image/png")},
        data={"title": "legacy-trash", "tagIds": child["id"], "categories": "function"},
    ).json()
    assert client.delete(f"/api/images/{image['id']}", headers=headers).status_code == 204

    with db_factory() as db:
        legacy_parent = db.get(Tag, parent["id"])
        assert legacy_parent is not None
        legacy_parent.assignable = False
        db.add(ImageTag(image_id=image["id"], tag_id=parent["id"]))
        db.commit()

    restored = client.post(f"/api/images/{image['id']}/restore", headers=headers)
    assert restored.status_code == 200
    assert [tag["id"] for tag in restored.json()["tags"]] == [child["id"]]

    with db_factory() as db:
        tag_ids = list(
            db.scalars(select(ImageTag.tag_id).where(ImageTag.image_id == image["id"])).all()
        )
    assert tag_ids == [child["id"]]


def test_liveness_and_readiness(client):
    assert client.get("/health/live").json()["status"] == "ok"
    assert client.get("/health/ready").json()["status"] == "ready"


def test_multiple_tag_filter_uses_and_semantics(client):
    csrf = login(client, "admin", "admin-password")
    headers = {"X-CSRF-Token": csrf, "Origin": "http://localhost:5173"}
    tags = [
        client.post(
            "/api/tags",
            headers=headers,
            json={"name": name, "color": "#111111"},
        ).json()
        for name in ("标签一", "标签二")
    ]
    both = client.post(
        "/api/images/upload",
        headers=headers,
        files={"file": ("both.png", png_file(), "image/png")},
        data={
            "title": "both",
            "tagIds": ",".join(tag["id"] for tag in tags),
            "categories": "function",
        },
    ).json()
    client.post(
        "/api/images/upload",
        headers=headers,
        files={"file": ("one.png", png_file(), "image/png")},
        data={"title": "one", "tagIds": tags[0]["id"], "categories": "function"},
    )
    response = client.get(
        "/api/images",
        params={"tagIds": ",".join(tag["id"] for tag in tags)},
    )
    assert [item["id"] for item in response.json()["items"]] == [both["id"]]
