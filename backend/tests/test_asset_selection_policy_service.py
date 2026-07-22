from types import SimpleNamespace

import pytest

from app.domain.asset_text_relevance import AssetSelectionEvidence, image_rank_key
from app.services.asset_selection_policy_service import AssetSelectionPolicyService
from app.services.search_models import SearchHit


def _hit(title: str) -> SearchHit:
    group = SimpleNamespace(title=title, search_phrases=[])
    image = SimpleNamespace(title=title, asset_group=group)
    return SearchHit(image=image)


def _link(code: str):
    return SimpleNamespace(
        concept=SimpleNamespace(code=code),
        relation_role="expresses",
        concept_id=code,
    )


@pytest.mark.parametrize(
    ("concept_code", "query", "matching_title"),
    [
        ("animation_explanation", "找学校课堂案例", "学校课堂实证"),
        ("new_curriculum_prediction", "新中考学校案例", "公办学校教研案例"),
        ("universal_method", "底层方法学校试点", "中学试点效果实证"),
        ("ai_learning_plan", "AI定制数据基础", "学习行为数据规模"),
        ("rapid_preview_review", "预习效率数据", "预习效果数据"),
        ("learning_report", "微信学习周报", "微信家长端周报"),
    ],
)
def test_evidence_requirements_keep_proof_queries_empty_until_matching_asset_exists(
    concept_code: str, query: str, matching_title: str
):
    service = AssetSelectionPolicyService()
    accepted_links = [_link(concept_code)]
    evidence = AssetSelectionEvidence()

    assert not service.allows(
        _hit("同卖点通用素材"),
        accepted_links,
        query,
        {concept_code},
        evidence,
    )
    assert service.allows(
        _hit(matching_title),
        accepted_links,
        query,
        {concept_code},
        evidence,
    )


@pytest.mark.parametrize(
    "query",
    [
        "找那种几分钟就能讲明白一个知识点的图",
        "有没有一节课不长，但一个点能讲透的",
    ],
)
def test_short_animation_micro_lesson_query_requires_matching_asset_detail(query: str):
    service = AssetSelectionPolicyService()
    accepted_links = [_link("animation_explanation")]
    evidence = AssetSelectionEvidence()

    assert not service.allows(
        _hit("抽象题目变为有趣动画"),
        accepted_links,
        query,
        {"animation_explanation"},
        evidence,
    )
    assert service.allows(
        _hit("5-8分钟讲透知识点，学完就练"),
        accepted_links,
        query,
        {"animation_explanation"},
        evidence,
    )


def test_direct_query_to_asset_text_ranks_before_generic_proof_language():
    direct = AssetSelectionEvidence(
        query_text_score=0.39,
        proof_asset_matched=True,
        proof_asset_score=0.92,
    )
    generic = AssetSelectionEvidence(
        phrase_matched=True,
        phrase_score=0.96,
        proof_asset_matched=True,
        proof_asset_score=0.92,
    )

    assert image_rank_key(direct, 0.8) > image_rank_key(generic, 0.98)
