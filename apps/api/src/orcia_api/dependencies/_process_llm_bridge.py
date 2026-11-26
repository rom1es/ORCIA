"""Live workspace LLM & datasource resolution bridge for Process execution (`Story 30.3`)."""

from __future__ import annotations

import os
from collections.abc import Sequence
from typing import Any
from uuid import UUID

import sqlalchemy as sa
from fastapi import FastAPI, Request

from orcia_api.dependencies._core_providers import get_auth_service, get_configured_db_engine
from orcia_api.dependencies._llm_streaming_providers import is_cassette_llm_enabled
from orcia_core.agents.errors import (
    ProcessDatasourcesRequiredError,
    ProcessModelNotConfiguredError,
)
from orcia_core.agents.llm_adapter import LlmEndpointResolver
from orcia_core.bootstrap import (
    list_workspace_datasources_from_postgres18,
    load_platform_setup_state_from_postgres18,
)
from orcia_core.bootstrap.setup_snapshot_cache import (
    get_valid_platform_setup_snapshot_async,
    set_cached_platform_setup_snapshot_async,
)
from orcia_core.orchestration.llm_endpoint_resolver import (
    resolve_configured_llm_endpoint_from_sources,
)
from orcia_core.permissions.models import UserIdentity
from orcia_core.ports.llm_streaming_port import LlmEndpointConfig
from orcia_core.workflows.schemas_v2 import WorkflowDefinitionV2


def is_test_cassette_active(app_or_request: FastAPI | Request) -> bool:
    """Return True only when explicit test cassette mode or a test-double gateway is active."""
    if is_cassette_llm_enabled():
        return True
    app = app_or_request.app if isinstance(app_or_request, Request) else app_or_request
    gw = getattr(app.state, "llm_gateway", None)
    return bool(gw is not None and getattr(gw, "is_cassette_adapter", False))


def _resolve_default_scope_uuid(app: FastAPI, workspace_id: str | None) -> str:
    if workspace_id and workspace_id != "scope-global":
        cleaned = workspace_id.removeprefix("scope-ws-").strip()
        try:
            return str(UUID(cleaned))
        except ValueError:
            pass
    auth = getattr(app.state, "auth_service", None)
    if auth is not None:
        workspaces = getattr(auth.evaluator, "workspaces", ())
        if workspaces:
            return str(workspaces[0].id)
    return "00000000-0000-7000-8000-000000000000"


def build_app_llm_endpoint_resolver(app: FastAPI) -> LlmEndpointResolver:
    """Build an app-scoped async `LlmEndpointConfig` resolver (`AD-21`, zero stale Request)."""

    async def _resolve(workspace_id: str | None) -> LlmEndpointConfig | None:
        if is_test_cassette_active(app):
            return None
        engine = getattr(app.state, "db_engine", None)
        auth = getattr(app.state, "auth_service", None)
        redis_client = getattr(app.state, "redis_client", None)
        snap = await get_valid_platform_setup_snapshot_async(app.state, redis_client=redis_client)
        hub_svc = getattr(app.state, "ai_models_hub_service", None)
        accostage_svc = getattr(app.state, "accostage_service", None)
        resolved_env = (
            getattr(accostage_svc, "orcia_env", None)
            or os.environ.get("ORCIA_ENV", "").strip()
            or "local"
        )
        scope_id = _resolve_default_scope_uuid(app, workspace_id)
        ep, refreshed_snap = await resolve_configured_llm_endpoint_from_sources(
            engine=engine,
            vault_cipher=getattr(auth, "vault_cipher", None),
            snapshot=snap,
            hub_svc=hub_svc,
            resolved_scope_id=scope_id,
            requested_tier="medium",
            orcia_env=resolved_env,
            use_cassette=False,
            snapshot_loader=lambda eng, env: load_platform_setup_state_from_postgres18(
                eng, orcia_env=env
            ),
        )
        if refreshed_snap is not None:
            await set_cached_platform_setup_snapshot_async(
                app.state, refreshed_snap, redis_client=redis_client
            )
        return ep

    return _resolve


