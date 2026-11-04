# 2026-11-04 — Persistance PostgreSQL 18 du 1er Compte Administrateur Jour 0, Script `db:reset` & Garde-Fous Anti-Silos

- **Date** : 2026-11-04
- **Story / Clé Sprint** : `2026-11-04-persistance-admin-jour0-et-reinit-bdd` (`Post-Epic 12 — Correctif & Gouvernance Tech Lead`)
- **Auteur / Contexte** : Résolution du bug de réapparition systématique de la mire de création du compte Administrateur initial (`first-boot-admin-setup-modal`) à chaque réouverture/rafraîchissement de l'URL ORCIA (`http://127.0.0.1:3100`), câblage bout-en-bout (`apps/web` $\rightarrow$ `@orcia/api-client` $\rightarrow$ `apps/api` $\rightarrow$ `orcia_core.bootstrap` $\rightarrow$ PostgreSQL 18 `users`), création du script de réinitialisation Jour 0 (`infra/scripts/maintenance/09_reset_db_first_boot.py` / `pnpm db:reset`), et institution dans `GEMINI.md`, `CLAUDE.md` et `TECH-LEAD-REPORT-TEMPLATE.md` de l'obligation de Rapport Tech Lead pré-modification (`{YYYY-MM-DD}-{descriptif-court}-tech-lead-report.md`) et des 4 garde-fous anti-silos (`Story 9.2`, `Story 12.1`, `Story 12.4`).
- **Commits associés** : `working-tree`

---

## 1. Analyse du Besoin & Étude d'Impact Tech Lead (Pré-Implémentation)

### 1.1 Contexte & Problématique
- **Symptôme observé** : À chaque ouverture ou rafraîchissement (`F5`) de l'URL d'ORCIA (`http://127.0.0.1:3100`), la modale bloquante de création du compte Administrateur initial (`first-boot-admin-setup-modal`) revenait systématiquement, même après avoir créé le premier compte.
- **Diagnostic racine (3 silos déconnectés entre les Stories `9.2`, `12.1` et `12.4`)** :
  1. **Silo Frontend (`apps/web/src/components/platformSetupStore.tsx`, Story 12.4)** : Le store `PlatformSetupProvider` conservait `platformAdmin` uniquement dans un `useState<ConfiguredPlatformAdmin | null>(null)` en mémoire vive React sans appeler l'API backend ni hydrater son état au démarrage.
  2. **Silo Backend API (`apps/api/src/orcia_api/routers/bootstrap.py`, Story 9.2)** : La route `POST /api/v1/bootstrap/welcome-setup/first-admin` appelait uniquement `ProgressiveDay0AccostageService.initialize_first_platform_admin()` en mémoire RAM Python et n'appelait jamais l'adaptateur SQL `create_first_platform_admin_on_postgres18()`.
  3. **Silo Base de Données & Proxy Vite** : Le script `04_backfill_system_bootstrap.py` insérait 3 utilisateurs fictifs (`karim.admin@orcia.io`, `marc.lead@orcia.io`, `nadia.dev@orcia.io`), aucun script `db:reset` ne permettait de revenir à l'état Jour 0 (`COUNT(*) FROM users == 0`), et `apps/web/vite.config.ts` ciblait par défaut le port `8100` au lieu du port `8000` de FastAPI.
- **Exigence méthodologique additionnelle** : Pour toute demande nécessitant des ajustements d'ORCIA (hors ou dans une User Story), un rapport Tech Lead basé sur `docs/implementation-artifacts/TECH-LEAD-REPORT-TEMPLATE.md` et nommé `docs/implementation-artifacts/tech-lead-reports/{YYYY-MM-DD}-{descriptif-court}-tech-lead-report.md` doit obligatoirement être généré **avant** d'effectuer toute modification du code, et les 4 garde-fous de câblage vertical doivent être inscrits dans `GEMINI.md` et `CLAUDE.md`.

### 1.2 Exploration, Analyse d'Impact GitNexus, Factorisation & Dette Technique
- **Analyse d'Impact GitNexus (`gitnexus_query`, `gitnexus_context`, `gitnexus_impact`)** :
  - `gitnexus_impact({target: "create_first_platform_admin_on_postgres18", direction: "upstream", repo: "ORCIA"})` : `impactedCount: 0` hors tests — confirmant que l'adaptateur SQL livré en Story 9.2 était orphelin dans `apps/api`.
  - `gitnexus_impact({target: "ProgressiveDay0AccostageService", direction: "upstream", repo: "ORCIA"})` : appelé par `apps/api/src/orcia_api/dependencies/__init__.py` et `apps/api/src/orcia_api/routers/bootstrap.py` (`risk: LOW`).
