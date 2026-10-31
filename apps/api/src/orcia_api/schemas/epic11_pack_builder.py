"""HTTP/OpenAPI schemas for Story 11.4 (`packages/orcia-pack-builder` Processes 1 to 4)."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


class DnaChainPackSeedItemRequest(BaseModel):
    """Causal DNA chain seed (`DIRECTIVE ➔ NORME ➔ MÉCANISME`) in Process 1."""

    model_config = ConfigDict(extra="forbid")

    directive_code: str = Field(..., min_length=2, max_length=64)
    directive_title: str = Field(..., min_length=2, max_length=256)
    norm_code: str = Field(..., min_length=2, max_length=64)
    norm_title: str = Field(..., min_length=2, max_length=256)
    mechanism_code: str = Field(..., min_length=2, max_length=64)
    rule_id: str = Field(..., min_length=2, max_length=64)
    starlark_source: str = Field(..., min_length=10, max_length=16384)
    passing_test_payload: dict[str, Any] = Field(default_factory=dict)
    failing_test_payload: dict[str, Any] = Field(default_factory=dict)


class CreateBusinessPackRequest(BaseModel):
    """Request payload for Process 1 (`create-business-pack`)."""

    model_config = ConfigDict(extra="forbid")

    pack_slug: str = Field(..., min_length=2, max_length=40)
    title: str = Field(..., min_length=3, max_length=200)
    version: str = Field(default="0.1.0", min_length=3, max_length=32)
    domain_name: str = Field(default="FINANCE", min_length=2, max_length=64)
    human_anchor_intent: str = Field(..., min_length=1, max_length=4000)
    dna_seeds: list[DnaChainPackSeedItemRequest] = Field(default_factory=list)
    human_profiles: list[str] = Field(default_factory=list)
    agents: list[str] = Field(default_factory=list)
    workflows: list[str] = Field(default_factory=list)
    actor_role: str = Field(default="ARCHITECT")
    actor_id: str = Field(default="architect-user")


class CreateBusinessPackResponse(BaseModel):
    """Response payload for Process 1 (`create-business-pack`)."""

    model_config = ConfigDict(extra="forbid")

    pack_id: str
    pack_slug: str
    version: str
    title: str
    human_anchor_intent: str
    target_directory: str
    generated_file_paths: list[str]
    manifest_validation_elapsed_ms: float
    starlark_rules_certified_count: int
    max_starlark_elapsed_ms: float
    kernel_or_core_touched: bool


class EvolveBusinessPackWhatIfRequest(BaseModel):
    """Request payload for Process 2 (`evolve-business-pack` *What-If*)."""

    model_config = ConfigDict(extra="forbid")

    pack_slug: str = Field(..., min_length=2, max_length=40)
    previous_version: str = Field(default="0.1.0")
    target_version: str = Field(default="0.2.0")
    modified_norms: list[str] = Field(default_factory=list)
    modified_workflows: list[str] = Field(default_factory=list)
    subscribed_workspaces: list[dict[str, Any]] = Field(default_factory=list)
    active_run_lock_ids: list[str] = Field(default_factory=list)
    actor_role: str = Field(default="ARCHITECT")


class WhatIfWorkspaceImpactItemResponse(BaseModel):
    """Per-workspace impact entry in Process 2."""

    model_config = ConfigDict(extra="forbid")

    workspace_key: str
    impacted_workflows: list[str]
    breaking_norms: list[str]
    active_runs_count: int
    run_locks_untouched: bool


class EvolveBusinessPackWhatIfResponse(BaseModel):
    """Response payload for Process 2 (`evolve-business-pack` *What-If*)."""

    model_config = ConfigDict(extra="forbid")

    pack_slug: str
    previous_version: str
    target_version: str
    impacted_workspaces_count: int
    impacted_workflows_count: int
    breaking_changes_detected: bool
    active_run_locks_preserved: bool
    untouched_run_lock_ids: list[str]
    workspace_impacts: list[WhatIfWorkspaceImpactItemResponse]


class CertifyPackToolRequest(BaseModel):
    """Request payload for Process 3 (`certify-pack-tool`)."""

    model_config = ConfigDict(extra="forbid")

    tool_slug: str = Field(..., min_length=2, max_length=80)
    sandbox_tier: Literal["TIER_1B_STARLARK", "TIER_2_CONTAINER"] = "TIER_1B_STARLARK"
    starlark_source: str = ""
    rule_id: str = "NORM-PACK-001"
    passing_test_payload: dict[str, Any] = Field(default_factory=dict)
    failing_test_payload: dict[str, Any] = Field(default_factory=dict)
    container_image_digest: str = ""
    container_command: list[str] = Field(default_factory=list)
    actor_role: str = Field(default="ARCHITECT")


class CertifyPackToolResponse(BaseModel):
    """Response payload for Process 3 (`certify-pack-tool`)."""

    model_config = ConfigDict(extra="forbid")

    tool_slug: str
    sandbox_tier: Literal["TIER_1B_STARLARK", "TIER_2_CONTAINER"]
    certified: bool
    elapsed_ms: float
    passing_vector_ok: bool
    failing_vector_rejected_ok: bool
    network_isolated: bool
    certificate_sha256: str
    diagnostics: list[str]


class ExportFromWorkspaceToPackRequest(BaseModel):
    """Request payload for Process 4 (`export-from-workspace-to-pack`)."""

    model_config = ConfigDict(extra="forbid")

    source_workspace_key: str = Field(..., min_length=2, max_length=80)
    target_pack_slug: str = Field(..., min_length=2, max_length=40)
    target_pack_version: str = Field(default="0.2.0")
    asset_kind: Literal["AGENT", "WORKFLOW", "NORM", "STARLARK_MECHANISM"] = "STARLARK_MECHANISM"
    asset_slug: str = Field(..., min_length=2, max_length=80)
    raw_asset_payload: dict[str, Any] = Field(default_factory=dict)
    actor_role: str = Field(default="ARCHITECT")


class ExportFromWorkspaceToPackResponse(BaseModel):
    """Response payload for Process 4 (`export-from-workspace-to-pack`)."""

    model_config = ConfigDict(extra="forbid")

    source_workspace_key: str
    target_pack_slug: str
    target_pack_version: str
    asset_kind: Literal["AGENT", "WORKFLOW", "NORM", "STARLARK_MECHANISM"]
    asset_slug: str
    promoted_uri: str
    scrubbed_references_count: int
    sanitized_payload: dict[str, Any]


class ValidateHelpArticleRequest(BaseModel):
    """Request payload for deterministic validator `validate_help_article` (`< 5 s`)."""

    model_config = ConfigDict(extra="forbid")

    markdown_text: str = Field(..., min_length=10, max_length=65536)
    lang: Literal["fr", "en"] = "fr"
    extra_allowed_routes: list[str] = Field(default_factory=list)
    known_glossary_terms: list[str] = Field(default_factory=list)


class ValidateHelpArticleResponse(BaseModel):
    """Response payload for `validate_help_article`."""

    model_config = ConfigDict(extra="forbid")

    article_id: str
    lang: Literal["fr", "en"]
    passed: bool
    bound_routes_valid: bool
    ui_components_and_sections_valid: bool
    glossary_and_zero_secret_valid: bool
    elapsed_ms: float
    violations: list[str]


class GenerateAndAttachHelpRequest(BaseModel):
    """Request payload for Process 5 (`generate-and-attach-help`)."""

    model_config = ConfigDict(extra="forbid")

    article_id: str = Field(..., min_length=3, max_length=128)
    article_slug: str = Field(..., min_length=2, max_length=80)
    version: str = Field(default="1.0.0", min_length=3, max_length=32)
    pack_slug: str = Field(default="core", max_length=40)
    title_fr: str = Field(..., min_length=3, max_length=255)
    title_en: str = Field(..., min_length=3, max_length=255)
    bound_routes: list[str] = Field(..., min_length=1)
    roles_allowed: list[str] = Field(default_factory=lambda: ["TEAM_LEAD", "CONTRIBUTOR"])
    glossary_terms: list[str] = Field(default_factory=list)
    related_workflows: list[str] = Field(default_factory=list)
    purpose_fr: str = Field(..., min_length=10, max_length=4000)
    purpose_en: str = Field(..., min_length=10, max_length=4000)
    steps_fr: list[str] = Field(..., min_length=1)
    steps_en: list[str] = Field(..., min_length=1)
    faq_fr: list[str] = Field(..., min_length=1)
    faq_en: list[str] = Field(..., min_length=1)
    ui_component_name: str = Field(default="ContextualHelpColumnAndCenter")
    trigger_regime: Literal["STAGED_HUMAN_REVIEW", "AUTONOMOUS_CONTRACT"] = "AUTONOMOUS_CONTRACT"
    known_glossary_terms: list[str] = Field(default_factory=list)
    actor_role: str = Field(default="ARCHITECT")


class GenerateAndAttachHelpResponse(BaseModel):
    """Response payload for Process 5 (`generate-and-attach-help`)."""

    model_config = ConfigDict(extra="forbid")

    article_id: str
    version: str
    pack_id: str
    trigger_regime: Literal["STAGED_HUMAN_REVIEW", "AUTONOMOUS_CONTRACT"]
    bound_routes: list[str]
    fr_cas_key: str
    en_cas_key: str
    fr_sha256: str
    en_sha256: str
    validation_fr: ValidateHelpArticleResponse
    validation_en: ValidateHelpArticleResponse
    invalidated_redis_keys: list[str]
    exported_git_paths: list[str]
    hot_attach_elapsed_ms: float
    authority_role: Literal["REFERENCE"] = "REFERENCE"
