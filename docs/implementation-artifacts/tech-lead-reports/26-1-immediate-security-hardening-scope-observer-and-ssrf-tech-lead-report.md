# Story 26.1 — Immediate Security Hardening: Pre-Stream Scope & Observer Guards, Server-Side `READ_SOURCE` / `CONFIDENTIAL_RESTRICTED`, Layer 1 Immutability, Env-Var SSRF + DNS Pinning & Secret Hygiene

- **Date**: 2026-11-21
- **Story / Sprint Key**: `26-1-immediate-security-hardening-scope-observer-and-ssrf` (`Epic 26` / Lot 1 — Security)
- **Capabilities**: `CAP-022`, `CAP-070`, `CAP-071`, `CAP-072`, `CAP-073`, `CAP-074` — classification: `feature` (`D9`: downgrade `CAP-022`, `CAP-070`, `CAP-072` to `verification: api` in `docs/product/capabilities.yaml`)
- **Author / Context**: Immediate security remediation for `"Mon Assistant"` (`H-06`, `H-07`, `H-08`, `H-15`, `H-16`, `H-17`, `H-30` prod `assert`) aligned with `AD-19`, `AD-21` Rule 7, `AD-24` Rule 8, `AD-25`, and `D3 + R8`, `D9` from `epic-26-decisions-grill-2026-11-21.md`.
- **Associated Commits**: pending (`feat/epic-26-assistant-harness-debt-remediation`)

---

## 1. Requirements & Tech Lead Impact Analysis (Analyse du Besoin)

### 1.1 Context & Problem Statement
- **Pre-stream `READ_ONLY_OBSERVER` & Workspace Scope IDOR (`H-06`, `H-07`):**
  - `POST /api/v1/assistant/three-speed/stream` checks `user.platform_role == "OBSERVER"` inside `stream_three_speed_turn_sse` after `StreamingResponse` opens HTTP `200` headers, causing mid-stream ASGI exceptions instead of pre-stream HTTP `403 ERR_OBSERVER_MODE_READ_ONLY`.
  - `X-Orcia-Access-Mode: READ_ONLY_OBSERVER` and `MatrixPermissionEvaluator.resolve_workspace_access` are missing or bypassed across `assistant_workspace.py`, `assistant_workspace_governance.py`, `assistant_workspace_citations.py`, `assistant_workspace_folders.py` (only 2 of 6 routes guarded, and `_enforce_workspace_guard` skips checks for slugs or unknown workspaces), and `assistant.py` (`resolve_workspace_access` return value discarded on `/chat` and `/chat/stream`; no guard on `/workflows/save-and-launch`).
  - `assistant_governance.py` authorizes `TEAM_LEAD` / `ARCHITECT` / `TECH_LEAD` / `EXECUTIVE` / `SECOPS` globally rather than scoping edits to the caller's authorized workspaces/teams.
  - `assistant_llm_resolver.py:97` passes hardcoded UUID `"0195f000-0000-7000-8000-000000000301"` instead of the resolved workspace UUID (while preserving `GLOBAL` fallback from Story `25.5`).
- **Client-Supplied `READ_SOURCE` & Missing `CONFIDENTIAL_RESTRICTED` Masking (`H-08`):**
  - `VerifyAndFilterCitationsRequest` (`assistant_citations_and_folders.py:102`) accepts `reader_allowed_source_uris` from the client, allowing a caller to spoof source read authorizations.
  - `AssistantAgentService` (`assistant_agent.py`) and `assistant_llm_prompts.py` do not filter `READ_SOURCE` or mask `CONFIDENTIAL_RESTRICTED` context slices, RAG hits, folder notes, or ontology concepts server-side prior to prompt assembly.
- **Layer 1 Override & Prompt Injection (`H-15`):**
  - `build_assistant_system_instructions` honors `system_instructions_override` unconditionally; only `agents_and_skills.py` legitimately uses this override.
  - `ConversationTurnMessageItem` accepts `role: Literal["user", "assistant", "tool"]` from untrusted client payloads, and `build_multi_turn_messages` passes `role="tool"` through to the LLM.
  - User prompt, `workspace_instructions`, `personal_instructions`, and `folder_pinned_notes` are not neutralized against `[LAYER_*]` / `[CONSTITUTIONAL_*]` tag spoofing or wrapped in untrusted delimiters.
- **Partial SSRF & Unpinned DNS (`H-16`, `D3 + R8`):**
  - `is_safe_llm_endpoint_url` (`assistant_llm_providers.py`, `ai_models_crypto.py`, `remote_test_bench.py`) lacks `ORCIA_LLM_ALLOWED_PRIVATE_HOSTS` policy enforcement, `ORCIA_ENV in ("local", "test")` gating for `localhost`, permanent blocks on internal ORCIA ports (`5432`, `5433`, `6379`, `8333`, `9333`, `9000`), and `socket.getaddrinfo` DNS resolution pinning against DNS rebinding.
  - `assistant_llm_resolver.py` does not re-validate PG18-stored endpoints across all resolution branches before connecting.
- **Bootstrap Setup State Exposure, Secret Hygiene & Production `assert` (`H-17`, `H-30`):**
  - `GET /api/v1/bootstrap/platform-setup-state` returns full `PlatformSetupStateResponse` unauthenticated, exposing admin emails, org units, workspaces, and LLM tiers (`H-17`).
  - `platform_setup_snapshot` does not explicitly strip `apiKey` / credential keys on ingress/snapshot storage.
  - `_REGISTERED_SECRET_VALUES` in `ecs_formatter.py` is an unbounded `set[str]`, and `str(exc)` in `assistant_background_turns.py:320` and RFC 9457 error responses does not pass through `scrub_sensitive_text`.
  - `assistant_three_speed_router.py:325` contains `assert det_ms < MAX_NODES_1_TO_4_DETERMINISTIC_MS` in production code (`H-30`).

