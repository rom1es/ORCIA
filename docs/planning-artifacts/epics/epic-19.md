## Epic 19: Hub Modèles IA Fiable, Découverte 0 Token, Test Réel & Embeddings Sémantiques (AD-24)

Éliminer toute illusion d'opérationnalité des modèles IA en découvrant automatiquement les modèles disponibles sans token dépensé (`0 $`), en assainissant la modale UI (placeholders dynamiques contextuels sans puces codées en dur trompeuses), en exécutant des tests de connectivité réels (chat `max_tokens=1` et validation stricte dimension 1024 pour embeddings) avec mesure réelle de la latence et restitution fine des erreurs HTTP RFC 9457, en purgeant intégralement le backend et l'amorçage Jour 0 de tout nom de modèle propriétaire codé en dur, en intégrant le rôle d'embedding dans le Hub avec un modèle unique GLOBAL, en remplaçant définitivement le hachage SHA-256 en production par de vrais embeddings vectoriels via `EmbeddingPort` HTTPX avec blocage explicite de toute indexation (ni chunks ni BM25) et de l'Assistant sans modèle actif (`ERR_NO_ACTIVE_EMBEDDING_MODEL`), en assurant une réindexation idempotente bloquante avec blocage total de la recherche RAG (HTTP 503 RFC 9457 `ERR_RAG_REINDEX_IN_PROGRESS` avec progression, zéro repli lexical dégradé), blocage complet de Mon Assistant (bannière avec % et saisie désactivée) et mise en file d'attente des nouvelles ingestions, et en maintenant strictement le Codegraph GitNexus à 0 token hors du périmètre des embeddings (`AD-8`, `AD-10`, `AD-16`, `AD-24`, `CAP-190`, `FR-14`, `FR-18`, `FR-23`, `FR-28`, `FR-31`, `FR-33`).

### Story 19.1: Modale UI Connecter un Modèle — Champs Vides, Placeholders Dynamiques par Fournisseur & Suppression des Puces Codées en Dur (D1)

As a Administrateur Plateforme / Responsable IA (`Karim UJ-9`),
I want que la modale d'ajout/modification d'un modèle démarre avec des champs textuels entièrement vides, des placeholders contextuels adaptés au fournisseur sélectionné, et sans aucune puce de suggestions codées en dur,
So that l'interface ne suggère jamais de modèles potentiellement absents de l'infrastructure de l'entreprise et force une configuration explicite ou issue d'une découverte dynamique (`AD-24.1`, `FR-31`, `UX-DR1`, `UX-DR2`).

**Dépendances :** Aucune (frontend autonome, mockable).
**Références :** `AD-24.1`, `FR-31`, `UX-DR1`, `UX-DR2`.
**Fichiers impactés connus :** `apps/web/src/features/settings/components/AiModelModal.tsx`, `apps/web/src/features/settings/components/AiModelForm.tsx`, `apps/web/src/i18n/locales/{fr,en}.ts`.
**Tests existants à adapter :** `apps/web/src/features/settings/__tests__/AiModelModal.test.tsx`, `tests/unit/test_codebase_architectural_anti_patterns_audit.py`.

**Acceptance Criteria:**

**Given** la modale `AiModelModal` (`OrciaDialog`) ouverte lors d'un clic sur `+ Connecter un modèle`
**When** l'utilisateur observe l'état initial des champs
**Then** les champs `model_name` et `base_url` sont strictement vides (`value === ""` sans pré-remplissage résiduel ni valeur par défaut cachée), et aucune puce de modèle codée en dur (`gpt-4o`, `claude-3-5-sonnet`, `mistral-large`, `nomic-embed-text`) n'est affichée dans le DOM (`AD-24.1`).

