"""Kernel base exception `OrciaDomainError` and localized RFC 9457 error registry (`AD-19`).

Pure kernel module — zero framework or business domain dependencies. Each domain in
`packages/orcia-core` defines its own `<domaine>/errors.py` inheriting from `OrciaDomainError`
and registers its localized FR/EN copy via `register_domain_error_catalog()`.
"""

from __future__ import annotations

from collections.abc import Mapping

from orcia_core.kernel._error_catalog import (
    ERROR_CATALOG,
    LocalizedErrorCopy,
    get_localized_error_text,
    register_domain_error_catalog,
    resolve_locale,
)
from orcia_core.kernel.enums import DEFAULT_LOCALE, SupportedLocale


class OrciaDomainError(Exception):
    """Base class for all ORCIA domain errors mapped to RFC 9457 Problem Details."""

    error_code: str = "ERR_INTERNAL_SERVER_ERROR"
    http_status: int = 500
    type_slug: str = "internal-server-error"

    def __init__(
        self,
        *,
        detail_override: str | None = None,
        detail_code: str | None = None,
        detail_params: Mapping[str, object] | None = None,
        instance: str | None = None,
        permission_broker_hint: str | None = None,
    ) -> None:
        self.detail_override = detail_override
        self.detail_code = detail_code
        self.detail_params = dict(detail_params) if detail_params is not None else None
        default_copy = get_localized_error_text(
            self.error_code,
            DEFAULT_LOCALE,
            detail_override,
            detail_code=detail_code,
            detail_params=self.detail_params,
        )
        super().__init__(default_copy.detail)
        self.instance = instance
        self.permission_broker_hint = permission_broker_hint

    @property
    def type_uri(self) -> str:
        return f"https://orcia.io/problems/{self.type_slug}"

    def localize(self, locale: SupportedLocale = DEFAULT_LOCALE) -> LocalizedErrorCopy:
        return get_localized_error_text(
            self.error_code,
            locale,
            self.detail_override,
            detail_code=self.detail_code,
            detail_params=self.detail_params,
        )


class ObserverModeReadOnlyError(OrciaDomainError):
    error_code = "ERR_OBSERVER_MODE_READ_ONLY"
    http_status, type_slug = 403, "observer-mode-read-only"


class HumanAnchorRequiredError(OrciaDomainError):
    error_code, http_status, type_slug = "ERR_HUMAN_ANCHOR_REQUIRED", 422, "human-anchor-required"


class ReadSourceDeniedError(OrciaDomainError):
    error_code, http_status, type_slug = "ERR_READ_SOURCE_DENIED", 403, "read-source-denied"


class ModelOrthogonalityViolationError(OrciaDomainError):
    error_code = "ERR_MODEL_ORTHOGONALITY_VIOLATION"
    http_status, type_slug = 422, "model-orthogonality-violation"


class ResourceNotFoundError(OrciaDomainError):
    error_code, http_status, type_slug = "ERR_RESOURCE_NOT_FOUND", 404, "resource-not-found"


class ValidationDomainError(OrciaDomainError):
    error_code, http_status, type_slug = "ERR_VALIDATION_FAILED", 422, "validation-failed"


class ScopeAccessDeniedError(OrciaDomainError):
    error_code, http_status, type_slug = "ERR_SCOPE_ACCESS_DENIED", 403, "scope-access-denied"


class CriticalWorkflowRequiresHumanGateError(OrciaDomainError):
    error_code = "ERR_CRITICAL_WORKFLOW_REQUIRES_HUMAN_GATE"
    http_status, type_slug = 422, "critical-workflow-requires-human-gate"


class TransientInfraError(OrciaDomainError):
    """Retryable transient infrastructure error with optional `retry_after_s` (`AC-F3`)."""

    error_code = "ERR_TRANSIENT_INFRA_ERROR"
    http_status, type_slug = 503, "transient-infra-error"

    def __init__(
        self,
        *,
        retry_after_s: float = 0.0,
        detail_override: str | None = None,
        detail_code: str | None = None,
        detail_params: Mapping[str, object] | None = None,
        instance: str | None = None,
        permission_broker_hint: str | None = None,
    ) -> None:
        super().__init__(
            detail_override=detail_override,
            detail_code=detail_code,
            detail_params=detail_params,
            instance=instance,
            permission_broker_hint=permission_broker_hint,
        )
        self.retry_after_s = max(0.0, float(retry_after_s))


class RateLimitedError(TransientInfraError):
    """Retryable HTTP 429 rate-limit error carrying `retry_after_s` (`AC-F3`, `AC-F4`)."""

    error_code = "ERR_RATE_LIMITED"
    http_status, type_slug = 429, "rate-limited"


class UpstreamTimeoutError(TransientInfraError):
    """Retryable upstream timeout error (`AC-F4`)."""

    error_code = "ERR_UPSTREAM_TIMEOUT"
    http_status, type_slug = 504, "upstream-timeout"


class TransientConnectorError(TransientInfraError):
    """Retryable external connector error eligible for `ConnectorInvoker` retry (`Story 7.2`)."""

    error_code = "ERR_TRANSIENT_CONNECTOR_ERROR"
    http_status, type_slug = 503, "transient-connector-error"


class FunctionalConnectorError(OrciaDomainError):
    """Non-retryable functional connector error escalating to human arbitration (`AC-F3`)."""

    error_code = "ERR_FUNCTIONAL_CONNECTOR_ERROR"
    http_status, type_slug = 422, "functional-connector-error"


class PolicyDeniedError(OrciaDomainError):
    """Non-retryable policy/governance denial error (`AC-F4`)."""

    error_code = "ERR_POLICY_DENIED"
    http_status, type_slug = 403, "policy-denied"


class PermanentInfraError(OrciaDomainError):
    """Non-retryable permanent infrastructure error or open circuit breaker (`AC-F3`, `AC-F4`)."""

    error_code = "ERR_PERMANENT_INFRA_ERROR"
    http_status, type_slug = 502, "permanent-infra-error"


__all__ = [
    "CriticalWorkflowRequiresHumanGateError",
    "DEFAULT_LOCALE",
    "ERROR_CATALOG",
    "FunctionalConnectorError",
    "HumanAnchorRequiredError",
    "LocalizedErrorCopy",
    "ModelOrthogonalityViolationError",
    "ObserverModeReadOnlyError",
    "OrciaDomainError",
    "PermanentInfraError",
    "PolicyDeniedError",
    "RateLimitedError",
    "ReadSourceDeniedError",
    "ResourceNotFoundError",
    "ScopeAccessDeniedError",
    "SupportedLocale",
    "TransientConnectorError",
    "TransientInfraError",
    "UpstreamTimeoutError",
    "ValidationDomainError",
    "get_localized_error_text",
    "register_domain_error_catalog",
    "resolve_locale",
]
