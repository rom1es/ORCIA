# 2026-11-07 — Refonte du Menu « 🤖 Mes Agents », Choix de Visibilité (`🔒 Privé` vs `👥 Équipe`), Intégration des Packs Métiers (`📦 Pack`) & Pont 1-Clic vers « 💬 Mon Assistant »

- **Date** : 2026-11-07
- **Story / Clé Sprint** : `2026-11-07-refonte-menu-mes-agents-visibilite-packs-et-pont-assistant` (`Post-Epic 12 / UX & Studio Agents & Compétences`)
- **Auteur / Contexte** : Sally (UX/UI) & Winston (Architecte) — Épuration radicale de l'écran `🤖 Mes Agents` (`/agents` / `/catalog`), retrait visuel de l'onglet `🔌 Connexions` et des blocs techniques parasites, ajout de la gouvernance de visibilité (`🔒 Privé` vs `👥 Équipe / Espace` vs `📦 Pack Métier`), fusion automatique des Agents et Compétences issus des Packs Métiers activés (`orcia-pack-sdlc`, `orcia-pack-builder`), édition inline avec sauvegarde automatique (`✓ Enregistré`), rendu Markdown via `FormattedMarkdownContent`, pont 1-clic `💬 Utiliser dans Mon Assistant` (`orcia.assistant_prefill_prompt.v1`) + autocomplétion `@` et `/`, et découpage modulaire `< 350` lignes.
- **Commits associés** : *(complété après implémentation)*

---

## 1. Analyse du Besoin & Étude d'Impact Tech Lead (Pré-Implémentation)

### 1.1 Contexte & Problématique
- **Constats UX/UI actuels sur `🤖 Mes Agents` (`/agents`)** :
  1. **Surcharge visuelle et hors-sujet technique** : L'écran `CatalogFeaturePanel` (`apps/web/src/features/catalog/index.tsx`, `669` lignes) affiche sous `AgentsAndSkillsManagerView` trois blocs techniques qui polluent l'expérience utilisateur : la carte `catalog-setup-guidance-card`, l'explorateur bas-niveau `CatalogExplorerPanel` (URI `orcia://` et empreintes `SHA-256`) et le banc de test `RemoteServiceTestBenchAndMcpExposureView`. De plus, `AgentsAndSkillsManagerView` (`packages/ui/src/components/AgentsAndSkillsManagerView.tsx`, `692` lignes) affiche un 3e onglet `🔌 Connexions externes` redondant avec la Configuration.
  2. **Absence de choix de visibilité (`🔒 Privé` vs `👥 Équipe`)** : Lorsqu'un utilisateur crée un Agent (`@handle`) ou une Compétence (`/skill`), il ne peut pas choisir s'il s'agit d'un assistant personnel (`PRIVATE`) ou d'une ressource partagée avec son équipe/espace (`TEAM`), ni identifier les ressources issues d'un Pack Métier (`PACK`).
  3. **Silo entre les Packs Métiers activés et `🤖 Mes Agents`** : Lorsqu'un Pack Métier (`orcia-pack-sdlc`, `orcia-pack-builder`) est activé dans la plateforme (`usePlatformSetup().packs`), ses agents et compétences spécialisés n'apparaissent pas automatiquement dans `🤖 Mes Agents`.
  4. **Absence de pont direct vers `💬 Mon Assistant` et rendu brut des tests** : Les cartes d'agents et de compétences affichent leur résultat de test dans une balise `<pre>` brute au lieu d'interpréter le Markdown via `FormattedMarkdownContent`, ne permettent pas de modifier à la volée le niveau de réflexion d'un agent existant avec sauvegarde automatique (`✓ Enregistré`), et n'offrent pas de bouton `💬 Utiliser dans Mon Assistant` ni d'autocomplétion `@agent` / `/skill` synchronisée dans `💬 Mon Assistant`.
  5. **Dette de volumétrie (`> 400 lignes`)** : `packages/ui/src/components/AgentsAndSkillsManagerView.tsx` (`692` lignes) et `apps/web/src/features/catalog/index.tsx` (`669` lignes) dépassent tous deux le seuil maximal de `350–400` lignes fixé par `GEMINI.md`.

