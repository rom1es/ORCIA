"""Unit & API contract tests for Story 2.3 (3-Regime Hybrid RAG) & Story 2.4 (Tripartite Graph)."""

from __future__ import annotations

import time

import pytest
from fastapi.testclient import TestClient

from orcia_api.main import create_app
from orcia_core.rag import (
    DifferentiatedIncrementalIndexer,
    build_empty_rag_service,
    build_seeded_rag_service,
    extract_jira_issue_keys,
)
from orcia_core.rag.errors import DdlOnlyTransactionalDataError
from orcia_worker.docling_indexer import docling_indexer_actor, execute_docling_index_job


def test_default_rag_service_is_completely_empty() -> None:
    """By default in runtime, Hybrid RAG & Tripartite Graph contain 0 rows."""
    rag, trip = build_empty_rag_service()
    assert rag.list_documents() == ()
    assert rag.list_code_edges() == ()
    assert trip.list_edges() == ()
    assert trip.list_alerts() == ()


def test_3_regime_differentiated_indexing_and_ddl_transactional_guard() -> None:
    """Story 2.3 AC1: Verifies Regime 1 (Confluence/Jira), Regime 2 (Git AST) & Regime 3 (DDL)."""
    # Regime 1a: Draft or unlabeled Confluence pages are skipped
    skipped_doc, skipped_chunks = DifferentiatedIncrementalIndexer.index_confluence_parent_child(
        workspace_id="ws-1",
        datasource_id="ds-conf",
        datasource_alias="conf_main",
        source_uri="confluence://SPACE/draft-1",
        title="Brouillon",
        hierarchy_path="SPACE",
        markdown_sections=("Sec 1",),
        revision_tag="v1",
        page_status="draft",
    )
    assert skipped_doc is None
    assert skipped_chunks == ()

    # Regime 1b: Operational Jira task (not in reference types) is skipped
    j_doc, j_chunks = DifferentiatedIncrementalIndexer.index_jira_reference_issue(
        workspace_id="ws-1",
        datasource_id="ds-jira",
        datasource_alias="jira_main",
        issue_key="OPS-99",
        issue_type="Sub-task",
        title="Daily chore",
        body_text="Nothing structural",
        updated_tag="t1",
    )
    assert j_doc is None
    assert j_chunks == ()

    # Regime 2: Git AST symbol chunking + CodeGraphEdge (DEFINES, CALLS, TESTED_BY)
    git_doc, git_chunks, git_edges = DifferentiatedIncrementalIndexer.index_git_ast_and_code_graph(
        workspace_id="ws-1",
        datasource_id="ds-git",
        datasource_alias="git_backend",
        repo_uri="git://org/repo",
        file_path="pkg/calc.py",
        python_source=(
            "from math import sqrt\n\n"
            "def helper(x: float) -> float:\n"
            "    return sqrt(x)\n\n"
            "def test_helper() -> None:\n"
            "    helper(4.0)\n"
        ),
        commit_sha="sha123",
        implements_concepts={"helper": "LossEvent"},
    )
    assert git_doc.indexing_regime == "CODE_AST_GRAPH"
    assert len(git_chunks) == 2
    edge_types = {e.edge_type for e in git_edges}
    assert {"IMPORTS", "DEFINES", "CALLS", "TESTED_BY", "IMPLEMENTS_CONCEPT"}.issubset(edge_types)

    # Regime 3: DB DDL-only rejects INSERT/UPDATE/DELETE/COPY with HTTP 422
    with pytest.raises(DdlOnlyTransactionalDataError) as exc_info:
        DifferentiatedIncrementalIndexer.index_db_ddl_schema_only(
            workspace_id="ws-1",
            datasource_id="ds-db",
            datasource_alias="db_prod",
            db_uri="db://prod/users",
            ddl_sql="CREATE TABLE users (id INT); INSERT INTO users VALUES (1);",
            schema_version="v1",
        )
    assert exc_info.value.error_code == "ERR_DDL_ONLY_TRANSACTIONAL_DATA_FORBIDDEN"
    assert exc_info.value.http_status == 422


def test_hybrid_rrf_search_parent_injection_passthrough_and_latency() -> None:
    """Story 2.3 AC2: Hybrid RRF (`halfvec(1024)` + BM25) < 50ms, parent injection & Passthrough."""
    rag, _ = build_seeded_rag_service(workspace_id="ws-claims-alpha")

    t0 = time.perf_counter()
    hits = rag.search_hybrid_rrf(
        workspace_id="ws-claims-alpha",
        query_text="PAY-142 calculate_reserve LossEvent",
        top_k=5,
    )
    elapsed_ms = (time.perf_counter() - t0) * 1000.0
    assert elapsed_ms < 50.0
    assert len(hits) >= 3

    # Verify CHILD chunk match injects the full PARENT section text
    conf_hit = next(h for h in hits if h.datasource_alias == "confluence_claims")
    assert "Section 1" in conf_hit.injected_content
    assert "Section 2" in conf_hit.injected_content
    assert conf_hit.is_stale is True
    assert conf_hit.stale_warning_marker == "[STALE_WARNING]"

    # Verify Passthrough source filtering excludes unauthorized datasources
    filtered_hits = rag.search_hybrid_rrf(
        workspace_id="ws-claims-alpha",
        query_text="PAY-142 calculate_reserve",
        allowed_datasource_aliases=frozenset({"git_core"}),
        top_k=5,
    )
    assert all(h.datasource_alias == "git_core" for h in filtered_hits)


