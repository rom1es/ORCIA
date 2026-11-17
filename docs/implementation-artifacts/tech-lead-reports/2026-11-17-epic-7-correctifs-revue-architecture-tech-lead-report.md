# 2026-11-17 — Correctifs Revue d'Architecture Epic 7 (`5 BLOCKING`, `5 MAJOR`, `3 MINOR`)

- **Date** : 2026-11-17
- **Story / Clé Sprint** : `2026-11-17-epic-7-correctifs-revue-architecture` (`Epic 7` / `Ajustement Transverse`)
- **Capacité(s)** : `CAP-201, CAP-202` — classification : `hygiène`
- **Auteur / Contexte** : Résolution intégrale des 13 findings (`5 BLOCKING`, `5 MAJOR`, `3 MINOR`) issus de la revue d'architecture finale `VALIDATE` (`epic-7-architect-validate-review.md`) couvrant les Stories `7.0a`, `7.0b`, `7.0c`, `7.1`, `7.2` et `7.4` (`AD-3`, `AD-6`, `AD-17`, `AD-18`, `AD-19`, `AD-21`, `AD-23`, `NFR-SEC-4`).
- **Commits associés** : *(en attente de validation finale)*

---

## 1. Analyse du Besoin & Étude d'Impact Tech Lead (Pré-Implémentation)

### 1.1 Contexte & Problématique
La revue d'architecture `VALIDATE` d'Epic 7 a identifié 13 défauts (`5 BLOCKING`, `5 MAJOR`, `3 MINOR`) qui empêchent le passage d'`epic-7` à `done` :
1. **`BLOCKING-01` (Composition Root PG18/Redis)** : `app_lifespan` / `initialize_app_services` conditionnaient `db_engine` à `ORCIA_ENABLE_PG_SESSION_MAKER == "1"` (absent des manifests/scripts) et n'initialisaient jamais `app.state.redis_client` ; les getters DI Epic 7 n'appelaient pas `get_or_create_shared_db_engine(request)`.
2. **`BLOCKING-02` (RBAC / IDOR & Confinement)** : les routes `GET`/`POST`/`PATCH`/`DELETE` de `autonomy_contracts.py` et `workflow_triggers.py` omettaient `resolve_finops_read_scope` et `enforce_scope_mutation_guard` ; `autonomous_supervision.py` court-circuitait la garde quand le workspace manquait en RAM ; `AutonomyContractService.sign_contract` acceptait `body.scope_path` client et ne vérifiait pas l'habilitation du signataire sur la hiérarchie cible ; `_autonomy_confinement.py` dispensait tout `SERVICE_PRINCIPAL` ayant `PLATFORM_ADMIN` de son périmètre `team_ids`.
3. **`BLOCKING-03` (Chaîne Autonome, Outbox & Arrêt d'Urgence)** : `workflow_triggers.py` et `trigger_dispatcher_daemon.py` appelaient `dispatch_trigger(..., execution_fn=None)` (runs figés à `INITIALIZED`) ; `_sql_workflow_triggers_queries.py` et `sql_autonomy_contracts.py` inséraient `domain_events_outbox` en `'PUBLISHED'` (jamais relayé par `claim_and_relay_pending_batch` filtrant `'PENDING'`) ; `_triggers_schedulers.py` envoyait `x-orcia-origin-run-id` sur `WorkflowPublished` (faux Self-Trigger) ; `autonomous_runner.py` / `dbos_engine.py` devaient renforcer la vérification `KILL_SWITCH_STOPPED` aux frontières de signature et d'exécution.
4. **`BLOCKING-04` (Normalisation `workspace_id`)** : `POST /api/v1/workflows/{workflow_id}/runs/autonomous` passait le `workspace_id` brut au lieu de `ws_uuid`.
5. **`BLOCKING-05` (Démon `trigger-dispatcher` & `LogSink`)** : le démon n'injectait ni `RedisTriggerIdempotencyLockAdapter` avec Redis, ni broker SSE partagé Redis Pub/Sub, ni `httpx.AsyncClient` partagé, ni `SecretProviderPort` (dans l'API et le démon), ni `session_factory`/`redis_client` dans `HelpGenerationAndHotAttachmentService`.
6. **`MAJOR-01` (Synchronisation PG/Redis Supervision & Aide)** : omission de `help_resource_id`/`previous_version_available` en SQL, repli `self._runs` quand PG renvoie `[]`, `redis.delete` non awaité, `LIKE '%' || c.workflow_id` non ancré, `ContextualHelpResolutionService` uniquement en RAM, pack `"orcia-core"` vs `"core"` et `isAdmin={true}` en dur dans `ShellContextualHelpColumn.tsx`.
7. **`MAJOR-02` (Concurrence ECS & Rotation Logs)** : `_REGISTERED_SECRET_VALUES` sans `threading.Lock`, et `RotatingFileHandler` fermé immédiatement dans `scripts/manage.py`.
8. **`MAJOR-03` (`secret-template.yaml` & `sandbox_daemon.py`)** : `secret-template.yaml` inclus dans `kustomization.yaml` neutralisait `ORCIA_SANDBOX_INTERNAL_TOKEN`, et `sandbox_daemon.py` autorisait un token vide hors `local`/`test`.
9. **`MAJOR-04` (E2E `13-epic-7` & Studio V2 Publish)** : `WorkflowFiveBlocksCanvas.tsx` publiait uniquement dans `localStorage`, et `13-epic-7` utilisait `if ((await stopBtns.count()) > 0)`.
10. **`MAJOR-05` (Volumétrie `> 400` L)** : 6 fichiers de production à découper `< 350` lignes.
11. **`MINOR-01`** : oracle `404` avant `401` HMAC sur `/api/v1/triggers/alerts` + erreur 500 possible au déchiffrement.
12. **`MINOR-02`** : mapping `catalog:write` vers `"update"` dans `_autonomy_confinement.py` + nouvelle migration `20261117_0705` ajoutant `fk_autonomy_contracts_workspace` (`ON DELETE CASCADE`).
13. **`MINOR-03`** : maintien de `epic-7: in-progress` jusqu'à passage de toutes les portes `AD-17`.

