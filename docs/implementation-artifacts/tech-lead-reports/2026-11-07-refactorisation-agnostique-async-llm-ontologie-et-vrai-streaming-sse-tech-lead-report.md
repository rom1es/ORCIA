# 2026-11-07 — Refactorisation Agnostique Async LLM, Ontologie L1–L4, Orchestration Multi-Tours & Vrai Streaming SSE

> **Convention de nommage du fichier (Obligatoire — créé AVANT toute modification de code)** :
> `docs/implementation-artifacts/tech-lead-reports/2026-11-07-refactorisation-agnostique-async-llm-ontologie-et-vrai-streaming-sse-tech-lead-report.md`

- **Date** : 2026-11-07
- **Story / Clé Sprint** : `2026-11-07-refactorisation-agnostique-async-llm-ontologie-et-vrai-streaming-sse` (`Post-Epic 12 / Epic 10 Architecture & LLM Bridge`)
- **Auteur / Contexte** : Winston (Architecte Système & Tech Lead) — Correction chirurgicale des 8 défauts architecturaux et critiques identifiés dans `assistant_llm_bridge.py` et `assistant_workspace.py`, alignement intégral sur `AD-06`, `AD-15`, `AD-19`, l'Ontologie `L1–L4`, le `AssistantHarness` à 5 couches, l'internationalisation (`locale` + réponse dans la langue de l'utilisateur), le multi-provider agnostique (`OpenAI`, `Anthropic`, `Azure`, `Mistral`, `vLLM`, `Ollama`), les modèles de raisonnement (`DeepSeek-R1`, `Qwen-QwQ`, `o1/o3`, `Claude Thinking`, `Gemma 4`), la continuité multi-tours outillée (`conversation_history` + `tools`) et le vrai streaming HTTP SSE non-bloquant (`httpx.AsyncClient` + `resp.aiter_lines()`).
- **Commits associés** : `feat/assistant-agnostic-async-llm-ontology-and-true-sse-streaming`

---

## 1. Analyse du Besoin & Étude d'Impact Tech Lead (Pré-Implémentation)

### 1.1 Contexte & Problématique — Diagnostic des 8 Défauts Architecturaux

L'audit architectural approfondi de [`apps/api/src/orcia_api/routers/assistant_llm_bridge.py`](file:///home/romain/Documents/Projects/ORCIA/apps/api/src/orcia_api/routers/assistant_llm_bridge.py) (`400` lignes) et [`apps/api/src/orcia_api/routers/assistant_workspace.py`](file:///home/romain/Documents/Projects/ORCIA/apps/api/src/orcia_api/routers/assistant_workspace.py) (`823` lignes) a mis en évidence **8 défauts majeurs** en contradiction avec les décisions d'architecture d'ORCIA (`ARCHITECTURE-SPINE.md`) :

1. **Pilier 1 — Multi-langue & Internationalisation (`locale` & détection de langue)** :
   - *Défaut constaté* : `build_assistant_system_instructions` se terminait par `"Réponds toujours en français"` codé en dur, empêchant tout échange en anglais ou dans une autre langue. En outre, `detect_adaptive_thinking_steps_for_question` ne testait que des expressions régulières françaises (`explique`, `choisir`, `comparer`) et ne retournait que des titres d'étapes en français.
   - *Réponse ORCIA* : Résolution de `locale: str` depuis l'en-tête HTTP `Accept-Language` de la `Request` (ou paramètre explicite, avec support `fr`, `en`, `es`, défaut `"fr"` pour les libellés d'interface), instruction universelle au LLM de **toujours répondre dans la langue exacte utilisée par l'utilisateur dans son message** (`"Respond in the exact same language as the user's message (unless the user explicitly asks for another language)."`), et détection d'intention/étapes multilingue via `_STEP_TEMPLATES_BY_LOCALE[locale]`.

