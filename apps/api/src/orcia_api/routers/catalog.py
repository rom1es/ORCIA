"""Federated Catalog, CAS SHA-256, 4-Layer Overrides & BMAD Adapter Router (Story 1.3)."""

from __future__ import annotations

from fastapi import APIRouter, Path, Query, Request

from orcia_api.dependencies import get_catalog_service
from orcia_api.routers.auth import PROBLEM_RESPONSES, resolve_request_user
from orcia_api.schemas.catalog import (
    BmadSkillPackImportRequest,
    BmadSkillPackImportResponse,
    CasObjectResponse,
    CatalogItemResponse,
    CatalogItemsListResponse,
    CatalogPromoteRequest,
    CatalogPromoteResponse,
    CatalogUriResolveRequest,
    CatalogUriResolveResponse,
    EffectiveWorkflowResolveRequest,
    EffectiveWorkflowResolveResponse,
    EvaluationLensItem,
    RunLockManifestItem,
    RunLockSourceTripletItem,
    WorkflowDefinitionResponseItem,
    WorkflowStepItem,
)
from orcia_core.catalog import (
    BmadSkillPackInput,
    BmadSkillStepFile,
    CatalogItemEntity,
    FederatedScheme,
    SeaweedFsObjectStorageAdapter,
    SeaweedFsS3HttpBackend,
    WorkflowDefinitionEntity,
)
from orcia_core.observability.logging import get_current_trace_id
from orcia_core.permissions import CatalogVisibilityScope, EffectiveResourcePermissions

router = APIRouter(prefix="/api/v1", tags=["federated-catalog"])


def _trace(request: Request) -> str:
    return str(getattr(request.state, "trace_id", None) or get_current_trace_id())


def _get_optional_seaweedfs_adapter(request: Request) -> SeaweedFsObjectStorageAdapter | None:
    """Return `SeaweedFsObjectStorageAdapter` when configured on `app.state`."""
    adapter: SeaweedFsObjectStorageAdapter | None = getattr(
        request.app.state, "seaweedfs_storage_adapter", None
    )
    if adapter is not None:
        return adapter
    s3_endpoint: str | None = getattr(request.app.state, "seaweedfs_endpoint_url", None)
    if s3_endpoint:
        backend = SeaweedFsS3HttpBackend(endpoint_url=s3_endpoint)
        adapter = SeaweedFsObjectStorageAdapter(backend=backend)
        request.app.state.seaweedfs_storage_adapter = adapter
        return adapter
    return None


def _serialize_catalog_item(
    item: CatalogItemEntity, effective: EffectiveResourcePermissions
) -> CatalogItemResponse:
    return CatalogItemResponse(
        id=item.id,
        resource_id=item.resource_id,
        uri=item.uri,
        scheme=item.scheme,
        title=item.title,
        description=item.description,
        resource_type=item.resource_type,
        source_format=item.source_format,
        version=item.version,
        sha256=item.sha256,
        sha256_short=item.sha256_short,
        cas_key=item.cas_key,
        visibility_scope=effective.visibility_scope,
        granted_permissions=list(effective.granted_permissions),
        source_masked=effective.source_masked,
    )


def _serialize_workflow_def(wf: WorkflowDefinitionEntity) -> WorkflowDefinitionResponseItem:
    return WorkflowDefinitionResponseItem(
        id=wf.id,
        workspace_id=wf.workspace_id,
        uri=wf.uri,
        title=wf.title,
        description=wf.description,
        version=wf.version,
        source_format=wf.source_format,
        adaptive_gate_policy=wf.adaptive_gate_policy,
        scalars=dict(wf.scalars),
        datasources=list(wf.datasources),
        rules=list(wf.rules),
        facts=list(wf.facts),
        lenses=[
            EvaluationLensItem(code=lens.code, weight=lens.weight, threshold=lens.threshold)
            for lens in wf.lenses
        ],
        steps=[
            WorkflowStepItem(
                step_key=s.step_key,
                title=s.title,
                instructions=s.instructions,
                human_authored_required=s.human_authored_required,
            )
            for s in wf.steps
        ],
        sha256=wf.sha256,
    )


