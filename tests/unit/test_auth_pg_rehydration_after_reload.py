"""Unit tests for AuthAndOrganizationService and PG rehydration helpers after reload.

Validates that:
1. `has_user_in_memory`, `verify_access_token_claims`, and `verify_refresh_token_claims` work.
2. Token claims can be verified even when RAM cache has 0 users.
3. `rehydrate_user_from_pg_by_id` registers the user when active and unregisters when deactivated.
4. `rehydrate_bearer_subject_from_pg_if_missing` recovers user identity without private access.
"""

from __future__ import annotations

from contextlib import asynccontextmanager
from unittest.mock import AsyncMock, MagicMock

import pytest

import orcia_api.routers._auth_pg_helpers as auth_pg_helpers
from orcia_api.routers._auth_pg_helpers import (
    rehydrate_bearer_subject_from_pg_if_missing,
    rehydrate_user_from_pg_by_id,
)
from orcia_core.bootstrap import LocalAuthCandidate
from orcia_core.permissions import (
    UserIdentity,
    build_default_auth_and_org_service,
)
from orcia_core.permissions.errors import (
    InvalidCredentialsError,
    RevokedTokenError,
)
from orcia_kernel.ids import new_uuid7_str


def _build_test_user(*, user_id: str, email: str, is_active: bool = True) -> UserIdentity:
    return UserIdentity(
        id=user_id,
        email=email,
        display_name="Test User",
        auth_mode="LOCAL",
        human_profile_archetype="CORE_ENGINEER",
        platform_role="CORE_TEAM",
        primary_org_unit_id="0195f000-0000-7000-8000-000000000103",
        is_active=is_active,
    )


def _build_test_candidate(
    *, user_id: str, email: str, is_active: bool = True
) -> LocalAuthCandidate:
    return LocalAuthCandidate(
        user_id=user_id,
        email=email,
        display_name="Candidate User",
        password_hash_argon2id="$argon2id$v=19$m=19456,t=2,p=1$fake$hash",
        is_active=is_active,
        must_change_password=False,
        platform_role="PLATFORM_ADMIN",
        roles=("PLATFORM_ADMIN", "CORE_TEAM"),
        iam_status="ACTIVE" if is_active else "DISABLED",
        primary_org_unit_id="0195f000-0000-7000-8000-000000000101",
        totp_secret_encrypted=None,
        totp_enabled=False,
        human_profile_archetype="CHIEF_ARCHITECT",
    )


def test_auth_service_has_user_in_memory_and_public_claims_verification() -> None:
    svc = build_default_auth_and_org_service(seed_reference_personas=False)
    user_id = new_uuid7_str()
    user = _build_test_user(user_id=user_id, email="alice@orcia.io")
    svc.register_user(user)

    # 1. has_user_in_memory checks
    assert svc.has_user_in_memory(user_id) is True
    assert svc.has_user_in_memory("00000000-0000-0000-0000-000000000000") is False

    # Deactivated user in RAM returns False
    inactive_id = new_uuid7_str()
    svc.register_user(_build_test_user(user_id=inactive_id, email="bob@orcia.io", is_active=False))
    assert svc.has_user_in_memory(inactive_id) is False

    # 2. Token issue and claim verification without requiring user in RAM
    pair = svc.jwt_manager.issue_token_pair(
        user_id=user_id,
        email=user.email,
        role=user.platform_role,
        org_unit_id=user.primary_org_unit_id,
        archetype=user.human_profile_archetype,
        auth_mode="LOCAL",
    )

    # Simulate RAM miss: unregister user
    svc.unregister_user(user_id)
    assert svc.has_user_in_memory(user_id) is False

    # verify_access_token_claims works even when user is missing from RAM
    access_claims = svc.verify_access_token_claims(f"Bearer {pair.access_token}")
    assert access_claims.sub == user_id
    assert access_claims.email == "alice@orcia.io"
    assert access_claims.token_type == "access"

    # verify_refresh_token_claims also works
    refresh_claims = svc.verify_refresh_token_claims(pair.refresh_token)
    assert refresh_claims.sub == user_id
    assert refresh_claims.token_type == "refresh"

    # Revocation check
    svc.revocation_store.revoke_jti(access_claims.jti)
    with pytest.raises(RevokedTokenError):
        svc.verify_access_token_claims(pair.access_token)

    # Invalid token check
    with pytest.raises(InvalidCredentialsError):
        svc.verify_access_token_claims("Bearer invalid.token.payload")


