# Story 19.4 — Suppression Intégrale des Noms de Modèles en Dur Backend, Tier Mappings Vides & Amorçage Jour 0 Propre (D4)

- **Date** : 2026-11-15
- **Story / Clé Sprint** : `19-4-suppression-noms-modeles-en-dur-backend-tier-mappings-vides-et-amorcage-jour-0` (`Epic 19`)
- **Capacité(s)** : `CAP-190` (Hub Modèles IA Fiable, Découverte Dynamique 0 Token, Test Réel, EmbeddingPort Hexagonal & RAG Sans Hachage SHA-256) — classification : `feature | hygiène` (`FR-28`, `FR-31`, `AD-24.4`, `AD-16`)
- **Auteur / Contexte** : Tech Lead / Senior Dev. Élimination complète de tout nom de modèle propriétaire ou fictif en dur côté backend (`packages/orcia-core` et `apps/api`), initialisation vide des tier mappings au Jour 0 (`workspace_llm_tier_mappings`), levée obligatoire de l'erreur RFC 9457 `ERR_TIER_MODEL_NOT_CONFIGURED` en cas d'invocation d'un palier non configuré, obligation de renseigner `model_name` sans valeur par défaut, script de maintenance dédié `11_purge_legacy_fictional_llm_seeds.py`, et préservation de la vérité terrain Jour 0 (`pnpm db:reset`).

---

## 1. Analyse du Besoin & Étude d'Impact Tech Lead (Pré-Implémentation)

### 1.1 Contexte & Problématique
- **Constat** : Dans le socle historique d'ORCIA, plusieurs constantes et valeurs par défaut injectaient des identifiants de modèles propriétaires en dur :
  1. `packages/orcia-core/src/orcia_core/bootstrap/workflow_bootstrap_seeds.py:L80-96` (`DEFAULT_LLM_MODEL_ENDPOINT_SEEDS`) définissait 3 endpoints fictifs (`claude-sonnet-4-20260514`, `gpt-4.1-2026-04-14`, `mistral-large-2511`).
  2. `packages/orcia-core/src/orcia_core/orchestration/cognitive_router.py:L133-177` (`build_default_tier_mappings`) pré-remplissait 3 paliers d'inférence avec `claude-3-5-haiku`, `gpt-4o-mini` et `claude-3-7-sonnet`.
  3. `apps/api/src/orcia_api/routers/assistant_llm_gemini_adapter.py:L45,49` et `apps/api/src/orcia_api/routers/assistant_llm_providers.py:L94` utilisaient `model_name: str = "gemini-argon"` par défaut.
  4. `apps/api/src/orcia_api/routers/bootstrap_accostage.py:L259` forçait `model_name = ... or "claude-3-7-sonnet"`.
- **Objectif Décision D4 (Epic 19)** :
  - Démarrer ORCIA dans un état 100 % neutre et souverain : zéro modèle fictif seedé au Jour 0.
  - Les tier mappings (`workspace_llm_tier_mappings`) doivent être initialisés vides tant que l'administrateur n'a pas configuré de modèle dans `/settings/ai-models`.
  - Toute tentative d'inférence sur un palier non assigné doit lever immédiatement `ERR_TIER_MODEL_NOT_CONFIGURED` (RFC 9457) guidant l'utilisateur vers `/settings/ai-models`.
  - Le paramètre `model_name` devient strictement obligatoire sans repli implicite.
  - La commande `pnpm db:reset` (`09_reset_db_first_boot.py --apply`) doit laisser les tables `llm_model_endpoints` et `workspace_llm_tier_mappings` à 0 ligne.
  - Pour les bases de données existantes ayant ingéré d'anciens seeds fictifs, fournir un script de maintenance `11_purge_legacy_fictional_llm_seeds.py` avec mode `--dry-run` par défaut.

