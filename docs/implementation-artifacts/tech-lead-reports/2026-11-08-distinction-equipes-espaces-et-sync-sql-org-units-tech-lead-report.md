# 2026-11-08 — Distinction Explicite Équipes / Espaces dans le Sélecteur d'Entête & Synchronisation Bidirectionnelle SQL `org_units` / `workspaces`

> **Convention de nommage du fichier (Obligatoire — créé AVANT toute modification de code)** :
> - `docs/implementation-artifacts/tech-lead-reports/2026-11-08-distinction-equipes-espaces-et-sync-sql-org-units-tech-lead-report.md`

- **Date** : 2026-11-08
- **Story / Clé Sprint** : `2026-11-08-distinction-equipes-espaces-et-sync-sql-org-units` (`Ajustement Transverse` — `Epic 8` / `Epic 9` / `Epic 11`)
- **Capacité(s)** : `CAP-067` (Rattachement d'équipe, facturation, espaces privés et sélecteur de contexte) & `CAP-061` (Accostage progressif Jour 0 et persistance `platform-setup-state`) — classification : `ux` & `hygiène`
- **Auteur / Contexte** : Résolution d'une ambiguïté UX et d'une asymétrie de persistance PostgreSQL 18 où un Espace de travail (`RTS`, table `workspaces`) apparaissait dans le sélecteur d'entête (`TopHeaderBar`) sous le badge `👥 Mes Équipes & Espaces` sans distinction visuelle avec une Équipe (`org_unit` de type `TEAM`), tandis que le panneau `1. Structure de l'Organisation (Directions / BU & Équipes)` n'affichait pas les unités d'organisation issues de la table relationnelle `org_units`. Couvre `FR-3`, `FR-21`, `FR-31`, `FR-32`, `FR-34`.
- **Branche Git dédiée** : `fix/scope-switcher-and-org-sql-sync`

---

## 1. Analyse du Besoin & Étude d'Impact Tech Lead (Pré-Implémentation)

### 1.1 Contexte & Problématique
- **Symptôme constaté par l'utilisateur** :
  - Dans le menu déroulant en haut à gauche (`Espace : Plateforme Globale ORCIA`), l'entrée `RTS` apparaît avec le badge `👥 Mes Équipes & Espaces`, donnant l'impression que `RTS` est une Équipe.
  - Or, dans `Configuration › Organisation & Habilitations › 1. Structure de l'Organisation (Directions / BU & Équipes)`, seule la BU `123` apparaît et l'alerte `⚠️ Aucune Équipe de facturation rattachée à votre compte (appels IA verrouillés)` est affichée.
- **Diagnostic racine (double cause UI + SQL)** :
  1. **Confusion visuelle dans le sélecteur de périmètre (`ShellContainer.tsx`)** :
     - `teamUnits` (`orgUnits` de niveau `TEAM`) et `sharedOrConfidentialWorkspaces` (`workspaces` de visibilité `STANDARD` ou `CONFIDENTIAL_RESTRICTED`) sont tous deux injectés dans `workspaceOptions` avec le même `groupLabel` (`👥 Mes Équipes & Espaces`).
     - Lorsqu'un espace de travail (`RTS`) n'a pas de `ownerOrgUnitName` renseigné, son libellé est simplement `RTS` en face du badge `👥 Mes Équipes & Espaces`, le rendant visuellement indiscernable d'une Équipe (`TEAM`).
  2. **Asymétrie de réconciliation et absence de purge relationnelle dans `sql_platform_setup_store.py`** :
     - `load_platform_setup_state_from_postgres18` possédait un fallback de réconciliation pour `workspaces` (depuis la table SQL `workspaces`) et `llm_tiers` (depuis `llm_model_endpoints`), mais **aucun fallback pour `org_units`** depuis la table SQL `org_units`.
     - `_sync_relational_tables_on_postgres18` exécutait uniquement des `INSERT ... ON CONFLICT DO UPDATE` sans supprimer des tables relationnelles `org_units` et `workspaces` les entités retirées du snapshot, et sans préserver le lien hiérarchique `parent_id` (`TEAM` $\rightarrow$ `BU`) ni `owner_org_unit_id` (`Workspace` $\rightarrow$ `TEAM`/`BU`).
     - De plus, le test de fuzzing `tests/contract/test_openapi_contract.py` (`test_schemathesis_openapi_contract_compliance`) s'exécutait sans `ORCIA_DISABLE_PG_BOOTSTRAP_SYNC="1"`, écrasant `platform_settings` en base locale avec `org_units: []` et `workspaces: []`, ce qui déclenchait ensuite la réhydratation fantôme de `RTS` depuis la table SQL `workspaces` sans réhydrater `org_units`.

### 1.2 Exploration, Analyse d'Impact GitNexus, Factorisation & Dette Technique
- **Analyse d'Impact GitNexus (`gitnexus_query`, `gitnexus_context`, `gitnexus_impact`)** :
  - `load_platform_setup_state_from_postgres18` & `save_platform_setup_state_to_postgres18` (`packages/orcia-core/src/orcia_core/bootstrap/_internal/sql_platform_setup_store.py`) : appelés par `get_platform_setup_state` et `put_platform_setup_state` dans `apps/api/src/orcia_api/routers/bootstrap_accostage.py`.
  - `InnerShellContainer` (`apps/web/src/components/ShellContainer.tsx`) : construit `workspaceOptions` transmis à `FourZoneDirectionCShell` (`packages/ui/src/primitives/FourZoneDirectionCShell.tsx`).
- **Exploration & Chiffres Clés (Base de Données PostgreSQL 18 locale)** :
  - `org_units` contenait 3 lignes (`orcia-root` ENTERPRISE, `DS3C` BU, `MonCompte` TEAM).
  - `workspaces` contenait 1 ligne (`RTS`, `slug: rts`, `ui_workspace_id: ws-1`).
  - `platform_settings` (`key = 'platform_setup_state_v1'`, version 54) avait été pollué par Schemathesis (`org_units: []`, `workspaces: [RTS]`, 18 entrées `llm_tiers` fuzzées).
- **Opportunités de Factorisation & Résorption de Dette Technique Naissante** :
  - **Découpage de `sql_platform_setup_store.py` (`422 lignes` $\rightarrow$ `< 260 lignes`)** : extraction de la synchronisation relationnelle PostgreSQL 18 (`_sync_relational_tables_on_postgres18` et réconciliation `org_units`/`workspaces`) dans `packages/orcia-core/src/orcia_core/bootstrap/_internal/sql_platform_setup_relational_sync.py`.
  - **Découpage de `ShellContainer.tsx` (`871 lignes` $\rightarrow$ `< 380 lignes`)** : extraction de la construction des options du sélecteur de périmètre, des notifications de prérequis et de la modale d'initialisation du 1er Administrateur Jour 0 dans `apps/web/src/components/FirstBootAdminSetupModal.tsx` et `apps/web/src/components/shellScopeOptions.ts`.

---

## 2. Plan d'Implémentation

### 2.1 Schéma de Données & Migrations Alembic (`infra/migrations/versions/...`, si applicable)
- Aucune migration Alembic requise : les tables `platform_settings`, `org_units` et `workspaces` disposent déjà de toutes les colonnes nécessaires (`unit_type`, `parent_id`, `owner_org_unit_id`, `settings_jsonb`).

### 2.2 Noyau Métier Hexagonal, Orchestration & Workers (`packages/orcia-core/`)
- `packages/orcia-core/src/orcia_core/bootstrap/_internal/sql_platform_setup_relational_sync.py` (Création) :
  - Synchronisation bidirectionnelle fidèle de `org_units` (`BU` puis `TEAM`, avec résolution du `parent_id` vers la `BU` parente ou `orcia-root` et stockage de l'identifiant UI dans une correspondance déterministe) et suppression des unités `BU`/`TEAM` retirées du snapshot (après réattribution sécurisée des FK éventuelles vers `orcia-root`).
  - Synchronisation fidèle de `workspaces` (avec résolution de `owner_org_unit_id` vers l'unité d'organisation propriétaire, persistance de `owner_org_unit_id` et `owner_org_unit_name` dans `settings_jsonb`, et suppression des espaces retirés du snapshot).
  - Réconciliation symétrique à la lecture (`reconcile_org_units_from_relational`, `reconcile_workspaces_from_relational`) : si `platform_settings` n'a pas encore d'état ou si `org_units` est vide alors que des `BU`/`TEAM` existent dans `org_units`, réhydrate `org_units` avec leur hiérarchie `parentId` et enrichit `ownerOrgUnitName` sur chaque espace de travail.
- `packages/orcia-core/src/orcia_core/bootstrap/_internal/sql_platform_setup_store.py` (Modification & allègement) :
  - Délègue la synchronisation et la réconciliation relationnelle à `sql_platform_setup_relational_sync.py`.

### 2.3 Couche Backend API, Sécurité & Contrats (`apps/api/`, `tests/contract/`)
- `apps/api/src/orcia_api/routers/bootstrap_accostage.py` :
  - Import explicite de `load_platform_setup_state_from_postgres18` et `save_platform_setup_state_to_postgres18` pour garantir la traçabilité directe dans le graphe d'appels GitNexus (`impactedCount >= 1`).
- `tests/contract/test_openapi_contract.py` :
  - Isolation du runner Schemathesis via `ORCIA_DISABLE_PG_BOOTSTRAP_SYNC="1"` pour empêcher le fuzzing de contrat OpenAPI d'écrire des payloads aléatoires Hypothesis dans la base PostgreSQL 18 locale.

### 2.4 Interface Utilisateur & Expérience (`apps/web/`)
- `apps/web/src/components/shellScopeOptions.ts` (Création) :
  - Construction typée et explicite des options du sélecteur de périmètre (`buildWorkspaceSwitcherOptions`) :
    - **Espaces privés** : `🔒 Espace · {ws.name}` (ou `🔒 Espace · {ws.name} · {ws.ownerOrgUnitName}`) — badge `🔒 Mes Espaces Privés`.
    - **Équipes (`TEAM`)** : `👥 Équipe · {team.name}` — badge `👥 Équipe · Mes Équipes & Espaces`.
    - **Espaces collectifs / confidentiels (`WORKSPACE`)** : `📦 Espace · {ws.name} · {ws.ownerOrgUnitName}` (ou `📦 Espace · {ws.name}`) — badge `📦 Espace · 👥 Mes Équipes & Espaces`.
    - **Directions (`BU`)** : `🏢 Direction (BU) · {bu.name}` — badge `🏢 Supervision Organisation`.
    - **Plateforme Globale (`GLOBAL`)** : `Plateforme Globale ORCIA` — badge `🏢 Supervision Organisation`.
- `apps/web/src/components/FirstBootAdminSetupModal.tsx` (Création) & `apps/web/src/components/ShellContainer.tsx` (Modification) :
  - Extraction de la modale Jour 0 et utilisation de `buildWorkspaceSwitcherOptions` pour ramener `ShellContainer.tsx` sous le seuil des 400 lignes.

### 2.5 Analyse d'Impact sur la Pyramide des Tests (`AD-17` — Couches 1 à 5 + Sécurité, Obligatoire)
- **Couche 1a (Unitaires Python `tests/unit/`)** : Ajout de tests dans `tests/unit/test_epic_9_story_9_2_accostage_and_first_user.py` vérifiant la synchronisation relationnelle (`org_units` + `workspaces`), la préservation de `parentId` / `ownerOrgUnitName`, la purge lors des suppressions et la réconciliation symétrique.
- **Couche 1b (Unitaires/Composants TS `Vitest`)** : Mise à jour et ajout d'assertions dans `apps/web/src/__tests__/i18n-and-shell.test.tsx` vérifiant que le sélecteur d'entête distingue explicitement `👥 Équipe · ...` et `📦 Espace · ...`.
- **Couche 2 (Intégration Verticale `HTTP FastAPI ➔ PostgreSQL 18` `tests/integration/`)** : Vérification dans `tests/integration/test_http_vertical_day0_and_agents_postgres18.py` que la suppression d'une `org_unit` ou d'un `workspace` via `PUT /api/v1/bootstrap/platform-setup-state` supprime bien la ligne correspondante dans PostgreSQL 18 et ne crée aucun fantôme au `GET` suivant.
- **Couche 3 (Contrats OpenAPI 3.1 `0-diff`, Schemathesis & `lint-imports`)** : Isolation de `test_schemathesis_openapi_contract_compliance` (`ORCIA_DISABLE_PG_BOOTSTRAP_SYNC="1"`) et vérification `lint-imports`.
- **Couche 4 & Sécurité** : Non-régression complète.

---

## 3. Bilan des Modifications & Résultats (Post-Implémentation)

### 3.1 Fichiers Développés & Modifiés
| Fichier | Nature (Création / Modification / Refactoring) | Description synthétique |
| :--- | :--- | :--- |
| `packages/orcia-core/src/orcia_core/bootstrap/_internal/sql_platform_setup_relational_sync.py` | Création (`272 lignes`) | Synchronisation relationnelle bidirectionnelle `org_units` (`BU` puis `TEAM` avec `parent_id`), `workspaces` (`owner_org_unit_id`, `owner_org_unit_name`) et purge sécurisée des entités supprimées |
| `packages/orcia-core/src/orcia_core/bootstrap/_internal/sql_platform_setup_store.py` | Refactoring (`422 ➔ 292 lignes`) | Réconciliation symétrique `_reconcile_org_units_on_load` + `_reconcile_workspaces_on_load` et délégation à `sql_platform_setup_relational_sync.py` |
| `apps/api/src/orcia_api/routers/bootstrap_accostage.py` | Modification | Import et appel directs de `load_platform_setup_state_from_postgres18` et `save_platform_setup_state_to_postgres18` pour traçabilité GitNexus |
| `apps/web/src/components/shellScopeOptions.ts` | Création (`242 lignes`) | Constructeur typé `buildWorkspaceSwitcherOptions` distinguant explicitement `👥 Équipe · <nom>`, `📦 Espace · <nom>`, `🔒 Espace · <nom>` et `🏢 Direction (BU) · <nom>` |
| `apps/web/src/components/FirstBootAdminSetupModal.tsx` | Création (`253 lignes`) | Extraction de la modale d'initialisation du 1er Administrateur Jour 0 |
| `apps/web/src/components/ShellContainer.tsx` | Refactoring (`871 ➔ 385 lignes`) | Délégation à `shellScopeOptions.ts` et `FirstBootAdminSetupModal.tsx` |
| `apps/web/src/components/platformSetupStore.tsx` | Modification | Réconciliation automatique de `memberTeamIds` avec les unités `TEAM` hydratées depuis PostgreSQL 18 |
| `infra/migrations/versions/20261108_0910_declarative_packs_and_workflows_v2.py` | Correctif | Séparation des instructions DDL multi-commandes en appels `op.execute` unitaires pour compatibilité `asyncpg` sous `testcontainers` |
| `tests/contract/test_openapi_contract.py` | Modification | Isolation du fuzzing Schemathesis via `ORCIA_DISABLE_PG_BOOTSTRAP_SYNC="1"` |
| `apps/web/src/__tests__/scope-switcher-and-org-sync.test.tsx` | Création | Tests unitaires Vitest FR/EN de `buildWorkspaceSwitcherOptions` |
| `tests/unit/test_epic_9_story_9_2_accostage_and_first_user.py` | Modification | Tests unitaires de synchronisation, purge et réconciliation relationnelle `org_units` / `workspaces` |
| `tests/integration/test_http_vertical_day0_and_agents_postgres18.py` | Modification | Test d'intégration vertical PostgreSQL 18 couvrant la hiérarchie `BU ➔ TEAM ➔ Workspace`, la réconciliation symétrique et la purge à la suppression |

### 3.2 Résultats Chiffrés, Métriques & Qualité
- **Couverture de tests** : `94 %` sur `sql_platform_setup_relational_sync.py` ; `100 %` sur `scope-switcher-and-org-sync.test.tsx`.
- **Volumétrie des fichiers refactorisés** :
  - `ShellContainer.tsx` : réduit de `871` à `385` lignes (`< 400` lignes).
  - `sql_platform_setup_store.py` : réduit de `422` à `292` lignes (`< 300` lignes).
- **Qualité statique & Architecture** :
  - `ruff check` : `0 warning`
  - `mypy --strict` & `pnpm --filter @orcia/web typecheck` : `0 error`
  - `lint-imports` : `5 contracts kept, 0 broken`
  - `lint_spine.py` : `ok: true, 0 findings`

### 3.3 Validation & Procédure de Test sur Toute la Pyramide (`AD-17` + 5 Garde-Fous de Câblage Vertical)
- **Couche 1a — Tests Unitaires Python (`pytest`)** : `tests/unit/test_epic_9_story_9_2_accostage_and_first_user.py` (`5 passed`).
- **Couche 1b — Tests Unitaires Frontend (`Vitest`)** : `apps/web/src/__tests__/scope-switcher-and-org-sync.test.tsx` (`2 passed`).
- **Couche 2 — Tests d'Intégration Verticale `HTTP ➔ PostgreSQL 18` (`testcontainers`)** : `tests/integration/test_http_vertical_day0_and_agents_postgres18.py::test_platform_setup_state_http_put_persists_settings_org_workspaces_and_llm_in_pg18` (`1 passed` sur conteneur PostgreSQL 18 réel).
- **Couche 3 — Contrats & Registre des Capacités** : `pnpm site:sync` & `pnpm site:check` conformes.
