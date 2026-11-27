"""Story 25.1 Layer 1a unit tests: Personal Workspace isolation, idempotence & Accostage."""

from __future__ import annotations

import pytest

from orcia_core.bootstrap import (
    ACCOSTAGE_SIX_MILESTONES,
    ProgressiveDay0AccostageService,
    build_personal_workspace_name,
)
from orcia_core.permissions import (
    MatrixPermissionEvaluator,
    OrgUnitNode,
    UserIdentity,
    WorkspaceEntity,
    WorkspaceMembershipEntity,
)
from orcia_core.permissions.errors import ScopeAccessDeniedError

ROOT_OU_ID = "0192c4e0-0000-7000-8000-000000000001"
USER_A_ID = "0195f000-0000-7000-8000-0000000000a1"
USER_B_ID = "0195f000-0000-7000-8000-0000000000b2"
WS_PERSONAL_A_ID = "0195f000-0000-7000-8000-000000000901"


def test_build_personal_workspace_name_localized_and_bounded() -> None:
    assert build_personal_workspace_name("Alice Admin", locale="fr") == (
        "Espace personnel — Alice Admin"
    )
    assert build_personal_workspace_name("Alice Admin", locale="en-US") == (
        "Personal Space — Alice Admin"
    )
    assert build_personal_workspace_name("   ", locale="fr") == "Mon espace personnel"
    assert build_personal_workspace_name("   ", locale="en") == "My Personal Space"
    long_name = "A" * 300
    assert len(build_personal_workspace_name(long_name, locale="fr")) == 255


def test_matrix_permission_evaluator_blocks_other_platform_admin_from_personal_workspace() -> None:
    evaluator = MatrixPermissionEvaluator(org_units=(), workspaces=())
    evaluator.upsert_org_unit(
        OrgUnitNode(
            id=ROOT_OU_ID,
            slug="orcia-root",
            name="ORCIA Root Organization",
            unit_type="ENTERPRISE",
            parent_id=None,
        )
    )
    evaluator.upsert_workspace(
        WorkspaceEntity(
            id=WS_PERSONAL_A_ID,
            slug=f"personal-{USER_A_ID}",
            name="Espace personnel — Alice",
            owner_org_unit_id=ROOT_OU_ID,
            visibility_mode="CONFIDENTIAL_RESTRICTED",
            personal_owner_user_id=USER_A_ID,
            ui_visibility_mode="PRIVATE_USER",
        )
    )
    evaluator.upsert_workspace(
        WorkspaceEntity(
            id="0195f000-0000-7000-8000-000000000902",
            slug="team-shared",
            name="Espace Équipe",
            owner_org_unit_id=ROOT_OU_ID,
            visibility_mode="STANDARD",
        )
    )
    # Even if a stale membership existed for Admin B, personal_owner_user_id guard MUST deny B.
    evaluator.upsert_membership(
        WorkspaceMembershipEntity(
            id="0195f000-0000-7000-8000-000000000999",
            workspace_id=WS_PERSONAL_A_ID,
            role="PLATFORM_ADMIN",
            access_mode="CONTRIBUTOR_ACTION_REQUIRED",
            user_id=USER_B_ID,
        )
    )

    user_a = UserIdentity(
        id=USER_A_ID,
        email="alice@orcia.test",
        display_name="Alice",
        auth_mode="LOCAL",
        human_profile_archetype="CONTRIBUTOR",
        platform_role="CONTRIBUTOR",
        primary_org_unit_id=ROOT_OU_ID,
        roles=("CONTRIBUTOR",),
    )
    admin_b = UserIdentity(
        id=USER_B_ID,
        email="bob.admin@orcia.test",
        display_name="Bob Admin",
        auth_mode="LOCAL",
        human_profile_archetype="PLATFORM_ADMIN",
        platform_role="PLATFORM_ADMIN",
        primary_org_unit_id=ROOT_OU_ID,
        roles=("PLATFORM_ADMIN", "SECOPS"),
    )
    observer_a = UserIdentity(
        id=USER_A_ID,
        email="alice@orcia.test",
        display_name="Alice",
        auth_mode="LOCAL",
        human_profile_archetype="OBSERVER",
        platform_role="OBSERVER",
        primary_org_unit_id=ROOT_OU_ID,
        roles=("OBSERVER",),
    )

    access_a = evaluator.resolve_workspace_access(user_a, WS_PERSONAL_A_ID)
    assert access_a is not None
    assert access_a.access_mode == "CONTRIBUTOR_ACTION_REQUIRED"
    assert access_a.workspace.ui_visibility_mode == "PRIVATE_USER"

    access_obs_a = evaluator.resolve_workspace_access(observer_a, WS_PERSONAL_A_ID)
    assert access_obs_a is not None
    assert access_obs_a.access_mode == "READ_ONLY_OBSERVER"

    assert evaluator.resolve_workspace_access(admin_b, WS_PERSONAL_A_ID) is None
    admin_b_ws_ids = {s.workspace.id for s in evaluator.resolve_accessible_workspaces(admin_b)}
    assert WS_PERSONAL_A_ID not in admin_b_ws_ids
    assert "0195f000-0000-7000-8000-000000000902" in admin_b_ws_ids

    with pytest.raises(ScopeAccessDeniedError):
        evaluator.enforce_scope_mutation_guard(
            admin_b,
            WS_PERSONAL_A_ID,
            instance=f"/api/v1/workspaces/{WS_PERSONAL_A_ID}/mutations/check",
        )


def test_progressive_accostage_milestones_exclude_private_user() -> None:
    assert ACCOSTAGE_SIX_MILESTONES[3].key == "first-space"
    assert ACCOSTAGE_SIX_MILESTONES[3].title_fr == "4. Premier Espace d'équipe"
    assert ACCOSTAGE_SIX_MILESTONES[3].title_en == "4. First Team Space"

    svc = ProgressiveDay0AccostageService(orcia_env="local")
    status_with_personal_only = svc.sync_from_pg18_counts(
        users_count=1,
        org_units_count=0,
        workspaces_count=0,
        models_count=0,
        sources_count=0,
        workflows_count=0,
    )
    assert status_with_personal_only.completed_count == 1
    assert "first-space" not in status_with_personal_only.completed_milestone_keys

    status_with_team_space = svc.sync_from_pg18_counts(
        users_count=1,
        org_units_count=1,
        workspaces_count=1,
        models_count=1,
        sources_count=0,
        workflows_count=0,
    )
    assert status_with_team_space.completed_count == 4
    assert "first-space" in status_with_team_space.completed_milestone_keys
