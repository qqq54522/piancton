"""Runtime business knowledge injected into AI tasks (D027).

Carries the currently enabled selling points so prompts and closed-catalog
validation follow the database instead of the static seed files.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class AiKnowledge:
    catalog_text: str
    concept_codes: frozenset[str]
    concept_pairs: frozenset[tuple[str, str]]
    concept_display_names: tuple[tuple[str, str], ...]
    concept_prompt_contexts: tuple[tuple[str, str], ...]
    concept_system_codes: tuple[tuple[str, tuple[str, ...]], ...]