### 1.2 Exploration, GitNexus Impact Analysis, Factorization & Technical Debt
- **GitNexus Impact Analysis (`repo: /home/romain/Documents/Projects/ORCIA`):**
  - `resolve_workspace_access` (`packages/orcia-core/src/orcia_core/permissions/evaluator.py`): `impactedCount = 121`, `risk = CRITICAL` (`114` direct callers, `10` affected processes across `Routers`, `Kernel`, `Orchestration`). We will preserve `MatrixPermissionEvaluator.resolve_workspace_access` unchanged and invoke it from a shared assistant FastAPI guard helper.
  - `MatrixPermissionEvaluator`: `epistemic = exact`, supports both UUID and slug lookup via `get_workspace(workspace_id_or_slug)`.
  - `is_safe_llm_endpoint_url`, `build_assistant_system_instructions`, `_enforce_workspace_guard`: index was 1 commit behind `HEAD`; verified all callers via `git grep` across `apps/`, `packages/`, and `tests/`.
  - `agents_and_skills.py`: lines 169 and 317 invoke `invoke_configured_llm_for_assistant_turn(..., system_instructions_override=...)`; must retain identical behavior via an explicit internal `allow_system_override=True` gate unreachable from `/api/v1/assistant/*` routes.
- **Factorization & File-Size Control (`<= 300` lines per touched harness file):**
  - Centralize pre-stream workspace access, slug/UUID resolution, observer checks, and server-side `READ_SOURCE` resolution in `apps/api/src/orcia_api/dependencies/_assistant_guards.py` (`<= 200` L).
  - Centralize SSRF URL validation, `ORCIA_LLM_ALLOWED_PRIVATE_HOSTS` allowlist parsing, and async `getaddrinfo` DNS resolution pinning in `packages/orcia-core/src/orcia_core/orchestration/ssrf_guard.py` (`<= 260` L), reused by `ai_models_crypto.py`, `assistant_llm_providers.py`, `assistant_llm_resolver.py`, and `remote_test_bench.py`.
  - Split oversized touched harness files (`assistant_workspace.py`, `assistant_llm_providers.py`, `assistant_llm_prompts.py`, `assistant_background_turns.py`, `assistant_governance.py`, `assistant_three_speed_router.py`, `assistant_agent.py`, `assistant_harness.py`, `ecs_formatter.py`, `assistant_citations_and_folders.py`, `bootstrap_accostage.py`, `agents_and_skills.py`) into focused modules each `<= 300` lines.

---

## 2. Implementation Plan (Plan d'Implémentation)

### 2.1 Database Schema & Alembic Migrations
- No Alembic schema migration is required for Story `26.1` (schema changes begin in Lot 3 / `26.0` ERD).

### 2.2 Hexagonal Core, Orchestration & Observability (`packages/orcia-core/`)
- `packages/orcia-core/src/orcia_core/orchestration/ssrf_guard.py` (new, `<= 260` L):
  - Parse `ORCIA_LLM_ALLOWED_PRIVATE_HOSTS` (hostnames, `.local`/`.internal` suffixes, CIDRs) and `ORCIA_ENV`.
  - Enforce permanent non-overridable blocks on cloud metadata (`169.254.0.0/16`, `169.254.169.254`, `fe80::/10`, `100.100.100.200`, `metadata.google.internal`, `metadata.goog`, `metadata.azure.com`), unspecified/multicast, and internal ORCIA ports (`5432`, `5433`, `6379`, `8333`, `9333`, `9000`).
  - Permit `localhost` / loopback only when `ORCIA_ENV in ("local", "test")` or explicitly allowlisted in `ORCIA_LLM_ALLOWED_PRIVATE_HOSTS`.
  - Provide async `resolve_and_pin_safe_endpoint_url(...)` using `loop.getaddrinfo` to validate all resolved IPs against the SSRF policy and produce a pinned IP target + `Host` header + TLS `sni_hostname` extension for `httpx`.
- `packages/orcia-core/src/orcia_core/orchestration/ai_models_crypto.py` & `ai_models_discovery.py` & `ai_models_connection.py` & `remote_test_bench.py`:
  - Delegate URL & DNS-pinned connection validation to `ssrf_guard.py` (`<= 300` L each).
- `packages/orcia-core/src/orcia_core/orchestration/assistant_governance.py` (+ split models/studio helpers `<= 300` L each):
  - Scope Mode A workspace settings and Mode B studio overrides to authorized workspace/team scopes.
- `packages/orcia-core/src/orcia_core/orchestration/assistant_three_speed_router.py` (+ split models `<= 300` L each):
  - Delete production `assert det_ms < MAX_NODES_1_TO_4_DETERMINISTIC_MS`.
- `packages/orcia-core/src/orcia_core/orchestration/assistant_agent.py` & `assistant_harness.py` & `assistant_citations_and_v5_guard.py`:
  - Add server-side `READ_SOURCE` & `CONFIDENTIAL_RESTRICTED` filtering to `AssistantAgentService.run_conversation_turn` and `AssistantHarness` sanitization of `[LAYER_*]` / `[CONSTITUTIONAL_*]` tags; split files `<= 300` L.
- `packages/orcia-core/src/orcia_core/observability/_internal/ecs_formatter.py` (+ split normalizer `<= 300` L each):
  - Bound `_REGISTERED_SECRET_VALUES` with an `OrderedDict` LRU capped at `2048` entries.
- `packages/orcia-core/src/orcia_core/bootstrap/_internal/sql_platform_setup_store.py`:
  - Strip raw credential keys (`apiKey`, `api_key`, `secret`, `token`, `password`, etc.) from `llm_tiers` before storing or returning `PlatformSetupSnapshotRecord`.

