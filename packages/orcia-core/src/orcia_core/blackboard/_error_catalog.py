"""Localized RFC 9457 error catalog for Blackboard (`Story 3.2a`, `Story 27.7`)."""

from __future__ import annotations

from orcia_kernel.enums import SupportedLocale
from orcia_kernel.errors import LocalizedErrorCopy, register_domain_error_catalog

BLACKBOARD_ERROR_CATALOG: dict[str, dict[SupportedLocale, LocalizedErrorCopy]] = {
    "ERR_BLACKBOARD_APPEND_ONLY_VIOLATION": {
        "fr": LocalizedErrorCopy(
            "Violation du Blackboard en ajout seul",
            "Les snapshots engagés dans blackboard_snapshots sont immuables.",
        ),
        "en": LocalizedErrorCopy(
            "Append-only Blackboard violation",
            "Committed snapshots in blackboard_snapshots are strictly immutable.",
        ),
    },
    "ERR_BLACKBOARD_COMMIT_REQUIRED": {
        "fr": LocalizedErrorCopy(
            "Validation de snapshot requise",
            "Utilisez commit_step_snapshot() pour passer une étape à COMMITTED.",
        ),
        "en": LocalizedErrorCopy(
            "Snapshot commit required",
            "Use commit_step_snapshot() to transition a step to COMMITTED.",
        ),
    },
    "ERR_BLACKBOARD_RETRY_CEILING_EXHAUSTED": {
        "fr": LocalizedErrorCopy(
            "Plafond de tentatives atteint",
            "Plafond de boucles de rétroaction atteint ({max_retries}) sur l'étape "
            "'{step_key}' — escalade vers arbitrage humain.",
        ),
        "en": LocalizedErrorCopy(
            "Feedback retry ceiling reached",
            "Feedback loop ceiling reached ({max_retries}) on step '{step_key}' "
            "— escalating to human arbitration.",
        ),
    },
}

register_domain_error_catalog(BLACKBOARD_ERROR_CATALOG)

__all__ = ["BLACKBOARD_ERROR_CATALOG"]