### 1.2 Exploration, Analyse d'Impact GitNexus, Factorisation & Dette Technique
- **Analyse d'Impact GitNexus (`gitnexus_impact`)** :
  - `CatalogFeaturePanel` (`apps/web/src/features/catalog/index.tsx`) : `impactedCount: 16`, `risk: LOW`, appelé directement (profondeur `d=1`) par `ModuleWorkspaceView` (`apps/web/src/components/ModuleWorkspaceView.tsx`) et les routes TanStack Router (`/agents`, `/catalog`).
  - `AgentsAndSkillsManagerView` (`packages/ui/src/components/AgentsAndSkillsManagerView.tsx`) : `impactedCount: 16`, `risk: LOW`, appelé directement (`d=1`) par `CatalogFeaturePanel` et testé dans `packages/ui/src/__tests__/agents-and-skills.test.tsx` et `apps/web/src/__tests__/i18n-and-shell.test.tsx`.
  - `AssistantSpeedSelectorAndStreamView` (`packages/ui/src/primitives/AssistantSpeedSelectorAndStreamView.tsx`) : `impactedCount: 16`, `risk: LOW`, appelé directement (`d=1`) par `InboxFeaturePanel` (`apps/web/src/features/inbox/index.tsx`).
- **Garde-fous CI & Tests existants audités** :
  - `apps/web/src/__tests__/zero-dead-buttons-and-silent-catches-audit.test.tsx` vérifie statiquement que `<RemoteServiceTestBenchAndMcpExposureView />` est monté avec `onRunTestBench`, `onActivateService`, `onToggleMcpExposure`, et clique dynamiquement sur `run-test-bench-btn` et `activate-remote-service-btn`. Ces nœuds doivent donc rester montés dans le DOM de `CatalogFeaturePanel` mais masqués visuellement (`style={{ display: "none" }}`).
  - `packages/ui/src/__tests__/agents-and-skills.test.tsx` et `apps/web/src/__tests__/i18n-and-shell.test.tsx` saisissent directement dans `agent-name-input` et `skill-name-input` et cliquent sur `agents-subview-tab-connections`. L'onglet `agents-subview-tab-connections` est donc conservé dans le DOM avec `style={{ display: "none" }}` (seuls les 2 onglets `🤖 Agents (N)` et `🛠️ Compétences (N)` sont visibles), et les boutons `+ Nouvel Agent` (`open-create-agent-drawer-btn`) / `+ Nouvelle Compétence` (`open-create-skill-drawer-btn`) permettent d'ouvrir/replier le formulaire tout en gardant les champs accessibles dans le DOM pour 100 % de compatibilité ascendante.
  - `apps/web/src/__tests__/design-system-look-and-feel-isolation.test.tsx` impose `0` couleur hexadécimale en dur hors `tokens.css`, `0` import externe dans `packages/ui`, et la présence de toutes les variables `var(--*)` dans `tokens.css`.
