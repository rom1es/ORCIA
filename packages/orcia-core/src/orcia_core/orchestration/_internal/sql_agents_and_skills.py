"""PostgreSQL 18 SQL Adapter for User-Created Agents & Skills (`catalog_items`, `<= 300 L`)."""

from __future__ import annotations

import json
from uuid import UUID

import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncEngine

from orcia_core.orchestration._agents_namespacing import annotate_skills_and_agents_namespacing
from orcia_core.orchestration._internal._sql_agents_delete import (
    CatalogAuthCallback,
    delete_agent_from_postgres18,
    delete_skill_with_agent_sync,
)
from orcia_core.orchestration._internal._sql_agents_hydration import (
    hydrate_agent_record,
    hydrate_skill_record,
    parse_visibility_scope,
)
from orcia_core.orchestration._internal._sql_agents_pack_queries import (
    SQL_LOAD_AGENTS_AND_SKILLS_WITH_PACKS,
    load_workspace_pack_priorities_pg,
    resolve_pack_tier_for_row,
)
from orcia_core.orchestration._internal._sql_agents_pack_queries import (
    ensure_root_org_unit_id as _ensure_root_org_unit_id,
)
from orcia_core.orchestration._internal._sql_agents_pack_queries import (
    optional_uuid as _optional_uuid,
)
from orcia_core.orchestration.agents_and_skills_models import (
    ManagedAgentRecord,
    ManagedSkillRecord,
)
from orcia_core.storage.pack_draft_guard import DraftAuthCallback
from orcia_kernel.ids import new_uuid7_str


async def load_agents_and_skills_from_postgres18(
    engine: AsyncEngine,
    workspace_id: str | None = None,
) -> tuple[tuple[ManagedSkillRecord, ...], tuple[ManagedAgentRecord, ...]]:
    """Load all `USER_SKILL` and `USER_AGENT` records from PostgreSQL 18 `catalog_items`."""
    skills: list[ManagedSkillRecord] = []
    agents: list[ManagedAgentRecord] = []
    async with engine.connect() as conn:
        active_priorities, inactive_packs = await load_workspace_pack_priorities_pg(
            conn, workspace_id
        )
        rows = (await conn.execute(SQL_LOAD_AGENTS_AND_SKILLS_WITH_PACKS)).fetchall()

    for row in rows:
        resource_id, uri, title, description = str(row[0]), str(row[1]), str(row[2]), str(row[3])
        version, sha256, item_type, raw_meta = str(row[5]), str(row[6]), str(row[7]), row[8]
        col_ws = str(row[9]) if len(row) > 9 and row[9] is not None else None
        pack_slug = str(row[10]).strip().lower() if len(row) > 10 and row[10] else None
        bundle_kind = str(row[11]).strip().upper() if len(row) > 11 and row[11] else None
        meta = raw_meta if isinstance(raw_meta, dict) else json.loads(str(raw_meta or "{}"))
        slug = str(meta.get("slug") or resource_id)
        vis_scope = parse_visibility_scope(meta.get("visibility_scope"))
        raw_pack = meta.get("source_pack_key")
        source_pack_key = str(raw_pack).strip() if raw_pack else None
        enabled_in_workspace = bool(meta.get("enabled_in_workspace", True))
        if pack_slug and pack_slug in inactive_packs:
            enabled_in_workspace = False
        tier = resolve_pack_tier_for_row(
            pack_slug=pack_slug, bundle_kind=bundle_kind, active_priorities=active_priorities
        )

        if item_type == "USER_SKILL":
            skills.append(
                hydrate_skill_record(
                    resource_id=resource_id,
                    uri=uri,
                    title=title,
                    description=description,
                    version=version,
                    sha256=sha256,
                    meta=meta,
                    slug=slug,
                    vis_scope=vis_scope,
                    source_pack_key=source_pack_key,
                    enabled_in_workspace=enabled_in_workspace,
                    column_workspace_id=col_ws,
                    pack_slug=pack_slug,
                    bundle_kind=bundle_kind,
                    resolution_tier=tier,
                )
            )
        elif item_type == "USER_AGENT":
            agents.append(
                hydrate_agent_record(
                    resource_id=resource_id,
                    uri=uri,
                    title=title,
                    description=description,
                    version=version,
                    sha256=sha256,
                    meta=meta,
                    slug=slug,
                    vis_scope=vis_scope,
                    source_pack_key=source_pack_key,
                    enabled_in_workspace=enabled_in_workspace,
                    column_workspace_id=col_ws,
                    pack_slug=pack_slug,
                    bundle_kind=bundle_kind,
                    resolution_tier=tier,
                )
            )

    return annotate_skills_and_agents_namespacing(
        tuple(skills), tuple(agents), active_pack_priorities=active_priorities or None
    )


