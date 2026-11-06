# 2026-11-06 — Rattachement Multi-Équipes, Espaces de Travail Privés Facturés à l'Équipe, Chaîne de Verrouillage Stricte des Appels IA & Sélecteur de Contexte à 3 Groupes

> **Convention de nommage du fichier (Obligatoire — créé AVANT toute modification de code)** :
> - Demande d'ajustement, correctif ou évolution hors Story : `docs/implementation-artifacts/tech-lead-reports/2026-11-06-rattachement-equipe-facturation-espaces-prives-et-selecteur-contexte-tech-lead-report.md`

- **Date** : 2026-11-06
- **Story / Clé Sprint** : `2026-11-06-rattachement-equipe-facturation-espaces-prives-et-selecteur-contexte` (`Post-Epic 12 / Gouvernance FinOps, Modèle Métier & Sélecteur de Contexte`)
- **Auteur / Contexte** : Winston (Architecte Système) & Sally (UX/UI Designer) — Implémentation de la synthèse validée avec l'utilisateur : (1) Parcours du 1ᵉʳ Administrateur au Jour 0 en 2 étapes (Option 1) avec rattachement multi-équipes (`memberTeamIds`), (2) Modèle relationnel Multi-Équipes par Utilisateur et Multi-Espaces par Équipe avec Espaces de Travail Privés (`PRIVATE_USER`), Collectifs (`STANDARD`) et Confidentiels (`CONFIDENTIAL_RESTRICTED`) systématiquement rattachés à une Équipe pour la facturation FinOps (`ownerOrgUnitId` — Option 2), (3) Chaîne de verrouillage stricte « Zéro appel LLM sans Équipe de facturation + Espace de Travail + Modèle IA » avec indicateur `!` rouge cerclé et infobulle rouge (`DisabledButtonAlertIndicator`), (4) Refonte du sélecteur de contexte en haut de l'écran (`TopHeaderBar`) en 3 groupes explicites (`🔒 Mes Espaces Privés`, `👥 Mes Équipes & Espaces`, `🏢 Supervision Organisation`) et filtrage contextuel dans les écrans, et (5) Enrichissement de la FAQ d'architecture (`architecture.md`, `faq-architecture-modele-metier.md`).
- **Commits associés** : branche `feat/team-billing-private-workspaces-and-scope-switcher`

---

## 1. Analyse du Besoin & Étude d'Impact Tech Lead (Pré-Implémentation)

