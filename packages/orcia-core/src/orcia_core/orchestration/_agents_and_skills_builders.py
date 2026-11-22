"""Deterministic Record Builders & Execution Formatters for Agents & Skills (`<= 300 L`).

Extracted from `agents_and_skills_models.py` (`AD-19`, zero framework imports).
"""

from __future__ import annotations

from orcia_core.orchestration._agents_and_skills_outcomes import (
    rebuild_agent_with_skills,
)
from orcia_core.orchestration._agents_and_skills_types import (
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
    compute_payload_sha256,
)


def build_managed_skill_record(
    *,
    resolved_id: str,
    slug: str,
    clean_name: str,
    clean_obj: str,
    params: tuple[str, ...],
    clean_inst: str,
    clean_fmt: str,
    version: str,
    existing: ManagedSkillRecord | None,
    visibility_scope: AgentSkillVisibilityScope | None,
    source_pack_key: str | None,
    enabled_in_workspace: bool | None,
    is_si_write: bool | None = None,
    human_authored_required: bool | None = None,
    owner_workspace_id: str | None = None,
    owner_user_id: str | None = None,
) -> ManagedSkillRecord:
    """Construct a `ManagedSkillRecord` with deterministic SHA-256 digest."""
    scope = visibility_scope or (existing.visibility_scope if existing else "TEAM")
    pack = (
        source_pack_key
        if source_pack_key is not None
        else (existing.source_pack_key if existing else None)
    )
    enabled = (
        enabled_in_workspace
        if enabled_in_workspace is not None
        else (existing.enabled_in_workspace if existing else True)
    )
    si_write = (
        bool(is_si_write)
        if is_si_write is not None
        else (existing.is_si_write if existing else False)
    )
    human_req = (
        bool(human_authored_required)
        if human_authored_required is not None
        else (existing.human_authored_required if existing else False)
    )
    ws_owner = (
        owner_workspace_id
        if owner_workspace_id is not None
        else (existing.owner_workspace_id if existing else None)
    )
    user_owner = (
        owner_user_id
        if owner_user_id is not None
        else (existing.owner_user_id if existing else None)
    )
    digest = compute_payload_sha256(
        {
            "skill_id": resolved_id,
            "slug": slug,
            "name": clean_name,
            "objective": clean_obj,
            "input_parameters": list(params),
            "instructions": clean_inst,
            "expected_output_format": clean_fmt,
            "version": version,
            "visibility_scope": scope,
            "source_pack_key": pack,
            "enabled_in_workspace": enabled,
            "is_si_write": si_write,
            "human_authored_required": human_req,
        }
    )
    return ManagedSkillRecord(
        skill_id=resolved_id,
        slug=slug,
        command_handle=f"/{slug}",
        uri=f"orcia://skills/{slug}@{version}",
        name=clean_name,
        objective=clean_obj,
        input_parameters=params,
        instructions=clean_inst,
        expected_output_format=clean_fmt,
        version=version,
        sha256=digest,
        visibility_scope=scope,
        source_pack_key=pack,
        enabled_in_workspace=enabled,
        is_si_write=si_write,
        human_authored_required=human_req,
        owner_workspace_id=ws_owner,
        owner_user_id=user_owner,
    )


