"""Shared Resource Lease Port & Monotonic Fencing Service (`DEC-CONC-01`, `AD-4`, `Story 5.1`).

Enforces:
1. Monotonic fencing tokens (`fencing_token >= highest_token(resource_uri)`), rejecting stale
   writes with `StaleFencingTokenError` (`HTTP 409`).
2. Canonical acquisition ordering (`sorted(set(resource_uris))`) to eliminate cross-resource
   deadlocks when a step locks multiple shared URIs.
3. Parent-child cyclic wait detection (`SUB_WORKFLOW` deadlock guard): if a child run attempts to
   acquire a resource currently leased by an ancestor run in its lineage, raises
   `CyclicResourceWaitDetectedError` (`HTTP 409`) immediately.
4. Lease expiration (`expires_at <= now`) allowing fenced preemption with an incremented fencing
   token.
"""

from __future__ import annotations

import threading
from datetime import UTC, datetime, timedelta
from typing import Any

from orcia_core.orchestration.errors import (
    CyclicResourceWaitDetectedError,
    ResourceLeaseHeldByOtherRunError,
    StaleFencingTokenError,
    ValidationDomainError,
)
from orcia_kernel.ids import new_uuid7_str
from orcia_kernel.ports import ResourceLeasePort, ResourceLeaseRecord


def _classify_resource_uri(resource_uri: str) -> str:
    """Derive DBOS resource queue class from `resource_uri` scheme (`DEC-CONC-01`)."""
    raw = resource_uri.strip()
    if "://" in raw:
        scheme = raw.split("://", 1)[0].strip().lower()
        return f"queue:resource:{scheme}" if scheme else "queue:resource:default"
    return "queue:resource:default"


