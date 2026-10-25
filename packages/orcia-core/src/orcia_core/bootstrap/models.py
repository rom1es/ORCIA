"""Pure domain models & ModelRouterService for Day-0 System Bootstrap Workflows (`AD-10`, `FR-28`).

Zero framework imports (`fastapi`, `sqlalchemy`, `dramatiq`, `redis`, `litellm`).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

from orcia_core.bootstrap.seeder import DEFAULT_HUMAN_PROFILE_ARCHETYPES
from orcia_core.catalog.models import CatalogItemEntity, ScalarValue
from orcia_core.domain.exceptions import ModelOrthogonalityViolationError
from orcia_core.permissions.broker_models import PermissionBrokerPolicy
from orcia_core.permissions.models import (
    DatasourceScheme,
    ExecutionIdentityMode,
    PassthroughCredentialRecord,
    PlatformRole,
    WorkspaceDatasourceEntity,
    WorkspaceEntity,
    WorkspaceVisibilityMode,
)

BootstrapScopeLevel = Literal["GLOBAL", "BU", "TEAM", "WORKSPACE"]
BootstrapRunStatus = Literal["COMPLETED", "BLOCKED_BY_GATE", "FAILED"]
OntologyLayerLevel = Literal["1_ENTERPRISE", "2_DOMAIN", "3_TEAM", "3_WORKSPACE"]

VALID_ARCHETYPES: frozenset[str] = frozenset(a.key for a in DEFAULT_HUMAN_PROFILE_ARCHETYPES)
CANONICAL_UPSTREAM_ONTOLOGY: dict[str, str] = {
    "workspace": "Espace solution logicielle multi-sources decouple de l'arbre OrgUnit",
    "run_lock": "Manifeste cryptographique immuable SHA-256 des sources resolues",
    "passthrough": "Execution deleguee sous l'identite de l'utilisateur declencheur",
    "payment_capture": "Capture transactionnelle PCI-DSS idempotente sur le grand livre",
}


@dataclass(frozen=True, slots=True)
class LlmModelEndpoint:
    """Registered LLM model endpoint verified by `ModelRouterService` (`AD-10`, `FR-28`)."""

    id: str
    endpoint_key: str
    provider_slug: str
    model_family: str
    model_name: str
    endpoint_uri: str
    connectivity_verified: bool = True
    is_active: bool = True


@dataclass(frozen=True, slots=True)
class ModelOrthogonalityReport:
    """Deterministic evaluation report of LLM model family orthogonality (`>= 2` families)."""

    verified_endpoints: tuple[LlmModelEndpoint, ...]
    distinct_families: tuple[str, ...]
    is_orthogonal: bool


class ModelRouterService:
    """Deterministic LLM router verifying `>= 2` distinct model families (`AD-10`, `FR-28`)."""

    def __init__(self, endpoints: tuple[LlmModelEndpoint, ...] = ()) -> None:
        self._endpoints: dict[str, LlmModelEndpoint] = {ep.endpoint_key: ep for ep in endpoints}

    def list_endpoints(self) -> list[LlmModelEndpoint]:
        return list(self._endpoints.values())

    def register_endpoint(self, endpoint: LlmModelEndpoint) -> LlmModelEndpoint:
        self._endpoints[endpoint.endpoint_key] = endpoint
        return endpoint

    def evaluate_orthogonality(
        self, endpoints: tuple[LlmModelEndpoint, ...] | None = None
    ) -> ModelOrthogonalityReport:
        source = endpoints if endpoints is not None else tuple(self._endpoints.values())
        verified = tuple(
            ep
            for ep in source
            if ep.is_active and ep.connectivity_verified and ep.model_family.strip()
        )
        families = tuple(sorted({ep.model_family.strip().lower() for ep in verified}))
        return ModelOrthogonalityReport(verified, families, len(families) >= 2)

    def enforce_orthogonality_gate(
        self,
        endpoints: tuple[LlmModelEndpoint, ...] | None = None,
        *,
        instance: str | None = None,
    ) -> ModelOrthogonalityReport:
        report = self.evaluate_orthogonality(endpoints)
        if not report.is_orthogonal:
            raise ModelOrthogonalityViolationError(instance=instance)
        return report

    @staticmethod
    def verify_executor_evaluator_pair(
        executor_family: str, evaluator_family: str, *, instance: str | None = None
    ) -> None:
        ex, ev = executor_family.strip().lower(), evaluator_family.strip().lower()
        if not ex or not ev or ex == ev:
            raise ModelOrthogonalityViolationError(instance=instance)


@dataclass(frozen=True, slots=True)
class SystemBootstrapWorkflowSpec:
    """Pre-embedded governed system workflow specification (`orcia://system/bootstrap/*`)."""

    id: str
    uri: str
    title: str
    description: str
    required_role: str
    scope_level: BootstrapScopeLevel
    deterministic_gate_rules: tuple[str, ...]
    sha256: str


@dataclass(frozen=True, slots=True)
class SystemBootstrapRunRecord:
    """Execution record of a `orcia://system/bootstrap/*` workflow run and its gate report."""

    id: str
    run_key: str
    workflow_uri: str
    scope_level: BootstrapScopeLevel
    target_org_unit_id: str | None
    target_workspace_id: str | None
    triggered_by_user_id: str
    status: BootstrapRunStatus
    gate_passed: bool
    gate_report: dict[str, object]
    execution_payload: dict[str, object]


@dataclass(frozen=True, slots=True)
class UserOnboardingState:
    """Tracks a member's invitation and automatic `init-user` first-login execution (`FR-28`)."""

    id: str
    user_email: str
    user_id: str | None
    invited_by_user_id: str | None
    org_unit_id: str
    human_profile_archetype: str
    assigned_role: PlatformRole
    workspace_ids: tuple[str, ...]
    init_user_completed: bool = False
    linked_connectors: tuple[DatasourceScheme, ...] = ()


