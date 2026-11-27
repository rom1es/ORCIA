"""System bootstrap seeder specifications, ModelRouterService & SystemBootstrapWorkflowService."""

from __future__ import annotations

import importlib
import json
from typing import TYPE_CHECKING, Any, cast

from orcia_core.bootstrap._lazy_exports import ALL_EXPORTS, SYMBOL_TO_MODULE

if TYPE_CHECKING:
    from orcia_core.bootstrap._internal.litellm_adapter import LiteLLMAdapter as LiteLLMAdapter
    from orcia_core.bootstrap._internal.setup_snapshot_sanitizer import (
        strip_snapshot_credentials as strip_snapshot_credentials,
    )
    from orcia_core.bootstrap._internal.smtp_otp_delivery import (
        DispatchedEmailOtpMessage as DispatchedEmailOtpMessage,
    )
    from orcia_core.bootstrap._internal.smtp_otp_delivery import (
        InMemoryOtpEmailSink as InMemoryOtpEmailSink,
    )
    from orcia_core.bootstrap._internal.smtp_otp_delivery import (
        OtpEmailSinkProtocol as OtpEmailSinkProtocol,
    )
    from orcia_core.bootstrap._internal.smtp_otp_delivery import (
        send_login_email_otp as send_login_email_otp,
    )
    from orcia_core.bootstrap._internal.sql_accostage_counts import (
        AccostagePg18Counts as AccostagePg18Counts,
    )
    from orcia_core.bootstrap._internal.sql_accostage_counts import (
        get_accostage_pg18_counts as get_accostage_pg18_counts,
    )
    from orcia_core.bootstrap._internal.sql_auth_policy import (
        ensure_platform_auth_policy_schema as ensure_platform_auth_policy_schema,
    )
    from orcia_core.bootstrap._internal.sql_auth_policy import (
        load_decrypted_oidc_client_secret as load_decrypted_oidc_client_secret,
    )
    from orcia_core.bootstrap._internal.sql_auth_policy import (
        load_platform_auth_policy_from_postgres18 as load_platform_auth_policy_from_postgres18,
    )
    from orcia_core.bootstrap._internal.sql_auth_policy import (
        update_platform_auth_policy_on_postgres18 as update_platform_auth_policy_on_postgres18,
    )
    from orcia_core.bootstrap._internal.sql_autonomy_contracts import (
        SqlAutonomyContractRepository as SqlAutonomyContractRepository,
    )
    from orcia_core.bootstrap._internal.sql_autonomy_contracts import (
        persist_autonomous_run_outcome_on_postgres18 as persist_autonomous_run_outcome_on_postgres18,  # noqa: E501
    )
    from orcia_core.bootstrap._internal.sql_datasource_freshness import (
        get_datasource_webhook_context_from_postgres18 as get_datasource_webhook_context_from_postgres18,  # noqa: E501
    )
    from orcia_core.bootstrap._internal.sql_datasource_freshness import (
        record_webhook_delivery_and_outbox as record_webhook_delivery_and_outbox,
    )
    from orcia_core.bootstrap._internal.sql_datasource_freshness import (
        update_datasource_freshness_state as update_datasource_freshness_state,
    )
    from orcia_core.bootstrap._internal.sql_declarative_packs import (
        DeclarativePackBundleRecord as DeclarativePackBundleRecord,
    )
    from orcia_core.bootstrap._internal.sql_declarative_packs import (
        get_declarative_pack_bundle_sql as get_declarative_pack_bundle_sql,
    )
    from orcia_core.bootstrap._internal.sql_declarative_packs import (
        list_declarative_pack_bundles_sql as list_declarative_pack_bundles_sql,
    )
    from orcia_core.bootstrap._internal.sql_declarative_packs import (
        upsert_declarative_pack_bundles_sql as upsert_declarative_pack_bundles_sql,
    )
    from orcia_core.bootstrap._internal.sql_enterprise_connectors import (
        UserAccountOrgUnitSummary as UserAccountOrgUnitSummary,
    )
    from orcia_core.bootstrap._internal.sql_enterprise_connectors import (
        UserAccountProfileRecord as UserAccountProfileRecord,
    )
    from orcia_core.bootstrap._internal.sql_enterprise_connectors import (
        create_enterprise_connector_on_postgres18 as create_enterprise_connector_on_postgres18,
    )
    from orcia_core.bootstrap._internal.sql_enterprise_connectors import (
        delete_enterprise_connector_on_postgres18 as delete_enterprise_connector_on_postgres18,
    )
    from orcia_core.bootstrap._internal.sql_enterprise_connectors import (
        get_user_account_profile_from_postgres18 as get_user_account_profile_from_postgres18,
    )
    from orcia_core.bootstrap._internal.sql_enterprise_connectors import (
        list_enterprise_connectors_from_postgres18 as list_enterprise_connectors_from_postgres18,
    )
    from orcia_core.bootstrap._internal.sql_enterprise_connectors import (
        list_user_passthrough_tokens_from_postgres18 as list_user_passthrough_tokens_from_postgres18,  # noqa: E501
    )
    from orcia_core.bootstrap._internal.sql_enterprise_connectors import (
        revoke_user_passthrough_token_on_postgres18 as revoke_user_passthrough_token_on_postgres18,
    )
    from orcia_core.bootstrap._internal.sql_enterprise_connectors import (
        update_enterprise_connector_on_postgres18 as update_enterprise_connector_on_postgres18,
    )
    from orcia_core.bootstrap._internal.sql_enterprise_connectors import (
        upsert_user_passthrough_token_on_postgres18 as upsert_user_passthrough_token_on_postgres18,
    )
    from orcia_core.bootstrap._internal.sql_first_user_guard import (
        create_first_platform_admin_on_postgres18 as create_first_platform_admin_on_postgres18,
    )
    from orcia_core.bootstrap._internal.sql_first_user_guard import (
        get_first_platform_admin_from_postgres18 as get_first_platform_admin_from_postgres18,
    )
    from orcia_core.bootstrap._internal.sql_iam_accounts import (
        create_iam_account_on_postgres18 as create_iam_account_on_postgres18,
    )
    from orcia_core.bootstrap._internal.sql_iam_accounts import (
        delete_iam_account_on_postgres18 as delete_iam_account_on_postgres18,
    )
    from orcia_core.bootstrap._internal.sql_iam_accounts import (
        sync_and_list_iam_accounts_from_postgres18 as sync_and_list_iam_accounts_from_postgres18,
    )
    from orcia_core.bootstrap._internal.sql_iam_accounts import (
        update_iam_account_on_postgres18 as update_iam_account_on_postgres18,
    )
    from orcia_core.bootstrap._internal.sql_iam_grants import (
        create_iam_grants_on_postgres18 as create_iam_grants_on_postgres18,
    )
    from orcia_core.bootstrap._internal.sql_iam_grants import (
        delete_iam_grant_on_postgres18 as delete_iam_grant_on_postgres18,
    )
    from orcia_core.bootstrap._internal.sql_iam_grants import (
        list_iam_grants_from_postgres18 as list_iam_grants_from_postgres18,
    )
    from orcia_core.bootstrap._internal.sql_local_auth import (
        LocalAuthCandidate as LocalAuthCandidate,
    )
    from orcia_core.bootstrap._internal.sql_local_auth import (
        load_auth_candidate_by_id_from_postgres18 as load_auth_candidate_by_id_from_postgres18,
    )
    from orcia_core.bootstrap._internal.sql_local_auth import (
        load_auth_candidate_by_oidc_from_postgres18 as load_auth_candidate_by_oidc_from_postgres18,
    )
    from orcia_core.bootstrap._internal.sql_local_auth import (
        load_local_auth_candidate_from_postgres18 as load_local_auth_candidate_from_postgres18,
    )
    from orcia_core.bootstrap._internal.sql_local_auth import (
        update_user_password_on_postgres18 as update_user_password_on_postgres18,
    )
    from orcia_core.bootstrap._internal.sql_local_auth import (
        upsert_human_user_credentials_on_postgres18 as upsert_human_user_credentials_on_postgres18,
    )
    from orcia_core.bootstrap._internal.sql_login_challenges import (
        activate_user_totp_secret_on_postgres18 as activate_user_totp_secret_on_postgres18,
    )
    from orcia_core.bootstrap._internal.sql_login_challenges import (
        consume_login_challenge_on_postgres18 as consume_login_challenge_on_postgres18,
    )
    from orcia_core.bootstrap._internal.sql_login_challenges import (
        create_login_second_factor_challenge_on_postgres18 as create_login_second_factor_challenge_on_postgres18,  # noqa: E501
    )
    from orcia_core.bootstrap._internal.sql_login_challenges import (
        increment_challenge_attempts_on_postgres18 as increment_challenge_attempts_on_postgres18,
    )
    from orcia_core.bootstrap._internal.sql_login_challenges import (
        load_login_challenge_by_token_from_postgres18 as load_login_challenge_by_token_from_postgres18,  # noqa: E501
    )
    from orcia_core.bootstrap._internal.sql_login_challenges import (
        update_login_challenge_email_otp_on_postgres18 as update_login_challenge_email_otp_on_postgres18,  # noqa: E501
    )
    from orcia_core.bootstrap._internal.sql_org_known_users import (
        load_known_org_users_from_postgres18 as load_known_org_users_from_postgres18,
    )
    from orcia_core.bootstrap._internal.sql_org_known_users import (
        search_known_org_users_from_postgres18 as search_known_org_users_from_postgres18,
    )
    from orcia_core.bootstrap._internal.sql_org_units import (
        create_org_unit_on_postgres18 as create_org_unit_on_postgres18,
    )
    from orcia_core.bootstrap._internal.sql_org_units import (
        delete_org_unit_on_postgres18 as delete_org_unit_on_postgres18,
    )
    from orcia_core.bootstrap._internal.sql_org_units import (
        list_org_units_from_postgres18 as list_org_units_from_postgres18,
    )
    from orcia_core.bootstrap._internal.sql_org_units import (
        update_org_unit_on_postgres18 as update_org_unit_on_postgres18,
    )
    from orcia_core.bootstrap._internal.sql_personal_workspace import (
        build_personal_workspace_name as build_personal_workspace_name,
    )
    from orcia_core.bootstrap._internal.sql_personal_workspace import (
        ensure_personal_workspace_on_postgres18 as ensure_personal_workspace_on_postgres18,
    )
    from orcia_core.bootstrap._internal.sql_platform_setup_store import (
        PlatformSetupSnapshotRecord as PlatformSetupSnapshotRecord,
    )
    from orcia_core.bootstrap._internal.sql_platform_setup_store import (
        load_platform_setup_state_from_postgres18 as load_platform_setup_state_from_postgres18,
    )
    from orcia_core.bootstrap._internal.sql_platform_setup_store import (
        persist_progressive_llm_endpoint_to_postgres18 as persist_progressive_llm_endpoint_to_postgres18,  # noqa: E501
    )
    from orcia_core.bootstrap._internal.sql_platform_setup_store import (
        save_platform_setup_state_to_postgres18 as save_platform_setup_state_to_postgres18,
    )
    from orcia_core.bootstrap._internal.sql_user_preferences import (
        SqlUserPreferencesAndMcpService as SqlUserPreferencesAndMcpService,
    )
    from orcia_core.bootstrap._internal.sql_wizard_sessions import (
        SqlWizardSessionRepository as SqlWizardSessionRepository,
    )
    from orcia_core.bootstrap._internal.sql_workspace_datasources import (
        create_workspace_datasource_on_postgres18 as create_workspace_datasource_on_postgres18,
    )
    from orcia_core.bootstrap._internal.sql_workspace_datasources import (
        delete_workspace_datasource_on_postgres18 as delete_workspace_datasource_on_postgres18,
    )
    from orcia_core.bootstrap._internal.sql_workspace_datasources import (
        get_workspace_datasource_from_postgres18 as get_workspace_datasource_from_postgres18,
    )
    from orcia_core.bootstrap._internal.sql_workspace_datasources import (
        list_workspace_datasources_from_postgres18 as list_workspace_datasources_from_postgres18,
    )
    from orcia_core.bootstrap._internal.sql_workspace_datasources import (
        trigger_workspace_datasource_sync_on_postgres18 as trigger_workspace_datasource_sync_on_postgres18,  # noqa: E501
    )
    from orcia_core.bootstrap._internal.sql_workspace_datasources import (
        update_workspace_datasource_on_postgres18 as update_workspace_datasource_on_postgres18,
    )
    from orcia_core.bootstrap._internal.sql_workspaces import (
        WorkspaceCreationRecord as WorkspaceCreationRecord,
    )
    from orcia_core.bootstrap._internal.sql_workspaces import (
        create_workspace_on_postgres18 as create_workspace_on_postgres18,
    )
    from orcia_core.bootstrap._internal.sql_workspaces import (
        resolve_exact_workspace_slug as resolve_exact_workspace_slug,
    )
    from orcia_core.bootstrap.durable_wizards import (
        WIZARD_STEPS_BY_TYPE as WIZARD_STEPS_BY_TYPE,
    )
    from orcia_core.bootstrap.durable_wizards import (
        DemoWorkspaceProvisionResult as DemoWorkspaceProvisionResult,
    )
    from orcia_core.bootstrap.durable_wizards import (
        DurableOnboardingWizardService as DurableOnboardingWizardService,
    )
    from orcia_core.bootstrap.durable_wizards import (
        WizardSessionRecord as WizardSessionRecord,
    )
    from orcia_core.bootstrap.durable_wizards import (
        WizardSessionRepositoryPort as WizardSessionRepositoryPort,
    )
    from orcia_core.bootstrap.durable_wizards import (
        WizardSessionStatus as WizardSessionStatus,
    )
    from orcia_core.bootstrap.durable_wizards import (
        WizardStepDescriptor as WizardStepDescriptor,
    )
    from orcia_core.bootstrap.durable_wizards import (
        WizardType as WizardType,
    )
    from orcia_core.bootstrap.engine import (
        CANONICAL_UPSTREAM_ONTOLOGY as CANONICAL_UPSTREAM_ONTOLOGY,
    )
    from orcia_core.bootstrap.engine import (
        VALID_ARCHETYPES as VALID_ARCHETYPES,
    )
    from orcia_core.bootstrap.engine import (
        InitExistingProjectInput as InitExistingProjectInput,
    )
    from orcia_core.bootstrap.engine import (
        InitExistingProjectOutcome as InitExistingProjectOutcome,
    )
    from orcia_core.bootstrap.engine import (
        InitSkillInput as InitSkillInput,
    )
    from orcia_core.bootstrap.engine import (
        InitSkillOutcome as InitSkillOutcome,
    )
    from orcia_core.bootstrap.engine import (
        ModelOrthogonalityReport as ModelOrthogonalityReport,
    )
    from orcia_core.bootstrap.engine import (
        ModelRouterService as ModelRouterService,
    )
    from orcia_core.bootstrap.engine import (
        SystemBootstrapWorkflowService as SystemBootstrapWorkflowService,
    )
    from orcia_core.bootstrap.models import (
        BootstrapRunStatus as BootstrapRunStatus,
    )
    from orcia_core.bootstrap.models import (
        BootstrapScopeLevel as BootstrapScopeLevel,
    )
    from orcia_core.bootstrap.models import (
        InitDatasourceInput as InitDatasourceInput,
    )
    from orcia_core.bootstrap.models import (
        InitDatasourceOutcome as InitDatasourceOutcome,
    )
    from orcia_core.bootstrap.models import (
        InitOrganizationInput as InitOrganizationInput,
    )
    from orcia_core.bootstrap.models import (
        InitUserInput as InitUserInput,
    )
    from orcia_core.bootstrap.models import (
        InitUserOutcome as InitUserOutcome,
    )
    from orcia_core.bootstrap.models import (
        InitUserPassthroughSecretInput as InitUserPassthroughSecretInput,
    )
    from orcia_core.bootstrap.models import (
        InitWorkspaceInput as InitWorkspaceInput,
    )
    from orcia_core.bootstrap.models import (
        InitWorkspaceOutcome as InitWorkspaceOutcome,
    )
    from orcia_core.bootstrap.models import (
        LlmModelEndpoint as LlmModelEndpoint,
    )
    from orcia_core.bootstrap.models import (
        MemberInvitationInput as MemberInvitationInput,
    )
    from orcia_core.bootstrap.models import (
        OntologyLayerLevel as OntologyLayerLevel,
    )
    from orcia_core.bootstrap.models import (
        OntologyTermSpec as OntologyTermSpec,
    )
    from orcia_core.bootstrap.models import (
        SystemBootstrapRunRecord as SystemBootstrapRunRecord,
    )
    from orcia_core.bootstrap.models import (
        SystemBootstrapWorkflowSpec as SystemBootstrapWorkflowSpec,
    )
    from orcia_core.bootstrap.models import (
        UserOnboardingState as UserOnboardingState,
    )
    from orcia_core.bootstrap.models import (
        WorkspaceBootstrapInput as WorkspaceBootstrapInput,
    )
    from orcia_core.bootstrap.plugin_registry import (
        PluginRegistryService as PluginRegistryService,
    )
    from orcia_core.bootstrap.plugin_registry import (
        UriSchemePluginDescriptor as UriSchemePluginDescriptor,
    )
    from orcia_core.bootstrap.plugin_registry import (
        build_litellm_gateway_plugin as build_litellm_gateway_plugin,
    )
    from orcia_core.bootstrap.progressive_accostage import (
        ACCOSTAGE_SIX_MILESTONES as ACCOSTAGE_SIX_MILESTONES,
    )
    from orcia_core.bootstrap.progressive_accostage import (
        EXCLUSIVE_USERS_LOCK_SQL as EXCLUSIVE_USERS_LOCK_SQL,
    )
    from orcia_core.bootstrap.progressive_accostage import (
        SINGLE_FAMILY_AMBER_WARNING_FR as SINGLE_FAMILY_AMBER_WARNING_FR,
    )
    from orcia_core.bootstrap.progressive_accostage import (
        AccostageMilestoneSpec as AccostageMilestoneSpec,
    )
    from orcia_core.bootstrap.progressive_accostage import (
        AccostageStatusReport as AccostageStatusReport,
    )
    from orcia_core.bootstrap.progressive_accostage import (
        AccostageVisibleMilestone as AccostageVisibleMilestone,
    )
    from orcia_core.bootstrap.progressive_accostage import (
        FirstPlatformAdminRecord as FirstPlatformAdminRecord,
    )
    from orcia_core.bootstrap.progressive_accostage import (
        LlmProgressiveTierMode as LlmProgressiveTierMode,
    )
    from orcia_core.bootstrap.progressive_accostage import (
        ProgressiveDay0AccostageService as ProgressiveDay0AccostageService,
    )
    from orcia_core.bootstrap.progressive_accostage import (
        is_accostage_milestone_accessible as is_accostage_milestone_accessible,
    )
    from orcia_core.bootstrap.seeder import (
        ASSISTANT_WORKFLOW_URI as ASSISTANT_WORKFLOW_URI,
    )
    from orcia_core.bootstrap.seeder import (
        DEFAULT_HUMAN_PROFILE_ARCHETYPES as DEFAULT_HUMAN_PROFILE_ARCHETYPES,
    )
    from orcia_core.bootstrap.seeder import (
        SYSTEM_BOOTSTRAP_WORKFLOW_URIS as SYSTEM_BOOTSTRAP_WORKFLOW_URIS,
    )
    from orcia_core.bootstrap.seeder import (
        HumanProfileArchetypeSeed as HumanProfileArchetypeSeed,
    )
    from orcia_core.bootstrap.seeder import (
        UpsertSpec as UpsertSpec,
    )
    from orcia_core.bootstrap.seeder import (
        build_postgres_upsert_sql as build_postgres_upsert_sql,
    )
    from orcia_core.catalog.service import FederatedCatalogService as FederatedCatalogService
    from orcia_core.permissions.broker import PermissionBrokerService as PermissionBrokerService
    from orcia_core.permissions.models import PlatformRole as PlatformRole
    from orcia_core.permissions.service import (
        AuthAndOrganizationService as AuthAndOrganizationService,
    )


