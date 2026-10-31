"""Story 9.4 — User Account Preferences (`0 ms` Anti-FOUC) & Personal MCP Tokens (`pat_mcp_*`).

Implements:
- `PATCH /api/v1/users/me/preferences` backing the dual-persistence (`localStorage` + API)
  for `UserAccountDropdown` (`280px`) and `UserSettingsModal` (`720px`, Tab 1).
- Scoped personal MCP tokens (`pat_mcp_*` hashed `SHA-256` at rest, mandatory `30d`/`90d`
  expiration, `RPM` cap, allowed Spaces, exposed capabilities, target selector
  `/api/v1/mcp/spaces/<ws_slug>` or `/api/v1/mcp/agents/<agent_slug>`, and IDE JSON snippet
  for VS Code / Cursor / Claude Code / Antigravity / JetBrains — Principle M.4).
"""

from __future__ import annotations

import hashlib
import json
import secrets
from dataclasses import dataclass
from typing import Literal

from orcia_kernel.errors import OrciaDomainError
from orcia_kernel.ids import new_uuid7_str

UserThemeMode = Literal["light", "dark", "system"]
UserLocaleCode = Literal["fr", "en"]
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


@dataclass(frozen=True, slots=True)
class UserAccountPreferences:
    """Personal display & workspace preferences synchronized with `localStorage`."""

    user_id: str
    theme: UserThemeMode = "light"
    locale: UserLocaleCode = "fr"
    default_hat: str = "ANALYST_PM_PO"
    auto_open_contextual_help: bool = True
    notifications_enabled: bool = True
    assistant_behavior_redirect_uri: str = ASSISTANT_BEHAVIOR_REDIRECT_URI


@dataclass(frozen=True, slots=True)
class ScopedMcpPersonalTokenRecord:
    """At-rest representation of a personal MCP token (`pat_mcp_*` stored as `SHA-256`)."""

    token_id: str
    user_id: str
    label: str
    token_prefix: str
    token_sha256: str
    expires_in_days: McpExpirationDays
    rpm_limit: int
    allowed_workspace_slugs: tuple[str, ...]
    exposed_capabilities: tuple[McpCapabilityKey, ...]
    target_kind: McpTargetKind
    target_slug: str
    mcp_endpoint_uri: str
    ide_json_snippet: str
    revoked: bool = False


@dataclass(frozen=True, slots=True)
class IssuedScopedMcpTokenResult:
    """One-time issuance result containing the plaintext `pat_mcp_*` token and its hashed record."""

    plaintext_token: str
    record: ScopedMcpPersonalTokenRecord


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


