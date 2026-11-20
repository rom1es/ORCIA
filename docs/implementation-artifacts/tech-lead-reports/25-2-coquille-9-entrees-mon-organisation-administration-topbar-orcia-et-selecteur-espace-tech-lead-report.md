# Story 25.2 — Coquille 9 Entrées (`Mon Organisation` & `Administration` 5 Onglets), TopBar `[O] ORCIA › Écran`, Sélecteur d'Espace Unique & Retrait `ⓘ` / `Active context`

- **Date** : 2026-11-20
- **Story / Clé Sprint** : `25-2-coquille-9-entrees-mon-organisation-administration-topbar-orcia-et-selecteur-espace` (`Epic 25`)
- **Capacité(s)** : `CAP-058`, `CAP-060`, `CAP-064`, `CAP-067`, `CAP-203` — classification : `feature` / `ux`
- **Auteur / Contexte** : Implémentation de la refonte structurelle de la coquille 4 Zones Direction C (`DESIGN.md`, `EXPERIENCE.md`) : passage du menu latéral à **9 entrées fixes** (`Mon Organisation` visible pour 100 % des utilisateurs authentifiés en lecture seule hors délégation, renommage de `Configuration` en `Administration` à 5 onglets stricts), placement du logo cliquable **`[O] ORCIA › <Écran>`** tout en haut à gauche de la `TopHeaderBar` (sans doublon dans la Sidebar), unification du double sélecteur en **un seul sélecteur d'`Espace actif` groupé** (`Personnel` + `Équipe / BU` + `Tous mes espaces`) persisté et câblé sur tous les écrans, et retrait des icônes flottantes `ⓘ` d'en-tête ainsi que du badge `Active context` / `Contexte actif`.
- **Commits associés** : `(en cours — pré-implémentation)`

---

## 1. Analyse du Besoin & Étude d'Impact Tech Lead (Pré-Implémentation)

### 1.1 Contexte & Problématique
- **Problème constaté** :
  1. La Sidebar gauche comporte actuellement **8 entrées** (`Cockpit`, `Mon Assistant`, `Mes Processus`, `Mes Agents`, `Mes Espaces`, `FinOps`, `Configuration`, `Aide`), masquant `/organization` derrière le 6e bouton de la barre d'onglets `/settings` et restreignant `organization` aux seuls `PLATFORM_ADMIN`, `BU_LEAD`, `TEAM_LEAD`. Les collaborateurs simples (`CONTRIBUTOR`, `OBSERVER`, `ONTOLOGY_LEAD`, `SECOPS`) ne peuvent pas consulter l'organigramme de leur entreprise via `GET /api/v1/org-units` ni via la Sidebar.
  2. L'entrée `Configuration` porte encore un libellé obsolète par rapport à la nomenclature cible **`Administration`** (`5` onglets stricts : `Comptes & Habilitations`, `Authentification`, `Modèles IA`, `Connecteurs`, `Packs Métiers`).
  3. **Bug 8** : Le logo `[O] ORCIA` est dupliqué dans `FourZoneSidebarRail` au-dessus du bouton de repli, tandis que la `TopHeaderBar` ne dispose pas d'un déclencheur `[O] ORCIA` cliquable tout en haut à gauche suivi immédiatement de `› <Écran>` ramenant à `/cockpit`.
  4. **Bug 7** : La Sidebar empile deux `<select>` (`sidebar-team-bu-selector` + `sidebar-workspace-selector`) sans persistance au rechargement `F5`, et plusieurs écrans métiers (`Mon Assistant`, `Mes Agents`, `Mes Processus`, `FinOps`, `Mes Espaces`) utilisent encore `workspaces[0]` en dur ou restent figés sur `"GLOBAL"` au lieu de suivre l'espace sélectionné. De plus, des occurrences de `"Plateforme Globale ORCIA"` codées en dur subsistent dans `platformSetupWorkspaces.ts` et `shellPresets.ts`.
  5. **Bug 5** : Le badge `cockpit-active-scope-badge` (`Active context: ...` / `Contexte actif : ...`) encombre le `Cockpit`, et de nombreuses icônes flottantes `ⓘ` (`<ContextualInfoTriggerButton />`) polluent les en-têtes des cartes principales d'écran alors que `? Aide` dans la `TopHeaderBar` est le point d'entrée unique Zone 4.
