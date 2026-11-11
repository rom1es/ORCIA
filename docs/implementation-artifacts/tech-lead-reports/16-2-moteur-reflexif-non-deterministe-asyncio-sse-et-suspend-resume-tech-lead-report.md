# Story 16.2 — Moteur `NonDeterministicReflexiveRuntime` (`asyncio` pur, Vrai Streaming SSE & *Suspend/Resume* `WritePreviewCard` survivant au `F5`)

- **Date** : 2026-11-11
- **Story / Clé Sprint** : `16-2-moteur-reflexif-non-deterministe-asyncio-sse-et-suspend-resume` (`Epic 16`)
- **Capacité(s)** : `CAP-160` — classification : `feature`
- **Auteur / Contexte** : Core Platform & AI Runtime Team — Implémentation du moteur d'orchestration réflexive non-déterministe `NonDeterministicReflexiveRuntime` en `asyncio` 100 % pur (zéro table système DBOS), aligné sur les 2 modes d'effort verrouillés (`Standard` vs `Approfondi`), avec diffusion temps réel SSE (`THOUGHT_DELTA`, `ANSWER_TOKEN_DELTA`, événements de trace chirurgicale `#Lstart-end`), séparation stricte `■ Arrêter` vs `Synthétiser maintenant`, délégation bornée (`max_delegation_depth = 1`), pause *Stateless Suspend/Resume* sur `WritePreviewCard` survivant au `F5` (PostgreSQL 18 `reflexive_execution_sessions` TTL `24h` + `SignedApprovalToken`) et archivage `ClaimCheckPointer` (`FR-1`, `FR-14`, `FR-20`, `FR-22`, `FR-24`, `FR-33`, `FR-36`, `AD-17`, `AD-19`, `AD-20`).
- **Commits associés** : *(à compléter en Section 3 après commit atomique)*

---

## 1. Analyse du Besoin & Étude d'Impact Tech Lead (Pré-Implémentation)

### 1.1 Contexte & Problématique
- **Opportunité métier & technique** : `Mon Assistant`, `Mes Agents` et les *Processus pilotés par l'objectif (adaptatifs)* nécessitent une boucle de raisonnement adaptative `Think -> Act -> Observe` à latence minimale (TTFT immédiat en streaming SSE, exploration chirurgicale `#Lstart-end` via `SurgicalExplorerPort`) sans payer le coût transactionnel de journalisation d'étapes DBOS à chaque micro-action de lecture.
- **Comportement attendu vs comportement actuel** :
  - Suite à la Story 16.1 (`5768a12`), ORCIA dispose du port `SurgicalExplorerPort` et des 4 primitives en lecture seule (`SurgicalContextExplorer`), mais pas encore du moteur `NonDeterministicReflexiveRuntime`, de la persistance de session légère `reflexive_execution_sessions`, ni des routes REST/SSE `/api/v1/executions/*`.
  - La Story 16.2 livre :
    1. Les ports hexagonaux purs `ReflexiveLlmPort`, `ReflexiveEventStreamPort`, `ReflexiveSessionStorePort` et `ReflexiveWriteGatePort` dans `orcia_core/ports/reflexive_runtime_ports.py`.
    2. Les schémas `ProcessOrchestrationType`, `ReflexiveRuntimeConfig` (unifié sur `Standard` `(4 tours, 8_000 tokens)` et `Approfondi` `(25 tours, 48_000 tokens)`), `TraceEventKind`, `AgentTraceEvent`, `ReflexiveTurnDecision`, `PendingWritePreviewSpec` et `ReflexiveSessionSnapshot` (TTL `24h`) dans `orcia_core/agents/reflexive_schemas.py`.
    3. Le moteur `NonDeterministicReflexiveRuntime` (`orcia_core/agents/reflexive_runtime.py`) en `asyncio` 100 % pur (zéro `@DBOS.workflow` / `@DBOS.step`), gérant `cancel_execution` (`0` appel LLM additionnel) vs `request_synthesize_now` (`force_final = True`), la délégation bornée à `max_delegation_depth = 1` sur budget de tokens partagé, le *Stateless Suspend/Resume* sur `WritePreviewCard` libérant immédiatement la coroutine ASGI, et l'archivage final `ClaimCheckStorageService.store_artifact()`.
    4. La migration PostgreSQL 18 `20261111_01_reflexive_execution_sessions.py`, les adaptateurs SQL (`SqlReflexiveSessionStore`), SSE/Redis (`ReflexiveEventStreamBroker`) et Write-Preview (`ConnectorReflexiveWriteGateAdapter`), ainsi que le routeur FastAPI `executions_trace.py` et le SDK OpenAPI 3.1 `@orcia/api-client` (`0-diff`).
