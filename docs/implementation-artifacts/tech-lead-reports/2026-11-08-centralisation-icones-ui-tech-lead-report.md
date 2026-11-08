# 2026-11-08 — Audit & Refactoring de la Centralisation des Icônes UI (`@orcia/ui` & `apps/web`)

- **Date** : 2026-11-08
- **Story / Clé Sprint** : `2026-11-08-centralisation-icones-ui` (`Ajustement Transverse — Design System @orcia/ui & SPA Direction C`)
- **Auteur / Contexte** : Audit exhaustif et refactoring complet de la gestion des icônes à travers le Design System `@orcia/ui` (`packages/ui/src/`) et l'application web (`apps/web/src/`). Mise en place d'une source unique de vérité (`packages/ui/src/components/icons/`) garantissant que toute modification d'une icône dans le registre central se répercute immédiatement dans l'ensemble des composants et écrans consommateurs (`UX-DR1` à `UX-DR16`, `DESIGN.md`, `AD-19`).
- **Commits associés** : `pending`

---

## 1. Analyse du Besoin & Étude d'Impact Tech Lead (Pré-Implémentation)

### 1.1 Contexte & Problématique
- **Problématique identifiée** :
  - Lors de l'audit exhaustif de `packages/ui/src/` et `apps/web/src/`, **aucun `<svg>` inline orphelin** n'a été détecté (`0` occurrence de `<svg`), mais **aucun registre central d'icônes n'existait** dans `@orcia/ui`.
  - L'ensemble des icônes de l'interface (menus de navigation, sélecteurs d'espaces/périmètres, boutons d'action de l'Assistant, indicateurs d'état, chevrons d'accordéons, boutons de fermeture de modales/tiroirs, déclencheurs d'aide contextuelle `ⓘ` et badges d'alerte `!`) était dispersé en dur sous forme de glyphes Unicode ou de dictionnaires locaux isolés dans plus de 25 fichiers (`DEFAULT_EIGHT_FIXED_MENU_ENTRIES` dans `FourZoneDirectionCShell.tsx`, `MODULE_ICONS` dans `GlobalSidebar.tsx`, `LEVEL_ICONS` dans `ScopeSwitcher.tsx`, boutons d'action dans `AssistantResponseFooterActionsAndCitations.tsx`, `AssistantSpeedSelectorAndStreamView.tsx`, `ContextualInfoTriggerButton.tsx`, `DisabledButtonAlertIndicator.tsx`, etc.).
- **Comportement attendu vs comportement actuel** :
  - **Actuel** : Modifier l'icône d'un module (ex. `processes`, `cockpit`, `configuration`), d'une action (ex. `copy`, `regenerate`, `send`, `stop`, `close`), ou d'un chevron oblige à chercher et remplacer manuellement des chaînes de caractères dispersées dans `packages/ui` et `apps/web`, avec un risque élevé d'incohérence visuelle.
  - **Attendu** : Disposer d'un **registre centralisé et fortement typé d'icônes** (`ORCIA_ICONS`, `OrciaIconName`, `getOrciaIconGlyph`, `<OrciaIcon name="..." />`) dans `packages/ui/src/components/icons/` exporté par `@orcia/ui`. Toute icône affichée dans l'interface provient de ce registre unique : **si l'on modifie la définition d'une icône dans ce registre central, le changement est immédiatement répercuté dans toutes les interfaces où elle est utilisée**.
- **Contraintes spécifiques de `ARCHITECTURE-SPINE.md` & `DESIGN.md`** :
  - Isolation stricte de `packages/ui` : zéro import de `@tanstack/react-router`, `@orcia/api-client`, `zustand` ou de stores de `apps/web`.
  - Zéro couleur hexadécimale en dur hors `packages/ui/src/styles/tokens.css`, et exclusivité de `--color-human-led-violet` pour `HumanLedAnchorCard.tsx`.
  - Accessibilité RGAA 4.1 : `aria-hidden="true"` par défaut sur les icônes décoratives, ou `role="img"` + `aria-label` lorsque `ariaLabel` est fourni.
  - Respect du seuil de volumétrie des fichiers (`300–400` lignes maximum par fichier créé).

