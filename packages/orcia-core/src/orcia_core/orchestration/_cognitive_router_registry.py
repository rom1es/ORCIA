"""Model mapping resolution and pin lifecycle helpers (`Story 8.2`).

Extracted to ensure router file maintains strict line count boundaries (< 350 lines).
"""

from __future__ import annotations

from dataclasses import replace

from orcia_core.orchestration._cognitive_router_models import (
    InferenceEffort,
    PinRemovalMode,
    ResolvedInferenceTier,
    WorkspaceLlmTierMapping,
    now_iso,
)
from orcia_core.orchestration.errors import (
    ObserverModeReadOnlyError,
    ResourceNotFoundError,
    ResourcePinnedByActiveRunsError,
    ScopeAccessDeniedError,
    TierModelNotConfiguredError,
)


def resolve_tier_mapping(
    mappings: dict[str, WorkspaceLlmTierMapping],
    *,
    scope_id: str,
    tier: ResolvedInferenceTier,
    effort: InferenceEffort = "default",
    allow_draining: bool = False,
) -> WorkspaceLlmTierMapping:
    candidates = [
        m
        for m in mappings.values()
        if m.inference_tier == tier
        and m.is_active
        and (allow_draining or not m.draining)
        and (m.scope_id == scope_id or m.scope_level == "GLOBAL")
    ]
    if not candidates:
        candidates = [
            m
            for m in mappings.values()
            if m.inference_tier == tier and m.is_active and (allow_draining or not m.draining)
        ]
    if not candidates:
        raise TierModelNotConfiguredError(
            detail_override=(
                f"No active AI model configured for tier '{tier}'. "
                "Please configure and activate a model for this tier in /settings/ai-models."
            )
        )
    exact_effort = [m for m in candidates if m.effort == effort]
    chosen_pool = exact_effort if exact_effort else candidates
    chosen_pool.sort(key=lambda m: (0 if m.scope_id == scope_id else 1, m.fallback_order))
    return chosen_pool[0]


def delete_or_drain_mapping_helper(
    mappings: dict[str, WorkspaceLlmTierMapping],
    pinned_models_by_mapping_id: dict[str, set[str]],
    mapping_id: str,
    *,
    mode: PinRemovalMode = "reject",
    actor_role: str = "PLATFORM_ADMIN",
    instance: str | None = None,
) -> WorkspaceLlmTierMapping | None:
    if actor_role == "OBSERVER":
        raise ObserverModeReadOnlyError(instance=instance)
    mapping = mappings.get(mapping_id)
    if mapping is None:
        raise ResourceNotFoundError(instance=instance)

    active_runs = sorted(pinned_models_by_mapping_id.get(mapping_id, set()))
    if active_runs:
        if mode == "reject":
            raise ResourcePinnedByActiveRunsError(
                detail_override=(
                    f"Model '{mapping.model_name}' ({mapping_id}) is pinned by active runs: "
                    f"{', '.join(active_runs)}. Use mode='drain' or mode='force'."
                ),
                instance=instance,
            )
        if mode == "drain":
            drained = replace(mapping, draining=True, updated_at_iso=now_iso())
            mappings[mapping_id] = drained
            return drained
        if mode == "force":
            if actor_role != "PLATFORM_ADMIN":
                raise ScopeAccessDeniedError(
                    detail_override="Only PLATFORM_ADMIN can force-remove a pinned model.",
                    instance=instance,
                )
            pinned_models_by_mapping_id.pop(mapping_id, None)
            mappings.pop(mapping_id, None)
            return None

    mappings.pop(mapping_id, None)
    return None


__all__ = [
    "delete_or_drain_mapping_helper",
    "resolve_tier_mapping",
]
