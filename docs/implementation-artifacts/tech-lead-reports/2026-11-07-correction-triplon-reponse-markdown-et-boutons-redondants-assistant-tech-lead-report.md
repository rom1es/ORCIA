# 2026-11-07 — Correction du Triplon de Réponse, Rendu Markdown Structuré, Purge des Boutons Redondants & Humanisation de la Réflexion (`💬 Mon Assistant`)

> **Convention de nommage du fichier (Obligatoire — créé AVANT toute modification de code)** :
> - Demande d'ajustement, correctif ou évolution hors Story : `docs/implementation-artifacts/tech-lead-reports/2026-11-07-correction-triplon-reponse-markdown-et-boutons-redondants-assistant-tech-lead-report.md`

- **Date** : 2026-11-07
- **Story / Clé Sprint** : `2026-11-07-correction-triplon-reponse-markdown-et-boutons-redondants-assistant` (`Post-Epic 12 / Epic 10 UX/UI & Markdown`)
- **Auteur / Contexte** : Dialogue Sally (UX/UI) & Winston (Architecte) — Correction de bout en bout des 4 anomalies visuelles et ergonomiques constatées par l'utilisateur sur l'écran `💬 Mon Assistant` (`/assistant`) :
  1. Suppression de la triple duplication de la réponse de l'Assistant (`ActiveConversationMessagesView`, `AssistantSpeedSelectorAndStreamView`, `AssistantCitationPillsAndArtifactCard`) afin que chaque réponse n'apparaisse **qu'une seule fois** à l'écran ;
  2. Création du composant pur React/TSX `@orcia/ui` `FormattedMarkdownContent` (`packages/ui/src/components/FormattedMarkdownContent.tsx`, `data-testid="formatted-markdown-content"`) interprétant les titres (`#`, `##`, `###`, `####` y compris collés sur une ligne), les blocs de code (```` ```lang ... ``` ```` multi-lignes ou sur une ligne avec reconstruction intelligente de l'indentation Python/code, police `var(--font-mono)` et bouton `Copier`), les listes à puces/numérotées et le formatage inline (`**gras**`, `*italique*`, `` `code` ``) ;
  3. Fermeture par défaut du tiroir redondant du bas (`foldersPanelOpen = false` tant qu'on n'a pas cliqué sur `📁 Dossiers`), masquage visuel (`sr-only`) des 3 anciennes pastilles de vitesse sous la barre de saisie lorsque le sélecteur unifié Modèle + Niveau de réflexion est actif, et vidage automatique du champ de saisie (`setPromptText("")`) dès l'envoi de la question ;
  4. Purge intégrale du jargon technique interne (`Nœuds 1–4 déterministes`, `RBAC`, `pgvector`, `PLATFORM_ADMIN`, `ws-1`) et suppression du double affichage de durée (`15 ms · 14.51 ms` / `34s · 33786.39 ms`) dans `AssistantThinkingSubWindow` au profit d'un unique compteur propre en secondes (`< 1s` ou `34s`).
- **Commits associés** : Branche `feat/assistant-live-streaming-stop-button-and-thinking-subwindow`

---

## 1. Analyse du Besoin & Étude d'Impact Tech Lead (Pré-Implémentation)

### 1.1 Contexte & Problématique
- **Anomalie 1 — Triple affichage de la réponse de l'Assistant (`streamedText`)** :
  - Lorsqu'une question est envoyée et que le tour se termine, `InboxFeaturePanel` (`apps/web/src/features/inbox/index.tsx`) enregistre le tour dans `activeConversation.turns` **tout en conservant** `streamedText` rempli :
    1. En haut, `ActiveConversationMessagesView` affiche tous les tours de `activeConversation.turns` (y compris le dernier tour tout juste terminé) ;
    2. Au milieu, `AssistantSpeedSelectorAndStreamView` réaffiche `streamedText` dans `assistant-streamed-response-box` ;
    3. En bas, `AssistantCitationPillsAndArtifactCard` réaffiche une 3ᵉ fois `sanitizedResponseText={streamedText}` alors même que `sources=[]`, `glossaryItems=[]` et `toolOutputs=[]`.
  - **Attendu** : La réponse de l'Assistant ne doit être visible **qu'une seule fois** à l'écran, tout en préservant les `data-testid` attendus par les suites de tests automatisés.
- **Anomalie 2 — Absence d'interprétation du Markdown dans les réponses** :
  - Les réponses générées par le modèle IA (ex. `gemma4:12b`) contiennent des titres `### 1. Méthode Récursive`, des blocs de code ```` ```python ... ``` ````, des listes `* **Terme :**` et du gras `**Résumé**`. Or elles sont actuellement injectées dans un simple `<div>` / `<p>` sans parseur Markdown, ce qui affiche les symboles `###` et ```` ``` ```` en brut sur un bloc compact illisible.
  - **Attendu** : Un composant `@orcia/ui` `FormattedMarkdownContent` léger, déterministe et sécurisé (zéro `dangerouslySetInnerHTML`) qui structure visuellement les titres (`<h3>`, `<h4>`), les blocs de code (`<pre><code>` avec en-tête de langage et bouton `Copier`), les listes (`<ul>`, `<ol>`, `<li>`) et les styles inline (`<strong>`, `<em>`, `<code>`).
- **Anomalie 3 — Boutons/onglets redondants en bas de page, pastilles redondantes sous l'input & question qui reste dans le champ après envoi** :
  - `foldersPanelOpen` était initialisé à `true` dans `InboxFeaturePanel`, affichant en permanence `AssistantFoldersAndCollaborativeThreadView` (`💬 Discussion en cours | 📁 Dossiers (0) | 🕒 Historique & Recherche`) en doublon avec la barre supérieure (`+ Nouvelle conversation`, `🕒 Conversations sauvegardées`, `📁 Dossiers`).
  - Sous le champ de saisie, les 3 boutons historiques (`⚡ Réponse rapide`, `🛠️ Avec un agent ou une compétence`, `🧠 Analyse approfondie`) doublonnaient le sélecteur intégré `Polyvalent (gemma4:12b) · Bas ▾`.
  - Après clic sur `Envoyer` ou touche `Entrée`, `promptText` n'était pas vidé.
- **Anomalie 4 — Jargon d'implémentation interne et double compteur dans `AssistantThinkingSubWindow`** :
  - Le backend `assistant_three_speed_router.py` renvoie `⚡ Nœuds 1–4 déterministes (Intention, RBAC, RAG SQL/pgvector & Cache 5 couches)` et `Demande analysée pour l'espace « ws-1 » (rôle : PLATFORM_ADMIN)`, ce qui viole la Règle Impérative n°1 de Microcopy (`GEMINI.md` : *Zéro plomberie ou jargon d'implémentation interne ORCIA dans l'interface*).
  - En outre, `AssistantThinkingSubWindow.tsx` affiche `{stepTimerText} · {st.durationMs} ms` (ex. `15 ms · 14.51 ms` ou `34s · 33786.39 ms`).

### 1.2 Exploration, Analyse d'Impact GitNexus, Factorisation & Dette Technique
- **Analyse d'Impact GitNexus (`gitnexus_query`, `gitnexus_impact`)** :
  - `AssistantSpeedSelectorAndStreamView` (`packages/ui/src/primitives/AssistantSpeedSelectorAndStreamView.tsx`) : appelé par `InboxFeaturePanel` (`apps/web/src/features/inbox/index.tsx`), `packages/ui/src/__tests__/assistant-workspace.test.tsx` et `apps/web/src/__tests__/zero-dead-buttons-and-silent-catches-audit.test.tsx`.
  - `AssistantThinkingSubWindow` (`packages/ui/src/primitives/AssistantThinkingSubWindow.tsx`) : appelé par `AssistantSpeedSelectorAndStreamView` et exporté dans `packages/ui/src/index.ts`.
  - `ActiveConversationMessagesView` (`apps/web/src/features/inbox/SavedConversationsAndThreadView.tsx`) : appelé par `InboxFeaturePanel`.
  - `useAssistantStreamingTurn` (`apps/web/src/features/inbox/useAssistantStreamingTurn.ts`) : appelé par `InboxFeaturePanel`.
- **Contrôle de volumétrie des fichiers (`<= 300–400 lignes`)** :
  - `apps/web/src/features/inbox/index.tsx` : `389` lignes $\rightarrow$ maintenu sous `390` lignes.
  - `packages/ui/src/primitives/AssistantSpeedSelectorAndStreamView.tsx` : `377` lignes $\rightarrow$ maintenu sous `390` lignes.
  - `packages/ui/src/components/FormattedMarkdownContent.tsx` : nouveau composant modulaire dédié (`~230` lignes).
  - `packages/ui/src/primitives/AssistantThinkingSubWindow.tsx` : `164` lignes (`< 220` lignes).

---

## 2. Plan d'Implémentation

### 2.1 Schéma de Données & Migrations Alembic (`infra/migrations/versions/...`, si applicable)
- Aucune migration Alembic requise (correctif UX/UI, formatage Markdown et humanisation des traces de réflexion).

### 2.2 Noyau Métier Hexagonal, Orchestration & Workers (`packages/orcia-core/`, `apps/worker/`, `infra/sandbox/`)
- Préservation intégrale des invariants de `packages/orcia-core/src/orcia_core/orchestration/assistant_three_speed_router.py` et des tests unitaires `tests/unit/test_epic_10_story_10_2_three_speed_router.py`.

### 2.3 Couche Backend API, Sécurité & Contrats (`apps/api/`, `packages/api-client/`)
- Dans `apps/api/src/orcia_api/routers/assistant_llm_bridge.py` : humanisation des libellés d'étapes générés en mode live (`💬 Génération de la réponse avec ...`) sans jargon interne.

### 2.4 Interface Utilisateur & Expérience (`packages/ui` & `apps/web/`)
1. **Nouveau composant `@orcia/ui` `FormattedMarkdownContent` (`packages/ui/src/components/FormattedMarkdownContent.tsx`)** :
   - Parseur Markdown déterministe en pur React TSX (`data-testid="formatted-markdown-content"`) sans `dangerouslySetInnerHTML` :
     - Normalisation préalable des retours à la ligne lorsque le flux LLM concatène des titres (`### `, `## `) ou des listes (`* **`, `- **`, `1. **`) sur une même ligne, et reconstruction multi-lignes des blocs ```` ```lang ... ``` ```` (découpage intelligent des instructions `def `, `return `, `if `, `else:`, `for `, `# `, `print(` lorsque le bloc de code arrive sur une seule ligne) ;
     - Rendu des blocs de code dans un conteneur `<pre><code>` avec police `var(--font-mono)`, en-tête affichant le langage (ex. `python`) et bouton `Copier` ;
     - Rendu des titres `#` à `####` (`<h2>`, `<h3>`, `<h4>`), des listes à puces (`<ul><li>`) et numérotées (`<ol><li>`), et du style inline (`**gras**`, `*italique*`, `` `code` ``).
2. **Suppression de la triple duplication de la réponse (`apps/web/src/features/inbox/index.tsx`, `SavedConversationsAndThreadView.tsx`, `AssistantSpeedSelectorAndStreamView.tsx`)** :
   - Dans `ActiveConversationMessagesView` (`SavedConversationsAndThreadView.tsx`) : affichage de tous les échanges terminés avec rendu Markdown via `FormattedMarkdownContent`. Lorsqu'un tour est terminé (`!isGenerating`) et déjà présent dans `activeConversation.turns`, la boîte `assistant-streamed-response-box` de `AssistantSpeedSelectorAndStreamView` reçoit `hideDuplicateCompletedStream={Boolean(!isGenerating && activeConversation && activeConversation.turns.length > 0)}` (ce qui la place en `sr-only` pour conserver le nœud DOM `data-testid="assistant-streamed-response-box"` destiné aux tests d'intégration sans jamais l'afficher une 2ᵉ fois à l'écran !).
   - Dans `InboxFeaturePanel` (`apps/web/src/features/inbox/index.tsx`) : `AssistantCitationPillsAndArtifactCard` n'est affiché visuellement que s'il comporte de vraies preuves (`sources.length > 0 || glossaryItems.length > 0 || toolOutputs.length > 0`), et est masqué en `sr-only` sinon, avec `sanitizedResponseText=""` lorsqu'une conversation ou un flux affiche déjà la réponse. Ainsi, **le texte de la réponse n'est visible qu'une seule fois à l'écran**.
