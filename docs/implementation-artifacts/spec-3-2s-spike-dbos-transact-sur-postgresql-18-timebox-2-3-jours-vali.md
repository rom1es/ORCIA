# Spécification Technique — Story 3.2s : Spike DBOS Transact sur PostgreSQL 18 (Timebox 2–3 Jours, Validation Pause/Reprise, Fork, Schedule, Idempotence & Unit of Work SQLAlchemy)

- **Story Key** : `3-2s-spike-dbos-transact-sur-postgresql-18-timebox-2-3-jours-vali`
- **Action Item** : `ARCH-P2-SPIKE` (`P0`, `depends_on: []`, conditionne `ARCH-P1` et `ARCH-P2`)
- **Epic** : Epic 3 — Orchestration Durable, Blackboard Append-Only, Agent Assistant & Gouvernance Humaine
- **Décisions d'Architecture** : `AD-2`, `AD-13`, `AD-17`, `AD-18`, `AD-19`, `OQ-01`, `C1`, `C2`
- **Statut** : `in-progress`

---

## 1. Objectif du Spike (`C1`, `C2`)

Valider formellement, par une suite de tests automatisés reproductibles sur PostgreSQL 18 (`pgvector/pgvector:pg18`) et Redis 7.4 via `testcontainers-python`, les **8 critères de sortie Go/No-Go** de `DBOS Transact` et fixer le patron exact de **Unit of Work `SQLAlchemy 2.1 Asyncio` (`asyncpg`)** avant l'écriture des repositories de domaine (`ARCH-P1`) et l'intégration complète du moteur (`ARCH-P2`) en `Story 3.2b`.

---

## 2. Les 8 Critères de Sortie Go/No-Go

| # | Critère | Mécanisme DBOS évalué | Seuil d'acceptation Go/No-Go |
|---|---|---|---|
| **1** | **Pause durable & reprise après crash (`SIGKILL`)** | `DBOS.recv_async` / `DBOS.send_async` + `DBOS._recover_pending_workflows()` | Le workflow en attente d'arbitrage humain (`WAITING_FOR_HUMAN_ARBITRATION`) survit à l'arrêt brutal + relance de l'instance DBOS et reprend exactement à l'étape en pause dès réception du signal `DBOS.send_async`. |
| **2** | **Relance ciblée (*Rewind / Replay*) à partir de l'étape $N$** | `DBOS.fork_workflow_async(workflow_id, start_step=N)` | Un workflow de 3 étapes relancé avec `start_step=2` ne ré-exécute **pas** l'étape 1 (`compteur_step_1 == 1`) et ré-exécute uniquement les étapes $\ge 2$ sous un nouveau `workflow_id`. |
| **3** | **Planification déclarative périodique (Cron)** | `DBOS.apply_schedules([ScheduleInput(...)])` & `DBOS.trigger_schedule(...)` | Enregistrement déclaratif d'une planification cron dans `dbos.workflow_schedules`, inspection via `DBOS.list_schedules()` et déclenchement effectif du workflow cible. |
| **4** | **Déduplication transactionnelle stricte (`0` doublon)** | `with SetWorkflowID("<trigger_id>:<idempotency_key>"):` | $K$ appels concurrents ou répétés avec la même clé `SetWorkflowID` n'exécutent l'effet de bord qu'**une seule fois** (`side_effect_count == 1`) et retournent le même résultat. |
| **5** | **Cohabitation avec le Blackboard en ajout seul** | Transaction SQL sur `public.blackboard_snapshots` + trigger `BEFORE UPDATE OR DELETE RAISE EXCEPTION` | L'insertion de snapshots immuables dans une transaction DBOS réussit ; toute tentative d'`UPDATE` ou `DELETE` lève `ERR_BLACKBOARD_APPEND_ONLY_VIOLATION` et annule atomiquement la transaction ; le *fork* insère une nouvelle branche sans muter l'historique. |
| **6** | **Cohabitation avec `Dramatiq 2.1.0`** | Appel d'un `@dramatiq.actor` depuis une étape `@DBOS.step()` | Aucun conflit de boucle d'événements `asyncio` ni de pool de connexions entre l'exécuteur DBOS et le broker Dramatiq (Redis / Stub). |
| **7** | **Intégration Unit of Work `SQLAlchemy 2.1 Asyncio` (`asyncpg`)** | `dbos.AsyncSQLAlchemyDatasource` (`run_tx_step_async` / `@ds.transaction` + `ds.sql_session`) | Une même méthode de repository/UoW fonctionne de manière transparente **dans** un `@DBOS.workflow()` (checkpoint `dbos.transaction_completion` commité dans la même transaction PostgreSQL que les tables métier `public.*`) et **hors** workflow (requête HTTP FastAPI directe), avec rollback atomique complet en cas d'exception. |
| **8** | **Testabilité déterministe sous `pytest` + `testcontainers-python`** | Initialisation / nettoyage du schéma `dbos` sur conteneur PG18 éphémère | Temps total d'exécution de la suite d'intégration des 8 critères $< 30\text{ s}$, déterministe à 100 % sans fuite de threads à la fermeture (`DBOS.destroy()`). |

---

## 3. Architecture Cible du Prototype (`packages/orcia-core/src/orcia_core/orchestration/_internal/dbos_spike.py`)

- **Isolation architecturale (`AD-19`)** : Tout le code dépendant du SDK `dbos`, de `sqlalchemy` et de `dramatiq` est strictement encapsulé dans `packages/orcia-core/src/orcia_core/orchestration/_internal/dbos_spike.py`. Aucun import de `dbos` ou `sqlalchemy` ne fuit dans `orcia_kernel` ni dans les modèles/ports publics de `orcia_core`.
- **Patron Unit of Work retenu pour `ARCH-P1` (`DbosSqlAlchemyUnitOfWork`)** :
  - Utilise `AsyncSQLAlchemyDatasource.create(database_url=async_database_url, schema=dbos_schema, run_migrations=True)` sur `postgresql+asyncpg://`.
  - Expose `session: AsyncSession` (délégué à `datasource.sql_session`) et `run_transaction(func, *args, name=None, isolation_level="READ COMMITTED", **kwargs)` (délégué à `datasource.run_tx_step_async`).
