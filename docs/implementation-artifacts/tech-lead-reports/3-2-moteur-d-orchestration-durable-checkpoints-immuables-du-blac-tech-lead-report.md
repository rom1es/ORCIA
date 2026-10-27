# Rapport Tech Lead — Analyse & Implémentation : Story 3.2 (Moteur d'Orchestration Durable, Checkpoints Immuables du Blackboard, Isolation des Sous-Workflows `SUB_WORKFLOW`, Hydratation JIT & Exécution Tri-Modale)

- **Identifiant Story / Ticket** : `3-2-moteur-d-orchestration-durable-checkpoints-immuables-du-blac`
- **Epic parent** : `Epic 3 — Cockpit "Human-Led", Agent Assistant Adaptatif, Moteur d'Orchestration Durable & Sous-Workflows Fractals (SUB_WORKFLOW <= 3)`
- **Date d'ouverture** : `2026-10-27`
- **Auteur (Rôle)** : `Tech Lead / Senior Developer Agent`
- **Statut** : `Done`

---

## 1. Analyse du Besoin & Étude d'Impact Tech Lead (Avant Implémentation)

### 1.1 Contexte Fonctionnel & Problématique Métier
Dans ORCIA, un *Workflow Run* peut durer de quelques secondes à plusieurs jours (pauses d'arbitrage humain, résolution d'habilitations ou de tickets Jira, ou exécution d'audits complexes en tâche de fond). De plus, avec l'ouverture aux sous-workflows fractals (`SUB_WORKFLOW` jusqu'à une profondeur `nesting_depth <= 3`) et aux trois régimes d'exécution (`INTERACTIVE_COACHING`, `BACKGROUND_FAST_PATH`, `AUTONOMOUS_CONTRACT`), le moteur d'orchestration doit garantir quatre invariants critiques :
1. **Immuabilité cryptographique du Blackboard (`AD-2`, `NFR-SEC-3`)** : tant qu'une étape est en cours (`EXECUTING_AGENT` ou `EVALUATING_GATES`), ses sorties et hypothèses intermédiaires sont écrites dans `step_executions.draft_artifact_jsonb` et `step_executions.step_memlog_jsonb`. Ce n'est qu'au passage au statut `COMMITTED` qu'une ligne est insérée dans `blackboard_snapshots`, table protégée par un trigger PostgreSQL `BEFORE UPDATE OR DELETE RAISE EXCEPTION`.
2. **Hydratation Just-In-Time stricte (`JitStepHydrator`, `AD-13`)** : l'*Agent Exécuteur* de l'étape $k$ ne reçoit que la directive de l'étape $k$ et les artefacts amont explicitement déclarés dans `input_mapping` (`orcia://runs/{run_id}/steps/{step_key}/artifacts/{artifact_key}`), avec **0 instruction des étapes futures $k+1..N$** et **0 artefact non déclaré**.
3. **Isolation lexicale des sous-workflows (`SUB_WORKFLOW`, `FR-30`, `AD-18`)** : chaque étape `SUB_WORKFLOW` instancie un `workflow_run` enfant doté de son propre Blackboard alimenté par `input_mapping`, partageant le plafond budgétaire `budget_max_usd` du `root_run_id`, et ne reversant au Blackboard parent que les clés déclarées dans `output_mapping`.
4. **Exécution non-bloquante en tâche de fond (`BACKGROUND_FAST_PATH` / `UJ-10`, `AD-13`)** : lorsqu'une ambiguïté ou divergence Doc vs Code survient en tâche de fond, l'agent consigne des marqueurs structurés (`[ASSUMPTION]`, `[BUG_CODE_SUSPECTED]`, `[DOC_OBSOLETE_SUSPECTED]`) dans `step_memlog_jsonb` et poursuit jusqu'au rapport consolidé final avec notification SSE (`< 500 ms`).

### 1.2 Analyse d'Impact GitNexus & Cartographie du Code Existant
- **Commandes GitNexus exécutées** :
  - `gitnexus analyze` (index rafraîchi à `4 911` nœuds, `7 617` relations, `292` flux d'exécution).
  - `gitnexus_impact({target: "WorkflowOrchestrationSetupService", direction: "upstream", repo: "ORCIA"})` $\rightarrow$ `risk: LOW`, `impactedCount: 2` (`orchestration/__init__.py`, `orchestration/seeds.py`).
  - `gitnexus_impact({target: "DeterministicCassetteLLM", direction: "upstream", repo: "ORCIA"})` $\rightarrow$ `risk: UNKNOWN` (vérifié par recherche textuelle : utilisé dans `tests/unit/test_orcia_core_and_api.py`).
  - `gitnexus_impact({target: "OntologyHierarchyResolver", direction: "upstream", repo: "ORCIA"})` $\rightarrow$ `risk: LOW`, `impactedCount: 2`.
- **Symboles et modules existants impactés** :
  - `packages/orcia-core/src/orcia_core/blackboard/__init__.py` (`LOW` : stub initial de 8 lignes à enrichir avec `models.py` et `store.py`).
  - `packages/orcia-core/src/orcia_core/orchestration/run_lock_service.py` (`LOW` : intégration avec `DurableOrchestrationEngine` et `AppendOnlyBlackboardStore`).
  - `apps/worker/src/orcia_worker/` (`LOW` : ajout de `step_runner.py` avec acteur Dramatiq idempotent `step_runner_actor`).
  - `apps/api/src/orcia_api/routers/blackboard_and_engine.py` (`LOW` : routes d'hydratation JIT, d'exécution d'étape et d'audit `BACKGROUND_FAST_PATH`).

### 1.3 Chiffres Clés & Exploration de la Base de Données
- **Tables existantes concernées** : `workflow_definitions`, `workflow_runs`, `run_lock_manifests` (créées en révision `0010_story_3_1`).
- **Nouvelles tables introduites en `0011_story_3_2`** :
  1. `step_executions` (`draft_artifact_jsonb`, `draft_cas_key`, `step_memlog_jsonb`, `hydrated_input_uris_jsonb`, `child_run_id`, `committed_snapshot_id`, `attempt_count <= 10`, `cost_usd`).
  2. `blackboard_snapshots` (`artifact_payload_jsonb`, `artifact_cas_key`, `artifact_sha256`, `memlog_summary_jsonb`, `branch_status`, protégée par le trigger PostgreSQL `trg_blackboard_snapshots_append_only`).

### 1.4 Opportunités de Factorisation & Dette Technique Identifiée
- **Factorisation identifiée** :
  - Réutilisation directe de `compute_bytes_sha256` et `FederatedUriResolver` (`orcia_core.catalog.cas_resolver`) pour stocker les artefacts brouillons et engagés dans le CAS (`cas/<sha256>`).
  - Réutilisation de `DeterministicCassetteLLM` (`orcia_core.testing.cassette_llm`) et de `LLMPort` (`orcia_core.ports.llm_port`) pour l'exécution agnostique d'étapes IA avec `0 $` d'appels externes en CI.
- **Découpage modulaire (`< 350` lignes par fichier)** :
  - Séparation nette entre `packages/orcia-core/src/orcia_core/blackboard/models.py`, `blackboard/store.py`, et `packages/orcia-core/src/orcia_core/orchestration/engine.py`.

---

## 2. Plan d'Implémentation (Architecture Cible)

### 2.1 Évolutions Base de Données & Migrations (`infra/migrations/` & `infra/scripts/`)
- **Migration Alembic** : `infra/migrations/versions/0011_story_3_2_step_executions_and_blackboard_snapshots.py` (révise `0010_story_3_1`) :
  - Création de `step_executions` et `blackboard_snapshots`.
  - Création de la fonction PL/pgSQL `prevent_blackboard_snapshot_mutation()` et du trigger `trg_blackboard_snapshots_append_only BEFORE UPDATE OR DELETE ON blackboard_snapshots`.
- **Script de maintenance** : `infra/scripts/maintenance/07_backfill_step_executions_and_blackboard_snapshots.py` (`--dry-run` par défaut, `--apply` idempotent).

### 2.2 Noyau Métier & Services Applicatifs (`packages/orcia-core/`, `apps/worker/`)
- `packages/orcia-core/src/orcia_core/blackboard/models.py` & `store.py` :
  - `StepMemlogEntry`, `StepExecutionEntity`, `BlackboardSnapshotEntity`, `HydratedStepContext`, `AppendOnlyBlackboardStore`.
- `packages/orcia-core/src/orcia_core/orchestration/engine.py` :
  - `JitStepHydrator` (`AD-13`) et `DurableOrchestrationEngine` (`AD-2`, `AD-12`, `AD-18`).
- `apps/worker/src/orcia_worker/step_runner.py` :
  - `execute_step_runner_job` et `@dramatiq.actor(actor_name="step_runner", max_retries=3) def step_runner_actor(...)`.

### 2.3 Couche Backend API, Sécurité & Contrats (`apps/api/`, `packages/api-client/`)
- `apps/api/src/orcia_api/routers/blackboard_and_engine.py` :
  - `POST /api/v1/orchestration/runs/steps/hydrate` : inspection du contexte JIT d'une étape $k$.
  - `POST /api/v1/orchestration/runs/steps/execute` : exécution durable d'une étape (avec support `SUB_WORKFLOW` et `BACKGROUND_FAST_PATH`).
  - `GET /api/v1/orchestration/runs/{run_id}/blackboard` : consultation des `step_executions` et `blackboard_snapshots` actifs d'un Run.
- Régénération du SDK OpenAPI 3.1 dans `packages/api-client`.

### 2.4 Interface Utilisateur & Expérience (`packages/ui/` & `apps/web/`)
- Enrichissement de `WorkflowStudioSection.tsx` et des dictionnaires `fr.ts` / `en.ts` pour afficher les checkpoints immuables du Blackboard, l'hydratation JIT et les marqueurs `BACKGROUND_FAST_PATH` (`[ASSUMPTION]`, `[BUG_CODE_SUSPECTED]`, `[DOC_OBSOLETE_SUSPECTED]`).

---

## 3. Bilan des Modifications & Résultats (Post-Implémentation)

### 3.1 Fichiers Créés ou Modifiés
| Fichier | Action | Rôle |
| --- | --- | --- |
| `infra/migrations/versions/0011_story_3_2_step_executions_and_blackboard_snapshots.py` | Créé | Tables `step_executions`, `blackboard_snapshots` et trigger PG18 `trg_blackboard_snapshots_append_only`. |
| `packages/orcia-core/src/orcia_core/blackboard/models.py` & `store.py` | Créés | Entités du Blackboard et `AppendOnlyBlackboardStore` (séparation brouillon/snapshot, isolation par `run_id`). |
| `packages/orcia-core/src/orcia_core/orchestration/engine.py` | Créé | `JitStepHydrator` (`0` fuite d'étape future) et `DurableOrchestrationEngine` (`SUB_WORKFLOW <= 3`, `BACKGROUND_FAST_PATH`). |
| `apps/worker/src/orcia_worker/step_runner.py` | Créé | Acteur Dramatiq idempotent `step_runner_actor` & `execute_step_runner_job`. |
| `packages/orcia-core/src/orcia_core/schemas/blackboard.py` & `apps/api/src/orcia_api/routers/blackboard_and_engine.py` | Créés | Schémas Pydantic v2 et endpoints REST `/api/v1/orchestration/runs/{run_id}/blackboard`, `/steps/hydrate`, `/steps/execute`, `/fast-path-audit`. |
| `infra/scripts/maintenance/07_backfill_step_executions_and_blackboard_snapshots.py` | Créé | Script de maintenance idempotent (`--dry-run` / `--apply`). |
| `tests/unit/test_durable_orchestration_and_blackboard.py` & `tests/integration/test_real_containers.py` | Créé / Modifié | Tests unitaires et test d'intégration PG18 `testcontainers` vérifiant le rejet de `UPDATE`/`DELETE` sur `blackboard_snapshots`. |

### 3.2 Métriques de Qualité & Validation des 5 Couches (`AD-17`)
- **Ruff & Mypy (`--strict`)** : `0` erreur.
- **Contrat OpenAPI 3.1 (`export_openapi.py --check`)** : `0` diff.
- **Tests Python (`pytest`)** : `53 passed` en `19.0s`, couverture globale `packages/orcia-core` à **`96.05 %`** ($\ge 90\%$).
- **Tests TypeScript (`pnpm turbo run lint typecheck test`)** : `9/9 tasks successful`.
- **Architecture Spine Lint (`lint_spine.py`)** : `ok: true`, `0 findings`.
