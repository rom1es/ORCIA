"""Orchestration, Inbox, Leases, RBAC, Settings, Cognitive Router & Studio providers (`AD-19`)."""

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

from orcia_api.dependencies.core_and_lifespan import initialize_app_services
from orcia_core.bootstrap import DurableOnboardingWizardService
from orcia_core.orchestration import (
    AiModelsHubService,
    CognitiveModelRouterService,
    ControlCenterOverviewService,
    ResourceLeaseService,
    SqlWorkflowTriggerRepository,
    TriggerDispatcherService,
    UnifiedNotificationAndClaimService,
    WorkflowOrchestrationSetupService,
    WorkflowStudioAndPackService,
)
from orcia_core.permissions import (
    AutonomyContractService,
    HierarchicalRbacService,
    IamAccountsGovernanceService,
    PlatformSettingsService,
)
from orcia_core.rag import ConnectorHubAndIngestionService


def get_orchestration_service(request: Request) -> WorkflowOrchestrationSetupService:
    """FastAPI `Depends` provider returning `WorkflowOrchestrationSetupService` from `app.state`."""
    svc: WorkflowOrchestrationSetupService | None = getattr(
        request.app.state, "orchestration_service", None
    )
    if svc is None:
        initialize_app_services(request.app)
        svc = request.app.state.orchestration_service
    assert svc is not None
    return svc


def get_notification_service(request: Request) -> UnifiedNotificationAndClaimService:
    """FastAPI `Depends` provider returning `UnifiedNotificationAndClaimService`."""
    from orcia_api.dependencies._core_providers import get_configured_db_engine

    engine = get_configured_db_engine(request)
    svc: UnifiedNotificationAndClaimService | None = getattr(
        request.app.state, "notification_service", None
    )
    if svc is None:
        initialize_app_services(request.app)
        svc = request.app.state.notification_service
    assert svc is not None
    if getattr(svc, "_engine", None) is None and engine is not None:
        svc.set_engine(engine)
    return svc


def get_resource_lease_service(request: Request) -> ResourceLeaseService:
    """FastAPI `Depends` provider returning `ResourceLeaseService` (`DEC-CONC-01`)."""
    from orcia_api.dependencies._core_providers import get_configured_db_engine

    engine = get_configured_db_engine(request)
    svc: ResourceLeaseService | None = getattr(request.app.state, "resource_lease_service", None)
    if svc is None:
        initialize_app_services(request.app)
        svc = request.app.state.resource_lease_service
    assert svc is not None
    if getattr(svc, "_engine", None) is None and engine is not None:
        svc.set_engine(engine)
    return svc


def get_control_center_service(request: Request) -> ControlCenterOverviewService:
    """FastAPI `Depends` provider returning `ControlCenterOverviewService`."""
    svc: ControlCenterOverviewService | None = getattr(
        request.app.state, "control_center_service", None
    )
    if svc is None:
        initialize_app_services(request.app)
        svc = request.app.state.control_center_service
    assert svc is not None
    return svc


def get_hierarchical_rbac_service(request: Request) -> HierarchicalRbacService:
    """FastAPI `Depends` provider returning `HierarchicalRbacService`."""
    svc: HierarchicalRbacService | None = getattr(
        request.app.state, "hierarchical_rbac_service", None
    )
    if svc is None:
        initialize_app_services(request.app)
        svc = request.app.state.hierarchical_rbac_service
    assert svc is not None
    return svc


def get_iam_accounts_service(request: Request) -> IamAccountsGovernanceService:
    """FastAPI `Depends` provider returning `IamAccountsGovernanceService` (`Story 17.3`)."""
    svc: IamAccountsGovernanceService | None = getattr(
        request.app.state, "iam_accounts_service", None
    )
    if svc is None:
        initialize_app_services(request.app)
        svc = request.app.state.iam_accounts_service
    assert svc is not None
    return svc


def get_platform_settings_service(request: Request) -> PlatformSettingsService:
    """FastAPI `Depends` provider returning `PlatformSettingsService`."""
    svc: PlatformSettingsService | None = getattr(
        request.app.state, "platform_settings_service", None
    )
    if svc is None:
        initialize_app_services(request.app)
        svc = request.app.state.platform_settings_service
    assert svc is not None
    return svc


def get_cognitive_router_service(request: Request) -> CognitiveModelRouterService:
    """FastAPI `Depends` provider returning `CognitiveModelRouterService`."""
    svc: CognitiveModelRouterService | None = getattr(
        request.app.state, "cognitive_router_service", None
    )
    if svc is None:
        initialize_app_services(request.app)
        svc = request.app.state.cognitive_router_service
    assert svc is not None
    return svc


def get_connector_hub_service(request: Request) -> ConnectorHubAndIngestionService:
    """FastAPI `Depends` provider returning `ConnectorHubAndIngestionService`."""
    svc: ConnectorHubAndIngestionService | None = getattr(
        request.app.state, "connector_hub_service", None
    )
    if svc is None:
        initialize_app_services(request.app)
        svc = request.app.state.connector_hub_service
    assert svc is not None
    return svc


def get_studio_and_pack_service(request: Request) -> WorkflowStudioAndPackService:
    """FastAPI `Depends` provider returning `WorkflowStudioAndPackService`."""
    svc: WorkflowStudioAndPackService | None = getattr(
        request.app.state, "studio_and_pack_service", None
    )
    if svc is None:
        initialize_app_services(request.app)
        svc = request.app.state.studio_and_pack_service
    assert svc is not None
    return svc


