# Story 22.10 — Rapports Tech Lead Individuels pour Tests en Échec & Plan Sally × Winston, Plan de Correction Global & Initialisation Epic 23

> **Convention de nommage du fichier (Obligatoire — à créer AVANT toute modification de code)** :
> - User Story du sprint : `docs/implementation-artifacts/tech-lead-reports/{story-key}-tech-lead-report.md`

- **Date** : 2026-11-18
- **Story / Clé Sprint** : `22-10-rapports-tech-lead-plan-correction-global-et-initialisation-epic-23` (`Epic 22` — Clôture & Initialisation `Epic 23`)
- **Capacité(s)** : `none (gouvernance documentaire & planification Epic 23 — rattache toute capacité failed_e2e résiduelle et tout chantier d'amélioration Sally × Winston issu de e2e-campaign-epic-22)` — classification : `doc`
- **Auteur / Contexte** : `22.0-init` (Pré-implémentation Story 22.10) — Consolidation post-campagne Epic 22 (`bilan-execution-tests-e2e-epic-22.md`, `synthese-remediation-sally-winston-epic-22.md`), analyse d'impact MCP GitNexus (`repo: "ORCIA"`), rédaction des rapports Tech Lead individuels (`23-1-...` à `23-N-...`), plan de correction global (`sprint-change-proposal-2026-11-18-epic-23-remediation-plan.md`), initialisation complète de l'**Epic 23** dans `epics.md`, `sprint-status.yaml` et `capabilities.yaml`, et création du test de traçabilité `tests/unit/test_epic22_to_epic23_traceability.py` (`AD-17`, `NFR-TEST-1`, `GEMINI.md` § Policy).
- **Commits associés** : `En attente d'implémentation (initialisé en 22.0)`

---

## 1. Analyse du Besoin & Étude d'Impact Tech Lead (Pré-Implémentation)

### 1.1 Contexte & Problématique
- **Exploitation rigoureuse des constats de `Story 22.9`** :
  - Une fois la campagne intégrale Epic 22 exécutée (`docs/implementation-artifacts/e2e-campaign-epic-22/`) et l'audit croisé **Sally × Winston** achevé (`synthese-remediation-sally-winston-epic-22.md`), il convient de transformer de façon systématique et traçable **100 % des tests E2E en échec résiduel** et **100 % des points d'amélioration UX/Architecture Sally × Winston** en un plan d'action structuré pour l'**Epic 23**.
- **Obligations du Protocole Tech Lead (`GEMINI.md`)** :
  - Chaque lot cohérent de correction ou d'amélioration (`Story 23.1`..`Story 23.N`) doit disposer **avant tout codage** de son **Rapport Tech Lead pré-implémentation individuel** (`docs/implementation-artifacts/tech-lead-reports/23-k-...-tech-lead-report.md`) conforme à `TECH-LEAD-REPORT-TEMPLATE.md`, basé sur une étude d'impact GitNexus réelle (`repo: "ORCIA"`).
  - Un **Plan de Correction Global** (`docs/planning-artifacts/sprint-change-proposal-2026-11-18-epic-23-remediation-plan.md`) doit relier explicitement chaque test en échec, chaque item Sally × Winston et chaque capacité `failed_e2e` résiduelle à une Story `23.k` et son rapport Tech Lead.
  - Aucune capacité `failed_e2e` ne peut conserver un `e2e_remediation_ref` générique ou obsolète (`"epic-22"` / clé `22-*` clôturée) : toutes les références résiduelles pointent vers une clé exacte `23-k-...` présente dans `sprint-status.yaml` et dotée d'un rapport Tech Lead.

### 1.2 Exploration, Analyse d'Impact GitNexus, Factorisation & Dette Technique
- **Analyse d'Impact GitNexus (`repo: "ORCIA"`)** :
  - Sera exécutée après rafraîchissement de l'index (`gitnexus analyze --index-only`) à l'issue des modifications de code des Stories `22.1`..`22.8` afin d'évaluer l'impact exact (`gitnexus_query`, `gitnexus_context`, `gitnexus_impact`) sur chaque symbole concerné par les constats de `22.9`.
- **Découpage cohérent des lots `23-1`..`23-N`** :
  - Regroupement par domaine / couche technique / priorité (`P0` bloquants E2E résiduels, `P1`/`P2` améliorations UX Sally & architecture Winston, clôture E2E finale Epic 23).
  - Vérification de volumétrie des fichiers ciblés (`> 300–400` lignes) et opportunités de factorisation DRY consignées dans chaque rapport `23-k`.
- **Verrou automatique de traçabilité** :
  - Modèle éprouvé hérité de `tests/unit/test_epic21_to_epic22_traceability.py` : création de `tests/unit/test_epic22_to_epic23_traceability.py` garantissant zéro échec E2E, zéro point Sally × Winston et zéro capacité `failed_e2e` orphelin.

---

## 2. Plan d'Implémentation

### 2.1 Schéma de Données & Migrations Alembic (`infra/migrations/versions/`)
- Aucune migration Alembic appliquée en Story `22.10` (`doc` + test unitaire de traçabilité uniquement). Tout besoin éventuel de schéma issu de `22.9` est spécifié en Section 2.1 des rapports Tech Lead `23-1`..`23-N`.

