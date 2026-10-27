# Rapport de Validation d'Architecture — ORCIA (`ARCHITECTURE-SPINE.md` vs Codebase Réelle)

- **Date de l'audit** : `2026-10-27`
- **Auteur** : Winston (Architecte Système BMAD — `/bmad-architecture` modes `validate` & `update`)
- **Workspace** : `docs/planning-artifacts/architecture/architecture-ORCIA-2026-10-24/`
- **Périmètre vérifié** : `ARCHITECTURE-SPINE.md`, `architecture.md`, `pyproject.toml`, `apps/web/package.json`, `packages/*`, `apps/*`, `infra/migrations/versions/0001..0011` (`85` fichiers Python, `11` révisions Alembic).

---

## 1. Synthèse Exécutive & Verdict de la Gate

> **Verdict de Validation (`Reviewer Gate`) : 🔴 ÉCART CRITIQUE D'IMPLÉMENTATION (`In-Memory Simulacrum Drift`) & 🟠 DÉRIVE DE STACK (`MinIO`, `Sandbox`, `Durable Engine`, `Versions`)**
> Si le domaine métier (`packages/orcia-core`), les schémas Pydantic v2 (`OpenAPI 3.1`), l'isolation UI (`@orcia/ui`) et les `11` migrations SQL Alembic (`0001..0011`) sont propres et testés à `96,05 %`, **la couche d'adaptateurs d'infrastructure réelle (`SQLAlchemy`, `asyncpg`, `LiteLLM`, `Docling`, `Wasmtime`, `OpenTelemetry`) est absente de `packages/` et `apps/`**. L'application tourne actuellement sur **37 stores en mémoire** instanciés comme singletons au chargement des modules, tandis que seules les suites `tests/integration/test_real_containers.py` et `infra/scripts/maintenance/00..07_*.py` parlent réellement à PostgreSQL 18, Redis 7 et au stockage objet.

---

## 2. Constats Vérifiés sur le Code (Classés par Gravité)

