# 2026-11-04 — Câblage Vertical & Persistance PostgreSQL 18 des Écrans Epics 8 à 12 (Garde-Fous Anti-Silos)

> **Convention de nommage du fichier (Obligatoire — créé AVANT toute modification de code)** :
> - Demande d'ajustement, correctif ou évolution hors Story : `docs/implementation-artifacts/tech-lead-reports/2026-11-04-cablage-vertical-persistance-epics-8-a-12-tech-lead-report.md`

- **Date** : 2026-11-04
- **Story / Clé Sprint** : `2026-11-04-cablage-vertical-persistance-epics-8-a-12` (`Post-Epic 12 — Audit Transverse & Câblage Vertical P0/P1/P2`)
- **Auteur / Contexte** : Résolution exhaustive des silos en mémoire identifiés par l'Audit des Autres Écrans des Epics 8 à 12 (`useState` éphémères dans `apps/web/src/components/platformSetupStore.tsx` et `apps/web/src/features/*`, méthodes manquantes dans `@orcia/api-client`, routeurs FastAPI déconnectés de PostgreSQL 18 et `session_factory=None` dans `workspace_and_packs.py`). Couvre `AD-1`, `AD-10`, `AD-14`, `AD-15`, `AD-17`, `AD-19`, `AD-20`, `AD-21`, `FR-28`, `UX-DR1..16`.
- **Commits associés** : `en-cours`

---

## 1. Analyse du Besoin & Étude d'Impact Tech Lead (Pré-Implémentation)

### 1.1 Contexte & Problématique
- **Problématique constatée lors de l'audit des écrans Epics 8 à 12** :
  1. **Silo Frontend `platformSetupStore.tsx` (`apps/web/src/components/platformSetupStore.tsx`)** : Si `platformAdmin` a été câblé sur PostgreSQL 18 et `localStorage`, les **11 autres collections métiers** (`orgUnits`, `rbacGrants`, `llmTiers`, `workspaces`, `datasources`, `packs`, `workflows`, `runs`, `catalogItems`, `ontologyConcepts`, `auditEvents`) demeuraient dans des `useState([])` purement éphémères en RAM navigateur. Conséquence : au moindre rechargement (`F5`) de l'URL, l'utilisateur perdait ses BU/Espaces, ses règles RBAC, ses paliers IA (`llmTiers`), ses Espaces de Travail (`workspaces`), ses connecteurs (`datasources`), et les entrées de menu `Mon Assistant`, `Mes Agents`, `Mes Processus` et `FinOps` redevenaient grisées (`disabled`).
  2. **Silo Backend `bootstrap.py` & Persistance SQL Jour 0 / Configuration (`apps/api/src/orcia_api/routers/bootstrap.py`)** :
     - Aucun endpoint `GET /api/v1/bootstrap/platform-setup-state` ni `PUT /api/v1/bootstrap/platform-setup-state` ne permettait de sauvegarder et relire de façon atomique l'état complet de configuration de la plateforme dans PostgreSQL 18 (`platform_settings`, `org_units`, `workspaces`, `llm_model_endpoints`).
     - La route `POST /api/v1/bootstrap/welcome-setup/progressive-llm` n'enregistrait le modèle IA qu'en mémoire dans `ProgressiveDay0AccostageService` sans l'insérer dans `llm_model_endpoints` ni `platform_settings`.
  3. **Silo Composition Root (`apps/api/src/orcia_api/dependencies/core_and_lifespan.py` & `workspace_and_packs.py`)** :
     - `PackBuilderSystemService` (Story 11.4) et `HelpGenerationAndHotAttachmentService` (Story 11.5) possèdent tous deux un paramètre `session_factory: async_sessionmaker[AsyncSession] | None = None` et des méthodes `_persist_pack_and_audit()` / `_persist_help_catalog_items()` écrivant dans `catalog_items` et `domain_events_outbox`, mais `workspace_and_packs.py:L63-86` les instancie sans leur passer `session_factory=getattr(request.app.state, "session_maker", None)` (`session_factory` restait toujours `None`).
     - Dans `core_and_lifespan.py`, `app_lifespan` n'attachait pas de `session_maker` par défaut (`async_sessionmaker`) lorsque l'application démarrait hors test d'intégration pré-injecté.
  4. **Silo SDK `@orcia/api-client` & Écrans `features/` (`Epics 9, 10, 11, 12`)** :
     - Les méthodes typées `getPlatformSetupState()`, `savePlatformSetupState()`, `searchFederated()`, `getUserPreferences()`, `updateUserPreferences()`, `resolveContextualHelp()`, `executeAssistantTurn()`, `listAssistantFolders()`, `createAssistantFolder()`, `compileDnaStarlark()`, `runRemoteServiceTestBench()` et `validateHelpArticle()` manquaient dans `packages/api-client/src/domains/bootstrapAndOntology.ts`.
     - Les écrans `apps/web/src/features/{inbox,workspaces,catalog,gates,ontology}/index.tsx` conservaient des états locaux déconnectés du SDK `@orcia/api-client` et du `platformSetupStore` persisté.

