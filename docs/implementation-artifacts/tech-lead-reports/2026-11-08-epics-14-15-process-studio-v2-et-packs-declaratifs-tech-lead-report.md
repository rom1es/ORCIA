# Epics 14 & 15 — Simplification Architecturale des Packs/Connecteurs (`orcia-connectors` + `packs/` Déclaratifs) & ORCIA Process Studio v2

- **Date** : 2026-11-08
- **Story / Clé Sprint** : `epic-14` (`14-1`..`14-5` — ORCIA Process Studio v2, traduisant `specs/epic-09-process-studio`) & `epic-15` (`15-1`..`15-3` — Simplification Architecturale des Packs & Connecteurs, traduisant `specs/epic-10-packs-simplification`)
- **Capacité(s)** : `CAP-054`, `CAP-055`, `CAP-056`, `CAP-083` (mises à jour) + nouvelles capacités `CAP-140` (`ORCIA Process Studio v2 — Cartographie VSM, Studio 5 Blocs Control-M, Gates Auto-Heal 3x & Portail HITL 4 Actions`) et `CAP-150` (`Architecture Unifiée Core/Connectors & Packs 100 % Déclaratifs`) — classification : `feature`
- **Auteur / Contexte** : Implémentation intégrale et ordonnée des tâches `TASK-01` à `TASK-08` (`specs/epic-09-process-studio/03-antigravity-tasks-breakdown.md`), en respectant les **7 Règles d'Or Architecturales Non-Négociables** et le prototype de référence `Workflow agentique 2 (1).html`.
- **Commits associés** : `pending`

---

## 1. Analyse du Besoin & Étude d'Impact Tech Lead (Pré-Implémentation)

### 1.1 Contexte & Problématique
- **Traduction dans la numérotation du Sprint (`Epics 14 & 15`)** : Les Epics `9` et `10` étant déjà occupées et terminées dans `docs/planning-artifacts/epics.md` et `docs/implementation-artifacts/sprint-status.yaml` (`Epic 9` : Coquille 4 Zones Direction C, `Epic 10` : Mon Assistant Tout-en-Un), les spécifications `specs/epic-09-process-studio/` et `specs/epic-10-packs-simplification/` sont intégrées comme **Epic 14 (ORCIA Process Studio v2)** et **Epic 15 (Simplification Architecturale des Packs & Connecteurs)** dans `epics.md`, `sprint-status.yaml` et `capabilities.yaml`.
- **7 Règles d'Or Architecturales Non-Négociables** :
  1. **Simplification des Packages Python (`packages/`)** : Il ne subsiste que **2 packages Python backend** dans `packages/` :
     - `packages/orcia-core` : absorbe `packages/orcia-kernel` dans `orcia_core.kernel` (avec alias de compatibilité transitoire du module `orcia_kernel` pointant vers `orcia_core.kernel`), gère DBOS, le Permission Broker, les 4 runners déterministes génériques de Gates, le stockage S3 Claim-Check (`ClaimCheckPointer`) et le `DeclarativePackLoader`.
     - `packages/orcia-connectors` : regroupe tous les connecteurs techniques (`atlassian_jira.py`, `atlassian_confluence.py`, `git_provider.py`, `sql_readonly.py`, `mcp_client_bridge.py`) derrière l'interface unique `OrciaConnectorProtocol` à 4 méthodes (`healthcheck`, `read`, `preview_write`, `execute_write`).
  2. **Packs 100 % Déclaratifs (`packs/<domaine>/`)** : Aucun code Python ni React dans un Pack métier. Conversion de `packages/orcia-pack-sdlc` et `packages/orcia-pack-builder` vers `packs/sdlc/` et `packs/orcia-docs/` (YAML + Markdown uniquement), et suppression définitive de `packages/orcia-pack-sdlc/`, `packages/orcia-pack-builder/` et `packages/orcia-kernel/`.
  3. **Zéro Fuite Métier dans `orcia-core`** : Aucun mot-clé `jira`, `confluence`, `git`, `git_branch`, `prd`, `wsjf`, `rovo`, `copilot` ou `safe` dans `packages/orcia-core` (vérifié par `tests/unit/core/test_core_domain_isolation.py`).
  4. **Séparation Chaîne de Valeur (Macro-VSM) vs Workflows Unitaires Bornés** : La chaîne de 11 étapes, 4 phases, 5 points de passage humains et 8 boucles de retour du POC HTML (`Workflow agentique 2 (1).html`) est chargée depuis `packs/sdlc/workflows/vsm-mon-compte-idea-to-prod.yaml` (`ValueStreamMapSpec`), et chaque étape outillée pointe vers un workflow DBOS court et autonome (`wf-01-qualification-prd.yaml`, `wf-03-etude-architecture.yaml`, `wf-06-decoupe-us.yaml`, `wf-08-dev-external-gate.yaml`).
  5. **Zéro « Agent Orchestrateur » lisant le chat (`ADR-01` & `ADR-02`)** : Toutes les transitions entre sous-étapes sont pilotées par `DeterministicSubStepSpec` et des signaux DBOS (`DBOS.recv`).
  6. **Pipeline de Gates (`ADR-06`)** : Les 4 runners déterministes génériques (`markdown_contract_runner`, `json_schema_runner`, `cli_sandbox_runner`, `catalog_invariant_runner`) s'exécutent toujours en premier avec auto-remédiation bornée (`max_self_heal_retries = 3`) avant d'invoquer les agents contradicteurs/évaluateurs probabilistes.
  7. **Claim-Check S3 & Idempotence Cyclique** : Tout artefact ou diff $> 4\text{ Ko}$ est stocké dans SeaweedFS via `ClaimCheckPointer(s3_uri, sha256, byte_size)`. Toute clé d'idempotence d'étape inclut `:iter-{iteration}` (`f"{run_id}:{sub_step.id}:iter-{iteration}"`) pour permettre les boucles de retour en mode `corrections`.

