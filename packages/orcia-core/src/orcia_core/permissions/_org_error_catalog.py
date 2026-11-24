"""Org-unit and IAM hierarchy localized RFC 9457 error catalog (`AD-19`, `Story 27.7`)."""

from __future__ import annotations

from orcia_core.permissions import _permissions_extra_error_catalog  # noqa: F401
from orcia_kernel.enums import SupportedLocale
from orcia_kernel.errors import LocalizedErrorCopy

ORG_ERROR_CATALOG: dict[str, dict[SupportedLocale, LocalizedErrorCopy]] = {
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
    "ERR_ORG_UNIT_DUPLICATE_SLUG_DETAIL": {
        "fr": LocalizedErrorCopy(
            "Identifiant court d'unité déjà utilisé",
            "L'identifiant court '{slug}' est déjà utilisé par « {existing_name} ».",
        ),
        "en": LocalizedErrorCopy(
            "Duplicate organizational unit slug",
            "The short identifier '{slug}' is already used by '{existing_name}'.",
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
    "ERR_ORG_UNIT_NOT_FOUND_DETAIL": {
        "fr": LocalizedErrorCopy(
            "Unité organisationnelle introuvable",
            "Unité organisationnelle introuvable : '{org_unit_id}'.",
        ),
        "en": LocalizedErrorCopy(
            "Organizational unit not found",
            "Organizational unit not found: '{org_unit_id}'.",
        ),
    },
    "ERR_ORG_UNIT_PARENT_NOT_FOUND_DETAIL": {
        "fr": LocalizedErrorCopy(
            "Unité organisationnelle introuvable",
            "Unité parente introuvable : '{parent_id}'.",
        ),
        "en": LocalizedErrorCopy(
            "Organizational unit not found",
            "Parent organizational unit not found: '{parent_id}'.",
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
            "Le rôle demandé n'appartient pas aux 7 rôles officiels (PLATFORM_ADMIN, SECOPS, "
            "BU_LEAD, TEAM_LEAD, ONTOLOGY_LEAD, CONTRIBUTOR, OBSERVER).",
        ),
        "en": LocalizedErrorCopy(
            "Invalid IAM role",
            "The requested role is not among the 7 official roles (PLATFORM_ADMIN, SECOPS, "
            "BU_LEAD, TEAM_LEAD, ONTOLOGY_LEAD, CONTRIBUTOR, OBSERVER).",
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
    "ERR_ORG_UNIT_UNKNOWN_USER_DETAIL": {
        "fr": LocalizedErrorCopy(
            "Utilisateur inconnu ou inactif",
            "L'identifiant '{identifier}' ne correspond à aucun utilisateur actif et connu "
            "de la plateforme.",
        ),
        "en": LocalizedErrorCopy(
            "Unknown or inactive user",
            "The identifier '{identifier}' does not match any active known user on the platform.",
        ),
    },
    "ERR_ORG_UNIT_SCOPE_FORBIDDEN": {
        "fr": LocalizedErrorCopy(
            "Action refusée hors de votre périmètre organisationnel",
            "Vous ne pouvez gérer que les unités relevant de votre Direction (BU) ou de vos "
            "équipes dirigées.",
        ),
        "en": LocalizedErrorCopy(
            "Action forbidden outside your organizational scope",
            "You can only manage units within your governed Business Unit subtree or led teams.",
        ),
    },
    "ERR_ORG_UNIT_ROOT_DELETE_FORBIDDEN": {
        "fr": LocalizedErrorCopy(
            "Suppression de votre Direction (BU) racine interdite",
            "Un Responsable de Direction (BU) ne peut supprimer que les sous-BUs et équipes "
            "enfants ; la suppression de sa BU racine relève de l'Administrateur Plateforme.",
        ),
        "en": LocalizedErrorCopy(
            "Deleting your root Business Unit is forbidden",
            "A Division Lead (BU) can only delete child sub-BUs and teams; deleting the root BU "
            "requires a Platform Administrator.",
        ),
    },
    "ERR_ORG_UNIT_LAST_LEAD_REMOVAL_FORBIDDEN": {
        "fr": LocalizedErrorCopy(
            "Retrait du dernier responsable interdit",
            "Une unité ne peut pas perdre son dernier responsable ni être laissée sans "
            "responsable par auto-retrait.",
        ),
        "en": LocalizedErrorCopy(
            "Removing the last lead is forbidden",
            "A unit cannot lose its last lead or be left without a lead via self-removal.",
        ),
    },
}

__all__ = ["ORG_ERROR_CATALOG"]
