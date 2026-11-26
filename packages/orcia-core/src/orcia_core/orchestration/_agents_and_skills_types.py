"""Value Objects & Frozen Records for User-Centered Agents & Skills (`🤖 Mes Agents`).

Zero framework imports (`fastapi`, `sqlalchemy`, `dramatiq`, `redis`, `litellm`).
"""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
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
AgentLifecycleStatus = Literal["DRAFT", "ACTIVE"]
AgentTestBenchStatus = Literal["UNTESTED", "PASSED", "FAILED"]

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
    ("doc_tool", "WRITE_PREVIEW"),
    ("issue_tracker", "WRITE_PREVIEW"),
    ("git", "READ_ONLY"),
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
    is_si_write: bool = False
    human_authored_required: bool = False
    owner_workspace_id: str | None = None
    owner_user_id: str | None = None


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
    posture: AgentPostureType = "PRODUCER"
    human_partner_role: AgentHumanPartnerRole = "PO_PM"
    llm_model_tier: AgentLlmModelTier = "team_default"
    temperature: float = 0.2
    max_tokens: int = 4096
    prompt_ref: str | None = None
    invocation_modes: tuple[str, ...] = DEFAULT_INVOCATION_MODES
    dialogue_mechanism: AgentDialogueMechanism = "questionnaire_prealable"
    allowed_rag_sources: tuple[str, ...] = DEFAULT_ALLOWED_RAG_SOURCES
    ontology_views: tuple[str, ...] = DEFAULT_ONTOLOGY_VIEWS
    mcp_tool_permissions: tuple[tuple[str, str], ...] = DEFAULT_MCP_TOOL_PERMISSIONS
    guardrails: tuple[str, ...] = DEFAULT_GUARDRAILS
    output_contract_format: AgentOutputContractFormat = "markdown_structure"
    write_preview_required: bool = True
    test_bench_validated: bool = False
    lifecycle_status: AgentLifecycleStatus = "DRAFT"
    test_bench_status: AgentTestBenchStatus = "UNTESTED"
    owner_workspace_id: str | None = None
    owner_user_id: str | None = None


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
    test_bench_status: AgentTestBenchStatus = "PASSED"
    lifecycle_status: AgentLifecycleStatus = "ACTIVE"
