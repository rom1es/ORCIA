"""Permissions & Auth domain errors (`AD-19`, `Story 3.2a`).

Inherits from `orcia_kernel.errors.OrciaDomainError` and registers localized FR/EN copy.
"""

from __future__ import annotations

from orcia_core.permissions._error_catalog import PERMISSIONS_ERROR_CATALOG
from orcia_kernel.errors import (
    CriticalWorkflowRequiresHumanGateError,
    ObserverModeReadOnlyError,
    OrciaDomainError,
    ReadSourceDeniedError,
    ResourceNotFoundError,
    ResourcePinnedByActiveRunsError,
    ScopeAccessDeniedError,
    ValidationDomainError,
    register_domain_error_catalog,
)

register_domain_error_catalog(PERMISSIONS_ERROR_CATALOG)


class InvalidCredentialsError(OrciaDomainError):
    error_code, http_status, type_slug = (
        "ERR_AUTH_INVALID_CREDENTIALS",
        401,
        "auth-invalid-credentials",
    )


class InvalidMfaCodeError(OrciaDomainError):
    error_code, http_status, type_slug = "ERR_AUTH_MFA_INVALID", 401, "auth-mfa-invalid"


class AuthenticationRequiredError(OrciaDomainError):
    """Raised when no Bearer token is supplied outside `ORCIA_ENV` local / test (BUG-E2E-04)."""

    error_code, http_status, type_slug = "ERR_AUTH_REQUIRED", 401, "auth-required"


class RevokedTokenError(OrciaDomainError):
    error_code, http_status, type_slug = "ERR_AUTH_TOKEN_REVOKED", 401, "auth-token-revoked"


class PermissionBrokerDeniedError(OrciaDomainError):
    error_code, http_status, type_slug = (
        "ERR_PERMISSION_BROKER_INTERCEPTED",
        403,
        "permission-broker-intercepted",
    )


class ConfusedDeputyBlockedError(OrciaDomainError):
    error_code, http_status, type_slug = (
        "ERR_CONFUSED_DEPUTY_BLOCKED",
        403,
        "confused-deputy-blocked",
    )


class GrantEscalationForbiddenError(OrciaDomainError):
    error_code, http_status, type_slug = (
        "ERR_GRANT_ESCALATION_FORBIDDEN",
        403,
        "grant-escalation-forbidden",
    )


class AdminLockoutPreventedError(OrciaDomainError):
    error_code, http_status, type_slug = (
        "ERR_ADMIN_LOCKOUT_PREVENTED",
        422,
        "admin-lockout-prevented",
    )


class SecretConfigReadDeniedError(OrciaDomainError):
    error_code, http_status, type_slug = (
        "ERR_SECRET_CONFIG_READ_DENIED",
        403,
        "secret-config-read-denied",
    )


class PreconditionRequiredError(OrciaDomainError):
    error_code, http_status, type_slug = "ERR_PRECONDITION_REQUIRED", 428, "precondition-required"


class SettingsVersionConflictError(OrciaDomainError):
    error_code, http_status, type_slug = (
        "ERR_SETTINGS_VERSION_CONFLICT",
        412,
        "settings-version-conflict",
    )


class C3WorkspaceRequiredError(OrciaDomainError):
    error_code, http_status, type_slug = "ERR_C3_WORKSPACE_REQUIRED", 403, "c3-workspace-required"


class PrivateWorkspaceVisibilityLockedError(OrciaDomainError):
    error_code, http_status, type_slug = (
        "ERR_PRIVATE_WORKSPACE_VISIBILITY_LOCKED",
        403,
        "private-workspace-visibility-locked",
    )


class OrgUnitInvalidParentKindError(OrciaDomainError):
    error_code, http_status, type_slug = (
        "ERR_ORG_UNIT_INVALID_PARENT_KIND",
        422,
        "org-unit-invalid-parent-kind",
    )


class OrgUnitHierarchyCycleError(OrciaDomainError):
    error_code, http_status, type_slug = (
        "ERR_ORG_UNIT_HIERARCHY_CYCLE",
        422,
        "org-unit-hierarchy-cycle",
    )


class OrgUnitDuplicateSlugError(OrciaDomainError):
    error_code, http_status, type_slug = (
        "ERR_ORG_UNIT_DUPLICATE_SLUG",
        409,
        "org-unit-duplicate-slug",
    )


class OrgUnitNotFoundError(ResourceNotFoundError):
    error_code, http_status, type_slug = (
        "ERR_ORG_UNIT_NOT_FOUND",
        404,
        "org-unit-not-found",
    )


class OrgUnitNotEmptyError(OrciaDomainError):
    error_code, http_status, type_slug = "ERR_ORG_UNIT_NOT_EMPTY", 409, "org-unit-not-empty"


