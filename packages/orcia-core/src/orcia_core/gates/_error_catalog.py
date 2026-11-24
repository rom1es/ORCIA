"""Gates localized RFC 9457 error catalog (`AD-9`, `AD-11`, `Story 27.7`)."""

from __future__ import annotations

from orcia_kernel.enums import SupportedLocale
from orcia_kernel.errors import LocalizedErrorCopy

GATES_ERROR_CATALOG: dict[str, dict[SupportedLocale, LocalizedErrorCopy]] = {
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
    "ERR_SANDBOX_TIMEOUT_DETAIL": {
        "fr": LocalizedErrorCopy(
            "Délai d'attente amont dépassé",
            "Dépassement du délai matériel de la Sandbox ({duration_ms} ms) : {stderr_summary}",
        ),
        "en": LocalizedErrorCopy(
            "Upstream service timeout",
            "Sandbox hardware timeout exceeded ({duration_ms} ms): {stderr_summary}",
        ),
    },
    "ERR_SANDBOX_ISOLATION_DETAIL": {
        "fr": LocalizedErrorCopy(
            "Action refusée par la politique de gouvernance",
            "Violation d'isolation de la Sandbox Palier 1 (code {exit_code}) : {stderr_summary}",
        ),
        "en": LocalizedErrorCopy(
            "Action denied by governance policy",
            "Tier 1 Sandbox isolation violation (code {exit_code}): {stderr_summary}",
        ),
    },
    "ERR_SANDBOX_VALIDATION_DETAIL": {
        "fr": LocalizedErrorCopy(
            "Échec de la Gate Déterministe (Sandbox Palier 1)",
            "Échec de validation dans la Sandbox Palier 1 (code {exit_code}) : {stderr_summary}",
        ),
        "en": LocalizedErrorCopy(
            "Deterministic Gate failed (Tier 1 Sandbox)",
            "Tier 1 Sandbox validation failed (code {exit_code}): {stderr_summary}",
        ),
    },
}

__all__ = ["GATES_ERROR_CATALOG"]
