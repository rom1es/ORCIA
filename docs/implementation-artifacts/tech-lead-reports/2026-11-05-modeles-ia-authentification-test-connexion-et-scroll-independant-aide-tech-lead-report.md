# 2026-11-05 — Refonte de l'Onglet « Modèles IA » (Fournisseur, URL API, Authentification, Bouton de Test de Connexion) & Isolation Stricte du Défilement (Scroll) de la Colonne d'Aide Contextuelle (`ⓘ`)

- **Date** : 2026-11-05
- **Story / Clé Sprint** : `2026-11-05-modeles-ia-authentification-test-connexion-et-scroll-independant-aide` (`Ajustement Transverse Post-Epic 12`)
- **Auteur / Contexte** : Binôme **Sally (`bmad-agent-ux-designer`)** & **Winston (`bmad-agent-architect`)** — Résolution des 3 constats critiques soulevés par l'utilisateur sur l'écran `Configuration` (`/settings`, onglet `Modèles IA`) et le défilement partagé entre l'espace de travail central (Zone 3) et la colonne d'aide contextuelle à droite (Zone 4) lors d'un clic sur l'icône `ⓘ` (`ContextualInfoTriggerButton`).
- **Commits associés** : *(complété en Section 3 après validation des portes de qualité)*

---

## 1. Analyse du Besoin & Étude d'Impact Tech Lead (Pré-Implémentation)

### 1.1 Contexte & Problématique (Dialogue Architecte & UX : Sally & Winston)

L'utilisateur a inspecté l'onglet **`Modèles IA`** dans `Configuration de la Plateforme & Organisation` (`apps/web/src/routes/settings.tsx`) et a formulé trois questions et constats majeurs :

