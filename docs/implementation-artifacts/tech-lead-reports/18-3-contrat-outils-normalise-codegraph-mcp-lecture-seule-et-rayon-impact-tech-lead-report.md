# Story 18.3 — Contrat d'Outils Normalisé `codegraph-mcp` Lecture Seule (`5` Outils) & Intégration Workflows de Revue

- **Date** : `2026-11-14`
- **Story / Clé Sprint** : `18-3-contrat-outils-normalise-codegraph-mcp-lecture-seule-et-rayon-impact` (`Epic 18`)
- **Capacité(s)** : `CAP-082`, `CAP-140`, `CAP-180` — classification : `feature`
- **Auteur / Contexte** : Exposition d'un contrat d'outils MCP normalisé, déterministe et strictement lecture seule dans `packages/orcia-connectors` (`5` outils : `codegraph_locate_symbol`, `codegraph_get_call_hierarchy`, `codegraph_find_references`, `codegraph_calculate_blast_radius`, `codegraph_read_span` borné à `<= 250` lignes), agnostique vis-à-vis de l'indexeur sous-jacent (`GitNexusMcpHttpProvider` par défaut ou `SourcegraphScipMcpProvider` via `CODEGRAPH_PROVIDER`), confiné côté serveur au `workspace_id` courant et aux dépôts `SOURCE_CODE` où `codegraph_enabled == True`, avec détection explicite de dérive (`GRAPH_MOVED_SINCE_RUN_LOCK`) vis-à-vis de `run-lock.json` et intégration dans `wf-03-etude-architecture.yaml` (`Arbitrages 3A` & `4A`). Couverture : `FR-17`, `FR-35`, `AD-17`, `AD-19`, `AD-20`.
- **Commits associés** : _À compléter en Section 3 après validation des portes CI_

---

## 1. Analyse du Besoin & Étude d'Impact Tech Lead (Pré-Implémentation)

### 1.1 Contexte & Problématique
- **Absence d'exploration déterministe de graphe de code par les agents** :
  1. `packages/orcia-connectors/src/orcia_connectors/` contient déjà `protocol.py` (`171` l., `OrciaConnectorProtocol` à 4 méthodes), `adapters/git_provider.py` (`95` l.) et `adapters/mcp_client_bridge.py` (`80` l.), mais aucun adaptateur dédié au graphe sémantique de code ni contrat normalisé anti-verrouillage éditeur (`GitNexus` vs `Sourcegraph SCIP`).
  2. Les agents de revue d'architecture (`wf-03-etude-architecture.yaml`) et *Blind Hunters* ne disposent pas encore d'outils typés pour tracer la hiérarchie d'appels, calculer le *blast radius* ou lire une tranche bornée de lignes (`<= 250` lignes) sans découpage vectoriel naïf.
- **Invariants non négociables (`ARCHITECTURE-SPINE.md` & `GEMINI.md`)** :
  - **Contrat 4 `lint-imports` (`pyproject.toml:L151-160`)** : `orcia_core` ne doit **JAMAIS** importer `orcia_connectors` (`api / worker -> orcia_connectors -> orcia_core`). Tout code `codegraph-mcp` vit donc exclusivement dans `packages/orcia-connectors` (et le routeur HTTP dans `apps/api`).
  - **Règle 1 FastAPI (`TID251`)** : aucun `httpx.Client` synchrone dans `apps/api/src/orcia_api/routers/codegraph_mcp.py` ; utiliser le client asynchrone partagé `request.app.state.http_client`.
  - **Lecture seule absolue & confinement** : `workspace_id` injecté côté serveur ; rejet si `repo_alias` absent de l'espace ou si `codegraph_enabled == False` ; rejet inconditionnel de `preview_write()` et `execute_write()`.

