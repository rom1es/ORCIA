"""Parent FK resolution & `run_lock_manifests` / `workflow_runs` SQL helpers (`REM-09`)."""

from __future__ import annotations

import json
from typing import Any, cast
from uuid import UUID

import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncSession

from orcia_core.catalog.models import RunLockSourceTriplet
from orcia_core.orchestration._internal.uow import DbosSqlAlchemyUnitOfWork
from orcia_core.orchestration.models import (
    RecursiveRunLockManifest,
    SubWorkflowLockEntry,
    WorkflowCriticality,
    WorkflowExecutionRegime,
    WorkflowRunEntity,
    WorkflowRunStatus,
)
from orcia_core.permissions.models import ExecutionIdentityMode


async def resolve_existing_user_id_sql(
    session: AsyncSession,
    user_id: str | None,
    *,
    fallback_to_any: bool = False,
) -> str | None:
    """Resolve `users.id` in PG18 if present; optionally fall back to the first user row."""
    if user_id and user_id.strip():
        try:
            UUID(user_id.strip())
            row = (
                await session.execute(
                    sa.text("SELECT id::text FROM users WHERE id = CAST(:uid AS uuid) LIMIT 1"),
                    {"uid": user_id.strip()},
                )
            ).scalar_one_or_none()
            if row is not None:
                return str(row)
        except ValueError:
            pass
    if not fallback_to_any:
        return None
    fallback = (
        await session.execute(sa.text("SELECT id::text FROM users ORDER BY created_at ASC LIMIT 1"))
    ).scalar_one_or_none()
    return str(fallback) if fallback is not None else None


async def ensure_workflow_definition_sql(
    session: AsyncSession,
    *,
    workflow_def_id: str,
    workspace_id: str,
    workflow_uri: str,
    workflow_sha256: str = "0" * 64,
) -> str:
    """Ensure a `workflow_definitions` row exists for `workflow_uri` and return its UUID."""
    existing_id = (
        await session.execute(
            sa.text("SELECT id::text FROM workflow_definitions WHERE uri = :uri LIMIT 1"),
            {"uri": workflow_uri},
        )
    ).scalar_one_or_none()
    if existing_id is not None:
        return str(existing_id)

    ws_exists = (
        await session.execute(
            sa.text("SELECT id::text FROM workspaces WHERE id = CAST(:ws AS uuid) LIMIT 1"),
            {"ws": workspace_id},
        )
    ).scalar_one_or_none()
    await session.execute(
        sa.text(
            """
            INSERT INTO workflow_definitions (
                id, workspace_id, uri, version, source_format, steps_schema_jsonb, sha256
            ) VALUES (
                CAST(:id AS uuid), CAST(:ws AS uuid), :uri, '1.0.0', 'ORCIA',
                '{}'::jsonb, :sha256
            )
            ON CONFLICT (uri) DO NOTHING;
            """
        ),
        {
            "id": workflow_def_id,
            "ws": str(ws_exists) if ws_exists is not None else None,
            "uri": workflow_uri,
            "sha256": workflow_sha256[:64].ljust(64, "0"),
        },
    )
    resolved = (
        await session.execute(
            sa.text("SELECT id::text FROM workflow_definitions WHERE uri = :uri LIMIT 1"),
            {"uri": workflow_uri},
        )
    ).scalar_one_or_none()
    return str(resolved) if resolved is not None else workflow_def_id


async def ensure_run_row_exists_in_session(
    session: AsyncSession,
    run: WorkflowRunEntity,
) -> None:
    """Ensure parent `workflow_definitions` and `workflow_runs` rows exist for `run`."""
    resolved_wf_def_id = await ensure_workflow_definition_sql(
        session,
        workflow_def_id=run.workflow_def_id,
        workspace_id=run.workspace_id,
        workflow_uri=run.workflow_uri,
        workflow_sha256=run.run_lock.workflow_sha256,
    )
    resolved_user_id = await resolve_existing_user_id_sql(
        session, run.initiated_by_user_id, fallback_to_any=False
    )
    await session.execute(
        sa.text(
            """
            INSERT INTO workflow_runs (
                id, run_key, workspace_id, workflow_def_id, parent_run_id,
                parent_step_execution_id, root_run_id, nesting_depth,
                execution_regime, criticality, trigger_id, trigger_idempotency_key,
                status, initiated_by_user_id, execution_identity_mode, budget_max_usd
            ) VALUES (
                CAST(:id AS uuid), :run_key, CAST(:workspace_id AS uuid),
                CAST(:workflow_def_id AS uuid), CAST(:parent_run_id AS uuid),
                CAST(:parent_step_execution_id AS uuid), CAST(:root_run_id AS uuid),
                :nesting_depth, :execution_regime, :criticality,
                CAST(:trigger_id AS uuid), :trigger_idempotency_key,
                :status, CAST(:initiated_by_user_id AS uuid),
                :execution_identity_mode, :budget_max_usd
            )
            ON CONFLICT (id) DO NOTHING;
            """
        ),
        {
            "id": run.id,
            "run_key": run.run_key,
            "workspace_id": run.workspace_id,
            "workflow_def_id": resolved_wf_def_id,
            "parent_run_id": run.parent_run_id,
            "parent_step_execution_id": run.parent_step_execution_id,
            "root_run_id": run.root_run_id,
            "nesting_depth": run.nesting_depth,
            "execution_regime": run.execution_regime,
            "criticality": run.criticality,
            "trigger_id": run.trigger_id,
            "trigger_idempotency_key": run.trigger_idempotency_key,
            "status": run.status,
            "initiated_by_user_id": resolved_user_id,
            "execution_identity_mode": run.execution_identity_mode,
            "budget_max_usd": run.budget_max_usd,
        },
    )


