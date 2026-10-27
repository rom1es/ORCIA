---
title: 'Story 3.1: Workflow-as-Code YAML/JSON (SUB_WORKFLOW <= 3 & Criticité), Gabarits d''Artefact Multi-Audience, Discipline Intention -> Code & Épinglage Récursif run-lock.json'
type: 'feature'
created: '2026-10-27'
status: 'done'
route: 'dispatch'
baseline_commit: '420a17130283c63f6f0e10a67b866fda43b5b7c7' # pragma: allowlist secret
review_loop_iteration: 0
context:
  - '{project-root}/AGENTS.md'
  - '{project-root}/docs/implementation-artifacts/epic-3-context.md'
---

<frozen-after-approval reason="human-owned intent — do not modify unless human renegotiates">

## Intent

**Problem:** Sans validation déclarative stricte avec numéros de lignes exacts, sans garde-fou interdisant `HIGH_CRITICAL + AUTONOMOUS_CONTRACT` ou le contournement de `Intention -> Code`, sans compilation duale des gabarits d'artefacts (Markdown Humain + JSON Schema typé par l'Ontologie) et sans épinglage récursif `run-lock.json` (`sub_workflow_locks` jusqu'à `nesting_depth <= 3`), les *Workflow Runs* ne peuvent garantir ni la reproductibilité cryptographique à 10 jours ni la sûreté des sous-workflows imbriqués.

**Approach:** Créer la révision Alembic `0010_story_3_1_workflow_runs_triggers_and_run_lock.py` (colonnes `criticality`, `execution_regime`, `tie_break_policy`, `workflow_mode` sur `workflow_definitions`, et tables `workflow_triggers`, `workflow_runs`, `run_lock_manifests`), implémenter dans `packages/orcia-core/orchestration/` le parseur/validateur YAML/JSON (`yaml_loader.py`, `yaml_validator.py`), le compilateur dual de gabarits multi-audiences (`template_compiler.py`) et le service d'épinglage récursif `run-lock.json` et d'instanciation de *Workflow Run* (`run_lock_service.py`, `seeds.py`), exposer les routes REST `/api/v1/orchestration/*` protégées par `ScopeAccessGuard`, régénérer `@orcia/api-client`, et ajouter le studio Workflow-as-Code & `run-lock.json` dans `@orcia/ui` et `apps/web`.

## Boundaries & Constraints

**Always:**
- Rapporter le numéro de ligne exact (`line >= 1`) et le code de règle violé lors de toute erreur de validation YAML/JSON (`FR-11`).
- Rejeter `criticality: HIGH_CRITICAL` combiné à `execution_regime: AUTONOMOUS_CONTRACT` avec `HTTP 422 ERR_CRITICAL_WORKFLOW_REQUIRES_HUMAN_GATE` (`FR-29`, `AD-18`).
- Rejeter toute étape d'écriture/modification de code (`writes_code: true`) non précédée en amont dans le DAG par une étape de déclaration d'intention/spécification (`declares_intention: true`) en mode `standard` avec `HTTP 422 ERR_INTENTION_BEFORE_CODE_REQUIRED` (`FR-13`), et rejeter les workflows de rétro-documentation (`Code -> Doc`) sans `mode: brownfield_bootstrap`.
- Détecter statiquement tout cycle d'appels `SUB_WORKFLOW` (`HTTP 422 ERR_SUB_WORKFLOW_CYCLE_DETECTED`) et toute profondeur `nesting_depth > 3` (`HTTP 422 ERR_SUB_WORKFLOW_MAX_DEPTH_EXCEEDED`, `FR-30`, `AD-18`).
- Épingler dans `run-lock.json` les triplets `(alias, scheme, uri, resolved_version, sha256, cas_key)`, les surcharges à 4 niveaux, le `kb_snapshot_hash` et l'arbre récursif `sub_workflow_locks`.

**Never:**
- Ne jamais importer `fastapi`, `sqlalchemy`, `dramatiq`, `redis` ou `litellm` dans `packages/orcia-core/domain` ou `packages/orcia-core/ports`.
- Ne jamais autoriser une mutation en mode `READ_ONLY_OBSERVER` (`HTTP 403 ERR_OBSERVER_MODE_READ_ONLY`).

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Validation DAG nominal avec `SUB_WORKFLOW <= 3` | Manifeste YAML valide (`nesting_depth <= 3`, intention avant code) | Retourne `valid=True`, DAG résolu et profondeur max calculée | N/A |
| Workflow `HIGH_CRITICAL` en régime `AUTONOMOUS_CONTRACT` | `criticality: HIGH_CRITICAL` + `execution_regime: AUTONOMOUS_CONTRACT` | Rejet immédiat avec ligne exacte | `HTTP 422 ERR_CRITICAL_WORKFLOW_REQUIRES_HUMAN_GATE` |
| Écriture de code sans intention amont en mode `standard` | Step `writes_code: true` sans ancêtre `declares_intention: true` | Rejet immédiat avec ligne exacte du step fautif | `HTTP 422 ERR_INTENTION_BEFORE_CODE_REQUIRED` |
| Cycle ou profondeur `> 3` dans `SUB_WORKFLOW` | `WF-A -> WF-B -> WF-A` ou chaîne `depth = 4` | Rejet statique avant instanciation | `HTTP 422 ERR_SUB_WORKFLOW_CYCLE_DETECTED` / `ERR_SUB_WORKFLOW_MAX_DEPTH_EXCEEDED` |
| Compilation Gabarit Multi-Audience | Définition de template avec variables Jinja/Mustache, ancres humaines et concepts d'Ontologie | Vue Markdown interpolée/chunkée + JSON Schema Draft 2020-12 typé par l'Ontologie | `HTTP 422 ERR_VALIDATION_FAILED` si concept ontologique inconnu |
| Instanciation `Workflow Run` & `run-lock.json` récursif | `workflow_uri`, `workspace_id`, `nesting_depth <= 3` | Crée `WorkflowRunEntity` + `RunLockManifest` immuable avec `sub_workflow_locks` et `kb_snapshot_hash` | `HTTP 403 ERR_OBSERVER_MODE_READ_ONLY` si `OBSERVER` |

</frozen-after-approval>

## Code Map

- `infra/migrations/versions/0010_story_3_1_workflow_runs_triggers_and_run_lock.py` -- Révision Alembic ajoutant les colonnes `AD-18` à `workflow_definitions` et créant `workflow_triggers`, `workflow_runs` et `run_lock_manifests`.
- `packages/orcia-core/src/orcia_core/domain/exceptions.py` -- Nouveaux codes d'erreur RFC 9457 (`ERR_CRITICAL_WORKFLOW_REQUIRES_HUMAN_GATE`, `ERR_INTENTION_BEFORE_CODE_REQUIRED`, `ERR_SUB_WORKFLOW_MAX_DEPTH_EXCEEDED`, `ERR_SUB_WORKFLOW_CYCLE_DETECTED`).
- `packages/orcia-core/src/orcia_core/orchestration/models.py` -- Entités pures du domaine d'orchestration, du validateur DAG, des gabarits multi-audiences et des verrous récursifs `sub_workflow_locks`.
- `packages/orcia-core/src/orcia_core/orchestration/yaml_loader.py` & `yaml_validator.py` -- Parseur YAML/JSON conservant les numéros de lignes et validateur DAG (`Intention -> Code`, `HIGH_CRITICAL`, `SUB_WORKFLOW <= 3` sans cycle).
- `packages/orcia-core/src/orcia_core/orchestration/template_compiler.py` -- Compilateur dual de gabarits d'artefacts (Markdown Humain + JSON Schema typé par l'Ontologie).
- `packages/orcia-core/src/orcia_core/orchestration/run_lock_service.py` & `seeds.py` -- Service d'orchestration Story 3.1 épinglant récursivement `run-lock.json` (`sub_workflow_locks`, `kb_snapshot_hash`, 4 couches d'overrides) et instanciant les `Workflow Runs`.
- `packages/orcia-core/src/orcia_core/schemas/orchestration.py` -- Schémas Pydantic v2 OpenAPI 3.1.
- `apps/api/src/orcia_api/routers/orchestration.py` -- Routeur FastAPI `/api/v1/orchestration/*`.
- `infra/scripts/maintenance/06_backfill_workflow_orchestration_and_locks.py` -- Script de maintenance `--dry-run` / `--apply` pour l'Epic 3 (Story 3.1).
- `packages/ui/src/shell/WorkflowStudioSection.tsx` & `packages/ui/src/shell/CatalogExplorerPanel.tsx` -- Inspecteur Workflow-as-Code, gabarit multi-audience et `run-lock.json` récursif dans `@orcia/ui`.

