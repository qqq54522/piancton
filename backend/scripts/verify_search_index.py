from __future__ import annotations

import argparse
import uuid

from app.core.config import get_settings
from app.db.session import SessionLocal
from app.domain.taxonomy_catalog import load_taxonomy_catalog
from app.repositories.image_repository import ImageRepository
from app.services.meilisearch_client import MeilisearchClient
from app.services.search_index import image_to_search_document
from app.services.search_service import SearchService


def verify(limit: int, keyword: str | None, cleanup: bool) -> None:
    settings = get_settings()
    if not settings.meilisearch_url:
        raise SystemExit("MEILISEARCH_URL 未配置，无法验证真实搜索实例")

    temp_index = f"{settings.meilisearch_index}_verify_{uuid.uuid4().hex[:8]}"
    client = MeilisearchClient(
        url=settings.meilisearch_url,
        api_key=settings.meilisearch_api_key,
        index=temp_index,
        timeout_seconds=max(settings.search_timeout_seconds, 10),
    )

    health = client.health()
    print(f"Meilisearch health: {health}")

    catalog = load_taxonomy_catalog()
    with SessionLocal() as db:
        repo = ImageRepository(db)
        images = repo.list_for_search_index(offset=0, limit=limit)
        if not images:
            raise SystemExit("当前数据库没有可索引图片，无法验证真实搜索结果")
        documents = [image_to_search_document(image, catalog=catalog) for image in images]
        query = keyword or documents[0]["title"]

        try:
            client.wait_task(client.configure_index())
            client.wait_task(client.add_documents(documents))

            raw = client.search(query, limit=5)
            hits = raw.get("hits", [])
            if not isinstance(hits, list) or not hits:
                raise SystemExit(f"Meilisearch 未返回命中：query={query!r}, response={raw}")

            service = SearchService(
                db,
                search_backend="meilisearch",
                meilisearch_url=settings.meilisearch_url,
                meilisearch_api_key=settings.meilisearch_api_key,
                meilisearch_index=temp_index,
                search_timeout_seconds=max(settings.search_timeout_seconds, 10),
            )
            response = service.search(query, limit=5)
            if response.search_mode != "meilisearch" or not response.results:
                raise SystemExit(
                    "SearchService 未走通 Meilisearch："
                    f"mode={response.search_mode}, fallback={response.fallback}, "
                    f"reason={response.fallback_reason}"
                )
            print(
                "Verified Meilisearch search: "
                f"index={temp_index}, documents={len(documents)}, "
                f"query={query!r}, hits={len(response.results)}, "
                f"top={response.results[0].image.title!r}"
            )
        finally:
            if cleanup:
                try:
                    client.wait_task(client.delete_index())
                    print(f"Cleaned temporary index: {temp_index}")
                except Exception as exc:
                    print(f"Temporary index cleanup failed: {temp_index}: {exc}")


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Verify Meilisearch indexing and SearchService integration "
            "with a temporary index."
        ),
    )
    parser.add_argument("--limit", type=int, default=20)
    parser.add_argument("--keyword", default=None)
    parser.add_argument("--keep-index", action="store_true")
    args = parser.parse_args()
    verify(max(args.limit, 1), args.keyword, cleanup=not args.keep_index)


if __name__ == "__main__":
    main()
