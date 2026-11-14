# Rapport Tech Lead — Story 17.1 : Coquille UI Direction C — Reset Boutons, Icônes SVG Filaires Monochromes, Barre de Repli & 5 Onglets de Configuration

- **Date** : `2026-11-11`
- **Auteur** : Équipe Tech Lead / Dev Senior ORCIA
- **Périmètre** : `Story 17.1` (`17-1-coquille-ui-direction-c-reset-boutons-icones-svg-filaires-et-5-onglets-configuration` — Epic 17 : Refonte Gouvernance IAM, Hiérarchie Organisationnelle & Coquille UI Direction C)
- **Statut** : `completed`
- **Capacité(s)** : `CAP-058`, `CAP-060`, `CAP-100`
- **Classification** : `ux` / `feature`

---

## 1. Analyse du Besoin & Étude d'Impact Tech Lead (Avant Implémentation)

### 1.1 Objectif Métier & Critères d'Acceptation

La **Story 17.1** aligne la coquille applicative 4 zones (`FourZoneDirectionCShell`), le système d'icônes centralisé (`@orcia/ui`) et l'écran `/settings` sur les standards visuels et de gouvernance **Direction C (`DESIGN.md` / `EXPERIENCE.md`)** :

1. **CA-17.1.1 — Reset CSS `<button>` & Harmonisation Visuelle Direction C** :
   - Suppression des bordures par défaut navigateur (`2px outset`) sur les `<button>` via une règle `@layer base` dans `packages/ui/src/styles/tokens.css`, garantissant que les boutons de navigation de la barre latérale ont un fond transparent au repos, un survol discret (`--color-bg-secondary`) et un état actif sobre (`--color-action-primary-subtle` + `--color-action-primary`), sans écraser les classes utilitaires ni `.orcia-ds-*`.
   - Alignement visuel des actions de pied de barre latérale (**Mon Compte** et **Documentation**) sur le style exact des 8 entrées de navigation principales.
   - Enrichissement de la variante sémantique `.orcia-ds-btn-danger` autour du jeton `--color-stale-crimson` (`#DC2626`) avec contraste AA, état `:hover:not(:disabled)`, anneau `:focus-visible` et état `:disabled`.

2. **CA-17.1.2 — Registre d'Icônes SVG Filaires Monochromes 16px & Barre de Repli Propre** :
   - Bascule du rendu visuel de `<OrciaIcon />` (`packages/ui/src/components/icons/`) sur des tracés vectoriels `<svg>` filaires monochromes `16px` (`viewBox="0 0 24 24"`, `fill="none"`, `stroke="currentColor"`, `strokeWidth={1.75}`, `strokeLinecap="round"`, `strokeLinejoin="round"`, `aria-hidden="true"` par défaut), tout en préservant l'export `getOrciaIconGlyph()` et la réactivité du registre `ORCIA_ICONS`.
   - Ajout des clés d'icônes dédiées à la coquille et aux 5 onglets de configuration : `nav.collapse`, `nav.expand`, `nav.account`, `settings.org`, `settings.iam`, `settings.models`, `settings.connectors`, `settings.packs`.
   - Refonte du bandeau supérieur de repli de la Sidebar : en mode déployé (`240px`), ligne d'en-tête alignée avec icône filaire `nav.collapse`, libellé épuré (`Replier le menu` / `Collapse menu`, sans parenthèse parasite `([)`) et badge clavier `<kbd>[</kbd>` aligné à droite ; en mode replié (`68px`), bouton icône centré `nav.expand` avec `title` / `aria-label` explicite (`Déplier le menu ([)`).

