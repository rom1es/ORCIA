# Rapport Tech Lead — Story 24.3 : Banc de Test MCP, Audit Ledger, Fin du PASS Optimiste & Assainissement Composition Root

- **Story :** `24-3-banc-mcp-audit-ledger-fin-pass-optimiste-et-assainissement-composition-root` (Epic 24 — Vague 0 `P0/P1`)
- **Date :** 2026-11-20
- **Statut :** `Terminé (`done`)` — Validé 5 couches `AD-17` (`92 %` couv. combinée, `9/9` Turbo, `7/7` E2E Desktop `03`/`19`/`18#2..18#5`)
- **Plan directeur :** [`sprint-change-proposal-2026-11-20-epic-24-remediation-plan.md`](../../planning-artifacts/sprint-change-proposal-2026-11-20-epic-24-remediation-plan.md)
- **Références remédiées :** `REM24-05`, `REM24-06` | Échec E2E `18#5 #45` | Constat `UX23-08` (étapes banc MCP) | Diagnostics `ARCH24-05`, `ARCH24-07`, `ARCH24-12`
- **Capacité(s) (`capabilities.yaml`) :** `CAP-055`, `CAP-082`, `CAP-092`, `CAP-150`, `CAP-200` (`5` capacités Desktop `failed_e2e`)
- **Classification :** `feature` (vérité HTTP, traçabilité append-only & assainissement DI/Redis)

---

## 1. Analyse du Besoin & Étude d'Impact Tech Lead

### 1.1 Contexte & Critères d'Acceptation
Le scénario `18#5 #45` (`18-catalog-packs-wizards-and-mcp-bench.spec.ts`) échoue sur deux falsifications symétriques UI ↔ Backend, aggravées par des résidus de caches en mémoire :
1. **PASS optimiste synchrone & exposition MCP volatil (`ARCH24-05`)** : `useCatalogRemoteTestBench.ts` (`171` L) positionne un statut `PASS` optimiste avant la réponse HTTP réelle, tandis que `RemoteServiceTestBenchAndGovernedMcpService` (`remote_test_bench_and_mcp_exposure.py` `440` L) stocke `_exposed_agents` et `_pat_tokens` en RAM et que `handleToggleMcp` / `handleActivateRemoteService` ne persistent pas leurs mutations via `PUT /api/v1/mcp/exposure`.
2. **Désynchronisation contrat `audit_ledger` (`ARCH24-07`)** : la requête attendue par la gouvernance/test (`WHERE event_type = 'ADMIN_CONNECTION_TEST'`) diverge du schéma/projection réel (`AuditLedgerOutboxSubscriber` / `audit_ledger`), provoquant un défaut de traçabilité append-only lors des tests de connexion.
3. **Résidus Composition Root & RAM (`ARCH24-12` / `REM24-06`)** : `TwoSpeedFederatedSearchService._speed2_cache` reste en RAM par worker ; `PacksRegistryPage.tsx` (`381` L) et `cockpit/index.tsx:113` (`wfKey`) conservent des branchements partiels ou statuts statiques hors API réelle.

**Critères d'acceptation :** suppression complète du `PASS` optimiste (statut en attente jusqu'à HTTP `200`, erreur visible `[role="alert"]` sur échec), persistance PG18 des expositions MCP et jetons PAT, écriture idempotente et vérifiée dans `audit_ledger` (`ADMIN_CONNECTION_TEST`), migration `_speed2_cache` vers Redis `300s` cloisonné par contexte, et `18#5 #45` PASS.

