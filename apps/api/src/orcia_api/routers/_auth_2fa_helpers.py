"""PostgreSQL 18 2-step 2FA (`EMAIL_OTP` / `TOTP` / `TOTP_ENROLL`) authentication helpers."""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime

from fastapi import Request, Response
from sqlalchemy.ext.asyncio import AsyncEngine

from orcia_api.routers._auth_token_issuer import (
    issue_completed_auth_response,
    user_identity_from_candidate,
)
from orcia_api.schemas.auth_and_org import AuthTokenResponse
from orcia_api.schemas.auth_policy import ResendLoginTwoFactorResponse
from orcia_core.bootstrap import (
    activate_user_totp_secret_on_postgres18,
    consume_login_challenge_on_postgres18,
    create_login_second_factor_challenge_on_postgres18,
    increment_challenge_attempts_on_postgres18,
    load_auth_candidate_by_id_from_postgres18,
    load_local_auth_candidate_from_postgres18,
    load_login_challenge_by_token_from_postgres18,
    send_login_email_otp,
    update_login_challenge_email_otp_on_postgres18,
)
from orcia_core.permissions import (
    EMAIL_OTP_TTL_SECONDS,
    TOTP_CHALLENGE_TTL_SECONDS,
    AuthAndOrganizationService,
    PlatformAuthPolicyState,
    TotpManager,
    UserIdentity,
    build_totp_provisioning_uri,
    format_totp_manual_key,
    generate_numeric_otp_code,
    mask_email_address,
    pack_totp_secret_for_user,
    unpack_totp_secret_for_user,
    verify_otp_code_hash,
)
from orcia_core.permissions.errors import (
    InvalidCredentialsError,
    InvalidMfaCodeError,
    InvalidOrExpiredLoginChallengeError,
)


def _request_locale(request: Request) -> str:
    hdr = request.headers.get("Accept-Language", "fr")
    return "en" if hdr.strip().lower().startswith("en") else "fr"


def _decrypt_or_raw_totp_secret(
    svc: AuthAndOrganizationService,
    user_id: str,
    stored_secret: str,
) -> str:
    if ":" in stored_secret:
        return unpack_totp_secret_for_user(svc.vault_cipher, user_id=user_id, packed=stored_secret)
    return stored_secret


def _two_factor_step_response(
    *,
    user: UserIdentity,
    challenge_token: str,
    challenge_kind: str,
    ttl_seconds: int,
    trace_id: str,
    masked_destination: str | None = None,
    totp_provisioning_uri: str | None = None,
    totp_manual_key: str | None = None,
) -> AuthTokenResponse:
    return AuthTokenResponse(
        access_token="",
        expires_in_seconds=ttl_seconds,
        user_id=user.id,
        email=user.email,
        display_name=user.display_name,
        platform_role=user.platform_role,
        human_profile_archetype=user.human_profile_archetype,
        primary_org_unit_id=user.primary_org_unit_id,
        roles=list(user.roles),
        must_change_password=user.must_change_password,
        requires_two_factor=True,
        challenge_token=challenge_token,
        challenge_kind=challenge_kind,  # type: ignore[arg-type]
        masked_destination=masked_destination,
        totp_provisioning_uri=totp_provisioning_uri,
        totp_manual_key=totp_manual_key,
        trace_id=trace_id,
    )


