# Story 7.0b — Puits de Logs Paramétrable (`LogSinkQueryPort`), Adaptateur Elasticsearch / OpenSearch Prioritaire, Traces OTel OTLP & Profils Compose

- **Date** : 2026-11-17
- **Story / Clé Sprint** : `7-0b-puits-de-logs-parametrable-logsinkqueryport-traces-otel` (`Epic 7` / Socle d'Observabilité Paramétrable & Traces OTLP)
- **Capacité(s)** : `CAP-202` (existant dans `docs/product/capabilities.yaml`, `partial` après 7.0a → enrichi 7.0b ; reste `partial` jusqu'à 7.0c OpenShift) — classification : `feature` (`AGENTS.md` §5)
- **Auteur / Contexte** : Tech Lead / Senior Dev — Abstraction hexagonale de l'accès en lecture au puits de logs (`LogSinkQueryPort`), adaptateur prioritaire OpenSearch/Elasticsearch sur REST JSON (`ElasticsearchLogSinkAdapter`), calcul déterministe `compute_error_fingerprint_sha256`, traces distribuées OpenTelemetry OTLP (`opentelemetry-sdk`, `opentelemetry-exporter-otlp-proto-http`, instrumentations `fastapi`, `sqlalchemy`, `httpx`), câblage Composition Root API/Worker et profils Docker Compose (`logs-elastic`, `logs-loki`) (`FR-23`, `FR-24`, `FR-29`, `NFR-OBS-1`, `NFR-SEC-4`, `AD-12`, `AD-18`, `AD-19`, `AD-23`).
- **Commits associés** : *(géré par l'orchestrateur parent après validation)*

---

## 1. Analyse du Besoin & Étude d'Impact Tech Lead (Pré-Implémentation)

### 1.1 Contexte & Problématique
- **Comportement actuel** :
  - `Story 7.0a` a posé la journalisation unifiée 12-Factor sur `stdout` (`JSON` 1 ligne aligné ECS via `structlog` + `ProcessorFormatter`, masquage des secrets et propagation du `trace_id`).
  - En revanche, `.venv` ne contient aujourd'hui que `opentelemetry-api==1.45.1` sans `opentelemetry-sdk`, sans exportateur OTLP ni instrumentations automatiques (`fastapi`, `sqlalchemy`, `httpx`). Les logs émis sous `TracerProvider` ne bénéficient pas encore d'export OTLP ni d'auto-instrumentation ASGI/SQL/HTTPX.
  - Il n'existe aucun port hexagonal `LogSinkQueryPort` ni aucun adaptateur pour interroger le puits de logs en lecture (`query_logs`, `count_errors`, `healthcheck`), ce qui bloque l'implémentation de `Story 7.2` (`LOG_SINK_ALERT`) et de `AIOPS-INCIDENT-LOOP-01` (`POST_ACTION_VERIFICATION`).
  - `infra/docker/docker-compose.yml` ne déclare ni les profils optionnels `--profile logs-elastic` / `--profile logs-loki`, ni la rotation Docker `json-file` (`max-size: "50m"`, `max-file: "3"`).
- **Comportement attendu** :
  - Port hexagonal pur `LogSinkQueryPort` + modèles immuables `LogQuery` / `LogEntry` + `NoopLogSinkAdapter` accessibles via `orcia_core.ports.log_sink` (zéro import SDK/framework, conforme Contrat 3 `import-linter`).
  - Calcul d'empreinte d'erreur déterministe `compute_error_fingerprint_sha256(service, exception_type, top_frame) -> "sha256:<64-hex>"` et extraction `extract_top_frame` 100 % côté ORCIA (`AD-23` Invariant 3).
  - Adaptateur prioritaire `ElasticsearchLogSinkAdapter` compatible OpenSearch 2.x et Elasticsearch 8.x via `httpx.AsyncClient` sur REST JSON standard (`/_search`, `/_count`, `/_cluster/health`), protégé par garde-fou SSRF sur l'URL et authentification optionnelle via `SecretRef` / `SecretProviderPort` (zéro fuite de secret, zéro `except Exception:` muet).
  - Traces distribuées OpenTelemetry via `configure_tracing(...)` (`OTEL_TRACES_EXPORTER=otlp|console|none`, `OTEL_EXPORTER_OTLP_ENDPOINT`) et `instrument_runtime(app, engine)` — sans **jamais** instancier de `LoggerProvider` ni `OTLPLogExporter` (`AD-23` Invariant 1), tout en préservant les spans actifs dans `bind_trace_context` et l'injection `trace_id`/`span_id` dans `structlog`.
  - Câblage exclusif au Composition Root (`initialize_app_services` / `app_lifespan` + `get_log_sink_port` dans `apps/api/src/orcia_api/dependencies/`, et initialisation worker dans `apps/worker/`) via `build_log_sink_from_env(...)` (`LOG_SINK_BACKEND=elasticsearch|loki|none`, défaut `none`).
  - Profils Compose `--profile logs-elastic` (`opensearchproject/opensearch:2.19.1` + `grafana/grafana:11.5.1`) et `--profile logs-loki` (`grafana/loki:3.4.1` + `grafana/grafana:11.5.1`) + rotation `json-file` `50m`/`3` sur les services applicatifs.
- **Contraintes `ARCHITECTURE-SPINE.md` (`AD-19`, `AD-23`)** :
  - `orcia_core.ports` et `orcia_core.observability` sont en **couche 5** du Contrat 2 `[tool.importlinter]` (`domain | ports | config | observability | storage`) : ni l'un ni l'autre ne peuvent importer les couches `1..4`, ni s'importer mutuellement entre frères de couche 5. Les primitives pures partagées (`LogQuery`, `LogEntry`, `LogSinkQueryPort`, `NoopLogSinkAdapter`) sont donc placées dans `orcia_core.kernel.log_sink_ports` (couche 6) et ré-exportées proprement par `orcia_core.ports.log_sink` et `orcia_core.ports` (conformément au modèle existant `secret_ports.py` / `ecs_formatter.py` et `ports.py` / `storage/claim_check.py`).
  - Contrat 3 (`orcia_core.kernel`, `orcia_core.domain`, `orcia_core.ports`) : zéro import SDK/framework (`httpx`, `opentelemetry-sdk`, `fastapi`, `sqlalchemy`, etc.).
  - Alignement des versions résolues `opentelemetry-*` dans `ARCHITECTURE-SPINE.md` (`## Stack`) pour garantir `lint_spine.py` = `0 findings`.

### 1.2 Exploration, Analyse d'Impact GitNexus, Factorisation & Dette Technique
- **Analyse d'Impact GitNexus (`gitnexus_context`, `gitnexus_impact`, `gitnexus_query` sur `repo: "/home/romain/Documents/Projects/ORCIA"`)** :
  - `configure_logging` (`packages/orcia-core/src/orcia_core/observability/logging.py:199-271`) : `impactedCount: 2` (`configure_structlog`, `ensure_logging_configured`), risque `LOW` ; toutefois `bind_trace_context` (`logging.py:106-148`) est invoquée par `TraceContextMiddleware` (`apps/api/src/orcia_api/middleware/trace_and_error.py:52`) et les workers (`broker.py`, `outbox_relay.py`, `dbos_workflow_runner.py`, `docling_indexer.py`, `codegraph_indexer.py`, `rag_reindexer.py`).
    - *Découverte critique* : lorsqu'un vrai span OTel `TracerProvider` est actif (`span.is_recording() == True`), `bind_trace_context` attachait un `NonRecordingSpan` par-dessus le span actif et `ecs_formatter._resolve_active_trace_fields` donnait la priorité à `_trace_ctx_var` sur `otel_trace.get_current_span()`. L'ajustement ciblé préserve tout span enregistrant actif dans `otel_context` et résout dynamiquement `trace_id`/`span_id` du span actif tout en conservant `workspace_id`/`run_id`/`step_id`.
  - `app_lifespan` & `initialize_app_services` (`apps/api/src/orcia_api/dependencies/core_and_lifespan.py:118-350`) : Composition Root unique (`apps/api/src/orcia_api/main.py:10,86,94` et ensemble des `dependencies/*.py`). `app.state.http_client` (`httpx.AsyncClient` partagé) y est déjà initialisé en ligne 295 : l'injection de `app.state.log_sink = build_log_sink_from_env(http_client=app.state.http_client)` et le démarrage/arrêt de `configure_tracing` / `instrument_runtime` / `shutdown_tracing` s'y intègrent sans singleton d'import.
  - `configure_broker` (`apps/worker/src/orcia_worker/broker.py:62`) et `roles.py:main` (`apps/worker/src/orcia_worker/roles.py:19`) : points d'entrée d'initialisation des workers où `configure_tracing` doit être appelé de manière idempotente selon `ORCIA_WORKER_ROLE`.
- **Exploration & Chiffres Clés (Environnement & Dépendances)** :
  - Résolution à sec `uv pip install --dry-run` validée : `opentelemetry-sdk==1.45.2`, `opentelemetry-exporter-otlp-proto-http==1.45.2`, `opentelemetry-instrumentation-fastapi==0.66b2`, `opentelemetry-instrumentation-sqlalchemy==0.66b2`, `opentelemetry-instrumentation-httpx==0.66b2`.
  - `logging.py` compte `318` lignes ; la création de fichiers dédiés `< 250` lignes (`kernel/log_sink_ports.py`, `ports/log_sink.py`, `observability/fingerprint.py`, `observability/tracing.py`, `observability/errors.py`, `observability/_internal/url_guard.py`, `observability/_internal/elasticsearch_sink.py`, `observability/log_sink_factory.py`) maintient l'ensemble du sous-système modulaire sous la barre des `330` lignes.
  - Docker est disponible localement (`DOCKER_OK`), permettant l'exécution du test d'intégration réel `testcontainers` avec `opensearchproject/opensearch:2.19.1`.
- **Opportunités de Factorisation & Dette Technique** :
  - Mutualisation du kit de test de contrat `LogSinkContractTestKit` dans `tests/conformance/log_sink_contract_kit.py` pour valider de façon identique `FakeInMemoryLogSinkAdapter` (`tests/unit/fakes/fake_log_sink.py`), `ElasticsearchLogSinkAdapter` (MockTransport et conteneur OpenSearch réel), et ultérieurement `LokiLogSinkAdapter` (`OBS-LOGSINK-LOKI-01`, qui reste en `status: open` P2 dans `sprint-status.yaml`).
  - Garde-fou SSRF réutilisable `is_safe_observability_endpoint_url` / `validate_safe_log_sink_url` dans `observability/_internal/url_guard.py` (zéro duplication dans `elasticsearch_sink.py` et `tracing.py`).

---

## 2. Plan d'Implémentation

### 2.1 Schéma de Données & Migrations Alembic
- Non applicable (`Story 7.0b` ne modifie aucune table PostgreSQL ni migration Alembic).

### 2.2 Noyau Métier Hexagonal, Observabilité & Workers (`packages/orcia-core/`, `apps/worker/`)
- **Dépendances `uv` & `ARCHITECTURE-SPINE.md`** :
  - Déclarer `opentelemetry-sdk`, `opentelemetry-exporter-otlp-proto-http`, `opentelemetry-instrumentation-fastapi`, `opentelemetry-instrumentation-sqlalchemy`, `opentelemetry-instrumentation-httpx` dans `pyproject.toml`, `packages/orcia-core/pyproject.toml`, `apps/api/pyproject.toml`, `apps/worker/pyproject.toml` (plus `httpx>=0.28.0` dans `packages/orcia-core/pyproject.toml`), synchroniser via `uv` et aligner `ARCHITECTURE-SPINE.md` (`## Stack`, `lint_spine.py` = `0 findings`).
- **Port Hexagonal Pur & Erreurs** :
  - `packages/orcia-core/src/orcia_core/kernel/log_sink_ports.py` (`< 160` l.) : dataclasses immuables `LogQuery`, `LogEntry`, protocole `@runtime_checkable LogSinkQueryPort` (`query_logs`, `count_errors`, `healthcheck`) et `NoopLogSinkAdapter`.
  - `packages/orcia-core/src/orcia_core/ports/log_sink.py` (`< 60` l.) et ré-exports dans `ports/__init__.py` et `orcia_kernel/ports.py` (0 import SDK/framework, Contrat 3 respecté).
  - `packages/orcia-core/src/orcia_core/observability/errors.py` (`< 90` l.) : erreurs `UnsafeLogSinkUrlError`, `UnsupportedLogSinkBackendError`, `LogSinkQueryFailedError` héritant de `OrciaDomainError` avec catalogue FR/EN enregistré dans `ERROR_CATALOG`.
- **Empreinte d'Erreur, Garde SSRF & Adaptateur OpenSearch/Elasticsearch** :
  - `packages/orcia-core/src/orcia_core/observability/fingerprint.py` (`< 110` l.) : `extract_top_frame` et `compute_error_fingerprint_sha256(service, exception_type, top_frame) -> "sha256:<64-hex>"`.
  - `packages/orcia-core/src/orcia_core/observability/_internal/url_guard.py` (`< 80` l.) : blocage strict Cloud Metadata (`169.254.0.0/16`, `fe80::/10`, `metadata.google.internal`, `100.100.100.200`, `0.0.0.0`, `::`, `user:pass@`), autorisation `localhost`, `127.0.0.1`, `.local`, `.internal`.
  - `packages/orcia-core/src/orcia_core/observability/_internal/elasticsearch_sink.py` (`< 260` l.) : `ElasticsearchLogSinkAdapter` sur `httpx.AsyncClient` REST JSON standard (`POST /{index}/_search`, `POST /{index}/_count`, `GET /_cluster/health`), auth optionnelle via `SecretRef`/`SecretProviderPort`, logs structurés sur toute erreur réseau/HTTP (0 `except Exception:` muet).
- **Traces OpenTelemetry OTLP & Factory Composition Root** :
  - `packages/orcia-core/src/orcia_core/observability/tracing.py` (`< 220` l.) : `configure_tracing`, `instrument_runtime`, `shutdown_tracing` (zéro `LoggerProvider` / `OTLPLogExporter`).
  - `packages/orcia-core/src/orcia_core/observability/log_sink_factory.py` (`< 90` l.) : `build_log_sink_from_env` (`LOG_SINK_BACKEND=elasticsearch|loki|none`, défaut `none`).
  - `packages/orcia-core/src/orcia_core/observability/logging.py` & `_internal/ecs_formatter.py` : corrélation déterministe avec les spans actifs `TracerProvider` (`trace_id` 32 hex, `span_id` 16 hex) sans écraser un span enregistrant en cours.
- **Workers (`apps/worker/`)** :
  - Initialisation OTel idempotente dans `apps/worker/src/orcia_worker/broker.py` et `roles.py:main`.

### 2.3 Couche Backend API, Sécurité, Contrats & Compose (`apps/api/`, `infra/docker/`)
- `apps/api/src/orcia_api/errors/registry.py` : enregistrement de `UnsafeLogSinkUrlError`, `UnsupportedLogSinkBackendError`, `LogSinkQueryFailedError`.
- `apps/api/src/orcia_api/dependencies/core_and_lifespan.py`, `orchestration_and_settings.py`, `__init__.py` : injection de `app.state.log_sink` dans `initialize_app_services`, cycle de vie `configure_tracing` / `instrument_runtime` / `shutdown_tracing` dans `app_lifespan`, et provider `get_log_sink_port(request)`.
- `infra/docker/docker-compose.yml` : profils optionnels `logs-elastic` (`opensearchproject/opensearch:2.19.1` + `grafana/grafana:11.5.1`) et `logs-loki` (`grafana/loki:3.4.1` + `grafana/grafana:11.5.1`), et bloc `logging: driver: "json-file", options: { max-size: "50m", max-file: "3" }` sur les services applicatifs.
- Aucune modification des routes HTTP publiques ni du SDK TypeScript `@orcia/api-client`.

### 2.4 Interface Utilisateur & Expérience (`apps/web/`)
- Non applicable (`Story 7.0b` concerne exclusivement l'infrastructure d'observabilité backend et Compose).

### 2.5 Analyse d'Impact sur la Pyramide des Tests (`AD-17`)
- **Couche 1a (`tests/unit/`, $\ge 90\%$ sur `orcia_core/observability`)** :
  - `tests/unit/fakes/fake_log_sink.py` : `FakeInMemoryLogSinkAdapter` implémentant `LogSinkQueryPort`.
  - `tests/unit/test_story_7_0b_log_sink_and_otel_tracing.py` : `compute_error_fingerprint_sha256` & `extract_top_frame`, garde SSRF (`169.254.169.254`, `fe80::`, `metadata.google.internal`, `100.100.100.200` vs `.local`/`.internal`/`localhost`), `ElasticsearchLogSinkAdapter` avec `httpx.MockTransport` (`/_search`, `/_count`, `/_cluster/health`, erreurs HTTP/réseau loguées), `build_log_sink_from_env` (`none` / `elasticsearch` / `loki` -> erreur explicite), `configure_tracing` (`none` / `otlp` / `console`), corrélation réelle `TracerProvider` $\rightarrow$ `trace_id`/`span_id` dans le JSON `structlog`, vérification statique `0` `OTLPLogExporter`/`LoggerProvider` (`AD-23` 4 invariants), profils `docker-compose.yml` et provider `get_log_sink_port`.
- **Couche 2 (`tests/integration/test_story_7_0b_opensearch_log_sink_container.py`)** :
  - Exécution du kit `LogSinkContractTestKit` contre un conteneur réel `testcontainers` `opensearchproject/opensearch:2.19.1` avec indexation de logs ECS réels via `httpx`.
- **Couche 3 (`tests/conformance/log_sink_contract_kit.py`, `lint-imports`, `lint_spine.py`)** :
  - `LogSinkContractTestKit` réutilisable validant `FakeInMemoryLogSinkAdapter` et `ElasticsearchLogSinkAdapter`.
  - `lint-imports` (`5 contracts kept, 0 broken`) et `lint_spine.py` (`total_findings == 0`).
- **Couche Sécurité (`tests/security/`)** :
  - Vérification du garde-fou SSRF et de la non-fuite de secret (`SecretRef` / `SecretProviderPort`) dans `ElasticsearchLogSinkAdapter` (avec `# pragma: allowlist secret` sur les fixtures).

---

## 3. Bilan des Modifications & Résultats (Post-Implémentation)

### 3.1 Fichiers Développés & Modifiés
| Fichier | Nature | Description synthétique |
| :--- | :--- | :--- |
| `pyproject.toml`, `packages/orcia-core/pyproject.toml`, `apps/api/pyproject.toml`, `apps/worker/pyproject.toml` | Modification | Déclaration des dépendances OpenTelemetry (`opentelemetry-sdk>=1.45.2`, `opentelemetry-exporter-otlp-proto-http>=1.45.2`, instrumentations `fastapi`, `sqlalchemy`, `httpx` `>=0.66b2`) et `httpx>=0.28.0` dans `orcia-core`. |
| `docs/planning-artifacts/architecture/architecture-ORCIA-2026-10-24/ARCHITECTURE-SPINE.md` | Modification | Alignement `## Stack` sur les versions OTel résolues (`1.45.2` / `0.66b2`). |
| `packages/orcia-core/src/orcia_core/kernel/log_sink_ports.py` & `src/orcia_kernel/log_sink_ports.py` | Création | Contrats purs `LogQuery` (`limit <= 200`), `LogEntry`, `LogSinkQueryPort`, `NoopLogSinkAdapter` (0 import SDK). |
| `packages/orcia-core/src/orcia_core/ports/log_sink.py` & `ports/__init__.py` | Création / Modif. | Façade hexagonale pure `orcia_core.ports.log_sink` conforme Contrat 3 `import-linter`. |
| `packages/orcia-core/src/orcia_core/observability/errors.py` | Création | Erreurs bilingues `UnsafeLogSinkUrlError`, `UnsupportedLogSinkBackendError`, `LogSinkQueryFailedError` (RFC 9457). |
| `packages/orcia-core/src/orcia_core/observability/fingerprint.py` | Création | `extract_top_frame` & `compute_error_fingerprint_sha256` déterministe (`sha256:<64-hex>`). |
| `packages/orcia-core/src/orcia_core/observability/_internal/url_guard.py` | Création | Garde-fou anti-SSRF partagé (`169.254.0.0/16`, `fe80::/10`, `metadata.google.internal`, `100.100.100.200`). |
| `packages/orcia-core/src/orcia_core/observability/_internal/elasticsearch_sink.py` | Création | `ElasticsearchLogSinkAdapter` REST JSON (`/_search`, `/_count`, `/_cluster/health`) compatible OpenSearch 2.x & Elasticsearch 8.x, auth `SecretRef` sans fuite et logs structurés d'erreur. |
| `packages/orcia-core/src/orcia_core/observability/tracing.py` | Création | `configure_tracing` (`otlp \| console \| none`), `instrument_runtime` (`FastAPI`, `SQLAlchemy`, `HTTPX`), `shutdown_tracing` (0 `LoggerProvider`/`OTLPLogExporter`). |
| `packages/orcia-core/src/orcia_core/observability/log_sink_factory.py` & `observability/__init__.py` | Création / Modif. | `build_log_sink_from_env` (`LOG_SINK_BACKEND=elasticsearch\|none`, rejet explicite `loki` différé P2). |
| `packages/orcia-core/src/orcia_core/observability/logging.py` & `_internal/ecs_formatter.py` | Modification | Préservation des spans actifs `TracerProvider` dans `bind_trace_context` et corrélation `trace_id`/`span_id` dans le JSON ECS. |
| `apps/api/src/orcia_api/errors/registry.py`, `dependencies/core_and_lifespan.py`, `orchestration_and_settings.py`, `__init__.py` | Modification | Câblage Composition Root (`app.state.log_sink`, `get_log_sink_port`, `configure_tracing`, `instrument_runtime`, `shutdown_tracing`) et catalogue RFC 9457. |
| `apps/worker/src/orcia_worker/broker.py` & `roles.py` | Modification | Initialisation idempotente OTel tracing et instrumentation HTTPX au démarrage des workers. |
| `infra/docker/docker-compose.yml` | Modification | Profils `--profile logs-elastic` (`opensearch:2.19.1` + `grafana:11.5.1`), `--profile logs-loki` (`loki:3.4.1` + `grafana:11.5.1`) et rotation `json-file` (`50m`, `3` fichiers). |
| `tests/unit/fakes/fake_log_sink.py`, `tests/conformance/log_sink_contract_kit.py`, `test_log_sink_conformance.py`, `tests/unit/test_story_7_0b_log_sink_and_otel_tracing.py`, `tests/security/test_story_7_0b_log_sink_security.py`, `tests/integration/test_story_7_0b_opensearch_log_sink_container.py` | Création | Fake exclusif en `tests/unit/fakes/`, kit de contrat `LogSinkContractTestKit`, unitaires, sécurité SSRF/secrets et test d'intégration conteneur réel `opensearchproject/opensearch:2.19.1`. |
| `docs/implementation-artifacts/sprint-status.yaml`, `docs/product/capabilities.yaml`, `docs/implementation-artifacts/tech-lead-reports/README.md`, `apps/web/src/generated/orciaSiteManifest.ts`, `docs/site-catalog/index.html`, `dist/orcia-site/index.html` | Modification | Passage de `7-0b` à `done`, enrichissement `CAP-202`, indexation du rapport et synchronisation du catalogue site (`pnpm site:sync`). |

### 3.2 Résultats Chiffrés, Métriques & Qualité
- **Couverture de tests** : `96.91 %` (branches + statements, seuil $\ge 90\%$ atteint : `660` statements, `11` manqués) sur `packages/orcia-core/src/orcia_core/observability` (`632 passed` sur `tests/unit` + `tests/conformance` + `tests/security`), plus `1 passed` sur `tests/integration/test_story_7_0b_opensearch_log_sink_container.py` (`opensearchproject/opensearch:2.19.1`).
- **Qualité statique & Architecture** :
  - `ruff check .` & `ruff format --check .` : `All checks passed!`, `951 files already formatted`
  - `mypy --strict packages/orcia-core packages/orcia-connectors apps/api apps/worker` : `Success: no issues found in 417 source files`
  - `lint-imports` : `Contracts: 5 kept, 0 broken` (`459` fichiers analysés, `3057` dépendances)
  - `lint_spine.py` : `{"ok": true, "total_findings": 0}`
  - `npx gitnexus@latest analyze --index-only && npx gitnexus@latest detect-changes --scope all --repo .` : `20 files, 17 symbols, 673 affected processes` (explicable par l'extension du Composition Root `initialize_app_services` / `app_lifespan`).

### 3.3 Validation & Procédure de Test sur Toute la Pyramide (`AD-17`)
- **Couche 1a — Tests Unitaires Python (`pytest`)** : `compute_error_fingerprint_sha256` & `extract_top_frame`, garde SSRF (`169.254.169.254`, `fe80::1`, `metadata.google.internal`, `100.100.100.200`, `0.0.0.0`), erreurs amont loguées via `structlog`, `build_log_sink_from_env` (`none`/`elasticsearch`/`loki`), `configure_tracing` (`none`/`otlp`/`console`), corrélation réelle `TracerProvider` $\rightarrow$ `trace_id`/`span_id`, vérification AST `0` `OTLPLogExporter`/`LoggerProvider` et validation YAML Compose.
- **Couche 2 — Test d'Intégration Conteneur Réel (`testcontainers` OpenSearch `2.19.1`)** : `tests/integration/test_story_7_0b_opensearch_log_sink_container.py` (`1 passed in 49.40s`) indexant de vrais documents JSON ECS via `httpx` et validant `LogSinkContractTestKit` contre le cluster OpenSearch éphémère.
- **Couche 3 — Kit de Contrat & Frontières (`tests/conformance/`, `lint-imports`, `lint_spine.py`)** : `LogSinkContractTestKit` validé de manière symétrique sur `FakeInMemoryLogSinkAdapter` et `ElasticsearchLogSinkAdapter`.
- **Couche Sécurité (`tests/security/test_story_7_0b_log_sink_security.py`)** : validation de la non-fuite des jetons `SecretRef` lors d'erreurs HTTP `401` et blocage SSRF Cloud Metadata.
- **Couche 5 — Garde Site & Documentation (`pnpm site:sync && pnpm site:check`, `scripts/check_implementation_docs.py`)** : validé après clôture documentaire.
