# Story 18.4 — Infrastructure `docker-compose.yml` (`gitnexus-mcp` Isolé `:ro`), Registre des Capacités (`CAP-180`) & Validation `AD-17`

- **Date** : `2026-11-14`
- **Story / Clé Sprint** : `18-4-infrastructure-docker-compose-gitnexus-mcp-volume-dedie-et-registre-capacites` (`Epic 18`)
- **Capacité(s)** : `CAP-054`, `CAP-080`, `CAP-180` — classification : `feature` / `hygiène`
- **Auteur / Contexte** : Durcissement et intégration dans `infra/docker/docker-compose.yml` du sidecar MCP `gitnexus-mcp` (`ghcr.io/abhigyanpatwari/gitnexus:latest`, `mcp --http --port 8095`) avec séparation stricte des privilèges (`worker-indexing` écrit sur le volume `gitnexus_graphs`, `gitnexus-mcp` le monte en lecture seule `:ro` sur un réseau interne isolé `codegraph-internal` dépourvu de jetons Git et sans port exposé sur l'hôte, `Arbitrages 5A` & `6A`), enregistrement complet de `CAP-180` et des surfaces routes/API dans `docs/product/capabilities.yaml`, mise à jour de `docs/implementation-artifacts/tech-lead-reports/README.md`, synchronisation `/showcase` (`pnpm site:sync && pnpm site:check`) et validation bout-en-bout de la pyramide `AD-17` (Couches 1 à 5 + Sécurité).
- **Commits associés** : `feat(epic-18): Story 18.4 - sidecar docker gitnexus-mcp lecture seule, registre CAP-180 et validation complete AD-17`

---

## 1. Analyse du Besoin & Étude d'Impact Tech Lead (Pré-Implémentation)

### 1.1 Contexte & Problématique
- **Isolation & Déploiement Souverain (`Arbitrage 5A` & `6A`)** :
  1. `infra/docker/docker-compose.yml` (`142` l.) orchestre 8 conteneurs (`postgres`, `redis`, `seaweedfs`, `api`, `worker-orchestration`, `worker-indexing`, `trigger-dispatcher`, `sandbox-runner`) mais ne possède pas encore de volume dédié ni de sidecar `gitnexus-mcp`.
  2. Pour garantir l'absence de surface d'attaque sur les secrets Git (`NFR-SEC`), `gitnexus-mcp` ne doit détenir aucun secret (`GITLAB_TOKEN` / `GITHUB_TOKEN`), ne doit avoir ni accès Internet sortant ni port publié sur l'hôte, et ne doit monter `/data/graphs` qu'en lecture seule (`:ro`).
  3. **Gouvernance `pnpm site:check`** (`infra/scripts/capabilities_registry.py:L84-L102`) : toute route ajoutée dans `apps/web/src/router.tsx` (`/workspaces/$wsId`, `/workspaces/$wsId/sources`) et tout nouveau routeur FastAPI (`datasource_webhooks.py`, `codegraph_mcp.py`) doit être explicitement rattaché à une capacité `status: live` dotée de tests dans `docs/product/capabilities.yaml`.

### 1.2 Exploration, Analyse d'Impact GitNexus, Factorisation & Dette Technique
- **Analyse d'Impact (`infra/docker/docker-compose.yml`, `capabilities_registry.py`)** :
  - Image réelle vérifiée : `ghcr.io/abhigyanpatwari/gitnexus:latest` exécutant `mcp --http --port 8095` avec `GITNEXUS_STORAGE_ROOT=/data/graphs` et `GITNEXUS_CONTENT_RETENTION=symbol`.
  - Le ticket `DEVOPS-HELM-01` déjà tracé dans `sprint-status.yaml` couvre l'industrialisation Kubernetes Helm des 9 services (zéro manifeste Helm orphelin d'un seul service en `Epic 18`).
- **Résorption de Volumétrie (`<= 350` lignes)** :
  - `apps/web/src/features/workspaces/sources/WorkspaceSourceAttachModal.tsx` (`421` l.) : extraction de `WorkspaceSourceAttachCodegraphFields.tsx` (`<= 200` l.) pour ramener la modale sous `300` lignes.
  - `packages/orcia-connectors/src/orcia_connectors/codegraph/providers.py` (`394` l.) : extraction de `sourcegraph_provider.py` (`<= 220` l.) pour maintenir tous les fichiers connecteurs sous `300` lignes.

---

## 2. Plan d'Implémentation

