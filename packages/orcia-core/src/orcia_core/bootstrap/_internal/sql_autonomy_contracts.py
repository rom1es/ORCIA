"""PostgreSQL 18 repository for `autonomy_contracts`, Outbox events & `audit_ledger` (`Story 7.1`).

Pure asynchronous SQL repository — zero application ORM imports, zero N+1 queries.
"""

from __future__ import annotations

import hashlib
import json
import uuid
from datetime import datetime
from typing import Any, cast

import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncConnection, AsyncEngine

from orcia_core.audit_finops.outbox_subscriber import map_domain_event_to_ledger_entry
from orcia_core.permissions.autonomy_contracts import (
    AutonomyContract,
    AutonomyContractRepositoryPort,
    AutonomyContractStatus,
    AutonomySignerRole,
    ContractCriticality,
)
from orcia_core.permissions.errors import AutonomyContractNotFoundError
from orcia_core.ports.finops_telemetry import AuditLedgerSinkPort
from orcia_kernel.enums import TieBreakPolicy
from orcia_kernel.events import DomainEvent


def _fmt_ts(val: object) -> str:
    if isinstance(val, datetime):
        return val.isoformat().replace("+00:00", "Z")
    return str(val or "")


def _parse_str_list(raw: object) -> tuple[str, ...]:
    if isinstance(raw, list):
        return tuple(str(x).strip() for x in raw if str(x).strip())
    if isinstance(raw, str):
        try:
            decoded = json.loads(raw)
        except ValueError:
            return ()
        if isinstance(decoded, list):
            return tuple(str(x).strip() for x in decoded if str(x).strip())
    return ()


def _row_to_contract(row: Any) -> AutonomyContract:
    return AutonomyContract(
        id=str(row[0]),
        workspace_id=str(row[1]),
        workflow_id=str(row[2]),
        workflow_version=str(row[3]),
        workflow_sha256=str(row[4]),
        criticality=cast(ContractCriticality, str(row[5])),
        service_principal_id=str(row[6]),
        allowed_read_sources=_parse_str_list(row[7]),
        allowed_write_actions=_parse_str_list(row[8]),
        max_cost_per_run_usd=float(row[9]),
        tie_break_policy=cast(TieBreakPolicy, str(row[10])),
        post_hoc_sampling_rate=float(row[11]),
        status=cast(AutonomyContractStatus, str(row[12])),
        signed_by_user_id=str(row[13]),
        signed_by_role=cast(AutonomySignerRole, str(row[14])),
        signature_sha256=str(row[15]),
        signed_at_iso=_fmt_ts(row[16]),
        revoked_at_iso=_fmt_ts(row[17]) if row[17] is not None else None,
        revoked_by_user_id=str(row[18]) if row[18] is not None else None,
    )


_SELECT_COLUMNS = """
    id::text,
    workspace_id::text,
    workflow_id,
    workflow_version,
    workflow_sha256,
    criticality,
    service_principal_id::text,
    allowed_read_sources_jsonb,
    allowed_write_actions_jsonb,
    max_cost_per_run_usd,
    tie_break_policy,
    post_hoc_sampling_rate,
    status,
    signed_by_user_id::text,
    signed_by_role,
    signature_sha256,
    signed_at,
    revoked_at,
    revoked_by_user_id::text
"""


async def _insert_outbox_and_audit_in_conn(
    conn: AsyncConnection,
    event: DomainEvent,
    audit_sink: AuditLedgerSinkPort | None,
) -> None:
    outbox_reg = (
        await conn.execute(sa.text("SELECT to_regclass('public.domain_events_outbox')"))
    ).scalar()
    if outbox_reg is not None:
        await conn.execute(
            sa.text(
                """
                INSERT INTO domain_events_outbox (
                    event_id, event_type, aggregate_type, aggregate_id,
                    run_id, workspace_id, payload_jsonb, trace_id, status, attempts
                )
                VALUES (
                    CAST(:event_id AS uuid), :event_type, :aggregate_type, :aggregate_id,
                    CAST(:run_id AS uuid), CAST(:workspace_id AS uuid),
                    CAST(:payload_jsonb AS jsonb), :trace_id, 'PUBLISHED', 1
                )
                ON CONFLICT (event_id) DO NOTHING
                """
            ),
            {
                "event_id": event.event_id,
                "event_type": event.event_type,
                "aggregate_type": event.aggregate_type,
                "aggregate_id": event.aggregate_id,
                "run_id": event.run_id,
                "workspace_id": event.workspace_id,
                "payload_jsonb": json.dumps(event.payload, sort_keys=True),
                "trace_id": event.trace_id,
            },
        )
    if audit_sink is not None:
        ledger_reg = (
            await conn.execute(sa.text("SELECT to_regclass('public.audit_ledger')"))
        ).scalar()
        if ledger_reg is not None:
            entry = map_domain_event_to_ledger_entry(event)
            await audit_sink.record_entry(entry, conn=conn)  # type: ignore[call-arg]


