"""Permissions & Auth domain localized RFC 9457 error catalog (`AD-19`, `Story 3.2a`).

Zero framework imports (`fastapi`, `sqlalchemy`, etc.).
"""

from __future__ import annotations

from orcia_core.permissions._auth_error_catalog import AUTH_ERROR_CATALOG
from orcia_core.permissions._org_error_catalog import ORG_ERROR_CATALOG
from orcia_kernel.enums import SupportedLocale
from orcia_kernel.errors import LocalizedErrorCopy

PERMISSIONS_ERROR_CATALOG: dict[str, dict[SupportedLocale, LocalizedErrorCopy]] = {
    **AUTH_ERROR_CATALOG,
    **ORG_ERROR_CATALOG,
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
    "ERR_GRANT_ESCALATION_FORBIDDEN": {
        "fr": LocalizedErrorCopy(
            "Escalade de privilèges lors de la délégation interdite",
            "Les droits délégués via le verbe 'grant' doivent être un sous-ensemble strict des "
            "droits détenus par le délégant sur ce périmètre (AD-21).",
        ),
        "en": LocalizedErrorCopy(
            "Privilege escalation during delegation forbidden",
            "Delegated permissions via the 'grant' verb must be a strict subset of the "
            "permissions held by the delegator on this scope (AD-21).",
        ),
    },
    "ERR_ADMIN_LOCKOUT_PREVENTED": {
        "fr": LocalizedErrorCopy(
            "Verrouillage administratif empêché",
            "Impossible de retirer le dernier administrateur actif (PLATFORM_ADMIN) ou de "
            "désactiver la dernière méthode d'authentification active (AD-21).",
        ),
        "en": LocalizedErrorCopy(
            "Administrative lockout prevented",
            "Cannot remove the last active PLATFORM_ADMIN or disable the last active "
            "authentication method (AD-21).",
        ),
    },
    "ERR_SECRET_CONFIG_READ_DENIED": {
        "fr": LocalizedErrorCopy(
            "Lecture des paramètres secrets refusée",
            "Le verbe 'execute' autorise l'invocation de la ressource mais interdit la lecture "
            "('read') de sa configuration détaillée ou de ses paramètres secrets (AD-21).",
        ),
        "en": LocalizedErrorCopy(
            "Secret configuration read access denied",
            "The 'execute' verb authorizes resource invocation but forbids reading ('read') "
            "its detailed configuration or secret parameters (AD-21).",
        ),
    },
    "ERR_PRECONDITION_REQUIRED": {
        "fr": LocalizedErrorCopy(
            "En-tête If-Match requis pour la modification des paramètres",
            "Toute mutation d'un paramètre versionné exige l'en-tête HTTP If-Match (AD-21).",
        ),
        "en": LocalizedErrorCopy(
            "If-Match header required for settings mutation",
            "Mutating a versioned setting requires the HTTP If-Match header (AD-21).",
        ),
    },
    "ERR_SETTINGS_VERSION_CONFLICT": {
        "fr": LocalizedErrorCopy(
            "Conflit de version sur le paramètre (ETag / If-Match périmé)",
            "Le paramètre a été modifié par un autre acteur. Rechargez l'ETag courant avant "
            "de soumettre votre modification (AD-21).",
        ),
        "en": LocalizedErrorCopy(
            "Settings version conflict (stale ETag / If-Match)",
            "The setting was modified by another actor. Reload the current ETag before "
            "submitting your update (AD-21).",
        ),
    },
    "ERR_C3_WORKSPACE_REQUIRED": {
        "fr": LocalizedErrorCopy(
            "Workspace habilité C3 requis",
            "Un document ou une source classifié C3 (Confidentiel Restreint) ne peut être "
            "rattaché qu'à un Workspace en visibilité CONFIDENTIAL_RESTRICTED (AD-21).",
        ),
        "en": LocalizedErrorCopy(
            "C3-cleared Workspace required",
            "A document or datasource classified C3 (Confidential Restricted) can only be "
            "attached to a Workspace with CONFIDENTIAL_RESTRICTED visibility (AD-21).",
        ),
    },
    "ERR_CODEGRAPH_WORKSPACE_LEAD_REQUIRED": {
        "fr": LocalizedErrorCopy(
            "Rôle Responsable d'espace requis pour GitNexus",
            "L'activation ou la modification du graphe de code GitNexus requiert au moins "
            "l'un des rôles : TEAM_LEAD, BU_LEAD, PLATFORM_ADMIN, SECOPS.",
        ),
        "en": LocalizedErrorCopy(
            "Workspace Lead role required for GitNexus",
            "Activating or modifying GitNexus code graph requires at least one of the "
            "following roles: TEAM_LEAD, BU_LEAD, PLATFORM_ADMIN, SECOPS.",
        ),
    },
    "ERR_WEBHOOK_SIGNATURE_INVALID": {
        "fr": LocalizedErrorCopy(
            "Signature webhook invalide ou manquante",
            "L'en-tête de signature HMAC-SHA256 du webhook entrant est invalide, absente ou "
            "ne correspond pas au secret configuré.",
        ),
        "en": LocalizedErrorCopy(
            "Invalid or missing webhook signature",
            "The incoming webhook HMAC-SHA256 signature header is missing, invalid, or "
            "does not match the configured secret.",
        ),
    },
    "ERR_UNSAFE_CONNECTOR_ENDPOINT_URL": {
        "fr": LocalizedErrorCopy(
            "URL de connecteur d'entreprise non sécurisée (protection anti-SSRF)",
            "L'URL de base du connecteur doit utiliser HTTP/HTTPS et ne peut pas cibler une "
            "adresse de métadonnées Cloud ou link-local (169.254.0.0/16, fe80::/10, "
            "metadata.google.internal, 100.100.100.200).",
        ),
        "en": LocalizedErrorCopy(
            "Unsafe enterprise connector endpoint URL (SSRF protection)",
            "The connector base URL must use HTTP/HTTPS and must not target cloud metadata or "
            "link-local addresses (169.254.0.0/16, fe80::/10, metadata.google.internal, "
            "100.100.100.200).",
        ),
    },
    "ERR_PRIVILEGE_ESCALATION_FORBIDDEN": {
        "fr": LocalizedErrorCopy(
            "Élévation de privilèges interdite",
            "L'attribution ou la modification des rôles PLATFORM_ADMIN et SECOPS est interdite "
            "dans ce contexte.",
        ),
        "en": LocalizedErrorCopy(
            "Privilege escalation forbidden",
            "Granting or modifying PLATFORM_ADMIN or SECOPS roles is forbidden in this context.",
        ),
    },
    "ERR_CONNECTOR_CIRCUIT_OPEN": {
        "fr": LocalizedErrorCopy(
            "Connecteur externe temporairement suspendu",
            "Le coupe-circuit de ce service externe est ouvert suite à un dépassement "
            "de plafond ou à des anomalies répétées. Réarmement requis dans FinOps.",
        ),
        "en": LocalizedErrorCopy(
            "External connector temporarily suspended",
            "This external service circuit breaker is open due to a quota ceiling or "
            "repeated telemetry anomalies. Manual reset is required in FinOps.",
        ),
    },
    "ERR_AUTONOMY_CONTRACT_NOT_FOUND": {
        "fr": LocalizedErrorCopy(
            "Contrat d'autonomie introuvable",
            "Aucun contrat d'autonomie actif ou correspondant n'a été trouvé pour ce processus.",
        ),
        "en": LocalizedErrorCopy(
            "Autonomy contract not found",
            "No active or matching autonomy contract was found for this process.",
        ),
    },
    "ERR_CONTRACT_SERVICE_PRINCIPAL_INVALID": {
        "fr": LocalizedErrorCopy(
            "Compte de service invalide ou non habilité sur cet espace",
            "Le compte de service sélectionné doit être actif dans l'annuaire IAM et "
            "habilité sur le périmètre du processus.",
        ),
        "en": LocalizedErrorCopy(
            "Service account invalid or not authorized on this workspace",
            "The selected service account must be active in the IAM directory and "
            "authorized on the workspace scope.",
        ),
    },
    "ERR_CONTRACT_PRIVILEGE_ESCALATION": {
        "fr": LocalizedErrorCopy(
            "Confinement du contrat dépassé (élévation de privilèges refusée)",
            "Les actions autorisées par le contrat doivent rester incluses dans l'intersection "
            "des droits du signataire et de ceux du compte de service.",
        ),
        "en": LocalizedErrorCopy(
            "Contract confinement exceeded (privilege escalation denied)",
            "Actions authorized by the contract must remain a subset of the intersection "
            "of the signer's permissions and the service account's permissions.",
        ),
    },
    "ERR_CONTRACT_SIGNATURE_FORBIDDEN": {
        "fr": LocalizedErrorCopy(
            "Rôle insuffisant pour signer un contrat d'autonomie",
            "Seul un responsable d'équipe, directeur de pôle ou administrateur de la plateforme "
            "habilité sur cet espace peut signer ou révoquer un contrat d'autonomie.",
        ),
        "en": LocalizedErrorCopy(
            "Insufficient role to sign an autonomy contract",
            "Only an authorized team lead, division lead, or platform administrator on this "
            "workspace can sign or revoke an autonomy contract.",
        ),
    },
    "ERR_AUTONOMY_CONTRACT_REQUIRED": {
        "fr": LocalizedErrorCopy(
            "Contrat d'autonomie actif requis pour ce déclencheur",
            "Tout déclencheur actif ou déclenché doit être rattaché à un contrat d'autonomie "
            "signé et actif sur ce processus.",
        ),
        "en": LocalizedErrorCopy(
            "Active autonomy contract required for this trigger",
            "Every active or fired trigger must be bound to a signed active autonomy contract "
            "on this workflow.",
        ),
    },
    "ERR_TRIGGER_CIRCUIT_OPEN": {
        "fr": LocalizedErrorCopy(
            "Déclencheur suspendu par protection (coupe-circuit ouvert)",
            "Ce déclencheur a atteint son seuil de sécurité ou d'erreurs consécutives. "
            "Réactivez-le manuellement après vérification.",
        ),
        "en": LocalizedErrorCopy(
            "Trigger paused by circuit breaker protection",
            "This trigger reached its safety or consecutive failure threshold. "
            "Re-enable it manually after inspection.",
        ),
    },
    "ERR_TRIGGER_NOT_FOUND": {
        "fr": LocalizedErrorCopy(
            "Déclencheur introuvable",
            "Le déclencheur demandé n'existe pas sur cet espace ou processus.",
        ),
        "en": LocalizedErrorCopy(
            "Trigger not found",
            "The requested workflow trigger does not exist on this workspace or workflow.",
        ),
    },
    "ERR_TRIGGER_DUPLICATE_KEY": {
        "fr": LocalizedErrorCopy(
            "Identifiant technique de déclencheur déjà utilisé",
            "Un déclencheur avec la même clé existe déjà.",
        ),
        "en": LocalizedErrorCopy(
            "Duplicate trigger key",
            "A workflow trigger with the same key already exists.",
        ),
    },
    "ERR_INVALID_MCP_TOKEN_CONFIG": {
        "fr": LocalizedErrorCopy(
            "Configuration du jeton d'accès éditeur invalide",
            "Les paramètres du jeton d'accès personnel ne respectent pas les règles de sécurité.",
        ),
        "en": LocalizedErrorCopy(
            "Invalid personal access token configuration",
            "The personal access token settings do not comply with security requirements.",
        ),
    },
    "ERR_MCP_TOKEN_TARGET_EMPTY": {
        "fr": LocalizedErrorCopy(
            "Cible de jeton invalide",
            "L'identifiant de cible (Espace ou Agent) ne peut pas être vide.",
        ),
        "en": LocalizedErrorCopy(
            "Invalid token target",
            "The target identifier (Space or Agent) cannot be empty.",
        ),
    },
    "ERR_PRIVATE_WORKSPACE_VISIBILITY_LOCKED": {
        "fr": LocalizedErrorCopy(
            "Visibilité d'espace personnel verrouillée",
            "Un espace personnel privé (PRIVATE_USER) ne peut pas changer de visibilité sur "
            "place ; créez un nouvel espace d'équipe si vous souhaitez partager.",
        ),
        "en": LocalizedErrorCopy(
            "Personal workspace visibility locked",
            "A private personal workspace (PRIVATE_USER) cannot change visibility in place; "
            "create a new team workspace if you wish to share.",
        ),
    },
}

__all__ = ["PERMISSIONS_ERROR_CATALOG"]
