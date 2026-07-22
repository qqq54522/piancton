"""Detects explicitly negated business terms inside a search query.

The goal is intentionally narrow: only treat a term as negated when the query
places a clear negation marker shortly before it inside the same clause
(e.g. “不需要真人老师督学”). Anything less explicit stays positive evidence,
so normal recall is untouched.
"""

from __future__ import annotations

NEGATION_MARKERS: tuple[str, ...] = (
    "不需要",
    "不想要",
    "不要",
    "不用",
    "不想",
    "不含",
    "不带",
    "不是",
    "无需",
    "排除",
    "去掉",
    "避免",
)

# Words that restart a positive request between a negation and a later term,
# e.g. “不需要错题本，要拍题讲解” keeps “拍题讲解” positive.
_RESET_MARKERS: tuple[str, ...] = ("要", "想", "但", "的", "还", "也")

# A negation only reaches terms that start within this many characters.
_NEGATION_WINDOW = 6

_IGNORED_CHARS = set(" ，。；;：:、,.!?！？“”\"'（）()《》<>[]【】-_")


def normalize_query_text(value: str) -> str:
    return "".join(char.lower() for char in value if char not in _IGNORED_CHARS)


def is_term_negated(query: str, term: str) -> bool:
    """True when every occurrence of ``term`` in ``query`` is negated.

    Both inputs are normalized with the same rules the local intent matcher
    uses, so offsets stay aligned with substring matching.
    """

    flat, boundaries = _flatten(query)
    normalized_term = normalize_query_text(term)
    if not flat or not normalized_term or normalized_term not in flat:
        return False

    start = 0
    occurrences = 0
    negated = 0
    while True:
        index = flat.find(normalized_term, start)
        if index < 0:
            break
        occurrences += 1
        if _occurrence_negated(flat, boundaries, index):
            negated += 1
        start = index + 1
    return occurrences > 0 and occurrences == negated


def _flatten(value: str) -> tuple[str, set[int]]:
    """Normalized text plus the positions where a clause boundary sits."""
    characters: list[str] = []
    boundaries: set[int] = set()
    pending_boundary = False
    for char in value.lower():
        if char in _IGNORED_CHARS:
            pending_boundary = True
            continue
        if pending_boundary:
            boundaries.add(len(characters))
            pending_boundary = False
        characters.append(char)
    return "".join(characters), boundaries


def _occurrence_negated(flat: str, boundaries: set[int], index: int) -> bool:
    prefix = _clause_prefix(flat, boundaries, index)
    marker_end = _last_marker_end(prefix)
    if marker_end is None:
        return False
    between = prefix[marker_end:]
    if len(between) > _NEGATION_WINDOW:
        return False
    return not any(reset in between for reset in _RESET_MARKERS)


def _clause_prefix(flat: str, boundaries: set[int], index: int) -> str:
    longest_reach = _NEGATION_WINDOW + max(len(marker) for marker in NEGATION_MARKERS)
    start = index
    while start > 0 and start not in boundaries and index - start < longest_reach:
        start -= 1
    return flat[start:index]


def _last_marker_end(prefix: str) -> int | None:
    best: int | None = None
    for marker in NEGATION_MARKERS:
        position = prefix.rfind(marker)
        if position < 0:
            continue
        end = position + len(marker)
        if best is None or end > best:
            best = end
    return best
