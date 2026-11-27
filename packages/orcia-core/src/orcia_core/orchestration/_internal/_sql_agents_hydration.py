"""PG18 Hydration Helpers for `sql_agents_and_skills.py` (`<= 200 L`, `AD-19`)."""

from __future__ import annotations

from typing import cast, get_args

from orcia_core.domain.namespacing import (
    ResolutionTier,
    format_agent_mention,
    format_skill_command,
)
from orcia_core.orchestration._agents_namespacing import infer_record_pack_slug_and_tier
from orcia_core.orchestration.agents_and_skills_models import (
    DEFAULT_ALLOWED_RAG_SOURCES,
    DEFAULT_GUARDRAILS,
    DEFAULT_INVOCATION_MODES,
    DEFAULT_MCP_TOOL_PERMISSIONS,
    DEFAULT_ONTOLOGY_VIEWS,
    AgentDialogueMechanism,
    AgentHumanPartnerRole,
    AgentKindType,
    AgentLifecycleStatus,
    AgentLlmModelTier,
    AgentOutputContractFormat,
    AgentPostureType,
    AgentSkillVisibilityScope,
    AgentTestBenchStatus,
    AgentThinkingLevel,
    ManagedAgentRecord,
    ManagedSkillRecord,
)


def parse_visibility_scope(raw_val: object) -> AgentSkillVisibilityScope:
    val = str(raw_val or "TEAM").upper()
    if val in ("PRIVATE", "TEAM", "PACK"):
        return cast(AgentSkillVisibilityScope, val)
    return "TEAM"


def parse_agent_kind(raw_val: object) -> AgentKindType:
    val = str(raw_val or "LOCAL").upper()
    if val in ("LOCAL", "REMOTE_MCP_A2A"):
        return cast(AgentKindType, val)
    return "LOCAL"


def parse_str_tuple(raw_val: object, default: tuple[str, ...]) -> tuple[str, ...]:
    if not isinstance(raw_val, list):
        return default
    cleaned = tuple(str(item).strip() for item in raw_val if str(item).strip())
    return cleaned or default


def parse_mcp_perms(raw_val: object) -> tuple[tuple[str, str], ...]:
    if isinstance(raw_val, dict):
        return tuple((str(k).strip(), str(v).strip()) for k, v in raw_val.items() if str(k).strip())
    return DEFAULT_MCP_TOOL_PERMISSIONS


def hydrate_skill_record(
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
    column_workspace_id: str | None,
    pack_slug: str | None = None,
    bundle_kind: str | None = None,
    resolution_tier: ResolutionTier | None = None,
) -> ManagedSkillRecord:
    raw_params = meta.get("input_parameters")
    params = (
        tuple(str(p) for p in raw_params if str(p).strip())
        if isinstance(raw_params, (list, tuple))
        else ()
    )
    raw_ws = meta.get("owner_workspace_id") or column_workspace_id
    raw_user = meta.get("owner_user_id")
    from orcia_core.orchestration._agents_skills_locales import get_agents_skills_copy

    default_fmt = get_agents_skills_copy().default_output_format
    resolved_pack, resolved_tier = infer_record_pack_slug_and_tier(
        entity_id=resource_id,
        slug=slug,
        uri=uri,
        visibility_scope=vis_scope,
        source_pack_key=source_pack_key,
        explicit_pack_slug=pack_slug or (str(meta["pack_slug"]) if meta.get("pack_slug") else None),
        explicit_tier=resolution_tier,
        bundle_kind=bundle_kind,
    )
    qualified = format_skill_command(
        slug, pack_slug=resolved_pack, workspace_scoped=(resolved_pack is None)
    )
    return ManagedSkillRecord(
        skill_id=resource_id,
        slug=slug,
        command_handle=str(meta.get("command_handle") or f"/{slug}"),
        uri=uri,
        name=title,
        objective=description,
        input_parameters=params,
        instructions=str(meta.get("instructions") or ""),
        expected_output_format=str(meta.get("expected_output_format") or default_fmt),
        version=version,
        sha256=sha256,
        visibility_scope=vis_scope,
        source_pack_key=source_pack_key,
        enabled_in_workspace=enabled_in_workspace,
        is_si_write=bool(meta.get("is_si_write", False)),
        human_authored_required=bool(meta.get("human_authored_required", False)),
        owner_workspace_id=str(raw_ws).strip() if raw_ws else None,
        owner_user_id=str(raw_user).strip() if raw_user else None,
        pack_slug=resolved_pack,
        qualified_ref=qualified,
        resolution_tier=resolved_tier,
    )


