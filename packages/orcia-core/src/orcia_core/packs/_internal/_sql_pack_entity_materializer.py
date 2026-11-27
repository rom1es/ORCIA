"""SQL materialization of pack `catalog_items` (`Story 31.2`, `<= 300 L`)."""

from __future__ import annotations

import hashlib
import json
from typing import Any
from uuid import UUID

import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncConnection
from uuid_utils import uuid7

from orcia_core.packs.models import LoadedPackBundleV2, PackReadinessStatus, PackScopeType

_THINKING_MAP = {
    "simple": "simple",
    "fast": "simple",
    "complex": "complex",
    "deep": "complex",
    "reasoning": "complex",
}
_TIER_MAP = {
    "fast": "fast",
    "deep": "deep",
    "discovery": "discovery",
    "simple": "fast",
    "complex": "deep",
}


def _maybe_uuid(raw: str | None) -> UUID | None:
    if not raw:
        return None
    try:
        return UUID(str(raw).strip())
    except (ValueError, TypeError):
        return None


async def ensure_pack_root_org_unit(conn: AsyncConnection) -> UUID:
    """Return existing root `org_units.id` or ensure `orcia-root` exists idempotently."""
    existing = (
        await conn.execute(
            sa.text(
                "SELECT id FROM org_units "
                "ORDER BY (CASE WHEN slug = 'orcia-root' THEN 0 ELSE 1 END), created_at ASC LIMIT 1"
            )
        )
    ).first()
    if existing is not None:
        return UUID(str(existing[0]))
    row = await conn.execute(
        sa.text(
            "INSERT INTO org_units (id, slug, name, unit_type, parent_id) "
            "VALUES (:id, 'orcia-root', 'ORCIA Root Organization', 'ENTERPRISE', NULL) "
            "ON CONFLICT (slug) DO UPDATE SET name = EXCLUDED.name RETURNING id"
        ),
        {"id": UUID(str(uuid7()))},
    )
    return UUID(str(row.scalar_one()))


_SQL_UPSERT_CATALOG_ITEM = sa.text(
    """
    INSERT INTO catalog_items (
        id, resource_id, uri, title, description, resource_type, source_format,
        version, sha256, cas_key, visibility_scope, owner_org_unit_id,
        owner_workspace_id, item_type, metadata_jsonb, pack_bundle_id
    )
    VALUES (
        CAST(:id AS uuid), :resource_id, :uri, :title, :description, :resource_type, 'ORCIA',
        :version, :sha256, :cas_key, :visibility_scope, CAST(:owner_org_unit_id AS uuid),
        CAST(:owner_workspace_id AS uuid), :item_type, CAST(:metadata_jsonb AS jsonb),
        CAST(:pack_bundle_id AS uuid)
    )
    ON CONFLICT (pack_bundle_id, resource_id) WHERE pack_bundle_id IS NOT NULL DO UPDATE SET
        uri = EXCLUDED.uri, title = EXCLUDED.title, description = EXCLUDED.description,
        resource_type = EXCLUDED.resource_type, version = EXCLUDED.version,
        sha256 = EXCLUDED.sha256, cas_key = EXCLUDED.cas_key,
        visibility_scope = EXCLUDED.visibility_scope,
        owner_workspace_id = EXCLUDED.owner_workspace_id,
        item_type = EXCLUDED.item_type, metadata_jsonb = EXCLUDED.metadata_jsonb
    """
)


async def _upsert_catalog_row(
    conn: AsyncConnection,
    ctx: dict[str, str | None],
    *,
    resource_id: str,
    uri: str,
    title: str,
    description: str,
    resource_type: str,
    digest: str,
    item_type: str,
    meta: dict[str, Any],
    version: str | None = None,
) -> None:
    resolved_ver = str(version or ctx["version"] or "1.0.0")[:64]
    await conn.execute(
        _SQL_UPSERT_CATALOG_ITEM,
        {
            "id": str(uuid7()),
            "resource_id": resource_id[:128],
            "uri": uri,
            "title": title[:255],
            "description": description,
            "resource_type": resource_type,
            "version": resolved_ver,
            "sha256": digest,
            "cas_key": f"cas/{digest}",
            "visibility_scope": ctx["col_vis"],
            "owner_org_unit_id": ctx["root_org_id"],
            "owner_workspace_id": ctx["ws_uuid"],
            "item_type": item_type,
            "metadata_jsonb": json.dumps(meta, ensure_ascii=False),
            "pack_bundle_id": ctx["bundle_id"],
        },
    )


