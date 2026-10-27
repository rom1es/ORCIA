"""Domain exceptions and localized RFC 9457 error catalog (FR default, EN supported).

Pure domain module — zero framework dependencies.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

SupportedLocale = Literal["fr", "en"]
DEFAULT_LOCALE: SupportedLocale = "fr"


@dataclass(frozen=True, slots=True)
class LocalizedErrorCopy:
    """Localized title and detail template for an invariant machine error code."""

    title: str
    detail: str


ERROR_CATALOG: dict[str, dict[SupportedLocale, LocalizedErrorCopy]] = {
    "ERR_OBSERVER_MODE_READ_ONLY": {
        "fr": LocalizedErrorCopy(
            "Mode observateur en lecture seule",
            "Cette action de modification est interdite en mode READ_ONLY_OBSERVER.",
        ),
        "en": LocalizedErrorCopy(
            "Read-only observer mode",
            "This mutation action is forbidden while in READ_ONLY_OBSERVER mode.",
        ),
    },
    "ERR_HUMAN_ANCHOR_REQUIRED": {
        "fr": LocalizedErrorCopy(
            "Ancrage humain obligatoire requis",
            "La section marquée human_authored_required exige une rédaction et une "
            "signature humaine explicites.",
        ),
        "en": LocalizedErrorCopy(
            "Mandatory human anchor required",
            "A section marked human_authored_required requires explicit human authoring "
            "and signature.",
        ),
    },
    "ERR_READ_SOURCE_DENIED": {
        "fr": LocalizedErrorCopy(
            "Accès au code source masqué refusé",
            "La permission READ_SOURCE est requise pour inspecter le contenu interne "
            "de cette ressource.",
        ),
        "en": LocalizedErrorCopy(
            "Read source access denied",
            "READ_SOURCE permission is required to inspect the internal source of this item.",
        ),
    },
    "ERR_MODEL_ORTHOGONALITY_VIOLATION": {
        "fr": LocalizedErrorCopy(
            "Violation d'orthogonalité des modèles",
            "La famille du modèle évaluateur doit être distincte de celle de l'exécuteur.",
        ),
        "en": LocalizedErrorCopy(
            "Model orthogonality violation",
            "The evaluator model family must differ from the executor model family.",
        ),
    },
    "ERR_RESOURCE_NOT_FOUND": {
        "fr": LocalizedErrorCopy(
            "Ressource introuvable",
            "La ressource ou la route demandée n'existe pas sur la plateforme ORCIA.",
        ),
        "en": LocalizedErrorCopy(
            "Resource not found",
            "The requested resource or route does not exist on the ORCIA platform.",
        ),
    },
    "ERR_VALIDATION_FAILED": {
        "fr": LocalizedErrorCopy(
            "Erreur de validation de la requête",
            "Les paramètres fournis ne respectent pas le contrat attendu.",
        ),
        "en": LocalizedErrorCopy(
            "Request validation failed",
            "The supplied parameters do not satisfy the expected schema contract.",
        ),
    },
    "ERR_INTERNAL_SERVER_ERROR": {
        "fr": LocalizedErrorCopy(
            "Erreur interne de la plateforme",
            "Une erreur inattendue est survenue lors du traitement de la requête.",
        ),
        "en": LocalizedErrorCopy(
            "Internal platform error",
            "An unexpected error occurred while processing the request.",
        ),
    },
    "ERR_AUTH_INVALID_CREDENTIALS": {
        "fr": LocalizedErrorCopy(
            "Identifiants d'authentification invalides",
            "L'adresse e-mail, le mot de passe ou le jeton OIDC fourni est invalide.",
        ),
        "en": LocalizedErrorCopy(
            "Invalid authentication credentials",
            "The supplied email, password, or OIDC token is invalid.",
        ),
    },
    "ERR_AUTH_MFA_INVALID": {
        "fr": LocalizedErrorCopy(
            "Code MFA TOTP invalide ou manquant",
            "Le code d'authentification multifacteur TOTP est requis ou incorrect.",
        ),
        "en": LocalizedErrorCopy(
            "Invalid or missing TOTP MFA code",
            "A valid TOTP multi-factor authentication code is required.",
        ),
    },
    "ERR_AUTH_TOKEN_REVOKED": {
        "fr": LocalizedErrorCopy(
            "Session expirée ou révoquée",
            "Le jeton de session ou de rafraîchissement a expiré ou a été révoqué.",
        ),
        "en": LocalizedErrorCopy(
            "Session expired or revoked",
            "The session or refresh token has expired or has been revoked.",
        ),
    },
    "ERR_SCOPE_ACCESS_DENIED": {
        "fr": LocalizedErrorCopy(
            "Accès au périmètre ou module refusé",
            "Votre rôle RBAC ne vous autorise pas à accéder à ce périmètre ou module.",
        ),
        "en": LocalizedErrorCopy(
            "Scope or module access denied",
            "Your RBAC role does not grant access to this scope or module.",
        ),
    },
    "ERR_PERMISSION_BROKER_INTERCEPTED": {
        "fr": LocalizedErrorCopy(
            "Accès externe intercepté par le Permission Broker",
            "L'accès à la ressource externe a été refusé (401/403). Consultez la carte "
            "Permission Broker pour demander le rôle requis dans Jira.",
        ),
        "en": LocalizedErrorCopy(
            "External access intercepted by Permission Broker",
            "External resource access was denied (401/403). Inspect the Permission Broker "
            "card to request the required role in Jira.",
        ),
    },
    "ERR_CONFUSED_DEPUTY_BLOCKED": {
        "fr": LocalizedErrorCopy(
            "Élévation de privilèges Service Principal bloquée",
            "L'exécution en mode service_principal est interdite sans approbation explicite "
            "d'un administrateur (protection anti-Confused Deputy).",
        ),
        "en": LocalizedErrorCopy(
            "Service Principal privilege escalation blocked",
            "Execution in service_principal mode is forbidden without explicit administrator "
            "approval (anti-Confused Deputy protection).",
        ),
    },
    "ERR_ONTOLOGY_CONFLICT": {
        "fr": LocalizedErrorCopy(
            "Conflit d'axiome ontologique immuable",
            "La spécialisation ou surcharge viole un axiome parent marqué immutable: true.",
        ),
        "en": LocalizedErrorCopy(
            "Immutable ontology axiom conflict",
            "The specialization or override violates a parent axiom marked immutable: true.",
        ),
    },
    "ERR_DDL_ONLY_TRANSACTIONAL_DATA_FORBIDDEN": {
        "fr": LocalizedErrorCopy(
            "Données transactionnelles interdites dans le RAG DB (DDL uniquement)",
            "Le régime DB_DDL_ONLY n'autorise que les schémas DDL (CREATE TABLE) et interdit "
            "toute indexation de lignes transactionnelles.",
        ),
        "en": LocalizedErrorCopy(
            "Transactional data forbidden in DB RAG (DDL only)",
            "The DB_DDL_ONLY regime only allows DDL schema definitions (CREATE TABLE) and "
            "forbids indexing transactional rows.",
        ),
    },
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


def resolve_locale(accept_language: str | None) -> SupportedLocale:
    """Resolve `Accept-Language` header value to `'fr'` (default) or `'en'` (`;q=` weights)."""
    if not accept_language:
        return DEFAULT_LOCALE
    candidates: list[tuple[float, int, str]] = []
    for index, token in enumerate(accept_language.split(",")):
        parts = [part.strip() for part in token.split(";") if part.strip()]
        if not parts:
            continue
        lang_tag, q, valid_q = parts[0].lower(), 1.0, True
        for param in parts[1:]:
            if param.lower().startswith("q="):
                try:
                    q = float(param[2:].strip())
                except ValueError:
                    valid_q = False
                    break
        if valid_q and 0.0 < q <= 1.0:
            candidates.append((q, index, lang_tag.split("-")[0]))

    candidates.sort(key=lambda item: (-item[0], item[1]))
    for _q, _index, primary in candidates:
        if primary in ("en", "fr"):
            return "en" if primary == "en" else "fr"
    return DEFAULT_LOCALE


def get_localized_error_text(
    error_code: str, locale: SupportedLocale = DEFAULT_LOCALE, detail_override: str | None = None
) -> LocalizedErrorCopy:
    """Return localized `(title, detail)` for `error_code` with safe fallback."""
    catalog_entry = ERROR_CATALOG.get(error_code) or ERROR_CATALOG["ERR_INTERNAL_SERVER_ERROR"]
    localized = catalog_entry.get(locale) or catalog_entry[DEFAULT_LOCALE]
    if detail_override:
        return LocalizedErrorCopy(title=localized.title, detail=detail_override)
    return localized


class OrciaDomainError(Exception):
    """Base class for all ORCIA domain errors mapped to RFC 9457 Problem Details."""

    error_code: str = "ERR_INTERNAL_SERVER_ERROR"
    http_status: int = 500
    type_slug: str = "internal-server-error"

    def __init__(
        self,
        *,
        detail_override: str | None = None,
        instance: str | None = None,
        permission_broker_hint: str | None = None,
    ) -> None:
        default_copy = get_localized_error_text(self.error_code, DEFAULT_LOCALE, detail_override)
        super().__init__(default_copy.detail)
        self.detail_override = detail_override
        self.instance = instance
        self.permission_broker_hint = permission_broker_hint

    @property
    def type_uri(self) -> str:
        return f"https://orcia.io/problems/{self.type_slug}"

    def localize(self, locale: SupportedLocale = DEFAULT_LOCALE) -> LocalizedErrorCopy:
        return get_localized_error_text(self.error_code, locale, self.detail_override)


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


class InvalidCredentialsError(OrciaDomainError):
    error_code = "ERR_AUTH_INVALID_CREDENTIALS"
    http_status, type_slug = 401, "auth-invalid-credentials"


class InvalidMfaCodeError(OrciaDomainError):
    error_code, http_status, type_slug = "ERR_AUTH_MFA_INVALID", 401, "auth-mfa-invalid"


class RevokedTokenError(OrciaDomainError):
    error_code, http_status, type_slug = "ERR_AUTH_TOKEN_REVOKED", 401, "auth-token-revoked"


class ScopeAccessDeniedError(OrciaDomainError):
    error_code, http_status, type_slug = "ERR_SCOPE_ACCESS_DENIED", 403, "scope-access-denied"


class PermissionBrokerDeniedError(OrciaDomainError):
    error_code = "ERR_PERMISSION_BROKER_INTERCEPTED"
    http_status, type_slug = 403, "permission-broker-intercepted"


class ConfusedDeputyBlockedError(OrciaDomainError):
    error_code = "ERR_CONFUSED_DEPUTY_BLOCKED"
    http_status, type_slug = 403, "confused-deputy-blocked"


class OntologyConflictError(OrciaDomainError):
    error_code, http_status, type_slug = "ERR_ONTOLOGY_CONFLICT", 422, "ontology-conflict"


class DdlOnlyTransactionalDataError(OrciaDomainError):
    error_code = "ERR_DDL_ONLY_TRANSACTIONAL_DATA_FORBIDDEN"
    http_status, type_slug = 422, "ddl-only-transactional-data-forbidden"


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
