# Story 23.8 — Clôture Epic 23, Bilan Conditionnel (`52/52` PASS Desktop & `0` `P0`/`P1` $\rightarrow$ Sans Epic 24 Vide) & Éventuelle Initialisation Epic 24

> **Convention de nommage du fichier (Obligatoire — à créer AVANT toute modification de code)** :
> - User Story du sprint : `docs/implementation-artifacts/tech-lead-reports/{story-key}-tech-lead-report.md`

- **Date** : 2026-11-20 *(initialisé 2026-11-19)*
- **Story / Clé Sprint** : `23-8-rapports-tech-lead-plan-correction-global-et-initialisation-epic-24` (`Epic 23` — Clôture Conditionnelle `Case B` & Initialisation `Epic 24`)
- **Capacité(s)** : `none (gouvernance documentaire & clôture Epic 23 — rattache CAP-042 à ACTION_ITEM-23.6 et transfère les 25 capacités Desktop failed_e2e vers Epic 24)` — classification : `doc`
- **Auteur / Contexte** : `23.0-impl` (Step 0), `23.6a-doc-init` (recadrage RCA), **`23.8-impl` / Winston & `23.8-test`** (2026-11-20 — déclenchement **`Case B`** sur `a1cca38` / `dd2d382` : `44 passed / 7 failed / 1 timedOut / 3 skipped` = `8` échecs/timeouts Desktop, `1 P0` + `9 P1` Sally).
- **Commits associés** : `feat/epic-23-remediation-pg18-sse-direction-c` (clôture `Story 23.8` après `a1cca38`)

---

## 1. Analyse du Besoin & Étude d'Impact Tech Lead (Pré-Implémentation)

### 1.1 Contexte & Problématique
- **Exploitation rigoureuse et sans artefact bureaucratique des constats de `Story 23.7`** :
  - Une fois la campagne intégrale figée Desktop `e2e-campaign-epic-23/` (`--project=desktop-cockpit`) et l'audit croisé **Sally × Winston** achevés (`Story 23.7`), la décision de clôture suit une règle binaire claire :
    1. **Condition de clôture sans Epic 24 (`52/52` PASS Desktop et `0` écart `P0`/`P1`)** : si les `52` scénarios Desktop exécutés passent à `100 %` et que Sally × Winston ne relèvent aucun écart `P0`/`P1`, l'Epic 23 est clôturé proprement (`epic-23: done`) **sans initialiser d'Epic 24 artificiel vide** (`CAP-042` / Mobile Companion restant tracés sous `ACTION_ITEM-23.6` dans `sprint-status.yaml`).
    2. **Condition d'initialisation de l'Epic 24 (si échec Desktop `> 0` ou écart `P0`/`P1` `> 0`)** : tout reliquat est converti en `K` lots cohérents (`Story 24.1`..`Story 24.K`) avec rapports Tech Lead individuels pré-implémentation conformes à `TECH-LEAD-REPORT-TEMPLATE.md`, basés sur GitNexus (`repo: "/home/romain/Documents/Projects/ORCIA"`), plan directeur global et suite `tests/unit/test_epic23_to_epic24_traceability.py`.
- **Obligations du Protocole Tech Lead (`GEMINI.md`)** :
  - Dans les deux cas, aucune capacité `failed_e2e` autre que `CAP-042` (`e2e_remediation_ref: "ACTION_ITEM-23.6"`) ne peut conserver une référence obsolète `23-*` une fois l'Epic 23 clôturé.
  - Toutes les vérifications statiques et documentaires (`check_implementation_docs.py`, `pnpm site:sync && pnpm site:check`, `test_epic22_to_epic23_traceability.py`, pyramide `AD-17`) doivent passer à `0` erreur.

### 1.2 Exploration, Analyse d'Impact GitNexus, Factorisation & Dette Technique
- **Périmètre d'analyse GitNexus planifié post-`23.7`** :
  - Rafraîchir l'index (`npx gitnexus analyze`) après les modifications de `23.1`–`23.6` avant de lancer `gitnexus_query`, `gitnexus_context` et `gitnexus_impact({direction: "upstream", repo: "/home/romain/Documents/Projects/ORCIA"})` sur tous les symboles touchés par les constats de `synthese-remediation-sally-winston-epic-23.md`.
