# Story 22.9 — Campagne E2E Intégrale Vérité PostgreSQL 18, Captures PNG Finales (Succès & Échecs), Bilan & Audit Croisé Sally × Winston

> **Convention de nommage du fichier (Obligatoire — à créer AVANT toute modification de code)** :
> - User Story du sprint : `docs/implementation-artifacts/tech-lead-reports/{story-key}-tech-lead-report.md`

- **Date** : 2026-11-19
- **Story / Clé Sprint** : `22-9-campagne-e2e-integrale-captures-png-bilan-et-audit-croise-sally-winston` (`Epic 22` — Vague 4 / Campagne Intégrale & Audit Croisé)
- **Capacité(s)** : Vérification runtime réelle de `100 %` des `65` capacités (`62` `feature` + `3` `foundation`, `CAP-001`..`CAP-203`) dans `docs/product/capabilities.yaml` — classification : `hygiène`
- **Auteur / Contexte** : `22.0-init` → `22.9-impl` — Exécution de la campagne Playwright complète post-remédiation Epic 22 (`22.1`..`22.8` + `22.8a`) sans retry ni maquillage (`--retries=0 --max-failures=0 --timeout=35000`) et avec purge `ORCIA_E2E_SEED_FIXTURES` + relecture à froid PG18 (`reloadColdFromPg`), archivage des captures PNG dans `docs/implementation-artifacts/e2e-campaign-epic-22/`, rédaction du bilan factuel, audit croisé **Sally (UX) × Winston (Architecture)** (`REM23-01`..`REM23-13`) et mise à jour honnête de `docs/product/capabilities.yaml` (`AD-17`, `NFR-TEST-1`, `GEMINI.md` §5).
- **Commits associés** : `feat/epic-22-remediation-pg18-direction-c` (campagne exécutée sur `a1bb059`, clôturée par le commit Story `22.9`)

---

## 1. Analyse du Besoin & Étude d'Impact Tech Lead (Pré-Implémentation)

### 1.1 Contexte & Problématique
- **Séparation propre entre outillage CI (`22.8`), assainissement Fail-Closed & CI (`22.8a`), et exécution de campagne / audit (`22.9`)** :
  - À l'issue des Stories `22.8` et `22.8a`, les `5` gardes CI initiales + les `4` verrous anti-faux-positifs (sync `data-testid`, `typedApiRequest.ts`, purge `ORCIA_E2E_SEED_FIXTURES` + `reloadColdFromPg` via `/api/v1/_e2e/evict-memory-caches`, réécriture `<RouterProvider>` de `zero-dead-buttons` + sonde `[role="alert"]`) sont actifs, `vitest.setup.ts` est assaini *Fail-Closed* contre `openapi.json`, le Composition Root `create_app()` est vérifié sans `dependency_overrides` sur PG18 réel, les `55` blocs `test(...)` (`110` scénarios Desktop `1440×900` et Mobile `390×844`) disposent d'assertions `SELECT` PostgreSQL 18 effectives (`test_e2e_sql_coverage_audit.py`), et `apps/web/e2e/support/e2eCaptureFixture.ts` supporte `ORCIA_E2E_CAMPAIGN_DIR`.
  - Il faut maintenant exécuter la **campagne intégrale sans retry ni arrêt anticipé** sur pile réelle (`PostgreSQL 18 + pgvector`, `Redis 7.4`, Alembic `head`, FastAPI + cassette LLM `0 $`, SPA Vite) et diriger toutes les sorties vers un répertoire neuf **`docs/implementation-artifacts/e2e-campaign-epic-22/`** afin de préserver intégralement les preuves historiques de `e2e-campaign-epic-21/`.
