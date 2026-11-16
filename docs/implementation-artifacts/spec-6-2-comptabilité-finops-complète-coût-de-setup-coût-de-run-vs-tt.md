---
story_key: "6-2-comptabilité-finops-complète-coût-de-setup-coût-de-run-vs-tt"
status: "ready-for-dev"
epic: "epic-6"
title: "Story 6.2 : Comptabilité FinOps Complète (Coût de Setup + Coût de Run vs TTM) & Coupe-Circuits Budgétaires / Anti-Boucles"
date: "2026-11-16"
authors:
  - "Winston (bmad-agent-architect 🏗️)"
  - "Sally (bmad-agent-ux-designer 🎨)"
capabilities:
  - "CAP-200"
---

# Spécification d'Implémentation — Story 6.2 : Comptabilité FinOps Complète (Coût de Setup + Coût de Run vs TTM) & Coupe-Circuits Budgétaires / Anti-Boucles

- **Story Key** : `6-2-comptabilité-finops-complète-coût-de-setup-coût-de-run-vs-tt`
- **Epic** : Epic 6 — Gouvernance Exécutive, Provenance Auditable Immuable, FinOps Consolidé & Réversibilité Humaine
- **Capacité rattachée** : `CAP-200` (Tableau de bord FinOps consolidé & coupe-circuits de gouvernance)
- **Références architecturales** : `FR-26`, `AD-10`, `AD-12`, `AD-17`, `AD-19`, `AD-21`, `SM-1`, `SM-5`, `UX-DR1`, `UX-DR3`

---

## 1. Intent & Boundaries

### 1.1 Problem & Approach
Les processus d'orchestration multi-agents consomment des ressources hétérogènes dont le coût réel reste opaque s'il ne prend pas en compte le temps d'ingénierie initial (Setup), la consommation de tokens et le temps d'expertise humaine investi lors des revues et arbitrages. Sans garde-fous automatisés, des boucles d'agents ou des tentatives répétées de résolution peuvent causer des dérives financières majeures.
Cette story implémente :
1. L'équation économique complète en arithmétique `Decimal` (`NUMERIC(12, 6)`) combinant l'amortissement du Setup, les coûts d'exécution consolidés (tokens internes + temps humain valorisé) et le gain de Time-to-Market (TTM) par rapport à une baseline déclarée (`finops_workflow_baselines`).
2. Un coupe-circuit budgétaire hiérarchique à 4 niveaux (`GLOBAL -> BU -> TEAM -> WORKSPACE`) et un compteur anti-boucles d'agents (`max_agent_retries`, défaut : 3) suspendant automatiquement les étapes en statut `PAUSED_BUDGET_EXCEEDED` ou `PAUSED_MAX_RETRIES`.
3. Un protocole de reprise explicite (`POST /api/v1/runs/{run_id}/budget-override`) persistant l'extension dans `finops_budget_overrides` et émettant `BudgetOverrideApproved`.
4. Le tableau de bord de gouvernance FinOps dans `@orcia/ui` monté sur `/finops` avec onglets, modale de gestion des plafonds et état vide masquant les KPI chiffrés lorsque `total == 0`.

### 1.2 Boundaries & Constraints
- **Toujours (`Always`)** :
  - Effectuer tous les calculs monétaires et agrégations en `Decimal` (Python) et `NUMERIC(12, 6)` (SQL) pour éliminer toute erreur d'arrondi flottant.
  - Protéger 100 % des mutations de budgets et d'overrides via `enforce_scope_mutation_guard` (`HTTP 403 ERR_OBSERVER_MODE_READ_ONLY` en mode observateur).
  - Suspendre immédiatement le Run et l'étape dès franchissement du plafond dur ($100\%$) ou du seuil `max_agent_retries`, et notifier le responsable par événement Outbox `BudgetCircuitTripped` et SSE (`SseBroadcastPort`).
  - Ajouter les tables mutables créées (`finops_scope_budgets`, `finops_workflow_baselines`, `finops_budget_overrides`) dans `ORDERED_MUTABLE_TABLES_TO_CLEAR` de `09_reset_db_first_boot.py`.
  - Isoler le contrôle budgétaire de `cognitive_router.py` en extrayant `_cognitive_budget_guard.py` (< 300 lignes).
  - Respecter les Design Tokens Direction C (zéro hexadécimal hors `tokens.css`, `OrciaTabBar`, `OrciaDialog`).
