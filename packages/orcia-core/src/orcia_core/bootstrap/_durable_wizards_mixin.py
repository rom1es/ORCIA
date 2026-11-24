"""Abort, draft cleanup & demo provisioning mixin for `DurableOnboardingWizardService`."""

from __future__ import annotations

from typing import TYPE_CHECKING, cast

from orcia_core.bootstrap._durable_wizard_helpers import (
    apply_discard_draft_or_abort,
    build_demo_workspace_result,
    persist_discard_draft_or_abort_async,
)
from orcia_core.bootstrap._durable_wizard_models import (
    DemoWorkspaceProvisionResult,
    WizardSessionRecord,
)
from orcia_core.permissions.errors import ObserverModeReadOnlyError
from orcia_core.permissions.models import UserIdentity
from orcia_kernel.enums import DEFAULT_LOCALE, SupportedLocale

if TYPE_CHECKING:
    from orcia_core.bootstrap.durable_wizards import DurableOnboardingWizardService


class DurableWizardAbortAndDemoMixin:
    """Draft discard, session abort & demo workspace provisioning methods."""

    def discard_unsaved_draft_or_abort(
        self,
        user: UserIdentity,
        session_id: str,
        *,
        discard_draft_only: bool = True,
        instance: str | None = None,
    ) -> WizardSessionRecord:
        """Discard unsaved draft keys or abort a wizard session on RGAA cancel/escape."""
        if user.platform_role == "OBSERVER":
            raise ObserverModeReadOnlyError(instance=instance)
        svc = cast("DurableOnboardingWizardService", self)
        updated = apply_discard_draft_or_abort(
            svc.get_session(session_id, instance=instance),
            discard_draft_only=discard_draft_only,
        )
        svc._sessions_by_id[session_id] = updated
        return updated

    async def discard_unsaved_draft_or_abort_async(
        self,
        user: UserIdentity,
        session_id: str,
        *,
        discard_draft_only: bool = True,
        instance: str | None = None,
    ) -> WizardSessionRecord:
        """Async draft cleanup / session abort persisted into PG18 `wizard_sessions`."""
        if user.platform_role == "OBSERVER":
            raise ObserverModeReadOnlyError(instance=instance)
        svc = cast("DurableOnboardingWizardService", self)
        if svc._repository is None:
            return self.discard_unsaved_draft_or_abort(
                user, session_id, discard_draft_only=discard_draft_only, instance=instance
            )
        current = await svc.get_session_async(session_id, instance=instance)
        persisted = await persist_discard_draft_or_abort_async(
            svc._repository,
            current,
            session_id=session_id,
            discard_draft_only=discard_draft_only,
            instance=instance,
        )
        svc._sessions_by_id[session_id] = persisted
        return persisted

    def provision_zero_empty_state_demo(
        self,
        user: UserIdentity,
        *,
        scope_id: str = "0195f000-0000-7000-8000-000000000399",
        locale: SupportedLocale = DEFAULT_LOCALE,
        instance: str | None = None,
    ) -> DemoWorkspaceProvisionResult:
        """Idempotently provision the Zero Empty-State Demo Workspace (`0` plaintext secrets)."""
        if user.platform_role == "OBSERVER":
            raise ObserverModeReadOnlyError(instance=instance)
        return build_demo_workspace_result(scope_id=scope_id, locale=locale)