class SqlAutonomyContractRepository(AutonomyContractRepositoryPort):
    """PostgreSQL 18 repository implementing `AutonomyContractRepositoryPort`."""

    def __init__(
        self,
        *,
        engine: AsyncEngine,
        audit_ledger_sink: AuditLedgerSinkPort | None = None,
    ) -> None:
        self._engine = engine
        self._audit_sink = audit_ledger_sink

    async def get_active_contract(
        self, *, workspace_id: str, workflow_id: str
    ) -> AutonomyContract | None:
        async with self._engine.connect() as conn:
            row = (
                await conn.execute(
                    sa.text(
                        f"""
                        SELECT {_SELECT_COLUMNS}
                        FROM autonomy_contracts
                        WHERE workspace_id = CAST(:workspace_id AS uuid)
                          AND workflow_id = :workflow_id
                          AND status = 'ACTIVE'
                        LIMIT 1
                        """
                    ),
                    {"workspace_id": workspace_id, "workflow_id": workflow_id},
                )
            ).fetchone()
            return _row_to_contract(row) if row is not None else None

    async def list_contracts(
        self, *, workspace_id: str, workflow_id: str
    ) -> list[AutonomyContract]:
        async with self._engine.connect() as conn:
            rows = (
                await conn.execute(
                    sa.text(
                        f"""
                        SELECT {_SELECT_COLUMNS}
                        FROM autonomy_contracts
                        WHERE workspace_id = CAST(:workspace_id AS uuid)
                          AND workflow_id = :workflow_id
                        ORDER BY signed_at DESC
                        """
                    ),
                    {"workspace_id": workspace_id, "workflow_id": workflow_id},
                )
            ).fetchall()
            return [_row_to_contract(r) for r in rows]

    async def save_signed_contract(
        self, contract: AutonomyContract, event: DomainEvent
    ) -> AutonomyContract:
        async with self._engine.begin() as conn:
            await conn.execute(
                sa.text(
                    """
                    UPDATE autonomy_contracts
                    SET status = 'SUPERSEDED'
                    WHERE workspace_id = CAST(:workspace_id AS uuid)
                      AND workflow_id = :workflow_id
                      AND status = 'ACTIVE'
                    """
                ),
                {"workspace_id": contract.workspace_id, "workflow_id": contract.workflow_id},
            )
            row = (
                await conn.execute(
                    sa.text(
                        f"""
                        INSERT INTO autonomy_contracts (
                            id, workspace_id, workflow_id, workflow_version, workflow_sha256,
                            criticality, service_principal_id, allowed_read_sources_jsonb,
                            allowed_write_actions_jsonb, max_cost_per_run_usd, tie_break_policy,
                            post_hoc_sampling_rate, status, signed_by_user_id, signed_by_role,
                            signature_sha256, signed_at
                        )
                        VALUES (
                            CAST(:id AS uuid), CAST(:workspace_id AS uuid), :workflow_id,
                            :workflow_version, :workflow_sha256, :criticality,
                            CAST(:service_principal_id AS uuid),
                            CAST(:allowed_read_sources_jsonb AS jsonb),
                            CAST(:allowed_write_actions_jsonb AS jsonb),
                            :max_cost_per_run_usd, :tie_break_policy,
                            :post_hoc_sampling_rate, 'ACTIVE',
                            CAST(:signed_by_user_id AS uuid), :signed_by_role,
                            :signature_sha256, NOW()
                        )
                        RETURNING {_SELECT_COLUMNS}
                        """
                    ),
                    {
                        "id": contract.id,
                        "workspace_id": contract.workspace_id,
                        "workflow_id": contract.workflow_id,
                        "workflow_version": contract.workflow_version,
                        "workflow_sha256": contract.workflow_sha256,
                        "criticality": contract.criticality,
                        "service_principal_id": contract.service_principal_id,
                        "allowed_read_sources_jsonb": json.dumps(
                            list(contract.allowed_read_sources)
                        ),
                        "allowed_write_actions_jsonb": json.dumps(
                            list(contract.allowed_write_actions)
                        ),
                        "max_cost_per_run_usd": contract.max_cost_per_run_usd,
                        "tie_break_policy": contract.tie_break_policy,
                        "post_hoc_sampling_rate": contract.post_hoc_sampling_rate,
                        "signed_by_user_id": contract.signed_by_user_id,
                        "signed_by_role": contract.signed_by_role,
                        "signature_sha256": contract.signature_sha256,
                    },
                )
            ).fetchone()
            await _insert_outbox_and_audit_in_conn(conn, event, self._audit_sink)
            assert row is not None
            return _row_to_contract(row)

    async def mark_contract_revoked(
        self,
        *,
        contract_id: str,
        revoked_by_user_id: str,
        revoked_at_iso: str,
        event: DomainEvent,
    ) -> AutonomyContract:
        del revoked_at_iso
        async with self._engine.begin() as conn:
            row = (
                await conn.execute(
                    sa.text(
                        f"""
                        UPDATE autonomy_contracts
                        SET status = 'REVOKED',
                            revoked_at = NOW(),
                            revoked_by_user_id = CAST(:revoked_by_user_id AS uuid)
                        WHERE id = CAST(:id AS uuid)
                          AND status = 'ACTIVE'
                        RETURNING {_SELECT_COLUMNS}
                        """
                    ),
                    {"id": contract_id, "revoked_by_user_id": revoked_by_user_id},
                )
            ).fetchone()
            if row is None:
                raise AutonomyContractNotFoundError()
            await _insert_outbox_and_audit_in_conn(conn, event, self._audit_sink)
            return _row_to_contract(row)


