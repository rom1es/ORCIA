"""Maintenance script `07_backfill_step_executions_and_blackboard_snapshots.py` for Story 3.2.

Conventions (AGENTS.md):
- Operational data transformations or backfills outside schema migrations live in
  `infra/scripts/maintenance/XX_*.py`.
- Mandatory `--dry-run` mode (default rollback unless `--apply` is explicitly passed).
- Never disable the `BEFORE UPDATE OR DELETE RAISE EXCEPTION` trigger on `blackboard_snapshots`;
  use `ON CONFLICT (snapshot_key) DO NOTHING` on `blackboard_snapshots`.
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

from orcia_core.config import resolve_database_url  # noqa: E402
from orcia_core.orchestration import build_default_orchestration_setup_service  # noqa: E402
from orcia_core.permissions.models import UserIdentity  # noqa: E402


@dataclass(frozen=True, slots=True)
class Story32BackfillReport:
    """Summary report for Story 3.2 step executions and append-only blackboard backfill."""

    step_executions_count: int
    blackboard_snapshots_count: int
    dry_run: bool
    committed: bool


async def backfill_step_executions_and_blackboard_snapshots(
    engine: AsyncEngine,
    *,
    apply_changes: bool = False,
) -> Story32BackfillReport:
    """Backfill canonical `step_executions` and append-only `blackboard_snapshots` rows."""
    svc = build_default_orchestration_setup_service()
    lead_user = UserIdentity(
        id="0192c4e0-0000-7000-8000-000000000603",
        email="marc.lead@orcia.io",
        display_name="Marc (Chef d'Équipe / Tech Lead)",
        auth_mode="HYBRID",
        human_profile_archetype="TECH_LEAD",
        platform_role="TEAM_LEAD",
        primary_org_unit_id="0192c4e0-0000-7000-8000-000000000104",
    )

    root_run = svc.runs[0]
    svc.engine.run_background_fast_path_audit(lead_user, run_id=root_run.id)

    upsert_step_sql = sa.text(
        "INSERT INTO step_executions ("
        "id, step_execution_key, run_id, step_key, step_index, step_type, execution_mode, "
        "status, attempt_count, max_agent_retries, draft_artifact_jsonb, draft_cas_key, "
        "step_memlog_jsonb, hydrated_input_uris_jsonb, child_run_id, committed_snapshot_id, "
        "cost_usd"
        ") VALUES ("
        ":id, :step_execution_key, :run_id, :step_key, :step_index, :step_type, :execution_mode, "
        ":status, :attempt_count, :max_agent_retries, CAST(:draft_artifact_jsonb AS jsonb), "
        ":draft_cas_key, CAST(:step_memlog_jsonb AS jsonb), "
        "CAST(:hydrated_input_uris_jsonb AS jsonb), :child_run_id, :committed_snapshot_id, "
        ":cost_usd"
        ") ON CONFLICT (step_execution_key) DO UPDATE SET "
        "status = EXCLUDED.status, "
        "draft_artifact_jsonb = EXCLUDED.draft_artifact_jsonb, "
        "committed_snapshot_id = EXCLUDED.committed_snapshot_id, "
        "updated_at = NOW();"
    )

    insert_snapshot_sql = sa.text(
        "INSERT INTO blackboard_snapshots ("
        "id, snapshot_key, run_id, step_execution_id, parent_snapshot_id, step_key, "
        "branch_status, artifact_payload_jsonb, artifact_cas_key, artifact_sha256, "
        "memlog_summary_jsonb, superseded_snapshot_ids_jsonb"
        ") VALUES ("
        ":id, :snapshot_key, :run_id, :step_execution_id, :parent_snapshot_id, :step_key, "
        ":branch_status, CAST(:artifact_payload_jsonb AS jsonb), :artifact_cas_key, "
        ":artifact_sha256, CAST(:memlog_summary_jsonb AS jsonb), "
        "CAST(:superseded_snapshot_ids_jsonb AS jsonb)"
        ") ON CONFLICT (snapshot_key) DO NOTHING;"
    )

    upsert_run_sql = sa.text(
        "INSERT INTO workflow_runs ("
        "id, run_key, workspace_id, workflow_def_id, parent_run_id, parent_step_execution_id, "
        "root_run_id, nesting_depth, execution_regime, criticality, trigger_id, "
        "trigger_idempotency_key, status, initiated_by_user_id, execution_identity_mode, "
        "budget_max_usd"
        ") VALUES ("
        ":id, :run_key, :workspace_id, :workflow_def_id, :parent_run_id, "
        ":parent_step_execution_id, :root_run_id, :nesting_depth, :execution_regime, "
        ":criticality, :trigger_id, :trigger_idempotency_key, :status, "
        ":initiated_by_user_id, :execution_identity_mode, :budget_max_usd"
        ") ON CONFLICT (run_key) DO UPDATE SET status = EXCLUDED.status;"
    )

    steps_count = 0
    snaps_count = 0
    async with engine.connect() as conn:
        trans = await conn.begin()
        try:
            res = await conn.execute(sa.text("SELECT id, uri FROM workflow_definitions;"))
            db_wf_ids = {str(r[1]): str(r[0]) for r in res.fetchall()}

            existing_runs_res = await conn.execute(
                sa.text("SELECT run_key, id FROM workflow_runs;")
            )
            db_run_ids_by_key = {str(r[0]): str(r[1]) for r in existing_runs_res.fetchall()}

            run_id_map: dict[str, str] = {}
            for idx, r in enumerate(svc.runs):
                canonical_key = (
                    "run-claims-engineering-delivery-000801"
                    if idx == 0
                    else f"run-sub-{r.nesting_depth}-00080{idx + 1}"
                )
                db_run_id = db_run_ids_by_key.get(
                    canonical_key, f"0192c4e0-0000-7000-8000-00000000081{idx + 1}"
                )
                run_id_map[r.id] = db_run_id

            for idx, r in enumerate(svc.runs):
                canonical_key = (
                    "run-claims-engineering-delivery-000801"
                    if idx == 0
                    else f"run-sub-{r.nesting_depth}-00080{idx + 1}"
                )
                db_run_id = run_id_map[r.id]
                wf_db_id = db_wf_ids.get(r.workflow_uri, r.workflow_def_id)
                await conn.execute(
                    upsert_run_sql,
                    {
                        "id": db_run_id,
                        "run_key": canonical_key,
                        "workspace_id": r.workspace_id,
                        "workflow_def_id": wf_db_id,
                        "parent_run_id": (
                            run_id_map.get(r.parent_run_id) if r.parent_run_id else None
                        ),
                        "parent_step_execution_id": None,
                        "root_run_id": run_id_map.get(r.root_run_id, db_run_id),
                        "nesting_depth": r.nesting_depth,
                        "execution_regime": r.execution_regime,
                        "criticality": r.criticality,
                        "trigger_id": None,
                        "trigger_idempotency_key": None,
                        "status": "COMPLETED",
                        "initiated_by_user_id": r.initiated_by_user_id,
                        "execution_identity_mode": r.execution_identity_mode,
                        "budget_max_usd": r.budget_max_usd,
                    },
                )

            step_id_map: dict[str, str] = {}
            seq = 1
            for r in svc.runs:
                db_run_id = run_id_map[r.id]
                for s in svc.engine.blackboard.list_step_executions(r.id):
                    db_step_id = f"0192c4e0-0000-7000-8000-0000000035{seq:02d}"
                    step_id_map[s.id] = db_step_id
                    seq += 1
                    await conn.execute(
                        upsert_step_sql,
                        {
                            "id": db_step_id,
                            "step_execution_key": f"stepexec-{db_run_id[-6:]}-{s.step_key}",
                            "run_id": db_run_id,
                            "step_key": s.step_key,
                            "step_index": s.step_index,
                            "step_type": s.step_type,
                            "execution_mode": s.execution_mode,
                            "status": s.status,
                            "attempt_count": s.attempt_count,
                            "max_agent_retries": s.max_agent_retries,
                            "draft_artifact_jsonb": json.dumps(s.draft_artifact),
                            "draft_cas_key": s.draft_cas_key,
                            "step_memlog_jsonb": json.dumps([m.to_dict() for m in s.step_memlog]),
                            "hydrated_input_uris_jsonb": json.dumps(list(s.hydrated_input_uris)),
                            "child_run_id": (
                                run_id_map.get(s.child_run_id) if s.child_run_id else None
                            ),
                            "committed_snapshot_id": None,
                            "cost_usd": s.cost_usd,
                        },
                    )
                    steps_count += 1

            snap_id_map: dict[str, str] = {}
            s_seq = 1
            for r in svc.runs:
                db_run_id = run_id_map[r.id]
                for sn in svc.engine.blackboard.get_active_snapshots(r.id):
                    db_snap_id = f"0192c4e0-0000-7000-8000-0000000036{s_seq:02d}"
                    snap_id_map[sn.id] = db_snap_id
                    s_seq += 1
                    await conn.execute(
                        insert_snapshot_sql,
                        {
                            "id": db_snap_id,
                            "snapshot_key": f"snap-{db_run_id[-6:]}-{sn.step_key}",
                            "run_id": db_run_id,
                            "step_execution_id": step_id_map[sn.step_execution_id],
                            "parent_snapshot_id": (
                                snap_id_map.get(sn.parent_snapshot_id)
                                if sn.parent_snapshot_id
                                else None
                            ),
                            "step_key": sn.step_key,
                            "branch_status": sn.branch_status,
                            "artifact_payload_jsonb": json.dumps(sn.artifact_payload),
                            "artifact_cas_key": sn.artifact_cas_key,
                            "artifact_sha256": sn.artifact_sha256,
                            "memlog_summary_jsonb": json.dumps(
                                [m.to_dict() for m in sn.memlog_summary]
                            ),
                            "superseded_snapshot_ids_jsonb": json.dumps(
                                list(sn.superseded_snapshot_ids)
                            ),
                        },
                    )
                    snaps_count += 1

            if apply_changes:
                await trans.commit()
            else:
                await trans.rollback()
        except Exception:
            if trans.is_active:
                await trans.rollback()
            raise

    return Story32BackfillReport(
        step_executions_count=steps_count,
        blackboard_snapshots_count=snaps_count,
        dry_run=not apply_changes,
        committed=apply_changes,
    )


async def _run_cli(apply: bool) -> Story32BackfillReport:
    engine = create_async_engine(resolve_database_url(), pool_pre_ping=True)
    try:
        return await backfill_step_executions_and_blackboard_snapshots(engine, apply_changes=apply)
    finally:
        await engine.dispose()


def main() -> int:
    """CLI entrypoint for `07_backfill_step_executions_and_blackboard_snapshots.py`."""
    parser = argparse.ArgumentParser(
        description="Backfill Story 3.2 step executions and append-only blackboard snapshots."
    )
    mode_group = parser.add_mutually_exclusive_group()
    mode_group.add_argument(
        "--dry-run",
        action="store_true",
        default=True,
        help="Run in dry-run mode and rollback transaction (default).",
    )
    mode_group.add_argument(
        "--apply",
        action="store_true",
        help="Commit the batched idempotent upserts.",
    )
    args = parser.parse_args()
    report = asyncio.run(_run_cli(apply=bool(args.apply)))
    print(json.dumps(report.__dict__, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
