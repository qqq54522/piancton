from __future__ import annotations

from functools import lru_cache

from app.core.config import PROJECT_DIR
from app.domain.evidence_points import render_evidence_points_for_prompt
from app.domain.proof_points import render_proof_points_for_prompt
from app.domain.taxonomy_catalog import render_catalog_for_prompt

MODEL_SKILLS = {
    "image_content_analysis": ("analyze-image-asset",),
    "asset_search_phrase_generation": ("generate-asset-search-phrases",),
    "search_intent_understanding": ("understand-image-search-intent",),
    "search_proof_point_understanding": ("understand-image-search-intent",),
    "search_candidate_review": ("understand-image-search-intent",),
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
INTENT_PROMPT_VERSION = "2026-07-27.strict-three-layer-v1"


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


def _load_layer_rules(filename: str) -> str:
    path = PROJECT_DIR / "skills" / "understand-image-search-intent" / filename
    if not path.is_file():
        raise FileNotFoundError(f"分层意图规则不存在：{filename}")
    return path.read_text(encoding="utf-8")


def _runtime_intent_summary(filename: str) -> str:
    text = load_intent_reference_file(filename)
    start_marker = "<!-- runtime-intent:start -->"
    end_marker = "<!-- runtime-intent:end -->"
    start = text.find(start_marker)
    end = text.find(end_marker)
    if start < 0 or end < 0 or end <= start:
        raise ValueError(f"运行时意图摘要标记缺失：{filename}")
    return text[start + len(start_marker) : end].strip()


def build_selling_point_prompt(
    system_codes: tuple[str, ...],
    *,
    catalog_text: str,
) -> str:
    """Second layer: load only selling-point summaries inside routed systems."""
    invalid = [code for code in system_codes if code not in INTENT_REFERENCE_BY_SYSTEM]
    if invalid:
        raise ValueError(f"未知体系 code：{', '.join(invalid)}")
    if not system_codes:
        raise ValueError("第二层至少需要一个候选体系")
    sections = [_load_layer_rules("SELLING_POINT_ROUTER_RULES.md")]
    if len(system_codes) > 1:
        sections.append(_runtime_intent_summary("cross-system-calibration.md"))
    for code in system_codes:
        sections.append(_runtime_intent_summary(INTENT_REFERENCE_BY_SYSTEM[code]))
    sections.append(catalog_text)
    return "\n\n---\n\n".join(sections)


def build_proof_point_prompt(concept_codes: tuple[str, ...]) -> str:
    """Third layer: load proof candidates only for second-layer selling points."""
    if not concept_codes:
        raise ValueError("第三层至少需要一个已命中卖点")
    sections = [
        _load_layer_rules("PROOF_POINT_ROUTER_RULES.md"),
        render_proof_points_for_prompt(concept_codes),
        render_evidence_points_for_prompt(concept_codes=concept_codes),
    ]
    return "\n\n---\n\n".join(sections)


def build_candidate_review_prompt() -> str:
    return """
# 第四层：候选图片复核

用途：只复核已召回候选图片是否承接本次用户原话和前三层搜索理解。不得新增候选图片，不得重判体系、卖点或证明点。

判断顺序：

1. 先看候选图是否有人工 accepted 业务关系承接已确认卖点。
2. 再看素材独有搜索表达、标题、语义总结和画面事实是否承接用户原话。
3. 若候选图只是泛泛相关但不冲突，返回 `demote`，不要轻易 `exclude`。
4. 只有候选图的业务关系、标题或语义证据与已确认意图明显不一致，
   或只承接相邻卖点而非本次需求时，才返回 `exclude`。
5. 不得因为图片缺少某个字段就排除；缺字段只能降低置信度。

输出协议：

```json
{
  "decisions": [
    {
      "image_id": "候选图片 id，必须来自输入",
      "decision": "keep | demote | exclude",
      "confidence": 0.0,
      "reason": "只解释该图与本次查询是否匹配的证据"
    }
  ],
  "review_strategy": "本次复核采用的简短策略"
}
```

约束：

- 必须只返回输入候选图片中的 image_id。
- 不确定时返回 `keep` 或 `demote`，不要编造排除理由。
- 不得输出 Markdown、解释文本或代码块之外的内容。
""".strip()


def build_task_prompt(task: str, *, catalog_text: str | None = None) -> str:
    """Compose the task prompt; ``catalog_text`` carries the D027 database catalog."""
    if task == "search_intent_understanding":
        raise ValueError(
            "搜索意图必须先调用 build_system_routing_prompt，"
            "再按候选体系调用 build_selling_point_prompt，"
            "最后按已命中卖点调用 build_proof_point_prompt"
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
