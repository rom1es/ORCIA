# 2026-11-04 — Audit Exhaustif de Câblage Vertical & Persistance Bout-en-Bout des Epics 1 à 7 (`UI ➔ SDK ➔ API ➔ SQL PostgreSQL 18 / Outbox / SeaweedFS / RAG`)

> **Convention de nommage du fichier (Obligatoire — créé AVANT toute modification de code)** :
> - `docs/implementation-artifacts/tech-lead-reports/2026-11-04-audit-et-cablage-vertical-epics-1-a-7-tech-lead-report.md`

- **Date** : 2026-11-04
- **Story / Clé Sprint** : `2026-11-04-audit-et-cablage-vertical-epics-1-a-7` (`Epics 1 à 7` / `Gouvernance Anti-Silos`)
- **Auteur / Contexte** : Audit vertical exhaustif et câblage bout-en-bout (`apps/web` $\rightarrow$ `@orcia/api-client` $\rightarrow$ `apps/api` / `apps/worker` $\rightarrow$ `packages/orcia-core` $\rightarrow$ PostgreSQL 18 / Outbox / SeaweedFS S3 / RAG Hybride) couvrant l'ensemble des Stories `1.1` à `5.4` ainsi que les vues de supervision et FinOps (`Epics 1 à 7`, `AD-1` à `AD-19`, `FR-1` à `FR-33`).
- **Commits associés** : `feat/epics-1-7-vertical-persistence-wiring`

---

## 1. Analyse du Besoin & Étude d'Impact Tech Lead (Pré-Implémentation)

### 1.1 Contexte & Problématique
- **Problème identifié** : Lors des implémentations successives des Epics 1 à 7 (fondations IAM/Catalogue/Broker, Ontologie & RAG Hybride, Orchestration Durable DBOS & Blackboard Append-Only, Gates Palier 1/2/Agentiques/Humaines & Jira/MCP, Notifications/Leases & Control Center, FinOps Roll-Up), plusieurs adaptateurs d'infrastructure réels développés en `Story 3.2b` et `Story 3.2c` dans `packages/orcia-core/src/orcia_core/*/_internal/` sont restés **orphelins des routeurs HTTP FastAPI (`apps/api`) et des workers (`apps/worker`)**, tandis que plusieurs méthodes du SDK `@orcia/api-client` et vues React (`apps/web`) n'appelaient pas encore les routes backend correspondantes.
- **Exigence des 4 Garde-Fous Anti-Silos (`GEMINI.md`)** :
  1. **Zéro Adaptateur SQL/S3/RAG/DBOS Orphelin (Gate GitNexus)** : chaque classe dans `_internal/` (`SqlOrchestrationRepository`, `SqlDomainEventsOutboxRepository`, `DbosSqlAlchemyUnitOfWork`, `DbosDurableWorkflowEngine`, `SqlHybridRagRepository`, `SeaweedFsObjectStorageAdapter`, `LiteLLMAdapter`) doit être ré-exportée proprement par la façade publique de son domaine (`AD-19`) et posséder $\ge 1$ appelant actif dans `apps/api` ou `apps/worker`.
  2. **Test d'Intégration Vertical `HTTP ➔ PostgreSQL 18` (Couche 2 `AD-17`)** : les routes FastAPI doivent persister et relire effectivement dans PostgreSQL 18 (`workflow_runs`, `step_executions`, `blackboard_snapshots`, `domain_events_outbox`, `kb_documents`, `kb_chunks`, `tripartite_trace_edges`) lorsque `session_maker` / `dbos_uow` est attaché à `app.state`.
  3. **Couverture SDK `@orcia/api-client` & Survie au `F5` (`apps/web`)** : exposition de toutes les opérations clientes typées des Epics 1 à 7 dans `@orcia/api-client` et câblage des écrans `/login` et `/finops` avec hydratation `GET` au montage et persistance survivant au démontage/remontage (`unmount()` + `render()`).
  4. **Respect strict des contrats `lint-imports` (`AD-19`) et de la limite de volumétrie (`< 350–400` lignes)**.