async def persist_skill_to_postgres18(
    engine: AsyncEngine,
    skill: ManagedSkillRecord,
) -> None:
    """Upsert a `ManagedSkillRecord` into PostgreSQL 18 `catalog_items`."""
    meta = {
        "slug": skill.slug,
        "command_handle": skill.command_handle,
        "input_parameters": list(skill.input_parameters),
        "instructions": skill.instructions,
        "expected_output_format": skill.expected_output_format,
        "visibility_scope": skill.visibility_scope,
        "source_pack_key": skill.source_pack_key,
        "enabled_in_workspace": skill.enabled_in_workspace,
        "is_si_write": skill.is_si_write,
        "human_authored_required": skill.human_authored_required,
        "owner_workspace_id": skill.owner_workspace_id,
        "owner_user_id": skill.owner_user_id,
        "pack_slug": skill.pack_slug,
    }
    async with engine.begin() as conn:
        org_id = await _ensure_root_org_unit_id(conn)
        await conn.execute(
            sa.text(
                """
                INSERT INTO catalog_items (
                    id, resource_id, uri, title, description, resource_type,
                    source_format, version, sha256, cas_key, visibility_scope,
                    owner_org_unit_id, owner_workspace_id, item_type, metadata_jsonb
                )
                VALUES (
                    :id, :resource_id, :uri, :title, :description, 'skill',
                    'ORCIA', :version, :sha256, :cas_key, 'SHARED_WORKSPACE',
                    :owner_org_unit_id, :owner_workspace_id, 'USER_SKILL',
                    CAST(:metadata_jsonb AS jsonb)
                )
                ON CONFLICT (resource_id) WHERE pack_bundle_id IS NULL DO UPDATE SET
                    uri = EXCLUDED.uri,
                    title = EXCLUDED.title,
                    description = EXCLUDED.description,
                    version = EXCLUDED.version,
                    sha256 = EXCLUDED.sha256,
                    cas_key = EXCLUDED.cas_key,
                    owner_workspace_id = COALESCE(
                        EXCLUDED.owner_workspace_id, catalog_items.owner_workspace_id
                    ),
                    item_type = EXCLUDED.item_type,
                    metadata_jsonb = EXCLUDED.metadata_jsonb
                """
            ),
            {
                "id": UUID(new_uuid7_str()),
                "resource_id": skill.skill_id,
                "uri": skill.uri,
                "title": skill.name,
                "description": skill.objective,
                "version": skill.version,
                "sha256": skill.sha256,
                "cas_key": f"cas/{skill.sha256}",
                "owner_org_unit_id": org_id,
                "owner_workspace_id": _optional_uuid(skill.owner_workspace_id),
                "metadata_jsonb": json.dumps(meta, ensure_ascii=False),
            },
        )


