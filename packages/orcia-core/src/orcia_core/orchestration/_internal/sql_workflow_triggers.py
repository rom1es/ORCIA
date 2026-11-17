"""PostgreSQL 18 repository for `workflow_triggers`, deliveries & Outbox (`Story 7.2`)."""

from __future__ import annotations

import hashlib
import uuid

import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncConnection, AsyncEngine

from orcia_core.orchestration._internal._sql_workflow_triggers_queries import (
    SELECT_TRIGGER_COLS,
    WorkflowTriggerRepositoryPort,
    insert_outbox_and_audit,
    row_to_trigger,
)
from orcia_core.orchestration.models import (
    WorkflowTriggerEntity,
    WorkflowTriggerStatus,
    WorkflowTriggerType,
)
from orcia_core.permissions.errors import TriggerDuplicateKeyError, TriggerNotFoundError
from orcia_core.ports.finops_telemetry import AuditLedgerSinkPort
from orcia_kernel.events import DomainEvent
from orcia_kernel.ids import new_uuid7_str


class SqlWorkflowTriggerRepository(WorkflowTriggerRepositoryPort):
    """PostgreSQL 18 repository implementing `WorkflowTriggerRepositoryPort` (`AD-18`)."""

    def __init__(
        self, *, engine: AsyncEngine, audit_ledger_sink: AuditLedgerSinkPort | None = None
    ) -> None:
        self._engine = engine
        self._audit_sink = audit_ledger_sink

    @staticmethod
    async def _ensure_workflow_def(
        conn: AsyncConnection, *, workspace_id: str, workflow_id: str
    ) -> str:
        wf_uri = workflow_id if "://" in workflow_id else f"orcia://workflows/{workflow_id}"
        wf_def_uuid = str(uuid.uuid5(uuid.NAMESPACE_URL, wf_uri))
        wf_sha256 = hashlib.sha256(wf_uri.encode()).hexdigest()
        row = (
            await conn.execute(
                sa.text(
                    """
                    INSERT INTO workflow_definitions (
                        id, workspace_id, uri, version, source_format,
                        steps_schema_jsonb, adaptive_gate_policy, sha256
                    ) VALUES (
                        CAST(:id AS uuid), CAST(:workspace_id AS uuid), :uri,
                        '1.0.0', 'ORCIA', '{}'::jsonb, 'STANDARD', :sha256
                    )
                    ON CONFLICT (uri) DO UPDATE SET uri = EXCLUDED.uri
                    RETURNING id::text
                    """
                ),
                {
                    "id": wf_def_uuid,
                    "workspace_id": workspace_id,
                    "uri": wf_uri,
                    "sha256": wf_sha256,
                },
            )
        ).fetchone()
        assert row is not None
        return str(row[0])

    async def list_triggers(
        self, *, workspace_id: str, workflow_id: str | None = None
    ) -> list[WorkflowTriggerEntity]:
        async with self._engine.connect() as conn:
            sql = (
                f"SELECT {SELECT_TRIGGER_COLS} FROM workflow_triggers "
                "WHERE workspace_id = CAST(:ws AS uuid)"
                + (" AND workflow_id = :wf" if workflow_id is not None else "")
                + " ORDER BY created_at DESC"
            )
            params: dict[str, object] = {"ws": workspace_id}
            if workflow_id is not None:
                params["wf"] = workflow_id
            rows = (await conn.execute(sa.text(sql), params)).fetchall()
            return [row_to_trigger(r)[0] for r in rows]

    async def list_active_triggers(
        self, *, trigger_type: WorkflowTriggerType | None = None
    ) -> list[WorkflowTriggerEntity]:
        async with self._engine.connect() as conn:
            sql = f"SELECT {SELECT_TRIGGER_COLS} FROM workflow_triggers WHERE status = 'ACTIVE'" + (
                " AND trigger_type = :ttype" if trigger_type is not None else ""
            )
            params: dict[str, object] = {"ttype": trigger_type} if trigger_type else {}
            rows = (await conn.execute(sa.text(sql), params)).fetchall()
            return [row_to_trigger(r)[0] for r in rows]

    async def get_trigger(self, trigger_id: str) -> tuple[WorkflowTriggerEntity, str | None] | None:
        async with self._engine.connect() as conn:
            row = (
                await conn.execute(
                    sa.text(
                        f"SELECT {SELECT_TRIGGER_COLS} FROM workflow_triggers "
                        "WHERE id = CAST(:id AS uuid)"
                    ),
                    {"id": trigger_id},
                )
            ).fetchone()
            return row_to_trigger(row) if row is not None else None

    async def save_trigger(
        self,
        trigger: WorkflowTriggerEntity,
        *,
        encrypted_secret: str | None = None,
        clear_secret: bool = False,
    ) -> WorkflowTriggerEntity:
        async with self._engine.begin() as conn:
            wf_def_id = await self._ensure_workflow_def(
                conn, workspace_id=trigger.workspace_id, workflow_id=trigger.workflow_id
            )
            dup = (
                await conn.execute(
                    sa.text(
                        "SELECT id::text FROM workflow_triggers "
                        "WHERE trigger_key = :tk AND id <> CAST(:tid AS uuid)"
                    ),
                    {"tk": trigger.trigger_key, "tid": trigger.id},
                )
            ).fetchone()
            if dup is not None:
                raise TriggerDuplicateKeyError()
            sec_sql = ""
            if clear_secret:
                sec_sql = (
                    ", webhook_secret_encrypted = NULL, webhook_secret_fingerprint = NULL"
                    ", webhook_secret_masked_hint = NULL, webhook_secret_updated_at = NOW()"
                    ", webhook_secret_updated_by = :secret_by"
                )
            elif encrypted_secret is not None:
                sec_sql = (
                    ", webhook_secret_encrypted = :enc_secret"
                    ", webhook_secret_fingerprint = :secret_fp"
                    ", webhook_secret_masked_hint = :secret_hint"
                    ", webhook_secret_updated_at = NOW(), webhook_secret_updated_by = :secret_by"
                )
            row = (
                await conn.execute(
                    sa.text(
                        f"""
                        INSERT INTO workflow_triggers (
                            id, trigger_key, workspace_id, workflow_def_id, trigger_type,
                            workflow_id, contract_id, cron_expr, webhook_secret_vault_ref,
                            cooldown_window_seconds, service_principal_id, max_runs_per_hour,
                            max_daily_cost_usd, max_consecutive_failures, post_hoc_sampling_rate,
                            contract_signature_id, status, auto_help_on_publish,
                            consecutive_failures, webhook_secret_encrypted,
                            webhook_secret_fingerprint, webhook_secret_masked_hint,
                            webhook_secret_updated_at, webhook_secret_updated_by,
                            log_sink_service, log_sink_query_text, outbox_event_filter, updated_at
                        ) VALUES (
                            CAST(:id AS uuid), :trigger_key, CAST(:workspace_id AS uuid),
                            CAST(:wf_def_id AS uuid), :trigger_type, :workflow_id,
                            CAST(:contract_id AS uuid), :cron_expr, :vault_ref,
                            :cooldown_s, :sp_id, :max_rph, :max_cost, :max_fail, :sampling,
                            CAST(:contract_sig_id AS uuid), :status, :auto_help, :consec_fail,
                            :enc_secret, :secret_fp, :secret_hint,
                            CASE
                                WHEN CAST(:enc_secret AS text) IS NOT NULL THEN NOW()
                                ELSE NULL
                            END,
                            :secret_by, :log_svc, :log_q, :outbox_flt, NOW()
                        )
                        ON CONFLICT (id) DO UPDATE SET
                            trigger_type = EXCLUDED.trigger_type,
                            contract_id = EXCLUDED.contract_id,
                            cron_expr = EXCLUDED.cron_expr,
                            cooldown_window_seconds = EXCLUDED.cooldown_window_seconds,
                            service_principal_id = EXCLUDED.service_principal_id,
                            max_runs_per_hour = EXCLUDED.max_runs_per_hour,
                            max_daily_cost_usd = EXCLUDED.max_daily_cost_usd,
                            max_consecutive_failures = EXCLUDED.max_consecutive_failures,
                            status = EXCLUDED.status,
                            auto_help_on_publish = EXCLUDED.auto_help_on_publish,
                            log_sink_service = EXCLUDED.log_sink_service,
                            log_sink_query_text = EXCLUDED.log_sink_query_text,
                            outbox_event_filter = EXCLUDED.outbox_event_filter,
                            updated_at = NOW() {sec_sql}
                        RETURNING {SELECT_TRIGGER_COLS}
                        """
                    ),
                    {
                        "id": trigger.id,
                        "trigger_key": trigger.trigger_key,
                        "workspace_id": trigger.workspace_id,
                        "wf_def_id": wf_def_id,
                        "trigger_type": trigger.trigger_type,
                        "workflow_id": trigger.workflow_id,
                        "contract_id": trigger.contract_id,
                        "cron_expr": trigger.cron_expr,
                        "vault_ref": trigger.webhook_secret_vault_ref,
                        "cooldown_s": trigger.cooldown_window_seconds,
                        "sp_id": trigger.service_principal_id,
                        "max_rph": trigger.max_runs_per_hour,
                        "max_cost": trigger.max_daily_cost_usd,
                        "max_fail": trigger.max_consecutive_failures,
                        "sampling": trigger.post_hoc_sampling_rate,
                        "contract_sig_id": trigger.contract_signature_id,
                        "status": trigger.status,
                        "auto_help": trigger.auto_help_on_publish,
                        "consec_fail": trigger.consecutive_failures,
                        "enc_secret": encrypted_secret,
                        "secret_fp": trigger.webhook_secret_fingerprint,
                        "secret_hint": trigger.webhook_secret_masked_hint,
                        "secret_by": trigger.webhook_secret_updated_by,
                        "log_svc": trigger.log_sink_service,
                        "log_q": trigger.log_sink_query_text,
                        "outbox_flt": trigger.outbox_event_filter,
                    },
                )
            ).fetchone()
            assert row is not None
            return row_to_trigger(row)[0]

    async def delete_trigger(self, *, workspace_id: str, trigger_id: str) -> None:
        async with self._engine.begin() as conn:
            res = (
                await conn.execute(
                    sa.text(
                        "DELETE FROM workflow_triggers WHERE id = CAST(:id AS uuid) "
                        "AND workspace_id = CAST(:ws AS uuid) RETURNING id::text"
                    ),
                    {"id": trigger_id, "ws": workspace_id},
                )
            ).fetchone()
            if res is None:
                raise TriggerNotFoundError()

    async def record_webhook_delivery(self, *, trigger_id: str, delivery_key: str) -> bool:
        async with self._engine.begin() as conn:
            row = (
                await conn.execute(
                    sa.text(
                        "INSERT INTO trigger_webhook_deliveries (id, trigger_id, delivery_key) "
                        "VALUES (CAST(:id AS uuid), CAST(:tid AS uuid), :dkey) "
                        "ON CONFLICT (trigger_id, delivery_key) DO NOTHING RETURNING id::text"
                    ),
                    {"id": new_uuid7_str(), "tid": trigger_id, "dkey": delivery_key},
                )
            ).fetchone()
            return row is not None

    async def count_runs_last_hour(self, *, trigger_id: str) -> int:
        async with self._engine.connect() as conn:
            cnt = (
                await conn.execute(
                    sa.text(
                        "SELECT COUNT(*) FROM workflow_runs WHERE trigger_id = CAST(:tid AS uuid) "
                        "AND created_at >= NOW() - INTERVAL '1 hour'"
                    ),
                    {"tid": trigger_id},
                )
            ).scalar()
            return int(cnt or 0)

    async def sum_daily_cost_usd(self, *, trigger_id: str) -> float:
        async with self._engine.connect() as conn:
            total = (
                await conn.execute(
                    sa.text(
                        "SELECT COALESCE(SUM(budget_max_usd), 0) FROM workflow_runs "
                        "WHERE trigger_id = CAST(:tid AS uuid) "
                        "AND created_at >= date_trunc('day', NOW())"
                    ),
                    {"tid": trigger_id},
                )
            ).scalar()
            return float(total or 0.0)

    async def create_idempotent_trigger_run(
        self,
        *,
        run_id: str,
        trigger: WorkflowTriggerEntity,
        idempotency_key: str,
        status: str,
        budget_max_usd: float,
    ) -> bool:
        async with self._engine.begin() as conn:
            wf_def_id = await self._ensure_workflow_def(
                conn, workspace_id=trigger.workspace_id, workflow_id=trigger.workflow_id
            )
            row = (
                await conn.execute(
                    sa.text(
                        """
                        INSERT INTO workflow_runs (
                            id, run_key, workspace_id, workflow_def_id, root_run_id,
                            nesting_depth, execution_regime, criticality,
                            trigger_id, trigger_idempotency_key, status,
                            execution_identity_mode, budget_max_usd
                        ) VALUES (
                            CAST(:id AS uuid), :run_key, CAST(:ws_id AS uuid),
                            CAST(:wf_def_id AS uuid), CAST(:id AS uuid),
                            0, 'AUTONOMOUS_CONTRACT', 'STANDARD',
                            CAST(:trigger_id AS uuid), :idem_key, :status,
                            'service_principal', :budget
                        )
                        ON CONFLICT (trigger_id, trigger_idempotency_key) DO NOTHING
                        RETURNING id::text
                        """
                    ),
                    {
                        "id": run_id,
                        "run_key": f"trig-{run_id}"[:128],
                        "ws_id": trigger.workspace_id,
                        "wf_def_id": wf_def_id,
                        "trigger_id": trigger.id,
                        "idem_key": idempotency_key[:255],
                        "status": status,
                        "budget": budget_max_usd,
                    },
                )
            ).fetchone()
            return row is not None

    async def mark_trigger_fired(self, *, trigger_id: str) -> WorkflowTriggerEntity | None:
        async with self._engine.begin() as conn:
            row = (
                await conn.execute(
                    sa.text(
                        f"UPDATE workflow_triggers SET consecutive_failures = 0, "
                        f"last_fired_at = NOW(), updated_at = NOW() "
                        f"WHERE id = CAST(:id AS uuid) RETURNING {SELECT_TRIGGER_COLS}"
                    ),
                    {"id": trigger_id},
                )
            ).fetchone()
            return row_to_trigger(row)[0] if row is not None else None

    async def record_trigger_failure(
        self, *, trigger_id: str, max_consecutive_failures: int
    ) -> tuple[int, bool]:
        async with self._engine.begin() as conn:
            row = (
                await conn.execute(
                    sa.text(
                        "UPDATE workflow_triggers SET "
                        "consecutive_failures = consecutive_failures + 1, "
                        "status = CASE WHEN consecutive_failures + 1 >= :mf THEN 'CIRCUIT_OPEN' "
                        "ELSE status END, updated_at = NOW() WHERE id = CAST(:id AS uuid) "
                        "RETURNING consecutive_failures, status"
                    ),
                    {"id": trigger_id, "mf": max(1, max_consecutive_failures)},
                )
            ).fetchone()
            return (int(row[0]), str(row[1]) == "CIRCUIT_OPEN") if row is not None else (0, False)

    async def set_trigger_status(
        self,
        *,
        trigger_id: str,
        status: WorkflowTriggerStatus,
        consecutive_failures: int | None = None,
    ) -> WorkflowTriggerEntity:
        async with self._engine.begin() as conn:
            row = (
                await conn.execute(
                    sa.text(
                        f"UPDATE workflow_triggers SET status = :st, "
                        f"consecutive_failures = COALESCE(:cf, consecutive_failures), "
                        f"updated_at = NOW() WHERE id = CAST(:id AS uuid) "
                        f"RETURNING {SELECT_TRIGGER_COLS}"
                    ),
                    {"id": trigger_id, "st": status, "cf": consecutive_failures},
                )
            ).fetchone()
            if row is None:
                raise TriggerNotFoundError()
            return row_to_trigger(row)[0]

    async def publish_outbox_event(self, event: DomainEvent) -> None:
        async with self._engine.begin() as conn:
            await insert_outbox_and_audit(conn, event, self._audit_sink)


__all__ = ["SqlWorkflowTriggerRepository", "WorkflowTriggerRepositoryPort"]
