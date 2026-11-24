"""Dataclasses, constants & seed builders for Workflow Studio & Pack Registry (`Story 8.5`)."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any, Literal

from orcia_core.orchestration._studio_and_packs_locales import get_studio_seed_copy
from orcia_core.orchestration.cognitive_router import InferenceEffort, InferenceTier
from orcia_kernel.enums import DEFAULT_LOCALE, SupportedLocale

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
    """Per-step connector least-privilege binding (`READ_ONLY` vs `READ_WRITE_STAGED`)."""

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
    """Isolated *What-If* dry-run execution outcome (`Story 8.5`)."""

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


def build_default_studio_seeds(
    locale: SupportedLocale = DEFAULT_LOCALE,
) -> tuple[dict[str, StudioWorkflowRevision], dict[str, BusinessPackRegistration]]:
    """Build default Studio workflow revisions and Business Pack registrations."""
    sc = get_studio_seed_copy(locale)
    pre_prompt = sc["pre_prompt"]
    rev_id = "0195f000-0000-7000-8000-000000008501"
    revisions = {
        rev_id: StudioWorkflowRevision(
            id=rev_id,
            workflow_uri="orcia://catalog/workflows/architecture-review",
            title=sc["wf_title"],
            version="v1.0.0",
            lifecycle_tab="PUBLISHED",
            ai_pre_prompt=pre_prompt,
            ai_pre_prompt_sha256=compute_text_sha256(pre_prompt),
            contract=StudioWorkflowContract(
                parameters=(
                    StudioContractParamSpec(
                        param_key="p_1",
                        label=sc["p1_label"],
                        param_type="string",
                        ontology_concept_uri="orcia://ontology/n1/functional-scope",
                        required=True,
                    ),
                    StudioContractParamSpec(
                        param_key="p_2",
                        label=sc["p2_label"],
                        param_type="enum",
                        ontology_concept_uri="orcia://ontology/n1/criticality",
                        required=True,
                        default_value="STANDARD",
                    ),
                ),
                required_markdown_sections=(sc["sec1"], sc["sec2"], sc["sec3"]),
            ),
            triggers=("CRON:0 8 * * 1", "OUTBOX:ArtifactProduced"),
            nodes=(
                StudioWorkflowNode(
                    step_key="step-01-framing",
                    title=sc["node1_title"],
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
                    title=sc["node2_title"],
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
                            title=sc["layer1_title"],
                            zone="1_INPUTS_CONTEXT",
                            enabled=True,
                        ),
                        SubWorkflowLayerItem(
                            layer_id="layer-02",
                            order_index=2,
                            title=sc["layer2_title"],
                            zone="2_CAPABILITIES_REASONING",
                            enabled=True,
                        ),
                        SubWorkflowLayerItem(
                            layer_id="layer-03",
                            order_index=3,
                            title=sc["layer3_title"],
                            zone="3_DELIVERABLES_PRE_GATES",
                            enabled=True,
                        ),
                    ),
                ),
            ),
            immutable=True,
        )
    }
    ws_id = "0195f000-0000-7000-8000-000000000301"
    packs = {
        "orcia-pack-sdlc": BusinessPackRegistration(
            pack_key="orcia-pack-sdlc",
            display_name=sc["pack_sdlc_name"],
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
        ),
        "orcia-pack-legacy-fin": BusinessPackRegistration(
            pack_key="orcia-pack-legacy-fin",
            display_name=sc["pack_legacy_name"],
            version="0.0.9",
            status="ORPHANED",
            scope_level="WORKSPACE",
            scope_id=ws_id,
            config_json_schema={"type": "object", "properties": {}},
            config_values={},
            installed_in_environment=False,
        ),
    }
    return revisions, packs


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
    "_bump_minor_draft_version",
    "_now_iso",
    "build_default_studio_seeds",
    "compute_text_sha256",
]
