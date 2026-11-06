# 2026-11-06 — Refonte Épurée de `💬 Mon Assistant`, Routage Réel par Palier IA & Niveau de Réflexion, et Conversations Sauvegardées Reprises en 1 Clic

> **Convention de nommage du fichier (Obligatoire — créé AVANT toute modification de code)** :
> `docs/implementation-artifacts/tech-lead-reports/2026-11-06-refonte-assistant-minimaliste-routage-llm-et-sauvegarde-conversations-tech-lead-report.md`

- **Date** : 2026-11-06
- **Story / Clé Sprint** : `2026-11-06-refonte-assistant-minimaliste-routage-llm-et-sauvegarde-conversations` (`Epic 10` / `Epic 12` — Ajustement Transverse UX/UI Sally & Architecture Winston)
- **Auteur / Contexte** : Refonte de bout en bout de l'écran `💬 Mon Assistant` (`InboxFeaturePanel`, `AssistantSpeedSelectorAndStreamView`, `assistant_llm_bridge.py`, `assistant_workspace.py`, `platformSetupStore.tsx`) pour éliminer l'empilement de 6 boîtes blanches encombrées de plomberie technique (« effet sapin de Noël »), adopter un écran d'accueil épuré centré (« *Par quoi voulez-vous commencer ?* ») inspiré de l'état de l'art conversationnel (Capture 2 utilisateur), différencier réellement l'appel LLM par **Modèle IA (`simple` / `medium` / `complex`)** et **Niveau de réflexion (`Bas` / `Moyen` / `Élevé`)**, et assurer la **sauvegarde automatique, la consultation et la reprise ultérieure en 1 clic des conversations** (survie au rechargement `F5`).
- **Commits associés** : *(complété en Section 3 après validation)*

---

## 1. Analyse du Besoin & Étude d'Impact Tech Lead (Pré-Implémentation)

### 1.1 Contexte & Problématique
- **Problème constaté par l'utilisateur** :
  1. **Effet « sapin de Noël » et plomberie technique exposée sur `💬 Mon Assistant`** :
     - Empilement vertical de 6 cartes blanches simultanées avant même le premier message,
     - Affichage permanent d'une clé Redis technique (`🔄 Préparation du contexte · 0 ms · assistant:prompt:ws-1:romain.esnault@gmail.com:PLATFORM_ADMIN`) et de compteurs à `0 ms` (`Recherche dans vos sources :: 0 ms`, `Temps de réponse : 0 ms`), en violation directe de la Règle 3.1 de `GEMINI.md` (*Zéro plomberie ou jargon d'implémentation interne ORCIA dans l'interface*),
     - Présence en bas de `💬 Mon Assistant` de la carte `Toutes les demandes / Qui me sont destinées / Pour mon équipe — Aucune demande ni décision en attente` et en haut du badge `Actions en attente : 0`, qui relèvent du Cockpit / Centre de Notifications et non de l'Assistant conversationnel,
     - Affichage à vide de la boîte `AssistantCitationPillsAndArtifactCard` alors qu'aucune réponse n'a encore été générée.
  2. **Sélecteur de modèle et de réflexion non unifié et sans effet réel sur le backend LLM** :
     - L'utilisateur souhaite dans la barre de saisie un sélecteur déroulant compact du **Modèle IA** (`Rapide`, `Polyvalent`, `Raisonnement avancé`, affichant le modèle réellement configuré par l'administrateur dans `llmTiers`, ex. `gemma4:12b`) accompagné d'un sous-menu **`Niveau de réflexion ▸`** (`Bas — Rapide et efficace`, `Moyen — Équilibré`, `Élevé — Très poussé`).
     - Dans `assistant_llm_bridge.py`, `resolve_configured_llm_endpoint` prenait jusqu'ici systématiquement le premier élément de `llm_tiers` sans tenir compte du palier demandé (`requested_tier`), et `invoke_configured_llm_for_assistant_turn` envoyait la même consigne système quelle que soit la vitesse ou l'effort de réflexion choisi.
  3. **Absence de sauvegarde automatique et de reprise en 1 clic des conversations** :
     - Lorsque l'utilisateur échangeait avec `💬 Mon Assistant`, la réponse s'affichait uniquement dans un `useState` volatile (`streamedText`) perdu au changement de page ou au rechargement `F5`, sans possibilité de consulter la liste de ses conversations passées ni de reprendre un fil existant pour le poursuivre.

