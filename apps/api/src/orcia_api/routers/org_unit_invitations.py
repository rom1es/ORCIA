"""Story 20.1 — Scoped Organization User Invitation Router (`/api/v1/org-units/invite-user`)."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Query, Request

from orcia_api.dependencies import (
    get_accostage_service,
    get_auth_service,
    get_iam_accounts_service,
    get_or_create_shared_db_engine,
)
from orcia_api.routers._auth_pg_helpers import sync_auth_service_user_by_email_from_pg
from orcia_api.routers._auth_policy_runtime import resolve_auth_policy_runtime
from orcia_api.routers._iam_accounts_passwords import (
    provision_human_temporary_password,
    sync_in_memory_team_memberships,
)
from orcia_api.routers._iam_accounts_routes_helpers import (
    is_pg_sync_enabled as _pg_enabled,
)
from orcia_api.routers._iam_accounts_routes_helpers import (
    refresh_evaluator_org_units_from_pg,
)
from orcia_api.routers._iam_accounts_routes_helpers import (
    resolve_trace_id as _trace,
)
from orcia_api.routers._org_units_delegation_helpers import (
    ensure_evaluator_org_units_synced,
    is_observer_request,
    record_governance_audit_event,
    resolve_evaluator_target_node,
    resolve_org_caller,
    serialize_org_unit_with_capabilities,
)
from orcia_api.routers.auth import PROBLEM_RESPONSES
from orcia_api.schemas.auth_and_org import (
    OrgUnitInviteUserRequest,
    OrgUnitInviteUserResponse,
)
from orcia_core.bootstrap import (
    create_iam_account_on_postgres18,
    list_org_units_from_postgres18,
    sync_and_list_iam_accounts_from_postgres18,
)
from orcia_core.observability.logging import get_logger
from orcia_core.permissions import (
    IamAccountRecord,
    IamAccountsGovernanceService,
    IamAuthSource,
    OrgUnitNode,
    OrgUnitSummary,
    assert_can_invite_org_user,
    list_evaluator_org_unit_summaries,
)
from orcia_core.permissions.errors import (
    ObserverModeReadOnlyError,
    OrciaDomainError,
    ValidationDomainError,
)

logger = get_logger("orcia.api.org_unit_invitations")
router = APIRouter()

INVITATION_PROBLEM_RESPONSES = {
    **PROBLEM_RESPONSES,
    409: PROBLEM_RESPONSES[422],
}


def _apply_in_memory_org_attachment(
    evaluator_nodes: list[OrgUnitNode],
    *,
    evaluator_upsert: object,
    target_node: OrgUnitNode,
    canonical_kind: str,
    principal_id: str,
) -> None:
    """Attach invited user onto in-memory `OrgUnitNode` when PG sync is disabled."""
    del evaluator_nodes
    upsert = evaluator_upsert  # MatrixPermissionEvaluator.upsert_org_unit
    next_leads = list(target_node.lead_user_ids)
    next_onto = list(target_node.ontology_lead_user_ids)
    if canonical_kind in ("TEAM_LEAD", "BU_LEAD") and principal_id not in next_leads:
        next_leads.append(principal_id)
    elif canonical_kind == "ONTOLOGY_LEAD" and principal_id not in next_onto:
        next_onto.append(principal_id)
    if canonical_kind in ("TEAM_LEAD", "BU_LEAD", "ONTOLOGY_LEAD"):
        upsert(  # type: ignore[operator]
            OrgUnitNode(
                id=target_node.id,
                slug=target_node.slug,
                name=target_node.name,
                unit_type=target_node.unit_type,
                parent_id=target_node.parent_id,
                billing_enabled=target_node.billing_enabled,
                lead_user_id=next_leads[0] if next_leads else None,
                lead_user_ids=tuple(next_leads),
                ontology_lead_user_ids=tuple(next_onto),
                member_user_ids=target_node.member_user_ids,
            )
        )


@router.post(
    "/org-units/invite-user",
    response_model=OrgUnitInviteUserResponse,
    summary=(
        "Invite a new human user scoped to a governed organizational unit "
        "(`BU_LEAD` / `PLATFORM_ADMIN`)"
    ),
    responses=INVITATION_PROBLEM_RESPONSES,
)
async def invite_org_unit_user(
    payload: OrgUnitInviteUserRequest,
    request: Request,
    iam_svc: Annotated[IamAccountsGovernanceService, Depends(get_iam_accounts_service)],
    persona_key: str | None = Query(default=None, min_length=1, max_length=64),
) -> OrgUnitInviteUserResponse:
    auth_svc = get_auth_service(request)
    caller = resolve_org_caller(request, persona_key)
    await ensure_evaluator_org_units_synced(request, auth_svc.evaluator)
    if is_observer_request(request, caller):
        raise ObserverModeReadOnlyError(instance=str(request.url.path))

    target_node = resolve_evaluator_target_node(
        auth_svc.evaluator, payload.target_org_unit_id, allow_enterprise=True
    )
    canonical_kind, effective_roles = assert_can_invite_org_user(
        caller,
        target_unit=target_node,
        assignment_role=payload.assignment_role,
        org_units=auth_svc.evaluator.org_units,
        instance=str(request.url.path),
    )

    cleaned_email = payload.email.strip().lower()
    cleaned_name = payload.display_name.strip()
    if not cleaned_email or "@" not in cleaned_email:
        raise ValidationDomainError(
            instance=str(request.url.path),
            detail_override="Adresse e-mail invalide pour l'invitation utilisateur.",
        )
    if not cleaned_name:
        raise ValidationDomainError(
            instance=str(request.url.path),
            detail_override="Le nom complet de l'utilisateur invité est requis.",
        )

    policy_state, _, _ = await resolve_auth_policy_runtime(request)
    effective_auth_source: IamAuthSource = (
        "OIDC_FEDERATED" if policy_state.auth_mode == "SSO" else "LOCAL_PASSWORD"
    )

    is_enterprise_root = target_node.unit_type == "ENTERPRISE"
    team_ids = (
        [target_node.id] if canonical_kind == "TEAM_MEMBER" and not is_enterprise_root else []
    )
    led_team_ids = (
        [target_node.id] if canonical_kind == "TEAM_LEAD" and not is_enterprise_root else []
    )
    led_bu_ids = [target_node.id] if canonical_kind == "BU_LEAD" and not is_enterprise_root else []
    ontology_led_bu_ids = (
        [target_node.id] if canonical_kind == "ONTOLOGY_LEAD" and not is_enterprise_root else []
    )

    created: IamAccountRecord | None = None
    updated_summary: OrgUnitSummary | None = None

    if _pg_enabled():
        try:
            engine = get_or_create_shared_db_engine(request)
            await sync_and_list_iam_accounts_from_postgres18(engine)
            created = await create_iam_account_on_postgres18(
                engine,
                principal_id=cleaned_email,
                display_name=cleaned_name,
                email=cleaned_email,
                account_kind="HUMAN",
                auth_source=effective_auth_source,
                roles=effective_roles,
                team_ids=team_ids,
                status="ACTIVE",
                led_bu_ids=led_bu_ids,
                led_team_ids=led_team_ids,
                ontology_led_bu_ids=ontology_led_bu_ids,
                instance=str(request.url.path),
            )
            await refresh_evaluator_org_units_from_pg(auth_svc, engine)
            summaries = await list_org_units_from_postgres18(engine)
            updated_summary = next((s for s in summaries if s.id == target_node.id), None)
        except OrciaDomainError:
            raise
        except Exception as exc:
            logger.warning("org_unit_invite_pg_fallback", error_type=type(exc).__name__)
            created = None

    if created is None:
        first_admin = get_accostage_service(request).first_admin
        iam_svc.ensure_day0_admin_account(
            email=first_admin.email if first_admin else None,
            display_name=first_admin.display_name if first_admin else None,
        )
        created = iam_svc.create_account(
            principal_id=cleaned_email,
            display_name=cleaned_name,
            email=cleaned_email,
            account_kind="HUMAN",
            auth_source=effective_auth_source,
            roles=effective_roles,
            team_ids=team_ids,
            status="ACTIVE",
            led_bu_ids=led_bu_ids,
            led_team_ids=led_team_ids,
            ontology_led_bu_ids=ontology_led_bu_ids,
            instance=str(request.url.path),
        )
        if not is_enterprise_root:
            if canonical_kind == "TEAM_MEMBER":
                sync_in_memory_team_memberships(
                    auth_svc.evaluator, created.principal_id, (target_node.id,)
                )
            else:
                _apply_in_memory_org_attachment(
                    list(auth_svc.evaluator.org_units),
                    evaluator_upsert=auth_svc.evaluator.upsert_org_unit,
                    target_node=target_node,
                    canonical_kind=canonical_kind,
                    principal_id=created.principal_id,
                )

    temp_pw: str | None = None
    if effective_auth_source == "LOCAL_PASSWORD":
        shared_engine = get_or_create_shared_db_engine(request) if _pg_enabled() else None
        temp_pw = await provision_human_temporary_password(
            account_id=created.id,
            email=cleaned_email,
            display_name=cleaned_name,
            roles=created.roles,
            auth_svc=auth_svc,
            engine=shared_engine,
            primary_org_unit_id=None if is_enterprise_root else target_node.id,
        )

    await sync_auth_service_user_by_email_from_pg(request, auth_svc, cleaned_email)

    if updated_summary is None:
        all_summaries = list_evaluator_org_unit_summaries(
            auth_svc.evaluator.org_units,
            [w.owner_org_unit_id for w in auth_svc.evaluator.workspaces],
            auth_svc.evaluator.workspaces,
        )
        updated_summary = next(
            (s for s in all_summaries if s.id == target_node.id),
            OrgUnitSummary(
                id=target_node.id,
                slug=target_node.slug,
                name=target_node.name,
                kind="BU" if target_node.unit_type in ("BU", "TRIBE") else "TEAM",
                parent_id=target_node.parent_id,
                billing_enabled=target_node.billing_enabled,
                lead_user_id=target_node.lead_user_id,
                lead_user_ids=target_node.lead_user_ids,
                ontology_lead_user_ids=target_node.ontology_lead_user_ids,
                member_user_ids=target_node.member_user_ids,
            ),
        )

    await record_governance_audit_event(
        request,
        actor=caller,
        event_type="IAM_ACCOUNT_INVITED",
        summary=f"Invitation de {cleaned_name} ({cleaned_email}) sur '{target_node.name}'",
        org_unit_id=target_node.id,
        scope_path=target_node.slug or "GLOBAL",
        metadata={
            "invited_email": cleaned_email,
            "assignment_role": payload.assignment_role.strip().upper(),
            "effective_roles": list(created.roles),
            "auth_source": effective_auth_source,
        },
    )

    return OrgUnitInviteUserResponse(
        account_id=created.id,
        principal_id=created.principal_id,
        email=cleaned_email,
        display_name=created.display_name,
        target_org_unit_id=target_node.id,
        assignment_role=payload.assignment_role.strip().upper(),
        effective_roles=list(created.roles),
        temporary_password=temp_pw,  # pragma: allowlist secret
        must_change_password=effective_auth_source == "LOCAL_PASSWORD",
        org_unit=serialize_org_unit_with_capabilities(
            request, caller, updated_summary, auth_svc.evaluator
        ),
        trace_id=_trace(request),
    )


__all__ = ["router"]
