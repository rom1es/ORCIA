# 2026-11-06 — Streaming Progressif de `💬 Mon Assistant`, Bouton Play/Stop (`▶` / `■`) & Sous-Fenêtre de Réflexion avec Compteur Temps Réel

- **Date** : 2026-11-06
- **Story / Clé Sprint** : `2026-11-06-streaming-assistant-bouton-stop-et-sous-fenetre-reflexion` (`Post-Epic 12 / Epic 10 UX & Streaming LLM`)
- **Auteur / Contexte** : Dialogue Tech Lead Sally (UX/UI) & Winston (Architecte) — Implémentation bout-en-bout du streaming progressif de `💬 Mon Assistant` (`/assistant`), du bouton d'action unique à bascule Triangle (`▶`) $\leftrightarrow$ Carré plein (`■`) avec interruption immédiate (`Stop`), et de la sous-fenêtre de réflexion intermédiaire repliable/dépliable avec compteur temps réel en secondes (`0s` $\rightarrow$ `1s` $\rightarrow$ `2s`…) et réponses des prompts intermédiaires (`intermediateOutput`).
- **Commits associés** : Branche `feat/assistant-live-streaming-stop-button-and-thinking-subwindow`

---

## 1. Analyse du Besoin & Étude d'Impact Tech Lead (Pré-Implémentation)

### 1.1 Contexte & Problématique
- **Problème constaté** :
  1. Lorsqu'une question était envoyée à `💬 Mon Assistant`, le bouton d'envoi passait en état `disabled` (`⏳ ...`) sans possibilité d'interrompre la génération en cours.
  2. Les étapes de réflexion n'apparaissaient qu'une fois l'appel HTTP complet terminé, sans compteur de temps réel en secondes ni affichage des réponses des prompts intermédiaires / du raisonnement (`thinking`) du modèle.
  3. Le texte de la réponse principale s'affichait d'un seul bloc à la fin au lieu de s'écrire progressivement au fil de l'eau (streaming).
