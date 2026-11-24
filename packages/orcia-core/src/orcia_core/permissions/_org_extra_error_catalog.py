"""Localized RFC 9457 error catalog extensions for organizational delegation (`Story 27.7`)."""

from __future__ import annotations

from orcia_kernel.enums import SupportedLocale
from orcia_kernel.errors import LocalizedErrorCopy, register_domain_error_catalog

ORG_EXTRA_ERROR_CATALOG: dict[str, dict[SupportedLocale, LocalizedErrorCopy]] = {
    "ERR_ORG_DELEGATION_ROOT_REQUIRED": {
        "fr": LocalizedErrorCopy(
            "Rattachement sous BU requis",
            "Un Responsable de Direction (BU) doit rattacher toute nouvelle sous-BU ou "
            "équipe sous une BU de son périmètre.",
        ),
        "en": LocalizedErrorCopy(
            "Parent BU attachment required",
            "A Business Unit (BU) lead must attach any new sub-BU or team under a BU "
            "in their scope.",
        ),
    },
    "ERR_ORG_DELEGATION_ROOT_MOVE_FORBIDDEN": {
        "fr": LocalizedErrorCopy(
            "Déplacement de BU racine interdit",
            "Impossible de déplacer votre Direction (BU) racine.",
        ),
        "en": LocalizedErrorCopy(
            "Root BU move forbidden",
            "Cannot move your root Business Unit (BU).",
        ),
    },
    "ERR_ORG_DELEGATION_TEAM_PARENT_FORBIDDEN": {
        "fr": LocalizedErrorCopy(
            "Modification d'unité parente interdite",
            "Un Responsable d'Équipe ne peut pas modifier l'unité parente.",
        ),
        "en": LocalizedErrorCopy(
            "Parent unit change forbidden",
            "A Team Lead cannot modify the parent organizational unit.",
        ),
    },
    "ERR_ORG_DELEGATION_TEAM_BILLING_FORBIDDEN": {
        "fr": LocalizedErrorCopy(
            "Modification FinOps interdite",
            "Un Responsable d'Équipe ne peut pas modifier la facturation FinOps.",
        ),
        "en": LocalizedErrorCopy(
            "FinOps billing change forbidden",
            "A Team Lead cannot modify FinOps billing settings.",
        ),
    },
    "ERR_ORG_DELEGATION_ONTOLOGY_BU_ONLY": {
        "fr": LocalizedErrorCopy(
            "Affectation référent glossaire limitée aux BU",
            "Les référents glossaire ne peuvent être modifiés que sur une Direction (BU).",
        ),
        "en": LocalizedErrorCopy(
            "Glossary leads restricted to BUs",
            "Glossary leads can only be modified on a Business Unit (BU).",
        ),
    },
    "ERR_ORG_INVITE_MEMBER_TEAM_ONLY": {
        "fr": LocalizedErrorCopy(
            "Rattachement à une équipe requis",
            "Un membre d'équipe doit être rattaché à une Équipe (TEAM).",
        ),
        "en": LocalizedErrorCopy(
            "Team attachment required",
            "A team member must be assigned to a Team (TEAM).",
        ),
    },
    "ERR_ORG_INVITE_OBSERVER_TEAM_ONLY": {
        "fr": LocalizedErrorCopy(
            "Rattachement observateur à une équipe requis",
            "Un observateur d'équipe doit être rattaché à une Équipe (TEAM).",
        ),
        "en": LocalizedErrorCopy(
            "Team attachment required for observer",
            "A team observer must be assigned to a Team (TEAM).",
        ),
    },
    "ERR_ORG_INVITE_TEAM_LEAD_TEAM_ONLY": {
        "fr": LocalizedErrorCopy(
            "Rattachement TEAM_LEAD invalide",
            "Le rôle TEAM_LEAD doit être rattaché à une Équipe (TEAM).",
        ),
        "en": LocalizedErrorCopy(
            "Invalid TEAM_LEAD attachment",
            "The TEAM_LEAD role must be assigned to a Team (TEAM).",
        ),
    },
    "ERR_ORG_INVITE_BU_LEAD_BU_ONLY": {
        "fr": LocalizedErrorCopy(
            "Rattachement BU_LEAD invalide",
            "Le rôle BU_LEAD doit être rattaché à une Direction (BU).",
        ),
        "en": LocalizedErrorCopy(
            "Invalid BU_LEAD attachment",
            "The BU_LEAD role must be assigned to a Business Unit (BU).",
        ),
    },
    "ERR_ORG_INVITE_ONTOLOGY_LEAD_BU_ONLY": {
        "fr": LocalizedErrorCopy(
            "Rattachement ONTOLOGY_LEAD invalide",
            "Le rôle ONTOLOGY_LEAD (Référent Glossaire) doit être rattaché à une Direction (BU).",
        ),
        "en": LocalizedErrorCopy(
            "Invalid ONTOLOGY_LEAD attachment",
            "The ONTOLOGY_LEAD (Glossary Lead) role must be assigned to a Business Unit (BU).",
        ),
    },
    "ERR_ORG_UNIT_EMPTY_NAME_OR_SLUG": {
        "fr": LocalizedErrorCopy(
            "Identifiant ou nom d'unité vide",
            "Le nom ou l'identifiant court de l'unité ne peut pas être vide.",
        ),
        "en": LocalizedErrorCopy(
            "Empty unit name or slug",
            "The unit name or short identifier cannot be empty.",
        ),
    },
    "ERR_ORG_UNIT_PARENT_NOT_FOUND": {
        "fr": LocalizedErrorCopy(
            "Unité parente introuvable",
            "Unité parente introuvable : '{parent_ref}'.",
        ),
        "en": LocalizedErrorCopy(
            "Parent unit not found",
            "Parent unit not found: '{parent_ref}'.",
        ),
    },
    "ERR_ORG_UNIT_DUPLICATE_SLUG_OWNED": {
        "fr": LocalizedErrorCopy(
            "Identifiant court déjà utilisé",
            "L'identifiant court '{slug}' est déjà utilisé par « {owner_name} ».",
        ),
        "en": LocalizedErrorCopy(
            "Short identifier already in use",
            "Short identifier '{slug}' is already used by '{owner_name}'.",
        ),
    },
    "ERR_ORG_UNIT_NOT_EMPTY_DETAIL": {
        "fr": LocalizedErrorCopy(
            "Suppression refusée — unité non vide",
            "Suppression refusée pour « {target_name} » : {details}. "
            "Déplacez ou supprimez d'abord ces éléments avant de supprimer l'unité.",
        ),
        "en": LocalizedErrorCopy(
            "Deletion refused — unit not empty",
            "Deletion refused for '{target_name}': {details}. "
            "Move or remove these items first before deleting the unit.",
        ),
    },
    "ERR_ORG_UNKNOWN_LEAD_USER": {
        "fr": LocalizedErrorCopy(
            "Responsable inconnu",
            "L'identifiant de responsable '{user_ref}' ne correspond à aucun utilisateur "
            "actif et connu de la plateforme.",
        ),
        "en": LocalizedErrorCopy(
            "Unknown lead user",
            "Lead identifier '{user_ref}' does not match any active known platform user.",
        ),
    },
    "ERR_ORG_UNKNOWN_MEMBER_USER": {
        "fr": LocalizedErrorCopy(
            "Membre inconnu",
            "L'identifiant de membre '{user_ref}' ne correspond à aucun utilisateur "
            "actif et connu de la plateforme.",
        ),
        "en": LocalizedErrorCopy(
            "Unknown member user",
            "Member identifier '{user_ref}' does not match any active known platform user.",
        ),
    },
}

register_domain_error_catalog(ORG_EXTRA_ERROR_CATALOG)

__all__ = ["ORG_EXTRA_ERROR_CATALOG"]
