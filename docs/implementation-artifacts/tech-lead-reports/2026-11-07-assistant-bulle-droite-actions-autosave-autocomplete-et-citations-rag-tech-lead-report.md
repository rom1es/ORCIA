# 2026-11-07 — Refonte de l'Échange `💬 Mon Assistant` : Bulle Utilisateur Bleue à Droite, Suppression Absolue des Doublons (`display: none`), Barre d'Actions sous la Réponse, Enregistrement Automatique des Réglages (`✓ Enregistré`), Menu `+` Flottant avec Autocomplétion `@Agent` / `/Compétence` & Citations RAG Cliquables

- **Date** : 2026-11-07
- **Story / Clé Sprint** : `2026-11-07-assistant-bulle-droite-actions-autosave-autocomplete-et-citations-rag` (`Post-Epic 12` / `Epic 10 — Mon Assistant Tout-en-Un`)
- **Auteur / Contexte** : Sally (UX/UI) & Winston (Architecte) — Réponse complète aux 5 captures d'écran de l'utilisateur sur `💬 Mon Assistant` (`/assistant`) :
  1. Suppression absolue des doublons et des blocs repliés via `style={{ display: "none" }}` (en complément de `sr-only`), bulle de la question utilisateur alignée à droite sur fond bleu (`var(--color-action-primary)`), indicateur animé de travail en cours (`assistant-thinking-slider-indicator`), défilement automatique (`scrollIntoView`) et barre d'actions sous la réponse (`👍 J'aime`, `👎 Je n'aime pas`, `📋 Copier`, `🔄 Régénérer`, `📄 Enregistrer en brouillon`, `☍ Poursuivre dans un Processus`).
  2. Refonte du panneau `⚙️ Réglages de Mon Assistant` (`AssistantGovernanceModalAndStudio.tsx` & `AssistantGovernanceModeATabs.tsx`) : zéro code anglais brut (`SYNTHETIC`, `BALANCED`, `STRUCTURED_SECTIONS`) ni jargon interne (`[S1]`, `🔒 AssistantHarness`), transformation de `Rôle par défaut` en vraie liste déroulante (`<select>`), et enregistrement automatique immédiat (Auto-save) avec badge vert `✓ Enregistré` (`assistant-gov-autosaved-badge`) sans fermer la fenêtre de réglages.
  3. Menu déroulant `+` flottant (`assistant-prompt-plus-popover`) et autocomplétion dynamique `@Agent` / `/Compétence` (`assistant-autocomplete-dropdown`) avec filtrage en direct au fil de la frappe, validation par `<Entrée>` ou clic qui insère `@slug` / `/slug` en tête du prompt, ajout de pièces jointes (fichier local PC et document ORCIA de l'Espace), et fermeture mutuelle immédiate au clic sur `📁 Gérer les dossiers thématiques`.
  4. Citations explicites des sources RAG internes de l'Espace (`assistant-rag-citations-list`) sous la réponse avec liens cliquables (`<a href={source.uri} target="_blank">`) redirigeant vers la source.
- **Commits associés** : branche `feat/assistant-chat-ux-autosave-settings-autocomplete-and-rag-citations`

---

## 1. Analyse du Besoin & Étude d'Impact Tech Lead (Pré-Implémentation)

### 1.1 Contexte & Problématique
Sur les 5 captures d'écran de l'utilisateur dans `💬 Mon Assistant` (`/assistant`) :
1. **Doublons visuels malgré `className="sr-only"` (Capture 4)** :
   - Le CSS chargé au runtime s'appuie sur les tokens CSS Direction C (`tokens.css`) sans générer systématiquement toutes les classes utilitaires Tailwind comme `.sr-only`. Par conséquent, `assistant-streamed-response-box` (une fois le tour enregistré dans `ActiveConversationMessagesView`), `assistant-folders-panel-wrapper` (quand `!foldersPanelOpen`), `assistant-citations-card-wrapper` et `assistant-legacy-speed-pills-row` restaient visibles à l'écran !
   - De plus, la question posée par l'utilisateur n'apparaissait pas immédiatement dans une bulle alignée à droite sur fond bleu dès le clic sur Envoyer (`isGenerating === true`), et il manquait un indicateur animé de travail en cours ainsi qu'une barre d'actions sous la réponse (`👍`, `👎`, `📋 Copier`, `🔄 Régénérer`, `📄 Brouillon`, `☍ Processus`).
2. **Jargon technique et absence d'Auto-Save dans `⚙️ Réglages de Mon Assistant` (Capture 5)** :
   - Les listes déroulantes *Ton & niveau de synthèse* et *Format de réponse préféré* affichaient les identifiants techniques bruts (`BALANCED`, `STRUCTURED_SECTIONS`).
   - Les textes par défaut contenaient du jargon interne (`Toujours citer [S1]...`, `🔒 AssistantHarness`).
   - Le champ *Rôle par défaut* était un `<input type="text">` libre au lieu d'une liste déroulante structurée.
   - L'utilisateur devait cliquer manuellement sur un bouton *Enregistrer*, ce qui fermait la modale dans `InboxFeaturePanel` au lieu d'enregistrer automatiquement chaque modification avec un indicateur visuel `✓ Enregistré`.
3. **Menu `+` non flottant et absence d'autocomplétion `@Agent` / `/Compétence` et de pièces jointes (Captures 1, 2, 3)** :
   - Le clic sur `+` affichait un bandeau statique décalant la mise en page au lieu d'un menu déroulant flottant vertical (`position: "absolute"`).
   - La frappe de `@` ou `/` (ou le clic sur `@ Mentionner un agent` / `/ Utiliser une compétence`) n'ouvrait pas de liste déroulante d'autocomplétion filtrée en temps réel permettant de sélectionner un agent ou une compétence avec `<Entrée>` ou au clic.
   - Il manquait l'ajout de fichier depuis l'ordinateur local et l'ajout de document ORCIA de l'Espace, ainsi que la fermeture mutuelle automatique des menus `+` / `@` / `/` lors du clic sur `📁 Gérer les dossiers thématiques`.
4. **Absence de liens cliquables sur les sources RAG internes sous la réponse** :
   - Les sources documentaires rattachées à l'Espace de Travail (`datasources` dans `platformSetupStore` ou documents ORCIA joints) n'étaient pas affichées sous chaque réponse avec un lien cliquable (`href`) redirigeant vers la source.

### 1.2 Exploration, Analyse d'Impact GitNexus, Factorisation & Dette Technique
- **Analyse d'Impact GitNexus (`gitnexus_query`, `gitnexus_impact`)** :
  - `AssistantSpeedSelectorAndStreamView` (`packages/ui/src/primitives/AssistantSpeedSelectorAndStreamView.tsx`) : appelé par `InboxFeaturePanel` (`apps/web/src/features/inbox/index.tsx`) et testé dans `packages/ui/src/__tests__/assistant-workspace.test.tsx` et `apps/web/src/__tests__/zero-dead-buttons-and-silent-catches-audit.test.tsx`.
  - `AssistantGovernanceModalAndStudio` (`packages/ui/src/primitives/AssistantGovernanceModalAndStudio.tsx`) : appelé par `InboxFeaturePanel` et testé dans `packages/ui/src/__tests__/assistant-workspace.test.tsx` et `packages/ui/src/__tests__/rgaa-modals-escape-unsaved-guard.test.tsx`.
  - `ActiveConversationMessagesView` (`apps/web/src/features/inbox/SavedConversationsAndThreadView.tsx`) : appelé par `InboxFeaturePanel`.
- **Opportunités de Factorisation & Contrôle Strict de Volumétrie (`< 400 lignes`)** :
  - `AssistantGovernanceModalAndStudio.tsx` faisait **588 lignes** (> 400 lignes) et `AssistantSpeedSelectorAndStreamView.tsx` faisait **396 lignes**.
  - Nous avons procédé à un découpage modulaire propre :
    1. Création de **`packages/ui/src/primitives/AssistantPromptPlusAndAutocomplete.tsx`** (`391 lignes`) regroupant le menu déroulant flottant `+` (`assistant-prompt-plus-popover`), la liste déroulante d'autocomplétion dynamique `@Agent` et `/Compétence` (`assistant-autocomplete-dropdown`), le sélecteur de fichier local PC (`assistant-local-file-input`), le sélecteur de documents ORCIA de l'Espace, et les pastilles de fichiers joints (`assistant-attached-file-pill`).
    2. Création de **`packages/ui/src/primitives/AssistantResponseFooterActionsAndCitations.tsx`** (`287 lignes`) regroupant l'indicateur animé de travail en cours (`assistant-thinking-slider-indicator`), la bulle utilisateur bleue alignée à droite (`assistant-user-question-bubble`), la barre d'actions sous la réponse (`assistant-response-actions-bar` : `👍 J'aime`, `👎 Je n'aime pas`, `📋 Copier`, `🔄 Régénérer`, `📄 Enregistrer en brouillon`, `☍ Poursuivre dans un Processus`) et la liste des citations RAG internes cliquables (`assistant-rag-citations-list`).
    3. Création de **`packages/ui/src/primitives/AssistantGovernanceModeATabs.tsx`** (`324 lignes`), permettant de ramener **`packages/ui/src/primitives/AssistantGovernanceModalAndStudio.tsx`** de 588 lignes à **`392 lignes`** (`< 400 lignes`).
    4. Maintien de **`packages/ui/src/primitives/AssistantSpeedSelectorAndStreamView.tsx`** (`375 lignes`), **`apps/web/src/features/inbox/SavedConversationsAndThreadView.tsx`** (`270 lignes`), **`apps/web/src/features/inbox/savedConversationsStore.ts`** (`313 lignes`) et **`apps/web/src/features/inbox/index.tsx`** (`331 lignes`) strictement **sous 400 lignes**.

---

## 2. Plan d'Implémentation

### 2.1 Schéma de Données & Migrations Alembic
- Aucune migration Alembic requise (évolution purement Frontend `@orcia/ui` & `apps/web` s'appuyant sur les contrats OpenAPI et stores existants).

### 2.2 Noyau Métier Hexagonal, Orchestration & Workers
- Aucun impact sur `packages/orcia-kernel`, `packages/orcia-core` ou `apps/worker` (les 5 contrats `lint-imports` restent intacts).

### 2.3 Couche Backend API, Sécurité & Contrats (`apps/api/`, `packages/api-client/`)
- Aucun changement de contrat OpenAPI requis (`0-diff` préservé).

### 2.4 Interface Utilisateur & Expérience (`packages/ui/` & `apps/web/`)
1. **Suppression absolue des doublons via `style={{ display: "none" }}`** :
   - Dans `AssistantSpeedSelectorAndStreamView.tsx` : application de `style={hideDuplicateCompletedStream && !isStoppedVisible ? { display: "none" } : undefined}` sur `assistant-streamed-response-box` et `style={hideLegacySpeedPills ? { display: "none" } : undefined}` sur `assistant-legacy-speed-pills-row`.
   - Dans `apps/web/src/features/inbox/index.tsx` : application de `style={foldersPanelOpen ? undefined : { display: "none" }}` sur `assistant-folders-panel-wrapper` et `style={{ display: "none" }}` sur `assistant-citations-card-wrapper`.
2. **Cinématique de l'échange, Bulle Utilisateur Bleue à droite, Indicateur animé, Auto-scroll & Barre d'Actions (`AssistantResponseFooterActionsAndCitations.tsx`, `AssistantSpeedSelectorAndStreamView.tsx`, `SavedConversationsAndThreadView.tsx`)** :
   - Affichage de la question de l'utilisateur dans une bulle alignée à droite (`marginLeft: "auto"`, `maxWidth: "75%"`, `borderRadius: "18px 18px 4px 18px"`, `backgroundColor: "var(--color-action-primary)"`, `color: "var(--color-primary-foreground)"`, `padding: "10px 16px"`, `fontWeight: 500`) aussi bien dans `ActiveConversationMessagesView` que pendant la génération en cours (`isGenerating === true`).
   - Tant que `isGenerating === true` et que `streamedText` est vide, affichage de l'indicateur animé `data-testid="assistant-thinking-slider-indicator"` sous la question (avec barre/slider de progression animée et trois points pulsants `•••`).
   - Déclenchement du défilement automatique (`scrollIntoView({ behavior: "smooth", block: "end" })` avec garde `typeof el?.scrollIntoView === "function"`) à chaque mise à jour de `streamedText`.
   - Affichage sous chaque réponse de l'Assistant de la barre d'actions `data-testid="assistant-response-actions-bar"` (`assistant-action-like-btn`, `assistant-action-dislike-btn`, `assistant-action-copy-btn`, `assistant-action-regenerate-btn`, `assistant-action-save-draft-btn`, `assistant-action-continue-process-btn`).
3. **Refonte de `⚙️ Réglages de Mon Assistant` (`AssistantGovernanceModalAndStudio.tsx` & `AssistantGovernanceModeATabs.tsx`)** :
   - Remplacement des options brutes par des libellés explicites en français (`Synthétique & Direct (Aller à l'essentiel)`, `Équilibré & Structuré (Recommandé)`, `Détaillé & Illustré (Avec exemples complets)` ; `Points clés (Liste à puces)`, `Sections structurées avec titres`, `Guide étape par étape`).
   - Remplacement des valeurs par défaut `initialPersonalInstructions`, `initialWorkspaceInstructions` et `initialStudioPrePrompt` pour éliminer tout jargon `[S1]` ou `🔒 AssistantHarness`.
   - Transformation du champ `Rôle par défaut` en `<select>` proposant les 7 rôles (`PM`, `TECH_LEAD`, `DEV`, `ANALYST`, `QA_COMPLIANCE`, `PLATFORM_ADMIN`, `CONTRIBUTOR`) et exposition de `data-testid="assistant-gov-hat-input"` (`assistant-gov-tone-select`, `assistant-gov-format-select`) tout en préservant les alias de compatibilité pour les tests existants.
   - Déclenchement automatique de `onSaveUserPreferences` / `onSaveWorkspaceSettings` dès modification d'un réglage, affichage du badge vert `✓ Enregistré` (`data-testid="assistant-gov-autosaved-badge"`), maintien de la fenêtre de réglages ouverte dans `InboxFeaturePanel`, et masquage (`style={{ display: "none" }}`) des boutons d'enregistrement manuel.
4. **Menu `+` flottant, Autocomplétion `@Agent` / `/Compétence` et Pièces jointes (`AssistantPromptPlusAndAutocomplete.tsx`)** :
   - Menu `+` flottant en `position: "absolute"` avec les 5 entrées (`@ Mentionner un agent`, `/ Utiliser une compétence`, `💻 Ajouter un fichier depuis mon ordinateur`, `🗂️ Ajouter un document disponible dans ORCIA`, `📁 Gérer les dossiers thématiques`).
   - Liste déroulante d'autocomplétion dynamique `data-testid="assistant-autocomplete-dropdown"` (`data-trigger-kind="agent" | "skill"`) filtrée en direct après `@` ou `/`, validée par `<Entrée>` ou clic sur `assistant-autocomplete-option-${slug}` pour insérer `@slug ` ou `/slug ` en tête du prompt sans soumettre le message.
   - Fermeture mutuelle des menus `+` / `@` / `/` dès clic sur `📁 Gérer les dossiers thématiques`.
5. **Citations des sources RAG internes avec liens cliquables (`AssistantResponseFooterActionsAndCitations.tsx`)** :
   - Affichage sous la réponse de `data-testid="assistant-rag-citations-list"` avec `<a href={source.uri} target="_blank" rel="noopener noreferrer" data-testid="assistant-rag-citation-link-${index}">📄 {source.title} ↗</a>`.

---

## 3. Bilan des Modifications & Résultats (Post-Implémentation)

### 3.1 Fichiers Développés & Modifiés
| Fichier | Nature | Description synthétique |
| :--- | :--- | :--- |
| `packages/ui/src/primitives/AssistantPromptPlusAndAutocomplete.tsx` | Création (`391 lignes`) | Menu déroulant flottant `+` (`assistant-prompt-plus-popover`), autocomplétion dynamique `@Agent` / `/Compétence` (`assistant-autocomplete-dropdown`), sélecteur de fichier local PC, sous-menu documents ORCIA, et pastilles de pièces jointes. |
| `packages/ui/src/primitives/AssistantResponseFooterActionsAndCitations.tsx` | Création (`287 lignes`) | Bulle utilisateur alignée à droite sur fond bleu (`AssistantUserQuestionBubble`), indicateur animé de travail en cours (`AssistantThinkingSliderIndicator`), barre d'actions sous la réponse (`👍`, `👎`, `📋 Copier`, `🔄 Régénérer`, `📄 Brouillon`, `☍ Processus`) et citations RAG cliquables (`assistant-rag-citations-list`). |
| `packages/ui/src/primitives/AssistantGovernanceModeATabs.tsx` | Création (`324 lignes`) | Extraction des 3 onglets du Mode A de `AssistantGovernanceModalAndStudio` avec libellés français des listes déroulantes, `<select>` pour le Rôle par défaut (`assistant-gov-hat-input`) et déclenchement de l'Auto-save. |
| `packages/ui/src/primitives/AssistantGovernanceModalAndStudio.tsx` | Refactoring (`392 lignes`) | Réduction de 588 à 392 lignes (`< 400 lignes`), valeurs par défaut sans jargon `[S1]` / `🔒 AssistantHarness`, et enregistrement automatique avec badge vert `✓ Enregistré` (`assistant-gov-autosaved-badge`). |
| `packages/ui/src/primitives/AssistantSpeedSelectorAndStreamView.tsx` | Modification (`375 lignes`) | Intégration de `style={{ display: "none" }}` anti-doublons, bulle utilisateur en cours de génération, indicateur animé, auto-scroll (`scrollIntoView`), barre d'actions, citations RAG et autocomplétion `@`/`/`. |
| `packages/ui/src/index.ts` | Modification | Export public des nouvelles primitives et types `@orcia/ui`. |
| `apps/web/src/features/inbox/SavedConversationsAndThreadView.tsx` | Modification (`270 lignes`) | Affichage de la bulle utilisateur alignée à droite sur fond bleu, de la barre d'actions et des citations RAG cliquables dans `ActiveConversationMessagesView`. |
| `apps/web/src/features/inbox/savedConversationsStore.ts` | Modification (`313 lignes`) | Fonction `buildAssistantAutocompleteAndRagOptions` agrégeant les agents/compétences du catalogue et les sources RAG de l'Espace. |
| `apps/web/src/features/inbox/index.tsx` | Modification (`331 lignes`) | Application de `style={{ display: "none" }}` sur `assistant-folders-panel-wrapper` et `assistant-citations-card-wrapper`, maintien de `governanceOpen` lors de l'Auto-save, et câblage des actions et citations RAG. |
| `packages/ui/src/__tests__/assistant-workspace.test.tsx` | Modification | Ajout du test `Story 10.2d` validant la bulle bleue alignée à droite, l'indicateur animé, `display: none`, la barre d'actions, l'Auto-save avec badge vert `✓ Enregistré`, l'autocomplétion `@`/`/` et les citations RAG cliquables. |
| `apps/web/src/__tests__/zero-dead-buttons-and-silent-catches-audit.test.tsx` | Modification | Vérification de `style.display === "none"` sur les blocs masqués et de la bulle utilisateur bleue alignée à droite dans `InboxFeaturePanel`. |

### 3.2 Résultats Chiffrés, Métriques & Qualité
- **Tests unitaires & d'intégration TypeScript (`Vitest`)** :
  - `@orcia/ui` : **15 fichiers de tests passés (`59/59` tests verts)**, y compris `ui-isolation.test.ts` (zéro couleur hexadécimale en dur hors `tokens.css`).
  - `@orcia/web` : **4 fichiers de tests passés (`36/36` tests verts)**, y compris l'audit anti-LastPass sur 100 % des `<input>` / `<textarea>` et l'audit zéro bouton muet.
- **Contrôle de volumétrie (`< 400 lignes`)** :
  - `AssistantPromptPlusAndAutocomplete.tsx` : `391 lignes`
  - `AssistantResponseFooterActionsAndCitations.tsx` : `287 lignes`
  - `AssistantGovernanceModeATabs.tsx` : `324 lignes`
  - `AssistantGovernanceModalAndStudio.tsx` : `392 lignes` (réduit depuis `588 lignes`)
  - `AssistantSpeedSelectorAndStreamView.tsx` : `375 lignes`
  - `SavedConversationsAndThreadView.tsx` : `270 lignes`
  - `savedConversationsStore.ts` : `313 lignes`
  - `apps/web/src/features/inbox/index.tsx` : `331 lignes`
- **Qualité statique & Architecture** :
  - `pnpm turbo run lint typecheck test` : `9/9 tasks successful, 0 error`
  - `.venv/bin/ruff check .` & `.venv/bin/ruff format --check .` : `All checks passed! 537 files already formatted`
  - `.venv/bin/mypy --strict packages/orcia-kernel packages/orcia-core apps/api apps/worker` : `Success: no issues found in 210 source files`
  - `.venv/bin/lint-imports` : `5 contracts kept, 0 broken`

### 3.3 Validation & Procédure de Test (`AD-17` & Garde-Fous de Câblage Vertical)
- **Couche 1 — Tests Unitaires `@orcia/ui` & `@orcia/web`** : Validation complète de la bulle utilisateur alignée à droite sur fond bleu (`var(--color-action-primary)`), de l'absence totale de doublons (`style.display === "none"`), de la barre d'actions sous la réponse (`👍`, `👎`, `📋 Copier`, `🔄 Régénérer`), des réglages en français avec Auto-save (`✓ Enregistré`), de l'autocomplétion dynamique `@Agent` / `/Compétence` avec filtrage temps réel et validation `<Entrée>`, et des liens cliquables vers les sources RAG internes.
- **Couche 5 — Survie au `F5` (`unmount()` + `render()`) & Garde-Fou n°5 (`zero-dead-buttons-and-silent-catches-audit.test.tsx`)** : 100 % des callbacks d'action sont câblés et testés de bout en bout.
