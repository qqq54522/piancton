import json
from io import BytesIO

from PIL import Image as PillowImage

from tests.conftest import login


def png() -> bytes:
    output = BytesIO()
    PillowImage.new("RGB", (8, 4), "blue").save(output, format="PNG")
    return output.getvalue()


def headers(csrf: str) -> dict[str, str]:
    return {"X-CSRF-Token": csrf, "Origin": "http://localhost:5173"}


def test_channel_folder_tree_and_old_image_batch_placement(client):
    admin = headers(login(client, "admin", "admin-password"))
    root = client.post(
        "/api/channel-folders/channels",
        headers=admin,
        json={"name": "合作学校"},
    )
    assert root.status_code == 200
    beijing = client.post(
        "/api/channel-folders/folders", headers=admin, json={"channel": "合作学校", "name": "北京"}
    )
    assert beijing.status_code == 200
    school = client.post(
        "/api/channel-folders/folders",
        headers=admin,
        json={"channel": "合作学校", "name": "朝阳学校", "parentId": beijing.json()["id"]},
    )
    assert school.status_code == 200
    third = client.post(
        "/api/channel-folders/folders",
        headers=admin,
        json={"channel": "合作学校", "name": "活动图", "parentId": school.json()["id"]},
    )
    assert third.status_code == 200
    fourth = client.post(
        "/api/channel-folders/folders",
        headers=admin,
        json={"channel": "合作学校", "name": "班级", "parentId": third.json()["id"]},
    )
    assert fourth.status_code == 200
    fifth = client.post(
        "/api/channel-folders/folders",
        headers=admin,
        json={"channel": "合作学校", "name": "班级活动", "parentId": fourth.json()["id"]},
    )
    assert fifth.status_code == 200

    old = client.post(
        "/api/images/upload",
        headers=admin,
        files={"file": ("old.png", png(), "image/png")},
        data={"title": "北京合作案例", "channel": "合作学校"},
    )
    assert old.status_code == 201
    old_id = old.json()["id"]
    assert old_id in ids(client.get("/api/images", params={"channel": "合作学校"}))
    assert old_id in ids(
        client.get("/api/images", params={"channel": "合作学校", "unfiled": "true"})
    )
    assert old_id not in ids(
        client.get("/api/images", params={"channel": "合作学校", "folderId": beijing.json()["id"]})
    )

    login(client, "designer", "designer-password")
    designer_csrf = client.cookies.get("piancton_csrf")
    # Designer is allowed to organize without editing business facts.
    placement = client.post(
        "/api/channel-folders/placements",
        headers=headers(designer_csrf),
        json={"channel": "合作学校", "imageIds": [old_id], "folderId": school.json()["id"]},
    )
    assert placement.status_code == 200
    assert old_id in ids(
        client.get("/api/images", params={"channel": "合作学校", "folderId": beijing.json()["id"]})
    )
    assert old_id in ids(
        client.get("/api/images", params={"channel": "合作学校", "folderId": school.json()["id"]})
    )
    assert old_id not in ids(
        client.get("/api/images", params={"channel": "合作学校", "folderId": fifth.json()["id"]})
    )
    assert old_id not in ids(
        client.get("/api/images", params={"channel": "合作学校", "unfiled": "true"})
    )
    assert (
        client.delete(
            f"/api/channel-folders/folders/{school.json()['id']}", headers=headers(designer_csrf)
        ).status_code
        == 409
    )


def test_upload_placement_and_variant_inherit_channel_folder(client):
    csrf = login(client, "admin", "admin-password")
    write_headers = headers(csrf)
    folder = client.post(
        "/api/channel-folders/folders",
        headers=write_headers,
        json={"channel": "手机端小图", "name": "数学"},
    ).json()
    uploaded = client.post(
        "/api/images/upload",
        headers=write_headers,
        files={"file": ("math.png", png(), "image/png")},
        data={
            "title": "数学小图",
            "channel": "手机端小图",
            "folderPlacements": json.dumps({"手机端小图": folder["id"]}),
        },
    )
    assert uploaded.status_code == 201
    image_id = uploaded.json()["id"]
    assert image_id in ids(
        client.get("/api/images", params={"channel": "手机端小图", "folderId": folder["id"]})
    )
    variant = client.post(
        f"/api/asset-groups/{uploaded.json()['assetGroupId']}/images",
        headers=write_headers,
        files={"file": ("variant.png", png(), "image/png")},
        data={"title": "数学小图延展", "assetRole": "derivative"},
    )
    assert variant.status_code == 201
    assert (
        len(
            ids(
                client.get(
                    "/api/images", params={"channel": "手机端小图", "folderId": folder["id"]}
                )
            )
        )
        == 2
    )
    wrong = client.post(
        "/api/images/upload",
        headers=write_headers,
        files={"file": ("wrong.png", png(), "image/png")},
        data={
            "title": "错误目录",
            "channel": "PPT",
            "folderPlacements": json.dumps({"PPT": folder["id"]}),
        },
    )
    assert wrong.status_code == 400
    assert "错误目录" not in [
        item["title"]
        for item in client.get("/api/images", params={"channel": "PPT"}).json()["items"]
    ]


def ids(response) -> set[str]:
    assert response.status_code == 200, response.text
    return {item["id"] for item in response.json()["items"]}
