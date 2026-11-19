# Story 23.6a — Durcissement Anti-Goodhart : Gardes OpenAPI `security`, Audits AST (`catch` muets, constantes fantômes, SQL domaine, jargon), Contrats Géométriques Direction C & Reset PG18 Dynamique

> **Convention de nommage du fichier (Obligatoire — à créer AVANT toute modification de code)** :
> - User Story du sprint : `docs/implementation-artifacts/tech-lead-reports/{story-key}-tech-lead-report.md`

- **Date** : 2026-11-19
- **Story / Clé Sprint** : `23-6a-durcissement-anti-goodhart-gardes-openapi-ast-geometrie-et-reset-pg18` (`Epic 23` — Story intercalaire de durcissement Anti-Goodhart, prérequis bloquant `Story 23.7`)
- **Capacité(s)** : `CAP-100` (hygiène — fermeture structurelle des contournements de gardes CI/E2E, transport OpenAPI `security`, introspection SQL dynamique et contrats géométriques Direction C) — classification : `hygiène`
- **Auteur / Contexte** : `23.6a-doc-init` (Tech Lead `Amelia` × Architecte `Winston` × UX `Sally`, cadrage RCA Epic 22 — `AD-17`, `AD-19`, `NFR-TEST-1`, `DESIGN.md`, `GEMINI.md` §3). Story intercalaire insérée entre `23.5` et `23.7` suite au report de `Story 23.6` et du périmètre Mobile Companion (`--project=mobile-companion`, `390×844`, `CAP-042`) vers `action_items:` (`ACTION_ITEM-23.6`).
- **Commits associés** : `En attente d'implémentation (initialisé en Step 2a Epic 23)`

---

## 1. Analyse du Besoin & Étude d'Impact Tech Lead (Pré-Implémentation)

