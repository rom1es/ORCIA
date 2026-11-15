# Rapport Tech Lead & Implémentation — Story 19.1 : Modale UI Connecter un Modèle IA — Champs Vides, Placeholders Dynamiques par Fournisseur & Suppression des Puces Codées en Dur (D1)

- **Date** : 2026-11-15
- **Story / Clé Sprint** : `19-1-modale-ui-champs-vides-placeholders-fournisseurs-et-suppression-puces-en-dur` (`Epic 19` — Décision D1)
- **Capacité(s)** : `CAP-190` (Hub Modèles IA Fiable, Découverte Dynamique 0 Token, Test Réel & Embeddings Sémantiques), impacte `CAP-052` / `CAP-053` — classification : `feature`
- **Auteur / Contexte** : Amelia (`bmad-dev-worker`) / Implémentation de la Story 19.1 de l'Epic 19 sur la branche `feat/epic-19-hub-modeles-ia-et-embeddings-semantiques`.
- **Commits associés** : à venir

---

## 1. Analyse du Besoin & Étude d'Impact Tech Lead (Pré-Implémentation)

### 1.1 Contexte & Problématique

Dans la modale « Connecter un nouveau modèle IA » (`AiModelConfigModal.tsx`, `AiModelFormFields.tsx`), ainsi que dans les formulaires et stores associés (`settingsAiModelsPresets.ts`, `platformSetupStore.tsx`, `SettingsAiModelsQuickForm.tsx`), plusieurs valeurs d'identifiants de modèles sont actuellement pré-remplies en dur :
- `primaryModel` est pré-rempli avec `claude-3-7-sonnet` ou `gemini-argon` (identifiant fictif), et `fallbackModel` avec `claude-3-5-haiku` ou `gemini-2.5-flash`.
- Le clic sur les tuiles de fournisseurs (`AI_PROVIDER_PRESETS`) force l'écrasement de `primaryModel` par des modèles codés en dur (`preset.samplePrimaryModel`), ignorant le modèle effectivement disponible sur l'infrastructure de l'entreprise.
- Des puces cliquables (`ai-model-quick-chip-*`) proposent des identifiants statiques (`gpt-4o`, `claude-3-7-sonnet`, `gemini-argon`, `llama3.3:70b`, etc.).
- Le repli d'hydratation dans `platformSetupStore.tsx:L364` injecte un fallback `claude-3-7-sonnet`.

**Comportement attendu (Décision D1 & Story 19.1)** :
1. **Champs Vides** : À l'ouverture de la modale en création et lors de la sélection d'un fournisseur, les champs `primaryModel` et `fallbackModel` doivent être strictement vides (`value === ""` sans valeur par défaut cachée ni pré-remplissage).
2. **Placeholders Dynamiques par Fournisseur** : Le champ `primaryModel` affiche un placeholder contextuel selon le fournisseur sélectionné :
   - Mistral : `ex. : mistral-large-latest` (FR) / `e.g. mistral-large-latest` (EN).
   - Ollama / vLLM : `ex. : llama3.2` (FR) / `e.g. llama3.2` (EN).
   - Google Gemini, OpenAI, Anthropic, Custom : `Identifiant exact publié par le fournisseur` (FR) / `Exact identifier published by provider` (EN).
   - Le champ `fallbackModel` reçoit un placeholder explicite : `Modèle de secours optionnel` (FR) / `Optional fallback model` (EN).
3. **Suppression Totale des Puces Codées en Dur** : Aucune puce de modèle (`ai-model-quick-chip-*`) ne doit être rendue dans le DOM.
4. **Conservation des Acquis** : Les URLs d'endpoints API par défaut, les sélecteurs de protocole (ex. Mode B Native vs Mode A OpenAI pour Gemini), les modes d'authentification et les libellés de tiers/efforts sont conservés.
5. **Internationalisation (i18n)** : Zéro chaîne utilisateur en dur dans le JSX. Tous les placeholders et textes sont extraits dans `AiModelsHubDictionary` (`apps/web/src/i18n/locales/{ai_models_hub_labels,fr,en}.ts`).

### 1.2 Exploration, Analyse d'Impact GitNexus, Factorisation & Dette Technique

- **Analyse d'Impact GitNexus (`direction: "upstream"`, `repo: "ORCIA"`)** :
  - `AI_PROVIDER_PRESETS` (`settingsAiModelsPresets.ts`) : consommé par `AiModelFormFields.tsx`, `SettingsAiModelsQuickForm.tsx`. Les propriétés `samplePrimaryModel`, `sampleSecondaryModel` et `recommendedModels` sont supprimées des spécifications de presets.
  - `AiModelConfigModal` (`AiModelConfigModal.tsx`) : 5 appelants (`SettingsAiModelsSection.tsx`, `settings.tsx`, `router.tsx`). Les états par défaut passent à `""`.
  - `AiModelFormFields` (`AiModelFormFields.tsx`) : suppression de `recommendedModels` et du bloc de puces rapides (`L218-244`). Intégration du placeholder dynamique.
  - `platformSetupStore.tsx` : suppression de `"claude-3-7-sonnet"` en fallback (ligne 364), remplacement par `""`.
