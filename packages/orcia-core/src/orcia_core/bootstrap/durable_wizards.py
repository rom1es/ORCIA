"""Durable DBOS Onboarding Wizards (`wizard_sessions`) & Demo Workspace (`Story 8.6`, `22.5`).

Implements (`FR-28`, `AD-2`, `AD-16`, `AD-19`, `AD-21`, `REM-15`):
- 3 profile-guided durable DBOS wizards (`sdlc_tech_lead`, `ops_manager`, `secops_admin`)
- Exact step resumption (`current_step_index` 1..5) and non-destructive `step_back`
- Strict `SecretRef` storage via `SecretProviderPort` (`0` plaintext secrets in `wizard_sessions`)
- Optional hexagonal `WizardSessionRepositoryPort` (PG18 persistence without SQLAlchemy imports)
- 1-click Zero Empty-State Demo Workspace provisioning (`0` plaintext secrets)
"""

from __future__ import annotations

from typing import Any

from orcia_core.bootstrap._durable_wizard_helpers import sanitize_and_store_wizard_step
from orcia_core.bootstrap._durable_wizard_models import (
    WIZARD_STEPS_BY_TYPE,
    DemoWorkspaceProvisionResult,
    WizardSessionRecord,
    WizardSessionRepositoryPort,
    WizardSessionStatus,
    WizardStepDescriptor,
    WizardType,
)
from orcia_core.bootstrap._durable_wizards_mixin import DurableWizardAbortAndDemoMixin
from orcia_core.permissions.errors import ObserverModeReadOnlyError, ResourceNotFoundError
from orcia_core.permissions.models import UserIdentity
from orcia_core.permissions.platform_settings import (
    DefaultMemorySecretProvider,
    SecretInputSpec,
)
from orcia_kernel.ids import new_uuid7_str
from orcia_kernel.secret_ports import SecretProviderPort


