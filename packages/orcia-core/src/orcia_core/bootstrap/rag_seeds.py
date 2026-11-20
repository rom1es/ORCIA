"""Bootstrap RAG & Tripartite demo dataset builder (`DEC-SEED-01`, `AD-20`).

Centralizes deterministic RAG/Tripartite test datasets inside `bootstrap` so that
`orcia_core.rag.__init__.py` contains zero hardcoded demo payloads (`AD-20` Rule 5).
"""

from __future__ import annotations

import asyncio
import concurrent.futures

from orcia_core.ports.embedding import EmbeddingPort
from orcia_core.rag.indexer_and_rrf import DifferentiatedIncrementalIndexer
from orcia_core.rag.tripartite_and_freshness import (
    HybridRagService,
    TripartiteGraphAndFreshnessService,
)


def populate_rag_test_dataset(
    rag: HybridRagService,
    tripartite: TripartiteGraphAndFreshnessService,
    *,
    workspace_id: str = "scope-global",
    embedding_port: EmbeddingPort | None = None,
) -> tuple[HybridRagService, TripartiteGraphAndFreshnessService]:
    """Populate `rag` and `tripartite` with deterministic test fixtures (`DEC-SEED-01`)."""
    conf_doc = None
    if embedding_port is not None:

        async def _seed_docs() -> None:
            nonlocal conf_doc
            (
                c_doc,
                conf_chunks,
            ) = await DifferentiatedIncrementalIndexer.index_confluence_parent_child(
                workspace_id=workspace_id,
                datasource_id="ds-confluence-claims",
                datasource_alias="confluence_claims",
                source_uri="confluence://CLAIMS/pages/101-spec-seuil-validation",
                title="Spécification Seuil Validation Sinistre",
                hierarchy_path="Espace CLAIMS > Règles Métier",
                markdown_sections=(
                    "Section 1 — Tout sinistre supérieur au seuil PAY-101 requiert validation.",
                    (
                        "Section 2 — La règle s'applique au concept LossEvent et à"
                        " calculate_reserve."
                    ),
                ),
                revision_tag="v12",
                embedding_port=embedding_port,
                labels=("orcia-kb",),
                ontology_concepts=("LossEvent",),
                freshness_ttl_days=90,
                age_days=120,
            )
            conf_doc = c_doc
            if c_doc is not None:
                rag.upsert_indexed_bundle(document=c_doc, chunks=conf_chunks)

            j_doc, jira_chunks = await DifferentiatedIncrementalIndexer.index_jira_reference_issue(
                workspace_id=workspace_id,
                datasource_id="ds-jira-claims",
                datasource_alias="jira_claims",
                issue_key="PAY-142",
                issue_type="Story",
                title="Relèvement du seuil de validation LossEvent de 5000 EUR à 7500 EUR",
                body_text=(
                    "Suite au comité risques, le ticket PAY-142 relève le seuil de"
                    " calculate_reserve pour LossEvent à 7500 EUR (remplace PAY-101)."
                ),
                updated_tag="2026-10-20T10:00:00Z",
                embedding_port=embedding_port,
                ontology_concepts=("LossEvent",),
            )
            if j_doc is not None:
                rag.upsert_indexed_bundle(document=j_doc, chunks=jira_chunks)

            ddl_doc, ddl_chunks = await DifferentiatedIncrementalIndexer.index_db_ddl_schema_only(
                workspace_id=workspace_id,
                datasource_id="ds-db-dwh",
                datasource_alias="db_claims_dwh",
                db_uri="db://claims-dwh/public/claim_events",
                ddl_sql=(
                    "CREATE TABLE claim_events (\n"
                    "    claim_id UUID PRIMARY KEY,\n"
                    "    exposure_amount NUMERIC(12, 2) NOT NULL\n"
                    ");"
                ),
                schema_version="2026.10.1",
                embedding_port=embedding_port,
                ontology_concepts=("LossEvent",),
            )
            rag.upsert_indexed_bundle(document=ddl_doc, chunks=ddl_chunks)

        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = None

        if loop is not None and loop.is_running():
            with concurrent.futures.ThreadPoolExecutor() as pool:
                pool.submit(lambda: asyncio.run(_seed_docs())).result()
        else:
            asyncio.run(_seed_docs())

    tripartite.register_cross_source_traceability(
        workspace_id=workspace_id,
        confluence_uri="confluence://CLAIMS/pages/101-spec-seuil-validation",
        confluence_text="Spécification initiale liée à PAY-101 et mise à jour par PAY-142.",
        git_repo_uri="git://claims/core-engine",
        git_symbol="calculate_reserve",
        commit_message="feat(claims): implement PAY-142 reserve threshold 7500 EUR",
        ontology_concept_key="LossEvent",
        fixed_jira_keys=("PAY-101",),
        blocked_jira_keys=("PAY-199",),
    )
    if conf_doc is not None:
        tripartite.evaluate_data_freshness(
            workspace_id=workspace_id,
            doc_key=conf_doc.doc_key,
            age_days=120,
            contradicting_done_jira_key="PAY-142",
            impacted_active_run_ids=("run-active-claims-01",),
        )

    return rag, tripartite


__all__ = ["populate_rag_test_dataset"]