- **Comportement attendu** :
  - Sidebar à **9 entrées fixes** (`cockpit`, `assistant`, `processes`, `agents`, `spaces`, `organization`, `finops`, `configuration` labellisé `Administration`, `help`), sans dépassement vertical en `1440×900`.
  - `GET /api/v1/org-units` accessible à 100 % des utilisateurs authentifiés (avec `can_* = False` hors délégation et maintien strict des rejets `403` sur toute mutation non autorisée), et `/organization` affichant l'arbre en lecture seule avec bannière `organization-readonly-access-banner`.
  - `TopHeaderBar` affichant `[O] ORCIA › <Écran>` tout en haut à gauche (`data-testid="topbar-orcia-home-link"`), sans logo dans `FourZoneSidebarRail`.
  - Sélecteur unique `sidebar-workspace-selector` groupé par `<optgroup>` (`Personnel` + `<Équipe / BU>` + `Tous mes espaces`), persisté en `localStorage` et réinitialisé proprement après `pnpm db:reset`, câblé via `resolveEffectiveWorkspaceId` sur tous les écrans.
  - Suppression de `cockpit-active-scope-badge` et des `<ContextualInfoTriggerButton />` dans les en-têtes de cartes principales d'écran.

### 1.2 Exploration, Analyse d'Impact GitNexus, Factorisation & Dette Technique
- **Analyse d'Impact GitNexus (`npx gitnexus analyze`, `gitnexus_query`, `gitnexus_cypher`, `grep` exhaustif des appelants)** :
  - Index GitNexus rafraîchi sur la branche courante (`41 667` nœuds, `218 937` arêtes, `714` clusters, `1 487` flux).
  - Appelants directs identifiés :
    - `FourZoneSidebarRail` (`packages/ui/src/primitives/FourZoneSidebarRail.tsx`) : instancié uniquement par `FourZoneDirectionCShell.tsx` (et couvert par `story-23-5-sobriety-and-login-brand.test.tsx`, `story-17-1-wireframe-icons-and-shell-rail.test.tsx`).
    - `FourZoneTopHeaderSection` (`packages/ui/src/primitives/FourZoneTopHeaderSection.tsx`) : instancié uniquement par `FourZoneDirectionCShell.tsx`.
    - `buildDoubleScopeSelectorState` (`apps/web/src/components/shellScopeOptions.ts`) : appelé uniquement par `shellBreadcrumbAndScope.ts`.
    - `canAccessMyOrganization` (`apps/web/src/stores/settingsRbacResolver.ts`) : réexporté par `authSessionStore.ts`, appelé par `routes/organization.tsx` et `platformSetupAccostage.ts` (+ test `story-20-3`).
    - `list_org_units` / `filter_and_annotate_org_units` (`apps/api/src/orcia_api/routers/org_units.py` & `_org_units_delegation_helpers.py`) : filtre de lecture dans `_org_units_delegation_helpers.py:L176-181`, gardes de mutation intacts dans `org_delegation.py` et `_finops_auth_guards.py` (qui continue d'utiliser `compute_managed_org_scope` pour l'isolation `/activity` et FinOps).
- **Opportunités de Factorisation & Résorption de Dette Technique Naissante** :
  - Extraction d'un helper partagé `resolveEffectiveWorkspaceId(activeScopeId, workspaces, currentUserId)` dans `apps/web/src/components/shellScopeOptions.ts` pour supprimer les résolutions ad-hoc `workspaces[0]` dispersées dans `inbox`, `catalog`, `processes`, `finops`, `workspaces`, `gates`, `ShellFederatedSearchModal` et `useShellAutonomousSupervision`.
  - Remplacement de `buildDoubleScopeSelectorState` par `buildUnifiedScopeSelectorState` produisant des groupes typés (`Personnel`, `<Nom Équipe / Direction>`, `Tous mes espaces`) consommés à l'identique par `FourZoneSidebarRail` (Desktop) et `MobileShellNavigationDrawer` (Mobile).
  - Découpage des fichiers dépassant `350` lignes touchés par cette Story :
    - `packages/ui/src/primitives/DesignSystemControls.tsx` (`362` L $\rightarrow$ `< 310` L par extraction de `OrciaAlertBanner` dans `OrciaAlertBanner.tsx` avec réexport).
    - `apps/web/src/routes/settings.tsx` (`318` L $\rightarrow$ `< 290` L).
    - `apps/web/src/routes/SettingsAiModelsSection.tsx` (`423` L $\rightarrow$ `< 280` L par extraction du contrôleur `useAiModelsSectionController.ts`).
    - `apps/web/src/routes/SettingsPacksSection.tsx` (`385` L $\rightarrow$ `< 290` L par extraction de `useSettingsPacksController.ts`).
    - `apps/web/src/features/admin/connectors/EnterpriseConnectorsSettingsSection.tsx` (`386` L $\rightarrow$ `< 290` L par extraction de `useEnterpriseConnectorsController.ts`).
    - `apps/web/src/features/ontology/index.tsx` (`386` L $\rightarrow$ `< 320` L par extraction de `OntologyConceptCreateCard.tsx`).
    - `apps/web/src/features/workspaces/WorkspaceStudioCardsAndDetailView.tsx` (`490` L $\rightarrow$ `< 340` L par extraction de `WorkspaceStudioSummaryCard.tsx`).