def test_idempotent_docling_indexer_actor_skips_unchanged_sha256() -> None:
    """Story 2.3 AC1: Worker `docling_indexer_actor` is idempotent on retry with same SHA-256."""
    rag, _ = build_empty_rag_service()
    first = execute_docling_index_job(
        workspace_id="ws-1",
        datasource_id="ds-conf",
        datasource_alias="conf_kb",
        source_uri="confluence://KB/page-1",
        title="Architecture Guide",
        hierarchy_path="KB > Archi",
        markdown_sections=("Contenu v1",),
        revision_tag="v1",
        trace_id="4bf92f3577b34da6a3ce929d0e0e4736",
        rag_service=rag,
    )
    assert first.already_indexed is False
    assert first.chunks_count == 2

    # Second retry with identical revision_tag & content is a no-op
    second = execute_docling_index_job(
        workspace_id="ws-1",
        datasource_id="ds-conf",
        datasource_alias="conf_kb",
        source_uri="confluence://KB/page-1",
        title="Architecture Guide",
        hierarchy_path="KB > Archi",
        markdown_sections=("Contenu v1",),
        revision_tag="v1",
        trace_id="4bf92f3577b34da6a3ce929d0e0e4736",
        rag_service=rag,
    )
    assert second.already_indexed is True

    # Also invoke the Dramatiq actor entrypoint directly and verify default worker RAG state
    from orcia_worker.docling_indexer import _default_worker_rag

    docling_indexer_actor(
        "ws-1",
        "ds-conf",
        "conf_kb",
        "confluence://KB/page-1",
        "Architecture Guide",
        "KB > Archi",
        ["Contenu v1"],
        "v1",
        "4bf92f3577b34da6a3ce929d0e0e4736",
    )
    assert len(_default_worker_rag.list_documents(workspace_id="ws-1")) >= 1

    # Verify skipped path (unlabeled page) and CODE_AST_GRAPH + DB_DDL_ONLY worker regimes
    skipped_job = execute_docling_index_job(
        workspace_id="ws-1",
        datasource_id="ds-conf",
        datasource_alias="conf_kb",
        source_uri="confluence://KB/draft",
        title="Draft",
        hierarchy_path="KB",
        markdown_sections=("Sec",),
        revision_tag="v1",
        trace_id="4bf92f3577b34da6a3ce929d0e0e4736",
        rag_service=rag,
        labels=(),
    )
    assert skipped_job.chunks_count == 0

    git_job = execute_docling_index_job(
        workspace_id="ws-1",
        datasource_id="ds-git",
        datasource_alias="git_kb",
        source_uri="git://org/repo",
        title="pkg/mod.py",
        hierarchy_path="pkg",
        markdown_sections=("def run():\n    return 1\n",),
        revision_tag="sha1",
        trace_id="4bf92f3577b34da6a3ce929d0e0e4736",
        rag_service=rag,
        indexing_regime="CODE_AST_GRAPH",
    )
    assert git_job.chunks_count == 1

    ddl_job = execute_docling_index_job(
        workspace_id="ws-1",
        datasource_id="ds-db",
        datasource_alias="db_kb",
        source_uri="db://prod/schema",
        title="schema.sql",
        hierarchy_path="db",
        markdown_sections=("CREATE TABLE t (id UUID PRIMARY KEY);",),
        revision_tag="v1",
        trace_id="4bf92f3577b34da6a3ce929d0e0e4736",
        rag_service=rag,
        indexing_regime="DB_DDL_ONLY",
    )
    assert ddl_job.chunks_count == 1


