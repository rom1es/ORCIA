"""PermissionBrokerService: Passthrough vs Service Principal Guard, KB Matcher & Jira Broker.

Pure hexagonal domain module (Story 1.4, AD-6, FR-22, UX-DR11) with optional PG18 SQL adapter.
"""

from __future__ import annotations

import fnmatch
from typing import Literal

from orcia_core.permissions._broker_evaluation import (
    evaluate_access_and_build_outcome,
    raise_if_denied_ticket,
    validate_positive_step_number,
)
from orcia_core.permissions._broker_mixin import PermissionBrokerDelegationMixin
from orcia_core.permissions._broker_policy_ops import (
    build_default_permission_broker_service,
    check_passthrough_credential,
    filter_tickets_by_scope,
    list_policies_pg,
    list_tickets_pg,
    prepare_and_import_policy_sync,
    prepare_policy_upsert,
)
from orcia_core.permissions._internal.sql_permission_broker import SqlPermissionBrokerRepository
from orcia_core.permissions.broker_models import (
    BrokerConnectorScheme,
    BrokerStepState,
    BrokerTicketAction,
    BrokerTicketStatus,
    PermissionBrokerPolicy,
    PermissionBrokerTicket,
    PermissionCheckOutcome,
    build_jira_request_url,
    build_prefilled_jira_request_url,
    extract_connector_host,
    extract_connector_scheme,
    get_allowed_broker_schemes,
    parse_permission_kb_markdown,
    reject_control_chars,
)
from orcia_core.permissions.crypto import PassthroughVaultCipher
from orcia_core.permissions.errors import (
    ObserverModeReadOnlyError,
    ResourceNotFoundError,
)
from orcia_core.permissions.evaluator import MatrixPermissionEvaluator
from orcia_core.permissions.models import (
    ExecutionIdentityMode,
    PassthroughCredentialRecord,
    UserIdentity,
)
from orcia_kernel.ports import AccessRequestChannelPort


