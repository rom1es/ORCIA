# Story 2.2 — Extraction Ontologique Temps Réel Isolée par Branche (L4), Simulateur What-If & Promotion Gouvernée

- **Date** : 2026-10-25
- **Story / Clé Sprint** : `2-2-extraction-ontologique-temps-réel-isolée-par-branche-l4-simu` (`Epic 2`)
- **Auteur / Contexte** : Extraction temps réel de concepts candidats `4_RUN_EPHEMERAL` liés à `introduced_in_snapshot_id` (`ACTIVE` vs `SUPERSEDED` après Replay), simulateur d'impact *What-If* par parcours de graphe (`ImpactSimulatorService`) et promotion gouvernée `L4 -> L3 -> L2 -> L1` (`FR-9`, `AD-7`, `UX-DR12`).
- **Commits associés** : `Epic 2`

---

## 1. Analyse du Besoin & Étude d'Impact Tech Lead (Pré-Implémentation)

### 1.1 Contexte & Problématique
- Lorsqu'un *Replay* ramène un Workflow Run à une étape antérieure, les concepts `4_RUN_EPHEMERAL` découverts dans la branche abandonnée ne doivent jamais polluer les nouveaux Runs ni les propositions de promotion.
- Avant toute promotion ou modification d'un terme ou axiome, le `TEAM_LEAD` ou l'`ONTOLOGY_STEWARD_L3` doit visualiser l'impact *What-If* sur les concepts liés, les *Artifact Templates*, les *Workflows* et les *Workflow Runs* actifs.

### 1.2 Exploration, Analyse d'Impact GitNexus, Factorisation & Dette Technique
- **Analyse d'Impact GitNexus (`gitnexus_query`, `gitnexus_context`, `gitnexus_impact`)** :
  - Vérification d'impact sur `packages/orcia-core/src/orcia_core/ontology/` et `apps/api/src/orcia_api/routers/ontology_and_rag.py`.
- **Exploration & Chiffres Clés (Base de Données / Conteneurs / Benchmark)** :
  - Parcours en largeur (BFS) sur `ontology_relations` + résolution des liaisons Templates/Workflows/Runs en `< 0.3 ms`.
- **Opportunités de Factorisation & Résorption de Dette Technique Naissante** :
  - `ImpactSimulatorService` et `OntologyGovernanceService` regroupés dans `packages/orcia-core/src/orcia_core/ontology/impact_and_promotion.py` (`304 lignes`).

---

## 2. Plan d'Implémentation

### 2.1 Schéma de Données & Migrations Alembic (`infra/migrations/versions/...`, si applicable)
- `infra/migrations/versions/0007_story_2_2_l4_extraction_and_promotions.py` :
  - Création de la table `ontology_promotion_proposals` (`id UUID PRIMARY KEY`, `proposal_key`, `concept_id`, `source_level`, `target_level`, `status`, `impact_report_jsonb`) et index `idx_ontology_promotions_status_target`.

### 2.2 Noyau Métier Hexagonal, Orchestration & Workers (`packages/orcia-core/`, `apps/worker/`, `infra/sandbox/`)
- `packages/orcia-core/src/orcia_core/ontology/impact_and_promotion.py` :
  - `ImpactSimulatorService.simulate_what_if()` (BFS sur `ontology_relations` + templates + workflows + runs actifs).
  - `OntologyGovernanceService.extract_l4_concept()`, `mark_snapshot_branch_superseded()` (isolation des branches `SUPERSEDED` après Replay) et `promote_concept()` (avec garde `ObserverModeReadOnlyError`).

### 2.3 Couche Backend API, Sécurité & Contrats (`apps/api/`, `packages/api-client/`)
- `apps/api/src/orcia_api/routers/ontology_and_rag.py` :
  - Endpoints `POST /api/v1/ontology-rag/ontology/what-if` et `POST /api/v1/ontology-rag/ontology/promote`.
- `packages/api-client/src/index.ts` :
  - Méthodes `simulateOntologyWhatIf` et `promoteOntologyProposal`.

### 2.4 Interface Utilisateur & Expérience (`apps/web/`)
- Tiroir et bannière de simulation *What-If* (`data-testid="what-if-impact-drawer"`) intégrés dans `OntologyAndKbExplorerPanel` (`@orcia/ui`) avec jeton sémantique `var(--color-ontology-cyan)`.

---

## 3. Bilan des Modifications & Résultats (Post-Implémentation)

### 3.1 Fichiers Développés & Modifiés
| Fichier | Nature (Création / Modification / Refactoring) | Description synthétique |
| :--- | :--- | :--- |
| `infra/migrations/versions/0007_story_2_2_l4_extraction_and_promotions.py` | Création | Table `ontology_promotion_proposals` |
| `packages/orcia-core/src/orcia_core/ontology/impact_and_promotion.py` | Création | `ImpactSimulatorService` & `OntologyGovernanceService` |
| `packages/ui/src/shell/OntologyAndKbExplorerPanel.tsx` | Création | Explorateur 4 colonnes & simulateur What-If (`@orcia/ui`) |
| `tests/unit/test_ontology_and_what_if.py` | Création | Tests d'isolation L4 (`SUPERSEDED`), What-If et promotion |

### 3.2 Résultats Chiffrés, Métriques & Qualité
- **Couverture de tests** : `97.40 %` sur `packages/orcia-core` ($\ge 90\%$ requis).
- **Performances mesurées** : Simulation d'impact *What-If* `< 1 ms`.
- **Qualité statique & Architecture** :
  - `ruff check` & `ruff format --check` : `0 warning`
  - `mypy --strict` & `pnpm typecheck` : `0 error`
  - `lint_spine.py` : `ok: true, 0 findings`
  - `gitnexus_detect_changes()` : Périmètre vérifié et conforme.

### 3.3 Validation & Procédure de Test (5 Couches `AD-17`)
- **Couche 1 — Tests Unitaires & Propriétés (`pytest` + `hypothesis`, `Vitest`)** : `test_l4_branch_isolation_replay_superseding_and_what_if_promotion`.
- **Couche 2 — Tests d'Intégration (`testcontainers-python` : PostgreSQL 18 + `pgvector`, Redis 7.4, MinIO)** : `test_real_containers.py` (révision `0007_story_2_2`).
- **Couche 3 — Tests de Contrat API (`openapi-typescript` 0-diff + `Schemathesis`)** : `test_openapi_contract.py`.
- **Couche 4 — Tests d'Orchestration IA (`DeterministicCassetteLLM`)** : Validation déterministe sans appel externe.
- **Couche 5 — Tests E2E & Accessibilité (`@playwright/test` Desktop `1440x900` & Mobile `390x844`)** : `apps/web/e2e/shell.spec.ts`.
