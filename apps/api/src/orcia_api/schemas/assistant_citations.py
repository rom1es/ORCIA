"""Pydantic v2 HTTP Transport Schemas for Assistant Citations (`Story 10.3`, `Story 26.1`)."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class RawSourceCandidateSchemaItem(BaseModel):
    """Input source candidate (`Story 10.3`)."""

    model_config = ConfigDict(extra="forbid")

    uri: str
    title: str
    authority_tier: Literal["REFERENCE", "ACTIVE"] = "ACTIVE"
    freshness: Literal["FRESH", "STALE_WARNING"] = "FRESH"
    snippet: str
    line_start: int = 1
    line_end: int = 25
    relevance_score: float = 0.9


class RawGlossaryCandidateSchemaItem(BaseModel):
    """Input glossary / axiom candidate (`Story 10.3`)."""

    model_config = ConfigDict(extra="forbid")

    term_or_axiom_id: str
    label: str
    ontology_level: Literal["N1_DIRECTIVE", "N2_NORME", "N3_MECANISME", "L4_GLOSSARY"] = (
        "L4_GLOSSARY"
    )
    definition: str


class RawToolOutputCandidateSchemaItem(BaseModel):
    """Input MCP tool / connector output candidate (`Story 10.3`)."""

    model_config = ConfigDict(extra="forbid")

    tool_name: str
    connector_uri: str
    summary: str


class EvidenceSourceCitationSchemaItem(BaseModel):
    """Numbered `[S1..Sn]` source entry (`Story 10.3`)."""

    model_config = ConfigDict(extra="forbid")

    tag: str
    index: int
    uri: str
    title: str
    authority_tier: Literal["REFERENCE", "ACTIVE"]
    freshness: Literal["FRESH", "STALE_WARNING"]
    snippet: str | None = None
    line_start: int
    line_end: int
    restricted_access: bool = False
    display_pill: str
    request_access_uri: str | None = None


class EvidenceGlossaryCitationSchemaItem(BaseModel):
    """Numbered `[G1..Gn]` glossary / axiom entry (`Story 10.3`)."""

    model_config = ConfigDict(extra="forbid")

    tag: str
    index: int
    term_or_axiom_id: str
    label: str
    ontology_level: Literal["N1_DIRECTIVE", "N2_NORME", "N3_MECANISME", "L4_GLOSSARY"]
    definition: str


class EvidenceToolCitationSchemaItem(BaseModel):
    """Numbered `[O1..On]` tool entry (`Story 10.3`)."""

    model_config = ConfigDict(extra="forbid")

    tag: str
    index: int
    tool_name: str
    connector_uri: str
    summary: str


class VerifyAndFilterCitationsRequest(BaseModel):
    """Request payload for `POST /api/v1/assistant/citations/verify-turn` (`Story 26.1`)."""

    model_config = ConfigDict(extra="forbid")

    workspace_id: str = Field(..., min_length=1)
    response_text: str = Field(..., min_length=1)
    sources: list[RawSourceCandidateSchemaItem] = Field(default_factory=list)
    glossary_items: list[RawGlossaryCandidateSchemaItem] = Field(default_factory=list)
    tool_outputs: list[RawToolOutputCandidateSchemaItem] = Field(default_factory=list)


class VerifyAndFilterCitationsResponse(BaseModel):
    """Response payload for `POST /api/v1/assistant/citations/verify-turn` (`Story 10.3`)."""

    model_config = ConfigDict(extra="forbid")

    sanitized_text: str
    valid_tags: list[str]
    stripped_phantom_tags: list[str]
    verification_duration_ms: float
    audit_id: str | None = None
    sources: list[EvidenceSourceCitationSchemaItem]
    glossary_items: list[EvidenceGlossaryCitationSchemaItem]
    tool_outputs: list[EvidenceToolCitationSchemaItem]
    footer_summary_line: str
    citation_map_emitted_at_ms: float = 80.0


class ArtifactCardActionRequest(BaseModel):
    """Request payload for `POST /api/v1/assistant/artifacts/action` (`Story 10.3` V5 Guard)."""

    model_config = ConfigDict(extra="forbid")

    workspace_id: str = Field(..., min_length=1)
    action_type: Literal[
        "COPY",
        "EXPORT_MD",
        "EXPORT_JSON",
        "SAVE_DRAFT",
        "CONTINUE_IN_PROCESS",
        "DIRECT_SI_WRITE",
        "PUBLISH_V1_VAULT",
    ]
    artifact_title: str = Field(..., min_length=1)
    artifact_content: str = Field(..., min_length=1)
    cited_tags: list[str] = Field(default_factory=list)
    target_uri: str | None = None


class ArtifactCardActionResponse(BaseModel):
    """Response payload for `POST /api/v1/assistant/artifacts/action` (`Story 10.3`)."""

    model_config = ConfigDict(extra="forbid")

    action_id: str
    workspace_id: str
    action_type: str
    artifact_title: str
    artifact_version_tag: str
    draft_uri: str | None = None
    process_launch_prefill: dict[str, object] = Field(default_factory=dict)
