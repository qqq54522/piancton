from __future__ import annotations

import asyncio
import time

from app.services.search_models import SearchBranchDiagnostic, SearchHit
from app.services.search_ranking_service import SearchRankingService


class SearchRerankCoordinator:
    """Runs the single optional Reranker call inside the remaining deadline."""

    def __init__(
        self,
        ranking: SearchRankingService,
        *,
        total_timeout_seconds: float,
        reranker_timeout_seconds: float,
    ):
        self.ranking = ranking
        self.total_timeout_seconds = max(0.1, total_timeout_seconds)
        self.reranker_timeout_seconds = max(0.01, reranker_timeout_seconds)

    async def rerank(
        self,
        keyword: str,
        hits: list[SearchHit],
        *,
        search_started: float,
    ) -> tuple[list[SearchHit], SearchBranchDiagnostic, bool, bool]:
        remaining = self.total_timeout_seconds - (time.monotonic() - search_started)
        if remaining <= 0:
            return hits, self._timed_out(hits, "总截止时间已到，跳过重排"), False, True
        if not self.ranking.reranker.configured or len(hits) <= 1:
            return (
                hits,
                SearchBranchDiagnostic(
                    source="reranker",
                    status="skipped",
                    duration_ms=0,
                    result_count=len(hits),
                    detail="服务未配置或候选不足",
                ),
                False,
                False,
            )

        started = time.monotonic()
        try:
            outcome = await asyncio.wait_for(
                self.ranking.rerank_hits_async(keyword, hits),
                timeout=min(self.reranker_timeout_seconds, remaining),
            )
        except asyncio.TimeoutError:
            return hits, self._timed_out(hits, "超过重排时间预算", started), False, False

        status = "failed" if outcome.error else "ok"
        return (
            outcome.hits,
            SearchBranchDiagnostic(
                source="reranker",
                status=status,
                duration_ms=_elapsed_ms(started),
                result_count=len(outcome.hits),
                detail=outcome.error,
            ),
            outcome.used,
            False,
        )

    def _timed_out(
        self,
        hits: list[SearchHit],
        detail: str,
        started: float | None = None,
    ) -> SearchBranchDiagnostic:
        return SearchBranchDiagnostic(
            source="reranker",
            status="timed_out",
            duration_ms=_elapsed_ms(started) if started is not None else 0,
            result_count=len(hits),
            detail=detail,
        )


def _elapsed_ms(started: float) -> int:
    return max(0, round((time.monotonic() - started) * 1000))