### 1.1 Contexte & Problématique
- **Leçon RCA Epic 22 — Fermeture des angles morts « Goodhart » entre pyramide locale (`AD-17`) et vérité E2E Desktop** :
  - Plusieurs incidents majeurs observés en Epic 22 (`3` rejets `HTTP 401` sur SSE sans `Bearer`, écrasement Zone 4 via `GENERAL_SECTIONS_FR` + `catch {}` silencieux, doublon `Accostage X/5` vs `X/6`, jargon technique et débordements visuels `TopHeaderBar` / `Cockpit`) ont traversé les gardes existants (`vitestFetchTransport`, `zero-dead-buttons-and-silent-catches-audit.test.tsx`, `test_e2e_sql_coverage_audit.py`, `anti-jargon-and-secrets-ui-audit.test.ts`, `layoutGeometryAssertions.ts`) à cause de failles structurelles ciblées :
    1. **Couche 2 (Reset Jour 0 PG18)** : `09_reset_db_first_boot.py` maintient une liste statique `ORDERED_MUTABLE_TABLES_TO_CLEAR` susceptible de désynchronisation lors de nouvelles migrations Alembic, et `reset_day0.py` ne vérifie pas dynamiquement via `information_schema.tables` et `pg_constraint` l'absence de tables orphelines ni l'état complet des triggers append-only, des tables `dbos.*`, de Redis (`DBSIZE == 0`) et des seeds socles (`connector_schemes`, `catalog_items`).
    2. **Couche 1b (`vitestFetchTransport` & appels réseau directs)** : `openApiRequestValidator.ts` (`validateRequestAgainstOpenApi`) valide aujourd'hui le chemin, la méthode, les paramètres et `requestBody`, mais ignore le champ `operation.security` de `packages/api-client/openapi.json`, laissant passer en test Vitest des appels authentifiés dépourvus d'en-tête `Authorization: Bearer <non-vide>` ; en parallèle, aucun verrou AST/ESLint n'empêche un ré-usage direct de `fetch(` ou `new EventSource(` dans `apps/web/src/**` ou `packages/api-client/src/domains/**` hors `createRequestJson` / `createRequestSse`.
    3. **Couche 1a/1b (Contournements Goodhart sur `catch`, constantes fantômes, SQL domaine et jargon)** :
       - Des `catch {}` sans paramètre / à corps vide ou `.catch(() => ...)` peuvent encore passer à côté d'une détection AST partielle sur `100 %` de `apps/web/src/**` ;
       - Des constantes de repli parallèles (`DEFAULT_HUMAN_PROFILE`, `GENERAL_SECTIONS_*`, compteurs d'accostage parallèles) peuvent réintroduire un *split-brain* UI vs PG18 ;
       - `tests/unit/test_e2e_sql_coverage_audit.py` se contente aujourd'hui de vérifier la présence lexicale d'un jeton (`expectDbRowExists`, `expectDbRowCount`, `queryDbRows`) par bloc `test(...)`, ce qui tolère les requêtes triviales (`SELECT 1`) ou hors domaine (`users` / `connector_schemes` sur des specs sans rapport avec l'IAM ou les connecteurs) ;
       - `anti-jargon-and-secrets-ui-audit.test.ts` liste des termes fixes (`FORBIDDEN_UI_TERMS`) sans regex structurelles attrapant les codes HTTP bruts (`HTTP 401`), versions de paquets (`@1.2.3`), chaînes de provenance (`BASE → PACK`), raccourcis clavier collés (`(Esc)`) ou identifiants `SCREAMING_SNAKE_CASE` multi-segments.
    4. **Couche 5 (Contrats géométriques & sobriété Direction C Desktop `1440×900`)** : `apps/web/e2e/support/layoutGeometryAssertions.ts` vérifie déjà le débordement horizontal, `elementFromPoint` et `[role="alert"]`, mais ne vérifie pas encore la sobriété `/cockpit <= 3` blocs, l'absence de troncature Zone 1 / Zone 2 / Accostage, l'unicité du sélecteur d'espace (`<= 1` visible), l'unicité du bouton annuler/fermer par dialog (`<= 1`), l'absence de `placeholder` contenant `•`, la fidélité de Zone 4 + `4` blocs `DESIGN.md` lors de la navigation `/cockpit -> /assistant -> /spaces`, ni la capture de jalons intermédiaires `< 440 KB` (`captureMilestoneScreenshot`).
- **Gouvernance d'exécution associée (RCA Epic 22)** :
  - Dépriorisation explicite de la `Story 23.6` et du périmètre `mobile-companion` (`390×844`, `CAP-042`) vers `ACTION_ITEM-23.6` (`sprint-status.yaml`) afin de concentrer l'Epic 23 sur la vérité Desktop (`--project=desktop-cockpit`, `1440×900`, `24` specs / `55` scénarios Desktop dont `52` exécutés et `3` `mobile-only` skipped).
  - Application systématique de l'**Étape 0 Réconciliation E2E ↔ `DESIGN.md`**, de la **Chaîne Canari Desktop Obligatoire** après chaque lot (`23.3`..`23.6a`) et du **Tir de reconnaissance Desktop V0** avant `Story 23.7`.

### 1.2 Exploration, Analyse d'Impact GitNexus, Factorisation & Dette Technique
- **Analyse d'Impact GitNexus (`repo: "/home/romain/Documents/Projects/ORCIA"`)** :
  - `createRequestSse` (`packages/api-client/src/helpers.ts`) : **`impactedCount: 130`**, risque **`CRITICAL`** (`direct: 117`, `d=2: 11`, `d=3: 2`, `processes_affected: 65`, `modules_affected: 16`) — prouve la criticité d'interdire tout contournement `fetch(` / `new EventSource(` en dehors de `packages/api-client/src/helpers.ts`.
  - Les sondes `gitnexus_context` / `gitnexus_impact` sur `vitestFetchTransport` (`apps/web/src/__tests__/setup/transportAndOpenApiValidator.ts`), `validateRequestAgainstOpenApi` (`apps/web/src/__tests__/setup/openApiRequestValidator.ts`), `captureFinalState` (`apps/web/e2e/support/e2eCaptureFixture.ts`) et `reset_day0_database` / `reset_db_first_boot` confirment que les harnais `__tests__/setup/`, `e2e/support/` et `infra/scripts/` ne sont pas indexés comme nœuds appelables dans le graphe GitNexus. L'étude d'impact a été complétée par inspection directe des fichiers :
    - `apps/web/src/__tests__/setup/transportAndOpenApiValidator.ts` (`L21-L172`) & `openApiRequestValidator.ts` (`L223-L318`) : point d'entrée unique du transport Vitest *fail-closed*, complété par la vérification `op.security` + headers.
    - `apps/web/e2e/support/layoutGeometryAssertions.ts` (`L1-L223`) & `e2eCaptureFixture.ts` (`L1-L144`) : socle partagé d'assertions E2E (DRY) prêt à recevoir les contrats géométriques Direction C et `captureMilestoneScreenshot` (`< 440 KB`).
    - `infra/scripts/e2e/reset_day0.py` (`L1-L214`) & `infra/scripts/maintenance/09_reset_db_first_boot.py` (`L1-L329`) : gouvernance du Reset Jour 0 sous contrainte stricte zéro `DISABLE TRIGGER`.
    - `tests/unit/test_e2e_sql_coverage_audit.py` (`L1-L39`), `apps/web/src/__tests__/zero-dead-buttons-and-silent-catches-audit.test.tsx` (`L1-L253`) & `anti-jargon-and-secrets-ui-audit.test.ts` (`L1-L130`) : gardes statiques/AST ciblés à durcir.
- **Opportunités de factorisation & contrôle de volumétrie (`<= 350` L)** :
  - Maintenir chaque module sous `apps/web/src/__tests__/setup/` et `apps/web/e2e/support/` strictement sous `350` lignes (extraire un module dédié si `layoutGeometryAssertions.ts` ou `openApiRequestValidator.ts` dépasse `320`–`350` lignes).
  - Mutualiser le parseur AST TypeScript (ou Babel/TypeScript Compiler API déjà disponible dans le workspace) dans les audits `apps/web/src/__tests__/` plutôt que des regex fragiles.

---

## 2. Plan d'Implémentation

### 2.1 Schéma de Données & Migrations Alembic (`infra/migrations/versions/`)
- Aucune nouvelle migration Alembic requise.
- **Verrou Couche 2 — Introspection SQL dynamique `information_schema.tables` & `pg_constraint` du Reset Jour 0** :
  - Dans `infra/scripts/maintenance/09_reset_db_first_boot.py` et `infra/scripts/e2e/reset_day0.py`, vérifier dynamiquement contre `information_schema.tables` (`table_schema = 'public'`) et `pg_constraint` qu'aucune table créée par Alembic n'est absente de la stratégie de purge/protection (zéro table Alembic orpheline), que les chaînes FK `ON DELETE RESTRICT` et les triggers append-only (`audit_ledger`, `blackboard_snapshots`) restent actifs (`0` `DISABLE TRIGGER`), que `dbos.*` est nettoyé, que Redis atteint `DBSIZE == 0`, et que les seeds socles `connector_schemes` & `catalog_items` restent intacts.
  - Ajouter les tests unitaires + intégration `testcontainers` PG18 + Redis correspondants dans `tests/unit/test_e2e_reset_day0_guard.py` et `tests/integration/test_e2e_reset_day0_postgres18_and_redis.py`.

### 2.2 Noyau Métier Hexagonal, Audits AST Python & Garde SQL Domaine (`tests/unit/`)
- **Verrou Couche 1a — Durcissement AST de `tests/unit/test_e2e_sql_coverage_audit.py`** :
  - Remplacer le contrôle purement lexical par une analyse structurée des appels `expectDbRowExists(...)`, `expectDbRowCount(...)` et `queryDbRows(...)` dans chacun des `55` blocs `test(...)` répartis sur les `24` specs E2E (`apps/web/e2e/*.spec.ts`).
  - Interdire explicitement les requêtes triviales (`SELECT 1`, `SELECT COUNT(*) FROM connector_schemes` hors spec connecteurs) et les tables hors domaine (`users` / `connector_schemes` utilisées comme alibi sur des specs non-IAM/non-connecteurs), en exigeant pour chaque bloc `test(...)` au moins une requête ciblant une table PostgreSQL 18 réelle du domaine métier de la spec.
  - Mettre à niveau toute spec E2E (`00`..`21`, `shell`) qui présenterait encore une assertion SQL alibi.

### 2.3 Couche Backend API, Contrats OpenAPI & Transport Vitest (`packages/api-client/`, `apps/web/src/__tests__/`)
- **Verrou Couche 1b — Application de `operation.security` & interdiction AST de `fetch(` / `new EventSource(`** :
  - Étendre `openApiRequestValidator.ts` / `transportAndOpenApiValidator.ts` pour lire `operation.security` (et la sécurité globale) dans `packages/api-client/openapi.json` : toute route protégée appelée sans en-tête `Authorization: Bearer <token-non-vide>` retourne immédiatement une erreur `HTTP 401` au format `application/problem+json` (RFC 9457) au lieu de passer silencieusement.
  - Compléter `apps/web/src/__tests__/vitest-transport-fail-closed-openapi.test.ts` pour prouver le rejet `HTTP 401 application/problem+json` sans `Bearer` et l'acceptation avec `Bearer` valide.
  - Ajouter un audit AST (et/ou règle ESLint) interdisant tout appel direct à `fetch(` et `new EventSource(` dans `apps/web/src/**` (hors `__tests__/`) ainsi que dans `packages/api-client/src/domains/**` (seul `packages/api-client/src/helpers.ts` étant autorisé à encapsuler le transport).

### 2.4 Interface Utilisateur, Audits AST Frontend & Contrats Géométriques Direction C (`apps/web/src/__tests__/`, `apps/web/e2e/`)
- **Verrou Couche 1b — Fermeture des contournements Goodhart Frontend** :
  1. **AST `catch` muets & constantes fantômes** (`apps/web/src/__tests__/zero-dead-buttons-and-silent-catches-audit.test.tsx`) : scanner `100 %` de `apps/web/src/**` (hors `__tests__/`) via l'AST TypeScript pour rejeter tout `catch {}` sans paramètre ou à corps vide/commentaire seul, tout `.catch(() => ...)` muet sans propagation/journalisation/alerte UI, ainsi que toute réintroduction des constantes fantômes (`DEFAULT_HUMAN_PROFILE`, `GENERAL_SECTIONS_*`, compteurs d'accostage parallèles).
  2. **Regex structurelles anti-jargon** (`apps/web/src/__tests__/anti-jargon-and-secrets-ui-audit.test.ts`) : ajouter des expressions régulières structurelles détectant `\bHTTP\s+[45]\d\d\b`, `@\d+\.\d+\.\d+`, `\b[A-Z]{3,}\s*→\s*[A-Z]{3,}\b`, `\(Esc\)` et `SCREAMING_SNAKE_CASE` multi-segments dans les libellés UI visibles (`i18n/locales`, `docs/help/`, composants aide).
- **Verrou Couche 5 — Contrats géométriques & sobriété Direction C Desktop (`1440×900`)** :
  - Enrichir `apps/web/e2e/support/layoutGeometryAssertions.ts` (ou un module frère `< 350` L réexporté) et `e2eCaptureFixture.ts` :
    - Vérification `/cockpit <= 3` blocs visuels distincts ;
    - Zéro troncature (`scrollWidth <= clientWidth` / `ellipsis` involontaire) sur Zone 1 (`four-zone-sidebar`), Zone 2 (`four-zone-top-header-bar`) et la bannière `Accostage X/6` ;
    - `<= 1` sélecteur d'espace visible sur Desktop ;
    - `<= 1` bouton annuler/fermer par dialog ouvert ;
    - Zéro `input[placeholder]` contenant `•` ;
    - Vérification de changement effectif du contenu Zone 4 (`four-zone-help-aside`) + présence des `4` blocs `DESIGN.md` lors de la navigation `/cockpit -> /assistant -> /spaces` ;
    - Helper `captureMilestoneScreenshot(page, testInfo, stepName)` respectant strictement la limite `< 440 KB` (`MAX_SCREENSHOT_BYTES`).
  - Brancher ces assertions géométriques et de sobriété sur `apps/web/e2e/shell.spec.ts` et `apps/web/e2e/11-screens-smoke-without-server-errors.spec.ts`.
  - **Étape 0 Réconciliation E2E ↔ `DESIGN.md` & Chaîne Canari Desktop Obligatoire (`--project=desktop-cockpit`)** :
    - Exécuter la Chaîne Canari Desktop (`00`, `01`, `02`, `03`, `04`, `11`, `12-epic16`, `shell.spec.ts` sous `--project=desktop-cockpit`) + le **Tir de reconnaissance Desktop V0** sur les `24` specs / `55` scénarios Desktop (`--project=desktop-cockpit`) afin de vérifier l'intégralité de la pile avant `Story 23.7`.

### 2.5 Analyse d'Impact sur la Pyramide des Tests (`AD-17` — Couches 1 à 5 + Sécurité, Obligatoire)
- **Couche 1a (`pytest`)** : `test_e2e_reset_day0_guard.py`, `test_e2e_sql_coverage_audit.py`, `test_epic22_to_epic23_traceability.py`, couverture `>= 90 %`.
- **Couche 1b (`Vitest`)** : `vitest-transport-fail-closed-openapi.test.ts`, `zero-dead-buttons-and-silent-catches-audit.test.tsx`, `anti-jargon-and-secrets-ui-audit.test.ts`, audit AST `fetch(`/`new EventSource(`.
- **Couche 2 (`testcontainers` PG18 + Redis)** : `test_e2e_reset_day0_postgres18_and_redis.py` prouvant introspection dynamique `information_schema.tables` & `pg_constraint`, triggers append-only actifs, `dbos.*`, Redis `DBSIZE == 0` et seeds `connector_schemes` / `catalog_items` intacts.
- **Couche 3 (`lint-imports`, `openapi`, `site:check`)** : `ruff`, `mypy --strict`, `lint-imports`, `export_openapi.py --check`, `check_implementation_docs.py`, `pnpm turbo run lint typecheck test`, `pnpm site:sync && pnpm site:check`.
- **Couche 5 (Playwright Desktop `--project=desktop-cockpit`)** : Chaîne Canari Desktop + `shell.spec.ts` + `11-screens-smoke-without-server-errors.spec.ts` + Tir de reconnaissance Desktop V0 (`24` specs / `55` scénarios Desktop).

---

## 3. Bilan des Modifications & Résultats (Post-Implémentation)

> *[En attente d'implémentation — Sections 1 & 2 initialisées en Step 2a Epic 23]*

### 3.1 Fichiers Développés & Modifiés
| Fichier | Nature (Création / Modification / Refactoring) | Description synthétique |
| :--- | :--- | :--- |
| `infra/scripts/{e2e/reset_day0.py,maintenance/09_reset_db_first_boot.py}` | Modification | *[À compléter : verrou Couche 2 introspection dynamique `information_schema.tables` & `pg_constraint`]* |
| `apps/web/src/__tests__/{setup/*,vitest-transport-fail-closed-openapi.test.ts,zero-dead-buttons-and-silent-catches-audit.test.tsx,anti-jargon-and-secrets-ui-audit.test.ts}` | Modification / Création | *[À compléter : verrous Couche 1b `operation.security`, AST `fetch`/`EventSource`, `catch` muets, constantes fantômes, regex jargon]* |
| `tests/unit/test_e2e_sql_coverage_audit.py` & `apps/web/e2e/**` | Modification | *[À compléter : verrou Couche 1a SQL domaine + verrou Couche 5 `layoutGeometryAssertions.ts` & `captureMilestoneScreenshot`]* |

### 3.2 Résultats Chiffrés, Métriques & Qualité
- **Couverture de tests** : *[À compléter après exécution de `Story 23.6a` ($\ge 90\%$ requis)]*
- **Qualité statique & Architecture** : *[À compléter : `ruff`, `mypy --strict`, `lint-imports`, `pnpm turbo run lint typecheck test`, `pnpm site:check`]*

### 3.3 Validation & Procédure de Test sur Toute la Pyramide (`AD-17` + 5 Garde-Fous de Câblage Vertical)
- *[À compléter après validation complète des 4 verrous structurels, de la Chaîne Canari Desktop et du Tir de reconnaissance Desktop V0 avant lancement de `Story 23.7`]*
