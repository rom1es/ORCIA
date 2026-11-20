# 🏗️ Audit Croisé Architecture, Vérité PostgreSQL 18 & Frontières Direction C — Campagne E2E Epic 23 (`23.7-winston`)

- **Auditeur** : 🏗️ **Winston** (System Architect — `bmad-agent-architect`)
- **Date** : `2026-11-20`
- **Branche / Commit figé** : `feat/epic-23-remediation-pg18-sse-direction-c` (`dd2d382` post-`Story 23.6a` — zéro modification applicative)
- **Périmètre exécuté** : `--project=desktop-cockpit` (`1440×900`, `24` fichiers `.spec.ts`, `--retries=0 --max-failures=0 --timeout=35000`, `env -u ORCIA_E2E_SEED_FIXTURES`)
- **Référentiels appliqués** :
  - [`ARCHITECTURE-SPINE.md`](../../planning-artifacts/architecture/architecture-ORCIA-2026-10-24/ARCHITECTURE-SPINE.md) & [`architecture.md`](../../planning-artifacts/architecture/architecture-ORCIA-2026-10-24/architecture.md) (`AD-1`..`AD-24`)
  - [`sprint-change-proposal-2026-11-18-epic-23-remediation-plan.md`](../../planning-artifacts/sprint-change-proposal-2026-11-18-epic-23-remediation-plan.md) (`Step 2a`, `23.6a`, condition de sortie `23.7`/`23.8`)
  - [`bilan-execution-tests-e2e-epic-23.md`](./bilan-execution-tests-e2e-epic-23.md) & [`playwright-results.json`](./playwright-results.json)
  - [`notes-audit-sally-ux.md`](./notes-audit-sally-ux.md) (`58/58` PNG inspectées, `UX23-01`..`UX23-17`)
  - Continuité Epic 22 : [`notes-audit-winston-architecture.md` (Epic 22)](../e2e-campaign-epic-22/notes-audit-winston-architecture.md) & [`GEMINI.md`](../../../GEMINI.md)

---

## 1. Synthèse exécutive & Chiffres de vérité PostgreSQL 18

🏗️ La campagne Desktop figée au commit `dd2d382` (`771 175,85 ms` soit `12,85 min`, code sortie `1`) réalise un saut structurel décisif par rapport à l'Epic 22 (`a1bb059`) :

- **Le blocage systémique d'Epic 22 est levé à `100 %`** : `0` échec dans `resetDay0()` (`RestrictViolationError` supprimée) et `0` échec `HTTP 401` sur `00-stack-smoke` (`#3`, `#4`) ou `02-assistant` (`#7`). Sur `55` scénarios Desktop planifiés, **`44` sont `passed`** (`18 / 24` specs à `100 %` vertes), **`7` sont `failed`**, **`1` est `timedOut`**, **`3` sont `skipped`** (`mobile-only` : `#14`, `#25`, `#27`), **`0` est `flaky`**, soit **`84,6 %` (`44 / 52`)** de réussite contre `13,2 %` (`7 / 53`) sur Desktop en Epic 22 (**`+37` scénarios PASS**).
- **L'angle mort des specs `04`–`21` est enfin ouvert** : l'exécution réelle contre PostgreSQL 18 + Redis 7.4 sans `ORCIA_E2E_SEED_FIXTURES` expose désormais précisément **`5` défauts applicatifs/SQL/API** (`6` scénarios), **`2` défauts du harnais/sélecteur E2E**, et **`1` fracture structurelle CSS Tailwind v4 × `tokens.css`** expliquant simultanément plusieurs défauts visuels majeurs relevés par Sally (`UX23-02`, `UX23-04`, `UX23-14`).

| Indicateur campagne | Epic 22 (`desktop-cockpit`) | Epic 23 (`dd2d382`, `desktop-cockpit`) | Écart |
| --- | ---: | ---: | ---: |
| Scénarios planifiés | `55` | `55` | `0` |
| `passed` | `7` | **`44`** | **`+37`** |
| `failed` + `timedOut` | `46` (`46` + `0`) | **`8`** (`7` + `1`) | **`-38`** |
| `skipped` (`mobile-only`) | `2` | `3` | `+1` |
| `flaky` | `0` | `0` | `0` |
| Taux de succès (`passed / exécutés`) | `13,2 %` (`7 / 53`) | **`84,6 %` (`44 / 52`)** | **`+71,4 pts`** |
| Captures PNG sur disque (`< 450 KB`) | `55` Desktop (`110` total) | **`58`** (`55` + `3` jalons, max `276 950 B`) | `0` > `450 KB` |

### 1.1 Verdict sur le critère de sortie `23.7` / `23.8` (`Case B`)

Conformément au [Plan Directeur Epic 23](../../planning-artifacts/sprint-change-proposal-2026-11-18-epic-23-remediation-plan.md), l'objectif de sortie directe (`Case A`) exige **`52 / 52` PASS Desktop (`0` échec, `0` timeout) et `0` écart `P0`/`P1`** dans la synthèse Sally × Winston. La campagne figée présentant **`8` scénarios Desktop en échec/timeout**, **`1 P0`** (`UX23-01`) et **`9 P1`** (`UX23-02`..`UX23-10`), le verdict formel est **`Case B` : l'ouverture d'un Epic 24 ciblé (`REM24-01`..`REM24-12`) est obligatoire** avant clôture définitive de la remédiation Desktop.

---

## 2. Audit Architectural Transverse (`AD-1`..`AD-24`, `AD-19`, Vérité PG18, Sécurité, SSE, Observabilité)

