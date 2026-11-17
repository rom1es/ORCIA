"""PostgreSQL 18 persistence for the immutable append-only audit ledger (`Story 6.1`).

Pure asynchronous SQL repository — zero application ORM imports, zero N+1 queries.
"""

from __future__ import annotations

import json
from typing import Any
from uuid import UUID

import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncConnection, AsyncEngine

from orcia_core.audit_finops._internal.sql_audit_ledger_mappers import (
    SQL_INSERT_ENTRY,
    SQL_LOOKUP_EXISTING_ID,
    SQL_PROVENANCE_ENTRIES,
    SQL_RUN_LOCK_MANIFEST_SHA,
    build_audit_ledger_where,
    parse_row_to_entry,
)
from orcia_core.audit_finops.models import (
    AuditLedgerEntry,
    AuditLedgerFilterParams,
)
from orcia_core.kernel.ids import new_uuid7_str
from orcia_core.observability.logging import get_logger
from orcia_core.ports.finops_telemetry import (
    AuditLedgerSinkPort,
    FinopsCostLedgerEntry,
)

logger = get_logger("orcia.core.audit_finops.ledger")

# Re-export for backward compatibility with unit tests
_parse_row_to_entry = parse_row_to_entry


class SqlAuditLedgerService(AuditLedgerSinkPort):
    """Hexagonal service managing PostgreSQL 18 append-only audit ledger operations."""

    def __init__(self, engine: AsyncEngine | None = None) -> None:
        self._engine = engine

    async def record_entry(
        self,
        entry: FinopsCostLedgerEntry,
        *,
        conn: AsyncConnection | None = None,
    ) -> str:
        """Insert an immutable row in audit_ledger with ON CONFLICT (source_event_id) DO NOTHING."""
        if self._engine is None and conn is None:
            return entry.id or new_uuid7_str()

        entry_id = entry.id or new_uuid7_str()

        params: dict[str, Any] = {
            "id": entry_id,
            "source_event_id": entry.source_event_id,
            "workspace_id": entry.workspace_id,
            "org_unit_id": entry.org_unit_id,
            "scope_path": entry.scope_path or "GLOBAL",
            "run_id": entry.run_id,
            "root_run_id": entry.root_run_id,
            "step_execution_id": entry.step_execution_id,
            "actor_type": entry.actor_type,
            "actor_id": entry.actor_id,
            "actor_display_name": entry.actor_display_name,
            "actor_email": entry.actor_email,
            "event_type": entry.event_type,
            "summary": entry.summary,
            "model_id": entry.model_id,
            "inference_tier": entry.inference_tier,
            "effort": entry.effort,
            "input_tokens": entry.input_tokens,
            "output_tokens": entry.output_tokens,
            "cost_usd": entry.cost_usd,
            "cost_source": entry.cost_source,
            "native_metric_type": entry.native_metric_type,
            "native_metric_value": entry.native_metric_value,
            "native_currency": entry.native_currency,
            "reported_by_remote": entry.reported_by_remote,
            "latency_ms": entry.latency_ms,
            "trace_id": entry.trace_id,
            "run_lock_sha256": entry.run_lock_sha256,
            "pre_prompt_sha256": entry.pre_prompt_sha256,
            "workflow_contract_sha256": entry.workflow_contract_sha256,
            "cas_references_jsonb": json.dumps(entry.cas_references or []),
            "metadata_jsonb": json.dumps(entry.metadata or {}),
            "created_at": entry.created_at,
        }

        async def _execute_on(c: AsyncConnection) -> str:
            res = await c.execute(SQL_INSERT_ENTRY, params)
            row = res.fetchone()
            if row is not None and row[0] is not None:
                return str(row[0])
            l_res = await c.execute(
                SQL_LOOKUP_EXISTING_ID, {"source_event_id": entry.source_event_id}
            )
            l_row = l_res.fetchone()
            return str(l_row[0]) if l_row else entry_id

        if conn is not None:
            return await _execute_on(conn)
        assert self._engine is not None
        async with self._engine.begin() as c:
            return await _execute_on(c)

    async def list_entries(
        self,
        params: AuditLedgerFilterParams,
        *,
        conn: AsyncConnection | None = None,
    ) -> tuple[list[AuditLedgerEntry], int]:
        """Fetch filtered and paginated audit ledger rows along with total count."""
        if self._engine is None and conn is None:
            return [], 0

        where_sql, sql_params = build_audit_ledger_where(params)
        limit_val = max(1, min(500, params.limit))
        offset_val = max(0, params.offset)
        sql_params["limit"] = limit_val
        sql_params["offset"] = offset_val

        count_sql = sa.text(f"SELECT COUNT(*) FROM audit_ledger WHERE {where_sql};")
        query_sql = sa.text(
            f"""
            SELECT *
            FROM audit_ledger
            WHERE {where_sql}
            ORDER BY created_at DESC
            LIMIT :limit OFFSET :offset;
            """
        )

        async def _query_on(c: AsyncConnection) -> tuple[list[AuditLedgerEntry], int]:
            c_res = await c.execute(count_sql, sql_params)
            total = int(c_res.scalar() or 0)

            q_res = await c.execute(query_sql, sql_params)
            rows = q_res.mappings().all()
            entries = [parse_row_to_entry(dict(r)) for r in rows]
            return entries, total

        if conn is not None:
            return await _query_on(conn)
        assert self._engine is not None
        async with self._engine.connect() as c:
            return await _query_on(c)

    async def get_run_provenance_entries(
        self,
        run_id: str,
        *,
        conn: AsyncConnection | None = None,
    ) -> list[AuditLedgerEntry]:
        """Fetch all audit events associated with a given run_id in chronological order."""
        if self._engine is None and conn is None:
            return []

        try:
            r_uuid = UUID(run_id.strip())
        except (ValueError, AttributeError):
            return []

        async def _query_on(c: AsyncConnection) -> list[AuditLedgerEntry]:
            res = await c.execute(SQL_PROVENANCE_ENTRIES, {"run_id": str(r_uuid)})
            rows = res.mappings().all()
            return [parse_row_to_entry(dict(r)) for r in rows]

        if conn is not None:
            return await _query_on(conn)
        assert self._engine is not None
        async with self._engine.connect() as c:
            return await _query_on(c)

    async def get_run_lock_manifest_sha(
        self,
        run_id: str,
        *,
        conn: AsyncConnection | None = None,
    ) -> str | None:
        """Fetch manifest_sha256 from run_lock_manifests for cross-verification."""
        if self._engine is None and conn is None:
            return None

        try:
            r_uuid = UUID(run_id.strip())
        except (ValueError, AttributeError):
            return None

        async def _query_on(c: AsyncConnection) -> str | None:
            res = await c.execute(SQL_RUN_LOCK_MANIFEST_SHA, {"run_id": str(r_uuid)})
            row = res.fetchone()
            return str(row[0]) if row and row[0] else None

        if conn is not None:
            return await _query_on(conn)
        assert self._engine is not None
        async with self._engine.connect() as c:
            return await _query_on(c)
