"""Fail-closed RBAC & confidential isolation guards for resolve and what-if routes."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import replace

from fastapi import Request

from orcia_api.dependencies import get_auth_service
from orcia_api.routers._ontology_promotions_helpers import prepare_ontology_handler_context
from orcia_api.routers.ontology_rag_helpers import (
    get_trace_id,
    serialize_concept,
    serialize_relation,
    serialize_what_if,
)
from orcia_api.routers.ontology_rag_helpers import (
    is_concept_readable as _is_concept_readable,
)
from orcia_api.schemas import ontology_and_rag as s
from orcia_core.ontology import (
    ImpactSimulatorService,
    OntologyConceptEntity,
    OntologyGovernanceService,
    OntologyHierarchyResolver,
    ProfileSemanticTranslator,
    list_concepts_pg,
)
from orcia_core.ontology.errors import ScopeAccessDeniedError
from orcia_core.packs import resolve_workspace_pack_ontology_pg
from orcia_core.permissions.models import (
    OrgUnitNode,
    UserIdentity,
    WorkspaceEntity,
    WorkspaceMembershipEntity,
)


def _filter_readable_concepts(
    request: Request,
    *,
    user: UserIdentity,
    concepts: tuple[OntologyConceptEntity, ...],
    org_units: Sequence[OrgUnitNode],
    workspaces: Sequence[WorkspaceEntity],
    memberships: Sequence[WorkspaceMembershipEntity],
    allowed_pack_slugs: frozenset[str] | None = None,
) -> tuple[OntologyConceptEntity, ...]:
    by_id = {c.id: c for c in concepts}
    return tuple(
        c
        for c in concepts
        if _is_concept_readable(
            request,
            user=user,
            concept=c,
            concepts_by_id=by_id,
            org_units=org_units,
            workspaces=workspaces,
            memberships=memberships,
            allowed_pack_slugs=allowed_pack_slugs,
        )
    )


async def resolve_ontology_for_caller(
    request: Request,
    *,
    body: s.OntologyResolveRequest,
    gov: OntologyGovernanceService,
    fixture: bool,
) -> s.OntologyResolveResponse:
    """Resolve 4-level ontology snapshot enforcing workspace & confidential isolation."""
    if fixture:
        snap = gov.resolve_snapshot(
            enterprise_scope_id=body.enterprise_scope_id,
            domain_scope_id=body.domain_scope_id,
            team_chain_scope_ids=tuple(body.team_chain_scope_ids),
            workspace_scope_id=body.workspace_scope_id,
            run_scope_id=body.run_scope_id,
        )
        labels = {
            term: ProfileSemanticTranslator.translate_concept(c, body.human_profile)
            for term, c in snap.concepts_by_term.items()
        }
        return s.OntologyResolveResponse(
            concepts=[serialize_concept(c) for c in snap.concepts_by_term.values()],
            relations=[serialize_relation(r) for r in snap.relations],
            profile_labels=labels,
            trace_id=get_trace_id(request),
        )

    persona_key = request.query_params.get("persona_key") or request.query_params.get("persona")
    user, memberships, _, engine, org_units, workspaces = await prepare_ontology_handler_context(
        request, fixture=False, persona_key=persona_key
    )
    auth_svc = get_auth_service(request)
    path = str(request.url.path)
    clean_ws = (body.workspace_scope_id or "").strip()
    if clean_ws and clean_ws not in ("scope-global", "GLOBAL"):
        ws_ent = auth_svc.evaluator.get_workspace(clean_ws)
        if ws_ent is None:
            if "workspace_scope_id" in body.model_fields_set:
                raise ScopeAccessDeniedError(instance=path)
        elif auth_svc.evaluator.resolve_workspace_access(user, ws_ent.id) is None:
            raise ScopeAccessDeniedError(instance=path)

    raw_concepts = tuple(gov.concepts)
    active_pack_priorities: dict[str, int] = {}
    dna_mechanisms: list[dict[str, object]] = []
    broker_policies: list[dict[str, object]] = []
    instructions: list[dict[str, object]] = []
    resolved_ws_scope = body.workspace_scope_id
    if engine is not None:
        pack_res = await resolve_workspace_pack_ontology_pg(
            engine,
            workspace_id=clean_ws or body.workspace_scope_id,
            enterprise_scope_id=body.enterprise_scope_id,
            domain_scope_id=body.domain_scope_id,
            team_chain_scope_ids=tuple(body.team_chain_scope_ids),
            run_scope_id=body.run_scope_id,
        )
        active_pack_priorities = dict(pack_res.active_pack_priorities)
        dna_mechanisms = list(pack_res.dna_mechanisms)
        broker_policies = list(pack_res.broker_policies)
        instructions = list(pack_res.instructions)
        resolved_ws_scope = pack_res.workspace_id
        if not raw_concepts:
            raw_concepts = tuple(await list_concepts_pg(engine))

    allowed_packs = frozenset(active_pack_priorities.keys())
    readable = _filter_readable_concepts(
        request,
        user=user,
        concepts=raw_concepts,
        org_units=org_units,
        workspaces=workspaces,
        memberships=memberships,
        allowed_pack_slugs=allowed_packs,
    )
    readable_keys = {c.concept_key for c in readable}
    safe_relations = tuple(
        r
        for r in gov.relations
        if r.source_concept_key in readable_keys and r.target_concept_key in readable_keys
    )
    snap = OntologyHierarchyResolver.resolve_effective_ontology(
        concepts=readable,
        relations=safe_relations,
        axioms=gov.axioms,
        enterprise_scope_id=body.enterprise_scope_id,
        domain_scope_id=body.domain_scope_id,
        team_chain_scope_ids=tuple(body.team_chain_scope_ids),
        workspace_scope_id=resolved_ws_scope,
        run_scope_id=body.run_scope_id,
        active_pack_priorities=active_pack_priorities or None,
    )
    labels = {
        term: ProfileSemanticTranslator.translate_concept(c, body.human_profile)
        for term, c in snap.concepts_by_term.items()
    }
    return s.OntologyResolveResponse(
        concepts=[serialize_concept(c) for c in snap.concepts_by_term.values()],
        relations=[serialize_relation(r) for r in snap.relations],
        profile_labels=labels,
        active_pack_priorities=active_pack_priorities,
        dna_mechanisms=dna_mechanisms,
        broker_policies=broker_policies,
        instructions=instructions,
        trace_id=get_trace_id(request),
    )


async def simulate_what_if_for_caller(
    request: Request,
    *,
    body: s.WhatIfSimulationRequest,
    gov: OntologyGovernanceService,
    fixture: bool,
) -> s.WhatIfSimulationResponse:
    """Execute What-If impact simulation while enforcing confidential isolation fail-closed."""
    if fixture:
        report = gov.simulate_what_if(
            concept_key=body.concept_key, proposed_change=body.proposed_change
        )
        return serialize_what_if(report, trace_id=get_trace_id(request))

    persona_key = request.query_params.get("persona_key") or request.query_params.get("persona")
    user, memberships, _, engine, org_units, workspaces = await prepare_ontology_handler_context(
        request, fixture=False, persona_key=persona_key
    )
    raw_concepts = tuple(gov.concepts)
    if not raw_concepts and engine is not None:
        raw_concepts = tuple(await list_concepts_pg(engine))

    concepts_by_id = {c.id: c for c in raw_concepts}
    target = next((c for c in raw_concepts if c.concept_key == body.concept_key), None)
    if target is not None and not _is_concept_readable(
        request,
        user=user,
        concept=target,
        concepts_by_id=concepts_by_id,
        org_units=org_units,
        workspaces=workspaces,
        memberships=memberships,
    ):
        raise ScopeAccessDeniedError(instance=str(request.url.path))

    readable = _filter_readable_concepts(
        request,
        user=user,
        concepts=raw_concepts,
        org_units=org_units,
        workspaces=workspaces,
        memberships=memberships,
    )
    readable_keys = {c.concept_key for c in readable}
    safe_relations = tuple(
        r
        for r in gov.relations
        if r.source_concept_key in readable_keys and r.target_concept_key in readable_keys
    )
    report = ImpactSimulatorService.simulate_what_if(
        concept_key=body.concept_key,
        proposed_change=body.proposed_change,
        concepts=readable,
        relations=safe_relations,
        axioms=gov.axioms,
        template_bindings=gov._template_bindings,
        workflow_bindings=gov._workflow_bindings,
        active_run_bindings=gov._active_run_bindings,
    )

    auth_svc = get_auth_service(request)
    denied_tokens: set[str] = set()
    for ws in workspaces:
        if auth_svc.evaluator.resolve_workspace_access(user, ws.id) is None:
            denied_tokens.add(ws.id.lower())
            if ws.slug:
                denied_tokens.add(ws.slug.lower())
    denied_run_ids: set[str] = set()
    cc_svc = getattr(request.app.state, "control_center_service", None)
    if cc_svc is not None:
        for run_id, run in getattr(cc_svc, "_runs", {}).items():
            if auth_svc.evaluator.resolve_workspace_access(user, run.workspace_id) is None:
                denied_run_ids.add(run_id)

    filtered_report = replace(
        report,
        transitively_affected_concepts=tuple(
            k for k in report.transitively_affected_concepts if k in readable_keys
        ),
        impacted_artifact_templates=tuple(
            t
            for t in report.impacted_artifact_templates
            if not any(d in t.lower() for d in denied_tokens)
        ),
        impacted_workflow_uris=tuple(
            w
            for w in report.impacted_workflow_uris
            if not any(d in w.lower() for d in denied_tokens)
        ),
        impacted_active_run_ids=tuple(
            r
            for r in report.impacted_active_run_ids
            if r not in denied_run_ids and not any(d in r.lower() for d in denied_tokens)
        ),
    )
    return serialize_what_if(filtered_report, trace_id=get_trace_id(request))
