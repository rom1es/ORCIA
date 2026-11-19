"""System bootstrap seeder specifications, ModelRouterService & SystemBootstrapWorkflowService."""

from __future__ import annotations

import json
from typing import cast

from orcia_core.bootstrap import workflow_bootstrap_seeds as wbs
from orcia_core.bootstrap._internal.litellm_adapter import LiteLLMAdapter
from orcia_core.bootstrap._internal.smtp_otp_delivery import (
    DispatchedEmailOtpMessage,
    InMemoryOtpEmailSink,
    OtpEmailSinkProtocol,
    send_login_email_otp,
)
from orcia_core.bootstrap._internal.sql_auth_policy import (
    ensure_platform_auth_policy_schema,
    load_decrypted_oidc_client_secret,
    load_platform_auth_policy_from_postgres18,
    update_platform_auth_policy_on_postgres18,
)
from orcia_core.bootstrap._internal.sql_autonomy_contracts import (
    SqlAutonomyContractRepository,
    persist_autonomous_run_outcome_on_postgres18,
)
from orcia_core.bootstrap._internal.sql_declarative_packs import (
    DeclarativePackBundleRecord,
    get_declarative_pack_bundle_sql,
    list_declarative_pack_bundles_sql,
    upsert_declarative_pack_bundles_sql,
)
from orcia_core.bootstrap._internal.sql_enterprise_connectors import (
    UserAccountOrgUnitSummary,
    UserAccountProfileRecord,
    create_enterprise_connector_on_postgres18,
    delete_enterprise_connector_on_postgres18,
    get_user_account_profile_from_postgres18,
    list_enterprise_connectors_from_postgres18,
    list_user_passthrough_tokens_from_postgres18,
    revoke_user_passthrough_token_on_postgres18,
    update_enterprise_connector_on_postgres18,
    upsert_user_passthrough_token_on_postgres18,
)
from orcia_core.bootstrap._internal.sql_first_user_guard import (
    create_first_platform_admin_on_postgres18,
    get_first_platform_admin_from_postgres18,
)
from orcia_core.bootstrap._internal.sql_iam_accounts import (
    create_iam_account_on_postgres18,
    delete_iam_account_on_postgres18,
    sync_and_list_iam_accounts_from_postgres18,
    update_iam_account_on_postgres18,
)
from orcia_core.bootstrap._internal.sql_iam_grants import (
    create_iam_grants_on_postgres18,
    delete_iam_grant_on_postgres18,
    list_iam_grants_from_postgres18,
)
from orcia_core.bootstrap._internal.sql_local_auth import (
    LocalAuthCandidate,
    load_auth_candidate_by_id_from_postgres18,
    load_auth_candidate_by_oidc_from_postgres18,
    load_local_auth_candidate_from_postgres18,
    update_user_password_on_postgres18,
    upsert_human_user_credentials_on_postgres18,
)
from orcia_core.bootstrap._internal.sql_login_challenges import (
    activate_user_totp_secret_on_postgres18,
    consume_login_challenge_on_postgres18,
    create_login_second_factor_challenge_on_postgres18,
    increment_challenge_attempts_on_postgres18,
    load_login_challenge_by_token_from_postgres18,
    update_login_challenge_email_otp_on_postgres18,
)
from orcia_core.bootstrap._internal.sql_org_known_users import (
    load_known_org_users_from_postgres18,
    search_known_org_users_from_postgres18,
)
from orcia_core.bootstrap._internal.sql_org_units import (
    create_org_unit_on_postgres18,
    delete_org_unit_on_postgres18,
    list_org_units_from_postgres18,
    update_org_unit_on_postgres18,
)
from orcia_core.bootstrap._internal.sql_platform_setup_store import (
    PlatformSetupSnapshotRecord,
    load_platform_setup_state_from_postgres18,
    persist_progressive_llm_endpoint_to_postgres18,
    save_platform_setup_state_to_postgres18,
)
from orcia_core.bootstrap._internal.sql_wizard_sessions import (
    SqlWizardSessionRepository,
)
from orcia_core.bootstrap._internal.sql_workspace_datasources import (
    create_workspace_datasource_on_postgres18,
    delete_workspace_datasource_on_postgres18,
    get_workspace_datasource_from_postgres18,
    list_workspace_datasources_from_postgres18,
    trigger_workspace_datasource_sync_on_postgres18,
    update_workspace_datasource_on_postgres18,
)
from orcia_core.bootstrap._internal.sql_workspaces import (
    WorkspaceCreationRecord,
    create_workspace_on_postgres18,
    resolve_exact_workspace_slug,
)
from orcia_core.bootstrap.durable_wizards import (
    WIZARD_STEPS_BY_TYPE,
    DemoWorkspaceProvisionResult,
    DurableOnboardingWizardService,
    WizardSessionRecord,
    WizardSessionRepositoryPort,
    WizardSessionStatus,
    WizardStepDescriptor,
    WizardType,
)
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
    build_litellm_gateway_plugin,
)
from orcia_core.bootstrap.progressive_accostage import (
    ACCOSTAGE_SIX_MILESTONES,
    EXCLUSIVE_USERS_LOCK_SQL,
    SINGLE_FAMILY_AMBER_WARNING_FR,
    AccostageMilestoneSpec,
    AccostageStatusReport,
    FirstPlatformAdminRecord,
    LlmProgressiveTierMode,
    ProgressiveDay0AccostageService,
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
    "ACCOSTAGE_SIX_MILESTONES",
    "ASSISTANT_WORKFLOW_URI",
    "CANONICAL_UPSTREAM_ONTOLOGY",
    "DEFAULT_HUMAN_PROFILE_ARCHETYPES",
    "EXCLUSIVE_USERS_LOCK_SQL",
    "SINGLE_FAMILY_AMBER_WARNING_FR",
    "SYSTEM_BOOTSTRAP_WORKFLOW_URIS",
    "VALID_ARCHETYPES",
    "WIZARD_STEPS_BY_TYPE",
    "AccostageMilestoneSpec",
    "AccostageStatusReport",
    "BootstrapRunStatus",
    "BootstrapScopeLevel",
    "DemoWorkspaceProvisionResult",
    "DeclarativePackBundleRecord",
    "DurableOnboardingWizardService",
    "FirstPlatformAdminRecord",
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
    "LiteLLMAdapter",
    "LlmModelEndpoint",
    "LlmProgressiveTierMode",
    "MemberInvitationInput",
    "ModelOrthogonalityReport",
    "ModelRouterService",
    "OntologyLayerLevel",
    "OntologyTermSpec",
    "PlatformSetupSnapshotRecord",
    "PluginRegistryService",
    "ProgressiveDay0AccostageService",
    "SystemBootstrapRunRecord",
    "SystemBootstrapWorkflowService",
    "SystemBootstrapWorkflowSpec",
    "UpsertSpec",
    "UriSchemePluginDescriptor",
    "UserAccountOrgUnitSummary",
    "UserAccountProfileRecord",
    "UserOnboardingState",
    "WizardSessionRecord",
    "WizardSessionRepositoryPort",
    "WizardSessionStatus",
    "WizardStepDescriptor",
    "WizardType",
    "WorkspaceBootstrapInput",
    "WorkspaceCreationRecord",
    "create_workspace_on_postgres18",
    "get_declarative_pack_bundle_sql",
    "list_declarative_pack_bundles_sql",
    "resolve_exact_workspace_slug",
    "SqlAutonomyContractRepository",
    "SqlWizardSessionRepository",
    "upsert_declarative_pack_bundles_sql",
    "persist_autonomous_run_outcome_on_postgres18",
    "build_default_system_bootstrap_service",
    "build_litellm_gateway_plugin",
    "build_postgres_upsert_sql",
    "create_enterprise_connector_on_postgres18",
    "create_first_platform_admin_on_postgres18",
    "create_iam_account_on_postgres18",
    "create_iam_grants_on_postgres18",
    "create_org_unit_on_postgres18",
    "create_workspace_datasource_on_postgres18",
    "delete_enterprise_connector_on_postgres18",
    "delete_iam_account_on_postgres18",
    "delete_iam_grant_on_postgres18",
    "delete_org_unit_on_postgres18",
    "delete_workspace_datasource_on_postgres18",
    "get_first_platform_admin_from_postgres18",
    "get_user_account_profile_from_postgres18",
    "get_workspace_datasource_from_postgres18",
    "list_enterprise_connectors_from_postgres18",
    "list_iam_grants_from_postgres18",
    "list_org_units_from_postgres18",
    "list_user_passthrough_tokens_from_postgres18",
    "list_workspace_datasources_from_postgres18",
    "load_known_org_users_from_postgres18",
    "load_local_auth_candidate_from_postgres18",
    "load_platform_setup_state_from_postgres18",
    "persist_progressive_llm_endpoint_to_postgres18",
    "revoke_user_passthrough_token_on_postgres18",
    "save_platform_setup_state_to_postgres18",
    "search_known_org_users_from_postgres18",
    "sync_and_list_iam_accounts_from_postgres18",
    "trigger_workspace_datasource_sync_on_postgres18",
    "update_enterprise_connector_on_postgres18",
    "update_iam_account_on_postgres18",
    "update_org_unit_on_postgres18",
    "update_user_password_on_postgres18",
    "update_workspace_datasource_on_postgres18",
    "upsert_human_user_credentials_on_postgres18",
    "upsert_user_passthrough_token_on_postgres18",
    "LocalAuthCandidate",
    "DispatchedEmailOtpMessage",
    "InMemoryOtpEmailSink",
    "OtpEmailSinkProtocol",
    "activate_user_totp_secret_on_postgres18",
    "consume_login_challenge_on_postgres18",
    "create_login_second_factor_challenge_on_postgres18",
    "ensure_platform_auth_policy_schema",
    "increment_challenge_attempts_on_postgres18",
    "load_auth_candidate_by_id_from_postgres18",
    "load_auth_candidate_by_oidc_from_postgres18",
    "load_decrypted_oidc_client_secret",
    "load_login_challenge_by_token_from_postgres18",
    "load_platform_auth_policy_from_postgres18",
    "send_login_email_otp",
    "update_login_challenge_email_otp_on_postgres18",
    "update_platform_auth_policy_on_postgres18",
]
