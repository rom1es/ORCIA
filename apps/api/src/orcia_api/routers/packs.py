"""Declarative Packs Registry, Import & Delete Router (`Story 31.2`, PG18 + SeaweedFS CAS)."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, Body, Depends, Path, Query, Request, Response

from orcia_api.dependencies import (
    get_pack_bundle_v2_repository,
    get_pack_cas_storage,
    get_pack_composer_service,
    get_pack_import_service,
)
from orcia_api.dependencies._core_providers import (
    get_configured_db_engine,
    is_pg_runtime_active,
)
from orcia_api.routers._pack_composer_helpers import execute_export_pack_zip_handler
from orcia_api.routers._packs_export_legacy_route import legacy_export_router
from orcia_api.routers._packs_router_helpers import (
    build_pack_summary_from_pg_row,
    enforce_pack_mutation_guard,
    evaluate_connector_requirement,
    parse_pack_import_payload,
    slots_to_required_connectors,
    trace_id_for,
)
from orcia_api.routers.auth import PROBLEM_RESPONSES
from orcia_api.schemas._pack_composer import PackExportRequest
from orcia_api.schemas.packs import (
    PackDeleteResponse,
    PackImportEntityCountsResponse,
    PackImportResponse,
)
from orcia_api.schemas.process_studio_v2 import (
    ConnectorRequirementHealthItemResponse,
    DeclarativePacksListResponse,
    PacksConnectorHealthResponse,
)
from orcia_connectors.adapters import get_default_enterprise_connectors
from orcia_core.bootstrap import list_enterprise_connectors_from_postgres18
from orcia_core.observability.logging import get_logger
from orcia_core.packs import (
    PackCasStoragePort,
    PackComposerService,
    PackImportService,
    SqlPackBundleV2Repository,
)
from orcia_core.permissions.enterprise_connectors import EnterpriseConnectorRecord

logger = get_logger("orcia.api.packs")
router = APIRouter(prefix="/api/v1/packs", tags=["Declarative Packs (Epic 15 / Epic 31)"])

PackRepoDep = Annotated[SqlPackBundleV2Repository, Depends(get_pack_bundle_v2_repository)]
PackImportDep = Annotated[PackImportService, Depends(get_pack_import_service)]
PackCasDep = Annotated[PackCasStoragePort | None, Depends(get_pack_cas_storage)]
PackComposerDep = Annotated[PackComposerService, Depends(get_pack_composer_service)]


async def _load_pg_connectors_by_kind(request: Request) -> dict[str, EnterpriseConnectorRecord]:
    if not is_pg_runtime_active(request):
        return {}
    engine = get_configured_db_engine(request)
    if engine is None:
        return {}
    try:
        rows = await list_enterprise_connectors_from_postgres18(engine)
        return {rec.connector_kind.lower(): rec for rec in rows}
    except Exception as exc:
        logger.warning("packs_pg_connectors_lookup_skipped", error_type=type(exc).__name__)
        return {}


async def _list_pg_bundles(repo: PackRepoDep) -> list[dict[str, object]]:
    if getattr(repo, "_engine", None) is None:
        return []
    return list(await repo.list_bundles_v2())


@router.get("", response_model=DeclarativePacksListResponse, responses=PROBLEM_RESPONSES)
async def list_declarative_packs(
    request: Request, repo: PackRepoDep
) -> DeclarativePacksListResponse:
    """List declarative packs strictly from PostgreSQL 18 with live connector healthchecks."""
    rows = await _list_pg_bundles(repo)
    connectors, pg_connectors = (
        get_default_enterprise_connectors(),
        await _load_pg_connectors_by_kind(request),
    )
    summaries = [await build_pack_summary_from_pg_row(r, connectors, pg_connectors) for r in rows]
    return DeclarativePacksListResponse(packs=summaries)


@router.get("/health", response_model=PacksConnectorHealthResponse, responses=PROBLEM_RESPONSES)
async def check_packs_connectors_health(
    request: Request, repo: PackRepoDep
) -> PacksConnectorHealthResponse:
    """Probe live connector health across all PostgreSQL 18 declarative packs."""
    rows = await _list_pg_bundles(repo)
    connectors, pg_connectors = (
        get_default_enterprise_connectors(),
        await _load_pg_connectors_by_kind(request),
    )
    seen_types: set[str] = set()
    items: list[ConnectorRequirementHealthItemResponse] = []
    for row in rows:
        raw_slots = row.get("declared_slots")
        slots = (
            [dict(s) for s in raw_slots if isinstance(s, dict)]
            if isinstance(raw_slots, list)
            else []
        )
        raw_manifest = row.get("manifest")
        meta = dict(raw_manifest) if isinstance(raw_manifest, dict) else {}
        for req_conn in slots_to_required_connectors(slots, meta):
            if req_conn.connector_type in seen_types:
                continue
            seen_types.add(req_conn.connector_type)
            items.append(await evaluate_connector_requirement(req_conn, connectors, pg_connectors))
    healthy_count = sum(1 for item in items if item.health.ok)
    total_count = len(items)
    return PacksConnectorHealthResponse(
        connectors=items,
        healthy_count=healthy_count,
        total_count=total_count,
        all_healthy=(healthy_count == total_count),
        checked_at_iso=datetime.now(UTC).isoformat().replace("+00:00", "Z"),
    )


@router.post(
    "/import",
    response_model=PackImportResponse,
    responses=PROBLEM_RESPONSES,
    openapi_extra={
        "requestBody": {
            "required": True,
            "content": {
                "application/json": {"schema": {"$ref": "#/components/schemas/PackImportRequest"}},
                "multipart/form-data": {
                    "schema": {
                        "type": "object",
                        "required": ["file"],
                        "properties": {
                            "file": {"type": "string", "format": "binary"},
                            "scope_type": {"type": "string"},
                            "scope_id": {"type": "string"},
                            "replace_draft": {"type": "boolean"},
                        },
                    }
                },
            },
        }
    },
)
async def import_declarative_pack_archive(
    request: Request,
    import_svc: PackImportDep,
) -> PackImportResponse:
    """Import a validated `.zip` APM pack into PostgreSQL 18 + SeaweedFS CAS."""
    user = enforce_pack_mutation_guard(request)
    zip_bytes, scope_type, scope_id, replace_draft = await parse_pack_import_payload(request)
    enforce_pack_mutation_guard(request, scope_type=scope_type, scope_id=scope_id)
    trace_id = trace_id_for(request)
    outcome = await import_svc.import_zip_bytes(
        zip_bytes,
        scope_type=scope_type,
        scope_id=scope_id,
        replace_draft=replace_draft,
        allow_system_kind=False,
        record_audit=True,
        actor_id=user.id,
        actor_email=user.email,
        trace_id=trace_id,
    )
    return PackImportResponse(
        bundle_id=outcome.bundle_id,
        pack_id=outcome.pack_id,
        slug=outcome.slug,
        name=outcome.name,
        version=outcome.version,
        bundle_kind=outcome.bundle_kind,
        scope_type=outcome.scope_type,
        scope_id=outcome.scope_id,
        status=outcome.status,
        archive_sha256=outcome.archive_sha256,
        cas_object_key=outcome.cas_object_key,
        idempotent_noop=outcome.idempotent_noop,
        counts=PackImportEntityCountsResponse(**outcome.counts),
        trace_id=trace_id,
    )


@router.delete(
    "/{bundle_id}",
    response_model=PackDeleteResponse,
    responses=PROBLEM_RESPONSES,
)
async def delete_declarative_pack_bundle(
    bundle_id: Annotated[str, Path(min_length=1, max_length=128)],
    request: Request,
    import_svc: PackImportDep,
) -> PackDeleteResponse:
    """Delete an unused non-SYSTEM pack bundle (`403`/`409` guarded)."""
    user = enforce_pack_mutation_guard(request)
    trace_id = trace_id_for(request)
    deleted = await import_svc.delete_bundle(
        bundle_id,
        allow_system_delete=False,
        record_audit=True,
        actor_id=user.id,
        actor_email=user.email,
        trace_id=trace_id,
    )
    return PackDeleteResponse(
        bundle_id=deleted["bundle_id"],
        slug=deleted["slug"],
        version=deleted["version"],
        deleted=True,
        trace_id=trace_id,
    )


router.include_router(legacy_export_router)


@router.post(
    "/{bundle_id}/export",
    responses={
        **PROBLEM_RESPONSES,
        200: {"content": {"application/zip": {"schema": {"type": "string", "format": "binary"}}}},
    },
)
async def export_declarative_pack_bundle_zip(
    bundle_id: Annotated[str, Path(min_length=1, max_length=128)],
    request: Request,
    composer_svc: PackComposerDep,
    payload: Annotated[PackExportRequest | None, Body()] = None,
    auto_include_dependencies: bool = Query(default=False),
    persona_key: Annotated[str | None, Query(min_length=1, max_length=64)] = None,
) -> Response:
    """Export any PG18 pack bundle as a scrubbed APM `.zip` with closure & leak guards."""
    auto_inc = auto_include_dependencies or (
        payload.auto_include_dependencies if payload else False
    )
    return await execute_export_pack_zip_handler(
        bundle_id,
        request=request,
        svc=composer_svc,
        auto_include_dependencies=auto_inc,
        persona_key=persona_key,
    )
