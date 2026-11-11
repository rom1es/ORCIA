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
from orcia_core.ontology.errors import OntologyConflictError
from orcia_core.orchestration.errors import (
    CriticalWorkflowRequiresHumanGateError,
    HumanAnchorRequiredError,
    IntentionBeforeCodeRequiredError,
    SubWorkflowCycleDetectedError,
    SubWorkflowMaxDepthExceededError,
    UnknownWorkflowPolicyError,
)
from orcia_core.permissions.errors import (
    ConfusedDeputyBlockedError,
    InvalidCredentialsError,
    InvalidMfaCodeError,
    ObserverModeReadOnlyError,
    PermissionBrokerDeniedError,
    RevokedTokenError,
    ScopeAccessDeniedError,
)
from orcia_core.rag.errors import DdlOnlyTransactionalDataError
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
    ResourceNotFoundError,
    ValidationDomainError,
    InvalidCredentialsError,
    InvalidMfaCodeError,
    RevokedTokenError,
    ScopeAccessDeniedError,
    BlackboardAppendOnlyViolationError,
    AuditLedgerImmutableViolationError,
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
    "ERROR_CATALOG",
    "ERROR_CLASS_REGISTRY",
    "ERROR_CODE_REGISTRY",
    "ErrorHttpMapping",
    "HumanAnchorRequiredError",
    "IntentionBeforeCodeRequiredError",
    "InvalidCredentialsError",
    "InvalidMfaCodeError",
    "ModelOrthogonalityViolationError",
    "ObserverModeReadOnlyError",
    "OntologyConflictError",
    "OrciaDomainError",
    "PermissionBrokerDeniedError",
    "PolicyDeniedError",
    "ReadSourceDeniedError",
    "ResourceNotFoundError",
    "RevokedTokenError",
    "ScopeAccessDeniedError",
    "SubWorkflowCycleDetectedError",
    "SubWorkflowMaxDepthExceededError",
    "SupportedLocale",
    "UnknownWorkflowPolicyError",
    "ValidationDomainError",
    "get_localized_error_text",
    "resolve_domain_error_mapping",
    "resolve_locale",
]
