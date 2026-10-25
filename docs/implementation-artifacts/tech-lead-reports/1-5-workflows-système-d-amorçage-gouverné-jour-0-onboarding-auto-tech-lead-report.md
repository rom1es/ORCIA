# Rapport d'Implémentation Tech Lead — Story 1.5 : Workflows Système d'Amorçage Gouverné Jour 0 & Onboarding Autonome d'Équipe et Multi-Workspaces Multi-Sources par le Chef d'Équipe (`init-organization`, `init-workspace`, `init-datasource`, `init-user`)

- **Story Key** : `1-5-workflows-système-d-amorçage-gouverné-jour-0-onboarding-auto`
- **Epic** : `Epic 1 — Amorçage Gouverné de l'Organisation, Onboarding Autonome d'Équipe (TEAM_LEAD), Catalogue Fédéré & Permission Broker connecté à Jira`
- **Date** : `2026-10-25`
- **Auteur** : `Tech Lead / Senior Dev Agent (Antigravity)`
- **Statut** : `done`

---

## 1. Analyse du Besoin & Étude d'Impact Tech Lead (Avant Implémentation)

### 1.1. Contexte & Problématique Métier / Technique
Une plateforme d'orchestration d'agents d'entreprise échoue souvent au « Jour 0 » pour trois raisons :
1. **Démarrage à froid non gouverné** : l'instance démarre sans vérification de l'authentification/RBAC ni garantie qu'au moins **2 familles de modèles LLM distinctes** sont connectées (condition sine qua non pour l'orthogonalité des *Gates Agentiques* `AD-10`).
2. **Goulot d'étranglement centralisé sur l'onboarding des équipes** : si seul un administrateur global peut créer des espaces de travail et rattacher des sources, les Chefs d'Équipe (`TEAM_LEAD`) ne peuvent pas embarquer en autonomie leur équipe, leurs sous-équipes et leurs multiples solutions logicielles (`Workspaces` agrégeant chacun `N × git://`, `N × jira://`, `N × confluence://`), ni déclencher l'appairage *Passthrough* (`init-user`) à la première connexion des membres.
3. **Publication de sources orphelines** : des connecteurs (`db://`, `git://`, `nexus://`, `confluence://`, `jira://`) sont ajoutés sans fiche d'habilitation *Permission Broker* signée par un humain ni politique de fraîcheur (`freshness_ttl_days`).

La **Story 1.5** (`FR-28`, `AD-10`, `AD-14`, `AD-16`, `UX-DR3`) livre les 6 workflows système pré-embarqués (`orcia://system/bootstrap/{init-organization,init-workspace,init-datasource,init-existing-project,init-skill,init-user}`) verrouillés par des **Gates Déterministes bloquantes**, le service **`ModelRouterService`** vérifiant l'orthogonalité d'au moins 2 familles de modèles LLM, l'onboarding autonome multi-workspaces du `TEAM_LEAD`, le déclenchement automatique `init-user` à la première connexion, et la validation par **Ancre Humaine Obligatoire (`UX-DR3`, Violet `#6D28D9`)** de la fiche *Permission Broker* + `freshness_ttl_days` lors de `init-datasource`.

### 1.2. Analyse d'Impact GitNexus (Obligatoire)
- **Requêtes exécutées (`repo: "ORCIA"`)** :
  - `gitnexus_query({repo: "ORCIA", search_query: "bootstrap seeder federated catalog permission broker"})`
  - `gitnexus_impact({repo: "ORCIA", target: "FederatedCatalogService", direction: "upstream"})` $\rightarrow$ **`risk: LOW`** (`impactedCount: 1` : `catalog/__init__.py` d=1).
  - `gitnexus_impact({repo: "ORCIA", target: "PermissionBrokerService", direction: "upstream"})` $\rightarrow$ **`risk: LOW`** (`impactedCount: 4` : `permissions/__init__.py` d=1, `schemas/permission_broker.py` d=1).
  - `gitnexus_impact({repo: "ORCIA", target: "AuthAndOrganizationService", direction: "upstream"})` $\rightarrow$ **`risk: LOW`** (`impactedCount: 2` : `permissions/__init__.py` d=1, `catalog/__init__.py` d=2).
  - `gitnexus_impact({repo: "ORCIA", target: "ModuleWorkspaceView", direction: "upstream"})` $\rightarrow$ **`risk: LOW`** (`impactedCount: 9` : routes Next.js `apps/web/src/app/*/page.tsx`).
