"""Pydantic v2 HTTP schemas for Inter-Step Upstream Challenge & Targeted Replay (`Story 3.5`)."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from orcia_core.ontology.models import HumanProfileArchetype
from orcia_core.orchestration.challenge_and_replay import ChallengeStatus


class UpstreamChallengePreviewRequest(BaseModel):
    """Request payload for `POST .../steps/{step_key}/challenge/preview` (`UX-DR7`, `AD-7`)."""

    model_config = ConfigDict(extra="forbid")

    target_upstream_step_key: str = Field(..., min_length=1, max_length=128)
    challenged_section_key: str = Field(default="business_rules", min_length=1, max_length=128)
    challenge_reason: str = Field(..., min_length=10, max_length=2000)
    target_profile_archetype: HumanProfileArchetype = Field(default="PM_BUSINESS")


class UpstreamChallengePreviewSchemaItem(BaseModel):
    """What-If impact preview item returned for an upstream challenge (`AD-7`, `UX-DR7`)."""

    model_config = ConfigDict(extra="forbid")

    run_id: str
    challenger_step_key: str
    target_upstream_step_key: str
    challenged_section_key: str
    challenge_reason: str
    target_profile_archetype: HumanProfileArchetype
    translated_summary: str
    invalidated_downstream_step_keys: list[str]
    invalidated_artifact_sections: list[str]
    invalidated_ontology_axiom_keys: list[str]
    preserved_upstream_step_keys: list[str]
    upstream_tokens_saved: int = Field(..., ge=0)


class UpstreamChallengePreviewResponse(BaseModel):
    """Response payload for `POST .../steps/{step_key}/challenge/preview`."""

    model_config = ConfigDict(extra="forbid")

    preview: UpstreamChallengePreviewSchemaItem
    trace_id: str = Field(..., min_length=32, max_length=32)


class UpstreamChallengeSubmitRequest(BaseModel):
    """Request payload for `POST .../steps/{step_key}/challenge` (`FR-7`, `UX-DR7`)."""

    model_config = ConfigDict(extra="forbid")

    target_upstream_step_key: str = Field(..., min_length=1, max_length=128)
    challenged_section_key: str = Field(default="business_rules", min_length=1, max_length=128)
    challenge_reason: str = Field(..., min_length=10, max_length=2000)
    target_profile_archetype: HumanProfileArchetype = Field(default="PM_BUSINESS")
    proposed_upstream_revision: str | None = Field(default=None, max_length=4000)


class UpstreamChallengeSchemaItem(BaseModel):
    """Persisted upstream challenge item (`FR-7`, `AD-7`)."""

    model_config = ConfigDict(extra="forbid")

    id: str
    challenge_key: str
    workspace_id: str
    run_id: str
    challenger_step_key: str
    target_upstream_step_key: str
    challenged_section_key: str
    challenge_reason: str
    target_profile_archetype: HumanProfileArchetype
    translated_summary: str
    invalidated_downstream_step_keys: list[str]
    invalidated_artifact_sections: list[str]
    invalidated_ontology_axiom_keys: list[str]
    preserved_upstream_step_keys: list[str]
    status: ChallengeStatus
    created_by_user_id: str
    outbox_event_id: str
    revised_artifact_version: str | None = None


class UpstreamChallengeSubmitResponse(BaseModel):
    """Response payload for `POST .../steps/{step_key}/challenge`."""

    model_config = ConfigDict(extra="forbid")

    challenge: UpstreamChallengeSchemaItem
    preview: UpstreamChallengePreviewSchemaItem
    trace_id: str = Field(..., min_length=32, max_length=32)


class StepReplayRequest(BaseModel):
    """Request payload for `POST .../runs/{run_id}/steps/{step_key}/replay` (`FR-16`, `FR-30`)."""

    model_config = ConfigDict(extra="forbid")

    sub_workflow_step_key: str | None = Field(default=None, min_length=1, max_length=128)
    revised_section_payload: dict[str, Any] | None = None


class StepReplayResultSchemaItem(BaseModel):
    """Replay execution summary proving 0 upstream re-execution (`FR-16`, `FR-30`, `AD-2`)."""

    model_config = ConfigDict(extra="forbid")

    run_id: str
    replayed_from_step_key: str
    sub_workflow_step_key: str | None = None
    reused_upstream_snapshot_ids: list[str]
    superseded_snapshot_ids: list[str]
    new_active_snapshot_ids: list[str]
    upstream_steps_reexecuted_count: int = Field(..., ge=0)
    upstream_tokens_consumed: int = Field(..., ge=0)
    run_lock_sha256: str = Field(..., min_length=64, max_length=64)


class StepReplayResponse(BaseModel):
    """Response payload for `POST .../runs/{run_id}/steps/{step_key}/replay`."""

    model_config = ConfigDict(extra="forbid")

    replay: StepReplayResultSchemaItem
    trace_id: str = Field(..., min_length=32, max_length=32)
