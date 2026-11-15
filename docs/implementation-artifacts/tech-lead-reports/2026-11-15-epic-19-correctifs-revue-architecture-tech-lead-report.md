# [2026-11-15 — Correctifs de Fin d'Epic 19 : Findings de la Revue d'Architecture Finale (VALIDATE)]

- **Date** : 2026-11-15
- **Story / Clé Sprint** : `2026-11-15-epic-19-correctifs-revue-architecture` (`Epic 19` / `VALIDATE`)
- **Capacité(s)** : `CAP-190` (Hub Modèles IA & Embeddings Sémantiques) — classification : `hygiène`
- **Auteur / Contexte** : Tech Lead & Senior Dev (`bmad-dev-worker`). Traitement rigoureux des 2 findings bloquants et des findings majeurs et mineurs identifiés lors de la revue d'architecture finale de l'Epic 19 par Winston (`VALIDATE`).
- **Commits associés** : à compléter en Section 3.

---

## 1. Analyse du Besoin & Étude d'Impact Tech Lead (Pré-Implémentation)

### 1.1 Contexte & Problématique
La revue d'architecture de l'Epic 19 a émis un avis **GO AVEC RÉSERVES** avec 2 anomalies bloquantes et plusieurs dettes techniques :
1. **[BLOQUANT B1] Clé de déchiffrement erronée dans le worker Dramatiq `rag_reindexer.py`** :
   - `cipher = PassthroughVaultCipher(master_key=b"0" * 32)` était codé en dur à la ligne 59.
   - En production, les clés API sont chiffrées avec `ORCIA_PASSTHROUGH_MASTER_KEY` (résolu depuis l'environnement ou `config.py`).
   - Tout job de réindexation en arrière-plan tentant de déchiffrer la clé API d'un modèle d'embedding crashait systématiquement avec une exception AES-GCM `InvalidTag`.
2. **[BLOQUANT B2] Violation de la décision D12 sur `GET /api/v1/search`** :
   - La route `GET /api/v1/search` dans `portal_and_help.py` capturait silencieusement `NoActiveEmbeddingModelError` et `RagReindexInProgressError` pour basculer sur `query_embedding = None`, servant des résultats V1 purement lexicaux (`200 OK`).
   - La décision D12 et la spec interdisent formellement tout mode dégradé lexical si aucun modèle d'embedding n'est configuré ou pendant un job de réindexation active / en échec. La route doit lever 422 `ERR_NO_ACTIVE_EMBEDDING_MODEL` ou 503 `ERR_RAG_REINDEX_IN_PROGRESS`.
3. **[MAJEUR M4] Route de tour `/threads/{thread_id}/turns` et routes Assistant non protégées de façon unifiée** :
   - La route collaborative `/threads/{thread_id}/turns` déclenchait un tour sans vérifier l'état du RAG ni la disponibilité du modèle d'embedding.
   - Nécessité de factoriser en une dépendance FastAPI unique (`require_rag_available`) injectée sur toutes les routes déclenchant un tour d'Assistant ou une recherche RAG, assortie d'un test d'audit qui inspecte l'application FastAPI et échoue si une route Assistant/RAG n'intègre pas cette dépendance.
4. **[MAJEUR M1] Repli en mémoire `InMemoryReindexManager` en production** :
   - Dans `dependencies/portal_and_assistant.py` et `routers/_ai_models_reindex_helpers.py`, un repli sur `default_in_memory_reindex_manager` était présent si `request.app.state.db_engine` était `None`.
   - Violation de la politique `GEMINI.md` (*« keep InMemory\* stores exclusively under tests/unit/fakes/ »*).
   - Solution : déplacer `InMemoryReindexManager` sous `tests/unit/fakes/in_memory_reindex.py` et forcer l'usage exclusif de PostgreSQL via `get_or_create_shared_db_engine(request)` en production.
5. **[MAJEUR M2] Duplication stricte du routage d'URL chat entre `ai_models_connection.py` et `assistant_llm_providers.py`** :
   - Les fonctions de normalisation d'URL et détection de protocoles (`_is_anthropic`, `_is_gemini_native`, `_normalize_chat_url`, `_build_legacy_local_chat_url`) étaient dupliquées ligne pour ligne.
   - Solution : extraction dans un module pur `packages/orcia-core/src/orcia_core/orchestration/ai_models_urls.py` (sans framework) réutilisé par `ai_models_connection.py` et `apps/api/src/orcia_api/routers/assistant_llm_providers.py`.
6. **[MAJEUR M3] Absence de clause d'étanchéité modèle dans `search_hybrid_rrf` (`sql_repository.py`)** :
   - La requête RRF hybride n'avait aucun filtre sur `c.embedding_model_id = :active_model_id`.
   - Risque théorique de calcul de distance cosinus entre espaces vectoriels hétérogènes si des chunks d'anciens modèles coexistaient.
   - Solution : paramètre `embedding_model_id: str | None = None` avec clause SQL `AND (:active_model_id IS NULL OR c.embedding_model_id = CAST(:active_model_id AS uuid) OR c.embedding IS NULL)`.
7. **[MINEUR m1 & m2] Fuite client HTTP worker et volumétrie `sql_reindex.py`** :
   - `httpx.AsyncClient` non fermé dans `rag_reindexer.py` -> ajout d'un `finally: await http_client.aclose()`.
   - `sql_reindex.py` (588 lignes) dépassant les 400 lignes de la politique `GEMINI.md` -> scission modulaire en `sql_reindex_jobs.py` et `sql_reindex_chunks.py`.

### 1.2 Exploration, Analyse d'Impact GitNexus, Factorisation & Dette Technique
- **Analyse d'Impact GitNexus** :
  - `execute_rag_reindex_worker_job_async` : impacte le worker Dramatiq `apps/worker/src/orcia_worker/rag_reindexer.py`.
  - `get_embedding_port` / `require_rag_available` : impacte `portal_and_assistant.py`, `portal_and_help.py`, `assistant.py`, `assistant_workspace.py`, `assistant_workspace_folders.py`, `ontology_and_rag.py`.
  - `search_hybrid_rrf` : impacte `packages/orcia-core/src/orcia_core/rag/_internal/sql_repository.py` et les routeurs appelants.
  - `normalize_chat_completions_url` / helpers d'URL : impacte `ai_models_connection.py` et `assistant_llm_providers.py`.
- **Opportunités de Factorisation & Contrôle de Volumétrie** :
  - Extraction de `ai_models_urls.py` dans `orcia_core` éliminant 60 lignes de duplication.
  - Découpage de `sql_reindex.py` (588 lignes) en `sql_reindex_jobs.py` (~280 lignes) et `sql_reindex_chunks.py` (~300 lignes).
  - Centralisation de la dépendance `require_rag_available` garantissant qu'aucune route ne réimplémente sa propre logique de verrouillage.

---

## 2. Plan d'Implémentation

### 2.1 Schéma de Données & Migrations Alembic
- Aucune nouvelle migration de schéma nécessaire : les tables `kb_chunks` (colonnes `embedding_model_id`, `embedding_generated_at`) et `rag_reindex_jobs` sont déjà créées et testées réversibles par les révisions `20261115_2206` et `20261115_2307`.

### 2.2 Noyau Métier Hexagonal, Orchestration & Workers (`packages/orcia-core/`, `apps/worker/`)
1. **Extraction de `ai_models_urls.py` (`packages/orcia-core/src/orcia_core/orchestration/ai_models_urls.py`)** :
   - Module pur sans dépendances externes.
   - Fonctions : `is_anthropic_provider`, `is_gemini_native_provider`, `normalize_chat_completions_url`, `build_legacy_local_chat_url`.
   - Réutilisation dans `ai_models_connection.py` et réexportation pour compatibilité.
2. **Clause d'étanchéité modèle dans `packages/orcia-core/src/orcia_core/rag/_internal/sql_repository.py`** :
   - Ajout du paramètre `embedding_model_id: str | None = None` dans `search_hybrid_rrf`.
   - Injection du paramètre SQL `:active_model_id` et clause `AND (:active_model_id IS NULL OR c.embedding_model_id = CAST(:active_model_id AS uuid) OR c.embedding IS NULL)`.
3. **Scission modulaire de `packages/orcia-core/src/orcia_core/rag/_internal/sql_reindex.py`** :
   - `sql_reindex_jobs.py` : création, complétion, échec, lecture de jobs de réindexation.
   - `sql_reindex_chunks.py` : fetch de chunks non indexés, batch update de chunks avec embedding et model_id, mise en attente d'ingestions.
   - `sql_reindex.py` : module façade réexportant l'ensemble de l'API publique sous 40 lignes.
4. **Correction du Worker Dramatiq (`apps/worker/src/orcia_worker/rag_reindexer.py`)** :
   - Résolution de la clé maîtresse AES-256-GCM via `get_env("ORCIA_PASSTHROUGH_MASTER_KEY", "orcia-story-1-2-aes256gcm-master-key-2026")`.
   - Support d'un paramètre optionnel `vault_cipher: PassthroughVaultCipherProtocol | None = None`.
   - Gestion stricte de `httpx.AsyncClient` avec fermeture via `try ... finally: await http_client.aclose()`.
5. **Déplacement de `InMemoryReindexManager`** :
   - Retrait de `packages/orcia-core/src/orcia_core/rag/reindex.py`.
   - Création de `tests/unit/fakes/in_memory_reindex.py` avec `InMemoryReindexManager`.
   - Export dans `tests/unit/fakes/__init__.py`.

### 2.3 Couche Backend API, Sécurité & Contrats (`apps/api/`)
1. **Création de la dépendance unifiée `require_rag_available` (`apps/api/src/orcia_api/dependencies/portal_and_assistant.py`)** :
   - Utilisation de `get_or_create_shared_db_engine(request)` pour vérifier l'état opérationnel du RAG via `check_rag_operational_on_conn(conn)` sur PostgreSQL 18.
   - Résolution du modèle actif GLOBAL via `get_active_global_embedding_model_pg18`.
   - Levée de `RagReindexInProgressError` (503) et `NoActiveEmbeddingModelError` (422).
   - Retour de l'`EmbeddingPort` actif.
2. **Protection stricte de `GET /api/v1/search` (`apps/api/src/orcia_api/routers/portal_and_help.py`)** :
   - Injection de `_embedding_port: Annotated[EmbeddingPort, Depends(require_rag_available)]`.
   - Suppression du bloc `try ... except (NoActiveEmbeddingModelError, RagReindexInProgressError): query_embedding = None` : aucune recherche même lexicale n'est autorisée si le RAG est indisponible ou sans modèle.
3. **Protection de la route `/threads/{thread_id}/turns` (`apps/api/src/orcia_api/routers/assistant_workspace_folders.py`)** :
   - Injection de `_embedding_port: Annotated[EmbeddingPort, Depends(require_rag_available)]`.
4. **Harmonisation des routes Assistant/RAG** :
   - Vérification et injection de `require_rag_available` sur `/assistant/chat`, `/assistant/chat/stream`, `/assistant/three-speed/turn`, `/assistant/three-speed/stream`, `/ontology-rag/rag/search`, `/ontology-rag/rag/index-db-ddl`.
5. **Alignement de `assistant_llm_providers.py`** :
   - Importation des helpers d'URL depuis `orcia_core.orchestration.ai_models_urls`.
6. **Suppression de tout usage de `default_in_memory_reindex_manager` en prod** :
   - Dans `_ai_models_reindex_helpers.py`, résolution systématique via `get_or_create_shared_db_engine(request)`.

### 2.4 Interface Utilisateur & Expérience (`apps/web/`)
- Aucune régression UI : les erreurs HTTP 422 `ERR_NO_ACTIVE_EMBEDDING_MODEL` et HTTP 503 `ERR_RAG_REINDEX_IN_PROGRESS` sont déjà mappées aux bannières Direction C et à la désactivation des contrôles interactifs.

### 2.5 Analyse d'Impact sur la Pyramide des Tests (`AD-17`)
- **Couche 1a (Unitaires)** :
  - Test unitaire du déchiffrement avec la vraie clé maîtresse dans `rag_reindexer.py`.
  - Test d'audit énumérant toutes les routes FastAPI Assistant et RAG et affirmant la présence de `require_rag_available` (ou `get_embedding_port`).
  - Test d'isolation de `InMemoryReindexManager` sous `tests/unit/fakes/in_memory_reindex.py`.
  - Test unitaire de `ai_models_urls.py`.
- **Couche 2 (Intégration PostgreSQL 18)** :
  - Test de `GET /api/v1/search` renvoyant 422 sans modèle et 503 pendant un job de réindexation.
  - Test de filtrage `search_hybrid_rrf` avec deux modèles différents vérifiant l'étanchéité vectorielle.
  - Test d'exécution du worker Dramatiq `execute_rag_reindex_worker_job_async` avec clé API chiffrée via `ORCIA_PASSTHROUGH_MASTER_KEY`.
- **Couche 3 (Contrats API & Lint)** :
  - Vérification `ruff`, `mypy --strict`, `lint-imports` (zéro violation).

---

## 3. Bilan des Modifications & Résultats (Post-Implémentation)
### 3.1 Tableau récapitulatif des fichiers créés et modifiés

| Fichier | Type d'action | Périmètre | Rôle & Justification |
| :--- | :--- | :--- | :--- |
| `packages/orcia-core/src/orcia_core/orchestration/ai_models_urls.py` | Création | Noyau hexagonal | Fonctions pures agnostiques de normalisation et détection protocolaire (M2) |
| `packages/orcia-core/src/orcia_core/orchestration/ai_models_connection.py` | Modification | Noyau hexagonal | Suppression de la duplication, délégation à `ai_models_urls.py` |
| `apps/api/src/orcia_api/routers/assistant_llm_providers.py` | Modification | API FastAPI | Réutilisation des helpers d'URL de `ai_models_urls.py` |
| `apps/worker/src/orcia_worker/rag_reindexer.py` | Modification | Worker Dramatiq | Utilisation de la vraie clé maîtresse `ORCIA_PASSTHROUGH_MASTER_KEY` et fermeture du client HTTP (B1, m1) |
| `tests/unit/fakes/in_memory_reindex.py` | Création | Fakes de test | Déplacement de `InMemoryReindexManager` hors de la production (M1) |
| `tests/unit/fakes/__init__.py` | Modification | Fakes de test | Export du fake `InMemoryReindexManager` pour les tests unitaires |
| `packages/orcia-core/src/orcia_core/rag/reindex.py` | Modification | Noyau RAG | Retrait des classes `InMemory*` de la production |
| `packages/orcia-core/src/orcia_core/rag/_internal/sql_repository.py` | Modification | Stockage RAG | Ajout du filtre `embedding_model_id = <modèle actif>` dans la branche vectorielle (M3) |
| `packages/orcia-core/src/orcia_core/rag/_internal/sql_reindex_chunks.py` | Création | Stockage RAG | Découpage batches chunks SQL (< 160 lignes) (m2) |
| `packages/orcia-core/src/orcia_core/rag/_internal/sql_reindex_jobs.py` | Création | Stockage RAG | Découpage gestion jobs SQL (< 300 lignes) (m2) |
| `packages/orcia-core/src/orcia_core/rag/_internal/sql_reindex_lifecycle.py` | Création | Stockage RAG | Découpage cycle de vie et outbox (< 170 lignes) (m2) |
| `packages/orcia-core/src/orcia_core/rag/_internal/sql_reindex.py` | Modification | Stockage RAG | Façade unifiée sans duplication (< 40 lignes) |
| `apps/api/src/orcia_api/dependencies/portal_and_assistant.py` | Modification | Injection API | Dépendance factorisée `require_rag_available` et suppression fallback in-memory (M1, M4) |
| `apps/api/src/orcia_api/dependencies/__init__.py` | Modification | Injection API | Export de `require_rag_available` |
| `apps/api/src/orcia_api/routers/_ai_models_reindex_helpers.py` | Modification | API FastAPI | Utilisation exclusive de PostgreSQL en production |
| `apps/api/src/orcia_api/routers/portal_and_help.py` | Modification | API FastAPI | Protection `GET /api/v1/search` avec 422 et 503 sans swallow lexical (B2) |
| `apps/api/src/orcia_api/routers/assistant_workspace_folders.py` | Modification | API FastAPI | Protection `/threads/{id}/turns` via `require_rag_available` (M4) |
| `apps/api/src/orcia_api/routers/assistant.py` | Modification | API FastAPI | Protection `/chat` et `/chat/stream` via `require_rag_available` (M4) |
| `apps/api/src/orcia_api/routers/assistant_workspace.py` | Modification | API FastAPI | Protection `/three-speed/turn` et `/stream` via `require_rag_available` (M4) |
| `apps/api/src/orcia_api/routers/ontology_and_rag.py` | Modification | API FastAPI | Protection `/rag/search` et `/rag/index-db-ddl` via `require_rag_available` (M4) |
| `tests/unit/test_assistant_and_rag_routes_require_rag_guard_audit.py` | Création | Couche 1 Unit | Audit automatique de toutes les routes FastAPI Assistant & RAG (M4) |
| `tests/unit/test_rag_reindexer_vault_cipher_and_http_closure.py` | Création | Couche 1 Unit | Déchiffrement avec vraie clé maîtresse et fermeture httpx worker (B1, m1) |
| `tests/unit/test_story_19_7_rag_reindexing_and_blocking.py` | Modification | Couche 1 Unit | Adaptation des tests avec le fake in-memory isolé |
| `tests/unit/test_story_19_5_ai_models_usage_and_uniqueness.py` | Modification | Couche 1 Unit | Utilisation du fake manager isolé |
| `tests/integration/api/test_story_19_7_reindexing_and_blocking_postgres18.py` | Modification | Couche 2 Integration | 3 nouveaux tests PG18 : 422/503 HTTP search, déchiffrement worker, isolation vectorielle RRF |

### 3.2 Résultats des Gates et Validation des 5 Couches AD-17

- **Ruff linter** : `All checks passed!` (`.venv/bin/ruff check .`).
- **Ruff formatter** : `847 files already formatted` (`.venv/bin/ruff format --check .`).
- **Lint-imports** : `Contracts: 5 kept, 0 broken` (`.venv/bin/lint-imports`).
- **Mypy strict** : `Success: no issues found in 357 source files` (`.venv/bin/mypy packages/orcia-core/src apps/api/src apps/worker/src packages/orcia-connectors/src`).
- **Couche 1 (Tests unitaires & audit)** : 76 tests passés (`76 passed in 21.36s`).
  - `test_assistant_and_rag_routes_require_rag_guard_audit.py` : valide que 100% des routes RAG et Assistant portent `require_rag_available`.
  - `test_rag_reindexer_vault_cipher_and_http_closure.py` : valide le déchiffrement avec la vraie clé maîtresse et la fermeture du client HTTP.
  - `test_codebase_architectural_anti_patterns_audit.py` : 0 violation anti-pattern.
- **Couche 2 (Tests d'intégration PostgreSQL 18)** : 6 tests passés sur testcontainer éphémère (`6 passed in 19.52s`).
  - Validation du code HTTP 422 `ERR_NO_ACTIVE_EMBEDDING_MODEL` et HTTP 503 `ERR_RAG_REINDEX_IN_PROGRESS` sur `GET /api/v1/search`.
  - Validation du déchiffrement de l'API key par le worker avec `ORCIA_PASSTHROUGH_MASTER_KEY` persistée dans PG18.
  - Validation de l'isolation vectorielle stricte par `embedding_model_id` dans `SqlHybridRagRepository.search_hybrid_rrf`.
- **Contrôle de volumétrie** : Aucun fichier ne dépasse 300 lignes (`sql_reindex_jobs.py` = 293 lignes, `sql_reindex_lifecycle.py` = 165 lignes, `sql_reindex_chunks.py` = 153 lignes, `sql_reindex.py` = 34 lignes).