- **Modèle de référence structurel** :
  - S'appuyer sur le modèle éprouvé de `Story 22.10` ([`22-10-rapports-tech-lead-plan-correction-global-et-initialisation-epic-23-tech-lead-report.md`](./22-10-rapports-tech-lead-plan-correction-global-et-initialisation-epic-23-tech-lead-report.md)) et de `tests/unit/test_epic22_to_epic23_traceability.py`.
- **Contrôle de volumétrie & factorisation** :
  - Identifier dès le cadrage des Stories `24.1`..`24.K` tout fichier approchant ou dépassant `300–400` lignes ainsi que les opportunités `DRY` transverses (`@orcia/ui`, `packages/api-client`, `packages/orcia-core`).
- **Verrou automatique de traçabilité** :
  - Création de `tests/unit/test_epic23_to_epic24_traceability.py` garantissant `100 %` de couverture des livrables `e2e-campaign-epic-23/`, des items Sally × Winston (`synthese-remediation-sally-winston-epic-23.md`), des `CAP-*` éventuelles en `failed_e2e` et de la cohérence `epics.md` ↔ `sprint-status.yaml` ↔ `tech-lead-reports/README.md`.

---

## 2. Plan d'Implémentation

### 2.1 Schéma de Données & Migrations Alembic (`infra/migrations/versions/`)
- Aucune migration Alembic appliquée directement en `Story 23.8` (`doc` + suite de traçabilité uniquement). Tout besoin éventuel de migration issu de `23.7` est spécifié en Section 2.1 des rapports Tech Lead `24-1`..`24-K`.

### 2.2 Noyau Métier Hexagonal, Orchestration & Workers (`packages/orcia-core/`, `apps/worker/`)
- Aucune modification de code applicatif dans `Story 23.8`. Les évolutions ou correctifs backend/domaine identifiés en `23.7` sont spécifiés avec leurs contrats hexagonaux `AD-1`..`AD-24` dans les rapports `24-k-*`.

### 2.3 Couche Backend API, Sécurité & Contrats (`apps/api/`, `packages/api-client/`)
- Aucune modification d'endpoint dans `Story 23.8`. Les ajustements API/OpenAPI 3.1 nécessaires pour l'Epic 24 sont détaillés dans les rapports `24-k-*`.

### 2.4 Documentation Planification, Clôture Epic 23 & Initialisation Conditionnelle Epic 24 (`docs/`)
1. **Évaluation du critère de sortie `23.7` (`52/52` PASS Desktop & `0` écart `P0`/`P1`)** :
   - **Si `52/52` PASS Desktop et `0` écart `P0`/`P1`** : passer `23-8-...: done` et `epic-23: done` dans `sprint-status.yaml`, vérifier que `CAP-042` pointe vers `ACTION_ITEM-23.6`, **ne pas créer d'Epic 24 artificiel vide**, et documenter le bilan final de clôture dans le présent rapport.
   - **Sinon (reliquat Desktop ou écart `P0`/`P1` > 0)** :
     - Rédiger `K` rapports Tech Lead individuels (`24-1-...`..`24-K-...`) conformes à `TECH-LEAD-REPORT-TEMPLATE.md` et les indexer dans `docs/implementation-artifacts/tech-lead-reports/README.md`.
     - Rédiger `docs/planning-artifacts/sprint-change-proposal-2026-11-19-epic-24-remediation-plan.md`, initialiser `Epic 24` dans `epics.md`, `sprint-status.yaml` (`epic-24: backlog`) et `capabilities.yaml`, puis créer `tests/unit/test_epic23_to_epic24_traceability.py`.

### 2.5 Analyse d'Impact sur la Pyramide des Tests (`AD-17` — Couches 1 à 5 + Sécurité, Obligatoire)
- **Couche 1a (`pytest`)** : adaptation finale de `tests/unit/test_epic22_to_epic23_traceability.py` (`23-7: done` + `23-8: done`) et, uniquement si un Epic 24 est nécessaire (`échec Desktop > 0` ou `écart P0/P1 > 0`), création de `tests/unit/test_epic23_to_epic24_traceability.py`.
- **Gouvernance documentaire & Vitrine** : `.venv/bin/python scripts/check_implementation_docs.py`, `pnpm site:sync && pnpm site:check`, `.venv/bin/ruff check/format`, `.venv/bin/lint-imports`, `.venv/bin/python .agent/skills/bmad-architecture/scripts/lint_spine.py`.

