# Story 5.1 — Centre de Notifications Unifié (Individuel & Équipe) & Prise en Charge Atomique (Claim) + DEC-CONC-01

- **Date** : 2026-10-30
- **Story / Clé Sprint** : `5-1-centre-de-notifications-unifié-individuel-équipe-prise-en-ch` (`Epic 5`, incluant `DEC-CONC-01`)
- **Auteur / Contexte** : Implémentation de la Boîte de Réception Unifiée (`task_notifications`), du verrou de présence atomique (`lock:step:{step_execution_id}` `NX EX 900`), du flux SSE temps réel `/api/v1/events/stream` (`< 500 ms`), du composant `@orcia/ui` `<PresenceClaimPill />` (`UX-DR9`), et du `ResourceLeasePort` à jetons de fencing monotones (`DEC-CONC-01`, `FR-2`, `NFR-PERF-2`, `AD-4`, `AD-19`, `AD-20`).
- **Commits associés** : `working-tree`

---

## 1. Analyse du Besoin & Étude d'Impact Tech Lead (Pré-Implémentation)

### 1.1 Contexte & Problématique
- Sans coordination temps réel entre pairs d'une même équipe, deux contributeurs risquent d'arbitrer ou d'éditer simultanément la même étape en pause (`WAITING_FOR_HUMAN_GATE`, `WAITING_FOR_HUMAN_ARBITRATION`, `WAITING_FOR_HUMAN_ANCHOR`), provoquant des conflits d'écriture et un gaspillage cognitif.
- De même, au niveau de l'orchestration multi-workflows (`SUB_WORKFLOW` ou runs parallèles), deux exécutions peuvent tenter de modifier concurremment une même ressource partagée (`resource_uri`) ou provoquer un interblocage parent-enfant (*cyclic wait*).

### 1.2 Exploration, Analyse d'Impact GitNexus, Factorisation & Dette Technique
- **Analyse d'Impact GitNexus (`gitnexus_query`, `gitnexus_context`, `gitnexus_impact`)** :
  - `OutboxEventBus` (`apps/worker/src/orcia_worker/outbox_relay.py`) : ajout du souscripteur `"notifications"` (`notifications_queue`) sans impact cassant sur les 4 souscripteurs existants (`search_indexer`, `sse_broadcaster`, `finops_projector`, `webhook_dispatcher`).
  - `InboxFeaturePanel` (`apps/web/src/features/inbox/index.tsx`) : enrichissement avec `<PresenceClaimPill />` et filtres `ALL | PERSONAL | TEAM`.
- **Opportunités de Factorisation & Contrôle de Volumétrie** :
  - Séparation stricte en 3 modules métier `< 370` lignes dans `packages/orcia-core/src/orcia_core/orchestration/` :
    1. `presence_and_sse.py` (`335` lignes) : ports, adaptateurs Redis/SSE et entité `TaskNotificationEntity`.
    2. `notifications_and_claims.py` (`368` lignes) : `UnifiedNotificationAndClaimService` et consommation Outbox idempotente.
    3. `resource_leases.py` (`231` lignes) : `ResourceLeaseService` (`DEC-CONC-01`).

---

## 2. Plan d'Implémentation

### 2.1 Schéma de Données & Migrations Alembic (`infra/migrations/versions/0021_story_5_1_task_notifications_and_resource_leases.py`)
- Ajout de `claimed_by_user_id UUID` et `claimed_at TIMESTAMPTZ` sur `step_executions`.
- Création de `task_notifications` (`UUIDv7`, index sur `(workspace_id, status)` et `(target_team_id, status)`).
- Création de `resource_leases` (`UUIDv7`, `resource_uri UNIQUE`, `fencing_token BIGINT NOT NULL CHECK (fencing_token >= 1)`, `holder_run_id`, `holder_parent_run_id`).
- Réversibilité complète testée via `downgrade("0020_story_4_4_contract")` puis `upgrade("head")` sur `pgvector/pgvector:pg18`.

