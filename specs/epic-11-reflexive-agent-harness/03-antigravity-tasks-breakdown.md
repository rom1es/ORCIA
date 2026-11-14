---
document_type: ANTIGRAVITY_IMPLEMENTATION_TASKS
epic_id: EPIC-11
version: "2.0.0"
execution_engine: "Antigravity / bmad-build"
---

# Plan d'Exécution des Tâches pour Antigravity — Epic 11 v2 (`TASK-11-01` à `TASK-11-06`)

Ce plan met en œuvre le moteur réflexif **non-déterministe (sans DBOS)** pour **Mon Assistant**, les **Agents** et les **Processus Non-Déterministes**, tout en le connectant proprement aux **Processus Déterministes (DBOS)**.

---

## TASK-11-01 : Implémentation des 4 Primitives d'Exploration Chirurgicale dans `packages/orcia-connectors`
* **Cible :** `packages/orcia-connectors/src/orcia_connectors/surgical.py`
* **Actions :**
  1. Créer `SurgicalContextExplorer` implémentant les 4 primitives en lecture seule (`check_resource_state`, `outline_resource_structure`, `search_workspace_snippets`, `inspect_resource_lines` borné à $250$ lignes max avec numérotation `#L1-200` et badge `M↓`, `Y`, `TS`, `PY`, `DOC`).
  2. Vérifier systématiquement le `ScopedExecutionToken` auprès du *Permission Broker*.
* **Tests obligatoires :** `tests/unit/connectors/test_surgical_context_explorer.py`.

---

## TASK-11-02 : Moteur `NonDeterministicReflexiveRuntime` (`asyncio` pur, sans DBOS) dans `packages/orcia-core`
* **Cible :** `packages/orcia-core/src/orcia_core/agents/reflexive_schemas.py`, `packages/orcia-core/src/orcia_core/agents/reflexive_runtime.py`
* **Actions :**
  1. Créer `ProcessOrchestrationType` (`NON_DETERMINISTIC` vs `DETERMINISTIC_DBOS`), `ReflexiveRuntimeConfig`, `AgentTraceEvent` et `ReflexiveTurnDecision`.
  2. Implémenter `NonDeterministicReflexiveRuntime.execute_reflexive_loop()` en **`asyncio` pur (aucun décorateur `@DBOS.workflow` ni `@DBOS.step`)** pour orchestrer de manière non-déterministe :
     * **Mon Assistant** (`allow_sub_agent_delegation=False`).
     * **Les Agents LLM** (`allow_sub_agent_delegation=False`).
     * **Les Processus Non-Déterministes** (`allow_sub_agent_delegation=True`, permettant au planificateur de déléguer dynamiquement des sous-objectifs aux agents du Pack).
  3. Intégrer l'interception `WritePreviewCard` via signalisation Redis asynchrone et l'archivage final unique dans SeaweedFS (`ClaimCheckPointer`).
* **Tests obligatoires :**
  * `tests/unit/core/test_non_deterministic_reflexive_runtime.py` : Vérifie que la boucle `Think -> Check -> Analyzed #L1-200 -> Final Answer` s'exécute sans toucher aux tables système de DBOS et respecte la *Write-Preview Gate*.

---

## TASK-11-03 : Aiguilleur `ProcessExecutionDispatcher` (Processus Non-Déterministe vs Processus Déterministe DBOS)
* **Cible :** `packages/orcia-core/src/orcia_core/workflows/dispatcher.py`, `packages/orcia-core/src/orcia_core/workflows/schemas_v2.py`
* **Actions :**
  1. Ajouter le champ `orchestration_type: ProcessOrchestrationType = ProcessOrchestrationType.NON_DETERMINISTIC` (ou `DETERMINISTIC_DBOS`) sur `WorkflowDefinitionV2`.
  2. Implémenter `ProcessExecutionDispatcher` :
     * Si `NON_DETERMINISTIC` : lance `NonDeterministicReflexiveRuntime` puis exécute le `GatePipelineExecutor` sur le livrable produit.
     * Si `DETERMINISTIC_DBOS` : lance le workflow durable DBOS (`run_bounded_workflow_v2`). Lorsqu'une étape DBOS est de type `AGENT_EXECUTOR`, l'étape DBOS invoque `NonDeterministicReflexiveRuntime` en interne et ne persiste dans PostgreSQL que le `ClaimCheckPointer` final de l'étape.
* **Tests obligatoires :**
  * `tests/unit/core/test_process_orchestration_dispatcher.py` : Vérifie l'exécution d'un processus en mode `NON_DETERMINISTIC` (sans DBOS) et d'un processus en mode `DETERMINISTIC_DBOS` (avec DBOS).

---

## TASK-11-04 : Streaming SSE Redis des Événements de Trace & Route d'Inspection de Lignes (`apps/api`)
* **Cible :** `apps/api/src/orcia_api/routers/executions_trace.py`, `apps/api/src/orcia_api/routers/sources.py`
* **Actions :**
  1. Créer l'endpoint SSE `GET /api/v1/executions/{execution_id}/trace-stream` diffusant en direct les `AgentTraceEvent` (`Thought`, `Check`, `Analyzed #L1-200`, `Delegated to @Agent`, `Working`).
  2. Créer `POST /api/v1/executions/{execution_id}/early-stop` et `GET /api/v1/sources/inspect-lines?uri=...&start=...&end=...`.
  3. Régénérer le client TypeScript `packages/api-client`.
* **Tests obligatoires :** `tests/integration/api/test_trace_sse_and_line_inspector.py`.

---

## TASK-11-05 : Composant UI `<AgentExecutionTrace />` & Tiroir `<SourceLineInspectorDrawer />` (`packages/ui` & `apps/web`)
* **Cible :** `packages/ui/src/components/agent-execution-trace.tsx`, `apps/web/src/features/sources/SourceLineInspectorDrawer.tsx`
* **Actions :**
  1. Créer `<AgentExecutionTrace />` reproduisant le visuel d'Antigravity (`Checking ... ⌄`, `Thought for Xs ›` dépliable, `Check ... ›`, `Analyzed <Badge> <fichier> #L1-200` cliquable, `Delegated to @Agent ⌄`, `◌ Working...`).
  2. Créer `<SourceLineInspectorDrawer />` ouvrant et surlignant exactement les lignes `#Lstart-end` cliquées.

---

## TASK-11-06 : Sélecteur de Mode d'Orchestration dans « Mes Processus » & Intégration dans « Mon Assistant » / « Mes Agents »
* **Cible :** `apps/web/src/features/processes/`, `apps/web/src/features/assistant/`, `apps/web/src/features/agents/`, `packs/`
* **Actions :**
  1. Dans la création/édition de processus (`Mes Processus`), ajouter le sélecteur en haut de formulaire : **`⚡ Processus Non-Déterministe (Dynamique / Agentique — Sans DBOS)`** vs **`🛡️ Processus Déterministe (Machine à états durable — DBOS)`**.
  2. Intégrer `<AgentExecutionTrace />` et `<SourceLineInspectorDrawer />` dans **Mon Assistant**, dans le **Banc de Test des Agents** et dans le suivi d'exécution des **Processus** (non-déterministes comme déterministes).
  3. Configurer dans `packs/orcia-docs/` le processus de génération documentaire en mode `NON_DETERMINISTIC` et dans `packs/sdlc/` les processus du cycle SAFe avec le choix explicite du mode.