### 1.2 Exploration, Analyse d'Impact GitNexus, Factorisation & Dette Technique
- **Analyse d'Impact GitNexus (`gitnexus_context`, `gitnexus_impact`, `repo: /home/romain/Documents/Projects/ORCIA`)** :
  - `McpClientBridgeConnector` (`packages/orcia-connectors/src/orcia_connectors/adapters/mcp_client_bridge.py`, `80` l.) : `impactedCount: 3` (`adapters/__init__.py`, `orcia_connectors/__init__.py`) + frontière de dispatch `OrciaConnectorProtocol` (`5` implémentations). Le nouvel adaptateur `CodegraphMcpConnector` implémente exactement `OrciaConnectorProtocol` pour hériter des tests de conformité de `test_connector_protocol_and_write_preview.py`.
  - `bounded_workflow_v2.py` (`apps/worker/src/orcia_worker/workflows/bounded_workflow_v2.py:L221-L275`) et `packs/sdlc/workflows/wf-03-etude-architecture.yaml` : les sous-étapes déclarent `toolbox_mcp_permissions` (`connector_id`, `scope`), permettant d'ajouter `connector_id: mcp:codegraph`, `scope: read` sans modifier la structure déclarative `AD-20`.
- **Volumétrie & Découpage Proactif (`<= 280` l. par module)** :
  - Séparation en 3 modules compacts : `orcia_connectors/codegraph/models.py`, `orcia_connectors/codegraph/providers.py`, et `orcia_connectors/adapters/codegraph_mcp.py`.

---

## 2. Plan d'Implémentation

### 2.1 Schéma de Données & Migrations Alembic
- Aucune nouvelle table SQL requise : `Story 18.3` consomme directement les métadonnées `workspace_datasources` (`alias`, `source_nature`, `codegraph_enabled`, `codegraph_status`, `codegraph_head_sha`, `target_ref`) livrées par la révision `20261114_1801`.

### 2.2 Noyau Connecteurs & Orchestration (`packages/orcia-connectors/`, `apps/worker/`, `packs/`)
- `packages/orcia-connectors/src/orcia_connectors/codegraph/models.py` (`<= 240` l.) :
  - Modèles Pydantic / dataclasses pour les 5 outils (`codegraph_locate_symbol`, `codegraph_get_call_hierarchy`, `codegraph_find_references`, `codegraph_calculate_blast_radius`, `codegraph_read_span` avec validation stricte `1 <= start_line <= end_line` et `end_line - start_line + 1 <= 250`, plus rejet anti-path-traversal `..` / chemin absolu).
  - Champ systématique `indexed_commit_sha` et alerte explicite `drift_warning = "GRAPH_MOVED_SINCE_RUN_LOCK"` si `run_lock_commit_sha` diffère de `indexed_commit_sha`.
- `packages/orcia-connectors/src/orcia_connectors/codegraph/providers.py` (`<= 260` l.) :
  - Protocole `CodegraphBackendProvider` + fabrique `build_codegraph_provider(provider_name)` lisant `CODEGRAPH_PROVIDER` (`gitnexus` par défaut ou `sourcegraph_scip`).
  - `GitNexusMcpHttpProvider` (client HTTP asynchrone `httpx.AsyncClient` injecté vers `CODEGRAPH_MCP_ENDPOINT` avec en-tête interne `X-Orcia-Internal-Token` et traduction JSON-RPC/MCP).
  - `SourcegraphScipMcpProvider` (adaptateur alternatif sur le même contrat de 5 outils).
- `packages/orcia-connectors/src/orcia_connectors/adapters/codegraph_mcp.py` (`<= 260` l.) :
  - `CodegraphMcpConnector(OrciaConnectorProtocol)` : injection serveur de `workspace_id`, résolution des dépôts autorisés (`source_nature == "SOURCE_CODE"` et `codegraph_enabled == True`), lecture seule stricte (`preview_write` et `execute_write` lèvent `PermissionError`).
- `packs/sdlc/workflows/wf-03-etude-architecture.yaml` & exécuteur workflow (`apps/worker/src/orcia_worker/workflows/` / `bounded_workflow_v2.py`) :
  - Ajout de `mcp:codegraph` (`scope: read`) dans `wf-03-etude-architecture.yaml` et support d'invocation de `codegraph_calculate_blast_radius` lors d'une étape de revue.

