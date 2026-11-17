# Story 7.2 — Déclencheurs Événementiels Idempotents (`WEBHOOK`, `LOG_SINK_ALERT`, `CRON`, `OUTBOX_EVENT`, `MANUAL_AUTONOMOUS`), Déduplication & Protection Anti-Boucle (*Self-Trigger Guard*)

- **Date** : 2026-11-17
- **Story / Clé Sprint** : `7-2-déclencheurs-événementiels-idempotents-webhook-log-sink-aler` (`Epic 7`)
- **Capacité(s)** : `CAP-201` (mise à jour dans `docs/product/capabilities.yaml`) — classification : `feature`
- **Auteur / Contexte** : Implémentation du socle complet de déclencheurs autonomes idempotents pour Process Studio V2 et `trigger-dispatcher` (`FR-24`, `FR-26`, `FR-29`, `AD-12`, `AD-18`, `AD-19`, `AD-23`)
- **Commits associés** : *En cours d'implémentation (non commité par le worker)*

---

## 1. Analyse du Besoin & Étude d'Impact Tech Lead (Pré-Implémentation)

### 1.1 Contexte & Problématique
- **Problème résolu** : Jusqu'ici, les *Workflows* autonomes sous `AutonomyContract` (Story 7.1) ne pouvaient être lancés que manuellement via `POST /api/v1/workspaces/{ws}/workflows/{wf}/runs/autonomous`. Il manquait l'infrastructure événementielle et planifiée (`WEBHOOK`, `LOG_SINK_ALERT`, `CRON`, `OUTBOX_EVENT`, `MANUAL_AUTONOMOUS`), la triple idempotence (`Redis NX EX 86400` + `UNIQUE (trigger_id, trigger_idempotency_key)` + `DBOS SetWorkflowID`), la déduplication des livraisons webhook, le *Self-Trigger Guard* anti-boucle, le coupe-circuit (`CIRCUIT_OPEN`), le démon réel `trigger-dispatcher`, l'opt-in explicite de mise à jour d'aide (`WorkflowPublished` -> `generate-and-attach-help` désactivé au Jour 0) et l'interface Studio V2 **« Déclencheurs »**.
- **Comportement attendu** :
  1. Un déclencheur ne peut être `ACTIVE` ou exécuté que s'il est rattaché à un `AutonomyContract` actif (`422 ERR_AUTONOMY_CONTRACT_REQUIRED`).
  2. La validation HMAC-SHA256 temps-constant des webhooks est factorisée dans un module noyau unique (`orcia_core.permissions.webhook_security`) partagé entre `datasource_webhooks.py` (Story 18.2) et `workflow_triggers.py` (Story 7.2).
  3. Chaque déclenchement applique la triple barrière d'idempotence `AD-18`, la détection anti-boucle (*Self-Trigger Guard* tracée dans `domain_events_outbox` + `audit_ledger`), et le coupe-circuit sur dépassement de `max_runs_per_hour`, `max_daily_cost_usd` ou `max_consecutive_failures` (défaut `3` sur erreurs fonctionnelles, jamais sur erreurs transitoires `TransientConnectorError` retentées par `ConnectorInvoker`).
  4. Au Jour 0 (`auto_help_on_publish DEFAULT FALSE`), la publication d'un workflow (`WorkflowPublished`) ne lance **jamais** `generate-and-attach-help` sans opt-in explicite.
  5. Dans Process Studio V2, la modale **« Déclencheurs »** (`WorkflowTriggersModal.tsx`) permet de gérer ces déclencheurs sans jargon technique, avec `<SecretField />` Write-Only et persistance complète après `F5`.