class PermissionBrokerService(PermissionBrokerDelegationMixin):
    """Domain service enforcing `passthrough` default and brokering `401/403` denials."""

    def __init__(
        self,
        *,
        policies: tuple[PermissionBrokerPolicy, ...],
        tickets: tuple[PermissionBrokerTicket, ...] = (),
        evaluator: MatrixPermissionEvaluator | None = None,
        passthrough_credentials: tuple[PassthroughCredentialRecord, ...] = (),
        vault_cipher: PassthroughVaultCipher | None = None,
        access_channel: AccessRequestChannelPort | None = None,
        engine: object | None = None,
    ) -> None:
        self._policies: dict[str, PermissionBrokerPolicy] = {p.policy_key: p for p in policies}
        self._tickets: dict[str, PermissionBrokerTicket] = {t.id: t for t in tickets}
        self._evaluator, self._vault_cipher = evaluator, vault_cipher
        self._access_channel = access_channel
        self._engine: object | None = engine
        self._sql_repo: SqlPermissionBrokerRepository | None = (
            SqlPermissionBrokerRepository(engine) if engine is not None else None
        )
        self._passthrough_credentials: dict[tuple[str, str, str], PassthroughCredentialRecord] = {
            (c.user_id, c.connector_scheme.lower(), c.target_host.lower()): c
            for c in passthrough_credentials
        }

    def set_engine(self, engine: object | None) -> None:
        """Bind or refresh the SQLAlchemy `AsyncEngine` from the Composition Root."""
        self._engine = engine
        self._sql_repo = SqlPermissionBrokerRepository(engine) if engine is not None else None

    async def _pg_ready(self) -> bool:
        return self._sql_repo is not None and await self._sql_repo.pg_tables_ready()

    def register_passthrough_credential(self, record: PassthroughCredentialRecord) -> None:
        key = (record.user_id, record.connector_scheme.lower(), record.target_host.lower())
        self._passthrough_credentials[key] = record

    def has_passthrough_credential(self, user_id: str, scheme: str, target_uri: str) -> bool:
        return check_passthrough_credential(self, user_id, scheme, target_uri)

    def list_policies(self) -> list[PermissionBrokerPolicy]:
        return list(self._policies.values())

    async def list_policies_async(self) -> list[PermissionBrokerPolicy]:
        """List policies from PG18 (seeding defaults idempotently if missing)."""
        return await list_policies_pg(self)

    def _filter_tickets_by_scope(
        self,
        tickets: list[PermissionBrokerTicket],
        workspace_id: str | None,
        user: UserIdentity | None,
        instance: str | None,
    ) -> list[PermissionBrokerTicket]:
        return filter_tickets_by_scope(self, tickets, workspace_id, user, instance)

    def list_tickets(
        self,
        workspace_id: str | None = None,
        *,
        user: UserIdentity | None = None,
        instance: str | None = None,
    ) -> list[PermissionBrokerTicket]:
        return self._filter_tickets_by_scope(
            list(self._tickets.values()), workspace_id, user, instance
        )

    async def list_tickets_async(
        self,
        workspace_id: str | None = None,
        *,
        user: UserIdentity | None = None,
        instance: str | None = None,
    ) -> list[PermissionBrokerTicket]:
        """List tickets from PG18 with scope access filtering."""
        return await list_tickets_pg(self, workspace_id, user=user, instance=instance)

    def _enforce_mutation_allowed(
        self, user: UserIdentity, workspace_id: str | None, *, instance: str | None = None
    ) -> None:
        if user.platform_role in ("OBSERVER", "BU_DIRECTOR"):
            raise ObserverModeReadOnlyError(instance=instance)
        if workspace_id is not None and self._evaluator is not None:
            self._evaluator.enforce_scope_mutation_guard(user, workspace_id, instance=instance)

    def _prepare_policy_upsert(
        self,
        user: UserIdentity,
        markdown_text: str,
        *,
        policy_key: str | None = None,
        workspace_id: str | None = None,
        instance: str | None = None,
    ) -> PermissionBrokerPolicy:
        return prepare_policy_upsert(
            self,
            user,
            markdown_text,
            policy_key=policy_key,
            workspace_id=workspace_id,
            instance=instance,
        )

    def import_policy_markdown(
        self,
        user: UserIdentity,
        markdown_text: str,
        *,
        policy_key: str | None = None,
        workspace_id: str | None = None,
        instance: str | None = None,
    ) -> PermissionBrokerPolicy:
        return prepare_and_import_policy_sync(
            self,
            user,
            markdown_text,
            policy_key=policy_key,
            workspace_id=workspace_id,
            instance=instance,
        )

    async def import_policy_markdown_async(
        self,
        user: UserIdentity,
        markdown_text: str,
        *,
        policy_key: str | None = None,
        workspace_id: str | None = None,
        instance: str | None = None,
    ) -> PermissionBrokerPolicy:
        """Import and persist a Markdown + YAML KB policy into PG18."""
        from orcia_core.permissions._broker_pg_ops import import_policy_markdown_pg

        return await import_policy_markdown_pg(
            self,
            user,
            markdown_text,
            policy_key=policy_key,
            workspace_id=workspace_id,
            instance=instance,
        )

    def resolve_matching_policy(
        self, target_uri: str, *, instance: str | None = None
    ) -> PermissionBrokerPolicy:
        extract_connector_scheme(target_uri, instance=instance)
        cleaned_uri = target_uri.strip()
        candidates = [
            p for p in self._policies.values() if fnmatch.fnmatchcase(cleaned_uri, p.uri_pattern)
        ]
        if not candidates:
            msg = f"No Permission Broker policy found for URI {cleaned_uri!r}."
            raise ResourceNotFoundError(detail_override=msg, instance=instance)
        candidates.sort(key=lambda p: len(p.uri_pattern.replace("*", "")), reverse=True)
        return candidates[0]

    def check_or_intercept_access(
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
        self._enforce_mutation_allowed(user, workspace_id, instance=instance)
        clean_step = reject_control_chars(step_key, "step_key", instance=instance)
        validate_positive_step_number(step_number, instance=instance)
        policy = self.resolve_matching_policy(target_uri, instance=instance)
        outcome, denied = evaluate_access_and_build_outcome(
            user,
            policy=policy,
            cleaned_uri=target_uri.strip(),
            execution_identity=execution_identity,
            clean_step=clean_step,
            step_number=step_number,
            workspace_id=workspace_id,
            resource_id=resource_id,
            simulated_upstream_status=simulated_upstream_status,
            granted_external_roles=granted_external_roles,
            evaluator=self._evaluator,
            has_passthrough_fn=self.has_passthrough_credential,
            access_channel=self._access_channel,
            instance=instance,
        )
        if denied and outcome.ticket is not None:
            self._tickets[outcome.ticket.id] = outcome.ticket
            raise_if_denied_ticket(outcome, raise_on_denied=raise_on_denied, instance=instance)
        return outcome


__all__ = [
    "BrokerConnectorScheme",
    "BrokerStepState",
    "BrokerTicketAction",
    "BrokerTicketStatus",
    "PermissionBrokerPolicy",
    "PermissionBrokerService",
    "PermissionBrokerTicket",
    "PermissionCheckOutcome",
    "build_default_permission_broker_service",
    "build_jira_request_url",
    "build_prefilled_jira_request_url",
    "extract_connector_host",
    "extract_connector_scheme",
    "get_allowed_broker_schemes",
    "parse_permission_kb_markdown",
]