- **Vérité absolue sans maquillage ni angle mort** :
  - Aucun `test.skip` ou `test.fixme` destiné à masquer un échec ne doit subsister.
  - Les captures PNG d'état final doivent être produites pour **100 % des scénarios exécutés (succès comme échecs)**, accompagnées de `manifest.jsonl` et `playwright-results.json`.
  - L'audit visuel de **Sally (UX/UI Direction C)** et l'audit architectural de **Winston (`AD-1..AD-24`)** doivent inspecter non seulement les échecs éventuels mais aussi les captures `PASSED` pour détecter toute dégradation résiduelle ou opportunité d'amélioration.
  - `docs/product/capabilities.yaml` ne doit promouvoir à `verification: runtime` que les capacités dont **100 % des specs associées ont réussi** ; toute capacité encore touchée par un échec reste/passe honnêtement à `verification: failed_e2e`.

### 1.2 Exploration, Analyse d'Impact GitNexus, Factorisation & Dette Technique
- **Composants du harnais et du registre impactés** :
  - `apps/web/e2e/support/e2eCaptureFixture.ts` : piloté par `ORCIA_E2E_CAMPAIGN_DIR=docs/implementation-artifacts/e2e-campaign-epic-22` (écriture de `manifest.jsonl` et `screenshots/<spec>/<project>--<test>--<status>.png`).
  - `infra/scripts/uj_e2e_coverage.py` (`PLAYWRIGHT_RESULTS_PATH`, `load_failed_e2e_specs`, `check_uj_e2e_coverage`) : vérifie la cohérence entre `playwright-results.json` et `docs/product/capabilities.yaml` lors de `pnpm site:check`.
  - `docs/implementation-artifacts/e2e-campaign-epic-21/*` : conservé intact comme base comparative (évolution `47 passed / 47 failed+timedOut` $\rightarrow$ bilan Epic 22).
- **Contraintes de volumétrie & hygiène** :
  - Aucun changement de code métier applicatif dans `Story 22.9` (sauf mise à jour éventuelle du chemin `PLAYWRIGHT_RESULTS_PATH` dans `uj_e2e_coverage.py` pour pointer sur `e2e-campaign-epic-22/playwright-results.json` et mise à jour de `capabilities.yaml` + synchronisation vitrine).
  - Les correctifs pour tout échec ou amélioration découvert pendant `22.9` sont planifiés et cadrés dans `Story 22.10` (`Epic 23`), sans bricolage hors périmètre.

---

## 2. Plan d'Implémentation

### 2.1 Schéma de Données & Migrations Alembic (`infra/migrations/versions/`)
- Aucune migration Alembic dans `Story 22.9`. Avant le lancement de la campagne E2E, la base éphémère `orcia_e2e` est réinitialisée proprement (`alembic upgrade head` + état Jour 0 à `0` utilisateur).

### 2.2 Noyau Métier Hexagonal, Orchestration & Workers (`packages/orcia-core/`, `apps/worker/`)
- Aucune modification de code métier dans `Story 22.9`. Les éventuelles violations `AD-1`..`AD-24`, fuites RAM, incohérences d'événements Outbox ou erreurs SQL observées durant la campagne sont consignées dans `notes-audit-winston-architecture.md` et `synthese-remediation-sally-winston-epic-22.md`.

### 2.3 Couche Backend API, Sécurité & Contrats (`apps/api/`, `packages/api-client/`)
- Aucune modification d'endpoint dans `Story 22.9`. Le serveur FastAPI est lancé avec la configuration PG18/Redis réelle et les traces logs/erreurs HTTP (`4xx`/`5xx`) sont exploitées dans `bilan-execution-tests-e2e-epic-22.md` et `notes-audit-winston-architecture.md`.

### 2.4 Livrables Campagne E2E, Audit Croisé & Registre (`docs/`, `infra/scripts/`)
1. **Exécution Playwright intégrale (`ORCIA_E2E_CAMPAIGN_DIR=docs/implementation-artifacts/e2e-campaign-epic-22`)** :
   - Lancement des `24` specs (`00..21` + `shell.spec.ts`) sur `desktop-cockpit` (`1440×900`) et `mobile-companion` (`390×844`) avec `--retries=0 --max-failures=0 --timeout=35000` et reporter JSON vers `docs/implementation-artifacts/e2e-campaign-epic-22/playwright-results.json`.
   - Archivage de `manifest.jsonl` (`110` entrées) et de toutes les captures PNG sous `docs/implementation-artifacts/e2e-campaign-epic-22/screenshots/**/*.png`.
