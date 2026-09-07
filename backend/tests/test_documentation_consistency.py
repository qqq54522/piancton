from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[2]
pytestmark = pytest.mark.skipif(
    not (PROJECT_ROOT / "README.md").is_file(),
    reason="文档一致性检查只在完整源码工作区运行，生产后端镜像不打包项目文档",
)

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
    global_search = _read("client/src/pages/ImageHome/GlobalImageSearch.tsx")
    search_result = _read("client/src/pages/ImageHome/SemanticSearchResult/index.tsx")
    search_card = _read("client/src/pages/ImageHome/SemanticSearchResult/ScoredImageCard.tsx")
    search_constants = _read("client/src/pages/ImageHome/SemanticSearchResult/constants.ts")
    upload_dialog = _read("client/src/pages/ImageHome/UploadDialog.tsx")
    concept_page = _read("client/src/pages/AdminConcepts/AdminConcepts.tsx")
    image_ai_panel = _read("client/src/pages/ImageDetail/ImageAiAnalysisPanel.tsx")
    semantic_profile_presentation = _read(
        "client/src/pages/ImageDetail/semanticProfilePresentation.ts"
    )
    concept_phrase_presentation = _read(
        "client/src/features/assets/conceptPhrasePresentation.ts"
    )
    asset_concept_panel = _read(
        "client/src/pages/ImageDetail/asset/AssetConceptReviewPanel.tsx"
    )
    asset_versions_panel = _read(
        "client/src/pages/ImageDetail/asset/AssetVersionsPanel.tsx"
    )
    asset_version_dialog = _read(
        "client/src/pages/ImageDetail/asset/AssetVersionDialog.tsx"
    )
    asset_variant_delete_dialog = _read(
        "client/src/pages/ImageDetail/asset/AssetVariantDeleteDialog.tsx"
    )
    asset_actions = _read("client/src/features/assets/useAssetActions.ts")
    related_image_service = _read("backend/app/services/related_image_service.py")
    asset_api = _read("backend/app/api/v1/assets.py")
    ai_api = _read("backend/app/api/v1/ai.py")
    image_analysis_service = _read("backend/app/services/image_analysis_service.py")
    asset_relation_service = _read("backend/app/services/asset_relation_service.py")
    database_search_recall = _read("backend/app/services/database_search_recall.py")
    image_repository = _read("backend/app/repositories/image_repository.py")
    image_semantic_profile = _read(
        "backend/app/services/image_semantic_profile_service.py"
    )
    ai_schema = _read("backend/app/schemas/ai.py")
    image_schema = _read("backend/app/schemas/image.py")
    ai_rules = _read("skills/analyze-image-asset/RULES.md")
    meilisearch_client = _read("backend/app/services/meilisearch_client.py")
    search_index = _read("backend/app/services/search_index.py")
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
    assert "D037" in master
    assert "D038" in master
    assert "D039" in master
    assert "D040" in master
    assert "D041" in master
    assert "D042" in master
    assert "D043" in master
    assert "D044" in master
    assert "D045" in master
    assert "D046" in master
    assert "D047" in master
    assert "D048" in master
    assert "D049" in master
    assert "D050" in master
    assert "文档一致性自动测试" in master
    assert "VikingDB" in master
    assert "系统正式产品名称统一为“卖点智库”" in master
    assert "# 卖点智库 UX/UI 设计规范" in ux_rules
    assert readme.startswith("# 卖点智库\n")
    assert "PRODUCT_NAME = '卖点智库'" in branding
    assert "PRODUCT_NAME" in layout
    assert "PRODUCT_NAME" in login
    assert "title={PRODUCT_NAME}" in home_header
    assert "业务素材库" not in home_header
    assert "外部增强" not in search_result
    assert "本次没有识别出可靠卖点" in search_result
    assert "外部语义增强未在时限内完成" in search_result
    assert "「{keyword}」的素材结果" not in search_result
    assert "推荐结果后再缩小" in ux_rules or "推荐结果后再缩小" in _read(
        "docs/DEVELOPMENT_GUARDRAILS.md"
    )
    assert 'aria-label="按使用渠道筛选"' in global_search
    assert 'aria-label="按场景图筛选"' in global_search
    concept_presentation = _read(
        "client/src/pages/ImageHome/SemanticSearchResult/searchConceptPresentation.ts"
    )
    assert "就是这张" in search_card
    assert "searchIntentTitle" in search_result
    assert "本次识别到的卖点" in concept_presentation
    assert "你可能在找" in concept_presentation
    assert "本次需求同时涉及" in concept_presentation
    assert "resultRecommendedPoint" in search_card
    assert "matchedQueryConcepts" in concept_presentation
    assert "没有合适素材提交需求" in search_constants
    assert "label: '提交素材需求'" not in search_constants
    assert "@client/src/components/ui/select" in search_card
    assert "业务筛选信息" in upload_dialog
    assert "不触发 AI 分析" in upload_dialog
    assert "files.length <= 1" in upload_dialog
    assert "单张上传可以在这里修改名称" in upload_dialog
    assert "styleLabel" in upload_dialog
    assert "isSceneImage" in upload_dialog
    assert 'title="业务卖点管理"' in concept_page
    assert "作为火山向量路由命中后的本地素材归属标签" in concept_page
    assert "卖点管理" in layout
    assert "AI培训" not in concept_page
    assert "new Set" in concept_phrase_presentation
    assert "link.origin === 'manual'" in concept_phrase_presentation
    assert "visibleSemanticProfileGroups" in image_ai_panel
    assert "页面只展示画面事实、场景和素材独有搜索表达" in image_ai_panel
    assert "title: '画面事实'" in semantic_profile_presentation
    assert "title: '场景'" in semantic_profile_presentation
    assert "title: '素材独有搜索表达'" in semantic_profile_presentation
    for hidden_group in (
        "OCR 文字",
        "主体",
        "动作",
        "视觉风格",
        "画面可见产品功能",
        "画面排除边界",
        "客观内容标签",
    ):
        assert hidden_group not in image_ai_panel
        assert hidden_group not in semantic_profile_presentation
    assert 'role="switch"' in asset_concept_panel
    assert "selectPendingConceptSuggestions" in asset_concept_panel
    assert "需要为这张素材补充其他卖点关系时再开启" in asset_concept_panel
    assert "image.id !== group.primaryImageId" in asset_versions_panel
    assert "删除版本" in asset_versions_panel
    assert "已继承主图业务信息" in asset_versions_panel
    assert "不运行 AI 分析" in asset_version_dialog
    assert "移入回收站" in asset_variant_delete_dialog
    assert "只会移除这个版本" in asset_variant_delete_dialog
    assert "queryKey: ['image-detail']" in asset_actions
    assert "candidate.asset_group_id != image.asset_group_id" in related_image_service
    assert 'if asset_role != "derivative"' in asset_api
    assert 'search-phrases' not in asset_api
    assert "derivative_analysis_not_required" in ai_api
    assert "group.primary_image_id == image.id" in image_analysis_service
    assert 'if phrase.review_status == "accepted"' in search_index
    assert 'if item.review_status == "accepted"' in database_search_recall
    assert 'AssetSearchPhrase.review_status == "accepted"' in image_repository
    assert "semantic_search_phrases" in image_semantic_profile
    assert 'if item.review_status == "rejected"' in image_semantic_profile
    assert "schema_version: Literal[3] = 3" in ai_schema
    assert "class ConfidenceTag" not in ai_schema
    assert "content_tags:" not in ai_schema
    assert "recommended_search_words:" not in ai_schema
    assert "schema_version: Literal[3] = 3" in image_schema
    assert "class ContentTagRead" not in image_schema
    assert "content_tags:" not in image_schema
    assert '"schema_version": 3' in ai_rules
    assert '"ocr_text"' not in ai_rules
    assert '"content_tags"' not in ai_rules
    assert '"contentTags"' not in search_index
    assert '"contentDimensions"' not in search_index
    assert '"contentTags"' not in meilisearch_client
    assert "self._sync_primary(group_id)" in asset_relation_service
    assert "def remove_phrase" in asset_relation_service
    assert "_reject_shadowed_ai_suggestions" in asset_relation_service
    assert "和学校课程一致" in master
    assert "外部服务只增强" in master
    assert "当前本地素材库已有 40 个素材组" in readme
    assert "API 中心是运行时唯一入口" in readme
    assert "使用统计" in layout
    assert "当前本地素材库为空" not in readme
    assert "当前正式素材库为空" not in _read("docs/SEARCH_MODES_AND_AI.md")
    assert "本地正式素材库当前为空" not in _read("docs/ARCHITECTURE.md")
    assert "<title>卖点智库</title>" in html
