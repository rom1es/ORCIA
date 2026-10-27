# Rapport d'Analyse, de Décision Go/No-Go & d'Implémentation Tech Lead — Story 3.2s : Spike DBOS Transact sur PostgreSQL 18 (Timebox 2–3 Jours, Validation Pause/Reprise, Fork, Schedule, Idempotence & Unit of Work SQLAlchemy)

- **Story Key** : `3-2s-spike-dbos-transact-sur-postgresql-18-timebox-2-3-jours-vali` (`ARCH-P2-SPIKE`)
- **Action Item résolu** : `ARCH-P2-SPIKE` (`P0`, `depends_on: []`, conditionne `ARCH-P1` et `ARCH-P2`)
- **Epic** : Epic 3 — Orchestration Durable, Blackboard Append-Only, Agent Assistant & Gouvernance Humaine
- **Date** : 2026-10-27
- **Auteurs** : Winston (System Architect) & Amelia (Senior Dev / Tech Lead)
- **Verdict du Spike (`C1`, `C2`)** : **🟢 GO FORMEL** (`8 / 8` critères de sortie validés sur PostgreSQL 18 + Redis 7.4 via `testcontainers-python`)
- **Statut** : `done`

---

## 1. Analyse du Besoin & Étude d'Impact Tech Lead (Avant Implémentation)

### 1.1 Contexte & Justification de l'Avenant A1 (`C1`, `C2`)
Conformément à l'Avenant A1 de la proposition de changement de sprint (`sprint-change-proposal-2026-10-27.md`), l'adoption de `DBOS Transact` (`ARCH-P2`) et l'écriture des repositories `SQLAlchemy 2.1 Asyncio` (`ARCH-P1`) présentaient deux risques majeurs si elles étaient menées directement dans la `Story 3.2b` :
1. **Inversion de dépendance (`C2`)** : Le moteur d'orchestration durable dicte le cycle de vie des transactions SQL (`AsyncSession`). Concevoir les repositories `SQLAlchemy 2.1 Asyncio` avant d'avoir éprouvé le mécanisme transactionnel de DBOS exposait au risque de devoir réécrire les 8 repositories de domaine.
2. **Validation empirique des 8 primitives critiques (`C1`)** : Pause/reprise après crash brutal (`SIGKILL`), relance ciblée à partir d'une étape $N$ (`fork_workflow`), planification déclarative (cron), déduplication transactionnelle (`SetWorkflowID`), cohabitation avec le *Blackboard* en ajout seul (protégé par trigger PostgreSQL), cohabitation avec `Dramatiq 2.1.0`, intégration `SQLAlchemy 2.1 Asyncio` (`asyncpg`), et exécution déterministe `< 30 s` sous `testcontainers-python`.

### 1.2 Analyse d'Impact GitNexus (`repo: "ORCIA"`)
- `gitnexus_impact({target: "packages/orcia-core/src/orcia_core/orchestration/engine.py", direction: "upstream", repo: "ORCIA"})` :
  - **Risque** : **`LOW`** (`impactedCount: 3`, dépendants : `orchestration/__init__.py`, `run_lock_service.py`, `orchestration/seeds.py`).
- Afin de respecter strictement l'invariant **`AD-19`** (aucun import de `dbos`, `sqlalchemy` ou `dramatiq` dans `orcia_kernel` ni dans les modèles/ports publics de `orcia_core`), le prototype de Unit of Work et le harnais de spike sont encapsulés dans `packages/orcia-core/src/orcia_core/orchestration/_internal/uow.py` et `packages/orcia-core/src/orcia_core/orchestration/_internal/dbos_spike.py`.

### 1.3 Découvertes Techniques Majeures du Spike (`dbos 3.3.0` sur PostgreSQL 18)
Le spike a permis d'identifier et de résoudre **4 subtilités techniques majeures** de `DBOS Transact` qui auraient bloqué la `Story 3.2b` sans cette étude préalable :

