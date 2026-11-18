# Story 21.8 — Campagne E2E Intégrale, Captures PNG, Bilan & Analyse Croisée Sally × Winston

- **Date** : 2026-11-18
- **Story / Clé Sprint** : `21-8-campagne-e2e-integrale-captures-bilan-audit-sally-winston-et-capabilities` (`Epic 21`)
- **Capacité(s)** : `CAP-001`..`CAP-203` (audit exhaustif des `65` capacités du registre `docs/product/capabilities.yaml`) — classification : `hygiène`
- **Auteur / Contexte** : `21.8-impl` (Synthèse & Vérité Registre — consolidation des livrables `21.8-test`, `21.8-sally` et `21.8-winston` sur la branche `feat/epic-21-user-journeys-e2e-db-audit`, `AD-17`, `GEMINI.md` §5)
- **Commits associés** : `575cf4a` (exécution campagne E2E), commit Story `21.8` à venir

---

## 1. Analyse du Besoin & Étude d'Impact Tech Lead (Pré-Implémentation)

### 1.1 Contexte & Problématique
- **Objectif de la Story 21.8** : Après l'exécution complète sans retry ni arrêt anticipé (`--retries=0 --max-failures=0 --timeout=35000`) des `24` fichiers Playwright (`00..21` + `shell.spec.ts`) sur les deux viewports (`desktop-cockpit` `1440×900` et `mobile-companion` `390×844`) contre une pile réelle éphémère (`PostgreSQL 18 + pgvector`, `Redis 7.4`, Alembic `head`, FastAPI + cassette LLM `0 $`, SPA Vite), consolider :
  1. Le dialogue croisé **Sally (UX)** × **Winston (Architecture)** et la table maîtresse exhaustive de remédiation (`REM-01`..`REM-NN`) dans `docs/implementation-artifacts/e2e-campaign-epic-21/synthese-remediation-sally-winston-epic-21.md`.
  2. La mise à jour honnête de `docs/product/capabilities.yaml` selon la vérité mesurée dans `playwright-results.json` et les règles strictes de `infra/scripts/uj_e2e_coverage.py` (`load_failed_e2e_specs` / `check_uj_e2e_coverage`).
  3. La synchronisation du site vitrine (`pnpm site:sync && pnpm site:check`) et la clôture de la Story `21.8` dans `sprint-status.yaml` et `tech-lead-reports/README.md`.
- **État initial constaté** :
  - `playwright-results.json` (`405 164` octets) et `manifest.jsonl` (`110` entrées, `110/110` captures PNG présentes) enregistrent sur `110` scénarios planifiés : **`47` `passed`**, **`36` `failed`**, **`11` `timedOut`** (`47` échecs/timeouts au total, `26` Desktop / `21` Mobile), **`16` `skipped`** (uniquement gardes viewport), `0` `flaky`.
  - Sur `24` fichiers `.spec.ts` : **`10`** sont `100 %` verts (`00`, `01`, `05`, `08`, `09`, `10`, `11`, `12-epic16`, `12-finops`, `shell`) et **`14`** présentent au moins un `failed` ou `timedOut` (`02`, `03`, `04`, `06`, `07`, `13`, `14`, `15`, `16`, `17`, `18`, `19`, `20`, `21`).
  - Parallèlement, l'audit visuel de Sally sur **49 captures PNG** (dont **21 captures de tests `PASSED`**) et l'audit architectural de Winston révèlent des défauts transverses invisibles aux assertions automatiques actuelles (Mobile Companion absent, modale `Paramètres du compte` coupée par Zone 4, aide contextuelle droite figée sur `@1.1.0`, wrappers `display: none`, silos RAM vs PostgreSQL 18, schisme `"ws-1"` vs `UUID`, jargon technique résiduel).
  - Dans `docs/product/capabilities.yaml`, `15` capacités `kind: feature` portent encore `verification: runtime` alors qu'au moins une de leurs specs E2E a échoué dans `playwright-results.json`, ce qui viole la porte bloquante `check_uj_e2e_coverage` de `pnpm site:check`.

