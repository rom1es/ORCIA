"""PostgreSQL 18 persistence adapter for single-use 2FA Login Challenges & TOTP Enrollment."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import cast
from uuid import UUID

import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncEngine

from orcia_core.bootstrap._internal.sql_auth_policy import ensure_platform_auth_policy_schema
from orcia_core.permissions.auth_policy import (
    DEFAULT_LOGIN_CHALLENGE_MAX_ATTEMPTS,
    EMAIL_OTP_TTL_SECONDS,
    LoginChallengeKind,
    LoginSecondFactorChallengeRecord,
    generate_opaque_challenge_token,
    hash_challenge_token,
    hash_otp_code,
)
from orcia_kernel.ids import new_uuid7_str


def _row_to_challenge(row: sa.RowMapping) -> LoginSecondFactorChallengeRecord:
    return LoginSecondFactorChallengeRecord(
        id=str(row["id"]),
        user_id=str(row["user_id"]),
        challenge_kind=cast(LoginChallengeKind, str(row["challenge_kind"])),
        challenge_token_hash=str(row["challenge_token_hash"]).strip(),
        otp_code_hash=str(row["otp_code_hash"]).strip() if row["otp_code_hash"] else None,
        pending_totp_secret_encrypted=(
            str(row["pending_totp_secret_encrypted"])
            if row["pending_totp_secret_encrypted"]
            else None
        ),
        masked_destination=str(row["masked_destination"]) if row["masked_destination"] else None,
        attempts_count=int(row["attempts_count"]),
        max_attempts=int(row["max_attempts"]),
        expires_at=row["expires_at"],
        consumed_at=row["consumed_at"],
    )


async def create_login_second_factor_challenge_on_postgres18(
    engine: AsyncEngine,
    *,
    user_id: str,
    challenge_kind: LoginChallengeKind,
    ttl_seconds: int = EMAIL_OTP_TTL_SECONDS,
    otp_code: str | None = None,
    pending_totp_secret_encrypted: str | None = None,
    masked_destination: str | None = None,
    max_attempts: int = DEFAULT_LOGIN_CHALLENGE_MAX_ATTEMPTS,
) -> tuple[LoginSecondFactorChallengeRecord, str]:
    """Create and persist a single-use step-2 challenge; return `(record, raw_token)`."""
    cid = new_uuid7_str()
    raw_token = generate_opaque_challenge_token()
    token_hash = hash_challenge_token(raw_token)
    otp_digest = hash_otp_code(challenge_id=cid, otp_code=otp_code) if otp_code else None
    expires_at = datetime.now(UTC) + timedelta(seconds=ttl_seconds)

    async with engine.begin() as conn:
        await ensure_platform_auth_policy_schema(conn)
        row = (
            (
                await conn.execute(
                    sa.text(
                        """
                    INSERT INTO auth_login_challenges (
                        id, user_id, challenge_token_hash, challenge_kind, otp_code_hash,
                        pending_totp_secret_encrypted, masked_destination,
                        attempts_count, max_attempts, expires_at
                    )
                    VALUES (
                        :id, :user_id, :token_hash, :kind, :otp_hash,
                        :pending_totp, :masked_dest, 0, :max_attempts, :expires_at
                    )
                    RETURNING id, user_id, challenge_token_hash, challenge_kind, otp_code_hash,
                              pending_totp_secret_encrypted, masked_destination,
                              attempts_count, max_attempts, expires_at, consumed_at;
                    """
                    ),
                    {
                        "id": UUID(cid),
                        "user_id": UUID(user_id),
                        "token_hash": token_hash,
                        "kind": challenge_kind,
                        "otp_hash": otp_digest,
                        "pending_totp": pending_totp_secret_encrypted,
                        "masked_dest": masked_destination,
                        "max_attempts": max_attempts,
                        "expires_at": expires_at,
                    },
                )
            )
            .mappings()
            .first()
        )
        assert row is not None
        return _row_to_challenge(row), raw_token


async def load_login_challenge_by_token_from_postgres18(
    engine: AsyncEngine,
    *,
    challenge_token: str,
) -> LoginSecondFactorChallengeRecord | None:
    """Load a step-2 login challenge by raw challenge token hash."""
    if not challenge_token.strip():
        return None
    token_hash = hash_challenge_token(challenge_token)
    async with engine.begin() as conn:
        await ensure_platform_auth_policy_schema(conn)
        row = (
            (
                await conn.execute(
                    sa.text(
                        """
                    SELECT id, user_id, challenge_token_hash, challenge_kind, otp_code_hash,
                           pending_totp_secret_encrypted, masked_destination,
                           attempts_count, max_attempts, expires_at, consumed_at
                    FROM auth_login_challenges
                    WHERE challenge_token_hash = :token_hash
                    LIMIT 1;
                    """
                    ),
                    {"token_hash": token_hash},
                )
            )
            .mappings()
            .first()
        )
        return _row_to_challenge(row) if row is not None else None


async def increment_challenge_attempts_on_postgres18(
    engine: AsyncEngine,
    *,
    challenge_id: str,
) -> int:
    """Increment `attempts_count` after an invalid 2FA code submission."""
    async with engine.begin() as conn:
        row = (
            await conn.execute(
                sa.text(
                    """
                    UPDATE auth_login_challenges
                    SET attempts_count = attempts_count + 1
                    WHERE id = :id AND consumed_at IS NULL
                    RETURNING attempts_count;
                    """
                ),
                {"id": UUID(challenge_id)},
            )
        ).fetchone()
        return int(row[0]) if row is not None else 0


async def consume_login_challenge_on_postgres18(
    engine: AsyncEngine,
    *,
    challenge_id: str,
) -> bool:
    """Atomically mark a challenge consumed (replay protection)."""
    async with engine.begin() as conn:
        res = await conn.execute(
            sa.text(
                """
                UPDATE auth_login_challenges
                SET consumed_at = NOW()
                WHERE id = :id
                  AND consumed_at IS NULL
                  AND expires_at > NOW()
                  AND attempts_count < max_attempts;
                """
            ),
            {"id": UUID(challenge_id)},
        )
        return bool(res.rowcount and res.rowcount > 0)


async def update_login_challenge_email_otp_on_postgres18(
    engine: AsyncEngine,
    *,
    challenge_id: str,
    new_otp_code: str,
    ttl_seconds: int = EMAIL_OTP_TTL_SECONDS,
) -> LoginSecondFactorChallengeRecord | None:
    """Regenerate email OTP hash & reset attempts on an active unconsumed `EMAIL_OTP` challenge."""
    otp_digest = hash_otp_code(challenge_id=challenge_id, otp_code=new_otp_code)
    expires_at = datetime.now(UTC) + timedelta(seconds=ttl_seconds)
    async with engine.begin() as conn:
        row = (
            (
                await conn.execute(
                    sa.text(
                        """
                    UPDATE auth_login_challenges
                    SET otp_code_hash = :otp_hash,
                        attempts_count = 0,
                        expires_at = :expires_at
                    WHERE id = :id
                      AND challenge_kind = 'EMAIL_OTP'
                      AND consumed_at IS NULL
                    RETURNING id, user_id, challenge_token_hash, challenge_kind, otp_code_hash,
                              pending_totp_secret_encrypted, masked_destination,
                              attempts_count, max_attempts, expires_at, consumed_at;
                    """
                    ),
                    {
                        "id": UUID(challenge_id),
                        "otp_hash": otp_digest,
                        "expires_at": expires_at,
                    },
                )
            )
            .mappings()
            .first()
        )
        return _row_to_challenge(row) if row is not None else None


async def activate_user_totp_secret_on_postgres18(
    engine: AsyncEngine,
    *,
    user_id: str,
    encrypted_totp_secret: str,
) -> None:
    """Persist encrypted TOTP secret and set `totp_enabled = TRUE` on first TOTP verification."""
    async with engine.begin() as conn:
        await conn.execute(
            sa.text(
                """
                UPDATE users
                SET totp_secret_encrypted = :secret_enc,
                    totp_enabled = TRUE
                WHERE id = :uid;
                """
            ),
            {"uid": UUID(user_id), "secret_enc": encrypted_totp_secret},
        )
