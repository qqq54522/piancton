from __future__ import annotations

import re
from collections.abc import Iterable

MAX_IMAGE_TITLE_LENGTH = 255
TITLE_SEQUENCE_PATTERN = re.compile(r"^(.*?)(\d{3})$")


def clean_image_title(value: str) -> str:
    return value.strip()[:MAX_IMAGE_TITLE_LENGTH]


def title_namespace(value: str) -> str:
    title = clean_image_title(value)
    match = TITLE_SEQUENCE_PATTERN.fullmatch(title)
    if match and match.group(1):
        return match.group(1)
    return title


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