### 1.1 Contexte & Problématique
- **Problématique métier & gouvernance FinOps** :
  1. **Rattachement Multi-Équipes & Parcours Jour 0 du 1ᵉʳ Administrateur (Option 1 en 2 étapes)** :
     - Au 1ᵉʳ démarrage (Jour 0), la modale `first-boot-admin-setup-modal` crée uniquement l'identité technique de l'Administrateur de la plateforme (`Nom complet`, `Adresse e-mail`, `Mot de passe`) avec `memberTeamIds: []` (`0` équipe rattachée).
     - En conséquence, même l'Administrateur de la plateforme ne peut effectuer aucun appel LLM facturable tant qu'au moins une **Équipe (`TEAM`)** n'a pas été créée dans `⚙️ Configuration > Organisation & Habilitations` et que son compte n'y est pas rattaché (case à cocher « Rattacher mon compte à cette équipe (facturation & accès) » cochée par défaut lors de la création d'une Équipe, et bouton 1-clic sur chaque Équipe existante pour se rattacher / retirer son rattachement). Un utilisateur peut appartenir à **plusieurs Équipes simultanément** (`memberTeamIds`).
  2. **Espaces de Travail Privés (`PRIVATE_USER`) vs Collectifs (`STANDARD`) vs Confidentiels (`CONFIDENTIAL_RESTRICTED`) — Option 2 FinOps** :
     - Un utilisateur peut avoir besoin d'un espace de travail personnel/privé (`PRIVATE_USER` : brouillons, explorations, dossiers privés) visible uniquement par lui, en plus des espaces collectifs de ses équipes (`STANDARD`) et des espaces confidentiels isolés (`CONFIDENTIAL_RESTRICTED`).
     - Cependant, **aucun espace de travail ne peut exister "hors-sol" sans imputation budgétaire** : tout `Workspace` (y compris `PRIVATE_USER`) doit obligatoirement être rattaché à une **Équipe de facturation (`ownerOrgUnitId` / `ownerOrgUnitName`)** afin que chaque jeton LLM consommé soit imputé à une équipe identifiée.
  3. **Chaîne de Verrouillage Stricte « Zéro Appel LLM sans Équipe de Facturation + Espace de Travail + Modèle IA »** :
     - Tant que les 3 maillons (`Équipe de facturation` + `Espace de Travail` + `Modèle IA`) ne sont pas réunis, tous les points d'entrée déclenchant un appel LLM et la soumission d'un espace sans équipe/nom affichent le verrouillage visuel `DisabledButtonAlertIndicator` (bouton grisé + badge `!` rouge cerclé aligné à droite + infobulle à texte rouge) et une notification explicite dans `🔔 Notifications`.
  4. **Sélecteur de Contexte (`TopHeaderBar`) en 3 Groupes & Filtrage Contextuel** :
     - Le menu déroulant `topbar-workspace-dropdown-menu` doit organiser clairement les périmètres en **3 groupes explicites** :
       - `🔒 Mes Espaces Privés` (espaces `PRIVATE_USER` avec indication de l'équipe de facturation `Nom Espace · Équipe X`),
       - `👥 Mes Équipes & Espaces` (les Équipes `TEAM` auxquelles l'utilisateur appartient et leurs Espaces `STANDARD` / `CONFIDENTIAL_RESTRICTED`),
       - `🏢 Supervision Organisation` (`Plateforme Globale ORCIA` et Directions `BU`).
     - La sélection d'un élément dans ce menu met à jour `activeScopeId` et adapte immédiatement le contexte dans `CockpitFeaturePanel`, `WorkspacesFeaturePanel`, `GatesFeaturePanel` et `/activity`.

### 1.2 Exploration, Analyse d'Impact GitNexus, Factorisation & Dette Technique
- **Analyse d'Impact GitNexus (`gitnexus_query`, `gitnexus_context`, `gitnexus_impact`)** :
  - `gitnexus_impact({target: "usePlatformSetup", direction: "upstream", repo: "/home/romain/Documents/Projects/ORCIA"})` : `impactedCount: 34` (`risk: HIGH`, `11` appelants directs à `d=1` : `InnerShellContainer`, `WorkspacesFeaturePanel`, `CockpitFeaturePanel`, `GatesFeaturePanel`, `FinopsFeaturePanel`, `InboxFeaturePanel`, `CatalogFeaturePanel`, `OntologyFeaturePanel`, `ActivityLogRouteView`, `SettingsHubView`).
  - `gitnexus_impact({target: "WorkspacesFeaturePanel", direction: "upstream", repo: "/home/romain/Documents/Projects/ORCIA"})` : `impactedCount: 16` (`risk: LOW`, monté via `ModuleWorkspaceView` sur `/workspaces` et `/spaces`).
  - `gitnexus_context({name: "FourZoneDirectionCShell", repo: "/home/romain/Documents/Projects/ORCIA"})` : appelé par `InnerShellContainer` (`apps/web/src/components/ShellContainer.tsx`).
- **Contrôle de volumétrie des fichiers (`<= 300–400 lignes`) & Découpage modulaire** :
  - `apps/web/src/features/workspaces/index.tsx` fait actuellement `481` lignes $\rightarrow$ **Découpage obligatoire** en extrayant le panneau de création d'espace et la bannière de filtre contextuel dans un sous-composant dédié `apps/web/src/features/workspaces/CreateWorkspaceCard.tsx` afin de ramener `features/workspaces/index.tsx` sous la barre des `380` lignes.
  - `apps/web/src/routes/SettingsOrganizationUnitsBlock.tsx` fait `299` lignes $\rightarrow$ conserver sous `360` lignes tout en ajoutant le rattachement multi-équipes (`memberTeamIds`, case à cocher « Rattacher mon compte à cette équipe (facturation & accès) » et bouton 1-clic `Rattacher mon compte` / `Retirer mon rattachement`).

---

## 2. Plan d'Implémentation

### 2.1 Schéma de Données & Migrations Alembic (`infra/migrations/versions/...`, si applicable)
- Aucune nouvelle migration SQL destructive requise : la table `workspaces` possède déjà `owner_org_unit_id UUID NOT NULL REFERENCES org_units(id) ON DELETE RESTRICT` et `visibility_mode`, et `platform_setup_snapshot` persiste déjà en JSONB l'intégralité des propriétés enrichies (`memberTeamIds`, `ownerOrgUnitId`, `ownerOrgUnitName`, `ownerUserId`, `visibilityMode: "STANDARD" | "CONFIDENTIAL_RESTRICTED" | "PRIVATE_USER"`).
- Documentation dans `architecture.md` et `faq-architecture-modele-metier.md` de l'évolution `visibility_mode IN ('STANDARD', 'CONFIDENTIAL_RESTRICTED', 'PRIVATE_USER')` et de la table/relation multi-équipes.

### 2.2 Noyau Métier Hexagonal, Orchestration & Workers (`packages/orcia-core/`, `apps/worker/`, `infra/sandbox/`)
- Inchangé côté Python (tous les contrats `lint-imports` et `ruff` demeurent 100 % verts).

### 2.3 Couche Backend API, Sécurité & Contrats (`apps/api/`, `packages/api-client/`)
- Persistance transparente via `GET/PUT /api/v1/bootstrap/platform-setup-state` (`@orcia/api-client`) déjà câblée dans `platformSetupStore.tsx`.

### 2.4 Interface Utilisateur & Expérience (`packages/ui/` & `apps/web/`)
1. **`packages/ui` (`@orcia/ui`)** :
   - Étendre `WorkspaceVisibilityMode = "STANDARD" | "CONFIDENTIAL_RESTRICTED" | "PRIVATE_USER"` dans `WorkspaceControlCenter.tsx`, `ProductLifecycleCard.tsx`, `WorkspaceTopologyPanel.tsx` et `shell/types.ts`.
   - Enrichir `ControlCenterWorkspaceGovItem` avec `ownerOrgUnitId?: string`, `ownerOrgUnitName?: string` et `ownerUserId?: string`.
   - Dans `WorkspaceTopologyPanel.tsx` et `ProductLifecycleCard.tsx`, afficher clairement le badge de visibilité (`PRIVATE_USER` $\rightarrow$ `🔒 Privé (Facturé à l'équipe)`, `CONFIDENTIAL_RESTRICTED` $\rightarrow$ `Confidentiel`, `STANDARD` $\rightarrow$ `Collectif d'équipe`) et le nom de l'Équipe de facturation (`ownerOrgUnitName`).
2. **`apps/web/src/components/platformSetupStore.tsx`** :
   - Enrichir `ConfiguredPlatformAdmin` avec `readonly memberTeamIds?: readonly string[]` (initialisé à `[]` lors de `createPlatformAdmin` — Étape A Jour 0).
   - Ajouter `toggleAdminTeamMembership(teamId: string)` dans `PlatformSetupContextValue` permettant d'attacher ou détacher le compte administrateur d'une Équipe (`TEAM`) avec trace d'audit dans le Journal d'Activité.
   - Dans `addOrgUnit`, accepter une option `attachCurrentAdmin?: boolean` (par défaut `true` quand `level === "TEAM"`) pour rattacher automatiquement le compte à la nouvelle Équipe créée, et retirer l'équipe de `memberTeamIds` lors de `removeOrgUnit`, tout en empêchant la suppression d'une Équipe ou BU à laquelle un Espace de Travail (`workspaces.some(w => w.ownerOrgUnitId === orgUnitId)`) est rattaché (`ON DELETE RESTRICT`).
   - Dans `createWorkspace`, accepter `visibilityMode: "STANDARD" | "CONFIDENTIAL_RESTRICTED" | "PRIVATE_USER"` et `ownerOrgUnitId?: string` (résolu vers l'équipe sélectionnée, ou la première équipe `TEAM` disponible, ou la première unité disponible pour rétrocompatibilité des tests existants).
3. **`apps/web/src/routes/SettingsOrganizationUnitsBlock.tsx` & `SettingsIamOrganizationSection.tsx`** :
   - Lorsque `orgLevel === "TEAM"`, afficher la case à cocher `org-unit-attach-admin-checkbox` (cochée par défaut) *« Rattacher mon compte à cette équipe (facturation & accès IA) »*.
   - Sur chaque ligne d'Équipe (`u.level === "TEAM"`), afficher le badge `org-unit-member-badge-${u.id}` (`✓ Membre · Facturation IA active` ou `Non rattaché`) et le bouton 1-clic `toggle-team-membership-btn-${u.id}` (`Retirer mon rattachement` / `+ Rattacher mon compte`).
4. **`apps/web/src/features/workspaces/CreateWorkspaceCard.tsx` & `apps/web/src/features/workspaces/index.tsx`** :
   - Créer `CreateWorkspaceCard.tsx` avec :
     - Sélecteur d'Équipe de rattachement / facturation FinOps (`data-testid="workspace-owner-team-select"`),
     - Sélecteur de visibilité enrichi (`STANDARD`, `PRIVATE_USER`, `CONFIDENTIAL_RESTRICTED`),
     - Bouton `create-workspace-submit-btn` équipé de `DisabledButtonAlertIndicator` (désactivé avec `!` rouge et infobulle rouge tant que le nom de l'espace est vide).
   - Filtrer et pré-sélectionner dynamiquement les espaces affichés dans `WorkspacesFeaturePanel` selon le contexte actif (`activeScopeId`) sélectionné dans `TopHeaderBar`, avec un bandeau contextuel `workspace-active-scope-banner`.
5. **`apps/web/src/components/ShellContainer.tsx`** :
   - Organiser `workspaceOptions` en **3 groupes explicites** :
     - `🔒 Mes Espaces Privés` (`PRIVATE_USER`, libellé `${ws.name} · ${ws.ownerOrgUnitName}`),
     - `👥 Mes Équipes & Espaces` (Équipes `TEAM` et Espaces `STANDARD` / `CONFIDENTIAL_RESTRICTED`),
     - `🏢 Supervision Organisation` (`Plateforme Globale ORCIA` et Directions `BU`).
   - Enrichir les raisons de verrouillage (`disabledMenuKeys`) et les cartes du Centre de Notifications (`🔔 Notifications`) pour rappeler explicitement la chaîne **« Équipe de facturation + Espace de Travail + Modèle IA »** (y compris une notification dédiée `setup-billing-team-missing` tant qu'aucune Équipe de facturation n'est rattachée).
   - Filtrer contextuellement `CockpitFeaturePanel` selon `activeScopeId`.
6. **Documentation FAQ (`architecture.md` & `faq-architecture-modele-metier.md`)** :
   - Ajouter `Q2` (Multi-Équipes par Utilisateur, Multi-Espaces par Équipe et Espaces Privés `PRIVATE_USER` rattachés à une Équipe pour la facturation FinOps — Option 2), `Q3` (Chaîne de verrouillage stricte « Zéro appel LLM sans Équipe de facturation + Espace de Travail + Modèle IA » et parcours Jour 0 en 2 étapes — Option 1) et `Q4` (Sélecteur de contexte en haut de l'écran en 3 groupes).

---

## 3. Bilan des Modifications & Résultats (Post-Implémentation)

### 3.1 Tableau Synthétique des Fichiers Développés et Modifiés

| Fichier | Action | Rôle & Modifications Réalisées |
| :--- | :--- | :--- |
| `packages/ui/src/shell/types.ts` & `packages/ui/src/index.ts` | Modifié | Ajout et export du type `WorkspaceVisibilityMode = "STANDARD" \| "CONFIDENTIAL_RESTRICTED" \| "PRIVATE_USER"` sur `UiWorkspaceCardView`. |
| `packages/ui/src/primitives/ProductLifecycleCard.tsx` | Modifié | Support du mode `"PRIVATE_USER"` (*🔒 Privé (Facturé à l'équipe)*) et affichage optionnel du nom de l'Équipe de facturation (`ownerOrgUnitName`). |
| `packages/ui/src/primitives/WorkspaceControlCenter.tsx` | Modifié | Enrichissement de `ControlCenterWorkspaceGovItem` avec `"PRIVATE_USER"`, `ownerOrgUnitId`, `ownerOrgUnitName`, `ownerUserId` et transmission à `ProductLifecycleCard`. |
| `packages/ui/src/shell/WorkspaceTopologyPanel.tsx` | Modifié | Badge `"cobalt"` pour le mode de visibilité `"PRIVATE_USER"`. |
| `apps/web/src/components/platformSetupStore.tsx` | Modifié | Ajout de `memberTeamIds` (`[]` au Jour 0 — Étape A) sur `ConfiguredPlatformAdmin`, méthode `toggleAdminTeamMembership(teamId)`, option `attachCurrentAdmin` (défaut `true` pour `TEAM`) dans `addOrgUnit`, protection anti-orphelin sur `removeOrgUnit` si un `Workspace` est rattaché à l'unité, et support de `PRIVATE_USER` + `ownerOrgUnitId` / `ownerOrgUnitName` / `ownerUserId` dans `createWorkspace`. |
| `apps/web/src/routes/settings.tsx`, `SettingsIamOrganizationSection.tsx` & `SettingsOrganizationUnitsBlock.tsx` | Modifié | Étape B du parcours Jour 0 : badge récapitulatif `admin-team-membership-summary-badge`, case à cocher `org-unit-attach-admin-checkbox` lors de la création d'une Équipe (`TEAM`), badge `org-unit-member-badge-${u.id}` et bouton 1-clic `toggle-team-membership-btn-${u.id}` pour le rattachement multi-équipes. |
| `apps/web/src/features/workspaces/CreateWorkspaceCard.tsx` | **Créé (`266` lignes)** | Extraction modulaire du formulaire de création d'Espace de Travail et de la bannière de filtre contextuel (`workspace-active-scope-banner`), sélecteur d'Équipe de facturation (`workspace-owner-team-select`), 3 modes de visibilité (`STANDARD`, `PRIVATE_USER`, `CONFIDENTIAL_RESTRICTED`) et `DisabledButtonAlertIndicator` sur `create-workspace-submit-btn`. |
| `apps/web/src/features/workspaces/index.tsx` | Modifié (`370` lignes, ramené de `481` lignes) | Utilisation de `CreateWorkspaceCard`, filtrage contextuel dynamique des espaces selon `activeScopeId` (Espace, Équipe, BU ou Plateforme Globale) et passage de `ownerOrgUnitId`/`ownerOrgUnitName` à `WorkspaceControlCenter`. |
| `apps/web/src/components/ShellContainer.tsx` | Modifié | Structuration de `workspaceOptions` en **3 groupes explicites** (`🔒 Mes Espaces Privés`, `👥 Mes Équipes & Espaces`, `🏢 Supervision Organisation`), chaîne de verrouillage FinOps (`disabledMenuKeys`) et notification dédiée `setup-billing-team-missing`. |
| `apps/web/src/features/cockpit/index.tsx`, `apps/web/src/features/gates/index.tsx` & `apps/web/src/routes/activity.tsx` | Modifié | Filtrage contextuel dynamique sur `activeScopeId` (`cockpit-active-scope-badge`, `gates-active-scope-badge`, inclusion des `childWorkspaces` rattachés à chaque `TEAM`/`BU` dans `/activity`). |
| `docs/planning-artifacts/architecture/architecture-ORCIA-2026-10-24/faq-architecture-modele-metier.md` & `architecture.md` | Modifié | Enrichissement de la FAQ d'architecture (Winston) avec `Q2` (Multi-Équipes, Multi-Espaces & Espaces Privés `PRIVATE_USER` Option 2 FinOps), `Q3` (Parcours Jour 0 en 2 étapes Option 1 & Chaîne de verrouillage LLM) et `Q4` (Sélecteur de contexte `TopHeaderBar` à 3 groupes). |
| `apps/web/src/__tests__/i18n-and-shell.test.tsx` | Modifié | Ajout du test d'intégration bout-en-bout couvrant le parcours Jour 0 en 2 étapes, le rattachement multi-équipes, la création d'Espace Privé facturé à l'équipe, la protection anti-suppression d'équipe propriétaire et le sélecteur de contexte à 3 groupes. |

### 3.2 Métriques Chiffrées & Validation des 5 Couches (`AD-17`) et des 5 Garde-Fous
- **`pnpm turbo run lint typecheck test`** : **9/9 tâches réussies** (`@orcia/ui`: `65` tests passés ; `@orcia/web`: `36` tests passés sur 4 fichiers de tests, dont `zero-dead-buttons-and-silent-catches-audit.test.tsx`, `design-system-look-and-feel-isolation.test.tsx`, `orcia-showcase-site.test.tsx` et `i18n-and-shell.test.tsx`).
- **Qualité Python & Architecture** :
  - `.venv/bin/ruff check .` : `All checks passed!`
  - `.venv/bin/lint-imports` : `5 contracts kept, 0 broken.`
  - `lint_spine.py` : `0 findings.`
- **Contrôle de volumétrie (`<= 400 lignes`)** : `features/workspaces/index.tsx` ramené de `481` à `370` lignes grâce à l'extraction de `CreateWorkspaceCard.tsx` (`266` lignes).
- **Synchronisation du Site Vitrine (`/showcase` & `docs/site-catalog/index.html`)** : `pnpm site:sync && pnpm site:check` exécutés avec succès (`39` rapports Tech Lead synchronisés).