| ID | Gravité | Constat vérifié dans le dépôt | Preuve factuelle dans le code (`HEAD`) | AD impacté |
| :--- | :--- | :--- | :--- | :--- |
| **G-1** | 🔴 **CRITIQUE** | **Absence totale d'adaptateurs d'infrastructure réels dans `packages/` et `apps/`** | Scan AST/regex sur les `85` fichiers `.py` de `packages/` et `apps/` : **`0` import** de `sqlalchemy`, `asyncpg`, `litellm`, `docling`, `wasmtime` ou `opentelemetry`. `packages/orcia-core/src/orcia_core/ports/llm_port.py` définit uniquement le `Protocol` `LLMPort`, implémenté uniquement par `DeterministicCassetteLLM`. | `AD-1`, `AD-2`, `AD-8`, `AD-9`, `AD-10`, `AD-12` |
| **G-2** | 🔴 **CRITIQUE** | **Stockage 100 % en mémoire et singletons créés à l'import (`Import-Time State`)** | **37 structures en mémoire** (`InMemoryCasStore`, dicts Python dans `AppendOnlyBlackboardStore`, `FederatedCatalogService`, `OntologyHierarchyResolver`, etc.). Les routeurs FastAPI instancient leurs services au chargement du module (ex. `apps/api/src/orcia_api/routers/orchestration.py:L39` `_DEFAULT_ORCHESTRATION_SERVICE = build_default_orchestration_setup_service()`), perdant tout état au redémarrage d'un worker Uvicorn/Dramatiq. | `AD-2`, `AD-4`, `AD-5`, `AD-7`, `AD-14` |
| **G-3** | 🔴 **CRITIQUE** | **Schéma SQL Alembic déconnecté de l'application (`ORM / Repository Gap`)** | Les **11 migrations Alembic** (`infra/migrations/versions/0001_story_1_1` à `0011_story_3_2`, couvrant 17 tables et les triggers append-only) s'exécutent dans `test_real_containers.py` et les scripts `00..07`, mais le dossier `packages/orcia-core/src/orcia_core/db/` annoncé dans la Spine (L353) n'existe pas. | `AD-2`, `AD-7`, `AD-12`, `AD-17` |
| **G-4** | 🔴 **CRITIQUE** | **Réimplémentation manuelle fragile du moteur d'orchestration durable sur Dramatiq** | Dramatiq (`apps/worker`) est une simple file `At-Least-Once` sans primitives d'attente durable multi-semaines (`WAITING_FOR_HUMAN_ARBITRATION`, `WAITING_FOR_PERMISSION`), ni timers/cron distribués, ni `fork/replay` transactionnel, ni gestion native de `SUB_WORKFLOW <= 3`. Tout est codé manuellement dans `orchestration/engine.py`. | `AD-2`, `AD-13`, `AD-18` |
| **G-5** | 🟠 **MAJEUR** | **Packaging Python monolithique (`setuptools`) et règle hexagonale non outillée** | La Spine annonce un workspace `uv` mais la racine utilise un unique `pyproject.toml` (`setuptools.build_meta`) regroupant `orcia-core`, `orcia_api` et `orcia_worker`. Aucun outil (`import-linter` ou `tach`) ne bloque en CI l'import accidentel de `fastapi`/`sqlalchemy`/`litellm` dans `domain/` et `ports/`. | `AD-1`, `AD-17` |
| **G-6** | 🟠 **MAJEUR** | **Obsolescence et risque de licence de MinIO (`AGPLv3` + dépôt communautaire archivé)** | En 2025, MinIO a retiré l'interface d'administration de son édition communautaire puis cessé de publier des images Docker officielles ; en 2026, le dépôt `minio/minio` a été archivé au profit de l'offre commerciale AIStor, tout en exposant le projet au risque de licence `AGPL-3.0`. | `AD-5`, `Stack` |
| **G-7** | 🟠 **MAJEUR** | **Irréalisme opérationnel de la Sandbox duale (`Wasmtime + bubblewrap < 5s`)** | `AD-9` mélange validateurs déterministes légers et exécution de linters/tests unitaires (`UJ-12`) sous un plafond unique de `5000ms` / `256MB` avec `bubblewrap --unshare-net`. Or : (1) `user namespaces` (`--unshare-net`) est fréquemment désactivé sur les nœuds Kubernetes d'entreprise, et (2) `pytest`/`ruff`/`tsc` ne tournent pas dans Wasmtime pur et nécessitent `30–60s` et `1 Go` de RAM. | `AD-9`, `AD-18` |
| **G-8** | 🟠 **MAJEUR** | **Instrumentation OpenTelemetry absente** | Aucun SDK OpenTelemetry (`opentelemetry-api`, `opentelemetry-sdk`, `opentelemetry-instrumentation-fastapi`) n'est installé : le `trace_id` dans `main.py` et `logging.py` est un simple identifiant généré ou lu depuis l'en-tête HTTP `X-Trace-Id`, sans propagation W3C TraceContext (`traceparent`) vers les workers ou PostgreSQL. | `AD-12`, `Conventions` |
| **G-9** | 🟡 **MODÉRÉ** | **Dérive des versions (`pyproject.toml`, `package.json`, `.venv`, `node_modules`) vs Spine** | - **Frontend (`apps/web/package.json`)** : `next: ^15.2.0` (installé `15.5.28` vs Spine `16.4.0`), `vitest: ^3.0.0` (installé `3.2.7` vs Spine `5.0.5`), `typescript: ^5.8.2` (installé `5.9.3`).<br>- **Frontend libs absentes** : `@tanstack/react-query`, `tailwindcss`, `@xyflow/react`, `openapi-fetch` sont absents de `apps/web/package.json`.<br>- **Backend (`pyproject.toml`)** : bornes basses (`fastapi>=0.115.0`, `pydantic>=2.9.0`, `dramatiq>=1.17.0`, `sqlalchemy>=2.0.35`, `alembic>=1.14.0`, `pytest>=8.3.0`) non alignées sur la Spine et `.venv`. | `AD-1`, `AD-15`, `Stack` |

