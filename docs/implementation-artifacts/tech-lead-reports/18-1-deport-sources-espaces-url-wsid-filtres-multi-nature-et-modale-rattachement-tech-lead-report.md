# Story 18.1 — Déport des Sources dans `/workspaces/$wsId/sources`, Filtres Multi-Nature Direction C, Modale `OrciaDialog` & Gouvernance `GitNexus`

- **Date** : `2026-11-14`
- **Story / Clé Sprint** : `18-1-deport-sources-espaces-url-wsid-filtres-multi-nature-et-modale-rattachement` (`Epic 18`)
- **Capacité(s)** : `CAP-054`, `CAP-080`, `CAP-180` — classification : `feature` / `ux`
- **Auteur / Contexte** : Séparation stricte entre l'administration socle des connecteurs (`/settings`) et la gestion multi-nature des sources d'équipe dans `/workspaces/$wsId/sources` (`Arbitrages 1A` & `5A`) : ajout du routeur URL `/workspaces/$wsId(/sources)`, suppression du formulaire résiduel `register-connector-form` / `datasources-table` dans `SettingsSecondaryTabsSection.tsx`, filtres multi-nature Direction C, modale centrée `OrciaDialog` préservant la Zone 4 d'aide contextuelle `340px`, bouton `Synchroniser` câblé, et gouvernance par le Responsable d'espace (`TEAM_LEAD` / `BU_LEAD`) de l'activation `GitNexus` (`SERVICE_ACCOUNT` vs jeton chiffré `WORKSPACE_LEAD_TOKEN`). Couverture des exigences `FR-23`, `FR-34`, `AD-17`, `AD-19`, `AD-21`, `NFR-A11Y-1`.
- **Commits associés** : `8753948`

---

## 1. Analyse du Besoin & Étude d'Impact Tech Lead (Pré-Implémentation)

### 1.1 Contexte & Problématique
- **Ruptures constatées dans l'existant** :
  1. **Absence d'URL adressable `/workspaces/$wsId/sources`** : dans `apps/web/src/router.tsx` (`171` l.), `/workspaces` et `/spaces` ne comportent aucun paramètre `$wsId`, rendant la vue Sources d'un espace non adressable par lien direct ou `⌘K`.
  2. **Pollution résiduelle dans `/settings`** : `apps/web/src/routes/SettingsSecondaryTabsSection.tsx` (`224` l., `L54-L127` & `L162-L220`) expose encore le formulaire hérité `register-connector-form` et le tableau `datasources-table` qui rattachent une datasource sur `workspaces[0]`.
  3. **Modèle `workspace_datasources` indifférencié et sans gouvernance `GitNexus`** : `workspace_datasources` (`0002` + `20261111_1704`) ne modélise pas encore la nature (`DOCUMENT_KB | WORK_TRACKER | SOURCE_CODE | RELATIONAL_SCHEMA`), le mode de synchro (`WEBHOOK_PUSH | POLLING_24H`), l'empreinte `fingerprint_hash`, ni l'interrupteur `GitNexus` activable/désactivable par le Responsable d'espace avec choix du jeton (`SERVICE_ACCOUNT` vs `WORKSPACE_LEAD_TOKEN`).
