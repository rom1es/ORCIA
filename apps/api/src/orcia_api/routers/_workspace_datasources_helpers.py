"""RBAC, isolation, and serialization helpers for `workspace_datasources` router."""

from __future__ import annotations

import json
from typing import Any
from uuid import UUID

import sqlalchemy as sa
from fastapi import Request

from orcia_api.dependencies import get_auth_service, get_or_create_shared_db_engine
from orcia_api.dependencies._core_providers import is_pg_runtime_active
from orcia_api.routers._finops_scope_guards import sync_evaluator_topology_from_pg
from orcia_api.routers.auth import resolve_request_user
from orcia_api.schemas.enterprise_connectors import WorkspaceDatasourceItemResponse
from orcia_core.observability.logging import get_current_trace_id
from orcia_core.permissions import UserIdentity
from orcia_core.permissions.errors import (
    CodegraphWorkspaceLeadRequiredError,
    ObserverModeReadOnlyError,
    ScopeAccessDeniedError,
)
from orcia_core.permissions.workspace_sources_governance import (
    WorkspaceDatasourceRecord,
    can_manage_workspace_codegraph,
)


def trace_id_for_request(request: Request) -> str:
    """Return active W3C trace ID."""
    return str(getattr(request.state, "trace_id", None) or get_current_trace_id())


def pg_enabled() -> bool:
    """Return True when PG18 runtime is active."""
    return is_pg_runtime_active()


def resolve_datasources_user(request: Request, persona_key: str | None = None) -> UserIdentity:
    """Resolve authenticated caller from Bearer JWT or local persona."""
    has_bearer = bool(request.headers.get("Authorization"))
    effective_persona = (
        None
        if has_bearer
        else (persona_key or request.headers.get("x-orcia-persona", "").strip() or None)
    )
    return resolve_request_user(request, persona_key=effective_persona)


def enforce_datasource_mutation_access(
    request: Request, persona_key: str | None = None
) -> UserIdentity:
    """Reject observer headers/users before mutating workspace datasources."""
    access_mode_hdr = request.headers.get("x-orcia-access-mode", "").strip().upper()
    observer_hdr = request.headers.get("x-orcia-observer-mode", "").strip().lower()
    active_hat = request.headers.get("x-orcia-active-hat", "").strip().upper()
    if (
        access_mode_hdr == "READ_ONLY_OBSERVER"
        or observer_hdr in ("1", "true", "yes")
        or active_hat == "OBSERVER"
    ):
        raise ObserverModeReadOnlyError(instance=str(request.url.path))

    user = resolve_datasources_user(request, persona_key=persona_key)
    if user.platform_role == "OBSERVER":
        raise ObserverModeReadOnlyError(instance=str(request.url.path))
    return user


def _decode_settings_jsonb(raw_st: Any) -> dict[str, object]:
    if isinstance(raw_st, dict):
        return raw_st
    if isinstance(raw_st, str):
        try:
            decoded = json.loads(raw_st)
            if isinstance(decoded, dict):
                return decoded
        except ValueError:
            return {}
    return {}


