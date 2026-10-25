"""PermissionBrokerService: Passthrough vs Service Principal Guard, KB Matcher & Jira Broker.

Pure hexagonal domain module (Story 1.4, AD-6, FR-22, UX-DR11) — zero framework imports.
"""

from __future__ import annotations

import fnmatch
from dataclasses import asdict, replace
from typing import Literal
from urllib.parse import quote

from orcia_core.bootstrap.permission_broker_seeds import (
    DEFAULT_PERMISSION_BROKER_POLICY_SEEDS,
    DEFAULT_PERMISSION_BROKER_TICKET_SEEDS,
)
from orcia_core.domain.exceptions import (
    ConfusedDeputyBlockedError,
    ObserverModeReadOnlyError,
    PermissionBrokerDeniedError,
    ResourceNotFoundError,
    ScopeAccessDeniedError,
    ValidationDomainError,
)
from orcia_core.domain.identifiers import new_uuid7_str
from orcia_core.permissions.broker_models import (
    ALLOWED_BROKER_SCHEMES,
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
    parse_permission_kb_markdown,
    reject_control_chars,
)
from orcia_core.permissions.crypto import PassthroughVaultCipher
from orcia_core.permissions.evaluator import MatrixPermissionEvaluator
from orcia_core.permissions.models import (
    ExecutionIdentityMode,
    PassthroughCredentialRecord,
    UserIdentity,
)


