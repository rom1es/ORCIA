"""Bounded Context 3: Federated Multi-Source Catalog, CAS SHA-256, 4-Layer Overrides & BMAD."""

from __future__ import annotations

import json
from typing import cast

from orcia_core.bootstrap.seeder import (
    DEFAULT_CATALOG_ITEM_SEEDS,
    DEFAULT_CUSTOMIZATION_OVERRIDE_SEEDS,
    DEFAULT_WORKFLOW_DEFINITION_SEEDS,
)
from orcia_core.catalog.bmad_adapter import BmadSkillPackAdapter
from orcia_core.catalog.cas_resolver import (
    CasObjectStoreProtocol,
    FederatedUriResolver,
    InMemoryCasObjectStore,
    S3BucketBackendProtocol,
    S3CompatibleCasObjectStore,
    compute_bytes_sha256,
    parse_federated_uri,
)
from orcia_core.catalog.models import (
    CATALOG_PROMOTION_ORDER,
    AdaptiveGatePolicy,
    ArchiveFormat,
    BmadSkillPackInput,
    BmadSkillStepFile,
    CasObjectEntry,
    CasResolutionResult,
    CatalogItemEntity,
    CatalogResourceType,
    CatalogSourceFormat,
    CustomizationOverrideEntity,
    EvaluationLensDefinition,
    FederatedScheme,
    OverrideLayer,
    ParsedFederatedUri,
    RunLockManifest,
    RunLockSourceTriplet,
    ScalarValue,
    WorkflowDefinitionEntity,
    WorkflowStepDefinition,
)
from orcia_core.catalog.override_merger import (
    EffectiveWorkflowMergeResult,
    FourLayerOverrideMerger,
    compute_workflow_sha256,
)
from orcia_core.catalog.service import FederatedCatalogService
from orcia_core.permissions.evaluator import MatrixPermissionEvaluator
from orcia_core.permissions.models import (
    CatalogAclEntry,
    CatalogVisibilityScope,
)

DOMAIN_NAME: str = "catalog"


def _parse_workflow_seed(
    seed_id: str,
    workspace_id: str | None,
    uri: str,
    version: str,
    source_format: str,
    steps_schema_json: str,
    adaptive_gate_policy: str,
    sha256: str,
) -> WorkflowDefinitionEntity:
    schema = json.loads(steps_schema_json)
    lenses = tuple(
        EvaluationLensDefinition(
            code=str(lens["code"]),
            weight=float(lens["weight"]),
            threshold=float(lens["threshold"]),
        )
        for lens in schema.get("lenses", [])
    )
    steps = tuple(
        WorkflowStepDefinition(
            step_key=str(s["step_key"]),
            title=str(s["title"]),
            instructions=str(s["instructions"]),
            human_authored_required=bool(s.get("human_authored_required", False)),
        )
        for s in schema.get("steps", [])
    )
    return WorkflowDefinitionEntity(
        id=seed_id,
        workspace_id=workspace_id,
        uri=uri,
        title=str(schema.get("title", uri)),
        description=str(schema.get("description", "")),
        version=version,
        source_format=cast(CatalogSourceFormat, source_format),
        adaptive_gate_policy=cast(AdaptiveGatePolicy, adaptive_gate_policy),
        scalars=dict(schema.get("scalars", {})),
        datasources=tuple(schema.get("datasources", [])),
        rules=tuple(schema.get("rules", [])),
        facts=tuple(schema.get("facts", [])),
        lenses=lenses,
        steps=steps,
        sha256=sha256,
    )


