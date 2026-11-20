"""Pure domain helpers for `pat_mcp_*` token construction and scope encoding."""

from __future__ import annotations

import hashlib
import json
import secrets
from datetime import UTC, datetime, timedelta
from typing import Literal, cast

from orcia_kernel.errors import OrciaDomainError
from orcia_kernel.ids import new_uuid7_str

UserThemeMode = Literal["light", "dark", "system"]
UserLocaleCode = Literal["fr", "en"]
AssistantToneMode = Literal["balanced", "concise", "detailed"]
McpExpirationDays = Literal[30, 90]
McpTargetKind = Literal["SPACE", "AGENT"]
McpCapabilityKey = Literal[
    "ASSISTANT",
    "PUBLISHED_AGENTS",
    "KB_GLOSSARY_SEARCH",
    "STAGED_DRAFTS",
]

PAT_MCP_PREFIX: str = "pat_mcp_"
ASSISTANT_BEHAVIOR_REDIRECT_URI: str = "/assistant?modal=settings"


class InvalidMcpTokenConfigurationError(OrciaDomainError):
    """Raised when an MCP personal token request violates security invariants."""

    error_code = "ERR_INVALID_MCP_TOKEN_CONFIG"
    http_status, type_slug = 422, "invalid-mcp-token-config"

    def __init__(self, detail_override: str | None = None) -> None:
        super().__init__(detail_override=detail_override)


def build_mcp_target_uri(target_kind: McpTargetKind, target_slug: str) -> str:
    """Build the canonical MCP endpoint URI for a Space or a specific Agent (`Principle M.4`)."""
    clean_slug = target_slug.strip().strip("/")
    if not clean_slug:
        raise InvalidMcpTokenConfigurationError(
            "Le slug de cible MCP (Espace ou Agent) ne peut pas être vide."
        )
    if target_kind == "SPACE":
        return f"/api/v1/mcp/spaces/{clean_slug}"
    return f"/api/v1/mcp/agents/{clean_slug}"


def build_ide_mcp_json_snippet(
    *,
    server_key: str,
    mcp_endpoint_uri: str,
    token_placeholder: str = "${ORCIA_MCP_PAT}",
) -> str:
    """Generate a ready-to-copy MCP JSON snippet for VS Code / Cursor / Claude Code."""
    payload = {
        "mcpServers": {
            server_key: {
                "url": f"https://orcia.internal{mcp_endpoint_uri}",
                "headers": {
                    "Authorization": f"Bearer {token_placeholder}",
                },
            }
        }
    }
    return json.dumps(payload, indent=2, ensure_ascii=False)


def encode_mcp_scopes_list(
    allowed_workspace_slugs: tuple[str, ...],
    exposed_capabilities: tuple[McpCapabilityKey, ...],
) -> list[str]:
    """Encode workspace slugs and capabilities into a flat JSONB scope list."""
    return [f"ws:{s}" for s in allowed_workspace_slugs] + [f"cap:{c}" for c in exposed_capabilities]


def decode_mcp_scopes_list(
    scopes: list[str] | tuple[str, ...],
) -> tuple[tuple[str, ...], tuple[McpCapabilityKey, ...]]:
    """Decode workspace slugs and capabilities from a flat JSONB scope list."""
    valid_caps: set[str] = {
        "ASSISTANT",
        "PUBLISHED_AGENTS",
        "KB_GLOSSARY_SEARCH",
        "STAGED_DRAFTS",
    }
    ws_slugs = tuple(item[3:] for item in scopes if item.startswith("ws:") and item[3:])
    caps = tuple(
        cast(McpCapabilityKey, item[4:])
        for item in scopes
        if item.startswith("cap:") and item[4:] in valid_caps
    )
    return (ws_slugs or ("scope-global",), caps or ("ASSISTANT",))


def mint_mcp_token_fields(
    *,
    label: str,
    expires_in_days: int,
    rpm_limit: int,
    allowed_workspace_slugs: tuple[str, ...],
    exposed_capabilities: tuple[McpCapabilityKey, ...],
    target_kind: McpTargetKind,
    target_slug: str,
) -> tuple[str, dict[str, object]]:
    """Validate MCP config and return `(plaintext_token, record_kwargs)`."""
    if expires_in_days not in (30, 90):
        raise InvalidMcpTokenConfigurationError(
            "L'expiration d'un jeton MCP personnel doit être obligatoirement de 30 ou 90 jours."
        )
    if rpm_limit < 1 or rpm_limit > 600:
        raise InvalidMcpTokenConfigurationError(
            "Le plafond RPM du jeton MCP doit être compris entre 1 et 600 requêtes/minute."
        )
    if not allowed_workspace_slugs:
        raise InvalidMcpTokenConfigurationError(
            "Au moins un Espace autorisé doit être sélectionné pour le jeton MCP."
        )
    if not exposed_capabilities:
        raise InvalidMcpTokenConfigurationError(
            "Au moins une capacité exposée doit être sélectionnée pour le jeton MCP."
        )
    clean_slug = target_slug.strip()
    endpoint_uri = build_mcp_target_uri(target_kind, clean_slug)
    raw_secret = f"{PAT_MCP_PREFIX}{secrets.token_urlsafe(24)}"
    token_sha256 = hashlib.sha256(raw_secret.encode("utf-8")).hexdigest()
    now_dt = datetime.now(UTC)
    exp_days: McpExpirationDays = 30 if expires_in_days == 30 else 90
    return raw_secret, {
        "token_id": new_uuid7_str(),
        "label": label.strip() or "Clé personnelle d'éditeur",
        "token_prefix": f"{raw_secret[:14]}...",
        "token_sha256": token_sha256,
        "expires_in_days": exp_days,
        "rpm_limit": rpm_limit,
        "allowed_workspace_slugs": tuple(allowed_workspace_slugs),
        "exposed_capabilities": tuple(exposed_capabilities),
        "target_kind": target_kind,
        "target_slug": clean_slug,
        "mcp_endpoint_uri": endpoint_uri,
        "ide_json_snippet": build_ide_mcp_json_snippet(
            server_key=f"orcia-{target_kind.lower()}-{clean_slug}",
            mcp_endpoint_uri=endpoint_uri,
        ),
        "revoked": False,
        "created_at_iso": now_dt.isoformat(),
        "expires_at_iso": (now_dt + timedelta(days=exp_days)).isoformat(),
        "revoked_at_iso": None,
    }