### 1.2 Exploration, Analyse d'Impact GitNexus, Factorisation & Dette Technique
- **Analyse d'Impact GitNexus (`repo: "/home/romain/Documents/Projects/ORCIA"`)** :
  - `gitnexus_query({search_query: "capabilities_registry run_registry_check load_failed_e2e_specs", repo: "/home/romain/Documents/Projects/ORCIA"})` confirme le rattachement du registre `infra/scripts/capabilities_registry.py` et signale un index en retard de `10` commits par rapport à `HEAD` (les scripts ajoutés en `21.3` nécessiteront un rafraîchissement d'index avant les chantiers d'Epic 22).
  - La lecture directe de `infra/scripts/uj_e2e_coverage.py` et `infra/scripts/capabilities_registry.py` confirme que `run_registry_check()` appelle `validate_registry()`, `check_coverage()` et `check_uj_e2e_coverage()` qui charge `PLAYWRIGHT_RESULTS_PATH` via `load_failed_e2e_specs()`.
- **Exploration & Chiffres Clés (Analyse `playwright-results.json` × `capabilities.yaml`)** :
  - Total des capacités dans `docs/product/capabilities.yaml` : **`65`** (`3` `kind: foundation` + `62` `kind: feature`).
  - `3` capacités `kind: foundation` conservent `verification: runtime` : `CAP-006`, `CAP-100`, `CAP-202`.
  - `11` capacités `kind: feature` ont **100 %** de leurs specs E2E vertes dans `playwright-results.json` : `CAP-004`, `CAP-005`, `CAP-042`, `CAP-060`, `CAP-061`, `CAP-062`, `CAP-065`, `CAP-083`, `CAP-090`, `CAP-091`, `CAP-160`.
  - `51` capacités `kind: feature` référencent au moins une spec E2E en échec/timeout (`load_failed_e2e_specs`) et doivent basculer honnêtement vers `verification: failed_e2e` avec `e2e_remediation_ref: "epic-22"`.
- **Opportunités de Factorisation & Résorption de Dette Technique Naissante** :
  - Regrouper les `47` échecs E2E, les constats UX/UI de Sally (y compris sur écrans `PASSED`) et les défauts d'architecture de Winston dans une table canonique `REM-01..REM-NN` structurée en **4 vagues d'exécution ordonnées** (`Vague 0` à `Vague 3`) pour préparer directement l'initialisation de l'Epic 22 en Story `21.9`.
  - Aucun code applicatif Python/TypeScript n'est modifié dans cette Story d'audit et de vérité registre : zéro dette supplémentaire introduite.

---

## 2. Plan d'Implémentation

