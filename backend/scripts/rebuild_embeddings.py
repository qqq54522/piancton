from __future__ import annotations

import argparse

from app.db.session import SessionLocal
from app.repositories.image_repository import ImageRepository
from app.services.embedding_index import EmbeddingIndexSync, image_to_embedding_document


def rebuild(batch_size: int, dry_run: bool) -> int:
    sync = EmbeddingIndexSync.from_settings()
    if not sync.client.configured and not dry_run:
        raise SystemExit("Embedding API 未配置，无法重建语义向量")

    indexed = 0
    offset = 0
    with SessionLocal() as db:
        repo = ImageRepository(db)
        while True:
            images = repo.list_for_search_index(offset=offset, limit=batch_size)
            if not images:
                break
            for image in images:
                if dry_run:
                    print(image_to_embedding_document(image))
                else:
                    sync.upsert_image(repo, image)
                indexed += 1
            if not dry_run:
                db.commit()
            offset += batch_size
    return indexed


def main() -> None:
    parser = argparse.ArgumentParser(description="Rebuild image semantic embeddings.")
    parser.add_argument("--batch-size", type=int, default=50)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    indexed = rebuild(max(args.batch_size, 1), args.dry_run)
    mode = "previewed" if args.dry_run else "rebuilt"
    print(f"{mode} {indexed} image embeddings")


if __name__ == "__main__":
    main()
