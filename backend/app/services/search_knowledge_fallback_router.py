from __future__ import annotations

from app.schemas.ai import SearchUnderstanding
from app.services.viking_knowledge_service_router import VikingKnowledgeServiceRouter
from app.services.vikingdb_knowledge_router import VikingDBKnowledgeRouter


class SearchKnowledgeFallbackRouter:
    """Try the published knowledge service first, then a strict vector fallback."""

    def __init__(
        self,
        *,
        primary: VikingKnowledgeServiceRouter,
        fallback: VikingDBKnowledgeRouter,
    ):
        self.primary = primary
        self.fallback = fallback

    @property
    def configured(self) -> bool:
        return self.primary.configured or self.fallback.configured

    def route(self, keyword: str) -> SearchUnderstanding | None:
        primary_error = ""
        try:
            primary_result = (
                self.primary.route(keyword) if self.primary.configured else None
            )
        except Exception as exc:
            primary_result = None
            primary_error = _safe_error(exc)
        if _is_terminal_result(primary_result):
            return primary_result
        fallback_result = (
            self.fallback.route(keyword) if self.fallback.configured else None
        )
        if fallback_result is None:
            return primary_result
        fallback_reason = (
            "知识库服务调用失败，改由 VikingDB 向量知识兜底取 top1："
            if primary_error
            else "知识库服务未产出可信卖点，改由 VikingDB 向量知识兜底取 top1："
        )
        fallback_result.search_strategy = (
            fallback_reason
            + (fallback_result.search_strategy or "按命中卖点返回本地图库")
        )
        return fallback_result


def _is_terminal_result(result: SearchUnderstanding | None) -> bool:
    if result is None:
        return False
    if result.query_type == "no_reliable_intent_search":
        return True
    return bool(result.matched_business_concepts)


def _safe_error(exc: Exception) -> str:
    message = str(exc).strip()
    return (message or exc.__class__.__name__)[:160]