async def upsert_run_lock_manifest_sql(
    uow: DbosSqlAlchemyUnitOfWork,
    run_lock: RecursiveRunLockManifest,
) -> None:
    """Persist or update a `run_lock_manifests` row (`0010`)."""
    async with uow.session_scope() as session:
        await session.execute(
            sa.text(
                """
                INSERT INTO run_lock_manifests (
                    run_id, manifest_jsonb, overrides_sha256, kb_snapshot_hash, manifest_sha256
                ) VALUES (
                    CAST(:run_id AS uuid), CAST(:manifest_jsonb AS jsonb),
                    :overrides_sha256, :kb_snapshot_hash, :manifest_sha256
                )
                ON CONFLICT (run_id) DO NOTHING;
                """
            ),
            {
                "run_id": run_lock.run_id,
                "manifest_jsonb": json.dumps(run_lock.to_dict(), sort_keys=True),
                "overrides_sha256": run_lock.overrides_sha256[:64],
                "kb_snapshot_hash": run_lock.kb_snapshot_hash[:64],
                "manifest_sha256": run_lock.manifest_sha256[:64],
            },
        )


def _deserialize_sub_locks(raw_items: Any) -> tuple[SubWorkflowLockEntry, ...]:
    items = raw_items if isinstance(raw_items, list) else []
    out: list[SubWorkflowLockEntry] = []
    for item in items:
        if not isinstance(item, dict):
            continue
        sources = tuple(
            RunLockSourceTriplet(
                alias=str(s.get("alias", "")),
                scheme=cast(Any, str(s.get("scheme", "git"))),
                uri=str(s.get("uri", "")),
                resolved_version=str(s.get("resolved_version", "1.0.0")),
                sha256=str(s.get("sha256", "0" * 64)),
                cas_key=str(s.get("cas_key", "")),
            )
            for s in (item.get("sources") or [])
            if isinstance(s, dict)
        )
        out.append(
            SubWorkflowLockEntry(
                step_key=str(item.get("step_key", "")),
                workflow_uri=str(item.get("workflow_uri", "")),
                workflow_version=str(item.get("workflow_version", "1.0.0")),
                workflow_sha256=str(item.get("workflow_sha256", "0" * 64)).ljust(64, "0")[:64],
                effective_workflow_sha256=str(
                    item.get("effective_workflow_sha256", "0" * 64)
                ).ljust(64, "0")[:64],
                nesting_depth=int(item.get("nesting_depth", 1)),
                applied_override_keys=tuple(
                    str(k) for k in (item.get("applied_override_keys") or [])
                ),
                sources=sources,
                sub_workflow_locks=_deserialize_sub_locks(item.get("sub_workflow_locks")),
            )
        )
    return tuple(out)


