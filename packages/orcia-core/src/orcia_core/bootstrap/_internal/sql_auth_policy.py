"""PostgreSQL 18 persistence adapter for singleton Platform Auth Policy."""

from __future__ import annotations

from typing import Any, cast
from uuid import UUID

import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncConnection, AsyncEngine

from orcia_core.bootstrap._internal.sql_enterprise_connectors import (
    ensure_enterprise_connectors_schema,
)
from orcia_core.permissions.auth_policy import (
    PlatformAuthMode,
    PlatformAuthPolicyState,
    PlatformTwoFactorMode,
    validate_platform_auth_policy_update,
)
from orcia_core.permissions.crypto import PassthroughVaultCipher
from orcia_core.permissions.enterprise_connectors_crypto import (
    compute_secret_fingerprint,
    extract_url_host,
    pack_encrypted_secret,
    unpack_encrypted_secret,
)
from orcia_kernel.ids import new_uuid7_str


async def ensure_platform_auth_policy_schema(conn: AsyncConnection) -> None:
    """Idempotently ensure `platform_auth_settings` and `auth_login_challenges` exist."""
    await conn.execute(
        sa.text(
            """
            CREATE TABLE IF NOT EXISTS platform_auth_settings (
                singleton_key VARCHAR(16) PRIMARY KEY CHECK (singleton_key = 'GLOBAL'),
                auth_mode VARCHAR(16) NOT NULL DEFAULT 'LOCAL'
                    CHECK (auth_mode IN ('LOCAL', 'SSO')),
                two_factor_mode VARCHAR(16) NOT NULL DEFAULT 'NONE'
                    CHECK (two_factor_mode IN ('NONE', 'EMAIL_OTP', 'TOTP')),
                oidc_issuer_url VARCHAR(512) NULL,
                oidc_client_id VARCHAR(255) NULL,
                oidc_client_secret_encrypted TEXT NULL,
                oidc_client_secret_fingerprint VARCHAR(32) NULL,
                oidc_scopes VARCHAR(255) NOT NULL DEFAULT 'openid profile email',
                oidc_redirect_uri VARCHAR(512) NULL,
                sso_button_label VARCHAR(160) NULL,
                boot_epoch UUID NOT NULL,
                updated_by VARCHAR(255) NULL,
                updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
            );
            """
        )
    )
    await conn.execute(
        sa.text(
            """
            INSERT INTO platform_auth_settings (
                singleton_key,
                auth_mode,
                two_factor_mode,
                oidc_scopes,
                boot_epoch
            )
            VALUES (
                'GLOBAL',
                'LOCAL',
                'NONE',
                'openid profile email',
                :boot_epoch
            )
            ON CONFLICT (singleton_key) DO NOTHING;
            """
        ),
        {"boot_epoch": UUID(new_uuid7_str())},
    )
    await conn.execute(
        sa.text(
            """
            CREATE TABLE IF NOT EXISTS auth_login_challenges (
                id UUID PRIMARY KEY,
                user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                challenge_token_hash CHAR(64) NOT NULL UNIQUE,
                challenge_kind VARCHAR(16) NOT NULL
                    CHECK (challenge_kind IN ('EMAIL_OTP', 'TOTP', 'TOTP_ENROLL')),
                otp_code_hash CHAR(64) NULL,
                pending_totp_secret_encrypted TEXT NULL,
                masked_destination VARCHAR(255) NULL,
                attempts_count INTEGER NOT NULL DEFAULT 0 CHECK (attempts_count >= 0),
                max_attempts INTEGER NOT NULL DEFAULT 5 CHECK (max_attempts > 0),
                expires_at TIMESTAMPTZ NOT NULL,
                consumed_at TIMESTAMPTZ NULL,
                created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
            );
            """
        )
    )


def _row_to_auth_policy_state(
    row: Any,
    *,
    smtp_connector_name: str | None,
) -> PlatformAuthPolicyState:
    has_secret = bool(row[5])
    return PlatformAuthPolicyState(
        auth_mode=cast(PlatformAuthMode, str(row[1])),
        two_factor_mode=cast(PlatformTwoFactorMode, str(row[2])),
        oidc_issuer_url=str(row[3]) if row[3] else None,
        oidc_client_id=str(row[4]) if row[4] else None,
        oidc_client_secret_configured=has_secret,
        oidc_client_secret_fingerprint=str(row[6]) if (has_secret and row[6]) else None,
        oidc_scopes=str(row[7] or "openid profile email"),
        oidc_redirect_uri=str(row[8]) if row[8] else None,
        sso_button_label=str(row[9]) if row[9] else None,
        smtp_connector_configured=smtp_connector_name is not None,
        smtp_connector_name=smtp_connector_name,
        boot_epoch=str(row[10]),
        updated_by=str(row[11]) if row[11] else None,
        updated_at_iso=row[12].isoformat() if row[12] else "",
    )


async def _find_active_smtp_connector_name(conn: AsyncConnection) -> str | None:
    row = (
        await conn.execute(
            sa.text(
                """
                SELECT name
                FROM enterprise_connectors
                WHERE connector_kind = 'SMTP_MAIL' AND enabled = TRUE
                ORDER BY created_at ASC, name ASC
                LIMIT 1;
                """
            )
        )
    ).fetchone()
    return str(row[0]) if row and row[0] else None


_SELECT_POLICY_SQL = """
SELECT singleton_key, auth_mode, two_factor_mode, oidc_issuer_url, oidc_client_id,
       oidc_client_secret_encrypted, oidc_client_secret_fingerprint, oidc_scopes,
       oidc_redirect_uri, sso_button_label, boot_epoch, updated_by, updated_at
FROM platform_auth_settings
WHERE singleton_key = 'GLOBAL'
"""