def build_managed_agent_record(
    *,
    resolved_id: str,
    slug: str,
    clean_name: str,
    clean_role: str,
    clean_inst: str,
    thinking_level: AgentThinkingLevel,
    valid_skills: tuple[str, ...],
    version: str,
    existing: ManagedAgentRecord | None,
    visibility_scope: AgentSkillVisibilityScope | None,
    source_pack_key: str | None,
    enabled_in_workspace: bool | None,
    mcp_exposed: bool | None,
    agent_kind: AgentKindType | None,
    remote_endpoint_url: str | None,
    posture: AgentPostureType | None = None,
    human_partner_role: AgentHumanPartnerRole | None = None,
    llm_model_tier: AgentLlmModelTier | None = None,
    temperature: float | None = None,
    max_tokens: int | None = None,
    prompt_ref: str | None = None,
    invocation_modes: tuple[str, ...] | None = None,
    dialogue_mechanism: AgentDialogueMechanism | None = None,
    allowed_rag_sources: tuple[str, ...] | None = None,
    ontology_views: tuple[str, ...] | None = None,
    mcp_tool_permissions: tuple[tuple[str, str], ...] | None = None,
    guardrails: tuple[str, ...] | None = None,
    output_contract_format: AgentOutputContractFormat | None = None,
    write_preview_required: bool | None = None,
    test_bench_validated: bool | None = None,
    owner_workspace_id: str | None = None,
    owner_user_id: str | None = None,
) -> ManagedAgentRecord:
    """Construct a `ManagedAgentRecord` with deterministic SHA-256 digest."""
    resolved_posture: AgentPostureType = posture or (existing.posture if existing else "PRODUCER")
    default_temp = 0.0 if resolved_posture == "EVALUATOR_GATE" else 0.2
    base = ManagedAgentRecord(
        agent_id=resolved_id,
        slug=slug,
        handle=f"@{slug}",
        uri=f"orcia://agents/{slug}@{version}",
        name=clean_name,
        role_mission=clean_role,
        instructions=clean_inst,
        thinking_level=thinking_level,
        skill_ids=valid_skills,
        version=version,
        visibility_scope=visibility_scope or (existing.visibility_scope if existing else "TEAM"),
        source_pack_key=(
            source_pack_key
            if source_pack_key is not None
            else (existing.source_pack_key if existing else None)
        ),
        enabled_in_workspace=(
            enabled_in_workspace
            if enabled_in_workspace is not None
            else (existing.enabled_in_workspace if existing else True)
        ),
        mcp_exposed=(
            mcp_exposed
            if mcp_exposed is not None
            else (existing.mcp_exposed if existing else False)
        ),
        agent_kind=agent_kind or (existing.agent_kind if existing else "LOCAL"),
        remote_endpoint_url=(
            remote_endpoint_url
            if remote_endpoint_url is not None
            else (existing.remote_endpoint_url if existing else None)
        ),
        posture=resolved_posture,
        human_partner_role=(
            human_partner_role or (existing.human_partner_role if existing else "PO_PM")
        ),
        llm_model_tier=(
            llm_model_tier or (existing.llm_model_tier if existing else "team_default")
        ),
        temperature=(
            temperature
            if temperature is not None
            else (existing.temperature if existing else default_temp)
        ),
        max_tokens=(
            max_tokens if max_tokens is not None else (existing.max_tokens if existing else 4096)
        ),
        prompt_ref=prompt_ref
        if prompt_ref is not None
        else (existing.prompt_ref if existing else None),
        invocation_modes=(
            invocation_modes
            if invocation_modes is not None
            else (existing.invocation_modes if existing else DEFAULT_INVOCATION_MODES)
        ),
        dialogue_mechanism=(
            dialogue_mechanism
            or (existing.dialogue_mechanism if existing else "questionnaire_prealable")
        ),
        allowed_rag_sources=(
            allowed_rag_sources
            if allowed_rag_sources is not None
            else (existing.allowed_rag_sources if existing else DEFAULT_ALLOWED_RAG_SOURCES)
        ),
        ontology_views=(
            ontology_views
            if ontology_views is not None
            else (existing.ontology_views if existing else DEFAULT_ONTOLOGY_VIEWS)
        ),
        mcp_tool_permissions=(
            mcp_tool_permissions
            if mcp_tool_permissions is not None
            else (existing.mcp_tool_permissions if existing else DEFAULT_MCP_TOOL_PERMISSIONS)
        ),
        guardrails=(
            guardrails
            if guardrails is not None
            else (existing.guardrails if existing else DEFAULT_GUARDRAILS)
        ),
        output_contract_format=(
            output_contract_format
            or (existing.output_contract_format if existing else "markdown_structure")
        ),
        write_preview_required=(
            write_preview_required
            if write_preview_required is not None
            else (existing.write_preview_required if existing else True)
        ),
        test_bench_validated=(
            test_bench_validated
            if test_bench_validated is not None
            else (existing.test_bench_validated if existing else False)
        ),
        owner_workspace_id=(
            owner_workspace_id
            if owner_workspace_id is not None
            else (existing.owner_workspace_id if existing else None)
        ),
        owner_user_id=(
            owner_user_id
            if owner_user_id is not None
            else (existing.owner_user_id if existing else None)
        ),
    )
    return rebuild_agent_with_skills(base, valid_skills)
