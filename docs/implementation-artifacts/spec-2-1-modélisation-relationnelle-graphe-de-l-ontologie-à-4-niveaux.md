---
title: 'Story 2.1: Modélisation Relationnelle-Graphe de l''Ontologie à 4 Niveaux & Triple Exécution Active'
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

**Problem:** Les équipes métier, architecture et engineering utilisent des vocabulaires différents pour désigner les mêmes actifs critiques, ce qui provoque des ambiguïtés dans les livrables du Blackboard et les requêtes RAG.

**Approach:** Créer la révision Alembic `0006_story_2_1_ontology_4_levels.py` (`ontology_concepts`, `ontology_relations`, `ontology_axioms` à clés `UUIDv7`), implémenter dans `packages/orcia-core/ontology/{models.py,resolver.py}` le résolveur hiérarchique CTE à 4 niveaux (`1_ENTERPRISE -> 2_DOMAIN -> 3_TEAM [Équipe Parente -> Sous-Équipe] -> 3_WORKSPACE -> 4_RUN_EPHEMERAL`) en `< 15 ms` (`NFR-PERF-3`), bloquer toute contradiction d'un axiome `immutable: true` avec `HTTP 422 ERR_ONTOLOGY_CONFLICT`, et activer la triple exécution (validation Blackboard, `ProfileSemanticTranslator` pour les 6 profils humains, et expansion sémantique RAG).

## Boundaries & Constraints

**Always:**
- Maintenir `0` import `fastapi`, `sqlalchemy`, `dramatiq`, `redis` ou `litellm` dans `packages/orcia-core/ontology/`.
- Résoudre la hiérarchie à 4 niveaux en `< 15 ms` (`NFR-PERF-3`) et vérifier les axiomes `immutable: true` le long de `canonical_term` et de `parent_concept_id` (y compris entre Sous-Équipe `3_TEAM` et Équipe Parente `3_TEAM`).
- Exposer la vue 4 colonnes dans `@orcia/ui` (`OntologyAndKbExplorerPanel.tsx`) avec sélecteur de traduction par Profil Humain et état vide par défaut.

**Never:**
- Ne jamais inclure dans l'ontologie effective un concept `4_RUN_EPHEMERAL` dont la branche `snapshot_branch_status` est `SUPERSEDED`.
- Ne jamais autoriser un `READ_ONLY_OBSERVER` (`OBSERVER` / `BU_DIRECTOR`) à muter un concept d'ontologie (`HTTP 403 ERR_OBSERVER_MODE_READ_ONLY`).

</frozen-after-approval>

## Code Map

- `infra/migrations/versions/0006_story_2_1_ontology_4_levels.py` — Tables `ontology_concepts`, `ontology_relations` et `ontology_axioms`.
- `packages/orcia-core/src/orcia_core/ontology/models.py` — Entités `OntologyConceptEntity`, `OntologyRelationEntity`, `OntologyAxiomEntity`, `ResolvedOntologySnapshot`.
- `packages/orcia-core/src/orcia_core/ontology/resolver.py` — `build_ontology_resolution_cte_sql()`, `OntologyHierarchyResolver` et `ProfileSemanticTranslator`.
- `apps/api/src/orcia_api/routers/ontology_and_rag.py` — Endpoints `/api/v1/ontology-rag/state`, `/ontology/resolve`, `/ontology/concepts`.
- `packages/ui/src/shell/OntologyAndKbExplorerPanel.tsx` — Composant Design System `@orcia/ui` 4 colonnes + sélecteur de Profil Humain.
- `tests/unit/test_ontology_and_what_if.py` — Tests unitaires, propriétés `hypothesis` et contrat FastAPI.