---

## 2. Plan d'Implémentation

### 2.1 Schéma de Données & Migrations Alembic
- Aucune modification de schéma PostgreSQL 18 requise pour cette Story (les tables `org_units`, `workspaces`, `iam_accounts` et `users` disposent déjà des colonnes nécessaires).

### 2.2 Noyau Métier Hexagonal, Orchestration & Workers (`packages/orcia-core/`)
- `packages/orcia-core/src/orcia_core/permissions/org_delegation_scope.py` & `org_delegation.py` :
  - Conservation intégrale de `compute_managed_org_scope` (`governed_bu_ids`, `direct_led_team_ids`, `editable_unit_ids`, `led_bu_root_ids`) et de `compute_org_unit_capabilities` afin de préserver l'isolation stricte des mutations (`403`) et des journaux `/activity` & `FinOps`.

### 2.3 Couche Backend API, Sécurité & Contrats (`apps/api/`, `packages/api-client/`)
- `apps/api/src/orcia_api/routers/_org_units_delegation_helpers.py` (`filter_and_annotate_org_units`) :
  - Suppression du filtre d'exclusion de lecture (`if not scope.is_platform_admin and not scope.is_global_reader and s.id not in scope.visible_unit_ids: continue`) afin que `GET /api/v1/org-units` retourne l'arbre organisationnel complet à tout utilisateur authentifié (`CONTRIBUTOR`, `OBSERVER`, `SECOPS`, `ONTOLOGY_LEAD`, `TEAM_LEAD`, `BU_LEAD`, `PLATFORM_ADMIN`), avec `can_edit=False, can_create_child=False, can_delete=False, can_manage_members=False, can_manage_ontology_leads=False, can_invite_users=False` sur tout nœud sans délégation.
  - Maintien strict de tous les gardes `403` (`enforce_org_create_delegation`, `enforce_org_patch_delegation`, `enforce_org_delete_delegation`, `assert_can_invite_org_user`).
- Contrats OpenAPI : aucun changement de schéma OpenAPI (`OrgUnitsListResponse` et `OrgUnitResponse` inchangés).

### 2.4 Interface Utilisateur & Expérience (`packages/ui/`, `apps/web/`)
1. **Menu 9 entrées & `Administration`** :
   - `packages/ui/src/primitives/FourZoneShellTypes.ts` & `packages/ui/src/components/icons/iconRegistry.ts` : ajout de `"organization"` dans `EightFixedMenuKey`, `ORCIA_EIGHT_MENU_ICON_NAMES` (`"organizationBu"`), et `DEFAULT_EIGHT_FIXED_MENU_ENTRIES` juste après `spaces`.
   - `apps/web/src/i18n/locales/shell_and_search_labels.ts`, `admin_and_studio_labels.ts`, `fr.ts`, `en.ts`, `epic18_sources_labels.ts` : ajout de `organization` (`"Mon Organisation"` / `"My Organization"`), renommage de `configuration` en `"Administration"`, mise à jour des titres/sous-titres `/settings` pour `"Administration de la plateforme"` / `"Platform Administration"`.
   - `apps/web/src/stores/settingsRbacResolver.ts` : ajout de `canMutateMyOrganization(session)` (réservé `PLATFORM_ADMIN`, `BU_LEAD`, `BU_DIRECTOR`, `TEAM_LEAD` hors `readOnlyObserver`) et ouverture de `canAccessMyOrganization` à tous les utilisateurs authentifiés.
   - `apps/web/src/components/ShellContainer.tsx`, `shellScopeOptions.ts`, `shellPresets.ts`, `shellBreadcrumbBuilders.ts`, `platformSetupAccostage.ts` : visibilité de `organization` pour 100 % des authentifiés (désactivé uniquement en pré-admin Jour 0 `!adminCreated`), maintien du masquage de `configuration`/`Administration` hors `PLATFORM_ADMIN | SECOPS`, fil d'Ariane direct `Mon Organisation` sur `/organization`.
   - `apps/web/src/routes/organization.tsx` & `SettingsOrganizationUnitsBlock.tsx` : affichage de l'arbre en lecture seule avec bannière `organization-readonly-access-banner` lorsque l'utilisateur n'a aucun droit de mutation (`!canMutate`), et boutons de mutation désactivés selon `can_*`.
   - `apps/web/src/routes/settings.tsx` (`< 290` L) : retrait du 6e bouton `settings-open-organization-link` de `settings-domain-tabs` pour ne garder strictement que 5 onglets, tout en conservant la redirection `/settings?tab=organization -> /organization`.
