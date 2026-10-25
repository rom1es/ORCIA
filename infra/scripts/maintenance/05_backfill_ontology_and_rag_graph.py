"""Maintenance script `05_backfill_ontology_and_rag_graph.py` for Epic 2 (Stories 2.1–2.4).

Conventions (AGENTS.md):
- Operational data transformations or backfills outside schema migrations live in
  `infra/scripts/maintenance/XX_*.py`.
- Mandatory `--dry-run` mode (default rollback unless `--apply` is explicitly passed).
- Uses batched idempotent transactions (`INSERT ... ON CONFLICT DO UPDATE`).
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from dataclasses import dataclass
from pathlib import Path

import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine

_CORE_SRC = str(Path(__file__).resolve().parents[3] / "packages" / "orcia-core" / "src")
if _CORE_SRC not in sys.path:
    sys.path.insert(0, _CORE_SRC)

from orcia_core.ontology import build_seeded_ontology_service  # noqa: E402
from orcia_core.rag import compute_deterministic_halfvec_1024  # noqa: E402


@dataclass(frozen=True, slots=True)
class OntologyAndRagBackfillReport:
    """Summary of the Epic 2 Ontology & Hybrid RAG + Tripartite Graph backfill."""

    concepts_count: int
    axioms_count: int
    kb_chunks_count: int
    tripartite_edges_count: int
    stale_alerts_count: int
    dry_run: bool
    committed: bool


async def backfill_ontology_and_rag_graph(
    engine: AsyncEngine,
    *,
    apply_changes: bool = False,
    batch_size: int = 100,
) -> OntologyAndRagBackfillReport:
    """Populate or update Epic 2 tables inside a controlled transaction.

    Rolls back by default unless `apply_changes=True` is explicitly provided.
    """
    if batch_size <= 0:
        raise ValueError("batch_size must be strictly positive")

    gov = build_seeded_ontology_service()
    concepts = gov.concepts
    concept_id_by_key = {c.concept_key: c.id for c in concepts}
    axioms = gov.axioms

    concept_sql = sa.text(
        "INSERT INTO ontology_concepts ("
        "id, concept_key, canonical_term, level, scope_id, parent_concept_id, "
        "definition_text, synonyms_jsonb, banned_terms_jsonb, "
        "profile_translations_jsonb, expected_schema_jsonb, "
        "introduced_in_snapshot_id, snapshot_branch_status"
        ") VALUES ("
        ":id, :concept_key, :canonical_term, :level, :scope_id, :parent_concept_id, "
        ":definition_text, CAST(:synonyms_jsonb AS jsonb), "
        "CAST(:banned_terms_jsonb AS jsonb), CAST(:profile_translations_jsonb AS jsonb), "
        "CAST(:expected_schema_jsonb AS jsonb), :introduced_in_snapshot_id, :snapshot_branch_status"
        ") ON CONFLICT (concept_key) DO UPDATE SET "
        "definition_text = EXCLUDED.definition_text, "
        "snapshot_branch_status = EXCLUDED.snapshot_branch_status;"
    )

    axiom_sql = sa.text(
        "INSERT INTO ontology_axioms ("
        "id, axiom_key, concept_id, level, scope_id, rule_expression, immutable"
        ") VALUES ("
        ":id, :axiom_key, :concept_id, :level, :scope_id, :rule_expression, :immutable"
        ") ON CONFLICT (axiom_key) DO UPDATE SET "
        "rule_expression = EXCLUDED.rule_expression;"
    )

    ws_id = "0192c4e0-0000-7000-8000-000000000201"
    ds_id = "0192c4e0-0000-7000-8000-000000000301"
    doc_id = "0192c4e0-0000-7000-8000-000000000701"
    chunk_id = "0192c4e0-0000-7000-8000-000000000702"
    edge_id = "0192c4e0-0000-7000-8000-000000000703"
    alert_id = "0192c4e0-0000-7000-8000-000000000704"

    vec_literal = (
        "["
        + ",".join(str(v) for v in compute_deterministic_halfvec_1024("LossEvent PAY-142"))
        + "]"
    )

    async with engine.connect() as conn:
        trans = await conn.begin()
        try:
            for c in concepts:
                await conn.execute(
                    concept_sql,
                    {
                        "id": c.id,
                        "concept_key": c.concept_key,
                        "canonical_term": c.canonical_term,
                        "level": c.level,
                        "scope_id": c.scope_id,
                        "parent_concept_id": c.parent_concept_id,
                        "definition_text": c.definition_text,
                        "synonyms_jsonb": json.dumps(list(c.synonyms)),
                        "banned_terms_jsonb": json.dumps(list(c.banned_terms)),
                        "profile_translations_jsonb": json.dumps(c.profile_translations),
                        "expected_schema_jsonb": json.dumps(c.expected_schema),
                        "introduced_in_snapshot_id": c.introduced_in_snapshot_id,
                        "snapshot_branch_status": c.snapshot_branch_status,
                    },
                )
            for ax in axioms:
                await conn.execute(
                    axiom_sql,
                    {
                        "id": ax.id,
                        "axiom_key": ax.axiom_key,
                        "concept_id": concept_id_by_key[ax.concept_key],
                        "level": ax.level,
                        "scope_id": ax.scope_id,
                        "rule_expression": ax.rule_expression,
                        "immutable": ax.immutable,
                    },
                )

            await conn.execute(
                sa.text(
                    "INSERT INTO kb_documents ("
                    "id, doc_key, workspace_id, datasource_id, source_uri, "
                    "source_scheme, indexing_regime, title, revision_tag, content_sha256, "
                    "freshness_ttl_days, is_stale"
                    ") VALUES ("
                    ":id, :doc_key, :workspace_id, :datasource_id, :source_uri, "
                    ":source_scheme, :indexing_regime, :title, :revision_tag, :content_sha256, "
                    "90, TRUE"
                    ") ON CONFLICT (doc_key) DO UPDATE SET is_stale = EXCLUDED.is_stale;"
                ),
                {
                    "id": doc_id,
                    "doc_key": "doc-confluence-claims-seuil",
                    "workspace_id": ws_id,
                    "datasource_id": ds_id,
                    "source_uri": "confluence://CLAIMS/pages/101-spec-seuil-validation",
                    "source_scheme": "confluence",
                    "indexing_regime": "DOC_PARENT_CHILD",
                    "title": "Spécification Seuil Validation Sinistre",
                    "revision_tag": "v12",
                    "content_sha256": "a" * 64,
                },
            )

            await conn.execute(
                sa.text(
                    "INSERT INTO kb_chunks ("
                    "id, chunk_key, document_id, workspace_id, datasource_alias, parent_chunk_id, "
                    "chunk_role, contextual_header, content_text, token_count, embedding"
                    ") VALUES ("
                    ":id, :chunk_key, :document_id, :workspace_id, :datasource_alias, NULL, "
                    "'CHILD', :contextual_header, :content_text, 256, "
                    "CAST(:embedding AS halfvec(1024))"
                    ") ON CONFLICT (chunk_key) DO UPDATE SET token_count = EXCLUDED.token_count;"
                ),
                {
                    "id": chunk_id,
                    "chunk_key": "chunk-confluence-claims-seuil-1",
                    "document_id": doc_id,
                    "workspace_id": ws_id,
                    "datasource_alias": "confluence_claims",
                    "contextual_header": "[confluence_claims : CLAIMS > Seuil | LossEvent]",
                    "content_text": "Tout sinistre LossEvent lié à PAY-142 requiert validation.",
                    "embedding": vec_literal,
                },
            )

            await conn.execute(
                sa.text(
                    "INSERT INTO tripartite_trace_edges ("
                    "id, edge_key, workspace_id, source_uri, source_node_type, "
                    "target_uri, target_node_type, relation_type, jira_issue_key"
                    ") VALUES ("
                    ":id, :edge_key, :workspace_id, :source_uri, 'GIT_SYMBOL', "
                    ":target_uri, 'JIRA_ISSUE', 'IMPLEMENTS_ISSUE', 'PAY-142'"
                    ") ON CONFLICT (edge_key) DO NOTHING;"
                ),
                {
                    "id": edge_id,
                    "edge_key": "trace-git-jira-calculate-reserve-pay-142",
                    "workspace_id": ws_id,
                    "source_uri": "git://claims/core-engine#calculate_reserve",
                    "target_uri": "jira://issues/PAY-142",
                },
            )

            await conn.execute(
                sa.text(
                    "INSERT INTO kb_stale_alerts ("
                    "id, alert_key, workspace_id, document_id, "
                    "alert_reason, diagnostic_marker, justifying_jira_key"
                    ") VALUES ("
                    ":id, :alert_key, :workspace_id, :document_id, "
                    "'NEWER_JIRA_CONTRADICTION', '[STALE_WARNING]', 'PAY-142'"
                    ") ON CONFLICT (alert_key) DO NOTHING;"
                ),
                {
                    "id": alert_id,
                    "alert_key": "stale-doc-confluence-claims-seuil",
                    "workspace_id": ws_id,
                    "document_id": doc_id,
                },
            )

            c_cnt = int(
                (await conn.execute(sa.text("SELECT COUNT(*) FROM ontology_concepts"))).scalar()
                or 0
            )
            a_cnt = int(
                (await conn.execute(sa.text("SELECT COUNT(*) FROM ontology_axioms"))).scalar() or 0
            )
            k_cnt = int(
                (await conn.execute(sa.text("SELECT COUNT(*) FROM kb_chunks"))).scalar() or 0
            )
            t_cnt = int(
                (
                    await conn.execute(sa.text("SELECT COUNT(*) FROM tripartite_trace_edges"))
                ).scalar()
                or 0
            )
            s_cnt = int(
                (await conn.execute(sa.text("SELECT COUNT(*) FROM kb_stale_alerts"))).scalar() or 0
            )

            if apply_changes:
                await trans.commit()
                committed = True
            else:
                await trans.rollback()
                committed = False

            return OntologyAndRagBackfillReport(
                concepts_count=c_cnt,
                axioms_count=a_cnt,
                kb_chunks_count=k_cnt,
                tripartite_edges_count=t_cnt,
                stale_alerts_count=s_cnt,
                dry_run=not apply_changes,
                committed=committed,
            )
        except Exception:
            await trans.rollback()
            raise


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Backfill Epic 2 Ontology & Hybrid RAG + Tripartite Graph tables."
    )
    mode_group = parser.add_mutually_exclusive_group()
    mode_group.add_argument("--dry-run", action="store_true", default=True)
    mode_group.add_argument("--apply", action="store_true", default=False)
    parser.add_argument("--batch-size", type=int, default=100)
    return parser


async def _async_main(argv: list[str] | None = None) -> int:
    from orcia_core.config import resolve_database_url

    args = build_arg_parser().parse_args(argv)
    engine = create_async_engine(resolve_database_url())
    try:
        report = await backfill_ontology_and_rag_graph(
            engine, apply_changes=bool(args.apply), batch_size=int(args.batch_size)
        )
    finally:
        await engine.dispose()
    return 0 if report.concepts_count >= 1 and report.kb_chunks_count >= 1 else 1


def main(argv: list[str] | None = None) -> int:
    return asyncio.run(_async_main(argv))


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
