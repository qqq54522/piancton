from __future__ import annotations

import argparse
import json
import shutil
import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.core.config import get_settings  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Back up local Piancton database and image storage together."
    )
    parser.add_argument(
        "--output-dir",
        default="../backups",
        help="Directory where timestamped backup folders are created.",
    )
    args = parser.parse_args()

    settings = get_settings()
    project_dir = Path(__file__).resolve().parents[2]
    output_root = (
        Path(args.output_dir)
        if Path(args.output_dir).is_absolute()
        else project_dir / args.output_dir
    ).resolve()
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    backup_dir = output_root / f"piancton-backup-{stamp}"
    backup_dir.mkdir(parents=True, exist_ok=False)

    db_path = _sqlite_path(settings.database_url)
    if db_path is None:
        raise SystemExit("backup_local_assets only supports SQLite DATABASE_URL")
    if not db_path.is_file():
        raise SystemExit(f"database file not found: {db_path}")

    db_backup = backup_dir / db_path.name
    source = sqlite3.connect(db_path)
    try:
        target = sqlite3.connect(db_backup)
        try:
            source.backup(target)
        finally:
            target.close()
    finally:
        source.close()

    storage_source = Path(settings.storage_dir)
    storage_target = backup_dir / "storage" / "images"
    if storage_source.exists():
        shutil.copytree(storage_source, storage_target)
    else:
        storage_target.mkdir(parents=True)

    manifest = {
        "createdAt": stamp,
        "database": str(db_backup.relative_to(backup_dir)),
        "storage": str(storage_target.relative_to(backup_dir)),
        "sourceDatabase": str(db_path),
        "sourceStorage": str(storage_source),
    }
    (backup_dir / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(f"Backup written to {backup_dir}")


def _sqlite_path(database_url: str) -> Path | None:
    prefix = "sqlite:///"
    if not database_url.startswith(prefix):
        return None
    path = Path(database_url.removeprefix(prefix))
    if not path.is_absolute():
        path = BACKEND_DIR / path
    return path.resolve()


if __name__ == "__main__":
    main()
