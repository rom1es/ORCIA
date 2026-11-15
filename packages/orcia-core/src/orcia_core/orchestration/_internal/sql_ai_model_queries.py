"""PostgreSQL 18 query adapter for AI Model Mappings (`Story 17.5`, `AD-21`)."""

from __future__ import annotations

from typing import Any, cast
from urllib.parse import urlparse

import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncConnection

from orcia_core.orchestration.ai_models_crypto import unpack_encrypted_api_key
from orcia_core.orchestration.ai_models_records import (
    AiModelMappingRecord,
    HealthStatus,
    InferenceEffort,
    InferenceTier,
    LlmAuthMode,
    LlmModelUsage,
    LlmProtocolMode,
    ScopeLevel,
)
from orcia_core.orchestration.errors import ResourceNotFoundError
from orcia_core.permissions.crypto import PassthroughVaultCipher
from orcia_core.permissions.secret_hint import SecretStatusView

COLUMNS_SELECT = """
    id, scope_level, scope_id, inference_tier, effort, provider_slug, model_family,
    model_name, secret_ref, inference_params_jsonb, max_tokens_budget, max_cost_usd,
    fallback_order, is_active, draining, updated_at, display_name, fallback_model_name,
    endpoint_uri, auth_mode, protocol_mode, env_var_name, encrypted_api_key,
    secret_fingerprint, secret_masked_hint, secret_updated_at, secret_updated_by,
    health_status, last_tested_at, last_latency_ms, created_at, usage
"""


def row_to_mapping(row: Any) -> AiModelMappingRecord:
    has_secret = bool(row[22])
    sec_status = SecretStatusView(
        configured=has_secret,
        fingerprint=str(row[23]) if (has_secret and row[23]) else None,
        masked_hint=str(row[24]) if (has_secret and row[24]) else None,
        updated_at=row[25].isoformat() if (has_secret and row[25]) else "",
        updated_by=str(row[26]) if (has_secret and row[26]) else "system",
    )
    usage_val: LlmModelUsage = (
        cast(LlmModelUsage, str(row[31])) if len(row) > 31 and row[31] else "chat"
    )
    return AiModelMappingRecord(
        id=str(row[0]),
        scope_level=cast(ScopeLevel, str(row[1])),
        scope_id=str(row[2]),
        inference_tier=cast(InferenceTier, str(row[3])),
        effort=cast(InferenceEffort, str(row[4])),
        provider_slug=str(row[5]),
        model_family=str(row[6]),
        model_name=str(row[7]),
        max_tokens_budget=int(row[10]),
        max_cost_usd=float(row[11]),
        fallback_order=int(row[12]),
        is_active=bool(row[13]),
        draining=bool(row[14]),
        updated_at=row[15].isoformat() if row[15] else "",
        display_name=str(row[16]) if row[16] else f"{row[5]} / {row[7]}",
        fallback_model_name=str(row[17]) if row[17] else None,
        endpoint_uri=str(row[18]) if row[18] else "",
        auth_mode=cast(LlmAuthMode, str(row[19]) if row[19] else "api_key"),
        protocol_mode=cast(LlmProtocolMode, str(row[20]) if row[20] else "openai_compatible"),
        usage=usage_val,
        env_var_name=str(row[21]) if row[21] else None,
        encrypted_api_key=str(row[22]) if row[22] else None,
        health_status=cast(HealthStatus, str(row[27]) if row[27] else "UNTESTED"),
        last_tested_at=row[28].isoformat() if row[28] else None,
        last_latency_ms=int(row[29]) if row[29] is not None else None,
        created_at=row[30].isoformat() if row[30] else "",
        secret_status=sec_status,
    )


