"""HTTP/OpenAPI 3.1 transport schemas for Agents (`🤖`) & Skills (`🛠️`) Management."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

AgentThinkingLevelSchema = Literal["simple", "medium", "complex", "auto"]
AgentSkillVisibilityScopeSchema = Literal["PRIVATE", "TEAM", "PACK"]
AgentKindTypeSchema = Literal["LOCAL", "REMOTE_MCP_A2A"]
AgentPostureTypeSchema = Literal["PRODUCER", "EVALUATOR_GATE"]
AgentHumanPartnerRoleSchema = Literal["PO_PM", "ARCHITECT", "TECH_LEAD", "SECURITY_QA", "ALL"]
AgentLlmModelTierSchema = Literal["team_default", "fast", "deep", "discovery"]
AgentDialogueMechanismSchema = Literal["questionnaire_prealable", "pause_par_bloc", "direct"]
AgentOutputContractFormatSchema = Literal[
    "markdown_structure", "confluence_draft", "jira_draft", "gate_risk_json"
]


class SkillItemResponse(BaseModel):
    """Transport schema for a reusable Skill (`🛠️ Compétence`)."""

    model_config = ConfigDict(extra="forbid")

    skill_id: str = Field(..., min_length=1, max_length=128)
    slug: str = Field(..., min_length=1, max_length=128)
    command_handle: str = Field(..., min_length=2, max_length=130)
    uri: str = Field(..., min_length=1, max_length=512)
    name: str = Field(..., min_length=1, max_length=255)
    objective: str = Field(..., min_length=1, max_length=2000)
    input_parameters: list[str] = Field(default_factory=list)
    instructions: str = Field(..., min_length=1, max_length=8000)
    expected_output_format: str = Field(default="Synthèse structurée", min_length=1, max_length=512)
    version: str = Field(default="1.0.0", min_length=1, max_length=64)
    sha256: str = Field(default="", max_length=64)
    visibility_scope: AgentSkillVisibilityScopeSchema = "TEAM"
    source_pack_key: str | None = Field(default=None, max_length=128)
    enabled_in_workspace: bool = True


class UpsertSkillRequest(BaseModel):
    """Request payload to create or update a reusable Skill."""

    model_config = ConfigDict(extra="forbid")

    skill_id: str | None = Field(default=None, max_length=128)
    name: str = Field(..., min_length=1, max_length=255)
    objective: str = Field(..., min_length=1, max_length=2000)
    input_parameters: list[str] = Field(default_factory=list)
    instructions: str = Field(..., min_length=1, max_length=8000)
    expected_output_format: str = Field(default="Synthèse structurée", min_length=1, max_length=512)
    version: str = Field(default="1.0.0", min_length=1, max_length=64)
    visibility_scope: AgentSkillVisibilityScopeSchema | None = None
    source_pack_key: str | None = Field(default=None, max_length=128)
    enabled_in_workspace: bool | None = None


class ExecuteSkillRequest(BaseModel):
    """Request payload to execute/test a Skill in 1 click."""

    model_config = ConfigDict(extra="forbid")

    input_text: str = Field(..., min_length=1, max_length=4000)
    parameters: dict[str, str] = Field(default_factory=dict)


class ExecuteSkillResponse(BaseModel):
    """Response payload after testing/executing a Skill in 1 click."""

    model_config = ConfigDict(extra="forbid")

    skill_id: str
    skill_name: str
    command_handle: str
    input_text: str
    applied_parameters: dict[str, str]
    output_text: str
    expected_output_format: str
    status: Literal["SUCCEEDED"] = "SUCCEEDED"
    trace_id: str


class AgentItemResponse(BaseModel):
    """Transport schema for a configured Agent (`🤖 Agent`) with 6 Governance Blocks."""

    model_config = ConfigDict(extra="forbid")

    agent_id: str = Field(..., min_length=1, max_length=128)
    slug: str = Field(..., min_length=1, max_length=128)
    handle: str = Field(..., min_length=2, max_length=130)
    uri: str = Field(..., min_length=1, max_length=512)
    name: str = Field(..., min_length=1, max_length=255)
    role_mission: str = Field(..., min_length=1, max_length=2000)
    instructions: str = Field(..., min_length=1, max_length=8000)
    thinking_level: AgentThinkingLevelSchema = "medium"
    skill_ids: list[str] = Field(default_factory=list)
    version: str = Field(default="1.0.0", min_length=1, max_length=64)
    sha256: str = Field(default="", max_length=64)
    visibility_scope: AgentSkillVisibilityScopeSchema = "TEAM"
    source_pack_key: str | None = Field(default=None, max_length=128)
    enabled_in_workspace: bool = True
    mcp_exposed: bool = False
    agent_kind: AgentKindTypeSchema = "LOCAL"
    remote_endpoint_url: str | None = Field(default=None, max_length=512)
    posture: AgentPostureTypeSchema = "PRODUCER"
    human_partner_role: AgentHumanPartnerRoleSchema = "PO_PM"
    llm_model_tier: AgentLlmModelTierSchema = "team_default"
    temperature: float = Field(default=0.2, ge=0.0, le=2.0)
    max_tokens: int = Field(default=4096, ge=256, le=65536)
    prompt_ref: str | None = Field(default=None, max_length=512)
    invocation_modes: list[str] = Field(
        default_factory=lambda: ["generer", "corrections", "section"]
    )
    dialogue_mechanism: AgentDialogueMechanismSchema = "questionnaire_prealable"
    allowed_rag_sources: list[str] = Field(default_factory=lambda: ["all_workspace_sources"])
    ontology_views: list[str] = Field(
        default_factory=lambda: ["glossary", "apis_adr", "prd_regles_metier"]
    )
    mcp_tool_permissions: dict[str, str] = Field(
        default_factory=lambda: {
            "search_tool": "READ_ONLY",
            "confluence": "WRITE_PREVIEW",
            "jira": "WRITE_PREVIEW",
            "git": "READ_ONLY",
        }
    )
    guardrails: list[str] = Field(
        default_factory=lambda: [
            "citations_obligatoires",
            "aucun_fait_invente",
            "isolation_prompt_injection",
            "filtrage_dcp_pii",
        ]
    )
    output_contract_format: AgentOutputContractFormatSchema = "markdown_structure"
    write_preview_required: bool = True
    test_bench_validated: bool = False


class UpsertAgentRequest(BaseModel):
    """Request payload to create or update an Agent (`POST /api/v1/agents-and-skills/agents`)."""

    model_config = ConfigDict(extra="forbid")

    agent_id: str | None = Field(default=None, max_length=128)
    name: str = Field(..., min_length=1, max_length=255)
    role_mission: str = Field(..., min_length=1, max_length=2000)
    instructions: str = Field(..., min_length=1, max_length=8000)
    thinking_level: AgentThinkingLevelSchema = "medium"
    skill_ids: list[str] = Field(default_factory=list)
    version: str = Field(default="1.0.0", min_length=1, max_length=64)
    visibility_scope: AgentSkillVisibilityScopeSchema | None = None
    source_pack_key: str | None = Field(default=None, max_length=128)
    enabled_in_workspace: bool | None = None
    mcp_exposed: bool | None = None
    agent_kind: AgentKindTypeSchema | None = None
    remote_endpoint_url: str | None = Field(default=None, max_length=512)
    posture: AgentPostureTypeSchema | None = None
    human_partner_role: AgentHumanPartnerRoleSchema | None = None
    llm_model_tier: AgentLlmModelTierSchema | None = None
    temperature: float | None = Field(default=None, ge=0.0, le=2.0)
    max_tokens: int | None = Field(default=None, ge=256, le=65536)
    prompt_ref: str | None = Field(default=None, max_length=512)
    invocation_modes: list[str] | None = None
    dialogue_mechanism: AgentDialogueMechanismSchema | None = None
    allowed_rag_sources: list[str] | None = None
    ontology_views: list[str] | None = None
    mcp_tool_permissions: dict[str, str] | None = None
    guardrails: list[str] | None = None
    output_contract_format: AgentOutputContractFormatSchema | None = None
    write_preview_required: bool | None = None
    test_bench_validated: bool | None = None


class DuplicateAgentRequest(BaseModel):
    """Request payload to duplicate an Agent into a customizable TEAM/PRIVATE Agent."""

    model_config = ConfigDict(extra="forbid")

    new_name: str | None = Field(default=None, max_length=255)
    visibility_scope: Literal["PRIVATE", "TEAM"] = "TEAM"


class ToggleAgentGovernanceRequest(BaseModel):
    """Request payload to update Agent governance flags and thinking level in 1 click."""

    model_config = ConfigDict(extra="forbid")

    enabled_in_workspace: bool | None = None
    mcp_exposed: bool | None = None
    visibility_scope: Literal["PRIVATE", "TEAM"] | None = None
    thinking_level: AgentThinkingLevelSchema | None = None
    test_bench_validated: bool | None = None


class UpdateAgentSkillsRequest(BaseModel):
    """Request payload to attach/detach Skills on an Agent in 1 click."""

    model_config = ConfigDict(extra="forbid")

    skill_ids: list[str] = Field(default_factory=list)


class ExecuteAgentRequest(BaseModel):
    """Request payload to execute/test an Agent in 1 click."""

    model_config = ConfigDict(extra="forbid")

    prompt: str = Field(..., min_length=1, max_length=4000)


class InvokedSkillTraceResponseItem(BaseModel):
    """Trace item of a Skill mobilized during Agent execution."""

    model_config = ConfigDict(extra="forbid")

    skill_id: str
    skill_name: str
    command_handle: str
    output_summary: str


class ExecuteAgentResponse(BaseModel):
    """Response payload after testing/executing an Agent in 1 click."""

    model_config = ConfigDict(extra="forbid")

    agent_id: str
    agent_name: str
    agent_handle: str
    thinking_level: AgentThinkingLevelSchema
    prompt: str
    response_text: str
    invoked_skills: list[InvokedSkillTraceResponseItem] = Field(default_factory=list)
    status: Literal["SUCCEEDED"] = "SUCCEEDED"
    trace_id: str


class AgentsAndSkillsListResponse(BaseModel):
    """Combined list of user-created Agents and Skills (`GET /api/v1/agents-and-skills`)."""

    model_config = ConfigDict(extra="forbid")

    agents: list[AgentItemResponse] = Field(default_factory=list)
    skills: list[SkillItemResponse] = Field(default_factory=list)
    trace_id: str


class DeleteSkillOrAgentResponse(BaseModel):
    """Response payload after deleting a Skill or an Agent."""

    model_config = ConfigDict(extra="forbid")

    deleted_id: str
    detached_from_agent_ids: list[str] = Field(default_factory=list)
    trace_id: str
