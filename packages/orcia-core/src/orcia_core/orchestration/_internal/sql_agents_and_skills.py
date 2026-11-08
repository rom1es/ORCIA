"""PostgreSQL 18 SQL Adapter for User-Created Agents & Skills (`catalog_items`).

Persists user-created Skills (`resource_type='skill'`, `item_type='USER_SKILL'`) and Agents
(`resource_type='agent'`, `item_type='USER_AGENT'`) in `catalog_items` with full `metadata_jsonb`.
"""

from __future__ import annotations

import json
from typing import cast
from uuid import UUID

import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncConnection, AsyncEngine

from orcia_core.orchestration.agents_and_skills_models import (
    AgentKindType,
    AgentSkillVisibilityScope,
    AgentThinkingLevel,
    ManagedAgentRecord,
    ManagedSkillRecord,
)
from orcia_kernel.ids import new_uuid7_str


async def _ensure_root_org_unit_id(conn: AsyncConnection) -> UUID:
    """Return an existing root `org_units.id` or create `orcia-root` idempotently."""
    existing = (
        await conn.execute(
            sa.text(
                """
                SELECT id FROM org_units
                ORDER BY (CASE WHEN slug = 'orcia-root' THEN 0 ELSE 1 END), created_at ASC
                LIMIT 1
                """
            )
        )
    ).first()
    if existing is not None:
        return UUID(str(existing[0]))

    row = await conn.execute(
        sa.text(
            """
            INSERT INTO org_units (id, slug, name, unit_type, parent_id)
            VALUES (:id, 'orcia-root', 'ORCIA Root Organization', 'ENTERPRISE', NULL)
            ON CONFLICT (slug) DO UPDATE SET name = EXCLUDED.name
            RETURNING id
            """
        ),
        {"id": UUID(new_uuid7_str())},
    )
    return UUID(str(row.scalar_one()))


def _parse_visibility_scope(raw_val: object) -> AgentSkillVisibilityScope:
    val = str(raw_val or "TEAM").upper()
    if val in ("PRIVATE", "TEAM", "PACK"):
        return cast(AgentSkillVisibilityScope, val)
    return "TEAM"


def _parse_agent_kind(raw_val: object) -> AgentKindType:
    val = str(raw_val or "LOCAL").upper()
    if val in ("LOCAL", "REMOTE_MCP_A2A"):
        return cast(AgentKindType, val)
    return "LOCAL"


