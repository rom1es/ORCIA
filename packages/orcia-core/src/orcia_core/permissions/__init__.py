"""Bounded Context 7: Permissions (5 Dissociated Catalog Permissions, Scope Guard & Broker)."""

from __future__ import annotations

from orcia_core.permissions._default_service import build_default_auth_and_org_service
from orcia_core.permissions.broker import (
    BrokerConnectorScheme,
    BrokerStepState,
    BrokerTicketAction,
    BrokerTicketStatus,
    PermissionBrokerPolicy,
    PermissionBrokerService,
    PermissionBrokerTicket,
    PermissionCheckOutcome,
    build_default_permission_broker_service,
    build_prefilled_jira_request_url,
    extract_connector_scheme,
    parse_permission_kb_markdown,
)
from orcia_core.permissions.crypto import (
    ACCESS_TOKEN_TTL_SECONDS,
    REFRESH_TOKEN_TTL_SECONDS,
    Argon2idPasswordHasher,
    JwtSessionManager,
    PassthroughVaultCipher,
    SessionTokenPair,
    TokenClaims,
    TotpManager,
)
from orcia_core.permissions.enterprise_connectors import (
    EnterpriseConnectorsGovernanceService,
)
from orcia_core.permissions.errors import (
    CodegraphWorkspaceLeadRequiredError,
    OrgUnitStorageSchemaError,
    OrgUnitUnknownUserError,
    PasswordUnchangedError,
    WeakPasswordPolicyError,
    WebhookSignatureInvalidError,
)
from orcia_core.permissions.evaluator import (
    ADMIN_MODULE_ALLOWED_ROLES,
    ROLLUP_SUPERVISOR_ROLES,
    MatrixPermissionEvaluator,
)
from orcia_core.permissions.hierarchical_rbac import (
    ALL_PERMISSION_VERBS,
    DEFAULT_ROLE_PERMISSION_MATRIX,
    HierarchicalRbacService,
    PermissionEffect,
    PermissionVerb,
    ResourceDiscoveryOutcome,
    RoleMatrixDescriptor,
    RolePermissionGrant,
    SubjectType,
    list_native_role_matrix,
)
from orcia_core.permissions.iam_accounts import (
    DEFAULT_DAY0_ADMIN_ROLES,
    VALID_GRANT_RESOURCE_KINDS,
    VALID_IAM_ROLES,
    IamAccountKind,
    IamAccountRecord,
    IamAccountsGovernanceService,
    IamAccountStatus,
    IamAuthSource,
    assert_anti_lockout_on_accounts,
    validate_grant_resource_kind,
    validate_iam_roles,
)
from orcia_core.permissions.models import (
    AccessMode,
    AuthMode,
    CatalogAclEntry,
    CatalogPermission,
    CatalogVisibilityScope,
    DatasourceScheme,
    EffectiveResourcePermissions,
    ExecutionIdentityMode,
    OrgUnitNode,
    OrgUnitType,
    PassthroughCredentialRecord,
    PlatformRole,
    UserIdentity,
    WorkspaceAccessSummary,
    WorkspaceDatasourceEntity,
    WorkspaceEntity,
    WorkspaceMembershipEntity,
    WorkspaceVisibilityMode,
)
from orcia_core.permissions.org_hierarchy import (
    AttachedWorkspaceRef,
    OrgUnitKind,
    OrgUnitSummary,
    assert_org_unit_deletable,
    assert_unique_org_unit_slug,
    build_org_unit_summary,
    generate_new_org_unit_id,
    list_evaluator_org_unit_summaries,
    normalize_member_user_ids,
    normalize_org_unit_slug,
    sort_org_unit_dicts_topologically,
    sort_org_unit_summaries_dfs,
    validate_org_unit_hierarchy,
)
from orcia_core.permissions.org_user_validation import (
    KnownOrgUser,
    resolve_and_validate_org_unit_users,
)
from orcia_core.permissions.platform_settings import (
    REGISTERED_IDEMPOTENT_OUTBOX_CONSUMERS,
    DefaultMemorySecretProvider,
    OutboxReplayOutcome,
    PlatformSettingRecord,
    PlatformSettingsService,
    SecretAction,
    SecretInputSpec,
    SecretStatusView,
    SettingCategory,
    SettingScopeLevel,
    compute_salted_secret_fingerprint,
    compute_secret_masked_hint,
)
from orcia_core.permissions.role_matrix import GrantResourceKind, OfficialIamRole
from orcia_core.permissions.service import (
    DEFAULT_TOTP_SECRET_KARIM,
    AuthAndOrganizationService,
    InMemoryRevocationStore,
    KeyValueRevocationStore,
    RevocationStoreProtocol,
    persona_impersonation_allowed,
)
from orcia_core.permissions.temporary_password import (
    generate_temporary_password,
    validate_password_policy,
)
from orcia_core.permissions.workspace_sources_governance import (
    CodegraphAuthMode,
    CodegraphStatus,
    SourceFreshnessStatus,
    SourceNature,
    SourceSyncMode,
    WorkspaceDatasourceRecord,
    can_manage_workspace_codegraph,
    evaluate_codegraph_governance_health,
    infer_source_nature_from_scheme,
)