async def ensure_ai_model_mappings_schema_on_postgres18(conn: AsyncConnection) -> None:
    """Ensure table and additive columns exist on PostgreSQL 18."""
    await conn.execute(
        sa.text(
            """
            CREATE TABLE IF NOT EXISTS workspace_llm_tier_mappings (
                id UUID PRIMARY KEY,
                scope_level VARCHAR(32) NOT NULL DEFAULT 'WORKSPACE',
                scope_id UUID NOT NULL,
                inference_tier VARCHAR(32) NOT NULL,
                effort VARCHAR(32) NOT NULL DEFAULT 'default',
                provider_slug VARCHAR(64) NOT NULL,
                model_family VARCHAR(64) NOT NULL,
                model_name VARCHAR(128) NOT NULL,
                secret_ref UUID NULL,
                inference_params_jsonb JSONB NOT NULL DEFAULT '{}'::jsonb,
                max_tokens_budget INTEGER NOT NULL DEFAULT 8192,
                max_cost_usd NUMERIC(12, 6) NOT NULL DEFAULT 10.000000,
                fallback_order INTEGER NOT NULL DEFAULT 1,
                is_active BOOLEAN NOT NULL DEFAULT TRUE,
                draining BOOLEAN NOT NULL DEFAULT FALSE,
                updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                display_name VARCHAR(160) NOT NULL DEFAULT '',
                fallback_model_name VARCHAR(128) NULL,
                endpoint_uri TEXT NOT NULL DEFAULT '',
                auth_mode VARCHAR(32) NOT NULL DEFAULT 'api_key',
                protocol_mode VARCHAR(32) NOT NULL DEFAULT 'openai_compatible',
                env_var_name VARCHAR(128) NULL,
                encrypted_api_key TEXT NULL,
                secret_fingerprint VARCHAR(64) NULL,
                secret_masked_hint VARCHAR(32) NULL,
                secret_updated_at TIMESTAMPTZ NULL,
                secret_updated_by VARCHAR(128) NULL,
                health_status VARCHAR(32) NOT NULL DEFAULT 'UNTESTED',
                last_tested_at TIMESTAMPTZ NULL,
                last_latency_ms INTEGER NULL,
                created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                usage VARCHAR(32) NOT NULL DEFAULT 'chat'
            )
            """
        )
    )
    await conn.execute(
        sa.text(
            """
            ALTER TABLE workspace_llm_tier_mappings
                ADD COLUMN IF NOT EXISTS display_name VARCHAR(160) NOT NULL DEFAULT '',
                ADD COLUMN IF NOT EXISTS fallback_model_name VARCHAR(128) NULL,
                ADD COLUMN IF NOT EXISTS endpoint_uri TEXT NOT NULL DEFAULT '',
                ADD COLUMN IF NOT EXISTS auth_mode VARCHAR(32) NOT NULL DEFAULT 'api_key',
                ADD COLUMN IF NOT EXISTS protocol_mode VARCHAR(32)
                    NOT NULL DEFAULT 'openai_compatible',
                ADD COLUMN IF NOT EXISTS env_var_name VARCHAR(128) NULL,
                ADD COLUMN IF NOT EXISTS encrypted_api_key TEXT NULL,
                ADD COLUMN IF NOT EXISTS secret_fingerprint VARCHAR(64) NULL,
                ADD COLUMN IF NOT EXISTS secret_masked_hint VARCHAR(32) NULL,
                ADD COLUMN IF NOT EXISTS secret_updated_at TIMESTAMPTZ NULL,
                ADD COLUMN IF NOT EXISTS secret_updated_by VARCHAR(128) NULL,
                ADD COLUMN IF NOT EXISTS health_status VARCHAR(32) NOT NULL DEFAULT 'UNTESTED',
                ADD COLUMN IF NOT EXISTS last_tested_at TIMESTAMPTZ NULL,
                ADD COLUMN IF NOT EXISTS last_latency_ms INTEGER NULL,
                ADD COLUMN IF NOT EXISTS created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                ADD COLUMN IF NOT EXISTS usage VARCHAR(32) NOT NULL DEFAULT 'chat'
            """
        )
    )
    await conn.execute(
        sa.text(
            """
            CREATE INDEX IF NOT EXISTS idx_llm_tier_mappings_scope_tier_active
                ON workspace_llm_tier_mappings (scope_level, inference_tier, is_active)
            """
        )
    )
    await conn.execute(
        sa.text(
            """
            CREATE UNIQUE INDEX IF NOT EXISTS idx_llm_tier_mappings_single_active_global_embedding
                ON workspace_llm_tier_mappings (scope_level, usage)
                WHERE (usage = 'embedding' AND is_active = TRUE AND scope_level = 'GLOBAL')
            """
        )
    )