2. **Bilan Factuel & Audit Croisé Sally × Winston** :
   - `docs/implementation-artifacts/e2e-campaign-epic-22/bilan-execution-tests-e2e-epic-22.md` : inventaire chiffré exact (`passed`, `failed`, `timedOut`, `skipped`), comparaison avec Epic 21, matrice `CAP ↔ UJ ↔ Spec ↔ UI/F5/SQL`, causes racines des éventuels échecs résiduels et liens vers captures.
   - `docs/implementation-artifacts/e2e-campaign-epic-22/notes-audit-sally-ux.md` : revue visuelle complète des captures Desktop et Mobile (Direction C, contrastes WCAG, surcharge, lisibilité, langue FR).
   - `docs/implementation-artifacts/e2e-campaign-epic-22/notes-audit-winston-architecture.md` : revue architecturale (`AD-1`..`AD-24`, SQL PG18, latences, contrat API).
   - `docs/implementation-artifacts/e2e-campaign-epic-22/synthese-remediation-sally-winston-epic-22.md` : table de synthèse priorisée (`P0`..`P3`) de tous les échecs résiduels et améliorations recommandées pour l'Epic 23.
3. **Vérité Registre & Vitrine** :
   - Mise à jour de `infra/scripts/uj_e2e_coverage.py` (`PLAYWRIGHT_RESULTS_PATH`) si nécessaire pour pointer sur la campagne Epic 22.
   - Mise à jour honnête de `docs/product/capabilities.yaml` (`verification: runtime` pour les capacités 100 % vertes ; `verification: failed_e2e` pour toute capacité encore en échec).
   - Exécution de `pnpm site:sync && pnpm site:check`.

### 2.5 Analyse d'Impact sur la Pyramide des Tests (`AD-17`)
- **Couche 1a (`pytest`)** : `.venv/bin/pytest tests/unit/test_uj_e2e_coverage_gate.py tests/unit/test_capabilities_registry.py` — validation de la cohérence stricte `capabilities.yaml` ↔ `playwright-results.json` ↔ `prd.md`.
- **Couche 3 / Vitrine** : `pnpm site:sync && pnpm site:check` — validation `0` erreur sur les `65` capacités, `20/20` UJ, routes SPA et routeurs FastAPI.
- **Couche 5 (Playwright E2E)** : Exécution intégrale des `110` scénarios (`24` specs) sur pile PG18 + Redis 7.4 sans retry ni maquillage.

---

## 3. Bilan des Modifications & Résultats (Post-Implémentation)