### 1.2 Exploration, Analyse d'Impact GitNexus, Factorisation & Dette Technique
- **Analyse d'Impact GitNexus (`gitnexus_query`, `gitnexus_context`, `gitnexus_impact`)** :
  - `apps/api/src/orcia_api/routers/datasource_webhooks.py` (`_verify_hmac` L73–80, appelé par `ingest_datasource_webhook` L88–219, processus `proc_1312_ingest_datasource_we`, impact direct `1`, risque `LOW`) : le helper local `_verify_hmac` est dupliqué à l'identique du besoin Story 7.2 ; son extraction vers `packages/orcia-core/src/orcia_core/permissions/webhook_security.py` supprime la duplication sans impacter la signature publique de la route `/api/v1/webhooks/datasources/{datasource_id}`.
  - `apps/worker/src/orcia_worker/roles.py` (`main` L43–93) : le rôle `"trigger-dispatcher"` est déjà déclaré dans `CANONICAL_DEPLOYMENT_ROLES` (`packages/orcia-core/src/orcia_core/gates/tier2_sandbox.py`), mais `main(..., --serve)` tombait dans le stub générique `_serve_signal_loop`. Il est câblé vers `serve_trigger_dispatcher_daemon(once=bool(args.once))` dans `apps/worker/src/orcia_worker/trigger_dispatcher_daemon.py`.
  - `apps/worker/src/orcia_worker/outbox_relay.py` (`OutboxEventBus` L39–102, importé par `apps/worker/src/orcia_worker/__init__.py`, risque `LOW`) : extension par ajout d'un abonné `triggers_outbox` écoutant `WorkflowPublished` sans altérer les abonnés existants (`audit_finops`, `ontology`, `notifications`, `sse`).
  - `apps/web/src/features/processes/studio/StudioWorkflowHeaderBar.tsx` (`StudioWorkflowHeaderBar` L25–185, appelé directement par `WorkflowFiveBlocksCanvas` L23–322, impact `1`, risque `LOW`) : ajout des props de déclencheurs et du bouton `data-testid="studio-triggers-btn"` à côté de `studio-autonomy-contract-btn`, avec montage de `<WorkflowTriggersModal />` dans `WorkflowFiveBlocksCanvas.tsx`.
- **Exploration & Contraintes Mesurées** :
  - Migration précédente `head` = `20261117_0701` (`autonomy_contracts`, 22 valeurs `domain_events_outbox.event_type` `CHECK`, `workflow_runs.status` `CHECK`).
  - `0010_story_3_1_workflow_runs_triggers_and_run_lock.py` a créé `workflow_triggers` avec `trigger_type IN ('WEBHOOK', 'LOG_SINK_ALERT', 'CRON', 'MANUAL_AUTONOMOUS')` et `workflow_definitions(id)` FK. La migration `20261117_0702` doit préserver 100 % des valeurs existantes et ajouter `workflow_id` (avec index) pour relier directement aux IDs Studio V2 tout en maintenant l'intégrité FK.
  - `test_core_domain_isolation.py` interdit strictement les mots-clés `jira`, `confluence`, `git_branch`, `wsjf`, `rovo`, `copilot`, `safe`, `prd` dans `packages/orcia-core/src/orcia_core/orchestration/`.
  - `test_codebase_architectural_anti_patterns_audit.py` + Ruff `TID251` imposent : zéro `httpx.Client`/`requests`/`ThreadPoolExecutor`/`asyncio.run` dans les routeurs API, zéro `except Exception:` muet sans `logger.*`.
- **Opportunités de Factorisation & Volumétrie** :
  - **Factorisation DRY `Story 18.2` + `Story 7.2`** : `verify_webhook_hmac_sha256` et `compute_webhook_hmac_sha256` dans `packages/orcia-core/src/orcia_core/permissions/webhook_security.py` (`< 120` l.), réutilisés dans `datasource_webhooks.py` et `workflow_triggers.py`.
  - **Factorisation Write-Only Secret** : réutilisation de `SecretInputSpec`, `SecretStatusView`, `compute_secret_masked_hint` (`secret_hint.py`) et `compute_secret_fingerprint`, `pack_encrypted_secret`, `unpack_encrypted_secret` (`enterprise_connectors_crypto.py`), ainsi que `SecretInputPayload` / `SecretStatusResponse` (`schemas/settings_and_studio.py`).
  - **Découpage `< 300–350` lignes** : séparation du scanner de logs / parseur CRON dans `_triggers_log_cron.py`, du SQL dans `_internal/sql_workflow_triggers.py`, du dispatcher principal dans `triggers_dispatcher.py`, du daemon worker dans `trigger_dispatcher_daemon.py`, et de la modale UI dans `WorkflowTriggersModal.tsx` + hook `useWorkflowTriggers.ts`.

