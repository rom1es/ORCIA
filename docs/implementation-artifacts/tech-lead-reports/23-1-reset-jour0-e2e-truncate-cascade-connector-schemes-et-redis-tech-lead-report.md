# Story 23.1 — Déblocage `resetDay0()` (`TRUNCATE CASCADE` E2E isolé `orcia_e2e`), Protection `connector_schemes` & Purge Redis `FLUSHDB`

- **Date** : 2026-11-19
- **Story / Clé Sprint** : `23-1-reset-jour0-e2e-truncate-cascade-connector-schemes-et-redis` (`Epic 23` — Vague 0 `P0`)
- **Capacité(s)** : `CAP-003`, `CAP-011`, `CAP-020`, `CAP-021`, `CAP-022`, `CAP-024`, `CAP-030`, `CAP-031`, `CAP-032`, `CAP-033`, `CAP-054`, `CAP-065`, `CAP-082`, `CAP-140`, `CAP-200`, `CAP-201` *(et déblocage transverse des `87` échecs `beforeEach` affectant la campagne E2E)* — classification : `feature` + `hygiène` (`REM23-01` / `ARCH23-01`)
- **Auteur / Contexte** : `22.10-impl` (Winston, Architecte BMAD — pré-implémentation Epic 23). Résout le paradoxe de maturité PostgreSQL 18 révélé en `Story 22.9` : dès que le scénario `#10` (`03-human-led-anchor-and-arbitration.spec.ts`) persiste réellement des lignes dans `step_executions` et `blackboard_snapshots`, les `87` scénarios E2E suivants (`#11`–`#110`, hors `13` skips) échouent dans `beforeEach` (`resetDay0()`) sur `RestrictViolationError` (`blackboard_snapshots_step_execution_id_fkey`).
- **Commits associés** : `fix(epic-23): story 23.1 - unblock e2e reset_day0 truncate cascade, protect connector_schemes and flush redis` (branche `feat/epic-23-remediation-pg18-sse-direction-c`)

---

## 1. Analyse du Besoin & Étude d'Impact Tech Lead (Pré-Implémentation)

### 1.1 Contexte & Problématique
- **Preuve E2E observée (`e2e-campaign-epic-22`)** :
  - Dans [`bilan-execution-tests-e2e-epic-22.md`](../e2e-campaign-epic-22/bilan-execution-tests-e2e-epic-22.md), les scénarios `#8`, `#9` (`assistant_folders`) et `#10` (`human_anchor_signatures`, `step_executions`, `blackboard_snapshots`) passent désormais de `FAIL` (Epic 21) à `PASS` grâce aux adaptateurs PostgreSQL 18 câblés en Epic 22.
  - Dès le scénario `#11` (`04-multi-actor-claim-sse.spec.ts`) et jusqu'au scénario `#110` (`shell.spec.ts` `mobile-companion`), **`87` scénarios consécutifs (`43` `desktop-cockpit` + `44` `mobile-companion`)** échouent en `~1 s` dès le hook `beforeEach` (`apps/web/e2e/support/day0.ts:L12-L18`) sur :
    `sqlalchemy.exc.IntegrityError: (sqlalchemy.dialects.postgresql.asyncpg.RestrictViolationError) update or delete on table "step_executions" violates RESTRICT setting of foreign key constraint "blackboard_snapshots_step_execution_id_fkey" on table "blackboard_snapshots"`.
  - Échouant dès `resetDay0()`, `09_reset_db_first_boot.py` annule sa transaction : `Alice Admin E2E` reste en base, provoquant la redirection de tous les scénarios `#11`–`#110` sur `/login` (`Connexion à ORCIA`).
  - **Captures représentatives associées** :
    - `#11` [`04-multi-actor-claim-sse` desktop](../e2e-campaign-epic-22/screenshots/04-multi-actor-claim-sse/desktop-cockpit--a-prend-en-charge-une-tache-b-est-refuse-409-et-un-nouveau-flux-sse-rejoue-l-evenement-5--failed.png)
    - `#57` [`00-stack-smoke` mobile](../e2e-campaign-epic-22/screenshots/00-stack-smoke/mobile-companion--apres-reset-jour-0-la-modale-de-premier-administrateur-est-presentee--failed.png)
    - `#69` [`05-mobile-companion-and-rgaa` mobile](../e2e-campaign-epic-22/screenshots/05-mobile-companion-and-rgaa/mobile-companion--aucun-debordement-horizontal-sur-mobile-une-fois-la-plateforme-initialisee--failed.png)
    - `#85` [`14-auth-2fa-account-and-profile` mobile](../e2e-campaign-epic-22/screenshots/14-auth-2fa-account-and-profile/mobile-companion--popup-mon-compte-parametres-5-onglets-cle-ide-mcp-et-page-profil-survivent-a-un-f5--failed.png)