def hydrate_agent_record(
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
    column_workspace_id: str | None,
    pack_slug: str | None = None,
    bundle_kind: str | None = None,
    resolution_tier: ResolutionTier | None = None,
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
        if raw_fmt in get_args(AgentOutputContractFormat)
        else "markdown_structure"
    )
    raw_prompt_ref = meta.get("prompt_ref")
    default_temp = 0.0 if posture == "EVALUATOR_GATE" else 0.2
    raw_temp = meta.get("temperature")
    raw_tokens = meta.get("max_tokens")
    raw_ws = meta.get("owner_workspace_id") or column_workspace_id
    raw_user = meta.get("owner_user_id")
    raw_bench_validated = bool(meta.get("test_bench_validated", False))
    raw_bench_status = str(meta.get("test_bench_status") or "").upper()
    test_bench_status: AgentTestBenchStatus = (
        cast(AgentTestBenchStatus, raw_bench_status)
        if raw_bench_status in ("UNTESTED", "PASSED", "FAILED")
        else ("PASSED" if raw_bench_validated else "UNTESTED")
    )
    raw_lifecycle = str(meta.get("lifecycle_status") or "").upper()
    lifecycle_status: AgentLifecycleStatus = (
        cast(AgentLifecycleStatus, raw_lifecycle)
        if raw_lifecycle in ("DRAFT", "ACTIVE")
        else "DRAFT"
    )
    resolved_pack, resolved_tier = infer_record_pack_slug_and_tier(
        entity_id=resource_id,
        slug=slug,
        uri=uri,
        visibility_scope=vis_scope,
        source_pack_key=source_pack_key,
        explicit_pack_slug=pack_slug or (str(meta["pack_slug"]) if meta.get("pack_slug") else None),
        explicit_tier=resolution_tier,
        bundle_kind=bundle_kind,
    )
    qualified = format_agent_mention(
        slug, pack_slug=resolved_pack, workspace_scoped=(resolved_pack is None)
    )
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
        agent_kind=parse_agent_kind(meta.get("agent_kind")),
        remote_endpoint_url=str(raw_remote).strip() if raw_remote else None,
        posture=posture,
        human_partner_role=human_partner_role,
        llm_model_tier=llm_model_tier,
        temperature=float(str(raw_temp)) if raw_temp is not None else default_temp,
        max_tokens=int(str(raw_tokens)) if raw_tokens is not None else 4096,
        prompt_ref=str(raw_prompt_ref).strip() if raw_prompt_ref else None,
        invocation_modes=parse_str_tuple(meta.get("invocation_modes"), DEFAULT_INVOCATION_MODES),
        dialogue_mechanism=dialogue_mechanism,
        allowed_rag_sources=parse_str_tuple(
            meta.get("allowed_rag_sources"), DEFAULT_ALLOWED_RAG_SOURCES
        ),
        ontology_views=parse_str_tuple(meta.get("ontology_views"), DEFAULT_ONTOLOGY_VIEWS),
        mcp_tool_permissions=parse_mcp_perms(meta.get("mcp_tool_permissions")),
        guardrails=parse_str_tuple(meta.get("guardrails"), DEFAULT_GUARDRAILS),
        output_contract_format=output_contract_format,
        write_preview_required=bool(meta.get("write_preview_required", True)),
        test_bench_validated=(test_bench_status == "PASSED"),
        lifecycle_status=lifecycle_status,
        test_bench_status=test_bench_status,
        owner_workspace_id=str(raw_ws).strip() if raw_ws else None,
        owner_user_id=str(raw_user).strip() if raw_user else None,
        pack_slug=resolved_pack,
        qualified_ref=qualified,
        resolution_tier=resolved_tier,
    )