### 1.2 Exploration, Analyse d'Impact GitNexus, Factorisation & Dette Technique
- **Analyse d'Impact GitNexus (`gitnexus_context`, `gitnexus_impact` sur `/home/romain/Documents/Projects/ORCIA`)** :
  - `initialize_app_services` : point d'entrée unique du Composition Root (`apps/api/src/orcia_api/main.py` et tous les getters `apps/api/src/orcia_api/dependencies/*`).
  - `TriggerDispatcherService.dispatch_trigger` (`impactedCount=8`, `risk=LOW`, `epistemic=exact`) : appelé par `run_cron_trigger_evaluation`, `run_log_sink_trigger_scan`, `run_workflow_published_optin_help` (`_triggers_schedulers.py`), `save_or_fork_workflow_v2` (`workflows.py`), `run_trigger_dispatcher_cycle` (`trigger_dispatcher_daemon.py`) et les routes `workflow_triggers.py`.
  - `AutonomousSupervisionService.is_run_stopped` (`impactedCount=0`, `risk=UNKNOWN` — lié par callback dans `autonomy_contracts.py` et les tests) : doit être câblé au travers du factory d'exécution autonome partagé entre API et worker.
  - `AutonomyContractService` : consommé par `sql_autonomy_contracts.py`, `triggers_dispatcher.py`, `autonomy_contracts.py`, `permissions/__init__.py`.
- **Exploration & Chiffres Clés** :
  - 6 fichiers de production dépassant le seuil `300–400` lignes : `help_generator_and_validator.py` (`919` L), `triggers_dispatcher.py` (`571` L), `WorkflowTriggersModal.tsx` (`564` L), `workflow_triggers.py` (`427` L), `autonomy_contracts.py` (`413` L), `autonomous_supervision.py` (`413` L).
  - Les tests de sécurité `test_story_7_1_contract_confinement_and_secrets.py`, `test_story_7_2_webhook_hmac_and_self_trigger.py`, `test_story_7_4_observer_and_rbac_guards.py` utilisent `ws_id = "0195f000-0000-7000-8000-000000000301"` absent de `DEFAULT_WORKSPACE_SEEDS` (`0192c4e0-0000-7000-8000-000000000201`), et `test_story_7_1..7_4_*_postgres18.py` utilisent un `org_id` sans rattachement à `marc` ; ils devront être alignés pour passer les gardes RBAC stricts.
