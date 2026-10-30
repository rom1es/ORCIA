"""Enriched Visual Workflow Studio (`Contrat`, `Pré-prompt`, `COUCHES · N`)
& Pack Registry (`Story 8.5`).

Implements (`AD-2`, `AD-5`, `AD-14`, `AD-18`, `AD-19`, `AD-20`, `AD-21`):
- 5 lifecycle tabs (`PUBLISHED`, `DRAFT`, `TRASH`, `ACTIVE_RUNS`, `PAUSED_ARBITRATION`)
- Immutable SemVer fork (`v1.0.0` PUBLISHED -> `v1.1.0-draft` DRAFT)
- Top Governance Bar: `ai_pre_prompt` (`sha256` pinned), `WorkflowContract` (`p_1..p_n` +
  mandatory Markdown output sections verified by deterministic structure gate), `triggers`,
  and isolated *What-If* dry-run (`▷ Tester`, `0` external writes)
- Per-step connector least privilege (`READ_ONLY` vs `READ_WRITE_STAGED`)
- `COUCHES · N` inspector on `SUB_WORKFLOW` macro-steps (3 zones, reorder, delete,
  `enabled: false -> SKIPPED` in DBOS checkpoint)
- Business Pack Registry (`/settings/packs`): `ACTIVE | DISABLED | DRAINING | ORPHANED` with
  `409 ERR_RESOURCE_PINNED_BY_ACTIVE_RUNS` guard
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field, replace
from datetime import UTC, datetime
from typing import Any, Literal

from orcia_core.orchestration.cognitive_router import (
    InferenceEffort,
    InferenceTier,
    PinRemovalMode,
)
from orcia_core.orchestration.errors import (
    ObserverModeReadOnlyError,
    ResourceNotFoundError,
    ResourcePinnedByActiveRunsError,
    ScopeAccessDeniedError,
    ValidationDomainError,
)
from orcia_kernel.ids import new_uuid7_str

StudioLifecycleTab = Literal["PUBLISHED", "DRAFT", "TRASH", "ACTIVE_RUNS", "PAUSED_ARBITRATION"]
StepConnectorPrivilegeMode = Literal["READ_ONLY", "READ_WRITE_STAGED"]
SubWorkflowLayerZone = Literal[
    "1_INPUTS_CONTEXT",
    "2_CAPABILITIES_REASONING",
    "3_DELIVERABLES_PRE_GATES",
]
PackLifecycleStatus = Literal["ACTIVE", "DISABLED", "DRAINING", "ORPHANED"]


def _now_iso() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


def compute_text_sha256(text: str) -> str:
    digest = hashlib.sha256(text.strip().encode("utf-8")).hexdigest()
    return f"sha256:{digest}"


def _bump_minor_draft_version(published_version: str) -> str:
    clean = published_version.strip().lstrip("v").split("-")[0]
    parts = clean.split(".")
    if len(parts) == 3 and all(p.isdigit() for p in parts):
        major, minor, _patch = int(parts[0]), int(parts[1]), int(parts[2])
        return f"v{major}.{minor + 1}.0-draft"
    return f"v{clean}.1-draft"


@dataclass(frozen=True, slots=True)
class StudioContractParamSpec:
    """Typed workflow input parameter (`p_1..p_n`) linked to an Ontology concept (`Story 8.5`)."""

    param_key: str
    label: str
    param_type: Literal["string", "number", "boolean", "enum"]
    ontology_concept_uri: str
    required: bool = True
    default_value: str | None = None


@dataclass(frozen=True, slots=True)
class StudioWorkflowContract:
    """Formal workflow input/output contract (`Story 8.5`, `AD-21`)."""

    parameters: tuple[StudioContractParamSpec, ...]
    required_markdown_sections: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class SubWorkflowLayerItem:
    """Sub-layer inside a `SUB_WORKFLOW` macro-step (`COUCHES · N`, `Story 8.5`)."""

    layer_id: str
    order_index: int
    title: str
    zone: SubWorkflowLayerZone
    enabled: bool = True


@dataclass(frozen=True, slots=True)
class StudioStepConnectorBinding:
    """Per-step connector least-privilege binding (`Lire` vs `Écrire`, `Story 8.5`)."""

    connector_uri: str
    privilege_mode: StepConnectorPrivilegeMode = "READ_ONLY"


@dataclass(frozen=True, slots=True)
class StudioWorkflowNode:
    """Visual Studio node (`PROGRAM_EXECUTOR`, `AGENT_EXECUTOR`, or `SUB_WORKFLOW`)."""

    step_key: str
    title: str
    executor_kind: Literal["PROGRAM_EXECUTOR", "AGENT_EXECUTOR", "SUB_WORKFLOW"]
    inference_tier: InferenceTier = "medium"
    effort: InferenceEffort = "default"
    gate_label: str = "DETERMINISTIC_AND_HUMAN"
    connector_bindings: tuple[StudioStepConnectorBinding, ...] = ()
    sub_layers: tuple[SubWorkflowLayerItem, ...] = ()


@dataclass(frozen=True, slots=True)
class StudioWorkflowRevision:
    """Workflow revision managed in the 5-tab Studio (`Story 8.5`, `AD-21`)."""

    id: str
    workflow_uri: str
    title: str
    version: str
    lifecycle_tab: StudioLifecycleTab
    ai_pre_prompt: str
    ai_pre_prompt_sha256: str
    contract: StudioWorkflowContract
    triggers: tuple[str, ...]
    nodes: tuple[StudioWorkflowNode, ...]
    immutable: bool
    updated_at_iso: str = field(default_factory=_now_iso)


@dataclass(frozen=True, slots=True)
class StudioDryRunResult:
    """Isolated *What-If* dry-run execution outcome (`▷ Tester`, `Story 8.5`)."""

    revision_id: str
    workflow_uri: str
    version: str
    validated_inputs: dict[str, Any]
    executed_steps: tuple[str, ...]
    skipped_layers: tuple[str, ...]
    markdown_output: str
    deterministic_structure_gate_passed: bool
    missing_markdown_sections: tuple[str, ...]
    external_writes_count: int = 0


@dataclass(frozen=True, slots=True)
class BusinessPackRegistration:
    """Business Pack registration in `/settings/packs` (`AD-20`, `AD-21`, `Story 8.5`)."""

    pack_key: str
    display_name: str
    version: str
    status: PackLifecycleStatus
    scope_level: Literal["GLOBAL", "BU", "TEAM", "WORKSPACE"]
    scope_id: str
    config_json_schema: dict[str, Any]
    config_values: dict[str, Any]
    installed_in_environment: bool = True
    updated_at_iso: str = field(default_factory=_now_iso)


class WorkflowStudioAndPackService:
    """Domain service for the 5-tab Workflow Studio, `COUCHES · N`, and Pack Registry."""

    def __init__(self) -> None:
        self._revisions: dict[str, StudioWorkflowRevision] = {}
        self._packs: dict[str, BusinessPackRegistration] = {}
        self._pinned_packs_by_key: dict[str, set[str]] = {}
        self._seed_defaults()

    def _seed_defaults(self) -> None:
        pre_prompt = (
            "Respecter l'ontologie N1..N3, citer chaque source et ne jamais inventer de faits."
        )
        rev_id = "0195f000-0000-7000-8000-000000008501"
        self._revisions[rev_id] = StudioWorkflowRevision(
            id=rev_id,
            workflow_uri="orcia://catalog/workflows/architecture-review",
            title="Conception & Validation Technique",
            version="v1.0.0",
            lifecycle_tab="PUBLISHED",
            ai_pre_prompt=pre_prompt,
            ai_pre_prompt_sha256=compute_text_sha256(pre_prompt),
            contract=StudioWorkflowContract(
                parameters=(
                    StudioContractParamSpec(
                        param_key="p_1",
                        label="Périmètre Fonctionnel",
                        param_type="string",
                        ontology_concept_uri="orcia://ontology/n1/functional-scope",
                        required=True,
                    ),
                    StudioContractParamSpec(
                        param_key="p_2",
                        label="Niveau de Criticité",
                        param_type="enum",
                        ontology_concept_uri="orcia://ontology/n1/criticality",
                        required=True,
                        default_value="STANDARD",
                    ),
                ),
                required_markdown_sections=(
                    "## 1. Intention & Cadrage",
                    "## 2. Analyse d'Impact",
                    "## 3. Décisions Retenues",
                ),
            ),
            triggers=("CRON:0 8 * * 1", "OUTBOX:ArtifactProduced"),
            nodes=(
                StudioWorkflowNode(
                    step_key="step-01-framing",
                    title="Cadrage & Intention Métier",
                    executor_kind="AGENT_EXECUTOR",
                    inference_tier="medium",
                    effort="balanced",
                    connector_bindings=(
                        StudioStepConnectorBinding(
                            connector_uri="orcia://connectors/primary-repo",
                            privilege_mode="READ_ONLY",
                        ),
                    ),
                ),
                StudioWorkflowNode(
                    step_key="step-02-macro-analysis",
                    title="Analyse Architecture & Sécurité",
                    executor_kind="SUB_WORKFLOW",
                    inference_tier="complex",
                    effort="deep",
                    connector_bindings=(
                        StudioStepConnectorBinding(
                            connector_uri="orcia://connectors/primary-kb",
                            privilege_mode="READ_ONLY",
                        ),
                        StudioStepConnectorBinding(
                            connector_uri="orcia://connectors/work-tracker",
                            privilege_mode="READ_WRITE_STAGED",
                        ),
                    ),
                    sub_layers=(
                        SubWorkflowLayerItem(
                            layer_id="layer-01",
                            order_index=1,
                            title="Collecte Chunks KB & Contrat",
                            zone="1_INPUTS_CONTEXT",
                            enabled=True,
                        ),
                        SubWorkflowLayerItem(
                            layer_id="layer-02",
                            order_index=2,
                            title="Vérification Axiomes Ontologie N1..N3",
                            zone="2_CAPABILITIES_REASONING",
                            enabled=True,
                        ),
                        SubWorkflowLayerItem(
                            layer_id="layer-03",
                            order_index=3,
                            title="Synthèse Livrable & Pré-Gate",
                            zone="3_DELIVERABLES_PRE_GATES",
                            enabled=True,
                        ),
                    ),
                ),
            ),
            immutable=True,
        )

        ws_id = "0195f000-0000-7000-8000-000000000301"
        self._packs["orcia-pack-sdlc"] = BusinessPackRegistration(
            pack_key="orcia-pack-sdlc",
            display_name="Pack Ingénierie Logicielle (SDLC)",
            version="0.1.0",
            status="ACTIVE",
            scope_level="WORKSPACE",
            scope_id=ws_id,
            config_json_schema={
                "type": "object",
                "properties": {
                    "enforce_intention_before_implementation": {"type": "boolean"},
                    "default_branch": {"type": "string"},
                },
                "required": ["enforce_intention_before_implementation"],
            },
            config_values={
                "enforce_intention_before_implementation": True,
                "default_branch": "main",
            },
            installed_in_environment=True,
        )
        self._packs["orcia-pack-legacy-fin"] = BusinessPackRegistration(
            pack_key="orcia-pack-legacy-fin",
            display_name="Pack Finance Legacy (Désinstallé)",
            version="0.0.9",
            status="ORPHANED",
            scope_level="WORKSPACE",
            scope_id=ws_id,
            config_json_schema={"type": "object", "properties": {}},
            config_values={},
            installed_in_environment=False,
        )

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
            f"{sec}\nContenu simulé pour {validated}."
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
        if actor_role == "OBSERVER":
            raise ObserverModeReadOnlyError(instance=instance)
        pack = self._packs.get(pack_key)
        if pack is None:
            raise ResourceNotFoundError(instance=instance)
        if not pack.installed_in_environment:
            return replace(pack, status="ORPHANED", updated_at_iso=_now_iso())

        if target_status == "DISABLED":
            active_runs = sorted(self._pinned_packs_by_key.get(pack_key, set()))
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
                    self._packs[pack_key] = drained
                    return drained
                if removal_mode == "force" and actor_role != "PLATFORM_ADMIN":
                    raise ScopeAccessDeniedError(
                        detail_override="Only PLATFORM_ADMIN can force-disable a pinned pack.",
                        instance=instance,
                    )
                self._pinned_packs_by_key.pop(pack_key, None)

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
        self._packs[pack_key] = updated
        return updated


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