@router.get(
    "/catalog/items",
    response_model=CatalogItemsListResponse,
    summary="List Federated Catalog items filtered by RBAC, URI scheme, and publication scope",
    responses=PROBLEM_RESPONSES,
)
async def list_catalog_items(
    request: Request,
    persona_key: str | None = Query(default=None, min_length=1, max_length=64),
    workspace_id: str | None = Query(default=None, min_length=1, max_length=128),
    scheme: FederatedScheme | None = None,
    visibility_scope: CatalogVisibilityScope | None = None,
) -> CatalogItemsListResponse:
    """Return discoverable Federated Catalog resources with `uri-badge` metadata."""
    user = resolve_request_user(request, persona_key=persona_key)
    rows = get_catalog_service(request).list_catalog_items(
        user, workspace_id=workspace_id, scheme=scheme, visibility_scope=visibility_scope
    )
    return CatalogItemsListResponse(
        items=[_serialize_catalog_item(item, eff) for item, eff in rows],
        trace_id=_trace(request),
    )


@router.post(
    "/catalog/items/{resource_id}/promote",
    response_model=CatalogPromoteResponse,
    summary="Promote a Catalog resource along the hierarchical publication lifecycle",
    responses=PROBLEM_RESPONSES,
)
async def promote_catalog_item(
    payload: CatalogPromoteRequest,
    request: Request,
    resource_id: str = Path(..., min_length=1, max_length=128),
    persona_key: str | None = Query(default=None, min_length=1, max_length=64),
) -> CatalogPromoteResponse:
    """Promote `resource_id` visibility scope (`ScopeAccessGuard` enforced)."""
    user = resolve_request_user(request, persona_key=persona_key)
    svc = get_catalog_service(request)
    inst = str(request.url.path)
    previous_scope = svc.get_catalog_item(resource_id, instance=inst).visibility_scope
    updated, eff = svc.promote_catalog_item(
        user, resource_id, payload.target_scope, workspace_id=payload.workspace_id, instance=inst
    )
    return CatalogPromoteResponse(
        item=_serialize_catalog_item(updated, eff),
        previous_scope=previous_scope,
        trace_id=_trace(request),
    )


@router.post(
    "/catalog/resolve",
    response_model=CatalogUriResolveResponse,
    summary="Resolve a federated URI into immutable `cas/<sha256>` cache (< 50 ms)",
    responses=PROBLEM_RESPONSES,
)
async def resolve_federated_uri(
    payload: CatalogUriResolveRequest,
    request: Request,
    persona_key: str | None = Query(default=None, min_length=1, max_length=64),
) -> CatalogUriResolveResponse:
    """Resolve `payload.uri` on the fly into immutable `cas/<sha256>` storage."""
    resolve_request_user(request, persona_key=persona_key)
    res = get_catalog_service(request).resolver.resolve(
        payload.uri, expected_sha256=payload.expected_sha256
    )
    seaweed = _get_optional_seaweedfs_adapter(request)
    if seaweed is not None:
        seaweed.put_bytes(
            cas_key=res.cas_key,
            sha256=res.sha256,
            source_uri=res.uri,
            content_bytes=res.content_text.encode("utf-8"),
            content_type="text/plain; charset=utf-8",
        )
    return CatalogUriResolveResponse(
        uri=res.uri,
        scheme=res.scheme,
        resolved_version=res.resolved_version,
        sha256=res.sha256,
        cas_key=res.cas_key,
        cache_hit=res.cache_hit,
        resolution_ms=res.resolution_ms,
        content_text=res.content_text,
        trace_id=_trace(request),
    )