### 1.2 Exploration, Analyse d'Impact GitNexus, Factorisation & Dette Technique
- **Analyse d'Impact GitNexus (`gitnexus_query`, `gitnexus_impact`)** :
  - `OrciaDomainError` (`packages/orcia-kernel/src/orcia_kernel/errors.py`) : `impactedCount = 62` (`55` direct callers dans `Orchestration`, `4` dans `Gates`, `risk: CRITICAL`).
  - `orcia_pack_sdlc` & `orcia_pack_builder` : `29` et `6` références dans `apps/api/src/orcia_api/routers/pack_builder.py`, `jira_and_mcp.py`, `dependencies/core_and_lifespan.py` et les tests unitaires.
- **Stratégie de Migration Sans Régression (`orcia_kernel` $\rightarrow$ `orcia_core.kernel`)** :
  - Intégrer `ids.py`, `enums.py`, `errors.py`, `events.py`, `ports.py`, `context_ports.py`, `connector_ports.py`, `secret_ports.py` dans `packages/orcia-core/src/orcia_core/kernel/`.
  - Exposer `orcia_kernel` depuis `packages/orcia-core/src/` (ou alias `sys.modules["orcia_kernel"] = orcia_core.kernel` + mise à jour des imports) tout en supprimant le dossier `packages/orcia-kernel/` afin que `packages/` ne contienne plus que `orcia-core` et `orcia-connectors` côté Python (ainsi que `ui` et `api-client` côté TypeScript).
- **Purge des Fuites Métier dans `packages/orcia-core`** :
  - Nettoyage de `permissions/seeds.py`, `permissions/__init__.py`, `permissions/errors.py`, `bootstrap/seeder.py`, `rag/`, `ontology/`, `orchestration/` pour remplacer toute mention de `jira`, `confluence`, `git`, `prd`, `wsjf`, `rovo`, `copilot`, `safe` par des termes et schémas agnostiques (`issue_tracker`, `knowledge_wiki`, `source_repo`, `work_item`, `priority_score`, `external_assistant`, `agile_framework`) ou les déléguer à `packages/orcia-connectors` et `packs/sdlc/`.

---

## 2. Plan d'Implémentation (`TASK-01` à `TASK-08`)

### 2.1 Schéma de Données & Migrations Alembic (`TASK-02`)
- `infra/migrations/versions/0028_20261108_0910_declarative_packs_and_workflows_v2.py` (et alias `20261108_0910_declarative_packs_and_workflows_v2.py`) :
  - Création des tables `declarative_pack_bundles`, `vsm_definitions_v2`, `workflow_definitions_v2`, `workflow_runs_v2` et `claim_check_artifacts` avec clés primaires `UUIDv7`, empreintes `SHA-256`, compteur `iteration_index` et réversibilité complète (`upgrade()` / `downgrade()`).