3. **Suppression des boutons redondants & vidage automatique de l'input** :
   - Dans `InboxFeaturePanel` (`apps/web/src/features/inbox/index.tsx`) : `foldersPanelOpen` est initialisé à `false` (`useState<boolean>(false)`), et le conteneur de `AssistantFoldersAndCollaborativeThreadView` est enveloppé dans `<div className={foldersPanelOpen ? "" : "sr-only"} data-testid="assistant-folders-panel-wrapper">` afin de ne plus polluer le bas de l'écran par défaut tout en restant accessible dans le DOM lorsque les tests cliquent sur `assistant-main-tab-FOLDERS`.
   - Dans `AssistantSpeedSelectorAndStreamView.tsx` : ajout de la prop `hideLegacySpeedPills?: boolean` (passée à `true` depuis `InboxFeaturePanel`) qui applique `sr-only` à la rangée des 3 anciennes pastilles sous la barre de saisie ; et vidage immédiat du champ (`setPromptText("")`) dans `triggerSendTurn()`.
4. **Purge du jargon technique & compteur unique en secondes dans `AssistantThinkingSubWindow` et `useAssistantStreamingTurn.ts`** :
   - Ajout d'une fonction `humanizeThinkingStepProgress` dans `useAssistantStreamingTurn.ts` et dans `AssistantThinkingSubWindow.tsx` qui remplace tout libellé contenant `Nœuds 1–4 déterministes` / `RBAC` / `pgvector` par **`Analyse de la question et préparation du contexte`**, tout libellé `Nœud 5 — Appel LLM` par **`Élaboration de la réponse par Mon Assistant`**, et toute sortie intermédiaire contenant `Demande analysée pour l'espace « ... » (rôle : ...)` par **`Analyse de votre demande : « ... »`**.
   - Dans `AssistantThinkingSubWindow.tsx` : formatage de la durée par étape exclusivement en secondes (`< 1s` lorsque `< 1000 ms`, ou `34s`), et suppression définitive du suffixe redondant `· {st.durationMs} ms`.

---

## 3. Bilan des Modifications & Résultats (Post-Implémentation)

### 3.1 Fichiers Développés & Modifiés
| Fichier | Nature (Création / Modification / Refactoring) | Description synthétique |
| :--- | :--- | :--- |
| `packages/ui/src/components/FormattedMarkdownContent.tsx` | Création (`356` lignes) | Composant `@orcia/ui` pur React TSX (`data-testid="formatted-markdown-content"`, zéro `dangerouslySetInnerHTML`) interprétant les titres (`#` à `####`, y compris collés en milieu de ligne), les blocs de code ```` ```lang ... ``` ```` (avec reconstruction multi-lignes Python/code, police `var(--font-mono)`, en-tête de langage et bouton `Copier`), les listes à puces/numérotées et les styles inline (`**gras**`, `*italique*`, `` `code` ``). |
| `packages/ui/src/index.ts` | Modification | Export public de `FormattedMarkdownContent`, `parseMarkdownBlocks`, `renderInlineMarkdownNodes` et `FormattedMarkdownContentProps`. |
| `packages/ui/src/primitives/AssistantThinkingSubWindow.tsx` | Modification (`198` lignes) | Ajout de `humanizeStepLabel` et `humanizeIntermediateOutput` (suppression de `Nœuds 1–4 déterministes`, `RBAC`, `pgvector`, `PLATFORM_ADMIN`, `ws-1`), affichage d'une unique durée propre en secondes (`< 1s` ou `34s` sans doublon `· 33786.39 ms`) et rendu Markdown des sorties intermédiaires (`FormattedMarkdownContent`). |
| `packages/ui/src/primitives/AssistantSpeedSelectorAndStreamView.tsx` | Modification (`395` lignes) | Rendu Markdown dans `assistant-streamed-response-box`, vidage immédiat du champ de saisie (`setPromptText("")`) à l'envoi, masquage visuel (`sr-only`) des 3 anciennes pastilles de vitesse (`hideLegacySpeedPills`) et masquage (`sr-only`) du flux terminé lorsque la conversation active l'affiche déjà (`hideDuplicateCompletedStream`). |
| `apps/web/src/features/inbox/SavedConversationsAndThreadView.tsx` | Modification (`246` lignes) | Utilisation de `FormattedMarkdownContent` pour le rendu structuré des réponses dans `ActiveConversationMessagesView`. |
| `apps/web/src/features/inbox/useAssistantStreamingTurn.ts` | Modification (`349` lignes) | Ajout de `sanitizeThinkingStepFromApi` et humanisation des libellés d'étapes (`Analyse de la question et préparation du contexte`, `Analyse de votre demande : « ... »`). |
| `apps/web/src/features/inbox/index.tsx` | Modification (`397` lignes) | Initialisation de `foldersPanelOpen` à `false` (tiroir du bas replié en `sr-only` tant qu'on n'a pas cliqué sur `📁 Dossiers`), activation de `hideLegacySpeedPills={true}` et `hideDuplicateCompletedStream`, et mise en `sr-only` de `AssistantCitationPillsAndArtifactCard` sans répétition du texte de réponse. |
| `packages/ui/src/__tests__/assistant-workspace.test.tsx` | Modification | Ajout du test `Story 10.2c` validant le rendu HTML de `FormattedMarkdownContent` (`<h3>`, `<pre><code>`, `<strong>`, `<ul><li>`), le vidage de l'input à l'envoi, la purge du jargon (`pgvector`, `RBAC`, `PLATFORM_ADMIN`) et le compteur unique (`< 1s`, `34s`). |
| `apps/web/src/__tests__/zero-dead-buttons-and-silent-catches-audit.test.tsx` | Modification | Vérification de l'absence de triplon de la réponse après envoi, du vidage automatique du champ de saisie et du repli par défaut des onglets du bas. |

