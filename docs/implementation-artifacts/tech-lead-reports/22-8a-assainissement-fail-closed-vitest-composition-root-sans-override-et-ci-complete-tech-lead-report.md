# Story 22.8a — Assainissement Fail-Closed de `vitest.setup.ts` Validé sur OpenAPI, Audit Composition Root Sans Override / Zéro Silo RAM & Pipeline CI GitHub Actions Complet 5 Couches

> **Convention de nommage du fichier (Obligatoire — à créer AVANT toute modification de code)** :
> - User Story du sprint : `docs/implementation-artifacts/tech-lead-reports/{story-key}-tech-lead-report.md`

- **Date** : `2026-11-19`
- **Story / Clé Sprint** : `22-8a-assainissement-fail-closed-vitest-composition-root-sans-override-et-ci-complete` (`Epic 22` — Vague 3 / Clôture Architecture de Tests & CI)
- **Capacité(s)** : `CAP-100` (hygiène — éradication structurelle des faux positifs Vitest, Couche 2 et CI, sans nouvelle entrée `CAP-*`) — classification : `hygiène`
- **Auteur / Contexte** : Tech Lead (`Amelia`) & Architecte (`Winston`) — Story intercalaire issue de l'analyse des causes racines (`RC-1`, `RC-2`, `RC-7`) de l'Epic 21 (`2026-11-18-rca-epic-21-enrichissement-22-8-et-story-22-8a-tech-lead-report.md`). Ordonnancée après `Story 22.8` et avant `Story 22.9` (`AD-1`, `AD-17`, `AD-19`, `NFR-TEST-1`).
- **Commits associés** : `feat/epic-22-remediation-pg18-direction-c` (commit Story `22.8a`)

---

## 1. Analyse du Besoin & Étude d'Impact Tech Lead (Pré-Implémentation)

### 1.1 Contexte & Problématique
- **Volet 1 — Faux positifs de `vitest.setup.ts` (`2 951` lignes, mode *Fail-Open*)** :
  - `apps/web/src/__tests__/vitest.setup.ts` remplace `globalThis.fetch` par `vitestFetchTransport` (`L2951`) avec un `backendState` permissif qui acceptait `"ws-1"`, ignorait la validation stricte `extra="forbid"` de Pydantic et répondait `return jsonResponse({})` (`L2948`) pour toute URL non gérée. Ce fichier dépasse largement le seuil de `300–400` lignes (`GEMINI.md`) et a masqué dès la Couche 1b les `404`/`422`/`403` observés ensuite en E2E.
- **Volet 2 — Contournement du Composition Root en Couche 2 & dual-mode RAM/SQL** :
  - Plusieurs tests d'intégration PostgreSQL 18 instancient directement `Sql*Repository` sans `create_app()`, et `tests/integration/test_epics_1_7_vertical_sql_wiring_postgres18.py:L138-L145` injectait manuellement `app.state.dbos_uow = uow` avec `dependency_overrides`, masquant que `core_and_lifespan.py` laissait `dbos_uow = None`.
  - Plusieurs constructeurs de services dans `packages/orcia-core` toléraient encore un repli implicite `session_factory=None -> dict RAM`, et la règle « Zéro Adaptateur SQL Orphelin » restait manuelle.
- **Volet 3 — CI GitHub Actions partielle & couverture fragmentée** :
  - Le dépôt ne contient que `.github/workflows/e2e.yml` (lancé tardivement le `2026-11-08` et limité à `pnpm e2e`), sans workflow exécutant `ruff`, `mypy --strict`, `lint-imports`, `lint_spine.py`, `export_openapi.py --check`, `pnpm turbo run lint typecheck test`, `pnpm site:check`, les suites Python (`unit`, `integration`, `contract`, `evals`, `security`) avec couverture globale `--cov=packages/orcia-core --cov-fail-under=90` combinée, ni de sharding Playwright (`--retries=0`).