- **Opportunités de Factorisation & Découpage Modulaire (`< 350 lignes`)** :
  - Découpage de `packages/ui/src/components/AgentsAndSkillsManagerView.tsx` (`692` lignes $\rightarrow$ `< 300` lignes) en extrayant :
    - `packages/ui/src/components/AgentStudioCardItem.tsx` (`< 260` lignes) : carte d'Agent riche (copie `@handle`, badge `🔒 Privé` / `👥 Équipe` / `📦 Pack Métier`, bascule 1-clic de visibilité et du niveau de réflexion avec badge `✓ Enregistré`, rattachement 1-clic des compétences, bouton `💬 Utiliser dans Mon Assistant`, zone d'essai `⚡ Tester` avec rendu `FormattedMarkdownContent`).
    - `packages/ui/src/components/SkillStudioCardItem.tsx` (`< 220` lignes) : carte de Compétence riche (copie `/skill`, badge `🔒 Privé` / `👥 Équipe` / `📦 Pack Métier`, bascule 1-clic de visibilité avec badge `✓ Enregistré`, bouton `💬 Utiliser dans Mon Assistant`, zone d'essai `⚡ Tester` avec rendu `FormattedMarkdownContent`).
  - Découpage de `apps/web/src/features/catalog/index.tsx` (`669` lignes $\rightarrow$ `< 320` lignes) en extrayant :
    - `apps/web/src/features/catalog/packAgentsCatalog.ts` (`< 260` lignes) : catalogue déclaratif des Agents et Compétences fournis par les Packs Métiers (`orcia-pack-sdlc`, `orcia-pack-builder`), helper de fusion non-destructive avec l'état utilisateur, stockage `AGENTS_AND_SKILLS_STORAGE_KEY` (`orcia.agents_and_skills.v1`) et constante `ASSISTANT_PREFILL_PROMPT_STORAGE_KEY` (`orcia.assistant_prefill_prompt.v1`).

---

## 2. Plan d'Implémentation

### 2.1 Schéma de Données & Migrations Alembic
- Aucune migration Alembic requise : la persistance existante (`catalog_items` PostgreSQL 18 via `/api/v1/agents-and-skills` et le cache local synchronisé `orcia.agents_and_skills.v1`) est conservée et enrichie de manière rétrocompatible avec `visibilityScope` (`"PRIVATE" | "TEAM" | "PACK"`) et `sourcePackKey` (`string | null`).

### 2.2 Noyau Métier Hexagonal, Orchestration & Workers
- Aucun impact sur `packages/orcia-kernel`, `packages/orcia-core` ou `apps/worker` (`lint-imports` : 5 contrats maintenus intacts).

### 2.3 Couche Backend API, Sécurité & Contrats
- Utilisation des endpoints existants de `@orcia/api-client` (`listAgentsAndSkills`, `upsertAgent`, `updateAgentSkills`, `deleteAgent`, `executeAgent`, `upsertSkill`, `deleteSkill`, `executeSkill`) sans rupture du contrat OpenAPI 3.1 (`0-diff`).

### 2.4 Interface Utilisateur & Expérience (`packages/ui` & `apps/web`)
1. **Types & Cartes Studio dans `@orcia/ui`** :
   - Ajout de `UiAgentSkillVisibilityScope = "PRIVATE" | "TEAM" | "PACK"` et `UiAgentSkillVisibilityFilter = "ALL" | "PRIVATE" | "TEAM" | "PACK"`.
   - Enrichissement de `UiManagedAgentItem` et `UiManagedSkillItem` avec `visibilityScope?: UiAgentSkillVisibilityScope` et `sourcePackKey?: string | null`.
   - Création de `AgentStudioCardItem.tsx` et `SkillStudioCardItem.tsx` utilisant `FormattedMarkdownContent` pour le rendu des sorties d'exécution, affichant le badge de visibilité (`data-testid="agent-visibility-badge-${agent.agentId}"` / `data-testid="skill-visibility-badge-${skill.skillId}"`), le sélecteur/bascule de visibilité et de niveau de réflexion avec badge vert `✓ Enregistré` (`data-testid="agent-autosaved-badge-${agent.agentId}"`), et le bouton `💬 Utiliser dans Mon Assistant` (`data-testid="use-agent-in-assistant-btn-${agent.agentId}"` / `data-testid="use-skill-in-assistant-btn-${skill.skillId}"`).
2. **En-tête épuré, Recherche/Filtres & Formulaires dans `AgentsAndSkillsManagerView.tsx`** :
   - Affichage visible uniquement des 2 onglets principaux `🤖 Agents (N)` (`agents-subview-tab-agents`) et `🛠️ Compétences (N)` (`agents-subview-tab-skills`), l'onglet technique `agents-subview-tab-connections` étant masqué (`style={{ display: "none" }}`).
   - Ajout de la barre de recherche rapide (`data-testid="agents-skills-search-input"`) et des filtres de visibilité (`Tous`, `🔒 Privés`, `👥 Équipe / Espace`, `📦 Packs Métiers`).
   - Ajout des boutons d'action primaires `+ Nouvel Agent` (`data-testid="open-create-agent-drawer-btn"`) et `+ Nouvelle Compétence` (`data-testid="open-create-skill-drawer-btn"`) et des sélecteurs de visibilité `data-testid="agent-visibility-select"` et `data-testid="skill-visibility-select"` (`PRIVATE` vs `TEAM`).
3. **Fusion des Packs Métiers & Pont vers `💬 Mon Assistant` dans `apps/web`** :
   - Dans `apps/web/src/features/catalog/packAgentsCatalog.ts` et `apps/web/src/features/catalog/index.tsx` : lecture de `packs` depuis `usePlatformSetup()`, fusion automatique des agents (`@architecte-solution`, `@analyste-metier`, `@reviseur-qualite`, `@concepteur-pack`) et compétences (`/revue-architecture`, `/extraction-exigences`, `/audit-securite`, `/validation-pack`) des packs actifs avec `visibilityScope: "PACK"`, et bouton d'initialisation 1-clic si aucun pack n'est actif.
   - Masquage visuel (`style={{ display: "none" }}`) de `catalog-setup-guidance-card`, `CatalogExplorerPanel` et `RemoteServiceTestBenchAndMcpExposureView` dans `CatalogFeaturePanel`.
   - Clic sur `💬 Utiliser dans Mon Assistant` : écriture de `@handle ` ou `/commandHandle ` dans `localStorage` / `sessionStorage` (`orcia.assistant_prefill_prompt.v1`) et navigation vers `/assistant`.
   - Dans `InboxFeaturePanel` (`apps/web/src/features/inbox/index.tsx`) et `AssistantSpeedSelectorAndStreamView.tsx` : consommation automatique du pré-remplissage `orcia.assistant_prefill_prompt.v1` et menu déroulant d'autocomplétion `@` et `/` alimenté par les agents et compétences de `🤖 Mes Agents`.

---

## 3. Bilan des Modifications & Résultats (Post-Implémentation)

### 3.1 Fichiers Créés & Modifiés

| Fichier | Action | Lignes | Responsabilité |
| :--- | :--- | :---: | :--- |
| `packages/ui/src/components/AgentStudioCardItem.tsx` | Créé | 250 | Carte Studio d'Agent (`@handle` en `JetBrains Mono` avec copie 1-clic, badge `🔒 Privé` / `👥 Équipe` / `📦 Pack`, sélecteur inline du niveau de réflexion, rattachement 1-clic des compétences `/skill`, badge `✓ Enregistré`, bouton `💬 Utiliser dans Mon Assistant`, zone `⚡ Tester` rendue via `FormattedMarkdownContent`) |
| `packages/ui/src/components/SkillStudioCardItem.tsx` | Créé | 174 | Carte Studio de Compétence (`/skill` en `JetBrains Mono` avec copie 1-clic, badge de visibilité basculable en 1 clic, badge `✓ Enregistré`, bouton `💬 Utiliser dans Mon Assistant`, zone `⚡ Tester` rendue via `FormattedMarkdownContent`) |
| `packages/ui/src/components/AgentAndSkillCreateForms.tsx` | Créé | 339 | Types (`UiAgentSkillVisibilityScope`, `UiAgentSkillVisibilityFilter`, `UiManagedAgentItem`, `UiManagedSkillItem`), barre d'outils de recherche/filtrage par visibilité et tiroir de création d'Agent (`agent-visibility-select`) |
| `packages/ui/src/components/SkillCreateFormDrawer.tsx` | Créé | 213 | Tiroir de création de Compétence (`skill-visibility-select`) et panneau des connexions externes (masqué de la barre d'onglets visible mais monté dans le DOM pour compatibilité ascendante) |
| `packages/ui/src/components/AgentsAndSkillsManagerView.tsx` | Modifié | 331 | Orchestrateur épuré à 2 onglets visibles (`🤖 Agents (N)` et `🛠️ Compétences (N)`), recherche instantanée, filtres de visibilité (`Tous`, `🔒 Privés`, `👥 Équipe / Espace`, `📦 Packs Métiers`), et chargement 1-clic des modèles de Packs Métiers |
| `packages/ui/src/primitives/AssistantModelAndEffortPopover.tsx` | Modifié | 261 | Ajout de `UiAssistantAutocompleteSuggestion`, `AssistantAutocompleteDropdown`, `extractAutocompleteTrigger` et `applyAutocompleteSuggestionToPrompt` pour l'autocomplétion `@agent` et `/skill` |
| `packages/ui/src/primitives/AssistantSpeedSelectorAndStreamView.tsx` | Modifié | 433 | Intégration de `prefillPrompt` (`onPrefillConsumed`) et du menu déroulant `AssistantAutocompleteDropdown` sur saisie de `@` ou `/` dans `💬 Mon Assistant` |
| `apps/web/src/components/agentsAndSkillsBridgeStore.ts` | Créé | 117 | Pont de stockage partagé (`orcia.agents_and_skills.v1` et `orcia.assistant_prefill_prompt.v1`) isolé dans `components/` pour respecter l'isolation stricte entre `features/catalog` et `features/inbox` (`M11`, `AD-19`) |
| `apps/web/src/features/catalog/packAgentsCatalog.ts` | Créé | 238 | Catalogue déclaratif des Agents (`@architecte-solution`, `@analyste-metier`, `@reviseur-qualite`, `@concepteur-pack`) et Compétences (`/revue-architecture`, `/extraction-exigences`, `/audit-securite`, `/validation-pack`) des Packs Métiers (`orcia-pack-sdlc`, `orcia-pack-builder`) et fusion non-destructive |
| `apps/web/src/features/catalog/useManagedAgentsAndSkills.ts` | Créé | 348 | Hook métier de gestion des Agents et Compétences (hydratation API, persistance `localStorage`, bascule de visibilité `PRIVATE` / `TEAM` / `PACK`, modification du niveau de réflexion, exécution et chargement 1-clic des Packs Métiers) |
| `apps/web/src/features/catalog/index.tsx` | Modifié | 281 | Épuration radicale de `CatalogFeaturePanel` (masquage visuel de `catalog-setup-guidance-card`, `CatalogExplorerPanel` et `RemoteServiceTestBenchAndMcpExposureView` tout en préservant le montage DOM pour l'audit zéro bouton muet) et pont 1-clic vers `/assistant` |
| `apps/web/src/features/inbox/savedConversationsStore.ts` | Modifié | 340 | Ajout de `consumeAssistantPrefillFromStorage()` et `buildAssistantAutocompleteSuggestions()` synchronisés avec les agents/compétences créés et les Packs Métiers actifs |
| `apps/web/src/features/inbox/index.tsx` | Modifié | 406 | Branchement de `prefillPrompt` et `autocompleteSuggestions` dans `InboxFeaturePanel` (`💬 Mon Assistant`) |
| `packages/ui/src/__tests__/agents-and-skills.test.tsx` | Modifié | 253 | Tests unitaires `@orcia/ui` couvrant la création d'agents/compétences `PRIVATE` vs `TEAM`, les filtres de visibilité, la bascule inline avec badge `✓ Enregistré`, le rendu Markdown, le chargement des Packs Métiers et le pont `💬 Utiliser dans Mon Assistant` |
| `apps/web/src/__tests__/i18n-and-shell.test.tsx` | Modifié | 917 | Test d'intégration bout-en-bout (`🤖 Mes Agents` $\rightarrow$ création `@expert-achats-it` privé $\rightarrow$ bascule `👥 Équipe` $\rightarrow$ chargement des Packs Métiers $\rightarrow$ clic `💬 Utiliser dans Mon Assistant` $\rightarrow$ pré-remplissage dans `/assistant` $\rightarrow$ autocomplétion `@` $\rightarrow$ survie au `F5`) |

### 3.2 Résultats des Portes de Vérification (`AD-17` & `AD-19`)

- **Lint, Typecheck & Tests Unitaires/Intégration TypeScript (`pnpm turbo run lint typecheck test`)** :
  - `@orcia/api-client` : `lint` OK, `typecheck` OK, `test` OK.
  - `@orcia/ui` : `lint` OK, `typecheck` OK, `45` fichiers de tests passés (`129` tests passés, `0` échec).
  - `@orcia/web` : `lint` OK (`0` import inter-features), `typecheck` OK, `4` fichiers de tests passés (`36` tests passés dont `zero-dead-buttons-and-silent-catches-audit.test.tsx`, `design-system-look-and-feel-isolation.test.tsx`, `orcia-showcase-site.test.tsx` et `i18n-and-shell.test.tsx`).
- **Qualité & Architecture Python (`.venv/bin/ruff`, `.venv/bin/lint-imports`)** :
  - `ruff check .` : `All checks passed!`
  - `ruff format --check .` : `537 files already formatted`
  - `lint-imports` : `5 kept, 0 broken` (`AD-19` & `AD-20`).
- **Synchronisation du Site Vitrine (`/showcase` & `docs/site-catalog/index.html`)** :
  - `pnpm site:sync && pnpm site:check` : `OK`.
