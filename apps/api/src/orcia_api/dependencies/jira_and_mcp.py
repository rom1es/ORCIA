"""Composition Root `Depends` providers for Jira Staged Actions & Governed MCP (`Story 24.1`)."""

from __future__ import annotations

from fastapi import Request

from orcia_api.dependencies._core_providers import (
    get_configured_db_engine,
    should_auto_init_infra,
)
from orcia_connectors import MultiProjectJiraStagedActionService, SqlJiraStagedActionsRepository
from orcia_core.orchestration import SqlMcpProposalsRepository
from orcia_core.orchestration.mcp_server import GovernedMcpServerService


def get_jira_staged_action_service(request: Request) -> MultiProjectJiraStagedActionService:
    """FastAPI `Depends` provider returning `MultiProjectJiraStagedActionService` wired to PG18."""
    engine = get_configured_db_engine(request)
    strict_sql = (engine is not None) or should_auto_init_infra("DATABASE_URL")
    svc: MultiProjectJiraStagedActionService | None = getattr(
        request.app.state, "jira_staged_action_service", None
    )
    if svc is None:
        repo = SqlJiraStagedActionsRepository(engine) if engine is not None else None
        svc = MultiProjectJiraStagedActionService(repository=repo, strict_sql=strict_sql)
        request.app.state.jira_staged_action_service = svc
    elif svc._repository is None and engine is not None:
        svc._repository = SqlJiraStagedActionsRepository(engine)
        svc._strict_sql = True
    return svc


def get_mcp_server_service(request: Request) -> GovernedMcpServerService:
    """FastAPI `Depends` provider returning `GovernedMcpServerService` wired to PG18."""
    engine = get_configured_db_engine(request)
    session_maker = getattr(request.app.state, "session_maker", None)
    has_pg = (session_maker is not None) or (engine is not None)
    strict_sql = has_pg or should_auto_init_infra("DATABASE_URL")
    svc: GovernedMcpServerService | None = getattr(request.app.state, "mcp_server_service", None)
    if svc is None:
        repo = (
            SqlMcpProposalsRepository(session_maker=session_maker, engine=engine)
            if has_pg
            else None
        )
        svc = GovernedMcpServerService(proposals_repository=repo, strict_sql=strict_sql)
        request.app.state.mcp_server_service = svc
    elif svc._proposals_repository is None and has_pg:
        svc._proposals_repository = SqlMcpProposalsRepository(
            session_maker=session_maker, engine=engine
        )
        svc._strict_sql = True
    return svc