### 2.2 Noyau Métier Hexagonal & Workers (`packages/orcia-kernel/`, `packages/orcia-core/`, `apps/worker/`)
- `orcia_kernel.connector_ports.ResourceLeasePort` : protocole neutre de bail à jeton de fencing monotone (`DEC-CONC-01`).
- `ResourceLeaseService` : acquisition triée canonique (`sorted(set(resource_uris))`), incrémentation monotone par `resource_uri`, rejet `409 ERR_STALE_FENCING_TOKEN` et détection immédiate d'attente cyclique parent-enfant (`409 ERR_CYCLIC_RESOURCE_WAIT_DETECTED`).
- `UnifiedNotificationAndClaimService` : verrou atomique `lock:step:{step_execution_id}` (`NX EX 900`), expiration / `Force Unclaim` après 15 min (`900 s`), rejet `403 ERR_OBSERVER_MODE_READ_ONLY` et diffusion SSE `< 500 ms`.

### 2.3 Couche Backend API (`apps/api/`)
- Endpoints dans `apps/api/src/orcia_api/routers/inbox_and_leases.py` :
  - `GET /api/v1/inbox/notifications`
  - `POST /api/v1/tasks/{task_id}/claim` & `POST /api/v1/tasks/{task_id}/release`
  - `POST /api/v1/runs/{run_id}/steps/{step_id}/claim`
  - `GET /api/v1/events/stream` (`text/event-stream`)
  - `POST /api/v1/resource-leases/acquire` & `POST /api/v1/resource-leases/fenced-write`

### 2.4 Interface Utilisateur Direction C (`packages/ui/` & `apps/web/`)
- `<PresenceClaimPill />` (`packages/ui/src/primitives/PresenceClaimPill.tsx`) : 3 états (`UNCLAIMED`, `CLAIMED_BY_ME`, `CLAIMED_BY_PEER` avec opacité `0.85` et bouton `Forcer la libération (15m)`).
- `InboxFeaturePanel` (`apps/web/src/features/inbox/index.tsx`) : filtres `Toutes / Individuelles / Équipe`, badge ambre et prise en charge interactive.

---

## 3. Bilan des Modifications & Résultats (Post-Implémentation)

### 3.1 Fichiers Développés & Modifiés
| Fichier | Nature | Description synthétique |
| :--- | :--- | :--- |
| `infra/migrations/versions/0021_story_5_1_task_notifications_and_resource_leases.py` | Création | Tables `task_notifications`, `resource_leases` et colonnes `claimed_*` sur `step_executions` |
| `packages/orcia-kernel/src/orcia_kernel/connector_ports.py` | Modification | Ajout de `ResourceLeaseRecord` et `ResourceLeasePort` (`DEC-CONC-01`) |
| `packages/orcia-core/src/orcia_core/orchestration/presence_and_sse.py` | Création | Ports/Adapters `StepPresenceLockPort`, `SseBroadcastPort`, `TaskNotificationEntity` |
| `packages/orcia-core/src/orcia_core/orchestration/notifications_and_claims.py` | Création | `UnifiedNotificationAndClaimService` (Outbox, Claim, Release 15m, Observer Guard) |
| `packages/orcia-core/src/orcia_core/orchestration/resource_leases.py` | Création | `ResourceLeaseService` (tri canonique, fencing monotone, détection deadlock `SUB_WORKFLOW`) |
| `apps/api/src/orcia_api/routers/inbox_and_leases.py` | Création | Routes REST + SSE `/api/v1/inbox/*`, `/api/v1/tasks/*`, `/api/v1/events/stream`, `/api/v1/resource-leases/*` |
| `packages/ui/src/primitives/PresenceClaimPill.tsx` | Création | Composant `<PresenceClaimPill />` (`UX-DR9`) |
| `tests/unit/test_story_5_1_notifications_claim_and_resource_leases.py` | Création | Tests unitaires, API, SSE et migration PG18 `testcontainers` |

### 3.2 Résultats Chiffrés, Métriques & Qualité
- **Diffusion SSE mesurée** : `< 2 ms` en mémoire (cible `< 500 ms` `NFR-PERF-2`).
- **Tests `test_story_5_1_notifications_claim_and_resource_leases.py`** : `4 passed` (incluant `pgvector/pgvector:pg18`).
