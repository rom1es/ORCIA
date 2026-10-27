---
title: 'Story 3.2: Moteur d''Orchestration Durable, Checkpoints Immuables du Blackboard, Isolation des Sous-Workflows (SUB_WORKFLOW), Hydratation JIT & Exécution Tri-Modale'
type: 'feature'
created: '2026-10-27'
status: 'done'
route: 'dispatch'
baseline_commit: '420a17130283c63f6f0e10a67b866fda43b5b7c7' # pragma: allowlist secret
review_loop_iteration: 1
context:
  - '{project-root}/AGENTS.md'
  - '{project-root}/docs/implementation-artifacts/epic-3-context.md'
---

<frozen-after-approval reason="human-owned intent — do not modify unless human renegotiates">

## Intent

**Problem:** Sans séparation stricte entre brouillon d'étape (`step_executions.draft_artifact_jsonb` / `step_memlog_jsonb`) et snapshot immuable validé (`blackboard_snapshots` protégé par trigger PostgreSQL append-only), sans hydratation Just-In-Time (`JitStepHydrator`) filtrant les instructions des étapes futures et les artefacts non déclarés, sans isolation lexicale des Blackboards des sous-workflows (`SUB_WORKFLOW <= 3`) partageant le budget du `root_run_id`, et sans exécution non-bloquante en tâche de fond (`BACKGROUND_FAST_PATH` avec marqueurs `[ASSUMPTION]`, `[BUG_CODE_SUSPECTED]`, `[DOC_OBSOLETE_SUSPECTED]`), les workflows longs ou imbriqués ne peuvent ni survivre aux redémarrages ni éviter la pollution de contexte.

**Approach:** Créer la migration Alembic `0011_story_3_2_step_executions_and_blackboard_snapshots.py` (tables `step_executions` et `blackboard_snapshots` avec trigger PostgreSQL `BEFORE UPDATE OR DELETE RAISE EXCEPTION`), implémenter `packages/orcia-core/blackboard/` (`models.py`, `store.py`) et `packages/orcia-core/orchestration/engine.py` (`JitStepHydrator`, `DurableOrchestrationEngine`), ajouter l'acteur Dramatiq idempotent `step_runner_actor` dans `apps/worker/src/orcia_worker/step_runner.py`, étendre `/api/v1/orchestration/*` et `@orcia/api-client`, créer le script de maintenance `07_backfill_step_executions_and_blackboard_snapshots.py`, et enrichir le Studio d'Orchestration dans `@orcia/ui` et `apps/web`.

## Boundaries & Constraints

**Always:**
- Séparer strictement les brouillons mutables (`step_executions.draft_artifact_jsonb` et `step_memlog_jsonb` pendant `EXECUTING_AGENT` / `EVALUATING_GATES`) des checkpoints validés (`blackboard_snapshots`, créés uniquement au passage à `COMMITTED`, `AD-2`, `AR-3`).
- Protéger `blackboard_snapshots` par un trigger PostgreSQL `BEFORE UPDATE OR DELETE RAISE EXCEPTION` (`NFR-SEC-3`).
- N'injecter via `JitStepHydrator` (`AD-13`) que la directive de l'étape $k$ et les artefacts amont explicitement déclarés dans `input_mapping` (`0` instruction des étapes $k+1..N$, `0` artefact non déclaré).
- Isoler lexicalement le Blackboard de chaque `SUB_WORKFLOW` enfant (`parent_run_id`, `parent_step_execution_id`, `root_run_id`, `nesting_depth <= 3`), partager le plafond `budget_max_usd` sur `root_run_id`, et ne copier vers le parent que les clés déclarées dans `output_mapping` (`FR-30`, `AD-18`).
- En mode `BACKGROUND_FAST_PATH` (`UJ-10`), consigner `[ASSUMPTION]`, `[BUG_CODE_SUSPECTED]` et `[DOC_OBSOLETE_SUSPECTED]` dans `step_memlog_jsonb` sans bloquer le worker à mi-parcours (`AD-13`).
- Garantir l'idempotence de l'acteur Dramatiq `step_runner` en cas de retry.