---

## 2. Plan d'Implémentation

### 2.1 Schéma de Données & Migrations Alembic (`infra/migrations/versions/`)
- `infra/migrations/versions/20261117_0702_story_7_2_triggers_outbox_and_optin_help.py` (`down_revision = "20261117_0701"`) :
  - **Table `workflow_triggers`** :
    - Remplacement dynamique de la contrainte `CHECK` sur `trigger_type` par `ck_workflow_triggers_type CHECK (trigger_type IN ('WEBHOOK', 'LOG_SINK_ALERT', 'CRON', 'OUTBOX_EVENT', 'MANUAL_AUTONOMOUS'))`.
    - Ajout des colonnes : `workflow_id VARCHAR(160) NOT NULL DEFAULT ''`, `contract_id UUID NULL REFERENCES autonomy_contracts(id) ON DELETE SET NULL`, `auto_help_on_publish BOOLEAN NOT NULL DEFAULT FALSE`, `consecutive_failures INTEGER NOT NULL DEFAULT 0 CHECK (consecutive_failures >= 0)`, `last_fired_at TIMESTAMPTZ NULL`, `updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()`, `webhook_secret_encrypted TEXT NULL`, `webhook_secret_fingerprint VARCHAR(80) NULL`, `webhook_secret_masked_hint VARCHAR(64) NULL`, `webhook_secret_updated_at TIMESTAMPTZ NULL`, `webhook_secret_updated_by VARCHAR(160) NULL`, `log_sink_service VARCHAR(128) NULL`, `log_sink_query_text VARCHAR(255) NULL`, `outbox_event_filter VARCHAR(128) NULL`.
    - Index `idx_workflow_triggers_workspace_wf` sur `(workspace_id, workflow_id, status)`.
  - **Table `trigger_webhook_deliveries`** :
    - `id UUID PRIMARY KEY`, `trigger_id UUID NOT NULL REFERENCES workflow_triggers(id) ON DELETE CASCADE`, `delivery_key VARCHAR(255) NOT NULL`, `received_at TIMESTAMPTZ NOT NULL DEFAULT NOW()`, `CONSTRAINT uq_trigger_webhook_delivery UNIQUE (trigger_id, delivery_key)`.
  - **Table `domain_events_outbox`** :
    - Extension de `domain_events_outbox_event_type_check` conservant les 22 types de `20261117_0701` et ajoutant `'TriggerFired'`, `'SelfTriggerBlocked'`, `'TriggerCircuitOpened'`, `'WorkflowPublished'`.
  - Réversibilité complète dans `downgrade()`.
- Mise à jour de `infra/scripts/maintenance/09_reset_db_first_boot.py` : insertion ordonnée `"trigger_webhook_deliveries"` $\rightarrow$ `"workflow_triggers"` $\rightarrow$ `"autonomy_contracts"` dans `ORDERED_MUTABLE_TABLES_TO_CLEAR`.

