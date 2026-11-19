# Story 22.8a — Assainissement Fail-Closed de `vitest.setup.ts` Validé sur OpenAPI, Audit Composition Root Sans Override / Zéro Silo RAM & Pipeline CI GitHub Actions Complet 5 Couches

> **Convention de nommage du fichier (Obligatoire — à créer AVANT toute modification de code)** :
> - User Story du sprint : `docs/implementation-artifacts/tech-lead-reports/{story-key}-tech-lead-report.md`

- **Date** : `2026-11-18`
- **Story / Clé Sprint** : `22-8a-assainissement-fail-closed-vitest-composition-root-sans-override-et-ci-complete` (`Epic 22` — Vague 3 / Clôture Architecture de Tests & CI)
- **Capacité(s)** : `CAP-100` (hygiène — éradication structurelle des faux positifs Vitest, Couche 2 et CI, sans nouvelle entrée `CAP-*`) — classification : `hygiène`
- **Auteur / Contexte** : Tech Lead (`Amelia`) & Architecte (`Winston`) — Story intercalaire issue de l'analyse des causes racines (`RC-1`, `RC-2`, `RC-7`) de l'Epic 21 (`2026-11-18-rca-epic-21-enrichissement-22-8-et-story-22-8a-tech-lead-report.md`). Ordonnancée après `Story 22.8` et avant `Story 22.9` (`AD-1`, `AD-17`, `AD-19`, `NFR-TEST-1`).
- **Commits associés** : `En attente d'implémentation (planifié en Vague 3 après Story 22.8)`

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
  - `initialize_app_services` (`apps/api/src/orcia_api/dependencies/core_and_lifespan.py`) : `impactedCount: 237`, risque **`CRITICAL`** (`direct: 24`, `d=2: 122`, `d=3: 91`, `processes_affected: 167`, `modules_affected: 9`).
  - `create_app` (`apps/api/src/orcia_api/main.py`) : `impactedCount: 4`, risque **`LOW`** (`direct: 1`).
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

> *[En attente d'implémentation de la Story 22.8a]*

### 3.1 Fichiers Développés & Modifiés
| Fichier | Nature (Création / Modification / Refactoring) | Description synthétique |
| :--- | :--- | :--- |
| `apps/web/src/__tests__/vitest.setup.ts` & `apps/web/src/__tests__/setup/*.ts` | Refactoring (`< 350` L) | *[À compléter après implémentation]* |
| `apps/web/src/__tests__/vitest-transport-fail-closed-openapi.test.ts` | Création | *[À compléter après implémentation]* |
| `tests/integration/test_composition_root_zero_ram_silo_postgres18.py` | Création | *[À compléter après implémentation]* |
| `tests/unit/test_integration_no_manual_app_state_audit.py` & `test_zero_orphan_sql_adapters_audit.py` | Création | *[À compléter après implémentation]* |
| `.github/workflows/ci.yml` & `.github/workflows/e2e.yml` | Création / Modification | *[À compléter après implémentation]* |

### 3.2 Résultats Chiffrés, Métriques & Qualité
- **Couverture combinée `packages/orcia-core`** : *[$\ge 90\%$ combiné Unit + Intégration requis]*
- **Volumétrie `apps/web/src/__tests__/setup/*.ts`** : *[Tous fichiers `< 350` L]*
- **Qualité statique & CI** : `ruff`, `mypy --strict`, `pnpm turbo run lint typecheck test`, `lint-imports`, `lint_spine.py`, `pnpm site:check` *[À compléter]*

### 3.3 Validation & Procédure de Test sur Toute la Pyramide (`AD-17`)
- *[À compléter après implémentation de la Story 22.8a]*
