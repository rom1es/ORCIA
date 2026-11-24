"""Shared Resource Lease Port & Monotonic Fencing Service (`DEC-CONC-01`, `AD-4`, `Story 5.1`)."""

from __future__ import annotations

import threading
from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING, Any

from orcia_core.orchestration._internal.sql_resource_leases import SqlResourceLeaseRepository
from orcia_core.orchestration._resource_leases_helpers import (
    check_lease_conflicts_unlocked,
    classify_resource_uri,
    resolve_ancestors_unlocked,
)
from orcia_core.orchestration.errors import (
    StaleFencingTokenError,
    ValidationDomainError,
)
from orcia_kernel.ids import new_uuid7_str
from orcia_kernel.ports import ResourceLeasePort, ResourceLeaseRecord

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncEngine


def _classify_resource_uri(resource_uri: str) -> str:
    return classify_resource_uri(resource_uri)


class ResourceLeaseService(ResourceLeasePort):
    """Concurrent-ready shared resource lease manager with monotonic fencing & deadlock guard."""

    def __init__(self, *, engine: AsyncEngine | None = None) -> None:
        self._engine: AsyncEngine | None = engine
        self._sql_repo: SqlResourceLeaseRepository | None = (
            SqlResourceLeaseRepository(engine) if engine is not None else None
        )
        self._lock = threading.Lock()
        self._active_leases: dict[str, ResourceLeaseRecord] = {}
        self._fencing_counters: dict[str, int] = {}
        self._run_parent_map: dict[str, str] = {}

    def set_engine(self, engine: AsyncEngine | None) -> None:
        """Bind or refresh the SQLAlchemy `AsyncEngine` from the Composition Root."""
        self._engine = engine
        self._sql_repo = SqlResourceLeaseRepository(engine) if engine is not None else None

    async def _pg_ready(self) -> bool:
        return self._sql_repo is not None and await self._sql_repo.pg_tables_ready()

    def register_run_parent(self, child_run_id: str, parent_run_id: str) -> None:
        """Record parent-child `SUB_WORKFLOW` relationship for cyclic wait detection."""
        with self._lock:
            self._run_parent_map[child_run_id] = parent_run_id

    def _resolve_ancestors_unlocked(
        self, holder_run_id: str, holder_parent_run_id: str | None, explicit: tuple[str, ...]
    ) -> set[str]:
        return resolve_ancestors_unlocked(
            self._run_parent_map, holder_run_id, holder_parent_run_id, explicit
        )

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
            raise ValidationDomainError(detail_code="ERR_RESOURCE_LEASE_URIS_REQUIRED")
        effective_ttl = max(1, int(ttl_seconds))
        now = now_utc or datetime.now(UTC)

        with self._lock:
            ancestors = self._resolve_ancestors_unlocked(
                holder_run_id, holder_parent_run_id, ancestor_run_ids
            )
            check_lease_conflicts_unlocked(
                self._active_leases,
                cleaned_uris=cleaned,
                holder_run_id=holder_run_id,
                holder_step_execution_id=holder_step_execution_id,
                holder_parent_run_id=holder_parent_run_id,
                ancestors=ancestors,
                now=now,
            )

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

    async def acquire_leases_async(
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
        """Acquire leases and persist them into PG18 `resource_leases`."""
        pg_ready = await self._pg_ready()
        if pg_ready:
            assert self._sql_repo is not None
            for uri in sorted({u.strip() for u in resource_uris if u and u.strip()}):
                db_lease = await self._sql_repo.get_lease(uri)
                if db_lease is not None:
                    with self._lock:
                        self._active_leases[uri] = db_lease
                        self._fencing_counters[uri] = max(
                            self._fencing_counters.get(uri, 0), db_lease.fencing_token
                        )
        records = self.acquire_leases(
            resource_uris=resource_uris,
            holder_run_id=holder_run_id,
            holder_root_run_id=holder_root_run_id,
            holder_step_execution_id=holder_step_execution_id,
            holder_parent_run_id=holder_parent_run_id,
            ancestor_run_ids=ancestor_run_ids,
            ttl_seconds=ttl_seconds,
            now_utc=now_utc,
        )
        if pg_ready:
            assert self._sql_repo is not None
            await self._sql_repo.upsert_leases(records)
        return records

    def validate_fencing_token(self, *, resource_uri: str, fencing_token: int) -> None:
        """Verify that `fencing_token` is not stale compared to the latest issued token."""
        norm_uri = resource_uri.strip()
        with self._lock:
            highest = self._fencing_counters.get(norm_uri, 0)
            if fencing_token < highest or fencing_token <= 0:
                raise StaleFencingTokenError(
                    detail_code="ERR_STALE_FENCING_TOKEN",
                    detail_params={
                        "uri": norm_uri,
                        "received": fencing_token,
                        "highest": highest,
                    },
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

    async def execute_fenced_resource_write_async(
        self,
        *,
        resource_uri: str,
        fencing_token: int,
        payload: dict[str, Any],
    ) -> dict[str, Any]:
        """Validate fencing token against PG18 `resource_leases` and return envelope."""
        if await self._pg_ready():
            assert self._sql_repo is not None
            db_lease = await self._sql_repo.get_lease(resource_uri)
            if db_lease is not None:
                with self._lock:
                    self._fencing_counters[resource_uri.strip()] = max(
                        self._fencing_counters.get(resource_uri.strip(), 0),
                        db_lease.fencing_token,
                    )
        return self.execute_fenced_write(
            resource_uri=resource_uri, fencing_token=fencing_token, payload=payload
        )

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

    async def release_leases_async(
        self, *, holder_run_id: str, holder_step_execution_id: str
    ) -> int:
        """Release active leases in memory and in PG18 `resource_leases`."""
        cnt = self.release_leases(
            holder_run_id=holder_run_id, holder_step_execution_id=holder_step_execution_id
        )
        if await self._pg_ready():
            assert self._sql_repo is not None
            pg_cnt = await self._sql_repo.release_leases(
                holder_run_id=holder_run_id, holder_step_execution_id=holder_step_execution_id
            )
            return max(cnt, pg_cnt)
        return cnt

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

    async def list_active_leases_async(
        self, *, now_utc: datetime | None = None
    ) -> tuple[ResourceLeaseRecord, ...]:
        """Return all non-expired active leases from PG18."""
        now = now_utc or datetime.now(UTC)
        if await self._pg_ready():
            assert self._sql_repo is not None
            return await self._sql_repo.list_active_leases(now_utc=now)
        return self.list_active_leases(now_utc=now)


__all__ = [
    "ResourceLeasePort",
    "ResourceLeaseRecord",
    "ResourceLeaseService",
]
