"""Localized RFC 9457 error catalog extensions for permissions & org domains (`Story 27.7`)."""

from __future__ import annotations

from orcia_core.permissions import _org_extra_error_catalog  # noqa: F401
from orcia_kernel.enums import SupportedLocale
from orcia_kernel.errors import LocalizedErrorCopy, register_domain_error_catalog

PERMISSIONS_EXTRA_ERROR_CATALOG: dict[str, dict[SupportedLocale, LocalizedErrorCopy]] = {
    "ERR_CONNECTOR_BREAKER_OPEN": {
        "fr": LocalizedErrorCopy(
            "Disjoncteur connecteur ouvert",
            "Disjoncteur OPEN pour le connecteur '{scheme}' ({failures} échecs consécutifs).",
        ),
        "en": LocalizedErrorCopy(
            "Connector circuit breaker open",
            "Circuit breaker is OPEN for connector '{scheme}' ({failures} consecutive failures).",
        ),
    },
    "ERR_CONNECTOR_BUDGET_EXCEEDED": {
        "fr": LocalizedErrorCopy(
            "Plafond budgétaire dépassé",
            "Plafond budgétaire dépassé sur '{scheme}.{action}' : "
            "{next_cost} USD > {max_cost} USD.",
        ),
        "en": LocalizedErrorCopy(
            "Budget ceiling exceeded",
            "Budget ceiling exceeded on '{scheme}.{action}': {next_cost} USD > {max_cost} USD.",
        ),
    },
    "ERR_BROKER_NO_DB_USER": {
        "fr": LocalizedErrorCopy(
            "Aucun utilisateur enregistré",
            "Aucun utilisateur enregistré en base pour créer un ticket d'accès.",
        ),
        "en": LocalizedErrorCopy(
            "No registered user",
            "No registered user found in database to create an access ticket.",
        ),
    },
    "ERR_MCP_TOKEN_EMPTY_TARGET_SLUG": {
        "fr": LocalizedErrorCopy(
            "Cible MCP invalide",
            "Le slug de cible MCP (Espace ou Agent) ne peut pas être vide.",
        ),
        "en": LocalizedErrorCopy(
            "Invalid MCP target",
            "The MCP target slug (Space or Agent) cannot be empty.",
        ),
    },
    "ERR_MCP_TOKEN_INVALID_EXPIRATION": {
        "fr": LocalizedErrorCopy(
            "Durée d'expiration MCP invalide",
            "L'expiration d'un jeton MCP personnel doit être obligatoirement de 30 ou 90 jours.",
        ),
        "en": LocalizedErrorCopy(
            "Invalid MCP token expiration",
            "Personal MCP token expiration must be 30 or 90 days.",
        ),
    },
    "ERR_MCP_TOKEN_INVALID_RPM": {
        "fr": LocalizedErrorCopy(
            "Plafond RPM MCP invalide",
            "Le plafond RPM du jeton MCP doit être compris entre 1 et 600 requêtes/minute.",
        ),
        "en": LocalizedErrorCopy(
            "Invalid MCP RPM limit",
            "MCP token RPM limit must be between 1 and 600 requests/minute.",
        ),
    },
    "ERR_MCP_TOKEN_MISSING_SPACE": {
        "fr": LocalizedErrorCopy(
            "Espace autorisé manquant",
            "Au moins un Espace autorisé doit être sélectionné pour le jeton MCP.",
        ),
        "en": LocalizedErrorCopy(
            "Missing authorized space",
            "At least one authorized Space must be selected for the MCP token.",
        ),
    },
    "ERR_MCP_TOKEN_MISSING_CAPABILITY": {
        "fr": LocalizedErrorCopy(
            "Capacité MCP manquante",
            "Au moins une capacité exposée doit être sélectionnée pour le jeton MCP.",
        ),
        "en": LocalizedErrorCopy(
            "Missing MCP capability",
            "At least one exposed capability must be selected for the MCP token.",
        ),
    },
    "ERR_CONTRACT_INVALID_CRITICALITY": {
        "fr": LocalizedErrorCopy(
            "Criticité de contrat invalide",
            "Criticité invalide pour contrat : '{criticality}'.",
        ),
        "en": LocalizedErrorCopy(
            "Invalid contract criticality",
            "Invalid contract criticality: '{criticality}'.",
        ),
    },
    "ERR_CONTRACT_INVALID_BUDGET": {
        "fr": LocalizedErrorCopy(
            "Plafond budgétaire invalide",
            "Le plafond budgétaire max_cost_per_run_usd doit être > 0.",
        ),
        "en": LocalizedErrorCopy(
            "Invalid budget ceiling",
            "max_cost_per_run_usd budget ceiling must be > 0.",
        ),
    },
    "ERR_CONTRACT_INVALID_SAMPLING_RATE": {
        "fr": LocalizedErrorCopy(
            "Taux d'échantillonnage invalide",
            "Le taux d'échantillonnage post-hoc doit être entre 0.10 et 0.20.",
        ),
        "en": LocalizedErrorCopy(
            "Invalid sampling rate",
            "Post-hoc sampling rate must be between 0.10 and 0.20.",
        ),
    },
    "ERR_CONTRACT_INVALID_TIE_BREAK": {
        "fr": LocalizedErrorCopy(
            "Politique de résolution invalide",
            "Politique tie_break_policy invalide : '{policy}'.",
        ),
        "en": LocalizedErrorCopy(
            "Invalid tie-break policy",
            "Invalid tie_break_policy: '{policy}'.",
        ),
    },
    "ERR_CONNECTOR_NOT_REGISTERED": {
        "fr": LocalizedErrorCopy(
            "Connecteur non enregistré",
            "Connecteur '{scheme}' non enregistré dans orcia.connectors.",
        ),
        "en": LocalizedErrorCopy(
            "Connector not registered",
            "Connector '{scheme}' is not registered in orcia.connectors.",
        ),
    },
    "ERR_IAM_EMPTY_ROLES": {
        "fr": LocalizedErrorCopy(
            "Rôle officiel requis",
            "Au moins un rôle officiel doit être attribué au compte.",
        ),
        "en": LocalizedErrorCopy(
            "Official role required",
            "At least one official role must be assigned to the account.",
        ),
    },
    "ERR_IAM_UNKNOWN_RESOURCE_KIND": {
        "fr": LocalizedErrorCopy(
            "Type de ressource IAM inconnu",
            "Type de ressource inconnu pour l'exception IAM : '{kind}'.",
        ),
        "en": LocalizedErrorCopy(
            "Unknown IAM resource kind",
            "Unknown resource kind for IAM exception: '{kind}'.",
        ),
    },
    "ERR_IAM_EMPTY_PRINCIPAL_ID": {
        "fr": LocalizedErrorCopy(
            "Identifiant de compte vide",
            "L'identifiant du compte ne peut pas être vide.",
        ),
        "en": LocalizedErrorCopy(
            "Empty account identifier",
            "The account identifier cannot be empty.",
        ),
    },
    "ERR_IAM_EMPTY_DISPLAY_NAME": {
        "fr": LocalizedErrorCopy(
            "Nom affiché vide",
            "Le nom affiché du compte ne peut pas être vide.",
        ),
        "en": LocalizedErrorCopy(
            "Empty display name",
            "The account display name cannot be empty.",
        ),
    },
    "ERR_MCP_TOKEN_EXPIRY_INVALID": {
        "fr": LocalizedErrorCopy(
            "Durée d'expiration invalide",
            "L'expiration d'un jeton personnel doit être de 30 ou 90 jours.",
        ),
        "en": LocalizedErrorCopy(
            "Invalid expiration duration",
            "Personal access token expiration must be 30 or 90 days.",
        ),
    },
    "ERR_MCP_TOKEN_RPM_INVALID": {
        "fr": LocalizedErrorCopy(
            "Plafond de débit invalide",
            "Le plafond de requêtes par minute du jeton doit être compris entre 1 et 600.",
        ),
        "en": LocalizedErrorCopy(
            "Invalid rate limit",
            "The token rate limit must be between 1 and 600 requests per minute.",
        ),
    },
    "ERR_MCP_TOKEN_SPACES_REQUIRED": {
        "fr": LocalizedErrorCopy(
            "Espace autorisé requis",
            "Au moins un Espace autorisé doit être sélectionné pour le jeton personnel.",
        ),
        "en": LocalizedErrorCopy(
            "Authorized Space required",
            "At least one authorized Space must be selected for the personal access token.",
        ),
    },
    "ERR_MCP_TOKEN_CAPS_REQUIRED": {
        "fr": LocalizedErrorCopy(
            "Capacité exposée requise",
            "Au moins une capacité exposée doit être sélectionnée pour le jeton personnel.",
        ),
        "en": LocalizedErrorCopy(
            "Exposed capability required",
            "At least one exposed capability must be selected for the personal access token.",
        ),
    },
}

register_domain_error_catalog(PERMISSIONS_EXTRA_ERROR_CATALOG)

__all__ = ["PERMISSIONS_EXTRA_ERROR_CATALOG"]
