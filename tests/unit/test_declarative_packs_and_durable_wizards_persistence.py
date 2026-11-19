"""Unit tests for declarative pack bundle PG18 sync and durable onboarding wizards."""

from __future__ import annotations

import inspect
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from datetime import UTC, datetime
from typing import Any

import pytest

from orcia_core.bootstrap import (
    DurableOnboardingWizardService,
    SqlWizardSessionRepository,
    WizardSessionRecord,
    WizardSessionStatus,
    WizardType,
    get_declarative_pack_bundle_sql,
    list_declarative_pack_bundles_sql,
    upsert_declarative_pack_bundles_sql,
)
from orcia_core.packs.loader import DeclarativePackLoader, resolve_default_packs_root
from orcia_core.permissions.errors import ResourceNotFoundError, ValidationDomainError
from orcia_core.permissions.models import UserIdentity
from orcia_core.permissions.platform_settings import SecretInputSpec


class _FakeResult:
    def __init__(
        self, *, scalar_val: Any = None, rows: list[tuple[Any, ...]] | None = None
    ) -> None:
        self._scalar_val = scalar_val
        self._rows = rows or []

    def scalar(self) -> Any:
        return self._scalar_val

    def fetchone(self) -> tuple[Any, ...] | None:
        return self._rows[0] if self._rows else None

    def fetchall(self) -> list[tuple[Any, ...]]:
        return list(self._rows)


class _FakeConnection:
    def __init__(self, handler: Any, recorded: list[tuple[str, dict[str, Any] | None]]) -> None:
        self._handler = handler
        self._recorded = recorded

    async def execute(self, stmt: Any, params: dict[str, Any] | None = None) -> _FakeResult:
        sql_text = str(stmt)
        self._recorded.append((sql_text, params))
        return self._handler(sql_text, params or {})


class _FakeAsyncEngine:
    def __init__(self, handler: Any) -> None:
        self._handler = handler
        self.executed: list[tuple[str, dict[str, Any] | None]] = []

    @asynccontextmanager
    async def begin(self) -> AsyncIterator[_FakeConnection]:
        yield _FakeConnection(self._handler, self.executed)

    @asynccontextmanager
    async def connect(self) -> AsyncIterator[_FakeConnection]:
        yield _FakeConnection(self._handler, self.executed)


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
async def test_declarative_pack_bundles_upsert_is_idempotent_and_persists_sha256() -> None:
    """Verify idempotent upsert, SHA-256 checksum storage, and read queries."""
    bundles = DeclarativePackLoader(resolve_default_packs_root()).load_all_packs()
    assert len(bundles) >= 2

    stored_by_pack_id: dict[str, tuple[Any, ...]] = {}
    now = datetime(2026, 11, 19, 6, 30, tzinfo=UTC)

    def _sql_handler(sql_text: str, params: dict[str, Any]) -> _FakeResult:
        if "to_regclass('public.declarative_pack_bundles')" in sql_text:
            return _FakeResult(scalar_val="declarative_pack_bundles")
        if "DELETE FROM declarative_pack_bundles" in sql_text:
            return _FakeResult()
        if "INSERT INTO declarative_pack_bundles" in sql_text:
            pack_id = params["pack_id"]
            existing = stored_by_pack_id.get(pack_id)
            row_id = existing[0] if existing is not None else params["id"]
            row = (
                row_id,
                pack_id,
                params["slug"],
                params["name"],
                params["version"],
                params["rbac_namespace"],
                params["bundle_sha256"],
                params["manifest_jsonb"],
                now,
            )
            stored_by_pack_id[pack_id] = row
            return _FakeResult(rows=[row])
        if "ORDER BY slug ASC" in sql_text:
            return _FakeResult(rows=sorted(stored_by_pack_id.values(), key=lambda r: str(r[2])))
        if "WHERE pack_id = :key OR slug = :key" in sql_text:
            key = params["key"]
            matched = [r for r in stored_by_pack_id.values() if r[1] == key or r[2] == key]
            return _FakeResult(rows=matched[:1])
        return _FakeResult()

    fake_engine: Any = _FakeAsyncEngine(_sql_handler)
    first_pass = await upsert_declarative_pack_bundles_sql(fake_engine, bundles)
    second_pass = await upsert_declarative_pack_bundles_sql(fake_engine, bundles)

    assert len(first_pass) == len(bundles)
    assert len(second_pass) == len(bundles)
    assert [r.id for r in first_pass] == [r.id for r in second_pass]
    for rec in second_pass:
        expected_bundle = bundles[rec.pack_id]
        assert rec.bundle_sha256 == expected_bundle.bundle_sha256
        assert len(rec.bundle_sha256) == 64
        assert rec.manifest_jsonb["counts"]["agents"] == len(expected_bundle.agents_markdown)

    listed = await list_declarative_pack_bundles_sql(fake_engine)
    assert [r.slug for r in listed] == sorted(r.slug for r in listed)
    fetched = await get_declarative_pack_bundle_sql(fake_engine, "sdlc")
    assert fetched is not None
    assert fetched.pack_id == "orcia-pack-sdlc"
    assert await get_declarative_pack_bundle_sql(fake_engine, "   ") is None
    assert await upsert_declarative_pack_bundles_sql(fake_engine, {}) == []

    missing_table_engine: Any = _FakeAsyncEngine(lambda _sql, _params: _FakeResult(scalar_val=None))
    assert await upsert_declarative_pack_bundles_sql(missing_table_engine, bundles) == []
    assert await list_declarative_pack_bundles_sql(missing_table_engine) == []
    assert await get_declarative_pack_bundle_sql(missing_table_engine, "sdlc") is None


