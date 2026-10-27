"""Maintenance script `06_backfill_workflow_orchestration_and_locks.py` for Story 3.1.

Conventions (AGENTS.md):
- Operational data transformations or backfills outside schema migrations live in
  `infra/scripts/maintenance/XX_*.py`.
- Mandatory `--dry-run` mode (default rollback unless `--apply` is explicitly passed).
- Uses batched idempotent transactions (`INSERT ... ON CONFLICT DO UPDATE`).
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from dataclasses import dataclass
from pathlib import Path

import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine

_CORE_SRC = str(Path(__file__).resolve().parents[3] / "packages" / "orcia-core" / "src")
if _CORE_SRC not in sys.path:
    sys.path.insert(0, _CORE_SRC)

from orcia_core.orchestration import build_default_orchestration_setup_service  # noqa: E402


@dataclass(frozen=True, slots=True)
class OrchestrationSetupBackfillReport:
    """Summary of the Story 3.1 Workflow-as-Code, Triggers, Runs & `run-lock.json` backfill."""

    workflows_count: int
    triggers_count: int
    runs_count: int
    run_locks_count: int
    dry_run: bool
    committed: bool


async def backfill_workflow_orchestration_and_locks(
    engine: AsyncEngine,
    *,
    apply_changes: bool = False,
    batch_size: int = 100,
) -> OrchestrationSetupBackfillReport:
    """Populate or update Story 3.1 tables inside a controlled transaction.

    Rolls back by default unless `apply_changes=True` is explicitly provided.
    """
    if batch_size <= 0:
        raise ValueError("batch_size must be strictly positive")

    svc = build_default_orchestration_setup_service()
    workflows = svc.workflows
    runs = svc.runs

    ws_id = "0192c4e0-0000-7000-8000-000000000201"
    user_id = "0192c4e0-0000-7000-8000-000000000603"
    trigger_id = "0192c4e0-0000-7000-8000-000000000801"

    wf_upsert_sql = sa.text(
        "INSERT INTO workflow_definitions ("
        "id, workspace_id, uri, version, source_format, steps_schema_jsonb, "
        "adaptive_gate_policy, sha256, criticality, execution_regime, tie_break_policy, "
        "workflow_mode"
        ") VALUES ("
        ":id, :workspace_id, :uri, :version, 'ORCIA', CAST(:steps_schema_jsonb AS jsonb), "
        ":adaptive_gate_policy, :sha256, :criticality, :execution_regime, :tie_break_policy, "
        ":workflow_mode"
        ") ON CONFLICT (uri) DO UPDATE SET "
        "version = EXCLUDED.version, "
        "sha256 = EXCLUDED.sha256, "
        "criticality = EXCLUDED.criticality, "
        "execution_regime = EXCLUDED.execution_regime, "
        "tie_break_policy = EXCLUDED.tie_break_policy, "
        "workflow_mode = EXCLUDED.workflow_mode;"
    )

    trigger_upsert_sql = sa.text(
        "INSERT INTO workflow_triggers ("
        "id, trigger_key, workspace_id, workflow_def_id, trigger_type, cron_expr, "
        "cooldown_window_seconds, service_principal_id, max_runs_per_hour, max_daily_cost_usd, "
        "max_consecutive_failures, post_hoc_sampling_rate, status"
        ") VALUES ("
        ":id, :trigger_key, :workspace_id, :workflow_def_id, 'CRON', '0 6 * * 1-5', "
        "300, 'sp-claims-finops-reporter', 4, 15.000000, 3, 0.1000, 'ACTIVE'"
        ") ON CONFLICT (trigger_key) DO UPDATE SET status = EXCLUDED.status;"
    )

    run_upsert_sql = sa.text(
        "INSERT INTO workflow_runs ("
        "id, run_key, workspace_id, workflow_def_id, parent_run_id, parent_step_execution_id, "
        "root_run_id, nesting_depth, execution_regime, criticality, trigger_id, "
        "trigger_idempotency_key, status, initiated_by_user_id, execution_identity_mode, "
        "budget_max_usd"
        ") VALUES ("
        ":id, :run_key, :workspace_id, :workflow_def_id, :parent_run_id, "
        ":parent_step_execution_id, :root_run_id, :nesting_depth, :execution_regime, "
        ":criticality, :trigger_id, :trigger_idempotency_key, :status, "
        ":initiated_by_user_id, :execution_identity_mode, "
        ":budget_max_usd"
        ") ON CONFLICT (run_key) DO UPDATE SET status = EXCLUDED.status;"
    )

    lock_upsert_sql = sa.text(
        "INSERT INTO run_lock_manifests ("
        "run_id, manifest_jsonb, overrides_sha256, kb_snapshot_hash, manifest_sha256"
        ") VALUES ("
        ":run_id, CAST(:manifest_jsonb AS jsonb), :overrides_sha256, :kb_snapshot_hash, "
        ":manifest_sha256"
        ") ON CONFLICT (run_id) DO UPDATE SET manifest_sha256 = EXCLUDED.manifest_sha256;"
    )

    async with engine.connect() as conn:
        trans = await conn.begin()
        try:
            wf_id_by_uri: dict[str, str] = {}
            for wf in workflows:
                await conn.execute(
                    wf_upsert_sql,
                    {
                        "id": wf.id,
                        "workspace_id": ws_id,
                        "uri": wf.uri,
                        "version": wf.version,
                        "steps_schema_jsonb": json.dumps(
                            [{"step_key": s.step_key, "step_type": s.step_type} for s in wf.steps]
                        ),
                        "adaptive_gate_policy": wf.adaptive_gate_policy,
                        "sha256": wf.sha256,
                        "criticality": wf.criticality,
                        "execution_regime": wf.execution_regime,
                        "tie_break_policy": wf.tie_break_policy,
                        "workflow_mode": wf.mode,
                    },
                )
                row_id = (
                    await conn.execute(
                        sa.text("SELECT id FROM workflow_definitions WHERE uri = :uri"),
                        {"uri": wf.uri},
                    )
                ).scalar()
                wf_id_by_uri[wf.uri] = str(row_id or wf.id)

            leaf_wf_id = wf_id_by_uri["orcia://workflows/sub-verify-regression-suite"]
            await conn.execute(
                trigger_upsert_sql,
                {
                    "id": trigger_id,
                    "trigger_key": "trg-cron-daily-regression-suite",
                    "workspace_id": ws_id,
                    "workflow_def_id": leaf_wf_id,
                },
            )

            for r in runs:
                db_wf_id = wf_id_by_uri.get(r.workflow_uri, r.workflow_def_id)
                await conn.execute(
                    run_upsert_sql,
                    {
                        "id": r.id,
                        "run_key": r.run_key,
                        "workspace_id": ws_id,
                        "workflow_def_id": db_wf_id,
                        "parent_run_id": r.parent_run_id,
                        "parent_step_execution_id": r.parent_step_execution_id,
                        "root_run_id": r.root_run_id,
                        "nesting_depth": r.nesting_depth,
                        "execution_regime": r.execution_regime,
                        "criticality": r.criticality,
                        "trigger_id": trigger_id,
                        "trigger_idempotency_key": f"idem-{r.run_key}",
                        "status": r.status,
                        "initiated_by_user_id": user_id,
                        "execution_identity_mode": r.execution_identity_mode,
                        "budget_max_usd": r.budget_max_usd,
                    },
                )
                await conn.execute(
                    lock_upsert_sql,
                    {
                        "run_id": r.id,
                        "manifest_jsonb": r.run_lock.to_json(),
                        "overrides_sha256": r.run_lock.overrides_sha256,
                        "kb_snapshot_hash": r.run_lock.kb_snapshot_hash,
                        "manifest_sha256": r.run_lock.manifest_sha256,
                    },
                )

            t_cnt = int(
                (await conn.execute(sa.text("SELECT COUNT(*) FROM workflow_triggers"))).scalar()
                or 0
            )
            r_cnt = int(
                (await conn.execute(sa.text("SELECT COUNT(*) FROM workflow_runs"))).scalar() or 0
            )
            l_cnt = int(
                (await conn.execute(sa.text("SELECT COUNT(*) FROM run_lock_manifests"))).scalar()
                or 0
            )

            if apply_changes:
                await trans.commit()
                committed = True
            else:
                await trans.rollback()
                committed = False

            return OrchestrationSetupBackfillReport(
                workflows_count=len(workflows),
                triggers_count=t_cnt,
                runs_count=r_cnt,
                run_locks_count=l_cnt,
                dry_run=not apply_changes,
                committed=committed,
            )
        except Exception:
            await trans.rollback()
            raise


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Backfill Story 3.1 Workflow-as-Code, Triggers, Runs & run-lock.json tables."
    )
    mode_group = parser.add_mutually_exclusive_group()
    mode_group.add_argument("--dry-run", action="store_true", default=True)
    mode_group.add_argument("--apply", action="store_true", default=False)
    parser.add_argument("--batch-size", type=int, default=100)
    return parser


async def _async_main(argv: list[str] | None = None) -> int:
    from orcia_core.config import resolve_database_url

    args = build_arg_parser().parse_args(argv)
    engine = create_async_engine(resolve_database_url())
    try:
        report = await backfill_workflow_orchestration_and_locks(
            engine, apply_changes=bool(args.apply), batch_size=int(args.batch_size)
        )
    finally:
        await engine.dispose()
    return 0 if report.runs_count >= 1 and report.run_locks_count >= 1 else 1


def main(argv: list[str] | None = None) -> int:
    return asyncio.run(_async_main(argv))


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
