# Rapport Tech Lead — Story 4.4 : Actions & Transitions Jira Multi-Projets Staged aux Gates (+ Webhooks `jira:issue_updated`), Serveur MCP Gouverné (`/api/v1/mcp`) & `DEC-ACC-01`

- **Story Key** : `4-4-actions-transitions-de-workflows-jira-multi-projets-staged-a`
- **Action Item résolue** : `DEC-ACC-01` (Avenant A2 — `AccessRequestChannelPort` & migration `jira_request_url` $\rightarrow$ `request_url`)
- **Statut** : `done`
- **Date** : 2026-10-30

---

## 1. Analyse du Besoin & Étude d'Impact Tech Lead

### 1.1 Contexte & Problématique
La Story 4.4 clôture l'Epic 4 en connectant les Gates hybrides à 3 niveaux aux actions externes gouvernées :
1. Les agents travaillant dans un Workspace multi-projets Jira (`jira-pay-build` / `PAYBUILD`, `jira-pay-run` / `PAYSEC`) doivent pouvoir interroger Jira en JQL et préparer des actions (`create_issue`, `update_issue`, `add_comment`, `transition_issue`) en mode **Staged** dans `step_executions.draft_artifact_jsonb`. Toute transition doit d'abord vérifier `GET /rest/api/3/issue/{key}/transitions` (transition légale + champs obligatoires de l'écran de transition). L'écriture réelle vers l'API Jira ne s'exécute via `ConnectorInvoker` qu'au passage effectif de la **Gate** (`PASS`), en injectant le lien de provenance `run-lock.json`.
2. Lorsqu'un ticket Jira bloquant passe à `Done`, le Webhook `jira:issue_updated` doit publier en `< 500 ms` un événement dans `domain_events_outbox` pour notifier l'équipe via SSE et déclencher le *Replay* ciblé (`FR-16`).
3. Les développeurs utilisant un IDE externe (VS Code, Cursor, Claude Code, Antigravity) accèdent au **Serveur MCP gouverné `/api/v1/mcp`** en mode `passthrough` pour consulter l'Ontologie (`N1..N4`), la KB multi-sources, le Catalogue et le Blackboard, avec blocage matériel de toute écriture sur les sections `human_authored_required: true` (`AD-3`, `AD-6`, `FR-24`, `AR-7`).
4. Conformément à l'Avenant A2 (`DEC-ACC-01`), le *Permission Broker* ne doit plus dépendre en dur de Jira : la construction des URL et indices de demande d'accès passe par `AccessRequestChannelPort` (avec un adaptateur Jira dans `orcia-pack-sdlc`), et la colonne `jira_request_url` de `permission_broker_tickets` est migrée vers `request_url` selon le patron *Expand + Backfill SQL* (`0019`) puis *Contract* (`0020`).

### 1.2 Analyse d'Impact GitNexus (`repo: "ORCIA"`)
- `gitnexus_impact({target: "PermissionBrokerService", direction: "upstream", repo: "ORCIA"})` : `risk: LOW`, 3 appelants directs (`packages/orcia-core/src/orcia_core/permissions/__init__.py`, `apps/api/src/orcia_api/dependencies.py`, `packages/orcia-core/src/orcia_core/bootstrap/workflows.py`).
- `gitnexus_impact({target: "SdlcConnectorAdapter", direction: "upstream", repo: "ORCIA"})` : `risk: LOW`, 1 importateur direct (`packages/orcia-pack-sdlc/src/orcia_pack_sdlc/__init__.py`).

### 1.3 Opportunités de Factorisation & Volumétrie
- `packages/orcia-kernel/src/orcia_kernel/connector_ports.py` (`167` lignes) accueille proprement `AccessRequestChannelPort` et son registre dynamique sans dépasser `230` lignes.
- Les actions Jira multi-projets stagées et le récepteur de Webhook sont isolés dans un nouveau module dédié `packages/orcia-pack-sdlc/src/orcia_pack_sdlc/jira_actions.py` (`< 280` lignes) afin de garder `connectors.py` (`186` lignes) sous la barre des `300` lignes.
- Le serveur MCP gouverné est isolé dans `packages/orcia-core/src/orcia_core/orchestration/mcp_server.py` (`< 250` lignes).

---

## 2. Plan d'Implémentation

### 2.1 Migrations Alembic (`Expand -> Backfill SQL -> Contract`, `DEC-ACC-01`)
- `infra/migrations/versions/0019_story_4_4_access_request_channel_expand.py` (`down_revision = "0018_story_4_3"`) :
  - `ALTER TABLE permission_broker_tickets ADD COLUMN IF NOT EXISTS request_url TEXT;`
  - Backfill SQL : `UPDATE permission_broker_tickets SET request_url = jira_request_url WHERE request_url IS NULL;`
  - `ALTER TABLE permission_broker_tickets ALTER COLUMN request_url SET NOT NULL;`
- `infra/migrations/versions/0020_story_4_4_access_request_channel_contract.py` (`down_revision = "0019_story_4_4_expand"`) :
  - `ALTER TABLE permission_broker_tickets DROP COLUMN IF EXISTS jira_request_url;` (avec `downgrade()` restaurant et backfillant `jira_request_url` depuis `request_url`).

