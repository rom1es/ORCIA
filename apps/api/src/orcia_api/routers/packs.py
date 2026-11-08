"""Declarative Packs Registry & Workspace Pack Export Router (`TASK-05`).

Exposes:
- `GET /api/v1/packs`: Lists hot-loaded declarative packs (`packs/<domain>/`) and evaluates
  real-time healthchecks for `required_connectors` via `orcia_connectors`.
- `POST /api/v1/packs/export/{workspace_id}`: Exports a workspace / pack into a `.zip` archive.
"""

from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, Query, Request, Response

from orcia_api.schemas.process_studio_v2 import (
    ConnectorRequirementHealthItemResponse,
    DeclarativePacksListResponse,
    DeclarativePackSummaryResponse,
)
from orcia_connectors.adapters import get_default_enterprise_connectors
from orcia_connectors.protocol import ConnectorHealthStatus
from orcia_core.packs.loader import DeclarativePackLoader, LoadedPackBundle, PackExporter

router = APIRouter(prefix="/api/v1/packs", tags=["Declarative Packs (Epic 15)"])


def _resolve_packs_root() -> Path:
    curr = Path(__file__).resolve()
    for parent in curr.parents:
        candidate = parent / "packs"
        if candidate.exists() and candidate.is_dir():
            return candidate
    return Path("packs")


def load_declarative_pack_bundles(request: Request) -> dict[str, LoadedPackBundle]:
    """Load declarative packs via `DeclarativePackLoader` and cache on `request.app.state`."""
    loader = DeclarativePackLoader(_resolve_packs_root())
    bundles = loader.load_all_packs()
    request.app.state.declarative_pack_bundles = bundles
    return bundles


@router.get("", response_model=DeclarativePacksListResponse)
async def list_declarative_packs(request: Request) -> DeclarativePacksListResponse:
    """Return all declarative packs from `packs/<domain>/` with real-time connector healthchecks."""
    bundles = load_declarative_pack_bundles(request)
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


@router.post("/export/{workspace_id}")
async def export_workspace_as_declarative_pack_zip(
    workspace_id: str,
    request: Request,
    pack_id: str = Query(default="orcia-pack-sdlc"),
) -> Response:
    """Export a workspace's active declarative pack into a downloadable `.zip` (`CA-10.2.2`)."""
    bundles = load_declarative_pack_bundles(request)
    bundle = bundles.get(pack_id) or next(iter(bundles.values()))
    zip_bytes = PackExporter.export_bundle_to_zip_bytes(bundle, workspace_id=workspace_id)
    filename = f"{bundle.manifest.slug}-{workspace_id}.zip"
    return Response(
        content=zip_bytes,
        media_type="application/zip",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