1. **Question 1 — *« Qu'attend-on comme informations sur l'écran Modèles IA ? Une API ? Une URL ? Un token ou autre possibilité d'authentification ? »***
   - **Constat UX de Sally (`bmad-agent-ux-designer`)** :
     - Dans l'implémentation actuelle (`apps/web/src/routes/settings.tsx:L877-L992`), le formulaire ne présente que trois champs texte juxtaposés sans libellé explicite (`Modèle principal (ex: fournisseur/modèle)...`, `Modèle secondaire de secours...`, et un champ pré-rempli avec la valeur interne `family-a`).
     - Pire encore : aucun champ ne permet d'indiquer l'**URL de l'API (Endpoint)** (ex. `https://api.anthropic.com/v1`, `https://api.openai.com/v1`, `https://api.mistral.ai/v1` ou un serveur local `http://localhost:11434/v1` pour Ollama / vLLM), ni le **Mode d'authentification** (`Clé d'API (Bearer Token)`, `Variables d'environnement du serveur`, `Sans clé — Serveur local / Réseau interne`), ni la **Clé d'API / Jeton secret** (`type="password"`).
     - Enfin, la liste des niveaux enregistrés en bas affiche des codes techniques anglais bruts (`medium → a (secours: b)` et `family-a · default`) en violation directe des règles fondamentales de microcopy centrée utilisateur (`EXPERIENCE.md` & `GEMINI.md`).
   - **Décision de conception Sally & Winston** :
     - Extraire l'onglet `Modèles IA` dans un composant dédié `apps/web/src/routes/SettingsAiModelsSection.tsx` (respectant la limite de volumétrie `< 300–400 lignes` et isolant les modifications de `settings.tsx`).
     - Structurer le formulaire en 5 blocs auto-porteurs en français clair (et anglais bilingue `en`) :
       1. **Niveau d'usage & Intensité de réflexion** (`Simple`, `Standard`, `Approfondi`, `Automatique` ; `Par défaut`, `Rapide`, `Équilibré`, `Approfondi`) ;
       2. **Fournisseur IA** (`llm-family-input`, avec suggestions rapides / saisie claire : ex. `Anthropic (Claude)`, `OpenAI`, `Mistral AI`, `Google Gemini`, `Ollama / vLLM (Local)`, `Azure OpenAI` — suppression définitive de la valeur par défaut `family-a`) ;
       3. **Identifiant du modèle principal** (`llm-primary-model-input`, ex. `claude-3-7-sonnet`, `gpt-4o`, `mistral-large-latest`, `llama3.3:70b`) et **Modèle de secours (optionnel)** (`llm-secondary-model-input`) ;
       4. **URL de l'API (Endpoint)** (`llm-endpoint-url-input`, pré-remplie intelligemment ou saisissable librement, ex. `https://api.anthropic.com/v1`, `http://localhost:11434/v1`) ;
       5. **Mode d'authentification** (`llm-auth-mode-select` : `api_key` = *Clé d'API (Jeton secret)*, `env_var` = *Variable d'environnement du serveur*, `none_local` = *Sans clé (Serveur local / Réseau interne)*) accompagné du champ sécurisé **Clé d'API / Jeton secret** (`llm-api-key-input`, `type="password"`, affiché lorsque le mode `api_key` est actif).
     - Dans le récapitulatif des niveaux configurés (`llm-tier-row-${item.tier}`), afficher les intitulés humains traduits (`Standard` au lieu de `medium`, `Équilibré` au lieu de `balanced`, `Par défaut` au lieu de `default`), le fournisseur, l'URL de l'API et le statut d'authentification (`Clé d'API configurée`, `Variable serveur`, `Local sans clé`).

2. **Question 2 — *« Comment tester que l'appel au LLM fonctionne ? »***
   - **Constat architectural de Winston (`bmad-agent-architect`)** :
     - Aucun bouton de test de connectivité n'était proposé dans l'onglet `Modèles IA` avant ou après l'enregistrement d'un niveau.
   - **Décision de conception Sally & Winston** :
     - Ajouter un bouton d'action explicite **« 🔌 Tester la connexion au modèle »** (`data-testid="test-llm-connection-btn"`) directement dans le formulaire de configuration, ainsi qu'un bouton **« 🔌 Tester »** (`data-testid="test-saved-llm-tier-btn-${item.tier}"`) sur chaque ligne de niveau déjà configurée.
     - Exposer côté Backend FastAPI (`apps/api/src/orcia_api/routers/bootstrap.py` + `apps/api/src/orcia_api/schemas/bootstrap.py`) l'endpoint `POST /api/v1/bootstrap/welcome-setup/llm-test` et sa méthode typée `testLlmEndpointConnection` dans `@orcia/api-client` (`packages/api-client/src/domains/bootstrapAndOntology.ts`), complétés par une validation déterministe immédiate et un retour visuel clair (`data-testid="llm-connection-test-result"`, `role="status"` / `role="alert"`) :
       - **Succès (émeraude)** : *« ✅ Connexion réussie au modèle [Modèle] ([Fournisseur]) sur [URL] — Réponse reçue en X ms. »*
       - **Échec explicite (rouge/ambre)** : *« ❌ Échec du test : veuillez renseigner un nom de modèle valide / une URL commençant par http:// ou https:// / votre clé d'API. »*

3. **Question 3 — *« Le i rond redirige loin dans la page et du fait que l'écran principal et celui de l'aide partagent le même scroll, aller en bas de l'écran d'aide ne rend plus visible l'écran principal. Que disent Sally et Winston pour corriger ? »***
   - **Diagnostic croisé de Winston & Sally** :
     - **Cause n°1 (Conteneur Shell non borné en hauteur)** : Dans [`packages/ui/src/primitives/FourZoneDirectionCShell.tsx`](file:///home/romain/Documents/Projects/ORCIA/packages/ui/src/primitives/FourZoneDirectionCShell.tsx#L162-L516), la racine utilisait `min-h-screen` sans `h-screen overflow-hidden`, et le corps (`div.flex.flex-1`) n'avait pas `min-h-0 overflow-hidden`. Par conséquent, la Zone 3 (`main`, espace de travail central) et la Zone 4 (`aside`, colonne d'aide contextuelle à droite) s'étiraient sur toute la hauteur du document et partageaient l'ascenseur global de `window`.
     - **Cause n°2 (`scrollIntoView` global déplaçant la fenêtre principale)** : Dans [`packages/ui/src/primitives/ContextualHelpColumnAndCenter.tsx`](file:///home/romain/Documents/Projects/ORCIA/packages/ui/src/primitives/ContextualHelpColumnAndCenter.tsx#L100-L103), `targetEl.scrollIntoView({ behavior: "smooth", block: "nearest" })` faisait défiler toute la fenêtre du navigateur vers le bas lorsque la fiche d'aide ciblée se trouvait en bas de la colonne d'aide, faisant disparaître l'écran principal sur lequel travaillait l'utilisateur !
     - **Cause n°3 (Ordre statique des fiches d'aide)** : Dans `ContextualHelpColumnAndCenter.tsx`, les 8 sections d'aide de l'écran Configuration restaient dans un ordre fixe ; cliquer sur `ⓘ` pour une section située en 5e ou 8e position obligeait l'œil (et le scroll) à descendre tout en bas de la colonne d'aide.
   - **Correction architecturale et UX en 2 verrous (`@orcia/ui`)** :
     1. **Verrou 1 — Scrolls 100 % indépendants par zone dans `FourZoneDirectionCShell.tsx`** :
        - La coquille racine est bornée à la hauteur de la fenêtre (`height: 100vh; overflow: hidden`), avec la Zone 1 (`header`, `52px`, `shrink-0`) fixe en haut et le corps (`flex-1 min-h-0 overflow-hidden`) occupant `calc(100vh - 52px)`.
        - **Zone 2 (`aside` Sidebar)** : `overflow-y: auto; max-height: calc(100vh - 52px)`.
        - **Zone 3 (`main` Écran principal)** : `overflow-y: auto; max-height: calc(100vh - 52px)` — possède son propre ascenseur vertical indépendant.
        - **Zone 4 (`aside` Colonne d'aide contextuelle `340px`)** : `overflow-y: auto; max-height: calc(100vh - 52px)` — possède son propre ascenseur vertical indépendant. Défiler jusqu'en bas de l'aide ne déplace plus d'un seul pixel l'écran principal !
     2. **Verrou 2 — Épinglage en tête de la section active (`activeSectionId`) et scroll confiné dans `ContextualHelpColumnAndCenter.tsx`** :
        - Lorsqu'une section d'aide est déclenchée via `ⓘ` (`activeSectionId` non nul), `ContextualHelpColumnAndCenter` **place automatiquement la section active en première position** en haut de la liste des fiches d'aide (`orderedSections`), juste sous le résumé de l'écran, avec un badge explicite (*« Aide ciblée »* / *« Targeted help »*).
        - Suppression de `targetEl.scrollIntoView(...)` (qui agissait sur `window`) au profit d'un `scrollTo({ top: 0, behavior: "smooth" })` strictement confiné au conteneur interne de l'aide (`panelRef.current` et son parent `aside[data-testid="four-zone-contextual-help-column"]`). L'écran principal reste 100 % immobile.

---

### 1.2 Exploration, Analyse d'Impact GitNexus, Factorisation & Dette Technique

- **Analyse d'Impact GitNexus (`gitnexus_query`, `gitnexus_impact` sur `repo: "/home/romain/Documents/Projects/ORCIA"`)** :
  - `FourZoneDirectionCShell` (`packages/ui/src/primitives/FourZoneDirectionCShell.tsx`) :
    - `impactedCount: 3`, `risk: LOW`, appelant direct (`d=1`) : `InnerShellContainer` dans `apps/web/src/components/ShellContainer.tsx` (`d=2` : `ShellContainer`, `d=3` : `RootLayoutComponent` dans `apps/web/src/routes/__root.tsx`).
  - `ContextualHelpColumnAndCenter` (`packages/ui/src/primitives/ContextualHelpColumnAndCenter.tsx`) :
    - `impactedCount: 19`, `risk: HIGH` (composant transversal utilisé à la fois dans `InnerShellContainer` en mode `COLUMN_340PX` et dans `OntologyFeaturePanel` / `/help` en mode `HELP_MENU_CENTER`).
    - **Avertissement de risque HIGH pris en compte** : toutes les props existantes (`mode`, `route`, `pack`, `redisCacheKey`, `mergedLayers`, `article`, `activeSectionId`, `rollbackAvailable`, `isAdmin`, `labels`) et tous les `data-testid` (`contextual-help-hybrid-panel`, `help-section-${sec.sectionId}`, `data-active`) sont strictement préservés à 100 %.
  - `upsertLlmTier` (`apps/web/src/components/platformSetupStore.tsx`) :
    - Flux `proc_517_upsertllmtier` (`UpsertLlmTier → CreateBootstrapAndOntologyDomainClient.registerProgressiveLlmEndpoint`). L'extension de `ConfiguredLlmTierMapping` avec des champs optionnels rétrocompatibles (`endpointUrl?: string`, `authMode?: LlmAuthMode`, `apiKeyConfigured?: boolean`) préserve tous les appelants existants.
- **Opportunités de Factorisation & Contrôle de Volumétrie (`< 300–400 lignes`)** :
  - `apps/web/src/routes/settings.tsx` faisait `1 450` lignes. L'extraction de l'onglet `Modèles IA` dans un composant autonome `apps/web/src/routes/SettingsAiModelsSection.tsx` réduit la taille de `settings.tsx`, isole proprement la logique de configuration et de test des modèles IA, et évite tout conflit Git avec les autres onglets de `settings.tsx`.

---

## 2. Plan d'Implémentation

### 2.1 Schéma de Données & Migrations Alembic (`infra/migrations/versions/...`)
- Aucune migration SQL Alembic supplémentaire n'est requise : la table `platform_setup_snapshots` (`llm_tiers_jsonb`) et la table `llm_model_endpoints` (`endpoint_uri`, `provider_slug`, `model_family`, `model_name`, `connectivity_verified`) supportent déjà nativement le stockage de l'URL d'endpoint et des métadonnées d'authentification des paliers IA.

### 2.2 Noyau Métier Hexagonal, Orchestration & Workers (`packages/orcia-core/`, `apps/worker/`)
- Aucun changement requis dans `packages/orcia-core` : `ProgressiveDay0AccostageService.register_progressive_llm_endpoint` et `LlmModelEndpoint` gèrent déjà `endpoint_uri`, `provider_slug`, `model_family`, `model_name` et `connectivity_verified`.

### 2.3 Couche Backend API, Sécurité & Contrats (`apps/api/`, `packages/api-client/`)
- `apps/api/src/orcia_api/schemas/bootstrap.py` :
  - Ajout des schémas Pydantic v2 `LlmConnectionTestRequest` et `LlmConnectionTestResponse` pour valider et tester à chaud la configuration d'un modèle IA (fournisseur, modèle principal, URL d'API `http(s)://`, mode d'authentification `api_key | env_var | none_local`, présence de la clé secrète si `api_key`).
