"""Story 22.2 (Couche 1a) — Unit tests for SQL workspace waivers & ENTERPRISE root invitations."""

from __future__ import annotations

import json
from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID

import pytest

from orcia_api.routers._org_units_delegation_helpers import resolve_evaluator_target_node
from orcia_core.orchestration._internal.sql_workspace_waivers import (
    _parse_dna_chain,
    _row_to_waiver,
    list_workspace_waivers_sql,
    update_workspace_waiver_status_sql,
    upsert_workspace_waiver_sql,
)
from orcia_core.orchestration._workspace_governance_models import (
    SOVEREIGNTY_RANK,
    DnaChainNode,
    ExceptionWaiverRecord,
)
from orcia_core.orchestration.errors import (
    EnterpriseDirectiveWaiverForbiddenError,
    ResourceNotFoundError,
)
from orcia_core.orchestration.workspace_governance_and_rebaser import (
    WorkspaceGovernanceAndArtifactRoutingService,
)
from orcia_core.permissions import (
    MatrixPermissionEvaluator,
    OrgUnitNode,
    UserIdentity,
    assert_can_invite_org_user,
)
from orcia_core.permissions.errors import (
    ObserverModeReadOnlyError,
    OrgUnitScopeForbiddenError,
    PrivilegeEscalationForbiddenError,
)
from orcia_core.permissions.errors import (
    ResourceNotFoundError as PermissionsResourceNotFoundError,
)


class _FakeResult:
    def __init__(
        self,
        *,
        scalar: Any = None,
        rows: list[dict[str, Any]] | None = None,
        one_row: dict[str, Any] | None = None,
    ) -> None:
        self._scalar = scalar
        self._rows = rows or []
        self._one_row = one_row

    def scalar_one_or_none(self) -> Any:
        return self._scalar

    def mappings(self) -> _FakeResult:
        return self

    def all(self) -> list[dict[str, Any]]:
        return self._rows

    def one(self) -> dict[str, Any]:
        assert self._one_row is not None
        return self._one_row


class _FakeBeginCtx:
    async def __aenter__(self) -> _FakeBeginCtx:
        return self

    async def __aexit__(self, *args: object) -> None:
        return None


class _FakeAsyncSession:
    def __init__(self, handler: Callable[[str, dict[str, Any]], _FakeResult]) -> None:
        self._handler = handler
        self.calls: list[tuple[str, dict[str, Any]]] = []

    async def __aenter__(self) -> _FakeAsyncSession:
        return self

    async def __aexit__(self, *args: object) -> None:
        return None

    def begin(self) -> _FakeBeginCtx:
        return _FakeBeginCtx()

    async def execute(self, stmt: Any, params: dict[str, Any] | None = None) -> _FakeResult:
        sql = str(stmt)
        bound = dict(params or {})
        self.calls.append((sql, bound))
        return self._handler(sql, bound)


def _sample_waiver_row(ws_id: UUID, waiver_id: UUID, user_id: UUID) -> dict[str, Any]:
    now = datetime.now(UTC)
    return {
        "waiver_id": str(waiver_id),
        "workspace_id": str(ws_id),
        "source_uri": "orcia://sources/spec.md",
        "source_sha256": "sha256:abc12345",
        "conflict_rule_id": "rule-local-override",
        "norm_level": "3_WORKSPACE",
        "dna_chain_jsonb": [
            {
                "node_key": "norm-1",
                "stereotype": "NORM",
                "level": "3_WORKSPACE",
                "inviolable": False,
            }
        ],
        "approved_by_user_id": str(user_id),
        "approved_by_role": "PLATFORM_ADMIN",
        "reason": "Dérogation test unitaire",
        "status": "ACTIVE",
        "expires_at": now + timedelta(days=30),
        "created_at": now,
    }


def test_parse_dna_chain_and_row_to_waiver() -> None:
    nodes_from_json = _parse_dna_chain(
        json.dumps([{"node_key": "dir-1", "stereotype": "DIRECTIVE", "level": "1_ENTERPRISE"}])
    )
    assert len(nodes_from_json) == 1
    assert nodes_from_json[0].node_key == "dir-1"
    assert _parse_dna_chain("ignored-invalid" if False else None) == ()
    assert _parse_dna_chain(["not-a-mapping", {"node_key": "n2"}])[0].node_key == "n2"

    ws_id = UUID("0195f000-0000-7000-8000-000000000111")
    waiver_id = UUID("0195f000-0000-7000-8000-000000000222")
    user_id = UUID("0195f000-0000-7000-8000-000000000333")
    record = _row_to_waiver(_sample_waiver_row(ws_id, waiver_id, user_id))
    assert record.waiver_id == waiver_id
    assert record.workspace_id == ws_id
    assert record.status == "ACTIVE"
    assert SOVEREIGNTY_RANK["ON_PREM_AIRGAPPED"] > SOVEREIGNTY_RANK["CLOUD_PUBLIC"]


