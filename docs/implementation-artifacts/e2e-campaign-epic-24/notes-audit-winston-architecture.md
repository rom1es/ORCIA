# 🏗️ Contre-Audit Croisé Architecture, Vérité PostgreSQL 18 & Frontières Direction C — Campagne E2E Epic 24 (`24.7-winston`)

- **Auditeur** : 🏗️ **Winston** (System Architect — `bmad-architect-worker`)
- **Date** : `2026-11-20`
- **Branche / État audité** : `feat/epic-24-remediation-pg18-ux-and-cockpit` (base `303ba27` + réconciliations `Story 24.7`)
- **Périmètre exécuté** : `--project=desktop-cockpit` (`1440×900`, `24` fichiers `.spec.ts`, `--retries=0 --max-failures=0`, `env -u ORCIA_E2E_SEED_FIXTURES`, post-`pnpm db:reset`)
- **Référentiels appliqués** :
  - [`ARCHITECTURE-SPINE.md`](../../planning-artifacts/architecture/architecture-ORCIA-2026-10-24/ARCHITECTURE-SPINE.md) (`AD-1`..`AD-24`)
  - [`sprint-change-proposal-2026-11-20-epic-24-remediation-plan.md`](../../planning-artifacts/sprint-change-proposal-2026-11-20-epic-24-remediation-plan.md) (`ARCH24-01`..`ARCH24-12`, `REM24-01`..`REM24-12`, `USER24-BUG-1`..`6`)
  - [`bilan-execution-tests-e2e-epic-24.md`](./bilan-execution-tests-e2e-epic-24.md), [`playwright-results.json`](./playwright-results.json), [`manifest.jsonl`](./manifest.jsonl)
  - Rapports Tech Lead Stories `24.1`..`24.6` ([`docs/implementation-artifacts/tech-lead-reports/`](../tech-lead-reports/README.md))
  - Contre-audit visuel : [`notes-audit-sally-ux.md`](./notes-audit-sally-ux.md) (`61/61` PNG inspectés : `0 P0`, `0 P1`, `3 P2`, `4 P3`)

---

## 1. Synthèse exécutive & Chiffres de vérité PostgreSQL 18

🏗️ La campagne figée Epic 24 (`719 690,61 ms` = `11,99 min`, code de sortie `0`) confirme l'éradication des `8` échecs/timeouts Desktop qui avaient déclenché `Case B` en Epic 23 (`dd2d382`) :

| Indicateur campagne (`desktop-cockpit`) | Epic 22 (`a1bb059`) | Epic 23 (`dd2d382`) | Epic 24 (`Story 24.7`) | Écart vs Epic 23 |
| --- | ---: | ---: | ---: | ---: |
| Fichiers `.spec.ts` `100 %` PASS Desktop | `0 / 24` | `18 / 24` | **`24 / 24`** | **`+6` specs** |
| Scénarios planifiés | `55` | `55` | `55` | `0` |
| `passed` (`expected`) | `7` | `44` | **`52`** | **`+8`** |
| `failed` + `timedOut` (`unexpected`) | `46` (`46` + `0`) | `8` (`7` + `1`) | **`0`** (`0` + `0`) | **`-8`** |
| `skipped` (`mobile-only` `#14`, `#25`, `#27`) | `2` | `3` | `3` | `0` (`ACTION_ITEM-23.6`) |
| `flaky` | `0` | `0` | **`0`** | `0` |
| Taux de succès (`passed / exécutés`) | `13,2 %` | `84,6 %` | **`100,0 %` (`52 / 52`)** | **`+15,4 pts`** |
| Captures PNG sur disque (`< 450 KB`) | `55` | `58` | **`61`** (max `274 576 B`) | `+3` jalons (`0` > `450 KB`) |

### 1.1 Verdict sur la porte de sortie Epic 24 (`Case A` sans Epic 25)

Conformément à la section 7 du [Plan Directeur Epic 24](../../planning-artifacts/sprint-change-proposal-2026-11-20-epic-24-remediation-plan.md) :
1. **`52 / 52` PASS Desktop (`0` échec, `0` timeout, `0` retry, `0` flaky, `0` fixture cachée)** : **ATTEINT ✅**.
2. **`0 P0 / 0 P1` au contre-audit visuel Sally** (`61/61` PNG inspectés : `0 P0`, `0 P1`, `3 P2`, `4 P3`) : **ATTEINT ✅**.
3. **`ACTION_ITEM-23.6` (`CAP-042` Mobile Companion `390×844`)** : `3` skips `mobile-only` conformes au report tracé séparément : **CONFORME ✅**.