async def authenticate_pg_local_with_policy(
    *,
    engine: AsyncEngine,
    request: Request,
    response: Response,
    svc: AuthAndOrganizationService,
    policy: PlatformAuthPolicyState,
    email: str,
    password: str,
    totp_code: str | None,
    trace_id: str,
) -> AuthTokenResponse:
    """Verify PG local credentials and execute configured 2FA (`NONE`, `EMAIL_OTP`, `TOTP`)."""
    async with engine.begin() as conn:
        candidate = await load_local_auth_candidate_from_postgres18(conn, email=email)
    if (
        candidate is None
        or not candidate.is_active
        or candidate.iam_status == "DISABLED"
        or not candidate.password_hash_argon2id
    ):
        raise InvalidCredentialsError(instance=str(request.url.path))

    is_valid = await asyncio.to_thread(
        svc.hasher.verify_password,
        candidate.password_hash_argon2id,
        password,
    )
    if not is_valid:
        raise InvalidCredentialsError(instance=str(request.url.path))

    user = user_identity_from_candidate(candidate, auth_mode="LOCAL")
    if policy.two_factor_mode == "NONE":
        return issue_completed_auth_response(
            response=response, request=request, svc=svc, user=user, trace_id=trace_id
        )

    if policy.two_factor_mode == "EMAIL_OTP":
        otp_code = generate_numeric_otp_code(digits=6)
        masked = mask_email_address(user.email)
        _, raw_token = await create_login_second_factor_challenge_on_postgres18(
            engine,
            user_id=user.id,
            challenge_kind="EMAIL_OTP",
            ttl_seconds=EMAIL_OTP_TTL_SECONDS,
            otp_code=otp_code,
            masked_destination=masked,
        )
        await send_login_email_otp(
            engine,
            cipher=svc.vault_cipher,
            recipient_email=user.email,
            otp_code=otp_code,
            locale=_request_locale(request),
            otp_email_sink=getattr(request.app.state, "otp_email_sink", None),
            instance=str(request.url.path),
        )
        return _two_factor_step_response(
            user=user,
            challenge_token=raw_token,
            challenge_kind="EMAIL_OTP",
            ttl_seconds=EMAIL_OTP_TTL_SECONDS,
            masked_destination=masked,
            trace_id=trace_id,
        )

    if user.totp_enabled and user.totp_secret:
        plain_secret = _decrypt_or_raw_totp_secret(svc, user.id, user.totp_secret)
        if totp_code and totp_code.strip():
            if not TotpManager.verify_code(plain_secret, totp_code.strip(), valid_window=1):
                raise InvalidMfaCodeError(instance=str(request.url.path))
            return issue_completed_auth_response(
                response=response, request=request, svc=svc, user=user, trace_id=trace_id
            )
        _, raw_token = await create_login_second_factor_challenge_on_postgres18(
            engine,
            user_id=user.id,
            challenge_kind="TOTP",
            ttl_seconds=TOTP_CHALLENGE_TTL_SECONDS,
        )
        return _two_factor_step_response(
            user=user,
            challenge_token=raw_token,
            challenge_kind="TOTP",
            ttl_seconds=TOTP_CHALLENGE_TTL_SECONDS,
            trace_id=trace_id,
        )

    fresh_secret = TotpManager.generate_secret()
    packed_secret = pack_totp_secret_for_user(
        svc.vault_cipher, user_id=user.id, secret_b32=fresh_secret
    )
    _, raw_token = await create_login_second_factor_challenge_on_postgres18(
        engine,
        user_id=user.id,
        challenge_kind="TOTP_ENROLL",
        ttl_seconds=TOTP_CHALLENGE_TTL_SECONDS,
        pending_totp_secret_encrypted=packed_secret,
    )
    return _two_factor_step_response(
        user=user,
        challenge_token=raw_token,
        challenge_kind="TOTP_ENROLL",
        ttl_seconds=TOTP_CHALLENGE_TTL_SECONDS,
        totp_provisioning_uri=build_totp_provisioning_uri(
            secret_b32=fresh_secret, account_email=user.email
        ),
        totp_manual_key=format_totp_manual_key(fresh_secret),
        trace_id=trace_id,
    )


