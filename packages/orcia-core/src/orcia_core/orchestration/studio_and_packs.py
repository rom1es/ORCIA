"""Enriched Visual Workflow Studio (`Contract`, `Pre-prompt`, `COUCHES · N`)
& Pack Registry (`Story 8.5`).
"""

from __future__ import annotations

from dataclasses import replace
from typing import Any, Literal

from orcia_core.orchestration._studio_and_packs_helpers import (
    configure_pack_registration,
    execute_studio_dry_run,
)
from orcia_core.orchestration._studio_and_packs_models import (
    BusinessPackRegistration,
    PackLifecycleStatus,
    StepConnectorPrivilegeMode,
    StudioContractParamSpec,
    StudioDryRunResult,
    StudioLifecycleTab,
    StudioStepConnectorBinding,
    StudioWorkflowContract,
    StudioWorkflowNode,
    StudioWorkflowRevision,
    SubWorkflowLayerItem,
    SubWorkflowLayerZone,
    _bump_minor_draft_version,
    _now_iso,
    build_default_studio_seeds,
    compute_text_sha256,
)
from orcia_core.orchestration.cognitive_router import (
    PinRemovalMode,
)
from orcia_core.orchestration.errors import (
    ObserverModeReadOnlyError,
    ResourceNotFoundError,
    ValidationDomainError,
)
from orcia_kernel.ids import new_uuid7_str


