from io import BytesIO
from pathlib import Path

import pytest
from PIL import Image as PillowImage
from sqlalchemy import select

from app.api import dependencies
from app.core.errors import AppError
from app.models.image import Image
from app.services.storage_factory import build_storage
from app.services.storage_migration import StorageMigrationService
from app.services.storage_service import LocalStorageProvider
from app.services.tos_storage import TosStorageProvider
from tests.test_security_and_images import admin_headers, png_file, upload


class MissingObject(Exception):
    status_code = 404


class FakeTos:
    def __init__(self):
        self.objects = {}
        self.fail_put = False
        self.fail_delete = False
        self.corrupt = False

    def put_object_from_file(self, bucket, key, path, **kwargs):
        assert kwargs["acl"].value == "private"
        if self.fail_put and "/thumbnails/" in key:
            raise RuntimeError("upstream secret must not escape")
        self.objects[(bucket, key)] = Path(path).read_bytes()

    def get_object_to_file(self, bucket, key, path):
        if (bucket, key) not in self.objects:
            raise MissingObject()
        Path(path).write_bytes(b"corrupt" if self.corrupt else self.objects[(bucket, key)])

    def delete_object(self, bucket, key):
        if self.fail_delete:
            raise RuntimeError("secret")
        self.objects.pop((bucket, key), None)


@pytest.fixture()
def remote(tmp_path):
    return TosStorageProvider(tmp_path / "images", FakeTos(), "test-bucket", "piancton")


def test_remote_roundtrip_and_cleanup(remote):
    staged = remote.stage(BytesIO(png_file()), 100000, 100000, 640)
    remote.finalize(staged)
    assert staged.storage_key.startswith("tos-")
    assert not staged.temp_path.exists()
    assert len(remote.client.objects) == 2
    path = remote.path_for(staged.storage_key)
    assert path.read_bytes() == png_file()
    remote.release(path)
    assert not path.exists()
    remote.delete_key(staged.storage_key)
    remote.delete_key(staged.thumbnail_storage_key, thumbnail=True)
    assert not remote.client.objects


def test_failed_thumbnail_upload_rolls_back_both_objects(remote):
    staged = remote.stage(BytesIO(png_file()), 100000, 100000, 640)
    remote.client.fail_put = True
    with pytest.raises(AppError) as error:
        remote.finalize(staged)
    assert error.value.status_code == 503
    assert "secret" not in str(error.value)
    remote.discard(staged)
    assert not remote.client.objects
    assert not list(remote.staging.iterdir())


@pytest.mark.parametrize("key", ["tos-../bad", "../bad", "/bad", "tos-", "tos-x/../../bad"])
def test_rejects_unsafe_remote_paths(remote, key):
    with pytest.raises(AppError):
        remote.object_key(key)


def test_missing_remote_file_does_not_leave_temporary_file(remote):
    with pytest.raises(AppError) as error:
        remote.path_for("tos-missing.jpg")
    assert error.value.status_code == 404
    assert not list(remote.downloads.iterdir())


def install_remote(monkeypatch, remote):
    monkeypatch.setattr(dependencies, "build_storage", lambda settings: remote)


def test_api_remote_upload_preview_download_zip_and_purge(client, db_factory, remote, monkeypatch):
    install_remote(monkeypatch, remote)
    assert client.get("/api/images/no-id/content").status_code == 401
    headers = admin_headers(client)
    image = upload(client, headers, "TOS image")
    assert len(remote.client.objects) == 2
    for url in [image["contentUrl"], image["thumbnailUrl"], image["downloadUrl"]]:
        assert client.get(url).status_code == 200
        assert not list(remote.downloads.iterdir())
    assert client.get(f"/api/images/{image['id']}").json()["downloadCount"] == 1
    bundle = client.post("/api/asset-groups/export", json={"groupIds": [image["assetGroupId"]]})
    assert bundle.status_code == 200
    from zipfile import ZipFile

    with ZipFile(BytesIO(bundle.content)) as archive:
        assert any(
            archive.read(name) == png_file() for name in archive.namelist() if name.endswith(".png")
        )
    assert not list(remote.downloads.iterdir())
    assert client.delete(f"/api/images/{image['id']}", headers=headers).status_code == 204
    assert len(remote.client.objects) == 2
    assert client.post(f"/api/images/{image['id']}/restore", headers=headers).status_code == 200
    assert client.delete(f"/api/images/{image['id']}", headers=headers).status_code == 204
    remote.client.fail_delete = True
    assert client.delete(f"/api/images/{image['id']}/purge", headers=headers).status_code == 503
    with db_factory() as db:
        assert db.get(Image, image["id"]) is not None
    remote.client.fail_delete = False
    assert client.delete(f"/api/images/{image['id']}/purge", headers=headers).status_code == 204
    assert not remote.client.objects