3. **CA-17.1.3 — 5 Onglets Adaptatifs dans `/settings`, Rôle Dynamique & Entrée « Mon Compte »** :
   - Remplacement des 6 onglets historiques de `/settings` par **5 onglets adaptatifs** éliminant les doublons avec `/processes` (`Atelier de Processus`) et `/workspaces` (`Glossaire & Règles`) :
     1. `organization` (**Organisation**) — hiérarchie Directions/BU & Équipes (`SettingsOrganizationUnitsBlock`), séparée des habilitations.
     2. `iam` (**Comptes & Habilitations**) — règles d'habilitation IAM (`SettingsIamPermissionsSection`), séparées de l'organigramme.
     3. `models` (**Modèles IA**) — configuration et banc de test des paliers LLM.
     4. `connectors` (**Connecteurs & SSO**) — sources documentaires et connecteurs externes.
     5. `packs` (**Packs Métiers**) — catalogue et activation des packs métiers.
   - Suppression du `useState(["create", "read", "update", "delete", "execute", "grant"])` codé en dur dans `settings.tsx` au profit d'un store typé `useAuthSessionStore` et du résolveur pur `resolveSettingsAccess(session)` :
     - `PLATFORM_ADMIN` et `SECOPS` (hors mode observateur) : accès aux 5 onglets + verbes d'administration complets.
     - `BU_LEAD` et `TEAM_LEAD` (hors mode observateur) : affichage adaptatif limité aux 2 onglets `organization` et `iam` + verbes de gestion sur leur périmètre.
     - `CONTRIBUTOR` et `OBSERVER` (`READ_ONLY_OBSERVER` ou `readOnlyObserver === true`) : `allowedVerbs = ["read"]` uniquement, masquage/désactivation des contrôles de mutation et bandeau explicite de lecture seule avec bouton d'accès rapide à **Mon Compte** (`UserSettingsModal`).
   - Remplacement du `userHatLabel="Administrateur de la plateforme"` codé en dur dans `ShellContainer.tsx` par une résolution dynamique localisée (`FR`/`EN`), suppression des pluriels bruts `(s)` (`Équipe(s)`, `Direction(s)`, `Espace(s)`), et ajout d'une entrée dédiée **Mon Compte** (`nav.account`) en pied de Sidebar ouvrant `UserSettingsModal` au même titre que le contrôle profil de la Topbar.

### 1.2 Décisions d'Architecture & Spécifications UX Aplicables

- **`AD-19` & Isolation `@orcia/ui`** : Tous les composants visuels (`FourZoneDirectionCShell`, `OrciaIcon`, `UserAccountDropdownAndSettingsModal`) et jetons CSS (`tokens.css`) restent strictement confinés dans `packages/ui` sans aucune dépendance vers `@tanstack/react-router` ni `@orcia/api-client`.
- **Direction C (`DESIGN.md` / `EXPERIENCE.md`)** : Zéro couleur hexadécimale hors `packages/ui/src/styles/tokens.css` ; jeton `--color-human-led-violet` (`#6D28D9`) strictement réservé à `HumanLedAnchorCard.tsx` ; icônes monochromes `currentColor` héritant de la couleur sémantique du texte parent.
- **Internationalisation (`FR` par défaut, parité `FR`/`EN`)** : Tous les nouveaux libellés (5 onglets `/settings`, sous-titre, rôles gouvernance, barre de repli, entrée `Mon Compte`, bandeau lecture seule, pluriels accordés) sont centralisés dans `apps/web/src/i18n/locales/`.

### 1.3 Analyse d'Impact GitNexus (Symboles & Dépendances Amont/Aval)

| Symbole / Module analysé | Fichier source | Appelants amont (`upstream`) | Niveau de risque | Décision Tech Lead |
| :--- | :--- | :--- | :---: | :--- |
| `FourZoneDirectionCShell` | `packages/ui/src/primitives/FourZoneDirectionCShell.tsx` | `InnerShellContainer` $\rightarrow$ `ShellContainer` $\rightarrow$ `RootLayoutComponent` (`3` appelants hors tests) | `LOW` | Préserver la signature publique de `FourZoneDirectionCShellProps` et `ORCIA_EIGHT_MENU_ICON_NAMES` ; découper le fichier (`753` lignes $\rightarrow$ `< 350` lignes) en extrayant TopHeaderBar et NotificationsDrawer. |
| `OrciaIcon` / `ORCIA_ICONS` | `packages/ui/src/components/icons/{OrciaIcon.tsx,iconRegistry.ts}` | `39` composants UI & Web + `icon-registry-centralization.test.tsx` | `MEDIUM` | Conserver `ORCIA_ICONS`, `getOrciaIconDefinition`, `getOrciaIconGlyph`, `data-orcia-icon` et `aria-hidden` ; loger les tracés vectoriels dans `packages/ui/src/components/icons/iconSvgPaths.ts` (autorisé par Audit Gate 1). |
| `UserAccountDropdownAndSettingsModal` | `packages/ui/src/primitives/UserAccountDropdownAndSettingsModal.tsx` | `ShellContainer.tsx` + tests RGAA / Shell | `LOW` | Ajouter le pilotage contrôlé optionnel `modalOpen` / `onModalOpenChange` et les libellés localisés des 6 rôles gouvernance ; découper (`633` lignes $\rightarrow$ `< 395` lignes). |
| `SettingsRoutePage` | `apps/web/src/routes/settings.tsx` | Route TanStack `/settings` (`router.tsx`) | `LOW` | Remplacer les 6 onglets par les 5 onglets adaptatifs gouvernés par `resolveSettingsAccess(session)` ; séparer `organization` et `iam`. |