**Given** la sélection successive des tuiles radio de fournisseurs (`Ollama / vLLM`, `Mistral`, `OpenAI`, `Anthropic`, `Google Gemini`, `Custom OpenAI-compatible`)
**When** l'utilisateur commute de fournisseur
**Then** les placeholders des champs `base_url` et `model_name` s'adaptent dynamiquement (ex. Ollama : `http://localhost:11434` / `llama3.2:latest`, OpenAI : `https://api.openai.com/v1` / `gpt-4o-mini`, Custom : `https://mon-llm-interne.corp/v1`), tandis que les libellés et microcopies proviennent du dictionnaire typé `i18n` (zéro texte français en dur dans le JSX).

**Given** les 5 couches de validation `AD-17`
**When** les suites de tests sont exécutées
**Then** Couche 1 (Vitest) teste le changement de fournisseur, la vacuité initiale et l'absence de puces codées en dur ; Couche 3 valide le contrat OpenAPI 3.1 `0-diff` ; Couche 5 (Playwright) vérifie le montage accessible et l'absence de régression visuelle (`zero-dead-buttons-and-silent-catches-audit.test.tsx`).

---

### Story 19.2: Découverte Dynamique des Modèles 0 Token (`GET /models`), Combobox Filtrable & Saisie Libre (D2)

As a Administrateur Plateforme (`Karim UJ-9`),
I want que le Hub interroge automatiquement les métadonnées du fournisseur pour lister les modèles réels disponibles sans consommer de tokens d'inférence (`0 $`), et m'offre une combobox filtrable avec saisie libre,
So that je puisse sélectionner immédiatement un modèle vérifié sur mon instance locale ou distante sans risque d'erreur de frappe (`AD-24.2`, `FR-31`, `NFR-PERF-1`, `NFR-OBS-1`).

**Dépendances :** Indépendante du backend d'embedding (nécessite l'endpoint de découverte côté `apps/api` et le composant combobox côté `apps/web`).
**Références :** `AD-24.2`, `FR-31`, `NFR-PERF-1`, `NFR-OBS-1`.
**Fichiers impactés connus :** `apps/api/src/orcia_api/routers/ai_models.py`, `apps/api/src/orcia_api/schemas/ai_models.py`, `packages/orcia-core/src/orcia_core/llm/discovery.py`, `apps/web/src/features/settings/components/AiModelDiscoveryCombobox.tsx`.
**Tests existants à adapter :** `tests/unit/test_ai_models_router.py`, `apps/web/src/features/settings/__tests__/AiModelModal.test.tsx`.

**Acceptance Criteria:**

**Given** une URL et/ou une clé API renseignée pour un fournisseur (`Ollama`, `Mistral`, `OpenAI`, `Anthropic`, `vLLM` ou compatible)
**When** le bouton ou déclencheur de découverte `Découvrir les modèles` est sollicité (`GET /api/v1/settings/ai-models/discover?provider={provider}&base_url={url}`)
**Then** l'API backend effectue un appel réseau asynchrone non bloquant (`httpx.AsyncClient`) vers l'endpoint standard de métadonnées du fournisseur (`GET /api/tags` pour Ollama, `GET /v1/models` pour OpenAI/Mistral/vLLM) sans envoyer aucun prompt d'inférence (`0 token LLM consommé`, coût `0 $`), avec un timeout strict de `3 000 ms` et validation anti-SSRF (`is_safe_llm_endpoint_url`).

**Given** la réponse réussie du endpoint de découverte
**When** la liste des modèles est retournée au frontend
**Then** le champ `model_name` se transforme en combobox filtrable avec recherche textuelle instantanée, affichant les identifiants réels retournés (avec badge ou tag de contexte si disponible), tout en préservant la possibilité de saisie libre d'un identifiant non listé (mode fallback si l'endpoint `/models` est restreint).

**Given** un échec réseau ou un refus d'accès du endpoint de découverte (ex. proxy d'entreprise bloquant `GET /models` ou clé sans droit de lecture des métadonnées)
**When** la requête de découverte échoue
**Then** une notification non bloquante informe l'utilisateur sans bloquer le formulaire, et le champ `model_name` bascule en saisie libre standard sans perte des données déjà saisies.

---

### Story 19.3: Test de Connexion Réel Chat (`max_tokens=1`) & Embeddings (Validation Dim 1024), Latence Réelle & Erreurs RFC 9457 (D3)

