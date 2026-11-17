"""Security tests for Story 7.0a: zero secret leakage across stdout/stderr JSON logs."""

from __future__ import annotations

import json
import logging

import pytest

from orcia_core.kernel.secret_ports import SecretRef
from orcia_core.observability.logging import (
    clear_sensitive_secret_values,
    configure_logging,
    get_logger,
    register_sensitive_secret_value,
)


def test_story_7_0a_canary_secret_never_leaks_in_stdout_or_stderr_logs(
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Inject canary secrets into structlog, stdlib, ctx, and exceptions and verify 0 leaks."""
    clear_sensitive_secret_values()
    configure_logging(service="api", log_level="DEBUG")

    canary = "CANARY_SECRET_7_0A_TEST_VALUE_XYZ123"  # pragma: allowlist secret
    jwt_canary = (
        "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9."  # pragma: allowlist secret
        "eyJzdWIiOiIxMjM0NTY3ODkwIn0.c2VjcmV0c2ln"
    )
    sk_canary = "sk-orcia-canary-key-99887766"  # pragma: allowlist secret
    pat_canary = "pat_orcia_canary_token_554433"  # pragma: allowlist secret
    boot_canary = "boot-secret-canary-445566"  # pragma: allowlist secret
    register_sensitive_secret_value(canary)

    secret_ref = SecretRef(uri="secret://workspace/ws-sec/llm-key", workspace_id="ws-sec")
    s_logger = get_logger("orcia.security.test")
    stdlib_logger = logging.getLogger("orcia.security.stdlib")

    s_logger.info(
        f"Structlog message leaking {canary} and Bearer {canary} and {jwt_canary}",
        password=canary,  # pragma: allowlist secret
        token=canary,
        api_key=sk_canary,  # pragma: allowlist secret
        authorization=f"Bearer {canary}",
        pat=pat_canary,
        jwt=jwt_canary,
        ORCIA_BOOTSTRAP_TOKEN=boot_canary,
        secret_ref=secret_ref,
        nested={"deep": {"secret": canary, "inline": f"ORCIA_BOOTSTRAP_TOKEN={boot_canary}"}},
    )

    stdlib_logger.warning(
        "Stdlib warning with %s and %s and ORCIA_BOOTSTRAP_TOKEN=%s",
        sk_canary,
        jwt_canary,
        boot_canary,
    )

    try:
        raise ValueError(
            f"Auth failed for Bearer {canary} with token={pat_canary} and key={sk_canary}"
        )
    except ValueError:
        s_logger.exception("exception.with.secrets")

    captured = capsys.readouterr()
    assert captured.err == ""
    raw_out = captured.out

    for forbidden in (canary, jwt_canary, sk_canary, pat_canary, boot_canary):
        assert forbidden not in raw_out

    lines = [line for line in raw_out.splitlines() if line.strip()]
    assert len(lines) == 3
    for line in lines:
        parsed = json.loads(line)
        assert "message" in parsed
        assert "ctx" in parsed
    clear_sensitive_secret_values()
