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
    home_header = _read("client/src/pages/ImageHome/ImageHomeHeader.tsx")
    search_result = _read("client/src/pages/ImageHome/SemanticSearchResult/index.tsx")
    search_card = _read("client/src/pages/ImageHome/SemanticSearchResult/ScoredImageCard.tsx")
    upload_phrases = _read("client/src/pages/ImageHome/UploadSearchPhraseFields.tsx")
    inheritance = _read("client/src/pages/ImageHome/ConceptPhraseInheritancePanel.tsx")
    concept_page = _read("client/src/pages/AdminConcepts/AdminConcepts.tsx")
    asset_phrase_panel = _read(
        "client/src/pages/ImageDetail/asset/AssetPhraseReviewPanel.tsx"
    )
    asset_concept_panel = _read(
        "client/src/pages/ImageDetail/asset/AssetConceptReviewPanel.tsx"
    )
    asset_versions_panel = _read(
        "client/src/pages/ImageDetail/asset/AssetVersionsPanel.tsx"
    )
    asset_variant_delete_dialog = _read(
        "client/src/pages/ImageDetail/asset/AssetVariantDeleteDialog.tsx"
    )
    html = _read("client/index.html")

    assert "状态：Phase 0～6 工程完成" in master
    assert "当前范围：Phase 0～Phase 6" in project_log
    assert "D026" in master
    assert "D028" in master
    assert "D029" in master
    assert "D030" in master
    assert "D031" in master
    assert "D032" in master
    assert "D033" in master
    assert "D034" in master
    assert "D035" in master
    assert "D036" in master
    assert "文档一致性自动测试" in master
    assert "首次上传最多录入 5 条" in master
    assert "不是素材搜索话术的永久总上限" in master
    assert "系统正式产品名称统一为“卖点智库”" in master
    assert "# 卖点智库 UX/UI 设计规范" in ux_rules
    assert readme.startswith("# 卖点智库\n")
    assert "PRODUCT_NAME = '卖点智库'" in branding
    assert "PRODUCT_NAME" in layout
    assert "PRODUCT_NAME" in login
    assert "title={PRODUCT_NAME}" in home_header
    assert "业务素材库" not in home_header
    assert "外部增强" not in search_result
    assert "智能语义搜索暂时响应较慢" in search_result
    assert "就是这张" in search_card
    assert "当前素材独有话术" in upload_phrases
    assert "公共话术只在卖点层维护一次" in inheritance
    assert "辅助关键词" in inheritance
    assert 'title="卖点与公共话术"' in concept_page
    assert "卖点管理" in layout
    assert "AI培训" not in concept_page
    assert "素材独有话术列表" in asset_phrase_panel
    assert "AI 待确认候选" in asset_phrase_panel
    assert "overflow-y-auto" in asset_phrase_panel
    assert 'role="switch"' in asset_concept_panel
    assert "需要为这张素材补充其他卖点关系时再开启" in asset_concept_panel
    assert "image.id !== group.primaryImageId" in asset_versions_panel
    assert "删除版本" in asset_versions_panel
    assert "移入回收站" in asset_variant_delete_dialog
    assert "只会移除这个版本" in asset_variant_delete_dialog
    assert "和学校课程一致" in master
    assert "外部服务只增强" in master
    assert "当前本地素材库已有 1 张" in readme
    assert "当前本地素材库为空" not in readme
    assert "当前正式素材库为空" not in _read("docs/SEARCH_MODES_AND_AI.md")
    assert "本地正式素材库当前为空" not in _read("docs/ARCHITECTURE.md")
    assert "<title>卖点智库</title>" in html
