# Spécification Technique — Story 5.2 (`5-2-supervision-multi-runs-dynamique-1-s-sélecteur-de-périmètre`)

## 1. Périmètre & Exigences Couvertes
- **User Story** : `5-2-supervision-multi-runs-dynamique-1-s-sélecteur-de-périmètre`
- **Exigences fonctionnelles & architecturales** : `FR-1`, `FR-3`, `AD-4`, `AD-14`, `AD-19`, `UX-DR2`, `UX-DR11`, `UX-DR13`, `NFR-PERF-1`.
- **Composants livrés** :
  1. **Service de Supervision Multi-Niveaux & `RunAccessGuard` (`packages/orcia-core/src/orcia_core/orchestration/control_center.py`)** :
     - Consolidation hiérarchique récursive (`GLOBAL -> BU -> TEAM -> WORKSPACE`) sans requête `N+1` pour les **4 onglets fractals** du Centre de Pilotage Unifié :
       - **Onglet 1 (`RUNS_AND_ARTIFACTS`)** : instances de *Workflow Runs* séparées en `CONTRIBUTOR_ACTION_REQUIRED` (actions requises en haut) vs `READ_ONLY_OBSERVER` (en suivi en bas), mode `COACHING` vs `FAST_PATH`, verrou de présence `Claim`, budget consommé USD, et masquage des payloads métiers sur les Workspaces `CONFIDENTIAL_RESTRICTED` pour un `PLATFORM_ADMIN` non membre explicite (tout en conservant la supervision technique/FinOps).
       - **Onglet 2 (`DATASOURCES`)** : sources dédiées et partagées (`workspace_datasources`), statut d'indexation dans le Graphe Tripartite, alertes `[STALE_WARNING]`, et les 5 étapes méthodologiques du `<GuidanceDrawer />`.
       - **Onglet 3 (`WORKFLOWS_AND_OVERRIDES`)** : workflows/agents actifs avec graphe DAG, inspecteur de surcharges déclaratives à 4 niveaux (`1. Base -> 2. TEAM -> 3. WORKSPACE -> 4. USER`), et contrat `ARCHITECTURE-SPINE.md`.
       - **Onglet 4 (`TEAMS_AND_GOVERNANCE`)** : arborescence `org_units`, produits/workspaces qualifiés par phase de cycle de vie **`RUN | BUILD | MIGRATION`** (`<ProductLifecycleCard />` + workflows suggérés adaptés), membres invités, délégations de Gates et politique de visibilité (`STANDARD` vs `CONFIDENTIAL_RESTRICTED`).
     - **`RunAccessGuard`** : vérification en $O(1)$ du mode d'accès (`CONTRIBUTOR_ACTION_REQUIRED` vs `READ_ONLY_OBSERVER`) et du verrou `lock:step:{step_execution_id}`, levant `HTTP 403 ERR_OBSERVER_MODE_READ_ONLY` ou `HTTP 409 ERR_STEP_ALREADY_CLAIMED_BY_PEER` sur toute tentative de mutation non autorisée.
  2. **Endpoints FastAPI (`apps/api/src/orcia_api/routers/control_center.py` & `schemas/control_center.py`)** :
     - `GET /api/v1/control-center/overview?scope_type=GLOBAL|BU|TEAM|WORKSPACE&scope_id={id}`
     - `POST /api/v1/control-center/runs/{run_id}/steps/{step_id}/mutate-check` (garde `RunAccessGuard` explicite et réutilisable sur toutes les mutations d'étapes/artefacts/Gates)
     - `PATCH /api/v1/control-center/workspaces/{workspace_id}/lifecycle` (bascule `RUN | BUILD | MIGRATION` protégée par `RunAccessGuard`)
     - `GET /api/v1/control-center/command-palette?q={query}` (recherche `< 1 s` Runs, Workspaces, Catalogue, Ontologie et raccourcis clavier `⌘K`)
  3. **Design System `@orcia/ui` (`packages/ui/src/primitives/`) & Routes `apps/web`** :
     - `<ProductLifecycleCard />` (`RUN | BUILD | MIGRATION` avec workflows recommandés)
     - `<GuidanceDrawer />` (tiroir méthodologique repliable en 5 étapes numérotées sur l'Onglet 2)
     - `<CommandPaletteModal />` (`⌘K` / `Ctrl+K`, bascule Run `< 1 s`, raccourcis `g c`, `g i`, `g f`, `g o`, `g g`, `g a`, `g s`, `g w`, `[`, `]`, `Alt + ↑/↓`)
     - `<WorkspaceControlCenter />` (4 onglets fractals + sélecteur de périmètre `⌘W` + bandeau `👁️ Mode Consultation Seule`) branché sur `/workspaces` et `/workspaces/$workspaceId`.
