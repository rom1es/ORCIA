# Story 23.7 — Campagne Playwright E2E Intégrale Desktop Epic 23 (`--project=desktop-cockpit`), Captures PNG d'État Final (`55/55`), Bilan Exhaustif & Audit Croisé Sally × Winston

> **Convention de nommage du fichier (Obligatoire — à créer AVANT toute modification de code)** :
> - User Story du sprint : `docs/implementation-artifacts/tech-lead-reports/{story-key}-tech-lead-report.md`

- **Date** : 2026-11-20 (initialisé le 2026-11-19)
- **Story / Clé Sprint** : `23-7-campagne-e2e-integrale-captures-png-bilan-et-audit-croise-sally-winston` (`Epic 23` — Vague 3 / Campagne Intégrale Figée Desktop & Audit Croisé)
- **Capacité(s)** : Vérification runtime réelle sur Desktop de `36 / 62` capacités `feature` (+ `3 / 3` `foundation` = `39` `runtime`) et maintien honnête en `failed_e2e` de `26` capacités (`25` rattachées aux `6` specs Desktop en échec + `CAP-042` Mobile Companion maintenue `failed_e2e` vers `ACTION_ITEM-23.6`) dans `docs/product/capabilities.yaml` — classification : `hygiène`
- **Auteur / Contexte** : `23.0-impl` (initialisation Step 0 Epic 23), mis à jour `23.6a-doc-init` (2026-11-19 — recadrage Desktop RCA Epic 22), clôturé `23.7-impl` (2026-11-20). Exécution sans retouche de code applicatif de la campagne Playwright E2E intégrale **`--project=desktop-cockpit`** (`1440×900`, `24` specs / `55` scénarios Desktop dont `52` exécutés et `3` `mobile-only` skipped) sur l'état figé `dd2d382` post-`23.1`..`23.5` + `23.6a` (`--retries=0 --max-failures=0 --timeout=35000`, `0` `ORCIA_E2E_SEED_FIXTURES`), archivage des `58` captures PNG (`55` états finaux + `3` jalons) dans `docs/implementation-artifacts/e2e-campaign-epic-23/`, rédaction du bilan exhaustif `bilan-execution-tests-e2e-epic-23.md`, audit croisé **Sally (UX) × Winston (Architecture)** (`Case B -> Epic 24`), bascule de `PLAYWRIGHT_RESULTS_PATH` dans `infra/scripts/uj_e2e_coverage.py` et mise à jour honnête de `docs/product/capabilities.yaml` (`CAP-042` maintenue `failed_e2e` vers `ACTION_ITEM-23.6`, `AD-17`, `NFR-TEST-1`, `GEMINI.md` §5).
- **Commits associés** : `dd2d382` (état figé post-`Story 23.6a` exécuté en campagne) + commit atomique de clôture `Story 23.7` sur `feat/epic-23-remediation-pg18-sse-direction-c`

---

## 1. Analyse du Besoin & Étude d'Impact Tech Lead (Pré-Implémentation)

### 1.1 Contexte & Problématique
- **Séparation stricte entre durcissement anti-Goodhart (`23.6a`), campagne figée Desktop & audit croisé (`23.7`), et clôture / éventuel Epic 24 (`23.8`)** :
  - À l'issue des Stories `23.1`..`23.5` et de `Story 23.6a` (prérequis **`100 %` vert sur les 5 couches `AD-17`** + **Chaîne Canari Desktop Obligatoire** + **Tir de reconnaissance Desktop V0**), la `Story 23.6` et le périmètre Mobile Companion (`--project=mobile-companion`, `390×844`, `CAP-042`) ont été reportés en **`ACTION_ITEM-23.6`**.
  - Il convient désormais d'exécuter une **campagne intégrale figée Desktop (`--project=desktop-cockpit`, `1440×900`, `24` specs / `55` scénarios Desktop) sans aucune retouche de code applicatif** sur la pile réelle (`PostgreSQL 18 + pgvector`, `Redis 7.4`, Alembic `head`, FastAPI + `DeterministicCassetteLLM` `0 $`, SPA Vite), en dirigeant les sorties vers le répertoire neuf **`docs/implementation-artifacts/e2e-campaign-epic-23/`** afin de préserver intégralement `e2e-campaign-epic-21/` et `e2e-campaign-epic-22/`.