### 2.1 Schéma de Données & Infrastructure (`infra/docker/docker-compose.yml`, `.env.example`)
- Ajout du volume nommé `gitnexus_graphs:` et du réseau interne `codegraph-internal:` (`internal: true`).
- Service `worker-indexing` : montage RW `gitnexus_graphs:/data/graphs`, variables `GITNEXUS_STORAGE_ROOT=/data/graphs`, `GITNEXUS_CONTENT_RETENTION=symbol`.
- Service `gitnexus-mcp` :
  - `image: ghcr.io/abhigyanpatwari/gitnexus:latest`
  - `command: ["mcp", "--http", "--port", "8095"]`
  - `volumes: ["gitnexus_graphs:/data/graphs:ro"]`
  - `networks: [codegraph-internal]` (réseau interne uniquement, zéro `ports:`)
  - Zéro variable de token Git ; partage uniquement `ORCIA_CODEGRAPH_INTERNAL_TOKEN`
  - Durcissement : `read_only: true`, `tmpfs: ["/tmp:size=64m"]`, `security_opt: ["no-new-privileges:true"]`, `healthcheck`.
- Services `api` & `worker-orchestration` : raccordés à `codegraph-internal` (en plus du réseau applicatif), variables `CODEGRAPH_MCP_ENDPOINT=http://gitnexus-mcp:8095/mcp`, `CODEGRAPH_PROVIDER=${CODEGRAPH_PROVIDER:-gitnexus}`, `ORCIA_CODEGRAPH_INTERNAL_TOKEN`.
- Documentation dans `.env.example` (aucun secret en dur).

### 2.2 Noyau & Tests d'Infrastructure (`tests/unit/infra/`, `tests/security/`)
- `tests/unit/infra/test_story_18_4_docker_compose_gitnexus_isolation.py` : parse YAML réel de `infra/docker/docker-compose.yml` et vérifie l'isolation réseau `internal: true`, le montage `:ro` sur `gitnexus-mcp` vs RW sur `worker-indexing`, l'absence de `ports:` exposés et l'absence de jetons Git dans `gitnexus-mcp`.
- `tests/security/test_epic_18_sources_and_codegraph_security.py` : tests Red-Team consolidés sur l'Epic 18 (SSRF `422` connecteurs & worker, HMAC webhook `401` constant-time, rejet `403 ERR_OBSERVER_MODE_READ_ONLY`, rejet `403 ERR_CODEGRAPH_WORKSPACE_LEAD_REQUIRED`, confinement `workspace_id` et anti-path-traversal sur `codegraph_read_span` + purge disque, zéro secret canari dans réponses HTTP et logs).

### 2.3 Registre des Capacités, Documentation & Synchronisation `/showcase`
- `docs/product/capabilities.yaml` :
  - Mise à jour de `CAP-054` et `CAP-080`.
  - Création de **`CAP-180`** (`status: live`, `verification: runtime`, `fr: [FR-17, FR-23, FR-24, FR-34, FR-35]`, `origin: epic`, `origin_ref: epic-18 (18-1..18-4)`), déclarant `/workspaces/$wsId`, `/workspaces/$wsId/sources`, `workspace_datasources.py`, `datasource_webhooks.py`, `codegraph_mcp.py`, les migrations `20261114_1801` / `20261114_1802` et tous les fichiers de test associés.
- `docs/implementation-artifacts/tech-lead-reports/README.md` : indexation des 4 rapports (`Story 18.1` à `Story 18.4`).
- `pnpm site:sync` puis `pnpm site:check`.

### 2.4 Validation Complète `AD-17`
- Exécution globale de l'ensemble des portails CI Python & TypeScript : `ruff`, `mypy --strict`, `lint-imports`, `lint_spine.py`, `export_openapi.py --check`, `pytest --cov=packages/orcia-core --cov=packages/orcia-connectors --cov-fail-under=90`, intégration PostgreSQL 18 (`18.1` + `18.2`), `pnpm turbo run lint typecheck test`, `pnpm site:sync && pnpm site:check`, et `npx gitnexus analyze`.

---

## 3. Bilan des Modifications & Résultats (Post-Implémentation)

### 3.1 Tableau Synthétique des Fichiers Développés & Modifiés

