"""PG18 `run_lock_manifests` pinning & pre-start guard for workflow-v2 runs (`Story 31.4`)."""

from __future__ import annotations

import hashlib
import json
from typing import Any
from uuid import UUID

import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncEngine
from uuid_utils import uuid7

from orcia_core.packs._internal._sql_run_lock_reads import (
    map_v2_status_to_workflow_run_status,
    parse_run_uuid,
)
from orcia_core.packs._internal._sql_workspace_pack_views import (
    load_active_workspace_packs_for_run_conn,
)
from orcia_core.packs.slot_guard import (
    PinnedPackManifestEntry,
    build_pinned_run_lock_payload,
)


async def validate_and_snapshot_workspace_packs_sql(
    engine: AsyncEngine,
    *,
    workspace_id: str | None,
    workflow_pack_id: str | None = None,
    instance: str | None = None,
) -> list[PinnedPackManifestEntry]:
    """Fail closed (`422 ERR_PACK_SLOT_UNBOUND`) or return pinned active workspace packs."""
    has_ws = bool(workspace_id and workspace_id.strip())
    has_pack = bool(workflow_pack_id and workflow_pack_id.strip())
    if not has_ws and not has_pack:
        return []
    async with engine.connect() as conn:
        return await load_active_workspace_packs_for_run_conn(
            conn,
            workspace_id=workspace_id,
            workflow_pack_id=workflow_pack_id,
            instance=instance,
        )


async def _upsert_v2_run_in_conn(
    conn: Any,
    *,
    run_id: str,
    ws_uuid: str,
    workflow_id: str,
    workflow_slug: str,
    status: str,
    v2_run_payload: dict[str, Any],
) -> None:
    await conn.execute(
        sa.text(
            """
            INSERT INTO workflow_v2_runs (
                id, run_id, workspace_id, workflow_id, workflow_slug,
                workflow_title, actor_slug, status, reflexive_execution_id,
                state_jsonb, created_at, updated_at
            )
            VALUES (
                CAST(:id AS UUID), :run_id, CAST(:workspace_id AS UUID), :workflow_id,
                :workflow_slug, :workflow_title, :actor_slug, :status,
                :reflexive_execution_id, CAST(:state_jsonb AS JSONB), NOW(), NOW()
            )
            ON CONFLICT (run_id) DO UPDATE SET
                workspace_id = COALESCE(EXCLUDED.workspace_id, workflow_v2_runs.workspace_id),
                workflow_title = EXCLUDED.workflow_title,
                actor_slug = EXCLUDED.actor_slug,
                status = EXCLUDED.status,
                reflexive_execution_id = COALESCE(
                    EXCLUDED.reflexive_execution_id, workflow_v2_runs.reflexive_execution_id
                ),
                state_jsonb = EXCLUDED.state_jsonb,
                updated_at = NOW()
            """
        ),
        {
            "id": str(uuid7()),
            "run_id": run_id,
            "workspace_id": ws_uuid,
            "workflow_id": workflow_id,
            "workflow_slug": workflow_slug,
            "workflow_title": str(v2_run_payload.get("workflow_title") or workflow_slug),
            "actor_slug": str(v2_run_payload.get("actor_slug") or "system"),
            "status": status,
            "reflexive_execution_id": v2_run_payload.get("reflexive_execution_id"),
            "state_jsonb": json.dumps(v2_run_payload.get("state") or {}, ensure_ascii=False),
        },
    )


