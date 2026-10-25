"""FourLayerOverrideMerger (`Base -> Team -> Workspace -> User`) & `run-lock.json` (AD-5, AD-14).

Zero framework imports (`fastapi`, `sqlalchemy`, `dramatiq`, `redis`, `litellm`).
"""

from __future__ import annotations

import json
from dataclasses import dataclass, replace

from orcia_core.catalog.cas_resolver import FederatedUriResolver, compute_bytes_sha256
from orcia_core.catalog.models import (
    CustomizationOverrideEntity,
    EvaluationLensDefinition,
    RunLockManifest,
    RunLockSourceTriplet,
    ScalarValue,
    WorkflowDefinitionEntity,
)
from orcia_core.permissions.models import OrgUnitNode, WorkspaceEntity


@dataclass(frozen=True, slots=True)
class EffectiveWorkflowMergeResult:
    """Output of the 4-layer declarative merge and `run-lock.json` generation (`AD-14`)."""

    base_workflow: WorkflowDefinitionEntity
    effective_workflow: WorkflowDefinitionEntity
    applied_override_keys: tuple[str, ...]
    run_lock: RunLockManifest


def _dedupe_tuple(existing: tuple[str, ...], additions: tuple[str, ...]) -> tuple[str, ...]:
    return tuple(dict.fromkeys([*existing, *additions]))


def _merge_lenses(
    existing: tuple[EvaluationLensDefinition, ...],
    overrides: tuple[EvaluationLensDefinition, ...],
) -> tuple[EvaluationLensDefinition, ...]:
    by_code: dict[str, EvaluationLensDefinition] = {lens.code: lens for lens in existing}
    for lens in overrides:
        by_code[lens.code] = lens
    return tuple(by_code.values())


def compute_workflow_sha256(workflow: WorkflowDefinitionEntity) -> str:
    """Compute canonical SHA-256 of a `WorkflowDefinitionEntity`."""
    canonical = json.dumps(
        {
            "uri": workflow.uri,
            "version": workflow.version,
            "source_format": workflow.source_format,
            "adaptive_gate_policy": workflow.adaptive_gate_policy,
            "scalars": dict(sorted(workflow.scalars.items())),
            "datasources": list(workflow.datasources),
            "rules": list(workflow.rules),
            "facts": list(workflow.facts),
            "lenses": [
                {"code": lens.code, "weight": lens.weight, "threshold": lens.threshold}
                for lens in workflow.lenses
            ],
            "steps": [
                {
                    "step_key": s.step_key,
                    "title": s.title,
                    "instructions": s.instructions,
                    "human_authored_required": s.human_authored_required,
                }
                for s in workflow.steps
            ],
        },
        sort_keys=True,
    )
    return compute_bytes_sha256(canonical.encode("utf-8"))


