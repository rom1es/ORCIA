# Spécification d'Implémentation — Story 3.2f : Exécution Réelle des Étapes (`orcia.step_executors`), Taxonomie d'Erreurs Connecteurs (`ConnectorInvoker`) et Validation Verticale Finance (`DEC-P0-EXEC`, `PROC-01`)

- **Story Key** : `3-2f-exécution-réelle-des-étapes-orcia-step_executors-taxonomie-d`
- **Action Items couverts** : `DEC-P0-EXEC` (`P0`), `PROC-01` (`P0`)
- **Clôture d'écart antérieur** : Clôture formelle de l'écart `EC-1` documenté dans le rapport Tech Lead de la `Story 3.2b` ([`3-2b-...-tech-lead-report.md`](file:///home/romain/Documents/Projects/ORCIA/docs/implementation-artifacts/tech-lead-reports/3-2b-persistance-sqlalchemy-async-et-instrumentation-opentelemetry-tech-lead-report.md)).
- **Statut** : `done`

---

## 1. Critères d'Acceptation (`AC-F1` à `AC-F6`)

- **`AC-F1` (`PROC-01`, `P0-3`)** : Registre dynamique `orcia.step_executors` (`StepExecutorPort` dans `orcia_kernel.ports`) et 6 exécuteurs réels (`AGENT` via `LLMPort` / `DeterministicCassetteLLM`, `SKILL`, `SUB_WORKFLOW`, `HUMAN_TASK` avec pause `WAITING_FOR_HUMAN_ARBITRATION` et reprise via `POST /api/v1/orchestration/runs/{run_id}/steps/{step_key}/resume`, `HTTP_ACTION` via `ConnectorInvoker`, `POST_ACTION_VERIFICATION`).
- **`AC-F2`** : Suppression complète des chaînes simulées (`0` occurrence de `simulated` dans `packages/orcia-core/src/orcia_core/orchestration/`) et suppression de `_recover_pending_workflows` et `_ACTIVE_ENGINE` (`0` occurrence dans `packages/` et `apps/`).
- **`AC-F3` & `AC-F4`** : `ConnectorInvoker` (`packages/orcia-core/src/orcia_core/orchestration/connector_invoker.py`) et taxonomie d'erreurs connecteurs (`TransientInfraError(retry_after_s)`, `RateLimitedError`, `UpstreamTimeoutError`, `FunctionalConnectorError`, `PolicyDeniedError`, `PermanentInfraError`) avec respect de `Retry-After`, `0` retry sur `FunctionalConnectorError` / `PolicyDeniedError` (bascule vers `WAITING_FOR_HUMAN_ARBITRATION`), disjoncteur par `(connector_scheme, target_host)` (`CLOSED` $\to$ `OPEN` $\to$ `HALF_OPEN`), conservation de `idempotency_key` sur retry, décompte budgétaire (`max_agent_retries`, `max_cost_usd`) et scrubbing des secrets (`NFR-SEC-4`).
- **`AC-F5`** : Validation verticale non-SDLC « Rapprochement de factures » (Finance / Invoice Reconciliation) exécutée de bout en bout jusqu'à `COMPLETED` en mode `core-without-sdlc` (`tests/fixtures/plugins/finance_reconciliation_plugin.py`).
- **`AC-F6`** : Qualité 5 couches (`AD-17`), couverture unitaire $\ge 90\%$, `lint-imports` (`0 broken`), `mypy --strict` (`0 issue`), test conteneur réel PostgreSQL 18 (`tests/integration/test_story_3_2f_real_api_run_and_restart_postgres18.py`).