- **Jamais (`Never`)** :
  - Ne jamais exécuter de calculs financiers avec des types `float` IEEE-754 en base ou dans les services de calcul du domaine.
  - Ne jamais permettre la reprise d'un Run suspendu sans validation formelle d'un responsable (`override_amount_usd > 0` et motif renseigné).
  - Ne jamais importer `orcia_core.audit_finops` directement depuis `orcia_core.orchestration` ou `orcia_core.permissions` sans passer par les ports hexagonaux `finops_telemetry.py`.
  - Ne jamais afficher de KPI chiffrés non pertinents à l'utilisateur lorsque `total == 0` (afficher l'état vide explicite selon le standard Direction C).

### 1.3 I/O & Edge-Case Matrix

| Contexte / Déclencheur | Entrée | Résultat Attendu | Code Retour / Effet |
| :--- | :--- | :--- | :--- |
| Exécution sous plafond | Dépense $< 80\%$ du budget | Poursuite normale du workflow | Step en cours d'exécution |
| Seuil d'alerte atteint | Dépense $\ge 80\%$ et $< 100\%$ | Émission d'alerte Outbox préventive | Notification émise, Run non suspendu |
| Dépassement budgétaire | Dépense $\ge 100\%$ du budget | Suspension immédiate du Run et du Step | Statut `PAUSED_BUDGET_EXCEEDED`, notification SSE |
| Boucle infinie d'agents | Échecs répétés $> max\_retries$ (3) | Suspension immédiate du Step et du Run | Statut `PAUSED_MAX_RETRIES`, notification SSE |
| Demande d'override valide | `POST /budget-override` (+50 $, motif) | Extension accordée, statut réveillé en `RUNNING` | `200 OK`, `BudgetOverrideApproved` émis |
| Demande d'override observateur | Tentative par `READ_ONLY_OBSERVER` | Rejet formel avec enveloppe RFC 9457 | `403 Forbidden` (`ERR_OBSERVER_MODE_READ_ONLY`) |
| Absence d'exécutions | Consultation de `/finops` à blanc | Masquage des KPI d'en-tête, panneau d'état vide | `total == 0` état vide affiché |

---

## 2. Acceptance Criteria (Given / When / Then)

### Critère 1 : Élargissement des Statuts & Schéma Relationnel Alembic
- **Given** la migration Alembic `20261116_0602_story_6_2_finops_budgets_baselines_and_pauses.py` (down_revision = `"20261116_0601"`),
- **When** la migration est appliquée,
- **Then** la colonne `workflow_runs.status` accepte la valeur `'PAUSED_MAX_RETRIES'`,
- **And** la contrainte `ck_step_executions_status` accepte `'PAUSED_BUDGET_EXCEEDED'` et `'PAUSED_MAX_RETRIES'`,
- **And** les tables `finops_scope_budgets`, `finops_workflow_baselines` et `finops_budget_overrides` sont créées avec clés primaires `UUIDv7` et montants `NUMERIC(12, 6)`.

### Critère 2 : Coupe-Circuit Budgétaire Hiérarchique & Alerte Préventive
- **Given** un Espace ou un Workflow Run doté d'un plafond budgétaire configuré,
- **When** un appel de modèle IA ou un coût d'étape fait franchir le seuil d'avertissement ($80\%$),
- **Then** un événement `BudgetCircuitTripped` d'avertissement est émis dans l'Outbox et diffusé par SSE,
- **When** le coût fait franchir le plafond dur ($100\%$),
- **Then** le coupe-circuit bloque l'appel LLM, passe l'étape en `PAUSED_BUDGET_EXCEEDED`, bascule le Run en `PAUSED_BUDGET_EXCEEDED` et diffuse une alerte rouge requérant un déblocage humain.

### Critère 3 : Détection Anti-Boucles d'Agents (`max_agent_retries`)
- **Given** un Step soumis à des réévaluations d'agents ou rejets de Gates successifs,
- **When** le nombre de tentatives atteint le plafond `max_agent_retries` (par défaut : 3),
- **Then** le système interrompt immédiatement la boucle de correction autonome,
- **And** l'étape et le Run passent en `PAUSED_MAX_RETRIES` avec notification au responsable.

