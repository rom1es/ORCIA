"""Value Objects, Frozen Records & Builders for User-Centered Agents & Skills (`🤖 Mes Agents`).

Zero framework imports (`fastapi`, `sqlalchemy`, `dramatiq`, `redis`, `litellm`).
Models the 6 Governance Blocks of an ORCIA LLM Agent (A. Identity/Persona, B. Cognitive Engine,
C. System Instructions & Modes, D. Knowledge Scope RAG/Ontology, E. MCP Toolbox & Skills,
F. Guardrails & Output Contract) and its 6 Conversational Readiness Conditions.
"""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass, replace
from typing import Literal

from orcia_kernel.ids import new_uuid7_str

AgentThinkingLevel = Literal["simple", "medium", "complex", "auto"]
AgentSkillVisibilityScope = Literal["PRIVATE", "TEAM", "PACK"]
AgentKindType = Literal["LOCAL", "REMOTE_MCP_A2A"]
AgentPostureType = Literal["PRODUCER", "EVALUATOR_GATE"]
AgentHumanPartnerRole = Literal["PO_PM", "ARCHITECT", "TECH_LEAD", "SECURITY_QA", "ALL"]
AgentLlmModelTier = Literal["team_default", "fast", "deep", "discovery"]
AgentInvocationMode = Literal["generer", "corrections", "section"]
AgentDialogueMechanism = Literal["questionnaire_prealable", "pause_par_bloc", "direct"]
AgentOutputContractFormat = Literal[
    "markdown_structure", "confluence_draft", "jira_draft", "gate_risk_json"
]
McpToolPermissionMode = Literal["NONE", "READ_ONLY", "WRITE_PREVIEW"]

DEFAULT_INVOCATION_MODES: tuple[str, ...] = ("generer", "corrections", "section")
DEFAULT_ALLOWED_RAG_SOURCES: tuple[str, ...] = ("all_workspace_sources",)
DEFAULT_ONTOLOGY_VIEWS: tuple[str, ...] = ("glossary", "apis_adr", "prd_regles_metier")
DEFAULT_GUARDRAILS: tuple[str, ...] = (
    "citations_obligatoires",
    "aucun_fait_invente",
    "isolation_prompt_injection",
    "filtrage_dcp_pii",
)
DEFAULT_MCP_TOOL_PERMISSIONS: tuple[tuple[str, str], ...] = (
    ("search_tool", "READ_ONLY"),
    ("knowledge_base_tool", "WRITE_PREVIEW"),
    ("work_tracker_tool", "WRITE_PREVIEW"),
    ("repository_tool", "READ_ONLY"),
)

_SLUG_CLEAN_RE = re.compile(r"[^a-z0-9]+")


def normalize_identifier_slug(raw_name: str, fallback_prefix: str = "item") -> str:
    """Convert a human-readable name into a clean lowercase kebab-case slug."""
    cleaned = _SLUG_CLEAN_RE.sub("-", raw_name.strip().lower()).strip("-")
    return cleaned or f"{fallback_prefix}-{new_uuid7_str()[:8]}"


def compute_payload_sha256(payload: dict[str, object]) -> str:
    """Compute a deterministic SHA-256 hex digest over a JSON-serializable payload."""
    canonical = json.dumps(payload, sort_keys=True, ensure_ascii=False).encode("utf-8")
    return hashlib.sha256(canonical).hexdigest()


@dataclass(frozen=True, slots=True)
class ManagedSkillRecord:
    """User-created or Pack-provided reusable Skill (`🛠️ Compétence`)."""

    skill_id: str
    slug: str
    command_handle: str
    uri: str
    name: str
    objective: str
    input_parameters: tuple[str, ...]
    instructions: str
    expected_output_format: str
    version: str = "1.0.0"
    sha256: str = ""
    visibility_scope: AgentSkillVisibilityScope = "TEAM"
    source_pack_key: str | None = None
    enabled_in_workspace: bool = True