**Verdict architectural formel :** **`Case A — Clôture Epic 24 autorisée sans Epic 25`**, sous réserve d'appliquer en Phase 3 de `Story 24.7` la correction triviale du drift de test unitaire `tests/unit/test_hybrid_rag_and_tripartite.py:305` (`"ws-claims-alpha"` $\rightarrow$ `"scope-global"`) puis la promotion de `capabilities.yaml` (`64/65` `runtime`) et le passage de `epic-24: done`.

---

## 2. Vérification des Preuves Architecturales (`AD-1`..`AD-24`, `AD-19`, PG18 & Redis 7.4)

### 2.1 Vérification directe des `12` diagnostics `ARCH24-01..ARCH24-12`

| ID | Diagnostic initial Epic 23 | Vérification code & artefacts Epic 24 (lecture directe) | Preuve E2E / PG18 | Statut |
| --- | --- | --- | --- | :---: |
| **`ARCH24-01`** | Actions Jira Staged & MCP Server 100 % RAM + singletons routeur (`jira_and_mcp.py`) | Révision Alembic `20261120_2401` (`jira_staged_actions`, `mcp_governed_proposals`) en SQL pur + UUIDv7 ; `SqlJiraStagedActionsRepository` & `SqlMcpProposalsRepository` câblés dans `apps/api/src/orcia_api/dependencies/jira_and_mcp.py:17-54` avec `strict_sql` ; singletons supprimés de `routers/jira_and_mcp.py` ; tables ajoutées à `_first_boot_reset_guards.py:58`. | `06 #15`, `19#2 #47` (`EXECUTED` survit à `reloadColdFromPg`) + `test_story_24_1_jira_mcp_vsm_postgres18.py` | ✅ **Résolu** |
| **`ARCH24-02`** | `vsm_definitions_v2` jamais alimentée/lue (YAML RAM) & `strict_sql=False` | `SqlVsmDefinitionsV2Store` + `load_vsm_definitions_from_pg18` (`_workflows_helpers.py:74-105`), seed idempotent, `get_vsm_v2_sql_store` dans `dependencies/reflexive_execution.py:139-153`, `SqlWorkflowDefinitionsV2Store` (`sql_workflows_v2.py:42-46,136-139`) strict sous PG18. *(Note `P3` : `get_workflow_v2_runs_store` L156-164 reste une map d'inspection mémoire, les runs persistants étant dans `reflexive_execution_sessions`).* | `20#1 #48` (`vsm_definitions_v2 >= 1` après `reloadClearingStorage`, `milestone-vsm-11-steps.png`) | ✅ **Résolu** |
| **`ARCH24-03`** | Collision UUIDv7 `tid[:8]` (`65,5 s`) sur `workflow_triggers` | `_triggers_lifecycle_ops.py:46-48` utilise `entropy_suffix = tid.replace("-", "")[-12:]` (48 bits aléatoires UUIDv7 au lieu des 32 bits MSB timestamp) + `trigger-create-key-input` dans `WorkflowTriggersModal`. | `20#2 #49` (`0` erreur `409` en rafale) + `test_story_24_2_triggers_dna_pg18.py` (`1 000` créations/ms) | ✅ **Résolu** |
| **`ARCH24-04`** | Waivers `void`, repli `default-ws` et ADN Starlark RAM | Révision `20261120_2402` (`workspace_dna_mechanisms`) ; `SqlStarlarkMechanismRepository` injecté dans `dependencies/workspace_and_packs.py:62-84` (`strict_sql`) ; `WorkspaceDnaAndWaiversSection` `await` strict + non-monté à `0` espace ; `WorkspaceFiveTabsPanels` commute les 5 onglets ; `"default-ws"`, `"ws-claims-alpha"`, `"ws-mon-compte"` purgés du code applicatif (`rag_seeds.py:24` $\rightarrow$ `"scope-global"`). | `17#3 #40` (`workspace_dna_mechanisms >= 1`, `workspace_exception_waivers`, `kb_documents`, `tripartite_trace_edges`), `11 #21` (`0` `default-ws`) | ✅ **Résolu** |
| **`ARCH24-05`** | Banc MCP : divergence `audit_ledger`, course optimiste `PASS` & RAM | Révision `20261120_2403` (`mcp_exposed_agents`, `mcp_governed_pat_tokens` SHA-256 uniquement, `ADMIN_CONNECTION_TEST` dans `domain_events_outbox_event_type_check`) ; `SqlMcpExposureRepository` dans `dependencies/workspace_and_packs.py:87-112` ; suppression du `PASS` optimiste dans `useCatalogRemoteTestBench.ts` (`await` HTTP `200`). | `18#5 #45` (`SELECT ... FROM audit_ledger WHERE event_type = 'ADMIN_CONNECTION_TEST'`) + `test_story_24_3_mcp_audit_and_redis_postgres18.py` | ✅ **Résolu** |
| **`ARCH24-06`** | Locators & helpers E2E (`openCatalogOrAgentsPage`, `<option>`, captures) | Distinction `catalog-explorer-panel` (`/catalog`) vs `agents-and-skills-manager-view` (`/agents`) ; `07-spaces` borné à `main` ; `ensureNonBlankPage` (`e2eCaptureFixture.ts:69-72`) attend `auth-hydrating-loader` hidden ; `3` nouveaux jalons `< 450 KB`. | `18#1 #41` (`10,2 s` vs timeout `35 s`), `07 #16` (`15,0 s`), `00 #3/#4`, `04 #12`, `61` PNG | ✅ **Résolu** |
| **`ARCH24-07`** | Poches RAM résiduelles (`_speed2_cache`, `wfKey`, `PacksRegistryPage`) | `TwoSpeedFederatedSearchService` (`two_speed_search.py:181-199`) adossé à Redis 7.4 (`_speed2_redis_cache.py`, TTL `300 s`, clé `(user_id, user_role, workspace_id, scope, route, locale)`) et vidage du cache unitaire dès `redis_client is not None` ; `PacksRegistryPage` sur `/api/v1/packs/health` ; `wfKey` réel dans `cockpit/index.tsx`. *(Note `P3` : `AgentsAndSkillsManagementService` L167-179 garde une synchro routeur `persist_*_to_postgres18` plutôt qu'un port repository injecté avec `strict_sql=True`, bien que la persistance PG18 fonctionne en `08`.)* | `10 #20`, `18 #43`, `24-3` integration Redis `TTL <= 300s` | ✅ **Résolu** |
| **`ARCH24-08`** | CSS import order (`main.tsx:1-2`), Tailwind v4 écrasé, contrastes, `100dvh`, `USER24-BUG-1,4A,4B,5` | `main.tsx:1-2` charge `tokens.css` avant `virtual:orcia-tailwind.css` ; `tokens*.css` scindé en `6` partials `< 280` L sans `.flex-col`/`.grid-cols-1` non layerés ; `tokens-dark.css:13` `#93C5FD` sur `#1E293B` (`8,45:1`) ; `tokens-shell.css:22-32` (`height: 100dvh; overflow: hidden`) ; `AgentDetailAndSandboxModal` (`204` L) sur `OrciaDialog` ; `UserSettingsModalDialog` onglets horizontaux ; fin doublon `Paramètres` ; reset secret PAT. | `61/61` PNG sans `#EAF2FB`, `12 #24`, `13 #26`, `14 #30`, `08 #17`, `shell #52..55` | ✅ **Résolu** *(hors `UX24-01` `P2`)* |
| **`ARCH24-09`** | Identité Accostage, Zone 4 `/inbox`, `/showcase`, `/organization`, Jour 0, `USER24-BUG-2` | `first-admin` $\rightarrow$ `/profile` (`01 #5`) ; `platform_admin_display_name` & `visible_milestones` filtrés (`14 #29`) ; `/inbox` Zone 4 dédiée (`04 #12`, `15 #34`) ; `/showcase` $\rightarrow$ `"help"` (`shellPresets.ts:113`) ; `/organization` autonome (`15 #33`) ; `ShellContainer.tsx` scindé (`378` $\rightarrow$ `269` L) ; `FirstBootAdminSetupModal` sans bouton `Fermer`. | `01 #5`, `04 #12`, `14 #29`, `15 #33`, `15 #34`, `shell #53/#55` | ✅ **Résolu** *(hors `UX24-02` `P2`)* |
| **`ARCH24-10`** | Recherche `⌘K` non filtrée `lang`, émoji `❓`, jargon UI, `USER24-BUG-3` | `sql_federated_search.py:51-154` filtre `HELP_ARTICLE` sur `:locale` ; `OrciaIcon` blanc dans `⌘K` (`10 #20`) ; `renderInlineMarkdownNodes` dans `ContextualHelpSharedBlocks.tsx` (`USER24-BUG-3`) ; `<FormattedMarkdownContent />` + `safeDecodeUri` dans `PermissionBrokerCard` (`16 #37`) ; traduction 100 % des enums/étapes (`03`, `06`, `15 #34`, `16 #35`, `18 #41`, `18 #43`). | `10 #20`, `16 #37`, `18 #41`, `18 #43`, `21 #51` | ✅ **Résolu** *(hors `UX24-03` `P2`, `UX24-04` `P3`)* |
| **`ARCH24-11`** | Troncatures `1440×900` & microcopy | `IamSecopsExceptionForm.tsx` scindé (`403` $\rightarrow$ `203` L, `Plateforme entière (Global)` entier), Studio & Espaces placeholders entiers, `Journal d'Activité →` aligné, `4 espaces` `/showcase`, `4 paliers cognitifs`, majuscule cassette. | `02 #7`, `07 #16`, `09 #18`, `12 #24`, `15 #32`, `16 #35`, `21 #51` | ✅ **Résolu** |
| **`ARCH24-12`** | Gouvernance `ACTION_ITEM-23.6` (`CAP-042`) & porte `Case A` Epic 24 | `52 / 52` PASS Desktop (`0` échec, `0` timeout, `0` flaky), `3` skips `mobile-only` (`#14`, `#25`, `#27`) sous `ACTION_ITEM-23.6`, contre-audit `0 P0 / 0 P1` prêt pour promotion `64/65` `capabilities.yaml`. | `playwright-results.json`, `manifest.jsonl`, `bilan-execution-tests-e2e-epic-24.md` | ✅ **Résolu** |

### 2.2 Invariants Statiques, Monolithe Modulaire (`AD-19`) & Migrations PG18

- **Contrats `import-linter` (`pyproject.toml:103-179`)** : Les `5` contrats `AD-19` / `AD-20` restent strictement définis et préservés (`api/worker -> connectors -> core`, hiérarchie acyclique intra-`orcia_core`, zéro framework/SDK dans `kernel/domain/ports`, isolation `orcia_core` $\nrightarrow$ `orcia_connectors`, exclusion `docling` hors `worker.docling_indexer`), vérifiés `5/5` (`0 broken`) à travers les Stories `24.1..24.6` et la passe Phase 1.
- **Règle `TID251` & Event Loop ASGI (`pyproject.toml:194-200`)** : `httpx.Client`, `requests` et `urllib.request` demeurent bannis des routeurs/services ASGI ; `ruff`, `mypy --strict`, `lint_spine.py` (`0` finding) et OpenAPI `0-diff` (`packages/api-client`) ont été maintenus tout au long de la remédiation `24.1..24.6` et contrôlés en Phase 1.
- **Intégrité Schéma PG18 & Reset Jour 0** : Les `3` nouvelles révisions Alembic (`20261120_2401`, `20261120_2402`, `20261120_2403`) utilisent exclusivement du SQL brut (`op.execute(sa.text(...))`), des clés primaires `UUIDv7` sans secret en clair, un `downgrade()` réversible, et toutes les nouvelles tables mutables (`jira_staged_actions`, `mcp_governed_proposals`, `workspace_dna_mechanisms`, `mcp_exposed_agents`, `mcp_governed_pat_tokens`) sont enregistrées dans `ORDERED_MUTABLE_TABLES_TO_CLEAR` (`_first_boot_reset_guards.py:57-58`) — prouvé par le reset Jour 0 pré-campagne (`cleared_tables=71, deleted_rows=272, remaining_users=0`).
- **Preuves d'intégration réelle `testcontainers` PG18 + Redis 7.4 (Phase 1 & Stories `24.1..24.6`)** :
  - Suite complète d'intégration remontée en Phase 1 : **`92 / 92` tests d'intégration `testcontainers` PASS** et **`92,17 %` de couverture combinée** (`>= 90 %` requis), confirmant les écritures/relectures à froid `create_app()` sans override sur l'ensemble des flux `24.1..24.6`.
  - **Drift unitaire mineur identifié en Phase 1 (à corriger avant clôture finale Phase 3)** : dans [`tests/unit/test_hybrid_rag_and_tripartite.py:305`](../../../tests/unit/test_hybrid_rag_and_tripartite.py#L305), le test envoie encore `"workspace_id": "ws-claims-alpha"` vers `POST /api/v1/ontology-rag/rag/search?fixture=true`, alors que la purge `"ws-claims-alpha"` livrée en `Story 24.2` dans [`packages/orcia-core/src/orcia_core/bootstrap/rag_seeds.py:24`](../../../packages/orcia-core/src/orcia_core/bootstrap/rag_seeds.py#L24) a remplacé la valeur par défaut par `"scope-global"`. La mise à jour de `"ws-claims-alpha"` $\rightarrow$ `"scope-global"` dans ce test unitaire (sans toucher au code applicatif) est requise en Phase 3 pour clôturer `24.7` avec `100 %` de la suite unitaire au vert.

---

## 3. Observations Architecturales Mineures (Non Bloquantes)

1. **`AgentsAndSkillsManagementService` (`dependencies/workspace_and_packs.py:167-179`)** (`P3`) : La persistance PG18 passe par les helpers du routeur (`_sync_from_postgres18_if_enabled` dans `routers/agents_and_skills.py:93-100`) plutôt que par un port repository injecté avec `strict_sql=True`. Fonctionnel et vérifié par E2E `08`, mais bon candidat d'harmonisation dans un lot d'hygiène futur.
2. **`get_workflow_v2_runs_store` (`dependencies/reflexive_execution.py:156-164`)** (`P3`) : Conserve une table mémoire d'inspection pour `BoundedWorkflowRunState`, tandis que les exécutions réflexives durables s'appuient bien sur `SqlReflexiveSessionStore` (`reflexive_execution_sessions`).
3. **Hydratation `PlatformSetupProvider` sur route standalone `/showcase` (`ShellContainer.tsx:82,127`)** (`P2` côté UX `UX24-02`) : Lors d'un rechargement à froid avec `localStorage` vidé, la coquille s'affiche avant la réponse `getAccostageStatus()`, provoquant un état transitoire `adminCreated = false` tant que l'appel est en vol.

---

## 4. Décision Architecturale Finale (`Case A`)

**Verdict Winston :** **`Case A — Clôture Epic 24 autorisée sans Epic 25`**.
La Phase 3 finale de `Story 24.7` est autorisée à :
1. Corriger le drift unitaire `tests/unit/test_hybrid_rag_and_tripartite.py:305` (`"ws-claims-alpha"` $\rightarrow$ `"scope-global"`) et valider l'exécution complète de `pytest` (`>= 90 %`), `lint-imports`, `ruff`, `mypy --strict`, `lint_spine.py`, OpenAPI `0-diff` et `pnpm turbo run lint typecheck test` ;
2. Promouvoir les **`25` capacités Desktop `failed_e2e`** vers `verification: runtime` (`verified_at: "2026-11-20"`) dans [`docs/product/capabilities.yaml`](../../product/capabilities.yaml) (`64 / 65` `runtime`, `CAP-042` inchangée sous `ACTION_ITEM-23.6`) ;
3. Tracer les `3 P2` / `4 P3` UX/hygiène dans un ticket borné `action_items:` (sans Epic 25), compléter le [rapport Tech Lead `24.7`](../tech-lead-reports/24-7-reconciliation-e2e-captures-jalons-campagne-52-sur-52-et-cloture-epic-24-tech-lead-report.md), clôturer `24-7` et `epic-24: done` dans `sprint-status.yaml`, puis exécuter `pnpm site:sync && pnpm site:check` et `npx gitnexus analyze`.