async def list_ai_model_mappings_pg18(
    conn: AsyncConnection,
    *,
    scope_level: ScopeLevel | None = None,
    scope_id: str | None = None,
    inference_tier: InferenceTier | None = None,
    is_active: bool | None = None,
    usage: LlmModelUsage | None = None,
) -> list[AiModelMappingRecord]:
    """Query mappings with optional filters ordered deterministically."""
    clauses = ["1=1"]
    params: dict[str, Any] = {}
    if scope_level is not None:
        clauses.append("scope_level = :scope_level")
        params["scope_level"] = scope_level
    if scope_id is not None:
        clauses.append("scope_id = :scope_id")
        params["scope_id"] = scope_id
    if inference_tier is not None:
        clauses.append("inference_tier = :inference_tier")
        params["inference_tier"] = inference_tier
    if is_active is not None:
        clauses.append("is_active = :is_active")
        params["is_active"] = is_active
    if usage is not None:
        clauses.append("usage = :usage")
        params["usage"] = usage
    where_sql = " AND ".join(clauses)
    query = sa.text(
        f"SELECT {COLUMNS_SELECT} FROM workspace_llm_tier_mappings "
        f"WHERE {where_sql} ORDER BY inference_tier, fallback_order, created_at"
    )
    res = await conn.execute(query, params)
    return [row_to_mapping(row) for row in res.fetchall()]


async def get_ai_model_mapping_pg18(
    conn: AsyncConnection, mapping_id: str, *, instance: str | None = None
) -> AiModelMappingRecord:
    """Fetch a single mapping by primary key UUIDv7."""
    res = await conn.execute(
        sa.text(f"SELECT {COLUMNS_SELECT} FROM workspace_llm_tier_mappings WHERE id = :id"),
        {"id": mapping_id},
    )
    row = res.fetchone()
    if row is None:
        raise ResourceNotFoundError(
            detail_override=f"AI model mapping '{mapping_id}' not found.", instance=instance
        )
    return row_to_mapping(row)


async def resolve_decrypted_ai_model_for_tier_pg18(
    conn: AsyncConnection,
    *,
    cipher: PassthroughVaultCipher,
    scope_id: str,
    inference_tier: str,
    effort: str = "default",
) -> tuple[AiModelMappingRecord, str | None] | None:
    """Resolve active model mapping with decrypted API key for runtime assistant execution."""
    _ = effort
    res = await conn.execute(
        sa.text(
            f"""
            SELECT {COLUMNS_SELECT} FROM workspace_llm_tier_mappings
            WHERE (scope_id = :scope_id OR scope_level = 'GLOBAL')
              AND inference_tier = :tier
              AND is_active = TRUE
              AND draining = FALSE
            ORDER BY fallback_order ASC, created_at ASC
            LIMIT 1
            """
        ),
        {"scope_id": scope_id, "tier": inference_tier},
    )
    row = res.fetchone()
    if row is None:
        return None
    rec = row_to_mapping(row)
    decrypted_key: str | None = None
    if rec.encrypted_api_key:
        host = urlparse(rec.endpoint_uri).netloc or "default"
        decrypted_key = unpack_encrypted_api_key(
            cipher, mapping_id=rec.id, packed=rec.encrypted_api_key, target_host=host
        )
    return rec, decrypted_key


async def get_active_global_embedding_model_pg18(
    conn: AsyncConnection,
    *,
    cipher: PassthroughVaultCipher,
) -> tuple[AiModelMappingRecord, str | None] | None:
    """Resolve active global embedding model mapping with decrypted API key."""
    res = await conn.execute(
        sa.text(
            f"""
            SELECT {COLUMNS_SELECT} FROM workspace_llm_tier_mappings
            WHERE usage = 'embedding'
              AND scope_level = 'GLOBAL'
              AND is_active = TRUE
              AND draining = FALSE
            ORDER BY created_at DESC
            LIMIT 1
            """
        )
    )
    row = res.fetchone()
    if row is None:
        return None
    rec = row_to_mapping(row)
    decrypted_key: str | None = None
    if rec.encrypted_api_key:
        host = urlparse(rec.endpoint_uri).netloc or "default"
        decrypted_key = unpack_encrypted_api_key(
            cipher, mapping_id=rec.id, packed=rec.encrypted_api_key, target_host=host
        )
    return rec, decrypted_key


__all__ = [
    "COLUMNS_SELECT",
    "ensure_ai_model_mappings_schema_on_postgres18",
    "get_active_global_embedding_model_pg18",
    "get_ai_model_mapping_pg18",
    "list_ai_model_mappings_pg18",
    "resolve_decrypted_ai_model_for_tier_pg18",
    "row_to_mapping",
]
