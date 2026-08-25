from io import BytesIO

from PIL import Image as PillowImage

from app.services.asset_identity_service import extract_identity_code
from tests.conftest import login


def png_file(color: str = "blue") -> bytes:
    output = BytesIO()
    PillowImage.new("RGB", (8, 4), color).save(output, format="PNG")
    return output.getvalue()


def test_identity_code_parser_accepts_codes_and_share_links():
    assert extract_identity_code("PC-8F4K2M") == "PC-8F4K2M"
    assert extract_identity_code("pc-8f4k2m-v03") == "PC-8F4K2M-V03"
    assert extract_identity_code("https://example.test/share/PC-8F4K2M") == "PC-8F4K2M"
    assert (
        extract_identity_code(
            "https://example.test/share?versionCode=PC-8F4K2M-V03"
        )
        == "PC-8F4K2M-V03"
    )
    assert extract_identity_code("PC-8F4K2O") is None


def test_upload_assigns_codes_and_same_search_box_resolves_asset_and_version(client):
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
    assert image["assetCode"].startswith("PC-")
    assert image["versionCode"] == f"{image['assetCode']}-V01"
    assert image["sharePath"] == f"/share/{image['versionCode']}"

    asset_search = client.post(
        "/api/images/search",
        headers=headers,
        json={"keyword": image["assetCode"]},
    )
    assert asset_search.status_code == 200
    assert asset_search.json()["exactMatch"] is True
    assert asset_search.json()["identityCode"] == image["assetCode"]
    assert asset_search.json()["results"][0]["image"]["id"] == image["id"]

    version_search = client.post(
        "/api/images/search",
        headers=headers,
        json={"keyword": f"http://localhost:5173/share/{image['versionCode']}"},
    )
    assert version_search.status_code == 200
    assert version_search.json()["exactMatch"] is True
    assert version_search.json()["results"][0]["image"]["versionCode"] == image["versionCode"]

    variant = client.post(
        f"/api/asset-groups/{image['assetGroupId']}/images",
        headers=headers,
        files={"file": ("variant.png", png_file("green"), "image/png")},
        data={"title": "身份码延展", "assetRole": "derivative", "autoAnalyze": "false"},
    )
    assert variant.status_code == 201
    variant_image = max(variant.json()["images"], key=lambda item: item["versionNo"])
    assert variant_image["versionCode"] == f"{image['assetCode']}-V02"

    old_code = image["assetCode"]
    deleted = client.delete(f"/api/images/{image['id']}", headers=headers)
    assert deleted.status_code == 204
    still_resolvable = client.post(
        "/api/images/search",
        headers=headers,
        json={"keyword": old_code},
    )
    assert still_resolvable.status_code == 200
    assert still_resolvable.json()["results"][0]["image"]["id"] == variant_image["id"]

    detail_by_code = client.get(
        f"/api/images/{variant_image['versionCode']}",
        headers=headers,
    )
    assert detail_by_code.status_code == 200
    assert detail_by_code.json()["versionCode"] == variant_image["versionCode"]


def test_admin_can_view_identity_ledger_but_business_cannot(client):
    admin_csrf = login(client, "admin", "admin-password")
    admin_headers = {
        "X-CSRF-Token": admin_csrf,
        "Origin": "http://localhost:5173",
    }
    uploaded = client.post(
        "/api/images/upload",
        headers=admin_headers,
        files={"file": ("ledger.png", png_file(), "image/png")},
        data={"title": "台账素材", "channel": "PPT", "autoAnalyze": "false"},
    )
    assert uploaded.status_code == 201
    image = uploaded.json()

    ledger = client.get("/api/admin/identity-codes", headers=admin_headers)
    assert ledger.status_code == 200
    body = ledger.json()
    assert body["total"] == 2
    assert body["summary"]["assetTotal"] == 1
    assert body["summary"]["versionTotal"] == 1
    assert {row["code"] for row in body["items"]} == {
        image["assetCode"],
        image["versionCode"],
    }
    assert all(row["status"] == "active" for row in body["items"])

    business_csrf = login(client, "business", "business-password")
    denied = client.get(
        "/api/admin/identity-codes",
        headers={
            "X-CSRF-Token": business_csrf,
            "Origin": "http://localhost:5173",
        },
    )
    assert denied.status_code == 403