- **Opportunités de Factorisation & Résorption de Dette Technique** :
  - Centralisation des gardes workspace/rôles dans `apps/api/src/orcia_api/routers/_finops_auth_guards.py` (`enforce_workspace_autonomy_mutation_guard`) et dérivation serveur de `scope_path` depuis `org_units`/`workspaces`.
  - Extraction d'un adaptateur partagé `RedisSseBrokerAdapter` (`orcia_core.orchestration._redis_sse_broker`) consommé par l'API et le worker `trigger-dispatcher`.
  - Factorisation du constructeur d'exécuteur autonome de déclencheurs (`build_autonomous_trigger_executor` dans `orcia_connectors/autonomous_runner.py`) pour l'API et le démon worker (respectant `AD-20 Contract 4`).
  - Découpage des 6 fichiers de production en modules `< 350` lignes à responsabilité unique.

---

## 2. Plan d'Implémentation

### 2.1 Schéma de Données & Migrations Alembic (`infra/migrations/versions/20261117_0705_epic7_review_fk_constraints.py`)
- Création d'une nouvelle révision réversible `20261117_0705` (`down_revision = "20261117_0704"`, sans jamais toucher `20261117_0701`) :
  - `upgrade()` : suppression préalable d'éventuelles lignes orphelines dans `autonomy_contracts` (`WHERE workspace_id NOT IN (SELECT id FROM workspaces)`) puis ajout de `CONSTRAINT fk_autonomy_contracts_workspace FOREIGN KEY (workspace_id) REFERENCES workspaces(id) ON DELETE CASCADE`.
  - `downgrade()` : `ALTER TABLE autonomy_contracts DROP CONSTRAINT IF EXISTS fk_autonomy_contracts_workspace;`.

### 2.2 Noyau Métier Hexagonal, Orchestration & Workers (`packages/orcia-core/`, `packages/orcia-connectors/`, `apps/worker/`, `scripts/`)
- **`orcia_core/permissions/`** :
  - `_autonomy_confinement.py` : suppression de la dispense `PLATFORM_ADMIN` dans `is_service_principal_scoped_to_workspace`, ajout de `:write`/`.write`/`write_` vers `"update"` dans `map_action_to_required_verb`.
  - `autonomy_contracts.py` : découpage si besoin pour rester `< 350` lignes et prise en charge stricte du périmètre signataire/SP.
- **`orcia_core/observability/`** :
  - `_internal/ecs_formatter.py` : protection de `_REGISTERED_SECRET_VALUES` par `threading.Lock`.
- **`orcia_core/orchestration/` & `orcia_core/catalog/`** :
  - Ajout de `RedisSseBrokerAdapter` (`_redis_sse_broker.py`) avec publication/écoute Redis Pub/Sub `channel:workspace:*` et buffer borné.
  - `triggers_dispatcher.py` : extraction de `_triggers_dispatch_helpers.py` (`< 350` L), support d'un port/callback `autonomous_executor`, gestion sécurisée de `unpack_encrypted_secret` dans `verify_webhook_request`.
  - `_triggers_schedulers.py` : suppression de `x-orcia-origin-run-id` sur `WorkflowPublished` dans `run_workflow_published_optin_help`.
  - `_sql_workflow_triggers_queries.py` & `sql_autonomy_contracts.py` : insertion Outbox en `'PENDING'` (`attempts = 0`) afin que `DramatiqOutboxRelay` dépile et relaie réellement les événements.
  - `autonomous_supervision.py`, `_autonomous_supervision_models.py`, `_internal/sql_autonomous_supervision.py` : hydratation SQL de `help_resource_id` et `previous_version_available`, ancrage de la correspondance `workflow_id` (`c.workflow_id = wd.uri OR wd.uri = 'orcia://workflows/' || c.workflow_id OR wd.uri LIKE '%/' || c.workflow_id`), suppression du repli `self._runs` quand `_engine` est actif, `await` systématique sur `redis_client.delete(...)`, découpage `< 350` L.
  - `contextual_help.py` : ajout de `resolve_for_route_async`, `publish_hot_version_async` et `rollback_to_previous_version_async` synchronisés sur PostgreSQL 18 (`catalog_items`) et Redis (`help:route:<route>:<pack>:<lang>`), normalisation `"orcia-core"` -> `"core"`.
  - `help_generator_and_validator.py` : découpage `< 350` L (`_help_article_models.py`, `_help_article_validator.py`, `_help_orcia_docs_workflow.py`, `_internal/_sql_help_catalog.py`), `await` sur `redis.delete`, préservation des métadonnées `@v(N-1)` dans `catalog_items`.
