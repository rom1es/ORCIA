# Spécification Technique — Story 3.2b : Phase B — Persistance Réelle `SQLAlchemy 2.1 Asyncio` (`asyncpg`), Intégration du Moteur Durable `DBOS Transact` sur PostgreSQL 18, Stockage CAS `SeaweedFS` (`ObjectStoragePort`), `LiteLLMAdapter` & Instrumentation `OpenTelemetry`

- **Story Key** : `3-2b-phase-b-persistance-réelle-sqlalchemy-2-1-asyncio-asyncpg-in`
- **Action Items résolus** : `ARCH-P1`, `ARCH-P2`, `ARCH-P6`, `ARCH-P7`, `ARCH-P9` (`C1`, `C2`, `C4`, `C6`)
- **Epic** : Epic 3 — Orchestration Durable, Blackboard Append-Only, Agent Assistant & Gouvernance Humaine
- **Décisions d'Architecture** : `AD-2`, `AD-5`, `AD-8`, `AD-10`, `AD-12`, `AD-13`, `AD-17`, `AD-18`, `AD-19`, `OQ-01`, `OQ-03`
- **Statut** : `in-progress`

---

## 1. Objectif & Périmètre

Suite au verdict **🟢 GO FORMEL (`8/8` critères)** du spike `Story 3.2s` (`ARCH-P2-SPIKE`) et à l'achèvement du socle modulaire `Story 3.2a` (`AD-19`), la `Story 3.2b` branche les adaptateurs d'infrastructure réels d'ORCIA :
1. **`ARCH-P1` (`SQLAlchemy 2.1 Asyncio` + `asyncpg` & `LiteLLMAdapter`)** : Repositories SQL asynchrones encapsulés dans `<domaine>/_internal/sql_repository.py` sur le schéma PostgreSQL 18 `public` unique (migrations Alembic `0001..0011`), pilotés par `DbosSqlAlchemyUnitOfWork`, et adaptateur `LiteLLMAdapter` implémentant `orcia_kernel.ports.LLMPort` aux côtés de `DeterministicCassetteLLM`.
2. **`ARCH-P2` & `C4` (`DBOS Transact` sur PostgreSQL 18 & Suppression du code mort)** : Intégration de `DbosDurableWorkflowEngine` (`orchestration/_internal/dbos_engine.py`) et remplacement de `apps/worker/src/orcia_worker/step_runner.py` par `apps/worker/src/orcia_worker/dbos_workflow_runner.py` tout en conservant `tests/unit/test_durable_orchestration_and_blackboard.py` 100 % vert.
3. **`ARCH-P6` (`SeaweedFS 4.17` Apache-2.0)** : Remplacement de MinIO par `chrislusf/seaweedfs:4.17` dans `infra/docker/docker-compose.yml` et implémentation de `SeaweedFsCasObjectStore` (`catalog/_internal/seaweedfs_adapter.py`) derrière `ObjectStoragePort` (`cas/<sha256>`).
4. **`ARCH-P7` (Recherche Hybride SQL `halfvec(1024)` + `tsvector` GIN `ts_rank_cd` RRF & CTE Tripartite `depth <= 2`)** : Exécution SQL réelle dans `rag/_internal/sql_repository.py`.
5. **`ARCH-P9` (`OpenTelemetry` W3C `trace_id`)** : Propagation de `SpanContext` OpenTelemetry (`traceparent` W3C `00-<trace_id>-<span_id>-01`) dans `observability/logging.py`, FastAPI, SQLAlchemy (`observability/_internal/otel_sqlalchemy.py`) et les enveloppes RFC 9457.
