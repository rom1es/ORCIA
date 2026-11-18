"""Unit tests for Story 20.2: Ontology L1–L4 permissions, step-up promotions & mappers."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from orcia_core.ontology import (
    OntologyConceptEntity,
    OntologyGovernanceService,
    WhatIfImpactReport,
    assert_can_review_promotion,
    assert_can_write_ontology_level,
    build_seeded_ontology_service,
    can_read_ontology_item,
    can_review_promotion_target,
    can_write_ontology_level,
    resolve_next_promotion_target,
)
from orcia_core.ontology._internal.sql_ontology_mappers import (
    maybe_uuid,
    parse_json_dict,
    parse_json_list,
    row_to_concept,
    row_to_proposal,
)
from orcia_core.ontology.errors import (
    ObserverModeReadOnlyError,
    PromotionLevelJumpError,
    ScopeAccessDeniedError,
)
from orcia_core.permissions.models import (
    OrgUnitNode,
    UserIdentity,
    WorkspaceEntity,
    WorkspaceMembershipEntity,
)


def _u(
    uid: str,
    email: str,
    role: str,
    org_id: str,
    roles: tuple[str, ...] = (),
) -> UserIdentity:
    return UserIdentity(
        id=uid,
        email=email,
        display_name=email,
        auth_mode="LOCAL",
        human_profile_archetype="TECH_LEAD",
        platform_role=role,  # type: ignore[arg-type]
        primary_org_unit_id=org_id,
        roles=roles,
    )


def _topology():
    bu_fin = OrgUnitNode(
        id="bu-fin",
        slug="bu-fin",
        name="BU Finance",
        unit_type="BU",
        lead_user_ids=("bu.lead@orcia.ia",),
        ontology_lead_user_ids=("onto.lead@orcia.ia",),
    )
    sub_bu = OrgUnitNode(
        id="bu-fintech",
        slug="bu-fintech",
        name="FinTech",
        unit_type="BU",
        parent_id="bu-fin",
    )
    bu_other = OrgUnitNode(
        id="bu-other",
        slug="bu-other",
        name="BU Other",
        unit_type="BU",
        lead_user_ids=("other.lead@orcia.ia",),
    )
    team = OrgUnitNode(
        id="team-pay",
        slug="team-pay",
        name="Team Pay",
        unit_type="TEAM",
        parent_id="bu-fintech",
        lead_user_ids=("team.lead@orcia.ia",),
        member_user_ids=("dev@orcia.ia",),
    )
    ws_team = WorkspaceEntity(
        id="ws-pay",
        slug="ws-pay",
        name="WS Pay",
        owner_org_unit_id="team-pay",
    )
    ws_bu = WorkspaceEntity(
        id="ws-bu-direct",
        slug="ws-bu-direct",
        name="WS BU Direct",
        owner_org_unit_id="bu-fin",
    )
    return (bu_fin, sub_bu, bu_other, team), (ws_team, ws_bu)


def test_l1_to_l4_write_matrix_and_ontology_lead_inheritance() -> None:
    org_units, workspaces = _topology()
    admin = _u("u-admin", "admin@orcia.ia", "PLATFORM_ADMIN", "bu-fin", ("PLATFORM_ADMIN",))
    bu_lead = _u("u-bu", "bu.lead@orcia.ia", "BU_LEAD", "bu-fin", ("BU_LEAD",))
    bu_dir = _u("u-dir", "bu.lead@orcia.ia", "BU_DIRECTOR", "bu-fin", ("BU_DIRECTOR",))
    onto_lead = _u("u-onto", "onto.lead@orcia.ia", "ONTOLOGY_LEAD", "bu-fin", ("ONTOLOGY_LEAD",))
    team_lead = _u("u-team", "team.lead@orcia.ia", "TEAM_LEAD", "team-pay", ("TEAM_LEAD",))
    contrib = _u("u-dev", "dev@orcia.ia", "CONTRIBUTOR", "team-pay", ("CONTRIBUTOR",))
    observer = _u("u-obs", "obs@orcia.ia", "OBSERVER", "team-pay", ("OBSERVER",))

    # L1: PLATFORM_ADMIN only
    assert can_write_ontology_level(admin, "1_ENTERPRISE", "scope-global", org_units, workspaces)
    for non_admin in (bu_lead, bu_dir, onto_lead, team_lead, contrib, observer):
        assert not can_write_ontology_level(
            non_admin, "1_ENTERPRISE", "scope-global", org_units, workspaces
        )

    # L2: PLATFORM_ADMIN, BU_LEAD/BU_DIRECTOR, ONTOLOGY_LEAD (inherited on sub-BU)
    for actor in (admin, bu_lead, bu_dir, onto_lead):
        assert can_write_ontology_level(actor, "2_DOMAIN", "bu-fin", org_units, workspaces)
        assert can_write_ontology_level(actor, "2_DOMAIN", "bu-fintech", org_units, workspaces)
    assert not can_write_ontology_level(onto_lead, "2_DOMAIN", "bu-other", org_units, workspaces)
    assert not can_write_ontology_level(team_lead, "2_DOMAIN", "bu-fin", org_units, workspaces)

    # L3: TEAM_LEAD of team + ancestor BU leads/ontology leads
    for actor in (admin, bu_lead, onto_lead, team_lead):
        assert can_write_ontology_level(actor, "3_TEAM", "team-pay", org_units, workspaces)
    assert not can_write_ontology_level(contrib, "3_TEAM", "team-pay", org_units, workspaces)

    # L4: CONTRIBUTOR member + leads; OBSERVER rejected with 403 ERR_OBSERVER_MODE_READ_ONLY
    assert can_write_ontology_level(contrib, "4_WORKSPACE", "ws-pay", org_units, workspaces)
    assert not can_write_ontology_level(observer, "4_WORKSPACE", "ws-pay", org_units, workspaces)
    with pytest.raises(ObserverModeReadOnlyError):
        assert_can_write_ontology_level(observer, "4_WORKSPACE", "ws-pay", org_units, workspaces)
    with pytest.raises(ScopeAccessDeniedError):
        assert_can_write_ontology_level(
            onto_lead, "1_ENTERPRISE", "scope-global", org_units, workspaces
        )

    # Direct membership observer override on workspace
    mem_obs = WorkspaceMembershipEntity(
        id="m-1",
        workspace_id="ws-pay",
        user_id="u-dev",
        role="OBSERVER",
        access_mode="READ_ONLY_OBSERVER",
    )
    assert not can_write_ontology_level(
        contrib, "4_WORKSPACE", "ws-pay", org_units, workspaces, (mem_obs,)
    )
    assert can_read_ontology_item(contrib, "2_DOMAIN", "bu-fin", org_units, workspaces)
    assert not can_read_ontology_item(contrib, "2_DOMAIN", "bu-other", org_units, workspaces)


def test_step_by_step_promotion_resolution_and_review_guards() -> None:
    org_units, workspaces = _topology()
    admin = _u("u-admin", "admin@orcia.ia", "PLATFORM_ADMIN", "bu-fin", ("PLATFORM_ADMIN",))
    onto_lead = _u("u-onto", "onto.lead@orcia.ia", "ONTOLOGY_LEAD", "bu-fin", ("ONTOLOGY_LEAD",))
    team_lead = _u("u-team", "team.lead@orcia.ia", "TEAM_LEAD", "team-pay", ("TEAM_LEAD",))
    contrib = _u("u-dev", "dev@orcia.ia", "CONTRIBUTOR", "team-pay", ("CONTRIBUTOR",))

    assert resolve_next_promotion_target("4_WORKSPACE", "ws-pay", org_units, workspaces) == (
        "3_TEAM",
        "team-pay",
    )
    assert resolve_next_promotion_target("4_WORKSPACE", "ws-bu-direct", org_units, workspaces) == (
        "2_DOMAIN",
        "bu-fin",
    )
    assert resolve_next_promotion_target("3_TEAM", "team-pay", org_units, workspaces) == (
        "2_DOMAIN",
        "bu-fintech",
    )
    assert resolve_next_promotion_target(
        "2_DOMAIN", "bu-fintech", org_units, workspaces, explicit_target_level="2_DOMAIN"
    ) == ("2_DOMAIN", "bu-fin")
    assert resolve_next_promotion_target("2_DOMAIN", "bu-fin", org_units, workspaces) == (
        "1_ENTERPRISE",
        "scope-global",
    )

    with pytest.raises(PromotionLevelJumpError):
        resolve_next_promotion_target(
            "4_WORKSPACE", "ws-pay", org_units, workspaces, explicit_target_level="1_ENTERPRISE"
        )
    with pytest.raises(PromotionLevelJumpError):
        resolve_next_promotion_target("1_ENTERPRISE", "scope-global", org_units, workspaces)

    assert can_review_promotion_target(team_lead, "3_TEAM", "team-pay", org_units, workspaces)
    assert not can_review_promotion_target(contrib, "3_TEAM", "team-pay", org_units, workspaces)
    assert can_review_promotion_target(onto_lead, "2_DOMAIN", "bu-fin", org_units, workspaces)
    assert not can_review_promotion_target(
        onto_lead, "1_ENTERPRISE", "scope-global", org_units, workspaces
    )
    assert can_review_promotion_target(admin, "1_ENTERPRISE", "scope-global", org_units, workspaces)

    with pytest.raises(ScopeAccessDeniedError):
        assert_can_review_promotion(
            onto_lead, "1_ENTERPRISE", "scope-global", org_units, workspaces
        )


def test_governance_service_supports_bu_director_and_new_roles() -> None:
    gov: OntologyGovernanceService = build_seeded_ontology_service()
    bu_dir = _u("u-dir", "claire@orcia.ia", "BU_DIRECTOR", "bu-1", ("BU_DIRECTOR",))
    onto_lead = _u("u-onto", "onto@orcia.ia", "ONTOLOGY_LEAD", "bu-1", ("ONTOLOGY_LEAD",))
    c_l4, prop = gov.extract_l4_concept(
        bu_dir,
        concept_key="c-l4-dir",
        canonical_term="Terme Dir",
        run_id="run-1",
        snapshot_id="snap-1",
        definition_text="Def",
        target_promotion_level="2_DOMAIN",
        target_scope_id="bu-1",
    )
    assert c_l4.level == "4_RUN_EPHEMERAL"
    approved = gov.promote_concept(onto_lead, proposal_key=prop.proposal_key)
    assert approved.status == "APPROVED"

    # L1 promotion denied for ONTOLOGY_LEAD
    _, prop_l1 = gov.extract_l4_concept(
        bu_dir,
        concept_key="c-l4-l1",
        canonical_term="Terme L1",
        run_id="run-1",
        snapshot_id="snap-1",
        definition_text="Def",
        target_promotion_level="1_ENTERPRISE",
        target_scope_id="scope-global",
    )
    with pytest.raises(ScopeAccessDeniedError):
        gov.promote_concept(onto_lead, proposal_key=prop_l1.proposal_key)


def test_sql_ontology_mappers_roundtrip() -> None:
    assert parse_json_list('["a", "b"]') == ("a", "b")
    assert parse_json_list("bad-json") == ()
    assert parse_json_dict('{"k": "v"}') == {"k": "v"}
    assert parse_json_dict("bad-json") == {}
    assert maybe_uuid("not-a-uuid") is None
    assert (
        maybe_uuid("0192c4e0-0000-7000-8000-000000002001") == "0192c4e0-0000-7000-8000-000000002001"
    )

    c_row = (
        "0192c4e0-0000-7000-8000-000000002001",
        "c-key",
        "Terme",
        "4_WORKSPACE",
        "ws-1",
        None,
        "Def",
        ["syn"],
        [],
        {"EXECUTIVE": "Exec"},
        {"id": "str"},
        None,
        "ACTIVE",
    )
    c = row_to_concept(c_row)
    assert c.level == "4_WORKSPACE"
    assert c.synonyms == ("syn",)

    now = datetime.now(UTC)
    p_row = (
        "0192c4e0-0000-7000-8000-000000002301",
        "prop-1",
        c.id,
        "4_WORKSPACE",
        "3_TEAM",
        "team-1",
        None,
        "PENDING_REVIEW",
        {
            "concept_key": "c-key",
            "canonical_term": "Terme",
            "proposed_change": "Promote",
            "collision_detected": True,
            "colliding_definition": "Existing",
            "proposed_by_actor": "dev@orcia.ia",
        },
        now,
        c.id,
        "c-key",
        "Terme",
        "Def",
        "ws-1",
        None,
        None,
        None,
    )
    p = row_to_proposal(p_row)
    assert p.collision_detected is True
    assert p.colliding_definition == "Existing"
    assert p.proposed_by_user_id == "dev@orcia.ia"


class _FakeResult:
    def __init__(self, rows: list[tuple[object, ...]] | None = None, scalar_val: object = None):
        self._rows = rows or []
        self._scalar = scalar_val

    def scalar(self) -> object:
        return self._scalar

    def fetchall(self) -> list[tuple[object, ...]]:
        return self._rows

    def first(self) -> tuple[object, ...] | None:
        return self._rows[0] if self._rows else None

    def one(self) -> tuple[object, ...]:
        return self._rows[0]


class _FakeAsyncConn:
    def __init__(self, handler) -> None:  # type: ignore[no-untyped-def]
        self._handler = handler

    async def execute(self, stmt, params=None):  # type: ignore[no-untyped-def]
        return self._handler(str(stmt), params or {})


class _FakeCtx:
    def __init__(self, conn: _FakeAsyncConn) -> None:
        self._conn = conn

    async def __aenter__(self) -> _FakeAsyncConn:
        return self._conn

    async def __aexit__(self, *_args: object) -> None:
        return None


class _FakeEngine:
    def __init__(self, handler) -> None:  # type: ignore[no-untyped-def]
        self._conn = _FakeAsyncConn(handler)

    def connect(self) -> _FakeCtx:
        return _FakeCtx(self._conn)

    def begin(self) -> _FakeCtx:
        return _FakeCtx(self._conn)


@pytest.mark.asyncio
async def test_sql_ontology_repository_unit_coverage() -> None:
    from orcia_core.ontology._internal.sql_ontology_mappers import (
        load_org_and_workspaces_context,
    )
    from orcia_core.ontology._internal.sql_ontology_queries import (
        record_ontology_audit_event_pg,
    )
    from orcia_core.ontology._internal.sql_ontology_repository import (
        create_proposal_pg,
        decide_proposal_pg,
        get_proposal_pg,
        list_concepts_pg,
        list_proposals_pg,
        upsert_concept_pg,
    )
    from orcia_core.ontology.errors import OntologyConflictError, ResourceNotFoundError

    cid = "0192c4e0-0000-7000-8000-000000002001"
    pid = "0192c4e0-0000-7000-8000-000000002301"
    now = datetime.now(UTC)
    c_row = (
        cid,
        "c-key",
        "Terme",
        "4_WORKSPACE",
        "ws-1",
        None,
        "Def",
        [],
        [],
        {},
        {},
        None,
        "ACTIVE",
    )
    p_row_pending = (
        pid,
        "prop-1",
        cid,
        "4_WORKSPACE",
        "3_TEAM",
        "team-1",
        None,
        "PENDING_REVIEW",
        {"concept_key": "c-key", "canonical_term": "Terme", "proposed_change": "Up"},
        now,
        cid,
        "c-key",
        "Terme",
        "Def",
        "ws-1",
        None,
        None,
        None,
    )
    p_row_approved = (
        *p_row_pending[:7],
        "APPROVED",
        *p_row_pending[8:15],
        "lead@orcia.ia",
        now,
        "OK",
    )
    state = {"status": "PENDING_REVIEW", "tables_present": True, "existing_concept": False}

    def handler(sql: str, _params: dict[str, object]) -> _FakeResult:
        if "SELECT to_regclass" in sql:
            return _FakeResult(scalar_val="ok" if state["tables_present"] else None)
        if "FROM org_units" in sql:
            return _FakeResult(
                rows=[
                    ("bu-1", "bu-1", "BU", "BU", None, True, None, [], [], ["onto@orcia.ia"]),
                ]
            )
        if "FROM workspaces" in sql:
            return _FakeResult(rows=[("ws-1", "ws-1", "WS", "bu-1", "STANDARD", 0.0)])
        if "FROM ontology_concepts WHERE snapshot_branch_status" in sql:
            return _FakeResult(rows=[c_row])
        if "SELECT id, concept_key, level, scope_id FROM ontology_concepts" in sql:
            if state["existing_concept"] and _params.get("concept_key") == "c-key":
                return _FakeResult(rows=[(cid, "c-key", "4_WORKSPACE", "ws-1")])
            return _FakeResult(rows=[])
        if "SELECT definition_text FROM ontology_concepts" in sql:
            return _FakeResult(rows=[("Def existante",)])
        if "SELECT id FROM users" in sql:
            return _FakeResult(rows=[("0192c4e0-0000-7000-8000-000000000603",)])
        if "FROM ontology_concepts WHERE id =" in sql:
            return _FakeResult(rows=[c_row])
        if "FROM ontology_promotion_proposals p" in sql:
            if "p.proposal_key = 'missing'" in str(_params.get("ref", "")):
                return _FakeResult(rows=[])
            if _params.get("ref") == "missing":
                return _FakeResult(rows=[])
            row = p_row_approved if state["status"] == "APPROVED" else p_row_pending
            return _FakeResult(rows=[row])
        return _FakeResult()

    eng: object = _FakeEngine(handler)
    units, wss = await load_org_and_workspaces_context(eng)  # type: ignore[arg-type]
    assert len(units) == 1 and len(wss) == 1
    assert len(await list_concepts_pg(eng)) == 1  # type: ignore[arg-type]

    c_entity = OntologyConceptEntity(
        id=cid,
        concept_key="c-key",
        canonical_term="Terme",
        level="4_WORKSPACE",
        scope_id="ws-1",
        definition_text="Def",
    )
    saved_insert = await upsert_concept_pg(eng, c_entity)  # type: ignore[arg-type]
    assert saved_insert.concept_key == "c-key"
    state["existing_concept"] = True
    saved_update = await upsert_concept_pg(eng, c_entity)  # type: ignore[arg-type]
    assert saved_update.concept_key == "c-key"

    assert len(await list_proposals_pg(eng, status="PENDING_REVIEW")) == 1  # type: ignore[arg-type]
    assert (await get_proposal_pg(eng, "prop-1")) is not None  # type: ignore[arg-type]
    assert (await get_proposal_pg(eng, "missing")) is None  # type: ignore[arg-type]

    actor = _u("u-1", "dev@orcia.ia", "CONTRIBUTOR", "team-1")
    created = await create_proposal_pg(
        eng,  # type: ignore[arg-type]
        source_concept=c_entity,
        target_level="3_TEAM",
        target_scope_id="team-1",
        proposed_by=actor,
        impact_report=WhatIfImpactReport(
            concept_key="c-key",
            canonical_term="Terme",
            proposed_change="Up",
            transitively_affected_concepts=(),
            impacted_artifact_templates=(),
            impacted_workflow_uris=(),
            impacted_active_run_ids=(),
        ),
    )
    assert created.proposal_key == "prop-1"

    with pytest.raises(ResourceNotFoundError):
        await decide_proposal_pg(
            eng,  # type: ignore[arg-type]
            proposal_id_or_key="missing",
            decision="APPROVE",
            reviewer=actor,
        )
    state["status"] = "APPROVED"
    with pytest.raises(OntologyConflictError):
        await decide_proposal_pg(
            eng,  # type: ignore[arg-type]
            proposal_id_or_key="prop-1",
            decision="APPROVE",
            reviewer=actor,
        )
    state["status"] = "PENDING_REVIEW"
    decided, promoted = await decide_proposal_pg(
        eng,  # type: ignore[arg-type]
        proposal_id_or_key="prop-1",
        decision="APPROVE",
        reviewer=actor,
        review_comment="OK",
    )
    assert decided.status == "PENDING_REVIEW" or promoted is not None

    await record_ontology_audit_event_pg(
        eng,  # type: ignore[arg-type]
        actor=actor,
        event_type="ONTOLOGY_CONCEPT_CREATED",
        summary="Test",
        scope_id="ws-1",
        metadata={"k": "v"},
    )

    state["tables_present"] = False
    assert await list_concepts_pg(eng) == []  # type: ignore[arg-type]
    assert await list_proposals_pg(eng) == []  # type: ignore[arg-type]
    assert (await get_proposal_pg(eng, "prop-1")) is None  # type: ignore[arg-type]
    assert await load_org_and_workspaces_context(eng) == ((), ())  # type: ignore[arg-type]
    await record_ontology_audit_event_pg(
        eng,  # type: ignore[arg-type]
        actor=actor,
        event_type="ONTOLOGY_CONCEPT_CREATED",
        summary="Test",
        scope_id="ws-1",
        metadata={},
    )


def test_permissions_and_promotion_edge_cases_for_full_coverage() -> None:
    from orcia_core.ontology.errors import OntologyConflictError, ResourceNotFoundError

    org_units, workspaces = _topology()
    observer = _u("u-obs", "obs@orcia.ia", "OBSERVER", "team-pay", ("OBSERVER",))
    team_lead = _u("u-team", "team.lead@orcia.ia", "TEAM_LEAD", "team-pay", ("TEAM_LEAD",))
    bu_lead = _u("u-bu", "bu.lead@orcia.ia", "BU_LEAD", "bu-fin", ("BU_LEAD",))
    contrib = _u("u-dev", "dev@orcia.ia", "CONTRIBUTOR", "team-pay", ("CONTRIBUTOR",))
    outsider = _u("u-out", "out@orcia.ia", "CONTRIBUTOR", "other-team", ("CONTRIBUTOR",))

    assert not can_write_ontology_level(team_lead, "3_TEAM", "missing-team", org_units, workspaces)
    ws_orphan = WorkspaceEntity(
        id="ws-orphan", slug="ws-orphan", name="Orphan", owner_org_unit_id="missing-owner"
    )
    assert not can_write_ontology_level(
        contrib, "4_WORKSPACE", "ws-orphan", org_units, (*workspaces, ws_orphan)
    )
    assert can_write_ontology_level(team_lead, "4_WORKSPACE", "ws-pay", org_units, workspaces)
    assert can_write_ontology_level(bu_lead, "4_WORKSPACE", "ws-bu-direct", org_units, workspaces)

    assert not can_read_ontology_item(outsider, "2_DOMAIN", "missing-bu", org_units, workspaces)
    assert can_read_ontology_item(outsider, "3_TEAM", "team-pay", org_units, workspaces) is False
    assert can_read_ontology_item(contrib, "3_TEAM", "team-pay", org_units, workspaces) is True
    assert not can_read_ontology_item(outsider, "3_TEAM", "missing-team", org_units, workspaces)
    assert not can_read_ontology_item(outsider, "4_WORKSPACE", "ws-pay", org_units, workspaces)

    assert resolve_next_promotion_target("4_RUN_EPHEMERAL", "run-1", org_units, workspaces) == (
        "4_WORKSPACE",
        "run-1",
    )
    with pytest.raises(PromotionLevelJumpError):
        resolve_next_promotion_target(
            "4_RUN_EPHEMERAL", "run-1", org_units, workspaces, explicit_target_level="1_ENTERPRISE"
        )
    with pytest.raises(PromotionLevelJumpError):
        resolve_next_promotion_target(
            "4_WORKSPACE",
            "ws-bu-direct",
            org_units,
            workspaces,
            explicit_target_level="1_ENTERPRISE",
        )
    with pytest.raises(PromotionLevelJumpError):
        resolve_next_promotion_target("4_WORKSPACE", "ws-unknown", org_units, workspaces)
    with pytest.raises(PromotionLevelJumpError):
        resolve_next_promotion_target(
            "3_TEAM", "team-pay", org_units, workspaces, explicit_target_level="1_ENTERPRISE"
        )
    with pytest.raises(PromotionLevelJumpError):
        resolve_next_promotion_target("3_TEAM", "team-unknown", org_units, workspaces)
    with pytest.raises(PromotionLevelJumpError):
        resolve_next_promotion_target(
            "2_DOMAIN", "bu-fin", org_units, workspaces, explicit_target_level="3_TEAM"
        )
    assert not can_review_promotion_target(observer, "3_TEAM", "team-pay", org_units, workspaces)

    gov = build_seeded_ontology_service()
    with pytest.raises(ResourceNotFoundError):
        gov.promote_concept(team_lead, proposal_key="missing-prop")
    # Remove source concept to exercise missing source concept error
    prop_key = next(iter(gov._proposals))  # noqa: SLF001
    src_key = gov._proposals[prop_key].concept_key  # noqa: SLF001
    saved_src = gov._concepts.pop(src_key)  # noqa: SLF001
    with pytest.raises(ResourceNotFoundError):
        gov.promote_concept(team_lead, proposal_key=prop_key)
    gov._concepts[src_key] = saved_src  # noqa: SLF001
    # Superseded source branch raises OntologyConflictError
    gov.mark_snapshot_branch_superseded(saved_src.introduced_in_snapshot_id or "")
    with pytest.raises(OntologyConflictError):
        gov.promote_concept(team_lead, proposal_key=prop_key)


def test_security_guards_fail_closed_l4_forged_target_and_cross_scope_conflict() -> None:
    from orcia_core.ontology import resolve_next_promotion_target
    from orcia_core.ontology._internal.sql_ontology_queries import (
        resolve_ontology_audit_scope_uuids,
    )
    from orcia_core.ontology.errors import OntologyScopeConflictError

    org_units, workspaces = _topology()
    outsider = _u("u-out", "out@orcia.ia", "CONTRIBUTOR", "other-team", ("CONTRIBUTOR",))
    bu_lead = _u("u-bu", "bu.lead@orcia.ia", "BU_LEAD", "bu-fin", ("BU_LEAD",))
    onto_other = _u(
        "u-onto-o", "other.onto@orcia.ia", "ONTOLOGY_LEAD", "bu-other", ("ONTOLOGY_LEAD",)
    )

    # Fail-closed when workspace does not exist
    assert (
        can_read_ontology_item(outsider, "4_WORKSPACE", "ws-missing", org_units, workspaces)
        is False
    )
    # Ancestor BU lead can read workspace owned by child team
    assert can_read_ontology_item(bu_lead, "4_WORKSPACE", "ws-pay", org_units, workspaces) is True

    # Sub-BU defaults to parent BU even without explicit_target_level
    assert resolve_next_promotion_target("2_DOMAIN", "bu-fintech", org_units, workspaces) == (
        "2_DOMAIN",
        "bu-fin",
    )
    # Forged explicit_target_scope_id raises ScopeAccessDeniedError (403)
    with pytest.raises(ScopeAccessDeniedError):
        resolve_next_promotion_target(
            "4_WORKSPACE",
            "ws-pay",
            org_units,
            workspaces,
            explicit_target_scope_id="bu-other",
        )

    # Cross-scope upsert on same concept_key raises OntologyScopeConflictError (409)
    gov = build_seeded_ontology_service()
    with pytest.raises(OntologyScopeConflictError) as exc_info:
        gov.upsert_concept(
            bu_lead,
            OntologyConceptEntity(
                id="0192c4e0-0000-7000-8000-000000009999",
                concept_key="concept-l1-strategic-asset",
                canonical_term="Hijacked",
                level="2_DOMAIN",
                scope_id="bu-fin",
                definition_text="Attempted downgrade",
            ),
        )
    assert exc_info.value.http_status == 409

    # Cross-BU promote_concept denied even without org_units
    _, prop_bu = gov.extract_l4_concept(
        bu_lead,
        concept_key="c-l4-cross-bu",
        canonical_term="Terme BU Fin",
        run_id="run-1",
        snapshot_id="snap-1",
        definition_text="Def",
        target_promotion_level="2_DOMAIN",
        target_scope_id="bu-fin",
    )
    with pytest.raises(ScopeAccessDeniedError):
        gov.promote_concept(onto_other, proposal_key=prop_bu.proposal_key)

    # Audit ledger UUID mapping never mixes workspace_id into org_unit_id
    ws_uuid = "0192c4e0-0000-7000-8000-000000000201"
    team_uuid = "0192c4e0-0000-7000-8000-000000000104"
    assert resolve_ontology_audit_scope_uuids(
        level="4_WORKSPACE", scope_id=ws_uuid, owner_org_unit_id=team_uuid
    ) == (ws_uuid, team_uuid)
    assert resolve_ontology_audit_scope_uuids(
        level="2_DOMAIN", scope_id=team_uuid, owner_org_unit_id=ws_uuid
    ) == (None, team_uuid)
    assert resolve_ontology_audit_scope_uuids(
        level="1_ENTERPRISE", scope_id="scope-global", owner_org_unit_id=team_uuid
    ) == (None, None)


def test_promote_concept_covers_axiom_conflict_team_domain_and_rank_guards() -> None:
    from dataclasses import replace

    from orcia_core.ontology.errors import OntologyConflictError
    from orcia_core.ontology.models import OntologyPromotionProposal, WhatIfImpactReport

    org_units, workspaces = _topology()
    contrib = _u("u-c", "c@orcia.ia", "CONTRIBUTOR", "team-pay", ("CONTRIBUTOR",))
    team_lead = _u("u-tl", "tl@orcia.ia", "TEAM_LEAD", "team-pay", ("TEAM_LEAD",))
    other_tl = _u("u-tl2", "tl2@orcia.ia", "TEAM_LEAD", "team-other", ("TEAM_LEAD",))
    bu_lead = _u("u-bu", "bu@orcia.ia", "BU_LEAD", "bu-fin", ("BU_LEAD",))

    gov = build_seeded_ontology_service()

    # 1. Immutable axiom conflict raises OntologyConflictError (line 331)
    _, prop_conflict = gov.extract_l4_concept(
        contrib,
        concept_key="c-l4-axiom-conflict",
        canonical_term="Terme Conflit",
        run_id="run-c",
        snapshot_id="snap-c",
        definition_text="Def",
        target_promotion_level="3_TEAM",
        target_scope_id="team-pay",
    )
    gov.save_proposal(
        replace(
            prop_conflict,
            impact_report=replace(prop_conflict.impact_report, has_immutable_axiom_conflict=True),
        )
    )
    with pytest.raises(OntologyConflictError):
        gov.promote_concept(team_lead, proposal_key=prop_conflict.proposal_key)

    # 2. Target 4_WORKSPACE denied via topology (line 356)
    empty_report = WhatIfImpactReport(
        concept_key="c-l4-axiom-conflict",
        canonical_term="Terme Conflit",
        proposed_change="promote",
        transitively_affected_concepts=(),
        impacted_artifact_templates=(),
        impacted_workflow_uris=(),
        impacted_active_run_ids=(),
    )
    gov.save_proposal(
        OntologyPromotionProposal(
            id="p-ws-id",
            proposal_key="prop-ws-target",
            concept_key="c-l4-axiom-conflict",
            canonical_term="Terme Conflit",
            source_level="4_WORKSPACE",
            target_level="4_WORKSPACE",
            target_scope_id="ws-pay",
            status="PENDING_REVIEW",
            impact_report=empty_report,
            proposed_by_user_id=contrib.id,
        )
    )
    with pytest.raises(ScopeAccessDeniedError):
        gov.promote_concept(
            other_tl,
            proposal_key="prop-ws-target",
            org_units=org_units,
            workspaces=workspaces,
        )

    # 3. Target 2_DOMAIN without topology denied for non-lead (line 374)
    _, prop_dom = gov.extract_l4_concept(
        contrib,
        concept_key="c-l4-dom",
        canonical_term="Terme Domaine",
        run_id="run-d",
        snapshot_id="snap-d",
        definition_text="Def",
        target_promotion_level="2_DOMAIN",
        target_scope_id="bu-fin",
    )
    with pytest.raises(ScopeAccessDeniedError):
        gov.promote_concept(contrib, proposal_key=prop_dom.proposal_key)

    # 4. Target 3_TEAM without topology: role guard + primary_org_unit_id guard + valid pass
    _, prop_team = gov.extract_l4_concept(
        contrib,
        concept_key="c-l4-team",
        canonical_term="Terme Equipe",
        run_id="run-t",
        snapshot_id="snap-t",
        definition_text="Def",
        target_promotion_level="3_TEAM",
        target_scope_id="team-pay",
    )
    with pytest.raises(ScopeAccessDeniedError):
        gov.promote_concept(contrib, proposal_key=prop_team.proposal_key)
    with pytest.raises(ScopeAccessDeniedError):
        gov.promote_concept(other_tl, proposal_key=prop_team.proposal_key)
    promoted_team = gov.promote_concept(team_lead, proposal_key=prop_team.proposal_key)
    assert promoted_team.target_level == "3_TEAM"
    assert promoted_team.status == "APPROVED"

    # 5. Target outranked by source_level raises OntologyConflictError (line 420)
    gov.upsert_concept(
        bu_lead,
        OntologyConceptEntity(
            id="0192c4e0-0000-7000-8000-000000009901",
            concept_key="c-dom-src",
            canonical_term="Source Domaine",
            level="2_DOMAIN",
            scope_id="bu-fin",
            definition_text="Def",
        ),
    )
    gov.save_proposal(
        OntologyPromotionProposal(
            id="p-rank-id",
            proposal_key="prop-rank-inversion",
            concept_key="c-dom-src",
            canonical_term="Source Domaine",
            source_level="2_DOMAIN",
            target_level="3_TEAM",
            target_scope_id="team-pay",
            status="PENDING_REVIEW",
            impact_report=replace(empty_report, concept_key="c-dom-src"),
            proposed_by_user_id=bu_lead.id,
        )
    )
    with pytest.raises(OntologyConflictError):
        gov.promote_concept(team_lead, proposal_key="prop-rank-inversion")
