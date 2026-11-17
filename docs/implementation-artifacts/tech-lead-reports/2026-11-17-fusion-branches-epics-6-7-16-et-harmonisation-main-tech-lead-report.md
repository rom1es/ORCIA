# 2026-11-17 — Fusion des Branches Epics 6, 7 & 16 et Harmonisation sur `main`

- **Date** : 2026-11-17
- **Story / Clé Sprint** : `2026-11-17-fusion-branches-epics-6-7-16-et-harmonisation-main` (`Ajustement Transverse`)
- **Capacité(s)** : `CAP-160`, `CAP-200`, `CAP-201`, `CAP-202` — classification : `hygiène`
- **Auteur / Contexte** : Consolidation Git locale sur `main` de l'ensemble des branches non encore fusionnées (`feat/epic-6-audit-ledger-finops-and-human-reversibility` déjà intégrée en `edf1eb3`, `feat/epic-7-observability-autonomous-contracts-and-supervision` fusionnée en `b7e54d4`, et `feat/epic-16-reflexive-agent-harness` `e06e975` issue de `86103b0`), avec réconciliation Alembic (`head` unique), découpage modulaire `< 350` lignes, préservation intégrale des invariants `AD-17` / `AD-19` / `AD-23` / `AD-24`, ré-export OpenAPI 3.1 `0-diff` et synchronisation `pnpm site:sync`.
- **Commits associés** : `b7e54d4` (`Merge branch 'feat/epic-7-observability-autonomous-contracts-and-supervision' into main`), commit de merge `feat/epic-16-reflexive-agent-harness` sur `main` (vérification préalable que `feat/epic-6-audit-ledger-finops-and-human-reversibility` `bbc1c5f` était déjà incluse dans `edf1eb3`).

---

## 1. Analyse du Besoin & Étude d'Impact Tech Lead (Pré-Implémentation)

### 1.1 Contexte & Problématique
- **Situation observée sur les branches locales et `origin`** :
  - `feat/epic-6-audit-ledger-finops-and-human-reversibility` (`bbc1c5f`) est déjà intégrée dans `main` (`edf1eb3`, `Already up to date.`).
  - `feat/epic-7-observability-autonomous-contracts-and-supervision` (`dd22380`, 8 commits) est partie de `edf1eb3` et fusionne sans conflit sur `main` (`b7e54d4`).
  - `feat/epic-16-reflexive-agent-harness` (`e06e975`, 5 commits) a divergé depuis `86103b0` (57 commits de retard par rapport à `edf1eb3`, incluant Epics 17, 18, 19, 6 et 7). La simulation `git merge-tree --write-tree dd22380 e06e975` révèle **26 fichiers en conflit** (`22` fichiers applicatifs/tests/registres et `4` artefacts auto-générés) ainsi que **2 `heads` Alembic parallèles** (`20261117_0705` côté Epic 7 et `20261111_01` côté Epic 16) et **des couplages sémantiques silencieux** sans conflit Git direct.