## Tasks & Acceptance

**Execution:**
- [x] `infra/migrations/versions/0010_story_3_1_workflow_runs_triggers_and_run_lock.py` -- Créer la migration Alembic (upgrade/downgrade SQL pur) pour `workflow_definitions`, `workflow_triggers`, `workflow_runs` et `run_lock_manifests`.
- [x] `packages/orcia-core/src/orcia_core/domain/exceptions.py` -- Ajouter les exceptions `CriticalWorkflowRequiresHumanGateError`, `IntentionBeforeCodeRequiredError`, `SubWorkflowMaxDepthExceededError` et `SubWorkflowCycleDetectedError`.
- [x] `packages/orcia-core/src/orcia_core/orchestration/` -- Implémenter `models.py`, `yaml_loader.py`, `yaml_validator.py`, `template_compiler.py`, `run_lock_service.py`, `seeds.py` et `__init__.py`.
- [x] `packages/orcia-core/src/orcia_core/schemas/orchestration.py` & `apps/api/src/orcia_api/routers/orchestration.py` -- Exposer les endpoints REST de validation YAML, compilation de gabarit et instanciation de Run avec `run-lock.json` récursif, puis régénérer `packages/api-client`.
- [x] `infra/scripts/maintenance/06_backfill_workflow_orchestration_and_locks.py` -- Implémenter le script de backfill idempotent `--dry-run` / `--apply`.
- [x] `packages/ui/src/shell/WorkflowStudioSection.tsx` & `apps/web/src/` -- Exposer l'inspecteur Workflow-as-Code, gabarits multi-audiences et `sub_workflow_locks` avec traductions `fr`/`en`.
- [x] `tests/unit/test_workflow_as_code_and_run_lock.py` & `tests/integration/test_real_containers.py` -- Couvrir la matrice I/O en tests unitaires + `hypothesis` ($\ge 90\%$) et en tests d'intégration `testcontainers` PostgreSQL 18.

**Acceptance Criteria:**
- Given un manifeste YAML invalide ou violant `HIGH_CRITICAL + AUTONOMOUS_CONTRACT`, `Intention -> Code` ou `SUB_WORKFLOW <= 3`, when le validateur s'exécute, then il lève l'erreur RFC 9457 attendue avec le numéro de ligne exact.
- Given un Workflow valide avec sous-workflows imbriqués, when un Run est instancié, then `run-lock.json` fige de manière déterministe toutes les sources, les 4 couches de surcharges, le `kb_snapshot_hash` et l'arbre `sub_workflow_locks`.

## Implementation Notes

## Spec Change Log

## Review Triage Log

## Verification

**Commands:**
- `.venv/bin/ruff check . && .venv/bin/ruff format --check .` -- expected: `0 errors`
- `.venv/bin/mypy --strict packages/orcia-core apps/api apps/worker` -- expected: `Success: no issues found`
- `.venv/bin/pytest --cov=packages/orcia-core --cov-fail-under=90` -- expected: `passed, coverage >= 90%`
- `pnpm turbo run lint typecheck test` -- expected: `0 errors`