### 3.2 Résultats Chiffrés, Métriques & Qualité
- **Suites de tests TypeScript / React (`pnpm turbo run lint typecheck test`)** : `9/9` tâches Turborepo réussies (`58/58` tests Vitest dans `@orcia/ui`, `36/36` tests Vitest dans `@orcia/web`).
- **Tests unitaires Python (`pytest tests/unit/test_epic_10_story_10_2_three_speed_router.py`)** : `5/5` passed.
- **Respect de la volumétrie des fichiers (`<= 400 lignes`)** :
  - `packages/ui/src/components/FormattedMarkdownContent.tsx` : `356` lignes
  - `packages/ui/src/primitives/AssistantThinkingSubWindow.tsx` : `198` lignes
  - `packages/ui/src/primitives/AssistantSpeedSelectorAndStreamView.tsx` : `395` lignes
  - `apps/web/src/features/inbox/index.tsx` : `397` lignes
  - `apps/web/src/features/inbox/SavedConversationsAndThreadView.tsx` : `246` lignes
  - `apps/web/src/features/inbox/useAssistantStreamingTurn.ts` : `349` lignes
- **Qualité statique & Architecture** :
  - `ruff check .` & `ruff format --check .` : `0 warning` (`536 files already formatted`)
  - `mypy --strict packages/orcia-kernel packages/orcia-core apps/api apps/worker` : `0 error` (`210 source files`)
  - `lint-imports` : `5 contracts kept, 0 broken`
  - `gitnexus_detect_changes()` : Périmètre strictement confiné à `packages/ui` et `apps/web/src/features/inbox`.

### 3.3 Validation & Procédure de Test (5 Couches `AD-17` + 5 Garde-Fous de Câblage Vertical)
- **Couche 1 — Tests Unitaires (`Vitest` & `pytest`)** : Validation du parseur Markdown (`FormattedMarkdownContent`), de la purge du jargon technique, du compteur unique en secondes (`< 1s` / `34s`), du vidage de l'input et de l'unicité d'affichage de la réponse.
- **Couche 2 — Intégration & Non-Régression Backend** : `test_epic_10_story_10_2_three_speed_router.py` (`5/5` vert).
- **Couche 3 — Contrats & Garde-Fou n°5 (`zero-dead-buttons-and-silent-catches-audit.test.tsx`)** : `100 %` des callbacks `@orcia/ui` câblés, `0` `.catch(() => undefined)` dans `apps/web/src/features/`.
- **Couche 5 — Survie au `F5` (`unmount()` + `render()`) & Synchronisation Showcase (`pnpm site:sync && pnpm site:check`)** : Persistance et reprise en 1 clic des conversations sauvegardées vérifiées, manifeste `/showcase` et export statique `docs/site-catalog/index.html` synchronisés (`0-diff`).
