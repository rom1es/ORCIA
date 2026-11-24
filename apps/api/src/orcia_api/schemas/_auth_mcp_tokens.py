"""Personal IDE/MCP token Pydantic v2 schemas (`Story 9.4`, split from `auth_and_org.py`)."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class McpPersonalTokenCreateRequest(BaseModel):
    """Story 9.4 — Request payload for `POST /api/v1/users/me/mcp-tokens` (`pat_mcp_*`, SHA-256)."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    label: str = Field(default="MCP IDE Key", min_length=1, max_length=120)
    expires_in_days: int = Field(default=30)
    rpm_limit: int = Field(default=60, ge=1, le=600)
    allowed_workspace_slugs: list[str] = Field(default_factory=list)
    exposed_capabilities: list[
        Literal["ASSISTANT", "PUBLISHED_AGENTS", "KB_GLOSSARY_SEARCH", "STAGED_DRAFTS"]
    ] = ["ASSISTANT", "KB_GLOSSARY_SEARCH"]
    target_kind: Literal["SPACE", "AGENT"] = "SPACE"
    target_slug: str = Field(default="scope-global", min_length=1, max_length=120)


class McpPersonalTokenMetadataItem(BaseModel):
    """Story 9.4 — Metadata item for a personal IDE/MCP token (`SHA-256` at rest)."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    token_id: str
    user_id: str
    label: str
    token_prefix: str
    token_sha256: str
    expires_in_days: Literal[30, 90]
    rpm_limit: int
    allowed_workspace_slugs: list[str]
    exposed_capabilities: list[
        Literal["ASSISTANT", "PUBLISHED_AGENTS", "KB_GLOSSARY_SEARCH", "STAGED_DRAFTS"]
    ]
    target_kind: Literal["SPACE", "AGENT"]
    target_slug: str
    mcp_endpoint_uri: str
    ide_json_snippet: str
    revoked: bool
    created_at_iso: str | None = None
    expires_at_iso: str | None = None
    revoked_at_iso: str | None = None


class McpPersonalTokenIssuedResponse(BaseModel):
    """Story 9.4 — One-time issuance response returning `plaintext_token` (`pat_mcp_*`)."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    plaintext_token: str
    record: McpPersonalTokenMetadataItem
    trace_id: str | None = None


class McpPersonalTokenListResponse(BaseModel):
    """Story 9.4 — List of personal IDE/MCP token metadata items."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    tokens: list[McpPersonalTokenMetadataItem]
    trace_id: str | None = None


class UserPreferencesUpdateRequest(BaseModel):
    """Story 9.4 & 20.3 — Payload for `PATCH /api/v1/users/me/preferences` (`0 ms` Anti-FOUC)."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    theme: Literal["light", "dark", "system"] | None = None
    locale: Literal["fr", "en"] | None = None
    default_hat: str | None = Field(default=None, min_length=1, max_length=64)
    default_assistant_hat: str | None = Field(default=None, min_length=1, max_length=64)
    assistant_tone: Literal["balanced", "concise", "detailed"] | None = None
    personal_instructions: str | None = Field(default=None, max_length=4000)
    auto_open_contextual_help: bool | None = None
    notifications_enabled: bool | None = None


class UserPreferencesResponse(BaseModel):
    """Story 9.4 & 20.3 — Response payload for `/api/v1/users/me/preferences`."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    user_id: str
    theme: Literal["light", "dark", "system"]
    locale: Literal["fr", "en"]
    default_hat: str
    default_assistant_hat: str
    assistant_tone: Literal["balanced", "concise", "detailed"]
    personal_instructions: str
    auto_open_contextual_help: bool
    notifications_enabled: bool
    assistant_behavior_redirect_uri: str
    trace_id: str | None = None