### 1.4 Opportunités de Factorisation & Dette Technique Identifiées

1. **Contrôle strict de volumétrie (`< 400` lignes par fichier créé/refactorisé)** :
   - `FourZoneDirectionCShell.tsx` (`753` lignes) cumule la TopHeaderBar, le tiroir de notifications `420px`, la Sidebar `240px/68px` et la grille 4 zones $\rightarrow$ extraction de `FourZoneSidebarRail.tsx`, `FourZoneTopHeaderSection.tsx` et `FourZoneNotificationsDrawer.tsx`.
   - `UserAccountDropdownAndSettingsModal.tsx` (`633` lignes) cumule le menu déroulant rapide et la modale RGAA 4 onglets $\rightarrow$ extraction de `UserAccountDropdownMenu.tsx` et `UserSettingsModalDialog.tsx`.
   - `ShellContainer.tsx` (`560` lignes) cumule la modale de recherche fédérée 2 vitesses et l'assemblage 4 zones $\rightarrow$ extraction de `ShellFederatedSearchModal.tsx`.
   - `SettingsOrganizationUnitsBlock.tsx` et `SettingsIamOrganizationSection.tsx` $\rightarrow$ séparation franche entre `SettingsOrganizationUnitsBlock.tsx` + `SettingsOrganizationUnitRow.tsx` pour l'onglet 1 `organization` et `SettingsIamOrganizationSection.tsx` + `SettingsIamGrantsList.tsx` pour l'onglet 2 `iam`.
2. **Factorisation de l'accord pluriel (`formatCountNoun`)** : Utilitaire pur partagé dans `authSessionStore.ts` éliminant tous les `(s)` bruts (`Équipe(s)`, `Direction(s)`, `Espace(s)`, `règle(s)`) dans `SettingsOrganizationUnitsBlock`, `SettingsIamGrantsList` et `platformSetupStore`.
3. **Continuité vers `Story 17.2` et `Story 17.3`** : Le store `useAuthSessionStore` et le contrat `resolveSettingsAccess` préparent directement le câblage serveur RBAC/organigramme PostgreSQL de `Story 17.2` et la gestion complète des comptes de `Story 17.3` sans aucun refactoring cassant ultérieur. Aucun ticket intercalaire `17.1a` supplémentaire n'est requis.

---

## 2. Plan d'Implémentation

### 2.1 Schéma de Données & Migrations Alembic (`infra/migrations/`)
- Aucune migration Alembic requise pour `Story 17.1` (périmètre Coquille UI Direction C, Design System `@orcia/ui` et gouvernance d'affichage `/settings` ; les évolutions SQL d'organigramme récursif et de comptes relèvent des Stories `17.2` et `17.3`).

### 2.2 Noyau Métier Hexagonal & Workers (`packages/orcia-core`, `packages/orcia-connectors`, `apps/worker`)
- Aucun changement dans les packages Python backend.

### 2.3 Backend FastAPI & Contrat OpenAPI (`apps/api`, `packages/api-client`)
- Aucun changement d'endpoint FastAPI ni régénération OpenAPI requise dans `Story 17.1`.

