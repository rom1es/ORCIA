# 2026-11-07 — Mon Assistant : Icônes d'Actions Seules, Sources Réelles Uniquement, Nettoyage des Préfixes/Tags, Réflexion Minimaliste (`›`), Pièces Jointes Intégrées & Déduplication des Modèles IA

> **Convention de nommage du fichier (Obligatoire — à créer AVANT toute modification de code)** :
> - Demande d'ajustement, correctif ou évolution hors Story : `docs/implementation-artifacts/tech-lead-reports/{YYYY-MM-DD}-{descriptif-court}-tech-lead-report.md`

- **Date** : 2026-11-07
- **Story / Clé Sprint** : `2026-11-07-assistant-icones-seules-sources-reelles-reflexion-minimaliste-et-pieces-jointes` (`Epic 10` / `Epic 12` — Ajustement UX/UI `💬 Mon Assistant`)
- **Auteur / Contexte** : Raffinement UX/UI et fonctionnel complet de l'écran `💬 Mon Assistant` (`/assistant`) suite aux retours visuels de l'utilisateur :
  1. Barre d'actions sous la réponse réduite aux **seules icônes** (`👍`, `👎`, `📋`/`✓`, `🔄`, `📄`/`✓`, `☍`) avec `title` et `aria-label` accessibles + nouvel icône `⋯` (`assistant-action-details-btn`) ouvrant le popover des détails de la réponse (`Modèle : ... · Niveau de réflexion : ...`).
  2. Suppression du repli factice sur `DEFAULT_ORCIA_DOCUMENT_OPTIONS` dans `ragCitations` : `Sources consultées :` ne s'affiche **que** si une source a réellement été jointe (`attachedFiles`) ou mobilisée (`filterUsedRagSourcesForTurn`).
  3. Nettoyage systématique (`sanitizeAssistantDisplayReply`) des préfixes techniques `[⚡ Vitesse 1 · Casquette PLATFORM_ADMIN]`, des mentions de cache Redis de repli et des marqueurs de fin ` [S1] [G1].` / `[S1] [O1]`.
  4. Affichage **ultra-minimaliste** des étapes de réflexion (`AssistantThinkingSubWindow`) inspiré de `Worked for Xs ›` : simple ligne sans cadre ni fond (`Réflexion en cours · Xs ›` / `Réflexion pendant Xs ›`) et liste verticale sobre à bordure latérale fine lorsqu'elle est dépliée.
  5. Intégration directe des pastilles de fichiers joints (`assistant-attached-files-bar`) **à l'intérieur** de la barre de saisie arrondie, bouton `×` épuré sans bordure, **vidage immédiat** (`setAttachedFiles([])`) à l'envoi, affichage des pièces jointes soumises sous la bulle bleue de la question utilisateur, suppression de la ligne superflue `"🧑 Vous"` / modèle au-dessus de la bulle de question, et bouton d'envoi/arrêt rond réduit à la seule icône (`▶` / `■`).
  6. Positionnement aéré de l'indicateur slider de recherche (`AssistantThinkingSliderIndicator` épuré sans cadre lourd + `AssistantThinkingSubWindow`) au milieu de la zone de réponse entre la bulle de question en haut à droite et la barre de saisie en bas, et déduplication des modèles IA dans `buildAssistantModelOptions` lorsqu'un seul modèle est configuré.
- **Commits associés** : `feat(assistant): icon-only actions, real RAG sources only, minimalist thinking & inline attachments`

---

## 1. Analyse du Besoin & Étude d'Impact Tech Lead (Pré-Implémentation)

