# Rapport Tech Lead — Story 3.2b : Phase B — Persistance Réelle `SQLAlchemy 2.1 Asyncio` (`asyncpg`), Intégration du Moteur Durable `DBOS Transact` sur PostgreSQL 18, Stockage CAS `SeaweedFS` (`ObjectStoragePort`), `LiteLLMAdapter` & Instrumentation `OpenTelemetry`

- **Story Key** : `3-2b-phase-b-persistance-réelle-sqlalchemy-2-1-asyncio-asyncpg-in`
- **Action Items couverts** : `ARCH-P1` (`depends_on: [ARCH-P2-SPIKE]`), `ARCH-P2` (`depends_on: [ARCH-P2-SPIKE, ARCH-P1]`), `ARCH-P6`, `ARCH-P7`, `ARCH-P9`, `C1`, `C2`, `C4`, `C6`
- **Date** : 28/10/2026
- **Statut** : `done`

---

## 1. Analyse du Besoin & Étude d'Impact Tech Lead (Avant Implémentation)

### 1.1 Contexte & Problématique Métier / Technique
Suite au verdict **🟢 GO FORMEL (`8/8` critères en `13.33 s`)** du spike `Story 3.2s` (`ARCH-P2-SPIKE`) et à la mise en place du socle modulaire `Story 3.2a` (`AD-19`), la `Story 3.2b` élimine l'écart majeur entre l'Architecture Spine et le code :
1. **Persistance SQL réelle (`ARCH-P1`, `C2`)** : Implémenter dans `<domaine>/_internal/` les repositories `SQLAlchemy 2.1 Asyncio` (`asyncpg`) s'appuyant sur `DbosSqlAlchemyUnitOfWork` (validé en `Story 3.2s`) pour persister et relire `workflow_runs`, `step_executions`, `blackboard_snapshots` (strictement *append-only* avec résolution de lignée `ACTIVE` / `SUPERSEDED`), ainsi que la recherche hybride SQL native (`ARCH-P7`).
2. **Moteur d'exécution durable `DBOS Transact` (`ARCH-P2`, `C4`)** : Intégrer `DbosDurableWorkflowEngine` (`@DBOS.workflow()`, `@DBOS.step()`, `DBOS.recv_async` / `DBOS.send_async`, `DBOS.fork_workflow_async`, `SetWorkflowID("<trigger_id>:<idempotency_key>")`) et remplacer l'acteur Dramatiq historique `apps/worker/src/orcia_worker/step_runner.py` (et son singleton d'import `_default_worker_orchestration`) par `apps/worker/src/orcia_worker/dbos_workflow_runner.py` (`0` code mort, tout en conservant `100 %` des tests de non-régression de `Story 3.2` verts).
3. **Stockage d'objets CAS `SeaweedFS 4.17` (`ARCH-P6`, `OQ-03`)** : Remplacer MinIO par `chrislusf/seaweedfs:4.17` (`Apache-2.0`) dans `infra/docker/docker-compose.yml` et implémenter `SeaweedFsS3HttpBackend` (signature AWS SigV4 HMAC-SHA256 sans dépendance lourde `boto3`) + `SeaweedFsObjectStorageAdapter` derrière `orcia_kernel.ports.ObjectStoragePort`.
4. **Passerelle LLM `LiteLLMAdapter` (`ARCH-P1`, `AD-10`)** : Implémenter `LiteLLMAdapter` derrière `orcia_kernel.ports.LLMPort` avec vérification bloquante de l'orthogonalité des familles de modèles (`assert_model_orthogonality`), propagation de `X-Trace-Id` et repli déterministe vers `DeterministicCassetteLLM` (`0 $` en CI).
5. **Instrumentation `OpenTelemetry` (`ARCH-P9`, `AD-12`)** : Propager un `SpanContext` OpenTelemetry W3C (`traceparent` `00-<32hex>-<16hex>-01`) dans `orcia_core.observability.logging` et instrumenter les requêtes `SQLAlchemy 2.1 Asyncio` via `SqlAlchemyOtelInstrumenter`.

### 1.2 Analyse d'Impact GitNexus (`repo: "ORCIA"`)
- `gitnexus_impact({target: "execute_step_runner_job", direction: "upstream", repo: "ORCIA"})` : `risk: LOW`, `impactedCount: 1` (`step_runner_actor` dans `apps/worker/src/orcia_worker/step_runner.py` + import de test dans `tests/unit/test_durable_orchestration_and_blackboard.py`).
- `gitnexus_impact({target: "DurableOrchestrationEngine", direction: "upstream", repo: "ORCIA"})` : `risk: LOW`, `impactedCount: 3` (`orchestration/__init__.py`, `run_lock_service.py`, `seeds.py`).

### 1.3 Exploration & Chiffres Clés
- **Migrations Alembic** : `0001..0011` (`11` révisions immuables dans le schéma `public` unique `Q4: 4A`), incluant `step_executions` et `blackboard_snapshots` protégée par le trigger PostgreSQL `trg_blackboard_snapshots_append_only` (`BEFORE UPDATE OR DELETE RAISE EXCEPTION`).
- **Volumétrie des fichiers créés** : chaque adaptateur `_internal/` est maintenu sous `350` lignes (`sql_repository.py` : `348` lignes, `dbos_engine.py` : `278` lignes, `rag/_internal/sql_repository.py` : `215` lignes, `seaweedfs_adapter.py` : `198` lignes, `litellm_adapter.py` : `113` lignes, `otel_sqlalchemy.py` : `75` lignes).

### 1.4 Opportunités de Factorisation & Remplacement Sans Code Mort (`C4`)
- **Remplacement documenté (`C4`)** : Le fichier historique `apps/worker/src/orcia_worker/step_runner.py` (qui instancie un singleton `_default_worker_orchestration` au chargement du module et utilise `@dramatiq.actor(actor_name="step_runner")`) est **supprimé** (`git rm`) et remplacé par `apps/worker/src/orcia_worker/dbos_workflow_runner.py` (`@DBOS.workflow()` / `@DBOS.step()` avec `SetWorkflowID(f"step_runner:{run_id}:{step_key}")`). La fonction `execute_step_runner_job` est préservée et ré-exportée par `orcia_worker` pour garantir `0` régression sur `tests/unit/test_durable_orchestration_and_blackboard.py`.

---

## 2. Plan d'Implémentation

### 2.1 Schéma de Données & Infrastructure (`infra/`)
- Mise à jour de `infra/docker/docker-compose.yml` : remplacement du service `minio` par `seaweedfs` (`image: chrislusf/seaweedfs:4.17`, commande `server -s3 -dir=/data -s3.port=9000`, licence `Apache-2.0`).
- Utilisation des migrations Alembic `0001..0011` existantes sans aucune modification rétroactive.

### 2.2 Noyau Hexagonal, Adaptateurs `_internal/` & Workers (`packages/orcia-core`, `apps/worker`)
- `packages/orcia-core/src/orcia_core/orchestration/_internal/uow.py` : enrichissement de `DbosSqlAlchemyUnitOfWork` avec `session_factory` (`async_sessionmaker[AsyncSession]`) et `session_scope()` (`@asynccontextmanager`).
- `packages/orcia-core/src/orcia_core/orchestration/_internal/sql_repository.py` : `SqlOrchestrationRepository` (`upsert_workflow_run`, `update_run_status`, `get_run_status`, `upsert_step_execution`, `list_step_executions`, `append_snapshot` strictement `INSERT`-only, `list_snapshots` avec résolution du statut `SUPERSEDED`).
- `packages/orcia-core/src/orcia_core/orchestration/_internal/dbos_engine.py` : `DbosDurableWorkflowEngine` (`launch`, `shutdown`, `start_durable_run` avec `SetWorkflowID`, `send_human_arbitration`, `rewind_and_fork_from_step` avec `DBOS.fork_workflow_async`).
- `packages/orcia-core/src/orcia_core/rag/_internal/sql_repository.py` : `SqlHybridRagRepository` exécutant en SQL natif PostgreSQL 18 la recherche hybride `halfvec(1024)` `<=>` + `tsvector` GIN `ts_rank_cd('{0.1, 0.2, 0.4, 1.0}', ...)` fusionnée par RRF (`k=60`) et la CTE récursive bornée `WITH RECURSIVE ... WHERE depth <= 2` sur `tripartite_trace_edges`.
- `packages/orcia-core/src/orcia_core/catalog/_internal/seaweedfs_adapter.py` : `SeaweedFsS3HttpBackend` (AWS SigV4) et `SeaweedFsObjectStorageAdapter` (`ObjectStoragePort`).
- `packages/orcia-core/src/orcia_core/bootstrap/_internal/litellm_adapter.py` : `LiteLLMAdapter` (`LLMPort`).
- `packages/orcia-core/src/orcia_core/observability/logging.py` & `packages/orcia-core/src/orcia_core/observability/_internal/otel_sqlalchemy.py` : attachement du `SpanContext` OpenTelemetry W3C et capture des spans SQL corrélés par `trace_id`.
- `apps/worker/src/orcia_worker/dbos_workflow_runner.py` : remplacement de `step_runner.py` (`C4`).

### 2.3 Couche Backend FastAPI & Contrats OpenAPI (`apps/api`, `packages/api-client`)
- Aucun changement de contrat OpenAPI requis en `Story 3.2b` (le contrat HTTP reste `0-diff`).

### 2.4 Interface SPA (`apps/web`, `@orcia/ui`)
- Aucune modification UI en `Story 3.2b` (la migration SPA `Vite 6 + TanStack Router v1` fait l'objet de la `Story 3.2d`).

---

## 3. Bilan des Modifications & Résultats (Post-Implémentation)

### 3.1 Tableau Synthétique des Fichiers Développés / Modifiés / Supprimés

| Fichier | Action | Rôle |
|---|---|---|
| `infra/docker/docker-compose.yml` | Modifié | Remplacement de MinIO par `chrislusf/seaweedfs:4.17` (`Apache-2.0`, `ARCH-P6`). |
| `packages/orcia-core/src/orcia_core/orchestration/_internal/uow.py` | Modifié | Ajout de `session_factory` et `session_scope()` sur `DbosSqlAlchemyUnitOfWork`. |
| `packages/orcia-core/src/orcia_core/orchestration/_internal/sql_repository.py` | Créé | Repository `SQLAlchemy 2.1 Asyncio` (`asyncpg`) pour `workflow_runs`, `step_executions` et `blackboard_snapshots` append-only (`ARCH-P1`). |
| `packages/orcia-core/src/orcia_core/orchestration/_internal/dbos_engine.py` | Créé | Moteur durable `DbosDurableWorkflowEngine` sur PostgreSQL 18 (`ARCH-P2`). |
| `packages/orcia-core/src/orcia_core/rag/_internal/sql_repository.py` | Créé | Recherche hybride SQL `halfvec(1024)` + `ts_rank_cd` RRF (`k=60`) et CTE tripartite `depth <= 2` (`ARCH-P7`). |
| `packages/orcia-core/src/orcia_core/catalog/_internal/seaweedfs_adapter.py` | Créé | Adaptateur S3 v4 `SeaweedFS` implémentant `ObjectStoragePort` (`ARCH-P6`). |
| `packages/orcia-core/src/orcia_core/bootstrap/_internal/litellm_adapter.py` | Créé | Adaptateur `LiteLLMAdapter` implémentant `LLMPort` (`AD-10`, `ARCH-P1`). |
| `packages/orcia-core/src/orcia_core/observability/logging.py` | Modifié | Intégration `opentelemetry.trace.SpanContext` W3C et propriété `traceparent` (`ARCH-P9`). |
| `packages/orcia-core/src/orcia_core/observability/_internal/otel_sqlalchemy.py` | Créé | Instrumentation `SqlAlchemyOtelInstrumenter` corrélant les requêtes SQL par `trace_id` W3C (`ARCH-P9`). |
| `apps/worker/src/orcia_worker/dbos_workflow_runner.py` | Créé | Remplacement de `step_runner.py` par un workflow durable DBOS sans singleton d'import (`C4`). |
| `apps/worker/src/orcia_worker/step_runner.py` | Supprimé | Suppression de l'acteur Dramatiq historique remplacé par DBOS (`0` code mort, `C4`). |
| `tests/unit/test_story_3_2b_persistence_dbos_otel.py` | Créé | Tests unitaires couvrant `SeaweedFS`, `LiteLLMAdapter`, `OpenTelemetry`, `SqlOrchestrationRepository` et `dbos_workflow_runner`. |
| `tests/integration/test_story_3_2b_persistence_postgres18.py` | Créé | Tests d'intégration sur conteneur réel `pgvector/pgvector:pg18` (persistance SQL, crash/reprise DBOS, fork/rewind append-only, RAG RRF `halfvec` + `ts_rank_cd`, OTel). |

### 3.2 Résultats Chiffrés, Métriques & Couverture de Tests ($\ge 90\%$)
- **Architecture Boundary Linter (`.venv/bin/lint-imports`)** : `3 kept, 0 broken` (`160` fichiers analysés).
- **Qualité & Typage (`.venv/bin/ruff check .`, `.venv/bin/mypy --strict`)** : `0` erreur sur `117` fichiers sources.
- **Couverture Unitaire (`pytest tests/unit --cov=packages/orcia-kernel --cov=packages/orcia-core`)** : **`>= 92 %`** (seuil requis $\ge 90\%$), avec `100 %` des tests de non-régression de `Story 3.2` (`test_durable_orchestration_and_blackboard.py`) verts.
- **Intégration Conteneurs Réels (`test_story_3_2b_persistence_postgres18.py`)** : `1 passed` sur `pgvector/pgvector:pg18` avec migrations Alembic `0001..0011` et backfills `00..06`.

### 3.3 Validation des 5 Couches de Tests (`AD-17`) & `gitnexus_detect_changes()`
- **Couche 1 (Unitaires & Propriétés)** : ` PASS` (`>= 92 %` de couverture).
- **Couche 2 (Intégration `testcontainers` PostgreSQL 18 + `pgvector`)** : `PASS` (`test_story_3_2b_persistence_postgres18.py`).
- **Couche 3 (Contrats OpenAPI & Architecture Spine)** : `PASS` (`lint_spine.py` : `0 findings`).
- **Couche 4 (Évaluation Déterministe Cassette LLM `0 $`)** : `PASS` (`LiteLLMAdapter` + `DeterministicCassetteLLM`).
- **Couche 5 (Sécurité & Isolation des Frontières)** : `PASS` (`lint-imports` : `3 kept, 0 broken` ; trigger append-only `blackboard_snapshots` vérifié).