### 2.1 Conformité aux décisions `AD-1`..`AD-24`

| Groupe d'AD | Décisions couvertes | État observé (`dd2d382`) | Preuves & écarts résiduels identifiés |
| --- | --- | :---: | --- |
| **Socle SPA & Monolithe Hexagonal** | `AD-1`, `AD-19`, `AD-20`, `AD-22` | ⚠️ **Partiel** | `pyproject.toml:103-179` verrouille `5` contrats `import-linter` (`orcia_api/orcia_worker -> orcia_connectors -> orcia_core`, hiérarchie acyclique interne, zéro SDK dans `kernel`/`domain`/`ports`, isolation `orcia_connectors`, exclusion `docling`). Mais **4 fabriques paresseuses hors Composition Root** subsistent dans `routers/jira_and_mcp.py:36-51` et `routers/_workflows_helpers.py:80-102`, et l'ordre d'import CSS (`main.tsx:1-2`) + doublons non-layered de `tokens.css:256-305` cassent les classes responsives Tailwind v4 dans `@orcia/ui` (`ARCH24-08`). |
| **Orchestration Durable, Ancres & Verrous** | `AD-2`, `AD-3`, `AD-4`, `AD-13` | ✅ **Validé** *(réserves `20#2`, RAM)* | `03`, `04`, `12-epic16` et `19#1` passent sur PostgreSQL 18 (`workflow_runs`, `step_executions`, `blackboard_snapshots`, `human_anchor_signatures`, `upstream_challenges`, `task_notifications`). Seule la génération `tid[:8]` sur `workflow_triggers` provoque une collision 409 (`ARCH24-03`). |
| **Fédération URI, Actions Jira Staged & CAS** | `AD-5`, `AD-11`, `AD-18` | ❌ **Écart `P0` (`06 #15`, `19#2 #47`, `17#3`)** | `MultiProjectJiraStagedActionService` (`jira_actions.py:180-408`) garde `_staged_by_id` et `_draft_artifacts_by_step` uniquement en RAM (aucune table PG18 dans `infra/scripts/maintenance/_first_boot_reset_guards.py:56-79`). Les dérogations `workspace_exception_waivers` souffrent d'un appel UI `void` non attendu (`17#3 #40`). |
| **Authentification, RBAC & Permission Broker** | `AD-6`, `AD-21` | ⚠️ **Partiel** | `00`, `14`, `15`, `16` passent (fail-closed `ORCIA_ENV="e2e"`, Argon2id, `platform_auth_settings`, `role_permission_grants`, `READ_ONLY_OBSERVER` `403`, `SecretInput`/`SecretStatus`, `permission_broker_tickets`). Mais `RemoteServiceTestBenchAndGovernedMcpService` (`remote_test_bench_and_mcp_exposure.py:114-115`) et `GovernedMcpServerService` conservent l'exposition MCP en RAM (`ARCH24-05`), et `PermissionBrokerCard` expose du Markdown brut + jargon (`UX23-08`). |
| **Ontologie 4 Niveaux, ADN Starlark & RAG** | `AD-7`, `AD-8`, `AD-9`, `AD-10`, `AD-24` | ⚠️ **Partiel** | `16` et `17#1/#2` prouvent `rag_reindexing_jobs`, `workspace_llm_tier_mappings`, garde SSRF (`is_safe_llm_endpoint_url`), promotion L4→L3 (`ontology_promotion_proposals`) et graphe tripartite (`tripartite_trace_edges`). Mais `dna_starlark_and_glossary_service` (`workspace_and_packs.py:47-57`) n'a pas de dépôt PG18 (`ARCH24-04`), et la recherche fédérée `⌘K` (`sql_federated_search.py:81-121`) oublie de filtrer `HELP_ARTICLE` par langue active (`UX23-05` / `ARCH24-10`). |
| **FinOps, Audit Ledger, Studio, Aide & Observabilité** | `AD-12`, `AD-14`, `AD-15`, `AD-16`, `AD-17`, `AD-23` | ⚠️ **Partiel** | Streaming SSE (`02`), `audit_ledger` append-only (`12-finops`, `15`), `httpx.AsyncClient` partagé (`assistant_llm_bridge.py:71-81`) et `stdout` JSON/OTel sont en place. Subsistent l'absence totale de persistance PG18 pour `vsm_definitions_v2` (`ARCH24-02`), la divergence `ADMIN_CONNECTION_TEST` vs `AdminConnectionTested` (`ARCH24-05`), et `ACTIVE_WORKSPACE_TURNS` en RAM (`assistant_llm_bridge.py:15`). |

### 2.2 Cartographie PG18 vs État RAM résiduel (`apps/api/src/orcia_api/routers/e2e_test_hooks.py`)

L'audit croisé de `infra/scripts/maintenance/_first_boot_reset_guards.py:56-79`, `apps/api/src/orcia_api/dependencies/` et `e2e_test_hooks.py:19-80` établit la frontière exacte entre les états véritablement persistés en PostgreSQL 18 et les poches RAM résiduelles qui s'évaporent sur redémarrage API ou `reloadColdFromPg` :

