# Story 23.7 — Campagne Playwright E2E Intégrale Epic 23, Captures PNG d'État Final (`110/110`), Bilan Exhaustif & Audit Croisé Sally × Winston

> **Convention de nommage du fichier (Obligatoire — à créer AVANT toute modification de code)** :
> - User Story du sprint : `docs/implementation-artifacts/tech-lead-reports/{story-key}-tech-lead-report.md`

- **Date** : 2026-11-19
- **Story / Clé Sprint** : `23-7-campagne-e2e-integrale-captures-png-bilan-et-audit-croise-sally-winston` (`Epic 23` — Vague 3 / Campagne Intégrale Figée & Audit Croisé)
- **Capacité(s)** : Vérification runtime réelle de `100 %` des `65` capacités (`62` `feature` + `3` `foundation`, `CAP-001`..`CAP-203`) dans `docs/product/capabilities.yaml` — classification : `hygiène`
- **Auteur / Contexte** : `23.0-impl` (initialisation Step 0 Epic 23 sur le modèle `Story 22.9`) — Exécution sans retouche de code applicatif de la campagne Playwright E2E intégrale post-stabilisation `23.1`–`23.6` (`--retries=0 --max-failures=0 --timeout=35000`, `0` `ORCIA_E2E_SEED_FIXTURES`), archivage des `110/110` captures PNG d'état final dans `docs/implementation-artifacts/e2e-campaign-epic-23/`, rédaction du bilan exhaustif `bilan-execution-tests-e2e-epic-23.md`, audit croisé **Sally (UX) × Winston (Architecture)**, bascule de `PLAYWRIGHT_RESULTS_PATH` dans `infra/scripts/uj_e2e_coverage.py` et mise à jour honnête de `docs/product/capabilities.yaml` (`AD-17`, `NFR-TEST-1`, `GEMINI.md` §5).
- **Commits associés** : `En attente d'implémentation (initialisé en Step 0 Epic 23)`

---

## 1. Analyse du Besoin & Étude d'Impact Tech Lead (Pré-Implémentation)

### 1.1 Contexte & Problématique
- **Séparation stricte entre stabilisation/audit SQL (`23.6`), campagne figée & audit croisé (`23.7`), et initialisation Epic 24 (`23.8`)** :
  - À l'issue de la `Story 23.6`, les Vagues 0, 1 et 2 (`23.1`..`23.6`) ont débloqué `resetDay0()`, sécurisé les flux SSE authentifiés (`createRequestSse`), aligné Zone 4 / Accostage `X/6` / Cockpit Direction C, stabilisé les specs `04`–`21` + `shell.spec.ts` + `mobile-companion` (`390×844`) et garanti par audit que `55/55` blocs `test(...)` E2E exécutent des assertions SQL PostgreSQL 18 effectives sur les tables du domaine testé (`tests/unit/test_e2e_sql_coverage_audit.py`).
  - Il convient désormais d'exécuter une **campagne intégrale figée sans aucune retouche de code applicatif** sur la pile réelle (`PostgreSQL 18 + pgvector`, `Redis 7.4`, Alembic `head`, FastAPI + `DeterministicCassetteLLM` `0 $`, SPA Vite), en dirigeant les sorties vers le répertoire neuf **`docs/implementation-artifacts/e2e-campaign-epic-23/`** afin de préserver intégralement `e2e-campaign-epic-21/` et `e2e-campaign-epic-22/`.
- **Exigence de vérité sans maquillage ni angle mort** :
  - Zéro `test.skip` ou `test.fixme` destiné à masquer un échec (seuls les `13` skips de garde viewport Desktop vs Mobile prévus restent autorisés).
  - Les captures PNG d'état final (`110/110`) doivent couvrir **100 % des scénarios exécutés (succès comme échecs)**, accompagnées de `manifest.jsonl` (`110` entrées) et `playwright-results.json`, chaque fichier respectant strictement la limite `< 450 KB` (`460 800` octets) du hook `pre-commit`.
  - L'audit visuel de **Sally (UX/UI Direction C)** et l'audit architectural de **Winston (`AD-1`..`AD-24`)** doivent inspecter les captures Desktop (`1440×900`) et Mobile Companion (`390×844`) sur `00`–`21` + `shell.spec.ts` pour relever tout reliquat ou axe d'amélioration pour l'Epic 24.
  - `docs/product/capabilities.yaml` ne promeut à `verification: runtime` que les capacités dont `100 %` des specs associées sont vertes ; toute capacité encore en échec éventuel reste/passe honnêtement à `verification: failed_e2e` en vue de `Story 23.8`.