### 1.2 Exploration, Analyse d'Impact GitNexus, Factorisation & Dette Technique
- **Analyse d'Impact GitNexus (`gitnexus_query`, `gitnexus_context`, `gitnexus_impact`)** :
  - `gitnexus_query({search_query: "icon glyph badge button rail header modal", repo: "/home/romain/Documents/Projects/ORCIA"})` : identification des composants structurants du Shell Direction C et des primitives d'interaction.
  - `gitnexus_context({name: "FourZoneDirectionCShell", file_path: "packages/ui/src/primitives/FourZoneDirectionCShell.tsx"})` : appelé par `InnerShellContainer` (`apps/web/src/components/ShellContainer.tsx`) et testé dans `four-zone-shell-and-cockpit.test.tsx` et `i18n-and-shell.test.tsx`.
  - `gitnexus_impact({target: "ContextualInfoTriggerButton", direction: "upstream"})` et `gitnexus_impact({target: "DisabledButtonAlertIndicator", direction: "upstream"})` : `DisabledButtonAlertIndicator` impacte `42` symboles en amont (`24` appelants directs via `OrciaButton`, `FourZoneDirectionCShell`, `RgaaModalDialog`, etc. — niveau de risque `HIGH`), exigeant une préservation à `100 %` des `data-testid` et de la structure DOM.
