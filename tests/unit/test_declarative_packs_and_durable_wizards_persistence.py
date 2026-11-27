"""Unit tests for declarative pack router checks and durable onboarding wizards."""

from __future__ import annotations

import inspect
from typing import Any

import pytest

from orcia_core.bootstrap import (
    DurableOnboardingWizardService,
    WizardSessionRecord,
    WizardSessionStatus,
    WizardType,
)
from orcia_core.permissions.errors import ResourceNotFoundError, ValidationDomainError
from orcia_core.permissions.models import UserIdentity
from orcia_core.permissions.platform_settings import SecretInputSpec


class _StubWizardRepository:
    def __init__(self) -> None:
        self.sessions: dict[str, WizardSessionRecord] = {}
        self.calls: list[str] = []

    async def start_or_resume_wizard_async(
        self,
        *,
        user_id: str,
        wizard_type: WizardType,
        scope_id: str,
        total_steps: int,
    ) -> WizardSessionRecord:
        self.calls.append("start_or_resume")
        for existing in self.sessions.values():
            if (
                existing.user_id == user_id
                and existing.wizard_type == wizard_type
                and existing.scope_id == scope_id
                and existing.status == "IN_PROGRESS"
            ):
                return existing
        rec = WizardSessionRecord(
            id="0195f000-0000-7000-8000-000000009101",
            wizard_type=wizard_type,
            user_id=user_id,
            scope_id=scope_id,
            current_step_index=1,
            total_steps=total_steps,
            state_jsonb={},
            dbos_workflow_id=f"dbos:wizard:{wizard_type}:{user_id}:{scope_id}",
            status="IN_PROGRESS",
        )
        self.sessions[rec.id] = rec
        return rec

    async def get_session_async(self, session_id: str) -> WizardSessionRecord | None:
        self.calls.append("get_session")
        return self.sessions.get(session_id)

    async def list_sessions_for_user_async(self, user_id: str) -> list[WizardSessionRecord]:
        self.calls.append("list_sessions")
        return [s for s in self.sessions.values() if s.user_id == user_id]

    async def save_step_and_advance_async(
        self,
        *,
        session_id: str,
        current_step_index: int,
        state_jsonb: dict[str, Any],
        status: WizardSessionStatus,
        completed_steps: tuple[int, ...],
        rag_reciprocity_verified: bool,
    ) -> WizardSessionRecord | None:
        self.calls.append("save_step")
        existing = self.sessions.get(session_id)
        if existing is None:
            return None
        updated = WizardSessionRecord(
            id=existing.id,
            wizard_type=existing.wizard_type,
            user_id=existing.user_id,
            scope_id=existing.scope_id,
            current_step_index=current_step_index,
            total_steps=existing.total_steps,
            state_jsonb=dict(state_jsonb),
            dbos_workflow_id=existing.dbos_workflow_id,
            status=status,
            completed_steps=completed_steps,
            rag_reciprocity_verified=rag_reciprocity_verified,
        )
        self.sessions[session_id] = updated
        return updated

    async def update_session_state_async(
        self,
        *,
        session_id: str,
        state_jsonb: dict[str, Any],
        status: WizardSessionStatus,
    ) -> WizardSessionRecord | None:
        self.calls.append("update_state")
        existing = self.sessions.get(session_id)
        if existing is None:
            return None
        updated = WizardSessionRecord(
            id=existing.id,
            wizard_type=existing.wizard_type,
            user_id=existing.user_id,
            scope_id=existing.scope_id,
            current_step_index=existing.current_step_index,
            total_steps=existing.total_steps,
            state_jsonb=dict(state_jsonb),
            dbos_workflow_id=existing.dbos_workflow_id,
            status=status,
            completed_steps=existing.completed_steps,
            rag_reciprocity_verified=existing.rag_reciprocity_verified,
        )
        self.sessions[session_id] = updated
        return updated


def _sample_user() -> UserIdentity:
    return UserIdentity(
        id="0195f000-0000-7000-8000-000000000201",
        email="architect@orcia.test",
        display_name="Architecte Test",
        auth_mode="LOCAL",
        human_profile_archetype="TECH_LEAD",
        platform_role="PLATFORM_ADMIN",
        primary_org_unit_id="0195f000-0000-7000-8000-000000000101",
        roles=("PLATFORM_ADMIN",),
    )


