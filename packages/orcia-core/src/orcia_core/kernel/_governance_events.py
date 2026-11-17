"""Governance domain events for the Transactional Outbox (`Story 8.1`, `Story 8.3`, `AD-21`).

Pure kernel module — zero framework or business domain dependencies.
"""

from __future__ import annotations

from dataclasses import dataclass

from orcia_core.kernel._events_base import DomainEvent
from orcia_core.kernel.ids import new_uuid7_str


@dataclass(frozen=True, slots=True)
class PermissionGranted(DomainEvent):
    """Published when a 6-verb permission grant is created or delegated (`Story 8.1`, `AD-21`)."""

    subject_type: str = "USER"
    subject_id: str = ""
    scope_path: str = ""
    verb: str = "read"

    @classmethod
    def create(
        cls,
        *,
        grant_id: str,
        workspace_id: str | None,
        subject_type: str,
        subject_id: str,
        scope_path: str,
        verb: str,
        granted_by_user_id: str,
        effect: str = "ALLOW",
        trace_id: str = "00000000000000000000000000000000",
    ) -> PermissionGranted:
        return cls(
            event_id=new_uuid7_str(),
            event_type="PermissionGranted",
            aggregate_type="role_permission_grant",
            aggregate_id=grant_id,
            run_id=None,
            workspace_id=workspace_id,
            payload={
                "subject_type": subject_type,
                "subject_id": subject_id,
                "scope_path": scope_path,
                "verb": verb,
                "effect": effect,
                "granted_by_user_id": granted_by_user_id,
            },
            trace_id=trace_id,
            subject_type=subject_type,
            subject_id=subject_id,
            scope_path=scope_path,
            verb=verb,
        )


@dataclass(frozen=True, slots=True)
class PermissionRevoked(DomainEvent):
    """Published when a 6-verb permission grant is revoked (`Story 8.1`, `AD-21`)."""

    subject_type: str = "USER"
    subject_id: str = ""
    scope_path: str = ""
    verb: str = "read"

    @classmethod
    def create(
        cls,
        *,
        grant_id: str,
        workspace_id: str | None,
        subject_type: str,
        subject_id: str,
        scope_path: str,
        verb: str,
        revoked_by_user_id: str,
        trace_id: str = "00000000000000000000000000000000",
    ) -> PermissionRevoked:
        return cls(
            event_id=new_uuid7_str(),
            event_type="PermissionRevoked",
            aggregate_type="role_permission_grant",
            aggregate_id=grant_id,
            run_id=None,
            workspace_id=workspace_id,
            payload={
                "subject_type": subject_type,
                "subject_id": subject_id,
                "scope_path": scope_path,
                "verb": verb,
                "revoked_by_user_id": revoked_by_user_id,
            },
            trace_id=trace_id,
            subject_type=subject_type,
            subject_id=subject_id,
            scope_path=scope_path,
            verb=verb,
        )


@dataclass(frozen=True, slots=True)
class AccessRequested(DomainEvent):
    """Published when a user requests access from a passive-discovery lock (`Story 8.1`)."""

    requester_user_id: str = ""
    scope_path: str = ""
    requested_verb: str = "read"

    @classmethod
    def create(
        cls,
        *,
        request_id: str,
        workspace_id: str | None,
        requester_user_id: str,
        scope_path: str,
        requested_verb: str,
        justification: str = "",
        trace_id: str = "00000000000000000000000000000000",
    ) -> AccessRequested:
        return cls(
            event_id=new_uuid7_str(),
            event_type="AccessRequested",
            aggregate_type="access_request",
            aggregate_id=request_id,
            run_id=None,
            workspace_id=workspace_id,
            payload={
                "requester_user_id": requester_user_id,
                "scope_path": scope_path,
                "requested_verb": requested_verb,
                "justification": justification,
            },
            trace_id=trace_id,
            requester_user_id=requester_user_id,
            scope_path=scope_path,
            requested_verb=requested_verb,
        )


@dataclass(frozen=True, slots=True)
class SettingsChanged(DomainEvent):
    """Published when a versioned platform setting is created/updated (`Story 8.3`, `AD-21`).

    Carries before/after SHA-256 hashes and changed keys, NEVER any secret value (`DEC-SEC-01`).
    """

    scope_level: str = "WORKSPACE"
    category: str = "iam"
    key: str = ""
    version: int = 1

    @classmethod
    def create(
        cls,
        *,
        setting_id: str,
        workspace_id: str | None,
        scope_level: str,
        scope_id: str,
        category: str,
        key: str,
        version: int,
        before_sha256: str,
        after_sha256: str,
        changed_keys: tuple[str, ...],
        updated_by: str,
        secret_action: str = "keep",
        trace_id: str = "00000000000000000000000000000000",
    ) -> SettingsChanged:
        return cls(
            event_id=new_uuid7_str(),
            event_type="SettingsChanged",
            aggregate_type="platform_setting",
            aggregate_id=setting_id,
            run_id=None,
            workspace_id=workspace_id,
            payload={
                "scope_level": scope_level,
                "scope_id": scope_id,
                "category": category,
                "key": key,
                "version": version,
                "before_sha256": before_sha256,
                "after_sha256": after_sha256,
                "changed_keys": list(changed_keys),
                "updated_by": updated_by,
                "secret_action": secret_action,
            },
            trace_id=trace_id,
            scope_level=scope_level,
            category=category,
            key=key,
            version=version,
        )


