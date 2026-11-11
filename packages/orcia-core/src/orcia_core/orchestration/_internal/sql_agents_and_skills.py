"""PostgreSQL 18 SQL Adapter for User-Created Agents & Skills (`catalog_items`).

Persists user-created Skills (`resource_type='skill'`, `item_type='USER_SKILL'`) and Agents
(`resource_type='agent'`, `item_type='USER_AGENT'`) in `catalog_items` with full `metadata_jsonb`
including the 6 ORCIA Agent Governance Blocks.
"""

from __future__ import annotations

import json
from typing import cast
from uuid import UUID

import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncConnection, AsyncEngine

from orcia_core.orchestration.agents_and_skills_models import (
    DEFAULT_ALLOWED_RAG_SOURCES,
    DEFAULT_GUARDRAILS,
    DEFAULT_INVOCATION_MODES,
    DEFAULT_MCP_TOOL_PERMISSIONS,
    DEFAULT_ONTOLOGY_VIEWS,
    AgentDialogueMechanism,
    AgentHumanPartnerRole,
    AgentKindType,
    AgentLlmModelTier,
    AgentOutputContractFormat,
    AgentPostureType,
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


def _parse_str_tuple(raw_val: object, default: tuple[str, ...]) -> tuple[str, ...]:
    if not isinstance(raw_val, list):
        return default
    cleaned = tuple(str(item).strip() for item in raw_val if str(item).strip())
    return cleaned or default


def _parse_mcp_perms(raw_val: object) -> tuple[tuple[str, str], ...]:
    if isinstance(raw_val, dict):
        return tuple((str(k).strip(), str(v).strip()) for k, v in raw_val.items() if str(k).strip())
    return DEFAULT_MCP_TOOL_PERMISSIONS


def _hydrate_agent_record(
    *,
    resource_id: str,
    uri: str,
    title: str,
    description: str,
    version: str,
    sha256: str,
    meta: dict[str, object],
    slug: str,
    vis_scope: AgentSkillVisibilityScope,
    source_pack_key: str | None,
    enabled_in_workspace: bool,
) -> ManagedAgentRecord:
    raw_skills = meta.get("skill_ids") or []
    skill_ids = (
        tuple(str(s) for s in raw_skills if str(s).strip()) if isinstance(raw_skills, list) else ()
    )
    raw_level = str(meta.get("thinking_level") or "medium")
    thinking_level: AgentThinkingLevel = (
        cast(AgentThinkingLevel, raw_level)
        if raw_level in ("simple", "medium", "complex", "auto")
        else "medium"
    )
    raw_remote = meta.get("remote_endpoint_url")
    remote_endpoint_url = str(raw_remote).strip() if raw_remote else None
    raw_posture = str(meta.get("posture") or "PRODUCER").upper()
    posture: AgentPostureType = (
        cast(AgentPostureType, raw_posture)
        if raw_posture in ("PRODUCER", "EVALUATOR_GATE")
        else "PRODUCER"
    )
    raw_partner = str(meta.get("human_partner_role") or "PO_PM").upper()
    human_partner_role: AgentHumanPartnerRole = (
        cast(AgentHumanPartnerRole, raw_partner)
        if raw_partner in ("PO_PM", "ARCHITECT", "TECH_LEAD", "SECURITY_QA", "ALL")
        else "PO_PM"
    )
    raw_tier = str(meta.get("llm_model_tier") or "team_default")
    llm_model_tier: AgentLlmModelTier = (
        cast(AgentLlmModelTier, raw_tier)
        if raw_tier in ("team_default", "fast", "deep", "discovery")
        else "team_default"
    )
    raw_dialogue = str(meta.get("dialogue_mechanism") or "questionnaire_prealable")
    dialogue_mechanism: AgentDialogueMechanism = (
        cast(AgentDialogueMechanism, raw_dialogue)
        if raw_dialogue in ("questionnaire_prealable", "pause_par_bloc", "direct")
        else "questionnaire_prealable"
    )
    raw_fmt = str(meta.get("output_contract_format") or "markdown_structure")
    output_contract_format: AgentOutputContractFormat = (
        cast(AgentOutputContractFormat, raw_fmt)
        if raw_fmt in ("markdown_structure", "confluence_draft", "jira_draft", "gate_risk_json")
        else "markdown_structure"
    )
    raw_prompt_ref = meta.get("prompt_ref")
    default_temp = 0.0 if posture == "EVALUATOR_GATE" else 0.2
    raw_temp = meta.get("temperature")
    temperature = float(str(raw_temp)) if raw_temp is not None else default_temp
    raw_tokens = meta.get("max_tokens")
    max_tokens = int(str(raw_tokens)) if raw_tokens is not None else 4096

    return ManagedAgentRecord(
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
        posture=posture,
        human_partner_role=human_partner_role,
        llm_model_tier=llm_model_tier,
        temperature=temperature,
        max_tokens=max_tokens,
        prompt_ref=str(raw_prompt_ref).strip() if raw_prompt_ref else None,
        invocation_modes=_parse_str_tuple(meta.get("invocation_modes"), DEFAULT_INVOCATION_MODES),
        dialogue_mechanism=dialogue_mechanism,
        allowed_rag_sources=_parse_str_tuple(
            meta.get("allowed_rag_sources"), DEFAULT_ALLOWED_RAG_SOURCES
        ),
        ontology_views=_parse_str_tuple(meta.get("ontology_views"), DEFAULT_ONTOLOGY_VIEWS),
        mcp_tool_permissions=_parse_mcp_perms(meta.get("mcp_tool_permissions")),
        guardrails=_parse_str_tuple(meta.get("guardrails"), DEFAULT_GUARDRAILS),
        output_contract_format=output_contract_format,
        write_preview_required=bool(meta.get("write_preview_required", True)),
        test_bench_validated=bool(meta.get("test_bench_validated", False)),
    )


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
        resource_id, uri, title, description = str(row[0]), str(row[1]), str(row[2]), str(row[3])
        version, sha256, item_type, raw_meta = str(row[5]), str(row[6]), str(row[7]), row[8]
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
            agents.append(
                _hydrate_agent_record(
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