def build_default_system_bootstrap_service(
    *,
    auth_service: AuthAndOrganizationService,
    catalog_service: FederatedCatalogService,
    permission_broker_service: PermissionBrokerService,
) -> SystemBootstrapWorkflowService:
    """Build the reference Story 1.5 `SystemBootstrapWorkflowService` with seeded workflows."""
    from orcia_core.bootstrap import workflow_bootstrap_seeds as wbs
    from orcia_core.bootstrap.engine import SystemBootstrapWorkflowService as _Service
    from orcia_core.bootstrap.models import (
        BootstrapRunStatus as _RunStatus,
    )
    from orcia_core.bootstrap.models import (
        BootstrapScopeLevel as _ScopeLevel,
    )
    from orcia_core.bootstrap.models import (
        SystemBootstrapRunRecord as _RunRecord,
    )
    from orcia_core.bootstrap.models import (
        SystemBootstrapWorkflowSpec as _WorkflowSpec,
    )
    from orcia_core.bootstrap.models import (
        UserOnboardingState as _OnboardingState,
    )

    workflows = tuple(
        _WorkflowSpec(
            s.id, s.uri, s.title, s.description, s.required_role,
            cast(_ScopeLevel, s.scope_level), s.deterministic_gate_rules, s.sha256,
        )
        for s in wbs.DEFAULT_SYSTEM_BOOTSTRAP_WORKFLOW_SEEDS
    )  # fmt: skip
    runs = tuple(
        _RunRecord(
            r.id, r.run_key, r.workflow_uri, cast(_ScopeLevel, r.scope_level),
            r.target_org_unit_id, r.target_workspace_id, r.triggered_by_user_id,
            cast(_RunStatus, r.status), r.gate_passed,
            cast(dict[str, object], json.loads(r.gate_report_json)),
            cast(dict[str, object], json.loads(r.execution_payload_json)),
        )
        for r in wbs.DEFAULT_SYSTEM_BOOTSTRAP_RUN_SEEDS
    )  # fmt: skip
    states = tuple(
        _OnboardingState(
            st.id, st.user_email, st.user_id, st.invited_by_user_id, st.org_unit_id,
            st.human_profile_archetype, cast("PlatformRole", st.assigned_role),
            tuple(json.loads(st.workspace_ids_json)), st.init_user_completed,
            tuple(json.loads(st.linked_connectors_json)),
        )
        for st in wbs.DEFAULT_USER_ONBOARDING_STATE_SEEDS
    )  # fmt: skip
    return _Service(
        auth_service=auth_service,
        catalog_service=catalog_service,
        permission_broker_service=permission_broker_service,
        workflows=workflows,
        runs=runs,
        onboarding_states=states,
    )


def __getattr__(name: str) -> Any:
    module_path = SYMBOL_TO_MODULE.get(name)
    if module_path is None:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    value = getattr(importlib.import_module(module_path), name)
    globals()[name] = value
    return value


def __dir__() -> list[str]:
    return sorted(set(globals()) | set(ALL_EXPORTS))


__all__ = list(ALL_EXPORTS)