@dataclass(frozen=True, slots=True)
class ManagedAgentRecord:
    """Governed ORCIA LLM Agent (`🤖 Agent`) structured around 6 configuration blocks."""

    agent_id: str
    slug: str
    handle: str
    uri: str
    name: str
    role_mission: str
    instructions: str
    thinking_level: AgentThinkingLevel
    skill_ids: tuple[str, ...] = ()
    version: str = "1.0.0"
    sha256: str = ""
    visibility_scope: AgentSkillVisibilityScope = "TEAM"
    source_pack_key: str | None = None
    enabled_in_workspace: bool = True
    mcp_exposed: bool = False
    agent_kind: AgentKindType = "LOCAL"
    remote_endpoint_url: str | None = None
    # Block A: Identity, Posture & Human Partner
    posture: AgentPostureType = "PRODUCER"
    human_partner_role: AgentHumanPartnerRole = "PO_PM"
    # Block B: Cognitive Engine (Model, Effort, Inference & Budget)
    llm_model_tier: AgentLlmModelTier = "team_default"
    temperature: float = 0.2
    max_tokens: int = 4096
    # Block C: System Instructions & Interaction Modes
    prompt_ref: str | None = None
    invocation_modes: tuple[str, ...] = DEFAULT_INVOCATION_MODES
    dialogue_mechanism: AgentDialogueMechanism = "questionnaire_prealable"
    # Block D: Knowledge Scope (RAG & Ontology)
    allowed_rag_sources: tuple[str, ...] = DEFAULT_ALLOWED_RAG_SOURCES
    ontology_views: tuple[str, ...] = DEFAULT_ONTOLOGY_VIEWS
    # Block E: MCP Toolbox Permissions
    mcp_tool_permissions: tuple[tuple[str, str], ...] = DEFAULT_MCP_TOOL_PERMISSIONS
    # Block F: Guardrails, Output Contract & Test Bench Validation
    guardrails: tuple[str, ...] = DEFAULT_GUARDRAILS
    output_contract_format: AgentOutputContractFormat = "markdown_structure"
    write_preview_required: bool = True
    test_bench_validated: bool = False


@dataclass(frozen=True, slots=True)
class SkillExecutionOutcome:
    """Result of testing/executing a Skill in 1 click."""

    skill_id: str
    skill_name: str
    command_handle: str
    input_text: str
    applied_parameters: dict[str, str]
    output_text: str
    expected_output_format: str
    status: Literal["SUCCEEDED"] = "SUCCEEDED"


@dataclass(frozen=True, slots=True)
class InvokedSkillTraceItem:
    """Trace of a Skill mobilized during an Agent execution."""

    skill_id: str
    skill_name: str
    command_handle: str
    output_summary: str


@dataclass(frozen=True, slots=True)
class AgentExecutionOutcome:
    """Result of testing/executing an Agent with its attached Skills in 1 click."""

    agent_id: str
    agent_name: str
    agent_handle: str
    thinking_level: AgentThinkingLevel
    prompt: str
    response_text: str
    invoked_skills: tuple[InvokedSkillTraceItem, ...]
    status: Literal["SUCCEEDED"] = "SUCCEEDED"


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
    )


def rebuild_agent_with_skills(
    agent: ManagedAgentRecord, next_skills: tuple[str, ...]
) -> ManagedAgentRecord:
    """Return a copy of `agent` with updated `skill_ids` and recomputed `sha256`."""
    digest = compute_payload_sha256(
        {
            "agent_id": agent.agent_id,
            "slug": agent.slug,
            "name": agent.name,
            "role_mission": agent.role_mission,
            "instructions": agent.instructions,
            "thinking_level": agent.thinking_level,
            "skill_ids": list(next_skills),
            "version": agent.version,
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
    )
    return replace(agent, skill_ids=next_skills, sha256=digest)


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
        source_pack_key=source_pack_key
        if source_pack_key is not None
        else (existing.source_pack_key if existing else None),
        enabled_in_workspace=enabled_in_workspace
        if enabled_in_workspace is not None
        else (existing.enabled_in_workspace if existing else True),
        mcp_exposed=mcp_exposed
        if mcp_exposed is not None
        else (existing.mcp_exposed if existing else False),
        agent_kind=agent_kind or (existing.agent_kind if existing else "LOCAL"),
        remote_endpoint_url=remote_endpoint_url
        if remote_endpoint_url is not None
        else (existing.remote_endpoint_url if existing else None),
        posture=resolved_posture,
        human_partner_role=human_partner_role
        or (existing.human_partner_role if existing else "PO_PM"),
        llm_model_tier=llm_model_tier or (existing.llm_model_tier if existing else "team_default"),
        temperature=temperature
        if temperature is not None
        else (existing.temperature if existing else default_temp),
        max_tokens=max_tokens
        if max_tokens is not None
        else (existing.max_tokens if existing else 4096),
        prompt_ref=prompt_ref
        if prompt_ref is not None
        else (existing.prompt_ref if existing else None),
        invocation_modes=invocation_modes
        if invocation_modes is not None
        else (existing.invocation_modes if existing else DEFAULT_INVOCATION_MODES),
        dialogue_mechanism=dialogue_mechanism
        or (existing.dialogue_mechanism if existing else "questionnaire_prealable"),
        allowed_rag_sources=allowed_rag_sources
        if allowed_rag_sources is not None
        else (existing.allowed_rag_sources if existing else DEFAULT_ALLOWED_RAG_SOURCES),
        ontology_views=ontology_views
        if ontology_views is not None
        else (existing.ontology_views if existing else DEFAULT_ONTOLOGY_VIEWS),
        mcp_tool_permissions=mcp_tool_permissions
        if mcp_tool_permissions is not None
        else (existing.mcp_tool_permissions if existing else DEFAULT_MCP_TOOL_PERMISSIONS),
        guardrails=guardrails
        if guardrails is not None
        else (existing.guardrails if existing else DEFAULT_GUARDRAILS),
        output_contract_format=output_contract_format
        or (existing.output_contract_format if existing else "markdown_structure"),
        write_preview_required=write_preview_required
        if write_preview_required is not None
        else (existing.write_preview_required if existing else True),
        test_bench_validated=test_bench_validated
        if test_bench_validated is not None
        else (existing.test_bench_validated if existing else False),
    )
    return rebuild_agent_with_skills(base, valid_skills)


