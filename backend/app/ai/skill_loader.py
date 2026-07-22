from __future__ import annotations

from functools import lru_cache

from app.core.config import PROJECT_DIR
from app.domain.evidence_points import render_evidence_points_for_prompt
from app.domain.taxonomy_catalog import render_catalog_for_prompt

MODEL_SKILLS = {
    "image_content_analysis": ("analyze-image-asset",),
    "asset_search_phrase_generation": ("generate-asset-search-phrases",),
    "search_intent_understanding": ("understand-image-search-intent",),
    "copy_selling_point_matching": ("match-copy-selling-points",),
}

INTENT_REFERENCE_BY_SYSTEM = {
    "sync_school": "sync-school.md",
    "sync_exam": "sync-exam.md",
    "sync_cultivation": "sync-cultivation.md",
    "sync_planning": "sync-planning.md",
    "sync_self_study": "sync-self-study.md",
    "sync_companion": "sync-companion.md",
}
INTENT_PROMPT_VERSION = "2026-07-21.evidence-expression-v4"


@lru_cache
def load_skill_rules(skill_name: str) -> str:
    path = PROJECT_DIR / "skills" / skill_name / "RULES.md"
    if not path.is_file():
        raise FileNotFoundError(f"项目 Skill 不存在：{skill_name}")
    return path.read_text(encoding="utf-8")


@lru_cache
def load_intent_reference_file(filename: str) -> str:
    """Load one routed reference in full without reading unrelated systems."""
    reference_dir = PROJECT_DIR / "skills" / "understand-image-search-intent" / "references"
    path = reference_dir / filename
    if not path.is_file():
        raise FileNotFoundError(f"意图知识文件不存在：{filename}")
    return path.read_text(encoding="utf-8")


def build_system_routing_prompt() -> str:
    """First layer: six-system routing only; no selling-point catalog."""
    path = PROJECT_DIR / "skills" / "understand-image-search-intent" / "SYSTEM_ROUTER_RULES.md"
    if not path.is_file():
        raise FileNotFoundError("体系路由规则不存在")
    return path.read_text(encoding="utf-8")


def build_selling_point_prompt(
    system_codes: tuple[str, ...],
    *,
    catalog_text: str,
) -> str:
    """Second layer: fully load only routed systems and their active concepts."""
    invalid = [code for code in system_codes if code not in INTENT_REFERENCE_BY_SYSTEM]
    if invalid:
        raise ValueError(f"未知体系 code：{', '.join(invalid)}")
    if not system_codes:
        raise ValueError("第二层至少需要一个候选体系")
    sections = [load_skill_rules("understand-image-search-intent")]
    if len(system_codes) > 1:
        sections.append(load_intent_reference_file("cross-system-calibration.md"))
    for code in system_codes:
        sections.append(load_intent_reference_file(INTENT_REFERENCE_BY_SYSTEM[code]))
    sections.append(catalog_text)
    sections.append(render_evidence_points_for_prompt(system_codes))
    return "\n\n---\n\n".join(sections)


def build_task_prompt(task: str, *, catalog_text: str | None = None) -> str:
    """Compose the task prompt; ``catalog_text`` carries the D027 database catalog."""
    if task == "search_intent_understanding":
        raise ValueError(
            "搜索意图必须先调用 build_system_routing_prompt，"
            "再按候选体系调用 build_selling_point_prompt"
        )
    skill_names = MODEL_SKILLS.get(task, ())
    if not skill_names:
        raise ValueError(f"任务没有绑定项目 Skill：{task}")
    sections = [load_skill_rules(name) for name in skill_names]
    if task in {
        "image_content_analysis",
        "search_intent_understanding",
    }:
        sections.append(catalog_text or render_catalog_for_prompt())
    elif task == "copy_selling_point_matching":
        sections.append(render_catalog_for_prompt(include_copy_points=True))
    return "\n\n---\n\n".join(sections)
