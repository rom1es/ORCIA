"""Composition Root `Depends` Providers for `GovernedAssistantToolRouter` (`Story 26.6b`)."""

from __future__ import annotations

from fastapi import Request

from orcia_api.dependencies._assistant_tools_helpers import (
    build_tool_execution_callbacks,
    collect_authorized_mcp_specs,
    is_record_visible_in_workspace,
)
from orcia_api.dependencies._core_providers import (
    get_auth_service,
    get_configured_db_engine,
    get_permission_broker_service,
)
from orcia_api.dependencies._rag_availability_guards import get_optional_embedding_port
from orcia_api.dependencies._telemetry_sinks import (
    resolve_assistant_outbox_emitter,
    resolve_audit_ledger_sink,
)
from orcia_api.dependencies._topology_sync import sync_evaluator_topology_from_pg
from orcia_api.dependencies.workspace_and_packs import (
    get_agents_and_skills_service,
    get_surgical_explorer_service,
)
from orcia_core.agents import GovernedAssistantToolRouter, RedisToolIdempotencyStore
from orcia_core.gates.sandbox import SubprocessTier1SandboxAdapter
from orcia_core.kernel.events import DomainEvent
from orcia_core.observability.logging import get_logger
from orcia_core.orchestration import load_agents_and_skills_from_postgres18
from orcia_core.permissions.models import UserIdentity
from orcia_core.ports.assistant_tool_executor_port import (
    AssistantToolCatalogContext,
    AssistantToolExecutorPort,
    SkillCatalogEntry,
)
from orcia_core.ports.embedding import EmbeddingPort

logger = get_logger("orcia.api.dependencies.assistant_tools")


async def _resolve_user_workspace_permissions(
    request: Request,
    *,
    user: UserIdentity | None,
    workspace_id: str,
) -> tuple[str, frozenset[str], frozenset[str]]:
    auth_svc = get_auth_service(request)
    await sync_evaluator_topology_from_pg(request, auth_svc)
    if user is None or not user.id or user.id == "u-anonymous":
        return ("OBSERVER", frozenset(), frozenset())
    role = str(user.platform_role or "OBSERVER").upper()
    user_roles = frozenset({role, *user.roles, *user.transverse_groups})
    if role in ("OBSERVER", "READ_ONLY_OBSERVER", "BU_DIRECTOR"):
        return (role, user_roles, frozenset({"read"}))
    evaluator = auth_svc.evaluator
    if workspace_id != "scope-global":
        ws = evaluator.get_workspace(workspace_id)
        if ws is None:
            return (role, user_roles, frozenset())
        access = evaluator.resolve_workspace_access(user, ws.id)
        if access is None:
            return (role, user_roles, frozenset())
        if access.access_mode == "READ_ONLY_OBSERVER":
            return ("READ_ONLY_OBSERVER", user_roles, frozenset({"read"}))
    return (role, user_roles, frozenset({"read", "execute"}))


async def _is_rag_active_for_turn(
    request: Request,
    *,
    embedding_port: EmbeddingPort | None = None,
) -> bool:
    if embedding_port is not None:
        return True
    try:
        return (await get_optional_embedding_port(request)) is not None
    except Exception as exc:
        logger.warning("assistant_tool_rag_probe_failed", error_type=type(exc).__name__)
        return False


