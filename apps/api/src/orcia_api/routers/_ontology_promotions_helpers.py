"""Helpers for Story 20.2 Ontology Permissions & Step-by-Step Promotions Router."""

from __future__ import annotations

from dataclasses import replace

from fastapi import Request
from sqlalchemy.ext.asyncio import AsyncEngine

from orcia_api.dependencies import get_auth_service, get_ontology_and_rag_services
from orcia_api.dependencies._core_providers import get_configured_db_engine
from orcia_api.routers._finops_scope_guards import sync_evaluator_topology_from_pg
from orcia_api.routers.auth import resolve_request_user
from orcia_api.routers.ontology_rag_helpers import serialize_what_if
from orcia_api.schemas import ontology_promotions as s
from orcia_core.observability.logging import get_logger
from orcia_core.ontology import (
    OntologyGovernanceService,
    OntologyLevel,
    OntologyPromotionProposal,
    can_write_ontology_level,
    find_org_unit,
    find_workspace,
    is_observer_user,
    load_org_and_workspaces_context,
)
from orcia_core.ontology.errors import ObserverModeReadOnlyError
from orcia_core.permissions.models import (
    OrgUnitNode,
    UserIdentity,
    WorkspaceEntity,
    WorkspaceMembershipEntity,
)

logger = get_logger("orcia.api.ontology_promotions")


def resolve_ontology_caller(request: Request, persona_key: str | None) -> UserIdentity:
    """Resolve authenticated caller identity and honor `X-Orcia-Active-Hat` / observer mode."""
    effective = persona_key or request.headers.get("x-orcia-persona", "").strip() or None
    user = resolve_request_user(request, persona_key=effective)
    is_obs = request.headers.get(
        "x-orcia-access-mode", ""
    ).strip().upper() == "READ_ONLY_OBSERVER" or request.headers.get(
        "x-orcia-observer-mode", ""
    ).strip().lower() in {"1", "true", "yes"}
    if is_obs:
        return replace(user, platform_role="OBSERVER", roles=("OBSERVER",))
    active_hat = request.headers.get("x-orcia-active-hat", "").strip().upper()
    if active_hat and active_hat != user.platform_role:
        caller_roles = {str(user.platform_role).upper(), *(str(r).upper() for r in user.roles)}
        if active_hat in ("OBSERVER", "READ_ONLY_OBSERVER"):
            return replace(user, platform_role="OBSERVER", roles=("OBSERVER",))
        if active_hat in caller_roles or "PLATFORM_ADMIN" in caller_roles:
            return replace(user, platform_role=active_hat, roles=(active_hat,))  # type: ignore[arg-type]
    return user


async def load_ontology_topology(
    request: Request,
    *,
    fixture: bool,
) -> tuple[AsyncEngine | None, tuple[OrgUnitNode, ...], tuple[WorkspaceEntity, ...]]:
    """Return `(engine_or_none, org_units, workspaces)` from PG18 when active, else evaluator."""
    svc = get_auth_service(request)
    engine = None if fixture else get_configured_db_engine(request)
    if engine is not None:
        if getattr(getattr(request, "state", None), "_orcia_topology_synced", False):
            return engine, tuple(svc.evaluator.org_units), tuple(svc.evaluator.workspaces)
        try:
            pg_units, pg_ws = await load_org_and_workspaces_context(engine)
            return engine, pg_units, pg_ws
        except Exception as exc:
            logger.warning("ontology_topology_pg_fallback", error_type=type(exc).__name__)
            engine = None
    return engine, tuple(svc.evaluator.org_units), tuple(svc.evaluator.workspaces)


def is_restricted_proposal_denied(
    user: UserIdentity,
    proposal: OntologyPromotionProposal,
    workspaces: tuple[WorkspaceEntity, ...],
    memberships: tuple[WorkspaceMembershipEntity, ...],
) -> bool:
    """Return True if proposal touches a confidential/private workspace without caller access."""
    from orcia_core.ontology import can_read_ontology_item

    for scope_id in (proposal.source_scope_id, proposal.target_scope_id):
        if not scope_id:
            continue
        ws = find_workspace(workspaces, scope_id)
        if (
            ws is not None
            and (
                ws.visibility_mode == "CONFIDENTIAL_RESTRICTED"
                or ws.ui_visibility_mode == "PRIVATE_USER"
                or ws.personal_owner_user_id is not None
            )
            and not can_read_ontology_item(user, "4_WORKSPACE", ws.id, (), workspaces, memberships)
        ):
            return True
    return False


def serialize_proposal_detail(
    p: OntologyPromotionProposal,
    *,
    can_decide: bool,
) -> s.OntologyPromotionProposalDetailItem:
    """Serialize `OntologyPromotionProposal` with collision and reviewer metadata."""
    return s.OntologyPromotionProposalDetailItem(
        id=p.id,
        proposal_key=p.proposal_key,
        concept_key=p.concept_key,
        canonical_term=p.canonical_term,
        source_level=p.source_level,
        target_level=p.target_level,
        target_scope_id=p.target_scope_id,
        proposed_by_user_id=p.proposed_by_user_id,
        status=p.status,
        impact_report=serialize_what_if(p.impact_report),
        badge_color_token=p.badge_color_token,
        source_concept_id=p.source_concept_id,
        source_scope_id=p.source_scope_id,
        definition_text=p.definition_text,
        reviewed_by_user_id=p.reviewed_by_user_id,
        review_comment=p.review_comment,
        created_at=p.created_at,
        reviewed_at=p.reviewed_at,
        collision_detected=p.collision_detected,
        colliding_definition=p.colliding_definition,
        can_decide=can_decide,
    )