async def load_agents_and_skills_from_postgres18(
    engine: AsyncEngine,
) -> tuple[tuple[ManagedSkillRecord, ...], tuple[ManagedAgentRecord, ...]]:
    """Load all `USER_SKILL` and `USER_AGENT` records from PostgreSQL 18 `catalog_items`."""
    skills: list[ManagedSkillRecord] = []
    agents: list[ManagedAgentRecord] = []
    async with engine.connect() as conn:
        rows = (
            await conn.execute(
                sa.text(
                    """
                    SELECT resource_id, uri, title, description, resource_type, version,
                           sha256, item_type, metadata_jsonb
                    FROM catalog_items
                    WHERE item_type IN ('USER_SKILL', 'USER_AGENT')
                    ORDER BY created_at ASC, resource_id ASC
                    """
                )
            )
        ).fetchall()

    for row in rows:
        resource_id = str(row[0])
        uri = str(row[1])
        title = str(row[2])
        description = str(row[3])
        version = str(row[5])
        sha256 = str(row[6])
        item_type = str(row[7])
        raw_meta = row[8]
        meta = raw_meta if isinstance(raw_meta, dict) else json.loads(str(raw_meta or "{}"))
        slug = str(meta.get("slug") or resource_id)
        vis_scope = _parse_visibility_scope(meta.get("visibility_scope"))
        raw_pack = meta.get("source_pack_key")
        source_pack_key = str(raw_pack).strip() if raw_pack else None
        enabled_in_workspace = bool(meta.get("enabled_in_workspace", True))

        if item_type == "USER_SKILL":
            raw_params = meta.get("input_parameters") or []
            params = tuple(str(p) for p in raw_params if str(p).strip())
            skills.append(
                ManagedSkillRecord(
                    skill_id=resource_id,
                    slug=slug,
                    command_handle=str(meta.get("command_handle") or f"/{slug}"),
                    uri=uri,
                    name=title,
                    objective=description,
                    input_parameters=params,
                    instructions=str(meta.get("instructions") or ""),
                    expected_output_format=str(
                        meta.get("expected_output_format") or "Synthèse structurée"
                    ),
                    version=version,
                    sha256=sha256,
                    visibility_scope=vis_scope,
                    source_pack_key=source_pack_key,
                    enabled_in_workspace=enabled_in_workspace,
                )
            )
        elif item_type == "USER_AGENT":
            raw_skills = meta.get("skill_ids") or []
            skill_ids = tuple(str(s) for s in raw_skills if str(s).strip())
            raw_level = str(meta.get("thinking_level") or "medium")
            thinking_level: AgentThinkingLevel = (
                cast(AgentThinkingLevel, raw_level)
                if raw_level in ("simple", "medium", "complex", "auto")
                else "medium"
            )
            raw_remote = meta.get("remote_endpoint_url")
            remote_endpoint_url = str(raw_remote).strip() if raw_remote else None
            agents.append(
                ManagedAgentRecord(
                    agent_id=resource_id,
                    slug=slug,
                    handle=str(meta.get("handle") or f"@{slug}"),
                    uri=uri,
                    name=title,
                    role_mission=description,
                    instructions=str(meta.get("instructions") or ""),
                    thinking_level=thinking_level,
                    skill_ids=skill_ids,
                    version=version,
                    sha256=sha256,
                    visibility_scope=vis_scope,
                    source_pack_key=source_pack_key,
                    enabled_in_workspace=enabled_in_workspace,
                    mcp_exposed=bool(meta.get("mcp_exposed", False)),
                    agent_kind=_parse_agent_kind(meta.get("agent_kind")),
                    remote_endpoint_url=remote_endpoint_url,
                )
            )

    return tuple(skills), tuple(agents)


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
    }
    async with engine.begin() as conn:
        org_id = await _ensure_root_org_unit_id(conn)
        await conn.execute(
            sa.text(
                """
                INSERT INTO catalog_items (
                    id, resource_id, uri, title, description, resource_type,
                    source_format, version, sha256, cas_key, visibility_scope,
                    owner_org_unit_id, item_type, metadata_jsonb
                )
                VALUES (
                    :id, :resource_id, :uri, :title, :description, 'skill',
                    'ORCIA', :version, :sha256, :cas_key, 'SHARED_WORKSPACE',
                    :owner_org_unit_id, 'USER_SKILL', CAST(:metadata_jsonb AS jsonb)
                )
                ON CONFLICT (resource_id) DO UPDATE SET
                    uri = EXCLUDED.uri,
                    title = EXCLUDED.title,
                    description = EXCLUDED.description,
                    version = EXCLUDED.version,
                    sha256 = EXCLUDED.sha256,
                    cas_key = EXCLUDED.cas_key,
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
    }
    async with engine.begin() as conn:
        org_id = await _ensure_root_org_unit_id(conn)
        await conn.execute(
            sa.text(
                """
                INSERT INTO catalog_items (
                    id, resource_id, uri, title, description, resource_type,
                    source_format, version, sha256, cas_key, visibility_scope,
                    owner_org_unit_id, item_type, metadata_jsonb
                )
                VALUES (
                    :id, :resource_id, :uri, :title, :description, 'agent',
                    'ORCIA', :version, :sha256, :cas_key, 'SHARED_WORKSPACE',
                    :owner_org_unit_id, 'USER_AGENT', CAST(:metadata_jsonb AS jsonb)
                )
                ON CONFLICT (resource_id) DO UPDATE SET
                    uri = EXCLUDED.uri,
                    title = EXCLUDED.title,
                    description = EXCLUDED.description,
                    version = EXCLUDED.version,
                    sha256 = EXCLUDED.sha256,
                    cas_key = EXCLUDED.cas_key,
                    item_type = EXCLUDED.item_type,
                    metadata_jsonb = EXCLUDED.metadata_jsonb
                """
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
                "metadata_jsonb": json.dumps(meta, ensure_ascii=False),
            },
        )


async def delete_skill_from_postgres18(
    engine: AsyncEngine,
    skill_id: str,
    updated_agents: tuple[ManagedAgentRecord, ...],
) -> None:
    """Delete a Skill from PostgreSQL 18 `catalog_items` and update detached Agents."""
    async with engine.begin() as conn:
        await conn.execute(
            sa.text(
                """
                DELETE FROM catalog_items
                WHERE resource_id = :resource_id AND item_type = 'USER_SKILL'
                """
            ),
            {"resource_id": skill_id},
        )
    for agent in updated_agents:
        await persist_agent_to_postgres18(engine, agent)


async def delete_agent_from_postgres18(
    engine: AsyncEngine,
    agent_id: str,
) -> None:
    """Delete an Agent from PostgreSQL 18 `catalog_items`."""
    async with engine.begin() as conn:
        await conn.execute(
            sa.text(
                """
                DELETE FROM catalog_items
                WHERE resource_id = :resource_id AND item_type = 'USER_AGENT'
                """
            ),
            {"resource_id": agent_id},
        )
