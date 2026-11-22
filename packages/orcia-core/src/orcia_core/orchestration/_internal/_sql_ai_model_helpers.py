"""Internal SQL Helpers for AI Model Mutations (`Story 17.5`, `Story 26.6a`)."""

from __future__ import annotations

from datetime import UTC, datetime

import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncConnection

from orcia_core.permissions.secret_hint import SecretStatusView


def now_iso() -> str:
    """Return current UTC timestamp in ISO-8601 `Z` format."""
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


def parse_iso_to_dt(iso_str: str | None) -> datetime | None:
    """Parse an optional ISO-8601 string into an aware datetime."""
    if not iso_str:
        return None
    try:
        return datetime.fromisoformat(iso_str.replace("Z", "+00:00"))
    except ValueError:
        return None


def secret_sql_params(sec: SecretStatusView, encrypted_key: str | None) -> dict[str, object]:
    """Build SQL parameter dictionary for masked/encrypted AI model secret columns."""
    return {
        "encrypted_api_key": encrypted_key,
        "secret_fingerprint": sec.fingerprint,
        "secret_masked_hint": sec.masked_hint,
        "secret_updated_at": parse_iso_to_dt(sec.updated_at) if sec.configured else None,
        "secret_updated_by": sec.updated_by if sec.configured else None,
    }


async def deactivate_other_global_embeddings(
    conn: AsyncConnection, exclude_id: str | None = None
) -> None:
    """Deactivate any previously active GLOBAL embedding mapping in PostgreSQL 18."""
    where_id = "id != :id AND " if exclude_id is not None else ""
    params = {"id": exclude_id} if exclude_id is not None else {}
    await conn.execute(
        sa.text(
            f"UPDATE workspace_llm_tier_mappings SET is_active = FALSE, updated_at = NOW() "
            f"WHERE {where_id}usage = 'embedding' AND scope_level = 'GLOBAL' AND is_active = TRUE"
        ),
        params,
    )
