"""Story 17.3 — Unit & Domain Invariant Tests for IAM Accounts, 6-Role Matrix & SecOps Exceptions.

Covers:
- Closed set of 6 official roles (`PLATFORM_ADMIN`, `SECOPS`, `BU_LEAD`, `TEAM_LEAD`,
  `CONTRIBUTOR`, `OBSERVER`) and `422 ERR_IAM_INVALID_ROLE` on unknown roles.
- `DEFAULT_ROLE_PERMISSION_MATRIX` including `BU_LEAD` and enforcing
  `secret_visibility == "WRITE_ONLY_NEVER_READABLE"` (`AD-21`).  # pragma: allowlist secret
- Anti-lockout deterministic invariant (`422 ERR_ADMIN_LOCKOUT_PREVENTED`) when demoting,
  disabling, or deleting the last `ACTIVE` `PLATFORM_ADMIN`, while allowing `SECOPS` separation
  onto a dedicated RSSI account.
- Granular `resource_kind` (`ALL`, `WORKFLOW`, `AGENT`, `DATASOURCE`, `CONNECTOR`) and
  `effect="INHERITANCE_BLOCK"` on `HierarchicalRbacService`.
- Hexagonal purity (`0` framework/SQL imports in `orcia_core.permissions`).
- FastAPI HTTP contract (`GET/POST/PATCH/DELETE /api/v1/settings/iam/accounts`,
  `GET /api/v1/settings/iam/role-matrix`, `GET/POST/DELETE /api/v1/settings/iam/grants`).
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from orcia_api.main import create_app
from orcia_core.bootstrap._internal.sql_iam_account_helpers import fmt_ts, parse_str_list
from orcia_core.bootstrap._internal.sql_iam_grants import (
    _fmt_ts as fmt_grant_ts,
)
from orcia_core.bootstrap._internal.sql_iam_grants import (
    _parse_conditions,
)
from orcia_core.permissions.errors import (
    AdminLockoutPreventedError,
    DuplicateIamPrincipalError,
    InvalidIamRoleError,
    ResourceNotFoundError,
    ValidationDomainError,
)
from orcia_core.permissions.hierarchical_rbac import (
    DEFAULT_ROLE_PERMISSION_MATRIX,
    HierarchicalRbacService,
    list_native_role_matrix,
)
from orcia_core.permissions.iam_accounts import (
    VALID_GRANT_RESOURCE_KINDS,
    VALID_IAM_ROLES,
    IamAccountsGovernanceService,
    normalize_principal_id,
    validate_grant_resource_kind,
    validate_iam_roles,
)
from orcia_core.permissions.models import UserIdentity

FORBIDDEN_IMPORTS = {"fastapi", "sqlalchemy", "dramatiq", "redis", "litellm", "dbos"}


def test_story_17_3_hexagonal_purity_permissions_package() -> None:
    repo_root = Path(__file__).resolve().parents[2]
    perm_dir = repo_root / "packages" / "orcia-core" / "src" / "orcia_core" / "permissions"
    for py_file in perm_dir.rglob("*.py"):
        tree = ast.parse(py_file.read_text(encoding="utf-8"), filename=str(py_file))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    assert alias.name.split(".")[0] not in FORBIDDEN_IMPORTS
            elif isinstance(node, ast.ImportFrom) and node.module:
                assert node.module.split(".")[0] not in FORBIDDEN_IMPORTS


def test_story_17_3_closed_six_roles_and_matrix_invariants() -> None:
    assert VALID_IAM_ROLES == (
        "PLATFORM_ADMIN",
        "SECOPS",
        "BU_LEAD",
        "TEAM_LEAD",
        "CONTRIBUTOR",
        "OBSERVER",
    )
    assert set(DEFAULT_ROLE_PERMISSION_MATRIX.keys()) == set(VALID_IAM_ROLES)
    assert "BU_LEAD" in DEFAULT_ROLE_PERMISSION_MATRIX

    matrix_list = list_native_role_matrix()
    assert len(matrix_list) == 6
    for entry in matrix_list:
        assert entry.secret_visibility == "WRITE_ONLY_NEVER_READABLE"  # pragma: allowlist secret
        assert set(entry.resource_permissions.keys()) == {
            "workflows",
            "agents",
            "datasources",
            "connectors",
            "org_units",
            "iam_exceptions",
        }

    bu_lead_entry = DEFAULT_ROLE_PERMISSION_MATRIX["BU_LEAD"]
    assert bu_lead_entry.natural_scope == "BU"
    assert "create" in bu_lead_entry.resource_permissions["org_units"]
    assert "execute" in bu_lead_entry.resource_permissions["workflows"]

    secops_entry = DEFAULT_ROLE_PERMISSION_MATRIX["SECOPS"]
    assert "grant" in secops_entry.resource_permissions["iam_exceptions"]

    observer_entry = DEFAULT_ROLE_PERMISSION_MATRIX["OBSERVER"]
    assert observer_entry.native_verbs == ("read",)

    normalized = validate_iam_roles(["SECOPS", "PLATFORM_ADMIN", "SECOPS"])
    assert normalized == ("PLATFORM_ADMIN", "SECOPS")

    with pytest.raises(InvalidIamRoleError) as bad_role:
        validate_iam_roles(["SUPER_ROOT_HACKER"])
    assert bad_role.value.error_code == "ERR_IAM_INVALID_ROLE"
    assert bad_role.value.http_status == 422

    with pytest.raises(ValidationDomainError):
        validate_iam_roles([])


def test_story_17_3_anti_lockout_and_secops_separation_domain_service() -> None:
    svc = IamAccountsGovernanceService()
    initial_accounts = svc.ensure_day0_admin_account(
        email="admin@orcia.fr",
        display_name="Romain Admin",
    )
    assert len(initial_accounts) == 1
    admin_acc = initial_accounts[0]
    assert admin_acc.roles == ("PLATFORM_ADMIN", "SECOPS")
    assert admin_acc.status == "ACTIVE"

    # 1. Attempting to remove PLATFORM_ADMIN from the sole admin -> 422 ERR_ADMIN_LOCKOUT_PREVENTED
    with pytest.raises(AdminLockoutPreventedError) as exc_demote:
        svc.update_account(admin_acc.id, roles=["SECOPS", "CONTRIBUTOR"])
    assert exc_demote.value.error_code == "ERR_ADMIN_LOCKOUT_PREVENTED"
    assert exc_demote.value.http_status == 422

    # 2. Attempting to disable the sole PLATFORM_ADMIN -> 422 ERR_ADMIN_LOCKOUT_PREVENTED
    with pytest.raises(AdminLockoutPreventedError):
        svc.update_account(admin_acc.id, status="DISABLED")

    # 3. Attempting to delete the sole PLATFORM_ADMIN -> 422 ERR_ADMIN_LOCKOUT_PREVENTED
    with pytest.raises(AdminLockoutPreventedError):
        svc.delete_account(admin_acc.id)

    # 4. Creating a dedicated RSSI account + separating SECOPS from initial admin IS allowed
    rssi_acc = svc.create_account(
        principal_id="rssi.secops@orcia.fr",
        display_name="Claire RSSI",
        email="rssi.secops@orcia.fr",
        account_kind="HUMAN",
        auth_source="OIDC_FEDERATED",
        roles=["SECOPS"],
        team_ids=["team-sec"],
        status="ACTIVE",
    )
    assert rssi_acc.roles == ("SECOPS",)

    with pytest.raises(DuplicateIamPrincipalError) as dup_exc:
        svc.create_account(
            principal_id="rssi.secops@orcia.fr",
            display_name="Duplicate",
            roles=["OBSERVER"],
        )
    assert dup_exc.value.http_status == 409

    updated_admin = svc.update_account(admin_acc.id, roles=["PLATFORM_ADMIN"])
    assert updated_admin.roles == ("PLATFORM_ADMIN",)

    # 5. An INVITED SERVICE_PRINCIPAL with PLATFORM_ADMIN does NOT unlock deleting sole ACTIVE admin
    sp_acc = svc.create_account(
        principal_id="sp-rag-indexer",
        display_name="Worker RAG Indexer",
        account_kind="SERVICE_PRINCIPAL",
        auth_source="SERVICE_TOKEN",
        roles=["CONTRIBUTOR"],
        status="ACTIVE",
    )
    assert sp_acc.account_kind == "SERVICE_PRINCIPAL"
    with pytest.raises(AdminLockoutPreventedError):
        svc.delete_account(admin_acc.id)

    # 6. Once a second ACTIVE PLATFORM_ADMIN exists, the first one can be demoted or deleted
    backup_admin = svc.create_account(
        principal_id="backup.admin@orcia.fr",
        display_name="Backup Admin",
        email="backup.admin@orcia.fr",
        roles=["PLATFORM_ADMIN"],
        status="ACTIVE",
    )
    assert backup_admin.status == "ACTIVE"
    deleted_id = svc.delete_account(admin_acc.id)
    assert deleted_id == admin_acc.id


def test_story_17_3_granular_resource_kind_and_inheritance_block_effect() -> None:
    assert VALID_GRANT_RESOURCE_KINDS == (
        "ALL",
        "WORKFLOW",
        "AGENT",
        "DATASOURCE",
        "CONNECTOR",
    )
    secops_actor = UserIdentity(
        id="user-secops-1",
        email="secops@orcia.fr",
        display_name="SecOps Lead",
        auth_mode="OIDC",
        human_profile_archetype="SECOPS",
        platform_role="PLATFORM_ADMIN",
        primary_org_unit_id="org-root",
    )
    svc = HierarchicalRbacService()

    # Parent BU allows read + execute on ALL resources for TEAM_LEAD
    svc.delegate_grant(
        secops_actor,
        subject_type="ROLE",
        subject_id="TEAM_LEAD",
        scope_path="bu-finance",
        verbs=("read", "execute"),
        effect="ALLOW",
        resource_kind="ALL",
    )

    # Confidential workspace isolates inheritance via effect="INHERITANCE_BLOCK"
    isolated = svc.delegate_grant(
        secops_actor,
        subject_type="ROLE",
        subject_id="TEAM_LEAD",
        scope_path="bu-finance/ws-c3",
        verbs=("read",),
        effect="INHERITANCE_BLOCK",
        resource_kind="ALL",
    )
    assert isolated[0].inheritance_block is True
    assert isolated[0].effect == "INHERITANCE_BLOCK"

    verbs_on_c3 = svc.resolve_effective_verbs(
        subject_id="u-lead",
        roles=("TEAM_LEAD",),
        scope_path="bu-finance/ws-c3",
    )
    assert verbs_on_c3 == set()

    # Granular allow ONLY on WORKFLOW inside ws-c3
    svc.delegate_grant(
        secops_actor,
        subject_type="ROLE",
        subject_id="TEAM_LEAD",
        scope_path="bu-finance/ws-c3",
        verbs=("read", "execute"),
        effect="ALLOW",
        resource_kind="WORKFLOW",
    )
    assert svc.resolve_effective_verbs(
        subject_id="u-lead",
        roles=("TEAM_LEAD",),
        scope_path="bu-finance/ws-c3",
        context={"resource_kind": "WORKFLOW"},
    ) == {"read", "execute"}
    assert (
        svc.resolve_effective_verbs(
            subject_id="u-lead",
            roles=("TEAM_LEAD",),
            scope_path="bu-finance/ws-c3",
            context={"resource_kind": "DATASOURCE"},
        )
        == set()
    )


def test_story_17_3_http_endpoints_in_memory_fallback_and_observer_guard(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("ORCIA_DISABLE_PG_BOOTSTRAP_SYNC", "1")
    app = create_app()
    client = TestClient(app)

    # 1. GET /api/v1/settings/iam/role-matrix
    matrix_resp = client.get("/api/v1/settings/iam/role-matrix")
    assert matrix_resp.status_code == 200
    matrix_json = matrix_resp.json()
    expected_policy = "WRITE_ONLY_NEVER_READABLE"  # pragma: allowlist secret
    assert matrix_json["secret_visibility_policy"] == expected_policy
    assert [r["role"] for r in matrix_json["roles"]] == list(VALID_IAM_ROLES)

    # 2. GET /api/v1/settings/iam/accounts auto-seeds Day-0 admin with PLATFORM_ADMIN + SECOPS
    list_resp = client.get("/api/v1/settings/iam/accounts")
    assert list_resp.status_code == 200
    accounts = list_resp.json()["accounts"]
    assert len(accounts) >= 1
    day0 = accounts[0]
    assert "PLATFORM_ADMIN" in day0["roles"]
    assert "SECOPS" in day0["roles"]

    # 3. Anti-lockout over HTTP returns 422 ERR_ADMIN_LOCKOUT_PREVENTED
    lockout_resp = client.delete(f"/api/v1/settings/iam/accounts/{day0['id']}")
    assert lockout_resp.status_code == 422
    assert lockout_resp.json()["error_code"] == "ERR_ADMIN_LOCKOUT_PREVENTED"

    # 4. Observer guard returns 403 ERR_OBSERVER_MODE_READ_ONLY
    obs_resp = client.post(
        "/api/v1/settings/iam/accounts",
        headers={"X-Orcia-Access-Mode": "READ_ONLY_OBSERVER"},
        json={
            "principal_id": "sp-blocked",
            "display_name": "Blocked SP",
            "account_kind": "SERVICE_PRINCIPAL",
            "auth_source": "SERVICE_TOKEN",
            "roles": ["CONTRIBUTOR"],
        },
    )
    assert obs_resp.status_code == 403
    assert obs_resp.json()["error_code"] == "ERR_OBSERVER_MODE_READ_ONLY"

    # 5. Granular grant creation + listing + deletion
    grant_post = client.post(
        "/api/v1/settings/iam/grants",
        json={
            "actor_persona": "karim",
            "subject_type": "ROLE",
            "subject_id": "BU_LEAD",
            "scope_path": "bu-ds3c/ws-confidentiel",
            "verbs": ["read"],
            "effect": "INHERITANCE_BLOCK",
            "resource_kind": "DATASOURCE",
        },
    )
    assert grant_post.status_code == 200
    created_grant = grant_post.json()[0]
    assert created_grant["resource_kind"] == "DATASOURCE"
    assert created_grant["effect"] == "INHERITANCE_BLOCK"
    assert created_grant["inheritance_block"] is True

    grants_list = client.get("/api/v1/settings/iam/grants")
    assert grants_list.status_code == 200
    assert any(g["id"] == created_grant["id"] for g in grants_list.json())

    del_grant = client.delete(f"/api/v1/settings/iam/grants/{created_grant['id']}")
    assert del_grant.status_code == 200


def test_story_17_3_helpers_and_validation_edge_cases() -> None:
    assert validate_grant_resource_kind(None) == "ALL"
    assert validate_grant_resource_kind("  agent ") == "AGENT"
    with pytest.raises(ValidationDomainError):
        validate_grant_resource_kind("SECRET_VAULT")

    assert (
        normalize_principal_id(
            None, email="Alice@Orcia.fr", display_name="Alice", account_kind="HUMAN"
        )
        == "alice@orcia.fr"
    )
    assert (
        normalize_principal_id(
            None, email=None, display_name="Connector Sync 01", account_kind="SERVICE_PRINCIPAL"
        )
        == "sp-connector-sync-01"
    )
    with pytest.raises(ValidationDomainError):
        normalize_principal_id("", email="", display_name="!!!", account_kind="HUMAN")

    svc = IamAccountsGovernanceService()
    seeded_default = svc.ensure_day0_admin_account()
    assert seeded_default[0].principal_id == "admin@orcia.local"
    replaced = svc.ensure_day0_admin_account(email="cto@orcia.fr", display_name="CTO")
    assert [a.principal_id for a in replaced] == ["cto@orcia.fr"]
    assert [a.principal_id for a in svc.ensure_day0_admin_account(email="cto@orcia.fr")] == [
        "cto@orcia.fr"
    ]
    assert [a.principal_id for a in svc.ensure_day0_admin_account()] == ["cto@orcia.fr"]

    with pytest.raises(ValidationDomainError):
        svc.create_account(display_name="   ", roles=["OBSERVER"])
    with pytest.raises(ResourceNotFoundError):
        svc.update_account("missing-id", display_name="X")
    with pytest.raises(ValidationDomainError):
        svc.update_account(replaced[0].id, display_name="   ")
    renamed = svc.update_account(
        replaced[0].id, display_name="CTO Principal", email="cto2@orcia.fr", email_provided=True
    )
    assert renamed.display_name == "CTO Principal"
    assert renamed.email == "cto2@orcia.fr"
    with pytest.raises(ResourceNotFoundError):
        svc.delete_account("missing-id")

    assert parse_str_list('["PLATFORM_ADMIN", "SECOPS"]') == ["PLATFORM_ADMIN", "SECOPS"]
    assert parse_str_list("{not-json") == []
    assert parse_str_list(42) == []
    assert fmt_ts("2026-11-11T00:00:00Z") == "2026-11-11T00:00:00Z"
    assert fmt_grant_ts("2026-11-11T00:00:00Z") == "2026-11-11T00:00:00Z"
    assert _parse_conditions('{"env": "prod"}') == {"env": "prod"}
    assert _parse_conditions("{bad-json") == {}
    assert _parse_conditions(None) == {}


def test_story_17_3_secops_delegation_authorized_via_iam_roles() -> None:
    svc = HierarchicalRbacService()

    secops_user = UserIdentity(
        id="user-contributor-secops",
        email="auditor@orcia.fr",
        display_name="Auditeur SecOps",
        auth_mode="LOCAL",
        human_profile_archetype="CONTRIBUTOR",
        platform_role="CONTRIBUTOR",
        primary_org_unit_id="org-root",
        roles=("CONTRIBUTOR", "SECOPS"),
    )

    grants = svc.delegate_grant(
        secops_user,
        subject_type="USER",
        subject_id="target-user-01",
        scope_path="bu-finance/ws-confidential",
        verbs=("read", "execute"),
        effect="ALLOW",
        resource_kind="DATASOURCE",
    )
    assert len(grants) == 2
    assert all(g.resource_kind == "DATASOURCE" for g in grants)

    admin_secops = UserIdentity(
        id="user-admin-secops",
        email="admin.secops@orcia.fr",
        display_name="Admin SecOps",
        auth_mode="LOCAL",
        human_profile_archetype="PLATFORM_ADMIN",
        platform_role="PLATFORM_ADMIN",
        primary_org_unit_id="org-root",
        roles=("PLATFORM_ADMIN", "SECOPS"),
    )
    grants_admin = svc.delegate_grant(
        admin_secops,
        subject_type="ROLE",
        subject_id="TEAM_LEAD",
        scope_path="bu-finance/ws-confidential",
        verbs=("read",),
        effect="INHERITANCE_BLOCK",
        resource_kind="WORKFLOW",
    )
    assert len(grants_admin) == 1
    assert grants_admin[0].effect == "INHERITANCE_BLOCK"
    assert grants_admin[0].resource_kind == "WORKFLOW"
