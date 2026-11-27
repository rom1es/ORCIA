"""Flat Priority-Ordered Loaders for Pack DNA, Broker Policies & Instructions (`Story 31.3`)."""

from __future__ import annotations

import json
from typing import Any

import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncConnection

from orcia_core.domain.namespacing import ResolutionTier, format_pack_resource_uri


def decode_json_dict(raw: object) -> dict[str, Any]:
    if isinstance(raw, dict):
        return dict(raw)
    if isinstance(raw, str) and raw.strip():
        try:
            decoded = json.loads(raw)
            return dict(decoded) if isinstance(decoded, dict) else {}
        except ValueError:
            return {}
    return {}


def tier_rank(
    bundle_id: str | None,
    bundle_kind: str | None,
    priorities_by_bundle: dict[str, int],
) -> tuple[tuple[int, int], ResolutionTier] | None:
    if bundle_id is None:
        return (0, 0), "WORKSPACE_OVERRIDE"
    if bundle_id in priorities_by_bundle:
        return (1, priorities_by_bundle[bundle_id]), "WORKSPACE_PACK"
    if (bundle_kind or "").upper() == "SYSTEM":
        return (2, 0), "SYSTEM_PACK"
    return None


async def load_flat_dna_mechanisms(
    conn: AsyncConnection,
    priorities_by_bundle: dict[str, int],
) -> tuple[dict[str, Any], ...]:
    reg = (await conn.execute(sa.text("SELECT to_regclass('public.pack_dna_mechanisms')"))).scalar()
    if reg is None:
        return ()
    rows = (
        await conn.execute(
            sa.text(
                "SELECT m.mechanism_slug, m.name, m.starlark_source, m.source_sha256, "
                "m.pack_bundle_id::text, dpb.slug, dpb.bundle_kind "
                "FROM pack_dna_mechanisms m "
                "JOIN declarative_pack_bundles dpb ON dpb.id = m.pack_bundle_id "
                "ORDER BY m.mechanism_slug ASC"
            )
        )
    ).fetchall()
    ranked: list[tuple[tuple[int, int], dict[str, Any]]] = []
    for row in rows:
        bid = str(row[4])
        tier_info = tier_rank(bid, str(row[6]), priorities_by_bundle)
        if tier_info is None:
            continue
        sort_key, tier = tier_info
        pslug = str(row[5]).strip().lower()
        mslug = str(row[0]).strip()
        ranked.append(
            (
                sort_key,
                {
                    "mechanism_slug": mslug,
                    "name": str(row[1]),
                    "starlark_source": str(row[2]),
                    "source_sha256": str(row[3]),
                    "pack_bundle_id": bid,
                    "pack_slug": pslug,
                    "resolution_tier": tier,
                    "qualified_ref": format_pack_resource_uri(pslug, "mechanisms", mslug),
                },
            )
        )
    ranked.sort(key=lambda pair: pair[0])
    winners: dict[str, dict[str, Any]] = {}
    for _, item in ranked:
        winners.setdefault(item["mechanism_slug"], item)
    return tuple(winners.values())


async def load_flat_broker_policies(
    conn: AsyncConnection,
    priorities_by_bundle: dict[str, int],
) -> tuple[dict[str, Any], ...]:
    reg = (
        await conn.execute(sa.text("SELECT to_regclass('public.permission_broker_policies')"))
    ).scalar()
    if reg is None:
        return ()
    rows = (
        await conn.execute(
            sa.text(
                "SELECT p.policy_key, p.uri_pattern, p.connector_scheme, p.required_role, "
                "p.approver_team, p.sla_hours, p.pack_bundle_id::text, "
                "dpb.slug, dpb.bundle_kind "
                "FROM permission_broker_policies p "
                "LEFT JOIN declarative_pack_bundles dpb ON dpb.id = p.pack_bundle_id "
                "ORDER BY p.policy_key ASC"
            )
        )
    ).fetchall()
    ranked: list[tuple[tuple[int, int], dict[str, Any]]] = []
    for row in rows:
        bid = str(row[6]) if row[6] is not None else None
        bkind = str(row[8]) if row[8] is not None else None
        tier_info = tier_rank(bid, bkind, priorities_by_bundle)
        if tier_info is None:
            continue
        sort_key, tier = tier_info
        pslug = str(row[7]).strip().lower() if row[7] else None
        raw_pkey = str(row[0])
        norm_slug = raw_pkey.split(":", 1)[-1] if ":" in raw_pkey else raw_pkey
        ranked.append(
            (
                sort_key,
                {
                    "policy_key": raw_pkey,
                    "policy_slug": norm_slug,
                    "uri_pattern": str(row[1]),
                    "connector_scheme": str(row[2]),
                    "required_role": str(row[3]),
                    "approver_team": str(row[4]),
                    "sla_hours": int(row[5]),
                    "pack_bundle_id": bid,
                    "pack_slug": pslug,
                    "resolution_tier": tier,
                },
            )
        )
    ranked.sort(key=lambda pair: pair[0])
    winners: dict[str, dict[str, Any]] = {}
    for _, item in ranked:
        winners.setdefault(item["uri_pattern"], item)
    return tuple(winners.values())


async def load_flat_pack_instructions(
    conn: AsyncConnection,
    resolved_ws: str,
    priorities_by_bundle: dict[str, int],
) -> tuple[dict[str, Any], ...]:
    rows = (
        await conn.execute(
            sa.text(
                "SELECT ci.resource_id, ci.uri, ci.title, ci.metadata_jsonb, "
                "ci.owner_workspace_id::text, ci.pack_bundle_id::text, "
                "dpb.slug, dpb.bundle_kind "
                "FROM catalog_items ci "
                "LEFT JOIN declarative_pack_bundles dpb ON dpb.id = ci.pack_bundle_id "
                "WHERE ci.item_type = 'INSTRUCTION' ORDER BY ci.resource_id ASC"
            )
        )
    ).fetchall()
    ranked: list[tuple[tuple[int, int], dict[str, Any]]] = []
    for row in rows:
        owner_ws = str(row[4]) if row[4] is not None else None
        bid = str(row[5]) if row[5] is not None else None
        bkind = str(row[7]) if row[7] is not None else None
        if bid is None and owner_ws is not None and owner_ws != resolved_ws:
            continue
        tier_info = tier_rank(bid, bkind, priorities_by_bundle)
        if tier_info is None:
            continue
        sort_key, tier = tier_info
        meta = decode_json_dict(row[3])
        pslug = str(row[6]).strip().lower() if row[6] else None
        islug = str(meta.get("slug") or row[2] or row[0]).strip().lower()
        ranked.append(
            (
                sort_key,
                {
                    "resource_id": str(row[0]),
                    "slug": islug,
                    "uri": str(row[1]),
                    "apply_to": str(meta.get("apply_to") or "**/*"),
                    "body_markdown": str(meta.get("body_markdown") or ""),
                    "pack_bundle_id": bid,
                    "pack_slug": pslug,
                    "resolution_tier": tier,
                    "qualified_ref": format_pack_resource_uri(
                        pslug or "workspace",
                        "instructions",
                        islug,
                        workspace_id=resolved_ws if pslug is None else None,
                    ),
                },
            )
        )
    ranked.sort(key=lambda pair: pair[0])
    winners: dict[str, dict[str, Any]] = {}
    for _, item in ranked:
        winners.setdefault(item["slug"], item)
    return tuple(winners.values())


__all__ = [
    "load_flat_broker_policies",
    "load_flat_dna_mechanisms",
    "load_flat_pack_instructions",
]
