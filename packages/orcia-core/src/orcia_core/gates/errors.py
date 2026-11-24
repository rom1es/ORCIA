"""Gates domain errors (`AD-9`, `AD-10`, `AD-11`, `AD-12`, `AD-19`, `Stories 4.1..4.3`)."""

from __future__ import annotations

from orcia_core.gates._error_catalog import GATES_ERROR_CATALOG
from orcia_kernel.errors import (
    FunctionalConnectorError,
    ModelOrthogonalityViolationError,
    OrciaDomainError,
    PolicyDeniedError,
    UpstreamTimeoutError,
    ValidationDomainError,
    register_domain_error_catalog,
)

register_domain_error_catalog(GATES_ERROR_CATALOG)


class DeterministicGateFailedError(FunctionalConnectorError):
    """Non-retryable functional error when a Deterministic Gate fails validation (`Story 4.1`)."""

    error_code = "ERR_DETERMINISTIC_GATE_FAILED"
    http_status, type_slug = 422, "deterministic-gate-failed"


class PatternDriftDetectedError(FunctionalConnectorError):
    """Non-retryable error when static analysis detects Pattern Drift against Spine (`FR-17`)."""

    error_code = "ERR_PATTERN_DRIFT_DETECTED"
    http_status, type_slug = 422, "pattern-drift-detected"


class UnapprovedChunksRemainingError(ValidationDomainError):
    """Raised when final approval is requested while required chunks remain pending (`FR-6`)."""

    error_code = "ERR_UNAPPROVED_CHUNKS_REMAINING"
    http_status, type_slug = 422, "unapproved-chunks-remaining"


class RubberStampingGuardTriggeredError(ValidationDomainError):
    """Raised when approval is submitted in < 15s on > 1,000 words without explicit confirmation."""

    error_code = "ERR_RUBBER_STAMPING_GUARD_TRIGGERED"
    http_status, type_slug = 422, "rubber-stamping-guard-triggered"


class HumanGateNotFoundError(OrciaDomainError):
    """Raised when a Human Gate evaluation or chunk cannot be located."""

    error_code = "ERR_HUMAN_GATE_NOT_FOUND"
    http_status, type_slug = 404, "human-gate-not-found"


__all__ = [
    "DeterministicGateFailedError",
    "FunctionalConnectorError",
    "HumanGateNotFoundError",
    "ModelOrthogonalityViolationError",
    "OrciaDomainError",
    "PatternDriftDetectedError",
    "PolicyDeniedError",
    "RubberStampingGuardTriggeredError",
    "UnapprovedChunksRemainingError",
    "UpstreamTimeoutError",
    "ValidationDomainError",
]
