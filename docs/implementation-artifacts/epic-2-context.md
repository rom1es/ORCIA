# Epic 2 Context — Ontologie d'Entreprise Vivante (4 Niveaux) & Connaissance Tripartite Multi-Sources (`AD-7`, `AD-8`, `FR-8..11`, `UX-DR12`)

- **Noyau Hexagonal Pur (`packages/orcia-core/ontology` & `packages/orcia-core/rag`)** : Zéro import `fastapi`, `sqlalchemy`, `dramatiq`, `redis`, `litellm`.
- **Ontologie Active à 4 Niveaux (`AD-7`, `FR-8`, `FR-9`)** :
  - `1_ENTERPRISE -> 2_DOMAIN -> 3_TEAM (Équipe Parente -> Sous-Équipe) -> 3_WORKSPACE -> 4_RUN_EPHEMERAL`.
  - Résolution hiérarchique CTE récursive en `< 15 ms` (`NFR-PERF-3`), rejetant toute surcharge contradictoire d'un axiome `immutable: true` avec `HTTP 422 ERR_ONTOLOGY_CONFLICT` (**RFC 9457**).
  - Triple exécution active : validation de schéma/cardinalité du Blackboard, `ProfileSemanticTranslator` (6 profils humains) et expansion sémantique des requêtes RAG.
  - Extraction `4_RUN_EPHEMERAL` isolée par branche (`introduced_in_snapshot_id`, marquée `SUPERSEDED` après Replay), simulateur d'impact *What-If* (`ImpactSimulatorService`) et promotion gouvernée `L4 -> L3 -> L2 -> L1`.
- **Indexation Différenciée 3 Régimes, RAG Hybride & Graphe Tripartite (`AD-8`, `FR-10`, `FR-11`, `UJ-10`)** :
  - Régime 1 (`DOC_PARENT_CHILD`) : Confluence CQL (`orcia-kb`, hors `draft`/`archived`) et Jira JQL de référence avec en-tête contextuel `[Alias Source : Espace/Projet > Parent > Titre | Concepts Ontologie]`.
  - Régime 2 (`CODE_AST_GRAPH`) : Découpage syntaxique AST Python par symbole + `CodeGraphEdge` (`IMPORTS`, `DEFINES`, `CALLS`, `TESTED_BY`, `IMPLEMENTS_CONCEPT`).
  - Régime 3 (`DB_DDL_ONLY`) : Schéma DDL uniquement (`CREATE`/`ALTER`/`COMMENT ON`), rejetant toute requête transactionnelle (`INSERT`, `UPDATE`, `DELETE`, `COPY`, `SELECT ... FROM`) avec `HTTP 422 ERR_DDL_ONLY_TRANSACTIONAL_DATA_FORBIDDEN`.
  - Recherche hybride `halfvec(1024)` (HNSW) + `BM25` (`tsvector` GIN) fusionnée par *Reciprocal Rank Fusion* (`RRF`) en `< 50 ms` (`NFR-PERF-4`) avec filtrage *Passthrough* par source.
  - Graphe Tripartite `Confluence 1..N <-> Jira 1..N <-> Git 1..N <-> Ontologie` (6 types de relations : `DOCUMENTS`, `SPECIFIES`, `FIXES`, `BLOCKS`, `IMPLEMENTS_ISSUE`, `AFFECTS_CONCEPT`), brique `data-freshness` (`[STALE_WARNING]`) et qualification `[DOC_OBSOLETE_SUSPECTED]` vs `[BUG_CODE_SUSPECTED]`.
