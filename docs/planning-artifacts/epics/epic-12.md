## Epic 12: Intégration Bout-en-Bout du Portail SPA (`apps/web`) — Bascule sur le Shell 4 Zones Direction C (8 Entrées Fixes), Cockpit Épuré, `Mon Assistant` (Epic 10), `Mes Espaces` 5 Onglets & Atelier `orcia-pack-builder` (Epic 11)

Réaliser la bascule visuelle et fonctionnelle complète de l'application SPA `apps/web` vers la refonte des **Epics 9, 10 et 11** conçue par **Sally (`bmad-agent-ux-designer`)** et **Winston (`bmad-agent-architect`)** : remplacer l'ancien `<AppShell />` à 3 zones (et son dock droit permanent + barre mobile du bas) par le **Shell 4 Zones Direction C (`FourZoneDirectionCShell`)** avec ses **8 entrées fixes** (`1. Cockpit`, `2. Mon Assistant`, `3. Mes Espaces`, `4. Mes Agents`, `5. Mes Processus`, `6. Centre de Contrôle`, `7. Paramètres`, `8. Aide`), unifier les jetons sémantiques CSS et classes utilitaires dans `@orcia/ui/styles/tokens.css`, épurer le Cockpit (`StreamlinedCockpitView` + `ProgressiveDay0AccostageBanner` sans les anciens blocs redondants), et monter dans `apps/web` l'intégralité des écrans **`Mon Assistant` (Epic 10)** et **`Mes Espaces` 5 sous-onglets / Chaîne ADN Starlark / Banc de Test MCP `🔌` / Atelier `orcia-pack-builder` (Epic 11)**.

### Story 12.1: Bascule de `apps/web` sur le Shell 4 Zones Direction C (`FourZoneDirectionCShell`), Navigation 8 Entrées Fixes, Unification CSS (`tokens.css`) & Cockpit Épuré (Epic 9)

As a Utilisateur d'ORCIA (Contributeur, Chef d'Équipe, Architecte ou Administrateur),
I want que le portail `apps/web` démarre directement dans le nouveau **Shell 4 Zones Direction C** (`FourZoneDirectionCShell`) avec la barre supérieure `52px` (sélecteur d'Espace, recherche globale `⌘K` `TopHeaderSearchCommand`, bouton `❓` et menu Avatar `UserAccountDropdownAndSettingsModal`), le rail gauche à **8 entrées fixes**, la colonne d'aide contextuelle `❓` (`340px` `ContextualHelpColumnAndCenter`) et le **Cockpit épuré** (`StreamlinedCockpitView` + `ProgressiveDay0AccostageBanner`), sans l'ancien dock droit ni les anciens blocs redondants ni aucun bouton HTML non stylé,
So that l'expérience visuelle réelle au lancement de l'interface corresponde à 100 % à la refonte Direction C et aux 11 règles fondamentales UX/UI (`DESIGN.md`, `EXPERIENCE.md`, `UX-DR1`, `AD-19`).

**Acceptance Criteria:**

**Given** le fichier `packages/ui/src/styles/tokens.css`, le conteneur `apps/web/src/components/ShellContainer.tsx`, le routeur `apps/web/src/router.tsx` et la vue `apps/web/src/features/cockpit/index.tsx`
**When** l'utilisateur démarre et ouvre `apps/web` sur `/cockpit` ou navigue entre les entrées du rail latéral gauche
**Then** :
1. `packages/ui/src/styles/tokens.css` définit tous les alias de jetons sémantiques Direction C (`--color-surface-elevated`, `--color-surface-base`, `--color-surface-muted`, `--color-border-subtle`, `--color-text-primary`, `--color-text-secondary`, `--color-accent-primary`, `--color-status-success`, `--color-status-warning`, `--color-status-danger`) et les classes utilitaires de mise en page utilisées par les primitives des Epics 9, 10 et 11 (sans aucune couleur hexadécimale hors de `tokens.css`) ;
2. `ShellContainer.tsx` monte **`FourZoneDirectionCShell`** en lieu et place de l'ancien `AppShell` (supprimant le dock latéral droit figé *« Agent Assistant & Permission Broker »* et l'ancienne barre basse `Inbox | Arbitrage/Chat | Briefing`), intègre dans le Header `52px` la recherche `⌘K` (`TopHeaderSearchCommand`) et le menu Compte/Paramètres (`UserAccountDropdownAndSettingsModal`), et peuple la colonne `❓` (`340px`) avec `ContextualHelpColumnAndCenter` ;
3. Le rail gauche expose les **8 entrées fixes** (`Cockpit` `/cockpit`, `Mon Assistant` `/assistant`, `Mes Espaces` `/workspaces`, `Mes Agents` `/agents`, `Mes Processus` `/processes`, `Centre de Contrôle` `/control-center`, `Paramètres` `/settings`, `Aide` `/help`) et le Cockpit (`CockpitFeaturePanel`) affiche uniquement la bannière d'accostage progressif **`ProgressiveDay0AccostageBanner`** et le flux **`StreamlinedCockpitView`** (sans l'ancien `ScopedPromptBox` ni l'ancienne `PlatformOnboardingChecklistCard` dupliquée)
**And** `pnpm turbo run lint typecheck test` passe à `0` erreur.

