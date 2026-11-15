# Story 19.2 — Découverte Dynamique des Modèles 0 Token (`GET /models`), Combobox Filtrable & Saisie Libre (D2)

- **Date** : 2026-11-15
- **Story / Clé Sprint** : `19-2-decouverte-dynamique-modeles-0-token-combobox-filtrable-et-saisie-libre` (Epic 19)
- **Capacité(s)** : `CAP-190` (Hub Modèles IA Fiable, Découverte Dynamique 0 Token, Test Réel & Embeddings Sémantiques) — classification : `feature`
- **Auteur / Contexte** : Tech Lead / Senior Dev (`bmad-dev-worker`). Implémentation de la décision validée **D2** d'ORCIA : permettre aux administrateurs de découvrir automatiquement les modèles publiés par les fournisseurs IA locaux (Ollama, vLLM) et distants (OpenAI, Mistral, Anthropic, Google Gemini) via leurs endpoints de métadonnées standard, avec un coût de **0 token d'inférence** (`0 $`), sans fuite de clé secrète, avec garde-fou anti-SSRF, et offrir dans l'interface une combobox accessible RGAA filtrable par saisie textuelle et par type d'usage (`chat` vs `embedding`), tout en garantissant en permanence la possibilité d'une saisie libre sans blocage en cas d'indisponibilité du endpoint de découverte.
- **Commits associés** : à compléter en Section 3.

---

## 1. Analyse du Besoin & Étude d'Impact Tech Lead (Pré-Implémentation)

### 1.1 Contexte & Problématique
1. **Absence d'auto-complétion et risque d'erreur de saisie** : Jusqu'à présent, l'administrateur devait saisir manuellement l'identifiant exact du modèle (`gpt-4o-mini`, `mistral-large-latest`, `claude-3-5-sonnet-20241022`, `gemini-1.5-pro`, `llama3.2:latest`, etc.). Une simple faute de frappe conduisait à des échecs d'inférence au runtime.
2. **Nécessité d'une découverte 0 token (`0 $`)** : Aucun appel de complétion ou de génération ne doit être émis pour lister les modèles disponibles. Tous les grands fournisseurs exposent des endpoints HTTP légers de métadonnées (`/v1/models` pour OpenAI, Mistral, Anthropic, vLLM ; `/api/tags` pour Ollama ; `/v1beta/models` pour Google Gemini).
3. **Sécurité & Zero Secret Leakage** : L'appel de découverte doit accepter soit un secret transitoire saisi dans la modale (jamais loggé, jamais persisté par cet appel), soit un `mapping_id` existant dont la clé est déchiffrée en mémoire via le coffre `AES-256-GCM` (`SecretRef`). La réponse ne doit jamais renvoyer la clé secrète ni d'informations confidentielles.
4. **Protection SSRF et RBAC** : L'URL du point de terminaison doit être validée par `is_safe_llm_endpoint_url` (rejet strict des adresses de métadonnées link-local ou Cloud `169.254.0.0/16`, `100.100.100.200`, `metadata.google.internal`). Les utilisateurs en mode `READ_ONLY_OBSERVER` doivent être rejetés avec `HTTP 403 ERR_OBSERVER_MODE_READ_ONLY`.
5. **Expérience Utilisateur & Direction C** :
   - Le champ « Identifiant du modèle » (principal et de secours) se dote d'une combobox filtrable accessible (@orcia/ui), réactive et fluide.
   - Saisie libre systématiquement préservée : si un modèle n'apparaît pas dans la liste (ou si le fournisseur bloque la liste), l'utilisateur tape directement ce qu'il souhaite.
   - Filtrage intelligent par type d'usage : lorsque le fournisseur fournit des métadonnées de capacité (notamment Google Gemini `supportedGenerationMethods` distinguant `generateContent` vs `embedContent`), les modèles incompatibles avec l'usage actif du formulaire (`chat` ou `embedding`) sont filtrés. Pour les autres fournisseurs sans typage strict, `usage_hint: "unknown"` est retourné et les modèles restent visibles pour éviter tout faux négatif.

### 1.2 Exploration, Analyse d'Impact GitNexus, Factorisation & Dette Technique
- **Analyse d'Impact GitNexus (`gitnexus_impact`)** :
  - `apps/api/src/orcia_api/routers/ai_models_hub.py` : appelants directs dans `main.py` ; risque faible. Le routeur approche 356 lignes ; la logique d'interrogation réseau et de mapping des protocoles sera factorisée dans un module dédié `packages/orcia-core/src/orcia_core/orchestration/ai_models_discovery.py` et son helper associé afin d'éviter le surpoids du routeur.
  - `apps/web/src/features/admin/ai-models/AiModelFormFields.tsx` & `AiModelConfigModal.tsx` : composants modaux appelés par `SettingsAiModelsSection.tsx` ; risque faible.