---

## 3. Instruction Technique des 9 Préconisations (`P1` à `P9`)

### P1 — Squelette de Bout en Bout Persistant (`Story 3.1a`)
- **Décision** : Intercaler immédiatement une **`Story 3.1a` (Squelette Hexagonal Persistant de Bout en Bout : Adaptateurs SQLAlchemy 2.1 Async, Injection `Depends`/`lifespan`, Adaptateur LiteLLM & Instrumentation OpenTelemetry)** avant de poursuivre les stories aval.
- **Contenu** :
  1. Créer `packages/orcia-core/src/orcia_core/db/` (`engine.py`, `session.py`, `repositories/`) mappant les tables Alembic `0001..0011` en SQLAlchemy 2.1 `AsyncSession` (`asyncpg`).
  2. Remplacer tous les singletons d'import (`_DEFAULT_*_SERVICE`) dans `apps/api` par un gestionnaire de cycle de vie `AsyncExitStack` (`lifespan` FastAPI) et des fournisseurs d'injection `Depends(get_orchestration_service)` branchés sur PostgreSQL 18 et Redis 7.
  3. Implémenter `LiteLLMAdapter(LLMPort)` à côté de `DeterministicCassetteLLM(LLMPort)` (sélectionné par configuration `ORCIA_LLM_PROVIDER=cassette|litellm`).
  4. Tester dans `tests/integration/test_real_containers.py` un **scénario complet de persistance et de survie au redémarrage** : création d'un `WorkflowRun` via HTTP $\rightarrow$ arrêt/recréation de l'application FastAPI et vidage de toute mémoire Python $\rightarrow$ reprise du `WorkflowRun` depuis PostgreSQL 18 à l'étape exacte où il s'était arrêté.

### P2 — Évaluation Comparative des Moteurs d'Exécution Durable (`DBOS` vs `Temporal` vs `Hatchet` vs `Maison`)

| Critère d'évaluation | Moteur Maison + Dramatiq (Actuel) | **DBOS Transact (`dbos` Python)** ⭐ **Recommandé** | Temporal (`temporalio` Python SDK) | Hatchet (`hatchet-sdk`) |
| :--- | :--- | :--- | :--- | :--- |
| **1. Couverture `AD-2`, `AD-13`, `AD-18`** | ❌ Partielle : ni `sleep` durable, ni `recv` multi-semaines, ni cron natif, ni `SUB_WORKFLOW` transactionnel. | ✅ **Complète** : `@DBOS.workflow()`, `@DBOS.step()`, `DBOS.recv(topic, timeout)` (pauses semaines), `@DBOS.scheduled(cron)`, `SetWorkflowID` (idempotence), appels natifs de sous-workflows. | ✅ **Complète** : Workflows, Activities, Signals (`wait_condition`), Schedules, Child Workflows. | ✅ **Bonne** : DAGs, Events, Cron, Child Workflows, Concurrency limits. |
| **2. Compatibilité Blackboard Append-Only (`AD-2`)** | ⚠️ Manuelle (non transactionnelle avec la file Redis). | ✅ **Native & Transactionnelle** : DBOS stocke ses checkpoints dans le schéma `dbos` du **même PostgreSQL 18** ; chaque `@DBOS.step` écrit dans `step_executions` et insère atomiquement dans `blackboard_snapshots`. | ⚠️ Double source de vérité (Event History interne de Temporal vs table `blackboard_snapshots`). | ⚠️ Double source de vérité (base interne Hatchet Engine vs `blackboard_snapshots`). |
| **3. Relance / Replay à partir de l'étape $N$ (`FR-16`)** | ⚠️ Codé à la main. | ✅ **Native via `DBOS.fork_workflow(wf_id, start_step=N)`** : crée un nouveau run forké réutilisant les sorties des étapes $1 \dots N-1$ sans les ré-exécuter, aligné à 100 % sur `ACTIVE`/`SUPERSEDED`. | ✅ `ResetWorkflowExecution` (complexe à corréler avec les UUIDv7 du Blackboard). | ⚠️ Replay par étape supporté mais moins granulaire sur l'arbre de branches. |
| **4. Versions figées (`run-lock.json`, `AD-5`)** | ✅ Géré dans `orcia-core`. | ✅ Épinglage du `run_lock_sha256` en entrée du `@DBOS.workflow` + versioning applicatif natif DBOS. | ✅ Versioning par `patched` / Worker Build IDs (verbeux). | ✅ Supporté via métadonnées d'input. |
| **5. Coût d'exploitation & Infra** | Faible (Redis), mais dette de code élevée. | ✅ **Minimal (0 démon supplémentaire)** : bibliothèque Python *in-process* utilisant uniquement PostgreSQL 18 existant. | 🔴 **Élevé** : cluster Temporal Server + UI + schéma Cassandra/Postgres dédié. | 🟠 **Moyen** : déploiement du serveur Hatchet Engine (Go) + RabbitMQ/Postgres. |
| **6. Licence** | LGPLv3 (Dramatiq) | ✅ **MIT** (`dbos-transact-py`) | ✅ **MIT** (SDK & Server) | ✅ **MIT** (Core) |
| **7. Testabilité (`testcontainers`, `AD-17`)** | ✅ Redis + PG18 | ✅ **Immédiate (`0` conteneur ajouté)** : tourne sur le conteneur `pgvector/pgvector:pg18` existant en `< 1s`. | 🔴 Lourd en CI (nécessite `TemporalEnvironment.start_time_skipping()` ou conteneur Temporal Server). | 🟠 Nécessite le conteneur Hatchet Engine. |