### 1.2 Exploration, Analyse d'Impact GitNexus, Factorisation & Dette Technique
- **Analyse d'Impact GitNexus (`gitnexus_impact`, `repo: "ORCIA"`, `direction: "upstream"`) avant intervention** :
  - `SqlOrchestrationRepository` (`packages/orcia-core/src/orcia_core/orchestration/_internal/sql_repository.py`) : `impactedCount = 2` (`orchestration/_internal/__init__.py`, `dbos_engine.py`) — **`0` appelant dans `apps/api` ou `apps/worker`**.
  - `SqlDomainEventsOutboxRepository` (`packages/orcia-core/src/orcia_core/orchestration/_internal/outbox_repository.py`) : `impactedCount = 3` (`orchestration/_internal/*`) — **`0` appelant dans `apps/api` ou `apps/worker`**.
  - `DbosSqlAlchemyUnitOfWork` (`packages/orcia-core/src/orcia_core/orchestration/_internal/uow.py`) : `impactedCount = 5` (`orchestration/_internal/*`) — **`0` appelant dans `apps/api` ou `apps/worker`**.
  - `DbosDurableWorkflowEngine` (`packages/orcia-core/src/orcia_core/orchestration/_internal/dbos_engine.py`) : `impactedCount = 1` (`orchestration/_internal/__init__.py`) — **`0` appelant dans `apps/api` ou `apps/worker`**.
  - `SqlHybridRagRepository` (`packages/orcia-core/src/orcia_core/rag/_internal/sql_repository.py`) : `impactedCount = 1` (`rag/_internal/__init__.py`) — **`0` appelant dans `apps/api`**.
  - `SeaweedFsObjectStorageAdapter` (`packages/orcia-core/src/orcia_core/catalog/_internal/seaweedfs_adapter.py`) : `impactedCount = 0` (`risk: UNKNOWN`) — **totalement orphelin**.
  - `LiteLLMAdapter` (`packages/orcia-core/src/orcia_core/bootstrap/_internal/litellm_adapter.py`) : `impactedCount = 2` (`bootstrap/plugin_registry.py`, `bootstrap/__init__.py`) — **`0` appelant dans `apps/api`**.

- **Matrice d'Audit Exhaustive Couche par Couche (Epics 1 à 7)** :