### 1.2 Exploration, Analyse d'Impact GitNexus, Factorisation & Dette Technique
- **Analyse d'Impact GitNexus (`gitnexus_query`, `gitnexus_context`, `gitnexus_impact`)** :
  - `build_default_tier_mappings` : impact direct sur `CognitiveModelRouterService.__init__` (`packages/orcia-core/src/orcia_core/orchestration/cognitive_router.py:L183-198`).
  - `DEFAULT_LLM_MODEL_ENDPOINT_SEEDS` : référencé par `packages/orcia-core/src/orcia_core/bootstrap/engine.py:L66` (`ModelRouterService`), `packages/orcia-core/src/orcia_core/bootstrap/seeder.py`, et `infra/scripts/maintenance/04_backfill_system_bootstrap.py`.
  - `build_gemini_native_url` et `normalize_chat_completions_url` : appelés par `invoke_provider_chat_async` et `stream_provider_chat_sse_async` dans `assistant_llm_providers.py` (qui transmettent déjà `ep.model_name`), et testés unitairement.
  - Risque global évalué par GitNexus : **LOW** (surfaces bien délimitées, pas de couplage cyclique).
- **Exploration & Chiffres Clés (Base de Données / Conteneurs / Benchmark)** :
  - Exécution de `pnpm db:reset` : 60 tables vidées, vérification SQL directe confirmant `COUNT(*) == 0` sur `llm_model_endpoints` et `workspace_llm_tier_mappings`.
  - L'implémentation de la décision D4 garantit que ni le seeder ni le reset n'injecteront de données fantômes.
- **Opportunités de Factorisation & Résorption de Dette Technique Naissante** :
  - Centralisation de l'erreur `TierModelNotConfiguredError` dans `packages/orcia-core/src/orcia_core/orchestration/errors.py` avec enregistrement du catalogue d'erreurs bilingue FR/EN conforme à `AD-19`.
  - Éradication des occurrences de modèles codés en dur identifiées dans le code de production (`claude-3-7-sonnet`, `gemini-argon`, `gpt-4o-mini`, `claude-3-5-haiku`).
  - Ajout d'une règle d'audit statique anti-modèles en dur dans `tests/unit/test_codebase_architectural_anti_patterns_audit.py`.

---

## 2. Plan d'Implémentation

### 2.1 Schéma de Données & Migrations Alembic (`infra/migrations/versions/...`, si applicable)
- Aucune modification de schéma DDL nécessaire : les tables `llm_model_endpoints` et `workspace_llm_tier_mappings` supportent déjà des lignes dynamiques créées par l'administrateur.
- Création d'un script de maintenance opérationnel `infra/scripts/maintenance/11_purge_legacy_fictional_llm_seeds.py` avec argument obligatoire `--dry-run` par défaut (`--apply` requis pour commiter) pour purger les anciens enregistrements de seed fictifs sans altérer les migrations Alembic passées (`Conventions GEMINI.md`).

### 2.2 Noyau Métier Hexagonal, Orchestration & Workers (`packages/orcia-core/`)
1. **`packages/orcia-core/src/orcia_core/orchestration/errors.py`** :
   - Déclaration de `TierModelNotConfiguredError(OrciaDomainError)` avec `error_code = "ERR_TIER_MODEL_NOT_CONFIGURED"`, `http_status = 422`, `type_slug = "tier-model-not-configured"`.
   - Entrées FR et EN dans `ORCHESTRATION_ERROR_CATALOG` guidant vers `/settings/ai-models`.
2. **`packages/orcia-core/src/orcia_core/orchestration/cognitive_router.py`** :
   - `build_default_tier_mappings()` retourne `()`.
   - `CognitiveModelRouterService.resolve_mapping()` lève `TierModelNotConfiguredError` si `candidates` est vide.
3. **`packages/orcia-core/src/orcia_core/bootstrap/workflow_bootstrap_seeds.py`** :
   - `DEFAULT_LLM_MODEL_ENDPOINT_SEEDS: tuple[LlmModelEndpointSeed, ...] = ()`.
   - Mise à jour du run de bootstrap Jour 0 (`DEFAULT_SYSTEM_BOOTSTRAP_RUN_SEEDS`) : `verified_llm_families: []` et `distinct_families_count: 0`.

### 2.3 Couche Backend API, Sécurité & Contrats (`apps/api/`)
1. **`apps/api/src/orcia_api/routers/assistant_llm_gemini_adapter.py`** :
   - `build_gemini_native_url(endpoint_uri: str, model_name: str, *, stream: bool = False) -> str` : suppression de la valeur par défaut `"gemini-argon"` ; validation que `model_name.strip()` est non vide.