- **Exploration & Chiffres Clés (Audit Exhaustif du Codebase)** :
  - **SVG inline (`<svg ...>`)** : `0` occurrence dans `packages/ui/src/` et `apps/web/src/`.
  - **Dictionnaires d'icônes locaux redondants identifiés** :
    1. `DEFAULT_EIGHT_FIXED_MENU_ENTRIES` dans `packages/ui/src/primitives/FourZoneDirectionCShell.tsx` (`◈`, `💬`, `☍`, `🤖`, `📦`, `📊`, `⚙`, `❓`, plus `📜` et `📖`).
    2. `MODULE_ICONS` dans `packages/ui/src/shell/GlobalSidebar.tsx` (`🏠`, `🔔`, `📦`, `🧬`, `🛡️`, `📊`, `⚙️`, `🚀` et `❖`).
    3. `LEVEL_ICONS` dans `packages/ui/src/shell/ScopeSwitcher.tsx` (`🌐`, `🏢`, `👥`, `🗂️`).
    4. `DEFAULT_MODULES` dans `apps/web/src/components/shellPresets.ts` (noms d'icônes non résolus via un registre central).
  - **Composants UI à icônes en dur identifiés** :
    - `ContextualInfoTriggerButton.tsx` (`i` / `ⓘ`), `DisabledButtonAlertIndicator.tsx` (`!`), `RgaaModalDialog.tsx` (`✕`, `⚠️`), `FormattedMarkdownContent.tsx` (`✓`).
    - `AssistantResponseFooterActionsAndCitations.tsx` (`👍`, `👎`, `📋`, `✓`, `↻`, `📄`, `☍`, `⋯`, `💻`, `🗂️`, `↗`), `AssistantSpeedSelectorAndStreamView.tsx` (`▶`, `■`, `⏹`, `▾`, `↓`, `📁`, `📌`, `+`, `×`), `AssistantThinkingSubWindow.tsx` (`⌄`, `›`, `⏳`, `✓`), `AssistantPromptPlusAndAutocomplete.tsx` (`💻`, `🗂️`, `▸`, `📄`, `📁`, `🤖`, `🛠️`), `AssistantModelAndEffortPopover.tsx` (`✓`, `🧠`, `▸`).
    - `TopHeaderBar.tsx` (`🗂️`, `🎯`, `🟢`, `🔴`, `🟡`), `TopHeaderSearchCommand.tsx` (`✨`, `❓`, `🎯`), `UserAccountDropdownAndSettingsModal.tsx` (`👤`, `☀️`, `🌙`), `UserSettingsModalTabs.tsx` (`❓`, `🔔`, `✅`), `CollapsibleAppRail.tsx` (`🔔`, `🟢`), `ContextualHelpColumnAndCenter.tsx` (`ⓘ`, `❓`, `▾`, `▸`), `BiModeLoginView.tsx` (`🔐`, `▾`, `▸`), `ChunkValidationCard.tsx` (`✓`, `✍️`, `⏪`, `🛡️`, `⚠️`), `CognitiveReviewBriefingGrid.tsx` (`🛡️`, `✓`, `⚠️`, `⚖️`), `ActivityLogExplorerView.tsx` (`🕒`, `👤`, `📍`), `WorkspaceControlCenter.tsx` (`⚡`, `👁️`), `AppShellTopbar.tsx` (`🔍`, `💬`, `▾`, `🌙`), `OntologyAndKbExplorerPanel.tsx` (`↻`), `AgentStudioCardItem.tsx` & `SkillStudioCardItem.tsx` (`🔒`, `📦`, `👥`, `✓`, `💬`, `⚡`), et vues `apps/web/src/` (`ShellContainer.tsx`, `ontology/index.tsx`, `SavedConversationsAndThreadView.tsx`, `WorkspaceStudioCardsAndDetailView.tsx`).
- **Opportunités de Factorisation & Résorption de Dette Technique Naissante** :
  - Création du module central `packages/ui/src/components/icons/` découpé en deux fichiers courts (`< 220` lignes chacun) pour respecter strictement la limite des `300–400` lignes :
    - `packages/ui/src/components/icons/iconRegistry.ts` : définition typée `OrciaIconName`, `OrciaIconDefinition`, `ORCIA_ICONS`, helpers `getOrciaIconGlyph(name)`, `getOrciaIconDefinition(name)`, et tables de correspondance sémantiques (`ORCIA_EIGHT_MENU_ICON_NAMES`, `ORCIA_MODULE_ICON_NAMES`, `ORCIA_SCOPE_LEVEL_ICON_NAMES`).
    - `packages/ui/src/components/icons/OrciaIcon.tsx` : composant React `<OrciaIcon />` standardisé, accessible (`aria-hidden="true"` par défaut ou `role="img"` + `aria-label` si labellisé, attribut `data-orcia-icon={name}`) et réactif à toute mise à jour de `ORCIA_ICONS`.
    - `packages/ui/src/components/icons/index.ts` : barrel d'export ré-exporté dans `packages/ui/src/index.ts`.

---

## 2. Plan d'Implémentation

### 2.1 Schéma de Données & Migrations Alembic (`infra/migrations/versions/...`, si applicable)
- Aucune modification de schéma PostgreSQL 18 requise (refactoring purement Design System `@orcia/ui` et SPA `apps/web`).

### 2.2 Noyau Métier Hexagonal, Orchestration & Workers (`packages/orcia-core/`, `apps/worker/`, `infra/sandbox/`)
- Aucun impact sur `packages/orcia-kernel` ni `packages/orcia-core` (frontières modulaires `AD-19` intactes).

### 2.3 Couche Backend API, Sécurité & Contrats (`apps/api/`, `packages/api-client/`)
- Aucun impact sur les schémas OpenAPI 3.1 ni sur `@orcia/api-client` (`0-diff` préservé).

### 2.4 Interface Utilisateur & Expérience (`packages/ui/` & `apps/web/`)
1. **Création du Registre Central d'Icônes (`packages/ui/src/components/icons/`)** :
   - Définir `ORCIA_ICONS` comme source unique de vérité associant chaque clé sémantique `OrciaIconName` (ex. `cockpit`, `assistant`, `processes`, `agents`, `spaces`, `finops`, `activity`, `configuration`, `help`, `vocabulary`, `search`, `notifications`, `user`, `close`, `check`, `cross`, `warning`, `alertBadge`, `infoBadge`, `chevronDown`, `chevronRight`, `caretDown`, `caretRight`, `play`, `playOutline`, `stopSquare`, `stopButton`, `regenerate`, `rollback`, `rewind`, `copy`, `like`, `dislike`, `moreHorizontal`, `externalLink`, `arrowDown`, `arrowUp`, `hourglass`, `folder`, `pin`, `laptop`, `workspaceFolder`, `document`, `globe`, `organizationBu`, `team`, `lock`, `pack`, `tools`, `brain`, `sparkles`, `target`, `lightning`, `shield`, `scale`, `pen`, `eye`, `clock`, `locationPin`, `sun`, `moon`, `plug`, `compass`, `desktop`, `dna`, `rocket`, `home`, `brandLogo`, `statusHealthy`, `statusWarning`, `statusError`, `plus`, `minus`, `money`, `book`, `books`, `keyLock`, `star`) à sa définition (`glyph`, `category`, `description`).
   - Créer `<OrciaIcon name="..." />` qui lit dynamiquement `ORCIA_ICONS[name].glyph` et applique `data-orcia-icon={name}` ainsi que les attributs d'accessibilité RGAA.
   - Exporter `ORCIA_ICONS`, `OrciaIcon`, `getOrciaIconGlyph`, `getOrciaIconDefinition`, `ORCIA_EIGHT_MENU_ICON_NAMES`, `ORCIA_MODULE_ICON_NAMES`, `ORCIA_SCOPE_LEVEL_ICON_NAMES` et leurs types depuis `packages/ui/src/index.ts`.
2. **Refactoring des Composants `@orcia/ui` et `apps/web` vers le Registre Central** :
   - Remplacer les dictionnaires d'icônes codés en dur et les glyphes UI dispersés dans `FourZoneDirectionCShell.tsx`, `GlobalSidebar.tsx`, `ScopeSwitcher.tsx`, `AppShellTopbar.tsx`, `TopHeaderBar.tsx`, `TopHeaderSearchCommand.tsx`, `CollapsibleAppRail.tsx`, `ContextualInfoTriggerButton.tsx`, `DisabledButtonAlertIndicator.tsx`, `RgaaModalDialog.tsx`, `FormattedMarkdownContent.tsx`, `ContextualHelpColumnAndCenter.tsx`, `AssistantSpeedSelectorAndStreamView.tsx`, `AssistantResponseFooterActionsAndCitations.tsx`, `AssistantThinkingSubWindow.tsx`, `AssistantPromptPlusAndAutocomplete.tsx`, `AssistantModelAndEffortPopover.tsx`, `AssistantFoldersAndCollaborativeThreadView.tsx`, `AssistantGovernanceModalAndStudio.tsx`, `AssistantGovernanceModeATabs.tsx`, `AssistantGovernanceStudioModeB.tsx`, `AgentStudioCardItem.tsx`, `SkillStudioCardItem.tsx`, `BiModeLoginView.tsx`, `ChunkValidationCard.tsx`, `CognitiveReviewBriefingGrid.tsx`, `ActivityLogExplorerView.tsx`, `WorkspaceControlCenter.tsx`, `UserAccountDropdownAndSettingsModal.tsx`, `UserSettingsModalTabs.tsx`, `OntologyAndKbExplorerPanel.tsx`, `GuidanceDrawer.tsx`, `HelpArticleGeneratorAndValidatorView.tsx`, `MobileCompanionView.tsx`, `ProgressiveDay0AccostageBanner.tsx`, `ScopedPromptBox.tsx`, `SprintContextWidget.tsx`, `UpstreamChallengeRewindModal.tsx`, ainsi que dans `apps/web/src/components/ShellContainer.tsx`, `apps/web/src/components/shellPresets.ts`, `apps/web/src/features/ontology/index.tsx`, `apps/web/src/features/inbox/SavedConversationsAndThreadView.tsx`, et `apps/web/src/features/workspaces/WorkspaceStudioCardsAndDetailView.tsx`.
3. **Tests d'Audit Anti-Régression Automatisés (Vitest)** :
   - Créer `packages/ui/src/__tests__/icon-registry-centralization.test.tsx` vérifiant :
     1. Qu'aucun `<svg` inline orphelin n'existe dans `packages/ui/src/` ou `apps/web/src/` en dehors du module central `packages/ui/src/components/icons/`.
     2. Qu'aucun dictionnaire local d'icônes non rattaché à `ORCIA_ICONS` n'existe dans les composants shell/primitives.
     3. Que toute modification d'une définition dans `ORCIA_ICONS` (ex. remplacement temporaire d'un glyphe dans le registre central) est **immédiatement répercutée** dans le rendu DOM de `<OrciaIcon />`, `FourZoneDirectionCShell`, `GlobalSidebar`, `ScopeSwitcher`, `AssistantResponseFooterActionsAndCitations`, `AssistantSpeedSelectorAndStreamView`, `ContextualInfoTriggerButton`, `DisabledButtonAlertIndicator`, etc.

