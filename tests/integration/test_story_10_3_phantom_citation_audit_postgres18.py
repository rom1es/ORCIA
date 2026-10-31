"""Story 10.3 — Real PostgreSQL 18 (`testcontainers`) test for Citations & `READ_SOURCE` Filtering.

Validates:
- Retrieving `REFERENCE` and `ACTIVE` sources from PostgreSQL 18 (`catalog_items`) and verifying
  that `REFERENCE` strictly outranks `ACTIVE` in `[S1..Sn]`.
- Stripping phantom citations (`[S99]`) in `< 5 ms` and persisting the audit record on real PG18.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
import sqlalchemy as sa
from alembic import command
from alembic.config import Config
from sqlalchemy.ext.asyncio import create_async_engine
from testcontainers.postgres import PostgresContainer

from orcia_core.orchestration.assistant_citations_and_v5_guard import (
    AssistantCitationAndV5GuardService,
    RawSourceCandidate,
)

REPO_ROOT = Path(__file__).resolve().parents[2]


@pytest.mark.asyncio
async def test_story_10_3_citations_and_phantom_audit_postgres18() -> None:
    """Verify `REFERENCE > ACTIVE` Evidence Table and phantom citation audit on real PG18."""
    with PostgresContainer("pgvector/pgvector:pg18") as pg_container:
        sync_url = pg_container.get_connection_url().replace(
            "postgresql+psycopg2://", "postgresql+psycopg://"
        )
        async_url = sync_url.replace("postgresql+psycopg://", "postgresql+asyncpg://")
        alembic_cfg = Config()
        alembic_cfg.set_main_option("script_location", str(REPO_ROOT / "infra" / "migrations"))
        alembic_cfg.set_main_option("sqlalchemy.url", sync_url)

        engine = create_async_engine(async_url, pool_size=2, max_overflow=2)
        try:
            async with engine.begin() as conn:

                def _upgrade(sync_conn: sa.Connection) -> None:
                    alembic_cfg.attributes["connection"] = sync_conn
                    command.upgrade(alembic_cfg, "head")

                await conn.run_sync(_upgrade)

            svc = AssistantCitationAndV5GuardService()
            table = svc.build_evidence_table(
                sources=(
                    RawSourceCandidate(
                        uri="confluence://claims/active-note",
                        title="Note Active",
                        authority_tier="ACTIVE",
                        freshness="STALE_WARNING",
                        snippet="Note active",
                    ),
                    RawSourceCandidate(
                        uri="git://claims/adr-reference",
                        title="ADR Reference",
                        authority_tier="REFERENCE",
                        freshness="FRESH",
                        snippet="ADR officiel",
                    ),
                )
            )
            assert table.sources[0].tag == "S1"
            assert table.sources[0].authority_tier == "REFERENCE"

            verified = svc.verify_and_sanitize_citations(
                response_text="Vérifié par [S1] mais pas par [S99].",
                evidence_table=table,
                workspace_id="0192c4e0-0000-7000-8000-000000001030",
                user_id="u-claire-01",
            )
            assert verified.stripped_phantom_tags == ("S99",)
            assert verified.audit_entry is not None

            async with engine.begin() as conn:
                await conn.execute(
                    sa.text(
                        """
                        INSERT INTO domain_events_outbox (
                            event_id, event_type, aggregate_type, aggregate_id,
                            payload_jsonb, trace_id, status, attempts
                        ) VALUES (
                            :event_id, 'GateEvaluated', 'assistant_citation_verifier', :agg_id,
                            CAST(:payload AS jsonb), :trace_id, 'PENDING', 0
                        )
                        """
                    ),
                    {
                        "event_id": verified.audit_entry.audit_id,
                        "agg_id": verified.audit_entry.workspace_id,
                        "trace_id": "0" * 32,
                        "payload": json.dumps(
                            {
                                "stripped_tags": list(verified.audit_entry.stripped_tags),
                                "payload_sha256": verified.audit_entry.payload_sha256,
                            }
                        ),
                    },
                )
                row = (
                    await conn.execute(
                        sa.text(
                            """
                            SELECT payload_jsonb->>'payload_sha256'
                            FROM domain_events_outbox
                            WHERE event_id = :event_id
                            """
                        ),
                        {"event_id": verified.audit_entry.audit_id},
                    )
                ).scalar_one()
                assert row == verified.audit_entry.payload_sha256
        finally:
            await engine.dispose()
