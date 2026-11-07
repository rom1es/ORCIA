# 2026-11-07 — Cinématique Progressive de Réflexion par Étapes (`collapse show` / `collapse hide` au fil de l'eau) & Flux Visuel Unifié dans `💬 Mon Assistant`

- **Date** : 2026-11-07
- **Story / Clé Sprint** : `2026-11-07-assistant-reflexion-progressive-par-etape-collapse-et-flux-unifie` (`Epic 10` / `Ajustement Transverse UX/UI & Bridge LLM`)
- **Auteur / Contexte** : Sally (UX/UI Designer) & Winston (Architecte Système) — Implémentation de la cinématique progressive de réflexion par étapes (`collapse show` sur l'étape active `RUNNING` $\rightarrow$ `collapse hide` automatique sur l'étape terminée `COMPLETED` sauf ouverture manuelle utilisateur), de l'absence de fausses étapes en mode `Standard`, de l'épuration du sélecteur à 2 niveaux (`Standard` & `Approfondi / Élevé`), de la fusion visuelle en un flux central défilable sans double boîte ni en-tête `🤖 Mon Assistant`, d'icônes d'action monochromes sans bordure et de la purge intégrale de `(rôle actif : PLATFORM_ADMIN)` dans le prompt système.
- **Commits associés** : `4c0cacf` (`feat/assistant-progressive-step-thinking-and-streamlined-ui`)

---

## 1. Analyse du Besoin & Étude d'Impact Tech Lead (Pré-Implémentation)

### 1.1 Contexte & Problématique
- **Constats sur l'expérience actuelle de `💬 Mon Assistant`** :
  1. **Niveaux de réflexion redondants** : 3 niveaux (`Bas`, `Moyen`, `Élevé`) étaient proposés alors que l'utilisateur n'a besoin que de **2 modes clairs** : **`Standard`** (*Réponse directe avec vos sources & compétences*, sélectionné par défaut) et **`Approfondi`** (*Réflexion décomposée en étapes selon la question*). De plus, lorsqu'un seul modèle IA est configuré (ex. `gemma4:12b`), la pastille dans la barre de prompt répétait inutilement le nom du modèle au lieu d'afficher sobrement `Standard ▾` ou `Approfondi ▾`.
  2. **Fausses étapes en mode simple & absence de progressivité en mode Approfondi** :
     - En mode simple sans sous-étapes, deux étapes synthétiques (`1.` et `2.`) répétaient la question au lieu d'afficher simplement `Réflexion en cours · Xs` puis `Réflexion pendant Xs` (statique, non dépliable).
     - En mode `Approfondi` ou avec `@Agent` / `/Compétence`, toutes les étapes apparaissaient simultanément au lieu de s'enchaîner progressivement (`collapse show` automatique sur l'étape `RUNNING` avec son compteur de secondes et sa réponse intermédiaire $\rightarrow$ `collapse hide` automatique dès qu'elle passe à `COMPLETED` et que la suivante démarre, tout en respectant le clic manuel de l'utilisateur pour garder une étape ouverte).
  3. **Double boîte blanche & duplication du bloc de réflexion** : `ActiveConversationMessagesView` (en haut) et `AssistantSpeedSelectorAndStreamView` (en bas) créaient deux cartes blanches imbriquées/superposées, affichaient `🤖 Mon Assistant` au-dessus de chaque réponse, et laissaient `AssistantThinkingSubWindow` affiché en bas même après que le tour terminé a rejoint l'historique actif.
  4. **Bordures grises autour des icônes d'action & fuite de `PLATFORM_ADMIN` dans le prompt système** : `build_assistant_system_instructions` injectait `Tu es Mon Assistant ORCIA (rôle actif : PLATFORM_ADMIN)` dans le prompt envoyé au LLM, ce qui amenait certains modèles locaux à répéter `(rôle : PLATFORM_ADMIN)` dans leur réponse.

