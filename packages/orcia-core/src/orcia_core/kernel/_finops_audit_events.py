"""Domain events for FinOps, audit ledger, circuit breakers, and telemetry (`AD-12`, `AD-19`).

Pure kernel module — zero framework or business domain dependencies.
Kept in a focused file to enforce strict lines-of-code thresholds (< 350 lines).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from orcia_core.kernel._events_base import DomainEvent
from orcia_core.kernel.ids import new_uuid7_str


@dataclass(frozen=True, slots=True)
class AdminConnectionTested(DomainEvent):
    """Published when an administrator triggers a live connectivity or health test."""

    target_type: str = ""
    target_id: str = ""
    protocol: str = ""
    test_status: str = "SUCCESS"
    latency_ms: int = 0
    detail: str = ""

    @classmethod
    def create(
        cls,
        *,
        actor_id: str,
        target_type: str,
        target_id: str,
        protocol: str = "",
        test_status: str = "SUCCESS",
        latency_ms: int = 0,
        detail: str = "",
        workspace_id: str | None = None,
        trace_id: str = "00000000000000000000000000000000",
        metadata: dict[str, Any] | None = None,
    ) -> AdminConnectionTested:
        payload: dict[str, Any] = {
            "actor_id": actor_id,
            "target_type": target_type,
            "target_id": target_id,
            "protocol": protocol,
            "test_status": test_status,
            "latency_ms": latency_ms,
            "detail": detail,
            **(metadata or {}),
        }
        return cls(
            event_id=new_uuid7_str(),
            event_type="AdminConnectionTested",
            aggregate_type=target_type or "admin_connection_test",
            aggregate_id=target_id or new_uuid7_str(),
            run_id=None,
            workspace_id=workspace_id,
            payload=payload,
            trace_id=trace_id,
            target_type=target_type,
            target_id=target_id,
            protocol=protocol,
            test_status=test_status,
            latency_ms=latency_ms,
            detail=detail,
        )


@dataclass(frozen=True, slots=True)
class BudgetCircuitTripped(DomainEvent):
    """Published when a workflow run or scope budget hard ceiling is reached."""

    current_burn_usd: float = 0.0
    budget_limit_usd: float = 0.0
    trip_reason: str = ""

    @classmethod
    def create(
        cls,
        *,
        run_id: str | None,
        workspace_id: str | None,
        current_burn_usd: float,
        budget_limit_usd: float,
        trip_reason: str,
        trace_id: str = "00000000000000000000000000000000",
    ) -> BudgetCircuitTripped:
        return cls(
            event_id=new_uuid7_str(),
            event_type="BudgetCircuitTripped",
            aggregate_type="budget_circuit",
            aggregate_id=run_id or (workspace_id or "global"),
            run_id=run_id,
            workspace_id=workspace_id,
            payload={
                "current_burn_usd": current_burn_usd,
                "budget_limit_usd": budget_limit_usd,
                "trip_reason": trip_reason,
            },
            trace_id=trace_id,
            current_burn_usd=current_burn_usd,
            budget_limit_usd=budget_limit_usd,
            trip_reason=trip_reason,
        )


@dataclass(frozen=True, slots=True)
class BudgetOverrideApproved(DomainEvent):
    """Published when an authorized human manager extends budget for a paused run."""

    override_amount_usd: float = 0.0
    approved_by_user_id: str = ""
    justification: str = ""

    @classmethod
    def create(
        cls,
        *,
        run_id: str,
        workspace_id: str | None,
        override_amount_usd: float,
        approved_by_user_id: str,
        justification: str,
        trace_id: str = "00000000000000000000000000000000",
    ) -> BudgetOverrideApproved:
        return cls(
            event_id=new_uuid7_str(),
            event_type="BudgetOverrideApproved",
            aggregate_type="budget_override",
            aggregate_id=run_id,
            run_id=run_id,
            workspace_id=workspace_id,
            payload={
                "override_amount_usd": override_amount_usd,
                "approved_by_user_id": approved_by_user_id,
                "justification": justification,
            },
            trace_id=trace_id,
            override_amount_usd=override_amount_usd,
            approved_by_user_id=approved_by_user_id,
            justification=justification,
        )


@dataclass(frozen=True, slots=True)
class RemoteUsageAnomalyCapped(DomainEvent):
    """Published when an external MCP/A2A usage report exceeds safety thresholds."""

    connector_id: str = ""
    reported_cost_eur: float = 0.0
    capped_cost_eur: float = 0.0

    @classmethod
    def create(
        cls,
        *,
        connector_id: str,
        reported_cost_eur: float,
        capped_cost_eur: float,
        workspace_id: str | None = None,
        run_id: str | None = None,
        trace_id: str = "00000000000000000000000000000000",
    ) -> RemoteUsageAnomalyCapped:
        return cls(
            event_id=new_uuid7_str(),
            event_type="RemoteUsageAnomalyCapped",
            aggregate_type="connector_usage",
            aggregate_id=connector_id,
            run_id=run_id,
            workspace_id=workspace_id,
            payload={
                "connector_id": connector_id,
                "reported_cost_eur": reported_cost_eur,
                "capped_cost_eur": capped_cost_eur,
            },
            trace_id=trace_id,
            connector_id=connector_id,
            reported_cost_eur=reported_cost_eur,
            capped_cost_eur=capped_cost_eur,
        )


@dataclass(frozen=True, slots=True)
class ConnectorCircuitTripped(DomainEvent):
    """Published when an external connector exceeds volume or cost limits and opens circuit."""

    connector_id: str = ""
    circuit_state: str = "CIRCUIT_OPEN"
    reason: str = ""

    @classmethod
    def create(
        cls,
        *,
        connector_id: str,
        circuit_state: str = "CIRCUIT_OPEN",
        reason: str = "",
        workspace_id: str | None = None,
        trace_id: str = "00000000000000000000000000000000",
    ) -> ConnectorCircuitTripped:
        return cls(
            event_id=new_uuid7_str(),
            event_type="ConnectorCircuitTripped",
            aggregate_type="connector_circuit",
            aggregate_id=connector_id,
            run_id=None,
            workspace_id=workspace_id,
            payload={
                "connector_id": connector_id,
                "circuit_state": circuit_state,
                "reason": reason,
            },
            trace_id=trace_id,
            connector_id=connector_id,
            circuit_state=circuit_state,
            reason=reason,
        )
