"""Dry-run & Pack Registry helpers for `WorkflowStudioAndPackService` (`Story 8.5`)."""

from __future__ import annotations

from dataclasses import replace
from typing import Any, Literal

from orcia_core.orchestration._studio_and_packs_locales import get_studio_seed_copy
from orcia_core.orchestration._studio_and_packs_models import (
    BusinessPackRegistration,
    StudioDryRunResult,
    StudioWorkflowRevision,
    _now_iso,
)
from orcia_core.orchestration.cognitive_router import PinRemovalMode
from orcia_core.orchestration.errors import (
    ObserverModeReadOnlyError,
    ResourceNotFoundError,
    ResourcePinnedByActiveRunsError,
    ScopeAccessDeniedError,
    ValidationDomainError,
)


def execute_studio_dry_run(
    rev: StudioWorkflowRevision,
    *,
    input_values: dict[str, Any],
    preview_markdown_output: str | None = None,
    instance: str | None = None,
) -> StudioDryRunResult:
    """Validate contract inputs and render isolated *What-If* dry-run output."""
    validated: dict[str, Any] = {}
    for param in rev.contract.parameters:
        val = input_values.get(param.param_key, param.default_value)
        if param.required and (val is None or str(val).strip() == ""):
            raise ValidationDomainError(
                detail_override=(
                    f"Missing required contract parameter '{param.param_key}' ({param.label})."
                ),
                instance=instance,
            )
        validated[param.param_key] = val

    executed_steps: list[str] = []
    skipped_layers: list[str] = []
    for node in rev.nodes:
        executed_steps.append(node.step_key)
        for layer in node.sub_layers:
            if not layer.enabled:
                skipped_layers.append(f"{node.step_key}:{layer.layer_id}:SKIPPED")

    default_md = "\n\n".join(
        get_studio_seed_copy()["dry_run_content"].format(sec=sec, validated=validated)
        for sec in rev.contract.required_markdown_sections
    )
    md_out = preview_markdown_output if preview_markdown_output is not None else default_md
    missing = tuple(sec for sec in rev.contract.required_markdown_sections if sec not in md_out)
    return StudioDryRunResult(
        revision_id=rev.id,
        workflow_uri=rev.workflow_uri,
        version=rev.version,
        validated_inputs=validated,
        executed_steps=tuple(executed_steps),
        skipped_layers=tuple(skipped_layers),
        markdown_output=md_out,
        deterministic_structure_gate_passed=len(missing) == 0,
        missing_markdown_sections=missing,
        external_writes_count=0,
    )


def configure_pack_registration(
    packs: dict[str, BusinessPackRegistration],
    pinned_packs_by_key: dict[str, set[str]],
    pack_key: str,
    *,
    target_status: Literal["ACTIVE", "DISABLED"] = "ACTIVE",
    config_values: dict[str, Any] | None = None,
    removal_mode: PinRemovalMode = "reject",
    actor_role: str = "PLATFORM_ADMIN",
    instance: str | None = None,
) -> BusinessPackRegistration:
    """Activate, configure, or deactivate a registered Business Pack."""
    if actor_role == "OBSERVER":
        raise ObserverModeReadOnlyError(instance=instance)
    pack = packs.get(pack_key)
    if pack is None:
        raise ResourceNotFoundError(instance=instance)
    if not pack.installed_in_environment:
        return replace(pack, status="ORPHANED", updated_at_iso=_now_iso())

    if target_status == "DISABLED":
        active_runs = sorted(pinned_packs_by_key.get(pack_key, set()))
        if active_runs:
            if removal_mode == "reject":
                raise ResourcePinnedByActiveRunsError(
                    detail_override=(
                        f"Pack '{pack_key}' is pinned by active runs: "
                        f"{', '.join(active_runs)}. Use Drain or Force."
                    ),
                    instance=instance,
                )
            if removal_mode == "drain":
                drained = replace(pack, status="DRAINING", updated_at_iso=_now_iso())
                packs[pack_key] = drained
                return drained
            if removal_mode == "force" and actor_role != "PLATFORM_ADMIN":
                raise ScopeAccessDeniedError(
                    detail_override="Only PLATFORM_ADMIN can force-disable a pinned pack.",
                    instance=instance,
                )
            pinned_packs_by_key.pop(pack_key, None)

    merged_vals = dict(pack.config_values)
    if config_values is not None:
        required_keys = pack.config_json_schema.get("required", [])
        merged_vals.update(config_values)
        for req_key in required_keys:
            if req_key not in merged_vals:
                raise ValidationDomainError(
                    detail_override=f"Missing required pack config key: '{req_key}'.",
                    instance=instance,
                )

    updated = replace(
        pack,
        status=target_status,
        config_values=merged_vals,
        updated_at_iso=_now_iso(),
    )
    packs[pack_key] = updated
    return updated


__all__ = ["configure_pack_registration", "execute_studio_dry_run"]