- **Opportunités de Factorisation & Contrôle de Volumétrie** :
  - Création du composant générique accessible `@orcia/ui` `OrciaModelCombobox` (`packages/ui/src/primitives/OrciaModelCombobox.tsx`) réutilisant les utilitaires de normalisation de recherche `comboboxSearchUtils.ts` déjà éprouvés dans `OrciaSearchableSelect` et `OrciaKnownUserCombobox`.
  - Zéro duplication de requêtes HTTP : extraction du client de découverte dans `ai_models_discovery.py` acceptant le `httpx.AsyncClient` partagé (`app.state.http_client`).
- **Erreurs RFC 9457 & Localisation** :
  - Déclaration des erreurs typées dans `packages/orcia-core/src/orcia_core/orchestration/ai_models_errors.py` :
    - `ModelDiscoveryAuthFailedError` (401, `ERR_MODEL_DISCOVERY_AUTH_FAILED`)
    - `ModelDiscoveryEndpointNotFoundError` (404, `ERR_MODEL_DISCOVERY_NOT_SUPPORTED`)
    - `ModelDiscoveryNetworkError` (502, `ERR_MODEL_DISCOVERY_NETWORK_ERROR`)
  - Enregistrement bilingue fr/en dans `AI_MODELS_ERROR_CATALOG` et dans `apps/api/src/orcia_api/errors/registry.py`.

---

## 2. Plan d'Implémentation

### 2.1 Schéma de Données & Migrations Alembic
- Aucun changement de schéma PostgreSQL requis pour cette story : la découverte est une opération stateless d'interrogation de métadonnées à la volée.

### 2.2 Noyau Métier Hexagonal, Orchestration & Workers (`packages/orcia-core/`)
- `packages/orcia-core/src/orcia_core/orchestration/ai_models_discovery.py` :
  - Fonction pure asynchrone `discover_models_from_provider(...)` :
    - Valide l'URL anti-SSRF via `validate_safe_llm_endpoint_url`.
    - Timeout court strict de 5.0 secondes.
    - Support des protocoles :
      - `openai_compatible` : tente `GET {base}/v1/models` avec `Authorization: Bearer <key>` ; si 404 et slug ollama, tente `GET {base}/api/tags` ;
      - `anthropic_messages` : `GET {base}/v1/models` avec en-têtes `x-api-key` et `anthropic-version: 2023-06-01` ;
      - `gemini_native` : `GET {base}/v1beta/models` avec en-tête `x-goog-api-key`, gestion de la pagination `pageToken` (limite de sécurité 250 modèles), typage `usage_hint` (`chat` si `generateContent`, `embedding` si `embedContent`).
    - Traduction unifiée des erreurs HTTP en erreurs du domaine ORCIA (`ModelDiscoveryAuthFailedError`, `ModelDiscoveryEndpointNotFoundError`, `ModelDiscoveryNetworkError`).

### 2.3 Couche Backend API, Sécurité & Contrats (`apps/api/`, `packages/api-client/`)
- `apps/api/src/orcia_api/schemas/ai_models_hub.py` :
  - Définition de `AiModelDiscoverRequest`, `DiscoveredModelItem`, `AiModelDiscoveryResponse`.
- `apps/api/src/orcia_api/routers/ai_models_hub.py` :
  - Endpoints `POST /api/v1/settings/ai-models/discover` et `GET /api/v1/settings/ai-models/discover`.
  - Résolution de clé (soit `api_key` direct, soit résolution de clé chiffrée si `mapping_id` passé).
  - Contrôle `assert_ai_models_write_allowed` pour rejeter `READ_ONLY_OBSERVER`.
  - Utilisation du `request.app.state.http_client`.
- `packages/api-client/` :
  - Ajout de la méthode `discoverAiModels` dans `createAiModelsHubDomainClient`.
  - Régénération `scripts/export_openapi.py` (0-diff gate).

### 2.4 Interface Utilisateur & Expérience (`packages/ui/`, `apps/web/`)
- `packages/ui/src/primitives/OrciaModelCombobox.tsx` :
  - Composant Direction C accessible RGAA (`role="combobox"`, `role="listbox"`, `role="option"`, raccourcis clavier Flèche Haut/Bas, Entrée, Échap, clic externe).
  - Affichage des modèles découverts avec badges d'usage (`Chat`, `Embedding`), description optionnelle, indicateur de chargement (`spinner` / skeleton), bouton de rafraîchissement manuel.
  - Saisie libre native préservée : la valeur est modifiable caractère par caractère sans restriction.
