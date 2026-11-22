"""PG18 non-N+1 queries for active workspace `blackboard_snapshots` (`Story 26.5`)."""

from __future__ import annotations

import json
from typing import Any
from uuid import UUID

import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncEngine

from orcia_core.blackboard.models import BlackboardSnapshotEntity, StepMemlogEntry


def _parse_json_dict(raw: Any) -> dict[str, Any]:
    if isinstance(raw, dict):
        return dict(raw)
    if isinstance(raw, str) and raw.strip():
        decoded = json.loads(raw)
        if isinstance(decoded, dict):
            return decoded
    return {}


def _parse_json_list(raw: Any) -> list[Any]:
    if isinstance(raw, list):
        return list(raw)
    if isinstance(raw, str) and raw.strip():
        decoded = json.loads(raw)
        if isinstance(decoded, list):
            return decoded
    return []


_READY_BB_ENGINES: set[int] = set()


async def list_active_workspace_blackboard_snapshots_pg(
    engine: AsyncEngine,
    *,
    workspace_id: str,
    limit: int = 25,
) -> tuple[BlackboardSnapshotEntity, ...]:
    """Load active `blackboard_snapshots` strictly scoped to `workspace_id` in one SQL query."""
    clean_ws = (workspace_id or "").strip()
    if not clean_ws:
        return ()
    try:
        UUID(clean_ws)
    except ValueError:
        async with engine.connect() as conn:
            ws_reg = (
                await conn.execute(sa.text("SELECT to_regclass('public.workspaces')"))
            ).scalar()
            if ws_reg is None:
                return ()
            ws_row = (
                await conn.execute(
                    sa.text("SELECT id::text FROM workspaces WHERE slug = :slug LIMIT 1"),
                    {"slug": clean_ws},
                )
            ).first()
            if ws_row is None:
                return ()
            clean_ws = str(ws_row[0])

    async with engine.connect() as conn:
        eng_key = id(engine)
        if eng_key not in _READY_BB_ENGINES:
            reg_row = (
                await conn.execute(
                    sa.text(
                        "SELECT to_regclass('public.blackboard_snapshots'), "
                        "to_regclass('public.workflow_runs')"
                    )
                )
            ).one()
            if reg_row[0] is None or reg_row[1] is None:
                return ()
            _READY_BB_ENGINES.add(eng_key)
        rows = (
            (
                await conn.execute(
                    sa.text(
                        """
                        SELECT
                            bs.id::text AS id,
                            bs.snapshot_key,
                            bs.run_id::text AS run_id,
                            bs.step_execution_id::text AS step_execution_id,
                            bs.parent_snapshot_id::text AS parent_snapshot_id,
                            bs.step_key,
                            bs.branch_status,
                            bs.artifact_payload_jsonb,
                            bs.artifact_cas_key,
                            TRIM(bs.artifact_sha256) AS artifact_sha256,
                            bs.memlog_summary_jsonb,
                            bs.superseded_snapshot_ids_jsonb
                        FROM blackboard_snapshots bs
                        JOIN workflow_runs wr ON wr.id = bs.run_id
                        WHERE wr.workspace_id = CAST(:workspace_id AS uuid)
                          AND bs.branch_status = 'ACTIVE'
                        ORDER BY bs.created_at DESC, bs.id DESC
                        LIMIT :limit;
                        """
                    ),
                    {"workspace_id": clean_ws, "limit": max(1, limit * 2)},
                )
            )
            .mappings()
            .all()
        )

    superseded_ids: set[str] = set()
    for row in rows:
        for sid in _parse_json_list(row["superseded_snapshot_ids_jsonb"]):
            superseded_ids.add(str(sid))

    active: list[BlackboardSnapshotEntity] = []
    for row in rows:
        snap_id = str(row["id"])
        if snap_id in superseded_ids or str(row["branch_status"]) == "SUPERSEDED":
            continue
        memlog = tuple(
            StepMemlogEntry(
                entry_id=str(m.get("entry_id") or ""),
                step_key=str(m.get("step_key") or row["step_key"]),
                marker_type=str(m.get("marker_type") or "ASSUMPTION"),
                summary=str(m.get("summary") or ""),
                details=str(m.get("details") or ""),
                source_uris=tuple(str(u) for u in m.get("source_uris", [])),
            )
            for m in _parse_json_list(row["memlog_summary_jsonb"])
            if isinstance(m, dict)
        )
        sup_tuple = tuple(str(s) for s in _parse_json_list(row["superseded_snapshot_ids_jsonb"]))
        active.append(
            BlackboardSnapshotEntity(
                id=snap_id,
                snapshot_key=str(row["snapshot_key"]),
                run_id=str(row["run_id"]),
                step_execution_id=str(row["step_execution_id"]),
                parent_snapshot_id=(
                    str(row["parent_snapshot_id"]) if row["parent_snapshot_id"] else None
                ),
                step_key=str(row["step_key"]),
                branch_status="ACTIVE",
                artifact_payload=_parse_json_dict(row["artifact_payload_jsonb"]),
                artifact_cas_key=str(row["artifact_cas_key"]),
                artifact_sha256=str(row["artifact_sha256"]).strip(),
                memlog_summary=memlog,
                superseded_snapshot_ids=sup_tuple,
            )
        )
        if len(active) >= limit:
            break
    return tuple(active)


__all__ = ["list_active_workspace_blackboard_snapshots_pg"]