- **Contraintes spécifiques de `ARCHITECTURE-SPINE.md` & `GEMINI.md`** :
  - **Isolation Hexagonale (`AD-19` Contrats 1..3 & `AD-20` Contrat 4)** : `orcia_core.ports` n'importe ni SDK externe ni modules de couche supérieure (`agents`, `workflows`, `storage`) ; `orcia_core` n'importe jamais `orcia_connectors` et ne contient aucun mot-clé métier interdit (`jira`, `confluence`, `git_branch`, `wsjf`, `rovo`, `copilot`, `safe`, `prd`).
  - **4 Invariants FastAPI/SSE (`GEMINI.md` §4)** : Zéro client HTTP/DB synchrone dans `routers/` (`TID251`), vrai streaming SSE `AsyncIterator` préservant intégralement `\n` et l'indentation Markdown (**zéro `.split(" ")`**), agnostisme fournisseur/langue, zéro `except Exception:` silencieux.
  - **Sécurité RBAC & Gouvernance d'Écriture** : Rejet `HTTP 403 ERR_OBSERVER_MODE_READ_ONLY` sur toutes les mutations (`POST`), et vérification cryptographique `SignedApprovalToken` (`HMAC-SHA256` + `payload_sha256`) avant toute exécution d'écriture externe lors de `approve-write`.