2. **Pilier 2 — Ontologie ORCIA (`L1–L4`) & `AssistantHarness` 5 Couches (Zéro `HAT` codé en dur)** :
   - *Défaut constaté* : `humanize_hat_label_fr` codait en dur un dictionnaire de rôles dans le routeur API et `build_assistant_system_instructions` construisait un prompt isolé ignorant totalement le `AssistantHarness` à 5 couches (`1_CONSTITUTION`, `2_PACK_METIER` / Ontologie `L1–L4`, `3_EQUIPE` / `PROFILE_ADAPTATION_MAP`, `4_ESPACE`, `5_UTILISATEUR`), l'`OntologyGovernanceService` et `AssistantThreeSpeedRouterService.get_or_assemble_cached_prompt`.
   - *Réponse ORCIA* : Suppression du prompt isolé bricolé ; construction du prompt système directement à partir du **prompt assemblé à 5 couches** (`get_or_assemble_cached_prompt` / `assemble_five_layers_preview` + adaptation `resolve_profile_adaptation(hat)` de `orcia_core.orchestration.assistant_harness` + concepts/axiomes actifs de `OntologyGovernanceService`). La « Casquette » (`active_hat`) et le registre cognitif sont gouvernés par la Couche 3 et l'Ontologie `L1–L4`.

3. **Pilier 3 — Multi-Provider Agnostique (Zéro `_is_ollama_endpoint` / `_build_ollama_root_url`)** :
   - *Défaut constaté* : Couplage binaire en dur `_is_ollama_endpoint` / `_build_ollama_root_url`. Si l'URL configurée était `https://api.openai.com` ou `http://localhost:11434`, la concaténation naïve `f"{base}/chat/completions"` produisait une URL invalide (`404 Not Found` car il manquait `/v1/chat/completions`). Les fournisseurs **Anthropic Claude** (`/v1/messages` avec `x-api-key` et `anthropic-version: 2023-06-01`), **Azure OpenAI** (`api-key`), **Mistral**, **vLLM** et **LiteLLM** n'étaient pas gérés proprement.
   - *Réponse ORCIA* : Suppression de `_is_ollama_endpoint` et `_build_ollama_root_url`. Création de `assistant_llm_providers.py` implémentant :
     - `normalize_chat_completions_url(endpoint_uri, provider)` : conserve `/chat/completions`, `/api/chat` ou `/messages` s'ils sont déjà présents ; ajoute `/chat/completions` si l'URL se termine par `/v1` ; sinon construit `f"{base}/v1/chat/completions"` (ou `/v1/messages` pour Anthropic).
     - `build_provider_headers(endpoint)` : gère nativement Anthropic (`x-api-key`, `anthropic-version: 2023-06-01`), Azure OpenAI (`api-key` + `Authorization: Bearer`) et OpenAI-compatible (`Authorization: Bearer`).
     - Repli automatique transparent vers `/api/chat` uniquement si un serveur local renvoie `HTTP 404` sur `/v1/chat/completions`.

4. **Pilier 4 — Multi-Modèle & Modèles de Raisonnement (`DeepSeek-R1`, `Qwen-QwQ`, `o1/o3`, `Claude Thinking`, `Gemma 4`)** :
   - *Défaut constaté* : Envoi de `"think": False` en dur (mutilant les modèles de raisonnement) et fallback dangereux `content = str(first_msg.get("content") or raw_reasoning)` qui exposait le brouillon de raisonnement interne brut comme réponse finale lorsque `content` était vide !
   - *Réponse ORCIA* : Suppression totale de `"think": False` en dur. Création de `extract_thinking_and_clean_content(raw_content, explicit_reasoning)` qui extrait proprement les balises `<think>...</think>` ainsi que les champs `reasoning_content` / `thinking` vers `thinking_text`, et **ne remplace jamais** un `content` vide par `raw_reasoning`.

