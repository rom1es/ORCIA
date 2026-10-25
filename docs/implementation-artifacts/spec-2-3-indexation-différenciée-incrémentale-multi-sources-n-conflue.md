---
title: 'Story 2.3: Indexation Différenciée Incrémentale Multi-Sources (N Confluence, N Jira, N Git, DB DDL) & RAG Hybride (halfvec(1024) + BM25)'
type: 'feature'
created: '2026-10-25'
status: 'done'
route: 'dispatch'
baseline_commit: 'd0230a1e8f92e15a7822e4f0e12d4a50b18c0e11' # pragma: allowlist secret
review_loop_iteration: 1
context:
  - '{project-root}/AGENTS.md'
  - '{project-root}/docs/implementation-artifacts/epic-2-context.md'
---

<frozen-after-approval reason="human-owned intent — do not modify unless human renegotiates">

## Intent

**Problem:** Un découpage générique à taille fixe dégrade la pertinence sur les pages Confluence hiérarchiques, casse la syntaxe des fonctions/classes Git et risque d'indexer des lignes transactionnelles métier sensibles issues des bases `db://`.

**Approach:** Créer la révision Alembic `0008_story_2_3_hybrid_rag_halfvec_bm25_and_code_graph.py` (`kb_documents`, `kb_chunks` avec `halfvec(1024)` HNSW + `tsvector` GIN, `code_graph_edges`), implémenter dans `packages/orcia-core/rag/{vector_and_ast.py,indexer_and_rrf.py,hybrid_rag_service.py}` les 3 régimes d'indexation (`DOC_PARENT_CHILD`, `CODE_AST_GRAPH` avec support des classes/méthodes et repli gracieux sur `SyntaxError`, et `DB_DDL_ONLY` rejetant toute instruction DML/SELECT hors commentaires SQL avec `HTTP 422 ERR_DDL_ONLY_TRANSACTIONAL_DATA_FORBIDDEN`), le moteur `HybridRagService` (`halfvec(1024)` + BM25 via *Reciprocal Rank Fusion* `< 50 ms`, injection du parent et filtrage *Passthrough*), et l'acteur Dramatiq idempotent `docling_indexer_actor`.

## Boundaries & Constraints

**Always:**
- Préfixer chaque chunk par l'en-tête contextuel `[Alias Source : Espace/Projet > Parent > Titre | Concepts Ontologie]` (`AD-8`).
- Purger les anciennes arêtes `CodeGraphEdge` d'un fichier Git lors d'une ré-indexation avec un nouveau `content_sha256`.
- Appliquer `ObserverModeReadOnlyError` (`HTTP 403`) sur `POST /api/v1/ontology-rag/rag/index-db-ddl`.

**Never:**
- Ne jamais indexer de lignes transactionnelles (`INSERT`, `UPDATE`, `DELETE`, `COPY`, `TRUNCATE`, `MERGE INTO`, `SELECT ... FROM`) dans le régime `DB_DDL_ONLY`.

</frozen-after-approval>

## Code Map

- `infra/migrations/versions/0008_story_2_3_hybrid_rag_halfvec_bm25_and_code_graph.py` — Tables `kb_documents`, `kb_chunks`, `code_graph_edges`.
- `packages/orcia-core/src/orcia_core/rag/vector_and_ast.py` — `compute_deterministic_halfvec_1024`, `build_contextual_header`, `chunk_ast_symbol`.
- `packages/orcia-core/src/orcia_core/rag/indexer_and_rrf.py` — `DifferentiatedIncrementalIndexer` (3 régimes).
- `packages/orcia-core/src/orcia_core/rag/hybrid_rag_service.py` — `HybridRagService` (`search_hybrid_rrf`, `upsert_document_and_chunks`).
- `apps/worker/src/orcia_worker/docling_indexer.py` — Acteur Dramatiq idempotent `docling_indexer_actor`.
- `tests/unit/test_hybrid_rag_and_tripartite.py` — Tests des 3 régimes, RRF `< 50 ms`, filtrage Passthrough et worker idempotent.