### 2.4 Interface SPA Vite + TanStack Router (`packages/ui`, `apps/web` — Direction C)
1. **Design System CSS (`packages/ui/src/styles/tokens.css`)** :
   - Ajout de `@layer base` réinitialisant `button` (`border: 0; background-color: transparent; color: inherit; font: inherit; cursor: pointer;`).
   - Ajout des classes sémantiques `.orcia-sidebar-nav-btn`, `.orcia-sidebar-rail-header`, `.orcia-kbd-badge` et enrichissement de `.orcia-ds-btn-danger` (`:hover:not(:disabled)`, `:focus-visible`, `:disabled`).
2. **Système d'icônes SVG filaires (`packages/ui/src/components/icons/`)** :
   - Création de `iconSvgPaths.ts` contenant les tracés vectoriels `24×24` (`stroke="currentColor"`, `strokeWidth={1.75}`) pour l'ensemble des `106` clés sémantiques (`98` clés existantes + `nav.collapse`, `nav.expand`, `nav.account`, `settings.org`, `settings.iam`, `settings.models`, `settings.connectors`, `settings.packs`).
   - Mise à jour de `iconRegistry.ts` et `OrciaIcon.tsx` pour rendre un `<svg>` filaire monochrome `16px` par défaut tout en conservant `getOrciaIconGlyph()` et la réactivité `ORCIA_ICONS`.
3. **Coquille 4 zones & Modale Compte (`packages/ui/src/primitives/`)** :
   - Découpage de `FourZoneDirectionCShell.tsx` (`322` lignes) + `FourZoneSidebarRail.tsx` (`218` lignes) + `FourZoneTopHeaderSection.tsx` (`244` lignes) + `FourZoneNotificationsDrawer.tsx` (`173` lignes) avec barre de repli propre (`<OrciaIcon name="nav.collapse" />` + libellé sans `([)` + `<kbd>[</kbd>` en mode déployé ; bouton centré `nav.expand` avec `title`/`aria-label` `"Déplier le menu ([)"` en mode rail `68px`), slot `renderSidebarFooter` et boutons de navigation sans bordure parasite.
   - Découpage de `UserAccountDropdownAndSettingsModal.tsx` (`393` lignes) + `UserAccountDropdownMenu.tsx` (`144` lignes) + `UserSettingsModalDialog.tsx` (`184` lignes) + support de l'ouverture contrôlée `modalOpen` / `onModalOpenChange` et des 6 rôles gouvernance localisés (`FR`/`EN`).
4. **Store de session RBAC, ShellContainer & `/settings` (`apps/web/src/`)** :
   - Création de `apps/web/src/stores/authSessionStore.ts` (`216` lignes : `useAuthSessionStore`, `resolveSettingsAccess`, `resolveSessionHatLabel`, `formatCountNoun`, `SETTINGS_TAB_ICON_NAMES`) avec réinitialisation propre dans `vitest.setup.ts`.
   - Mise à jour des dictionnaires `FR`/`EN` (`shell_and_search_labels.ts`, `admin_and_studio_labels.ts`).
   - Découpage de `ShellContainer.tsx` (`384` lignes) + `ShellFederatedSearchModal.tsx` (`205` lignes) : `userHatLabel` dynamique localisé, bouton **Mon Compte** (`sidebar-open-my-account-btn`, `nav.account`) et bouton **Documentation** (`open-orcia-showcase-site-btn`, `bookOpen`) harmonisés en pied de Sidebar.
   - Refonte de `apps/web/src/routes/settings.tsx` (`243` lignes) et découpage de `SettingsOrganizationUnitsBlock.tsx` (`337` lignes) + `SettingsOrganizationUnitRow.tsx` (`155` lignes) et `SettingsIamOrganizationSection.tsx` (`398` lignes) + `SettingsIamGrantsList.tsx` (`171` lignes) autour des 5 onglets adaptatifs (`organization`, `iam`, `models`, `connectors`, `packs`), `.orcia-ds-btn-danger` sur les actions destructrices, zéro `(s)` brut, et bandeau lecture seule avec accès direct à **Mon Compte**.
5. **Tests TDD (`packages/ui` & `apps/web`)** :
   - Création de `packages/ui/src/__tests__/story-17-1-wireframe-icons-and-shell-rail.test.tsx` (`198` lignes) et `apps/web/src/__tests__/story-17-1-settings-5-tabs-and-rbac.test.tsx` (`229` lignes), et alignement des assertions de migration d'onglets/icônes SVG dans `i18n-and-shell.test.tsx`, `zero-dead-buttons-and-silent-catches-audit.test.tsx`, `icon-registry-centralization.test.tsx`, `four-zone-shell-and-cockpit.test.tsx`, `assistant-workspace.test.tsx` et `agents-and-skills.test.tsx`.