### 1.1 Contexte & Problématique
- **Problème 1 (Barre d'actions verbeuse & détails du modèle mal placés)** : Les boutons d'action sous la réponse affichaient à la fois l'icône et le texte complet (`👍 J'aime`, `👎 Je n'aime pas`, `📋 Copier`, `🔄 Régénérer`, `📄 Enregistrer en brouillon`, `☍ Poursuivre dans un Processus`), tandis que `"Polyvalent (gemma4:12b) · Réflexion Basse 🧑 Vous"` encombrait le dessus de la bulle de question. L'utilisateur souhaite uniquement les icônes en pied de réponse, zéro mention `"🧑 Vous"` au-dessus de sa question, et un icône `⋯` en fin de barre d'actions pour consulter le modèle et le niveau de réflexion utilisés.
- **Problème 2 (Sources consultées factices sur questions générales)** : `buildAssistantAutocompleteAndRagOptions` repliait systématiquement `ragCitations` sur `DEFAULT_ORCIA_DOCUMENT_OPTIONS` même lorsqu'aucune source n'était connectée ni utilisée (ex. question `code la fonction factorielle en python`).
- **Problème 3 (Fuites de préfixes et marqueurs internes)** : Des préfixes `[⚡ Vitesse 1 · Casquette PLATFORM_ADMIN]` et des suffixes `» [S1] [G1].` apparaissaient dans le texte affiché à l'utilisateur, en violation de la Règle 3.1 (`Zéro plomberie ou jargon d'implémentation interne ORCIA dans l'interface`).
- **Problème 4 (Sous-fenêtre de réflexion trop massive)** : `AssistantThinkingSubWindow` entourait l'en-tête et chaque étape de cadres gris bordés, alors que la référence UX attendue est une ligne ultra-minimaliste `Réflexion pendant Xs ›`.
- **Problème 5 (Pièce jointe hors de la barre de saisie, non vidée à l'envoi & bouton Envoyer verbeux)** : `assistant-attached-files-bar` était rendu au-dessus de la barre de saisie et `attachedFiles` n'était pas vidé dans `triggerSendTurn()`. De plus, le bouton d'envoi affichait `"▶ Envoyer à Mon Assistant"` au lieu d'un bouton rond compact contenant uniquement l'icône `▶` ou `■`.
- **Problème 6 (Positionnement du slider de recherche & triplon de modèle IA)** : Pendant `isGenerating && !streamedText`, l'indicateur de recherche et la ligne de réflexion doivent occuper un espace de réponse aéré entre la bulle utilisateur et la barre de saisie. Par ailleurs, lorsqu'un seul modèle IA (`gemma4:12b`) est configuré dans `llmTiers`, le sélecteur ne doit pas afficher 3 faux choix pointant vers ce même modèle.

### 1.2 Exploration, Analyse d'Impact GitNexus, Factorisation & Dette Technique
- **Analyse d'Impact (`packages/ui` & `apps/web`)** :
  - `packages/ui/src/primitives/AssistantResponseFooterActionsAndCitations.tsx` (379 lignes `< 400`) : `sanitizeAssistantDisplayReply`, `AssistantUserQuestionBubble` épurée sans en-tête `"🧑 Vous"`, `AssistantThinkingSliderIndicator` sans boîte encadrée, `AssistantResponseFooterActionsAndCitations` avec boutons icônes seuls + bouton `⋯` (`assistant-action-details-btn`) et popover `assistant-response-details-popover`.
  - `packages/ui/src/primitives/AssistantThinkingSubWindow.tsx` (206 lignes `< 400`) : ligne ultra-minimaliste `Réflexion en cours · Xs ›` / `Réflexion pendant Xs ›` et liste verticale `pl-3 border-l`.
  - `packages/ui/src/primitives/AssistantPromptPlusAndAutocomplete.tsx` (310 lignes `< 400`) : composant `AssistantAttachedFilesInlineBar` intégré dans la barre de saisie avec bouton `×` sans bordure.
  - `packages/ui/src/primitives/AssistantModelAndEffortPopover.tsx` (271 lignes `< 400`) : prise en charge de `hiddenDuplicate` pour n'afficher que les modèles réellement distincts.
  - `packages/ui/src/primitives/AssistantSpeedSelectorAndStreamView.tsx` (398 lignes `< 400`) : vidage de `attachedFiles` à l'envoi (`lastSubmittedFiles`), bouton rond icône seule `▶` / `■`, zone de recherche centrale aérée (`assistant-active-research-zone`).
  - `apps/web/src/features/inbox/savedConversationsStore.ts` (396 lignes `< 400`) : `ragCitations: []` par défaut sans repli factice, `filterUsedRagSourcesForTurn`, déduplication des modèles dans `buildAssistantModelOptions`, persistance de `attachedFiles` et `usedSources` par tour.

---

## 2. Plan d'Implémentation

### 2.1 Schéma de Données & Migrations Alembic (`infra/migrations/versions/...`, si applicable)
- Aucune migration Alembic requise.

### 2.2 Noyau Métier Hexagonal, Orchestration & Workers (`packages/orcia-core/`, `apps/worker/`, `infra/sandbox/`)
- Aucun impact sur `packages/orcia-core` : les tests unitaires Python (`test_epic_10_story_10_2_three_speed_router.py`, `test_epic_10_story_10_3_citations_and_v5_guard.py`) restent 100 % intacts.

### 2.3 Couche Backend API, Sécurité & Contrats (`apps/api/`, `packages/api-client/`)
- Aucun changement de contrat OpenAPI (`0-diff` préservé).

### 2.4 Interface Utilisateur & Expérience (`packages/ui/` & `apps/web/`)
- Implémentation complète dans `packages/ui/src/primitives/` et `apps/web/src/features/inbox/` en respectant la limite stricte de `< 400` lignes par fichier et les 11 règles fondamentales UX/UI.

---

## 3. Bilan des Modifications & Résultats (Post-Implémentation)

### 3.1 Fichiers Développés & Modifiés
| Fichier | Nature | Description synthétique |
| :--- | :--- | :--- |
| `packages/ui/src/primitives/AssistantResponseFooterActionsAndCitations.tsx` | Modification (`379` lignes) | Boutons d'actions icônes seuls (`👍`, `👎`, `📋`/`✓`, `🔄`, `📄`/`✓`, `☍`), bouton `⋯` (`assistant-action-details-btn`) + popover `assistant-response-details-popover` (`Modèle : ... · Niveau de réflexion : ...`), suppression de `"🧑 Vous"` au-dessus de `AssistantUserQuestionBubble`, affichage des pièces jointes sous la bulle bleue, `AssistantThinkingSliderIndicator` épuré et `sanitizeAssistantDisplayReply`. |
| `packages/ui/src/primitives/AssistantThinkingSubWindow.tsx` | Modification (`206` lignes) | Affichage ultra-minimaliste sans boîte ni bordure (`Réflexion en cours · Xs ›` / `Réflexion pendant Xs ›`) et liste verticale sobre (`pl-3 border-l`). |
| `packages/ui/src/primitives/AssistantPromptPlusAndAutocomplete.tsx` | Modification (`310` lignes) | Extraction de `AssistantAttachedFilesInlineBar` intégré à l'intérieur de la barre de saisie avec bouton `×` sans bordure. |
| `packages/ui/src/primitives/AssistantModelAndEffortPopover.tsx` | Modification (`271` lignes) | Masquage des paliers dupliqués (`hiddenDuplicate`) lorsqu'un seul modèle IA est configuré. |
| `packages/ui/src/primitives/AssistantSpeedSelectorAndStreamView.tsx` | Modification (`398` lignes) | Intégration de `AssistantAttachedFilesInlineBar` dans le conteneur de saisie, vidage immédiat de `attachedFiles` à l'envoi, zone de recherche centrale aérée (`assistant-active-research-zone`), et bouton d'envoi/arrêt rond à icône seule (`▶` / `■`). |
| `packages/ui/src/index.ts` | Modification | Export de `sanitizeAssistantDisplayReply` et `AssistantAttachedFilesInlineBar`. |
| `packages/ui/src/__tests__/assistant-workspace.test.tsx` | Modification | Mise à jour et enrichissement des assertions (`Story 10.2d` : icônes seules, bouton `⋯` détails, ajout et vidage immédiat de document ORCIA à l'envoi). |
| `apps/web/src/features/inbox/savedConversationsStore.ts` | Modification (`396` lignes) | Suppression du repli factice sur `DEFAULT_ORCIA_DOCUMENT_OPTIONS` dans `ragCitations`, ajout de `filterUsedRagSourcesForTurn`, déduplication des modèles dans `buildAssistantModelOptions`, et sauvegarde de `attachedFiles` / `usedSources` par tour. |
| `apps/web/src/features/inbox/useAssistantStreamingTurn.ts` | Modification (`361` lignes) | Nettoyage systématique via `sanitizeAssistantDisplayReply` et propagation de `attachedFiles`. |
| `apps/web/src/features/inbox/SavedConversationsAndThreadView.tsx` | Modification (`278` lignes) | Affichage des sources réellement utilisées par tour (`turn.usedSources`), des pièces jointes (`turn.attachedFiles`) et transmission de `modelLabel` / `effortLabel` au pied de réponse. |
| `apps/web/src/features/inbox/index.tsx` | Modification (`351` lignes) | Calcul de `usedSources` via `filterUsedRagSourcesForTurn` à la fin de chaque tour. |

### 3.2 Résultats Chiffrés, Métriques & Qualité
- **Tests TypeScript (`pnpm turbo run lint typecheck test`)** : `9/9 tasks successful` (`packages/ui` et `apps/web` `37/37` tests Vitest passés).
- **Qualité statique & Architecture Python** :
  - `.venv/bin/ruff check .` & `.venv/bin/ruff format --check .` : `All checks passed! (541 files already formatted)`
  - `.venv/bin/lint-imports` : `5 contracts kept, 0 broken`
  - `lint_spine.py` : `ok: true, 0 findings`
  - Volumétrie des fichiers : 100 % des fichiers modifiés sont strictement `< 400 lignes`.

### 3.3 Validation & Procédure de Test (5 Couches `AD-17` + 5 Garde-Fous de Câblage Vertical)
- **Couche 1 — Tests Unitaires (`Vitest` `@orcia/ui` & `apps/web`)** : Validation des boutons d'actions icônes seuls, du popover de détails `⋯`, de l'absence de sources factices par défaut, du nettoyage des préfixes/tags internes, de l'affichage minimaliste `Réflexion pendant Xs ›` et du vidage immédiat des pièces jointes à l'envoi.
- **Garde-Fou n°5 (`zero-dead-buttons-and-silent-catches-audit.test.tsx`)** : `PASS` (tous les callbacks et sélecteurs de modèles/réflexion fonctionnent et survivent au rechargement `F5`).