### Critère 4 : Protocole de Reprise & Extension Budgétaire (`Budget Override`)
- **Given** un Run suspendu en `PAUSED_BUDGET_EXCEEDED`,
- **When** un responsable autorisé appelle `POST /api/v1/runs/{run_id}/budget-override` avec un montant `override_amount_usd` et une justification textuelle,
- **Then** une entrée immuable est enregistrée dans `finops_budget_overrides`,
- **And** le plafond du Run est étendu du montant spécifié, le Run repasse en `RUNNING` et le workflow DBOS reprend son exécution de manière déterministe.

### Critère 5 : Tableau de Bord FinOps & Respect Direction C
- **Given** l'écran `/finops` (`apps/web/src/features/finops/`),
- **When** des exécutions sont présentes,
- **Then** il affiche la ventilation par Step, Tier cognitif, niveau d'effort, Run, Workflow et Équipe/BU (coûts Setup amortis, coûts Run en `numeric(12, 6)` USD convertis en `€`, temps humain valorisé et différentiel TTM),
- **When** aucune exécution n'existe (`total == 0`),
- **Then** les compteurs KPI sont masqués au profit d'un état d'accueil explicite conforme à Direction C,
- **And** tous les boutons de configuration de budget ouvrent `FinopsBudgetPolicyModal` et sont enregistrés dans `zero-dead-buttons-and-silent-catches-audit.test.tsx`.

---

## 3. Code Map

```
ORCIA/
├── infra/
│   ├── migrations/versions/
│   │   └── 20261116_0602_story_6_2_finops_budgets_baselines_and_pauses.py [CRÉATION - Migration Alembic]
│   └── scripts/maintenance/
│       └── 09_reset_db_first_boot.py                                      [MODIFICATION - Ajout 3 tables mutables]
├── packages/
│   ├── orcia-core/src/orcia_core/
│   │   ├── kernel/
│   │   │   └── enums.py                                                   [MODIFICATION - Statuts PAUSED_*]
│   │   ├── orchestration/
│   │   │   ├── models.py                                                  [MODIFICATION - Alignement statuts de run]
│   │   │   ├── cognitive_router.py                                        [REFACTORING - Allégement < 350 lignes]
│   │   │   └── _cognitive_budget_guard.py                                 [CRÉATION - Extraction du garde budgétaire]
│   │   └── audit_finops/
│   │       ├── finops_accounting_service.py                               [CRÉATION - Service d'équation FinOps Decimal]
│   │       ├── budget_guard_service.py                                    [CRÉATION - Implémentation BudgetCircuitGuardPort]
│   │       └── _internal/
│   │           └── sql_finops_accounting.py                               [CRÉATION - Requêtes SQL de calcul FinOps]
│   └── ui/src/
│       ├── index.ts                                                       [MODIFICATION - Exports composants FinOps]
│       └── primitives/finops/
│           ├── FinopsGovernanceDashboardView.tsx                          [CRÉATION - Vue principale avec onglets]
│           ├── FinopsKpiStrip.tsx                                         [CRÉATION - Barre des 4 KPIs ou état vide]
│           ├── FinopsProcessAndTiersTab.tsx                               [CRÉATION - Tableau ventilé processus/tiers]
│           └── FinopsBudgetPolicyModal.tsx                                [CRÉATION - Modale d'édition des budgets]
├── apps/
│   ├── api/src/orcia_api/
│   │   ├── dependencies/
│   │   │   └── orchestration_and_settings.py                              [MODIFICATION - Provider get_finops_service]
│   │   ├── schemas/
│   │   │   └── finops.py                                                  [CRÉATION - Schémas Pydantic RFC 9457]
│   │   └── routers/
│   │       └── finops.py                                                  [CRÉATION - Routeur /api/v1/finops/*]
│   └── web/src/
│       ├── features/finops/
│       │   └── index.tsx                                                  [REFACTORING - Montage complet tableau de bord]
│       └── i18n/locales/
│           ├── fr.ts                                                      [MODIFICATION - Traductions FinOps sans jargon]
│           └── en.ts                                                      [MODIFICATION - Traductions anglaises]
└── tests/
    ├── unit/
    │   ├── test_story_6_2_finops_accounting_decimal.py                    [CRÉATION - Hypothesis sur calculs et arrondis]
    │   └── test_story_6_2_budget_circuit_guards.py                        [CRÉATION - Tests suspensions et retries]
    ├── integration/
    │   └── test_story_6_2_finops_postgres18.py                            [CRÉATION - Testcontainers PG18 + Redis]
    └── evals/
        └── test_story_6_2_cognitive_escalation_finops.py                  [CRÉATION - Scénario déterministe 0 $]
```

