"""Audit & FinOps localized RFC 9457 error catalog (`AD-19`, `Story 27.7`)."""

from __future__ import annotations

from orcia_kernel.enums import SupportedLocale
from orcia_kernel.errors import LocalizedErrorCopy

AUDIT_FINOPS_ERROR_CATALOG: dict[str, dict[SupportedLocale, LocalizedErrorCopy]] = {
    "ERR_AUDIT_LEDGER_IMMUTABLE": {
        "fr": LocalizedErrorCopy(
            "Journal d'audit immuable (ajout seul)",
            "Toute modification ou suppression dans audit_ledger est interdite.",
        ),
        "en": LocalizedErrorCopy(
            "Immutable audit ledger (append-only)",
            "Updating or deleting rows in audit_ledger is strictly forbidden.",
        ),
    },
    "ERR_AUDIT_RUN_NOT_FOUND": {
        "fr": LocalizedErrorCopy(
            "Exécution d'audit introuvable",
            (
                "Aucun enregistrement d'audit ou dossier de provenance n'a été trouvé "
                "pour cet identifiant d'exécution."
            ),
        ),
        "en": LocalizedErrorCopy(
            "Audit run not found",
            "No audit record or provenance report was found for this run identifier.",
        ),
    },
    "ERR_AUDIT_RUN_NOT_FOUND_DETAIL": {
        "fr": LocalizedErrorCopy(
            "Exécution d'audit introuvable",
            "Aucun enregistrement d'audit trouvé pour le run_id '{run_id}'.",
        ),
        "en": LocalizedErrorCopy(
            "Audit run not found",
            "No audit record found for run_id '{run_id}'.",
        ),
    },
    "ERR_COGNITIVE_REC_NOT_FOUND_DETAIL": {
        "fr": LocalizedErrorCopy(
            "Ressource introuvable",
            "Recommandation de politique de validation '{recommendation_id}' introuvable.",
        ),
        "en": LocalizedErrorCopy(
            "Resource not found",
            "Gate policy recommendation '{recommendation_id}' not found.",
        ),
    },
}

__all__ = ["AUDIT_FINOPS_ERROR_CATALOG"]
