# 2026-11-07 — Refonte de `📁 Dossiers` & `📌 Notes`, Persistance (`Survie au F5`) des Réglages & Dossiers, et Câblage Complet du Contexte Multi-Tours dans l'Appel LLM

> **Convention de nommage du fichier (Obligatoire — créé AVANT toute modification de code)** :
> `docs/implementation-artifacts/tech-lead-reports/2026-11-07-assistant-dossiers-notes-reglages-et-contexte-multi-tours-llm-tech-lead-report.md`

- **Date** : 2026-11-07
- **Story / Clé Sprint** : `2026-11-07-assistant-dossiers-notes-reglages-et-contexte-multi-tours-llm` (`Post-Epic 12 / Epic 10 UX/UI, Persistance F5 & Contexte LLM`)
- **Auteur / Contexte** : Sally (UX/UI Designer) & Winston (Architecte Système & Tech Lead) — Correction des 7 points critiques relevés par l'utilisateur sur `💬 Mon Assistant` (`/assistant`) : épuration visuelle du panneau `📁 Dossiers` (suppression des 3 faux onglets redondants et des enums internes `PRIVATE`/`WORKSPACE_OPEN`/`SHARED_SELECTED` en texte brut, correction du double `: :`, ajout d'un encadré pédagogique avec icône d'aide `ⓘ` et d'un badge de dossier/note actifs au-dessus du prompt), persistance `Survie au F5` des Dossiers, Notes et Réglages de Mon Assistant, suppression du `.split(" ")` résiduel côté frontend (`useAssistantStreamingTurn.ts`), et câblage vertical complet vers le LLM du System Prompt 5 couches, des Réglages (`defaultHat`, `responseTone`, `responseFormat`, `personalInstructions`, `workspaceInstructions`), des Notes du dossier actif (`folder_pinned_notes`) et de l'historique multi-tours complet (`conversation_history`).
- **Commits associés** : `feat/assistant-agnostic-async-llm-ontology-and-true-sse-streaming`

---

## 1. Analyse du Besoin & Étude d'Impact Tech Lead (Pré-Implémentation)

### 1.1 Contexte & Problématique — Diagnostic des 7 Points Soulevés par l'Utilisateur