async def persist_autonomous_run_outcome_on_postgres18(
    engine: AsyncEngine,
    *,
    run_id: str,
    workspace_id: str,
    workflow_id: str,
    workflow_version: str,
    status: str,
    event: DomainEvent | None = None,
    audit_sink: AuditLedgerSinkPort | None = None,
) -> None:
    """Persist autonomous `workflow_runs` outcome (`COMMITTED_AUTONOMOUS`/escalation)."""
    wf_uri = workflow_id if "://" in workflow_id else f"orcia://workflows/{workflow_id}"
    wf_def_uuid = str(uuid.uuid5(uuid.NAMESPACE_URL, wf_uri))
    wf_sha256 = hashlib.sha256(f"{wf_uri}@{workflow_version}".encode()).hexdigest()
    async with engine.begin() as conn:
        wf_reg = (
            await conn.execute(sa.text("SELECT to_regclass('public.workflow_runs')"))
        ).scalar()
        if wf_reg is not None:
            resolved_wf_def_id = (
                await conn.execute(
                    sa.text(
                        """
                        INSERT INTO workflow_definitions (
                            id, workspace_id, uri, version, source_format,
                            steps_schema_jsonb, adaptive_gate_policy, sha256
                        )
                        VALUES (
                            CAST(:id AS uuid), CAST(:workspace_id AS uuid), :uri,
                            :version, 'ORCIA', '{}'::jsonb, 'STANDARD', :sha256
                        )
                        ON CONFLICT (uri) DO UPDATE SET version = EXCLUDED.version
                        RETURNING id::text
                        """
                    ),
                    {
                        "id": wf_def_uuid,
                        "workspace_id": workspace_id,
                        "uri": wf_uri,
                        "version": workflow_version[:64],
                        "sha256": wf_sha256,
                    },
                )
            ).scalar_one()
            await conn.execute(
                sa.text(
                    """
                    INSERT INTO workflow_runs (
                        id, run_key, workspace_id, workflow_def_id, root_run_id,
                        nesting_depth, execution_regime, criticality, status,
                        execution_identity_mode, budget_max_usd
                    )
                    VALUES (
                        CAST(:id AS uuid), :run_key, CAST(:workspace_id AS uuid),
                        CAST(:workflow_def_id AS uuid), CAST(:id AS uuid),
                        0, 'AUTONOMOUS_CONTRACT', 'STANDARD', :status,
                        'service_principal', 10.000000
                    )
                    ON CONFLICT (id) DO UPDATE SET
                        status = EXCLUDED.status,
                        execution_regime = 'AUTONOMOUS_CONTRACT'
                    """
                ),
                {
                    "id": run_id,
                    "run_key": f"autonomy-run-{run_id}"[:128],
                    "workspace_id": workspace_id,
                    "workflow_def_id": resolved_wf_def_id,
                    "status": status,
                },
            )
        if event is not None:
            await _insert_outbox_and_audit_in_conn(conn, event, audit_sink)