### Story 12.2: Montage de l'Écran Dédié `Mon Assistant` (`/assistant`) Tout-en-Un dans `apps/web` (Epic 10 : Dossiers Collaboratifs, Sélecteur 3 Vitesses, Citations `[S1]`/`[G1]`/`[O1]` & Gouvernance 4 Niveaux)

As a Utilisateur Métier, Product Manager ou Tech Lead (`Hélène UJ-1`, `Yanis UJ-3`, `Marc UJ-5`),
I want accéder depuis l'entrée **`2. 💬 Mon Assistant`** du rail gauche (ou depuis le raccourci du Cockpit) à l'écran complet `Mon Assistant` réunissant mes dossiers thématiques et fils collaboratifs, le sélecteur 3 vitesses (`⚡ Rapide`, `🧠 Réflexion`, `🔬 Recherche Approfondie`), les pastilles de citations déterministes `[S1]` / `[G1]` / `[O1]`, la carte d'artefact `📄 Ouvrir dans l'Atelier` et la modale `⚙️ Gouvernance & Instructions (4 niveaux)` (Mode A Formulaires & Mode B Studio),
So that je puisse utiliser concrètement dans le navigateur toutes les capacités conversationnelles et collaboratives livrées dans l'Epic 10 (`Principes B, H, K`, `AD-6`, `AD-15`, `AD-19`).

**Acceptance Criteria:**

**Given** la route `/assistant` et le module feature `apps/web/src/features/inbox/index.tsx` (ou vue dédiée `Mon Assistant`)
**When** l'utilisateur clique sur **`💬 Mon Assistant`** dans le rail gauche ou sur la carte d'accès rapide du Cockpit
**Then** :
1. L'écran monte et orchestre de façon interactive les 4 briques `@orcia/ui` de l'Epic 10 :
   - **`AssistantFoldersAndCollaborativeThreadView`** (barre latérale des dossiers thématiques, visibilité `🔒 Privé` / `👁️ Lecture seule` / `✍️ Co-contribution`, recherche plein texte dans l'historique) ;
   - **`AssistantSpeedSelectorAndStreamView`** (sélecteur 3 vitesses `⚡ Rapide`, `🧠 Réflexion`, `🔬 Recherche Approfondie`, indicateur TTFT `< 1,2 s` et progression temps réel) ;
   - **`AssistantCitationPillsAndArtifactCard`** (pastilles interactives `[S1]` Sources, `[G1]` Glossaire & Normes, `[O1]` Outils MCP, tiroir de preuve et carte d'artefact long) ;
   - **`AssistantGovernanceModalAndStudio`** (ouverture de la modale `⚙️ Personnaliser & Gouverner` avec bascule Mode A Formulaires 4 niveaux $\leftrightarrow$ Mode B Studio DAG) ;
2. Toutes les étiquettes proviennent des dictionnaires `fr.ts` / `en.ts` (`100 %` parité bilingue)
**And** `pnpm turbo run lint typecheck test` passe à `0` erreur.

### Story 12.3: Montage dans `apps/web` de `Mes Espaces` à 5 Sous-Onglets (`/workspaces`), Chaîne ADN & Glossaire Starlark, Banc de Test MCP/A2A `🔌` (`/agents`, `/settings`) & Atelier `orcia-pack-builder` (`/processes`, `/help`) (Epic 11)

As a Responsable d'Espace, Steward Métier, Concepteur de Pack ou Administrateur (`Marc UJ-5`, `Hélène UJ-1`, `Antoine UJ-2`, `Karim UJ-9`),
I want retrouver et manipuler directement dans les écrans **`3. 📦 Mes Espaces`**, **`4. 🤖 Mes Agents`**, **`5. 🔗 Mes Processus`**, **`7. ⚙️ Paramètres`** et **`8. ❓ Aide`** de `apps/web` les 5 sous-onglets de l'Espace (`Vue d'ensemble`, `Documents & Sources`, `Livrables & Artefacts`, `Glossaire & Règles métier`, `Membres & Équipe`), le compilateur `Text-to-Starlark` & la file `✨ À valider` du Glossaire, le Banc de Test à Chaud en 4 étapes (`🔌`) + exposition MCP gouvernée, ainsi que l'Atelier Système `orcia-pack-builder` (Processus 1 à 5 et validateur `validate_help_article`),
So that toutes les fonctionnalités de gouvernance métier, de sécurité MCP et d'extensibilité par Packs de l'Epic 11 soient pleinement opérationnelles dans l'interface web (`Principes D.4, I, J, L, M`, `AD-7`, `AD-9`, `AD-19`, `AD-20`).