---

## 3. Bilan des Modifications & Résultats (Post-Implémentation)

### 3.1 Tableau Synthétique des Fichiers Développés & Modifiés

| Fichier | Action | Rôle & Modifications |
| :--- | :--- | :--- |
| `packages/ui/src/components/icons/iconRegistry.ts` | **Créé** (`245` lignes) | Source unique de vérité (`ORCIA_ICONS`) centralisant `97` clés sémantiques `OrciaIconName` par catégorie (`navigation`, `action`, `status`, `chevron`, `scope`, `assistant`, `governance`), accesseurs `getOrciaIconDefinition(name)` / `getOrciaIconGlyph(name)`, et tables de correspondance (`ORCIA_EIGHT_MENU_ICON_NAMES`, `ORCIA_MODULE_ICON_NAMES`, `ORCIA_SCOPE_LEVEL_ICON_NAMES`). |
| `packages/ui/src/components/icons/OrciaIcon.tsx` | **Créé** (`47` lignes) | Composant React standardisé `<OrciaIcon name="..." />` lisant dynamiquement `getOrciaIconGlyph(name)` avec attribut `data-orcia-icon={name}` et accessibilité RGAA 4.1 (`aria-hidden="true"` par défaut ou `role="img"` + `aria-label` lorsque `ariaLabel` est renseigné). |
| `packages/ui/src/components/icons/index.ts` | **Créé** (`16` lignes) | Point d'entrée public du module d'icônes, ré-exporté dans `packages/ui/src/index.ts`. |
| `packages/ui/src/__tests__/icon-registry-centralization.test.tsx` | **Créé** (`368` lignes) | Suite d'audit anti-régression Vitest à 5 gates : (1) zéro `<svg` inline orphelin hors `components/icons/`, (2) zéro dictionnaire local d'icônes déconnecté dans le Shell, (2b) zéro `<span aria-hidden="true">` à glyphe d'icône codé en dur hors `components/icons/`, (3) complétude et accessibilité RGAA de `ORCIA_ICONS` / `<OrciaIcon />`, et (4) preuve de réactivité immédiate bout-en-bout lorsqu'une définition dans `ORCIA_ICONS` est modifiée. |
| `packages/ui/src/components/{ContextualInfoTriggerButton,DisabledButtonAlertIndicator,RgaaModalDialog,FormattedMarkdownContent}.tsx` | **Modifiés** | Remplacement des glyphes codés en dur (`i`, `!`, `✕`, `⚠️`, `✓`) par `<OrciaIcon />` et `getOrciaIconGlyph(...)`. |
| `packages/ui/src/shell/{GlobalSidebar,ScopeSwitcher,AppShellTopbar,OntologyAndKbExplorerPanel}.tsx` | **Modifiés** | Suppression de `MODULE_ICONS` et `LEVEL_ICONS` locaux au profit de `ORCIA_MODULE_ICON_NAMES`, `ORCIA_SCOPE_LEVEL_ICON_NAMES` et `<OrciaIcon />`. |
| `packages/ui/src/primitives/FourZoneDirectionCShell.tsx` | **Modifié** | Liaison dynamique par getters (`get icon()`) de `DEFAULT_EIGHT_FIXED_MENU_ENTRIES` sur `ORCIA_EIGHT_MENU_ICON_NAMES` et remplacement des icônes de la TopBar/Sidebar/Notifications par `<OrciaIcon />`. |
| `packages/ui/src/primitives/{AssistantSpeedSelectorAndStreamView,AssistantResponseFooterActionsAndCitations,AssistantThinkingSubWindow,AssistantPromptPlusAndAutocomplete,AssistantModelAndEffortPopover,AssistantFoldersAndCollaborativeThreadView,AssistantGovernanceModalAndStudio,AssistantGovernanceModeATabs,AssistantGovernanceStudioModeB}.tsx` | **Modifiés** | Centralisation intégrale des icônes de `💬 Mon Assistant` (Play `▶`, Stop `■`, `⏹`, `👍`, `👎`, `📋`, `✓`, `↻`, `📄`, `☍`, `⋯`, `⌄`, `›`, `⏳`, `💻`, `🗂️`, `📁`, `📌`, `🧠`, `🔒`, `↺`, `💡`) via `<OrciaIcon />` et `getOrciaIconGlyph(...)`. |
| `packages/ui/src/primitives/{TopHeaderBar,TopHeaderSearchCommand,CollapsibleAppRail,ContextualHelpColumnAndCenter,UserAccountDropdownAndSettingsModal,UserSettingsModalTabs,BiModeLoginView,ChunkValidationCard,CognitiveReviewBriefingGrid,ActivityLogExplorerView,WorkspaceControlCenter,GuidanceDrawer,HelpArticleGeneratorAndValidatorView,MobileCompanionView,ProgressiveDay0AccostageBanner,ScopedPromptBox,SprintContextWidget,UpstreamChallengeRewindModal,AgentStudioCardItem,SkillStudioCardItem,OrciaProductShowcaseSiteView}.tsx` | **Modifiés** | Remplacement de tous les glyphes d'icônes en dur et liaison par getters de `NINE_SCREENS_GUIDE` dans `OrciaProductShowcaseSiteView.tsx` sur `ORCIA_ICONS`. |
| `apps/web/src/components/ShellContainer.tsx`, `apps/web/src/features/ontology/index.tsx`, `apps/web/src/features/inbox/SavedConversationsAndThreadView.tsx`, `apps/web/src/features/workspaces/{WorkspaceStudioCardsAndDetailView,WorkspaceDetailTabsPanel,WorkspaceGlossaryAndOntologyTab}.tsx` | **Modifiés** | Consommation directe de `<OrciaIcon />` et `getOrciaIconGlyph(...)` depuis `@orcia/ui` dans les vues `apps/web`. |