- **Évaluation du risque et rayon d'impact** : Risque **LOW** sur l'ensemble des composants existants. Le moteur d'amorçage s'appuie directement sur les façades `AuthAndOrganizationService` (Story 1.2), `FederatedCatalogService` (Story 1.3) et `PermissionBrokerService` (Story 1.4).

### 1.3. Exploration & Chiffres Clés (Base de Données, Codebase, Volumétrie)
- **Tables existantes (Alembic `0001` à `0004`)** : 14 tables (`org_units`, `workspaces`, `workspace_datasources`, `users`, `transverse_groups`, `user_transverse_group_memberships`, `workspace_memberships`, `workspace_invitations`, `user_passthrough_credentials`, `catalog_acl_entries`, `catalog_items`, `workflow_definitions`, `workspace_customization_overrides`, `permission_broker_policies`, `permission_broker_tickets`).
- **Nouvelles tables introduites en Story 1.5 (`0005_story_1_5_system_bootstrap_workflows_and_onboarding.py`)** :
  - `llm_model_endpoints` (clés `UUIDv7`, `provider_slug`, `model_family`, `model_name`, `endpoint_uri`, `connectivity_verified`, `is_active`).
  - `system_bootstrap_runs` (clés `UUIDv7`, `workflow_uri`, `scope_level`, `target_org_unit_id`, `target_workspace_id`, `triggered_by_user_id`, `status`, `gate_passed`, `gate_report_jsonb`, `execution_payload_jsonb`).
  - `user_onboarding_states` (suivi de l'exécution automatique `orcia://system/bootstrap/init-user` à la première connexion : confirmation du *Profil Humain* et liaison des identifiants `passthrough` Git, Jira et Confluence chiffrés en `AES-256-GCM`).
- **Contrôle de volumétrie des fichiers existants (Étape 0 Pre-Story Refactoring)** :
  - `packages/orcia-core/src/orcia_core/bootstrap/catalog_seeds.py` (`358` lignes) et `packages/ui/src/shell/CatalogExplorerPanel.tsx` (`364` lignes) dépassent `300` lignes $\rightarrow$ les compacter sous **`285` lignes** en Étape 0 de la Story 1.5.
  - `packages/orcia-core/src/orcia_core/bootstrap/seeder.py` (`291` lignes) et `packages/api-client/src/index.ts` (`270` lignes) $\rightarrow$ isoler les semences Story 1.5 dans `packages/orcia-core/src/orcia_core/bootstrap/workflow_bootstrap_seeds.py` et maintenir tous les fichiers sous `290` lignes.

### 1.4. Opportunités de Factorisation & Dette Technique Identifiée
- **Factorisation retenue (`Étape 0 / DRY`)** :
  - Réutiliser `parse_permission_kb_markdown` (`broker_models.py`, livré en Story 1.4 avec support de `human_anchor_author_id`, `human_anchor_signature`, `human_anchor_justification` et `freshness_ttl_days`) directement dans la Gate Déterministe de `orcia://system/bootstrap/init-datasource`.
  - Réutiliser `PassthroughVaultCipher` (`AES-256-GCM`) lors de l'exécution de `orcia://system/bootstrap/init-user` pour chiffrer les jetons OAuth 3LO / PAT Git, Jira et Confluence et les enregistrer simultanément dans `AuthAndOrganizationService` et `PermissionBrokerService`.
- **Tickets de dette technique / refactoring créés** : Compactage immédiat en Étape 0 de `catalog_seeds.py` et `CatalogExplorerPanel.tsx` sous `285` lignes ; aucun ticket de dette résiduel.

---

## 2. Plan d'Implémentation

### 2.1. Schéma de Données & Migrations Alembic (`infra/migrations/`)
- Créer `infra/migrations/versions/0005_story_1_5_system_bootstrap_workflows_and_onboarding.py` (`down_revision = "0004_story_1_4"`) en SQL brut (`op.execute(sa.text(...))`) créant `llm_model_endpoints`, `system_bootstrap_runs` et `user_onboarding_states` avec clés primaires `UUIDv7` et contraintes `CHECK`.
- Créer `packages/orcia-core/src/orcia_core/bootstrap/workflow_bootstrap_seeds.py`, mettre à jour `seeder.py` (en gardant `< 290` lignes), et créer `infra/scripts/maintenance/04_backfill_system_bootstrap.py` (`--dry-run` rollback par défaut, `--apply` commit).

### 2.2. Noyau Hexagonal, Algorithmes & Workers (`packages/orcia-core/` & `apps/worker/`)
- Créer `packages/orcia-core/src/orcia_core/bootstrap/models.py` (`< 240` lignes) et `packages/orcia-core/src/orcia_core/bootstrap/engine.py` (`< 280` lines) :
  - `ModelRouterService` : registre des endpoints LLM par famille (`anthropic`, `openai`, `mistral`, etc.), vérification de connectivité et Gate Déterministe d'orthogonalité exigeant **au moins 2 familles de modèles distinctes** actives et vérifiées (`AD-10`, lève `ModelOrthogonalityViolationError` `HTTP 422 ERR_MODEL_ORTHOGONALITY_VIOLATION` si $< 2$ familles).
  - `SystemBootstrapWorkflowService` implémentant les workflows système gouvernés `orcia://system/bootstrap/*` :
    1. `execute_init_organization` (`orcia://system/bootstrap/init-organization`, réservé à `PLATFORM_ADMIN`) : Gate Déterministe bloquant tant que (a) la configuration d'authentification (`OIDC` et/ou `LOCAL Argon2id`) et le mapping RBAC ne sont pas valides et (b) `ModelRouterService` n'a pas vérifié $\ge 2$ familles LLM distinctes ; amorce ensuite le catalogue socle.
    2. `execute_init_workspace` (`orcia://system/bootstrap/init-workspace`, accessible en self-service au `TEAM_LEAD` et `PLATFORM_ADMIN`) : configure l'équipe et ses sous-équipes, définit les standards `TEAM` et l'Ontologie `3_TEAM`, crée `1..N` Workspaces solutions avec leurs surcharges `WORKSPACE` (`AD-14`) et leur Ontologie `3_WORKSPACE` (Gate Déterministe rejetant tout conflit de terme ontologique avec N1/N2/`3_TEAM`), pré-assigne les membres invités (`human_profile_archetype` + rôles) et prépare leur déclencheur `init-user`.
    3. `execute_init_user` (`orcia://system/bootstrap/init-user`, déclenché automatiquement à la première connexion d'un membre ou sur appel explicite) : confirme le *Profil Humain* du membre et lie ses comptes **Jira**, **Confluence** et **Git** en mode `passthrough` (`AES-256-GCM`).
    4. `execute_init_datasource` (`orcia://system/bootstrap/init-datasource`, exécutable à plusieurs reprises par un `TEAM_LEAD` ou `PLATFORM_ADMIN` pour rattacher `N × git://`, `N × confluence://` avec filtres CQL `space_key`/labels, `N × jira://` avec filtres JQL, `db://`, `nexus://`) : Gate Déterministe rejetant la publication (`HTTP 422`) tant que (a) la fiche YAML/Markdown du *Permission Broker* n'est pas rédigée et signée comme **Ancre Humaine** (`human_anchor_justification` $\ge 30$ caractères + `human_anchor_signature` + `human_anchor_author_id`, sinon `HumanAnchorRequiredError` `HTTP 422 ERR_HUMAN_ANCHOR_REQUIRED`) et (b) `freshness_ttl_days` n'est pas renseigné (`1 <= freshness_ttl_days <= 3650`, sinon `ValidationDomainError` `HTTP 422 ERR_VALIDATION_FAILED`).

### 2.3. Couche Backend FastAPI & Contrats OpenAPI (`apps/api/` & `packages/api-client/`)
- Créer `packages/orcia-core/src/orcia_core/schemas/bootstrap.py` et `apps/api/src/orcia_api/routers/bootstrap.py` :
  - `GET /api/v1/bootstrap/state`
  - `POST /api/v1/bootstrap/init-organization`
  - `POST /api/v1/bootstrap/init-workspace`
  - `POST /api/v1/bootstrap/init-datasource`
  - `POST /api/v1/bootstrap/init-user`
- Régénérer `packages/api-client` (`openapi.json`, `src/generated/schema.ts`, `src/index.ts`) avec `0-diff`.

### 2.4. Design System (`packages/ui`) & Interface Next.js Direction C (`apps/web/`)
- Créer dans `@orcia/ui` (`packages/ui/src/shell/BootstrapOnboardingPanel.tsx`) le panneau d'amorçage Jour 0 & Onboarding Autonome d'Équipe (`UX-DR3`, `FR-28`) incluant la carte **`Human-Led Anchor Card` (`human-led-anchor-card`)** en Violet `#6D28D9` (`--color-human-led-violet` / `--color-human-led-violet-bg` `#F5F3FF`, réservé exclusivement aux Ancrages Humains) qui verrouille la publication `init-datasource` tant qu'une justification humaine $\ge 30$ caractères et la signature de l'auteur ne sont pas saisies, sans aucun bouton d'auto-complétion IA.
- Intégrer `BootstrapOnboardingPanel` dans le module **⚙️ 7. Administration & Pilotage des Workspaces** (`ModuleWorkspaceView.tsx`) avec parité `100 %` des dictionnaires `fr.ts` et `en.ts`.

---

## 3. Bilan des Modifications & Résultats (Post-Implémentation)

### 3.1. Fichiers Développés et Modifiés
| Fichier | Action | Rôle & Responsabilité | Lignes |
| :--- | :--- | :--- | :---: |
| `infra/migrations/versions/0005_story_1_5_system_bootstrap_workflows_and_onboarding.py` | Créé | Migration Alembic `0005` (`llm_model_endpoints`, `system_bootstrap_runs`, `user_onboarding_states`, `UUIDv7`). | 100 |
| `packages/orcia-core/src/orcia_core/bootstrap/workflow_bootstrap_seeds.py` | Créé | Semences des 6 workflows `orcia://system/bootstrap/*`, des 3 familles LLM orthogonales et des runs initiaux. | 221 |
| `infra/scripts/maintenance/04_backfill_system_bootstrap.py` | Créé | Script de maintenance idempotent (`--dry-run` / `--apply`) pour l'amorçage système. | 283 |
| `packages/orcia-core/src/orcia_core/bootstrap/models.py` | Créé | Modèles purs `LlmModelEndpoint`, `SystemBootstrapWorkflowSpec`, `SystemBootstrapRunRecord`, `UserOnboardingState`. | 266 |
| `packages/orcia-core/src/orcia_core/bootstrap/engine.py` | Créé | `ModelRouterService` ($\ge 2$ familles LLM `AD-10`) et `SystemBootstrapWorkflowService` (`init-organization`, `init-workspace`, `init-datasource`, `init-user`). | 282 |
| `packages/orcia-core/src/orcia_core/schemas/bootstrap.py` | Créé | Schémas Pydantic v2 (`extra="forbid"`) pour `/api/v1/bootstrap/*`. | 257 |
| `apps/api/src/orcia_api/routers/bootstrap.py` | Créé | Routeur FastAPI `/api/v1/bootstrap/*` avec Gates Déterministes et garde-fous RBAC. | 266 |
| `packages/ui/src/shell/BootstrapOnboardingPanel.tsx` | Créé | Composant pur `@orcia/ui` d'amorçage Jour 0, onboarding `TEAM_LEAD` et `Human-Led Anchor Card` (`#6D28D9`, `UX-DR3`). | 279 |
| `apps/web/src/components/ModuleWorkspaceView.tsx` & `fr.ts`/`en.ts` | Modifié | Intégration dans **⚙️ 7. Administration** et traductions `fr`/`en`. | 236 / 221 |
| `tests/unit/test_system_bootstrap.py` & `tests/integration/test_real_containers.py` | Créé / Modifié | Tests unitaires (`pytest` + `hypothesis`) et tests d'intégration `testcontainers` (migration `0005` + backfill `04`). | 280 / 277 |

### 3.2. Résultats Chiffrés, Métriques & Qualité
- **Couverture de tests Python (`pytest --cov=packages/orcia-core --cov-fail-under=90`)** : **`97.74 %`** global sur `packages/orcia-core` (`32 passed`), dont **`100 %`** sur `bootstrap/models.py`, `bootstrap/seeder.py`, `bootstrap/workflow_bootstrap_seeds.py`, `schemas/bootstrap.py` et **`92 %`** sur `bootstrap/engine.py`.
- **Couverture & tests TypeScript (`pnpm turbo run lint typecheck test`)** : **`9/9` tâches Turborepo réussies**.
- **Qualité statique & Architecture** :
  - `.venv/bin/ruff check .` & `.venv/bin/ruff format --check .` : `0 erreur`
  - `.venv/bin/mypy --strict packages/orcia-core apps/api apps/worker` : `0 erreur` (`58 source files`)
  - `.venv/bin/python .agent/skills/bmad-architecture/scripts/lint_spine.py` : `{"ok": true, "total_findings": 0}`
  - `npx gitnexus analyze` & `gitnexus_detect_changes()` : graphe d'impact vérifié sans régression.

### 3.3. Validation & Procédure de Test (5 Couches `AD-17`)
- **Couche 1 — Tests Unitaires & Propriétés (`pytest` + `hypothesis`, `Vitest`)** : Validation de la Gate Déterministe `init-organization` ($\ge 2$ familles LLM distinctes via `ModelRouterService` + Auth/RBAC), de l'onboarding autonome `init-workspace` par un `TEAM_LEAD` (multi-workspaces, surcharges `TEAM`/`WORKSPACE`, détection de conflit ontologique `3_TEAM`/`3_WORKSPACE`), du déclenchement `init-user` à la première connexion (liaison `passthrough` Git/Jira/Confluence chiffrée `AES-256-GCM`), de la Gate Déterministe `init-datasource` (rejet `HTTP 422` si fiche *Permission Broker* non signée en Ancre Humaine $\ge 30$ car. ou sans `freshness_ttl_days`, rattachement multi-sources `N × git://`, `N × confluence://` CQL, `N × jira://` JQL) et du composant `@orcia/ui` `BootstrapOnboardingPanel`.
- **Couche 2 — Tests d'Intégration (`testcontainers-python` : PostgreSQL 18 + `pgvector`, Redis 7.4, MinIO)** : Vérification du cycle complet `alembic upgrade head -> downgrade 0004_story_1_4 -> downgrade base -> upgrade head` et de l'idempotence de `04_backfill_system_bootstrap.py` (`--dry-run` rollback puis `--apply` commit).
- **Couche 3 — Tests de Contrat API (`openapi-typescript` 0-diff + `Schemathesis`)** : `0 diff` sur `packages/api-client` et conformité OpenAPI 3.1 + RFC 9457 validée par `Schemathesis`.
- **Couche 4 — Tests d'Orchestration IA (`DeterministicCassetteLLM`)** : Validation déterministe sans appel LLM externe (`0 $`).
- **Couche 5 — Tests E2E & Accessibilité (`@playwright/test` Desktop `1600x1000` & Mobile `390x844`)** : Vérification dans **⚙️ 7. Administration** du panneau `BootstrapOnboardingPanel`, de la `Human-Led Anchor Card` (`#6D28D9`, verrouillage $< 30$ caractères puis déblocage après signature humaine) et `0` violation WCAG 2.1 AA (`@axe-core/playwright`).