### 3.1 Fichiers Développés & Modifiés
| Fichier | Nature (Création / Modification / Refactoring) | Description synthétique |
| :--- | :--- | :--- |
| `docs/implementation-artifacts/e2e-campaign-epic-22/playwright-results.json` | Création | Rapport Playwright JSON complet (`24` specs, `110` scénarios : `7` passed, `90` failed, `0` timedOut, `13` skipped ; `378 KB < 450 KB`). |
| `docs/implementation-artifacts/e2e-campaign-epic-22/manifest.jsonl` | Création | Index complet des `110/110` scénarios et captures (`121 KB < 450 KB`). |
| `docs/implementation-artifacts/e2e-campaign-epic-22/screenshots/**/*.png` | Création | `110/110` captures PNG d'état final (`24` répertoires de specs, `desktop-cockpit` `1440×900` + `mobile-companion` `390×844`, toutes `<= 218 KB < 450 KB`). |
| `docs/implementation-artifacts/e2e-campaign-epic-22/bilan-execution-tests-e2e-epic-22.md` | Création | Bilan factuel exhaustif des `110` scénarios, delta Epic 21 → Epic 22 (`#8`/`#9`/`#10` FAIL → PASS, puis cascade `resetDay0()` `#11`–`#110`) et liens vers les `110` PNG. |
| `docs/implementation-artifacts/e2e-campaign-epic-22/notes-audit-sally-ux.md` | Création | Audit visuel Direction C / WCAG de Sally sur `24` captures représentatives (`7/7` passed, `3/3` `401` directs, `14` cascade `beforeEach`) : `P0-UX-1`..`P3-UX-12`. |
| `docs/implementation-artifacts/e2e-campaign-epic-22/notes-audit-winston-architecture.md` | Création | Diagnostic architectural de Winston (`ARCH23-01`..`ARCH23-10`), dialogue croisé Sally × Winston et ordonnancement en 3 vagues Epic 23 (`23.1`..`23.6`). |
| `docs/implementation-artifacts/e2e-campaign-epic-22/synthese-remediation-sally-winston-epic-22.md` | Création | Table Maîtresse Exhaustive `REM23-01`..`REM23-13` couvrant `100 %` des `90` échecs E2E, `12/12` constats Sally et `10/10` constats Winston. |
| `infra/scripts/uj_e2e_coverage.py` | Modification | Bascule de `PLAYWRIGHT_RESULTS_PATH` par défaut vers `docs/implementation-artifacts/e2e-campaign-epic-22/playwright-results.json`. |
| `docs/product/capabilities.yaml` | Modification | Mise à jour honnête (`0` maquillage) : `3` `foundation` (`CAP-006`, `CAP-100`, `CAP-202`) en `runtime` (`verified_at: "2026-11-19"`) ; `62` `feature` (`CAP-001`..`CAP-203`) en `failed_e2e` pointant provisoirement vers `22-10-rapports-tech-lead-plan-correction-global-et-initialisation-epic-23`. |
| `apps/web/src/generated/orciaSiteManifest.ts` & `docs/site-catalog/index.html` | Régénération (`pnpm site:sync`) | Synchronisation vitrine `/showcase` et site statique autonome après mise à jour de `capabilities.yaml`. |
| `docs/implementation-artifacts/sprint-status.yaml` & `docs/implementation-artifacts/tech-lead-reports/README.md` | Modification | Passage de `22-9-*` à `done` et indexation finale du rapport Story `22.9`. |

### 3.2 Résultats Chiffrés, Métriques & Qualité
- **Campagne E2E Epic 22 (`playwright-results.json` & `manifest.jsonl`, `--retries=0 --max-failures=0 --timeout=35000`)** :
  - **Total** : `110` scénarios planifiés sur `24` specs (`55` `desktop-cockpit` + `55` `mobile-companion`), durée totale **`432 047 ms`** (**`7,20 min`**).
  - **Verdicts** : **`7` `passed`** (`desktop-cockpit` : `#1`, `#2`, `#5`, `#6`, `#8`, `#9`, `#10`), **`90` `failed`** (`46` desktop + `44` mobile), **`0` `timedOut`**, **`13` `skipped`** (gardes viewport attendus : `2` desktop + `11` mobile), taux de succès **`7,2 %`** (`7 / 97` exécutés).
  - **Delta positif vs Epic 21** : les corrections Epic 22 ont fait passer **3 échecs PG18 en succès réels** (`#8` et `#9` `assistant_folders`, `#10` `human_anchor_signatures` + `step_executions` + `blackboard_snapshots`).
  - **Causes racines des `90` échecs** :
    - **`3` échecs `HTTP 401` directs** : `00-stack-smoke` #3/#4 (appels anonymes Jour 0 sur `ORCIA_ENV="e2e"` *fail-closed*) et `02-assistant` #7 (`streamAssistantTurnSse` omettant `Authorization: Bearer`).
    - **`87` échecs en cascade (`#11`–`#110` hors skips)** : le succès `#10` ayant écrit dans `step_executions` et `blackboard_snapshots`, `09_reset_db_first_boot.py` a échoué dès `#11` en `beforeEach` (`RestrictViolationError` sur FK `blackboard_snapshots_step_execution_id_fkey`), bloquant les specs `04`–`21`, `shell.spec.ts` et **`100 %` (`0 / 55`) du projet `mobile-companion`**.