- **Décision reportée dans `AD-2`, `AD-13` et `AD-18`** : Retenir **DBOS Transact (`dbos` sur PostgreSQL 18)** comme moteur d'exécution durable transactionnel pour les workflows, les pauses humaines longues (`DBOS.recv`), le *Replay* (`DBOS.fork_workflow`), les déclencheurs idempotents (`SetWorkflowID`) et les `SUB_WORKFLOW`, tout en conservant `DBOS.Queue` / workers dédiés pour les tâches CPU lourdes (`Docling`). Soumis en **Question Ouverte `OQ-A1`** (avec recommandation d'exécuter `/bmad-deep-recon` en mode `technical` + `select` si un benchmark comparatif DBOS vs Temporal sous charge est souhaité).

### P3 & P4 — Réalignement des Versions, Workspace `uv` Multi-Packages & Garde-Fou Hexagonal (`import-linter`)
- **Décision reportée dans `AD-1` et `Stack`** :
  1. Structurer le dépôt Python en **workspace `uv`** (`pyproject.toml` racine avec `[tool.uv.workspace] members = ["packages/orcia-core", "apps/api", "apps/worker"]` et fichier `uv.lock` versionné).
  2. Ajouter **`import-linter`** (`lint-imports`) en CI avec deux contrats bloquants :
     - `Contract 1 (Pure Domain & Ports)` : `orcia_core.domain` et `orcia_core.ports` ont interdiction formelle d'importer `fastapi`, `sqlalchemy`, `asyncpg`, `dbos`, `dramatiq`, `redis`, `litellm`, `docling`, `boto3`.
     - `Contract 2 (Layered Architecture)` : `orcia_core` a interdiction d'importer `orcia_api` ou `orcia_worker`.
  3. Réaligner la table `Stack` de `ARCHITECTURE-SPINE.md` et les `pyproject.toml` / `package.json` sur les versions réelles vérifiées du projet.

