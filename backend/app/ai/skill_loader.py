from functools import lru_cache

from app.core.config import PROJECT_DIR
from app.domain.taxonomy_catalog import render_catalog_for_prompt

MODEL_SKILLS = {
    "image_content_analysis": (
        "analyze-image-content",
        "classify-secondary-selling-points",
    ),
    "secondary_selling_point_classification": (
        "classify-secondary-selling-points",
    ),
    "search_intent_understanding": (
        "understand-image-search-intent",
    ),
    "copy_selling_point_matching": (
        "match-copy-selling-points",
    ),
}


@lru_cache
def load_skill_rules(skill_name: str) -> str:
    path = PROJECT_DIR / "skills" / skill_name / "RULES.md"
    if not path.is_file():
        raise FileNotFoundError(f"项目 Skill 不存在：{skill_name}")
    return path.read_text(encoding="utf-8")


def build_task_prompt(task: str) -> str:
    skill_names = MODEL_SKILLS.get(task, ())
    if not skill_names:
        raise ValueError(f"任务没有绑定项目 Skill：{task}")
    sections = [load_skill_rules(name) for name in skill_names]
    if task in {
        "image_content_analysis",
        "secondary_selling_point_classification",
        "search_intent_understanding",
    }:
        sections.append(render_catalog_for_prompt())
    elif task == "copy_selling_point_matching":
        sections.append(render_catalog_for_prompt(include_copy_points=True))
    return "\n\n---\n\n".join(sections)