- **Captures PNG (`110 / 110`)** :
  - `110 / 110` fichiers PNG archivés dans `docs/implementation-artifacts/e2e-campaign-epic-22/screenshots/<spec>/<project>--<test>--<status>.png` (`0` manquant, taille max `218 KB < 450 KB` ; `0` fichier `> 450 KB` dans `e2e-campaign-epic-22/`).
  - Couverture visuelle inspectée par Sally (`24` captures) : `7/7` `passed` + `3/3` `401` directs + `14` captures `beforeEach` (`/login`).
- **Synthèse croisée Sally × Winston (`synthese-remediation-sally-winston-epic-22.md`)** :
  - **`13` chantiers de remédiation (`REM23-01`..`REM23-13`)** répartis sur **3 vagues** (`Vague 0` : `REM23-01`..`REM23-04` ; `Vague 1` : `REM23-05`..`REM23-12` ; `Vague 2` : `REM23-13`), couvrant `100 %` des `90` échecs E2E, `12/12` items Sally (`P0-UX-1`..`P3-UX-12`) et `10/10` items Winston (`ARCH23-01`..`ARCH23-10`).
- **État exact de `docs/product/capabilities.yaml` (`65` capacités)** :
  - **`3` `foundation` en `verification: runtime`** (`verified_at: "2026-11-19"`) : `CAP-006`, `CAP-100`, `CAP-202`.
  - **`62` `feature` en `verification: failed_e2e`** (`e2e_remediation_ref: "22-10-rapports-tech-lead-plan-correction-global-et-initialisation-epic-23"`), toutes les `24` specs E2E comptant au moins un échec dans `e2e-campaign-epic-22/playwright-results.json` (y compris les `11` capacités précédemment `runtime` rétrogradées honnêtement suite aux échecs `mobile-companion` / `401` / cascade).

### 3.3 Validation & Procédure de Test sur Toute la Pyramide (`AD-17`)
- **Couche 1a (`pytest` registre & traçabilité)** : `.venv/bin/pytest tests/unit/test_uj_e2e_coverage_gate.py tests/unit/test_capabilities_registry.py tests/unit/test_epic21_to_epic22_traceability.py -q` → **`27 passed` (`100 %`)**.
- **Qualité Python & Documentation** :
  - `.venv/bin/ruff check infra/scripts/uj_e2e_coverage.py` & `.venv/bin/ruff format --check infra/scripts/uj_e2e_coverage.py` → **`0` erreur**.
  - `MYPYPATH=infra/scripts .venv/bin/mypy --strict infra/scripts/uj_e2e_coverage.py` → **Success: no issues found**.
  - `.venv/bin/python scripts/check_implementation_docs.py` → **`0` erreur**.
  - `find docs/implementation-artifacts/e2e-campaign-epic-22 -type f -size +450k` → **aucun fichier `> 450 KB`**.
- **Synchronisation Vitrine & Verrou `CAP ↔ UJ ↔ E2E`** : `pnpm site:sync && pnpm site:check` → **`0` erreur** (`65/65` capacités valides, `20/20` UJ couverts, `0` runtime non vérifié).
- **Couche 5 (Playwright E2E PG18 + Redis 7.4 sans `ORCIA_E2E_SEED_FIXTURES`)** : campagne intégrale `24` specs / `110` scénarios archivée dans `docs/implementation-artifacts/e2e-campaign-epic-22/` (`7` passed, `90` failed, `0` timedOut, `13` skipped). Suite planifiée dans `Story 22.10` pour l'initialisation complète de l'`Epic 23`.
