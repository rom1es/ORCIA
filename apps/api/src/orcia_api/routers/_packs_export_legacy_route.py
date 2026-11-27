"""Hardened legacy `/api/v1/packs/export/{workspace_id}` sub-router (`Story 31.2 / 31.5`)."""

from __future__ import annotations

import io
import re
import zipfile
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request, Response

from orcia_api.dependencies import (
    get_auth_service,
    get_pack_bundle_v2_repository,
    get_pack_cas_storage,
    get_pack_composer_service,
)
from orcia_api.dependencies._core_providers import (
    get_configured_db_engine,
    is_pg_runtime_active,
)
from orcia_api.routers._finops_scope_guards import sync_evaluator_topology_from_pg
from orcia_api.routers._pack_composer_helpers import enforce_composer_scope_access
from orcia_api.routers._packs_router_helpers import (
    enforce_pack_mutation_guard,
    synthesize_zip_from_pg_row,
)
from orcia_api.routers._workspace_packs_guards import enforce_workspace_packs_access
from orcia_api.routers.auth import PROBLEM_RESPONSES
from orcia_core.packs import (
    PackBundleNotFoundError,
    PackCasStoragePort,
    PackComposerService,
    SqlPackBundleV2Repository,
    load_tenant_infra_identifiers_conn,
    scan_rendered_files_for_leaks,
)
from orcia_core.permissions.errors import ScopeAccessDeniedError

legacy_export_router = APIRouter(responses=PROBLEM_RESPONSES)
PackRepoDep = Annotated[SqlPackBundleV2Repository | None, Depends(get_pack_bundle_v2_repository)]
PackCasDep = Annotated[PackCasStoragePort | None, Depends(get_pack_cas_storage)]
PackComposerDep = Annotated[PackComposerService, Depends(get_pack_composer_service)]


@legacy_export_router.post(
    "/export/{workspace_id}",
    responses={
        **PROBLEM_RESPONSES,
        200: {"content": {"application/zip": {"schema": {"type": "string", "format": "binary"}}}},
    },
)
async def export_workspace_as_declarative_pack_zip(
    workspace_id: str,
    request: Request,
    repo: PackRepoDep,
    cas_storage: PackCasDep,
    composer_svc: PackComposerDep,
    pack_id: str = Query(default="orcia-pack-sdlc"),
) -> Response:
    """Export a PG18 / CAS pack bundle with ScopeAccessGuard, closure & leak scanning."""
    user = enforce_pack_mutation_guard(request)
    auth_svc = get_auth_service(request)
    await sync_evaluator_topology_from_pg(request, auth_svc)
    cleaned_ws = workspace_id.strip().removeprefix("scope-ws-").strip()
    ws = auth_svc.evaluator.get_workspace(cleaned_ws)
    is_admin = user.platform_role == "PLATFORM_ADMIN" or "PLATFORM_ADMIN" in user.roles
    if ws is not None:
        await enforce_workspace_packs_access(request, ws.id, require_write=False)
    elif not is_admin:
        raise ScopeAccessDeniedError(instance=str(request.url.path))
    else:
        try:
            UUID(cleaned_ws)
            if is_pg_runtime_active(request):
                await enforce_workspace_packs_access(request, cleaned_ws, require_write=False)
        except ValueError:
            pass
    all_rows = (
        list(await repo.list_bundles_v2())
        if repo is not None and getattr(repo, "_engine", None) is not None
        else []
    )
    row = next(
        (r for r in all_rows if r.get("pack_id") == pack_id or r.get("slug") == pack_id),
        None,
    )
    if row is None:
        raise PackBundleNotFoundError(
            detail_override=f"No declarative pack bundle found for {pack_id!r}.",
            instance=str(request.url.path),
        )
    if str(row.get("scope_type") or "GLOBAL").upper() != "GLOBAL":
        await enforce_composer_scope_access(
            request,
            scope_type=str(row["scope_type"]),
            scope_id=str(row["scope_id"]),
            require_write=False,
        )
    zip_bytes: bytes | None = None
    if is_pg_runtime_active(request) and row.get("id") and str(row.get("bundle_kind")) != "SYSTEM":
        zip_bytes = (
            await composer_svc.export_bundle(str(row["id"]), instance=str(request.url.path))
        ).zip_bytes
    else:
        cas_key = str(row["cas_object_key"]) if row.get("cas_object_key") else None
        if cas_key and cas_storage is not None:
            zip_bytes = await cas_storage.get_archive_zip(cas_key)
        if zip_bytes is None:
            zip_bytes = synthesize_zip_from_pg_row(row)
        eng = get_configured_db_engine(request)
        if eng is not None:
            with zipfile.ZipFile(io.BytesIO(zip_bytes), "r") as zf:
                scanned_files = {n: zf.read(n) for n in zf.namelist() if not n.endswith("/")}
            async with eng.connect() as conn:
                infra = await load_tenant_infra_identifiers_conn(conn)
            scan_rendered_files_for_leaks(scanned_files, infra, instance=str(request.url.path))
    safe_ws = re.sub(r"[^A-Za-z0-9_.-]+", "-", workspace_id).strip("-") or "workspace"
    slug = str(row.get("slug") or "pack")
    filename = f"{slug}-{safe_ws[:64]}.zip"
    return Response(
        content=zip_bytes,
        media_type="application/zip",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


__all__ = ["legacy_export_router"]