As a Administrateur Plateforme / Responsable IA (`Karim UJ-9`),
I want tester la connectivité réelle de chaque modèle avec un appel minimal vérifié (chat `max_tokens=1` ou embedding sur chaîne test avec contrôle de dimension 1024), mesurer la latence aller-retour réelle et recevoir un diagnostic d'erreur RFC 9457 précis en cas d'échec,
So that aucun modèle étiqueté « Opérationnel » ne soit en réalité muet, bridé ou mal dimensionné (`AD-24.3`, `FR-14`, `FR-18`, `FR-31`, `NFR-OBS-1`, `NFR-TEST-1`).

**Dépendances :** Dépend de Story 19.5 pour la validation des modèles d'embedding via `EmbeddingPort`.
**Références :** `AD-24.3`, `FR-14`, `FR-18`, `FR-31`, `NFR-OBS-1`.
**Fichiers impactés connus :** `apps/api/src/orcia_api/routers/ai_models.py`, `packages/orcia-core/src/orcia_core/llm/connection_test.py`, `packages/orcia-core/src/orcia_core/llm/errors.py`, `apps/web/src/features/settings/components/AiModelConnectionTestButton.tsx`.
**Tests existants à adapter :** `tests/unit/test_ai_model_connection_test.py`, `tests/integration/test_ai_models_api_pg18.py`.

**Acceptance Criteria:**

**Given** un modèle de type chat / raisonnement enregistré ou en cours de saisie
**When** l'utilisateur déclenche le test de connexion (`POST /api/v1/settings/ai-models/mappings/{id}/test` ou `POST /test-connection`)
**Then** le backend envoie une requête réelle d'inférence minimale (`max_tokens=1`, prompt `"ping"`) via `httpx.AsyncClient` non bloquant, mesure le temps aller-retour précis en millisecondes (`latency_ms`), et valide le statut `OPERATIONAL` uniquement si le statut HTTP est 200 et qu'un token valide est retourné.

**Given** un modèle avec l'usage `embedding` (cf. Story 19.5)
**When** l'utilisateur déclenche son test de connexion
**Then** le backend soumet une chaîne test (`"orcia connection test"`) à l'API d'embeddings via `EmbeddingPort`, vérifie que le vecteur retourné contient exactement **1024 dimensions** de type flottant fini (`len(vector) == 1024` et tous nombres finis), et rejette avec `HTTP 422 ERR_EMBEDDING_DIMENSION_MISMATCH` si la dimension diffère de 1024 (ex. 768 ou 1536) en indiquant la dimension constatée et la dimension requise.

**Given** une erreur lors du test de connexion (authentification 401/403, modèle introuvable 404, rate limit 429, timeout ou URL inaccessible)
**When** le test échoue
**Then** l'API retourne une enveloppe **RFC 9457 Problem Details** enrichie (`error_code`, `status`, `detail`, `remediation_hint`, `raw_provider_status`, `trace_id`), sans masquer l'erreur dans un faux `200 OK`, et le Hub affiche le statut `ERROR` avec l'explication exploitable dans l'UI.

---

### Story 19.4: Suppression Intégrale des Noms de Modèles en Dur Backend, Tier Mappings Vides & Amorçage Jour 0 Propre (D4)

As a Développeur / Ingénieur Plateforme (`Karim UJ-9`),
I want que le backend, les constantes, les scripts de seed et l'amorçage Jour 0 soient intégralement purgés de tout nom de modèle propriétaire codé en dur et que les tier mappings soient initialisés vides,
So that ORCIA démarre dans un état neutre, souverain et gouverné, sans présumer des abonnements ou modèles disponibles dans l'infrastructure de déploiement (`AD-24.4`, `FR-28`, `FR-31`, `NFR-ISO-1`).

