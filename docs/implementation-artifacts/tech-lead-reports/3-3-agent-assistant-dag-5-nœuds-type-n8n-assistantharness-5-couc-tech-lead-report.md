# Rapport Tech Lead — Story 3.3 : Agent Assistant (DAG 5 Nœuds Type n8n), `AssistantHarness` à 5 Couches & Composition Conversationnelle de Workflows

- **Clé de Story** : `3-3-agent-assistant-dag-5-nœuds-type-n8n-assistantharness-5-couc`
- **Action Item résolu** : `DEC-CTX-01` (`ContextSourcePort` & `VectorStorePort` + point d'extension `orcia.indexers`)
- **Épopée** : `Epic 3 — Orchestration Durable de Workflows, Tableau Noir Immuable & Co-Design Humain/Agent`
- **Statut** : `done`
- **Date** : `2026-10-28`

---

## 1. Analyse du Besoin & Étude d'Impact Tech Lead

### 1.1 Contexte & Problématique Métier
La **Story 3.3** livre le workflow système `orcia://system/workflows/assistant-agent` conçu comme un graphe dirigé déterministe à **5 nœuds** (inspiré de `n8n` / `Flowise`, `AD-15`, `AR-4`), ainsi que son constructeur de prompts immuable à **5 couches** (`AssistantHarness`), l'adaptation sémantique au **Profil Humain** (`EXECUTIVE`, `PM`, `ARCHITECT`, `SECOPS`, `FR-1`, `UX-DR12`), et le **Compositeur Conversationnel de Workflows** (`FR-11`, `UX-DR15`, `UJ-10`). Conformément à l'**Avenant A2 (`AD-20`)** et à l'action item **`DEC-CTX-01`**, l'Assistant ne lit jamais de fichiers Markdown locaux et interroge le contexte fédéré exclusivement via `ContextSourcePort` et `VectorStorePort`, sans aucun vocabulaire SDLC codé en dur dans `orcia-core`.

### 1.2 Analyse d'Impact GitNexus (`repo: "ORCIA"`)
- **Symboles analysés via `gitnexus_context` & `gitnexus_impact`** :
  - `CockpitFeaturePanel` (`apps/web/src/features/cockpit/index.tsx`) : appelé par `ModuleWorkspaceView` (`18` flux d'exécution UI), risque maîtrisé.
  - `buildCockpitWorkflowPreviewGraph` (`apps/web/src/features/cockpit/index.tsx`) : enrichi de 2 à **5 nœuds** (`intent-router` $\rightarrow$ `query-planner` $\rightarrow$ `parallel-fan-out` $\rightarrow$ `critical-triage` $\rightarrow$ `profile-synthesizer`) et 4 arêtes.
  - `WorkflowOrchestrationSetupService` & `DurableOrchestrationEngine` (`packages/orcia-core/src/orcia_core/orchestration/`) : réutilisés par `AssistantAgentService.save_and_launch_workflow` pour enregistrer et exécuter réellement les étapes via `orcia.step_executors`.

### 1.3 Opportunités de Factorisation & Contrôle de Volumétrie (`< 400` lignes)
- Découpage de l'implémentation de l'Assistant en 3 modules spécialisés sous `packages/orcia-core/src/orcia_core/orchestration/` :
  - `assistant_harness.py` (`307` lignes) : assembleur déterministe des 5 couches de prompt et adaptation au Profil Humain.
  - `assistant_composer.py` (`226` lignes) : modèles `@xyflow/react` (`XyFlowNodeSpec`, `XyFlowEdgeSpec`, `AssistantWorkflowProposal`) et résolution de blueprints via `orcia.assistant_templates`.
  - `assistant_agent.py` (`374` lignes) : moteur d'exécution du DAG à 5 nœuds, streaming SSE (`< 1.5 s`) et `save_and_launch_workflow` réutilisant `_run_llm_sync` de `step_executors.py`.
- Aucune nouvelle dette technique identifiée ; `DEC-CTX-01` est intégralement soldé.

---

## 2. Plan d'Implémentation

### 2.1 Base de Données & Migrations Alembic
- Aucune nouvelle table requise : `save_and_launch_workflow` persiste les définitions, runs, exécutions d'étapes et snapshots immuables via l'infrastructure `WorkflowOrchestrationSetupService` et `DurableOrchestrationEngine` (`0001..0014`).

### 2.2 Noyau Hexagonal (`orcia_kernel`, `orcia_core`, `orcia_pack_sdlc`)
- **`packages/orcia-kernel/src/orcia_kernel/context_ports.py`** :
  - `ContextSourcePort` & `ContextSliceRecord`, `VectorStorePort` & `VectorSearchHitRecord`.
  - Registre dynamique `orcia.indexers` (`IndexerRegimeDescriptor`, `register_indexer_regime`, `get_registered_indexer_regime`, `list_registered_indexer_regimes`).
  - Registre `orcia.assistant_templates` (`AssistantWorkflowTemplatePort`, `AssistantWorkflowBlueprint`).
- **`packages/orcia-core/src/orcia_core/rag/context_adapters.py`** :
  - `HybridRagVectorStoreAdapter` et `CatalogAndBlackboardContextSourceAdapter`.
- **`packages/orcia-core/src/orcia_core/orchestration/{assistant_harness,assistant_composer,assistant_agent}.py`** :
  - DAG à 5 nœuds, `AssistantHarness` à 5 couches (avec refus constitutionnel `HUMAN_ANCHOR_WRITE_REFUSAL` sur `human_authored_required: true`), et exécution réelle `save_and_launch_workflow`.
- **`packages/orcia-pack-sdlc/src/orcia_pack_sdlc/formats_and_indexers.py`** :
  - Enregistrement de `CODE_AST_GRAPH`, `JIRA_HYBRID`, `TRIPARTITE_GRAPH` dans `orcia.indexers` et patron `SdlcDocVsCodeAuditAssistantTemplate` (`UJ-10`).

### 2.3 Backend FastAPI & SDK OpenAPI 3.1
- **`apps/api/src/orcia_api/schemas/assistant.py`** & **`apps/api/src/orcia_api/routers/assistant.py`** :
  - `POST /api/v1/assistant/chat`, `POST /api/v1/assistant/chat/stream` (`text/event-stream`), et `POST /api/v1/assistant/workflows/save-and-launch` (rejetant `READ_ONLY_OBSERVER` avec `403 ERR_OBSERVER_MODE_READ_ONLY`).
- Régénération sans dérive (`0-diff`) du SDK `@orcia/api-client` via `scripts/export_openapi.py`.

### 2.4 Interface SPA Vite + TanStack Router (`Direction C`)
- **`apps/web/src/features/cockpit/index.tsx`** : graphe `@xyflow/react` complet des 5 nœuds du DAG `assistant-agent`.

---

## 3. Bilan des Modifications & Résultats

### 3.1 Fichiers Créés ou Modifiés
| Fichier | Action | Rôle |
| --- | --- | --- |
| `packages/orcia-kernel/src/orcia_kernel/context_ports.py` | Créé | Ports `ContextSourcePort`, `VectorStorePort`, registres `orcia.indexers` et `orcia.assistant_templates` (`DEC-CTX-01`) |
| `packages/orcia-core/src/orcia_core/rag/context_adapters.py` | Créé | Adaptateurs concrets `HybridRagVectorStoreAdapter` et `CatalogAndBlackboardContextSourceAdapter` |
| `packages/orcia-core/src/orcia_core/orchestration/assistant_harness.py` | Créé | Constructeur immuable à 5 couches et adaptation aux Profils Humains (`AD-15`, `FR-1`, `FR-4`) |
| `packages/orcia-core/src/orcia_core/orchestration/assistant_composer.py` | Créé | Compositeur `@xyflow/react` + YAML sans vocabulaire SDLC (`FR-11`, `UX-DR15`, `AD-20`) |
| `packages/orcia-core/src/orcia_core/orchestration/assistant_agent.py` | Créé | Service d'exécution du DAG à 5 nœuds, SSE streaming (`< 1.5 s`) et `save_and_launch_workflow` |
| `packages/orcia-pack-sdlc/src/orcia_pack_sdlc/formats_and_indexers.py` | Modifié | Enregistrement des indexeurs SDLC et du patron `SdlcDocVsCodeAuditAssistantTemplate` (`UJ-10`) |
| `apps/api/src/orcia_api/schemas/assistant.py` | Créé | Schémas de transport HTTP Pydantic v2 de l'Assistant |
| `apps/api/src/orcia_api/routers/assistant.py` | Créé | Endpoints REST et SSE `/api/v1/assistant/*` |
| `apps/web/src/features/cockpit/index.tsx` | Modifié | Graphe `@xyflow/react` à 5 nœuds du workflow `assistant-agent` |
| `tests/unit/test_story_3_3_assistant_agent_5_nodes_and_context_ports.py` | Créé | Suite complète de tests unitaires, conformité API/SSE et `core-without-sdlc` |

### 3.2 Métriques & Validation des 5 Couches de Tests (`AD-17`)
- **Couverture unitaire globale** : **`92.07%`** (`>= 90%` requis ; `assistant_harness.py: 100%`, `context_adapters.py: 100%`, `formats_and_indexers.py: 100%`, `assistant_agent.py: 96%`, `assistant_composer.py: 95%`).
- **Frontières modulaires (`AD-19` & `AD-20`)** : `.venv/bin/lint-imports` $\rightarrow$ **`4 kept, 0 broken`** ; `0` terme SDLC dans `assistant_harness.py`, `assistant_agent.py` et `assistant_composer.py`.
- **Qualité statique Python & TypeScript** : `ruff check`, `ruff format --check`, `mypy --strict` (`137` fichiers, `0` erreur) et `pnpm turbo run lint typecheck test` (`9/9` tâches vertes).
- **Latence premier token SSE (`NFR-PERF-1`)** : `< 5 ms` mesuré en test (`<< 1500 ms` requis).