@pytest.mark.asyncio
async def test_sql_workspace_waivers_crud_and_not_found_guards() -> None:
    ws_id = UUID("0195f000-0000-7000-8000-000000000111")
    waiver_id = UUID("0195f000-0000-7000-8000-000000000222")
    user_id = UUID("0195f000-0000-7000-8000-000000000333")
    row = _sample_waiver_row(ws_id, waiver_id, user_id)
    sessions: list[_FakeAsyncSession] = []

    def handler(sql: str, params: dict[str, Any]) -> _FakeResult:
        if "FROM workspace_exception_waivers" in sql and "SELECT" in sql:
            assert "status = 'ACTIVE'" in sql
            return _FakeResult(rows=[row])
        if "FROM workspaces WHERE id" in sql:
            return _FakeResult(scalar=str(ws_id))
        if "FROM users WHERE id" in sql:
            return _FakeResult(scalar=None)
        if "FROM users WHERE lower(email)" in sql:
            return _FakeResult(scalar=str(user_id))
        if "INSERT INTO workspace_exception_waivers" in sql:
            assert params["approved_by_user_id"] == str(user_id)
            return _FakeResult(one_row=row)
        return _FakeResult()

    def session_factory() -> _FakeAsyncSession:
        sess = _FakeAsyncSession(handler)
        sessions.append(sess)
        return sess

    listed = await list_workspace_waivers_sql(
        session_factory,  # type: ignore[arg-type]
        workspace_id=ws_id,
        active_only=True,
    )
    assert len(listed) == 1
    assert listed[0].conflict_rule_id == "rule-local-override"

    listed_all = await list_workspace_waivers_sql(
        lambda: _FakeAsyncSession(
            lambda sql, _p: (
                _FakeResult(rows=[row])
                if "FROM workspace_exception_waivers" in sql
                else _FakeResult()
            )
        ),  # type: ignore[arg-type,return-value]
        workspace_id=ws_id,
        active_only=False,
    )
    assert len(listed_all) == 1

    # Approver matched directly by ID + fallback to earliest user when ID & email absent
    for lookup_sql, expected_id in (
        ("FROM users WHERE id", user_id),
        ("ORDER BY created_at ASC", user_id),
    ):

        def _make_approver_handler(target_fragment: str, uid: UUID):  # type: ignore[no-untyped-def]
            def _h(sql: str, _p: dict[str, Any]) -> _FakeResult:
                if "FROM workspaces WHERE id" in sql:
                    return _FakeResult(scalar=str(ws_id))
                if target_fragment in sql:
                    return _FakeResult(scalar=str(uid))
                if "INSERT INTO workspace_exception_waivers" in sql:
                    return _FakeResult(one_row=row)
                return _FakeResult(scalar=None)

            return _h

        handler_fn = _make_approver_handler(lookup_sql, expected_id)
        saved_direct = await upsert_workspace_waiver_sql(
            lambda h=handler_fn: _FakeAsyncSession(h),  # type: ignore[arg-type,misc,return-value]
            ExceptionWaiverRecord(
                waiver_id=waiver_id,
                workspace_id=ws_id,
                source_uri="orcia://sources/spec.md",
                source_sha256="sha256:abc12345",
                conflict_rule_id="rule-local-override",
                norm_level="3_WORKSPACE",
                dna_chain=(DnaChainNode("norm-1", "NORM", "3_WORKSPACE", False),),
                approved_by_user_id=user_id,
                approved_by_role="PLATFORM_ADMIN",
                reason="Dérogation test unitaire",
                status="ACTIVE",
                expires_at=datetime.now(UTC) + timedelta(days=30),
                created_at=datetime.now(UTC),
            ),
        )
        assert saved_direct.approved_by_user_id == expected_id

    waiver_input = ExceptionWaiverRecord(
        waiver_id=waiver_id,
        workspace_id=ws_id,
        source_uri="orcia://sources/spec.md",
        source_sha256="sha256:abc12345",
        conflict_rule_id="rule-local-override",
        norm_level="3_WORKSPACE",
        dna_chain=(DnaChainNode("norm-1", "NORM", "3_WORKSPACE", False),),
        approved_by_user_id=UUID("0195f000-0000-7000-8000-000000000999"),
        approved_by_role="PLATFORM_ADMIN",
        reason="Dérogation test unitaire",
        status="ACTIVE",
        expires_at=datetime.now(UTC) + timedelta(days=30),
        created_at=datetime.now(UTC),
    )
    saved = await upsert_workspace_waiver_sql(
        session_factory,  # type: ignore[arg-type]
        waiver_input,
        approved_by_email="admin@orcia.ia",
    )
    assert saved.approved_by_user_id == user_id

    await update_workspace_waiver_status_sql(
        session_factory,  # type: ignore[arg-type]
        waiver_id=waiver_id,
        status="INVALIDATED_SHA_DRIFT",
    )
    assert any("UPDATE workspace_exception_waivers" in sql for sql, _ in sessions[-1].calls)

    # Missing workspace raises ResourceNotFoundError
    def missing_ws_factory() -> _FakeAsyncSession:
        return _FakeAsyncSession(lambda _sql, _p: _FakeResult(scalar=None))

    with pytest.raises(ResourceNotFoundError):
        await upsert_workspace_waiver_sql(
            missing_ws_factory,  # type: ignore[arg-type]
            waiver_input,
        )

    # Existing workspace but zero users raises ResourceNotFoundError
    def no_user_handler(sql: str, _p: dict[str, Any]) -> _FakeResult:
        if "FROM workspaces WHERE id" in sql:
            return _FakeResult(scalar=str(ws_id))
        return _FakeResult(scalar=None)

    with pytest.raises(ResourceNotFoundError):
        await upsert_workspace_waiver_sql(
            lambda: _FakeAsyncSession(no_user_handler),  # type: ignore[arg-type,return-value]
            waiver_input,
        )


