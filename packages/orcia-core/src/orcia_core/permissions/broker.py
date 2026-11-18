"""PermissionBrokerService: Passthrough vs Service Principal Guard, KB Matcher & Jira Broker.

Pure hexagonal domain module (Story 1.4, AD-6, FR-22, UX-DR11) with optional PG18 SQL adapter.
"""

from __future__ import annotations

import fnmatch
from dataclasses import asdict, replace
from typing import Literal

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
    resolve_active_access_request_channel,
)
from orcia_core.permissions.crypto import PassthroughVaultCipher
from orcia_core.permissions.errors import (
    ConfusedDeputyBlockedError,
    ObserverModeReadOnlyError,
    PermissionBrokerDeniedError,
    ResourceNotFoundError,
    ScopeAccessDeniedError,
    ValidationDomainError,
)
from orcia_core.permissions.evaluator import MatrixPermissionEvaluator
from orcia_core.permissions.models import (
    ExecutionIdentityMode,
    PassthroughCredentialRecord,
    UserIdentity,
)
from orcia_core.permissions.seeds import (
    DEFAULT_PERMISSION_BROKER_POLICY_SEEDS,
    DEFAULT_PERMISSION_BROKER_TICKET_SEEDS,
)
from orcia_kernel.ids import new_uuid7_str
from orcia_kernel.ports import AccessRequestChannelPort


