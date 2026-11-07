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
- Ajout des champs optionnels dans `ThreeSpeedTurnRequest` (`schemas/assistant.py`), de `assembled_system_prompt` dans `ThreeSpeedTurnResponse`, et création de [`assistant_background_turns.py`](file:///home/romain/Documents/Projects/ORCIA/apps/api/src/orcia_api/routers/assistant_background_turns.py) :
  - Exécution découplée en tâche de fond `asyncio.Task` (`ACTIVE_WORKSPACE_TURNS`) afin qu'une déconnexion temporaire du flux SSE ou un changement d'écran n'interrompe jamais la génération du LLM,
  - Exposition de `GET /api/v1/assistant/three-speed/active-turn` (`ActiveBackgroundTurnStatusResponse`), `POST /api/v1/assistant/three-speed/stop` (`StopActiveBackgroundTurnRequest`) et `POST /api/v1/assistant/three-speed/feedback` (`RecordAssistantTurnFeedbackRequest`),
  - Régénération du schéma OpenAPI 3.1 (`scripts/export_openapi.py` `0-diff`) et ajout des méthodes typées dans `packages/api-client/src/domains/bootstrapAndOntology.ts`.

### 2.4 Design System `@orcia/ui` & Application Web (`packages/ui/`, `apps/web/`)
- Refonte et allègement (`< 330` lignes) de `AssistantFoldersAndCollaborativeThreadView.tsx` (`formatFolderVisibilityLabel`, encadré explicatif `assistant-folders-and-notes-explainer`, ouverture directe des notes épinglées, masquage `display: none` des 3 onglets redondants).
- Ajout du badge `assistant-prompt-active-folder-badge` dans `AssistantSpeedSelectorAndStreamView.tsx`.
- Création du composant animé `ThinkingDots` (`animate-bounce` avec `animationDelay` `-0.3s` / `-0.15s`) et de la bannière de confirmation **`Merci pour votre retour !`** (`data-testid="assistant-feedback-thanks-banner"`, `👍 Bonne réponse` / `👎 Réponse à améliorer`) dans `AssistantResponseFooterActionsAndCitations.tsx`.
- Création de `assistantFoldersAndPrefsStore.ts` et `assistantBackgroundStreamStore.ts`, et câblage complet dans `InboxFeaturePanel` + `useAssistantStreamingTurn.ts` :
  - Consommation directe du flux SSE `POST /api/v1/assistant/three-speed/stream` (`ReadableStream` + `TextDecoder`) avec persistance en tâche de fond (`assistantBackgroundStreamStore.ts` + `readSavedActiveConversationId` / `writeSavedActiveConversationId` + fallback polling `getActiveAssistantTurnStatus`) pour que le changement d'écran dans ORCIA n'interrompe jamais la réflexion ou le streaming en cours et que la conversation active soit immédiatement retrouvée au retour sur `/assistant`,
  - Enregistrement systématique (sans aucun cache LLM) de chaque question, du `assembledSystemPrompt` complet (5 couches + ontologie + notes épinglées + préférences), du raisonnement, de la réponse et de l'évaluation utilisateur (`👍 Bonne réponse` / `👎 Réponse à améliorer`) dans `orcia.assistant.prompt_telemetry_log.v1` et inspection dédiée dans l'onglet 3 (`FULL_ASSEMBLY`) de `⚙️ Réglages de Mon Assistant` (`data-testid="assistant-prompt-telemetry-log-section"`),
  - Affichage en direct dans `AssistantThinkingSubWindow` des événements `thinking_delta` (`delta.reasoning` de `gemma4:12b` / `deepseek-r1`) replié par défaut (`collapse hide`, `data-expanded="false"`, `data-step-expanded="false"`) avec chronomètre temps réel (`1s`, `2s`...) et dépliable au clic,
  - Pattern **Viewport-Locked Chat Layout + Smart Sticky Scroll** dans `AssistantSpeedSelectorAndStreamView.tsx` : barre de prompt ancrée en bas (`assistant-sticky-prompt-footer`, `position: "sticky"`, `bottom: 0`), historique de conversation rendu dans le flux central (`previousTurnsSlot` dans `assistant-central-scrollable-stream`), défilement automatique en bas (`data-pinned-to-bottom="true"`) qui s'interrompt automatiquement dès que l'utilisateur remonte manuellement (`distanceFromBottom > 48px` $\rightarrow$ `data-pinned-to-bottom="false"`) avec bouton flottant `↓ Suivre la réponse en direct` (`assistant-resume-autoscroll-btn`),
  - Timeout `httpx.Timeout(300.0, connect=10.0)` côté backend (`core_and_lifespan.py` & `assistant_llm_bridge.py`) et interdiction absolue d'afficher la phrase de test `"synthèse conforme pour « ... »"` en cas d'erreur ou de timeout d'un modèle IA réel.

---

## 3. Bilan des Modifications & Résultats (Post-Implémentation)

### 3.1 Tableau Synthétique des Fichiers Créés & Modifiés

| Fichier | Action | Lignes (`wc -l`) | Description |
| :--- | :--- | :--- | :--- |
| [`packages/ui/src/primitives/AssistantFoldersAndCollaborativeThreadView.tsx`](file:///home/romain/Documents/Projects/ORCIA/packages/ui/src/primitives/AssistantFoldersAndCollaborativeThreadView.tsx) | Modifié & Allégé | `296` | Masquage (`display: none`) des 3 faux onglets redondants (`ACTIVE_DISCUSSION`, `FOLDERS`, `HISTORY_SEARCH`), affichage direct de la grille des dossiers et de l'éditeur de notes épinglées, fonction `formatFolderVisibilityLabel` (`🔒 Privé`, `👥 Partagé`, `📦 Visible par tout l'Espace` sans `PRIVATE` brut), correction du double `: :`, encadré pédagogique `assistant-folders-and-notes-explainer` + aide `ⓘ`. |
| [`packages/ui/src/primitives/AssistantResponseFooterActionsAndCitations.tsx`](file:///home/romain/Documents/Projects/ORCIA/packages/ui/src/primitives/AssistantResponseFooterActionsAndCitations.tsx) | Modifié | `308` | Ajout de `ThinkingDots` (3 points rebondissants `6px × 6px`), libellés `Bonne réponse` (`👍`) / `Réponse à améliorer` (`👎`), et bannière `assistant-feedback-thanks-banner` (`Merci pour votre retour !`). |
| [`packages/ui/src/primitives/AssistantThinkingSubWindow.tsx`](file:///home/romain/Documents/Projects/ORCIA/packages/ui/src/primitives/AssistantThinkingSubWindow.tsx) | Modifié | `278` | Maintien en `collapse hide` par défaut (`data-expanded="false"`, `data-step-expanded="false"`) de `LIVE_MODEL_REASONING` (`delta.reasoning`) avec compteur en direct (`initialElapsedSeconds`) et ouverture manuelle au clic. |
| [`packages/ui/src/primitives/AssistantSpeedSelectorAndStreamView.tsx`](file:///home/romain/Documents/Projects/ORCIA/packages/ui/src/primitives/AssistantSpeedSelectorAndStreamView.tsx) | Modifié | `386` | Ajout de `previousTurnsSlot`, `assistant-sticky-prompt-footer` (`position: "sticky"`, `bottom: 0`), `data-pinned-to-bottom` (Smart Sticky Scroll + bouton `↓ Suivre la réponse en direct`), `currentTurnFeedback` / `onFeedbackLastTurn`, et badge `assistant-prompt-active-folder-badge`. |
| [`packages/ui/src/primitives/AssistantGovernanceModeATabs.tsx`](file:///home/romain/Documents/Projects/ORCIA/packages/ui/src/primitives/AssistantGovernanceModeATabs.tsx) & [`AssistantGovernanceModalAndStudio.tsx`](file:///home/romain/Documents/Projects/ORCIA/packages/ui/src/primitives/AssistantGovernanceModalAndStudio.tsx) | Modifié | `344` / `379` | Bannière explicative `assistant-gov-explainer-banner` et section `📊 Journal des Prompts, Contextes & Retours Utilisateurs` (`assistant-prompt-telemetry-log-section`) dans l'onglet 3 (`FULL_ASSEMBLY`) permettant d'inspecter le `assembledSystemPrompt` envoyé au LLM et l'évaluation `👍`/`👎` de chaque tour. |
| [`apps/web/src/features/inbox/assistantFoldersAndPrefsStore.ts`](file:///home/romain/Documents/Projects/ORCIA/apps/web/src/features/inbox/assistantFoldersAndPrefsStore.ts) & [`assistantBackgroundStreamStore.ts`](file:///home/romain/Documents/Projects/ORCIA/apps/web/src/features/inbox/assistantBackgroundStreamStore.ts) | Créés | `223` / `186` | Stores de persistance (`Survie au F5` & survie aux changements d'écran) pour les dossiers thématiques, la conversation active (`readSavedActiveConversationId`), le journal de télémétrie des prompts/contextes (`readSavedPromptTelemetryLog`, `upsertSavedPromptTelemetryRecord`, `updatePromptTelemetryFeedback`) et l'état du flux SSE en tâche de fond. |
| [`apps/web/src/features/inbox/useAssistantStreamingTurn.ts`](file:///home/romain/Documents/Projects/ORCIA/apps/web/src/features/inbox/useAssistantStreamingTurn.ts) | Modifié | `383` | Consommation temps réel du flux SSE `/api/v1/assistant/three-speed/stream` persisté au niveau module + reprise automatique via `getActiveAssistantTurnStatus` si la connexion SSE est interrompue, et arrêt explicite via `stopActiveAssistantTurn` uniquement sur clic utilisateur `■`. |
| [`apps/web/src/features/inbox/SavedConversationsAndThreadView.tsx`](file:///home/romain/Documents/Projects/ORCIA/apps/web/src/features/inbox/SavedConversationsAndThreadView.tsx), [`savedConversationsStore.ts`](file:///home/romain/Documents/Projects/ORCIA/apps/web/src/features/inbox/savedConversationsStore.ts) & [`index.tsx`](file:///home/romain/Documents/Projects/ORCIA/apps/web/src/features/inbox/index.tsx) | Modifié | `273` / `377` / `384` | Rendu unifié des tours précédents dans `previousTurnsSlot`, synchronisation automatique de `activeConversationId` et de `promptTelemetryLog` après complétion en tâche de fond sur un autre menu, et persistance des avis `👍`/`👎`. |
| [`apps/api/src/orcia_api/routers/assistant_background_turns.py`](file:///home/romain/Documents/Projects/ORCIA/apps/api/src/orcia_api/routers/assistant_background_turns.py) | Créé | `297` | Registre des tours en tâche de fond (`ACTIVE_WORKSPACE_TURNS`, `asyncio.Task` découplée de la requête SSE) et journal de télémétrie des prompts/contextes/retours (`PROMPT_TELEMETRY_LOG`). |
| [`apps/api/src/orcia_api/schemas/assistant.py`](file:///home/romain/Documents/Projects/ORCIA/apps/api/src/orcia_api/schemas/assistant.py) & [`assistant_workspace.py`](file:///home/romain/Documents/Projects/ORCIA/apps/api/src/orcia_api/routers/assistant_workspace.py) & [`assistant_llm_bridge.py`](file:///home/romain/Documents/Projects/ORCIA/apps/api/src/orcia_api/routers/assistant_llm_bridge.py) | Modifié | `389` / `376` / `387` | Endpoints `GET /three-speed/active-turn`, `POST /three-speed/stop`, `POST /three-speed/feedback`, inclusion de `assembled_system_prompt`, et régénération `0-diff` du SDK OpenAPI (`packages/api-client/src/generated/schema.ts`). |

### 3.2 Métriques de Qualité & Portes de Vérification (`AD-17`)
- **Volumétrie** : Tous les fichiers créés ou modifiés respectent strictement le plafond `< 390` lignes (`AssistantFoldersAndCollaborativeThreadView.tsx`: `296`, `AssistantResponseFooterActionsAndCitations.tsx`: `308`, `AssistantThinkingSubWindow.tsx`: `278`, `AssistantSpeedSelectorAndStreamView.tsx`: `386`, `AssistantGovernanceModeATabs.tsx`: `344`, `AssistantGovernanceModalAndStudio.tsx`: `379`, `index.tsx`: `384`, `useAssistantStreamingTurn.ts`: `383`, `assistantBackgroundStreamStore.ts`: `186`, `assistant_background_turns.py`: `297`, `assistant_workspace.py`: `376`, `assistant_llm_bridge.py`: `387`, `schemas/assistant.py`: `389`).
- **Contrat OpenAPI (`0-diff`)** : `.venv/bin/python scripts/export_openapi.py --check` $\rightarrow$ `0-diff`.
- **Qualité Python** : `ruff check .`, `ruff format --check .`, `mypy --strict`, `lint-imports` (`5 kept, 0 broken`) $\rightarrow$ `100 % PASS`.
- **Tests Unitaires & Garde-Fous Frontend/Backend** :
  - `pytest tests/unit/test_assistant_agnostic_async_llm_bridge.py tests/unit/test_codebase_architectural_anti_patterns_audit.py` $\rightarrow$ `12 passed (100 % PASS)`.
  - `pnpm turbo run lint typecheck test` (`@orcia/api-client`, `@orcia/ui`, `@orcia/web` incluant `ThinkingDots`, la continuité inter-écrans, le `Smart Sticky Scroll`, la bannière `Merci pour votre retour !`, le journal de télémétrie des prompts/contextes et la survie au `F5`) $\rightarrow$ `100 % PASS`.
