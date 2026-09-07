import pytest

from app.ai.skill_loader import (
    build_proof_point_prompt,
    build_search_route_explanation_prompt,
    build_selling_point_prompt,
    build_system_routing_prompt,
    build_task_prompt,
    render_selling_point_decision_cards,
)
from app.domain.taxonomy_catalog import load_taxonomy_catalog


def test_catalog_has_stable_expected_shape():
    catalog = load_taxonomy_catalog()

    assert catalog.version == "2026-07-23.1"
    assert len(catalog.system_nodes) == 6
    assert len(catalog.image_label_nodes) == 16
    assert len(catalog.copy_points) == 30
    assert all(not node.assignable for node in catalog.system_nodes)
    assert all(node.assignable for node in catalog.image_label_nodes)


def test_every_copy_point_maps_to_existing_image_labels():
    catalog = load_taxonomy_catalog()
    node_by_code = catalog.node_by_code

    for point in catalog.copy_points:
        assert point.target_label_codes
        assert all(
            node_by_code[target_code].node_type == "image_label"
            for target_code in point.target_label_codes
        )


def test_retired_image_analysis_prompt_is_not_a_runtime_task():
    with pytest.raises(ValueError, match="没有绑定项目 Skill"):
        build_task_prompt("image_content_analysis")

    catalog = load_taxonomy_catalog()
    assert catalog.node_by_code["photo_guided_learning"].name == "AI拍题精学"


def test_search_intent_prompt_progressively_loads_only_routed_system():
    router_prompt = build_system_routing_prompt()

    assert "sync_school" in router_prompt
    assert "sync_companion" in router_prompt
    assert "animation_explanation" not in router_prompt
    assert "ai_tutor_qa" not in router_prompt
    assert "matched_business_concepts" not in router_prompt

    prompt = build_selling_point_prompt(
        ("sync_self_study",),
        catalog_text=(
            "# 候选体系目录\n"
            "`ai_tutor_qa` / AI私教答疑\n"
            "`photo_guided_learning` / AI拍题精学"
        ),
    )

    assert "## 同步自学运行时意图摘要" in prompt
    assert "同步自学运行时意图摘要" in prompt
    assert "`ai_tutor_qa` / AI私教答疑" in prompt
    assert "`photo_guided_learning` / AI拍题精学" in prompt
    assert "第二层：候选体系内卖点判断" in prompt
    assert "matched_proof_points` 必须是空数组" in prompt
    assert "### 证明点" not in prompt
    assert "候选体系证据表达点目录" not in prompt
    assert "# 同步校内体系" not in prompt
    assert "# 同步伴学体系" not in prompt
    assert "# 六大体系跨体系校准" not in prompt

    assert "角色职责与决策纪律" in router_prompt
    assert "此层不得判断具体卖点" in router_prompt


def test_multi_system_selling_point_prompt_adds_cross_system_calibration():
    prompt = build_selling_point_prompt(
        ("sync_planning", "sync_companion"),
        catalog_text="# 候选体系目录",
    )

    assert "## 同步规划运行时意图摘要" in prompt
    assert "## 同步伴学运行时意图摘要" in prompt
    assert "## 跨体系运行时校准摘要" in prompt
    assert "### 证明点" not in prompt
    assert "# 同步考点体系" not in prompt


def test_selling_point_decision_cards_are_scoped_to_routed_system():
    cards = render_selling_point_decision_cards(("sync_self_study",))

    assert "# 候选体系卖点判断卡片" in cards
    assert "### `photo_guided_learning` / AI拍题精学" in cards
    assert "一句话判定：如果用户重点在“拍当前不会的一道题" in cards
    assert "背后意思：这个卖点背后解决的是拍照搜题容易变成抄答案的问题" in cards
    assert "边界逻辑：它判断的是一道当前题的拍题学习流程" in cards
    assert "### `ai_error_book` / AI错题本" in cards
    assert "### `school_sync` / 同步校内" not in cards
    assert "### `focused_excellence` / 专项培优" not in cards


def test_selling_point_prompt_can_disable_decision_cards():
    prompt = build_selling_point_prompt(
        ("sync_self_study",),
        catalog_text="# 候选体系目录",
        include_decision_cards=False,
    )

    assert "# 候选体系卖点判断卡片" not in prompt
    assert "## 同步自学运行时意图摘要" in prompt


def test_selling_point_prompt_loads_decision_cards_before_runtime_phrases():
    prompt = build_selling_point_prompt(
        ("sync_self_study",),
        catalog_text="# 候选体系目录",
        include_decision_cards=True,
    )

    cards_index = prompt.index("# 候选体系卖点判断卡片")
    summary_index = prompt.index("## 同步自学运行时意图摘要")
    catalog_index = prompt.index("# 候选体系目录")
    assert cards_index < summary_index < catalog_index
    assert "公共话术只能作为辅助入口，不能覆盖卡片边界" in prompt
    assert "oneSentenceDecision → meaningBehind → boundaryLogic" in prompt


def test_third_layer_prompt_only_loads_selected_selling_point_proofs():
    prompt = build_proof_point_prompt(("animation_explanation",))

    assert "第三层：已命中卖点内证明点判断" in prompt
    assert "pp_animation_pedagogy_design" in prompt
    assert "ep_school_short_animation_lesson" in prompt
    assert "pp_school_quiz_immediate_feedback" not in prompt
    assert "pp_companion_report_core_metrics" not in prompt


def test_full_search_intent_prompt_cannot_be_built_without_system_route():
    with pytest.raises(ValueError, match="必须先调用"):
        build_task_prompt("search_intent_understanding")


def test_manual_review_keeps_transfer_method_and_error_boundaries():
    catalog = load_taxonomy_catalog()
    node_by_code = catalog.node_by_code

    transfer = node_by_code["transfer_practice"]
    universal = node_by_code["universal_method"]
    focused = node_by_code["focused_excellence"]
    error_book = node_by_code["ai_error_book"]
    common_mistakes = next(
        item for item in catalog.copy_points if item.code == "common_mistakes"
    )

    assert "相似题推荐" in transfer.positive_evidence
    assert "一题多解" in universal.positive_evidence
    assert "换题不会" not in universal.positive_evidence
    assert "全网高频错题" in focused.aliases
    assert "这个学生自己做错的题" in error_book.definition
    assert common_mistakes.target_label_codes == ("focused_excellence",)


def test_search_route_explanation_prompt_does_not_load_six_system_intent_summaries():
    prompt = build_search_route_explanation_prompt()

    assert "同步校内运行时意图摘要" not in prompt
    assert "同步考点运行时意图摘要" not in prompt
    assert "只解释 `query` 与 `matched_selling_points` 之间的关系" in prompt
    assert "返回数量" in prompt
    assert "未指定渠道" in prompt
    assert "卡片展示规则" in prompt