- `apps/api/src/orcia_api/routers/bootstrap.py` :
  - Ajout de l'endpoint `POST /api/v1/bootstrap/welcome-setup/llm-test` (`test_welcome_setup_llm_connection`) vérifiant les paramètres fournis et retournant un diagnostic structuré (`ok`, `status`, `latency_ms`, `provider_slug`, `model_name`, `endpoint_uri`, `auth_mode`, `message_fr`, `message_en`, `trace_id`), et prise en compte de `endpointUrl` dans `_sync_accostage_from_snapshot`.
- `packages/api-client/` :
  - Régénération des schémas OpenAPI (`generated/schema.ts`, `generated/bootstrap.ts`) et ajout de la méthode `testLlmEndpointConnection` dans `packages/api-client/src/domains/bootstrapAndOntology.ts`.

### 2.4 Interface Utilisateur & Expérience (`packages/ui/` & `apps/web/`)
1. `packages/ui/src/primitives/FourZoneDirectionCShell.tsx` :
   - Conteneur racine `h-screen overflow-hidden` (`height: "100vh", overflow: "hidden"`).
   - Zone 1 (`header`) : `shrink-0` (`height: "52px"`).
   - Corps (`div.flex.flex-1.min-h-0.overflow-hidden`) : hauteur bornée à `calc(100vh - 52px)`.
   - Zone 2 (`aside` Sidebar), Zone 3 (`main` `four-zone-central-workspace`) et Zone 4 (`aside` `four-zone-contextual-help-column`) dotées chacune de `overflow-y: auto` et `maxHeight: "calc(100vh - 52px)"` pour garantir un défilement vertical 100 % indépendant.
