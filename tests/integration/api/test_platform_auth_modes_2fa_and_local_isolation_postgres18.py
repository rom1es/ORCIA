"""Vertical HTTP -> PostgreSQL 18 tests for Exclusive Auth Policy, 2FA, & Isolation."""

from __future__ import annotations

import os
import subprocess
import sys
from collections.abc import Iterator
from pathlib import Path
from urllib.parse import parse_qs, quote_plus, urlparse

import pytest
import sqlalchemy as sa
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import create_async_engine
from testcontainers.postgres import PostgresContainer

from orcia_core.bootstrap._internal.smtp_otp_delivery import InMemoryOtpEmailSink
from orcia_core.permissions import TotpManager

REPO_ROOT = Path(__file__).resolve().parents[3]
DB_NAME = "orcia_auth_policy_test"
DB_USER = "orcia"
DB_PASSWORD = "orcia_auth_policy_pw"  # pragma: allowlist secret


@pytest.fixture(scope="module")
def database_url() -> Iterator[str]:
    with PostgresContainer(
        "pgvector/pgvector:pg18", username=DB_USER, password=DB_PASSWORD, dbname=DB_NAME
    ) as pg:
        url = (
            f"postgresql+asyncpg://{DB_USER}:{quote_plus(DB_PASSWORD)}"
            f"@127.0.0.1:{pg.get_exposed_port(5432)}/{DB_NAME}"
        )
        env = {
            "PATH": os.environ.get("PATH", "/usr/bin:/bin"),
            "PYTHONPATH": os.environ.get("PYTHONPATH", ""),
            "DATABASE_URL": url,
            "ORCIA_ENV_FILE": str(REPO_ROOT / ".orcia-run" / "does-not-exist.env"),
        }
        alembic_bin = str(Path(sys.executable).with_name("alembic"))
        alembic_cmd = [alembic_bin, "-c", "infra/migrations/alembic.ini"]
        subprocess.run([*alembic_cmd, "upgrade", "head"], cwd=REPO_ROOT, env=env, check=True)
        subprocess.run(
            [*alembic_cmd, "downgrade", "20261114_1706"], cwd=REPO_ROOT, env=env, check=True
        )
        subprocess.run([*alembic_cmd, "upgrade", "head"], cwd=REPO_ROOT, env=env, check=True)
        yield url


def _build_real_runtime_app(
    database_url: str,
    monkeypatch: pytest.MonkeyPatch,
    *,
    sink: InMemoryOtpEmailSink | None = None,
):
    monkeypatch.setenv("DATABASE_URL", database_url)
    monkeypatch.setenv("ORCIA_ENV_FILE", str(REPO_ROOT / ".orcia-run" / "does-not-exist.env"))
    monkeypatch.setenv("ORCIA_USE_CASSETTE_LLM", "true")
    monkeypatch.setenv("ORCIA_JWT_SIGNING_SECRET", "orcia-test-jwt-secret-key-1234")
    monkeypatch.setenv("ORCIA_PASSTHROUGH_MASTER_KEY", "orcia-test-vault-secret-key-1234")
    monkeypatch.setenv("ORCIA_ENABLE_PG_SESSION_MAKER", "1")
    monkeypatch.delenv("ORCIA_DISABLE_PG_BOOTSTRAP_SYNC", raising=False)
    monkeypatch.delenv("ORCIA_SEED_TEST_PERSONAS", raising=False)
    monkeypatch.delenv("ORCIA_E2E_SEED_FIXTURES", raising=False)
    monkeypatch.setenv("ORCIA_FORCE_REAL_RUNTIME", "1")
    monkeypatch.delenv("PYTEST_CURRENT_TEST", raising=False)

    from orcia_api.dependencies.core_and_lifespan import initialize_app_services
    from orcia_api.main import create_app

    app = create_app()
    initialize_app_services(app)
    if sink is not None:
        app.state.otp_email_sink = sink
    return app