### 2.3 Backend API, Security & Contracts (`apps/api/`, `packages/api-client/`)
- `apps/api/src/orcia_api/dependencies/_assistant_guards.py` (new, `<= 220` L):
  - `enforce_assistant_workspace_guard(request, user, workspace_id, require_write=..., persona_key=...)`: syncs evaluator topology from PG18 (`sync_evaluator_topology_from_pg`), checks `READ_ONLY_OBSERVER` (`X-Orcia-Access-Mode`, role, persona) and `evaluator.resolve_workspace_access(user, workspace_id)` for both UUIDs and slugs, raising RFC 9457 `403` before any response stream starts.
  - `resolve_server_allowed_source_uris(...)`: computes `READ_SOURCE` permissions and `CONFIDENTIAL_RESTRICTED` denials server-side via `MatrixPermissionEvaluator` and `PermissionBrokerService`.
- Wire `enforce_assistant_workspace_guard` into all routes of `assistant_workspace.py`, `assistant_workspace_governance.py`, `assistant_workspace_citations.py`, `assistant_workspace_folders.py`, and `assistant.py`.
- `apps/api/src/orcia_api/routers/assistant_llm_prompts.py` & `assistant_llm_bridge.py` & `assistant_llm_providers.py` & `assistant_llm_resolver.py` & `assistant_background_turns.py`:
  - Gate `system_instructions_override` behind `allow_system_override: bool = False` (set `True` only by `agents_and_skills.py`); restrict history `role` strictly to `user | assistant`; escape/delimit `[LAYER_*]` & `[CONSTITUTIONAL_*]` tags; resolve real workspace `scope_id` in `assistant_llm_resolver.py` (preserving Story `25.5` `GLOBAL` fallback); enforce DNS-pinned SSRF on Hub + runtime; scrub `str(exc)` via `scrub_sensitive_text`.
- `apps/api/src/orcia_api/routers/bootstrap_accostage.py` & `apps/api/src/orcia_api/openapi_security.py` & `apps/api/src/orcia_api/schemas/bootstrap.py`:
  - Allow unauthenticated `GET /api/v1/bootstrap/platform-setup-state` returning **only** `{is_initialized, step}`; gate full snapshot view (and `PUT`) to `PLATFORM_ADMIN` and strip raw provider credentials from `platform_setup_snapshot`.
- `apps/api/src/orcia_api/schemas/assistant_citations_and_folders.py` & `apps/api/src/orcia_api/schemas/assistant.py`:
  - Remove `reader_allowed_source_uris` from `VerifyAndFilterCitationsRequest`; restrict `ConversationTurnMessageItem.role` to `Literal["user", "assistant"]`; regenerate OpenAPI 3.1 SDK (`0-diff`).
- `infra/scripts/capabilities_registry.py` & `docs/product/capabilities.yaml` & `infra/scripts/e2e/e2e_stack_config.py`:
  - Add `"api"` to `VERIFICATIONS` and set `CAP-022`, `CAP-070`, `CAP-072` to `verification: api`; configure `ORCIA_LLM_ALLOWED_PRIVATE_HOSTS` in `e2e_stack_config.py` for E2E `16` local mock LLM.

### 2.4 Frontend SPA (`apps/web/`)
- `apps/web/src/components/platformSetupHydration.ts`:
  - Tolerate HTTP `403` on `getPlatformSetupState()` when authenticated non-admin users hydrate the SPA (`E2E 14`/`15`), while still failing fast on server errors.
- Regenerate `packages/api-client/openapi.json`, `packages/api-client/src/generated/schema.ts`, and domain shards (`0-diff`).

### 2.5 Test Pyramid Impact (`AD-17` Layers 1–5 + Security)
- **Layer 1a/1b (Unit Python + Vitest):** Unit tests for `ssrf_guard`, DNS rebinding prevention, bounded `_REGISTERED_SECRET_VALUES`, prompt tag sanitization, `agents_and_skills.py` non-regression, and Vitest hydration resilience.
- **Layer 2 (PG18 Integration):** Real `create_app()` vertical tests against PostgreSQL 18 verifying real workspace `scope_id` LLM resolution, cross-workspace IDOR rejection on slugs/UUIDs, and `GET /bootstrap/platform-setup-state` Day-0 projection vs `PLATFORM_ADMIN`.
- **Layer 3 (Contracts):** `export_openapi.py --check` (`0-diff`), `lint-imports` (`0` broken), `lint_spine.py` (`0` findings).
- **Security (`tests/security/test_story_26_1_assistant_security_hardening.py`):** Pre-stream `403 ERR_OBSERVER_MODE_READ_ONLY` on all mutating `/assistant/*` endpoints, cross-workspace IDOR on UUID + slug, server-side `READ_SOURCE` & `CONFIDENTIAL_RESTRICTED` masking, Layer 1 immutability + `role: "tool"` rejection, DNS-rebinding SSRF, and zero credential exposure on `platform-setup-state` & `str(exc)`.
- **Layer 5 (Playwright E2E):** Preserve `00`, `01`, `02`, `12`, `16`, `21` passing.

---

## 3. Modifications Summary & Verification Results (Bilan des Modifications)

### 3.1 Created & Modified Files