def compute_writable_options(
    user: UserIdentity,
    org_units: tuple[OrgUnitNode, ...],
    workspaces: tuple[WorkspaceEntity, ...],
    memberships: tuple[WorkspaceMembershipEntity, ...] = (),
) -> tuple[list[OntologyLevel], list[s.WritableScopeOptionItem]]:
    """Compute allowed direct-write `(level, scope_id, label)` choices for `user`."""
    options: list[s.WritableScopeOptionItem] = []
    if can_write_ontology_level(
        user, "1_ENTERPRISE", "scope-global", org_units, workspaces, memberships
    ):
        options.append(
            s.WritableScopeOptionItem(
                level="1_ENTERPRISE", scope_id="scope-global", label="Organisation (Global)"
            )
        )
    for unit in org_units:
        if unit.unit_type == "BU" and can_write_ontology_level(
            user, "2_DOMAIN", unit.id, org_units, workspaces, memberships
        ):
            options.append(
                s.WritableScopeOptionItem(level="2_DOMAIN", scope_id=unit.id, label=unit.name)
            )
        elif unit.unit_type in ("TEAM", "SUB_TEAM") and can_write_ontology_level(
            user, "3_TEAM", unit.id, org_units, workspaces, memberships
        ):
            options.append(
                s.WritableScopeOptionItem(level="3_TEAM", scope_id=unit.id, label=unit.name)
            )
    for ws in workspaces:
        if can_write_ontology_level(user, "4_WORKSPACE", ws.id, org_units, workspaces, memberships):
            options.append(
                s.WritableScopeOptionItem(level="4_WORKSPACE", scope_id=ws.id, label=ws.name)
            )
    levels: list[OntologyLevel] = list(dict.fromkeys(opt.level for opt in options))
    return levels, options


def resolve_dynamic_ontology_scopes(
    level: OntologyLevel,
    scope_id: str,
    org_units: tuple[OrgUnitNode, ...],
    workspaces: tuple[WorkspaceEntity, ...],
) -> tuple[str, str, tuple[str, ...], str, str | None]:
    """Resolve real `(enterprise, domain, team_chain, workspace, run)` scopes from topology."""
    enterprise_scope = scope_id if level == "1_ENTERPRISE" else "scope-global"
    if level == "1_ENTERPRISE":
        return enterprise_scope, "", (), "", None
    if level == "4_RUN_EPHEMERAL":
        return enterprise_scope, "", (), "", scope_id
    if level == "2_DOMAIN":
        return enterprise_scope, scope_id, (), "", None

    by_id = {u.id: u for u in org_units}
    team_chain: list[str] = []
    domain_scope = ""
    workspace_scope = ""
    start_node: OrgUnitNode | None = None

    if level in ("3_WORKSPACE", "4_WORKSPACE"):
        workspace_scope = scope_id
        ws = find_workspace(workspaces, scope_id)
        if ws is not None:
            start_node = find_org_unit(org_units, ws.owner_org_unit_id)
    elif level == "3_TEAM":
        start_node = find_org_unit(org_units, scope_id)
        if start_node is None:
            team_chain.append(scope_id)

    cur = start_node
    visited: set[str] = set()
    while cur is not None and cur.id not in visited and len(visited) < 32:
        visited.add(cur.id)
        if cur.unit_type in ("TEAM", "SUB_TEAM"):
            team_chain.append(cur.id)
        elif cur.unit_type in ("BU", "TRIBE") and not domain_scope:
            domain_scope = cur.id
        cur = by_id.get(cur.parent_id) if cur.parent_id else None

    return enterprise_scope, domain_scope, tuple(team_chain), workspace_scope, None


async def prepare_ontology_handler_context(
    request: Request,
    *,
    fixture: bool,
    persona_key: str | None,
    reject_observer: bool = False,
) -> tuple[
    UserIdentity,
    tuple[WorkspaceMembershipEntity, ...],
    OntologyGovernanceService,
    AsyncEngine | None,
    tuple[OrgUnitNode, ...],
    tuple[WorkspaceEntity, ...],
]:
    """Resolve caller, sync PG18 topology when non-fixture, and load ontology topology."""
    user = resolve_ontology_caller(request, persona_key)
    if reject_observer and is_observer_user(user):
        raise ObserverModeReadOnlyError(instance=str(request.url.path))
    auth_svc = get_auth_service(request)
    if not fixture:
        await sync_evaluator_topology_from_pg(request, auth_svc)
    memberships = auth_svc.evaluator.list_memberships()
    gov, _, _ = get_ontology_and_rag_services(request, fixture=fixture)
    engine, org_units, workspaces = await load_ontology_topology(request, fixture=fixture)
    return user, memberships, gov, engine, org_units, workspaces
