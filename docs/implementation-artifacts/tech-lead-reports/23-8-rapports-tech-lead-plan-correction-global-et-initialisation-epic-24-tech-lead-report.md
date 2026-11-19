# Story 23.8 — Rapports Tech Lead Individuels, Plan de Correction Global & Initialisation Epic 24

> **Convention de nommage du fichier (Obligatoire — à créer AVANT toute modification de code)** :
> - User Story du sprint : `docs/implementation-artifacts/tech-lead-reports/{story-key}-tech-lead-report.md`

- **Date** : 2026-11-19
- **Story / Clé Sprint** : `23-8-rapports-tech-lead-plan-correction-global-et-initialisation-epic-24` (`Epic 23` — Clôture & Initialisation `Epic 24`)
- **Capacité(s)** : `none (gouvernance documentaire & planification Epic 24 — rattache toute capacité failed_e2e résiduelle et tout chantier Sally × Winston issus de e2e-campaign-epic-23)` — classification : `doc`
- **Auteur / Contexte** : `23.0-impl` (initialisation Step 0 Epic 23 sur le modèle `Story 22.10`) — Consolidation post-campagne Epic 23 (`bilan-execution-tests-e2e-epic-23.md`, `synthese-remediation-sally-winston-epic-23.md`), analyse d'impact MCP GitNexus (`repo: "/home/romain/Documents/Projects/ORCIA"`), rédaction des rapports Tech Lead individuels (`24-1-...` à `24-K-...`), rédaction du plan directeur global (`sprint-change-proposal-2026-11-19-epic-24-remediation-plan.md`), initialisation complète de l'**Epic 24** dans `epics.md`, `sprint-status.yaml` et `capabilities.yaml`, création de `tests/unit/test_epic23_to_epic24_traceability.py`, validation de la pyramide `AD-17` et clôture `epic-23: done`.
- **Commits associés** : `En attente d'implémentation (initialisé en Step 0 Epic 23)`

---

## 1. Analyse du Besoin & Étude d'Impact Tech Lead (Pré-Implémentation)

### 1.1 Contexte & Problématique
- **Exploitation rigoureuse et systématique des constats de `Story 23.7`** :
  - Une fois la campagne intégrale figée `e2e-campaign-epic-23/` et l'audit croisé **Sally × Winston** achevés (`Story 23.7`), tout reliquat d'échec E2E éventuel et tout point d'amélioration UX/Architecture consigné dans `synthese-remediation-sally-winston-epic-23.md` doivent être convertis en lots actionnables et ordonnancés pour l'**Epic 24**.
- **Obligations du Protocole Tech Lead (`GEMINI.md`)** :
  - Chaque lot cohérent (`Story 24.1`..`Story 24.K`) dispose **avant tout codage** de son **Rapport Tech Lead pré-implémentation individuel** (`docs/implementation-artifacts/tech-lead-reports/24-k-...-tech-lead-report.md`) conforme à `TECH-LEAD-REPORT-TEMPLATE.md`, basé sur une analyse d'impact GitNexus réelle (`repo: "/home/romain/Documents/Projects/ORCIA"`).
  - Le **Plan de Correction Global** (`docs/planning-artifacts/sprint-change-proposal-2026-11-19-epic-24-remediation-plan.md`) relie explicitement chaque éventuel test en échec, chaque item Sally × Winston (`REM24-*` / `P*-UX-*` / `ARCH24-*`) et chaque éventuelle capacité `failed_e2e` résiduelle à une Story `24.k` et son rapport Tech Lead.
  - Aucune capacité en `failed_e2e` ne peut conserver une référence obsolète `23-*` une fois l'Epic 23 clôturé : toute capacité non promue `runtime` en `23.7` pointe vers une clé exacte `24-k-...` présente dans `sprint-status.yaml` et dotée d'un rapport Tech Lead.

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

### 2.4 Documentation Planification, Rapports Tech Lead & Initialisation Epic 24 (`docs/`)
1. **Rapports Tech Lead individuels (`24-1-...`..`24-K-...`)** :
   - Rédaction de `K` rapports conformes à `TECH-LEAD-REPORT-TEMPLATE.md` (Sections 1 & 2 complètes, Section 3 préparée avec les 3 titres obligatoires vérifiés par `scripts/check_implementation_docs.py`).
   - Indexation de tous les rapports `24-*` (et complétion Section 3 de `23-8`) dans `docs/implementation-artifacts/tech-lead-reports/README.md`.
2. **Plan de correction global (`docs/planning-artifacts/sprint-change-proposal-2026-11-19-epic-24-remediation-plan.md`)** :
   - Synthèse exécutive, ordonnancement topologique par vagues (`24.1` $\rightarrow$ `24.K`) et matrices exhaustives reliant chaque constat de `e2e-campaign-epic-23/` à une Story `24.k` et son rapport Tech Lead.
3. **Initialisation `Epic 24` & Clôture `Epic 23`** :
   - `docs/planning-artifacts/epics.md` : ajout de `Epic 24` dans `FR Coverage Map`, `Epic List` et section détaillée `## Epic 24:` avec `### Story 24.1:`..`### Story 24.K:` (`Given/When/Then`).
   - `docs/implementation-artifacts/sprint-status.yaml` : ajout de `epic-24: backlog` + `24-1-...`..`24-K-...: ready-for-dev`, passage de `23-8-...: done` et `epic-23: done`.
   - `docs/product/capabilities.yaml` : mise à jour de toute éventuelle `e2e_remediation_ref` vers une clé `24-k-...` exacte.

### 2.5 Analyse d'Impact sur la Pyramide des Tests (`AD-17` — Couches 1 à 5 + Sécurité, Obligatoire)
- **Couche 1a (`pytest`)** : création et exécution de `tests/unit/test_epic23_to_epic24_traceability.py` + adaptation finale de `tests/unit/test_epic22_to_epic23_traceability.py` (`23-7: done` + `23-8: done`).
- **Gouvernance documentaire & Vitrine** : `.venv/bin/python scripts/check_implementation_docs.py`, `pnpm site:sync && pnpm site:check`, `.venv/bin/ruff check/format`, `.venv/bin/lint-imports`, `.venv/bin/python .agent/skills/bmad-architecture/scripts/lint_spine.py`.

---

## 3. Bilan des Modifications & Résultats (Post-Implémentation)

> *[Pré-implémentation initialisée en Step 0 Epic 23 — à compléter après exécution de la Story 23.8]*

### 3.1 Fichiers Développés & Modifiés
| Fichier | Nature (Création / Modification / Refactoring) | Description synthétique |
| :--- | :--- | :--- |
| `docs/implementation-artifacts/tech-lead-reports/24-1-*.md`..`24-K-*.md` | Création | *[À compléter après exécution Story 23.8]* |
| `docs/planning-artifacts/sprint-change-proposal-2026-11-19-epic-24-remediation-plan.md`, `epics.md`, `sprint-status.yaml`, `tests/unit/test_epic23_to_epic24_traceability.py` | Création / Modification | *[À compléter après exécution Story 23.8]* |

### 3.2 Résultats Chiffrés, Métriques & Qualité
- **Traçabilité `Epic 23 -> Epic 24` (`100 %`)** : *[À compléter]*
- **Qualité statique & Pyramide `AD-17`** : *[À compléter]*

### 3.3 Validation & Procédure de Test sur Toute la Pyramide (`AD-17` + 5 Garde-Fous de Câblage Vertical)
- *[À compléter après clôture de `tests/unit/test_epic23_to_epic24_traceability.py`, `check_implementation_docs.py`, `pnpm site:sync && pnpm site:check` et passage de `epic-23: done`]*