| Epic / Story | Domaine & Fonctionnalité | UI (`apps/web`) | SDK (`@orcia/api-client`) | Routeur FastAPI (`apps/api/routers/`) | Persistance SQL / S3 / Outbox (`orcia_core`) | Verdict Pré-Fix & Action |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **Epic 1 — Story 1.1** | Coquille Direction C, i18n, Santé `/api/v1/health` | `ShellContainer.tsx` | `getHealth()`, `getShellSummary()` | `health.py`, `shell.py` | Sonde PostgreSQL 18 (`SELECT 1`) | 🟢 Conforme |
| **Epic 1 — Story 1.2** | Auth Bi-Mode (`OIDC` + `Argon2id/TOTP`), Arbre `OrgUnit`, Workspaces & Matrice 5 Permissions | `routes/login.tsx` (validation locale seule), `/settings` IAM | `loginLocal()`, `loginOidc()` présents dans `authAndShell.ts` | `auth.py`, `org_and_workspaces.py` | `DualModeAuthenticationService`, `PermissionMatrixEvaluator` | 🟠 Câbler `routes/login.tsx` sur `loginLocal` / `loginOidc` du SDK |
| **Epic 1 — Story 1.3** | Catalogue Fédéré Multi-Sources, Cache CAS `SHA-256`, Fusion 4 Niveaux & `run-lock.json` | `features/catalog/index.tsx` | `catalogAndPermissions.ts` (`getCatalogState`, `resolveFederatedUri`, `getCasObject`, `mergeFourLayers`) | `catalog.py` (en mémoire uniquement, `SeaweedFsObjectStorageAdapter` non appelé) | `SeaweedFsObjectStorageAdapter` **orphelin** (`impactedCount = 0`) | 🔴 Ré-exporter `SeaweedFsObjectStorageAdapter` dans `orcia_core.catalog` et le câbler dans `routers/catalog.py` (`resolve_federated_uri` + `get_cas_object`) |
| **Epic 1 — Story 1.4** | Exécution Passthrough/SP & Permission Broker IAM | Dock Permission Broker | `catalogAndPermissions.ts` (`evaluatePermissionBrokerAccess`, `replayPermissionBrokerStep`) | `permission_broker.py` | `PermissionBrokerService` | 🟢 Conforme |
| **Epic 1 — Story 1.5** | Workflows Système Jour 0, `ModelRouterService` & `LiteLLMAdapter` | `/settings`, `/wizards` | `bootstrapAndOnboarding.ts` | `bootstrap.py`, `dependencies/core_and_lifespan.py` | `LiteLLMAdapter` / `build_litellm_gateway_plugin` non résolu au démarrage API | 🟠 Câbler `build_litellm_gateway_plugin` / `LiteLLMAdapter` dans `dependencies/core_and_lifespan.py` |
| **Epic 2 — Stories 2.1 & 2.2** | Ontologie 4 Niveaux, Extraction L4 par Branche & Simulateur *What-If* | `features/ontology/index.tsx` | `ontology.ts` (`resolveOntology`, `extractOntologyL4`, `simulateOntologyImpact`, `promoteOntologyConcept`) | `ontology_and_rag.py` | `OntologyFourLayerGoalService` | 🟢 Conforme |
| **Epic 2 — Stories 2.3 & 2.4** | Indexation 3 Régimes, RAG Hybride `halfvec(1024)` + BM25 RRF & Graphe Tripartite | `features/ontology/index.tsx` | `searchHybridRag`, `indexKnowledgeDocument`, `registerTripartiteEdge`, `recordGitPushFreshness` absents du client de domaine unifié | `ontology_and_rag.py` (`SqlHybridRagRepository` non appelé par `/rag/search` ni `/state`) | `SqlHybridRagRepository` **orphelin** (`impactedCount = 1`) | 🔴 Ré-exporter `SqlHybridRagRepository` dans `orcia_core.rag`, le câbler dans `routers/ontology_and_rag.py` et exposer les méthodes dans `@orcia/api-client` |
| **Epic 3 — Stories 3.1, 3.2, 3.2b, 3.2c** | Workflow-as-Code, Moteur Durable DBOS, Blackboard Append-Only & Outbox Transactionnelle | `features/cockpit/index.tsx` | Méthodes d'orchestration et blackboard absentes des clients de domaine | `orchestration.py`, `blackboard_and_engine.py` (en mémoire uniquement, `SqlOrchestrationRepository` & `SqlDomainEventsOutboxRepository` non appelés) | `SqlOrchestrationRepository`, `SqlDomainEventsOutboxRepository`, `DbosSqlAlchemyUnitOfWork`, `DbosDurableWorkflowEngine` **orphelins** | 🔴 Ré-exporter dans `orcia_core.orchestration`, câbler dans `routers/orchestration.py`, `blackboard_and_engine.py`, `challenge_and_replay.py` et `apps/worker` (`outbox_relay.py`, `dbos_workflow_runner.py`) |
| **Epic 3 — Stories 3.3, 3.4, 3.5** | Assistant DAG 5 Nœuds, Ancres Humaines (`#6D28D9`), Arbitrage Tie-Break & Challenge Amont / Replay Step $N$ | `features/inbox/index.tsx`, `features/cockpit/index.tsx` | Méthodes `signHumanAnchor`, `requestHumanArbitration`, `resolveHumanArbitration`, `previewUpstreamChallenge`, `submitUpstreamChallenge`, `replayWorkflowFromStep` à exposer | `blackboard_and_engine.py`, `challenge_and_replay.py`, `assistant.py` | Événements Outbox `HumanArbitrationRequested`, `StepCompleted`, `ArtifactProduced` à persister dans `domain_events_outbox` | 🔴 Câbler la persistance SQL/Outbox via `orchestration_sql_wiring.py` et exposer toutes les méthodes dans `epics1To7Operations.ts` |
| **Epic 4 — Stories 4.1, 4.1a, 4.2, 4.3, 4.4** | Sandbox Palier 1/2, Gates Agentiques 5 Lentilles, Gates Humaines Adaptatives & Actions Jira Staged / MCP | `features/gates/index.tsx`, `features/catalog/index.tsx` | Méthodes Gates (`evaluateDeterministicGate`, `verifyTier2Tdd`, `evaluateAgenticGate`, `evaluateHumanGate`, `decideHumanGateChunk`, `finalizeHumanGate`, Jira/MCP) à exposer | `gates.py`, `human_gates.py`, `jira_and_mcp.py` | `DeterministicGateService`, `AgenticGateService`, `AdaptiveHumanGateService`, `MultiProjectJiraStagedActionService` + Outbox `GateEvaluated` | 🟠 Exposer l'ensemble des méthodes typées dans `epics1To7Operations.ts` et relayer les événements `GateEvaluated` vers `SqlDomainEventsOutboxRepository` quand SQL est actif |
| **Epics 5, 6 & 7 — Stories 5.1 à 5.4 & FinOps** | Inbox Unifiée, Prise en Charge Atomique, Leases Fencing, Control Center `< 1s` & Roll-Up FinOps | `features/finops/index.tsx` (statique par défaut, sans hydratation API ni survie `F5`) | Méthodes `listInboxNotifications`, `claimTaskNotification`, `acquireResourceLeases`, `getControlCenterOverview`, `searchCommandPalette` à exposer | `inbox_and_leases.py`, `control_center.py` | `UnifiedNotificationAndClaimService`, `ResourceLeaseService`, `ControlCenterAndRunSupervisionService` | 🔴 Exposer les méthodes dans `epics1To7Operations.ts` et câbler `features/finops/index.tsx` sur `@orcia/api-client` avec survie au rechargement `F5` |