### 2.2 Noyau Métier Hexagonal, Orchestration & Workers (`packages/orcia-core/`, `apps/worker/`)
- Aucune modification de code applicatif dans `Story 22.10`. Les lots backend/domaine/persistance identifiés en `22.9` sont spécifiés avec leurs contrats hexagonaux et invariants `AD-1`..`AD-24` dans les rapports `23-k-*`.

### 2.3 Couche Backend API, Sécurité & Contrats (`apps/api/`, `packages/api-client/`)
- Aucune modification d'endpoint dans `Story 22.10`. Les ajustements API/contenus/contrats OpenAPI nécessaires sont détaillés dans les rapports `23-k-*`.

### 2.4 Documentation Planification, Rapports Tech Lead & Initialisation Epic 23 (`docs/`)
1. **Rapports Tech Lead individuels (`23-1-...`..`23-N-...`)** :
   - Rédaction de `N` rapports conformes à `TECH-LEAD-REPORT-TEMPLATE.md` (Sections 1 & 2 complètes, Section 3 préparée avec les 3 titres obligatoires vérifiés par `scripts/check_implementation_docs.py`).
   - Enregistrement de tous les rapports `23-*` (et complétion Section 3 de `22.10`) dans `docs/implementation-artifacts/tech-lead-reports/README.md`.
2. **Plan de correction global (`docs/planning-artifacts/sprint-change-proposal-2026-11-18-epic-23-remediation-plan.md`)** :
   - Synthèse exécutive, graphe Mermaid d'ordonnancement topologique par vagues (`23.1` $\rightarrow$ `23.N`), matrices exhaustives de traçabilité (Échecs E2E Epic 22 $\rightarrow$ `23.k`, Items Sally × Winston $\rightarrow$ `23.k`, `CAP-*` `failed_e2e` $\rightarrow$ `23.k`).
3. **Initialisation `Epic 23` & Clôture `Epic 22`** :
   - `docs/planning-artifacts/epics.md` : ajout de `Epic 23` dans `FR Coverage Map`, `Epic List` et section détaillée `## Epic 23:` avec `### Story 23.1:`..`### Story 23.N:` (`Given/When/Then`).
   - `docs/implementation-artifacts/sprint-status.yaml` : ajout de `epic-23: backlog` + `23-1-...`..`23-N-...: ready-for-dev`, passage de `22-10-...: done` et `epic-22: done`.
   - `docs/product/capabilities.yaml` : mise à jour de tout éventuel `e2e_remediation_ref` résiduel vers les clés `23-k-...` exactes.

### 2.5 Analyse d'Impact sur la Pyramide des Tests (`AD-17`)
- **Couche 1a (`pytest`)** : création et exécution de `tests/unit/test_epic22_to_epic23_traceability.py` prouvant à `100 %` que chaque échec E2E de `e2e-campaign-epic-22/playwright-results.json`, chaque point d'amélioration de `synthese-remediation-sally-winston-epic-22.md` et chaque `CAP-*` en `failed_e2e` est relié à une Story `23.k` dans `epics.md`, `sprint-status.yaml` et son rapport Tech Lead indexé dans `README.md`.
- **Gouvernance documentaire & Vitrine** : `.venv/bin/python scripts/check_implementation_docs.py`, `pnpm site:sync && pnpm site:check`, `.venv/bin/ruff check/format`, `.venv/bin/lint-imports`, `.venv/bin/python .agent/skills/bmad-architecture/scripts/lint_spine.py`.

---

## 3. Bilan des Modifications & Résultats (Post-Implémentation)

> *[En attente d'implémentation de la Story 22.10]*

### 3.1 Fichiers Développés & Modifiés
| Fichier | Nature (Création / Modification / Refactoring) | Description synthétique |
| :--- | :--- | :--- |
| `docs/implementation-artifacts/tech-lead-reports/23-1-*.md` .. `23-N-*.md` | Création | *[À compléter après implémentation Story 22.10]* |
| `docs/planning-artifacts/sprint-change-proposal-2026-11-18-epic-23-remediation-plan.md` | Création | *[À compléter après implémentation Story 22.10]* |
| `docs/planning-artifacts/epics.md` | Modification | *[À compléter après ajout Epic 23]* |
| `docs/implementation-artifacts/sprint-status.yaml` | Modification | *[À compléter après initialisation Epic 23 & clôture Epic 22]* |
| `docs/product/capabilities.yaml` | Modification | *[À compléter si capacités failed_e2e résiduelles]* |
| `tests/unit/test_epic22_to_epic23_traceability.py` | Création | *[À compléter après implémentation Story 22.10]* |

### 3.2 Résultats Chiffrés, Métriques & Qualité
- **Traçabilité `Epic 22 -> Epic 23`** : *[À compléter : `pytest tests/unit/test_epic22_to_epic23_traceability.py`, `check_implementation_docs.py`, `pnpm site:sync && pnpm site:check`]*
- **Qualité statique & Architecture** : `ruff`, `lint-imports`, `lint_spine.py`, `gitnexus_detect_changes()` *[À compléter]*

### 3.3 Validation & Procédure de Test sur Toute la Pyramide (`AD-17`)
- *[À compléter après exécution complète de la Story 22.10 et clôture de l'Epic 22]*