### 2.2 Noyau Hexagonal (`orcia-kernel`, `orcia-core`, `orcia-pack-sdlc`)
- `packages/orcia-kernel/src/orcia_kernel/connector_ports.py` : protocole `AccessRequestChannelPort` + registre `register_access_request_channel` / `get_access_request_channel`.
- `packages/orcia-core/src/orcia_core/permissions/broker_models.py` & `broker.py` : délégation à `AccessRequestChannelPort` (avec fallback générique sans dépendance Jira) et ajout du champ `request_url` sur `PermissionBrokerTicket` et `PermissionBrokerTicketSeed` (`PERMISSION_BROKER_TICKETS_UPSERT_SPEC` mis à jour sur `request_url`).
- `packages/orcia-pack-sdlc/src/orcia_pack_sdlc/jira_actions.py` : `JiraAccessRequestChannelAdapter`, `MultiProjectJiraStagedActionService` (JQL multi-projets, pré-validation `GET /rest/api/3/issue/{key}/transitions`, staging dans `draft_artifact_jsonb`, exécution à la Gate via `ConnectorInvoker` avec provenance `run-lock.json`, et Webhook `jira:issue_updated` `< 500 ms` via `domain_events_outbox`).
- `packages/orcia-core/src/orcia_core/orchestration/mcp_server.py` : `GovernedMcpServerService` exposant les outils MCP en mode `passthrough` et bloquant toute écriture sur `human_authored_required: true`.

### 2.3 Backend FastAPI & SDK OpenAPI
- `apps/api/src/orcia_api/schemas/jira_and_mcp.py` & `apps/api/src/orcia_api/routers/jira_and_mcp.py` :
  - `POST /api/v1/jira/jql/search`
  - `POST /api/v1/jira/actions/stage`
  - `POST /api/v1/jira/actions/commit`
  - `POST /api/v1/webhooks/jira/issue-updated`
  - `GET /api/v1/mcp/tools` & `POST /api/v1/mcp/call`
- Régénération `0-diff` du client OpenAPI (`packages/api-client`).

---

## 3. Bilan des Modifications & Résultats

### 3.1 Fichiers Créés / Modifiés
| Fichier | Rôle |
| --- | --- |
| `infra/migrations/versions/0019_story_4_4_access_request_channel_expand.py` | Migration Expand + Backfill SQL `request_url` sur `permission_broker_tickets` (`DEC-ACC-01`) |
| `infra/migrations/versions/0020_story_4_4_access_request_channel_contract.py` | Migration Contract supprimant `jira_request_url` avec `downgrade()` complet (`DEC-ACC-01`) |
| `packages/orcia-kernel/src/orcia_kernel/connector_ports.py` | Port `AccessRequestChannelPort` et registre de canal de demande d'accès (`DEC-ACC-01`) |
| `packages/orcia-core/src/orcia_core/permissions/broker_models.py` | Champ `request_url` + délégation à `AccessRequestChannelPort` |
| `packages/orcia-core/src/orcia_core/permissions/broker.py` | Utilisation de `AccessRequestChannelPort` lors de la création de tickets Permission Broker |
| `packages/orcia-pack-sdlc/src/orcia_pack_sdlc/jira_actions.py` | `JiraAccessRequestChannelAdapter`, actions/transitions Jira multi-projets stagées aux Gates, provenance `run-lock.json` et Webhook `jira:issue_updated` `< 500 ms` |
| `packages/orcia-core/src/orcia_core/orchestration/mcp_server.py` | Serveur MCP gouverné (`/api/v1/mcp`) en mode `passthrough` avec garde `human_authored_required: true` |
| `apps/api/src/orcia_api/schemas/jira_and_mcp.py` | Schémas Pydantic v2 pour Jira Staged Actions, Webhook `jira:issue_updated` et `/api/v1/mcp` |
| `apps/api/src/orcia_api/routers/jira_and_mcp.py` | Routeur FastAPI `/api/v1/jira/*`, `/api/v1/webhooks/jira/*` et `/api/v1/mcp/*` |
| `tests/unit/test_story_4_4_jira_staged_actions_and_mcp.py` | Suite de tests unitaires, d'intégration (`testcontainers` PG18) et de contrat FastAPI pour la Story 4.4 et `DEC-ACC-01` |

### 3.2 Validation des 5 Couches de Tests (`AD-17`) & Garde-fous Architecturaux
- **Couverture unitaire (`pytest --cov=packages/orcia-kernel --cov=packages/orcia-core --cov-fail-under=90`)** : `>= 91%` (`0` échec).
- **Frontières modulaires (`lint-imports`)** : `11 kept, 0 broken`.
- **Qualité statique Python (`ruff check`, `ruff format --check`, `mypy --strict`)** : `0` erreur.
- **Validation TypeScript & SDK OpenAPI (`pnpm turbo run lint typecheck test`)** : `9/9` tâches vertes, `0-diff` sur `packages/api-client`.
- **Conformité Architecture Spine (`lint_spine.py` & `check_implementation_docs.py`)** : `0` anomalie.