- `apps/web/src/features/admin/ai-models/AiModelFormFields.tsx` & `AiModelConfigModal.tsx` :
  - Remplacement de l'input texte brut de `primaryModel` et `fallbackModel` par `OrciaModelCombobox`.
  - Déclenchement automatique de la découverte (debouncé à 500 ms) dès que l'URL ou la clé change, ou à l'ouverture en édition.
  - Affichage explicite de l'erreur en cas de défaillance (sans aucun `.catch(() => undefined)` silencieux).
  - Traduction complète dans `apps/web/src/i18n/locales/ai_models_hub_labels.ts` (fr & en).

### 2.5 Analyse d'Impact sur la Pyramide des Tests (`AD-17`)
- **Couche 1a (Unitaires Python)** :
  - Tests complets de `ai_models_discovery.py` avec `httpx.MockTransport` simulant :
    - Succès OpenAI `/v1/models` et Ollama `/api/tags`
    - Succès Anthropic `/v1/models`
    - Succès Gemini `/v1beta/models` avec pagination `pageToken` et classification `chat` vs `embedding`
    - Erreurs 401 / 403 (`ModelDiscoveryAuthFailedError`)
    - Erreur 404 (`ModelDiscoveryEndpointNotFoundError`)
    - Timeout / Erreur de connexion (`ModelDiscoveryNetworkError`)
    - Rejet SSRF (`UnsafeLlmEndpointUrlError`)
- **Couche 1b (Composants UI Vitest)** :
  - Tests unitaires de `OrciaModelCombobox` : saisie libre, sélection clavier, filtrage par usage, affichage chargement et message d'erreur.
  - Tests de régression de `AiModelConfigModal` : vérification du câblage vertical et absence de bouton muet.
- **Couche 2 (Intégration FastAPI)** :
  - Test de l'endpoint `POST /api/v1/settings/ai-models/discover` via `httpx.AsyncClient` testant la dérivation de clé depuis `mapping_id` existant et le rejet `READ_ONLY_OBSERVER`.
- **Couche 3 (Contrats OpenAPI)** :
  - Validation du zéro drift via `scripts/export_openapi.py --check`.

---

## 3. Bilan des Modifications & Résultats (Post-Implémentation)

### 3.1 Tableau des Fichiers Modifiés et Créés

