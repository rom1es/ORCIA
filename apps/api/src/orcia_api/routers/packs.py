"""Declarative Packs Registry & Workspace Pack Export Router (`TASK-05`, `Story 22.5`).

Exposes:
- `GET /api/v1/packs`: Lists hot-loaded declarative packs (`packs/<domain>/`), synchronizes
  them idempotently into PostgreSQL 18 `declarative_pack_bundles`, and evaluates real-time
  healthchecks for `required_connectors` via `orcia_connectors`.
- `POST /api/v1/packs/export/{workspace_id}`: Synchronizes packs into PostgreSQL 18 and
  exports a workspace / pack into a `.zip` archive.
"""

from __future__ import annotations

import re

from fastapi import APIRouter, Query, Request, Response

from orcia_api.dependencies._core_providers import (
    get_configured_db_engine,
    is_pg_runtime_active,
)
from orcia_api.routers._settings_helpers import enforce_not_observer_mode
from orcia_api.routers.auth import PROBLEM_RESPONSES, resolve_request_user
from orcia_api.schemas.process_studio_v2 import (
    ConnectorRequirementHealthItemResponse,
    DeclarativePacksListResponse,
    DeclarativePackSummaryResponse,
)
from orcia_connectors.adapters import get_default_enterprise_connectors
from orcia_connectors.protocol import ConnectorHealthStatus
from orcia_core.bootstrap import upsert_declarative_pack_bundles_sql
from orcia_core.observability.logging import get_logger
from orcia_core.packs.loader import (
    DeclarativePackLoader,
    LoadedPackBundle,
    PackExporter,
    resolve_default_packs_root,
)
from orcia_core.permissions.errors import ObserverModeReadOnlyError
from orcia_core.workflows import upsert_vsm_definitions_v2_sql

logger = get_logger("orcia.api.packs")
router = APIRouter(prefix="/api/v1/packs", tags=["Declarative Packs (Epic 15)"])


def load_declarative_pack_bundles(request: Request) -> dict[str, LoadedPackBundle]:
    """Load declarative packs via `DeclarativePackLoader` and cache on `request.app.state`."""
    loader = DeclarativePackLoader(resolve_default_packs_root())
    bundles = loader.load_all_packs()
    request.app.state.declarative_pack_bundles = bundles
    return bundles


async def sync_declarative_pack_bundles_to_pg(
    request: Request,
    bundles: dict[str, LoadedPackBundle],
) -> None:
    """Idempotently upsert loaded pack bundles into PostgreSQL 18 `declarative_pack_bundles`."""
    if not is_pg_runtime_active(request):
        return
    engine = get_configured_db_engine(request)
    if engine is None:
        return
    try:
        await upsert_declarative_pack_bundles_sql(engine, bundles)
        await upsert_vsm_definitions_v2_sql(engine, bundles)
    except Exception as exc:
        logger.warning(
            "declarative_pack_bundles_pg_sync_failed",
            error_type=type(exc).__name__,
            error=str(exc),
        )


@router.get("", response_model=DeclarativePacksListResponse, responses=PROBLEM_RESPONSES)
async def list_declarative_packs(request: Request) -> DeclarativePacksListResponse:
    """Return all declarative packs from `packs/<domain>/` with PG18 sync & healthchecks."""
    bundles = load_declarative_pack_bundles(request)
    await sync_declarative_pack_bundles_to_pg(request, bundles)
    connectors = get_default_enterprise_connectors()
    summaries: list[DeclarativePackSummaryResponse] = []

    for bundle in bundles.values():
        m = bundle.manifest
        health_items: list[ConnectorRequirementHealthItemResponse] = []
        for req_conn in m.required_connectors:
            adapter = connectors.get(req_conn.connector_type)
            if adapter is not None:
                health = await adapter.healthcheck()
            else:
                health = ConnectorHealthStatus(
                    connector_type=req_conn.connector_type,
                    ok=False,
                    latency_ms=0,
                    error_message="Connector not registered",
                )
            health_items.append(
                ConnectorRequirementHealthItemResponse(
                    connector_type=req_conn.connector_type,
                    required_scopes=req_conn.required_scopes,
                    used_for=req_conn.used_for,
                    health=health,
                )
            )

        summaries.append(
            DeclarativePackSummaryResponse(
                id=m.id,
                slug=m.slug,
                name=m.name,
                version=m.version,
                description=m.description,
                rbac_namespace=m.rbac_namespace,
                bundle_sha256=bundle.bundle_sha256,
                agents_count=len(bundle.agents_markdown),
                skills_count=len(bundle.skills_markdown),
                gates_count=len(bundle.gates_specs),
                vsm_count=len(bundle.vsm_specs),
                workflows_count=len(bundle.workflows),
                agents_slugs=sorted(bundle.agents_markdown.keys()),
                skills_slugs=sorted(bundle.skills_markdown.keys()),
                gates_slugs=sorted(bundle.gates_specs.keys()),
                required_connectors=m.required_connectors,
                connector_health=health_items,
                quick_actions=m.quick_actions,
            )
        )

    return DeclarativePacksListResponse(packs=summaries)


@router.post(
    "/export/{workspace_id}",
    responses={
        **PROBLEM_RESPONSES,
        200: {
            "content": {
                "application/zip": {
                    "schema": {"type": "string", "format": "binary"},
                }
            },
            "description": "Downloadable declarative pack .zip archive",
        },
    },
)
async def export_workspace_as_declarative_pack_zip(
    workspace_id: str,
    request: Request,
    pack_id: str = Query(default="orcia-pack-sdlc"),
) -> Response:
    """Sync packs to PG18 and export a workspace's declarative pack into `.zip` (`CA-10.2.2`)."""
    enforce_not_observer_mode(request)
    if request.headers.get("Authorization"):
        user = resolve_request_user(request)
        if user.platform_role == "OBSERVER":
            raise ObserverModeReadOnlyError(instance=str(request.url.path))
    bundles = load_declarative_pack_bundles(request)
    await sync_declarative_pack_bundles_to_pg(request, bundles)
    bundle = bundles.get(pack_id) or next(iter(bundles.values()))
    zip_bytes = PackExporter.export_bundle_to_zip_bytes(bundle, workspace_id=workspace_id)
    safe_ws = re.sub(r"[^A-Za-z0-9_.-]+", "-", workspace_id).strip("-") or "workspace"
    filename = f"{bundle.manifest.slug}-{safe_ws[:64]}.zip"
    return Response(
        content=zip_bytes,
        media_type="application/zip",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