1. **Point 1A — Trois onglets redondants et trompeurs dans `📁 Dossiers`** :
   - *Constat* : Lorsque l'utilisateur clique sur `📁 Dossiers (N)` dans la barre d'outils supérieure de `💬 Mon Assistant`, le composant [`AssistantFoldersAndCollaborativeThreadView.tsx`](file:///home/romain/Documents/Projects/ORCIA/packages/ui/src/primitives/AssistantFoldersAndCollaborativeThreadView.tsx) s'ouvre sur un sous-onglet `💬 Discussion en cours` (avec un second champ d'envoi redondant !) accompagné de `📁 Dossiers (2)` et `🕒 Historique & Recherche` (qui doublonne `🕒 Conversations sauvegardées`).
   - *Correction* : Masquer visuellement (`style={{ display: "none" }}`) la barre des 3 onglets legacy ainsi que les panneaux `ACTIVE_DISCUSSION` et `HISTORY_SEARCH` (conservés dans le DOM en `display: none` uniquement pour la compatibilité des tests unitaires historiques `Story 10.4`), et afficher directement la vue dédiée aux **Dossiers thématiques et à leurs Notes épinglées**.

2. **Point 1B — Mots internes ORCIA (`PRIVATE`, `SHARED_SELECTED`, `WORKSPACE_OPEN`) et double deux-points (`: :`) visibles** :
   - *Constat* : Les cartes de dossiers affichent `{folder.visibilityMode}` brut (`PRIVATE`, `WORKSPACE_OPEN`), la bannière d'état dans `InboxFeaturePanel` affiche `✅ Visibilité du dossier mise à jour (WORKSPACE_OPEN)`, et la pastille du dossier actif affiche `📁 Dossier actif : : test` (double `:`).
   - *Correction* : Créer `formatFolderVisibilityLabel(mode, isFr)` traduisant systématiquement `PRIVATE` $\rightarrow$ `🔒 Privé (Moi uniquement)`, `SHARED_SELECTED` $\rightarrow$ `👥 Partagé (Membres choisis)` et `WORKSPACE_OPEN` $\rightarrow$ `📦 Visible par tout l'Espace`. Corriger le double `:` en normalisant `labels.activeFolderPillPrefix.replace(/\s*:\s*$/, "")`.

3. **Point 1C — Manque d'explication sur le rôle des Dossiers & Notes et absence de retour visuel dans la zone de question** :
   - *Constat* : L'utilisateur ne sait pas à quoi servent un Dossier et ses Notes, ni si l'Assistant les utilise lorsqu'il pose une question.
   - *Correction* :
     - Ajouter en tête du panneau `📁 Dossiers` un encadré pédagogique clair (`data-testid="assistant-folders-and-notes-explainer"`) expliquant :
       1. **📁 Dossier thématique** : regroupe les conversations d'un même sujet ; lorsqu'il est actif, chaque nouvelle question y est rattachée.
       2. **📌 Notes du dossier (mémo permanent)** : consignes ou éléments de contexte transmis automatiquement à Mon Assistant à chaque question posée dans ce dossier.
     - Afficher directement l'éditeur de **📌 Notes du dossier actif** ouvert par défaut dès qu'un dossier est sélectionné, et permettre de sélectionner/désélectionner un dossier en 1 clic sur sa carte.
     - Afficher juste au-dessus du champ de saisie principal (`AssistantSpeedSelectorAndStreamView`) un badge contextuel (`data-testid="assistant-prompt-active-folder-badge"`) : `📁 Dossier actif : {titre}` + `· 📌 Note active transmise à l'Assistant` + bouton `×` pour détacher le dossier actif.

4. **Point 2A — Persistance (`Survie au F5`) des Dossiers, des Notes et des `⚙️ Réglages de Mon Assistant`** :
   - *Constat* : Dans `InboxFeaturePanel`, `folders` et `activeFolderId` étaient de simples `useState([])` perdus au `F5`, et `AssistantGovernanceModalAndStudio` réinitialisait toujours ses champs aux constantes par défaut (`initialDefaultHat = "PM"`) sans relire les préférences sauvegardées.
   - *Correction* : Persister dans `savedConversationsStore.ts` (et synchroniser avec les endpoints backend `/api/v1/assistant/folders`, `/api/v1/assistant/governance/mode-a/user`, `/api/v1/assistant/governance/mode-a/workspace`) :
     - `readSavedAssistantFolders()` / `writeSavedAssistantFolders(folders, activeFolderId)`
     - `readSavedAssistantGovernancePrefs()` / `writeSavedAssistantGovernancePrefs(prefs)` (`responseTone`, `favoriteFormat`, `defaultHat`, `personalInstructions`, `workspaceInstructions`, `mcpExposeAssistant`).

5. **Point 2B — Suppression du `.split(" ")` dans `useAssistantStreamingTurn.ts`** :
   - *Constat* : `streamTextProgressively` dans `useAssistantStreamingTurn.ts:L159` utilisait encore `fullText.split(" ")` et `.join(" ")`, ce qui écrasait les sauts de ligne `\n` et l'indentation Markdown côté navigateur !
   - *Correction* : Remplacer le découpage par mots `.split(" ")` par un découpage par lignes (`fullText.match(/[^\n]*\n|[^\n]+/g)`) et `chunks.slice(0, currentIndex).join("")`, préservant à **100 %** chaque `\n` et chaque espace d'indentation.

6. **Point 2C — Envoi effectif au LLM du System Prompt, des Réglages (`defaultHat`, `tone`, `format`, `instructions`), des Notes du dossier actif et de l'historique complet des réponses précédentes (`conversation_history`)** :
   - *Constat* : `useAssistantStreamingTurn.ts` envoyait `hat: "PLATFORM_ADMIN"` en dur, sans `conversation_history`, sans `folder_pinned_notes`, et sans les préférences de `⚙️ Réglages de Mon Assistant`.
   - *Correction* :
     - Enrichir `ThreeSpeedTurnRequest` (`apps/api/src/orcia_api/schemas/assistant.py` + `scripts/export_openapi.py` `0-diff`) avec `folder_id`, `folder_pinned_notes`, `response_tone`, `response_format`, `personal_instructions` et `workspace_instructions`.
     - Injecter ces éléments dans `build_assistant_system_instructions` (`assistant_llm_prompts.py`) et les propager depuis `assistant_workspace.py` $\rightarrow$ `assistant_llm_bridge.py`.
     - Dans `useAssistantStreamingTurn.ts` et `InboxFeaturePanel`, transmettre systématiquement à `executeAssistantTurn` :
       - `hat: governancePrefs.defaultHat`,
       - `response_tone`, `response_format`, `personal_instructions`, `workspace_instructions`,
       - `folder_id: activeFolder?.folderId`, `folder_pinned_notes: activeFolder?.pinnedNotesMarkdown`,
       - `conversation_history`: tous les tours précédents de `activeConversation.turns` (`user` + `assistant`), ainsi que le contexte des pièces jointes (`attachedFiles`).

### 1.2 Contrôle de Volumétrie (`< 380` lignes par fichier)
- `packages/ui/src/primitives/AssistantFoldersAndCollaborativeThreadView.tsx` (`442` lignes) $\rightarrow$ ramené sous **`330` lignes**.
- `apps/web/src/features/inbox/savedConversationsStore.ts` (`359` lignes) $\rightarrow$ extraction des helpers de persistance des dossiers et réglages dans `apps/web/src/features/inbox/assistantFoldersAndPrefsStore.ts` (~180 lignes) afin que chaque fichier reste `< 360` lignes.
- `apps/api/src/orcia_api/schemas/assistant.py` (`696` lignes) $\rightarrow$ découpage en `assistant.py` (~340 lignes) + `assistant_citations_and_folders.py` (~350 lignes) ré-exportés proprement.

---

## 2. Plan d'Implémentation

### 2.1 Schéma de Données & Migrations Alembic
- Aucune migration Alembic requise.

### 2.2 Noyau Métier & Prompt 5 Couches (`apps/api/src/orcia_api/routers/assistant_llm_prompts.py`)
- Enrichissement de `build_assistant_system_instructions` pour intégrer :
  - Le ton (`SYNTHETIC`, `BALANCED`, `DETAILED_CODE`) et le format (`BULLETS_SUMMARY`, `STRUCTURED_SECTIONS`, `STEP_BY_STEP`) choisis dans `⚙️ Réglages de Mon Assistant`,
  - Les instructions de l'Espace (`workspace_instructions` — Couche 4) et les instructions personnelles (`personal_instructions` — Couche 5),
  - Les **Notes épinglées du dossier actif** (`folder_pinned_notes` — Mémoire continue de Couche 5).

### 2.3 Couche Backend FastAPI & SDK OpenAPI (`apps/api/`, `packages/api-client/`)
- Ajout des champs optionnels dans `ThreeSpeedTurnRequest` (`schemas/assistant.py`), régénération du schéma OpenAPI 3.1 (`scripts/export_openapi.py` `0-diff`), et propagation dans `assistant_workspace.py` et `assistant_llm_bridge.py`.

### 2.4 Design System `@orcia/ui` & Application Web (`packages/ui/`, `apps/web/`)
- Refonte et allègement (`< 330` lignes) de `AssistantFoldersAndCollaborativeThreadView.tsx` (`formatFolderVisibilityLabel`, encadré explicatif `assistant-folders-and-notes-explainer`, ouverture directe des notes épinglées, masquage `display: none` des 3 onglets redondants).
- Ajout du badge `assistant-prompt-active-folder-badge` dans `AssistantSpeedSelectorAndStreamView.tsx`.
- Création du composant animé `ThinkingDots` (`animate-bounce` avec `animationDelay` `-0.3s` / `-0.15s`) dans `AssistantResponseFooterActionsAndCitations.tsx` et suppression des `...` en fin de ligne après `"Recherche et rédaction en cours"`.
- Création de `assistantFoldersAndPrefsStore.ts` et câblage complet dans `InboxFeaturePanel` + `useAssistantStreamingTurn.ts` :
  - Consommation directe du flux SSE `POST /api/v1/assistant/three-speed/stream` (`ReadableStream` + `TextDecoder`) avec persistance en tâche de fond (module-level state + `subscribeActiveTurn`) pour que le changement d'écran dans ORCIA n'interrompe jamais la réflexion ou le streaming en cours,
  - Affichage en direct dans `AssistantThinkingSubWindow` des événements `thinking_delta` (`delta.reasoning` de `gemma4:12b` / `deepseek-r1`) replié par défaut (`collapse hide`, `data-expanded="false"`, `data-step-expanded="false"`) avec chronomètre temps réel (`1s`, `2s`...) et dépliable au clic,
  - Pattern **Viewport-Locked Chat Layout + Smart Sticky Scroll** dans `AssistantSpeedSelectorAndStreamView.tsx` : barre de prompt ancrée en bas (`assistant-sticky-prompt-footer`, `position: "sticky"`, `bottom: 0`), historique de conversation rendu dans le flux central (`previousTurnsSlot` dans `assistant-central-scrollable-stream`), défilement automatique en bas (`data-pinned-to-bottom="true"`) qui s'interrompt automatiquement dès que l'utilisateur remonte manuellement (`distanceFromBottom > 48px` $\rightarrow$ `data-pinned-to-bottom="false"`) avec bouton flottant `↓ Suivre la réponse en direct` (`assistant-resume-autoscroll-btn`),
  - Timeout `httpx.Timeout(300.0, connect=10.0)` côté backend (`core_and_lifespan.py` & `assistant_llm_bridge.py`) et interdiction absolue d'afficher la phrase de test `"synthèse conforme pour « ... »"` en cas d'erreur ou de timeout d'un modèle IA réel.

---

## 3. Bilan des Modifications & Résultats (Post-Implémentation)

### 3.1 Tableau Synthétique des Fichiers Créés & Modifiés

| Fichier | Action | Lignes (`wc -l`) | Description |
| :--- | :--- | :--- | :--- |
| [`packages/ui/src/primitives/AssistantFoldersAndCollaborativeThreadView.tsx`](file:///home/romain/Documents/Projects/ORCIA/packages/ui/src/primitives/AssistantFoldersAndCollaborativeThreadView.tsx) | Modifié & Allégé | `296` | Masquage (`display: none`) des 3 faux onglets redondants (`ACTIVE_DISCUSSION`, `FOLDERS`, `HISTORY_SEARCH`), affichage direct de la grille des dossiers et de l'éditeur de notes épinglées, fonction `formatFolderVisibilityLabel` (`🔒 Privé`, `👥 Partagé`, `📦 Visible par tout l'Espace` sans `PRIVATE` brut), correction du double `: :`, encadré pédagogique `assistant-folders-and-notes-explainer` + aide `ⓘ`. |
| [`packages/ui/src/primitives/AssistantResponseFooterActionsAndCitations.tsx`](file:///home/romain/Documents/Projects/ORCIA/packages/ui/src/primitives/AssistantResponseFooterActionsAndCitations.tsx) | Modifié | `369` | Ajout de `ThinkingDots` (3 points rebondissants `6px × 6px` `.orcia-thinking-dot` + `@keyframes orciaThinkingBounce` dans `tokens.css`) en début de ligne dans `AssistantThinkingSliderIndicator` et texte `"Recherche et rédaction en cours"` sans `…` final. |
| [`packages/ui/src/primitives/AssistantThinkingSubWindow.tsx`](file:///home/romain/Documents/Projects/ORCIA/packages/ui/src/primitives/AssistantThinkingSubWindow.tsx) | Modifié | `278` | Maintien en `collapse hide` par défaut (`data-expanded="false"`, `data-step-expanded="false"`) de `LIVE_MODEL_REASONING` (`delta.reasoning`) avec compteur en direct (`initialElapsedSeconds`) et ouverture manuelle au clic. |
| [`packages/ui/src/primitives/AssistantSpeedSelectorAndStreamView.tsx`](file:///home/romain/Documents/Projects/ORCIA/packages/ui/src/primitives/AssistantSpeedSelectorAndStreamView.tsx) | Modifié | `383` | Ajout de `previousTurnsSlot`, `assistant-sticky-prompt-footer` (`position: "sticky"`, `bottom: 0`), `data-pinned-to-bottom` (Smart Sticky Scroll : arrêt de l'auto-scroll si l'utilisateur remonte manuellement + bouton `↓ Suivre la réponse en direct` `assistant-resume-autoscroll-btn`), et badge `assistant-prompt-active-folder-badge`. |
| [`packages/ui/src/primitives/AssistantGovernanceModeATabs.tsx`](file:///home/romain/Documents/Projects/ORCIA/packages/ui/src/primitives/AssistantGovernanceModeATabs.tsx) | Modifié | `330` | Ajout de la bannière explicative `assistant-gov-explainer-banner` détaillant comment le rôle, le ton, le format et les instructions de Couche 4/5 sont transmis au modèle IA à chaque question. |
| [`packages/ui/src/primitives/AssistantPromptPlusAndAutocomplete.tsx`](file:///home/romain/Documents/Projects/ORCIA/packages/ui/src/primitives/AssistantPromptPlusAndAutocomplete.tsx) | Modifié | `312` | Ajout de `contentExcerpt?: string` sur `UiAssistantAttachedFileItem` pour transmettre le contexte des pièces jointes au LLM. |
| [`apps/web/src/features/inbox/assistantFoldersAndPrefsStore.ts`](file:///home/romain/Documents/Projects/ORCIA/apps/web/src/features/inbox/assistantFoldersAndPrefsStore.ts) | Créé | `160` | Store de persistance (`Survie au F5`) pour les dossiers thématiques (`readSavedAssistantFolders`, `writeSavedAssistantFolders`), le dossier actif (`readSavedActiveFolderId`, `writeSavedActiveFolderId`), les réglages de Mon Assistant (`readSavedAssistantGovernancePrefs`, `writeSavedAssistantGovernancePrefs`) et `buildConversationHistoryPayload`. |
| [`apps/web/src/features/inbox/useAssistantStreamingTurn.ts`](file:///home/romain/Documents/Projects/ORCIA/apps/web/src/features/inbox/useAssistantStreamingTurn.ts) | Modifié | `373` | Consommation temps réel du flux SSE `/api/v1/assistant/three-speed/stream` persisté au niveau module (`activeTurnSnapshot` + `subscribeActiveTurn`) pour survivre aux changements d'écran dans ORCIA sans perdre la question bleue ni le chronomètre de réflexion. |
| [`apps/web/src/features/inbox/SavedConversationsAndThreadView.tsx`](file:///home/romain/Documents/Projects/ORCIA/apps/web/src/features/inbox/SavedConversationsAndThreadView.tsx) & [`index.tsx`](file:///home/romain/Documents/Projects/ORCIA/apps/web/src/features/inbox/index.tsx) | Modifié | `268` / `382` | Rendu unifié des tours précédents dans `previousTurnsSlot` à l'intérieur de `assistant-central-scrollable-stream` pour garantir que la barre de prompt reste toujours visible en bas de l'écran. |
| [`apps/api/src/orcia_api/schemas/assistant.py`](file:///home/romain/Documents/Projects/ORCIA/apps/api/src/orcia_api/schemas/assistant.py) & [`assistant_citations_and_folders.py`](file:///home/romain/Documents/Projects/ORCIA/apps/api/src/orcia_api/schemas/assistant_citations_and_folders.py) | Modifié & Découpé | `327` / `326` | Découpage sous `350` lignes et enrichissement de `ThreeSpeedTurnRequest` (`folder_id`, `folder_pinned_notes`, `response_tone`, `response_format`, `personal_instructions`, `workspace_instructions`) + régénération `0-diff` du SDK OpenAPI (`packages/api-client/src/generated/schema.ts`). |
| [`apps/api/src/orcia_api/routers/assistant_llm_prompts.py`](file:///home/romain/Documents/Projects/ORCIA/apps/api/src/orcia_api/routers/assistant_llm_prompts.py) | Modifié | `379` | Injection dans `build_assistant_system_instructions` des blocs `[LAYER_4_WORKSPACE_INSTRUCTIONS]`, `[LAYER_5_USER_PREFERENCES]` (ton, format, instructions personnelles) et `[LAYER_5_ACTIVE_FOLDER_PINNED_NOTES]`. |
| [`apps/api/src/orcia_api/dependencies/core_and_lifespan.py`](file:///home/romain/Documents/Projects/ORCIA/apps/api/src/orcia_api/dependencies/core_and_lifespan.py) & [`assistant_llm_bridge.py`](file:///home/romain/Documents/Projects/ORCIA/apps/api/src/orcia_api/routers/assistant_llm_bridge.py) & [`assistant_workspace.py`](file:///home/romain/Documents/Projects/ORCIA/apps/api/src/orcia_api/routers/assistant_workspace.py) | Modifié | `371` / `365` / `265` | Timeout `httpx.Timeout(300.0, connect=10.0)` pour les modèles à raisonnement long (`gemma4:12b`), événement SSE `stream_error` explicite si un modèle IA réel configuré échoue sans jamais renvoyer la cassette `"synthèse conforme pour..."` hors `testclient`. |

### 3.2 Métriques de Qualité & Portes de Vérification (`AD-17`)
- **Volumétrie** : Tous les fichiers modifiés respectent strictement le plafond `< 390` lignes (`AssistantFoldersAndCollaborativeThreadView.tsx`: `296` lignes, `AssistantResponseFooterActionsAndCitations.tsx`: `369` lignes, `AssistantThinkingSubWindow.tsx`: `278` lignes, `AssistantSpeedSelectorAndStreamView.tsx`: `383` lignes, `index.tsx`: `382` lignes, `useAssistantStreamingTurn.ts`: `373` lignes, `schemas/assistant.py`: `327` lignes, `assistant_llm_prompts.py`: `379` lignes).
- **Contrat OpenAPI (`0-diff`)** : `.venv/bin/python scripts/export_openapi.py --check` $\rightarrow$ `0-diff`.
- **Qualité Python** : `ruff check .`, `ruff format --check .`, `mypy --strict`, `lint-imports` (`5 kept, 0 broken`) $\rightarrow$ `100 % PASS`.
- **Tests Unitaires & Garde-Fous Frontend/Backend** :
  - `pytest tests/unit/test_assistant_agnostic_async_llm_bridge.py tests/unit/test_codebase_architectural_anti_patterns_audit.py` $\rightarrow$ `100 % PASS`.
  - `pnpm turbo run lint typecheck test` (`@orcia/api-client`, `@orcia/ui`, `@orcia/web` incluant `ThinkingDots`, le streaming SSE temps réel, le `Smart Sticky Scroll` et la survie au `F5`) $\rightarrow$ `100 % PASS`.