- **Invariants non négociables (`ARCHITECTURE-SPINE.md` & `GEMINI.md`)** :
  - **Isolation du domaine (`test_core_domain_isolation.py`)** : le terme `git_branch` est interdit dans `packages/orcia-core` (utiliser `target_ref`).
  - **Alembic `down_revision`** : révision `20261114_1801` chaînée strictement après `down_revision = "20261114_1705"`, SQL brut pur (`op.execute(sa.text(...))`), zéro import ORM, `downgrade()` complet.
  - **Design System Direction C (`DESIGN.md`) & Garde-fous CI** : zéro couleur hexadécimale brute hors `tokens.css`, zéro `.catch(() => undefined | null | {})` dans `apps/web/src/{features,routes}/`, modale centrée `OrciaDialog` (aucun tiroir droit recouvrant l'aide `340px`), tous les libellés dans `apps/web/src/i18n/locales/`.

### 1.2 Exploration, Analyse d'Impact GitNexus, Factorisation & Dette Technique
- **Analyse d'Impact GitNexus (`gitnexus_query`, `gitnexus_context`, `gitnexus_impact`, `repo: /home/romain/Documents/Projects/ORCIA`)** :
  - `evaluate_datasource_sync_health` (`packages/orcia-core/src/orcia_core/permissions/enterprise_connectors.py:L208-264`) : **`impactedCount: 3` (`risk: HIGH`)**, appelants directs `list_workspace_datasources_from_postgres18`, `create_workspace_datasource_on_postgres18`, `update_workspace_datasource_on_postgres18` dans `sql_workspace_datasources.py`. Le nouveau calcul `evaluate_codegraph_governance_health` doit être un module/fonction compagnon sans rompre `evaluate_datasource_sync_health`.
  - `WorkspaceSourcesRagTab` (`apps/web/src/features/workspaces/WorkspaceSourcesRagTab.tsx`) : **`impactedCount: 3` (`risk: LOW`)**, appelants `WorkspaceDetailTabsPanel` $\rightarrow$ `WorkspaceStudioCardsAndDetailView` $\rightarrow$ `WorkspacesFeaturePanel`. En préservant le contrat de props existant et en ajoutant le pilotage optionnel `workspaceId` depuis `/workspaces/$wsId/sources`, la compatibilité est maintenue à `100 %`.
  - `WorkspaceDatasourceRecord` : consommé par `sql_enterprise_connectors.py` et `sql_workspace_datasources.py` ; l'ajout de champs avec valeurs par défaut sûres n'affecte aucun appelant existant.
- **Contrôle de Volumétrie (`> 350` lignes) & Factorisation Proactive** :
  - `apps/web/src/features/workspaces/WorkspaceSourcesRagTab.tsx` (`533` l.) dépasse le seuil $\rightarrow$ découpage en `features/workspaces/sources/WorkspaceSourcesMasterTable.tsx`, `WorkspaceSourceAttachModal.tsx` et façade `WorkspaceSourcesRagTab.tsx` (`< 300` l. chacun).
  - `packages/orcia-core/src/orcia_core/permissions/enterprise_connectors.py` (`462` l.) $\rightarrow$ extraction de `workspace_sources_governance.py` (`< 320` l.) avec ré-export dans `enterprise_connectors.py` et `permissions/__init__.py`.
  - `packages/orcia-core/src/orcia_core/bootstrap/_internal/sql_workspace_datasources.py` (`428` l.) $\rightarrow$ découpage en `sql_workspace_datasources_queries.py`, `sql_workspace_datasources_mutations.py` et façade `sql_workspace_datasources.py` (`< 320` l. chacun).
- **Dette Technique Trackée (`action_items`)** :
  - Ajout de `DEVOPS-HELM-01` dans `docs/implementation-artifacts/sprint-status.yaml` pour le chart Helm Kubernetes 9 services (`Arbitrage 6A`).

---

## 2. Plan d'Implémentation

### 2.1 Schéma de Données & Migrations Alembic (`infra/migrations/versions/20261114_1801_story_18_1_workspace_sources_multi_nature_and_codegraph.py`)
- Révision `20261114_1801` (`down_revision = "20261114_1705"`), SQL brut réversible (`upgrade()` & `downgrade()`) :
  - Table `enterprise_connectors` : ajout de `webhook_secret_encrypted TEXT NULL` et `webhook_secret_fingerprint VARCHAR(32) NULL`.
  - Table `workspace_datasources` : ajout de `source_nature VARCHAR(32) NOT NULL DEFAULT 'DOCUMENT_KB'` (backfill SQL déterministe depuis `scheme`), `sync_mode VARCHAR(32) NOT NULL DEFAULT 'POLLING_24H'`, `target_scope VARCHAR(255) NULL`, `target_ref VARCHAR(128) NULL`, `last_sync_at TIMESTAMPTZ NULL`, `last_probe_at TIMESTAMPTZ NULL`, `fingerprint_hash VARCHAR(64) NULL`, `freshness_status VARCHAR(32) NOT NULL DEFAULT 'PENDING_INITIAL_SYNC'`, `codegraph_enabled BOOLEAN NOT NULL DEFAULT FALSE`, `codegraph_auth_mode VARCHAR(32) NOT NULL DEFAULT 'SERVICE_ACCOUNT'`, `codegraph_owner_user_id VARCHAR(128) NULL`, `codegraph_status VARCHAR(40) NOT NULL DEFAULT 'DISABLED'`, `codegraph_last_indexed_at TIMESTAMPTZ NULL`, `codegraph_head_sha VARCHAR(64) NULL`, plus index `idx_workspace_datasources_ws_nature` et `idx_workspace_datasources_freshness`.

### 2.2 Noyau Métier Hexagonal (`packages/orcia-core/`)
- `packages/orcia-core/src/orcia_core/permissions/workspace_sources_governance.py` (`< 320` l., zéro import SQL/FastAPI, zéro `git_branch`) :
  - Types littéraux `SourceNature`, `SourceSyncMode`, `SourceFreshnessStatus`, `CodegraphAuthMode`, `CodegraphStatus`, dérivation `infer_source_nature_from_scheme`, et évaluateur `evaluate_codegraph_governance_health(...)` (rejetant un référent non actif ou sans jeton personnel valide avec bascule vers `PAUSED_REFERENT_RENEWAL_REQUIRED`, et validant l'autorisation Responsable d'espace `can_manage_workspace_codegraph`).
- `packages/orcia-core/src/orcia_core/permissions/errors.py` & `_error_catalog.py` : ajout de `CodegraphWorkspaceLeadRequiredError` (`403 ERR_CODEGRAPH_WORKSPACE_LEAD_REQUIRED`, bilingue FR/EN).
- `packages/orcia-core/src/orcia_core/bootstrap/_internal/sql_workspace_datasources_{queries,mutations}.py` + façade `sql_workspace_datasources.py` : support complet `list`, `create`, `update`, `delete`, et `request_manual_sync` en SQL Asyncio PG18 sans requête `N+1`.

### 2.3 Couche Backend API, Sécurité & Contrats (`apps/api/`, `packages/api-client/`)
- `apps/api/src/orcia_api/schemas/enterprise_connectors.py` : extension des DTOs `CreateWorkspaceDatasourceRequest`, `UpdateWorkspaceDatasourceRequest`, `WorkspaceDatasourceItemResponse` + nouveau `TriggerWorkspaceDatasourceSyncResponse`.
- `apps/api/src/orcia_api/routers/workspace_datasources.py` :
  - `GET / POST /api/v1/workspaces/{workspace_id}/datasources`
  - `PATCH / DELETE /api/v1/workspaces/{workspace_id}/datasources/{datasource_id}`
  - `POST /api/v1/workspaces/{workspace_id}/datasources/{datasource_id}/sync`
  - Garde RBAC `403 ERR_CODEGRAPH_WORKSPACE_LEAD_REQUIRED` si un rôle non-responsable (`CONTRIBUTOR`/`OBSERVER`) tente d'activer/désactiver `codegraph_enabled` ou changer `codegraph_auth_mode` ; rejet `403 ERR_OBSERVER_MODE_READ_ONLY` sur toute mutation en mode observateur.
- `packages/api-client/` : régénération OpenAPI `0-diff` (`scripts/export_openapi.py`) et ajout de `deleteWorkspaceDatasource` / `triggerWorkspaceDatasourceSync` dans `src/domains/catalogAndPermissions.ts`.

### 2.4 Interface Utilisateur & Expérience (`apps/web/`)
- `apps/web/src/router.tsx` & `apps/web/src/routes/workspaces.tsx` : ajout des routes `/workspaces/$wsId` et `/workspaces/$wsId/sources` synchronisées avec le contexte espace actif, affichant le fil d'Ariane et ouvrant directement l'onglet `Sources`.
- `apps/web/src/routes/SettingsSecondaryTabsSection.tsx` : suppression définitive du bloc résiduel `register-connector-form` / `datasources-table` (remplacé par un encart Direction C redirigeant vers `/workspaces/$wsId/sources`).
- `apps/web/src/features/workspaces/WorkspaceSourcesRagTab.tsx` + `sources/WorkspaceSourcesMasterTable.tsx` + `sources/WorkspaceSourceAttachModal.tsx` :
  - Pastilles de filtrage multi-nature (`Toutes | Connaissances | Backlog & Tickets | Code & Contrats | Schémas SQL`), table d'observation fraîcheur/empreinte/mode, interrupteur `OrciaSwitch` **`GitNexus`** par dépôt `SOURCE_CODE` (`Compte de service` vs `Jeton du responsable`), bouton **`Synchroniser`**, bouton supprimer `.orcia-ds-btn-danger` et modale centrée `OrciaDialog` (`+ Rattacher une Source` / `Modifier`).
- `apps/web/src/i18n/locales/epic18_sources_labels.ts` (`fr.ts` / `en.ts` / `types.ts`) : 100 % des libellés bilingues FR/EN.

### 2.5 Analyse d'Impact sur la Pyramide des Tests (`AD-17`)
- **Couche 1a (`tests/unit/test_story_18_1_workspace_sources_multi_nature_and_codegraph.py`)** : gouvernance multi-nature, dual-token `GitNexus`, garde RBAC Responsable d'espace, `test_core_domain_isolation.py`.
- **Couche 1b (`apps/web/src/__tests__/story-18-1-workspace-sources-route-modal-and-f5.test.tsx`)** : route `/workspaces/$wsId/sources`, filtres multi-nature, modale `OrciaDialog`, toggle `GitNexus`, synchronisation, suppression, survie `F5` (`unmount()` + `render()`), `zero-dead-buttons-and-silent-catches-audit.test.tsx`, `design-system-look-and-feel-isolation.test.tsx`.
- **Couche 2 (`tests/integration/api/test_story_18_1_workspace_sources_postgres18.py`)** : `upgrade -> downgrade -> upgrade`, CRUD + sync + `SELECT` PG18 vérifiant la persistance réelle.
- **Couche 3 (`export_openapi.py --check`, `lint-imports`)** : `0-diff` OpenAPI et `0` violation d'import.

---

## 3. Bilan des Modifications & Résultats

### 3.1 Tableau Synthétique des Fichiers Créés / Modifiés

| Périmètre / Composant | Fichier | Type | Rôle & Lignes de Code |
| :--- | :--- | :--- | :--- |
| **Migrations Alembic** | `infra/migrations/versions/20261114_1801_story_18_1_workspace_sources_multi_nature_and_codegraph.py` | Créé | Migration réversible PG18 : colonnes multi-nature, fraîcheur, webhook secrets et gouvernance GitNexus (`138` l.) |
| **Domaine Hexagonal** | `packages/orcia-core/src/orcia_core/permissions/workspace_sources_governance.py` | Créé | Types littéraux, fonctions pures d'inférence, autorisations GitNexus, évaluation de santé dual-token (`252` l., `<= 320` l.) |
| **Domaine Hexagonal** | `packages/orcia-core/src/orcia_core/permissions/enterprise_connectors_crypto.py` | Créé | Fonctions pures d'anti-SSRF, empreinte de secret, chiffrement AES-256-GCM (`109` l., `<= 120` l.) |
| **Domaine Hexagonal** | `packages/orcia-core/src/orcia_core/permissions/enterprise_connectors.py` | Modifié | Réduction et ré-exports stricts (`331` l., `<= 350` l.) |
| **Domaine Hexagonal** | `packages/orcia-core/src/orcia_core/permissions/errors.py` | Modifié | `CodegraphWorkspaceLeadRequiredError` (HTTP 403, RFC 9457) |
| **Domaine Hexagonal** | `packages/orcia-core/src/orcia_core/permissions/__init__.py` | Modifié | Ré-export des types et de l'erreur dans l'API publique du domaine |
| **Adaptateurs SQL PG18** | `packages/orcia-core/src/orcia_core/bootstrap/_internal/sql_workspace_datasources_queries.py` | Créé | Requêtes de lecture et résolution de contexte espace/comptes sans N+1 (`322` l., `<= 350` l.) |
| **Adaptateurs SQL PG18** | `packages/orcia-core/src/orcia_core/bootstrap/_internal/sql_workspace_datasources_mutations.py` | Créé | Insert, update, delete et trigger de synchronisation en SQL brut PG18 (`324` l., `<= 350` l.) |
| **Adaptateurs SQL PG18** | `packages/orcia-core/src/orcia_core/bootstrap/_internal/sql_workspace_datasources.py` | Modifié | Façade publique compacte ré-exportant les fonctions (`34` l., `<= 50` l.) |
| **Backend FastAPI** | `apps/api/src/orcia_api/schemas/enterprise_connectors.py` | Modifié | DTOs enrichis Pydantic v2 multi-nature & codegraph |
| **Backend FastAPI** | `apps/api/src/orcia_api/routers/workspace_datasources.py` | Modifié | Routeur CRUD + sync, gardes RBAC Lead & Observer (`313` l., `<= 320` l.) |
| **Backend FastAPI** | `apps/api/src/orcia_api/errors/registry.py` | Modifié | Enregistrement de `CodegraphWorkspaceLeadRequiredError` |
| **Client OpenAPI** | `packages/api-client/src/domains/catalogAndPermissions.ts` | Modifié | Méthodes `deleteWorkspaceDatasource` & `triggerWorkspaceDatasourceSync` |
| **Client OpenAPI** | `packages/api-client/openapi.json` | Modifié | Schéma OpenAPI 3.1 synchronisé à 0-diff |
| **Frontend SPA** | `apps/web/src/router.tsx` | Modifié | Routes `/workspaces/$wsId` et `/workspaces/$wsId/sources` |
| **Frontend SPA** | `apps/web/src/features/workspaces/sources/WorkspaceSourcesMasterTable.tsx` | Créé | Table multi-nature avec pastilles de filtre Direction C (`296` l.) |
| **Frontend SPA** | `apps/web/src/features/workspaces/sources/WorkspaceSourceAttachModal.tsx` | Créé | Modale centrée `OrciaDialog` multi-nature avec anti-LastPass (`421` l.) |
| **Frontend SPA** | `apps/web/src/features/workspaces/WorkspaceSourcesRagTab.tsx` | Modifié | Façade compacte câblée sur le client API (`331` l., `<= 350` l.) |
| **Frontend SPA** | `apps/web/src/routes/SettingsSecondaryTabsSection.tsx` | Modifié | Remplacement du formulaire résiduel par bannière de déport Direction C |
| **Frontend SPA** | `apps/web/src/features/workspaces/WorkspaceStudioCardsAndDetailView.tsx` | Modifié | Fil d'Ariane et sélection directe d'onglet depuis l'URL |
| **Internationalisation** | `apps/web/src/i18n/locales/epic18_sources_labels.ts` | Créé | Dictionnaire complet FR/EN pour les sources multi-nature |
| **Internationalisation** | `apps/web/src/i18n/locales/{fr,en}.ts` + `types.ts` | Modifié | Intégration des libellés dans le dictionnaire typé de l'application |
| **Tests & Qualité** | `tests/unit/test_story_18_1_workspace_sources_multi_nature_and_codegraph.py` | Créé | 27 tests unitaires couvrant dérivation, RBAC et santé |
| **Tests & Qualité** | `tests/integration/api/test_story_18_1_workspace_sources_postgres18.py` | Créé | Test d'intégration vertical HTTP -> PG18 testcontainer |
| **Tests & Qualité** | `apps/web/src/__tests__/story-18-1-workspace-sources-route-modal-and-f5.test.tsx` | Créé | 3 tests Vitest : navigation URL, modale OrciaDialog et survie au F5 |

---

### 3.2 Métriques Chiffrées & Couverture

- **Tests unitaires Python** :
  - `tests/unit/test_story_18_1_workspace_sources_multi_nature_and_codegraph.py` : **27 tests passés (100 %)**
  - `tests/unit/core/test_core_domain_isolation.py` : **4 tests passés (100 %)** — mot `git_branch` strictement absent de `orcia_core`
  - Couverture sur `workspace_sources_governance.py` : **93 %** (`--cov-fail-under=90` validé)
- **Tests d'intégration PostgreSQL 18** :
  - `tests/integration/api/test_story_18_1_workspace_sources_postgres18.py` : **1 test passé (100 %)**
  - Vérification de l'idempotence Alembic `upgrade head -> downgrade 20261114_1705 -> upgrade head`
  - Rejet `403 ERR_OBSERVER_MODE_READ_ONLY` et `403 ERR_CODEGRAPH_WORKSPACE_LEAD_REQUIRED` validés
  - Persistance réelle contrôlée par requête `SELECT` directe sur PostgreSQL 18
- **Tests Vitest Frontend (`apps/web`)** :
  - `story-18-1-workspace-sources-route-modal-and-f5.test.tsx` : **3 tests passés (100 %)**
  - `zero-dead-buttons-and-silent-catches-audit.test.tsx` : **7 tests passés (100 %)**
  - Survie au rechargement F5 validée (`unmount()` + `render()`)
- **Linters et vérification statique** :
  - `ruff check .` et `ruff format --check .` : **0 erreur**
  - `mypy --strict packages/orcia-core packages/orcia-connectors apps/api apps/worker` : **0 erreur dans 301 fichiers**
  - `lint-imports` : **5 contrats respectés, 0 violation**
  - `export_openapi.py --check` : **0-diff validé**
  - `turbo run lint typecheck` : **6/6 tâches réussies (3 packages)**

---

### 3.3 Traçabilité des Cinq Garde-Fous de Câblage Vertical

1. **Zéro Adaptateur SQL Orphelin** : Les fonctions `create_workspace_datasource_on_postgres18`, `update_workspace_datasource_on_postgres18`, `delete_workspace_datasource_on_postgres18`, `trigger_workspace_datasource_sync_on_postgres18` et `list_workspace_datasources_from_postgres18` sont toutes appelées activement dans `apps/api/src/orcia_api/routers/workspace_datasources.py`.
2. **Test d'Intégration Vertical HTTP -> PostgreSQL 18** : Testé via `test_story_18_1_workspace_sources_postgres18.py` sur un conteneur `pgvector/pgvector:pg18` réel avec vérification `SELECT` directe.
3. **Interdiction des Stores Métier Éphémères & Survie au F5** : Les sources sont persistées en base via `@orcia/api-client`, rechargées au montage via `loadData()`, et testées sous démontage/remontage React (`unmount()` $\rightarrow$ `render()`).
4. **Zéro Bouton Muet & Zéro Callback Optionnel Oublié** : Les boutons d'action (Rattacher, Modifier, Synchroniser, Supprimer) appellent leurs gestionnaires respectifs sans aucun `.catch(() => undefined)` silencieux.
5. **Respect des Seuils de Volumétrie** : Aucun fichier touché ne dépasse le seuil cible de 350 lignes (`enterprise_connectors.py` : 331 l., `workspace_sources_governance.py` : 252 l., `sql_workspace_datasources_queries.py` : 322 l., `sql_workspace_datasources_mutations.py` : 324 l., `WorkspaceSourcesRagTab.tsx` : 331 l.).
