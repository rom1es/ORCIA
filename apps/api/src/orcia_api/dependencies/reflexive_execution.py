"""Composition Root `Depends` providers for `Story 16.2` & `Story 16.3` Dual-Mode Runtime.

Wires `NonDeterministicReflexiveRuntime`, `SqlReflexiveSessionStore` (PostgreSQL 18),
`SqlWorkflowDefinitionsV2Store` (PostgreSQL 18 `workflow_definitions_v2`),
`ProcessExecutionDispatcher`, `BoundedWorkflowLauncherAdapter`, `ReflexiveEventStreamBroker`
(Redis 7.4 / `asyncio.Queue`), `GatewayReflexiveLlmAdapter`, `SurgicalContextExplorer`, and
`ConnectorReflexiveWriteGateAdapter` on `request.app.state`.
"""

from __future__ import annotations

import os

from fastapi import Request
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from orcia_api.dependencies.core_and_lifespan import (
    get_or_create_shared_db_engine,
    initialize_app_services,
)
from orcia_api.dependencies.workspace_and_packs import get_surgical_explorer_service
from orcia_connectors import ConnectorReflexiveWriteGateAdapter
from orcia_connectors.bounded_workflow_v2 import BoundedWorkflowLauncherAdapter
from orcia_core.agents import (
    GatewayReflexiveLlmAdapter,
    NonDeterministicReflexiveRuntime,
    ProcessExecutionDispatcher,
    ReflexiveEventStreamBroker,
    SqlReflexiveSessionStore,
)
from orcia_core.storage.claim_check import get_claim_check_storage
from orcia_core.workflows import SqlWorkflowDefinitionsV2Store


def _resolve_reflexive_session_maker(
    request: Request,
) -> async_sessionmaker[AsyncSession] | None:
    """Resolve `AsyncSession` maker from `app.state` or `DATABASE_URL` when PostgreSQL is active."""
    existing: async_sessionmaker[AsyncSession] | None = getattr(
        request.app.state, "session_maker", None
    )
    if existing is not None:
        return existing

    cached: async_sessionmaker[AsyncSession] | None = getattr(
        request.app.state, "reflexive_session_maker", None
    )
    if cached is not None:
        return cached

    if os.environ.get("ORCIA_DISABLE_PG_BOOTSTRAP_SYNC") == "1":
        return None
    has_pg_env = bool((os.environ.get("DATABASE_URL") or "").strip()) or (
        os.environ.get("ORCIA_ENABLE_PG_SESSION_MAKER") == "1"
    )
    if not has_pg_env:
        return None

    engine = get_or_create_shared_db_engine(request)
    maker = async_sessionmaker(engine, expire_on_commit=False)
    request.app.state.reflexive_session_maker = maker
    return maker


def get_reflexive_event_stream_broker(request: Request) -> ReflexiveEventStreamBroker:
    """FastAPI `Depends` provider returning `ReflexiveEventStreamBroker`."""
    broker: ReflexiveEventStreamBroker | None = getattr(
        request.app.state, "reflexive_event_stream_broker", None
    )
    if broker is None:
        redis_url = (os.environ.get("REDIS_URL") or "").strip() or None
        broker = ReflexiveEventStreamBroker(redis_url=redis_url)
        request.app.state.reflexive_event_stream_broker = broker
    return broker


def get_reflexive_write_gate_service(request: Request) -> ConnectorReflexiveWriteGateAdapter:
    """FastAPI `Depends` provider returning `ConnectorReflexiveWriteGateAdapter`."""
    gate: ConnectorReflexiveWriteGateAdapter | None = getattr(
        request.app.state, "reflexive_write_gate_service", None
    )
    if gate is None:
        gate = ConnectorReflexiveWriteGateAdapter()
        request.app.state.reflexive_write_gate_service = gate
    return gate


def get_reflexive_runtime_service(request: Request) -> NonDeterministicReflexiveRuntime:
    """FastAPI `Depends` provider returning `NonDeterministicReflexiveRuntime`."""
    runtime: NonDeterministicReflexiveRuntime | None = getattr(
        request.app.state, "reflexive_runtime_service", None
    )
    if runtime is not None:
        return runtime

    if getattr(request.app.state, "llm_gateway", None) is None:
        initialize_app_services(request.app)

    session_maker = _resolve_reflexive_session_maker(request)
    strict_sql = os.environ.get("ORCIA_ENABLE_PG_SESSION_MAKER") == "1"
    session_store = SqlReflexiveSessionStore(
        session_maker=session_maker,
        strict_sql=strict_sql,
    )
    llm_adapter = GatewayReflexiveLlmAdapter(llm_gateway=request.app.state.llm_gateway)
    runtime = NonDeterministicReflexiveRuntime(
        llm_port=llm_adapter,
        surgical_explorer=get_surgical_explorer_service(request),
        session_store=session_store,
        event_stream=get_reflexive_event_stream_broker(request),
        write_gate=get_reflexive_write_gate_service(request),
        claim_check_storage=get_claim_check_storage(),
    )
    request.app.state.reflexive_runtime_service = runtime
    return runtime


def get_workflows_v2_sql_store(request: Request) -> SqlWorkflowDefinitionsV2Store:
    """FastAPI `Depends` provider returning `SqlWorkflowDefinitionsV2Store` (PostgreSQL 18)."""
    store: SqlWorkflowDefinitionsV2Store | None = getattr(
        request.app.state, "workflows_v2_sql_store", None
    )
    if store is None:
        session_maker = _resolve_reflexive_session_maker(request)
        strict_sql = os.environ.get("ORCIA_ENABLE_PG_SESSION_MAKER") == "1"
        store = SqlWorkflowDefinitionsV2Store(
            session_maker=session_maker,
            strict_sql=strict_sql,
        )
        request.app.state.workflows_v2_sql_store = store
    return store


def get_process_execution_dispatcher(request: Request) -> ProcessExecutionDispatcher:
    """FastAPI `Depends` provider returning `ProcessExecutionDispatcher` (`Story 16.3`)."""
    dispatcher: ProcessExecutionDispatcher | None = getattr(
        request.app.state, "process_execution_dispatcher", None
    )
    if dispatcher is None:
        claim_storage = get_claim_check_storage()
        dispatcher = ProcessExecutionDispatcher(
            reflexive_runtime=get_reflexive_runtime_service(request),
            bounded_launcher=BoundedWorkflowLauncherAdapter(storage=claim_storage),
            claim_check_storage=claim_storage,
        )
        request.app.state.process_execution_dispatcher = dispatcher
    return dispatcher
