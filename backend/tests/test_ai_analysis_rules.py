from pathlib import Path

import pytest

from app.core.errors import AppError
from app.services.ai_service import AiService


class StaticProvider:
    name = "test"
    configured = True

    def __init__(self, payload):
        self.payload = payload
        self.last_request = None

    def generate_json(self, request):
        self.last_request = request
        return self.payload


class SequenceProvider:
    name = "test"
    configured = True

    def __init__(self, payloads):
        self.payloads = iter(payloads)
        self.requests = []

    def generate_json(self, request):
        self.requests.append(request)
        return next(self.payloads)


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


def test_pre_upload_phrase_generation_returns_exact_requested_count():
    provider = StaticProvider(
        {
            "phrases": [
                "找一张能体现和学校教材进度一致的图",
                "找一张学校学到哪课程就讲到哪的图",
                "想找一张教材目录和课程目录能对应上的素材",
            ]
        }
    )

    result = AiService(provider).generate_asset_search_phrases(
        Path("unused.upload"),
        count=3,
        title="课程同步",
        concept_code="school_sync",
        image_media_type="image/png",
    )

    assert result.phrases == [
        "找一张能体现和学校教材进度一致的图",
        "找一张学校学到哪课程就讲到哪的图",
        "想找一张教材目录和课程目录能对应上的素材",
    ]
    assert provider.last_request is not None
    assert "业务小白" in provider.last_request.input_text
    assert "课程版本、章节和学校课堂进度保持一致" in (
        provider.last_request.input_text
    )
    assert "图片用于让话术确实能找到这张素材" in provider.last_request.prompt
    assert "找一张能体现和学校教材进度一致的图" in (
        provider.last_request.prompt
    )


def test_pre_upload_phrase_generation_rejects_wrong_model_count():
    provider = StaticProvider({"phrases": ["只有一条", "只有两条"]})
    with pytest.raises(AppError) as exc_info:
        AiService(provider).generate_asset_search_phrases(
            Path("unused.png"),
            count=3,
        )

    assert exc_info.value.code == "model_response_invalid"
    assert exc_info.value.details == {"expected": 3, "actual": 2}


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
    route = {
        "original_query": "孩子听不懂老师讲课",
        "route_type": "single_system",
        "candidate_systems": [
            {
                "code": "sync_school",
                "relation": "primary",
                "reason": "课堂知识没有听懂",
                "weight": 0.96,
            }
        ],
        "excluded_systems": [],
    }
    provider = SequenceProvider(
        [
            route,
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
                        "concept": "animation_explanation",
                        "relation": "direct",
                        "reason": "课堂没听懂，需要动画讲透",
                        "weight": 0.95,
                    }
                ],
                "excluded_concepts": ["instant_quiz"],
                "search_strategy": "优先召回动画精讲",
            },
            {
                "original_query": "孩子听不懂老师讲课",
                "matched_proof_points": [],
                "matched_evidence_points": [],
                "search_strategy": "查询停留在动画精讲卖点层",
            },
        ]
    )
    result = AiService(provider).understand_search("孩子听不懂老师讲课")

    assert result.expanded_terms[0].term == "同步校内体系 > 动画精讲"
    assert result.matched_business_concepts[0].concept == "同步校内体系 > 动画精讲"
    assert result.excluded_concepts == ["同步校内体系 > 课后小测"]
    assert [request.task for request in provider.requests] == [
        "search_system_routing",
        "search_intent_understanding",
        "search_proof_point_understanding",
    ]
    assert "animation_explanation" not in provider.requests[0].prompt
    assert "`animation_explanation` / 动画精讲" in provider.requests[1].prompt
    assert "ai_tutor_qa" not in provider.requests[1].prompt


def test_visual_search_stops_after_system_routing():
    provider = SequenceProvider(
        [
            {
                "original_query": "蓝色横版有孩子的图",
                "route_type": "visual_scene",
                "candidate_systems": [],
                "excluded_systems": [],
            }
        ]
    )

    result = AiService(provider).understand_search("蓝色横版有孩子的图")

    assert result.query_type == "visual_scene_search"
    assert result.matched_business_concepts == []
    assert [request.task for request in provider.requests] == [
        "search_system_routing"
    ]


def test_second_layer_rejects_concepts_outside_routed_system():
    provider = SequenceProvider(
        [
            {
                "original_query": "随时找 AI 回答问题",
                "route_type": "single_system",
                "candidate_systems": [
                    {
                        "code": "sync_self_study",
                        "relation": "primary",
                        "reason": "AI 即时答疑",
                        "weight": 0.97,
                    }
                ],
                "excluded_systems": [],
            },
            {
                "original_query": "随时找 AI 回答问题",
                "normalized_query": "真人老师督学",
                "search_intent": "错误跨体系返回",
                "query_type": "business_intent_search",
                "expanded_terms": [],
                "matched_business_concepts": [
                    {
                        "concept": "human_teacher_supervision",
                        "relation": "direct",
                        "reason": "模型越界",
                        "weight": 0.9,
                    }
                ],
                "excluded_concepts": [],
                "search_strategy": "错误",
            },
        ]
    )

    with pytest.raises(AppError) as exc_info:
        AiService(provider).understand_search("随时找 AI 回答问题")

    assert exc_info.value.code == "model_response_invalid"
    assert "候选体系之外" in exc_info.value.message