@dataclass(frozen=True, slots=True)
class AutonomousContractSigned(DomainEvent):
    """Published when an autonomy contract is signed on a workflow (`Story 7.1`, `AD-18`)."""

    workflow_id: str = ""
    service_principal_id: str = ""
    signed_by_user_id: str = ""

    @classmethod
    def create(
        cls,
        *,
        contract_id: str,
        workspace_id: str,
        workflow_id: str,
        workflow_version: str,
        service_principal_id: str,
        signed_by_user_id: str,
        signed_by_role: str,
        signature_sha256: str,
        scope_path: str = "GLOBAL",
        trace_id: str = "00000000000000000000000000000000",
    ) -> AutonomousContractSigned:
        return cls(
            event_id=new_uuid7_str(),
            event_type="AutonomousContractSigned",
            aggregate_type="autonomy_contract",
            aggregate_id=contract_id,
            run_id=None,
            workspace_id=workspace_id,
            payload={
                "contract_id": contract_id,
                "workflow_id": workflow_id,
                "workflow_version": workflow_version,
                "service_principal_id": service_principal_id,
                "signed_by_user_id": signed_by_user_id,
                "signed_by_role": signed_by_role,
                "signature_sha256": signature_sha256,
                "scope_path": scope_path,
                "actor_id": signed_by_user_id,
                "actor_type": "USER",
            },
            trace_id=trace_id,
            workflow_id=workflow_id,
            service_principal_id=service_principal_id,
            signed_by_user_id=signed_by_user_id,
        )


@dataclass(frozen=True, slots=True)
class AutonomousContractRevoked(DomainEvent):
    """Published when an autonomy contract is revoked (`Story 7.1`, `AD-18`)."""

    workflow_id: str = ""
    revoked_by_user_id: str = ""

    @classmethod
    def create(
        cls,
        *,
        contract_id: str,
        workspace_id: str,
        workflow_id: str,
        revoked_by_user_id: str,
        scope_path: str = "GLOBAL",
        trace_id: str = "00000000000000000000000000000000",
    ) -> AutonomousContractRevoked:
        return cls(
            event_id=new_uuid7_str(),
            event_type="AutonomousContractRevoked",
            aggregate_type="autonomy_contract",
            aggregate_id=contract_id,
            run_id=None,
            workspace_id=workspace_id,
            payload={
                "contract_id": contract_id,
                "workflow_id": workflow_id,
                "revoked_by_user_id": revoked_by_user_id,
                "scope_path": scope_path,
                "actor_id": revoked_by_user_id,
                "actor_type": "USER",
            },
            trace_id=trace_id,
            workflow_id=workflow_id,
            revoked_by_user_id=revoked_by_user_id,
        )


@dataclass(frozen=True, slots=True)
class AutonomousEscalated(DomainEvent):
    """Published when an autonomous run suspends to human escalation (`Story 7.1`, `AD-18`)."""

    workflow_id: str = ""
    reason: str = ""

    @classmethod
    def create(
        cls,
        *,
        run_id: str,
        workspace_id: str,
        workflow_id: str,
        reason: str,
        contract_id: str | None = None,
        service_principal_id: str | None = None,
        scope_path: str = "GLOBAL",
        trace_id: str = "00000000000000000000000000000000",
    ) -> AutonomousEscalated:
        return cls(
            event_id=new_uuid7_str(),
            event_type="AutonomousEscalated",
            aggregate_type="workflow_run",
            aggregate_id=run_id,
            run_id=run_id,
            workspace_id=workspace_id,
            payload={
                "run_id": run_id,
                "workflow_id": workflow_id,
                "reason": reason,
                "contract_id": contract_id,
                "service_principal_id": service_principal_id,
                "scope_path": scope_path,
                "actor_id": f"sp:{service_principal_id}" if service_principal_id else "system",
                "actor_type": "SERVICE_PRINCIPAL" if service_principal_id else "SYSTEM",
            },
            trace_id=trace_id,
            workflow_id=workflow_id,
            reason=reason,
        )


