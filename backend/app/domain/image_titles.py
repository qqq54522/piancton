from __future__ import annotations

import re
from collections.abc import Iterable

MAX_IMAGE_TITLE_LENGTH = 255
TITLE_SEQUENCE_PATTERN = re.compile(r"^(.*?)(\d{3})$")
MATERIAL_ASPECT_SUFFIX_PATTERN = re.compile(
    r"(?:[（(【\[]\s*(?:1\s*[-:：比]\s*1|4\s*[-:：比]\s*3|3\s*[-:：比]\s*4|"
    r"16\s*[-:：比]\s*9|9\s*[-:：比]\s*16)\s*[）)】\]])$",
    re.IGNORECASE,
)
MATERIAL_SEQUENCE_SUFFIX_PATTERN = re.compile(
    r"(?:[\s_-]*(?<!\d)(?:0\d{3}|\d{1,3}))$"
)


def clean_image_title(value: str) -> str:
    return value.strip()[:MAX_IMAGE_TITLE_LENGTH]


def title_namespace(value: str) -> str:
    title = clean_image_title(value)
    match = TITLE_SEQUENCE_PATTERN.fullmatch(title)
    if match and match.group(1):
        return match.group(1)
    return title


def material_title_family(value: str) -> str:
    """Return a stable display-title family without treating it as business truth.

    Batch uploads often encode a visual sequence and its aspect ratio in the title,
    for example ``学情报告02（4-3）``.  Agent recommendation expansion uses this
    presentation-only family to include sibling sizes while accepted business
    concept links remain the authority for selling-point relevance.
    """

    title = " ".join(clean_image_title(value).split())
    if not title:
        return ""
    title = MATERIAL_ASPECT_SUFFIX_PATTERN.sub("", title).rstrip()
    title = MATERIAL_SEQUENCE_SUFFIX_PATTERN.sub("", title).strip(" _-")
    return title.casefold()


def allocate_unique_image_title(
    requested: str,
    existing_titles: Iterable[str],
) -> str:
    title = clean_image_title(requested)
    existing = [clean_image_title(item) for item in existing_titles]
    existing = [item for item in existing if item]
    occupied = {item.casefold() for item in existing}
    if title.casefold() not in occupied:
        return title

    possible_base = title_namespace(title)
    base = (
        possible_base
        if possible_base != title
        and possible_base.casefold() in occupied
        else title
    )
    base_key = base.casefold()
    highest = 0
    for candidate in existing:
        candidate_match = TITLE_SEQUENCE_PATTERN.fullmatch(candidate)
        if candidate.casefold() == base_key:
            highest = max(highest, 0)
        elif (
            candidate_match
            and candidate_match.group(1).casefold() == base_key
        ):
            highest = max(highest, int(candidate_match.group(2)))

    sequence = highest + 1
    while True:
        suffix = f"{sequence:03d}"
        resolved = f"{base[: MAX_IMAGE_TITLE_LENGTH - len(suffix)]}{suffix}"
        if resolved.casefold() not in occupied:
            return resolved
        sequence += 1
