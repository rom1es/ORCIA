"""Gates domain errors (`AD-9`, `AD-10`, `AD-11`, `AD-12`, `AD-19`, `Stories 4.1..4.3`)."""

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
        "ERR_UNAPPROVED_CHUNKS_REMAINING": {
            "fr": LocalizedErrorCopy(
                "Sections non validées restantes (Validation par Découpage)",
                "Toutes les sections obligatoires doivent être validées (APPROVED ou CO_EDITED) "
                "et le bloc 4 (Hypothèses Retenues) doit être inspecté avant l'approbation finale.",
            ),
            "en": LocalizedErrorCopy(
                "Unapproved sections remaining (Chunked Validation)",
                "All required sections must be approved (APPROVED or CO_EDITED) "
                "and Block 4 (Retained Hypotheses) must be inspected before final approval.",
            ),
        },
        "ERR_RUBBER_STAMPING_GUARD_TRIGGERED": {
            "fr": LocalizedErrorCopy(
                "Garde-fou Anti-Rubber-Stamping déclenché (< 15 s)",
                "Approbation soumise en moins de 15 secondes sur un artefact > 1 000 mots. "
                "Veuillez confirmer explicitement les hypothèses retenues.",
            ),
            "en": LocalizedErrorCopy(
                "Anti-Rubber-Stamping Guard triggered (< 15 s)",
                "Approval submitted in under 15 seconds on an artifact > 1,000 words. "
                "Please explicitly confirm the retained hypotheses.",
            ),
        },
        "ERR_HUMAN_GATE_NOT_FOUND": {
            "fr": LocalizedErrorCopy(
                "Gate Humaine introuvable",
                "L'évaluation de Gate Humaine ou la section demandée est introuvable.",
            ),
            "en": LocalizedErrorCopy(
                "Human Gate not found",
                "The requested Human Gate evaluation or chunk was not found.",
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


class UnapprovedChunksRemainingError(ValidationDomainError):
    """Raised when final approval is requested while required chunks remain pending (`FR-6`)."""

    error_code = "ERR_UNAPPROVED_CHUNKS_REMAINING"
    http_status, type_slug = 422, "unapproved-chunks-remaining"


class RubberStampingGuardTriggeredError(ValidationDomainError):
    """Raised when approval is submitted in < 15s on > 1,000 words without explicit confirmation."""

    error_code = "ERR_RUBBER_STAMPING_GUARD_TRIGGERED"
    http_status, type_slug = 422, "rubber-stamping-guard-triggered"


class HumanGateNotFoundError(OrciaDomainError):
    """Raised when a Human Gate evaluation or chunk cannot be found."""

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