- **Opportunités de Factorisation & Contrôle de Volumétrie (`< 350–400` lignes)** :
  - `apps/api/src/orcia_api/routers/blackboard_and_engine.py` compte actuellement **446 lignes** (dépassement du seuil de 400 lignes). Nous allons extraire la logique de sérialisation et de synchronisation SQL/Outbox dans un module dédié `apps/api/src/orcia_api/routers/orchestration_sql_wiring.py`, ramenant `blackboard_and_engine.py` sous les **340 lignes** tout en mutualisant le pont transactionnel `FastAPI ➔ SqlOrchestrationRepository / SqlDomainEventsOutboxRepository / DbosDurableWorkflowEngine` entre `orchestration.py`, `blackboard_and_engine.py` et `challenge_and_replay.py`.

---

## 2. Plan d'Implémentation

### 2.1 Schéma de Données & Migrations Alembic (`infra/migrations/versions/`)
- Aucune nouvelle révision Alembic n'est requise : les tables `workflow_runs` (`0010`), `step_executions` et `blackboard_snapshots` (`0011`), `domain_events_outbox` (`0012`), `kb_documents`, `kb_chunks`, `code_graph_edges` (`0008`) et `tripartite_trace_edges` (`0009`) existent déjà et sont protégées par leurs contraintes d'intégrité et triggers PostgreSQL 18 (`BEFORE UPDATE OR DELETE RAISE EXCEPTION` sur `blackboard_snapshots` et `audit_ledger`).
- Le module `orchestration_sql_wiring.py` s'assure que les clés étrangères prérequises (`organizations`, `org_units`, `workspaces`, `workflow_definitions`) sont présentes (ou créées de manière idempotente `ON CONFLICT DO NOTHING`) avant d'invoquer `SqlOrchestrationRepository.upsert_workflow_run`, `upsert_step_execution`, `append_snapshot` et `SqlDomainEventsOutboxRepository.enqueue_event`.

