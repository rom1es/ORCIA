"""Story 18.1 — Unit tests for Workspace Sources & GitNexus Codegraph Governance.

Covers:
1. Pure heuristic mapping `infer_source_nature_from_scheme(scheme)`.
2. Strict role authorization (`can_manage_workspace_codegraph(roles)`).
3. Pure health evaluation `evaluate_codegraph_governance_health(...)` for both
   SERVICE_ACCOUNT and WORKSPACE_LEAD_TOKEN modes.
4. In-memory governance operations on `EnterpriseConnectorsGovernanceService`
   (`delete_workspace_datasource`, `request_workspace_datasource_sync`).
5. RFC 9457 Problem Details error contract for `CodegraphWorkspaceLeadRequiredError`.
"""

from __future__ import annotations

import pytest

from orcia_core.permissions import (
    CodegraphWorkspaceLeadRequiredError,
    EnterpriseConnectorsGovernanceService,
    WorkspaceDatasourceRecord,
    can_manage_workspace_codegraph,
    evaluate_codegraph_governance_health,
    infer_source_nature_from_scheme,
)
from orcia_core.permissions.crypto import PassthroughVaultCipher
from orcia_core.permissions.errors import ResourceNotFoundError
from orcia_core.permissions.iam_accounts import IamAccountRecord
from orcia_core.permissions.models import OrgUnitNode


@pytest.mark.parametrize(
    ("scheme", "expected_nature"),
    [
        ("confluence", "DOCUMENT_KB"),
        ("CONFLUENCE", "DOCUMENT_KB"),
        ("jira", "WORK_TRACKER"),
        ("JIRA", "WORK_TRACKER"),
        ("git", "SOURCE_CODE"),
        ("gitlab", "SOURCE_CODE"),
        ("github", "SOURCE_CODE"),
        ("sql", "RELATIONAL_SCHEMA"),
        ("postgres", "RELATIONAL_SCHEMA"),
        ("postgresql", "RELATIONAL_SCHEMA"),
        ("custom_doc", "DOCUMENT_KB"),
        ("", "DOCUMENT_KB"),
    ],
)
def test_infer_source_nature_from_scheme(scheme: str, expected_nature: str) -> None:
    assert infer_source_nature_from_scheme(scheme) == expected_nature


@pytest.mark.parametrize(
    ("roles", "expected_allowed"),
    [
        (["TEAM_LEAD"], True),
        (["BU_LEAD"], True),
        (["PLATFORM_ADMIN"], True),
        (["SECOPS"], True),
        (["CONTRIBUTOR", "TEAM_LEAD"], True),
        (["CONTRIBUTOR"], False),
        (["OBSERVER"], False),
        (["READ_ONLY_OBSERVER"], False),
        ([], False),
    ],
)
def test_can_manage_workspace_codegraph_rbac(roles: list[str], expected_allowed: bool) -> None:
    assert can_manage_workspace_codegraph(roles) is expected_allowed


def test_evaluate_codegraph_governance_health_disabled() -> None:
    status, reason = evaluate_codegraph_governance_health(
        codegraph_enabled=False,
        codegraph_auth_mode="SERVICE_ACCOUNT",
    )
    assert status == "DISABLED"
    assert reason is None


def test_evaluate_codegraph_governance_health_service_account() -> None:
    status, reason = evaluate_codegraph_governance_health(
        codegraph_enabled=True,
        codegraph_auth_mode="SERVICE_ACCOUNT",
    )
    assert status == "READY"
    assert reason is None


def test_evaluate_codegraph_governance_health_lead_token() -> None:
    # 1. Missing owner
    status_no_owner, reason_no_owner = evaluate_codegraph_governance_health(
        codegraph_enabled=True,
        codegraph_auth_mode="WORKSPACE_LEAD_TOKEN",
        codegraph_owner_user_id=None,
    )
    assert status_no_owner == "PAUSED_REFERENT_RENEWAL_REQUIRED"
    assert reason_no_owner == "REFERENT_USER_REQUIRED"

    # 2. Account disabled
    disabled_account = IamAccountRecord(
        id="acc-lead-1",
        principal_id="lead@corp.local",
        display_name="Lead",
        email="lead@corp.local",
        account_kind="HUMAN",
        auth_source="OIDC_FEDERATED",
        status="DISABLED",
        roles=("TEAM_LEAD",),
    )
    status_disabled, reason_disabled = evaluate_codegraph_governance_health(
        codegraph_enabled=True,
        codegraph_auth_mode="WORKSPACE_LEAD_TOKEN",
        codegraph_owner_user_id="lead@corp.local",
        iam_accounts=[disabled_account],
    )
    assert status_disabled == "PAUSED_REFERENT_RENEWAL_REQUIRED"
    assert reason_disabled == "REFERENT_ACCOUNT_DISABLED"

    # 3. Referent left team
    active_account = IamAccountRecord(
        id="acc-lead-1",
        principal_id="lead@corp.local",
        display_name="Lead",
        email="lead@corp.local",
        account_kind="HUMAN",
        auth_source="OIDC_FEDERATED",
        status="ACTIVE",
        roles=("TEAM_LEAD",),
        team_ids=(),
    )
    team_org_unit = OrgUnitNode(
        id="ou-team-1",
        name="Team Alpha",
        slug="team-alpha",
        unit_type="TEAM",
        member_user_ids=("other_user@corp.local",),
    )
    status_left, reason_left = evaluate_codegraph_governance_health(
        codegraph_enabled=True,
        codegraph_auth_mode="WORKSPACE_LEAD_TOKEN",
        codegraph_owner_user_id="lead@corp.local",
        iam_accounts=[active_account],
        owner_org_unit=team_org_unit,
    )
    assert status_left == "PAUSED_REFERENT_RENEWAL_REQUIRED"
    assert reason_left == "REFERENT_LEFT_TEAM"

    # 4. Token missing
    team_with_lead = OrgUnitNode(
        id="ou-team-1",
        name="Team Alpha",
        slug="team-alpha",
        unit_type="TEAM",
        member_user_ids=("lead@corp.local",),
    )
    status_no_token, reason_no_token = evaluate_codegraph_governance_health(
        codegraph_enabled=True,
        codegraph_auth_mode="WORKSPACE_LEAD_TOKEN",
        codegraph_owner_user_id="lead@corp.local",
        connector_id="conn-git-1",
        iam_accounts=[active_account],
        owner_org_unit=team_with_lead,
        active_token_pairs=set(),
    )
    assert status_no_token == "PAUSED_REFERENT_RENEWAL_REQUIRED"
    assert reason_no_token == "REFERENT_TOKEN_MISSING"

    # 5. All valid -> READY
    status_ready, reason_ready = evaluate_codegraph_governance_health(
        codegraph_enabled=True,
        codegraph_auth_mode="WORKSPACE_LEAD_TOKEN",
        codegraph_owner_user_id="lead@corp.local",
        connector_id="conn-git-1",
        iam_accounts=[active_account],
        owner_org_unit=team_with_lead,
        active_token_pairs={("lead@corp.local", "conn-git-1")},
    )
    assert status_ready == "READY"
    assert reason_ready is None


