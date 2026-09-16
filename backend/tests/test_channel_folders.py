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
    removed = client.delete(
        f"/api/channel-folders/folders/{school.json()['id']}", headers=headers(designer_csrf)
    )
    assert removed.status_code == 200
    channel = next(item for item in removed.json() if item["name"] == "合作学校")
    assert [(item["id"], item["name"]) for item in channel["folders"]] == [
        (beijing.json()["id"], "北京")
    ]
    assert old_id in ids(
        client.get("/api/images", params={"channel": "合作学校", "unfiled": "true"})
    )
    assert old_id in ids(client.get("/api/images", params={"channel": "合作学校"}))


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


def test_copy_folder_tree_merges_names_without_copying_image_placements(client):
    write_headers = headers(login(client, "admin", "admin-password"))
    source_root = client.post(
        "/api/channel-folders/folders",
        headers=write_headers,
        json={"channel": "PPT", "name": "产品"},
    ).json()
    source_child = client.post(
        "/api/channel-folders/folders",
        headers=write_headers,
        json={"channel": "PPT", "name": "AI功能", "parentId": source_root["id"]},
    ).json()
    client.post(
        "/api/channel-folders/folders",
        headers=write_headers,
        json={"channel": "PPT", "name": "拍题精学", "parentId": source_child["id"]},
    )
    client.post(
        "/api/channel-folders/folders",
        headers=write_headers,
        json={"channel": "官网大图", "name": "产品"},
    )

    uploaded = client.post(
        "/api/images/upload",
        headers=write_headers,
        files={"file": ("shared.png", png(), "image/png")},
        data={"title": "共用渠道图片", "channel": "PPT、官网大图"},
    ).json()
    client.post(
        "/api/channel-folders/placements",
        headers=write_headers,
        json={"channel": "PPT", "imageIds": [uploaded["id"]], "folderId": source_child["id"]},
    )

    copied = client.post(
        "/api/channel-folders/folders/copy",
        headers=write_headers,
        json={"sourceChannel": "PPT", "targetChannel": "官网大图"},
    )
    assert copied.status_code == 200
    assert copied.json() == {"created": 2, "skipped": 1}

    catalog = client.get("/api/channel-folders").json()
    target_folders = next(item["folders"] for item in catalog if item["name"] == "官网大图")
    target_root = next(item for item in target_folders if item["name"] == "产品")
    target_child = next(item for item in target_folders if item["name"] == "AI功能")
    target_grandchild = next(item for item in target_folders if item["name"] == "拍题精学")
    assert target_child["parentId"] == target_root["id"]
    assert target_grandchild["parentId"] == target_child["id"]
    assert uploaded["id"] not in ids(
        client.get(
            "/api/images",
            params={"channel": "官网大图", "folderId": target_child["id"]},
        )
    )
    assert uploaded["id"] in ids(
        client.get("/api/images", params={"channel": "官网大图", "unfiled": "true"})
    )

    repeated = client.post(
        "/api/channel-folders/folders/copy",
        headers=write_headers,
        json={"sourceChannel": "PPT", "targetChannel": "官网大图"},
    )
    assert repeated.status_code == 200
    assert repeated.json() == {"created": 0, "skipped": 3}


def test_copy_selected_folder_subtree_under_target_folder(client):
    write_headers = headers(login(client, "admin", "admin-password"))
    source_root = client.post(
        "/api/channel-folders/folders",
        headers=write_headers,
        json={"channel": "PPT", "name": "小学"},
    ).json()
    source_subject = client.post(
        "/api/channel-folders/folders",
        headers=write_headers,
        json={"channel": "PPT", "name": "数学", "parentId": source_root["id"]},
    ).json()
    source_topic = client.post(
        "/api/channel-folders/folders",
        headers=write_headers,
        json={"channel": "PPT", "name": "计算", "parentId": source_subject["id"]},
    ).json()
    client.post(
        "/api/channel-folders/folders",
        headers=write_headers,
        json={"channel": "PPT", "name": "不应复制"},
    )
    target_parent = client.post(
        "/api/channel-folders/folders",
        headers=write_headers,
        json={"channel": "官网大图", "name": "课程介绍"},
    ).json()

    copied = client.post(
        "/api/channel-folders/folders/copy",
        headers=write_headers,
        json={
            "sourceChannel": "PPT",
            "targetChannel": "官网大图",
            "sourceFolderId": source_subject["id"],
            "targetParentId": target_parent["id"],
        },
    )
    assert copied.status_code == 200
    assert copied.json() == {"created": 2, "skipped": 0}

    catalog = client.get("/api/channel-folders").json()
    target_folders = next(item["folders"] for item in catalog if item["name"] == "官网大图")
    copied_subject = next(item for item in target_folders if item["name"] == "数学")
    copied_topic = next(item for item in target_folders if item["name"] == "计算")
    assert copied_subject["parentId"] == target_parent["id"]
    assert copied_topic["parentId"] == copied_subject["id"]
    assert source_topic["id"] != copied_topic["id"]
    assert "小学" not in {item["name"] for item in target_folders}
    assert "不应复制" not in {item["name"] for item in target_folders}


def ids(response) -> set[str]:
    assert response.status_code == 200, response.text
    return {item["id"] for item in response.json()["items"]}
