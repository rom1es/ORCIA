"""Unit tests for Exclusive Auth Policy (`LOCAL` vs `SSO`), 2FA helpers, and Runtime Isolation."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from orcia_api.dependencies.core_and_lifespan import should_seed_test_personas_in_memory
from orcia_api.main import create_app
from orcia_api.routers._auth_oidc_helpers import (
    _issue_signed_oidc_state,
    _verify_and_consume_oidc_state,
)
from orcia_core.permissions import (
    DEFAULT_TOTP_SECRET_KARIM,
    InMemoryPlatformAuthPolicyStore,
    PassthroughVaultCipher,
    SmtpConnectorRequiredForEmailOtpError,
    SsoConfigurationIncompleteError,
    TotpManager,
    build_default_auth_and_org_service,
    build_totp_provisioning_uri,
    format_totp_manual_key,
    generate_numeric_otp_code,
    hash_challenge_token,
    hash_otp_code,
    mask_email_address,
    pack_totp_secret_for_user,
    unpack_totp_secret_for_user,
    verify_otp_code_hash,
)
from orcia_core.permissions.errors import ValidationDomainError

REPO_ROOT = Path(__file__).resolve().parents[2]


def test_policy_store_enforces_sso_completeness_and_email_otp_smtp_requirement() -> None:
    cipher = PassthroughVaultCipher(b"u" * 32)
    store = InMemoryPlatformAuthPolicyStore(cipher=cipher)
    initial = store.get_state()
    assert initial.auth_mode == "LOCAL"
    assert initial.two_factor_mode == "NONE"

    with pytest.raises(SsoConfigurationIncompleteError):
        store.update_policy(
            auth_mode="SSO",
            two_factor_mode="NONE",
            oidc_issuer_url="https://idp.example.com",
            oidc_client_id="",
            oidc_redirect_uri="https://orcia.local/login",
        )

    with pytest.raises(SmtpConnectorRequiredForEmailOtpError):
        store.update_policy(
            auth_mode="LOCAL",
            two_factor_mode="EMAIL_OTP",
            has_active_smtp_connector=False,
        )

    updated_otp = store.update_policy(
        auth_mode="LOCAL",
        two_factor_mode="EMAIL_OTP",
        has_active_smtp_connector=True,
        smtp_connector_name="SMTP Principal",
        updated_by="admin@orcia.local",
    )
    assert updated_otp.auth_mode == "LOCAL"
    assert updated_otp.two_factor_mode == "EMAIL_OTP"
    assert updated_otp.smtp_connector_configured is True
    assert updated_otp.smtp_connector_name == "SMTP Principal"

    updated_sso = store.update_policy(
        auth_mode="SSO",
        two_factor_mode="NONE",
        oidc_issuer_url="https://idp.example.com/realms/orcia",
        oidc_client_id="orcia-spa",
        oidc_client_secret="top-secret-oidc-value",  # pragma: allowlist secret
        oidc_redirect_uri="https://orcia.local/login",
        sso_button_label="Connexion SSO Entreprise",
        updated_by="admin@orcia.local",
    )
    assert updated_sso.auth_mode == "SSO"
    assert updated_sso.oidc_client_secret_configured is True
    assert updated_sso.oidc_client_secret_fingerprint is not None
    assert "top-secret-oidc-value" not in (updated_sso.oidc_client_secret_fingerprint or "")


def test_otp_hmac_masking_and_user_bound_totp_crypto_helpers() -> None:
    code = generate_numeric_otp_code(digits=6)
    assert len(code) == 6
    assert code.isdigit()

    chal_id = "0195f000-0000-7000-8000-000000000123"
    digest = hash_otp_code(challenge_id=chal_id, otp_code=code)
    assert verify_otp_code_hash(challenge_id=chal_id, candidate_code=code, expected_hash=digest)
    assert (
        not verify_otp_code_hash(
            challenge_id=chal_id, candidate_code="000000", expected_hash=digest
        )
        or code == "000000"
    )
    assert not verify_otp_code_hash(
        challenge_id="other-challenge", candidate_code=code, expected_hash=digest
    )
    assert not verify_otp_code_hash(
        challenge_id=chal_id, candidate_code="12ab56", expected_hash=digest
    )
    assert len(hash_challenge_token("opaque-tok")) == 64

    assert mask_email_address("claire.admin@orcia.fr") == "c***n@orcia.fr"
    assert mask_email_address("ab@orcia.fr") == "a***@orcia.fr"

    secret = TotpManager.generate_secret()
    formatted = format_totp_manual_key(secret)
    assert " " in formatted
    uri = build_totp_provisioning_uri(secret_b32=secret, account_email="Admin@Orcia.fr")
    assert uri.startswith("otpauth://totp/ORCIA:admin@orcia.fr?secret=")
    assert "&issuer=ORCIA" in uri

    cipher = PassthroughVaultCipher(b"t" * 32)
    packed = pack_totp_secret_for_user(cipher, user_id="user-1", secret_b32=secret)
    assert secret not in packed
    assert unpack_totp_secret_for_user(cipher, user_id="user-1", packed=packed) == secret

    # Binding check prevents moving encrypted TOTP envelope to a different user_id
    with pytest.raises(ValidationDomainError):
        unpack_totp_secret_for_user(cipher, user_id="user-2", packed=packed)


def test_runtime_persona_isolation_and_oidc_state_replay_protection(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from orcia_api.main import create_app

    monkeypatch.setenv("ORCIA_FORCE_REAL_RUNTIME", "1")
    monkeypatch.delenv("ORCIA_E2E_SEED_FIXTURES", raising=False)
    monkeypatch.delenv("ORCIA_SEED_TEST_PERSONAS", raising=False)
    assert should_seed_test_personas_in_memory() is False
    real_app = create_app()
    assert real_app.state.auth_service.list_personas() == ()

    monkeypatch.delenv("ORCIA_FORCE_REAL_RUNTIME", raising=False)
    monkeypatch.setenv("ORCIA_SEED_TEST_PERSONAS", "1")
    assert should_seed_test_personas_in_memory() is True

    clean_env = {
        k: v
        for k, v in os.environ.items()
        if not k.startswith("PYTEST_")
        and k
        not in {
            "ORCIA_E2E_SEED_FIXTURES",
            "ORCIA_SEED_TEST_PERSONAS",
            "ORCIA_FORCE_REAL_RUNTIME",
        }
    }
    proc = subprocess.run(
        [
            sys.executable,
            "-c",
            (
                "import sys; assert 'pytest' not in sys.modules; "
                "from orcia_api.dependencies.core_and_lifespan import "
                "should_seed_test_personas_in_memory; "
                "from orcia_api.main import create_app; "
                "assert should_seed_test_personas_in_memory() is False; "
                "assert create_app().state.auth_service.list_personas() == ()"
            ),
        ],
        cwd=REPO_ROOT,
        env=clean_env,
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr

    svc_clean = build_default_auth_and_org_service(seed_reference_personas=False)
    assert svc_clean.list_personas() == ()

    # Verify OIDC CSRF state signature, tamper rejection, and single-use replay rejection
    state = _issue_signed_oidc_state(svc_clean)
    assert _verify_and_consume_oidc_state(svc_clean, f"{state}tamper") is False
    assert _verify_and_consume_oidc_state(svc_clean, state) is True
    assert _verify_and_consume_oidc_state(svc_clean, state) is False


@pytest.mark.parametrize(
    "script_rel",
    [
        "infra/scripts/maintenance/01_backfill_default_org_tree.py",
        "infra/scripts/maintenance/02_backfill_federated_catalog.py",
        "infra/scripts/maintenance/03_backfill_permission_broker.py",
        "infra/scripts/maintenance/08_seed_uat_dataset.py",
    ],
)
def test_demo_backfill_and_uat_scripts_require_explicit_confirm_flag_on_apply(
    script_rel: str,
) -> None:
    proc = subprocess.run(
        [sys.executable, str(REPO_ROOT / script_rel), "--apply"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode != 0
    combined = f"{proc.stdout}\n{proc.stderr}"
    assert "--confirm-demo-seed" in combined


def test_session_bootstrap_returns_200_when_anonymous_or_cookie_stale_while_refresh_stays_401(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("ORCIA_DISABLE_PG_BOOTSTRAP_SYNC", "1")
    app = create_app()
    client = TestClient(app)

    # 1. Anonymous boot -> HTTP 200 {authenticated: false, session: null} (zero 401 noise)
    anon = client.get("/api/v1/auth/session")
    assert anon.status_code == 200
    assert anon.json()["authenticated"] is False
    assert anon.json()["session"] is None

    # 2. Stale/tampered cookie -> HTTP 200 {authenticated: false, session: null} & clears cookie
    client.cookies.set(
        "orcia_refresh_token",
        "invalid-stale-jwt-cookie",
        path="/api/v1/auth",
    )
    stale = client.get("/api/v1/auth/session")
    assert stale.status_code == 200
    assert stale.json()["authenticated"] is False
    assert stale.json()["session"] is None
    assert "Max-Age=0" in stale.headers.get("set-cookie", "")
    client.cookies.clear()

    # 3. Valid refresh cookie (via local login) -> HTTP 200 {authenticated: true, session: {...}}
    totp_code = TotpManager.generate_code(DEFAULT_TOTP_SECRET_KARIM)
    login = client.post(
        "/api/v1/auth/login/local",
        json={
            "email": "karim.admin@orcia.io",
            "password": "OrciaAdmin!2026",  # pragma: allowlist secret
            "totp_code": totp_code,
        },
    )
    assert login.status_code == 200
    authed = client.get("/api/v1/auth/session")
    assert authed.status_code == 200
    body = authed.json()
    assert body["authenticated"] is True
    assert body["session"]["email"] == "karim.admin@orcia.io"

    # 4. Explicit POST /refresh without cookie keeps strict HTTP 401 ERR_AUTH_INVALID_CREDENTIALS
    clean_client = TestClient(app)
    refresh = clean_client.post("/api/v1/auth/refresh")
    assert refresh.status_code == 401
    assert refresh.json()["error_code"] == "ERR_AUTH_INVALID_CREDENTIALS"