class PermissionBrokerService:
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
        key = (user_id, scheme.lower(), extract_connector_host(target_uri))
        rec = self._passthrough_credentials.get(key)
        if rec is None:
            return False
        if self._vault_cipher is not None:
            return bool(
                self._vault_cipher.decrypt(
                    rec.user_id, rec.ciphertext_b64, rec.nonce_b64,
                    connector_scheme=rec.connector_scheme, target_host=rec.target_host,
                    key_version=rec.key_version,
                )
            )  # fmt: skip
        return bool(rec.ciphertext_b64)

    def list_policies(self) -> list[PermissionBrokerPolicy]:
        return list(self._policies.values())

    async def list_policies_async(self) -> list[PermissionBrokerPolicy]:
        """List policies from PG18 (seeding defaults idempotently if missing)."""
        if not await self._pg_ready():
            return self.list_policies()
        assert self._sql_repo is not None
        policies = await self._sql_repo.ensure_policies_seeded(tuple(self._policies.values()))
        for p in policies:
            self._policies[p.policy_key] = p
        return policies

    def _filter_tickets_by_scope(
        self,
        tickets: list[PermissionBrokerTicket],
        workspace_id: str | None,
        user: UserIdentity | None,
        instance: str | None,
    ) -> list[PermissionBrokerTicket]:
        ev = self._evaluator
        if workspace_id is not None:
            clean_ws = reject_control_chars(workspace_id, "workspace_id", instance=instance)
            if user and ev and ev.resolve_workspace_access(user, clean_ws) is None:
                raise ScopeAccessDeniedError(instance=instance)
            return [t for t in tickets if t.workspace_id in (None, clean_ws)]
        if user is not None and ev is not None:
            return [
                t
                for t in tickets
                if not t.workspace_id or ev.resolve_workspace_access(user, t.workspace_id)
            ]
        return tickets

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
        if not await self._pg_ready():
            return self.list_tickets(workspace_id, user=user, instance=instance)
        assert self._sql_repo is not None
        if workspace_id is not None:
            clean_ws = reject_control_chars(workspace_id, "workspace_id", instance=instance)
            if (
                user
                and self._evaluator
                and self._evaluator.resolve_workspace_access(user, clean_ws) is None
            ):
                raise ScopeAccessDeniedError(instance=instance)
            return await self._sql_repo.list_tickets(clean_ws)
        tickets = await self._sql_repo.list_tickets(None)
        return self._filter_tickets_by_scope(tickets, None, user, instance)

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
        self._enforce_mutation_allowed(user, workspace_id, instance=instance)
        policy = parse_permission_kb_markdown(
            markdown_text, policy_key=policy_key, instance=instance
        )
        if policy.service_principal_allowed and user.platform_role != "PLATFORM_ADMIN":
            raise ConfusedDeputyBlockedError(instance=instance)
        admin_id = user.id if policy.service_principal_allowed else None
        return replace(policy, approved_by_admin_id=admin_id)

    def import_policy_markdown(
        self,
        user: UserIdentity,
        markdown_text: str,
        *,
        policy_key: str | None = None,
        workspace_id: str | None = None,
        instance: str | None = None,
    ) -> PermissionBrokerPolicy:
        policy = self._prepare_policy_upsert(
            user, markdown_text, policy_key=policy_key, workspace_id=workspace_id, instance=instance
        )
        matches = [
            k
            for k, p in self._policies.items()
            if p.policy_key == policy.policy_key or p.uri_pattern == policy.uri_pattern
        ]
        existing = self._policies[matches[0]] if matches else None
        for k in matches:
            self._policies.pop(k, None)
        if existing is not None:
            policy = replace(policy, id=existing.id, policy_key=existing.policy_key)
        self._policies[policy.policy_key] = policy
        return policy

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
        if not await self._pg_ready():
            return self.import_policy_markdown(
                user,
                markdown_text,
                policy_key=policy_key,
                workspace_id=workspace_id,
                instance=instance,
            )
        assert self._sql_repo is not None
        policy = self._prepare_policy_upsert(
            user, markdown_text, policy_key=policy_key, workspace_id=workspace_id, instance=instance
        )
        persisted = await self._sql_repo.upsert_policy(policy)
        self._policies[persisted.policy_key] = persisted
        return persisted

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

    def _evaluate_access_and_build_outcome(
        self,
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
        instance: str | None,
    ) -> tuple[PermissionCheckOutcome, bool]:
        sp_ok = policy.service_principal_allowed and bool(policy.approved_by_admin_id)
        if execution_identity == "service_principal" and not sp_ok:
            raise ConfusedDeputyBlockedError(instance=instance)

        denied_status: Literal[401, 403] | None = None
        if self._evaluator is not None:
            acl = self._evaluator.get_catalog_acl_by_uri(cleaned_uri)
            eff_res_id = (
                reject_control_chars(resource_id, "resource_id", instance=instance)
                if resource_id
                else (acl.resource_id if acl is not None else None)
            )
            if eff_res_id is not None:
                eff, _ = self._evaluator.evaluate_catalog_resource(
                    user, eff_res_id, workspace_id=workspace_id, instance=instance
                )
                denied_status = None if eff.can_execute else 403

        if denied_status is None:
            cred = self.has_passthrough_credential(user.id, policy.connector_scheme, cleaned_uri)
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

        channel = self._access_channel or resolve_active_access_request_channel()
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
        if step_number <= 0:
            raise ValidationDomainError(
                detail_override="step_number must be strictly positive.", instance=instance
            )
        policy = self.resolve_matching_policy(target_uri, instance=instance)
        outcome, denied = self._evaluate_access_and_build_outcome(
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
            instance=instance,
        )
        if denied and outcome.ticket is not None:
            self._tickets[outcome.ticket.id] = outcome.ticket
            if raise_on_denied:
                raise PermissionBrokerDeniedError(
                    instance=instance, permission_broker_hint=outcome.permission_broker_hint or ""
                )
        return outcome

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
        if not await self._pg_ready():
            return self.check_or_intercept_access(
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
        assert self._sql_repo is not None
        self._enforce_mutation_allowed(user, workspace_id, instance=instance)
        clean_step = reject_control_chars(step_key, "step_key", instance=instance)
        if step_number <= 0:
            raise ValidationDomainError(
                detail_override="step_number must be strictly positive.", instance=instance
            )
        await self.list_policies_async()
        cleaned_uri = target_uri.strip()
        ds_match = await self._sql_repo.find_workspace_datasource(
            cleaned_uri, workspace_id=workspace_id
        )
        policy = self.resolve_matching_policy(cleaned_uri, instance=instance)
        if ds_match is not None and policy.policy_key.endswith("-default-fallback"):
            policy = replace(
                policy,
                procedure_markdown=(
                    f"{policy.procedure_markdown}\n\n"
                    f"**Source d'espace associée** : `{ds_match['alias']}` (`{ds_match['uri']}`)"
                ).strip(),
            )
        outcome, denied = self._evaluate_access_and_build_outcome(
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
            instance=instance,
        )
        if denied and outcome.ticket is not None:
            persisted = await self._sql_repo.insert_ticket(
                outcome.ticket, policy=policy, requester_email=user.email
            )
            self._tickets[persisted.id] = persisted
            outcome = replace(outcome, ticket=persisted)
            if raise_on_denied:
                raise PermissionBrokerDeniedError(
                    instance=instance, permission_broker_hint=outcome.permission_broker_hint or ""
                )
        return outcome

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
        clean_id = reject_control_chars(ticket_id, "ticket_id", instance=instance)
        target = self._tickets.get(clean_id) or next(
            (t for t in self._tickets.values() if t.ticket_key == clean_id), None
        )
        if target is None or (
            workspace_id and target.workspace_id and workspace_id != target.workspace_id
        ):
            raise ResourceNotFoundError(instance=instance)
        self._enforce_mutation_allowed(user, target.workspace_id or workspace_id, instance=instance)
        if action == "PAUSE" and target.status in ("REPLAYED", "GRANTED"):
            raise ValidationDomainError(
                detail_override="Ticket already replayed.", instance=instance
            )
        is_grant = action == "GRANT" or grant_permission
        state_val: Literal["PAUSED", "REPLAYED", "GRANTED"] = (
            "PAUSED" if action == "PAUSE" else ("GRANTED" if is_grant else "REPLAYED")
        )
        updated = replace(target, step_state=state_val, status=state_val)
        self._tickets[updated.id] = updated
        return updated

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
        if not await self._pg_ready():
            return self.apply_ticket_action(
                user,
                ticket_id,
                action,
                workspace_id=workspace_id,
                grant_permission=grant_permission,
                instance=instance,
            )
        assert self._sql_repo is not None
        clean_id = reject_control_chars(ticket_id, "ticket_id", instance=instance)
        target = await self._sql_repo.get_ticket(clean_id)
        if target is None or (
            workspace_id and target.workspace_id and workspace_id != target.workspace_id
        ):
            raise ResourceNotFoundError(instance=instance)
        self._enforce_mutation_allowed(user, target.workspace_id or workspace_id, instance=instance)
        if action == "PAUSE" and target.status in ("REPLAYED", "GRANTED"):
            raise ValidationDomainError(
                detail_override="Ticket already replayed.", instance=instance
            )
        is_grant = action == "GRANT" or grant_permission
        state_val: Literal["PAUSED", "REPLAYED", "GRANTED"] = (
            "PAUSED" if action == "PAUSE" else ("GRANTED" if is_grant else "REPLAYED")
        )
        updated = await self._sql_repo.update_ticket_state(
            clean_id, step_state=state_val, status=state_val
        )
        assert updated is not None
        self._tickets[updated.id] = updated
        return updated


def build_default_permission_broker_service(
    evaluator: MatrixPermissionEvaluator | None = None,
    *,
    passthrough_credentials: tuple[PassthroughCredentialRecord, ...] = (),
    vault_cipher: PassthroughVaultCipher | None = None,
    engine: object | None = None,
) -> PermissionBrokerService:
    return PermissionBrokerService(
        policies=tuple(
            PermissionBrokerPolicy(**asdict(s)) for s in DEFAULT_PERMISSION_BROKER_POLICY_SEEDS
        ),
        tickets=tuple(
            PermissionBrokerTicket(**asdict(t)) for t in DEFAULT_PERMISSION_BROKER_TICKET_SEEDS
        ),
        evaluator=evaluator,
        passthrough_credentials=passthrough_credentials,
        vault_cipher=vault_cipher,
        engine=engine,
    )


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