#### Core Hexagonal & Security Modules (`packages/orcia-core/`, all `<= 300` L)
| File | Kind | Lines | Summary |
| :--- | :--- | :--- | :--- |
| `packages/orcia-core/src/orcia_core/permissions/ssrf_policy.py` | Creation | 275 | Canonical env-var SSRF parser (`ORCIA_LLM_ALLOWED_PRIVATE_HOSTS`), strict `ORCIA_ENV in ("local", "test")` loopback gate, IPv4-mapped IPv6 unwrapping (`::ffff:*`), permanent metadata/internal ORCIA port blocks (`5432`, `6379`, `8333`, `9333`, `9000`), and credential/port/hostname validation (`AD-21` Rule 7, `AD-19` clean). |
| `packages/orcia-core/src/orcia_core/permissions/ssrf_guard.py` | Creation | 140 | Canonical async DNS resolution (`socket.getaddrinfo`) validating every resolved IP against `ssrf_policy` and returning DNS-pinned `PinnedEndpointTarget` against DNS rebinding. |
| `packages/orcia-core/src/orcia_core/permissions/pinned_http.py` | Creation | 33 | Canonical async HTTP transport helper translating `PinnedEndpointTarget` into pinned IP URL, `Host` header, and TLS `sni_hostname` extension. |
| `packages/orcia-core/src/orcia_core/orchestration/{ssrf_policy,ssrf_guard,ai_models_pinned_http}.py` | Modification | 27 / 25 / 7 | Thin backwards-compatible re-export shims delegating to `orcia_core.permissions` (`AD-19` zero cycles). |
| `packages/orcia-core/src/orcia_core/orchestration/ai_models_errors.py` | Modification | 267 | Houses shared `UnsafeLlmEndpointUrlError` domain error under `<= 300` lines. |
| `packages/orcia-core/src/orcia_core/orchestration/ai_models_connection.py` | Modification | 264 | Applied SSRF policy + DNS-pinned HTTP execution across Hub connection checks (`<= 300` L). |
| `packages/orcia-core/src/orcia_core/orchestration/ai_models_connection_helpers.py` | Creation | 147 | Extracted dialect payload builders and connection diagnostic helpers (`<= 300` L). |
| `packages/orcia-core/src/orcia_core/orchestration/ai_models_discovery.py` | Modification | 67 | Applied DNS-pinned SSRF checks on Hub model discovery (`<= 300` L). |
| `packages/orcia-core/src/orcia_core/orchestration/ai_models_discovery_dialects.py` | Creation | 291 | Extracted OpenAI/Anthropic/Ollama/Gemini Hub model discovery dialect parsers (`<= 300` L). |
| `packages/orcia-core/src/orcia_core/orchestration/ai_models_crypto.py` | Modification | 100 | Registered decrypted LLM credentials with the bounded secret scrubber. |
| `packages/orcia-core/src/orcia_core/orchestration/remote_test_bench.py` | Modification | 214 | Updated Hub/bench test flows for env-var SSRF policy compliance. |
| `packages/orcia-core/src/orcia_core/orchestration/_internal/sql_ai_model_queries.py` | Modification | 296 | Aligned workspace-scoped tier queries (`scope_id` UUID fallback to `GLOBAL` preserved for Story `25.5`). |
| `packages/orcia-core/src/orcia_core/orchestration/assistant_agent.py` | Modification | 292 | Added post-fetch `source_uri_authorizer` callback inside Node 3 after dynamic slice and RAG hit retrieval so real context is preserved while filtering unauthorized URIs (`<= 300` L). |
| `packages/orcia-core/src/orcia_core/orchestration/assistant_agent_models.py` | Creation | 106 | Extracted `AssistantAgent` domain request/response/artifact dataclasses (`<= 300` L). |
| `packages/orcia-core/src/orcia_core/orchestration/assistant_agent_synthesis.py` | Creation | 241 | Extracted citation filtering, `CONFIDENTIAL_RESTRICTED` masking, and grounded synthesis helpers (`<= 300` L). |
| `packages/orcia-core/src/orcia_core/orchestration/assistant_citations_and_v5_guard.py` | Modification | 300 | Removed `PLATFORM_ADMIN` shortcut on `READ_SOURCE`/`CONFIDENTIAL_RESTRICTED` filtering and split dataclasses (`<= 300` L). |
| `packages/orcia-core/src/orcia_core/orchestration/assistant_citations_models.py` | Creation | 140 | Extracted citation verification and masking dataclasses (`<= 300` L). |
| `packages/orcia-core/src/orcia_core/orchestration/assistant_harness.py` | Modification | 195 | Added `sanitize_layer_marker_tags` and Layer 1 immutability boundary guards (`allow_system_override=False` default). |
| `packages/orcia-core/src/orcia_core/orchestration/assistant_profile_adaptation.py` | Creation | 140 | Extracted role/archetype prompt adaptation helpers and expanded `[LAYER\|CONSTITUTIONAL\|ONTOLOGY\|HUMAN_PROFILE\|ADAPTATION*]` tag escaping (`<= 300` L). |
| `packages/orcia-core/src/orcia_core/orchestration/assistant_governance.py` | Modification | 282 | Enforced workspace/team-scoped Mode A/B edits and sanitized governance instructions (`<= 300` L). |
| `packages/orcia-core/src/orcia_core/orchestration/assistant_governance_models.py` | Creation | 268 | Extracted Mode A/B governance domain dataclasses (`<= 300` L). |
| `packages/orcia-core/src/orcia_core/orchestration/assistant_governance_layers.py` | Creation | 96 | Extracted 5-layer prompt preview assembly helpers (`<= 300` L). |
| `packages/orcia-core/src/orcia_core/orchestration/assistant_governance_studio.py` | Creation | 244 | Extracted Studio Mode B defaults, manager authorization checks (removing `human_profile_archetype` write privilege), and frozen MCP helpers (`<= 300` L). |
| `packages/orcia-core/src/orcia_core/orchestration/assistant_three_speed_router.py` | Modification | 292 | Removed production `assert det_ms < 80.0` (`H-30`) and split router models/steps (`<= 300` L). |
| `packages/orcia-core/src/orcia_core/orchestration/assistant_three_speed_models.py` | Creation | 165 | Extracted 3-speed routing domain models (`<= 300` L). |
| `packages/orcia-core/src/orcia_core/orchestration/assistant_three_speed_steps.py` | Creation | 269 | Extracted 3-speed deterministic/fast-path step builders (`<= 300` L). |
| `packages/orcia-core/src/orcia_core/rag/adapters/embedding_httpx.py` | Modification | 270 | Wired `post_pinned_embedding_json` (DNS-pinned HTTP + TLS SNI) into embedding calls (`<= 300` L). |
| `packages/orcia-core/src/orcia_core/rag/adapters/embedding_httpx_helpers.py` | Creation | 75 | Extracted DNS-pinned embedding HTTP execution helper (`<= 300` L). |
| `packages/orcia-core/src/orcia_core/bootstrap/_internal/litellm_adapter.py` | Modification | 299 | Wired DNS pinning on provider base URLs and removed raw Bearer header preview logging (`<= 300` L). |
| `packages/orcia-core/src/orcia_core/observability/_internal/ecs_formatter.py` | Modification | 193 | Bounded `_REGISTERED_SECRET_VALUES` to an `OrderedDict` LRU (`<= 2048` entries) and exported `scrub_sensitive_text` (`H-30`). |
| `packages/orcia-core/src/orcia_core/observability/_internal/ecs_normalizer.py` | Creation | 219 | Extracted ECS record normalization and key redaction helpers (`<= 300` L). |
| `packages/orcia-core/src/orcia_core/observability/_internal/trace_context.py` | Creation | 178 | Extracted trace/span context propagation helpers (`<= 300` L). |
| `packages/orcia-core/src/orcia_core/observability/logging.py` | Modification | 193 | Split `trace_context.py` to keep `logging.py` under `<= 300` lines while preserving exports. |
| `packages/orcia-core/src/orcia_core/bootstrap/_internal/setup_snapshot_sanitizer.py` | Creation | 52 | Recursively stripped raw `apiKey`/`api_key`/credentials inside nested snapshot dicts/lists/tuples (`H-17`). |
| `packages/orcia-core/src/orcia_core/bootstrap/_internal/sql_platform_setup_store.py` | Modification | 240 | Invoked recursive `setup_snapshot_sanitizer` and split ORM models (`<= 300` L). |
| `packages/orcia-core/src/orcia_core/bootstrap/_internal/sql_platform_setup_models.py` | Creation | 97 | Extracted SQL setup store ORM models (`<= 300` L). |