- **Exploration & Chiffres Clés (Base de Données / Conteneurs / Benchmark)** :
  - Inspection de la table PostgreSQL 18 `users` sur `localhost:5433/orcia` : présence de `3` utilisateurs issus du seed `04_backfill_system_bootstrap.py`.
  - Après exécution de `09_reset_db_first_boot.py --apply` : `cleared_tables=45`, `deleted_rows=59`, `remaining_users=0`, catalogue système `bootstrap_artifacts` (`5` artefacts `orcia://system/bootstrap/*`) et `agent_definitions` (`1` DAG `assistant-agent`) intégralement préservés.
- **Opportunités de Factorisation & Résorption de Dette Technique Naissante** :
  - Réutilisation de `AuthAndOrgService.hasher.hash_password` (Argon2id) dans `routers/bootstrap.py` pour hacher le mot de passe du 1er administrateur avant persistance SQL.
  - Exposition propre de `create_first_platform_admin_on_postgres18` et `get_first_platform_admin_from_postgres18` dans l'API publique `orcia_core.bootstrap` afin de respecter `AD-19` (`lint-imports` : interdiction d'importer `_internal` depuis `orcia_api`).

---

## 2. Plan d'Implémentation

### 2.1 Schéma de Données & Migrations Alembic (`infra/migrations/versions/...`, si applicable)
- Aucune migration Alembic supplémentaire requise : la table `users` (`id UUID PRIMARY KEY`, `email`, `display_name`, `password_hash`, `is_platform_admin`, `human_profile`, `preferred_locale`) existe déjà.
- Création du script de maintenance opérationnelle [`infra/scripts/maintenance/09_reset_db_first_boot.py`](file:///home/romain/Documents/Projects/ORCIA/infra/scripts/maintenance/09_reset_db_first_boot.py) :
  - Respecte les triggers *Append-Only* sur `audit_ledger` et `blackboard_snapshots` en utilisant `TRUNCATE TABLE ... RESTART IDENTITY CASCADE` (les triggers PostgreSQL étant `BEFORE UPDATE OR DELETE`, `TRUNCATE` est autorisé sans désactiver les triggers).
  - Réamorce de façon idempotente le socle système (`orcia://system/bootstrap/*` et `assistant-agent`) avec `0` ligne dans `users`.
  - Mode `--dry-run` par défaut (rollback) et `--apply` pour commiter, exposé via `scripts/manage.py reset-db` et `pnpm db:reset`.

### 2.2 Noyau Métier Hexagonal, Orchestration & Workers (`packages/orcia-core/`, `apps/worker/`, `infra/sandbox/`)
- [`packages/orcia-core/src/orcia_core/bootstrap/_internal/sql_first_user_guard.py`](file:///home/romain/Documents/Projects/ORCIA/packages/orcia-core/src/orcia_core/bootstrap/_internal/sql_first_user_guard.py) :
  - Ajout de `get_first_platform_admin_from_postgres18(engine)` retournant le 1er administrateur persisté dans `users` (ou `None` si la table `users` est vide).
- [`packages/orcia-core/src/orcia_core/bootstrap/progressive_accostage.py`](file:///home/romain/Documents/Projects/ORCIA/packages/orcia_core/bootstrap/progressive_accostage.py) :
  - Suppression de l'initialisation en dur `self._completed_keys = {"first-admin"}` au profit d'un ensemble vide `set()` au Jour 0.
  - Enrichissement de `AccostageStatusReport` avec `first_admin_initialized: bool`, `first_admin_email: str | None` et `first_admin_display_name: str | None`, et ajout de `sync_first_admin_from_record()`.

### 2.3 Couche Backend API, Sécurité & Contrats (`apps/api/`, `packages/api-client/`)
- [`apps/api/src/orcia_api/routers/bootstrap.py`](file:///home/romain/Documents/Projects/ORCIA/apps/api/src/orcia_api/routers/bootstrap.py) & [`apps/api/src/orcia_api/schemas/bootstrap.py`](file:///home/romain/Documents/Projects/ORCIA/apps/api/src/orcia_api/schemas/bootstrap.py) :
  - `GET /api/v1/bootstrap/accostage-status` interroge PostgreSQL 18 via `get_first_platform_admin_from_postgres18(engine)` lorsque `session_maker` est disponible, synchronise `ProgressiveDay0AccostageService` et retourne `first_admin_initialized`, `first_admin_email` et `first_admin_display_name`.
  - `POST /api/v1/bootstrap/welcome-setup/first-admin` hache le mot de passe via Argon2id et exécute `create_first_platform_admin_on_postgres18(engine, ...)` sous verrou `LOCK TABLE users IN EXCLUSIVE MODE` (renvoyant `HTTP 409 ERR_FIRST_ADMIN_ALREADY_INITIALIZED` en RFC 9457 si un compte existe déjà).
- [`packages/api-client/src/domains/bootstrapAndOntology.ts`](file:///home/romain/Documents/Projects/ORCIA/packages/api-client/src/domains/bootstrapAndOntology.ts) :
  - Régénération du schéma OpenAPI 3.1 (`scripts/export_openapi.py`) et ajout des méthodes typées `getAccostageStatus()`, `createWelcomeSetupFirstAdmin()` et `registerProgressiveLlmEndpoint()`.

### 2.4 Interface Utilisateur & Expérience (`apps/web/`)
- [`apps/web/src/components/platformSetupStore.tsx`](file:///home/romain/Documents/Projects/ORCIA/apps/web/src/components/platformSetupStore.tsx) & [`apps/web/src/components/ShellContainer.tsx`](file:///home/romain/Documents/Projects/ORCIA/apps/web/src/components/ShellContainer.tsx) :
  - Persistance locale immédiate dans `localStorage` (`orcia.platform_admin.v1`) doublée d'une hydratation/réconciliation au montage via `getAccostageStatus()` sur PostgreSQL 18 :
    - Si la base contient déjà le compte Admin (`first_admin_initialized: true`), `platformAdmin` est hydraté et la mire `first-boot-admin-setup-modal` ne s'affiche plus.
    - Si la base a été réinitialisée (`first_admin_initialized: false`), le cache local est purgé automatiquement et la mire réapparaît.
  - Lors de la validation du formulaire dans `ShellContainer.tsx`, appel à `createWelcomeSetupFirstAdmin()` pour enregistrer le compte dans PostgreSQL 18 avant de fermer la modale.
- [`apps/web/vite.config.ts`](file:///home/romain/Documents/Projects/ORCIA/apps/web/vite.config.ts) :
  - Alignement du port proxy `/api` par défaut sur `8000`.

### 2.5 Gouvernance Documentaire (`GEMINI.md`, `CLAUDE.md`, `TECH-LEAD-REPORT-TEMPLATE.md`)
- Ajout dans [`GEMINI.md`](file:///home/romain/Documents/Projects/ORCIA/GEMINI.md) et [`CLAUDE.md`](file:///home/romain/Documents/Projects/ORCIA/CLAUDE.md) de la règle impérative :
  - **Avant toute modification du projet ORCIA** (qu'il s'agisse d'une User Story `{story-key}` ou d'une demande d'ajustement/correctif ponctuel), générer un Rapport Tech Lead dans `docs/implementation-artifacts/tech-lead-reports/` basé sur `TECH-LEAD-REPORT-TEMPLATE.md` et préfixé par la date du jour complétée d'un descriptif court (`{YYYY-MM-DD}-{descriptif-court}-tech-lead-report.md` pour toute demande hors Story, ou `{story-key}-tech-lead-report.md` pour une Story du sprint).
  - Ajout des **4 garde-fous anti-silos** : (1) Zéro adaptateur SQL orphelin (`gitnexus_impact`), (2) Test d'intégration vertical `HTTP ➔ PostgreSQL 18`, (3) Interdiction des stores métier `useState` éphémères et test de survie au `F5` (`unmount()` + `render()`), (4) Validation sur base Jour 0 vierge via `pnpm db:reset`.

---

## 3. Bilan des Modifications & Résultats (Post-Implémentation)

### 3.1 Fichiers Développés & Modifiés
| Fichier | Nature (Création / Modification / Refactoring) | Description synthétique |
| :--- | :--- | :--- |
| `packages/orcia-core/src/orcia_core/bootstrap/_internal/sql_first_user_guard.py` | Modification | Ajout de `get_first_platform_admin_from_postgres18` pour relire le 1er admin depuis PostgreSQL 18 |
| `packages/orcia-core/src/orcia_core/bootstrap/progressive_accostage.py` | Modification | État Jour 0 vierge par défaut et enrichissement de `AccostageStatusReport` |
| `packages/orcia-core/src/orcia_core/bootstrap/__init__.py` | Modification | Ré-export public des gardes SQL Jour 0 (`AD-19`) |
| `apps/api/src/orcia_api/schemas/bootstrap.py` | Modification | Ajout de `first_admin_initialized`, `first_admin_email`, `first_admin_display_name` dans `AccostageStatusResponse` |
| `apps/api/src/orcia_api/routers/bootstrap.py` | Modification | Câblage de `GET /accostage-status` et `POST /welcome-setup/first-admin` sur PostgreSQL 18 + Argon2id |
| `packages/api-client/src/domains/bootstrapAndOntology.ts` | Modification | Ajout de `getAccostageStatus`, `createWelcomeSetupFirstAdmin` et `registerProgressiveLlmEndpoint` |
| `apps/web/src/components/platformSetupStore.tsx` | Modification | Hydratation depuis `GET /api/v1/bootstrap/accostage-status` + synchronisation `localStorage` |
| `apps/web/src/components/ShellContainer.tsx` | Modification | Persistance via `POST /api/v1/bootstrap/welcome-setup/first-admin` à la création du 1er Admin |
| `apps/web/vite.config.ts` | Modification | Alignement du port proxy API par défaut sur `8000` |
| `infra/scripts/maintenance/09_reset_db_first_boot.py` | Création | Script de remise à zéro Jour 0 (`--dry-run` / `--apply`) préservant les triggers *Append-Only* |
| `scripts/manage.py` & `package.json` | Modification | Ajout de la commande `reset-db` et du script `pnpm db:reset` |
| `tests/integration/test_story_9_2_first_user_lock_postgres18.py` | Modification | Ajout du test d'intégration HTTP FastAPI $\rightarrow$ PostgreSQL 18 + test de `09_reset_db_first_boot.py` |
| `apps/web/src/__tests__/i18n-and-shell.test.tsx` | Modification | Ajout du test de survie au rechargement (`unmount()` puis `render()`) après création de l'admin |
| `GEMINI.md`, `CLAUDE.md` & `docs/implementation-artifacts/TECH-LEAD-REPORT-TEMPLATE.md` | Modification | Inscription de la consigne de Rapport Tech Lead préfixé par la date (`YYYY-MM-DD-descriptif-court`) et des 4 garde-fous anti-silos |

### 3.2 Résultats Chiffrés, Métriques & Qualité
- **Couverture de tests** : `19 passed` en unitaire sur la suite Bootstrap/Jour 0, `5 passed` en intégration `testcontainers` PostgreSQL 18, `19 passed` sous Vitest (`apps/web`).
- **Performances mesurées** : `GET /api/v1/bootstrap/accostage-status` `< 5 ms`, réinitialisation complète Jour 0 (`09_reset_db_first_boot.py --apply`) `< 120 ms` (`45` tables purgées).
- **Qualité statique & Architecture** :
  - `ruff check` & `ruff format --check` : `0 warning`
  - `mypy --strict` & `pnpm typecheck` : `0 error`
  - `lint-imports` : `5 contracts kept, 0 broken`
  - `lint_spine.py` : `ok: true, 0 findings`
  - `gitnexus_detect_changes()` : Périmètre vérifié et conforme (`create_first_platform_admin_on_postgres18` et `get_first_platform_admin_from_postgres18` désormais rattachés à `routers/bootstrap.py`).

### 3.3 Validation & Procédure de Test (5 Couches `AD-17`)
- **Couche 1 — Tests Unitaires (`pytest`, `Vitest`)** : Validation de `ProgressiveDay0AccostageService` (`first_admin_initialized: False` au départ puis `True` après création) et survie au démontage/remontage React dans `apps/web/src/__tests__/i18n-and-shell.test.tsx`.
- **Couche 2 — Tests d'Intégration (`testcontainers-python` PostgreSQL 18)** : Validation bout-en-bout dans `tests/integration/test_story_9_2_first_user_lock_postgres18.py` (`GET /accostage-status` $\rightarrow$ `POST /welcome-setup/first-admin` $\rightarrow$ vérification `SELECT` dans `users` $\rightarrow$ `GET /accostage-status` $\rightarrow$ rejet `409` du second appel $\rightarrow$ remise à zéro via `09_reset_db_first_boot.py`).
- **Couche 3 — Tests de Contrat API (`openapi-typescript` 0-diff)** : Schémas OpenAPI 3.1 régénérés (`docs/planning-artifacts/architecture/architecture-ORCIA-2026-10-24/openapi/domains/bootstrap.openapi.json`).
- **Couche 4 — Tests d'Orchestration IA** : Sans impact sur les cassettes LLM (`DeterministicCassetteLLM`).
- **Couche 5 — Vérification E2E sur les services locaux actifs** : Base locale réinitialisée (`0` user) et API `:8000` + Web `:3100` opérationnels.