### 2.2 Noyau Métier Hexagonal, Connecteurs, Packs Déclaratifs & Workers (`TASK-01`, `TASK-02`, `TASK-03`, `TASK-04`, `TASK-05`)
- **`TASK-01` (`packages/orcia-connectors` & `orcia_core.kernel`)** :
  - `packages/orcia-connectors/pyproject.toml` & `src/orcia_connectors/protocol.py` (`OrciaConnectorProtocol`, `ConnectorHealthStatus`, `WritePreviewCard`, `SignedApprovalToken`, vérification HMAC/SHA-256 du *Permission Broker*).
  - Adaptateurs dans `packages/orcia-connectors/src/orcia_connectors/adapters/` : `atlassian_jira.py`, `atlassian_confluence.py`, `git_provider.py`, `sql_readonly.py`, `mcp_client_bridge.py` (+ services de staging Jira migrés depuis `orcia-pack-sdlc`).
  - Fusion de `orcia-kernel` dans `packages/orcia-core/src/orcia_core/kernel/`.
  - Test unitaire : `tests/unit/connectors/test_connector_protocol_and_write_preview.py`.
- **`TASK-02` (`schemas_v2.py`, `claim_check.py`, `loader.py` & Isolation Core)** :
  - `packages/orcia-core/src/orcia_core/workflows/schemas_v2.py` (`ClaimCheckPointer`, `ValueStreamMapSpec`, `WorkflowDefinitionV2`, `DeterministicSubStepSpec`, `StepControlsPipeline`).
  - `packages/orcia-core/src/orcia_core/storage/claim_check.py` (`ClaimCheckStorageService` stockant tout artefact ou diff $> 4\text{ Ko}$ sous `s3://orcia-artifacts/...` avec `sha256` et `byte_size`).
  - `packages/orcia-core/src/orcia_core/packs/loader.py` (`DeclarativePackLoader` et `PackExporter` `.zip`).
  - Test unitaire : `tests/unit/core/test_core_domain_isolation.py`.
- **`TASK-03` (`packs/sdlc/`, `packs/orcia-docs/` & Suppression des anciens packages)** :
  - `packs/sdlc/` : `pack.yaml`, `glossary.yaml`, `agents/*.md`, `skills/*.md`, `gates/*.{yaml,md}`, `workflows/vsm-mon-compte-idea-to-prod.yaml` (fidèle à `Workflow agentique 2 (1).html`), `wf-01-qualification-prd.yaml`, `wf-03-etude-architecture.yaml`, `wf-06-decoupe-us.yaml`, `wf-08-dev-external-gate.yaml`.
  - `packs/orcia-docs/` : `pack.yaml`, `glossary.yaml`, `agents/redacteur-documentation-orcia.md`, `skills/*.md`, `gates/*.yaml`, `workflows/*.yaml`.
  - Suppression définitive de `packages/orcia-pack-sdlc/`, `packages/orcia-pack-builder/` et `packages/orcia-kernel/`.
  - Test unitaire : `tests/unit/packs/test_declarative_packs_loading.py`.
- **`TASK-04` (4 Runners Déterministes Génériques & `GatePipelineExecutor`)** :
  - `packages/orcia-core/src/orcia_core/workflows/gates/runners.py` (`markdown_contract_runner`, `json_schema_runner`, `cli_sandbox_runner`, `catalog_invariant_runner`) et `pipeline.py` (`GatePipelineExecutor` avec Fail-Fast, Auto-Heal borné à `max_self_heal_retries = 3`, puis exécution des Hunters probabilistes uniquement si `100 % NOMINAL`).
  - Test unitaire : `tests/unit/core/test_generic_gate_runners_and_auto_heal.py`.
- **`TASK-05` (`run_bounded_workflow_v2` DBOS & Routes FastAPI `workflows.py` / `packs.py`)** :
  - `apps/worker/src/orcia_worker/workflows/bounded_workflow_v2.py` (`run_bounded_workflow_v2` avec clés `f"{run_id}:{sub_step.id}:iter-{iteration}"`, modes `NATIVE_ORCIA` et `EXTERNAL_DELEGATED_GATE`, signaux HITL `APPROVE`, `AMEND_DIFF`, `REJECT_RETRY_SUBSTEP`, `REJECT_AND_LOOP`, `SUSPEND_SLA`).
  -Test d'intégration : `tests/integration/api/test_dbos_return_loops_and_claim_check.py`.

