---
story_key: 3-3-agent-assistant-dag-5-nœuds-type-n8n-assistantharness-5-couc
status: done
epic: epic-3
decisions:
  - AD-15
  - AD-20
  - AR-4
  - DEC-CTX-01
---

# Specification — Story 3.3 : Agent Assistant (DAG 5 Nœuds Type n8n), `AssistantHarness` à 5 Couches & Composition Conversationnelle de Workflows

## 1. Objectif & Périmètre
Implémenter le workflow système `orcia://system/workflows/assistant-agent` sous forme de graphe dirigé déterministe à **5 nœuds** (`AD-15`, `AR-4`), le constructeur de prompts immuable à **5 couches `AssistantHarness`**, les ports génériques de contexte et d'indexation **`DEC-CTX-01`** (`ContextSourcePort`, `VectorStorePort`, `orcia.indexers`), et le compositeur conversationnel de workflows (`@xyflow/react` + YAML + exécution réelle 1-clic via `orcia.step_executors`).

## 2. Architecture & Composants Livrés
- **Noyau (`packages/orcia-kernel/src/orcia_kernel/context_ports.py`)** :
  - `ContextSourcePort` & `ContextSliceRecord` (`JSON_PAYLOAD | CAS_OBJECT | KB_DOCUMENT | BLACKBOARD_SNAPSHOT | CATALOG_ITEM | PERMISSION_POLICY`).
  - `VectorStorePort` & `VectorSearchHitRecord` (`halfvec(1024)` + BM25 RRF).
  - Registre dynamique `orcia.indexers` (`IndexerRegimeDescriptor`, `register_indexer_regime`, `get_registered_indexer_regime`, `list_registered_indexer_regimes`).
  - Registre de patrons de workflows `orcia.assistant_templates` (`AssistantWorkflowTemplatePort`, `AssistantWorkflowBlueprint`).
- **Domaine (`packages/orcia-core/src/orcia_core/orchestration/`)** :
  - `assistant_harness.py` : assemblage déterministe des 5 couches (`1_CONSTITUTIONAL_IMMUTABLE`, `2_ONTOLOGY_AND_AXIOMS_L1_L4`, `3_HUMAN_PROFILE_ADAPTATION`, `4_FEDERATED_CONTEXT_FANOUT`, `5_CONVERSATIONAL_INTENT_AND_COMPOSER`), refus constitutionnel strict (`FR-4`) et adaptation sémantique multi-profils (`EXECUTIVE`, `PM`, `ARCHITECT`, `SECOPS`).
  - `assistant_composer.py` : génération et modification conversationnelle de graphes `@xyflow/react` v12 (`XyFlowNodeSpec`, `XyFlowEdgeSpec`) et de manifestes YAML `Workflow-as-Code`, sans aucun vocabulaire SDLC dans `orcia-core` (`AD-20`).
  - `assistant_agent.py` : exécution du DAG à 5 nœuds (`1_INTENT_ROUTER` $\rightarrow$ `2_QUERY_PLANNER_AND_ONTOLOGY_EXPANSION` $\rightarrow$ `3_PARALLEL_FAN_OUT` $\rightarrow$ `4_CRITICAL_TRIAGE_AND_AXIOM_VERIFICATION` $\rightarrow$ `5_PROFILE_ADAPTIVE_SYNTHESIZER`), streaming SSE (`< 1.5 s`, `NFR-PERF-1`) et `save_and_launch_workflow`.
- **Pack SDLC (`packages/orcia-pack-sdlc/src/orcia_pack_sdlc/formats_and_indexers.py`)** :
  - Enregistrement des régimes `CODE_AST_GRAPH`, `JIRA_HYBRID` et `TRIPARTITE_GRAPH` dans `orcia.indexers`.
  - Patron `SdlcDocVsCodeAuditAssistantTemplate` pour le parcours d'Arthur (`UJ-10`).
- **API & Frontend (`apps/api/src/orcia_api/routers/assistant.py`, `apps/web/src/features/cockpit/index.tsx`)** :
  - `POST /api/v1/assistant/chat`, `POST /api/v1/assistant/chat/stream` (SSE), et `POST /api/v1/assistant/workflows/save-and-launch`.
