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
