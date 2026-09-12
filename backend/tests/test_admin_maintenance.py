from io import BytesIO

from PIL import Image as PillowImage

from app.models.asset import AssetConceptLink, AssetGroup
from app.models.business_concept import BusinessConcept
from tests.conftest import login


def png_file() -> bytes:
    output = BytesIO()
    PillowImage.new("RGB", (12, 8), "blue").save(output, format="PNG")
    return output.getvalue()


def headers_for(client, username: str, password: str) -> dict[str, str]:
    csrf = login(client, username, password)
    return {"X-CSRF-Token": csrf, "Origin": "http://localhost:5173"}


def test_business_concept_assets_show_only_accepted_current_images(client, db_factory):
    admin_headers = headers_for(client, "admin", "admin-password")
    uploaded = client.post(
        "/api/images/upload",
        headers=admin_headers,
        files={"file": ("selling-point.png", png_file(), "image/png")},
        data={"title": "卖点素材", "channel": "PPT", "autoAnalyze": "false"},
    )
    assert uploaded.status_code == 201
    image = uploaded.json()

    with db_factory() as db:
        concept = BusinessConcept(code="admin_assets", name="后台素材卖点")
        group = db.get(AssetGroup, image["assetGroupId"])
        group.concept_links.append(
            AssetConceptLink(
                concept=concept,
                relation_role="expresses",
                origin="manual",
                review_status="accepted",
            )
        )
        db.add_all([concept, group])
        db.commit()
        concept_id = concept.id

    response = client.get(
        f"/api/business-concepts/{concept_id}/assets",
    )
    assert response.status_code == 200
    payload = response.json()
    assert len(payload) == 1
    assert payload[0]["relationRole"] == "expresses"
    assert payload[0]["image"]["title"] == "卖点素材"
    assert payload[0]["image"]["identityCode"]

    headers_for(client, "business", "business-password")
    forbidden = client.get(
        f"/api/business-concepts/{concept_id}/assets",
    )
    assert forbidden.status_code == 403