### 2.2 Noyau Métier Hexagonal, Orchestration & Workers (`packages/orcia-core/`, `apps/worker/`)
- `packages/orcia-core/src/orcia_core/kernel/errors.py` : ajout de `TransientConnectorError(TransientInfraError)` (`ERR_TRANSIENT_CONNECTOR_ERROR`).
- `packages/orcia-core/src/orcia_core/kernel/_governance_events.py` & `events.py` : ajout des événements `TriggerFired`, `SelfTriggerBlocked`, `TriggerCircuitOpened`, `WorkflowPublished`.
- `packages/orcia-core/src/orcia_core/permissions/webhook_security.py` : factorisation `verify_webhook_hmac_sha256` & `compute_webhook_hmac_sha256`.
- `packages/orcia-core/src/orcia_core/permissions/errors.py` & `_error_catalog.py` : erreurs `ERR_AUTONOMY_CONTRACT_REQUIRED` (`422`), `ERR_TRIGGER_CIRCUIT_OPEN` (`503`), `ERR_TRIGGER_NOT_FOUND` (`404`), `ERR_WEBHOOK_SIGNATURE_INVALID` (`401` existante), `ERR_TRIGGER_VALIDATION_FAILED` (`422`), `ERR_TRIGGER_DUPLICATE_KEY` (`409`).
- `packages/orcia-core/src/orcia_core/audit_finops/outbox_subscriber.py` : prise en charge de `TriggerFired`, `SelfTriggerBlocked`, `TriggerCircuitOpened`, `WorkflowPublished`.
- `packages/orcia-core/src/orcia_core/orchestration/triggers_dispatcher.py`, `_triggers_log_cron.py`, `_internal/sql_workflow_triggers.py` :
  - `TriggerDispatcherService` avec triple idempotence (`Redis SET lock:trigger:{trigger_id}:{idempotency_key} 1 NX EX 86400`, SQL `UNIQUE (trigger_id, trigger_idempotency_key)`, DBOS `SetWorkflowID(f"{trigger_id}:{idempotency_key}")`),
  - `evaluate_self_trigger_guard` (`x-orcia-origin-run-id`, `actor_account_id` / `service_principal_id` du contrat, `origin_service_principal`),
  - Coupe-circuit sur `max_runs_per_hour`, `max_daily_cost_usd` et `max_consecutive_failures` (défaut `3` ; erreurs `TransientConnectorError` retentées via `ConnectorInvoker`, erreurs fonctionnelles incrémentant `consecutive_failures` sans relance), émettant `TriggerCircuitOpened` + diffusion SSE `< 500 ms` sur `channel:workspace:{ws_id}`,
  - `LogSinkAnomalyScanner` interrogeant `LogSinkQueryPort` (`compute_error_fingerprint_sha256` + fenêtre `cooldown_window_seconds`),
  - Évaluateur `CRON` déterministe,
  - `OptInWorkflowHelpSubscriber` déclenchant `HelpGenerationAndHotAttachmentService.generate_and_attach_help` sur `WorkflowPublished` **uniquement** si `auto_help_on_publish == True` + contrat actif.
- `apps/worker/src/orcia_worker/outbox_relay.py`, `trigger_dispatcher_daemon.py`, `roles.py` : abonnement `triggers_outbox` sur `OutboxEventBus` et activation du rôle `--role trigger-dispatcher --serve [--once]`.

### 2.3 Couche Backend API, Sécurité & Contrats (`apps/api/`, `packages/api-client/`)
- `apps/api/src/orcia_api/schemas/workflow_triggers.py` + enregistrement dans `scripts/export_openapi.py` (`SCHEMA_DOMAIN_MODULES`).
- `apps/api/src/orcia_api/routers/datasource_webhooks.py` : remplacement de `_verify_hmac` par `verify_webhook_hmac_sha256`.
- `apps/api/src/orcia_api/routers/workflows.py` : émission de `WorkflowPublished` lors de `PUT /api/v1/workflows/v2/{workflow_id}` (`publish=True`), sans lancement d'aide au Jour 0 si opt-in `FALSE`.
- `apps/api/src/orcia_api/routers/workflow_triggers.py` : CRUD `/api/v1/workspaces/{workspace_id}/workflows/{workflow_id}/triggers`, `/fire`, `/reset-circuit`, `/api/v1/webhooks/triggers/{trigger_id}` (HMAC + `trigger_webhook_deliveries` + Self-Trigger Guard), `/api/v1/triggers/alerts` (repli alerte plateforme `AD-23.5` protégé par signature/secret).
- Câblage dans `apps/api/src/orcia_api/main.py` et `apps/api/src/orcia_api/dependencies/` + régénération OpenAPI 3.1 `0-diff` (`packages/api-client/` + `domains/workflowTriggers.ts`).

### 2.4 Interface Utilisateur & Expérience (`packages/ui/`, `apps/web/`)
- `packages/ui/src/primitives/WorkflowTriggersModal.tsx` (`< 340` l.) sur `OrciaDialog`, `<SecretField />` Write-Only, case à cocher *« Mettre à jour automatiquement la fiche d'aide à chaque publication »* **décochée par défaut**, état du coupe-circuit avec *« Réactiver »*, *« Déclencher maintenant »*, `<ContextualInfoTriggerButton />`, `<OrciaIcon />`, `0` `#hex`, `0` jargon banni.
- `apps/web/src/i18n/locales/workflow_triggers_labels.ts` (`fr` / `en`), hook `useWorkflowTriggers.ts`, câblage dans `StudioWorkflowHeaderBar.tsx` et `WorkflowFiveBlocksCanvas.tsx` avec survie `F5`.

