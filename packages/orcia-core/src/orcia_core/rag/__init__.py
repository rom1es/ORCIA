"""Differentiated Hybrid RAG (`halfvec(1024)` + BM25) & Tripartite Graph package (`AD-8`).

By default in runtime (`build_empty_rag_service()`), the system is 100% empty of sample data.
`build_seeded_rag_service()` is strictly reserved for automated tests (`pytest` / `Vitest`).
"""

from __future__ import annotations

from orcia_core.rag.indexer_and_rrf import (
    ALLOWED_JIRA_REFERENCE_TYPES,
    EMBEDDING_DIM,
    DifferentiatedIncrementalIndexer,
    build_contextual_header,
    compute_deterministic_halfvec_1024,
    cosine_similarity,
)
from orcia_core.rag.models import (
    ChunkRole,
    CodeGraphEdgeEntity,
    CodeGraphEdgeType,
    DocVsCodeAuditFinding,
    HybridRagHit,
    IndexingRegime,
    KbChunkEntity,
    KbDocumentEntity,
    KbStaleAlertEntity,
    StaleAlertReason,
    TripartiteNodeType,
    TripartiteRelationType,
    TripartiteTraceEdgeEntity,
)
from orcia_core.rag.tripartite_and_freshness import (
    HybridRagService,
    TripartiteGraphAndFreshnessService,
    extract_jira_issue_keys,
)

DOMAIN_NAME: str = "rag"


def build_empty_rag_service() -> tuple[HybridRagService, TripartiteGraphAndFreshnessService]:
    """Return an empty Hybrid RAG & Tripartite Graph bundle (default runtime state: 0 rows)."""
    rag = HybridRagService()
    tripartite = TripartiteGraphAndFreshnessService(rag_service=rag)
    return rag, tripartite


def build_seeded_rag_service(
    *, workspace_id: str = "ws-claims-alpha"
) -> tuple[HybridRagService, TripartiteGraphAndFreshnessService]:
    """Return a deterministic Hybrid RAG & Tripartite Graph bundle strictly for automated tests."""
    rag, tripartite = build_empty_rag_service()

    conf_doc, conf_chunks = DifferentiatedIncrementalIndexer.index_confluence_parent_child(
        workspace_id=workspace_id,
        datasource_id="ds-confluence-claims",
        datasource_alias="confluence_claims",
        source_uri="confluence://CLAIMS/pages/101-spec-seuil-validation",
        title="Spécification Seuil Validation Sinistre",
        hierarchy_path="Espace CLAIMS > Règles Métier",
        markdown_sections=(
            "Section 1 — Tout sinistre supérieur au seuil PAY-101 requiert validation.",
            "Section 2 — La règle s'applique au concept LossEvent et à calculate_reserve.",
        ),
        revision_tag="v12",
        labels=("orcia-kb",),
        ontology_concepts=("LossEvent",),
        freshness_ttl_days=90,
        age_days=120,
    )
    if conf_doc is not None:
        rag.upsert_indexed_bundle(document=conf_doc, chunks=conf_chunks)

    jira_doc, jira_chunks = DifferentiatedIncrementalIndexer.index_jira_reference_issue(
        workspace_id=workspace_id,
        datasource_id="ds-jira-claims",
        datasource_alias="jira_claims",
        issue_key="PAY-142",
        issue_type="Story",
        title="Relèvement du seuil de validation LossEvent de 5000 EUR à 7500 EUR",
        body_text=(
            "Suite au comité risques, le ticket PAY-142 relève le seuil de calculate_reserve "
            "pour LossEvent à 7500 EUR (remplace PAY-101)."
        ),
        updated_tag="2026-10-20T10:00:00Z",
        ontology_concepts=("LossEvent",),
    )
    if jira_doc is not None:
        rag.upsert_indexed_bundle(document=jira_doc, chunks=jira_chunks)

    git_doc, git_chunks, git_edges = DifferentiatedIncrementalIndexer.index_git_ast_and_code_graph(
        workspace_id=workspace_id,
        datasource_id="ds-git-core",
        datasource_alias="git_core",
        repo_uri="git://claims/core-engine",
        file_path="src/claims/reserve.py",
        python_source=(
            "import decimal\n\n"
            "def validate_threshold(amount: float) -> bool:\n"
            "    return amount >= 7500.0\n\n"
            "def calculate_reserve(amount: float) -> float:\n"
            "    if validate_threshold(amount):\n"
            "        return amount * 1.15\n"
            "    return amount\n"
        ),
        commit_sha="a1b2c3d",
        implements_concepts={"calculate_reserve": "LossEvent"},
    )
    rag.upsert_indexed_bundle(document=git_doc, chunks=git_chunks, code_edges=git_edges)

    ddl_doc, ddl_chunks = DifferentiatedIncrementalIndexer.index_db_ddl_schema_only(
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
        ontology_concepts=("LossEvent",),
    )
    rag.upsert_indexed_bundle(document=ddl_doc, chunks=ddl_chunks)

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


__all__ = [
    "ALLOWED_JIRA_REFERENCE_TYPES",
    "ChunkRole",
    "CodeGraphEdgeEntity",
    "CodeGraphEdgeType",
    "DifferentiatedIncrementalIndexer",
    "DocVsCodeAuditFinding",
    "EMBEDDING_DIM",
    "HybridRagHit",
    "HybridRagService",
    "IndexingRegime",
    "KbChunkEntity",
    "KbDocumentEntity",
    "KbStaleAlertEntity",
    "StaleAlertReason",
    "TripartiteGraphAndFreshnessService",
    "TripartiteNodeType",
    "TripartiteRelationType",
    "TripartiteTraceEdgeEntity",
    "build_contextual_header",
    "build_empty_rag_service",
    "build_seeded_rag_service",
    "compute_deterministic_halfvec_1024",
    "cosine_similarity",
    "extract_jira_issue_keys",
]
