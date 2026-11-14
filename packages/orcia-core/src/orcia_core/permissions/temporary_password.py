"""Story 17.6 — Temporary password generation & policy validation (`AD-6`, `AD-19`).

Pure domain logic: zero framework imports (`fastapi`, `sqlalchemy`, etc.).
"""

from __future__ import annotations

import random
import re
import secrets
import string

from orcia_core.permissions.errors import (
    WeakPasswordPolicyError,
)

_LOWERCASE = string.ascii_lowercase
_UPPERCASE = string.ascii_uppercase
_DIGITS = string.digits
_ALPHANUMERIC = _LOWERCASE + _UPPERCASE + _DIGITS


def generate_temporary_password(length: int = 12) -> str:
    """Generate a cryptographically secure alphanumeric password meeting policy requirements.

    Guarantee:
    - Length is exactly `length` (defaults to 12).
    - Only characters from `[a-zA-Z0-9]`.
    - Contains at least 1 lowercase letter, 1 uppercase letter, and 1 digit.
    """
    if length < 12:
        length = 12

    # Guarantee at least one of each mandatory category
    guaranteed = [
        secrets.choice(_LOWERCASE),
        secrets.choice(_UPPERCASE),
        secrets.choice(_DIGITS),
    ]

    # Fill remaining characters with random choices from full alphanumeric set
    remaining = [secrets.choice(_ALPHANUMERIC) for _ in range(length - len(guaranteed))]

    chars = guaranteed + remaining
    random.SystemRandom().shuffle(chars)
    return "".join(chars)


def validate_password_policy(password: str, *, instance: str | None = None) -> None:
    """Validate password against complexity policy (>= 12 chars, upper, lower, digit).

    Raises:
        WeakPasswordPolicyError: if any condition is not met.
    """
    candidate = password or ""
    if len(candidate) < 12:
        raise WeakPasswordPolicyError(instance=instance)

    if not re.search(r"[a-z]", candidate):
        raise WeakPasswordPolicyError(instance=instance)

    if not re.search(r"[A-Z]", candidate):
        raise WeakPasswordPolicyError(instance=instance)

    if not re.search(r"[0-9]", candidate):
        raise WeakPasswordPolicyError(instance=instance)
