# Story 21.4 — Harnais Playwright de Vérité PostgreSQL 18 (`query_db.py` + `dbAssertions.ts`), Fixture Capture PNG Systématique (`e2eCaptureFixture.ts`) & Mise à Niveau des 16 Specs Existantes

- **Date** : 2026-11-18
- **Story / Clé Sprint** : `21-4-harnais-playwright-verite-pg18-capture-png-finale-et-maj-16-specs-existantes` (`Epic 21`)
- **Capacité(s)** : `none (outillage tests E2E AD-17)` — classification : `hygiène` (`GEMINI.md` §5)
- **Auteur / Contexte** : Tech Lead (`Amelia` / `Winston`) — Story 21.4 (`AD-17`, `GEMINI.md` §3, règle de non-maquillage Epic 21). Fournir un harnais Playwright interrogeant PostgreSQL 18 (`orcia_e2e`) en lecture seule stricte sans ajouter de package npm (`infra/scripts/e2e/query_db.py` + `apps/web/e2e/support/dbAssertions.ts`), une fixture capturant systématiquement le screenshot PNG final de chaque test (`apps/web/e2e/support/e2eCaptureFixture.ts`), puis mettre à niveau les 16 specs existantes (`00..13` + `shell.spec.ts` — hors périmètre `21.4-impl`, pris en charge par `21.4-test`).
- **Commits associés** : Branche `feat/epic-21-user-journeys-e2e-db-audit` (`21.4-impl` + `21.4-test`).

---

## 1. Analyse du Besoin & Étude d'Impact Tech Lead (Pré-Implémentation)

### 1.1 Contexte & Problématique
- **Problématique** :
  1. Les specs Playwright E2E (`apps/web/e2e/*.spec.ts`) vérifient l'UI et les réponses HTTP, mais ne contrôlent pas directement la persistance effective en base PostgreSQL 18 (`orcia_e2e`), laissant un risque de faux positif en cas d'état uniquement en mémoire Python (`AD-17`, `GEMINI.md` §3).
  2. Les exécutions Playwright ne produisent ni capture PNG finale systématique (en succès comme en échec / timeout), ni manifeste structuré (`manifest.jsonl`) exploitable par l'audit croisé Sally × Winston (`Story 21.8`) et le verrou CI `Story 21.3`.
- **Comportement attendu vs actuel** :
  - `infra/scripts/e2e/query_db.py` (`< 180` lignes, 0 nouvelle dépendance) doit lire `.orcia-run/e2e-stack-state.json` via `e2e_stack_config.read_state()`, refuser strictement toute base ne passant pas `is_isolated_e2e_database_url()`, valider la requête en lecture seule stricte (`validate_readonly_sql`), exécuter en `SET TRANSACTION READ ONLY` via `sqlalchemy.ext.asyncio` + `asyncpg` avec paramètres liés `--params`, et sérialiser `{ "rows": [...], "row_count": N }` sur `stdout`.
  - `apps/web/e2e/support/dbAssertions.ts` (`< 160` lignes, 0 package npm ajouté) doit appeler `.venv/bin/python infra/scripts/e2e/query_db.py` via `execFileSync` (motif identique à `day0.ts`) et exporter `queryDbRows`, `expectDbRowExists` et `expectDbRowCount`.
  - `apps/web/e2e/support/e2eCaptureFixture.ts` (`< 180` lignes) doit étendre `test` de `@playwright/test` avec une fixture automatique `{ auto: true }` capturant `<projectName>--<test-slug>--<status>.png` dans `docs/implementation-artifacts/e2e-campaign-epic-21/screenshots/<spec-slug>/`, naviguant vers `/cockpit` (repli `/`) si la page est restée sur `about:blank`, supprimant les captures d'un statut antérieur du même test, et enregistrant les métadonnées (`@uj`, `@cap`, `status`, `url`, `duration_ms`, `error`, etc.) dans `docs/implementation-artifacts/e2e-campaign-epic-21/manifest.jsonl`.
- **Contraintes `.gitignore` & outillage** :
  - Vérification `git check-ignore -v docs/implementation-artifacts/e2e-campaign-epic-21/` : le répertoire cible n'est pas ignoré par `.gitignore`.