1. **Évolution de l'API Transactionnelle (`AsyncSQLAlchemyDatasource` vs `@DBOS.transaction`)** :
   - Dans `dbos >= 3.x`, les attributs `DBOS.transaction` et `DBOS.sql_session` de la classe statique ont été remplacés par la classe dédiée **`dbos.AsyncSQLAlchemyDatasource`** (et `SQLAlchemyDatasource` en mode synchrone).
   - `AsyncSQLAlchemyDatasource` crée dans le schéma `dbos` la table `dbos.datasource_outputs` (et `dbos.datasource_migrations`), expose `ds.sql_session()` (retournant l'`AsyncSession` active) et `await ds.run_tx_step_async(options, func, *args, **kwargs)`.
   - **Avantage architectural décisif pour ORCIA** : lorsqu'une fonction exécutée via `run_tx_step_async` est appelée **à l'intérieur d'un `@DBOS.workflow()`**, DBOS exécute `async with session.begin():`, fait un `await session.flush()` des écritures métier (`public.*`), puis insère le résultat sérialisé de l'étape dans `dbos.datasource_outputs` **au sein de la même transaction PostgreSQL ACID** avant le `COMMIT` (puis enregistre la sortie finale dans `dbos.operation_outputs` et nettoie `datasource_outputs` en fin de workflow). Lorsqu'elle est appelée **hors d'un workflow** (ex. endpoint HTTP FastAPI direct), `in_wf == False` et DBOS exécute simplement `async with session.begin():` sans surcharge de workflow !

2. **Piège du pilote `asyncpg` dans `PostgresAsyncDatasource._create_engine`** :
   - Par défaut, si aucun `engine: AsyncEngine` explicite n'est passé à `AsyncSQLAlchemyDatasource.create(database_url=...)`, la fonction interne `dbos._datasource_postgres._make_url` réécrit silencieusement le `drivername` en `"postgresql+psycopg"`.
   - **Solution verrouillée dans `DbosSqlAlchemyUnitOfWork.create`** : instancier explicitement `create_async_engine("postgresql+asyncpg://...")` et le passer via le paramètre `engine=resolved_engine` à `AsyncSQLAlchemyDatasource.create(...)`. Le test d'intégration vérifie formellement `assert runtime.uow.engine.dialect.driver == "asyncpg"`.

3. **Ordre d'initialisation strict `DBOS(config=...)` $\rightarrow$ `AsyncSQLAlchemyDatasource.create(...)` $\rightarrow$ `DBOS.launch()`** :
   - `DBOSRegistry.register_datasource` lève `DBOSException("Datasources must be created before DBOS.launch()")` si `registry.dbos._launched` est `True`. Après un `DBOS.destroy(destroy_registry=False)`, l'ancienne instance `registry.dbos` conserve `_launched == True` jusqu'à ce que `DBOS(config=...)` soit appelé. Il faut donc toujours instancier `DBOS(config=...)` **avant** `DbosSqlAlchemyUnitOfWork.create(...)`, puis appeler `DBOS.launch()`.

4. **Planification Déclarative (`DBOS.apply_schedules` & `ScheduleInput`) et `asyncpg` Prepared Statements** :
   - Le décorateur historique `@DBOS.scheduled` est remplacé par la déclaration atomique `DBOS.apply_schedules([ScheduleInput(schedule_name=..., workflow_fn=..., schedule="*/5 * * * * *", context=...)])` inspectable via `DBOS.list_schedules(schedule_name_prefix=...)` et déclenchable de façon déterministe en test via `DBOS.trigger_schedule(schedule_name)`.
   - Avec `asyncpg`, chaque appel `await session.execute(sa.text(...))` utilise un *prepared statement* PostgreSQL qui n'accepte qu'une seule commande SQL (interdiction de chaîner `DROP TRIGGER ...; CREATE TRIGGER ...;` dans un seul `sa.text()`).

---

## 2. Plan d'Implémentation

### 2.1 Schéma de Données & Migrations Alembic
- Aucune révision Alembic applicative (`public.*`) requise pour le spike ; les tables système DBOS sont créées automatiquement et isolées dans le schéma PostgreSQL dédié `dbos` (`dbos_system_schema="dbos"`).

### 2.2 Noyau Hexagonal & Patron Unit of Work (`packages/orcia-core/src/orcia_core/orchestration/_internal/`)
Le module [`uow.py`](file:///home/romain/Documents/Projects/ORCIA/packages/orcia-core/src/orcia_core/orchestration/_internal/uow.py) fixe le contrat de session que tous les repositories `SQLAlchemy 2.1 Asyncio` utiliseront en `Story 3.2b` (`ARCH-P1`) :

```python
# 1. Initialisation au démarrage (Composition Root lifespan) :
DBOS(config=dbos_config)
uow = await DbosSqlAlchemyUnitOfWork.create(
    async_database_url="postgresql+asyncpg://...",
    schema="dbos",
    run_migrations=True,
)
DBOS.launch()

# 2. Exécution d'une écriture atomique (identique depuis FastAPI ou depuis un @DBOS.workflow()) :
await uow.run_transaction(
    repo.save_run_and_outbox_event,
    run_entity,
    outbox_event,
    name="save_run_and_outbox_event",
    isolation_level="READ COMMITTED",
)
```

### 2.3 Backend FastAPI & Contrats OpenAPI
- Aucun impact sur le contrat OpenAPI 3.1 (`0-diff`).

### 2.4 Interface SPA
- Aucun impact UI.

---

## 3. Bilan des Modifications & Résultats (Post-Implémentation)

### 3.1 Tableau de Validation des 8 Critères Go/No-Go (`tests/integration/test_story_3_2s_dbos_postgres18.py`)

| # | Critère de Sortie | Mécanisme Validé | Résultat Observé sur PG 18 + Redis 7.4 | Verdict |
|---|---|---|---|---|
| **1** | **Pause durable & reprise après crash (`SIGKILL`)** | `DBOS.recv_async` $\rightarrow$ `DBOS.destroy()` + `DBOS.launch()` + `_recover_pending_workflows()` $\rightarrow$ `DBOS.send_async` | Statut `PENDING` vérifié pendant l'attente sans thread bloqué ; reprise exacte après crash et réception de `OPTION_B_APPROVED`. | ✅ **GO** |
| **2** | **Relance ciblée (*Rewind / Replay*) dès l'étape $N$** | `DBOS.fork_workflow_async(orig_id, start_step=2)` | `fork_step_1` exécuté **1 seule fois** (`0` ré-exécution amont) ; `fork_step_2` et `fork_step_3` exécutés **2 fois** sous un nouveau `workflow_id`. | ✅ **GO** |
| **3** | **Planification déclarative périodique (Cron)** | `DBOS.apply_schedules([ScheduleInput(...)])` + `DBOS.list_schedules` + `DBOS.trigger_schedule` | Planification enregistrée dans `dbos.workflow_schedules` et exécutée avec passage de `(scheduled_at, context)`. | ✅ **GO** |
| **4** | **Déduplication transactionnelle stricte (`SetWorkflowID`)** | `with SetWorkflowID("<trigger_id>:<idempotency_key>"):` (`concurrency=6`) | 6 appels concurrents retournent la même sortie avec `exec_count == 1` (`0` doublon). | ✅ **GO** |
| **5** | **Cohabitation avec le Blackboard en ajout seul** | Insertion via `uow.run_transaction` + tentative d'`UPDATE` bloquée par trigger PostgreSQL | L'`UPDATE` lève `ERR_BLACKBOARD_APPEND_ONLY_VIOLATION` et annule la transaction ; le *fork* insère une nouvelle ligne (`total_snapshots == 2`). | ✅ **GO** |
| **6** | **Cohabitation avec `Dramatiq 2.1.0`** | Appel d'un `@dramatiq.actor` depuis un `@DBOS.step()` + connexion `RedisBroker` Redis 7.4 | Exécution sans conflit de boucle `asyncio` ni de pool de connexions. | ✅ **GO** |
| **7** | **Intégration Unit of Work `SQLAlchemy 2.1 Asyncio` (`asyncpg`)** | `DbosSqlAlchemyUnitOfWork` (`uow.engine.dialect.driver == "asyncpg"`) en mode workflow et en mode HTTP autonome | Commit atomique des tables métier + `dbos.datasource_outputs`/`dbos.operation_outputs` en mode workflow, et commit direct en mode HTTP autonome. | ✅ **GO** |
| **8** | **Testabilité déterministe `< 30 s` (`testcontainers`)** | Démarrage PG18 + Redis 7.4, migrations DBOS, exécution des 8 critères et `runtime.stop()` | Exécuté de manière déterministe en **`13,33 s`** (bien sous le seuil de `30 s`). | ✅ **GO** |

### 3.2 Fichiers Créés / Modifiés

| Fichier | Rôle | Lignes |
|---|---|---|
| [`uow.py`](file:///home/romain/Documents/Projects/ORCIA/packages/orcia-core/src/orcia_core/orchestration/_internal/uow.py) | `DbosSqlAlchemyUnitOfWork` (`AsyncSQLAlchemyDatasource` + préservation du pilote `asyncpg`) pour `ARCH-P1` (`100 %` de couverture unitaire) | 91 |
| [`dbos_spike.py`](file:///home/romain/Documents/Projects/ORCIA/packages/orcia-core/src/orcia_core/orchestration/_internal/dbos_spike.py) | Workflows DBOS et harnais de vérification `DbosSpikeRuntime` des 8 critères Go/No-Go | 400 |
| [`test_story_3_2s_dbos_postgres18.py`](file:///home/romain/Documents/Projects/ORCIA/tests/integration/test_story_3_2s_dbos_postgres18.py) | Test d'intégration réel `testcontainers-python` (PostgreSQL 18 + `pgvector` et Redis 7.4) validant les 8 critères | 222 |
| [`test_story_3_2s_dbos_spike.py`](file:///home/romain/Documents/Projects/ORCIA/tests/unit/test_story_3_2s_dbos_spike.py) | Tests unitaires du `DbosSqlAlchemyUnitOfWork`, des steps/workflows et de la configuration | 228 |
| [`spec-3-2s-spike-dbos-transact-sur-postgresql-18-timebox-2-3-jours-vali.md`](file:///home/romain/Documents/Projects/ORCIA/docs/implementation-artifacts/spec-3-2s-spike-dbos-transact-sur-postgresql-18-timebox-2-3-jours-vali.md) | Spécification technique du spike `Story 3.2s` | 64 |

### 3.3 Validation des Portes de Qualité & `gitnexus_detect_changes()`
- **Couverture unitaire (`pytest`)** : **`93,50 %`** global (`uow.py` : **`100 %`**).
- **Test d'intégration réel (`testcontainers` PG18 + Redis 7.4)** : **`1 passed in 13.33s`**.
- **Contrats `import-linter` (`AD-19`)** : **`3 kept, 0 broken`** (`148 files, 610 dependencies`).
- **Typage `mypy --strict` & `ruff`** : **`0` erreur**.
- **`gitnexus_detect_changes({scope: "all", repo: "ORCIA"})`** : `risk_level: "low"`.
