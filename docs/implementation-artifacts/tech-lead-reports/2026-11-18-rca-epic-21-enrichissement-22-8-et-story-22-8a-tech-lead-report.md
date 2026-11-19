# 2026-11-18 — RCA Anomalies Epic 21 (« L'Illusion du Vert »), Enrichissement Story `22.8` & Création Story Intercalaire `22.8a`

> **Convention de nommage du fichier (Obligatoire — à créer AVANT toute modification de code)** :
> - Demande d'ajustement, correctif ou évolution hors Story : `docs/implementation-artifacts/tech-lead-reports/{YYYY-MM-DD}-{descriptif-court}-tech-lead-report.md`

- **Date** : `2026-11-18`
- **Story / Clé Sprint** : `2026-11-18-rca-epic-21-enrichissement-22-8-et-story-22-8a` (`Ajustement Transverse Gouvernance & Planification Epic 22`)
- **Capacité(s)** : `CAP-100` (fondation hygiène UI/CI existante dans `docs/product/capabilities.yaml` ; `0` nouvelle entrée `CAP-*`) — classification : `hygiène`
- **Auteur / Contexte** : Tech Lead (`Amelia`) & Architecte (`Winston`) — Analyse des causes racines (`RC-1`..`RC-7`) expliquant comment les `47` échecs/timeouts E2E (`14/24` specs) et non-conformités UX/UI de l'Epic 21 ont échappé aux 5 couches de tests avant l'Epic 21, suivie de l'enrichissement de `Story 22.8` et de la création de `Story 22.8a` en Vague 3 (`AD-1`, `AD-17`, `AD-19`, `NFR-TEST-1`, `GEMINI.md`).
- **Commits associés** : À consolider après validation documentaire et CI sur branche courante (`HEAD = 610ab7e`).

---

## 1. Analyse du Besoin & Étude d'Impact Tech Lead (Pré-Implémentation)