### 2.3 Couche Backend API, Sécurité & Contrats (`TASK-05`)
- `apps/api/src/orcia_api/routers/packs.py` & `apps/api/src/orcia_api/routers/workflows.py` :
  - `GET /api/v1/packs`, `POST /api/v1/packs/export/{workspace_id}`
  - `GET /api/v1/vsm`, `GET /api/v1/workflows/v2`, `PUT /api/v1/workflows/v2/{id}`, `POST /api/v1/workflows/v2/{id}/what-if`, `POST /api/v1/workflows/v2/{id}/runs`, `POST /api/v1/runs/{run_id}/hitl-signal`.

### 2.4 Interface Utilisateur & Expérience (`TASK-06`, `TASK-07`, `TASK-08`)
- **`TASK-06`** : `apps/web/src/features/settings/packs/PacksRegistryPage.tsx` (`/settings/packs`) & `apps/web/src/features/processes/ProcessesHubPage.tsx` (`/processes`).
- **`TASK-07`** : `apps/web/src/features/processes/vsm/ValueStreamMapView.tsx`, `ReturnLoopsSvgOverlay.tsx`, `StepDetailSheet.tsx` (`/processes/vsm/$vsmId`), restituant fidèlement `Workflow agentique 2 (1).html` (commutateur `Aujourd'hui | Avec les agents | Comparer`, 4 phases, 11 étapes, 5 losanges de passage, 8 boucles de retour SVG sans collision, fiche 6 onglets, tiroir opportunités `P1..P3`, mode `Présenter`).
- **`TASK-08`** : `apps/web/src/features/processes/studio/StudioCopilotSidebar.tsx`, `WorkflowFiveBlocksCanvas.tsx` (`/processes/studio/$workflowId`) & `apps/web/src/features/processes/execution/InteractiveRunDrawer.tsx` (Portail HITL à 4 actions souveraines + `WritePreviewCard`).

### 2.5 Analyse d'Impact sur la Pyramide des Tests (`AD-17`)
- **Couche 1a (Unitaires Python)** :
  - `tests/unit/connectors/test_connector_protocol_and_write_preview.py`
  - `tests/unit/core/test_core_domain_isolation.py`
  - `tests/unit/packs/test_declarative_packs_loading.py`
  - `tests/unit/core/test_generic_gate_runners_and_auto_heal.py`
- **Couche 1b (Unitaires/Composants TS `Vitest`)** :
  - Tests des vues `PacksRegistryPage`, `ProcessesHubPage`, `ValueStreamMapView`, `WorkflowFiveBlocksCanvas`, `InteractiveRunDrawer`.
- **Couche 2 (Intégration Verticale)** :
  - `tests/integration/api/test_dbos_return_loops_and_claim_check.py`.
- **Couche 3 (Contrats & Architecture)** :
  - `lint-imports`, `ruff check`, `mypy`, `pnpm lint`, `pnpm typecheck`, `pnpm site:check`.

---

## 3. Bilan des Modifications & Résultats (Post-Implémentation)

