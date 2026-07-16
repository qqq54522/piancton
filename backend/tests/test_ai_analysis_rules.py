from pathlib import Path

import pytest

from app.core.errors import AppError
from app.services.ai_service import AiService


class StaticProvider:
    name = "test"
    configured = True

    def __init__(self, payload):
        self.payload = payload

    def generate_json(self, _request):
        return self.payload


def payload(*, concept_suggestions=None):
    return {
        "image_summary": (
            "孩子在学习界面观看动画讲解数学知识点，突出同步校内讲清思路，"
            "不是只展示答案的普通题库页面。"
        ),
        "semantic_profile": {
            "visual_facts": ["学习界面", "动画讲解数学知识点", "学生观看课程"],
            "scenes": ["同步课程内容展示场景"],
            "asset_search_phrases": [
                "动画讲解",
                "孩子听不懂老师讲课",
                "同步校内知识点讲解",
                "讲清学习思路",
                "课堂内容听不懂",
            ],
        },
        "concept_suggestions": concept_suggestions
        if concept_suggestions is not None
        else [
            {
                "system_name": "同步校内体系",
                "concept_name": "动画精讲",
                "confidence": 0.92,
                "evidence_level": "A",
                "relation_role": "expresses",
                "reason": (
                    "画面直接展示动画课程和知识讲解，适合动画精讲，"
                    "不是课后小测或普通答案页。"
                ),
            }
        ],
    }


def test_image_analysis_uses_streamlined_semantic_profile_v3_without_content_tags():
    result = AiService(StaticProvider(payload())).analyze_image(Path("unused.png"))

    assert result.semantic_profile.schema_version == 3
    assert "动画讲解数学知识点" in result.semantic_profile.visual_facts
    assert result.semantic_profile.scenes == ["同步课程内容展示场景"]
    assert "孩子听不懂老师讲课" in result.semantic_profile.asset_search_phrases
    assert set(result.semantic_profile.model_dump()) == {
        "schema_version",
        "visual_facts",
        "scenes",
        "asset_search_phrases",
    }


def test_image_analysis_ignores_legacy_fixed_tag_fields():
    provider_payload = payload()
    provider_payload["content_tags"] = [
        {"tag": "平板", "confidence": 0.95, "dimension": "物体"}
    ]
    provider_payload["recommended_search_words"] = ["旧推荐词"]
    provider_payload["semantic_profile"].update(
        {
            "ocr_text": ["数学精讲"],
            "subjects": ["学生"],
            "actions": ["观看课程"],
            "visual_style": ["蓝色界面"],
            "visible_product_features": ["动画播放"],
            "negative_visual_concepts": ["普通答案页"],
        }
    )

    result = AiService(StaticProvider(provider_payload)).analyze_image(Path("unused.png"))

    assert "content_tags" not in result.model_dump()
    assert "recommended_search_words" not in result.model_dump()
    assert "ocr_text" not in result.semantic_profile.model_dump()
    assert "negative_visual_concepts" not in result.semantic_profile.model_dump()


def test_image_analysis_allows_provider_payload_without_semantic_profile():
    provider_payload = payload()
    provider_payload.pop("semantic_profile")

    result = AiService(StaticProvider(provider_payload)).analyze_image(Path("unused.png"))

    assert result.semantic_profile.schema_version == 3
    assert result.semantic_profile.visual_facts


def test_image_analysis_rejects_unknown_closed_concept_suggestion():
    invalid_label = [
        {
            "system_name": "同步校内体系",
            "concept_name": "模型临时发明的概念",
            "confidence": 0.9,
            "evidence_level": "A",
            "relation_role": "expresses",
            "reason": "无效标签。",
        }
    ]

    with pytest.raises(AppError) as exc_info:
        AiService(
            StaticProvider(payload(concept_suggestions=invalid_label))
        ).analyze_image(Path("unused.png"))

    assert exc_info.value.code == "unknown_concept_suggestions"


def test_image_analysis_allows_short_asset_specific_search_phrases():
    valid = payload()
    valid["semantic_profile"]["asset_search_phrases"] = [
        "动画讲解",
        "知识点",
        "同步校内",
        "讲解",
        "课堂",
    ]

    result = AiService(StaticProvider(valid)).analyze_image(Path("unused.png"))
    assert result.semantic_profile.asset_search_phrases[-1] == "课堂"


def test_image_analysis_rejects_too_many_asset_specific_search_phrases():
    invalid = payload()
    invalid["semantic_profile"]["asset_search_phrases"] = [
        f"素材独有表达{index}" for index in range(9)
    ]

    with pytest.raises(AppError) as exc_info:
        AiService(StaticProvider(invalid)).analyze_image(Path("unused.png"))

    assert exc_info.value.code == "model_response_invalid"


def test_image_analysis_requires_concept_suggestion_reason_boundary():
    invalid_label = [
        {
            "system_name": "同步校内体系",
            "concept_name": "动画精讲",
            "confidence": 0.9,
            "evidence_level": "A",
            "relation_role": "expresses",
            "reason": "图片适合动画讲解知识点。",
        }
    ]

    with pytest.raises(AppError) as exc_info:
        AiService(
            StaticProvider(payload(concept_suggestions=invalid_label))
        ).analyze_image(Path("unused.png"))

    assert exc_info.value.code == "model_response_invalid"
    assert exc_info.value.details == {"conceptSuggestions": ["同步校内体系 > 动画精讲"]}


def test_image_analysis_rejects_generated_concept_suggestion_reason():
    invalid_label = [
        {
            "concept_code": "animation_explanation",
            "confidence": 0.9,
            "evidence_level": "A",
            "relation_role": "expresses",
        }
    ]

    with pytest.raises(AppError) as exc_info:
        AiService(
            StaticProvider(payload(concept_suggestions=invalid_label))
        ).analyze_image(Path("unused.png"))

    assert exc_info.value.code == "model_response_invalid"
    assert exc_info.value.details == {"conceptSuggestions": ["同步校内体系 > 动画精讲"]}


def test_search_intent_normalizes_catalog_codes_to_chinese_names():
    result = AiService(
        StaticProvider(
            {
                "original_query": "孩子听不懂老师讲课",
                "normalized_query": "动画精讲",
                "search_intent": "寻找课堂听不懂时的讲解素材",
                "query_type": "pain_point_search",
                "expanded_terms": [
                    {
                        "term": "animation_explanation",
                        "relation": "exact",
                        "reason": "命中动画精讲",
                        "weight": 0.95,
                    }
                ],
                "matched_business_concepts": [
                    {
                        "concept": "sync_school",
                        "relation": "direct",
                        "reason": "属于同步校内体系",
                        "weight": 0.8,
                    }
                ],
                "excluded_concepts": ["instant_quiz"],
                "search_strategy": "优先召回动画精讲",
            }
        )
    ).understand_search("孩子听不懂老师讲课")

    assert result.expanded_terms[0].term == "同步校内体系 > 动画精讲"
    assert result.matched_business_concepts[0].concept == "同步校内体系"
    assert result.excluded_concepts == ["同步校内体系 > 课后小测"]