### 2.5 Analyse d'Impact sur la Pyramide des Tests (`AD-17`)
- **Couche 1a (`tests/unit/test_story_7_2_triggers_and_self_trigger_guard.py`)** : HMAC factorisé, `Self-Trigger Guard`, coupe-circuit après 3 échecs fonctionnels (vs retry `TransientConnectorError`), `LogSinkAnomalyScanner` + cooldown, `CRON`, `OUTBOX_EVENT` opt-in (`FALSE` vs `TRUE`), `test_core_domain_isolation.py`.
- **Couche 1b (`apps/web/src/__tests__/story-7-2-studio-triggers-modal-and-f5.test.tsx`)** : création/édition déclencheur, opt-in aide décoché par défaut, Write-Only secret webhook, survie `F5` (`unmount()` $\rightarrow$ `render()`), audits `zero-dead-buttons-and-silent-catches-audit.test.tsx` & `design-system-look-and-feel-isolation.test.tsx`.
- **Couche 2 (`tests/integration/api/test_story_7_2_triggers_concurrency_postgres18.py`)** : migration Alembic `20261117_0702` (`upgrade`/`downgrade`/`upgrade`), rafale concurrente `asyncio.gather` sur PostgreSQL 18 + Redis 7.4 prouvant `1` seul `workflow_run`, déduplication `trigger_webhook_deliveries`, `Self-Trigger Guard` scellé dans `audit_ledger`, et test `09_reset_db_first_boot.py`.
- **Couche 3 (Contrats & Architecture)** : `export_openapi.py --check` (`0-diff`), `lint-imports` (`5 contracts kept, 0 broken`), `mypy --strict`, `ruff check`.
- **Couche Sécurité (`tests/security/test_story_7_2_webhook_hmac_and_self_trigger.py`)** : rejet HMAC `401`, rejet `403 ERR_OBSERVER_MODE_READ_ONLY`, `0` secret webhook en clair dans réponses API, logs et `audit_ledger`.

---

## 3. Bilan des Modifications & Résultats (Post-Implémentation)

