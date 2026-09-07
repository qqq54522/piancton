from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1]))

from app.services.vikingdb_vector_index import VikingDBVectorIndexSync


def rebuild(batch_size: int, dry_run: bool, async_write: bool) -> int:
    sync = VikingDBVectorIndexSync.from_settings()
    sync.batch_size = max(1, min(batch_size, 100))
    if not sync.client.configured and not dry_run:
        raise SystemExit("VikingDB 未配置或未启用，无法同步体系/卖点知识索引")

    stats, previews = sync.upsert_knowledge_documents(
        dry_run=dry_run,
        async_write=async_write,
    )
    if dry_run:
        for document in previews:
            print(document)
    return stats.submitted if not dry_run else stats.scanned


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Rebuild VikingDB system and selling-point knowledge documents."
    )
    parser.add_argument("--batch-size", type=int, default=100)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--async-write", action="store_true")
    args = parser.parse_args()
    count = rebuild(
        batch_size=max(args.batch_size, 1),
        dry_run=args.dry_run,
        async_write=args.async_write,
    )
    mode = "previewed" if args.dry_run else "submitted"
    print(f"{mode} {count} VikingDB knowledge documents")


if __name__ == "__main__":
    main()
