"""Permissions & Auth domain errors (`AD-19`, `Story 3.2a`).

Inherits from `orcia_kernel.errors.OrciaDomainError` and registers localized FR/EN copy.
"""

from __future__ import annotations

from orcia_kernel.enums import SupportedLocale
from orcia_kernel.errors import (
    LocalizedErrorCopy,
    ObserverModeReadOnlyError,
    OrciaDomainError,
    ReadSourceDeniedError,
    ResourceNotFoundError,
    ScopeAccessDeniedError,
    ValidationDomainError,
    register_domain_error_catalog,
)

PERMISSIONS_ERROR_CATALOG: dict[str, dict[SupportedLocale, LocalizedErrorCopy]] = {
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
    "ERR_AUTH_REQUIRED": {
        "fr": LocalizedErrorCopy(
            "Authentification requise",
            "Connectez-vous pour accéder à cette ressource.",
        ),
        "en": LocalizedErrorCopy(
            "Authentication required",
            "Sign in to access this resource.",
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
}

register_domain_error_catalog(PERMISSIONS_ERROR_CATALOG)


class InvalidCredentialsError(OrciaDomainError):
    error_code = "ERR_AUTH_INVALID_CREDENTIALS"
    http_status, type_slug = 401, "auth-invalid-credentials"


class InvalidMfaCodeError(OrciaDomainError):
    error_code, http_status, type_slug = "ERR_AUTH_MFA_INVALID", 401, "auth-mfa-invalid"


class AuthenticationRequiredError(OrciaDomainError):
    """Raised when no Bearer token is supplied outside `ORCIA_ENV` local / test (BUG-E2E-04)."""

    error_code, http_status, type_slug = "ERR_AUTH_REQUIRED", 401, "auth-required"


class RevokedTokenError(OrciaDomainError):
    error_code, http_status, type_slug = "ERR_AUTH_TOKEN_REVOKED", 401, "auth-token-revoked"


class PermissionBrokerDeniedError(OrciaDomainError):
    error_code = "ERR_PERMISSION_BROKER_INTERCEPTED"
    http_status, type_slug = 403, "permission-broker-intercepted"


class ConfusedDeputyBlockedError(OrciaDomainError):
    error_code = "ERR_CONFUSED_DEPUTY_BLOCKED"
    http_status, type_slug = 403, "confused-deputy-blocked"


class GrantEscalationForbiddenError(OrciaDomainError):
    error_code = "ERR_GRANT_ESCALATION_FORBIDDEN"
    http_status, type_slug = 403, "grant-escalation-forbidden"


class AdminLockoutPreventedError(OrciaDomainError):
    error_code = "ERR_ADMIN_LOCKOUT_PREVENTED"
    http_status, type_slug = 422, "admin-lockout-prevented"


class SecretConfigReadDeniedError(OrciaDomainError):
    error_code = "ERR_SECRET_CONFIG_READ_DENIED"
    http_status, type_slug = 403, "secret-config-read-denied"


class PreconditionRequiredError(OrciaDomainError):
    error_code = "ERR_PRECONDITION_REQUIRED"
    http_status, type_slug = 428, "precondition-required"


class SettingsVersionConflictError(OrciaDomainError):
    error_code = "ERR_SETTINGS_VERSION_CONFLICT"
    http_status, type_slug = 412, "settings-version-conflict"


class C3WorkspaceRequiredError(OrciaDomainError):
    error_code = "ERR_C3_WORKSPACE_REQUIRED"
    http_status, type_slug = 403, "c3-workspace-required"


class OrgUnitInvalidParentKindError(OrciaDomainError):
    error_code = "ERR_ORG_UNIT_INVALID_PARENT_KIND"
    http_status, type_slug = 422, "org-unit-invalid-parent-kind"


class OrgUnitHierarchyCycleError(OrciaDomainError):
    error_code = "ERR_ORG_UNIT_HIERARCHY_CYCLE"
    http_status, type_slug = 422, "org-unit-hierarchy-cycle"


class OrgUnitDuplicateSlugError(OrciaDomainError):
    error_code = "ERR_ORG_UNIT_DUPLICATE_SLUG"
    http_status, type_slug = 409, "org-unit-duplicate-slug"


class OrgUnitNotEmptyError(OrciaDomainError):
    error_code = "ERR_ORG_UNIT_NOT_EMPTY"
    http_status, type_slug = 409, "org-unit-not-empty"


class InvalidIamRoleError(OrciaDomainError):
    error_code = "ERR_IAM_INVALID_ROLE"
    http_status, type_slug = 422, "iam-invalid-role"


class DuplicateIamPrincipalError(OrciaDomainError):
    error_code = "ERR_IAM_DUPLICATE_PRINCIPAL"
    http_status, type_slug = 409, "iam-duplicate-principal"


class UnsafeConnectorEndpointUrlError(OrciaDomainError):
    error_code = "ERR_UNSAFE_CONNECTOR_ENDPOINT_URL"
    http_status, type_slug = 422, "unsafe-connector-endpoint-url"


class CodegraphWorkspaceLeadRequiredError(OrciaDomainError):
    error_code = "ERR_CODEGRAPH_WORKSPACE_LEAD_REQUIRED"
    http_status, type_slug = 403, "codegraph-workspace-lead-required"


class WebhookSignatureInvalidError(OrciaDomainError):
    error_code = "ERR_WEBHOOK_SIGNATURE_INVALID"
    http_status, type_slug = 401, "webhook-signature-invalid"


__all__ = [
    "AdminLockoutPreventedError",
    "C3WorkspaceRequiredError",
    "CodegraphWorkspaceLeadRequiredError",
    "ConfusedDeputyBlockedError",
    "DuplicateIamPrincipalError",
    "GrantEscalationForbiddenError",
    "InvalidCredentialsError",
    "InvalidIamRoleError",
    "InvalidMfaCodeError",
    "ObserverModeReadOnlyError",
    "OrciaDomainError",
    "OrgUnitDuplicateSlugError",
    "OrgUnitHierarchyCycleError",
    "OrgUnitInvalidParentKindError",
    "OrgUnitNotEmptyError",
    "PermissionBrokerDeniedError",
    "PreconditionRequiredError",
    "ReadSourceDeniedError",
    "ResourceNotFoundError",
    "RevokedTokenError",
    "ScopeAccessDeniedError",
    "SecretConfigReadDeniedError",
    "SettingsVersionConflictError",
    "UnsafeConnectorEndpointUrlError",
    "ValidationDomainError",
    "WebhookSignatureInvalidError",
]
