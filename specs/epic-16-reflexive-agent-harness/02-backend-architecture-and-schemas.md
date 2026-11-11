---
document_type: BACKEND_TECHNICAL_SPECIFICATION
epic_id: EPIC-16
version: "2.1.0"
target_packages:
  - "packages/orcia-core/src/orcia_core/ports/"
  - "packages/orcia-core/src/orcia_core/agents/"
  - "packages/orcia-core/src/orcia_core/workflows/"
  - "packages/orcia-connectors/src/orcia_connectors/"
  - "apps/api/src/orcia_api/routers/"
  - "apps/api/src/orcia_api/schemas/"
---

# Architecture Backend (v2.1) — Isolation Hexagonale (`AD-19`/`AD-20`), Vrai Streaming SSE & *Stateless Suspend/Resume*

## 1. Contrats Hexagonaux Inviolables (`lint-imports` & `test_core_domain_isolation.py`)
1. **`orcia_core` n'importe jamais `orcia_connectors`** (`AD-20 Contract 4` dans `pyproject.toml`).
   - `orcia_core/ports/surgical_explorer_port.py` définit `SurgicalExplorerPort` (Protocol) et les DTOs de domaine agnostiques (`SurgicalObservation`, `SurgicalLineSlice`).
   - `orcia_core/ports/bounded_workflow_port.py` définit `BoundedWorkflowLauncherPort` (Protocol) pour invoquer le moteur par jalons sans importer `orcia_connectors.bounded_workflow_v2`.
   - `pyproject.toml` déclare `agents` dans `AD-19 Contract 2` (`bootstrap | orchestration | packs | agents`).
2. **Zéro mot-clé métier SDLC dans `orcia_core`** : aucun terme `jira`, `confluence`, `git_branch`, `wsjf`, `rovo`, `copilot`, `safe`, `prd` dans `orcia_core/agents/`, `orcia_core/workflows/` ni `orcia_core/ports/`.
3. **Alignement avec les types existants d'Epic 14/15** :
   - Réutilisation de `EffortLevel` (`packages/orcia-core/src/orcia_core/workflows/schemas_v2.py`) mappé sur les **2 modes UI** :
     - `Standard` (`EffortLevel.DEFAULT` / `EffortLevel.LOW` / `EffortLevel.MEDIUM`) $\rightarrow$ `(4 tours, 8_000 tokens)`.
     - `Approfondi` (`EffortLevel.HIGH`) $\rightarrow$ `(25 tours, 48_000 tokens)`.
   - Réutilisation de `ClaimCheckStorageService.store_artifact()` (`packages/orcia-core/src/orcia_core/storage/claim_check.py`) et `GatePipelineExecutor.execute_pipeline()` (`packages/orcia-core/src/orcia_core/workflows/gates/pipeline.py`).

## 2. Schémas du Domaine (`packages/orcia-core/src/orcia_core/agents/reflexive_schemas.py`)
- `ProcessOrchestrationType(StrEnum)` :
  - `NON_DETERMINISTIC = "non_deterministic"` (*Processus piloté par l'objectif (adaptatif)*)
  - `DETERMINISTIC_DBOS = "deterministic_dbos"` (*Processus piloté par les jalons (étapes garanties)* — défaut rétrocompatible sur `WorkflowDefinitionV2`)
- `SurgicalPrimitiveName(StrEnum)` : `check_resource_state`, `outline_resource_structure`, `search_workspace_snippets`, `inspect_resource_lines` (`<= 250` lignes par appel).
- `TraceEventKind(StrEnum)` :
  - `GROUP_HEADER`, `THOUGHT_DELTA`, `THOUGHT_COMPLETED`, `CHECK_EXECUTED`, `FILE_ANALYZED`, `AGENT_DELEGATED`, `WRITE_PREVIEW_REQUESTED`, `ANSWER_TOKEN_DELTA`, `STATUS_WORKING`, `LOOP_COMPLETED`, `LOOP_CANCELLED`.
- `ReflexiveSessionSnapshot(BaseModel)` : état sérialisable léger (`execution_id`, `actor_slug`, `turn_index`, `cumulative_tokens`, `scratchpad`, `trace_events`, `pending_write_preview`, `status`, `expires_at_utc`) persisté lors d'une pause `WAITING_WRITE_PREVIEW` ou à la complétion pour survivre à tout rafraîchissement `F5` et redémarrage serveur sans maintenir de coroutine ASGI bloquée en mémoire.

## 3. Sécurité RBAC `READ_SOURCE` & Anti-Boucle de Délégation
- `SurgicalContextExplorer` (`packages/orcia-connectors/src/orcia_connectors/surgical.py`) et `GET /api/v1/sources/inspect-lines` valident :
  1. L'absence de traversée de chemin (`..`, schémas `file://` arbitraires hors espace/packs autorisés) et le garde-fou SSRF.
  2. La permission `READ_SOURCE` de l'utilisateur courant via le *Permission Broker* : si refusée, retourne un descripteur gouverné `redacted_reason = "READ_SOURCE_REQUIRED"` (affiché `🔒 Extrait protégé` côté UI, `0` fuite de contenu).
- En mode `NON_DETERMINISTIC` avec délégation (`allow_sub_agent_delegation=True`), `max_delegation_depth = 1` : un sous-agent délégué s'exécute toujours avec `allow_sub_agent_delegation=False` et partage le compteur `cumulative_tokens` du parent.