def _build_run_lock_from_row(row: dict[str, Any]) -> RecursiveRunLockManifest:
    raw_manifest = row.get("manifest_jsonb")
    manifest = (
        json.loads(raw_manifest)
        if isinstance(raw_manifest, str)
        else (dict(raw_manifest) if isinstance(raw_manifest, dict) else {})
    )
    sources = tuple(
        RunLockSourceTriplet(
            alias=str(s.get("alias", "")),
            scheme=cast(Any, str(s.get("scheme", "git"))),
            uri=str(s.get("uri", "")),
            resolved_version=str(s.get("resolved_version", "1.0.0")),
            sha256=str(s.get("sha256", "0" * 64)),
            cas_key=str(s.get("cas_key", "")),
        )
        for s in (manifest.get("sources") or [])
        if isinstance(s, dict)
    )
    wf_sha = str(manifest.get("workflow_sha256") or row.get("wf_sha256") or ("0" * 64))
    eff_sha = str(manifest.get("effective_workflow_sha256") or wf_sha)
    ovr_sha = str(manifest.get("overrides_sha256") or row.get("overrides_sha256") or ("0" * 64))
    man_sha = str(manifest.get("manifest_sha256") or row.get("manifest_sha256") or ("0" * 64))
    return RecursiveRunLockManifest(
        run_id=str(row["id"]),
        workspace_id=str(row["workspace_id"]),
        workflow_uri=str(manifest.get("workflow_uri") or row.get("workflow_uri") or ""),
        workflow_version=str(manifest.get("workflow_version") or "1.0.0"),
        workflow_sha256=wf_sha.ljust(64, "0")[:64],
        effective_workflow_sha256=eff_sha.ljust(64, "0")[:64],
        overrides_sha256=ovr_sha.ljust(64, "0")[:64],
        kb_snapshot_hash=str(
            manifest.get("kb_snapshot_hash") or row.get("kb_snapshot_hash") or ("0" * 64)
        ),
        applied_override_keys=tuple(str(k) for k in (manifest.get("applied_override_keys") or [])),
        sources=sources,
        sub_workflow_locks=_deserialize_sub_locks(manifest.get("sub_workflow_locks")),
        manifest_sha256=man_sha.ljust(64, "0")[:64],
    )


async def list_workflow_runs_with_locks_sql(
    uow: DbosSqlAlchemyUnitOfWork, *, run_id: str | None = None
) -> tuple[WorkflowRunEntity, ...]:
    """Read `workflow_runs` joined with `workflow_definitions` and `run_lock_manifests`."""
    where_clause = "WHERE wr.id = CAST(:run_id AS uuid)" if run_id else ""
    params: dict[str, Any] = {"run_id": run_id} if run_id else {}
    async with uow.session_scope() as session:
        rows = (
            (
                await session.execute(
                    sa.text(
                        f"""
                        SELECT
                            wr.id::text, wr.run_key, wr.workspace_id::text,
                            wr.workflow_def_id::text, wd.uri AS workflow_uri,
                            wd.sha256 AS wf_sha256, wr.parent_run_id::text,
                            wr.parent_step_execution_id::text, wr.root_run_id::text,
                            wr.nesting_depth, wr.execution_regime, wr.criticality,
                            wr.trigger_id::text, wr.trigger_idempotency_key,
                            wr.status, wr.initiated_by_user_id::text,
                            wr.execution_identity_mode, wr.budget_max_usd::float8,
                            rlm.manifest_jsonb, rlm.overrides_sha256,
                            rlm.kb_snapshot_hash, rlm.manifest_sha256
                        FROM workflow_runs wr
                        JOIN workflow_definitions wd ON wd.id = wr.workflow_def_id
                        LEFT JOIN run_lock_manifests rlm ON rlm.run_id = wr.id
                        {where_clause}
                        ORDER BY wr.created_at ASC, wr.id ASC;
                        """
                    ),
                    params,
                )
            )
            .mappings()
            .all()
        )
        return tuple(
            WorkflowRunEntity(
                id=str(r["id"]),
                run_key=str(r["run_key"]),
                workspace_id=str(r["workspace_id"]),
                workflow_def_id=str(r["workflow_def_id"]),
                workflow_uri=str(r["workflow_uri"]),
                parent_run_id=str(r["parent_run_id"]) if r["parent_run_id"] else None,
                parent_step_execution_id=(
                    str(r["parent_step_execution_id"]) if r["parent_step_execution_id"] else None
                ),
                root_run_id=str(r["root_run_id"]),
                nesting_depth=int(r["nesting_depth"]),
                execution_regime=cast(WorkflowExecutionRegime, str(r["execution_regime"])),
                criticality=cast(WorkflowCriticality, str(r["criticality"])),
                trigger_id=str(r["trigger_id"]) if r["trigger_id"] else None,
                trigger_idempotency_key=(
                    str(r["trigger_idempotency_key"]) if r["trigger_idempotency_key"] else None
                ),
                status=cast(WorkflowRunStatus, str(r["status"])),
                initiated_by_user_id=(
                    str(r["initiated_by_user_id"]) if r["initiated_by_user_id"] else None
                ),
                execution_identity_mode=cast(
                    ExecutionIdentityMode, str(r["execution_identity_mode"])
                ),
                budget_max_usd=float(r["budget_max_usd"]),
                run_lock=_build_run_lock_from_row(dict(r)),
            )
            for r in rows
        )