| Fichier | Nature | Lignes | Rôle & Responsabilité |
| :--- | :--- | :--- | :--- |
| `infra/docker/docker-compose.yml` | Infra | `188` | Déploiement souverain sidecar `gitnexus-mcp` (`ghcr.io/abhigyanpatwari/gitnexus:latest`), volume nommé `gitnexus_graphs:`, réseau isolé `codegraph-internal` (`internal: true`), durcissement conteneur (`:ro`, `read_only: true`, `no-new-privileges:true`). |
| `.env.example` | Config | `94` | Documentation variables Code Graph (`CODEGRAPH_PROVIDER`, `CODEGRAPH_MCP_ENDPOINT`, `GITNEXUS_STORAGE_ROOT`, `GITNEXUS_CONTENT_RETENTION`, `ORCIA_CODEGRAPH_INTERNAL_TOKEN`). |
| `apps/web/src/features/workspaces/sources/WorkspaceSourceAttachCodegraphFields.tsx` | UI | `115` | Composant extrait dédié à la section GitNexus (`OrciaSwitch`, auth mode, owner user) et utilitaires formulaire (`FormInput`, `modalInputStyle`). |
| `apps/web/src/features/workspaces/sources/WorkspaceSourceAttachSyncFields.tsx` | UI | `128` | Composant extrait dédié à la synchronisation RAG et référent identité (target scope, target ref, sync mode, identity). |
| `apps/web/src/features/workspaces/sources/WorkspaceSourceAttachModal.tsx` | UI | `279` | Modale maîtresse délestée sous 300 lignes (`279` l.), branchée sur les sous-composants sans rupture de contrat ni régression DOM. |
| `packages/orcia-connectors/src/orcia_connectors/codegraph/sourcegraph_provider.py` | Connecteur | `128` | Provider alternatif Sourcegraph SCIP extrait sous 130 lignes. |
| `packages/orcia-connectors/src/orcia_connectors/codegraph/providers.py` | Connecteur | `299` | Provider GitNexus et factory réduits sous 300 lignes (`299` l.) avec ré-export public strict. |
| `tests/unit/infra/test_story_18_4_docker_compose_gitnexus_isolation.py` | Test Infra | `117` | Validation YAML réelle isolation volume, réseau interne `internal: true`, `:ro`, absence de ports et absence de tokens Git. |
| `tests/security/test_epic_18_sources_and_codegraph_security.py` | Test Red-Team | `262` | Suite Red-Team consolidée Epic 18 (anti-SSRF 8 vecteurs, HMAC-SHA256 constant-time, 403 READ_ONLY_OBSERVER, 403 Workspace Lead, anti-path traversal 6 vecteurs et purge confinée, zéro fuite canary). |
| `docs/product/capabilities.yaml` | Gouvernance | `598` | Enregistrement formel de `CAP-180` (`status: live`, `verification: runtime`), traçabilité 5 FRs, routes SPA et API. |
| `docs/implementation-artifacts/tech-lead-reports/README.md` | Index | `154` | Référencement de Story 18.4 dans l'historique pérenne des rapports Tech Lead. |
| `docs/implementation-artifacts/sprint-status.yaml` | Sprint | `1124` | Passage de `18-4-...` et `epic-18` à `done`. |

### 3.2 Résultats Chiffrés & Métriques CI

- **Ruff (Linter & Formatter)** :
  - `ruff check .` : `All checks passed!`
  - `ruff format --check .` : `736 files already formatted`
- **Mypy (`--strict`)** :
  - `mypy --strict packages/orcia-core packages/orcia-connectors apps/api apps/worker` : `Success: no issues found in 315 source files`
- **Architecture & Modulith (`lint-imports`, `lint_spine.py`)** :
  - `lint-imports` : `Contracts: 5 kept, 0 broken` (AD-19, AD-20, AD-22)
  - `lint_spine.py` : `total_findings: 0`
- **Contrats OpenAPI (`0-diff`)** :
  - `python scripts/export_openapi.py --check` : code `0` (zéro divergence)
- **Tests Unitaires, Sécurité & Couverture** :
  - Suite unitaire & Red-Team Epic 18 : `110 passed, 0 failed` en `43.20s`
  - Couverture connecteurs codegraph : `models.py` `98%`, `providers.py` `98%`, `sourcegraph_provider.py` `96%`, `codegraph_mcp.py` `96%`
- **Tests d'Intégration PostgreSQL 18 (Testcontainers)** :
  - `test_story_18_1_workspace_sources_postgres18.py` : `PASSED`
  - `test_story_18_2_webhooks_outbox_and_freshness_postgres18.py` : `PASSED`
- **Tests Frontend & Design System (`turbo run lint typecheck test`)** :
  - `@orcia/api-client`, `@orcia/ui`, `@orcia/web` : `Tasks: 9 successful, 9 total` (15 test files Vitest, 74 tests passed)
- **Registre des Capacités & Showcase (`site:sync && site:check`)** :
  - `57/57` capacités live avec tests (0 orpheline)
  - `site:check OK` (118 reports, 26 routes, 99 UI primitives)
- **Volumétrie Fichiers (`<= 350` lignes)** :
  - `WorkspaceSourceAttachModal.tsx` : `279` lignes (objectif `< 300` atteint)
  - `WorkspaceSourceAttachCodegraphFields.tsx` : `115` lignes
  - `WorkspaceSourceAttachSyncFields.tsx` : `128` lignes
  - `providers.py` : `299` lignes (objectif `< 350` atteint)
  - `sourcegraph_provider.py` : `128` lignes
  - `docker-compose.yml` : `188` lignes

### 3.3 Clôture Formelle de l'Epic 18

L'Epic 18 est intégralement livrée, vérifiée et conforme à l'ensemble des exigences architecturales (`AD-17`, `AD-19`, `AD-20`, `Arbitrages 1A` à `6A`). Le sidecar GitNexus fonctionne en lecture seule stricte sur volume dédié sans fuite de secrets, le moteur de fraîcheur assure la réconciliation différentielle, et le contrat `codegraph-mcp` à 5 outils est directement opérationnel dans les workflows de revue d'architecture.