### 3.2 Métriques Chiffrées & Validation des Gates Qualité

- **Clés sémantiques d'icônes centralisées (`ORCIA_ICONS`)** : `97` icônes typées (`OrciaIconName`).
- **Occurrences `<svg>` inline orphelines hors `packages/ui/src/components/icons/`** : `0` (vérifié automatiquement par `Audit Gate 1`).
- **Occurrences `<span aria-hidden="true">` à glyphe d'icône en dur hors `packages/ui/src/components/icons/`** : `0` (vérifié automatiquement par `Audit Gate 2b`).
- **Suites de tests TypeScript / React (`pnpm turbo run lint typecheck test`)** :
  - `@orcia/ui` : `16/16` fichiers de tests Vitest passés (`69/69` tests `PASS`, incluant les 5 gates de `icon-registry-centralization.test.tsx`), `lint` `0` erreur, `typecheck` `0` erreur.
  - `@orcia/web` : `5/5` fichiers de tests Vitest passés (`40/40` tests `PASS`, incluant `design-system-look-and-feel-isolation.test.tsx`, `zero-dead-buttons-and-silent-catches-audit.test.tsx` et `i18n-and-shell.test.tsx`), `lint` `0` erreur, `typecheck` `0` erreur.
  - `@orcia/api-client` : `lint`, `typecheck` et `test` `PASS` (`0-diff` préservé).
- **Synchronisation du Site de Présentation (`pnpm site:sync` & `pnpm site:check`)** : `PASS` (`apps/web/src/generated/orciaSiteManifest.ts` et `docs/site-catalog/index.html` synchronisés).
