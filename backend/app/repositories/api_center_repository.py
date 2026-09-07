from __future__ import annotations

from datetime import datetime, timedelta, timezone

from sqlalchemy import delete, desc, func, or_, select
from sqlalchemy.orm import Session

from app.models.api_provider import (
    ApiCenterSetting,
    ModelApiCredential,
    ModelApiHealthCheck,
    ModelCallTrace,
    ModelRoutingSlot,
)
from app.models.search_log import SearchLog


class ApiCenterRepository:
    def __init__(self, db: Session):
        self.db = db

    def add_credential(self, credential: ModelApiCredential) -> ModelApiCredential:
        self.db.add(credential)
        self.db.flush()
        return credential

    def get_credential(self, credential_id: str) -> ModelApiCredential | None:
        return self.db.get(ModelApiCredential, credential_id)

    def get_credential_by_label(self, label: str) -> ModelApiCredential | None:
        return self.db.scalar(
            select(ModelApiCredential).where(ModelApiCredential.label == label)
        )

    def find_credential_by_inventory_identity(
        self,
        *,
        provider_type: str,
        base_url: str,
        model_name: str,
        api_key_fingerprint: str,
        exclude_id: str | None = None,
    ) -> ModelApiCredential | None:
        query = (
            select(ModelApiCredential)
            .where(ModelApiCredential.provider_type == provider_type)
            .where(ModelApiCredential.base_url == base_url)
            .where(ModelApiCredential.model_name == model_name)
            .where(ModelApiCredential.api_key_fingerprint == api_key_fingerprint)
        )
        if exclude_id is not None:
            query = query.where(ModelApiCredential.id != exclude_id)
        return self.db.scalar(query.limit(1))

    def list_credentials(self) -> list[ModelApiCredential]:
        return list(
            self.db.scalars(
                select(ModelApiCredential)
                .order_by(
                    ModelApiCredential.priority.asc(),
                    ModelApiCredential.created_at.desc(),
                )
            ).all()
        )

    def list_credentials_due_for_health_check(
        self,
        *,
        cutoff: datetime,
        limit: int,
    ) -> list[ModelApiCredential]:
        return list(
            self.db.scalars(
                select(ModelApiCredential)
                .where(ModelApiCredential.status == "active")
                .where(
                    or_(
                        ModelApiCredential.last_checked_at.is_(None),
                        ModelApiCredential.last_checked_at < cutoff,
                    )
                )
                .order_by(
                    ModelApiCredential.last_checked_at.asc().nulls_first(),
                    ModelApiCredential.priority.asc(),
                    ModelApiCredential.created_at.asc(),
                )
                .limit(max(1, int(limit)))
            ).all()
        )

    def delete_credential(self, credential: ModelApiCredential) -> None:
        self.db.delete(credential)
        self.db.flush()

    def get_setting(self, key: str) -> ApiCenterSetting | None:
        return self.db.get(ApiCenterSetting, key)

    def set_setting(self, key: str, value: str) -> ApiCenterSetting:
        setting = self.get_setting(key)
        if setting is None:
            setting = ApiCenterSetting(key=key, value=value)
            self.db.add(setting)
        else:
            setting.value = value
        self.db.flush()
        return setting

    def list_auto_assign_credentials(self) -> list[ModelApiCredential]:
        return list(
            self.db.scalars(
                select(ModelApiCredential)
                .where(ModelApiCredential.auto_assign_enabled.is_(True))
                .where(ModelApiCredential.status == "active")
                .order_by(
                    ModelApiCredential.priority.asc(),
                    ModelApiCredential.last_latency_ms.asc().nulls_last(),
                    ModelApiCredential.created_at.asc(),
                )
            ).all()
        )

    def add_slot(self, slot: ModelRoutingSlot) -> ModelRoutingSlot:
        self.db.add(slot)
        self.db.flush()
        return slot

    def get_slot_by_task(self, task: str) -> ModelRoutingSlot | None:
        return self.db.scalar(select(ModelRoutingSlot).where(ModelRoutingSlot.task == task))

    def list_slots(self) -> list[ModelRoutingSlot]:
        return list(
            self.db.scalars(
                select(ModelRoutingSlot).order_by(ModelRoutingSlot.created_at.asc())
            ).all()
        )

    def delete_slot(self, slot: ModelRoutingSlot) -> None:
        self.db.delete(slot)
        self.db.flush()

    def add_health_check(self, check: ModelApiHealthCheck) -> ModelApiHealthCheck:
        self.db.add(check)
        self.db.flush()
        return check

    def list_recent_health_checks(self, *, limit: int = 50) -> list[ModelApiHealthCheck]:
        return list(
            self.db.scalars(
                select(ModelApiHealthCheck)
                .order_by(desc(ModelApiHealthCheck.checked_at))
                .limit(limit)
            ).all()
        )

    def add_call_trace(self, trace: ModelCallTrace) -> ModelCallTrace:
        self.db.add(trace)
        self.db.flush()
        return trace

    def list_recent_call_traces(self, *, limit: int = 100) -> list[ModelCallTrace]:
        return list(
            self.db.scalars(
                select(ModelCallTrace)
                .order_by(desc(ModelCallTrace.created_at))
                .limit(limit)
            ).all()
        )

    def list_call_traces_filtered(
        self,
        *,
        limit: int = 100,
        offset: int = 0,
        task: str | None = None,
        status: str | None = None,
        provider: str | None = None,
        credential_id: str | None = None,
        request_id: str | None = None,
        keyword: str | None = None,
    ) -> tuple[int, list[ModelCallTrace]]:
        base_filters = []
        if task:
            base_filters.append(ModelCallTrace.task == task)
        if status:
            base_filters.append(ModelCallTrace.status == status)
        if provider:
            provider_pattern = f"%{provider}%"
            base_filters.append(ModelCallTrace.provider.ilike(provider_pattern))
        if credential_id:
            base_filters.append(ModelCallTrace.credential_id == credential_id)
        if request_id:
            base_filters.append(ModelCallTrace.request_id == request_id)
        keyword_filter = None
        if keyword:
            keyword_pattern = f"%{keyword}%"
            keyword_filter = or_(
                SearchLog.keyword.ilike(keyword_pattern),
                ModelCallTrace.request_id.ilike(keyword_pattern),
                ModelCallTrace.layer_name.ilike(keyword_pattern),
                ModelCallTrace.error_code.ilike(keyword_pattern),
                ModelCallTrace.error_summary.ilike(keyword_pattern),
            )

        count_stmt = select(func.count()).select_from(ModelCallTrace)
        query = select(ModelCallTrace)
        if keyword_filter is not None:
            count_stmt = count_stmt.outerjoin(
                SearchLog,
                SearchLog.id == ModelCallTrace.search_log_id,
            )
            query = query.outerjoin(
                SearchLog,
                SearchLog.id == ModelCallTrace.search_log_id,
            )
        if base_filters:
            count_stmt = count_stmt.where(*base_filters)
            query = query.where(*base_filters)
        if keyword_filter is not None:
            count_stmt = count_stmt.where(keyword_filter)
            query = query.where(keyword_filter)

        safe_limit = min(max(1, int(limit)), 500)
        safe_offset = max(0, int(offset))
        total = int(self.db.scalar(count_stmt) or 0)
        items = list(
            self.db.scalars(
                query.order_by(desc(ModelCallTrace.created_at))
                .offset(safe_offset)
                .limit(safe_limit)
            ).all()
        )
        return total, items

    def get_search_log_id_by_request_id(self, request_id: str) -> str | None:
        return self.db.scalar(
            select(SearchLog.id)
            .where(SearchLog.request_id == request_id)
            .order_by(desc(SearchLog.created_at))
            .limit(1)
        )

    def search_context_by_ids(
        self,
        search_log_ids: set[str],
    ) -> dict[str, tuple[str, int, bool]]:
        if not search_log_ids:
            return {}
        return {
            search_log_id: (keyword, result_count, timed_out)
            for search_log_id, keyword, result_count, timed_out in self.db.execute(
                select(
                    SearchLog.id,
                    SearchLog.keyword,
                    SearchLog.result_count,
                    SearchLog.timed_out,
                ).where(SearchLog.id.in_(search_log_ids))
            ).all()
        }

    def list_call_traces_since(self, *, hours: int = 24, limit: int = 2000) -> list[ModelCallTrace]:
        since = datetime.now(timezone.utc) - timedelta(hours=max(1, hours))
        return list(
            self.db.scalars(
                select(ModelCallTrace)
                .where(ModelCallTrace.created_at >= since)
                .order_by(desc(ModelCallTrace.created_at))
                .limit(limit)
            ).all()
        )

    def delete_call_traces_before(self, cutoff: datetime) -> int:
        result = self.db.execute(
            delete(ModelCallTrace).where(ModelCallTrace.created_at < cutoff)
        )
        self.db.flush()
        return int(result.rowcount or 0)

    def delete_health_checks_before(self, cutoff: datetime) -> int:
        result = self.db.execute(
            delete(ModelApiHealthCheck).where(ModelApiHealthCheck.checked_at < cutoff)
        )
        self.db.flush()
        return int(result.rowcount or 0)