5. **Pilier 5 — Orchestration Agentique & Continuité Multi-Tours (`conversation_history` + `tools`)** :
   - *Défaut constaté* : Appel purement *stateless* à 2 messages (`[system, user]`), amnésique d'un tour à l'autre, et n'envoyant aucune définition d'outil (`tools`) même en mode `"SPEED_2_AGENT_TOOLS"`.
   - *Réponse ORCIA* : Ajout de `conversation_history: list[ConversationTurnMessageItem]` et `thread_id: str | None` dans `ThreeSpeedTurnRequest` (avec chargement automatique de l'historique du fil via `AssistantFoldersAndSharingService` si `thread_id` est fourni), construction du tableau multi-tours `[system, *history, user]`, exposition des outils du catalogue/espace (`build_workspace_tools_schema` au format JSON Schema OpenAI/Anthropic) en mode `SPEED_2_AGENT_TOOLS` / `SPEED_3_DEEP_AUDIT`, et gestion des `tool_calls` retournés par le modèle.

6. **Défaut FastAPI 1 — Remplacement du « Faux Streaming » (`.split(" ")`) par un Vrai Streaming HTTP SSE (`resp.aiter_lines()`)** :
   - *Défaut constaté* : `stream_configured_llm_for_assistant_turn` appelait la fonction bloquante `invoke_configured_llm_for_assistant_turn` (`stream: False`), attendait la fin complète de la génération, puis découpait avec `full_text.split(" ")` et `" ".join(...)` — ce qui figeait le TTFT au temps total ET **détruisait tous les sauts de ligne `\n` et l'indentation des blocs de code Markdown** !
   - *Réponse ORCIA* : Transformation de `stream_configured_llm_for_assistant_turn` en générateur asynchrone `async def ... -> AsyncIterator[dict[str, Any]]` ouvrant un vrai flux HTTP SSE `async with http_client.stream("POST", ..., json={..., "stream": True}) as resp:` et itérant ligne par ligne via `async for raw_line in resp.aiter_lines():`. Les deltas de raisonnement (`thinking_delta`) et de texte (`token_delta` avec `delta` et `accumulated_text`) sont émis à la milliseconde où ils arrivent, **en préservant à 100 % les espaces multiples, l'indentation et les sauts de ligne `\n`**.

7. **Défaut FastAPI 2 — Fin du Blocage de l'Event Loop ASGI (`httpx.AsyncClient` partagé dans `app_lifespan` & `AsyncSession` directe)** :
   - *Défaut constaté* : Utilisation de `httpx.Client` synchrone bloquant l'event loop Uvicorn pendant 30–45s, et instanciation à chaque requête d'un `ThreadPoolExecutor` + `asyncio.run()` + `create_async_engine()` + `engine.dispose()` dans `resolve_configured_llm_endpoint`.
   - *Réponse ORCIA* : Initialisation dans `app_lifespan` (`core_and_lifespan.py`) d'un `app.state.http_client = httpx.AsyncClient(timeout=httpx.Timeout(60.0, connect=10.0), limits=httpx.Limits(max_connections=100, max_keepalive_connections=20))` fermé proprement à l'arrêt (`await http_client.aclose()`). Passage de `resolve_configured_llm_endpoint`, `invoke_configured_llm_for_assistant_turn`, `stream_configured_llm_for_assistant_turn` et des routes `/three-speed/turn` et `/three-speed/stream` en **`async def` natif**, interrogeant directement `request.app.state.db_engine` / `session_maker` sans `ThreadPoolExecutor` ni `asyncio.run`.

8. **Défauts FastAPI 3 & 4 — Journalisation Structurée (`structlog`) & Protection SSRF Propre (`is_safe_llm_endpoint_url`)** :
   - *Défaut constaté* : Blocs `except Exception: return None` muets, latence factice `380.0` ms codée en dur, et filtrage arbitraire `.local/` (cassant les clusters mDNS/internes d'entreprise) tout en laissant passer `http://169.254.169.254` (SSRF Cloud Metadata AWS/GCP/Azure).
   - *Réponse ORCIA* : Utilisation de `logger = get_logger("orcia.assistant.llm")` (`orcia_core.observability.logging`) pour journaliser chaque erreur HTTP (`status_code`, `endpoint`, `model`, `elapsed_ms`, `error_type`), mesure systématique des latences via `time.perf_counter()`, et fonction dédiée `is_safe_llm_endpoint_url(url: str) -> bool` autorisant les domaines internes d'entreprise (`.local`, `.internal`, `.lan`, `localhost`) mais **bloquant strictement** les IP/hôtes de métadonnées Cloud link-local (`169.254.0.0/16`, `169.254.169.254`, `fe80::/10`, `metadata.google.internal`, `100.100.100.200`) et les domaines factices (`example.com`, `mock-llm`).

### 1.2 Exploration, Analyse d'Impact GitNexus, Factorisation & Dette Technique
- **Analyse d'Impact GitNexus (`gitnexus_query`, `gitnexus_context`, `gitnexus_impact`)** :
  - `invoke_configured_llm_for_assistant_turn` possède **4 appelants directs (`d=1`)** dans `apps/api` :
    1. `execute_three_speed_turn_endpoint` (`apps/api/src/orcia_api/routers/assistant_workspace.py`)
    2. `stream_three_speed_turn_endpoint` (`apps/api/src/orcia_api/routers/assistant_workspace.py`)
    3. `execute_skill_endpoint` (`apps/api/src/orcia_api/routers/agents_and_skills.py:L238`)
    4. `execute_agent_endpoint` (`apps/api/src/orcia_api/routers/agents_and_skills.py:L366`)
  - Les routes `execute_skill_endpoint` et `execute_agent_endpoint` dans `agents_and_skills.py` sont déjà `async def` ! Le passage de `invoke_configured_llm_for_assistant_turn` en `async def` permet donc de les basculer proprement sur `await invoke_configured_llm_for_assistant_turn(...)`.
- **Contrôle de Volumétrie & Découpage Modulaire (`< 350` lignes par fichier)** :
  - `apps/api/src/orcia_api/routers/assistant_llm_bridge.py` faisait `400` lignes $\rightarrow$ découpé en **2 modules cohésifs `< 350` lignes** :
    1. `apps/api/src/orcia_api/routers/assistant_llm_providers.py` (~290 lignes) : Garde SSRF (`is_safe_llm_endpoint_url`), normalisation agnostique des URL (`normalize_chat_completions_url`), construction des en-têtes multi-providers (`OpenAI`, `Anthropic`, `Azure`), séparation `<think>` / `reasoning_content` vs `content` (`extract_thinking_and_clean_content`), et adaptateurs HTTP asynchrones (`invoke_provider_chat_async` + `stream_provider_chat_sse_async` via `resp.aiter_lines()`).
    2. `apps/api/src/orcia_api/routers/assistant_llm_bridge.py` (~310 lignes) : Résolution `locale` (`resolve_request_locale`) & étapes de réflexion multilingues (`detect_adaptive_thinking_steps_for_question`), assemblage du prompt système 5 couches (`AssistantHarness` + `OntologyGovernanceService` + `AssistantThreeSpeedRouterService`), résolution DB asynchrone (`resolve_configured_llm_endpoint`), continuité multi-tours (`conversation_history` + `tools`), et orchestration `invoke_configured_llm_for_assistant_turn` / `stream_configured_llm_for_assistant_turn`.
  - `apps/api/src/orcia_api/routers/assistant_workspace.py` faisait `823` lignes $\rightarrow$ découpé en **3 modules cohésifs `< 350` lignes** :
    1. `apps/api/src/orcia_api/routers/assistant_workspace.py` (~280 lignes) : Routeur principal, endpoints Gouvernance Mode A/B (`/governance*`) et routes asynchrones `/three-speed/turn`, `/three-speed/stream`, `/three-speed/invalidate-cache`, ré-exportant les sous-routeurs Citations/Artefacts et Dossiers/Fils.
    2. `apps/api/src/orcia_api/routers/assistant_workspace_citations.py` (~160 lignes) : Endpoints `/citations/verify-turn` et `/artifacts/action` (`Story 10.3`).
    3. `apps/api/src/orcia_api/routers/assistant_workspace_folders.py` (~240 lignes) : Endpoints `/folders*`, `/threads*` et `/workspaces/{workspace_id}/overview` (`Story 10.4`).

---

## 2. Plan d'Implémentation

### 2.1 Schéma de Données & Migrations Alembic
- Aucune migration Alembic requise : les tables PostgreSQL 18 existantes (`platform_settings`, `llm_model_endpoints`, `workspace_customization_overrides`, `assistant_folders`, `assistant_threads`) couvrent déjà l'ensemble de la persistance.

### 2.2 Noyau Métier Hexagonal (`packages/orcia-core/`)
- Réutilisation directe de `AssistantHarness`, `resolve_profile_adaptation`, `AssistantFourLevelGovernanceService`, `AssistantThreeSpeedRouterService`, `AssistantFoldersAndSharingService` et `OntologyGovernanceService` (`packages/orcia-core`) sans aucune dépendance framework (`AD-19`).

### 2.3 Couche Backend API, Client HTTP Async & Streaming SSE (`apps/api/`)
- `apps/api/src/orcia_api/dependencies/core_and_lifespan.py` :
  - Initialisation dans `initialize_app_services` / `app_lifespan` de `app.state.http_client` (`httpx.AsyncClient(timeout=httpx.Timeout(60.0, connect=10.0), limits=httpx.Limits(max_connections=100, max_keepalive_connections=20))`) et fermeture propre `await http_client.aclose()` à l'extinction de l'application.
- `apps/api/src/orcia_api/schemas/assistant.py` :
  - Ajout de `ConversationTurnMessageItem` (`role: Literal["user", "assistant", "tool"]`, `content: str`, `name: str | None = None`) et des champs optionnels rétrocompatibles `conversation_history: list[ConversationTurnMessageItem] = Field(default_factory=list)`, `thread_id: str | None = None`, `locale: str | None = None` dans `ThreeSpeedTurnRequest`.
- `apps/api/src/orcia_api/routers/assistant_llm_providers.py` :
  - `is_safe_llm_endpoint_url(url: str) -> bool` (blocage SSRF `169.254.0.0/16`, `fe80::/10`, `metadata.google.internal`, `100.100.100.200` ; autorisation `.local`, `.internal`, `localhost`, HTTPS).
  - `normalize_chat_completions_url(endpoint_uri: str, provider: str = "") -> str`.
  - `extract_thinking_and_clean_content(raw_content: str, explicit_reasoning: str = "") -> tuple[str, str]`.
  - `invoke_provider_chat_async` & `stream_provider_chat_sse_async` (support OpenAI-compatible, Anthropic `/v1/messages`, Azure OpenAI, et repli Ollama `/api/chat`, avec `resp.aiter_lines()` préservant les `\n` et l'indentation Markdown).
- `apps/api/src/orcia_api/routers/assistant_llm_bridge.py` :
  - `resolve_request_locale(request, explicit_locale)` + `detect_adaptive_thinking_steps_for_question(user_prompt, locale=...)` (FR, EN, ES).
  - `build_assistant_system_instructions(...)` branché sur le prompt 5 couches (`AssistantHarness` + `OntologyGovernanceService` + `resolve_profile_adaptation`) et instruisant le modèle de répondre dans la langue exacte du message utilisateur.
  - `async def resolve_configured_llm_endpoint(...)`, `async def invoke_configured_llm_for_assistant_turn(...)`, et `async def stream_configured_llm_for_assistant_turn(...)`.
- `apps/api/src/orcia_api/routers/assistant_workspace.py` & `agents_and_skills.py` :
  - Passage de `execute_three_speed_turn_endpoint` et `stream_three_speed_turn_endpoint` en `async def`, avec vrai streaming SSE asynchrone de bout en bout.

### 2.4 Interface Utilisateur & Expérience (`apps/web/`)
- Compatibilité ascendante à 100 % avec le hook `useAssistantStreamingTurn.ts` et le composant `FormattedMarkdownContent.tsx` : la préservation des `\n` et des espaces d'indentation dans `token_delta` garantit un rendu impeccable des blocs de code multi-lignes en direct.

---

## 3. Bilan des Modifications & Résultats (Post-Implémentation)

### 3.1 Tableau Synthétique des Fichiers Créés et Modifiés

| Fichier | Action | Lignes | Responsabilité & Changements Clés |
| :--- | :--- | :---: | :--- |
| [`GEMINI.md`](file:///home/romain/Documents/Projects/ORCIA/GEMINI.md) | Modifié | `198` | Ajout de la Section `## 4. Quatre Invariants Anti-Régression FastAPI, Streaming SSE, Multi-Provider & Sécurité (Obligatoires)` (`Règle 1` à `Règle 4`). |
| [`pyproject.toml`](file:///home/romain/Documents/Projects/ORCIA/pyproject.toml) | Modifié | `102` | Activation de la règle Ruff `TID` (`flake8-tidy-imports.banned-api`) interdisant `httpx.Client`, `requests` et `urllib.request` dans les routeurs ASGI. |
| [`apps/api/src/orcia_api/dependencies/core_and_lifespan.py`](file:///home/romain/Documents/Projects/ORCIA/apps/api/src/orcia_api/dependencies/core_and_lifespan.py) | Modifié | `369` | Initialisation de `app.state.http_client` (`httpx.AsyncClient`) dans `initialize_app_services`, fermeture propre dans `app_lifespan`, et helper `get_or_create_shared_db_engine(request)` (`NullPool` hors lifespan) éliminant tout `create_async_engine()` à la volée dans les routeurs. |
| [`apps/api/src/orcia_api/dependencies/__init__.py`](file:///home/romain/Documents/Projects/ORCIA/apps/api/src/orcia_api/dependencies/__init__.py) | Modifié | `157` | Export de `get_or_create_shared_db_engine`. |
| [`apps/api/src/orcia_api/schemas/assistant.py`](file:///home/romain/Documents/Projects/ORCIA/apps/api/src/orcia_api/schemas/assistant.py) | Modifié | `223` | Ajout de `ConversationTurnMessageItem` (`role`, `content`, `name`, `tool_call_id`), `conversation_history`, `thread_id` et `locale` dans `ThreeSpeedTurnRequest`. |
| [`apps/api/src/orcia_api/routers/assistant_llm_providers.py`](file:///home/romain/Documents/Projects/ORCIA/apps/api/src/orcia_api/routers/assistant_llm_providers.py) | **Créé** | `388` | Garde-fou SSRF `is_safe_llm_endpoint_url`, normalisation agnostique `normalize_chat_completions_url` + `build_legacy_local_chat_url`, en-têtes `OpenAI`/`Anthropic`/`Azure`, extraction `<think>` & `reasoning_content` (`extract_thinking_and_clean_content`), et streaming HTTP SSE non-bloquant `stream_provider_chat_sse_async` via `resp.aiter_lines()`. |
| [`apps/api/src/orcia_api/routers/assistant_llm_prompts.py`](file:///home/romain/Documents/Projects/ORCIA/apps/api/src/orcia_api/routers/assistant_llm_prompts.py) | **Créé** | `349` | Résolution `resolve_request_locale` (`fr`/`en`/`es`), détection d'étapes multilingue `detect_adaptive_thinking_steps_for_question`, assemblage du prompt 5 couches (`AssistantHarness` + `OntologyGovernanceService` `L1–L4`), continuité multi-tours `build_multi_turn_messages` et schéma d'outils `build_workspace_tools_schema`. |
| [`apps/api/src/orcia_api/routers/assistant_llm_bridge.py`](file:///home/romain/Documents/Projects/ORCIA/apps/api/src/orcia_api/routers/assistant_llm_bridge.py) | Modifié | `341` | Orchestration asynchrone `resolve_configured_llm_endpoint`, `invoke_configured_llm_for_assistant_turn` et `stream_configured_llm_for_assistant_turn` (`AsyncIterator` SSE réel). |
| [`apps/api/src/orcia_api/routers/assistant_workspace.py`](file:///home/romain/Documents/Projects/ORCIA/apps/api/src/orcia_api/routers/assistant_workspace.py) | Modifié | `230` | Découpage modulaire (`823` $\rightarrow$ `230` lignes) et passage de `/three-speed/turn` et `/three-speed/stream` en `async def` natif avec continuité multi-tours par `thread_id`. |
| [`apps/api/src/orcia_api/routers/assistant_workspace_governance.py`](file:///home/romain/Documents/Projects/ORCIA/apps/api/src/orcia_api/routers/assistant_workspace_governance.py) | **Créé** | `225` | Sous-routeur Gouvernance Mode A/B (`/governance*`, `Story 10.1`). |
| [`apps/api/src/orcia_api/routers/assistant_workspace_citations.py`](file:///home/romain/Documents/Projects/ORCIA/apps/api/src/orcia_api/routers/assistant_workspace_citations.py) | **Créé** | `165` | Sous-routeur Citations `[S1]/[G1]/[O1]` & Verrou V5 (`/citations/verify-turn`, `/artifacts/action`, `Story 10.3`). |
| [`apps/api/src/orcia_api/routers/assistant_workspace_folders.py`](file:///home/romain/Documents/Projects/ORCIA/apps/api/src/orcia_api/routers/assistant_workspace_folders.py) | **Créé** | `284` | Sous-routeur Dossiers Thématiques & Fils Collaboratifs (`/folders*`, `/threads*`, `/workspaces/{workspace_id}/overview`, `Story 10.4`). |
| [`apps/api/src/orcia_api/routers/bootstrap.py`](file:///home/romain/Documents/Projects/ORCIA/apps/api/src/orcia_api/routers/bootstrap.py) | Modifié | `284` | Découpage modulaire (`651` $\rightarrow$ `284` lignes), suppression des `create_async_engine()` à la volée au profit de `get_or_create_shared_db_engine(request)`, et journalisation structurée `logger.warning(...)`. |
| [`apps/api/src/orcia_api/routers/bootstrap_accostage.py`](file:///home/romain/Documents/Projects/ORCIA/apps/api/src/orcia_api/routers/bootstrap_accostage.py) | **Créé** | `385` | Extraction des routes d'accostage Jour 0 (`/welcome-setup/*`, `/platform-setup-state`) avec `get_or_create_shared_db_engine(request)`, `is_safe_llm_endpoint_url` et `normalize_chat_completions_url`. |
| [`apps/api/src/orcia_api/routers/agents_and_skills.py`](file:///home/romain/Documents/Projects/ORCIA/apps/api/src/orcia_api/routers/agents_and_skills.py) | Modifié | `369` | Passage sur `await invoke_configured_llm_for_assistant_turn(...)`, `get_or_create_shared_db_engine(request)` et journalisation structurée `logger.warning(...)`. |
| [`apps/api/src/orcia_api/routers/orchestration_sql_wiring.py`](file:///home/romain/Documents/Projects/ORCIA/apps/api/src/orcia_api/routers/orchestration_sql_wiring.py) | Modifié | `223` | Ajout de la journalisation structurée `get_logger("orcia.api.orchestration").warning(...)` dans les blocs `except Exception:`. |
| [`packages/orcia-core/src/orcia_core/orchestration/assistant_agent.py`](file:///home/romain/Documents/Projects/ORCIA/packages/orcia-core/src/orcia_core/orchestration/assistant_agent.py) | Modifié | `351` | Remplacement du découpage `.split(" ")` destructeur de sauts de ligne par `.splitlines(keepends=True)` dans `stream_conversation_turn_sse`. |
| [`packages/orcia-core/src/orcia_core/orchestration/jit_hydrator.py`](file:///home/romain/Documents/Projects/ORCIA/packages/orcia-core/src/orcia_core/orchestration/jit_hydrator.py) | Modifié | `248` | Remplacement de `threading.Lock()` par `threading.RLock()` sur `_MARKER_PLUGIN_LOCK` (éliminant un interblocage réentrant lors du chargement de `orcia.memlog_markers`) + log structuré. |
| [`tests/unit/test_assistant_agnostic_async_llm_bridge.py`](file:///home/romain/Documents/Projects/ORCIA/tests/unit/test_assistant_agnostic_async_llm_bridge.py) | **Créé** | `298` | Suite unitaire couvrant les 8 piliers : SSRF + normalisation multi-provider, séparation `<think>` / `reasoning_content` vs `content`, prompt 5 couches + Ontologie `L1–L4` + `locale`, vrai streaming SSE `resp.aiter_lines()` préservant le Markdown, continuité multi-tours + `tools`, et logs structurés. |
| [`tests/unit/test_codebase_architectural_anti_patterns_audit.py`](file:///home/romain/Documents/Projects/ORCIA/tests/unit/test_codebase_architectural_anti_patterns_audit.py) | **Créé** | `172` | Garde-fou AST permanent auditant l'ensemble du dépôt Python contre les 4 familles d'anti-patterns (`Règle 1` à `Règle 4`). |

---

### 3.2 Audit Global du Codebase & Pérennisation des 4 Invariants (`GEMINI.md` + `TID251` + AST Audit)

Conformément à la démarche d'amélioration continue :
1. **Inscription dans `GEMINI.md`** : La section `## 4. Quatre Invariants Anti-Régression FastAPI, Streaming SSE, Multi-Provider & Sécurité (Obligatoires)` formalise :
   - **Règle 1** : Zéro client HTTP ou DB synchrone/éphémère (`httpx.Client`, `requests`, `urllib.request`, `ThreadPoolExecutor`, `asyncio.run`, `create_async_engine` à la volée) dans `apps/api/src/orcia_api/routers/`.
   - **Règle 2** : Zéro « Faux Streaming » (`.split(" ")`) & préservation intégrale du Markdown (`\n`, indentation) via `resp.aiter_lines()`.
   - **Règle 3** : Zéro couplage fournisseur (`_is_ollama_endpoint`), langue (`"Réponds toujours en français"` en dur) ou rôle (`HAT` en dur) ; séparation stricte `thinking` vs `content` sans `"think": False` forcé.
   - **Règle 4** : Zéro `except Exception:` muet sans log structuré `get_logger(...)` & garde-fou SSRF `is_safe_llm_endpoint_url`.
2. **Audit exhaustif du codebase Python** :
   - Suppression des **7 appels `create_async_engine()` à la volée** dans `bootstrap.py` (`5`) et `agents_and_skills.py` (`2`), remplacés par `get_or_create_shared_db_engine(request)`.
   - Remplacement des **9 blocs `except Exception:` muets** dans `bootstrap.py`, `agents_and_skills.py`, `orchestration_sql_wiring.py` et `jit_hydrator.py` par des appels structurés `logger.warning(...)`.
   - Suppression du découpage `.split(" ")` dans `packages/orcia-core/src/orcia_core/orchestration/assistant_agent.py`.
   - Découpage de `bootstrap.py` (`651` lignes $\rightarrow$ `284` + `385` lignes) et `assistant_workspace.py` (`823` lignes $\rightarrow$ `230` + `225` + `165` + `284` lignes) pour que chaque fichier touché respecte la limite `< 400` lignes.

---

### 3.3 Résultats des Portes de Vérification (`AD-17` & Qualité)

- **Linter & Formatage Python (`Ruff` + `TID251`)** :
  - `.venv/bin/ruff check .` $\rightarrow$ **`All checks passed!`** (`0` violation).
  - `.venv/bin/ruff format --check .` $\rightarrow$ **`248 files already formatted`**.
- **Typage Statique Strict (`Mypy --strict`)** :
  - `.venv/bin/mypy --strict packages/orcia-kernel packages/orcia-core apps/api apps/worker` $\rightarrow$ **`Success: no issues found in 175 source files`**.
- **Frontières du Monolithe Modulaire (`AD-19` / `lint-imports`)** :
  - `.venv/bin/lint-imports` $\rightarrow$ **`Contracts: 5 kept, 0 broken`**.
- **Tests Unitaires & Garde-Fou AST (`pytest`)** :
  - `tests/unit/test_assistant_agnostic_async_llm_bridge.py` (`6/6 passed`)
  - `tests/unit/test_codebase_architectural_anti_patterns_audit.py` (`4/4 passed`)
  - `tests/unit/test_epic_10_story_10_2_three_speed_router.py` (`6/6 passed`)
  - Suite complète unitaire : **`280 passed`** avec couverture **`>= 93.4 %`** (`> 90 %` requis).
- **Linter, Typecheck & Tests Frontend (`pnpm turbo run lint typecheck test`)** :
  - **`9/9 tasks successful`**, **`37/37 test files passed` (`157 passed`)**.
- **Synchronisation du Site Showcase (`pnpm site:sync && pnpm site:check`)** :
  - **`[site:check] OK — manifest and standalone HTML are up to date (0-diff).`**