async def build_assistant_tool_catalog_context_async(
    request: Request,
    *,
    user: UserIdentity | None,
    workspace_id: str,
    active_hat: str = "ARCHITECT",
    embedding_port: EmbeddingPort | None = None,
) -> AssistantToolCatalogContext:
    """Build full per-turn catalog context from PG18 skills, MCP exposure & workspace RBAC."""
    role, user_roles, user_perms = await _resolve_user_workspace_permissions(
        request, user=user, workspace_id=workspace_id
    )
    rag_active = await _is_rag_active_for_turn(request, embedding_port=embedding_port)

    auth_svc = get_auth_service(request)
    ws = auth_svc.evaluator.get_workspace(workspace_id)
    ws_uuid = ws.id if ws is not None else workspace_id
    ws_slug = ws.slug if ws is not None else workspace_id

    ag_svc = get_agents_and_skills_service(request)
    engine = get_configured_db_engine(request)
    loaded_agents = list(ag_svc.agents)
    loaded_skills = list(ag_svc.skills)
    if engine is not None:
        try:
            pg_skills, pg_agents = await load_agents_and_skills_from_postgres18(
                engine, workspace_id=ws_uuid
            )
            if pg_skills or pg_agents:
                ag_svc.sync_from_records(skills=pg_skills, agents=pg_agents)
                loaded_skills = list(pg_skills)
                loaded_agents = list(pg_agents)
        except Exception as exc:
            logger.warning(
                "assistant_tool_catalog_pg18_skills_load_failed",
                workspace_id=workspace_id,
                error_type=type(exc).__name__,
            )

    scoped_skills = [
        sk
        for sk in loaded_skills
        if is_record_visible_in_workspace(sk, ws_uuid=ws_uuid, ws_slug=ws_slug, user=user)
    ]
    scoped_agents = [
        ag
        for ag in loaded_agents
        if is_record_visible_in_workspace(ag, ws_uuid=ws_uuid, ws_slug=ws_slug, user=user)
    ]
    skills_by_id = {
        sk.skill_id: SkillCatalogEntry(
            skill_id=sk.skill_id,
            slug=sk.slug,
            name=sk.name,
            objective=sk.objective,
            input_parameters=tuple(sk.input_parameters),
            instructions=sk.instructions,
            expected_output_format=sk.expected_output_format,
            enabled_in_workspace=bool(sk.enabled_in_workspace),
            sandbox_tier="TIER_1_WASM",
            is_si_write=bool(getattr(sk, "is_si_write", False)),
            human_authored_required=bool(getattr(sk, "human_authored_required", False)),
            uri=sk.uri,
        )
        for sk in scoped_skills
    }
    mcp_specs = await collect_authorized_mcp_specs(
        request,
        workspace_id=ws_uuid,
        workspace_slug=ws_slug,
        loaded_agents=scoped_agents,
    )
    return AssistantToolCatalogContext(
        workspace_id=workspace_id,
        user_id=user.id if user is not None else "u-anonymous",
        user_role=role,
        active_hat=active_hat,
        user_roles=user_roles,
        user_permissions=user_perms,
        rag_active=rag_active,
        skills=tuple(skills_by_id.values()),
        mcp_tools=tuple(mcp_specs),
    )


def get_governed_assistant_tool_router(request: Request) -> AssistantToolExecutorPort:
    """FastAPI `Depends` provider returning `GovernedAssistantToolRouter` wired to PG18/Redis."""
    cached: AssistantToolExecutorPort | None = getattr(
        request.app.state, "governed_assistant_tool_router", None
    )
    if cached is not None:
        return cached

    redis_cli = getattr(request.app.state, "redis_client", None)
    idem_store = getattr(request.app.state, "assistant_tool_idempotency_store", None)
    if idem_store is None:
        idem_store = RedisToolIdempotencyStore(redis_client=redis_cli)
        request.app.state.assistant_tool_idempotency_store = idem_store
    elif redis_cli is not None and getattr(idem_store, "_redis", None) is None:
        idem_store.set_redis_client(redis_cli)

    rag_fn, onto_fn, skill_fn, mcp_fn = build_tool_execution_callbacks(request)

    async def _outbox_enqueue(event: DomainEvent) -> str | None:
        emitter = resolve_assistant_outbox_emitter(request)
        if emitter is None:
            return None
        return await emitter.emit_domain_event(event)

    router = GovernedAssistantToolRouter(
        permission_broker=get_permission_broker_service(request),
        evaluator=get_auth_service(request).evaluator,
        surgical_explorer=get_surgical_explorer_service(request),
        sandbox_port=SubprocessTier1SandboxAdapter(),
        audit_ledger_sink=resolve_audit_ledger_sink(request),
        idempotency_store=idem_store,
        rag_search_fn=rag_fn,
        ontology_lookup_fn=onto_fn,
        skill_runner_fn=skill_fn,
        mcp_tool_runner_fn=mcp_fn,
        outbox_enqueue_fn=_outbox_enqueue,
    )
    request.app.state.governed_assistant_tool_router = router
    return router


__all__ = [
    "build_assistant_tool_catalog_context_async",
    "get_governed_assistant_tool_router",
]