### 1.2 Analyse d'Impact GitNexus (`repo: "/home/romain/Documents/Projects/ORCIA"`)
- `RemoteServiceTestBenchAndGovernedMcpService` (`packages/orcia-core/src/orcia_core/orchestration/remote_test_bench_and_mcp_exposure.py:111-440`) : `impactedCount: 261`, `risk: "CRITICAL"`, `epistemic: "exact"` (`direct: 242`, `d=2: 19`, `processes_affected: 32`, `modules_affected: 20`).
- `AuditLedgerOutboxSubscriber` (`packages/orcia-core/src/orcia_core/audit_finops/outbox_subscriber.py:242-264`) : `impactedCount: 261`, `risk: "CRITICAL"`, `epistemic: "exact"` (`direct: 242`, `d=2: 19`, `processes_affected: 32`, `modules_affected: 20`).
- `TwoSpeedFederatedSearchService` (`packages/orcia-core/src/orcia_core/rag/two_speed_search.py:171`) : `ambiguous` (`totalCandidates: 9`, candidat principal `L171` : `impactedCount: 261`, `risk: "CRITICAL"`, `direct: 242`).
- `runRemoteServiceTestBench` (`bootstrapAndOntology.ts:222`) : résolu dans l'index (`impactedCount: 0`, appel indirect via `useCatalogRemoteTestBench.ts:94`).
- Impact API (`gitnexus api_impact`) : `apps/api/src/orcia_api/routers/mcp_and_test_bench.py` (`236` L, `3` routes HTTP).

### 1.3 Opportunités de Factorisation & Contrôle de Volumétrie (`< 350` L)
- **Découpage obligatoire `remote_test_bench_and_mcp_exposure.py` (`440` L > seuil `400` L)** : séparer le banc de test distant (`RemoteServiceTestBenchService` + garde SSRF `is_safe_llm_endpoint_url`) de l'exposition gouvernée MCP (`McpExposureService` + adaptateur PG18) en deux modules `< 250` L.
- **Contrôle de `PacksRegistryPage.tsx` (`381` L)** : extraire la sous-vue des healthchecks API en préparation du travail complémentaire `24-6` sur les compteurs pour rester sous `< 300` L.
- **Clé de cache Redis unifiée** : factoriser la construction de clé dans `orcia_kernel` / `rag` (`user_id`, `role`, `workspace_id`, `scope`, `route`, `locale`) afin d'éviter toute fuite inter-tenant dans `TwoSpeedFederatedSearchService`.

---

## 2. Plan d'Implémentation

### 2.1 Couche Données & Migrations Alembic / PostgreSQL 18
1. Inspecter les tables existantes (`catalog_items`, `audit_ledger`, `domain_events_outbox`) ; si nécessaire, ajouter une révision Alembic `Expand` dédiée aux expositions MCP (`mcp_exposed_agents` / colonnes gouvernées + hash jeton PAT, jamais de secret en clair).
2. Aligner le contrat canonique `audit_ledger` sans modifier les triggers append-only (`BEFORE UPDATE OR DELETE RAISE EXCEPTION`) : conserver la structure append-only et vérifier les colonnes exactes (`event_type = 'ADMIN_CONNECTION_TEST'`, `actor_type`, `payload_jsonb`).
3. Enregistrer toute nouvelle table mutable dans `_first_boot_reset_guards.py` (tout en maintenant `audit_ledger` dans `APPEND_ONLY_TABLES`).

### 2.2 Noyau Hexagonal (`orcia-kernel` / `orcia-core`) & Workers
1. Découper `remote_test_bench_and_mcp_exposure.py` (`440` L $\rightarrow$ deux modules `< 250` L) et remplacer `_exposed_agents` / `_pat_tokens` RAM par une persistance PG18 stricte + hash SHA-256 / secret chiffré pour les jetons PAT.
2. Enregistrer l'événement `ADMIN_CONNECTION_TEST` via `domain_events_outbox` / `AuditLedgerOutboxSubscriber` (avec clé d'idempotence) de façon transactionnelle lors des exécutions du banc de test distant.
3. Migrer `TwoSpeedFederatedSearchService._speed2_cache` vers le client Redis `7.4` injecté (TTL `300s`, clé déterministe incluant `user_id`, `role`, `workspace_id`, `scope`, `route`, `locale`).