### 3.1 Tableau des Fichiers Créés & Modifiés
| Couche | Fichier | Action | Rôle exact |
| :--- | :--- | :--- | :--- |
| **Alembic / DB** | `infra/migrations/versions/20261117_0702_story_7_2_triggers_outbox_and_optin_help.py` | Créé | Extension `workflow_triggers` (`OUTBOX_EVENT`, `auto_help_on_publish DEFAULT FALSE`, secrets Write-Only, circuit breaker), table `trigger_webhook_deliveries` et extension `domain_events_outbox` (`TriggerFired`, `SelfTriggerBlocked`, `TriggerCircuitOpened`, `WorkflowPublished`) |
| **Maintenance DB** | `infra/scripts/maintenance/09_reset_db_first_boot.py` | Modifié | Ordre `TRUNCATE`/`DELETE` Jour 0 : `trigger_webhook_deliveries` $\rightarrow$ `workflow_triggers` $\rightarrow$ `autonomy_contracts` |
| **Kernel** | `packages/orcia-core/src/orcia_core/kernel/errors.py`, `_governance_events.py`, `events.py` | Modifié | `TransientConnectorError` + 4 événements domaine (`TriggerFired`, `SelfTriggerBlocked` avec `run_id=None`, `TriggerCircuitOpened`, `WorkflowPublished`) |
| **Permissions (DRY)** | `packages/orcia-core/src/orcia_core/permissions/webhook_security.py`, `errors.py`, `_error_catalog.py`, `__init__.py` | Créé / Modifié | Factorisation `verify_webhook_hmac_sha256` & `compute_webhook_hmac_sha256` (Story 18.2 + 7.2) et erreurs domaine triggers (`401`/`404`/`409`/`422`/`503`) |
| **Audit Outbox** | `packages/orcia-core/src/orcia_core/audit_finops/outbox_subscriber.py` | Modifié | Traduction `audit_ledger` des 4 événements déclencheurs (`TriggerFired`, `SelfTriggerBlocked`, `TriggerCircuitOpened`, `WorkflowPublished`) |
| **Orchestration** | `packages/orcia-core/src/orcia_core/orchestration/triggers_dispatcher.py`, `_triggers_crud_helpers.py`, `_triggers_log_cron.py`, `_triggers_runtime_ports.py`, `_triggers_schedulers.py`, `_internal/_sql_workflow_triggers_queries.py`, `_internal/sql_workflow_triggers.py`, `models.py`, `__init__.py` | Créé / Modifié | `TriggerDispatcherService`, triple idempotence (`Redis NX EX 86400` + `UNIQUE` PG18 + `DBOS SetWorkflowID`), `evaluate_self_trigger_guard`, `LogSinkAnomalyScanner`, parseur `CRON`, opt-in `WorkflowPublished` (`auto_help_on_publish`), adaptateur PG18 & taxonomie d'erreurs |
| **Workers** | `apps/worker/src/orcia_worker/trigger_dispatcher_daemon.py`, `outbox_relay.py`, `roles.py` | Créé / Modifié | Démon `--role trigger-dispatcher --serve [--once]` et abonné `triggers_outbox` sur `OutboxEventBus` |
| **API FastAPI** | `apps/api/src/orcia_api/routers/workflow_triggers.py`, `schemas/workflow_triggers.py`, `routers/datasource_webhooks.py`, `routers/workflows.py`, `dependencies/orchestration_and_settings.py`, `dependencies/__init__.py`, `main.py`, `scripts/export_openapi.py` | Créé / Modifié | Routes CRUD/fire/reset-circuit, webhook HMAC + `trigger_webhook_deliveries`, repli `/api/v1/triggers/alerts` (`AD-23.5`), réutilisation `verify_webhook_hmac_sha256` dans `datasource_webhooks.py`, émission `WorkflowPublished` sur publication |
| **SDK OpenAPI** | `packages/api-client/openapi.json`, `src/generated/schema.ts`, `src/generated/workflow_triggers.ts`, `src/domains/workflowTriggers.ts`, `src/index.ts` | Créé / Modifié | Schéma OpenAPI 3.1 `0-diff` et client typé `workflowTriggers` |
| **Design System UI** | `packages/ui/src/primitives/WorkflowTriggersModal.tsx`, `packages/ui/src/index.ts` | Créé / Modifié | Modale RGAA `OrciaDialog` Direction C, `<SecretField />` Write-Only, opt-in aide décoché par défaut, `0` `#hex` |
| **SPA Web & i18n** | `apps/web/src/features/processes/studio/useWorkflowTriggers.ts`, `StudioWorkflowHeaderBar.tsx`, `WorkflowFiveBlocksCanvas.tsx`, `apps/web/src/i18n/locales/workflow_triggers_labels.ts`, `types.ts`, `fr.ts`, `en.ts`, `apps/web/src/__tests__/vitest.setup.ts`, `zero-dead-buttons-and-silent-catches-audit.test.tsx` | Créé / Modifié | Bouton `studio-triggers-btn`, persistance REST & survie `F5`, dictionnaires FR/EN sans jargon banni, garde-fou zéro bouton muet |
| **Tests (5 Couches)** | `tests/unit/test_story_7_2_triggers_and_self_trigger_guard.py`, `tests/unit/test_story_7_2_triggers_coverage.py`, `tests/security/test_story_7_2_webhook_hmac_and_self_trigger.py`, `tests/integration/api/test_story_7_2_triggers_concurrency_postgres18.py`, `apps/web/src/__tests__/story-7-2-studio-triggers-modal-and-f5.test.tsx` | Créé | Unitaires, sécurité Red-Team HMAC/`403`/secrets, concurrence PG18 + Redis `testcontainers` + Alembic up/down/up + `09_reset_db_first_boot.py`, Vitest + survie `F5` |
| **Gouvernance** | `docs/implementation-artifacts/sprint-status.yaml`, `docs/product/capabilities.yaml`, `docs/implementation-artifacts/tech-lead-reports/README.md`, manifeste & site statique (`pnpm site:sync`) | Modifié | `7-2-...: done`, `CAP-201` enrichie avec surfaces/tests `7.2`, rapport indexé & manifeste synchronisé |

