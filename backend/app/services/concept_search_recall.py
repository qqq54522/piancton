from __future__ import annotations

from app.domain.query_negation import is_term_negated
from app.models.business_concept import BusinessConcept, ConceptSearchPhrase
from app.models.image import Image
from app.repositories.business_concept_repository import BusinessConceptRepository
from app.repositories.image_repository import ImageRepository
from app.services.query_expansion_service import unique
from app.services.search_models import ConceptMatch, SearchHit


class ConceptSearchRecallService:
    """Matches versioned concepts locally and recalls their published asset groups."""

    def __init__(
        self,
        concepts: BusinessConceptRepository,
        images: ImageRepository,
    ):
        self.concepts = concepts
        self.images = images

    def match(self, keyword: str, *, limit: int = 8) -> list[ConceptMatch]:
        needle = _normalize(keyword)
        if not needle:
            return []
        matches = [
            match
            for concept in self.concepts.list()
            if (match := self._match_concept(needle, concept, keyword)) is not None
        ]
        return sorted(matches, key=lambda item: item.score, reverse=True)[:limit]

    def recall(
        self,
        matches: list[ConceptMatch],
        *,
        limit: int,
    ) -> list[SearchHit]:
        if not matches:
            return []
        match_by_id = {item.concept_id: item for item in matches}
        images = self._recall_images_by_match(matches, limit=limit)
        hits: list[SearchHit] = []
        for image in images:
            group = image.asset_group
            if group is None:
                continue
            excluded_ids = {
                link.concept_id
                for link in group.concept_links
                if link.relation_role == "excludes"
                and link.review_status == "accepted"
                and link.concept_id in match_by_id
            }
            if excluded_ids:
                continue
            scores: list[float] = []
            reasons: list[str] = []
            for link in group.concept_links:
                match = match_by_id.get(link.concept_id)
                if match is None or link.review_status == "rejected":
                    continue
                link_score = _link_score(
                    origin=link.origin,
                    review_status=link.review_status,
                    relation_role=link.relation_role,
                )
                if link_score <= 0:
                    continue
                scores.append(min(match.score, link_score))
                reasons.extend(match.reasons)
                reasons.append(
                    f"素材{_relation_name(link.relation_role)}业务概念：{match.name}"
                )
            if not scores:
                continue
            hits.append(
                SearchHit(
                    image=image,
                    score=max(scores),
                    reasons=tuple(unique(reasons)),
                )
            )
        return hits

    def _recall_images_by_match(
        self,
        matches: list[ConceptMatch],
        *,
        limit: int,
    ) -> list[Image]:
        images_by_id = {}
        for match in matches:
            for image in self.images.search_by_concept_ids(
                [match.concept_id],
                limit=limit,
            ):
                images_by_id.setdefault(image.id, image)
        return list(images_by_id.values())

    def _match_concept(
        self,
        needle: str,
        concept: BusinessConcept,
        keyword: str,
    ) -> ConceptMatch | None:
        candidates = [
            (concept.name, 1.0, "业务概念名称命中"),
            (concept.code, 0.96, "业务概念 code 命中"),
            *[
                (
                    phrase.phrase,
                    min(0.98, max(0.6, phrase.weight)),
                    f"概念搜索表达命中：{phrase.phrase}",
                )
                for phrase in concept.search_phrases
                if _searchable_phrase(phrase)
            ],
        ]
        scored: list[tuple[float, str]] = []
        for term, weight, reason in candidates:
            match_score = _term_match_score(needle, _normalize(term))
            if match_score <= 0:
                continue
            if is_term_negated(keyword, term):
                continue
            scored.append((min(match_score, weight), reason))
        if not scored:
            return None
        score = max(item[0] for item in scored)
        reasons = tuple(unique([reason for item_score, reason in scored if item_score == score]))
        system_codes = tuple(
            unique(
                [
                    link.system_tag.code
                    for link in concept.system_links
                    if link.status == "active" and link.system_tag.code
                ]
            )
        )
        return ConceptMatch(
            concept_id=concept.id,
            code=concept.code,
            name=concept.name,
            score=score,
            system_codes=system_codes,
            reasons=reasons,
        )


def _searchable_phrase(phrase: ConceptSearchPhrase) -> bool:
    return phrase.review_status == "accepted" and bool(phrase.phrase.strip())


def _term_match_score(needle: str, term: str) -> float:
    if not needle or len(term) < 2:
        return 0.0
    if needle == term:
        return 1.0
    # Two/three-character business words such as “课程”“教材” are useful as
    # exact queries but too broad to claim a concept inside a longer sentence.
    if len(term) < 4:
        return 0.0
    if term in needle:
        return 0.95
    if len(needle) >= 4 and needle in term:
        return 0.84
    return 0.0


def _link_score(*, origin: str, review_status: str, relation_role: str) -> float:
    if relation_role == "excludes":
        return 0.0
    # D080: 未审核的关系建议只是待办，不参与任何搜索召回；
    # 人工 accepted 之后才成为素材的业务语义事实。
    if review_status != "accepted":
        return 0.0
    role_score = {
        "expresses": 1.0,
        "supports": 0.92,
        "visual_related": 0.74,
    }.get(relation_role, 0.68)
    if origin == "ai":
        return min(role_score, 0.82)
    return role_score


def _relation_name(value: str) -> str:
    return {
        "expresses": "主要表达",
        "supports": "支持",
        "visual_related": "画面关联",
    }.get(value, "关联")


def _normalize(value: str) -> str:
    ignored = set(" ，。；;：:、,.!?！？“”\"'（）()《》<>[]【】-_")
    return "".join(char.lower() for char in value if char not in ignored)
