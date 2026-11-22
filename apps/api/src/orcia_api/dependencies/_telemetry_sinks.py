"""Telemetry sink & transactional Outbox resolvers for Composition Root (`Story 26.6b`)."""

from __future__ import annotations

from typing import Any

from orcia_core.orchestration.assistant_outbox_emitter import AssistantOutboxEmitter
from orcia_core.ports.finops_telemetry import AuditLedgerSinkPort


def resolve_audit_ledger_sink(request: Any | None) -> AuditLedgerSinkPort | None:
    """Safely resolve `AuditLedgerSinkPort` from `request.app.state` without side effects."""
    state = getattr(getattr(request, "app", None), "state", None)
    if state is None:
        return None
    svc = getattr(state, "audit_ledger_service", None)
    if isinstance(svc, AuditLedgerSinkPort):
        return svc
    engine = getattr(state, "db_engine", None)
    if engine is not None:
        from orcia_core.audit_finops import SqlAuditLedgerService

        return SqlAuditLedgerService(engine=engine)
    return None


def resolve_assistant_outbox_emitter(request: Any | None) -> AssistantOutboxEmitter | None:
    """Resolve `AssistantOutboxEmitter` backed by `SqlDomainEventsOutboxRepository`."""
    state = getattr(getattr(request, "app", None), "state", None)
    if state is None:
        return None
    cached = getattr(state, "assistant_outbox_emitter", None)
    if isinstance(cached, AssistantOutboxEmitter):
        return cached
    emitter = AssistantOutboxEmitter.from_uow_or_engine(
        uow=getattr(state, "dbos_uow", None),
        engine=getattr(state, "db_engine", None),
    )
    if emitter is not None:
        state.assistant_outbox_emitter = emitter
    return emitter


__all__ = [
    "resolve_assistant_outbox_emitter",
    "resolve_audit_ledger_sink",
]
