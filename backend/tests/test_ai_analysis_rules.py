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


def payload(*, tag_count: int = 20, secondary_labels=None):
    return {
        "image_type": "function",
        "image_summary": (
            "孩子在学习界面观看动画讲解数学知识点，突出同步校内讲清思路，"
            "不是只展示答案的普通题库页面。"
        ),
        "content_tags": [
            {
                "tag": f"内容标签{index}",
                "confidence": 0.9,
                "dimension": "object" if index % 2 else "scene",
            }
            for index in range(tag_count)
        ],
        "secondary_labels": secondary_labels
        if secondary_labels is not None
        else [
            {
                "system": "同步校内体系",
                "label": "动画精讲",
                "confidence": 0.92,
                "evidence_level": "A",
                "role": "primary",
                "reason": (
                    "画面直接展示动画课程和知识讲解，适合动画精讲，"
                    "不是课后小测或普通答案页。"
                ),
            }
        ],
        "recommended_search_words": [
            "动画讲解",
            "数学知识点",
            "同步校内",
            "讲清思路",
            "孩子听不懂老师讲课",
        ],
        "negative_tags": ["课后小测", "普通答案页"],
    }


def test_image_analysis_requires_about_twenty_content_tags():
    with pytest.raises(AppError) as exc_info:
        AiService(StaticProvider(payload(tag_count=7))).analyze_image(Path("unused.png"))

    assert exc_info.value.code == "model_response_invalid"
    assert exc_info.value.details == {"contentTagCount": 7}


def test_image_analysis_normalizes_known_english_dimensions():
    result = AiService(StaticProvider(payload())).analyze_image(Path("unused.png"))

    assert len(result.content_tags) == 20
    assert {item.dimension for item in result.content_tags} == {"物体", "场景"}


def test_image_analysis_rejects_unknown_closed_secondary_label():
    invalid_label = [
        {
            "system": "同步校内体系",
            "label": "模型临时发明的标签",
            "confidence": 0.9,
            "evidence_level": "A",
            "role": "primary",
            "reason": "无效标签。",
        }
    ]

    with pytest.raises(AppError) as exc_info:
        AiService(
            StaticProvider(payload(secondary_labels=invalid_label))
        ).analyze_image(Path("unused.png"))

    assert exc_info.value.code == "unknown_secondary_labels"


def test_image_analysis_requires_search_words_with_long_pain_phrase():
    invalid = payload()
    invalid["recommended_search_words"] = [
        "动画讲解",
        "知识点",
        "同步校内",
        "讲解",
        "课堂",
    ]

    with pytest.raises(AppError) as exc_info:
        AiService(StaticProvider(invalid)).analyze_image(Path("unused.png"))

    assert exc_info.value.code == "model_response_invalid"
    assert "真实痛点长短语" in exc_info.value.message


def test_image_analysis_requires_negative_tags():
    invalid = payload()
    invalid["negative_tags"] = []

    with pytest.raises(AppError) as exc_info:
        AiService(StaticProvider(invalid)).analyze_image(Path("unused.png"))

    assert exc_info.value.code == "model_response_invalid"
    assert exc_info.value.details == {"negativeTagCount": 0}


def test_image_analysis_requires_secondary_label_reason_boundary():
    invalid_label = [
        {
            "system": "同步校内体系",
            "label": "动画精讲",
            "confidence": 0.9,
            "evidence_level": "A",
            "role": "primary",
            "reason": "图片适合动画讲解知识点。",
        }
    ]

    with pytest.raises(AppError) as exc_info:
        AiService(
            StaticProvider(payload(secondary_labels=invalid_label))
        ).analyze_image(Path("unused.png"))

    assert exc_info.value.code == "model_response_invalid"
    assert exc_info.value.details == {"secondaryLabels": ["同步校内体系 > 动画精讲"]}


def test_image_analysis_rejects_generated_secondary_label_reason():
    invalid_label = [
        {
            "label_code": "animation_explanation",
            "confidence": 0.9,
            "evidence_level": "A",
            "role": "primary",
        }
    ]

    with pytest.raises(AppError) as exc_info:
        AiService(
            StaticProvider(payload(secondary_labels=invalid_label))
        ).analyze_image(Path("unused.png"))

    assert exc_info.value.code == "model_response_invalid"
    assert exc_info.value.details == {"secondaryLabels": ["同步校内体系 > 动画精讲"]}


def test_search_intent_normalizes_catalog_codes_to_chinese_names():
    result = AiService(
        StaticProvider(
            {
                "original_query": "孩子听不懂老师讲课",
                "normalized_query": "动画精讲",
                "search_intent": "寻找课堂听不懂时的讲解素材",
                "query_type": "pain_point_search",
                "expanded_level1_tags": [
                    {
                        "tag": "animation_explanation",
                        "relation": "exact",
                        "reason": "命中动画精讲",
                        "weight": 0.95,
                    }
                ],
                "matched_level2_categories": [
                    {
                        "category": "sync_school",
                        "relation": "direct",
                        "reason": "属于同步校内体系",
                        "weight": 0.8,
                    }
                ],
                "exclude_tags": ["instant_quiz"],
                "search_strategy": "优先召回动画精讲",
            }
        )
    ).understand_search("孩子听不懂老师讲课")

    assert result.expanded_level1_tags[0].tag == "同步校内体系 > 动画精讲"
    assert result.matched_level2_categories[0].category == "同步校内体系"
    assert result.exclude_tags == ["同步校内体系 > 课后小测"]
