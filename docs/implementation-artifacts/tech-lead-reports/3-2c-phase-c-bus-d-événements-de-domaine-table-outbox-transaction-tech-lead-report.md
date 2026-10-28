# Rapport Tech Lead — Story 3.2c : Phase C — Bus d'Événements de Domaine, Table Outbox Transactionnelle (`domain_events_outbox`) Indépendante du Moteur (`OutboxRelayPort`) & Plugins `entry_points`

- **Story Key** : `3-2c-phase-c-bus-d-événements-de-domaine-table-outbox-transaction`
- **Action Items couverts** : `ARCH-M6` (`depends_on: [ARCH-P1]` uniquement, `C3`), `M6`, `M7`, `Q2: 2A`, `Q3: 3A`
- **Date** : 28/10/2026
- **Statut** : `done`

---

## 1. Analyse du Besoin & Étude d'Impact Tech Lead (Avant Implémentation)

### 1.1 Contexte & Problématique Métier / Technique
Afin que le moteur d'orchestration (`orchestration/engine.py`) reste compact et fermé à la modification (principe *Open/Closed*) lorsque les Epics 4 à 7 ajoutent de nouveaux effets secondaires (`audit_finops`, extraction ontologique asynchrone L4, notifications SSE `< 500 ms`, réveil de déclencheurs), la `Story 3.2c` introduit :
1. **Table Outbox Transactionnelle (`domain_events_outbox`, `Q2: 2A`, `C3`)** : Indépendante du moteur d'orchestration (`ARCH-M6.depends_on = [ARCH-P1]`), alimentée dans la **même transaction SQL (`AsyncSession`)** que le changement d'état du Run, du Step ou du Snapshot Blackboard.
2. **Relais Idempotent Abstrait derrière `OutboxRelayPort` (`C3`)** : Deux implémentations interchangeables dans `apps/worker/src/orcia_worker/outbox_relay.py` (`DramatiqOutboxRelay` et `DbosOutboxRelay`) s'appuyant sur `SELECT ... FOR UPDATE SKIP LOCKED` par lots dans `SqlDomainEventsOutboxRepository` et distribuant chaque événement avec `0` doublon par `event_id` via `OutboxEventBus`.
3. **Découverte de Plugins `entry_points` Python (`M7`, `Q3: 3A`)** : Enregistrement déclaratif de `orcia.uri_resolvers` (`git`, `jira`, `confluence`, `db`, `nexus`, `orcia`) et `orcia.llm_gateways` (`litellm`, `cassette`) dans `packages/orcia-core/pyproject.toml`, découverts dynamiquement au démarrage via `importlib.metadata.entry_points` par `PluginRegistryService`.

### 1.2 Analyse d'Impact GitNexus (`repo: "ORCIA"`)
- `gitnexus_impact({target: "OutboxRelayPort", direction: "upstream", repo: "ORCIA"})` : `0` appelant amont existant avant `3.2c` ; `SqlOrchestrationRepository.append_snapshot` est étendu de manière rétrocompatible (`outbox_events: tuple[DomainEvent, ...] = ()`).

### 1.3 Exploration & Chiffres Clés
- **Migration Alembic `0012_story_3_2c_domain_events_outbox.py`** : table `domain_events_outbox` (`event_id UUID PK`, `event_type`, `aggregate_type`, `aggregate_id`, `run_id`, `workspace_id`, `payload_jsonb`, `trace_id`, `status`, `attempts`, `created_at`, `published_at`) + index partiel `idx_domain_events_outbox_pending` (`WHERE status = 'PENDING'`).
- **Volumétrie des fichiers** : `outbox_repository.py` (`163` lignes), `outbox_relay.py` (`144` lignes), `plugin_registry.py` (`165` lignes) — tous bien en deçà du seuil de `300` lignes.

### 1.4 Opportunités de Factorisation (`DRY`)
- Réutilisation directe des 5 classes d'événements immuables de `orcia_kernel.events` (`StepCompleted`, `ArtifactProduced`, `GateEvaluated`, `RunTerminated`, `HumanArbitrationRequested`) et du protocole `orcia_kernel.ports.OutboxRelayPort`.

---

## 2. Plan d'Implémentation

### 2.1 Schéma de Données & Migrations Alembic (`infra/migrations/versions/`)
- `infra/migrations/versions/0012_story_3_2c_domain_events_outbox.py` : création de `domain_events_outbox` et de son index partiel `idx_domain_events_outbox_pending` avec `upgrade()` et `downgrade()` testés sur PostgreSQL 18.