2. **`apps/api/src/orcia_api/routers/assistant_llm_providers.py`** :
   - `normalize_chat_completions_url(...)` : suppression du défaut `"gemini-argon"`, `model_name: str` devient obligatoire.
3. **`apps/api/src/orcia_api/routers/bootstrap_accostage.py`** :
   - `_apply_setup_snapshot_to_services` : suppression du fallback `"claude-3-7-sonnet"`. Si `model_name` n'est pas renseigné, aucun endpoint fantôme n'est créé.

### 2.4 Interface Utilisateur & Expérience (`apps/web/`)
- Hors périmètre (Story 19.1 déjà livrée, modale avec champs vides et placeholders dynamiques). Le backend garantit la réciprocité complète : champs vides côté UI $\leftrightarrow$ structures vides côté backend $\leftrightarrow$ guidage RFC 9457 explicite.

### 2.5 Analyse d'Impact sur la Pyramide des Tests (`AD-17`)
- **Couche 1a (Unitaires Python `tests/unit/`)** :
  - Création de `tests/unit/test_story_19_4_clean_day0_seeds_and_empty_tiers.py` : vérification que les seeds et tier mappings sont vides, levée de `TierModelNotConfiguredError`, rejet des noms de modèles vides, et fonctionnement idempotent du script de maintenance.
  - Adaptation de `tests/unit/test_epic_8_settings_rbac_llm_studio_and_wizards.py` pour injecter des mappings explicites de test.
  - Adaptation de `tests/unit/test_assistant_agnostic_async_llm_bridge.py`, `tests/unit/test_epic_10_story_10_2_three_speed_router.py`, `tests/unit/test_gemini_argon_provider_adapter.py` pour fournir `model_name`.
  - Extension de `tests/unit/test_codebase_architectural_anti_patterns_audit.py` avec le contrôle d'absence de noms de modèles en dur dans les constantes de production.
- **Couche 2 (Intégration PostgreSQL 18 `tests/integration/`)** :
  - Vérification de `pnpm db:reset` et de l'initialisation propre sans insertion de modèles fantômes.
- **Couche 3 (Contrats OpenAPI 3.1 & `lint-imports`)** :
  - `lint-imports` (0 violation).
  - OpenAPI 3.1 0-diff.
- **Couche 4 (Evals IA Déterministes)** :
  - `DeterministicCassetteLLM` reste 100 % fonctionnel pour les tests de CI à 0 $.
- **Couche Sécurité** :
  - Respect de l'isolation sovereign/agnostique sans préjuger des abonnements externes.

---

## 3. Bilan des Modifications & Résultats (Post-Implémentation)