---

## 3. Bilan des Modifications & Résultats (Post-Implémentation)

### 3.1 Fichiers Développés & Modifiés
| Fichier | Nature | Description synthétique |
| :--- | :--- | :--- |
| `docs/planning-artifacts/sprint-change-proposal-2026-11-20-epic-24-remediation-plan.md` | Création (`23.8-impl`) | Plan directeur `Case B` post-`23.7` (`3` vagues, diagramme Mermaid, matrices `8/8` échecs/timeouts, `12/12` `REM24-*`, `17/17` `UX23-*`, `12/12` `ARCH24-*`, `25` `CAP-*` Desktop + `CAP-042` sous `ACTION_ITEM-23.6`) |
| `docs/implementation-artifacts/tech-lead-reports/24-{1..7}-*-tech-lead-report.md` | Création (`23.8-impl`) | `7` rapports Tech Lead pré-implémentation individuels (`24-1`..`24-7`, Sections 1 & 2, analyse d'impact GitNexus & découpage `< 350` L) |
| `docs/planning-artifacts/epics.md` | Modification (`23.8-impl`) | Ajout `Epic 24` (`Stories 24.1`..`24.7` `Given/When/Then`) et mise à jour de l'`Epic List` / couverture `CAP-*` |
| `docs/implementation-artifacts/sprint-status.yaml` | Modification (`23.8-impl`) | Clôture `epic-23: done` + `23-8-...: done` et initialisation `epic-24: backlog` + `24-1..24-7: backlog` (`epic-24-retrospective: optional`) |
| `docs/product/capabilities.yaml` | Modification (`23.8-impl`) | Réaffectation des `25` capacités Desktop `failed_e2e` vers `24-1..24-7` (`0` reliquat `23-*`), maintien `CAP-042 -> ACTION_ITEM-23.6` (`39 runtime + 26 failed_e2e = 65`) |
| `tests/unit/test_epic23_to_epic24_traceability.py` | Création (`23.8-test`) | Suite automatisée (`252` L, `4/4` tests) vérifiant `e2e-campaign-epic-23/`, `8/8` échecs, `17/17` `UX23-*`, `12/12` `ARCH24-*`, `12/12` `REM24-*`, `25/25` `CAP-* -> 24-*`, `CAP-042 -> ACTION_ITEM-23.6`, `24-1..24-7`, `epics.md` & `README.md` |
| `tests/unit/test_epic22_to_epic23_traceability.py`, `tests/unit/test_epic21_to_epic22_traceability.py` | Modification (`23.8-test`) | Verrouillage post-clôture `epic-23: done` / `23-8: done` (zéro reliquat `23-*`, acceptation des clés `24-*` dans `capabilities.yaml`) |
| `docs/implementation-artifacts/tech-lead-reports/{23-8-...,README}.md` | Modification (`23.8-test`) | Rédaction Section 3 de clôture (`23.8`) et indexation des `7` rapports `24-1..24-7` + mise à jour `Story 23.8` (`Clôture (done)`) dans `README.md` (`200` rapports) |
| `apps/web/src/generated/orciaSiteManifest.ts`, `docs/site-catalog/index.html`, `dist/orcia-site/index.html` | Régénération (`pnpm site:sync`) | Synchronisation de la vitrine produit (`200` rapports, `28` routes, `136` primitives UI, `65/65` capacités, `39` `runtime`, `20/20` UJ) |

### 3.2 Résultats Chiffrés, Métriques & Qualité
- **Verdict de sortie Epic 23 (`Case B -> Epic 24`) & Traçabilité (`100 %`)** :
  - Campagne `e2e-campaign-epic-23/` (`dd2d382`) : `44 passed / 7 failed / 1 timedOut / 3 skipped / 0 flaky` (`55` entrées `manifest.jsonl`, `58` PNG `< 450 KB`).
  - Couverture `100 %` vers Epic 24 : `8/8` échecs/timeouts (`06 #15`, `07 #16`, `17#3 #40`, `18#1 #41`, `18#5 #45`, `19#2 #47`, `20#1 #48`, `20#2 #49`), `17/17` `UX23-01..UX23-17`, `12/12` `ARCH24-01..ARCH24-12`, `12/12` `REM24-01..REM24-12`, `25/25` `CAP-*` Desktop `failed_e2e` vers `24-1..24-7` (`0` reliquat `23-*`), `CAP-042` maintenue sur `ACTION_ITEM-23.6`.
- **Qualité Statique, Architecture & TypeScript (`0` erreur)** :
  - `pnpm site:sync && pnpm site:check` : **OK** (`200` rapports, `28` routes, `136` primitives UI, `65/65` capacités live, `62/62` E2E fonctionnels, `20/20` UJ, `39` `runtime`).
  - `.venv/bin/python scripts/check_implementation_docs.py` : **OK** (`200 / 200` rapports conformes et indexés).
  - `.venv/bin/ruff check packages/ apps/ tests/ infra/ scripts/` & `ruff format --check` : **`0` erreur** (`865` fichiers formatés).
  - `.venv/bin/mypy --strict packages/orcia-core packages/orcia-connectors apps/api apps/worker` (`553` fichiers) & `MYPYPATH=infra/scripts/e2e:infra/scripts/maintenance .venv/bin/mypy --strict` (`3` fichiers reset Jour 0) : **`0` erreur**.
  - `.venv/bin/lint-imports` : **`5 contracts kept, 0 broken`** (`599` files, `4 302` dependencies).
  - `.venv/bin/python scripts/export_openapi.py --check` : **`0-diff`**.
  - `.venv/bin/python .agent/skills/bmad-architecture/scripts/lint_spine.py` : **`0 findings`**.
  - `pnpm turbo run lint typecheck test --force --concurrency=2` : **`9 / 9` tâches vertes** (`@orcia/api-client`: `20/20` sur `3` fichiers, `@orcia/ui`: `124/124` sur `30` fichiers, `@orcia/web`: `218/218` sur `55` fichiers = **`362 / 362` tests JS/TS**).
  - Contrôle taille fichiers créés/modifiés : tous les nouveaux fichiers (`24-1..24-7`, plan directeur, `test_epic23_to_epic24_traceability.py`, `orciaSiteManifest.ts`, `docs/site-catalog/index.html` `362.4 KB`) sont `< 450 KB` (`epics.md` existant `510.6 KB` sur disque depuis `487.2 KB` sur `HEAD`).

### 3.3 Validation & Procédure de Test sur Toute la Pyramide (`AD-17` + 5 Garde-Fous de Câblage Vertical)
- **Pyramide Python (`AD-17`)** :
  - `.venv/bin/pytest tests/unit/ tests/security/ tests/conformance/ tests/contract/ -q` : **`961 passed`** (`0` fail, `0` skip).
  - `.venv/bin/pytest tests/integration/test_e2e_reset_day0_postgres18_and_redis.py tests/integration/test_contextual_help_and_accostage_postgres18.py tests/integration/api/test_story_23_5_federated_search_postgres18.py -q` : **`4 passed`** sur conteneurs réels PostgreSQL 18 + Redis 7.4.
  - Mesure de couverture unitaires `.venv/bin/pytest tests/unit/ --cov=packages/orcia-core/src/orcia_core -q` : **`843 passed`** sans exclusion de `test_alembic_0021`, couverture unitaires seuls sur `packages/orcia-core/src/orcia_core` = **`84 %`** (`23 467` instructions, `3 135` manquées principalement dans `_internal/sql_*.py` exercés par `tests/integration/`).
  - `.venv/bin/pytest tests/unit/test_epic21_to_epic22_traceability.py tests/unit/test_epic22_to_epic23_traceability.py tests/unit/test_epic23_to_epic24_traceability.py -v` : **`16 passed`** (`0` fail).
- **Intégrité campagnes & GitNexus** :
  - `docs/implementation-artifacts/e2e-campaign-epic-21/`, `e2e-campaign-epic-22/` et `e2e-campaign-epic-23/` strictement intouchés ; zéro modification de code applicatif (`packages/`, `apps/` hors régénération `site:sync`).
  - Index GitNexus rafraîchi (`npx gitnexus analyze`) et état Git propre après commit atomique `Story 23.8`.