async def enforce_personal_workspace_isolation(
    request: Request,
    user: UserIdentity,
    workspace_id: str,
    *,
    require_write: bool = False,
) -> None:
    """Enforce `PRIVATE_USER`, `CONFIDENTIAL_RESTRICTED`, and workspace RBAC confinement."""
    path = str(request.url.path)
    auth_svc = get_auth_service(request)
    await sync_evaluator_topology_from_pg(request, auth_svc)
    ws_ent = auth_svc.evaluator.get_workspace(workspace_id)
    if ws_ent is not None:
        if (
            ws_ent.ui_visibility_mode == "PRIVATE_USER" or ws_ent.personal_owner_user_id is not None
        ) and (
            not ws_ent.personal_owner_user_id or str(ws_ent.personal_owner_user_id) != str(user.id)
        ):
            raise ScopeAccessDeniedError(instance=path)
        access = auth_svc.evaluator.resolve_workspace_access(user, ws_ent.id)
        if access is None:
            raise ScopeAccessDeniedError(instance=path)
        if require_write and access.access_mode == "READ_ONLY_OBSERVER":
            raise ObserverModeReadOnlyError(instance=path)

    if pg_enabled() or getattr(request.app.state, "db_engine", None) is not None:
        try:
            UUID(workspace_id)
        except (ValueError, TypeError) as exc:
            raise ScopeAccessDeniedError(instance=path) from exc
        engine = get_or_create_shared_db_engine(request)
        async with engine.connect() as conn:
            row = (
                (
                    await conn.execute(
                        sa.text(
                            "SELECT visibility_mode, settings_jsonb FROM workspaces "
                            "WHERE id = CAST(:ws_id AS uuid)"
                        ),
                        {"ws_id": workspace_id},
                    )
                )
                .mappings()
                .first()
            )
            if row is None:
                raise ScopeAccessDeniedError(instance=path)
            st_dict = _decode_settings_jsonb(row.get("settings_jsonb"))
            ui_vis = str(st_dict.get("ui_visibility_mode") or "").strip()
            personal_owner = str(st_dict.get("personal_owner_user_id") or "").strip() or None
            if (ui_vis == "PRIVATE_USER" or personal_owner is not None) and (
                not personal_owner or personal_owner != str(user.id)
            ):
                raise ScopeAccessDeniedError(instance=path)
            db_vis = str(row.get("visibility_mode") or "STANDARD").strip().upper()
            if db_vis == "CONFIDENTIAL_RESTRICTED":
                mem_row = (
                    await conn.execute(
                        sa.text(
                            "SELECT access_mode FROM workspace_memberships "
                            "WHERE workspace_id = CAST(:ws_id AS uuid) "
                            "AND (user_id::text = :uid "
                            "OR (:ou_id != '' AND invited_org_unit_id::text = :ou_id)) "
                            "LIMIT 1"
                        ),
                        {
                            "ws_id": workspace_id,
                            "uid": str(user.id),
                            "ou_id": str(user.primary_org_unit_id or ""),
                        },
                    )
                ).first()
                if mem_row is None:
                    raise ScopeAccessDeniedError(instance=path)
                if require_write and str(mem_row[0] or "") == "READ_ONLY_OBSERVER":
                    raise ObserverModeReadOnlyError(instance=path)
    elif ws_ent is None:
        raise ScopeAccessDeniedError(instance=path)


def enforce_codegraph_access(request: Request, user: Any) -> None:
    """Enforce lead-level permissions for enabling or configuring Codegraph."""
    candidate_roles: set[str] = set()
    if getattr(user, "platform_role", None):
        candidate_roles.add(str(user.platform_role).upper())
    if hat := request.headers.get("x-orcia-active-hat"):
        candidate_roles.add(hat.strip().upper())
    if role_hdr := request.headers.get("x-orcia-role"):
        candidate_roles.add(role_hdr.strip().upper())

    if not can_manage_workspace_codegraph(candidate_roles):
        raise CodegraphWorkspaceLeadRequiredError(instance=str(request.url.path))


def serialize_datasource(rec: WorkspaceDatasourceRecord) -> WorkspaceDatasourceItemResponse:
    """Serialize `WorkspaceDatasourceRecord` into OpenAPI response model."""
    return WorkspaceDatasourceItemResponse(
        id=rec.id,
        workspace_id=rec.workspace_id,
        alias=rec.alias,
        scheme=rec.scheme,
        uri=rec.uri,
        connector_id=rec.connector_id,
        sync_identity_mode=rec.sync_identity_mode,
        service_account_id=rec.service_account_id,
        referent_user_id=rec.referent_user_id,
        sync_status=rec.sync_status,
        sync_status_reason=rec.sync_status_reason,
        created_at_iso=rec.created_at_iso,
        source_nature=rec.source_nature,
        sync_mode=rec.sync_mode,
        target_scope=rec.target_scope,
        target_ref=rec.target_ref,
        last_sync_at_iso=rec.last_sync_at_iso,
        last_probe_at_iso=rec.last_probe_at_iso,
        fingerprint_hash=rec.fingerprint_hash,
        freshness_status=rec.freshness_status,
        codegraph_enabled=rec.codegraph_enabled,
        codegraph_auth_mode=rec.codegraph_auth_mode,
        codegraph_owner_user_id=rec.codegraph_owner_user_id,
        codegraph_status=rec.codegraph_status,
        codegraph_status_reason=rec.codegraph_status_reason,
        codegraph_last_indexed_at_iso=rec.codegraph_last_indexed_at_iso,
        codegraph_head_sha=rec.codegraph_head_sha,
    )
