"""Composition Root infrastructure, PG18 adapters & lifespan shutdown helpers (`AD-19`)."""

from __future__ import annotations

import asyncio
import os
from contextlib import suppress
from typing import Any

from fastapi import FastAPI

from orcia_api.dependencies._core_providers import should_auto_init_infra
from orcia_connectors import (
    MultiProjectJiraStagedActionService,
    SqlJiraStagedActionsRepository,
)
from orcia_core.gates import SqlGateEvaluationRepository
from orcia_core.observability.logging import get_logger
from orcia_core.orchestration import (
    DbosDurableWorkflowEngine,
    DbosSqlAlchemyUnitOfWork,
    GovernedMcpServerService,
    SqlMcpExposureRepository,
    SqlMcpProposalsRepository,
)
from orcia_core.orchestration.remote_test_bench_and_mcp_exposure import (
    RemoteServiceTestBenchAndGovernedMcpService,
)


def init_pg_engine_and_uow(app: FastAPI) -> None:
    """Initialize SQLAlchemy AsyncEngine, sessionmaker, and DBOS UnitOfWork on `app.state`."""
    if getattr(app.state, "session_maker", None) is not None or not should_auto_init_infra(
        "DATABASE_URL"
    ):
        return
    try:
        from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
        from sqlalchemy.pool import NullPool

        from orcia_core.config import resolve_database_url

        engine_kwargs: dict[str, object] = {"connect_args": {"timeout": 1.5}}
        force_real = os.environ.get("ORCIA_FORCE_REAL_RUNTIME", "").strip() == "1"
        is_test_runtime = not force_real and bool(
            os.environ.get("ORCIA_ENV", "").strip().lower() == "test"
            or os.environ.get("PYTEST_CURRENT_TEST", "").strip()
            or os.environ.get("PYTEST_VERSION", "").strip()
        )
        if is_test_runtime:
            engine_kwargs["poolclass"] = NullPool
        else:
            engine_kwargs["pool_size"] = 10
            engine_kwargs["max_overflow"] = 10
        db_engine = getattr(app.state, "db_engine", None)
        if db_engine is None:
            db_engine = create_async_engine(resolve_database_url(), **engine_kwargs)
            app.state.db_engine = db_engine
        app.state.session_maker = async_sessionmaker(db_engine, expire_on_commit=False)
        if getattr(app.state, "dbos_uow", None) is None:
            app.state.dbos_uow = DbosSqlAlchemyUnitOfWork.from_engine(
                db_engine, session_factory=app.state.session_maker
            )
    except Exception as exc:
        get_logger("orcia.api.lifespan").warning(
            "lifespan_pg_session_maker_init_skipped", error_type=type(exc).__name__
        )


def attach_pg18_repositories(app: FastAPI) -> None:
    """Attach PG18 SQL repositories to `app.state` domain services when `db_engine` exists."""
    active_db_engine = getattr(app.state, "db_engine", None)
    if active_db_engine is None:
        return
    if getattr(app.state, "gate_repository", None) is None:
        gate_repo = SqlGateEvaluationRepository(active_db_engine)
        app.state.gate_repository = gate_repo
        if getattr(app.state, "bootstrap_service", None) is not None:
            app.state.bootstrap_service.gate_service.set_repository(gate_repo)
    wiz_svc = getattr(app.state, "durable_wizard_service", None)
    if wiz_svc is not None and getattr(wiz_svc, "_repository", None) is None:
        from orcia_core.bootstrap import SqlWizardSessionRepository

        wiz_svc.set_repository(SqlWizardSessionRepository(active_db_engine))
    if getattr(app.state, "jira_staged_action_service", None) is None:
        app.state.jira_staged_action_service = MultiProjectJiraStagedActionService(
            repository=SqlJiraStagedActionsRepository(active_db_engine),
            strict_sql=True,
        )
    if getattr(app.state, "mcp_server_service", None) is None:
        app.state.mcp_server_service = GovernedMcpServerService(
            proposals_repository=SqlMcpProposalsRepository(
                session_maker=getattr(app.state, "session_maker", None),
                engine=active_db_engine,
            ),
            strict_sql=True,
        )
    if getattr(app.state, "remote_test_bench_and_mcp_service", None) is None:
        app.state.remote_test_bench_and_mcp_service = RemoteServiceTestBenchAndGovernedMcpService(
            repository=SqlMcpExposureRepository(
                session_maker=getattr(app.state, "session_maker", None),
                engine=active_db_engine,
            ),
            strict_sql=True,
        )
    for attr_name in (
        "audit_ledger_service",
        "connector_quota_guard_service",
        "finops_accounting_service",
        "cognitive_impact_service",
        "post_hoc_audit_service",
        "autonomous_supervision_service",
        "contextual_help_service",
        "notification_service",
        "resource_lease_service",
        "permission_broker_service",
        "assistant_folders_and_sharing_service",
        "assistant_thread_messages_repository",
        "pack_bundle_v2_repository",
        "pack_import_service",
    ):
        svc_inst = getattr(app.state, attr_name, None)
        if svc_inst is not None and getattr(svc_inst, "_engine", None) is None:
            if hasattr(svc_inst, "set_engine"):
                svc_inst.set_engine(active_db_engine)
            else:
                svc_inst._engine = active_db_engine