### 3.2 Métriques & Couverture (`>= 90 %`)
- **Couverture combinée (`orcia_core.orchestration` + `orcia_core.permissions`)** : **90.28 %** (`9084` instructions, `2076` branches — seuil `--cov-fail-under=90` atteint).
  - `orcia_core/orchestration/_triggers_crud_helpers.py` : **100 %**
  - `orcia_core/orchestration/_triggers_log_cron.py` : **99 %**
  - `orcia_core/orchestration/_triggers_runtime_ports.py` : **99 %**
  - `orcia_core/orchestration/_internal/_sql_workflow_triggers_queries.py` : **98 %**
  - `orcia_core/orchestration/_internal/sql_workflow_triggers.py` : **98 %**
  - `orcia_core/orchestration/triggers_dispatcher.py` : **95 %**
  - `orcia_core/permissions/webhook_security.py` : **93 %**
  - `orcia_core/orchestration/_triggers_schedulers.py` : **88 %**

### 3.3 Validation des 5 Couches (`AD-17`) & Garde-Fous
- **Qualité Statique & Architecture** :
  - `.venv/bin/ruff check .` & `.venv/bin/ruff format --check .` $\rightarrow$ **0 erreur** (`983 files already formatted`).
  - `.venv/bin/lint-imports` $\rightarrow$ **`Contracts: 5 kept, 0 broken`** (`AD-19`, `AD-20`).
  - `.venv/bin/mypy --strict packages/orcia-core packages/orcia-connectors apps/api apps/worker` $\rightarrow$ **`Success: no issues found in 435 source files`**.
  - `.venv/bin/python scripts/export_openapi.py --check` $\rightarrow$ **`0-diff`** (`OpenAPI 3.1`).
  - `.venv/bin/python .agent/skills/bmad-architecture/scripts/lint_spine.py --workspace docs/planning-artifacts/architecture/architecture-ORCIA-2026-10-24` $\rightarrow$ **`ok: true, 0 findings`**.
- **Tests Python (`unit`, `contract`, `conformance`, `security`, `integration`)** :
  - `.venv/bin/pytest tests/unit tests/contract tests/conformance tests/security --cov=orcia_core.orchestration --cov=orcia_core.permissions --cov-fail-under=90` : `659 passed` (`Total coverage: 90.28%`), avec `1` flake Hypothesis `HealthCheck.too_slow` sur `tests/unit/test_permission_broker.py` sous charge immédiatement ré-exécuté et validé (`4 passed` dans `test_permission_broker.py`).
  - `.venv/bin/pytest tests/contract/test_openapi_contract.py` (`Schemathesis`) $\rightarrow$ **`2 passed`**.
  - `.venv/bin/pytest tests/integration/api/test_story_7_2_triggers_concurrency_postgres18.py` (`testcontainers` `pgvector/pgvector:pg18` + `redis:7.4.2-alpine`, Alembic `upgrade`/`downgrade`/`upgrade`, rafale concurrente `6` requêtes $\rightarrow$ `1` seul `workflow_run`, Self-Trigger Guard Outbox, repli alerte et `09_reset_db_first_boot.py`) $\rightarrow$ **`1 passed`**.
- **Tests TypeScript / UI (`Turborepo`)** :
  - `pnpm turbo run lint typecheck test --filter=@orcia/web --filter=@orcia/ui --filter=@orcia/api-client` $\rightarrow$ **`9 successful, 9 total`** (`@orcia/web: 31 files / 130 tests passed`, `@orcia/ui: 25 files / 106 tests passed`, `@orcia/api-client: 2 files / 13 tests passed`).
- **Gouvernance Capacités, Docs & GitNexus** :
  - `pnpm site:sync && pnpm site:check` $\rightarrow$ **`61/61 capacités live référencent au moins un test`** (`62` capacités, `150` rapports Tech Lead).
  - `.venv/bin/python scripts/check_implementation_docs.py` & `npx gitnexus@latest analyze --index-only && npx gitnexus@latest detect-changes --scope all --repo .` exécutés en fin de vérification.