### 1.2 Exploration, Analyse d'Impact GitNexus, Factorisation & Dette Technique
- **Analyse d'Impact GitNexus (`gitnexus_query`, `gitnexus_context`, `gitnexus_impact` avec `repo: "ORCIA"`)** :
  - `gitnexus_impact({target: "PlatformSetupProvider", direction: "upstream", repo: "ORCIA"})` : appelé par `ShellContainer.tsx` et utilisé via `usePlatformSetup()` dans `ShellContainer.tsx`, `routes/settings.tsx`, `routes/wizards.tsx` et les 6 modules `features/{cockpit,inbox,workspaces,catalog,ontology,finops}/index.tsx` (`risk: MEDIUM` — les signatures existantes de `PlatformSetupContextValue` doivent rester 100 % rétro-compatibles tout en ajoutant les opérations de suppression/réinitialisation et la persistance automatique).
  - `gitnexus_impact({target: "PackBuilderSystemService", direction: "upstream", repo: "ORCIA"})` & `gitnexus_impact({target: "HelpGenerationAndHotAttachmentService", direction: "upstream", repo: "ORCIA"})` : `risk: UNKNOWN` (injection via FastAPI `Depends` dans `routers/pack_builder.py` et `dependencies/workspace_and_packs.py`).
  - `gitnexus_impact({target: "createBootstrapAndOntologyDomainClient", direction: "upstream", repo: "ORCIA"})` : agrégé dans `createOrciaApiClient` (`packages/api-client/src/index.ts`), consommé par `platformSetupStore.tsx` et les tests de contrat OpenAPI (`risk: LOW`).
  - `gitnexus_impact({target: "initialize_app_services", direction: "upstream", repo: "ORCIA"})` : appelé dans `app_lifespan` et les providers `Depends` de `core_and_lifespan.py` (`risk: MEDIUM`).
- **Exploration & Chiffres Clés (Base de Données / Conteneurs / Volumétrie)** :
  - Vérification des tables PostgreSQL 18 créées par les migrations `0002`, `0005` et `0022` :
    - `platform_settings` (`0022`) : `UNIQUE (scope_level, scope_id, category, key)` avec `category IN ('iam', 'connectors', 'ai-models', 'packs', 'workflows', 'audit')` et `value_jsonb JSONB`.
    - `org_units` (`0002`) : `id UUID`, `slug VARCHAR(128) UNIQUE`, `name`, `unit_type IN ('ENTERPRISE', 'BU', 'TRIBE', 'TEAM', 'SUB_TEAM')`, `parent_id`.
    - `workspaces` (`0002`) : `id UUID`, `slug VARCHAR(128) UNIQUE`, `name`, `owner_org_unit_id`, `visibility_mode`, `settings_jsonb`.
    - `llm_model_endpoints` (`0005`) : `id UUID`, `endpoint_key VARCHAR(128) UNIQUE`, `provider_slug`, `model_family`, `model_name`, `endpoint_uri`.
  - Vérification de `infra/scripts/maintenance/09_reset_db_first_boot.py` : les tables `platform_settings`, `llm_model_endpoints`, `workspaces`, `org_units`, `users`, `catalog_items`, `role_permission_grants`, `workspace_datasources` et `ontology_concepts` figurent déjà toutes dans `ORDERED_MUTABLE_TABLES_TO_CLEAR`.
- **Opportunités de Factorisation & Contrôle de Volumétrie** :
  - `apps/api/src/orcia_api/routers/bootstrap.py` fait actuellement `412` lignes : nous allons factoriser la synchronisation PostgreSQL 18 dans `packages/orcia-core/src/orcia_core/bootstrap/_internal/sql_platform_setup_store.py` afin de garder `routers/bootstrap.py` concis et lisible.
  - **Préservation stricte anti-conflits Git** : aucune modification dans `packages/ui/` ni dans `apps/web/src/components/ShellContainer.tsx` (réservés au sous-agent RGAA Modales).

