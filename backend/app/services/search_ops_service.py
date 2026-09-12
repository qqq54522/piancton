from __future__ import annotations

from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone
from math import ceil
from pathlib import Path

from PIL import Image as PILImage
from PIL import UnidentifiedImageError

from app.core.config import get_settings
from app.models.search_feedback import SearchFeedbackEvent
from app.models.search_log import SearchLog
from app.repositories.search_feedback_repository import SearchFeedbackRepository
from app.repositories.search_log_repository import SearchLogRepository
from app.repositories.search_ops_repository import SearchOpsRepository
from app.repositories.usage_repository import UsageEventRepository, UsageUserRepository
from app.schemas.search_ops import (
    AiConceptReviewQueueItem,
    AssetGapItem,
    AssetOperationsOverview,
    AssetOpsIssueRead,
    ConceptHealthItem,
    SearchActivitySummary,
    SearchMetricItem,
    SearchOpsIssueRead,
    SearchOpsSummary,
    SearchPerformanceSummary,
    SourceLinkHealth,
    SourceLinkRecentItem,
)
from app.services.recommendation_strategy_service import RecommendationStrategyService
from app.services.search_ops_serializers import feedback_read, interaction_read, log_read

SOURCE_LINK_REVIEW_DAYS = 90
STALE_UNUSED_ASSET_DAYS = 45