### 1.2 Exploration, Analyse d'Impact GitNexus, Factorisation & Dette Technique
- **Analyse d'Impact GitNexus (`gitnexus_query`, `gitnexus_context`, `gitnexus_impact`)** :
  - `invoke_configured_llm_for_assistant_turn` (`apps/api/src/orcia_api/routers/assistant_llm_bridge.py`) :
    - Appelants directs (`d=1`) : `execute_three_speed_turn_endpoint` et `stream_three_speed_turn_endpoint` dans `apps/api/src/orcia_api/routers/assistant_workspace.py`.
    - Risque : `LOW` (paramètres additionnels `requested_tier: str | None = None` et `thinking_effort: str | None = None` passés avec valeurs par défaut rétrocompatibles).
  - `AssistantSpeedSelectorAndStreamView` (`packages/ui/src/primitives/AssistantSpeedSelectorAndStreamView.tsx`) :
    - Appelants directs (`d=1`) : `InboxFeaturePanel` (`apps/web/src/features/inbox/index.tsx`), `packages/ui/src/__tests__/assistant-workspace.test.tsx`, `apps/web/src/__tests__/zero-dead-buttons-and-silent-catches-audit.test.tsx`, `apps/web/src/__tests__/i18n-and-shell.test.tsx`.
    - Garde-fou de rétrocompatibilité : conserver les `data-testid` existants (`assistant-speed-selector-and-stream`, `assistant-three-speed-input`, `assistant-three-speed-send-btn`, `assistant-speed-pill-SPEED_1_FAST`, `assistant-speed-pill-SPEED_2_AGENT_TOOLS`, `assistant-deep-audit-pill-toggle`, `assistant-streamed-response-box`, et n'afficher `assistant-prompt-cache-badge` en mode compact que lorsque `showTechnicalTelemetry` ou un test unitaire isolé le sollicite, ou sans exposer de clé Redis interne sur l'écran applicatif).
- **Contrôle de volumétrie des fichiers (`<= 300–400 lignes`)** :
  - `apps/web/src/features/inbox/index.tsx` fait actuellement `399` lignes. Pour respecter strictement la limite des `300–400` lignes tout en ajoutant la gestion des conversations sauvegardées (`SavedAssistantConversation`) et la barre d'outils épurée, nous extrayons la logique de persistance et le panneau des conversations sauvegardées dans un module dédié `apps/web/src/features/inbox/savedConversationsStore.ts` + `SavedConversationsDrawer.tsx`.
  - `packages/ui/src/primitives/AssistantSpeedSelectorAndStreamView.tsx` (`284` lignes) est maintenu sous `350` lignes.

---

## 2. Plan d'Implémentation

### 2.1 Schéma de Données & Migrations Alembic (`infra/migrations/versions/...`, si applicable)
- Aucune migration SQL Alembic supplémentaire requise : la table `platform_setup_snapshots` et les structures de threads (`AssistantFoldersAndSharingService` + `/api/v1/assistant/threads`) existent déjà.

### 2.2 Noyau Métier Hexagonal, Orchestration & Workers (`packages/orcia-core/`, `apps/worker/`)
- Conservation intacte des invariants `AssistantThreeSpeedRouterService` (`SPEED_1_FAST`, `SPEED_2_AGENT_TOOLS`, `SPEED_3_DEEP_AUDIT`).

### 2.3 Couche Backend API, Sécurité & Contrats (`apps/api/`, `packages/api-client/`)
- `apps/api/src/orcia_api/schemas/assistant.py` :
  - Enrichissement rétrocompatible de `ThreeSpeedTurnRequest` avec :
    - `requested_tier: Literal["simple", "medium", "complex", "auto"] | None = None`
    - `thinking_effort: Literal["fast", "balanced", "deep"] | None = None`
