"""Recursive `run-lock.json` sub-workflow locking & manifest builders (`Story 3.1`, `AD-5`)."""

from __future__ import annotations

import json

from orcia_core.catalog.cas_resolver import FederatedUriResolver, compute_bytes_sha256
from orcia_core.catalog.models import (
    CustomizationOverrideEntity,
    RunLockSourceTriplet,
    WorkflowDefinitionEntity,
    WorkflowStepDefinition,
)
from orcia_core.catalog.override_merger import FourLayerOverrideMerger
from orcia_core.orchestration.errors import (
    ResourceNotFoundError,
    SubWorkflowCycleDetectedError,
    SubWorkflowMaxDepthExceededError,
)
from orcia_core.orchestration.models import (
    MAX_SUB_WORKFLOW_NESTING_DEPTH,
    RecursiveRunLockManifest,
    SubWorkflowLockEntry,
    WorkflowAsCodeDefinition,
    WorkflowRunEntity,
)
from orcia_core.permissions.models import OrgUnitNode, WorkspaceEntity


def to_catalog_workflow(wf: WorkflowAsCodeDefinition) -> WorkflowDefinitionEntity:
    """Project `WorkflowAsCodeDefinition` onto `WorkflowDefinitionEntity` for override merging."""
    return WorkflowDefinitionEntity(
        id=wf.id,
        workspace_id=wf.workspace_id,
        uri=wf.uri,
        title=wf.title,
        description=wf.description,
        version=wf.version,
        source_format="ORCIA",
        adaptive_gate_policy=wf.adaptive_gate_policy,
        scalars=dict(wf.scalars),
        datasources=wf.datasources,
        rules=wf.rules,
        facts=wf.facts,
        lenses=(),
        steps=tuple(
            WorkflowStepDefinition(
                step_key=s.step_key,
                title=s.title,
                instructions=s.instructions,
                human_authored_required=s.human_authored_required,
            )
            for s in wf.steps
        ),
        sha256=wf.sha256,
    )


def build_recursive_sub_locks_helper(
    wf: WorkflowAsCodeDefinition,
    *,
    workflows_by_uri: dict[str, WorkflowAsCodeDefinition],
    org_units: tuple[OrgUnitNode, ...],
    overrides: tuple[CustomizationOverrideEntity, ...],
    resolver: FederatedUriResolver,
    workspace: WorkspaceEntity,
    user_id: str | None,
    depth: int,
    call_stack: tuple[str, ...],
    instance: str | None = None,
) -> tuple[SubWorkflowLockEntry, ...]:
    """Recursively pin child `SUB_WORKFLOW` overrides and source digests (`FR-30`)."""
    entries: list[SubWorkflowLockEntry] = []
    for step in wf.steps:
        if step.step_type != "SUB_WORKFLOW" or not step.sub_workflow_uri:
            continue
        target_uri = step.sub_workflow_uri
        next_depth = depth + 1
        if target_uri in call_stack:
            raise SubWorkflowCycleDetectedError(
                detail_code="ERR_RUN_LOCK_SUB_WORKFLOW_CYCLE",
                detail_params={"chain": " -> ".join((*call_stack, target_uri))},
                instance=instance,
            )
        if next_depth > MAX_SUB_WORKFLOW_NESTING_DEPTH:
            raise SubWorkflowMaxDepthExceededError(
                detail_code="ERR_RUN_LOCK_SUB_WORKFLOW_DEPTH",
                detail_params={
                    "depth": next_depth,
                    "max_depth": MAX_SUB_WORKFLOW_NESTING_DEPTH,
                    "uri": target_uri,
                },
                instance=instance,
            )
        child_wf = workflows_by_uri.get(target_uri)
        if child_wf is None:
            raise ResourceNotFoundError(
                detail_code="ERR_RUN_LOCK_SUB_WORKFLOW_MISSING",
                detail_params={"uri": target_uri},
                instance=instance,
            )
        merged_child = FourLayerOverrideMerger.merge_and_lock(
            base_workflow=to_catalog_workflow(child_wf),
            org_units=org_units,
            workspace=workspace,
            user_id=user_id,
            overrides=overrides,
            resolver=resolver,
        )
        nested_locks = build_recursive_sub_locks_helper(
            child_wf,
            workflows_by_uri=workflows_by_uri,
            org_units=org_units,
            overrides=overrides,
            resolver=resolver,
            workspace=workspace,
            user_id=user_id,
            depth=next_depth,
            call_stack=(*call_stack, target_uri),
            instance=instance,
        )
        entries.append(
            SubWorkflowLockEntry(
                step_key=step.step_key,
                workflow_uri=child_wf.uri,
                workflow_version=child_wf.version,
                workflow_sha256=child_wf.sha256,
                effective_workflow_sha256=merged_child.effective_workflow.sha256,
                nesting_depth=next_depth,
                applied_override_keys=merged_child.applied_override_keys,
                sources=merged_child.run_lock.sources,
                sub_workflow_locks=nested_locks,
            )
        )
    return tuple(entries)