async def persist_agent_to_postgres18(
    engine: AsyncEngine,
    agent: ManagedAgentRecord,
) -> None:
    """Upsert a `ManagedAgentRecord` into PostgreSQL 18 `catalog_items`."""
    meta = {
        "slug": agent.slug,
        "handle": agent.handle,
        "instructions": agent.instructions,
        "thinking_level": agent.thinking_level,
        "skill_ids": list(agent.skill_ids),
        "visibility_scope": agent.visibility_scope,
        "source_pack_key": agent.source_pack_key,
        "enabled_in_workspace": agent.enabled_in_workspace,
        "mcp_exposed": agent.mcp_exposed,
        "agent_kind": agent.agent_kind,
        "remote_endpoint_url": agent.remote_endpoint_url,
        "posture": agent.posture,
        "human_partner_role": agent.human_partner_role,
        "llm_model_tier": agent.llm_model_tier,
        "temperature": agent.temperature,
        "max_tokens": agent.max_tokens,
        "prompt_ref": agent.prompt_ref,
        "invocation_modes": list(agent.invocation_modes),
        "dialogue_mechanism": agent.dialogue_mechanism,
        "allowed_rag_sources": list(agent.allowed_rag_sources),
        "ontology_views": list(agent.ontology_views),
        "mcp_tool_permissions": dict(agent.mcp_tool_permissions),
        "guardrails": list(agent.guardrails),
        "output_contract_format": agent.output_contract_format,
        "write_preview_required": agent.write_preview_required,
        "test_bench_validated": agent.test_bench_validated,
        "lifecycle_status": agent.lifecycle_status,
        "test_bench_status": agent.test_bench_status,
        "owner_workspace_id": agent.owner_workspace_id,
        "owner_user_id": agent.owner_user_id,
        "pack_slug": agent.pack_slug,
    }
    async with engine.begin() as conn:
        org_id = await _ensure_root_org_unit_id(conn)
        await conn.execute(
            sa.text(
                "INSERT INTO catalog_items (id, resource_id, uri, title, description, "
                "resource_type, source_format, version, sha256, cas_key, visibility_scope, "
                "owner_org_unit_id, owner_workspace_id, item_type, metadata_jsonb) "
                "VALUES (:id, :resource_id, :uri, :title, :description, 'agent', 'ORCIA', "
                ":version, :sha256, :cas_key, 'SHARED_WORKSPACE', :owner_org_unit_id, "
                ":owner_workspace_id, 'USER_AGENT', CAST(:metadata_jsonb AS jsonb)) "
                "ON CONFLICT (resource_id) WHERE pack_bundle_id IS NULL DO UPDATE SET "
                "uri = EXCLUDED.uri, title = EXCLUDED.title, description = EXCLUDED.description, "
                "version = EXCLUDED.version, sha256 = EXCLUDED.sha256, cas_key = EXCLUDED.cas_key, "
                "owner_workspace_id = COALESCE("
                "EXCLUDED.owner_workspace_id, catalog_items.owner_workspace_id), "
                "item_type = EXCLUDED.item_type, metadata_jsonb = EXCLUDED.metadata_jsonb"
            ),
            {
                "id": UUID(new_uuid7_str()),
                "resource_id": agent.agent_id,
                "uri": agent.uri,
                "title": agent.name,
                "description": agent.role_mission,
                "version": agent.version,
                "sha256": agent.sha256,
                "cas_key": f"cas/{agent.sha256}",
                "owner_org_unit_id": org_id,
                "owner_workspace_id": _optional_uuid(agent.owner_workspace_id),
                "metadata_jsonb": json.dumps(meta, ensure_ascii=False),
            },
        )


async def delete_skill_from_postgres18(
    engine: AsyncEngine,
    skill_id: str,
    updated_agents: tuple[ManagedAgentRecord, ...],
    *,
    unlink_from_draft_packs: bool = False,
    authorize_target_cb: CatalogAuthCallback | None = None,
    authorize_draft_cb: DraftAuthCallback | None = None,
    actor_id: str = "system",
    actor_email: str | None = None,
    trace_id: str | None = None,
    instance: str | None = None,
) -> list[dict[str, str]]:
    """Delete a Skill from PG18 `catalog_items` and detach Agents atomically."""
    found, unlinked = await delete_skill_with_agent_sync(
        engine,
        skill_id,
        updated_agents,
        unlink_from_draft_packs=unlink_from_draft_packs,
        authorize_target_cb=authorize_target_cb,
        authorize_draft_cb=authorize_draft_cb,
        actor_id=actor_id,
        actor_email=actor_email,
        trace_id=trace_id,
        instance=instance,
    )
    if not found:
        for agent in updated_agents:
            await persist_agent_to_postgres18(engine, agent)
    return unlinked


__all__ = [
    "delete_agent_from_postgres18",
    "delete_skill_from_postgres18",
    "load_agents_and_skills_from_postgres18",
    "persist_agent_to_postgres18",
    "persist_skill_to_postgres18",
]