def test_tripartite_graph_jira_extraction_stale_warning_and_doc_obsolete_audit() -> None:
    """Story 2.4 AC1 & AC2: Tripartite links, `[STALE_WARNING]` & `[DOC_OBSOLETE_SUSPECTED]`."""
    keys = extract_jira_issue_keys("Spec PAY-101 remplacée par PAY-142 et SECOPS-9 (PAY-142).")
    assert keys == ("PAY-101", "PAY-142", "SECOPS-9")

    _, trip = build_seeded_rag_service(workspace_id="ws-claims-alpha")
    edges = trip.list_edges(workspace_id="ws-claims-alpha")
    relation_types = {e.relation_type for e in edges}
    assert {
        "DOCUMENTS",
        "SPECIFIES",
        "FIXES",
        "BLOCKS",
        "IMPLEMENTS_ISSUE",
        "AFFECTS_CONCEPT",
    }.issubset(relation_types)

    alerts = trip.list_alerts(workspace_id="ws-claims-alpha")
    assert len(alerts) == 1
    assert alerts[0].diagnostic_marker == "[STALE_WARNING]"
    assert alerts[0].justifying_jira_key == "PAY-142"
    assert "run-active-claims-01" in alerts[0].impacted_run_ids

    # Doc vs Code audit: newer Done Jira ticket qualifies as [DOC_OBSOLETE_SUSPECTED]
    obsolete = trip.audit_doc_vs_code_divergence(
        confluence_uri="confluence://CLAIMS/pages/101-spec-seuil-validation",
        git_repo_uri="git://claims/core-engine",
        git_symbol="calculate_reserve",
        doc_rule_summary="seuil >= 5000 EUR",
        code_rule_summary="seuil >= 7500 EUR",
        newer_done_jira_key="PAY-142",
    )
    assert obsolete.qualification_marker == "[DOC_OBSOLETE_SUSPECTED]"
    assert obsolete.justifying_jira_key == "PAY-142"

    # Without a justifying Jira ticket, qualifies as [BUG_CODE_SUSPECTED]
    bug = trip.audit_doc_vs_code_divergence(
        confluence_uri="confluence://CLAIMS/pages/101-spec-seuil-validation",
        git_repo_uri="git://claims/core-engine",
        git_symbol="calculate_reserve",
        doc_rule_summary="seuil >= 5000 EUR",
        code_rule_summary="seuil >= 7500 EUR",
        newer_done_jira_key=None,
    )
    assert bug.qualification_marker == "[BUG_CODE_SUSPECTED]"


def test_fastapi_rag_search_ddl_guard_and_tripartite_audit_endpoints() -> None:
    """Verify FastAPI /api/v1/ontology-rag/rag/* and /tripartite/* endpoints."""
    client = TestClient(create_app())

    res_search = client.post(
        "/api/v1/ontology-rag/rag/search?fixture=true",
        json={
            "workspace_id": "ws-claims-alpha",
            "query_text": "PAY-142 calculate_reserve",
            "top_k": 3,
        },
    )
    assert res_search.status_code == 200
    assert len(res_search.json()["hits"]) >= 1

    # Valid DDL with SQL comments containing keywords succeeds (200 OK)
    res_ddl_ok = client.post(
        "/api/v1/ontology-rag/rag/index-db-ddl?fixture=true&persona_key=marc",
        json={
            "workspace_id": "ws-claims-alpha",
            "datasource_id": "ds-db",
            "datasource_alias": "db_claims",
            "db_uri": "db://claims/events",
            "ddl_sql": "-- select from audit\nCREATE TABLE claim_events (id UUID PRIMARY KEY);",
            "schema_version": "v2",
        },
    )
    assert res_ddl_ok.status_code == 200
    assert res_ddl_ok.json()["indexing_regime"] == "DB_DDL_ONLY"

    # Observer persona is rejected with 403 ERR_OBSERVER_MODE_READ_ONLY
    res_ddl_obs = client.post(
        "/api/v1/ontology-rag/rag/index-db-ddl?fixture=true&persona_key=claire",
        json={
            "workspace_id": "ws-claims-alpha",
            "datasource_id": "ds-db",
            "datasource_alias": "db_claims",
            "db_uri": "db://claims/events",
            "ddl_sql": "CREATE TABLE claim_events (id UUID PRIMARY KEY);",
            "schema_version": "v2",
        },
    )
    assert res_ddl_obs.status_code == 403
    assert res_ddl_obs.json()["error_code"] == "ERR_OBSERVER_MODE_READ_ONLY"

    # Schema-qualified UPDATE or DELETE is rejected with 422
    res_ddl_bad = client.post(
        "/api/v1/ontology-rag/rag/index-db-ddl?fixture=true",
        json={
            "workspace_id": "ws-claims-alpha",
            "datasource_id": "ds-db",
            "datasource_alias": "db_claims",
            "db_uri": "db://claims/events",
            "ddl_sql": "CREATE TABLE t (id INT); UPDATE public.claim_events SET id = 1;",
            "schema_version": "v1",
        },
    )
    assert res_ddl_bad.status_code == 422
    assert res_ddl_bad.json()["error_code"] == "ERR_DDL_ONLY_TRANSACTIONAL_DATA_FORBIDDEN"

    res_audit = client.post(
        "/api/v1/ontology-rag/tripartite/audit-doc-vs-code?fixture=true",
        json={
            "confluence_uri": "confluence://CLAIMS/pages/101",
            "git_repo_uri": "git://claims/core-engine",
            "git_symbol": "calculate_reserve",
            "doc_rule_summary": "5000 EUR",
            "code_rule_summary": "7500 EUR",
            "newer_done_jira_key": "PAY-142",
        },
    )
    assert res_audit.status_code == 200
    assert res_audit.json()["qualification_marker"] == "[DOC_OBSOLETE_SUSPECTED]"