### 1.2 Exploration, Analyse d'Impact GitNexus, Factorisation & Dette Technique
- **Analyse d'Impact GitNexus (`repo: "ORCIA"`, `direction: "upstream"`)** :
  - `initialize_app_services` (`apps/api/src/orcia_api/dependencies/core_and_lifespan.py`) : `impactedCount: 240`, risque **`CRITICAL`** (`direct: 25`, `d=2: 122`, `d=3: 93`, `processes_affected: 168`, `modules_affected: 9`).
  - `create_app` (`apps/api/src/orcia_api/main.py`) : `impactedCount: 4`, risque **`LOW`** (`direct: 1`).
  - `StartReflexiveExecutionRequest` (`apps/api/src/orcia_api/schemas/reflexive_execution.py`) : `impactedCount: 5`, risque **`LOW`** (`direct: 2`, `d=2: 1`, `d=3: 2`).
- **Factorisation & contrôle de volumétrie (`< 350` L)** :
  - Découpage de `apps/web/src/__tests__/vitest.setup.ts` (`2 951` L) en sous-modules spécialisés par domaine sous `apps/web/src/__tests__/setup/` (`< 350` L chacun) partageant un validateur unique contre `packages/api-client/openapi.json`.
  - Suppression complète des replis `session_factory=None` dans `packages/orcia-core` au profit de ports `RepositoryPort` obligatoires (`tests/unit/fakes/` réservé aux tests unitaires).

---

## 2. Plan d'Implémentation

### 2.1 Schéma de Données & Migrations Alembic (`infra/migrations/versions/`)
- Aucune nouvelle table requise ; vérification complète de la chaîne Alembic dans le job `python-integration-pg18` en CI.

### 2.2 Noyau Métier Hexagonal, Audits AST & Composition Root (`packages/orcia-core/`, `tests/`)
- **Suppression du dual-mode RAM/SQL dans `packages/orcia-core`** : exiger un adaptateur/port explicite dans les services persistés (zéro `dict` RAM de repli en production ; fakes uniquement sous `tests/unit/fakes/`).
- **Test d'intégration du Composition Root sans override** (`tests/integration/test_composition_root_zero_ram_silo_postgres18.py`) :
  - Démarre `create_app()` sur de vrais conteneurs PostgreSQL 18 + Redis **sans aucun `app.dependency_overrides` ni assignation manuelle sur `app.state`**.
  - Vérifie que `app.state.db_engine`, `app.state.session_maker`, `app.state.dbos_uow` sont initialisés et non-`None`, résout chaque dépendance `Depends(get_*_service)` des routeurs et vérifie qu'aucun service injecté ne possède de stockage métier RAM sans repository SQL.
- **Nettoyage Couche 2 & audits AST** :
  - Supprimer l'injection manuelle `app.state.dbos_uow = uow` dans `tests/integration/test_epics_1_7_vertical_sql_wiring_postgres18.py` et utiliser le Composition Root réel.
  - Créer `tests/unit/test_integration_no_manual_app_state_audit.py` interdisant d'écrire sur `app.state.*` ou `dependency_overrides` dans les tests d'intégration HTTP verticaux (hors fakes LLM `0 $`).
  - Créer `tests/unit/test_zero_orphan_sql_adapters_audit.py` vérifiant par AST que chaque module `_internal/sql_*.py` est branché dans `apps/api/src/orcia_api/dependencies/` ou `apps/worker/`, sans repli `if uow is None: return None`.

