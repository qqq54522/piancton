from __future__ import annotations

import json
from functools import lru_cache
from typing import Any

from app.core.config import PROJECT_DIR, get_settings
from app.domain.evidence_points import render_evidence_points_for_prompt
from app.domain.proof_points import render_proof_points_for_prompt
from app.domain.taxonomy_catalog import render_catalog_for_prompt

MODEL_SKILLS = {
    "search_intent_understanding": ("understand-image-search-intent",),
    "search_proof_point_understanding": ("understand-image-search-intent",),
    "search_candidate_review": ("understand-image-search-intent",),
    "search_result_recommendation_reason": ("understand-image-search-intent",),
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
DECISION_CARDS_REFERENCE = "selling-point-decision-cards.json"


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


@lru_cache
def load_selling_point_decision_cards() -> dict[str, Any]:
    text = load_intent_reference_file(DECISION_CARDS_REFERENCE)
    payload = json.loads(text)
    if not isinstance(payload, dict):
        raise ValueError("卖点判断卡片格式错误")
    return payload


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
    include_decision_cards: bool | None = None,
) -> str:
    """Second layer: load only selling-point summaries inside routed systems."""
    invalid = [code for code in system_codes if code not in INTENT_REFERENCE_BY_SYSTEM]
    if invalid:
        raise ValueError(f"未知体系 code：{', '.join(invalid)}")
    if not system_codes:
        raise ValueError("第二层至少需要一个候选体系")
    sections = [_load_layer_rules("SELLING_POINT_ROUTER_RULES.md")]
    if include_decision_cards is None:
        include_decision_cards = (
            get_settings().search_selling_point_decision_cards_enabled
        )
    if include_decision_cards:
        sections.append(render_selling_point_decision_cards(system_codes))
    if len(system_codes) > 1:
        sections.append(_runtime_intent_summary("cross-system-calibration.md"))
    for code in system_codes:
        sections.append(_runtime_intent_summary(INTENT_REFERENCE_BY_SYSTEM[code]))
    sections.append(catalog_text)
    return "\n\n---\n\n".join(sections)


def render_selling_point_decision_cards(system_codes: tuple[str, ...]) -> str:
    payload = load_selling_point_decision_cards()
    systems = payload.get("systems")
    if not isinstance(systems, list):
        raise ValueError("卖点判断卡片缺少 systems")
    selected = set(system_codes)
    lines = [
        "# 候选体系卖点判断卡片",
        "",
        (
            "用途：先判断卖点本体，再参考公共话术。卡片只服务第二层卖点识别，"
            "不替代数据库启用目录、人工素材关系或第三层证明点。"
        ),
        "",
        (
            "判断顺序：oneSentenceDecision → meaningBehind → boundaryLogic → "
            "definition → object → action → purpose → positiveSignals → "
            "boundaries → confusesWith。公共话术只能辅助解释，不能覆盖卡片边界。"
        ),
    ]
    for system in systems:
        if not isinstance(system, dict) or system.get("code") not in selected:
            continue
        lines.append(f"\n## {system['code']}")
        cards = system.get("cards")
        if not isinstance(cards, list):
            continue
        for card in cards:
            if not isinstance(card, dict):
                continue
            code = str(card.get("code", "")).strip()
            if not code:
                continue
            lines.extend(
                [
                    f"\n### `{code}` / {card.get('displayName', code)}",
                    f"- 一句话判定：{card.get('oneSentenceDecision', '')}",
                    f"- 背后意思：{card.get('meaningBehind', '')}",
                    f"- 边界逻辑：{card.get('boundaryLogic', '')}",
                    f"- 本体定义：{card.get('definition', '')}",
                    f"- 核心对象：{_join_card_items(card.get('object'))}",
                    f"- 主动作：{_join_card_items(card.get('action'))}",
                    f"- 用户目的：{_join_card_items(card.get('purpose'))}",
                    f"- 正向信号：{_join_card_items(card.get('positiveSignals'))}",
                    f"- 排除边界：{_join_card_items(card.get('boundaries'))}",
                    f"- 易混卖点：{_join_card_items(card.get('confusesWith'))}",
                    f"- 判定规则：{card.get('decisionRule', '')}",
                ]
            )
    lines.append("\n只能返回本卡片与当前启用目录共同存在的稳定 code。")
    return "\n".join(lines)


def _join_card_items(value: object) -> str:
    if not isinstance(value, list):
        return ""
    return "；".join(str(item).strip() for item in value if str(item).strip())


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


def build_result_recommendation_reason_prompt() -> str:
    return """
# 第五层：动态结果推荐理由

用途：为已经完成召回、排序和候选复核的最终图片结果生成“为什么这张图适合本次搜索”的业务说明。

严格边界：

1. 只能解释输入中已有的图片，必须原样使用输入里的 `image_id`，不得新增候选。
2. 只能基于用户原始搜索、已确认搜索理解、人工 accepted 卖点关系、
   证明点/证据点、素材独有话术、图片语义事实和召回理由作答。
3. 不得重新判断体系、卖点或证明点，不得改变排序，不得把模型推断写回素材事实。
4. 不得编造图片中没有出现的对象、数据、功能、渠道、效果或品牌信息。
5. 每张图片返回一条完整、自然、面向业务选图人员的中文理由，
   回答“为什么适合当前搜索句”，不要只复述标题。
6. 如果证据不足，只引用输入已有依据，不能为了让文案更完整而补造事实。

输出协议：

```json
{
  "reasons": [
    {
      "image_id": "必须来自输入候选",
      "reason": "完整的中文推荐理由，建议 1～2 句"
    }
  ],
  "generation_strategy": "本次使用的证据范围"
}
```

必须为输入中的每张候选图片返回一条理由；不得返回 Markdown、代码块或协议之外的字段。
""".strip()


def build_search_route_explanation_prompt() -> str:
    return """
# 搜索结果：命中卖点解释

用途：生成搜索结果顶部的一段专业命中分析，让运营/市场选图人员一眼理解“为什么这句话应该看这些卖点素材”。

严格边界：

1. 只解释 `query` 与 `matched_selling_points` 之间的关系。
2. 不评价每张图片，不为单图生成推荐理由，不改变召回、排序或候选准入。
3. 不重新发明卖点；只能使用输入里已经确认的卖点名称。
4. 不输出内部实现、模型分数、VikingDB、索引、算法、Provider、返回数量、渠道默认规则或卡片展示规则。
5. 不写“未指定渠道”“当前返回 X 组”“保留手机端大图/小图”“卡片下方只保留卖点”等流程说明。
6. 语言面向运营/市场选图人员，要像专业业务判断：拆出用户原话里的对象、
   动作、目的和隐含需求，再说明它们如何对应命中卖点。
7. 证据不足时要保守，不夸大、不编造产品能力；最多用 2～3 句中文自然段。

输出协议：

```json
{
  "explanation": "一段中文专业命中分析，解释为什么这句话命中这些卖点",
  "generation_strategy": "本次解释使用的证据范围"
}
```

不得返回 Markdown、代码块或协议之外的字段。
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
