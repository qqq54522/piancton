"""Default: report inventory only. --apply copies, verifies, and updates locations."""

import argparse

from sqlalchemy import select

from app.core.config import get_settings
from app.core.errors import AppError
from app.db.session import SessionLocal
from app.models.image import Image
from app.services.storage_factory import build_storage
from app.services.storage_migration import StorageMigrationService
from app.services.tos_storage import REMOTE_PREFIX, TosStorageProvider


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    with SessionLocal() as db:
        ids = list(
            db.scalars(
                select(Image.id)
                .where(~Image.storage_key.startswith(REMOTE_PREFIX))
                .order_by(Image.id)
            )
        )
        print(f"Local images (including recycle bin): {len(ids)}")
        if not args.apply:
            print("Dry run. Use --apply during a maintenance window; local files are retained.")
            return
        remote = build_storage(get_settings())
        if not isinstance(remote, TosStorageProvider):
            raise AppError("migration_config_invalid", "请先设置 STORAGE_BACKEND=tos")
        migration = StorageMigrationService(db, remote)
        for image_id in ids:
            image = db.scalar(select(Image).where(Image.id == image_id).with_for_update())
            if image is not None and migration.migrate(image):
                print(f"Migrated and verified: {image_id}")
        print("Complete. Local source files retained; do not delete the image_data volume.")


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        # Never print SDK exception details containing signed URLs or credentials.
        print(f"Migration stopped: {getattr(exc, 'code', 'migration_failed')}")
        raise SystemExit(1) from None
