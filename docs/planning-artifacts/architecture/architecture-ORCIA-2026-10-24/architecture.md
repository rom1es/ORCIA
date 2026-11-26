---
title: "Document d'Architecture Système — ORCIA (MVP)"
project: "ORCIA — Orchestration of Processes, Context, and Intelligent Agents"
author: "Winston (System Architect — BMAD)"
status: "final"
date: "2026-10-24"
spine_ref: "docs/planning-artifacts/architecture/architecture-ORCIA-2026-10-24/ARCHITECTURE-SPINE.md"
prd_ref: "docs/planning-artifacts/prds/prd-ORCIA-2026-10-24/prd.md"
ux_design_ref: "docs/planning-artifacts/ux-designs/ux-ORCIA-2026-10-24/DESIGN.md"
ux_experience_ref: "docs/planning-artifacts/ux-designs/ux-ORCIA-2026-10-24/EXPERIENCE.md"
visual_blueprint_ref: "docs/planning-artifacts/architecture/architecture-ORCIA-2026-10-24/visual-architecture-blueprint.html"
---

# Document d'Architecture Système — ORCIA (MVP)

## 1. Vue d'Ensemble & Principes Directeurs

**ORCIA** (*Orchestration of Processes, Context, and Intelligent Agents*) est une plateforme d'exécution de processus complexes assistés par agents IA qui applique le paradigme **« Human-Led, Agent-Accelerated »**.

