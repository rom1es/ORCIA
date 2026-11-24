"""Localized RFC 9457 error detail catalog for orchestration runtime (`Story 27.7`)."""

from __future__ import annotations

from orcia_kernel.enums import SupportedLocale
from orcia_kernel.errors import LocalizedErrorCopy, register_domain_error_catalog

ORCHESTRATION_RUNTIME_ERROR_CATALOG: dict[str, dict[SupportedLocale, LocalizedErrorCopy]] = {
    "ERR_AUTONOMOUS_RUN_NOT_FOUND": {
        "fr": LocalizedErrorCopy("Exécution introuvable", "Exécution introuvable : {run_id}"),
        "en": LocalizedErrorCopy("Execution not found", "Execution not found: {run_id}"),
    },
    "ERR_REPLAY_STEP_NOT_SUB_WORKFLOW": {
        "fr": LocalizedErrorCopy(
            "Étape non sous-workflow",
            "L'étape '{step_key}' n'est pas un SUB_WORKFLOW; impossible de rejouer "
            "le sous-step '{sub_step}'.",
        ),
        "en": LocalizedErrorCopy(
            "Step is not a sub-workflow",
            "Step '{step_key}' is not a SUB_WORKFLOW; cannot replay sub-step '{sub_step}'.",
        ),
    },
    "ERR_CHALLENGE_REASON_TOO_SHORT": {
        "fr": LocalizedErrorCopy(
            "Justification du challenge trop courte",
            "La justification du Challenge Amont doit comporter au moins 10 caractères.",
        ),
        "en": LocalizedErrorCopy(
            "Challenge reason too short",
            "Upstream Challenge justification must contain at least 10 characters.",
        ),
    },
    "ERR_CHALLENGE_UPSTREAM_NOT_FOUND": {
        "fr": LocalizedErrorCopy(
            "Étape amont introuvable", "Étape amont '{step_key}' introuvable."
        ),
        "en": LocalizedErrorCopy(
            "Upstream step not found", "Upstream step '{step_key}' not found."
        ),
    },
    "ERR_CHALLENGE_CHALLENGER_NOT_FOUND": {
        "fr": LocalizedErrorCopy(
            "Étape émettrice introuvable",
            "Étape émettrice '{step_key}' introuvable.",
        ),
        "en": LocalizedErrorCopy(
            "Challenger step not found",
            "Challenger step '{step_key}' not found.",
        ),
    },
    "ERR_CHALLENGE_NOT_UPSTREAM": {
        "fr": LocalizedErrorCopy(
            "Cible non située en amont",
            "L'étape cible '{target}' (index {target_idx}) doit être en amont "
            "de l'étape '{challenger}' (index {challenger_idx}).",
        ),
        "en": LocalizedErrorCopy(
            "Target step not upstream",
            "Target step '{target}' (index {target_idx}) must precede "
            "step '{challenger}' (index {challenger_idx}).",
        ),
    },
    "ERR_REPLAY_STEP_NOT_FOUND": {
        "fr": LocalizedErrorCopy(
            "Étape introuvable pour le Replay",
            "Étape '{step_key}' introuvable pour le Replay.",
        ),
        "en": LocalizedErrorCopy(
            "Step not found for replay",
            "Step '{step_key}' not found for replay.",
        ),
    },
    "ERR_WAIVER_SIGNER_NOT_FOUND": {
        "fr": LocalizedErrorCopy(
            "Signataire introuvable",
            "Aucun compte utilisateur valide trouvé pour signer la dérogation.",
        ),
        "en": LocalizedErrorCopy(
            "Signer account not found",
            "No valid user account found to sign the waiver.",
        ),
    },
    "ERR_THREAD_TURN_LOCK_HELD": {
        "fr": LocalizedErrorCopy(
            "Verrou de tour Redis actif",
            "Verrou de tour Redis actif sur {key} (détenu par '{holder}').",
        ),
        "en": LocalizedErrorCopy(
            "Redis thread turn lock held",
            "Redis turn lock active on {key} (held by '{holder}').",
        ),
    },
    "ERR_RESOURCE_LEASE_URIS_REQUIRED": {
        "fr": LocalizedErrorCopy(
            "URI de ressource requise",
            "Au moins une URI de ressource est requise pour acquérir un bail.",
        ),
        "en": LocalizedErrorCopy(
            "Resource URI required",
            "At least one resource URI is required to acquire a lease.",
        ),
    },
    "ERR_RESOURCE_LEASE_CYCLIC_WAIT": {
        "fr": LocalizedErrorCopy(
            "Attente cyclique sur bail de ressource",
            "Attente cyclique parent-enfant détectée sur '{uri}': le sous-workflow enfant "
            "'{holder_run_id}' attend le bail détenu par son ancêtre '{existing_holder}'.",
        ),
        "en": LocalizedErrorCopy(
            "Cyclic resource lease wait",
            "Parent-child cyclic wait detected on '{uri}': child sub-workflow "
            "'{holder_run_id}' is waiting for lease held by ancestor '{existing_holder}'.",
        ),
    },
    "ERR_RESOURCE_LEASE_HELD": {
        "fr": LocalizedErrorCopy(
            "Ressource déjà verrouillée",
            "Ressource '{uri}' déjà verrouillée par le Run '{holder}' "
            "(fencing_token={token}, expire à {expires_at}).",
        ),
        "en": LocalizedErrorCopy(
            "Resource lease already held",
            "Resource '{uri}' already locked by Run '{holder}' "
            "(fencing_token={token}, expires at {expires_at}).",
        ),
    },
    "ERR_STALE_FENCING_TOKEN": {
        "fr": LocalizedErrorCopy(
            "Jeton de fencing périmé",
            "Jeton de fencing périmé pour '{uri}': jeton reçu={received} < jeton actif={highest}.",
        ),
        "en": LocalizedErrorCopy(
            "Stale fencing token",
            "Stale fencing token for '{uri}': received={received} < active={highest}.",
        ),
    },
    "ERR_RUN_LOCK_SUB_WORKFLOW_CYCLE": {
        "fr": LocalizedErrorCopy(
            "Cycle SUB_WORKFLOW détecté",
            "Cycle d'appels SUB_WORKFLOW détecté: {chain}.",
        ),
        "en": LocalizedErrorCopy(
            "SUB_WORKFLOW cycle detected",
            "SUB_WORKFLOW call cycle detected: {chain}.",
        ),
    },
    "ERR_RUN_LOCK_SUB_WORKFLOW_DEPTH": {
        "fr": LocalizedErrorCopy(
            "Profondeur SUB_WORKFLOW dépassée",
            "Profondeur SUB_WORKFLOW {depth} > {max_depth} pour '{uri}'.",
        ),
        "en": LocalizedErrorCopy(
            "SUB_WORKFLOW max depth exceeded",
            "SUB_WORKFLOW depth {depth} > {max_depth} for '{uri}'.",
        ),
    },
    "ERR_RUN_LOCK_SUB_WORKFLOW_MISSING": {
        "fr": LocalizedErrorCopy(
            "Sous-workflow cible introuvable",
            "Sous-workflow cible '{uri}' introuvable.",
        ),
        "en": LocalizedErrorCopy(
            "Target sub-workflow not found",
            "Target sub-workflow '{uri}' not found.",
        ),
    },
    "ERR_WORKFLOW_NOT_FOUND": {
        "fr": LocalizedErrorCopy("Workflow introuvable", "Workflow '{uri}' introuvable."),
        "en": LocalizedErrorCopy("Workflow not found", "Workflow '{uri}' not found."),
    },
    "ERR_PARENT_RUN_NOT_FOUND": {
        "fr": LocalizedErrorCopy(
            "Run parent introuvable", "Run parent '{parent_run_id}' introuvable."
        ),
        "en": LocalizedErrorCopy("Parent run not found", "Parent run '{parent_run_id}' not found."),
    },
    "ERR_WORKFLOW_RUN_NOT_FOUND": {
        "fr": LocalizedErrorCopy(
            "Workflow Run introuvable", "Workflow Run '{run_id}' introuvable."
        ),
        "en": LocalizedErrorCopy("Workflow Run not found", "Workflow Run '{run_id}' not found."),
    },
    "ERR_ARTIFACT_TEMPLATE_NOT_FOUND": {
        "fr": LocalizedErrorCopy(
            "Gabarit d'artefact introuvable",
            "Gabarit d'artefact '{template_key}' introuvable.",
        ),
        "en": LocalizedErrorCopy(
            "Artifact template not found",
            "Artifact template '{template_key}' not found.",
        ),
    },
}

register_domain_error_catalog(ORCHESTRATION_RUNTIME_ERROR_CATALOG)

__all__ = ["ORCHESTRATION_RUNTIME_ERROR_CATALOG"]