class SearchOpsService:
    """Read path for the admin search operations dashboard.

    Pulls raw rows through repositories and only performs in-memory
    aggregation, ranking and formatting here.
    """

    def __init__(self, db):
        self.logs = SearchLogRepository(db)
        self.feedback = SearchFeedbackRepository(db)
        self.ops = SearchOpsRepository(db)
        self.usage_events = UsageEventRepository(db)
        self.users = UsageUserRepository(db)
        self.recommendation_strategy = RecommendationStrategyService(db)

    def activity_summary(
        self,
        *,
        days: int = 7,
        limit: int = 2000,
    ) -> SearchActivitySummary:
        """Return only the user-search data needed by the daily operations page."""
        bounded_days = max(1, min(days, 90))
        now = datetime.now(timezone.utc)
        since = now - timedelta(days=bounded_days)
        logs = self.logs.list_since(since, limit=limit)
        feedback_events = self.feedback.list_since(since, limit=limit)
        interaction_events = [
            event
            for event in self.usage_events.list_between(
                start_at=since,
                end_at=now + timedelta(seconds=1),
                limit=limit,
            )
            if event.event_type == "search_interaction"
        ]
        users_by_id = {user.id: user for user in self.users.list()}
        total = len(logs)
        return SearchActivitySummary(
            total_searches=total,
            search_user_count=len({item.actor_user_id for item in logs if item.actor_user_id}),
            positive_feedback_count=sum(
                1 for item in feedback_events if item.feedback_type == "relevant"
            ),
            negative_feedback_count=sum(
                1 for item in feedback_events if item.feedback_type != "relevant"
            ),
            feedback_response_rate=(
                round(
                    len({item.search_log_id for item in feedback_events if item.search_log_id})
                    / total
                    * 100,
                    1,
                )
                if total
                else 0.0
            ),
            interaction_count=len(interaction_events),
            top_queries=self._top_items(item.keyword for item in logs if item.keyword),
            recent_feedback=[
                feedback_read(item, users_by_id.get(item.actor_user_id or ""))
                for item in feedback_events[:100]
            ],
            recent_logs=[
                log_read(item, users_by_id.get(item.actor_user_id or "")) for item in logs[:100]
            ],
            recent_interactions=[
                interaction_read(item, users_by_id.get(item.user_id or ""))
                for item in interaction_events[:100]
            ],
            recommendation_evaluation=self.recommendation_strategy.evaluate(
                window_days=30,
            ).to_read(),
        )

    def summary(self, *, days: int = 7, limit: int = 2000) -> SearchOpsSummary:
        bounded_days = max(1, min(days, 90))
        now = datetime.now(timezone.utc)
        since = now - timedelta(days=bounded_days)
        logs = self.logs.list_since(since, limit=limit)
        feedback_events = self.feedback.list_since(since, limit=limit)
        interaction_events = [
            event
            for event in self.usage_events.list_between(
                start_at=since,
                end_at=now + timedelta(seconds=1),
                limit=limit,
            )
            if event.event_type == "search_interaction"
        ]
        users_by_id = {user.id: user for user in self.users.list()}
        total = len(logs)
        durations = sorted(item.duration_ms for item in logs if item.duration_ms is not None)
        return SearchOpsSummary(
            total_searches=total,
            search_user_count=len({item.actor_user_id for item in logs if item.actor_user_id}),
            zero_result_count=sum(1 for item in logs if item.result_count == 0),
            fallback_count=sum(1 for item in logs if item.fallback),
            timed_out_count=sum(1 for item in logs if item.timed_out),
            cache_hit_count=sum(1 for item in logs if item.cache_hit),
            reranker_used_count=sum(1 for item in logs if item.reranker_used),
            average_duration_ms=(round(sum(durations) / len(durations), 2) if durations else 0.0),
            p95_duration_ms=_percentile_95(durations),
            ai_understood_count=sum(1 for item in logs if item.normalized_query),
            top_queries=self._top_items(item.keyword for item in logs if item.keyword),
            zero_result_queries=self._top_items(
                item.keyword for item in logs if item.keyword and item.result_count == 0
            ),
            top_normalized_queries=self._top_items(
                item.normalized_query for item in logs if item.normalized_query
            ),
            top_matched_concepts=self._top_items(
                item.matched_concept for item in logs if item.matched_concept
            ),
            feedback_count=len(feedback_events),
            positive_feedback_count=sum(
                1 for item in feedback_events if item.feedback_type == "relevant"
            ),
            negative_feedback_count=sum(
                1 for item in feedback_events if item.feedback_type != "relevant"
            ),
            feedback_response_rate=(
                round(
                    len({item.search_log_id for item in feedback_events if item.search_log_id})
                    / total
                    * 100,
                    1,
                )
                if total
                else 0.0
            ),
            interaction_count=len(interaction_events),
            feedback_by_type=self._top_items(
                item.feedback_type for item in feedback_events if item.feedback_type
            ),
            feedback_queries=self._top_items(
                item.keyword for item in feedback_events if item.keyword
            ),
            recent_feedback=[
                feedback_read(item, users_by_id.get(item.actor_user_id or ""))
                for item in feedback_events[:100]
            ],
            recent_logs=[
                log_read(item, users_by_id.get(item.actor_user_id or "")) for item in logs[:100]
            ],
            recent_interactions=[
                interaction_read(item, users_by_id.get(item.user_id or ""))
                for item in interaction_events[:100]
            ],
            search_issues=self._search_issues(logs, feedback_events),
            ai_review_queue=self._ai_review_queue(),
            concept_health=self._concept_health(logs),
            asset_gaps=self._asset_gaps(logs, feedback_events),
            asset_operations=self._asset_operations_overview(),
            asset_ops_issues=self._asset_ops_issues(),
            source_link_health=self._source_link_health(),
            search_performance=self._search_performance(logs),
        )

    def _asset_operations_overview(self) -> AssetOperationsOverview:
        groups = self.ops.published_asset_groups()
        total_groups = len(groups)
        current_images = [
            image
            for group in groups
            for image in group.images
            if image.deleted_at is None and image.is_current
        ]
        all_images = [
            image for group in groups for image in group.images if image.deleted_at is None
        ]

        def has_business_relation(group) -> bool:
            return any(
                link.review_status != "rejected" and link.relation_role != "excludes"
                for link in group.concept_links
            )

        def has_search_phrase(group) -> bool:
            return any(phrase.review_status != "rejected" for phrase in group.search_phrases)

        no_download_groups = 0
        for group in groups:
            downloads = sum(
                image.download_count for image in group.images if image.deleted_at is None
            )
            if downloads == 0:
                no_download_groups += 1

        missing_source = sum(1 for group in groups if not group.source_links)
        return AssetOperationsOverview(
            asset_group_count=total_groups,
            image_count=len(all_images),
            current_image_count=len(current_images),
            missing_source_link_count=missing_source,
            missing_source_link_rate=_ratio(missing_source, total_groups),
            single_version_group_count=sum(
                1
                for group in groups
                if sum(1 for image in group.images if image.deleted_at is None) <= 1
            ),
            missing_business_relation_count=sum(
                1 for group in groups if not has_business_relation(group)
            ),
            missing_search_phrase_count=sum(1 for group in groups if not has_search_phrase(group)),
            missing_style_count=sum(1 for group in groups if not group.style_label),
            unset_scene_count=sum(1 for group in groups if group.is_scene_image is None),
            missing_channel_count=sum(1 for image in current_images if not image.channel),
            total_download_count=self.ops.total_download_count(),
            unused_asset_group_count=no_download_groups,
        )

    def _asset_ops_issues(self, limit: int = 80) -> list[AssetOpsIssueRead]:
        groups = self.ops.published_asset_groups()
        issues: list[AssetOpsIssueRead] = []

        def add(group, issue_type, severity, message, action) -> None:
            issues.append(
                AssetOpsIssueRead(
                    id=f"{issue_type}:{group.id}",
                    asset_group_id=group.id,
                    title=group.title,
                    primary_image_id=group.primary_image_id,
                    issue_type=issue_type,
                    severity=severity,
                    message=message,
                    suggested_action=action,
                    updated_at=group.updated_at,
                )
            )

        active_images_by_fingerprint: dict[
            tuple[str, int, int | None, int | None],
            list,
        ] = defaultdict(list)
        active_images_by_visual_hash: dict[
            tuple[str, int | None, int | None, str],
            list,
        ] = defaultdict(list)
        storage_dir = get_settings().storage_dir
        source_link_review_before = datetime.now(timezone.utc) - timedelta(
            days=SOURCE_LINK_REVIEW_DAYS
        )
        stale_unused_before = datetime.now(timezone.utc) - timedelta(days=STALE_UNUSED_ASSET_DAYS)
        for group in groups:
            active_images = [image for image in group.images if image.deleted_at is None]
            for image in active_images:
                active_images_by_fingerprint[
                    (
                        image.file_name.strip().casefold(),
                        image.size_bytes,
                        image.width,
                        image.height,
                    )
                ].append((group, image))
                visual_hash = _average_image_hash(
                    storage_dir / image.storage_key,
                    media_type=image.media_type,
                )
                if visual_hash:
                    active_images_by_visual_hash[
                        (
                            image.media_type,
                            image.width,
                            image.height,
                            visual_hash,
                        )
                    ].append((group, image))
            has_relation = any(
                link.review_status != "rejected" and link.relation_role != "excludes"
                for link in group.concept_links
            )
            has_phrase = any(phrase.review_status != "rejected" for phrase in group.search_phrases)
            if not group.source_links:
                add(
                    group,
                    "missing_source_link",
                    "high",
                    "还没有记录 Figma、网盘或其他设计源文件。",
                    "补上源文件链接，后续设计师才能快速回到可编辑文件。",
                )
            elif all(
                _aware_datetime(link.updated_at) < source_link_review_before
                for link in group.source_links
            ):
                add(
                    group,
                    "stale_source_link",
                    "medium",
                    f"源文件链接已经超过 {SOURCE_LINK_REVIEW_DAYS} 天没有复查。",
                    "打开确认 Figma、网盘或设计文件仍可访问，必要时更新链接备注。",
                )
            if not has_relation:
                add(
                    group,
                    "missing_business_relation",
                    "high",
                    "还没有确认它主要表达或可以支持哪些业务概念。",
                    "在素材详情里确认业务关系，否则业务搜索很难稳定命中。",
                )
            if not has_phrase:
                add(
                    group,
                    "missing_search_phrase",
                    "medium",
                    "还没有沉淀这张图自己的搜索话术。",
                    "补 3-5 条业务方会说的话，提升模糊搜索召回。",
                )
            if len(active_images) <= 1:
                add(
                    group,
                    "single_version",
                    "medium",
                    "目前只有一个版本或尺寸。",
                    "按常用场景补 PPT、海报、详情页等延展尺寸。",
                )
            if not group.style_label:
                add(
                    group,
                    "missing_style",
                    "low",
                    "还没有标记设计风格。",
                    "补充风格标签，方便按视觉语言筛选。",
                )
            if sum(image.download_count for image in active_images) == 0:
                add(
                    group,
                    "unused_asset",
                    "low",
                    "这组素材还没有被业务下载使用过。",
                    "判断是新素材等待曝光，还是需要下架、重命名或补搜索话术。",
                )
                if _aware_datetime(group.updated_at) < stale_unused_before:
                    add(
                        group,
                        "stale_unused_asset",
                        "medium",
                        f"这组素材超过 {STALE_UNUSED_ASSET_DAYS} 天未更新且没有下载记录。",
                        "优先检查标题、业务关系和搜索话术；确认无价值时可下架或归档。",
                    )
            for image in active_images:
                if image.media_type == "image/gif" and image.size_bytes >= 8 * 1024 * 1024:
                    add(
                        group,
                        "large_gif",
                        "medium",
                        "这组素材包含较大的 GIF，列表动图预览可能影响加载速度。",
                        "考虑压缩 GIF、补静态替代图，或只在需要时保留动图版本。",
                    )
                    break

        duplicate_group_ids: set[str] = set()
        for duplicates in active_images_by_fingerprint.values():
            duplicate_asset_ids = {group.id for group, _image in duplicates}
            if len(duplicate_asset_ids) <= 1:
                continue
            for group, _image in duplicates:
                if group.id in duplicate_group_ids:
                    continue
                duplicate_group_ids.add(group.id)
                add(
                    group,
                    "possible_duplicate",
                    "medium",
                    "发现文件名、大小和尺寸一致的素材，可能是重复上传。",
                    "检查是否应合并为同一素材组的版本，或删除多余素材。",
                )

        visual_duplicate_group_ids: set[str] = set()
        for duplicates in active_images_by_visual_hash.values():
            duplicate_asset_ids = {group.id for group, _image in duplicates}
            if len(duplicate_asset_ids) <= 1:
                continue
            for group, _image in duplicates:
                if group.id in visual_duplicate_group_ids:
                    continue
                visual_duplicate_group_ids.add(group.id)
                add(
                    group,
                    "possible_visual_duplicate",
                    "medium",
                    "发现画面近似的素材，可能是重复上传或同视觉拆成了多个素材组。",
                    "检查是否应合并为同一素材组的版本，保留一个清晰主素材入口。",
                )

        severity_rank = {"high": 0, "medium": 1, "low": 2}
        return sorted(
            issues,
            key=lambda item: (
                severity_rank.get(item.severity, 3),
                item.updated_at,
                item.title,
            ),
            reverse=False,
        )[:limit]

    def _source_link_health(self) -> SourceLinkHealth:
        groups = self.ops.published_asset_groups()
        links = [link for group in groups for link in group.source_links]
        review_before = datetime.now(timezone.utc) - timedelta(days=SOURCE_LINK_REVIEW_DAYS)
        stale_links = [link for link in links if _aware_datetime(link.updated_at) < review_before]
        return SourceLinkHealth(
            total_links=len(links),
            groups_with_source_links=sum(1 for group in groups if group.source_links),
            groups_without_source_links=sum(1 for group in groups if not group.source_links),
            stale_link_count=len(stale_links),
            groups_requiring_review=len({link.asset_group_id for link in stale_links}),
            link_type_counts=self._top_items(link.link_type for link in links),
            recent_links=[
                SourceLinkRecentItem(
                    id=link.id,
                    asset_group_id=link.asset_group_id,
                    asset_group_title=link.asset_group.title,
                    primary_image_id=link.asset_group.primary_image_id,
                    label=link.label,
                    link_type=link.link_type,
                    url=link.url,
                    review_status=(
                        "stale" if _aware_datetime(link.updated_at) < review_before else "ok"
                    ),
                    updated_at=link.updated_at,
                )
                for link in self.ops.recent_source_links(limit=20)
            ],
        )

    def _search_performance(self, logs: list[SearchLog]) -> SearchPerformanceSummary:
        durations = sorted(item.duration_ms for item in logs if item.duration_ms is not None)
        total = len(logs)
        slow_logs = [
            item for item in logs if item.duration_ms is not None and item.duration_ms >= 3000
        ]
        model_work_unit_count = sum(
            (1 if item.normalized_query else 0) + (1 if item.reranker_used else 0) for item in logs
        )
        return SearchPerformanceSummary(
            sample_count=total,
            average_duration_ms=(round(sum(durations) / len(durations), 2) if durations else 0.0),
            p50_duration_ms=_percentile(durations, 0.5),
            p95_duration_ms=_percentile_95(durations),
            p99_duration_ms=_percentile(durations, 0.99),
            slow_search_count=len(slow_logs),
            slow_search_rate=_ratio(len(slow_logs), total),
            timeout_count=sum(1 for item in logs if item.timed_out),
            fallback_count=sum(1 for item in logs if item.fallback),
            cache_hit_count=sum(1 for item in logs if item.cache_hit),
            cache_hit_rate=_ratio(sum(1 for item in logs if item.cache_hit), total),
            reranker_used_count=sum(1 for item in logs if item.reranker_used),
            ai_understood_count=sum(1 for item in logs if item.normalized_query),
            model_work_unit_count=model_work_unit_count,
            model_work_unit_rate=_ratio(model_work_unit_count, total),
            recent_slow_logs=[
                log_read(item)
                for item in sorted(
                    slow_logs,
                    key=lambda item: item.duration_ms or 0,
                    reverse=True,
                )[:20]
            ],
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
                    suggested_action="先判断是素材缺口、概念关系缺失，还是业务话术没有进入意图词库",
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
            "right_business_wrong_visual": (
                "visual_mismatch",
                "业务点命中但画面表达不合适",
                "检查素材独有话术、画面风格和场景图标记，必要时补更贴合的视觉版本",
                "medium",
            ),
            "right_visual_wrong_business": (
                "business_mismatch",
                "画面对但业务卖点不对",
                "检查业务概念关系是否误标，避免视觉相似素材越界召回",
                "high",
            ),
            "wrong_version": (
                "wrong_version",
                "素材方向对但版本或尺寸不对",
                "补齐对应渠道/尺寸版本，并确认同组版本的渠道标记",
                "medium",
            ),
            "asset_request": (
                "asset_request",
                "业务方提交素材需求",
                "沉淀为素材需求，优先补齐高频业务话术对应图片",
                "high",
            ),
        }
        for event in feedback_events:
            if event.feedback_type == "relevant":
                continue
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

    def _ai_review_queue(self, limit: int = 50) -> list[AiConceptReviewQueueItem]:
        rows: list[AiConceptReviewQueueItem] = []
        for link in self.ops.pending_ai_concept_links(limit=limit):
            image_id = link.asset_group.primary_image_id
            if not image_id:
                continue
            rows.append(
                AiConceptReviewQueueItem(
                    id=link.id,
                    asset_group_id=link.asset_group_id,
                    image_id=image_id,
                    image_title=link.asset_group.title,
                    thumbnail_url=f"/api/images/{image_id}/thumbnail",
                    concept_code=link.concept.code,
                    concept_name=link.concept.name,
                    system_names=[
                        item.system_tag.name
                        for item in link.concept.system_links
                        if item.status == "active"
                    ],
                    relation_role=link.relation_role,
                    confidence=link.confidence,
                    reason=link.evidence_reason,
                    created_at=link.created_at,
                )
            )
        return rows

    def _concept_health(self, logs: list[SearchLog]) -> list[ConceptHealthItem]:
        concepts = self.ops.active_concepts()
        asset_counts = self.ops.asset_counts_by_concept()
        links = self.ops.active_concept_links()
        manual_counts: Counter[str] = Counter()
        ai_pending_counts: Counter[str] = Counter()
        ai_accepted_counts: Counter[str] = Counter()
        ai_rejected_counts: Counter[str] = Counter()
        for link in links:
            if link.origin in {"manual", "migrated"}:
                manual_counts[link.concept_id] += 1
            elif link.review_status == "pending":
                ai_pending_counts[link.concept_id] += 1
            elif link.review_status == "accepted":
                ai_accepted_counts[link.concept_id] += 1
            elif link.review_status == "rejected":
                ai_rejected_counts[link.concept_id] += 1

        search_counts: Counter[str] = Counter()
        for log in logs:
            for concept in concepts:
                if log.matched_concept == concept.name or log.normalized_query == concept.name:
                    search_counts[concept.id] += 1

        rows: list[ConceptHealthItem] = []
        for concept in concepts:
            image_count = int(asset_counts.get(concept.id, 0))
            pending = ai_pending_counts[concept.id]
            manual = manual_counts[concept.id]
            accepted = ai_accepted_counts[concept.id]
            search_count = search_counts[concept.id]
            if image_count == 0 and search_count > 0:
                level = "needs_assets"
                recommendation = "有搜索需求但没有可用素材，优先补图或检查概念关系"
            elif pending >= max(2, manual + accepted):
                level = "needs_review"
                recommendation = "AI 待审核量偏高，优先批量确认或拒绝"
            elif search_count > 0 and image_count < 3:
                level = "watch"
                recommendation = "有搜索需求但素材覆盖偏少，建议继续观察并补充"
            else:
                level = "healthy"
                recommendation = "当前概念供给和审核状态基本正常"
            rows.append(
                ConceptHealthItem(
                    concept_id=concept.id,
                    concept_code=concept.code,
                    concept_name=concept.name,
                    system_names=[
                        item.system_tag.name
                        for item in concept.system_links
                        if item.status == "active"
                    ],
                    image_count=image_count,
                    manual_count=manual,
                    ai_pending_count=pending,
                    ai_accepted_count=accepted,
                    ai_rejected_count=ai_rejected_counts[concept.id],
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
                item.concept_name,
            ),
        )[:80]

    def _asset_gaps(
        self,
        logs: list[SearchLog],
        feedback_events: list[SearchFeedbackEvent],
    ) -> list[AssetGapItem]:
        demand: Counter[str] = Counter()
        source: dict[str, set[str]] = {}
        suggested_concept: dict[str, str] = {}
        for log in logs:
            if log.result_count == 0:
                demand[log.keyword] += 2
                source.setdefault(log.keyword, set()).add("空结果")
            elif log.result_count < 3:
                demand[log.keyword] += 1
                source.setdefault(log.keyword, set()).add("结果少")
            if log.matched_concept or log.normalized_query:
                suggested_concept[log.keyword] = log.matched_concept or log.normalized_query or ""
        for event in feedback_events:
            if event.feedback_type in {
                "asset_request",
                "too_few_results",
                "need_different_style",
                "right_business_wrong_visual",
                "wrong_version",
            }:
                demand[event.keyword] += 2 if event.feedback_type == "asset_request" else 1
                source.setdefault(event.keyword, set()).add("用户反馈")
        rows = [
            AssetGapItem(
                keyword=keyword,
                demand_count=count,
                suggested_concept=suggested_concept.get(keyword) or None,
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


def _percentile_95(values: list[int]) -> int:
    return _percentile(values, 0.95)


def _percentile(values: list[int], percentile: float) -> int:
    if not values:
        return 0
    index = max(0, min(len(values) - 1, ceil(percentile * len(values)) - 1))
    return values[index]


def _ratio(part: int, total: int) -> float:
    if total <= 0:
        return 0.0
    return round(part / total, 4)


def _aware_datetime(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value


def _average_image_hash(path: Path, *, media_type: str) -> str | None:
    if media_type not in {"image/jpeg", "image/png", "image/webp", "image/gif"}:
        return None
    try:
        with PILImage.open(path) as image:
            grayscale = image.convert("L").resize((8, 8))
            pixels = list(grayscale.getdata())
    except (FileNotFoundError, OSError, UnidentifiedImageError):
        return None
    if not pixels:
        return None
    average = sum(pixels) / len(pixels)
    bits = "".join("1" if pixel >= average else "0" for pixel in pixels)
    return f"{int(bits, 2):016x}"
