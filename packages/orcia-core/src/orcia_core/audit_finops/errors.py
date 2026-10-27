"""Audit & FinOps domain errors (`AD-19`, `Story 3.2a`)."""

from __future__ import annotations

from orcia_kernel.errors import (
    LocalizedErrorCopy,
    OrciaDomainError,
    ResourceNotFoundError,
    ValidationDomainError,
    register_domain_error_catalog,
)

register_domain_error_catalog(
    {
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
    }
)


class AuditLedgerImmutableViolationError(OrciaDomainError):
    error_code = "ERR_AUDIT_LEDGER_IMMUTABLE"
    http_status, type_slug = 409, "audit-ledger-immutable"


__all__ = [
    "AuditLedgerImmutableViolationError",
    "OrciaDomainError",
    "ResourceNotFoundError",
    "ValidationDomainError",
]
