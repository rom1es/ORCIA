"""Value Objects, Frozen Records & Builders for User-Centered Agents & Skills (`🤖 Mes Agents`).

Zero framework imports (`fastapi`, `sqlalchemy`, `dramatiq`, `redis`, `litellm`).
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
    """User-created or Pack-provided Agent (`🤖 Agent`) with 1-click attached Skills."""

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
) -> ManagedAgentRecord:
    """Construct a `ManagedAgentRecord` with deterministic SHA-256 digest."""
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
    lines = [
        f"🤖 Réponse de {agent.name} ({agent.handle}) — Mission : {agent.role_mission}",
        f"• Demande traitée : « {clean_prompt} »",
        f"• Compétences mobilisées ({len(traces)}) : {skills_names}",
        (
            f"• Synthèse : Selon mes instructions (« {agent.instructions} »), "
            f"voici la proposition structurée pour « {clean_prompt} ». ({llm_text})"
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