@dataclass(frozen=True, slots=True)
class OntologyTermSpec:
    """Ontology concept definition proposed during `init-workspace` (`3_TEAM` / `3_WORKSPACE`)."""

    term_key: str
    definition: str
    level: OntologyLayerLevel = "3_WORKSPACE"


@dataclass(frozen=True, slots=True)
class InitOrganizationInput:
    """Input contract for `orcia://system/bootstrap/init-organization` (`AD-10`, `FR-28`)."""

    organization_name: str
    oidc_enabled: bool
    local_argon2id_enabled: bool
    rbac_role_mappings: dict[str, str]
    llm_endpoints: tuple[LlmModelEndpoint, ...]


@dataclass(frozen=True, slots=True)
class WorkspaceBootstrapInput:
    """Solution Workspace specification inside `orcia://system/bootstrap/init-workspace`."""

    slug: str
    name: str
    visibility_mode: WorkspaceVisibilityMode = "STANDARD"
    notification_channel: str = "#workspace-alerts"
    workspace_override_scalars: dict[str, ScalarValue] = field(default_factory=dict)
    workspace_ontology_terms: tuple[OntologyTermSpec, ...] = ()


@dataclass(frozen=True, slots=True)
class MemberInvitationInput:
    """Team member pre-assignment prepared during `init-workspace` for `init-user`."""

    email: str
    display_name: str
    human_profile_archetype: str
    role: PlatformRole = "CONTRIBUTOR"


@dataclass(frozen=True, slots=True)
class InitWorkspaceInput:
    """Input contract for autonomous team & multi-workspace onboarding (`init-workspace`)."""

    team_slug: str
    team_name: str
    parent_org_unit_id: str
    subteam_slug: str | None = None
    subteam_name: str | None = None
    team_override_scalars: dict[str, ScalarValue] = field(default_factory=dict)
    team_ontology_terms: tuple[OntologyTermSpec, ...] = ()
    workspaces: tuple[WorkspaceBootstrapInput, ...] = ()
    invited_members: tuple[MemberInvitationInput, ...] = ()


@dataclass(frozen=True, slots=True)
class InitDatasourceInput:
    """Input contract for governed multi-source publication (`init-datasource`, `UX-DR3`)."""

    workspace_id: str
    alias: str
    scheme: DatasourceScheme
    uri: str
    role: str
    freshness_ttl_days: int
    permission_broker_markdown: str
    human_anchor_justification: str
    human_anchor_signature: str
    execution_identity: ExecutionIdentityMode = "passthrough"
    cql_filter: str | None = None
    jql_filter: str | None = None
    human_anchor_author_id: str | None = None
    visibility_scope: Literal["SHARED_WORKSPACE", "SHARED_TEAM"] = "SHARED_WORKSPACE"


@dataclass(frozen=True, slots=True)
class InitUserPassthroughSecretInput:
    """Plaintext passthrough token (`git`, `jira`, `confluence`) to encrypt in `AES-256-GCM`."""

    connector_scheme: DatasourceScheme
    target_host: str
    plaintext_secret: str


@dataclass(frozen=True, slots=True)
class InitUserInput:
    """Input contract for first-login `orcia://system/bootstrap/init-user` (`NFR-SEC-4`)."""

    confirmed_human_profile_archetype: str
    passthrough_secrets: tuple[InitUserPassthroughSecretInput, ...]
    user_email: str | None = None


@dataclass(frozen=True, slots=True)
class InitWorkspaceOutcome:
    run: SystemBootstrapRunRecord
    workspaces: tuple[WorkspaceEntity, ...]
    onboarding_states: tuple[UserOnboardingState, ...]


@dataclass(frozen=True, slots=True)
class InitDatasourceOutcome:
    run: SystemBootstrapRunRecord
    datasource: WorkspaceDatasourceEntity
    policy: PermissionBrokerPolicy
    catalog_item: CatalogItemEntity


@dataclass(frozen=True, slots=True)
class InitUserOutcome:
    run: SystemBootstrapRunRecord
    onboarding_state: UserOnboardingState
    credentials: tuple[PassthroughCredentialRecord, ...]
