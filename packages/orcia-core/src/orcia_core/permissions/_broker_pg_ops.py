"""Async PG18 check/interception and ticket transition helpers for `PermissionBrokerService`."""

from __future__ import annotations

from dataclasses import replace
from typing import TYPE_CHECKING, Literal

from orcia_core.permissions._broker_evaluation import (
    enrich_fallback_policy_with_datasource,
    evaluate_access_and_build_outcome,
    raise_if_denied_ticket,
    validate_positive_step_number,
)
from orcia_core.permissions.broker_models import (
    BrokerTicketAction,
    PermissionBrokerPolicy,
    PermissionBrokerTicket,
    PermissionCheckOutcome,
    reject_control_chars,
)
from orcia_core.permissions.errors import ResourceNotFoundError, ValidationDomainError
from orcia_core.permissions.models import ExecutionIdentityMode, UserIdentity

if TYPE_CHECKING:
    from orcia_core.permissions.broker import PermissionBrokerService


async def check_or_intercept_access_pg(
    service: PermissionBrokerService,
    user: UserIdentity,
    *,
    target_uri: str,
    execution_identity: ExecutionIdentityMode = "passthrough",
    step_key: str = "step-02-execution",
    step_number: int = 2,
    workspace_id: str | None = None,
    resource_id: str | None = None,
    simulated_upstream_status: Literal[200, 401, 403] | None = None,
    granted_external_roles: tuple[str, ...] = (),
    raise_on_denied: bool = True,
    instance: str | None = None,
) -> PermissionCheckOutcome:
    """Check access against PG18 policies + datasources and persist denial ticket."""
    if not await service._pg_ready():
        return service.check_or_intercept_access(
            user,
            target_uri=target_uri,
            execution_identity=execution_identity,
            step_key=step_key,
            step_number=step_number,
            workspace_id=workspace_id,
            resource_id=resource_id,
            simulated_upstream_status=simulated_upstream_status,
            granted_external_roles=granted_external_roles,
            raise_on_denied=raise_on_denied,
            instance=instance,
        )
    assert service._sql_repo is not None
    service._enforce_mutation_allowed(user, workspace_id, instance=instance)
    clean_step = reject_control_chars(step_key, "step_key", instance=instance)
    validate_positive_step_number(step_number, instance=instance)
    await service.list_policies_async()
    cleaned_uri = target_uri.strip()
    ds_match = await service._sql_repo.find_workspace_datasource(
        cleaned_uri, workspace_id=workspace_id
    )
    policy = enrich_fallback_policy_with_datasource(
        service.resolve_matching_policy(cleaned_uri, instance=instance),
        ds_match,
    )
    outcome, denied = evaluate_access_and_build_outcome(
        user,
        policy=policy,
        cleaned_uri=cleaned_uri,
        execution_identity=execution_identity,
        clean_step=clean_step,
        step_number=step_number,
        workspace_id=workspace_id,
        resource_id=resource_id,
        simulated_upstream_status=simulated_upstream_status,
        granted_external_roles=granted_external_roles,
        evaluator=service._evaluator,
        has_passthrough_fn=service.has_passthrough_credential,
        access_channel=service._access_channel,
        instance=instance,
    )
    if denied and outcome.ticket is not None:
        persisted = await service._sql_repo.insert_ticket(
            outcome.ticket, policy=policy, requester_email=user.email
        )
        service._tickets[persisted.id] = persisted
        outcome = replace(outcome, ticket=persisted)
        raise_if_denied_ticket(outcome, raise_on_denied=raise_on_denied, instance=instance)
    return outcome


def apply_ticket_action_sync(
    service: PermissionBrokerService,
    user: UserIdentity,
    ticket_id: str,
    action: BrokerTicketAction | Literal["GRANT"],
    *,
    workspace_id: str | None = None,
    grant_permission: bool = False,
    instance: str | None = None,
) -> PermissionBrokerTicket:
    """Apply `PAUSE`/`REPLAY`/`GRANT` state transition in memory."""
    clean_id = reject_control_chars(ticket_id, "ticket_id", instance=instance)
    target = service._tickets.get(clean_id) or next(
        (t for t in service._tickets.values() if t.ticket_key == clean_id), None
    )
    if target is None or (
        workspace_id and target.workspace_id and workspace_id != target.workspace_id
    ):
        raise ResourceNotFoundError(instance=instance)
    service._enforce_mutation_allowed(user, target.workspace_id or workspace_id, instance=instance)
    if action == "PAUSE" and target.status in ("REPLAYED", "GRANTED"):
        raise ValidationDomainError(detail_override="Ticket already replayed.", instance=instance)
    is_grant = action == "GRANT" or grant_permission
    state_val: Literal["PAUSED", "REPLAYED", "GRANTED"] = (
        "PAUSED" if action == "PAUSE" else ("GRANTED" if is_grant else "REPLAYED")
    )
    updated = replace(target, step_state=state_val, status=state_val)
    service._tickets[updated.id] = updated
    return updated


async def apply_ticket_action_pg(
    service: PermissionBrokerService,
    user: UserIdentity,
    ticket_id: str,
    action: BrokerTicketAction | Literal["GRANT"],
    *,
    workspace_id: str | None = None,
    grant_permission: bool = False,
    instance: str | None = None,
) -> PermissionBrokerTicket:
    """Transition ticket state (`PAUSED` / `REPLAYED` / `GRANTED`) in PG18."""
    if not await service._pg_ready():
        return apply_ticket_action_sync(
            service,
            user,
            ticket_id,
            action,
            workspace_id=workspace_id,
            grant_permission=grant_permission,
            instance=instance,
        )
    assert service._sql_repo is not None
    clean_id = reject_control_chars(ticket_id, "ticket_id", instance=instance)
    target = await service._sql_repo.get_ticket(clean_id)
    if target is None or (
        workspace_id and target.workspace_id and workspace_id != target.workspace_id
    ):
        raise ResourceNotFoundError(instance=instance)
    service._enforce_mutation_allowed(user, target.workspace_id or workspace_id, instance=instance)
    if action == "PAUSE" and target.status in ("REPLAYED", "GRANTED"):
        raise ValidationDomainError(detail_override="Ticket already replayed.", instance=instance)
    is_grant = action == "GRANT" or grant_permission
    state_val: Literal["PAUSED", "REPLAYED", "GRANTED"] = (
        "PAUSED" if action == "PAUSE" else ("GRANTED" if is_grant else "REPLAYED")
    )
    updated = await service._sql_repo.update_ticket_state(
        clean_id, step_state=state_val, status=state_val
    )
    assert updated is not None
    service._tickets[updated.id] = updated
    return updated


async def import_policy_markdown_pg(
    service: PermissionBrokerService,
    user: UserIdentity,
    markdown_text: str,
    *,
    policy_key: str | None = None,
    workspace_id: str | None = None,
    instance: str | None = None,
) -> PermissionBrokerPolicy:
    """Import and persist a Markdown + YAML KB policy into PG18."""
    if not await service._pg_ready():
        return service.import_policy_markdown(
            user, markdown_text, policy_key=policy_key, workspace_id=workspace_id, instance=instance
        )
    assert service._sql_repo is not None
    policy = service._prepare_policy_upsert(
        user, markdown_text, policy_key=policy_key, workspace_id=workspace_id, instance=instance
    )
    persisted = await service._sql_repo.upsert_policy(policy)
    service._policies[persisted.policy_key] = persisted
    return persisted


__all__ = [
    "apply_ticket_action_pg",
    "apply_ticket_action_sync",
    "check_or_intercept_access_pg",
    "import_policy_markdown_pg",
]
