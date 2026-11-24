"""Post-Hoc Quality Sampling (`10-20%`) Service (`Story 7.4`)."""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from typing import Literal

from sqlalchemy.ext.asyncio import AsyncEngine

from orcia_core.audit_finops._audit_finops_locales import get_audit_finops_locale_bundle
from orcia_core.audit_finops._internal.sql_autonomous_metrics import (
    fetch_autonomous_governance_aggregates_sql,
    fetch_post_hoc_samples_sql,
    insert_post_hoc_sample_sql,
    update_post_hoc_review_sql,
)
from orcia_core.audit_finops.finops_models import ScopeType
from orcia_core.audit_finops.post_hoc_audit_models import (
    DEFAULT_POST_HOC_SAMPLING_RATE,
    INVALIDATION_ALERT_THRESHOLD,
    MAX_SAMPLING_RATE,
    MIN_SAMPLING_RATE,
    AutonomousGovernanceMetrics,
    PostHocAuditSampleRecord,
    PostHocReviewStatus,
    clamp_sampling_rate,
    compute_autonomous_governance_metrics,
    compute_in_memory_governance_metrics,
    select_post_hoc_sample_deterministic,
)
from orcia_core.kernel.events import DomainEvent, PostHocSampleSelected
from orcia_core.kernel.ids import new_uuid7_str
from orcia_core.ports.finops_telemetry import AuditLedgerSinkPort