### 2.3 Backend FastAPI (`apps/api`) & Contrat OpenAPI (`packages/api-client`)
1. Vérifier `apps/api/src/orcia_api/routers/mcp_and_test_bench.py` (`3` routes) et le câblage dans `apps/api/src/orcia_api/dependencies/` (zéro instanciation au niveau module, `Audit` complet `dependencies/` pour `ARCH24-12`).
2. Aligner les schémas Pydantic v2 (`RemoteServiceTestBenchResult` / `McpExposureRequest` / `PacksHealthResponse`), exposer le statut réel des healthchecks pour `PacksRegistryPage`, et régénérer `@orcia/api-client` (`0-diff`).

### 2.4 Interface SPA Vite + TanStack Router & Design System (`@orcia/ui` / `apps/web`)
1. Dans `apps/web/src/features/catalog/useCatalogRemoteTestBench.ts` (`171` L) et `RemoteServiceTestBenchAndMcpExposureView.tsx` (`194` L) :
   - Supprimer le `PASS` optimiste synchrone ; afficher un état « Vérification en cours… » durant la promesse et ne passer à `Réussi` (ou `PASS` sur `data-status` technique si requis) qu'après réception effective HTTP `200`, ou basculer en alerte `[role="alert"]` sur erreur `>= 400`.
   - Câbler `handleToggleMcp` et `handleActivateRemoteService` sur `PUT /api/v1/mcp/exposure` via `@orcia/api-client` avec rechargement à froid depuis `GET`.
2. Brancher `PacksRegistryPage.tsx` (`381` L, extrait en sous-composants `< 300` L) sur les healthchecks API réels et corriger `apps/web/src/features/cockpit/index.tsx:113` pour utiliser le `wfKey` réel au lieu d'une valeur figée.

### 2.5 Stratégie de Vérification & 5 Couches de Tests (`AD-17`)
- **Couche 1 (Unitaire >= 90 %)** : tests unitaires split `remote_test_bench_and_mcp_exposure`, génération événement `ADMIN_CONNECTION_TEST` et clé de cache Redis multi-contexte.
- **Couche 2 (Intégration `testcontainers` PG18 + Redis réel)** : `create_app()` réel $\rightarrow$ exécution banc distant + `PUT /api/v1/mcp/exposure` $\rightarrow$ `SELECT` dans `audit_ledger` (`event_type = 'ADMIN_CONNECTION_TEST'`) + vérification persistance MCP après éviction cache + TTL Redis `300s`.
- **Couche 3 (Composants React)** : Vitest sur `useCatalogRemoteTestBench` & `RemoteServiceTestBenchAndMcpExposureView` prouvant l'absence de `PASS` tant que la promesse HTTP n'est pas résolue (`200`) et l'affichage `[role="alert"]` sur `502`/`422`.
- **Couche 4 (E2E Playwright ciblé)** : exécution de `18-catalog-packs-wizards-and-mcp-bench.spec.ts` (`18#5 #45`), rechargement `F5` vérifiant le maintien de l'exposition MCP.
- **Couche 5 (Statique & Sécurité)** : `ruff`, `mypy --strict`, `lint-imports`, vérification garde SSRF sur endpoints du banc distant, `pnpm turbo run lint typecheck test`, `pnpm site:check`.

---

## 3. Bilan des Modifications & Résultats

> **Statut :** `Terminé (done)` — Validé sur les 5 couches `AD-17` (Unitaires Python, Vitest `@orcia/ui` & `@orcia/web`, Intégration `testcontainers` PG18 + Redis `7.4` sur `create_app()` sans override, Couverture combinée `92 %` & Statique, Playwright E2E réel sans retry), ré-indexation GitNexus (`npx gitnexus analyze` + `gitnexus_detect_changes`) et synchronisation vitrine (`pnpm site:sync && pnpm site:check`).