### 2.3 Couche Backend API, Sécurité & Contrats (`apps/api/`, `packages/api-client/`)
- `apps/api/src/orcia_api/schemas/codegraph_mcp.py` (enregistré dans `SCHEMA_DOMAIN_MODULES` de `scripts/export_openapi.py`) & `apps/api/src/orcia_api/routers/codegraph_mcp.py` (`<= 240` l.) monté dans `main.py` :
  - `GET /api/v1/workspaces/{workspace_id}/codegraph/tools` : liste les 5 outils normalisés et les dépôts actifs (`codegraph_enabled = True`) de l'espace.
  - `POST /api/v1/workspaces/{workspace_id}/codegraph/invoke` : invoque l'un des 5 outils en lecture seule (avec `request.app.state.http_client`, confinement `workspace_id`, et audit structuré sans fuite de secret).
- Régénération SDK OpenAPI `0-diff` (`scripts/export_openapi.py`) et helpers dans `packages/api-client/`.

### 2.4 Interface Utilisateur & Expérience (`apps/web/`)
- Pas de nouvel écran complexe : l'état d'exposition `GitNexus` et les métadonnées des dépôts activés sont déjà affichés sur `/workspaces/$wsId/sources` (`Story 18.1`) ; mise à jour mineure éventuelle du lien ou badge si le SDK reflète l'endpoint `codegraph/tools`.

### 2.5 Analyse d'Impact sur la Pyramide des Tests (`AD-17`)
- **Couche 1a (`tests/unit/connectors/test_story_18_3_codegraph_mcp_tools_and_providers.py` & `test_connector_protocol_and_write_preview.py`)** : validation `OrciaConnectorProtocol` (rejet écriture), les 5 outils, plafond `250` lignes et rejet `..` sur `codegraph_read_span`, détection `GRAPH_MOVED_SINCE_RUN_LOCK`, bascule `gitnexus <-> sourcegraph_scip`, confinement strict `workspace_id` + `codegraph_enabled`, et invocation de `codegraph_calculate_blast_radius` dans un workflow de revue.
- **Couche 3 (`lint-imports`, `export_openapi.py --check`)** : `0` violation `orcia_core -> orcia_connectors`, `0-diff` OpenAPI.

---

## 3. Bilan des Modifications & Résultats

