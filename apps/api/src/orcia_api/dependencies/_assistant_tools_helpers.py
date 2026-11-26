"""Callbacks & PG18/RAG/MCP Helpers for `assistant_tools.py` (`Story 26.6b`)."""

from __future__ import annotations

from typing import Any

from fastapi import Request
from sqlalchemy.ext.asyncio import async_sessionmaker

from orcia_api.dependencies._assistant_guards import (
    prepare_server_source_uri_authorizer,
    resolve_assistant_workspace_uuid,
)
from orcia_api.dependencies._assistant_tools_ontology import (
    is_record_visible_in_workspace as is_record_visible_in_workspace,
)
from orcia_api.dependencies._assistant_tools_ontology import run_workspace_ontology_lookup
from orcia_api.dependencies._core_providers import (
    get_auth_service,
    get_configured_db_engine,
)
from orcia_api.dependencies._rag_availability_guards import get_optional_embedding_port
from orcia_api.dependencies.workspace_and_packs import (
    get_agents_and_skills_service,
    get_remote_test_bench_and_mcp_service,
)
from orcia_core.observability.logging import get_logger
from orcia_core.permissions.models import UserIdentity
from orcia_core.ports.assistant_tool_executor_port import (
    AssistantToolExecutionRequest,
    AuthorizedToolDescriptor,
    McpExposedToolSpec,
)
from orcia_core.rag import SqlHybridRagRepository
from orcia_core.rag.errors import NoActiveEmbeddingModelError, RagReindexInProgressError

logger = get_logger("orcia.api.dependencies.assistant_tools")


async def collect_authorized_mcp_specs(
    request: Request,
    *,
    workspace_id: str,
    workspace_slug: str | None = None,
    loaded_agents: list[Any],
) -> list[McpExposedToolSpec]:
    """Collect MCP-exposed tool descriptors using canonical workspace slug & exposure service."""
    evaluator = get_auth_service(request).evaluator
    ws = evaluator.get_workspace(workspace_id)
    canonical_slug = workspace_slug or (ws.slug if ws is not None else workspace_id)
    mcp_specs: list[McpExposedToolSpec] = []
    for ag in loaded_agents:
        if (
            not ag.enabled_in_workspace
            or not ag.mcp_exposed
            or getattr(ag, "lifecycle_status", "DRAFT") == "DRAFT"
        ):
            continue
        for raw_tool_key, raw_mode in ag.mcp_tool_permissions:
            mode = str(raw_mode or "NONE").strip().upper()
            if mode == "NONE":
                continue
            perm_mode = "WRITE_PREVIEW" if mode == "WRITE_PREVIEW" else "READ_ONLY"
            mcp_specs.append(
                McpExposedToolSpec(
                    tool_name=f"mcp_{ag.slug.replace('-', '_')}_{raw_tool_key}",
                    agent_slug=ag.slug,
                    description=f"MCP tool '{raw_tool_key}' on agent '{ag.name}' ({perm_mode}).",
                    permission_mode=perm_mode,  # type: ignore[arg-type]
                    is_si_write=(perm_mode == "WRITE_PREVIEW"),
                    human_authored_required=False,
                    mcp_exposed=True,
                    required_permission="execute",
                    source_uri_or_scope=f"mcp://{canonical_slug}/{ag.slug}/{raw_tool_key}",
                )
            )
    try:
        mcp_svc = get_remote_test_bench_and_mcp_service(request)
        exposed = await mcp_svc.list_exposed_agents_async(workspace_slug=canonical_slug)
        for spec in exposed:
            if not spec.mcp_exposed:
                continue
            is_write = spec.regime != "CONSULTATION_ANALYSIS"
            mcp_specs.append(
                McpExposedToolSpec(
                    tool_name=f"mcp_agent_{spec.agent_slug.replace('-', '_')}",
                    agent_slug=spec.agent_slug,
                    description=f"Governed MCP agent '{spec.display_name}'.",
                    permission_mode="WRITE_PREVIEW" if is_write else "READ_ONLY",
                    is_si_write=is_write,
                    human_authored_required=spec.human_authored_required,
                    mcp_exposed=True,
                    required_permission="execute",
                    source_uri_or_scope=f"mcp://{canonical_slug}/{spec.agent_slug}",
                )
            )
    except Exception as exc:
        logger.warning(
            "assistant_tool_catalog_mcp_load_failed",
            workspace_id=workspace_id,
            workspace_slug=canonical_slug,
            error_type=type(exc).__name__,
        )
    return mcp_specs


def _build_sql_rag_repo(request: Request) -> SqlHybridRagRepository | None:
    session_maker: Any = getattr(request.app.state, "session_maker", None)
    if session_maker is not None:
        return SqlHybridRagRepository(session_maker)
    engine = get_configured_db_engine(request)
    if engine is not None:
        return SqlHybridRagRepository(async_sessionmaker(engine, expire_on_commit=False))
    return None