async def resolve_workspace_datasource_uris(
    request: Request,
    *,
    workspace_id: str | None,
    user: UserIdentity,
) -> list[str]:
    """Resolve attached datasource URIs from PG18 `workspace_datasources` or evaluator."""
    engine = get_configured_db_engine(request)
    cleaned_ws = (
        workspace_id.removeprefix("scope-ws-").strip()
        if workspace_id and workspace_id != "scope-global"
        else None
    )
    uris: list[str] = []
    if engine is not None:
        if cleaned_ws:
            records = await list_workspace_datasources_from_postgres18(
                engine, workspace_id=cleaned_ws
            )
            uris.extend(r.uri for r in records if r.uri)
        else:
            auth_svc = get_auth_service(request)
            accessible = auth_svc.evaluator.resolve_accessible_workspaces(user)
            ws_ids: list[UUID] = []
            for access in accessible:
                try:
                    if access.workspace.id:
                        ws_ids.append(UUID(str(access.workspace.id)))
                except (ValueError, TypeError, AttributeError):
                    continue
            if ws_ids:
                async with engine.connect() as conn:
                    rows = (
                        await conn.execute(
                            sa.text(
                                "SELECT uri FROM workspace_datasources "
                                "WHERE workspace_id = ANY(:ws_ids) "
                                "ORDER BY created_at ASC"
                            ),
                            {"ws_ids": ws_ids},
                        )
                    ).fetchall()
                uris.extend(str(r[0]) for r in rows if r[0])
        return list(dict.fromkeys(uris))

    auth_svc = get_auth_service(request)
    if cleaned_ws:
        ws = auth_svc.evaluator.get_workspace(cleaned_ws)
        if ws is not None:
            uris.extend(ds.uri for ds in ws.datasources if ds.uri)
    else:
        for access in auth_svc.evaluator.resolve_accessible_workspaces(user):
            uris.extend(ds.uri for ds in access.workspace.datasources if ds.uri)
    return list(dict.fromkeys(uris))


def has_meaningful_step_inputs(
    inputs: dict[str, Any] | None,
    workflow: WorkflowDefinitionV2 | None = None,
) -> bool:
    """Return True when caller supplied explicit non-default step inputs."""
    if not inputs:
        return False
    wf_title = (workflow.title if workflow is not None else "").strip()
    for key, val in inputs.items():
        if val is None:
            continue
        text = str(val).strip()
        if not text:
            continue
        if key == "objective" and wf_title and text == wf_title:
            continue
        return True
    return False


async def enforce_live_process_prerequisites(
    request: Request,
    *,
    user: UserIdentity,
    workspace_id: str | None,
    workflow: WorkflowDefinitionV2 | None = None,
    inputs: dict[str, Any] | None = None,
    explicit_resources: Sequence[str] = (),
) -> tuple[str, ...]:
    """Validate live LLM + attached datasources (or explicit inputs) and return resource URIs."""
    ds_uris = await resolve_workspace_datasource_uris(request, workspace_id=workspace_id, user=user)
    merged_resources = tuple(
        dict.fromkeys(
            [
                *(str(u).strip() for u in explicit_resources if str(u).strip()),
                *ds_uris,
            ]
        )
    )
    if is_test_cassette_active(request):
        return merged_resources

    resolver = build_app_llm_endpoint_resolver(request.app)
    endpoint = await resolver(workspace_id)
    if endpoint is None:
        raise ProcessModelNotConfiguredError(instance=str(request.url.path))

    if not merged_resources and not has_meaningful_step_inputs(inputs, workflow):
        raise ProcessDatasourcesRequiredError(instance=str(request.url.path))

    return merged_resources


__all__ = [
    "build_app_llm_endpoint_resolver",
    "enforce_live_process_prerequisites",
    "has_meaningful_step_inputs",
    "is_test_cassette_active",
    "resolve_workspace_datasource_uris",
]