async def execute_verify_login_2fa(
    *,
    engine: AsyncEngine,
    request: Request,
    response: Response,
    svc: AuthAndOrganizationService,
    challenge_token: str,
    code: str,
    trace_id: str,
) -> AuthTokenResponse:
    """Verify a step-2 `EMAIL_OTP`, `TOTP`, or `TOTP_ENROLL` code and finalize login."""
    challenge = await load_login_challenge_by_token_from_postgres18(
        engine, challenge_token=challenge_token
    )
    now = datetime.now(UTC)
    if (
        challenge is None
        or challenge.consumed_at is not None
        or challenge.expires_at <= now
        or challenge.attempts_count >= challenge.max_attempts
    ):
        raise InvalidOrExpiredLoginChallengeError(instance=str(request.url.path))

    async with engine.begin() as conn:
        candidate = await load_auth_candidate_by_id_from_postgres18(conn, user_id=challenge.user_id)
    if candidate is None or not candidate.is_active or candidate.iam_status == "DISABLED":
        raise InvalidOrExpiredLoginChallengeError(instance=str(request.url.path))

    normalized_code = code.strip()
    valid_code = False
    if challenge.challenge_kind == "EMAIL_OTP":
        valid_code = bool(
            challenge.otp_code_hash
            and verify_otp_code_hash(
                challenge_id=challenge.id,
                candidate_code=normalized_code,
                expected_hash=challenge.otp_code_hash,
            )
        )
    elif challenge.challenge_kind == "TOTP":
        if candidate.totp_secret_encrypted:
            secret_b32 = _decrypt_or_raw_totp_secret(
                svc, candidate.user_id, candidate.totp_secret_encrypted
            )
            valid_code = TotpManager.verify_code(secret_b32, normalized_code, valid_window=1)
    elif challenge.challenge_kind == "TOTP_ENROLL" and challenge.pending_totp_secret_encrypted:
        secret_b32 = _decrypt_or_raw_totp_secret(
            svc, candidate.user_id, challenge.pending_totp_secret_encrypted
        )
        valid_code = TotpManager.verify_code(secret_b32, normalized_code, valid_window=1)

    if not valid_code:
        new_attempts = await increment_challenge_attempts_on_postgres18(
            engine, challenge_id=challenge.id
        )
        if new_attempts >= challenge.max_attempts:
            raise InvalidOrExpiredLoginChallengeError(instance=str(request.url.path))
        raise InvalidMfaCodeError(instance=str(request.url.path))

    consumed = await consume_login_challenge_on_postgres18(engine, challenge_id=challenge.id)
    if not consumed:
        raise InvalidOrExpiredLoginChallengeError(instance=str(request.url.path))

    final_candidate = candidate
    if challenge.challenge_kind == "TOTP_ENROLL" and challenge.pending_totp_secret_encrypted:
        await activate_user_totp_secret_on_postgres18(
            engine,
            user_id=candidate.user_id,
            encrypted_totp_secret=challenge.pending_totp_secret_encrypted,
        )
        async with engine.begin() as conn:
            refreshed = await load_auth_candidate_by_id_from_postgres18(
                conn, user_id=candidate.user_id
            )
            if refreshed is not None:
                final_candidate = refreshed

    user = user_identity_from_candidate(final_candidate, auth_mode="LOCAL")
    return issue_completed_auth_response(
        response=response, request=request, svc=svc, user=user, trace_id=trace_id
    )


async def execute_resend_login_2fa(
    *,
    engine: AsyncEngine,
    request: Request,
    svc: AuthAndOrganizationService,
    challenge_token: str,
    trace_id: str,
) -> ResendLoginTwoFactorResponse:
    """Regenerate and dispatch a fresh 6-digit `EMAIL_OTP` code for an active challenge."""
    challenge = await load_login_challenge_by_token_from_postgres18(
        engine, challenge_token=challenge_token
    )
    if (
        challenge is None
        or challenge.challenge_kind != "EMAIL_OTP"
        or challenge.consumed_at is not None
        or challenge.expires_at <= datetime.now(UTC)
    ):
        raise InvalidOrExpiredLoginChallengeError(instance=str(request.url.path))

    async with engine.begin() as conn:
        candidate = await load_auth_candidate_by_id_from_postgres18(conn, user_id=challenge.user_id)
    if candidate is None or not candidate.is_active or candidate.iam_status == "DISABLED":
        raise InvalidOrExpiredLoginChallengeError(instance=str(request.url.path))

    fresh_otp = generate_numeric_otp_code(digits=6)
    await update_login_challenge_email_otp_on_postgres18(
        engine, challenge_id=challenge.id, new_otp_code=fresh_otp, ttl_seconds=EMAIL_OTP_TTL_SECONDS
    )
    await send_login_email_otp(
        engine,
        cipher=svc.vault_cipher,
        recipient_email=candidate.email,
        otp_code=fresh_otp,
        locale=_request_locale(request),
        otp_email_sink=getattr(request.app.state, "otp_email_sink", None),
        instance=str(request.url.path),
    )
    return ResendLoginTwoFactorResponse(
        sent=True,
        masked_destination=challenge.masked_destination or mask_email_address(candidate.email),
        expires_in_seconds=EMAIL_OTP_TTL_SECONDS,
        trace_id=trace_id,
    )