- **`packages/orcia-connectors/src/orcia_connectors/autonomous_runner.py`** :
  - Double vérification `kill_switch_check_fn` avant émission `SignedApprovalToken` et avant exécution connecteur, plus helper partagé `build_autonomous_trigger_executor` et `InternalCatalogActionAdapter`.
- **`apps/worker/` & `scripts/` & `infra/`** :
  - `trigger_dispatcher_daemon.py` : câblage complet avec `redis_client`, `RedisTriggerIdempotencyLockAdapter`, `RedisSseBrokerAdapter`, `httpx.AsyncClient` partagé, `EnvelopeVaultSecretProvider`, `HelpGenerationAndHotAttachmentService(session_factory=..., redis_client=...)`, et exécuteur autonome complet.
  - `sandbox_daemon.py` & `infra/k8s/base/kustomization.yaml` : retrait de `secret-template.yaml` de `resources:` et refus de démarrer `SandboxDaemonServer` avec `internal_token` vide hors `ORCIA_ENV in ("local", "test")`.
  - `scripts/manage.py` : sous-processus/tube `log-pipe` utilisant `RotatingFileHandler` 50 Mo pour rotation à chaud sans fermeture prématurée du descripteur.

### 2.3 Couche Backend API, Sécurité & Contrats (`apps/api/`, `packages/api-client/`)
- **`apps/api/src/orcia_api/dependencies/`** :
  - `core_and_lifespan.py` : initialisation réelle de `db_engine`, `session_maker`, `redis_client`, `secret_provider` et `RedisSseBrokerAdapter` (avec fermeture propre dans `app_lifespan` et démarrage du listener Pub/Sub Redis) sans exiger `ORCIA_ENABLE_PG_SESSION_MAKER=1`.
  - `orchestration_and_settings.py`, `autonomous_supervision.py`, `portal_and_assistant.py`, `workspace_and_packs.py` : appel à `get_or_create_shared_db_engine(request)`, injection de `redis_client`, `secret_provider`, `sse_broker`, et `autonomous_executor` dans `TriggerDispatcherService`.
- **`apps/api/src/orcia_api/routers/`** :
  - `autonomy_contracts.py` (+ `_autonomy_contracts_helpers.py` `< 350` L) : gardes stricts lecture/écriture (`resolve_finops_read_scope`, `enforce_scope_level_mutation`, habilitation signataire sur le workspace cible), dérivation serveur de `scope_path`, passage systématique de `ws_uuid` (`BLOCKING-04`), option `force_post_hoc_sample` sur `StartAutonomousRunRequest`.
  - `workflow_triggers.py` (+ `_workflow_triggers_helpers.py` `< 350` L) : gardes stricts lecture/écriture, suppression oracle `404` avant `401` HMAC + capture propre des erreurs de déchiffrement sur `/api/v1/triggers/alerts`.
  - `autonomous_supervision.py` : suppression des contournements `if ws is not None:` ; exécution systématique de `resolve_finops_read_scope` et `enforce_scope_level_mutation` + vérification rôle gouvernant.
  - `portal_and_help.py` : bascule des routes `/help/resolve`, `/help/publish`, `/help/rollback` sur les méthodes async PG18/Redis.
  - `workflows.py` : normalisation `X-Orcia-Workspace-Id` et journalisation structurée sur le hook `WorkflowPublished`.
- **`packages/api-client/`** :
  - Ajout de `saveWorkflowV2` et `rollbackContextualHelp`, et régénération complète via `scripts/export_openapi.py` (`0-diff`).

### 2.4 Interface Utilisateur & Expérience (`packages/ui/`, `apps/web/`)
- **`packages/ui/src/primitives/WorkflowTriggersModal.tsx`** : découpage `< 350` L en `WorkflowTriggersTypes.ts`, `WorkflowTriggerCard.tsx` et `WorkflowTriggersModal.tsx`.
- **`apps/web/src/components/ShellContextualHelpColumn.tsx`** : harmonisation `pack="core"`, dérivation de `isAdmin` depuis `useAuthSessionStore` (`roles`), câblage `onRollbackVersion`.
- **`apps/web/src/features/processes/studio/WorkflowFiveBlocksCanvas.tsx`** : câblage du bouton `Publier` sur `PUT /api/v1/workflows/v2/{workflow_id}` (`publish=True`) via `@orcia/api-client` avec gestion d'erreur explicite.

