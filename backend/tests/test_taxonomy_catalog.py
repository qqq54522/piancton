import pytest

from app.ai.skill_loader import (
    build_selling_point_prompt,
    build_system_routing_prompt,
    build_task_prompt,
)
from app.domain.taxonomy_catalog import load_taxonomy_catalog


def test_catalog_has_stable_expected_shape():
    catalog = load_taxonomy_catalog()

    assert catalog.version == "2026.06.1"
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

    assert "权威标签目录（版本 2026.06.1）" in prompt
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

    assert "# 同步自学体系" in prompt
    assert "同步自学运行时意图摘要" in prompt
    assert "## 体系业务原文" in prompt
    assert "> 身边有 AI 名师，随时随地帮助解决难题，孩子自驱式完成学习。" in prompt
    assert "## 第一批意图用例" in prompt
    assert "## 待确认" in prompt
    assert "`ai_tutor_qa` / AI 私教随时答疑" in prompt
    assert "`photo_guided_learning` / AI 拍题精学" in prompt
    assert "角色职责与证据顺序" in prompt
    assert "对象与主动作决定候选范围" in prompt
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

    assert "# 同步规划体系" in prompt
    assert "### 原版价值与痛点拆解" in prompt
    assert "# 同步伴学体系" in prompt
    assert "### 证明点" in prompt
    assert "# 六大体系跨体系校准" in prompt
    assert "## 16 个卖点最小充分证据" in prompt
    assert "# 同步考点体系" not in prompt


def test_full_search_intent_prompt_cannot_be_built_without_system_route():
    with pytest.raises(ValueError, match="必须先调用"):
        build_task_prompt("search_intent_understanding")


def test_non_intent_prompt_does_not_load_six_system_intent_summaries():
    prompt = build_task_prompt(
        "image_content_analysis",
        catalog_text="# 当前数据库启用概念",
    )

    assert "同步校内运行时意图摘要" not in prompt
    assert "同步考点运行时意图摘要" not in prompt
