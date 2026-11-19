# Story 22.5 — Persistance PG18 Packs Déclaratifs (`declarative_pack_bundles`) & Parcours Wizards Durables (`wizard_sessions`)

> **Convention de nommage du fichier (Obligatoire — à créer AVANT toute modification de code)** :
> - User Story du sprint : `docs/implementation-artifacts/tech-lead-reports/{story-key}-tech-lead-report.md`

- **Date** : 2026-11-18
- **Story / Clé Sprint** : `22-5-persistance-pg18-packs-declaratifs-et-wizards-durables` (`Epic 22` — Vague 1)
- **Capacité(s)** : `CAP-055`, `CAP-056`, `CAP-057`, `CAP-150` (ancrages `failed_e2e` sur `22-5`) — classification : `feature`
- **Auteur / Contexte** : `bmad-architect-worker` (initialisation pré-implémentation Story 21.9) — Résolution des chantiers **`REM-14`** et **`REM-15`** (`synthese-remediation-sally-winston-epic-21.md`). Couvre `FR-11`, `FR-13`, `FR-14`, `FR-28`, `FR-31`, `FR-34`, `FR-35`, `AD-1`, `AD-2`, `AD-16`, `AD-20`, `NFR-REL-1`, `UJ-19`.
- **Commits associés** : `En attente d'implémentation (initialisé sur 575cf4a)`

---

## 1. Analyse du Besoin & Étude d'Impact Tech Lead (Pré-Implémentation)

### 1.1 Contexte & Problématique
- **Silo RAM `declarative_pack_bundles` (`REM-14`, `2` échecs)** :
  - `routers/packs.py:38-43` et `core_and_lifespan.py:291-294` chargent les manifests YAML depuis `packs/<domaine>/` dans la liste en mémoire `app.state.declarative_pack_bundles` **sans jamais synchroniser ni écrire en PostgreSQL 18**. Lors du test `18-catalog` #3, la table `declarative_pack_bundles` compte `0` ligne.