### 1.2 Exploration, Analyse d'Impact GitNexus, Factorisation & Dette Technique
- **Analyse d'Impact GitNexus (`gitnexus_query`, `gitnexus_context`, `repo: "/home/romain/Documents/Projects/ORCIA"`)** :
  - Exploration ciblée des briques E2E existantes :
    - `infra/scripts/e2e/e2e_stack_config.py` (`read_state`, `is_isolated_e2e_database_url`, `STATE_FILE`) consommé par `infra/scripts/e2e/e2e_stack.py`, `infra/scripts/e2e/reset_day0.py` et couvert par `tests/unit/test_e2e_stack_config.py`.
    - `apps/web/e2e/support/day0.ts` (`resetDay0`) appelant `.venv/bin/python infra/scripts/e2e/reset_day0.py` via `execFileSync`.
    - `infra/scripts/uj_e2e_coverage.py` (`parse_e2e_spec_headers`) qui extrait `@uj` (`UJ-[1-9]\d?`) et `@cap` (`CAP-\d+`) sur les 40 premières lignes de chaque `apps/web/e2e/*.spec.ts`.
  - Aucune régression ni modification requise sur `e2e_stack.py`, `e2e_stack_config.py`, `reset_day0.py` ou `day0.ts` (réutilisation directe par composition).
- **Opportunités de Factorisation & Contrôle de Volumétrie** :
  - Réutilisation directe de `read_state` et `is_isolated_e2e_database_url` depuis `e2e_stack_config.py` sans dupliquer la logique d'isolation (`orcia_e2e`, ports non-dev).
  - Alignement exact du parseur d'en-tête `@uj`/`@cap` dans `e2eCaptureFixture.ts` sur l'expression régulière de `infra/scripts/uj_e2e_coverage.py` (`@tag\s+([^|\n*]+)` sur les 40 premières lignes).
  - Chaque nouveau fichier reste strictement compact (`query_db.py` `< 180` lignes, `dbAssertions.ts` `< 160` lignes, `e2eCaptureFixture.ts` `< 180` lignes).

---

## 2. Plan d'Implémentation

### 2.1 Schéma de Données & Migrations Alembic (`infra/migrations/versions/...`)
- Non applicable : aucune table ni migration Alembic modifiée pour cet outillage de test.

### 2.2 Outillage Python E2E Lecture Seule (`infra/scripts/e2e/query_db.py`, `< 180` lignes)
- Insertion de `Path(__file__).resolve().parent` dans `sys.path` (motif identique à `reset_day0.py`) et import de `read_state` et `is_isolated_e2e_database_url` depuis `e2e_stack_config`.
- Fonction pure `validate_readonly_sql(sql: str) -> str` :
  - Parcours lexical tenant compte des littéraux simples (`'...'` et `E'...'`), identifiants doubles (`"..."`), chaînes dollar-quoted (`$tag$...$tag$`), commentaires ligne (`--`) et commentaires blocs imbriqués (`/* ... */`).
  - Rejet de toute requête vide ou réduite à des commentaires/espaces.
  - Suppression des commentaires/espaces en tête et vérification que le premier mot-clé est strictement `SELECT` ou `WITH` (insensible à la casse).
  - Interdiction des requêtes multiples (`;` suivi de tout autre jeton hors commentaires/espaces, ou plusieurs `;`), avec tolérance d'un unique `;` final optionnel supprimé avant exécution.
  - Interdiction de tout mot-clé DDL/DML (`INSERT`, `UPDATE`, `DELETE`, `DROP`, `ALTER`, `TRUNCATE`, `CREATE`, `GRANT`, `REVOKE`, `COPY`, `VACUUM`, `CALL`, `DO`, `LOCK`) hors littéraux texte et identifiants entre guillemets doubles.
- Fonction asynchrone `execute_readonly_query(database_url: str, sql: str, params: dict[str, Any]) -> list[dict[str, Any]]` :
  - Garde immédiat via `is_isolated_e2e_database_url(database_url)`.
  - Exécution via `create_async_engine` (`sqlalchemy.ext.asyncio` + `asyncpg`) dans une transaction `SET TRANSACTION READ ONLY` avec paramètres nommés `text(cleaned_sql)` + `params`.
  - Sérialisation JSON sûre (`UUID`, `datetime`/`date`/`time`, `Decimal`) retournant `{"rows": [...], "row_count": N}` sur `stdout`.

### 2.3 Helpers TypeScript E2E & Fixture Capture PNG (`apps/web/e2e/support/`)
- `apps/web/e2e/support/dbAssertions.ts` (`< 160` lignes, 0 dépendance npm) :
  - Appel synchrone de `.venv/bin/python infra/scripts/e2e/query_db.py --sql ... --params ...` via `execFileSync` (motif `day0.ts`).
  - Export de `queryDbRows<T extends Record<string, unknown>>(sql, params?)`, `expectDbRowExists(sql, params?, contextMessage?)` et `expectDbRowCount(sql, params, minCount, contextMessage?)` avec messages d'assertion `@playwright/test` explicites en cas de `0` ligne persistée en PG18.