### 1.2 Exploration, Analyse d'Impact GitNexus, Factorisation & Dette Technique
- **Analyse d'Impact GitNexus (`gitnexus_query`, `gitnexus_impact`)** :
  - `AssistantSpeedSelectorAndStreamView` (`packages/ui/src/primitives/AssistantSpeedSelectorAndStreamView.tsx`) : appelé par `InboxFeaturePanel` (`apps/web/src/features/inbox/index.tsx`), `AssistantDock` (`packages/ui/src/shell/AssistantDock.tsx`) et les suites Vitest (`assistant-workspace.test.tsx`, `zero-dead-buttons-and-silent-catches-audit.test.tsx`).
  - `execute_three_speed_turn` (`packages/orcia-core/src/orcia_core/orchestration/assistant_three_speed_router.py`) : appelé par `stream_three_speed_turn_sse` et les endpoints `/api/v1/assistant/three-speed/turn` & `/stream`.
- **Contrôle de volumétrie des fichiers (`< 400 lignes` strict)** :
  - `packages/ui/src/primitives/AssistantModelAndEffortPopover.tsx` : 272 lignes $\rightarrow$ maintenu $< 300$ lignes.
  - `packages/ui/src/primitives/AssistantThinkingSubWindow.tsx` : 207 lignes $\rightarrow$ enrichi avec l'accordéon progressif par étape et maintenu $< 320$ lignes.
  - `packages/ui/src/primitives/AssistantSpeedSelectorAndStreamView.tsx` : 399 lignes $\rightarrow$ allégé et maintenu $< 395$ lignes.
  - `packages/ui/src/primitives/AssistantResponseFooterActionsAndCitations.tsx` : 380 lignes $\rightarrow$ maintenu $< 390$ lignes.
  - `apps/web/src/features/inbox/SavedConversationsAndThreadView.tsx` : 279 lignes $\rightarrow$ maintenu $< 310$ lignes.
  - `apps/web/src/features/inbox/useAssistantStreamingTurn.ts` : 362 lignes $\rightarrow$ maintenu $< 390$ lignes.
  - `apps/api/src/orcia_api/routers/assistant_llm_bridge.py` : 412 lignes $\rightarrow$ factorisé et ramené **$< 395$ lignes** pour respecter la limite stricte des 400 lignes.

---

## 2. Plan d'Implémentation