2. **Bug 8 — TopBar `[O] ORCIA › <Écran>` & retrait doublon Sidebar** :
   - `packages/ui/src/primitives/FourZoneSidebarRail.tsx` : suppression du bloc `sidebar-brand-logo` en haut de la Sidebar ; conservation exclusive du contrôle de repli (`sidebar-rail-toggle-btn`).
   - `packages/ui/src/primitives/FourZoneTopHeaderSection.tsx` & `FourZoneDirectionCShell.tsx` : ajout du lien/bouton cliquable `[O] ORCIA` (`data-testid="topbar-orcia-home-link"`) tout à gauche de la `TopHeaderBar` naviguant vers `/cockpit`, suivi du chevron `›` et du fil d'Ariane de l'écran ouvert sans duplication de `"ORCIA"`.
3. **Bug 7 — Sélecteur unique d'`Espace actif` groupé & câblage multi-écrans** :
   - `packages/ui/src/primitives/FourZoneSidebarRail.tsx` & `MobileCompanionBottomBar.tsx` : remplacement du double `<select>` par un unique `<select data-testid="sidebar-workspace-selector">` structuré en `<optgroup>` (`Personnel`, `<Nom Équipe / BU>`, option `Tous mes espaces` `scope-global`).
   - `apps/web/src/components/useShellContainerState.ts`, `shellScopeOptions.ts`, `platformSetupWorkspaces.ts`, `shellPresets.ts` : persistance `localStorage` (`orcia.shell.active_scope_id.v1`) avec réinitialisation propre si l'ID stocké n'existe plus après `db:reset` ; purge de `"Plateforme Globale ORCIA"` codée en dur au profit des clés i18n ; extraction de `resolveEffectiveWorkspaceId(activeScopeId, workspaces, currentUserId)` et câblage dans `useInboxPanelController.ts`, `catalog/index.tsx`, `ProcessesHubPage.tsx` (+ `WorkflowFiveBlocksCanvas.tsx`), `useFinopsDashboardController.ts`, `workspaces/index.tsx`, `ShellFederatedSearchModal.tsx`, `useShellAutonomousSupervision.ts`.
4. **Bug 5 — Retrait `Active context` & icônes `ⓘ` d'en-tête** :
   - Suppression de `cockpit-active-scope-badge` dans `apps/web/src/features/cockpit/index.tsx`.
   - Suppression de `<ContextualInfoTriggerButton />` dans `DesignSystemControls.tsx` (`OrciaSectionCard`) et dans tous les en-têtes de cartes principales des écrans métiers (`cockpit`, `SettingsAiModelsSection`, `SettingsOrganizationUnitsBlock`, `ProcessesHubPage`, `WorkflowStudioHeaderBar`, `SavedConversationsAndThreadView`, `WorkspaceStudioCardsAndDetailView`, `WorkspaceSourcesRagTab`, `WorkspaceGlossaryAndOntologyTab`, `FinopsGovernanceDashboardView`, `FinopsRemoteMcpServicesTab`, `FinopsHumanMasteryTab`, `FinopsAutonomousGovernanceSection`, `ActivityLogExplorerView`, `AssistantFoldersAndCollaborativeThreadView`, `ModuleWorkspaceView`, `ontology/index.tsx`, `SettingsPacksSection`, `EnterpriseConnectorsSettingsSection`, `IamNativeRoleMatrixCard`, `OrciaDocumentationProcessCard`, `SimplifiedProcessBuilderSection`).

