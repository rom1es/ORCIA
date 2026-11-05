"""HTTP/OpenAPI 3.1 transport schemas for Agents (`🤖`) & Skills (`🛠️`) Management."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

AgentThinkingLevelSchema = Literal["simple", "medium", "complex", "auto"]


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
    """Transport schema for a configured Agent (`🤖 Agent`)."""

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