- `apps/web/e2e/support/e2eCaptureFixture.ts` (`< 180` lignes) :
  - Extension de `test` de `@playwright/test` via fixture automatique `{ auto: true }` exécutée en teardown de chaque test (quel que soit `testInfo.status`).
  - Création de `docs/implementation-artifacts/e2e-campaign-epic-21/screenshots/<spec-slug>/`, suppression d'éventuelles captures antérieures `<projectName>--<test-slug>--*.png` pour le même test, repli `page.goto('/cockpit')` / `'/'` si la page est restée sur `about:blank`, `page.screenshot({ path, fullPage: true, timeout: 8000 })` en `try/catch` sans masquer l'erreur métier du test, attachement `testInfo.attach`, lecture des tags `@uj`/`@cap` dans les 40 premières lignes de `testInfo.file`, et ajout d'une ligne JSONL dans `docs/implementation-artifacts/e2e-campaign-epic-21/manifest.jsonl`.
  - Ré-export de `{ test, expect }`.

### 2.4 Mise à Niveau des 16 Specs Existantes (`apps/web/e2e/*.spec.ts` — périmètre `21.4-test`)
- Prise en charge dédiée par le sous-agent `21.4-test` : ajout des en-têtes `/** @uj ... | @cap ... */`, bascule sur `e2eCaptureFixture`, vérifications `F5` et assertions `SELECT` PostgreSQL 18 via `dbAssertions.ts`.

### 2.5 Analyse d'Impact sur la Pyramide des Tests (`AD-17`)
- **Couche 1a (Unitaires Python `tests/unit/`)** : `tests/unit/test_e2e_query_db_readonly.py` (pris en charge par `21.4-test`) couvrant `validate_readonly_sql`, refus hors `orcia_e2e`, paramètres liés et sérialisation.
- **Qualité Statique (`21.4-impl`)** : `.venv/bin/ruff check infra/scripts/e2e/query_db.py`, `MYPYPATH=infra/scripts/e2e .venv/bin/mypy --strict infra/scripts/e2e/query_db.py`, `pnpm --filter @orcia/web typecheck` et vérification `.gitignore`.
- **Couche 5 (E2E Playwright `apps/web/e2e/`)** : mise à niveau et validation des 16 specs par `21.4-test`.

---

## 3. Bilan des Modifications & Résultats (Post-Implémentation)

### 3.1 Fichiers Développés & Modifiés
| Fichier | Nature (Création / Modification) | Description synthétique |
| :--- | :--- | :--- |
| `infra/scripts/e2e/query_db.py` | Création (`21.4-impl`) | Exécuteur SQL lecture seule stricte (`validate_readonly_sql`, `SET TRANSACTION READ ONLY`, garde `is_isolated_e2e_database_url`, sérialisation JSON `UUID`/`datetime`/`Decimal`, `177` lignes `< 180`). |
| `apps/web/e2e/support/dbAssertions.ts` | Création (`21.4-impl`) | Pont Playwright → `.venv/bin/python infra/scripts/e2e/query_db.py` exportant `queryDbRows`, `expectDbRowExists`, `expectDbRowCount` (`98` lignes `< 160`, `0` package npm ajouté). |
| `apps/web/e2e/support/e2eCaptureFixture.ts` | Création (`21.4-impl`) | Fixture automatique `{ auto: true }` capturant le screenshot final PNG (`screenshots/<spec-slug>/<project>--<test>--<status>.png`) + métadonnées `@uj`/`@cap` dans `manifest.jsonl` (`135` lignes `< 180`). |
| `tests/unit/test_e2e_query_db_readonly.py` | Création (`21.4-test`) | Suite unitaire (`208` lignes `< 220`, `41` cas) : `validate_readonly_sql` (`SELECT`/`WITH`/commentaires/littéraux vs `INSERT`..`LOCK`/multi-requêtes), garde `orcia_e2e` (`5432`/`5433`/remote), sérialisation JSON, `SET TRANSACTION READ ONLY` & CLI. |
| `apps/web/e2e/00-stack-smoke.spec.ts` .. `13-epic-7-autonomous-governance-and-supervision.spec.ts` + `shell.spec.ts` (`16` fichiers) | Modification (`21.4-test`) | Bascule de `test`/`expect` sur `./support/e2eCaptureFixture`, ajout des en-têtes `/** @uj ... \| @cap ... */`, vérifications `F5` (`page.reload()`) et assertions `expectDbRowExists` / `expectDbRowCount` / `queryDbRows` sur les tables PG18 réelles (`users`, `org_units`, `workspaces`, `assistant_folders`, `human_anchor_signatures`, `task_notifications`, `gate_evaluations`, `chunk_approvals`, `catalog_items`, `workflow_definitions_v2`, `reflexive_execution_sessions`, `finops_scope_budgets`, `autonomy_contracts`, `workflow_triggers`, `workflow_runs`, `autonomous_post_hoc_audits`, `audit_ledger`), et retrait du `test.fixme` dans `02-assistant-streaming-and-folders.spec.ts`. |
| `apps/web/src/generated/orciaSiteManifest.ts` & `docs/site-catalog/index.html` | Régénération (`21.4-test`) | Synchronisation `pnpm site:sync && pnpm site:check` (`167` rapports, `28` routes, `133` primitives UI, `65` capacités, `20/20` UJ, `26/62` E2E fonctionnels). |
| `docs/implementation-artifacts/tech-lead-reports/README.md` & `docs/implementation-artifacts/sprint-status.yaml` | Clôture (`21.4-test`) | Indexation du rapport `21-4` et passage de la story `21-4` à `done`. |

