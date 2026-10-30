# Spécification Technique — Story 4.4 : Actions & Transitions Jira Multi-Projets Staged aux Gates (+ Webhooks `jira:issue_updated`), Serveur MCP Gouverné (`/api/v1/mcp`) & `DEC-ACC-01` (`AccessRequestChannelPort`)

- **Story Key** : `4-4-actions-transitions-de-workflows-jira-multi-projets-staged-a`
- **Action Item Associée** : `DEC-ACC-01` (Avenant A2 — `AccessRequestChannelPort` & migration *Expand/Backfill/Contract* `jira_request_url` $\rightarrow$ `request_url`)
- **Epic** : Epic 4 — Gouvernance d'Exécution & Gates Hybrides à 3 Niveaux
- **Références** : `FR-16`, `FR-24`, `AD-3`, `AD-5`, `AD-6`, `AD-11`, `AD-12`, `AD-19`, `AD-20`, `AR-7`, `NFR-EXT-1`, `DEC-ACC-01`

## 1. Objectifs Fonctionnels & Architecturaux

1. **`DEC-ACC-01` (`AccessRequestChannelPort` & Migrations `0019` Expand / `0020` Contract)** :
   - Définir `AccessRequestChannelPort` dans `orcia_kernel.connector_ports` (exporté dans `orcia_kernel.ports`) pour découpler `orcia_core.permissions` d'Atlassian Jira (`AD-20`).
   - Fournir un adaptateur générique par défaut dans `orcia_core.permissions` et enregistrer `JiraAccessRequestChannelAdapter` dans `orcia_pack_sdlc`.
   - Ajouter la colonne générique `request_url` sur `permission_broker_tickets` (`0019_story_4_4_access_request_channel_expand.py` : Expand + Backfill SQL `UPDATE permission_broker_tickets SET request_url = jira_request_url WHERE request_url IS NULL` + `SET NOT NULL`), puis contracter `jira_request_url` (`0020_story_4_4_access_request_channel_contract.py`), tout en conservant `request_url` et l'alias `jira_request_url` sur le modèle de domaine et le schéma API pour la rétrocompatibilité.
2. **Actions & Transitions Jira Multi-Projets Staged aux Gates (`orcia_pack_sdlc.jira_actions`)** :
   - Routage multi-projets Jira au sein d'un Workspace par alias/rôle (ex. `jira-pay-build` $\rightarrow$ `PAYBUILD`, `jira-pay-run` $\rightarrow$ `PAYSEC`) et interrogation JQL temps réel.
   - Pré-validation d'une transition (`transition_issue`) via simulation/appel de `GET /rest/api/3/issue/{key}/transitions` vérifiant la légalité de la transition cible et la présence des champs obligatoires de l'écran de transition.
   - Enregistrement en mode **Action Staged** (`status: "STAGED"`) dans `step_executions.draft_artifact_jsonb` (sans effet de bord externe avant le passage de la Gate).
   - Exécution effective uniquement au passage de la **Gate** (`gate_status == "PASS"`) via `ConnectorInvoker` (`AD-12`, idempotence par `idempotency_key`), avec injection automatique du lien de provenance `run-lock.json` (`run_lock_sha256`, `run_id`, `step_execution_id`).
3. **Récepteur de Webhook `jira:issue_updated` (`< 500 ms`, `FR-16`)** :
   - Réception du payload `jira:issue_updated` (passage du statut à `Done`).
   - Publication transactionnelle immédiate (`< 500 ms`) d'un événement dans `domain_events_outbox` pour notifier l'équipe via SSE et déclencher le *Replay* ciblé du Run en pause.
4. **Serveur MCP Gouverné (`/api/v1/mcp` pour IDE externes, `FR-24`, `AR-7`, `AD-3`, `AD-6`)** :
   - Exposition des outils MCP en mode `passthrough` (`ontology.query`, `kb.search`, `catalog.get`, `blackboard.read`, `blackboard.propose_draft`).
   - Blocage matériel de toute écriture sur une section ou un artefact marqué `human_authored_required: true` (`HTTP 422 ERR_HUMAN_ANCHOR_REQUIRED`) ainsi que pour tout appelant `READ_ONLY_OBSERVER` (`HTTP 403 ERR_OBSERVER_MODE_READ_ONLY`).