| Service / État inspecté | Localisation | Table PG18 existante ? | Persistance réelle constatée | Verdict |
| --- | --- | :---: | --- | :---: |
| `MultiProjectJiraStagedActionService` (`_staged_by_id`, `_draft_artifacts_by_step`) | `orcia_connectors/jira_actions.py:191-192` + `routers/jira_and_mcp.py:36-43` | **Non** *(absente du schéma PG18)* | **100 % RAM** (`evict-memory-caches` l.69) | **`P0` (`ARCH24-01`)** |
| `GovernedMcpServerService` | `routers/jira_and_mcp.py:46-51` | **Non** | **100 % RAM** (`evict-memory-caches` l.70) | **`P1` (`ARCH24-01`)** |
| `vsm_v2_store` (`ValueStreamMapSpec`) | `routers/_workflows_helpers.py:80-91` + `routers/workflows.py:78-94` | **Oui (`vsm_definitions_v2`)** | **100 % YAML/RAM** (`evict-memory-caches` l.72 — table `vsm_definitions_v2` vide) | **`P0` (`ARCH24-02`)** |
| `workflow_v2_runs_store` | `routers/_workflows_helpers.py:94-102` | Oui (`workflow_runs` / `reflexive_execution_sessions`) | Fabrique paresseuse RAM dans helper routeur | **`P1` (`ARCH24-02`)** |
| `SqlWorkflowDefinitionsV2Store` (`strict_sql`) | `workflows/_internal/sql_workflows_v2.py:100-103,129-130` | Oui (`workflow_definitions_v2`) | Défaut `strict_sql=False` avec `_memory_fallback` ; `strict_sql=True` uniquement si `session_maker` résolu (`reflexive_execution.py:124-131`) | **`P1` (`ARCH24-07`)** |
| `RemoteServiceTestBenchAndGovernedMcpService` (`_exposed_agents`, `_pat_tokens`) | `orchestration/remote_test_bench_and_mcp_exposure.py:114-115` + `workspace_and_packs.py:60-70` | Partielle (`user_mcp_tokens` seulement) | **100 % RAM** (aucun dépôt PG18 injecté, évincé l.55 ; `useCatalogRemoteTestBench.ts:141-160` en `useState`) | **`P0` (`ARCH24-05`)** |
| `DnaStarlarkAndGlossaryLifecycleService` | `dependencies/workspace_and_packs.py:47-57` | Oui (`ontology_relations`, `workspace_exception_waivers`) | Service sans dépôt PG18 injecté (évincé l.54) ; UI garde `fallbackMechanism` et `onSignAndActivate` locaux (`WorkspaceDnaAndWaiversSection.tsx:171-235`) | **`P0` (`ARCH24-04`)** |
| `TwoSpeedFederatedSearchService._speed2_cache` | `rag/two_speed_search.py:181` + `portal_and_assistant.py:87-95` | Non (devrait être Redis `300s`) | Cache Speed 2 en `dict` Python RAM par worker au lieu de Redis | **`P2` (`ARCH24-07`)** |
| `ACTIVE_WORKSPACE_TURNS` (streaming assistant) | `routers/assistant_background_turns.py:15` + `assistant_llm_bridge.py:15` | Non | État de tour en cours en RAM par worker (acceptable mono-worker, fragile multi-workers) | **`P2` (`ARCH24-12`)** |
| `AssistantFourLevelGovernanceService`, `AssistantThreeSpeedRouterService`, `AssistantCitationAndV5GuardService` | `dependencies/portal_and_assistant.py:136-173` | Partielle | Surcharges / règles sans injection PG18 directe | **`P2` (`ARCH24-07`)** |

### 2.3 Sécurité, RBAC, Streaming SSE & Observabilité

- **SSRF & Transport Async (`AD-1`, `AD-24`)** : `assistant_llm_bridge.py:71-81` et `assistant_llm_providers.py:45,73-94` utilisent correctement `request.app.state.http_client` (`httpx.AsyncClient` partagé) et appliquent `is_safe_llm_endpoint_url` (blocage `169.254.169.254`, link-local, multicast, metadata Cloud tout en autorisant `.local`/`.internal`), sans appel HTTP bloquant dans l'event loop (`ruff` `TID251` actif dans `pyproject.toml:197-200`).
- **RBAC & Fail-Closed (`AD-6`, `AD-21`)** : Les specs `14`, `15` et `16` prouvent le rejet `HTTP 403 ERR_OBSERVER_MODE_READ_ONLY`, la délégation scopée, le masquage write-only des secrets (`SecretField`) et l'authentification des flux SSE. En revanche, l'absence de filtrage de rôle sur l'affichage des jalons d'accostage (`UX23-07`) et le breadcrumb `/organization` renvoyant vers `Configuration` masquée (`UX23-09`) dégradent la lisibilité RBAC côté interface.
- **Anti-patterns mineurs de contrat & fallbacks** : `cockpit/index.tsx:113` envoie en dur `workflow_uri: "orcia://workflows/claims-engineering-delivery"` sans respecter `wfKey` ; `portal_and_help.py:79,94` et `two_speed_search.py:192` utilisent encore `"ws-claims-alpha"` par défaut ; `workspace_governance.py:129` et `WorkspaceDnaAndWaiversSection.tsx:45` utilisent `"default-ws"` ; `PacksRegistryPage.tsx:35,53-57` utilise `"ws-mon-compte"` et un diagnostic MCP codé en dur.

---

## 3. Fiches Causes Racines Exactes des `8` Échecs E2E Desktop (`dd2d382`)

### Échecs #1 & #6 (`06 #15` et `19#2 #47`) — Disparition post-F5 du statut `EXECUTED` de l'action Jira échelonnée sur `/gates` (`P0`)

