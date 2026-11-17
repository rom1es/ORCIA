# Rapport d'Implémentation Tech Lead — Story 16.3 : Double Mode de Processus (Piloté par l'objectif vs Piloté par les jalons), Dispatcher & Packs

- **Clé de Story / Référence** : `16-3-double-mode-processus-objectif-vs-jalons-dispatcher-et-packs`
- **Date** : `2026-11-11`
- **Auteur** : `Amelia (Tech Lead / Senior Staff Engineer)`
- **Statut** : `done`
- **Capacité(s)** : `CAP-160` — **classification** : `feature`
- **Épopée parente** : `Epic 16 — Harnais Agentique Réflexif, Exploration Chirurgicale & Double Mode d'Exécution des Processus`
- **Références Architecture & UX** : `specs/epic-16-reflexive-agent-harness/00-prd-and-stories-invest.md` (`US-16.3`, `CA-16.3.1` à `CA-16.3.6`), `01-ux-ascii-wireframes.md` (§1, §2), `02-backend-architecture-and-schemas.md` (§2, §4), `03-antigravity-tasks-breakdown.md` (`TASK-16.3-BE`, `TASK-16.3-FE`, `TASK-16.3-PACKS`), `ARCHITECTURE-SPINE.md` (`AD-02`, `AD-17`, `AD-19`), `DESIGN.md` (`Direction C`, zéro hex hors `tokens.css`, zéro jargon technique en UI).

---

## 1. Analyse du Besoin & Étude d'Impact Tech Lead

