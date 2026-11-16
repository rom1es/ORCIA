"""Security tests for canary leak & audit scope (`DEC-SEC-01`, `AD-20`)."""

from __future__ import annotations

from orcia_core.audit_finops.outbox_subscriber import (
    map_domain_event_to_ledger_entry,
    scrub_sensitive_dict,
)
from orcia_core.kernel.events import AdminConnectionTested


def test_dec_sec_01_canary_leak_scrubbing_exhaustive() -> None:
    """Verify that any canary secret pattern is wiped with [REDACTED_SECRET]."""
    canary = "sk-live-" + "super-secret-canary-key-998877"  # pragma: allowlist secret
    fake_pem = ("-----" + "BEGIN ") + ("PRIVATE " + "KEY----- ...")
    raw_payload = {
        "api_key": canary,  # pragma: allowlist secret
        "nested_config": {
            "token": canary,  # pragma: allowlist secret
            "private_key": fake_pem,
            "password": "UltraSecretPassword!",  # pragma: allowlist secret
            "auth": f"Bearer {canary}",  # pragma: allowlist secret
            "authorization": f"Basic {canary}",  # pragma: allowlist secret
        },
        "safe_identifier": "mcp_connector_1",
    }

    sanitized = scrub_sensitive_dict(raw_payload)
    serialized = str(sanitized)

    assert canary not in serialized
    assert sanitized["api_key"] == "[REDACTED_SECRET]"
    assert isinstance(sanitized["nested_config"], dict)
    assert sanitized["nested_config"]["token"] == "[REDACTED_SECRET]"
    assert sanitized["nested_config"]["password"] == "[REDACTED_SECRET]"
    assert sanitized["nested_config"]["authorization"] == "[REDACTED_SECRET]"
    assert sanitized["safe_identifier"] == "mcp_connector_1"


def test_audit_event_mapping_never_retains_raw_canary() -> None:
    """Verify that domain event mapping immediately scrubs canary credentials."""
    canary = "ghp_" + "canary_pat_personal_access_token_456"  # pragma: allowlist secret
    evt = AdminConnectionTested.create(
        actor_id="admin-sec",
        target_type="mcp_connector",
        target_id="github-sdlc",
        protocol="stdio",
        test_status="SUCCESS",
        latency_ms=30,
        metadata={
            "token": canary,
            "secret_env": canary,
        },
    )

    entry = map_domain_event_to_ledger_entry(evt)

    assert canary not in str(entry.metadata)
    assert entry.metadata.get("token") == "[REDACTED_SECRET]"