class OrgUnitBuMembersForbiddenError(OrciaDomainError):
    error_code, http_status, type_slug = (
        "ERR_ORG_UNIT_BU_MEMBERS_FORBIDDEN",
        422,
        "org-unit-bu-members-forbidden",
    )


class OrgUnitStorageSchemaError(OrciaDomainError):
    error_code, http_status, type_slug = (
        "ERR_ORG_STORAGE_SCHEMA_OUTDATED",
        503,
        "org-storage-schema-outdated",
    )


class OrgUnitUnknownUserError(OrciaDomainError):
    error_code, http_status, type_slug = (
        "ERR_ORG_UNIT_UNKNOWN_USER",
        422,
        "org-unit-unknown-user",
    )


class OrgUnitScopeForbiddenError(OrciaDomainError):
    error_code, http_status, type_slug = (
        "ERR_ORG_UNIT_SCOPE_FORBIDDEN",
        403,
        "org-unit-scope-forbidden",
    )


class OrgUnitRootDeleteForbiddenError(OrciaDomainError):
    error_code, http_status, type_slug = (
        "ERR_ORG_UNIT_ROOT_DELETE_FORBIDDEN",
        403,
        "org-unit-root-delete-forbidden",
    )


class OrgUnitLastLeadRemovalForbiddenError(OrciaDomainError):
    error_code, http_status, type_slug = (
        "ERR_ORG_UNIT_LAST_LEAD_REMOVAL_FORBIDDEN",
        422,
        "org-unit-last-lead-removal-forbidden",
    )


class PrivilegeEscalationForbiddenError(OrciaDomainError):
    error_code, http_status, type_slug = (
        "ERR_PRIVILEGE_ESCALATION_FORBIDDEN",
        403,
        "privilege-escalation-forbidden",
    )


class InvalidIamRoleError(OrciaDomainError):
    error_code, http_status, type_slug = "ERR_IAM_INVALID_ROLE", 422, "iam-invalid-role"


class DuplicateIamPrincipalError(OrciaDomainError):
    error_code, http_status, type_slug = (
        "ERR_IAM_DUPLICATE_PRINCIPAL",
        409,
        "iam-duplicate-principal",
    )


class UnsafeConnectorEndpointUrlError(OrciaDomainError):
    error_code, http_status, type_slug = (
        "ERR_UNSAFE_CONNECTOR_ENDPOINT_URL",
        422,
        "unsafe-connector-endpoint-url",
    )


class WeakPasswordPolicyError(OrciaDomainError):
    error_code, http_status, type_slug = (
        "ERR_AUTH_WEAK_PASSWORD",
        422,
        "auth-weak-password",
    )


class PasswordUnchangedError(OrciaDomainError):
    error_code, http_status, type_slug = (
        "ERR_AUTH_PASSWORD_UNCHANGED",
        422,
        "auth-password-unchanged",
    )


class InvalidCurrentPasswordError(OrciaDomainError):
    error_code = "ERR_AUTH_CURRENT_PASSWORD_INVALID"
    http_status, type_slug = 422, "auth-current-password-invalid"


class LocalPasswordChangeForbiddenForSsoError(OrciaDomainError):
    error_code = "ERR_AUTH_SSO_PASSWORD_MANAGED_EXTERNALLY"
    http_status, type_slug = 422, "auth-sso-password-managed-externally"


class CodegraphWorkspaceLeadRequiredError(OrciaDomainError):
    error_code = "ERR_CODEGRAPH_WORKSPACE_LEAD_REQUIRED"
    http_status, type_slug = 403, "codegraph-workspace-lead-required"


class WebhookSignatureInvalidError(OrciaDomainError):
    error_code = "ERR_WEBHOOK_SIGNATURE_INVALID"
    http_status, type_slug = 401, "webhook-signature-invalid"


class LocalAuthDisabledByPolicyError(OrciaDomainError):
    error_code = "ERR_LOCAL_AUTH_DISABLED"
    http_status, type_slug = 403, "local-auth-disabled"


class SsoAuthDisabledByPolicyError(OrciaDomainError):
    error_code = "ERR_SSO_AUTH_DISABLED"
    http_status, type_slug = 403, "sso-auth-disabled"


class SsoConfigurationIncompleteError(OrciaDomainError):
    error_code = "ERR_SSO_CONFIG_INCOMPLETE"
    http_status, type_slug = 422, "sso-config-incomplete"


class SmtpConnectorRequiredForEmailOtpError(OrciaDomainError):
    error_code = "ERR_AUTH_SMTP_CONNECTOR_REQUIRED"
    http_status, type_slug = 422, "auth-smtp-connector-required"


