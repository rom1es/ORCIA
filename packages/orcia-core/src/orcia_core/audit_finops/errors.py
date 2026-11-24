"""Audit & FinOps domain errors (`AD-19`, `Story 3.2a`)."""

from __future__ import annotations

from orcia_core.audit_finops._error_catalog import AUDIT_FINOPS_ERROR_CATALOG
from orcia_kernel.errors import (
    OrciaDomainError,
    ResourceNotFoundError,
    ValidationDomainError,
    register_domain_error_catalog,
)

register_domain_error_catalog(AUDIT_FINOPS_ERROR_CATALOG)


class AuditLedgerImmutableViolationError(OrciaDomainError):
    error_code = "ERR_AUDIT_LEDGER_IMMUTABLE"
    http_status, type_slug = 409, "audit-ledger-immutable"


class AuditRunNotFoundError(ResourceNotFoundError):
    error_code = "ERR_AUDIT_RUN_NOT_FOUND"
    http_status, type_slug = 404, "audit-run-not-found"


__all__ = [
    "AUDIT_FINOPS_ERROR_CATALOG",
    "AuditLedgerImmutableViolationError",
    "AuditRunNotFoundError",
    "OrciaDomainError",
    "ResourceNotFoundError",
    "ValidationDomainError",
]
