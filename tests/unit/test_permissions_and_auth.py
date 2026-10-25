"""Layer 1 Unit & Property-Based Tests for Story 1.2: Auth, OrgUnits, Workspaces & 5 Permissions."""

from __future__ import annotations

import ast
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from hypothesis import given, settings
from hypothesis import strategies as st

from orcia_api.main import create_app
from orcia_core.domain.exceptions import (
    InvalidCredentialsError,
    ObserverModeReadOnlyError,
    ReadSourceDeniedError,
    ResourceNotFoundError,
    RevokedTokenError,
    ScopeAccessDeniedError,
    ValidationDomainError,
)
from orcia_core.permissions import (
    DEFAULT_TOTP_SECRET_KARIM,
    Argon2idPasswordHasher,
    InMemoryRevocationStore,
    JwtSessionManager,
    KeyValueRevocationStore,
    PassthroughVaultCipher,
    TotpManager,
    build_default_auth_and_org_service,
)

FORBIDDEN_IMPORTS = {"fastapi", "sqlalchemy", "dramatiq", "redis", "litellm"}


def test_hexagonal_purity_permissions_package() -> None:
    """Enforce AD-1: `packages/orcia-core/src/orcia_core/permissions` has 0 framework imports."""
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


def test_argon2id_totp_jwt_and_aes256gcm_crypto() -> None:
    """Verify Argon2id hashing, RFC 6238 TOTP, JWT 15m TTL, and AES-256-GCM vault encryption."""
    hasher = Argon2idPasswordHasher(time_cost=1, memory_cost=8192, parallelism=1)
    with pytest.raises(ValidationDomainError):
        hasher.hash_password("   ")

    hashed = hasher.hash_password("StrongSecret!2026")
    assert hashed.startswith("$argon2id$")
    assert hasher.verify_password(hashed, "StrongSecret!2026") is True
    assert hasher.verify_password(hashed, "WrongPassword") is False
    assert hasher.verify_password("", "StrongSecret!2026") is False
    assert hasher.verify_password("not-a-valid-hash", "StrongSecret!2026") is False

    # TOTP RFC 6238
    secret = TotpManager.generate_secret()
    assert len(secret) >= 16
    code = TotpManager.generate_code(secret, timestamp=1700000000)
    assert len(code) == 6 and code.isdigit()
    assert TotpManager.verify_code(secret, code, timestamp=1700000000) is True
    assert TotpManager.verify_code(secret, code, timestamp=1700000030) is True
    wrong_code = "999999" if code == "000000" else "000000"
    assert not TotpManager.verify_code(secret, wrong_code, timestamp=1700000000, valid_window=0)
    assert TotpManager.verify_code(secret, "abc", timestamp=1700000000) is False
    with pytest.raises(ValidationDomainError):
        TotpManager.generate_code("   ")
    with pytest.raises(ValidationDomainError):
        TotpManager.generate_code("!!!invalid-base32!!!")

    # AES-256-GCM PassthroughVaultCipher
    with pytest.raises(ValueError, match="at least 16 bytes"):
        PassthroughVaultCipher("short")

    cipher = PassthroughVaultCipher(b"0123456789abcdef0123456789abcdef")
    with pytest.raises(ValidationDomainError):
        cipher.encrypt("", "secret")

    ct_b64, nonce_b64 = cipher.encrypt(
        "user-1",
        "ghp_super_secret_pat_token",
        connector_scheme="git",
        target_host="gitlab.entreprise.io",
    )
    decrypted = cipher.decrypt(
        "user-1",
        ct_b64,
        nonce_b64,
        connector_scheme="git",
        target_host="gitlab.entreprise.io",
    )
    assert decrypted == "ghp_super_secret_pat_token"

    # Cross-user or tampered ciphertext must fail GCM authentication
    with pytest.raises(ValidationDomainError):
        cipher.decrypt(
            "user-2",
            ct_b64,
            nonce_b64,
            connector_scheme="git",
            target_host="gitlab.entreprise.io",
        )
    with pytest.raises(ValidationDomainError):
        cipher.decrypt("user-1", "!!!bad-b64!!!", nonce_b64)
    with pytest.raises(ValidationDomainError):
        cipher.decrypt("user-1", "YWJj", "YWJj")

    # JWT Session Manager
    with pytest.raises(ValueError, match="at least 16 bytes"):
        JwtSessionManager("short-key")
    jwt_mgr = JwtSessionManager("0123456789abcdef0123456789abcdef")
    pair = jwt_mgr.issue_token_pair(
        user_id="u-1",
        email="u1@orcia.io",
        role="TEAM_LEAD",
        org_unit_id="org-1",
        archetype="TECH_LEAD",
        auth_mode="LOCAL",
        now_ts=1700000000,
    )
    claims = jwt_mgr.verify_token(pair.access_token, expected_type="access", now_ts=1700000100)
    assert claims.sub == "u-1"
    assert claims.jti == pair.access_jti

    with pytest.raises(RevokedTokenError):
        jwt_mgr.verify_token(pair.access_token, expected_type="access", now_ts=1700001000)
    with pytest.raises(InvalidCredentialsError):
        jwt_mgr.verify_token(pair.access_token, expected_type="refresh", now_ts=1700000100)
    with pytest.raises(InvalidCredentialsError):
        jwt_mgr.verify_token("not.a.jwt.token", expected_type="access")
    with pytest.raises(InvalidCredentialsError):
        jwt_mgr.verify_token("bad-token", expected_type="access")
    with pytest.raises(InvalidCredentialsError):
        jwt_mgr.verify_token("éàù.nonascii.sig", expected_type="access")
    with pytest.raises(InvalidCredentialsError):
        jwt_mgr.verify_token(pair.access_token + "tampered", expected_type="access")