def build_default_federated_catalog_service(
    *,
    evaluator: MatrixPermissionEvaluator | None = None,
    cas_store: CasObjectStoreProtocol | None = None,
) -> FederatedCatalogService:
    """Build the reference Story 1.3 Federated Catalog Service with seeded items & overrides."""
    if evaluator is None:
        from orcia_core.permissions import build_default_auth_and_org_service

        active_evaluator = build_default_auth_and_org_service().evaluator
    else:
        active_evaluator = evaluator
    resolver = FederatedUriResolver(cas_store=cas_store)

    items: list[CatalogItemEntity] = []
    extra_acls: list[CatalogAclEntry] = []

    for seed in DEFAULT_CATALOG_ITEM_SEEDS:
        parsed = parse_federated_uri(seed.uri)
        item = CatalogItemEntity(
            id=seed.id,
            resource_id=seed.resource_id,
            uri=seed.uri,
            scheme=parsed.scheme,
            title=seed.title,
            description=seed.description,
            resource_type=cast(CatalogResourceType, seed.resource_type),
            source_format=cast(CatalogSourceFormat, seed.source_format),
            version=seed.version,
            sha256=seed.sha256,
            cas_key=seed.cas_key,
            visibility_scope=cast(CatalogVisibilityScope, seed.visibility_scope),
            owner_org_unit_id=seed.owner_org_unit_id,
            owner_workspace_id=seed.owner_workspace_id,
            content_payload=seed.content_payload,
        )
        items.append(item)
        if seed.resource_id not in ("res-blackbox-security-agent", "res-open-checkout-skill"):
            extra_acls.append(
                CatalogAclEntry(
                    id=seed.id,
                    resource_id=seed.resource_id,
                    resource_uri=seed.uri,
                    title=seed.title,
                    visibility_scope=cast(CatalogVisibilityScope, seed.visibility_scope),
                    owner_org_unit_id=seed.owner_org_unit_id,
                    owner_workspace_id=seed.owner_workspace_id,
                    grantee_transverse_group="architecture-board",
                    can_discover=True,
                    can_execute=True,
                    can_read_source=True,
                    can_edit=True,
                    can_admin=True,
                    system_prompt_secret=seed.content_payload,
                )
            )

    workflows = tuple(
        _parse_workflow_seed(
            s.id,
            s.workspace_id,
            s.uri,
            s.version,
            s.source_format,
            s.steps_schema_json,
            s.adaptive_gate_policy,
            s.sha256,
        )
        for s in DEFAULT_WORKFLOW_DEFINITION_SEEDS
    )

    overrides: list[CustomizationOverrideEntity] = []
    for ovr_seed in DEFAULT_CUSTOMIZATION_OVERRIDE_SEEDS:
        manifest = json.loads(ovr_seed.override_manifest_json)
        lenses = tuple(
            EvaluationLensDefinition(
                code=str(lens["code"]),
                weight=float(lens["weight"]),
                threshold=float(lens["threshold"]),
            )
            for lens in manifest.get("lenses", [])
        )
        overrides.append(
            CustomizationOverrideEntity(
                id=ovr_seed.id,
                override_key=ovr_seed.override_key,
                target_uri=ovr_seed.target_uri,
                override_layer=cast(OverrideLayer, ovr_seed.override_layer),
                org_unit_id=ovr_seed.org_unit_id,
                workspace_id=ovr_seed.workspace_id,
                user_id=ovr_seed.user_id,
                scalars=dict(manifest.get("scalars", {})),
                datasources=tuple(manifest.get("datasources", [])),
                rules=tuple(manifest.get("rules", [])),
                facts=tuple(manifest.get("facts", [])),
                lenses=lenses,
                sha256=ovr_seed.sha256,
            )
        )

    return FederatedCatalogService(
        evaluator=active_evaluator,
        resolver=resolver,
        catalog_items=tuple(items),
        workflows=workflows,
        overrides=tuple(overrides),
        extra_acls=tuple(extra_acls),
    )


__all__ = [
    "CATALOG_PROMOTION_ORDER",
    "DOMAIN_NAME",
    "AdaptiveGatePolicy",
    "ArchiveFormat",
    "BmadSkillPackAdapter",
    "BmadSkillPackInput",
    "BmadSkillStepFile",
    "CasObjectEntry",
    "CasObjectStoreProtocol",
    "CasResolutionResult",
    "CatalogItemEntity",
    "CatalogResourceType",
    "CatalogSourceFormat",
    "CustomizationOverrideEntity",
    "EffectiveWorkflowMergeResult",
    "EvaluationLensDefinition",
    "FederatedCatalogService",
    "FederatedScheme",
    "FederatedUriResolver",
    "FourLayerOverrideMerger",
    "InMemoryCasObjectStore",
    "OverrideLayer",
    "ParsedFederatedUri",
    "RunLockManifest",
    "RunLockSourceTriplet",
    "S3BucketBackendProtocol",
    "S3CompatibleCasObjectStore",
    "ScalarValue",
    "WorkflowDefinitionEntity",
    "WorkflowStepDefinition",
    "build_default_federated_catalog_service",
    "compute_bytes_sha256",
    "compute_workflow_sha256",
    "parse_federated_uri",
]
