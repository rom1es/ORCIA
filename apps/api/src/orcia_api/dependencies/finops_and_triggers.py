"""FinOps, Audit Ledger, Autonomy Contracts & Trigger Dispatcher providers (`AD-19`)."""

from __future__ import annotations

from typing import TYPE_CHECKING

from fastapi import Request

if TYPE_CHECKING:
    from orcia_core.audit_finops import (
        CognitiveImpactService,
        FinopsAccountingService,
        ProvenanceExporterService,
        RemoteUsageSanitizer,
        SqlAuditLedgerService,
        SqlConnectorQuotaGuardService,
    )
    from orcia_core.ports.log_sink import LogSinkQueryPort

from orcia_api.dependencies._core_providers import get_configured_db_engine
from orcia_api.dependencies.core_and_lifespan import get_auth_service, initialize_app_services
from orcia_core.bootstrap import SqlAutonomyContractRepository
from orcia_core.orchestration import (
    SqlWorkflowTriggerRepository,
    TriggerDispatcherService,
    has_active_dbos_runtime_bindings,
)
from orcia_core.permissions import AutonomyContractService


def get_audit_ledger_service(request: Request) -> SqlAuditLedgerService:
    """FastAPI `Depends` provider returning `SqlAuditLedgerService` (`Story 6.1`)."""
    from orcia_core.audit_finops import SqlAuditLedgerService

    engine = get_configured_db_engine(request)
    svc: SqlAuditLedgerService | None = getattr(request.app.state, "audit_ledger_service", None)
    if svc is None:
        initialize_app_services(request.app)
        svc = getattr(request.app.state, "audit_ledger_service", None)
        if svc is None:
            svc = SqlAuditLedgerService(engine=engine)
            request.app.state.audit_ledger_service = svc
    if getattr(svc, "_engine", None) is None and engine is not None:
        svc._engine = engine
    assert svc is not None
    return svc


def get_provenance_exporter_service(request: Request) -> ProvenanceExporterService:
    """FastAPI `Depends` provider returning `ProvenanceExporterService` (`Story 6.1`)."""
    from orcia_core.audit_finops import ProvenanceExporterService

    return ProvenanceExporterService(get_audit_ledger_service(request))


def get_finops_accounting_service(request: Request) -> FinopsAccountingService:
    """FastAPI `Depends` provider returning `FinopsAccountingService` (`Story 6.2`)."""
    from orcia_core.audit_finops import FinopsAccountingService
    from orcia_core.observability.logging import get_logger

    engine = get_configured_db_engine(request)

    async def _resume_dbos_run(run_id: str) -> None:
        from dbos import DBOS

        if has_active_dbos_runtime_bindings():
            await DBOS.send_async(
                run_id,
                "BUDGET_OVERRIDE_APPROVED",
                topic="orcia.budget.override",
            )
        else:
            get_logger("orcia.api.finops").info(
                "finops_budget_override_run_marked_pending_dbos_idle",
                run_id=run_id,
            )

    svc: FinopsAccountingService | None = getattr(
        request.app.state, "finops_accounting_service", None
    )
    if svc is None:
        initialize_app_services(request.app)
        svc = getattr(request.app.state, "finops_accounting_service", None)
        if svc is None:
            engine = getattr(request.app.state, "db_engine", None) or engine
            svc = FinopsAccountingService(
                engine=engine,
                sse_broker=getattr(request.app.state, "sse_broker", None),
                run_resumer=_resume_dbos_run,
            )
            request.app.state.finops_accounting_service = svc
    if getattr(svc, "_engine", None) is None and engine is not None:
        svc._engine = engine
    return svc


def get_cognitive_impact_service(request: Request) -> CognitiveImpactService:
    """FastAPI `Depends` provider returning `CognitiveImpactService` (`Story 6.3`, `Story 7.4`)."""
    from orcia_api.dependencies.autonomous_supervision import get_post_hoc_audit_service
    from orcia_core.audit_finops import CognitiveImpactService

    engine = get_configured_db_engine(request)
    post_hoc = get_post_hoc_audit_service(request)
    svc: CognitiveImpactService | None = getattr(
        request.app.state, "cognitive_impact_service", None
    )
    if svc is None:
        svc = CognitiveImpactService(engine=engine, post_hoc_service=post_hoc)
        request.app.state.cognitive_impact_service = svc
    else:
        if getattr(svc, "_engine", None) is None and engine is not None:
            svc._engine = engine
        svc._post_hoc = post_hoc
    return svc


def get_remote_usage_sanitizer(request: Request) -> RemoteUsageSanitizer:
    """FastAPI `Depends` provider returning `RemoteUsageSanitizer` (`Story 6.4`)."""
    from orcia_core.audit_finops import RemoteUsageSanitizer

    svc: RemoteUsageSanitizer | None = getattr(request.app.state, "finops_sanitizer", None)
    if svc is None:
        svc = RemoteUsageSanitizer()
        request.app.state.finops_sanitizer = svc
    return svc