- **Opportunités de Factorisation & Contrôle de Volumétrie** :
  - `AiModelFormFields.tsx` passe de 317 lignes à moins de 260 lignes suite à la suppression des puces et du code de suggestion statique.
  - Fonction utilitaire typée `resolvePrimaryModelPlaceholder(family: string, isFr: boolean, labels: AiModelsHubDictionary): string` centralisée dans `settingsAiModelsPresets.ts`.
  - Nettoyage des puces masquées de `SettingsAiModelsQuickForm.tsx` pour éliminer tout résidu de `gemini-argon` ou autre nom obsolète.

---

## 2. Plan d'Implémentation

### 2.1 Schéma de Données & Migrations Alembic
- Aucun impact base de données / Alembic pour la Story 19.1 (périmètre purement frontend UI).

### 2.2 Noyau Métier Hexagonal & Workers
- Aucun impact backend / worker pour la Story 19.1 (réservé aux Stories 19.2 à 19.7).

### 2.3 Couche Backend API, Sécurité & Contrats
- Aucun changement de contrat OpenAPI 3.1 (`0-diff` préservé).

### 2.4 Interface Utilisateur & Expérience (`apps/web/`, `packages/ui/`)
1. **Dictionnaire i18n (`apps/web/src/i18n/locales/ai_models_hub_labels.ts`)** :
   - Ajout des clés `primaryModelPlaceholderGeneric`, `primaryModelPlaceholderMistral`, `primaryModelPlaceholderOllama`, `fallbackModelPlaceholder` dans `AiModelsHubDictionary` (FR et EN).
2. **Spécification des Presets (`apps/web/src/routes/settingsAiModelsPresets.ts`)** :
   - Nettoyage de `ProviderPresetSpec` : suppression de `samplePrimaryModel`, `sampleSecondaryModel`, `recommendedModels`.
   - Purge de `AI_PROVIDER_PRESETS` : aucun nom de modèle en dur.
   - Ajout de `resolvePrimaryModelPlaceholder(modelFamily: string, labels: AiModelsHubDictionary): string`.
   - Retrait de `resolveRecommendedModelsForProvider`.
3. **Modale et Champs de Formulaire (`apps/web/src/features/admin/ai-models/`)** :
   - `AiModelConfigModal.tsx` : `primaryModel` et `fallbackModel` initialisés à `""` en création.
   - `AiModelFormFields.tsx` : retrait des puces `ai-model-quick-chip-*`, ajout des placeholders dynamiques, suppression de l'écrasement des modèles lors du clic sur un préréglage de fournisseur.
4. **Hydratation du Store (`apps/web/src/components/platformSetupStore.tsx`)** :
   - Ligne 364 : remplacement de `"claude-3-7-sonnet"` par `""`.
5. **Formulaire de Compatibilité (`apps/web/src/routes/SettingsAiModelsQuickForm.tsx` & `SettingsAiModelsSection.tsx`)** :
   - Suppression des puces cachées et du préremplissage de modèle sur clic preset.

### 2.5 Analyse d'Impact sur la Pyramide des Tests (`AD-17`)
- **Couche 1b (Vitest Frontend)** :
  - `apps/web/src/__tests__/story-17-5-ai-models-hub-modal-lifecycle-and-f5.test.tsx` : adapter le test de modale pour vérifier la vacuité initiale, la présence du placeholder dynamique et l'absence de puces rapides.
  - `apps/web/src/__tests__/gemini-argon-settings-and-assistant.test.tsx` $\rightarrow$ renommer / adapter vers `gemini-settings-and-assistant.test.tsx` pour tester la saisie explicite de modèle et le sélecteur de protocole Mode A / Mode B sans s'appuyer sur des puces ou pré-remplissage.
  - **Nouveau test garde-fou (`apps/web/src/__tests__/story-19-1-ai-models-empty-fields-and-placeholders-guard.test.tsx`)** :
    - Vérifie que pour TOUS les préréglages fournisseurs de la modale, `primaryModel` et `fallbackModel` restent strictement vides.
    - Vérifie l'absence absolue de tout élément `[data-testid^="ai-model-quick-chip-"]` dans le DOM.
    - Vérifie la concordance exacte des placeholders (Mistral $\rightarrow$ `mistral-large-latest`, Ollama $\rightarrow$ `llama3.2`, Gemini/OpenAI/Anthropic $\rightarrow$ générique).
    - Échoue immédiatement si une régression réintroduit une valeur par défaut ou une puce.
- **Couche 3** : Contrôle `pnpm typecheck` et `pnpm turbo run lint`.

---

## 3. Bilan des Modifications & Résultats (Post-Implémentation)