- **Exigence de vérité sans maquillage ni angle mort Desktop** :
  - Zéro `test.skip` ou `test.fixme` destiné à masquer un échec (seuls les `3` skips `mobile-only` prévus dans `05`, `12-finops` et `13-epic-7` sous `--project=desktop-cockpit` restent autorisés, produisant **`52` scénarios exécutés + `3` skipped = `55` scénarios Desktop**).
  - Les captures PNG d'état final (`55/55` Desktop) doivent couvrir **100 % des scénarios Desktop (succès comme échecs)**, accompagnées de `manifest.jsonl` (`55` entrées) et `playwright-results.json`, chaque fichier respectant strictement la limite `< 450 KB` (`460 800` octets) du hook `pre-commit`.
  - L'audit visuel de **Sally (UX/UI Direction C)** et l'audit architectural de **Winston (`AD-1`..`AD-24`)** inspectent les captures Desktop (`1440×900`) sur `00`–`21` + `shell.spec.ts` pour vérifier l'absence totale d'écart `P0`/`P1`.
  - `docs/product/capabilities.yaml` promeut à `verification: runtime` les capacités Desktop prouvées à `100 %` ; **`CAP-042` (Mobile Companion `390×844`) reste honnêtement en `verification: failed_e2e` avec `e2e_remediation_ref: "ACTION_ITEM-23.6"`**, et toute autre capacité éventuellement en échec reste en `failed_e2e`.

### 1.2 Exploration, Analyse d'Impact GitNexus, Factorisation & Dette Technique
- **Analyse d'Impact GitNexus & Inspection Directe (`repo: "/home/romain/Documents/Projects/ORCIA"`)** :
  - La sonde MCP `gitnexus_context` / `gitnexus_impact` sur `load_failed_e2e_specs` (`infra/scripts/uj_e2e_coverage.py`), `check_uj_e2e_coverage` (`infra/scripts/uj_e2e_coverage.py`) et `captureFinalState` (`apps/web/e2e/support/e2eCaptureFixture.ts`) confirme que ces scripts d'outillage CI/E2E hors package applicatif ne sont pas indexés comme symboles appelables dans le graphe GitNexus. L'étude d'impact a donc été complétée par inspection directe des fichiers :
    - `docs/implementation-artifacts/tech-lead-reports/23-6a-durcissement-anti-goodhart-gardes-openapi-ast-geometrie-et-reset-pg18-tech-lead-report.md` : définit les préconditions `23.1`..`23.5` + `23.6a` `100 %` vertes sur les 5 couches `AD-17` et le Tir de reconnaissance Desktop V0 avant lancement de la campagne figée.
    - `apps/web/e2e/support/e2eCaptureFixture.ts` (`L8-16`, `L80-112`) : piloté par `ORCIA_E2E_CAMPAIGN_DIR=docs/implementation-artifacts/e2e-campaign-epic-23` ; capture `fullPage: true` puis bascule sur `fullPage: false` si la taille dépasse `MAX_SCREENSHOT_BYTES` (`440 * 1024`), garantissant `< 450 KB` par capture PNG.
    - `infra/scripts/uj_e2e_coverage.py` (`L14-29`, `L112-261`) : lit `PLAYWRIGHT_RESULTS_PATH` (actuellement `docs/implementation-artifacts/e2e-campaign-epic-22/playwright-results.json`, surchargeable via `ORCIA_PLAYWRIGHT_RESULTS_PATH`) et bloque `pnpm site:check` si une capacité `verification: runtime` pointe vers une spec E2E en échec dans `playwright-results.json`.
    - `docs/implementation-artifacts/tech-lead-reports/22-9-campagne-e2e-integrale-captures-png-bilan-et-audit-croise-sally-winston-tech-lead-report.md` : modèle de référence des livrables et de la méthode d'audit.
- **Contraintes de volumétrie & séparation des rôles** :
  - Aucune retouche de code métier applicatif dans `Story 23.7` (seuls `PLAYWRIGHT_RESULTS_PATH` dans `infra/scripts/uj_e2e_coverage.py`, `docs/product/capabilities.yaml` et les artefacts régénérés par `pnpm site:sync` sont mis à jour avec les livrables de campagne).
  - Tout éventuel échec résiduel ou écart `P0`/`P1` identifié pendant `23.7` est consigné dans `synthese-remediation-sally-winston-epic-23.md` pour traitement en `Story 23.8` (`52/52` PASS Desktop et `0` écart `P0`/`P1` $\rightarrow$ clôture directe de l'Epic 23 sans créer d'Epic 24 artificiel vide).

