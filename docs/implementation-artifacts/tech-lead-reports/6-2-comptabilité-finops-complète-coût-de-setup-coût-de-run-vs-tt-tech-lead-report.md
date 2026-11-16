# Story 6.2 — Comptabilité FinOps Complète (Coût de Setup + Coût de Run vs TTM) & Coupe-Circuits Budgétaires / Anti-Boucles

> **Convention de nommage du fichier (Obligatoire — créé AVANT toute modification de code applicatif)** :
> - User Story du sprint : `docs/implementation-artifacts/tech-lead-reports/6-2-comptabilité-finops-complète-coût-de-setup-coût-de-run-vs-tt-tech-lead-report.md`

- **Date** : 2026-11-16
- **Story / Clé Sprint** : `6-2-comptabilité-finops-complète-coût-de-setup-coût-de-run-vs-tt` (`Epic 6`)
- **Capacité(s)** : `CAP-200` (Comptabilité FinOps consolidée & coupe-circuits de gouvernance) — classification : `feature` (voir `AGENTS.md` §5 et `capabilities.yaml`)
- **Auteur / Contexte** : Winston (`bmad-agent-architect` 🏗️) & Sally (`bmad-agent-ux-designer` 🎨). Calcul de l'équation économique complète (Setup amorti + Run consolidé tokens/humain vs TTM baseline), coupe-circuit budgétaire hiérarchique à 4 niveaux (`GLOBAL -> BU -> TEAM -> WORKSPACE`), compteur anti-boucles d'agents (`max_agent_retries`, défaut : 3) avec statuts `PAUSED_BUDGET_EXCEEDED` et `PAUSED_MAX_RETRIES`, protocole d'override explicite (`POST /runs/{id}/budget-override`), découpage de `cognitive_router.py` (< 350 lignes) et tableau de bord FinOps `@orcia/ui` monté sur `/finops` avec masquage des KPI lorsque `total == 0`. Couvre `FR-26`, `AD-10`, `AD-12`, `AD-17`, `AD-19`, `AD-21`, `SM-1`, `SM-5`, `UX-DR1` et `UX-DR3`.
- **Commits associés** : `pending-implementation`

---

## 1. Analyse du Besoin & Étude d'Impact Tech Lead (Pré-Implémentation)