class WorkflowStudioAndPackService:
    """Domain service for the 5-tab Workflow Studio, `COUCHES · N`, and Pack Registry."""

    def __init__(self) -> None:
        self._revisions, self._packs = build_default_studio_seeds()
        self._pinned_packs_by_key: dict[str, set[str]] = {}

    def get_lifecycle_tab_counts(self) -> dict[StudioLifecycleTab, int]:
        counts: dict[StudioLifecycleTab, int] = {
            "PUBLISHED": 0,
            "DRAFT": 0,
            "TRASH": 0,
            "ACTIVE_RUNS": 1,
            "PAUSED_ARBITRATION": 1,
        }
        for rev in self._revisions.values():
            counts[rev.lifecycle_tab] = counts.get(rev.lifecycle_tab, 0) + 1
        return counts

    def list_revisions(
        self, lifecycle_tab: StudioLifecycleTab | None = None
    ) -> list[StudioWorkflowRevision]:
        items = list(self._revisions.values())
        if lifecycle_tab is not None:
            items = [r for r in items if r.lifecycle_tab == lifecycle_tab]
        return items

    def get_revision(
        self, revision_id: str, *, instance: str | None = None
    ) -> StudioWorkflowRevision:
        rev = self._revisions.get(revision_id)
        if rev is None:
            raise ResourceNotFoundError(instance=instance)
        return rev

    def fork_published_to_draft(
        self,
        revision_id: str,
        *,
        actor_role: str = "TEAM_LEAD",
        instance: str | None = None,
    ) -> StudioWorkflowRevision:
        """Fork an immutable `PUBLISHED` revision (`v1.0.0`) into a mutable `v1.1.0-draft`."""
        if actor_role == "OBSERVER":
            raise ObserverModeReadOnlyError(instance=instance)
        source = self.get_revision(revision_id, instance=instance)
        draft_version = _bump_minor_draft_version(source.version)
        draft = replace(
            source,
            id=new_uuid7_str(),
            version=draft_version,
            lifecycle_tab="DRAFT",
            immutable=False,
            updated_at_iso=_now_iso(),
        )
        self._revisions[draft.id] = draft
        return draft

    def update_draft_governance(
        self,
        revision_id: str,
        *,
        ai_pre_prompt: str | None = None,
        contract: StudioWorkflowContract | None = None,
        triggers: tuple[str, ...] | None = None,
        actor_role: str = "TEAM_LEAD",
        instance: str | None = None,
    ) -> StudioWorkflowRevision:
        """Update `Pré-prompt IA`, `Contrat du workflow` or `Déclencheurs` on a draft revision."""
        if actor_role == "OBSERVER":
            raise ObserverModeReadOnlyError(instance=instance)
        rev = self.get_revision(revision_id, instance=instance)
        if rev.immutable or rev.lifecycle_tab == "PUBLISHED":
            raise ValidationDomainError(
                detail_override=(
                    f"Published revision '{rev.version}' is immutable. Fork to a draft revision "
                    "before editing (AD-21)."
                ),
                instance=instance,
            )
        next_prompt = ai_pre_prompt.strip() if ai_pre_prompt is not None else rev.ai_pre_prompt
        updated = replace(
            rev,
            ai_pre_prompt=next_prompt,
            ai_pre_prompt_sha256=compute_text_sha256(next_prompt),
            contract=contract if contract is not None else rev.contract,
            triggers=triggers if triggers is not None else rev.triggers,
            updated_at_iso=_now_iso(),
        )
        self._revisions[revision_id] = updated
        return updated

    def update_sub_workflow_layer(
        self,
        revision_id: str,
        *,
        step_key: str,
        layer_id: str,
        enabled: bool | None = None,
        new_order_index: int | None = None,
        delete: bool = False,
        actor_role: str = "TEAM_LEAD",
        instance: str | None = None,
    ) -> StudioWorkflowRevision:
        """Toggle (`👁️ enabled: false -> SKIPPED`), reorder or delete a layer in `COUCHES · N`."""
        if actor_role == "OBSERVER":
            raise ObserverModeReadOnlyError(instance=instance)
        rev = self.get_revision(revision_id, instance=instance)
        if rev.immutable:
            raise ValidationDomainError(
                detail_override="Cannot mutate layers on an immutable PUBLISHED revision.",
                instance=instance,
            )

        new_nodes: list[StudioWorkflowNode] = []
        found = False
        for node in rev.nodes:
            if node.step_key != step_key:
                new_nodes.append(node)
                continue
            updated_layers: list[SubWorkflowLayerItem] = []
            for layer in node.sub_layers:
                if layer.layer_id != layer_id:
                    updated_layers.append(layer)
                    continue
                found = True
                if delete:
                    continue
                updated_layers.append(
                    replace(
                        layer,
                        enabled=enabled if enabled is not None else layer.enabled,
                        order_index=(
                            new_order_index if new_order_index is not None else layer.order_index
                        ),
                    )
                )
            updated_layers.sort(key=lambda item: item.order_index)
            new_nodes.append(replace(node, sub_layers=tuple(updated_layers)))

        if not found:
            raise ResourceNotFoundError(
                detail_override=f"Layer '{layer_id}' not found on step '{step_key}'.",
                instance=instance,
            )
        updated_rev = replace(rev, nodes=tuple(new_nodes), updated_at_iso=_now_iso())
        self._revisions[revision_id] = updated_rev
        return updated_rev

    def run_what_if_dry_run(
        self,
        revision_id: str,
        *,
        input_values: dict[str, Any],
        preview_markdown_output: str | None = None,
        instance: str | None = None,
    ) -> StudioDryRunResult:
        """Execute an isolated *What-If* dry-run (`▷ Tester`) from the Workflow Contract."""
        rev = self.get_revision(revision_id, instance=instance)
        return execute_studio_dry_run(
            rev,
            input_values=input_values,
            preview_markdown_output=preview_markdown_output,
            instance=instance,
        )

    def list_packs(self) -> list[BusinessPackRegistration]:
        return list(self._packs.values())

    def pin_pack_for_active_run(self, pack_key: str, run_id: str) -> None:
        self._pinned_packs_by_key.setdefault(pack_key, set()).add(run_id)

    def configure_or_toggle_pack(
        self,
        pack_key: str,
        *,
        target_status: Literal["ACTIVE", "DISABLED"] = "ACTIVE",
        config_values: dict[str, Any] | None = None,
        removal_mode: PinRemovalMode = "reject",
        actor_role: str = "PLATFORM_ADMIN",
        instance: str | None = None,
    ) -> BusinessPackRegistration:
        """Activate, configure or deactivate a Business Pack (`/settings/packs`, `Story 8.5`)."""
        return configure_pack_registration(
            self._packs,
            self._pinned_packs_by_key,
            pack_key,
            target_status=target_status,
            config_values=config_values,
            removal_mode=removal_mode,
            actor_role=actor_role,
            instance=instance,
        )


__all__ = [
    "BusinessPackRegistration",
    "PackLifecycleStatus",
    "StepConnectorPrivilegeMode",
    "StudioContractParamSpec",
    "StudioDryRunResult",
    "StudioLifecycleTab",
    "StudioStepConnectorBinding",
    "StudioWorkflowContract",
    "StudioWorkflowNode",
    "StudioWorkflowRevision",
    "SubWorkflowLayerItem",
    "SubWorkflowLayerZone",
    "WorkflowStudioAndPackService",
    "compute_text_sha256",
]