class FourLayerOverrideMerger:
    """Pure, non-mutating 4-layer override engine (`Base -> Team -> Workspace -> User`)."""

    @staticmethod
    def resolve_org_unit_chain_top_down(
        org_units: tuple[OrgUnitNode, ...], leaf_org_unit_id: str
    ) -> tuple[str, ...]:
        """Return ordered tuple of `org_unit.id` from root ancestor down to `leaf_org_unit_id`."""
        by_id = {u.id: u for u in org_units}
        chain: list[str] = []
        visited: set[str] = set()
        curr = by_id.get(leaf_org_unit_id)
        while curr is not None and curr.id not in visited:
            visited.add(curr.id)
            chain.append(curr.id)
            curr = by_id.get(curr.parent_id) if curr.parent_id else None
        chain.reverse()
        return tuple(chain)

    @classmethod
    def select_ordered_overrides(
        cls,
        *,
        target_uri: str,
        org_units: tuple[OrgUnitNode, ...],
        workspace: WorkspaceEntity,
        user_id: str | None,
        overrides: tuple[CustomizationOverrideEntity, ...],
    ) -> tuple[CustomizationOverrideEntity, ...]:
        """Order applicable overrides along `Team (Parent -> Sub-Team) -> Workspace -> User`."""
        matching = [ovr for ovr in overrides if ovr.target_uri == target_uri]
        team_chain = cls.resolve_org_unit_chain_top_down(org_units, workspace.owner_org_unit_id)
        ordered = [
            ovr
            for org_id in team_chain
            for ovr in matching
            if ovr.override_layer == "TEAM" and ovr.org_unit_id == org_id
        ]
        ordered.extend(
            ovr
            for ovr in matching
            if ovr.override_layer == "WORKSPACE" and ovr.workspace_id == workspace.id
        )
        if user_id is not None:
            ordered.extend(
                ovr for ovr in matching if ovr.override_layer == "USER" and ovr.user_id == user_id
            )
        return tuple(ordered)

    @classmethod
    def merge_workflow(
        cls,
        *,
        base_workflow: WorkflowDefinitionEntity,
        org_units: tuple[OrgUnitNode, ...],
        workspace: WorkspaceEntity,
        user_id: str | None,
        overrides: tuple[CustomizationOverrideEntity, ...],
    ) -> tuple[WorkflowDefinitionEntity, tuple[str, ...]]:
        """Produce a new `WorkflowDefinitionEntity` without mutating `base_workflow` (`AD-14`)."""
        ordered_overrides = cls.select_ordered_overrides(
            target_uri=base_workflow.uri,
            org_units=org_units,
            workspace=workspace,
            user_id=user_id,
            overrides=overrides,
        )

        merged_scalars: dict[str, ScalarValue] = dict(base_workflow.scalars)
        merged_datasources: tuple[str, ...] = tuple(base_workflow.datasources)
        merged_rules: tuple[str, ...] = tuple(base_workflow.rules)
        merged_facts: tuple[str, ...] = tuple(base_workflow.facts)
        merged_lenses: tuple[EvaluationLensDefinition, ...] = tuple(base_workflow.lenses)
        applied_keys: list[str] = []
        workspace_ds_injected = False

        for ovr in ordered_overrides:
            if ovr.override_layer == "WORKSPACE" and not workspace_ds_injected:
                merged_datasources = _dedupe_tuple(
                    merged_datasources, tuple(ds.uri for ds in workspace.datasources)
                )
                workspace_ds_injected = True

            merged_scalars = {**merged_scalars, **ovr.scalars}
            merged_datasources = _dedupe_tuple(merged_datasources, ovr.datasources)
            merged_rules = _dedupe_tuple(merged_rules, ovr.rules)
            merged_facts = _dedupe_tuple(merged_facts, ovr.facts)
            merged_lenses = _merge_lenses(merged_lenses, ovr.lenses)
            applied_keys.append(ovr.override_key)

        if not workspace_ds_injected and workspace.datasources:
            merged_datasources = _dedupe_tuple(
                merged_datasources, tuple(ds.uri for ds in workspace.datasources)
            )

        provisional = replace(
            base_workflow,
            workspace_id=workspace.id,
            scalars=merged_scalars,
            datasources=merged_datasources,
            rules=merged_rules,
            facts=merged_facts,
            lenses=merged_lenses,
            steps=tuple(base_workflow.steps),
            sha256="",
            customize_metadata=dict(base_workflow.customize_metadata),
        )
        effective = replace(provisional, sha256=compute_workflow_sha256(provisional))
        return effective, tuple(applied_keys)

    @classmethod
    def merge_and_lock(
        cls,
        *,
        base_workflow: WorkflowDefinitionEntity,
        org_units: tuple[OrgUnitNode, ...],
        workspace: WorkspaceEntity,
        user_id: str | None,
        overrides: tuple[CustomizationOverrideEntity, ...],
        resolver: FederatedUriResolver,
    ) -> EffectiveWorkflowMergeResult:
        """Merge 4 layers and generate the deterministic `run-lock.json` manifest (`AD-5`)."""
        effective_wf, applied_keys = cls.merge_workflow(
            base_workflow=base_workflow,
            org_units=org_units,
            workspace=workspace,
            user_id=user_id,
            overrides=overrides,
        )

        wf_res = resolver.resolve(base_workflow.uri)
        triplets: list[RunLockSourceTriplet] = [
            RunLockSourceTriplet(
                alias="workflow-definition",
                scheme=wf_res.scheme,
                uri=wf_res.uri,
                resolved_version=wf_res.resolved_version,
                sha256=wf_res.sha256,
                cas_key=wf_res.cas_key,
            )
        ]
        seen_uris: set[str] = {wf_res.uri}
        for ds in workspace.datasources:
            res = resolver.resolve(ds.uri)
            seen_uris.add(res.uri)
            triplets.append(
                RunLockSourceTriplet(
                    alias=ds.alias,
                    scheme=res.scheme,
                    uri=res.uri,
                    resolved_version=res.resolved_version,
                    sha256=res.sha256,
                    cas_key=res.cas_key,
                )
            )
        for idx, extra_uri in enumerate(effective_wf.datasources, start=1):
            if extra_uri not in seen_uris:
                res = resolver.resolve(extra_uri)
                seen_uris.add(res.uri)
                triplets.append(
                    RunLockSourceTriplet(
                        alias=f"extra-source-{idx}",
                        scheme=res.scheme,
                        uri=res.uri,
                        resolved_version=res.resolved_version,
                        sha256=res.sha256,
                        cas_key=res.cas_key,
                    )
                )

        sorted_triplets = tuple(sorted(triplets, key=lambda item: (item.alias, item.uri)))
        manifest_payload = json.dumps(
            {
                "workspace_id": workspace.id,
                "workflow_uri": base_workflow.uri,
                "workflow_version": base_workflow.version,
                "workflow_sha256": base_workflow.sha256,
                "effective_workflow_sha256": effective_wf.sha256,
                "applied_override_keys": list(applied_keys),
                "sources": [
                    {
                        "alias": t.alias,
                        "scheme": t.scheme,
                        "uri": t.uri,
                        "resolved_version": t.resolved_version,
                        "sha256": t.sha256,
                        "cas_key": t.cas_key,
                    }
                    for t in sorted_triplets
                ],
            },
            sort_keys=True,
        )
        run_lock = RunLockManifest(
            workspace_id=workspace.id,
            workflow_uri=base_workflow.uri,
            workflow_version=base_workflow.version,
            workflow_sha256=base_workflow.sha256,
            effective_workflow_sha256=effective_wf.sha256,
            applied_override_keys=applied_keys,
            sources=sorted_triplets,
            manifest_sha256=compute_bytes_sha256(manifest_payload.encode("utf-8")),
        )
        return EffectiveWorkflowMergeResult(
            base_workflow=base_workflow,
            effective_workflow=effective_wf,
            applied_override_keys=applied_keys,
            run_lock=run_lock,
        )