L'architecture système d'ORCIA est conçue pour garantir simultanément :
1. **La souveraineté cognitive de l'humain** : Application stricte côté serveur des *Ancres Humaines* (`human_authored_required: true`), de l'*Arbitrage Humain* face à toute ambiguïté (`WAITING_FOR_HUMAN_ARBITRATION`), de l'exécution bimodale (*Coaching* interactif ou *Fast-Path* avec conversion automatique des `[ASSUMPTION]` en arbitrages humains), du *Briefing de Revue* en 4 blocs et de la *Validation par Découpage* (`AD-3`, `AD-11`, `AD-13`).
2. **La reproductibilité déterministe et l'auditabilité** : Fédération pure d'URI (`db://`, `git://`, `nexus://`, URI internes `orcia://` et import natif de packs BMAD) avec surcharge déclarative à 3 niveaux (`Base → Workspace → Utilisateur`), épinglage cryptographique dans `run-lock.json`, cache local *Content-Addressable* (`CAS SHA-256`), séparation entre brouillon d'étape (`step_executions.draft_artifact_jsonb`), mémoire de décision structurée (`step_memlog_jsonb`) et snapshots `JSONB` immuables du *Blackboard* (`blackboard_snapshots`) permettant un *Replay* ciblé sans perte d'historique, et journal d'audit append-only (`AD-2`, `AD-5`, `AD-12`, `AD-14`).
3. **La rigueur épistémique et sémantique** : *Ontologie* dynamique à 4 niveaux résolue dans PostgreSQL (avec isolation des termes éphémères L4 par lignée de snapshots actifs), RAG hybride (`pgvector` + BM25) filtré par empreinte de version avec détection d'obsolescence `[STALE_WARNING]`, et *Orthogonalité des Modèles* + *DAG de Lentilles d'Évaluation* aux *Gates Agentiques* (`AD-7`, `AD-8`, `AD-10`).
4. **La réactivité multi-utilisateurs temps réel (`< 500ms`)** : *Boîte de Notifications Unifiée* (personnelle et d'équipe), verrous atomiques unifiés par exécution d'étape (`lock:step:<step_execution_id>`) via Redis et Server-Sent Events (SSE), et séparation stricte entre *Consultation seule* (`READ_ONLY_OBSERVER`) et *Contributeur* (`CONTRIBUTOR_ACTION_REQUIRED`) (`AD-4`).

---

## 2. Paradigme Architectural & Topologie C4

### 2.1. Monolithe Modulaire Hexagonal dans un Monorepo Hybride (`AD-1`, `AD-19`)

Pour combiner l'excellence ergonomique de l'écosystème React moderne avec la puissance native de l'écosystème IA/Data Python, ORCIA repose sur un **Monorepo Hybride TypeScript + Python** gouverné par un workspace **`uv 0.13.5`** à **4 packages** (`packages/orcia-kernel`, `packages/orcia-core`, `apps/api`, `apps/worker`) et un graphe de dépendances acyclique (`apps -> orchestration -> domaines -> kernel`) vérifié en CI par **`import-linter 2.3.0`** :

- **Frontend SPA Pure (`apps/web`)** : **Vite 6.3.5 + TanStack Router 1.120.4 (SPA pure servie par `nginx:alpine`, React 19.1.0, TypeScript 5.9.3)** + **Tailwind CSS 4.3.0** + **shadcn/ui (Radix 1.1.2)** + **TanStack Query 5.69.0** + **Zustand 5.0.3** + **`@xyflow/react` 12.12.0**, organisé par fonctionnalité métier (`apps/web/src/features/<domaine>/` — `M11`). Aucun serveur Node.js/RSC/Middleware n'est exposé en production : `apps/web` agit exclusivement comme bundle statique de rendu et de routage typé (`validateSearch` Zod + loaders `QueryClient`) consommant `apps/api`. Implémente la Direction C (*Executive Slate Sidebar* `#0F172A` à 7 modules RBAC + *Crisp Light Workspace* `#F8FAFC` + *Agent Assistant Dock*) sur Desktop et le compagnon Mobile restreint.
- **Contrat d'Interface (`packages/api-client`)** : Généré automatiquement à partir du schéma **OpenAPI 3.1** exposé par `apps/api/src/orcia_api/schemas/` via `openapi-typescript` (`7.6.1`) et consommé avec `openapi-fetch` (`0.13.4`). Aucune définition manuelle de DTO n'est tolérée côté frontend (`0-diff` gate en CI).
- **Backend Synchrone & Temps Réel (`apps/api` — Package `uv` #3)** : **FastAPI 0.162.0 (Python 3.12.9, Pydantic 2.14.1, SQLAlchemy 2.1.6 + `asyncpg` 0.30.0, orjson 3.13.0)** avec point d'assemblage unique (*Composition Root* dans `lifespan` $\rightarrow$ `app.state` + `Depends()`, zéro singleton en mémoire créé au chargement des modules — `M5`), contrats HTTP dans `orcia_api/schemas/` (`M4`) et registre déclaratif `error_code -> HTTP RFC 9457`. Gère les requêtes REST, l'authentification OIDC/Locale, le contrôle RBAC/ABAC, l'accès sécurisé en streaming aux objets du cache CAS (`/api/v1/cas/<sha256>`), les verrous de présence atomiques et le flux **Server-Sent Events (SSE)** `/api/v1/events/stream`, instrumentés par **OpenTelemetry 1.31.0**.
- **Orchestration Durable Transactionnelle, Relais Outbox & Workers Asynchrones (`apps/worker` — Package `uv` #4)** :
  - **DBOS Transact (`dbos 2.14.0`, licence MIT)** adossé nativement à **PostgreSQL 18** (`@DBOS.workflow()`, `@DBOS.step()`, `DBOS.recv()`, `DBOS.sleep()`, `@DBOS.scheduled()`, `DBOS.fork_workflow()`, `SetWorkflowID`) pour l'exécution durable, les attentes d'arbitrage humain de plusieurs semaines, la déduplication transactionnelle des déclencheurs, les sous-workflows imbriqués (`nesting_depth <= 3`) et le *Replay* déterministe à partir de l'étape $N$.
  - **Dramatiq (`2.2.1`)** adossé à **Redis 7.4.2** pour le délestage asynchrone lourd hors chemin critique (`Docling 2.142.1` dans le rôle `worker-indexing`, indexation RAG en masse).
- **Socle Fondamental Pur (`packages/orcia-kernel` — Package `uv` #1) & Domaines Métier Encapsulés (`packages/orcia-core` — Package `uv` #2)** :
  - `packages/orcia-kernel` contient les identifiants UUIDv7 (`uuid-utils 1.1.0`), les énumérations partagées (`WorkflowExecutionRegime`, `WorkflowStepType`), la classe de base `OrciaDomainError`, l'enveloppe `DomainEvent` et les ports `Protocol` transverses (`BlackboardPort`, `LLMPort`, `ObjectStoragePort`, `SandboxPort`), avec **zéro dépendance externe**.
  - `packages/orcia-core` regroupe les domaines métier (`orchestration`, `blackboard`, `catalog` avec plugins `entry_points`, `ontology`, `rag`, `gates`, `permissions`, `audit_finops`, `bootstrap`). Chaque domaine expose uniquement sa façade publique dans `__init__.py`, déclare ses erreurs dans `<domaine>/errors.py` et isole son implémentation dans `_internal/`, sous le contrôle strict d'**`import-linter 2.3.0`** (`AD-19`).

### 2.2. Diagramme C4 des Conteneurs (5 Rôles Opérationnels — `AD-19`)

```mermaid
flowchart TB
    subgraph Clients["Clients Utilisateurs"]
        Desktop["Navigateur Desktop (Cockpit Complet 7 Modules)"]
        Mobile["Navigateur Mobile Companion (Triage, Briefing, Arbitrage)"]
    end

    subgraph Monorepo["ORCIA Platform (Monorepo Hybride — uv 4 packages + pnpm)"]
        Web["apps/web\nVite 6.3 + TanStack Router 1.120 SPA + React 19.1 + Tailwind 4.3"]
        API["apps/api (Rôle 1: api)\nFastAPI + lifespan/Depends + orcia_api/schemas + SSE + OTel\n(Python 3.12.9)"]
        WorkerOrch["apps/worker (Rôles 2 & 4: worker-orchestration & trigger-dispatcher)\nDBOS Transact 2.14 (Workflows Durables PG18) + Outbox Relay"]
        WorkerIdx["apps/worker (Rôle 3: worker-indexing)\nDramatiq 2.2 + Docling 2.142 + tree-sitter 0.24 (CPU/RAM isolés)"]
        Sandbox["infra/sandbox (Rôle 5: sandbox-runner — AD-9 & AD-19)\nProcessus isolé MCP : Palier 1 Wasmtime-py 27.0 (< 5s / 256MB)\nPalier 2 gVisor runsc / Podman Rootless (< 60s / 1024MB, --network=none)"]
    end

    subgraph DataStores["Couche de Persistance Unifiée (Schéma public unique)"]
        PG[("PostgreSQL 18.0 + pgvector 0.8.7\nRelationnel + Checkpoints DBOS + Outbox + JSONB + CTE Ontologie\n+ HNSW halfvec(1024) + BM25 tsvector GIN + Audit")]
        Redis[("Redis 7.4.2\nVerrous SET NX (< 500ms)\n+ Pub/Sub SSE + Files Dramatiq")]
        CAS[("Stockage Objet S3 v4 (ObjectStoragePort)\nSeaweedFS 3.85 (Apache-2.0) / S3 Managé\nCache CAS Immuable (cas/<sha256>)")]
    end

    subgraph External["Systèmes Fédérés & Fournisseurs LLM"]
        Git["Dépôts git:// (GitLab / GitHub / Packs BMAD)"]
        Nexus["Registres nexus:// (Artefacts / Skills)"]
        ExtDB["Bases db:// (Schémas & Vues Métier)"]
        LLMs["Passerelle LiteLLM 1.106.2\n(Familles Modèles A, B, C orthogonales)"]
        IdP["Fournisseur d'Identité OIDC / SSO"]
    end

    Desktop -->|HTTPS + SSE| Web
    Mobile -->|HTTPS + SSE| Web
    Web -->|REST OpenAPI 3.1 + SSE| API
    API -->|Auth OIDC| IdP
    API -->|SQLAlchemy Async + DBOS Client| PG
    API -->|Streaming sécurisé /api/v1/cas/*| CAS
    API -->|SET NX Locks + Pub/Sub + Enqueue| Redis
    Redis -->|Dequeue Heavy Indexing Jobs| WorkerIdx
    PG <-->|Checkpoints DBOS & Outbox| WorkerOrch
    PG <-->|Chunks & Vecteurs RAG| WorkerIdx
    WorkerOrch -->|Publie événements SSE| Redis
    WorkerOrch -->|Lecture/Écriture CAS S3 v4| CAS
    WorkerOrch -->|MCP / gRPC Local| Sandbox
    WorkerOrch -->|Résolution Fédérée (entry_points)| Git
    WorkerOrch -->|Résolution Fédérée (entry_points)| Nexus
    WorkerOrch -->|Résolution Fédérée (entry_points)| ExtDB
    WorkerOrch -->|Exécuteur ≠ Évaluateur| LLMs
```

---

## 3. Conception Détaillée des 8 Domaines (`packages/orcia-core`)

### 3.1. Moteur d'Orchestration Durable Transactionnel (`DBOS Transact`), Hydratation JIT, Exécution Bimodale & *Replay* (`orchestration` & `blackboard` — `AD-2`, `AD-3`, `AD-13`)

ORCIA écarte à la fois la lourdeur opérationnelle d'un cluster externe dédié (Temporal) et la fragilité d'un moteur de workflow réimplémenté manuellement au-dessus de Dramatiq au profit de **DBOS Transact (`dbos 2.18.0`, licence MIT)** adossé nativement à **PostgreSQL 18**, complété par **Dramatiq** pour les travaux d'arrière-plan hors chemin critique :

1. **Exécution Durable Transactionnelle sur PostgreSQL 18 (`DBOS Transact`, `AD-2`)** :
   - Chaque *Workflow Run* est exécuté comme un workflow durable `@DBOS.workflow()` et chaque étape comme une transaction journalisée `@DBOS.step()`.
   - Les pauses d'arbitrage humain (`WAITING_FOR_HUMAN_ARBITRATION`), d'ancre humaine (`PENDING_HUMAN_ANCHOR`) ou d'habilitation (`WAITING_FOR_PERMISSION`) utilisent `DBOS.recv(topic, timeout_seconds)` sans consommer de thread ni de worker actif, même sur plusieurs semaines.
   - Les déclencheurs planifiés utilisent `@DBOS.scheduled()`, l'idempotence des déclencheurs s'appuie sur `SetWorkflowID("<trigger_id>:<idempotency_key>")`, et le *Rewind / Replay* (`FR-16`) exploite `DBOS.fork_workflow(workflow_id, start_step)` couplé au marquage `SUPERSEDED` des `blackboard_snapshots` avals.

2. **Hydratation *Just-In-Time* par Étape et *Step Memlog* (`AD-13`)** :
   - **Isolation contre le *Context Rot*** : Lors de l'exécution d'une étape $k$, le `JitStepHydrator` ne fournit à l'*Agent Exécuteur* que le contrat d'instructions de l'étape $k$ et les artefacts amont explicitement déclarés (`orcia://...`), jamais les instructions des étapes futures $k+1 \dots N$.
   - **Séparation Livrable / Mémoire de Décision (`step_memlog_jsonb`)** : Chaque étape maintient un journal structuré append-only (hypothèses écartées, compromis étudiés, arbitrages retenus) séparé du livrable propre (`draft_artifact_jsonb`). Ce *Step Memlog* permet de reprendre une étape interrompue sans perte de contexte et alimente directement la génération du **Briefing de Revue en 4 blocs** (`FR-4`).

3. **Exécution Bimodale (*Coaching Path* vs *Fast-Path / Tâche de Fond*) (`AD-13`, `UJ-10`)** :
   - Une fois les sections `human_authored_required: true` initiales signées (`PENDING_HUMAN_ANCHOR` $\rightarrow$ `READY_FOR_EXECUTION`), le contributeur choisit le mode d'exécution :
     - **Mode Coaching (Interactif)** : L'agent progresse par passes courtes et suspend immédiatement l'étape en `WAITING_FOR_HUMAN_ARBITRATION` (`DBOS.recv`) dès qu'une décision ouverte ($\ge 2$ options) se présente.
     - **Mode Fast-Path / Tâche de Fond (`BACKGROUND_AUDIT`)** : Idéal pour les audits lourds en arrière-plan (comme la comparaison Documentation vs Codebase d'Arthur dans `UJ-10`). Les étapes durables DBOS s'enchaînent sans bloquer sur les ambiguïtés intermédiaires : chaque choix non tranché ou écart détecté est consigné dans `step_memlog_jsonb` avec une balise structurée (`[ASSUMPTION]`, `[BUG_CODE_SUSPECTED]`, `[DOC_OBSOLETE_SUSPECTED]`). En fin de *Run*, tous ces points sont consolidés dans le rapport final en unités de **Validation par Découpage** et d'**Arbitrage Humain (`FR-5`)**, et l'utilisateur reçoit une notification SSE temps réel (`< 500ms`) pour trancher.

4. **Arbre de Snapshots Immuables et *Replay* Ciblé (`FR-6`, `AD-2`)** :
   - Tant qu'une étape est en cours, le brouillon vit dans `step_executions.draft_artifact_jsonb`. Ce n'est qu'au statut `COMMITTED` qu'un nouveau `BlackboardSnapshot` immuable est scellé dans `blackboard_snapshots`.
   - Lors d'un retour arrière (*Rewind*) de l'Étape 3 vers l'Étape 1 suivi d'un *Replay* (`DBOS.fork_workflow`), les snapshots `#101`, `#102`, `#103` passent au statut `SUPERSEDED` (conservés intégralement pour la piste d'audit `FR-23`), et une nouvelle branche `ACTIVE` `#104 -> #105 -> #106` est créée avec calcul de différentiel (*diff*) pour ne re-valider aux étapes intermédiaires que les sections impactées.

```mermaid
stateDiagram-v2
    [*] --> PENDING_HUMAN_ANCHOR: Step has human_authored_required
    [*] --> READY_FOR_EXECUTION: No prior human anchor required
    PENDING_HUMAN_ANCHOR --> READY_FOR_EXECUTION: Human submits signed anchors (FR-2)
    READY_FOR_EXECUTION --> EXECUTING_AGENT: Worker claims job (Coaching or Fast-Path)
    EXECUTING_AGENT --> WAITING_FOR_HUMAN_ARBITRATION: Ambiguity >= 2 options or Fast-Path [ASSUMPTION] extracted (FR-3, AD-13)
    WAITING_FOR_HUMAN_ARBITRATION --> EXECUTING_AGENT: Human selects option in Tie-Break Matrix
    EXECUTING_AGENT --> WAITING_FOR_PERMISSION: 401/403 intercepted by Permission Broker (FR-27)
    WAITING_FOR_PERMISSION --> EXECUTING_AGENT: Permission granted + Replay Step clicked
    EXECUTING_AGENT --> PAUSED_BUDGET_EXCEEDED: Step or Run max_cost_usd reached (AD-12)
    PAUSED_BUDGET_EXCEEDED --> EXECUTING_AGENT: Budget override approved
    EXECUTING_AGENT --> EVALUATING_GATES: Draft saved in draft_artifact_jsonb + step_memlog_jsonb
    EVALUATING_GATES --> EXECUTING_AGENT: Gate rejected (retry <= max_agent_retries)
    EVALUATING_GATES --> PAUSED_MAX_RETRIES: Retries > max_agent_retries (AD-12)
    PAUSED_MAX_RETRIES --> EXECUTING_AGENT: Human guidance or manual edit
    EVALUATING_GATES --> WAITING_FOR_UPSTREAM_RESOLUTION: Upstream Challenge raised (FR-6)
    WAITING_FOR_UPSTREAM_RESOLUTION --> READY_FOR_EXECUTION: Tripartite arbitration + Rewind/Replay
    EVALUATING_GATES --> COMMITTED: All Gates PASS + Sealed in blackboard_snapshots
    COMMITTED --> [*]
```

---

### 3.2. Temps Réel (`< 500ms`), Boîte Unifiée & Verrous de Présence Unifiés (`sse` & `inbox` — `AD-4`)

Pour répondre au parcours `UJ-4` (Nadia et son équipe gérant de multiples workflows simultanés), ORCIA implémente une architecture temps réel légère et résiliente aux proxys d'entreprise :

1. **Verrouillage Atomique Unifié sur `step_execution_id` (*Claim / Lock*)** :
   - La clé canonique de verrouillage dans Redis est `lock:step:{step_execution_id}`.
   - Lorsqu'un membre d'une équipe clique sur **« Prendre en charge »** dans la *Boîte de Notifications Unifiée* (`POST /api/v1/tasks/{task_id}/claim`) ou ouvre directement l'étape dans le *Cockpit* (`POST /api/v1/runs/{run_id}/steps/{step_id}/claim`), FastAPI exécute atomiquement `SET lock:step:{step_execution_id} {user_id} NX EX 900`, met à jour `claimed_by_user_id` dans PostgreSQL et publie immédiatement l'événement `task.claim.locked` sur Redis Pub/Sub (`channel:workspace:{ws_id}`).
   - Tous les clients connectés au flux SSE `/api/v1/events/stream` reçoivent l'événement en `< 100ms` (budget NFR `< 500ms`), mettant à jour le badge `🔒 En cours : Nadia K.` sans rechargement.
   - Le middleware `RunAccessGuard` vérifie en $O(1)$ la détention de `lock:step:{step_execution_id}` sans jointure SQL supplémentaire.

2. **Séparation Stricte `READ_ONLY_OBSERVER` vs `CONTRIBUTOR_ACTION_REQUIRED` (`FR-8`)** :
   - Le middleware FastAPI `RunAccessGuard` calcule les droits effectifs `(user_id, run_id, step_execution_id)`.
   - Si le mode est `READ_ONLY_OBSERVER`, tout appel `POST/PUT/PATCH/DELETE` de mutation sur l'étape ou l'artefact est rejeté avec `HTTP 403 ERR_OBSERVER_MODE_READ_ONLY`, et l'interface web désactive les contrôles d'édition et de *Gate* tout en affichant le bandeau ambre d'observation.

---

### 3.3. Catalogue Fédéré, Connecteurs (`confluence://`, `jira://`), Surcharge 3 Niveaux, Adaptateur BMAD & *Permission Broker* (`catalog` & `permissions` — `AD-5`, `AD-6`, `AD-14`)

#### 3.3.1. Résolution d'URI Externe/Interne, Actions Jira Gouvernées, Surcharge Déclarative et Épinglage `run-lock.json`
ORCIA ne duplique jamais les sources tierces dans sa base de définition : il agit comme un **plan de contrôle fédéré**.
- **Ressources externes (`db://`, `git://`, `nexus://`, `confluence://`, `jira://`) & Port `ObjectStoragePort` (`AD-5`)** : Au démarrage d'un *Run*, le `FederatedUriResolver` résout la référence symbolique (ex. `@v2.1.0`, la révision `page.version.number` d'une page Confluence `confluence://<space_key>/<page_id>`, ou l'état courant d'un ticket/filtre Jira `jira://<project_key>/<issue_key>`) vers sa révision immuable, télécharge le contenu, calcule son empreinte `SHA-256`, et le stocke via le port hexagonal `ObjectStoragePort` (compatible S3 v4, adossé par défaut à **SeaweedFS 4.17 `Apache-2.0`** en dev/CI/on-prem et à AWS S3 / GCS / Scaleway S3 en cloud managé, en remplacement de MinIO AGPL-3.0 archivé en 2026) sous la clé immuable `cas/<sha256>`.
- **Actions et Transitions de Workflows Jira Staged aux Gates (`AD-5`, `AD-6`)** : Les agents exécuteurs peuvent créer des tickets (`create_issue`), les mettre à jour (`update_issue`), les commenter (`add_comment`) et faire avancer les workflows Jira (`transition_issue` après interrogation préalable de `GET /rest/api/3/issue/{key}/transitions` pour valider les transitions autorisées et les champs obligatoires de l'écran de transition). Afin d'éviter toute pollution du backlog Jira par des hallucinations, ces mutations sont préparées sous forme d'**Actions Staged** dans `step_executions.draft_artifact_jsonb` (révisables unitairement via la *Validation par Découpage* `FR-6`) et ne sont exécutées sur Jira qu'une fois la *Gate* de l'étape validée (`AD-11`), en inscrivant le lien de provenance `run-lock.json` dans le ticket Jira. En sens inverse, les **Webhooks Jira (`jira:issue_updated`)** peuvent déclencher un *Run* ou réveiller une étape en pause (`UJ-3`).
- **Surcharge Déclarative à 3 Niveaux (`AD-14`)** : Inspiré du `customize.toml` de BMAD, tout workflow ou agent du catalogue est résolu en fusionnant **`1. Base (URI Catalogue) → 2. Surcharge Workspace/Équipe → 3. Préférences Profil Utilisateur`** sans jamais dupliquer le workflow de base.
- **Adaptateur Natif de Packs BMAD (`BmadSkillPackAdapter`, `AD-14`)** : ORCIA peut importer directement un répertoire de skills BMAD (`SKILL.md` + `customize.toml` + `steps/*.md`) depuis `git://` ou `nexus://` et l'exécuter comme un workflow ORCIA natif doté des *Gates*, de l'*Ontologie* et du *Blackboard*.
- **Protocole MCP Bidirectionnel — Client & Serveur IDE Gouverné (`/api/v1/mcp`, `FR-24`, `AD-6`)** : Outre le client MCP permettant aux workers d'invoquer des serveurs MCP externes, ORCIA expose un **Serveur MCP gouverné (`/api/v1/mcp`)** pour les IDE (VS Code, Cursor, Claude Code, Antigravity). Les développeurs et architectes peuvent ainsi interroger l'*Ontologie active (N1..N4)*, la *Base de Connaissances*, le *Catalogue Fédéré* et le *Blackboard du Run courant* depuis leur éditeur en mode *Passthrough*, sous le contrôle du *Permission Broker* et avec blocage matériel de toute écriture IA sur les *Ancrages Humains* (`AD-3`).
- **Ressources internes inter-étapes (`orcia://`)** : Lorsqu'une étape $N$ consomme un livrable produit par une étape amont $M < N$, elle le référence via l'URI canonique `orcia://runs/{run_id}/steps/{step_key}/artifacts/{artifact_key}`, résolue de manière déterministe depuis la branche `ACTIVE` de `blackboard_snapshots`.

#### 3.3.2. Résolution de `OQ-1` (Authentification Passthrough vs Service Principal) et `OQ-2` (*Permission Broker*)

```mermaid
sequenceDiagram
    autonumber
    actor User as Utilisateur (Ex. Yanis)
    participant Web as apps/web (Cockpit)
    participant API as apps/api (FastAPI + SSE)
    participant PG as PostgreSQL 18 (DBOS Transact)
    participant Worker as apps/worker (DBOS Step)
    participant Broker as PermissionBrokerService
    participant Git as Dépôt Externe (git://)
    participant CAS as Cache CAS S3 (SeaweedFS / S3)

    User->>Web: Lance l'Étape 2 du Workflow
    Web->>API: POST /api/v1/runs/{id}/steps/{step}/execute
    API->>PG: Démarre/Reprend @DBOS.workflow (avec User Context)
    PG->>Worker: Exécute @DBOS.step
    Worker->>Git: Résolution URI git://corp/sec-templates@v1 (Mode Passthrough)
    alt Accès Autorisé (200 OK)
        Git-->>Worker: Contenu de la ressource
        Worker->>CAS: Écriture immuable cas/<sha256> + Mise à jour run-lock.json
        Worker-->>API: Publie événement SSE (run.step.progress)
        API-->>Web: SSE run.step.progress (Exécution Agent)
    else Accès Refusé (401/403 ou Droit EXECUTE manquant)
        Git-->>Worker: HTTP 403 Forbidden
        Worker->>Broker: intercept_access_denied(user, uri, error)
        Broker->>Broker: Recherche motif URI dans la KB d'Habilitations (YAML/MD)
        Broker->>PG: Persiste WAITING_FOR_PERMISSION (DBOS.recv) + Publie run.step.paused
        API-->>Web: SSE run.step.paused (Permission Broker Card)
        Web-->>User: Affiche : Rôle requis, Approbateur, Lien IAM pré-rempli & bouton "Rejouer l'étape"
    end
```

---

### 3.4. Ontologie Dynamique à 4 Niveaux, Simulation d'Impact (*What-If*) & RAG Hybride (`ontology` & `rag` — `AD-7`, `AD-8`)

#### 3.4.1. Modèle Relationnel-Graphe à 4 Niveaux et Simulation d'Impact (`ImpactSimulatorService`) dans PostgreSQL 18
Les concepts (`ontology_concepts`), relations typées (`ontology_relations`) et axiomes formels (`ontology_axioms`) sont stockés dans PostgreSQL avec 4 niveaux de visibilité (`1_ENTERPRISE`, `2_DOMAIN`, `3_WORKSPACE`, `4_RUN_EPHEMERAL`).
- La résolution de l'ontologie active d'un *Run* utilise une requête CTE SQL prenant par priorité `4 -> 3 -> 2 -> 1`, en filtrant les concepts `4_RUN_EPHEMERAL` pour n'inclure que ceux appartenant à la lignée de snapshots `ACTIVE` de l'étape courante (`introduced_in_snapshot_id`).
- Lors d'un **Challenge Amont (`FR-7`)** ou d'une promotion/modification d'un concept d'ontologie (`FR-9`), le `ImpactSimulatorService` exécute une traversée de graphe (CTE sur `ontology_relations` et dépendances `orcia://` de `blackboard_snapshots`) pour afficher un **Aperçu de Simulation d'Impact (*What-If Impact Preview*)** listant exactement les *Steps*, *Artefacts* et *Workflows* impactés avant validation.

#### 3.4.2. Indexation Différenciée Incrémentale Multi-Sources, Vecteurs `halfvec(1024)` Réels (`EmbeddingPort`, `AD-24`) + Recherche Lexicale Native PostgreSQL 18 (`tsvector` + `GIN` + `ts_rank_cd` + RRF `k=60`) & Alerte `[STALE_WARNING]` (`FR-23`, `AD-8`, `AD-24`)
Pour garantir des réponses en `< 50ms` sans dupliquer l'intégralité du SI, sans dépendance AGPL-3.0 ni restriction sur les réplicas de lecture (l'extension ParadeDB `pg_search` étant explicitement écartée pour le MVP au profit du moteur natif PostgreSQL 18), `packages/orcia-core/rag` applique **3 régimes d'indexation incrémentale** adossés au port hexagonal d'embeddings réels **`EmbeddingPort` (`AD-24`)** (zéro hachage SHA-256 en production, dimension stricte 1024). Les vecteurs sont stockés en **`halfvec(1024)` (FP16)** dans `pgvector 0.8.7` HNSW et fusionnés par *Reciprocal Rank Fusion (`RRF`, `k=60`)* avec l'index lexical natif PostgreSQL 18 **`tsvector` + index `GIN` + `ts_rank_cd` pondéré (`A`: titre/identifiant/clé Jira/symbole AST, `B`: en-tête contextuel, `C`: corps, `D`: métadonnées)** complété par `pg_trgm` :
1. **Documentation, Multi-Espaces Confluence & Multi-Projets Jira de Référence (`1..N confluence://`, `1..N jira://`, Markdown, PDF, OpenAPI via `Docling`)** : Ingestion Confluence sélective sur chacun des espaces dédiés du *Workspace* gouvernée par `space_key`, page racine et labels (`orcia-kb`, exclusion des pages `draft`/`archived`), et **indexation hybride sur chacun des projets Jira du *Workspace*** (seuls les tickets porteurs de connaissance durable — *Epics, User Stories, Bugs résolus avec Root Cause, Post-mortems* filtrés par JQL dans `init-datasource` — sont vectorisés en **1 chunk unifié (`256-1024` tokens)** préfixé par son *Contextual Header* `[Projet > Epic > Clé | Type | Statut | Composants | Versions]`, tandis que le suivi opérationnel temps réel multi-projets est interrogé en direct via l'API JQL en mode *Passthrough*). Découpage hiérarchique *Parent-Child* pour les documents longs (**chunk enfant `256-512` tokens** portant le vecteur `halfvec(1024)` $\rightarrow$ **chunk parent `1024-2048` tokens** injecté à l'agent). Les adaptateurs HTTPX d'`EmbeddingPort` supportent `gemini_native` (`:batchEmbedContents` + `output_dimensionality=1024`), `openai_compatible` (`dimensions=1024` quand supporté), et Ollama (`/v1/embeddings` ou `/api/embed` ; ancien `/api/embeddings` banni), Anthropic étant exclu. En l'absence de modèle d'embedding actif configuré au niveau `GLOBAL` dans le Hub (`AD-24` amendé Epic 25, y compris au Jour 0 après `pnpm db:reset`), l'ajout (`POST /datasources`), la mise à jour (`PATCH /datasources`) et l'ingestion des sources documentaires/RAG (`source_nature != 'SOURCE_CODE'`) sont bloqués dès la validation avec émission du code harmonisé `ERR_NO_ACTIVE_EMBEDDING_MODEL` (`HTTP 422`, aucun chunk vectoriel ni index BM25 inséré), et la recherche/indexation RAG directe est bloquée avec `ERR_NO_ACTIVE_EMBEDDING_MODEL` ; en revanche, `Mon Assistant` reste opérationnel dès qu'un modèle `chat` actif est configuré (mode conversationnel + Rôle/Casquette + Glossaire/Ontologie SQL sans `pgvector`, avec notice non bloquante signalant l'inactivité de la recherche documentaire et lien vers `/settings/ai-models`). Toute mise à jour du modèle d'embedding global déclenche une réindexation asynchrone (`rag_reindexing_jobs`, masquée côté UI tant que `0` document est indexé) pendant laquelle la recherche RAG directe renvoie `HTTP 503 ERR_RAG_REINDEX_IN_PROGRESS` avec progression sans aucun mode dégradé lexical ou Vitesse 1, et les nouvelles ingestions documentaires sont mises en file d'attente, tandis que `Mon Assistant` demeure disponible en mode conversationnel avec bannière non bloquante de réindexation en cours.
2. **Multi-Codebases (`1..N git://` via `tree-sitter 0.24.0`) & Graphe Tripartite Multi-Sources (`Confluence ↔ Jira ↔ Git`)** : Découpage syntaxique strict par symbole AST (**`150-800` tokens** par fonction/classe/modèle Pydantic) sur l'ensemble des dépôts `git://` dédiés au *Workspace*, couplé à l'extraction d'un *Code Property Graph* inter-dépôts (`DEFINES`, `CALLS`, `IMPORTS`, `IMPLEMENTS_CONCEPT`, `TESTED_BY`) et à la détection automatique des clés de tous les projets Jira liés (`[A-Z][A-Z0-9]+-[0-9]+`) dans les commits/PR, les pages de tous les espaces Confluence et les liens d'issues pour alimenter un **Graphe Tripartite de Traçabilité unifié à l'échelle du Workspace (`DOCUMENTS`, `SPECIFIES`, `FIXES`, `IMPLEMENTS_ISSUE`, `BLOCKS`, `AFFECTS_CONCEPT`)** avec traversée CTE bornée (`depth <= 2`). Les chunks de Code Graph (Epic 18, GitNexus) restent hors périmètre des embeddings (`embedding = NULL`) et ne sont jamais bloqués par l'absence de modèle d'embedding.
3. **Bases de Données (`db://`)** : Indexation **exclusive du schéma DDL et de son mapping Ontologique** (zéro ligne transactionnelle dans le RAG).
Chaque requête est filtrée sur le `kb_snapshot_hash` de `run-lock.json`, avec brique explicite `data-freshness` et injection automatique de `[STALE_WARNING]` en cas de dépassement de `freshness_ttl_days` ou de contradiction avec le code.

---

### 3.5. Pipeline Tri-Modal des Gates, Sandbox Bimodale à 2 Paliers (`AD-9`), Pseudonymisation PII Réversible, Orthogonalité & DAG de Lentilles (`gates` — `AD-9`, `AD-10`, `AD-11`)

1. **Sandbox Déterministe Bimodale à 2 Paliers de Budget (`AD-9`)** :
   - **Palier 1 — Validation Rapide de Schémas & Règles Pures (`Wasmtime 27.0.0`, `< 5s`, `256 Mo RAM`, zéro réseau)** : Exécute les validateurs JSON Schema, OpenAPI, axiomes d'ontologie et règles de *Pattern Drift* compilables en WASM sans dépendre des *user namespaces* Linux de l'hôte Kubernetes.
   - **Palier 2 — Analyse Statique, Linters, Compilateurs & Tests Unitaires d'Auto-Remédiation (`gVisor runsc` en Kubernetes / Conteneur Rootless éphémère `Podman/Docker --network=none --read-only`, `< 60s`, `1024 Mo RAM`)** : Exécute les outils natifs (`ruff`, `mypy`, `tsc`, `eslint`, `pytest`, `vitest`) et la boucle TDD `Red -> Green` de `UJ-12` dans un conteneur éphémère isolé monté uniquement sur le snapshot CAS en lecture seule et un `/tmp` en `tmpfs`.

2. **Pseudonymisation PII Réversible, Orthogonalité & DAG de Lentilles (`AD-10`, `AD-11`)** :
   - **Pseudonymisation PII Réversible (`PiiReversibleScrubber`, `NFR-SEC-2`)** : Avant tout appel vers un fournisseur LLM Cloud externe, les données personnelles ou secrets métiers identifiés sont remplacés par des jetons déterministes réversibles (stockés en Redis sur la durée du `run_id`) et ré-hydratés localement au retour.
   - **Orthogonalité & DAG de Lentilles d'Évaluation** (via **LiteLLM** sur une famille de modèle distincte de l'exécuteur et sans sa *Chain-of-Thought*) :
     1. **Lentilles Indépendantes Parallèles** :
        - *Lentille 1 — Alignement Transverse Étape 1* (vérifie la conformité directe vis-à-vis du PRD / Architecture de fondation).
        - *Lentille 2 — Vérification Atomique de Faits (`fact_verification`)* : décompose l'artefact en assertions factuelles atomiques et les confronte à l'*Ontologie (N1..N4)* et aux *Bases de Connaissances* épinglées avec un score de confiance (`0..1`) par assertion.
        - *Lentille 3 — Attaque Adversariale & Edge-Cases* (recherche les contradictions d'interfaces et cas limites omis).
        - *Lentille 4 — Conformité Domaine & Sécurité* (vérifie les règles métier et RGPD).
     2. **Lentille Dépendante (`after`)** :
        - *Lentille 5 — Synthèse & Briefing* : consolide les trouvailles des lentilles parallèles (`lens_findings_jsonb`), intègre le `step_memlog_jsonb`, calcule le score global `agentic_score` et structure le **Briefing de Revue en 4 blocs** pour la *Gate Humaine Adaptative* (`AD-11`).

---

### 3.6. Architecture de l'Agent Assistant : Workflow de Nœuds type n8n, `AssistantHarness` & Prompt à 5 Couches (`AD-15`)

L'*Agent Assistant* est conçu comme un **Workflow Système de Nœuds orientés (DAG type n8n)** enregistré dans le *Catalogue Fédéré* (`orcia://system/workflows/assistant-agent`) et éditable visuellement dans l'UI via **`@xyflow/react` (`12.12.0`)** ou en manifeste YAML :

1. **Graphe de Nœuds de l'Assistant (Exécution visible en temps réel via SSE)** :
   - **Nœud 1 — Routeur d'Intention & Désambiguïsation** : Analyse la question de l'humain et l'Ontologie active (Niveaux 1 à 4). Si l'intention est ambiguë, sollicite une clarification immédiate ; sinon, achemine vers le planificateur.
   - **Nœud 2 — Planificateur de Recherche (`Query Planner & Ontology Expander`)** : Décompose la question en sous-requêtes typées et enrichit les termes via les synonymes de l'Ontologie.
   - **Nœud 3 — Fan-Out Parallèle de Recherche** : Exécute simultanément les branches pertinentes : (3A) *RAG Hybride + vérification `[STALE_WARNING]`*, (3B) *Catalogue Fédéré filtré RBAC*, (3C) *Inspection du Blackboard & Step Memlog du Run actif*, et (3D) *Permission Broker*.
   - **Nœud 4 — Tri Critique & Vérification d'Axiomes** : Écarte les résultats hors-sujet, vérifie la cohérence avec les axiomes de l'Ontologie et prépare les preuves citées.
   - **Nœud 5 — Synthétiseur Adaptatif au *Profil Humain* & Compositeur de Workflow** : Formate la réponse selon le profil de l'utilisateur (`FR-15`), génère les cartes d'action interactives du Dock, et permet d'assembler ou d'ajuster conversationnellement un manifeste **Workflow-as-Code** à partir des briques du *Catalogue Fédéré* puis de l'enregistrer et le lancer en tâche de fond (`UJ-10`, `FR-11`).

2. **Encapsulation par le `AssistantHarness` et Prompt Modulaire à 5 Couches** :
   - Le `AssistantHarness` injecte de manière déterministe le contexte de l'écran actif (`active_module`, `run_id`, `step_id`, `access_mode`, `human_profile`), impose l'identité `passthrough` de l'utilisateur et bloque matériellement toute tentative d'écriture directe sur une *Ancre Humaine* (`human_authored_required: true`).
   - Pour chaque nœud, le Harness compile un prompt structuré en **5 couches** :
     1. **Couche 1 — Constitution Immuable du Harness** *(verrouillée en code Python, non modifiable par surcharge)* : philosophie *Human-Led*, interdiction de pré-remplir les *Ancres Humaines*, obligation de signaler `[STALE_WARNING]`, respect du mode `READ_ONLY_OBSERVER`.
     2. **Couche 2 — Directive & Contrat Pydantic du Nœud Actif**.
     3. **Couche 3 — Surcharges Déclaratives (`Base → Team → Workspace → User`, `AD-14`)**.
     4. **Couche 4 — Profil Humain (`FR-15`) & Ontologie Active (`AD-7`)**.
     5. **Couche 5 — Contexte Éphémère du Cockpit & Résultats des Nœuds Amont**.

#### 3.6.3. Unified Assistant Turn Engine, Canonical REST v2 & SSE v2 Contract (`AD-25`, Epic 26)

Per `AD-25`, the three historical assistant execution paths converge into a single `AssistantTurnEngine` in `packages/orcia-core` executing fixed, non-overridable constitutional phases (`N1 IntentGuard -> N2 Planner & Ontology -> N3 Pre-fetch / Tool Loop -> N4 Server EvidenceTable -> N5 Synthesis (AssistantPromptBuilder) -> CitationGuard`):

- **Dual Execution Speeds & "Deepen" Flow (`D1`, `R3`):**
  - **Speed 1 (`SPEED_1_FAST`):** Single-shot fast-path with bounded `< 50 ms` hybrid RAG pre-fetch (preserving `AD-24.6` optional embedding decoupling when `0` active `embedding` models are configured), direct SSE streaming, and post-first-byte PG18 session persistence (`TTFT p95 < 1.2 s`). Emits deterministic `low_evidence: bool` on `turn_completed` when the server `EvidenceTable` is empty; zero pre-LLM auto-escalation. The UI exposes a **"Deepen"** action after Speed 1 (when `supports_tools=true`, highlighted on `low_evidence=true`) that launches a linked Speed 2 turn carrying `parent_turn_id`.
  - **Speed 2 / Speed 3 (`SPEED_2_AGENT_TOOLS`, `SPEED_3_DEEP_AUDIT`):** Run on the `ASSISTANT` profile of `NonDeterministicReflexiveRuntime` with bounded iteration/token/wall-clock budgets, tool invocations routed exclusively through `GovernedAssistantToolRouter` (`PermissionBroker -> V5/human-anchor guard -> sandboxed executor (asyncio.wait_for) -> secret scrubber -> audit_ledger + domain_events_outbox`), `ConnectorReflexiveWriteGateAdapter` barred, and `PROCESS` profile defaults left unchanged.
- **Single-Process Hosting & Redis Streams Reattachment (`D2`, `R1`):**
  - All speeds (`1`, `2`, `3`) execute inside `apps/api` in bounded, tracked `asyncio.Task` handles (`add_done_callback`) with `SIGTERM` graceful drain capped by the profile wall-clock budget; **no Dramatiq worker** handles assistant turns.
  - Redis backs the `(workspace_id, user_id, turn_id)` registry, cursor-reattachable Redis Streams event buffer, `stop` coordination signals, thread turn locks (`SET lock:thread:{thread_id} NX EX ...`), sliding-window rate limits & per-user concurrency semaphores, and a refreshed task liveness key (`TTL`). On reattach after a brutal pod crash, expired liveness emits terminal `stream_error` with `ERR_ASSISTANT_TURN_INTERRUPTED` (RFC 9457 + `trace_id`, no automatic retry).
- **3 Preserved Text Adapters & 2 Native Tool Dialects (`D5`, `R7`) + SSRF (`D3`, `R8`):**
  - `LlmStreamingPort` (`orcia_core/ports/`) preserves all 3 `httpx` text/reasoning streaming adapters (`openai_compatible`, `anthropic`, `gemini_native` `CAP-076` with strict `thinking`/`content` separation). Native `tool_calls` streaming/non-streaming parsing and re-injection is scoped strictly to `openai_compatible` (`delta.tool_calls`) and `anthropic` (`tool_use` / `input_json_delta`); `gemini_native` REST and non-`/v1` Ollama default to `supports_tools=false` (`HTTP 422 ERR_MODEL_TOOLS_UNSUPPORTED` on Speed 2/3, UI disabled, `ACTION_ITEM-26.4`).
  - Ops env var `ORCIA_LLM_ALLOWED_PRIVATE_HOSTS` (`localhost` allowed only in `local`/`test`) + connection-time `getaddrinfo` DNS pinning protect all Hub save/discovery/test/runtime calls (`AD-21` Rule 7). Public Day-0 `GET /api/v1/bootstrap/platform-setup-state` returns only `{is_initialized, step}`.
- **Direct Cutover & Deferred Scope (`R2`, `R4`, `R5`, `R6`):**
  - Mode B graphical studio is deferred (`ACTION_ITEM-26.1`); only Mode A 3-level overrides (`TEAM -> WORKSPACE -> USER` in `workspace_customization_overrides`) are active. No Redis assembled-prompt cache is built upfront (`R6`, measure-first under `ACTION_ITEM-26.3`). Atomic cutover in `26.7` switches backend, `apps/web`, and E2E specs directly to `/api/v1/assistant/turns*` with zero `/three-speed/*` facade (`ACTION_ITEM-26.2`, `R4`).

1. **Canonical REST v2 Contract (`/api/v1/assistant/*` & MCP `assistant.ask`):**

   | Method & Path | Pre-Stream Guards & Status | Request / Response Semantics |
   | :--- | :--- | :--- |
   | `POST /api/v1/assistant/turns` | `ScopeAccessGuard` (UUID + slug), `403 ERR_OBSERVER_MODE_READ_ONLY`, `422 ERR_MODEL_TOOLS_UNSUPPORTED` (when `supports_tools=false` on Speed 2/3), `429` Redis rate-limit/concurrency, `409` Redis thread turn lock (`ERR_THREAD_TURN_LOCK_HELD`) | Returns `202 Accepted` `{turn_id, thread_id, workspace_id, parent_turn_id, speed, status, stream_url}`. Server resolves `READ_SOURCE` & `CONFIDENTIAL_RESTRICTED` masking (`reader_allowed_source_uris` removed), enforces immutable Layer 1, accepts optional `parent_turn_id` for **"Deepen"** (Speed 1 -> Speed 2), and starts bounded `asyncio.Task` writing to Redis Streams. |
   | `GET /api/v1/assistant/turns/{turn_id}/stream?after=<cursor>` | Authenticated user + `ScopeAccessGuard` matching turn owner/workspace | Returns `200 OK` `text/event-stream`. Replays and live-tails Redis Streams entries strictly after `<cursor>` (`F5` & multi-worker safe). Checks Redis liveness key; emits `stream_error` `ERR_ASSISTANT_TURN_INTERRUPTED` if pod died mid-turn. |
   | `GET /api/v1/assistant/turns/active` | Authenticated user + `ScopeAccessGuard` | Returns `200 OK` list of active turns for `(workspace_id, user_id)` from the Redis turn registry for `F5` stream reattachment. |
   | `POST /api/v1/assistant/turns/{turn_id}/stop` | `ScopeAccessGuard` + `403 ERR_OBSERVER_MODE_READ_ONLY` | Publishes Redis `stop` signal across workers, drains bounded cancellation, flushes partial FinOps usage to `audit_ledger` / `domain_events_outbox` in `finally`, releases thread lock, and emits `turn_stopped`. |
   | `POST /api/v1/assistant/turns/{turn_id}/approve` | `ScopeAccessGuard` + `403 ERR_OBSERVER_MODE_READ_ONLY` | Approves an `approval_required` proposal via `CONTINUE_IN_PROCESS` into durable DBOS + PG18 (`AD-2`), enforcing `WAITING_FOR_HUMAN_ANCHOR` (`AD-3`, `HTTP 422 ERR_HUMAN_ANCHOR_REQUIRED`). |
   | `POST /api/v1/assistant/turns/{turn_id}/synthesize-now` | `ScopeAccessGuard` + `403 ERR_OBSERVER_MODE_READ_ONLY` | Signals Speed 2/3 `NonDeterministicReflexiveRuntime` (`ASSISTANT` profile) to halt `N3` tool iterations and transition immediately to `N4 Server EvidenceTable -> N5 Synthesis -> CitationGuard` (`202 Accepted`). |
   | `POST /api/v1/assistant/turns/{turn_id}/feedback` | `ScopeAccessGuard` + `403 ERR_OBSERVER_MODE_READ_ONLY` | Idempotent `UNIQUE (turn_id, user_id)` upsert into `assistant_turn_feedback` (`rating IN ('up', 'down')`, optional `reason_code`, `comment`). |
   | `GET /api/v1/assistant/threads/{thread_id}/messages` | `ScopeAccessGuard` + `READ_SOURCE` membership | Returns `200 OK` ordered `assistant_thread_messages` (`role IN ('user', 'assistant')`, `citation_map`, `turn_id`, `parent_turn_id`, `token_count`, `created_at`). Zero `role: "tool"` messages exposed or re-injected. |
   | `POST /api/v1/mcp/spaces/{workspace_slug}/invoke` (`assistant.ask`) | 7 MCP hardware locks, `QuotaGuard`, `ScopeAccessGuard`, server-side `READ_SOURCE` / `CONFIDENTIAL_RESTRICTED` | Executes synchronously via `AssistantTurnEngine` Speed 1 read-only governed mode (`AssistantPromptBuilder` + `CitationGuard`; zero SI writes, zero recursive tool loop). |

2. **Canonical SSE v2 Wire Format & 9 Event Types:**
   Every SSE frame emits `id: <redis_stream_id>`, `event: <type>`, and `data: <JSON>` where `data` always includes `turn_id`, `seq` (monotonically increasing per turn), `timestamp` (UTC ISO-8601), and `trace_id` (W3C OpenTelemetry):

   | Event Type | Phase | Required Payload Fields & Semantics |
   | :--- | :---: | :--- |
   | `thinking_delta` | `N3` / `N5` | `delta_text` — Incremental reasoning tokens from separated thinking channel (`thinking` / `reasoning_content` / `<think>`), never merged into `content`. |
   | `tool_call` | `N3` | `tool_call_id`, `tool_name`, `sanitized_args`, `iteration` — Emitted when `GovernedAssistantToolRouter` begins a governed tool call (`OpenAI-compatible` or `Anthropic` native dialect). |
   | `tool_result` | `N3` | `tool_call_id`, `tool_name`, `status` (`ok \| denied \| error`), `summary`, `evidence_refs`, `audit_event_id` — Secret-scrubbed result summary recorded after `audit_ledger` persistence. |
   | `approval_required` | `N1` / `N3` | `proposal_id`, `action_kind`, `target_uri`, `workflow_ref`, `requires_human_anchor: true` — Emitted when an action requires `CONTINUE_IN_PROCESS` via DBOS + PG18 Gate instead of direct SI write (`V5` / `AD-3`). |
   | `token_delta` | `N5` | `delta_text` — Incremental answer markdown tokens emitted verbatim from real `aiter_lines()` streaming (newlines and code indentation preserved). |
   | `citation_map` | `CitationGuard` | `citations` (`[S1]/[G1]/[O1]` -> `{label, source_uri, authority_tier, freshness, stale_warning, excerpt_verified}`), `purged_phantom_count` — Emitted by server `CitationGuard` strictly **before** `turn_completed`; purged phantom labels are logged to `audit_ledger` (`ASSISTANT_PHANTOM_CITATION_PURGED`). |
   | `turn_completed` | Terminal | `message_id`, `low_evidence` (`bool`, true when server `EvidenceTable` is empty), `supports_tools` (`bool`), `usage` (`{input_tokens, output_tokens, cost_usd, usage_source}`) — Signals clean completion and drives UI **"Deepen"** highlight. |
   | `turn_stopped` | Terminal | `stopped_by_user_id`, `partial_usage` (`{input_tokens, output_tokens, cost_usd}`) — Signals graceful cancellation after partial FinOps ledger write. |
   | `stream_error` | Terminal | RFC 9457 Problem Details envelope (`type`, `title`, `status`, `detail`, `instance`, `error_code`, `trace_id`) plus `turn_id`, `seq`, `timestamp` — Explicitly covers `ERR_ASSISTANT_TURN_INTERRUPTED` (expired pod liveness key) and `HTTP 422 ERR_MODEL_TOOLS_UNSUPPORTED` (`supports_tools=false` on Speed 2/3). |

---

### 3.7. Processus d'Initialisation & Auto-Amorçage Gouverné (`orcia://system/bootstrap/*` — `AD-16`, `FR-28`)

Pour éliminer le problème du démarrage à froid (*Cold-Start* au Jour 0) et empêcher toute configuration incomplète en production, ORCIA s'initialise lui-même à travers **6 Workflows Système pré-embarqués (`orcia://system/bootstrap/*`)** exécutés sous le contrôle de *Gates Déterministes* :

1. **`init-organization` (Initialisation d'une Organisation / Tenant — Jour 0)** :
   - Configure l'authentification primaire bi-mode (**SSO d'Entreprise `OIDC / OAuth 2.1`** et/ou **Authentification Locale autonome `Argon2id + TOTP`**) et le mapping des groupes vers les rôles RBAC.
   - **Gate Déterministe d'Orthogonalité (`AD-10`, `AD-24` amendé Epic 25)** : Refuse de valider l'initialisation complète tant qu'au moins **2 familles de modèles distinctes** (chat/raisonnement) ne sont pas validées par test de connexion réel (`AD-10`) ; le modèle d'**embedding sémantique** (`EmbeddingPort`, dim 1024, `AD-24`) demeure quant à lui strictement requis avant tout rattachement ou synchronisation de source documentaire/RAG (`source_nature != 'SOURCE_CODE'`, `FR-23`) et toute recherche vectorielle directe (`FR-18`, `FR-31`), sans bloquer `Mon Assistant` en mode conversationnel seul.
   - Amorce l'*Ontologie* Niveau 1 (Entreprise) par extraction assistée sur les documents fondateurs et validation par découpage du Steward, puis charge le catalogue socle (Agent Assistant + pack BMAD).
2. **`init-workspace` (Initialisation & Onboarding Autonome d'une Équipe et de ses Workspaces Solutions par le Chef d'Équipe `TEAM_LEAD`)** :
   - Exécutable en autonomie par un **Chef d'Équipe (`TEAM_LEAD` / `Workspace Admin`)** sans solliciter un Administrateur Plateforme.
   - Permet de structurer l'équipe (et d'éventuelles sous-équipes dans l'arbre `org_units`), d'inviter ou d'affecter ses membres (par recherche OIDC ou lien d'invitation signé en mode local), de pré-assigner à chaque membre son **Profil Humain** (`PM/Métier`, `Architecte`, `Tech Lead`, `Développeur`, `SecOps`, `Direction`) et ses rôles d'exécution (`CONTRIBUTOR`, `GATE_REVIEWER`, `ONTOLOGY_STEWARD_L3`, `OBSERVER`), de définir les standards d'équipe (`TEAM`) et l'*Ontologie* `3_TEAM`, puis de créer **un ou plusieurs `Workspaces` (solutions logicielles)** rattachés à l'équipe avec leur surcharge `WORKSPACE` (`AD-14`), leur *Boîte de Notifications* (`FR-2`) et leur *Ontologie* `3_WORKSPACE`.
3. **`init-datasource` (Enrôlement Multi-Sources `N × git://`, `N × jira://`, `N × confluence://`, `db://`, `nexus://` ou KB)** :
   - Exécutable à plusieurs reprises par un Administrateur Plateforme ou par le **Chef d'Équipe (`TEAM_LEAD`)** au sein d'un `Workspace` solution (ou en portée `SHARED_TEAM`) pour connecter **plusieurs dépôts `git://`, plusieurs projets/filtres `jira://` et plusieurs espaces/arborescences `confluence://`** dédiés à la solution logicielle (chacun qualifié par un `alias` et un `role` logique, ex. `git:backend`, `git:frontend`, `jira:product`, `jira:secops`, `confluence:specs`, `confluence:adr`).
   - Teste la résolution d'URI et le hachage `SHA-256` dans le cache CAS (`ObjectStoragePort`).
   - **Gate Déterministe du *Permission Broker* (`AD-6`) & de Fraîcheur (`AD-8`)** : Bloque la publication de chaque source dans le catalogue tant que le propriétaire n'a pas signé comme *Ancre Humaine* sa fiche d'habilitation YAML/Markdown (groupe IAM ou rôle Jira requis, approbateur, lien de demande, SLA) et défini son `freshness_ttl_days`.
4. **`init-existing-project` (Adoption d'un Projet Existant — *Brownfield Onboarding*)** :
   - Analyse l'ensemble des dépôts `git://` existants rattachés à un `Workspace` pour extraire la stack, les conventions et l'architecture implicite afin de générer un `ARCHITECTURE-SPINE.md` initial (`[ADOPTED]`) servant de référence aux contrôles de *Pattern Drift* (`FR-17`).
5. **`init-skill` (Enrôlement & Certification d'un Nouveau *Skill* ou MCP)** :
   - Exécute le *Skill* candidat dans la sandbox isolée (`AD-9`, Palier 1 `< 5s / 256MB` ou Palier 2 `< 60s / 1024MB`, `--network=none`) sur un jeu de test avant de l'épingler au catalogue.
6. **`init-user` (Onboarding Express d'un Nouvel Utilisateur au 1er Login)** :
   - Déclenché automatiquement à la première connexion d'un membre invité par son **Chef d'Équipe (`TEAM_LEAD`)** : confirme ou affine le *Profil Humain* pré-assigné (`FR-1`), lie ses comptes externes (**Atlassian Jira/Confluence** et **GitLab/GitHub** via OAuth 2.0 `3LO` ou `PAT` chiffré AES-256-GCM) pour le mode *Passthrough*, vérifie ses accès et l'abonne aux Workspaces et flux de son équipe.

---

### 3.8. Exécution Autonome sous Contrat, Déclencheurs Événementiels Idempotents, Boucle Fermée d'Auto-Remédiation & Imbrication Fractale (`AD-18`, `FR-29`, `FR-30`, `UJ-11`, `UJ-12`)

1. **Régime Autonome sous Contrat (`AUTONOMOUS_CONTRACT`) & Classification de Criticité** :
   - Chaque *Workflow* déclare sa criticité (`LOW_NON_CRITICAL | STANDARD | HIGH_CRITICAL`), son régime d'exécution (`INTERACTIVE_COACHING | BACKGROUND_FAST_PATH | AUTONOMOUS_CONTRACT`) et sa politique de départage sans humain (`tie_break_policy: ONTOLOGY_AXIOM_FIRST | DEFER_AND_CONTINUE_WITH_ASSUMPTION | PAUSE_AND_ESCALATE`).
   - Les workflows `HIGH_CRITICAL` sont formellement interdits d'exécution autonome de bout en bout (`HTTP 422 ERR_CRITICAL_WORKFLOW_REQUIRES_HUMAN_GATE`).
   - Tout passage en `AUTONOMOUS_CONTRACT` exige un **Contrat d'Autonomie** signé dans `human_anchor_signatures` par le `TEAM_LEAD` (et par un `SECOPS` en cas d'utilisation d'un `service_principal`).

2. **Déclencheurs Événementiels Idempotents (`workflow_triggers` + `DBOS SetWorkflowID`) & Protection Anti-Boucle (*Self-Trigger Guard*)** :
   - Les *Workflow Runs* autonomes peuvent être instanciés par un humain en mode *Fire-and-Forget* (`MANUAL_AUTONOMOUS`), par un **Webhook entrant** (`WEBHOOK` : Jira, Git, Confluence ou générique signé HMAC-SHA256), par une **Alerte de Puits de Logs** (`LOG_SINK_ALERT`, `UJ-12`, dont la détection d'anomalies, le calcul de l'empreinte `error_fingerprint_sha256` et la déduplication temporelle sont assurés côté ORCIA via le port découplé `LogSinkQueryPort`, `AD-23`), ou par une **Tâche Planifiée** (`CRON` via `@DBOS.scheduled`, `UJ-11`).
   - La contrainte PostgreSQL `UNIQUE (trigger_id, trigger_idempotency_key)` combinée à `DBOS SetWorkflowID("<trigger_id>:<idempotency_key>")` et au verrou Redis `SET lock:trigger:{trigger_id}:{idempotency_key} NX EX 86400` garantit qu'un même événement (ou un *retry*) ne crée jamais deux *Runs* concurrents.
   - Le filtre **Self-Trigger Guard** ignore tout événement émis par le `service_principal` d'ORCIA ou portant l'en-tête `x-orcia-origin-run-id`.

3. **Boucle Fermée d'Auto-Remédiation (`UJ-12`) & Vérification Post-Action (`POST_ACTION_VERIFICATION`)** :
   - Lorsqu'un workflow autonome corrige une anomalie applicative ou d'infrastructure suite à une alerte de logs (`LOG_SINK_ALERT`), le moteur impose : (a) un diagnostic avec `root_cause_confidence >= 0.90` (sinon escalade en ticket Jira), (b) la génération préalable d'une *Intention de Remédiation* (`FR-13`), (c) la reproduction du bug par un test unitaire qui échoue avant correctif et passe après en Sandbox Palier 2 (`AD-9`, `< 60s`), (d) un test de non-régression en environnement *staging / prod-like*, et (e) une étape finale `POST_ACTION_VERIFICATION` observant le puits de logs via `LogSinkQueryPort` (`AD-23`) pendant `verification_window_seconds` après déploiement. En cas de persistance de l'erreur, ORCIA déclenche automatiquement le **Rollback**, ouvre le coupe-circuit (`CIRCUIT_OPEN`) et alerte l'astreinte en `< 500 ms`.

4. **Imbrication Fractale de Workflows (`SUB_WORKFLOW` & `Workflow-as-Agent`, profondeur $\le 3$, `FR-30`)** :
   - Une étape `step_type: SUB_WORKFLOW` invoque un workflow cible en instanciant un `workflow_run` enfant DBOS lié par `parent_run_id`, `parent_step_execution_id` et `root_run_id` (`nesting_depth <= 3`, sans cycle).
   - Le `run-lock.json` du parent épingle récursivement l'arbre des sous-workflows (`sub_workflow_locks`), chaque sous-workflow possède un *Blackboard* lexicalement isolé (`input_mapping` / `output_mapping`), et le budget `max_cost_usd` du `root_run_id` est partagé atomiquement sur toute la hiérarchie.

---

### 3.9. Architecture en Monolithe Modulaire, Graphe Acyclique de Packages `uv`, Point Unique d'Assemblage, Outbox Transactionnelle, Plugins & 5 Rôles Opérationnels (`AD-19`)

1. **Sens Unique des Dépendances & Suppression des 3 Cycles (`M1`, `M3`, `P4`)** :
   - Ordre strict imposé par `import-linter 2.3.0` (`lint-imports`) : `apps (api, worker) -> orchestration / bootstrap -> domaines (blackboard, catalog, ontology, rag, gates, permissions, audit_finops) -> orcia-kernel`.
   - Rupture des cycles : `WorkflowExecutionRegime` et `WorkflowStepType` sont déplacés dans `orcia_kernel.enums` et `BlackboardPort` dans `orcia_kernel.ports` (`blackboard` n'importe jamais `orchestration`) ; les données de référence résident dans `catalog/seeds.py` et `permissions/seeds.py` et sont agrégées par `bootstrap`.
2. **4 Packages `uv`, Façade Publique `__init__.py` & Implémentation Privée `_internal/` (`M2`, `P3`)** :
   - Workspace `uv 0.13.5` découpé en 4 packages : `packages/orcia-kernel` (0 dépendance externe), `packages/orcia-core` (domaines métier), `apps/api`, `apps/worker`.
   - Chaque domaine de `orcia-core` expose uniquement ses contrats publics dans `__init__.py` et place ses modèles SQLAlchemy, dépôts et adaptateurs dans `_internal/` (protégé par `import-linter`).
3. **Séparation des Schémas HTTP (`orcia_api/schemas/`) & Décentralisation des Erreurs (`<domaine>/errors.py`) (`M4`)** :
   - Les `2 060` lignes de DTO HTTP/OpenAPI quittent `orcia-core` pour `apps/api/src/orcia_api/schemas/<domaine>.py`.
   - `domain/exceptions.py` (`377` lignes, rayon d'impact critique de `59` dépendants) est scindé : seule la classe de base `OrciaDomainError` vit dans `orcia_kernel.errors`, chaque domaine déclare ses exceptions dans `<domaine>/errors.py`, et `apps/api` les traduit en enveloppes **RFC 9457**.
4. **Point Unique d'Assemblage (*Composition Root*) & Zéro Singleton à l'Import (`M5`, `P1`)** :
   - Suppression des singletons `_DEFAULT_*_SERVICE = build_default_*()` exécutés à l'import dans `routers/auth.py`, `routers/catalog.py` et `routers/orchestration.py`.
   - Assemblage unique dans `lifespan` (`apps/api/src/orcia_api/main.py` $\rightarrow$ `app.state` + `Depends()`) et `on_startup` (`apps/worker/src/orcia_worker/main.py`). Les adaptateurs `InMemory*` sont déplacés dans `tests/unit/fakes/`.
5. **Événements de Domaine & Table Outbox Transactionnelle (`domain_events_outbox`, `M6`)** :
   - Les effets secondaires transverses non bloquants (`audit_finops`, extraction `ontology`, notifications SSE, réveil de déclencheurs) sont publiés sous forme d'événements immuables (`StepCompleted`, `ArtifactProduced`, `GateEvaluated`, `RunTerminated`) insérés dans `domain_events_outbox` au sein de la même transaction SQL que le changement d'état du Run, puis relayés de manière idempotente. Les *Gates* et l'arbitrage humain restent synchrones.
6. **Plugins `entry_points` & Sidecar MCP (`sandbox-runner`, `M7`, `M8`, `P5`)** :
   - Plugins Python `entry_points` (`pyproject.toml`) appliqués selon la *Règle de Trois* aux résolveurs d'URI (`orcia.uri_resolvers`) et passerelles LLM (`orcia.llm_gateways`).
   - Exécution hors processus via MCP/subprocess pour les outils tiers et le rôle **`sandbox-runner`** (`wasmtime-py 27.0.0` Palier 1 `< 5s` et `gVisor/Podman` Palier 2 `< 60s`).
7. **Image Conteneur Unique Déployée en 5 Rôles & Frontend par Fonctionnalité (`M9`, `M11`)** :
   - Base PostgreSQL 18 unique (schéma `public` unique garantissant les clés étrangères et transactions ACID inter-tables).
   - 5 rôles opérationnels : `api`, `worker-orchestration`, `worker-indexing` (isolant Docling), `trigger-dispatcher`, `sandbox-runner`.
   - Organisation frontend par fonctionnalité métier dans `apps/web/src/features/<domaine>/`.

### 3.10. Core Agnostique, Pack SDLC, Interface de Connecteur Unique, Exécution Réelle & Taxonomie d'Erreurs (`AD-20`, Avenant A2 du 28/10/2026)

1. **Frontière Core / Packs** : `orcia_kernel` et `orcia_core` sont exempts de vocabulaire métier. Le SDLC est livré dans `packages/orcia-pack-sdlc` (connecteurs `git`, `jira`, `confluence`, `nexus` ; `BmadSkillPackAdapter` ; politique FR-13 ; marqueurs `sdlc.*` ; indexeurs code AST et Jira ; graphe tripartite). Contrat `import-linter` : `orcia_kernel` / `orcia_core` ↛ `orcia_pack_*`. Job CI `core-without-sdlc` (workflow Finance « Rapprochement de factures » + connecteur ERP factice, pack désinstallé).
2. **Registres `entry_points`** : `orcia.connectors`, `orcia.step_executors`, `orcia.workflow_policies`, `orcia.indexers` (absorbe `orcia.uri_resolvers`).
3. **`ConnectorPort`** (`orcia_kernel.ports`) : `capabilities()`, `fetch(uri)`, `invoke(action, payload, idempotency_key)`, `health()`, `map_error(exc)` ; kit de conformité commun ; `FederatedUriResolver` délègue au registre sans changer la signature de `parse_federated_uri` (risque GitNexus CRITICAL, 7 flux).
4. **Exécution réelle** : un seul moteur DBOS injecté par le *Composition Root* ; chaque `@DBOS.step()` appelle l'exécuteur résolu (`AGENT`, `SKILL`, `SUB_WORKFLOW`, `HUMAN_TASK`, `HTTP_ACTION`) ; suppression du moteur simulé en mémoire, de `_ACTIVE_ENGINE` et de tout appel à une API privée `dbos._*`.
5. **Taxonomie d'erreurs & `ConnectorInvoker`** : `TransientInfraError(retry_after_s)`, `RateLimitedError`, `UpstreamTimeoutError` (relançables) ; `FunctionalConnectorError`, `PolicyDeniedError`, `PermanentInfraError` (non relançables → arbitrage humain) ; relances bornées par le budget `AD-12`, `Retry-After`, coupe-circuit par connecteur, `idempotency_key`.
6. **Secrets** : `SecretRef` non sérialisable + `SecretProviderPort` ; masquage structlog ; liste blanche de sérialisation pour outbox, audit, `step_executions` et `dbos.*` ; test du secret témoin (`NFR-SEC-4`).
7. **Concurrence** : `ResourceLeasePort` (bail PostgreSQL + jeton de fencing), ordre d'acquisition canonique, files DBOS par classe de ressource.

---

## 4. Schéma de Données Principal (PostgreSQL 18 + `pgvector`)

| Table | Rôle Principal | Colonnes Clés & Index |
| --- | --- | --- |
| `workspaces` (et `org_units`, `workspace_datasources`) | Découplage entre l'arbre hiérarchique d'équipes (`org_units` avec `parent_id`), les espaces solutions (`workspaces`) et leurs multiples sources dédiées (`workspace_datasources` : `N × git://`, `N × jira://`, `N × confluence://`) | `id (uuid PK)`, `slug`, `owner_org_unit_id`, `visibility_mode (STANDARD\|CONFIDENTIAL_RESTRICTED)`, `settings_jsonb` |
| `workflow_definitions` | Définitions de workflows du catalogue (natifs ou packs BMAD) | `id`, `workspace_id`, `uri`, `version`, `source_format (ORCIA\|BMAD_PACK)`, `criticality`, `execution_regime`, `tie_break_policy`, `steps_schema_jsonb`, `adaptive_gate_policy` |
| `workflow_triggers` | Déclencheurs autonomes gouvernés (`WEBHOOK`, `LOG_SINK_ALERT`, `CRON`, `MANUAL_AUTONOMOUS`, `AD-18`, `FR-29`) | `id`, `workspace_id`, `workflow_def_id`, `trigger_type`, `cron_expr`, `webhook_secret_vault_ref`, `event_filter_jsonb`, `cooldown_window_seconds`, `service_principal_id`, `max_runs_per_hour`, `max_daily_cost_usd`, `max_consecutive_failures`, `post_hoc_sampling_rate`, `contract_signature_id`, `status (ACTIVE\|PAUSED\|CIRCUIT_OPEN)` |
| `workspace_customization_overrides` | Surcharges déclaratives à 4 niveaux (`Base -> Team -> Workspace -> User`, `AD-14`) | `id`, `org_unit_id (nullable)`, `workspace_id (nullable)`, `target_uri`, `user_id (nullable)`, `override_layer (TEAM\|WORKSPACE\|USER)`, `override_manifest_jsonb`, `sha256` |
| `workflow_runs` | Instances d'exécution (*Runs* et *Sub-Workflows* imbriqués) isolées par *Workspace* (`AD-2`, `AD-18`, `FR-29`, `FR-30`) | `id`, `workspace_id`, `workflow_def_id`, `parent_run_id (nullable)`, `parent_step_execution_id (nullable)`, `root_run_id`, `nesting_depth (int <= 3)`, `execution_regime`, `criticality`, `trigger_id (nullable)`, `trigger_idempotency_key (nullable)`, `status`, `initiated_by_user_id`, `execution_identity_mode`, `budget_max_usd` (`UNIQUE (trigger_id, trigger_idempotency_key)`) |
| `run_lock_manifests` | Épinglage immuable `run-lock.json` incluant `sub_workflow_locks` récursifs et les `active_packs` / `slot_bindings` résolus par le *Workspace* (`AD-5`, `AD-14`, `AD-18`, `Epic 31`) | `run_id (PK/FK)`, `manifest_jsonb` (`active_packs`, `slot_bindings`, `archive_sha256`), `overrides_sha256`, `manifest_sha256`, `locked_at` |
| `step_executions` | État d'exécution, brouillon et memlog de chaque étape (`AD-2`, `AD-13`) | `id`, `run_id`, `step_key`, `step_type (AGENT\|SKILL\|SUB_WORKFLOW\|POST_ACTION_VERIFICATION)`, `execution_mode (COACHING\|FAST_PATH\|AUTONOMOUS_CONTRACT)`, `status`, `draft_artifact_jsonb`, `draft_cas_key`, `step_memlog_jsonb`, `executor_model_id`, `evaluator_model_id`, `retry_count`, `claimed_by_user_id` |
| `blackboard_snapshots` | Historique append-only des états validés du *Blackboard* (`AD-2`) | `id`, `run_id`, `parent_snapshot_id`, `step_execution_id`, `branch_status (ACTIVE\|SUPERSEDED)`, `state_jsonb`, `sha256` |
| `domain_events_outbox` | Table Outbox transactionnelle garantissant la publication idempotente des effets secondaires (`AD-19`, `M6`) | `id (uuid PK)`, `event_type`, `aggregate_type`, `aggregate_id`, `run_id (nullable)`, `step_execution_id (nullable)`, `payload_jsonb`, `trace_id`, `status (PENDING\|PUBLISHED\|FAILED)`, `attempts`, `created_at`, `published_at` |
| `human_anchor_signatures` | Preuves cryptographiques de saisie humaine, d'amendement ou de *Contrat d'Autonomie* (`AD-3`, `AD-18`) | `id`, `step_execution_id`, `section_key`, `authored_by_user_id`, `content_sha256`, `signed_at` |
| `gate_evaluations` | Résultats des *Gates* et du DAG de lentilles (`AD-9..11`) | `id`, `step_execution_id`, `gate_type`, `status`, `score`, `lens_findings_jsonb`, `briefing_4blocks_jsonb`, `evaluator_model_id`, `review_duration_ms`, `fast_approval_warning` |
| `chunk_approvals` | État et co-édition de la *Validation par Découpage* (`FR-5`) | `id`, `gate_evaluation_id`, `chunk_index`, `section_title`, `status (APPROVED\|AMENDED\|CHALLENGED)`, `amended_content (text nullable)`, `reviewer_user_id` |
| `task_notifications` | Boîte de notifications unifiée personnelle, d'équipe & d'audit post-hoc (`FR-2`, `FR-29`) | `id`, `workspace_id`, `target_team_id`, `target_user_id`, `run_id`, `step_execution_id`, `type`, `claimed_by_user_id`, `claimed_at` |
| `ontology_concepts` | Concepts des 4 niveaux d'*Ontologie* (`1_ENTERPRISE`, `2_DOMAIN`, `3_TEAM`, `3_WORKSPACE`, `4_RUN_EPHEMERAL`, `AD-7`) | `id`, `level`, `scope_id`, `introduced_in_snapshot_id (nullable)`, `canonical_term`, `definition`, `synonyms_array`, `profile_translations_jsonb` |
| `ontology_relations` | Relations orientées et typées entre concepts (`AD-7`) | `id`, `source_concept_id`, `target_concept_id`, `relation_type`, `cardinality`, `level` |
| `ontology_axioms` | Règles d'intégrité sémantique et invariants (`AD-7`) | `id`, `concept_id`, `axiom_expression_jsonb`, `immutable (bool)`, `level` |
| `kb_documents` & `kb_chunks` | Index RAG hybride & fraîcheur documentaire isolé par *Workspace* et par `datasource_id` (`AD-8`) | `id`, `workspace_id`, `datasource_id`, `kb_id`, `kb_snapshot_hash`, `embedding halfvec(1024)` (Index HNSW), `search_tsv tsvector` (Index GIN), `freshness_ttl_days`, `last_verified_at` |
| `audit_ledger` | Journal d'audit et de télémétrie FinOps append-only (`AD-12`) | `id`, `run_id`, `step_execution_id`, `actor_type`, `actor_id`, `event_type`, `model_id`, `input_tokens`, `output_tokens`, `cost_usd`, `created_at` (Trigger `BEFORE UPDATE OR DELETE RAISE EXCEPTION`) |
| `connector_schemes` | Source de vérité unique des types de source (Avenant A2, `AD-5`, `AD-20`) — remplace les 4 contraintes `CHECK` (migrations `0013` Expand / `0014` Contract) | `id (uuid PK UUIDv7)`, `scheme (varchar UNIQUE)`, `provided_by_package`, `capabilities_jsonb`, `enabled`, `registered_at` ; FK vers `connector_schemes(scheme)` depuis `workspace_datasources.scheme`, `user_passthrough_credentials.connector_scheme`, `permission_broker_policies.connector_scheme`, `permission_broker_tickets.connector_scheme` |
| `resource_leases` | Baux de ressources partagées avec fencing (Avenant A2, `AD-4`, `DEC-CONC-01`) | `id (uuid PK UUIDv7)`, `resource_uri (UNIQUE)`, `holder_run_id`, `holder_step_execution_id`, `fencing_token (bigint monotone)`, `expires_at` |
| `assistant_thread_messages` | Persistent `"Mon Assistant"` conversational turn history separated from reflexive tool execution traces (`AD-25`, `D4`) | `id (uuid PK UUIDv7)`, `thread_id (uuid FK -> assistant_threads.thread_id ON DELETE CASCADE)`, `workspace_id (uuid FK -> workspaces.id ON DELETE CASCADE)`, `turn_id (uuid NOT NULL)`, `parent_turn_id (uuid NULL)`, `role VARCHAR(16) CHECK (role IN ('user', 'assistant'))`, `content TEXT`, `citation_map JSONB`, `token_count INTEGER`, `created_at TIMESTAMPTZ`, index `(thread_id, created_at)` (detailed tool traces remain isolated in `reflexive_execution_sessions` keyed by `turn_id`, never re-injected as `role: 'tool'`) |
| `assistant_turn_feedback` | Idempotent per-user conversational turn feedback persistence (`AD-25`, `R5`) | `id (uuid PK UUIDv7)`, `turn_id (uuid NOT NULL)`, `workspace_id (uuid FK -> workspaces.id ON DELETE CASCADE)`, `user_id (uuid FK -> users.id ON DELETE CASCADE)`, `rating VARCHAR(8) CHECK (rating IN ('up', 'down'))`, `reason_code VARCHAR(64) NULL`, `comment TEXT NULL`, `created_at TIMESTAMPTZ`, `updated_at TIMESTAMPTZ`, `UNIQUE (turn_id, user_id)` upsert constraint |
| `declarative_pack_bundles` | Registre v2 des packs déclaratifs APM-Superset (`SYSTEM`, `IMPORTED`, `CUSTOM`, cycle `DRAFT`/`PUBLISHED`/`DEPRECATED`) (`Epic 31`) | `id (uuid PK UUIDv7)`, `pack_id`, `slug`, `version`, `rbac_namespace`, `bundle_kind`, `scope_type`, `scope_id`, `status`, `source_origin`, `archive_sha256`, `cas_object_key`, `manifest_jsonb`, `declared_slots_jsonb`, `UNIQUE (scope_type, scope_id, slug, version)`; nullable `pack_bundle_id` (`ON DELETE CASCADE`) sur `catalog_items`, `workflow_definitions_v2`, `vsm_definitions_v2`, `ontology_*`, `permission_broker_policies`; schéma `'pack'` dans `connector_schemes` |
| `pack_dna_mechanisms` | Mécanismes Starlark de garde gouvernés appartenant à un pack déclaratif et validés en Sandbox Palier 1b (`Epic 31`) | `id (uuid PK UUIDv7)`, `pack_bundle_id (FK -> declarative_pack_bundles ON DELETE CASCADE)`, `mechanism_key`, `mechanism_kind`, `starlark_source`, `ast_sha256`, `passing_test_payload_jsonb`, `failing_test_payload_jsonb`, `UNIQUE (pack_bundle_id, mechanism_key)` |
| `pack_draft_memberships` | Appartenance typée des entités d'un brouillon `CUSTOM` avec protection anti-otage `ON DELETE RESTRICT` (`Epic 31`) | `id (uuid PK UUIDv7)`, `draft_bundle_id (FK -> declarative_pack_bundles ON DELETE CASCADE)`, `entity_type`, `entity_id`, `entity_slug`, 8 colonnes FK typées (`catalog_item_id`, `workflow_def_v2_id`, `vsm_def_v2_id`, `ontology_concept_id`, `ontology_relation_id`, `ontology_axiom_id`, `broker_policy_id`, `dna_mechanism_id` `ON DELETE RESTRICT`) |
| `workspace_pack_activations` | Activations exclusives au périmètre `WORKSPACE` avec priorité atomique réordonnançable (`Epic 31`) | `id (uuid PK UUIDv7)`, `workspace_id (FK -> workspaces ON DELETE CASCADE)`, `pack_bundle_id (FK -> declarative_pack_bundles ON DELETE RESTRICT)`, `pack_slug`, `is_active`, `priority_order`, trigger `trg_workspace_pack_activations_scope_guard`, `uq_workspace_pack_priority DEFERRABLE INITIALLY DEFERRED` |
| `workspace_pack_slot_bindings` | Liaisons explicites des emplacements de connecteurs déclarés d'un pack vers une source ou un connecteur du *Workspace* (`Epic 31`) | `id (uuid PK UUIDv7)`, `workspace_id (FK -> workspaces ON DELETE CASCADE)`, `pack_bundle_id (FK -> declarative_pack_bundles ON DELETE CASCADE)`, `slot_key`, `target_kind (UNBOUND\|WORKSPACE_DATASOURCE\|ENTERPRISE_CONNECTOR\|INTERNAL)`, `bound_datasource_id`, `bound_connector_id`, `connector_scheme`, `UNIQUE (workspace_id, pack_bundle_id, slot_key)` |

> **Architectural Scope Note (`AD-25`, `R2`, `R5`):** Neither `assistant_studio_graphs` (Mode B graphical studio deferred to `ACTION_ITEM-26.1`) nor `assistant_citation_drafts` (draft card actions deleted in `26.7` alongside `_saved_drafts`) exists in the PostgreSQL 18 schema. Phantom citations stripped by server `CitationGuard` and per-tool execution records are persisted directly in append-only `audit_ledger` (`ASSISTANT_PHANTOM_CITATION_PURGED`, `ASSISTANT_TOOL_INVOKED`, `ASSISTANT_TOOL_DENIED`).

---

## 5. Cartographie des 7 Modules du Menu Global vers l'API Backend

| Module du Menu Global (UX Direction C + Sélecteur `⌘W`) | Routes (`apps/web/src/routes`) & Features (`apps/web/src/features`) | Routeur FastAPI & Schémas (`apps/api/src/orcia_api`) | Domaine Principal (`orcia-core`) |
| --- | --- | --- | --- |
| **1. Cockpit & Chat** | `/cockpit`, `/runs/$runId` (`features/cockpit/`) | `/api/v1/runs/*`, `/api/v1/chat/*`, `/api/v1/cas/*` (`schemas/orchestration.py`, `schemas/blackboard.py`) | `orchestration`, `blackboard` |
| **2. Boîte, Runs & Workspaces (Centre de Pilotage 4 Onglets)** | `/inbox`, `/runs`, `/workspaces`, `/workspaces/$workspaceId` (`features/inbox/`, `features/workspaces/`) | `/api/v1/inbox/*`, `/api/v1/tasks/*/claim`, `/api/v1/workspaces/*`, `/api/v1/org-units/*`, `/api/v1/events/stream` | `orchestration`, `catalog`, `rag`, `permissions`, `sse` |
| **3. Catalogue Fédéré** | `/catalog/$type` (`features/catalog/`) | `/api/v1/catalog/*`, `/api/v1/resolver/*`, `/api/v1/overrides/*` (`schemas/catalog.py`) | `catalog` |
| **4. Ontologie & KB** | `/ontology`, `/kb` (`features/ontology/`) | `/api/v1/ontology/*`, `/api/v1/kb/*` (`schemas/ontology.py`, `schemas/rag.py`) | `ontology`, `rag` |
| **5. Gates & Habilitations** | `/gates`, `/permissions` (`features/gates/`) | `/api/v1/gates/*`, `/api/v1/permissions/broker/*` (`schemas/gates.py`, `schemas/permissions.py`) | `gates`, `permissions` |
| **6. FinOps & Audit** | `/finops`, `/audit` (`features/finops/`) | `/api/v1/finops/*`, `/api/v1/audit/ledger/*` (`schemas/audit_finops.py`) | `audit_finops` |
| **7. Administration** | `/admin/*`, `/settings`, `/settings/packs` (`features/admin/`, `features/settings/packs/`) | `/api/v1/admin/*`, `/api/v1/org-units/*`, `/api/v1/workspaces/*`, `/api/v1/workspaces/*/packs/*`, `/api/v1/packs/*`, `/api/v1/packs/composer/*` (`schemas/auth.py`, `schemas/bootstrap.py`, `schemas/packs.py`) | `permissions`, `gates`, `catalog`, `packs`, `bootstrap` |

---

## 6. Sécurité, Résilience & Observabilité

1. **Authentification Primaire Bi-Mode, Hiérarchie d'Équipes vs Workspaces Multi-Sources, Centre de Pilotage Multi-Niveaux, Rôle `TEAM_LEAD` & Autorisation Matricielle (`AD-6`, `AD-14`, `FR-3`, `FR-21`)** :
   - **Mode 1 — SSO d'Entreprise (`OIDC / OAuth 2.1`)** : Fédération native avec Keycloak, Microsoft Entra ID, Okta ou Google Workspace, récupérant les claims JWT (`sub`, `email`, `groups`, `bu`, `team`).
   - **Mode 2 — Authentification Locale Autonome (`Argon2id + TOTP`)** : Permet un déploiement personnel ou le lancement immédiat d'une équipe pilote sans dépendre de la DSI centrale, avec hachage `Argon2id`, MFA TOTP optionnel et liens d'invitation signés à durée de vie limitée.
   - **Sessions & Révocation** : Jetons JWT d'accès courts (`15 min`) + Refresh Tokens en cookie `HttpOnly / Secure / SameSite=Strict` révocables instantanément dans Redis.
   - **Découplage Arbre d'Équipes (`org_units`) & Espaces Solutions Multi-Sources (`workspaces` + `workspace_datasources`)** : Une équipe (ou sous-équipe dans un arbre hiérarchique $N$-niveaux) peut maintenir **plusieurs `Workspaces`** correspondant à ses différentes solutions logicielles, et **chaque `Workspace` peut rattacher plusieurs dépôts `git://`, plusieurs projets `jira://` et plusieurs espaces `confluence://` dédiés** (ainsi que ses *Runs* et ses *Artefacts*).
   - **Centre de Pilotage Unifié Multi-Niveaux (`/workspaces` & Sélecteur `⌘W`)** : Rassemble sur un même écran à **4 onglets** (*1. Instances de `Workflow Runs` & Artefacts*, *2. Sources Dédiées & Partagées*, *3. Workflows, Agents & Surcharges*, *4. Équipes, Membres & Gouvernance*) toute la gestion d'un périmètre selon une logique fractale (*Roll-up* / *Drill-down*) :
     - **Niveau Global (`PLATFORM_ADMIN`)** : consultation et administration de 100 % des BU, équipes, Workspaces, sources, agents, workflows et *Runs* de la plateforme (les métadonnées techniques/FinOps des Workspaces `CONFIDENTIAL_RESTRICTED` sont visibles pour l'exploitation mais leur contenu métier reste masqué sauf habilitation explicite).
     - **Niveau BU / Organisation (`BU_DIRECTOR` / Lead d'équipe parente)** : vue consolidée (*Roll-up*) de toutes les équipes, sous-équipes et Workspaces de son organisation (supervision des *Runs* en `READ_ONLY_OBSERVER` hors `CONFIDENTIAL_RESTRICTED`, suivi des sources et `[STALE_WARNING]`, gestion des actifs `SHARED_BU` / `SHARED_TEAM` et des surcharges d'équipe).
     - **Niveau Équipe (`TEAM_LEAD`) & Niveau Solution (`Workspace`)** : pilotage opérationnel complet par le Chef d'Équipe et ses contributeurs (`init-workspace`, invitations `init-user`, enrôlement multi-sources `init-datasource`, surcharges `WORKSPACE` et exécution des *Runs*).
   - **Autorisation Matricielle (`AuthorizationEnginePort`)** : Combine la position dans l'arbre `org_units`, le rôle sur le *Workspace*, les 5 permissions dissociées sur le *Catalogue Fédéré* (`DISCOVER`, `EXECUTE`, `READ_SOURCE`, `EDIT`, `ADMIN`) et le mode d'accès sur chaque *Run* (`CONTRIBUTOR_ACTION_REQUIRED` vs `READ_ONLY_OBSERVER`).
2. **Coffre d'Identité Déléguée (*Passthrough Identity Vault* — `NFR-SEC-4`)** :
   - Les jetons OAuth 2.0 (`3LO`) ou jetons personnels (`PAT`) enregistrés par un utilisateur lors de `init-user` pour le mode *Passthrough* sur `git://`, `nexus://`, `confluence://` et `jira://` sont chiffrés au repos par **AES-256-GCM** avec une clé dérivée par utilisateur (KMS / Vault) et déchiffrés uniquement en mémoire dans le worker le temps de la résolution d'URI.
3. **Observabilité OpenTelemetry de bout en bout, Journalisation 12-Factor & Puits de Logs Découplé (`AD-12`, `AD-23`)** :
   - **Traces Distribuées W3C OTLP** : Chaque requête HTTP, événement SSE, workflow/step DBOS, relais Outbox, job Dramatiq, requête SQLAlchemy, appel LiteLLM et exécution de sandbox propage un `trace_id` W3C OpenTelemetry commun (`opentelemetry-sdk 1.31.0`, `opentelemetry-exporter-otlp 1.31.0`, `opentelemetry-instrumentation-fastapi 0.52b0`, `opentelemetry-instrumentation-sqlalchemy 0.52b0`, `opentelemetry-instrumentation-httpx 0.52b0`), systématiquement inclus dans les enveloppes d'erreur **RFC 9457**.
   - **Journalisation 12-Factor Unifiée (JSON stdout)** : Tous les processus Python (API, workers, triggers, scripts, Uvicorn, Dramatiq, DBOS) écrivent exclusivement sur `stdout` sous le format **1 ligne = 1 événement JSON sérialisé** (`structlog 26.1.0` unifiant la stdlib via `ProcessorFormatter`). Le niveau est paramétrable par `LOG_LEVEL` (défaut `INFO`) et les secrets sont systématiquement masqués (`NFR-SEC-4`).
   - **Port d'Interrogation Découplé (`LogSinkQueryPort`)** : Le code applicatif ignore le puits lors de l'émission. Pour les besoins de surveillance et d'auto-remédiation (`LOG_SINK_ALERT`, `POST_ACTION_VERIFICATION`), l'interrogation passe par `LogSinkQueryPort`, avec l'adaptateur de production `ElasticsearchLogSinkAdapter` (`opensearch-py / elasticsearch-py` compatible) et l'alternative dev locale `LokiLogSinkAdapter` (profils Compose `logs-loki`, `logs-elastic`).
   - **4 Invariants de Réversibilité & Cible OpenShift** : Émission pure `stdout`, traces OTLP standard, règles métier (SHA-256, déduplication, cooldown) 100 % dans ORCIA, et lecture isolée par port. En cible OpenShift (SCC `restricted`, UID non root, conteneurs `readOnlyRootFilesystem: true`), la collecte est déléguée au `ClusterLogForwarder` plateforme avec parsing JSON natif (`structuredTypeKey`) sans fichier de log sur disque pod.

---

## 7. Stratégie de Tests à 5 Couches & Couverture Unitaire de la Plateforme (`AD-17`)

Chaque Epic et chaque User Story du développement d'ORCIA est soumis à une stratégie de vérification en **5 couches**, avec un accent prioritaire sur les **tests unitaires de la plateforme elle-même** et les **tests d'intégration sur conteneurs réels** :

### 7.1. Couche 1 — Tests Unitaires de la Plateforme (`pytest 9.1.1` + `hypothesis 6.170.9` & `Vitest 3.2.7` — Exécution `< 5s`)
Exigence de couverture minimale de **90 %** sur le code de la plateforme (`packages/orcia-kernel`, `packages/orcia-core`, `apps/api`, `apps/worker`, `apps/web`), exécutée sans accès réseau ni base de données, complétée par **`import-linter 2.3.0`** vérifiant l'isolation hexagonale et le graphe acyclique du monolithe modulaire (`AD-19`) :
- **Noyau Domaine Python (`packages/orcia-kernel/tests/unit/`, `packages/orcia-core/tests/unit/`)** :
  - `orchestration` : Tests unitaires et *Property-Based Testing* (`hypothesis`) de toutes les transitions de la machine à états des *Runs*, de l'`JitStepHydrator`, de l'extraction automatique des `[ASSUMPTION]` en mode *Fast-Path* (`AD-13`) et du calcul de branche lors d'un *Rewind / Replay* (`AD-2`).
  - `blackboard` : Vérification du rejet systématique (`ERR_HUMAN_ANCHOR_REQUIRED`) de toute écriture IA sur une section `human_authored_required: true` non signée (`AD-3`) et fusion des `chunk_approvals.amended_content`.
  - `catalog` : Tests unitaires du parseur d'URI et des plugins `entry_points` (`db://`, `git://`, `nexus://`, `orcia://`), de l'algorithme de fusion déterministe à 4 niveaux (`Base → Team → Workspace → Utilisateur`) et du `BmadSkillPackAdapter` (`AD-14`).
  - `ontology` : Tests unitaires de la détection d'`ONTOLOGY_CONFLICT` et du traducteur sémantique par *Profil Humain* (`FR-15`).
  - `rag` : Tests unitaires de l'algorithme *Reciprocal Rank Fusion (RRF, `k=60`)* et des règles d'expiration `freshness_ttl_days` (`[STALE_WARNING]`).
  - `gates` : Tests unitaires du `ModelRouterService` vérifiant qu'aucun couple `(executor_model, evaluator_model)` de même famille n'est accepté (`AD-10`), de la fonction pure de purge de la *Chain-of-Thought*, du moteur de politiques adaptatives (`mandatory_full`, `risk >= 0.85`, `sampling 20%`) et du détecteur de *Rubber-Stamping* `< 15s` (`AD-11`).
  - `permissions` : Tests unitaires de la matrice RBAC/ABAC (`AuthorizationEnginePort`) et du matcher de motifs d'URI du `PermissionBrokerService` (`AD-6`).
  - `audit_finops` : Tests unitaires du calculateur de coûts tokens, de l'abonné Outbox et du déclenchement des coupe-circuits `PAUSED_BUDGET_EXCEEDED` / `PAUSED_MAX_RETRIES` (`AD-12`).
  - `AssistantHarness` : Tests unitaires de l'assemblage des **5 couches de prompt** et de l'inviolabilité de la Couche 1 (`AD-15`).
- **API & Workers (`apps/api/tests/unit/`, `apps/worker/tests/unit/`)** : Tests unitaires des middlewares (`RunAccessGuard` bloquant le mode `READ_ONLY_OBSERVER`, registre déclaratif d'erreurs **RFC 9457**) et de l'idempotence des étapes DBOS, du relais Outbox et des acteurs Dramatiq.
- **Frontend Web (`apps/web/src/features/**/__tests__/`)** : Tests unitaires **Vitest + React Testing Library** des composants cognitifs (`BriefingCard`, `ChunkedArtifactReviewer`, `TieBreakMatrixModal`, `PresenceLockBadge`), des hooks (`useSseStream`, `useClaimLock`) et des stores Zustand.

### 7.2. Couche 2 — Tests d'Intégration sur Infrastructure Réelle (`testcontainers-python 4.15.0`)
- **Zéro Mock SQLite/Redis** : Lancement automatique de conteneurs éphémères **PostgreSQL 18 + `pgvector`**, **Redis 7.4.2** et **SeaweedFS 3.85 S3** pour tester les repositories `SQLAlchemy 2.1.6 Async`, la reprise sur crash des workflows durables **DBOS Transact 2.14.0**, la table transactionnelle `domain_events_outbox`, les CTE récursives d'ontologie (et l'exclusion des concepts L4 des branches `SUPERSEDED`), l'atomicité réelle de `SET lock:step:<id> NX` sous forte concurrence, les triggers PostgreSQL interdisant `UPDATE/DELETE` sur `audit_ledger` et `blackboard_snapshots`, et les tests d'isolation de la sandbox bimodale (`AD-9` Palier 1 `Wasmtime` & Palier 2 conteneur isolé `--network=none`).

### 7.3. Couche 3 — Tests de Contrat API & Fuzzing (`openapi-typescript 7.6.1` + `Schemathesis 4.32.4`)
- Vérification en CI qu'aucune dérive n'existe entre le schéma OpenAPI 3.1 de `apps/api/src/orcia_api/schemas/` et `packages/api-client`, complétée par un fuzzing automatique `Schemathesis` sur toutes les routes REST.

### 7.4. Couche 4 — Tests d'Orchestration IA : Cassettes Déterministes (CI) & Suite d'Evals (`orcia-evals`)
- En CI à chaque commit, `DeterministicCassetteLLM` rejoue de manière instantanée et déterministe (`0 $`) les réponses d'agents (incluant appels d'arbitrage, erreurs `403`, rejets de gates).
- En pré-release, `orcia-evals` évalue sur un *Golden Dataset* la qualité du workflow de l'Agent Assistant (`AD-15`) et des lentilles d'évaluation (`AD-10`).

### 7.5. Couche 5 — Tests End-to-End Multi-Utilisateurs & Multi-Device (`@playwright/test 1.64.1`)
- Exécution de parcours complets sur une **pile bi-serveur E2E 100 % isolée** (conteneurs éphémères `testcontainers` PostgreSQL 18 + Redis 7.4, `FastAPI :8100` en mode `DeterministicCassetteLLM`, `Vite :3101`, protégée par le garde-fou `is_isolated_e2e_database_url`) ouvrant simultanément deux sessions navigateur (ex. *Contributeur* et *Observateur*) pour valider la latence SSE `< 500ms` des verrous de présence, le vrai rechargement `F5` (`page.reload()`) en base de données et le rejet `403 ERR_OBSERVER_MODE_READ_ONLY`, tant sur **Desktop (`1440x900`)** que sur **Mobile Companion (`390x844`)**.

### 7.6. Couche Transverse Sécurité & 10 Mécanismes Automatisés Anti-Dette de Tests
Pour empêcher structurellement l'apparition de dette de tests au fil des Epics et des évolutions ad-hoc, la pyramide `AD-17` est complétée par la suite de sécurité [`tests/security/test_api_security_baseline.py`](file:///home/romain/Documents/Projects/ORCIA/tests/security/test_api_security_baseline.py) (Anti-SSRF `is_safe_llm_endpoint_url`, rejet `403 ERR_OBSERVER_MODE_READ_ONLY` sur mutations, anti-escalade RBAC `403 ERR_GRANT_ESCALATION_FORBIDDEN`, masquage `CONFIDENTIAL_RESTRICTED`, non-divulgation des secrets canaris `DEC-SEC-01`) et par **10 verrous automatisés bloquants** documentés en détail dans [**`docs/testing-strategy.md`**](file:///home/romain/Documents/Projects/ORCIA/docs/testing-strategy.md) :
1. **Contrat Registre des Capacités $\leftrightarrow$ Routes $\leftrightarrow$ Tests (`capabilities.yaml` & `pnpm site:check`)** : aucune route FastAPI ou SPA sans capacité `CAP-xxx`, aucune capacité `live` sans fichier de test vérifié sur disque (`tests:` + `verification: runtime`).
2. **Garde-Fou « Zéro Bouton Muet, Zéro Callback Oublié & Zéro `.catch(() => undefined)` »** (`zero-dead-buttons-and-silent-catches-audit.test.tsx`).
3. **Garde Centralisée d'Environnement `isJsdomTestEnv()`** (`runtime-env-guard-audit.test.ts`).
4. **Garde-Fou de Survie au `F5`** (`unmount()` $\rightarrow$ `render()` en Vitest + `page.reload()` en Playwright E2E sur PostgreSQL 18).
5. **Audit AST Anti-Patterns Architecturaux & Asynchronisme (`TID251`)** (`test_codebase_architectural_anti_patterns_audit.py`).
6. **Audit « Zero Mock & Zero Fictional Data » en Production** (`test_zero_fictional_data_and_mocks_in_prod.py`).
7. **Contrats d'Isolation Hexagonale & Frontière Core / Pack (`lint-imports` `AD-19` & `AD-20`)**.
8. **Garde-Fou GitNexus « Zéro Adaptateur SQL Orphelin » & Seuil de Couverture $\ge 90\%$**.
9. **Audits UX/UI Automatisés** (isolation `@orcia/ui`, registre central d'icônes `ORCIA_ICONS`, zéro jargon interne).
10. **Protocole Tech Lead & Overrides BMAD** (`AGENTS.md` §6, `CLAUDE.md`, `TECH-LEAD-REPORT-TEMPLATE.md` §2.5 & §3.3, `_bmad/custom/*.toml`) imposant la revue de toute la pyramide jusqu'au E2E à chaque changement.

---

## 8. FAQ Architecture & Modèle Métier (Winston)

### Q1. Quel est le lien entre l'objet Espace de Travail (quel est son terme interne dans ORCIA) et les entités de l'organisation ?

> **Réponse de Winston (Architecte Système ORCIA)** — Références : [`0002_story_1_2_auth_org_workspaces_permissions.py`](file:///home/romain/Documents/Projects/ORCIA/infra/migrations/versions/0002_story_1_2_auth_org_workspaces_permissions.py), `AD-6`, `AD-14`, `AD-21`, `FR-3`, `FR-21`.

#### 1. Termes internes dans ORCIA (Modèle de données & Domaine)

Dans ORCIA, l'**Organisation** et l'**Espace de Travail** sont volontairement découplés en deux concepts distincts afin qu'une même équipe puisse gérer plusieurs produits/projets et que plusieurs équipes puissent collaborer sur un même espace :

| Concept Métier (UI FR) | Terme Interne Domaine (`orcia_core`) | Table PostgreSQL 18 | Granularité & Niveaux | Rôle Fondamental |
| :--- | :--- | :--- | :--- | :--- |
| **Entité de l'Organisation** *(Entreprise, Direction / BU, Tribu, Équipe, Sous-Équipe)* | **`OrgUnit`** | `org_units` | `unit_type IN ('ENTERPRISE', 'BU', 'TRIBE', 'TEAM', 'SUB_TEAM')` (arbre hiérarchique récursif via `parent_id`) | **« Qui nous sommes »** *(l'organigramme de l'entreprise)* : rattachement RH/organisationnel des utilisateurs (`users.primary_org_unit_id`), porteur des directives et habilitations d'organisation. |
| **Espace de Travail** *(Projet, Produit, Solution logicielle, Chantier)* | **`Workspace`** | `workspaces` | Unité opérationnelle (`visibility_mode IN ('STANDARD', 'CONFIDENTIAL_RESTRICTED')`) | **« Sur quoi nous travaillons »** *(l'environnement opérationnel de travail)* : conteneur où sont connectées les sources documentaires (`workspace_datasources` : Git, Confluence, Jira, DB), où s'exécutent les processus (`workflow_runs`), où s'accumule le contexte (`kb_documents`, `blackboard_snapshots`) et où sont imputés les coûts IA (`finops_cost_usd`). |

#### 2. Les deux liens relationnels entre `Workspace` et `OrgUnit` (`0002_story_1_2_auth_org_workspaces_permissions.py`)

Le modèle relationnel PostgreSQL 18 établit **deux liens complémentaires** entre `workspaces` et `org_units` :

- **A. Lien de Propriété / Rattachement principal (`owner_org_unit_id` : `N ➔ 1`)** :
  Chaque `Workspace` appartient obligatoirement à une `OrgUnit` propriétaire (généralement une Équipe `TEAM` ou une Direction `BU`) via la clé étrangère `workspaces.owner_org_unit_id`. Une même Équipe (`TEAM`) peut ainsi posséder `0, 1` ou plusieurs Espaces de Travail (`Workspace`). La contrainte `ON DELETE RESTRICT` empêche structurellement la suppression d'une Direction ou d'une Équipe tant qu'au moins un Espace de Travail lui est rattaché.

  ```sql
  CREATE TABLE org_units (
      id UUID PRIMARY KEY,
      slug VARCHAR(128) NOT NULL UNIQUE,
      name VARCHAR(255) NOT NULL,
      unit_type VARCHAR(32) NOT NULL CHECK (
          unit_type IN ('ENTERPRISE', 'BU', 'TRIBE', 'TEAM', 'SUB_TEAM')
      ),
      parent_id UUID NULL REFERENCES org_units(id) ON DELETE RESTRICT,
      created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
  );

  CREATE TABLE workspaces (
      id UUID PRIMARY KEY,
      slug VARCHAR(128) NOT NULL UNIQUE,
      name VARCHAR(255) NOT NULL,
      owner_org_unit_id UUID NOT NULL REFERENCES org_units(id) ON DELETE RESTRICT,
      visibility_mode VARCHAR(32) NOT NULL DEFAULT 'STANDARD' CHECK (
          visibility_mode IN ('STANDARD', 'CONFIDENTIAL_RESTRICTED')
      ),
      settings_jsonb JSONB NOT NULL DEFAULT '{}'::jsonb,
      finops_cost_usd NUMERIC(12, 4) NOT NULL DEFAULT 0.0000,
      created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
  );
  ```

- **B. Lien de Collaboration / Invitation inter-équipes (`workspace_memberships` : `N ➔ N`)** :
  Au-delà de l'équipe propriétaire (`owner_org_unit_id`), la table d'association `workspace_memberships` permet d'inviter dans un `Workspace` soit des utilisateurs nominatifs (`user_id`), soit **toute une autre Équipe ou Direction de l'organisation** (`invited_org_unit_id REFERENCES org_units(id)`) avec un rôle précis (`TEAM_LEAD`, `CONTRIBUTOR`, `GATE_REVIEWER`, `ONTOLOGY_STEWARD_L3`, `OBSERVER`) et un mode d'accès (`CONTRIBUTOR_ACTION_REQUIRED` ou `READ_ONLY_OBSERVER`). La contrainte `CHECK (num_nonnulls(user_id, invited_org_unit_id) = 1)` garantit qu'une entrée cible exactement soit un individu, soit une entité d'organisation.

  ```sql
  CREATE TABLE workspace_memberships (
      id UUID PRIMARY KEY,
      workspace_id UUID NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
      user_id UUID NULL REFERENCES users(id) ON DELETE CASCADE,
      invited_org_unit_id UUID NULL REFERENCES org_units(id) ON DELETE CASCADE,
      role VARCHAR(64) NOT NULL CHECK (
          role IN (
              'TEAM_LEAD',
              'CONTRIBUTOR',
              'GATE_REVIEWER',
              'ONTOLOGY_STEWARD_L3',
              'OBSERVER'
          )
      ),
      access_mode VARCHAR(64) NOT NULL CHECK (
          access_mode IN ('CONTRIBUTOR_ACTION_REQUIRED', 'READ_ONLY_OBSERVER')
      ),
      created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
      CHECK (num_nonnulls(user_id, invited_org_unit_id) = 1)
  );
  ```

#### 3. Diagramme Entité-Relation (ER Mermaid)

```mermaid
erDiagram
    ORG_UNITS ||--o{ ORG_UNITS : "parent_id (Arbre ENTERPRISE > BU > TRIBE > TEAM > SUB_TEAM)"
    ORG_UNITS ||--o{ USERS : "primary_org_unit_id (Rattachement RH principal)"
    ORG_UNITS ||--o{ WORKSPACES : "owner_org_unit_id (Propriété N -> 1, ON DELETE RESTRICT)"
    ORG_UNITS ||--o{ WORKSPACE_MEMBERSHIPS : "invited_org_unit_id (Équipe invitée N -> N)"
    USERS ||--o{ WORKSPACE_MEMBERSHIPS : "user_id (Membre nominatif invité)"
    WORKSPACES ||--o{ WORKSPACE_MEMBERSHIPS : "workspace_id (Habilitations & Rôles sur l'Espace)"
    WORKSPACES ||--o{ WORKSPACE_DATASOURCES : "workspace_id (Sources Git, Jira, Confluence, DB)"
    WORKSPACES ||--o{ WORKFLOW_RUNS : "workspace_id (Exécutions de processus & Coûts IA)"
    WORKSPACES ||--o{ ASSISTANT_THREADS : "workspace_id (Conversational threads)"
    ASSISTANT_THREADS ||--o{ ASSISTANT_THREAD_MESSAGES : "thread_id (ON DELETE CASCADE, user|assistant)"
    WORKSPACES ||--o{ ASSISTANT_TURN_FEEDBACK : "workspace_id (Scoped feedback)"
    USERS ||--o{ ASSISTANT_TURN_FEEDBACK : "user_id (UNIQUE turn_id, user_id)"
    ASSISTANT_THREAD_MESSAGES ||--o| REFLEXIVE_EXECUTION_SESSIONS : "turn_id (Isolated Speed 2/3 tool traces)"
    DECLARATIVE_PACK_BUNDLES ||--o{ PACK_DNA_MECHANISMS : "pack_bundle_id (Starlark DNA guards)"
    DECLARATIVE_PACK_BUNDLES ||--o{ PACK_DRAFT_MEMBERSHIPS : "draft_bundle_id (8 typed entity FKs)"
    DECLARATIVE_PACK_BUNDLES ||--o{ WORKSPACE_PACK_ACTIVATIONS : "pack_bundle_id (Priority-ordered activation)"
    WORKSPACES ||--o{ WORKSPACE_PACK_ACTIVATIONS : "workspace_id (DEFERRABLE priority_order)"
    WORKSPACES ||--o{ WORKSPACE_PACK_SLOT_BINDINGS : "workspace_id (Slot -> datasource/connector bindings)"
    DECLARATIVE_PACK_BUNDLES ||--o{ WORKSPACE_PACK_SLOT_BINDINGS : "pack_slug (Logical connector slots)"

    ORG_UNITS {
        uuid id PK
        varchar slug UK
        varchar name
        varchar unit_type "ENTERPRISE | BU | TRIBE | TEAM | SUB_TEAM"
        uuid parent_id FK
    }
    USERS {
        uuid id PK
        varchar email UK
        varchar platform_role
        uuid primary_org_unit_id FK
    }
    WORKSPACES {
        uuid id PK
        varchar slug UK
        varchar name
        uuid owner_org_unit_id FK
        varchar visibility_mode "STANDARD | CONFIDENTIAL_RESTRICTED"
        numeric finops_cost_usd
    }
    WORKSPACE_MEMBERSHIPS {
        uuid id PK
        uuid workspace_id FK
        uuid user_id FK "Nullable (exclusif avec invited_org_unit_id)"
        uuid invited_org_unit_id FK "Nullable (exclusif avec user_id)"
        varchar role "TEAM_LEAD | CONTRIBUTOR | GATE_REVIEWER | ONTOLOGY_STEWARD_L3 | OBSERVER"
        varchar access_mode "CONTRIBUTOR_ACTION_REQUIRED | READ_ONLY_OBSERVER"
    }
    WORKSPACE_DATASOURCES {
        uuid id PK
        uuid workspace_id FK
        varchar alias
        varchar scheme "git | jira | confluence | db | nexus"
        text uri
    }
    WORKFLOW_RUNS {
        uuid id PK
        uuid workspace_id FK
        uuid workflow_def_id FK
        varchar status
        numeric budget_max_usd
    }
    ASSISTANT_THREADS {
        uuid thread_id PK
        uuid workspace_id FK
        uuid folder_id FK
        uuid creator_user_id FK
        varchar title
        int turn_count
    }
    ASSISTANT_THREAD_MESSAGES {
        uuid id PK
        uuid thread_id FK "ON DELETE CASCADE"
        uuid workspace_id FK
        uuid turn_id
        uuid parent_turn_id "Nullable (Deepen link)"
        varchar role "user | assistant"
        text content
        jsonb citation_map
        int token_count
        timestamptz created_at
    }
    ASSISTANT_TURN_FEEDBACK {
        uuid id PK
        uuid turn_id
        uuid workspace_id FK
        uuid user_id FK "UNIQUE (turn_id, user_id)"
        varchar rating "up | down"
        varchar reason_code "Nullable"
        text comment "Nullable"
        timestamptz created_at
        timestamptz updated_at
    }
    REFLEXIVE_EXECUTION_SESSIONS {
        uuid id PK
        varchar execution_id UK "Linked by turn_id"
        varchar workspace_id
        varchar actor_slug
        varchar effort_level
        varchar status
        jsonb snapshot_jsonb
        timestamptz expires_at
    }
    DECLARATIVE_PACK_BUNDLES {
        uuid id PK
        varchar pack_id
        varchar slug
        varchar version
        varchar bundle_kind "SYSTEM | ORG | IMPORTED | CUSTOM"
        varchar scope_type "GLOBAL | BU | TEAM | WORKSPACE"
        varchar scope_id
        varchar status "DRAFT | PUBLISHED | DEPRECATED"
        varchar archive_sha256
        varchar cas_object_key
        jsonb declared_slots_jsonb
    }
    PACK_DNA_MECHANISMS {
        uuid id PK
        uuid pack_bundle_id FK "ON DELETE CASCADE"
        varchar mechanism_slug
        text starlark_source
        varchar source_sha256
    }
    PACK_DRAFT_MEMBERSHIPS {
        uuid id PK
        uuid draft_bundle_id FK "ON DELETE CASCADE"
        varchar entity_type
        varchar entity_id
        varchar entity_slug
        uuid catalog_item_id FK "Nullable ON DELETE RESTRICT"
        uuid workflow_v2_id FK "Nullable ON DELETE RESTRICT"
        uuid vsm_v2_id FK "Nullable ON DELETE RESTRICT"
        uuid dna_mechanism_id FK "Nullable ON DELETE RESTRICT"
    }
    WORKSPACE_PACK_ACTIVATIONS {
        uuid id PK
        uuid workspace_id FK "ON DELETE CASCADE"
        uuid pack_bundle_id FK "ON DELETE CASCADE"
        varchar pack_slug
        int priority_order "DEFERRABLE UNIQUE (workspace_id, priority_order)"
        boolean is_active
    }
    WORKSPACE_PACK_SLOT_BINDINGS {
        uuid id PK
        uuid workspace_id FK "ON DELETE CASCADE"
        varchar pack_slug
        varchar slot_key
        varchar target_kind "UNBOUND | WORKSPACE_DATASOURCE | ENTERPRISE_CONNECTOR | INTERNAL"
        uuid bound_datasource_id FK "Nullable ON DELETE SET NULL"
        uuid bound_connector_id FK "Nullable ON DELETE SET NULL"
    }
```

#### 4. Cascade d'héritage de gouvernance à 4 niveaux (`GLOBAL ➔ BU ➔ TEAM ➔ WORKSPACE`), Modèle Multi-Équipes / Espaces Privés & Chaîne de Verrouillage FinOps

Toute la gouvernance d'ORCIA (habilitations RBAC/ABAC `AD-21`, surcharges déclaratives du catalogue `AD-14`, ontologie `AD-7`, paramètres `platform_settings` et routage de modèles IA) s'applique selon une **cascade hiérarchique à 4 niveaux** :

$$\text{GLOBAL (Plateforme)} \longrightarrow \text{BU (Direction)} \longrightarrow \text{TEAM (Équipe)} \longrightarrow \text{WORKSPACE (Espace de Travail)}$$

1. **Les 3 premiers niveaux (`GLOBAL ➔ BU ➔ TEAM`) constituent l'Organisation (`org_units`)** : ils portent les directives d'entreprise (`1_ENTERPRISE`), les règles de Direction (`BU`), les conventions d'Équipe (`TEAM`) et les budgets FinOps. Un même utilisateur peut être rattaché à **plusieurs Équipes (`Multi-Équipes`)** simultanément, et une même Équipe peut posséder **plusieurs Espaces de Travail (`Multi-Espaces`)**.
2. **Le 4ᵉ niveau (`WORKSPACE`) est l'Espace de Travail (`workspaces`)**, obligatoirement rattaché à son `owner_org_unit_id` (aucun espace ni aucun coût IA orphelin), selon **3 modes de visibilité** :
   - **En mode `STANDARD` (Collectif d'équipe — par défaut)** : l'Espace de Travail hérite automatiquement des règles, du glossaire, des packs métiers et des habilitations de son Équipe (`TEAM`) et de sa Direction (`BU`) parentes, tout en permettant la supervision consolidée (*Roll-up* en lecture seule `READ_ONLY_OBSERVER`) par les responsables de l'équipe ou de la BU parente.
   - **En mode `PRIVATE_USER` (Privé personnel — Facturé à l'équipe, Option 2 FinOps)** : l'Espace de Travail est personnel et confiné à son créateur pour l'idéation et l'expérimentation, mais **demeure rattaché à une Équipe de facturation (`owner_org_unit_id`)** afin que chaque jeton LLM consommé soit imputé au budget de l'équipe choisie.
   - **En mode `CONFIDENTIAL_RESTRICTED` (Confidentiel / Isolé)** : l'Espace de Travail active une coupure d'héritage d'observation descendante (`INHERITANCE_BLOCK`). Les responsables des niveaux parents (`BU_DIRECTOR`, équipes parentes) conservent uniquement la visibilité sur les compteurs techniques et budgétaires globaux (`finops_cost_usd`), mais le contenu métier des documents, du *Blackboard* et des *Runs* reste strictement confiné aux membres explicitement habilités dans `workspace_memberships`.
3. **Amorçage Jour 0 en 2 étapes (`Option 1`) & Chaîne stricte de verrouillage LLM** :
   - Lors du premier démarrage (`Jour 0`), le compte du **1er Administrateur** est créé sans équipe pré-imposée (`memberTeamIds = []`), puis rattaché en 1 clic lors de la création de ses Équipes (`TEAM`) dans `/settings`.
   - **Invariant FinOps strict** : *Zéro appel LLM sans Équipe de facturation (`TEAM`) + Espace de Travail (`WORKSPACE`) + Modèle IA configuré*.
4. **Sélecteur de Contexte (`TopHeaderBar`) en 3 groupes** :
   - La barre supérieure regroupe les périmètres dans 3 sections explicites : **`🔒 Mes Espaces Privés`** (`PRIVATE_USER`), **`👥 Mes Équipes & Espaces`** (`TEAM` + espaces `STANDARD`/`CONFIDENTIAL_RESTRICTED`) et **`🏢 Supervision Organisation`** (`BU` + `Plateforme Globale ORCIA`), filtrant dynamiquement `/cockpit`, `/workspaces`, `/processes` et `/activity`.

#### 5. Assistant Turn Persistence & Trace Isolation Model (`AD-25`, `D4`, `R2`, `R5`)

- **Strict Turn History vs Trace Separation (`D4`):** `assistant_thread_messages` stores only human-facing `user` and `assistant` turns (`ON DELETE CASCADE` from `assistant_threads(thread_id)`) indexed by `(thread_id, created_at)`, along with server-verified `citation_map JSONB`, `turn_id`, optional `parent_turn_id` (linking **"Deepen"** Speed 2 turns back to their parent Speed 1 turn), and `token_count`. Speed 2/3 tool-call and tool-result traces reside strictly in `reflexive_execution_sessions` keyed by `turn_id` and are never injected into prompt history as `role: "tool"`.
- **Feedback & Append-Only Audit (`R5`):** `assistant_turn_feedback` stores one row per `(turn_id, user_id)` (`UNIQUE (turn_id, user_id)` upsert with `rating IN ('up', 'down')`, optional `reason_code` and `comment`). No `assistant_studio_graphs` (`R2`) or `assistant_citation_drafts` (`R5`) tables exist; phantom citations purged by `CitationGuard` (`ASSISTANT_PHANTOM_CITATION_PURGED`) and per-tool execution records (`ASSISTANT_TOOL_INVOKED`, `ASSISTANT_TOOL_DENIED`) write directly to append-only `audit_ledger`.