class DurableOnboardingWizardService(DurableWizardAbortAndDemoMixin):
    """Service managing durable 5-step DBOS onboarding wizards and Zero Empty-State Demo."""

    def __init__(
        self,
        *,
        secret_provider: SecretProviderPort | None = None,
        repository: WizardSessionRepositoryPort | None = None,
    ) -> None:
        self._secret_provider: SecretProviderPort = secret_provider or DefaultMemorySecretProvider()
        self._repository: WizardSessionRepositoryPort | None = repository
        self._sessions_by_id: dict[str, WizardSessionRecord] = {}
        self._session_id_by_workflow_key: dict[str, str] = {}

    def set_repository(self, repository: WizardSessionRepositoryPort | None) -> None:
        """Attach or replace the PostgreSQL 18 `WizardSessionRepositoryPort`."""
        self._repository = repository

    def get_steps_for_wizard(self, wizard_type: WizardType) -> tuple[WizardStepDescriptor, ...]:
        if wizard_type not in WIZARD_STEPS_BY_TYPE:
            from orcia_core.permissions.errors import ValidationDomainError

            raise ValidationDomainError(detail_override=f"Unknown wizard_type: {wizard_type!r}")
        return WIZARD_STEPS_BY_TYPE[wizard_type]

    def _sanitize_and_store_step(
        self,
        user: UserIdentity,
        session: WizardSessionRecord,
        *,
        step_index: int,
        step_payload: dict[str, Any],
        secret_input: SecretInputSpec | None,
        step_back: bool,
        instance: str | None,
    ) -> WizardSessionRecord:
        return sanitize_and_store_wizard_step(
            self._secret_provider,
            user,
            session,
            step_index=step_index,
            step_payload=step_payload,
            secret_input=secret_input,
            step_back=step_back,
            instance=instance,
        )

    def start_or_resume_wizard(
        self,
        user: UserIdentity,
        *,
        wizard_type: WizardType,
        scope_id: str,
        instance: str | None = None,
    ) -> WizardSessionRecord:
        """Start a new wizard or resume an existing `IN_PROGRESS` session at exact step $k/5$."""
        if user.platform_role == "OBSERVER":
            raise ObserverModeReadOnlyError(instance=instance)
        steps = self.get_steps_for_wizard(wizard_type)
        workflow_id = f"dbos:wizard:{wizard_type}:{user.id}:{scope_id}"
        existing_id = self._session_id_by_workflow_key.get(workflow_id)
        if existing_id is not None:
            existing = self._sessions_by_id[existing_id]
            if existing.status == "IN_PROGRESS":
                return existing

        session_id = new_uuid7_str()
        record = WizardSessionRecord(
            id=session_id,
            wizard_type=wizard_type,
            user_id=user.id,
            scope_id=scope_id,
            current_step_index=1,
            total_steps=len(steps),
            state_jsonb={},
            dbos_workflow_id=workflow_id,
            status="IN_PROGRESS",
        )
        self._sessions_by_id[session_id] = record
        self._session_id_by_workflow_key[workflow_id] = session_id
        return record

    async def start_or_resume_wizard_async(
        self,
        user: UserIdentity,
        *,
        wizard_type: WizardType,
        scope_id: str,
        instance: str | None = None,
    ) -> WizardSessionRecord:
        """Async start/resume backed by PG18 when repository is attached."""
        if user.platform_role == "OBSERVER":
            raise ObserverModeReadOnlyError(instance=instance)
        steps = self.get_steps_for_wizard(wizard_type)
        if self._repository is None:
            return self.start_or_resume_wizard(
                user, wizard_type=wizard_type, scope_id=scope_id, instance=instance
            )
        rec = await self._repository.start_or_resume_wizard_async(
            user_id=user.id,
            wizard_type=wizard_type,
            scope_id=scope_id,
            total_steps=len(steps),
        )
        self._sessions_by_id[rec.id] = rec
        return rec

    def get_session(self, session_id: str, *, instance: str | None = None) -> WizardSessionRecord:
        rec = self._sessions_by_id.get(session_id)
        if rec is None:
            raise ResourceNotFoundError(instance=instance)
        return rec

    async def get_session_async(
        self, session_id: str, *, instance: str | None = None
    ) -> WizardSessionRecord:
        """Async session lookup backed by PG18 when repository is attached."""
        if self._repository is None:
            return self.get_session(session_id, instance=instance)
        rec = await self._repository.get_session_async(session_id)
        if rec is None:
            raise ResourceNotFoundError(instance=instance)
        self._sessions_by_id[rec.id] = rec
        return rec

    async def list_sessions_for_user_async(self, user: UserIdentity) -> list[WizardSessionRecord]:
        """List wizard sessions owned by `user` ordered by `updated_at DESC`."""
        if self._repository is None:
            items = [s for s in self._sessions_by_id.values() if s.user_id == user.id]
            return sorted(items, key=lambda s: s.updated_at_iso, reverse=True)
        items = await self._repository.list_sessions_for_user_async(user.id)
        for item in items:
            self._sessions_by_id[item.id] = item
        return items

    def save_step_and_advance(
        self,
        user: UserIdentity,
        session_id: str,
        *,
        step_index: int,
        step_payload: dict[str, Any],
        secret_input: SecretInputSpec | None = None,
        step_back: bool = False,
        instance: str | None = None,
    ) -> WizardSessionRecord:
        """Persist step state (`SecretRef` only), run fail-fast check, and advance or step back."""
        if user.platform_role == "OBSERVER":
            raise ObserverModeReadOnlyError(instance=instance)
        session = self.get_session(session_id, instance=instance)
        updated = self._sanitize_and_store_step(
            user,
            session,
            step_index=step_index,
            step_payload=step_payload,
            secret_input=secret_input,
            step_back=step_back,
            instance=instance,
        )
        self._sessions_by_id[session_id] = updated
        return updated

    async def save_step_and_advance_async(
        self,
        user: UserIdentity,
        session_id: str,
        *,
        step_index: int,
        step_payload: dict[str, Any],
        secret_input: SecretInputSpec | None = None,
        step_back: bool = False,
        instance: str | None = None,
    ) -> WizardSessionRecord:
        """Async step save/advance/step_back persisted into PG18 `wizard_sessions`."""
        if user.platform_role == "OBSERVER":
            raise ObserverModeReadOnlyError(instance=instance)
        if self._repository is None:
            return self.save_step_and_advance(
                user,
                session_id,
                step_index=step_index,
                step_payload=step_payload,
                secret_input=secret_input,
                step_back=step_back,
                instance=instance,
            )
        session = await self.get_session_async(session_id, instance=instance)
        updated = self._sanitize_and_store_step(
            user,
            session,
            step_index=step_index,
            step_payload=step_payload,
            secret_input=secret_input,
            step_back=step_back,
            instance=instance,
        )
        persisted = await self._repository.save_step_and_advance_async(
            session_id=session_id,
            current_step_index=updated.current_step_index,
            state_jsonb=updated.state_jsonb,
            status=updated.status,
            completed_steps=updated.completed_steps,
            rag_reciprocity_verified=updated.rag_reciprocity_verified,
        )
        if persisted is None:
            raise ResourceNotFoundError(instance=instance)
        self._sessions_by_id[session_id] = persisted
        return persisted


__all__ = [
    "DemoWorkspaceProvisionResult",
    "DurableOnboardingWizardService",
    "WIZARD_STEPS_BY_TYPE",
    "WizardSessionRecord",
    "WizardSessionRepositoryPort",
    "WizardSessionStatus",
    "WizardStepDescriptor",
    "WizardType",
]