### 2.1 Schéma de Données & Migrations Alembic (`infra/migrations/versions/`)
- Non applicable pour Story `21.8` (aucune modification de schéma ; les besoins de persistance SQL identifiés sont inventoriés dans `REM-xx` pour l'Epic 22).

### 2.2 Noyau Métier Hexagonal, Orchestration & Workers (`packages/orcia-core/`, `apps/worker/`, `infra/sandbox/`)
- Non applicable pour Story `21.8` (aucune modification de code applicatif ; les défauts RAM/DBOS/Broker sont tracés dans `synthese-remediation-sally-winston-epic-21.md`).

### 2.3 Couche Backend API, Sécurité & Contrats (`apps/api/`, `packages/api-client/`)
- Non applicable pour Story `21.8` (aucune modification d'endpoint ; les défauts de Composition Root, RBAC `403`, `404` Broker, `422` schemas sont tracés dans `REM-xx`).

### 2.4 Interface Utilisateur, Registre & Documentation (`apps/web/`, `docs/`)
1. Rédiger `docs/implementation-artifacts/e2e-campaign-epic-21/synthese-remediation-sally-winston-epic-21.md` :
   - Dialogue croisé Sally × Winston, arbitrage des `5` questions architecturales & UX, ordonnancement en `4` vagues (`Vague 0` → `Vague 3`).
   - Table maîtresse exhaustive `REM-01`..`REM-NN` couvrant **100 % des `47` échecs/timeouts E2E**, **100 % des constats UX/UI de Sally** (écrans `FAILED`/`TIMEDOUT` et `PASSED`) et **100 % des défauts d'architecture de Winston**, avec pour chaque ligne : `ID`, `Sévérité`, `Vague Epic 22`, `Titre & Cause Racine`, `Specs E2E & Captures PNG associées`, `Tables PG18 / Routes API / Composants UI impactés`, `CAP-* & UJ-*`, `Action de correction concrète`.
2. Mettre à jour `docs/product/capabilities.yaml` :
   - Conserver `verification: runtime` sur les `3` `foundation` (`CAP-006`, `CAP-100`, `CAP-202`).
   - Conserver/passer `verification: runtime` et `verified_at: "2026-11-18"` (sans `e2e_remediation_ref`) sur les `11` `feature` dont toutes les specs E2E sont vertes.
   - Passer `verification: failed_e2e` et `e2e_remediation_ref: "epic-22"` sur les `51` `feature` impactées par au moins une spec en échec.
3. Synchroniser le catalogue (`pnpm site:sync && pnpm site:check`), exécuter les tests du registre, compléter la Section 3 et clôturer Story `21.8` dans `tech-lead-reports/README.md` et `sprint-status.yaml`.

### 2.5 Analyse d'Impact sur la Pyramide des Tests (`AD-17`)
- **Couche 1a (`pytest`)** : `.venv/bin/pytest tests/unit/test_uj_e2e_coverage_gate.py tests/unit/test_capabilities_registry.py` — validation de l'alignement strict `capabilities.yaml` ↔ `playwright-results.json` ↔ `prd.md`.
- **Couche 3 / Cohérence Registre & Vitrine** : `pnpm site:sync && pnpm site:check` — vérification `0` erreur sur les `65` capacités, `20/20` UJ, routes SPA et routeurs FastAPI, et synchronisation de `orciaSiteManifest.ts` / `docs/site-catalog/index.html`.
- **Couche 5 (E2E)** : Exploitation directe de `playwright-results.json` (`110` cas, `24` specs) comme preuve de vérité pour `capabilities.yaml`.

---

## 3. Bilan des Modifications & Résultats (Post-Implémentation)

### 3.1 Fichiers Développés & Modifiés
| Fichier | Nature (Création / Modification / Refactoring) | Description synthétique |
| :--- | :--- | :--- |
| `docs/implementation-artifacts/e2e-campaign-epic-21/synthese-remediation-sally-winston-epic-21.md` | Création | Synthèse du dialogue croisé Sally × Winston, ordonnancement en `4` vagues (`Vague 0` → `Vague 3`) et table maîtresse exhaustive `REM-01`..`REM-34` couvrant `47/47` échecs E2E, `49` captures PNG Sally (incluant écrans `PASSED`) et constats Winston. |
| `docs/product/capabilities.yaml` | Modification | Mise à jour honnête de `verification` d'après `playwright-results.json` (`load_failed_e2e_specs`) : `3` `foundation` + `11` `feature` en `runtime` (`verified_at: "2026-11-18"`), `51` `feature` en `failed_e2e` (`e2e_remediation_ref: "epic-22"`). |
| `docs/implementation-artifacts/tech-lead-reports/21-8-campagne-e2e-captures-bilan-et-analyse-croisee-sally-winston-tech-lead-report.md` | Création | Rapport Tech Lead pérenne de la Story `21.8` (Sections 1, 2 et 3). |
| `docs/implementation-artifacts/tech-lead-reports/README.md` | Modification | Enregistrement de `Story 21.8` dans l'index (`171` rapports). |
| `docs/implementation-artifacts/sprint-status.yaml` | Modification | Clôture de `21-8-campagne-e2e-integrale-captures-bilan-audit-sally-winston-et-capabilities: done` et mise à jour de `last_updated: 11-18-2026 11:00`. |
| `apps/web/src/generated/orciaSiteManifest.ts` | Régénération (`pnpm site:sync`) | Synchronisation du manifeste (`verifiedCapabilitiesCount: 14`, `techLeadReportsCount: 171`). |
| `docs/site-catalog/index.html` & `dist/orcia-site/index.html` | Régénération (`pnpm site:sync`) | Synchronisation du site vitrine statique autonome. |

### 3.2 Résultats Chiffrés, Métriques & Qualité
- **Campagne E2E Epic 21 (`playwright-results.json` & `manifest.jsonl`)** :
  - `110` scénarios planifiés sur `24` specs (`10` specs `100 %` vertes / `14` specs avec `>= 1` échec ou timeout) : **`47` `passed`**, **`36` `failed`**, **`11` `timedOut`**, **`16` `skipped`** (gardes viewport), `0` `flaky`.
  - `110 / 110` captures PNG archivées (`0` fichier `> 450 KB`).
- **Répartition finale `docs/product/capabilities.yaml` (`65` capacités)** :
  - `3` `kind: foundation` conservées en `verification: runtime` (`CAP-006`, `CAP-100`, `CAP-202`).
  - `11` `kind: feature` en `verification: runtime` (`verified_at: "2026-11-18"`) : `CAP-004`, `CAP-005`, `CAP-042`, `CAP-060`, `CAP-061`, `CAP-062`, `CAP-065`, `CAP-083`, `CAP-090`, `CAP-091`, `CAP-160`.
  - `51` `kind: feature` en `verification: failed_e2e` (`e2e_remediation_ref: "epic-22"`) : `CAP-001`, `CAP-002`, `CAP-003`, `CAP-010`, `CAP-011`, `CAP-020`, `CAP-021`, `CAP-022`, `CAP-023`, `CAP-024`, `CAP-030`, `CAP-031`, `CAP-032`, `CAP-033`, `CAP-040`, `CAP-041`, `CAP-043`, `CAP-050`, `CAP-051`, `CAP-052`, `CAP-053`, `CAP-054`, `CAP-055`, `CAP-056`, `CAP-057`, `CAP-058`, `CAP-063`, `CAP-064`, `CAP-066`, `CAP-067`, `CAP-068`, `CAP-069`, `CAP-070`, `CAP-071`, `CAP-072`, `CAP-073`, `CAP-074`, `CAP-075`, `CAP-076`, `CAP-080`, `CAP-081`, `CAP-082`, `CAP-084`, `CAP-092`, `CAP-140`, `CAP-150`, `CAP-180`, `CAP-190`, `CAP-200`, `CAP-201`, `CAP-203`.
- **Synthèse de remédiation (`REM-01` .. `REM-34`)** : `34` chantiers structurés sur `4` vagues (`Vague 0` : `7`, `Vague 1` : `9`, `Vague 2` : `7`, `Vague 3` : `11`).
- **Qualité statique & Architecture** :
  - `pnpm site:sync && pnpm site:check` : `0` erreur (`[capabilities] 65/65 capacités live référencent au moins un test (0 sans test) · E2E fonctionnels: 62/62 · UJ: 20/20. [site:check OK] Manifest (171 reports, 28 routes, 133 UI primitives) is in sync.`).
  - `.venv/bin/pytest tests/unit/test_uj_e2e_coverage_gate.py tests/unit/test_capabilities_registry.py` : **`22 passed in 0.88s`**.
  - `gitnexus:detect_changes({repo: "/home/romain/Documents/Projects/ORCIA", scope: "all"})` : `changed_count: 1` (`ORCIA_SITE_MANIFEST` dans `apps/web/src/generated/orciaSiteManifest.ts`), `affected_count: 0`, `risk_level: "low"`.

### 3.3 Validation & Procédure de Test sur Toute la Pyramide (`AD-17`)
- **Couche 1a — Tests Unitaires Registre & Porte CI (`pytest`)** : `22 passed in 0.88s` sur `test_uj_e2e_coverage_gate.py` et `test_capabilities_registry.py` (`check_uj_e2e_coverage` vérifie la cohérence stricte avec `playwright-results.json`).
- **Couche 3 — Cohérence Vitrine & Registre (`pnpm site:sync && pnpm site:check`)** : `0` erreur sur les `65` capacités, `20/20` UJ, `28` routes SPA et tous les routeurs FastAPI.
- **Couche 5 — Campagne E2E Bi-Serveur Playwright (`playwright-results.json`)** : Base de preuve directe utilisée pour la mise à jour de `capabilities.yaml` (`14` capacités `runtime`, `51` `failed_e2e`).