| Fichier / Composant | Action Réalisée | Statut |
|---|---|---|
| `packages/orcia-core/.../orchestration/{remote_test_bench_models.py,remote_test_bench.py,governed_mcp_exposure.py,_internal/sql_mcp_exposure.py,remote_test_bench_and_mcp_exposure.py}` | Découpage `< 355` L (`137`/`256`/`351`/`310`/`258` L), garde SSRF `is_safe_llm_endpoint_url`, mode `strict_sql=True` fail-closed, persistance PG18 `mcp_exposed_agents` & hash SHA-256 `mcp_governed_pat_tokens` + miroir `catalog_items` | `Terminé` |
| `infra/migrations/versions/20261120_2403_story_24_3_mcp_exposures_and_audit_contract.py` + `infra/scripts/maintenance/_first_boot_reset_guards.py` | Révision `Expand` SQL pur `20261120_2403` (round-trip `upgrade`/`downgrade`/`upgrade` validé PG18) + purge Jour 0 dans `ORDERED_MUTABLE_TABLES_TO_CLEAR` | `Terminé` |
| `packages/orcia-core/.../audit_finops/outbox_subscriber.py` + `apps/api/.../routers/mcp_and_test_bench.py` + `apps/web/src/routes/activityFormatters.ts` | Support `ADMIN_CONNECTION_TEST` dans `AUDITABLE_EVENT_TYPES`, écriture append-only `audit_ledger`, routes `GET`/`PUT /api/v1/mcp/exposure` & `POST /api/v1/mcp/spaces/{ws}/invoke`, libellés FR/EN | `Terminé` |
| `packages/orcia-core/.../rag/{_speed2_redis_cache.py,two_speed_search.py}` + `apps/api/.../routers/portal_and_help.py` | Migration `_speed2_cache` vers Redis `7.4` (`TTL = 300s`), clé déterministe cloisonnée sur `(user_id, user_role, workspace_id, scope, active_screen_route, locale)` | `Terminé` |
| `apps/api/.../{dependencies/,routers/packs.py,schemas/}` + `packages/api-client/` | Assainissement Composition Root (`strict_sql=True` sous PG18, zéro fallback RAM silencieux), `GET /api/v1/packs/health` et régénération OpenAPI `0-diff` | `Terminé` |
| `apps/web/src/features/catalog/useCatalogRemoteTestBench.ts` + `packages/ui/.../RemoteServiceTestBenchAndMcpExposureView.tsx` + `governance_and_packs_labels.ts` | Fin du `PASS` optimiste synchrone (`isTesting`), bascule sur HTTP `200` uniquement, `[role="alert"]` sur `>= 400`, relecture `GET /api/v1/mcp/exposure` au montage (survie `F5`), libellés FR/EN | `Terminé` |
| `apps/web/src/features/settings/packs/{PacksRegistryPage.tsx,PackCardItem.tsx,usePacksRegistryHealthchecks.ts}` + `cockpit/index.tsx` + `run_lock_service.py` | Découpage `< 200` L, healthchecks réels `/api/v1/packs/health`, `handleExportPackBundleZip` (`platform`), et transmission du `wfKey` réel (`assistant-agent` inclus) dans `cockpit/index.tsx` | `Terminé` |
| `tests/{unit/test_story_24_3_mcp_bench_audit_and_redis.py,integration/test_story_24_3_mcp_audit_and_redis_postgres18.py}` + `packages/ui/src/__tests__/story-24-3-*` + `apps/web/src/__tests__/story-24-3-*` + `apps/web/e2e/18-*` | Suite complète `AD-17` 5 couches (couverture combinée `92 %`, `testcontainers` PG18 + Redis `7.4`, Vitest React sans `isJsdom`, Playwright `click()` + `toBeChecked()` sur case asynchrone) | `Terminé` |

### 3.1 Résultats des Vérifications `AD-17` & Métriques Exactes

