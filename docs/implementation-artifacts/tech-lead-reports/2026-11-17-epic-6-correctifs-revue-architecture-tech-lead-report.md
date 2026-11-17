# 2026-11-17 — Correctifs Suite à la Revue d'Architecture & UX (`VALIDATE`) de l'Epic 6

- **Date** : 2026-11-17
- **Story / Clé Sprint** : `2026-11-17-epic-6-correctifs-revue-architecture` (`Epic 6` — Stories `6-1` à `6-4`)
- **Capacité(s)** : `CAP-065`, `CAP-200` — classification : `hygiène / feature / ux`
- **Auteur / Contexte** : Résolution exhaustive des 5 constats `BLOCKING` (`BLOCKING-01..05`), 5 constats `MAJOR` (`MAJOR-01..05`) et 3 constats `MINOR` (`MINOR-01..03`) issus de la revue `VALIDATE` de Winston & Sally sur la branche `feat/epic-6-audit-ledger-finops-and-human-reversibility` (`FR-25`, `FR-26`, `FR-27`, `AD-17`, `AD-19`, `AD-21`, `DEC-SEC-01`).
- **Commits associés** : *(implémentation terminée et vérifiée sur `feat/epic-6-audit-ledger-finops-and-human-reversibility`, prêt pour commit)*

---

## 1. Analyse du Besoin & Étude d'Impact Tech Lead (Pré-Implémentation)

### 1.1 Contexte & Problématique
La revue finale d'architecture & UX (`VALIDATE`) de l'Epic 6 a rendu le verdict **`CHANGES_REQUIRED`**, identifiant :
1. **`BLOCKING-01` (Crash SQL `wd.title` + produits cartésiens + périmètres `BU`/`TEAM`)** : `fetch_dashboard_processes_sql` interroge une colonne inexistante `wd.title` sur `workflow_definitions` (masquée en `[]` par `except Exception: return []`), joint simultanément `workflow_runs`, `audit_ledger`, `finops_budget_overrides` et `finops_workflow_baselines` (multipliant les sommes et décomptes), et ignore la hiérarchie `org_units` (`BU`/`TEAM`) dans les requêtes dashboard.
2. **`BLOCKING-02` (Dérogation budgétaire UI -> API cassée)** : `FinopsProcessItemResponse` n'expose ni `sample_paused_run_id` ni `paused_reason`, `finopsMappers.ts` laisse `samplePausedRunId: undefined`, `FinopsProcessAndTiersTab.tsx` se replie sur `p.workflowId` (envoyant un `workflow_definition_id` à `POST /runs/{run_id}/budget-override` -> violation FK) sans `workspace_id`.
3. **`BLOCKING-03` (`fetch()` brut + crash `HTTP 422` `"scope-global"` + modale désynchronisée)** : `activityApiBridge.ts` contourne `@orcia/api-client` par `globalThis.fetch` (sans Bearer ni en-têtes `X-Orcia-*`), `packages/api-client` n'exporte pas le domaine `auditFinops`, `features/finops/index.tsx` envoie `"scope-global"` aux pilules `WORKSPACE`/`TEAM`, et `FinopsBudgetPolicyModal` n'est pas réinitialisée sur `[open, currentScopeType, currentScopeId]`.
4. **`BLOCKING-04` (Câblage runtime Outbox & `BudgetGuardService`)** : `OutboxEventBus` dans `apps/worker/outbox_relay.py` n'injecte pas `AuditLedgerOutboxSubscriber(SqlAuditLedgerService(engine))`, `BudgetGuardService` n'est pas injecté dans `CognitiveModelRouterService` (`core_and_lifespan.py`), `evaluate_budget_allowance` ne totalise pas mensuellement selon `GLOBAL -> BU -> TEAM -> WORKSPACE` avec `warning_threshold_pct`/`hard_stop_pct`, et `approve_budget_override` n'écrit pas transactionnellement dans `domain_events_outbox` + `audit_ledger` et ne signale pas le réveil DBOS.
5. **`BLOCKING-05` (Faille IDOR lecture & contournements de garde en mutation + FK magique)** : les routeurs `audit_ledger.py`, `finops.py`, `finops_cognitive.py` et `finops_remote.py` ne filtrent/contrôlent pas le périmètre `user` en lecture (`GET`), autorisent le contournement de `enforce_scope_mutation_guard` lorsque `workspace_id`/`scope_id` est omis ou hors `WORKSPACE`, et `sql_finops_accounting.py` utilise un UUID magique `018d0000-...` pour `requested_by` ainsi qu'une jointure cartésienne `step_executions × audit_ledger` dans `fetch_run_finops_state_sql`.
6. **5 `MAJOR` (`MAJOR-01` à `MAJOR-05`)** :
   - `MAJOR-01` : Migration Alembic `20261117_0605` pour élargir `workflow_definitions.adaptive_gate_policy` (`CHECK`), persistance sur `workflow_definitions`, `ResourceNotFoundError` (`404`) si recommandation inconnue, suppression d'`assert applied.applied_at is not None`.
   - `MAJOR-02` : Vraie boucle async `await asyncio.sleep` dans `ConnectorInvoker.invoke_async` (zéro `time.sleep` bloquant) et unification via `ConnectorInvoker`.
   - `MAJOR-03` : `"actor_id": actor_id` dans `AdminConnectionTested.create` et injection `CurrentUserDep` dans `ai_models_hub.py` (zéro `"admin"` codé en dur).
   - `MAJOR-04` : Suppression d'`assert engine is not None` dans `get_finops_accounting_service`, synchronisation `_engine` de `finops_accounting_service` et `cognitive_impact_service` dans `core_and_lifespan.py`, calcul SQL réel de `human_time_cost_usd` et `cache_savings_usd`, log structuré `get_logger` à la place de `contextlib.suppress(Exception)` et `logging.getLogger`.
   - `MAJOR-05` : Migration de `ActivityProvenanceModal` dans `packages/ui` avec `<OrciaDialog>` accessible RGAA, enrichissement de `apps/web/e2e/12-finops-and-audit-provenance.spec.ts` (assertion mobile `scrollWidth <= innerWidth` + scénario desktop données réelles/provenance), réconciliation de `capabilities.yaml` (`CAP-065`, `CAP-200`) et `pnpm site:sync`.
