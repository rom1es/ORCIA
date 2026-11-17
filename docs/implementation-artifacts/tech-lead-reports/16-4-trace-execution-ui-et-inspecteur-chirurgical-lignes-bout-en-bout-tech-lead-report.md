# Rapport Tech Lead & Bilan d'Implémentation — Story 16.4 : Trace d'Exécution Vivante (`<AgentExecutionTrace />`), Inspecteur Chirurgical de Lignes (`<SourceLineInspectorDrawer />`) & Intégration Bout-en-Bout (`CAP-160`)

- **Identifiant Story / Tâche** : `16-4-trace-execution-ui-et-inspecteur-chirurgical-lignes-bout-en-bout`
- **Epic parent** : `Epic 16 — Orchestration Réflexive (Mon Assistant, Mes Agents & Processus Pilotés par l'Objectif), Exploration Chirurgicale #Lstart-end & Articulation avec les Processus Pilotés par les Jalons`
- **Date** : `2026-11-11`
- **Auteur (Rôle)** : `Tech Lead / Senior Full-Stack Engineer (Antigravity)`
- **Statut** : `done`

---

## 1. Analyse du Besoin & Étude d'Impact Tech Lead (Pré-Implémentation)

### 1.1 Objectif Métier & Critères d'Acceptation Visés
La **Story 16.4** clôt l'**Epic 16** (`CAP-160`) en exposant sur les **3 surfaces d'exécution d'ORCIA** (`💬 Mon Assistant`, `🤖 Mes Agents`, `☍ Mes Processus`) une **trace d'exécution vivante sobre, repliable et sans jargon technique** (`<AgentExecutionTrace />`) ainsi qu'un **inspecteur chirurgical de lignes** (`<SourceLineInspectorDrawer />` basé sur `@radix-ui/react-dialog`) reliés de bout en bout aux APIs livrées en Stories `16.1`, `16.2` et `16.3`.