#### Backend API, Guards, Schemas & SDK (`apps/api/`, `packages/api-client/`, all non-generated files `<= 300` L)
| File | Kind | Lines | Summary |
| :--- | :--- | :--- | :--- |
| `apps/api/src/orcia_api/dependencies/_assistant_guards.py` | Creation | 237 | Pre-stream `enforce_assistant_workspace_guard` (`READ_ONLY_OBSERVER` + UUID/slug IDOR via `MatrixPermissionEvaluator`), `require_manage`/`can_user_manage_workspace_governance`, `resolve_assistant_workspace_uuid`, `prepare_server_source_uri_authorizer`, and non-bypass `READ_SOURCE` evaluation. |
| `apps/api/src/orcia_api/routers/assistant.py` | Modification | 224 | Wired pre-stream scope/observer guard, real workspace UUID resolution, post-fetch `source_uri_authorizer` callback, sanitized history/tags, and scrubbed `str(exc)` messages (`<= 300` L). |
| `apps/api/src/orcia_api/routers/assistant_workspace.py` | Modification | 250 | Wired pre-stream guards on `three-speed/*`, `artifacts/action`, and `workflows/save-and-launch`; extracted controls router (`<= 300` L). |
| `apps/api/src/orcia_api/routers/_assistant_workspace_controls.py` | Creation | 101 | Extracted guarded `stop`, `feedback`, and `invalidate-cache` routes (`<= 300` L). |
| `apps/api/src/orcia_api/routers/_assistant_workspace_context.py` | Modification | 207 | Resolved workspace context strictly via `MatrixPermissionEvaluator`, enforced `enforce_folder_turn_access(folder, user)` before loading folder notes or thread history, and sanitized pinned markdown (`<= 300` L). |
| `apps/api/src/orcia_api/routers/assistant_workspace_citations.py` | Modification | 173 | Removed client `reader_allowed_source_uris` trust; enforced server-side `READ_SOURCE` & `CONFIDENTIAL_RESTRICTED` filtering (`<= 300` L). |
| `apps/api/src/orcia_api/routers/assistant_workspace_folders.py` | Modification | 280 | Wired pre-stream scope/observer guards, filtered private/unshared folders in `GET /folders`, and sanitized `pinned_notes_markdown` (`<= 300` L). |
| `apps/api/src/orcia_api/routers/assistant_workspace_governance.py` | Modification | 260 | Enforced `can_user_manage_workspace_governance` (org leadership or `PLATFORM_ADMIN`, explicit `scope-global` handling) and observer rejection across Mode A/B mutations (`<= 300` L). |
| `apps/api/src/orcia_api/routers/assistant_background_turns.py` | Modification | 267 | Wired pre-stream scope/observer checks and split background registry (`<= 300` L). |
| `apps/api/src/orcia_api/routers/_assistant_background_registry.py` | Creation | 117 | Extracted background turn registry helpers (`<= 300` L). |
| `apps/api/src/orcia_api/routers/assistant_llm_resolver.py` | Modification | 201 | Prioritized PG18 `resolve_decrypted_ai_model_for_tier_pg18` before `platform_setup_snapshot`, resolved configured `orcia_env`, preserved Story `25.5` `GLOBAL` fallback, and enforced SSRF validation (`<= 300` L). |
| `apps/api/src/orcia_api/routers/assistant_llm_providers.py` | Modification | 227 | Enforced DNS-pinned SSRF and secret scrubbing on runtime LLM HTTP calls (`<= 300` L). |
| `apps/api/src/orcia_api/routers/_assistant_llm_provider_parsing.py` | Creation | 175 | Extracted provider URL/header/model normalization helpers (`<= 300` L). |
| `apps/api/src/orcia_api/routers/_assistant_llm_stream_bridge.py` | Creation | 123 | Extracted async streaming line bridge with scrubbed upstream error forwarding (`<= 300` L). |
| `apps/api/src/orcia_api/routers/assistant_llm_prompts.py` | Modification | 280 | Locked `allow_system_override=False` default, enforced server-side source masking, sanitized tags, and translated governance labels to English (`<= 300` L). |
| `apps/api/src/orcia_api/routers/_assistant_prompt_sanitization.py` | Creation | 139 | Extracted expanded tag escaping, history role normalization, and Layer 1 override rejection (`<= 300` L). |
| `apps/api/src/orcia_api/routers/assistant_llm_bridge.py` | Modification | 290 | Preserved bridge facade while enforcing SSRF, prompt sanitization, and file size cap (`<= 300` L). |
| `apps/api/src/orcia_api/routers/agents_and_skills.py` | Modification | 235 | Preserved `allow_system_override=True` for authorized agent invocations and split skills routes (`<= 300` L). |
| `apps/api/src/orcia_api/routers/_agents_and_skills_{helpers,skills_routes}.py` | Creation | 83 / 110 | Extracted agent helpers and skills routes (`<= 300` L). |
| `apps/api/src/orcia_api/routers/_ai_models_helpers.py` | Modification | 266 | Wrapped ephemeral fallback `httpx.AsyncClient` in `async with` (`<= 300` L). |
| `apps/api/src/orcia_api/routers/bootstrap_accostage.py` | Modification | 215 | Delegated setup-state & LLM routes to modular routers while exporting `_resolve_optional_caller_role` (`<= 300` L). |
| `apps/api/src/orcia_api/routers/_bootstrap_setup_state.py` | Creation | 264 | Returned minimal `{is_initialized, step}` (`200`) for unauthenticated and non-`PLATFORM_ADMIN` callers on default GET (and `403` on `?detail=true`) vs full snapshot for `PLATFORM_ADMIN` (`<= 300` L). |
| `apps/api/src/orcia_api/routers/_bootstrap_llm_routes.py` | Creation | 255 | Enforced SSRF validation on progressive bootstrap LLM routes and wrapped fallback `httpx.AsyncClient` in `async with` (`<= 300` L). |
| `apps/api/src/orcia_api/routers/bootstrap.py` | Modification | 288 | Enforced `validate_safe_llm_endpoint_url` on `init-organization` LLM registration (`<= 300` L). |
| `apps/api/src/orcia_api/middleware/trace_and_error.py` | Modification | 177 | Scrubbed registered secret values from Problem Details error messages while preserving `trace_id`. |
| `apps/api/src/orcia_api/openapi_security.py` | Modification | 91 | Reflected `PlatformSetupStatePublicResponse \| PlatformSetupStateResponse` union security metadata. |
| `apps/api/src/orcia_api/schemas/assistant.py` | Modification | 188 | Restricted client history `role` strictly to `Literal["user", "assistant"]`. |
| `apps/api/src/orcia_api/schemas/assistant_citations_and_folders.py` | Modification | 210 | Removed `reader_allowed_source_uris` from `VerifyAndFilterCitationsRequest`; split `assistant_citations.py` (`<= 300` L). |
| `apps/api/src/orcia_api/schemas/assistant_citations.py` | Creation | 153 | Extracted citation verification schemas (`<= 300` L). |
| `apps/api/src/orcia_api/schemas/assistant_governance_and_three_speed.py` | Creation | 265 | Extracted governance and 3-speed transport schemas (`<= 300` L). |
| `apps/api/src/orcia_api/schemas/bootstrap.py` | Modification | 298 | Added `PlatformSetupStatePublicResponse` (`{is_initialized, step}`), split `_bootstrap_setup.py`, and exported `__all__` (`<= 300` L). |
| `apps/api/src/orcia_api/schemas/_bootstrap_setup.py` | Creation | 186 | Extracted setup snapshot and accostage schemas (`<= 300` L). |
| `packages/api-client/openapi.json`, `src/generated/{schema.ts,bootstrap.ts}` | Modification | — | Regenerated OpenAPI 3.1 schema & typed SDK (`0-diff`). |

