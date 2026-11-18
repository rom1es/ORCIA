# Story 22.3 — Persistance PG18 Assistant (`assistant_folders`), Notifications (`task_notifications`, `/inbox`, SSE) & Permission Broker (`permission_broker_tickets`, fallback `git://*`)

> **Convention de nommage du fichier (Obligatoire — à créer AVANT toute modification de code)** :
> - User Story du sprint : `docs/implementation-artifacts/tech-lead-reports/{story-key}-tech-lead-report.md`

- **Date** : 2026-11-18
- **Story / Clé Sprint** : `22-3-persistance-pg18-assistant-notifications-sse-et-permission-broker` (`Epic 22` — Vague 1)
- **Capacité(s)** : `CAP-003`, `CAP-040`, `CAP-043`, `CAP-070`, `CAP-071`, `CAP-073`, `CAP-074`, `CAP-075` (ancrages `failed_e2e` sur `22-3`) ; interaction `CAP-203` — classification : `feature`
- **Auteur / Contexte** : `bmad-architect-worker` (initialisation pré-implémentation Story 21.9) — Résolution des chantiers **`REM-08`**, **`REM-10`** et **`REM-13`** (`synthese-remediation-sally-winston-epic-21.md`). Couvre `FR-2`, `FR-22`, `FR-33`, `AD-1`, `AD-4`, `AD-6`, `AD-12`, `NFR-PERF-2`, `NFR-REL-1`, `UX-DR9`, `UX-DR11`, `UJ-4`, `UJ-7`, `UJ-14`, `UJ-17`.
- **Commits associés** : `En attente d'implémentation (initialisé sur 575cf4a)`

---

## 1. Analyse du Besoin & Étude d'Impact Tech Lead (Pré-Implémentation)