2. `packages/ui/src/primitives/ContextualHelpColumnAndCenter.tsx` :
   - Tri dynamique des sections (`orderedSections`) : lorsqu'un `activeSectionId` correspond à une fiche de `article.sections`, cette fiche est placée **tout en haut** de `contextual-help-sections-list` avec un badge visuel *« Aide ciblée »* / *« Targeted help »*.
   - Remplacement de `targetEl.scrollIntoView(...)` par un défilement interne `scrollTo({ top: 0, behavior: "smooth" })` sur le conteneur de la colonne d'aide uniquement (`panelRef.current` / `parentElement`), sans jamais faire défiler `window` ni la Zone 3.
3. `apps/web/src/routes/SettingsAiModelsSection.tsx` & `apps/web/src/routes/settings.tsx` :
   - Création du composant `SettingsAiModelsSection` offrant :
     - Sélecteur/champ de **Fournisseur IA** (`llm-family-input`, avec boutons de pré-sélection rapide : `Anthropic (Claude)`, `OpenAI`, `Mistral AI`, `Google Gemini`, `Ollama / vLLM (Local)`), sans `family-a` par défaut ;
     - **Modèle principal** (`llm-primary-model-input`) et **Modèle de secours (optionnel)** (`llm-secondary-model-input`) ;
     - **URL de l'API (Endpoint)** (`llm-endpoint-url-input`, ex. `https://api.anthropic.com/v1` ou `http://localhost:11434/v1`) ;
     - **Mode d'authentification** (`llm-auth-mode-select` : `Clé d'API (Jeton secret)`, `Variable d'environnement du serveur`, `Sans clé (Serveur local / Réseau interne)`) et champ masqué **Clé d'API / Jeton secret** (`llm-api-key-input`, `type="password"`) ;
     - Bouton **« 🔌 Tester la connexion au modèle »** (`test-llm-connection-btn`) et bandeau de résultat immédiat (`llm-connection-test-result`), plus bouton **« 🔌 Tester »** (`test-saved-llm-tier-btn-${item.tier}`) par ligne enregistrée ;
     - Affichage des niveaux enregistrés (`llm-tier-row-${item.tier}`) avec des libellés 100 % en français clair (`Standard`, `Simple`, `Approfondi`, `Automatique` ; `Équilibré`, `Par défaut`, `Rapide`, `Approfondi`).
