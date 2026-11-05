"""Unit tests for DurableOnboardingWizardService.discard_unsaved_draft_or_abort."""

from __future__ import annotations

from dataclasses import replace

import pytest

from orcia_core.bootstrap.durable_wizards import DurableOnboardingWizardService
from orcia_core.permissions.errors import ObserverModeReadOnlyError
from orcia_core.permissions.models import UserIdentity


def _make_admin() -> UserIdentity:
    return UserIdentity(
        id="0195f000-0000-7000-8000-000000000001",
        email="admin@orcia.io",
        display_name="Admin",
        auth_mode="LOCAL",
        human_profile_archetype="TECH_LEAD_DEV",
        platform_role="PLATFORM_ADMIN",
        primary_org_unit_id="0195f000-0000-7000-8000-000000000010",
    )


def _make_observer() -> UserIdentity:
    return UserIdentity(
        id="0195f000-0000-7000-8000-000000000002",
        email="observer@orcia.io",
        display_name="Observer",
        auth_mode="LOCAL",
        human_profile_archetype="TECH_LEAD_DEV",
        platform_role="OBSERVER",
        primary_org_unit_id="0195f000-0000-7000-8000-000000000010",
    )


def test_discard_unsaved_draft_or_abort_cleans_draft_keys_and_supports_abort() -> None:
    svc = DurableOnboardingWizardService()
    admin = _make_admin()
    session = svc.start_or_resume_wizard(
        admin,
        wizard_type="sdlc_tech_lead",
        scope_id="0195f000-0000-7000-8000-000000000100",
    )

    svc.save_step_and_advance(
        admin,
        session.id,
        step_index=1,
        step_payload={"org_name": "ORCIA Corp"},
    )
    current = svc.get_session(session.id)
    svc._sessions_by_id[session.id] = replace(
        current,
        state_jsonb={
            **current.state_jsonb,
            "draft_step_2": {"unsaved_field": "temp"},
        },
    )

    cleaned = svc.discard_unsaved_draft_or_abort(
        admin,
        session.id,
        discard_draft_only=True,
    )
    assert "draft_step_2" not in cleaned.state_jsonb
    assert "step_1" in cleaned.state_jsonb
    assert cleaned.status == "IN_PROGRESS"

    aborted = svc.discard_unsaved_draft_or_abort(
        admin,
        session.id,
        discard_draft_only=False,
    )
    assert aborted.status == "ABANDONED"


def test_discard_unsaved_draft_or_abort_rejects_observer() -> None:
    svc = DurableOnboardingWizardService()
    admin = _make_admin()
    observer = _make_observer()
    session = svc.start_or_resume_wizard(
        admin,
        wizard_type="sdlc_tech_lead",
        scope_id="0195f000-0000-7000-8000-000000000100",
    )

    with pytest.raises(ObserverModeReadOnlyError):
        svc.discard_unsaved_draft_or_abort(observer, session.id)
