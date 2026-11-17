# Story 7.0c — Conformité & Préparation au Déploiement OpenShift (Dockerfiles Non-Root, Kustomize SCC Restricted, FS Read-Only, Sonde `/ready` & Contrat `ClusterLogForwarder`)

- **Date** : 2026-11-17
- **Story / Clé Sprint** : `7-0c-conformite-deploiement-openshift-et-clusterlogforwarder` (`Epic 7` / Socle d'Observabilité & Déploiement OpenShift)
- **Capacité(s)** : `CAP-202` — classification : `feature`
- **Auteur / Contexte** : Préparation et mise en conformité des conteneurs et manifestes ORCIA pour un déploiement en production sur plateforme OpenShift SCC `restricted` (`FR-28`, `NFR-SEC-1`, `NFR-OBS-1`, `AD-9`, `AD-12`, `AD-19`, `AD-23`, Décision `D6`/`D8`).
- **Commits associés** : *(en cours — géré par l'orchestrateur après validation)*

---

## 1. Analyse du Besoin & Étude d'Impact Tech Lead (Pré-Implémentation)

### 1.1 Contexte & Problématique
- **Situation actuelle** :
  - `apps/api/src/orcia_api/routers/health.py` expose uniquement `GET /api/v1/health` (`livenessProbe`), sans route `GET /ready` ni `GET /api/v1/ready` (`readinessProbe`).
  - Dans `packages/orcia-core/src/orcia_core/observability/_internal/ecs_formatter.py`, `HealthProbeLogFilter` filtre `/api/v1/health` et `/ready`, mais pas encore `/api/v1/ready`.
  - `apps/worker/src/orcia_worker/roles.py` vérifie uniquement l'isolation des modules (`verify_role_process_isolation`) puis sort avec le code `0`, sans démon HTTP/async interne réel pour `sandbox-runner` ni boucle de service `--serve` pour `worker-orchestration` / `trigger-dispatcher`.
  - Le dépôt ne contient pas encore `infra/docker/Dockerfile`, `infra/docker/Dockerfile.web`, les manifestes Kustomize `infra/k8s/base/` + `infra/k8s/overlays/openshift/`, ni le contrat d'intégration plateforme `docs/operations/openshift-clusterlogforwarder-contract.md`.
- **Comportement attendu** :
  - Sonde `GET /ready` (à la racine) et `GET /api/v1/ready` répondant en `< 100 ms` sans aucune requête SQL lourde (`status: "ready"`, `version`, `trace_id`, vérification légère d'initialisation de `app.state`), filtrée en statut `< 400` par `HealthProbeLogFilter`, avec schéma OpenAPI 3.1 + SDK `@orcia/api-client` régénérés (`0-diff`).
  - Sidecar / pod interne `sandbox-runner` (`apps/worker/src/orcia_worker/sandbox_daemon.py` + `roles.py --role sandbox-runner --serve`) fonctionnant en serveur HTTP async sur `ORCIA_SANDBOX_HOST:ORCIA_SANDBOX_PORT` (`8096`), exécutant `tier1_runner.py` en sous-processus isolé `-I` avec écritures exclusives sous `/tmp`, zéro `podman`/`docker` imbriqué (`AD-9`), jeton interne optionnel en temps constant (`X-Orcia-Sandbox-Token`), et politique réseau `egress: []`.
  - Dockerfiles non-root compatibles UID arbitraire OpenShift (`chgrp -R 0 && chmod -R g=u`, `USER 10001:0` Python et `nginxinc/nginx-unprivileged:1.27-alpine` `101:0` sur port `8080` pour le front Vite) et durcissement des services `app-roles` dans `infra/docker/docker-compose.yml` (`read_only: true`, `no-new-privileges:true`, `tmpfs /tmp`).
  - Manifestes Kustomize `infra/k8s/base/` + `infra/k8s/overlays/openshift/` respectant OpenShift SCC `restricted` (absence stricte de `runAsUser`/`fsGroup` figés dans l'overlay, `runAsNonRoot: true`, `allowPrivilegeEscalation: false`, `readOnlyRootFilesystem: true`, `capabilities.drop: ["ALL"]`, `emptyDir` sur `/tmp`, `NetworkPolicy` isolée sur `sandbox-runner`, `Route` TLS Edge) et document contractuel `docs/operations/openshift-clusterlogforwarder-contract.md` (`OPS-OPENSHIFT-LOGGING-01`).

### 1.2 Exploration, Analyse d'Impact GitNexus, Factorisation & Dette Technique
- **Analyse d'Impact GitNexus (`gitnexus_context`, `gitnexus_impact` sur `repo: "/home/romain/Documents/Projects/ORCIA"`)** :
  - `apps/api/src/orcia_api/routers/health.py:get_health` : `impactedCount = 0` (`epistemic: exact` côté graphe Python ; monté dans `apps/api/src/orcia_api/main.py` via `health_router` et consommé via HTTP par `packages/api-client/src/domains/authAndShell.ts`, `apps/web/playwright.config.ts`, `apps/web/e2e/00-stack-smoke.spec.ts` et les tests unitaires). Ajouter `GET /ready` et `GET /api/v1/ready` via un second `APIRouter` dans `health.py` préserve `100 %` de rétrocompatibilité sur `/api/v1/health`.
  - `apps/worker/src/orcia_worker/roles.py:main` : `impactedCount = 2` (`risk: LOW`, `direct: 1` dans `roles.py`, `depth 2` dans `apps/worker/src/orcia_worker/__init__.py`). Les tests `tests/unit/test_story_4_1a_bimodal_sandbox_and_roles.py` et `tests/unit/test_story_7_0a_unified_ecs_logging_and_masking.py` invoquent `roles.main(["--role", ...])` sans `--serve` et attendent un retour immédiat `0`. L'introduction d'un flag explicite `--serve` (plus `--once`) garantit zéro régression des tests existants tout en permettant l'exécution réelle du démon en conteneur.
  - `packages/orcia-core/src/orcia_core/observability/_internal/ecs_formatter.py:HealthProbeLogFilter` : `impactedCount = 51` (`risk: MEDIUM`, `direct: 3` : `logging.py`, `tracing.py`, `elasticsearch_sink.py`). L'extension de `_HEALTH_PROBE_PATH_RE` pour inclure `/api/v1/ready` en plus de `/api/v1/health` et `/ready` n'altère aucune signature publique et préserve tous les appels existants.
- **Exploration & Chiffres Clés** :
  - Absence de `uv.lock` à la racine du dépôt : `infra/docker/Dockerfile` ne doit pas utiliser `COPY uv.lock` ni `uv sync --frozen`, mais installer le workspace via `uv sync --no-dev` (et copier `pyproject.toml`, `packages/`, `apps/`, `infra/sandbox/`, `scripts/`).
  - Taille des fichiers modifiés maintenue bien en deçà du seuil `300–400` lignes (`health.py < 120` l., `roles.py < 220` l., `sandbox_daemon.py < 240` l.).
  - Vérification `capabilities_registry.py` : `health` figure dans `coverage_exemptions` de `docs/product/capabilities.yaml` ; conserver les sondes dans `routers/health.py` évite d'introduire un routeur non couvert.
- **Opportunités de Factorisation & Résorption de Dette Technique** :
  - Factoriser la construction de la réponse de readiness dans une fonction `_build_readiness_response(request)` partagée entre `/ready` et `/api/v1/ready`.
  - Réutiliser `infra/sandbox/tier1_runner.py` depuis `sandbox_daemon.py` via `sys.executable -I` (zéro duplication de la logique de jail réseau/système de fichiers Tier 1).
  - Réutiliser `configure_logging`, `configure_tracing` et `instrument_runtime` dans `roles.py` pour tous les rôles `--serve`.

---

## 2. Plan d'Implémentation

### 2.1 Schéma de Données & Migrations Alembic (`infra/migrations/versions/`)
- Aucune modification de schéma PostgreSQL ni migration Alembic requise pour la Story 7.0c (la sonde `/ready` n'exécute aucune requête SQL lourde et les livrables relèvent de l'API santé, du sidecar sandbox, de la conteneurisation et de Kustomize).

### 2.2 Noyau Métier Hexagonal, Orchestration & Workers (`packages/orcia-core/`, `apps/worker/`, `infra/sandbox/`, `infra/docker/`, `infra/k8s/`, `docs/operations/`)
- `packages/orcia-core/src/orcia_core/observability/_internal/ecs_formatter.py` :
  - Étendre `_HEALTH_PROBE_PATH_RE` pour filtrer `/api/v1/health`, `/ready` et `/api/v1/ready` lorsque le statut HTTP est `< 400` et le niveau `< WARNING`.
- `apps/worker/src/orcia_worker/sandbox_daemon.py` (`< 240` lignes) :
  - Serveur HTTP/1.1 asynchrone `asyncio.start_server` sur `ORCIA_SANDBOX_HOST:ORCIA_SANDBOX_PORT` (`0.0.0.0:8096`).
  - `GET /health` -> `200 {"status": "ok", "role": "sandbox-runner"}`.
  - `POST /execute-tier1` -> contrôle temps-constant (`hmac.compare_digest`) sur `X-Orcia-Sandbox-Token` si `ORCIA_SANDBOX_INTERNAL_TOKEN` est défini (`401`/`403` sinon), répertoire scratch éphémère exclusivement sous `/tmp` (`ORCIA_SANDBOX_TMP_DIR`), exécution isolée `python -I infra/sandbox/tier1_runner.py` bornée (`<= 5 s`), nettoyage garanti du répertoire temporaire, zéro `podman`/`docker` imbriqué (`AD-9`).
- `apps/worker/src/orcia_worker/roles.py` (`< 220` lignes) :
  - Ajout des options `--serve`, `--once`, `--host`, `--port` : mode vérification immédiate conservé par défaut pour rétrocompatibilité des tests `Story 4.1a` / `Story 7.0a`, mode `--serve` démarrant la boucle réelle pour `sandbox-runner` (`serve_sandbox_daemon`), `worker-orchestration` (boucle durable/outbox avec arrêt propre `SIGINT`/`SIGTERM`) et `trigger-dispatcher` (boucle prête pour `Story 7.2`).
- `infra/docker/Dockerfile`, `infra/docker/Dockerfile.web`, `infra/docker/docker-compose.yml` :
  - `Dockerfile` Python multi-rôles non-root (`python:3.12-slim` + `uv`, `chgrp -R 0 /app && chmod -R g=u /app`, `HOME=/tmp`, `USER 10001:0`, `--no-access-log`).
  - `Dockerfile.web` multi-stage (`node:24-alpine` + `pnpm` -> `nginxinc/nginx-unprivileged:1.27-alpine` `USER 101:0`, port `8080`, pid/temp nginx sous `/tmp` pour `readOnlyRootFilesystem: true`).
  - `docker-compose.yml` : durcissement des 5 services `app-roles` (`user: "10001:0"`, `read_only: true`, `no-new-privileges:true`, `tmpfs` `/tmp`, `--serve` sur les rôles workers).
- `infra/k8s/base/` & `infra/k8s/overlays/openshift/` & `docs/operations/openshift-clusterlogforwarder-contract.md` :
  - Base Kustomize complète (`kustomization.yaml`, `configmap.yaml`, `secret-template.yaml` sans secret en dur, `deployment-*.yaml`, `service-*.yaml`, `networkpolicy-sandbox-runner.yaml` avec `egress: []` et `networkpolicy-runtime-egress.yaml`).
  - Overlay OpenShift (`kustomization.yaml`, `patch-scc-*.yaml` sans aucun `runAsUser`/`fsGroup` figé, `route-web.yaml` & `route-api.yaml` TLS Edge, annotations/labels).
  - Contrat `OPS-OPENSHIFT-LOGGING-01` consignant les 4 engagements `AD-23.8`.

### 2.3 Couche Backend API, Sécurité & Contrats (`apps/api/`, `packages/api-client/`)
- `apps/api/src/orcia_api/schemas/shell.py` : ajout de `ReadinessResponse`.
- `apps/api/src/orcia_api/routers/health.py` & `apps/api/src/orcia_api/main.py` : exposition de `GET /ready` (racine) et `GET /api/v1/ready` (`< 100 ms`, zéro SQL, `trace_id`, contrôle léger `app.state`, `503` Problem Details si non initialisé).
- `packages/api-client/` : régénération déterministe via `.venv/bin/python scripts/export_openapi.py` + vérification `--check` (`0-diff`).

### 2.4 Interface Utilisateur & Expérience (`apps/web/`)
- Aucune route ou composant React/UI modifié (`Dockerfile.web` + configuration Nginx non-root pour servir le bundle statique `apps/web/dist` sur port `8080`).

### 2.5 Analyse d'Impact sur la Pyramide des Tests (`AD-17`)
- **Couche 1a (Unitaires Python `tests/unit/`)** :
  - `tests/unit/test_story_7_0c_openshift_scc_kustomize_and_ready.py` : tests de `GET /ready` et `GET /api/v1/ready` (`200`, `< 100 ms`, `503` si `app.state` non initialisé, filtrage `HealthProbeLogFilter`), tests réels de `sandbox_daemon.py` sur `127.0.0.1:0` (auth token `401`/`403`/`200`, isolation `/tmp`, nettoyage, `roles.py --serve --once`), et validation structurelle complète des Dockerfiles, `docker-compose.yml`, manifestes YAML Kustomize (`base` + `overlays/openshift`) et contrat `ClusterLogForwarder`.
  - Enrichissement de `tests/unit/test_story_7_0a_unified_ecs_logging_and_masking.py` pour couvrir `/api/v1/ready` dans `HealthProbeLogFilter`.
- **Couche 3 (Contrats OpenAPI 3.1 `0-diff` & `lint-imports`)** : `scripts/export_openapi.py --check`, `lint-imports` (`5 contracts kept, 0 broken`), `tests/contract/`.
- **Couche Sécurité (`tests/security/`)** : non-régression `detect-secrets` sur `secret-template.yaml` et fixtures, validation non-root / `readOnlyRootFilesystem` / `capabilities.drop: ALL` / `egress: []`.

---

## 3. Bilan des Modifications & Résultats (Post-Implémentation)

### 3.1 Fichiers Développés & Modifiés
| Fichier | Nature (Création / Modification / Refactoring) | Description synthétique |
| :--- | :--- | :--- |
| `apps/api/src/orcia_api/schemas/shell.py` | Modification | Ajout du schéma `ReadinessResponse` (`status`, `version`, `trace_id`, `initialized`). |
| `apps/api/src/orcia_api/routers/health.py` | Modification | Exposition de `GET /ready` (`probe_router`) et `GET /api/v1/ready` (`< 100 ms`, zéro SQL, `503 ERR_API_NOT_READY` RFC 9457 si non initialisé). |
| `apps/api/src/orcia_api/main.py` | Modification | Montage de `health_probe_router` pour exposer `/ready` à la racine. |
| `packages/orcia-core/src/orcia_core/observability/_internal/ecs_formatter.py` | Modification | Extension de `HealthProbeLogFilter` pour filtrer `/api/v1/health`, `/ready` et `/api/v1/ready` en réponse `< 400`. |
| `apps/worker/src/orcia_worker/sandbox_daemon.py` | Création | Démon HTTP/1.1 async interne (`GET /health`, `POST /execute-tier1`) exécutant `tier1_runner.py` sous `python -I` et `/tmp` sans Podman-in-Pod (`271` l.). |
| `apps/worker/src/orcia_worker/roles.py` | Modification | Support `--serve`, `--once`, `--host`, `--port` pour `sandbox-runner`, `worker-orchestration` et `trigger-dispatcher` (`108` l.). |
| `infra/docker/Dockerfile` | Création | Image Python 3.12 non-root (`USER 10001:0`, `uv sync --no-dev`, `chgrp -R 0 /app && chmod -R g=u /app`, `HOME=/tmp`, `--no-access-log`). |
| `infra/docker/Dockerfile.web` & `infra/docker/nginx.conf` | Création | Build multi-stage Vite 6 + `nginxinc/nginx-unprivileged:1.27-alpine` (`USER 101:0`, port `8080`, `pid` et caches sous `/tmp`). |
| `infra/docker/docker-compose.yml` | Modification | Durcissement des 5 services `app-roles` (`user: "10001:0"`, `read_only: true`, `no-new-privileges:true`, `tmpfs /tmp`, `--serve`). |
| `infra/k8s/base/*` | Création | Base Kustomize mono-document (`kustomization.yaml`, `configmap.yaml`, `secret-template.yaml`, 6 `deployment-*.yaml`, 3 `service-*.yaml`, `networkpolicy-sandbox-runner.yaml` `egress: []`, `networkpolicy-runtime-egress.yaml`). |
| `infra/k8s/overlays/openshift/*` | Création | Overlay OpenShift SCC `restricted` mono-document (`kustomization.yaml`, 6 `patch-scc-*.yaml` sans `runAsUser`/`fsGroup` figés, `route-web.yaml` & `route-api.yaml` TLS Edge). |
| `docs/operations/openshift-clusterlogforwarder-contract.md` | Création | Contrat plateforme `OPS-OPENSHIFT-LOGGING-01` consignant les 4 engagements `AD-23.8`. |
| `packages/api-client/openapi.json`, `src/generated/schema.ts`, `src/generated/shell.ts` | Régénération | SDK OpenAPI 3.1 régénéré (`0-diff` vérifié par `scripts/export_openapi.py --check`). |
| `tests/unit/test_story_7_0c_openshift_scc_kustomize_and_ready.py` & `tests/unit/test_story_7_0a_unified_ecs_logging_and_masking.py` | Création / Modification | Couverture `/ready`, `/api/v1/ready`, `sandbox_daemon.py`, `roles.py --serve --once`, Dockerfiles, Compose, Kustomize & contrat `ClusterLogForwarder`. |

### 3.2 Résultats Chiffrés, Métriques & Qualité
- **Couverture de tests** : `96.91 %` sur `packages/orcia-core/src/orcia_core/observability` (`639 passed`, `0` échec sur `tests/unit`, `tests/contract`, `tests/conformance`, `tests/security`).
- **Performances mesurées** : Sondes `GET /ready` et `GET /api/v1/ready` vérifiées `< 100 ms` sans requête SQL.
- **Qualité statique & Architecture** :
  - `ruff check .` & `ruff format --check .` : `0 warning / 0 error` (`955` fichiers).
  - `mypy --strict` (`packages/orcia-core`, `packages/orcia-connectors`, `apps/api`, `apps/worker`) : `0 error` (`418` fichiers).
  - `pnpm turbo run lint typecheck test` : `9/9` tâches réussies (`@orcia/api-client`, `@orcia/ui`, `@orcia/web` — `29` fichiers, `128` tests Vitest).
  - `lint-imports` : `5 contracts kept, 0 broken`.
  - `scripts/export_openapi.py --check` : `0-diff`.
  - `lint_spine.py` : `ok: true, 0 findings`.
  - `gitnexus detect-changes --scope all --repo .` : `12 files, 23 symbols`, `Affected processes: 0`, `Risk level: low`.

### 3.3 Validation & Procédure de Test sur Toute la Pyramide (`AD-17`)
- **Couche 1a & 1b — Unitaires Python & TS** : `pytest tests/unit/test_story_7_0c_openshift_scc_kustomize_and_ready.py` (validation sondes `/ready`, `sandbox_daemon.py` sur `127.0.0.1:0`, `--serve --once`, validation structurelle Dockerfiles / Compose / YAML Kustomize / contrat `ClusterLogForwarder`) + `pnpm turbo run lint typecheck test` (`9/9`).
- **Couche 3 — Contrats API & Architecture** : `scripts/export_openapi.py --check` (`0-diff`), `tests/contract/test_openapi_contract.py` (`Schemathesis`), `lint-imports` (`5 kept, 0 broken`), `lint_spine.py` (`0 findings`).
- **Couche Sécurité (`tests/security/` & `detect-secrets`)** : `detect-secrets-hook --baseline .secrets.baseline` (`0` secret en clair dans `secret-template.yaml` et les fixtures de test), vérification `runAsNonRoot: true`, `readOnlyRootFilesystem: true`, `capabilities.drop: ["ALL"]`, `egress: []` sur `sandbox-runner` et absence de `runAsUser`/`fsGroup` figés dans `infra/k8s/overlays/openshift/`.
- **Clôture Registre & Catalogue** : `sprint-status.yaml` (`7-0c-...: done`), `docs/product/capabilities.yaml` (`CAP-202: status: live, verification: runtime`), `pnpm site:sync && pnpm site:check` validés.
