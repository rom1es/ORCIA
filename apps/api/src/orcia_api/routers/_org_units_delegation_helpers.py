"""Story 20.1 — Delegation & Capability Annotation Helpers for `/api/v1/org-units`."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import replace

from fastapi import Request

from orcia_api.routers._org_units_audit import record_governance_audit_event
from orcia_api.routers._org_units_helpers import (
    serialize_org_unit_summary,
    sync_evaluator_from_summaries,
)
from orcia_api.routers.auth import resolve_request_user
from orcia_api.schemas.auth_and_org import (
    OrgUnitCreateRequest,
    OrgUnitPatchRequest,
    OrgUnitResponse,
)
from orcia_core.bootstrap import list_org_units_from_postgres18
from orcia_core.observability.logging import get_logger
from orcia_core.permissions import (
    MatrixPermissionEvaluator,
    OrgUnitNode,
    OrgUnitSummary,
    UserIdentity,
    assert_can_create_org_unit,
    assert_can_delete_org_unit,
    assert_can_update_org_unit,
    compute_managed_org_scope,
    compute_org_unit_capabilities,
)
from orcia_core.permissions.errors import (
    ObserverModeReadOnlyError,
    ResourceNotFoundError,
    ScopeAccessDeniedError,
)

logger = get_logger("orcia.api.org_units.delegation")


def is_observer_request(request: Request, user: UserIdentity) -> bool:
    """Return True if caller is in `READ_ONLY_OBSERVER` mode via header or role."""
    return (
        request.headers.get("x-orcia-access-mode", "").strip().upper() == "READ_ONLY_OBSERVER"
        or request.headers.get("x-orcia-observer-mode", "").strip().lower() in {"1", "true", "yes"}
        or request.headers.get("x-orcia-active-hat", "").strip().upper() == "OBSERVER"
        or user.platform_role == "OBSERVER"
    )


def resolve_org_caller(request: Request, persona_key: str | None) -> UserIdentity:
    """Resolve authenticated user identity and enforce optional `X-Orcia-Active-Hat` step-down."""
    effective_persona = persona_key or request.headers.get("x-orcia-persona", "").strip() or None
    user = resolve_request_user(request, persona_key=effective_persona)
    active_hat = request.headers.get("x-orcia-active-hat", "").strip().upper()
    if active_hat and active_hat != user.platform_role:
        caller_roles = {str(user.platform_role).upper(), *(str(r).upper() for r in user.roles)}
        if active_hat in ("OBSERVER", "READ_ONLY_OBSERVER"):
            return replace(user, platform_role="OBSERVER", roles=("OBSERVER",))
        if active_hat in caller_roles or "PLATFORM_ADMIN" in caller_roles:
            return replace(user, platform_role=active_hat, roles=(active_hat,))  # type: ignore[arg-type]
    return user


async def ensure_evaluator_org_units_synced(
    request: Request,
    evaluator: MatrixPermissionEvaluator,
) -> None:
    """Ensure `evaluator.org_units` reflects PG18 state before delegation checks."""
    from orcia_api.dependencies._core_providers import get_configured_db_engine

    engine = get_configured_db_engine(request)
    if engine is None:
        return
    try:
        summaries = await list_org_units_from_postgres18(engine)
        sync_evaluator_from_summaries(evaluator, summaries)
    except Exception as exc:
        logger.warning("org_units_delegation_sync_fallback", error_type=type(exc).__name__)


def resolve_evaluator_target_node(
    evaluator: MatrixPermissionEvaluator,
    org_unit_id_or_slug: str,
    *,
    allow_enterprise: bool = False,
) -> OrgUnitNode:
    """Resolve target `OrgUnitNode` by ID or slug or raise 404."""
    cleaned = org_unit_id_or_slug.strip()
    target = evaluator.get_org_unit(cleaned)
    if (
        target is None
        and allow_enterprise
        and cleaned.lower()
        in {
            "0192c4e0-0000-7000-8000-000000000001",
            "orcia-root",
            "orcia-root-org",
            "orcia-enterprise",
            "global",
            "scope-global",
        }
    ):
        target = next((u for u in evaluator.org_units if u.unit_type == "ENTERPRISE"), None)
        if target is None:
            return OrgUnitNode(
                id="0192c4e0-0000-7000-8000-000000000001",
                slug="orcia-root",
                name="Plateforme Globale ORCIA",
                unit_type="ENTERPRISE",
                parent_id=None,
                billing_enabled=True,
            )
    if target is None or (target.unit_type == "ENTERPRISE" and not allow_enterprise):
        raise ResourceNotFoundError(
            detail_override=f"Unité organisationnelle introuvable : '{cleaned}'."
        )
    return target


def _summary_to_node(summary: OrgUnitSummary) -> OrgUnitNode:
    return OrgUnitNode(
        id=summary.id,
        slug=summary.slug,
        name=summary.name,
        unit_type=summary.kind,
        parent_id=summary.parent_id,
        billing_enabled=summary.billing_enabled,
        lead_user_id=summary.lead_user_id,
        lead_user_ids=summary.lead_user_ids,
        ontology_lead_user_ids=summary.ontology_lead_user_ids,
        member_user_ids=summary.member_user_ids,
    )


def serialize_org_unit_with_capabilities(
    request: Request,
    user: UserIdentity,
    summary: OrgUnitSummary,
    evaluator: MatrixPermissionEvaluator,
) -> OrgUnitResponse:
    """Serialize a single `OrgUnitSummary` with caller-computed `can_*` flags."""
    tree_nodes = [n for n in evaluator.org_units if n.unit_type != "ENTERPRISE"]
    nodes_by_id = {n.id: n for n in tree_nodes}
    target_node = nodes_by_id.get(summary.id) or _summary_to_node(summary)
    if target_node.id not in nodes_by_id:
        tree_nodes.append(target_node)
    scope = compute_managed_org_scope(user, tree_nodes)
    caps = compute_org_unit_capabilities(
        user,
        target_node,
        scope,
        is_observer=is_observer_request(request, user),
    )
    return serialize_org_unit_summary(summary, capabilities=caps)


def filter_and_annotate_org_units(
    request: Request,
    user: UserIdentity,
    summaries: Sequence[OrgUnitSummary],
    evaluator: MatrixPermissionEvaluator,
) -> list[OrgUnitResponse]:
    """Filter units to caller's visible scope and attach server-computed `can_*` booleans."""
    tree_nodes = [n for n in evaluator.org_units if n.unit_type != "ENTERPRISE"]
    summary_nodes = [_summary_to_node(s) for s in summaries]
    nodes = tree_nodes if len(tree_nodes) >= len(summary_nodes) else summary_nodes
    nodes_by_id = {n.id: n for n in nodes}

    scope = compute_managed_org_scope(user, nodes)
    is_obs = is_observer_request(request, user)
    out: list[OrgUnitResponse] = []
    for s in summaries:
        if (
            not scope.is_platform_admin
            and not scope.is_global_reader
            and s.id not in scope.visible_unit_ids
        ):
            continue
        node = nodes_by_id.get(s.id) or _summary_to_node(s)
        caps = compute_org_unit_capabilities(user, node, scope, is_observer=is_obs)
        out.append(serialize_org_unit_summary(s, capabilities=caps))
    return out


