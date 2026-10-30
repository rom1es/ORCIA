# Rapport d'Implémentation Tech Lead — Story 4.1a : Phase E — Sandbox Bimodale Palier 2 Hors Processus (Conteneur Isolé `gVisor/Rootless`, `< 60 s`, `1024 Mo`, `--network=none`) & Séparation des 5 Rôles de Déploiement (Isolation de `Docling`)

- **Clé de Story** : `4-1a-phase-e-sandbox-bimodale-palier-2-hors-processus-conteneur-i`
- **Action Associée** : `ARCH-P5`
- **Epic** : `Epic 4` — Pipeline Tri-Modal des Gates, Validation Cognitive par Découpage & Écosystème d'Exécution (Actions Jira, Sandbox & MCP IDE)
- **Date** : `2026-10-30`
- **Auteur** : Tech Lead / Dev Senior (`Amelia`, `Sophie` & `Karim`)
- **Statut** : `done`
- **Références Architecture & UX** : `FR-17`, `FR-29`, `AD-9`, `AD-18`, `AD-19`, `P5`, `M8`, `M9`, `Q3: 3A`, `Q5`

---

## 1. Analyse du Besoin & Étude d'Impact Tech Lead (Avant Implémentation)

### 1.1 Contexte & Problématique Métier / Technique
La Sandbox Palier 1 (`TIER_1_WASM`, `< 5 000 ms`, `256 MB`, livrée en `Story 4.1`) est idéale pour les validations déterministes pures (schémas JSON/YAML, axiomes d'ontologie, détection statique de *Pattern Drift*). En revanche, l'exécution de suites de tests unitaires (`pytest`, `vitest`), de vérificateurs de types (`mypy`, `tsc`) ou de linters (`ruff`) dans le cadre des Gates Déterministes lourdes et de la boucle fermée d'auto-remédiation TDD (`Red -> Green`, `UJ-12`) nécessite un budget de temps et de mémoire supérieur (`< 60 s`, `1 024 MB`) ainsi qu'un environnement d'exécution POSIX complet isolé sans réseau (`--network=none`) et sans dépendance aux `user namespaces` Linux hôtes sur Kubernetes (`bubblewrap`).

Parallèlement, l'analyse de modularité (`M9`, `AD-19`) a mis en évidence que le chargement de `Docling 2.91.0` (et de ses modèles de vision/layout PDF) dans le même processus que l'API FastAPI ou le worker d'orchestration `DBOS Transact` risque de dégrader la latence temps réel (`SSE < 500 ms`, transition d'étape `< 1 s`).

La `Story 4.1a` (`ARCH-P5`) résout ces deux problématiques :
1. **Sandbox Bimodale Hors Processus (Palier 1 + Palier 2)** :
   - Implémentation de `ContainerSandboxRunner` et `infra/sandbox/tier2_runner.py` pour le Palier 2 (`TIER_2_CONTAINER` : `--network=none`, `--read-only`, `--tmpfs /tmp:rw,noexec,nosuid,size=256m`, `--memory=1024m`, `--cpus=2.0`, `--pids-limit=64`, timeout matériel `< 60 000 ms`, montage CAS en lecture seule), permettant d'exécuter `pytest`, `ruff`, `mypy`, `tsc` et `vitest` et de certifier une séquence TDD `Red` (échec reproduisant le bug avant patch) $\rightarrow$ `Green` (`100 %` de passage après patch).
   - Implémentation de `BimodalSandboxAdapter` routant dynamiquement `TIER_1_WASM` vers `SubprocessTier1SandboxAdapter` (`< 5 s / 256 MB`) et `TIER_2_CONTAINER` vers `ContainerSandboxRunner` (`< 60 s / 1 024 MB`).
2. **Séparation des 5 Rôles Opérationnels de Déploiement & Isolation de `Docling`** :
   - Déclaration de l'extra optionnel `orcia-worker[indexing]` dans `apps/worker/pyproject.toml`.
   - Chargement paresseux dans `apps/worker/src/orcia_worker/__init__.py` et création de `apps/worker/src/orcia_worker/roles.py` définissant les 5 rôles (`api`, `worker-orchestration`, `worker-indexing`, `trigger-dispatcher`, `sandbox-runner`).
   - Mise à jour de `infra/docker/docker-compose.yml` avec les 5 rôles de déploiement et ajout du **Contrat 5 `import-linter`** interdisant tout import de `docling` ou `orcia_worker.docling_indexer` depuis `orcia_api`, `orcia_core.orchestration` et `orcia_worker.dbos_workflow_runner`.

### 1.2 Analyse d'Impact GitNexus (Pré-Codage)
- **`gitnexus_context({name: "SubprocessTier1SandboxAdapter", repo: "ORCIA"})` & `gitnexus_impact({target: "SubprocessTier1SandboxAdapter", direction: "upstream", repo: "ORCIA"})`** :
  - Risque `LOW` (`2` fichiers importateurs dans `orcia_core/gates/`). L'introduction de `ContainerSandboxRunner` et `BimodalSandboxAdapter` dans `packages/orcia-core/src/orcia_core/gates/tier2_sandbox.py` étend `SandboxPort` sans casser aucun appelant existant.

