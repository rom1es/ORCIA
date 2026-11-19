# Story 23.8 — Clôture Epic 23, Bilan Conditionnel (`52/52` PASS Desktop & `0` `P0`/`P1` $\rightarrow$ Sans Epic 24 Vide) & Éventuelle Initialisation Epic 24

> **Convention de nommage du fichier (Obligatoire — à créer AVANT toute modification de code)** :
> - User Story du sprint : `docs/implementation-artifacts/tech-lead-reports/{story-key}-tech-lead-report.md`

- **Date** : 2026-11-19
- **Story / Clé Sprint** : `23-8-rapports-tech-lead-plan-correction-global-et-initialisation-epic-24` (`Epic 23` — Clôture Conditionnelle & Initialisation `Epic 24` uniquement si écart `P0`/`P1` ou échec Desktop)
- **Capacité(s)** : `none (gouvernance documentaire & clôture Epic 23 — rattache CAP-042 à ACTION_ITEM-23.6 et, uniquement si échec Desktop ou écart P0/P1 résiduel en 23.7, initialise Epic 24)` — classification : `doc`
- **Auteur / Contexte** : `23.0-impl` (initialisation Step 0 Epic 23), mis à jour `23.6a-doc-init` (2026-11-19 — recadrage RCA Epic 22). Consolide les résultats de la campagne Desktop `23.7` (`--project=desktop-cockpit`, `24` specs / `55` scénarios Desktop dont `52` exécutés et `3` `mobile-only` skipped) :
  - **Cas A (nominal visé) — `52/52` PASS Desktop (`0` échec, `0` timeout) ET `0` écart `P0`/`P1` dans l'audit Sally × Winston** : clôture directe de l'Epic 23 (`epic-23: done`, `23-8-...: done`), maintien de `CAP-042` sous `ACTION_ITEM-23.6`, **sans créer d'Epic 24 artificiel vide** ;
  - **Cas B (si échec Desktop ou écart `P0`/`P1` résiduel en `23.7`)** : analyse d'impact MCP GitNexus (`repo: "/home/romain/Documents/Projects/ORCIA"`), rédaction des rapports Tech Lead individuels (`24-1-...` à `24-K-...`), plan directeur global (`sprint-change-proposal-2026-11-19-epic-24-remediation-plan.md`), initialisation complète de l'**Epic 24** dans `epics.md`, `sprint-status.yaml` et `capabilities.yaml`, création de `tests/unit/test_epic23_to_epic24_traceability.py`, validation de la pyramide `AD-17` et clôture `epic-23: done`.
- **Commits associés** : `En attente d'implémentation (initialisé en Step 0 Epic 23, recadré Step 2a)`

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

> *[Pré-implémentation initialisée en Step 0 Epic 23, recadrée Step 2a — à compléter après exécution de la Story 23.8]*

### 3.1 Fichiers Développés & Modifiés
| Fichier | Nature (Création / Modification / Refactoring) | Description synthétique |
| :--- | :--- | :--- |
| `docs/implementation-artifacts/sprint-status.yaml`, `docs/product/capabilities.yaml` | Modification | *[À compléter : passage `epic-23: done`, `CAP-042` sous `ACTION_ITEM-23.6`]* |
| `docs/implementation-artifacts/tech-lead-reports/24-*.md` & `tests/unit/test_epic23_to_epic24_traceability.py` *(conditionnels)* | Création *(si échec Desktop ou écart P0/P1 > 0)* | *[Non créés si `52/52` PASS Desktop et `0` écart `P0`/`P1`]* |

### 3.2 Résultats Chiffrés, Métriques & Qualité
- **Critère de clôture (`52/52` PASS Desktop & `0` écart `P0`/`P1`)** : *[À compléter]*
- **Qualité statique & Pyramide `AD-17`** : *[À compléter]*

### 3.3 Validation & Procédure de Test sur Toute la Pyramide (`AD-17` + 5 Garde-Fous de Câblage Vertical)
- *[À compléter après clôture de `check_implementation_docs.py`, `pnpm site:sync && pnpm site:check`, `test_epic22_to_epic23_traceability.py` et passage de `epic-23: done`]*