def enforce_org_create_delegation(
    request: Request,
    user: UserIdentity,
    payload: OrgUnitCreateRequest,
    evaluator: MatrixPermissionEvaluator,
) -> None:
    """Enforce observer, active-hat, and subtree delegation checks on `POST /api/v1/org-units`."""
    if is_observer_request(request, user):
        raise ObserverModeReadOnlyError(instance=str(request.url.path))
    active_hat = request.headers.get("x-orcia-active-hat", "").strip().upper()
    if active_hat and active_hat not in ("PLATFORM_ADMIN", "BU_LEAD", "BU_DIRECTOR"):
        raise ScopeAccessDeniedError(instance=str(request.url.path))
    assert_can_create_org_unit(
        user,
        parent_id=payload.parent_id,
        org_units=evaluator.org_units,
        instance=str(request.url.path),
    )


def enforce_org_patch_delegation(
    request: Request,
    user: UserIdentity,
    org_unit_id: str,
    payload: OrgUnitPatchRequest,
    evaluator: MatrixPermissionEvaluator,
) -> OrgUnitNode:
    """Enforce observer, active-hat, subtree, field restrictions, and anti-eviction on `PATCH`."""
    if is_observer_request(request, user):
        raise ObserverModeReadOnlyError(instance=str(request.url.path))
    active_hat = request.headers.get("x-orcia-active-hat", "").strip().upper()
    if active_hat and active_hat not in ("PLATFORM_ADMIN", "BU_LEAD", "BU_DIRECTOR", "TEAM_LEAD"):
        raise ScopeAccessDeniedError(instance=str(request.url.path))
    target = resolve_evaluator_target_node(evaluator, org_unit_id)
    lead_provided = (
        "lead_user_ids" in payload.model_fields_set or "lead_user_id" in payload.model_fields_set
    )
    if "lead_user_ids" in payload.model_fields_set:
        next_leads = payload.lead_user_ids or []
    elif "lead_user_id" in payload.model_fields_set:
        lead_str = (payload.lead_user_id or "").strip()
        next_leads = [lead_str] if lead_str else []
    else:
        next_leads = list(target.lead_user_ids)

    raw_parent = (payload.parent_id or "").strip() or None
    next_parent = None if raw_parent == "scope-global" else raw_parent
    assert_can_update_org_unit(
        user,
        target=target,
        parent_id_provided="parent_id" in payload.model_fields_set,
        next_parent_id=next_parent,
        billing_enabled_provided="billing_enabled" in payload.model_fields_set,
        next_billing_enabled=(
            payload.billing_enabled
            if payload.billing_enabled is not None
            else target.billing_enabled
        ),
        lead_user_ids_provided=lead_provided,
        next_lead_user_ids=next_leads,
        ontology_lead_user_ids_provided="ontology_lead_user_ids" in payload.model_fields_set,
        next_ontology_lead_user_ids=payload.ontology_lead_user_ids or [],
        org_units=evaluator.org_units,
        instance=str(request.url.path),
    )
    return target