### 3.1 Tableau Synthétique des Fichiers Modifiés / Créés
| Fichier | Nature | Responsabilité / Rôle |
|---|---|---|
| `packages/orcia-connectors/src/orcia_connectors/codegraph/models.py` | Création (`149` l.) | Modèles Pydantic normalisés des 5 outils MCP, validation `read_span` (`<= 250` l., anti-path traversal), calcul déterministe de dérive `compute_drift_warning` (`GRAPH_MOVED_SINCE_RUN_LOCK`). |
| `packages/orcia-connectors/src/orcia_connectors/codegraph/providers.py` | Création (`274` l.) | Protocole `CodegraphBackendProvider`, provider HTTP par défaut `GitNexusMcpHttpProvider` (`X-Orcia-Internal-Token`, `httpx.AsyncClient`), et provider alternatif `SourcegraphScipMcpProvider` piloté par `CODEGRAPH_PROVIDER`. |
| `packages/orcia-connectors/src/orcia_connectors/codegraph/__init__.py` | Création (`19` l.) | Exports du sous-module `codegraph`. |
| `packages/orcia-connectors/src/orcia_connectors/adapters/codegraph_mcp.py` | Création (`287` l.) | Connecteur `CodegraphMcpConnector(OrciaConnectorProtocol)` : lecture seule stricte (`PermissionError` sur écriture), confinement espace `workspace_id`, vérification `SOURCE_CODE` + `codegraph_enabled` et statut actif. |
| `packages/orcia-connectors/src/orcia_connectors/codegraph_tool_runner.py` | Création (`159` l.) | Exécuteur d'outils codegraph pour les workflows de revue, exécution de `codegraph_calculate_blast_radius`, détection de dérive et enrichissement Markdown. |
| `apps/worker/src/orcia_worker/workflows/codegraph_tool_runner.py` | Création (`17` l.) | Re-export pour l'isolation et la compatibilité du worker. |
| `packages/orcia-connectors/src/orcia_connectors/bounded_workflow_v2.py` & `apps/worker/src/orcia_worker/workflows/bounded_workflow_v2.py` | Modification | Intégration de l'exécution automatique de blast radius codegraph lors des étapes avec `mcp:codegraph`, persistance sur `codegraph_impact` et audit event `CODEGRAPH_TOOL_EXECUTED`. |
| `packs/sdlc/workflows/wf-03-etude-architecture.yaml` | Modification | Déclaration de `mcp:codegraph` (`scope: read`) dans les permissions MCP de l'étape d'architecture. |
| `apps/api/src/orcia_api/schemas/codegraph_mcp.py` | Création (`67` l.) | Schémas de transport OpenAPI (`CodegraphToolsListResponse`, `InvokeCodegraphToolRequest`, `InvokeCodegraphToolResponse`). |
| `apps/api/src/orcia_api/routers/codegraph_mcp.py` | Création (`181` l.) | Routes `GET /tools` et `POST /invoke` avec RFC 9457 Problem Details et non-bloquant (`httpx.AsyncClient`). |
| `apps/api/src/orcia_api/main.py` | Modification | Montage du routeur `codegraph_mcp_router` sous `/api/v1`. |
| `packages/api-client/src/domains/codegraphMcp.ts` & `src/index.ts` | Création / Modification | Méthodes clientes typées `listCodegraphTools` et `invokeCodegraphTool`. |
| `scripts/export_openapi.py` & `packages/api-client/src/generated/*` | Modification | Export OpenAPI régénéré à `0-diff` incluant le domaine `codegraph_mcp`. |
| `docs/product/capabilities.yaml` | Modification | Référencement de `codegraph_mcp.py` et des tests unitaires sous `CAP-082`. |
| `tests/unit/connectors/test_story_18_3_codegraph_mcp_tools_and_providers.py` | Création (`270` l.) | Tests unitaires ciblés sur les 5 outils MCP, le plafond de 250 lignes, le drift warning, la bascule de provider et les endpoints HTTP. |
| `tests/unit/connectors/test_connector_protocol_and_write_preview.py` | Modification | Test de conformité protocole et rejet d'écriture pour `CodegraphMcpConnector`. |
| `tests/unit/connectors/test_connectors_coverage_suite.py` | Création (`387` l.) | Suite de couverture permettant d'atteindre `>= 90%` sur le paquet `orcia_connectors`. |

### 3.2 Métriques Chiffrées & Couverture de Tests
- **Couverture `orcia_connectors`** : `90.29%` (seuil `>= 90%` satisfait avec `--cov-fail-under=90`).
- **Tests unitaires Python** : `26 passed` (0 failed, 1 warning bénin `TestClient`).
- **Typage statique Mypy strict** : `Success: no issues found in 314 source files` (`0` warning, `0` erreur).
- **Linter & Formatage Ruff** : `All checks passed!` (`742 files already formatted`).
- **Frontières Architecturales (`lint-imports`)** : `5 kept, 0 broken` (`AD-19 Contracts 1-3, 5` & `AD-20 Contract 4: orcia_core never imports orcia_connectors`).
- **Contrat OpenAPI (`scripts/export_openapi.py --check`)** : `0-diff` validé.
- **Suite TypeScript Turbo (`pnpm turbo run lint typecheck test`)** : `9 successful, 9 total` (15/15 fichiers vitest web passés, 74 tests passés).
- **Site Catalog & Cohérence Manifeste (`pnpm site:sync && pnpm site:check`)** : `[site:check OK] Manifest (116 reports, 26 routes, 99 UI primitives) is in sync.`

### 3.3 Validation des Garde-Fous
- **Règle Fail-Fast** : Aucun échec bloquant répété.
- **Lecture seule absolue** : Rejet systématique de `preview_write` et `execute_write` par `PermissionError("codegraph-mcp is strictly read-only")`.
- **Confinement Espace & Traversal Guard** : Rejet strict des chemins hors workspace, des dépôts non `SOURCE_CODE` ou non activés, et des chemins contenant `..`, `/` ou `\x00` avec plafond strict de 250 lignes.
- **Dérive de graphe (`GRAPH_MOVED_SINCE_RUN_LOCK`)** : Calcul déterministe et injection dans le rapport de revue lors de l'exécution de workflow.