### 1.2 Exploration, Analyse d'Impact GitNexus, Factorisation & Dette Technique
- **Analyse d'Impact GitNexus & Inspection Directe (`repo: "/home/romain/Documents/Projects/ORCIA"`)** :
  - La sonde MCP `gitnexus_context` / `gitnexus_impact` sur `load_failed_e2e_specs` (`infra/scripts/uj_e2e_coverage.py`), `check_uj_e2e_coverage` (`infra/scripts/uj_e2e_coverage.py`) et `captureFinalState` (`apps/web/e2e/support/e2eCaptureFixture.ts`) confirme que ces scripts d'outillage CI/E2E hors package applicatif ne sont pas indexés comme symboles appelables dans le graphe GitNexus. L'étude d'impact a donc été complétée par inspection directe des fichiers :
    - `docs/implementation-artifacts/tech-lead-reports/23-6-campagne-e2e-integrale-mobile-companion-audit-et-62-capacites-runtime-tech-lead-report.md` : définit les préconditions Vagues 0–2 (`23.1`–`23.6`) avant lancement de la campagne.
    - `apps/web/e2e/support/e2eCaptureFixture.ts` (`L8-16`, `L80-112`) : piloté par `ORCIA_E2E_CAMPAIGN_DIR=docs/implementation-artifacts/e2e-campaign-epic-23` ; capture `fullPage: true` puis bascule sur `fullPage: false` si la taille dépasse `MAX_SCREENSHOT_BYTES` (`440 * 1024`), garantissant `< 450 KB` par capture PNG.
    - `infra/scripts/uj_e2e_coverage.py` (`L14-29`, `L112-261`) : lit `PLAYWRIGHT_RESULTS_PATH` (actuellement `docs/implementation-artifacts/e2e-campaign-epic-22/playwright-results.json`, surchargeable via `ORCIA_PLAYWRIGHT_RESULTS_PATH`) et bloque `pnpm site:check` si une capacité `verification: runtime` pointe vers une spec E2E en échec dans `playwright-results.json`.
    - `docs/implementation-artifacts/tech-lead-reports/22-9-campagne-e2e-integrale-captures-png-bilan-et-audit-croise-sally-winston-tech-lead-report.md` : modèle de référence des livrables et de la méthode d'audit.
- **Contraintes de volumétrie & séparation des rôles** :
  - Aucune retouche de code métier applicatif dans `Story 23.7` (seuls `PLAYWRIGHT_RESULTS_PATH` dans `infra/scripts/uj_e2e_coverage.py`, `docs/product/capabilities.yaml` et les artefacts régénérés par `pnpm site:sync` sont mis à jour avec les livrables de campagne).
  - Tout échec résiduel ou axe d'amélioration identifié pendant `23.7` est consigné dans `synthese-remediation-sally-winston-epic-23.md` pour traitement structuré dans `Story 23.8` (`Epic 24`).

---

## 2. Plan d'Implémentation

### 2.1 Schéma de Données & Migrations Alembic (`infra/migrations/versions/`)
- Aucune migration Alembic dans `Story 23.7`. Avant lancement de la campagne E2E, la base isolée `orcia_e2e` est remise au niveau `alembic upgrade head` et réinitialisée à l'état Jour 0 (`0` utilisateur) par le harnais `resetDay0()`.