#### Frontend, Capabilities, E2E Stack & Tests (`apps/web/`, `docs/`, `infra/`, `tests/`)
| File | Kind | Lines | Summary |
| :--- | :--- | :--- | :--- |
| `apps/web/src/components/platformSetupHydration.ts` | Modification | 252 | Tolerated HTTP `403` from `getPlatformSetupState()` for authenticated non-admin SPA hydration, narrowed `"workspaces" in rawSetup`, and split mappers (`<= 300` L). |
| `apps/web/src/components/platformSetupHydrationMappers.ts` | Creation | 172 | Extracted pure platform setup snapshot hydration mappers (`<= 300` L). |
| `apps/web/src/components/platformSetupStore.tsx` | Modification | 300 | Extracted hydration/persistence helpers into `usePlatformSetupHydrationEffect.ts` (`<= 300` L). |
| `apps/web/src/components/usePlatformSetupHydrationEffect.ts` | Creation | 187 | Extracted setup hydration effect and cleared user-scoped workspaces/cache on logout or user switch (`Alice -> Claire`, `<= 300` L). |
| `apps/web/src/components/useShellContainerState.ts` | Modification | 217 | Reset `activeScopeId` and `ORCIA_ACTIVE_SCOPE_STORAGE_KEY` on logout or authenticated identity switch (`<= 300` L). |
| `apps/web/src/components/ShellContainer.tsx` | Modification | 286 | Cleared saved active scope on logout and wired user identity props into scope state & supervision hooks (`<= 300` L). |
| `apps/web/src/components/useShellAutonomousSupervision.ts` | Modification | 84 | Filtered personal workspaces to matching `currentUserEmail` so prior-user personal workspaces never leak `403` polls (`<= 300` L). |
| `apps/web/vite.config.ts`, `apps/web/playwright.config.ts` | Modification | 39 / 99 | Configured Vite `preview.proxy` + `vite build && vite preview` E2E webServer to eliminate 420-file dev `ERR_NETWORK_CHANGED` module aborts. |
| `apps/web/e2e/support/typedApiRequest.ts`, `support/localLlmCassetteServer.ts`, `16-ai-models-reindex-connectors-and-broker.spec.ts` | Mod / Creation / Mod | 162 / 131 / 294 | Waited for initial shell/login/Day-0 mount in `reloadColdFromPg` and `/assistant` unlock readiness in `16`, and extracted `localLlmCassetteServer.ts` so `16` stays `<= 300` lines. |
| `packages/orcia-core/src/orcia_core/permissions/{revocation,_passthrough_helpers,service}.py` | Creation / Creation / Mod | 79 / 59 / 296 | Extracted revocation stores and passthrough vault helpers from `service.py` (`<= 300` L) and added `bootstrap_access_from_refresh` for idempotent session bootstrap without rotating/revoking refresh `jti` on `GET /api/v1/auth/session`. |
| `apps/api/src/orcia_api/routers/{_auth_token_issuer,_auth_session_routes}.py` | Modification | 120 / 275 | Switched `GET /api/v1/auth/session` to `_bootstrap_session_and_hydrate` (verifies signature, expiry, revocation, and PG18 active user without rotating refresh cookie across concurrent/aborted navigations) while preserving strict single-use rotation on `POST /api/v1/auth/refresh`. |
| `apps/web/src/components/useSidebarAccountSettings.ts`, `packages/ui/src/primitives/{UserSettingsMcpTokensTab,UserSettingsModalDialog}.tsx` | Modification | 297 / 291 / 300 | Awaited `loadModalDetails()` before revealing `lastIssuedPlaintext`, cleared dirty state at submit start, and reset `isDirty` on modal close to eliminate the `user-settings-modal-close-btn` race on `IDE_MCP_KEYS` (`E2E 14`). |
| `tests/unit/test_auth_session_bootstrap_idempotency.py`, `apps/web/src/__tests__/user-settings-mcp-close-race.test.tsx` | Creation | 106 / 59 | Added unit regression tests for concurrent `GET /api/v1/auth/session` idempotency, strict `POST /refresh` + `/logout` revocation, and `UserSettingsModalDialog` MCP token close race guard. |
| `infra/scripts/capabilities_registry.py` | Modification | 233 | Added `"api"` verification level (`D9`) alongside `"ui_only"` and `"e2e"`. |
| `docs/product/capabilities.yaml` | Modification | — | Set `CAP-022`, `CAP-070`, `CAP-072` `verification: api` (`D9`) and registered split sub-routers in `surfaces.api`. |
| `infra/scripts/e2e/e2e_stack_config.py` | Modification | 101 | Configured `ORCIA_LLM_ALLOWED_PRIVATE_HOSTS` for E2E local mock LLM stack. |
| `tests/conftest.py` | Creation | 7 | Defaulted `ORCIA_ENV="test"` for unit/security test collection so strict empty-env production SSRF defaults stay enforced without breaking local test fixtures. |
| `tests/security/test_story_26_1_assistant_security_hardening.py` | Creation | 609 | Red-team & security suite covering pre-stream `403`, UUID/slug cross-workspace IDOR, `READ_SOURCE`/`CONFIDENTIAL_RESTRICTED`, Layer 1 immutability + `agents_and_skills.py` non-regression, DNS-pinned SSRF, minimal setup state + `?detail=true` `403`, bounded LRU scrubber, and zero prod `assert`. |
| `tests/security/test_story_26_1_review_hardening.py` | Creation | 275 | Targeted regression suite covering post-fetch dynamic slice/RAG URI preservation, cross-org/archetype governance rejection, `PLATFORM_ADMIN` no-`READ_SOURCE`-bypass, folder ACL enforcement, empty `ORCIA_ENV` & IPv4-mapped SSRF, adapter DNS pinning + Bearer log redaction, recursive snapshot stripping, and tag escaping. |
| `tests/unit/test_story_26_1_guards_and_ssrf_policy.py` | Creation | 276 | Unit tests for `TEAM`/`GLOBAL` scope, membership `READ_ONLY_OBSERVER`, embedded credentials, private suffixes, IPv4-mapped IPv6, empty DNS resolution, and SSRF canonical imports. |
| `tests/integration/api/test_story_26_1_assistant_security_postgres18.py` | Creation | 242 | Real `create_app()` vertical integration tests against PostgreSQL 18 (`testcontainers`) verifying workspace `scope_id` PG18 priority over snapshot fallback, cross-workspace slug/UUID IDOR, and public `{is_initialized, step}` vs `PLATFORM_ADMIN` setup state. |
| Legacy unit/integration/traceability test updates (`13` files) | Modification | — | Aligned assertions with `D9`, `CAP-022/070/072`, minimal `platform-setup-state`, and Story `26.1` security guards. |

