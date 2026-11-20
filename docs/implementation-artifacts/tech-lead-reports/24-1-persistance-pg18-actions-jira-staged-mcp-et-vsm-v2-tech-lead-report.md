# Rapport Tech Lead — Story 24.1 : Persistance PostgreSQL 18 des Actions Jira Staged, Propositions MCP & Workflow VSM v2

- **Story :** `24-1-persistance-pg18-actions-jira-staged-mcp-et-vsm-v2` (Epic 24 — Vague 0 `P0/P1`)
- **Date :** 2026-11-20
- **Statut :** `En attente d'implémentation` (initialisé par `Story 23.8`)
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

> **Statut :** `En attente d'implémentation` — Cette section sera complétée après implémentation, passage des 5 couches `AD-17`, ré-indexation GitNexus (`npx gitnexus analyze` + `gitnexus_detect_changes()`) et exécution de `pnpm site:sync`.

| Fichier / Composant | Action Prévue | Statut |
|---|---|---|
| `infra/migrations/versions/*_jira_staged_and_mcp_pg18.py` | Migration Alembic `Expand` PG18 | `En attente d'implémentation` |
| `infra/scripts/maintenance/_first_boot_reset_guards.py` | Ajout tables mutables Jour 0 | `En attente d'implémentation` |
| `packages/orcia-connectors/.../jira_actions.py` + `_internal/sql_jira_staged_actions.py` | Persistance PG18 & split `< 300` L | `En attente d'implémentation` |
| `packages/orcia-core/.../orchestration/mcp_server.py` | Persistance PG18 `_draft_proposals` | `En attente d'implémentation` |
| `packages/orcia-core/.../workflows/_internal/sql_workflows_v2.py` | Câblage strict `vsm_definitions_v2` + seed | `En attente d'implémentation` |
| `apps/api/src/orcia_api/{dependencies/,routers/jira_and_mcp.py,routers/_workflows_helpers.py}` | Suppression lazy singletons & DI | `En attente d'implémentation` |
| `apps/web/src/features/gates/GatesAdaptiveHumanReviewSection.tsx` | Split `< 300` L & câblage PG18 | `En attente d'implémentation` |