@pytest.mark.asyncio
async def test_workspace_governance_service_waivers_lifecycle_and_guards() -> None:
    svc = WorkspaceGovernanceAndArtifactRoutingService()
    ws_id = UUID("0195f000-0000-7000-8000-000000000111")
    user_id = UUID("0195f000-0000-7000-8000-000000000333")

    with pytest.raises(ObserverModeReadOnlyError):
        svc.register_exception_waiver(
            workspace_id=ws_id,
            source_uri="orcia://sources/spec.md",
            source_sha256="sha256:11111111",
            conflict_rule_id="rule-1",
            norm_level="3_WORKSPACE",
            dna_chain=[],
            approved_by_user_id=user_id,
            approved_by_role="READ_ONLY_OBSERVER",
            reason="Blocked",
        )

    with pytest.raises(EnterpriseDirectiveWaiverForbiddenError):
        svc.register_exception_waiver(
            workspace_id=ws_id,
            source_uri="orcia://sources/spec.md",
            source_sha256="sha256:11111111",
            conflict_rule_id="rule-enterprise",
            norm_level="2_DOMAIN",
            dna_chain=[DnaChainNode("dir-root", "DIRECTIVE", "1_ENTERPRISE", inviolable=True)],
            approved_by_user_id=user_id,
            approved_by_role="TEAM_LEAD",
            reason="Should fail",
        )

    waiver = await svc.register_exception_waiver_async(
        workspace_id=ws_id,
        source_uri="orcia://sources/spec.md",
        source_sha256="sha256:11111111",
        conflict_rule_id="rule-local",
        norm_level="3_WORKSPACE",
        dna_chain=[],
        approved_by_user_id=user_id,
        approved_by_role="TEAM_LEAD",
        reason="Valid workspace waiver",
    )
    assert waiver.status == "ACTIVE"

    state = await svc.get_workspace_five_tabs_state_async(
        workspace_id=ws_id,
        workspace_slug="ws-demo",
    )
    assert len(state.active_waivers) == 1
    assert state.active_waivers[0].waiver_id == waiver.waiver_id

    assert (
        await svc.evaluate_conflict_waiver_async(
            workspace_id=ws_id,
            source_uri="orcia://sources/spec.md",
            current_source_sha256="sha256:11111111",
            conflict_rule_id="rule-local",
        )
        is True
    )
    # SHA-256 drift invalidates the waiver
    assert (
        await svc.evaluate_conflict_waiver_async(
            workspace_id=ws_id,
            source_uri="orcia://sources/spec.md",
            current_source_sha256="sha256:22222222",
            conflict_rule_id="rule-local",
        )
        is False
    )
    assert await svc.list_exception_waivers_async(workspace_id=ws_id, active_only=True) == []

    # Sync evaluate_conflict_waiver: unrelated workspace + expired waiver
    other_ws = UUID("0195f000-0000-7000-8000-000000000999")
    assert (
        svc.evaluate_conflict_waiver(
            workspace_id=other_ws,
            source_uri="orcia://sources/spec.md",
            current_source_sha256="sha256:11111111",
            conflict_rule_id="rule-local",
        )
        is False
    )
    expired_waiver = ExceptionWaiverRecord(
        waiver_id=UUID("0195f000-0000-7000-8000-000000000777"),
        workspace_id=ws_id,
        source_uri="orcia://sources/expired.md",
        source_sha256="sha256:exp11111",
        conflict_rule_id="rule-exp",
        norm_level="3_WORKSPACE",
        dna_chain=(),
        approved_by_user_id=user_id,
        approved_by_role="PLATFORM_ADMIN",
        reason="Expired sync",
        status="ACTIVE",
        expires_at=datetime.now(UTC) - timedelta(days=1),
        created_at=datetime.now(UTC) - timedelta(days=2),
    )
    svc._waivers[expired_waiver.waiver_id] = expired_waiver  # noqa: SLF001
    assert (
        svc.evaluate_conflict_waiver(
            workspace_id=ws_id,
            source_uri="orcia://sources/expired.md",
            current_source_sha256="sha256:exp11111",
            conflict_rule_id="rule-exp",
        )
        is False
    )

    # Service backed by async session_factory exercises SQL delegation, expiration & drift updates
    updated_statuses: list[str] = []
    other_source_row = _sample_waiver_row(
        ws_id, UUID("0195f000-0000-7000-8000-000000000801"), user_id
    )
    other_source_row["source_uri"] = "orcia://sources/other.md"
    expired_row = _sample_waiver_row(ws_id, UUID("0195f000-0000-7000-8000-000000000802"), user_id)
    expired_row["source_uri"] = "orcia://sources/spec.md"
    expired_row["expires_at"] = datetime.now(UTC) - timedelta(hours=1)
    drift_row = _sample_waiver_row(ws_id, UUID("0195f000-0000-7000-8000-000000000803"), user_id)
    drift_row["source_uri"] = "orcia://sources/spec.md"
    drift_row["source_sha256"] = "sha256:old-hash"

    def svc_handler(sql: str, params: dict[str, Any]) -> _FakeResult:
        if "FROM workspace_exception_waivers" in sql and "SELECT" in sql:
            return _FakeResult(rows=[other_source_row, expired_row, drift_row])
        if "UPDATE workspace_exception_waivers" in sql:
            updated_statuses.append(str(params["status"]))
            return _FakeResult()
        if "FROM workspaces WHERE id" in sql:
            return _FakeResult(scalar=str(ws_id))
        if "FROM users WHERE id" in sql:
            return _FakeResult(scalar=str(user_id))
        if "INSERT INTO workspace_exception_waivers" in sql:
            return _FakeResult(
                one_row=_sample_waiver_row(ws_id, UUID(params["waiver_id"]), user_id)
            )
        return _FakeResult()

    sql_svc = WorkspaceGovernanceAndArtifactRoutingService(
        session_factory=lambda: _FakeAsyncSession(svc_handler)  # type: ignore[arg-type,return-value]
    )
    sql_svc.configure_workspace_tabs(
        workspace_id=ws_id,
        workspace_slug="ws-sql",
        actor_role="PLATFORM_ADMIN",
        default_artifact_destination_uri="orcia://workspaces/ws-sql/artifacts",
        sources=None,
    )
    created_sql = await sql_svc.register_exception_waiver_async(
        workspace_id=ws_id,
        source_uri="orcia://sources/spec.md",
        source_sha256="sha256:abc12345",
        conflict_rule_id="rule-local-override",
        norm_level="3_WORKSPACE",
        dna_chain=[],
        approved_by_user_id=user_id,
        approved_by_role="PLATFORM_ADMIN",
        reason="SQL-backed",
    )
    assert created_sql.status == "ACTIVE"
    assert (
        await sql_svc.evaluate_conflict_waiver_async(
            workspace_id=ws_id,
            source_uri="orcia://sources/spec.md",
            current_source_sha256="sha256:new-hash",
            conflict_rule_id="rule-local-override",
        )
        is False
    )
    assert updated_statuses == ["EXPIRED", "INVALIDATED_SHA_DRIFT"]