**Never:**
- Ne jamais modifier ou supprimer une ligne de `blackboard_snapshots`.
- Ne jamais importer `fastapi`, `sqlalchemy`, `dramatiq`, `redis` ou `litellm` dans `packages/orcia-core/domain` ou `packages/orcia-core/ports`.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Hydratation JIT de l'étape $k$ (`JitStepHydrator`) | Workflow à 3 étapes, exécution de l'étape 2 déclarant `input_mapping` sur l'étape 1 | Contexte contient uniquement la directive de l'étape 2 et l'artefact validé de l'étape 1 (`0` info de l'étape 3) | `ResourceNotFoundError` si snapshot amont requis absent |
| Séparation Brouillon vs Snapshot (`COMMITTED`) | Étape en `EXECUTING_AGENT` puis `COMMITTED` | Brouillon écrit dans `step_executions.draft_artifact_jsonb` ; `blackboard_snapshots` ne reçoit une ligne qu'au `COMMITTED` | Trigger PG18 bloque tout `UPDATE`/`DELETE` sur `blackboard_snapshots` |
| Boucle de rétroaction bornée (`max_agent_retries`) | Échec de vérification avec feedback | Incrémente `attempt_count` jusqu'à `max_agent_retries` puis bascule en `WAITING_FOR_HUMAN_ARBITRATION` / `FAILED` | Rejet si `attempt_count > max_agent_retries` |
| Exécution `SUB_WORKFLOW` isolée (`nesting_depth <= 3`) | Étape `SUB_WORKFLOW` avec `input_mapping` et `output_mapping` | Crée un `workflow_run` enfant isolé, partage le budget `root_run_id`, remonte uniquement `output_mapping` au parent | `ValidationDomainError` si budget `root_run_id` dépassé |
| Exécution `BACKGROUND_FAST_PATH` (`UJ-10`) | Divergence Doc vs Code détectée pendant l'audit | Ajoute `[ASSUMPTION]`, `[BUG_CODE_SUSPECTED]`, `[DOC_OBSOLETE_SUSPECTED]` dans `step_memlog` sans bloquer le Run, émet un événement SSE de fin | N/A |

</frozen-after-approval>

## Code Map

- `infra/migrations/versions/0011_story_3_2_step_executions_and_blackboard_snapshots.py` -- Migration Alembic créant `step_executions`, `blackboard_snapshots` et le trigger `trg_blackboard_snapshots_append_only`.
- `packages/orcia-core/src/orcia_core/blackboard/models.py` & `store.py` -- Entités pures et store append-only du Blackboard avec isolation lexicale par `run_id`.
- `packages/orcia-core/src/orcia_core/orchestration/engine.py` -- `JitStepHydrator` (`AD-13`) et `DurableOrchestrationEngine` (`AD-2`, `AD-12`, `AD-18`).
- `apps/worker/src/orcia_worker/step_runner.py` -- Acteur Dramatiq idempotent `step_runner_actor`.
- `packages/orcia-core/src/orcia_core/schemas/blackboard.py` & `apps/api/src/orcia_api/routers/blackboard_and_engine.py` -- Routes REST `/api/v1/orchestration/runs/steps/hydrate`, `/execute` et `/fast-path-audit`.
- `infra/scripts/maintenance/07_backfill_step_executions_and_blackboard_snapshots.py` -- Script de maintenance idempotent (`--dry-run` / `--apply`).
- `packages/ui/src/shell/WorkflowStudioSection.tsx` & `apps/web/src/i18n/locales/{fr,en}.ts` -- Visualisation des checkpoints Blackboard, hydratation JIT et marqueurs `BACKGROUND_FAST_PATH`.

## Tasks & Acceptance

**Execution:**
- [x] `infra/migrations/versions/0011_story_3_2_step_executions_and_blackboard_snapshots.py` -- Créer la migration Alembic avec le trigger append-only PostgreSQL sur `blackboard_snapshots`.
- [x] `packages/orcia-core/src/orcia_core/blackboard/` -- Implémenter `models.py`, `store.py` et `__init__.py`.
- [x] `packages/orcia-core/src/orcia_core/orchestration/engine.py` -- Implémenter `JitStepHydrator` et `DurableOrchestrationEngine` (supportant `INTERACTIVE_COACHING`, `BACKGROUND_FAST_PATH`, `AUTONOMOUS_CONTRACT` et `SUB_WORKFLOW` isolé).
- [x] `apps/worker/src/orcia_worker/step_runner.py` -- Implémenter l'acteur Dramatiq idempotent `step_runner_actor`.
- [x] `packages/orcia-core/src/orcia_core/schemas/blackboard.py` & `apps/api/src/orcia_api/routers/blackboard_and_engine.py` -- Exposer les endpoints d'hydratation JIT, d'exécution d'étape et d'audit `BACKGROUND_FAST_PATH`, puis régénérer `@orcia/api-client`.
- [x] `infra/scripts/maintenance/07_backfill_step_executions_and_blackboard_snapshots.py` -- Créer le script de maintenance idempotent (`--dry-run` / `--apply`).
- [x] `packages/ui/src/shell/WorkflowStudioSection.tsx` & `apps/web/src/i18n/locales/{fr,en}.ts` -- Ajouter l'inspecteur Blackboard Append-Only, JIT Hydrator et marqueurs `BACKGROUND_FAST_PATH`.
- [x] `tests/unit/test_durable_orchestration_and_blackboard.py` & `tests/integration/test_real_containers.py` -- Couvrir la Story 3.2 à $\ge 90\%$ avec `DeterministicCassetteLLM` et `testcontainers` PostgreSQL 18 (vérifiant le rejet SQL de tout `UPDATE`/`DELETE` sur `blackboard_snapshots`).

**Acceptance Criteria:**
- Given une étape en cours d'exécution, when `JitStepHydrator` prépare le contexte, then seules la directive de l'étape $k$ et ses entrées `orcia://` déclarées sont injectées, et le livrable reste dans `draft_artifact_jsonb` jusqu'au `COMMITTED`.
- Given un sous-workflow `SUB_WORKFLOW`, when il s'exécute, then son Blackboard est isolé du parent, partage le budget du `root_run_id`, et ne remonte que `output_mapping`.
- Given un Run en mode `BACKGROUND_FAST_PATH`, when une divergence Doc vs Code apparaît, then les marqueurs `[ASSUMPTION]`, `[BUG_CODE_SUSPECTED]` ou `[DOC_OBSOLETE_SUSPECTED]` sont tracés dans `step_memlog_jsonb` sans bloquer le worker.

## Verification

**Commands:**
- `.venv/bin/ruff check . && .venv/bin/ruff format --check .` -- expected: `0 errors`
- `.venv/bin/mypy --strict packages/orcia-core apps/api apps/worker` -- expected: `Success: no issues found`
- `.venv/bin/pytest --cov=packages/orcia-core --cov-fail-under=90` -- expected: `passed, coverage >= 90%`
- `pnpm turbo run lint typecheck test` -- expected: `0 errors`
