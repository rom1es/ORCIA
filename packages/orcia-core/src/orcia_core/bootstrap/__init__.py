"""System bootstrap seeder specifications, ModelRouterService & SystemBootstrapWorkflowService."""

from __future__ import annotations

import json
from typing import cast

from orcia_core.bootstrap import workflow_bootstrap_seeds as wbs
from orcia_core.bootstrap.engine import (
    CANONICAL_UPSTREAM_ONTOLOGY,
    VALID_ARCHETYPES,
    InitExistingProjectInput,
    InitExistingProjectOutcome,
    InitSkillInput,
    InitSkillOutcome,
    ModelOrthogonalityReport,
    ModelRouterService,
    SystemBootstrapWorkflowService,
)
from orcia_core.bootstrap.models import (
    BootstrapRunStatus,
    BootstrapScopeLevel,
    InitDatasourceInput,
    InitDatasourceOutcome,
    InitOrganizationInput,
    InitUserInput,
    InitUserOutcome,
    InitUserPassthroughSecretInput,
    InitWorkspaceInput,
    InitWorkspaceOutcome,
    LlmModelEndpoint,
    MemberInvitationInput,
    OntologyLayerLevel,
    OntologyTermSpec,
    SystemBootstrapRunRecord,
    SystemBootstrapWorkflowSpec,
    UserOnboardingState,
    WorkspaceBootstrapInput,
)
from orcia_core.bootstrap.plugin_registry import (
    PluginRegistryService,
    UriSchemePluginDescriptor,
)
from orcia_core.bootstrap.seeder import (
    ASSISTANT_WORKFLOW_URI,
    DEFAULT_HUMAN_PROFILE_ARCHETYPES,
    SYSTEM_BOOTSTRAP_WORKFLOW_URIS,
    HumanProfileArchetypeSeed,
    UpsertSpec,
    build_postgres_upsert_sql,
)
from orcia_core.catalog.service import FederatedCatalogService
from orcia_core.permissions.broker import PermissionBrokerService
from orcia_core.permissions.models import PlatformRole
from orcia_core.permissions.service import AuthAndOrganizationService


def build_default_system_bootstrap_service(
    *,
    auth_service: AuthAndOrganizationService,
    catalog_service: FederatedCatalogService,
    permission_broker_service: PermissionBrokerService,
) -> SystemBootstrapWorkflowService:
    """Build the reference Story 1.5 `SystemBootstrapWorkflowService` with seeded workflows."""
    workflows = tuple(
        SystemBootstrapWorkflowSpec(
            s.id, s.uri, s.title, s.description, s.required_role,
            cast(BootstrapScopeLevel, s.scope_level), s.deterministic_gate_rules, s.sha256,
        )
        for s in wbs.DEFAULT_SYSTEM_BOOTSTRAP_WORKFLOW_SEEDS
    )  # fmt: skip
    runs = tuple(
        SystemBootstrapRunRecord(
            r.id, r.run_key, r.workflow_uri, cast(BootstrapScopeLevel, r.scope_level),
            r.target_org_unit_id, r.target_workspace_id, r.triggered_by_user_id,
            cast(BootstrapRunStatus, r.status), r.gate_passed,
            cast(dict[str, object], json.loads(r.gate_report_json)),
            cast(dict[str, object], json.loads(r.execution_payload_json)),
        )
        for r in wbs.DEFAULT_SYSTEM_BOOTSTRAP_RUN_SEEDS
    )  # fmt: skip
    states = tuple(
        UserOnboardingState(
            st.id, st.user_email, st.user_id, st.invited_by_user_id, st.org_unit_id,
            st.human_profile_archetype, cast(PlatformRole, st.assigned_role),
            tuple(json.loads(st.workspace_ids_json)), st.init_user_completed,
            tuple(json.loads(st.linked_connectors_json)),
        )
        for st in wbs.DEFAULT_USER_ONBOARDING_STATE_SEEDS
    )  # fmt: skip
    return SystemBootstrapWorkflowService(
        auth_service=auth_service,
        catalog_service=catalog_service,
        permission_broker_service=permission_broker_service,
        workflows=workflows,
        runs=runs,
        onboarding_states=states,
    )


__all__ = [
    "ASSISTANT_WORKFLOW_URI",
    "CANONICAL_UPSTREAM_ONTOLOGY",
    "DEFAULT_HUMAN_PROFILE_ARCHETYPES",
    "SYSTEM_BOOTSTRAP_WORKFLOW_URIS",
    "VALID_ARCHETYPES",
    "BootstrapRunStatus",
    "BootstrapScopeLevel",
    "HumanProfileArchetypeSeed",
    "InitDatasourceInput",
    "InitDatasourceOutcome",
    "InitExistingProjectInput",
    "InitExistingProjectOutcome",
    "InitOrganizationInput",
    "InitSkillInput",
    "InitSkillOutcome",
    "InitUserInput",
    "InitUserOutcome",
    "InitUserPassthroughSecretInput",
    "InitWorkspaceInput",
    "InitWorkspaceOutcome",
    "LlmModelEndpoint",
    "MemberInvitationInput",
    "ModelOrthogonalityReport",
    "ModelRouterService",
    "OntologyLayerLevel",
    "OntologyTermSpec",
    "PluginRegistryService",
    "SystemBootstrapRunRecord",
    "SystemBootstrapWorkflowService",
    "SystemBootstrapWorkflowSpec",
    "UpsertSpec",
    "UriSchemePluginDescriptor",
    "UserOnboardingState",
    "WorkspaceBootstrapInput",
    "build_default_system_bootstrap_service",
    "build_postgres_upsert_sql",
]
