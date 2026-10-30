# Spécification d'Implémentation — Story 4.1a : Phase E — Sandbox Bimodale Palier 2 Hors Processus (`gVisor/Rootless < 60 s / 1024 Mo / --network=none`) & Séparation des 5 Rôles de Déploiement (Isolation de `Docling`)

- **Clé de Story** : `4-1a-phase-e-sandbox-bimodale-palier-2-hors-processus-conteneur-i`
- **Epic** : `Epic 4` — Pipeline Tri-Modal des Gates, Validation Cognitive par Découpage & Écosystème d'Exécution
- **Actions Associées** : `ARCH-P5`
- **Statut** : `done`
- **Références** : `FR-17`, `FR-29`, `AD-9`, `AD-18`, `AD-19`, `P5`, `M8`, `M9`, `Q3: 3A`, `Q5`

---

## 1. Objectif & Périmètre

1. **Sandbox Hors Processus Palier 2 (`TIER_2_CONTAINER`, `ContainerSandboxRunner` & `BimodalSandboxAdapter`, `infra/sandbox/tier2_runner.py`)** :
   - Complète la Sandbox Palier 1 (`TIER_1_WASM`, `< 5 000 ms`, `256 MB`) par un runner Palier 2 hors processus (`TIER_2_CONTAINER`, `< 60 000 ms`, `1 024 MB`, `--network=none`, `--read-only`, `--tmpfs /tmp:rw,noexec,nosuid,size=256m`, `--cpus=2.0`, `--pids-limit=64`, runtime `runsc` gVisor en Kubernetes ou `podman`/`docker` rootless).
   - Monte le snapshot CAS (`SeaweedFS`) en lecture seule et exécute les outils de vérification lourde (`pytest`, `ruff`, `mypy`, `tsc`, `vitest`) nécessaires aux boucles TDD d'auto-remédiation (`Red -> Green`, `UJ-12`).
   - Vérifie formellement le cycle TDD (`Red` : le test reproduisant le bug échoue avant correctif avec `exit_code != 0` ; `Green` : le test passe à `100 %` après application du correctif avec `exit_code == 0`).
2. **Séparation des 5 Rôles Opérationnels de Déploiement & Isolation de `Docling` (`M9`, `AD-19`)** :
   - `apps/worker/pyproject.toml` déclare l'extra optionnel `orcia-worker[indexing]` (`docling>=2.91.0`, `tree-sitter>=0.24.0`).
   - `apps/worker/src/orcia_worker/roles.py` formalise et valide les **5 rôles de déploiement** exécutés depuis la même image conteneur :
     1. `api` (FastAPI REST + SSE, sans `Docling`).
     2. `worker-orchestration` (DBOS Transact + Outbox Relay, sans `Docling`).
     3. `worker-indexing` (Dramatiq + `orcia-worker[indexing]` avec `Docling` + `tree-sitter`).
     4. `trigger-dispatcher` (Webhooks, Log Sink, Cron).
     5. `sandbox-runner` (Wasmtime Palier 1 `< 5 s` & Conteneur isolé Palier 2 `< 60 s`).
   - `infra/docker/docker-compose.yml` configure les 5 services applicatifs correspondants.
   - `pyproject.toml` ajoute le **Contrat 5 `import-linter`** (`AD-19 Contract 5: API and Orchestration never import docling`) garantissant que `orcia_api`, `orcia_core.orchestration` et `orcia_worker.dbos_workflow_runner` n'importent jamais `docling` ni `orcia_worker.docling_indexer`.