### 2.5 Analyse d'Impact sur la Pyramide des Tests (`AD-17` — Couches 1 à 5 + Sécurité)
*(Les modifications de tests seront prises en charge par un sous-agent QA indépendant après l'implémentation applicative.)*
- **Couche 1a (Python `tests/unit/`)** : `tests/unit/test_story_20_1_org_delegation_and_audit_scope.py` (vérifier `GET /api/v1/org-units` pour tous les rôles avec `can_* = False` hors délégation et `403` sur mutations hors périmètre).
- **Couche 1b (Vitest `packages/ui/src/__tests__/` & `apps/web/src/__tests__/`)** : `four-zone-shell-and-cockpit.test.tsx`, `story-17-1-wireframe-icons-and-shell-rail.test.tsx`, `story-23-5-sobriety-and-login-brand.test.tsx`, `icon-registry-centralization.test.tsx`, `direction-c-shell-mobile-companion-and-dynamic-help.test.tsx`, `story-20-1-mon-organisation-and-scoped-activity.test.tsx`, `story-23-5-sobriety-and-citations-wiring.test.tsx`, `i18n-and-shell.test.tsx`, `shell-desktop-viewport-scroll-lock-audit.test.tsx`, `scope-switcher-and-org-sync.test.tsx`.
- **Couche 2 (`tests/integration/api/`)** : `test_story_20_1_org_delegation_and_audit_postgres18.py`.
- **Couche 3 (Contrats & Statique)** : `ruff check`, `mypy --strict`, `lint-imports`, `scripts/export_openapi.py --check`, `pnpm turbo run lint typecheck`.
- **Couche 5 (E2E Playwright `apps/web/e2e/`)** : `directionCSobrietyAssertions.ts`, `15-organization-iam-secops-inbox-and-observer.spec.ts`, `07-spaces-org-and-workspace-persistence.spec.ts`, `shell.spec.ts`.

---

## 3. Bilan des Modifications & Résultats (Post-Implémentation)

### 3.1 Fichiers créés et modifiés (`wc -l`)

#### Backend (`apps/api`)
- `apps/api/src/orcia_api/routers/_org_units_delegation_helpers.py` (`283` L) : ouverture en lecture de l'arbre complet sur `GET /api/v1/org-units` pour tout utilisateur authentifié (`can_* = False` hors délégation, mutations strictement protégées en `403`).

#### Design System (`packages/ui`)
- `packages/ui/src/components/icons/iconRegistry.ts` (`291` L) : ajout de l'icône `organization: "organizationBu"` dans `ORCIA_EIGHT_MENU_ICON_NAMES`.
- `packages/ui/src/primitives/FourZoneShellTypes.ts` (`177` L) : ajout de `"organization"` dans `EightFixedMenuKey` et `DEFAULT_EIGHT_FIXED_MENU_ENTRIES` juste après `spaces`, ajout de `UnifiedScopeOptionGroup`, props du sélecteur unifié et `onNavigateHome`.
- `packages/ui/src/index.ts` (`760` L) : export de `UnifiedScopeOptionGroup`.
- `packages/ui/src/primitives/useFourZoneShellHotkeys.ts` (`29` L, créé) : extraction du hook raccourcis clavier depuis `FourZoneDirectionCShell.tsx`.
- `packages/ui/src/primitives/FourZoneDirectionCShell.tsx` (`344` L) : passage des props `onNavigateHome` et sélecteur unifié au rail et à la topbar.
- `packages/ui/src/primitives/FourZoneSidebarRail.tsx` (`290` L) : suppression du logo `sidebar-brand-logo` en haut du rail, conservation du contrôle de repli, remplacement des 2 sélecteurs par le `<select data-testid="sidebar-workspace-selector">` groupé par `<optgroup>`, réglage de densité `py-1.5` pour la tenue en `1440×900`.
- `packages/ui/src/primitives/MobileCompanionBottomBar.tsx` (`272` L) : alignement du tiroir mobile sur le sélecteur unifié et les 9 entrées.
- `packages/ui/src/primitives/FourZoneTopHeaderSection.tsx` (`317` L) : ajout tout à gauche de `topbar-orcia-home-link` (`[O] ORCIA`) cliquable vers `/cockpit` suivi de `›` et du fil d'Ariane dédupliqué.
- `packages/ui/src/primitives/OrciaAlertBanner.tsx` (`77` L, créé) : extraction depuis `DesignSystemControls.tsx`.
- `packages/ui/src/primitives/DesignSystemControls.tsx` (`281` L) : retrait de `<ContextualInfoTriggerButton />` dans `OrciaSectionCard` et ré-export de `OrciaAlertBanner`.
- `packages/ui/src/primitives/finops/FinopsGovernanceDashboardView.tsx` (`288` L), `FinopsRemoteMcpServicesTab.tsx` (`215` L), `FinopsHumanMasteryTab.tsx` (`293` L), `FinopsAutonomousGovernanceSection.tsx` (`276` L), `ActivityLogExplorerView.tsx` (`337` L), `AssistantFoldersAndCollaborativeThreadView.tsx` (`295` L) : suppression des icônes flottantes `ⓘ` des en-têtes de cartes principales.

#### Frontend SPA (`apps/web`)
- `apps/web/src/i18n/locales/shell_and_search_labels.ts` (`648` L), `admin_and_studio_labels.ts` (`250` L), `epic18_sources_labels.ts` (`300` L), `fr.ts` (`355` L), `en.ts` (`355` L) : ajout de l'entrée `organization`, renommage visible `Configuration` $\rightarrow$ `Administration`, libellés du sélecteur unifié d'espace.
- `apps/web/src/stores/settingsRbacResolver.ts` (`169` L), `authSessionStore.ts` (`349` L), `platformSetupAccostage.ts` (`217` L) : ajout de `canMutateMyOrganization`, ouverture de `canAccessMyOrganization` à tous les utilisateurs authentifiés.
- `apps/web/src/components/platformSetupWorkspaces.ts` (`257` L), `shellPresets.ts` (`199` L), `shellBreadcrumbBuilders.ts` (`175` L), `shellZone4HelpWiring.tsx` (`106` L) : purge de `"Plateforme Globale ORCIA"` codé en dur, fil d'Ariane dédupliqué et découplage `/organization` de `/configuration`.
- `apps/web/src/components/shellUnifiedScope.ts` (`119` L, créé), `shellScopeOptions.ts` (`250` L), `shellBreadcrumbAndScope.ts` (`213` L), `useShellContainerState.ts` (`178` L), `ShellContainer.tsx` (`275` L) : `resolveEffectiveWorkspaceId`, `buildUnifiedScopeSelectorState`, persistance `localStorage` et réinitialisation si ID obsolète après `db:reset`, désactivation Jour 0 pré-admin de `organization`.
- `apps/web/src/routes/settings.tsx` (`278` L) : retrait du 6e lien `settings-open-organization-link` (`5` onglets strictement dans `settings-domain-tabs`) et titre/description `Administration`.
- `apps/web/src/routes/organization.tsx` (`83` L), `apps/web/src/routes/SettingsOrganizationUnitsBlock.tsx` (`221` L) : affichage en lecture seule (`organization-readonly-access-banner`) hors délégation, masquage/désactivation des mutations selon `can_*`, retrait de `ⓘ`.
- `apps/web/src/routes/SettingsAiModelsSection.tsx` (`153` L), `useAiModelsSectionController.ts` (`244` L, créé), `SettingsPacksSection.tsx` (`344` L), `settingsPacksPresets.ts` (`34` L, créé) : retrait de `ⓘ` et découpage sous `350` L.
- `apps/web/src/features/cockpit/index.tsx` (`286` L) : retrait du badge `cockpit-active-scope-badge` et des `ⓘ` en en-tête.
- `apps/web/src/features/inbox/useInboxPanelController.ts` (`328` L), `InboxNotificationsCenterView.tsx` (`260` L), `SavedConversationsAndThreadView.tsx` (`325` L) : câblage `resolveEffectiveWorkspaceId` et retrait des `ⓘ`.
- `apps/web/src/features/catalog/index.tsx` (`252` L) : câblage `resolveEffectiveWorkspaceId` et libellé `Administration`.
- `apps/web/src/features/processes/ProcessesHubPage.tsx` (`315` L), `ProcessStudioAndPackAuthoringSection.tsx` (`233` L), `execution/InteractiveRunDrawer.tsx` (`280` L), `execution/useInteractiveProcessRunController.ts` (`349` L), `execution/interactiveRunFormatters.ts` (`89` L), `studio/WorkflowFiveBlocksCanvas.tsx` (`288` L), `studio/WorkflowStudioHeaderBar.tsx` (`249` L), `studio/WorkflowOrchestrationModeSelector.tsx` (`168` L) : câblage `resolveEffectiveWorkspaceId` et retrait des `ⓘ`.
- `apps/web/src/features/finops/useFinopsDashboardController.ts` (`297` L) : synchronisation de `selectedScope` avec `activeScopeId` au montage et à chaque sélection dans la barre latérale.
- `apps/web/src/features/workspaces/index.tsx` (`233` L), `WorkspaceStudioCardsAndDetailView.tsx` (`241` L), `WorkspaceStudioSummaryCard.tsx` (`264` L, créé), `WorkspaceSourcesRagTab.tsx` (`319` L), `WorkspaceGlossaryAndOntologyTab.tsx` (`340` L) : câblage `resolveEffectiveWorkspaceId`, extraction de carte sous `350` L et retrait des `ⓘ`.
- `apps/web/src/components/ShellContextualHelpColumn.tsx` (`169` L, correctif QA) : suppression du verrou conditionnel `activeHelpSectionId ? ... : undefined` pour conserver en Zone 4 les sections contextuelles ciblées par route (`iam-role-grants`, `ai-models-overview`, `packs-overview`, `audit-overview`) même sans bouton `ⓘ` flottant dans les cartes.
- `apps/web/src/features/admin/organization/InviteOrganizationUserModal.tsx` (`251` L, correctif QA) : garde `wasOpenRef` dans l'effet d'initialisation de la modale d'invitation afin que le rafraîchissement de référence de `invitableUnits` (polling/SSE en arrière-plan) n'efface jamais `displayName` ni `email` en cours de saisie.
- `apps/web/src/features/gates/index.tsx` (`108` L), `OrciaDocumentationProcessCard.tsx` (`295` L), `orciaDocProcessTemplates.ts` (`114` L, créé), `admin/index.tsx` (`89` L), `admin/iam/IamNativeRoleMatrixCard.tsx` (`209` L), `admin/connectors/EnterpriseConnectorsSettingsSection.tsx` (`298` L), `admin/connectors/useEnterpriseConnectorsController.ts` (`113` L, créé), `ontology/index.tsx` (`189` L), `ontology/useOntologyFeatureController.ts` (`172` L, créé), `components/ModuleWorkspaceView.tsx` (`111` L), `SimplifiedProcessBuilderSection.tsx` (`177` L), `ShellFederatedSearchModal.tsx` (`211` L), `useShellAutonomousSupervision.ts` (`78` L) : câblage `resolveEffectiveWorkspaceId`, retrait des `ⓘ`, libellés `Administration` et découpage `< 350` L.

#### Tests Créés / Mis à Jour (`QA Indépendant`)
- Backend Python :
  - `tests/unit/test_story_20_1_org_delegation_and_audit_scope.py` (mis à jour pour lecture seule arbre `GET /api/v1/org-units` hors délégation + `403` mutations)
  - `tests/unit/test_story_25_2_org_units_read_access.py` (créé — `CONTRIBUTOR`, `OBSERVER`, `ONTOLOGY_LEAD`, `SECOPS` en lecture seule avec `can_* == False` et `403` sur mutations/invitations)
  - `tests/security/test_story_20_1_delegation_and_audit_isolation.py` (mis à jour — isolation lecture seule + rejet `READ_ONLY_OBSERVER`)
  - `tests/integration/api/test_story_20_1_org_delegation_and_audit_postgres18.py` (mis à jour — cas réel `CONTRIBUTOR` & `READ_ONLY_OBSERVER` contre PG18 `create_app()` sans `dependency_overrides`)
- Frontend Vitest (`@orcia/ui` & `@orcia/web`) :
  - `@orcia/ui` : `four-zone-shell-and-cockpit.test.tsx`, `icon-registry-centralization.test.tsx`, `story-17-1-wireframe-icons-and-shell-rail.test.tsx`, `story-23-5-sobriety-and-login-brand.test.tsx`
  - `@orcia/web` : `setup/orgUnitsReadAndInviteHandlers.ts`, `design-system-look-and-feel-isolation.test.tsx`, `direction-c-shell-mobile-companion-and-dynamic-help.test.tsx`, `i18n-and-shell.test.tsx`, `shell-desktop-viewport-scroll-lock-audit.test.tsx`, `story-17-1-settings-5-tabs-and-rbac.test.tsx`, `story-20-1-mon-organisation-and-scoped-activity.test.tsx`, `story-23-3-zone4-route-fidelity-and-no-unauth-resolve.test.tsx`, `story-24-5-accostage-routes-navigation-and-day0.test.tsx`
  - `apps/web/src/__tests__/story-25-2-shell-9-items-org-admin-and-unified-scope.test.tsx` (créé sous `<RouterProvider>` réel — 9 entrées, `[O] ORCIA`, `Mon Organisation` lecture seule vs `Administration` 5 onglets, sélecteur unifié `sidebar-workspace-selector` + F5 + propagation + stabilité saisie `InviteOrganizationUserModal`)
- E2E Playwright (`apps/web/e2e/`) : `support/directionCSobrietyAssertions.ts`, `support/processAndAssistantHelpers.ts`, `shell.spec.ts`, `07-spaces-org-and-workspace-persistence.spec.ts`, `15-organization-iam-secops-inbox-and-observer.spec.ts`, `19-orchestration-whatif-replay-and-gates.spec.ts`, `21-assistant-citations-v5-audit-help-showcase.spec.ts`.

### 3.2 Résultats Chiffrés, Portes Statiques & Couverture (`AD-17`)
- **Couverture ciblée Story 25.2 (`pytest ... --cov=orcia_core.permissions.org_delegation --cov=... --cov-fail-under=90`, 17 tests unitaires, sécurité & intégration PG18 réel)** : **`95.63 %`** (`349` instructions / `86` branches : `models.py` `99 %`, `org_delegation.py` `93 %`, `org_delegation_invitations.py` `100 %`, `org_delegation_scope.py` `95 %`, `role_matrix.py` `94 %`).
- **Suite Python globale (`tests/unit tests/security tests/evals`)** : **`1041 passed`** (`0` échec, `0` skipped — couverture globale sur `orcia-core` seul hors `tests/integration` : `83.64 %` car les adaptateurs `_internal/sql_*.py` sont couverts en Couche 2).
- **Couche 2 — Intégration PG18 réelle (`tests/integration/api/test_story_20_1_org_delegation_and_audit_postgres18.py`)** : **`1 passed`** (`28.55s`, `create_app()` + `lifespan` réel sur `pgvector/pgvector:pg18`, `0` override).
- **Couche 1b & 3 JS/TS (`pnpm turbo run lint typecheck test`)** : **`9 successful, 9 total`** (`@orcia/api-client` : `3/3` fichiers `20/20`, `@orcia/ui` : `34/34` fichiers `136/136`, `@orcia/web` : `63/63` fichiers `248/248`, ESLint + `tsc --noEmit` + `check-feature-boundaries` à `0` erreur).
- **Qualité statique & Architecture** :
  - `.venv/bin/ruff check . && .venv/bin/ruff format --check .` : **PASS** (`All checks passed!`, `1328 files already formatted`)
  - `.venv/bin/mypy --strict packages/orcia-core packages/orcia-connectors apps/api apps/worker` : **PASS** (`Success: no issues found in 577 source files`)
  - `.venv/bin/lint-imports` : **PASS** (`Contracts: 5 kept, 0 broken.`, `620` files, `4481` dependencies)
  - `.venv/bin/python scripts/export_openapi.py --check` : **PASS** (`exit code 0`, `0-diff`)
  - `lint_spine.py` : **PASS** (`ok: true, total_findings: 0`)
- **Couche 5 — E2E Playwright (`--project=desktop-cockpit`, `ORCIA_E2E_CAMPAIGN_DIR=/tmp/orcia-e2e-story-25-2`)** sur `shell.spec.ts`, `00-stack-smoke.spec.ts`, `01-day0-boot-and-f5-persistence.spec.ts`, `07-spaces-org-and-workspace-persistence.spec.ts`, `09-pack-builder-and-contextual-help.spec.ts`, `12-finops-and-audit-provenance.spec.ts` et `15-organization-iam-secops-inbox-and-observer.spec.ts` : **`17 passed, 1 skipped (test mobile-only dans 12-finops), 0 failed (3.8m)`**.

### 3.3 Validation Verticale (`AD-17` & Garde-Fous)
1. **Couche 1a & Sécurité** : L'ouverture de `GET /api/v1/org-units` retourne l'arbre organisationnel en lecture seule avec tous les drapeaux `can_*` à `False` pour `CONTRIBUTOR`, `OBSERVER`, `ONTOLOGY_LEAD` et `SECOPS`, tandis que toutes les routes de mutation et d'invitation renvoient `403` (`ERR_OBSERVER_MODE_READ_ONLY` en mode observateur).
2. **Couche 1b & Garde-Fous UI** : Audit complet sous `<RouterProvider>` réel (`0` court-circuit `isJsdom`), validation des `9` entrées fixes, de `[O] ORCIA`, de l'isolation 5 onglets d'`Administration` (1 seule ligne desktop), du sélecteur unifié `sidebar-workspace-selector` (survie F5 + propagation), et du maintien des sections d'aide contextuelle Zone 4 et de la saisie dans la modale d'invitation.
3. **Couche 2 & Couche 5** : Vérification bout-en-bout sur PostgreSQL 18 + Redis 7.4 éphémères (`17/17` scénarios Desktop verts) : clic `[O] ORCIA` $\rightarrow$ `/cockpit`, `0` débordement vertical (`1440×900`), `Mon Organisation` accessible en lecture seule à `OBSERVER`, sélection et persistance F5 de `sidebar-workspace-selector` en `/spaces` $\rightarrow$ `/finops` $\rightarrow$ `/spaces`.
4. **Clôture Documentaire & Catalogue** : Mise à jour de `capabilities.yaml` (`CAP-058`, `CAP-060`, `CAP-203`), `sprint-status.yaml` (`done`), `tech-lead-reports/README.md`, `sync_site_catalog.py --check` (`0` erreur) et `check_implementation_docs.py` (`0` erreur).
