# 2026-11-05 — Gestion Complète, Création, Rattachement en 1 Clic & Exécution des Compétences (`Skills`) et des Agents (`Agents`) dans `🤖 Mes Agents`

> **Convention de nommage du fichier (Obligatoire — à créer AVANT toute modification de code)** :
> - Demande d'ajustement, correctif ou évolution hors Story : `docs/implementation-artifacts/tech-lead-reports/{YYYY-MM-DD}-{descriptif-court}-tech-lead-report.md`
> - User Story du sprint : `docs/implementation-artifacts/tech-lead-reports/{story-key}-tech-lead-report.md`

- **Date** : 2026-11-05
- **Story / Clé Sprint** : `2026-11-05-gestion-creation-et-execution-agents-et-competences-skills` (`Post-Epic 12 — Évolution Fonctionnelle & UX Centrée Utilisateur`)
- **Auteur / Contexte** : Implémentation bout-en-bout (`UI @orcia/ui & apps/web` $\rightarrow$ `SDK @orcia/api-client` $\rightarrow$ `Routeur FastAPI apps/api` $\rightarrow$ `Noyau orcia_core & Persistance SQL PostgreSQL 18`) de la création, du rattachement en 1 clic et de l'exécution/test direct des **Compétences (`Skills`)** et des **Agents (`Agents`)** dans l'écran **`🤖 Mes Agents`** (`/agents` / `/catalog`), structuré en 3 sous-vues claires et sans jargon technique (`🤖 Mes Agents`, `🛠️ Compétences`, `🔌 Connexions externes`). Couvre `FR-11`, `FR-20`, `FR-21`, `FR-28`, `AD-16`, `AD-17`, `AD-19`, `UX-DR1` à `UX-DR16`.
- **Commits associés** : `pending`

---

## 1. Analyse du Besoin & Étude d'Impact Tech Lead (Pré-Implémentation)

