"""Composition Root `Depends` providers for Story 7.4 (Autonomous Supervision & Post-Hoc Audit)."""

from __future__ import annotations

import os

from fastapi import Request

from orcia_api.dependencies.orchestration_and_settings import (
    get_audit_ledger_service,
    get_notification_service,
)
from orcia_api.dependencies.portal_and_assistant import get_contextual_help_service
from orcia_core.audit_finops.post_hoc_audit import PostHocAuditService
from orcia_core.orchestration.autonomous_supervision import AutonomousSupervisionService


def get_post_hoc_audit_service(request: Request) -> PostHocAuditService:
    """FastAPI `Depends` provider returning `PostHocAuditService` (`Story 7.4`)."""
    engine = getattr(request.app.state, "db_engine", None)
    use_pg = engine is not None and os.environ.get("ORCIA_DISABLE_PG_BOOTSTRAP_SYNC") != "1"
    svc: PostHocAuditService | None = getattr(request.app.state, "post_hoc_audit_service", None)
    if svc is None:
        audit_sink = get_audit_ledger_service(request)
        svc = PostHocAuditService(engine=engine if use_pg else None, audit_sink=audit_sink)
        request.app.state.post_hoc_audit_service = svc
    elif use_pg and getattr(svc, "_engine", None) is None:
        svc._engine = engine
    return svc


def get_autonomous_supervision_service(request: Request) -> AutonomousSupervisionService:
    """FastAPI `Depends` provider returning `AutonomousSupervisionService` (`Story 7.4`)."""
    engine = getattr(request.app.state, "db_engine", None)
    use_pg = engine is not None and os.environ.get("ORCIA_DISABLE_PG_BOOTSTRAP_SYNC") != "1"
    svc: AutonomousSupervisionService | None = getattr(
        request.app.state, "autonomous_supervision_service", None
    )
    if svc is None:
        post_hoc = get_post_hoc_audit_service(request)
        help_svc = get_contextual_help_service(request)
        notif_svc = get_notification_service(request)
        audit_sink = get_audit_ledger_service(request)
        redis_client = getattr(request.app.state, "redis_client", None)
        svc = AutonomousSupervisionService(
            engine=engine if use_pg else None,
            redis_client=redis_client,
            post_hoc_service=post_hoc,
            help_service=help_svc,
            sse_broker=notif_svc.sse_broker,
            audit_sink=audit_sink,
        )
        request.app.state.autonomous_supervision_service = svc
    else:
        if use_pg and getattr(svc, "_engine", None) is None:
            svc._engine = engine
        if getattr(svc, "_redis", None) is None:
            svc._redis = getattr(request.app.state, "redis_client", None)
    return svc
