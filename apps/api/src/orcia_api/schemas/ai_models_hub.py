"""OpenAPI Pydantic Transport Schemas for AI Models Hub (`Story 17.5`, `AD-21`).

Zero secret leakage: encrypted keys, plaintext secrets, and decryption nonces
are strictly prohibited from all response models.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from orcia_api.schemas.settings_and_studio import SecretInputPayload, SecretStatusResponse

SecretInputRequest = SecretInputPayload

ScopeLevelLiteral = Literal["GLOBAL", "BU", "TEAM", "WORKSPACE"]
InferenceTierLiteral = Literal["simple", "medium", "complex", "auto"]
InferenceEffortLiteral = Literal["default", "fast", "balanced", "deep"]
LlmAuthModeLiteral = Literal["api_key", "env_var", "none_local"]
LlmProtocolModeLiteral = Literal["openai_compatible", "gemini_native", "anthropic_messages"]
LlmModelUsageLiteral = Literal["chat", "embedding"]
HealthStatusLiteral = Literal["OPERATIONAL", "DEGRADED", "ERROR", "UNTESTED"]
PinRemovalModeLiteral = Literal["reject", "drain", "force"]
RagReindexJobStatusLiteral = Literal[
    "IDLE", "PENDING", "IN_PROGRESS", "COMPLETED", "FAILED", "CANCELLED"
]


class AiModelMappingItemResponse(BaseModel):
    """Full public representation of an AI model mapping with health and masked secret."""

    model_config = ConfigDict(extra="forbid")

    id: str
    scope_level: ScopeLevelLiteral
    scope_id: str
    display_name: str
    inference_tier: InferenceTierLiteral
    effort: InferenceEffortLiteral
    provider_slug: str
    model_family: str
    model_name: str
    fallback_model_name: str | None = None
    endpoint_uri: str
    auth_mode: LlmAuthModeLiteral
    protocol_mode: LlmProtocolModeLiteral
    usage: LlmModelUsageLiteral = "chat"
    env_var_name: str | None = None
    fallback_order: int
    max_tokens_budget: int
    max_cost_usd: float
    is_active: bool
    draining: bool
    health_status: HealthStatusLiteral
    last_tested_at: str | None = None
    last_latency_ms: int | None = None
    created_at: str
    updated_at: str
    secret_status: SecretStatusResponse


class AiModelMappingsListResponse(BaseModel):
    """List response with tier coverage summary."""

    model_config = ConfigDict(extra="forbid")

    items: list[AiModelMappingItemResponse]
    total_count: int
    active_tiers_coverage: dict[str, bool]


class AiModelCreateRequest(BaseModel):
    """Write-only command to connect a new AI model."""

    model_config = ConfigDict(extra="forbid")

    scope_level: ScopeLevelLiteral = "WORKSPACE"
    scope_id: str = "0195f000-0000-7000-8000-000000000301"
    display_name: str = Field(default="", max_length=160)
    inference_tier: InferenceTierLiteral = "medium"
    effort: InferenceEffortLiteral = "default"
    provider_slug: str = Field(min_length=1, max_length=64)
    model_family: str = Field(min_length=1, max_length=64)
    model_name: str = Field(min_length=1, max_length=128)
    fallback_model_name: str | None = Field(default=None, max_length=128)
    endpoint_uri: str = Field(min_length=1, max_length=1024)
    auth_mode: LlmAuthModeLiteral = "api_key"
    protocol_mode: LlmProtocolModeLiteral = "openai_compatible"
    usage: LlmModelUsageLiteral = "chat"
    env_var_name: str | None = Field(default=None, max_length=128)
    fallback_order: int = Field(default=1, ge=1, le=100)
    max_tokens_budget: int = Field(default=8192, gt=0)
    max_cost_usd: float = Field(default=10.0, ge=0.0)
    secret_input: SecretInputRequest | None = None


class AiModelPatchRequest(BaseModel):
    """Partial update command for model configuration and key rotation."""

    model_config = ConfigDict(extra="forbid")

    display_name: str | None = Field(default=None, max_length=160)
    fallback_model_name: str | None = Field(default=None, max_length=128)
    endpoint_uri: str | None = Field(default=None, max_length=1024)
    auth_mode: LlmAuthModeLiteral | None = None
    protocol_mode: LlmProtocolModeLiteral | None = None
    usage: LlmModelUsageLiteral | None = None
    env_var_name: str | None = Field(default=None, max_length=128)
    is_active: bool | None = None
    secret_input: SecretInputRequest | None = None


class AiModelTestResponse(BaseModel):
    """Outcome of an on-demand connectivity test."""

    model_config = ConfigDict(extra="forbid")

    mapping_id: str
    health_status: HealthStatusLiteral
    latency_ms: int
    tested_at: str
    message: str


class AiModelDeleteImpactResponse(BaseModel):
    """Pre-deletion impact analysis report on published workflows and DBOS runs."""

    model_config = ConfigDict(extra="forbid")

    mapping_id: str
    inference_tier: InferenceTierLiteral
    model_name: str
    remaining_active_for_tier: int
    dependent_workflows_count: int
    dependent_workflow_ids: list[str]
    pinned_active_runs_count: int
    pinned_run_ids: list[str]
    is_last_active_for_tier: bool


class AiModelDeleteResponse(BaseModel):
    """Result of delete or drain operation."""

    model_config = ConfigDict(extra="forbid")

    mapping_id: str
    status: Literal["DELETED", "DRAINING"]


class DiscoveredModelItem(BaseModel):
    """Public representation of a model discovered on a provider metadata endpoint."""

    model_config = ConfigDict(extra="forbid")

    id: str
    display_name: str | None = None
    description: str | None = None
    usage_hint: Literal["chat", "embedding", "unknown"] = "unknown"
    owned_by: str | None = None


class AiModelDiscoverRequest(BaseModel):
    """Parameters to query a provider's model metadata endpoint without inference tokens."""

    model_config = ConfigDict(extra="forbid")

    endpoint_uri: str = Field(min_length=1, max_length=1024)
    protocol_mode: LlmProtocolModeLiteral = "openai_compatible"
    provider_slug: str | None = Field(default=None, max_length=64)
    mapping_id: str | None = Field(default=None, max_length=128)
    api_key: str | None = Field(default=None, max_length=512)


