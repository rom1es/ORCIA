"""Permissions & Auth domain localized RFC 9457 error catalog (`AD-19`, `Story 3.2a`).

Zero framework imports (`fastapi`, `sqlalchemy`, etc.).
"""

from __future__ import annotations

from orcia_core.permissions._auth_error_catalog import AUTH_ERROR_CATALOG
from orcia_kernel.enums import SupportedLocale
from orcia_kernel.errors import LocalizedErrorCopy

PERMISSIONS_ERROR_CATALOG: dict[str, dict[SupportedLocale, LocalizedErrorCopy]] = {
    **AUTH_ERROR_CATALOG,
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
    "ERR_ORG_UNIT_INVALID_PARENT_KIND": {
        "fr": LocalizedErrorCopy(
            "Rattachement hiérarchique invalide",
            "Une Direction ou un Pôle (BU) ne peut pas être rattaché sous une Équipe (TEAM).",
        ),
        "en": LocalizedErrorCopy(
            "Invalid organizational parent kind",
            "A Division or Sub-Division (BU) cannot be attached under a Team (TEAM).",
        ),
    },
    "ERR_ORG_UNIT_HIERARCHY_CYCLE": {
        "fr": LocalizedErrorCopy(
            "Cycle détecté dans l'organigramme",
            "Une unité organisationnelle ne peut pas être rattachée à elle-même ni à l'une de "
            "ses sous-unités descendantes.",
        ),
        "en": LocalizedErrorCopy(
            "Organizational hierarchy cycle detected",
            "An organizational unit cannot be attached to itself or to any of its descendant "
            "sub-units.",
        ),
    },
    "ERR_ORG_UNIT_DUPLICATE_SLUG": {
        "fr": LocalizedErrorCopy(
            "Identifiant court d'unité déjà utilisé",
            "Une unité organisationnelle utilise déjà cet identifiant court (slug).",
        ),
        "en": LocalizedErrorCopy(
            "Duplicate organizational unit slug",
            "Another organizational unit already uses this short identifier (slug).",
        ),
    },
    "ERR_ORG_UNIT_NOT_FOUND": {
        "fr": LocalizedErrorCopy(
            "Unité organisationnelle introuvable",
            "L'unité organisationnelle spécifiée n'existe pas ou ne correspond pas au type requis.",
        ),
        "en": LocalizedErrorCopy(
            "Organizational unit not found",
            "The specified organizational unit does not exist or does not match the required type.",
        ),
    },
    "ERR_ORG_UNIT_NOT_EMPTY": {
        "fr": LocalizedErrorCopy(
            "Unité organisationnelle non vide",
            "Impossible de supprimer cette unité tant que des sous-unités ou des espaces de "
            "travail y sont rattachés. Déplacez ou supprimez d'abord ces éléments.",
        ),
        "en": LocalizedErrorCopy(
            "Organizational unit is not empty",
            "Cannot delete this unit while child units or workspaces are still attached to it. "
            "Move or delete those items first.",
        ),
    },
    "ERR_ORG_UNIT_BU_MEMBERS_FORBIDDEN": {
        "fr": LocalizedErrorCopy(
            "Affectation de membres interdite sur une Direction ou un Pôle (BU)",
            "Les membres individuels doivent être rattachés à une Équipe (TEAM) et non à une "
            "Direction ou un Pôle (BU). Seuls les co-responsables sont autorisés sur une BU.",
        ),
        "en": LocalizedErrorCopy(
            "Direct member assignment forbidden on Business Unit",
            "Individual members must be assigned to a Team, not a Business Unit (BU). "
            "Only leads (lead_user_ids) are allowed on a BU.",
        ),
    },
    "ERR_IAM_INVALID_ROLE": {
        "fr": LocalizedErrorCopy(
            "Rôle d'habilitation invalide",
            "Le rôle demandé n'appartient pas aux 6 rôles officiels (PLATFORM_ADMIN, SECOPS, "
            "BU_LEAD, TEAM_LEAD, CONTRIBUTOR, OBSERVER).",
        ),
        "en": LocalizedErrorCopy(
            "Invalid IAM role",
            "The requested role is not among the 6 official roles (PLATFORM_ADMIN, SECOPS, "
            "BU_LEAD, TEAM_LEAD, CONTRIBUTOR, OBSERVER).",
        ),
    },
    "ERR_IAM_DUPLICATE_PRINCIPAL": {
        "fr": LocalizedErrorCopy(
            "Identifiant de compte déjà enregistré",
            "Un compte humain ou un compte de service utilise déjà cet identifiant principal.",
        ),
        "en": LocalizedErrorCopy(
            "Duplicate account principal identifier",
            "A human account or service principal already uses this principal identifier.",
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
    "ERR_ORG_STORAGE_SCHEMA_OUTDATED": {
        "fr": LocalizedErrorCopy(
            "Schéma PostgreSQL de l'organisation obsolète",
            "La base de données n'est pas migrée au dernier schéma requis pour l'organisation. "
            "Une migration Alembic est requise.",
        ),
        "en": LocalizedErrorCopy(
            "Outdated organization PostgreSQL schema",
            "The database schema is not up to date for organizational units. "
            "An Alembic migration is required.",
        ),
    },
    "ERR_ORG_UNIT_UNKNOWN_USER": {
        "fr": LocalizedErrorCopy(
            "Utilisateur inconnu ou inactif",
            "L'identifiant spécifié ne correspond à aucun utilisateur humain actif "
            "et connu de la plateforme.",
        ),
        "en": LocalizedErrorCopy(
            "Unknown or inactive user",
            "The specified identifier does not match any active known human user on the platform.",
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
}

__all__ = ["PERMISSIONS_ERROR_CATALOG"]
