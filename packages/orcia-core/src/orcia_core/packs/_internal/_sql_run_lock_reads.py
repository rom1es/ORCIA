"""PG18 `run_lock_manifests` read, attach & status-sync helpers (`Story 31.4`, `<= 300 L`)."""

from __future__ import annotations

import hashlib
import json
from typing import Any
from uuid import UUID

import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncEngine

from orcia_core.packs.slot_guard import PinnedPackManifestEntry


def parse_run_uuid(run_id: str) -> str | None:
    """Extract canonical UUID string from `run-<uuid>` or `<uuid>`."""
    clean = (run_id or "").strip().removeprefix("run-").strip()
    if not clean:
        return None
    try:
        return str(UUID(clean))
    except (ValueError, TypeError):
        return None


def map_v2_status_to_workflow_run_status(v2_status: str) -> str:
    """Map `BoundedWorkflowRunState.status` onto `workflow_runs` CHECK values (`0010`)."""
    upper = (v2_status or "").strip().upper()
    if upper in ("COMPLETED", "COMPLETED_APPROVED"):
        return "COMPLETED"
    if upper in ("FAILED", "FAILED_GATES"):
        return "FAILED"
    if upper in ("ROLLED_BACK", "CANCELLED"):
        return "ROLLED_BACK"
    if upper in (
        "WAITING_SUBSTEP_HITL",
        "WAITING_EXTERNAL_GATE",
        "WAITING_FINAL_ANCHOR",
        "WAITING_WRITE_PREVIEW",
        "WAITING_FOR_HUMAN_GATE",
        "RETURN_LOOP_TRIGGERED",
    ):
        return "WAITING_FOR_HUMAN_GATE"
    if upper == "WAITING_FOR_HUMAN_ARBITRATION":
        return "WAITING_FOR_HUMAN_ARBITRATION"
    if upper in ("SLA_SUSPENDED", "PAUSED_CIRCUIT_BREAKER"):
        return "PAUSED_CIRCUIT_BREAKER"
    if upper == "PAUSED_BUDGET_EXCEEDED":
        return "PAUSED_BUDGET_EXCEEDED"
    return "RUNNING"


async def sync_workflow_v2_run_status_sql(
    engine: AsyncEngine,
    *,
    run_id: str,
    status: str,
) -> None:
    """Update `workflow_runs.status` on v2 progress (never alters `run_lock_manifests`)."""
    run_uuid = parse_run_uuid(run_id)
    if run_uuid is None:
        return
    mapped = map_v2_status_to_workflow_run_status(status)
    async with engine.begin() as conn:
        await conn.execute(
            sa.text("UPDATE workflow_runs SET status = :st WHERE id = CAST(:rid AS uuid)"),
            {"st": mapped, "rid": run_uuid},
        )


async def get_run_lock_manifest_sql(
    engine: AsyncEngine,
    *,
    run_id: str,
) -> dict[str, Any] | None:
    """Fetch immutable `run_lock_manifests` snapshot from PG18 by `run_id`."""
    run_uuid = parse_run_uuid(run_id)
    if run_uuid is None:
        return None
    async with engine.connect() as conn:
        row = (
            await conn.execute(
                sa.text(
                    """
                    SELECT rlm.run_id::text, wr.workspace_id::text, rlm.manifest_jsonb,
                           rlm.manifest_sha256, rlm.locked_at
                    FROM run_lock_manifests rlm
                    JOIN workflow_runs wr ON wr.id = rlm.run_id
                    WHERE rlm.run_id = CAST(:rid AS uuid)
                    LIMIT 1
                    """
                ),
                {"rid": run_uuid},
            )
        ).first()
    if row is None:
        return None
    raw_manifest = row[2]
    manifest = (
        json.loads(raw_manifest)
        if isinstance(raw_manifest, str)
        else (dict(raw_manifest) if isinstance(raw_manifest, dict) else {})
    )
    locked_at = row[4]
    return {
        "run_id": str(manifest.get("run_id") or run_id),
        "workspace_id": str(row[1]),
        "workflow_id": str(manifest.get("workflow_id") or ""),
        "workflow_slug": str(manifest.get("workflow_slug") or ""),
        "workflow_version": str(manifest.get("workflow_version") or ""),
        "pinned_packs": list(manifest.get("pinned_packs") or []),
        "resolved_pack_slots": list(manifest.get("resolved_pack_slots") or []),
        "manifest_sha256": str(row[3]).strip(),
        "locked_at_iso": (
            locked_at.isoformat() if hasattr(locked_at, "isoformat") else str(locked_at or "")
        ),
        "manifest": manifest,
    }


async def attach_pinned_packs_to_run_lock_sql(
    engine: AsyncEngine,
    *,
    run_id: str,
    pinned_packs: list[PinnedPackManifestEntry],
) -> None:
    """Merge `pinned_packs` & `resolved_pack_slots` into an orchestration `run_lock_manifests`."""
    if not pinned_packs:
        return
    run_uuid = parse_run_uuid(run_id)
    if run_uuid is None:
        return
    flat_slots = [s.model_dump(mode="json") for p in pinned_packs for s in p.resolved_pack_slots]
    pack_dicts = [p.model_dump(mode="json") for p in pinned_packs]
    async with engine.begin() as conn:
        row = (
            await conn.execute(
                sa.text(
                    "SELECT manifest_jsonb FROM run_lock_manifests "
                    "WHERE run_id = CAST(:rid AS uuid) LIMIT 1 FOR UPDATE"
                ),
                {"rid": run_uuid},
            )
        ).first()
        if row is None:
            return
        raw = row[0]
        manifest = json.loads(raw) if isinstance(raw, str) else dict(raw or {})
        manifest["pinned_packs"] = pack_dicts
        manifest["resolved_pack_slots"] = flat_slots
        manifest.pop("manifest_sha256", None)
        msha = hashlib.sha256(
            json.dumps(manifest, sort_keys=True, ensure_ascii=False).encode("utf-8")
        ).hexdigest()
        manifest["manifest_sha256"] = msha
        await conn.execute(
            sa.text(
                "UPDATE run_lock_manifests "
                "SET manifest_jsonb = CAST(:manifest AS jsonb), manifest_sha256 = :msha "
                "WHERE run_id = CAST(:rid AS uuid)"
            ),
            {
                "manifest": json.dumps(manifest, sort_keys=True, ensure_ascii=False),
                "msha": msha,
                "rid": run_uuid,
            },
        )


__all__ = [
    "attach_pinned_packs_to_run_lock_sql",
    "get_run_lock_manifest_sql",
    "map_v2_status_to_workflow_run_status",
    "parse_run_uuid",
    "sync_workflow_v2_run_status_sql",
]