### 2.2 Noyau Métier Hexagonal, Orchestration & Workers (`packages/orcia-core/`, `apps/worker/`)
- **Ré-exports publics conformes `AD-19` (`lint-imports`)** :
  - `packages/orcia-core/src/orcia_core/catalog/__init__.py` : ré-export de `SeaweedFsObjectStorageAdapter`, `SeaweedFsS3HttpBackend`, `build_s3_sigv4_headers`.
  - `packages/orcia-core/src/orcia_core/rag/__init__.py` : ré-export de `SqlHybridRagRepository`.
  - `packages/orcia-core/src/orcia_core/orchestration/__init__.py` : ré-export de `DbosSqlAlchemyUnitOfWork`, `SqlOrchestrationRepository`, `SqlDomainEventsOutboxRepository`, `AsyncSubscriberCallback`, `DbosDurableWorkflowEngine`, `DurableWorkflowRunSummary`.
- **Workers (`apps/worker/src/orcia_worker/`)** :
  - `outbox_relay.py` : ajout de la méthode asynchrone `DramatiqOutboxRelay.relay_sql_pending_batch(uow: DbosSqlAlchemyUnitOfWork, batch_size: int = 50) -> int` qui instancie `SqlDomainEventsOutboxRepository(uow)` et invoque `claim_and_relay_pending_batch(batch_size=batch_size, subscriber_fn=self.event_bus.publish_idempotent_async)`.
  - `dbos_workflow_runner.py` : ajout de `DbosWorkflowRunner.execute_durable_sql_workflow(uow: DbosSqlAlchemyUnitOfWork, ...)` qui instancie et délègue à `DbosDurableWorkflowEngine(uow)`.