def get_connector_quota_guard_service(request: Request) -> SqlConnectorQuotaGuardService:
    """FastAPI `Depends` provider returning `SqlConnectorQuotaGuardService` (`Story 6.4`)."""
    from orcia_core.audit_finops import SqlConnectorQuotaGuardService

    svc: SqlConnectorQuotaGuardService | None = getattr(
        request.app.state, "connector_quota_guard_service", None
    )
    engine = get_configured_db_engine(request)
    if svc is None or (getattr(svc, "_engine", None) is None and engine is not None):
        svc = SqlConnectorQuotaGuardService(engine=engine)
        request.app.state.connector_quota_guard_service = svc
    return svc


def get_log_sink_port(request: Request) -> LogSinkQueryPort:
    """FastAPI `Depends` provider returning the configured `LogSinkQueryPort` (`AD-23`)."""
    from orcia_core.observability import build_log_sink_from_env

    sink: LogSinkQueryPort | None = getattr(request.app.state, "log_sink", None)
    if sink is None:
        initialize_app_services(request.app)
        sink = getattr(request.app.state, "log_sink", None)
        if sink is None:
            sink = build_log_sink_from_env(
                http_client=getattr(request.app.state, "http_client", None),
                secret_provider=getattr(request.app.state, "secret_provider", None),
            )
            request.app.state.log_sink = sink
    return sink


def get_autonomy_contract_service(request: Request) -> AutonomyContractService:
    """FastAPI `Depends` provider returning `AutonomyContractService` (`Story 7.1`)."""
    from orcia_api.dependencies.orchestration_and_settings import get_hierarchical_rbac_service

    engine = get_configured_db_engine(request)
    svc: AutonomyContractService | None = getattr(
        request.app.state, "autonomy_contract_service", None
    )
    if svc is None:
        rbac_svc = get_hierarchical_rbac_service(request)
        audit_sink = get_audit_ledger_service(request)
        repo: SqlAutonomyContractRepository | None = (
            SqlAutonomyContractRepository(engine=engine, audit_ledger_sink=audit_sink)
            if engine is not None
            else None
        )
        svc = AutonomyContractService(rbac_service=rbac_svc, repository=repo)
        request.app.state.autonomy_contract_service = svc
    elif engine is not None and getattr(svc, "_repo", None) is None:
        audit_sink = get_audit_ledger_service(request)
        svc._repo = SqlAutonomyContractRepository(engine=engine, audit_ledger_sink=audit_sink)
    return svc


def get_trigger_dispatcher_service(request: Request) -> TriggerDispatcherService:
    """FastAPI `Depends` provider returning `TriggerDispatcherService` (`Story 7.2`)."""
    from orcia_api.dependencies.autonomous_supervision import get_autonomous_supervision_service
    from orcia_api.dependencies.orchestration_and_settings import get_notification_service
    from orcia_api.dependencies.workspace_and_packs import (
        get_help_generation_and_attachment_service,
    )
    from orcia_connectors._autonomous_trigger_bridge import build_autonomous_trigger_executor
    from orcia_core.orchestration._triggers_runtime_ports import RedisTriggerIdempotencyLockAdapter

    engine = get_configured_db_engine(request)
    contract_svc = get_autonomy_contract_service(request)
    executor = build_autonomous_trigger_executor(
        contract_service=contract_svc,
        supervision_service=get_autonomous_supervision_service(request),
        help_generator=get_help_generation_and_attachment_service(request),
        secret_provider=getattr(request.app.state, "secret_provider", None),
    )
    svc: TriggerDispatcherService | None = getattr(
        request.app.state, "trigger_dispatcher_service", None
    )
    if svc is None:
        repo: SqlWorkflowTriggerRepository | None = (
            SqlWorkflowTriggerRepository(
                engine=engine, audit_ledger_sink=get_audit_ledger_service(request)
            )
            if engine is not None
            else None
        )
        svc = TriggerDispatcherService(
            contract_service=contract_svc,
            repository=repo,
            idempotency_lock=RedisTriggerIdempotencyLockAdapter(
                redis_client=getattr(request.app.state, "redis_client", None)
            ),
            sse_broker=get_notification_service(request).sse_broker,
            vault_cipher=get_auth_service(request).vault_cipher,
            log_sink=get_log_sink_port(request),
            autonomous_executor=executor,
        )
        request.app.state.trigger_dispatcher_service = svc
    else:
        if engine is not None and getattr(svc, "_repo", None) is None:
            svc._repo = SqlWorkflowTriggerRepository(
                engine=engine, audit_ledger_sink=get_audit_ledger_service(request)
            )
        if getattr(svc, "_autonomous_executor", None) is None:
            svc.set_autonomous_executor(executor)
    return svc
