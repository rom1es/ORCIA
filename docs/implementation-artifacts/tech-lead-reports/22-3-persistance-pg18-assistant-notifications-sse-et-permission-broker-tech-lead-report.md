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

> *[En attente d'implémentation de la Story 22.3]*

### 3.1 Fichiers Développés & Modifiés
| Fichier | Nature (Création / Modification / Refactoring) | Description synthétique |
| :--- | :--- | :--- |
| `packages/orcia-core/src/orcia_core/orchestration/_internal/sql_assistant_folders.py` | Création | *[À compléter après implémentation]* |
| `packages/orcia-core/src/orcia_core/orchestration/_internal/sql_task_notifications.py` | Création | *[À compléter après implémentation]* |
| `packages/orcia-core/src/orcia_core/permissions/_internal/sql_permission_broker.py` | Création | *[À compléter après implémentation]* |
| `apps/api/src/orcia_api/dependencies/*` | Modification | *[À compléter après implémentation]* |

### 3.2 Résultats Chiffrés, Métriques & Qualité
- **Couverture de tests** : *[$\ge 90\%$ requis à mesurer après implémentation]*
- **Qualité statique & Architecture** : `ruff`, `mypy --strict`, `pnpm typecheck`, `lint-imports`, `lint_spine.py`, `gitnexus_detect_changes()` *[À compléter]*

### 3.3 Validation & Procédure de Test sur Toute la Pyramide (`AD-17`)
- *[À compléter après exécution des 5 couches `AD-17` et Playwright Desktop/Mobile]*