### 2.5 Analyse d'Impact sur la Pyramide des Tests (`AD-17` — Couches 1 à 5 + Sécurité)
- **Couche 1a & 1b (`tests/unit/`, `Vitest`)** : mise à jour et enrichissement pour lock ECS, rotation logs `manage.py`, refus token vide `sandbox_daemon.py`, `kustomization.yaml`, mapping `catalog:write -> update`, confinement SP strict, helpers découpage, `ShellContextualHelpColumn`, `WorkflowFiveBlocksCanvas`.
- **Couche 2 (`tests/integration/api/`)** : exécution complète des suites PG18/Redis `7.1`, `7.2`, `7.4` + ajout d'un nouveau test d'intégration Composition Root vérifiant `HTTP -> PostgreSQL 18 + Redis` **sans** injection manuelle de `app.state.*`, plus test du relais Outbox `WorkflowPublished` (`status='PENDING' -> 'PUBLISHED'`).
- **Couche 3 (`tests/contract/`, `lint-imports`, `lint_spine.py`)** : validation `export_openapi.py --check` (`0-diff`) et `5/5` contrats `lint-imports`.
- **Couche Sécurité (`tests/security/`)** : alignement des tests existants et ajout d'assertions anti-IDOR lecture/écriture inter-équipes, signataire inter-équipes, oracle 401 sur `/triggers/alerts`.
- **Couche 5 (`apps/web/e2e/13-epic-7-autonomous-governance-and-supervision.spec.ts`)** : suppression du branchement conditionnel `if ((await stopBtns.count()) > 0)`, assertions inconditionnelles sur publication Studio V2, exécution autonome, arrêt d'urgence + `F5`, échantillon post-hoc `/finops` + `F5`, et rétablissement `@v(N-1)`.

---

## 3. Bilan des Modifications & Résultats (Post-Implémentation)

### 3.1 Tableau Synthétique des Fichiers Développés & Modifiés