### 1.1 Contexte & Problématique
- **Opportunité métier & UX** : L'écran **`🤖 Mes Agents`** (`/agents` et `/catalog`, rendu par [`CatalogFeaturePanel`](file:///home/romain/Documents/Projects/ORCIA/apps/web/src/features/catalog/index.tsx)) exposait jusqu'ici uniquement l'explorateur du Catalogue Fédéré bas-niveau (`CatalogExplorerPanel`) et le banc de test des services distants (`RemoteServiceTestBenchAndMcpExposureView`). Un utilisateur métier, Tech Lead ou administrateur ne disposait pas d'une interface claire et directe pour :
  1. **Créer et gérer ses propres Compétences (`Skills`)** réutilisables (Nom, Objectif métier, Paramètres attendus, Instructions / Méthode d'exécution, Format du résultat attendu), les **tester en 1 clic** sur un cas concret, et savoir comment les invoquer via `/nom-de-la-competence` dans `Mon Assistant` ;
  2. **Créer et gérer ses propres Agents (`Agents`)** (Nom, Rôle / Mission métier, Instructions, Niveau de réflexion souhaité `simple | medium | complex | auto`), **cocher/rattacher en 1 clic les Compétences (`Skills`)** que chaque Agent a le droit de mobiliser, et **exécuter/tester l'Agent en 1 clic** sur une demande concrète en visualisant sa réponse ainsi que les compétences mobilisées ;
  3. **Conserver l'accès fluide aux `🔌 Connexions externes`** (banc de test MCP/A2A) dans un 3e onglet dédié.
- **Comportement attendu vs comportement actuel** :
  - **Zéro jargon d'implémentation interne** : Tous les libellés FR/EN doivent parler le langage de l'utilisateur (*« Compétence »*, *« Rôle et mission de l'agent »*, *« Tester maintenant »*, *« Compétences associées »*), sans jamais exposer `catalog_items`, `CAS SHA-256`, `Palier 1b`, `SkillStepExecutor`, `DBOS`, ni aucune métrique NFR en millisecondes.
  - **Zéro donnée fictive au démarrage (Jour 0)** : Au premier lancement, la liste des Agents et des Compétences démarre vide (`0` agent fictif, `0` compétence fictive) avec un état vide accueillant et un bouton d'action clair.
  - **Persistance bout-en-bout & Survie au `F5`** : Chaque création, modification, rattachement de compétence ou suppression est persisté dans PostgreSQL 18 (`catalog_items` avec `resource_type IN ('agent', 'skill')`, `item_type IN ('USER_AGENT', 'USER_SKILL')` et `metadata_jsonb` + repli mémoire propre hors DB) et synchronisé côté frontend (`GET /api/v1/agents-and-skills` + cache `localStorage` `orcia.agents_and_skills.v1`).

### 1.2 Exploration, Analyse d'Impact GitNexus, Factorisation & Dette Technique
- **Analyse d'Impact GitNexus (`gitnexus_query`, `gitnexus_context`, `gitnexus_impact`)** :
  - `gitnexus_query({repo: "/home/romain/Documents/Projects/ORCIA", search_query: "CatalogFeaturePanel agents skills catalog_items step_executors"})` : identifie les flux `CatalogFeaturePanel -> CatalogExplorerPanel` et `SkillStepExecutor -> evaluate_deterministic_gate`.
  - `gitnexus_context({repo: "/home/romain/Documents/Projects/ORCIA", name: "CatalogFeaturePanel"})` : `CatalogFeaturePanel` (`apps/web/src/features/catalog/index.tsx:L10-90`) est appelé uniquement par `ModuleWorkspaceView` (`apps/web/src/components/ModuleWorkspaceView.tsx`) et invoque `CatalogExplorerPanel` et `RemoteServiceTestBenchAndMcpExposureView`.
  - `gitnexus_impact({repo: "/home/romain/Documents/Projects/ORCIA", target: "CatalogFeaturePanel", direction: "upstream"})` : `impactedCount: 1` (`ModuleWorkspaceView`), `risk: LOW`.
  - `gitnexus_impact({repo: "/home/romain/Documents/Projects/ORCIA", target: "FederatedCatalogService", direction: "upstream"})` : `impactedCount: 4` (`orcia_core/catalog/__init__.py`, `orcia_core/bootstrap/__init__.py`, `orcia_core/bootstrap/engine.py`, `orcia_core/bootstrap/project_and_skill_bootstrap.py`), `risk: LOW`.
- **Exploration & Chiffres Clés (Base de Données / Conteneurs / Benchmark)** :
  - La table `catalog_items` (créée par `0003_story_1_3` et enrichie par `0023_story_9_5` avec `item_type VARCHAR(64)` et `metadata_jsonb JSONB`) accepte nativement `resource_type IN ('workflow', 'agent', 'skill', 'template', 'datasource')` et `visibility_scope IN ('DRAFT', 'SHARED_WORKSPACE', 'SHARED_TEAM', 'SHARED_BU', 'PENDING_APPROVAL', 'PUBLISHED_ORG')`.
  - Le script `09_reset_db_first_boot.py` vide déjà `catalog_items` lors d'un `pnpm db:reset`, garantissant la vérité terrain Jour 0 (`0` agent et `0` compétence après réinitialisation).
- **Opportunités de Factorisation & Résorption de Dette Technique Naissante** :
  - Création d'un service domaine dédié `AgentsAndSkillsManagementService` dans `packages/orcia-core/src/orcia_core/orchestration/agents_and_skills_manager.py` (< 320 lignes) + adaptateur SQL PostgreSQL 18 dans `packages/orcia-core/src/orcia_core/orchestration/_internal/sql_agents_and_skills.py` (< 250 lignes) réutilisant `LLMPort` (`DeterministicCassetteLLM` par défaut) et le calcul d'empreinte `SHA-256` de `orcia_core.catalog`.
  - Création du composant `@orcia/ui` `AgentsAndSkillsManagerView` dans `packages/ui/src/components/AgentsAndSkillsManagerView.tsx` (< 340 lignes), 100 % piloté par `labels` FR/EN, zéro couleur hexadécimale en dur, respectant `tokens.css`.
  - Conservation dans `apps/web/src/features/catalog/index.tsx` des composants et `data-testid` existants (`catalog-explorer-panel`, `remote-service-test-bench`) pour garantir zéro régression sur les suites de tests existantes.

---

## 2. Plan d'Implémentation

### 2.1 Schéma de Données & Migrations Alembic (`infra/migrations/versions/...`, si applicable)
- Aucune nouvelle migration Alembic n'est requise : la table `catalog_items` issue des révisions `0003_story_1_3` et `0023_story_9_5` possède déjà :
  - `id UUID PRIMARY KEY` (`UUIDv7`), `resource_id VARCHAR(128) UNIQUE`, `uri TEXT`, `title VARCHAR(255)`, `description TEXT`, `resource_type VARCHAR(32)` (`'agent' | 'skill'`), `source_format VARCHAR(32)` (`'ORCIA'`), `version VARCHAR(64)`, `sha256 VARCHAR(64)`, `cas_key VARCHAR(128)`, `visibility_scope VARCHAR(32)` (`'SHARED_WORKSPACE'`), `owner_org_unit_id UUID`, `item_type VARCHAR(64)` (`'USER_AGENT' | 'USER_SKILL'`), et `metadata_jsonb JSONB` (stockant les paramètres, instructions, format de sortie, niveau de réflexion et `skill_ids` rattachés).

### 2.2 Noyau Métier Hexagonal, Orchestration & Workers (`packages/orcia-core/`, `apps/worker/`, `infra/sandbox/`)
- `packages/orcia-core/src/orcia_core/orchestration/agents_and_skills_manager.py` :
  - Entités immuables `ManagedSkillRecord`, `ManagedAgentRecord`, `SkillExecutionOutcome`, `AgentExecutionOutcome`.
  - Service `AgentsAndSkillsManagementService` démarrant à vide (`0` compétence, `0` agent au Jour 0) :
    - `list_state()` : retourne `(agents, skills)`.
    - `upsert_skill(...)` : crée ou met à jour une Compétence (`slug`, `command_handle` `/slug`, `name`, `objective`, `input_parameters`, `instructions`, `expected_output_format`).
    - `delete_skill(skill_id)` : supprime la Compétence et retire automatiquement `skill_id` de tous les `ManagedAgentRecord.skill_ids` qui y faisaient référence.
    - `execute_skill(skill_id, input_text, parameters)` : exécute la Compétence de façon déterministe et structurée en appliquant ses instructions, ses paramètres et son format de sortie attendu.
    - `upsert_agent(...)` : crée ou met à jour un Agent (`slug`, `handle` `@slug`, `name`, `role_mission`, `instructions`, `thinking_level`, `skill_ids` filtrés sur les compétences existantes).
    - `set_agent_skills(agent_id, skill_ids)` : rattache/détache en 1 clic les Compétences d'un Agent.
    - `delete_agent(agent_id)` : supprime un Agent.
    - `execute_agent(agent_id, prompt)` : exécute chaque Compétence rattachée pertinente puis invoque `LLMPort` (`DeterministicCassetteLLM`) avec le rôle de l'Agent et les résultats des compétences mobilisées, retournant la réponse synthétique et la trace `invoked_skills`.
- `packages/orcia-core/src/orcia_core/orchestration/_internal/sql_agents_and_skills.py` :
  - Adaptateur PostgreSQL 18 asynchrone (`load_agents_and_skills_from_postgres18`, `persist_skill_to_postgres18`, `delete_skill_from_postgres18`, `persist_agent_to_postgres18`, `delete_agent_from_postgres18`) persistant dans `catalog_items` (`item_type IN ('USER_SKILL', 'USER_AGENT')`) avec création idempotente de l'`org_unit` racine `orcia-root` si nécessaire.

### 2.3 Couche Backend API, Sécurité & Contrats (`apps/api/`, `packages/api-client/`)
- `apps/api/src/orcia_api/schemas/agents_and_skills.py` :
  - Schémas Pydantic v2 stricts : `SkillItemResponse`, `UpsertSkillRequest`, `ExecuteSkillRequest`, `ExecuteSkillResponse`, `AgentItemResponse`, `UpsertAgentRequest`, `UpdateAgentSkillsRequest`, `ExecuteAgentRequest`, `ExecuteAgentResponse`, `AgentsAndSkillsListResponse`, `DeleteResourceResponse`.
- `apps/api/src/orcia_api/routers/agents_and_skills.py` (enregistré dans `apps/api/src/orcia_api/main.py` et `dependencies/workspace_and_packs.py`) :
  - `GET /api/v1/agents-and-skills`
  - `POST /api/v1/agents-and-skills/skills`
  - `DELETE /api/v1/agents-and-skills/skills/{skill_id}`
  - `POST /api/v1/agents-and-skills/skills/{skill_id}/execute`
  - `POST /api/v1/agents-and-skills/agents`
  - `PATCH /api/v1/agents-and-skills/agents/{agent_id}/skills`
  - `DELETE /api/v1/agents-and-skills/agents/{agent_id}`
  - `POST /api/v1/agents-and-skills/agents/{agent_id}/execute`
- `packages/api-client/src/domains/agentsAndSkills.ts` & `packages/api-client/src/index.ts` :
  - Client typé `createAgentsAndSkillsDomainClient` exposé dans `createOrciaApiClient` et régénération OpenAPI 3.1 (`scripts/export_openapi.py` avec shard `agents_and_skills`).

### 2.4 Interface Utilisateur & Expérience (`packages/ui/` & `apps/web/`)
- `packages/ui/src/components/AgentsAndSkillsManagerView.tsx` (exporté dans `packages/ui/src/index.ts`) :
  - Barre de navigation à 3 sous-vues :
    1. `🤖 Mes Agents` (`agents-subview-tab-agents`) : état vide accueillant au Jour 0, formulaire de création d'Agent (Nom, Rôle / Mission métier, Instructions, Niveau de réflexion, cases à cocher des Compétences associées), cartes d'Agents avec cases à cocher de rattachement/détachement en 1 clic et panneau « Tester maintenant » en 1 clic affichant la réponse et les compétences mobilisées.
    2. `🛠️ Compétences` (`agents-subview-tab-skills`) : état vide accueillant au Jour 0, encart explicatif d'utilisation (`/nom-de-la-competence` dans `Mon Assistant` ou rattachement aux Agents et Processus), formulaire de création de Compétence (Nom, Objectif métier, Paramètres attendus, Instructions / Méthode d'exécution, Format du résultat attendu), cartes de Compétences avec bouton « Tester maintenant » en 1 clic et suppression propre.
    3. `🔌 Connexions externes` (`agents-subview-tab-connections`) : affiche le banc de test des services externes (`children` / `RemoteServiceTestBenchAndMcpExposureView`).
- `apps/web/src/features/catalog/index.tsx` & `apps/web/src/components/ShellContainer.tsx` :
  - Montage de `AgentsAndSkillsManagerView` dans `CatalogFeaturePanel` avec hydratation au chargement via `GET /api/v1/agents-and-skills` et persistance `localStorage` (`orcia.agents_and_skills.v1`) pour survie instantanée au `F5`.
  - Déverrouillage de l'entrée `🤖 Mes Agents` dans la barre latérale dès le démarrage pour permettre à l'utilisateur de créer ses Compétences et ses Agents à tout moment, tout en conservant le comportement attendu par les tests existants.

---

## 3. Bilan des Modifications & Résultats (Post-Implémentation)

### 3.1 Fichiers Créés ou Modifiés

| Fichier | Nature | Rôle & Responsabilité |
| :--- | :--- | :--- |
| [`packages/orcia-core/src/orcia_core/orchestration/agents_and_skills_manager.py`](file:///home/romain/Documents/Projects/ORCIA/packages/orcia-core/src/orcia_core/orchestration/agents_and_skills_manager.py) | **Créé** | Service domaine `AgentsAndSkillsManagementService` + entités immuables (`ManagedSkillRecord`, `ManagedAgentRecord`, `SkillExecutionOutcome`, `AgentExecutionOutcome`, `InvokedSkillTraceItem`) : création, rattachement en 1 clic (`set_agent_skills`), détachement automatique à la suppression d'une compétence et exécution déterministe en 1 clic (`DeterministicCassetteLLM`). |
| [`packages/orcia-core/src/orcia_core/orchestration/_internal/sql_agents_and_skills.py`](file:///home/romain/Documents/Projects/ORCIA/packages/orcia-core/src/orcia_core/orchestration/_internal/sql_agents_and_skills.py) | **Créé** | Adaptateur PostgreSQL 18 asynchrone (`load_agents_and_skills_from_postgres18`, `persist_skill_to_postgres18`, `persist_agent_to_postgres18`, `delete_skill_from_postgres18`, `delete_agent_from_postgres18`) stockant `USER_SKILL` et `USER_AGENT` dans `catalog_items`. |
| [`packages/orcia-core/src/orcia_core/orchestration/__init__.py`](file:///home/romain/Documents/Projects/ORCIA/packages/orcia-core/src/orcia_core/orchestration/__init__.py) | **Modifié** | Ré-export public de `AgentsAndSkillsManagementService`, des entités associées et des fonctions de persistance SQL PostgreSQL 18. |
| [`apps/api/src/orcia_api/schemas/agents_and_skills.py`](file:///home/romain/Documents/Projects/ORCIA/apps/api/src/orcia_api/schemas/agents_and_skills.py) | **Créé** | Schémas de transport HTTP/OpenAPI 3.1 Pydantic v2 (`SkillItemResponse`, `UpsertSkillRequest`, `ExecuteSkillRequest`, `ExecuteSkillResponse`, `AgentItemResponse`, `UpsertAgentRequest`, `UpdateAgentSkillsRequest`, `ExecuteAgentRequest`, `ExecuteAgentResponse`, `AgentsAndSkillsListResponse`, `DeleteSkillOrAgentResponse`). |
| [`apps/api/src/orcia_api/routers/agents_and_skills.py`](file:///home/romain/Documents/Projects/ORCIA/apps/api/src/orcia_api/routers/agents_and_skills.py) | **Créé** | Routeur FastAPI `/api/v1/agents-and-skills` exposant les 8 endpoints REST (`GET`, `POST /skills`, `DELETE /skills/{id}`, `POST /skills/{id}/execute`, `POST /agents`, `PATCH /agents/{id}/skills`, `DELETE /agents/{id}`, `POST /agents/{id}/execute`) avec garde-fou `ERR_OBSERVER_MODE_READ_ONLY` (`403`) et synchronisation PostgreSQL 18. |
| [`apps/api/src/orcia_api/dependencies/workspace_and_packs.py`](file:///home/romain/Documents/Projects/ORCIA/apps/api/src/orcia_api/dependencies/workspace_and_packs.py) & [`apps/api/src/orcia_api/dependencies/__init__.py`](file:///home/romain/Documents/Projects/ORCIA/apps/api/src/orcia_api/dependencies/__init__.py) | **Modifiés** | Injection `get_agents_and_skills_service` dans le Composition Root FastAPI (`app.state.agents_and_skills_service`). |
| [`apps/api/src/orcia_api/main.py`](file:///home/romain/Documents/Projects/ORCIA/apps/api/src/orcia_api/main.py) & [`scripts/export_openapi.py`](file:///home/romain/Documents/Projects/ORCIA/scripts/export_openapi.py) | **Modifiés** | Montage de `agents_and_skills_router` et génération du 9e shard OpenAPI 3.1 `agents_and_skills.ts`. |
| [`packages/api-client/src/domains/agentsAndSkills.ts`](file:///home/romain/Documents/Projects/ORCIA/packages/api-client/src/domains/agentsAndSkills.ts), [`packages/api-client/src/helpers.ts`](file:///home/romain/Documents/Projects/ORCIA/packages/api-client/src/helpers.ts) & [`packages/api-client/src/index.ts`](file:///home/romain/Documents/Projects/ORCIA/packages/api-client/src/index.ts) | **Créé / Modifiés** | Client SDK typé `createAgentsAndSkillsDomainClient` (`listAgentsAndSkills`, `upsertSkill`, `deleteSkill`, `executeSkill`, `upsertAgent`, `updateAgentSkills`, `deleteAgent`, `executeAgent`) et support des méthodes HTTP `PUT`, `PATCH`, `DELETE` dans `requestJson`. |
| [`packages/ui/src/components/AgentsAndSkillsManagerView.tsx`](file:///home/romain/Documents/Projects/ORCIA/packages/ui/src/components/AgentsAndSkillsManagerView.tsx) & [`packages/ui/src/index.ts`](file:///home/romain/Documents/Projects/ORCIA/packages/ui/src/index.ts) | **Créé / Modifié** | Composant Design System Direction C `@orcia/ui` à 3 sous-vues (`🤖 Mes Agents`, `🛠️ Compétences`, `🔌 Connexions externes`), zéro couleur hexadécimale en dur, 100 % piloté par `labels`. |
| [`apps/web/src/i18n/locales/governance_and_packs_labels.ts`](file:///home/romain/Documents/Projects/ORCIA/apps/web/src/i18n/locales/governance_and_packs_labels.ts) | **Modifié** | Section bilingue `agentsAndSkillsManager` FR/EN (parité récursive 100 %, zéro jargon technique interne). |
| [`apps/web/src/features/catalog/index.tsx`](file:///home/romain/Documents/Projects/ORCIA/apps/web/src/features/catalog/index.tsx) | **Modifié** | Montage de `AgentsAndSkillsManagerView` sur `/agents` et `/catalog` avec hydratation via `@orcia/api-client`, persistance `localStorage` (`orcia.agents_and_skills.v1`) pour survie au `F5` et conservation des panneaux existants (`CatalogExplorerPanel`, `RemoteServiceTestBenchAndMcpExposureView`). |
| [`tests/unit/test_agents_and_skills_router_and_service.py`](file:///home/romain/Documents/Projects/ORCIA/tests/unit/test_agents_and_skills_router_and_service.py), [`packages/ui/src/__tests__/agents-and-skills.test.tsx`](file:///home/romain/Documents/Projects/ORCIA/packages/ui/src/__tests__/agents-and-skills.test.tsx) & [`apps/web/src/__tests__/i18n-and-shell.test.tsx`](file:///home/romain/Documents/Projects/ORCIA/apps/web/src/__tests__/i18n-and-shell.test.tsx) | **Créés / Modifiés** | Suites de tests unitaires Python, contrats HTTP FastAPI, adaptateur SQL PostgreSQL 18, tests composants `@orcia/ui` et test d'intégration frontend de survie au `F5` (`unmount()` + `render()`). |

### 3.2 Métriques & Validation des 5 Couches de Tests (`AD-17`)

- **Couche 1 — Qualité Statique, Architecture & Contrats** :
  - `ruff check .` & `ruff format --check .` : **PASS** (`0` erreur sur `501` fichiers).
  - `mypy --strict packages/orcia-kernel packages/orcia-core apps/api apps/worker` : **PASS** (`0` erreur sur `207` fichiers sources).
  - `lint-imports` (`AD-19`) : **PASS** (`5` contrats d'architecture hexagonale maintenus, `0` brisé).
  - `scripts/export_openapi.py --check` : **PASS** (`0-diff` sur `openapi.json` et les `9` shards générés).
  - `lint_spine.py` : **PASS** (`total_findings: 0`).
  - `pnpm turbo run lint typecheck` : **PASS** (`@orcia/api-client`, `@orcia/ui`, `@orcia/web`, isolation des 8 modules `features/<domaine>/` vérifiée).
- **Couche 2 — Persistance SQL PostgreSQL 18 & Garde-fou Zéro Adaptateur Orphelin** :
  - `test_agents_and_skills_postgres18_sql_adapter_queries` : **PASS** (vérification de l'upsert `INSERT INTO catalog_items ... ON CONFLICT (resource_id) DO UPDATE`, de la lecture `SELECT` filtrée sur `USER_SKILL` / `USER_AGENT`, du détachement automatique des `skill_ids` lors d'un `DELETE` de compétence et de la suppression d'agent).
  - Toutes les fonctions de `sql_agents_and_skills.py` sont appelées activement par `apps/api/src/orcia_api/routers/agents_and_skills.py`.
- **Couche 3 — Contrat HTTP FastAPI & RBAC (`RFC 9457 Problem Details`)** :
  - `test_agents_and_skills_fastapi_router_contract` : **PASS** (état initial Jour 0 vide `{"agents": [], "skills": []}`, rejet `HTTP 403 ERR_OBSERVER_MODE_READ_ONLY` en mode observateur, création et exécution en 1 clic d'une Compétence et d'un Agent, modification des compétences rattachées via `PATCH`, détachement automatique lors de la suppression de la compétence).
- **Couche 4 — Tests Composants Design System `@orcia/ui`** :
  - `packages/ui/src/__tests__/agents-and-skills.test.tsx` & `ui-isolation.test.ts` : **PASS** (`14` fichiers de tests, `44` tests passants).
- **Couche 5 — Intégration SPA `@orcia/web`, Parité `i18n` FR/EN & Gate de « Survie au F5 »** :
  - `apps/web/src/__tests__/i18n-and-shell.test.tsx` : **PASS** (`15/15` tests passants, incluant la création d'une Compétence, son test en 1 clic, la création d'un Agent avec compétence rattachée, son exécution en 1 clic, puis `unmount()` + `render()` sur `/agents` prouvant la survie complète de l'état au rafraîchissement `F5`).
