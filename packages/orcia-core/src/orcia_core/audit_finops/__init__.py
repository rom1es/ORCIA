"""Bounded Context 8: Audit & FinOps (Append-Only Ledger, Token Cost Tracking & Circuit Breaker)."""

from __future__ import annotations

from orcia_core.audit_finops._internal.sql_audit_ledger import SqlAuditLedgerService
from orcia_core.audit_finops.errors import (
    AuditLedgerImmutableViolationError,
    AuditRunNotFoundError,
)
from orcia_core.audit_finops.models import (
    AuditLedgerEntry,
    AuditLedgerFilterParams,
    AuditProvenanceExport,
    AuditProvenanceSummary,
    AuditTimeWindow,
)
from orcia_core.audit_finops.outbox_subscriber import (
    AUDITABLE_EVENT_TYPES,
    AuditLedgerOutboxSubscriber,
    map_domain_event_to_ledger_entry,
)
from orcia_core.audit_finops.provenance_exporter import ProvenanceExporterService

DOMAIN_NAME: str = "audit_finops"

__all__ = [
    "AUDITABLE_EVENT_TYPES",
    "AuditLedgerEntry",
    "AuditLedgerFilterParams",
    "AuditLedgerImmutableViolationError",
    "AuditLedgerOutboxSubscriber",
    "AuditProvenanceExport",
    "AuditProvenanceSummary",
    "AuditRunNotFoundError",
    "AuditTimeWindow",
    "DOMAIN_NAME",
    "ProvenanceExporterService",
    "SqlAuditLedgerService",
    "map_domain_event_to_ledger_entry",
]
