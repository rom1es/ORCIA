"""Versioned Platform Settings (`ETag`/`If-Match` `412`), Write-Only Secrets
& Outbox Replay (`Story 8.3`).

Implements:
- `platform_settings` optimistic concurrency (`If-Match` required -> `428`, stale -> `412`)
- `SecretInputSpec` (`keep | set | clear`) and `SecretStatusView` (`sha256:<8-hex salted by id>`)
- `DEC-SEC-01` canary secret protection: never stores or returns plaintext secrets in settings,
  `SettingsChanged` Outbox events, or logs
- Bounded idempotent Outbox replay (`max_events <= 500`, `dry_run: true` by default)
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, replace
from datetime import UTC, datetime
from typing import Any, Literal

from orcia_core.permissions.errors import (
    ObserverModeReadOnlyError,
    PreconditionRequiredError,
    ResourceNotFoundError,
    ScopeAccessDeniedError,
    SettingsVersionConflictError,
    ValidationDomainError,
)
from orcia_core.permissions.models import UserIdentity
from orcia_core.permissions.secret_hint import (
    DefaultMemorySecretProvider,
    OutboxReplayOutcome,
    SecretAction,
    SecretInputSpec,
    SecretStatusView,
    compute_etag,
    compute_secret_masked_hint,
    compute_value_sha256,
)
from orcia_kernel.events import DomainEvent, SettingsChanged
from orcia_kernel.ids import new_uuid7_str
from orcia_kernel.secret_ports import SecretProviderPort, SecretRef

SettingScopeLevel = Literal["GLOBAL", "BU", "TEAM", "WORKSPACE"]
SettingCategory = Literal["iam", "connectors", "ai-models", "packs", "workflows", "audit"]

REGISTERED_IDEMPOTENT_OUTBOX_CONSUMERS: frozenset[str] = frozenset(
    {
        "notifications",
        "audit_finops",
        "ontology_extractor",
        "trigger_dispatcher",
    }
)


def _now_iso() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


def compute_salted_secret_fingerprint(resource_id: str, plaintext: str) -> str:
    """Compute salted 8-hex SHA-256 fingerprint (`sha256:<8-hex>`, `AD-21`)."""
    material = f"orcia-secret-salt:{resource_id}:{plaintext}".encode()
    digest = hashlib.sha256(material).hexdigest()[:8]
    return f"sha256:{digest}"


@dataclass(frozen=True, slots=True)
class PlatformSettingRecord:
    """Versioned row in `platform_settings` (`Story 8.3`, `AD-21`)."""

    id: str
    scope_level: SettingScopeLevel
    scope_id: str
    category: SettingCategory
    key: str
    value_jsonb: dict[str, Any]
    secret_ref: SecretRef | None
    secret_status: SecretStatusView
    version: int
    etag: str
    updated_at: str
    updated_by: str


class PlatformSettingsService:
    """Service managing versioned `platform_settings`, write-only secrets & Outbox replay."""

    def __init__(
        self,
        *,
        secret_provider: SecretProviderPort | None = None,
        initial_settings: tuple[PlatformSettingRecord, ...] = (),
    ) -> None:
        self._secret_provider: SecretProviderPort = secret_provider or DefaultMemorySecretProvider()
        self._settings: dict[tuple[str, str, str, str], PlatformSettingRecord] = {
            (s.scope_level, s.scope_id, s.category, s.key): s for s in initial_settings
        }
        self._outbox_events: list[DomainEvent] = []

    @property
    def outbox_events(self) -> tuple[DomainEvent, ...]:
        return tuple(self._outbox_events)

    def record_external_outbox_event(self, event: DomainEvent) -> None:
        self._outbox_events.append(event)

    def list_settings(
        self,
        *,
        scope_level: SettingScopeLevel | None = None,
        scope_id: str | None = None,
        category: SettingCategory | None = None,
    ) -> list[PlatformSettingRecord]:
        items = list(self._settings.values())
        if scope_level is not None:
            items = [s for s in items if s.scope_level == scope_level]
        if scope_id is not None:
            items = [s for s in items if s.scope_id == scope_id]
        if category is not None:
            items = [s for s in items if s.category == category]
        return items

    def get_setting(
        self,
        *,
        scope_level: SettingScopeLevel,
        scope_id: str,
        category: SettingCategory,
        key: str,
        instance: str | None = None,
    ) -> PlatformSettingRecord:
        rec = self._settings.get((scope_level, scope_id, category, key))
        if rec is None:
            raise ResourceNotFoundError(instance=instance)
        return rec

    def upsert_initial_setting(
        self,
        *,
        scope_level: SettingScopeLevel,
        scope_id: str,
        category: SettingCategory,
        key: str,
        value_jsonb: dict[str, Any],
        secret_input: SecretInputSpec | None = None,
        actor_id: str = "system",
    ) -> PlatformSettingRecord:
        setting_id = new_uuid7_str()
        now = _now_iso()
        sec_ref: SecretRef | None = None
        sec_status = SecretStatusView(
            configured=False, fingerprint=None, updated_at=now, updated_by=actor_id
        )
        if secret_input is not None and secret_input.action == "set":
            assert secret_input.plaintext_value is not None
            sec_ref = SecretRef(
                uri=f"secret://{scope_level.lower()}/{scope_id}/{category}/{key}",
                workspace_id=scope_id if scope_level == "WORKSPACE" else None,
            )
            self._secret_provider.store_secret(
                sec_ref, secret_input.plaintext_value, actor_id=actor_id
            )
            fp = compute_salted_secret_fingerprint(setting_id, secret_input.plaintext_value)
            hint = compute_secret_masked_hint(secret_input.plaintext_value)
            sec_status = SecretStatusView(
                configured=True,
                fingerprint=fp,
                masked_hint=hint,
                updated_at=now,
                updated_by=actor_id,
            )

        val_sha = compute_value_sha256(value_jsonb, sec_status.fingerprint)
        etag = compute_etag(setting_id, 1, val_sha)
        rec = PlatformSettingRecord(
            id=setting_id,
            scope_level=scope_level,
            scope_id=scope_id,
            category=category,
            key=key,
            value_jsonb=dict(value_jsonb),
            secret_ref=sec_ref,
            secret_status=sec_status,
            version=1,
            etag=etag,
            updated_at=now,
            updated_by=actor_id,
        )
        self._settings[(scope_level, scope_id, category, key)] = rec
        return rec

    def patch_setting(
        self,
        user: UserIdentity,
        *,
        scope_level: SettingScopeLevel,
        scope_id: str,
        category: SettingCategory,
        key: str,
        value_jsonb: dict[str, Any],
        if_match: str | None,
        secret_input: SecretInputSpec | None = None,
        instance: str | None = None,
    ) -> PlatformSettingRecord:
        """Mutate a versioned setting enforcing `If-Match` (`428`/`412`) and write-only secrets."""
        if user.platform_role == "OBSERVER":
            raise ObserverModeReadOnlyError(instance=instance)
        if not if_match or not if_match.strip():
            raise PreconditionRequiredError(instance=instance)

        composite_key = (scope_level, scope_id, category, key)
        current = self._settings.get(composite_key)
        if current is None:
            raise ResourceNotFoundError(instance=instance)
        if if_match.strip() != current.etag:
            raise SettingsVersionConflictError(instance=instance)

        now = _now_iso()
        before_sha = compute_value_sha256(current.value_jsonb, current.secret_status.fingerprint)
        sec_ref = current.secret_ref
        sec_status = current.secret_status
        sec_action: SecretAction = secret_input.action if secret_input is not None else "keep"

        if secret_input is not None:
            if secret_input.action == "set":
                assert secret_input.plaintext_value is not None
                next_ver = f"v{current.version + 1}"
                sec_ref = SecretRef(
                    uri=f"secret://{scope_level.lower()}/{scope_id}/{category}/{key}",
                    workspace_id=scope_id if scope_level == "WORKSPACE" else None,
                    version=next_ver,
                )
                self._secret_provider.store_secret(
                    sec_ref, secret_input.plaintext_value, actor_id=user.id
                )
                fp = compute_salted_secret_fingerprint(current.id, secret_input.plaintext_value)
                hint = compute_secret_masked_hint(secret_input.plaintext_value)
                sec_status = SecretStatusView(
                    configured=True,
                    fingerprint=fp,
                    masked_hint=hint,
                    updated_at=now,
                    updated_by=user.id,
                )
            elif secret_input.action == "clear":
                sec_ref = None
                sec_status = SecretStatusView(
                    configured=False,
                    fingerprint=None,
                    masked_hint=None,
                    updated_at=now,
                    updated_by=user.id,
                )

        next_version = current.version + 1
        after_sha = compute_value_sha256(value_jsonb, sec_status.fingerprint)
        next_etag = compute_etag(current.id, next_version, after_sha)

        changed_keys = sorted(
            {
                k
                for k in (*current.value_jsonb.keys(), *value_jsonb.keys())
                if current.value_jsonb.get(k) != value_jsonb.get(k)
            }
        )
        if sec_action != "keep":
            changed_keys.append("secret_ref")

        updated = replace(
            current,
            value_jsonb=dict(value_jsonb),
            secret_ref=sec_ref,
            secret_status=sec_status,
            version=next_version,
            etag=next_etag,
            updated_at=now,
            updated_by=user.id,
        )
        self._settings[composite_key] = updated
        self._outbox_events.append(
            SettingsChanged.create(
                setting_id=updated.id,
                workspace_id=scope_id if scope_level == "WORKSPACE" else None,
                scope_level=scope_level,
                scope_id=scope_id,
                category=category,
                key=key,
                version=next_version,
                before_sha256=before_sha,
                after_sha256=after_sha,
                changed_keys=tuple(changed_keys),
                updated_by=user.id,
                secret_action=sec_action,
            )
        )
        return updated

    def replay_outbox_events(
        self,
        user: UserIdentity,
        *,
        consumer_name: str,
        event_ids: tuple[str, ...] = (),
        max_events: int = 500,
        dry_run: bool = True,
        instance: str | None = None,
    ) -> OutboxReplayOutcome:
        """Bounded Outbox replay (`<= 500` events, idempotent consumer, `dry_run: true` default)."""
        if user.platform_role == "OBSERVER":
            raise ObserverModeReadOnlyError(instance=instance)
        if user.platform_role not in ("PLATFORM_ADMIN", "BU_DIRECTOR", "TEAM_LEAD"):
            raise ScopeAccessDeniedError(instance=instance)
        clean_consumer = consumer_name.strip()
        if clean_consumer not in REGISTERED_IDEMPOTENT_OUTBOX_CONSUMERS:
            raise ValidationDomainError(
                detail_override=(
                    f"Consumer '{clean_consumer}' is not registered as an idempotent Outbox "
                    f"consumer ({sorted(REGISTERED_IDEMPOTENT_OUTBOX_CONSUMERS)})."
                ),
                instance=instance,
            )
        if max_events <= 0 or max_events > 500:
            raise ValidationDomainError(
                detail_override="max_events for Outbox replay must be between 1 and 500.",
                instance=instance,
            )

        candidates = list(self._outbox_events)
        if event_ids:
            wanted = set(event_ids)
            candidates = [e for e in candidates if e.event_id in wanted]
        bounded = candidates[:max_events]
        matched_ids = tuple(e.event_id for e in bounded)
        replayed_count = 0 if dry_run else len(matched_ids)
        return OutboxReplayOutcome(
            consumer_name=clean_consumer,
            dry_run=dry_run,
            scanned_count=len(bounded),
            replayed_count=replayed_count,
            event_ids=matched_ids,
        )


__all__ = [
    "DefaultMemorySecretProvider",
    "OutboxReplayOutcome",
    "PlatformSettingRecord",
    "PlatformSettingsService",
    "REGISTERED_IDEMPOTENT_OUTBOX_CONSUMERS",
    "SecretAction",
    "SecretInputSpec",
    "SecretStatusView",
    "SettingCategory",
    "SettingScopeLevel",
    "compute_salted_secret_fingerprint",
    "compute_secret_masked_hint",
]