def test_enterprise_connectors_governance_service_datasource_lifecycle() -> None:
    cipher = PassthroughVaultCipher("test-cipher-master-key-32-chars-long!")
    service = EnterpriseConnectorsGovernanceService(vault_cipher=cipher)

    # Register datasource with Story 18.1 fields
    ds = WorkspaceDatasourceRecord(
        id="ds-test-1",
        workspace_id="ws-18-test",
        alias="Repo Core Microservices",
        scheme="git",
        uri="https://gitlab.internal/core/repo.git",
        source_nature="SOURCE_CODE",
        sync_mode="WEBHOOK_PUSH",
        target_scope="apps/api",
        target_ref="main",
        codegraph_enabled=True,
        codegraph_auth_mode="SERVICE_ACCOUNT",
    )
    registered = service.register_workspace_datasource(ds)
    assert registered.source_nature == "SOURCE_CODE"
    assert registered.sync_mode == "WEBHOOK_PUSH"
    assert registered.target_scope == "apps/api"
    assert registered.target_ref == "main"
    assert registered.codegraph_enabled is True
    assert registered.freshness_status == "PENDING_INITIAL_SYNC"

    # Trigger sync
    synced_ds = service.request_workspace_datasource_sync("ws-18-test", ds.id)
    assert synced_ds is not None
    assert synced_ds.freshness_status == "SYNCED"
    assert synced_ds.last_sync_at_iso is not None
    assert synced_ds.codegraph_status == "READY"

    # Delete datasource
    service.delete_workspace_datasource("ws-18-test", ds.id)
    assert len(service.list_workspace_datasources("ws-18-test")) == 0

    # Deleting non-existent datasource raises ResourceNotFoundError
    with pytest.raises(ResourceNotFoundError):
        service.delete_workspace_datasource("ws-18-test", ds.id)


def test_codegraph_workspace_lead_required_error() -> None:
    err = CodegraphWorkspaceLeadRequiredError(
        detail_override="Only workspace leads can configure codegraph.",
        instance="/api/v1/workspaces/ws-1/datasources/ds-1",
    )
    assert err.http_status == 403
    assert err.error_code == "ERR_CODEGRAPH_WORKSPACE_LEAD_REQUIRED"
    assert err.instance == "/api/v1/workspaces/ws-1/datasources/ds-1"
    assert err.type_uri == "https://orcia.io/problems/codegraph-workspace-lead-required"
    fr_copy = err.localize("fr")
    en_copy = err.localize("en")
    assert "Responsable" in fr_copy.title or "GitNexus" in fr_copy.title
    assert "Workspace Lead" in en_copy.title or "GitNexus" in en_copy.title


def test_evaluate_codegraph_governance_health_indexing_and_enterprise() -> None:
    # 1. SERVICE_ACCOUNT mode with current_status == "INDEXING"
    st1, r1 = evaluate_codegraph_governance_health(
        codegraph_enabled=True,
        codegraph_auth_mode="SERVICE_ACCOUNT",
        current_status="INDEXING",
    )
    assert st1 == "INDEXING"
    assert r1 is None

    # 2. WORKSPACE_LEAD_TOKEN mode with current_status == "INDEXING" and active token
    st2, r2 = evaluate_codegraph_governance_health(
        codegraph_enabled=True,
        codegraph_auth_mode="WORKSPACE_LEAD_TOKEN",
        codegraph_owner_user_id="lead-user-1",
        connector_id="conn-git-1",
        active_token_pairs={("lead-user-1", "conn-git-1")},
        current_status="INDEXING",
    )
    assert st2 == "INDEXING"
    assert r2 is None

    # 3. ENTERPRISE unit_type skips team check
    ent_ou = OrgUnitNode(
        id="ou-ent",
        slug="orcia-ent",
        name="Enterprise",
        unit_type="ENTERPRISE",
        lead_user_id="someone-else",
        member_user_ids=("user-a", "user-b"),
    )
    st3, r3 = evaluate_codegraph_governance_health(
        codegraph_enabled=True,
        codegraph_auth_mode="WORKSPACE_LEAD_TOKEN",
        codegraph_owner_user_id="lead-user-1",
        connector_id="conn-git-1",
        owner_org_unit=ent_ou,
        active_token_pairs={("lead-user-1", "conn-git-1")},
    )
    assert st3 == "READY"
    assert r3 is None