| Fichier | Nature | Description |
|---|---|---|
| `packages/orcia-core/src/orcia_core/orchestration/ai_models_errors.py` | Modifié | Ajout des erreurs RFC 9457 `ModelDiscoveryAuthFailedError` (401), `ModelDiscoveryEndpointNotFoundError` (404), `ModelDiscoveryNetworkError` (502) et traductions fr/en associées |
| `packages/orcia-core/src/orcia_core/orchestration/ai_models_discovery.py` | Créé | Module hexagonal de découverte dynamique des modèles multi-fournisseurs (0 token consommé, pagination Gemini, filtrage `usage_hint`, repli Ollama `/api/tags`) |
| `packages/orcia-core/src/orcia_core/orchestration/__init__.py` | Modifié | Export public des types et de la fonction `discover_models_from_provider` |
| `apps/api/src/orcia_api/errors/registry.py` | Modifié | Enregistrement des 3 nouvelles exceptions de découverte dans `DOMAIN_ERROR_CLASSES` |
| `apps/api/src/orcia_api/schemas/ai_models_hub.py` | Modifié | Schémas de transport `DiscoveredModelItem`, `AiModelDiscoverRequest`, `AiModelDiscoveryResponse` |
| `apps/api/src/orcia_api/routers/_ai_models_helpers.py` | Modifié | Fonctions d'exécution `execute_models_discovery` et `resolve_mapping_decrypted_key` avec garde anti-fuite de secret |
| `apps/api/src/orcia_api/routers/ai_models_hub.py` | Modifié | Endpoints `POST /api/v1/settings/ai-models/discover` et `GET /api/v1/settings/ai-models/discover` avec gardes RBAC et rejet `READ_ONLY_OBSERVER` |
| `packages/api-client/openapi.json` | Modifié | Spécification OpenAPI 3.1 régénérée (0-diff gate) |
| `packages/api-client/src/generated/types.ts` | Modifié | Types TypeScript du SDK régénérés (`DiscoveredModelItem`, etc.) |
| `packages/api-client/src/domains/aiModelsHub.ts` | Modifié | Méthode cliente typée `discoverAiModels` |
| `packages/ui/src/primitives/OrciaModelCombobox.tsx` | Créé | Primitrive Combobox Direction C accessible RGAA (listbox, option, clavier, filtrage usage, saisie libre, rafraîchissement manuel, bannière d'erreur) |
| `packages/ui/src/index.ts` | Modifié | Export de `OrciaModelCombobox` et de ses props |
| `apps/web/src/i18n/locales/ai_models_hub_labels.ts` | Modifié | Clés i18n fr/en pour la découverte et la combobox |
| `apps/web/src/routes/settingsAiModelsPresets.ts` | Modifié | Fonction helper `discoverProviderModelsViaApi` |
| `apps/web/src/features/admin/ai-models/AiModelFormFields.tsx` | Modifié | Intégration de `OrciaModelCombobox` sur `primaryModel` et `fallbackModel` |
| `apps/web/src/features/admin/ai-models/AiModelConfigModal.tsx` | Modifié | Câblage de la découverte réactive (debounce 500ms, modal open, refresh button, affichage d'erreur sans blocage) |
| `tests/unit/test_story_19_2_ai_models_discovery.py` | Créé | 12 tests unitaires complets de découverte avec `httpx.MockTransport` (couverture 94%) |
| `tests/unit/test_story_19_2_ai_models_discover_endpoint.py` | Créé | 9 tests unitaires FastAPI de l'endpoint discover (RBAC, clé masquée, SSRF, protocoles) |
| `packages/ui/src/__tests__/model-combobox.test.tsx` | Créé | 5 tests Vitest de la combobox (@orcia/ui) |
| `apps/web/src/__tests__/story-19-2-ai-models-combobox-discovery-and-freeform.test.tsx` | Créé | 4 tests Vitest d'intégration web (saisie libre, découverte, filtrage usage, gestion d'erreurs) |
| `tests/unit/test_codebase_architectural_anti_patterns_audit.py` | Modifié | Ajustement du regex de détection de modèles en dur pour exclure le nom du runtime `ollama` (`(?<!o)llama`) |
| `docs/product/capabilities.yaml` | Modifié | Mise à jour de `CAP-081` et `CAP-190` avec les surfaces et tests de la Story 19.2 |
| `docs/implementation-artifacts/sprint-status.yaml` | Modifié | Statut de la Story 19.2 passé à `review` |

---

### 3.2 Résultats des Vérifications et Couverture de Tests

1. **Tests unitaires et intégration Python (`pytest`)** :
   - `tests/unit/test_story_19_2_ai_models_discovery.py` : 12 passed
   - `tests/unit/test_story_19_2_ai_models_discover_endpoint.py` : 9 passed
   - Total Story 19.2 : 21 tests passés avec succès
   - Couverture sur `packages/orcia-core/src/orcia_core/orchestration/ai_models_discovery.py` : **94%** (seuil exigé $\ge 90\%$)
   - `tests/unit/test_codebase_architectural_anti_patterns_audit.py` : 5 passed (0 violation de noms de modèles en dur)
2. **Typage strict et linters** :
   - `.venv/bin/mypy --strict packages/orcia-core apps/api apps/worker` : `Success: no issues found in 315 source files`
   - `.venv/bin/ruff check .` : `All checks passed!`
   - `.venv/bin/ruff format --check .` : `811 files already formatted`
   - `.venv/bin/lint-imports` : 5 contrats AD-19/AD-20 vérifiés, 0 brisé
3. **Contrat OpenAPI 3.1 (`0-diff gate`)** :
   - `.venv/bin/python scripts/export_openapi.py --check` : 0 diff, code de sortie 0
4. **Tests Frontend Vitest (`pnpm turbo run test`)** :
   - `@orcia/ui` : 24 test files, 102 passed (dont 5 tests `model-combobox.test.tsx` et 3 tests `ui-isolation.test.ts`)
   - `@orcia/api-client` : 2 test files, 14 passed
   - `@orcia/web` : 21 test files, 106 passed (dont 4 tests `story-19-2-ai-models-combobox-discovery-and-freeform.test.tsx` et 7 tests `zero-dead-buttons-and-silent-catches-audit.test.tsx`)
   - `pnpm turbo run lint typecheck` : 6 tâches réussies, 0 erreur TypeScript
5. **Registre des Capacités et Showcase** :
   - `pnpm site:sync` et `pnpm site:check` validés : 57/57 capacités live référencent au moins un test, 0 sans test, manifeste synchronisé.

---

### 3.3 Points d'Attention pour les Stories Suivantes

- **Story 19.3 (Test Réel de Connexion)** :
  - La découverte (19.2) liste les modèles sans émettre d'inférence (0 token consommé, 0 $). La Story 19.3 introduira le test actif d'appel de modèle (`max_tokens=1` pour le chat, embedding 1024 pour l'embedding) avec mesure de latence et mise à jour de `last_test_latency_ms`.
- **Story 19.6 (Migration Alembic & Suppression Hachage SHA-256 en Prod)** :
  - S'assurer que les modèles découverts et configurés par l'utilisateur sont persistés sans injection de valeurs par défaut codées en dur côté base de données.