class PostHocAuditService:
    """Domain service orchestrating post-hoc sampling & `SM-A1..A3` metrics (`Story 7.4`)."""

    def __init__(
        self,
        *,
        engine: AsyncEngine | None = None,
        audit_sink: AuditLedgerSinkPort | None = None,
    ) -> None:
        self._engine = engine
        self._audit_sink = audit_sink
        self._in_mem_samples: dict[str, PostHocAuditSampleRecord] = {}
        self._in_mem_runs: list[dict[str, object]] = []
        self._outbox_events: list[DomainEvent] = []

    @property
    def outbox_events(self) -> tuple[DomainEvent, ...]:
        return tuple(self._outbox_events)

    def register_in_memory_run(
        self,
        *,
        run_id: str,
        workspace_id: str,
        status: str,
        cost_usd: Decimal = Decimal("0.050000"),
        ttm_gain_minutes: Decimal = Decimal("15.00"),
    ) -> None:
        """Record an in-memory run for unit tests when PostgreSQL engine is absent."""
        for existing in self._in_mem_runs:
            if existing["run_id"] == run_id:
                existing["status"] = status
                return
        self._in_mem_runs.append(
            {
                "run_id": run_id,
                "workspace_id": workspace_id,
                "status": status,
                "cost_usd": cost_usd,
                "ttm_gain_minutes": ttm_gain_minutes,
            }
        )

    async def maybe_sample_committed_run(
        self,
        *,
        run_id: str,
        workspace_id: str,
        contract_id: str,
        workflow_id: str,
        sampling_rate: Decimal | float = DEFAULT_POST_HOC_SAMPLING_RATE,
        force_select: bool = False,
        trigger_label: str | None = None,
        trace_id: str = "00000000000000000000000000000000",
        locale: str = "fr",
    ) -> PostHocAuditSampleRecord | None:
        """Select a `COMMITTED_AUTONOMOUS` run into `autonomous_post_hoc_audits` (`10-20%`)."""
        effective_label = (
            trigger_label or get_audit_finops_locale_bundle(locale).post_hoc_contract_trigger
        )
        rate = clamp_sampling_rate(sampling_rate)
        if not force_select and not select_post_hoc_sample_deterministic(
            run_id=run_id, sampling_rate=rate
        ):
            return None

        audit_id = new_uuid7_str()
        event = PostHocSampleSelected.create(
            audit_id=audit_id,
            run_id=run_id,
            workspace_id=workspace_id,
            contract_id=contract_id,
            workflow_id=workflow_id,
            sampling_rate=float(rate),
            trace_id=trace_id,
        )
        if self._engine is not None:
            inserted = await insert_post_hoc_sample_sql(
                self._engine,
                audit_id=audit_id,
                run_id=run_id,
                workspace_id=workspace_id,
                contract_id=contract_id,
                event=event,
                audit_sink=self._audit_sink,
            )
            if not inserted:
                return None

        rec = PostHocAuditSampleRecord(
            id=audit_id,
            run_id=run_id,
            workspace_id=workspace_id,
            contract_id=contract_id,
            workflow_title=workflow_id.rsplit("/", 1)[-1] or workflow_id,
            trigger_label=effective_label,
            review_status="PENDING_SAMPLE",
            run_status="COMMITTED_AUTONOMOUS",
            sampled_at=datetime.now(UTC),
        )
        self._in_mem_samples[run_id] = rec
        self._outbox_events.append(event)
        return rec

    async def record_review(
        self,
        *,
        run_id: str,
        decision: Literal["VALIDATED", "INVALIDATED_ROLLED_BACK"],
        reviewer_user_id: str,
        review_comment: str | None = None,
        workspace_id: str | None = None,
        contract_id: str | None = None,
    ) -> PostHocAuditSampleRecord | None:
        """Record a post-hoc sample validation or invalidation decision."""
        if self._engine is not None:
            row = await update_post_hoc_review_sql(
                self._engine,
                run_id=run_id,
                review_status=decision,
                reviewer_user_id=reviewer_user_id,
                review_comment=review_comment,
                workspace_id=workspace_id,
                contract_id=contract_id,
            )
            if row is not None:
                return PostHocAuditSampleRecord(
                    id=str(row["id"]),
                    run_id=str(row["run_id"]),
                    workspace_id=str(row["workspace_id"]),
                    contract_id=str(row["contract_id"]),
                    workflow_title="",
                    trigger_label="",
                    review_status=row["review_status"],
                    run_status=(
                        "ROLLED_BACK"
                        if decision == "INVALIDATED_ROLLED_BACK"
                        else "COMMITTED_AUTONOMOUS"
                    ),
                    sampled_at=row["sampled_at"],
                    reviewer_user_id=row["reviewer_user_id"],
                    review_comment=row["review_comment"],
                    reviewed_at=row["reviewed_at"],
                )
            return None

        existing = self._in_mem_samples.get(run_id)
        if existing is None and (workspace_id is None or contract_id is None):
            return None
        now = datetime.now(UTC)
        updated = PostHocAuditSampleRecord(
            id=existing.id if existing else new_uuid7_str(),
            run_id=run_id,
            workspace_id=existing.workspace_id if existing else str(workspace_id),
            contract_id=existing.contract_id if existing else str(contract_id),
            workflow_title=existing.workflow_title if existing else "",
            trigger_label=existing.trigger_label if existing else "",
            review_status=decision,
            run_status=(
                "ROLLED_BACK" if decision == "INVALIDATED_ROLLED_BACK" else "COMMITTED_AUTONOMOUS"
            ),
            sampled_at=existing.sampled_at if existing else now,
            reviewer_user_id=reviewer_user_id,
            review_comment=review_comment,
            reviewed_at=now,
        )
        self._in_mem_samples[run_id] = updated
        return updated

    async def get_autonomous_governance_metrics(
        self,
        *,
        scope_type: ScopeType = "GLOBAL",
        scope_id: str | None = None,
        time_window: str = "30D",
        allowed_workspace_ids: tuple[str, ...] | None = None,
    ) -> AutonomousGovernanceMetrics:
        """Return consolidated `SM-A1..A3` metrics and pending post-hoc samples."""
        if self._engine is not None:
            agg = await fetch_autonomous_governance_aggregates_sql(
                self._engine,
                scope_type=scope_type,
                scope_id=scope_id,
                time_window=time_window,
                allowed_workspace_ids=allowed_workspace_ids,
            )
            raw_samples = await fetch_post_hoc_samples_sql(
                self._engine,
                scope_type=scope_type,
                scope_id=scope_id,
                allowed_workspace_ids=allowed_workspace_ids,
            )
            samples = tuple(
                PostHocAuditSampleRecord(
                    id=str(r["id"]),
                    run_id=str(r["run_id"]),
                    workspace_id=str(r["workspace_id"]),
                    contract_id=str(r["contract_id"]),
                    workflow_title=str(r["workflow_uri"]).rsplit("/", 1)[-1]
                    or str(r["workflow_uri"]),
                    trigger_label=str(r["trigger_label"]),
                    review_status=r["review_status"],
                    run_status=str(r["run_status"]),
                    sampled_at=r["sampled_at"],
                    reviewer_user_id=r["reviewer_user_id"],
                    review_comment=r["review_comment"],
                    reviewed_at=r["reviewed_at"],
                )
                for r in raw_samples
            )
            return compute_autonomous_governance_metrics(
                total_autonomous_runs=agg["total_autonomous_runs"],
                escalated_runs_count=agg["escalated_runs_count"],
                killed_runs_count=agg["killed_runs_count"],
                sampled_runs_count=agg["sampled_runs_count"],
                pending_samples_count=agg["pending_samples_count"],
                validated_samples_count=agg["validated_samples_count"],
                invalidated_samples_count=agg["invalidated_samples_count"],
                total_autonomous_cost_usd=agg["total_autonomous_cost_usd"],
                total_ttm_gain_minutes=agg["total_ttm_gain_minutes"],
                pending_samples=samples,
            )

        return compute_in_memory_governance_metrics(
            self._in_mem_runs,
            list(self._in_mem_samples.values()),
            scope_type=scope_type,
            scope_id=scope_id,
            allowed_workspace_ids=allowed_workspace_ids,
        )


__all__ = [
    "DEFAULT_POST_HOC_SAMPLING_RATE",
    "INVALIDATION_ALERT_THRESHOLD",
    "MAX_SAMPLING_RATE",
    "MIN_SAMPLING_RATE",
    "AutonomousGovernanceMetrics",
    "PostHocAuditSampleRecord",
    "PostHocAuditService",
    "PostHocReviewStatus",
    "clamp_sampling_rate",
    "compute_autonomous_governance_metrics",
    "select_post_hoc_sample_deterministic",
]