@given(
    secret_text=st.text(min_size=1, max_size=120).filter(lambda s: bool(s.strip())),
    user_suffix=st.integers(min_value=1, max_value=9999),
)
@settings(max_examples=15, deadline=None)
def test_property_aes256gcm_roundtrip_and_user_isolation(
    secret_text: str, user_suffix: int
) -> None:
    """Property test: AES-256-GCM roundtrips for owner user and rejects any other user."""
    cipher = PassthroughVaultCipher("property-test-master-key-32-bytes!!")
    owner_id = f"user-{user_suffix}"
    other_id = f"user-{user_suffix + 1}"
    ct_b64, nonce_b64 = cipher.encrypt(owner_id, secret_text)
    assert cipher.decrypt(owner_id, ct_b64, nonce_b64) == secret_text
    with pytest.raises(ValidationDomainError):
        cipher.decrypt(other_id, ct_b64, nonce_b64)


def test_matrix_permission_evaluator_rollup_isolation_and_5_permissions() -> None:
    """Verify OrgUnit hierarchy, upward Roll-up, CONFIDENTIAL_RESTRICTED, and 5 permissions."""
    svc = build_default_auth_and_org_service()
    ev = svc.evaluator

    karim = svc.resolve_user(persona_key="karim")
    claire = svc.resolve_user(persona_key="claire")
    marc = svc.resolve_user(persona_key="marc")
    nadia = svc.resolve_user(persona_key="nadia")
    partenaire = svc.resolve_user(persona_key="partenaire")

    # 1. Marc (TEAM_LEAD on subteam-checkout-squad) sees all 3 workspaces of his team
    marc_ws = ev.resolve_accessible_workspaces(marc)
    assert len(marc_ws) == 3
    ws1_datasources = marc_ws[0].workspace.datasources
    assert len([d for d in ws1_datasources if d.scheme == "git"]) == 3
    assert len([d for d in ws1_datasources if d.scheme == "jira"]) == 2
    assert len([d for d in ws1_datasources if d.scheme == "confluence"]) == 2
    assert ev.compute_finops_rollup_usd(marc) == 539.75

    # 2. Claire (BU_DIRECTOR on parent BU) gets upward Roll-up in READ_ONLY_OBSERVER on WS 1 & 2,
    #    but WS 3 (CONFIDENTIAL_RESTRICTED) is strictly excluded!
    claire_ws = ev.resolve_accessible_workspaces(claire)
    assert [w.workspace.slug for w in claire_ws] == [
        "ws-solution-paiement",
        "ws-solution-fidelite",
    ]
    assert all(w.access_mode == "READ_ONLY_OBSERVER" for w in claire_ws)
    assert all(w.access_origin == "ROLLUP_PARENT" for w in claire_ws)
    assert ev.compute_finops_rollup_usd(claire, org_unit_id=claire.primary_org_unit_id) == 229.75

    # Claire cannot mutate WS 1 (READ_ONLY_OBSERVER -> 403 ERR_OBSERVER_MODE_READ_ONLY)
    with pytest.raises(ObserverModeReadOnlyError):
        ev.enforce_scope_mutation_guard(claire, "0192c4e0-0000-7000-8000-000000000201")

    # 3. Partner team invited onto Workspace 1 sees ONLY Workspace 1, zero visibility on WS 2 or 3
    partner_ws = ev.resolve_accessible_workspaces(partenaire)
    assert [w.workspace.slug for w in partner_ws] == ["ws-solution-paiement"]
    assert partner_ws[0].access_origin == "PARTNER_INVITE"
    assert ev.compute_finops_rollup_usd(partenaire) == 0.0
    with pytest.raises(ScopeAccessDeniedError):
        ev.enforce_scope_mutation_guard(partenaire, "0192c4e0-0000-7000-8000-000000000202")
    with pytest.raises(ResourceNotFoundError):
        ev.enforce_scope_mutation_guard(marc, "non-existent-ws")

    # 4. Downward inheritance of 5 permissions & Black-Box protection (READ_SOURCE=False)
    eff_blackbox, secret_none = ev.evaluate_catalog_resource(
        marc, "res-blackbox-security-agent", require_read_source=False
    )
    assert eff_blackbox.can_discover is True
    assert eff_blackbox.can_execute is True
    assert eff_blackbox.can_read_source is False
    assert eff_blackbox.source_masked is True
    assert eff_blackbox.granted_permissions == ("DISCOVER", "EXECUTE")
    assert secret_none is None

    with pytest.raises(ReadSourceDeniedError) as exc_info:
        ev.evaluate_catalog_resource(marc, "res-blackbox-security-agent", require_read_source=True)
    assert exc_info.value.error_code == "ERR_READ_SOURCE_DENIED"

    # Open skill on Workspace 1 allows READ_SOURCE for Marc and Partenaire on Workspace 1,
    # but is denied when workspace_id is omitted or set to Workspace 2 (...0202)
    eff_open, secret_open = ev.evaluate_catalog_resource(
        marc,
        "res-open-checkout-skill",
        workspace_id="0192c4e0-0000-7000-8000-000000000201",
        require_read_source=True,
    )
    assert eff_open.source_masked is False
    assert "OPEN_SKILL_SOURCE" in (secret_open or "")

    eff_partner_open, secret_partner_open = ev.evaluate_catalog_resource(
        partenaire,
        "res-open-checkout-skill",
        workspace_id="0192c4e0-0000-7000-8000-000000000201",
        require_read_source=True,
    )
    assert eff_partner_open.source_masked is False
    assert "OPEN_SKILL_SOURCE" in (secret_partner_open or "")

    with pytest.raises(ScopeAccessDeniedError):
        ev.evaluate_catalog_resource(partenaire, "res-open-checkout-skill")
    with pytest.raises(ScopeAccessDeniedError):
        ev.evaluate_catalog_resource(
            partenaire,
            "res-open-checkout-skill",
            workspace_id="0192c4e0-0000-7000-8000-000000000202",
        )
    with pytest.raises(ScopeAccessDeniedError):
        ev.evaluate_catalog_resource(
            marc,
            "res-open-checkout-skill",
            workspace_id="0192c4e0-0000-7000-8000-000000000202",
        )

    # Partner cannot discover parent team's SHARED_TEAM resource
    with pytest.raises(ScopeAccessDeniedError):
        ev.evaluate_catalog_resource(partenaire, "res-blackbox-security-agent")
    with pytest.raises(ResourceNotFoundError):
        ev.evaluate_catalog_resource(marc, "unknown-resource")

    # 5. Module 7 (Administration) RBAC filtering
    assert ev.evaluate_module_permissions(karim)["admin"] is True
    assert ev.evaluate_module_permissions(claire)["admin"] is True
    assert ev.evaluate_module_permissions(marc)["admin"] is True
    assert ev.evaluate_module_permissions(nadia)["admin"] is False
    with pytest.raises(ScopeAccessDeniedError):
        ev.enforce_module_access(nadia, "admin")