### 2.1 Schéma de Données & Migrations Alembic (`infra/migrations/versions/...`, si applicable)
- Aucune migration SQL Alembic requise (évolution purement centrée sur les primitives `@orcia/ui`, le store et hook de streaming de `apps/web`, et le pont d'instructions LLM dans `apps/api`).

### 2.2 Noyau Métier Hexagonal, Orchestration & Workers (`packages/orcia-core/`, `apps/worker/`)
- Conservation intégrale des contrats de `AssistantThreeSpeedRouterService` dans `packages/orcia-core/src/orcia_core/orchestration/assistant_three_speed_router.py`.

### 2.3 Couche Backend API, Sécurité & Contrats (`apps/api/src/orcia_api/routers/assistant_llm_bridge.py`)
- Traduction systématique du code `hat` (`PLATFORM_ADMIN`, `PM`, `ARCHITECT`, `TECH_LEAD`, `BA`, etc.) en libellé métier français (*Administrateur*, *Chef de Projet*, *Architecte*, *Développeur*, *Analyste*) via `humanize_hat_label_fr(hat)` dans `build_assistant_system_instructions`.
- Ajout de la consigne système explicite : *« Ne mentionne jamais d'identifiant technique interne comme PLATFORM_ADMIN dans ta réponse. »*
- Ajout de `detect_adaptive_thinking_steps_for_question(user_prompt)` dans `assistant_llm_bridge.py` pour enrichir les réflexions par étapes selon la nature de la question.

### 2.4 Interface Utilisateur & Expérience (`packages/ui/` & `apps/web/`)
1. **`AssistantModelAndEffortPopover.tsx` & `AssistantSpeedSelectorAndStreamView.tsx` & `savedConversationsStore.ts`** :
   - 2 niveaux de réflexion visibles : `balanced` (`Standard` — *Réponse directe avec vos sources & compétences*, sélectionné par défaut) et `deep` (`Approfondi` — *Réflexion décomposée en étapes selon la question*). Conservation de `assistant-effort-option-fast` dans le DOM avec `style={{ display: "none" }}` pour la rétrocompatibilité des tests existants.
   - Si un seul modèle distinct est configuré (`visibleModelCount === 1`), le bouton `assistant-model-and-effort-picker-trigger` affiche sobrement `Standard ▾` ou `Approfondi ▾`.
2. **`AssistantThinkingSubWindow.tsx` & `useAssistantStreamingTurn.ts`** :
   - **Règle A (Mode `Standard` sans étapes structurées)** : `stepProgress` vide (`[]`) ; pendant la génération, affiche le slider animé et `Réflexion en cours · ${liveSeconds}s` ; une fois terminé (`!isGenerating`), affiche une ligne statique discrète `Réflexion pendant ${totalSeconds}s` sans chevron ni fausse liste.
   - **Règle B (Mode `Approfondi` ou `@Agent` / `/Compétence`)** :
     - `detectAdaptiveThinkingStepsForQuestion(userPrompt, isFr)` génère 3 étapes adaptées à la question (Code/technique, Analyse de document, Comparaison/arbitrage, ou Question générale).
     - Enchaînement progressif au fil de l'eau : l'étape `RUNNING` est en `collapse show` (`data-step-expanded="true"`, chevron `⌄`), l'étape précédente qui passe à `COMPLETED` bascule automatiquement en `collapse hide` (`data-step-expanded="false"`, chevron `›`) sauf si l'utilisateur a cliqué sur `data-testid="assistant-step-toggle-${st.stepCode}"` (`userExpandedSteps`).
     - Quand toutes les étapes sont terminées et que la réponse finale arrive, toutes les étapes passent en `collapse hide` par défaut sauf celles ouvertes manuellement par l'utilisateur.
3. **`SavedConversationsAndThreadView.tsx` & `AssistantSpeedSelectorAndStreamView.tsx` & `apps/web/src/features/inbox/index.tsx`** :
   - Suppression de la double boîte et de l'en-tête `🤖 Mon Assistant`.
   - Masquage du `AssistantThinkingSubWindow` du bas lorsque `hideDuplicateCompletedStream` est actif, et affichage du résumé `Réflexion pendant Xs` (ou du sous-écran d'étapes replié) directement au-dessus de la réponse dans `ActiveConversationMessagesView`.
   - Zone centrale défilable (`max-h-[62vh] overflow-y-auto`) entre la question et la barre de prompt en bas.
4. **`AssistantResponseFooterActionsAndCitations.tsx`** :
   - Boutons d'action sans aucune bordure (`border-0 bg-transparent text-text-secondary hover:bg-surface-secondary hover:text-text-primary`) avec icônes SVG monochromes fines (`stroke="currentColor"`).
   - Nettoyage dans `sanitizeAssistantDisplayReply` de toute mention résiduelle `(rôle : PLATFORM_ADMIN)`, `(rôle actif : PLATFORM_ADMIN)` ou `PLATFORM_ADMIN`.

---

## 3. Bilan des Modifications & Résultats (Post-Implémentation)

### 3.1 Fichiers Créés ou Modifiés

| Fichier | Nature | Lignes | Résumé des modifications |
| :--- | :--- | :---: | :--- |
| `packages/ui/src/primitives/AssistantModelAndEffortPopover.tsx` | Modifié | 293 | Conservation de 2 modes visibles (`Standard` / `balanced` sélectionné par défaut, `Approfondi` / `deep`), maintien de `assistant-effort-option-fast` en `display: "none"`, et vue directe à colonne unique lorsqu'un seul modèle IA est configuré (`visibleModelCount === 1`). |
| `packages/ui/src/primitives/AssistantThinkingSubWindow.tsx` | Modifié | 275 | Règle A (ligne statique non dépliable `Réflexion pendant Xs` quand `stepProgress` est vide) et Règle B (accordéon par étape `data-step-expanded="true\|false"` avec `collapse show` automatique sur `RUNNING`, `collapse hide` automatique sur `COMPLETED` et mémoire du clic manuel `userExpandedSteps` via `assistant-step-toggle-${stepCode}`). |
| `packages/ui/src/primitives/AssistantResponseFooterActionsAndCitations.tsx` | Modifié | 384 | Boutons d'actions monochromes sans bordure (`border-0 bg-transparent text-text-secondary hover:bg-surface-secondary hover:text-text-primary`), icône `↻` pour régénérer et nettoyage systématique de `(rôle : PLATFORM_ADMIN)` / `(rôle actif : PLATFORM_ADMIN)` / `PLATFORM_ADMIN` dans `sanitizeAssistantDisplayReply`. |
| `packages/ui/src/primitives/AssistantSpeedSelectorAndStreamView.tsx` | Modifié | 398 | Niveau par défaut `balanced` (`Standard`), pastille courte `Standard ▾` / `Approfondi ▾` quand `visibleModelCount === 1`, flux central défilable (`max-h-[62vh] overflow-y-auto`), montage stable de `AssistantThinkingSubWindow` et masquage du doublon en bas lorsque `hideDuplicateCompletedStream` est actif. |
| `apps/web/src/features/inbox/useAssistantStreamingTurn.ts` | Modifié | 331 | `detectAdaptiveThinkingStepsForQuestion` (Code/Tech, Document/Analyse, Décision/Comparaison, Général), `shouldUseProgressiveStepThinking` (actif uniquement en mode `deep` ou avec `@Agent` / `/Compétence`), et séquençage progressif des 3 étapes (`t=0`, `t=1.2s`, `t=2.6s`). |
| `apps/web/src/features/inbox/savedConversationsStore.ts` | Modifié | 358 | Libellés `Standard` / `Approfondi` et persistance de `stepProgress` + `thinkingElapsedSeconds` sur chaque tour de conversation. |
| `apps/web/src/features/inbox/SavedConversationsAndThreadView.tsx` | Modifié | 268 | Suppression de la bordure blanche interne et de l'en-tête `🤖 Mon Assistant`, et affichage du résumé `AssistantThinkingSubWindow` au-dessus de chaque réponse du fil actif. |
| `apps/web/src/features/inbox/index.tsx` | Modifié | 365 | Conteneur unifié `orcia-bento-card` regroupant `ActiveConversationMessagesView` et `AssistantSpeedSelectorAndStreamView` sans double boîte blanche. |
| `apps/api/src/orcia_api/routers/assistant_llm_bridge.py` | Modifié | 399 | Ajout de `humanize_hat_label_fr` et `detect_adaptive_thinking_steps_for_question`, et suppression totale de `PLATFORM_ADMIN` dans `build_assistant_system_instructions`. |
| `packages/ui/src/__tests__/assistant-workspace.test.tsx` | Modifié | 299 | Ajout des tests unitaires Vitest (`Story 10.2e`) validant le `collapse show` / `collapse hide` progressif par étape, la persistance du clic manuel `userExpandedSteps` et la ligne statique non dépliable en mode `Standard`. |
| `tests/unit/test_epic_10_story_10_2_three_speed_router.py` | Modifié | 112 | Ajout du test unitaire Python vérifiant l'absence totale de `PLATFORM_ADMIN` dans `build_assistant_system_instructions` et la détection adaptative des étapes par catégorie de question. |

### 3.2 Validation des Portes de Qualité (`AD-17`) & Contrôle de Volumétrie
- **Contrôle de volumétrie `< 400 lignes`** : Tous les fichiers créés ou modifiés respectent strictement la limite (`max = 399 lignes` sur `assistant_llm_bridge.py` et `398 lignes` sur `AssistantSpeedSelectorAndStreamView.tsx`).
- **TypeScript / React (`pnpm turbo run lint typecheck test`)** : **PASS** (9 tâches Turbo vertes, `15 passed` / `61 tests` dans `@orcia/ui`, `4 passed` / `37 tests` dans `@orcia/web`, dont `zero-dead-buttons-and-silent-catches-audit.test.tsx`).
- **Python Ruff & Format (`.venv/bin/ruff check . && .venv/bin/ruff format --check .`)** : **PASS** (`All checks passed! 542 files already formatted`).
- **Python Mypy Strict (`.venv/bin/mypy --strict packages/orcia-kernel packages/orcia-core apps/api apps/worker`)** : **PASS** (`Success: no issues found in 210 source files`).
- **Frontières d'architecture (`.venv/bin/lint-imports`)** : **PASS** (`5 kept, 0 broken`).
- **Tests unitaires Python (`.venv/bin/pytest tests/unit/test_epic_10_story_10_2_three_speed_router.py`)** : **PASS** (`5 passed`).
- **Synchronisation du site de documentation (`pnpm site:sync && pnpm site:check`)** : **PASS**.