@pytest.mark.asyncio
async def test_exclusive_auth_modes_2fa_and_runtime_isolation_postgres18(
    database_url: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    engine = create_async_engine(database_url)
    try:
        async with engine.begin() as conn:
            await conn.execute(sa.text("DELETE FROM auth_login_challenges"))
            await conn.execute(sa.text("DELETE FROM role_permission_grants"))
            await conn.execute(sa.text("DELETE FROM iam_accounts"))
            await conn.execute(sa.text("DELETE FROM enterprise_connectors"))
            await conn.execute(sa.text("DELETE FROM users"))

        sink = InMemoryOtpEmailSink()
        app = _build_real_runtime_app(database_url, monkeypatch, sink=sink)
        # Zero mock personas (e.g. marc) loaded outside pytest demo seed
        assert app.state.auth_service.list_personas() == ()

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            # 1. Create Day-0 Platform Admin in PG18 and verify default public-config (LOCAL / NONE)
            first_res = await client.post(
                "/api/v1/bootstrap/welcome-setup/first-admin",
                json={
                    "display_name": "Claire Admin",
                    "email": "admin@orcia.local",
                    "password": "PasswordAdmin123!",  # pragma: allowlist secret
                },
            )
            assert first_res.status_code == 200, first_res.text
            bearer = {"Authorization": f"Bearer {first_res.json()['access_token']}"}

            pub_res = await client.get("/api/v1/auth/public-config")
            assert pub_res.status_code == 200
            pub = pub_res.json()
            assert pub["auth_mode"] == "LOCAL"
            assert pub["two_factor_mode"] == "NONE"
            initial_epoch = pub["boot_epoch"]

            # Hardcoded Marc persona login does not exist in real runtime
            marc_res = await client.post(
                "/api/v1/auth/login/oidc",
                json={"oidc_subject": "oidc|marc-lead"},
            )
            assert marc_res.status_code in (401, 403, 404)

            # 2. Enabling EMAIL_OTP without active SMTP_MAIL connector is rejected (422)
            no_smtp_res = await client.put(
                "/api/v1/settings/authentication",
                headers=bearer,
                json={"auth_mode": "LOCAL", "two_factor_mode": "EMAIL_OTP"},
            )
            assert no_smtp_res.status_code == 422
            assert no_smtp_res.json()["error_code"] == "ERR_AUTH_SMTP_CONNECTOR_REQUIRED"

            # 3. Register active SMTP_MAIL connector then persist LOCAL + EMAIL_OTP in PG18
            smtp_res = await client.post(
                "/api/v1/settings/connectors",
                headers=bearer,
                json={
                    "connector_kind": "SMTP_MAIL",
                    "name": "SMTP Corporate",
                    "base_url": "smtp://mail.internal:587",
                    "auth_mode": "SERVICE_SECRET",
                    "admin_secret_value": (  # pragma: allowlist secret
                        "mailer@orcia.local:smtp-secret"  # pragma: allowlist secret
                    ),
                    "enabled": True,
                },
            )
            assert smtp_res.status_code == 201, smtp_res.text

            otp_cfg_res = await client.put(
                "/api/v1/settings/authentication",
                headers=bearer,
                json={"auth_mode": "LOCAL", "two_factor_mode": "EMAIL_OTP"},
            )
            assert otp_cfg_res.status_code == 200, otp_cfg_res.text
            assert otp_cfg_res.json()["two_factor_mode"] == "EMAIL_OTP"
            assert otp_cfg_res.json()["smtp_connector_configured"] is True

            async with engine.connect() as conn:
                row = (
                    (
                        await conn.execute(
                            sa.text(
                                "SELECT auth_mode, two_factor_mode FROM platform_auth_settings "
                                "WHERE singleton_key = 'GLOBAL'"
                            )
                        )
                    )
                    .mappings()
                    .first()
                )
                assert row == {"auth_mode": "LOCAL", "two_factor_mode": "EMAIL_OTP"}

            # 4. 2-step EMAIL_OTP login + resend + replay protection in PG18
            step1_email = await client.post(
                "/api/v1/auth/login/local",
                json={
                    "email": "admin@orcia.local",
                    "password": "PasswordAdmin123!",  # pragma: allowlist secret
                },
            )
            assert step1_email.status_code == 200, step1_email.text
            s1 = step1_email.json()
            assert s1["requires_two_factor"] is True
            assert s1["challenge_kind"] == "EMAIL_OTP"
            assert s1["access_token"] == ""
            chal_token = s1["challenge_token"]
            assert len(sink.messages) >= 1
            otp_code = sink.messages[-1].otp_code
            assert len(otp_code) == 6

            verify_res = await client.post(
                "/api/v1/auth/login/verify-2fa",
                json={"challenge_token": chal_token, "code": otp_code},
            )
            assert verify_res.status_code == 200, verify_res.text
            assert verify_res.json()["requires_two_factor"] is False
            assert len(verify_res.json()["access_token"]) > 10

            # Replay rejected + consumed_at stamped in PG18
            replay_res = await client.post(
                "/api/v1/auth/login/verify-2fa",
                json={"challenge_token": chal_token, "code": otp_code},
            )
            assert replay_res.status_code == 401
            assert replay_res.json()["error_code"] == "ERR_AUTH_CHALLENGE_INVALID"
            async with engine.connect() as conn:
                consumed = await conn.scalar(
                    sa.text(
                        "SELECT consumed_at FROM auth_login_challenges "
                        "WHERE challenge_kind = 'EMAIL_OTP' ORDER BY created_at DESC LIMIT 1"
                    )
                )
                assert consumed is not None

            # 5. Switch to LOCAL + TOTP -> first login triggers TOTP_ENROLL, second triggers TOTP
            totp_cfg_res = await client.put(
                "/api/v1/settings/authentication",
                headers=bearer,
                json={"auth_mode": "LOCAL", "two_factor_mode": "TOTP"},
            )
            assert totp_cfg_res.status_code == 200, totp_cfg_res.text

            enroll_step1 = await client.post(
                "/api/v1/auth/login/local",
                json={
                    "email": "admin@orcia.local",
                    "password": "PasswordAdmin123!",  # pragma: allowlist secret
                },
            )
            assert enroll_step1.status_code == 200
            enroll_data = enroll_step1.json()
            assert enroll_data["challenge_kind"] == "TOTP_ENROLL"
            assert enroll_data["totp_manual_key"] is not None
            prov_uri = enroll_data["totp_provisioning_uri"]
            secret_b32 = parse_qs(urlparse(prov_uri).query)["secret"][0]
            totp_code = TotpManager.generate_code(secret_b32)

            enroll_verify = await client.post(
                "/api/v1/auth/login/verify-2fa",
                json={"challenge_token": enroll_data["challenge_token"], "code": totp_code},
            )
            assert enroll_verify.status_code == 200, enroll_verify.text
            assert len(enroll_verify.json()["access_token"]) > 10

            async with engine.connect() as conn:
                totp_enabled = await conn.scalar(
                    sa.text("SELECT totp_enabled FROM users WHERE email = 'admin@orcia.local'")
                )
                assert totp_enabled is True

            second_totp = await client.post(
                "/api/v1/auth/login/local",
                json={
                    "email": "admin@orcia.local",
                    "password": "PasswordAdmin123!",  # pragma: allowlist secret
                },
            )
            assert second_totp.status_code == 200
            assert second_totp.json()["challenge_kind"] == "TOTP"
            assert second_totp.json()["totp_provisioning_uri"] is None

            # 6. Switch to exclusive SSO -> secret hidden in HTTP & encrypted in PG18, local 403
            oidc_canary = "CANARY_OIDC_CLIENT_SECRET_987654"  # pragma: allowlist secret
            sso_cfg = await client.put(
                "/api/v1/settings/authentication",
                headers=bearer,
                json={
                    "auth_mode": "SSO",
                    "two_factor_mode": "NONE",
                    "oidc_issuer_url": "https://idp.example.com/realms/orcia",
                    "oidc_client_id": "orcia-prod",
                    "oidc_client_secret": oidc_canary,
                    "oidc_redirect_uri": "https://orcia.local/login",
                    "sso_button_label": "SSO Corporate",
                },
            )
            assert sso_cfg.status_code == 200, sso_cfg.text
            assert oidc_canary not in sso_cfg.text
            assert sso_cfg.json()["oidc_client_secret_configured"] is True

            async with engine.connect() as conn:
                pg_row = (
                    (
                        await conn.execute(
                            sa.text(
                                "SELECT auth_mode, oidc_client_secret_encrypted "
                                "FROM platform_auth_settings WHERE singleton_key = 'GLOBAL'"
                            )
                        )
                    )
                    .mappings()
                    .first()
                )
                assert pg_row is not None
                assert pg_row["auth_mode"] == "SSO"
                assert pg_row["oidc_client_secret_encrypted"] is not None
                assert oidc_canary not in pg_row["oidc_client_secret_encrypted"]

            blocked_local = await client.post(
                "/api/v1/auth/login/local",
                json={
                    "email": "admin@orcia.local",
                    "password": "PasswordAdmin123!",  # pragma: allowlist secret
                },
            )
            assert blocked_local.status_code == 403
            assert blocked_local.json()["error_code"] == "ERR_LOCAL_AUTH_DISABLED"

        # 7. CLI break-glass `10_reset_auth_mode_local.py` & Day-0 `09_reset_db_first_boot.py`
        cli_env = {
            "PATH": os.environ.get("PATH", "/usr/bin:/bin"),
            "PYTHONPATH": os.environ.get("PYTHONPATH", ""),
            "DATABASE_URL": database_url,
        }
        subprocess.run(
            [
                sys.executable,
                "infra/scripts/maintenance/10_reset_auth_mode_local.py",
                "--database-url",
                database_url,
                "--apply",
            ],
            cwd=REPO_ROOT,
            env=cli_env,
            check=True,
        )
        async with engine.connect() as conn:
            recovered = (
                (
                    await conn.execute(
                        sa.text(
                            "SELECT auth_mode, two_factor_mode FROM platform_auth_settings "
                            "WHERE singleton_key = 'GLOBAL'"
                        )
                    )
                )
                .mappings()
                .first()
            )
            assert recovered == {"auth_mode": "LOCAL", "two_factor_mode": "NONE"}

        subprocess.run(
            [
                sys.executable,
                "infra/scripts/maintenance/09_reset_db_first_boot.py",
                "--database-url",
                database_url,
                "--apply",
            ],
            cwd=REPO_ROOT,
            env=cli_env,
            check=True,
        )
        async with engine.connect() as conn:
            users_left = await conn.scalar(sa.text("SELECT COUNT(*) FROM users"))
            next_epoch = await conn.scalar(
                sa.text(
                    "SELECT boot_epoch::text FROM platform_auth_settings "
                    "WHERE singleton_key = 'GLOBAL'"
                )
            )
            assert users_left == 0
            assert next_epoch is not None and next_epoch != initial_epoch
    finally:
        await engine.dispose()