class ResourceLeaseService(ResourceLeasePort):
    """Concurrent-ready shared resource lease manager with monotonic fencing & deadlock guard."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._active_leases: dict[str, ResourceLeaseRecord] = {}
        self._fencing_counters: dict[str, int] = {}
        self._run_parent_map: dict[str, str] = {}

    def register_run_parent(self, child_run_id: str, parent_run_id: str) -> None:
        """Record parent-child `SUB_WORKFLOW` relationship for cyclic wait detection."""
        with self._lock:
            self._run_parent_map[child_run_id] = parent_run_id

    def _resolve_ancestors_unlocked(
        self, holder_run_id: str, holder_parent_run_id: str | None, explicit: tuple[str, ...]
    ) -> set[str]:
        ancestors: set[str] = {a for a in explicit if a}
        if holder_parent_run_id:
            ancestors.add(holder_parent_run_id)
            self._run_parent_map[holder_run_id] = holder_parent_run_id
        cursor = self._run_parent_map.get(holder_run_id)
        visited: set[str] = {holder_run_id}
        while cursor and cursor not in visited:
            ancestors.add(cursor)
            visited.add(cursor)
            cursor = self._run_parent_map.get(cursor)
        return ancestors

    def acquire_leases(
        self,
        *,
        resource_uris: tuple[str, ...],
        holder_run_id: str,
        holder_root_run_id: str,
        holder_step_execution_id: str,
        holder_parent_run_id: str | None = None,
        ancestor_run_ids: tuple[str, ...] = (),
        ttl_seconds: int = 120,
        now_utc: datetime | None = None,
    ) -> tuple[ResourceLeaseRecord, ...]:
        """Acquire leases in canonical sorted order (`sorted(set(resource_uris))`)."""
        cleaned = tuple(sorted({u.strip() for u in resource_uris if u and u.strip()}))
        if not cleaned:
            raise ValidationDomainError(
                detail_override="Au moins une URI de ressource est requise pour acquérir un bail."
            )
        effective_ttl = max(1, int(ttl_seconds))
        now = now_utc or datetime.now(UTC)

        with self._lock:
            ancestors = self._resolve_ancestors_unlocked(
                holder_run_id, holder_parent_run_id, ancestor_run_ids
            )
            # Phase 1: Validate all requested URIs in canonical order before mutating state
            for uri in cleaned:
                existing = self._active_leases.get(uri)
                if existing is None:
                    continue
                exp_dt = datetime.fromisoformat(existing.expires_at)
                if exp_dt <= now:
                    # Expired lease can be safely preempted
                    continue
                if (
                    existing.holder_run_id == holder_run_id
                    and existing.holder_step_execution_id == holder_step_execution_id
                ):
                    # Re-entrant acquisition by same run + step
                    continue
                if existing.holder_run_id in ancestors or (
                    holder_parent_run_id is not None
                    and existing.holder_run_id == holder_parent_run_id
                ):
                    raise CyclicResourceWaitDetectedError(
                        detail_override=(
                            f"Attente cyclique parent-enfant détectée sur '{uri}': "
                            f"le sous-workflow enfant '{holder_run_id}' attend le bail "
                            f"détenu par son ancêtre '{existing.holder_run_id}'."
                        )
                    )
                raise ResourceLeaseHeldByOtherRunError(
                    detail_override=(
                        f"Ressource '{uri}' déjà verrouillée par le Run '{existing.holder_run_id}' "
                        f"(fencing_token={existing.fencing_token}, expire à {existing.expires_at})."
                    )
                )

            # Phase 2: Commit leases in canonical order with monotonically increasing fencing tokens
            acquired: list[ResourceLeaseRecord] = []
            for uri in cleaned:
                existing = self._active_leases.get(uri)
                if (
                    existing is not None
                    and datetime.fromisoformat(existing.expires_at) > now
                    and existing.holder_run_id == holder_run_id
                    and existing.holder_step_execution_id == holder_step_execution_id
                ):
                    refreshed = ResourceLeaseRecord(
                        id=existing.id,
                        resource_uri=uri,
                        resource_class=existing.resource_class,
                        holder_run_id=holder_run_id,
                        holder_root_run_id=holder_root_run_id,
                        holder_parent_run_id=holder_parent_run_id,
                        holder_step_execution_id=holder_step_execution_id,
                        fencing_token=existing.fencing_token,
                        acquired_at=existing.acquired_at,
                        expires_at=(now + timedelta(seconds=effective_ttl)).isoformat(),
                    )
                    self._active_leases[uri] = refreshed
                    acquired.append(refreshed)
                    continue

                next_token = self._fencing_counters.get(uri, 0) + 1
                self._fencing_counters[uri] = next_token
                record = ResourceLeaseRecord(
                    id=new_uuid7_str(),
                    resource_uri=uri,
                    resource_class=_classify_resource_uri(uri),
                    holder_run_id=holder_run_id,
                    holder_root_run_id=holder_root_run_id,
                    holder_parent_run_id=holder_parent_run_id,
                    holder_step_execution_id=holder_step_execution_id,
                    fencing_token=next_token,
                    acquired_at=now.isoformat(),
                    expires_at=(now + timedelta(seconds=effective_ttl)).isoformat(),
                )
                self._active_leases[uri] = record
                acquired.append(record)

            return tuple(acquired)

    def validate_fencing_token(self, *, resource_uri: str, fencing_token: int) -> None:
        """Verify that `fencing_token` is not stale compared to the latest issued token."""
        norm_uri = resource_uri.strip()
        with self._lock:
            highest = self._fencing_counters.get(norm_uri, 0)
            if fencing_token < highest or fencing_token <= 0:
                raise StaleFencingTokenError(
                    detail_override=(
                        f"Jeton de fencing périmé pour '{norm_uri}': jeton reçu={fencing_token} "
                        f"< jeton actif={highest}."
                    )
                )

    def execute_fenced_write(
        self,
        *,
        resource_uri: str,
        fencing_token: int,
        payload: dict[str, Any],
    ) -> dict[str, Any]:
        """Validate `fencing_token` and return a fenced write envelope for connector invocation."""
        self.validate_fencing_token(resource_uri=resource_uri, fencing_token=fencing_token)
        return {
            "resource_uri": resource_uri.strip(),
            "fencing_token": fencing_token,
            "resource_class": _classify_resource_uri(resource_uri),
            "status": "COMMITTED_FENCED",
            "payload": dict(payload),
        }

    def release_leases(self, *, holder_run_id: str, holder_step_execution_id: str) -> int:
        """Release all active leases held by `(holder_run_id, holder_step_execution_id)`."""
        with self._lock:
            to_delete = [
                uri
                for uri, lease in self._active_leases.items()
                if lease.holder_run_id == holder_run_id
                and lease.holder_step_execution_id == holder_step_execution_id
            ]
            for uri in to_delete:
                self._active_leases.pop(uri, None)
            return len(to_delete)

    def list_active_leases(
        self, *, now_utc: datetime | None = None
    ) -> tuple[ResourceLeaseRecord, ...]:
        """Return all non-expired active leases sorted by `resource_uri`."""
        now = now_utc or datetime.now(UTC)
        with self._lock:
            return tuple(
                lease
                for _uri, lease in sorted(self._active_leases.items())
                if datetime.fromisoformat(lease.expires_at) > now
            )


__all__ = [
    "ResourceLeasePort",
    "ResourceLeaseRecord",
    "ResourceLeaseService",
]
