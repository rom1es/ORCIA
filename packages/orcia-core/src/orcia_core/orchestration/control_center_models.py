"""Immutable Domain Models for Unified Workspace Control Center (`Story 5.2`, `AD-14`)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from orcia_core.permissions.models import AccessMode, OrgUnitNode

ScopeType = Literal["GLOBAL", "BU", "TEAM", "WORKSPACE"]
ProductLifecyclePhase = Literal["RUN", "BUILD", "MIGRATION"]

LIFECYCLE_SUGGESTED_WORKFLOWS: dict[ProductLifecyclePhase, tuple[str, ...]] = {
    "RUN": (
        "diagnostic-incident-postmortem",
        "audit-conformite-continu",
        "optimisation-finops-production",
    ),
    "BUILD": (
        "conception-architecture-cible",
        "livraison-incrementale-gouvernee",
        "revue-securite-et-gates",
    ),
    "MIGRATION": (
        "cartographie-dependances-existant",
        "plan-bascule-sans-interruption",
        "validation-non-regression-cible",
    ),
}


@dataclass(frozen=True, slots=True)
class GuidanceStepSpec:
    """One of the 5 methodological steps displayed in `<GuidanceDrawer />` (Tab 2)."""

    step_number: int
    title_fr: str
    description_fr: str
    action_command: str


DEFAULT_GUIDANCE_DRAWER_STEPS: tuple[GuidanceStepSpec, ...] = (
    GuidanceStepSpec(
        step_number=1,
        title_fr="1. Qualifier la phase du Produit / Workspace",
        description_fr="Sélectionner RUN, BUILD ou MIGRATION dans l'onglet Gouvernance.",
        action_command="set-lifecycle-phase",
    ),
    GuidanceStepSpec(
        step_number=2,
        title_fr="2. Rattacher les sources dédiées et partagées",
        description_fr=(
            "Connecter les dépôts documentaires, bases et référentiels avec un TTL de fraîcheur."
        ),
        action_command="init-datasource",
    ),
    GuidanceStepSpec(
        step_number=3,
        title_fr="3. Configurer l'identité d'exécution (Passthrough vs Compte de Service)",
        description_fr=(
            "Choisir passthrough (défaut sécurisé) ou service_account pour l'indexation."
        ),
        action_command="configure-execution-identity",
    ),
    GuidanceStepSpec(
        step_number=4,
        title_fr="4. Vérifier l'alignement dans le Graphe Tripartite",
        description_fr=(
            "Inspecter les alertes [STALE_WARNING] et lancer une synchronisation RAG hybride."
        ),
        action_command="sync-tripartite-graph",
    ),
    GuidanceStepSpec(
        step_number=5,
        title_fr="5. Activer les Workflows et Surcharges 4 niveaux",
        description_fr="Valider les Gates de gouvernance et lancer un premier Run supervisé.",
        action_command="launch-supervised-run",
    ),
)


@dataclass(frozen=True, slots=True)
class SupervisedRunItem:
    """Workflow Run entry in Tab 1 (`RUNS_AND_ARTIFACTS`) & `⌘K` palette (`FR-1`, `FR-3`)."""

    run_id: str
    workspace_id: str
    workspace_name: str
    workflow_key: str
    title: str
    status: Literal["RUNNING", "PAUSED_HUMAN_GATE", "PAUSED_ARBITRATION", "COMPLETED"]
    current_step_id: str
    current_step_key: str
    execution_mode: Literal["COACHING", "FAST_PATH"]
    access_mode: AccessMode
    claimed_by_user_id: str | None
    claimed_by_display_name: str | None
    budget_consumed_usd: float
    blackboard_summary: str
    blackboard_payload_masked: bool = False


@dataclass(frozen=True, slots=True)
class SupervisedDatasourceItem:
    """Attached datasource entry in Tab 2 (`DATASOURCES`)."""

    id: str
    workspace_id: str
    workspace_name: str
    alias: str
    scheme: str
    uri: str
    role: str
    execution_identity: str
    freshness_ttl_days: int
    tripartite_status: Literal["ALIGNED", "STALE_WARNING", "INDEXING"]


@dataclass(frozen=True, slots=True)
class DeclarativeOverrideLayer:
    """4-level override item in Tab 3 (`1. BASE -> 2. TEAM -> 3. WORKSPACE -> 4. USER`)."""

    workflow_key: str
    title: str
    base_layer: str
    team_override: str
    workspace_override: str
    user_override: str
    spine_contract_ref: str


@dataclass(frozen=True, slots=True)
class WorkspaceGovernanceItem:
    """Workspace product lifecycle & governance summary in Tab 4 (`TEAMS_AND_GOVERNANCE`)."""

    workspace_id: str
    slug: str
    name: str
    owner_org_unit_id: str
    visibility_mode: Literal["STANDARD", "CONFIDENTIAL_RESTRICTED"]
    lifecycle_phase: ProductLifecyclePhase
    suggested_workflows: tuple[str, ...]
    access_mode: AccessMode
    finops_cost_usd: float | None
    blackboard_payload_masked: bool


@dataclass(frozen=True, slots=True)
class CommandPaletteEntry:
    """Universal `⌘K` Command Palette item with keyboard shortcut (`UX-DR13`, `< 1 s`)."""

    entry_id: str
    category: Literal["RUN", "WORKSPACE", "NAVIGATION", "ONTOLOGY", "CATALOG"]
    label_fr: str
    subtitle_fr: str
    shortcut: str
    target_route: str
    access_mode: AccessMode | None = None


@dataclass(frozen=True, slots=True)
class ControlCenterOverview:
    """Consolidated 4-tab fractal payload for `GET /api/v1/control-center/overview`."""

    scope_type: ScopeType
    scope_id: str
    scope_label: str
    viewer_access_mode: AccessMode
    observer_banner_fr: str | None
    consolidated_finops_usd: float
    contributor_runs: tuple[SupervisedRunItem, ...]
    observer_runs: tuple[SupervisedRunItem, ...]
    datasources: tuple[SupervisedDatasourceItem, ...]
    guidance_steps: tuple[GuidanceStepSpec, ...]
    workflow_overrides: tuple[DeclarativeOverrideLayer, ...]
    org_units: tuple[OrgUnitNode, ...]
    workspaces_governance: tuple[WorkspaceGovernanceItem, ...]


__all__ = [
    "CommandPaletteEntry",
    "ControlCenterOverview",
    "DEFAULT_GUIDANCE_DRAWER_STEPS",
    "DeclarativeOverrideLayer",
    "GuidanceStepSpec",
    "LIFECYCLE_SUGGESTED_WORKFLOWS",
    "ProductLifecyclePhase",
    "ScopeType",
    "SupervisedDatasourceItem",
    "SupervisedRunItem",
    "WorkspaceGovernanceItem",
]
