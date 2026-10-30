"""Orchestration domain errors (`AD-19`, `AD-20`, `Story 3.2a`, `Story 3.2e`)."""

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
            "Discipline d'intention amont obligatoire",
            "Aucune étape d'implémentation cible n'est autorisée sans étape amont de déclaration "
            "d'intention validée (ou politique explicite de rétro-documentation).",
        ),
        "en": LocalizedErrorCopy(
            "Upstream intention discipline required",
            "Target implementation steps require an upstream validated intention step (or explicit "
            "reverse-documentation policy).",
        ),
    },
    "ERR_UNKNOWN_WORKFLOW_POLICY": {
        "fr": LocalizedErrorCopy(
            "Politique de workflow inconnue",
            "Le manifeste référence une politique dans 'policies' non enregistrée dans le "
            "registre de plugins 'orcia.workflow_policies'.",
        ),
        "en": LocalizedErrorCopy(
            "Unknown workflow policy",
            "The manifest references a policy in 'policies' that is not registered in the "
            "'orcia.workflow_policies' plugin registry.",
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
    "ERR_STEP_ALREADY_CLAIMED_BY_PEER": {
        "fr": LocalizedErrorCopy(
            "Étape déjà prise en charge par un pair",
            "Cette étape ou notification d'équipe est déjà verrouillée par un autre coéquipier "
            "(verrou de présence actif < 15 min).",
        ),
        "en": LocalizedErrorCopy(
            "Step already claimed by peer",
            "This step or team notification is already locked by another teammate "
            "(active presence lock < 15 min).",
        ),
    },
    "ERR_STEP_CLAIM_NOT_HELD": {
        "fr": LocalizedErrorCopy(
            "Verrou de prise en charge d'étape non détenu",
            "Vous devez détenir le verrou de présence sur cette étape avant d'effectuer "
            "cette modification.",
        ),
        "en": LocalizedErrorCopy(
            "Step presence claim lock not held",
            "You must hold the presence claim lock on this step before performing this mutation.",
        ),
    },
    "ERR_STALE_FENCING_TOKEN": {
        "fr": LocalizedErrorCopy(
            "Jeton de fencing de bail périmé",
            "L'écriture sur la ressource partagée a été rejetée car son jeton de fencing "
            "est inférieur au bail actif.",
        ),
        "en": LocalizedErrorCopy(
            "Stale resource lease fencing token",
            "The write to the shared resource was rejected because its fencing token is older "
            "than the active lease.",
        ),
    },
    "ERR_RESOURCE_LEASE_HELD_BY_OTHER_RUN": {
        "fr": LocalizedErrorCopy(
            "Ressource partagée déjà verrouillée par un autre Run",
            "La ressource cible est actuellement détenue par un bail actif "
            "d'un autre Workflow Run.",
        ),
        "en": LocalizedErrorCopy(
            "Shared resource already leased by another Run",
            "The target resource is currently held by an active lease of another Workflow Run.",
        ),
    },
    "ERR_CYCLIC_RESOURCE_WAIT_DETECTED": {
        "fr": LocalizedErrorCopy(
            "Attente cyclique parent-enfant sur ressource partagée détectée",
            "Un sous-workflow enfant tente d'acquérir un bail détenu par son workflow parent "
            "en attente (deadlock hiérarchique SUB_WORKFLOW).",
        ),
        "en": LocalizedErrorCopy(
            "Parent-child cyclic resource wait detected",
            "A child sub-workflow attempted to acquire a lease held by its waiting parent "
            "workflow (SUB_WORKFLOW hierarchical deadlock).",
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


class UnknownWorkflowPolicyError(OrciaDomainError):
    error_code = "ERR_UNKNOWN_WORKFLOW_POLICY"
    http_status, type_slug = 422, "unknown-workflow-policy"


class SubWorkflowMaxDepthExceededError(OrciaDomainError):
    error_code = "ERR_SUB_WORKFLOW_MAX_DEPTH_EXCEEDED"
    http_status, type_slug = 422, "sub-workflow-max-depth-exceeded"


class SubWorkflowCycleDetectedError(OrciaDomainError):
    error_code = "ERR_SUB_WORKFLOW_CYCLE_DETECTED"
    http_status, type_slug = 422, "sub-workflow-cycle-detected"


class StepAlreadyClaimedByPeerError(OrciaDomainError):
    error_code = "ERR_STEP_ALREADY_CLAIMED_BY_PEER"
    http_status, type_slug = 409, "step-already-claimed-by-peer"


class StepClaimNotHeldError(OrciaDomainError):
    error_code = "ERR_STEP_CLAIM_NOT_HELD"
    http_status, type_slug = 403, "step-claim-not-held"


class StaleFencingTokenError(OrciaDomainError):
    error_code = "ERR_STALE_FENCING_TOKEN"
    http_status, type_slug = 409, "stale-fencing-token"


class ResourceLeaseHeldByOtherRunError(OrciaDomainError):
    error_code = "ERR_RESOURCE_LEASE_HELD_BY_OTHER_RUN"
    http_status, type_slug = 409, "resource-lease-held-by-other-run"


class CyclicResourceWaitDetectedError(OrciaDomainError):
    error_code = "ERR_CYCLIC_RESOURCE_WAIT_DETECTED"
    http_status, type_slug = 409, "cyclic-resource-wait-detected"


__all__ = [
    "CriticalWorkflowRequiresHumanGateError",
    "CyclicResourceWaitDetectedError",
    "HumanAnchorRequiredError",
    "IntentionBeforeCodeRequiredError",
    "ObserverModeReadOnlyError",
    "OrciaDomainError",
    "ResourceLeaseHeldByOtherRunError",
    "ResourceNotFoundError",
    "ScopeAccessDeniedError",
    "StaleFencingTokenError",
    "StepAlreadyClaimedByPeerError",
    "StepClaimNotHeldError",
    "SubWorkflowCycleDetectedError",
    "SubWorkflowMaxDepthExceededError",
    "UnknownWorkflowPolicyError",
    "ValidationDomainError",
]