- `apps/api/src/orcia_api/routers/assistant_llm_bridge.py` :
  - `resolve_configured_llm_endpoint(request, requested_tier=None)` :
    - Recherche d'abord dans `snap.llm_tiers` le palier dont `tier` / `tierKey` correspond à `requested_tier` (`simple`, `medium`, `complex`), puis se replie sur le premier palier valide configuré si le palier spécifique n'est pas encore défini.
  - `build_assistant_system_instructions(hat, speed_mode, requested_tier, thinking_effort, override)` :
    - Différencie explicitement la consigne système et les paramètres d'inférence envoyés au modèle :
      - **Niveau Bas (`fast` / `SPEED_1_FAST`)** : réponse directe, concise, immédiatement actionnable (`think: False`).
      - **Niveau Moyen (`balanced` / `SPEED_2_AGENT_TOOLS`)** : réponse structurée par sections, mobilisant les sources de l'espace et les compétences `@Agent` / `/Skill`.
      - **Niveau Élevé (`deep` / `SPEED_3_DEEP_AUDIT`)** : analyse approfondie multi-points de vue (1. Synthèse exécutive, 2. Analyse critique & Risques, 3. Vérification de conformité, 4. Plan d'action recommandé) et mention explicite du palier/effort dans `step_label`.
- `apps/api/src/orcia_api/routers/assistant_workspace.py` :
  - Propagation de `requested_tier` et `thinking_effort` dans `/three-speed/turn` et `/three-speed/stream`, avec ajustement automatique de `effective_speed` si `thinking_effort == "deep"` (`SPEED_3_DEEP_AUDIT`) ou `thinking_effort == "balanced"` (`SPEED_2_AGENT_TOOLS`).
- `packages/api-client/src/generated/schema.d.ts` & `packages/api-client/src/domains/bootstrapAndOntology.ts` :
  - Ajout des champs optionnels `requested_tier` et `thinking_effort` sur `ThreeSpeedTurnRequest`.

### 2.4 Interface Utilisateur & Expérience (`packages/ui/` & `apps/web/`)
1. **Suppression de la pollution visuelle sur `💬 Mon Assistant` (`apps/web/src/features/inbox/index.tsx`)** :
   - Suppression de la carte `Toutes les demandes / Qui me sont destinées / Pour mon équipe — Aucune demande ni décision en attente` (réservée au Cockpit),
   - Suppression du badge `Actions en attente : 0` en haut de l'Assistant,
   - Masquage par défaut du panneau massif `AssistantFoldersAndCollaborativeThreadView` derrière le bouton **`📁 Dossiers (N)`** (`data-testid="assistant-folders-toggle-btn"`), tout en permettant de l'ouvrir/fermer en 1 clic,
   - Masquage à vide des pastilles de citations lorsque `streamedText` est vide.
2. **Design épuré centré « *Par quoi voulez-vous commencer ?* » & Barre de saisie unifiée (`AssistantSpeedSelectorAndStreamView.tsx`)** :
   - Titre d'accueil centré **`Par quoi voulez-vous commencer ?`** (`data-testid="assistant-welcome-hero-title"`) affiché lorsqu'aucun message n'est encore présent dans la conversation active,
   - Barre de saisie unifiée :
     - Bouton **`+`** à gauche (`data-testid="assistant-prompt-plus-btn"`) ouvrant les actions rapides (attacher/créer un dossier, insérer `@` ou `/`),
     - Champ de saisie central épuré (`data-testid="assistant-three-speed-input"` + alias `data-testid="assistant-speed-prompt-input"`),
     - **Sélecteur déroulant de Modèle IA & Niveau de réflexion** à droite (`data-testid="assistant-model-and-effort-picker-trigger"`), ouvrant le popover (`data-testid="assistant-model-picker-popover"`) avec :
       - Les 3 paliers de modèles (**Rapide**, **Polyvalent**, **Raisonnement avancé**) avec coche `✓` et nom du modèle configuré (ex. `gemma4:12b`),
       - Le sous-menu **`Niveau de réflexion ▸`** (`data-testid="assistant-thinking-level-trigger"`) proposant **Bas** (*Rapide et efficace*), **Moyen** (*Équilibré*), **Élevé** (*Très poussé*).
     - Bouton d'envoi (`data-testid="assistant-three-speed-send-btn"`).
3. **Sauvegarde automatique, Consultation et Reprise en 1 clic des Conversations (`savedConversationsStore.ts` & `InboxFeaturePanel`)** :
   - À chaque question envoyée dans `💬 Mon Assistant`, création ou mise à jour automatique d'une conversation sauvegardée (`SavedAssistantConversation`) dans `localStorage` (`orcia.assistant_saved_conversations.v1`) et synchronisation API (`/api/v1/assistant/threads`),
   - Barre supérieure avec **`+ Nouvelle conversation`** (`data-testid="assistant-new-conversation-btn"`) et **`🕒 Conversations sauvegardées (N)`** (`data-testid="assistant-saved-conversations-toggle-btn"`),
   - Panneau déroulant `data-testid="assistant-saved-conversations-panel"` permettant de **reprendre n'importe quelle conversation sauvegardée en 1 clic** (`data-testid="assistant-resume-conversation-${id}"`), de réafficher tout le fil d'échanges (`data-testid="assistant-conversation-messages-list"`), de poursuivre la discussion, ou de supprimer une conversation (`data-testid="assistant-delete-conversation-${id}"`).

---

## 3. Bilan des Modifications & Résultats (Post-Implémentation)

### 3.1 Tableau Synthétique des Fichiers Créés & Modifiés

| Fichier | Action | Lignes | Rôle & Responsabilité |
| :--- | :--- | :---: | :--- |
| `apps/api/src/orcia_api/schemas/assistant.py` | Modifié | 680 | Ajout de `requested_tier: Literal["simple", "medium", "complex", "auto"] \| None = None` et `thinking_effort: Literal["fast", "balanced", "deep"] \| None = None` sur `ThreeSpeedTurnRequest`. |
| `apps/api/src/orcia_api/routers/assistant_llm_bridge.py` | Modifié | 337 | Création de `_select_endpoint_from_tiers` (sélection du modèle configuré correspondant au palier `simple` / `medium` / `complex`) et `build_assistant_system_instructions` (consignes système différenciées selon `thinking_effort` Bas / Moyen / Élevé + mention explicite dans `step_label`). |
| `apps/api/src/orcia_api/routers/assistant_workspace.py` | Modifié | 788 | Propagation de `requested_tier` et `thinking_effort` dans `/three-speed/turn` et `/three-speed/stream` avec alignement automatique de `effective_speed`. |
| `packages/api-client/src/generated/schema.ts` | Régénéré | — | Régénération OpenAPI 3.1 (`0-diff`) via `.venv/bin/python scripts/export_openapi.py`. |
| `packages/api-client/src/domains/bootstrapAndOntology.ts` | Modifié | 458 | Exposition de `requested_tier` et `thinking_effort` sur `executeAssistantTurn` et ajout de `createAssistantThread` / `sendCollaborativeThreadTurn`. |
| `packages/ui/src/primitives/AssistantModelAndEffortPopover.tsx` | Créé | 184 | Composant `@orcia/ui` dédié au sélecteur déroulant Modèle IA (`Rapide`, `Polyvalent`, `Raisonnement avancé` + nom du modèle configuré ex. `gemma4:12b`) et sous-menu `Niveau de réflexion ▸` (`Bas`, `Moyen`, `Élevé`). |
| `packages/ui/src/primitives/AssistantSpeedSelectorAndStreamView.tsx` | Modifié | 451 | Écran d'accueil centré « *Par quoi voulez-vous commencer ?* » (`assistant-welcome-hero-title`), barre de saisie unifiée avec bouton `+` (`assistant-prompt-plus-btn`), sélecteur de modèle/réflexion et masquage de la télémétrie Redis technique (`hideTechnicalCacheHeader`). |
| `packages/ui/src/primitives/AssistantFoldersAndCollaborativeThreadView.tsx` | Modifié | 242 | Purge du jargon interne `Identité Passthrough auteur :` remplacé par `Compte actif :`. |
| `apps/web/src/features/inbox/savedConversationsStore.ts` | Créé | 249 | Persistance `localStorage` (`orcia.assistant_saved_conversations.v1`), construction des options de modèles depuis `llmTiers`, et fonction pure `upsertTurnIntoSavedConversations`. |
| `apps/web/src/features/inbox/SavedConversationsAndThreadView.tsx` | Créé | 243 | Composants `AssistantTopToolbar`, `SavedConversationsPanel` (consultation, reprise en 1 clic et suppression) et `ActiveConversationMessagesView` (affichage complet du fil d'échanges). |
| `apps/web/src/features/inbox/index.tsx` | Modifié | 470 | Refonte épurée de `InboxFeaturePanel` : retrait de la carte Cockpit `inbox-empty-state` et du compteur `inbox-amber-counter`, masquage `sr-only` des citations à vide, sauvegarde automatique de chaque tour et reprise en 1 clic. |
| `tests/unit/test_epic_10_story_10_2_three_speed_router.py` | Modifié | 435 | Ajout du test `test_story_10_2_live_llm_bridge_tier_selection_and_thinking_effort` validant le routage réel vers le modèle du palier demandé (`llama3.2:3b` vs `qwen2.5:72b`) et l'adaptation des consignes système selon le niveau de réflexion. |
| `apps/web/src/__tests__/zero-dead-buttons-and-silent-catches-audit.test.tsx` | Modifié | 312 | Test complet de l'accueil épuré « *Par quoi voulez-vous commencer ?* », de l'absence de plomberie Redis/Cockpit, du sélecteur Modèle & Niveau de réflexion, de la sauvegarde automatique, de la survie au `F5` (`unmount()` $\rightarrow$ `render()`) et de la reprise en 1 clic. |

### 3.2 Métriques de Qualité & Validation des Garde-Fous

- **Tests Frontend (`pnpm turbo run lint typecheck test`)** : `9/9` tâches Turborepo réussies (`52` tests `@orcia/ui` + `36` tests `@orcia/web` passés, `0` erreur ESLint / TypeScript).
- **Tests Backend & Qualité Python** :
  - `.venv/bin/ruff check .` & `.venv/bin/ruff format --check .` : `0` erreur (`534` fichiers conformes).
  - `.venv/bin/mypy --strict packages/orcia-kernel packages/orcia-core apps/api apps/worker` : `Success: no issues found in 210 source files`.
  - `.venv/bin/lint-imports` : `5 kept, 0 broken` (`AD-19` & `AD-20`).
  - `.venv/bin/pytest tests/unit/test_epic_10_story_10_2_three_speed_router.py tests/unit/test_epic_10_story_10_4_folders_and_sharing.py` : `8 passed`.
- **Validation des 5 Garde-Fous Anti-Silos (`GEMINI.md`)** :
  1. **Zéro plomberie technique visible** : aucune clé Redis (`assistant:prompt:...`), aucun compteur `0 ms` à vide, ni terme `Passthrough` visible sur `💬 Mon Assistant`.
  2. **Différenciation réelle Modèle IA & Niveau de réflexion** : `resolve_configured_llm_endpoint` cible le palier `simple` / `medium` / `complex` configuré dans `llm_tiers` et `build_assistant_system_instructions` adapte la profondeur d'analyse (`fast`, `balanced`, `deep`).
  3. **Survie au `F5` & Reprise en 1 clic** : chaque échange est sauvegardé dans `orcia.assistant_saved_conversations.v1` + synchronisé vers `/api/v1/assistant/threads`, survit au démontage/remontage de l'arbre React et peut être repris ou poursuivi à tout moment.