### 2.3 Couche Backend API, Contrats & Transport Vitest *Fail-Closed* (`apps/web/src/__tests__/`)
- **Découpage `< 350` L et durcissement de `vitest.setup.ts`** :
  - Scinder `apps/web/src/__tests__/vitest.setup.ts` (`2 951` L) en modules `< 350` L sous `apps/web/src/__tests__/setup/` (`transportAndOpenApiValidator.ts`, `authAndOrgMockHandlers.ts`, `workspacesAndCatalogMockHandlers.ts`, `assistantAndProcessMockHandlers.ts`, etc.).
  - Supprimer `return jsonResponse({})` (`L2948`) pour passer `vitestFetchTransport` en mode **Fail-Closed** (`throw new Error(...)` sur toute route non gérée explicitement).
  - Valider chaque requête traversant `vitestFetchTransport` contre `packages/api-client/openapi.json` : existence du chemin/méthode, conformité UUID stricte de tout paramètre `format: "uuid"` (bloquant `"ws-1"` en `< 1 s`), et validation `required` / `additionalProperties: false` sur le payload JSON.
  - Créer `apps/web/src/__tests__/vitest-transport-fail-closed-openapi.test.ts` prouvant le rejet immédiat d'une route inconnue, d'un UUID invalide (`"ws-1"`) et d'un champ non déclaré.

### 2.4 Pipeline CI GitHub Actions Complet 5 Couches (`.github/workflows/`)
- Créer `.github/workflows/ci.yml` et aligner `.github/workflows/e2e.yml` sur 4 jobs bloquants :
  1. `static-and-contracts` (`< 2 min`) : `ruff check .`, `ruff format --check .`, `mypy --strict`, `lint-imports`, `lint_spine.py`, `export_openapi.py --check`, `check_implementation_docs.py`, `pnpm turbo run lint typecheck test`, `pnpm site:check`.
  2. `python-unit-evals-security` : `pytest tests/unit tests/contract tests/conformance tests/evals tests/security --cov=packages/orcia-core --cov-report=xml`.
  3. `python-integration-pg18` : `pytest tests/integration --cov=packages/orcia-core --cov-append --cov-report=xml` puis `coverage combine` + `coverage report --fail-under=90` sur **l'intégralité de `packages/orcia-core`** (incluant `sql_*.py`).
  4. `playwright-e2e-sharded` : exécution shardée (`matrix.shard: [1/4 .. 4/4]`, `--retries=0 --max-failures=0 --timeout=35000`), fusion des résultats JSON et contrôle final via `pnpm site:check` + archivage des captures PNG en artefact CI.

### 2.5 Analyse d'Impact sur la Pyramide des Tests (`AD-17` — Couches 1 à 5 + Sécurité)
- **Couche 1a (`pytest`)** : `test_integration_no_manual_app_state_audit.py`, `test_zero_orphan_sql_adapters_audit.py` + seuil global combiné `>= 90 %`.
- **Couche 1b (`Vitest`)** : `vitest-transport-fail-closed-openapi.test.ts` et passage au vert de l'ensemble de `@orcia/web` (`39+` fichiers) sous transport *Fail-Closed* validé OpenAPI.
- **Couche 2 (`testcontainers` PG18 + Redis)** : `test_composition_root_zero_ram_silo_postgres18.py` sans override ni contournement.
- **Couche 3 & Gouvernance CI** : validation syntaxique/structurelle des workflows `.github/workflows/{ci,e2e}.yml` et `pnpm site:check`.
- **Couche 5 (Playwright E2E)** : préparation de l'exécution shardée `--retries=0` avant `Story 22.9`.

---

## 3. Bilan des Modifications & Résultats (Post-Implémentation)

