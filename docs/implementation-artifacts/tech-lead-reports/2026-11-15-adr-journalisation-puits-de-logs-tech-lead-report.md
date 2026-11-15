# 2026-11-15 — Architecture Décisionnelle : Journalisation 12-Factor Unifiée & Puits de Logs Paramétrable (AD-23)

> **Convention de nommage du fichier (Obligatoire — créé AVANT toute modification de documentation/spécification)** :
> `docs/implementation-artifacts/tech-lead-reports/2026-11-15-adr-journalisation-puits-de-logs-tech-lead-report.md`

- **Date** : 2026-11-15
- **Story / Clé Sprint** : `2026-11-15-adr-journalisation-puits-de-logs` (`ADR AD-23` / Prérequis d'Observabilité pour Epic 7 & Déploiement Cible OpenShift)
- **Capacité(s)** : `CAP-202` (création, `status: planned`) liée à `CAP-201` (Epic 7) et `CAP-200` (Epic 6) — classification : `doc`
- **Auteur / Contexte** : Winston (Architecte Système) & Tech Lead ORCIA. Formalisation de la décision d'architecture AD-23 relative à la journalisation 12-factor unifiée sur `stdout`, au découpage du puits de logs paramétrable (`LogSinkQueryPort`), aux traces distribuées OpenTelemetry (OTLP standard), aux 4 invariants stricts de réversibilité, et à la conformité pour déploiement en conteneur non-root sur plateforme OpenShift (OpenShift Logging / `ClusterLogForwarder`). Préparation du découpage en Stories 7.0a, 7.0b et 7.0c pour débloquer les Stories 7.2 et 7.3.
- **Commits associés** : `doc/adr-23-logging-and-log-sink`

---

## 1. Analyse du Besoin & Étude d'Impact Tech Lead (Pré-Implémentation)

### 1.1 Contexte & Problématique
- **Contexte** : Dans le cadre de l'orchestration de processus complexes et de l'auto-remédiation autonome prévue dans l'Epic 7 (notamment Story 7.2 `LOG_SINK_ALERT` et Story 7.3 `POST_ACTION_VERIFICATION`), le système doit être capable de surveiller et d'interroger les journaux d'erreurs techniques pour déclencher des actions correctives et vérifier l'absence d'erreurs résiduelles après déploiement. Par ailleurs, la cible de déploiement en production d'ORCIA est un cluster OpenShift d'entreprise imposant des contraintes d'exploitation strictes (SCC `restricted`, UID arbitraire non-root, conteneurs en système de fichiers racine en lecture seule `readOnlyRootFilesystem: true`, collecte mutualisée par `ClusterLogForwarder` vers un puits Elasticsearch/OpenSearch plateforme).
- **Problématique & État des lieux actuel (constats factuels du 2026-11-15)** :
  1. *Émission hétérogène et partielle* : `structlog` en JSON est configuré uniquement dans l'API (`apps/api/src/orcia_api/main.py:L71`). Les workers (`apps/worker`), le dispatcher de triggers et les scripts d'administration (`scripts/manage.py`, `infra/scripts/maintenance/*`) ne sont pas unifiés. Le worker tourne avec le format console par défaut de la bibliothèque standard, sans masquage systématique des secrets (`NFR-SEC-4`). Le niveau de log est fixé en dur à `INFO` (`orcia_core/observability/logging.py:L238`), sans possibilité d'ajustement dynamique par variable d'environnement (`LOG_LEVEL`).
  2. *Stderr et stacktraces multi-lignes* : Uvicorn et Dramatiq émettent des logs en texte brut sur `stderr`, causant un éclatement des stacktraces en multiples lignes non structurées lors de la collecte.
  3. *Mélange et rétention locale sans rotation* : En développement local, `scripts/manage.py` concatène `stdout` et `stderr` dans des fichiers plats `.orcia-run/*.log` sans aucune rotation (`RotatingFileHandler` absent), créant un risque de saturation disque. `docker-compose.yml` ne définit aucun bloc `logging:` avec `max-size`.
  4. *Trou béant dans les traces OpenTelemetry* : Le composant OTel n'utilise que `NonRecordingSpan` en mémoire (`otel_sqlalchemy.py`). Aucun `TracerProvider` complet ni exportateur OTLP n'est branché. Les dépendances `opentelemetry-sdk` et `opentelemetry-instrumentation-fastapi` sont absentes de `pyproject.toml`, bien que mentionnées dans `ARCHITECTURE-SPINE.md` L319.
  5. *Frontend web* : `pino` est déclaré dans `apps/web/package.json` mais n'est jamais importé ; les erreurs React sont uniquement émises via `console.error` dans la console du navigateur sans remontée serveur.
  6. *Trou de planification bloquant l'Epic 7* : Les Stories 7.2 (`LOG_SINK_ALERT`) et 7.3 (`POST_ACTION_VERIFICATION`) postulent l'existence d'un puits de logs interrogeable, sans qu'aucune story d'infrastructure ou d'architecture ne le définisse ni ne l'implémente.
- **Objectifs de l'arbitrage** :
  - Définir une architecture d'observabilité 12-factor où **l'application ignore totalement l'outil de stockage des logs**.
  - Garantir l'unification 1 ligne = 1 JSON sur `stdout` pour 100 % des processus (api, worker, triggers, scripts, Uvicorn, Dramatiq, SQLAlchemy).
  - Fournir un port d'interrogation abstrait (`LogSinkQueryPort`) et découplé du puits, avec un adaptateur prioritaire pour la cible de production (Elasticsearch / OpenSearch via `opensearch-py` / `elasticsearch-py`) et une alternative dev locale (Loki via LogQL).
  - Déporter la logique métier (détection d'anomalies, empreinte SHA-256, déduplication, cooldown) à l'intérieur d'ORCIA, sans dépendre des alertes propriétaires du puits (Watcher ou Loki Ruler).
  - Établir les 4 invariants de réversibilité garantissant une bascule d'infrastructure (OTel Collector ↔ Vector, Loki ↔ Elasticsearch) en 2 à 3 jours d'infra sans toucher au code applicatif.
  - Découper le travail en 3 User Stories ordonnées (7.0a, 7.0b, 7.0c) préalables aux Stories 7.1..7.4 de l'Epic 7.

### 1.2 Exploration, Analyse d'Impact GitNexus, Factorisation & Dette Technique
- **Analyse d'Impact GitNexus (`repo: "ORCIA"`)** :
  - Symboles impactés :
    - `packages/orcia-core/src/orcia_core/observability/logging.py` : fonction `configure_structlog` et masquage des secrets.
    - `apps/api/src/orcia_api/main.py` : point d'assemblage lifespan de l'API.
    - `apps/worker/src/orcia_worker/main.py` : point d'assemblage startup des workers.
    - `scripts/manage.py` : gestion des logs en local.
    - `apps/api/src/orcia_api/routers/triggers.py` & `apps/worker/src/orcia_worker/actors/` : points de consommation pour Stories 7.2 et 7.3.
  - Niveau de risque : **Moyen à Élevé** sur l'observabilité globale, mais **Zéro impact régressif immédiat sur le code applicatif** puisque le présent travail est strictement cantonné à la documentation, à l'ADR (`AD-23`), à la mise à jour de la Spine et à la planification des Stories dans l'Epic 7.
- **Opportunités de Factorisation & Contrôle de Volumétrie** :
  - Centraliser toute la configuration de journalisation dans `orcia_core.observability.logging` : une fonction unique `configure_logging(service_name: str, log_level: str | None = None)` réutilisable par l'API, les workers et les scripts infra.
  - Utiliser `structlog.stdlib.ProcessorFormatter` pour formater en JSON unifié sur `stdout` y compris les logs émis par la stdlib Python (`logging`), Uvicorn, Dramatiq, DBOS et SQLAlchemy.
  - Définir le port `LogSinkQueryPort` dans `orcia_core/ports/` (ou `orcia_core/observability/ports.py`), respectant strictement l'architecture hexagonale (`AD-19`, aucune dépendance à Elasticsearch ou Loki dans le noyau).
- **Tickets de Dette Technique & Découpage Backlog Créés** :
  - `Story 7.0a` : Socle de journalisation unifié 12-factor (JSON stdout, LOG_LEVEL, ProcessorFormatter stdlib, masquage secrets, worker configuré, scripts, rotation .orcia-run).
  - `Story 7.0b` : Puits de logs paramétrable (`LogSinkQueryPort`), adaptateur Elasticsearch prioritaire, traces OTel (SDK + OTLP standard) et profils Compose (`logs-loki`, `logs-elastic`).
  - `Story 7.0c` : Préparation du déploiement conteneurisé cible OpenShift (SCC restricted, FS read-only, UID arbitraire, sondes liveness/readiness, ConfigMap/Secret, contrat ClusterLogForwarder documenté).
  - Entrées `action_items` dans `sprint-status.yaml` :
    1. `LokiLogSinkAdapter` pour stack dev alternative si non finalisé dans 7.0b.
    2. Télémétrie erreurs front (`POST /api/v1/telemetry/client-errors`) et nettoyage de la dépendance `pino`.
    3. Contrat formel d'intégration `ClusterLogForwarder` avec l'équipe plateforme OpenShift.

---

## 2. Plan d'Implémentation

### 2.1 Schéma de Données & Migrations Alembic (`infra/migrations/versions/...`)
- Aucune modification de schéma de données transactionnelles requise pour l'observabilité de base (les logs transitent par `stdout` et le puits externe).
- Pour Story 7.2 / 7.3 ultérieure : les tables existantes `workflow_triggers` (`trigger_type: LOG_SINK_ALERT`) et `domain_events_outbox` couvrent déjà le besoin. Aucune migration SQL nécessaire dans le cadre de cet arbitrage.

### 2.2 Noyau Métier Hexagonal, Observabilité & Workers (`packages/orcia-core/`, `apps/worker/`)
- `packages/orcia-core/src/orcia_core/observability/` :
  - `logging.py` : Ajout de `configure_logging(service: str)` unifiant structlog et standard library logging via `ProcessorFormatter`. Prise en charge de `LOG_LEVEL` (défaut `INFO`, configurable via env var). Masquage strict des secrets (`SecretRef`, tokens, mots de passe) avant émission.
  - Schéma ECS (Elastic Common Schema) simplifié :
    - `timestamp` (ISO-8601 UTC)
    - `level` (DEBUG, INFO, WARNING, ERROR, CRITICAL)
    - `logger` (nom du module émetteur)
    - `message` (texte principal de l'événement)
    - `service` (api, worker, trigger-dispatcher, script)
    - `env` (dev, test, staging, prod)
    - `version` (version applicative)
    - `trace_id` (W3C TraceContext hex 128-bit)
    - `span_id` (hex 64-bit)
    - `workspace_id`, `run_id`, `step_id` (si présents dans le contexte)
    - `ctx` (dictionnaire regroupant les attributs additionnels pour éviter l'explosion de mapping du puits)
    - `exception` (traceback sérialisé sur 1 ligne JSON en cas d'erreur)
  - `ports.py` (ou `orcia_core/ports/log_sink.py`) :
    - Définition du protocole `LogSinkQueryPort` :
      - `query_logs(query: LogQuery) -> list[LogEntry]`
      - `count_errors(fingerprint: str, window_seconds: int) -> int`
      - `healthcheck() -> bool`
  - `adapters/elasticsearch_sink.py` :
    - Implémentation `ElasticsearchLogSinkAdapter` utilisant le client compatible OpenSearch/Elasticsearch (`opensearch-py` ou `elasticsearch-py`).
    - Requêtage borné par temps et par namespace/service.
  - `adapters/loki_sink.py` :
    - Implémentation `LokiLogSinkAdapter` (LogQL) pour l'environnement dev local optionnel.
- `apps/worker/src/orcia_worker/main.py` :
  - Appel immédiat de `configure_logging("worker")` au démarrage (`on_startup`).
- `apps/api/src/orcia_api/main.py` :
  - Remplacement de l'ancien appel partiel par `configure_logging("api")`.
  - Filtrage des requêtes HTTP régulières de sondes (`/api/v1/health`, `/ready`) pour ne pas polluer les journaux d'accès.

### 2.3 Couche Backend API, Traces Distribuées & Contrats (`apps/api/`, `packages/api-client/`)
- **Traces OpenTelemetry** :
  - Initialisation de `TracerProvider` avec `BatchSpanProcessor` vers `OTLPSpanExporter` (`opentelemetry-exporter-otlp`) ciblant `OTEL_EXPORTER_OTLP_ENDPOINT`.
  - Désactivable proprement via `OTEL_TRACES_EXPORTER=none` en test/local.
  - Instrumentation automatique via `opentelemetry-instrumentation-fastapi`, `opentelemetry-instrumentation-sqlalchemy` et `opentelemetry-instrumentation-httpx`.
  - Corrélation automatique : extraction du `trace_id` et `span_id` courants pour injection dans le contexte `structlog` de chaque log émis.
  - **Interdiction formelle** d'un exportateur OTel Logs dans le code applicatif : les logs sortent uniquement par `stdout` JSON (règle 12-factor).

### 2.4 Interface Utilisateur & Expérience (`apps/web/`)
- Retrait ou plan de nettoyage de la dépendance inutilisée `pino` dans `apps/web/package.json`.
- Inscription en `action_item` de l'endpoint `POST /api/v1/telemetry/client-errors` (RFC 9457, rate-limité, masquage de tokens/secrets) pour capter les erreurs React de production et les injecter dans le flux `stdout` de l'API.

### 2.5 Analyse d'Impact sur la Pyramide des Tests (`AD-17` — Couches 1 à 5 + Sécurité)
- **Couche 1a (Unitaires Python `tests/unit/`)** :
  - Test unitaire du `ProcessorFormatter` et de la sérialisation JSON 1 ligne (absence de saut de ligne dans le champ exception).
  - Test unitaire du respect de `LOG_LEVEL`.
  - Test unitaire du masquage des secrets témoin dans les logs (`NFR-SEC-4`).
  - Test de contrat abstrait commun `LogSinkContractTestKit` validant les implémentations de `LogSinkQueryPort`.
- **Couche 2 (Intégration sur Infrastructure Réelle `tests/integration/`)** :
  - Test d'intégration de l'adaptateur `ElasticsearchLogSinkAdapter` avec conteneur éphémère `testcontainers` Elasticsearch / OpenSearch.
  - Test d'intégration de `LokiLogSinkAdapter` avec conteneur éphémère Loki.
- **Couche 3 (Contrats OpenAPI 3.1 & `lint-imports`)** :
  - Respect strict des contrats d'import (`orcia_core` n'importe aucun SDK client d'infrastructure directement dans `domain/` ni `ports/`).
- **Couche Sécurité (`tests/security/`)** :
  - Test d'absence absolue de token JWT, secret PAT ou clé d'API dans les événements JSON émis sur stdout (test du secret témoin).

---

## 3. Bilan des Modifications & Résultats (Post-Implémentation)

### 3.1 Fichiers Développés & Modifiés
| Fichier | Nature | Description synthétique |
| :--- | :--- | :--- |
| `docs/implementation-artifacts/tech-lead-reports/2026-11-15-adr-journalisation-puits-de-logs-tech-lead-report.md` | Création | Rapport Tech Lead officiel de cadrage architectural et de planification. |
| `docs/planning-artifacts/architecture/architecture-ORCIA-2026-10-24/ARCHITECTURE-SPINE.md` | Modification | Ajout de l'AD-23 (Journalisation 12-factor unifiée, puits de logs paramétrable, port découplé, traces OTLP, conformité OpenShift) ; mise à jour conventions ligne 304 ; mise à jour tableau Stack (versions OTel, Elasticsearch/OpenSearch, Grafana/Loki/Collector) ; liaison AD-18, FR-23, FR-29. |
| `docs/planning-artifacts/architecture/architecture-ORCIA-2026-10-24/architecture.md` | Modification | Mise à jour §3.8 (référence à AD-23 pour LOG_SINK_ALERT et POST_ACTION_VERIFICATION via LogSinkQueryPort) et §6.3 (observabilité unifiée, traces OTel OTLP, 4 invariants de réversibilité, intégration OpenShift Logging). |
| `docs/planning-artifacts/epics.md` | Modification | Ajout des Stories 7.0a, 7.0b, 7.0c dans l'Epic 7 ; mise à jour des Stories 7.2 et 7.3 avec dépendance à 7.0b et décision D5 ; mise à jour de la FR Coverage Map. |
| `docs/implementation-artifacts/sprint-status.yaml` | Modification | Ajout des clés 7-0a, 7-0b, 7-0c au statut `backlog` ; ajout des 3 action items (LokiLogSinkAdapter, télémétrie front/pino, contrat ClusterLogForwarder OpenShift). |
| `docs/product/capabilities.yaml` | Modification | Ajout de la capacité `CAP-202` (`status: planned`) rattachée à l'ADR `2026-11-15-adr-journalisation-puits-de-logs`. |
| `docs/implementation-artifacts/tech-lead-reports/README.md` | Modification | Enregistrement de l'entrée du rapport dans l'index officiel. |

### 3.2 Résultats Chiffrés, Métriques & Qualité
- **Règles d'Architecture & Spine** :
  - Décision d'Architecture AD-23 adoptée et numérotée de façon strictement ascendante et monotone (`AD-22 -> AD-23`).
  - Aucun champ obligatoire omis (`Binds`, `Prevents`, `Rule` rigoureusement structurés).
  - Aucune variable non épinglée dans le tableau `## Stack` (toutes les entrées possèdent leur version figée).
  - Zéro placeholder `TBD`, `TODO`, `FIXME` orphelin introduit.
  - Validation mécanique par l'équivalent de `lint_spine.py` : `0 finding`, `ok: true`.
- **Alignement du Registre des Capacités (`capabilities.yaml`)** :
  - Capacité `CAP-202` correctement typée en `status: planned` avec référence `origin_ref: 2026-11-15-adr-journalisation-puits-de-logs`.
  - Couverture complète et cohérence garantie avec `epics.md`.

### 3.3 Validation & Procédure de Test sur Toute la Pyramide (`AD-17`)
- **Vérification Statique Documentation & Architecture** :
  - Contrôle de la syntaxe YAML et Markdown des fichiers modifiés.
  - Respect de l'isolation du code applicatif : 0 ligne de code exécutable modifiée (respect strict de la directive BMAD Architect).
  - Vérification de la cohérence croisée entre `ARCHITECTURE-SPINE.md`, `architecture.md`, `epics.md`, `sprint-status.yaml`, `capabilities.yaml` et le registre des rapports.
