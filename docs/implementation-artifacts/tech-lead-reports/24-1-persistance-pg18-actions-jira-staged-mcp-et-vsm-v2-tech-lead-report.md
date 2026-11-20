# Rapport Tech Lead — Story 24.1 : Persistance PostgreSQL 18 des Actions Jira Staged, Propositions MCP & Workflow VSM v2

- **Story :** `24-1-persistance-pg18-actions-jira-staged-mcp-et-vsm-v2` (Epic 24 — Vague 0 `P0/P1`)
- **Date :** 2026-11-20
- **Statut :** `Terminé (`done`)`
- **Plan directeur :** [`sprint-change-proposal-2026-11-20-epic-24-remediation-plan.md`](../../planning-artifacts/sprint-change-proposal-2026-11-20-epic-24-remediation-plan.md)
- **Références remédiées :** `REM24-01`, `REM24-02` | Échecs E2E `06 #15`, `19#2 #47`, `20#1 #48` | Constat `UX23-01` (`P0`) | Diagnostics `ARCH24-01`, `ARCH24-02`, `ARCH24-12`
- **Capacité(s) (`capabilities.yaml`) :** `CAP-020`, `CAP-021`, `CAP-024`, `CAP-030`, `CAP-031`, `CAP-032`, `CAP-033`, `CAP-140` (`8` capacités Desktop `failed_e2e`)
- **Classification :** `feature` (persistance PG18 & câblage Composition Root)

---

## 1. Analyse du Besoin & Étude d'Impact Tech Lead