### 1.3 Exploration & Chiffres Clés
- **Contraintes d'isolation Palier 2 (`AD-9`, `P5`)** :
  - Arguments conteneur : `--network=none`, `--read-only`, `--tmpfs /tmp:rw,noexec,nosuid,size=256m`, `--memory=1024m`, `--cpus=2.0`, `--pids-limit=64`, `--security-opt=no-new-privileges:true`.
  - Timeout matériel : `60 000 ms` (`exit_code = 124` $\rightarrow$ `UpstreamTimeoutError`).
  - Outils supportés (whitelist d'exécutables autorisés en Palier 2) : `pytest`, `ruff`, `mypy`, `tsc`, `vitest`.

### 1.4 Opportunités de Factorisation (`DRY`) & Dette Technique
- Réutilisation de `classify_sandbox_failure` (`packages/orcia-core/src/orcia_core/gates/sandbox.py`) pour classifier uniformément les timeouts (`124` $\rightarrow$ `UpstreamTimeoutError`) et les violations d'isolation (`126`, `137` $\rightarrow$ `PolicyDeniedError`) sur les Paliers 1 et 2.

---

## 2. Plan d'Implémentation

### 2.1 Packaging Worker, `import-linter` & `docker-compose.yml` (`apps/worker/`, `infra/docker/`, `pyproject.toml`)
- Mise à jour de `apps/worker/pyproject.toml` avec `[project.optional-dependencies] indexing = ["docling>=2.91.0", "tree-sitter>=0.24.0"]`.
- Création de `apps/worker/src/orcia_worker/roles.py` formalisant les 5 rôles (`api`, `worker-orchestration`, `worker-indexing`, `trigger-dispatcher`, `sandbox-runner`) et isolation de `docling_indexer` hors du chargement de `worker-orchestration`.
- Mise à jour de `infra/docker/docker-compose.yml` avec les 5 services applicatifs.
- Ajout du Contrat 5 dans `pyproject.toml` (`AD-19 Contract 5: API and Orchestration never import docling`).

### 2.2 Runner Palier 2 Hors Processus & Vérificateur TDD `Red -> Green` (`infra/sandbox/tier2_runner.py`, `packages/orcia-core/src/orcia_core/gates/tier2_sandbox.py`)
- Création de `infra/sandbox/tier2_runner.py` : runner isolé hors processus pour `TIER_2_CONTAINER` montant le snapshot CAS en lecture seule, copiant l'espace de test dans un `/tmp` éphémère de `256 MB`, bloquant le réseau (`socket` désactivé -> `exit_code 126`), limitant la RAM à `1 024 MB` (`exit_code 137`) et exécutant `pytest`/`ruff`/`mypy`/`tsc`/`vitest` ou un cycle complet TDD `Red -> Green`.
- Création de `packages/orcia-core/src/orcia_core/gates/tier2_sandbox.py` : `ContainerSandboxRunner`, `BimodalSandboxAdapter`, `TddRemediationCheckInput`, `TddRemediationCheckResult`.
- Intégration de `BimodalSandboxAdapter` dans `DeterministicGateService` et `SkillStepExecutor`.

### 2.3 Couche Backend FastAPI & Contrats OpenAPI (`apps/api/`, `packages/api-client/`)
- Ajout de la route `POST /api/v1/gates/sandbox/tier2/tdd-verify` et `GET /api/v1/gates/sandbox/deployment-roles` dans `apps/api/src/orcia_api/routers/gates.py` et `schemas/gates.py`.
- Régénération du SDK OpenAPI 3.1 (`0-diff`).

### 2.4 Tests Unitaires & d'Intégration (`tests/unit/test_story_4_1a_bimodal_sandbox_and_roles.py`)
- Vérification de l'isolation Palier 2 (`--network=none`, `--read-only`, `--tmpfs`, `--memory=1024m`, `--pids-limit=64`, timeout `< 60 s`), de l'exécution réelle `pytest` `Red -> Green` sur un snapshot CAS en lecture seule, des 5 rôles de déploiement et du Contrat 5 `lint-imports` isolant `Docling`.

---

## 3. Bilan des Modifications & Résultats (Post-Implémentation)

### 3.1 Fichiers Créés ou Modifiés

| Fichier | Action | Lignes | Rôle & Responsabilité |
| :--- | :--- | :---: | :--- |
| `infra/sandbox/tier2_runner.py` | Créé | `265` | Runner Palier 2 hors processus (`TIER_2_CONTAINER` : `--network=none` $\rightarrow$ `exit_code 126`, plafond mémoire `1 024 MB` $\rightarrow$ `exit_code 137`, `/tmp` éphémère `256 MB`, outils `pytest`/`ruff`/`mypy`/`tsc`/`vitest`, cycle TDD `Red -> Green` sur snapshot CAS en lecture seule). |
| `packages/orcia-core/src/orcia_core/gates/tier2_sandbox.py` | Créé | `346` | `ContainerSandboxSpec`, `build_tier2_container_cli_args`, `ContainerSandboxRunner`, `BimodalSandboxAdapter`, `TddRemediationCheckInput`/`Result`, et spécification canonique des 5 rôles opérationnels de déploiement (`CANONICAL_DEPLOYMENT_ROLES`, `verify_role_process_isolation`). |
| `apps/worker/src/orcia_worker/roles.py` | Créé | `23` | Point d'entrée des rôles opérationnels côté worker (`api`, `worker-orchestration`, `worker-indexing`, `trigger-dispatcher`, `sandbox-runner`). |
| `apps/worker/src/orcia_worker/__init__.py` | Modifié | `42` | Chargement paresseux (`__getattr__`) de `docling_indexer` afin que les rôles `api`, `worker-orchestration`, `trigger-dispatcher` et `sandbox-runner` ne chargent jamais `Docling` dans `sys.modules`. |
| `apps/worker/pyproject.toml` | Modifié | `27` | Déclaration de l'extra optionnel `[project.optional-dependencies] indexing = ["docling>=2.91.0", "tree-sitter>=0.24.0"]`. |
| `pyproject.toml` | Modifié | `149` | Ajout du **Contrat 5 `import-linter`** (`AD-19 Contract 5: API and Orchestration never import docling (Story 4.1a)`). |
| `infra/docker/docker-compose.yml` | Modifié | `124` | Déclaration des 5 services applicatifs correspondant aux 5 rôles de déploiement (`api`, `worker-orchestration`, `worker-indexing`, `trigger-dispatcher`, `sandbox-runner`). |
| `packages/orcia-core/src/orcia_core/gates/deterministic.py` | Modifié | `265` | Câblage par défaut sur `BimodalSandboxAdapter` et ajout de `verify_tdd_red_green()`. |
| `apps/api/src/orcia_api/schemas/gates.py` | Modifié | `223` | Schémas de transport HTTP/OpenAPI `Tier2TddRemediationVerifyRequest`/`Response` et `DeploymentRoleListResponse`. |
| `apps/api/src/orcia_api/routers/gates.py` | Modifié | `135` | Endpoints `POST /api/v1/gates/sandbox/tier2/tdd-verify` (avec garde `READ_ONLY_OBSERVER`) et `GET /api/v1/gates/sandbox/deployment-roles`. |
| `tests/unit/test_story_4_1a_bimodal_sandbox_and_roles.py` | Créé | `191` | Suite de tests couvrant la Sandbox Bimodale Palier 1/Palier 2, l'isolation réseau/FS/timeout/mémoire, la boucle fermée TDD `Red -> Green` sur snapshot CAS immuable, les 5 rôles de déploiement et l'isolation de `Docling`. |

### 3.2 Validation des 5 Couches de Tests (`AD-17`) & Qualité

- **Couche 1 — Qualité Statique & Frontières Modulaires (`AD-19`)** :
  - `.venv/bin/ruff check .` & `.venv/bin/ruff format --check .` : `0` erreur.
  - `.venv/bin/mypy --strict packages/orcia-kernel packages/orcia-core apps/api apps/worker` : `Success: no issues found in 144 source files`.
  - `.venv/bin/lint-imports` : `5 contracts kept, 0 broken` (incluant le nouveau **Contrat 5** isolant `Docling`).
  - `.venv/bin/python .agent/skills/bmad-architecture/scripts/lint_spine.py` : `0 findings`.
- **Couche 2 — Tests Unitaires & Couverture Globale (`>= 90 %`)** :
  - `.venv/bin/pytest tests/unit/test_story_4_1a_bimodal_sandbox_and_roles.py` : `3 passed`.
  - Couverture globale sur `packages/orcia-kernel` + `packages/orcia-core` : **`91.93 %`** (`>= 90 %` requis), dont **`91 %`** sur `gates/tier2_sandbox.py` et **`98 %`** sur `gates/deterministic.py`.
- **Couche 3 — Intégration Hors Processus & Immuabilité CAS** :
  - Exécution réelle en sous-processus isolé (`infra/sandbox/tier2_runner.py`) de `pytest` et `ruff` sur un snapshot CAS en lecture seule (`0o555`) avec vérification qu'aucun fichier du CAS n'est altéré après le cycle `Red -> Green`.
- **Couche 4 — Contrats OpenAPI 3.1 & Turborepo TypeScript (`0-diff`)** :
  - `.venv/bin/python scripts/export_openapi.py` : SDK `@orcia/api-client` régénéré (`0-diff`).
  - `pnpm turbo run lint typecheck test` : `9/9` tâches réussies.
- **Couche 5 — Analyse de Graphe GitNexus Post-Implémentation** :
  - `gitnexus analyze` + `gitnexus_detect_changes({scope: "all", repo: "ORCIA"})` : graphe à jour et sans régression de frontière.
