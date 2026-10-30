# Spécification Technique — Story 5.1 : Centre de Notifications Unifié (Individuel & Équipe), Prise en Charge Atomique (`Claim`), Verrou de Présence SSE `< 500 ms` & `DEC-CONC-01` (`ResourceLeasePort`)

- **Story Key** : `5-1-centre-de-notifications-unifié-individuel-équipe-prise-en-ch`
- **Action Item Associée** : `DEC-CONC-01` (Avenant A2 — `ResourceLeasePort`, table `resource_leases`, jeton de fencing monotone, ordre d'acquisition canonique & détection des attentes cycliques parent-enfant `SUB_WORKFLOW`)
- **Epic** : Epic 5 — Centre de Notifications Temps Réel (`< 500ms`), Supervision Multi-Runs, Centre de Pilotage Unifié Multi-Niveaux des Workspaces (`/workspaces`) & Expérience Mobile Companion
- **Références** : `FR-2`, `FR-7`, `AD-4`, `AD-17`, `AD-19`, `UX-DR2`, `UX-DR9`, `UX-DR11`, `NFR-PERF-2`, `DEC-CONC-01`

## 1. Objectifs Fonctionnels & Architecturaux

1. **Migration Alembic `0021_story_5_1_task_notifications_and_resource_leases.py`** :
   - Création de la table `task_notifications` (`id` UUIDv7 PK, `workspace_id`, `target_team_id`, `target_user_id`, `run_id`, `step_execution_id`, `notification_type`, `scope_kind`, `title`, `summary`, `status`, `claimed_by_user_id`, `claimed_by_display_name`, `claimed_at`, `lock_expires_at`, `source_event_id` UNIQUE pour idempotence Outbox, `created_at`).
   - Ajout de `claimed_by_user_id UUID NULL` et `claimed_at TIMESTAMPTZ NULL` sur `step_executions` (`ALTER TABLE step_executions ADD COLUMN IF NOT EXISTS ...`).
   - Création de la table `resource_leases` (`id` UUIDv7 PK, `resource_uri` UNIQUE, `resource_class`, `holder_run_id`, `holder_root_run_id`, `holder_parent_run_id`, `holder_step_execution_id`, `fencing_token` BIGINT monotone `> 0`, `acquired_at`, `expires_at`).
2. **Centre de Notifications Unifié, Abonné Outbox & Verrou de Présence Atomique SSE `< 500 ms` (`AD-4`, `UX-DR9`, `UX-DR11`)** :
   - Abonné Outbox idempotent créant automatiquement une notification dans `task_notifications` à partir de `HumanArbitrationRequested`, `GateEvaluated`, `StepCompleted` (`WAITING_FOR_HUMAN_*`) ou alertes d'habilitation/obsolescence (`0` doublon par `source_event_id`).
   - Prise en charge atomique (`POST /api/v1/tasks/{task_id}/claim` et `POST /api/v1/runs/{run_id}/steps/{step_id}/claim`) acquérant `SET lock:step:{step_execution_id} {user_id} NX EX 900`, persistant `claimed_by_user_id` et diffusant `task.claim.locked` sur Redis Pub/Sub `channel:workspace:{ws_id}` et `/api/v1/events/stream` en `< 500 ms`.
   - Support du `Force Unclaim` après `15 minutes` (`900 s`) d'inactivité ou par un `TEAM_LEAD` / `PLATFORM_ADMIN`.
3. **Baux de Ressources Partagées, Jeton de Fencing & Détection de Cycles Parent-Enfant (`DEC-CONC-01`, `AD-4`)** :
   - Définition de `ResourceLeasePort` dans `orcia_kernel.connector_ports` (exporté dans `orcia_kernel.ports`).
   - Implémentation de `ResourceLeaseService` (en mémoire et SQL PostgreSQL 18 `resource_leases`) garantissant :
     - un jeton de fencing strictement monotone (`fencing_token`) rejetant toute écriture sur un connecteur portant un jeton périmé (`ERR_STALE_FENCING_TOKEN` `HTTP 409`),
     - l'acquisition multi-ressources dans l'**ordre canonique** (`sorted(set(resource_uris))`) pour éliminer les deadlocks croisés,
     - la détection immédiate des **attentes cycliques parent-enfant (`SUB_WORKFLOW`)** lorsqu'un sous-workflow enfant tente d'acquérir un bail détenu par un ancêtre en attente (`ERR_CYCLIC_RESOURCE_WAIT_DETECTED` `HTTP 409`),
     - la reprise automatique d'un bail expiré (`expires_at <= now`) avec incrément du `fencing_token`.
4. **Composant `@orcia/ui` `<PresenceClaimPill />` (`UX-DR9`) & Panneau `InboxFeaturePanel` (`apps/web/src/features/inbox/`)** :
   - États `UNCLAIMED` (`Prendre (Claim)`), `CLAIMED_BY_ME` (`🔒 Pris par vous` + `Relâcher`), `CLAIMED_BY_PEER` (`🔒 En cours : {nom}`, opacité `85%`, + `Forcer la reprise (15m)`).
   - Filtres par portée (*Toutes*, *À moi*, *À mon équipe*) et par type, avec région `aria-live="polite"`.
