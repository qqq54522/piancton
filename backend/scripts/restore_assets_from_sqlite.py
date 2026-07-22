"""Replace Docker asset data with a compatible legacy SQLite asset library.

This utility intentionally restores only asset-owned records. Users, sessions,
taxonomy, business concepts, and operational logs stay in the target database.
Concept links are remapped by stable concept code because the two databases use
different UUIDs for the same business concepts.
"""

from __future__ import annotations

import argparse
import os
import shutil
import sqlite3
import sys
import uuid
from pathlib import Path, PurePosixPath

from sqlalchemy import create_engine, text


ASSET_TABLE_COLUMNS = {
    "asset_groups": (
        "id", "title", "primary_image_id", "approval_status", "publish_status",
        "style_label", "is_scene_image", "created_by", "created_at", "updated_at",
    ),
    "images": (
        "id", "title", "file_name", "storage_key", "thumbnail_storage_key",
        "media_type", "size_bytes", "uploader", "download_count", "image_summary",
        "semantic_profile_json", "asset_group_id", "asset_role", "width", "height",
        "aspect_ratio", "channel", "version_no", "is_current", "created_at", "deleted_at",
    ),
    "asset_search_phrases": (
        "id", "asset_group_id", "phrase", "origin", "review_status", "weight", "created_at",
    ),
    "analysis_runs": (
        "id", "image_id", "task", "status", "taxonomy_version", "model_provider",
        "model_name", "created_at",
    ),
    "image_embeddings": (
        "image_id", "model_name", "dimension", "content_hash", "document_text",
        "vector_json", "updated_at",
    ),
    "image_title_reservations": ("normalized_title", "title", "created_at"),
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-db", type=Path, required=True)
    parser.add_argument("--source-images", type=Path, required=True)
    parser.add_argument("--target-images", type=Path, default=Path("/data/images"))
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--files-only", action="store_true")
    return parser.parse_args()


def rows(connection: sqlite3.Connection, table: str, columns: tuple[str, ...]):
    selected = ", ".join(columns)
    return [dict(row) for row in connection.execute(f"SELECT {selected} FROM {table}")]


def safe_relative(storage_key: str) -> Path:
    path = PurePosixPath(storage_key)
    if path.is_absolute() or ".." in path.parts or not path.parts:
        raise ValueError(f"unsafe storage key: {storage_key!r}")
    return Path(*path.parts)


def copy_to_stage(image_rows: list[dict], source_root: Path, staging_root: Path) -> None:
    for image in image_rows:
        for key_name in ("storage_key", "thumbnail_storage_key"):
            storage_key = image[key_name]
            if not storage_key:
                continue
            relative = safe_relative(str(storage_key))
            is_thumbnail = key_name == "thumbnail_storage_key"
            source = source_root / ".thumbnails" / relative if is_thumbnail else source_root / relative
            if not source.is_file():
                raise FileNotFoundError(f"missing source file for {image['title']}: {source}")
            target = staging_root / ".thumbnails" / relative if is_thumbnail else staging_root / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, target)


def insert_rows(connection, table: str, columns: tuple[str, ...], values: list[dict]) -> None:
    if not values:
        return
    names = ", ".join(columns)
    placeholders = ", ".join(f":{column}" for column in columns)
    connection.execute(text(f"INSERT INTO {table} ({names}) VALUES ({placeholders})"), values)


def replace_image_files(staging_root: Path, target_images: Path) -> None:
    """Replace contents without renaming the Docker volume mount point itself."""
    target_images.mkdir(parents=True, exist_ok=True)
    for child in target_images.iterdir():
        if child.is_dir():
            shutil.rmtree(child)
        else:
            child.unlink()
    for child in staging_root.iterdir():
        shutil.move(str(child), target_images / child.name)
    staging_root.rmdir()


def restore(args: argparse.Namespace) -> dict[str, int]:
    if not args.source_db.is_file():
        raise FileNotFoundError(args.source_db)
    if not args.source_images.is_dir():
        raise NotADirectoryError(args.source_images)
    database_url = os.environ.get("DATABASE_URL")
    if not database_url:
        raise RuntimeError("DATABASE_URL is required")

    source = sqlite3.connect(args.source_db)
    source.row_factory = sqlite3.Row
    try:
        payload = {
            table: rows(source, table, columns)
            for table, columns in ASSET_TABLE_COLUMNS.items()
        }
        for group in payload["asset_groups"]:
            value = group["is_scene_image"]
            if value is not None:
                group["is_scene_image"] = bool(value)
        for image in payload["images"]:
            image["is_current"] = bool(image["is_current"])
        concept_codes = {
            row["id"]: row["code"]
            for row in source.execute("SELECT id, code FROM business_concepts")
        }
        links = [dict(row) for row in source.execute("SELECT * FROM asset_concept_links")]
    finally:
        source.close()

    staging_root = args.target_images.parent / f".asset-restore-stage-{uuid.uuid4()}"
    copy_to_stage(payload["images"], args.source_images, staging_root)

    summary = {
        "asset_groups": len(payload["asset_groups"]),
        "images": len(payload["images"]),
        "asset_concept_links": len(links),
        "asset_search_phrases": len(payload["asset_search_phrases"]),
        "analysis_runs": len(payload["analysis_runs"]),
        "image_embeddings": len(payload["image_embeddings"]),
    }
    if args.dry_run:
        shutil.rmtree(staging_root)
        return summary

    if args.files_only:
        replace_image_files(staging_root, args.target_images)
        return summary

    engine = create_engine(database_url)
    try:
        with engine.begin() as target:
            target_concepts = {
                row.code: row.id
                for row in target.execute(text("SELECT id, code FROM business_concepts"))
            }
            remapped_links = []
            for link in links:
                concept_code = concept_codes.get(link["concept_id"])
                target_concept_id = target_concepts.get(concept_code)
                if target_concept_id is None:
                    raise RuntimeError(f"target is missing concept code: {concept_code!r}")
                link["concept_id"] = target_concept_id
                remapped_links.append(link)

            target.execute(text("DELETE FROM images"))
            target.execute(text("DELETE FROM asset_groups"))
            target.execute(text("DELETE FROM image_title_reservations"))
            insert_rows(target, "asset_groups", ASSET_TABLE_COLUMNS["asset_groups"], payload["asset_groups"])
            insert_rows(target, "images", ASSET_TABLE_COLUMNS["images"], payload["images"])
            insert_rows(
                target,
                "asset_concept_links",
                (
                    "id", "asset_group_id", "concept_id", "relation_role", "origin",
                    "review_status", "confidence", "evidence_reason", "source_ref", "created_at",
                ),
                remapped_links,
            )
            for table in (
                "asset_search_phrases",
                "analysis_runs",
                "image_embeddings",
                "image_title_reservations",
            ):
                insert_rows(target, table, ASSET_TABLE_COLUMNS[table], payload[table])

        replace_image_files(staging_root, args.target_images)
    except Exception:
        shutil.rmtree(staging_root, ignore_errors=True)
        raise
    finally:
        engine.dispose()
    return summary


def main() -> int:
    args = parse_args()
    try:
        summary = restore(args)
    except Exception as exc:  # noqa: BLE001 - CLI needs one clear failure message.
        print(f"restore failed: {exc}", file=sys.stderr)
        return 1
    mode = "dry-run verified" if args.dry_run else "restore completed"
    print(f"{mode}: {summary}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
