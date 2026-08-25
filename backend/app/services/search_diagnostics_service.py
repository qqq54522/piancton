from __future__ import annotations

from app.schemas.image import ModelAttemptRead, SearchBranchStatusRead, SearchDiagnosticsRead
from app.services.search_models import SearchBranchDiagnostic

NON_DEGRADING_BRANCHES = frozenset({"result_recommendation_reason"})


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
            if (
                item.status in {"failed", "timed_out"}
                and item.source not in NON_DEGRADING_BRANCHES
            )
        ]
        return SearchDiagnosticsRead(
            total_duration_ms=total_duration_ms,
            timed_out=total_timed_out
            or any(
                item.status == "timed_out"
                and item.source not in NON_DEGRADING_BRANCHES
                for item in branches
            ),
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
                    attempts=[
                        ModelAttemptRead(
                            task=attempt.task,
                            layer=attempt.layer,
                            provider=attempt.provider,
                            model=attempt.model,
                            status=attempt.status,
                            duration_ms=attempt.duration_ms,
                            fallback_index=attempt.fallback_index,
                            error=attempt.error,
                        )
                        for attempt in item.attempts
                    ],
                )
                for item in branches
            ],
        )

    def fallback_reason(self, branches: list[SearchBranchDiagnostic]) -> str | None:
        reasons = []
        for item in branches:
            if (
                item.status not in {"failed", "timed_out"}
                or item.source in NON_DEGRADING_BRANCHES
            ):
                continue
            reason = f"{item.source}{'超时' if item.status == 'timed_out' else '不可用'}"
            if item.detail:
                reason += f"（{item.detail}）"
            reasons.append(reason)
        if not reasons:
            return None
        return "搜索已降级：" + "；".join(dict.fromkeys(reasons))

    def user_fallback_reason(
        self,
        branches: list[SearchBranchDiagnostic],
        *,
        trusted_business_route: bool,
    ) -> str | None:
        """Only expose degradation when it can materially change user results."""
        if trusted_business_route:
            return None
        return self.fallback_reason(branches)