### 3.1 Tableau Synthétique des Fichiers Créés, Modifiés & Supprimés
| Tâche | Fichiers Créés / Modifiés / Supprimés | Rôle & Responsabilité |
| :--- | :--- | :--- |
| **`TASK-01`** | `packages/orcia-connectors/pyproject.toml`, `src/orcia_connectors/protocol.py`, `src/orcia_connectors/adapters/{atlassian_jira,atlassian_confluence,git_provider,sql_readonly,mcp_client_bridge}.py`, `packages/orcia-core/src/orcia_core/kernel/*` | Package unifié `orcia-connectors` (`OrciaConnectorProtocol` à 4 méthodes + `WritePreviewCard` / `SignedApprovalToken`) et fusion de `orcia-kernel` dans `orcia_core.kernel`. |
| **`TASK-02`** | `packages/orcia-core/src/orcia_core/workflows/schemas_v2.py`, `storage/claim_check.py`, `packs/loader.py`, `infra/migrations/versions/20261108_0910_declarative_packs_and_workflows_v2.py` | Schémas agnostiques `ValueStreamMapSpec` & `WorkflowDefinitionV2`, stockage S3 Claim-Check (`> 4 Ko`) et chargeur `DeclarativePackLoader` + `PackExporter` `.zip`. |
| **`TASK-03`** | `packs/sdlc/**`, `packs/orcia-docs/**`, suppression définitive de `packages/orcia-pack-sdlc/`, `packages/orcia-pack-builder/`, `packages/orcia-kernel/` | Conversion 100 % déclarative (YAML + Markdown) des Packs SDLC (11 étapes VSM + 4 workflows DBOS bornés extraits de `Workflow agentique 2 (1).html`) et Documentation ORCIA. |
| **`TASK-04`** | `packages/orcia-core/src/orcia_core/workflows/gates/{runners.py,pipeline.py,__init__.py}` | 4 runners déterministes génériques (`markdown_contract_runner`, `json_schema_runner`, `cli_sandbox_runner`, `catalog_invariant_runner`) + pipeline Fail-Fast / Auto-Heal (`max 3` essais) avant agents contradicteurs. |
| **`TASK-05`** | `apps/worker/src/orcia_worker/workflows/bounded_workflow_v2.py`, `apps/api/src/orcia_api/schemas/process_studio_v2.py`, `apps/api/src/orcia_api/routers/{packs.py,workflows.py}` | Exécution DBOS bornée (`:iter-{iteration}`, `NATIVE_ORCIA` & `EXTERNAL_DELEGATED_GATE`), simulation *What-If* (`0` écriture externe), signaux HITL 4 actions et routes FastAPI. |
| **`TASK-06`** | `apps/web/src/features/settings/packs/PacksRegistryPage.tsx`, `apps/web/src/features/processes/ProcessesHubPage.tsx` | Registre des Packs déclaratifs (`/settings/packs`, santé connecteurs MCP + export `.zip`) et Hub des Processus (`/processes`, séparation Macro-VSM vs Workflows unitaires DBOS). |
| **`TASK-07`** | `apps/web/src/features/processes/vsm/{ValueStreamMapView.tsx,ReturnLoopsSvgOverlay.tsx,StepDetailSheet.tsx}` | Cartographie VSM interactive 11 étapes (`/processes/vsm/$vsmId`), commutateur 3 modes (`Aujourd'hui | Avec les agents | Comparer`), 12 boucles de retour SVG sans collision, fiche 6 onglets, tiroir opportunités `P1..P3` et mode `Présenter`. |
| **`TASK-08`** | `apps/web/src/features/processes/studio/{WorkflowFiveBlocksCanvas.tsx,StudioCopilotSidebar.tsx}`, `apps/web/src/features/processes/execution/InteractiveRunDrawer.tsx` | Studio 5 Blocs Control-M (`/processes/studio/$workflowId`), auto-fork `-draft` persistant au `F5`, Copilot `[+]` et tiroir d'arbitrage HITL à 4 actions souveraines sur Diff S3. |

### 3.2 Validation des 7 Règles d'Or & Pyramide de Tests (`AD-17`)
- **`TASK-01`** : `pytest tests/unit/connectors/test_connector_protocol_and_write_preview.py` $\rightarrow$ **`3 passed`**.
- **`TASK-02`** : `pytest tests/unit/core/test_core_domain_isolation.py` $\rightarrow$ **`4 passed`** (`0` mot-clé métier SDLC dans `orcia-core`).
- **`TASK-03`** : `pytest tests/unit/packs/test_declarative_packs_loading.py` $\rightarrow$ **`3 passed`** (`0` fichier `.py`/`.ts`/`.tsx` dans `packs/`, uniquement `orcia-core` et `orcia-connectors` côté Python dans `packages/`).
- **`TASK-04`** : `pytest tests/unit/core/test_generic_gate_runners_and_auto_heal.py` $\rightarrow$ **`3 passed`**.
- **`TASK-05`** : `pytest tests/integration/api/test_dbos_return_loops_and_claim_check.py` $\rightarrow$ **`4 passed`**.
- **`TASK-06` à `TASK-08`** : `vitest run src/__tests__/epics-14-15-process-studio-v2-and-declarative-packs.test.tsx` $\rightarrow$ **`3 passed`** + `design-system-look-and-feel-isolation.test.tsx` (**`4 passed`**) + `zero-dead-buttons-and-silent-catches-audit.test.tsx` (**`7 passed`**).
- **Qualité & Typage** : `.venv/bin/ruff check` (**`All checks passed!`**), `pnpm lint` (**`3/3 passed`**), `pnpm typecheck` (**`3/3 passed`**).