**Dépendances :** Aucune (backend / seeds autonome).
**Références :** `AD-24.4`, `FR-28`, `FR-31`.
**Fichiers impactés connus :** `packages/orcia-core/src/orcia_core/llm/constants.py`, `packages/orcia-core/src/orcia_core/llm/service.py`, `packages/orcia-core/src/orcia_core/bootstrap/seeder.py`, `infra/scripts/maintenance/09_reset_db_first_boot.py`, `apps/api/src/orcia_api/routers/ai_models.py`.
**Tests existants à adapter :** `tests/unit/test_ai_models_seeds.py`, `tests/integration/test_reset_db_first_boot.py`, `tests/unit/test_codebase_architectural_anti_patterns_audit.py`.

**Acceptance Criteria:**

**Given** le code source de `packages/orcia-core` et `apps/api`
**When** une recherche globale (grep / audit statique) est exécutée sur les constantes de seed
**Then** `DEFAULT_LLM_MODEL_ENDPOINT_SEEDS` et `build_default_tier_mappings` ne contiennent plus aucun nom de modèle propriétaire en dur (`gpt-4o`, `claude-3-5-sonnet`, `mistral-large`, `nomic-embed-text`), et toute valeur codée en dur est remplacée par des structures vides ou des gabarits configurables (`AD-24.4`).

**Given** une réinitialisation Jour 0 de la base de données via `pnpm db:reset` (`09_reset_db_first_boot.py --apply`)
**When** l'état initial des tables de modèles et de tiers est vérifié par `SELECT` SQL
**Then** la table `workspace_llm_tier_mappings` est initialisée avec `0` mapping ou des mappings non assignés (`model_id IS NULL`), et l'état Jour 0 est préservé sans injection de modèles fantômes.

**Given** un premier démarrage ou une réinitialisation Jour 0 via `pnpm db:reset` (`09_reset_db_first_boot.py --apply`)
**When** l'administrateur se connecte et accède à la plateforme ou au Cockpit
**Then** le wizard d'accueil / parcours d'onboarding Jour 0 guide explicitement l'administrateur vers la configuration obligatoire du modèle d'embedding dans `/settings/ai-models`, et Mon Assistant affiche d'emblée une bannière d'avertissement persistante avec désactivation complète de la zone de saisie et de tout envoi de message tant qu'aucun modèle d'embedding n'a été configuré et validé (`AD-16`, `AD-24.6`).

**Given** une tentative d'invocation d'un tier ou d'un workflow alors qu'aucun modèle n'est mappé
**When** le moteur LLM tente de résoudre le modèle pour un tier donné
**Then** il lève immédiatement `ERR_TIER_MODEL_NOT_CONFIGURED` avec une enveloppe RFC 9457 guidant l'utilisateur vers `/settings/ai-models` pour configurer le modèle manquant, sans tentative d'appel silencieux vers des endpoints inexistants.

---

### Story 19.5: Usage Embedding dans le Hub des Modèles, Port Hexagonal `EmbeddingPort` & Adaptateurs HTTPX (D5, D6)

As a Tech Lead / Architecte (`Winston`),
I want déclarer le rôle `embedding` dans le Hub des modèles IA, imposer la sélection d'un **modèle d'embedding unique GLOBAL** pour l'instance, et router les requêtes via un port hexagonal découplé `EmbeddingPort` avec adaptateurs HTTPX,
So that la génération de vecteurs sémantiques repose sur une interface standardisée sans aucun SDK vendeur ni couplage propriétaire (`AD-8`, `AD-24.5`, `AD-24.6`, `FR-23`, `FR-31`).

**Dépendances :** Précède Story 19.3 (partie embedding), Story 19.6 et Story 19.7.
**Références :** `AD-8`, `AD-24.5`, `AD-24.6`, `FR-23`, `FR-31`, `AD-19`.
**Fichiers impactés connus :** `packages/orcia-kernel/src/orcia_kernel/ports.py` (ou `packages/orcia-core/src/orcia_core/rag/ports.py`), `packages/orcia-core/src/orcia_core/rag/adapters/embedding_httpx.py`, `apps/api/src/orcia_api/schemas/ai_models.py`, `packages/orcia-core/src/orcia_core/llm/models.py`.
**Tests existants à adapter :** `tests/unit/test_embedding_port.py`, `tests/unit/test_ai_models_schemas.py`.