async def materialize_pack_catalog_items(
    conn: AsyncConnection,
    *,
    bundle_id: str,
    bundle: LoadedPackBundleV2,
) -> None:
    """Materialize agents, skills, instructions, and help articles into `catalog_items`."""
    m = bundle.manifest
    slug = m.slug.strip()
    pack_id = m.id or f"orcia-pack-{slug}"
    root_org_id = str(await ensure_pack_root_org_unit(conn))
    ws_uuid = (
        str(_maybe_uuid(m.scope_id))
        if m.scope_type == PackScopeType.WORKSPACE and _maybe_uuid(m.scope_id) is not None
        else None
    )
    col_vis = (
        "PUBLISHED_ORG"
        if m.scope_type in (PackScopeType.GLOBAL, PackScopeType.BU)
        else "SHARED_WORKSPACE"
    )
    ctx: dict[str, str | None] = {
        "col_vis": col_vis,
        "root_org_id": root_org_id,
        "ws_uuid": ws_uuid,
        "bundle_id": bundle_id,
        "version": m.version,
    }
    kept_ids: list[str] = []

    for agent in bundle.agents:
        res_id = f"{slug}:{agent.slug}"[:128]
        kept_ids.append(res_id)
        xo_raw = agent.frontmatter.get("x-orcia")
        xo = dict(xo_raw) if isinstance(xo_raw, dict) else {}
        digest = hashlib.sha256(agent.instructions_markdown.encode("utf-8")).hexdigest()
        is_ready = (
            agent.lifecycle_status == PackReadinessStatus.ACTIVE and agent.has_orcia_governance
        )
        agent_meta: dict[str, Any] = {
            "slug": agent.slug,
            "pack_slug": slug,
            "handle": f"@{agent.slug}",
            "qualified_ref": f"@{slug}/{agent.slug}",
            "instructions": agent.instructions_markdown,
            "thinking_level": _THINKING_MAP.get(agent.model_tier.strip().lower(), "medium"),
            "skill_ids": [s if ":" in s else f"{slug}:{s}" for s in agent.skill_refs],
            "visibility_scope": "PACK",
            "source_pack_key": pack_id,
            "enabled_in_workspace": True,
            "mcp_exposed": False,
            "agent_kind": "LOCAL",
            "posture": str(xo.get("posture") or "PRODUCER").upper(),
            "human_partner_role": str(xo.get("human_partner_role") or "PO_PM").upper(),
            "llm_model_tier": _TIER_MAP.get(agent.model_tier.strip().lower(), "team_default"),
            "connector_slots": list(agent.connector_slots),
            "lifecycle_status": agent.lifecycle_status.value,
            "test_bench_status": "PASSED" if is_ready else "UNTESTED",
            "test_bench_validated": is_ready,
            "owner_workspace_id": ws_uuid,
        }
        await _upsert_catalog_row(
            conn,
            ctx,
            resource_id=res_id,
            uri=f"orcia://packs/{slug}/agents/{agent.slug}@{m.version}",
            title=agent.name,
            description=agent.description or agent.name,
            resource_type="agent",
            digest=digest,
            item_type="USER_AGENT",
            meta=agent_meta,
        )

    for skill in bundle.skills:
        res_id = f"{slug}:{skill.slug}"[:128]
        kept_ids.append(res_id)
        digest = hashlib.sha256(skill.instructions_markdown.encode("utf-8")).hexdigest()
        cmd = (
            skill.command_handle
            if skill.command_handle.startswith("/")
            else f"/{skill.command_handle or skill.slug}"
        )
        params = [
            str(p.get("name") or p) if isinstance(p, dict) else str(p)
            for p in skill.input_parameters
        ]
        skill_meta: dict[str, Any] = {
            "slug": skill.slug,
            "pack_slug": slug,
            "command_handle": cmd,
            "qualified_ref": f"/{slug}/{skill.slug}",
            "input_parameters": params,
            "instructions": skill.instructions_markdown,
            "visibility_scope": "PACK",
            "source_pack_key": pack_id,
            "enabled_in_workspace": True,
            "is_si_write": skill.is_si_write,
            "human_authored_required": skill.human_authored_required,
            "lifecycle_status": skill.lifecycle_status.value,
            "owner_workspace_id": ws_uuid,
        }
        await _upsert_catalog_row(
            conn,
            ctx,
            resource_id=res_id,
            uri=f"orcia://packs/{slug}/skills/{skill.slug}@{m.version}",
            title=skill.name,
            description=skill.description or skill.name,
            resource_type="skill",
            digest=digest,
            item_type="USER_SKILL",
            meta=skill_meta,
        )

    for instr in bundle.instructions:
        res_id = f"{slug}:instr:{instr.slug}"[:128]
        kept_ids.append(res_id)
        digest = hashlib.sha256(instr.body_markdown.encode("utf-8")).hexdigest()
        await _upsert_catalog_row(
            conn,
            ctx,
            resource_id=res_id,
            uri=f"orcia://packs/{slug}/instructions/{instr.slug}@{m.version}",
            title=instr.slug,
            description=instr.description or instr.apply_to,
            resource_type="template",
            digest=digest,
            item_type="INSTRUCTION",
            meta={
                "slug": instr.slug,
                "apply_to": instr.apply_to,
                "body_markdown": instr.body_markdown,
                "source_pack_key": pack_id,
            },
        )
    for art in bundle.help_articles:
        suffix = f"-{art.lang}"
        res_id = (
            art.slug if art.slug.endswith((suffix, f":{art.lang}")) else f"{art.slug}{suffix}"
        )[:128]
        kept_ids.append(res_id)
        digest = hashlib.sha256(art.body_markdown.encode("utf-8")).hexdigest()
        summary = str(art.frontmatter.get("summary_what_for") or art.title or art.slug)
        uri = str(art.frontmatter.get("uri") or f"orcia://packs/{slug}/help/{art.slug}/{art.lang}")
        await _upsert_catalog_row(
            conn,
            ctx,
            resource_id=res_id,
            uri=uri,
            title=art.title or art.slug,
            description=summary,
            resource_type="template",
            digest=digest,
            item_type="HELP_ARTICLE",
            version=str(art.frontmatter.get("version") or m.version),
            meta={
                "lang": art.lang,
                "layer": "PACK",
                "pack_name": pack_id,
                "bound_routes": list(art.bound_routes),
                "summary_what_for": summary,
                "markdown_body": art.body_markdown,
            },
        )

    await conn.execute(
        sa.text(
            "DELETE FROM catalog_items WHERE pack_bundle_id = CAST(:bid AS uuid) "
            "AND NOT (resource_id = ANY(:kept))"
        ),
        {"bid": bundle_id, "kept": kept_ids},
    )


__all__ = ["ensure_pack_root_org_unit", "materialize_pack_catalog_items"]