### 3.1 Fichiers Développés & Modifiés
| Fichier | Nature | Description synthétique |
| :--- | :--- | :--- |
| `packages/orcia-core/src/orcia_core/orchestration/errors.py` | Modification | Ajout de `TierModelNotConfiguredError(OrciaDomainError)` (HTTP 422, `tier-model-not-configured`), messages bilingues FR/EN guidant vers `/settings/ai-models`. |
| `packages/orcia-core/src/orcia_core/orchestration/cognitive_router.py` | Modification | `build_default_tier_mappings()` retourne `()`. `resolve_mapping` lève `TierModelNotConfiguredError` si aucun mapping candidat n'est configuré. |
| `packages/orcia-core/src/orcia_core/bootstrap/workflow_bootstrap_seeds.py` | Modification | `DEFAULT_LLM_MODEL_ENDPOINT_SEEDS` vidé (`()`). Amorce de run de Jour 0 avec 0 famille vérifiée. |
| `apps/api/src/orcia_api/routers/assistant_llm_gemini_adapter.py` | Modification | Suppression de la valeur par défaut `model_name="gemini-argon"`. `model_name` non vide obligatoire. |
| `apps/api/src/orcia_api/routers/assistant_llm_providers.py` | Modification | `normalize_chat_completions_url` exige `model_name` obligatoire sans valeur par défaut codée en dur. |
| `apps/api/src/orcia_api/routers/bootstrap_accostage.py` | Modification | Suppression du repli par défaut `"claude-3-7-sonnet"` lors de la synchronisation de configuration. |
| `infra/scripts/maintenance/11_purge_legacy_fictional_llm_seeds.py` | Création | Script de maintenance idempotente de purge des seeds fictifs historiques (`--dry-run` par défaut, `--apply`). |
| `tests/unit/test_story_19_4_clean_day0_seeds_and_empty_tiers.py` | Création | Suite de tests unitaires dédiée Story 19.4 (amorce vide, exception RFC 9457, simulation maintenance 11). |
| `tests/unit/test_epic_8_settings_rbac_llm_studio_and_wizards.py` | Modification | Adaptation des tests pour vérifier le 422 `ERR_TIER_MODEL_NOT_CONFIGURED` en état non configuré. |
| `tests/unit/test_system_bootstrap.py` | Modification | Fourniture de fixtures orthogonales de test et assertion de la liste d'endpoints vide au Jour 0. |
| `tests/unit/test_assistant_agnostic_async_llm_bridge.py` | Modification | Injection explicite de noms de modèles de test dans les appels de normalisation. |
| `tests/unit/test_gemini_argon_provider_adapter.py` | Modification | Test de rejet de `model_name` vide pour le constructeur d'URL Gemini native. |
| `tests/unit/test_epic_10_story_10_2_three_speed_router.py` | Modification | Enregistrement de mappings de test explicites sur le routeur cognitif. |
| `packages/orcia-core/src/orcia_core/orchestration/step_executors.py` | Modification | Résolution dynamique des modèles via `cognitive_router` ou `metadata` ; éradication de `"anthropic/claude-3-7-sonnet"`. |
| `packages/orcia-core/src/orcia_core/orchestration/assistant_agent.py` | Modification | Résolution dynamique de l'agent assistant via le routeur cognitif ; éradication de `"anthropic/claude-3-7-sonnet"`. |
| `packages/orcia-core/src/orcia_core/orchestration/agents_and_skills_manager.py` | Modification | Résolution dynamique du tier modèle de l'agent (`llm_model_tier`) via le routeur cognitif ; éradication de `"anthropic/claude-3-7-sonnet"`. |
| `packages/orcia-core/src/orcia_core/gates/agentic_lenses.py` | Modification | `evaluator_model_id` rendu obligatoire sans valeur par défaut codée en dur. |
| `packages/orcia-core/src/orcia_core/gates/agentic.py` | Modification | Routage souverain orthogonal sans noms de modèles en dur (`"local/ollama-qwen2.5-coder-32b"` et `"local/vllm-mistral-small-24b"` supprimés). |
| `packages/orcia-core/src/orcia_core/catalog/seeds.py` | Modification | Suppression des scalaires modèles en dur (`"claude-sonnet-4"` et `"gpt-4.1"` remplacés par les tiers cognitifs). |
| `apps/api/src/orcia_api/schemas/gates.py` | Modification | `evaluator_model_id` rendu obligatoire sans valeur par défaut (`google/gemini-2.5-pro` supprimé). |
| `apps/api/src/orcia_api/schemas/workspace_governance.py` | Modification | `generator_model_family` et `judge_model_family` rendus obligatoires sans repli en dur (`claude-4.6`, `mistral-large-3`). |
| `tests/unit/test_codebase_architectural_anti_patterns_audit.py` | Modification | Règle d'audit statique élargie scannant tout `packages/orcia-core/src`, `orcia-connectors/src`, `schemas/`, `routers/` et `apps/worker/src`. |
| `tests/unit/test_story_4_2_agentic_gates_and_secrets.py` | Modification | Fourniture de fixtures d'évaluation orthogonale de test adaptées au contrat strict. |

### 3.2 Résultats Chiffrés, Métriques & Qualité
- **Couverture de tests ciblée** :
  - `packages/orcia-core/src/orcia_core/bootstrap/workflow_bootstrap_seeds.py` : `100%`
  - `apps/api/src/orcia_api/routers/assistant_llm_gemini_adapter.py` : `84%`
  - `apps/api/src/orcia_api/routers/assistant_llm_providers.py` : `86%`
  - `packages/orcia-core/src/orcia_core/orchestration/cognitive_router.py` : `79%`
  - Total ciblé : `85%` (couverture unitaire globale des tests de la story : 6/6 tests dédiés passés à 100%).
