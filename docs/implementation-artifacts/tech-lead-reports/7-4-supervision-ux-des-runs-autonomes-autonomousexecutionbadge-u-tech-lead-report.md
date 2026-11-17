# Story 7.4 — Supervision UX des Runs Autonomes (`AutonomousExecutionBadge`, `UX-DR17`), Sorties de Secours, Échantillonnage Post-Hoc & Métriques `SM-A1..A3`

- **Date** : 2026-11-17
- **Story / Clé Sprint** : `7-4-supervision-ux-des-runs-autonomes-autonomousexecutionbadge-u` (`Epic 7`)
- **Capacité(s)** : `CAP-201` (`status: partial -> live`, `verification: runtime`), `CAP-202` (`status: live`, `verification: runtime`) — classification : `ux`
- **Auteur / Contexte** : Permettre aux Directeurs de BU, Chefs d'Équipe et Auditeurs SecOps (`Claire UJ-8/UJ-11`, `Marc UJ-5`, `Sophie UJ-6`) de distinguer visuellement tout run ou fiche d'aide exécuté sans intervention humaine (`AutonomousExecutionBadge` Cyan/Cobalt `#0284C7` / `#F0F9FF`, jamais `#6D28D9`), de consulter les exécutions autonomes regroupées par déclencheur dans le tiroir `Notifications` et sur `/processes`, d'actionner en 1 clic l'**Arrêt d'urgence** (`KILL_SWITCH_STOPPED`, effectif à la frontière de `@DBOS.step` `AD-21.5`) et l'**Annulation / rétablissement de la version précédente** (`@v(N-1)` dans `catalog_items` + invalidation cache Redis `< 10 ms` y compris depuis `ShellContextualHelpColumn.tsx`), d'auditer par échantillonnage post-hoc (`10–20 %`) une fraction des runs autonomes, et de suivre les indicateurs `SM-A1..A3` dans l'onglet existant **« Maîtrise humaine & Qualité »** de `/finops` (`0` nouvel onglet, masqué si `0` exécution autonome, isolation stricte de `SM-C1/C2`) avec une microcopy 100 % métier FR/EN exempte de tout jargon technique (`FR-27`, `FR-29`, `AD-19`, `AD-21`, `AD-22`, `UX-DR17`, `Principe D.4`, `SM-C1..C2`, `SM-A1..A3`).
- **Commits associés** : *(en cours — branche `feat/epic-7-observability-autonomous-contracts-and-supervision`)*

---

## 1. Analyse du Besoin & Étude d'Impact Tech Lead (Pré-Implémentation)

### 1.1 Contexte & Problématique
- Les Stories 7.1 et 7.2 ont livré les contrats d'autonomie (`autonomy_contracts`, signature unique `TEAM_LEAD`/`BU_LEAD`/`PLATFORM_ADMIN`) et les déclencheurs événementiels idempotents (`workflow_triggers`, `trigger_webhook_deliveries`, `trigger-dispatcher`, coupe-circuit SSE).
- Toutefois, aucun point de supervision opérationnelle ni aucune sortie de secours humaine ne sont encore exposés dans le portail Direction C :
  - L'opérateur ne peut pas encore distinguer d'un coup d'œil un run ou une fiche d'aide produite automatiquement sous contrat (`UX-DR17`) d'une étape nécessitant une rédaction humaine (`#6D28D9`).
  - L'arrêt d'urgence d'un run autonome en cours (`KILL_SWITCH_STOPPED`) et le rétablissement 1-clic `@v(N-1)` d'un artefact ou d'une fiche `HELP_ARTICLE` générée automatiquement n'existent ni dans le schéma PostgreSQL 18 ni dans l'API ni dans l'UI.
  - Les runs autonomes (`0 min` humaine) risquent de contaminer les contre-métriques interactives `SM-C1` (validations expéditives) et `SM-C2` (ratio cadrage actif) s'ils ne sont pas explicitement isolés (`execution_regime != 'AUTONOMOUS_CONTRACT'`).
  - Aucun mécanisme d'échantillonnage post-hoc (`10–20 %`) ni de calcul `Decimal` des 3 indicateurs d'autonomie (`SM-A1`, `SM-A2` avec alerte `>= 1 %`, `SM-A3`) n'est encore persisté ni affiché dans `/finops` (« Maîtrise humaine & Qualité »).