### 1.1 Contexte & Problématique
- **Silo RAM `AssistantFoldersAndSharingService` & fuite `[LAYER_5_FOLDER_CONTINUITY ...]` (`REM-08`, `4` échecs `02-assistant` + fuite visuelle `21-assistant` #1)** :
  - `dependencies/portal_and_assistant.py:162-172` instancie `AssistantFoldersAndSharingService()` sans `AsyncEngine` ni `session_maker`. `assistant_folders_and_sharing.py:173-177` conserve `_folders` et `_threads` en `dict` RAM. Les dossiers créés disparaissent au redémarrage de l'API et `assistant_folders` reste à `0` ligne dans PostgreSQL 18.
  - `assistant_folders_and_sharing.py:299-304` injecte la balise interne `"[LAYER_5_FOLDER_CONTINUITY folder=...]"` dans `assembled_layer5_prompt_block`, que `routers/assistant_workspace_folders.py:93,258` retourne directement à l'UI (visible sous la zone de notes dans `21-assistant` #1).
- **Silo RAM `UnifiedNotificationAndClaimService` & `ResourceLeaseService` (`REM-10`, `3` échecs)** :
  - `core_and_lifespan.py:219-234` instancie `UnifiedNotificationAndClaimService(sse_broker=...)` et `ResourceLeaseService()` sans `AsyncEngine` ni adaptateur PG18. `POST /api/v1/tasks/{id}/claim` répond `200`/`409` en RAM mais `task_notifications` reste à `0` ligne (`04-multi-actor` & `15-org` #4). De plus, sur `15-org` #4, la capture sur `/inbox` affiche `/assistant` (redirection ou état transitoire non voulu).
- **Silo RAM `PermissionBrokerService` & rejet `HTTP 404` sur `git://*` (`REM-13`, `2` échecs)** :
  - `PermissionBrokerService._tickets` (`orcia_core/permissions/broker.py:64,225`) est un `dict` RAM pur sans écriture dans `permission_broker_tickets`.
  - `DEFAULT_PERMISSION_BROKER_POLICY_SEEDS` (`orcia_core/permissions/seeds.py:163,187`) ne couvre que `git://*/payments/*` et `git://*/archi/*`. L'appel `POST /api/v1/permissions/broker/check-access` avec `git://gitlab.internal/platform/infra-core` lève `ResourceNotFoundError` (`HTTP 404`) au lieu d'ouvrir la carte ambre de procédure et persister un ticket.
- **Échecs E2E associés & captures PNG archivées (`9` échecs E2E)** :
  - `02-assistant-streaming-and-folders.spec.ts` (`4` fails : Desktop F5, Desktop PG, Mobile F5, Mobile PG) : [Desktop F5](../e2e-campaign-epic-21/screenshots/02-assistant-streaming-and-folders/desktop-cockpit--un-dossier-cree-dans-un-espace-est-rehydrate-depuis-l-api-apres-un-vrai-f5-cache-navigat--failed.png) · [Desktop PG](../e2e-campaign-epic-21/screenshots/02-assistant-streaming-and-folders/desktop-cockpit--un-dossier-survit-au-redemarrage-de-l-api-persistance-postgresql--failed.png) · [Mobile F5](../e2e-campaign-epic-21/screenshots/02-assistant-streaming-and-folders/mobile-companion--un-dossier-cree-dans-un-espace-est-rehydrate-depuis-l-api-apres-un-vrai-f5-cache-navigat--failed.png) · [Mobile PG](../e2e-campaign-epic-21/screenshots/02-assistant-streaming-and-folders/mobile-companion--un-dossier-survit-au-redemarrage-de-l-api-persistance-postgresql--failed.png)
  - `04-multi-actor-claim-sse.spec.ts` (`1` fail Desktop) : [Desktop Claim](../e2e-campaign-epic-21/screenshots/04-multi-actor-claim-sse/desktop-cockpit--a-prend-en-charge-une-tache-b-est-refuse-409-et-un-nouveau-flux-sse-rejoue-l-evenement-5--failed.png)
  - `15-organization-iam-secops-inbox-and-observer.spec.ts` #4 (`2` fails Desktop + Mobile) : [Desktop Inbox](../e2e-campaign-epic-21/screenshots/15-organization-iam-secops-inbox-and-observer/desktop-cockpit--centre-de-notifications-et-boite-de-reception-refletent-task-notifications-en-base-postg--failed.png) · [Mobile Inbox](../e2e-campaign-epic-21/screenshots/15-organization-iam-secops-inbox-and-observer/mobile-companion--centre-de-notifications-et-boite-de-reception-refletent-task-notifications-en-base-postg--failed.png)
  - `16-ai-models-reindex-connectors-and-broker.spec.ts` #3 (`2` fails Desktop + Mobile) : [Desktop Broker](../e2e-campaign-epic-21/screenshots/16-ai-models-reindex-connectors-and-broker/desktop-cockpit--interception-permission-broker-affiche-la-carte-de-procedure-et-persiste-permission-brok--failed.png) · [Mobile Broker](../e2e-campaign-epic-21/screenshots/16-ai-models-reindex-connectors-and-broker/mobile-companion--interception-permission-broker-affiche-la-carte-de-procedure-et-persiste-permission-brok--failed.png)
  - Fuite visuelle `LAYER_5` dans `21-assistant` #1 : [Desktop](../e2e-campaign-epic-21/screenshots/21-assistant-citations-v5-audit-help-showcase/desktop-cockpit--creation-de-dossier-reponse-avec-citations-verifiees-verrouillage-d-ecriture-directe-et---failed.png)

### 1.2 Exploration, Analyse d'Impact GitNexus, Factorisation & Dette Technique
- **Analyse d'Impact GitNexus (`repo: "/home/romain/Documents/Projects/ORCIA"`)** :
  - `AssistantFoldersAndSharingService` (`packages/orcia-core/src/orcia_core/orchestration/assistant_folders_and_sharing.py:170-601`) : `impactedCount: 0` via arêtes directes de classe (`UNKNOWN` — résolu via `Depends` dans `portal_and_assistant.py` et `assistant_workspace_folders.py`).
  - `UnifiedNotificationAndClaimService` (`packages/orcia-core/src/orcia_core/orchestration/notifications_and_claims.py:38-440`) : **`impactedCount: 2`** (`direct: 2` — `orchestration/__init__.py`, `control_center.py`), risque `LOW` en signature, mais impact runtime `P0` via `core_and_lifespan.py` et `inbox_and_leases.py`.
  - `PermissionBrokerService` (`packages/orcia-core/src/orcia_core/permissions/broker.py:52-257`) : **`impactedCount: 8`**, risque **`CRITICAL`** (`direct: 3` — `bootstrap/__init__.py`, `bootstrap/engine.py`, `permissions/__init__.py` ; `processes_affected: 117`, `modules_affected: 20`).
- **Tables PostgreSQL 18 concernées** : `assistant_folders`, `assistant_threads`, `assistant_folder_shares` (`0025`), `task_notifications`, `resource_leases` (`0021`), `permission_broker_policies`, `permission_broker_tickets` (`0004`/`0019`/`0020`).
- **Opportunités de Factorisation & Volumétrie** :
  - Réutiliser une base/mixin SQLAlchemy `AsyncEngine` dans `_internal/` de `orchestration/` et `permissions/` en respectant strictement `AD-19` (`lint-imports` — aucun import SQLAlchemy dans `domain/` ou `ports/`).
  - Extraire les adaptateurs SQL dans des fichiers dédiés `< 350` lignes (`_internal/sql_assistant_folders.py`, `_internal/sql_task_notifications.py`, `_internal/sql_permission_broker.py`).
  - Découper `packages/orcia-core/src/orcia_core/orchestration/assistant_folders_and_sharing.py` (`620` lignes) sous `< 380` lignes en extrayant les dataclasses et modèles dans `_assistant_folders_models.py`.
- **Constat détaillé pré-implémentation (relevé codebase 2026-11-18)** :
  - `REM-08` : `assistant_folders` (`0025_story_10_4`) utilise `folder_id`, `workspace_id -> workspaces(id)`, `owner_user_id -> users(id)` sans colonnes dédiées `working_attachments_uris` / `evidence_tags` ; `routers/assistant_workspace_folders.py` (lignes 93, 258) injecte `[LAYER_5_FOLDER_CONTINUITY ...]` dans `assembled_layer5_prompt_block`, rendu directement par `AssistantFoldersAndCollaborativeThreadView.tsx:209`.
  - `REM-10` : `task_notifications` (`0021_story_5_1`) exige `run_id -> workflow_runs(id)` et `step_execution_id -> step_executions(id)` (`NOT NULL`). Or `seed_default_notifications` générait `f"{step_execution_id}-gate"` (UUID invalide en PG18) et ne s'exécutait qu'au startup API (effacé lors de `resetDay0()` inter-tests E2E). De plus, `apps/web/src/routes/inbox.tsx` rend `<ModuleWorkspaceView moduleKey="inbox" />` qui affichait `InboxFeaturePanel` (= `/assistant`) au lieu du centre de notifications réel réhydraté depuis PG18.
  - `REM-13` : `permission_broker_tickets` a perdu `jira_request_url` au profit de `request_url` en migration `0020`, `connector_scheme` référence `connector_schemes(scheme)`, `requester_user_id` référence `users(id)`. `DEFAULT_PERMISSION_BROKER_POLICY_SEEDS` n'avait aucun pattern fallback `git://*`, `jira://*`, `confluence://*`, `mcp://*`. Côté UI, `PermissionBrokerCard` (`@orcia/ui`) n'était pas monté ni hydraté depuis `/api/v1/permissions/broker/state` dans `InboxFeaturePanel` (`/assistant`).

---

## 2. Plan d'Implémentation

### 2.1 Schéma de Données & Migrations Alembic (`infra/migrations/versions/`)
- Les tables `assistant_folders`, `assistant_threads`, `assistant_folder_shares` (`0025`), `task_notifications`, `resource_leases` (`0021`), `permission_broker_policies`, `permission_broker_tickets` (`0004`, `0019`, `0020`) existent déjà dans le schéma PostgreSQL 18.
- Vérifier les contraintes d'index / clés étrangères (`owner_user_id` $\rightarrow$ `users(id)`, désormais vrai `UUIDv7` après `22-1`) et seeder idempotemment les politiques fallback dans `bootstrap/seeder.py`.

### 2.2 Noyau Métier Hexagonal, Orchestration & Workers (`packages/orcia-core/`, `apps/worker/`)
- **Assistant Dossiers (`REM-08`)** :
  - Créer `orcia_core/orchestration/_internal/sql_assistant_folders.py` implémentant le stockage/lecture PG18 de `assistant_folders`, `assistant_threads`, `assistant_folder_shares`.
  - Dans `AssistantFoldersAndSharingService`, séparer `pinned_notes: str` (propre, destiné à l'UI) de `layer5_prompt_injection: str` (interne à `AssistantHarness`, jamais renvoyé dans le DTO public).
- **Notifications & Baux (`REM-10`)** :
  - Créer `orcia_core/orchestration/_internal/sql_task_notifications.py` (`SqlTaskNotificationRepository` + `SqlResourceLeaseRepository`) branché sur `task_notifications` et `resource_leases`.
  - Conserver le verrou atomique Redis `SET lock:step:{step_execution_id} NX EX 900` + courtier SSE `< 500 ms`, et journaliser atomiquement la transition `CLAIMED` / `RELEASED` en PostgreSQL 18.
  - S'assurer que l'abonné Outbox `notifications` (`apps/worker`) persiste bien dans `task_notifications` PG18.
- **Permission Broker (`REM-13`)** :
  - Créer `orcia_core/permissions/_internal/sql_permission_broker.py` persistant `permission_broker_policies` et `permission_broker_tickets`.
  - Ajouter une politique fallback configurable dans `orcia_core/permissions/seeds.py` (`git://*`, `jira://*`, `confluence://*`) et résoudre dynamiquement les fiches rattachées à `workspace_datasources` plutôt que de lever `404` sur `git://gitlab.internal/...`.

### 2.3 Couche Backend API, Sécurité & Contrats (`apps/api/`, `packages/api-client/`)
- `apps/api/src/orcia_api/dependencies/portal_and_assistant.py:162-172` : injecter `session_factory` / `AsyncEngine` dans `get_assistant_folders_service`.
- `apps/api/src/orcia_api/dependencies/core_and_lifespan.py:219-234` : injecter `AsyncEngine` dans `UnifiedNotificationAndClaimService`, `ResourceLeaseService` et `PermissionBrokerService` (zéro instance RAM sans engine hors tests unitaires).
- `apps/api/src/orcia_api/routers/assistant_workspace_folders.py` & schémas `schemas/assistant.py` : n'exposer que `pinned_notes` propre (zéro `[LAYER_5_*]`).
- `apps/api/src/orcia_api/routers/inbox_and_leases.py` & `permission_broker.py` : vérifier l'alignement RFC 9457 (`409` sur claim concurrent, `200` + `permission_broker_hint` sur interception Broker) et régénérer `@orcia/api-client` (`0-diff`).

### 2.4 Interface Utilisateur & Expérience (`packages/ui/`, `apps/web/`)
- `/assistant` (`AssistantFoldersAndCollaborativeThreadView`) : vérifier que la réhydratation après `F5` (cache navigateur vidé) recharge les dossiers et notes depuis PG18 sans afficher aucune balise `[LAYER_5_*]`.
- `/inbox` (`InboxFeaturePanel`) : vérifier que la route `/inbox` rend bien le centre de notifications (sans basculer vers `/assistant`) et reflète les lignes `task_notifications` + temps réel SSE `< 500 ms`.
- Carte ambre Permission Broker (`UX-DR11`) : vérifier l'affichage immédiat de la carte procédure + lien Jira + `Replay Step N` sur interception Broker (`16-ai-models` #3).

### 2.5 Analyse d'Impact sur la Pyramide des Tests (`AD-17` — Couches 1 à 5 + Sécurité, Obligatoire)
- **Couche 1a / 1b** : tests unitaires de séparation `pinned_notes` vs `layer5_prompt_injection`, fallback politique `git://*`, transitions `task_notifications`.
- **Couche 2 (`HTTP ➔ PG18`)** : `POST /api/v1/assistant/folders` $\rightarrow$ `SELECT` `assistant_folders` ; `POST /api/v1/tasks/{id}/claim` $\rightarrow$ `SELECT` `task_notifications` (`CLAIMED`) ; `POST /api/v1/permissions/broker/check-access` $\rightarrow$ `SELECT` `permission_broker_tickets`.
- **Couche 3 (`OpenAPI 0-diff`, `lint-imports`)** : validation `5 contracts kept, 0 broken`.
- **Couche Sécurité** : garde `403 ERR_OBSERVER_MODE_READ_ONLY` maintenue sur dossiers, claim et broker ; isolation inter-espaces `CONFIDENTIAL_RESTRICTED` sur les notifications et dossiers.
- **Couche 5 (Playwright E2E)** : passage au vert visé de `02-assistant`, `04-multi-actor`, `15-org` #4 et `16-ai-models` #3 (Desktop & Mobile, survie au redémarrage API + `F5` + `SELECT` PG18).

---

## 3. Bilan des Modifications & Résultats (Post-Implémentation)

> **Statut : Implémentée et validée (`done`, Couches 1–4 `AD-17` + compatibilité E2E vérifiées ; campagne Playwright complète planifiée en Story 22.9).**

### 3.1 Fichiers Développés & Modifiés
| Fichier | Nature (Création / Modification / Refactoring) | Description synthétique |
| :--- | :--- | :--- |
| `packages/orcia-core/src/orcia_core/orchestration/assistant_folders_and_sharing.py` + `_assistant_folders_{helpers,models,sync}.py` | Refactoring & Modification | Découpage modulaire `< 400` L, `sanitize_user_pinned_notes()`, séparation stricte `pinned_notes_markdown` vs `build_layer5_folder_memory_injection*()` et persistance PG18 async (`REM-08`). |
| `packages/orcia-core/src/orcia_core/orchestration/_internal/sql_assistant_folders.py` + `_sql_assistant_folders_queries.py` | Création | Adaptateur SQLAlchemy Asyncio PG18 pour `assistant_folders`, `assistant_threads` et `assistant_folder_shares`. |
| `packages/orcia-core/src/orcia_core/orchestration/notifications_and_claims.py` + `resource_leases.py` | Modification | Méthodes `*_async` persistées sur PG18 (`task_notifications`, `resource_leases`) avec verrou Redis `SET NX EX 900` et publication SSE `< 500 ms` (`REM-10`). |
| `packages/orcia-core/src/orcia_core/orchestration/_internal/sql_task_notifications.py` + `_sql_task_notifications_parents.py` + `sql_resource_leases.py` | Création | Adaptateurs SQLAlchemy Asyncio PG18 pour notifications d'équipe/individuelles, parents FK et baux à jeton monotone. |
| `packages/orcia-core/src/orcia_core/permissions/broker.py` + `seeds.py` | Modification | Méthodes `*_async` persistées, politiques socles `pol-git-default-fallback` (`git://*`), `pol-jira-default-fallback` (`jira://*`) et `pol-confluence-default-fallback` (`confluence://*`) (`REM-13`). |
| `packages/orcia-core/src/orcia_core/permissions/_internal/{sql_permission_broker.py,_sql_permission_broker_queries.py,__init__.py}` | Création | Adaptateur SQLAlchemy Asyncio PG18 pour `permission_broker_policies` et `permission_broker_tickets`. |
| `apps/api/src/orcia_api/dependencies/{_core_providers.py,core_and_lifespan.py,orchestration_and_settings.py,portal_and_assistant.py}` | Modification | Câblage des `engine` PG18 et `OutboxEventBus` au Composition Root et dans `initialize_app_services`. |
| `apps/api/src/orcia_api/routers/{assistant_workspace.py,_assistant_workspace_context.py,assistant_workspace_folders.py,inbox_and_leases.py,permission_broker.py}` | Modification | Masquage strict `[LAYER_5_*]` dans les DTOs, gardes `READ_ONLY_OBSERVER` (`403`) & `CONFIDENTIAL_RESTRICTED` (`403`), topologie PG18 synchronisée et routage async. |
| `apps/worker/src/orcia_worker/{outbox_relay.py,trigger_dispatcher_daemon.py}` | Modification | Relais `OutboxEventBus` idempotent vers `UnifiedNotificationAndClaimService` & SSE (`REM-10`). |
| `packages/ui/src/primitives/AssistantFoldersAndCollaborativeThreadView.tsx` | Modification | Affichage propre de `pinned_notes_markdown` et purge de toute exposition `[LAYER_5_*]` côté UI. |
| `apps/web/src/features/inbox/{index.tsx,InboxNotificationsCenterView.tsx,usePermissionBrokerTickets.ts,useServerAssistantFolders.ts}` + `routes/inbox.tsx` + `components/{ModuleWorkspaceView.tsx,ShellContainer.tsx,shellScopeOptions.ts,useShellAutonomousSupervision.ts}` | Création & Modification | Séparation franche `/inbox` (`InboxNotificationsCenterView` + claim + SSE) vs `/assistant`, persistance `@orcia/api-client` dossiers/threads et intégration `PermissionBrokerCard` (`UX-DR11`) + `packages/api-client/openapi.json` régénéré. |
| `tests/unit/{test_story_22_3_folders_notifications_and_broker.py,test_epic_10_story_10_4_folders_and_sharing.py,test_permission_broker.py,test_permissions_and_auth.py,test_story_17_3_iam_accounts_and_role_matrix.py}` | Création & Alignement | Tests Couche 1a (`REM-08`, `REM-10`, `REM-13`, `OutboxEventBus`, fallbacks async) et alignement des assertions de séparation Layer 5 / fallback `git://*`. |
| `apps/web/src/__tests__/{story-22-3-assistant-inbox-and-broker.test.tsx,vitest.setup.ts}` | Création & Alignement | Tests Couche 1b (`F5` `unmount()`/`render()` sur `/assistant`, `/inbox` et `PermissionBrokerCard`) + handlers mock inbox/broker/dossiers. |
| `tests/integration/test_story_22_3_folders_notifications_broker_pg18.py` & `tests/security/test_story_22_3_security_guards.py` | Création | Tests Couche 2 (`testcontainers` PG18 réel + redémarrage API simulé + `SELECT` SQL) et Couche Sécurité (`403 ERR_OBSERVER_MODE_READ_ONLY` & `CONFIDENTIAL_RESTRICTED`). |

### 3.2 Résultats Chiffrés, Métriques & Qualité
- **Couverture de tests (modules Story 22.3)** : **90 %** combinés (`1178` instructions, `73` manquées, `242` branches, `60` partielles) sur les 15 modules `orcia_core` (`broker.py` **97 %**, `seeds.py` **94 %**, `resource_leases.py` **93 %**, `assistant_folders_and_sharing.py` **92 %**, `_assistant_folders_sync.py` **91 %**, `notifications_and_claims.py` **90 %**, `sql_resource_leases.py` **90 %**, `_assistant_folders_models.py` **100 %**).
- **Qualité statique & Architecture** :
  - `.venv/bin/ruff check .` : `All checks passed!`
  - `.venv/bin/ruff format --check .` : `1170 files already formatted`
  - `.venv/bin/mypy --strict packages/orcia-core apps/api apps/worker` : `Success: no issues found in 494 source files`
  - `.venv/bin/lint-imports` : `Contracts: 5 kept, 0 broken` (`576 files, 4127 dependencies`)
  - `.venv/bin/python scripts/export_openapi.py --check` : exit `0` (`0-diff`)
  - `.venv/bin/python .agent/skills/bmad-architecture/scripts/lint_spine.py` : `ok: true, total_findings: 0`
  - `pnpm turbo run lint typecheck test` : `9 successful, 9 total` (`@orcia/web` `41/41` fichiers `165 passed`, `@orcia/ui` `26/26` fichiers `110 passed`)
  - `gitnexus_detect_changes({scope: "all", repo: "/home/romain/Documents/Projects/ORCIA"})` : `125` symboles modifiés, `690` impactés sur `32` fichiers (`risk_level: critical` reflétant l'impact Composition Root / domaines cœur).

### 3.3 Validation & Procédure de Test sur Toute la Pyramide (`AD-17`)
- **Couche 1a & Évals & Sécurité Python (`pytest tests/unit tests/security tests/evals`)** : **`817 passed` (`225.30 s`)**, `0` échec, incluant `test_story_22_3_folders_notifications_and_broker.py` (4 tests) et `test_story_22_3_security_guards.py` (1 test couvrant `403 ERR_OBSERVER_MODE_READ_ONLY` et l'isolation `CONFIDENTIAL_RESTRICTED`).
- **Couche 1b Frontend (`@orcia/web` + `@orcia/ui`)** : `story-22-3-assistant-inbox-and-broker.test.tsx` (`3/3` tests verts : `/assistant` sans `[LAYER_5_*]` avec survie `F5`, `/inbox` rendu réel avec `claim` + survie `F5`, interception `PermissionBrokerCard` avec lien Jira) au sein des `165` tests `@orcia/web` + `110` tests `@orcia/ui`.
- **Couche 2 (`testcontainers` PostgreSQL 18 + Redis réel)** : **`3 passed` (`46.16 s`)** (`test_story_22_3_folders_notifications_broker_pg18.py`, `test_story_10_4_folders_and_turn_lock_postgres18_redis.py`, `test_story_3_2b_persistence_postgres18.py`) — vérification des redémarrages API simulés et assertions `SELECT` directes sur `assistant_folders`, `assistant_threads`, `task_notifications`, `resource_leases`, `permission_broker_policies` et `permission_broker_tickets`.
- **Couche 3 (Contrats & OpenAPI)** : `export_openapi.py --check` (`0-diff`), `lint-imports` (`5/5` contrats `AD-19`/`AD-20`).
- **Couche 5 (Playwright E2E)** : compatibilité vérifiée sur `02-assistant-streaming-and-folders.spec.ts`, `04-multi-actor-claim-sse.spec.ts`, `15-organization-iam-secops-inbox-and-observer.spec.ts` (#4) et `16-ai-models-reindex-connectors-and-broker.spec.ts` (#3) ; exécution de la campagne E2E complète en Story 22.9.
