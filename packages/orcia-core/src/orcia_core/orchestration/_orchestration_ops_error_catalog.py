"""Localized RFC 9457 error detail catalog for orchestration operations (`Story 27.7`)."""

from __future__ import annotations

from orcia_kernel.enums import SupportedLocale
from orcia_kernel.errors import LocalizedErrorCopy, register_domain_error_catalog

ORCHESTRATION_OPS_ERROR_CATALOG: dict[str, dict[SupportedLocale, LocalizedErrorCopy]] = {
    "ERR_ROOT_BUDGET_EXCEEDED": {
        "fr": LocalizedErrorCopy(
            "Plafond budgétaire dépassé",
            "Plafond budgétaire root_run_id '{root_run_id}' dépassé: {spent} USD > {max_usd} USD.",
        ),
        "en": LocalizedErrorCopy(
            "Budget ceiling exceeded",
            "Budget ceiling for root_run_id '{root_run_id}' exceeded: {spent} USD > {max_usd} USD.",
        ),
    },
    "ERR_STEP_NOT_FOUND": {
        "fr": LocalizedErrorCopy("Étape introuvable", "Étape '{step_key}' introuvable."),
        "en": LocalizedErrorCopy("Step not found", "Step '{step_key}' not found."),
    },
    "ERR_STEP_EXECUTOR_NOT_FOUND": {
        "fr": LocalizedErrorCopy(
            "Exécuteur d'étape introuvable",
            "Aucun exécuteur d'étape enregistré dans orcia.step_executors "
            "pour step_type='{step_type}'.",
        ),
        "en": LocalizedErrorCopy(
            "Step executor not found",
            "No step executor registered in orcia.step_executors for step_type='{step_type}'.",
        ),
    },
    "ERR_ARBITRATION_NOT_FOUND": {
        "fr": LocalizedErrorCopy(
            "Demande d'arbitrage introuvable",
            "Demande d'arbitrage '{arbitration_id}' introuvable.",
        ),
        "en": LocalizedErrorCopy(
            "Arbitration request not found",
            "Arbitration request '{arbitration_id}' not found.",
        ),
    },
    "ERR_ARBITRATION_OPTION_MISSING": {
        "fr": LocalizedErrorCopy(
            "Option d'arbitrage absente",
            "Option '{option_key}' absente de options_matrix.",
        ),
        "en": LocalizedErrorCopy(
            "Arbitration option missing",
            "Option '{option_key}' missing from options_matrix.",
        ),
    },
    "ERR_HUMAN_ANCHOR_AGENT_FORBIDDEN": {
        "fr": LocalizedErrorCopy(
            "Ancre humaine interdite aux agents",
            "Toute écriture ou signature par une identité d'agent (author_type='AGENT') sur "
            "un champ human_authored_required: true est strictement interdite (AD-3, FR-4).",
        ),
        "en": LocalizedErrorCopy(
            "Agent write forbidden on human anchor",
            "Writing or signing by an agent identity (author_type='AGENT') on a "
            "human_authored_required: true field is strictly forbidden (AD-3, FR-4).",
        ),
    },
    "ERR_HUMAN_ANCHOR_TOO_SHORT": {
        "fr": LocalizedErrorCopy(
            "Ancre humaine trop courte",
            "Une ancre humaine obligatoire exige au moins {min_chars} caractères significatifs "
            "rédigés et signés par un humain (reçu: {char_len}).",
        ),
        "en": LocalizedErrorCopy(
            "Human anchor too short",
            "A mandatory human anchor requires at least {min_chars} meaningful characters "
            "authored and signed by a human (received: {char_len}).",
        ),
    },
    "ERR_HUMAN_ANCHOR_STEP_AGENT_FORBIDDEN": {
        "fr": LocalizedErrorCopy(
            "Ancre humaine requise sur l'étape",
            "L'étape '{step_key}' requiert une ancre humaine obligatoire "
            "(human_authored_required: true) et rejette toute écriture par un agent.",
        ),
        "en": LocalizedErrorCopy(
            "Step requires human anchor",
            "Step '{step_key}' requires a mandatory human anchor "
            "(human_authored_required: true) and rejects any agent write.",
        ),
    },
    "ERR_HUMAN_ANCHOR_MISSING_SIGNATURE": {
        "fr": LocalizedErrorCopy(
            "Signature d'ancre humaine absente",
            "Impossible de lancer l'agent sur l'étape '{step_key}' : aucune signature dans "
            "human_anchor_signatures (>= 30 caractères).",
        ),
        "en": LocalizedErrorCopy(
            "Human anchor signature missing",
            "Cannot start agent on step '{step_key}': no signature in "
            "human_anchor_signatures (>= 30 characters).",
        ),
    },
    "ERR_JIT_STEP_NOT_FOUND": {
        "fr": LocalizedErrorCopy(
            "Étape introuvable dans le processus",
            "Étape '{step_key}' introuvable dans '{workflow_uri}'.",
        ),
        "en": LocalizedErrorCopy(
            "Step not found in process",
            "Step '{step_key}' not found in '{workflow_uri}'.",
        ),
    },
    "ERR_JIT_UPSTREAM_SNAPSHOT_MISSING": {
        "fr": LocalizedErrorCopy(
            "Snapshot amont introuvable",
            "Snapshot amont requis introuvable pour '{canonical_uri}' lors de l'hydratation JIT "
            "de '{step_key}'.",
        ),
        "en": LocalizedErrorCopy(
            "Upstream snapshot missing",
            "Required upstream snapshot not found for '{canonical_uri}' during JIT hydration "
            "of '{step_key}'.",
        ),
    },
    "ERR_JIT_INPUT_REF_INVALID": {
        "fr": LocalizedErrorCopy(
            "Référence d'entrée JIT invalide",
            "Référence d'entrée JIT invalide '{ref_expr}' sur le run '{run_id}'.",
        ),
        "en": LocalizedErrorCopy(
            "Invalid JIT input reference",
            "Invalid JIT input reference '{ref_expr}' on run '{run_id}'.",
        ),
    },
    "ERR_RUN_NOT_FOUND": {
        "fr": LocalizedErrorCopy("Exécution introuvable", "Run '{run_id}' introuvable."),
        "en": LocalizedErrorCopy("Run not found", "Run '{run_id}' not found."),
    },
    "ERR_CONTROL_CENTER_SCOPE_NOT_FOUND": {
        "fr": LocalizedErrorCopy("Périmètre introuvable", "Périmètre '{scope_id}' introuvable."),
        "en": LocalizedErrorCopy("Scope not found", "Scope '{scope_id}' not found."),
    },
    "ERR_CONTROL_CENTER_STEP_LOCKED": {
        "fr": LocalizedErrorCopy(
            "Étape verrouillée par un pair",
            "Mutation refusée: l'étape '{step_id}' du Run '{run_id}' "
            "est verrouillée par '{holder}'.",
        ),
        "en": LocalizedErrorCopy(
            "Step locked by peer",
            "Mutation denied: step '{step_id}' of Run '{run_id}' is locked by '{holder}'.",
        ),
    },
    "ERR_NOTIFICATION_NOT_FOUND": {
        "fr": LocalizedErrorCopy(
            "Notification introuvable",
            "Notification '{task_id}' introuvable.",
        ),
        "en": LocalizedErrorCopy(
            "Notification not found",
            "Notification '{task_id}' not found.",
        ),
    },
    "ERR_CLAIM_RELEASE_FORBIDDEN": {
        "fr": LocalizedErrorCopy(
            "Relâchement de verrou refusé",
            "Impossible de relâcher le verrou sur '{step_id}': détenu par '{holder}' "
            "et non expiré (< 15 min).",
        ),
        "en": LocalizedErrorCopy(
            "Lock release denied",
            "Cannot release lock on '{step_id}': held by '{holder}' and not expired (< 15 min).",
        ),
    },
    "ERR_STEP_LOCKED_BY_PEER": {
        "fr": LocalizedErrorCopy(
            "Étape verrouillée par un pair",
            "Étape '{step_id}' verrouillée par '{holder}' (lock Redis '{lock_key}').",
        ),
        "en": LocalizedErrorCopy(
            "Step locked by peer",
            "Step '{step_id}' locked by '{holder}' (Redis lock '{lock_key}').",
        ),
    },
    "ERR_TTL_MUST_BE_POSITIVE": {
        "fr": LocalizedErrorCopy(
            "TTL invalide",
            "ttl_seconds doit être strictement positif.",
        ),
        "en": LocalizedErrorCopy(
            "Invalid TTL",
            "ttl_seconds must be strictly positive.",
        ),
    },
    "ERR_NOTIFICATION_ALREADY_CLAIMED": {
        "fr": LocalizedErrorCopy(
            "Notification déjà prise en charge",
            "La notification '{notif_id}' (step '{step_id}') est déjà prise en charge "
            "par '{holder}' jusqu'à {expires_at}.",
        ),
        "en": LocalizedErrorCopy(
            "Notification already claimed",
            "Notification '{notif_id}' (step '{step_id}') is already claimed by '{holder}' "
            "until {expires_at}.",
        ),
    },
}

register_domain_error_catalog(ORCHESTRATION_OPS_ERROR_CATALOG)

__all__ = ["ORCHESTRATION_OPS_ERROR_CATALOG"]