class AiModelDiscoveryResponse(BaseModel):
    """Response containing the list of discovered models."""

    model_config = ConfigDict(extra="forbid")

    endpoint_uri: str
    protocol_mode: LlmProtocolModeLiteral
    provider_slug: str | None = None
    models: list[DiscoveredModelItem]
    total_count: int


class RagReindexStatusResponse(BaseModel):
    """Current status of the global RAG vector reindexing job (`Story 19.7`)."""

    model_config = ConfigDict(extra="forbid")

    job_id: str | None = None
    status: RagReindexJobStatusLiteral = "IDLE"
    target_model_id: str | None = None
    target_model_name: str | None = None
    total_chunks: int = 0
    processed_chunks: int = 0
    progress_percentage: int = 0
    error_message: str | None = None
    created_at: str | None = None
    started_at: str | None = None
    completed_at: str | None = None
    updated_at: str | None = None


class RagReindexTriggerResponse(BaseModel):
    """Response returned upon triggering a global RAG vector reindexing job (`Story 19.7`)."""

    model_config = ConfigDict(extra="forbid")

    job_id: str
    status: RagReindexJobStatusLiteral = "PENDING"
    target_model_id: str
    target_model_name: str
    message: str


__all__ = [
    "AiModelCreateRequest",
    "AiModelDeleteImpactResponse",
    "AiModelDeleteResponse",
    "AiModelDiscoverRequest",
    "AiModelDiscoveryResponse",
    "AiModelMappingItemResponse",
    "AiModelMappingsListResponse",
    "AiModelPatchRequest",
    "AiModelTestResponse",
    "DiscoveredModelItem",
    "HealthStatusLiteral",
    "InferenceEffortLiteral",
    "InferenceTierLiteral",
    "LlmAuthModeLiteral",
    "LlmModelUsageLiteral",
    "LlmProtocolModeLiteral",
    "PinRemovalModeLiteral",
    "RagReindexJobStatusLiteral",
    "RagReindexStatusResponse",
    "RagReindexTriggerResponse",
    "ScopeLevelLiteral",
]
