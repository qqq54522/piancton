from pathlib import Path

from app.ai.skill_loader import MODEL_SKILLS

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SKILLS_ROOT = PROJECT_ROOT / "skills"

FORMAL_SKILLS = {
    "analyze-image-asset",
    "evaluate-image-search-quality",
    "generate-asset-search-phrases",
    "govern-selling-point-knowledge",
    "maintain-piancton-architecture",
    "manage-image-library",
    "match-copy-selling-points",
    "operate-model-providers",
    "understand-image-channel-intent",
    "understand-image-search-intent",
}

RETIRED_SKILLS = {
    "analyze-image-content",
    "classify-secondary-selling-points",
    "integrate-model-provider",
    "manage-local-image-storage",
    "manage-tag-taxonomy",
    "orchestrate-ai-tagging",
    "recall-selling-point-images",
    "score-image-search-results",
}


def test_project_exposes_only_complete_formal_skills():
    discovered = {
        path.parent.name for path in SKILLS_ROOT.glob("*/SKILL.md")
    }

    assert discovered == FORMAL_SKILLS
    for name in FORMAL_SKILLS:
        skill_dir = SKILLS_ROOT / name
        metadata = (skill_dir / "agents" / "openai.yaml").read_text(
            encoding="utf-8"
        )
        assert f"${name}" in metadata
        assert "allow_implicit_invocation: true" in metadata


def test_retired_skill_directories_are_removed():
    assert [name for name in RETIRED_SKILLS if (SKILLS_ROOT / name).exists()] == []


def test_runtime_model_tasks_load_the_current_skill_rules():
    assert MODEL_SKILLS == {
        "image_content_analysis": ("analyze-image-asset",),
        "asset_search_phrase_generation": ("generate-asset-search-phrases",),
        "search_intent_understanding": ("understand-image-search-intent",),
        "search_proof_point_understanding": ("understand-image-search-intent",),
        "search_candidate_review": ("understand-image-search-intent",),
        "copy_selling_point_matching": ("match-copy-selling-points",),
    }
    for skill_names in MODEL_SKILLS.values():
        for name in skill_names:
            assert (SKILLS_ROOT / name / "RULES.md").is_file()


def test_all_system_references_keep_proof_points_structured():
    references = SKILLS_ROOT / "understand-image-search-intent" / "references"
    for path in sorted(references.glob("sync-*.md")):
        content = path.read_text(encoding="utf-8")
        assert "状态：证明点已按统一口径结构化" in content
        assert "#### `pp_" in content
        assert "- 论断：" in content
        assert "- 搜索语言：" in content
        assert "- 证据样例（可增删）" in content
        assert "- 边界：" in content