| Couche / Domaine | Fichier | Nature | Rôle & Findings Résolus |
| :--- | :--- | :--- | :--- |
| **Alembic** | `infra/migrations/versions/20261117_0705_epic7_review_fk_constraints.py` | Créé | `MINOR-02` : nouvelle révision réversible (`down_revision="20261117_0704"`) purgeant d'éventuelles lignes orphelines et ajoutant `fk_autonomy_contracts_workspace` (`ON DELETE CASCADE`) sans toucher `20261117_0701`. |
| **Core Permissions** | `packages/orcia-core/src/orcia_core/permissions/_autonomy_confinement.py` | Modifié | `BLOCKING-02`, `MINOR-02` : suppression de la dispense `PLATFORM_ADMIN` sur `is_service_principal_scoped_to_workspace`, ajout `:write`/`.write`/`write_` $\rightarrow$ `"update"`. |
| **Core Bootstrap** | `packages/orcia-core/src/orcia_core/bootstrap/_internal/sql_autonomy_contracts.py` | Modifié | `BLOCKING-03` : insertion Outbox en `'PENDING'` (`attempts=0`) pour dépilement par `DramatiqOutboxRelay`. |
| **Core Observability** | `packages/orcia-core/src/orcia_core/observability/_internal/ecs_formatter.py` | Modifié | `MAJOR-02` : protection thread-safe de `_REGISTERED_SECRET_VALUES` via `threading.Lock()`. |
| **Core Orchestration** | `packages/orcia-core/src/orcia_core/orchestration/_redis_sse_broker.py` + `__init__.py` | Créé / Modifié | `BLOCKING-05` : `RedisSseBrokerAdapter` cross-process sur Redis Pub/Sub `channel:workspace:*` + tampon borné `list_recent_events_async`. |
| **Core Orchestration** | `triggers_dispatcher.py` (`320` L) + `_triggers_dispatch_helpers.py` (`290` L) + `_triggers_lifecycle_ops.py` (`261` L) + `_triggers_pipeline.py` (`154` L) + `_triggers_schedulers.py` + `_internal/_sql_workflow_triggers_queries.py` | Modifié / Créés | `BLOCKING-03`, `MAJOR-05`, `MINOR-01` : injection `autonomous_executor`, Outbox `'PENDING'`, suppression `x-orcia-origin-run-id` sur `WorkflowPublished`, gestion sécurisée déchiffrement HMAC, découpage `< 350` L. |
| **Core Orchestration & Catalog** | `autonomous_supervision.py` (`355` L) + `_autonomous_supervision_models.py` + `_autonomous_supervision_ops.py` (`257` L) + `_internal/sql_autonomous_supervision.py` + `_internal/dbos_engine.py` + `catalog/contextual_help.py` + `catalog/_internal/sql_contextual_help.py` (`274` L) + `help_generator_and_validator.py` (`277` L) + `_help_article_models.py` (`190` L) + `_help_article_validator.py` (`170` L) + `_help_orcia_docs_workflow.py` (`292` L) + `_internal/_sql_help_catalog.py` (`134` L) | Modifié / Créés | `BLOCKING-03`, `MAJOR-01`, `MAJOR-05` : garde `KILL_SWITCH_STOPPED` `@DBOS.step`, jointure SQL ancrée + `help_resource_id`/`previous_version_available`, suppression repli RAM, `await redis.delete`, persistance async PG18/Redis de `ContextualHelpResolutionService`, normalisation pack `"core"`, découpages `< 350` L. |
| **Connectors** | `packages/orcia-connectors/src/orcia_connectors/autonomous_runner.py` + `_autonomous_trigger_bridge.py` (`206` L) | Modifié / Créé | `BLOCKING-03` : double contrôle `kill_switch_check_fn`, factory `build_autonomous_trigger_executor` et `InternalCatalogActionAdapter`. |
| **Worker & Infra** | `apps/worker/src/orcia_worker/trigger_dispatcher_daemon.py`, `sandbox_daemon.py`, `scripts/manage.py`, `infra/k8s/base/kustomization.yaml` | Modifié | `BLOCKING-05`, `MAJOR-02`, `MAJOR-03` : câblage Redis Lock / Pub/Sub / Vault / Help / Exécuteur autonome du démon, rejet token sandbox vide hors `local`/`test`, retrait `secret-template.yaml` de `kustomization.yaml`, rotation logs `pipe_stream_to_rotating_log` (`log-pipe`). |
| **Backend API** | `dependencies/{_core_providers,core_and_lifespan,orchestration_and_settings,autonomous_supervision,portal_and_assistant,workspace_and_packs}.py` | Modifié | `BLOCKING-01`, `BLOCKING-05` : initialisation réelle `db_engine`, `session_maker`, `redis_client`, `secret_provider` et `RedisSseBrokerAdapter` au Composition Root sans flag `ORCIA_ENABLE_PG_SESSION_MAKER`. |
| **Backend API Routers & Schemas** | `schemas/autonomy_contracts.py`, `routers/{_finops_auth_guards,autonomy_contracts,_autonomy_contracts_helpers,workflow_triggers,_workflow_triggers_helpers,autonomous_supervision,inbox_and_leases,portal_and_help,workflows}.py` | Modifié / Créés | `BLOCKING-02`, `BLOCKING-04`, `MAJOR-01`, `MAJOR-05`, `MINOR-01` : gardes RBAC/IDOR `resolve_finops_read_scope` & `enforce_workspace_governed_mutation`, `scope_path` dérivé serveur, `ws_uuid`, suppression oracle 404 `/triggers/alerts`, routes async `/help/*`, découpage `< 350` L (`292` / `305` / `229` L). |
| **SDK & UI** | `packages/api-client/{openapi.json,src/**}`, `packages/ui/src/primitives/{WorkflowTriggersModal,WorkflowTriggerCard,WorkflowTriggersTypes}.*`, `apps/web/src/components/ShellContextualHelpColumn.tsx`, `apps/web/src/features/processes/studio/WorkflowFiveBlocksCanvas.tsx` | Modifié / Créés | `MAJOR-01`, `MAJOR-04`, `MAJOR-05` : `saveWorkflowV2` (`PUT /api/v1/workflows/v2/{id}`), `rollbackContextualHelp`, SDK `0-diff`, découpage `WorkflowTriggersModal.tsx` (`336` L), `pack="core"` & `isAdmin` depuis session, câblage bouton `Publier`. |
| **Tests & Gouvernance** | `tests/unit/test_epic_7_review_fixes.py`, `tests/integration/api/test_epic_7_composition_root_postgres18.py`, `tests/integration/api/test_story_7_{1,2,4}_*_postgres18.py`, `tests/security/test_story_7_{1,2,4}_*.py`, `tests/unit/test_story_7_{0c,1}_*.py`, `apps/web/src/__tests__/vitestAutonomousSupervisionMockHandlers.ts`, `apps/web/e2e/13-epic-7-autonomous-governance-and-supervision.spec.ts`, `sprint-status.yaml`, `capabilities.yaml` | Modifié / Créés | `BLOCKING-01`, `MAJOR-04`, `MINOR-03` : E2E inconditionnel Studio V2 Publish $\rightarrow$ Contrat $\rightarrow$ Trigger $\rightarrow$ `/processes` Arrêt d'urgence + `F5` $\rightarrow$ `/finops` échantillon & rollback `@v(N-1)` + `F5`, test Composition Root sans injection `app.state.*`, `epic-7: done`, `CAP-201`/`CAP-202` à jour. |