**Acceptance Criteria:**

**Given** les routes `/workspaces`, `/agents`, `/processes`, `/control-center`, `/settings` et `/help` dans `apps/web`
**When** l'utilisateur navigue vers ces écrans depuis le rail gauche à 8 entrées
**Then** :
1. **`📦 Mes Espaces` (`/workspaces`)** monte **`WorkspaceFiveTabsAndExternalRebaseView`** (navigation interactive entre les 5 sous-onglets, qualification des sources `📚 RÉFÉRENCE` / `🛠️ ACTIF`, dérogations d'exception `Verrou V1`, et statut `🔒 HUMAN_AMENDED_EXTERNAL` `Verrou V2`) ainsi que **`DnaStarlarkCompilerAndGlossaryLifecycleView`** dans l'onglet `Glossaire & Règles métier` (fil d'Ariane causal `🛡️ DIRECTIVE ➔ 📏 NORME ➔ ⚙️ MÉCANISME`, compilation Starlark `< 2 ms` et promotion *In-Flow* `Verrou V4`) ;
2. **`🤖 Mes Agents` (`/agents`) & `⚙️ Paramètres` (`/settings`)** montent **`RemoteServiceTestBenchAndMcpExposureView`** permettant d'exécuter visuellement les 4 étapes du Banc de Test à Chaud (`🔌`) et d'activer l'exposition MCP gouvernée (`/api/v1/mcp`) ;
3. **`🔗 Mes Processus` (`/processes`) & `❓ Aide` (`/help`)** montent **`PackBuilderProcessesStudioView`** (Processus 1 à 4 de `orcia-pack-builder` avec Ancrage Humain Violet obligatoire, simulation *What-If* et certification Starlark) ainsi que **`HelpArticleGeneratorAndValidatorView`** (Processus 5 `generate-and-attach-help` & Gate `validate_help_article` `< 5 s`) et le Centre d'Aide complet ;
4. L'isolation d'architecture (`check-feature-boundaries.mjs`, `ui-isolation.test.ts`, parité i18n `fr`/`en`) et l'ensemble des tests Vitest de `packages/ui` et `apps/web` passent à `100 %`.

### Story 12.4: Épuration UX « Zéro Donnée Fictive », Modale de Création du Compte Administrateur au 1er Démarrage, Grisage des Fonctionnalités Non Configurées, Nettoyage de la Sidebar & Purge des Libellés NFR

As a Administrateur de la Plateforme ou Utilisateur d'ORCIA (`Karim UJ-9`, `Hélène UJ-1`, `Yanis UJ-3`),
I want que l'application démarre au 1er lancement sur la modale de création du compte Administrateur de la plateforme, parte d'une interface 100 % vierge sans aucune donnée fictive (`0` dossier `PAY-142`, `0` source `PSD2`, `0` règle Starlark pré-remplie, `0` profil fictif `Administrateur / Tech Lead`), grise (`disabled`) toutes les entrées de navigation et fonctionnalités non encore accessibles faute de configuration suffisante, retire le bouton de langue redondant de la `TopHeaderBar`, supprime le sélecteur `Pack Métier actif` et les raccourcis parasites du bas de la Sidebar gauche, remplace « Casquette métier » par le sélecteur « Rôle » avec des libellés humains, et purge tous les textes liés aux NFR et à la plomberie technique (`< 500ms`, `0 ms`, `< 2 ms`, `340px`, `Couche 5`, `AD-*`, `UX-DR*`),
So that l'interface respecte intégralement les 11 règles fondamentales UX/UI (`EXPERIENCE.md`, `DESIGN.md` — Centrer sur l'utilisateur, Loi de Hick / Minimalisme, et credo « partir d'une interface vide »).

**Acceptance Criteria:**

**Given** le premier démarrage de la plateforme (`0` compte administrateur initialisé) dans `apps/web`
**When** l'application s'affiche dans le navigateur
**Then** :
1. **Modale de 1er démarrage (`first-boot-admin-setup-modal`)** : l'écran affiche en premier plan la modale dédiée de création du compte **Administrateur de la plateforme** (Nom complet, Adresse e-mail, Mot de passe, jeton d'amorçage si requis) sans aucune identité fictive pré-remplie ; une fois validée, l'identité active affiche le nom saisi et le rôle **`Administrateur de la plateforme`** (et jamais `Administrateur / Tech Lead`) ;
2. **Credo « Partir d'une interface vide » (`0` donnée fictive)** : tous les écrans (`Cockpit`, `Mon Assistant`, `Mes Espaces`, `Mes Agents`, `Mes Processus`, `FinOps`, `Configuration`, `Aide`) démarrent avec `0` dossier fictif (`PAY-142` / `ADR-019` supprimés), `0` message ou extrait pré-rempli, `0` source ou dérogation fictive, `0` mécanisme Starlark ou candidat glossaire fictif, et `0` service MCP fictif ;
3. **Grisage (`disabled`) des fonctionnalités non accessibles faute de configuration** : dans la Sidebar à 8 entrées (`FourZoneDirectionCShell`) et dans les vues centrales, toute fonctionnalité dont les prérequis de configuration ne sont pas remplis (ex. `Mon Assistant` et `Mes Agents` tant qu'aucun modèle IA n'est configuré ; `Mes Processus` et `FinOps` tant qu'aucun Espace ou modèle IA n'est configuré) est visuellement grisée (`disabled`, `aria-disabled="true"`) avec une infobulle explicite indiquant la configuration requise ;
4. **Nettoyage de la `TopHeaderBar`, du bas de la Sidebar et du Menu Utilisateur** :
   - Le bouton de langue redondant (`shell-locale-toggle`) est retiré de la `TopHeaderBar` (le sélecteur de langue résidant dans le menu de l'utilisateur à droite) ;
   - Le sélecteur `Pack Métier actif` et les raccourcis redondants (`sidebarModuleShortcuts`) sont retirés du bas de la Sidebar gauche ;
   - Dans le menu de l'utilisateur à droite (`UserAccountDropdownAndSettingsModal`), le sélecteur est conservé et renommé **« Rôle »** (`Role` en anglais) avec des libellés métiers lisibles (*Administrateur de la plateforme*, *Product Manager / Métier*, *Architecte*, *Tech Lead / Développeur*, *Sécurité & Conformité*) ;
5. **Purge complète des textes NFR et du jargon interne** : toutes les mentions de latences NFR (`< 500ms`, `0 ms`, `< 30 ms`, `< 50 ms`, `< 2 ms`, `< 5 s`, `< 100 ms`, `< 1,2 s`, `< 10 ms`, `< 15 s`), de dimensions en pixels (`340px`, `420px`, `280px`, `720px × max 600px`) et de références internes (`Couche 5`, `Mode A — 3 onglets`, `AD-*`, `UX-DR*`, `LOCK TABLE users`, `POST /api/v1/auth/logout → /login`) sont retirées des dictionnaires `fr.ts`, `en.ts` et `epic5..11_labels.ts`
**And** la parité bilingue `fr`/`en` à `100 %`, l'isolation `@orcia/ui` et `pnpm turbo run lint typecheck test` passent à `0` erreur.