- **Comportement attendu (validé avec l'utilisateur)** :
  1. **Bouton d'action unique à bascule Triangle (`▶`) $\leftrightarrow$ Carré plein (`■`)** :
     - À l'arrêt (`!isGenerating`) : affiche un triangle `▶` (`data-testid="assistant-send-play-icon"`) + libellé d'envoi ; cliquer lance l'appel.
     - En cours de réflexion/génération (`isGenerating === true`) : le bouton **reste actif (non `disabled`)**, affiche un carré plein `■` (`data-testid="assistant-stop-square-icon"`, `aria-label="Arrêter la réflexion de Mon Assistant"`), et permet d'interrompre immédiatement la génération (`AbortController.abort()` + arrêt des timers), conserve à l'écran les étapes et le début de réponse déjà affichés avec le badge discret **`⏹ Génération interrompue par l'utilisateur`** (`data-testid="assistant-generation-stopped-badge"`), et redonne le focus au champ de saisie (`assistant-three-speed-input`).
  2. **Sous-fenêtre de réflexion repliable/dépliable (`AssistantThinkingSubWindow`) avec compteur en secondes temps réel & réponses intermédiaires** :
     - Placée juste au-dessus de la boîte de réponse principale (`assistant-streamed-response-box`).
     - **Ouverte automatiquement** (`data-expanded="true"`) dès le lancement de la question (`isGenerating === true`), puis **repliée automatiquement** (`data-expanded="false"`) dès que la réponse finale s'écrit (ou se termine), tout en restant dépliable/repliable à tout moment au clic sur son en-tête (`data-testid="assistant-thinking-subwindow-toggle"`).
     - Affiche un compteur en secondes temps réel (`0s` $\rightarrow$ `1s` $\rightarrow$ `2s`…) dans l'en-tête (`Réflexion en cours · Xs`) et sur chaque étape en cours (`data-testid="assistant-step-live-timer-${stepCode}"`), puis fige la durée une fois l'étape terminée.
     - Affiche sous chaque étape un encadré lisible (`data-testid="assistant-step-intermediate-output-${stepCode}"`) contenant la réponse du prompt intermédiaire / le flux `thinking` du modèle.
  3. **Streaming progressif au fil de l'eau** :
     - Côté Backend (`assistant_llm_bridge.py`, `assistant_workspace.py`, `schemas/assistant.py`, `assistant_three_speed_router.py`) : enrichissement de `ThreeSpeedStepProgressItem` / `ThreeSpeedStepProgressSchemaItem` avec `intermediate_output: str | None = None`, extraction du raisonnement intermédiaire (`thinking` Ollama / analyse cadrée) et générateur de streaming `stream_configured_llm_for_assistant_turn(...)` sur `POST /api/v1/assistant/three-speed/stream` émettant `step_progress`, `thinking_delta`, `token_delta` / `token` et `turn_completed` / `done`.
     - Côté Frontend (`useAssistantStreamingTurn.ts`, `InboxFeaturePanel`, `AssistantSpeedSelectorAndStreamView.tsx`) : progression temps réel des étapes dans la sous-fenêtre, écriture progressive du texte dans `assistant-streamed-response-box`, repli automatique de la sous-fenêtre de réflexion et support de l'arrêt immédiat via `AbortController`.

### 1.2 Exploration, Analyse d'Impact GitNexus, Factorisation & Dette Technique
- **Analyse d'Impact GitNexus (`gitnexus_query`, `gitnexus_context`, `gitnexus_impact`)** :
  - `AssistantSpeedSelectorAndStreamView` (`packages/ui/src/primitives/AssistantSpeedSelectorAndStreamView.tsx`) : appelé dans `apps/web/src/features/inbox/index.tsx` et testé dans `packages/ui/src/__tests__/assistant-workspace.test.tsx` + `apps/web/src/__tests__/zero-dead-buttons-and-silent-catches-audit.test.tsx`.
  - `invoke_configured_llm_for_assistant_turn` (`apps/api/src/orcia_api/routers/assistant_llm_bridge.py`) : appelé dans `apps/api/src/orcia_api/routers/assistant_workspace.py` (`execute_three_speed_turn_endpoint`, `stream_three_speed_turn_endpoint`) et testé dans `tests/unit/test_epic_10_story_10_2_three_speed_router.py`.
- **Opportunités de Factorisation & Contrôle de Volumétrie (`< 400 lignes`)** :
  - `packages/ui/src/primitives/AssistantSpeedSelectorAndStreamView.tsx` faisait `452 lignes` : extraction de la sous-fenêtre de réflexion dans `packages/ui/src/primitives/AssistantThinkingSubWindow.tsx` (`163 lignes`), ramenant `AssistantSpeedSelectorAndStreamView.tsx` à `376 lignes`.
  - `apps/web/src/features/inbox/index.tsx` faisait `469 lignes` : extraction de la logique d'exécution et de streaming avec `AbortController` dans `apps/web/src/features/inbox/useAssistantStreamingTurn.ts` (`318 lignes`), ramenant `apps/web/src/features/inbox/index.tsx` à `388 lignes`.

---

## 2. Plan d'Implémentation

### 2.1 Schéma de Données & Migrations Alembic
- Aucune migration SQL Alembic requise.

### 2.2 Noyau Métier Hexagonal (`packages/orcia-core/src/orcia_core/orchestration/assistant_three_speed_router.py`)
- Ajout du champ optionnel `intermediate_output: str | None = None` sur `ThreeSpeedStepProgressItem`.
- Enrichissement des étapes `SPEED_1_FAST`, `SPEED_2_AGENT_TOOLS` et `SPEED_3_DEEP_AUDIT` avec des sorties intermédiaires explicites et structurées (`intermediate_output`), ainsi que la prise en compte d'un `llm_thinking_override: str | None = None` issu du pont LLM.
- Mise à jour de `stream_three_speed_turn_sse` pour inclure `intermediate_output` dans chaque événement `step_progress`.

### 2.3 Couche Backend API & SDK OpenAPI (`apps/api/`, `packages/api-client/`)
- `apps/api/src/orcia_api/schemas/assistant.py` : ajout de `intermediate_output: str | None = None` sur `ThreeSpeedStepProgressSchemaItem`.
- `apps/api/src/orcia_api/routers/assistant_llm_bridge.py` :
  - Enrichissement de `LiveLlmTurnOutcome` avec `thinking_text: str | None = None`.
  - Extraction du champ `thinking` / `reasoning` lorsqu'il est fourni par Ollama ou un endpoint compatible OpenAI, ou synthèse d'un cadrage intermédiaire structuré.
  - Ajout de `stream_configured_llm_for_assistant_turn(...)` qui génère en temps réel les événements SSE (`thinking_delta`, `token_delta`, `turn_completed`).
- `apps/api/src/orcia_api/routers/assistant_workspace.py` : propagation de `intermediate_output` dans `execute_three_speed_turn_endpoint` et enrichissement de `stream_three_speed_turn_endpoint`.
- Régénération du SDK OpenAPI 3.1 via `.venv/bin/python scripts/export_openapi.py` (`0-diff`).

### 2.4 Design System `@orcia/ui` & Interface `apps/web`
- Création de `packages/ui/src/primitives/AssistantThinkingSubWindow.tsx` (`163 lignes`) :
  - Sous-fenêtre accordéon (`data-testid="assistant-thinking-subwindow"`, `data-expanded="true|false"`), bouton d'en-tête (`data-testid="assistant-thinking-subwindow-toggle"`), compteur temps réel en secondes (`0s` $\rightarrow$ `1s` $\rightarrow$ `2s`…) tant que `isGenerating === true` et durées figées par étape (`data-testid="assistant-step-live-timer-${stepCode}"`), et affichage de `intermediateOutput` (`data-testid="assistant-step-intermediate-output-${stepCode}"`).
  - Repli automatique dès que le texte principal arrive ou que la génération se termine, tout en restant ré-ouvrable au clic.
- Mise à jour de `packages/ui/src/primitives/AssistantSpeedSelectorAndStreamView.tsx` (`376 lignes`) :
  - Bouton unique à bascule Triangle (`▶`, `data-testid="assistant-send-play-icon"`) quand `!isGenerating` $\leftrightarrow$ Carré plein (`■`, `data-testid="assistant-stop-square-icon"`) actif (non `disabled`) quand `isGenerating === true`.
  - Au clic sur `■`, appel de `onStopGeneration?.()` et remise immédiate du focus dans `assistant-three-speed-input`.
  - Badge discret `⏹ Génération interrompue par l'utilisateur` (`data-testid="assistant-generation-stopped-badge"`) lorsque `generationStopped === true`.
- Création de `apps/web/src/features/inbox/useAssistantStreamingTurn.ts` (`318 lignes`) et intégration dans `apps/web/src/features/inbox/index.tsx` (`388 lignes`).

---

## 3. Bilan des Modifications & Résultats (Post-Implémentation)

### 3.1 Fichiers Développés & Modifiés
| Fichier | Nature | Description synthétique |
| :--- | :--- | :--- |
| `packages/ui/src/primitives/AssistantThinkingSubWindow.tsx` | Création (`163` lignes) | Sous-fenêtre accordéon de réflexion intermédiaire avec compteur temps réel en secondes (`0s` $\rightarrow$ `1s`…), ouverture auto au lancement, repli auto à l'arrivée de la réponse, et encadrés `intermediateOutput`. |
| `packages/ui/src/primitives/AssistantSpeedSelectorAndStreamView.tsx` | Modification (`376` lignes) | Bouton unique à bascule Triangle `▶` (`assistant-send-play-icon`) $\leftrightarrow$ Carré plein `■` (`assistant-stop-square-icon`, non `disabled`), intégration de `AssistantThinkingSubWindow`, badge `⏹ Génération interrompue par l'utilisateur` et reprise du focus dans le champ de saisie. |
| `packages/ui/src/index.ts` | Modification | Export public de `AssistantThinkingSubWindow`, `formatStepDurationSeconds` et `AssistantThinkingSubWindowProps`. |
| `apps/web/src/features/inbox/useAssistantStreamingTurn.ts` | Création (`318` lignes) | Hook dédié gérant `AbortController`, le timer temps réel des étapes en cours, le streaming progressif du texte de réponse et l'interruption immédiate (`stopGeneration`). |
| `apps/web/src/features/inbox/index.tsx` | Refactoring (`388` lignes) | Intégration de `useAssistantStreamingTurn` et câblage de `onStopGeneration` + `generationStopped` sur `AssistantSpeedSelectorAndStreamView`. |
| `packages/orcia-core/src/orcia_core/orchestration/assistant_three_speed_router.py` | Modification | Ajout de `intermediate_output` sur `ThreeSpeedStepProgressItem`, `llm_thinking_override` sur `execute_three_speed_turn` / `stream_three_speed_turn_sse`. |
| `apps/api/src/orcia_api/schemas/assistant.py` | Modification | Ajout de `intermediate_output: str \| None = None` sur `ThreeSpeedStepProgressSchemaItem`. |
| `apps/api/src/orcia_api/routers/assistant_llm_bridge.py` | Modification | Extraction de `thinking_text` sur `LiveLlmTurnOutcome` et ajout du générateur `stream_configured_llm_for_assistant_turn` (`thinking_delta`, `token_delta`, `turn_completed`). |
| `apps/api/src/orcia_api/routers/assistant_workspace.py` | Modification | Propagation de `intermediate_output` et émission des événements SSE `thinking_delta`, `token_delta` et `turn_completed`. |
| `packages/api-client/src/generated/schema.ts` | Régénération (`0-diff`) | Synchronisation OpenAPI 3.1 incluant `intermediate_output` sur `ThreeSpeedStepProgressSchemaItem`. |
| `packages/ui/src/__tests__/assistant-workspace.test.tsx` | Modification | Ajout du test unitaire `Story 10.2b` validant la bascule `▶` / `■`, la sous-fenêtre `assistant-thinking-subwindow`, le compteur en secondes, le repli auto et le badge d'interruption. |
| `apps/web/src/__tests__/zero-dead-buttons-and-silent-catches-audit.test.tsx` | Modification | Ajout de `onStopGeneration` aux callbacks obligatoires vérifiés sur `AssistantSpeedSelectorAndStreamView`. |
| `tests/unit/test_epic_10_story_10_2_three_speed_router.py` | Modification | Vérification de `intermediate_output` et des événements SSE `thinking_delta`, `token_delta`, `turn_completed`. |

### 3.2 Résultats Chiffrés, Métriques & Qualité
- **Tests TypeScript (`pnpm turbo run lint typecheck test`)** : `9/9 tasks successful` (`@orcia/ui`, `@orcia/api-client`, `@orcia/web` — `100 %` verts).
- **Tests Python (`pytest tests/unit/test_epic_10_story_10_2_three_speed_router.py`)** : `5 passed` (`100 %` verts).
- **Qualité statique & Architecture** :
  - `ruff check .` & `ruff format --check .` : `0 warning`, `535 files already formatted`
  - `mypy --strict packages/orcia-kernel packages/orcia-core apps/api apps/worker` : `Success: no issues found in 210 source files`
  - `lint-imports` : `5 contracts kept, 0 broken`
  - `scripts/export_openapi.py --check` : `0-diff`

### 3.3 Validation & Procédure de Test (5 Couches `AD-17` + 5 Garde-Fous de Câblage Vertical)
- **Couche 1 — Tests Unitaires (`pytest`, `Vitest`)** : Bascule `▶` $\leftrightarrow$ `■`, clic sur `■` déclenchant `onStopGeneration` et affichant `⏹ Génération interrompue par l'utilisateur`, sous-fenêtre `assistant-thinking-subwindow` ouverte pendant la réflexion puis repliée automatiquement quand le texte principal arrive, compteur temps réel en secondes (`Xs`) et encadrés `intermediateOutput`.
- **Couche 3 — Contrat OpenAPI (`0-diff`)** : `ThreeSpeedStepProgressSchemaItem.intermediate_output` synchronisé dans `packages/api-client/src/generated/schema.ts`.
- **Garde-Fou n°5 (`zero-dead-buttons-and-silent-catches-audit.test.tsx`)** : `onSendTurn` et `onStopGeneration` tous deux exigés et câblés sur `<AssistantSpeedSelectorAndStreamView />`, zéro `.catch(() => undefined)`.
