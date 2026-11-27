"""Shared active run-lock pin checks across storage, packs & bootstrap (`AD-19`, `Story 31.4`)."""

from __future__ import annotations

import json

import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncConnection

from orcia_kernel.errors import ResourcePinnedByActiveRunsError

TERMINAL_RUN_STATUSES: tuple[str, ...] = (
    "COMPLETED",
    "COMMITTED_AUTONOMOUS",
    "FAILED",
    "CANCELLED",
    "ROLLED_BACK",
    "KILL_SWITCH_STOPPED",
)
TERMINAL_RUN_STATUSES_SQL = ", ".join(f"'{status}'" for status in TERMINAL_RUN_STATUSES)


async def assert_resource_not_pinned_by_active_runs_conn(
    conn: AsyncConnection,
    *,
    target_kind: str,
    target_id: str,
    instance: str | None = None,
) -> None:
    """Raise `409 ERR_RESOURCE_PINNED_BY_ACTIVE_RUNS` if an active run pins this slot target."""
    has_tables = (
        await conn.execute(
            sa.text(
                "SELECT (to_regclass('run_lock_manifests') IS NOT NULL "
                "AND to_regclass('workflow_runs') IS NOT NULL)"
            )
        )
    ).scalar()
    if not has_tables:
        return
    slot_match = json.dumps([{"target_kind": target_kind, "target_id": target_id}])
    pinned = (
        await conn.execute(
            sa.text(
                f"SELECT 1 FROM run_lock_manifests rlm "
                f"JOIN workflow_runs wr ON wr.id = rlm.run_id "
                f"WHERE wr.status NOT IN ({TERMINAL_RUN_STATUSES_SQL}) "
                f"AND COALESCE(rlm.manifest_jsonb->'resolved_pack_slots', '[]'::jsonb) "
                f"@> CAST(:slot_match AS jsonb) LIMIT 1"
            ),
            {"slot_match": slot_match},
        )
    ).scalar()
    if pinned is not None:
        raise ResourcePinnedByActiveRunsError(
            detail_override=(
                f"{target_kind} {target_id!r} is pinned inside an active run lock manifest."
            ),
            instance=instance,
        )


async def assert_pack_bundle_not_pinned_by_active_runs_conn(
    conn: AsyncConnection,
    *,
    bundle_id: str,
    slug: str | None = None,
    version: str | None = None,
    instance: str | None = None,
) -> None:
    """Raise `409 ERR_RESOURCE_PINNED_BY_ACTIVE_RUNS` if active runs pin `bundle_id`."""
    has_tables = (
        await conn.execute(
            sa.text(
                "SELECT (to_regclass('run_lock_manifests') IS NOT NULL "
                "AND to_regclass('workflow_runs') IS NOT NULL)"
            )
        )
    ).scalar()
    if not has_tables:
        return
    pin_match = json.dumps([{"pack_bundle_id": bundle_id}])
    if slug and version:
        uri_exact = f"orcia://packs/{slug}@{version}"
        legacy_uri = f"packs/{slug}@{version}"
        uri_prefix = f"orcia://packs/{slug}/%@{version}"
    elif slug:
        uri_exact = "__never__"
        legacy_uri = "__never__"
        uri_prefix = f"orcia://packs/{slug}/%"
    else:
        uri_exact = "__never__"
        legacy_uri = "__never__"
        uri_prefix = "__never__"
    pinned = (
        await conn.execute(
            sa.text(
                f"SELECT 1 FROM run_lock_manifests rlm "
                f"JOIN workflow_runs wr ON wr.id = rlm.run_id "
                f"WHERE wr.status NOT IN ({TERMINAL_RUN_STATUSES_SQL}) "
                f"AND ("
                f"  COALESCE(rlm.manifest_jsonb->'pinned_packs', '[]'::jsonb) "
                f"      @> CAST(:pin_match AS jsonb) "
                f"  OR rlm.manifest_jsonb->>'pack_bundle_id' = :bid "
                f"  OR EXISTS ("
                f"      SELECT 1 FROM jsonb_array_elements("
                f"          COALESCE(rlm.manifest_jsonb->'sources', '[]'::jsonb)"
                f"      ) AS src "
                f"      WHERE src->>'uri' IN (:uri_exact, :legacy_uri) "
                f"         OR src->>'uri' LIKE :uri_prefix"
                f"  )"
                f") LIMIT 1"
            ),
            {
                "pin_match": pin_match,
                "bid": bundle_id,
                "uri_exact": uri_exact,
                "legacy_uri": legacy_uri,
                "uri_prefix": uri_prefix,
            },
        )
    ).scalar()
    if pinned is not None:
        raise ResourcePinnedByActiveRunsError(
            detail_override=f"Pack bundle {bundle_id!r} is pinned by active workflow runs.",
            instance=instance,
        )


__all__ = [
    "TERMINAL_RUN_STATUSES",
    "TERMINAL_RUN_STATUSES_SQL",
    "assert_pack_bundle_not_pinned_by_active_runs_conn",
    "assert_resource_not_pinned_by_active_runs_conn",
]
