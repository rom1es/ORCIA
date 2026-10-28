# Spécification Technique — Story 3.2c : Phase C — Bus d'Événements de Domaine, Table Outbox Transactionnelle (`domain_events_outbox`) Indépendante du Moteur (`OutboxRelayPort`) & Plugins `entry_points`

- **Story Key** : `3-2c-phase-c-bus-d-événements-de-domaine-table-outbox-transaction`
- **Action Items** : `ARCH-M6` (`depends_on: [ARCH-P1]`), `M6`, `M7`, `Q2: 2A`, `Q3: 3A`, `C3`
- **Statut** : `in-progress`

## 1. Objectifs & Critères d'Acceptation
1. **Migration Alembic `0012_story_3_2c_domain_events_outbox.py`** :
   - Crée dans le schéma `public` la table `domain_events_outbox` (`event_id UUID PRIMARY KEY`, `event_type`, `aggregate_type`, `aggregate_id`, `run_id`, `workspace_id`, `payload_jsonb`, `trace_id`, `status PENDING | PUBLISHED | FAILED`, `attempts`, `created_at`, `published_at`) avec index partiel `idx_domain_events_outbox_pending` sur `status = 'PENDING'`.
2. **Publication Transactionnelle & Relais `OutboxRelayPort` (`C3`, `Q2: 2A`)** :
   - Écriture des événements immuables (`StepCompleted`, `ArtifactProduced`, `GateEvaluated`, `RunTerminated`, `HumanArbitrationRequested`) dans la **même transaction SQL (`AsyncSession`)** que la mutation métier sur `workflow_runs`, `step_executions` ou `blackboard_snapshots`.
   - Relais idempotent abstrait derrière `orcia_kernel.ports.OutboxRelayPort` avec deux implémentations dans `apps/worker/src/orcia_worker/outbox_relay.py` (`DramatiqOutboxRelay` et `DbosOutboxRelay`) utilisant `SELECT ... FOR UPDATE SKIP LOCKED` par lots et distribuant sans doublon (`0` doublon par `event_id`) aux abonnés découplés (`audit_finops`, `ontology`, `sse`).
3. **Plugins Python `entry_points` (`M7`, `Q3: 3A`)** :
   - Déclaration de `orcia.uri_resolvers` (`git`, `jira`, `confluence`, `db`, `nexus`, `orcia`) et `orcia.llm_gateways` (`litellm`, `cassette`) dans `packages/orcia-core/pyproject.toml`.
   - Découverte dynamique via `importlib.metadata.entry_points` dans `packages/orcia-core/src/orcia_core/bootstrap/plugin_registry.py`.