### P5 — Sandbox à Deux Paliers de Budget (`AD-9`)
- **Décision reportée dans `AD-9`** : Remplacer la sandbox monolithique (`< 5s`, `bubblewrap`) par une **Sandbox Bimodale à 2 Paliers (Tiers)** compatible Kubernetes sans privilèges `CAP_SYS_ADMIN` / `userns` :
  - **Palier 1 — Validateurs Déterministes & Règles Statiques (`Wasmtime`, budget `< 5s`, `256 Mo` RAM, `0` réseau, `0` FS hôte)** : validation JSON Schema, YAML Workflow-as-Code, sections Markdown obligatoires, axiomes d'ontologie.
  - **Palier 2 — Linters, Compilateurs & Tests d'Auto-Remédiation `UJ-12` (`Conteneur Rootless Isolé gVisor runsc / Podman --network=none`, budget `< 60s`, `1024 Mo` RAM, `/tmp` `256 Mo`)** : exécution hermétique de `pytest`, `ruff`, `mypy`, `tsc` sur un snapshot monté en lecture seule depuis le CAS, sans requérir de `user namespaces` sur le nœud hôte Kubernetes.

### P6 — Stockage Objet CAS : Sortie de MinIO vers `ObjectStoragePort` S3 + SeaweedFS (`AD-5`)
- **Décision reportée dans `AD-5` et `Stack`** : Face à l'archivage du dépôt communautaire `minio/minio` en 2026, au retrait de sa console d'administration en 2025 et à sa licence `AGPL-3.0`, le CAS (`cas/<sha256>`) est abstrait derrière `ObjectStoragePort` (protocole S3 v4 standard via `boto3` / `aiobotocore`) et utilise **SeaweedFS (`Apache-2.0`, mode `-s3`)** pour le développement local (`docker-compose.yml`) et les tests d'intégration (`testcontainers`), et tout service S3 managé (AWS S3, Scaleway Object Storage, Ceph RGW) en production.

### P7 — Recherche Lexicale BM25 : Choix Explicite de PostgreSQL 18 `tsvector` + `GIN` + `RRF` (`AD-8`)
- **Décision reportée dans `AD-8` et `Deferred`** : Choix explicite et assumé de **PostgreSQL 18 natif (`tsvector` pondéré `setweight` A/B/C/D + index `GIN` + `ts_rank_cd`) fusionné par RRF (`k=60`) avec `pgvector` `halfvec(1024)` HNSW**. Ce choix évite la licence `AGPL-3.0` et les restrictions sur réplicas de lecture physiques de **ParadeDB `pg_search`**, ainsi que la maintenance d'une image PostgreSQL custom. Limite assumée : `ts_rank_cd` ne calcule pas l'IDF global du corpus ; cette limite est compensée par la pondération haute (`A`) sur les identifiants exacts (clés Jira, symboles AST, URI `orcia://`) et par la fusion RRF avec `halfvec(1024)`. L'adoption de `ParadeDB pg_search` est inscrite dans `Deferred` avec seuil de déclenchement explicite (`> 5 000 000` chunks et dégradation mesurée du Recall@10 lexical).

### P8 — Rôle de Next.js (`AD-1`) & Bibliothèques Frontend
- **Décision reportée dans `AD-1`** : Next.js (`apps/web`) est strictement cantonné à un rôle d'**interface cliente réactive (UI/SPA sur App Router, sans BFF métier ni Server Actions mutantes ni accès DB direct)**. Toute lecture/mutation métier transite par `@orcia/api-client` (`openapi-fetch`) et le flux SSE `/api/v1/events/stream` de FastAPI (`apps/api`). L'installation effective de `@tanstack/react-query`, `@xyflow/react`, `tailwindcss` v4 et `openapi-fetch` dans `apps/web/package.json` est planifiée dès la **`Story 3.2a` / `Story 3.3`**.

### P9 — Observabilité OpenTelemetry de Bout en Bout (`AD-12` & `Story 3.1a`)
- **Décision reportée dans `AD-12` et `Stack`** : Intégration obligatoire d'**OpenTelemetry Python (`opentelemetry-api`, `opentelemetry-sdk`, `opentelemetry-instrumentation-fastapi`, `opentelemetry-instrumentation-sqlalchemy`)** dès la `Story 3.1a`, propageant le contexte W3C `traceparent` (`trace_id`, `span_id`) de FastAPI vers DBOS/Workers, Structlog et les enveloppes d'erreur `RFC 9457`.