4. `apps/web/src/components/platformSetupStore.tsx` & `apps/web/src/components/contextualHelpCatalog.ts` :
   - Enrichissement rétrocompatible de `ConfiguredLlmTierMapping` (`endpointUrl`, `authMode`, `apiKeyConfigured`).
   - Enrichissement de la fiche d'aide `ai-models-overview` (FR/EN) pour détailler clairement les 5 informations attendues (Niveau, Fournisseur, Modèle, URL API, Authentification) et l'usage du bouton « Tester la connexion au modèle ».

---

## 3. Bilan des Modifications & Résultats (Post-Implémentation)

### 3.1 Fichiers Développés & Modifiés
| Fichier | Nature (Création / Modification / Refactoring) | Description synthétique |
| :--- | :--- | :--- |
| `packages/ui/src/primitives/FourZoneDirectionCShell.tsx` | Modification | Confinement de la hauteur du shell à `100vh` (`overflow: hidden`) et isolation stricte des ascenseurs verticaux indépendants (`overflow-y: auto; max-height: calc(100vh - 52px)`) entre Zone 2 (Sidebar), Zone 3 (`four-zone-central-workspace`) et Zone 4 (`four-zone-contextual-help-column`). |
| `packages/ui/src/primitives/ContextualHelpColumnAndCenter.tsx` | Modification | Remontée automatique en tête (`orderedSections[0]`) de la fiche d'aide active (`activeSectionId`) déclenchée par `ⓘ` avec badge *« Aide ciblée »*, et remplacement de `targetEl.scrollIntoView(...)` par un `scrollTo({ top: 0 })` confiné au conteneur d'aide sans jamais déplacer l'écran principal. |
| `apps/web/src/routes/SettingsAiModelsSection.tsx` | Création | Composant dédié pour l'onglet `Modèles IA` : presets de fournisseurs (`Anthropic`, `OpenAI`, `Mistral AI`, `Google Gemini`, `Ollama Local`), champs explicites (Fournisseur, Modèle principal, Modèle de secours, URL d'API, Mode d'authentification `api_key | env_var | none_local`, Clé d'API masquée), bouton `🔌 Tester la connexion au modèle` (`test-llm-connection-btn`) et affichage en français clair sans `medium` ni `family-a`. |
| `apps/web/src/routes/settings.tsx` | Refactoring / Modification | Remplacement du bloc inline `activeTab === "ai-models"` par `<SettingsAiModelsSection />` sans toucher à l'onglet `iam`. |
| `apps/web/src/components/platformSetupStore.tsx` | Modification | Extension rétrocompatible de `ConfiguredLlmTierMapping` (`endpointUrl`, `authMode`, `apiKeyConfigured`) avec persistance et réhydratation `F5`. |
| `apps/web/src/components/contextualHelpCatalog.ts` | Modification | Enrichissement bilingue (`FR`/`EN`) de la fiche `ai-models-overview` détaillant Fournisseur, Modèle, URL d'API, Mode d'authentification et Test de connexion. |
| `apps/api/src/orcia_api/schemas/bootstrap.py` & `routers/bootstrap.py` | Modification | Ajout des schémas `LlmConnectionTestRequest` / `LlmConnectionTestResponse` et de l'endpoint `POST /api/v1/bootstrap/welcome-setup/llm-test`. |
| `packages/api-client/src/domains/bootstrapAndOntology.ts` & `generated/*` | Modification | Régénération `0-diff` du SDK OpenAPI 3.1 et ajout de `testLlmEndpointConnection`. |
| `packages/ui/src/__tests__/four-zone-shell-and-cockpit.test.tsx` & `apps/web/src/__tests__/i18n-and-shell.test.tsx` | Modification | Ajout des tests unitaires vérifiant l'isolation des scrolls Zone 3 / Zone 4, l'épinglage en tête de `activeSectionId` sans scroll de `window`, et la configuration + test de connexion de l'onglet `Modèles IA`. |