def test_remote_legacy_long_thumbnail_falls_back_and_cleans_temp_file(
    client,
    db_factory,
    remote,
    monkeypatch,
):
    install_remote(monkeypatch, remote)
    response = client.post(
        "/api/images/upload",
        headers=admin_headers(client),
        files={"file": ("legacy-long.png", png_file(1200, 3600), "image/png")},
        data={"title": "远端旧长图", "channel": "手机端大图", "autoAnalyze": "false"},
    )
    assert response.status_code == 201
    payload = response.json()

    legacy_thumbnail = BytesIO()
    PillowImage.new("RGB", (213, 640), "red").save(legacy_thumbnail, format="JPEG")
    with db_factory() as db:
        image = db.get(Image, payload["id"])
        object_key = remote.object_key(image.thumbnail_storage_key, thumbnail=True)
    remote.client.objects[(remote.bucket, object_key)] = legacy_thumbnail.getvalue()

    preview = client.get(payload["thumbnailUrl"])
    assert preview.status_code == 200
    assert preview.headers["content-type"].startswith("image/png")
    with PillowImage.open(BytesIO(preview.content)) as served:
        assert served.size == (1200, 3600)
    assert not list(remote.downloads.iterdir())


def test_legacy_local_reads_and_verified_migration(client, db_factory, monkeypatch):
    headers = admin_headers(client)
    image = upload(client, headers)
    remote = TosStorageProvider(dependencies.settings.storage_dir, FakeTos(), "test", "piancton")
    install_remote(monkeypatch, remote)
    assert client.get(image["contentUrl"]).content == png_file()
    with db_factory() as db:
        record = db.get(Image, image["id"])
        source = remote.path_for(record.storage_key)
        migration = StorageMigrationService(db, remote)
        assert migration.migrate(record)
        assert not migration.migrate(record)
        assert source.exists()
    assert client.get(image["contentUrl"]).content == png_file()
    assert len(remote.client.objects) == 2
    assert not list(remote.downloads.iterdir())


def test_migration_verification_failure_keeps_local_record(client, db_factory):
    image = upload(client, admin_headers(client))
    remote = TosStorageProvider(dependencies.settings.storage_dir, FakeTos(), "test", "piancton")
    remote.client.corrupt = True
    with db_factory() as db:
        record = db.get(Image, image["id"])
        original_key = record.storage_key
        with pytest.raises(AppError):
            StorageMigrationService(db, remote).migrate(record)
        assert db.scalar(select(Image.storage_key).where(Image.id == image["id"])) == original_key
    assert not remote.client.objects
    assert not list(remote.downloads.iterdir())


def test_missing_credentials_fails_explicitly(monkeypatch):
    monkeypatch.setattr(dependencies.settings, "storage_backend", "tos")
    monkeypatch.setattr(dependencies.settings, "tos_access_key_id", "")
    with pytest.raises(AppError) as error:
        build_storage(dependencies.settings)
    assert error.value.code == "storage_config_invalid"


def test_local_mode_cannot_silently_delete_remote_record(tmp_path):
    local = LocalStorageProvider(tmp_path)
    with pytest.raises(AppError) as error:
        local.delete_key("tos-file.png")
    assert error.value.code == "object_storage_not_enabled"


def test_failed_database_commit_cleans_remote_upload(client, remote, monkeypatch):
    from app.services.unit_of_work import UnitOfWork

    headers = admin_headers(client)
    install_remote(monkeypatch, remote)

    def fail_commit(self):
        raise RuntimeError("database commit failed")

    monkeypatch.setattr(UnitOfWork, "commit", fail_commit)
    with pytest.raises(RuntimeError, match="database commit failed"):
        upload(client, headers, "rollback")
    assert not remote.client.objects
    assert not list(remote.staging.iterdir())


def test_response_releases_temporary_file_on_send_failure(remote):
    import asyncio

    from app.api.storage_response import StorageFileResponse

    staged = remote.stage(BytesIO(png_file()), 100000, 100000, 640)
    remote.finalize(staged)
    path = remote.path_for(staged.storage_key)
    response = StorageFileResponse(path, release=remote.release)

    async def send(message):
        raise RuntimeError("connection lost")

    async def receive():
        return {"type": "http.disconnect"}

    with pytest.raises(RuntimeError, match="connection lost"):
        asyncio.run(response({"type": "http", "method": "GET", "headers": []}, receive, send))
    assert not path.exists()


def test_configure_script_preserves_existing_settings(tmp_path, monkeypatch, capsys):
    from scripts import configure_tos

    script = tmp_path / "backend" / "scripts" / "configure_tos.py"
    monkeypatch.setattr(configure_tos, "__file__", str(script))
    env = tmp_path / ".env"
    env.write_text("POSTGRES_PASSWORD=unchanged\nTOS_BUCKET=old\nTOS_BUCKET=duplicate\n")
    credentials = iter(["test-ak", "test-sk"])
    monkeypatch.setattr(configure_tos.getpass, "getpass", lambda prompt: next(credentials))
    configure_tos.main()
    content = env.read_text()
    assert "POSTGRES_PASSWORD=unchanged" in content
    assert content.count("TOS_BUCKET=") == 1
    assert "TOS_BUCKET=ued-zhiku" in content
    assert env.stat().st_mode & 0o777 == 0o600
    assert "test-sk" not in capsys.readouterr().out
