"""Localized RFC 9457 error catalog for the declarative packs domain (`Story 31.1`, `31.2`)."""

from __future__ import annotations

from orcia_kernel.enums import SupportedLocale
from orcia_kernel.errors import LocalizedErrorCopy, register_domain_error_catalog

PACKS_ERROR_CATALOG: dict[str, dict[SupportedLocale, LocalizedErrorCopy]] = {
    "ERR_PACK_EXECUTABLE_HOOK_FORBIDDEN": {
        "fr": LocalizedErrorCopy(
            "Script ou hook exécutable interdit dans le pack",
            "Les dossiers scripts/ ou hooks/, les clés de hooks YAML et les fichiers "
            "exécutables (.py, .sh, .js, .ts, .wasm) sont strictement interdits dans un pack.",
        ),
        "en": LocalizedErrorCopy(
            "Executable hook or script forbidden in pack",
            "Directories scripts/ or hooks/, YAML hook keys, and executable suffixes "
            "(.py, .sh, .js, .ts, .wasm) are strictly forbidden inside a pack.",
        ),
    },
    "ERR_PACK_INVALID_ARCHIVE": {
        "fr": LocalizedErrorCopy(
            "Archive ou manifeste de pack invalide",
            "Le pack fourni est corrompu, mal formé, hors limites de sécurité ou viole "
            "les invariants déclaratifs/Starlark.",
        ),
        "en": LocalizedErrorCopy(
            "Invalid pack archive or manifest",
            "The supplied pack is corrupted, malformed, exceeds archive safety bounds, or "
            "violates declarative/Starlark invariants.",
        ),
    },
    "ERR_PACK_VERSION_CONFLICT": {
        "fr": LocalizedErrorCopy(
            "Conflit de version SemVer du pack",
            "Une version publiée identique existe déjà avec une empreinte SHA-256 différente.",
        ),
        "en": LocalizedErrorCopy(
            "Pack SemVer version conflict",
            "An identical published pack version already exists with a different SHA-256 digest.",
        ),
    },
    "ERR_PACK_SLOT_UNBOUND": {
        "fr": LocalizedErrorCopy(
            "Slot de connecteur requis non lié",
            "Un ou plusieurs slots de connecteurs requis par le pack ne sont liés à aucune "
            "source de données ni connecteur actif dans cet Espace.",
        ),
        "en": LocalizedErrorCopy(
            "Required pack connector slot unbound",
            "One or more required pack connector slots are not bound to an active workspace "
            "datasource or enterprise connector.",
        ),
    },
    "ERR_PACK_CLOSURE_INCOMPLETE": {
        "fr": LocalizedErrorCopy(
            "Clôture transitive du pack incomplète",
            "Le pack référence des agents, compétences, workflows ou politiques manquants ou "
            "encore en état DRAFT.",
        ),
        "en": LocalizedErrorCopy(
            "Incomplete pack dependency closure",
            "The pack references missing or non-ACTIVE agents, skills, workflows, or policies.",
        ),
    },
    "ERR_PACK_PII_OR_INFRA_LEAK": {
        "fr": LocalizedErrorCopy(
            "Fuite potentielle de PII, secret ou infrastructure détectée",
            "L'export du pack a été bloqué car un identifiant interne, hôte privé, secret ou "
            "e-mail non autorisé subsiste dans les fichiers rendus.",
        ),
        "en": LocalizedErrorCopy(
            "Potential PII, secret, or infrastructure leak detected",
            "Pack export was blocked because an internal tenant identifier, private host, secret, "
            "or unauthorized email literal remains in the rendered archive.",
        ),
    },
    "ERR_RESOURCE_PINNED_BY_ACTIVE_RUNS": {
        "fr": LocalizedErrorCopy(
            "Ressource épinglée par des Workflow Runs actifs",
            "Impossible de supprimer ou désactiver immédiatement ce pack car il est épinglé "
            "dans le run-lock.json de runs actifs (AD-21).",
        ),
        "en": LocalizedErrorCopy(
            "Resource pinned by active Workflow Runs",
            "Cannot immediately delete or deactivate this pack because it is pinned in the "
            "run-lock.json of active runs (AD-21).",
        ),
    },
    "ERR_ENTITY_REFERENCED_BY_PACK_DRAFT": {
        "fr": LocalizedErrorCopy(
            "Entité référencée par un brouillon de pack",
            "Cette ressource est référencée par un ou plusieurs brouillons de packs. Détachez "
            "d'abord les liens du brouillon ou confirmez le détachement explicite.",
        ),
        "en": LocalizedErrorCopy(
            "Entity referenced by a pack draft",
            "This resource is referenced by one or more pack drafts. Unlink the draft "
            "membership first or confirm explicit unlink.",
        ),
    },
    "ERR_PACK_BUNDLE_NOT_FOUND": {
        "fr": LocalizedErrorCopy(
            "Pack déclaratif introuvable",
            "Le pack demandé est introuvable dans le registre PostgreSQL 18.",
        ),
        "en": LocalizedErrorCopy(
            "Declarative pack not found",
            "The requested pack bundle was not found in the PostgreSQL 18 registry.",
        ),
    },
    "ERR_PACK_SYSTEM_DELETE_FORBIDDEN": {
        "fr": LocalizedErrorCopy(
            "Suppression d'un pack système interdite",
            "Les packs systèmes intégrés (SYSTEM) ne peuvent pas être supprimés via l'API.",
        ),
        "en": LocalizedErrorCopy(
            "System pack deletion forbidden",
            "Built-in SYSTEM pack bundles cannot be deleted via the API.",
        ),
    },
    "ERR_PACK_SCOPE_ESCALATION_FORBIDDEN": {
        "fr": LocalizedErrorCopy(
            "Portée ou type de pack non autorisé à l'import",
            "L'import d'un pack de type SYSTEM ou de portée GLOBAL est interdit via l'API.",
        ),
        "en": LocalizedErrorCopy(
            "Pack scope or kind escalation forbidden",
            "Importing a SYSTEM pack bundle or GLOBAL scope pack via user API is forbidden.",
        ),
    },
}

register_domain_error_catalog(PACKS_ERROR_CATALOG)

__all__ = ["PACKS_ERROR_CATALOG"]
