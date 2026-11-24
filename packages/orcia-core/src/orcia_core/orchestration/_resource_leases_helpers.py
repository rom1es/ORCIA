"""Lease validation & ancestor resolution helpers for `ResourceLeaseService` (`DEC-CONC-01`)."""

from __future__ import annotations

from datetime import datetime

from orcia_core.orchestration.errors import (
    CyclicResourceWaitDetectedError,
    ResourceLeaseHeldByOtherRunError,
)
from orcia_kernel.ports import ResourceLeaseRecord


def classify_resource_uri(resource_uri: str) -> str:
    """Derive DBOS resource queue class from `resource_uri` scheme (`DEC-CONC-01`)."""
    raw = resource_uri.strip()
    if "://" in raw:
        scheme = raw.split("://", 1)[0].strip().lower()
        return f"queue:resource:{scheme}" if scheme else "queue:resource:default"
    return "queue:resource:default"


def resolve_ancestors_unlocked(
    run_parent_map: dict[str, str],
    holder_run_id: str,
    holder_parent_run_id: str | None,
    explicit: tuple[str, ...],
) -> set[str]:
    """Compute ancestor run IDs while recording `holder_parent_run_id`."""
    ancestors: set[str] = {a for a in explicit if a}
    if holder_parent_run_id:
        ancestors.add(holder_parent_run_id)
        run_parent_map[holder_run_id] = holder_parent_run_id
    cursor = run_parent_map.get(holder_run_id)
    visited: set[str] = {holder_run_id}
    while cursor and cursor not in visited:
        ancestors.add(cursor)
        visited.add(cursor)
        cursor = run_parent_map.get(cursor)
    return ancestors


def check_lease_conflicts_unlocked(
    active_leases: dict[str, ResourceLeaseRecord],
    *,
    cleaned_uris: tuple[str, ...],
    holder_run_id: str,
    holder_step_execution_id: str,
    holder_parent_run_id: str | None,
    ancestors: set[str],
    now: datetime,
) -> None:
    """Raise `CyclicResourceWaitDetectedError` or `ResourceLeaseHeldByOtherRunError` on conflict."""
    for uri in cleaned_uris:
        existing = active_leases.get(uri)
        if existing is None or datetime.fromisoformat(existing.expires_at) <= now:
            continue
        if (
            existing.holder_run_id == holder_run_id
            and existing.holder_step_execution_id == holder_step_execution_id
        ):
            continue
        if existing.holder_run_id in ancestors or (
            holder_parent_run_id is not None and existing.holder_run_id == holder_parent_run_id
        ):
            raise CyclicResourceWaitDetectedError(
                detail_code="ERR_RESOURCE_LEASE_CYCLIC_WAIT",
                detail_params={
                    "uri": uri,
                    "holder_run_id": holder_run_id,
                    "existing_holder": existing.holder_run_id,
                },
            )
        raise ResourceLeaseHeldByOtherRunError(
            detail_code="ERR_RESOURCE_LEASE_HELD",
            detail_params={
                "uri": uri,
                "holder": existing.holder_run_id,
                "token": existing.fencing_token,
                "expires_at": existing.expires_at,
            },
        )


__all__ = [
    "check_lease_conflicts_unlocked",
    "classify_resource_uri",
    "resolve_ancestors_unlocked",
]