### 1.1 Contexte & Problématique (« L'Illusion du Vert » sur les 5 Couches `AD-17`)
La campagne End-to-End Epic 21 (`bilan-execution-tests-e2e-epic-21.md`) a révélé **`47` scénarios `unexpected`** (`36` `failed` + `11` `timedOut`, `51/62` capacités `feature` en `failed_e2e`) et des défauts visuels majeurs sur des tests pourtant `PASSED` (`notes-audit-sally-ux.md`). Chaque couche de vérification présentait un angle mort masquant les coutures réelles du système :
1. **Couche 1b (`Vitest` + `jsdom`)** : `apps/web/src/__tests__/vitest.setup.ts` (`2 951` lignes) écrase `globalThis.fetch` via `vitestFetchTransport` (`L2951`) avec un `backendState` en mémoire JS permissif et un repli `return jsonResponse({})` (`L2948`). Il acceptait `"ws-1"`, ignorait `403 ERR_OBSERVER_MODE_READ_ONLY` et ne validait pas `extra="forbid"` des schémas Pydantic. De plus, `jsdom` ne calcule aucune feuille CSS (masquant l'absence de `@tailwindcss/vite`, le chevauchement de Zone 4 `sticky` sur les modales sans `Portal` et les débordements mobiles).
2. **Couche 2 (`tests/integration/` PostgreSQL 18)** : plusieurs suites instancient directement les classes `Sql*Repository` ou insèrent en SQL brut sans appeler `create_app()`, tandis que `test_epics_1_7_vertical_sql_wiring_postgres18.py` (`L138-L145`) assignait manuellement `app.state.dbos_uow = uow` et utilisait `dependency_overrides`, masquant `dbos_uow = None` dans `core_and_lifespan.py`. La règle « Zéro Adaptateur SQL Orphelin » restait manuelle.
3. **Couche 5 (Playwright E2E pré-Epic 21)** : `page.reload()` (`F5`) vidait le navigateur mais pas la RAM Python (`:8100`) ; avant Story `21.4` (`query_db.py`/`dbAssertions.ts`), aucune assertion `SELECT` PG18 n'existait ; avant Story `21.3`, `36/62` capacités `feature` étaient marquées `runtime` sans spec E2E fonctionnelle (simple smoke `11-*`) ; `ORCIA_E2E_SEED_FIXTURES="1"` (`e2e_stack_config.py:L76`) injectait personas (`marc`) et notifications RAM ; `overflow-x: hidden` sur `html/body` neutralisait `scrollWidth <= innerWidth` et aucune capture PNG systématique n'était inspectée.
4. **Effet Goodhart des audits statiques Regex** : `zero-dead-buttons-and-silent-catches-audit.test.tsx` (`L62-L197`) vérifiait par regex qu'un composant apparaissait dans `apps/web/src/`, incitant 4 fichiers à masquer d'anciens panneaux via `style={{ display: "none" }}`. Les audits Python ciblaient une liste fermée sans contrôler le Composition Root, `ORCIA_DISABLE_PG_BOOTSTRAP_SYNC` ni les dictionnaires `i18n`.
5. **CI GitHub Actions partielle & écriture E2E découplée de l'exécution** : `.github/workflows/e2e.yml` n'exécutait que `pnpm e2e` (ni `pytest`, ni `pnpm test`, ni `pnpm site:check`, ni couverture globale `orcia-core` tombée à `84.24 %` sur `tests/unit` seuls), et les specs `21.5`–`21.7` n'ont été vérifiées qu'avec `tsc --noEmit` avant `21.8`.

#### Regroupement des `34` chantiers (`REM-01`..`REM-34`) par Root Cause
| Root Cause | Chantiers `REM-*` (`34/34`) | Mécanisme racine & Stories Epic 22 |
| :--- | :--- | :--- |
| **`RC-1` Dual-Stack RAM/PG18 au Composition Root** | `REM-07` *(flag PG)*, `REM-08`, `REM-09`, `REM-10`, `REM-11`, `REM-13`, `REM-14`, `REM-15` | Services instanciés sans `engine`/`dbos_uow=None`, `ORCIA_DISABLE_PG_BOOTSTRAP_SYNC`, `wizards.tsx` en `useState` (`22.1`, `22.3`..`22.5`). |
| **`RC-2` Schisme identité `"ws-1"` / `slug` / `"marc"` & RBAC** | `REM-01`, `REM-02`, `REM-07` *(auth)*, `REM-16` | ID synthétique `"ws-1"` + perte `slug`, `PLATFORM_ADMIN` rétrogradé en `READ_ONLY_OBSERVER` `403`, bouton invitation masqué (`22.1`, `22.2`). |
| **`RC-3` Contournement `display: none` & collisions routes** | `REM-04`, `REM-05`, `REM-06` | `4` wrappers `display: none`, `/catalog` pointant sur `/agents`, double montage MCP et `/help` Zone 3+4 (`22.2`). |
| **`RC-4` Pipeline CSS Tailwind v4, Portals & Mobile `< 768px`** | `REM-03`, `REM-17`, `REM-18`, `REM-28`, `REM-29`, `REM-33` | `@tailwindcss/vite` absent, modale sans Portal coupée par Zone 4, `MobileCompanionView` inutilisé, `overflow-x: hidden` (`22.2`, `22.6`..`22.8`). |
| **`RC-5` Fuites internes, jargon `i18n`, erreurs muettes & UX** | `REM-08` *(tag)*, `REM-19`..`REM-23`, `REM-26`, `REM-27`, `REM-30`..`REM-32` | `[LAYER_5_*]`, `"LOCK TABLE..."`, `SYNTHESIS_READY`, `Chef1`/`aqwZSX`, sidebar `11` vs `8`, Cockpit `> 3` blocs, `4xx` muets, `$`/`€`, `(!)` (`22.3`, `22.6`, `22.7`). |
| **`RC-6` Transition SQL concurrente non gardée** | `REM-12` | `_sql_autonomous_rollback.py` écrasant `KILL_SWITCH_STOPPED` lors d'un rollback post-hoc (`22.4`). |
| **`RC-7` Contrats de tests (`data-testid`, JSON brut) & CI** | `REM-24`, `REM-25`, `REM-34` | `local-ollama` vs `ollama`, `what_if` vs `whatif`, `value` vs `plaintext_value` hors SDK, absence de gardes CI (`22.2`, `22.8`, `22.8a`). |

### 1.2 Exploration, Analyse d'Impact GitNexus, Factorisation & Dette Technique
- **Analyse d'Impact GitNexus (`repo: "ORCIA"`, `direction: "upstream"`)** :
  - `initialize_app_services` (`apps/api/src/orcia_api/dependencies/core_and_lifespan.py`) : `impactedCount: 237`, risque **`CRITICAL`** (`direct: 24`, `d=2: 122`, `d=3: 91`, `processes_affected: 167`, `modules_affected: 9`).
  - `create_app` (`apps/api/src/orcia_api/main.py`) : `impactedCount: 4`, risque **`LOW`** (`direct: 1`).
  - `is_isolated_e2e_database_url` (`infra/scripts/e2e/e2e_stack_config.py`) : `impactedCount: 9`, risque **`LOW`** (`direct: 3`, `modules_affected: 1` `E2e`).
- **Découpage & Ticket Intercalaire (`GEMINI.md` § Policy)** :
  - Afin de préserver la clé sprint `22-8-gardes-ci-anti-regression-campagne-e2e-110-vert-et-62-capacites-runtime` (verrouillée dans `tests/unit/test_epic21_to_epic22_traceability.py:L34`) tout en séparant l'enrichissement des gardes E2E/UI (`Story 22.8`) du chantier structurel d'assainissement de `vitest.setup.ts` (`2 951` L $\rightarrow$ modules `< 350` L), d'audit Composition Root sans override et de refonte CI GitHub Actions complète, création de la Story intercalaire **`Story 22.8a`** (`22-8a-assainissement-fail-closed-vitest-composition-root-sans-override-et-ci-complete`) ordonnancée `22.8 -> 22.8a -> 22.9 -> 22.10`.
  - Maintien strict des `65` capacités (`62` `feature` + `3` `foundation` dont `CAP-100`) sans ajout de nouvelle entrée `CAP-*`.

---

## 2. Plan d'Implémentation

### 2.1 Schéma de Données & Migrations Alembic (`infra/migrations/versions/`)
- Aucune migration Alembic modifiée dans cet ajustement documentaire et de planification ; la vérification de `0001` $\rightarrow$ `head` reste exécutée dans `Story 22.8` et en CI `Story 22.8a`.

### 2.2 Noyau Métier, Audits Backend & CI (`Story 22.8` enrichie + `Story 22.8a`)
- **`Story 22.8` (compléments Vague 3 côté E2E/Backend)** :
  - Suppression de `ORCIA_E2E_SEED_FIXTURES="1"` dans `infra/scripts/e2e/e2e_stack_config.py` et des seeds RAM E2E associés dans `core_and_lifespan.py` (démarrage Jour 0 pur PG18).
  - Endpoint strictement réservé à `ORCIA_ENV == "e2e"` (`POST /api/v1/_e2e/evict-memory-caches`, `HTTP 404` hors `e2e`) + helper Playwright `reloadColdFromPg(page)` vérifiant la **relecture SQL à froid** au `F5`.
- **`Story 22.8a` (Volets 2 & 3 — Composition Root, Couverture & CI 5 Couches)** :
  - Éradication des replis implicites `session_factory=None -> dict RAM` résiduels dans `packages/orcia-core` (ports `RepositoryPort` obligatoires ; `Fake*` confinés à `tests/unit/fakes/`).
  - Création de `tests/integration/test_composition_root_zero_ram_silo_postgres18.py` démarrant `create_app()` sur PG18 + Redis réels **sans `dependency_overrides` ni `app.state.* = ...` manuel**, nettoyage de `test_epics_1_7_vertical_sql_wiring_postgres18.py`, plus `tests/unit/test_integration_no_manual_app_state_audit.py` et `tests/unit/test_zero_orphan_sql_adapters_audit.py`.
  - Pipeline CI complet (`.github/workflows/ci.yml` + `.github/workflows/e2e.yml` shardé `4` shards `--retries=0`) avec `coverage combine` imposant `--cov=packages/orcia-core --cov-fail-under=90` sur tout le package.

### 2.3 Couche Backend API, Contrats & Transport Test (`Story 22.8` & `Story 22.8a`)
- **`Story 22.8`** : création de `apps/web/e2e/support/typedApiRequest.ts` imposant les schémas OpenAPI `@orcia/api-client` sur les requêtes directes Playwright (zéro JSON brut non typé).
- **`Story 22.8a` (Volet 1)** : découpage `< 350` L de `apps/web/src/__tests__/vitest.setup.ts` (`apps/web/src/__tests__/setup/*.ts`), suppression de `return jsonResponse({})` (`fail-closed`), et validation automatique de chaque requête dans `vitestFetchTransport` contre `packages/api-client/openapi.json` (route, `format: "uuid"` strict bloquant `"ws-1"` en `< 1 s`, `required` / `additionalProperties: false`) vérifiée par `vitest-transport-fail-closed-openapi.test.ts`.

### 2.4 Interface Utilisateur, Audits Anti-Goodhart & Gouvernance (`Story 22.8` + `docs/`)
- **`Story 22.8`** :
  - `apps/web/src/__tests__/e2e-testids-sync-audit.test.ts` (vérification `< 1 s` que 100 % des `getByTestId(...)` de `apps/web/e2e/` existent dans `@orcia/ui` ou `apps/web/src/`).
  - Refonte anti-Goodhart de `zero-dead-buttons-and-silent-catches-audit.test.tsx` (montage sur `<RouterProvider>` réel avec `toBeVisible()` et unicité `count === 1` au lieu de regex JSX sur fichiers).
  - Sonde Playwright « zéro erreur HTTP muette » (`[role="alert"]` visible sur `4xx`/`5xx`) et vérifications automatiques Direction C (`8` entrées sidebar, aide dynamique par route, contraste WCAG AA).
- **Documents de planification & gouvernance mis à jour maintenant** : `epics.md`, `sprint-status.yaml`, `sprint-change-proposal-2026-11-18-epic-22-remediation-plan.md`, `docs/testing-strategy.md` (règle Shift-Left : exécution Playwright + inspection des 2 PNG dès la Story), `GEMINI.md` (hors marqueurs gérés) et rapports `22-8`, `22-8a`, `22-9`, `README.md`.

### 2.5 Analyse d'Impact sur la Pyramide des Tests (`AD-17` — Couches 1 à 5 + Sécurité)
- **Couche 1a (`pytest`)** : `test_epic21_to_epic22_traceability.py`, `test_capabilities_registry.py`, `test_uj_e2e_coverage_gate.py`, `test_uj_prd_experience_consistency.py`, `test_site_catalog_sync.py`.
- **Couche 1b (`TypeScript`)** : `pnpm --filter @orcia/web typecheck`.
- **Couche 3 / Gouvernance** : `scripts/check_implementation_docs.py`, `pnpm site:sync && pnpm site:check`, `lint_spine.py`.

---

## 3. Bilan des Modifications & Résultats (Post-Implémentation)

> Lot de cadrage documentaire et de gouvernance terminé sur la base `610ab7e` (`Story 22.3` préservée en `done` ; implémentation code prévue en `Story 22.8` et `Story 22.8a`).

### 3.1 Fichiers Développés & Modifiés
| Fichier | Nature | Description synthétique |
| :--- | :--- | :--- |
| `docs/implementation-artifacts/tech-lead-reports/2026-11-18-rca-epic-21-enrichissement-22-8-et-story-22-8a-tech-lead-report.md` | Création | Rapport Tech Lead d'analyse RCA (`RC-1..RC-7`), enrichissement `22.8` et cadrage `22.8a`. |
| `docs/implementation-artifacts/tech-lead-reports/22-8a-assainissement-fail-closed-vitest-composition-root-sans-override-et-ci-complete-tech-lead-report.md` | Création | Rapport Tech Lead pré-implémentation de `Story 22.8a`. |
| `docs/implementation-artifacts/tech-lead-reports/22-8-gardes-ci-anti-regression-campagne-e2e-110-vert-et-62-capacites-runtime-tech-lead-report.md` & `22-9-...-tech-lead-report.md` | Modification | Enrichissement `22.8` (`4` verrous anti-faux-positifs, purge `ORCIA_E2E_SEED_FIXTURES`, `reloadColdFromPg`) et mise à jour dépendance `22.9`. |
| `docs/planning-artifacts/epics.md`, `sprint-change-proposal-2026-11-18-epic-22-remediation-plan.md`, `docs/implementation-artifacts/sprint-status.yaml` | Modification | Enrichissement `Story 22.8`, insertion `Story 22.8a` (`ready-for-dev`) et mise à jour plan directeur Epic 22 (`22-3-...: done` conservé). |
| `docs/testing-strategy.md`, `AGENTS.md` (via symlink `GEMINI.md`), `docs/implementation-artifacts/tech-lead-reports/README.md` | Modification | Durcissement des règles de test Shift-Left / anti-faux-positifs, indexation des rapports (`22.3` `done` conservée) et synchronisation `/showcase`. |
| `apps/web/src/generated/orciaSiteManifest.ts`, `docs/site-catalog/index.html`, `dist/orcia-site/index.html` | Régénération | Synchronisation via `pnpm site:sync` (`184` rapports Tech Lead indexés). |

### 3.2 Résultats Chiffrés, Métriques & Qualité
- **Synchronisation vitrine & registre (`pnpm site:sync` & `pnpm site:check`)** : `65/65` capacités `live` référençant au moins un test (`62/62` E2E fonctionnels, `20/20` UJ couverts), `184` rapports Tech Lead, `28` routes actives, `133` primitives UI (`[site:check OK]`).
- **Audit des rapports Tech Lead (`scripts/check_implementation_docs.py`)** : `184` rapports conformes et indexés dans `README.md`.
- **Traçabilité Python (`pytest`)** : `test_epic21_to_epic22_traceability.py`, `test_capabilities_registry.py`, `test_uj_e2e_coverage_gate.py`, `test_uj_prd_experience_consistency.py`, `test_site_catalog_sync.py` exécutés (`34 passed`). *(Couverture code applicatif non modifiée dans ce lot documentaire ; le seuil combiné `>= 90 %` sera vérifié lors des Stories `22.8` / `22.8a`.)*
- **Typecheck & Architecture Spine** : `pnpm --filter @orcia/web typecheck` (`0` erreur) et `lint_spine.py` (`total_findings: 0`).

### 3.3 Validation & Procédure de Test sur Toute la Pyramide (`AD-17`)
- Validé en local sans modification de code applicatif sur la pyramide documentaire/gouvernance :
  1. `pnpm site:sync && pnpm site:check`
  2. `.venv/bin/python scripts/check_implementation_docs.py`
  3. `.venv/bin/pytest tests/unit/test_epic21_to_epic22_traceability.py tests/unit/test_capabilities_registry.py tests/unit/test_uj_e2e_coverage_gate.py tests/unit/test_uj_prd_experience_consistency.py tests/unit/test_site_catalog_sync.py`
  4. `pnpm --filter @orcia/web typecheck`
  5. `.venv/bin/python .agent/skills/bmad-architecture/scripts/lint_spine.py --workspace docs/planning-artifacts/architecture/architecture-ORCIA-2026-10-24`
