"""SQL constants and row mappers for `sql_user_preferences.py` (`Story 20.3`)."""

from __future__ import annotations

import json
from datetime import datetime
from typing import Any, cast

import sqlalchemy as sa

from orcia_core.permissions.user_preferences_and_mcp_tokens import (
    ASSISTANT_BEHAVIOR_REDIRECT_URI,
    AssistantToneMode,
    McpExpirationDays,
    McpTargetKind,
    ScopedMcpPersonalTokenRecord,
    UserAccountPreferences,
    UserLocaleCode,
    UserThemeMode,
    decode_mcp_scopes_list,
)

SQL_SELECT_PREFS = sa.text(
    """
    SELECT user_id, theme, locale, default_assistant_hat, assistant_tone,
           personal_instructions, auto_open_help, notifications_enabled
    FROM user_preferences
    WHERE user_id = :user_id
    """
)

SQL_UPSERT_PREFS = sa.text(
    """
    INSERT INTO user_preferences (
        user_id, theme, locale, default_assistant_hat, assistant_tone,
        personal_instructions, auto_open_help, notifications_enabled, updated_at
    )
    VALUES (
        :user_id, :theme, :locale, :default_assistant_hat, :assistant_tone,
        :personal_instructions, :auto_open_help, :notifications_enabled, NOW()
    )
    ON CONFLICT (user_id) DO UPDATE SET
        theme = EXCLUDED.theme,
        locale = EXCLUDED.locale,
        default_assistant_hat = EXCLUDED.default_assistant_hat,
        assistant_tone = EXCLUDED.assistant_tone,
        personal_instructions = EXCLUDED.personal_instructions,
        auto_open_help = EXCLUDED.auto_open_help,
        notifications_enabled = EXCLUDED.notifications_enabled,
        updated_at = NOW()
    RETURNING user_id, theme, locale, default_assistant_hat, assistant_tone,
              personal_instructions, auto_open_help, notifications_enabled
    """
)

SQL_INSERT_MCP_TOKEN = sa.text(
    """
    INSERT INTO user_mcp_tokens (
        id, user_id, label, token_prefix, token_sha256, scopes_jsonb,
        expires_in_days, rpm_limit, target_kind, target_slug,
        mcp_endpoint_uri, ide_json_snippet, expires_at, revoked_at, created_at
    )
    VALUES (
        :id, :user_id, :label, :token_prefix, :token_sha256, CAST(:scopes_jsonb AS JSONB),
        :expires_in_days, :rpm_limit, :target_kind, :target_slug,
        :mcp_endpoint_uri, :ide_json_snippet, :expires_at, NULL, :created_at
    )
    """
)

SQL_LIST_MCP_TOKENS = sa.text(
    """
    SELECT id, user_id, label, token_prefix, token_sha256, scopes_jsonb,
           expires_in_days, rpm_limit, target_kind, target_slug,
           mcp_endpoint_uri, ide_json_snippet, expires_at, revoked_at, created_at
    FROM user_mcp_tokens
    WHERE user_id = :user_id
    ORDER BY created_at DESC
    """
)

SQL_REVOKE_MCP_TOKEN = sa.text(
    """
    UPDATE user_mcp_tokens
    SET revoked_at = COALESCE(revoked_at, NOW())
    WHERE id = :id AND user_id = :user_id
    RETURNING id, user_id, label, token_prefix, token_sha256, scopes_jsonb,
              expires_in_days, rpm_limit, target_kind, target_slug,
              mcp_endpoint_uri, ide_json_snippet, expires_at, revoked_at, created_at
    """
)


def _iso_or_none(val: Any) -> str | None:
    if val is None:
        return None
    if isinstance(val, datetime):
        return val.isoformat()
    return str(val)


def row_to_prefs(row: Any) -> UserAccountPreferences:
    """Map a `user_preferences` row to `UserAccountPreferences`."""
    hat = str(row[3])
    return UserAccountPreferences(
        user_id=str(row[0]),
        theme=cast(UserThemeMode, str(row[1])),
        locale=cast(UserLocaleCode, str(row[2])),
        default_hat=hat,
        default_assistant_hat=hat,
        assistant_tone=cast(AssistantToneMode, str(row[4])),
        personal_instructions=str(row[5]),
        auto_open_contextual_help=bool(row[6]),
        notifications_enabled=bool(row[7]),
        assistant_behavior_redirect_uri=ASSISTANT_BEHAVIOR_REDIRECT_URI,
    )


def row_to_mcp_record(row: Any) -> ScopedMcpPersonalTokenRecord:
    """Map a `user_mcp_tokens` row to `ScopedMcpPersonalTokenRecord`."""
    raw_scopes = row[5]
    scopes_list = (
        json.loads(raw_scopes)
        if isinstance(raw_scopes, str)
        else (list(raw_scopes) if isinstance(raw_scopes, list) else [])
    )
    ws_slugs, caps = decode_mcp_scopes_list([str(s) for s in scopes_list])
    exp_days: McpExpirationDays = 90 if int(row[6]) == 90 else 30
    target_kind: McpTargetKind = "AGENT" if str(row[8]) == "AGENT" else "SPACE"
    revoked_at = row[13]
    return ScopedMcpPersonalTokenRecord(
        token_id=str(row[0]),
        user_id=str(row[1]),
        label=str(row[2]),
        token_prefix=str(row[3]),
        token_sha256=str(row[4]),
        expires_in_days=exp_days,
        rpm_limit=int(row[7]),
        allowed_workspace_slugs=ws_slugs,
        exposed_capabilities=caps,
        target_kind=target_kind,
        target_slug=str(row[9]),
        mcp_endpoint_uri=str(row[10]),
        ide_json_snippet=str(row[11]),
        revoked=revoked_at is not None,
        created_at_iso=_iso_or_none(row[14]),
        expires_at_iso=_iso_or_none(row[12]),
        revoked_at_iso=_iso_or_none(revoked_at),
    )
