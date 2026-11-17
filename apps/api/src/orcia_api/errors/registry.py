"""Centralized RFC 9457 Problem Details Error Registry for `apps/api` (`AD-12`, `AD-19`).

Maps every `OrciaDomainError` subclass across all bounded contexts (`permissions`, `catalog`,
`bootstrap`, `ontology`, `rag`, `orchestration`, `blackboard`, `gates`, `audit_finops`) to its
canonical HTTP status code, RFC 9457 `type` URI, and localized `ProblemDetails` envelope.
"""

from __future__ import annotations

from dataclasses import dataclass

from orcia_core.agents.errors import (
    ReflexiveInvalidStateError,
    ReflexiveSessionExpiredError,
)
from orcia_core.audit_finops.errors import AuditLedgerImmutableViolationError
from orcia_core.blackboard.errors import BlackboardAppendOnlyViolationError
from orcia_core.bootstrap.errors import ModelOrthogonalityViolationError
from orcia_core.catalog.errors import ReadSourceDeniedError
from orcia_core.observability.errors import (
    LogSinkQueryFailedError,
    UnsafeLogSinkUrlError,
    UnsupportedLogSinkBackendError,
)
from orcia_core.ontology.errors import OntologyConflictError
from orcia_core.orchestration.ai_models_errors import (
    LastTierModelInUseError,
    ModelConnectionAuthFailedError,
    ModelConnectionNetworkError,
    ModelConnectionNotFoundError,
    ModelConnectionRateLimitedError,
    ModelConnectionTimeoutError,
    ModelConnectionUpstreamError,
    ModelDiscoveryAuthFailedError,
    ModelDiscoveryEndpointNotFoundError,
    ModelDiscoveryNetworkError,
    UnsafeLlmEndpointUrlError,
)
from orcia_core.orchestration.errors import (
    CriticalWorkflowRequiresHumanGateError,
    HumanAnchorRequiredError,
    IntentionBeforeCodeRequiredError,
    SubWorkflowCycleDetectedError,
    SubWorkflowMaxDepthExceededError,
    UnknownWorkflowPolicyError,
)
from orcia_core.permissions.errors import (
    AdminLockoutPreventedError,
    AutonomyContractNotFoundError,
    AutonomyContractSignForbiddenError,
    CodegraphWorkspaceLeadRequiredError,
    ConfusedDeputyBlockedError,
    ContractPrivilegeEscalationError,
    DuplicateIamPrincipalError,
    GrantEscalationForbiddenError,
    InvalidCredentialsError,
    InvalidCurrentPasswordError,
    InvalidIamRoleError,
    InvalidMfaCodeError,
    InvalidOrExpiredLoginChallengeError,
    LocalAuthDisabledByPolicyError,
    LocalPasswordChangeForbiddenForSsoError,
    ObserverModeReadOnlyError,
    OrgUnitBuMembersForbiddenError,
    OrgUnitDuplicateSlugError,
    OrgUnitHierarchyCycleError,
    OrgUnitInvalidParentKindError,
    OrgUnitNotEmptyError,
    OrgUnitNotFoundError,
    OrgUnitStorageSchemaError,
    OrgUnitUnknownUserError,
    PasswordUnchangedError,
    PermissionBrokerDeniedError,
    RevokedTokenError,
    ScopeAccessDeniedError,
    SecretConfigReadDeniedError,
    ServicePrincipalInvalidForContractError,
    SmtpConnectorRequiredForEmailOtpError,
    SsoAuthDisabledByPolicyError,
    SsoConfigurationIncompleteError,
    UnsafeConnectorEndpointUrlError,
    WeakPasswordPolicyError,
    WebhookSignatureInvalidError,
)
from orcia_core.rag.errors import (
    DdlOnlyTransactionalDataError,
    EmbeddingDimensionMismatchError,
    EmbeddingGenerationFailedError,
    EmbeddingProviderUnsupportedError,
    NoActiveEmbeddingModelError,
    RagReindexInProgressError,
)
from orcia_kernel.errors import (
    ERROR_CATALOG,
    OrciaDomainError,
    PolicyDeniedError,
    ResourceNotFoundError,
    SupportedLocale,
    ValidationDomainError,
    get_localized_error_text,
    resolve_locale,
)


@dataclass(frozen=True, slots=True)
class ErrorHttpMapping:
    """HTTP status and RFC 9457 problem type mapping for a domain error class."""

    error_code: str
    http_status: int
    type_uri: str


