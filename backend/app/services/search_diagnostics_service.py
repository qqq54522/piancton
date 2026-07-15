from __future__ import annotations

from app.schemas.image import SearchBranchStatusRead, SearchDiagnosticsRead
from app.services.search_models import SearchBranchDiagnostic


class SearchDiagnosticsService:
    def build(
        self,
        *,
        total_duration_ms: int,
        branches: list[SearchBranchDiagnostic],
        reranker_used: bool,
        total_timed_out: bool,
    ) -> SearchDiagnosticsRead:
        degraded_sources = [
            item.source
            for item in branches
            if item.status in {"failed", "timed_out"}
        ]
        return SearchDiagnosticsRead(
            total_duration_ms=total_duration_ms,
            timed_out=total_timed_out
            or any(item.status == "timed_out" for item in branches),
            reranker_used=reranker_used,
            cache_hit=any(item.cache_hit for item in branches),
            degraded_sources=list(dict.fromkeys(degraded_sources)),
            branches=[
                SearchBranchStatusRead(
                    source=item.source,
                    status=item.status,
                    duration_ms=item.duration_ms,
                    result_count=item.result_count,
                    cache_hit=item.cache_hit,
                    detail=item.detail,
                )
                for item in branches
            ],
        )

    def fallback_reason(self, branches: list[SearchBranchDiagnostic]) -> str | None:
        reasons = []
        for item in branches:
            if item.status not in {"failed", "timed_out"}:
                continue
            reason = f"{item.source}{'超时' if item.status == 'timed_out' else '不可用'}"
            if item.detail:
                reason += f"（{item.detail}）"
            reasons.append(reason)
        if not reasons:
            return None
        return "搜索已降级：" + "；".join(dict.fromkeys(reasons))