---

## 4. Ordered Tasks (Dependencies First)

### Tâche 1 : Migration Alembic & Élargissement des Statuts
- Créer `infra/migrations/versions/20261116_0602_story_6_2_finops_budgets_baselines_and_pauses.py` avec `down_revision = "20261116_0601"`.
- Modifier les contraintes CHECK de `workflow_runs.status` et `step_executions.status` pour incorporer `'PAUSED_MAX_RETRIES'` et `'PAUSED_BUDGET_EXCEEDED'`.
- Créer les tables `finops_scope_budgets`, `finops_workflow_baselines` et `finops_budget_overrides`.
- Mettre à jour `ORDERED_MUTABLE_TABLES_TO_CLEAR` dans `infra/scripts/maintenance/09_reset_db_first_boot.py`.

### Tâche 2 : Enums Kernel & Découpage de `cognitive_router.py`
- Mettre à jour `packages/orcia-core/src/orcia_core/kernel/enums.py` et `orchestration/models.py` avec les statuts de pause.
- Extraire `packages/orcia-core/src/orcia_core/orchestration/_cognitive_budget_guard.py` (< 300 lignes) de `cognitive_router.py`.
- Implémenter l'évaluation du seuil d'avertissement (80%) et du seuil dur (100%), ainsi que le bornage `max_agent_retries`.

### Tâche 3 : Moteur Comptable FinOps & Requêtes SQL Asynchrones
- Développer `packages/orcia-core/src/orcia_core/audit_finops/finops_accounting_service.py` effectuant tous les calculs monétaires en `Decimal` (`NUMERIC(12, 6)`).
- Implémenter la valorisation à 3 composantes (Setup amorti + Run consolidé + Temps humain) et l'écart TTM vs baseline.
- Rédiger les requêtes SQL dans `packages/orcia-core/src/orcia_core/audit_finops/_internal/sql_finops_accounting.py`.
- Développer `budget_guard_service.py` implémentant `BudgetCircuitGuardPort`.

### Tâche 4 : Routeur FastAPI `/api/v1/finops/*` & OpenAPI SDK
- Définir les schémas dans `apps/api/src/orcia_api/schemas/finops.py`.
- Créer `apps/api/src/orcia_api/routers/finops.py` exposant :
  - `GET /api/v1/finops/dashboard`
  - `PUT /api/v1/finops/budgets`
  - `PUT /api/v1/finops/baselines`
  - `POST /api/v1/runs/{run_id}/budget-override` (avec garde `enforce_scope_mutation_guard`).
- Régénérer le SDK OpenAPI via `.venv/bin/python scripts/export_openapi.py` (`0-diff`).

### Tâche 5 : Composants `@orcia/ui` & Refactor de `apps/web/src/features/finops/`
- Créer les composants dans `packages/ui/src/primitives/finops/` (`FinopsGovernanceDashboardView`, `FinopsKpiStrip`, `FinopsProcessAndTiersTab`, `FinopsBudgetPolicyModal`).
- Monter la vue complète dans `apps/web/src/features/finops/index.tsx`.
- Implémenter l'état vide strict lorsque `total == 0` (masquage des 4 KPI).
- Renseigner les props requises dans `zero-dead-buttons-and-silent-catches-audit.test.tsx` et ajouter le bouton d'aide contextuelle `ContextualInfoTriggerButton` pointant sur `finops-overview`.

### Tâche 6 : Pyramide des Tests `AD-17` & Évaluations Déterministes
- Couche 1a : Tests unitaires Python avec `hypothesis` vérifiant la précision `Decimal` sur 10 000 itérations sans divergence d'arrondi.
- Couche 1b : Tests composants Vitest vérifiant le montage sans `isJsdom` et la survie au rechargement de page (`F5`).
- Couche 2 : Tests d'intégration `testcontainers` PostgreSQL 18 + Redis simulant le dépassement de budget, la suspension du workflow et sa reprise par appel de l'API.
- Couche 4 : Évaluation déterministe à 0 $ dans `tests/evals/test_story_6_2_cognitive_escalation_finops.py`.