class InvalidOrExpiredLoginChallengeError(OrciaDomainError):
    error_code = "ERR_AUTH_CHALLENGE_INVALID"
    http_status, type_slug = 401, "auth-challenge-invalid"


class ConnectorCircuitOpenError(OrciaDomainError):
    error_code = "ERR_CONNECTOR_CIRCUIT_OPEN"
    http_status, type_slug = 503, "connector-circuit-open"


class AutonomyContractNotFoundError(ResourceNotFoundError):
    error_code = "ERR_AUTONOMY_CONTRACT_NOT_FOUND"
    http_status, type_slug = 404, "autonomy-contract-not-found"


class ServicePrincipalInvalidForContractError(OrciaDomainError):
    error_code = "ERR_CONTRACT_SERVICE_PRINCIPAL_INVALID"
    http_status, type_slug = 422, "contract-service-principal-invalid"


class ContractPrivilegeEscalationError(OrciaDomainError):
    error_code = "ERR_CONTRACT_PRIVILEGE_ESCALATION"
    http_status, type_slug = 403, "contract-privilege-escalation"


class AutonomyContractSignForbiddenError(OrciaDomainError):
    error_code = "ERR_CONTRACT_SIGNATURE_FORBIDDEN"
    http_status, type_slug = 403, "contract-signature-forbidden"


class AutonomyContractRequiredForTriggerError(OrciaDomainError):
    error_code = "ERR_AUTONOMY_CONTRACT_REQUIRED"
    http_status, type_slug = 422, "autonomy-contract-required"


class TriggerCircuitOpenError(OrciaDomainError):
    error_code = "ERR_TRIGGER_CIRCUIT_OPEN"
    http_status, type_slug = 503, "trigger-circuit-open"


class TriggerNotFoundError(ResourceNotFoundError):
    error_code = "ERR_TRIGGER_NOT_FOUND"
    http_status, type_slug = 404, "trigger-not-found"


class TriggerDuplicateKeyError(OrciaDomainError):
    error_code = "ERR_TRIGGER_DUPLICATE_KEY"
    http_status, type_slug = 409, "trigger-duplicate-key"


__all__ = [
    "AdminLockoutPreventedError",
    "AuthenticationRequiredError",
    "AutonomyContractNotFoundError",
    "AutonomyContractRequiredForTriggerError",
    "AutonomyContractSignForbiddenError",
    "C3WorkspaceRequiredError",
    "CodegraphWorkspaceLeadRequiredError",
    "ConfusedDeputyBlockedError",
    "ConnectorCircuitOpenError",
    "ContractPrivilegeEscalationError",
    "CriticalWorkflowRequiresHumanGateError",
    "DuplicateIamPrincipalError",
    "GrantEscalationForbiddenError",
    "InvalidCredentialsError",
    "InvalidCurrentPasswordError",
    "InvalidIamRoleError",
    "InvalidMfaCodeError",
    "InvalidOrExpiredLoginChallengeError",
    "LocalAuthDisabledByPolicyError",
    "LocalPasswordChangeForbiddenForSsoError",
    "ObserverModeReadOnlyError",
    "OrciaDomainError",
    "OrgUnitBuMembersForbiddenError",
    "OrgUnitDuplicateSlugError",
    "OrgUnitHierarchyCycleError",
    "OrgUnitInvalidParentKindError",
    "OrgUnitLastLeadRemovalForbiddenError",
    "OrgUnitNotEmptyError",
    "OrgUnitNotFoundError",
    "OrgUnitRootDeleteForbiddenError",
    "OrgUnitScopeForbiddenError",
    "OrgUnitStorageSchemaError",
    "OrgUnitUnknownUserError",
    "PERMISSIONS_ERROR_CATALOG",
    "PasswordUnchangedError",
    "PermissionBrokerDeniedError",
    "PreconditionRequiredError",
    "PrivateWorkspaceVisibilityLockedError",
    "PrivilegeEscalationForbiddenError",
    "ReadSourceDeniedError",
    "ResourceNotFoundError",
    "ResourcePinnedByActiveRunsError",
    "RevokedTokenError",
    "ScopeAccessDeniedError",
    "SecretConfigReadDeniedError",
    "ServicePrincipalInvalidForContractError",
    "SettingsVersionConflictError",
    "SmtpConnectorRequiredForEmailOtpError",
    "SsoAuthDisabledByPolicyError",
    "SsoConfigurationIncompleteError",
    "TriggerCircuitOpenError",
    "TriggerDuplicateKeyError",
    "TriggerNotFoundError",
    "UnsafeConnectorEndpointUrlError",
    "ValidationDomainError",
    "WeakPasswordPolicyError",
    "WebhookSignatureInvalidError",
]