---

## 3. Bilan des Modifications & Résultats (Après Implémentation)

### 3.1 Tableau Récapitulatif des Fichiers Créés & Modifiés

| Fichier | Action | Volumétrie | Rôle & Responsabilité |
| :--- | :---: | :---: | :--- |
| `packages/ui/src/styles/tokens.css` | Modifié | `~340` l. | Reset `@layer base { button }`, classes `.orcia-sidebar-rail-header`, `.orcia-sidebar-nav-btn`, `.orcia-kbd-badge` et variante `.orcia-ds-btn-danger` (`--color-stale-crimson` `#DC2626`). |
| `packages/ui/src/components/icons/iconSvgPaths.ts` | Créé | `119` l. | Tracés vectoriels `24×24` filaires monochromes pour les `106` clés `OrciaIconName`. |
| `packages/ui/src/components/icons/iconRegistry.ts` | Modifié | `286` l. | Ajout de `nav.collapse`, `nav.expand`, `nav.account`, `settings.org`, `settings.iam`, `settings.models`, `settings.connectors`, `settings.packs` + `svgPaths`. |
| `packages/ui/src/components/icons/OrciaIcon.tsx` | Modifié | `80` l. | Rendu `<svg>` filaire `16px` (`viewBox="0 0 24 24"`, `fill="none"`, `stroke="currentColor"`, `strokeWidth={1.75}`, `aria-hidden="true"`). |
| `packages/ui/src/components/icons/index.ts` & `packages/ui/src/index.ts` | Modifié | `14` / `205` l. | Ré-export propre des types/helpers d'icônes et des 6 libellés localisés de rôles gouvernance. |
| `packages/ui/src/primitives/FourZoneDirectionCShell.tsx` | Modifié | `322` l. | Coquille 4 zones Direction C découplée (`< 350` l.) avec `renderSidebarFooter`. |
| `packages/ui/src/primitives/FourZoneSidebarRail.tsx` | Créé | `218` l. | Bandeau de repli épuré (`nav.collapse` + `<kbd>[</kbd>` déployé ; `nav.expand` centré en rail `68px`), 8 entrées sans bordure et pied de barre. |
| `packages/ui/src/primitives/FourZoneTopHeaderSection.tsx` | Créé | `244` l. | En-tête supérieur Direction C extrait de `FourZoneDirectionCShell`. |
| `packages/ui/src/primitives/FourZoneNotificationsDrawer.tsx` | Créé | `173` l. | Tiroir de notifications `420px` extrait de `FourZoneDirectionCShell`. |
| `packages/ui/src/primitives/UserAccountDropdownAndSettingsModal.tsx` | Modifié | `393` l. | Ouverture contrôlée `modalOpen`/`onModalOpenChange` et dictionnaires `ROLE_DISPLAY_LABELS_FR`/`EN` des 6 rôles gouvernance. |
| `packages/ui/src/primitives/UserAccountDropdownMenu.tsx` | Créé | `144` l. | Menu déroulant rapide profil extrait sous `< 200` lignes. |
| `packages/ui/src/primitives/UserSettingsModalDialog.tsx` | Créé | `184` l. | Modale RGAA 4 onglets `Mon Compte` extraite sous `< 200` lignes. |
| `apps/web/src/stores/authSessionStore.ts` | Créé | `216` l. | Store typé `useAuthSessionStore`, résolveur pur `resolveSettingsAccess`, `resolveSessionHatLabel`, `formatCountNoun` et `SETTINGS_TAB_ICON_NAMES`. |
| `apps/web/src/components/ShellContainer.tsx` | Modifié | `384` l. | `userHatLabel` dynamique localisé, pilotage partagé de `UserSettingsModal` et entrées Sidebar `Mon Compte` + `Documentation`. |
| `apps/web/src/components/ShellFederatedSearchModal.tsx` | Créé | `205` l. | Modale de recherche fédérée `⌘K` extraite de `ShellContainer`. |
| `apps/web/src/routes/settings.tsx` | Modifié | `243` l. | 5 onglets adaptatifs (`organization`, `iam`, `models`, `connectors`, `packs`), suppression des doublons `workflows`/`glossary`, bandeau lecture seule + accès `Mon Compte`. |
| `apps/web/src/routes/SettingsOrganizationUnitsBlock.tsx` & `SettingsOrganizationUnitRow.tsx` | Modifié / Créé | `337` / `155` l. | Onglet 1 `Organisation` dédié aux Directions (BU) & Équipes, suppression `.orcia-ds-btn-danger` et accords pluriels propres. |
| `apps/web/src/routes/SettingsIamOrganizationSection.tsx` & `SettingsIamGrantsList.tsx` | Modifié / Créé | `398` / `171` l. | Onglet 2 `Comptes & Habilitations` dédié aux règles IAM, désactivation en lecture seule (`canMutate`), suppression `.orcia-ds-btn-danger`. |
| `apps/web/src/routes/SettingsSecondaryTabsSection.tsx` & `apps/web/src/components/platformSetupStore.tsx` | Modifié | `215` l. | Nettoyage des onglets supprimés (`workflows`, `glossary`), icône `<OrciaIcon name="settings.connectors" />` et suppression des `(s)` bruts. |
| `apps/web/src/i18n/locales/{shell_and_search_labels.ts,admin_and_studio_labels.ts}` | Modifié | `314` / `203` l. | Parité `FR`/`EN` complète pour les 5 onglets `/settings`, la barre de repli, le bandeau lecture seule et le pied de Sidebar. |
| `packages/ui/src/__tests__/story-17-1-wireframe-icons-and-shell-rail.test.tsx` | Créé | `198` l. | Tests unitaires `CA-17.1.1` & `CA-17.1.2` (reset CSS `tokens.css`, `.orcia-ds-btn-danger`, `106` icônes `<svg>`, barre de repli `240px`/`68px`, `modalOpen`). |
| `apps/web/src/__tests__/story-17-1-settings-5-tabs-and-rbac.test.tsx` | Créé | `229` l. | Tests unitaires & rendu `CA-17.1.3` (matrice RBAC des 6 rôles gouvernance + `readOnlyObserver`, séparation `organization`/`iam`, zéro `(s)` brut, ouverture `Mon Compte` depuis la Sidebar). |
| `docs/implementation-artifacts/sprint-status.yaml` & `docs/product/capabilities.yaml` | Modifié | — | `17-1` $\rightarrow$ `done`, `17-2` $\rightarrow$ `ready-for-dev` ; mise à jour `CAP-058` & `CAP-060` + synchronisation `/showcase`. |

