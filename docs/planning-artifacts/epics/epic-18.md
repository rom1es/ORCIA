## Epic 18: Refonte Multi-Nature des Sources d'Espace (`/workspaces/$wsId/sources`), Moteur de Fraîcheur Différentiel (`SHA-256` & Sonde `24h`), Contrat d'Outils Normalisé `codegraph-mcp` & Service Souverain `GitNexus`

Découpler rigoureusement les **Connecteurs d'Entreprise** (infrastructure globale administrée une seule fois dans `/settings`) des **Sources d'Espace** (rattachées par chaque équipe dans `/workspaces/$wsId/sources`), prendre en charge leur triple nature réelle (`DOCUMENT_KB` Confluence/docs, `WORK_TRACKER` Jira, `SOURCE_CODE` Git avec indexation AST légère `0 $` LLM + graphe déterministe `GitNexus` activable/désactivable par le Responsable d'espace via `SERVICE_ACCOUNT` ou jeton personnel `WORKSPACE_LEAD_TOKEN`, et `RELATIONAL_SCHEMA` DDL), industrialiser le moteur de fraîcheur (`WEBHOOK_PUSH` via `domain_events_outbox`, court-circuit `SHA-256` *no-op* et sonde légère `24h`), normaliser l'exploration déterministe du code derrière le contrat lecture seule `codegraph-mcp` (`5` outils agnostiques `GitNexus` / `Sourcegraph SCIP` dans `packages/orcia-connectors`), et durcir le sidecar Docker `gitnexus-mcp` monté strictement en lecture seule (`:ro`, réseau interne sans jeton Git) (`FR-17`, `FR-23`, `FR-24`, `FR-34`, `FR-35`, `AD-17`, `AD-19`, `AD-21`).

### Story 18.1: Déport des Sources dans `/workspaces/$wsId/sources`, Filtres Multi-Nature Direction C, Modale `OrciaDialog` & Gouvernance `GitNexus` par Responsable d'Espace

As a Responsable d'Espace (`TEAM_LEAD` / `BU_LEAD`),
I want consulter, filtrer par nature, rattacher en modale centrée `OrciaDialog`, synchroniser manuellement et gouverner l'activation `GitNexus` (avec compte de service ou mon jeton personnel chiffré) des sources directement sous `/workspaces/$wsId/sources`,
So that l'administration globale `/settings` reste strictement dédiée aux connecteurs socle et chaque équipe maîtrise le périmètre et le moteur d'indexation de ses dépôts et bases documentaires (`FR-23`, `FR-34`, `AD-19`, `AD-21`).

**Acceptance Criteria:**

**Given** un utilisateur naviguant vers `/workspaces/$wsId/sources` ou `/workspaces/$wsId` (synchronisé avec le sélecteur d'espace et le fil d'Ariane)
**When** la page se charge
**Then** elle affiche les pastilles de filtrage Direction C (`Toutes | Connaissances | Backlog & Tickets | Code & Contrats | Schémas SQL`), l'horodatage de fraîcheur (`last_sync_at`), l'empreinte `fingerprint_hash`, le mode (`WEBHOOK_PUSH` / `POLLING_24H`), un bouton actif `Synchroniser` (`POST /api/v1/workspaces/{ws_id}/datasources/{id}/sync`) et — pour les sources `SOURCE_CODE` — un interrupteur `GitNexus` (`SERVICE_ACCOUNT` vs `WORKSPACE_LEAD_TOKEN`)
**And** dans `/settings`, l'ancien bloc résiduel `register-connector-form` / `datasources-table` est définitivement purgé au profit d'un lien vers `/workspaces/$wsId/sources`.

**Given** un clic sur `+ Rattacher une Source` ou `Modifier`
**When** la modale centrée `OrciaDialog` s'ouvre (laissant visible la Zone 4 d'Aide Contextuelle `340px`)
**Then** elle permet de choisir la `source_nature`, le connecteur homologué, `target_scope`, `target_ref`, `sync_mode`, l'identité de synchro RAG et les options `GitNexus` (`codegraph_enabled`, `codegraph_auth_mode`) ; la mutation rejette `READ_ONLY_OBSERVER` (`HTTP 403 ERR_OBSERVER_MODE_READ_ONLY`) et refuse à un simple `CONTRIBUTOR` d'activer/désactiver `GitNexus` (`HTTP 403 ERR_CODEGRAPH_WORKSPACE_LEAD_REQUIRED`), tandis que l'état créé/modifié persiste intégralement en PostgreSQL 18 et survit au rechargement `F5`.

### Story 18.2: Moteur de Fraîcheur Différentiel, Webhooks `Outbox`, Court-Circuit `SHA-256`, Sonde `24h` & Cycle de Vie Disque `GitNexus`

As a Développeur ou utilisateur d'Agent IA,
I want que les webhooks entrants validés par HMAC et la sonde légère `24h` réconcilient les index sans recalcul inutile grâce à l'empreinte `SHA-256`, et que le worker d'indexation maintienne ou purge immédiatement le graphe `GitNexus` selon le choix du Responsable d'espace,
So that les réponses et revues d'architecture s'appuient sur des index à jour à coût token nul sur les dépôts inchangés (`0 $` LLM sur `git push` et les week-ends calmes) (`FR-23`, `FR-24`, `AD-12`, `AD-17`).

**Acceptance Criteria:**

**Given** un événement Webhook entrant sur `POST /api/v1/webhooks/datasources/{datasource_id}`
**When** la signature HMAC est vérifiée en temps constant (sinon `HTTP 401 ERR_WEBHOOK_SIGNATURE_INVALID`) et la livraison dédupliquée sur `(datasource_id, delivery_key)` dans `datasource_webhook_deliveries`
**Then** si `remote_fingerprint_sha256` est identique à `fingerprint_hash`, le traitement court-circuite immédiatement en `NO_OP_UNCHANGED` (`0` embedding recalculé) ; sinon l'événement neutre `DatasourceSyncRequested` est publié atomiquement dans `domain_events_outbox` pour `worker-indexing`.

