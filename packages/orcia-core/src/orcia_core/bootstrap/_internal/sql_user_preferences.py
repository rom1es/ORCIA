"""Story 20.3 — PostgreSQL 18 adapter for User Preferences & Personal IDE/MCP Tokens."""

from __future__ import annotations

import json
from datetime import datetime
from uuid import UUID

import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncEngine

from orcia_core.bootstrap._internal.sql_user_preferences_queries import (
    SQL_INSERT_MCP_TOKEN,
    SQL_LIST_MCP_TOKENS,
    SQL_REVOKE_MCP_TOKEN,
    SQL_SELECT_PREFS,
    SQL_UPSERT_PREFS,
    row_to_mcp_record,
    row_to_prefs,
)
from orcia_core.permissions.user_preferences_and_mcp_tokens import (
    AssistantToneMode,
    IssuedScopedMcpTokenResult,
    McpCapabilityKey,
    McpTargetKind,
    ScopedMcpPersonalTokenRecord,
    UserAccountPreferences,
    UserLocaleCode,
    UserPreferencesAndMcpTokenService,
    UserThemeMode,
    build_new_mcp_token_bundle,
    encode_mcp_scopes_list,
)
from orcia_kernel.errors import ResourceNotFoundError


class SqlUserPreferencesAndMcpService:
    """PostgreSQL 18 persistence service for `user_preferences` and `user_mcp_tokens`."""

    def __init__(self, *, engine: AsyncEngine | None = None) -> None:
        self._engine = engine
        self._fallback: UserPreferencesAndMcpTokenService | None = (
            UserPreferencesAndMcpTokenService() if engine is None else None
        )

    async def _pg_tables_ready(self) -> bool:
        if self._engine is None:
            return False
        async with self._engine.connect() as conn:
            reg = (
                await conn.execute(sa.text("SELECT to_regclass('public.user_preferences')"))
            ).scalar()
            if reg is None:
                raise RuntimeError("PostgreSQL table 'public.user_preferences' is not migrated.")
            return True

    def _require_fallback(self) -> UserPreferencesAndMcpTokenService:
        assert self._fallback is not None, "RAM fallback is forbidden when AsyncEngine is wired."
        return self._fallback

    async def get_preferences(self, user_id: str) -> UserAccountPreferences:
        """Fetch user preferences from PostgreSQL 18 (or default record if absent)."""
        if not await self._pg_tables_ready():
            return self._require_fallback().get_preferences(user_id)
        assert self._engine is not None
        async with self._engine.connect() as conn:
            row = (await conn.execute(SQL_SELECT_PREFS, {"user_id": user_id})).first()
            return UserAccountPreferences(user_id=user_id) if row is None else row_to_prefs(row)

    async def update_preferences(
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
        """Upsert user preferences atomically in PostgreSQL 18."""
        if not await self._pg_tables_ready():
            return self._require_fallback().update_preferences(
                user_id=user_id,
                theme=theme,
                locale=locale,
                default_hat=default_hat,
                default_assistant_hat=default_assistant_hat,
                assistant_tone=assistant_tone,
                personal_instructions=personal_instructions,
                auto_open_contextual_help=auto_open_contextual_help,
                notifications_enabled=notifications_enabled,
            )
        assert self._engine is not None
        current = await self.get_preferences(user_id)
        next_hat = (
            default_assistant_hat
            if default_assistant_hat is not None
            else (default_hat if default_hat is not None else current.default_assistant_hat)
        )
        params = {
            "user_id": user_id,
            "theme": theme if theme is not None else current.theme,
            "locale": locale if locale is not None else current.locale,
            "default_assistant_hat": next_hat,
            "assistant_tone": (
                assistant_tone if assistant_tone is not None else current.assistant_tone
            ),
            "personal_instructions": (
                personal_instructions
                if personal_instructions is not None
                else current.personal_instructions
            ),
            "auto_open_help": (
                auto_open_contextual_help
                if auto_open_contextual_help is not None
                else current.auto_open_contextual_help
            ),
            "notifications_enabled": (
                notifications_enabled
                if notifications_enabled is not None
                else current.notifications_enabled
            ),
        }
        async with self._engine.begin() as conn:
            row = (await conn.execute(SQL_UPSERT_PREFS, params)).one()
            return row_to_prefs(row)

    async def list_user_mcp_tokens(self, user_id: str) -> tuple[ScopedMcpPersonalTokenRecord, ...]:
        """List all personal MCP token metadata rows for `user_id`."""
        if not await self._pg_tables_ready():
            return self._require_fallback().list_user_mcp_tokens(user_id)
        assert self._engine is not None
        async with self._engine.connect() as conn:
            rows = (await conn.execute(SQL_LIST_MCP_TOKENS, {"user_id": user_id})).fetchall()
            return tuple(row_to_mcp_record(r) for r in rows)

    async def issue_mcp_token(
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
        """Issue and store a hashed `pat_mcp_*` personal token in PostgreSQL 18."""
        if not await self._pg_tables_ready():
            return self._require_fallback().issue_mcp_token(
                user_id=user_id,
                label=label,
                expires_in_days=expires_in_days,
                rpm_limit=rpm_limit,
                allowed_workspace_slugs=allowed_workspace_slugs,
                exposed_capabilities=exposed_capabilities,
                target_kind=target_kind,
                target_slug=target_slug,
            )
        assert self._engine is not None
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
        rec = issued.record
        scopes_jsonb = json.dumps(
            encode_mcp_scopes_list(rec.allowed_workspace_slugs, rec.exposed_capabilities)
        )
        created_dt = (
            datetime.fromisoformat(rec.created_at_iso) if rec.created_at_iso else datetime.now()
        )
        expires_dt = datetime.fromisoformat(rec.expires_at_iso) if rec.expires_at_iso else None
        async with self._engine.begin() as conn:
            await conn.execute(
                SQL_INSERT_MCP_TOKEN,
                {
                    "id": UUID(rec.token_id),
                    "user_id": rec.user_id,
                    "label": rec.label,
                    "token_prefix": rec.token_prefix,
                    "token_sha256": rec.token_sha256,
                    "scopes_jsonb": scopes_jsonb,
                    "expires_in_days": rec.expires_in_days,
                    "rpm_limit": rec.rpm_limit,
                    "target_kind": rec.target_kind,
                    "target_slug": rec.target_slug,
                    "mcp_endpoint_uri": rec.mcp_endpoint_uri,
                    "ide_json_snippet": rec.ide_json_snippet,
                    "expires_at": expires_dt,
                    "created_at": created_dt,
                },
            )
        return issued

    async def revoke_mcp_token(
        self,
        *,
        user_id: str,
        token_id: str,
    ) -> ScopedMcpPersonalTokenRecord:
        """Revoke an existing MCP token strictly owned by `user_id`."""
        if not await self._pg_tables_ready():
            return self._require_fallback().revoke_mcp_token(user_id=user_id, token_id=token_id)
        assert self._engine is not None
        try:
            token_uuid = UUID(token_id)
        except ValueError as exc:
            raise ResourceNotFoundError(
                detail_override=f"Jeton MCP introuvable : {token_id}"
            ) from exc
        async with self._engine.begin() as conn:
            row = (
                await conn.execute(SQL_REVOKE_MCP_TOKEN, {"id": token_uuid, "user_id": user_id})
            ).first()
            if row is None:
                raise ResourceNotFoundError(detail_override=f"Jeton MCP introuvable : {token_id}")
            return row_to_mcp_record(row)