- **Double silo RAM sur `/wizards` & défauts d'ergonomie (`REM-15`, `2` échecs)** :
  - Côté frontend, `apps/web/src/routes/wizards.tsx:52-103` (`WizardsRouteComponent`) conserve `currentStep` et `status` en pur `useState` React sans jamais invoquer `@orcia/api-client` (`GET`/`POST` `/api/v1/wizards`). Au rafraîchissement `F5`, l'état est perdu et `wizard-completed-badge` n'apparaît pas.
  - Côté backend, `core_and_lifespan.py:291-294` instancie `DurableOnboardingWizardService()` sans `AsyncEngine`, laissant `wizard_sessions` vide en base PG18.
  - Visuellement (constat Sally sur `18-catalog` #4), l'écran `/wizards` affiche l'identifiant brut `sdlc_tech_lead · Étape 1/5`, une triple numérotation redondante `1. #1/5 1. Organisation & Équipe`, et pousse le formulaire de l'étape active sous la ligne de flottaison.
- **Échecs E2E associés & captures PNG archivées (`4` échecs E2E)** :
  - `18-catalog-packs-wizards-and-mcp-bench.spec.ts` #3 (`declarative_pack_bundles`, Desktop + Mobile ×2) : [Desktop Packs](../e2e-campaign-epic-21/screenshots/18-catalog-packs-wizards-and-mcp-bench/desktop-cockpit--registre-des-packs-declaratifs-et-export-zip-persistent-dans-declarative-pack-bundles-ap--failed.png) · [Mobile Packs](../e2e-campaign-epic-21/screenshots/18-catalog-packs-wizards-and-mcp-bench/mobile-companion--registre-des-packs-declaratifs-et-export-zip-persistent-dans-declarative-pack-bundles-ap--failed.png)
  - `18-catalog-packs-wizards-and-mcp-bench.spec.ts` #4 (`wizard_sessions` / `wizard-completed-badge`, Desktop + Mobile ×2) : [Desktop Wizards](../e2e-campaign-epic-21/screenshots/18-catalog-packs-wizards-and-mcp-bench/desktop-cockpit--parcours-guide-d-initialisation-avec-retour-arriere-survit-a-f5-et-persiste-dans-wizard---failed.png) · [Mobile Wizards](../e2e-campaign-epic-21/screenshots/18-catalog-packs-wizards-and-mcp-bench/mobile-companion--parcours-guide-d-initialisation-avec-retour-arriere-survit-a-f5-et-persiste-dans-wizard---failed.png)

### 1.2 Exploration, Analyse d'Impact GitNexus, Factorisation & Dette Technique
- **Analyse d'Impact GitNexus (`repo: "/home/romain/Documents/Projects/ORCIA"`)** :
  - `DurableOnboardingWizardService` (`packages/orcia-core/src/orcia_core/bootstrap/durable_wizards.py`) : **`impactedCount: 1`** (`direct: 1` — `bootstrap/__init__.py`), risque **`LOW`**, `epistemic: exact`.
  - `load_declarative_pack_bundles` (`apps/api/src/orcia_api/routers/packs.py:38`) : **`impactedCount: 12`** (`direct: 4` — `_workflows_helpers.py` & `packs.py` ; `d=2: 8` — `workflows.py`), risque **`LOW`**, `epistemic: exact`.
  - `DurableWizardRunnerView` (`packages/ui/src/primitives/DurableWizardRunnerView.tsx`) : **`impactedCount: 3`** (`direct: 1` — `WizardsRouteComponent` dans `apps/web/src/routes/wizards.tsx`), risque **`LOW`**, `epistemic: exact`.
- **Tables PostgreSQL 18 concernées** : `declarative_pack_bundles` (`20261108_0910_declarative_packs_and_workflows_v2.py`), `wizard_sessions` (`0022`).
- **Opportunités de Factorisation & Volumétrie** :
  - Réutiliser le patron d'upsert idempotent (`INSERT ... ON CONFLICT DO UPDATE`) de `bootstrap/seeder.py` pour synchroniser `packs/*/pack.yaml` dans `declarative_pack_bundles` au démarrage de FastAPI et lors de `GET /api/v1/packs` + `POST /api/v1/packs/export/{workspace_id}` (`packs.py`), tout en câblant `PacksRegistryPage.tsx` sur `@orcia/api-client`.
  - Factoriser la résolution d'acteur JWT/PG18 (`_resolve_wizard_actor` avec `rehydrate_bearer_subject_from_pg_if_missing`) et le port hexagonal `WizardSessionRepositoryPort` (sans SQLAlchemy dans `durable_wizards.py`, `AD-19`) + `WizardsStepForm.tsx` (`< 350` L sur `routes/wizards.tsx`).
  - Factoriser les libellés métier des profils de wizard (`sdlc_tech_lead`, `ops_manager`, `secops_admin`) et `stepCounterConnector` dans `apps/web/src/i18n/locales/admin_and_studio_labels.ts` (FR/EN).

---

## 2. Plan d'Implémentation

### 2.1 Schéma de Données & Migrations Alembic (`infra/migrations/versions/`)
- Les tables `declarative_pack_bundles` (`20261108_0910`) et `wizard_sessions` (`0022`) existent déjà. Aucune migration destructive requise ; vérifier uniquement l'index/clé unique (`pack_id` / `version`) permettant l'upsert idempotent des bundles et `session_id` / `wizard_key` sur `wizard_sessions`.

### 2.2 Noyau Métier Hexagonal, Orchestration & Workers (`packages/orcia-core/`, `apps/worker/`)
- **`declarative_pack_bundles` (`REM-14`)** :
  - Créer `packages/orcia-core/src/orcia_core/bootstrap/_internal/sql_declarative_packs.py` (ou dans `catalog/_internal/`) exposant `upsert_declarative_pack_bundles_sql(engine, bundles)` et `list_declarative_pack_bundles_sql(engine)` avec empreinte `SHA-256`.
- **`DurableOnboardingWizardService` (`REM-15`)** :
  - Créer `packages/orcia-core/src/orcia_core/bootstrap/_internal/sql_wizard_sessions.py` (`SqlWizardSessionRepository`) implémentant `start_or_resume_wizard`, `get_session`, `save_step_and_advance` (avec `step_back` préservant les saisies et transition `COMPLETED`).
  - Injecter ce repository dans `DurableOnboardingWizardService` sans importer SQLAlchemy dans `durable_wizards.py` (`AD-19`).

### 2.3 Couche Backend API, Sécurité & Contrats (`apps/api/`, `packages/api-client/`)
- `apps/api/src/orcia_api/dependencies/core_and_lifespan.py` :
  - Synchroniser idempotemment les manifests chargés de `packs/` dans `declarative_pack_bundles` au lifespan (sans `ORCIA_DISABLE_PG_BOOTSTRAP_SYNC`).
  - Instancier `DurableOnboardingWizardService` avec son repository SQLAlchemy Asyncio sur PG18.
- `apps/api/src/orcia_api/routers/packs.py` : lire/écrire dans `declarative_pack_bundles` lors de la liste, publication et export ZIP (`GET`/`POST` `/api/v1/packs*`).
- `apps/api/src/orcia_api/routers/studio_and_wizards.py` : vérifier que `GET /api/v1/wizards`, `POST /api/v1/wizards/{type}/start`, `POST /api/v1/wizards/{id}/step` (avancer/reculer) retournent l'état persisté PG18 avec contrôle observateur `403`.
- Régénérer `@orcia/api-client` (`0-diff`) si des champs de réponse sont ajustés.

### 2.4 Interface Utilisateur & Expérience (`packages/ui/`, `apps/web/`)
- `apps/web/src/routes/wizards.tsx` :
  - Supprimer le `useState` éphémère de progression ; charger l'état initial via `@orcia/api-client` (`GET /api/v1/wizards`) au montage et persister chaque avancée/retour arrière par `POST` API, afin que `page.reload()` (`F5`) réaffiche exactement l'étape courante ou `wizard-completed-badge`.
- `DurableWizardRunnerView` (`packages/ui`) :
  - Remplacer `sdlc_tech_lead` par son libellé métier traduit (`i18n`).
  - Supprimer la triple numérotation `1. #1/5 1.` au profit d'un indicateur unique sobre (`Étape 1 sur 5`).
  - Remonter l'étape active et son formulaire au-dessus de la ligne de flottaison (`order`/layout compact).

### 2.5 Analyse d'Impact sur la Pyramide des Tests (`AD-17` — Couches 1 à 5 + Sécurité, Obligatoire)
- **Couche 1a / 1b** : tests unitaires de `DurableOnboardingWizardService` (retour arrière sans perte, completion), tests Vitest `wizards.tsx` avec `unmount()` + `render()` prouvant la survie au `F5` sans `useState` local.
- **Couche 2 (`HTTP ➔ PG18`)** : bootstrap/export packs $\rightarrow$ `SELECT COUNT(*) FROM declarative_pack_bundles >= 1` ; parcours wizard `POST` + `step_back` + `complete` $\rightarrow$ `SELECT status, current_step FROM wizard_sessions`.
- **Couche 3 (`OpenAPI 0-diff`, `lint-imports`)** : validation `5 contracts kept, 0 broken`.
- **Couche Sécurité** : rejet `403 ERR_OBSERVER_MODE_READ_ONLY` sur mutations `/api/v1/packs` et `/api/v1/wizards/*`.
- **Couche 5 (Playwright E2E)** : passage au vert visé de `18-catalog` #3 et #4 (Desktop & Mobile, `F5` + `SELECT` PG18).

---

## 3. Bilan des Modifications & Résultats (Post-Implémentation)

### 3.1 Fichiers Développés & Modifiés
| Fichier | Nature (Création / Modification / Refactoring) | Description synthétique |
| :--- | :--- | :--- |
| `packages/orcia-core/src/orcia_core/bootstrap/_internal/sql_declarative_packs.py` & `__init__.py` | Création / Modification | Adaptateur SQL asynchrone PG18 `upsert_declarative_pack_bundles_sql`, `list_declarative_pack_bundles_sql` & `get_declarative_pack_bundle_sql` avec empreinte `SHA-256` et manifest JSONB sans dépendance croisée `orcia_core.packs`. |
| `packages/orcia-core/src/orcia_core/bootstrap/_internal/sql_wizard_sessions.py` | Création | `SqlWizardSessionRepository` PG18 (`WizardSessionRepositoryPort`) pour `start_or_resume_wizard_async`, `get_session_async`, `list_sessions_for_user_async`, `save_step_and_advance_async` & `update_session_state_async`. |
| `packages/orcia-core/src/orcia_core/bootstrap/durable_wizards.py` | Modification | Port hexagonal `WizardSessionRepositoryPort`, méthodes `*_async`, non-destructivité du `step_back` (conservation des saisies antérieures), transition `COMPLETED` + `rag_reciprocity_verified`. |
| `packages/orcia-core/src/orcia_core/packs/loader.py` | Modification | Correction `resolve_default_packs_root()` pour cibler le répertoire monorepo `packs/` contenant `*/pack.yaml` plutôt que le sous-package Python `orcia_core/packs`. |
| `apps/api/src/orcia_api/dependencies/core_and_lifespan.py` & `orchestration_and_settings.py` | Modification | Synchronisation des packs déclaratifs dans `declarative_pack_bundles` au lifespan (sans `ORCIA_DISABLE_PG_BOOTSTRAP_SYNC`) et câblage de `DurableOnboardingWizardService` avec `SqlWizardSessionRepository(db_engine)`. |
| `apps/api/src/orcia_api/routers/packs.py`, `studio_and_wizards.py` & `schemas/settings_and_studio.py` | Modification | Synchronisation PG18 sur `GET /api/v1/packs` & `POST /api/v1/packs/export/{workspace_id}` via `is_pg_runtime_active`, nouveaux endpoints `GET /api/v1/wizards`, `GET /api/v1/wizards/sessions/{id}`, `POST /api/v1/wizards/sessions/{id}/step-back` avec `enforce_not_observer_mode` (`403`). |
| `packages/api-client/openapi.json`, `src/generated/*`, `src/domains/{bootstrapAndOntology,workflowsV2}.ts`, `src/helpers.ts`, `src/index.ts` | Modification / Régénération | SDK OpenAPI 3.1 régénéré (`0-diff`) avec `listDeclarativePacks`, `exportWorkspacePackZip` (`createRequestBinary`), `listWizardSessions`, `getWizardSession` et `stepBackWizard`. |
| `packages/ui/src/primitives/DurableWizardRunnerView.tsx` | Modification | Affichage du libellé métier traduit (`profileLabels`), indicateur unique `Étape N sur 5`, bouton `wizard-step-back-btn` et placement du panneau actif au-dessus de la ligne de flottaison. |
| `apps/web/src/i18n/locales/admin_and_studio_labels.ts`, `apps/web/src/features/settings/packs/PacksRegistryPage.tsx`, `apps/web/src/features/bootstrap/WizardsStepForm.tsx` & `apps/web/src/routes/wizards.tsx` | Création / Modification | Câblage `@orcia/api-client` sur `/settings/packs` et `/wizards`, suppression du `useState` éphémère de progression, bannières d'erreur `[role="alert"]` RFC 9457 et extraction `WizardsStepForm.tsx` (`< 350` L). |
| `tests/unit/test_declarative_packs_and_durable_wizards_persistence.py`, `tests/security/test_packs_and_wizards_observer_guard.py`, `tests/integration/test_declarative_packs_and_wizards_postgres18.py`, `apps/web/src/__tests__/{vitestPacksAndWizardsMockHandlers.ts,vitest.setup.ts,declarative-packs-and-durable-wizards-f5.test.tsx,epics-14-15-process-studio-v2-and-declarative-packs.test.tsx,i18n-and-shell.test.tsx}` | Création / Modification | Couverture complète `AD-17` (unitaires, sécurité `403 ERR_OBSERVER_MODE_READ_ONLY`, intégration `create_app()` sans override sur PG18 réel + Redis, Vitest F5 `unmount()`/`render()` et handlers `openapi.json`). |

### 3.2 Résultats Chiffrés, Métriques & Qualité
- **Couverture de tests combinée Story `22.5` (`unit + security + integration PG18`)** : **`90.07 %`** (`569` statements, `39` manqués, `136` branches, `29` partielles — `--cov-fail-under=90` passé : `sql_declarative_packs.py` `95 %`, `packs/loader.py` `94 %`, `routers/packs.py` `91 %`, `routers/studio_and_wizards.py` `90 %`, `sql_wizard_sessions.py` `89 %`, `durable_wizards.py` `85 %`).
- **Tests Python** : **`831 passed`** (`tests/unit`, `tests/security`, `tests/evals`), **`5 passed`** sur `test_declarative_packs_and_durable_wizards_persistence.py` + `test_packs_and_wizards_observer_guard.py`, **`1 passed`** sur `tests/integration/test_declarative_packs_and_wizards_postgres18.py` (`testcontainers` PG18 + Redis).
- **Tests TypeScript / Vitest (`pnpm turbo run lint typecheck test`)** : **`9/9` tâches vertes** — `@orcia/ui` **`26/26` fichiers (`110/110` tests)**, `@orcia/api-client` **`2/2` fichiers (`13/13` tests)**, `@orcia/web` **`43/43` fichiers (`171/171` tests)** dont `declarative-packs-and-durable-wizards-f5.test.tsx` (`3/3`), `epics-14-15-process-studio-v2-and-declarative-packs.test.tsx` (`3/3`), `i18n-and-shell.test.tsx` (`26/26`) et `zero-dead-buttons-and-silent-catches-audit.test.tsx`.
- **Qualité statique & Architecture** :
  - `grep -rn "ORCIA_DISABLE_PG_BOOTSTRAP_SYNC" apps/api/src apps/worker/src packages/orcia-core/src packages/orcia-connectors/src` : **`0` occurrence**.
  - `.venv/bin/ruff check .` (`All checks passed!`) & `.venv/bin/ruff format --check .` (`1190 files already formatted`).
  - `.venv/bin/mypy --strict packages/orcia-core apps/api apps/worker` (`Success: no issues found in 506 source files`).
  - `.venv/bin/lint-imports` (`Contracts: 5 kept, 0 broken`).
  - `.venv/bin/python scripts/export_openapi.py --check` (`0-diff`).
  - `.venv/bin/python .agent/skills/bmad-architecture/scripts/lint_spine.py` (`0 findings`, `ok: true`).
  - `gitnexus_detect_changes({scope: "all", repo: "/home/romain/Documents/Projects/ORCIA"})` : `changed_count: 121`, `affected_count: 618`, `changed_files: 23`, `risk_level: "critical"`.

### 3.3 Validation & Procédure de Test sur Toute la Pyramide (`AD-17`)
- **Couche 1a / 1b (Unitaires & UI Vitest)** :
  - `timeout --kill-after=5s 60s .venv/bin/pytest tests/unit/test_declarative_packs_and_durable_wizards_persistence.py tests/security/test_packs_and_wizards_observer_guard.py -v` (`5 passed`).
  - `pnpm --filter @orcia/web exec vitest run src/__tests__/declarative-packs-and-durable-wizards-f5.test.tsx` (`3 passed`) & `pnpm turbo run lint typecheck test` (`9/9` tâches vertes, `294/294` tests JS/TS).
- **Couche 2 (`HTTP ➔ PG18` sur Composition Root réel sans override)** :
  - `timeout --kill-after=5s 180s .venv/bin/pytest tests/integration/test_declarative_packs_and_wizards_postgres18.py -v` (`1 passed in 22.86s` — `create_app()` via `app.router.lifespan_context(app)` sans `dependency_overrides` ni `app.state.*`, vérification `SELECT COUNT(*) FROM declarative_pack_bundles >= 1` au boot et après `DELETE` + `GET /api/v1/packs` + `POST /api/v1/packs/export/{workspace_id}`, parcours `/api/v1/wizards/sessions` -> `steps` -> `step-back` -> `COMPLETED`, `SELECT wizard_sessions` et relecture à froid `app2`).
- **Couche 3 (Contrats & Architecture)** : `export_openapi.py --check` (`0-diff`), `lint-imports` (`5/5 kept`), `ruff`, `mypy --strict`, `lint_spine.py` (`0 findings`).
- **Couche Sécurité & Couche 4 (Evals)** : `test_packs_and_wizards_observer_guard.py` (`HTTP 403 ERR_OBSERVER_MODE_READ_ONLY` par header `READ_ONLY_OBSERVER` et JWT `OBSERVER` sur les `5` mutations packs/wizards) et `tests/unit tests/security tests/evals` (`831 passed`).
- **Couche 5 (Playwright E2E)** : Cohérence des sélecteurs `data-testid` (`declarative-pack-card-sdlc`, `export-pack-sdlc-zip-btn`, `packs-registry-status-banner`, `exported-pack-zip-filename`, `wizard-step-form-1..5`, `wizard-step-back-btn`, `wizard-completed-badge`) vérifiée dans `apps/web/e2e/18-catalog-packs-wizards-and-mcp-bench.spec.ts` (#3 & #4 ; exécution complète en Vague 4 dans `Story 22.9`).