### 3.1 Fichiers Développés & Modifiés
| Fichier | Nature (Création / Modification / Refactoring) | Description synthétique |
| :--- | :--- | :--- |
| `apps/web/src/__tests__/vitest.setup.ts` & `apps/web/src/__tests__/setup/*.ts` (`13` modules `< 350` L) | Refactoring (`2 951 -> 48` L) | Découpage modulaire par domaine (`aiModelsAndToolsMockHandlers.ts`, `assistantAndInboxMockHandlers.ts`, `authAndBootstrapMockHandlers.ts`, `autonomyTriggersAndWorkflowsV2Handlers.ts`, `finopsAndGatesMockHandlers.ts`, `mockBackendState.ts`, `openApiRequestValidator.ts`, `orchestrationRunsMockHandlers.ts`, `orgUnitsMutationsHandlers.ts`, `orgUnitsReadAndInviteHandlers.ts`, `orgUnitsScopeHelpers.ts`, `transportAndOpenApiValidator.ts`, `workspacesAndCatalogMockHandlers.ts`) + mode *Fail-Closed* validé contre `packages/api-client/openapi.json`. |
| `apps/web/src/__tests__/vitest-transport-fail-closed-openapi.test.ts` & `zero-dead-buttons-and-silent-catches-audit.test.tsx` | Création / Modification | Prouve en `5/5` tests le rejet immédiat d'une route inexistante, d'un identifiant non-UUID (`"ws-1"`) sur `format: "uuid"`, d'un champ `required` manquant et d'un champ non déclaré sur `additionalProperties: false` (`SecretInputPayload`), sans aucun `return jsonResponse({})`. |
| `packages/orcia-core/src/orcia_core/**` & `apps/api/src/orcia_api/**` | Modification | Suppression des replis RAM implicites (`sql_reflexive_sessions.py`, `cognitive_impact_service.py`, `sql_user_preferences.py`, `sql_workflows_v2.py`), durcissement Composition Root (`core_and_lifespan.py`, `orchestration_and_settings.py`, `reflexive_execution.py`) et schéma `reflexive_execution.py` + `openapi.json` `0-diff`. |
| `tests/integration/test_composition_root_zero_ram_silo_postgres18.py` | Création | Démarre `create_app()` via `app.router.lifespan_context(app)` contre PG18 + Redis 7.4 `testcontainers` sans `dependency_overrides` ni écriture `app.state.*`, vérifie `db_engine`/`session_maker`/`dbos_uow`, exécute les 8 flux critiques (`workspaces`, `assistant_folders`, `task_notifications`, `gate_evaluations`, `declarative_pack_bundles`, `wizard_sessions`, `permission_broker_tickets`, `catalog_items`), contrôle par `SELECT` PG18 et revalide après redémarrage à froid sur `app2`. |
| `tests/unit/test_integration_no_manual_app_state_audit.py` & `tests/unit/test_zero_orphan_sql_adapters_audit.py` | Création | Audits AST prouvant l'absence de mutation `app.state.*` (hors `http_client`/`otp_email_sink` `0 $`) et `dependency_overrides` dans `tests/integration/**/*.py`, ainsi que le câblage effectif de `100 %` des `78` adaptateurs SQL `_internal/{sql_,_sql_}*.py` dans `apps/api` / `apps/worker` (`0` orphelin). |
| `tests/integration/test_epics_1_7_vertical_sql_wiring_postgres18.py`, `tests/integration/api/test_story_*.py`, `tests/integration/test_http_vertical_day0_and_agents_postgres18.py`, `tests/integration/test_real_containers.py` | Modification | Suppression des contournements `app.state.*` en Couche 2, création explicite du workspace PG18 avant création de dossier assistant et alignement du compteur de seeds `PermissionBroker` (`10` politiques incluant les `4` fallbacks de `Story 22.3`). |
| `.github/workflows/ci.yml` & `.github/workflows/e2e.yml` | Création / Modification | Pipeline CI GitHub Actions complet à `4` jobs bloquants (`static-and-contracts`, `python-unit-evals-security`, `python-integration-pg18` avec `coverage combine` `>= 90 %`, `playwright-e2e-sharded` `4` shards `--retries=0 --timeout=35000` + `pnpm site:check`). |