- **Angles morts secondaires identifiés par Winston (`ARCH23-01`)** :
  1. **Suppression involontaire de `connector_schemes`** : `09_reset_db_first_boot.py` déclare `alembic_version`, `blackboard_snapshots` et `audit_ledger` dans `PROTECTED_TABLES` (`L38-L44`), mais omet `connector_schemes` ; la boucle dynamique finale (`L153-L158`) exécute alors `DELETE FROM connector_schemes`, brisant la table de référence attendue par `00-stack-smoke.spec.ts` et les FK `ON DELETE RESTRICT` de `0013_story_3_2e_connector_schemes_expand.py#L89,L108,L127,L146`.
  2. **Résidus hors `public` et hors PostgreSQL** : `09_reset_db_first_boot.py:L141` ne parcourt que `schemaname = 'public'` (ignorant `schema="dbos"` créé dans `dbos_engine.py:L89-109` / `uow.py:L70-93`), et `reset_day0.py` ne vide ni Redis (`help:*`, `speed2:*`, verrous `lock:step:*`) ni les caches `app.state` dans le processus FastAPI maintenu actif entre scénarios E2E (`e2e_stack.py`).
- **Contrainte bloquante `GEMINI.md`** :
  - Les tables `audit_ledger` (`prevent_audit_ledger_mutation` — migration `20261116_0601:L145-153`) et `blackboard_snapshots` (`trg_blackboard_snapshots_append_only` — migration `0011:L138-142`) sont strictement append-only. **Il est formellement interdit de désactiver ces triggers (`DISABLE TRIGGER`)** dans les migrations ou scripts de maintenance (`09_reset_db_first_boot.py`).

### 1.2 Exploration, Analyse d'Impact GitNexus, Factorisation & Dette Technique
- **Analyse d'Impact GitNexus (`repo: "/home/romain/Documents/Projects/ORCIA"`)** :
  - `reset_database_to_first_boot` (`infra/scripts/maintenance/09_reset_db_first_boot.py:L124-L225`) :
    - `impactedCount: 127`, `risk: "CRITICAL"`, `epistemic: "exact"`, profondeur `direct: 87`, `d=2: 33`, `d=3: 7`, `processes_affected: 138`, `modules_affected: 18`.
  - `reset_day0` (`infra/scripts/e2e/reset_day0.py:L23-L39`) : absent en tant que nœud appelable de l'index GitNexus courant (`commitsBehind: 2`) ; chaîne d'appel vérifiée par lecture directe : `apps/web/e2e/support/day0.ts:L12-L18` → `infra/scripts/e2e/reset_day0.py` (`43` L) → `infra/scripts/maintenance/09_reset_db_first_boot.py` (`286` L).
- **Exploration & Chiffres Clés** :
  - Triggers append-only PG18 vérifiés dans les migrations `0011#L138-L142` et `20261116_0601#L145-L153` : ils sont déclarés `BEFORE UPDATE OR DELETE ... FOR EACH ROW` (et **non** `BEFORE TRUNCATE`).
  - Conséquence PostgreSQL 18 exacte : sur la base E2E isolée **`orcia_e2e` uniquement**, `TRUNCATE TABLE <tables> RESTART IDENTITY CASCADE` vide atomiquement `step_executions`, `workflow_runs`, `blackboard_snapshots`, `audit_ledger`, `users` et leurs tables dépendantes **sans jamais altérer ni désactiver les triggers append-only** ni enfreindre `ON DELETE RESTRICT`, tout en excluant `alembic_version` et `connector_schemes`.