- **Capacité(s)** : `CAP-160` — **classification** : `feature` (clôture runtime `status: live`, `verification: runtime`, `verified_at: "2026-11-11"` de `CAP-160` dans `docs/product/capabilities.yaml`).
- **Références PRD / Architecture / UX** :
  - **PRD & Stories Epic 16** : `CA-16.4.1` (trace progressive repliable sans jargon, bouton `[Synthétiser maintenant]` distinct de `■ Arrêter`), `CA-16.4.2` (clic sur pastille `#Lstart-end` ou `[S1]` ouvrant `<SourceLineInspectorDrawer />` avec lignes numérotées et surlignées, fermeture `Escape`, copie de tranche, et bandeau gouverné `Extrait protégé (habilitation requise)` avec `0` ligne exposée si `redacted === true`), `CA-16.4.3` (intégration sur `Mon Assistant` à 2 modes d'effort `Standard` / `Approfondi`, `Mes Agents` Banc de Test, et `Mes Processus` `InteractiveRunDrawer` objectif & sous-étapes de jalons + survie complète au rechargement `F5`).
  - **Architecture (`AD-17`, `AD-19`, `AD-22`)** : isolation stricte `@orcia/ui` (zéro import `@orcia/api-client`, `@tanstack/*`, `apps/web` ou `fetch`, zéro couleur hexadécimale hors `tokens.css`, zéro usage de `--color-human-led-violet` hors `HumanLedAnchorCard.tsx`, icônes centralisées `<OrciaIcon />`), primitives Radix Dialog (`@radix-ui/react-dialog`), dictionnaires bilingues typés `fr.ts` / `en.ts`, zéro `.catch(() => undefined)`.
  - **UX (`DESIGN.md`, `EXPERIENCE.md`, `UX-DR15`)** : Direction C sobre et lisible sur bureau `1280px+` (panneau latéral droit sans écraser le canevas central) et sur mobile `< 768px` (`390x844`, feuille pleine largeur sans débordement horizontal), fusion de la réflexion dans `<AgentExecutionTrace />` (zéro double boîte de réflexion avec `<AssistantThinkingSubWindow />`).

### 1.2 Analyse d'Impact GitNexus (Rayon d'Explosion & Dépendances)
- **Symboles / Modules impactés (requêtes `gitnexus` sur `repo: "/home/romain/Documents/Projects/ORCIA"` après rafraîchissement d'index `21 986 nœuds / 37 741 arêtes`)** :
  - `InboxFeaturePanel` (`apps/web/src/features/inbox/index.tsx`) : `impactedCount: 15`, `direct: 1` (`ModuleWorkspaceView.tsx`), risque `LOW`. Actuellement `402` lignes $\rightarrow$ **découpage préalable obligatoire** (`< 350` lignes).
  - `AssistantSpeedSelectorAndStreamView` (`packages/ui/src/primitives/AssistantSpeedSelectorAndStreamView.tsx`) : `impactedCount: 15`, `direct: 1` (`InboxFeaturePanel`), risque `LOW`. Actuellement `368` lignes $\rightarrow$ **découpage / allègement obligatoire** (`< 350` lignes) lors de l'intégration du slot `<AgentExecutionTrace />` unifié.
  - `InteractiveRunDrawer` (`apps/web/src/features/processes/execution/InteractiveRunDrawer.tsx`) : `impactedCount: 4`, `direct: 2` (`ProcessesHubPage.tsx`, `WorkflowFiveBlocksCanvas.tsx`), risque `LOW`. Actuellement `600` lignes $\rightarrow$ **découpage préalable obligatoire** en sous-modules cohérents `< 350` lignes.
  - `AgentDetailAndSandboxModal` (`packages/ui/src/components/AgentDetailAndSandboxModal.tsx`) : `impactedCount: 3`, `direct: 1` (`AgentsAndSkillsManagerView.tsx` $\rightarrow$ `CatalogFeaturePanel`), risque `LOW`. Actuellement `405` lignes $\rightarrow$ **découpage préalable obligatoire** (`< 350` lignes) en extrayant le panneau Bac à Sable / Banc de Test réflexif.
  - `createReflexiveExecutionDomainClient` (`packages/api-client/src/domains/reflexiveExecution.ts`) : déjà exposé sur `createOrciaApiClient` (`inspectSourceLines`, `startReflexiveExecution`, `getReflexiveExecutionSnapshot`, `buildReflexiveTraceStreamUrl`, `synthesizeReflexiveExecutionNow`, `cancelReflexiveExecution`, `approveReflexiveWrite`) aux côtés de `workflowsV2.ts` (`startWorkflowV2Run`, `getWorkflowV2Run`, `sendWorkflowV2HitlSignal`). Zéro modification requise du schéma OpenAPI.

### 1.3 Opportunités de Factorisation & Décisions de Refactoring Préalable
- **Composants et contrôleurs réutilisables (DRY)** :
  - Factorisation de toute la cinématique d'inspection chirurgicale dans un hook partagé `apps/web/src/features/shared/useSourceLineInspector.ts` (`203` lignes) consommé par les 3 surfaces (`Mon Assistant`, `Mes Agents`, `Mes Processus`).
  - Factorisation du cycle de vie d'exécution réflexive (`start`, streaming SSE ligne par ligne préservant `\n`, réhydratation `F5` via `getReflexiveExecution`, `synthesizeNow`, `cancel`, `approveWrite`) et des normaliseurs OpenAPI $\rightarrow$ UI (`mapApiKindToUiKind`, `mapApiSnapshotToUi`) dans `apps/web/src/features/shared/useReflexiveExecutionController.ts` (`277` lignes) et `reflexiveTraceMappers.ts` (`223` lignes).
  - Centralisation des libellés FR/EN de la trace et de l'inspecteur dans `apps/web/src/i18n/locales/reflexive_trace_and_inspector_labels.ts` (`138` lignes) avec audit automatisé anti-jargon.
- **Fichiers approchant ou dépassant `350` lignes découpés en Étape 0** :
  1. `apps/web/src/features/processes/execution/InteractiveRunDrawer.tsx` (`600` $\rightarrow$ `276` lignes) + `InteractiveRunDrawerHeader.tsx` (`129` lignes) + `InteractiveRunDeliverableAndHitlPanels.tsx` (`225` lignes) + `useInteractiveProcessRunController.ts` (`333` lignes).
  2. `apps/web/src/features/inbox/index.tsx` (`402` $\rightarrow$ `307` lignes) + `useInboxPanelController.ts` (`289` lignes) + `inboxTurnSyncHelpers.ts` (`170` lignes) + `InboxAuxiliaryPanels.tsx` (`217` lignes) + `assistantAutocompleteHelpers.ts` (`267` lignes).
  3. `packages/ui/src/components/AgentDetailAndSandboxModal.tsx` (`405` $\rightarrow$ `318` lignes) + `AgentTestBenchSection.tsx` (`148` lignes) + `AgentsAndSkillsManagerView.tsx` (`494` $\rightarrow$ `340` lignes) + `AgentsAndSkillsTypes.ts` (`184` lignes).
  4. `packages/ui/src/primitives/AssistantSpeedSelectorAndStreamView.tsx` (`368` $\rightarrow$ `315` lignes) + `AssistantActiveStreamContent.tsx` (`144` lignes) + `AssistantStickyPromptFooter.tsx` (`253` lignes) + `AssistantSpeedSelectorTypes.ts` (`102` lignes).
- **Tickets de dette technique / refactoring créés dans `sprint-status.yaml` ou `epics.md`** :
  - Aucun ticket différé nécessaire : l'intégralité du découpage modulaire `< 350` lignes est absorbée dans la présente Story 16.4.

---

## 2. Plan d'Implémentation

### 2.1 Base de Données & Migrations Alembic (`Expand -> Migrate -> Contract`)
- Aucune nouvelle migration SQL requise : les tables `reflexive_execution_sessions` (`20261111_01`) et `workflow_definitions_v2` (`20261108_0910`) livrées précédemment portent déjà l'état complet (`status`, `trace_events_json`, `pending_write_preview_json`, `final_synthesis_markdown`, `artifact_pointer_json`) pour la réhydratation `F5`.

### 2.2 Noyau Métier Hexagonal (`packages/orcia-core` & `packages/orcia-connectors`)
- Enrichissement déterministe de `GatewayReflexiveLlmAdapter._build_deterministic_cassette_decision` (`packages/orcia-core/src/orcia_core/agents/llm_adapter.py`, `221` lignes) avec l'étape `1b` (`delegate_sub_agent`) afin que `DeterministicCassetteLLM` (`0 $` en CI/E2E) exerce réellement la délégation `@Agent` bornée (`TraceEventKind.AGENT_DELEGATED`) lorsque `allow_sub_agent_delegation=True` et `available_delegate_agents` est renseigné.

### 2.3 Backend FastAPI (`apps/api`) & Contrat OpenAPI (`packages/api-client`)
- Réutilisation directe sans modification (`0-diff` OpenAPI 3.1) des endpoints livrés en Stories `16.1`–`16.3` :
  - `GET /api/v1/sources/inspect-lines` (`inspectSourceLines`)
  - `POST /api/v1/executions/reflexive` (`startReflexiveExecution`)
  - `GET /api/v1/executions/{execution_id}` (`getReflexiveExecution`)
  - `GET /api/v1/executions/{execution_id}/trace-stream` (`buildReflexiveTraceStreamUrl`)
  - `POST /api/v1/executions/{execution_id}/synthesize-now` (`synthesizeReflexiveExecutionNow`)
  - `POST /api/v1/executions/{execution_id}/cancel` (`cancelReflexiveExecution`)
  - `POST /api/v1/executions/{execution_id}/approve-write` (`decideReflexiveWritePreview`)
  - `POST /api/v1/workflows/v2/{workflow_id}/runs` (`startWorkflowV2Run`), `GET /api/v1/runs/{run_id}` (`getWorkflowV2Run`), `POST /api/v1/runs/{run_id}/hitl-signal` (`sendWorkflowV2HitlSignal`).

### 2.4 Interface Utilisateur Pure `@orcia/ui` & Câblage Vertical `apps/web` (Direction C)
1. **Tokens & Styles (`packages/ui/src/styles/tokens.css`)** : classes sémantiques `.orcia-execution-trace*` et `.orcia-line-inspector*` utilisant exclusivement les variables `:root` / `[data-theme="dark"]` existantes (`0` couleur hexadécimale hors `tokens.css`, `0` usage de `--color-human-led-violet` hors `HumanLedAnchorCard.tsx`), avec tiroir latéral droit `min(540px, 44vw)` sur `>= 768px` et feuille pleine largeur `100vw` sans débordement sur `< 768px`.
2. **Composants Design System Purs (`packages/ui/src/components/`)** :
   - `AgentExecutionTraceTypes.ts` (`99` l.), `AgentExecutionTraceItems.tsx` (`243` l.) et `AgentExecutionTrace.tsx` (`294` l.).
   - `SourceLineInspectorDrawer.tsx` (`236` l., basé sur `@radix-ui/react-dialog`).
3. **Dictionnaires i18n (`fr.ts` / `en.ts`) & Contrôleurs Partagés (`apps/web/src/features/shared/`)** :
   - `reflexive_trace_and_inspector_labels.ts` (`138` l.), `gates_and_modules_labels.ts` (`259` l.), `reflexiveTraceMappers.ts` (`223` l.), `useSourceLineInspector.ts` (`203` l.), `useReflexiveExecutionController.ts` (`277` l.).
4. **Câblage des 3 Surfaces & Survie au `F5`** :
   - **Surface 1 (`💬 Mon Assistant`)** : 2 modes d'effort visibles (`Standard` / `Approfondi`), `<AgentExecutionTrace />` unifié sans double boîte de réflexion, citations `[S1]` et pastilles `#Lstart-end` reliées à `<SourceLineInspectorDrawer />`, distinction `[Synthétiser maintenant]` vs `■ Arrêter`, et survie `F5`.
   - **Surface 2 (`🤖 Mes Agents`)** : montage de `<AgentExecutionTrace />` + `<SourceLineInspectorDrawer />` dans `AgentTestBenchSection` (`AgentDetailAndSandboxModal`) et `CatalogFeaturePanel`.
   - **Surface 3 (`☍ Mes Processus`)** : montage de `<AgentExecutionTrace />` + `<SourceLineInspectorDrawer />` dans `InteractiveRunDrawer` + persistance `ACTIVE_PROCESS_RUN_WORKFLOW_STORAGE_KEY` (`ProcessesHubPage.tsx`) et protection anti-écrasement de l'hydratation initiale dans `useStudioWorkflowController.ts`.

---

## 3. Bilan des Modifications & Résultats (Post-Implémentation)

### 3.1 Tableau Synthétique des Fichiers Créés et Modifiés

| Fichier | Action & Volumétrie | Rôle & Responsabilité |
| :--- | :--- | :--- |
| `packages/ui/src/components/AgentExecutionTraceTypes.ts`, `AgentExecutionTraceItems.tsx` & `AgentExecutionTrace.tsx` | Création (`99` l. / `243` l. / `294` l.) | Composant Design System pur `<AgentExecutionTrace />` : groupes repliables `GROUP_HEADER`, accordéon `THOUGHT_COMPLETED` / `THOUGHT_DELTA` préservant `\n`, pastilles cliquables `FILE_ANALYZED` (`M↓`/`Y`/`TS`/`PY`/`JSON`/`SQL`/`DOC` + `#Lstart-end`), sous-blocs `AGENT_DELEGATED` (`@Agent`), carte gouvernée `WRITE_PREVIEW_REQUESTED` et bouton `[Synthétiser maintenant]`. |
| `packages/ui/src/components/SourceLineInspectorDrawer.tsx` & `packages/ui/src/styles/tokens.css` | Création (`236` l.) & Modif. | Tiroir latéral accessible `<SourceLineInspectorDrawer />` (`@radix-ui/react-dialog`, fermeture `Escape`, copie de tranche `#Lstart-end`, lignes 1-indexées `data-highlighted="true"`, bandeau gouverné `redacted === true` avec `0` ligne exposée, responsive desktop/mobile sans débordement). |
| `packages/ui/src/components/AgentsAndSkillsTypes.ts`, `AgentsAndSkillsManagerView.tsx`, `AgentTestBenchSection.tsx` & `AgentDetailAndSandboxModal.tsx` | Découpage & Modif. (`184` l. / `340` l. / `148` l. / `318` l.) | Découpage modulaire `< 350` lignes, ajout du slot `sandboxTraceSlot` dans le Banc de Test de `AgentDetailAndSandboxModal` et conformité stricte `autoComplete="off"` / `data-lpignore="true"` sur tous les champs. |
| `packages/ui/src/primitives/AssistantSpeedSelectorTypes.ts`, `AssistantActiveStreamContent.tsx`, `AssistantStickyPromptFooter.tsx`, `AssistantSpeedSelectorAndStreamView.tsx` & `AssistantResponseFooterActionsAndCitations.tsx` | Découpage & Modif. (`102` l. / `144` l. / `253` l. / `315` l. / `303` l.) | Découpage modulaire `< 350` lignes, intégration de `activeTraceSlot` unifié (masquant `<AssistantThinkingSubWindow />` dès qu'une trace réflexive est présente), sélecteur d'effort épuré à 2 modes (`Standard` / `Approfondi`) et clic `[S1]` ouvrant `<SourceLineInspectorDrawer />`. |
| `apps/web/src/i18n/locales/reflexive_trace_and_inspector_labels.ts`, `gates_and_modules_labels.ts`, `fr.ts`, `en.ts` & `types.ts` | Création (`138` l. / `259` l.) & Modif. (`265` l. / `265` l. / `65` l.) | Dictionnaires bilingues FR/EN complets (`executionTrace`, `sourceLineInspector`) garantis sans aucun jargon technique (`0` occurrence `DBOS`, `asyncio`, `Redis`, `SSE`, `Claim-Check`, `déterministe`, `non-déterministe`). |
| `apps/web/src/features/shared/reflexiveTraceMappers.ts`, `useSourceLineInspector.ts` & `useReflexiveExecutionController.ts` | Création (`223` l. / `203` l. / `277` l.) | Normalisation OpenAPI $\rightarrow$ UI (`mapApiKindToUiKind`, `mapApiSnapshotToUi`, `parseUriWithLineRange`), contrôleur d'inspection chirurgicale (`inspectSourceLines` + copie) et contrôleur de cycle de vie réflexif (`start`, SSE ligne par ligne, survie `F5`, `synthesizeNow`, `cancel`, `approveWrite`). |
| `apps/web/src/features/inbox/` (`index.tsx`, `useInboxPanelController.ts`, `inboxTurnSyncHelpers.ts`, `InboxAuxiliaryPanels.tsx`, `SavedConversationsAndThreadView.tsx`, `savedConversationsStore.ts`, `assistantAutocompleteHelpers.ts`) | Découpage & Modif. (`307` l. / `289` l. / `170` l. / `217` l. / `322` l. / `307` l. / `267` l.) | Câblage vertical complet de `💬 Mon Assistant` sur `<AgentExecutionTrace />` et `<SourceLineInspectorDrawer />` avec persistance des traces par tour et réhydratation `F5`. |
| `apps/web/src/features/catalog/index.tsx` & `useCatalogRemoteTestBench.ts` | Découpage & Modif. (`252` l. / `170` l.) | Câblage vertical du Banc de Test de `🤖 Mes Agents` sur `startReflexiveExecution` + `<AgentExecutionTrace />` + `<SourceLineInspectorDrawer />` avec survie `F5`. |
| `apps/web/src/features/processes/` (`ProcessesHubPage.tsx`, `execution/InteractiveRunDrawer.tsx`, `execution/InteractiveRunDrawerHeader.tsx`, `execution/InteractiveRunDeliverableAndHitlPanels.tsx`, `execution/useInteractiveProcessRunController.ts`, `studio/useStudioWorkflowController.ts`) | Découpage & Modif. (`344` l. / `276` l. / `129` l. / `225` l. / `333` l. / `270` l.) | Câblage vertical de `☍ Mes Processus` (`startWorkflowV2Run` + `startReflexiveExecution` + `WAITING_WRITE_PREVIEW` + survie `F5` du dossier ouvert) et garde `hasUserEditedRef` évitant l'écrasement d'une saisie rapide dans le Studio 5-Blocs. |
| `packages/orcia-core/src/orcia_core/agents/llm_adapter.py` | Modification (`221` l.) | Étape `1b` (`delegate_sub_agent`) dans `DeterministicCassetteLLM` permettant d'exercer de bout en bout la délégation `@Agent` bornée sur la pile E2E réelle (`0 $`). |
| `packages/ui/src/__tests__/story-16-4-agent-execution-trace-and-inspector.test.tsx`, `apps/web/src/__tests__/story-16-4-reflexive-trace-wiring-and-f5.test.tsx`, `apps/web/src/__tests__/vitestReflexiveBackend.ts` & `apps/web/e2e/12-epic16-reflexive-trace-and-line-inspector.spec.ts` | Création (`285` l. / `309` l. / `346` l. / `176` l.) | Suites TDD Couche 1b (`@orcia/ui` + `@orcia/web` + Garde-Fou n°5 `zero-dead-buttons`) et Couche 5 Playwright E2E réel bi-serveur sur `desktop-cockpit` (`1440x900`) et `mobile-companion` (`390x844`). |
| `docs/product/capabilities.yaml`, `docs/implementation-artifacts/sprint-status.yaml` & `docs/implementation-artifacts/tech-lead-reports/README.md` | Modification | Promotion de `CAP-160` à `status: live` (`verification: runtime`, `verified_at: "2026-11-11"`, `origin_ref: epic-16 (16-1..16-4)`) et clôture `done` de `Story 16.4` et `Epic 16`. |

### 3.2 Résultats Chiffrés, Métriques & Qualité
- **Volumétrie strictement maîtrisée (`< 350` lignes sur 100 % des fichiers sources créés ou refactorisés)** :
  - `@orcia/ui` : `AgentExecutionTrace.tsx` (`294` l.), `AgentExecutionTraceItems.tsx` (`243` l.), `AgentExecutionTraceTypes.ts` (`99` l.), `SourceLineInspectorDrawer.tsx` (`236` l.), `AgentDetailAndSandboxModal.tsx` (`318` l.), `AgentTestBenchSection.tsx` (`148` l.), `AgentsAndSkillsManagerView.tsx` (`340` l.), `AssistantSpeedSelectorAndStreamView.tsx` (`315` l.), `AssistantResponseFooterActionsAndCitations.tsx` (`303` l.).
  - `@orcia/web` & `orcia-core` : `inbox/index.tsx` (`307` l.), `useInboxPanelController.ts` (`289` l.), `catalog/index.tsx` (`252` l.), `ProcessesHubPage.tsx` (`344` l.), `InteractiveRunDrawer.tsx` (`276` l.), `useInteractiveProcessRunController.ts` (`333` l.), `useReflexiveExecutionController.ts` (`277` l.), `reflexiveTraceMappers.ts` (`223` l.), `useSourceLineInspector.ts` (`203` l.), `llm_adapter.py` (`221` l.).
- **Couverture unitaire Python Epic 16 (`AD-17` Couche 1a)** : **`94.00 %`** (`>= 90 %` requis ; `22 passed` ; `llm_adapter.py` : `91 %`, `process_dispatcher.py` : `93 %`, `reflexive_schemas.py` : `98 %`, `reflexive_write_gate.py` : `100 %`, ports hexagonaux : `100 %`).
- **Suites TypeScript Monorepo (`pnpm turbo run lint typecheck test`)** : **`9/9` tâches vertes** (`144 passed` au total : **`77/77`** `@orcia/ui` sur `18` fichiers, **`8/8`** `@orcia/api-client`, **`59/59`** `@orcia/web` sur `11` fichiers incluant `design-system-look-and-feel-isolation.test.tsx`, `zero-dead-buttons-and-silent-catches-audit.test.tsx` `7/7`, `story-16-3` et `story-16-4`).
- **Analyse statique, typage strict & contrats d'architecture** :
  - `.venv/bin/ruff check .` & `.venv/bin/ruff format --check .` : **`0` erreur** (`701` fichiers conformes).
  - `.venv/bin/mypy --strict packages/orcia-core packages/orcia-connectors apps/api apps/worker` : **`0` erreur** sur `294` fichiers sources.
  - `.venv/bin/lint-imports` : **`5 contracts kept, 0 broken`** (`329` fichiers, `1 947` dépendances).
  - `.venv/bin/python scripts/export_openapi.py --check` : **`0-diff`**.
  - `lint_spine.py` : **`0` finding** (`ok: true`).

### 3.3 Validation sur Toute la Pyramide (`AD-17`) & Audit GitNexus Post-Implémentation
- **Couche 1b (`@orcia/ui` & `@orcia/web` Vitest)** :
  - `story-16-4-agent-execution-trace-and-inspector.test.tsx` (`4/4 passed`) : rendu des groupes repliables, préservation des sauts de ligne `\n` dans `THOUGHT_COMPLETED`, clic `#Lstart-end`, bouton `[Synthétiser maintenant]`, lignes surlignées `data-highlighted="true"`, copie de tranche, fermeture `Escape`, et masquage strict `redacted === true` (`0` ligne exposée).
  - `story-16-4-reflexive-trace-wiring-and-f5.test.tsx` (`4/4 passed`) : audit bilingue FR/EN zéro jargon interdit, câblage `💬 Mon Assistant` (2 modes d'effort uniquement, zéro double boîte de réflexion, inspection `#Lstart-end`), câblage `🤖 Mes Agents` (Banc de Test + garde `READ_SOURCE`), et câblage `☍ Mes Processus` (`@Agent`, `[Synthétiser maintenant]` vs `■ Arrêter`, `WritePreviewCard` + survie `unmount() -> render()` `F5`).
- **Couche 2 (`Testcontainers PostgreSQL 18 + Redis 7.4`)** :
  - `test_story_16_3_dual_mode_processes_api.py` : **`1 passed` (`15.93s`)** sur `pgvector/pgvector:pg18` + `redis:7.4.2-alpine`, confirmant la non-régression complète du `ProcessExecutionDispatcher` avec la délégation `@Agent` active dans `DeterministicCassetteLLM`.
- **Couche 5 (`Playwright E2E` Bi-Serveur Réel PostgreSQL 18 + Redis 7.4 + FastAPI + Vite)** :
  - `e2e/12-epic16-reflexive-trace-and-line-inspector.spec.ts` : **`2 passed` (`36.6s`)** sur **`desktop-cockpit` (`1440x900`, `9.2s`)** ET **`mobile-companion` (`390x844`, `7.3s`)** — lancement réel de `wf-generate-orcia-documentation` sur `/processes`, vérification zéro jargon + délégation `@redacteur-documentation-orcia` + accordéon de réflexion + clic `#L1-35` ouvrant `<SourceLineInspectorDrawer />` (`inspector-code-line-1` `data-highlighted="true"`), zéro débordement horizontal (`<= 1px`), copie d'extrait, fermeture `Escape`, test réel de refus `READ_SOURCE` (`x-orcia-read-source: denied` $\rightarrow$ `inspector-redacted-banner` + `0` ligne DOM), mise en pause `WAITING_WRITE_PREVIEW` + vrai `page.reload()` (`F5`) réhydratant la `WritePreviewCard` depuis PostgreSQL 18 + approbation `approve-write` et `0` erreur serveur `5xx`.
  - Suite de non-régression Playwright (`e2e/00`, `e2e/02`, `e2e/09`, `e2e/11` sur `desktop-cockpit`) : **`8 passed, 1 skipped` (`50.1s`, `0` échec)**.
- **Audit GitNexus Post-Implémentation (`Garde-Fou #1`) & Synchronisation Catalogue** :
  - `GITNEXUS_LBUG_BUFFER_POOL_SIZE=2147483648 npx gitnexus analyze` (`22 592` nœuds, `38 738` arêtes, `343` clusters, `1 219` flux) + `detect_changes({repo: "/home/romain/Documents/Projects/ORCIA", scope: "all"})` (`changed_files: 23`, `changed_count: 70`, `affected_count: 14`).
  - `gitnexus.impact({target: "AgentExecutionTrace", direction: "upstream"})` : `impactedCount: 22`, `direct: 4` (`AssistantActiveStreamContent`, `SavedConversationsAndThreadView`, `CatalogFeaturePanel`, `InteractiveRunDrawer`), `epistemic: "exact"`.
  - `gitnexus.impact({target: "SourceLineInspectorDrawer", direction: "upstream"})` : `impactedCount: 21`, `direct: 3` (`InboxAuxiliaryPanels`, `CatalogFeaturePanel`, `InteractiveRunDrawer`), `epistemic: "exact"`.
  - `pnpm site:sync && pnpm site:check` & `.venv/bin/python scripts/check_implementation_docs.py` : **`0` erreur**.