### 2.2 Noyau Métier Hexagonal, Orchestration & Workers (`packages/orcia-core/`, `apps/worker/`)
- Aucune modification de code métier dans `Story 23.7` (campagne figée sur l'état stabilisé en `Story 23.6`). Toute anomalie `AD-1`..`AD-24`, divergence SQL PG18 ou latence observée durant la campagne est consignée dans `notes-audit-winston-architecture.md` et `synthese-remediation-sally-winston-epic-23.md`.

### 2.3 Couche Backend API, Sécurité & Contrats (`apps/api/`, `packages/api-client/`)
- Aucune modification d'endpoint ou de schéma OpenAPI dans `Story 23.7`. Les éventuels statuts `4xx`/`5xx` inattendus ou écarts de contrat observés lors du run Playwright sont documentés dans `bilan-execution-tests-e2e-epic-23.md` et `notes-audit-winston-architecture.md`.

### 2.4 Livrables Campagne E2E, Audit Croisé & Registre (`docs/`, `infra/scripts/`)
1. **Exécution Playwright intégrale figée (`ORCIA_E2E_CAMPAIGN_DIR=docs/implementation-artifacts/e2e-campaign-epic-23`)** :
   - Commande cible : `CI=1 ORCIA_E2E_CAMPAIGN_DIR=docs/implementation-artifacts/e2e-campaign-epic-23 PLAYWRIGHT_JSON_OUTPUT_NAME=docs/implementation-artifacts/e2e-campaign-epic-23/playwright-results.json timeout --kill-after=30s 2400s pnpm --filter @orcia/web exec playwright test --retries=0 --max-failures=0 --timeout=35000 --reporter=list,json`.
   - Archivage de `playwright-results.json`, `manifest.jsonl` (`110` entrées) et `110/110` captures PNG sous `docs/implementation-artifacts/e2e-campaign-epic-23/screenshots/**/*.png` (tous fichiers `< 450 KB`).
2. **Bilan Factuel & Audit Croisé Sally × Winston** :
   - `docs/implementation-artifacts/e2e-campaign-epic-23/bilan-execution-tests-e2e-epic-23.md` : décompte exact (`passed`, `failed`, `timedOut`, `skipped`), comparaison Epic 22 → Epic 23, matrice `CAP ↔ UJ ↔ Spec ↔ F5/SQL`, synthèse des éventuels reliquats et liens vers captures.
   - `docs/implementation-artifacts/e2e-campaign-epic-23/notes-audit-sally-ux.md` : inspection visuelle exhaustive des captures Desktop (`1440×900`) et Mobile Companion (`390×844`) sur les écrans `00`–`21` + `shell.spec.ts` (Direction C, contraste WCAG AA, sobriété, langue FR).
   - `docs/implementation-artifacts/e2e-campaign-epic-23/notes-audit-winston-architecture.md` : audit architectural (`AD-1`..`AD-24`, persistance PG18, flux SSE, latences).
   - `docs/implementation-artifacts/e2e-campaign-epic-23/synthese-remediation-sally-winston-epic-23.md` : table de synthèse priorisée (`P0`..`P3`) de tout reliquat ou amélioration recommandée pour l'Epic 24 (`REM24-*`).
3. **Vérité Registre & Vitrine** :
   - Bascule de `PLAYWRIGHT_RESULTS_PATH` dans `infra/scripts/uj_e2e_coverage.py` vers `docs/implementation-artifacts/e2e-campaign-epic-23/playwright-results.json`.
   - Mise à jour honnête de `docs/product/capabilities.yaml` (`verification: runtime` + `verified_at` pour chaque capacité dont `100 %` des specs sont vertes ; `verification: failed_e2e` pour tout reliquat éventuel).
   - Exécution de `pnpm site:sync && pnpm site:check` (`0` erreur).

### 2.5 Analyse d'Impact sur la Pyramide des Tests (`AD-17` — Couches 1 à 5 + Sécurité, Obligatoire)
- **Couche 1a (`pytest`)** : `.venv/bin/pytest tests/unit/test_uj_e2e_coverage_gate.py tests/unit/test_capabilities_registry.py tests/unit/test_e2e_sql_coverage_audit.py` — cohérence stricte `capabilities.yaml` ↔ `playwright-results.json` ↔ `prd.md` ↔ `55/55` assertions SQL PG18.
- **Couche 3 / Vitrine** : `pnpm site:sync && pnpm site:check`, `.venv/bin/python scripts/check_implementation_docs.py` — `0` erreur sur les `65` capacités, `20/20` UJ et le registre des rapports Tech Lead.
- **Couche 5 (Playwright E2E)** : exécution intégrale des `110` scénarios (`24` specs Desktop `1440×900` + Mobile Companion `390×844`) sur pile réelle PG18 + Redis 7.4 sans `ORCIA_E2E_SEED_FIXTURES` ni retry.

---

## 3. Bilan des Modifications & Résultats (Post-Implémentation)

> *[Pré-implémentation initialisée en Step 0 Epic 23 — à compléter après exécution de la Story 23.7]*

### 3.1 Fichiers Développés & Modifiés
| Fichier | Nature (Création / Modification / Refactoring) | Description synthétique |
| :--- | :--- | :--- |
| `docs/implementation-artifacts/e2e-campaign-epic-23/*` | Création | *[À compléter après exécution Story 23.7 : `playwright-results.json`, `manifest.jsonl`, `screenshots/**/*.png`, `bilan-execution-tests-e2e-epic-23.md`, `notes-audit-*.md`, `synthese-remediation-sally-winston-epic-23.md`]* |
| `infra/scripts/uj_e2e_coverage.py` & `docs/product/capabilities.yaml` | Modification | *[À compléter après exécution Story 23.7]* |

### 3.2 Résultats Chiffrés, Métriques & Qualité
- **Campagne E2E Epic 23** : *[Objectif : `97 / 97` exécutés PASS, `0` failed, `0` timedOut, `13` skipped viewport, `110/110` PNG `< 450 KB` ; mise à jour honnête de `capabilities.yaml`]*
- **Qualité statique & Pyramide `AD-17`** : *[À compléter]*

### 3.3 Validation & Procédure de Test sur Toute la Pyramide (`AD-17` + 5 Garde-Fous de Câblage Vertical)
- *[À compléter après clôture de la campagne figée `e2e-campaign-epic-23`, de l'audit croisé Sally × Winston et de `pnpm site:sync && pnpm site:check`]*