@pytest.mark.asyncio
async def test_packs_router_and_lifespan_do_not_use_disable_sync_env_var(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Verify `ORCIA_DISABLE_PG_BOOTSTRAP_SYNC` is absent and runtime check delegates cleanly."""
    from orcia_api.dependencies import core_and_lifespan
    from orcia_api.routers import packs as packs_router

    assert "ORCIA_DISABLE_PG_BOOTSTRAP_SYNC" not in inspect.getsource(packs_router)
    assert "DeclarativePackLoader" not in inspect.getsource(packs_router)
    assert "ORCIA_DISABLE_PG_BOOTSTRAP_SYNC" not in inspect.getsource(core_and_lifespan)

    class _StubRepo:
        _engine: Any = None

        async def list_bundles_v2(self) -> list[dict[str, object]]:
            return [{"id": "b1", "slug": "sdlc"}]

    stub = _StubRepo()
    assert await packs_router._list_pg_bundles(stub) == []  # type: ignore[arg-type]
    stub._engine = object()
    assert await packs_router._list_pg_bundles(stub) == [{"id": "b1", "slug": "sdlc"}]  # type: ignore[arg-type]


@pytest.mark.asyncio
async def test_durable_wizard_service_preserves_inputs_on_step_back_and_completes() -> None:
    """Verify async start/resume, SecretRef storage, step_back input retention, and completion."""
    repo = _StubWizardRepository()
    service = DurableOnboardingWizardService(repository=repo)
    actor = _sample_user()
    scope_id = "0195f000-0000-7000-8000-000000000301"

    started = await service.start_or_resume_wizard_async(
        actor, wizard_type="sdlc_tech_lead", scope_id=scope_id
    )
    assert started.current_step_index == 1
    assert started.status == "IN_PROGRESS"

    resumed = await service.start_or_resume_wizard_async(
        actor, wizard_type="sdlc_tech_lead", scope_id=scope_id
    )
    assert resumed.id == started.id

    with pytest.raises(ValidationDomainError):
        await service.save_step_and_advance_async(
            actor,
            started.id,
            step_index=1,
            step_payload={"api_key": "raw-plaintext-forbidden"},  # pragma: allowlist secret
        )

    after_step1 = await service.save_step_and_advance_async(
        actor,
        started.id,
        step_index=1,
        step_payload={"org_unit_name": "Plateforme Architecture"},
        secret_input=SecretInputSpec(
            action="set",
            plaintext_value="token-value-123",  # pragma: allowlist secret
        ),
    )
    assert after_step1.current_step_index == 2
    assert after_step1.completed_steps == (1,)
    assert after_step1.state_jsonb["step_1"]["org_unit_name"] == "Plateforme Architecture"
    assert after_step1.state_jsonb["step_1"]["secret_ref_uri"].startswith("secret://wizards/")
    assert "token-value-123" not in repr(after_step1.state_jsonb)

    stepped_back = await service.save_step_and_advance_async(
        actor,
        started.id,
        step_index=2,
        step_payload={"workspace_name": "Espace Brouillon"},
        step_back=True,
    )
    assert stepped_back.current_step_index == 1
    assert stepped_back.status == "IN_PROGRESS"
    assert stepped_back.state_jsonb["step_1"]["org_unit_name"] == "Plateforme Architecture"
    assert stepped_back.state_jsonb["step_2"]["workspace_name"] == "Espace Brouillon"

    for idx, payload in [
        (1, {"org_unit_name": "Plateforme Architecture"}),
        (2, {"workspace_name": "Espace Principal"}),
        (3, {"connector_alias": "git-core", "connector_uri": "https://git.internal/core.git"}),
        (4, {"primary_model_id": "qwen2.5:14b"}),
        (5, {"verify_rag_reciprocity": True}),
    ]:
        latest = await service.save_step_and_advance_async(
            actor, started.id, step_index=idx, step_payload=payload
        )

    assert latest.status == "COMPLETED"
    assert latest.current_step_index == 5
    assert latest.completed_steps == (1, 2, 3, 4, 5)
    assert latest.rag_reciprocity_verified is True

    listed = await service.list_sessions_for_user_async(actor)
    assert len(listed) == 1
    assert listed[0].status == "COMPLETED"

    fetched = await service.get_session_async(started.id)
    assert fetched.id == started.id

    with pytest.raises(ResourceNotFoundError):
        await service.get_session_async("0195f000-0000-7000-8000-000000009999")

    aborted = await service.discard_unsaved_draft_or_abort_async(
        actor, started.id, discard_draft_only=False
    )
    assert aborted.status == "ABANDONED"
