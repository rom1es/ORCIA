---
document_type: ANTIGRAVITY_IMPLEMENTATION_TASKS
epic_id: EPIC-16
version: "2.1.0"
execution_engine: "Antigravity / 1 Subagent per User Story + Tech Lead Report + E2E + Git Commit"
---

# Plan d'Exécution Séquentiel par User Story — Epic 16 (`Story 16.1` à `Story 16.4`)

Chaque User Story est exécutée par **un sous-agent dédié**, précédée de son **Rapport Tech Lead** (`docs/implementation-artifacts/tech-lead-reports/{story-key}-tech-lead-report.md`), validée sur les **5 couches de tests incluant les tests E2E Playwright**, et clôturée par un **commit Git atomique**.

---

## Story 16.1 (`TASK-16-01`) : Ports Hexagonaux & 4 Primitives d'Exploration Chirurgicale + Endpoint `/api/v1/sources/inspect-lines`
- **Clé Sprint** : `16-1-quatre-primitives-exploration-chirurgicale-et-ports-hexagonaux`
- **Livrables** :
  1. `packages/orcia-core/src/orcia_core/ports/surgical_explorer_port.py` (`SurgicalExplorerPort`, modèles de tranches `#Lstart-end` bornées à `250` lignes, badges `M↓`, `Y`, `TS`, `PY`, `DOC`).
  2. `packages/orcia-connectors/src/orcia_connectors/surgical.py` (`SurgicalContextExplorer` : `check_resource_state`, `outline_resource_structure`, `search_workspace_snippets`, `inspect_resource_lines` avec garde RBAC `READ_SOURCE` et protection Path Traversal).
  3. `apps/api/src/orcia_api/schemas/reflexive_execution.py` + `apps/api/src/orcia_api/routers/sources_surgical.py` (`GET /api/v1/sources/inspect-lines`, rejet `READ_ONLY` / masquage gouverné `READ_SOURCE`) + régénération `@orcia/api-client` (`0-diff`).
  4. Tests unitaires, intégration PG18, sécurité anti-*Confused Deputy* et revue/exécution E2E Playwright + commit Git US `16.1`.

---

## Story 16.2 (`TASK-16-02` & `TASK-16-04`) : Moteur `NonDeterministicReflexiveRuntime` (`asyncio` pur, SSE temps réel & *Suspend/Resume* `WritePreviewCard`)
- **Clé Sprint** : `16-2-moteur-reflexif-non-deterministe-asyncio-sse-et-suspend-resume`
- **Livrables** :
  1. `packages/orcia-core/src/orcia_core/agents/reflexive_schemas.py` & `reflexive_runtime.py` + mise à jour `pyproject.toml` (`agents` dans `import-linter`).
  2. Boucle `Think -> Act -> Observe` 100 % `asyncio` (zéro table système DBOS touchée), 2 modes `Standard` / `Approfondi` (`EffortLevel`), vrai streaming SSE (`thinking_delta`, `token_delta`, événements de trace), `max_delegation_depth = 1`, *Stateless Suspend/Resume* sur `WritePreviewCard` survivant au `F5` (24h TTL) et archivage `ClaimCheckStorageService` + Outbox.
  3. `apps/api/src/orcia_api/routers/executions_trace.py` : `POST /api/v1/executions/reflexive`, `GET /api/v1/executions/{execution_id}`, `GET /api/v1/executions/{execution_id}/trace-stream` (SSE réel), `POST /api/v1/executions/{execution_id}/synthesize-now`, `POST /api/v1/executions/{execution_id}/cancel`, `POST /api/v1/executions/{execution_id}/approve-write` + régénération `@orcia/api-client`.
  4. Tests unitaires, intégration PG18 + Redis + SeaweedFS, revue/exécution E2E Playwright (`02-assistant-streaming-and-folders.spec.ts` + flux SSE) + commit Git US `16.2`.

---

## Story 16.3 (`TASK-16-03` & `TASK-16-06a`) : Double Mode de Processus (« Piloté par l'objectif » vs « Piloté par les jalons »), `ProcessExecutionDispatcher` & Packs
- **Clé Sprint** : `16-3-double-mode-processus-objectif-vs-jalons-dispatcher-et-packs`
- **Livrables** :
  1. Découpage modulaire préalable de `WorkflowFiveBlocksCanvas.tsx` (`< 350` lignes par fichier).
  2. `BoundedWorkflowLauncherPort` dans `orcia_core/ports/`, enrichissement rétrocompatible de `WorkflowDefinitionV2` (`orchestration_type`, `reflexive_objective`, `allowed_delegate_agents`, `reflexive_config`), `ProcessExecutionDispatcher` (`orcia_core/workflows/dispatcher.py`) + encapsulation de `NonDeterministicReflexiveRuntime` dans les sous-étapes `agent_executor` de `bounded_workflow_v2.py`.
  3. Mise à jour de `packs/orcia-docs/workflows/wf-generate-orcia-documentation.yaml` (`non_deterministic`) et `packs/sdlc/workflows/*.yaml` (`deterministic_dbos` commutable).
  4. Sélecteur métier dans l'Atelier 5 Blocs (`Processus piloté par l'objectif (adaptatif)` vs `Processus piloté par les jalons (étapes garanties)`, parité `fr.ts`/`en.ts`, zéro terme technique) et badges sur `ProcessesHubPage.tsx`.
  5. Tests 5 couches + E2E `/processes` et Studio mis à jour et exécutés + commit Git US `16.3`.

---

## Story 16.4 (`TASK-16-05` & `TASK-16-06b`) : Composants `@orcia/ui` `<AgentExecutionTrace />` & `<SourceLineInspectorDrawer />` et Câblage Bout-en-Bout
- **Clé Sprint** : `16-4-trace-execution-ui-et-inspecteur-chirurgical-lignes-bout-en-bout`
- **Livrables** :
  1. `packages/ui/src/components/AgentExecutionTrace.tsx` & `SourceLineInspectorDrawer.tsx` (`tokens.css`, `<OrciaIcon />`, Radix `Dialog`/`Sheet` fermable par `Échap`, bilingue `fr`/`en`, bouton `Synthétiser maintenant` distinct de `■ Arrêter`, état `🔒 Extrait protégé`, test anti-jargon technique).
  2. Intégration unifiée sans doublon dans `Mon Assistant` (`/assistant`, relié à `[S1]`), le Banc de Test de `Mes Agents` (`/agents`) et `InteractiveRunDrawer.tsx` de `Mes Processus` (`/processes`).
  3. Finalisation de `CAP-160` (`status: live`, `verification: runtime`), `pnpm site:sync && pnpm site:check`, spec E2E dédiée `apps/web/e2e/12-epic16-reflexive-trace-and-line-inspector.spec.ts` + passage complet des E2E impactés + commit Git US `16.4`.