7. **3 `MINOR` (`MINOR-01` à `MINOR-03`)** :
   - `MINOR-01` : Découpage sous `350` lignes des fichiers touchés (`ai_models_hub.py`, `contextualHelpCatalog.ts`, `core_and_lifespan.py`, `fr.ts`/`en.ts`).
   - `MINOR-02` : Éradication des chaînes en dur (`"Run:"`, fallbacks FR dans `FinopsProcessAndTiersTab`, enums `HIGH_CRITICAL`/`STANDARD`/`simple`/`low`), réinitialisation de `FinopsBudgetOverrideModal`, suppression du double en-tête `/finops`, ajout de `FinopsConnectorQuotaModal` dans `zero-dead-buttons-and-silent-catches-audit.test.tsx`.
   - `MINOR-03` : Sécurisation des `downgrade()` `20261116_0601` / `20261116_0602` (attention : vérification de la politique d'immutabilité des migrations — sécurisation sans casser la chaîne), propagation `ProgrammingError` dans `sql_connector_circuit.py`, filtrage `BU`/`TEAM` dans `list_connector_quotas_sql`, distinction explicite `has_declared_baseline` sans fabriquer `-25 %` TTM.

### 1.2 Exploration, Analyse d'Impact GitNexus, Factorisation & Dette Technique
- **Analyse d'Impact GitNexus (`gitnexus_impact` sur `/home/romain/Documents/Projects/ORCIA`)** :
  - `fetch_dashboard_processes_sql` : `impactedCount: 1` (`FinopsAccountingService`, risque `LOW`).
  - `BudgetGuardService` : `impactedCount: 1` (risque `LOW`, non encore câblé dans `core_and_lifespan.py`).
  - `OutboxEventBus` : `impactedCount: 1` (risque `LOW`, sans `audit_sink` par défaut dans `apps/worker`).
  - `FinopsAccountingService` : `impactedCount: 1` (risque `LOW`).
  - `ConnectorInvoker` : `impactedCount: 9` (`2` directs, `4` depth 2, `3` depth 3, risque `LOW`).
  - `MatrixPermissionEvaluator.enforce_scope_mutation_guard` : `impactedCount: 34` (`5` directs, `15` processus affectés, risque `CRITICAL` — ne pas modifier la signature existante, réutiliser telle quelle depuis les routeurs Epic 6).
  - `CognitiveModelRouterService` : `impactedCount: 4` (risque `LOW`).
  - `AdminConnectionTested` : `impactedCount: 37` (`6` directs, `11` depth 2, `20` depth 3, risque `MEDIUM`).
- **Opportunités de Factorisation & Résorption de Dette Technique** :
  - Factoriser un helper SQL partagé de filtrage hiérarchique de périmètre (`GLOBAL | BU | TEAM | WORKSPACE` via `WITH RECURSIVE org_tree`) dans `packages/orcia-core/src/orcia_core/audit_finops/_internal/_sql_scope_filter.py` réutilisé par `sql_finops_dashboard.py`, `sql_connector_quotas.py`, `sql_audit_ledger_mappers.py`, `sql_finops_accounting.py`.
  - Factoriser un garde-fou RBAC/ABAC partagé pour les routeurs FinOps/Audit dans `apps/api/src/orcia_api/routers/_finops_auth_guards.py` (résolution de `workspace_id` depuis `workflow_runs` / `finops_connector_quotas` / `workflow_definitions`, vérification de lecture `resolve_accessible_workspaces`, vérification de mutation `enforce_scope_mutation_guard` + rôles gouverneurs `PLATFORM_ADMIN` / `BU_DIRECTOR` / `TEAM_LEAD` pour `GLOBAL`/`BU`/`TEAM`).
  - Découper les fichiers volumineux (`MINOR-01`) en sous-modules ciblés `< 350` lignes (`_ai_models_connection_helpers.py`, `_lifespan_bootstrap.py` ou extraction de helpers, découpage de `contextualHelpCatalog.ts` et des fichiers de locales si besoin).

---

## 2. Plan d'Implémentation

### 2.1 Schéma de Données & Migrations Alembic (`infra/migrations/versions/`)
- Créer `infra/migrations/versions/20261117_0605_epic6_review_adaptive_gate_policy_check.py` (`down_revision = "20261116_0604"`) :
  - `upgrade()` : remplacer `ck_workflow_definitions_adaptive_gate_policy` sur `workflow_definitions.adaptive_gate_policy` pour inclure `'STRICT'`, `'STANDARD'`, `'FAST_TRACK'`, `'RISK_OR_EXCEPTION_BASED'`, `'SAMPLING_20_PCT'`, `'STRENGTHEN_ANCHORS'` en SQL brut.
  - `downgrade()` : reclasser les valeurs étendues vers `'STANDARD'` avant de restaurer l'ancienne contrainte `CHECK ('STRICT', 'STANDARD', 'FAST_TRACK')`.
- Sécuriser les `downgrade()` de `20261116_0601` et `20261116_0602` (`MINOR-03`) en nettoyant/reclassant les éventuelles lignes Epic 6 avant de restaurer les anciens `CHECK`.

### 2.2 Noyau Métier Hexagonal, Orchestration & Workers (`packages/orcia-core/`, `apps/worker/`)
- `packages/orcia-core/src/orcia_core/audit_finops/_internal/sql_finops_dashboard.py` & `sql_connector_quotas.py` & `sql_connector_circuit.py` :
  - Remplacer `wd.title` par `COALESCE(NULLIF(wd.steps_schema_jsonb->>'title', ''), NULLIF(split_part(wd.uri, '/', -1), ''), wd.uri)`.
  - Réécrire `fetch_dashboard_processes_sql` avec CTE anti-produit-cartésien (`scoped_workspaces`, `run_ledger`, `run_overrides`, `wf_baselines`) + `sample_paused_run_id` + `sample_paused_status`.
  - Filtrage hiérarchique `BU`/`TEAM` via `WITH RECURSIVE` sur `org_units` sur toutes les requêtes dashboard (y compris `open_circuits` et `list_connector_quotas_sql`).
  - Calculer réellement `human_time_cost_usd` et `cache_savings_usd` depuis PostgreSQL (`audit_ledger` + `finops_workflow_baselines` / économies de cache).
  - Remplacer `logging.getLogger` par `orcia_core.observability.logging.get_logger`, supprimer les `except Exception: return []` masquant `UndefinedColumnError` / `ProgrammingError` (n'accepter une absence de table qu'en contexte unitaire sans schéma, et jamais dans `reset_connector_circuit_sql`).
- `packages/orcia-core/src/orcia_core/audit_finops/finops_accounting_service.py` & `sql_finops_accounting.py` & `budget_guard_service.py` :
  - Exposer `sample_paused_run_id`, `paused_reason`, `has_declared_baseline` dans les modèles de domaine FinOps ; ne plus fabriquer `-25 %` TTM quand aucune baseline n'est déclarée (`MINOR-03`).
  - Corriger `insert_budget_override_sql` (supprimer UUID magique `018d0000-...`, valider vers `users(id)` ou lever `ValidationDomainError`) et `fetch_run_finops_state_sql` (supprimer produit cartésien `step_executions × audit_ledger`).
  - Corriger `BudgetGuardService.evaluate_budget_allowance` pour agréger mensuellement selon `GLOBAL -> BU -> TEAM -> WORKSPACE` avec `warning_threshold_pct` et `hard_stop_pct`.
  - Dans `approve_budget_override`, persister transactionnellement `BudgetOverrideApproved` dans `domain_events_outbox` + `audit_ledger` et déclencher la reprise des steps `PAUSED_*` -> `PENDING` + réveil DBOS si applicable.
  - Remplacer `contextlib.suppress(Exception)` SSE par un log structuré `get_logger`.
- `packages/orcia-core/src/orcia_core/audit_finops/cognitive_impact_service.py` & `_internal/sql_cognitive_recommendations.py` :
  - Mettre à jour `workflow_definitions.adaptive_gate_policy` dans `apply_policy_recommendation`, lever `ResourceNotFoundError` (`404`) si `recommendation_id` inconnu.
- `packages/orcia-core/src/orcia_core/permissions/connector_invoker.py` :
  - Boucle async réelle avec `await asyncio.sleep(wait_s)` dans `invoke_async` (`MAJOR-02`).
- `packages/orcia-core/src/orcia_core/kernel/_finops_audit_events.py` :
  - Inclure `"actor_id": actor_id` dans `AdminConnectionTested.create` (`MAJOR-03`).
- `apps/worker/src/orcia_worker/outbox_relay.py` :
  - Injecter `AuditLedgerOutboxSubscriber(SqlAuditLedgerService(engine))` dans `OutboxEventBus` (relais Dramatiq/DBOS/SQL batch).

### 2.3 Couche Backend API, Sécurité & Contrats (`apps/api/`, `packages/api-client/`)
- `apps/api/src/orcia_api/dependencies/core_and_lifespan.py` & `orchestration_and_settings.py` :
  - Câbler `BudgetGuardService` dans `CognitiveModelRouterService(..., budget_guard=...)`.
  - Synchroniser `_engine` de `finops_accounting_service` et `cognitive_impact_service` dans `core_and_lifespan.py`.
  - Remplacer `assert engine is not None` dans `get_finops_accounting_service` par une résolution via `get_or_create_shared_db_engine(request)` / `OrciaDomainError` 503.
  - Découper `core_and_lifespan.py` sous `< 350` lignes (`MINOR-01`).
- `apps/api/src/orcia_api/routers/{audit_ledger,finops,finops_cognitive,finops_remote}.py` & `_finops_auth_guards.py` :
  - Fermer les failles IDOR sur toutes les routes `GET` (filtrage via `resolve_accessible_workspaces` / rejet `403 ScopeAccessDeniedError`).
  - Sur toutes les mutations, résoudre le périmètre réel côté serveur depuis PostgreSQL, appeler `auth_svc.evaluator.enforce_scope_mutation_guard` et vérifier les habilitations `PLATFORM_ADMIN` / `BU_DIRECTOR` / `TEAM_LEAD` sur `GLOBAL`/`BU`/`TEAM`.
  - Supprimer `assert applied.applied_at is not None` dans `finops_cognitive.py`.
- `apps/api/src/orcia_api/routers/ai_models_hub.py` & `mcp_and_test_bench.py` :
  - Injecter `user: CurrentUserDep` dans `ai_models_hub.py` pour `AdminConnectionTested` (`MAJOR-03`) et découper `ai_models_hub.py` sous `< 350` lignes (`MINOR-01`).
  - Unifier l'appel distant dans `mcp_and_test_bench.py` via `ConnectorInvoker` lorsque pertinent (`MAJOR-02`).
- `apps/api/src/orcia_api/schemas/finops.py` & `packages/api-client/` :
  - Exposer `sample_paused_run_id` et `paused_reason` (`"BUDGET" | "RETRIES"`) ainsi que `has_declared_baseline: bool` dans les schémas Pydantic.
  - Exporter `auditFinops` dans `packages/api-client/src/domains/auditFinops.ts` et `packages/api-client/src/index.ts`.
  - Régénérer le SDK OpenAPI via `.venv/bin/python scripts/export_openapi.py` (`0-diff`).

### 2.4 Interface Utilisateur & Expérience (`packages/ui/`, `apps/web/`)
- `packages/ui/src/primitives/ActivityProvenanceModal.tsx` (déplacé depuis `apps/web/src/routes/`) utilisant `<OrciaDialog>` accessible RGAA (`MAJOR-05`) et exporté dans `@orcia/ui`.
- `apps/web/src/routes/activityApiBridge.ts` : remplacer `globalThis.fetch` par le client typé `@orcia/api-client` (`auditFinops`, Bearer + `X-Orcia-*`).
- `apps/web/src/features/finops/finopsMappers.ts`, `features/finops/index.tsx`, `FinopsProcessAndTiersTab.tsx`, `FinopsBudgetPolicyModal.tsx`, `FinopsBudgetOverrideModal.tsx`, `FinopsHumanMasteryTab.tsx` :
  - Mapper `sample_paused_run_id` et `paused_reason` sans fallback `workflowId`, désactiver/masquer le bouton de rallonge si absent, transmettre `workspace_id` dans `handleSubmitOverride`.
  - Corriger la résolution de `scopeId` UUID dans `features/finops/index.tsx` (ne jamais passer `"scope-global"` aux pilules `WORKSPACE`/`TEAM`).
  - Passer `currentScopeId` à `FinopsBudgetPolicyModal` + `useEffect` sur `[open, currentScopeType, currentScopeId]`, et réinitialiser `FinopsBudgetOverrideModal` via `useEffect`.
  - Remplacer les libellés en dur (`"Run:"`, fallbacks FR, enums bruts) via `i18n`, supprimer le double en-tête `/finops`, découper `contextualHelpCatalog.ts` et `fr.ts`/`en.ts` sous `< 350` lignes (`MINOR-01`, `MINOR-02`).

### 2.5 Analyse d'Impact sur la Pyramide des Tests (`AD-17`)
- **Couche 1a & 1b** : Adapter/compléter les tests unitaires Python (`test_story_6_1..6_4_*.py`) et Vitest (`story-6-1..6-4-*.test.tsx`, `zero-dead-buttons-and-silent-catches-audit.test.tsx`).
- **Couche 2 (`PG18`)** : Vérifier `test_story_6_*.py` avec assertion stricte sur `processes` non vide, calcul sans produit cartésien, hiérarchie `BU`/`TEAM`, Outbox -> `audit_ledger`, `BudgetGuardService` et RBAC/IDOR.
- **Couche 3 (`Contrats`)** : `export_openapi.py` `0-diff`, `lint-imports`, `lint_spine.py`, `tests/contract`.
- **Couche 4 (`Evals`)** : `tests/evals`.
- **Couche Sécurité** : `tests/security` (IDOR lecture, `403` observateur/hors-périmètre sur mutations, fuite de secrets).
- **Couche 5 (`E2E Playwright`)** : `11-screens-smoke-without-server-errors.spec.ts` et `12-finops-and-audit-provenance.spec.ts` (assertion mobile `scrollWidth <= innerWidth` + scénario desktop données réelles / provenance).
- **Registre & Site** : Mise à jour de `docs/product/capabilities.yaml` (`CAP-065`, `CAP-200`), `sprint-status.yaml` (`epic-6: done`), `pnpm site:sync && pnpm site:check`.

---

## 3. Bilan des Modifications & Résultats (Post-Implémentation)

### 3.1 Synthèse des Fichiers Créés / Modifiés / Supprimés
| Couche / Module | Fichiers créés (`C`), modifiés (`M`) ou supprimés (`D`) | Rôle & Traçabilité (`BLOCKING` / `MAJOR` / `MINOR`) |
| --- | --- | --- |
| **Migrations Alembic** | `M` `infra/migrations/versions/20261116_0601_story_6_1_audit_ledger_append_only.py`, `M` `20261116_0602_story_6_2_finops_budgets_baselines_and_pauses.py`, `C` `20261117_0605_epic6_review_adaptive_gate_policy_check.py` | `MINOR-03` (`downgrade()` sécurisés sur `0601`/`0602`), `MAJOR-01` (élargissement du `CHECK` `adaptive_gate_policy` sur `workflow_definitions`, `head` = `20261117_0605`) |
| **Noyau `orcia_core` (`audit_finops`, `kernel`, `orchestration`, `permissions`)** | `C` `packages/orcia-core/src/orcia_core/audit_finops/_finops_accounting_helpers.py`, `_internal/_sql_finops_baselines.py`, `_internal/_sql_scope_filter.py`, `sql_finops_dashboard_processes.py`, `permissions/_connector_invoker_loops.py` ; `M` `_internal/sql_audit_ledger.py`, `_internal/sql_audit_ledger_mappers.py`, `_internal/sql_cognitive_impact.py`, `_internal/sql_cognitive_recommendations.py`, `_internal/sql_connector_circuit.py`, `_internal/sql_connector_quotas.py`, `_internal/sql_finops_accounting.py`, `_internal/sql_finops_dashboard.py`, `budget_guard_service.py`, `cognitive_impact_service.py`, `connector_quota_service.py`, `finops_accounting_service.py`, `finops_models.py`, `models.py`, `outbox_subscriber.py` ; `M` `kernel/_finops_audit_events.py`, `orchestration/_cognitive_budget_guard.py`, `permissions/connector_invoker.py`, `permissions/evaluator.py` | `BLOCKING-01..05`, `BLOCKING-RES-01` (attribution `workspace_id` + `scope_path = WORKSPACE/{ws_id}` et filtrage strict `fetch_applied_recommendations_sql`), `BLOCKING-RES-02` (isolation `list_workflow_baselines_sql` sur `?scope_type=GLOBAL` selon `allowed_workspace_ids`), `MAJOR-01..04`, `MINOR-01`/`03` (suppression `contextlib.suppress` avec `get_logger`, scission `< 325` l. sur `connector_invoker`, `sql_finops_accounting`, `finops_accounting_service`, `sql_cognitive_impact`, `sql_finops_dashboard`) |
| **Worker & API FastAPI (`apps/worker`, `apps/api`)** | `C` `apps/api/src/orcia_api/dependencies/_core_providers.py`, `apps/api/src/orcia_api/routers/_ai_models_test_and_reindex_routes.py`, `apps/api/src/orcia_api/routers/_finops_auth_guards.py`, `apps/api/src/orcia_api/routers/_finops_scope_guards.py` ; `M` `apps/worker/src/orcia_worker/outbox_relay.py`, `apps/api/src/orcia_api/dependencies/core_and_lifespan.py`, `orchestration_and_settings.py`, `routers/ai_models_hub.py`, `routers/audit_ledger.py`, `routers/finops.py`, `routers/finops_cognitive.py`, `routers/finops_remote.py`, `schemas/finops.py` | `BLOCKING-02` (`sample_paused_run_id`, `paused_reason`), `BLOCKING-04` (câblage `AuditLedgerOutboxSubscriber` + `BudgetGuardService` + `run_resumer`), `BLOCKING-05` (contrôles lecture + `enforce_scope_mutation_guard`), `MAJOR-03` (`CurrentUserDep` dans `ai_models_hub`), `MAJOR-04` (suppression `assert`, log SSE), `MINOR-01` (`< 320` lignes sur `core_and_lifespan.py`, `ai_models_hub.py`, `_finops_auth_guards.py` & `_finops_scope_guards.py`) |
| **SDK `@orcia/api-client` & UI `@orcia/ui`** | `C` `packages/api-client/src/domains/auditFinops.ts`, `packages/ui/src/primitives/ActivityProvenanceModal.tsx` ; `M` `packages/api-client/{openapi.json,src/generated/schema.ts,src/index.ts}`, `packages/ui/src/index.ts`, `ActivityLogExplorerView.tsx`, `FourZoneDirectionCShell.tsx`, `activityLogHelpers.ts`, `finops/{FinopsBudgetOverrideModal,FinopsBudgetPolicyModal,FinopsDashboardTypes,FinopsGovernanceDashboardView,FinopsHumanMasteryTab,FinopsProcessAndTiersTab}.tsx` | `BLOCKING-02`/`03` (`auditFinops`, suppression fallback `workflowId`, `scopeId`), `MAJOR-05` (`ActivityProvenanceModal` sur `OrciaDialog`, collapse shell mobile `< 768px`/`< 1024px`), `MINOR-02` (`i18n` enums/préfixes, reset modales) |
| **Frontend `apps/web` & E2E** | `C` `apps/web/src/components/_contextualHelpSections.ts`, `apps/web/src/i18n/locales/gates_and_inbox_labels.ts` ; `D` `apps/web/src/routes/ActivityProvenanceModal.tsx` ; `M` `apps/web/src/components/{ModuleWorkspaceView,ShellContainer,contextualHelpCatalog,useShellContainerState}.ts(x)`, `features/finops/{finopsMappers,index}.ts(x)`, `i18n/locales/{activity_labels,en,finops_human_mastery_labels,finops_labels,fr}.ts`, `routes/{activity.tsx,activityApiBridge.ts}`, `__tests__/zero-dead-buttons-and-silent-catches-audit.test.tsx`, `e2e/12-finops-and-audit-provenance.spec.ts` | `BLOCKING-02`/`03` (zéro `fetch` brut dans `activityApiBridge.ts`, UUID `scopeId` sans `"scope-global"`), `MAJOR-05` (E2E mobile `scrollWidth <= innerWidth` & desktop), `MINOR-01` (découpage `< 350` lignes), `MINOR-02` (suppression double en-tête `/finops` + `ActivityProvenanceModal` dans audit anti-boutons-muets) |
| **Tests & Gouvernance / Catalogue** | `M` `tests/unit/test_story_6_{2_budget_circuit_guards,2_finops_accounting_decimal,3_cognitive_governance_and_drift,4_sql_connector_quotas_unit}.py`, `tests/integration/api/test_story_6_{1_audit_ledger,2_finops,3_cognitive_impact,4_connector_quotas}_postgres18.py`, `docs/product/capabilities.yaml`, `docs/implementation-artifacts/sprint-status.yaml`, `docs/implementation-artifacts/tech-lead-reports/README.md`, `apps/web/src/generated/orciaSiteManifest.ts`, `docs/site-catalog/index.html` ; `D` `docs/implementation-artifacts/epic-6-final-review.md` | Clôture `epic-6: done`, `CAP-065`/`CAP-200`, archivage définitif des constats de `epic-6-final-review.md`, régénération `site:sync` (`145` rapports) |

### 3.2 Métriques & Qualité (Avant / Après)
- **Qualité & Contrats Python (`ruff`, `mypy`, `lint-imports`, `lint_spine`, `OpenAPI`)** :
  - `.venv/bin/ruff format --check .` : **PASS** (`930` fichiers formatés).
  - `.venv/bin/ruff check .` : **PASS** (`All checks passed!`).
  - `.venv/bin/mypy --strict packages/orcia-core packages/orcia-connectors apps/api apps/worker` : **PASS** (`Success: no issues found in 407 source files`).
  - `.venv/bin/lint-imports` : **PASS** (`Contracts: 5 kept, 0 broken` sur `450` fichiers / `2984` dépendances).
  - `.venv/bin/python scripts/export_openapi.py --check` : **PASS** (`0-diff`).
  - `.venv/bin/python .agent/skills/bmad-architecture/scripts/lint_spine.py --workspace docs/planning-artifacts/architecture/architecture-ORCIA-2026-10-24` : **PASS** (`total_findings: 0`).
- **Couverture & Suites de Tests** :
  - Suite Python complète combinée (`.venv/bin/pytest -q tests/unit tests/contract tests/evals tests/security tests/integration --cov=packages/orcia-core --cov-fail-under=90`) : **674 passed, 0 failed, 0 skipped**, couverture combinée `packages/orcia-core` = **91.41%** (`17235` Stmts / `1007` Miss / `3620` Branch / `611` BrPart, `>= 90%` requis atteint).
  - Intégration PostgreSQL 18 / Redis 7.4 `testcontainers` Epic 6 (inclus dans les `674` tests verts, `test_story_6_2` & `test_story_6_3` enrichis avec `BLOCKING-RES-01` et `BLOCKING-RES-02`) : isolation inter-espaces sur les recommandations appliquées et les baselines sur `?scope_type=GLOBAL`, `processes` non vide sans produit cartésien, filtrage récursif `BU`, Outbox + `audit_ledger` `BudgetOverrideApproved`, `workflow_definitions.adaptive_gate_policy == 'SAMPLING_20_PCT'`, `404` et rejets IDOR `403`.
  - Suite TypeScript (`pnpm turbo run lint typecheck test`) : **9/9 tasks successful** (`@orcia/api-client`: `13` tests, `@orcia/ui`: `107` tests incluant fix `min={warningPct}` dans `FinopsBudgetPolicyModal.tsx`, `@orcia/web`: `128` tests incluant l'audit anti-boutons-muets et les captures silencieuses).
  - Playwright E2E (`e2e/11-screens-smoke-without-server-errors.spec.ts` et `e2e/12-finops-and-audit-provenance.spec.ts`) : **4 passed, 4 skipped (project-scoped desktop/mobile), 0 failed**, `0` erreur SQL `wd.title` / `UndefinedColumn`, mobile `scrollWidth <= innerWidth` vérifié sur `/finops` et `/activity`.
- **Volumétrie & Analyse GitNexus** :
  - Réindexation `npx gitnexus analyze` : `28,854 nodes | 51,381 edges | 441 clusters | 1,325 flows`.
  - Vérification anti-adaptateur-SQL-orphelin (`gitnexus_impact` upstream hors tests) : `impactedCount >= 1` confirmé pour tous les adaptateurs SQL Epic 6.
  - Fichiers scindés sous `< 325` lignes : `_finops_auth_guards.py` (**180 l.**), `_finops_scope_guards.py` (**264 l.**), `_sql_scope_filter.py` (**271 l.**), `sql_finops_dashboard.py` (**264 l.**), `sql_finops_dashboard_processes.py` (**209 l.**), `connector_invoker.py` (**214 l.**), `_connector_invoker_loops.py` (**301 l.**), `sql_finops_accounting.py` (**322 l.**), `_sql_finops_baselines.py` (**190 l.**), `finops_accounting_service.py` (**307 l.**), `_finops_accounting_helpers.py` (**159 l.**), `sql_cognitive_impact.py` (**310 l.**), `sql_cognitive_recommendations.py` (**224 l.**), `_cognitive_budget_guard.py` (**297 l.**), `ai_models_hub.py`, `core_and_lifespan.py`, `contextualHelpCatalog.ts`, `fr.ts`, `en.ts`.

### 3.3 Conformité aux 5 Couches de Tests & Clôture (`AD-17`)
| Couche `AD-17` & Garde-fou | Statut | Preuve / Commande |
| --- | --- | --- |
| **Couche 1 & 2 & 5 — Pyramide Python complète + PG18 + Redis 7.4 + Évals + Sécurité** | ✅ PASS | `.venv/bin/pytest -q tests/unit tests/contract tests/evals tests/security tests/integration --cov=packages/orcia-core --cov-fail-under=90` (**674 passed, 0 failed, 0 skipped**, couverture combinée **91.41%**), `alembic heads` = `20261117_0605` |
| **Couche 3 — Contrats & SDK OpenAPI + Vitest UI** | ✅ PASS | `export_openapi.py --check` (`0-diff`) & `pnpm turbo run lint typecheck test` (**9/9 tasks**) |
| **Couche 4 — E2E Playwright (Desktop & Mobile)** | ✅ PASS | `playwright test e2e/11-... e2e/12-...` (`4 passed, 4 skipped (project-scoped), 0 failed`) |
| **Vérité Terrain Jour 0 & Catalogue `CAP-*` / Sprint** | ✅ PASS | `09_reset_db_first_boot.py --dry-run` (`cleared_tables=66, remaining_users=0`), `pnpm site:sync && pnpm site:check` (`60/60` capacités live), `epic-6: done` (`sprint-status.yaml`), suppression `epic-6-final-review.md` |