- **Contraintes spécifiques `ARCHITECTURE-SPINE.md` & `GEMINI.md`** :
  - Chaînage strict Alembic depuis `head = "20261117_0702"` en préservant **100 %** des valeurs `CHECK` existantes sur `workflow_runs.status` et `domain_events_outbox.event_type`, ainsi que la mise à jour de `09_reset_db_first_boot.py`.
  - Frontières `AD-19` (`lint-imports` 5 contrats conservés), zéro import de framework dans `orcia_kernel`, zéro client HTTP/DB synchrone dans les routeurs FastAPI (`TID251`), OpenAPI `0-diff`, et stricte séparation `@orcia/ui` vs `apps/web` (`0` hex hors `tokens.css`, `<OrciaIcon />`, `0` jargon interne, `0` bouton muet / `.catch(() => undefined)`).

### 1.2 Exploration, Analyse d'Impact GitNexus, Factorisation & Dette Technique
- **Analyse d'Impact GitNexus (`gitnexus_query`, `gitnexus_context`, `gitnexus_impact` sur `repo: "/home/romain/Documents/Projects/ORCIA"`)** :
  - `ProcessesHubPage` (`apps/web/src/features/processes/ProcessesHubPage.tsx`, `438` l.) : `risk: LOW`, `impactedCount: 1` (`d=1`: `processesRoute.component` dans `apps/web/src/router.tsx`).
  - `InteractiveRunDrawer` (`apps/web/src/features/processes/execution/InteractiveRunDrawer.tsx`, `599` l.) : `risk: LOW`, `impactedCount: 4` (`d=1`: `ProcessesHubPage`, `WorkflowFiveBlocksCanvas`; `d=2`: `processesRoute.component`, `processesStudioRoute.component`).
  - `FourZoneNotificationsDrawer` (`packages/ui/src/primitives/FourZoneNotificationsDrawer.tsx`, `173` l.) : `risk: LOW`, `impactedCount: 3` (`d=1`: `FourZoneDirectionCShell`; `d=2`: `InnerShellContainer`; `d=3`: `ShellContainer`).
  - `ShellContextualHelpColumn` (`apps/web/src/components/ShellContextualHelpColumn.tsx`, `40` l.) : `risk: LOW`, `impactedCount: 3` (`d=1`: `InnerShellContainer`; `d=2`: `ShellContainer`; `d=3`: `RootLayoutComponent`).
  - `FinopsHumanMasteryTab` (`packages/ui/src/primitives/finops/FinopsHumanMasteryTab.tsx`, `337` l.) : `risk: HIGH`, `impactedCount: 3` (`d=1`: `FinopsGovernanceDashboardView`; `d=2`: `FinopsFeaturePanel`; `d=3`: `ModuleWorkspaceView`).
  - `get_cognitive_impact` (`apps/api/src/orcia_api/routers/finops_cognitive.py`, `148` l.) : `gitnexus_context` montre ses appels sortants vers `resolve_finops_read_scope` et `validate_uuid` et sa participation à 5 flux de contrôle d'accès (`Has_org_unit`, `Get_ancestor_org_unit_ids`, `_user_is_member_of_node`, `_user_leads_node`, `Get_workspace`).
  - `sql_cognitive_impact.py` (`packages/orcia-core/src/orcia_core/audit_finops/_internal/sql_cognitive_impact.py`, `310` l.) : porte `fetch_cognitive_mastery_overview_sql` et `fetch_workflow_cognitive_breakdown_sql` qui doivent filtrer `wr.execution_regime != 'AUTONOMOUS_CONTRACT'` afin d'isoler `SM-C1` et `SM-C2`.
  - `portal_and_help.py` (`apps/api/src/orcia_api/routers/portal_and_help.py`, `322` l.) : `resolve_contextual_help` et `rollback_contextual_help` participent aux flux `Resolve_contextual_help -> Build_help_redis_cache_key` et `Rollback_contextual_help` sur `ContextualHelpResolutionService`.