@router.get(
    "/cas/{sha256}",
    response_model=CasObjectResponse,
    summary="Fetch an immutable Content-Addressable Storage object by `cas/<sha256>` digest",
    responses=PROBLEM_RESPONSES,
)
async def get_cas_object(
    request: Request,
    sha256: str = Path(..., min_length=64, max_length=64, pattern=r"^[0-9a-fA-F]{64}$"),
    persona_key: str | None = Query(default=None, min_length=1, max_length=64),
) -> CasObjectResponse:
    """Retrieve an immutable object from `cas/<sha256>` verifying SHA-256 integrity."""
    resolve_request_user(request, persona_key=persona_key)
    seaweed = _get_optional_seaweedfs_adapter(request)
    if seaweed is not None:
        s3_entry = seaweed.get_bytes(f"cas/{sha256}")
        if s3_entry is not None:
            return CasObjectResponse(
                sha256=s3_entry.sha256,
                cas_key=s3_entry.cas_key,
                content_type=s3_entry.content_type,
                content_text=s3_entry.content_bytes.decode("utf-8"),
                trace_id=_trace(request),
            )
    entry = get_catalog_service(request).resolver.get_cas_entry(
        sha256, instance=str(request.url.path)
    )
    return CasObjectResponse(
        sha256=entry.sha256,
        cas_key=entry.cas_key,
        content_type=entry.content_type,
        content_text=entry.content_text,
        trace_id=_trace(request),
    )


@router.post(
    "/catalog/workflows/resolve-effective",
    response_model=EffectiveWorkflowResolveResponse,
    summary="Merge 4 override layers (Base -> Team -> Workspace -> User) and generate run-lock",
    responses=PROBLEM_RESPONSES,
)
async def resolve_effective_workflow(
    payload: EffectiveWorkflowResolveRequest,
    request: Request,
    persona_key: str | None = Query(default=None, min_length=1, max_length=64),
) -> EffectiveWorkflowResolveResponse:
    """Execute deterministic 4-layer merge without mutating base workflow."""
    user = resolve_request_user(request, persona_key=persona_key)
    merged = get_catalog_service(request).resolve_effective_workflow(
        user,
        workflow_uri=payload.workflow_uri,
        workspace_id=payload.workspace_id,
        instance=str(request.url.path),
    )
    rl = merged.run_lock
    return EffectiveWorkflowResolveResponse(
        base_workflow=_serialize_workflow_def(merged.base_workflow),
        effective_workflow=_serialize_workflow_def(merged.effective_workflow),
        applied_override_keys=list(merged.applied_override_keys),
        run_lock=RunLockManifestItem(
            workspace_id=rl.workspace_id,
            workflow_uri=rl.workflow_uri,
            workflow_version=rl.workflow_version,
            workflow_sha256=rl.workflow_sha256,
            effective_workflow_sha256=rl.effective_workflow_sha256,
            applied_override_keys=list(rl.applied_override_keys),
            sources=[
                RunLockSourceTripletItem(
                    alias=s.alias,
                    scheme=s.scheme,
                    uri=s.uri,
                    resolved_version=s.resolved_version,
                    sha256=s.sha256,
                    cas_key=s.cas_key,
                )
                for s in rl.sources
            ],
            manifest_sha256=rl.manifest_sha256,
        ),
        trace_id=_trace(request),
    )


@router.post(
    "/catalog/bmad-packs/import",
    response_model=BmadSkillPackImportResponse,
    summary="Losslessly import a BMAD Skill Pack (SKILL.md + customize.toml) into ORCIA",
    responses=PROBLEM_RESPONSES,
)
async def import_bmad_skill_pack(
    payload: BmadSkillPackImportRequest,
    request: Request,
    persona_key: str | None = Query(default=None, min_length=1, max_length=64),
) -> BmadSkillPackImportResponse:
    """Convert a BMAD skill pack via `BmadSkillPackAdapter` and pin it in `cas/<sha256>`."""
    user = resolve_request_user(request, persona_key=persona_key)
    pack_input = BmadSkillPackInput(
        uri=payload.uri,
        skill_markdown=payload.skill_markdown,
        customize_toml=payload.customize_toml,
        steps=tuple(
            BmadSkillStepFile(filename=s.filename, content_markdown=s.content_markdown)
            for s in payload.steps
        ),
        workspace_id=payload.workspace_id,
        owner_org_unit_id=user.primary_org_unit_id,
    )
    item, wf_def, effective = get_catalog_service(request).import_bmad_skill_pack(
        user, pack_input, instance=str(request.url.path)
    )
    return BmadSkillPackImportResponse(
        catalog_item=_serialize_catalog_item(item, effective),
        workflow_definition=_serialize_workflow_def(wf_def),
        trace_id=_trace(request),
    )
