"""Delete Impact & Drain Helpers for `AiModelsHubService` (`Story 17.5`, `Story 26.6a`)."""

from __future__ import annotations

from dataclasses import replace

from orcia_core.orchestration.ai_models_errors import LastTierModelInUseError
from orcia_core.orchestration.ai_models_records import (
    AiModelDeleteImpact,
    AiModelMappingRecord,
    PinRemovalMode,
)
from orcia_core.orchestration.errors import (
    ObserverModeReadOnlyError,
    ResourcePinnedByActiveRunsError,
)


def evaluate_inmemory_delete_impact(
    *,
    mappings: dict[str, AiModelMappingRecord],
    workflows_tier_reqs: dict[str, set[str]],
    active_runs: dict[str, set[str]],
    mapping_id: str,
    current: AiModelMappingRecord,
) -> AiModelDeleteImpact:
    """Evaluate active run pins and workflow dependencies prior to deletion/drain."""
    other_active = [
        m
        for m in mappings.values()
        if m.id != mapping_id
        and m.inference_tier == current.inference_tier
        and m.is_active
        and not m.draining
    ]
    wf_deps = tuple(sorted(workflows_tier_reqs.get(current.inference_tier, set())))
    run_pins = tuple(sorted(active_runs.get(mapping_id, set())))
    return AiModelDeleteImpact(
        mapping_id=mapping_id,
        inference_tier=current.inference_tier,
        model_name=current.model_name,
        remaining_active_for_tier=len(other_active),
        dependent_workflows_count=len(wf_deps),
        dependent_workflow_ids=wf_deps,
        pinned_active_runs_count=len(run_pins),
        pinned_run_ids=run_pins,
        is_last_active_for_tier=len(other_active) == 0,
    )


def apply_inmemory_delete_or_drain(
    *,
    mappings: dict[str, AiModelMappingRecord],
    impact: AiModelDeleteImpact,
    current: AiModelMappingRecord,
    mapping_id: str,
    mode: PinRemovalMode,
    actor_role: str,
    now_iso: str,
    instance: str | None,
) -> AiModelMappingRecord | None:
    """Delete or mark draining an AI model mapping enforcing safety guards."""
    if actor_role == "OBSERVER":
        raise ObserverModeReadOnlyError(instance=instance)
    if impact.dependent_workflows_count > 0 and impact.is_last_active_for_tier and mode != "force":
        raise LastTierModelInUseError(instance=instance)
    if impact.pinned_active_runs_count > 0:
        if mode == "reject":
            raise ResourcePinnedByActiveRunsError(instance=instance)
        if mode == "drain":
            draining = replace(current, draining=True, is_active=False, updated_at=now_iso)
            mappings[mapping_id] = draining
            return draining
    mappings.pop(mapping_id, None)
    return None
