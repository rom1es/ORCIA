"""Row mappers & root org helper for `SqlMcpExposureRepository` (`Story 24.3`)."""

from __future__ import annotations

import json
from typing import Any, cast
from uuid import UUID

import sqlalchemy as sa
from sqlalchemy.engine import RowMapping
from sqlalchemy.ext.asyncio import AsyncSession

from orcia_core.orchestration.remote_test_bench_models import (
    ExposedMcpAgentSpec,
    McpExposureRegime,
)

_ROOT_ORG_UNIT_ID = UUID("0192c4e0-0000-7000-8000-000000000001")
_SELECT_AGENT_COLS = (
    "workspace_slug, agent_slug, display_name, mcp_exposed, regime, "
    "system_prompt_layers_1_to_4, secret_refs_jsonb, human_authored_required"
)


def _parse_str_tuple(raw: Any) -> tuple[str, ...]:
    if isinstance(raw, str):
        parsed = json.loads(raw) if raw else []
        return tuple(str(x) for x in parsed) if isinstance(parsed, list) else ()
    if isinstance(raw, list):
        return tuple(str(x) for x in raw)
    return ()


def _row_to_spec(row: RowMapping) -> ExposedMcpAgentSpec:
    regime_raw = str(row["regime"])
    regime: McpExposureRegime = (
        cast(McpExposureRegime, regime_raw)
        if regime_raw in ("CONSULTATION_ANALYSIS", "GOVERNED_STAGED_COPILOT")
        else "CONSULTATION_ANALYSIS"
    )
    return ExposedMcpAgentSpec(
        agent_slug=str(row["agent_slug"]),
        workspace_slug=str(row["workspace_slug"]),
        display_name=str(row["display_name"]),
        mcp_exposed=bool(row["mcp_exposed"]),
        regime=regime,
        system_prompt_layers_1_to_4=str(row["system_prompt_layers_1_to_4"] or ""),
        secret_refs=_parse_str_tuple(row["secret_refs_jsonb"]),
        human_authored_required=bool(row["human_authored_required"]),
    )


async def _ensure_root_org_unit_id(session: AsyncSession) -> UUID:
    row = (
        await session.execute(
            sa.text(
                """
                SELECT id FROM org_units
                ORDER BY (CASE WHEN unit_type = 'ENTERPRISE' THEN 0 ELSE 1 END), id ASC
                LIMIT 1
                """
            )
        )
    ).first()
    if row is not None and row[0] is not None:
        return UUID(str(row[0]))
    await session.execute(
        sa.text(
            """
            INSERT INTO org_units (id, slug, name, unit_type, parent_id)
            VALUES (:id, 'orcia-root', 'ORCIA Root Organization', 'ENTERPRISE', NULL)
            ON CONFLICT (slug) DO NOTHING
            """
        ),
        {"id": _ROOT_ORG_UNIT_ID},
    )
    created = (
        await session.execute(sa.text("SELECT id FROM org_units WHERE slug = 'orcia-root' LIMIT 1"))
    ).scalar_one()
    return UUID(str(created))


__all__ = [
    "_SELECT_AGENT_COLS",
    "_ensure_root_org_unit_id",
    "_parse_str_tuple",
    "_row_to_spec",
]