async def pin_workflow_v2_run_lock_sql(
    engine: AsyncEngine,
    *,
    run_id: str,
    workspace_id: str | None,
    workflow_id: str,
    workflow_slug: str,
    workflow_version: str,
    workflow_sha256: str,
    status: str,
    actor_user_id: str | None,
    pinned_packs: list[PinnedPackManifestEntry],
    v2_run_payload: dict[str, Any] | None = None,
) -> tuple[dict[str, Any], str] | None:
    """Persist `workflow_runs` + immutable `run_lock_manifests` snapshot in PG18."""
    if not workspace_id or not workspace_id.strip():
        return None
    run_uuid = parse_run_uuid(run_id)
    if run_uuid is None:
        return None

    clean_ws = workspace_id.strip().removeprefix("scope-ws-").strip()
    async with engine.begin() as conn:
        ws_uuid = (
            await conn.execute(
                sa.text(
                    "SELECT id::text FROM workspaces "
                    "WHERE id::text = :ws OR LOWER(slug) = LOWER(:ws) LIMIT 1"
                ),
                {"ws": clean_ws},
            )
        ).scalar_one_or_none()
        if ws_uuid is None:
            return None

        wf_uri = f"orcia://workflows/v2/{workflow_slug}"
        wf_def_id = (
            await conn.execute(
                sa.text("SELECT id::text FROM workflow_definitions WHERE uri = :uri LIMIT 1"),
                {"uri": wf_uri},
            )
        ).scalar_one_or_none()
        if wf_def_id is None:
            await conn.execute(
                sa.text(
                    "INSERT INTO workflow_definitions ("
                    "id, workspace_id, uri, version, source_format, steps_schema_jsonb, sha256"
                    ") VALUES ("
                    "CAST(:id AS uuid), CAST(:ws AS uuid), :uri, :ver, 'ORCIA', "
                    "CAST(:meta AS jsonb), :sha256"
                    ") ON CONFLICT (uri) DO NOTHING"
                ),
                {
                    "id": str(uuid7()),
                    "ws": str(ws_uuid),
                    "uri": wf_uri,
                    "ver": workflow_version[:64],
                    "meta": json.dumps({"workflow_id": workflow_id, "title": workflow_slug}),
                    "sha256": workflow_sha256[:64].ljust(64, "0"),
                },
            )
            wf_def_id = (
                await conn.execute(
                    sa.text("SELECT id::text FROM workflow_definitions WHERE uri = :uri LIMIT 1"),
                    {"uri": wf_uri},
                )
            ).scalar_one()

        resolved_uid: str | None = None
        if actor_user_id and actor_user_id.strip():
            try:
                UUID(actor_user_id.strip())
                resolved_uid = (
                    await conn.execute(
                        sa.text("SELECT id::text FROM users WHERE id = CAST(:u AS uuid) LIMIT 1"),
                        {"u": actor_user_id.strip()},
                    )
                ).scalar_one_or_none()
            except ValueError:
                resolved_uid = None

        mapped_status = map_v2_status_to_workflow_run_status(status)
        await conn.execute(
            sa.text(
                """
                INSERT INTO workflow_runs (
                    id, run_key, workspace_id, workflow_def_id, parent_run_id,
                    parent_step_execution_id, root_run_id, nesting_depth,
                    execution_regime, criticality, status, initiated_by_user_id,
                    execution_identity_mode, budget_max_usd
                )
                VALUES (
                    CAST(:id AS uuid), :run_key, CAST(:ws AS uuid), CAST(:wf_def_id AS uuid),
                    NULL, NULL, CAST(:id AS uuid), 0, 'INTERACTIVE_COACHING', 'STANDARD',
                    :status, CAST(:uid AS uuid), 'passthrough', 10.0
                )
                ON CONFLICT (id) DO NOTHING
                """
            ),
            {
                "id": run_uuid,
                "run_key": run_id[:128],
                "ws": str(ws_uuid),
                "wf_def_id": str(wf_def_id),
                "status": mapped_status,
                "uid": str(resolved_uid) if resolved_uid is not None else None,
            },
        )
        manifest_payload, manifest_sha = build_pinned_run_lock_payload(
            run_id=run_id,
            workspace_id=str(ws_uuid),
            workflow_id=workflow_id,
            workflow_slug=workflow_slug,
            workflow_version=workflow_version,
            workflow_sha256=workflow_sha256,
            pinned_packs=pinned_packs,
        )
        empty_sha = hashlib.sha256(b"[]").hexdigest()
        await conn.execute(
            sa.text(
                """
                INSERT INTO run_lock_manifests (
                    run_id, manifest_jsonb, overrides_sha256, kb_snapshot_hash, manifest_sha256
                )
                VALUES (
                    CAST(:rid AS uuid), CAST(:manifest AS jsonb), :ovr, :kb, :msha
                )
                ON CONFLICT (run_id) DO NOTHING
                """
            ),
            {
                "rid": run_uuid,
                "manifest": json.dumps(manifest_payload, sort_keys=True, ensure_ascii=False),
                "ovr": empty_sha,
                "kb": empty_sha,
                "msha": manifest_sha,
            },
        )
        if v2_run_payload is not None:
            await _upsert_v2_run_in_conn(
                conn,
                run_id=run_id,
                ws_uuid=str(ws_uuid),
                workflow_id=workflow_id,
                workflow_slug=workflow_slug,
                status=status,
                v2_run_payload=v2_run_payload,
            )
        return manifest_payload, manifest_sha


__all__ = [
    "pin_workflow_v2_run_lock_sql",
    "validate_and_snapshot_workspace_packs_sql",
]