### 3.2 Métriques, Volumétrie & Validation des 5 Couches (`AD-17`)
- **Volumétrie (`MAJOR-05`)** : les 6 fichiers signalés dépassant `400` lignes ont tous été ramenés sous `350` lignes (`help_generator_and_validator.py`: `277` L, `triggers_dispatcher.py`: `320` L, `WorkflowTriggersModal.tsx`: `336` L, `workflow_triggers.py`: `305` L, `autonomy_contracts.py`: `292` L, `autonomous_supervision.py` routeur: `229` L ; service `autonomous_supervision.py`: `355` L) et chaque module extrait reste `< 300` lignes (`103–292` L).
- **Portes statiques & contrats** :
  - `.venv/bin/ruff check . && .venv/bin/ruff format --check .` : `All checks passed! 1016 files already formatted`.
  - `.venv/bin/mypy --strict packages/orcia-core packages/orcia-connectors apps/api apps/worker` : `Success: no issues found in 459 source files`.
  - `.venv/bin/lint-imports` : `Analyzed 505 files, 3514 dependencies` — `Contracts: 5 kept, 0 broken`.
  - `lint_spine.py` : `"ok": true, "total_findings": 0`.
  - `scripts/export_openapi.py --check` : `0-diff` (`0` sortie).
  - `.venv/bin/detect-secrets-hook --baseline .secrets.baseline ...` : `DETECT_SECRETS_OK` (`0` secret non annoté).
- **Pyramide des tests `AD-17` (Exécution après derniers correctifs)** :
  - **Couche 1a & 3 & Sécurité (`pytest tests/unit tests/contract tests/conformance tests/security -q`)** : `669` tests exécutés, **0 échec** (inclut `tests/unit/test_epic_7_review_fixes.py`, `test_story_7_1_contract_confinement_and_secrets.py`, `test_story_7_2_webhook_hmac_and_self_trigger.py`, `test_story_7_4_observer_and_rbac_guards.py`).
  - **Couche 1b (`pnpm turbo run lint typecheck test`)** : `9 successful, 9 total` (`@orcia/api-client` `13/13`, `@orcia/ui` `25` fichiers, `@orcia/web` `32/32` fichiers / `135/135` tests).
  - **Couche 2 (`tests/integration/api/test_story_7_{1,2,4}_*_postgres18.py` + `test_epic_7_composition_root_postgres18.py`)** : `4 passed in 68.70s` sur conteneurs éphémères PostgreSQL 18 (`pgvector`) + Redis 7.4 sans aucune injection manuelle sur `app.state.*`.
  - **Couche 5 E2E (`pnpm --filter @orcia/web exec playwright test e2e/13-epic-7-autonomous-governance-and-supervision.spec.ts`)** : `2 passed (50.1s)` (parcours Bureau complet inconditionnel + Mobile Companion sans débordement ni erreur serveur).
  - **Vérité Terrain Jour 0 (`pnpm db:reset`)** : `APPLY (COMMITTED) — cleared_tables=66, deleted_rows=3, remaining_users=0, remaining_org_units=0, remaining_workspaces=0`.
- **Clôture & Traçabilité (`MINOR-03`)** : `epic-7: done` dans `docs/implementation-artifacts/sprint-status.yaml`, `CAP-201` & `CAP-202` mis à jour dans `docs/product/capabilities.yaml`, `scripts/check_implementation_docs.py`, `pnpm site:sync && pnpm site:check`, et `gitnexus detect-changes` exécutés après mise à jour documentaire.
