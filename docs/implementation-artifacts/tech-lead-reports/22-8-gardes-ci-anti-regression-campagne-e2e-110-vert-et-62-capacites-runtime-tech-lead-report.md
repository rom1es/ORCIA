# Story 22.8 — Activation des 5 Gardes CI Anti-Régression, Couverture `100 %` Assertions SQL PG18 sur `55` Blocs `test(...)` E2E, Paramétrage `ORCIA_E2E_CAMPAIGN_DIR` & Budget `< 35s`

> **Convention de nommage du fichier (Obligatoire — à créer AVANT toute modification de code)** :
> - User Story du sprint : `docs/implementation-artifacts/tech-lead-reports/{story-key}-tech-lead-report.md`

- **Date** : 2026-11-18
- **Story / Clé Sprint** : `22-8-gardes-ci-anti-regression-campagne-e2e-110-vert-et-62-capacites-runtime` (`Epic 22` — Vague 3 / Clôture Technique & Gardes) *(clé sprint conservée pour traçabilité avec `capabilities.yaml` et `test_epic21_to_epic22_traceability.py` ; l'assainissement Fail-Closed de `vitest.setup.ts`, le test Composition Root sans override et la CI GitHub Actions complète sont portés par la Story intercalaire `22.8a`, la campagne E2E intégrale + captures PNG + audit croisé Sally × Winston + mise à jour `capabilities.yaml` par `Story 22.9`, et les rapports Tech Lead + initialisation Epic 23 par `Story 22.10`)*
- **Capacité(s)** : `CAP-100` (hygiène CI transverse, verrous anti-faux-positifs E2E/Vitest, purge `ORCIA_E2E_SEED_FIXTURES` + relecture à froid PG18 et couverture SQL E2E `100 %` préparant `Story 22.8a` puis `Story 22.9`) — classification : `hygiène`
- **Auteur / Contexte** : `bmad-architect-worker` (initialisation Story 21.9, recalibrée Story 22.0, enrichie suite RCA Epic 21 le 2026-11-18) — Résolution des chantiers **`REM-33`** et **`REM-34`** (`synthese-remediation-sally-winston-epic-21.md`, `notes-audit-winston-architecture.md` § 3.5, `2026-11-18-rca-epic-21-enrichissement-22-8-et-story-22-8a-tech-lead-report.md`). Couvre `AD-17`, `NFR-TEST-1`, `NFR-PERF-1`, `NFR-A11Y-1`, `GEMINI.md` §5.
- **Commits associés** : `En attente d'implémentation (initialisé sur 575cf4a)`

---

## 1. Analyse du Besoin & Étude d'Impact Tech Lead (Pré-Implémentation)

### 1.1 Contexte & Problématique
- **Budget temps E2E sur parcours multi-étapes (`REM-33`)** :
  - `14-auth` #2 (Desktop + Mobile) et `16-ai-models` #2 (Desktop) atteignaient le plafond `35 000 ms` principalement à cause de l'obstruction Zone 4 sur `UserSettingsModalDialog` et de séquences d'attentes cumulées. Après `REM-03` (`22-2`), il faut re-mesurer et optimiser les parcours sous `< 35 s` avec marge confortable (`< 20 s` visé).
- **Absence des 5 gardes automatisées anti-régression (`REM-34`)** :
  - L'audit Epic 21 a montré que plusieurs défauts majeurs (`PASSED` faussement verts) passaient la CI actuelle :
    1. Fuites de jargon technique dans les dictionnaires `i18n`, `_contextualHelpSections.ts` et `docs/help/`.
    2. Montage toxique de panneaux cachés via `style={{ display: "none" }}` (permettant à `zero-dead-buttons` de rester vert malgré des écrans vides/dupliqués).
    3. Utilisation de classes Tailwind v4 non compilées (`tokens.css` sans `@tailwindcss/vite`).
    4. Fuites de balises internes `[LAYER_5_*]` dans les schémas/streams UI et maintien du drapeau `ORCIA_DISABLE_PG_BOOTSTRAP_SYNC`.
    5. Débordements mobiles masqués par `overflow-x: hidden` sur `html/body` (faux positifs `scrollWidth <= innerWidth` sur `05-mobile-companion` et `12-finops`) et superposition de Zone 4 sur les modales.
- **Généralisation des assertions SQL PostgreSQL 18 à `100 %` des `55` blocs `test(...)` E2E & Paramétrage Campagne (`Story 22.8`)** :
  - Certaines specs E2E héritées ne vérifiaient pas encore par `SELECT` PostgreSQL 18 (`queryPgCount`/`queryPgRows`) que l'état persisté existe en base. La Story `22.8` complète les assertions PG18 sur **100 % des `55` blocs `test(...)` (`110` scénarios Desktop + Mobile)** et verrouille cette exigence par un test statique `tests/unit/test_e2e_sql_coverage_audit.py`.
  - `apps/web/e2e/support/e2eCaptureFixture.ts` est paramétré via `ORCIA_E2E_CAMPAIGN_DIR` (ciblant `docs/implementation-artifacts/e2e-campaign-epic-22` sans écraser les preuves historiques `e2e-campaign-epic-21`).
- **Séparation claire `22.8` → `22.8a` → `22.9` → `22.10`** :
  - **`Story 22.8`** : activation des `5` gardes CI initiales + **`4` verrous anti-faux-positifs** (sync `data-testid` E2E↔UI, helper Playwright typé OpenAPI, purge `ORCIA_E2E_SEED_FIXTURES="1"` + relecture à froid PG18 `reloadColdFromPg` via `/api/v1/_e2e/evict-memory-caches`, réécriture `<RouterProvider>` de `zero-dead-buttons` + sonde `[role="alert"]` + Direction C / WCAG AA), couverture `100 %` assertions SQL PG18 sur les `55` blocs `test(...)` E2E + `test_e2e_sql_coverage_audit.py`, paramétrage `ORCIA_E2E_CAMPAIGN_DIR` et optimisation `< 35 s`.
  - **`Story 22.8a` (intercalaire)** : assainissement *Fail-Closed* de `apps/web/src/__tests__/vitest.setup.ts` (`< 350` L, validation contre `openapi.json`, suppression `return jsonResponse({})`), élimination des fallbacks RAM résiduels + test Composition Root `create_app()` sans `dependency_overrides` ni injection `app.state.*`, et pipeline CI GitHub Actions complet à `5` couches (`AD-17`).
  - **`Story 22.9`** : exécution intégrale de la campagne Playwright E2E (`110` scénarios), archivage PNG (`e2e-campaign-epic-22`), bilan, audit croisé **Sally × Winston** et mise à jour honnête de `docs/product/capabilities.yaml`.
  - **`Story 22.10`** : rapports Tech Lead individuels (`23-1..23-N`), plan de correction global et initialisation complète de l'**Epic 23**.

### 1.2 Exploration, Analyse d'Impact GitNexus, Factorisation & Dette Technique
- **Périmètre des `5` Gardes CI + Garde Couverture SQL E2E + `4` Verrous Anti-Faux-Positifs** :
  1. `apps/web/src/__tests__/anti-jargon-and-secrets-ui-audit.test.ts` (scan `i18n/locales/*.ts`, `_contextualHelpSections.ts`, `packages/ui/src/**`, `docs/help/**/*.md`, `packs/**/help/**/*.md`).
  2. `apps/web/src/__tests__/no-hidden-legacy-panels-audit.test.ts` (interdiction `display: none` / `className="hidden"` sur panneaux métier + vérification que chaque `role="dialog"` passe par `Portal`).
  3. `apps/web/src/__tests__/css-class-integrity-audit.test.ts` (vérification `@tailwindcss/vite` + cohérence classes `tokens.css` + tokens Direction C / contraste WCAG AA sans hex codé en dur).
  4. `tests/unit/test_no_raw_enum_codes_in_ui_streams.py` (zéro `[LAYER_5_*]` ou code brut dans les champs UI des schémas/streams + interdiction `ORCIA_DISABLE_PG_BOOTSTRAP_SYNC` hors tests unitaires).
  5. `apps/web/e2e/support/layoutGeometryAssertions.ts` (helper Playwright géométrique `rect.right <= window.innerWidth + 1` & `elementFromPoint` sur modales ouvertes + vérification absence d'overflow texte / WCAG AA).
  6. `tests/unit/test_e2e_sql_coverage_audit.py` (audit statique garantissant que `100 %` des `55` blocs `test(...)` de `apps/web/e2e/*.spec.ts` comportent une assertion SQL PostgreSQL 18 via `dbAssertions.ts`).
  7. `apps/web/src/__tests__/e2e-testids-sync-audit.test.ts` (**Verrou 1** — vérifie que `100 %` des `data-testid` interrogés dans `apps/web/e2e/*.spec.ts` existent dans `apps/web/src/` ou `packages/ui/src/`).
  8. `apps/web/e2e/support/typedApiRequest.ts` + `apps/web/src/__tests__/e2e-openapi-helper-audit.test.ts` (**Verrou 2** — helper Playwright typé via `@orcia/api-client` / `paths` OpenAPI et interdiction de `page.request.post/put/patch` bruts non typés dans `apps/web/e2e/*.spec.ts`).
  9. Purge totale de `ORCIA_E2E_SEED_FIXTURES="1"` dans `apps/web/playwright.config.ts` / `apps/web/e2e/` + helper `reloadColdFromPg()` adossé à `POST /api/v1/_e2e/evict-memory-caches` (`ORCIA_ENV == "e2e"` uniquement) (**Verrou 3** — preuve de persistance à froid en PG18 sans cache RAM ni fixture pré-injectée).
  10. Réécriture anti-Goodhart de `apps/web/src/__tests__/zero-dead-buttons-and-silent-catches-audit.test.tsx` (montage via `<RouterProvider>` réel au lieu d'un faux neutre) + sonde `[role="alert"]` sur réponses HTTP `>= 400` dans `apps/web/e2e/support/` (**Verrou 4**).
- **Analyse d'impact GitNexus (`repo: "/home/romain/Documents/Projects/ORCIA"`) & Inventaire pré-implémentation** :
  - `gitnexus_query` (`ORCIA_E2E_SEED_FIXTURES e2eCaptureFixture build_api_env initialize_app_services`) et `gitnexus_context` (`list_inbox_notifications` dans `apps/api/src/orcia_api/routers/inbox_and_leases.py:L135-170`) : confirment que `inbox_and_leases.py` et `core_and_lifespan.py` sont les deux seuls points applicatifs injectant des notifications/personas fictives sous `ORCIA_E2E_SEED_FIXTURES=1`, alimentés par `infra/scripts/e2e/e2e_stack_config.py:L76`.
  - `gitnexus_impact({target: "create_app", direction: "upstream"})` : `impactedCount: 235` (`CRITICAL`, `77` processus, `14` modules), imposant de garder `create_app()` léger, d'exposer le routeur `_e2e` en mode `APIRouter(prefix="/api/v1/_e2e")` avec `ResourceNotFoundError` (RFC 9457 `404`) si `ORCIA_ENV != "e2e"` afin de préserver la conformité `Schemathesis` (`tests/contract/test_openapi_contract.py`), et de déclarer `e2e_test_hooks.py` sur `CAP-100` dans `docs/product/capabilities.yaml`.
  - **Audit `ORCIA_E2E_SEED_FIXTURES` & impersonation** : `infra/scripts/e2e/e2e_stack_config.py` passe `ORCIA_ENV="e2e"` (désactivant toute impersonation `persona_key` car `persona_impersonation_allowed("e2e") == False`) sans `ORCIA_E2E_SEED_FIXTURES`. Les specs `04-multi-actor-claim-sse.spec.ts` et `15-organization-iam-secops-inbox-and-observer.spec.ts` (#4) créent leurs acteurs et notifications via les vraies API authentifiées (`POST /api/v1/bootstrap/welcome-setup/first-admin`, `POST /api/v1/settings/iam/accounts`, `POST /api/v1/auth/login/local`, `POST /api/v1/runs/{run_id}/steps/{step_id}/claim` + `release`).
  - **Audit couverture SQL PG18 (`55` blocs `test(...)` dans `24` specs)** : `17` blocs sans assertion SQL directe identifiés (`00` #1/#2/#3, `04` #2, `05` #1/#2, `10` #1/#2, `11` #1/#2, `12-finops` #2, `13` #2, `15` #3, `shell.spec.ts` #1/#2/#3/#4) + renforcement `02` #1 (`assistant_threads` / `audit_ledger`).
- **Facteur de succès clé** : exécuter cette Story **uniquement après achèvement et validation des Stories `22.1` à `22.7`** afin que les gardes et verrous passent immédiatement sans faux positifs et préparent `Story 22.8a` puis l'exécution de la campagne intégrale en `Story 22.9`.

---

## 2. Plan d'Implémentation

### 2.1 Schéma de Données & Migrations Alembic (`infra/migrations/versions/`)
- Vérification finale de la chaîne Alembic `0001` $\rightarrow$ `head` (test `upgrade()` / `downgrade()` + `pnpm db:reset` Jour 0 à `0` utilisateur).

### 2.2 Noyau Métier Hexagonal, Orchestration & Workers (`packages/orcia-core/`, `apps/worker/`)
- Garde CI Python `tests/unit/test_no_raw_enum_codes_in_ui_streams.py` vérifiant :
  - Absence totale d'occurrences de `ORCIA_DISABLE_PG_BOOTSTRAP_SYNC` dans `apps/` et `packages/` ;
  - Absence de marqueurs `[LAYER_5_*]` dans les DTOs / schémas UI de `apps/api/src/orcia_api/schemas/` et les adaptateurs de streaming SSE.
- Garde statique `tests/unit/test_e2e_sql_coverage_audit.py` vérifiant la présence effective d'assertions `SELECT` PostgreSQL 18 (`queryPgCount` / `queryPgRows`) dans `55/55` blocs `test(...)` E2E.

### 2.3 Couche Backend API, Sécurité & Contrats (`apps/api/`, `packages/api-client/`)
- Exposition conditionnelle (`ORCIA_ENV == "e2e"` uniquement, refus `HTTP 404` en `dev`/`prod`) de `POST /api/v1/_e2e/evict-memory-caches` dans `apps/api` pour permettre aux tests Playwright (`reloadColdFromPg`) d'évincer tout cache applicatif en mémoire et de prouver la relecture à froid depuis PostgreSQL 18.
- Vérification de l'absence totale de `ORCIA_E2E_SEED_FIXTURES` dans `apps/web/playwright.config.ts` et dans l'amorçage E2E : tout jeu de test E2E crée ses entités via les API réelles authentifiées (`typedApiRequest.ts`).
- Exécution complète de la couche 3 (`openapi-typescript` `0-diff`, `Schemathesis`, `lint-imports` `5 contracts kept, 0 broken`) et de la couche Sécurité (`tests/security/`).

### 2.4 Interface Utilisateur & Expérience (`packages/ui/`, `apps/web/`)
- Activation des `3` audits statiques Vitest (`anti-jargon-and-secrets-ui-audit.test.ts`, `no-hidden-legacy-panels-audit.test.ts`, `css-class-integrity-audit.test.ts`) + `2` nouveaux verrous statiques (`e2e-testids-sync-audit.test.ts`, `e2e-openapi-helper-audit.test.ts`) et réécriture anti-Goodhart de `zero-dead-buttons-and-silent-catches-audit.test.tsx` avec `<RouterProvider>`.
- Déploiement du helper Playwright `layoutGeometryAssertions.ts` dans `05-mobile-companion`, `12-finops`, `14-auth`, `16-ai-models` et les specs de modales/mobile (`rect.right <= window.innerWidth + 1`, `elementFromPoint`, contrôle Direction C / contraste WCAG AA), plus sonde `[role="alert"]` sur toute réponse API `>= 400` en E2E.
- Paramétrage de `ORCIA_E2E_CAMPAIGN_DIR` dans `apps/web/e2e/support/e2eCaptureFixture.ts` (valeur par défaut ou override vers `docs/implementation-artifacts/e2e-campaign-epic-22`) et utilisation obligatoire de `typedApiRequest.ts` + `reloadColdFromPg()`.
- Complétion des assertions `SELECT` PostgreSQL 18 sur l'ensemble des `55` blocs `test(...)` des `24` specs Playwright.
- Optimisation des séquences E2E `14-auth` #2 et `16-ai-models` #2 sous `< 35 s` (`REM-33`).

### 2.5 Analyse d'Impact sur la Pyramide des Tests (`AD-17` — Couches 1 à 5 + Sécurité, Obligatoire)
- **Couche 1a / 1b** : `.venv/bin/pytest --cov=packages/orcia-kernel --cov=packages/orcia-core --cov-fail-under=90` (incluant `test_no_raw_enum_codes_in_ui_streams.py`, `test_e2e_sql_coverage_audit.py` et test du endpoint `_e2e/evict-memory-caches` actif uniquement en `ORCIA_ENV=e2e`) + `pnpm turbo run lint typecheck test`.
- **Couche 2 (`testcontainers` PG18 / Redis / SeaweedFS)** : suite d'intégration complète verte.
- **Couche 3 (`OpenAPI 0-diff`, `Schemathesis`, `lint-imports`, `lint_spine.py`)** : `0` anomalie.
- **Couche 4 (Evals `0 $`) & Couche Sécurité (`tests/security/`)** : `100 %` vert.
- **Couche 5 (Préparation Campagne `Story 22.9` après `Story 22.8a`)** : tests ciblés `tsc --noEmit`, specs optimisées `14-auth` et `16-ai-models` sous `< 35 s`, purge confirmée de `ORCIA_E2E_SEED_FIXTURES`, et validation du harnais `ORCIA_E2E_CAMPAIGN_DIR` avant `Story 22.8a` puis `Story 22.9`.

---

## 3. Bilan des Modifications & Résultats (Post-Implémentation)

### 3.1 Fichiers Développés & Modifiés
| Fichier | Nature (Création / Modification / Refactoring) | Description synthétique |
| :--- | :--- | :--- |
| `apps/web/src/__tests__/anti-jargon-and-secrets-ui-audit.test.ts` | Création | Garde anti-jargon & anti-fuites (`SYNTHESIS_READY`, `Chef1`, `[LAYER_5_`, `ORCIA_BOOTSTRAP_TOKEN`, etc.) sur dictionnaires i18n, aide contextuelle, `docs/help/**`, `packs/**/help/**` et `packages/ui/src/**`. |
| `apps/web/src/__tests__/no-hidden-legacy-panels-audit.test.ts` | Création | Garde garantissant `0` `display: none` dans `apps/web/src` & `packages/ui/src` et `100 %` des `role="dialog"` portalisés via `OrciaDialog` / `DialogPrimitive.Portal`. |
| `apps/web/src/__tests__/css-class-integrity-audit.test.ts` | Création | Garde vérifiant `@theme inline` (`viteTailwindV4Plugin.ts`), la compilation des classes critiques (`.z-50`, `.h-[580px]`, `.max-w-[820px]`, `.pl-5`, `.grid-cols-1`), tokens `--z-overlay`/`--z-dialog`, absence de `#hex` hors `tokens.css` et exclusivité `#6D28D9` pour `HumanLedAnchorCard`. |
| `apps/web/src/__tests__/e2e-testids-sync-audit.test.ts` | Création | **Verrou 1** : extraction de `100 %` des `getByTestId(...)` et `[data-testid=...]` E2E et vérification de leur présence effective (ou préfixe dynamique explicite) dans `apps/web/src` & `packages/ui/src`. |
| `apps/web/src/__tests__/e2e-openapi-helper-audit.test.ts` & `apps/web/e2e/support/typedApiRequest.ts` | Création | **Verrou 2** + client typé `@orcia/api-client` (`openapi-fetch`) interdisant tout appel `page.request.*` / `request.*` brut et toute référence à `ORCIA_E2E_SEED_FIXTURES` dans `apps/web/e2e/**`. |
| `apps/web/src/__tests__/zero-dead-buttons-and-silent-catches-audit.test.tsx` | Modification (Refactoring) | **Verrou 4** : réécriture anti-Goodhart sous `<RouterProvider>` réel (`createMemoryHistory` sur 10 routes), `0` bouton muet, `0` `.catch(() => undefined)`, `count === 1` et vérification `[role="alert"]` sur erreur HTTP simulée. |
| `tests/unit/test_no_raw_enum_codes_in_ui_streams.py` & `tests/unit/test_e2e_sql_coverage_audit.py` | Création | Gardes Python : `0` `ORCIA_DISABLE_PG_BOOTSTRAP_SYNC`, `0` `ORCIA_E2E_SEED_FIXTURES`, `0` `[LAYER_5_*]` exposé, contrôle `_e2e/evict-memory-caches` (`404` hors `e2e` / `200` en `e2e`), et couverture SQL PG18 sur **`55/55` blocs `test(...)`** (`24` specs). |
| `apps/api/src/orcia_api/routers/e2e_test_hooks.py`, `schemas/e2e_test_hooks.py`, `main.py`, `dependencies/core_and_lifespan.py`, `packages/api-client/src/generated/e2e_test_hooks.ts` | Création / Modification | Endpoint `POST /api/v1/_e2e/evict-memory-caches` monté uniquement quand `ORCIA_ENV == "e2e"` + régénération OpenAPI `0-diff` (`export_openapi.py`). |
| `apps/web/e2e/support/{coldReload.ts,layoutGeometryAssertions.ts,authAndOrgHelpers.ts,firstAdmin.ts,dbAssertions.ts,e2eCaptureFixture.ts}` & `apps/web/e2e/*.spec.ts` (`24` specs) | Création / Modification | **Verrou 3** (`reloadColdFromPg` sans `ORCIA_E2E_SEED_FIXTURES`), assertions géométriques/visibilité, assertions SQL PG18 sur `55/55` tests, `ORCIA_E2E_CAMPAIGN_DIR` et optimisation `14-auth` / `16-ai-models` sous `< 35 s`. |
| `packages/ui/src/primitives/{AssistantGovernanceModalAndStudio,ChunkValidationCard,FourZoneDirectionCShell,FourZoneNotificationsDrawer,FourZoneShellTypes,MobileCompanionBottomBar,SidebarAccountPopover,TopHeaderSearchCommand}.tsx` & `apps/web/src/...` | Modification / Refactoring | Portalisation Radix des `6` modales/tiroirs restants, auto-fermeture du tiroir mobile à la navigation/modale, suppression de `2` `display: none` dans `WorkspaceSourcesMasterTable.tsx`, montage racine de `ShellUserSettingsModal.tsx`, `@theme inline` (`viteTailwindV4Plugin.ts` / `main.tsx`), affichage `[role="alert"]` SSRF (`SettingsAiModelsSection.tsx`) et wrap mobile (`EnterpriseConnectorsSettingsSection.tsx`). |

### 3.2 Résultats Chiffrés, Métriques & Qualité
- **Pyramide Python (`tests/unit`, `tests/security`, `tests/evals`)** : **`883 passed`** (`0` échec, `0` skipped) après les dernières modifications, incluant `test_no_raw_enum_codes_in_ui_streams.py` & `test_e2e_sql_coverage_audit.py` (`24` specs, **`55/55` blocs `test(...)`** avec assertion SQL PG18).
- **Suite TypeScript (`pnpm turbo run lint typecheck test --force`)** : **`9/9` tâches réussies** (`0` erreur `tsc --noEmit` / ESLint) :
  - `@orcia/ui` : `26` fichiers, **`110 passed`**
  - `@orcia/api-client` : `2` fichiers, **`13 passed`**
  - `@orcia/web` : `50` fichiers, **`185 passed`** (incluant les `6` fichiers de gardes et verrous CI).
- **Tir Playwright Ciblé de Validation (`--retries=0 --timeout=35000`, PG18 + Redis réels, sans `ORCIA_E2E_SEED_FIXTURES`, `ORCIA_E2E_CAMPAIGN_DIR=/tmp/orcia-e2e-22-8-check` puis nettoyé)** : **`17 passed, 3 skipped (3.1m), 0 failed`** sur `04-multi-actor-claim-sse`, `05-mobile-companion-and-rgaa`, `14-auth-2fa-account-and-profile` et `16-ai-models-reindex-connectors-and-broker` (skips uniquement sur gardes desktop-only / mobile-only prévues dans `04` et `05`) :
  - `14-auth` #1 : `13.1 s` (desktop) / `11.2 s` (mobile)
  - **`14-auth` #2 (`REM-33`) : `11.4 s` (desktop) / `10.9 s` (mobile)** (`< 35 000 ms`)
  - `14-auth` #3 : `10.9 s` (desktop) / `11.1 s` (mobile)
  - `16-ai-models` #1 : `14.7 s` (desktop) / `12.5 s` (mobile)
  - **`16-ai-models` #2 (`REM-33`) : `11.1 s` (desktop) / `10.7 s` (mobile)** (`< 35 000 ms`)
  - `16-ai-models` #3 : `6.1 s` (desktop) / `5.7 s` (mobile)
  - Campagne E2E intégrale `110` cas (`e2e-campaign-epic-22`) & promotion `62/62` `runtime` : portées par `Story 22.9` après `Story 22.8a`.
- **Qualité statique & Architecture** : `ruff check .` (`0` erreur), `ruff format --check .` (`1235` fichiers conformes), `mypy --strict` (`513` fichiers, `0` erreur), `lint-imports` (`5 contracts kept, 0 broken`), `export_openapi.py --check` (`0-diff`), `lint_spine.py` (`0 findings`), `pnpm site:sync && pnpm site:check`, `scripts/check_implementation_docs.py` et `gitnexus_detect_changes()`.

### 3.3 Validation & Procédure de Test sur Toute la Pyramide (`AD-17`)
1. **Couche 1 (Unitaires & Gardes CI)** : `pnpm turbo run lint typecheck test --force` (`9/9` tâches vertes, `110` UI + `13` API-Client + `185` Web) et `pytest tests/unit` (`883 passed` sur `unit + security + evals`), incluant les `6` gardes/verrous TS et `2` gardes Python.
2. **Couche 2 (Intégration PG18 / Redis)** : `POST /api/v1/_e2e/evict-memory-caches` validé (`404` hors `e2e`, `200` en `e2e`) et relecture à froid `reloadColdFromPg` vérifiée sur la pile réelle `testcontainers` PG18 + Redis lors du tir E2E ciblé.
3. **Couche 3 (Contrats & Architecture)** : `export_openapi.py --check` (`0-diff`), `lint-imports` (`5/5` contrats AD-19/AD-20), `mypy --strict` (`513` fichiers), `ruff`, `lint_spine.py` (`0` finding).
4. **Couche 4 (Sécurité & Evals)** : inclus dans `pytest tests/unit tests/security tests/evals -q` (`883 passed`, `0` fuite de secret/jargon, garde `_e2e` isolée par `ORCIA_ENV`).
5. **Couche 5 (Playwright E2E Ciblé `< 35 s`)** : `17 passed, 3 skipped (0 failed)` sur les `4` specs critiques (`04`, `05`, `14`, `16`) desktop & mobile (`max 14.7 s < 35 s`), la campagne complète `110` scénarios restant dédiée à `Story 22.9` après `Story 22.8a`.
