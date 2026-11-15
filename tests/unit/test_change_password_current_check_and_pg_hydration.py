"""Unit tests for change-password current password verification, PG hash hydration, and SSO guard.

Verifies RFC 9457 error contracts, localized catalogs, and memory/PG synchronization.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from starlette.requests import Request

from orcia_api.routers._auth_password_helpers import execute_change_password
from orcia_api.routers._auth_pg_helpers import hydrate_user_identity_from_pg
from orcia_core.bootstrap import LocalAuthCandidate
from orcia_core.permissions import build_default_auth_and_org_service
from orcia_core.permissions._error_catalog import PERMISSIONS_ERROR_CATALOG
from orcia_core.permissions.errors import (
    AuthenticationRequiredError,
    InvalidCurrentPasswordError,
    LocalPasswordChangeForbiddenForSsoError,
    PasswordUnchangedError,
    ResourceNotFoundError,
    WeakPasswordPolicyError,
)
from orcia_core.permissions.models import UserIdentity

TEST_TRACE_ID = "4bf92f3577b34da6a3ce929d0e0e4736"


def _build_request(
    headers: list[tuple[bytes, bytes]] | None = None,
    cookies: str | None = None,
) -> Request:
    hdrs = list(headers or [])
    if cookies:
        hdrs.append((b"cookie", cookies.encode("latin-1")))
    scope = {
        "type": "http",
        "method": "POST",
        "path": "/api/v1/auth/change-password",
        "headers": hdrs,
    }
    return Request(scope)


def test_invalid_current_password_error_attributes_and_localized_copy() -> None:
    """Validate RFC 9457 status code 422 and copy without OIDC/email mention."""
    err = InvalidCurrentPasswordError(instance="/api/v1/auth/change-password")
    assert err.http_status == 422
    assert err.error_code == "ERR_AUTH_CURRENT_PASSWORD_INVALID"

    catalog_entry = PERMISSIONS_ERROR_CATALOG["ERR_AUTH_CURRENT_PASSWORD_INVALID"]
    fr_copy = catalog_entry["fr"]
    en_copy = catalog_entry["en"]

    assert "OIDC" not in fr_copy.detail
    assert "e-mail" not in fr_copy.detail.lower()
    assert "Mot de passe actuel incorrect" in fr_copy.title

    assert "OIDC" not in en_copy.detail
    assert "email" not in en_copy.detail.lower()
    assert "Incorrect current password" in en_copy.title


def test_local_password_change_forbidden_for_sso_error_attributes_and_copy() -> None:
    """Validate RFC 9457 status code 422 for SSO account password rejection."""
    err = LocalPasswordChangeForbiddenForSsoError(instance="/api/v1/auth/change-password")
    assert err.http_status == 422
    assert err.error_code == "ERR_AUTH_SSO_PASSWORD_MANAGED_EXTERNALLY"

    catalog_entry = PERMISSIONS_ERROR_CATALOG["ERR_AUTH_SSO_PASSWORD_MANAGED_EXTERNALLY"]
    fr_copy = catalog_entry["fr"]
    assert "SSO" in fr_copy.title or "fournisseur SSO" in fr_copy.title


@pytest.mark.asyncio
async def test_execute_change_password_rejects_wrong_current_password() -> None:
    """Wrong current_password raises InvalidCurrentPasswordError (422)."""
    svc = build_default_auth_and_org_service()
    current_hash = svc.hasher.hash_password("ClaireCurrent2026")  # pragma: allowlist secret

    user = UserIdentity(
        id="usr-claire-1",
        primary_org_unit_id="bu-core",
        display_name="Claire Martin",
        email="claire.martin@orcia.fr",
        auth_mode="LOCAL",
        human_profile_archetype="EXPERT",
        platform_role="CONTRIBUTOR",
        password_hash_argon2id=current_hash,
        must_change_password=True,
    )
    svc.register_user(user)

    tokens = svc.jwt_manager.issue_token_pair(
        user_id=user.id,
        email=user.email,
        role=user.platform_role,
        org_unit_id=user.primary_org_unit_id,
        archetype=user.human_profile_archetype,
        auth_mode="LOCAL",
    )

    req = _build_request([(b"authorization", f"Bearer {tokens.access_token}".encode("latin-1"))])

    with pytest.raises(InvalidCurrentPasswordError) as exc_info:
        await execute_change_password(
            request=req,
            current_password="WrongPassword123",  # pragma: allowlist secret
            new_password="NewSecurePassword2026",  # pragma: allowlist secret
            trace_id=TEST_TRACE_ID,
            svc=svc,
            engine=None,
        )

    assert exc_info.value.http_status == 422
    assert exc_info.value.error_code == "ERR_AUTH_CURRENT_PASSWORD_INVALID"


@pytest.mark.asyncio
async def test_execute_change_password_rejects_missing_password_hash() -> None:
    """Account with None password hash cannot bypass current password check."""
    svc = build_default_auth_and_org_service()

    user = UserIdentity(
        id="usr-nohash-1",
        primary_org_unit_id="bu-core",
        display_name="No Hash User",
        email="nohash@orcia.fr",
        auth_mode="LOCAL",
        human_profile_archetype="EXPERT",
        platform_role="CONTRIBUTOR",
        password_hash_argon2id=None,
        must_change_password=True,
    )
    svc.register_user(user)

    tokens = svc.jwt_manager.issue_token_pair(
        user_id=user.id,
        email=user.email,
        role=user.platform_role,
        org_unit_id=user.primary_org_unit_id,
        archetype=user.human_profile_archetype,
        auth_mode="LOCAL",
    )

    req = _build_request([(b"authorization", f"Bearer {tokens.access_token}".encode("latin-1"))])

    with pytest.raises(InvalidCurrentPasswordError):
        await execute_change_password(
            request=req,
            current_password="AnyPassword123",  # pragma: allowlist secret
            new_password="NewSecurePassword2026",  # pragma: allowlist secret
            trace_id=TEST_TRACE_ID,
            svc=svc,
            engine=None,
        )


@pytest.mark.asyncio
async def test_execute_change_password_rejects_sso_oidc_account() -> None:
    """Account signed in via OIDC cannot change password locally."""
    svc = build_default_auth_and_org_service()
    hashed = svc.hasher.hash_password("TempPassword123")  # pragma: allowlist secret

    user = UserIdentity(
        id="usr-oidc-1",
        primary_org_unit_id="bu-core",
        display_name="SSO User",
        email="sso.user@orcia.fr",
        auth_mode="OIDC",
        human_profile_archetype="EXPERT",
        platform_role="CONTRIBUTOR",
        password_hash_argon2id=hashed,
        must_change_password=False,
    )
    svc.register_user(user)

    tokens = svc.jwt_manager.issue_token_pair(
        user_id=user.id,
        email=user.email,
        role=user.platform_role,
        org_unit_id=user.primary_org_unit_id,
        archetype=user.human_profile_archetype,
        auth_mode="OIDC",
    )

    req = _build_request([(b"authorization", f"Bearer {tokens.access_token}".encode("latin-1"))])

    with pytest.raises(LocalPasswordChangeForbiddenForSsoError) as exc_info:
        await execute_change_password(
            request=req,
            current_password="TempPassword123",  # pragma: allowlist secret
            new_password="NewSecurePassword2026",  # pragma: allowlist secret
            trace_id=TEST_TRACE_ID,
            svc=svc,
            engine=None,
        )

    assert exc_info.value.http_status == 422
    assert exc_info.value.error_code == "ERR_AUTH_SSO_PASSWORD_MANAGED_EXTERNALLY"


@pytest.mark.asyncio
async def test_hydrate_user_identity_from_pg_propagates_pg_candidate_password_hash() -> None:
    """hydrate_user_identity_from_pg copies candidate.password_hash_argon2id to refreshed user."""
    svc = build_default_auth_and_org_service()
    old_hash = svc.hasher.hash_password("OldPassword123")  # pragma: allowlist secret
    new_pg_temp_hash = svc.hasher.hash_password("NewTempSecret1")  # pragma: allowlist secret

    user = UserIdentity(
        id="usr-sync-1",
        primary_org_unit_id="bu-core",
        display_name="Sync User",
        email="sync.user@orcia.fr",
        auth_mode="LOCAL",
        human_profile_archetype="EXPERT",
        platform_role="CONTRIBUTOR",
        password_hash_argon2id=old_hash,
        must_change_password=False,
    )
    svc.register_user(user)

    candidate = LocalAuthCandidate(
        user_id="usr-sync-1",
        email="sync.user@orcia.fr",
        display_name="Sync User",
        password_hash_argon2id=new_pg_temp_hash,
        must_change_password=True,
        is_active=True,
        iam_status="ACTIVE",
        platform_role="CONTRIBUTOR",
        roles=("CONTRIBUTOR",),
        primary_org_unit_id="bu-core",
        human_profile_archetype="EXPERT",
    )

    mock_conn = AsyncMock()
    mock_begin = MagicMock()
    mock_begin.__aenter__ = AsyncMock(return_value=mock_conn)
    mock_begin.__aexit__ = AsyncMock(return_value=None)
    mock_engine = MagicMock()
    mock_engine.begin.return_value = mock_begin

    with patch(
        "orcia_api.routers._auth_pg_helpers.load_local_auth_candidate_from_postgres18",
        new=AsyncMock(return_value=candidate),
    ):
        hydrated = await hydrate_user_identity_from_pg(mock_engine, user, svc=svc)

    assert hydrated.password_hash_argon2id == new_pg_temp_hash
    assert hydrated.must_change_password is True
    # In-memory service also updated
    in_memory = svc.get_user_by_id("usr-sync-1")
    assert in_memory.password_hash_argon2id == new_pg_temp_hash


@pytest.mark.asyncio
async def test_execute_change_password_succeeds_with_rehydrated_candidate_hash() -> None:
    """When user in RAM has stale hash, PG rehydration supplies updated temp hash."""
    svc = build_default_auth_and_org_service()
    old_hash = svc.hasher.hash_password("OldStalePass123")  # pragma: allowlist secret
    temp_pwd = "NewTempSecret12"  # pragma: allowlist secret
    temp_hash = svc.hasher.hash_password(temp_pwd)

    user = UserIdentity(
        id="usr-claire-2",
        primary_org_unit_id="bu-core",
        display_name="Claire Martin",
        email="claire.martin@orcia.fr",
        auth_mode="LOCAL",
        human_profile_archetype="EXPERT",
        platform_role="CONTRIBUTOR",
        password_hash_argon2id=old_hash,
        must_change_password=True,
    )
    svc.register_user(user)

    tokens = svc.jwt_manager.issue_token_pair(
        user_id=user.id,
        email=user.email,
        role=user.platform_role,
        org_unit_id=user.primary_org_unit_id,
        archetype=user.human_profile_archetype,
        auth_mode="LOCAL",
    )

    candidate = LocalAuthCandidate(
        user_id="usr-claire-2",
        email="claire.martin@orcia.fr",
        display_name="Claire Martin",
        password_hash_argon2id=temp_hash,
        must_change_password=True,
        is_active=True,
        iam_status="ACTIVE",
        platform_role="CONTRIBUTOR",
        roles=("CONTRIBUTOR",),
        primary_org_unit_id="bu-core",
        human_profile_archetype="EXPERT",
    )

    mock_conn = AsyncMock()
    mock_begin = MagicMock()
    mock_begin.__aenter__ = AsyncMock(return_value=mock_conn)
    mock_begin.__aexit__ = AsyncMock(return_value=None)
    mock_engine = MagicMock()
    mock_engine.begin.return_value = mock_begin

    req = _build_request([(b"authorization", f"Bearer {tokens.access_token}".encode("latin-1"))])

    with (
        patch(
            "orcia_api.routers._auth_pg_helpers.load_local_auth_candidate_from_postgres18",
            new=AsyncMock(return_value=candidate),
        ),
        patch(
            "orcia_api.routers._auth_password_helpers.update_user_password_on_postgres18",
            new=AsyncMock(),
        ) as mock_update_pg,
    ):
        res = await execute_change_password(
            request=req,
            current_password=temp_pwd,
            new_password="ClaireBrandNew2026",  # pragma: allowlist secret
            trace_id=TEST_TRACE_ID,
            svc=svc,
            engine=mock_engine,
        )

    assert res.success is True
    assert res.must_change_password is False
    assert mock_update_pg.await_count == 1
    # Check that in-memory user has new password and must_change_password = False
    updated_user = svc.get_user_by_id("usr-claire-2")
    assert updated_user.must_change_password is False
    assert svc.hasher.verify_password(
        updated_user.password_hash_argon2id or "", "ClaireBrandNew2026"
    )


@pytest.mark.asyncio
async def test_execute_change_password_fallback_to_refresh_cookie() -> None:
    """When RAM cache is lost, refresh cookie rehydrates caller from PG and changes password."""
    svc = build_default_auth_and_org_service()
    current_pwd = "CurrentSecret12"  # pragma: allowlist secret
    current_hash = svc.hasher.hash_password(current_pwd)

    tokens = svc.jwt_manager.issue_token_pair(
        user_id="usr-reloaded-1",
        email="reloaded@orcia.fr",
        role="CONTRIBUTOR",
        org_unit_id="bu-core",
        archetype="EXPERT",
        auth_mode="LOCAL",
    )

    # In RAM, user does NOT exist (lost on reload)
    with pytest.raises(ResourceNotFoundError):
        svc.get_user_by_id("usr-reloaded-1")

    candidate = LocalAuthCandidate(
        user_id="usr-reloaded-1",
        email="reloaded@orcia.fr",
        display_name="Reloaded User",
        password_hash_argon2id=current_hash,
        must_change_password=True,
        is_active=True,
        iam_status="ACTIVE",
        platform_role="CONTRIBUTOR",
        roles=("CONTRIBUTOR",),
        primary_org_unit_id="bu-core",
        human_profile_archetype="EXPERT",
    )

    mock_conn = AsyncMock()
    mock_connect = MagicMock()
    mock_connect.__aenter__ = AsyncMock(return_value=mock_conn)
    mock_connect.__aexit__ = AsyncMock(return_value=None)
    mock_engine = MagicMock()
    mock_engine.connect.return_value = mock_connect

    mock_begin = MagicMock()
    mock_begin.__aenter__ = AsyncMock(return_value=mock_conn)
    mock_begin.__aexit__ = AsyncMock(return_value=None)
    mock_engine.begin.return_value = mock_begin

    req = _build_request(cookies=f"orcia_refresh_token={tokens.refresh_token}")

    with (
        patch(
            "orcia_api.routers._auth_pg_helpers.load_auth_candidate_by_id_from_postgres18",
            new=AsyncMock(return_value=candidate),
        ),
        patch(
            "orcia_api.routers._auth_pg_helpers.load_local_auth_candidate_from_postgres18",
            new=AsyncMock(return_value=candidate),
        ),
        patch(
            "orcia_api.routers._auth_password_helpers.update_user_password_on_postgres18",
            new=AsyncMock(),
        ),
    ):
        res = await execute_change_password(
            request=req,
            current_password=current_pwd,
            new_password="NewPermanentPassword2026",  # pragma: allowlist secret
            trace_id=TEST_TRACE_ID,
            svc=svc,
            engine=mock_engine,
        )

    assert res.success is True
    assert res.must_change_password is False


@pytest.mark.asyncio
async def test_execute_change_password_requires_authentication() -> None:
    """Without Authorization header or refresh cookie, raises AuthenticationRequiredError (401)."""
    svc = build_default_auth_and_org_service()
    req = _build_request()

    with pytest.raises(AuthenticationRequiredError):
        await execute_change_password(
            request=req,
            current_password="AnyPassword123",  # pragma: allowlist secret
            new_password="NewPassword1234",  # pragma: allowlist secret
            trace_id=TEST_TRACE_ID,
            svc=svc,
            engine=None,
        )


@pytest.mark.asyncio
async def test_execute_change_password_rejects_identical_password() -> None:
    """Identical current and new password raises PasswordUnchangedError (422)."""
    svc = build_default_auth_and_org_service()
    pwd = "SamePassword123"  # pragma: allowlist secret
    hashed = svc.hasher.hash_password(pwd)

    user = UserIdentity(
        id="usr-same-1",
        primary_org_unit_id="bu-core",
        display_name="Same User",
        email="same@orcia.fr",
        auth_mode="LOCAL",
        human_profile_archetype="EXPERT",
        platform_role="CONTRIBUTOR",
        password_hash_argon2id=hashed,
        must_change_password=True,
    )
    svc.register_user(user)

    tokens = svc.jwt_manager.issue_token_pair(
        user_id=user.id,
        email=user.email,
        role=user.platform_role,
        org_unit_id=user.primary_org_unit_id,
        archetype=user.human_profile_archetype,
        auth_mode="LOCAL",
    )

    req = _build_request([(b"authorization", f"Bearer {tokens.access_token}".encode("latin-1"))])

    with pytest.raises(PasswordUnchangedError):
        await execute_change_password(
            request=req,
            current_password=pwd,
            new_password=pwd,
            trace_id=TEST_TRACE_ID,
            svc=svc,
            engine=None,
        )


@pytest.mark.asyncio
async def test_execute_change_password_rejects_weak_new_password() -> None:
    """Weak new password raises WeakPasswordPolicyError (422)."""
    svc = build_default_auth_and_org_service()
    pwd = "ValidCurrentPassword123"  # pragma: allowlist secret
    hashed = svc.hasher.hash_password(pwd)

    user = UserIdentity(
        id="usr-weak-1",
        primary_org_unit_id="bu-core",
        display_name="Weak User",
        email="weak@orcia.fr",
        auth_mode="LOCAL",
        human_profile_archetype="EXPERT",
        platform_role="CONTRIBUTOR",
        password_hash_argon2id=hashed,
        must_change_password=True,
    )
    svc.register_user(user)

    tokens = svc.jwt_manager.issue_token_pair(
        user_id=user.id,
        email=user.email,
        role=user.platform_role,
        org_unit_id=user.primary_org_unit_id,
        archetype=user.human_profile_archetype,
        auth_mode="LOCAL",
    )

    req = _build_request([(b"authorization", f"Bearer {tokens.access_token}".encode("latin-1"))])

    with pytest.raises(WeakPasswordPolicyError):
        await execute_change_password(
            request=req,
            current_password=pwd,
            new_password="short",  # pragma: allowlist secret
            trace_id=TEST_TRACE_ID,
            svc=svc,
            engine=None,
        )