### 3.2 Coverage & Quantitative Verification Results
- **Independent Reviewer Verdict & Closure Status:** **`APPROVED`** by `pro` architecture/security reviewer; `86/86` touched production source files strictly `<= 300` lines (`H-34` compliant); Story `26.1` status closed as `done`.
- **Targeted Story 26.1 Coverage (`--cov-fail-under=90 --cov-report=term-missing` across `20` Story `26.1` security, SSRF, ECS/trace, guard, citation, governance, and setup modules):**
  - **Total coverage: `93.35%`** (including PG18 integration run) — **PASS**:
    - `assistant_agent` / `assistant_citations_models` / `assistant_harness` / `pinned_http`: `100%`
    - `ai_models_connection_helpers`: `98%`; `ssrf_guard`: `97%`; `ssrf_policy` / `assistant_citations_and_v5_guard`: `96%`
    - `ai_models_connection` / `ecs_formatter`: `95%`; `ecs_normalizer`: `94%`
    - `apps/api/dependencies/_assistant_guards` / `_assistant_prompt_sanitization` / `assistant_agent_synthesis`: `93%`
    - `assistant_governance_studio`: `92%`; `assistant_governance`: `89%`; `setup_snapshot_sanitizer` / `_bootstrap_setup_state`: `88%`; `ai_models_crypto`: `86%`; `trace_context`: `75%`