- **Qualité statique & Architecture** :
  - `ruff check .` : `0 warning, 0 error`
  - `ruff format --check .` : `0 diff` (798 fichiers vérifiés conformes)
  - `mypy --strict packages/orcia-core/src apps/api/src apps/worker/src` : `Success: no issues found in 311 source files`
  - `lint-imports` : `5 contracts kept, 0 broken`
  - `lint_spine.py` : `ok: true, 0 findings`
  - `grep -rnE "gemini-|claude-|gpt-[0-9]|mistral-|llama|qwen|gemma" apps/api/src packages/*/src apps/worker/src --include=*.py` : **0 hit** (éradication intégrale sur l'ensemble du périmètre de production).
- **Audit Anti-Patrons Architecturaux** :
  - `tests/unit/test_codebase_architectural_anti_patterns_audit.py` : `5 passed` (dont `test_no_hardcoded_model_names_in_production_endpoints_and_adapters` scannant récursivement `packages/orcia-core/src`, `packages/orcia-connectors/src`, `apps/api/src/orcia_api/schemas`, `apps/api/src/orcia_api/routers`, et `apps/worker/src`).

### 3.3 Validation & Procédure de Test sur Toute la Pyramide (`AD-17` + 5 Garde-Fous de Câblage Vertical)
- **Couche 1a — Tests Unitaires Python (`pytest` + `hypothesis`)** :
  - `tests/unit/test_story_19_4_clean_day0_seeds_and_empty_tiers.py` : 6 passed (défense en profondeur : router lève `TierModelNotConfiguredError`, seeds vides, script 11 validé).
  - `tests/unit/test_epic_8_settings_rbac_llm_studio_and_wizards.py` : 10 passed.
  - `tests/unit/test_system_bootstrap.py` : 8 passed.
  - `tests/unit/test_gemini_argon_provider_adapter.py` : 5 passed.
  - `tests/unit/test_assistant_agnostic_async_llm_bridge.py` : 8 passed.
  - `tests/unit/test_epic_10_story_10_2_three_speed_router.py` : 5 passed.
- **Couche 2 — Tests d'Intégration Verticale `HTTP ➔ PostgreSQL 18` (`testcontainers-python` : PostgreSQL 18)** :
  - `tests/integration/test_http_vertical_day0_and_agents_postgres18.py` : 5 passed (test vertical d'accostage et d'agents sur instance réelle PostgreSQL 18).
- **Couche 3 — Tests de Contrat API & Architecture** :
  - Respect strict du contrat RFC 9457 `application/problem+json` avec le code `ERR_TIER_MODEL_NOT_CONFIGURED` (HTTP 422).
  - Validation architecturale `lint-imports` (5 contrats AD-19/AD-20 intacts).
- **Couche 4 — Tests d'Orchestration IA & Evals Golden Dataset (`DeterministicCassetteLLM`)** :
  - Intégrité des cassettes préservée ; `0 $` d'appels externes LLM.
- **Couche Sécurité / Red-Team (`tests/security/`)** :
  - Maintien du contrôle d'accès `RunAccessGuard` et `ScopeAccessGuard` (`WORKSPACE`, `TEAM`, `BU`, `GLOBAL`).
  - Validation SSRF intacte (`is_safe_llm_endpoint_url`).
- **Couche 5 — Survie au F5 & Vérité Terrain Jour 0 (`pnpm db:reset`)** :
  - Exécution réelle de `pnpm db:reset` (`infra/scripts/maintenance/09_reset_db_first_boot.py --apply`).
  - Vérification SQL directe post-reset :
    * `SELECT count(*) FROM workspace_llm_tier_mappings;` $\rightarrow$ **`0`**
    * `SELECT count(*) FROM llm_model_endpoints;` $\rightarrow$ **`0`**
  - La base démarre dans un état neutre et souverain parfait.