@dataclass(frozen=True, slots=True)
class TriggerFired(DomainEvent):
    """Published when an autonomous workflow trigger launches a run (`Story 7.2`, `AD-18`)."""

    trigger_id: str = ""
    trigger_type: str = "WEBHOOK"
    workflow_id: str = ""

    @classmethod
    def create(
        cls,
        *,
        trigger_id: str,
        workspace_id: str,
        workflow_id: str,
        trigger_type: str,
        run_id: str,
        idempotency_key: str,
        service_principal_id: str | None = None,
        scope_path: str = "GLOBAL",
        trace_id: str = "00000000000000000000000000000000",
    ) -> TriggerFired:
        return cls(
            event_id=new_uuid7_str(),
            event_type="TriggerFired",
            aggregate_type="workflow_trigger",
            aggregate_id=trigger_id,
            run_id=run_id,
            workspace_id=workspace_id,
            payload={
                "trigger_id": trigger_id,
                "trigger_type": trigger_type,
                "workflow_id": workflow_id,
                "run_id": run_id,
                "idempotency_key": idempotency_key,
                "service_principal_id": service_principal_id,
                "scope_path": scope_path,
                "actor_id": f"sp:{service_principal_id}" if service_principal_id else "system",
                "actor_type": "SERVICE_PRINCIPAL" if service_principal_id else "SYSTEM",
            },
            trace_id=trace_id,
            trigger_id=trigger_id,
            trigger_type=trigger_type,
            workflow_id=workflow_id,
        )


@dataclass(frozen=True, slots=True)
class SelfTriggerBlocked(DomainEvent):
    """Published when Self-Trigger Guard blocks a recursive trigger event (`Story 7.2`)."""

    trigger_id: str = ""
    reason: str = ""

    @classmethod
    def create(
        cls,
        *,
        trigger_id: str,
        workspace_id: str,
        workflow_id: str,
        reason: str,
        origin_run_id: str | None = None,
        service_principal_id: str | None = None,
        scope_path: str = "GLOBAL",
        trace_id: str = "00000000000000000000000000000000",
    ) -> SelfTriggerBlocked:
        return cls(
            event_id=new_uuid7_str(),
            event_type="SelfTriggerBlocked",
            aggregate_type="workflow_trigger",
            aggregate_id=trigger_id,
            run_id=None,
            workspace_id=workspace_id,
            payload={
                "trigger_id": trigger_id,
                "workflow_id": workflow_id,
                "reason": reason,
                "origin_run_id": origin_run_id,
                "service_principal_id": service_principal_id,
                "scope_path": scope_path,
                "actor_id": f"sp:{service_principal_id}" if service_principal_id else "system",
                "actor_type": "SYSTEM",
            },
            trace_id=trace_id,
            trigger_id=trigger_id,
            reason=reason,
        )


@dataclass(frozen=True, slots=True)
class TriggerCircuitOpened(DomainEvent):
    """Published when a workflow trigger circuit opens (`CIRCUIT_OPEN`, `Story 7.2`)."""

    trigger_id: str = ""
    reason: str = ""

    @classmethod
    def create(
        cls,
        *,
        trigger_id: str,
        workspace_id: str,
        workflow_id: str,
        reason: str,
        consecutive_failures: int = 0,
        scope_path: str = "GLOBAL",
        trace_id: str = "00000000000000000000000000000000",
    ) -> TriggerCircuitOpened:
        return cls(
            event_id=new_uuid7_str(),
            event_type="TriggerCircuitOpened",
            aggregate_type="workflow_trigger",
            aggregate_id=trigger_id,
            run_id=None,
            workspace_id=workspace_id,
            payload={
                "trigger_id": trigger_id,
                "workflow_id": workflow_id,
                "reason": reason,
                "consecutive_failures": consecutive_failures,
                "scope_path": scope_path,
                "actor_id": "system",
                "actor_type": "SYSTEM",
            },
            trace_id=trace_id,
            trigger_id=trigger_id,
            reason=reason,
        )


@dataclass(frozen=True, slots=True)
class WorkflowPublished(DomainEvent):
    """Published when a Studio V2 workflow or pack is published (`Story 7.2`, opt-in help)."""

    workflow_id: str = ""
    version: str = "1.0.0"

    @classmethod
    def create(
        cls,
        *,
        workflow_id: str,
        workspace_id: str,
        version: str,
        pack_slug: str = "orcia-docs",
        title: str = "",
        actor_id: str = "system",
        scope_path: str = "GLOBAL",
        trace_id: str = "00000000000000000000000000000000",
    ) -> WorkflowPublished:
        return cls(
            event_id=new_uuid7_str(),
            event_type="WorkflowPublished",
            aggregate_type="workflow_definition",
            aggregate_id=workflow_id,
            run_id=None,
            workspace_id=workspace_id,
            payload={
                "workflow_id": workflow_id,
                "version": version,
                "pack_slug": pack_slug,
                "title": title,
                "scope_path": scope_path,
                "actor_id": actor_id,
                "actor_type": "USER",
            },
            trace_id=trace_id,
            workflow_id=workflow_id,
            version=version,
        )