### 1.2 Exploration, Analyse d'Impact GitNexus, Factorisation & Dette Technique
- **Analyse d'Impact GitNexus (`gitnexus_query`, `gitnexus_context`, `gitnexus_impact` sur `repo: "/home/romain/Documents/Projects/ORCIA"`)** :
  - `gitnexus_query("ClaimCheckStorageService SurgicalExplorerPort SignedApprovalToken ObserverModeReadOnlyError StreamingResponse")` : identifie les flux `run_bounded_workflow_v2` / `apply_hitl_signal_to_run` consommant `ClaimCheckStorageService` et `verify_signed_approval_token`.
  - `gitnexus_context({name: "ClaimCheckStorageService"})` : confirme la signature synchrone sans I/O bloquante `store_artifact(*, run_id, step_id, iteration, content, mime_type) -> ClaimCheckPointer` (`s3://orcia-artifacts/...`, `sha256` 64 car.).
  - `gitnexus_impact({target: "SurgicalExplorerPort", direction: "upstream"})` : `impactedCount = 2`, risque `LOW` (`SurgicalContextExplorer`, `orcia_core/ports/__init__.py`).
  - `gitnexus_impact({target: "SignedApprovalToken", direction: "upstream"})` : `impactedCount = 11`, risque `MEDIUM` (`orcia_connectors/protocol.py` + 5 connecteurs d'entreprise + `bounded_workflow_v2.py`) — nous réutilisons `WritePreviewCard`, `SignedApprovalToken` et `verify_signed_approval_token` sans modifier leurs signatures dans `orcia_connectors/reflexive_write_gate.py`.
  - `gitnexus_impact({target: "ObserverModeReadOnlyError", direction: "upstream"})` : `impactedCount = 87`, risque `MEDIUM` — pattern standardisé (`user.platform_role in ("OBSERVER", "BU_DIRECTOR")` ou `access_mode == "READ_ONLY_OBSERVER"` $\rightarrow$ `403 ERR_OBSERVER_MODE_READ_ONLY`).
- **Exploration & Chiffres Clés (Base de Données & Volumétrie)** :
  - Dernière révision Alembic : `20261108_0910` (`20261108_0910_declarative_packs_and_workflows_v2.py`). La nouvelle migration `20261111_01_reflexive_execution_sessions.py` s'enchaînera proprement avec `down_revision = "20261108_0910"`.
  - Contrôle de volumétrie : `apps/api/src/orcia_api/dependencies/workspace_and_packs.py` fait déjà `178` lignes ; pour respecter strictement le plafond `< 350` lignes sur chaque fichier, nous créons un module dédié `apps/api/src/orcia_api/dependencies/reflexive_execution.py` ré-exporté par `dependencies/__init__.py`.
- **Opportunités de Factorisation & Résorption de Dette Technique Naissante** :
  - Factorisation de la résolution du budget `(max_turns, max_budget_tokens)` depuis `EffortLevel` directement sur `ReflexiveRuntimeConfig` afin que `Mon Assistant`, `Mes Agents` et `ProcessExecutionDispatcher` (Story 16.3) partagent une vérité unique.
  - Découpage propre de `packages/orcia-core/src/orcia_core/agents/` en modules courts et cohésifs (`reflexive_schemas.py`, `reflexive_runtime.py`, `llm_adapter.py`, `_internal/sql_reflexive_sessions.py`, `_internal/redis_event_stream.py`), chacun `< 350` lignes.
  - Aucun ticket de dette technique additionnel requis.

---

## 2. Plan d'Implémentation

### 2.1 Schéma de Données & Migrations Alembic (`infra/migrations/versions/20261111_01_reflexive_execution_sessions.py`)
- Révision `20261111_01` (`down_revision = "20261108_0910"`), SQL brut via `op.execute(sa.text(...))` (zéro import ORM) :
  - Table `reflexive_execution_sessions` :
    - `execution_id VARCHAR(128) PRIMARY KEY` (UUIDv7 string compatible)
    - `workspace_id VARCHAR(128) NULL`
    - `actor_slug VARCHAR(128) NOT NULL`
    - `orchestration_mode VARCHAR(32) NOT NULL DEFAULT 'non_deterministic'`
    - `effort_level VARCHAR(32) NOT NULL DEFAULT 'default'`
    - `status VARCHAR(32) NOT NULL` (`RUNNING`, `WAITING_WRITE_PREVIEW`, `COMPLETED`, `CANCELLED`, `FAILED`)
    - `snapshot_jsonb JSONB NOT NULL DEFAULT '{}'::jsonb`
    - `created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()`
    - `updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()`
    - `expires_at TIMESTAMPTZ NOT NULL` (TTL `24h`)
  - Index composite B-Tree `ix_reflexive_exec_sessions_ws_status_updated` sur `(workspace_id, status, updated_at DESC)` pour les requêtes de réhydratation et supervision `< 5 ms`.
  - Réversibilité complète vérifiée par test d'intégration (`downgrade` puis `upgrade head`).
  - Ajout explicite de `"reflexive_execution_sessions"` dans `ORDERED_MUTABLE_TABLES_TO_CLEAR` de `infra/scripts/maintenance/09_reset_db_first_boot.py`.

### 2.2 Noyau Métier Hexagonal & Connecteurs (`packages/orcia-core/`, `packages/orcia-connectors/`)
- **`pyproject.toml` & `tests/unit/core/test_core_domain_isolation.py`** :
  - Ajout de `agents` au sommet de `AD-19 Contract 2` (`"bootstrap | orchestration | packs | agents"`).
  - Ajout de `ORCIA_CORE_SRC / "agents"` dans `isolated_packages` de `test_core_domain_isolation.py`.
- **`packages/orcia-core/src/orcia_core/ports/reflexive_runtime_ports.py`** (ré-exporté dans `orcia_core/ports/__init__.py`) :
  - Modèles de contrat purs (`ConfigDict(extra="forbid")`, zéro dépendance vers `agents`/`workflows`/`connectors`) : `TraceEventKind`, `AgentTraceEvent`, `PendingWritePreviewSpec`, `ReflexiveWriteApprovalInput`, `ReflexiveLlmChunk`, `ReflexiveTurnInput`, `ReflexiveTurnDecision`.
  - Protocoles `@runtime_checkable` : `ReflexiveLlmPort`, `ReflexiveEventStreamPort`, `ReflexiveSessionStorePort`, `ReflexiveWriteGatePort`.
- **`packages/orcia-core/src/orcia_core/agents/reflexive_schemas.py`** :
  - `ProcessOrchestrationType(StrEnum)` (`NON_DETERMINISTIC`, `DETERMINISTIC_DBOS`).
  - `ReflexiveRuntimeConfig` aligné sur `EffortLevel` (`Standard` $\rightarrow$ `4` tours / `8_000` tokens ; `Approfondi` $\rightarrow$ `25` tours / `48_000` tokens).
  - `ReflexiveScratchpadEntry`, `ReflexiveSessionSnapshot` (incluant `artifact_pointer: ClaimCheckPointer | None` et `expires_at_utc` à `+24h`).
- **`packages/orcia-core/src/orcia_core/agents/reflexive_runtime.py`** :
  - `NonDeterministicReflexiveRuntime` en `asyncio` 100 % pur (zéro DBOS) :
    - Boucle `Think -> Act -> Observe` invoquant `SurgicalExplorerPort`, publiant `AgentTraceEvent` et chunks `THOUGHT_DELTA` / `ANSWER_TOKEN_DELTA` sans altérer `\n` ni l'indentation.
    - `cancel_execution(execution_id)` (`status="CANCELLED"`, `LOOP_CANCELLED`, `0` appel LLM supplémentaire) vs `request_synthesize_now(execution_id)` (`force_final=True`).
    - Délégation bornée (`max_delegation_depth = 1`) : un sous-agent délégué s'exécute avec `allow_sub_agent_delegation=False` et débite le budget `tokens_used` du parent.
    - Pause *Stateless Suspend/Resume* sur `propose_external_write_preview` : appelle `ReflexiveWriteGatePort.prepare_write_preview(...)`, émet `WRITE_PREVIEW_REQUESTED`, persiste `ReflexiveSessionSnapshot` (`WAITING_WRITE_PREVIEW`, TTL `24h`) et **libère immédiatement la coroutine**.
    - `resume_after_write_decision(...)` : recharge le snapshot, vérifie l'expiration TTL `24h`, exécute l'écriture signée (`SignedApprovalToken`) si `approved=True` ou consigne le motif de refus humain dans `scratchpad` si `approved=False`, puis reprend à `turn + 1` jusqu'à `COMPLETED` + `ClaimCheckStorageService.store_artifact()`.
- **Adaptateurs d'infrastructure (`orcia_core/agents/_internal/` & `orcia_connectors/`)** :
  - `orcia_core/agents/llm_adapter.py` : `GatewayReflexiveLlmAdapter` branché sur `LlmGatewayPort` (`DeterministicCassetteLLM` / `LiteLLMAdapter`) avec découpage de flux préservant `\n` et l'indentation Markdown.
  - `orcia_core/agents/_internal/sql_reflexive_sessions.py` : `SqlReflexiveSessionStore` sur PostgreSQL 18 (`AsyncSession` via `session_maker` + repli propre en mémoire uniquement hors DB en test unitaire pur).
  - `orcia_core/agents/_internal/redis_event_stream.py` : `ReflexiveEventStreamBroker` (`AsyncIterator` temps réel + relecture d'historique + publication Redis Pub/Sub optionnelle).
  - `packages/orcia-connectors/src/orcia_connectors/reflexive_write_gate.py` : `ConnectorReflexiveWriteGateAdapter` préparant `WritePreviewCard` et imposant `verify_signed_approval_token` avant `execute_write`.

### 2.3 Couche Backend API, Sécurité & Contrats (`apps/api/`, `packages/api-client/`)
- **`apps/api/src/orcia_api/routers/executions_trace.py`** (injecté via `dependencies/reflexive_execution.py` et monté dans `main.py`) :
  - Garde `READ_ONLY_OBSERVER` (`403 ERR_OBSERVER_MODE_READ_ONLY`) sur les 4 routes `POST`.
  - `POST /api/v1/executions/reflexive` : démarre (en direct ou tâche de fond `run_in_background`) une exécution réflexive.
  - `GET /api/v1/executions/{execution_id}` : retourne le `ReflexiveSessionSnapshot` persisté (survie au `F5`).
  - `GET /api/v1/executions/{execution_id}/trace-stream` : `async def` retournant un `StreamingResponse` SSE `text/event-stream` réel via `AsyncIterator`.
  - `POST /api/v1/executions/{execution_id}/synthesize-now` : active `force_final = True` (et finalise si en cours / reprend).
  - `POST /api/v1/executions/{execution_id}/cancel` : annule immédiatement (`CANCELLED`, `LOOP_CANCELLED`).
  - `POST /api/v1/executions/{execution_id}/approve-write` : valide (avec vérification ou émission gouvernée `SignedApprovalToken`) ou refuse une `WritePreviewCard` et reprend la boucle.
- **Schémas OpenAPI 3.1 & SDK TypeScript (`0-diff`)** :
  - Enrichissement de `apps/api/src/orcia_api/schemas/reflexive_execution.py`, export `.venv/bin/python scripts/export_openapi.py` (`--check` `0-diff`) et enrichissement de `packages/api-client/src/domains/reflexiveExecution.ts`.
  - Mise à jour de `CAP-160` dans `docs/product/capabilities.yaml`.

### 2.4 Interface Utilisateur & Expérience (`apps/web/`)
- Les composants visuels `<AgentExecutionTrace />` et `<SourceLineInspectorDrawer />` relèvent de la Story 16.4 ; le client typé `@orcia/api-client` expose dès la Story 16.2 toutes les méthodes (`startReflexiveExecution`, `getReflexiveExecution`, `synthesizeReflexiveExecutionNow`, `cancelReflexiveExecution`, `decideReflexiveWritePreview`, URL SSE `/trace-stream`).
- Enrichissement de `apps/web/e2e/00-stack-smoke.spec.ts` et vérification E2E complète de `00-stack-smoke.spec.ts` + `02-assistant-streaming-and-folders.spec.ts`.

### 2.5 Analyse d'Impact sur la Pyramide des Tests (`AD-17` — Couches 1 à 5 + Sécurité, Obligatoire)
- **Couche 1a & 1b (Unitaires Python & TS)** : `tests/unit/core/test_non_deterministic_reflexive_runtime.py`, `tests/unit/core/test_core_domain_isolation.py`, `tests/unit/test_codebase_architectural_anti_patterns_audit.py` + `pnpm turbo run lint typecheck test`.
- **Couche 2 (Intégration Verticale `HTTP FastAPI ➔ PostgreSQL 18`)** : `tests/integration/api/test_story_16_2_reflexive_runtime_and_sse_postgres18.py` sur conteneur réel `pgvector/pgvector:pg18` (testant `upgrade`/`downgrade`/`upgrade` de `20261111_01`, `SELECT` SQL direct sur `reflexive_execution_sessions`, survie `F5`, reprise `approve-write` $\rightarrow$ `COMPLETED` + `ClaimCheckPointer`, SSE `/trace-stream`, `synthesize-now`, `cancel` et `403 ERR_OBSERVER_MODE_READ_ONLY`).
- **Couche 3 (Contrats OpenAPI 3.1 `0-diff`, `lint-imports` & `lint_spine.py`)** : `export_openapi.py --check`, `lint-imports` (`5/5`), `lint_spine.py` (`0 findings`).
- **Couche 4 & Sécurité** : Zéro appel externe payant (`DeterministicCassetteLLM`), rejet `403 ERR_POLICY_DENIED` sur `SignedApprovalToken` falsifié et `403 ERR_OBSERVER_MODE_READ_ONLY` en mode observateur.
- **Couche 5 (Playwright E2E Réel Bi-Serveur)** : Exécution réelle sur `e2e/00-stack-smoke.spec.ts` et `e2e/02-assistant-streaming-and-folders.spec.ts` (`--project=desktop-cockpit`).

---

## 3. Bilan des Modifications & Résultats (Post-Implémentation)

### 3.1 Fichiers Développés & Modifiés

| Fichier | Action & Volumétrie | Responsabilité |
| :--- | :--- | :--- |
| `packages/orcia-core/src/orcia_core/ports/reflexive_runtime_ports.py` & `ports/__init__.py` | Création (`250` l.) | Ports hexagonaux purs (`@runtime_checkable` `Protocol`) : `ReflexiveLlmPort`, `ReflexiveSessionStorePort`, `ReflexiveEventStreamPort`, `ReflexiveWriteGatePort`, `AgentTraceEvent`, `TraceEventKind` (`13` événements typés) et `PendingWritePreviewSpec` (`0` import SDK/framework). |
| `packages/orcia-core/src/orcia_core/agents/errors.py` | Création (`58` l.) | Exceptions métier du contexte borné `agents` (`ReflexiveSessionExpiredError`, `ReflexiveInvalidStateError` héritant d'`OrciaDomainError`). |
| `packages/orcia-core/src/orcia_core/agents/reflexive_schemas.py` | Création (`224` l.) | Schémas Pydantic v2 (`ProcessOrchestrationType`, `ReflexiveRuntimeConfig` avec 2 modes verrouillés `Standard` `(4 tours, 8 000 tokens)` et `Approfondi` `(25 tours, 48 000 tokens)`, `ReflexiveScratchpadEntry`, `ReflexiveSessionSnapshot` à TTL `24 h`). |
| `packages/orcia-core/src/orcia_core/agents/_runtime_helpers.py` | Création (`206` l.) | Constructeurs purs de snapshot initial, sous-session déléguée (`delegation_depth = 1`, sous-délégation désactivée), entrées de tour et conversion des `SurgicalObservation`. |
| `packages/orcia-core/src/orcia_core/agents/_runtime_turn_actions.py` | Création (`313` l.) | Streaming réel des deltas `thought_delta` / `answer_token_delta` préservant `\n`, exécution chirurgicale, suspension sans état `WAITING_WRITE_PREVIEW`, application du `WritePreviewCard` (`SignedApprovalToken` ou refus humain), et archivage `ClaimCheckPointer` (`SHA-256`). |
| `packages/orcia-core/src/orcia_core/agents/reflexive_runtime.py` | Création (`343` l.) | Moteur pur `asyncio` `NonDeterministicReflexiveRuntime` (`0` décorateur/table DBOS), séparation stricte `cancel_execution` (`■ Arrêter`, `0` tour LLM supplémentaire) vs `request_synthesize_now` (`Synthétiser maintenant` $\rightarrow$ `force_final = True`), délégation bornée `depth <= 1` à budget partagé, et `resume_after_write_decision`. |
| `packages/orcia-core/src/orcia_core/agents/llm_adapter.py` | Création (`195` l.) | Adaptateur agnostique `GatewayReflexiveLlmAdapter` branché sur `LlmGatewayPort` (`LiteLLMAdapter` / `DeterministicCassetteLLM`, découpage par tranches de caractères préservant chaque `\n` et indentation). |
| `packages/orcia-core/src/orcia_core/agents/_internal/sql_reflexive_sessions.py` | Création (`163` l.) | Adaptateur PostgreSQL 18 `SqlReflexiveSessionStore` (`UUIDv7` `id` + `execution_id`, `INSERT ... ON CONFLICT (execution_id) DO UPDATE`, survie au `F5`). |
| `packages/orcia-core/src/orcia_core/agents/_internal/redis_event_stream.py` & `agents/__init__.py` | Création (`145` l. / `66` l.) | Adaptateur `ReflexiveEventStreamBroker` (Redis 7.4 `RPUSH` + `PUBLISH` avec TTL `24 h` et repli `asyncio.Queue` sans duplication lors d'un `WAITING_WRITE_PREVIEW` suivi d'un `COMPLETED`). |
| `packages/orcia-connectors/src/orcia_connectors/reflexive_write_gate.py` & `__init__.py` | Création (`161` l.) | Adaptateur `ConnectorReflexiveWriteGateAdapter` (`OrciaConnectorProtocol` + vérification cryptographique `HMAC-SHA256` `SignedApprovalToken` + `payload_sha256` avant toute écriture externe). |
| `infra/migrations/versions/20261111_01_reflexive_execution_sessions.py` & `09_reset_db_first_boot.py` | Création (`62` l.) & Modif. | Migration Alembic SQL brute réversible (`upgrade` / `downgrade` vers `20261108_0910`, PK `UUIDv7`, index workspace/statut et expiration) + ajout dans `ORDERED_MUTABLE_TABLES_TO_CLEAR`. |
| `apps/api/src/orcia_api/dependencies/reflexive_execution.py`, `errors/registry.py`, `schemas/reflexive_execution.py`, `routers/executions_trace.py` & `main.py` | Création (`111` l. / `255` l. / `330` l.) & Modif. | Injection Composition Root `Depends`, enregistrement RFC 9457 (`409` / `410`), et 6 routes REST/SSE `/api/v1/executions/*` avec garde `403 ERR_OBSERVER_MODE_READ_ONLY` sur toutes les mutations. |
| `packages/api-client/src/generated/reflexive_execution.d.ts` & `src/domains/reflexiveExecution.ts` | Régénération (`0-diff`) & Modif. (`113` l.) | Régénération automatique OpenAPI 3.1 et méthodes typées SDK (`startReflexiveExecution`, `getReflexiveExecution`, `buildReflexiveTraceStreamUrl`, `synthesizeReflexiveExecutionNow`, `cancelReflexiveExecution`, `decideReflexiveWritePreview`). |
| `tests/unit/core/test_non_deterministic_reflexive_runtime.py`, `tests/unit/core/test_reflexive_llm_stream_and_gate_adapters.py` & `tests/integration/api/test_story_16_2_reflexive_runtime_and_sse_postgres18.py` | Création | Suites TDD Couche 1a (`9` tests unitaires réflexifs + isolation AST/domaine) et Couche 2 (`2` scénarios complets sur `pgvector/pgvector:pg18` + `redis:7.4.2-alpine`). |
| `pyproject.toml`, `docs/product/capabilities.yaml`, `docs/implementation-artifacts/sprint-status.yaml` & `tech-lead-reports/README.md` | Modification | Contrat `AD-19` (`agents`), mise à jour `CAP-160` (`executions_trace.py`, `20261111_01`, tests), passage `16-2` à `done` et `16-3` à `ready-for-dev`. |

### 3.2 Résultats Chiffrés, Métriques & Qualité
- **Volumétrie maîtrisée (`< 350` lignes par fichier source)** : `reflexive_runtime_ports.py` (`250` l.), `reflexive_schemas.py` (`224` l.), `_runtime_helpers.py` (`206` l.), `_runtime_turn_actions.py` (`313` l.), `reflexive_runtime.py` (`343` l.), `llm_adapter.py` (`195` l.), `sql_reflexive_sessions.py` (`163` l.), `redis_event_stream.py` (`145` l.), `reflexive_write_gate.py` (`161` l.), `schemas/reflexive_execution.py` (`255` l.), `routers/executions_trace.py` (`330` l.).
- **Couverture unitaire Story 16.2** : **`93.48 %`** (`>= 90 %` requis ; `reflexive_runtime_ports.py` : `100 %`, `reflexive_write_gate.py` : `100 %`, `agents/errors.py` : `100 %`, `reflexive_schemas.py` : `98 %`, `llm_adapter.py` : `94 %`).
- **Analyse statique, typage strict & frontières modulaires** :
  - `.venv/bin/ruff check .` & `.venv/bin/ruff format --check .` : **`0` erreur** (`689` fichiers conformes).
  - `.venv/bin/mypy --strict packages/orcia-core packages/orcia-connectors apps/api apps/worker` : **`0` erreur** sur `287` fichiers sources.
  - `.venv/bin/lint-imports` : **`5 contracts kept, 0 broken`** (`AD-19` & `AD-20`).
  - `.venv/bin/python scripts/export_openapi.py --check` : **`0-diff`**.
  - `lint_spine.py` : **`0` finding** (`ok: true`).

### 3.3 Validation & Procédure de Test sur Toute la Pyramide (`AD-17` + 5 Garde-Fous de Câblage Vertical)
- **Couche 1a & 1b (Unitaires Python & TypeScript/Vitest)** :
  - Python : **`17 passed`** (`93.48 %` de couverture) sur `test_core_domain_isolation.py`, `test_codebase_architectural_anti_patterns_audit.py`, `test_non_deterministic_reflexive_runtime.py` et `test_reflexive_llm_stream_and_gate_adapters.py` (zéro import DBOS dans `orcia_core.agents`, séparation `cancel_execution` vs `request_synthesize_now`, délégation bornée `depth <= 1` à budget partagé, `0` coroutine bloquée en RAM sur `WAITING_WRITE_PREVIEW`, rejet `PolicyDeniedError` sur `SignedApprovalToken` falsifié et expiration TTL `24 h`).
  - TypeScript Monorepo (`pnpm turbo run lint typecheck test`) : **`9/9` tâches vertes** (`134 passed` au total : `73` `@orcia/ui`, `8` `@orcia/api-client`, `53` `@orcia/web`).
- **Couche 2 (Intégration Verticale `HTTP FastAPI ➔ PostgreSQL 18 + Redis 7.4`)** :
  - `.venv/bin/pytest tests/integration/api/test_story_16_2_reflexive_runtime_and_sse_postgres18.py -v` : **`2 passed` (`12.41s`)** contre de vrais conteneurs éphémères `pgvector/pgvector:pg18` et `redis:7.4.2-alpine`, vérifiant la réversibilité Alembic (`upgrade head` $\rightarrow$ `downgrade 20261108_0910` $\rightarrow$ `upgrade head`), le `SELECT` SQL direct sur `reflexive_execution_sessions` (`Garde-Fou #2`), la survie au `F5` sur une nouvelle instance `create_app()`, le rejet `HTTP 403 ERR_POLICY_DENIED` sur jeton falsifié, la reprise `approve-write` $\rightarrow$ `COMPLETED` avec `ClaimCheckPointer`, le flux SSE réel `/trace-stream` préservant `\n` + historique Redis 7.4, la remise à zéro Jour 0 (`09_reset_db_first_boot.py`), et le rejet `HTTP 403 ERR_OBSERVER_MODE_READ_ONLY` en mode observateur.
- **Couche 5 (Playwright E2E Réel Bi-Serveur)** :
  - `pnpm --filter @orcia/web exec playwright test e2e/00-stack-smoke.spec.ts e2e/02-assistant-streaming-and-folders.spec.ts --project=desktop-cockpit` : **`6 passed, 1 skipped (38.9s)`** sur la pile réelle bi-serveur (PostgreSQL 18 + Redis 7.4 + FastAPI + Vite + Chromium).
- **Audit GitNexus Post-Implémentation (`Garde-Fou #1`)** :
  - `npx gitnexus analyze` (`21,545` nœuds, `36,837` arêtes).
  - `gitnexus_impact({target: "SqlReflexiveSessionStore", direction: "upstream"})` : appelant actif hors `tests/` confirmé via `orcia_core.agents` $\rightarrow$ `apps/api/src/orcia_api/dependencies/reflexive_execution.py` (`0` adaptateur SQL orphelin).
  - `pnpm site:sync && pnpm site:check` & `check_implementation_docs.py` : **`0` erreur**.
