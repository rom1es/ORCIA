"""Gates domain errors (`AD-9`, `AD-10`, `AD-12`, `AD-19`, `Story 3.2a`, `Story 4.1`)."""

from __future__ import annotations

from orcia_kernel.errors import (
    FunctionalConnectorError,
    LocalizedErrorCopy,
    ModelOrthogonalityViolationError,
    OrciaDomainError,
    PolicyDeniedError,
    UpstreamTimeoutError,
    ValidationDomainError,
    register_domain_error_catalog,
)

register_domain_error_catalog(
    {
        "ERR_DETERMINISTIC_GATE_FAILED": {
            "fr": LocalizedErrorCopy(
                "Échec de la Gate Déterministe (Sandbox Palier 1)",
                "L'artefact ou le Skill a échoué aux contrôles déterministes "
                "(schéma, axiomes d'ontologie ou Pattern Drift).",
            ),
            "en": LocalizedErrorCopy(
                "Deterministic Gate failed (Tier 1 Sandbox)",
                "The artifact or Skill failed deterministic checks "
                "(schema, ontology axioms, or Pattern Drift).",
            ),
        },
        "ERR_PATTERN_DRIFT_DETECTED": {
            "fr": LocalizedErrorCopy(
                "Dérive architecturale détectée (Pattern Drift)",
                "Une bibliothèque ou un motif interdit par ARCHITECTURE-SPINE.md a été détecté.",
            ),
            "en": LocalizedErrorCopy(
                "Architectural Pattern Drift detected",
                "A library or pattern forbidden by ARCHITECTURE-SPINE.md was detected.",
            ),
        },
    }
)


class DeterministicGateFailedError(FunctionalConnectorError):
    """Non-retryable functional error when a Deterministic Gate fails validation (`Story 4.1`)."""

    error_code = "ERR_DETERMINISTIC_GATE_FAILED"
    http_status, type_slug = 422, "deterministic-gate-failed"


class PatternDriftDetectedError(FunctionalConnectorError):
    """Non-retryable error when static analysis detects Pattern Drift against Spine (`FR-17`)."""

    error_code = "ERR_PATTERN_DRIFT_DETECTED"
    http_status, type_slug = 422, "pattern-drift-detected"


__all__ = [
    "DeterministicGateFailedError",
    "FunctionalConnectorError",
    "ModelOrthogonalityViolationError",
    "OrciaDomainError",
    "PatternDriftDetectedError",
    "PolicyDeniedError",
    "UpstreamTimeoutError",
    "ValidationDomainError",
]