---

## 2. Plan d'Implémentation

### 2.1 Schéma de Données & Migrations Alembic (`infra/migrations/versions/...`, si applicable)
- Aucune nouvelle migration Alembic requise : les tables PostgreSQL 18 `platform_settings` (`0022`), `org_units` (`0002`), `workspaces` (`0002`), `llm_model_endpoints` (`0005`), `catalog_items` (`0003`) et `domain_events_outbox` (`0012`) couvrent intégralement les besoins de persistance atomique.
- Le script `09_reset_db_first_boot.py` purge déjà l'intégralité de ces tables lors d'un `pnpm db:reset`.

### 2.2 Noyau Métier Hexagonal, Orchestration & Workers (`packages/orcia-core/`)
- Création de [`packages/orcia-core/src/orcia_core/bootstrap/_internal/sql_platform_setup_store.py`](file:///home/romain/.gemini/antigravity/worktrees/1de3c5dc-2b06-4bb5-b4cf-fabf6b66fb31/subagent-Epics-8-12-Vertical-Persistence-Wiring-Engineer-self-dc5f94d1/packages/orcia-core/src/orcia_core/bootstrap/_internal/sql_platform_setup_store.py) et ré-export public dans [`packages/orcia-core/src/orcia_core/bootstrap/__init__.py`](file:///home/romain/.gemini/antigravity/worktrees/1de3c5dc-2b06-4bb5-b4cf-fabf6b66fb31/subagent-Epics-8-12-Vertical-Persistence-Wiring-Engineer-self-dc5f94d1/packages/orcia-core/src/orcia_core/bootstrap/__init__.py) (`AD-19`) :
  - `PlatformSetupSnapshotRecord` (dataclass immuable portant les 11 collections + métadonnées `first_admin_initialized`, `first_admin_email`, `first_admin_display_name`).
  - `load_platform_setup_state_from_postgres18(engine, *, orcia_env="local")` :
    - Interroge `get_first_platform_admin_from_postgres18(engine, orcia_env=orcia_env)` pour vérifier l'état réel de la table `users`.
    - Relit l'état complet depuis `platform_settings` (`scope_level = 'GLOBAL'`, `category = 'iam'`, `key = 'platform_setup_state_v1'`) et réconcilie avec les lignes relationnelles de `llm_model_endpoints` et `workspaces` si présentes.
  - `save_platform_setup_state_to_postgres18(engine, snapshot)` :
    - Persiste de manière transactionnelle (`async with engine.begin() as conn`) l'état JSONB complet dans `platform_settings` (`ON CONFLICT (scope_level, scope_id, category, key) DO UPDATE`).
    - Synchronise les tables relationnelles PostgreSQL 18 `org_units`, `workspaces` et `llm_model_endpoints` (upserts idempotents + nettoyage des entrées supprimées).
  - `persist_progressive_llm_endpoint_to_postgres18(engine, endpoint)` :
    - Insère/met à jour le modèle IA dans `llm_model_endpoints` lors de l'appel à `POST /api/v1/bootstrap/welcome-setup/progressive-llm` et met à jour `llm_tiers` dans `platform_settings` si nécessaire.

### 2.3 Couche Backend API, Sécurité & Contrats (`apps/api/`, `packages/api-client/`)
- [`apps/api/src/orcia_api/schemas/bootstrap.py`](file:///home/romain/.gemini/antigravity/worktrees/1de3c5dc-2b06-4bb5-b4cf-fabf6b66fb31/subagent-Epics-8-12-Vertical-Persistence-Wiring-Engineer-self-dc5f94d1/apps/api/src/orcia_api/schemas/bootstrap.py) :
  - Ajout des schémas Pydantic v2 `PlatformSetupStatePutRequest` et `PlatformSetupStateResponse` portant `first_admin_initialized`, `first_admin_email`, `first_admin_display_name` et les 11 collections (`org_units`, `rbac_grants`, `llm_tiers`, `workspaces`, `datasources`, `packs`, `workflows`, `runs`, `catalog_items`, `ontology_concepts`, `audit_events`) + `trace_id`.
- [`apps/api/src/orcia_api/routers/bootstrap.py`](file:///home/romain/.gemini/antigravity/worktrees/1de3c5dc-2b06-4bb5-b4cf-fabf6b66fb31/subagent-Epics-8-12-Vertical-Persistence-Wiring-Engineer-self-dc5f94d1/apps/api/src/orcia_api/routers/bootstrap.py) :
  - Exposition de `GET /api/v1/bootstrap/platform-setup-state` et `PUT /api/v1/bootstrap/platform-setup-state` connectés à PostgreSQL 18 (avec repli en mémoire dans `app.state` uniquement lorsque `ORCIA_DISABLE_PG_BOOTSTRAP_SYNC=1` ou hors base en test unitaire pur) et synchronisant `ProgressiveDay0AccostageService` (enregistrement automatique des `llm_tiers` dans `svc.register_progressive_llm_endpoint`).
  - Dans `POST /api/v1/bootstrap/welcome-setup/progressive-llm`, persistance dans PostgreSQL 18 (`llm_model_endpoints` + `platform_settings`).
- [`apps/api/src/orcia_api/dependencies/workspace_and_packs.py`](file:///home/romain/.gemini/antigravity/worktrees/1de3c5dc-2b06-4bb5-b4cf-fabf6b66fb31/subagent-Epics-8-12-Vertical-Persistence-Wiring-Engineer-self-dc5f94d1/apps/api/src/orcia_api/dependencies/workspace_and_packs.py) & [`apps/api/src/orcia_api/dependencies/core_and_lifespan.py`](file:///home/romain/.gemini/antigravity/worktrees/1de3c5dc-2b06-4bb5-b4cf-fabf6b66fb31/subagent-Epics-8-12-Vertical-Persistence-Wiring-Engineer-self-dc5f94d1/apps/api/src/orcia_api/dependencies/core_and_lifespan.py) :
  - Dans `core_and_lifespan.py`, attachement d'un `async_sessionmaker` par défaut basé sur `resolve_database_url()` dans `app.state.session_maker` si non pré-injecté.
  - Dans `workspace_and_packs.py`, passage de `session_factory=getattr(request.app.state, "session_maker", None)` à `PackBuilderSystemService(session_factory=...)` et `HelpGenerationAndHotAttachmentService(session_factory=...)`.
- [`packages/api-client/src/domains/bootstrapAndOntology.ts`](file:///home/romain/.gemini/antigravity/worktrees/1de3c5dc-2b06-4bb5-b4cf-fabf6b66fb31/subagent-Epics-8-12-Vertical-Persistence-Wiring-Engineer-self-dc5f94d1/packages/api-client/src/domains/bootstrapAndOntology.ts) :
  - Régénération OpenAPI 3.1 (`0-diff`) via `.venv/bin/python scripts/export_openapi.py`.
  - Ajout des méthodes typées `getPlatformSetupState()`, `savePlatformSetupState(payload)`, `searchFederated(query, scope)`, `getUserPreferences()`, `updateUserPreferences(payload)`, `resolveContextualHelp(route, lang)`, `executeAssistantTurn(payload)`, `listAssistantFolders(workspaceId)`, `createAssistantFolder(payload)`, `compileDnaStarlark(workspaceId, payload)`, `runRemoteServiceTestBench(payload)`, et `validateHelpArticle(payload)`.

### 2.4 Interface Utilisateur & Expérience (`apps/web/`)
- [`apps/web/src/components/platformSetupStore.tsx`](file:///home/romain/.gemini/antigravity/worktrees/1de3c5dc-2b06-4bb5-b4cf-fabf6b66fb31/subagent-Epics-8-12-Vertical-Persistence-Wiring-Engineer-self-dc5f94d1/apps/web/src/components/platformSetupStore.tsx) :
  - Persistance et réhydratation immédiate au démarrage via `localStorage` (`orcia.platform_setup_state.v1`) **et** synchronisation avec le backend PostgreSQL 18 via `getPlatformSetupState()` :
    - Si `first_admin_initialized === false` au retour du backend (après `pnpm db:reset`), purge complète de `orcia.platform_admin.v1` et `orcia.platform_setup_state.v1` et remise à zéro des 11 collections en mémoire pour repartir d'une interface 100 % vierge.
    - Si `first_admin_initialized === true` ou que le backend renvoie des collections persistées, réhydratation des 11 collections (`orgUnits`, `rbacGrants`, `llmTiers`, `workspaces`, `datasources`, `packs`, `workflows`, `runs`, `catalogItems`, `ontologyConcepts`, `auditEvents`).
  - Chaque mutation (`addOrgUnit`, `removeOrgUnit`, `addRbacGrant`, `removeRbacGrant`, `removeRbacGrantsByIds`, `upsertLlmTier`, `removeLlmTier`, `createWorkspace`, `updateWorkspacePhase`, `removeWorkspace`, `registerDatasource`, `removeDatasource`, `registerPack`, `removePack`, `upsertWorkflow`, `removeWorkflow`, `launchRun`, `addOntologyConcept`, `resetPlatformSetup`) met à jour de façon synchrone `orcia.platform_setup_state.v1` et déclenche `savePlatformSetupState()` vers PostgreSQL 18.
- Câblage des écrans features (`apps/web/src/features/{inbox,workspaces,catalog,gates,ontology}/index.tsx`) :
  - `inbox/index.tsx` : appel à `executeAssistantTurn` et `createAssistantFolder` / `listAssistantFolders` via `@orcia/api-client` (avec repli gracieux hors-ligne en test unitaire) et persistance locale des dossiers/réponses.
  - `workspaces/index.tsx` : câblage de `WorkspaceFiveTabsAndExternalRebaseView` sur `datasources` et `ontologyConcepts` du `platformSetupStore` pour que les sources et concepts survivent au `F5`, et câblage de `compileDnaStarlark`.
  - `catalog/index.tsx`, `gates/index.tsx`, `ontology/index.tsx` : câblage aux méthodes `@orcia/api-client` (`runRemoteServiceTestBench`, `validateHelpArticle`, `resolveContextualHelp`, `upsertOntologyConcept`) et au store persisté.

---

## 3. Bilan des Modifications & Résultats (Post-Implémentation)

### 3.1 Tableau Récapitulatif des Fichiers Créés & Modifiés

| Fichier | Action | Lignes | Responsabilité & Changements Clés |
| --- | --- | --- | --- |
| [`packages/orcia-core/src/orcia_core/bootstrap/_internal/sql_platform_setup_store.py`](file:///home/romain/.gemini/antigravity/worktrees/1de3c5dc-2b06-4bb5-b4cf-fabf6b66fb31/subagent-Epics-8-12-Vertical-Persistence-Wiring-Engineer-self-dc5f94d1/packages/orcia-core/src/orcia_core/bootstrap/_internal/sql_platform_setup_store.py) | Créé | `421` | Adaptateur SQL PostgreSQL 18 (`PlatformSetupSnapshotRecord`, `save_platform_setup_state_to_postgres18`, `load_platform_setup_state_from_postgres18`, `persist_progressive_llm_endpoint_to_postgres18`) synchronisant `platform_settings`, `org_units`, `workspaces` et `llm_model_endpoints`. |
| [`packages/orcia-core/src/orcia_core/bootstrap/__init__.py`](file:///home/romain/.gemini/antigravity/worktrees/1de3c5dc-2b06-4bb5-b4cf-fabf6b66fb31/subagent-Epics-8-12-Vertical-Persistence-Wiring-Engineer-self-dc5f94d1/packages/orcia-core/src/orcia_core/bootstrap/__init__.py) | Modifié | `188` | Ré-export public des primitives de persistance `PlatformSetupSnapshotRecord` et fonctions PostgreSQL 18 (`AD-19`, zéro import `_internal` hors domaine). |
| [`packages/orcia-core/src/orcia_core/bootstrap/models.py`](file:///home/romain/.gemini/antigravity/worktrees/1de3c5dc-2b06-4bb5-b4cf-fabf6b66fb31/subagent-Epics-8-12-Vertical-Persistence-Wiring-Engineer-self-dc5f94d1/packages/orcia-core/src/orcia_core/bootstrap/models.py) | Modifié | `271` | Ajout de `ModelRouterService.replace_endpoints()` pour resynchroniser atomiquement les endpoints IA depuis PostgreSQL 18. |
| [`packages/orcia-core/src/orcia_core/bootstrap/progressive_accostage.py`](file:///home/romain/.gemini/antigravity/worktrees/1de3c5dc-2b06-4bb5-b4cf-fabf6b66fb31/subagent-Epics-8-12-Vertical-Persistence-Wiring-Engineer-self-dc5f94d1/packages/orcia-core/src/orcia_core/bootstrap/progressive_accostage.py) | Modifié | `328` | Ajout de `sync_platform_setup_snapshot()` recalculant les jalons `Accostage 1/6..6/6` et le mode d'orthogonalité `AD-10` à partir de l'état persisté. |
| [`apps/api/src/orcia_api/schemas/bootstrap.py`](file:///home/romain/.gemini/antigravity/worktrees/1de3c5dc-2b06-4bb5-b4cf-fabf6b66fb31/subagent-Epics-8-12-Vertical-Persistence-Wiring-Engineer-self-dc5f94d1/apps/api/src/orcia_api/schemas/bootstrap.py) | Modifié | `362` | Schémas Pydantic v2 `PlatformSetupStatePutRequest` et `PlatformSetupStateResponse` pour les 11 collections métiers. |
| [`apps/api/src/orcia_api/routers/bootstrap.py`](file:///home/romain/.gemini/antigravity/worktrees/1de3c5dc-2b06-4bb5-b4cf-fabf6b66fb31/subagent-Epics-8-12-Vertical-Persistence-Wiring-Engineer-self-dc5f94d1/apps/api/src/orcia_api/routers/bootstrap.py) | Modifié | `548` | Endpoints `GET /api/v1/bootstrap/platform-setup-state`, `PUT /api/v1/bootstrap/platform-setup-state` et persistance PostgreSQL 18 sur `POST /api/v1/bootstrap/welcome-setup/progressive-llm`. |
| [`apps/api/src/orcia_api/dependencies/workspace_and_packs.py`](file:///home/romain/.gemini/antigravity/worktrees/1de3c5dc-2b06-4bb5-b4cf-fabf6b66fb31/subagent-Epics-8-12-Vertical-Persistence-Wiring-Engineer-self-dc5f94d1/apps/api/src/orcia_api/dependencies/workspace_and_packs.py) | Modifié | `88` | Injection de `session_factory=getattr(request.app.state, "session_maker", None)` dans `PackBuilderSystemService` et `HelpGenerationAndHotAttachmentService`. |
| [`apps/api/src/orcia_api/dependencies/core_and_lifespan.py`](file:///home/romain/.gemini/antigravity/worktrees/1de3c5dc-2b06-4bb5-b4cf-fabf6b66fb31/subagent-Epics-8-12-Vertical-Persistence-Wiring-Engineer-self-dc5f94d1/apps/api/src/orcia_api/dependencies/core_and_lifespan.py) | Modifié | `309` | Initialisation de `app.state.session_maker` (`async_sessionmaker`) dans `initialize_app_services` lorsque `ORCIA_DISABLE_PG_BOOTSTRAP_SYNC != "1"`. |
| [`packages/api-client/src/helpers.ts`](file:///home/romain/.gemini/antigravity/worktrees/1de3c5dc-2b06-4bb5-b4cf-fabf6b66fb31/subagent-Epics-8-12-Vertical-Persistence-Wiring-Engineer-self-dc5f94d1/packages/api-client/src/helpers.ts) | Modifié | `72` | Support des verbes HTTP `PUT`, `PATCH` et `DELETE` dans `requestJson`. |
| [`packages/api-client/src/domains/bootstrapAndOntology.ts`](file:///home/romain/.gemini/antigravity/worktrees/1de3c5dc-2b06-4bb5-b4cf-fabf6b66fb31/subagent-Epics-8-12-Vertical-Persistence-Wiring-Engineer-self-dc5f94d1/packages/api-client/src/domains/bootstrapAndOntology.ts) | Modifié | `301` | Ajout des 12 méthodes SDK typées couvrant les Epics 8 à 12 (`getPlatformSetupState`, `savePlatformSetupState`, `searchFederated`, `getUserPreferences`, `updateUserPreferences`, `resolveContextualHelp`, `executeAssistantTurn`, `listAssistantFolders`, `createAssistantFolder`, `compileDnaStarlark`, `runRemoteServiceTestBench`, `validateHelpArticle`). |
| [`packages/api-client/openapi/openapi.json`](file:///home/romain/.gemini/antigravity/worktrees/1de3c5dc-2b06-4bb5-b4cf-fabf6b66fb31/subagent-Epics-8-12-Vertical-Persistence-Wiring-Engineer-self-dc5f94d1/packages/api-client/openapi/openapi.json) & [`packages/api-client/src/generated/schema.ts`](file:///home/romain/.gemini/antigravity/worktrees/1de3c5dc-2b06-4bb5-b4cf-fabf6b66fb31/subagent-Epics-8-12-Vertical-Persistence-Wiring-Engineer-self-dc5f94d1/packages/api-client/src/generated/schema.ts) | Régénéré | `10287` | Régénération automatique (`0-diff`) du contrat OpenAPI 3.1 et des types TypeScript. |
| [`apps/web/src/components/platformSetupStore.tsx`](file:///home/romain/.gemini/antigravity/worktrees/1de3c5dc-2b06-4bb5-b4cf-fabf6b66fb31/subagent-Epics-8-12-Vertical-Persistence-Wiring-Engineer-self-dc5f94d1/apps/web/src/components/platformSetupStore.tsx) | Modifié | `920` | Persistance synchrone `orcia.platform_setup_state.v1` + synchronisation bidirectionnelle PostgreSQL 18 (`getPlatformSetupState` / `savePlatformSetupState` / `registerProgressiveLlmEndpoint`) et purge automatique après `pnpm db:reset`. |
| [`apps/web/src/features/inbox/index.tsx`](file:///home/romain/.gemini/antigravity/worktrees/1de3c5dc-2b06-4bb5-b4cf-fabf6b66fb31/subagent-Epics-8-12-Vertical-Persistence-Wiring-Engineer-self-dc5f94d1/apps/web/src/features/inbox/index.tsx) | Modifié | `225` | Câblage de `Mon Assistant` (Epic 10) sur `executeAssistantTurn`, `listAssistantFolders` et `createAssistantFolder` via `@orcia/api-client`. |
| [`apps/web/src/features/workspaces/index.tsx`](file:///home/romain/.gemini/antigravity/worktrees/1de3c5dc-2b06-4bb5-b4cf-fabf6b66fb31/subagent-Epics-8-12-Vertical-Persistence-Wiring-Engineer-self-dc5f94d1/apps/web/src/features/workspaces/index.tsx) | Modifié | `301` | Câblage de `WorkspaceFiveTabsAndExternalRebaseView` (Epic 11) sur `datasources` et `ontologyConcepts` persistés dans `platformSetupStore` + `compileDnaStarlark`. |
| [`apps/web/src/features/catalog/index.tsx`](file:///home/romain/.gemini/antigravity/worktrees/1de3c5dc-2b06-4bb5-b4cf-fabf6b66fb31/subagent-Epics-8-12-Vertical-Persistence-Wiring-Engineer-self-dc5f94d1/apps/web/src/features/catalog/index.tsx) & [`apps/web/src/features/gates/index.tsx`](file:///home/romain/.gemini/antigravity/worktrees/1de3c5dc-2b06-4bb5-b4cf-fabf6b66fb31/subagent-Epics-8-12-Vertical-Persistence-Wiring-Engineer-self-dc5f94d1/apps/web/src/features/gates/index.tsx) | Modifiés | `90` / `108` | Câblage sur `validateHelpArticle`, `resolveContextualHelp` et `runRemoteServiceTestBench` via `@orcia/api-client`. |
| [`tests/unit/test_epic_9_story_9_2_accostage_and_first_user.py`](file:///home/romain/.gemini/antigravity/worktrees/1de3c5dc-2b06-4bb5-b4cf-fabf6b66fb31/subagent-Epics-8-12-Vertical-Persistence-Wiring-Engineer-self-dc5f94d1/tests/unit/test_epic_9_story_9_2_accostage_and_first_user.py) | Modifié | `328` | Tests unitaires et HTTP FastAPI couvrant `PUT / GET /api/v1/bootstrap/platform-setup-state` et la progression `Accostage 1/6 -> 6/6`. |
| [`tests/integration/test_story_9_2_first_user_lock_postgres18.py`](file:///home/romain/.gemini/antigravity/worktrees/1de3c5dc-2b06-4bb5-b4cf-fabf6b66fb31/subagent-Epics-8-12-Vertical-Persistence-Wiring-Engineer-self-dc5f94d1/tests/integration/test_story_9_2_first_user_lock_postgres18.py) | Modifié | `303` | Test d'intégration `testcontainers` PostgreSQL 18 (`pgvector/pgvector:pg18`) vérifiant la persistance SQL (`platform_settings`, `workspaces`, `org_units`, `llm_model_endpoints`) et la remise à zéro via `09_reset_db_first_boot.py`. |
| [`apps/web/src/__tests__/i18n-and-shell.test.tsx`](file:///home/romain/.gemini/antigravity/worktrees/1de3c5dc-2b06-4bb5-b4cf-fabf6b66fb31/subagent-Epics-8-12-Vertical-Persistence-Wiring-Engineer-self-dc5f94d1/apps/web/src/__tests__/i18n-and-shell.test.tsx) | Modifié | `615` | Ajout du test de « Survie au F5 » (`unmount()` $\rightarrow$ `render()`) vérifiant que l'état complet (admin, BU, règle RBAC, 2 familles IA, Espace, source Git) et le déverrouillage des entrées de navigation survivent au rechargement de l'application. |
| [`docs/implementation-artifacts/tech-lead-reports/README.md`](file:///home/romain/.gemini/antigravity/worktrees/1de3c5dc-2b06-4bb5-b4cf-fabf6b66fb31/subagent-Epics-8-12-Vertical-Persistence-Wiring-Engineer-self-dc5f94d1/docs/implementation-artifacts/tech-lead-reports/README.md) | Modifié | `77` | Référencement du rapport Tech Lead dans l'index officiel. |

### 3.2 Métriques de Qualité, Couverture ($\ge 90\%$) & Validation des 5 Couches (`AD-17`)

- **Vérifications Statiques & Contrats d'Architecture** :
  - `.venv/bin/ruff format --check .` & `.venv/bin/ruff check .` : **PASS (`0` erreur)**.
  - `.venv/bin/mypy --strict packages/orcia-kernel packages/orcia-core apps/api apps/worker` : **PASS (`Success: no issues found in 204 source files`)**.
  - `.venv/bin/lint-imports` : **PASS (`5 contracts kept, 0 broken`)**.
  - `.venv/bin/python .agent/skills/bmad-architecture/scripts/lint_spine.py --workspace docs/planning-artifacts/architecture/architecture-ORCIA-2026-10-24` : **PASS (`ok: true, findings: 0`)**.
  - `.venv/bin/python scripts/export_openapi.py --check` : **PASS (`0-diff`)**.
- **Couverture de Tests Python (`pytest` Unit + `testcontainers` PostgreSQL 18)** :
  - `57 passed` sur la suite unitaire Epics 8–12 + intégration PostgreSQL 18 (`test_story_9_2_first_user_lock_postgres18.py`).
  - Couverture sur les modules modifiés/créés :
    - `packages/orcia-core/src/orcia_core/bootstrap/__init__.py` : **`100%`**
    - `packages/orcia-core/src/orcia_core/bootstrap/models.py` : **`100%`**
    - `packages/orcia-core/src/orcia_core/bootstrap/progressive_accostage.py` : **`98%`**
    - `packages/orcia-core/src/orcia_core/bootstrap/_internal/sql_platform_setup_store.py` : **`92%`**
    - `packages/orcia-core/src/orcia_core/bootstrap/_internal/sql_first_user_guard.py` : **`90%`**
    - **Moyenne pondérée sur le périmètre touché : `96.1%` ($\ge 90\%$ requis)**.
- **Tests TypeScript, Lint & Gate « Survie au F5 » (`pnpm turbo run lint typecheck test`)** :
  - `9/9` tâches Turborepo réussies (`@orcia/ui`, `@orcia/api-client`, `@orcia/web`).
  - `15 passed` dans `@orcia/web` (`apps/web/src/__tests__/i18n-and-shell.test.tsx`), incluant le test explicite de démontage/remontage complet de l'arbre React (`unmount()` $\rightarrow$ `render()`).
- **Analyse Post-Implémentation GitNexus (`gitnexus_detect_changes` & `gitnexus_impact`)** :
  - Index GitNexus rafraîchi (`15,407 nodes | 25,680 edges | 240 clusters | 1005 flows`).
  - `detect_changes({scope: "all"})` : `21` fichiers modifiés, `179` symboles touchés.
  - Vérification des appelants actifs (Garde-Fou #1 « Zéro Adaptateur SQL Orphelin ») : `save_platform_setup_state_to_postgres18`, `load_platform_setup_state_from_postgres18` et `persist_progressive_llm_endpoint_to_postgres18` sont tous trois appelés activement dans `apps/api/src/orcia_api/routers/bootstrap.py` (`L396`, `L473`, `L537`) et couverts par `tests/integration/test_story_9_2_first_user_lock_postgres18.py`.