### 3.1 Fichiers Développés & Modifiés
| Fichier | Nature | Description synthétique |
| :--- | :--- | :--- |
| `apps/web/src/i18n/locales/ai_models_hub_labels.ts` | Modification | Ajout des clés `primaryModelPlaceholderGeneric`, `primaryModelPlaceholderMistral`, `primaryModelPlaceholderOllama`, `fallbackModelPlaceholder` en FR et EN. |
| `apps/web/src/routes/settingsAiModelsPresets.ts` | Modification / Refactoring | Purge de `samplePrimaryModel`, `sampleSecondaryModel`, `recommendedModels` de `ProviderPresetSpec` et `AI_PROVIDER_PRESETS`. Ajout de `resolvePrimaryModelPlaceholder`. Retrait de `resolveRecommendedModelsForProvider`. |
| `apps/web/src/features/admin/ai-models/AiModelConfigModal.tsx` | Modification | Initialisation de `primaryModel` et `fallbackModel` à `""` en création. Retrait du prop `recommendedModels`. |
| `apps/web/src/features/admin/ai-models/AiModelFormFields.tsx` | Modification / Refactoring | Suppression des puces rapides (`ai-model-quick-chip-*`), placeholders dynamiques selon le fournisseur, suppression de l'écrasement des modèles sur clic preset. 288 lignes (< 300 lignes). |
| `apps/web/src/routes/SettingsAiModelsQuickForm.tsx` | Modification | Suppression des puces masquées et du préremplissage des modèles lors du clic preset. Placeholders dynamiques. |
| `apps/web/src/routes/SettingsAiModelsSection.tsx` | Modification | Nettoyage des appels à `resolveRecommendedModelsForProvider`. |
| `apps/web/src/components/platformSetupStore.tsx` | Modification | Suppression du fallback en dur `"claude-3-7-sonnet"` remplacé par `""`. |
| `apps/web/src/__tests__/gemini-settings-and-assistant.test.tsx` | Renommage / Refactoring | Ancien `gemini-argon-settings-and-assistant.test.tsx` adapté pour tester la vacuité initiale, les placeholders et la saisie explicite de modèle. |
| `apps/web/src/__tests__/story-17-5-ai-models-hub-modal-lifecycle-and-f5.test.tsx` | Modification | Adaptation du test de modale (vacuité initiale, absence de puces, saisie manuelle). |
| `apps/web/src/__tests__/story-19-1-ai-models-empty-fields-and-placeholders-guard.test.tsx` | Création | Suite de garde-fous stricte validant l'absence de préremplissage et de puces sur tous les presets (FR et EN). |
| `docs/product/capabilities.yaml` | Modification | Mise à jour de `CAP-052` (ajout du test garde-fou, référence 19-1). |
| `docs/implementation-artifacts/sprint-status.yaml` | Modification | Passage de `19-1-...` au statut `review`. |

### 3.2 Résultats Chiffrés, Métriques & Qualité
- **Tests unitaires et de composants Vitest (`apps/web`)** :
  - `src/__tests__/story-19-1-ai-models-empty-fields-and-placeholders-guard.test.tsx` : **3/3 passed** (100 %).
  - `src/__tests__/gemini-settings-and-assistant.test.tsx` : **2/2 passed** (100 %).
  - `src/__tests__/story-17-5-ai-models-hub-modal-lifecycle-and-f5.test.tsx` : **5/5 passed** (100 %).
  - `src/__tests__/zero-dead-buttons-and-silent-catches-audit.test.tsx` : **7/7 passed** (100 %).
- **Qualité statique & Architecture** :
  - `pnpm turbo run lint typecheck` : **6/6 passed**, `0 error`.
  - `.venv/bin/ruff check .` : `All checks passed!`.
  - `.venv/bin/ruff format --check .` : `795 files already formatted`.
  - `.venv/bin/mypy --strict packages/orcia-core apps/api apps/worker` : `Success: no issues found in 312 source files`.
  - `.venv/bin/lint-imports` : `5 contracts kept, 0 broken`.
  - `.venv/bin/pytest tests/unit/test_codebase_architectural_anti_patterns_audit.py` : **4 passed**, `0 warning`.
  - `pnpm site:check` : `Manifest in sync (57/57 capacités live référencent au moins un test)`.

### 3.3 Validation & Procédure de Test sur Toute la Pyramide (`AD-17`)
- **Couche 1b — Frontend TS (`Vitest`)** :
  - Validation exhaustive de l'état initial des champs textuels (`primaryModel === ""`, `fallbackModel === ""`).
  - Validation du comportement lors de la sélection des tuiles de fournisseurs : conservation de la vacuité des champs, adaptation instantanée du placeholder (`ex. : mistral-large-latest` pour Mistral, `ex. : llama3.2` pour Ollama/vLLM, `Identifiant exact publié par le fournisseur` pour OpenAI/Anthropic/Google).
  - Validation de l'absence complète de tout élément de puce de modèle (`ai-model-quick-chip-*`).
- **Couche 3 — Contrats API & Typage Strict** :
  - Aucune modification de contrat API backend (réservé aux Stories 19.2 à 19.7).
  - Typage TypeScript strict à zéro erreur (`tsc --noEmit`).
- **Couche 5 — Survie au F5 & Non-Régression Visuelle** :
  - Tests de cycle de vie et réhydratation validés (`story-17-5-ai-models-hub-modal-lifecycle-and-f5.test.tsx`).