def assemble_recursive_run_lock(
    *,
    run_id: str,
    workspace: WorkspaceEntity,
    wf: WorkflowAsCodeDefinition,
    effective_workflow_sha256: str,
    applied_override_keys: tuple[str, ...],
    kb_snapshot_hash: str,
    sorted_sources: tuple[RunLockSourceTriplet, ...],
    sub_locks: tuple[SubWorkflowLockEntry, ...],
) -> RecursiveRunLockManifest:
    """Compute SHA-256 digest and assemble immutable `RecursiveRunLockManifest`."""
    overrides_sha256 = compute_bytes_sha256(json.dumps(list(applied_override_keys)).encode("utf-8"))
    manifest_payload = json.dumps(
        {
            "run_id": run_id,
            "workspace_id": workspace.id,
            "workflow_uri": wf.uri,
            "workflow_version": wf.version,
            "workflow_sha256": wf.sha256,
            "effective_workflow_sha256": effective_workflow_sha256,
            "overrides_sha256": overrides_sha256,
            "kb_snapshot_hash": kb_snapshot_hash,
            "applied_override_keys": list(applied_override_keys),
            "sources": [
                {
                    "alias": s.alias,
                    "scheme": s.scheme,
                    "uri": s.uri,
                    "resolved_version": s.resolved_version,
                    "sha256": s.sha256,
                    "cas_key": s.cas_key,
                }
                for s in sorted_sources
            ],
            "sub_workflow_locks": [sub.to_dict() for sub in sub_locks],
        },
        sort_keys=True,
    )
    return RecursiveRunLockManifest(
        run_id=run_id,
        workspace_id=workspace.id,
        workflow_uri=wf.uri,
        workflow_version=wf.version,
        workflow_sha256=wf.sha256,
        effective_workflow_sha256=effective_workflow_sha256,
        overrides_sha256=overrides_sha256,
        kb_snapshot_hash=kb_snapshot_hash,
        applied_override_keys=applied_override_keys,
        sources=sorted_sources,
        sub_workflow_locks=sub_locks,
        manifest_sha256=compute_bytes_sha256(manifest_payload.encode("utf-8")),
    )


def collect_step_lock_sources(
    wf: WorkflowAsCodeDefinition,
    base_sources: tuple[RunLockSourceTriplet, ...],
    resolver: FederatedUriResolver,
) -> tuple[RunLockSourceTriplet, ...]:
    """Resolve and deterministically sort all step agent/skill/KB lock source triplets."""
    extra_triplets: list[RunLockSourceTriplet] = list(base_sources)
    seen_uris = {t.uri for t in extra_triplets}
    for step in wf.steps:
        for step_uri in (step.agent_uri, step.skill_uri, *step.kb_uris):
            if step_uri and step_uri not in seen_uris:
                res = resolver.resolve(step_uri)
                seen_uris.add(res.uri)
                extra_triplets.append(
                    RunLockSourceTriplet(
                        alias=f"step-{step.step_key}-{res.scheme}",
                        scheme=res.scheme,
                        uri=res.uri,
                        resolved_version=res.resolved_version,
                        sha256=res.sha256,
                        cas_key=res.cas_key,
                    )
                )
    return tuple(sorted(extra_triplets, key=lambda t: (t.alias, t.uri)))


def resolve_workflow_and_parent(
    workflows_by_uri: dict[str, WorkflowAsCodeDefinition],
    runs_by_id: dict[str, WorkflowRunEntity],
    *,
    workflow_uri: str,
    parent_run_id: str | None,
    instance: str | None,
) -> tuple[WorkflowAsCodeDefinition, int, str | None]:
    """Resolve target workflow definition and validate parent run nesting depth."""
    clean_uri = workflow_uri.strip()
    wf = workflows_by_uri.get(clean_uri)
    if wf is None and clean_uri in (
        "orcia://system/workflows/assistant-agent",
        "orcia://workflows/assistant-agent",
    ):
        wf = workflows_by_uri.get("orcia://workflows/claims-engineering-delivery") or next(
            iter(workflows_by_uri.values()), None
        )
    if wf is None:
        raise ResourceNotFoundError(
            detail_code="ERR_WORKFLOW_NOT_FOUND",
            detail_params={"uri": workflow_uri},
            instance=instance,
        )
    nesting_depth = 0
    root_run_id_candidate: str | None = None
    if parent_run_id is not None:
        parent_run = runs_by_id.get(parent_run_id)
        if parent_run is None:
            raise ResourceNotFoundError(
                detail_code="ERR_PARENT_RUN_NOT_FOUND",
                detail_params={"parent_run_id": parent_run_id},
                instance=instance,
            )
        nesting_depth = parent_run.nesting_depth + 1
        if nesting_depth > MAX_SUB_WORKFLOW_NESTING_DEPTH:
            raise SubWorkflowMaxDepthExceededError(instance=instance)
        root_run_id_candidate = parent_run.root_run_id
    return wf, nesting_depth, root_run_id_candidate


__all__ = [
    "assemble_recursive_run_lock",
    "build_recursive_sub_locks_helper",
    "collect_step_lock_sources",
    "resolve_workflow_and_parent",
    "to_catalog_workflow",
]
