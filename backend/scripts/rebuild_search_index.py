from __future__ import annotations

import argparse

from app.core.config import get_settings
from app.db.session import SessionLocal
from app.repositories.image_repository import ImageRepository
from app.services.meilisearch_client import MeilisearchClient
from app.services.search_index import image_to_search_document


def rebuild(batch_size: int, dry_run: bool, replace: bool) -> int:
    settings = get_settings()
    client = MeilisearchClient(
        url=settings.meilisearch_url,
        api_key=settings.meilisearch_api_key,
        index=settings.meilisearch_index,
        timeout_seconds=settings.search_timeout_seconds,
    )
    if not dry_run:
        if replace:
            client.wait_task(client.delete_index())
        client.wait_task(client.configure_index())

    indexed = 0
    offset = 0
    with SessionLocal() as db:
        repo = ImageRepository(db)
        while True:
            images = repo.list_for_search_index(offset=offset, limit=batch_size)
            if not images:
                break
            documents = [image_to_search_document(image) for image in images]
            if dry_run:
                for document in documents[:3]:
                    print(document)
            else:
                client.wait_task(client.add_documents(documents))
            indexed += len(documents)
            offset += batch_size
    return indexed


def main() -> None:
    parser = argparse.ArgumentParser(description="Rebuild the derived Meilisearch image index.")
    parser.add_argument("--batch-size", type=int, default=100)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument(
        "--replace",
        action="store_true",
        help="Delete the existing derived index before rebuilding it.",
    )
    args = parser.parse_args()
    indexed = rebuild(max(args.batch_size, 1), args.dry_run, args.replace)
    mode = "previewed" if args.dry_run else "submitted"
    print(f"{mode} {indexed} image search documents")


if __name__ == "__main__":
    main()
