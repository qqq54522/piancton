from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]

ACTIVE_DOCS = (
    "README.md",
    "backend/README.md",
    "docs/ARCHITECTURE.md",
    "docs/DEVELOPMENT_GUARDRAILS.md",
    "docs/SEARCH_MODES_AND_AI.md",
    "docs/SERVER_DEPLOYMENT_CHECKLIST.md",
    "docs/UX_UI_DESIGN_SYSTEM.md",
)

HISTORICAL_DOCS = (
    "docs/FRONTEND_REFACTOR_ROUND2.md",
    "docs/OPTIMIZATION_PLAN.md",
    "docs/REFACTOR_AND_INTENT_EXECUTION_PLAN.md",
    "docs/SEARCH_BUSINESS_INTENT_MAP.md",
    "docs/TAGGING_SYSTEM_IMPROVEMENT_PLAN.md",
)

RETIRED_ACTIVE_DOC_SNIPPETS = (
    "标签树、允许打标标签必选",
    "生成 18–22 个中文隐形内容标签",
    "状态：已接入“精准搜索 / 智能搜索”",
    "搜索已支持精准搜索与智能搜索手动切换",
    "上传和编辑图片时至少选择一个已启用且允许打标的标签",
    "- [ ] 标签树与筛选",
    "`seed_taxonomy` 除了同步六大体系目录，也会把旧的 `image_tags`",
)


def _read(relative_path: str) -> str:
    return (PROJECT_ROOT / relative_path).read_text(encoding="utf-8")


def test_active_docs_do_not_restore_retired_product_contracts():
    violations: list[str] = []
    for relative_path in ACTIVE_DOCS:
        content = _read(relative_path)
        for snippet in RETIRED_ACTIVE_DOC_SNIPPETS:
            if snippet in content:
                violations.append(f"{relative_path}: {snippet}")

    assert violations == []


def test_active_docs_point_to_the_master_plan():
    missing = [
        relative_path
        for relative_path in ACTIVE_DOCS
        if "IMAGE_SEARCH_REBUILD_MASTER_PLAN.md" not in _read(relative_path)
    ]

    assert missing == []


def test_historical_docs_are_explicitly_marked():
    missing = [
        relative_path
        for relative_path in HISTORICAL_DOCS
        if "> **历史文档说明**" not in _read(relative_path)
    ]

    assert missing == []


def test_master_and_project_log_publish_the_same_current_phase():
    master = _read("docs/IMAGE_SEARCH_REBUILD_MASTER_PLAN.md")
    project_log = _read("docs/IMAGE_SEARCH_REBUILD_PROJECT_LOG.md")
    ux_rules = _read("docs/UX_UI_DESIGN_SYSTEM.md")
    readme = _read("README.md")
    branding = _read("client/src/lib/branding.ts")
    layout = _read("client/src/components/Layout.tsx")
    login = _read("client/src/pages/Login/Login.tsx")
    html = _read("client/index.html")

    assert "状态：Phase 0～6 工程完成" in master
    assert "当前范围：Phase 0～Phase 6" in project_log
    assert "D026" in master
    assert "D028" in master
    assert "D029" in master
    assert "D030" in master
    assert "文档一致性自动测试" in master
    assert "首次上传最多录入 5 条" in master
    assert "不是素材搜索话术的永久总上限" in master
    assert "系统正式产品名称统一为“卖点智库”" in master
    assert "# 卖点智库 UX/UI 设计规范" in ux_rules
    assert readme.startswith("# 卖点智库\n")
    assert "PRODUCT_NAME = '卖点智库'" in branding
    assert "PRODUCT_NAME" in layout
    assert "PRODUCT_NAME" in login
    assert "<title>卖点智库</title>" in html