### 2.2 Noyau Hexagonal, Repositories `_internal/`, Plugins & Workers (`packages/orcia-core`, `apps/worker`)
- `packages/orcia-core/src/orcia_core/orchestration/_internal/outbox_repository.py` : `SqlDomainEventsOutboxRepository` (`insert_event_in_session`, `enqueue_event`, `claim_and_relay_pending_batch` avec `SELECT ... FOR UPDATE SKIP LOCKED`, `list_events_by_run`).
- `packages/orcia-core/src/orcia_core/orchestration/_internal/sql_repository.py` : extension de `append_snapshot` pour insérer `outbox_events` dans la même transaction `AsyncSession` que le snapshot Blackboard.
- `apps/worker/src/orcia_worker/outbox_relay.py` : `OutboxEventBus` (abonnés `audit_finops`, `ontology`, `sse` avec déduplication stricte `(subscriber_name, event_id)`), `DramatiqOutboxRelay` (`outbox_relay_actor`) et `DbosOutboxRelay` (`dbos_outbox_relay_workflow`).
- `packages/orcia-core/src/orcia_core/bootstrap/plugin_registry.py` & `packages/orcia-core/pyproject.toml` : `PluginRegistryService` découvrant `orcia.uri_resolvers` et `orcia.llm_gateways` via `importlib.metadata.entry_points`.

### 2.3 Couche Backend FastAPI & Contrats OpenAPI (`apps/api`, `packages/api-client`)
- Aucun changement de schéma HTTP OpenAPI requis en `Story 3.2c`.

### 2.4 Interface SPA (`apps/web`, `@orcia/ui`)
- Aucune modification UI en `Story 3.2c` (la migration SPA `Vite 6 + TanStack Router v1` est traitée en `Story 3.2d`).

---

## 3. Bilan des Modifications & Résultats (Post-Implémentation)

### 3.1 Tableau Synthétique des Fichiers Développés & Modifiés

| Fichier | Action | Rôle |
|---|---|---|
| `infra/migrations/versions/0012_story_3_2c_domain_events_outbox.py` | Créé | Migration Alembic `0012` créant `domain_events_outbox` + index partiel `PENDING` (`ARCH-M6`). |
| `packages/orcia-core/src/orcia_core/orchestration/_internal/outbox_repository.py` | Créé | Repository `SqlDomainEventsOutboxRepository` (`FOR UPDATE SKIP LOCKED`, `C3`). |
| `packages/orcia-core/src/orcia_core/orchestration/_internal/sql_repository.py` | Modifié | Écriture atomique de `outbox_events` dans la transaction de `append_snapshot`. |
| `apps/worker/src/orcia_worker/outbox_relay.py` | Créé | `OutboxEventBus`, `DramatiqOutboxRelay` et `DbosOutboxRelay` (`OutboxRelayPort`, `C3`). |
| `packages/orcia-core/src/orcia_core/bootstrap/plugin_registry.py` | Créé | `PluginRegistryService` découvrant `orcia.uri_resolvers` et `orcia.llm_gateways` (`M7`). |
| `packages/orcia-core/pyproject.toml` | Modifié | Déclaration des groupes `[project.entry-points."orcia.uri_resolvers"]` et `orcia.llm_gateways`. |
| `tests/unit/test_story_3_2c_outbox_and_plugins.py` | Créé | Tests unitaires du relais Outbox (`Dramatiq` & `DBOS`), du bus idempotent et des plugins `entry_points`. |
| `tests/integration/test_story_3_2c_outbox_postgres18.py` | Créé | Test d'intégration PostgreSQL 18 (`upgrade`/`downgrade` `0012`, simulation de crash après `COMMIT` SQL et livraison `100 %` sans doublon au redémarrage). |

### 3.2 Résultats Chiffrés, Métriques & Couverture de Tests ($\ge 90\%$)
- **Architecture Boundary Linter (`.venv/bin/lint-imports`)** : `3 kept, 0 broken` (`164` fichiers analysés, `0` import de `audit_finops`, `ontology` ou `sse` dans `orchestration/engine.py`).
- **Qualité & Typage (`.venv/bin/ruff check .`, `.venv/bin/mypy --strict`)** : `0` erreur sur `120` fichiers sources.
- **Couverture Unitaire (`pytest tests/unit --cov=packages/orcia-kernel --cov=packages/orcia-core`)** : **`>= 93 %`** (seuil requis $\ge 90\%$).
- **Intégration Conteneur Réel PostgreSQL 18 (`test_story_3_2c_outbox_postgres18.py`)** : `1 passed` en `5.36 s` (`3/3` événements en attente livrés après redémarrage, `0` doublon au second passage).

### 3.3 Validation des 5 Couches de Tests (`AD-17`) & `gitnexus_detect_changes()`
- **Couche 1 (Unitaires)** : `PASS` (`>= 93 %`).
- **Couche 2 (Intégration `testcontainers` PostgreSQL 18)** : `PASS` (`test_story_3_2c_outbox_postgres18.py`).
- **Couche 3 (Contrats & Architecture Spine)** : `PASS` (`lint_spine.py` : `0 findings`).
- **Couche 4 (Cassette LLM Déterministe)** : `PASS` (`cassette` plugin découvert via `orcia.llm_gateways`).
- **Couche 5 (Frontières Modulaires)** : `PASS` (`lint-imports` : `3 kept, 0 broken`).
