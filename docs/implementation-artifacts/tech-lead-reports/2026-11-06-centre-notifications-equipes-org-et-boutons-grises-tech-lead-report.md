# Rapport Tech Lead — Centre des Notifications vs Journal d'Activité, Clarification « Équipes » d'Organisation & Indicateur Rouge `!` sur Boutons Grisés

- **Ticket / Demande** : Demande transverse UX/UI & Architecture (3 volets : Centre des Notifications vs Journal d'Activité, Sémantique « Équipe » vs « Espace de Travail », Indicateur `!` rouge cerclé + infobulle rouge sur tous les boutons grisés)
- **Date** : `2026-11-06`
- **Auteur** : Équipe Tech Lead / Dev Senior & UX/UI (Sally UX Designer & Winston Architect)
- **Statut** : `DONE`

---

## 1. Analyse du Besoin & Étude d'Impact Tech Lead (Avant Codage)

### 1.1 Périmètre Fonctionnel & Critères d'Acceptation

La demande utilisateur couvre trois volets complémentaires de gouvernance UX/UI (Direction C) et de cohérence sémantique :

1. **Volet 1 — Centre des Notifications (`🔔 Notifications`) vs Journal d'Activité (`📜 Journal d'Activité`)** :
   - **Couverture dans les Epics & la base de code** :
     - **Epic 5 (`Story 5.1`, statut `done`)** dans [`docs/planning-artifacts/epics.md`](file:///home/romain/Documents/Projects/ORCIA/docs/planning-artifacts/epics.md#L1278-L1324) : *« Centre de Notifications Unifié (Individuel & Équipe), Prise en Charge Atomique (`Claim`) & Verrou de Présence SSE `< 500 ms` »*, soutenu en base PostgreSQL 18 par la table `task_notifications` (migration [`0021_story_5_1_task_notifications_and_resource_leases.py`](file:///home/romain/Documents/Projects/ORCIA/infra/migrations/versions/0021_story_5_1_task_notifications_and_resource_leases.py)), le domaine `orcia_core/orchestration/task_notifications.py` et la vue dédiée [`apps/web/src/features/inbox/index.tsx`](file:///home/romain/Documents/Projects/ORCIA/apps/web/src/features/inbox/index.tsx).
     - **Epic 9 (`Story 9.1`, statut `done`)** dans [`docs/planning-artifacts/epics.md`](file:///home/romain/Documents/Projects/ORCIA/docs/planning-artifacts/epics.md#L1988-L2020) : tiroir latéral droit `🔔 Notifications` (`420px`, `topbar-notifications-toggle` / `topbar-notifications-drawer`) dans [`FourZoneDirectionCShell.tsx`](file:///home/romain/Documents/Projects/ORCIA/packages/ui/src/primitives/FourZoneDirectionCShell.tsx#L301-L372).
   - **Différence fondamentale avec le Journal d'Activité (`📜 Journal d'Activité`, `/activity`)** :
     - Le **Centre des Notifications (`🔔 Notifications`)** est **prospectif, actionnable et centré sur l'attention immédiate de l'utilisateur** : il regroupe les prérequis de configuration manquants qui verrouillent certains modules (ex. aucun modèle d'IA configuré, aucune structure d'organisation définie, aucun espace de travail créé), les décisions ou arbitrages humains en attente de prise en charge, et les alertes d'attention directe avec bouton d'accès immédiat vers l'écran concerné.
     - Le **Journal d'Activité (`📜 Journal d'Activité`, `/activity`)** ([`ActivityLogExplorerView.tsx`](file:///home/romain/Documents/Projects/ORCIA/packages/ui/src/primitives/ActivityLogExplorerView.tsx), adossé au registre immuable `audit_ledger` / `audit_events` d'Epic 6 `Story 6.1`) est **rétrospectif, historique et probatoire** : il trace chronologiquement tous les événements survenus sur la plateforme dans le périmètre d'observation autorisé de l'utilisateur (`Plateforme entière`, `Direction / BU`, `Équipe`, `Espace de travail`), avec filtres par catégorie (`Sécurité`, `Configuration`, `Processus`, `Gouvernance`) et par sévérité.
   - **Amélioration concrète implémentée** : enrichir `FourZoneDirectionCShell.tsx` et `ShellContainer.tsx` pour que le tiroir `🔔 Notifications` ne reste plus un panneau statique vide mais affiche un badge compteur actif (`topbar-notifications-badge`), la liste dynamique des notifications actionnables (prérequis d'amorçage Jour 0 expliquant pourquoi tel menu est grisé + exécutions/décisions en cours) avec bouton d'action directe (`onSelectNotification`), ainsi qu'un encart explicatif distinguant clairement le Centre des Notifications du Journal d'Activité avec lien direct vers `/activity`.

2. **Volet 2 — Sémantique « Équipe » dans la Gestion de l'Organisation vs « Espace de Travail »** :
   - **Problème identifié** : Dans `Configuration > Utilisateurs, Rôles & Accès` ([`SettingsOrganizationUnitsBlock.tsx`](file:///home/romain/Documents/Projects/ORCIA/apps/web/src/routes/SettingsOrganizationUnitsBlock.tsx), [`SettingsIamOrganizationSection.tsx`](file:///home/romain/Documents/Projects/ORCIA/apps/web/src/routes/SettingsIamOrganizationSection.tsx)) et dans plusieurs sélecteurs de portée ([`SettingsPacksSection.tsx`](file:///home/romain/Documents/Projects/ORCIA/apps/web/src/routes/SettingsPacksSection.tsx), [`ShellContainer.tsx`](file:///home/romain/Documents/Projects/ORCIA/apps/web/src/components/ShellContainer.tsx), [`contextualHelpCatalog.ts`](file:///home/romain/Documents/Projects/ORCIA/apps/web/src/components/contextualHelpCatalog.ts)), le niveau hiérarchique d'organisation `level: "TEAM"` était libellé `Espace` ou `Espace (Équipe)` (`Directions / BU & Espaces`), créant une confusion directe avec les **Espaces de Travail** (`📦 Mes Espaces`, `/workspaces`).
   - **Règle d'ubiquitous language appliquée** :
     - **Structure d'Organisation (`Configuration > Organisation`)** : `Plateforme entière` (`GLOBAL`) $\rightarrow$ `Direction (BU)` (`BU`) $\rightarrow$ **`Équipe`** (`TEAM`).
     - **Espaces projets/produits (`📦 Mes Espaces`)** : **`Espace de travail`** (`WORKSPACE`).

3. **Volet 3 — Indicateur Point d'Exclamation Rouge Cerclé (`!`) aligné à droite & Infobulle Rouge sur tous les Boutons Grisés (`disabled`)** :
   - Lorsqu'un bouton est grisé (`disabled`), il doit afficher **dans son libellé, aligné à droite**, une icône de type **point d'exclamation dans un rond rouge (`!`)** (même gabarit circulaire `18px × 18px` que l'icône d'information `ⓘ` de `ContextualInfoTriggerButton`) ainsi qu'une **infobulle dont le texte est en rouge** expliquant la raison du verrouillage.
   - Dès que le bouton devient activable (`!disabled`), le badge rouge `!` et l'infobulle rouge **disparaissent intégralement du DOM**.
   - Ce comportement doit être vérifié et appliqué de manière transversale sur l'ensemble des boutons pouvant être grisés (`disabled`) dans `@orcia/ui` (`packages/ui`) et `apps/web`.

### 1.2 Analyse d'Impact GitNexus (Symboles & Flux)

- **Requêtes GitNexus exécutées (`repo: "/home/romain/Documents/Projects/ORCIA"`)** :
  - `gitnexus_query({query: "FourZoneDirectionCShell notifications drawer disabledMenuReasons", repo: "/home/romain/Documents/Projects/ORCIA"})` : identifie `FourZoneDirectionCShell.tsx`, `ShellContainer.tsx`, `shell_and_search_labels.ts` et `four-zone-shell-and-cockpit.test.tsx`.
  - `gitnexus_query({query: "SettingsOrganizationUnitsBlock SettingsIamOrganizationSection orgUnits", repo: "/home/romain/Documents/Projects/ORCIA"})` : identifie `SettingsOrganizationUnitsBlock.tsx`, `SettingsIamOrganizationSection.tsx`, `SettingsPacksSection.tsx`, `platformSetupStore.tsx` et `contextualHelpCatalog.ts`.
  - `gitnexus_impact({target: "FourZoneDirectionCShell", direction: "upstream", repo: "/home/romain/Documents/Projects/ORCIA"})` : `impactedCount: 1` (`apps/web/src/components/ShellContainer.tsx`, profondeur `d=1`, risque `LOW`).
  - `gitnexus_impact({target: "ContextualInfoTriggerButton", direction: "upstream", repo: "/home/romain/Documents/Projects/ORCIA"})` : `impactedCount: 5` (`FourZoneDirectionCShell.tsx`, `SettingsAiModelsSection.tsx`, `SettingsIamOrganizationSection.tsx`, `SettingsOrganizationUnitsBlock.tsx`, `SettingsPacksSection.tsx`, `SettingsSecondaryTabsSection.tsx`).

### 1.3 Opportunités de Factorisation & Contrôle de Volumétrie (Loi des 300–400 lignes)

- **Factorisation dans `@orcia/ui` (`packages/ui/src/components/DisabledButtonAlertIndicator.tsx`)** :
  - Plutôt que de dupliquer le badge `!` rouge cerclé et l'infobulle rouge dans les ~20 composants qui possèdent des boutons désactivables, nous créons une primitive réutilisable **`DisabledButtonAlertIndicator`** (exportée par `@orcia/ui`) adossée aux classes CSS sémantiques `.orcia-disabled-alert-badge` et `.orcia-disabled-alert-tooltip` dans [`packages/ui/src/styles/tokens.css`](file:///home/romain/Documents/Projects/ORCIA/packages/ui/src/styles/tokens.css) (zéro couleur hexadécimale hors `tokens.css`, utilisation exclusive de `var(--color-status-error)` et `var(--color-stale-bg)`).
  - Intégration directe dans `OrciaButton` ([`DesignSystemControls.tsx`](file:///home/romain/Documents/Projects/ORCIA/packages/ui/src/primitives/DesignSystemControls.tsx)), `PermissionGuard` ([`PermissionGuard.tsx`](file:///home/romain/Documents/Projects/ORCIA/packages/ui/src/primitives/PermissionGuard.tsx)), `FourZoneDirectionCShell` ([`FourZoneDirectionCShell.tsx`](file:///home/romain/Documents/Projects/ORCIA/packages/ui/src/primitives/FourZoneDirectionCShell.tsx)), `RgaaModalDialog` ([`RgaaModalDialog.tsx`](file:///home/romain/Documents/Projects/ORCIA/packages/ui/src/components/RgaaModalDialog.tsx)), `AgentsAndSkillsManagerView` ([`AgentsAndSkillsManagerView.tsx`](file:///home/romain/Documents/Projects/ORCIA/packages/ui/src/components/AgentsAndSkillsManagerView.tsx)), ainsi que l'ensemble des primitives `@orcia/ui` et écrans `apps/web` comportant des boutons `disabled`.
- **Contrôle de volumétrie (< 300–400 lignes)** :
  - [`SettingsIamOrganizationSection.tsx`](file:///home/romain/Documents/Projects/ORCIA/apps/web/src/routes/SettingsIamOrganizationSection.tsx) compte actuellement `394` lignes : nous maintenons sa taille sous le seuil de `395` lignes.
  - [`FourZoneDirectionCShell.tsx`](file:///home/romain/Documents/Projects/ORCIA/packages/ui/src/primitives/FourZoneDirectionCShell.tsx) compte `539` lignes : nous extrayons le rendu du tiroir du Centre des Notifications dans un sous-composant dédié ou gardons `FourZoneDirectionCShell.tsx` propre et modulaire.

### 1.4 Dette Technique Identifiée & Tickets Créés (`Story N.Ma` / `action_items`)

- Aucune dette technique structurelle différée : l'intégralité de la factorisation (`DisabledButtonAlertIndicator`, harmonisation sémantique `Équipe` vs `Espace de travail`, et enrichissement du Centre des Notifications) est traitée immédiatement dans ce lot.

---

## 2. Plan d'Implémentation

### 2.1 Schéma de Données & Migrations Alembic

- Aucune migration SQL requise : la table `task_notifications` (`0021_story_5_1_task_notifications_and_resource_leases.py`) et la table `audit_ledger` (`0001_initial_foundation.py`) existent déjà en PostgreSQL 18.

### 2.2 Noyau Métier Hexagonal (`packages/orcia-kernel` & `packages/orcia-core`) & Workers

- Aucun changement requis dans `packages/orcia-kernel` ou `packages/orcia-core` : l'énumération `ScopeLevel` distingue déjà `GLOBAL`, `BU`, `TEAM` (Équipe d'organisation) et `WORKSPACE` (Espace de travail).

### 2.3 Backend FastAPI (`apps/api`) & Client OpenAPI (`packages/api-client`)

- Aucun changement de contrat HTTP requis.

### 2.4 Interface SPA Vite + TanStack Router (`apps/web` & `packages/ui` — Direction C)

1. **Primitive `DisabledButtonAlertIndicator` & Styles Sémantiques (`packages/ui`)** :
   - Ajout dans [`packages/ui/src/styles/tokens.css`](file:///home/romain/Documents/Projects/ORCIA/packages/ui/src/styles/tokens.css) des classes `.orcia-disabled-alert-badge` (cercle `18px × 18px`, bordure et texte `var(--color-status-error)`, fond `var(--color-stale-bg)`, aligné à droite `margin-left: auto`) et `.orcia-disabled-alert-tooltip` (infobulle à texte rouge `color: var(--color-status-error)`, bordure `var(--color-status-error)`, fond `var(--color-stale-bg)`).
   - Création de [`packages/ui/src/components/DisabledButtonAlertIndicator.tsx`](file:///home/romain/Documents/Projects/ORCIA/packages/ui/src/components/DisabledButtonAlertIndicator.tsx) qui rend, uniquement lorsque `disabled === true`, le cercle rouge `!` aligné à droite (`data-testid="disabled-button-alert-icon"`) et l'infobulle rouge (`data-testid="disabled-button-alert-tooltip"`, `role="tooltip"`), et retourne `null` dès que `!disabled`.
   - Déploiement sur tous les boutons pouvant être grisés dans `packages/ui` et `apps/web` :
     - `FourZoneDirectionCShell.tsx` (`eight-menu-item-*`)
     - `DesignSystemControls.tsx` (`OrciaButton`)
     - `PermissionGuard.tsx` (`permission-guard-disabled-wrapper`)
     - `RgaaModalDialog.tsx` (`RgaaDialogFooterActions` submit button)
     - `AgentsAndSkillsManagerView.tsx` (`create-agent-submit-btn`, `create-skill-submit-btn`)
     - `CognitiveReviewBriefingGrid.tsx` (`inspect-hypotheses-btn`)
     - `PresenceClaimPill.tsx` (`claim-task-btn-*`, `release-claim-btn-*`)
     - `ProductLifecycleCard.tsx` (`lifecycle-btn-*`)
     - `WorkspaceControlCenter.tsx` (`launch-run-btn`, `attach-datasource-btn`)
     - `DurableWizardRunnerView.tsx` (`wizard-complete-step-btn`)
     - `HelpArticleGeneratorAndValidatorView.tsx` (`generate-and-attach-help-btn`)
     - `AssistantSpeedSelectorAndStreamView.tsx` (`assistant-three-speed-send-btn`)
     - `ChunkValidationCard.tsx` (`chunk-approve-btn-*`, `chunk-coedit-btn-*`, `chunk-challenge-btn-*`, `finalize-human-gate-btn`, `rubber-stamp-confirm-submit-btn`)
     - `CommandPaletteModal.tsx` (`command-palette-submit-btn`)
     - `HumanLedAnchorCard.tsx` (`human-anchor-submit-*`)
     - `PackBuilderProcessesStudioView.tsx` (`process1-create-pack-btn`)
     - `RemoteServiceTestBenchAndMcpExposureView.tsx` (`activate-remote-service-btn`)
     - `ScopedPromptBox.tsx` (`rag-source-toggle-*`)
     - `TopHeaderSearchCommand.tsx` (`cmdk-submit-btn`)
     - `UpstreamChallengeRewindModal.tsx` (`upstream-challenge-submit-btn`)
     - `CatalogExplorerPanel.tsx` (`promote-btn-*`)
     - `ShellContainer.tsx` (`first-boot-admin-submit-btn`)
     - `SettingsIamOrganizationSection.tsx` (`create-rbac-grant-btn`, `rbac-verb-toggle-*`)
2. **Enrichissement du Centre des Notifications vs Journal d'Activité (`FourZoneDirectionCShell.tsx`, `ShellContainer.tsx`, `shell_and_search_labels.ts`)** :
   - Ajout des types `UiNotificationCenterItem` dans `FourZoneDirectionCShell.tsx` et alimentation dynamique depuis `ShellContainer.tsx` (prérequis Jour 0 manquants qui verrouillent des menus + décisions/exécutions actives).
   - Affichage d'un badge compteur (`data-testid="topbar-notifications-badge"`) sur le bouton `🔔 Notifications`, cartes actionnables avec navigation directe (`onSelectNotification`), et encart explicatif comparant **Centre des Notifications** (actions & alertes personnelles/équipe) et **Journal d'Activité** (historique complet d'audit selon le périmètre d'observation) avec bouton d'accès vers `/activity`.
3. **Harmonisation Sémantique « Équipe » vs « Espace de Travail »** :
   - Mise à jour de `SettingsOrganizationUnitsBlock.tsx`, `SettingsIamOrganizationSection.tsx`, `SettingsPacksSection.tsx`, `ShellContainer.tsx`, `platformSetupStore.tsx`, `contextualHelpCatalog.ts` et `OrciaProductShowcaseSiteView.tsx`.

---

## 3. Bilan des Modifications & Résultats (Après Implémentation)

### 3.1 Fichiers Créés & Modifiés

| Fichier | Action | Rôle & Modifications |
| :--- | :--- | :--- |
| [`packages/ui/src/styles/tokens.css`](file:///home/romain/Documents/Projects/ORCIA/packages/ui/src/styles/tokens.css) | Modifié | Ajout des classes sémantiques `.orcia-disabled-alert-badge` (`18px × 18px`, cercle rouge aligné à droite `margin-left: auto`, `var(--color-status-error)`, `var(--color-stale-bg)`) et `.orcia-disabled-alert-tooltip` (infobulle à texte rouge `color: var(--color-status-error)`). |
| [`packages/ui/src/components/DisabledButtonAlertIndicator.tsx`](file:///home/romain/Documents/Projects/ORCIA/packages/ui/src/components/DisabledButtonAlertIndicator.tsx) | Créé | Primitive réutilisable `@orcia/ui` rendant le point d'exclamation rouge cerclé (`!`) aligné à droite et l'infobulle à texte rouge uniquement lorsque `disabled === true`, et retournant `null` dès que `disabled === false`. |
| [`packages/ui/src/index.ts`](file:///home/romain/Documents/Projects/ORCIA/packages/ui/src/index.ts) | Modifié | Export public de `DisabledButtonAlertIndicator`, `DisabledButtonAlertIndicatorProps`, `UiNotificationCenterItem` et `UiNotificationCenterItemKind`. |
| [`packages/ui/src/primitives/FourZoneDirectionCShell.tsx`](file:///home/romain/Documents/Projects/ORCIA/packages/ui/src/primitives/FourZoneDirectionCShell.tsx) | Modifié | Intégration de `DisabledButtonAlertIndicator` sur les 8 entrées de navigation (`eight-menu-item-*`), ajout du badge compteur `topbar-notifications-badge` et enrichissement du tiroir `🔔 Notifications` (`topbar-notifications-drawer`) avec cartes actionnables (`notification-item-*`), encart explicatif `notifications-vs-activity-log-box` et bouton `notifications-open-activity-log-btn` vers `/activity`. |
| [`packages/ui/src/primitives/DesignSystemControls.tsx`](file:///home/romain/Documents/Projects/ORCIA/packages/ui/src/primitives/DesignSystemControls.tsx) | Modifié | Intégration native de `DisabledButtonAlertIndicator` dans `OrciaButton` (`disabledReason` / `title`). |
| [`packages/ui/src/components/RgaaModalDialog.tsx`](file:///home/romain/Documents/Projects/ORCIA/packages/ui/src/components/RgaaModalDialog.tsx) | Modifié | Intégration de `DisabledButtonAlertIndicator` sur le bouton de soumission des modales RGAA (`RgaaDialogFooterActions`). |
| [`packages/ui/src/components/AgentsAndSkillsManagerView.tsx`](file:///home/romain/Documents/Projects/ORCIA/packages/ui/src/components/AgentsAndSkillsManagerView.tsx) | Modifié | Intégration de `DisabledButtonAlertIndicator` sur `create-agent-submit-btn` et `create-skill-submit-btn`. |
| [`packages/ui/src/primitives/PermissionGuard.tsx`](file:///home/romain/Documents/Projects/ORCIA/packages/ui/src/primitives/PermissionGuard.tsx) | Modifié | Intégration de `DisabledButtonAlertIndicator` dans `permission-guard-disabled`. |
| `packages/ui/src/primitives/*.tsx` & `packages/ui/src/shell/CatalogExplorerPanel.tsx` | Modifiés | Intégration transversale de `DisabledButtonAlertIndicator` sur tous les boutons pouvant être grisés (`PackBuilderProcessesStudioView`, `RemoteServiceTestBenchAndMcpExposureView`, `DurableWizardRunnerView`, `HelpArticleGeneratorAndValidatorView`, `HumanLedAnchorCard`, `UpstreamChallengeRewindModal`, `WorkspaceControlCenter`, `ProductLifecycleCard`, `PresenceClaimPill`, `CognitiveReviewBriefingGrid`, `ChunkValidationCard`, `AssistantSpeedSelectorAndStreamView`, `ScopedPromptBox`, `CommandPaletteModal`, `TopHeaderSearchCommand`, `CatalogExplorerPanel`). |
| [`apps/web/src/components/ShellContainer.tsx`](file:///home/romain/Documents/Projects/ORCIA/apps/web/src/components/ShellContainer.tsx) | Modifié | Intégration de `DisabledButtonAlertIndicator` sur `first-boot-admin-submit-btn`, construction dynamique de `notificationItems` (prérequis d'amorçage Jour 0 manquants + exécutions/décisions en attente), navigation vers `/activity` depuis le tiroir Notifications, et renommage du groupe `TEAM` en `Équipe`. |
| [`apps/web/src/routes/SettingsOrganizationUnitsBlock.tsx`](file:///home/romain/Documents/Projects/ORCIA/apps/web/src/routes/SettingsOrganizationUnitsBlock.tsx) | Modifié | Remplacement de « Espace (Équipe) » / « Espaces » par **« Équipe »** (`1. Structure de l'Organisation (Directions / BU & Équipes)`, `Équipe(s) rattachée(s)`). |
| [`apps/web/src/routes/SettingsIamOrganizationSection.tsx`](file:///home/romain/Documents/Projects/ORCIA/apps/web/src/routes/SettingsIamOrganizationSection.tsx) | Modifié | Intégration de `DisabledButtonAlertIndicator` sur `create-rbac-grant-btn` et remplacement de « Espace » par **« Équipe »** pour les unités d'organisation (`TEAM`), tout en conservant « Espace de travail » pour `WORKSPACE`. |
| [`apps/web/src/routes/SettingsPacksSection.tsx`](file:///home/romain/Documents/Projects/ORCIA/apps/web/src/routes/SettingsPacksSection.tsx), [`apps/web/src/components/platformSetupStore.tsx`](file:///home/romain/Documents/Projects/ORCIA/apps/web/src/components/platformSetupStore.tsx), [`apps/web/src/components/contextualHelpCatalog.ts`](file:///home/romain/Documents/Projects/ORCIA/apps/web/src/components/contextualHelpCatalog.ts), [`apps/web/src/i18n/locales/shell_and_search_labels.ts`](file:///home/romain/Documents/Projects/ORCIA/apps/web/src/i18n/locales/shell_and_search_labels.ts), [`packages/ui/src/primitives/OrciaProductShowcaseSiteView.tsx`](file:///home/romain/Documents/Projects/ORCIA/packages/ui/src/primitives/OrciaProductShowcaseSiteView.tsx) | Modifiés | Harmonisation de la terminologie « Équipe » vs « Espace de travail » et ajout des libellés bilingues (`fr`/`en`) du Centre des Notifications vs Journal d'Activité. |
| [`packages/ui/src/__tests__/four-zone-shell-and-cockpit.test.tsx`](file:///home/romain/Documents/Projects/ORCIA/packages/ui/src/__tests__/four-zone-shell-and-cockpit.test.tsx) & [`apps/web/src/__tests__/i18n-and-shell.test.tsx`](file:///home/romain/Documents/Projects/ORCIA/apps/web/src/__tests__/i18n-and-shell.test.tsx) | Modifiés | Ajout des tests unitaires et d'intégration couvrant `DisabledButtonAlertIndicator` (apparition quand `disabled=true`, disparition complète quand `disabled=false`), le Centre des Notifications vs Journal d'Activité, et la terminologie « Équipe » dans la gestion de l'Organisation. |

### 3.2 Métriques & Validation des Portes de Qualité (`AD-17` & Garde-Fous)

- **Lint, Typecheck & Tests TypeScript (`pnpm turbo run lint typecheck test`)** :
  - `@orcia/ui` : `15 passed (15)` fichiers de test (`56 passed` tests), `0` erreur ESLint/TypeScript.
  - `@orcia/api-client` : `1 passed (1)` fichier de test, `0` erreur.
  - `@orcia/web` : `4 passed (4)` fichiers de test (`35 passed` tests, incluant la parité récursive `fr.ts`/`en.ts`, l'isolation du Design System, l'audit `zero-dead-buttons-and-silent-catches-audit.test.tsx` et le nouveau test de bout en bout sur les 3 volets), `0` erreur.
- **Portes Python & Contrats d'Architecture (`AD-19`)** :
  - `.venv/bin/ruff check .` : `All checks passed!`.
  - `.venv/bin/lint-imports` : `5 kept, 0 broken` (`264 files, 1560 dependencies`).
- **Synchronisation du Site Vitrine (`/showcase` & `docs/site-catalog/index.html`)** :
  - `pnpm site:sync` et `pnpm site:check` exécutés avec succès (`0-diff`).