def test_enterprise_root_invitation_rules_and_target_node_resolver() -> None:
    root_id = "0192c4e0-0000-7000-8000-000000000001"
    root_node = OrgUnitNode(
        id=root_id,
        slug="orcia-root",
        name="Plateforme Globale ORCIA",
        unit_type="ENTERPRISE",
        parent_id=None,
    )
    bu_node = OrgUnitNode(
        id="0192c4e0-0000-7000-8000-000000000201",
        slug="bu-ops",
        name="Direction Ops",
        unit_type="BU",
        parent_id=root_id,
        lead_user_ids=("bu.lead@orcia.ia",),
    )
    team_node = OrgUnitNode(
        id="0192c4e0-0000-7000-8000-000000000301",
        slug="team-ops",
        name="Équipe Ops",
        unit_type="TEAM",
        parent_id=bu_node.id,
        lead_user_ids=("team.lead@orcia.ia",),
    )
    org_units = (root_node, bu_node, team_node)

    admin = UserIdentity(
        id="u-admin",
        email="admin@orcia.ia",
        display_name="Admin",
        auth_mode="LOCAL",
        human_profile_archetype="ADMIN",
        platform_role="PLATFORM_ADMIN",
        primary_org_unit_id=root_id,
        roles=("PLATFORM_ADMIN",),
    )
    bu_lead = UserIdentity(
        id="u-bulead",
        email="bu.lead@orcia.ia",
        display_name="BU Lead",
        auth_mode="LOCAL",
        human_profile_archetype="EXECUTIVE",
        platform_role="BU_LEAD",
        primary_org_unit_id=bu_node.id,
        roles=("BU_LEAD",),
    )
    team_lead = UserIdentity(
        id="u-teamlead",
        email="team.lead@orcia.ia",
        display_name="Team Lead",
        auth_mode="LOCAL",
        human_profile_archetype="TECH_LEAD",
        platform_role="TEAM_LEAD",
        primary_org_unit_id=team_node.id,
        roles=("TEAM_LEAD",),
    )

    # PLATFORM_ADMIN can invite CONTRIBUTOR onto root ENTERPRISE
    canonical, effective = assert_can_invite_org_user(
        admin,
        target_unit=root_node,
        assignment_role="CONTRIBUTOR",
        org_units=org_units,
    )
    assert canonical == "TEAM_MEMBER"
    assert effective == ("CONTRIBUTOR",)

    # Anti-escalation holds on ENTERPRISE root
    with pytest.raises(PrivilegeEscalationForbiddenError):
        assert_can_invite_org_user(
            admin,
            target_unit=root_node,
            assignment_role="PLATFORM_ADMIN",
            org_units=org_units,
        )

    # BU_LEAD and TEAM_LEAD remain forbidden on ENTERPRISE root
    for caller in (bu_lead, team_lead):
        with pytest.raises(OrgUnitScopeForbiddenError):
            assert_can_invite_org_user(
                caller,
                target_unit=root_node,
                assignment_role="CONTRIBUTOR",
                org_units=org_units,
            )

    # resolve_evaluator_target_node permits ENTERPRISE only when allow_enterprise=True
    evaluator = MatrixPermissionEvaluator(org_units=[], workspaces=[])
    evaluator.replace_org_units(org_units)
    assert resolve_evaluator_target_node(evaluator, root_id, allow_enterprise=True).id == root_id
    assert (
        resolve_evaluator_target_node(evaluator, "orcia-root", allow_enterprise=True).id == root_id
    )
    with pytest.raises(PermissionsResourceNotFoundError):
        resolve_evaluator_target_node(evaluator, root_id, allow_enterprise=False)

    # Synthetic fallback when evaluator has no ENTERPRISE node yet
    empty_eval = MatrixPermissionEvaluator(org_units=[], workspaces=[])
    fallback_root = resolve_evaluator_target_node(empty_eval, root_id, allow_enterprise=True)
    assert fallback_root.unit_type == "ENTERPRISE"
    assert fallback_root.id == root_id