### 1.1 Contexte & Problématique
Le pilotage de la rentabilité des processus assistés ou autonomes exige d'aller au-delà de la simple somme des factures d'API LLM :
1. **Équation économique incomplète** : Si le coût d'ingénierie initial (Setup du workflow) et la valeur du temps humain passé en relecture/arbitrage ne sont pas pris en compte, le ROI annoncé est artificiellement surévalué. L'objectif d'entreprise `SM-1` impose de mesurer une réduction réelle de $\ge 25\%$ du coût complet comparé à la baseline manuelle de référence.
2. **Risque de dérive financière incontrôlée** : Lors de corrections autonomes répétées ou d'escalades en cascade (`auto -> complex`), un Run peut consommer des sommes considérables en quelques minutes. L'organisation nécessite un coupe-circuit déterministe préventif (seuil d'alerte à $80\%$) et bloquant (plafond dur à $100\%$), suspendant automatiquement l'étape et le Run en `PAUSED_BUDGET_EXCEEDED`.
3. **Protection contre les boucles d'agents infinies** : Un agent qui échoue de manière répétée à franchir une Gate déterministe ou agentique doit être stoppé après `max_agent_retries` (défaut : 3), basculant en `PAUSED_MAX_RETRIES` avec notification au responsable.
4. **Protocole d'extension budgétaire audité** : La reprise d'un Run suspendu requiert une action humaine explicite d'un contributeur ou responsable (`POST /api/v1/runs/{run_id}/budget-override`), enregistrée de manière immuable dans `finops_budget_overrides`.
5. **Ergonomie Direction C & État Vide** : L'écran `/finops` actuel est une coquille vide avec un store volatile (`orcia.finops.overview.v1`). Il doit être remplacé par un véritable tableau de bord de gouvernance avec onglets, masquant les compteurs d'en-tête lorsque `total == 0`.

### 1.2 Exploration, Analyse d'Impact GitNexus, Factorisation & Dette Technique
- **Analyse d'Impact GitNexus (`gitnexus_query`, `gitnexus_context`, `gitnexus_impact`)** :
  - `CognitiveModelRouterService` (`packages/orcia-core/src/orcia_core/orchestration/cognitive_router.py`) : 511 lignes. Risque élevé de dépassement de complexité. Doit intégrer le coupe-circuit hiérarchique avant chaque invocation sans introduire de cycle avec `audit_finops`.
  - `workflow_runs.status` et `step_executions.status` : colonnes maîtresses impactant le moteur DBOS, l'ordonnanceur et l'API. L'élargissement doit préserver strictement les statuts existants (`RUNNING`, `COMPLETED`, `FAILED`, `PAUSED_WAITING_FOR_HUMAN`, etc.).
  - `enforce_scope_mutation_guard` : doit obligatoirement protéger `PUT /api/v1/finops/budgets`, `PUT /api/v1/finops/baselines` et `POST /api/v1/runs/{id}/budget-override` contre tout accès observateur (`HTTP 403 ERR_OBSERVER_MODE_READ_ONLY`).
- **Exploration & Volumétries Constatées** :
  - Toutes les données financières doivent impérativement être modélisées en `NUMERIC(12, 6)` et manipulées via `decimal.Decimal` en Python pour interdire tout écart d'arrondi flottant.
  - La table `workflow_runs` possède déjà une colonne `budget_max_usd NUMERIC(12, 6)` qui servira de plafond par défaut pour le Run.
- **Opportunités de Factorisation & Résorption de Dette Technique Naissante** :
  - **Découpage de `cognitive_router.py`** : extraction de `_cognitive_budget_guard.py` (~150 lignes), ramenant `cognitive_router.py` à $< 350$ lignes.
  - **Script de remise à zéro `09_reset_db_first_boot.py`** : ajout des 3 nouvelles tables mutables (`finops_budget_overrides`, `finops_workflow_baselines`, `finops_scope_budgets`) en tête du tuple `ORDERED_MUTABLE_TABLES_TO_CLEAR`.

---

## 2. Plan d'Implémentation

### 2.1 Schéma de Données & Migrations Alembic Linéaires
- Création de `infra/migrations/versions/20261116_0602_story_6_2_finops_budgets_baselines_and_pauses.py` (`down_revision = "20261116_0601"`) :
  - Élargissement des contraintes de statuts :
    - `workflow_runs.status` : ajout de `'PAUSED_MAX_RETRIES'`.
    - `step_executions.status` (`ck_step_executions_status`) : ajout de `'PAUSED_BUDGET_EXCEEDED'` et `'PAUSED_MAX_RETRIES'`.
  - Table `finops_scope_budgets` :
    - `id UUID PRIMARY KEY`, `scope_type VARCHAR(32) NOT NULL CHECK (scope_type IN ('GLOBAL', 'BU', 'TEAM', 'WORKSPACE'))`, `scope_id UUID NULL`, `monthly_budget_usd NUMERIC(12, 6) NOT NULL`, `warning_threshold_pct INTEGER NOT NULL DEFAULT 80`, `hard_stop_pct INTEGER NOT NULL DEFAULT 100`, `created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()`, `updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()`.
    - Contrainte `UNIQUE (scope_type, scope_id)`.
  - Table `finops_workflow_baselines` :
    - `id UUID PRIMARY KEY`, `workflow_definition_id UUID NOT NULL REFERENCES workflow_definitions(id) ON DELETE CASCADE`, `scope_id UUID NULL REFERENCES workspaces(id) ON DELETE CASCADE`, `manual_time_minutes INTEGER NOT NULL`, `manual_cost_usd NUMERIC(12, 6) NOT NULL`, `target_ttm_reduction_pct INTEGER NOT NULL DEFAULT 25`, `created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()`.
  - Table `finops_budget_overrides` :
    - `id UUID PRIMARY KEY`, `run_id UUID NOT NULL REFERENCES workflow_runs(id) ON DELETE CASCADE`, `requested_by UUID NOT NULL REFERENCES users(id)`, `approved_by UUID NOT NULL REFERENCES users(id)`, `override_amount_usd NUMERIC(12, 6) NOT NULL`, `reason TEXT NOT NULL`, `created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()`.
  - Mise à jour de `infra/scripts/maintenance/09_reset_db_first_boot.py` en ajoutant ces 3 tables à `ORDERED_MUTABLE_TABLES_TO_CLEAR`.

### 2.2 Noyau Métier Hexagonal, Orchestration & Workers
- **Enums & Modèles Kernel/Orchestration** :
  - Mise à jour de `packages/orcia-core/src/orcia_core/kernel/enums.py` et `orchestration/models.py` avec les statuts `PAUSED_BUDGET_EXCEEDED` et `PAUSED_MAX_RETRIES`.
- **Extraction & Implémentation du Garde Budgétaire** :
  - Création de `packages/orcia-core/src/orcia_core/orchestration/_cognitive_budget_guard.py` (< 300 lignes).
  - Vérification des plafonds hiérarchiques avant chaque appel LLM ou escalade d'effort (`fast`, `default`, `balanced`, `deep`).
  - Suspension immédiate dès franchissement du plafond dur et émission de `BudgetCircuitTripped` dans `domain_events_outbox`.
  - Arrêt automatique des agents après `max_agent_retries` (défaut : 3) avec bascule en `PAUSED_MAX_RETRIES`.
- **Service Comptable FinOps (`packages/orcia-core/src/orcia_core/audit_finops/`)** :
  - `finops_accounting_service.py` : calcul monétaire intégral en `Decimal` (`NUMERIC(12, 6)`) selon l'équation à 3 composantes (Setup amorti + Run consolidé + Temps humain valorisé) et différentiel TTM vs baseline déclarée.
  - `budget_guard_service.py` : implémente `BudgetCircuitGuardPort` (défini dans `orcia_core/ports/finops_telemetry.py`).
  - `_internal/sql_finops_accounting.py` : requêtes SQL asynchrones pour ventiler les coûts par Step, Tier, Effort, Run, Workflow et Équipe/BU.

### 2.3 Couche Backend API, Sécurité & Contrats
- **Schémas RFC 9457 (`apps/api/src/orcia_api/schemas/finops.py`)** :
  - `FinopsOverviewResponse`, `FinopsBreakdownResponse`, `UpdateScopeBudgetRequest`, `SetWorkflowBaselineRequest`, `BudgetOverrideRequest`, `BudgetOverrideResponse`.
- **Routeur FastAPI (`apps/api/src/orcia_api/routers/finops.py`)** :
  - `GET /api/v1/finops/dashboard` (vue consolidée et ventilations).
  - `PUT /api/v1/finops/budgets` (configuration des plafonds budgétaires, protégé par `enforce_scope_mutation_guard`).
  - `PUT /api/v1/finops/baselines` (enregistrement des baselines manuelles, protégé par `enforce_scope_mutation_guard`).
  - `POST /api/v1/runs/{run_id}/budget-override` (autorisation d'extension budgétaire et reprise, protégé par `enforce_scope_mutation_guard`).
- **Composition Root & SDK Client** :
  - Câblage dans `apps/api/src/orcia_api/dependencies/orchestration_and_settings.py`.
  - Régénération du client TypeScript via `scripts/export_openapi.py` (`0-diff`).

### 2.4 Interface Utilisateur & Expérience (`apps/web/` & `@orcia/ui`)
- **Composants `@orcia/ui` (`packages/ui/src/primitives/finops/`)** :
  - `FinopsGovernanceDashboardView.tsx` : coquille d'accueil avec `OrciaTabBar`.
  - `FinopsKpiStrip.tsx` : affichage des 4 compteurs KPI (Coût consolidé, Tokens LLM, Appels externes, Économie TTM) ou masquage strict si `total == 0`.
  - `FinopsProcessAndTiersTab.tsx` : tableau ventilé par processus, Step, Tier cognitif et effort.
  - `FinopsBudgetPolicyModal.tsx` : dialogue accessible (`OrciaDialog`) pour régler les plafonds et seuils d'alerte.
- **Montage dans `apps/web/src/features/finops/index.tsx`** :
  - Remplacement complet du store volatile par l'appel `@orcia/api-client` (`GET /api/v1/finops/dashboard`).
  - Intégration de l'aide contextuelle `ContextualInfoTriggerButton` pointant sur `finops-overview`.
  - Enregistrement des props dans `zero-dead-buttons-and-silent-catches-audit.test.tsx`.

### 2.5 Analyse d'Impact sur la Pyramide des Tests (`AD-17`)
- **Couche 1a (Unitaires Python)** :
  - `test_story_6_2_finops_accounting_decimal.py` : tests déterministes et `hypothesis` vérifiant l'absence d'erreurs d'arrondi sur calculs `Decimal`.
  - `test_story_6_2_budget_circuit_guards.py` : validation des suspensions `PAUSED_BUDGET_EXCEEDED` et `PAUSED_MAX_RETRIES`.
- **Couche 1b (Composants TS `Vitest`)** :
  - Rendu du tableau de bord FinOps, ouverture de la modale de budget et survie au rechargement de page (`F5`).
- **Couche 2 (Intégration `testcontainers` PostgreSQL 18 + Redis)** :
  - `test_story_6_2_finops_postgres18.py` : simulation d'un dépassement budgétaire, vérification de la suspension en base, reprise via `POST /budget-override` et passage en `RUNNING`.
- **Couche 4 (Evals Déterministes `0 $`)** :
  - `tests/evals/test_story_6_2_cognitive_escalation_finops.py` : évaluation déterministe avec cassette LLM validant l'attribution des coûts d'escalade cognitive.

---

## 3. Bilan des Modifications & Résultats (Post-Implémentation)

> *Section réservée à l'implémentation par le dev worker (`bmad-dev-worker` ⚡).*

### 3.1 Fichiers Développés & Modifiés
| Fichier | Nature (Création / Modification / Refactoring) | Description synthétique |
| :--- | :--- | :--- |
| `infra/migrations/versions/20261116_0602_story_6_2_finops_budgets_baselines_and_pauses.py` | Création | Migration Alembic élargissant les statuts de run et créant les tables FinOps |
| `infra/scripts/maintenance/09_reset_db_first_boot.py` | Modification | Ajout des 3 tables mutables dans `ORDERED_MUTABLE_TABLES_TO_CLEAR` |
| `packages/orcia-core/src/orcia_core/kernel/enums.py` | Modification | Ajout des statuts `PAUSED_BUDGET_EXCEEDED` et `PAUSED_MAX_RETRIES` |
| `packages/orcia-core/src/orcia_core/orchestration/models.py` | Modification | Alignement des statuts de run |
| `packages/orcia-core/src/orcia_core/orchestration/cognitive_router.py` | Refactoring | Découpage et allègement sous 350 lignes |
| `packages/orcia-core/src/orcia_core/orchestration/_cognitive_budget_guard.py` | Création | Extraction du garde budgétaire et anti-boucles |
| `packages/orcia-core/src/orcia_core/audit_finops/finops_accounting_service.py` | Création | Moteur de calcul de l'équation économique en `Decimal` |
| `packages/orcia-core/src/orcia_core/audit_finops/budget_guard_service.py` | Création | Implémentation de `BudgetCircuitGuardPort` |
| `packages/orcia-core/src/orcia_core/audit_finops/_internal/sql_finops_accounting.py` | Création | Requêtes SQL d'agrégation budgétaire |
| `packages/ui/src/primitives/finops/FinopsGovernanceDashboardView.tsx` | Création | Vue principale avec onglets |
| `packages/ui/src/primitives/finops/FinopsKpiStrip.tsx` | Création | Barre des KPI consolidés ou état vide |
| `packages/ui/src/primitives/finops/FinopsProcessAndTiersTab.tsx` | Création | Tableau ventilé processus/tiers |
| `packages/ui/src/primitives/finops/FinopsBudgetPolicyModal.tsx` | Création | Modale de gestion des plafonds budgétaires |
| `apps/api/src/orcia_api/schemas/finops.py` | Création | Schémas RFC 9457 pour FinOps et overrides |
| `apps/api/src/orcia_api/routers/finops.py` | Création | Routeur FastAPI `/api/v1/finops/*` |
| `apps/web/src/features/finops/index.tsx` | Refactoring | Montage du tableau de bord complet avec survie au F5 |
| `tests/unit/test_story_6_2_finops_accounting_decimal.py` | Création | Tests unitaires `hypothesis` sur calculs `Decimal` |
| `tests/unit/test_story_6_2_budget_circuit_guards.py` | Création | Tests unitaires des coupe-circuits et suspensions |
| `tests/integration/test_story_6_2_finops_postgres18.py` | Création | Tests d'intégration testcontainers PG18 + Redis |
| `tests/evals/test_story_6_2_cognitive_escalation_finops.py` | Création | Évaluation déterministe à 0 $ |

### 3.2 Résultats Chiffrés, Métriques & Qualité
- **Couverture de tests** : Requis $\ge 90\%$.
- **Performances mesurées** : Évaluation du coupe-circuit $< 5$ ms, Calcul consolidé du tableau de bord $< 20$ ms.
- **Qualité statique & Architecture** :
  - `ruff check` & `ruff format --check` : `0 warning`
  - `mypy --strict` & `pnpm typecheck` : `0 error`
  - `lint-imports` : `5 contracts kept, 0 broken`
  - `lint_spine.py` : `ok: true, 0 findings`
  - `gitnexus_detect_changes()` : Périmètre conforme.

### 3.3 Validation & Procédure de Test sur Toute la Pyramide (`AD-17`)
- **Couche 1a & 1b** : Précision arithmétique `Decimal` et comportement du composant d'état vide.
- **Couche 2** : Suspension réelle du workflow et déblocage par appel API d'extension budgétaire.
- **Couche 3** : Conformité du schéma OpenAPI `0-diff`.
- **Couche 4** : Évaluation déterministe à 0 $ validant le respect du budget sur scénario d'escalade.
- **Couche 5** : Vérification Playwright du tableau de bord et de la modale de budget.