---

## 2. Plan d'Implémentation

### 2.1 Schéma de Données & Migrations Alembic (`infra/migrations/versions/`)
- Aucune migration Alembic dans `Story 23.7`. Avant lancement de la campagne E2E Desktop, la base isolée `orcia_e2e` est remise au niveau `alembic upgrade head` et réinitialisée à l'état Jour 0 (`0` utilisateur) par le harnais `resetDay0()`.

### 2.2 Noyau Métier Hexagonal, Orchestration & Workers (`packages/orcia-core/`, `apps/worker/`)
- Aucune modification de code métier dans `Story 23.7` (campagne figée sur l'état stabilisé en `Stories 23.1`–`23.5` + `23.6a`). Toute anomalie `AD-1`..`AD-24`, divergence SQL PG18 ou latence observée durant la campagne est consignée dans `notes-audit-winston-architecture.md` et `synthese-remediation-sally-winston-epic-23.md`.

### 2.3 Couche Backend API, Sécurité & Contrats (`apps/api/`, `packages/api-client/`)
- Aucune modification d'endpoint ou de schéma OpenAPI dans `Story 23.7`. Les éventuels statuts `4xx`/`5xx` inattendus ou écarts de contrat observés lors du run Playwright sont documentés dans `bilan-execution-tests-e2e-epic-23.md` et `notes-audit-winston-architecture.md`.

### 2.4 Livrables Campagne E2E Desktop, Audit Croisé & Registre (`docs/`, `infra/scripts/`)
1. **Exécution Playwright intégrale figée Desktop (`ORCIA_E2E_CAMPAIGN_DIR=docs/implementation-artifacts/e2e-campaign-epic-23`)** :
   - Commande cible : `CI=1 ORCIA_E2E_CAMPAIGN_DIR=docs/implementation-artifacts/e2e-campaign-epic-23 PLAYWRIGHT_JSON_OUTPUT_NAME=docs/implementation-artifacts/e2e-campaign-epic-23/playwright-results.json timeout --kill-after=30s 2400s pnpm --filter @orcia/web exec playwright test --project=desktop-cockpit --retries=0 --max-failures=0 --timeout=35000 --reporter=list,json`.
   - Archivage de `playwright-results.json`, `manifest.jsonl` (`55` entrées Desktop) et `55/55` captures PNG sous `docs/implementation-artifacts/e2e-campaign-epic-23/screenshots/**/*.png` (tous fichiers `< 450 KB`).
2. **Bilan Factuel & Audit Croisé Sally × Winston** :
   - `docs/implementation-artifacts/e2e-campaign-epic-23/bilan-execution-tests-e2e-epic-23.md` : décompte exact Desktop (`52` passed attendus, `0` failed, `0` timedOut, `3` skipped `mobile-only`), comparaison Epic 22 → Epic 23, matrice `CAP ↔ UJ ↔ Spec ↔ F5/SQL` et liens vers captures.
   - `docs/implementation-artifacts/e2e-campaign-epic-23/notes-audit-sally-ux.md` : inspection visuelle exhaustive des captures Desktop (`1440×900`) sur les écrans `00`–`21` + `shell.spec.ts` (Direction C, contraste WCAG AA, sobriété, langue FR).
   - `docs/implementation-artifacts/e2e-campaign-epic-23/notes-audit-winston-architecture.md` : audit architectural (`AD-1`..`AD-24`, persistance PG18, flux SSE, latences).
   - `docs/implementation-artifacts/e2e-campaign-epic-23/synthese-remediation-sally-winston-epic-23.md` : table de synthèse priorisée (`P0`..`P3`) ou confirmation `0` écart `P0`/`P1` (Mobile Companion `CAP-042` tracé vers `ACTION_ITEM-23.6`).
3. **Vérité Registre & Vitrine** :
   - Bascule de `PLAYWRIGHT_RESULTS_PATH` dans `infra/scripts/uj_e2e_coverage.py` vers `docs/implementation-artifacts/e2e-campaign-epic-23/playwright-results.json`.
   - Mise à jour honnête de `docs/product/capabilities.yaml` (`verification: runtime` + `verified_at` pour chaque capacité Desktop dont `100 %` des specs sont vertes ; **`CAP-042` maintenue en `verification: failed_e2e` avec `e2e_remediation_ref: "ACTION_ITEM-23.6"`** ; toute autre capacité éventuellement en échec maintenue `failed_e2e`).
   - Exécution de `pnpm site:sync && pnpm site:check` (`0` erreur).

### 2.5 Analyse d'Impact sur la Pyramide des Tests (`AD-17` — Couches 1 à 5 + Sécurité, Obligatoire)
- **Prérequis bloquant** : `23.1`..`23.5` + `23.6a` `100 %` verts sur l'ensemble des 5 couches `AD-17`.
- **Couche 1a (`pytest`)** : `.venv/bin/pytest tests/unit/test_uj_e2e_coverage_gate.py tests/unit/test_capabilities_registry.py tests/unit/test_e2e_sql_coverage_audit.py` — cohérence stricte `capabilities.yaml` ↔ `playwright-results.json` ↔ `prd.md` ↔ `55/55` assertions SQL PG18 domaine.
- **Couche 3 / Vitrine** : `pnpm site:sync && pnpm site:check`, `.venv/bin/python scripts/check_implementation_docs.py` — `0` erreur sur les `65` capacités, `20/20` UJ et le registre des rapports Tech Lead.
- **Couche 5 (Playwright E2E Desktop `--project=desktop-cockpit`)** : exécution intégrale des `55` scénarios Desktop (`24` specs `1440×900` : `52` exécutés + `3` `mobile-only` skipped) sur pile réelle PG18 + Redis 7.4 sans `ORCIA_E2E_SEED_FIXTURES` ni retry.

---

## 3. Bilan des Modifications & Résultats (Post-Implémentation)

### 3.1 Fichiers Développés & Modifiés
| Fichier | Nature (Création / Modification / Refactoring) | Description synthétique |
| :--- | :--- | :--- |
| `docs/implementation-artifacts/e2e-campaign-epic-23/playwright-results.json`, `manifest.jsonl`, `screenshots/**/*.png` | Création | Artefacts bruts de la campagne figée `--project=desktop-cockpit` sur `dd2d382` (`55` entrées `manifest.jsonl`, `58` captures PNG dont `55` états finaux et `3` jalons `milestone-*.png`, `64` fichiers totaux tous `< 450 KB`). |
| `docs/implementation-artifacts/e2e-campaign-epic-23/{bilan-execution-tests-e2e-epic-23,notes-audit-sally-ux,notes-audit-winston-architecture,synthese-remediation-sally-winston-epic-23}.md` | Création | Bilan factuel des `55` scénarios (`18` specs `100 % PASS`, `6` specs en échec/timeout), audit visuel Sally (`58/58` PNG, `17` constats `UX23-*`), diagnostic Winston (`12` `ARCH24-*`) et synthèse croisée (`12` `REM24-*` en `3` vagues, verdict `Case B -> Epic 24`). |
| `infra/scripts/uj_e2e_coverage.py` | Modification | Bascule de `PLAYWRIGHT_RESULTS_PATH` vers `docs/implementation-artifacts/e2e-campaign-epic-23/playwright-results.json`. |
| `docs/product/capabilities.yaml` | Modification | Promotion honnête à `verification: runtime` (`verified_at: "2026-11-20"`) des `36` capacités `feature` Desktop `100 % PASS` (+ `3` `foundation` = `39` `runtime`) ; maintien en `verification: failed_e2e` des `25` capacités liées aux `6` specs en échec (`06`, `07`, `17`, `18`, `19`, `20`) vers `23-8-rapports-tech-lead-plan-correction-global-et-initialisation-epic-24` et de `CAP-042` vers `ACTION_ITEM-23.6` (`26` `failed_e2e`). |
| `tests/unit/test_epic22_to_epic23_traceability.py` | Modification | Renforcement des assertions post-`23.7` (`done`) : présence et intégrité `< 450 KB` de `e2e-campaign-epic-23/`, `CAP-042 -> ACTION_ITEM-23.6`, interdiction de promotion des capacités en échec, et décompte exact `39 runtime / 26 failed_e2e`. |
| `docs/implementation-artifacts/sprint-status.yaml`, `docs/implementation-artifacts/tech-lead-reports/{23-7-...,README}.md` | Modification | Passage `23-7-campagne-e2e-integrale-captures-png-bilan-et-audit-croise-sally-winston: done`, rédaction de la Section 3 et mise à jour de l'index Tech Lead. |
| `apps/web/src/generated/orciaSiteManifest.ts`, `docs/site-catalog/index.html`, `dist/orcia-site/index.html` | Régénération (`pnpm site:sync`) | Synchronisation de la vitrine produit (`65` capacités, `39` vérifiées `runtime`, `193` rapports Tech Lead, `0` hex brut). |

### 3.2 Résultats Chiffrés, Métriques & Qualité
- **Campagne E2E Desktop figée (`--project=desktop-cockpit`, `dd2d382`, sans `ORCIA_E2E_SEED_FIXTURES`, `--retries=0 --max-failures=0 --timeout=35000`, durée `771 175,85 ms` = `12,85 min`)** :
  - **`44 passed / 7 failed / 1 timedOut / 3 skipped / 0 flaky`** sur `55` scénarios planifiés (`24` specs : **`18` `100 % PASS`**, **`6` avec ≥ 1 échec/timeout** `06`, `07`, `17`, `18`, `19`, `20` ; taux de succès **`84,6 %`** `44 / 52`, progression **`+37` scénarios PASS** vs `7 / 53` en Epic 22).
  - **`58` PNG `< 450 KB`** (`55` états finaux `manifest.jsonl` + `3` captures jalons `milestone-*.png`, plus grosse capture `276 950` octets ; `64` fichiers sous `e2e-campaign-epic-23/` tous `< 450 KB`).
- **Audit croisé Sally × Winston (`e2e-campaign-epic-23/`)** :
  - **`17` constats `UX23-*`** (`UX23-01`..`UX23-17` : `1 P0`, `9 P1`, `5 P2`, `2 P3`) ;
  - **`12` diagnostics `ARCH24-*`** (`ARCH24-01`..`ARCH24-12`) ;
  - **`12` chantiers consolidés `REM24-*`** (`REM24-01`..`REM24-12` répartis en `3` vagues) ;
  - **Verdict porte de sortie Epic 23** : **`Case B -> Epic 24`** (`Stories 24.1`..`24.7` à initialiser et planifier en `Story 23.8`).
- **Registre `docs/product/capabilities.yaml` (`65` capacités `live`)** :
  - **`39` `verification: runtime`** (`36` `feature` Desktop `100 % PASS` vérifiées au `2026-11-20` + `3` `foundation` `CAP-006`, `CAP-100`, `CAP-202`) ;
  - **`26` `verification: failed_e2e`** (`25` `feature` rattachées aux `6` specs en échec vers `23-8-rapports-tech-lead-plan-correction-global-et-initialisation-epic-24` + `CAP-042` Mobile Companion maintenue vers `ACTION_ITEM-23.6`).

### 3.3 Validation & Procédure de Test sur Toute la Pyramide (`AD-17` + 5 Garde-Fous de Câblage Vertical)
- `pnpm site:sync && pnpm site:check` : **OK** (`0` erreur ; `65/65` capacités live avec test, `62/62` E2E fonctionnels, `20/20` UJ, `39` `runtime`, `193` rapports, `28` routes, `136` primitives UI).
- `.venv/bin/python scripts/check_implementation_docs.py` : **OK** (`193/193` rapports Tech Lead conformes et indexés dans `README.md`).
- `.venv/bin/ruff check infra/scripts tests/unit/` & `.venv/bin/ruff format --check infra/scripts tests/unit/` : **OK** (`0` erreur, `156` fichiers conformes).
- `.venv/bin/pytest tests/unit/test_uj_e2e_coverage_gate.py tests/unit/test_capabilities_registry.py tests/unit/test_e2e_sql_coverage_audit.py tests/unit/test_epic22_to_epic23_traceability.py tests/unit/test_site_catalog_sync.py -q` : **`34 passed`** (`0` échec, `0` skip).
- Contrôle `pre-commit` taille fichiers `docs/implementation-artifacts/e2e-campaign-epic-23/` : `64 / 64` fichiers strictement `< 450 KB` (`0` dépassement) ; `docs/implementation-artifacts/e2e-campaign-epic-21/` et `e2e-campaign-epic-22/` intouchés.