### 1.2 Exploration, Analyse d'Impact GitNexus, Factorisation & Dette Technique
- **Analyse d'impact & conflits sémantiques identifiés (au-delà des marqueurs Git)** :
  1. **`packages/orcia-connectors/src/orcia_connectors/bounded_workflow_v2.py`** : Epic 16 a extrait `bounded_workflow_models.py` (`312` l.) et `bounded_workflow_hitl.py` (`324` l.) pour ramener `bounded_workflow_v2.py` à `251` l. (`< 350` l.), tandis que `main`/`dd22380` a enrichi le monolithe (`601` l.) avec l'étape **Epic 18 CodeGraph** (`run_codegraph_blast_radius`, `format_codegraph_markdown_section`, `SubStepExecutionRecord.codegraph_impact`, trace `CODEGRAPH_TOOL_EXECUTED`). Il faut conserver la structure modulaire éclatée `< 350` l. et réinjecter le support CodeGraph dans les exécuteurs sync et async.
  2. **`apps/api/src/orcia_api/routers/workflows.py` & `_workflows_helpers.py`** : Une fusion naïve dépasserait `358` l. Le bloc `if payload.publish:` (émission Outbox `WorkflowPublished`, `trigger_dispatcher.handle_workflow_published`, `help_service`) doit être factorisé dans `_workflows_helpers.py`, tout en préservant `_enforce_not_observer`, `await sql_store.upsert_workflow(saved)` et `incoming.model_copy(...)` sur le fork `-draft`.
  3. **`packages/api-client/src/domains/workflowsV2.ts`** (`CONFLICT add/add`) : Epic 7 transmet `workspaceId` via `X-Orcia-Workspace-Id` sur `saveWorkflowV2` (nécessaire pour `WorkflowPublished`), tandis qu'Epic 16 expose 7 méthodes et `personaKey?`. Un 3e paramètre rétro-compatible `workspaceIdOrOptions?: string | { workspaceId?: string; personaKey?: string }` réconcilie tous les appelants sans rupture.
  4. **`packages/ui/src/primitives/AssistantSpeedSelectorAndStreamView.tsx` & `apps/web/src/features/inbox/index.tsx`** : Epic 16 a extrait `AssistantSpeedSelectorTypes.ts`, `AssistantStickyPromptFooter.tsx`, `useInboxPanelController.ts` et `InboxAuxiliaryPanels.tsx` (`< 350` l.) ; Epic 19 sur `main` a ajouté le verrouillage RAG/Embedding (`disabled`, `disabledReasonBanner`, `useActiveEmbeddingModelStatus`, `useRagReindexStatus`, `AssistantNoEmbeddingBanner`, `AssistantReindexingBanner`). Les deux doivent cohabiter dans l'architecture découpée.
  5. **`apps/web/src/features/processes/ProcessesHubPage.tsx` & `WorkflowFiveBlocksCanvas.tsx`** : Epic 16 a extrait `ProcessCatalogCardGrid` + le Studio Dual-Mode (`WorkflowStudioHeaderBar`, `WorkflowOrchestrationModeSelector`, `WorkflowBlock2ExecutionSection`, `WorkflowBlocks1345Sections`, `WorkflowPreviewAndWhatIfPanels`, `useStudioWorkflowController`) ; Epic 7 a extrait `AutonomousRunsSupervisionPanel`, `ProcessesValueStreamOverviewCard`, et monté `AutonomyContractModal` + `WorkflowTriggersModal` (vérifiés par `zero-dead-buttons-and-silent-catches-audit.test.tsx`). Les modales/boutons Epic 7 et `resolvedWorkspaceId` doivent être câblés dans `WorkflowFiveBlocksCanvas.tsx` / `WorkflowStudioHeaderBar.tsx` / `useStudioWorkflowController.ts`, et les 3 anciens sous-composants Studio (`StudioFiveBlocksGrid.tsx`, `StudioWhatIfPanel.tsx`, `StudioWorkflowHeaderBar.tsx`) supprimés pour zéro code mort.
  6. **`apps/web/src/i18n/locales/{fr,en}.ts` & `types.ts`** : Prévention de collision de clés (`upstreamChallengeModal`, `humanGates`, `inboxAndClaims` déjà fournis par `gates_and_inbox_labels.ts` vs `gates_and_modules_labels.ts` d'Epic 16).
  7. **Alembic `head` unique** : `20261111_01_reflexive_execution_sessions.py` (`down_revision = "20261108_0910"`) et `20261117_0705_epic7_review_fk_constraints.py` nécessitent une migration de merge dédiée `20261117_1601_merge_epic7_and_epic16_heads.py` sans modifier les migrations immutables.

---

## 2. Plan d'Implémentation

### 2.1 Schéma de Données & Migrations Alembic (`infra/migrations/versions/`)
- Conservation intacte de `20261111_01_reflexive_execution_sessions.py` (Epic 16) et de toute la chaîne `20261117_0701..0705` (Epic 7).
- Création de `infra/migrations/versions/20261117_1601_merge_epic7_and_epic16_heads.py` :
  - `revision = "20261117_1601"`, `down_revision = ("20261117_0705", "20261111_01")`, `upgrade()` / `downgrade()` en `pass`.
  - Contrôle `.venv/bin/alembic -c infra/migrations/alembic.ini heads` (`1` seule head) et exécution réelle sur PostgreSQL 18 via `testcontainers`.

### 2.2 Noyau Métier Hexagonal, Connecteurs & Workers (`packages/orcia-core/`, `packages/orcia-connectors/`)
- Réconciliation de `orcia_core/orchestration/agents_and_skills_models.py` (alignement `doc_tool`/`issue_tracker`/`git`) et union de `orcia_core/ports/__init__.py` (`embedding`, `log_sink` + `bounded_workflow_port`, `reflexive_runtime_ports`, `surgical_explorer_port`).
- Union de `orcia_connectors/__init__.py`.
- Fusion modulaire de `bounded_workflow_v2.py` + `bounded_workflow_models.py` + `bounded_workflow_hitl.py` (`< 350` l. chacun) en conservant l'exécution async/réflexive d'Epic 16 et l'intégration CodeGraph MCP d'Epic 18.
- Vérification des frontières hexagonales `AD-19` via `.venv/bin/lint-imports`.

### 2.3 Couche Backend API, Sécurité & Contrats (`apps/api/`, `packages/api-client/`)
- Union de `apps/api/src/orcia_api/dependencies/__init__.py`, `errors/registry.py`, et `main.py` (conservation complète des middlewares, `PROBLEM_RESPONSES`, routeurs Epics 6/7/17/18/19 + `sources_surgical_router` et `executions_trace_router`).
- Factorisation de la publication `WorkflowPublished` dans `_workflows_helpers.py` pour garder `workflows.py < 350` l. tout en conservant `_enforce_not_observer`, la persistance SQL `upsert_workflow`, la préservation Dual-Mode du fork `-draft` et les triggers Epic 7.
- Fusion de `packages/api-client/src/domains/workflowsV2.ts` et `index.ts`, puis régénération du schéma OpenAPI 3.1 et des types TS via `.venv/bin/python scripts/export_openapi.py` (`--check` = `0-diff`).

### 2.4 Interface Utilisateur & Expérience (`packages/ui/`, `apps/web/`)
- `@orcia/ui` : maintien de l'extraction `AssistantSpeedSelectorTypes.ts` + `AssistantStickyPromptFooter.tsx` (`< 350` l.) enrichis avec `disabled` et `disabledReasonBanner` (Epic 19).
- `apps/web/src/features/inbox/` : maintien du découpage `useInboxPanelController.ts` + `InboxAuxiliaryPanels.tsx` + `index.tsx` (`< 350` l.) avec réintégration complète de `useActiveEmbeddingModelStatus`, `useRagReindexStatus`, `AssistantNoEmbeddingBanner` et `AssistantReindexingBanner`.
- `apps/web/src/features/processes/` : combinaison dans `ProcessesHubPage.tsx` de `ProcessCatalogCardGrid` (Epic 16) + `AutonomousRunsSupervisionPanel` & `ProcessesValueStreamOverviewCard` (Epic 7) ; intégration dans `WorkflowFiveBlocksCanvas.tsx` + `WorkflowStudioHeaderBar.tsx` + `useStudioWorkflowController.ts` des boutons/modales `AutonomyContractModal` & `WorkflowTriggersModal` + `resolvedWorkspaceId` ; suppression des 3 fichiers devenus orphelins (`StudioFiveBlocksGrid.tsx`, `StudioWhatIfPanel.tsx`, `StudioWorkflowHeaderBar.tsx`).
- Harmonisation i18n (`fr.ts`, `en.ts`, `types.ts`, `gates_and_modules_labels.ts`), registres (`epics.md`, `sprint-status.yaml`, `capabilities.yaml`, `tech-lead-reports/README.md`) et synchronisation `pnpm site:sync` / `pnpm site:check`.

### 2.5 Analyse d'Impact sur la Pyramide des Tests (`AD-17` — Couches 1 à 5 + Sécurité)
- **Couche 1a & 1b** : Fusion de `vitest.setup.ts` et `zero-dead-buttons-and-silent-catches-audit.test.tsx` ; exécution complète de `pytest tests/unit packages/orcia-connectors/tests` (`>= 90%`, incl. `test_codebase_architectural_anti_patterns_audit.py`) et `pnpm turbo run lint typecheck test`.
- **Couche 2 (`HTTP ➔ PostgreSQL 18`)** : Exécution des tests d'intégration `testcontainers` PostgreSQL 18 pour Epic 7 (`test_epic_7_composition_root_postgres18.py`) et Epic 16 (`test_story_16_1..3*.py`).
- **Couche 3 (`Contrats & Hygiène`)** : `ruff check`, `ruff format --check`, `mypy --strict`, `lint-imports`, `lint_spine.py`, `export_openapi.py --check`, `pnpm site:check`, `check_implementation_docs.py`.
- **Couche Sécurité & Couche 5** : Vérification des tests sécurité et audit zéro bouton muet / zéro catch silencieux sur l'arbre fusionné.

---

## 3. Bilan des Modifications & Résultats (Post-Implémentation)

### 3.1 Fichiers Développés & Modifiés
| Fichier | Nature (Création / Modification / Suppression) | Description synthétique |
| :--- | :--- | :--- |
| `infra/migrations/versions/20261117_1601_merge_epic7_and_epic16_heads.py` | Création (`19` l.) | Révision Alembic de merge reliant `("20261117_0705", "20261111_01")` pour préserver une `head` SQL unique sans éditer les migrations immutables. |
| `packages/orcia-core/src/orcia_core/orchestration/agents_and_skills_models.py`, `ports/__init__.py`, `ports/bounded_workflow_port.py` | Harmonisation | Alignement `doc_tool`/`issue_tracker`/`git` sur `HEAD`, union triée des ports Epics 6/7/16/19 et propagation `codegraph_impact` sur `BoundedWorkflowSubStepDto`. |
| `packages/orcia-connectors/src/orcia_connectors/{__init__.py,bounded_workflow_models.py,bounded_workflow_hitl.py,bounded_workflow_v2.py}` | Refactoring & Harmonisation (`319`/`338`/`266` l.) | Conservation de l'architecture modulaire `< 350` l. d'Epic 16 avec réinjection complète de `run_codegraph_blast_radius`, `format_codegraph_markdown_section` et de l'événement `CODEGRAPH_TOOL_EXECUTED` d'Epic 18. |
| `apps/api/src/orcia_api/{dependencies/__init__.py,errors/registry.py,main.py,routers/_workflows_helpers.py,routers/workflows.py}` | Harmonisation (`137`/`307` l.) | Union des dépendances/erreurs/routeurs (`sources_surgical_router`, `executions_trace_router`), extraction de `publish_workflow_outbox_event` dans `_workflows_helpers.py`, préservation `_enforce_not_observer`, `upsert_workflow`, `WorkflowPublished` et fork `-draft`. |
| `packages/api-client/{openapi.json,src/generated/*,src/domains/workflowsV2.ts,src/index.ts}` | Régénération & Harmonisation (`92`/`110` l.) | Contrat OpenAPI 3.1 `0-diff`, support rétro-compatible `string \| { workspaceId?, personaKey? }` et header `X-Orcia-Workspace-Id` sur `saveWorkflowV2`. |
| `packages/ui/src/primitives/{AssistantSpeedSelectorTypes.ts,AssistantStickyPromptFooter.tsx,AssistantSpeedSelectorAndStreamView.tsx}` | Harmonisation (`104`/`260`/`323` l.) | Découpage modulaire `< 350` l. conservé avec réintégration de `disabled`, `disabledReasonBanner` et des gardes d'envoi/clavier Epic 19. |
| `apps/web/src/features/inbox/{index.tsx,useInboxPanelController.ts,InboxAuxiliaryPanels.tsx}` | Harmonisation (`344`/`299`/`217` l.) + Suppression (`AssistantGovernanceDialog.tsx`) | Trace réflexive & inspecteur chirurgical combinés avec `useActiveEmbeddingModelStatus`, `useRagReindexStatus`, `AssistantNoEmbeddingBanner` et `AssistantReindexingBanner`. |
| `apps/web/src/features/processes/{ProcessesHubPage.tsx,studio/WorkflowFiveBlocksCanvas.tsx,studio/WorkflowStudioHeaderBar.tsx,studio/useStudioWorkflowController.ts}` | Harmonisation (`253`/`287`/`248`/`276` l.) + Suppression 3 orphelins (`StudioFiveBlocksGrid.tsx`, `StudioWhatIfPanel.tsx`, `StudioWorkflowHeaderBar.tsx`) | Hub combinant `ProcessCatalogCardGrid`, `AutonomousRunsSupervisionPanel` et `ProcessesValueStreamOverviewCard` ; Studio Dual-Mode câblé avec `resolvedWorkspaceId`, `useWorkflowAutonomyContract`, `useWorkflowTriggers`, `AutonomyContractModal` et `WorkflowTriggersModal`. |
| `apps/web/src/i18n/{types.ts,locales/fr.ts,locales/en.ts}` | Harmonisation (`90`/`331`/`331` l.) + Suppression (`gates_and_modules_labels.ts`) | Union complète des dictionnaires Epics 6/7/16/17/18/19 sans clé dupliquée. |
| `apps/web/src/__tests__/{vitest.setup.ts,zero-dead-buttons-and-silent-catches-audit.test.tsx}` | Harmonisation | Union `MockBackendState` / `vitestFetchTransport` (routage prioritaire `/autonomy-contract` et `/triggers` avant `/workflows/v2/{id}`) et `requiredPropsByComponent`. |
| `tests/integration/api/{test_epic_7_composition_root_postgres18.py,test_story_7_1_*,test_story_7_2_*,test_story_7_4_*,test_story_17_3_iam_accounts_and_secops_postgres18.py}` | Adaptation fixture SQL | Remplacement des 4 `alembic downgrade -1` par leurs révisions cibles explicites face au mergepoint `20261117_1601` et passage de `DROP TABLE iam_accounts CASCADE` dans `test_story_17_3` (FK Epic 7 `autonomy_contracts_service_principal_id_fkey`). |
| `docs/{planning-artifacts/epics.md,implementation-artifacts/sprint-status.yaml,implementation-artifacts/tech-lead-reports/README.md,product/capabilities.yaml}`, `apps/web/src/generated/orciaSiteManifest.ts`, `docs/site-catalog/index.html` | Documentation & Synchronisation | Epics 6/7/16–19 consolidés, surfaces UI `CAP-201` actualisées et manifeste showcase régénéré (`pnpm site:sync`). |

### 3.2 Résultats Chiffrés, Métriques & Qualité
- **Couverture de tests Python (`packages/orcia-core`)** : **`91.58 %`** (`20 869` stmts, `1 202` miss, `4 538` branches, `734` partial) via `.venv/bin/pytest --cov=packages/orcia-core --cov-fail-under=90` — exécution complète : `779 passed, 1 failed, 0 skipped` (`0:19:59`), suivie du correctif `DROP TABLE iam_accounts CASCADE` dans `tests/integration/api/test_story_17_3_iam_accounts_and_secops_postgres18.py` et ré-exécution ciblée verte (`2 passed in 23.43s`). Note : le run isolé sur `tests/unit` seul atteint `587 passed` (`84.20 %`), les adaptateurs SQL/Redis `_internal` étant couverts sur de vrais conteneurs PostgreSQL 18 / Redis dans `tests/integration/`.
- **Tests TypeScript / UI / Web (`pnpm turbo run lint typecheck test`)** : **`9/9` tâches réussies** (`@orcia/api-client`: `2` fichiers / `13` tests ; `@orcia/ui`: `26` fichiers / `110` tests ; `@orcia/web`: `34` fichiers / `141` tests ; total `62` fichiers / `264` tests passés ; ESLint et `tsc --noEmit` à `0` erreur).
- **Qualité statique, Architecture & Documentation** :
  - `.venv/bin/ruff check .` & `.venv/bin/ruff format --check .` : `0` erreur (`1 062` fichiers formatés).
  - `.venv/bin/mypy --strict packages/orcia-core packages/orcia-connectors apps/api apps/worker` : `0` erreur sur `486` fichiers source.
  - `.venv/bin/lint-imports` : `5 contracts kept, 0 broken` (`531` fichiers, `3 732` dépendances).
  - `.venv/bin/python .agent/skills/bmad-architecture/scripts/lint_spine.py` : `ok: true`, `total_findings: 0`.
  - `.venv/bin/alembic -c infra/migrations/alembic.ini heads` : `20261117_1601 (head)` (tête unique).
  - `.venv/bin/python scripts/export_openapi.py --check` : `0` écart (`0-diff`).
  - `pnpm site:sync && pnpm site:check` : `63/63` capacités live testées, `158` rapports, `26` routes, `126` primitives UI synchronisés.
  - `gitnexus analyze` & `detect-changes` : vérifiés post-commit sur `main`.

### 3.3 Validation & Procédure de Test sur Toute la Pyramide (`AD-17`)
- **Couche 1a & 1b (Unitaires Python & Frontend TS)** : `pytest tests/unit` (`587 passed`, incluant `test_codebase_architectural_anti_patterns_audit.py` et `test_bounded_workflow_v2_encapsulation.py`), Vitest (`264` tests sur `@orcia/api-client`, `@orcia/ui`, `@orcia/web`, incluant `zero-dead-buttons-and-silent-catches-audit.test.tsx`).
- **Couche 2 (Intégration Verticale `HTTP ➔ PostgreSQL 18` / Redis `testcontainers`)** : `test_epic_7_composition_root_postgres18.py`, `test_story_7_1_autonomy_contracts_postgres18.py`, `test_story_7_2_triggers_concurrency_postgres18.py`, `test_story_7_4_supervision_rollback_postgres18.py`, `test_story_16_1_sources_surgical_api.py`, `test_story_16_2_reflexive_runtime_and_sse_postgres18.py`, `test_story_16_3_dual_mode_processes_api.py` (`9 passed in 107.09s`, prouvant `alembic upgrade head` jusqu'à `20261117_1601`) et `test_story_17_3_iam_accounts_and_secops_postgres18.py` (`2 passed in 23.43s`).
- **Couche 3 (Contrats & Architecture)** : `export_openapi.py --check`, `lint-imports` (`5/5` contrats), `lint_spine.py` (`0` finding), `pnpm site:check`.
- **Couche Sécurité (`tests/security`)** : `95 passed, 1 warning in 19.63s`.
- **Couche 4 & 5** : incluses dans l'exécution complète `pytest` (couche evals `0 $`) et validées lors des merges respectifs des branches Epics 6, 7 et 16 ; la suite Vitest vérifie la non-régression d'interface et la survie au démontage/remontage `F5` des parcours Studio V2, Triggers, Supervision autonome, Trace réflexive et Verrouillage RAG.