def test_fastapi_auth_workspaces_and_catalog_endpoints() -> None:
    """Verify /api/v1/auth/*, /api/v1/workspaces/*, and /api/v1/catalog/resources/* HTTP routes."""
    app = create_app()
    client = TestClient(app, base_url="https://testserver", raise_server_exceptions=False)

    # 1. Local login with MFA TOTP for Karim
    totp_code = TotpManager.generate_code(DEFAULT_TOTP_SECRET_KARIM)
    login_res = client.post(
        "/api/v1/auth/login/local",
        json={
            "email": "karim.admin@orcia.io",
            "password": "OrciaAdmin!2026",
            "totp_code": totp_code,
        },
    )
    assert login_res.status_code == 200
    assert "orcia_refresh_token" in login_res.cookies
    access_token = login_res.json()["access_token"]

    # Missing or invalid MFA code -> 401 ERR_AUTH_MFA_INVALID
    mfa_err = client.post(
        "/api/v1/auth/login/local",
        json={"email": "karim.admin@orcia.io", "password": "OrciaAdmin!2026"},
    )
    assert mfa_err.status_code == 401
    assert mfa_err.json()["error_code"] == "ERR_AUTH_MFA_INVALID"

    wrong_code = next(
        cand
        for cand in ("000000", "111111", "222222", "333333", "444444")
        if not TotpManager.verify_code(DEFAULT_TOTP_SECRET_KARIM, cand, valid_window=1)
    )
    mfa_wrong = client.post(
        "/api/v1/auth/login/local",
        json={
            "email": "karim.admin@orcia.io",
            "password": "OrciaAdmin!2026",
            "totp_code": wrong_code,
        },
    )
    assert mfa_wrong.status_code == 401
    assert mfa_wrong.json()["error_code"] == "ERR_AUTH_MFA_INVALID"

    # Wrong password or unknown user -> 401 ERR_AUTH_INVALID_CREDENTIALS
    bad_pw = client.post(
        "/api/v1/auth/login/local",
        json={"email": "marc.lead@orcia.io", "password": "WrongPassword"},
    )
    assert bad_pw.status_code == 401
    assert bad_pw.json()["error_code"] == "ERR_AUTH_INVALID_CREDENTIALS"

    bad_oidc = client.post(
        "/api/v1/auth/login/oidc",
        json={"oidc_subject": "oidc|unknown-subject"},
    )
    assert bad_oidc.status_code == 401

    # 2. OIDC login for Claire (BU_DIRECTOR)
    oidc_res = client.post(
        "/api/v1/auth/login/oidc",
        json={"oidc_subject": "oidc|claire-bu", "email": "claire.bu@orcia.io"},
    )
    assert oidc_res.status_code == 200
    claire_token = oidc_res.json()["access_token"]

    # 3. GET /api/v1/auth/me with Bearer token
    me_res = client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {claire_token}"},
    )
    assert me_res.status_code == 200
    me_data = me_res.json()
    assert me_data["platform_role"] == "BU_DIRECTOR"
    assert len(me_data["workspaces"]) == 2  # WS 3 confidential excluded

    # 4. Refresh session rotates token and revokes previous refresh token
    old_refresh = oidc_res.cookies["orcia_refresh_token"]
    refresh_res = client.post(
        "/api/v1/auth/refresh",
        headers={"X-Refresh-Token": old_refresh},
    )
    assert refresh_res.status_code == 200
    # Replaying the rotated refresh token must fail with 401 ERR_AUTH_TOKEN_REVOKED
    replay_res = client.post(
        "/api/v1/auth/refresh",
        headers={"X-Refresh-Token": old_refresh},
    )
    assert replay_res.status_code == 401
    assert replay_res.json()["error_code"] == "ERR_AUTH_TOKEN_REVOKED"

    # 5. Logout revokes token -> subsequent use of access_token returns 401 ERR_AUTH_TOKEN_REVOKED
    logout_res = client.post(
        "/api/v1/auth/logout",
        headers={"Authorization": f"Bearer {access_token}", "X-Refresh-Token": "invalid.token.val"},
    )
    assert logout_res.status_code == 200
    revoked_me = client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {access_token}"},
    )
    assert revoked_me.status_code == 401
    assert revoked_me.json()["error_code"] == "ERR_AUTH_TOKEN_REVOKED"

    # 6. Passthrough credential storage in AES-256-GCM & owner-only decryption
    pt_res = client.post(
        "/api/v1/auth/passthrough-credentials?persona_key=marc",
        json={
            "connector_scheme": "git",
            "target_host": "gitlab.entreprise.io",
            "plaintext_secret": "glpat-secret-token-123",
        },
    )
    assert pt_res.status_code == 200
    assert pt_res.json()["encrypted_at_rest"] is True
    assert "glpat-secret-token-123" not in pt_res.text

    pt_observer_403 = client.post(
        "/api/v1/auth/passthrough-credentials?persona_key=claire",
        json={
            "connector_scheme": "git",
            "target_host": "gitlab.entreprise.io",
            "plaintext_secret": "glpat-secret-token-123",
        },
    )
    assert pt_observer_403.status_code == 403
    assert pt_observer_403.json()["error_code"] == "ERR_OBSERVER_MODE_READ_ONLY"

    svc = app.state.auth_service
    marc_user = svc.resolve_user(persona_key="marc")
    assert (
        svc.decrypt_passthrough_credential(marc_user, pt_res.json()["id"])
        == "glpat-secret-token-123"
    )
    with pytest.raises(ResourceNotFoundError):
        svc.decrypt_passthrough_credential(marc_user, "unknown-cred-id")
    with pytest.raises(ResourceNotFoundError):
        svc.get_user_by_id("unknown-user-id")
    with pytest.raises(ResourceNotFoundError):
        svc.resolve_user(persona_key="unknown-persona")

    # 7. Workspaces & ScopeAccessGuard mutation check
    ws_list = client.get("/api/v1/workspaces?persona_key=partenaire")
    assert ws_list.status_code == 200
    assert len(ws_list.json()["workspaces"]) == 1

    ws_filtered = client.get(
        "/api/v1/workspaces?persona_key=claire&org_unit_id=0192c4e0-0000-7000-8000-000000000105"
    )
    assert ws_filtered.status_code == 200
    assert ws_filtered.json()["workspaces"] == []

    ws_unknown_org = client.get("/api/v1/workspaces?persona_key=claire&org_unit_id=unknown-org")
    assert ws_unknown_org.status_code == 404

    mut_ok = client.post(
        "/api/v1/workspaces/0192c4e0-0000-7000-8000-000000000201/mutations/check?persona_key=marc"
    )
    assert mut_ok.status_code == 200

    mut_denied = client.post(
        "/api/v1/workspaces/0192c4e0-0000-7000-8000-000000000201/mutations/check?persona_key=claire"
    )
    assert mut_denied.status_code == 403
    assert mut_denied.json()["error_code"] == "ERR_OBSERVER_MODE_READ_ONLY"

    # 8. Catalog resource inspect & black-box source denial
    insp_res = client.get(
        "/api/v1/catalog/resources/res-blackbox-security-agent/inspect?persona_key=marc"
    )
    assert insp_res.status_code == 200
    assert insp_res.json()["source_masked"] is True

    src_denied = client.get(
        "/api/v1/catalog/resources/res-blackbox-security-agent/source?persona_key=marc"
    )
    assert src_denied.status_code == 403
    assert src_denied.json()["error_code"] == "ERR_READ_SOURCE_DENIED"

    src_ok = client.get(
        "/api/v1/catalog/resources/res-open-checkout-skill/source"
        "?persona_key=marc&workspace_id=0192c4e0-0000-7000-8000-000000000201"
    )
    assert src_ok.status_code == 200
    assert "OPEN_SKILL_SOURCE" in src_ok.json()["system_prompt_secret"]

    src_partner_ok = client.get(
        "/api/v1/catalog/resources/res-open-checkout-skill/source"
        "?persona_key=partenaire&workspace_id=0192c4e0-0000-7000-8000-000000000201"
    )
    assert src_partner_ok.status_code == 200
    assert "OPEN_SKILL_SOURCE" in src_partner_ok.json()["system_prompt_secret"]

    for denied_query in (
        "?persona_key=partenaire",
        "?persona_key=partenaire&workspace_id=0192c4e0-0000-7000-8000-000000000202",
        "?persona_key=marc&workspace_id=0192c4e0-0000-7000-8000-000000000202",
    ):
        res_403 = client.get(
            f"/api/v1/catalog/resources/res-open-checkout-skill/inspect{denied_query}"
        )
        assert res_403.status_code == 403
        assert res_403.json()["error_code"] == "ERR_SCOPE_ACCESS_DENIED"

    # 9. Shell navigation RBAC module filtering for Nadia (CONTRIBUTOR)
    shell_nadia = client.get("/api/v1/navigation/shell?persona_key=nadia")
    assert shell_nadia.status_code == 200
    admin_mod = next(m for m in shell_nadia.json()["modules"] if m["key"] == "admin")
    assert admin_mod["enabled"] is False

    shell_nadia_admin_403 = client.get(
        "/api/v1/navigation/shell?persona_key=nadia&require_module=admin"
    )
    assert shell_nadia_admin_403.status_code == 403
    assert shell_nadia_admin_403.json()["error_code"] == "ERR_SCOPE_ACCESS_DENIED"

    # KeyValueRevocationStore & InMemoryRevocationStore unit check
    fake_kv: dict[str, str] = {}

    class _FakeKv:
        def set(self, name: str, value: str, *, ex: int | None = None) -> object:
            fake_kv[name] = value
            return True

        def exists(self, *names: str) -> int:
            return sum(1 for n in names if n in fake_kv)

    kv_store = KeyValueRevocationStore(_FakeKv())
    assert kv_store.is_revoked("jti-1") is False
    kv_store.revoke_jti("jti-1", ttl_seconds=60)
    assert kv_store.is_revoked("jti-1") is True

    mem_store = InMemoryRevocationStore()
    assert mem_store.is_revoked("jti-missing") is False
    mem_store.revoke_jti("jti-mem", ttl_seconds=60)
    assert mem_store.is_revoked("jti-mem") is True
    mem_store.revoke_jti("jti-expired", ttl_seconds=0)
    assert mem_store.is_revoked("jti-expired") is False