@pytest.mark.asyncio
async def test_rehydrate_user_from_pg_by_id_registers_active_and_purges_inactive(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    svc = build_default_auth_and_org_service(seed_reference_personas=False)
    user_id = new_uuid7_str()
    candidate = _build_test_candidate(user_id=user_id, email="karim@orcia.io", is_active=True)

    # Mock load_auth_candidate_by_id_from_postgres18
    mock_load = AsyncMock(return_value=candidate)
    monkeypatch.setattr(
        auth_pg_helpers,
        "load_auth_candidate_by_id_from_postgres18",
        mock_load,
    )

    conn_mock = AsyncMock()

    @asynccontextmanager
    async def _fake_connect():
        yield conn_mock

    engine_mock = MagicMock()
    engine_mock.connect = _fake_connect

    # 1. Rehydration succeeds and registers user into memory
    rehydrated = await rehydrate_user_from_pg_by_id(
        engine_mock, svc, user_id=user_id, auth_mode="LOCAL"
    )
    assert rehydrated is not None
    assert rehydrated.id == user_id
    assert svc.has_user_in_memory(user_id) is True
    assert svc.get_user_by_id(user_id).email == "karim@orcia.io"

    # 2. Deactivated candidate removes user from memory
    inactive_candidate = _build_test_candidate(
        user_id=user_id, email="karim@orcia.io", is_active=False
    )
    mock_load.return_value = inactive_candidate

    result = await rehydrate_user_from_pg_by_id(engine_mock, svc, user_id=user_id)
    assert result is None
    assert svc.has_user_in_memory(user_id) is False


@pytest.mark.asyncio
async def test_rehydrate_bearer_subject_from_pg_if_missing_middleware_helper(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    svc = build_default_auth_and_org_service(seed_reference_personas=False)
    user_id = new_uuid7_str()
    candidate = _build_test_candidate(user_id=user_id, email="admin@orcia.io", is_active=True)

    tokens = svc.jwt_manager.issue_token_pair(
        user_id=user_id,
        email="admin@orcia.io",
        role="PLATFORM_ADMIN",
        org_unit_id="0195f000-0000-7000-8000-000000000101",
        archetype="CHIEF_ARCHITECT",
        auth_mode="LOCAL",
    )

    mock_load = AsyncMock(return_value=candidate)
    monkeypatch.setattr(
        auth_pg_helpers,
        "load_auth_candidate_by_id_from_postgres18",
        mock_load,
    )

    conn_mock = AsyncMock()

    @asynccontextmanager
    async def _fake_connect():
        yield conn_mock

    engine_mock = MagicMock()
    engine_mock.connect = _fake_connect

    request_mock = MagicMock()
    request_mock.headers = {"Authorization": f"Bearer {tokens.access_token}"}
    request_mock.app.state.auth_service = svc
    request_mock.app.state.db_engine = engine_mock

    monkeypatch.setattr(
        "orcia_api.dependencies.get_or_create_shared_db_engine",
        lambda _req: engine_mock,
    )

    assert svc.has_user_in_memory(user_id) is False
    await rehydrate_bearer_subject_from_pg_if_missing(request_mock)
    assert svc.has_user_in_memory(user_id) is True
    assert svc.get_user_by_id(user_id).platform_role == "PLATFORM_ADMIN"
