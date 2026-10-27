"""Orchestration domain errors (`AD-19`, `Story 3.2a`)."""

from __future__ import annotations

from orcia_kernel.enums import SupportedLocale
from orcia_kernel.errors import (
    HumanAnchorRequiredError,
    LocalizedErrorCopy,
    ObserverModeReadOnlyError,
    OrciaDomainError,
    ResourceNotFoundError,
    ScopeAccessDeniedError,
    ValidationDomainError,
    register_domain_error_catalog,
)

ORCHESTRATION_ERROR_CATALOG: dict[str, dict[SupportedLocale, LocalizedErrorCopy]] = {
    "ERR_CRITICAL_WORKFLOW_REQUIRES_HUMAN_GATE": {
        "fr": LocalizedErrorCopy(
            "Workflow critique incompatible avec l'autonomie totale",
            "Tout workflow classé HIGH_CRITICAL exige au moins une Gate Humaine et ne peut pas "
            "être exécuté en régime AUTONOMOUS_CONTRACT.",
        ),
        "en": LocalizedErrorCopy(
            "Critical workflow requires human gate",
            "Any workflow classified as HIGH_CRITICAL requires at least one Human Gate and "
            "cannot run under AUTONOMOUS_CONTRACT regime.",
        ),
    },
    "ERR_INTENTION_BEFORE_CODE_REQUIRED": {
        "fr": LocalizedErrorCopy(
            "Discipline Intention -> Code obligatoire",
            "Aucune étape d'écriture de code n'est autorisée sans étape amont de déclaration "
            "d'intention validée (ou mode: brownfield_bootstrap pour la rétro-documentation).",
        ),
        "en": LocalizedErrorCopy(
            "Intention -> Code discipline required",
            "Code modification steps require an upstream validated intention step (or explicit "
            "mode: brownfield_bootstrap for reverse documentation).",
        ),
    },
    "ERR_SUB_WORKFLOW_MAX_DEPTH_EXCEEDED": {
        "fr": LocalizedErrorCopy(
            "Profondeur maximale de sous-workflow dépassée (<= 3)",
            "L'imbrication de sous-workflows (SUB_WORKFLOW) est strictement bornée à une "
            "profondeur maximale de 3 niveaux.",
        ),
        "en": LocalizedErrorCopy(
            "Sub-workflow maximum nesting depth exceeded (<= 3)",
            "Sub-workflow nesting (SUB_WORKFLOW) is strictly bounded to a maximum depth of 3.",
        ),
    },
    "ERR_SUB_WORKFLOW_CYCLE_DETECTED": {
        "fr": LocalizedErrorCopy(
            "Cycle d'appels détecté dans le graphe de workflows",
            "Un cycle direct ou indirect a été détecté dans les transitions d'étapes ou "
            "les appels de sous-workflows (SUB_WORKFLOW).",
        ),
        "en": LocalizedErrorCopy(
            "Cycle detected in workflow call graph",
            "A direct or indirect cycle was detected in step transitions or SUB_WORKFLOW calls.",
        ),
    },
}

register_domain_error_catalog(ORCHESTRATION_ERROR_CATALOG)


class CriticalWorkflowRequiresHumanGateError(OrciaDomainError):
    error_code = "ERR_CRITICAL_WORKFLOW_REQUIRES_HUMAN_GATE"
    http_status, type_slug = 422, "critical-workflow-requires-human-gate"


class IntentionBeforeCodeRequiredError(OrciaDomainError):
    error_code = "ERR_INTENTION_BEFORE_CODE_REQUIRED"
    http_status, type_slug = 422, "intention-before-code-required"


class SubWorkflowMaxDepthExceededError(OrciaDomainError):
    error_code = "ERR_SUB_WORKFLOW_MAX_DEPTH_EXCEEDED"
    http_status, type_slug = 422, "sub-workflow-max-depth-exceeded"


class SubWorkflowCycleDetectedError(OrciaDomainError):
    error_code = "ERR_SUB_WORKFLOW_CYCLE_DETECTED"
    http_status, type_slug = 422, "sub-workflow-cycle-detected"


__all__ = [
    "CriticalWorkflowRequiresHumanGateError",
    "HumanAnchorRequiredError",
    "IntentionBeforeCodeRequiredError",
    "ObserverModeReadOnlyError",
    "OrciaDomainError",
    "ResourceNotFoundError",
    "ScopeAccessDeniedError",
    "SubWorkflowCycleDetectedError",
    "SubWorkflowMaxDepthExceededError",
    "ValidationDomainError",
]