def format_skill_execution_outcome(
    skill: ManagedSkillRecord,
    clean_input: str,
    parameters: dict[str, str] | None,
    llm_response_override: str | None,
) -> SkillExecutionOutcome:
    """Build a formatted `SkillExecutionOutcome` from a `ManagedSkillRecord` and input."""
    provided = {
        str(k).strip(): str(v).strip() for k, v in (parameters or {}).items() if str(k).strip()
    }
    for p in skill.input_parameters:
        provided.setdefault(p, clean_input)
    params_summary = (
        ", ".join(f"{k}={v}" for k, v in provided.items())
        if provided
        else "aucun paramètre additionnel"
    )
    res = (
        llm_response_override.strip()
        if llm_response_override and llm_response_override.strip()
        else f"Synthèse validée pour « {clean_input} »."
    )
    lines = [
        f"✅ Compétence « {skill.name} » ({skill.command_handle}) exécutée avec succès.",
        f"• Objectif appliqué : {skill.objective}",
        f"• Entrée analysée : {clean_input}",
        f"• Paramètres pris en compte : {params_summary}",
        f"• Méthode exécutée : {skill.instructions}",
        f"• Résultat ({skill.expected_output_format}) :\n{res}",
    ]
    return SkillExecutionOutcome(
        skill_id=skill.skill_id,
        skill_name=skill.name,
        command_handle=skill.command_handle,
        input_text=clean_input,
        applied_parameters=provided,
        output_text="\n".join(lines),
        expected_output_format=skill.expected_output_format,
    )


def format_agent_execution_outcome(
    agent: ManagedAgentRecord,
    clean_prompt: str,
    traces: list[InvokedSkillTraceItem],
    llm_text: str,
) -> AgentExecutionOutcome:
    """Build a formatted `AgentExecutionOutcome` from an Agent, traces, and LLM output."""
    skills_names = (
        ", ".join(f"{t.skill_name} ({t.command_handle})" for t in traces)
        if traces
        else "aucune compétence rattachée"
    )
    posture_lbl = (
        "Évaluateur / Contradicteur (Gate)"
        if agent.posture == "EVALUATOR_GATE"
        else "Producteur / Assistant métier"
    )
    lines = [
        f"🤖 Réponse de {agent.name} ({agent.handle}) — Mission : {agent.role_mission}",
        (
            f"• Posture : {posture_lbl} | Binôme humain : {agent.human_partner_role} "
            f"| Contrat : {agent.output_contract_format}"
        ),
        (
            f"• Moteur cognitif : {agent.llm_model_tier} "
            f"(effort={agent.thinking_level}, temp={agent.temperature}, "
            f"max_tokens={agent.max_tokens})"
        ),
        f"• Demande traitée : « {clean_prompt} »",
        f"• Compétences mobilisées ({len(traces)}) : {skills_names}",
        (
            f"• Synthèse : Selon mes instructions (« {agent.instructions} »), "
            f"voici la proposition structurée avec citations [S1] pour « {clean_prompt} ». "
            f"({llm_text})"
        ),
    ]
    return AgentExecutionOutcome(
        agent_id=agent.agent_id,
        agent_name=agent.name,
        agent_handle=agent.handle,
        thinking_level=agent.thinking_level,
        prompt=clean_prompt,
        response_text="\n".join(lines),
        invoked_skills=tuple(traces),
    )