### 3.2 Résultats Chiffrés, Métriques & Qualité
- **Couverture combinée `packages/orcia-core`** : **`92.34 %`** (`23 410` instructions, `1 211` manquées ; `5 302` branches, `796` partielles ; `132` fichiers à `100 %` — Pass 1 `unit+contract+conformance+evals+security` combiné à Pass 2 `tests/integration`, seuil `--cov-fail-under=90` atteint).
- **Volumétrie `apps/web/src/__tests__/setup/*.ts`** : `vitest.setup.ts` réduit à **`48`** lignes ; les **`13`** modules sous `apps/web/src/__tests__/setup/` font tous **`<= 346`** lignes (`86` à `346` L, tous `< 350` L).
- **Qualité statique & CI** :
  - `.venv/bin/ruff check . && .venv/bin/ruff format --check .` : **PASS** (`0` erreur, `1 238` fichiers formatés).
  - `.venv/bin/mypy --strict packages/orcia-core apps/api apps/worker` (+ nouveaux tests AST/intégration) : **PASS** (`Success: no issues found in 516 source files`).
  - `.venv/bin/lint-imports` : **PASS** (`Contracts: 5 kept, 0 broken`, `596` fichiers analysés).
  - `.venv/bin/python scripts/export_openapi.py --check` : **PASS** (`0-diff`).
  - `.venv/bin/python .agent/skills/bmad-architecture/scripts/lint_spine.py --workspace docs/planning-artifacts/architecture/architecture-ORCIA-2026-10-24` : **PASS** (`0 findings`).
  - `pnpm turbo run lint typecheck test --force` : **PASS** (`9/9` tâches réussies en `47.539 s` : `@orcia/api-client` `2` fichiers / `13` tests, `@orcia/ui` `26` fichiers / `110` tests, `@orcia/web` `51` fichiers / `190` tests incluant `vitest-transport-fail-closed-openapi.test.ts` `5/5`, soit `313/313` tests JS/TS).
  - `pnpm site:sync && pnpm site:check` + `scripts/check_implementation_docs.py` : **PASS**.

### 3.3 Validation & Procédure de Test sur Toute la Pyramide (`AD-17`)
- **Couche 1a (`pytest` unitaires & audits AST)** :
  - `tests/unit/test_integration_no_manual_app_state_audit.py` + `tests/unit/test_zero_orphan_sql_adapters_audit.py` : **`3/3` passed** (`78/78` adaptateurs SQL câblés, `0` override/tampering `app.state.*`).
  - Suites combinées Pass 1a (`356` passed) + Pass 1b (`402` passed) + Pass 1c (`contract` + `conformance` + `evals` + `security`, `137` passed) : **`895/895` passed**.
- **Couche 1b (`Vitest` *Fail-Closed* OpenAPI)** : **`313/313` tests JS/TS passed** (`@orcia/web` `190/190` dont `5/5` dans `vitest-transport-fail-closed-openapi.test.ts`).
- **Couche 2 (`testcontainers` PG18 + Redis)** :
  - `tests/integration/test_composition_root_zero_ram_silo_postgres18.py` : **`1/1` passed** (`create_app()` réel via lifespan sans override, `8/8` tables vérifiées par `SELECT` PG18 + redémarrage à froid `app2`).
  - Intégralité de `tests/integration/api/` (**`49/49` passed**) + `tests/integration/test_*.py` (**`31/31` passed**) : **`80/80` passed** (`975/975` tests Python sur toute la pyramide, couverture combinée **`92.34 %`**).
- **Couches 3 & 4 (Contrats OpenAPI / Evals / Sécurité)** : inclus dans Pass 1c (**`137/137` passed**, `Schemathesis` + `0-diff` + gardes RBAC/Observer).
- **Couche 5 (Playwright E2E CI)** : workflows `.github/workflows/{ci,e2e}.yml` alignés sur le sharding `4` shards (`--retries=0 --max-failures=0 --timeout=35000`), la fusion JSON et `pnpm site:check` en vue de la campagne intégrale `Story 22.9`.
- **GitNexus (`gitnexus_detect_changes({scope: "all"})`)** : index rafraîchi (`36 947` nœuds, `66 114` arêtes, `1 725` flux) — `18` symboles modifiés, `23` flux affectés sur `24` fichiers, niveau de risque `critical` lié au Composition Root (`initialize_app_services`) et entièrement couvert par les tests `testcontainers` PG18.
