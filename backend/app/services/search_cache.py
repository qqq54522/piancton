from __future__ import annotations

import time
from collections import OrderedDict
from dataclasses import dataclass
from functools import lru_cache
from threading import Lock
from typing import Generic, TypeVar

from app.schemas.ai import SearchUnderstanding

T = TypeVar("T")


class TtlCache(Generic[T]):
    """Small process-local cache for safe, rebuildable search intermediates."""

    def __init__(self, *, ttl_seconds: float, max_entries: int):
        self.ttl_seconds = max(0.0, ttl_seconds)
        self.max_entries = max(1, max_entries)
        self._values: OrderedDict[str, tuple[float, T]] = OrderedDict()
        self._lock = Lock()

    def get(self, key: str) -> T | None:
        now = time.monotonic()
        with self._lock:
            row = self._values.get(key)
            if row is None:
                return None
            expires_at, value = row
            if expires_at <= now:
                self._values.pop(key, None)
                return None
            self._values.move_to_end(key)
            return value

    def set(self, key: str, value: T) -> None:
        if self.ttl_seconds <= 0:
            return
        with self._lock:
            self._values[key] = (time.monotonic() + self.ttl_seconds, value)
            self._values.move_to_end(key)
            while len(self._values) > self.max_entries:
                self._values.popitem(last=False)

    def clear(self) -> None:
        with self._lock:
            self._values.clear()


@dataclass(frozen=True)
class SearchCaches:
    understanding: TtlCache[SearchUnderstanding]
    embedding_vectors: TtlCache[tuple[float, ...]]


def build_search_caches(*, ttl_seconds: float, max_entries: int) -> SearchCaches:
    return SearchCaches(
        understanding=TtlCache(
            ttl_seconds=ttl_seconds,
            max_entries=max_entries,
        ),
        embedding_vectors=TtlCache(
            ttl_seconds=ttl_seconds,
            max_entries=max_entries,
        ),
    )


@lru_cache
def shared_search_caches(ttl_seconds: float, max_entries: int) -> SearchCaches:
    return build_search_caches(
        ttl_seconds=ttl_seconds,
        max_entries=max_entries,
    )
