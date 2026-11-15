"""Permissions & Auth domain errors (`AD-19`, `Story 3.2a`).

Inherits from `orcia_kernel.errors.OrciaDomainError` and registers localized FR/EN copy.
"""

from __future__ import annotations

from orcia_core.permissions._error_catalog import PERMISSIONS_ERROR_CATALOG
from orcia_kernel.errors import (
    ObserverModeReadOnlyError,
    OrciaDomainError,
    ReadSourceDeniedError,
    ResourceNotFoundError,
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


class OrgUnitNotEmptyError(OrciaDomainError):
    error_code, http_status, type_slug = "ERR_ORG_UNIT_NOT_EMPTY", 409, "org-unit-not-empty"


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


__all__ = [
    "AdminLockoutPreventedError",
    "AuthenticationRequiredError",
    "C3WorkspaceRequiredError",
    "CodegraphWorkspaceLeadRequiredError",
    "ConfusedDeputyBlockedError",
    "DuplicateIamPrincipalError",
    "GrantEscalationForbiddenError",
    "InvalidCredentialsError",
    "InvalidIamRoleError",
    "InvalidMfaCodeError",
    "InvalidOrExpiredLoginChallengeError",
    "LocalAuthDisabledByPolicyError",
    "ObserverModeReadOnlyError",
    "OrciaDomainError",
    "OrgUnitDuplicateSlugError",
    "OrgUnitHierarchyCycleError",
    "OrgUnitInvalidParentKindError",
    "OrgUnitNotEmptyError",
    "OrgUnitStorageSchemaError",
    "OrgUnitUnknownUserError",
    "PERMISSIONS_ERROR_CATALOG",
    "PasswordUnchangedError",
    "PermissionBrokerDeniedError",
    "PreconditionRequiredError",
    "ReadSourceDeniedError",
    "ResourceNotFoundError",
    "RevokedTokenError",
    "ScopeAccessDeniedError",
    "SecretConfigReadDeniedError",
    "SettingsVersionConflictError",
    "SmtpConnectorRequiredForEmailOtpError",
    "SsoAuthDisabledByPolicyError",
    "SsoConfigurationIncompleteError",
    "UnsafeConnectorEndpointUrlError",
    "ValidationDomainError",
    "WeakPasswordPolicyError",
    "WebhookSignatureInvalidError",
]