def build_tool_execution_callbacks(request: Request) -> tuple[Any, Any, Any, Any]:
    """Return `(rag_search_fn, ontology_lookup_fn, skill_runner_fn, mcp_tool_runner_fn)`."""

    async def _rag_search(
        ws_id: str, query: str, limit: int, user: UserIdentity | None = None
    ) -> list[dict[str, Any]]:
        if not isinstance(user, UserIdentity) or not user.id or user.id == "u-anonymous":
            return []
        sql_rag = _build_sql_rag_repo(request)
        if sql_rag is None or not query.strip():
            return []
        ws_uuid = await resolve_assistant_workspace_uuid(request, ws_id)
        emb_port = await get_optional_embedding_port(request)
        if emb_port is None:
            return []
        try:
            q_emb = tuple(await emb_port.embed_query(query))
            hits = await sql_rag.search_hybrid_rrf(
                workspace_id=ws_uuid if ws_uuid != "GLOBAL" else ws_id,
                query_text=query,
                query_embedding=q_emb,
                limit=limit,
            )
        except (NoActiveEmbeddingModelError, RagReindexInProgressError):
            return []
        if not hits:
            return []
        authorizer = await prepare_server_source_uri_authorizer(request, user, workspace_id=ws_id)
        allowed_uris = authorizer(tuple(dict.fromkeys(h.source_uri for h in hits)))
        evaluator = get_auth_service(request).evaluator
        ws = evaluator.get_workspace(ws_id)
        ws_access = evaluator.resolve_workspace_access(user, ws.id) if ws is not None else None
        is_observer = str(user.platform_role or "").upper() in (
            "OBSERVER",
            "READ_ONLY_OBSERVER",
            "BU_DIRECTOR",
        ) or (ws_access is not None and ws_access.access_mode == "READ_ONLY_OBSERVER")
        filtered = [
            h
            for h in hits
            if h.source_uri in allowed_uris
            and (not is_observer or h.source_uri.startswith("orcia://blackboard/"))
        ]
        return [
            {
                "source_uri": h.source_uri,
                "title": h.contextual_header,
                "content": h.injected_content[:400],
                "score": round(float(h.rrf_score), 4),
            }
            for h in filtered
        ]

    async def _ontology_lookup(ws_id: str, query: str, level: str | None) -> list[dict[str, Any]]:
        return await run_workspace_ontology_lookup(request, ws_id=ws_id, query=query, level=level)

    async def _skill_runner(
        desc: AuthorizedToolDescriptor, args: dict[str, Any], _ws_id: str
    ) -> dict[str, Any]:
        ag_svc = get_agents_and_skills_service(request)
        skill_id = desc.skill_id or desc.tool_name
        input_text = str(
            args.get("input_text") or next((str(v) for v in args.values() if v), desc.tool_name)
        )
        str_params = {str(k): str(v) for k, v in args.items()}
        outcome = ag_svc.execute_skill(skill_id, input_text=input_text, parameters=str_params)
        return {
            "skill_id": outcome.skill_id,
            "skill_name": outcome.skill_name,
            "output_text": outcome.output_text,
            "status": outcome.status,
        }

    async def _mcp_runner(
        desc: AuthorizedToolDescriptor, req: AssistantToolExecutionRequest
    ) -> dict[str, Any]:
        evaluator = get_auth_service(request).evaluator
        ws = evaluator.get_workspace(req.workspace_id)
        ws_slug = ws.slug if ws is not None else req.workspace_id
        prompt_text = str(
            req.arguments.get("query") or req.arguments.get("input_text") or desc.description
        )
        mcp_svc = get_remote_test_bench_and_mcp_service(request)
        res = await mcp_svc.invoke_governed_mcp_read_only_for_assistant_async(
            workspace_slug=ws_slug,
            agent_slug=desc.mcp_agent_slug or desc.tool_name,
            caller_role=req.user_role,
            passthrough_identity=req.user_email or req.user_id,
            prompt_text=prompt_text,
        )
        return {
            "status": "EXECUTED",
            "invocation_id": str(res.invocation_id),
            "tool_name": desc.tool_name,
            "mcp_agent_slug": desc.mcp_agent_slug or res.tool_name,
            "workspace_slug": res.workspace_slug,
            "execution_identity": req.execution_identity,
            "passthrough_identity": res.passthrough_identity,
            "audit_actor_type": res.audit_actor_type,
            "history_badge_fr": res.history_badge_fr,
            "response_text": res.sanitized_response_text,
        }

    return _rag_search, _ontology_lookup, _skill_runner, _mcp_runner


__all__ = [
    "build_tool_execution_callbacks",
    "collect_authorized_mcp_specs",
    "is_record_visible_in_workspace",
]