- **Volumétrie & Décision DRY (`ARCH23-01`)** :
  - `infra/scripts/maintenance/09_reset_db_first_boot.py` (`286` L) et `infra/scripts/e2e/reset_day0.py` (`43` L) restent sous `< 350` L.
  - Séparation de responsabilité stricte : **ne jamais** introduire de `TRUNCATE` des tables append-only dans le script de maintenance général `09_reset_db_first_boot.py` (utilisable en dev/staging où l'historique immuable doit être préservé) ; cantonner le `TRUNCATE ... RESTART IDENTITY CASCADE` exclusivement dans `infra/scripts/e2e/reset_day0.py` derrière le garde-fou bloquant `is_isolated_e2e_database_url(state["database_url"])` (`e2e_stack_config.py#L28` : `dbname == "orcia_e2e"`, hôte local).

---

## 2. Plan d'Implémentation

### 2.1 Schéma de Données & Migrations Alembic (`infra/migrations/versions/`)
- Aucune nouvelle migration Alembic requise (les contraintes `ON DELETE RESTRICT` et triggers `BEFORE UPDATE OR DELETE FOR EACH ROW` sur `blackboard_snapshots` et `audit_ledger` restent **strictement intacts et inchangés**).
- Vérification de non-régression sur `connector_schemes` (`0013_story_3_2e_connector_schemes_expand.py`) et `platform_auth_settings` (`20261115_1901`).

### 2.2 Noyau Métier, Scripts E2E & Maintenance (`infra/scripts/maintenance/`, `infra/scripts/e2e/`)
1. **`infra/scripts/maintenance/09_reset_db_first_boot.py`** :
   - Ajouter `"connector_schemes"` (et les tables de référence système immuables équivalentes) à `PROTECTED_TABLES` (`L38-L44`) afin que `DELETE` dans `L153-L158` n'efface jamais les schémas de connecteurs socle.
   - Ajouter une garde explicite avant `DELETE FROM step_executions` / `workflow_runs` : si des lignes existent dans les tables append-only référencées (`blackboard_snapshots`, `audit_ledger`), échouer explicitement avec un message clair orientant vers le harnais E2E isolé plutôt que de tenter un `DISABLE TRIGGER`.
2. **`infra/scripts/e2e/reset_day0.py`** :
   - Conserver la vérification bloquante `is_isolated_e2e_database_url(database_url)` (échec immédiat `RuntimeError` si `dbname != "orcia_e2e"` ou hôte non local).
   - Découvrir dynamiquement les tables du schéma `public` **en excluant** `alembic_version` et `connector_schemes`, exécuter `TRUNCATE TABLE ... RESTART IDENTITY CASCADE` dans une transaction atomique, et purger les tables d'exécution DBOS dans `dbos.*` si le schéma `dbos` existe (hors métadonnées structurelles le cas échéant, en revalidant le boot DBOS).
   - Réinitialiser `platform_auth_settings` aux valeurs Jour 0 et incrémenter / régénérer `boot_epoch` pour invalider tout jeton antérieur.
   - Exécuter `FLUSHDB` sur Redis (`state["redis_url"]`) pour purger `help:*`, `speed2:*`, `lock:step:*` et caches de session.
   - Appeler l'invalidation des caches mémoire côté FastAPI (`POST /api/v1/_e2e/evict-memory-caches` si actif) puis relancer l'amorçage système minimal Jour 0 (`ensure_system_bootstrap_seed`, `0` utilisateur en table `users`).

### 2.3 Couche Backend API, Sécurité & Contrats (`apps/api/`, `packages/api-client/`)
- Vérifier que l'endpoint strictement E2E `POST /api/v1/_e2e/evict-memory-caches` (introduit en `Story 22.8` sous garde `ORCIA_ENV == "e2e"`) vide proprement tout cache résiduel `platform_setup_snapshot` / accostage en mémoire lors du `resetDay0()`.
- Aucune modification de schéma OpenAPI publique (`openapi-typescript` reste `0-diff`).

### 2.4 Interface Utilisateur & Expérience (`apps/web/e2e/support/`)
- Vérifier dans [`apps/web/e2e/support/day0.ts`](../../../apps/web/e2e/support/day0.ts#L12-L18) que `resetDay0(page)` complète le reset PG18 + Redis + éviction caches API + nettoyage stockage navigateur sans jamais réintroduire de fixtures cachées (`ORCIA_E2E_SEED_FIXTURES` interdit).

### 2.5 Analyse d'Impact sur la Pyramide des Tests (`AD-17` — Couches 1 à 5 + Sécurité, Obligatoire)
- **Couche 1a (Unitaires Python `tests/unit/`)** :
  - Tests unitaires sur `09_reset_db_first_boot.py` (`connector_schemes` dans `PROTECTED_TABLES`) et `reset_day0.py` (refus strict hors `orcia_e2e` via `is_isolated_e2e_database_url`).
- **Couche 2 (Intégration Verticale `HTTP FastAPI ➔ PostgreSQL 18` `tests/integration/`)** :
  - Nouveau test `testcontainers` PostgreSQL 18 + Redis 7.4 : *amorçage migrations Alembic → création utilisateur + `workflow_runs` + `step_executions` + `blackboard_snapshots` + `audit_ledger` + clé Redis → exécution `reset_day0()` → assertion `SELECT COUNT(*) == 0` sur `users`, `step_executions`, `workflow_runs`, `blackboard_snapshots`, `audit_ledger`, `COUNT(*) >= 1` sur `connector_schemes`, triggers `trg_blackboard_snapshots_append_only` et `prevent_audit_ledger_mutation` toujours actifs (`tgenabled = 'O'`), et `DBSIZE == 0` dans Redis*.
- **Couche 3 (Contrats & Lint)** : `ruff`, `mypy --strict`, `lint-imports` (`5 contracts kept`), `lint_spine.py` (`0 findings`), `0` `DISABLE TRIGGER`.
- **Couche 5 (E2E Playwright ciblé post-fix)** :
  - Exécution enchaînée `03-human-led-anchor-and-arbitration.spec.ts` suivi immédiatement de `04-multi-actor-claim-sse.spec.ts` et `shell.spec.ts` (`desktop-cockpit` + `mobile-companion`) prouvant l'absence de `RestrictViolationError` en `beforeEach`.

---

## 3. Bilan des Modifications & Résultats (Post-Implémentation)

### 3.1 Fichiers Développés & Modifiés
| Fichier | Nature (Création / Modification / Refactoring) | Description synthétique |
| :--- | :--- | :--- |
| `infra/scripts/maintenance/09_reset_db_first_boot.py` (`329` L) | Modification | Ajout de `"connector_schemes"` à `PROTECTED_TABLES`, extraction du helper réutilisable `reset_platform_auth_settings_and_system_seed()`, et garde `_assert_no_append_only_restrict_refs()` rejetant explicitement par `RuntimeError` toute suppression de `step_executions`/`workflow_runs` référencées par `blackboard_snapshots`/`audit_ledger` sans jamais désactiver aucun trigger (`0` `DISABLE TRIGGER`). |
| `infra/scripts/e2e/reset_day0.py` (`214` L) | Modification | Exécution atomique `TRUNCATE TABLE ... RESTART IDENTITY CASCADE` sur `public` (excluant `alembic_version`, `connector_schemes`) et `dbos` (excluant `dbos_migrations`, `dbos_datasource_migrations`, `alembic_version`) derrière le garde-fou strict `is_isolated_e2e_database_url()`, réinitialisation `platform_auth_settings` (`LOCAL`/`NONE`, nouveau `boot_epoch`) + seed socle `connector_schemes`, `FLUSHDB` Redis 7.4 et `POST /api/v1/_e2e/evict-memory-caches` (`ConnectError` non bloquant -> `False`, HTTP `>= 400` -> `RuntimeError`). |
| `apps/api/src/orcia_api/routers/e2e_test_hooks.py` (`116` L) | Modification | Mise à jour de `_E2E_EVICTABLE_STATE_ATTRS` et ré-initialisation Composition Root via `initialize_app_services(request.app)` sans jamais évincer les handles infra critiques (`db_engine`, `session_maker`, `reflexive_session_maker`, `http_client`, `redis_client`, `sse_broker`, `dbos_uow`, `dbos_datasource`). |
| `tests/unit/test_e2e_reset_day0_guard.py` (`313` L) | Création | Couche 1a (`16` tests) : protection `connector_schemes`, refus immédiat des URLs hors `orcia_e2e`/non locales/ports `5432`/`5433`, comportement `ConnectError` vs HTTP `>= 400` vs `200`, absence d'attributs infra critiques dans `_E2E_EVICTABLE_STATE_ATTRS`, garde `ON DELETE RESTRICT` et CLI `main()`. |
| `tests/integration/test_e2e_reset_day0_postgres18_and_redis.py` (`398` L) | Création | Couche 2 (`testcontainers` `pgvector/pgvector:pg18` sur base `orcia_e2e` port éphémère + `redis:7.4-alpine` + vrai `create_app()` `ORCIA_ENV="e2e"` sans override ni `app.state` manuel) : vérifie le `RuntimeError` de `09_reset_db_first_boot.py`, l'exécution de `reset_day0_environment()` + `POST /api/v1/_e2e/evict-memory-caches`, `COUNT(*) == 0` sur `users`/`workflow_runs`/`step_executions`/`blackboard_snapshots`/`audit_ledger`, `COUNT(*) >= 7` sur `connector_schemes`, triggers `trg_blackboard_snapshots_append_only` & `prevent_audit_ledger_mutation` toujours actifs (`tgenabled = 'O'`), `platform_auth_settings` réinitialisé (`LOCAL`/`NONE`) et Redis `DBSIZE == 0`. |

### 3.2 Résultats Chiffrés, Métriques & Qualité
- **Couverture de tests ciblée (`coverage` sur les 3 modules modifiés Story 23.1)** : **`95 %`** (`232` statements, `3` missed, `64` branches, `11` partial) :
  - `apps/api/src/orcia_api/routers/e2e_test_hooks.py` : **`100 %`** (`23/23` stmts, `6/6` branches)
  - `infra/scripts/e2e/reset_day0.py` : **`97 %`** (`101` stmts, `1` miss)
  - `infra/scripts/maintenance/09_reset_db_first_boot.py` : **`93 %`** (`108` stmts, `2` miss)
- **Qualité statique & Architecture (Couche 3)** :
  - `.venv/bin/ruff check . && .venv/bin/ruff format --check .` : **`0` erreur**, `1254` fichiers formatés.
  - `.venv/bin/mypy --strict packages/orcia-core packages/orcia-connectors apps/api apps/worker` : **`0` erreur** (`550` fichiers source).
  - `MYPYPATH=infra/scripts/e2e .venv/bin/mypy --strict infra/scripts/maintenance/09_reset_db_first_boot.py infra/scripts/e2e/reset_day0.py` : **`0` erreur** (`2` fichiers source).
  - `.venv/bin/lint-imports` : **`5` contrats conservés, `0` brisé** (`596` fichiers, `4279` dépendances).
  - `.venv/bin/python .agent/skills/bmad-architecture/scripts/lint_spine.py --workspace docs/planning-artifacts/architecture/architecture-ORCIA-2026-10-24` : **`0` finding** (`ok: true`).
  - **GitNexus (`npx gitnexus analyze .` + `detect_changes(scope="all")`)** : `37 416` nœuds / `75 002` arêtes indexés ; `changed_count: 2` (`PUBLIC_EXCLUDED_TABLES`, `_SAFE_IDENT_RE` dans `infra/scripts/e2e/reset_day0.py`), `changed_files: 3`, `affected_count: 1724`, `risk_level: "critical"` (couvert par la garde `is_isolated_e2e_database_url()` et les tests Couche 1a + Couche 2 PG18/Redis).

### 3.3 Validation & Procédure de Test sur Toute la Pyramide (`AD-17` + 5 Garde-Fous de Câblage Vertical)
- **Couche 1a & Audits AST** :
  - `.venv/bin/pytest tests/unit/test_e2e_reset_day0_guard.py tests/unit/test_e2e_stack_config.py tests/unit/test_integration_no_manual_app_state_audit.py tests/unit/test_zero_orphan_sql_adapters_audit.py tests/unit/test_codebase_architectural_anti_patterns_audit.py -v` : **`35 passed` (`100 %`)**.
- **Couche 2 (Intégration Verticale PG18 + Redis + `09_reset_db_first_boot.py` non-régression)** :
  - `.venv/bin/pytest tests/integration/test_e2e_reset_day0_postgres18_and_redis.py -v` : **`1 passed` (`19.90s`)**.
  - Suite complète des tests existants invoquant `09_reset_db_first_boot.py` (`test_story_6_4`, `test_story_9_2`, `test_platform_auth_modes_2fa_and_local_isolation`, `test_story_7_1`, `test_story_7_2`, `test_story_7_4`, `test_story_16_2`, `test_story_16_3`, `test_story_20_3`) : **`11 passed` (`128.73s`)**.
- **Couche 5 (Tir Playwright enchaîné `03 -> 04 -> shell`, `ORCIA_E2E_CAMPAIGN_DIR=/tmp/orcia-e2e-verify-23-1`)** :
  - `RestrictViolationError` dans `beforeEach` (`resetDay0()`) : **`0` occurrence** (`87` échecs en cascade de l'Epic 22 intégralement levés).
  - `03-human-led-anchor-and-arbitration.spec.ts` : **`2/2 passed`** (`desktop-cockpit` `15.9s`, `mobile-companion` `12.7s`).
  - `04-multi-actor-claim-sse.spec.ts` : **`2/2 passed`** (`desktop-cockpit` `5.4s` & `5.0s` — précédemment bloqués dès `beforeEach` en Epic 22), **`2 skipped`** (`mobile-companion` skip attendu).
  - `shell.spec.ts` : `resetDay0()` s'exécute sans erreur sur les `8` cas (`4` desktop + `4` mobile) qui atteignent tous le shell et butent uniquement sur les erreurs `HTTP 401` pré-existantes sur `/api/v1/org-units`, `/api/v1/orchestration/state`, `/api/v1/users/me/preferences` au Jour 0 (périmètre `Story 23.2` / `Story 23.4`).