### 3.2 Résultats Chiffrés, Métriques & Qualité
- **Volumétrie des briques (`< 180` / `< 220` lignes)** : `query_db.py` (`177` L), `dbAssertions.ts` (`98` L), `e2eCaptureFixture.ts` (`135` L), `test_e2e_query_db_readonly.py` (`208` L).
- **Tests Unitaires Python (`pytest`)** : `.venv/bin/pytest tests/unit/test_e2e_query_db_readonly.py tests/unit/test_e2e_stack_config.py tests/unit/test_uj_e2e_coverage_gate.py tests/unit/test_capabilities_registry.py -q` → `73 passed` (`41` dans `test_e2e_query_db_readonly.py`).
- **Qualité statique & Typage** :
  - `.venv/bin/ruff check infra/scripts tests/unit/test_e2e_query_db_readonly.py` : `All checks passed!`
  - `.venv/bin/ruff format --check infra/scripts/e2e/query_db.py tests/unit/test_e2e_query_db_readonly.py` : `2 files already formatted`
  - `MYPYPATH=infra/scripts/e2e .venv/bin/mypy --strict infra/scripts/e2e/query_db.py` : `Success: no issues found in 1 source file`
  - `tsc --noEmit` sur `apps/web/e2e/*.spec.ts` et `apps/web/e2e/support/*.ts` : `0` erreur.
  - `pnpm turbo run lint typecheck test` : `9 successful, 9 total` (`@orcia/web`: `38 passed`, `153 tests`).
  - `pnpm site:sync && pnpm site:check` : `[capabilities] 65/65 capacités live référencent au moins un test (0 sans test) · E2E fonctionnels: 26/62 · UJ: 20/20.` / `[site:check OK]`.
  - `gitnexus:detect_changes` (`repo: "/home/romain/Documents/Projects/ORCIA"`, `scope: "all"`) : `changed_count: 2`, `affected_count: 0`, `changed_files: 17`, `risk_level: "low"`.

### 3.3 Validation & Procédure de Test sur Toute la Pyramide (`AD-17` + Gouvernance Registre)
- **Couche 1a — Tests Unitaires Python (`pytest`)** : Validation complète de `validate_readonly_sql`, du garde-fou `orcia_e2e`, de la sérialisation JSON, de `SET TRANSACTION READ ONLY` et de la résolution d'état CLI (`73 passed`).
- **Couche 1b — Frontend TS (`Vitest` & `tsc --noEmit`)** : Validation complète de `pnpm turbo run lint typecheck test` (`9/9` tâches) et vérification TypeScript stricte de l'ensemble des `16` specs E2E et de leurs `7` modules support.
- **Couche Transverse — Gouvernance Registre (`pnpm site:check`)** : Toutes les `16` specs sont taguées `/** @uj ... | @cap ... */` et reconnues par `uj_e2e_coverage.py`.
- **Couche 5 (Exécution Playwright complète contre conteneurs PG18/Redis éphémères)** : Les `16` specs sont prêtes et équipées des assertions SQL et captures PNG pour la campagne d'exécution complète (`Story 21.8`).
