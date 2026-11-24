"""Evaluation & ticket state transition helpers for `PermissionBrokerService`."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import replace
from typing import Any, Literal

from orcia_core.permissions._permissions_locales import BROKER_WORKSPACE_SOURCE_LABEL_LOCALES
from orcia_core.permissions.broker_models import (
    PermissionBrokerPolicy,
    PermissionBrokerTicket,
    PermissionCheckOutcome,
    reject_control_chars,
    resolve_active_access_request_channel,
)
from orcia_core.permissions.errors import (
    ConfusedDeputyBlockedError,
    PermissionBrokerDeniedError,
    ValidationDomainError,
)
from orcia_core.permissions.evaluator import MatrixPermissionEvaluator
from orcia_core.permissions.models import ExecutionIdentityMode, UserIdentity
from orcia_kernel.enums import DEFAULT_LOCALE, SupportedLocale
from orcia_kernel.ids import new_uuid7_str
from orcia_kernel.ports import AccessRequestChannelPort


def evaluate_access_and_build_outcome(
    user: UserIdentity,
    *,
    policy: PermissionBrokerPolicy,
    cleaned_uri: str,
    execution_identity: ExecutionIdentityMode,
    clean_step: str,
    step_number: int,
    workspace_id: str | None,
    resource_id: str | None,
    simulated_upstream_status: Literal[200, 401, 403] | None,
    granted_external_roles: tuple[str, ...],
    evaluator: MatrixPermissionEvaluator | None,
    has_passthrough_fn: Callable[[str, str, str], bool],
    access_channel: AccessRequestChannelPort | None,
    instance: str | None,
) -> tuple[PermissionCheckOutcome, bool]:
    """Evaluate Passthrough/SP authority and build granted/denied check outcome."""
    sp_ok = policy.service_principal_allowed and bool(policy.approved_by_admin_id)
    if execution_identity == "service_principal" and not sp_ok:
        raise ConfusedDeputyBlockedError(instance=instance)

    denied_status: Literal[401, 403] | None = None
    if evaluator is not None:
        acl = evaluator.get_catalog_acl_by_uri(cleaned_uri)
        eff_res_id = (
            reject_control_chars(resource_id, "resource_id", instance=instance)
            if resource_id
            else (acl.resource_id if acl is not None else None)
        )
        if eff_res_id is not None:
            eff, _ = evaluator.evaluate_catalog_resource(
                user, eff_res_id, workspace_id=workspace_id, instance=instance
            )
            denied_status = None if eff.can_execute else 403

    if denied_status is None:
        cred = has_passthrough_fn(user.id, policy.connector_scheme, cleaned_uri)
        is_admin = user.platform_role == "PLATFORM_ADMIN"
        pt_ok = policy.required_role in granted_external_roles or is_admin or cred
        if simulated_upstream_status in (401, 403):
            denied_status = simulated_upstream_status
        elif execution_identity == "passthrough" and not pt_ok:
            denied_status = 403

    if denied_status is None:
        return (
            PermissionCheckOutcome(
                True,
                "GRANTED",
                execution_identity,
                cleaned_uri,
                policy.connector_scheme,
                policy,
            ),
            False,
        )

    channel = access_channel or resolve_active_access_request_channel()
    req_url = channel.build_access_request_url(
        policy.request_url_template,
        target_uri=cleaned_uri,
        required_role=policy.required_role,
        approver_team=policy.approver_team,
        requester_email=user.email,
        step_key=clean_step,
        execution_identity=execution_identity,
    )
    hint = channel.build_access_request_hint(
        target_uri=cleaned_uri,
        required_role=policy.required_role,
        approver_team=policy.approver_team,
        sla_hours=policy.sla_hours,
    )
    ticket_id = new_uuid7_str()
    ticket = PermissionBrokerTicket(
        ticket_id,
        f"tkt-{clean_step}-{ticket_id[-6:]}",
        workspace_id,
        user.id,
        policy.id,
        clean_step,
        step_number,
        "PERMISSION_DENIED_STEP",
        "WAITING_FOR_PERMISSION",
        cleaned_uri,
        policy.connector_scheme,
        execution_identity,
        denied_status,
        policy.required_role,
        policy.approver_team,
        policy.sla_hours,
        req_url,
        hint,
        policy.procedure_markdown,
        req_url,
    )
    return (
        PermissionCheckOutcome(
            False,
            "WAITING_FOR_PERMISSION",
            execution_identity,
            cleaned_uri,
            policy.connector_scheme,
            policy,
            ticket,
            hint,
        ),
        True,
    )


def enrich_fallback_policy_with_datasource(
    policy: PermissionBrokerPolicy,
    ds_match: dict[str, Any] | None,
    *,
    locale: SupportedLocale = DEFAULT_LOCALE,
) -> PermissionBrokerPolicy:
    """Append localized associated workspace datasource details onto fallback policies."""
    if ds_match is None or not policy.policy_key.endswith("-default-fallback"):
        return policy
    tpl = BROKER_WORKSPACE_SOURCE_LABEL_LOCALES.get(
        locale, BROKER_WORKSPACE_SOURCE_LABEL_LOCALES[DEFAULT_LOCALE]
    )
    suffix = tpl.format(alias=ds_match["alias"], uri=ds_match["uri"])
    return replace(policy, procedure_markdown=f"{policy.procedure_markdown}\n\n{suffix}".strip())


def raise_if_denied_ticket(
    outcome: PermissionCheckOutcome, *, raise_on_denied: bool, instance: str | None
) -> None:
    if raise_on_denied:
        raise PermissionBrokerDeniedError(
            instance=instance, permission_broker_hint=outcome.permission_broker_hint or ""
        )


def validate_positive_step_number(step_number: int, *, instance: str | None) -> None:
    if step_number <= 0:
        raise ValidationDomainError(
            detail_override="step_number must be strictly positive.", instance=instance
        )


__all__ = [
    "enrich_fallback_policy_with_datasource",
    "evaluate_access_and_build_outcome",
    "raise_if_denied_ticket",
    "validate_positive_step_number",
]
