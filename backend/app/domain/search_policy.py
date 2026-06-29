from __future__ import annotations

import json
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any

from app.core.config import PROJECT_DIR

SEARCH_POLICY_PATH = PROJECT_DIR / "taxonomy" / "search_policy.json"


@dataclass(frozen=True)
class SearchPolicyCatalog:
    version: str
    ambiguous_terms: tuple[str, ...]


def _strings(value: Any) -> tuple[str, ...]:
    if not isinstance(value, list):
        return ()
    return tuple(str(item).strip() for item in value if str(item).strip())


@lru_cache
def load_search_policy(path: Path = SEARCH_POLICY_PATH) -> SearchPolicyCatalog:
    raw = json.loads(path.read_text(encoding="utf-8"))
    return SearchPolicyCatalog(
        version=str(raw.get("version") or "").strip(),
        ambiguous_terms=_strings(raw.get("ambiguous_terms")),
    )