### 1.1 Objectif Métier & Périmètre Fonctionnel
La **Story 16.3** unifie dans une expérience unique de **Mes Processus** (`/processes`) et du **Studio 5-Blocs** (`/processes/studio/$workflowId`) les deux modes d'orchestration d'ORCIA sans exposer aucun jargon d'infrastructure (`DBOS`, `asyncio`, `SQL`, `Redis`, `SSE`, `Claim-Check`, `déterministe`, `non-déterministe`, `deterministic`, `non-deterministic`) :
1. **`Processus piloté par l'objectif (adaptatif)` (`non_deterministic`)** : l'utilisateur fixe le résultat métier attendu (`reflexive_objective`) et les agents spécialistes mobilisables (`allowed_delegate_agents`) ; le runtime réflexif (`NonDeterministicReflexiveRuntime`) explore les sources chirurgicalement, délègue à 1 niveau maximum (`allow_sub_agent_delegation=True`), puis soumet le livrable consolidé au pipeline de contrôles de qualité (`GatePipelineExecutor` avec jusqu'à 3 boucles d'auto-correction déterministe + Hunters) avant le point d'ancrage humain.
2. **`Processus piloté par les jalons (étapes garanties)` (`deterministic_dbos`)** : l'utilisateur fixe la séquence ordonnée de sous-étapes (`sub_steps`), les jalons d'arbitrage humain et les boucles de reprise ; lorsqu'une sous-étape est portée par un agent (`step_executor_type == "agent_executor"`), elle peut exécuter en interne sa propre boucle réflexive bornée (`allow_sub_agent_delegation=False`) tout en ne persistant dans l'état du workflow borné que le pointeur `ClaimCheckPointer` final et `reflexive_execution_id` (**Principe 7 d'encapsulation**).
3. **Persistance PostgreSQL 18 de bout en bout & Survie au `F5`** : les définitions `WorkflowDefinitionV2` éditées ou dérivées en brouillon via `PUT /api/v1/workflows/v2/{workflow_id}` sont persistées dans la table PostgreSQL 18 `workflow_definitions_v2` via un adaptateur SQL dédié (`SqlWorkflowDefinitionsV2Store`) et rechargées par `GET /api/v1/workflows/v2` via `@orcia/api-client`.
4. **Mise à jour des Packs Déclaratifs (`packs/`)** :
   - `packs/orcia-docs/workflows/wf-generate-orcia-documentation.yaml` bascule explicitement en `orchestration_type: non_deterministic` avec un `reflexive_objective` métier clair et `allowed_delegate_agents: [redacteur-documentation-orcia]`.
   - Les 4 workflows `packs/sdlc/workflows/wf-01-qualification-prd.yaml`, `wf-03-etude-architecture.yaml`, `wf-06-decoupe-us.yaml` et `wf-08-dev-external-gate.yaml` déclarent explicitement `orchestration_type: deterministic_dbos`.

### 1.2 Analyse d'Impact GitNexus (`repo: "/home/romain/Documents/Projects/ORCIA"`)
- `gitnexus.context` & `gitnexus.impact({target: "WorkflowDefinitionV2", direction: "upstream"})` :
  - `impactedCount = 11` (`4` dépendants directs : `orcia_core/agents/reflexive_schemas.py`, `orcia_core/packs/loader.py`, `orcia_core/workflows/__init__.py`, `orcia_core/workflows/gates/pipeline.py`, `risk = CRITICAL` sur l'arbre d'appels mais `riskSharedAxes = LOW`).
  - L'ajout des 3 champs rétrocompatibles avec valeurs par défaut (`orchestration_type = ProcessOrchestrationType.DETERMINISTIC_DBOS`, `reflexive_objective = None`, `allowed_delegate_agents = []`) garantit `0` régression sur les packs et tests existants.
- `gitnexus.impact({target: "run_bounded_workflow_v2", direction: "upstream"})` :
  - `impactedCount = 257`, `risk = CRITICAL`. Tous les nouveaux paramètres (`reflexive_step_runner: Callable[...] | None = None`) et attributs de `SubStepExecutionRecord` / `BoundedWorkflowRunState` (`reflexive_execution_id`, `orchestration_type`, `trace_events`) seront optionnels avec valeurs par défaut strictement rétrocompatibles.
- `gitnexus.impact({target: "NonDeterministicReflexiveRuntime", direction: "upstream"})` :
  - `impactedCount = 1` (`orcia_core/agents/__init__.py`, `risk = LOW`). Prêt à être orchestré par `ProcessExecutionDispatcher` dans `orcia_core/agents/process_dispatcher.py`.
- `gitnexus.impact({target: "WorkflowFiveBlocksCanvas", direction: "upstream"})` :
  - `maxImpactedCount = 1` (`router.tsx` sur `/processes/studio/$workflowId`, `risk = LOW`), mais le fichier fait actuellement **`786` lignes** (au-dessus du plafond de `350–400` lignes) et `ProcessesHubPage.tsx` fait **`439` lignes** — un découpage modulaire préalable (**Étape 0**) est donc impératif.

### 1.3 Opportunités de Factorisation & Contraintes d'Isolation Hexagonale (`AD-19`)
- **Hiérarchie des couches `lint-imports` (`pyproject.toml`)** :
  - `agents` appartient à la couche supérieure (`bootstrap | orchestration | packs | agents`) au-dessus de `workflows` (`blackboard | ontology | rag | gates | audit_finops | workflows`) et de `ports` (`domain | ports | config | observability | storage`).
  - En conséquence :
    1. `ProcessOrchestrationType` est défini dans `orcia_core/workflows/schemas_v2.py` et ré-exporté dans `orcia_core/agents/reflexive_schemas.py` (`workflows` $\leftarrow$ `agents`, 100 % conforme).
    2. `BoundedWorkflowLauncherPort` (et `UnifiedProcessRunResult`) est défini dans `orcia_core/ports/bounded_workflow_port.py` sans aucun import `orcia_connectors` ni SDK externe.
    3. `ProcessExecutionDispatcher` est implémenté dans `orcia_core/agents/process_dispatcher.py` (couche `agents`, qui peut légitimement importer `NonDeterministicReflexiveRuntime`, `GatePipelineExecutor`, `ClaimCheckStorageService` et `BoundedWorkflowLauncherPort`).
- **Isolation Métier (`test_core_domain_isolation.py`)** : aucun terme spécifique à un pack métier (`jira`, `confluence`, `git_branch`, `wsjf`, `rovo`, `copilot`, `safe`, `prd`) ne doit figurer dans `packages/orcia-core` (code, docstrings ou commentaires).
- **Contrôle de volumétrie (`< 350` lignes par fichier créé/refactorisé)** :
  - Découpage de `WorkflowFiveBlocksCanvas.tsx` (`786` lignes) en sous-composants cohérents (`WorkflowOrchestrationModeSelector.tsx`, `WorkflowBlock2ExecutionSection.tsx`, `WorkflowBlocks1345Sections.tsx`, `WorkflowStudioHeaderAndBanners.tsx`, `studioLabelsAndMappers.ts`).
  - Découpage de `ProcessesHubPage.tsx` (`439` lignes) via l'extraction de `ProcessCatalogCardGrid.tsx`.
  - Extraction des helpers de `bounded_workflow_v2.py` (`577` lignes) dans `bounded_workflow_models.py` afin de ramener chaque module sous `350` lignes.

### 1.4 Décisions sur la Dette Technique & Refactoring Préalable
- **Étape 0 (Pre-Story Refactoring intégré)** :
  1. Découpage modulaire de `WorkflowFiveBlocksCanvas.tsx`, `ProcessesHubPage.tsx` et `bounded_workflow_v2.py` sous `350` lignes par fichier.
  2. Remplacement du store purement mémoire `request.app.state.workflows_v2_store` par une persistance PostgreSQL 18 réelle (`SqlWorkflowDefinitionsV2Store` sur la table existante `workflow_definitions_v2`) doublée d'un cache mémoire synchronisé et du garde RBAC `_enforce_not_observer` (`HTTP 403 ERR_OBSERVER_MODE_READ_ONLY` RFC 9457).
  3. Réalignement du test E2E Playwright `apps/web/e2e/09-pack-builder-and-contextual-help.spec.ts` sur le Hub Processus v2 et le Studio 5-Blocs actuels afin de couvrir en navigateur réel la bascule `Piloté par l'objectif` / `Piloté par les jalons` et la survie au `F5`.
- Aucune dette technique résiduelle hors périmètre nécessitant une Story `16.3a` supplémentaire.

---

## 2. Plan d'Implémentation

### 2.1 Schéma de Données & Migrations Alembic (`infra/migrations/`)
- La table `workflow_definitions_v2` (`id UUID PRIMARY KEY`, `workflow_id`, `slug`, `version`, `status`, `pack_id`, `execution_mode`, `spec_jsonb JSONB`, `updated_at`, `UNIQUE (workflow_id, version)`) existe déjà via la révision `20261108_0910_declarative_packs_and_workflows_v2.py`.
- Le JSONB `spec_jsonb` sérialise nativement `WorkflowDefinitionV2` enrichi (`orchestration_type`, `reflexive_objective`, `allowed_delegate_agents`) sans nécessiter de nouvelle révision Alembic destructive.
- Ajout explicite de `"workflow_definitions_v2"` dans `ORDERED_MUTABLE_TABLES_TO_CLEAR` de `infra/scripts/maintenance/09_reset_db_first_boot.py` pour garantir la vérité terrain Jour 0 (`pnpm db:reset`).

### 2.2 Noyau Hexagonal, Connecteurs & Packs (`packages/orcia-core`, `packages/orcia-connectors`, `packs/`)
1. **`packages/orcia-core/src/orcia_core/workflows/schemas_v2.py`** :
   - Définir `ProcessOrchestrationType(StrEnum)` (`NON_DETERMINISTIC = "non_deterministic"`, `DETERMINISTIC_DBOS = "deterministic_dbos"`).
   - Enrichir `WorkflowDefinitionV2` avec `orchestration_type`, `reflexive_objective: str | None = None` et `allowed_delegate_agents: list[str] = Field(default_factory=list)`.
   - Ré-exporter `ProcessOrchestrationType` dans `orcia_core/workflows/__init__.py` et `orcia_core/agents/reflexive_schemas.py`.
2. **`packages/orcia-core/src/orcia_core/ports/bounded_workflow_port.py`** :
   - Définir les DTOs de domaine (`SubStepAgentExecutionOutcome`, `BoundedWorkflowLaunchInput`, `UnifiedProcessRunResult`) et le `Protocol` `BoundedWorkflowLauncherPort` sans aucune dépendance vers `orcia_connectors`.
3. **`packages/orcia-connectors/src/orcia_connectors/bounded_workflow_models.py` & `bounded_workflow_v2.py`** :
   - Découper les modèles Pydantic (`SubStepExecutionRecord` enrichi de `reflexive_execution_id: str | None = None`, `BoundedWorkflowRunState` enrichi de `orchestration_type`, `reflexive_execution_id`, `trace_events`) dans `bounded_workflow_models.py` (ré-exportés dans `bounded_workflow_v2.py`).
   - Implémenter l'**encapsulation Principe 7** dans `run_bounded_workflow_v2` / `BoundedWorkflowLauncherAdapter` : lorsqu'une sous-étape active a `step_executor_type == "agent_executor"` et qu'un exécuteur réflexif interne est fourni (`allow_sub_agent_delegation=False`), seul le `ClaimCheckPointer` final et `reflexive_execution_id` sont persistés dans `SubStepExecutionRecord` (sans polluer l'état durable avec le scratchpad interne).