async def load_platform_auth_policy_from_postgres18(
    engine: AsyncEngine,
) -> PlatformAuthPolicyState:
    """Load the singleton authentication policy + active `SMTP_MAIL` status from PostgreSQL."""
    async with engine.begin() as conn:
        await ensure_enterprise_connectors_schema(conn)
        await ensure_platform_auth_policy_schema(conn)
        smtp_name = await _find_active_smtp_connector_name(conn)
        row = (await conn.execute(sa.text(f"{_SELECT_POLICY_SQL};"))).fetchone()
        assert row is not None
        return _row_to_auth_policy_state(row, smtp_connector_name=smtp_name)


async def update_platform_auth_policy_on_postgres18(
    engine: AsyncEngine,
    *,
    cipher: PassthroughVaultCipher,
    auth_mode: PlatformAuthMode,
    two_factor_mode: PlatformTwoFactorMode,
    oidc_issuer_url: str | None = None,
    oidc_client_id: str | None = None,
    oidc_client_secret: str | None = None,
    clear_oidc_client_secret: bool = False,
    oidc_scopes: str = "openid profile email",
    oidc_redirect_uri: str | None = None,
    sso_button_label: str | None = None,
    updated_by: str | None = None,
    instance: str | None = None,
) -> PlatformAuthPolicyState:
    """Validate and atomically persist the singleton platform authentication policy."""
    async with engine.begin() as conn:
        await ensure_enterprise_connectors_schema(conn)
        await ensure_platform_auth_policy_schema(conn)
        smtp_name = await _find_active_smtp_connector_name(conn)
        clean_issuer, clean_cid, clean_scopes, clean_redirect, clean_label = (
            validate_platform_auth_policy_update(
                auth_mode=auth_mode,
                two_factor_mode=two_factor_mode,
                oidc_issuer_url=oidc_issuer_url,
                oidc_client_id=oidc_client_id,
                oidc_scopes=oidc_scopes,
                oidc_redirect_uri=oidc_redirect_uri,
                sso_button_label=sso_button_label,
                has_active_smtp_connector=smtp_name is not None,
                instance=instance,
            )
        )
        current = (await conn.execute(sa.text(f"{_SELECT_POLICY_SQL} FOR UPDATE;"))).fetchone()
        assert current is not None
        enc_secret: str | None = current[5]
        secret_fp: str | None = current[6]
        if clear_oidc_client_secret:
            enc_secret = None
            secret_fp = None
        elif oidc_client_secret and oidc_client_secret.strip():
            plain = oidc_client_secret.strip()
            enc_secret = pack_encrypted_secret(
                cipher,
                owner_id="platform_auth:oidc",
                plaintext=plain,
                scheme="https",
                host=extract_url_host(clean_issuer or "oidc.local"),
            )
            secret_fp = compute_secret_fingerprint("platform_auth:oidc", plain)

        updated = (
            await conn.execute(
                sa.text(
                    """
                    UPDATE platform_auth_settings
                    SET auth_mode = :auth_mode,
                        two_factor_mode = :two_factor_mode,
                        oidc_issuer_url = :oidc_issuer_url,
                        oidc_client_id = :oidc_client_id,
                        oidc_client_secret_encrypted = :enc_secret,
                        oidc_client_secret_fingerprint = :secret_fp,
                        oidc_scopes = :oidc_scopes,
                        oidc_redirect_uri = :oidc_redirect_uri,
                        sso_button_label = :sso_button_label,
                        updated_by = :updated_by,
                        updated_at = NOW()
                    WHERE singleton_key = 'GLOBAL'
                    RETURNING singleton_key, auth_mode, two_factor_mode, oidc_issuer_url,
                              oidc_client_id, oidc_client_secret_encrypted,
                              oidc_client_secret_fingerprint, oidc_scopes, oidc_redirect_uri,
                              sso_button_label, boot_epoch, updated_by, updated_at;
                    """
                ),
                {
                    "auth_mode": auth_mode,
                    "two_factor_mode": two_factor_mode,
                    "oidc_issuer_url": clean_issuer,
                    "oidc_client_id": clean_cid,
                    "enc_secret": enc_secret,
                    "secret_fp": secret_fp,
                    "oidc_scopes": clean_scopes,
                    "oidc_redirect_uri": clean_redirect,
                    "sso_button_label": clean_label,
                    "updated_by": updated_by,
                },
            )
        ).fetchone()
        assert updated is not None
        return _row_to_auth_policy_state(updated, smtp_connector_name=smtp_name)


async def load_decrypted_oidc_client_secret(
    engine: AsyncEngine,
    *,
    cipher: PassthroughVaultCipher,
) -> tuple[PlatformAuthPolicyState, str | None]:
    """Load policy and server-side decrypted OIDC client secret (never returned to API clients)."""
    async with engine.begin() as conn:
        await ensure_enterprise_connectors_schema(conn)
        await ensure_platform_auth_policy_schema(conn)
        smtp_name = await _find_active_smtp_connector_name(conn)
        row = (await conn.execute(sa.text(f"{_SELECT_POLICY_SQL};"))).fetchone()
        assert row is not None
        state = _row_to_auth_policy_state(row, smtp_connector_name=smtp_name)
        plain_secret: str | None = None
        if row[5]:
            plain_secret = unpack_encrypted_secret(
                cipher,
                owner_id="platform_auth:oidc",
                packed=str(row[5]),
                scheme="https",
                host=extract_url_host(state.oidc_issuer_url or "oidc.local"),
            )
        return state, plain_secret
