"""Policy import, listing & default service factory for `PermissionBrokerService`."""

from __future__ import annotations

from dataclasses import asdict, replace
from typing import TYPE_CHECKING

from orcia_core.permissions.broker_models import (
    PermissionBrokerPolicy,
    PermissionBrokerTicket,
    extract_connector_host,
    parse_permission_kb_markdown,
    reject_control_chars,
)
from orcia_core.permissions.crypto import PassthroughVaultCipher
from orcia_core.permissions.errors import ConfusedDeputyBlockedError, ScopeAccessDeniedError
from orcia_core.permissions.evaluator import MatrixPermissionEvaluator
from orcia_core.permissions.models import PassthroughCredentialRecord, UserIdentity
from orcia_core.permissions.seeds import (
    DEFAULT_PERMISSION_BROKER_POLICY_SEEDS,
    DEFAULT_PERMISSION_BROKER_TICKET_SEEDS,
)

if TYPE_CHECKING:
    from orcia_core.permissions.broker import PermissionBrokerService


def filter_tickets_by_scope(
    service: PermissionBrokerService,
    tickets: list[PermissionBrokerTicket],
    workspace_id: str | None,
    user: UserIdentity | None,
    instance: str | None,
) -> list[PermissionBrokerTicket]:
    ev = service._evaluator
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


def prepare_and_import_policy_sync(
    service: PermissionBrokerService,
    user: UserIdentity,
    markdown_text: str,
    *,
    policy_key: str | None = None,
    workspace_id: str | None = None,
    instance: str | None = None,
) -> PermissionBrokerPolicy:
    policy = prepare_policy_upsert(
        service,
        user,
        markdown_text,
        policy_key=policy_key,
        workspace_id=workspace_id,
        instance=instance,
    )
    matches = [
        k
        for k, p in service._policies.items()
        if p.policy_key == policy.policy_key or p.uri_pattern == policy.uri_pattern
    ]
    existing = service._policies[matches[0]] if matches else None
    for k in matches:
        service._policies.pop(k, None)
    if existing is not None:
        policy = replace(policy, id=existing.id, policy_key=existing.policy_key)
    service._policies[policy.policy_key] = policy
    return policy


def prepare_policy_upsert(
    service: PermissionBrokerService,
    user: UserIdentity,
    markdown_text: str,
    *,
    policy_key: str | None = None,
    workspace_id: str | None = None,
    instance: str | None = None,
) -> PermissionBrokerPolicy:
    service._enforce_mutation_allowed(user, workspace_id, instance=instance)
    policy = parse_permission_kb_markdown(markdown_text, policy_key=policy_key, instance=instance)
    if policy.service_principal_allowed and user.platform_role != "PLATFORM_ADMIN":
        raise ConfusedDeputyBlockedError(instance=instance)
    admin_id = user.id if policy.service_principal_allowed else None
    return replace(policy, approved_by_admin_id=admin_id)


def build_default_permission_broker_service(
    evaluator: MatrixPermissionEvaluator | None = None,
    *,
    passthrough_credentials: tuple[PassthroughCredentialRecord, ...] = (),
    vault_cipher: PassthroughVaultCipher | None = None,
    engine: object | None = None,
) -> PermissionBrokerService:
    from orcia_core.permissions.broker import PermissionBrokerService

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


def check_passthrough_credential(
    service: PermissionBrokerService, user_id: str, scheme: str, target_uri: str
) -> bool:
    key = (user_id, scheme.lower(), extract_connector_host(target_uri))
    rec = service._passthrough_credentials.get(key)
    if rec is None:
        return False
    if service._vault_cipher is not None:
        return bool(
            service._vault_cipher.decrypt(
                rec.user_id,
                rec.ciphertext_b64,
                rec.nonce_b64,
                connector_scheme=rec.connector_scheme,
                target_host=rec.target_host,
                key_version=rec.key_version,
            )
        )
    return bool(rec.ciphertext_b64)


async def list_policies_pg(service: PermissionBrokerService) -> list[PermissionBrokerPolicy]:
    if not await service._pg_ready():
        return service.list_policies()
    assert service._sql_repo is not None
    policies = await service._sql_repo.ensure_policies_seeded(tuple(service._policies.values()))
    for p in policies:
        service._policies[p.policy_key] = p
    return policies


async def list_tickets_pg(
    service: PermissionBrokerService,
    workspace_id: str | None = None,
    *,
    user: UserIdentity | None = None,
    instance: str | None = None,
) -> list[PermissionBrokerTicket]:
    if not await service._pg_ready():
        return service.list_tickets(workspace_id, user=user, instance=instance)
    assert service._sql_repo is not None
    if workspace_id is not None:
        clean_ws = reject_control_chars(workspace_id, "workspace_id", instance=instance)
        if (
            user
            and service._evaluator
            and service._evaluator.resolve_workspace_access(user, clean_ws) is None
        ):
            raise ScopeAccessDeniedError(instance=instance)
        return await service._sql_repo.list_tickets(clean_ws)
    tickets = await service._sql_repo.list_tickets(None)
    return service._filter_tickets_by_scope(tickets, None, user, instance)


__all__ = [
    "build_default_permission_broker_service",
    "check_passthrough_credential",
    "filter_tickets_by_scope",
    "list_policies_pg",
    "list_tickets_pg",
    "prepare_and_import_policy_sync",
    "prepare_policy_upsert",
]