DOMAIN_ERROR_CLASSES: tuple[type[OrciaDomainError], ...] = (
    OrciaDomainError,
    ObserverModeReadOnlyError,
    HumanAnchorRequiredError,
    ReadSourceDeniedError,
    ModelOrthogonalityViolationError,
    OntologyConflictError,
    DdlOnlyTransactionalDataError,
    SubWorkflowMaxDepthExceededError,
    SubWorkflowCycleDetectedError,
    CriticalWorkflowRequiresHumanGateError,
    IntentionBeforeCodeRequiredError,
    UnknownWorkflowPolicyError,
    PermissionBrokerDeniedError,
    PolicyDeniedError,
    ConfusedDeputyBlockedError,
    AdminLockoutPreventedError,
    GrantEscalationForbiddenError,
    SecretConfigReadDeniedError,
    InvalidIamRoleError,
    DuplicateIamPrincipalError,
    CodegraphWorkspaceLeadRequiredError,
    UnsafeConnectorEndpointUrlError,
    OrgUnitBuMembersForbiddenError,
    OrgUnitDuplicateSlugError,
    OrgUnitHierarchyCycleError,
    OrgUnitInvalidParentKindError,
    OrgUnitNotEmptyError,
    OrgUnitNotFoundError,
    OrgUnitStorageSchemaError,
    OrgUnitUnknownUserError,
    ResourceNotFoundError,
    ValidationDomainError,
    InvalidCredentialsError,
    InvalidCurrentPasswordError,
    LocalPasswordChangeForbiddenForSsoError,
    InvalidMfaCodeError,
    RevokedTokenError,
    ScopeAccessDeniedError,
    WeakPasswordPolicyError,
    PasswordUnchangedError,
    BlackboardAppendOnlyViolationError,
    AuditLedgerImmutableViolationError,
    UnsafeLlmEndpointUrlError,
    LastTierModelInUseError,
    ModelDiscoveryAuthFailedError,
    ModelDiscoveryEndpointNotFoundError,
    ModelDiscoveryNetworkError,
    ModelConnectionAuthFailedError,
    ModelConnectionNotFoundError,
    ModelConnectionRateLimitedError,
    ModelConnectionTimeoutError,
    ModelConnectionNetworkError,
    ModelConnectionUpstreamError,
    WebhookSignatureInvalidError,
    LocalAuthDisabledByPolicyError,
    SsoAuthDisabledByPolicyError,
    SsoConfigurationIncompleteError,
    SmtpConnectorRequiredForEmailOtpError,
    InvalidOrExpiredLoginChallengeError,
    EmbeddingDimensionMismatchError,
    EmbeddingGenerationFailedError,
    EmbeddingProviderUnsupportedError,
    NoActiveEmbeddingModelError,
    RagReindexInProgressError,
    UnsafeLogSinkUrlError,
    UnsupportedLogSinkBackendError,
    LogSinkQueryFailedError,
    AutonomyContractNotFoundError,
    AutonomyContractSignForbiddenError,
    ContractPrivilegeEscalationError,
    ServicePrincipalInvalidForContractError,
    ReflexiveInvalidStateError,
    ReflexiveSessionExpiredError,
)

ERROR_CLASS_REGISTRY: dict[type[OrciaDomainError], ErrorHttpMapping] = {
    cls: ErrorHttpMapping(
        error_code=cls.error_code,
        http_status=cls.http_status,
        type_uri=f"https://orcia.io/problems/{cls.type_slug}",
    )
    for cls in DOMAIN_ERROR_CLASSES
}

ERROR_CODE_REGISTRY: dict[str, ErrorHttpMapping] = {
    mapping.error_code: mapping for mapping in ERROR_CLASS_REGISTRY.values()
}


def resolve_domain_error_mapping(exc: OrciaDomainError) -> ErrorHttpMapping:
    """Resolve the registered `ErrorHttpMapping` for a `OrciaDomainError` instance."""
    registered = ERROR_CLASS_REGISTRY.get(type(exc))
    if registered is not None:
        return registered
    by_code = ERROR_CODE_REGISTRY.get(exc.error_code)
    if by_code is not None:
        return by_code
    return ErrorHttpMapping(
        error_code=exc.error_code,
        http_status=exc.http_status,
        type_uri=exc.type_uri,
    )


__all__ = [
    "AuditLedgerImmutableViolationError",
    "BlackboardAppendOnlyViolationError",
    "ConfusedDeputyBlockedError",
    "CriticalWorkflowRequiresHumanGateError",
    "DOMAIN_ERROR_CLASSES",
    "DdlOnlyTransactionalDataError",
    "EmbeddingDimensionMismatchError",
    "EmbeddingGenerationFailedError",
    "EmbeddingProviderUnsupportedError",
    "NoActiveEmbeddingModelError",
    "ERROR_CATALOG",
    "ERROR_CLASS_REGISTRY",
    "ERROR_CODE_REGISTRY",
    "ErrorHttpMapping",
    "HumanAnchorRequiredError",
    "IntentionBeforeCodeRequiredError",
    "InvalidCredentialsError",
    "InvalidCurrentPasswordError",
    "InvalidMfaCodeError",
    "LocalPasswordChangeForbiddenForSsoError",
    "ModelOrthogonalityViolationError",
    "ObserverModeReadOnlyError",
    "OntologyConflictError",
    "OrciaDomainError",
    "OrgUnitBuMembersForbiddenError",
    "OrgUnitDuplicateSlugError",
    "OrgUnitHierarchyCycleError",
    "OrgUnitInvalidParentKindError",
    "OrgUnitNotEmptyError",
    "OrgUnitNotFoundError",
    "OrgUnitStorageSchemaError",
    "PasswordUnchangedError",
    "PermissionBrokerDeniedError",
    "PolicyDeniedError",
    "ReadSourceDeniedError",
    "RagReindexInProgressError",
    "ReflexiveInvalidStateError",
    "ReflexiveSessionExpiredError",
    "ResourceNotFoundError",
    "RevokedTokenError",
    "ScopeAccessDeniedError",
    "SubWorkflowCycleDetectedError",
    "SubWorkflowMaxDepthExceededError",
    "SupportedLocale",
    "UnknownWorkflowPolicyError",
    "ValidationDomainError",
    "WeakPasswordPolicyError",
    "WebhookSignatureInvalidError",
    "InvalidOrExpiredLoginChallengeError",
    "LocalAuthDisabledByPolicyError",
    "SmtpConnectorRequiredForEmailOtpError",
    "SsoAuthDisabledByPolicyError",
    "SsoConfigurationIncompleteError",
    "get_localized_error_text",
    "resolve_domain_error_mapping",
    "resolve_locale",
]