**Given** une source dont le dernier signal remonte à `> 24h` lors de `POST /api/v1/workspaces/{workspace_id}/datasources/reconcile-staleness`
**When** la sonde légère `24h` (`RemoteFingerprintProbePort`, `0 $` LLM) interroge la cible
**Then** un dépôt calme à empreinte inchangée reste `SYNCED` (`last_probe_at` mis à jour), une dérive d'empreinte déclenche `AUTO_HEAL_DELTA_SYNC`, et une source muette/injoignable bascule en `STALE` avec publication de `DatasourceFreshnessEvaluated` ; de plus, l'acteur `codegraph_indexer` utilise `SERVICE_ACCOUNT` ou `WORKSPACE_LEAD_TOKEN` (basculant en `PAUSED_REFERENT_RENEWAL_REQUIRED` si le jeton du responsable expire) et purge immédiatement `${GITNEXUS_STORAGE_ROOT}/{ws_id}/{ds_id}` lorsque `codegraph_enabled` repasse à `false`.

### Story 18.3: Contrat d'Outils Normalisé `codegraph-mcp` Lecture Seule (`5` Outils) & Intégration Workflows de Revue

As a Agent d'Architecture ou *Blind Hunter*,
I want invoquer un contrat normalisé et agnostique `codegraph-mcp` limité en lecture seule aux dépôts `codegraph_enabled` de l'espace courant,
So that l'analyse d'impact et l'exploration de code reposent sur un graphe déterministe et sur des tranches de lignes bornées sans aucun chunking vectoriel naïf ni dérive silencieuse vis-à-vis de `run-lock.json` (`FR-17`, `FR-35`, `AD-19`, `AD-20`).

**Acceptance Criteria:**

**Given** `CodegraphMcpConnector` dans `packages/orcia-connectors` (`5` outils : `codegraph_locate_symbol`, `codegraph_get_call_hierarchy`, `codegraph_find_references`, `codegraph_calculate_blast_radius`, `codegraph_read_span` borné à `<= 250` lignes sans traversée de chemin)
**When** un agent ou le routeur `/api/v1/workspaces/{workspace_id}/codegraph/invoke` appelle un outil
**Then** `workspace_id` est injecté côté serveur (rejet si le dépôt n'est pas `SOURCE_CODE` et `codegraph_enabled = true` dans cet espace), `preview_write`/`execute_write` sont refusés en lecture seule, un écart `indexed_commit_sha != run_lock_commit_sha` émet l'alerte explicite `GRAPH_MOVED_SINCE_RUN_LOCK`, et le fournisseur est interchangeable par configuration (`CODEGRAPH_PROVIDER=gitnexus | sourcegraph_scip`).

**Given** un workflow déclaratif de revue (`packs/sdlc/workflows/wf-03-etude-architecture.yaml`)
**When** l'étape d'étude d'impact s'exécute via `mcp:codegraph` (`scope: read`)
**Then** l'Agent Executor invoque `codegraph_calculate_blast_radius` en respectant l'isolation `lint-imports` (`orcia_core` n'importe jamais `orcia_connectors`) et la cohérence OpenAPI `0-diff`.

### Story 18.4: Infrastructure `docker-compose.yml` (`gitnexus-mcp` Isolé `:ro`), Registre des Capacités (`CAP-180`) & Validation `AD-17` Complète

As a Administrateur Plateforme / Ingénieur DevOps,
I want déployer le sidecar `gitnexus-mcp` dans `infra/docker/docker-compose.yml` avec montage `:ro` d'un volume dédié sur un réseau interne dépourvu de jetons Git et tracer l'ensemble de l'`Epic 18` dans `capabilities.yaml`,
So that l'architecture locale et CI offre un graphe de code souverain, isolé et auditable à `100 %` (`AD-17`, `AD-19`, `NFR-SEC`).

**Acceptance Criteria:**

**Given** `infra/docker/docker-compose.yml` et `.env.example`
**When** la pile est inspectée et testée par les garde-fous d'infrastructure et de sécurité
**Then** `worker-indexing` monte `gitnexus_graphs:/data/graphs` en lecture-écriture (`GITNEXUS_CONTENT_RETENTION=symbol`), tandis que `gitnexus-mcp` (`ghcr.io/abhigyanpatwari/gitnexus:latest`, `mcp --http --port 8095`) monte `gitnexus_graphs:/data/graphs:ro`, tourne sur le réseau `codegraph-internal` (`internal: true`) sans port exposé ni jeton Git, protégé par `ORCIA_CODEGRAPH_INTERNAL_TOKEN` et durcissement conteneur (`read_only: true`, `no-new-privileges: true`), et le chart Helm 9 services est tracé dans `DEVOPS-HELM-01` (`sprint-status.yaml`).

**Given** l'enregistrement de `CAP-180` (et la mise à jour de `CAP-054`/`CAP-080`) dans `docs/product/capabilities.yaml` et des 4 rapports Tech Lead dans `docs/implementation-artifacts/tech-lead-reports/README.md`
**When** toutes les portes CI sont exécutées (`ruff`, `mypy --strict`, `lint-imports`, `lint_spine.py`, `export_openapi.py --check`, `pytest --cov-fail-under=90` + intégration PG18, `pnpm turbo run lint typecheck test`, `pnpm site:sync`, `pnpm site:check`)
**Then** toutes les vérifications passent à `0` erreur sans contournement.

---