def enforce_org_delete_delegation(
    request: Request,
    user: UserIdentity,
    org_unit_id: str,
    evaluator: MatrixPermissionEvaluator,
) -> OrgUnitNode:
    """Enforce observer, active-hat, root-BU protection, and subtree confinement on `DELETE`."""
    if is_observer_request(request, user):
        raise ObserverModeReadOnlyError(instance=str(request.url.path))
    active_hat = request.headers.get("x-orcia-active-hat", "").strip().upper()
    if active_hat and active_hat not in ("PLATFORM_ADMIN", "BU_LEAD", "BU_DIRECTOR"):
        raise ScopeAccessDeniedError(instance=str(request.url.path))
    target = resolve_evaluator_target_node(evaluator, org_unit_id)
    assert_can_delete_org_unit(
        user,
        target=target,
        org_units=evaluator.org_units,
        instance=str(request.url.path),
    )
    return target


__all__ = [
    "enforce_org_create_delegation",
    "enforce_org_delete_delegation",
    "enforce_org_patch_delegation",
    "ensure_evaluator_org_units_synced",
    "filter_and_annotate_org_units",
    "is_observer_request",
    "record_governance_audit_event",
    "resolve_evaluator_target_node",
    "resolve_org_caller",
    "serialize_org_unit_with_capabilities",
]