- **Exploration & Chiffres Clés (Volumétrie des Fichiers & Base de Données)** :
  - `InteractiveRunDrawer.tsx` (`599` l.), `ProcessesHubPage.tsx` (`438` l.), `FinopsHumanMasteryTab.tsx` (`337` l.) et `sql_cognitive_impact.py` (`310` l.) atteignent ou dépassent le seuil de `300–400` lignes.
  - Les contraintes existantes dans `20261117_0701` et `20261117_0702` définissent `ck_workflow_runs_status` (12 statuts dont `PAUSED_AUTONOMOUS_ESCALATION`, `COMMITTED_AUTONOMOUS`, `ROLLED_BACK`) et `domain_events_outbox_event_type_check` (26 types d'événements dont `WorkflowPublished`, `TriggerCircuitOpened`, `AutonomousEscalated`).
- **Opportunités de Factorisation & Résorption de Dette Technique Naissante** :
  - **Extraction modulaire systématique (`< 350` l./fichier)** :
    - Backend : isoler la logique post-hoc et sorties de secours dans `packages/orcia-core/src/orcia_core/audit_finops/post_hoc_audit.py` (`< 280` l.) et `packages/orcia-core/src/orcia_core/audit_finops/_internal/sql_autonomous_metrics.py` (`< 280` l.), ainsi que le service de supervision/sorties de secours d'exécution dans `packages/orcia-core/src/orcia_core/orchestration/autonomous_supervision.py` (`< 280` l.) et `packages/orcia-core/src/orcia_core/orchestration/_internal/sql_autonomous_supervision.py` (`< 280` l.), et un routeur dédié `apps/api/src/orcia_api/routers/autonomous_supervision.py` (`< 280` l.).
    - Frontend `@orcia/ui` : créer `AutonomousExecutionBadge.tsx` (`< 220` l.) et `FinopsAutonomousGovernanceSection.tsx` (`< 280` l.) pour ne pas gonfler `FinopsHumanMasteryTab.tsx`.
    - Frontend `apps/web` : créer `AutonomousRunsSupervisionPanel.tsx` (`< 280` l.) et `useAutonomousRunsSupervision.ts` (`< 200` l.) raccordés à `ProcessesHubPage.tsx` (allégé sous `350` l. par extraction du bloc VSM/cartes si nécessaire), et extraire la section regroupée des notifications autonomes dans `FourZoneAutonomousNotificationsGroup.tsx` (`< 180` l.) pour garder `FourZoneNotificationsDrawer.tsx` concis.
    - Réutilisation `DRY` des gardes existants `enforce_scope_level_mutation` / `enforce_observer_headers_guard` (`_finops_auth_guards.py`), de `SqlAuditLedgerService`, de `InMemorySseBrokerAdapter` / `SseBroadcastPort`, et de `ContextualHelpResolutionService` (`rollback_to_previous_version` + invalidation `help:route:*`).

---

## 2. Plan d'Implémentation

### 2.1 Schéma de Données & Migrations Alembic (`infra/migrations/versions/20261117_0704_story_7_4_post_hoc_audit_and_kill_switch.py`)
- **`down_revision = "20261117_0702"`** (SQL brut réversible dans `upgrade()` et `downgrade()`):
  1. Création de la table `autonomous_post_hoc_audits` :
     - `id UUID PRIMARY KEY` (`UUIDv7`)
     - `run_id UUID NOT NULL UNIQUE REFERENCES workflow_runs(id) ON DELETE CASCADE`
     - `workspace_id UUID NOT NULL`
     - `contract_id UUID NOT NULL REFERENCES autonomy_contracts(id) ON DELETE CASCADE`
     - `review_status VARCHAR(48) NOT NULL DEFAULT 'PENDING_SAMPLE' CHECK (review_status IN ('PENDING_SAMPLE', 'VALIDATED', 'INVALIDATED_ROLLED_BACK'))`
     - `reviewer_user_id UUID NULL`
     - `review_comment TEXT NULL`
     - `sampled_at TIMESTAMPTZ NOT NULL DEFAULT NOW()`
     - `reviewed_at TIMESTAMPTZ NULL`
     - Index `idx_post_hoc_audits_ws_status ON autonomous_post_hoc_audits (workspace_id, review_status)`.
  2. Extension de `workflow_runs.status` `CHECK` (`ck_workflow_runs_status`) en préservant 100 % des 12 statuts existants (`20261117_0701`) et en ajoutant `'KILL_SWITCH_STOPPED'`.
  3. Extension de `domain_events_outbox.event_type` `CHECK` (`domain_events_outbox_event_type_check`) en préservant 100 % des 26 types existants (`20261117_0702`) et en ajoutant `'PostHocSampleSelected'`, `'KillSwitchActivated'`, `'AutonomousArtifactRolledBack'`.
- Mise à jour de `ORDERED_MUTABLE_TABLES_TO_CLEAR` dans `infra/scripts/maintenance/09_reset_db_first_boot.py` en insérant `"autonomous_post_hoc_audits"` avant `"workflow_runs"` et `"autonomy_contracts"`.

### 2.2 Noyau Métier Hexagonal, Orchestration & Workers (`packages/orcia-core/`, `packages/orcia-connectors/`)
- **Événements noyau (`orcia_core.kernel._governance_events` & `events.py`)** :
  - Ajout des 3 `DomainEvent` immuables : `PostHocSampleSelected`, `KillSwitchActivated`, `AutonomousArtifactRolledBack`.
  - Enregistrement dans `AUDITABLE_EVENT_TYPES` + `_build_event_summary` (`audit_finops/outbox_subscriber.py`) avec résumés métier sans secret ni jargon.
- **Échantillonnage post-hoc & Métriques `SM-A1..A3` (`orcia_core/audit_finops/post_hoc_audit.py`, `_internal/sql_autonomous_metrics.py`)** :
  - Échantillonnage stratifié/déterministe (`10–20 %`, défaut `0.15` selon `contract.post_hoc_sampling_rate`) sur tout run clôturé en `COMMITTED_AUTONOMOUS` : insertion idempotente (`ON CONFLICT (run_id) DO NOTHING`) dans `autonomous_post_hoc_audits`, publication de `PostHocSampleSelected` dans `domain_events_outbox` + `audit_ledger` et création d'une notification prioritaire `POST_HOC_AUDIT_SAMPLE`.
  - Calcul strict en `Decimal` / `NUMERIC(12,6)` :
    - `SM-A1` (`autonomous_escalation_rate`) = `PAUSED_AUTONOMOUS_ESCALATION / total_autonomous_runs`.
    - `SM-A2` (`post_hoc_invalidation_rate`) = `INVALIDATED_ROLLED_BACK / sampled_or_reviewed_runs` (alerte `invalidation_alert = True` dès `SM-A2 >= Decimal("0.01")`).
    - `SM-A3` (`avg_autonomous_cost_usd`, `avg_ttm_gain_minutes`).
- **Isolation stricte `SM-C1` et `SM-C2` (`sql_cognitive_impact.py`, `cognitive_impact_service.py`)** :
  - Exclusion explicite des runs `execution_regime = 'AUTONOMOUS_CONTRACT'` dans les requêtes SQL d'agrégation `SM-C1` (validations expéditives) et `SM-C2` (ratio cadrage actif) afin de garantir que les runs autonomes (`0 min` humaine) ne faussent jamais `SM-C1` ni `SM-C2`.
- **Sorties de secours & Frontière `@DBOS.step` (`orcia_core/orchestration/autonomous_supervision.py`, `_internal/sql_autonomous_supervision.py`, `orcia_connectors/autonomous_runner.py`, `orcia_core/orchestration/_internal/dbos_engine.py`)** :
  - Vérification de l'arrêt d'urgence (`KILL_SWITCH_STOPPED`) à chaque frontière de `@DBOS.step` (`AD-21.5`) dans `execute_autonomous_contract_run` et `_orcia_durable_run_workflow`.
  - `emergency_stop(run_id, actor, suspend_trigger=...)` : passe le run à `KILL_SWITCH_STOPPED`, suspend optionnellement le déclencheur associé (`CIRCUIT_OPEN`), émet `KillSwitchActivated` (`domain_events_outbox` + `audit_ledger`) et diffuse l'événement SSE `< 500 ms` sur `channel:workspace:{ws_id}`.
  - `invalidate_and_restore(run_id, actor, comment, help_resource_id=...)` : pour une fiche `HELP_ARTICLE`, restaure `@v(N-1)` dans `catalog_items` et invalide immédiatement le cache Redis `help:route:*` (`< 10 ms`) ; passe l'échantillon/run à `INVALIDATED_ROLLED_BACK` / `ROLLED_BACK`, trace dans `audit_ledger`, publie `AutonomousArtifactRolledBack` dans `domain_events_outbox` + SSE `< 500 ms`.
  - `review_post_hoc_sample(run_id, actor, decision, comment)` : valide (`VALIDATED`) ou invalide avec rétablissement `@v(N-1)` (`INVALIDATED_ROLLED_BACK`).

### 2.3 Couche Backend API, Sécurité & Contrats (`apps/api/`, `packages/api-client/`)
- **Schémas Pydantic v2** :
  - Enrichissement de `apps/api/src/orcia_api/schemas/finops.py` (`AutonomousGovernanceMetricsSchema`, champ `autonomous_governance` optionnel sur `CognitiveImpactDashboardResponse`).
  - Nouveau module `apps/api/src/orcia_api/schemas/autonomous_supervision.py` enregistré dans `SCHEMA_DOMAIN_MODULES` de `scripts/export_openapi.py`.
  - Enrichissement de `ContextualHelpResolveResponse` (`apps/api/src/orcia_api/schemas/catalog.py`) et `portal_and_help.py` avec les métadonnées optionnelles `is_autonomous_generated`, `autonomous_run_id`, `contract_label`, `trigger_label`, `previous_version_available`.
- **Endpoints FastAPI** (`apps/api/src/orcia_api/routers/autonomous_supervision.py` & `finops_cognitive.py`) :
  - Protégés par `resolve_request_user`, `resolve_finops_read_scope` / `enforce_scope_level_mutation` et garde `READ_ONLY_OBSERVER` (`HTTP 403 ERR_OBSERVER_MODE_READ_ONLY`) :
    - `GET /api/v1/workspaces/{workspace_id}/autonomous-runs`
    - `POST /api/v1/runs/{run_id}/emergency-stop`
    - `POST /api/v1/runs/{run_id}/invalidate-and-restore`
    - `POST /api/v1/runs/{run_id}/post-hoc-review`
- **SDK `@orcia/api-client`** :
  - Régénération OpenAPI 3.1 via `.venv/bin/python scripts/export_openapi.py` (`--check` `0-diff`), ajout du client typé `packages/api-client/src/domains/autonomousSupervision.ts` et export dans `packages/api-client/src/index.ts`.

### 2.4 Interface Utilisateur & Expérience (`packages/ui/`, `apps/web/`)
- **Tokens Direction C (`packages/ui/src/styles/tokens.css`)** :
  - Ajout de `--color-autonomous-badge-bg: #F0F9FF`, `--color-autonomous-badge-fg: #0284C7`, `--color-autonomous-badge-border: #BAE6FD` (zéro `#hex` hors `tokens.css`, zéro `--color-human-led-violet` sur les badges d'autonomie).
- **Primitives `@orcia/ui`** :
  - `AutonomousExecutionBadge.tsx` (`< 220` l.) : badge Cyan/Cobalt (`UX-DR17`), libellé métier *« Automatisé sous contrat »*, mention du déclencheur/contrat, boutons optionnels *« Arrêt d'urgence »* (`onEmergencyStop`) et *« Annuler et rétablir la version précédente »* (`onInvalidateAndRestore`), exclusivement via `<OrciaIcon />`.
  - `FinopsAutonomousGovernanceSection.tsx` (`< 280` l.) : monté **à l'intérieur** de `FinopsHumanMasteryTab.tsx` (`0` nouvel onglet dans `/finops`), masqué si `totalAutonomousRuns === 0`, affichant les 3 indicateurs d'autonomie, l'alerte visuelle si taux d'annulation `>= 1 %`, et la file des dossiers tirés au sort pour contrôle qualité post-hoc (`Valider` / `Annuler et rétablir la version précédente`), avec `<ContextualInfoTriggerButton />`.
  - `FourZoneNotificationsDrawer.tsx` + `FourZoneAutonomousNotificationsGroup.tsx` : regroupement des exécutions autonomes nominales par déclencheur dans un bloc replié par défaut (`<details>` / bouton dépliable), tandis que les escalades, déclencheurs suspendus et tirages de contrôle qualité remontent en priorité.
- **Montage `apps/web`** :
  - `/processes` : `AutonomousRunsSupervisionPanel.tsx` (`< 280` l.) + `useAutonomousRunsSupervision.ts` dans `ProcessesHubPage.tsx` (avec allègement de `ProcessesHubPage.tsx` sous `350` l.) et badge `UX-DR17` sur les fiches autonomes.
  - `ShellContextualHelpColumn.tsx` + `ContextualHelpColumnAndCenter.tsx` : affichage du `AutonomousExecutionBadge` lorsque la fiche active a été générée automatiquement (`isAutonomousGenerated`), avec bouton 1-clic *« Annuler et rétablir la version précédente »* invalidant le cache et rafraîchissant la fiche (survie au `F5`).
  - `apps/web/src/i18n/locales/{fr,en}.ts` & `autonomous_supervision_labels.ts` : microcopy 100 % métier FR/EN, zéro jargon technique (`Kill-Switch`, `Rollback`, `Tie-Break`, `Service Principal`, `CIRCUIT_OPEN`, `POST_HOC_AUDIT_SAMPLE`, `AUTONOMOUS_CONTRACT`, `SM-A1..A3`, `DBOS`, `PostgreSQL`, `Redis`, `Outbox` bannis côté UI).

### 2.5 Analyse d'Impact sur la Pyramide des Tests (`AD-17` — Couches 1 à 5 + Sécurité)
- **Couche 1a (`tests/unit/test_story_7_4_post_hoc_audit_and_autonomous_metrics.py`)** : calculs `Decimal` `SM-A1..A3`, seuil d'alerte `>= 1 %`, isolation `SM-C1/C2`, échantillonnage `10–20 %`, arrêt d'urgence à frontière de step, rétablissement `@v(N-1)` + invalidation Redis `< 10 ms`.
- **Couche 1b (`apps/web/src/__tests__/story-7-4-autonomous-supervision-and-finops.test.tsx`)** : rendu Cyan/Cobalt `AutonomousExecutionBadge` (`0` violet), regroupement tiroir Notifications, masquage à vide `/finops`, arrêt d'urgence / rétablissement + survie au `F5` (`unmount()` -> `render()`), passage de `zero-dead-buttons-and-silent-catches-audit.test.tsx`, `design-system-look-and-feel-isolation.test.tsx`, `icon-registry-centralization.test.tsx`, et test explicite d'absence de tout jargon banni dans les dictionnaires FR/EN.
- **Couche 2 (`tests/integration/api/test_story_7_4_supervision_rollback_postgres18.py`)** : réversibilité migration `20261117_0704`, appels HTTP FastAPI `AsyncClient` -> PostgreSQL 18 + `SELECT` direct vérifiant `KILL_SWITCH_STOPPED`, `autonomous_post_hoc_audits`, rétablissement `@v(N-1)` dans `catalog_items` + Redis réel `testcontainers`, isolation `SM-C1/C2` vs `SM-A1..A3`, et exécution réelle de `pnpm db:reset`.
- **Couche 3 (Contrats)** : `export_openapi.py --check` (`0-diff`), `lint-imports`, `mypy --strict`, `ruff`.
- **Couche Sécurité (`tests/security/test_story_7_4_observer_and_rbac_guards.py`)** : rejet `HTTP 403 ERR_OBSERVER_MODE_READ_ONLY` sur `/emergency-stop`, `/invalidate-and-restore`, `/post-hoc-review` et contrôle périmètre.
- **Couche 5 (`apps/web/e2e/13-epic-7-autonomous-governance-and-supervision.spec.ts`)** : Desktop `1440×900` + Mobile `390×844` couvrant Studio V2 (contrat + déclencheur + exécution autonome), badge dans `/processes` et tiroir `Notifications`, arrêt d'urgence / rétablissement `@v(N-1)`, onglet `/finops` « Maîtrise humaine & Qualité ».

---

## 3. Bilan des Modifications & Résultats (Post-Implémentation)

### 3.1 Tableau des Fichiers Créés & Modifiés

| Couche | Fichiers Créés | Fichiers Modifiés |
| :--- | :--- | :--- |
| **Alembic & Maintenance** | `infra/migrations/versions/20261117_0704_story_7_4_post_hoc_audit_and_kill_switch.py` | `infra/scripts/maintenance/09_reset_db_first_boot.py` |
| **Kernel & Noyau Hexagonal (`orcia_core` / `orcia_connectors`)** | `packages/orcia-core/src/orcia_core/kernel/_autonomous_supervision_events.py`, `packages/orcia-core/src/orcia_core/audit_finops/post_hoc_audit_models.py`, `packages/orcia-core/src/orcia_core/audit_finops/post_hoc_audit.py`, `packages/orcia-core/src/orcia_core/audit_finops/_internal/sql_autonomous_metrics.py`, `packages/orcia-core/src/orcia_core/orchestration/_autonomous_supervision_models.py`, `packages/orcia-core/src/orcia_core/orchestration/autonomous_supervision.py`, `packages/orcia-core/src/orcia_core/orchestration/_internal/sql_autonomous_supervision.py`, `packages/orcia-core/src/orcia_core/orchestration/_internal/_sql_autonomous_rollback.py` | `packages/orcia-core/src/orcia_core/kernel/events.py`, `packages/orcia-core/src/orcia_core/audit_finops/__init__.py`, `packages/orcia-core/src/orcia_core/audit_finops/cognitive_impact_models.py`, `packages/orcia-core/src/orcia_core/audit_finops/cognitive_impact_service.py`, `packages/orcia-core/src/orcia_core/audit_finops/_internal/sql_cognitive_impact.py`, `packages/orcia-core/src/orcia_core/audit_finops/outbox_subscriber.py`, `packages/orcia-core/src/orcia_core/catalog/contextual_help.py`, `packages/orcia-core/src/orcia_core/orchestration/__init__.py`, `packages/orcia-core/src/orcia_core/orchestration/models.py`, `packages/orcia-core/src/orcia_core/orchestration/_internal/dbos_engine.py`, `packages/orcia-connectors/src/orcia_connectors/autonomous_runner.py` |
| **Backend FastAPI & SDK (`apps/api`, `@orcia/api-client`)** | `apps/api/src/orcia_api/schemas/autonomous_supervision.py`, `apps/api/src/orcia_api/dependencies/autonomous_supervision.py`, `apps/api/src/orcia_api/routers/autonomous_supervision.py`, `packages/api-client/src/domains/autonomousSupervision.ts`, `packages/api-client/src/generated/autonomous_supervision.ts` | `apps/api/src/orcia_api/main.py`, `apps/api/src/orcia_api/dependencies/__init__.py`, `apps/api/src/orcia_api/dependencies/orchestration_and_settings.py`, `apps/api/src/orcia_api/routers/_finops_scope_guards.py`, `apps/api/src/orcia_api/routers/autonomy_contracts.py`, `apps/api/src/orcia_api/routers/workflow_triggers.py`, `apps/api/src/orcia_api/routers/finops_cognitive.py`, `apps/api/src/orcia_api/routers/portal_and_help.py`, `apps/api/src/orcia_api/schemas/{autonomy_contracts,catalog,finops}.py`, `scripts/export_openapi.py`, `packages/api-client/{openapi.json,src/index.ts,src/domains/finops.ts,src/generated/finops.ts,src/generated/schema.ts}` |
| **Design System & SPA (`@orcia/ui`, `@orcia/web`)** | `packages/ui/src/primitives/AutonomousExecutionBadge.tsx`, `packages/ui/src/primitives/FourZoneAutonomousNotificationsGroup.tsx`, `packages/ui/src/primitives/finops/FinopsAutonomousGovernanceSection.tsx`, `packages/ui/src/primitives/finops/FinopsHumanMasteryWorkflowsTable.tsx`, `apps/web/src/i18n/locales/autonomous_supervision_labels.ts`, `apps/web/src/components/useShellAutonomousSupervision.ts`, `apps/web/src/features/processes/AutonomousRunsSupervisionPanel.tsx`, `apps/web/src/features/processes/ProcessesValueStreamOverviewCard.tsx` | `packages/ui/src/styles/tokens.css`, `packages/ui/src/index.ts`, `packages/ui/src/primitives/{ContextualHelpColumnAndCenter,FourZoneDirectionCShell,FourZoneNotificationsDrawer}.tsx`, `packages/ui/src/primitives/finops/{FinopsGovernanceDashboardView,FinopsHumanMasteryTab}.tsx`, `apps/web/src/i18n/{types.ts,locales/fr.ts,locales/en.ts,locales/shell_and_search_labels.ts}`, `apps/web/src/components/{ShellContainer,ShellContextualHelpColumn,_contextualHelpSections,shellScopeOptions,useWorkspaceEventsSse}.ts*`, `apps/web/src/features/finops/{finopsMappers.ts,index.tsx}`, `apps/web/src/features/processes/ProcessesHubPage.tsx` |
| **Tests & Gouvernance (`AD-17`, `site:sync`)** | `tests/unit/test_story_7_4_post_hoc_audit_and_autonomous_metrics.py`, `tests/security/test_story_7_4_observer_and_rbac_guards.py`, `tests/integration/api/test_story_7_4_supervision_rollback_postgres18.py`, `apps/web/src/__tests__/vitestAutonomousSupervisionMockHandlers.ts`, `apps/web/src/__tests__/story-7-4-autonomous-supervision-and-f5.test.tsx`, `apps/web/e2e/13-epic-7-autonomous-governance-and-supervision.spec.ts` | `apps/web/src/__tests__/{vitest.setup.ts,zero-dead-buttons-and-silent-catches-audit.test.tsx}`, `docs/implementation-artifacts/sprint-status.yaml`, `docs/product/capabilities.yaml`, `docs/implementation-artifacts/tech-lead-reports/README.md`, `apps/web/src/generated/orciaSiteManifest.ts`, `docs/site-catalog/index.html` |

### 3.2 Découpage Volumétrique & Factorisation Réalisés
- **`autonomous_supervision.py`** : extraction des projections, construction d'items et résolution de contexte dans `_autonomous_supervision_models.py` (`196` l.), maintenant `autonomous_supervision.py` sous `400` l.
- **`FinopsHumanMasteryTab.tsx`** : extraction du tableau des workflows dans `FinopsHumanMasteryWorkflowsTable.tsx` (`105` l.), ramenant `FinopsHumanMasteryTab.tsx` à `299` l.
- **`ProcessesHubPage.tsx`** : extraction de `ProcessesValueStreamOverviewCard.tsx` et `AutonomousRunsSupervisionPanel.tsx` (`210` l.), ramenant `ProcessesHubPage.tsx` à `333` l.
- **`ShellContainer.tsx`** : extraction du hook `useShellAutonomousSupervision.ts` (`62` l.) et normalisation du helper `resolve_workspace_uuid_or_setup_key` partagé entre `autonomy_contracts.py`, `workflow_triggers.py` et `autonomous_supervision.py` (résolvant également en amont la compatibilité PostgreSQL 18 des clés d'espace `ws-*` issues du Studio V2 / E2E).

### 3.3 Validation Pyramide des Tests (`AD-17`) & Métriques de Qualité
- **Qualité Statique & Contrats** : `.venv/bin/ruff check .` (`All checks passed!`), `.venv/bin/ruff format --check .` (`999 files already formatted`), `.venv/bin/mypy --strict packages/orcia-core packages/orcia-connectors apps/api apps/worker` (`0` erreur sur `446` fichiers), `.venv/bin/lint-imports` (`5/5` contrats `AD-19`/`AD-20` respectés), `.venv/bin/python scripts/export_openapi.py --check` (`0-diff`), `.venv/bin/detect-secrets-hook` (`0` alerte), fins de fichier `\n` (`0` manquant).
- **Couche 1a & Couverture Combinée Story 7.4** : `.venv/bin/pytest tests/unit tests/contract tests/conformance tests/security -q` **100 % vert** ; couverture combinée (`unit` + `security` + `integration PG18`) des 12 modules Story 7.4 à **`91 %`** (`>= 90 %`, dont `100 %` sur `post_hoc_audit_models.py`, `_autonomous_supervision_events.py`, `sql_cognitive_impact.py`, `schemas/autonomous_supervision.py` ; `96 %` sur `_autonomous_supervision_models.py` ; `93 %` sur `autonomous_supervision.py` ; `92 %` sur `routers/autonomous_supervision.py`).
- **Couche 1b (`@orcia/ui`, `@orcia/api-client`, `@orcia/web`)** : `pnpm turbo run lint typecheck test` **`9/9` tâches vertes** (`25/25` fichiers `@orcia/ui`, `2/2` `@orcia/api-client`, `32/32` fichiers / `135/135` tests `@orcia/web`, incluant `story-7-4-autonomous-supervision-and-f5.test.tsx`, `zero-dead-buttons-and-silent-catches-audit.test.tsx`, `design-system-look-and-feel-isolation.test.tsx`, `icon-registry-centralization.test.tsx`, survie `F5`, zéro `#hex` et zéro jargon banni).
- **Couche 2 (`testcontainers` PG18 + Redis 7.4)** : `tests/integration/api/test_story_7_4_supervision_rollback_postgres18.py` **vert** (`alembic upgrade head -> downgrade -1 -> upgrade head`, persistance `KILL_SWITCH_STOPPED`, suspend `CIRCUIT_OPEN`, rollback `@v(N-1)` sur `catalog_items`, invalidation Redis réelle `< 10 ms`, isolation `SM-C1/C2` vs `SM-A1..A3` et reset `09_reset_db_first_boot.py`).
- **Couche Sécurité** : `tests/security/test_story_7_4_observer_and_rbac_guards.py` **vert** (`HTTP 403 ERR_OBSERVER_MODE_READ_ONLY` + contrôle périmètre).
- **Couche 5 (Playwright E2E)** : `e2e/13-epic-7-autonomous-governance-and-supervision.spec.ts` **vert (`2 passed`, `50.1s`)** sur Desktop `1440×900` et Mobile `390×844`, plus `pnpm db:reset` réel (`cleared_tables=66, remaining_users=0`).
- **Registre Capacités & GitNexus** : `CAP-201` promu `status: live`, `verification: runtime` ; `pnpm site:sync && pnpm site:check` **`62/62` live**, `0` sans test ; `npx gitnexus@latest analyze --index-only && detect-changes` (`30,823` nœuds, `53,379` arêtes, `54` fichiers, `184` symboles, `99` flux impactés, `0` blocage non maîtrisé).