def get_durable_wizard_service(request: Request) -> DurableOnboardingWizardService:
    """FastAPI `Depends` provider returning `DurableOnboardingWizardService`."""
    from orcia_api.dependencies._core_providers import get_configured_db_engine
    from orcia_core.bootstrap import SqlWizardSessionRepository

    engine = get_configured_db_engine(request)
    svc: DurableOnboardingWizardService | None = getattr(
        request.app.state, "durable_wizard_service", None
    )
    if svc is None:
        initialize_app_services(request.app)
        svc = request.app.state.durable_wizard_service
    assert svc is not None
    if engine is not None and getattr(svc, "_repository", None) is None:
        svc.set_repository(SqlWizardSessionRepository(engine))
    return svc


def get_ai_models_hub_service(request: Request) -> AiModelsHubService:
    """FastAPI `Depends` provider returning `AiModelsHubService` (`Story 17.5`)."""
    svc: AiModelsHubService | None = getattr(request.app.state, "ai_models_hub_service", None)
    if svc is None:
        initialize_app_services(request.app)
        auth = request.app.state.auth_service
        svc = AiModelsHubService(vault_cipher=auth.vault_cipher)
        request.app.state.ai_models_hub_service = svc
    return svc


def get_audit_ledger_service(request: Request) -> SqlAuditLedgerService:
    """FastAPI `Depends` provider returning `SqlAuditLedgerService` (`Story 6.1`)."""
    from orcia_api.dependencies._core_providers import get_configured_db_engine
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

    ledger_svc = get_audit_ledger_service(request)
    return ProvenanceExporterService(ledger_svc)


def get_finops_accounting_service(request: Request) -> FinopsAccountingService:
    """FastAPI `Depends` provider returning `FinopsAccountingService` (`Story 6.2`)."""
    from orcia_api.dependencies._core_providers import get_configured_db_engine
    from orcia_core.audit_finops import FinopsAccountingService
    from orcia_core.observability.logging import get_logger

    engine = get_configured_db_engine(request)

    async def _resume_dbos_run(run_id: str) -> None:
        from dbos import DBOS

        from orcia_core.orchestration._internal.dbos_engine import _RUNTIME_BINDINGS

        if _RUNTIME_BINDINGS:
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
            sse_broker = getattr(request.app.state, "sse_broker", None)
            svc = FinopsAccountingService(
                engine=engine,
                sse_broker=sse_broker,
                run_resumer=_resume_dbos_run,
            )
            request.app.state.finops_accounting_service = svc
    if getattr(svc, "_engine", None) is None and engine is not None:
        svc._engine = engine
    return svc


def get_cognitive_impact_service(request: Request) -> CognitiveImpactService:
    """FastAPI `Depends` provider returning `CognitiveImpactService` (`Story 6.3`, `Story 7.4`)."""
    from orcia_api.dependencies._core_providers import get_configured_db_engine
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
    from orcia_api.dependencies._core_providers import get_configured_db_engine
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
    from orcia_api.dependencies._core_providers import get_configured_db_engine
    from orcia_core.bootstrap import SqlAutonomyContractRepository

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
    from orcia_api.dependencies._core_providers import get_configured_db_engine
    from orcia_api.dependencies.autonomous_supervision import get_autonomous_supervision_service
    from orcia_api.dependencies.core_and_lifespan import get_auth_service
    from orcia_api.dependencies.workspace_and_packs import (
        get_help_generation_and_attachment_service,
    )
    from orcia_connectors._autonomous_trigger_bridge import build_autonomous_trigger_executor
    from orcia_core.orchestration._triggers_runtime_ports import RedisTriggerIdempotencyLockAdapter

    engine = get_configured_db_engine(request)
    contract_svc = get_autonomy_contract_service(request)
    supervision_svc = get_autonomous_supervision_service(request)
    help_gen_svc = get_help_generation_and_attachment_service(request)
    secret_provider = getattr(request.app.state, "secret_provider", None)
    executor = build_autonomous_trigger_executor(
        contract_service=contract_svc,
        supervision_service=supervision_svc,
        help_generator=help_gen_svc,
        secret_provider=secret_provider,
    )
    svc: TriggerDispatcherService | None = getattr(
        request.app.state, "trigger_dispatcher_service", None
    )
    if svc is None:
        audit_sink = get_audit_ledger_service(request)
        notif_svc = get_notification_service(request)
        auth_svc = get_auth_service(request)
        log_sink = get_log_sink_port(request)
        redis_client = getattr(request.app.state, "redis_client", None)
        repo: SqlWorkflowTriggerRepository | None = (
            SqlWorkflowTriggerRepository(engine=engine, audit_ledger_sink=audit_sink)
            if engine is not None
            else None
        )
        svc = TriggerDispatcherService(
            contract_service=contract_svc,
            repository=repo,
            idempotency_lock=RedisTriggerIdempotencyLockAdapter(redis_client=redis_client),
            sse_broker=notif_svc.sse_broker,
            vault_cipher=auth_svc.vault_cipher,
            log_sink=log_sink,
            autonomous_executor=executor,
        )
        request.app.state.trigger_dispatcher_service = svc
    else:
        if engine is not None and getattr(svc, "_repo", None) is None:
            audit_sink = get_audit_ledger_service(request)
            svc._repo = SqlWorkflowTriggerRepository(engine=engine, audit_ledger_sink=audit_sink)
        if getattr(svc, "_autonomous_executor", None) is None:
            svc.set_autonomous_executor(executor)
    return svc
