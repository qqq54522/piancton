from __future__ import annotations

from typing import Literal

from app.domain.evidence_points import load_evidence_point_catalog
from app.domain.proof_points import load_proof_point_catalog
from app.models.image import Image
from app.schemas.image import ScoredImage, SearchResultConceptMatch
from app.services.image_semantic_profile_service import ImageSemanticProfileService
from app.services.query_expansion_service import unique
from app.services.search_asset_presenter import SearchAssetPresenter
from app.services.serializers import image_to_read


class SearchScorer:
    def __init__(
        self,
        asset_presenter: SearchAssetPresenter | None = None,
    ):
        self.asset_presenter = asset_presenter or SearchAssetPresenter()
        self.semantic_profile = ImageSemanticProfileService()

    def build_scored_image(
        self,
        image: Image,
        needle: str,
        external_score: float | None,
        external_reasons: list[str],
        query_concept_ids: set[str] | None = None,
    ) -> ScoredImage:
        semantic_terms = self.semantic_profile.profile_terms(image)
        concept_links = [
            link
            for link in (image.asset_group.concept_links if image.asset_group else [])
            if link.review_status != "rejected" and link.relation_role != "excludes"
        ]

        title = image.title.lower()
        exact_title = bool(needle and (needle in title or title in needle))
        summary = image.image_summary.lower() if image.image_summary else ""
        summary_match = bool(needle and summary and (needle in summary or summary in needle))
        matched_content = self._matching_names(needle, semantic_terms)
        matched_concepts = self._matching_concepts(needle, concept_links)

        reasons = list(external_reasons)
        if exact_title:
            reasons.append("标题匹配")
        if matched_content:
            reasons.append("素材语义匹配")
        if matched_concepts:
            reasons.append("业务概念匹配")
        if summary_match:
            reasons.append("图片摘要匹配")
        if not reasons:
            reasons.append("搜索索引匹配")

        concept_score = self._concept_score(needle, concept_links)
        score_candidates = [
            score
            for score in (
                external_score,
                1.0 if exact_title else None,
                0.9 if summary_match else None,
                concept_score,
                0.8 if matched_content else None,
            )
            if score is not None
        ]
        score = max(score_candidates) if score_candidates else 0.65
        score = max(0.0, min(score, 1.0))

        asset = self.asset_presenter.present(image)
        matched_query_concepts = self._matched_query_concepts(
            concept_links,
            query_concept_ids or set(),
        )
        group = image.asset_group
        proof_code = group.primary_proof_point_code if group else None
        evidence_code = group.primary_evidence_point_code if group else None
        proof = load_proof_point_catalog().by_code.get(proof_code or "")
        evidence = load_evidence_point_catalog().by_code.get(evidence_code or "")
        result_recommendation_reason = self._result_recommendation_reason(
            image=image,
            asset_title=asset.title,
            matched_query_concepts=matched_query_concepts,
            proof_name=proof.name if proof else None,
            evidence_name=evidence.name if evidence else None,
            reasons=unique(reasons),
            matched_content=matched_content,
        )
        return ScoredImage(
            image=image_to_read(image),
            match_level=self.match_level(score),
            final_score=score,
            match_reasons=unique(reasons),
            result_recommendation_reason=result_recommendation_reason,
            matched_content_terms=matched_content,
            matched_business_concepts=matched_concepts,
            asset_group_id=asset.group_id,
            asset_title=asset.title,
            available_variants=list(asset.variants),
            expressed_concepts=list(asset.expressed_concepts),
            supported_concepts=list(asset.supported_concepts),
            matched_query_concepts=matched_query_concepts,
            primary_proof_point_code=proof_code,
            primary_proof_point_name=proof.name if proof else None,
            primary_proof_point_claim=proof.claim if proof else None,
            primary_evidence_point_code=evidence_code,
            primary_evidence_point_name=evidence.name if evidence else None,
        )

    def match_level(self, score: float) -> Literal["S", "A", "B", "C"]:
        if score >= 0.95:
            return "S"
        if score >= 0.8:
            return "A"
        if score >= 0.65:
            return "B"
        return "C"

    def _matching_names(self, needle: str, names: list[str]) -> list[str]:
        if not needle:
            return []
        return unique([name for name in names if needle in name.lower()])

    def _matching_concepts(self, needle: str, links) -> list[str]:
        if not needle:
            return []
        matched: list[str] = []
        for link in links:
            names = [
                link.concept.code,
                link.concept.name,
                *(
                    phrase.phrase
                    for phrase in link.concept.search_phrases
                    if phrase.review_status == "accepted"
                ),
            ]
            if any(needle in name.lower() for name in names if name):
                matched.append(link.concept.name)
        return unique(matched)

    def _concept_score(self, needle: str, links) -> float | None:
        if not needle:
            return None
        scores: list[float] = []
        for link in links:
            names = [
                link.concept.code,
                link.concept.name,
                *(
                    phrase.phrase
                    for phrase in link.concept.search_phrases
                    if phrase.review_status == "accepted"
                ),
            ]
            if not any(needle in name.lower() for name in names if name):
                continue
            if link.review_status == "accepted" and link.origin in {"manual", "migrated"}:
                scores.append(0.96 if link.relation_role == "expresses" else 0.9)
            elif link.review_status == "accepted":
                scores.append(0.85)
            else:
                scores.append(0.72)
        return max(scores) if scores else None

    def _matched_query_concepts(
        self,
        links,
        query_concept_ids: set[str],
    ) -> list[SearchResultConceptMatch]:
        if not query_concept_ids:
            return []
        role_priority = {"expresses": 3, "supports": 2, "visual_related": 1}
        selected = {}
        for link in links:
            if (
                link.concept_id not in query_concept_ids
                or link.review_status != "accepted"
                or link.relation_role not in role_priority
            ):
                continue
            current = selected.get(link.concept_id)
            current_rank = (
                int(current.origin in {"manual", "migrated"}),
                role_priority[current.relation_role],
            ) if current else (-1, -1)
            candidate_rank = (
                int(link.origin in {"manual", "migrated"}),
                role_priority[link.relation_role],
            )
            if candidate_rank > current_rank:
                selected[link.concept_id] = link
        ordered = sorted(
            selected.values(),
            key=lambda link: role_priority[link.relation_role],
            reverse=True,
        )
        return [
            SearchResultConceptMatch(
                concept_code=link.concept.code,
                concept_name=link.concept.name,
                relation_role=link.relation_role,
                recommendation_text=link.concept.recommendation_text,
            )
            for link in ordered
        ]

    def _result_recommendation_reason(
        self,
        *,
        image: Image,
        asset_title: str,
        matched_query_concepts: list[SearchResultConceptMatch],
        proof_name: str | None,
        evidence_name: str | None,
        reasons: list[str],
        matched_content: list[str],
    ) -> str:
        concept = matched_query_concepts[0] if matched_query_concepts else None
        concept_name = concept.concept_name if concept else ""
        relation = _relation_label(concept.relation_role) if concept else "匹配"
        title = asset_title or image.title
        asset_phrase = _first_reason_value(reasons, "卖点内素材独有话术命中：")
        concept_phrase = _first_reason_value(reasons, "概念搜索表达命中：")
        proof_reason = _first_reason_value(reasons, "证明点匹配：")
        detail = (
            _clean_reason(asset_phrase)
            or _clean_reason(proof_reason)
            or _clean_reason(concept_phrase)
            or (matched_content[0] if matched_content else "")
            or proof_name
            or evidence_name
        )
        visual = _image_specific_signal(image, title)
        business_anchor = evidence_name or proof_name or detail

        if concept_name and business_anchor and visual:
            return (
                f"推荐这张「{title}」，因为它{relation}“{concept_name}”，"
                f"并用“{business_anchor}”把卖点落到具体画面/功能上；"
                f"{visual}，适合市场同学快速说明这张图为什么贴合本次需求。"
            )
        if concept_name and business_anchor:
            return (
                f"推荐这张「{title}」，因为它{relation}“{concept_name}”，"
                f"核心证据集中在“{business_anchor}”，比泛泛卖点文案更适合解释本次选图理由。"
            )
        if detail:
            return (
                f"推荐这张「{title}」，因为它命中了“{detail}”，"
                "能把本次搜索需求落到具体素材表达上。"
            )
        return f"推荐这张「{title}」，因为它与本次搜索需求在标题、素材语义或业务关系上相关。"


def _first_reason_value(reasons: list[str], prefix: str) -> str | None:
    for reason in reasons:
        if reason.startswith(prefix):
            return reason[len(prefix) :].strip()
    return None


def _clean_reason(value: str | None) -> str:
    if not value:
        return ""
    return value.replace("（100%）", "").strip()


def _relation_label(role: str) -> str:
    return {
        "expresses": "主要表达",
        "supports": "可以支撑",
        "visual_related": "画面相关于",
    }.get(role, "匹配")


def _image_specific_signal(image: Image, asset_title: str) -> str:
    facts: list[str] = []
    if image.title and image.title != asset_title:
        facts.append(f"当前图名是“{image.title}”")
    if image.channel:
        facts.append(f"可用于{image.channel}渠道")
    group = image.asset_group
    if group and group.style_label:
        facts.append(f"画面风格是{group.style_label}")
    if group and group.is_scene_image is True:
        facts.append("属于场景化素材")
    elif group and group.is_scene_image is False:
        facts.append("属于功能/信息表达素材")
    return "，".join(facts)