class UserPreferencesAndMcpTokenService:
    """Domain service managing user preferences (`0 ms` Anti-FOUC sync) and `pat_mcp_*` tokens."""

    def __init__(self) -> None:
        self._preferences_by_user: dict[str, UserAccountPreferences] = {}
        self._tokens_by_id: dict[str, ScopedMcpPersonalTokenRecord] = {}
        self._revoked_sha256_redis_set: set[str] = set()

    def get_preferences(self, user_id: str) -> UserAccountPreferences:
        """Return current user preferences or default French / Light preferences."""
        existing = self._preferences_by_user.get(user_id)
        if existing is not None:
            return existing
        default_prefs = UserAccountPreferences(user_id=user_id)
        self._preferences_by_user[user_id] = default_prefs
        return default_prefs

    def update_preferences(
        self,
        *,
        user_id: str,
        theme: UserThemeMode | None = None,
        locale: UserLocaleCode | None = None,
        default_hat: str | None = None,
        auto_open_contextual_help: bool | None = None,
        notifications_enabled: bool | None = None,
    ) -> UserAccountPreferences:
        """Persist updated user preferences (`PATCH /api/v1/users/me/preferences`)."""
        current = self.get_preferences(user_id)
        updated = UserAccountPreferences(
            user_id=user_id,
            theme=theme if theme is not None else current.theme,
            locale=locale if locale is not None else current.locale,
            default_hat=default_hat if default_hat is not None else current.default_hat,
            auto_open_contextual_help=(
                auto_open_contextual_help
                if auto_open_contextual_help is not None
                else current.auto_open_contextual_help
            ),
            notifications_enabled=(
                notifications_enabled
                if notifications_enabled is not None
                else current.notifications_enabled
            ),
            assistant_behavior_redirect_uri=ASSISTANT_BEHAVIOR_REDIRECT_URI,
        )
        self._preferences_by_user[user_id] = updated
        return updated

    def issue_mcp_token(
        self,
        *,
        user_id: str,
        label: str,
        expires_in_days: int,
        rpm_limit: int,
        allowed_workspace_slugs: tuple[str, ...],
        exposed_capabilities: tuple[McpCapabilityKey, ...],
        target_kind: McpTargetKind,
        target_slug: str,
    ) -> IssuedScopedMcpTokenResult:
        """Issue a scoped `pat_mcp_*` token stored strictly as a `SHA-256` hash."""
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

        endpoint_uri = build_mcp_target_uri(target_kind, target_slug)
        raw_secret = f"{PAT_MCP_PREFIX}{secrets.token_hex(20)}"
        token_sha256 = hashlib.sha256(raw_secret.encode("utf-8")).hexdigest()
        token_prefix = f"{raw_secret[:14]}..."
        server_key = f"orcia-{target_kind.lower()}-{target_slug.strip()}"
        ide_snippet = build_ide_mcp_json_snippet(
            server_key=server_key,
            mcp_endpoint_uri=endpoint_uri,
        )

        exp_days: McpExpirationDays = 30 if expires_in_days == 30 else 90
        record = ScopedMcpPersonalTokenRecord(
            token_id=new_uuid7_str(),
            user_id=user_id,
            label=label.strip() or "Clé IDE MCP",
            token_prefix=token_prefix,
            token_sha256=token_sha256,
            expires_in_days=exp_days,
            rpm_limit=rpm_limit,
            allowed_workspace_slugs=tuple(allowed_workspace_slugs),
            exposed_capabilities=tuple(exposed_capabilities),
            target_kind=target_kind,
            target_slug=target_slug.strip(),
            mcp_endpoint_uri=endpoint_uri,
            ide_json_snippet=ide_snippet,
            revoked=False,
        )
        self._tokens_by_id[record.token_id] = record
        return IssuedScopedMcpTokenResult(plaintext_token=raw_secret, record=record)

    def list_user_mcp_tokens(self, user_id: str) -> tuple[ScopedMcpPersonalTokenRecord, ...]:
        """List all MCP personal token metadata records for `user_id` (never exposes plaintext)."""
        return tuple(rec for rec in self._tokens_by_id.values() if rec.user_id == user_id)

    def revoke_mcp_token(self, *, user_id: str, token_id: str) -> ScopedMcpPersonalTokenRecord:
        """Instantly revoke a personal MCP token (`< 10 ms` Redis revocation set)."""
        rec = self._tokens_by_id.get(token_id)
        if rec is None or rec.user_id != user_id:
            raise InvalidMcpTokenConfigurationError(f"Jeton MCP introuvable : {token_id}")
        revoked_rec = ScopedMcpPersonalTokenRecord(
            token_id=rec.token_id,
            user_id=rec.user_id,
            label=rec.label,
            token_prefix=rec.token_prefix,
            token_sha256=rec.token_sha256,
            expires_in_days=rec.expires_in_days,
            rpm_limit=rec.rpm_limit,
            allowed_workspace_slugs=rec.allowed_workspace_slugs,
            exposed_capabilities=rec.exposed_capabilities,
            target_kind=rec.target_kind,
            target_slug=rec.target_slug,
            mcp_endpoint_uri=rec.mcp_endpoint_uri,
            ide_json_snippet=rec.ide_json_snippet,
            revoked=True,
        )
        self._tokens_by_id[token_id] = revoked_rec
        self._revoked_sha256_redis_set.add(rec.token_sha256)
        return revoked_rec

    def is_token_hash_revoked(self, token_sha256: str) -> bool:
        """Check in `< 10 ms` whether a token SHA-256 hash has been revoked."""
        return token_sha256 in self._revoked_sha256_redis_set