async def startup_declarative_packs_and_dbos(app: FastAPI) -> None:
    """Seed Day-0 SYSTEM packs via `PackImportService`, help seeds, and DBOS on startup."""
    from orcia_core.config import resolve_database_url
    from orcia_core.packs import seed_system_packs_on_engine

    db_engine = getattr(app.state, "db_engine", None)
    if db_engine is None:
        return
    try:
        outcomes = await seed_system_packs_on_engine(
            db_engine,
            cas_storage=getattr(app.state, "pack_cas_storage", None),
            import_service=getattr(app.state, "pack_import_service", None),
        )
        app.state.declarative_pack_seed_outcomes = outcomes
        help_svc = getattr(app.state, "contextual_help_service", None)
        if help_svc is not None and hasattr(help_svc, "ensure_seeded_in_postgres18_async"):
            await help_svc.ensure_seeded_in_postgres18_async()
    except Exception as exc:
        get_logger("orcia.api.lifespan").warning(
            "lifespan_declarative_packs_pg_sync_skipped",
            error_type=type(exc).__name__,
        )
    if getattr(app.state, "dbos_datasource", None) is None:
        try:
            uow = await DbosSqlAlchemyUnitOfWork.create(
                resolve_database_url(),
                engine=db_engine,
                schema="dbos",
                run_migrations=True,
            )
            app.state.dbos_datasource = uow.datasource
            app.state.dbos_uow = uow
        except Exception as exc:
            get_logger("orcia.api.lifespan").warning(
                "lifespan_dbos_datasource_fallback_engine", error_type=type(exc).__name__
            )
    if getattr(app.state, "dbos_durable_engine", None) is None:
        try:
            async_db_url = resolve_database_url()
            sync_db_url = async_db_url.replace("+asyncpg", "", 1)
            dbos_eng = DbosDurableWorkflowEngine(
                system_database_url=sync_db_url,
                application_database_url=async_db_url,
                app_name="orcia-api",
            )
            await dbos_eng.launch(existing_engine=db_engine)
            app.state.dbos_durable_engine = dbos_eng
        except Exception as exc:
            get_logger("orcia.api.lifespan").warning(
                "lifespan_dbos_durable_engine_skipped", error_type=type(exc).__name__
            )


def _resolve_assistant_drain_timeout_seconds() -> float:
    try:
        drain_s = max(
            0.05, float(os.environ.get("ORCIA_ASSISTANT_DRAIN_TIMEOUT_S", "10.0").strip())
        )
    except ValueError:
        drain_s = 10.0
    try:
        wall_cap_s = max(
            0.05, float(os.environ.get("ORCIA_ASSISTANT_WALL_CLOCK_BUDGET_S", "120.0").strip())
        )
    except ValueError:
        wall_cap_s = 120.0
    return min(drain_s, wall_cap_s)


async def drain_assistant_turn_tasks(app: FastAPI) -> None:
    """Gracefully wait for active assistant tasks up to bounded drain timeout, then cancel."""
    tasks: set[asyncio.Task[Any]] | None = getattr(app.state, "assistant_turn_tasks", None)
    if not tasks:
        return
    pending = [t for t in list(tasks) if not t.done()]
    if not pending:
        return
    drain_budget_s = _resolve_assistant_drain_timeout_seconds()
    _done, still_pending = await asyncio.wait(pending, timeout=drain_budget_s)
    if still_pending:
        for t in still_pending:
            t.cancel()
        await asyncio.gather(*still_pending, return_exceptions=True)


async def shutdown_app_resources(app: FastAPI, tracer_provider: Any) -> None:
    """Drain active assistant turns, then close SSE broker, tracing, HTTPX, Redis & SQL pool."""
    from orcia_core.observability import shutdown_tracing

    await drain_assistant_turn_tasks(app)
    sse_broker = getattr(app.state, "sse_broker", None)
    if sse_broker is not None and hasattr(sse_broker, "stop_pubsub_listener"):
        with suppress(Exception):
            await sse_broker.stop_pubsub_listener()
    shutdown_tracing(tracer_provider)
    http_client = getattr(app.state, "http_client", None)
    if http_client is not None:
        with suppress(Exception):
            await http_client.aclose()
    redis_client = getattr(app.state, "redis_client", None)
    if redis_client is not None:
        with suppress(Exception):
            await redis_client.aclose()
    dbos_durable_engine = getattr(app.state, "dbos_durable_engine", None)
    if dbos_durable_engine is not None:
        with suppress(Exception):
            await dbos_durable_engine.shutdown(dispose_engine=False)
    db_engine = getattr(app.state, "db_engine", None)
    if db_engine is not None:
        with suppress(Exception):
            await db_engine.dispose()