4. **`packages/orcia-core/src/orcia_core/agents/process_dispatcher.py`** :
   - Implémenter `ProcessExecutionDispatcher` :
     - `NON_DETERMINISTIC` : exécute `NonDeterministicReflexiveRuntime` (`allow_sub_agent_delegation=True`, `available_delegate_agents=tuple(workflow.allowed_delegate_agents)`, `effort_level=workflow.effort`), soumet le livrable Markdown consolidé à `GatePipelineExecutor.execute_pipeline` (avec auto-correction déterministe bornée à 3 tentatives + Hunters), persiste le livrable corrigé dans `ClaimCheckStorageService` si nécessaire, et retourne `UnifiedProcessRunResult` (`WAITING_FINAL_ANCHOR` / `COMPLETED_APPROVED` / `FAILED_GATES`).
     - `DETERMINISTIC_DBOS` : délègue via `BoundedWorkflowLauncherPort` en injectant un runner réflexif interne pour les sous-étapes `agent_executor` (`allow_sub_agent_delegation=False`).
5. **`packages/orcia-core/src/orcia_core/workflows/_internal/sql_workflows_v2.py`** :
   - Implémenter `SqlWorkflowDefinitionsV2Store` (lecture + upsert idempotent par `(workflow_id, version)` avec clé primaire `UUIDv7` sur PostgreSQL 18).