- **Full Python Unit, Security, Evals & Contract Sweep (`tests/unit tests/security tests/evals tests/contract`):**
  - **Final independent run:** **`1087 passed`** (`100%` pass across all unit, security, evals, and contract tests).
- **Static, Type, Security Hygiene, Modularity, Contract & Spine Gates (final post-fix verification):**
  - `.venv/bin/ruff check .`: `exit 0` (`All checks passed!`)
  - `.venv/bin/ruff format --check .`: `exit 0` (`1391 files already formatted`)
  - `.venv/bin/detect-secrets-hook --baseline .secrets.baseline` across all modified/created files: `exit 0`
  - `.venv/bin/lint-imports`: `exit 0` (`Contracts: 5 kept, 0 broken` across `661` files / `4749` dependencies)
  - `.venv/bin/mypy --strict packages/orcia-core/src packages/orcia-connectors/src apps/api/src apps/worker/src`: `exit 0` (`Success: no issues found in 617 source files`)
  - `.venv/bin/python scripts/export_openapi.py --check`: `exit 0` (`0-diff`)
  - `.venv/bin/python .agent/skills/bmad-architecture/scripts/lint_spine.py --workspace docs/planning-artifacts/architecture/architecture-ORCIA-2026-10-24`: `exit 0` (`"total_findings": 0`)
- **TypeScript / Turborepo Verification:**
  - `pnpm turbo run lint typecheck test`: `exit 0` (`Tasks: 9 successful, 9 total`; `@orcia/web`: `67` files / `261` tests passed; `@orcia/ui`: `34` files / `136` tests passed; `@orcia/api-client`: `3` files / `20` tests passed).
- **Playwright Desktop E2E Verification (`desktop-cockpit`, isolated `ORCIA_E2E_CAMPAIGN_DIR`):**
  - Repeatability check (`14` and `16`, `--repeat-each=2`): **`14 passed (3.0m)`**.
  - Full 9-spec sweep (`00`, `01`, `02`, `12-finops`, `12-epic16`, `14`, `15`, `16`, `21`): **`24 passed, 1 skipped (mobile-only), 0 failed (4.4m)`**.
- **Documentation, Living Catalog & GitNexus Gates:**
  - `.venv/bin/python scripts/check_implementation_docs.py`: `exit 0`
  - `pnpm site:sync && pnpm site:check`: `exit 0`
  - `npx gitnexus analyze --index-only && npx gitnexus status`: `up-to-date` (refreshed after all edits).

### 3.3 5-Layer Pyramid (`AD-17`) & Vertical Wiring Status
- **Layer 1a/1b (Python Unit & Vitest):** Verified across Story `26.1` security/unit suites (`176` targeted unit/security/contract tests passed) and `pnpm turbo run lint typecheck test` (`9/9`).
- **Layer 2 (PG18 Integration, `testcontainers`):** `.venv/bin/pytest tests/integration/api/test_story_26_1_assistant_security_postgres18.py tests/integration/test_http_vertical_day0_and_agents_postgres18.py`: `6 passed` on real `create_app()` composition root without overrides. (Unrelated pre-existing failure noted in `tests/integration/test_contextual_help_and_accostage_postgres18.py:178` where Story `25.1` personal workspace row makes `SELECT COUNT(*) FROM workspaces` return `2 != 1`.)
- **Layer 3 (Contracts & Docs):** `export_openapi.py --check` (`0-diff`), `lint-imports` (`5/5 kept`), `lint_spine.py` (`0` findings), `scripts/check_implementation_docs.py`, and `pnpm site:check` verified on closure.
- **Security Layer:** `tests/security/test_story_26_1_assistant_security_hardening.py` + `tests/security/test_story_26_1_review_hardening.py`: all tests passed covering all `H-06`, `H-07`, `H-08`, `H-15`, `H-16`, `H-17`, `H-30`, and post-review findings (`[P0-1]`, `[P0-2]`, `[P1-1]..[P1-4]`, `[P2-1]..[P2-4]`, `[P3-1]`).
- **Layer 5 (Playwright E2E):** **`24 passed, 1 skipped (mobile-only), 0 failed (4.4m)`** across `00`, `01`, `02`, `12-finops`, `12-epic16`, `14`, `15`, `16`, and `21` (plus `14 passed` on `--repeat-each=2` for `14` & `16`) on real PostgreSQL 18 + Redis 7.4 + Vite preview bundle with `e2e_stack_config.py` `ORCIA_LLM_ALLOWED_PRIVATE_HOSTS`, idempotent `GET /api/v1/auth/session`, deterministic MCP modal close guard, and cold PG18 reloads.