### 3.2 Métriques Qualité & Validation des Portes (`AD-17` & Garde-Fous CI)

- **Tests Unitaires & Intégration Composants (`@orcia/ui`)** : `18/18` fichiers de tests passants (`77/77` tests verts), incluant `story-17-1-wireframe-icons-and-shell-rail.test.tsx` et `icon-registry-centralization.test.tsx`.
- **Tests Unitaires, Intégration Routes & Garde-Fous (`@orcia/web`)** : `10/10` fichiers de tests passants (`58/58` tests verts), incluant `story-17-1-settings-5-tabs-and-rbac.test.tsx`, `design-system-look-and-feel-isolation.test.tsx` (zéro hex hors `tokens.css`, `#6D28D9` exclusif à `HumanLedAnchorCard.tsx`), `zero-dead-buttons-and-silent-catches-audit.test.tsx`, `i18n-and-shell.test.tsx` et `orcia-showcase-site.test.tsx`.
- **Qualité Statique & Architecture** :
  - `pnpm turbo run lint typecheck test` : `0` erreur ESLint, `0` erreur TypeScript (`tsc --noEmit`), `100 %` des suites vertes.
  - `pnpm site:sync && pnpm site:check` : `0` écart entre `capabilities.yaml`, `tech-lead-reports/README.md`, `orciaSiteManifest.ts` et `docs/site-catalog/index.html`.
  - `.venv/bin/ruff check .` & `lint_spine.py` : `0` anomalie (`0 findings`, aucune dépendance tierce ajoutée).
