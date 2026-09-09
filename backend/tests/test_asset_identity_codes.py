from io import BytesIO

from PIL import Image as PillowImage

from app.services.asset_identity_service import extract_identity_code
from tests.conftest import login


def png_file(color: str = "blue") -> bytes:
    output = BytesIO()
    PillowImage.new("RGB", (8, 4), color).save(output, format="PNG")
    return output.getvalue()


def test_identity_code_parser_accepts_only_single_image_codes():
    assert extract_identity_code("PC-8F4K2M") == "PC-8F4K2M"
    assert extract_identity_code("https://example.test/image/PC-8F4K2M") == "PC-8F4K2M"
    assert extract_identity_code("https://example.test/find?code=PC-8F4K2M") == "PC-8F4K2M"
    assert extract_identity_code("PC-8F4K2M-V03") is None
    assert extract_identity_code("PC-8F4K2O") is None


def test_each_image_gets_one_code_and_delete_removes_it(client):
    csrf = login(client, "admin", "admin-password")
    headers = {"X-CSRF-Token": csrf, "Origin": "http://localhost:5173"}
    uploaded = client.post(
        "/api/images/upload",
        headers=headers,
        files={"file": ("primary.png", png_file(), "image/png")},
        data={"title": "身份码主图", "channel": "PPT", "autoAnalyze": "false"},
    )
    assert uploaded.status_code == 201
    image = uploaded.json()
    assert image["identityCode"].startswith("PC-")
    assert "assetCode" not in image
    assert "versionCode" not in image
    assert "sharePath" not in image

    identity_search = client.post(
        "/api/images/search",
        headers=headers,
        json={"keyword": image["identityCode"]},
    )
    assert identity_search.status_code == 200
    assert identity_search.json()["exactMatch"] is True
    assert identity_search.json()["identityCode"] == image["identityCode"]
    assert identity_search.json()["results"][0]["image"]["id"] == image["id"]

    variant = client.post(
        f"/api/asset-groups/{image['assetGroupId']}/images",
        headers=headers,
        files={"file": ("variant.png", png_file("green"), "image/png")},
        data={"title": "身份码延展", "assetRole": "derivative", "autoAnalyze": "false"},
    )
    assert variant.status_code == 201
    variant_image = max(variant.json()["images"], key=lambda item: item["versionNo"])
    assert variant_image["identityCode"].startswith("PC-")
    assert variant_image["identityCode"] != image["identityCode"]

    deleted_code = image["identityCode"]
    assert client.delete(f"/api/images/{image['id']}", headers=headers).status_code == 204
    missing = client.post(
        "/api/images/search",
        headers=headers,
        json={"keyword": deleted_code},
    )
    assert missing.status_code == 200
    assert missing.json()["results"] == []

    restored = client.post(f"/api/images/{image['id']}/restore", headers=headers)
    assert restored.status_code == 200
    assert restored.json()["identityCode"].startswith("PC-")
    assert restored.json()["identityCode"] != deleted_code


def test_admin_lists_only_codes_for_active_images(client):
    admin_csrf = login(client, "admin", "admin-password")
    admin_headers = {
        "X-CSRF-Token": admin_csrf,
        "Origin": "http://localhost:5173",
    }
    uploaded = client.post(
        "/api/images/upload",
        headers=admin_headers,
        files={"file": ("ledger.png", png_file(), "image/png")},
        data={"title": "身份码素材", "channel": "PPT", "autoAnalyze": "false"},
    )
    assert uploaded.status_code == 201
    image = uploaded.json()

    listing = client.get("/api/admin/identity-codes", headers=admin_headers)
    assert listing.status_code == 200
    body = listing.json()
    assert body["total"] == 1
    assert body["summary"] == {"imageTotal": 1}
    assert body["items"][0]["code"] == image["identityCode"]
    assert body["items"][0]["imageId"] == image["id"]

    assert client.delete(f"/api/images/{image['id']}", headers=admin_headers).status_code == 204
    after_delete = client.get("/api/admin/identity-codes", headers=admin_headers)
    assert after_delete.status_code == 200
    assert after_delete.json()["total"] == 0
    assert after_delete.json()["items"] == []

    business_csrf = login(client, "business", "business-password")
    denied = client.get(
        "/api/admin/identity-codes",
        headers={
            "X-CSRF-Token": business_csrf,
            "Origin": "http://localhost:5173",
        },
    )
    assert denied.status_code == 403
