"""Data Models & Boundary Validators for Assistant 4-Level Governance (`Story 10.1`)."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from typing import Any, Literal

from orcia_core.orchestration.errors import ImmutableHarnessBoundaryError

AssistantResponseTone = Literal["SYNTHETIC", "BALANCED", "DETAILED_CODE"]
AssistantResponseFormat = Literal["BULLETS_SUMMARY", "STRUCTURED_SECTIONS", "STEP_BY_STEP"]
AssistantOverrideScope = Literal["TEAM", "WORKSPACE", "USER"]
AssistantArbitrationPolicy = Literal["PAUSE_AND_ESCALATE", "AUTO_RESOLVE_WITH_TRACE"]

ENTRY_HARNESS_NODE_ID: str = "ENTRY_BOUNDARY_HARNESS"
EXIT_HARNESS_NODE_ID: str = "EXIT_BOUNDARY_HARNESS"
REQUIRED_CORE_NODE_IDS: tuple[str, ...] = (
    "1_INTENT_ROUTER",
    "2_QUERY_PLANNER_AND_ONTOLOGY_EXPANSION",
    "3_PARALLEL_FAN_OUT",
    "4_CRITICAL_TRIAGE_AND_AXIOM_VERIFICATION",
    "5_PROFILE_ADAPTIVE_SYNTHESIZER",
)


def _compute_sha256_hex(payload: Any) -> str:
    raw = (
        payload
        if isinstance(payload, str)
        else json.dumps(payload, sort_keys=True, ensure_ascii=False)
    )
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


@dataclass(frozen=True, slots=True)
class UserLayerPreferences:
    """Tab 1 (`Mes préférences — Couche 5 USER`) settings (`Story 10.1`)."""

    user_id: str
    workspace_id: str
    response_tone: AssistantResponseTone = "BALANCED"
    favorite_format: AssistantResponseFormat = "STRUCTURED_SECTIONS"
    default_hat: str = "PM"
    personal_instructions: str = "Toujours citer les preuves [S1] et synthétiser les risques."
    sha256: str = ""


@dataclass(frozen=True, slots=True)
class WorkspaceLayerSettings:
    """Tab 2 (`Réglages de l'Espace — Couche 4 WORKSPACE`) settings (`Story 10.1`)."""

    workspace_id: str
    workspace_instructions: str = (
        "Respecter le glossaire actif de l'Espace et privilégier les sources RÉFÉRENCE."
    )
    default_checked_sources: tuple[str, ...] = (
        "orcia://sources/repo-main",
        "orcia://sources/architecture-kb",
        "orcia://sources/project-delivery",
    )
    recommended_agents: tuple[str, ...] = ("@spec-architect", "@security-reviewer")
    arbitration_policy: AssistantArbitrationPolicy = "PAUSE_AND_ESCALATE"
    welcome_suggestions: tuple[str, ...] = (
        "Synthétiser les derniers écarts documentaires de l'Espace",
        "Vérifier la conformité d'un ticket avec l'ontologie N1–N3",
        "Préparer un dossier de cadrage technique",
        "Analyser l'impact d'une modification d'API",
    )
    mcp_expose_assistant: bool = True
    mcp_frozen_by_upper_layer: bool = False
    mcp_frozen_origin: Literal["PLATFORM", "TEAM"] | None = None
    mcp_endpoint_url: str = "/api/v1/mcp/spaces/default"
    mcp_tool_name: str = "assistant.ask"
    mcp_ide_config_json: str = ""
    sha256: str = ""


@dataclass(frozen=True, slots=True)
class AssembledLayerPreviewItem:
    """Single layer displayed in Tab 3 (`Assemblage complet — Lecture seule`)."""

    layer_number: int
    layer_code: Literal[
        "1_CONSTITUTION",
        "2_PACK_METIER",
        "3_EQUIPE",
        "4_ESPACE",
        "5_UTILISATEUR",
    ]
    label: str
    immutable: bool
    origin_badge: Literal["SOCLE", "PACK", "EQUIPE", "ESPACE", "UTILISATEUR"]
    content: str
    sha256: str


@dataclass(frozen=True, slots=True)
class AssistantStudioNodeSpec:
    """Node in Mode B Studio `@xyflow/react` graph."""

    node_id: str
    title: str
    node_order: int
    is_harness_boundary: bool
    locked_by: Literal["HARNESS", "PLATFORM", "TEAM"] | None
    enabled: bool = True
    sub_layers_count: int = 3
    enabled_sub_layers: tuple[str, ...] = (
        "1_INPUT_VALIDATION",
        "2_CORE_PROCESSING",
        "3_OUTPUT_TRIAGE",
    )
    sub_agent_uri: str | None = None


@dataclass(frozen=True, slots=True)
class AssistantStudioGraphState:
    """Mode B Studio state for `orcia://system/workflows/assistant-agent` (`Story 10.1`)."""

    workflow_uri: str
    scope_level: Literal["DEFAULT", "TEAM", "WORKSPACE"]
    scope_id: str
    ai_pre_prompt: str
    nodes: tuple[AssistantStudioNodeSpec, ...]
    override_key: str | None
    sha256: str


@dataclass(frozen=True, slots=True)
class AssistantCustomizationOverrideRecord:
    """Row representation for `workspace_customization_overrides` (`Story 10.1`)."""

    id: str
    override_key: str
    org_unit_id: str | None
    workspace_id: str | None
    user_id: str | None
    target_uri: str
    override_layer: AssistantOverrideScope
    override_manifest_jsonb: dict[str, Any]
    sha256: str


@dataclass(frozen=True, slots=True)
class AssistantGovernanceView:
    """Consolidated response for `GET /api/v1/assistant/governance` (`Story 10.1`)."""

    workspace_id: str
    can_edit_workspace_layer: bool
    can_open_studio_mode_b: bool
    user_preferences: UserLayerPreferences
    workspace_settings: WorkspaceLayerSettings
    assembled_layers: tuple[AssembledLayerPreviewItem, ...]
    studio_graph: AssistantStudioGraphState
    override_records: tuple[AssistantCustomizationOverrideRecord, ...] = field(
        default_factory=tuple
    )


def build_default_studio_nodes() -> tuple[AssistantStudioNodeSpec, ...]:
    """Return the canonical 5 nodes wrapped inside the 2 immutable `AssistantHarness` bounds."""
    return (
        AssistantStudioNodeSpec(
            node_id=ENTRY_HARNESS_NODE_ID,
            title="🔒 Borne d'Entrée — AssistantHarness (PII/Secrets & Contexte)",
            node_order=0,
            is_harness_boundary=True,
            locked_by="HARNESS",
            enabled=True,
            sub_layers_count=2,
            enabled_sub_layers=("1_PASSTHROUGH_IDENTITY", "2_PII_REVERSIBLE_SCRUBBER"),
        ),
        AssistantStudioNodeSpec(
            node_id="1_INTENT_ROUTER",
            title="1. Routeur d'Intention & Casquette",
            node_order=1,
            is_harness_boundary=False,
            locked_by="PLATFORM",
            enabled=True,
            sub_layers_count=3,
        ),
        AssistantStudioNodeSpec(
            node_id="2_QUERY_PLANNER_AND_ONTOLOGY_EXPANSION",
            title="2. Query Planner & Expansion Ontologique",
            node_order=2,
            is_harness_boundary=False,
            locked_by=None,
            enabled=True,
            sub_layers_count=3,
        ),
        AssistantStudioNodeSpec(
            node_id="3_PARALLEL_FAN_OUT",
            title="3. Fan-Out Parallèle (RAG, Glossaire, Outils MCP)",
            node_order=3,
            is_harness_boundary=False,
            locked_by=None,
            enabled=True,
            sub_layers_count=4,
        ),
        AssistantStudioNodeSpec(
            node_id="4_CRITICAL_TRIAGE_AND_AXIOM_VERIFICATION",
            title="4. Tri Critique & Vérification d'Axiomes",
            node_order=4,
            is_harness_boundary=False,
            locked_by=None,
            enabled=True,
            sub_layers_count=3,
        ),
        AssistantStudioNodeSpec(
            node_id="5_PROFILE_ADAPTIVE_SYNTHESIZER",
            title="5. Synthétiseur Adaptatif au Profil Humain",
            node_order=5,
            is_harness_boundary=False,
            locked_by=None,
            enabled=True,
            sub_layers_count=3,
        ),
        AssistantStudioNodeSpec(
            node_id=EXIT_HARNESS_NODE_ID,
            title="🔒 Borne de Sortie — AssistantHarness (Anti-Citation Fantôme & Verrou V5)",
            node_order=6,
            is_harness_boundary=True,
            locked_by="HARNESS",
            enabled=True,
            sub_layers_count=2,
            enabled_sub_layers=("1_CITATION_VERIFIER", "2_HUMAN_ANCHOR_AND_V5_GUARD"),
        ),
    )


def validate_harness_boundaries(nodes: tuple[AssistantStudioNodeSpec, ...]) -> None:
    """Reject any Studio modification tampering with immutable AssistantHarness boundaries."""
    if len(nodes) < 3:
        raise ImmutableHarnessBoundaryError()
    first, last = nodes[0], nodes[-1]
    if (
        first.node_id != ENTRY_HARNESS_NODE_ID
        or not first.is_harness_boundary
        or not first.enabled
        or first.locked_by != "HARNESS"
    ):
        raise ImmutableHarnessBoundaryError(
            detail_override="Entry boundary ENTRY_BOUNDARY_HARNESS must remain enabled and locked."
        )
    if (
        last.node_id != EXIT_HARNESS_NODE_ID
        or not last.is_harness_boundary
        or not last.enabled
        or last.locked_by != "HARNESS"
    ):
        raise ImmutableHarnessBoundaryError(
            detail_override="Exit boundary EXIT_BOUNDARY_HARNESS must remain enabled and locked."
        )
    node_ids = {n.node_id: n for n in nodes}
    for core_id in REQUIRED_CORE_NODE_IDS:
        core_node = node_ids.get(core_id)
        if core_node is None:
            raise ImmutableHarnessBoundaryError(
                detail_override=f"Mandatory system node {core_id} cannot be removed."
            )
        if core_node.locked_by in ("HARNESS", "PLATFORM", "TEAM") and not core_node.enabled:
            raise ImmutableHarnessBoundaryError(
                detail_override=(
                    f"Locked system node {core_id} ({core_node.locked_by}) cannot be disabled."
                )
            )
