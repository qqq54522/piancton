import pytest

from app.ai.skill_loader import (
    build_proof_point_prompt,
    build_selling_point_prompt,
    build_system_routing_prompt,
    build_task_prompt,
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


def test_prompt_is_built_from_versioned_catalog():
    prompt = build_task_prompt("image_content_analysis")

    assert "权威标签目录（版本 2026-07-23.1）" in prompt
    assert "`photo_guided_learning` / AI拍题精学" in prompt
    assert "模型只能返回以上目录中存在的稳定 code" in prompt


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


def test_non_intent_prompt_does_not_load_six_system_intent_summaries():
    prompt = build_task_prompt(
        "image_content_analysis",
        catalog_text="# 当前数据库启用概念",
    )

    assert "同步校内运行时意图摘要" not in prompt
    assert "同步考点运行时意图摘要" not in prompt
