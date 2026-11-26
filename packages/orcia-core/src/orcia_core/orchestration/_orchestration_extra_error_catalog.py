"""Localized RFC 9457 error catalog extensions for orchestration (`Story 27.7`)."""

from __future__ import annotations

from orcia_kernel.enums import SupportedLocale
from orcia_kernel.errors import LocalizedErrorCopy, register_domain_error_catalog

ORCHESTRATION_EXTRA_ERROR_CATALOG: dict[str, dict[SupportedLocale, LocalizedErrorCopy]] = {
    "ERR_PACK_SKILL_AGENT_IMMUTABLE": {
        "fr": LocalizedErrorCopy(
            "Ressource issue d'un Pack Métier immuable",
            "Les agents et compétences issus d'un Pack Métier ne peuvent pas être supprimés ; "
            "vous pouvez les désactiver sur l'espace ou les dupliquer pour les personnaliser.",
        ),
        "en": LocalizedErrorCopy(
            "Business Pack resource immutable",
            "Agents and skills provided by a Business Pack cannot be deleted; "
            "you can disable them on the space or duplicate them to customize.",
        ),
    },
    "ERR_SKILL_NAME_REQUIRED": {
        "fr": LocalizedErrorCopy(
            "Nom de compétence requis",
            "Le nom de la compétence est obligatoire.",
        ),
        "en": LocalizedErrorCopy(
            "Skill name required",
            "Skill name is required.",
        ),
    },
    "ERR_SKILL_OBJECTIVE_REQUIRED": {
        "fr": LocalizedErrorCopy(
            "Objectif métier requis",
            "L'objectif métier de la compétence est obligatoire.",
        ),
        "en": LocalizedErrorCopy(
            "Skill business objective required",
            "Skill business objective is required.",
        ),
    },
    "ERR_SKILL_INSTRUCTIONS_REQUIRED": {
        "fr": LocalizedErrorCopy(
            "Instructions de compétence requises",
            "Les instructions d'exécution de la compétence sont obligatoires.",
        ),
        "en": LocalizedErrorCopy(
            "Skill instructions required",
            "Skill execution instructions are required.",
        ),
    },
    "ERR_SKILL_TEST_INPUT_REQUIRED": {
        "fr": LocalizedErrorCopy(
            "Entrée de test requise",
            "Veuillez saisir une entrée de test pour exécuter la compétence.",
        ),
        "en": LocalizedErrorCopy(
            "Test input required",
            "Please enter a test input to run the skill.",
        ),
    },
    "ERR_AGENT_NAME_REQUIRED": {
        "fr": LocalizedErrorCopy(
            "Nom d'agent requis",
            "Le nom de l'agent est obligatoire.",
        ),
        "en": LocalizedErrorCopy(
            "Agent name required",
            "Agent name is required.",
        ),
    },
    "ERR_AGENT_ROLE_REQUIRED": {
        "fr": LocalizedErrorCopy(
            "Rôle et mission d'agent requis",
            "Le rôle et la mission de l'agent sont obligatoires.",
        ),
        "en": LocalizedErrorCopy(
            "Agent role and mission required",
            "Agent role and mission are required.",
        ),
    },
    "ERR_AGENT_INSTRUCTIONS_REQUIRED": {
        "fr": LocalizedErrorCopy(
            "Instructions d'agent requises",
            "Les instructions de l'agent sont obligatoires.",
        ),
        "en": LocalizedErrorCopy(
            "Agent instructions required",
            "Agent instructions are required.",
        ),
    },
    "ERR_AGENT_TEST_PROMPT_REQUIRED": {
        "fr": LocalizedErrorCopy(
            "Demande de test requise",
            "Veuillez saisir une demande pour tester l'agent.",
        ),
        "en": LocalizedErrorCopy(
            "Test prompt required",
            "Please enter a prompt to test the agent.",
        ),
    },
    "ERR_FOLDER_SHARE_FORBIDDEN": {
        "fr": LocalizedErrorCopy(
            "Partage de dossier non autorisé",
            "Seul le propriétaire du dossier ou un responsable d'équipe peut modifier son partage.",
        ),
        "en": LocalizedErrorCopy(
            "Folder sharing forbidden",
            "Only the folder owner or a team lead can modify its sharing settings.",
        ),
    },
    "ERR_FOLDER_CONFINEMENT_VIOLATION": {
        "fr": LocalizedErrorCopy(
            "Violation du confinement à l'Espace",
            "Confinement à l'Espace ({workspace_id}) : impossible de partager un dossier avec "
            "l'utilisateur externe '{grantee_user_id}' (AD-21).",
        ),
        "en": LocalizedErrorCopy(
            "Space confinement violation",
            "Space confinement ({workspace_id}): cannot share a folder with external user "
            "'{grantee_user_id}' (AD-21).",
        ),
    },
    "ERR_FOLDER_PRIVATE": {
        "fr": LocalizedErrorCopy(
            "Dossier privé",
            "Ce dossier est privé (🔒 Privé).",
        ),
        "en": LocalizedErrorCopy(
            "Private folder",
            "This folder is private (🔒 Private).",
        ),
    },
    "ERR_FOLDER_ACCESS_DENIED": {
        "fr": LocalizedErrorCopy(
            "Accès dossier refusé",
            "Vous n'avez pas accès à ce dossier partagé.",
        ),
        "en": LocalizedErrorCopy(
            "Folder access denied",
            "You do not have access to this shared folder.",
        ),
    },
    "ERR_FOLDER_READ_ONLY": {
        "fr": LocalizedErrorCopy(
            "Dossier en lecture seule",
            "Accès en 👁️ Lecture seule sur ce dossier partagé : "
            "seul un ✍️ Co-contributeur peut interroger l'assistant.",
        ),
        "en": LocalizedErrorCopy(
            "Folder read-only access",
            "👁️ Read-only access on this shared folder: "
            "only a ✍️ Co-contributor can query the assistant.",
        ),
    },
    "ERR_FOLDER_EMPTY_TITLE": {
        "fr": LocalizedErrorCopy(
            "Titre de dossier vide",
            "Le titre du dossier thématique ne peut pas être vide.",
        ),
        "en": LocalizedErrorCopy(
            "Empty folder title",
            "The thematic folder title cannot be empty.",
        ),
    },
    "ERR_PACK_SLUG_RESERVED_OR_INVALID": {
        "fr": LocalizedErrorCopy(
            "Slug de Pack Métier invalide ou réservé",
            "Le slug de pack '{pack_slug}' est invalide ou réservé au noyau (`AD-20`).",
        ),
        "en": LocalizedErrorCopy(
            "Invalid or reserved Business Pack slug",
            "Pack slug '{pack_slug}' is invalid or reserved for core modules (`AD-20`).",
        ),
    },
    "ERR_PACK_DNA_CHAIN_EMPTY": {
        "fr": LocalizedErrorCopy(
            "Chaîne ADN causale requise",
            "Processus 1 exige au moins une chaîne causale ADN (DIRECTIVE ➔ NORME ➔ MÉCANISME).",
        ),
        "en": LocalizedErrorCopy(
            "Causal DNA chain required",
            "Process 1 requires at least one causal DNA chain (DIRECTIVE ➔ NORM ➔ MECHANISM).",
        ),
    },
    "ERR_STARLARK_RULE_CERTIFICATION_FAILED": {
        "fr": LocalizedErrorCopy(
            "Certification Starlark Palier 1b échouée",
            "La règle Starlark '{mechanism_code}' ({rule_id}) "
            "a échoué à la certification Palier 1b.",
        ),
        "en": LocalizedErrorCopy(
            "Tier 1b Starlark rule certification failed",
            "Starlark rule '{mechanism_code}' ({rule_id}) failed Tier 1b certification.",
        ),
    },
    "ERR_DRAFT_AGENT_LIFECYCLE_BLOCKED": {
        "fr": LocalizedErrorCopy(
            "Action refusée pour un agent en brouillon (DRAFT)",
            "Cet agent est actuellement en brouillon (DRAFT) et doit être activé ou validé au "
            "Banc de Test avant d'être utilisé ou exposé.",
        ),
        "en": LocalizedErrorCopy(
            "Action blocked for a DRAFT agent",
            "This agent is currently in DRAFT status and must be activated or verified in the "
            "Test Bench before use or external exposure.",
        ),
    },
    "ERR_DRAFT_AGENT_CANNOT_EXPOSE_MCP": {
        "fr": LocalizedErrorCopy(
            "Exposition externe interdite sur un agent en brouillon (DRAFT)",
            "L'agent « {agent_name} » est en brouillon (DRAFT). Validez-le au Banc de Test ou "
            "activez-le avant de l'exposer en outil externe MCP.",
        ),
        "en": LocalizedErrorCopy(
            "External MCP exposure forbidden for DRAFT agent",
            "Agent '{agent_name}' is in DRAFT status. Pass the Test Bench or activate it "
            "before exposing it as an external MCP tool.",
        ),
    },
    "ERR_DRAFT_AGENT_INVOCATION_BLOCKED": {
        "fr": LocalizedErrorCopy(
            "Invocation bloquée : agent en brouillon (DRAFT)",
            "L'agent « {agent_name} » ({agent_handle}) est en brouillon (DRAFT) et ne peut "
            "pas encore être invoqué dans Mon Assistant ou dans un Processus.",
        ),
        "en": LocalizedErrorCopy(
            "Invocation blocked: DRAFT agent",
            "Agent '{agent_name}' ({agent_handle}) is in DRAFT status and cannot be invoked "
            "in My Assistant or Processes yet.",
        ),
    },
    "ERR_AGENT_INCOMPLETE_FOR_ACTIVATION": {
        "fr": LocalizedErrorCopy(
            "Agent incomplet pour l'activation",
            "L'agent « {agent_name} » ne remplit pas encore les critères d'activation "
            "(nom, mission, instructions requises et absence d'échec au Banc de Test).",
        ),
        "en": LocalizedErrorCopy(
            "Agent incomplete for activation",
            "Agent '{agent_name}' does not meet activation requirements yet "
            "(name, mission, instructions required, and no failed Test Bench status).",
        ),
    },
}

register_domain_error_catalog(ORCHESTRATION_EXTRA_ERROR_CATALOG)

__all__ = ["ORCHESTRATION_EXTRA_ERROR_CATALOG"]
