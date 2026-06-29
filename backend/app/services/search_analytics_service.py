from __future__ import annotations

import json
import logging
from collections import Counter
from datetime import datetime, timedelta, timezone

from sqlalchemy import func, select
from sqlalchemy.orm import selectinload

from app.models.image import Image, ImageBusinessLabel, ImageTag
from app.models.search_feedback import SearchFeedbackEvent
from app.models.search_log import SearchLog
from app.models.tag import Tag
from app.repositories.search_feedback_repository import SearchFeedbackRepository
from app.repositories.search_log_repository import SearchLogRepository
from app.schemas.image import SearchResponse
from app.schemas.search_ops import (
    AiReviewQueueItem,
    AssetGapItem,
    LabelHealthItem,
    SearchFeedbackCreate,
    SearchFeedbackRead,
    SearchLogRead,
    SearchMetricItem,
    SearchOpsSummary,
    SearchOpsIssueRead,
)
from app.services.unit_of_work import UnitOfWork

logger = logging.getLogger(__name__)


class SearchAnalyticsService:
    def __init__(self, db):
        self.db = db
        self.logs = SearchLogRepository(db)
        self.feedback = SearchFeedbackRepository(db)
        self.uow = UnitOfWork(db)

    def record_search(
        self,
        *,
        actor_user_id: str | None,
        keyword: str,
        requested_mode: str,
        response: SearchResponse,
        request_id: str | None = None,
    ) -> str | None:
        understanding = response.search_understanding
        top_result_ids = [item.image.id for item in response.results[:8]]
        match_reasons = sorted(
            {
                reason
                for result in response.results[:5]
                for reason in result.match_reasons
            }
        )
        matched_category = None
        if understanding and understanding.matched_level2_categories:
            matched_category = understanding.matched_level2_categories[0].category

        try:
            log = self.logs.add(
                SearchLog(
                    actor_user_id=actor_user_id,
                    keyword=keyword.strip()[:200],
                    requested_mode=requested_mode,
                    served_mode=response.search_mode,
                    fallback=response.fallback,
                    fallback_reason=response.fallback_reason,
                    result_count=len(response.results),
                    normalized_query=(
                        understanding.normalized_query[:200]
                        if understanding and understanding.normalized_query
                        else None
                    ),
                    query_type=understanding.query_type if understanding else None,
                    matched_category=matched_category[:200] if matched_category else None,
                    top_image_ids_json=json.dumps(top_result_ids, ensure_ascii=False),
                    match_reasons_json=json.dumps(match_reasons, ensure_ascii=False),
                    request_id=request_id,
                )
            )
            self.uow.commit()
            return log.id
        except Exception:
            self.uow.rollback()
            logger.warning("failed to record search analytics", exc_info=True)
            return None

    def record_feedback(
        self,
        *,
        actor_user_id: str | None,
        payload: SearchFeedbackCreate,
        request_id: str | None = None,
    ) -> SearchFeedbackRead | None:
        try:
            event = self.feedback.add(
                SearchFeedbackEvent(
                    search_log_id=payload.search_log_id,
                    actor_user_id=actor_user_id,
                    keyword=payload.keyword.strip()[:200],
                    feedback_type=payload.feedback_type,
                    note=(payload.note or "").strip()[:1000] or None,
                    request_id=request_id,
                )
            )
            self.uow.commit()
            return self._feedback_read(event)
        except Exception:
            self.uow.rollback()
            logger.warning("failed to record search feedback", exc_info=True)
            return None

    def summary(self, *, days: int = 7, limit: int = 2000) -> SearchOpsSummary:
        bounded_days = max(1, min(days, 90))
        since = datetime.now(timezone.utc) - timedelta(days=bounded_days)
        logs = self.logs.list_since(since, limit=limit)
        feedback_events = self.feedback.list_since(since, limit=limit)
        total = len(logs)
        return SearchOpsSummary(
            total_searches=total,
            zero_result_count=sum(1 for item in logs if item.result_count == 0),
            fallback_count=sum(1 for item in logs if item.fallback),
            ai_understood_count=sum(1 for item in logs if item.normalized_query),
            smart_search_count=sum(1 for item in logs if item.requested_mode == "smart"),
            precise_search_count=sum(1 for item in logs if item.requested_mode == "precise"),
            top_queries=self._top_items(item.keyword for item in logs if item.keyword),
            zero_result_queries=self._top_items(
                item.keyword for item in logs if item.keyword and item.result_count == 0
            ),
            top_normalized_queries=self._top_items(
                item.normalized_query for item in logs if item.normalized_query
            ),
            top_matched_categories=self._top_items(
                item.matched_category for item in logs if item.matched_category
            ),
            feedback_count=len(feedback_events),
            feedback_by_type=self._top_items(
                item.feedback_type for item in feedback_events if item.feedback_type
            ),
            feedback_queries=self._top_items(
                item.keyword for item in feedback_events if item.keyword
            ),
            recent_feedback=[
                self._feedback_read(item) for item in feedback_events[:50]
            ],
            recent_logs=[self._log_read(item) for item in logs[:50]],
            search_issues=self._search_issues(logs, feedback_events),
            ai_review_queue=self._ai_review_queue(),
            label_health=self._label_health(logs),
            asset_gaps=self._asset_gaps(logs, feedback_events),
        )

    def _search_issues(
        self,
        logs: list[SearchLog],
        feedback_events: list[SearchFeedbackEvent],
    ) -> list[SearchOpsIssueRead]:
        grouped: dict[tuple[str, str], dict] = {}

        def add(
            *,
            keyword: str,
            issue_type: str,
            source: str,
            reason: str,
            suggested_action: str,
            created_at: datetime,
            severity: str,
        ) -> None:
            key = (keyword.strip(), issue_type)
            if not key[0]:
                return
            row = grouped.setdefault(
                key,
                {
                    "count": 0,
                    "source": source,
                    "reason": reason,
                    "suggested_action": suggested_action,
                    "latest_at": created_at,
                    "severity": severity,
                },
            )
            row["count"] += 1
            if created_at > row["latest_at"]:
                row["latest_at"] = created_at
            if severity == "high" or (severity == "medium" and row["severity"] == "low"):
                row["severity"] = severity

        for log in logs:
            if log.result_count == 0:
                add(
                    keyword=log.keyword,
                    issue_type="zero_result",
                    source="search_log",
                    reason="用户搜索没有返回素材",
                    suggested_action="先判断是素材缺口、标签缺失，还是业务话术没有进入意图词库",
                    created_at=log.created_at,
                    severity="high",
                )
            if log.fallback:
                add(
                    keyword=log.keyword,
                    issue_type="search_fallback",
                    source="search_log",
                    reason=log.fallback_reason or "智能搜索发生降级",
                    suggested_action="检查 Meilisearch、Embedding/Reranker 或模型理解链路是否可用",
                    created_at=log.created_at,
                    severity="medium",
                )

        feedback_map = {
            "not_relevant": (
                "irrelevant_results",
                "业务方反馈结果不相关",
                "查看 Top 图片和命中原因，判断是否误标、summary 偏泛或强意图过滤不够收紧",
                "high",
            ),
            "too_few_results": (
                "too_few_results",
                "业务方反馈结果太少",
                "判断是否需要补素材，或把同义表达补进业务意图词库",
                "medium",
            ),
            "need_different_style": (
                "style_gap",
                "业务方想要不同风格",
                "记录为素材风格需求，后续补充设计生产 brief",
                "low",
            ),
            "asset_request": (
                "asset_request",
                "业务方提交素材需求",
                "沉淀为素材需求，优先补齐高频业务话术对应图片",
                "high",
            ),
        }
        for event in feedback_events:
            issue_type, reason, action, severity = feedback_map.get(
                event.feedback_type,
                ("feedback", "业务方提交了搜索反馈", "查看反馈备注并归因", "medium"),
            )
            add(
                keyword=event.keyword,
                issue_type=issue_type,
                source="search_feedback",
                reason=reason,
                suggested_action=action,
                created_at=event.created_at,
                severity=severity,
            )

        severity_rank = {"high": 0, "medium": 1, "low": 2}
        rows = [
            SearchOpsIssueRead(
                id=f"{issue_type}:{keyword}",
                keyword=keyword,
                issue_type=issue_type,
                severity=data["severity"],
                source=data["source"],
                count=data["count"],
                reason=data["reason"],
                suggested_action=data["suggested_action"],
                latest_at=data["latest_at"],
            )
            for (keyword, issue_type), data in grouped.items()
        ]
        return sorted(
            rows,
            key=lambda item: (
                severity_rank.get(item.severity, 3),
                -item.count,
                item.latest_at,
            ),
            reverse=False,
        )[:50]

    def _ai_review_queue(self, limit: int = 50) -> list[AiReviewQueueItem]:
        stmt = (
            select(ImageBusinessLabel)
            .join(Image, Image.id == ImageBusinessLabel.image_id)
            .where(
                Image.deleted_at.is_(None),
                ImageBusinessLabel.origin == "ai",
                ImageBusinessLabel.review_status == "pending",
            )
            .options(
                selectinload(ImageBusinessLabel.image),
                selectinload(ImageBusinessLabel.tag).selectinload(Tag.parent),
            )
            .order_by(
                ImageBusinessLabel.confidence.desc().nullslast(),
                ImageBusinessLabel.created_at.desc(),
            )
            .limit(limit)
        )
        return [
            AiReviewQueueItem(
                id=label.id,
                image_id=label.image_id,
                image_title=label.image.title,
                thumbnail_url=f"/api/images/{label.image_id}/thumbnail",
                label_code=label.label_code,
                label_name=label.tag.name,
                system_name=label.tag.parent.name if label.tag.parent else None,
                role=label.role,
                confidence=label.confidence,
                evidence_level=label.evidence_level,
                reason=label.reason,
                created_at=label.created_at,
            )
            for label in self.db.scalars(stmt).all()
        ]

    def _label_health(self, logs: list[SearchLog]) -> list[LabelHealthItem]:
        tags = list(
            self.db.scalars(
                select(Tag)
                .where(Tag.assignable.is_(True), Tag.status == "active")
                .options(selectinload(Tag.parent))
                .order_by(Tag.sort_order.asc(), Tag.name.asc())
            ).all()
        )
        image_counts = Counter(
            {
                tag_id: count
                for tag_id, count in self.db.execute(
                    select(ImageTag.tag_id, func.count(func.distinct(ImageTag.image_id)))
                    .join(Image, Image.id == ImageTag.image_id)
                    .where(Image.deleted_at.is_(None))
                    .group_by(ImageTag.tag_id)
                ).all()
            }
        )
        label_rows = list(
            self.db.scalars(
                select(ImageBusinessLabel)
                .join(Image, Image.id == ImageBusinessLabel.image_id)
                .where(Image.deleted_at.is_(None))
                .options(selectinload(ImageBusinessLabel.tag).selectinload(Tag.parent))
            ).all()
        )
        manual_counts: Counter[str] = Counter()
        ai_pending_counts: Counter[str] = Counter()
        ai_accepted_counts: Counter[str] = Counter()
        ai_rejected_counts: Counter[str] = Counter()
        for label in label_rows:
            if label.origin == "manual":
                manual_counts[label.tag_id] += 1
            elif label.review_status == "pending":
                ai_pending_counts[label.tag_id] += 1
            elif label.review_status == "accepted":
                ai_accepted_counts[label.tag_id] += 1
            elif label.review_status == "rejected":
                ai_rejected_counts[label.tag_id] += 1

        search_counts = Counter()
        for log in logs:
            for tag in tags:
                display = self._tag_display_name(tag)
                if log.matched_category == display or log.normalized_query == tag.name:
                    search_counts[tag.id] += 1

        rows: list[LabelHealthItem] = []
        for tag in tags:
            image_count = int(image_counts[tag.id])
            pending = ai_pending_counts[tag.id]
            manual = manual_counts[tag.id]
            accepted = ai_accepted_counts[tag.id]
            search_count = search_counts[tag.id]
            if image_count == 0 and search_count > 0:
                level = "needs_assets"
                recommendation = "有搜索需求但没有可用素材，优先补图或检查标签归档"
            elif pending >= max(2, manual + accepted):
                level = "needs_review"
                recommendation = "AI 待审核量偏高，优先批量确认或拒绝"
            elif search_count > 0 and image_count < 3:
                level = "watch"
                recommendation = "有搜索需求但素材覆盖偏少，建议继续观察并补充"
            else:
                level = "healthy"
                recommendation = "当前标签供给和审核状态基本正常"
            rows.append(
                LabelHealthItem(
                    tag_id=tag.id,
                    label_code=tag.code,
                    label_name=tag.name,
                    system_name=tag.parent.name if tag.parent else None,
                    image_count=image_count,
                    manual_count=manual,
                    ai_pending_count=pending,
                    ai_accepted_count=accepted,
                    ai_rejected_count=ai_rejected_counts[tag.id],
                    search_count=search_count,
                    health_level=level,
                    recommendation=recommendation,
                )
            )
        rank = {"needs_assets": 0, "needs_review": 1, "watch": 2, "healthy": 3}
        return sorted(
            rows,
            key=lambda item: (
                rank[item.health_level],
                -item.search_count,
                item.image_count,
                item.label_name,
            ),
        )[:80]

    def _asset_gaps(
        self,
        logs: list[SearchLog],
        feedback_events: list[SearchFeedbackEvent],
    ) -> list[AssetGapItem]:
        demand: Counter[str] = Counter()
        source: dict[str, set[str]] = {}
        suggested_label: dict[str, str] = {}
        for log in logs:
            if log.result_count == 0:
                demand[log.keyword] += 2
                source.setdefault(log.keyword, set()).add("空结果")
            elif log.result_count < 3:
                demand[log.keyword] += 1
                source.setdefault(log.keyword, set()).add("结果少")
            if log.matched_category or log.normalized_query:
                suggested_label[log.keyword] = log.matched_category or log.normalized_query or ""
        for event in feedback_events:
            if event.feedback_type in {"asset_request", "too_few_results", "need_different_style"}:
                demand[event.keyword] += 2 if event.feedback_type == "asset_request" else 1
                source.setdefault(event.keyword, set()).add("用户反馈")
        rows = [
            AssetGapItem(
                keyword=keyword,
                demand_count=count,
                suggested_label=suggested_label.get(keyword) or None,
                reason="高频需求未被现有素材充分满足",
                source="、".join(sorted(source.get(keyword, {"搜索"}))),
            )
            for keyword, count in demand.most_common(30)
            if keyword.strip()
        ]
        return rows

    def _top_items(self, values) -> list[SearchMetricItem]:
        return [
            SearchMetricItem(label=label, count=count)
            for label, count in Counter(values).most_common(10)
        ]

    def _tag_display_name(self, tag: Tag) -> str:
        if tag.parent:
            return f"{tag.parent.name} > {tag.name}"
        return tag.name

    def _log_read(self, log: SearchLog) -> SearchLogRead:
        return SearchLogRead(
            id=log.id,
            keyword=log.keyword,
            requested_mode=log.requested_mode,
            served_mode=log.served_mode,
            fallback=log.fallback,
            fallback_reason=log.fallback_reason,
            result_count=log.result_count,
            normalized_query=log.normalized_query,
            query_type=log.query_type,
            matched_category=log.matched_category,
            top_image_ids=self._json_list(log.top_image_ids_json),
            match_reasons=self._json_list(log.match_reasons_json),
            created_at=log.created_at,
        )

    def _feedback_read(self, event: SearchFeedbackEvent) -> SearchFeedbackRead:
        return SearchFeedbackRead(
            id=event.id,
            search_log_id=event.search_log_id,
            keyword=event.keyword,
            feedback_type=event.feedback_type,
            note=event.note,
            created_at=event.created_at,
        )

    def _json_list(self, payload: str) -> list[str]:
        try:
            value = json.loads(payload)
        except json.JSONDecodeError:
            return []
        if not isinstance(value, list):
            return []
        return [str(item) for item in value]