**Acceptance Criteria:**

**Given** la gestion des modèles dans `/settings/ai-models`
**When** un modèle est configuré ou modifié
**Then** un sélecteur d'usage permet de déclarer son rôle : `chat_reasoning`, `embedding`, ou `both` ; et un indicateur strict `is_primary_embedding: true` garantit qu'exactement **un seul modèle d'embedding actif** est désigné au niveau GLOBAL de l'instance ORCIA (`AD-24.5`). Si un nouveau modèle est désigné comme primaire, l'ancien est automatiquement basculé en inactif pour l'embedding.

**Given** le contrat hexagonal `EmbeddingPort`
**When** un appel `embed_texts(texts: list[str]) -> list[list[float]]` ou `embed_query(query: str) -> list[float]` est exécuté
**Then** l'appel passe par un adaptateur HTTPX (`HttpxEmbeddingAdapter`) sans aucun SDK tiers (`openai`, `anthropic`, `litellm`), couvrant nativement :
- `gemini_native` via `:batchEmbedContents` avec le paramètre obligatoire `output_dimensionality=1024` ;
- `openai_compatible` via `/v1/embeddings` avec transmission de `dimensions=1024` lorsque supporté par le modèle (OpenAI `text-embedding-3`, TEI, vLLM) ;
- Ollama en privilégiant son endpoint standard compatible OpenAI `/v1/embeddings` ou natif `/api/embed` (l'ancien endpoint `/api/embeddings` déprécié étant formellement banni) ;
- et excluant formellement le fournisseur `Anthropic` qui n'offre aucune API native d'embeddings ;
tout en vérifiant rigoureusement que la dimension de chaque vecteur retourné est exactement de 1024 (rejet par `ERR_EMBEDDING_DIMENSION_MISMATCH` sinon) et en levant `ERR_EMBEDDING_GENERATION_FAILED` en cas d'erreur réseau HTTP (`AD-24.4`, `AD-24.6`).

**Given** la vérification architecturale `lint-imports`
**When** l'ordonnancement des dépendances est audité
**Then** `EmbeddingPort` réside dans le noyau hexagonal sans aucune importation vers `fastapi`, `sqlalchemy` ou des SDK externes, respectant strictement `AD-19`.

---

### Story 19.6: Migration Alembic, Suppression Intégrale du Hachage SHA-256 en Prod & Blocage sans Modèle (D7, D8, D10, D11)

As a Tech Lead / Développeur Backend (`Amelia`),
I want exécuter la migration de schéma Alembic, supprimer définitivement tout repli sur le pseudo-hachage SHA-256 en runtime de production, et bloquer immédiatement toute indexation de source si aucun modèle d'embedding n'est configuré,
So that le RAG d'ORCIA ne stocke plus jamais de vecteurs factices et garantisse une sémantique vectorielle réelle de bout en bout (`AD-8`, `AD-24.7`, `AD-24.8`, `AD-24.10`, `AD-24.11`, `FR-23`).

**Dépendances :** Dépend de Story 19.5 (`EmbeddingPort` requis). Précède Story 19.7.
**Références :** `AD-8`, `AD-24.7`, `AD-24.8`, `AD-24.10`, `AD-24.11`, `FR-23`.
**Fichiers impactés connus :** `infra/migrations/versions/0019_add_embedding_model_metadata.py`, `packages/orcia-core/src/orcia_core/rag/service.py`, `packages/orcia-core/src/orcia_core/rag/indexer.py`, `packages/orcia-core/src/orcia_core/rag/vector.py` (ou suppression de `compute_deterministic_halfvec_1024` vers `tests/unit/fakes/`).
**Tests existants à adapter :** `tests/unit/test_rag_service.py`, `tests/unit/test_differentiated_indexer.py`, `tests/integration/test_rag_pipeline_pg18.py`.

**Acceptance Criteria:**

**Given** la migration Alembic `0019` (ou numéro séquentiel suivant)
**When** la migration est appliquée via `.venv/bin/alembic upgrade head`
**Then** elle ajoute les colonnes de métadonnées de traçabilité d'embedding sur `kb_chunks` (`embedding_model_id UUID REFERENCES workspace_llm_tier_mappings(id)`, `embedding_generated_at TIMESTAMP`) avec clauses `upgrade()` et `downgrade()` testées sous PostgreSQL 18 `testcontainers` (`AD-24.7`).

**Given** le runtime de production de `packages/orcia-core/rag`
**When** l'indexeur différentiel traite des documents ou chunks
**Then** la fonction de pseudo-hachage `compute_deterministic_halfvec_1024` est totalement éliminée du code applicatif de production et déplacée exclusivement sous `tests/unit/fakes/fake_embeddings.py` pour les tests unitaires hors ligne (`AD-24.8`).

**Given** une source documentaire dont l'indexation est déclenchée alors qu'aucun modèle d'embedding n'est configuré ou validé (`is_primary_embedding = true` absent, que ce soit au Jour 0 après `pnpm db:reset` ou suite à la suppression d'un modèle)
**When** `DifferentiatedIncrementalIndexer` ou `POST /api/v1/workspaces/{ws_id}/datasources/{id}/sync` s'exécute
**Then** l'ingestion est totalement bloquée avec émission de l'erreur harmonisée `HTTP 422 ERR_NO_ACTIVE_EMBEDDING_MODEL` (aucun chunk n'est inséré dans `kb_chunks`, aucun index lexical BM25 n'est généré : zéro chunk sans vecteur, zéro corruption d'état), et la source passe en statut `AWAITING_EMBEDDING_MODEL` (`AD-24.6`).

**Given** l'absence de modèle d'embedding actif (`is_primary_embedding = true` absent, au Jour 0 après `pnpm db:reset` ou après suppression/désactivation d'un modèle)
**When** un utilisateur accède à Mon Assistant dans le Cockpit ou soumet une requête de recherche RAG directe
**Then** la recherche RAG retourne immédiatement l'enveloppe RFC 9457 avec le code d'erreur harmonisé `ERR_NO_ACTIVE_EMBEDDING_MODEL`, et Mon Assistant est totalement bloqué : une bannière persistante indique que le modèle d'embedding est manquant avec un lien d'action direct vers `/settings/ai-models`, et le champ d'entrée de texte ainsi que le bouton d'envoi de message sont matériellement désactivés (`disabled = true`, aucun envoi de prompt possible) (`AD-24.6`).

**Given** l'exploration et l'analyse de code via Codegraph / GitNexus
**When** une source `SOURCE_CODE` est synchronisée avec `codegraph_enabled = true`
**Then** GitNexus génère son graphe de symboles déterministe AST de manière souveraine à `0 token LLM`, strictement indépendant du pipeline d'embeddings textuels RAG (`AD-24.11`).

---

### Story 19.7: Réindexation Bloquante Idempotente, Suivi de Progression & Verrouillage Assistant/Recherche (D9, D12)

As a Administrateur Plateforme / Responsable IA (`Karim UJ-9`),
I want déclencher une réindexation globale bloquante et idempotente lors de l'enregistrement ou du changement du modèle d'embedding, suivre sa progression, et verrouiller totalement la recherche vectorielle et l'assistant sans mode dégradé,
So that aucun calcul de similarité cosinus incohérent ne soit exécuté entre des espaces vectoriels de modèles différents (`AD-24.7`, `FR-23`, `FR-31`, `FR-33`).

**Dépendances :** Dépend de Story 19.5 et Story 19.6.
**Références :** `AD-24.7`, `FR-23`, `FR-31`, `FR-33`, `NFR-REL-1`, `NFR-OBS-1`.
**Fichiers impactés connus :** `packages/orcia-core/src/orcia_core/rag/service.py`, `packages/orcia-core/src/orcia_core/rag/reindex.py`, `apps/api/src/orcia_api/routers/rag.py`, `apps/web/src/features/settings/components/AiModelReindexProgressModal.tsx`, `apps/web/src/features/cockpit/components/ChatAssistantInput.tsx`.
**Tests existants à adapter :** `tests/unit/test_rag_reindexing.py`, `tests/integration/test_rag_reindexing_pg18.py`.

**Acceptance Criteria:**

**Given** un changement ou une première configuration du modèle d'embedding principal (`POST /api/v1/settings/ai-models/reindex-embeddings`)
**When** la réindexation est initiée
**Then** elle acquiert un verrou d'indexation exclusif (`ResourceLeasePort` / Redis `lock:rag:reindex`), met à jour le statut global `reindexing_status = IN_PROGRESS`, et recalcule les vecteurs 1024 de tous les `kb_chunks` existants par lots idempotents (`batch_size = 50`), avec mise à jour continue de `progress_percentage`, `processed_chunks` et `total_chunks` (`AD-24.7`).

**Given** une réindexation globale en cours (`reindexing_status == IN_PROGRESS`)
**When** un utilisateur effectue une recherche RAG (`TwoSpeedFederatedSearchService`, recherche `⌘K` ou endpoint API) ou sollicite Mon Assistant (`AssistantHarness`)
**Then** aucun mode dégradé lexical ni repli Vitesse 1 n'est toléré :
- toute recherche RAG est immédiatement rejetée avec le statut **`HTTP 503 Service Unavailable`** au format RFC 9457 Problem Details portant le code **`ERR_RAG_REINDEX_IN_PROGRESS`** et incluant le pourcentage d'avancement (`progress_percentage`) ;
- Mon Assistant est **totalement bloqué** : l'interface affiche une bannière d'indisponibilité bloquante avec la progression en temps réel (`Réindexation sémantique en cours : {progress}%`), et la zone de saisie textuelle ainsi que le bouton d'envoi de message sont matériellement désactivés (`disabled = true`, aucun envoi de prompt possible tant que le recalcul n'est pas terminé) (`AD-24.7`).

**Given** de nouvelles tentatives d'ingestion documentaire pendant la réindexation (`reindexing_status == IN_PROGRESS`)
**When** une synchronisation de datasource ou un webhook Confluence/Jira/Git arrive
**Then** les ingestions documentaires ne sont pas traitées immédiatement mais automatiquement suspendues et placées dans une file d'attente persistante (`rag_reindexing_pending_ingestions`), garantissant qu'aucun calcul vectoriel concurrent ne s'exécute sur l'ancien modèle et que l'ingestion reprendra dès la fin de la réindexation (`AD-24.7`).

**Given** l'achèvement réussi de la réindexation
**When** le dernier lot est persisté
**Then** le verrou est libéré, `reindexing_status` passe à `COMPLETED`, un événement outbox `EmbeddingReindexCompleted` est émis, et la recherche hybride RRF (`halfvec(1024)` HNSW + `tsvector` GIN) redevient immédiatement disponible avec 100 % de vecteurs homogènes générés par le nouveau modèle actif.

**Given** aucun chunk documentaire ni source documentaire à réindexer (total = 0, ex. Jour 0 après `pnpm db:reset`)
**When** un modèle d'embedding est activé ou changé
**Then** le job passe directement à `COMPLETED` (traçé avec `EmbeddingReindexStarted` et `EmbeddingReindexCompleted`, idempotent) SANS phase de blocage visible : aucune réponse 503 `ERR_RAG_REINDEX_IN_PROGRESS`, aucune bannière « Réindexation 0 % », Assistant immédiatement débloqué.

**Given** les 5 couches de validation `AD-17` de l'ensemble de l'Epic 19
**When** toutes les suites de tests et portes de gouvernance sont exécutées
**Then** couverture unitaire $\ge 90\%$ sur `orcia_core/llm` et `orcia_core/rag`, tests d'intégration réels sur PostgreSQL 18 + `pgvector` avec `testcontainers`, contrats OpenAPI 3.1 `0-diff`, cassettes déterministes CI et tests Playwright passent sans aucun warning ni contournement.

---