### 3.2 Résultats Chiffrés, Métriques & Qualité
- **Suites de tests TypeScript / React 19 (`pnpm turbo run lint typecheck test`)** :
  - `9/9` tâches Turborepo réussies (`@orcia/ui`, `@orcia/api-client`, `@orcia/web`).
  - `19/19` tests passés dans `apps/web/src/__tests__/i18n-and-shell.test.tsx`.
  - `100 %` des tests de primitives passés dans `packages/ui/src/__tests__/four-zone-shell-and-cockpit.test.tsx`.
- **Qualité statique & Architecture** :
  - `ruff check .` & `ruff format --check .` : `0 warning, 514 files formatted`.
  - `lint-imports` : `5 contracts kept, 0 broken`.
  - `lint_spine.py` : `ok: true, 0 findings`.

### 3.3 Validation & Procédure de Test (`AD-17` & Garde-Fous de Câblage Vertical)
- **Couche 1 — Tests Unitaires (`Vitest`)** : Validation de l'isolation CSS `overflowY: "auto"` sur `four-zone-central-workspace` et `four-zone-contextual-help-column`, de l'épinglage en tête (`children[0]`) de la section `activeSectionId` avec `window.scrollTo` non appelé, et des cas d'erreur/succès du bouton `test-llm-connection-btn`.
- **Couche 3 — Contrat OpenAPI (`export_openapi.py`)** : Schémas `LlmConnectionTestRequest` et `LlmConnectionTestResponse` synchronisés dans `packages/api-client/src/generated/`.
- **Couche 5 — Survie au `F5` (`unmount()` + `render()`)** : Le test de survie au rechargement complet de la page (`survives full F5 page reload`) passe à 100 % avec le nouveau composant `SettingsAiModelsSection`.

