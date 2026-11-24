"""Async & ticket action mixin for `PermissionBrokerService` (`Story 1.4`, `Story 27.7`)."""

from __future__ import annotations

from typing import TYPE_CHECKING, Literal, cast

from orcia_core.permissions._broker_pg_ops import (
    apply_ticket_action_pg,
    apply_ticket_action_sync,
    check_or_intercept_access_pg,
)
from orcia_core.permissions.broker_models import (
    BrokerTicketAction,
    PermissionBrokerTicket,
    PermissionCheckOutcome,
)
from orcia_core.permissions.models import ExecutionIdentityMode, UserIdentity

if TYPE_CHECKING:
    from orcia_core.permissions.broker import PermissionBrokerService


class PermissionBrokerDelegationMixin:
    """Async access checks and sync/async ticket decision methods."""

    async def check_or_intercept_access_async(
        self,
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
        return await check_or_intercept_access_pg(
            cast("PermissionBrokerService", self),
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

    def apply_ticket_action(
        self,
        user: UserIdentity,
        ticket_id: str,
        action: BrokerTicketAction | Literal["GRANT"],
        *,
        workspace_id: str | None = None,
        grant_permission: bool = False,
        instance: str | None = None,
    ) -> PermissionBrokerTicket:
        return apply_ticket_action_sync(
            cast("PermissionBrokerService", self),
            user,
            ticket_id,
            action,
            workspace_id=workspace_id,
            grant_permission=grant_permission,
            instance=instance,
        )

    async def apply_ticket_action_async(
        self,
        user: UserIdentity,
        ticket_id: str,
        action: BrokerTicketAction | Literal["GRANT"],
        *,
        workspace_id: str | None = None,
        grant_permission: bool = False,
        instance: str | None = None,
    ) -> PermissionBrokerTicket:
        """Transition ticket state (`PAUSED` / `REPLAYED` / `GRANTED`) in PG18."""
        return await apply_ticket_action_pg(
            cast("PermissionBrokerService", self),
            user,
            ticket_id,
            action,
            workspace_id=workspace_id,
            grant_permission=grant_permission,
            instance=instance,
        )
