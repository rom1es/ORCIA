"""Story 9.4 & 20.3 — User Preferences (`0 ms` Anti-FOUC) & Personal MCP Tokens (`pat_mcp_*`).

Pure hexagonal domain logic (zero FastAPI / SQLAlchemy imports, `AD-19`).
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime

from orcia_core.permissions._mcp_token_helpers import (
    ASSISTANT_BEHAVIOR_REDIRECT_URI as ASSISTANT_BEHAVIOR_REDIRECT_URI,
)
from orcia_core.permissions._mcp_token_helpers import (
    PAT_MCP_PREFIX as PAT_MCP_PREFIX,
)
from orcia_core.permissions._mcp_token_helpers import (
    AssistantToneMode as AssistantToneMode,
)
from orcia_core.permissions._mcp_token_helpers import (
    InvalidMcpTokenConfigurationError as InvalidMcpTokenConfigurationError,
)
from orcia_core.permissions._mcp_token_helpers import (
    McpCapabilityKey as McpCapabilityKey,
)
from orcia_core.permissions._mcp_token_helpers import (
    McpExpirationDays as McpExpirationDays,
)
from orcia_core.permissions._mcp_token_helpers import (
    McpTargetKind as McpTargetKind,
)
from orcia_core.permissions._mcp_token_helpers import (
    UserLocaleCode as UserLocaleCode,
)
from orcia_core.permissions._mcp_token_helpers import (
    UserThemeMode as UserThemeMode,
)
from orcia_core.permissions._mcp_token_helpers import (
    build_ide_mcp_json_snippet as build_ide_mcp_json_snippet,
)
from orcia_core.permissions._mcp_token_helpers import (
    build_mcp_target_uri as build_mcp_target_uri,
)
from orcia_core.permissions._mcp_token_helpers import (
    decode_mcp_scopes_list as decode_mcp_scopes_list,
)
from orcia_core.permissions._mcp_token_helpers import (
    encode_mcp_scopes_list as encode_mcp_scopes_list,
)
from orcia_core.permissions._mcp_token_helpers import mint_mcp_token_fields
from orcia_kernel.errors import ResourceNotFoundError


@dataclass(frozen=True, slots=True)
class UserAccountPreferences:
    """Personal display, assistant personalization & notification preferences."""

    user_id: str
    theme: UserThemeMode = "light"
    locale: UserLocaleCode = "fr"
    default_hat: str = "ANALYST_PM_PO"
    default_assistant_hat: str = "ANALYST_PM_PO"
    assistant_tone: AssistantToneMode = "balanced"
    personal_instructions: str = ""
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
    created_at_iso: str | None = None
    expires_at_iso: str | None = None
    revoked_at_iso: str | None = None


@dataclass(frozen=True, slots=True)
class IssuedScopedMcpTokenResult:
    """One-time issuance result containing the plaintext `pat_mcp_*` token and its hashed record."""

    plaintext_token: str
    record: ScopedMcpPersonalTokenRecord


def build_new_mcp_token_bundle(
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
    """Validate configuration and mint a cryptographic `pat_mcp_*` + SHA-256 record."""
    raw_secret, fields = mint_mcp_token_fields(
        label=label,
        expires_in_days=expires_in_days,
        rpm_limit=rpm_limit,
        allowed_workspace_slugs=allowed_workspace_slugs,
        exposed_capabilities=exposed_capabilities,
        target_kind=target_kind,
        target_slug=target_slug,
    )
    record = ScopedMcpPersonalTokenRecord(user_id=user_id, **fields)  # type: ignore[arg-type]
    return IssuedScopedMcpTokenResult(plaintext_token=raw_secret, record=record)


class UserPreferencesAndMcpTokenService:
    """In-memory domain service managing user preferences & `pat_mcp_*` tokens (unit / fallback)."""

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
        default_assistant_hat: str | None = None,
        assistant_tone: AssistantToneMode | None = None,
        personal_instructions: str | None = None,
        auto_open_contextual_help: bool | None = None,
        notifications_enabled: bool | None = None,
    ) -> UserAccountPreferences:
        """Persist updated user preferences (`PATCH /api/v1/users/me/preferences`)."""
        current = self.get_preferences(user_id)
        next_hat = (
            default_assistant_hat
            if default_assistant_hat is not None
            else (default_hat if default_hat is not None else current.default_assistant_hat)
        )
        updated = UserAccountPreferences(
            user_id=user_id,
            theme=theme if theme is not None else current.theme,
            locale=locale if locale is not None else current.locale,
            default_hat=next_hat,
            default_assistant_hat=next_hat,
            assistant_tone=assistant_tone if assistant_tone is not None else current.assistant_tone,
            personal_instructions=(
                personal_instructions
                if personal_instructions is not None
                else current.personal_instructions
            ),
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
        issued = build_new_mcp_token_bundle(
            user_id=user_id,
            label=label,
            expires_in_days=expires_in_days,
            rpm_limit=rpm_limit,
            allowed_workspace_slugs=allowed_workspace_slugs,
            exposed_capabilities=exposed_capabilities,
            target_kind=target_kind,
            target_slug=target_slug,
        )
        self._tokens_by_id[issued.record.token_id] = issued.record
        return issued

    def list_user_mcp_tokens(self, user_id: str) -> tuple[ScopedMcpPersonalTokenRecord, ...]:
        """List all MCP personal token metadata records for `user_id` (never exposes plaintext)."""
        return tuple(rec for rec in self._tokens_by_id.values() if rec.user_id == user_id)

    def revoke_mcp_token(self, *, user_id: str, token_id: str) -> ScopedMcpPersonalTokenRecord:
        """Instantly revoke a personal MCP token owned by `user_id`."""
        rec = self._tokens_by_id.get(token_id)
        if rec is None or rec.user_id != user_id:
            raise ResourceNotFoundError(detail_override=f"Jeton MCP introuvable : {token_id}")
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
            created_at_iso=rec.created_at_iso,
            expires_at_iso=rec.expires_at_iso,
            revoked_at_iso=datetime.now(UTC).isoformat(),
        )
        self._tokens_by_id[token_id] = revoked_rec
        self._revoked_sha256_redis_set.add(rec.token_sha256)
        return revoked_rec

    def is_token_hash_revoked(self, token_sha256: str) -> bool:
        """Check whether a token SHA-256 hash has been revoked."""
        return token_sha256 in self._revoked_sha256_redis_set
