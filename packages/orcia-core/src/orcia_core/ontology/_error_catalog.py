"""Localized RFC 9457 error catalog for the ontology domain (`Story 27.7`)."""

from __future__ import annotations

from orcia_kernel.enums import SupportedLocale
from orcia_kernel.errors import LocalizedErrorCopy, register_domain_error_catalog

ONTOLOGY_ERROR_CATALOG: dict[str, dict[SupportedLocale, LocalizedErrorCopy]] = {
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
    "ERR_ONTOLOGY_PROMOTION_STEP_INVALID": {
        "fr": LocalizedErrorCopy(
            "Transition de promotion ontologique invalide",
            "La promotion doit cibler le palier immédiatement supérieur (L4 -> L3 -> L2 -> L1).",
        ),
        "en": LocalizedErrorCopy(
            "Invalid ontology promotion transition",
            "Promotion must target the immediate next governance level (L4 -> L3 -> L2 -> L1).",
        ),
    },
    "ERR_ONTOLOGY_SCOPE_CONFLICT_DETAIL": {
        "fr": LocalizedErrorCopy(
            "Conflit de périmètre ontologique",
            (
                "La clé '{concept_key}' appartient déjà au périmètre "
                "({existing_level}, '{existing_scope}') et ne peut être écrasée "
                "depuis ({level}, '{target_scope}')."
            ),
        ),
        "en": LocalizedErrorCopy(
            "Ontology scope conflict",
            (
                "Key '{concept_key}' already belongs to scope "
                "({existing_level}, '{existing_scope}') and cannot be overwritten "
                "from ({level}, '{target_scope}')."
            ),
        ),
    },
    "ERR_ONTOLOGY_PROPOSAL_NOT_FOUND": {
        "fr": LocalizedErrorCopy(
            "Proposition introuvable",
            "Proposition '{proposal_id}' introuvable.",
        ),
        "en": LocalizedErrorCopy(
            "Proposal not found",
            "Proposal '{proposal_id}' not found.",
        ),
    },
    "ERR_ONTOLOGY_PROPOSAL_STATUS": {
        "fr": LocalizedErrorCopy(
            "Statut de proposition invalide",
            "La proposition '{proposal_key}' a déjà le statut '{status}'.",
        ),
        "en": LocalizedErrorCopy(
            "Invalid proposal status",
            "Proposal '{proposal_key}' already has status '{status}'.",
        ),
    },
    "ERR_ONTOLOGY_ACCESS_DENIED_SCOPE": {
        "fr": LocalizedErrorCopy(
            "Accès refusé sur ce périmètre ontologique",
            "Droits insuffisants pour écrire au niveau {level} sur '{scope_id}'.",
        ),
        "en": LocalizedErrorCopy(
            "Ontology scope access denied",
            "Insufficient permissions to write at level {level} on '{scope_id}'.",
        ),
    },
    "ERR_ONTOLOGY_L1_PROMOTION_FORBIDDEN": {
        "fr": LocalizedErrorCopy(
            "Promotion L1 interdite",
            "Un concept L1 ne peut pas être promu plus haut.",
        ),
        "en": LocalizedErrorCopy(
            "L1 promotion forbidden",
            "An L1 concept cannot be promoted higher.",
        ),
    },
    "ERR_ONTOLOGY_TARGET_TEAM_MISSING": {
        "fr": LocalizedErrorCopy(
            "Équipe cible introuvable",
            "Équipe cible introuvable pour L4 -> L3.",
        ),
        "en": LocalizedErrorCopy(
            "Target team not found",
            "Target team not found for L4 -> L3 promotion.",
        ),
    },
    "ERR_ONTOLOGY_PARENT_BU_MISSING": {
        "fr": LocalizedErrorCopy(
            "BU parente introuvable",
            "BU parente introuvable pour L3 -> L2.",
        ),
        "en": LocalizedErrorCopy(
            "Parent BU not found",
            "Parent business unit not found for L3 -> L2 promotion.",
        ),
    },
    "ERR_ONTOLOGY_PROMOTION_TARGET_FORBIDDEN": {
        "fr": LocalizedErrorCopy(
            "Cible de promotion non autorisée",
            (
                "Cible de promotion '{requested_scope_id}' non autorisée : "
                "la cible canonique imposée est '{canonical_scope_id}'."
            ),
        ),
        "en": LocalizedErrorCopy(
            "Unauthorized promotion target",
            (
                "Promotion target '{requested_scope_id}' is not authorized: "
                "the enforced canonical target is '{canonical_scope_id}'."
            ),
        ),
    },
    "ERR_ONTOLOGY_VALIDATION_DENIED": {
        "fr": LocalizedErrorCopy(
            "Validation de promotion refusée",
            "Validation refusée pour le palier {target_level} ({target_scope_id}).",
        ),
        "en": LocalizedErrorCopy(
            "Promotion review denied",
            "Review denied for level {target_level} ({target_scope_id}).",
        ),
    },
}

register_domain_error_catalog(ONTOLOGY_ERROR_CATALOG)

__all__ = ["ONTOLOGY_ERROR_CATALOG"]
