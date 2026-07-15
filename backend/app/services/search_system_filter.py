from __future__ import annotations

from app.models.image import Image
from app.services.search_models import SearchHit


class SearchSystemFilter:
    """Applies a hard system constraint only when the user selected one."""

    def apply(self, hits: list[SearchHit], system_code: str | None) -> list[SearchHit]:
        code = (system_code or "").strip()
        if not code:
            return hits
        return [hit for hit in hits if self._matches(hit.image, code)]

    def _matches(self, image: Image, system_code: str) -> bool:
        group = image.asset_group
        if group is None:
            return False
        return any(
            link.review_status == "accepted"
            and link.relation_role != "excludes"
            and any(
                system.status == "active" and system.system_tag.code == system_code
                for system in link.concept.system_links
            )
            for link in group.concept_links
        )