- **Couche 1a (Unitaires Python)** : `.venv/bin/pytest tests/unit/test_story_24_3_mcp_bench_audit_and_redis.py` $\rightarrow$ **`25 passed in 10.72s`** (et `71 passed` sur l'ensemble unitaires Story 24.3 + `11_3` + `9_3` + `23_5` + `6_1` + `7_1/7_2` + `packs` + audit anti-patterns).
- **Couche 1b (React Vitest & Workspaces JS/TS)** : `pnpm turbo run lint typecheck test` $\rightarrow$ **`9 successful, 9 total`** :
  - `@orcia/api-client` : `3 passed (3)` fichiers, `20 passed (20)` tests
  - `@orcia/ui` : `32 passed (32)` fichiers, `128 passed (128)` tests (dont `story-24-3-remote-test-bench-and-mcp-exposure.test.tsx` `2/2`)
  - `@orcia/web` : `58 passed (58)` fichiers, `229 passed (229)` tests (dont `story-24-3-mcp-bench-packs-health-and-cockpit-wfkey.test.tsx` `4/4`)
- **Couche 2 (`testcontainers` PostgreSQL 18 + Redis `7.4` sur `create_app()` réel)** : `.venv/bin/pytest tests/integration/test_story_24_3_mcp_audit_and_redis_postgres18.py` $\rightarrow$ **`2 passed in 28.43s`** (round-trip Alembic `20261120_2403` $\rightarrow$ `20261120_2402` $\rightarrow$ `head`, `SELECT` SQL `audit_ledger WHERE event_type = 'ADMIN_CONNECTION_TEST'`, relecture à froid `create_app()` #2 `mcp_exposed_agents` & `catalog_items`, SHA-256 `mcp_governed_pat_tokens` sans secret en clair, `TTL <= 300s` & isolation multi-utilisateur/rôle/locale sous Redis `7.4`, purge `09_reset_db_first_boot.py` conservant `audit_ledger`).
- **Couche 3 (Couverture combinée & Statique / Sécurité)** :
  - Couverture combinée (`coverage run` + `coverage combine` Couche 1a + Couche 2 sur les `11` modules Python Story 24.3) : **`92 %`** (`770 Stmts, 47 Miss, 170 Branch, 11 BrPart` — `governed_mcp_exposure.py` `100 %`, `remote_test_bench_and_mcp_exposure.py` `100 %`, `remote_test_bench_models.py` `100 %`, `_speed2_redis_cache.py` `100 %`, `mcp_test_bench.py` `100 %`, `two_speed_search.py` `99 %`, `remote_test_bench.py` `97 %`, `mcp_and_test_bench.py` `95 %`, `sql_mcp_exposure.py` `90 %`, `packs.py` `88 %`, `outbox_subscriber.py` `74 %`).
  - `.venv/bin/ruff check .` : **`All checks passed!`**
  - `.venv/bin/ruff format --check .` : **`1308 files already formatted`**
  - `.venv/bin/mypy --strict packages/orcia-core packages/orcia-connectors apps/api apps/worker` : **`Success: no issues found in 574 source files`**
  - `.venv/bin/lint-imports` : **`Contracts: 5 kept, 0 broken`** (`617 files, 4442 dependencies`)
  - `.venv/bin/python scripts/export_openapi.py --check` : **`PASS` (`exit code 0`)**
  - `.venv/bin/pre-commit run detect-secrets --files ...` : **`Passed`** (`0` secret exposé)
- **Couche 5 (Playwright E2E réel `--project=desktop-cockpit --retries=0`)** :
  - `ORCIA_E2E_CAMPAIGN_DIR=/tmp/orcia-e2e-story-24-3 pnpm --filter @orcia/web exec playwright test e2e/03-human-led-anchor-and-arbitration.spec.ts e2e/19-orchestration-whatif-replay-and-gates.spec.ts e2e/18-catalog-packs-wizards-and-mcp-bench.spec.ts --grep-invert "Explorateur du catalogue fédéré" --project=desktop-cockpit --retries=0` $\rightarrow$ **`7 passed (2.1m)`** (`0 failed` : `03`, `19#1`, `19#2`, `18#2`, `18#3`, `18#4`, **`18#5 #45`** avec `reloadColdFromPg` + SQL `audit_ledger` `ADMIN_CONNECTION_TEST` + `catalog_items` ; `18#1` isolé uniquement sur `openCatalogOrAgentsPage` planifié en Story `24.7`).
- **GitNexus** : `npx gitnexus analyze` (`40,785 nodes | 167,662 edges | 697 clusters | 1492 flows`) + `gitnexus_detect_changes(repo="/home/romain/Documents/Projects/ORCIA", scope="all")` $\rightarrow$ `changed_count: 21`, `affected_count: 1492`, `changed_files: 32`, `risk_level: "critical"`.