@pytest.mark.asyncio
async def test_packs_router_and_lifespan_do_not_use_disable_sync_env_var(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Verify `ORCIA_DISABLE_PG_BOOTSTRAP_SYNC` is absent and runtime check delegates cleanly."""
    from orcia_api.dependencies import core_and_lifespan
    from orcia_api.routers import packs as packs_router

    assert "ORCIA_DISABLE_PG_BOOTSTRAP_SYNC" not in inspect.getsource(packs_router)
    assert "ORCIA_DISABLE_PG_BOOTSTRAP_SYNC" not in inspect.getsource(core_and_lifespan)

    class _DummyState:
        db_engine: Any = None

    class _DummyApp:
        state = _DummyState()

    class _DummyRequest:
        app = _DummyApp()

    req: Any = _DummyRequest()
    bundles = DeclarativePackLoader(resolve_default_packs_root()).load_all_packs()

    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.delenv("ORCIA_ENABLE_PG_SESSION_MAKER", raising=False)
    await packs_router.sync_declarative_pack_bundles_to_pg(req, bundles)

    called: list[int] = []

    async def _fake_upsert(_engine: Any, passed_bundles: Any) -> list[Any]:
        called.append(len(passed_bundles))
        return []

    req.app.state.db_engine = object()
    monkeypatch.setattr(packs_router, "upsert_declarative_pack_bundles_sql", _fake_upsert)
    await packs_router.sync_declarative_pack_bundles_to_pg(req, bundles)
    assert called == [len(bundles)]


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


@pytest.mark.asyncio
async def test_sql_wizard_session_repository_persistence_contract() -> None:
    """Verify `SqlWizardSessionRepository` SQL contract, JSON serialization, and guards."""
    user_uuid = "0195f000-0000-7000-8000-000000000201"
    scope_uuid = "0195f000-0000-7000-8000-000000000301"
    sessions_table: dict[str, tuple[Any, ...]] = {}
    users_present = {user_uuid}
    now = datetime(2026, 11, 19, 6, 45, tzinfo=UTC)

    def _sql_handler(sql_text: str, params: dict[str, Any]) -> _FakeResult:
        if "FROM users WHERE id" in sql_text:
            return _FakeResult(scalar_val=1 if params["user_id"] in users_present else None)
        if "AND status = 'IN_PROGRESS'" in sql_text:
            matched = [
                r
                for r in sessions_table.values()
                if r[1] == params["wizard_type"]
                and r[2] == params["user_id"]
                and r[3] == params["scope_id"]
                and r[7] == "IN_PROGRESS"
            ]
            return _FakeResult(rows=matched[:1])
        if "WHERE dbos_workflow_id = :wf" in sql_text:
            taken = any(r[6] == params["wf"] for r in sessions_table.values())
            return _FakeResult(scalar_val=1 if taken else None)
        if "INSERT INTO wizard_sessions" in sql_text:
            row = (
                params["id"],
                params["wizard_type"],
                params["user_id"],
                params["scope_id"],
                1,
                params["state_jsonb"],
                params["dbos_workflow_id"],
                "IN_PROGRESS",
                now,
            )
            sessions_table[params["id"]] = row
            return _FakeResult(rows=[row])
        if "WHERE id = CAST(:id AS uuid) LIMIT 1" in sql_text:
            row = sessions_table.get(params["id"])
            return _FakeResult(rows=[row] if row is not None else [])
        if "WHERE user_id = CAST(:user_id AS uuid) ORDER BY updated_at DESC" in sql_text:
            matched = [r for r in sessions_table.values() if r[2] == params["user_id"]]
            return _FakeResult(rows=matched)
        if "UPDATE wizard_sessions" in sql_text:
            existing = sessions_table.get(params["id"])
            if existing is None:
                return _FakeResult(rows=[])
            updated = (
                existing[0],
                existing[1],
                existing[2],
                existing[3],
                params["current_step_index"],
                params["state_jsonb"],
                existing[6],
                params["status"],
                now,
            )
            sessions_table[params["id"]] = updated
            return _FakeResult(rows=[updated])
        return _FakeResult()

    repo = SqlWizardSessionRepository(_FakeAsyncEngine(_sql_handler))  # type: ignore[arg-type]

    with pytest.raises(ResourceNotFoundError):
        await repo.start_or_resume_wizard_async(
            user_id="0195f000-0000-7000-8000-000000000999",
            wizard_type="ops_manager",
            scope_id="scope-global",
            total_steps=5,
        )

    created = await repo.start_or_resume_wizard_async(
        user_id=user_uuid,
        wizard_type="ops_manager",
        scope_id="scope-global",
        total_steps=5,
    )
    assert created.scope_id == scope_uuid
    assert created.current_step_index == 1

    resumed = await repo.start_or_resume_wizard_async(
        user_id=user_uuid,
        wizard_type="ops_manager",
        scope_id="scope-global",
        total_steps=5,
    )
    assert resumed.id == created.id

    saved = await repo.save_step_and_advance_async(
        session_id=created.id,
        current_step_index=2,
        state_jsonb={"step_1": {"org_unit_name": "Ops Core"}},
        status="IN_PROGRESS",
        completed_steps=(1,),
        rag_reciprocity_verified=False,
    )
    assert saved is not None
    assert saved.completed_steps == (1,)
    assert saved.state_jsonb == {"step_1": {"org_unit_name": "Ops Core"}}

    fetched = await repo.get_session_async(created.id)
    assert fetched is not None
    assert fetched.current_step_index == 2
    assert await repo.get_session_async("not-a-uuid") is None

    listed = await repo.list_sessions_for_user_async(user_uuid)
    assert len(listed) == 1
    assert await repo.list_sessions_for_user_async("not-a-uuid") == []

    updated_state = await repo.update_session_state_async(
        session_id=created.id,
        state_jsonb={"step_1": {"org_unit_name": "Ops Core"}},
        status="ABANDONED",
    )
    assert updated_state is not None
    assert updated_state.status == "ABANDONED"

    # Starting again after ABANDONED creates a fresh session with unique dbos_workflow_id
    restarted = await repo.start_or_resume_wizard_async(
        user_id=user_uuid,
        wizard_type="ops_manager",
        scope_id="scope-global",
        total_steps=5,
    )
    assert restarted.id != created.id
    assert restarted.dbos_workflow_id != created.dbos_workflow_id