class PermissionBrokerService:
    """Domain service enforcing `passthrough` default and brokering `401/403` denials via Jira."""

    def __init__(
        self, *, policies: tuple[PermissionBrokerPolicy, ...],
        tickets: tuple[PermissionBrokerTicket, ...] = (),
        evaluator: MatrixPermissionEvaluator | None = None,
        passthrough_credentials: tuple[PassthroughCredentialRecord, ...] = (),
        vault_cipher: PassthroughVaultCipher | None = None,
    ) -> None:  # fmt: skip
        self._policies: dict[str, PermissionBrokerPolicy] = {p.policy_key: p for p in policies}
        self._tickets: dict[str, PermissionBrokerTicket] = {t.id: t for t in tickets}
        self._evaluator, self._vault_cipher = evaluator, vault_cipher
        self._passthrough_credentials: dict[tuple[str, str, str], PassthroughCredentialRecord] = {
            (c.user_id, c.connector_scheme.lower(), c.target_host.lower()): c
            for c in passthrough_credentials
        }

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

    def list_tickets(
        self, workspace_id: str | None = None, *, user: UserIdentity | None = None,
        instance: str | None = None,
    ) -> list[PermissionBrokerTicket]:  # fmt: skip
        ev = self._evaluator
        if workspace_id is not None:
            clean_ws = reject_control_chars(workspace_id, "workspace_id", instance=instance)
            if user and ev and ev.resolve_workspace_access(user, clean_ws) is None:
                raise ScopeAccessDeniedError(instance=instance)
            return [t for t in self._tickets.values() if t.workspace_id in (None, clean_ws)]
        if user is not None and ev is not None:
            return [
                t for t in self._tickets.values()
                if not t.workspace_id or ev.resolve_workspace_access(user, t.workspace_id)
            ]  # fmt: skip
        return list(self._tickets.values())

    def _enforce_mutation_allowed(
        self, user: UserIdentity, workspace_id: str | None, *, instance: str | None = None
    ) -> None:
        if user.platform_role in ("OBSERVER", "BU_DIRECTOR"):
            raise ObserverModeReadOnlyError(instance=instance)
        if workspace_id is not None and self._evaluator is not None:
            self._evaluator.enforce_scope_mutation_guard(user, workspace_id, instance=instance)

    def import_policy_markdown(
        self, user: UserIdentity, markdown_text: str, *, policy_key: str | None = None,
        workspace_id: str | None = None, instance: str | None = None,
    ) -> PermissionBrokerPolicy:  # fmt: skip
        self._enforce_mutation_allowed(user, workspace_id, instance=instance)
        policy = parse_permission_kb_markdown(
            markdown_text, policy_key=policy_key, instance=instance
        )
        if policy.service_principal_allowed and user.platform_role != "PLATFORM_ADMIN":
            raise ConfusedDeputyBlockedError(instance=instance)
        admin_id = user.id if policy.service_principal_allowed else None
        policy = replace(policy, approved_by_admin_id=admin_id)
        matches = [
            k for k, p in self._policies.items()
            if p.policy_key == policy.policy_key or p.uri_pattern == policy.uri_pattern
        ]  # fmt: skip
        existing = self._policies[matches[0]] if matches else None
        for k in matches:
            self._policies.pop(k, None)
        if existing is not None:
            policy = replace(policy, id=existing.id, policy_key=existing.policy_key)
        self._policies[policy.policy_key] = policy
        return policy

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
        self, user: UserIdentity, *, target_uri: str,
        execution_identity: ExecutionIdentityMode = "passthrough",
        step_key: str = "step-02-execution", step_number: int = 2,
        workspace_id: str | None = None, resource_id: str | None = None,
        simulated_upstream_status: Literal[200, 401, 403] | None = None,
        granted_external_roles: tuple[str, ...] = (), raise_on_denied: bool = True,
        instance: str | None = None,
    ) -> PermissionCheckOutcome:  # fmt: skip
        self._enforce_mutation_allowed(user, workspace_id, instance=instance)
        clean_step = reject_control_chars(step_key, "step_key", instance=instance)
        if step_number <= 0:
            msg = "step_number must be strictly positive."
            raise ValidationDomainError(detail_override=msg, instance=instance)
        policy = self.resolve_matching_policy(target_uri, instance=instance)
        cleaned_uri = target_uri.strip()
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
            return PermissionCheckOutcome(
                True, "GRANTED", execution_identity, cleaned_uri, policy.connector_scheme, policy
            )

        jira_url = build_prefilled_jira_request_url(
            policy.request_url_template, target_uri=cleaned_uri, required_role=policy.required_role,
            approver_team=policy.approver_team, requester_email=user.email, step_key=clean_step,
            execution_identity=execution_identity,
        )  # fmt: skip
        req_q, uri_q = quote(policy.required_role, safe=""), quote(cleaned_uri, safe="")
        app_q = quote(policy.approver_team, safe="")
        hint = f"jira://IAM/{req_q}?target={uri_q}&approver={app_q}&sla_hours={policy.sla_hours}"
        ticket_id = new_uuid7_str()
        ticket = PermissionBrokerTicket(
            ticket_id, f"tkt-{clean_step}-{ticket_id[-6:]}", workspace_id, user.id, policy.id,
            clean_step, step_number, "PERMISSION_DENIED_STEP", "WAITING_FOR_PERMISSION",
            cleaned_uri, policy.connector_scheme, execution_identity, denied_status,
            policy.required_role, policy.approver_team, policy.sla_hours, jira_url, hint,
            policy.procedure_markdown,
        )  # fmt: skip
        self._tickets[ticket.id] = ticket
        if raise_on_denied:
            raise PermissionBrokerDeniedError(instance=instance, permission_broker_hint=hint)
        return PermissionCheckOutcome(
            False, "WAITING_FOR_PERMISSION", execution_identity, cleaned_uri,
            policy.connector_scheme, policy, ticket, hint,
        )  # fmt: skip

    def apply_ticket_action(
        self, user: UserIdentity, ticket_id: str,
        action: BrokerTicketAction | Literal["GRANT"], *, workspace_id: str | None = None,
        grant_permission: bool = False, instance: str | None = None,
    ) -> PermissionBrokerTicket:  # fmt: skip
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


def build_default_permission_broker_service(
    evaluator: MatrixPermissionEvaluator | None = None, *,
    passthrough_credentials: tuple[PassthroughCredentialRecord, ...] = (),
    vault_cipher: PassthroughVaultCipher | None = None,
) -> PermissionBrokerService:  # fmt: skip
    return PermissionBrokerService(
        policies=tuple(
            PermissionBrokerPolicy(**asdict(s)) for s in DEFAULT_PERMISSION_BROKER_POLICY_SEEDS
        ),
        tickets=tuple(
            PermissionBrokerTicket(**asdict(t)) for t in DEFAULT_PERMISSION_BROKER_TICKET_SEEDS
        ),
        evaluator=evaluator, passthrough_credentials=passthrough_credentials,
        vault_cipher=vault_cipher,
    )  # fmt: skip


__all__ = [
    "ALLOWED_BROKER_SCHEMES", "BrokerConnectorScheme", "BrokerStepState", "BrokerTicketAction",
    "BrokerTicketStatus", "PermissionBrokerPolicy", "PermissionBrokerService",
    "PermissionBrokerTicket", "PermissionCheckOutcome", "build_default_permission_broker_service",
    "build_jira_request_url", "build_prefilled_jira_request_url", "extract_connector_host",
    "extract_connector_scheme", "parse_permission_kb_markdown",
]  # fmt: skip
