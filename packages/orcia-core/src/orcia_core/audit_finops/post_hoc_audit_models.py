"""Domain models & pure `Decimal` calculators for Post-Hoc Sampling & `SM-A1..A3` (`Story 7.4`)."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from datetime import datetime
from decimal import ROUND_HALF_UP, Decimal
from typing import Literal

PostHocReviewStatus = Literal["PENDING_SAMPLE", "VALIDATED", "INVALIDATED_ROLLED_BACK"]

DEFAULT_POST_HOC_SAMPLING_RATE = Decimal("0.15")
MIN_SAMPLING_RATE = Decimal("0.10")
MAX_SAMPLING_RATE = Decimal("0.20")
INVALIDATION_ALERT_THRESHOLD = Decimal("0.01")


@dataclass(frozen=True, slots=True)
class PostHocAuditSampleRecord:
    """Single sampled autonomous run awaiting or having completed post-hoc human review."""

    id: str
    run_id: str
    workspace_id: str
    contract_id: str
    workflow_title: str
    trigger_label: str
    review_status: PostHocReviewStatus
    run_status: str
    sampled_at: datetime
    reviewer_user_id: str | None = None
    review_comment: str | None = None
    reviewed_at: datetime | None = None


@dataclass(frozen=True, slots=True)
class AutonomousGovernanceMetrics:
    """Consolidated autonomous governance metrics `SM-A1`, `SM-A2`, `SM-A3` (`Decimal`)."""

    total_autonomous_runs: int
    escalated_runs_count: int
    killed_runs_count: int
    sampled_runs_count: int
    pending_samples_count: int
    invalidated_samples_count: int
    autonomous_escalation_rate: Decimal
    post_hoc_invalidation_rate: Decimal
    invalidation_alert: bool
    avg_autonomous_cost_usd: Decimal
    avg_ttm_gain_minutes: Decimal
    pending_samples: tuple[PostHocAuditSampleRecord, ...] = field(default_factory=tuple)


def clamp_sampling_rate(rate: Decimal | float | str | None) -> Decimal:
    """Clamp post-hoc sampling rate to `[0.10, 0.20]` (default `0.15`)."""
    if rate is None:
        return DEFAULT_POST_HOC_SAMPLING_RATE
    dec = Decimal(str(rate))
    if dec < MIN_SAMPLING_RATE:
        return MIN_SAMPLING_RATE
    if dec > MAX_SAMPLING_RATE:
        return MAX_SAMPLING_RATE
    return dec


def select_post_hoc_sample_deterministic(
    *,
    run_id: str,
    sampling_rate: Decimal | float = DEFAULT_POST_HOC_SAMPLING_RATE,
) -> bool:
    """Deterministically select `[10%, 20%]` of `COMMITTED_AUTONOMOUS` runs via SHA-256."""
    clamped = clamp_sampling_rate(sampling_rate)
    threshold_bps = int((clamped * Decimal("10000")).to_integral_value(rounding=ROUND_HALF_UP))
    digest = hashlib.sha256(run_id.encode("utf-8")).hexdigest()
    bucket = int(digest[:8], 16) % 10000
    return bucket < threshold_bps


def compute_autonomous_governance_metrics(
    *,
    total_autonomous_runs: int,
    escalated_runs_count: int,
    killed_runs_count: int,
    sampled_runs_count: int,
    pending_samples_count: int,
    validated_samples_count: int,
    invalidated_samples_count: int,
    total_autonomous_cost_usd: Decimal,
    total_ttm_gain_minutes: Decimal,
    pending_samples: tuple[PostHocAuditSampleRecord, ...] = (),
) -> AutonomousGovernanceMetrics:
    """Compute `SM-A1`, `SM-A2`, `SM-A3` in exact `Decimal` arithmetic."""
    if total_autonomous_runs > 0:
        esc_rate = (Decimal(escalated_runs_count) / Decimal(total_autonomous_runs)).quantize(
            Decimal("0.0001"), rounding=ROUND_HALF_UP
        )
        avg_cost = (total_autonomous_cost_usd / Decimal(total_autonomous_runs)).quantize(
            Decimal("0.000001"), rounding=ROUND_HALF_UP
        )
        avg_ttm_gain = (total_ttm_gain_minutes / Decimal(total_autonomous_runs)).quantize(
            Decimal("0.01"), rounding=ROUND_HALF_UP
        )
    else:
        esc_rate = Decimal("0.0000")
        avg_cost = Decimal("0.000000")
        avg_ttm_gain = Decimal("0.00")

    reviewed_count = validated_samples_count + invalidated_samples_count
    denom = reviewed_count if reviewed_count > 0 else sampled_runs_count
    if denom > 0:
        inv_rate = (Decimal(invalidated_samples_count) / Decimal(denom)).quantize(
            Decimal("0.0001"), rounding=ROUND_HALF_UP
        )
    else:
        inv_rate = Decimal("0.0000")

    return AutonomousGovernanceMetrics(
        total_autonomous_runs=total_autonomous_runs,
        escalated_runs_count=escalated_runs_count,
        killed_runs_count=killed_runs_count,
        sampled_runs_count=sampled_runs_count,
        pending_samples_count=pending_samples_count,
        invalidated_samples_count=invalidated_samples_count,
        autonomous_escalation_rate=esc_rate,
        post_hoc_invalidation_rate=inv_rate,
        invalidation_alert=inv_rate >= INVALIDATION_ALERT_THRESHOLD,
        avg_autonomous_cost_usd=avg_cost,
        avg_ttm_gain_minutes=avg_ttm_gain,
        pending_samples=pending_samples,
    )


def compute_in_memory_governance_metrics(
    in_mem_runs: list[dict[str, object]],
    in_mem_samples: list[PostHocAuditSampleRecord],
    *,
    scope_type: str,
    scope_id: str | None,
    allowed_workspace_ids: tuple[str, ...] | frozenset[str] | None,
) -> AutonomousGovernanceMetrics:
    """Compute autonomous governance KPIs from in-memory run and sample collections."""
    scoped_runs = [
        r
        for r in in_mem_runs
        if (allowed_workspace_ids is None or str(r["workspace_id"]) in allowed_workspace_ids)
        and (scope_type != "WORKSPACE" or scope_id is None or str(r["workspace_id"]) == scope_id)
    ]
    scoped_samples = [
        s
        for s in in_mem_samples
        if (allowed_workspace_ids is None or s.workspace_id in allowed_workspace_ids)
        and (scope_type != "WORKSPACE" or scope_id is None or s.workspace_id == scope_id)
    ]
    total_cost = sum((Decimal(str(r["cost_usd"])) for r in scoped_runs), Decimal("0.000000"))
    total_ttm = sum((Decimal(str(r["ttm_gain_minutes"])) for r in scoped_runs), Decimal("0.00"))
    return compute_autonomous_governance_metrics(
        total_autonomous_runs=len(scoped_runs),
        escalated_runs_count=sum(
            1 for r in scoped_runs if r["status"] == "PAUSED_AUTONOMOUS_ESCALATION"
        ),
        killed_runs_count=sum(1 for r in scoped_runs if r["status"] == "KILL_SWITCH_STOPPED"),
        sampled_runs_count=len(scoped_samples),
        pending_samples_count=sum(1 for s in scoped_samples if s.review_status == "PENDING_SAMPLE"),
        validated_samples_count=sum(1 for s in scoped_samples if s.review_status == "VALIDATED"),
        invalidated_samples_count=sum(
            1 for s in scoped_samples if s.review_status == "INVALIDATED_ROLLED_BACK"
        ),
        total_autonomous_cost_usd=total_cost,
        total_ttm_gain_minutes=total_ttm,
        pending_samples=tuple(scoped_samples),
    )