- **Scénarios & Captures** :
  - `#15` (`06-gates-review-and-anti-rubber-stamping.spec.ts:145`, `19 552 ms`) — [`failed.png`](screenshots/06-gates-review-and-anti-rubber-stamping/desktop-cockpit--inspection-du-bloc-4-approbation-par-decoupage-garde-fou-15-s-action-jira-et-survie-f5--failed.png)
  - `#47` (`19-orchestration-whatif-replay-and-gates.spec.ts:191`, `21 557 ms`) — [`failed.png`](screenshots/19-orchestration-whatif-replay-and-gates/desktop-cockpit--validation-deterministe-sandbox-validation-agentique-orthogonale-revue-humaine-par-decou--failed.png)
- **Erreur Playwright observée** : `getByTestId('gates-staged-jira-status-badge')` (`Expected: "EXECUTED"`) introuvable dans le DOM après `reloadColdFromPg` / `reloadClearingStorage` (`timeout 5000ms`), alors que `gates-human-evaluation-status-badge` réapparaît bien en `PASS`.
- **Chaîne causale exacte (Code + PG18)** :
  1. `MultiProjectJiraStagedActionService` (`packages/orcia-connectors/src/orcia_connectors/jira_actions.py:191-192,331-354,406`) conserve `_staged_by_id: dict[str, StagedJiraActionItem]` et `_draft_artifacts_by_step: dict[str, dict[str, Any]]` **strictement en RAM** ; aucune table PG18 n'existe dans `infra/scripts/maintenance/_first_boot_reset_guards.py:56-79`.
  2. `apps/api/src/orcia_api/routers/jira_and_mcp.py:36-43` instancie paresseusement ce service sur `request.app.state.jira_staged_action_service` via `_get_jira_service`, hors Composition Root.
  3. Lors du F5 à froid (`reloadColdFromPg`), `POST /api/v1/_e2e/evict-memory-caches` (`apps/api/src/orcia_api/routers/e2e_test_hooks.py:69`) vide `jira_staged_action_service`.
  4. Au montage de `/gates`, `GatesAdaptiveHumanReviewSection.tsx:44-49,294-311` reçoit `gate_evaluations` depuis PG18 (d'où `Point de contrôle : Validé` + `Section 1 Approuvé` visibles dans les deux PNG) mais `GET /api/v1/jira/actions/staged` renvoie `actions: []`, laissant `stagedJira = null` et démontant complètement `gates-staged-jira-status-badge` (`UX23-01`).
- **Remédiation (`REM24-01`)** : Migration Alembic créant `jira_staged_actions` + dépôt SQL `SqlJiraStagedActionsRepository` câblé au Composition Root + suppression de `_get_jira_service` paresseux.

---

### Échec #2 (`07 #16`) — Sélecteur Playwright ambigu capturant l'`<option>` cachée du `<select>` sidebar (`P3`)

- **Scénario & Capture** : `#16` (`07-spaces-org-and-workspace-persistence.spec.ts:42`, `32 440 ms`) — [`failed.png`](screenshots/07-spaces-org-and-workspace-persistence/desktop-cockpit--bu-equipe-espace-crees-par-l-ui-sont-persistes-cote-api-et-survivent-a-un-f5--failed.png)
- **Erreur Playwright observée** : `locator resolved to <option value="01a1f7a5-9ace-72e8-817d-6a0e28e5a900">📦 Espace E2E Comptabilité</option> - unexpected value "hidden"` (`timeout 20000ms`).
- **Chaîne causale exacte** : Dans la capture `#16`, la carte `Espace E2E Comptabilité` (`Équipe de facturation : Equipe E2E`, `Phase : Construction`) est **parfaitement persistée et affichée dans `<main>`** (`org_units` et `workspaces` verts en PG18). Mais `apps/web/e2e/07-spaces-org-and-workspace-persistence.spec.ts:42` exécute `page.getByText("Espace E2E Comptabilité").first()`, qui matche en premier l'`<option>` du `<select data-testid="sidebar-workspace-selector">` (`FourZoneSidebarRail.tsx:167-190`), considéré `hidden` par Playwright.
- **Remédiation (`REM24-11`)** : Scoper l'assertion dans `page.getByRole("main")` ou sur le `data-testid` de la carte d'espace.

---

### Échec #3 (`17#3 #40`) — Dérogation `workspace_exception_waivers` à `0` ligne après F5 (`P0`)

- **Scénario & Capture** : `#40` (`17-workspace-sources-codegraph-dna-and-ontology.spec.ts:200`, `14 958 ms`) — [`failed.png`](screenshots/17-workspace-sources-codegraph-dna-and-ontology/desktop-cockpit--chaine-adn-starlark-derogations-d-espace-et-graphe-tripartite-rag-persistent-en-base-apr--failed.png)
- **Erreur Playwright observée** : `expectDbRowExists` sur `SELECT waiver_id::text ... FROM workspace_exception_waivers WHERE workspace_id = :ws_id` retourne `Expected >= 1, Received: 0` après clic sur `[data-testid^="register-waiver-btn-"]` et `reloadColdFromPg(page)`.
- **Chaîne causale exacte (Code + PG18)** :
  1. La table `workspace_exception_waivers` et son dépôt SQL (`sql_workspace_waivers.py`) existent bien en PG18, et `WorkspaceFiveTabsAndExternalRebaseView.tsx:180-188,213-226` émet `onRegisterWaiver(...)` au clic sur `register-waiver-btn-*`.
  2. Mais `apps/web/src/features/workspaces/WorkspaceDnaAndWaiversSection.tsx:96` exécute un appel **fire-and-forget non `await`é** : `void client.registerWorkspaceExceptionWaiver(...)` !
  3. De plus, `WorkspaceDnaAndWaiversSection.tsx:45` calcule `targetWorkspace?.slug ?? targetWorkspace?.workspaceId ?? "default-ws"` (`UX23-06`), `L171-195` injecte un `fallbackMechanism` optimiste avant `compileDnaStarlark`, `L224-235` (`onSignAndActivate`) ne mute que le state React sans persister en PG18, et `dependencies/workspace_and_packs.py:47-57` instancie `dna_starlark_and_glossary_service` sans dépôt PG18 (évincé dans `e2e_test_hooks.py:54`).
  4. Le test enchaîne immédiatement sur `reloadColdFromPg`, coupant ou précédant l'enregistrement SQL dans `workspace_exception_waivers`.
- **Remédiation (`REM24-04`)** : `await` strict sur `registerWorkspaceExceptionWaiver` avec retour serveur visible avant réinitialisation/navigation, suppression de `"default-ws"` et du `fallbackMechanism` optimiste, persistance PG18 des mécanismes ADN signés (`AD-7`).

---

### Échec #4 (`18#1 #41`) — Timeout `35 275 ms` du helper `openCatalogOrAgentsPage(..., { route: "/catalog" })` (`P1`)

- **Scénario & Capture** : `#41` (`18-catalog-packs-wizards-and-mcp-bench.spec.ts:19`, `35 275 ms` `timedOut`) — [`timedOut.png`](screenshots/18-catalog-packs-wizards-and-mcp-bench/desktop-cockpit--explorateur-du-catalogue-federe-droits-granulaires-et-definitions-persistent-en-base-apr--timedOut.png)
- **Erreur Playwright observée** : `Test timeout of 35000ms exceeded` en attendant `getByTestId('agents-and-skills-manager-view')` (`timeout 30000ms`).
- **Chaîne causale exacte** :
  1. Dans `apps/web/e2e/support/workspaceAndCatalogHelpers.ts:126-130`, `openCatalogOrAgentsPage` navigue vers `options.route ?? "/catalog"`, puis attend `agents-and-skills-manager-view`.
  2. Or `apps/web/src/features/catalog/index.tsx:103-135` ne monte `<AgentsAndSkillsManagerView />` que sur `catalogMode === "agents"` (`/agents`), tandis que `/catalog` (`catalogMode === "catalog"`) monte `<CatalogExplorerPanel />`.
  3. La capture montre d'ailleurs `/catalog` correctement rendu — et révèle en même temps `UX23-08` dans `packages/ui/src/shell/CatalogExplorerPanel.tsx:96,138-151` : le cadre d'état vide affiche un **`0`** littéral nu (`visibleItems.length === 0`) sous les puces techniques `depth=0 : ...` et `depth=1 : ...`.
- **Remédiation (`REM24-11` + `REM24-09`)** : Corriger `openCatalogOrAgentsPage` pour attendre `catalog-explorer-panel` sur `/catalog` et `agents-and-skills-manager-view` sur `/agents` ; remplacer le `0` nu de `CatalogExplorerPanel.tsx:148` par une phrase d'état vide métier et purger `depth=0/1` et `(cache_hit=true, 0.4ms < 50ms)`.

---

### Échec #5 (`18#5 #45`) — Banc de test MCP non audité sous `ADMIN_CONNECTION_TEST`, course UI optimiste & silo RAM (`P0`)

- **Scénario & Capture** : `#45` (`18-catalog-packs-wizards-and-mcp-bench.spec.ts:158`, `8 652 ms`) — [`failed.png`](screenshots/18-catalog-packs-wizards-and-mcp-bench/desktop-cockpit--banc-de-test-connecteur-distant-trace-audit-ledger-et-exposition-gouvernee-mcp-survivent--failed.png)
- **Erreur Playwright observée** : `expectDbRowExists` sur `SELECT id::text AS id, event_type FROM audit_ledger WHERE event_type = 'ADMIN_CONNECTION_TEST'` retourne `Expected >= 1, Received: 0`.
- **Chaîne causale exacte (Triple défaut Frontend / API / Core)** :
  1. **Divergence de schéma `audit_ledger`** : `apps/api/src/orcia_api/routers/mcp_and_test_bench.py:89-109` émet `AdminConnectionTested.create(...)` (`event_type = "AdminConnectionTested"`, `metadata.actor_type = "ADMIN_CONNECTION_TEST"`). `outbox_subscriber.py:139-145,191` persiste donc `event_type = 'AdminConnectionTested'` et `actor_type = 'ADMIN_CONNECTION_TEST'`, jamais `event_type = 'ADMIN_CONNECTION_TEST'`.
  2. **Course UI optimiste (`useCatalogRemoteTestBench.ts:44-139`)** : Au clic sur `run-test-bench-btn`, le hook peuple **synchroniquement** un résultat `PASS` codé en dur dans React (`L47-85`) puis lance `void client.runRemoteServiceTestBench(...)` (`L93-138`) sans `await`, laissant le test vérifier PostgreSQL avant que l'API ait écrit `audit_ledger`.
  3. **Absence de persistance PG18 de l'exposition MCP (`L141-160`)** : `handleActivateRemoteService` et `handleToggleMcp` ne mutent qu'un `useState` local sans appeler le backend, et `RemoteServiceTestBenchAndGovernedMcpService` (`remote_test_bench_and_mcp_exposure.py:114-115`, `workspace_and_packs.py:60-70`) maintient `_exposed_agents` et `_pat_tokens` uniquement en RAM (évincé à `e2e_test_hooks.py:55`), tout en exposant des codes bruts `1_NETWORK_TLS_ANTI_SSRF..4_HOT_DRY_RUN` + `PASS` (`UX23-08`).
- **Remédiation (`REM24-05`)** : Supprimer le `PASS` synchrone optimiste (`await` réel avec bannière confirmée après `200`), unifier le contrat `audit_ledger` (`event_type` / `actor_type`), persister en PG18 les expositions MCP & résultats du banc de test, et traduire les 4 étapes en français métier.

---

### Échec #7 (`20#1 #48`) — Table `vsm_definitions_v2` à `0` ligne (Chaîne de valeur servie en YAML/RAM uniquement) (`P0`)

- **Scénario & Capture** : `#48` (`20-process-studio-v2-finops-and-log-sink.spec.ts:88`, `21 315 ms`) — [`failed.png`](screenshots/20-process-studio-v2-finops-and-log-sink/desktop-cockpit--catalogue-agents-avec-pont-assistant-chaine-de-valeur-studio-cinq-blocs-tiroir-hitl-et-s--failed.png)
- **Erreur Playwright observée** : `expectDbRowCount` sur `SELECT COUNT(*)::int AS count FROM vsm_definitions_v2` retourne `Expected >= 1, Received: 0`, alors que `workflow_definitions_v2` (`l.83`) est bien persistée en PG18.
- **Chaîne causale exacte (Code + PG18)** : Bien que la table `vsm_definitions_v2` soit présente dans le schéma PG18 (`_first_boot_reset_guards.py:58`), `apps/api/src/orcia_api/routers/_workflows_helpers.py:80-91` (`get_vsm_store`) et `routers/workflows.py:78-94` (`GET /api/v1/vsm` et `/api/v1/vsm/{vsm_id}`) chargent exclusivement `bundle.vsm_specs` depuis les YAML vers un dictionnaire RAM `request.app.state.vsm_v2_store` (évincé à `e2e_test_hooks.py:72`). Aucun store SQL (`SqlVsmDefinitionsV2Store`) ni seed PG18 ne peuple `vsm_definitions_v2`. En parallèle, `sql_workflows_v2.py:100-103,129-130` tolère `strict_sql: bool = False` avec repli silencieux `_memory_fallback`.
- **Remédiation (`REM24-02`)** : Implémenter `SqlVsmDefinitionsV2Store` sur `vsm_definitions_v2`, seeder les VSM des packs déclaratifs de manière idempotente au bootstrap/sync packs, relier `workflows.py` au Composition Root (`dependencies/reflexive_execution.py`), et capturer une preuve visuelle VSM + tiroir HITL (`UX23-17`).

---

### Échec #8 (`20#2 #49`) — Conflit `HTTP 409 ERR_TRIGGER_DUPLICATE_KEY` causé par `tid[:8]` UUIDv7 sur `workflow_triggers` (`P0`)

- **Scénario & Capture** : `#49` (`20-process-studio-v2-finops-and-log-sink.spec.ts:158`, `15 668 ms`) — [`failed.png`](screenshots/20-process-studio-v2-finops-and-log-sink/desktop-cockpit--contrat-d-autonomie-alerte-applicative-dedupliquee-arret-d-urgence-et-gouvernance-finops--failed.png)
- **Erreur Playwright observée** : `POST /api/v1/workspaces/${ws.pgWorkspaceId}/workflows/wf-01-qualification-prd/triggers` retourne **HTTP 409** au lieu de `201` (`l.158`) après création d'un premier déclencheur `LOG_SINK_ALERT` via la modale UI (`l.135-140`).
- **Chaîne causale exacte (Mathématique UUIDv7 + Code)** :
  1. `WorkflowTriggersModal.tsx:94-105` et `useWorkflowTriggers.ts:77-95` omettent `trigger_key` dans le payload `createWorkflowTrigger`.
  2. Dans `packages/orcia-core/src/orcia_core/orchestration/_triggers_lifecycle_ops.py:46-47` :
     ```python
     tid = new_uuid7_str()
     tkey = (cmd.trigger_key or "").strip() or f"trg-{cmd.trigger_type.lower()}-{tid[:8]}"
     ```
  3. Dans un UUIDv7 (`8-4-4-4-12` hex), les `8` premiers caractères (`tid[:8]`) encodent uniquement les **32 bits supérieurs du timestamp Unix en millisecondes sur 48 bits** — valeur qui ne change que toutes les **$2^{16}\text{ ms} = 65\,536\text{ ms} \approx 65,5\text{ s}$** !
  4. Créer deux déclencheurs `LOG_SINK_ALERT` sans `trigger_key` explicite à `< 65,5 s` d'intervalle (UI à `l.135-140`, puis API à `l.146`) génère **exactement la même chaîne `tkey`**, déclenchant `TriggerDuplicateKeyError` (`HTTP 409 ERR_TRIGGER_DUPLICATE_KEY`) dans `sql_workflow_triggers.py:121-131` et `permissions/errors.py:313-316`.
- **Remédiation (`REM24-03`)** : Générer la clé par défaut à partir de l'UUIDv7 complet ou de ses bits entropiques (`tid` ou `tid.replace("-", "")[-12:]`) et exposer un champ `trigger_key` optionnel en Studio.

---

## 4. Diagnostics Architecturaux Consolidés (`ARCH24-01`..`ARCH24-12`) & Pont vers `UX23-01`..`UX23-17`

Les `8` échecs E2E ci-dessus et les `17` constats visuels `UX23-*` de [`notes-audit-sally-ux.md`](./notes-audit-sally-ux.md) convergent vers **`12` diagnostics architecturaux distincts (`ARCH24-*`)** :

| ID Winston | Sév. | Domaine / Fracture architecturale | Preuve code & mécanisme | Échecs E2E & `UX23-*` expliqués |
| --- | :---: | --- | --- | --- |
| **`ARCH24-01`** | **`P0`** | Actions Jira Staged & MCP Server 100 % RAM + singletons routeur | `jira_actions.py:191-192,331-354`, `routers/jira_and_mcp.py:36-51`, `e2e_test_hooks.py:69-70`, `GatesAdaptiveHumanReviewSection.tsx:44-49,294-311` | `06 #15`, `19#2 #47`, `UX23-01` |
| **`ARCH24-02`** | **`P0`** | `vsm_definitions_v2` jamais alimentée/lue (YAML RAM uniquement) | `routers/_workflows_helpers.py:80-102`, `routers/workflows.py:78-94`, `e2e_test_hooks.py:72`, `sql_workflows_v2.py:100-103` | `20#1 #48` |
| **`ARCH24-03`** | **`P0`** | Collision UUIDv7 `tid[:8]` (fenêtre `65,5 s`) sur `workflow_triggers` | `_triggers_lifecycle_ops.py:46-47`, `sql_workflow_triggers.py:121-131`, `permissions/errors.py:313-316`, `useWorkflowTriggers.ts:77-95` | `20#2 #49` |
| **`ARCH24-04`** | **`P0`** | Dérogations `void`, repli `default-ws` et ADN Starlark RAM | `WorkspaceDnaAndWaiversSection.tsx:45,96,171-235`, `workspaces/index.tsx:176-184`, `workspace_and_packs.py:47-57`, `workspace_governance.py:129` | `17#3 #40`, `UX23-06` |
| **`ARCH24-05`** | **`P0`** | Banc MCP : divergence `audit_ledger`, course optimiste `PASS` & RAM | `mcp_and_test_bench.py:89-109`, `outbox_subscriber.py:139-145,191`, `useCatalogRemoteTestBench.ts:44-160`, `remote_test_bench_and_mcp_exposure.py:114-115` | `18#5 #45`, `UX23-08` (étapes MCP) |
| **`ARCH24-06`** | **`P1`** | Locators & helpers E2E désalignés (`openCatalogOrAgentsPage`, `<option>`, captures) | `workspaceAndCatalogHelpers.ts:126-130`, `catalog/index.tsx:103-135`, `07-spaces...spec.ts:42`, captures splash `00`/`04` & `20#1` | `18#1 #41`, `07 #16`, `UX23-17` |
| **`ARCH24-07`** | **`P1`** | Poches RAM résiduelles, `strict_sql=False` & URI/WS codés en dur | `_workflows_helpers.py:94-102`, `sql_workflows_v2.py:100-130`, `two_speed_search.py:181,192`, `portal_and_assistant.py:136-173`, `cockpit/index.tsx:113`, `portal_and_help.py:79,94`, `PacksRegistryPage.tsx:35,53-57` | Transversal PG18 / `AD-19` / `AD-24` |
| **`ARCH24-08`** | **`P1`** | CSS import order (`main.tsx:1-2` + `tokens.css` écrasant `md:`/`sm:`/`xl:`), dark contrast, transition onglets `150ms` & modale/shell `100vh` | `main.tsx:1-2`, `viteTailwindV4Plugin.ts:62-123`, `tokens.css:184-191,262,293,548-577,752-755`, `UserSettingsModalDialog.tsx:197,219`, `FinopsKpiStrip.tsx:94`, `FinopsGovernanceDashboardView.tsx:163`, `AgentDetailAndSandboxModal.tsx:131-145`, `FourZoneDirectionCShell.tsx:185-193,254-257,282-293`, `FourZoneHelpAsideColumn.tsx:65-72` | `UX23-02`, `UX23-03`, `UX23-04`, `UX23-13`, `UX23-14` |
| **`ARCH24-09`** | **`P1`** | Identité Accostage (`authDisplayName` vs `platformAdmin`), routage Zone 4 `/inbox`, Sidebar `/showcase`, `/organization` & Jour 0 | `cockpit/index.tsx:204-213`, `platformSetupHydration.ts:195-204`, `bootstrap_accostage.py:97-98`, `_contextualHelpSections.ts:242`, `shellPresets.ts:80,89,103,110,256-260`, `FirstBootAdminSetupModal.tsx`, `FourZoneSidebarRail.tsx` | `UX23-07`, `UX23-09`, `UX23-15` |
| **`ARCH24-10`** | **`P1`** | Recherche `⌘K` non filtrée par `lang`, émoji rouge `❓`, jargon UI, `0` nu & Markdown brut | `sql_federated_search.py:81-121`, `portal_and_help.py:72-124`, `TopHeaderSearchCommand.tsx`, `CatalogExplorerPanel.tsx:96,138-151`, `PermissionBrokerCard.tsx:77`, `ArbitrationTieBreakCard.tsx`, `PacksRegistryPage.tsx`, `docs/help/fr/` | `UX23-05`, `UX23-08`, `UX23-10`, `UX23-12` |
| **`ARCH24-11`** | **`P2`** | Troncatures `1440×900`, microcopy & ergonomie `/finops` (`Journal d'Activité →` & décimales) | `StudioCopilotSidebar`, `IamSecopsExceptionForm.tsx`, `apps/web/src/features/finops/index.tsx:344-353`, `FinopsKpiStrip.tsx:45-47`, `sql_finops_dashboard.py:68-94`, `apps/web/src/features/ontology/index.tsx` | `UX23-11`, `UX23-14` (FinOps), `UX23-16` |
| **`ARCH24-12`** | **`P2`** | Gouvernance `ACTION_ITEM-23.6` (`CAP-042` reporté hors Epic 23) & porte `Case B` Epic 24 | `sprint-status.yaml`, `sprint-change-proposal-2026-11-18-epic-23-remediation-plan.md`, `bilan-execution-tests-e2e-epic-23.md` | `#14`, `#25`, `#27` (`mobile-only` skipped), Clôture `23.8` -> Epic 24 |

### 4.1 Zoom sur la fracture CSS Tailwind v4 × `tokens.css` (`ARCH24-08`)

L'inspection conjointe de `apps/web/src/main.tsx:1-2`, `apps/web/viteTailwindV4Plugin.ts` et `packages/ui/src/styles/tokens.css` explique à **`100 %`** pourquoi plusieurs dispositions responsives écrites dans `@orcia/ui` sont inopérantes à `1440×900` :

1. `main.tsx:1-2` charge `virtual:orcia-tailwind.css` **avant** `@orcia/ui/styles/tokens.css`.
2. `tokens.css:256-305` duplique des utilitaires non-layered (`.flex-col` `L262`, `.grid-cols-1` `L293`) **après** la feuille Tailwind compilée : par égalité de spécificité `(0,1,0)`, `.flex-col` écrase `md:flex-row` dans `UserSettingsModalDialog.tsx:197` (`UX23-02`, générant le vide vertical de ~220 px) et `.grid-cols-1` écrase `sm:grid-cols-2 xl:grid-cols-4` dans `FinopsKpiStrip.tsx:94` (`UX23-14`, empilant les 4 KPIs sur 1 colonne).
3. Sur `/finops` (`12 #24`), `.orcia-ds-tab` (`tokens.css:559`) applique `transition: all 150ms ease;` : une capture immédiatement après `.click()` (`12-finops-and-audit-provenance.spec.ts:68-69`) saisit l'onglet en cours d'interpolation entre `#DBEAFE`/`#1E3A8A` et `#2563EB`/`#FFFFFF` (`UX23-04`). Simultanément, `FinopsScopePills` (`FinopsGovernanceDashboardView.tsx:163`) applique la classe `.active` au lieu de `[aria-selected="true"]`, et `[data-theme="dark"]` (`tokens.css:184,191,752-755`) combine `#2563EB` sur `#1E293B` (`2,86:1`).
4. Sur la coquille Desktop (`FourZoneDirectionCShell.tsx:188-193,256`), `height: 100vh; overflow: hidden` coupe Zone 1 et Zone 4 à `900 px` lors des captures `fullPage` jusqu'à `1563 px` (`UX23-13`).

---

## 5. Recoupement `ACTION_ITEM-23.6` (`CAP-042`) & Recommandation Topologique Epic 24

1. **`ACTION_ITEM-23.6` / `CAP-042` (`Mobile Companion 390×844`)** : Les `3` scénarios `skipped` observés (`#14` `05-mobile-companion`, `#25` `12-finops`, `#27` `13-epic-7`) sont conformes au périmètre gelé `--project=desktop-cockpit`. La capacité `CAP-042` reste différée hors Epic 23/24 sous `ACTION_ITEM-23.6` tant que le produit priorise la clôture Desktop, sauf réintégration explicite décidée en sprint planning.
2. **Ordonnancement strict recommandé pour l'Epic 24 (`Case B`)** :
   - **Vague 0 (Persistance PG18 & Contrats bloquants — Stories `24.1`–`24.3`)** : résoudre d'abord `ARCH24-01` (Jira Staged PG18 + MCP server), `ARCH24-02` (`vsm_definitions_v2` SQL), `ARCH24-03` (`trigger_key` UUIDv7 non tronqué), `ARCH24-04` (`await` dérogations + ADN PG18 + fin `default-ws`), `ARCH24-05` (Banc MCP `audit_ledger` + fin `PASS` optimiste) et `ARCH24-07` (retrait des singletons hors Composition Root & `strict_sql=True`).
   - **Vague 1 (Socle CSS, Shell/Navigation, RGAA & Zéro Jargon — Stories `24.4`–`24.6`)** : assainir l'ordre CSS Tailwind v4 vs `tokens.css` (`UX23-02`, `UX23-04`, `UX23-13`, `UX23-14`), migrer `AgentDetailAndSandboxModal` vers `OrciaDialog` (`UX23-03`), corriger Accostage identité/rôles (`UX23-07`), aligner Breadcrumb/Zone 4 `/inbox`/`/showcase`/`/organization` (`UX23-09`, `UX23-15`), filtrer `⌘K` par langue + `OrciaIcon` (`UX23-05`), purger 100 % du jargon UI et corriger troncatures/microcopy (`UX23-08`, `UX23-10`, `UX23-11`, `UX23-12`, `UX23-16`).
   - **Vague 2 (Réconciliation E2E & Campagne Finale Desktop — Story `24.7`)** : corriger `openCatalogOrAgentsPage` (`#41`), scoper `07 #16` sur `<main>`, enrichir les captures jalons (`UX23-17`), puis exécuter la campagne finale **`52 / 52` PASS Desktop (`0` échec, `0` `P0`, `0` `P1`)** et promouvoir `capabilities.yaml`.
