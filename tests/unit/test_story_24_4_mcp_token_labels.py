"""Story 24.4 (USER24-BUG-5) — French readable fallback labels for personal IDE/MCP tokens."""

from __future__ import annotations

from orcia_core.permissions._mcp_token_helpers import (
    decode_mcp_scopes_list,
    mint_mcp_token_fields,
)


def test_story_24_4_mcp_token_default_labels_avoid_legacy_default_slug() -> None:
    ws_slugs, caps = decode_mcp_scopes_list([])
    assert ws_slugs == ("scope-global",)
    assert "default" not in ws_slugs
    assert caps == ("ASSISTANT",)

    raw_secret, fields = mint_mcp_token_fields(
        label="   ",
        expires_in_days=30,
        rpm_limit=60,
        allowed_workspace_slugs=("mon-espace",),
        exposed_capabilities=("ASSISTANT",),
        target_kind="SPACE",
        target_slug="mon-espace",
    )
    assert raw_secret.startswith("pat_mcp_")
    assert fields["label"] == "Clé personnelle d'éditeur"
    assert "IDE MCP" not in str(fields["label"])
