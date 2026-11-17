# Story 7.0a — Socle de Journalisation Unifié 12-Factor (JSON stdout), Masquage des Secrets & Niveau de Log Dynamique

- **Date** : 2026-11-17
- **Story / Clé Sprint** : `7-0a-socle-de-journalisation-unifie-12-factor-json-stdout` (`Epic 7` / Socle d'Observabilité 12-Factor)
- **Capacité(s)** : `CAP-202` (existant dans `docs/product/capabilities.yaml`, `planned` → `partial` après 7.0a) — classification : `hygiène` (`AGENTS.md` §5)
- **Auteur / Contexte** : Tech Lead / Senior Dev — Mise en œuvre du socle de journalisation 12-Factor unifié sur `stdout` (`JSON` 1 ligne aligné ECS), masquage récursif des secrets (`NFR-SEC-4`), niveau de log dynamique `LOG_LEVEL`, filtrage des sondes HTTP de santé (`/api/v1/health`, `/ready`), rotation bornée à `50 Mo` dans `scripts/manage.py` et suppression de `pino` dans `apps/web/package.json` (`NFR-OBS-1`, `AD-12`, `AD-23`, Décisions D1, D2).
- **Commits associés** : *(géré par l'orchestrateur parent après validation)*

---

## 1. Analyse du Besoin & Étude d'Impact Tech Lead (Pré-Implémentation)

### 1.1 Contexte & Problématique
- **Comportement actuel** :
  - `packages/orcia-core/src/orcia_core/observability/logging.py` (`248` lignes) configure `structlog` via `PrintLoggerFactory()` et un niveau statique codé en dur (`20` / `INFO`), sans unifier les loggers `logging` de la bibliothèque standard (`uvicorn`, `uvicorn.error`, `uvicorn.access`, `dramatiq`, `dbos`, `sqlalchemy`).
  - Les exceptions et stacktraces émises via `stdlib logging` ou serveurs ASGI/workers sortent en texte brut multi-lignes sur `stderr`, ce qui brise le contrat 12-Factor et l'ingestion native par les collecteurs de conteneurs (`ClusterLogForwarder`, Vector, OTel Collector).
  - Le schéma JSON actuel émet `"event"` à plat sans normalisation ECS (`message`, `service`, `env`, `version`, `logger`, regroupement des attributs dynamiques sous `ctx` pour éviter l'explosion de mapping Elasticsearch/OpenSearch).
  - Plusieurs appels existants dans `packages/` et `apps/` utilisent le formatage positionnel `%s` (`logger.warning("...: %s", exc)`) qui nécessite `structlog.stdlib.PositionalArgumentsFormatter()` et `LoggerFactory()`.
  - `scripts/manage.py` ouvre `.orcia-run/<component>.log` via `log_path.open("ab")` sans borne de taille ni rotation, exposant le poste local au risque de saturation disque.
  - `apps/web/package.json` déclare la dépendance inutilisée `"pino": "^9.6.0"` (absente de `apps/web/src/`).
- **Comportement attendu** :
  - `configure_logging(service: str = "api", log_level: str | None = None, env: str | None = None, version: str = "0.1.0")` unifie `structlog` et `logging` stdlib sur un unique `StreamHandler(sys.stdout)` via `structlog.stdlib.ProcessorFormatter`, garantissant **1 ligne = 1 événement JSON** aligné ECS (`timestamp`, `level`, `logger`, `message`, `service`, `env`, `version`, `trace_id`, `span_id`, `workspace_id`, `run_id`, `step_id`, `exception` aplati en chaîne unique, `ctx`), **0 stacktrace brute sur `stderr`**.
  - `LOG_LEVEL` (`DEBUG | INFO | WARNING | ERROR | CRITICAL`, défaut `INFO`) pilote dynamiquement tous les processus (`apps/api`, `apps/worker`, `scripts/`).
  - `HealthProbeLogFilter` supprime les logs d'accès HTTP réguliers (`< 400`) sur `/api/v1/health` et `/ready` tout en conservant les erreurs `>= 400` (`4xx`/`5xx`).
  - `mask_secrets_processor` masque récursivement les secrets (`password`, `token`, `secret`, `api_key`, `authorization`, `bearer`, `pat`, `jwt`, `ORCIA_BOOTSTRAP_TOKEN`, `Bearer ...`, `eyJ...`, `sk-...`, `SecretRef`) dans `message`, `ctx` et `exception`.
  - `scripts/manage.py` applique une rotation bornée à `50 Mo` max (`RotatingFileHandler(maxBytes=50 * 1024 * 1024, backupCount=3)` ou flux borné asynchrone/helper lors du spawn des daemons locaux) et `pino` est retiré de `apps/web/package.json`.
- **Contraintes `ARCHITECTURE-SPINE.md` (`AD-19`, `AD-23`)** :
  - `orcia_core.observability` est en **couche 5** du Contrat 2 `[tool.importlinter]` : il ne peut importer **que** `orcia_core.kernel` (couche 6) — zéro import vers `permissions`, `catalog`, `orchestration`, `audit_finops`, `gates`, `orcia_api`, `orcia_worker` ou `orcia_connectors`.
  - Conservation stricte de la rétrocompatibilité de `configure_structlog()` et `get_logger(name: str = "orcia")` (et compatibilité `caplog`/`capsys` dans les tests existants).

### 1.2 Exploration, Analyse d'Impact GitNexus, Factorisation & Dette Technique
- **Analyse d'Impact GitNexus (`gitnexus_context`, `gitnexus_impact` sur `repo: "/home/romain/Documents/Projects/ORCIA"`)** :
  - `configure_structlog` (`packages/orcia-core/src/orcia_core/observability/logging.py:228-242`) : `impactedCount: 0` dans le graphe d'appel statique (`staleness: 3 commits behind`), mais `grep` confirme `apps/api/src/orcia_api/main.py:72,78`, `tests/unit/test_orcia_core_and_api.py:53,173` et `tests/unit/test_story_4_2_agentic_gates_and_secrets.py:39,235`. Conservation en tant qu'alias appelant `configure_logging(service="api")`.
  - `get_logger` (`packages/orcia-core/src/orcia_core/observability/logging.py:245-248`) : `risk: HIGH`, `impactedCount: 44` (`22` appels directs de profondeur 1 dans `audit_finops`, `bootstrap`, `orchestration`, `rag`, `gates`; `14` en profondeur 2 ; `8` en profondeur 3 ; `4` processus affectés dans `apps/api/src/orcia_api/routers/blackboard_and_engine.py`). De plus, `grep` recense `7` appels avec formatage positionnel `%s` (`sql_datasource_freshness.py`, `sql_connector_circuit.py`, `datasource_webhooks.py`, `codegraph_indexer.py`) et `test_epic_18_sources_and_codegraph_security.py` utilise `caplog` sur le logger racine.
  - Conséquence architecturale : `get_logger(name)` doit utiliser `structlog.get_logger(name)` avec `structlog.stdlib.LoggerFactory()`, `PositionalArgumentsFormatter()` et laisser `orcia.*` propager vers `root` (pour préserver `caplog`), tout en isolant `uvicorn`, `uvicorn.error`, `uvicorn.access`, `dramatiq`, `dbos` et `sqlalchemy` (`propagate = False`, `handlers = [handler]`).
- **Exploration & Volumétrie** :
  - `logging.py` fait actuellement `248` lignes ; l'extraction du formatage ECS, de la résolution `LOG_LEVEL`, du filtre `HealthProbeLogFilter` et du masquage renforcé vers `packages/orcia-core/src/orcia_core/observability/_internal/ecs_formatter.py` maintient chaque module sous `280` lignes.
  - `apps/web/package.json` contient `"pino": "^9.6.0"` (ligne 22) et `0` import de `pino` dans `apps/web/src/` et `apps/web/scripts/`.
  - `tests/security/test_epic_18_sources_and_codegraph_security.py` utilise `caplog` et `tests/unit/test_story_4_2_agentic_gates_and_secrets.py` utilise `capsys` : l'utilisation d'un proxy dynamique vers `sys.stdout` courant dans le `StreamHandler` garantit la capture `capsys` même après une initialisation préalable.
- **Opportunités de Factorisation & Dette Technique** :
  - Extraction des primitives pures dans `_internal/ecs_formatter.py` (`resolve_log_level`, `HealthProbeLogFilter`, `scrub_sensitive_text`, `scrub_sensitive_dict`, `mask_secrets_processor`, `build_ecs_event_processor`, `build_json_processor_formatter`).
  - Helper réutilisable dans `scripts/manage.py` (`_RotatingLogPipe` / `append_bounded_process_log` s'appuyant sur `logging.handlers.RotatingFileHandler(maxBytes=50 * 1024 * 1024, backupCount=3)`) pour borner la sortie combinée `stdout`/`stderr` des daemons locaux à `50 Mo`.
  - Aucune nouvelle dette technique générée ; `CAP-202` restera suivie pour les Stories `7.0b` et `7.0c`.

---

## 2. Plan d'Implémentation

### 2.1 Schéma de Données & Migrations Alembic
- Non applicable (`Story 7.0a` ne modifie aucune table PostgreSQL ni migration Alembic).

### 2.2 Noyau Métier Hexagonal, Orchestration & Workers (`packages/orcia-core/`, `apps/worker/`, `scripts/`)
- `packages/orcia-core/src/orcia_core/observability/_internal/ecs_formatter.py` (`< 280` lignes) :
  - `resolve_log_level(explicit_level: str | None = None) -> int` lisant `explicit_level or os.environ.get("LOG_LEVEL", "INFO")` (supportant `DEBUG`, `INFO`, `WARNING`, `ERROR`, `CRITICAL`, défaut `INFO` si absent ou invalide).
  - `HealthProbeLogFilter(logging.Filter)` filtrant les accès HTTP réguliers (`status < 400` ou sans statut d'erreur) sur `/api/v1/health` et `/ready`, tout en laissant passer toute entrée `>= 400` ou `levelno >= WARNING`.
  - `scrub_sensitive_text`, `scrub_sensitive_dict`, `register_sensitive_secret_value`, `clear_sensitive_secret_values` et `mask_secrets_processor` : masquage récursif des clés sensibles (`password`, `token`, `secret`, `api_key`, `authorization`, `bearer`, `pat`, `jwt`, `ORCIA_BOOTSTRAP_TOKEN`, `SecretRef`, etc.) et des motifs inline (`Bearer ...`, `Basic ...`, `eyJ...`, `sk-...`, `ghp_...`, `pat_...`, `CANARY_SECRET_...`, `ORCIA_BOOTSTRAP_TOKEN=...`, `password=...`, etc.) dans `message`, `ctx` et `exception`.
  - Normalisation ECS à 1 ligne (`build_ecs_normalizer(service, env, version)`) garantissant les clés `timestamp` (ISO-8601 UTC), `level`, `logger`, `message`, `service`, `env`, `version`, `trace_id`, `span_id`, `workspace_id`, `run_id`, `step_id`, `exception` (chaîne unique aplatie lorsque présente) et `ctx` (clés dynamiques isolées).
  - Uniquement stdlib + `structlog` (respect absolu du Contrat 2 couche 5 `lint-imports` — aucun import de domaine métier).
- `packages/orcia-core/src/orcia_core/observability/logging.py` (`< 250` lignes) :
  - Conserver `TraceContext`, `generate_trace_id`, `generate_span_id`, `resolve_or_create_trace_id`, `bind_trace_context`, `clear_trace_context`, `get_current_trace_context`, `get_current_trace_id`.
  - Implémenter `configure_logging(service: str = "api", log_level: str | None = None, env: str | None = None, version: str = "0.1.0") -> None` configurant `structlog.configure(...)` (`wrap_for_formatter`, `PositionalArgumentsFormatter`, `LoggerFactory`) et attachant un unique `logging.StreamHandler` sur `stdout` (proxy dynamique vers `sys.stdout` compatible `capsys`) doté du `ProcessorFormatter` JSON et du `HealthProbeLogFilter` sur `root`, `uvicorn`, `uvicorn.error`, `uvicorn.access`, `dramatiq`, `dbos` et `sqlalchemy` (`propagate = False` sur ces loggers tiers, tout en laissant `orcia.*` propager vers `root` pour `caplog`).
  - Conserver `configure_structlog() -> None` (alias vers `configure_logging(service="api")`) et `get_logger(name: str = "orcia") -> structlog.stdlib.BoundLogger`.
- `packages/orcia-core/src/orcia_core/observability/__init__.py` :
  - Exporter `configure_logging` et `resolve_log_level` en plus des exports existants.
- `apps/worker/src/orcia_worker/` (`broker.py`, `roles.py`, `outbox_relay.py`, `dbos_workflow_runner.py`, `docling_indexer.py`, `codegraph_indexer.py`, `rag_reindexer.py`) :
  - Configurer `configure_logging(service=os.environ.get("ORCIA_WORKER_ROLE", "worker"))` au démarrage des points d'entrée / acteurs et dans `roles.py:main()` sans casser l'isolation paresseuse de `docling_indexer` (Contrat 5 `lint-imports`).
- `scripts/manage.py` :
  - Remplacer `log_path.open("ab")` par un helper de journalisation locale bornée s'appuyant sur `RotatingFileHandler(maxBytes=50 * 1024 * 1024, backupCount=3)` (avec option `ORCIA_MANAGE_LOG_STDOUT=1` ou redirection bornée à `50 Mo` max sans blocage du daemon détaché).

### 2.3 Couche Backend API, Sécurité & Contrats (`apps/api/`)
- `apps/api/src/orcia_api/main.py` : remplacer `configure_structlog()` par `configure_logging(service="api")`.
- `scripts/run_api.py` : appeler `configure_logging(service="api")` au démarrage et passer `log_config=None` à `uvicorn.run(...)` afin d'empêcher Uvicorn d'écraser le `ProcessorFormatter`.
- Aucune modification des schémas HTTP OpenAPI 3.1 ni du SDK `@orcia/api-client`.

### 2.4 Interface Utilisateur & Expérience (`apps/web/`)
- `apps/web/package.json` & `pnpm-lock.yaml` : suppression de la dépendance inutilisée `"pino": "^9.6.0"` puis exécution de `pnpm install`.

### 2.5 Analyse d'Impact sur la Pyramide des Tests (`AD-17` — Couches 1 à 5 + Sécurité, Obligatoire)
- **Couche 1a (Unitaires Python `tests/unit/`)** :
  - Création de `tests/unit/test_story_7_0a_unified_ecs_logging_and_masking.py` couvrant : **1 ligne = 1 JSON valide** sur `stdout` (`0` sortie multi-ligne sur `stderr`) pour `structlog`, `uvicorn.access`, `dramatiq`, `sqlalchemy.engine`, `dbos` ; sérialisation d'exception aplatie dans `exception` ; présence des champs ECS (`timestamp`, `level`, `logger`, `message`, `service`, `env`, `version`, `trace_id`, `span_id`, `workspace_id`, `run_id`, `step_id`, `ctx`) ; `LOG_LEVEL` dynamique (`DEBUG`, `WARNING`, `ERROR`, défaut `INFO`) ; filtrage `/api/v1/health` et `/ready` (`200` filtré, `500` conservé) ; rotation bornée `50 Mo` dans `scripts/manage.py` ; absence de `pino` dans `apps/web/package.json`.
  - Non-régression des tests existants (`test_orcia_core_and_api.py`, `test_story_4_2_agentic_gates_and_secrets.py`, `test_codebase_architectural_anti_patterns_audit.py`).
- **Couche 1b (Frontend TS `Vitest`)** : `pnpm turbo run lint typecheck test`.
- **Couche 3 (`lint-imports`)** : `5 contracts kept, 0 broken`.
- **Couche Sécurité (`tests/security/`)** :
  - Création de `tests/security/test_story_7_0a_log_secret_masking.py` validant le **secret témoin** (`NFR-SEC-4`) injecté dans `structlog`, `stdlib`, `ctx`, `ORCIA_BOOTSTRAP_TOKEN`, `Bearer`, `eyJ...`, `sk-...`, `SecretRef` et dans une exception Python : `0` fuite en clair dans `stdout` et `stderr`.

---

## 3. Bilan des Modifications & Résultats (Post-Implémentation)

### 3.1 Fichiers Développés & Modifiés
| Fichier | Nature | Description synthétique |
| :--- | :--- | :--- |
| `packages/orcia-core/src/orcia_core/observability/_internal/ecs_formatter.py` | Création (`293` l.) | Briques pures ECS : `resolve_log_level`, `HealthProbeLogFilter`, `mask_secrets_processor` / `scrub_sensitive_*` renforcés (`password`, `token`, `secret`, `api_key`, `authorization`, `bearer`, `pat`, `jwt`, `ORCIA_BOOTSTRAP_TOKEN`, `eyJ...`, `sk-...`, `SecretRef`), `build_ecs_normalizer`, `build_json_processor_formatter`. |
| `packages/orcia-core/src/orcia_core/observability/logging.py` | Modification (`295` l.) | Remplacement de `PrintLoggerFactory` par `configure_logging(service, log_level, env, version)` unifiant `structlog` + stdlib (`root`, `uvicorn`, `uvicorn.error`, `uvicorn.access`, `dramatiq`, `dbos`, `sqlalchemy`) sur `stdout` via `_DynamicStdoutStream`, réactivation des loggers désactivés par `fileConfig`, `ensure_logging_configured`, conservation de `configure_structlog()` et `get_logger()`. |
| `packages/orcia-core/src/orcia_core/observability/__init__.py` | Modification | Export de `configure_logging`, `ensure_logging_configured`, `HealthProbeLogFilter` et `resolve_log_level`. |
| `apps/api/src/orcia_api/main.py` | Modification | Remplacement de `configure_structlog()` par `configure_logging(service="api")`. |
| `scripts/run_api.py` | Modification | Appel à `configure_logging(service="api")` et `uvicorn.run(..., log_config=None)`. |
| `apps/worker/src/orcia_worker/` (`broker.py`, `roles.py`, `outbox_relay.py`, `dbos_workflow_runner.py`, `docling_indexer.py`, `codegraph_indexer.py`, `rag_reindexer.py`) | Modification | Configuration de journalisation `ensure_logging_configured` / `configure_logging(service=os.environ.get("ORCIA_WORKER_ROLE", ...))` dans les points d'entrée CLI et acteurs sans casser l'isolation `docling`. |
| `scripts/manage.py` | Modification | Helper `create_bounded_log_handler` (`RotatingFileHandler`, `maxBytes=50 * 1024 * 1024`, `backupCount=3`) + support `ORCIA_MANAGE_LOG_STDOUT=1`. |
| `apps/web/package.json` & `pnpm-lock.yaml` | Modification | Suppression de la dépendance inutilisée `"pino"` et mise à jour du lockfile (`pnpm install`). |
| `tests/unit/test_story_7_0a_unified_ecs_logging_and_masking.py` | Création | Tests unitaires (ECS 1 ligne JSON `stdout`, 0 `stderr`, `exception` JSON, `LOG_LEVEL`, `HealthProbeLogFilter`, rotation `50 Mo`, absence `pino`, `roles.py`). |
| `tests/security/test_story_7_0a_log_secret_masking.py` | Création | Test du secret témoin (`NFR-SEC-4`) sur `structlog`, `stdlib`, `ctx`, `ORCIA_BOOTSTRAP_TOKEN`, `Bearer`, `eyJ...`, `sk-...`, `SecretRef` et exception Python. |
| `docs/implementation-artifacts/sprint-status.yaml` & `docs/product/capabilities.yaml` | Modification | `epic-7: in-progress`, `7-0a-...: done`, `CAP-202` mise à jour (`status: partial`, `verification: runtime`). |

### 3.2 Résultats Chiffrés, Métriques & Qualité
- **Couverture de tests** :
  - `packages/orcia-core/src/orcia_core/observability/` : **`96.79 %`** (`328` stmts, `5` miss, `108` branches, `9` brpart — `logging.py` à `99 %`, `ecs_formatter.py` à `94 %`, `otel_sqlalchemy.py` à `100 %`) sur `tests/unit/test_story_7_0a_*`, `tests/security/test_story_7_0a_*`, `test_story_3_2b_*` et `test_orcia_core_and_api.py` (`25 passed`).
  - Suite unitaire/sécurité ciblée Story 7.0a + anti-patterns + secrets (`73 passed`) ; suite complète `pytest tests/unit tests/security`: `603 passed`, `1` échec isolé hors périmètre sous charge (`test_pack_builder_fastapi_endpoints`, qui passe `4 passed` en exécution dédiée ; la couverture globale unit+security seule sans `tests/integration/` PG18 sur `packages/orcia-core` est de `84.46 %` du fait des adaptateurs SQL testés en Couche 2).
  - Frontend (`pnpm turbo run lint typecheck test`) : **`9/9` tâches réussies** (`@orcia/web` : `29` fichiers, `128` tests `passed`).
- **Qualité statique & Architecture** :
  - `ruff check .` & `ruff format --check .` : `0` erreur (`935` fichiers conformes).
  - `mypy --strict packages/orcia-core packages/orcia-connectors apps/api apps/worker` : `Success: no issues found in 408 source files`.
  - `lint-imports` : `5 contracts kept, 0 broken` (`451` fichiers, `3005` dépendances).
  - `pnpm site:sync && pnpm site:check` : `OK` (`146` -> `147` rapports après ajout, `60/60` capacités live testées).
  - `gitnexus detect-changes --scope all --repo .` : `Changes: 16 files, 18 symbols | Affected processes: 0 | Risk level: low`.

### 3.3 Validation & Procédure de Test sur Toute la Pyramide (`AD-17`)
- **Couche 1a & 1b (Unitaires Python & Vitest)** : `test_story_7_0a_unified_ecs_logging_and_masking.py` (ECS JSON 1 ligne, exceptions aplaties, `LOG_LEVEL`, filtre `/api/v1/health` et `/ready`, rotation `50 Mo`, `roles.py`, retrait `pino`) + `pnpm turbo run lint typecheck test`.
- **Couche 3 (Contrats & Isolation)** : `lint-imports` (`5/5` contrats conservés) et `test_codebase_architectural_anti_patterns_audit.py`.
- **Couche Sécurité (`tests/security/`)** : `test_story_7_0a_log_secret_masking.py` (`0` fuite de secret témoin sur `stdout` et `stderr`) + non-régression `test_epic_18_sources_and_codegraph_security.py`.