DOMAIN_NAME: str = "permissions"

__all__ = [
    "ACCESS_TOKEN_TTL_SECONDS", "ADMIN_MODULE_ALLOWED_ROLES", "ALL_PERMISSION_VERBS",
    "DEFAULT_DAY0_ADMIN_ROLES", "DEFAULT_ROLE_PERMISSION_MATRIX", "DEFAULT_TOTP_SECRET_KARIM",
    "DOMAIN_NAME", "DefaultMemorySecretProvider", "GrantResourceKind", "HierarchicalRbacService",
    "IamAccountKind", "IamAccountRecord", "IamAccountStatus", "IamAccountsGovernanceService",
    "IamAuthSource", "OfficialIamRole", "OutboxReplayOutcome", "PermissionEffect", "PermissionVerb",
    "PlatformSettingRecord", "PlatformSettingsService", "REFRESH_TOKEN_TTL_SECONDS",
    "REGISTERED_IDEMPOTENT_OUTBOX_CONSUMERS", "ROLLUP_SUPERVISOR_ROLES", "ResourceDiscoveryOutcome",
    "RoleMatrixDescriptor", "RolePermissionGrant", "SecretAction", "SecretInputSpec",
    "SecretStatusView", "SettingCategory", "SettingScopeLevel", "SubjectType",
    "VALID_GRANT_RESOURCE_KINDS", "VALID_IAM_ROLES", "AccessMode", "Argon2idPasswordHasher",
    "AttachedWorkspaceRef", "AuthAndOrganizationService", "persona_impersonation_allowed",
    "AuthMode", "BrokerConnectorScheme", "BrokerStepState", "BrokerTicketAction",
    "BrokerTicketStatus", "CatalogAclEntry", "CatalogPermission", "CatalogVisibilityScope",
    "DatasourceScheme", "EffectiveResourcePermissions", "ExecutionIdentityMode",
    "InMemoryRevocationStore", "JwtSessionManager", "KeyValueRevocationStore",
    "MatrixPermissionEvaluator", "OrgUnitKind", "OrgUnitNode", "OrgUnitStorageSchemaError",
    "OrgUnitSummary", "OrgUnitType", "OrgUnitUnknownUserError",
    "PassthroughCredentialRecord", "PassthroughVaultCipher",
    "PasswordUnchangedError", "PermissionBrokerPolicy",
    "PermissionBrokerService", "PermissionBrokerTicket",
    "PermissionCheckOutcome", "PlatformRole", "RevocationStoreProtocol",
    "SessionTokenPair", "TokenClaims", "TotpManager", "UserIdentity", "WorkspaceAccessSummary",
    "WeakPasswordPolicyError", "generate_temporary_password", "validate_password_policy",
    "WorkspaceDatasourceEntity", "WorkspaceEntity", "WorkspaceMembershipEntity",
    "WorkspaceVisibilityMode", "assert_anti_lockout_on_accounts", "assert_org_unit_deletable",
    "assert_unique_org_unit_slug", "build_default_auth_and_org_service",
    "build_default_permission_broker_service", "build_org_unit_summary",
    "build_prefilled_jira_request_url", "compute_salted_secret_fingerprint",
    "compute_secret_masked_hint",
    "extract_connector_scheme", "generate_new_org_unit_id", "list_evaluator_org_unit_summaries",
    "list_native_role_matrix", "normalize_member_user_ids", "normalize_org_unit_slug",
    "parse_permission_kb_markdown", "resolve_and_validate_org_unit_users",
    "KnownOrgUser", "sort_org_unit_dicts_topologically",
    "sort_org_unit_summaries_dfs", "validate_grant_resource_kind", "validate_iam_roles",
    "validate_org_unit_hierarchy",
    "EnterpriseConnectorsGovernanceService",
    "CodegraphWorkspaceLeadRequiredError",
    "WebhookSignatureInvalidError",
    "CodegraphAuthMode",
    "CodegraphStatus",
    "SourceFreshnessStatus",
    "SourceNature",
    "SourceSyncMode",
    "WorkspaceDatasourceRecord",
    "can_manage_workspace_codegraph",
    "evaluate_codegraph_governance_health",
    "infer_source_nature_from_scheme",
]  # fmt: skip