6. **Packs déclaratifs (`packs/`)** :
   - `packs/orcia-docs/workflows/wf-generate-orcia-documentation.yaml` $\rightarrow$ `orchestration_type: non_deterministic`, `reflexive_objective` métier explicite, `allowed_delegate_agents: [redacteur-documentation-orcia]`.
   - `packs/sdlc/workflows/{wf-01-qualification-prd,wf-03-etude-architecture,wf-06-decoupe-us,wf-08-dev-external-gate}.yaml` $\rightarrow$ `orchestration_type: deterministic_dbos`.

### 2.3 Backend FastAPI & Client OpenAPI (`apps/api`, `packages/api-client`)
1. **`apps/api/src/orcia_api/schemas/process_studio_v2.py` & `dependencies/workflows_v2.py` & `routers/workflows.py`** :
   - Étendre `SaveWorkflowV2Request` (rétrocompatible) avec `orchestration_type`, `reflexive_objective`, `allowed_delegate_agents`, `effort`.
   - Protéger toutes les routes de mutation (`PUT /api/v1/workflows/v2/{workflow_id}`, `POST /api/v1/workflows/v2/{workflow_id}/runs`, `POST /api/v1/runs/{run_id}/hitl-signal`) par `_enforce_not_observer` (`HTTP 403 ERR_OBSERVER_MODE_READ_ONLY` RFC 9457 `application/problem+json` avec `trace_id`).
   - Connecter `GET/PUT /api/v1/workflows/v2*` à `SqlWorkflowDefinitionsV2Store` (initialisé à partir des packs déclaratifs + surcharges SQL persistées) et connecter `POST /api/v1/workflows/v2/{workflow_id}/runs` à `ProcessExecutionDispatcher` (connecté au `ReflexiveExecutionContext` pour que la trace d'exécution soit aussi consultable via `/api/v1/executions/{id}/trace`).
2. **SDK TypeScript (`scripts/export_openapi.py` & `packages/api-client`)** :
   - Régénérer `openapi.json` et `packages/api-client/src/generated/` (`0-diff` gate).
   - Créer `packages/api-client/src/domains/workflowsV2.ts` et exposer `client.workflowsV2` dans `createOrciaApiClient`.

### 2.4 Interface SPA Direction C & Dictionnaire Bilingue (`apps/web`)
1. **`apps/web/src/i18n/locales/{fr,en}.ts` & `types.ts`** :
   - Ajouter la section typée `processOrchestrationModes` portant exactement les libellés bilingues verrouillés (`Processus piloté par l'objectif (adaptatif)` / `Piloté par l'objectif` vs `Processus piloté par les jalons (étapes garanties)` / `Piloté par les jalons`, et équivalents EN `Goal-driven process (adaptive)` / `Goal-driven` vs `Milestone-driven process (guaranteed steps)` / `Milestone-driven`), avec `0` jargon technique.
2. **Studio 5-Blocs (`apps/web/src/features/processes/studio/`)** :
   - Découper `WorkflowFiveBlocksCanvas.tsx` en sous-composants `< 350` lignes.
   - Intégrer en haut du canevas `WorkflowOrchestrationModeSelector` (`data-testid="workflow-orchestration-mode-selector"`, `data-testid="mode-option-goal-driven"`, `data-testid="mode-option-milestone-driven"`) avec `<OrciaIcon />` et variables CSS `tokens.css`.
   - Adapter uniquement le **Bloc 2** (`WorkflowBlock2ExecutionSection.tsx`) selon le mode actif tout en conservant en mémoire les brouillons des deux modes lors des allers-retours.
   - Câbler la sauvegarde et la réhydratation sur `@orcia/api-client` (`client.workflowsV2.listWorkflows()`, `client.workflowsV2.saveWorkflow(...)`) avec bannière d'état explicite (zéro `.catch(() => undefined)`).
3. **Hub Mes Processus & Tiroir d'Exécution (`ProcessesHubPage.tsx`, `ProcessCatalogCardGrid.tsx`, `InteractiveRunDrawer.tsx`)** :
   - Réhydrater la liste des processus depuis `client.workflowsV2.listWorkflows()`, afficher le badge court de mode (`Piloté par l'objectif` / `Piloté par les jalons`) sur chaque carte, et supporter le lancement / suivi des deux modes dans `InteractiveRunDrawer.tsx` via `client.workflowsV2.launchWorkflowRun(...)` et `client.workflowsV2.sendRunHitlSignal(...)`.

---

## 3. Bilan des Modifications & Résultats

### 3.1 Tableau Synthétique des Fichiers Créés et Modifiés

| Fichier | Action & Volumétrie | Rôle & Responsabilité |
| :--- | :--- | :--- |
| `packages/orcia-core/src/orcia_core/workflows/schemas_v2.py` & `__init__.py` | Modification (`310` l.) | Définition de `ProcessOrchestrationType` (`non_deterministic` vs `deterministic_dbos`), enrichissement rétrocompatible de `WorkflowDefinitionV2` (`orchestration_type`, `reflexive_objective`, `allowed_delegate_agents`) et préservation dans `fork_workflow_as_draft`. |
| `packages/orcia-core/src/orcia_core/ports/bounded_workflow_port.py` & `__init__.py` | Création (`115` l.) | Port hexagonal pur `BoundedWorkflowLauncherPort` et DTOs (`SubStepAgentExecutionOutcome`, `BoundedWorkflowLaunchOutcome`, `UnifiedProcessRunResult`) sans aucun import `orcia_connectors`. |
| `packages/orcia-core/src/orcia_core/agents/process_dispatcher.py` & `_internal/dispatcher_helpers.py` | Création (`234` l. / `173` l.) | `ProcessExecutionDispatcher` aiguillant les processus pilotés par l'objectif (`NonDeterministicReflexiveRuntime` avec délégation `depth <= 1` + `GatePipelineExecutor` auto-heal `3x` + `ClaimCheckStorageService`) et les processus pilotés par les jalons (`BoundedWorkflowLauncherPort` avec runner réflexif interne encapsulé). |
| `packages/orcia-core/src/orcia_core/workflows/_internal/sql_workflows_v2.py` | Création (`134` l.) | Adaptateur PostgreSQL 18 `SqlWorkflowDefinitionsV2Store` (`UUIDv7`, `INSERT ... ON CONFLICT (workflow_id, version) DO UPDATE` sur `workflow_definitions_v2`). |
| `packages/orcia-connectors/src/orcia_connectors/bounded_workflow_models.py`, `bounded_workflow_hitl.py` & `bounded_workflow_v2.py` | Découpage & Modif. (`260` l. / `325` l. / `252` l.) | Découpage modulaire sous `350` lignes, implémentation de `BoundedWorkflowLauncherAdapter` et du **Principe 7 d'encapsulation** (`SubStepExecutionRecord` ne persiste que `ClaimCheckPointer` + `reflexive_execution_id`, `0` bloat scratchpad). |
| `packs/orcia-docs/workflows/wf-generate-orcia-documentation.yaml` & `packs/sdlc/workflows/*.yaml` | Modification | Passage de `wf-generate-orcia-documentation.yaml` en `orchestration_type: non_deterministic` (`reflexive_objective` + `allowed_delegate_agents: [redacteur-documentation-orcia]`) et déclaration explicite `orchestration_type: deterministic_dbos` sur les 4 workflows `packs/sdlc`. |
| `apps/api/src/orcia_api/routers/workflows.py`, `_workflows_helpers.py`, `dependencies/reflexive_execution.py` & `09_reset_db_first_boot.py` | Découpage & Modif. (`305` l. / `93` l. / `148` l.) | Injection Composition Root `Depends` (`get_workflows_v2_sql_store`, `get_process_execution_dispatcher`), garde RBAC `_enforce_not_observer` (`HTTP 403 ERR_OBSERVER_MODE_READ_ONLY` RFC 9457), persistance PG18 sur `GET/PUT /api/v1/workflows/v2*` et remise à zéro Jour 0 (`workflow_definitions_v2`). |
| `packages/api-client/src/domains/workflowsV2.ts` & `src/generated/process_studio_v2.d.ts` | Création (`79` l.) & Régénération (`0-diff`) | Régénération automatique OpenAPI 3.1 et domaine SDK typé `workflowsV2` (`listWorkflowsV2`, `getWorkflowV2`, `saveWorkflowV2`, `runWorkflowV2WhatIf`, `launchWorkflowV2Run`, `getRunState`, `sendRunHitlSignal`). |
| `apps/web/src/i18n/locales/process_orchestration_modes_labels.ts`, `fr.ts`, `en.ts`, `types.ts` & `index.tsx` | Création (`120` l.) & Modif. | Dictionnaire bilingue verrouillé `processOrchestrationModes` (`Piloté par l'objectif` / `Goal-driven` vs `Piloté par les jalons` / `Milestone-driven`, `0` jargon technique) et préservation de la locale parente dans `I18nProvider`. |
| `apps/web/src/features/processes/` (`ProcessesHubPage.tsx`, `ProcessCatalogCardGrid.tsx`, `studio/WorkflowFiveBlocksCanvas.tsx`, `studio/useStudioWorkflowController.ts`, `studio/WorkflowOrchestrationModeSelector.tsx`, `studio/WorkflowBlock2ExecutionSection.tsx`, `studio/WorkflowBlocks1345Sections.tsx`, `studio/WorkflowPreviewAndWhatIfPanels.tsx`, `studio/WorkflowStudioHeaderBar.tsx`, `studio/studioLabelsAndMappers.ts`, `studio/studioCatalogLabels.ts`) | Création & Découpage (`< 350` l. chacun) | Refonte modulaire sous `350` lignes/fichier : sélecteur segmenté à 2 cartes (`WorkflowOrchestrationModeSelector` avec `<OrciaIcon />` et aide contextuelle `ⓘ`), Bloc 2 adaptatif préservant les saisies lors des allers-retours, badges de mode sur `/processes`, et persistance `@orcia/api-client` survivant au `F5`. |
| `tests/unit/core/test_process_orchestration_dispatcher.py`, `tests/unit/connectors/test_bounded_workflow_v2_encapsulation.py`, `tests/integration/api/test_story_16_3_dual_mode_processes_api.py`, `apps/web/src/__tests__/story-16-3-dual-mode-processes-studio.test.tsx` & `apps/web/e2e/09-pack-builder-and-contextual-help.spec.ts` | Création & Mise à jour | Suites complètes Couche 1a (`Python pytest`), Couche 1b (`Vitest`), Couche 2 (`Testcontainers PG18 + Redis 7.4`) et Couche 5 (`Playwright E2E` bi-serveur Chromium). |

### 3.2 Résultats Chiffrés, Métriques & Qualité
- **Volumétrie strictement maîtrisée (`< 350` lignes par fichier source créé ou refactorisé)** :
  - Backend : `process_dispatcher.py` (`234` l.), `dispatcher_helpers.py` (`173` l.), `bounded_workflow_port.py` (`115` l.), `sql_workflows_v2.py` (`134` l.), `bounded_workflow_v2.py` (`252` l.), `bounded_workflow_models.py` (`260` l.), `bounded_workflow_hitl.py` (`325` l.), `routers/workflows.py` (`305` l.), `routers/_workflows_helpers.py` (`93` l.), `dependencies/reflexive_execution.py` (`148` l.).
  - Frontend : `ProcessesHubPage.tsx` (`331` l.), `ProcessCatalogCardGrid.tsx` (`248` l.), `WorkflowFiveBlocksCanvas.tsx` (`174` l.), `useStudioWorkflowController.ts` (`246` l.), `WorkflowOrchestrationModeSelector.tsx` (`179` l.), `WorkflowBlock2ExecutionSection.tsx` (`325` l.), `WorkflowBlocks1345Sections.tsx` (`240` l.), `WorkflowPreviewAndWhatIfPanels.tsx` (`169` l.), `WorkflowStudioHeaderBar.tsx` (`197` l.), `studioLabelsAndMappers.ts` (`323` l.), `studioCatalogLabels.ts` (`110` l.), `workflowsV2.ts` (`79` l.).
- **Couverture unitaire Epic 16 / Story 16.3** : **`91.58 %`** (`>= 90 %` requis ; `bounded_workflow_port.py` : `100 %`, `sql_workflows_v2.py` : `98 %`, `schemas_v2.py` : `98 %`, `reflexive_schemas.py` : `98 %`, `bounded_workflow_hitl.py` : `95 %`, `process_dispatcher.py` : `93 %`).
- **Analyse statique, typage strict & frontières modulaires** :
  - `.venv/bin/ruff check .` & `.venv/bin/ruff format --check .` : **`0` erreur** (`700` fichiers conformes).
  - `.venv/bin/mypy --strict packages/orcia-core packages/orcia-connectors apps/api apps/worker` : **`0` erreur** sur `294` fichiers sources.
  - `.venv/bin/lint-imports` : **`5 contracts kept, 0 broken`** (`AD-19` & `AD-20`).
  - `.venv/bin/python scripts/export_openapi.py --check` : **`0-diff`**.
  - `lint_spine.py` : **`0` finding** (`ok: true`).

### 3.3 Validation & Procédure de Test sur Toute la Pyramide (`AD-17` + 5 Garde-Fous de Câblage Vertical)
- **Couche 1a & 1b (Unitaires Python & TypeScript/Vitest)** :
  - Python : **`36 passed`** (`91.58 %` de couverture) validant les défauts et le fork `WorkflowDefinitionV2`, l'aiguillage `ProcessExecutionDispatcher` (`NON_DETERMINISTIC` avec délégation 1 niveau + auto-correction déterministe `3x` + `FAILED_GATES` + `ClaimCheckPointer`, vs `DETERMINISTIC_DBOS`), le **Principe 7 d'encapsulation** (`0` bloat scratchpad dans `SubStepExecutionRecord`, `allow_sub_agent_delegation=False` en sous-étape), le chargement des packs `orcia-docs` et `sdlc`, l'isolation domaine (`0` mot interdit dans `orcia-core`) et l'audit AST anti-patterns.
  - TypeScript Monorepo (`pnpm turbo run lint typecheck test`) : **`9/9` tâches vertes** (`136 passed` au total : `73` `@orcia/ui`, `8` `@orcia/api-client`, `55` `@orcia/web` incluant `story-16-3-dual-mode-processes-studio.test.tsx`, `design-system-look-and-feel-isolation.test.tsx` et `zero-dead-buttons-and-silent-catches-audit.test.tsx`).
- **Couche 2 (Intégration Verticale `HTTP FastAPI ➔ PostgreSQL 18 + Redis 7.4`)** :
  - `.venv/bin/pytest tests/integration/api/test_story_16_3_dual_mode_processes_api.py -v` : **`1 passed` (`12.75s`)** sur conteneurs réels `pgvector/pgvector:pg18` + `redis:7.4.2-alpine`, vérifiant : `GET /api/v1/workflows/v2` bi-mode, rejet `HTTP 403 ERR_OBSERVER_MODE_READ_ONLY` (`application/problem+json` + `trace_id`) pour `claire` sur `PUT` et `POST .../runs`, bascule et sauvegarde `PUT` en brouillon dans `workflow_definitions_v2` vérifiée par `SELECT` SQL direct (`Garde-Fou #2`), exécution complète d'un processus piloté par l'objectif (`wf-generate-orcia-documentation` $\rightarrow$ `reflexive_execution_sessions`) et d'un processus piloté par les jalons (`wf-03-etude-architecture` avec sous-étapes encapsulées Principe 7), survie au `F5` sur une nouvelle instance `create_app()` (`Garde-Fou #3`), et remise à zéro Jour 0 via `09_reset_db_first_boot.py` (`Garde-Fou #4`).
- **Couche 5 (Playwright E2E Réel Bi-Serveur)** :
  - `pnpm --filter @orcia/web exec playwright test e2e/09-pack-builder-and-contextual-help.spec.ts e2e/11-screens-smoke-without-server-errors.spec.ts --project=desktop-cockpit` : **`2 passed (30.5s)`** sur la pile réelle bi-serveur (PostgreSQL 18 + Redis 7.4 + FastAPI + Vite + Chromium), prouvant l'affichage des badges sans jargon sur `/processes`, la bascule `Piloté par l'objectif` / `Piloté par les jalons` dans `/processes/studio/wf-01-qualification-prd`, la persistance réelle PostgreSQL 18 après `localStorage.removeItem` + `page.reload()`, l'ouverture/fermeture de l'aide contextuelle `ⓘ` et `0` erreur HTTP `>= 500`.
- **Audit GitNexus Post-Implémentation (`Garde-Fou #1`) & Synchronisation Site** :
  - `npx gitnexus analyze` + `gitnexus.impact({target: "SqlWorkflowDefinitionsV2Store", direction: "upstream"})` & `gitnexus.impact({target: "ProcessExecutionDispatcher", direction: "upstream"})` : appelants actifs hors `tests/` confirmés dans `apps/api/src/orcia_api/dependencies/reflexive_execution.py` et `apps/api/src/orcia_api/routers/workflows.py` (`0` adaptateur SQL ou service orphelin).
  - `pnpm site:sync && pnpm site:check` & `.venv/bin/python scripts/check_implementation_docs.py` : **`0` erreur**.