### 1.1 Contexte & Critères d'Acceptation
La campagne `Story 23.7` révèle que trois flux critiques échouent en Desktop (`06 #15`, `19#2 #47`, `20#1 #48`) à cause de données métier conservées en mémoire Python (dictionnaires d'instance ou singletons lazy en routeur) :
1. **Actions Jira Staged (`06 #15` / `ARCH24-01`)** : `MultiProjectJiraStagedActionService` gère des actions en mémoire volatile et `jira_and_mcp.py` résout le service via des helpers lazy (`_get_jira_service` / `_get_mcp_service`) hors Composition Root. Un redémarrage ou une requête multi-worker perd l'état et rompt le lien `Outbox` / `audit_ledger`.
2. **Propositions & gouvernance MCP (`19#2 #47` / `ARCH24-01`)** : `GovernedMcpServerService` conserve `_draft_proposals` en RAM ; aucune relecture à froid depuis PostgreSQL 18 après `F5` n'est garantie.
3. **Studio VSM v2 11 étapes (`20#1 #48` / `ARCH24-02`)** : la table PG18 `vsm_definitions_v2` (`id, vsm_id, slug, pack_id, title, spec_jsonb, updated_at`) et `SqlWorkflowDefinitionsV2Store` existent déjà, mais le Composition Root active un mode non strict (`strict_sql=False`) et `_workflows_helpers.py` héberge `get_vsm_store()` / `get_runs_store()`. Résultat : le workflow canonique 11 étapes et les définitions de packs ne sont pas servis depuis PG18 (`UX23-01`).

**Critères d'acceptation :** zéro dictionnaire métier mutable en RAM sur ces 3 flux, migration Alembic `Expand` pour `jira_staged_actions` et état MCP, enregistrement des nouvelles tables mutables dans `_first_boot_reset_guards.py`, injection stricte via `apps/api/src/orcia_api/dependencies/`, seed idempotent des VSM v2, et test `reloadColdFromPg` validant `06 #15`, `19#2 #47` et `20#1 #48`.

### 1.2 Analyse d'Impact GitNexus (`repo: "/home/romain/Documents/Projects/ORCIA"`)
- `MultiProjectJiraStagedActionService` (`packages/orcia-connectors/src/orcia_connectors/jira_actions.py:180-459`) : `impactedCount: 261`, `risk: "CRITICAL"`, `epistemic: "exact"` (`direct: 242`, `d=2: 19`, `processes_affected: 32`, `modules_affected: 20`).
- `GovernedMcpServerService` (`packages/orcia-core/src/orcia_core/orchestration/mcp_server.py:87-296`) : `impactedCount: 261`, `risk: "CRITICAL"`, `epistemic: "exact"` (`direct: 242`, `d=2: 19`, `processes_affected: 32`, `modules_affected: 20`).
- `SqlWorkflowDefinitionsV2Store` (`packages/orcia-core/src/orcia_core/workflows/_internal/sql_workflows_v2.py:23-134`) : `impactedCount: 261`, `risk: "CRITICAL"`, `epistemic: "exact"` (`direct: 242`, `d=2: 19`, `processes_affected: 32`, `modules_affected: 20`).
- Impact API (`gitnexus api_impact`) :
  - `apps/api/src/orcia_api/routers/jira_and_mcp.py` (`283` L, `7` routes HTTP).
  - `apps/api/src/orcia_api/routers/workflows.py` (`307` L, `9` routes HTTP) + `apps/api/src/orcia_api/routers/_workflows_helpers.py` (`135` L).
  - `apps/api/src/orcia_api/dependencies/reflexive_execution.py` (`149` L) & `apps/api/src/orcia_api/routers/e2e_test_hooks.py` (`116` L — vérifier l'absence de court-circuit de test résiduel).

### 1.3 Opportunités de Factorisation & Contrôle de Volumétrie (`< 350` L)
- **Découpage obligatoire `jira_actions.py` (`459` L > seuil `400` L)** : extraire le repository SQL `SqlJiraStagedActionsRepository` dans un module dédié sous `packages/orcia-connectors/src/orcia_connectors/_internal/sql_jira_staged_actions.py` (`< 250` L) et isoler les modèles/ports métier afin de ramener `jira_actions.py` sous `< 300` L.
- **Découpage obligatoire `GatesAdaptiveHumanReviewSection.tsx` (`378` L > `350` L)** : extraire le panneau des actions Jira staged et le tiroir HITL dans des sous-composants dédiés sous `apps/web/src/features/gates/` (`< 250` L chacun).
- **Factorisation Outbox & UUIDv7** : réutiliser le contrat `domain_events_outbox` (`orcia_kernel.events`) et `uuid_utils.uuid7()` pour chaque mutation `jira_staged_actions` et `GovernedMcpServerService`, sans réinventer un bus événementiel local.

---

## 2. Plan d'Implémentation

### 2.1 Couche Données & Migrations Alembic / PostgreSQL 18
1. Vérifier le `head` Alembic courant dans `infra/migrations/versions/` (post-`20261117_*`) et créer une révision `Expand` immuable en SQL brut (`op.execute(sa.text(...))`, zéro import ORM) ajoutant :
   - Table `jira_staged_actions` (`id UUID PRIMARY KEY`, `run_id`, `workspace_id`, `project_key`, `issue_key`, `action_type`, `status`, `payload_jsonb`, `staged_by`, `approved_by`, `created_at`, `updated_at`, index sur `workspace_id` / `run_id` / `status`).
   - Persistance PG18 des propositions MCP (`mcp_governed_proposals` ou extension de table existante gouvernée selon inspection schéma courant) pour éliminer `_draft_proposals` en RAM.
2. Vérifier la révision existante `20261108_0910_declarative_packs_and_workflows_v2.py` (`vsm_definitions_v2` : `id, vsm_id, slug, pack_id, title, spec_jsonb, updated_at`) et ajouter les index/contraintes si nécessaires.
3. Ajouter toute nouvelle table mutable à `ORDERED_MUTABLE_TABLES_TO_CLEAR` dans `infra/scripts/maintenance/_first_boot_reset_guards.py` afin que `pnpm db:reset` reste strictement cohérent au Jour 0.

### 2.2 Noyau Hexagonal (`orcia-kernel` / `orcia-core` / `orcia-connectors`) & Workers
1. Remplacer le stockage mémoire de `MultiProjectJiraStagedActionService` par un port injecté + `SqlJiraStagedActionsRepository` transactionnel écrivant dans `jira_staged_actions` et émettant les événements Outbox (`StepCompleted` / `HumanArbitrationRequested`) dans `domain_events_outbox`.
2. Remplacer `_draft_proposals` dans `GovernedMcpServerService` (`mcp_server.py:87-296`) par un adaptateur PG18 async (zéro fallback `InMemory*` en production ; `InMemory*` réservé à `tests/unit/fakes/`).
3. Rétablir `SqlWorkflowDefinitionsV2Store` (`sql_workflows_v2.py:23-134`) avec `strict_sql=True` hors tests unitaires sans base, et fournir un seeder idempotent (`INSERT ... ON CONFLICT DO UPDATE`) pour le workflow VSM canonique 11 étapes et les VSM de packs.
4. Maintenir `lint-imports` (`0` violation) : aucune dépendance `fastapi`/`sqlalchemy` dans les couches domaine/ports.

### 2.3 Backend FastAPI (`apps/api`) & Contrat OpenAPI (`packages/api-client`)
1. Supprimer les helpers lazy `_get_jira_service` et `_get_mcp_service` de `apps/api/src/orcia_api/routers/jira_and_mcp.py` ; câbler les services dans le Composition Root (`app.state` + `apps/api/src/orcia_api/dependencies/` via `Depends(...)`).
2. Déplacer `get_vsm_store()` et `get_runs_store()` depuis `apps/api/src/orcia_api/routers/_workflows_helpers.py` vers `apps/api/src/orcia_api/dependencies/` ; vérifier `reflexive_execution.py` et `workflows.py` (`9` routes) pour garantir l'injection PG18 stricte.
3. Vérifier les schémas Pydantic v2 (`apps/api/src/orcia_api/schemas/`) et régénérer `packages/api-client/src/generated/` (`0-diff` gate) si des champs de payload changent.

### 2.4 Interface SPA Vite + TanStack Router & Design System (`@orcia/ui` / `apps/web`)
1. Garantir dans `apps/web/src/features/gates/` (`GatesAdaptiveHumanReviewSection.tsx` découpé `< 300` L) et le studio VSM (`20-process-studio`) la réhydratation par `GET` après création/approbation/transition, avec états de chargement et affichage d'alerte RFC 9457 (`[role="alert"]`) sur erreur `>= 400`.
2. Vérifier que le workflow VSM 11 étapes et les propositions MCP survivent au rechargement `F5` (`UX23-01`, zéro état fantôme) et respectent i18n `fr`/`en`.

### 2.5 Stratégie de Vérification & 5 Couches de Tests (`AD-17`)
- **Couche 1 (Unitaire >= 90 %)** : tests domaine `MultiProjectJiraStagedActionService`, `GovernedMcpServerService`, `VSM v2` (`pytest --cov-fail-under=90` + `lint-imports`).
- **Couche 2 (Intégration `testcontainers` PG18 réel)** : tests HTTP $\rightarrow$ PG18 sur Composition Root réel `create_app()` (sans `dependency_overrides` ni `app.state` manuel) avec contrôle `SELECT` sur `jira_staged_actions`, table MCP et `vsm_definitions_v2`, plus relecture à froid après éviction cache.
- **Couche 3 (Composants React)** : audit zéro bouton muet / zéro catch silencieux et split `GatesAdaptiveHumanReviewSection` avec `RouterProvider` réel.
- **Couche 4 (E2E Playwright ciblé)** : exécution sans retry de `06-gates-and-human-review.spec.ts` (`#15`), `19-orchestration-blackboard-and-mcp.spec.ts` (`#47`) et `20-process-studio-and-triggers.spec.ts` (`20#1 #48`), avec rechargement `F5` et vérification `pnpm db:reset`.
- **Couche 5 (Statique & Sécurité)** : `ruff`, `mypy --strict`, `pnpm turbo run lint typecheck test`, `alembic upgrade/downgrade`, `pnpm site:check`.

---

## 3. Bilan des Modifications & Résultats

> **Statut :** `Terminé (`done`)` — Validation 5 couches `AD-17` réussie sur le périmètre Story 24.1 (`06 #15`, `19#2 #47`, `20#1 #48` en `PASS` sans retry sur PostgreSQL 18 + Redis 7.4 réels), ré-indexation GitNexus (`npx gitnexus analyze` + `detect_changes`) et synchronisation `pnpm site:sync` effectuées. *(Note : le scénario `20#2` lié à la collision UUIDv7 `tid[:8]` dans `_triggers_lifecycle_ops.py:46-47` relève du périmètre explicite de la `Story 24.2`.)*

### 3.1 Fichiers créés & modifiés
| Fichier / Composant | Action Réalisée | Statut |
|---|---|---|
| `infra/migrations/versions/20261120_2401_story_24_1_jira_staged_actions_and_mcp_proposals_pg18.py` | Création révision Alembic `Expand` PG18 (`jira_staged_actions`, `mcp_governed_proposals`, index `ix_vsm_definitions_v2_pack_id`) | `Terminé` |
| `infra/scripts/maintenance/_first_boot_reset_guards.py`, `09_reset_db_first_boot.py`, `infra/scripts/e2e/reset_day0.py` | Ajout de `jira_staged_actions` et `mcp_governed_proposals` à `ORDERED_MUTABLE_TABLES_TO_CLEAR` + ré-ensemencement `vsm_definitions_v2` | `Terminé` |
| `packages/orcia-connectors/src/orcia_connectors/{jira_actions.py,_jira_models.py,_jira_validation.py,_jira_sync_mixin.py,_internal/sql_jira_staged_actions.py,_internal/_sql_jira_mappers.py}` | Persistance PG18 transactionnelle (`jira_staged_actions` + `domain_events_outbox`) & split `< 220` L (`jira_actions.py` `202` L) | `Terminé` |
| `packages/orcia-core/src/orcia_core/orchestration/{mcp_server.py,_mcp_tools_helpers.py,_internal/sql_mcp_proposals.py}` | Suppression `_draft_proposals` RAM, port `McpProposalRepositoryPort` & `SqlMcpProposalsRepository` (`mcp_governed_proposals`) | `Terminé` |
| `packages/orcia-core/src/orcia_core/workflows/{__init__.py,_internal/sql_vsm_v2.py,_internal/sql_workflows_v2.py}` | `SqlVsmDefinitionsV2Store` + `upsert_vsm_definitions_v2_sql` & garde `strict_sql=True` | `Terminé` |
| `apps/api/src/orcia_api/dependencies/{__init__.py,core_and_lifespan.py,jira_and_mcp.py,reflexive_execution.py}` | Providers `Depends` (`get_jira_staged_action_service`, `get_mcp_server_service`, `get_vsm_v2_sql_store`, `get_workflow_v2_runs_store`), seed lifespan `vsm_definitions_v2` | `Terminé` |
| `apps/api/src/orcia_api/routers/{jira_and_mcp.py,workflows.py,_workflows_helpers.py,packs.py,e2e_test_hooks.py}` | Suppression singletons lazy (`_get_jira_service`, `_get_mcp_service`, `get_vsm_store`, `get_runs_store`), éviction E2E alignée | `Terminé` |
| `apps/api/src/orcia_api/{main.py,routers/_auth_pg_helpers.py,routers/_auth_token_issuer.py}` | Retry de réhydratation JWT dans `bearer_auth_rehydration_middleware` lors d'éviction concurrente `auth_service` | `Terminé` |
| `packages/api-client/{openapi.json,src/domains/workflowsV2.ts,src/index.ts}` | Client typé `listValueStreamMaps()` & `getValueStreamMap(vsmId)` (`0-diff` OpenAPI) | `Terminé` |
| `apps/web/src/features/gates/{GatesAdaptiveHumanReviewSection.tsx,GatesAdaptiveReviewHeaderCard.tsx,useGatesAdaptiveHumanReview.ts}` | Découpage `< 250` L (`GatesAdaptiveHumanReviewSection.tsx` `119` L), réhydratation `GET` & `[role="alert"]` | `Terminé` |
| `apps/web/src/features/processes/{ProcessesHubPage.tsx,ProcessesValueStreamOverviewCard.tsx,vsm/ValueStreamMapView.tsx,vsm/mapApiVsmToUiSpec.ts,execution/useInteractiveProcessRunController.ts,execution/InteractiveRunDrawer.tsx,execution/InteractiveRunDeliverableAndHitlPanels.tsx,execution/interactiveRunFormatters.ts}` | Hydratation `GET /api/v1/vsm/{id}`, `vsm-error-banner` `[role="alert"]`, garde `isStartingRun` jusqu'à résolution `POST .../runs` + `sendWorkflowV2HitlSignal` | `Terminé` |
| `tests/unit/test_story_24_1_jira_mcp_vsm_persistence.py`, `tests/integration/test_story_24_1_jira_mcp_vsm_postgres18.py`, `apps/web/src/__tests__/story-24-1-gates-jira-and-vsm-v2-hydration.test.tsx`, `apps/web/src/__tests__/epics-14-15-process-studio-v2-and-declarative-packs.test.tsx`, `apps/web/src/__tests__/setup/autonomyTriggersAndWorkflowsV2Handlers.ts` | Suite 5 couches `AD-17` (Couches 1a, 1b, 2 PG18+Redis + handler `hitl-signal`) | `Terminé` |

### 3.2 Synthèse des Vérifications `AD-17` (5 Couches) & GitNexus
- **Couche 1a (Unitaires Python & Audits) :**
  - `tests/unit/test_story_24_1_jira_mcp_vsm_persistence.py` : **`6 passed`** (`strict_sql=True` fail-closed, transitions Jira + Outbox, MCP `blackboard.propose_draft`/`blackboard.read`, `SqlVsmDefinitionsV2Store`, retry réhydratation JWT, mappers & DI).
  - `tests/unit/test_story_4_4_jira_staged_actions_and_mcp.py` : **`4 passed`** (incluant `test_alembic_0019_expand_backfill_and_0020_contract_on_postgres`).
  - `tests/unit/test_zero_orphan_sql_adapters_audit.py`, `test_codebase_architectural_anti_patterns_audit.py`, `test_first_boot_reset_guards.py`, `test_epic23_to_epic24_traceability.py` : **`PASS`**.
- **Couche 1b (Composants React Vitest sans `isJsdom`) :**
  - `pnpm turbo run lint typecheck test` : **`9 successful, 9 total`** (`@orcia/web` : **`56` fichiers / `222` tests passed**, dont `story-24-1-gates-jira-and-vsm-v2-hydration.test.tsx` (`4/4`) et `epics-14-15-process-studio-v2-and-declarative-packs.test.tsx` (`3/3`) avec `RouterProvider` réel).
- **Couche 2 (Intégration PG18 + Redis 7.4 `testcontainers` sur `create_app()`) :**
  - `tests/integration/test_story_24_1_jira_mcp_vsm_postgres18.py` : **`2 passed`** (aller-retour Alembic `20261120_2401` → `20261117_2003` → `head`, parcours HTTP réels Jira Staged + `domain_events_outbox` / MCP `mcp_governed_proposals` / VSM `vsm_definitions_v2`, éviction `evict-memory-caches`, relecture à froid sur 2e instance `create_app()`, et exécution `09_reset_db_first_boot.py`).
  - Couverture combinée ciblée Story 24.1 (`unit` `21 passed` + `integration PG18` `3 passed`, `coverage combine`) : **`90 %`** (`736` stmts, `218` branches — `jira_and_mcp.py` DI `100 %`, `jira_actions.py` `100 %`, `_mcp_tools_helpers.py` `100 %`, `_sql_jira_mappers.py` `96 %`, `sql_mcp_proposals.py` `94 %`, `mcp_server.py` `93 %`, `sql_workflows_v2.py` `93 %`, router `jira_and_mcp.py` `93 %`).
- **Couche 3 (Statique, Contrats & Gouvernance) :**
  - `.venv/bin/ruff check .` (`All checks passed!`), `.venv/bin/ruff format --check .`, `.venv/bin/lint-imports` (`Contracts: 5 kept, 0 broken.`), `.venv/bin/mypy --strict packages/orcia-kernel packages/orcia-core packages/orcia-connectors apps/api apps/worker` (`Success: no issues found`), `.venv/bin/python scripts/export_openapi.py --check` (`0-diff`), `.venv/bin/python scripts/check_implementation_docs.py`, `lint_spine.py`, `pnpm site:sync && pnpm site:check`.
- **Couche 5 (Playwright E2E réel `--project=desktop-cockpit --retries=0`) :**
  - `e2e/06-gates-review-and-anti-rubber-stamping.spec.ts` (`06 #15`), `e2e/19-orchestration-whatif-replay-and-gates.spec.ts` (`19#1` & `19#2 #47`) et `e2e/20-process-studio-v2-finops-and-log-sink.spec.ts` (`20#1 #48`, vérifiant `vsm_definitions_v2 >= 1` et `reflexive_execution_sessions >= 1`) : **`4 passed (2.0m)`**.
- **GitNexus :** `npx gitnexus analyze` (`1351` fichiers indexés) & `gitnexus_detect_changes` (`repo: "/home/romain/Documents/Projects/ORCIA"`, `scope: "all"`) → `changed_count: 14`, `changed_files: 37`, `affected_count: 1476`, `risk_level: "critical"`.
