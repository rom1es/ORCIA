# Story 5.2 — Supervision Multi-Runs Dynamique (< 1 s), Sélecteur de Périmètre Hiérarchique (⌘W), Centre de Pilotage Unifié Multi-Niveaux des Workspaces (/workspaces à 4 Onglets), RunAccessGuard (HTTP 403) & Palette ⌘K

- **Date** : 2026-10-30
- **Story / Clé Sprint** : `5-2-supervision-multi-runs-dynamique-1-s-sélecteur-de-périmètre` (`Epic 5`)
- **Auteur / Contexte** : Consolidation hiérarchique (`GLOBAL | BU | TEAM | WORKSPACE`) des 4 onglets fractals du Centre de Pilotage Unifié (`/workspaces`), distinction `CONTRIBUTOR_ACTION_REQUIRED` vs `READ_ONLY_OBSERVER`, masquage des payloads métiers `CONFIDENTIAL_RESTRICTED` pour `PLATFORM_ADMIN` tout en conservant la visibilité FinOps, garde `RunAccessGuard` ($O(1)$ `HTTP 403 ERR_OBSERVER_MODE_READ_ONLY` / `HTTP 409 ERR_STEP_ALREADY_CLAIMED_BY_PEER`), `<ProductLifecycleCard />` (`RUN | BUILD | MIGRATION`), `<GuidanceDrawer />` (5 étapes) et palette `<CommandPaletteModal />` (`⌘K` `< 1 s`) (`FR-1`, `FR-3`, `AD-4`, `AD-14`, `AD-19`, `UX-DR2`, `UX-DR11`, `UX-DR13`, `NFR-PERF-1`).
- **Commits associés** : `working-tree`

---

## 1. Analyse du Besoin & Étude d'Impact Tech Lead (Pré-Implémentation)

### 1.1 Contexte & Problématique
- Un directeur de BU, un administrateur plateforme ou un Tech Lead multi-projets doit pouvoir superviser simultanément plusieurs *Workflow Runs* et *Workspaces* à différentes échelles (`GLOBAL -> BU -> TEAM -> WORKSPACE`) sans jamais altérer par erreur une étape en mode `READ_ONLY_OBSERVER` ni exposer les payloads métiers des espaces `CONFIDENTIAL_RESTRICTED`.

### 1.2 Exploration, Analyse d'Impact GitNexus, Factorisation & Dette Technique
- **Analyse d'Impact GitNexus (`gitnexus_impact`)** :
  - `MatrixPermissionEvaluator` (`risk: MEDIUM`, 15 dépendants) : réutilisation directe sans modification cassante dans `ControlCenterOverviewService`.
  - `WorkspaceTopologyPanel` : enrichissement de `WorkspacesFeaturePanel` avec `<WorkspaceControlCenter />` et `<CommandPaletteModal />`.
- **Contrôle de Volumétrie** :
  - Découpage en 2 fichiers `< 330` lignes dans `packages/orcia-core/src/orcia_core/orchestration/` : `control_center_models.py` (`177` lignes) et `control_center.py` (`324` lignes).

---

## 2. Plan d'Implémentation

### 2.1 Schéma de Données & Migrations Alembic
- S'appuie sur `org_units`, `workspaces`, `workspace_datasources`, `workflow_runs`, `step_executions` et `task_notifications` (`0021_story_5_1`).

### 2.2 Noyau Métier Hexagonal (`packages/orcia-core/src/orcia_core/orchestration/control_center.py`)
- `ControlCenterOverviewService.build_overview()` : consolidation en 1 passe des 4 onglets fractals (`contributor_runs`, `observer_runs`, `datasources`, `guidance_steps`, `workflow_overrides`, `org_units`, `workspaces_governance`).
- `ControlCenterOverviewService.enforce_run_mutation_guard()` : garde $O(1)$ rejetant `READ_ONLY_OBSERVER` (`403`) et les verrous détenus par un pair (`409`).
- `ControlCenterOverviewService.set_workspace_lifecycle_phase()` : qualification `RUN | BUILD | MIGRATION` avec adaptation dynamique des workflows recommandés.

### 2.3 Couche Backend API (`apps/api/src/orcia_api/routers/control_center.py`)
- `GET /api/v1/control-center/overview`
- `PATCH /api/v1/control-center/workspaces/{workspace_id}/lifecycle`
- `POST /api/v1/control-center/runs/{run_id}/steps/{step_id}/mutate-check`
- `GET /api/v1/control-center/command-palette`

### 2.4 Interface Utilisateur Direction C (`packages/ui/` & `apps/web/`)
- `<WorkspaceControlCenter />`, `<ProductLifecycleCard />`, `<GuidanceDrawer />`, `<CommandPaletteModal />` dans `@orcia/ui`.

---

## 3. Bilan des Modifications & Résultats (Post-Implémentation)

### 3.1 Fichiers Développés & Modifiés
| Fichier | Nature | Description synthétique |
| :--- | :--- | :--- |
| `packages/orcia-core/src/orcia_core/orchestration/control_center_models.py` | Création | Modèles immuables des 4 onglets fractals et de la palette `⌘K` |
| `packages/orcia-core/src/orcia_core/orchestration/control_center.py` | Création | `ControlCenterOverviewService` et `RunAccessGuard` |
| `apps/api/src/orcia_api/routers/control_center.py` | Création | Routes REST `/api/v1/control-center/*` |
| `packages/ui/src/primitives/WorkspaceControlCenter.tsx` | Création | Centre de pilotage 4 onglets + sélecteur `⌘W` |
| `packages/ui/src/primitives/ProductLifecycleCard.tsx` | Création | Carte cycle de vie `RUN | BUILD | MIGRATION` |
| `packages/ui/src/primitives/GuidanceDrawer.tsx` | Création | Tiroir méthodologique en 5 étapes |
| `packages/ui/src/primitives/CommandPaletteModal.tsx` | Création | Palette universelle `⌘K` |
| `tests/unit/test_story_5_2_control_center_and_run_access_guard.py` | Création | Tests unitaires et HTTP de Story 5.2 |

### 3.2 Résultats Chiffrés, Métriques & Qualité
- **Recherche `⌘K` mesurée** : `< 1 ms` (cible `< 1 s` `NFR-PERF-1`).
- **Tests `test_story_5_2_control_center_and_run_access_guard.py`** : `3 passed`.