### 2.3 Couche Backend API, Sécurité & Contrats (`apps/api/`, `packages/api-client/`)
- **Composition Root & Routeurs FastAPI (`apps/api/src/orcia_api/`)** :
  - `dependencies/core_and_lifespan.py` : câblage de `build_litellm_gateway_plugin` / `LiteLLMAdapter` dans `lifespan` et helper `get_optional_dbos_uow(request)` gérant un `DbosSqlAlchemyUnitOfWork` partagé ou construit à partir de `request.app.state.session_maker`.
  - `routers/catalog.py` : câblage de `SeaweedFsObjectStorageAdapter` dans `resolve_federated_uri` (`put_cas_artifact` lorsque l'adaptateur S3 est attaché à `request.app.state.seaweedfs_storage_adapter`) et dans `get_cas_object` (`get_cas_artifact` en repli/vérification CAS).
  - `routers/ontology_and_rag.py` : câblage de `SqlHybridRagRepository` dans `search_hybrid_rag` (`search_hybrid_rrf` sur PostgreSQL 18 `pgvector halfvec(1024)` + `ts_rank_cd`) et dans `get_ontology_and_rag_state` (`traverse_tripartite_neighborhood` sur `tripartite_trace_edges`).
  - `routers/orchestration_sql_wiring.py` + `routers/orchestration.py`, `routers/blackboard_and_engine.py`, `routers/challenge_and_replay.py` : synchronisation transactionnelle vers `SqlOrchestrationRepository` (`upsert_workflow_run`, `upsert_step_execution`, `append_snapshot`, `update_run_status`, `list_step_executions`, `list_snapshots`) et `SqlDomainEventsOutboxRepository` (`enqueue_event`, `list_events_by_run`), ainsi que `DbosDurableWorkflowEngine` lors du lancement ou replay durable.
- **SDK TypeScript (`packages/api-client/`)** :
  - Création de `packages/api-client/src/domains/epics1To7Operations.ts` exposant les méthodes typées couvrant l'intégralité des routes des Epics 2 à 7 (RAG/Tripartite, Orchestration, Blackboard, Ancres/Arbitrage, Challenge/Replay, Assistant, Gates Déterministes/Palier 2/Agentiques/Humaines, Jira/MCP, Inbox/Leases, Control Center/FinOps).
  - Enregistrement de `createEpics1To7OperationsDomainClient` dans `packages/api-client/src/index.ts`.

### 2.4 Interface Utilisateur & Expérience (`apps/web/`)
- `apps/web/src/routes/login.tsx` : câblage de `onSubmitLocal` et `onTriggerOidc` sur `apiClient.loginLocal(...)` et `apiClient.loginOidc(...)` via `@orcia/api-client`, avec persistance du jeton de session pour la survie au `F5` et repli déterministe hors-ligne pour les tests unitaires.
- `apps/web/src/features/finops/index.tsx` : hydratation automatique au montage via `apiClient.getControlCenterOverview(...)` et synchronisation persistante permettant d'afficher et de conserver après rechargement (`F5` : `unmount()` + `render()`) le roll-up FinOps multi-runs par périmètre (`GLOBAL | BU | TEAM | WORKSPACE`).

---

## 3. Bilan des Modifications & Résultats (Post-Implémentation)

### 3.1 Fichiers Créés ou Modifiés
| Fichier | Nature | Rôle & Responsabilité |
|---|---|---|
| `packages/orcia-core/src/orcia_core/bootstrap/__init__.py` | Modifié | Ré-export public de `LiteLLMAdapter` et `build_litellm_gateway_plugin` (`AD-19`). |
| `packages/orcia-core/src/orcia_core/catalog/__init__.py` | Modifié | Ré-export public de `SeaweedFsObjectStorageAdapter`, `SeaweedFsS3HttpBackend`, `build_s3_sigv4_headers` (`AD-19`). |
| `packages/orcia-core/src/orcia_core/rag/__init__.py` | Modifié | Ré-export public de `SqlHybridRagRepository` (`AD-19`). |
| `packages/orcia-core/src/orcia_core/orchestration/__init__.py` | Modifié | Ré-export public de `DbosSqlAlchemyUnitOfWork`, `SqlOrchestrationRepository`, `SqlDomainEventsOutboxRepository`, `AsyncSubscriberCallback`, `DbosDurableWorkflowEngine`, `DurableWorkflowRunSummary` (`AD-19`). |
| `apps/api/src/orcia_api/dependencies/core_and_lifespan.py` | Modifié | Câblage de `LiteLLMAdapter` et `build_litellm_gateway_plugin` dans `_resolve_default_llm_gateway()` (`ORCIA_LLM_GATEWAY=litellm`). |
| `apps/api/src/orcia_api/routers/catalog.py` | Modifié | Câblage de `SeaweedFsObjectStorageAdapter` (`put_bytes`, `get_bytes`) et `SeaweedFsS3HttpBackend` dans `resolve_federated_uri` et `get_cas_object`. |
| `apps/api/src/orcia_api/routers/ontology_and_rag.py` | Modifié | Câblage de `SqlHybridRagRepository` (`search_hybrid_rrf`, `traverse_tripartite_neighborhood`) dans `search_hybrid_rag` et `get_ontology_and_rag_state`. |
| `apps/api/src/orcia_api/routers/orchestration_sql_wiring.py` | Créé | Pont transactionnel SQL/Outbox/DBOS (`SqlOrchestrationRepository`, `SqlDomainEventsOutboxRepository`, `DbosSqlAlchemyUnitOfWork`, `DbosDurableWorkflowEngine`) et sérialiseurs extraits de `blackboard_and_engine.py`. |
| `apps/api/src/orcia_api/routers/orchestration.py` | Modifié | Câblage de `sync_instantiated_run_to_sql` lors de `POST /api/v1/orchestration/runs/instantiate`. |
| `apps/api/src/orcia_api/routers/blackboard_and_engine.py` | Modifié | Réduction de **446 à 316 lignes** (`< 350` lignes) et câblage de `read_sql_blackboard_if_available`, `sync_step_execution_and_snapshot_to_sql` et `sync_arbitration_request_to_sql`. |
| `apps/api/src/orcia_api/routers/challenge_and_replay.py` | Modifié | Câblage de `sync_replay_fork_to_sql` (`DbosDurableWorkflowEngine.persist_step_and_commit_snapshot`) lors de `POST /api/v1/orchestration/runs/replay`. |
| `apps/worker/src/orcia_worker/outbox_relay.py` | Modifié | Ajout de `DramatiqOutboxRelay.relay_sql_pending_batch` et `DbosOutboxRelay.relay_sql_pending_batch` consommant `SqlDomainEventsOutboxRepository.claim_and_relay_pending_batch` (`FOR UPDATE SKIP LOCKED`). |
| `apps/worker/src/orcia_worker/dbos_workflow_runner.py` | Modifié | Ajout de `execute_durable_sql_workflow` orchestrant `DbosDurableWorkflowEngine` et `SqlOrchestrationRepository`. |
| `packages/api-client/src/helpers.ts` | Modifié | Extension de `createRequestJson` aux verbes HTTP `"GET" | "POST" | "PUT" | "PATCH" | "DELETE"`. |
| `packages/api-client/src/domains/epics1To7Operations.ts` | Créé | 44 méthodes SDK typées couvrant l'intégralité des routes des Epics 2 à 7 (`ontology-rag`, `orchestration`, `assistant`, `gates`, `jira-mcp`, `inbox`, `resource-leases`, `control-center`). |
| `packages/api-client/src/index.ts` | Modifié | Enregistrement de `createEpics1To7OperationsDomainClient` dans `createOrciaApiClient`. |
| `packages/api-client/src/__tests__/client.test.ts` | Modifié | Ajout du test unitaire couvrant les 44 opérations des Epics 2 à 7. |
| `apps/web/src/routes/login.tsx` | Modifié | Câblage de `@orcia/api-client` (`getMe`, `loginOidc`, `loginLocal`) et persistance `localStorage` pour la survie au `F5`. |
| `apps/web/src/features/finops/index.tsx` | Modifié | Hydratation via `apiClient.getControlCenterOverview({ scopeType: "GLOBAL" })` et persistance `localStorage` pour la survie au `F5`. |
| `tests/unit/test_epics_1_7_vertical_wiring.py` | Créé | Tests unitaires vérifiant les ré-exports `AD-19`, le câblage `SeaweedFsObjectStorageAdapter` sur `/api/v1/catalog/resolve` & `/api/v1/cas/{sha256}`, et `LiteLLMAdapter`. |
| `tests/integration/test_epics_1_7_vertical_sql_wiring_postgres18.py` | Créé | Test d'intégration vertical `HTTP FastAPI ➔ PostgreSQL 18 (testcontainers pgvector:pg18)` validant l'instanciation de run, l'exécution d'étape, les snapshots Blackboard, le relai Outbox SQL (`SKIP LOCKED`), la recherche RAG hybride `halfvec(1024)` + `ts_rank_cd` RRF et la traversée récursive tripartite. |

### 3.2 Métriques Chiffrées & Validation des 5 Couches de Tests (`AD-17`)
- **Qualité Statique Python** :
  - `.venv/bin/ruff check .` : **0 erreur** (`All checks passed!`)
  - `.venv/bin/ruff format --check .` : **499 fichiers formatés** (`0 diff`)
  - `.venv/bin/mypy --strict packages/orcia-kernel packages/orcia-core apps/api apps/worker` : **0 erreur** sur **204 fichiers sources**
  - `.venv/bin/lint-imports` : **5 contrats respectés, 0 brisé** (`257 files, 1469 dependencies`)
  - `lint_spine.py` : `{"ok": true, "total_findings": 0}`
- **Couche 1 (`AD-17`) — Tests Unitaires Python & TypeScript** :
  - `tests/unit/test_epics_1_7_vertical_wiring.py` : **2 passed**
  - `pnpm turbo run lint typecheck test --force` : **9/9 tâches réussies** (`@orcia/api-client`: **9 tests passed**, `@orcia/ui`: **13 fichiers / 41 tests passed**, `@orcia/web`: **14 tests passed**).
- **Couche 2 (`AD-17`) — Test d'Intégration Vertical `HTTP FastAPI ➔ PostgreSQL 18` (`testcontainers`)** :
  - `tests/integration/test_epics_1_7_vertical_sql_wiring_postgres18.py` : **1 passed** sur conteneur réel `pgvector/pgvector:pg18` (27 migrations Alembic `0001` $\rightarrow$ `0027`, scripts de backfill `00` $\rightarrow$ `06`, requêtes HTTP `/api/v1/orchestration/runs/instantiate`, `/anchors/sign`, `/steps/execute`, `/blackboard`, `/api/v1/ontology-rag/rag/search`, `/state` et vérification `SELECT` directe sur `workflow_runs`, `blackboard_snapshots` et `domain_events_outbox` + relai `DramatiqOutboxRelay.relay_sql_pending_batch`).

### 3.3 Bilan d'Impact GitNexus Post-Implémentation (`npx gitnexus analyze`)
- Index rafraîchi : **15 340 nœuds | 25 608 arêtes | 229 clusters | 964 flux**.
- **Preuve d'élimination des adaptateurs SQL/S3/LLM orphelins (`direction: "upstream"`, hors `tests/`)** :
  - `SqlOrchestrationRepository` (`upsert_workflow_run`, `upsert_step_execution`, `append_snapshot`, `list_snapshots`) : appelé par `apps/api/src/orcia_api/routers/orchestration_sql_wiring.py` et `apps/worker/src/orcia_worker/dbos_workflow_runner.py` (`impactedCount: 3` classes + méthodes actives dans `apps/api` et `apps/worker`).
  - `SqlDomainEventsOutboxRepository.claim_and_relay_pending_batch` : appelé par `DramatiqOutboxRelay.relay_sql_pending_batch` et `DbosOutboxRelay.relay_sql_pending_batch` dans `apps/worker/src/orcia_worker/outbox_relay.py` (`impactedCount: 2`).
  - `DbosSqlAlchemyUnitOfWork` : `impactedCount: 6` (dont `orcia_core.orchestration`, `orchestration_sql_wiring.py`, `outbox_relay.py`, `dbos_workflow_runner.py`).
  - `DbosDurableWorkflowEngine.persist_step_and_commit_snapshot` : appelé par `sync_replay_fork_to_sql` (`apps/api/src/orcia_api/routers/orchestration_sql_wiring.py`) et `execute_durable_sql_workflow` (`apps/worker/src/orcia_worker/dbos_workflow_runner.py`).
  - `SqlHybridRagRepository.search_hybrid_rrf` & `traverse_tripartite_neighborhood` : appelés par `search_hybrid_rag` et `get_ontology_and_rag_state` dans `apps/api/src/orcia_api/routers/ontology_and_rag.py` (`impactedCount: 1` chacun dans `Routers`).
  - `SeaweedFsObjectStorageAdapter` (`put_bytes`, `get_bytes`) : appelé par `_get_optional_seaweedfs_adapter`, `resolve_federated_uri` et `get_cas_object` dans `apps/api/src/orcia_api/routers/catalog.py`.
  - `LiteLLMAdapter` & `build_litellm_gateway_plugin` : appelés par `_resolve_default_llm_gateway` dans `apps/api/src/orcia_api/dependencies/core_and_lifespan.py`.
- `gitnexus_detect_changes({scope: "all"})` : **18 fichiers modifiés, 54 symboles touchés**, `0` dépendance circulaire.
