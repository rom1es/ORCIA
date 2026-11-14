"""Unit tests for temporary password generation, password policy validation,

and in-memory local authentication helpers.
"""

from __future__ import annotations

import re

import pytest

from orcia_core.permissions import build_default_auth_and_org_service
from orcia_core.permissions.errors import InvalidCredentialsError, WeakPasswordPolicyError
from orcia_core.permissions.models import UserIdentity
from orcia_core.permissions.temporary_password import (
    generate_temporary_password,
    validate_password_policy,
)


def test_generate_temporary_password_guarantees_length_and_composition() -> None:
    for _ in range(50):
        pwd = generate_temporary_password(12)  # pragma: allowlist secret
        assert len(pwd) == 12
        assert re.match(r"^[a-zA-Z0-9]{12}$", pwd) is not None
        assert any(c.islower() for c in pwd)
        assert any(c.isupper() for c in pwd)
        assert any(c.isdigit() for c in pwd)
        validate_password_policy(pwd)


def test_validate_password_policy_accepts_strong_passwords() -> None:
    valid_passwords = [
        "OrciaPlatform2026",  # pragma: allowlist secret
        "TemporaryPass123",  # pragma: allowlist secret
        "Abcdefghijk1",  # pragma: allowlist secret
    ]
    for pwd in valid_passwords:
        validate_password_policy(pwd)


def test_validate_password_policy_rejects_weak_passwords() -> None:
    short_pwd = "Abc1"  # pragma: allowlist secret
    with pytest.raises(WeakPasswordPolicyError):
        validate_password_policy(short_pwd)

    no_digit = "OrciaPlatformAdmin"  # pragma: allowlist secret
    with pytest.raises(WeakPasswordPolicyError):
        validate_password_policy(no_digit)

    no_upper = "orciaplatform123"  # pragma: allowlist secret
    with pytest.raises(WeakPasswordPolicyError):
        validate_password_policy(no_upper)

    no_lower = "ORCIAPLATFORM123"  # pragma: allowlist secret
    with pytest.raises(WeakPasswordPolicyError):
        validate_password_policy(no_lower)


def test_auth_service_in_memory_user_registration_and_login() -> None:
    service = build_default_auth_and_org_service()
    hashed = service.hasher.hash_password("InitialTemp123")  # pragma: allowlist secret

    user = UserIdentity(
        id="usr-test-1",
        primary_org_unit_id="bu-core",
        display_name="Romain Dev",
        email="romain.dev@orcia.local",
        auth_mode="LOCAL",
        human_profile_archetype="EXPERT",
        platform_role="PLATFORM_ADMIN",
        password_hash_argon2id=hashed,
        must_change_password=True,
    )
    service.register_user(user)

    registered = service.get_user_by_id("usr-test-1")
    assert registered.email == "romain.dev@orcia.local"
    assert registered.must_change_password is True

    # Bad password rejected
    with pytest.raises(InvalidCredentialsError):
        service.login_local(
            "romain.dev@orcia.local",
            "WrongPassword123",  # pragma: allowlist secret
        )

    # Valid login succeeds and returns session
    authed_user, session = service.login_local(
        "romain.dev@orcia.local",
        "InitialTemp123",  # pragma: allowlist secret
    )
    assert authed_user.id == "usr-test-1"
    assert authed_user.must_change_password is True
    assert session.access_token is not None

    # Simulate password change
    new_hashed = service.hasher.hash_password("NewSecurePassword2026")  # pragma: allowlist secret
    updated_user = UserIdentity(
        id="usr-test-1",
        primary_org_unit_id="bu-core",
        display_name="Romain Dev",
        email="romain.dev@orcia.local",
        auth_mode="LOCAL",
        human_profile_archetype="EXPERT",
        platform_role="PLATFORM_ADMIN",
        password_hash_argon2id=new_hashed,
        must_change_password=False,
    )
    service.register_user(updated_user)

    re_authed, _ = service.login_local(
        "romain.dev@orcia.local",
        "NewSecurePassword2026",  # pragma: allowlist secret
    )
    assert re_authed.must_change_password is False
