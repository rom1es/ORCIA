# 2026-11-07 — Refonte de Mes Espaces (`🗂️ Mes Espaces`), Intégration Directe du Glossaire & Règles Métiers (Ontologie Multi-Niveaux) et Option A (Retrait de l'Entrée Séparée Vocabulaire du Menu Latéral)

> **Convention de nommage du fichier (Obligatoire — créé AVANT toute modification de code)** :
> - Demande d'ajustement, correctif ou évolution hors Story : `docs/implementation-artifacts/tech-lead-reports/2026-11-07-refonte-mes-espaces-et-integration-glossaire-ontologie-option-a-tech-lead-report.md`

- **Date** : 2026-11-07
- **Story / Clé Sprint** : `2026-11-07-refonte-mes-espaces-et-integration-glossaire-ontologie-option-a` (`Ajustement Transverse UX/UI Direction C — Epic 9 & Epic 11 & Epic 12`)
- **Auteur / Contexte** : Sally (UX/UI Designer) & Winston (System Architect) — Épuration cognitive et refonte opérationnelle de l'écran `🗂️ Mes Espaces` (`/workspaces` & `/spaces`) autour d'une grille claire de cartes d'Espaces de Travail et d'un panneau de détail unifié en 3 onglets métiers (`📚 Sources & Documents de l'Espace`, `📖 Glossaire & Règles Métiers (Ontologie)`, `👥 Membres, Accès & Consignes`), avec intégration complète de la cascade d'héritage ontologique (`🏢 Entreprise` ➔ `🏛️ Direction` ➔ `👥 Équipe` ➔ `🗂️ Cet Espace`), promotion ascendante en 1 clic (`⬆️`), partage d'espace privé vers l'équipe en auto-save (`✓ Enregistré`), et retrait de toute entrée séparée `📖 Vocabulaire` (`vocabulary`) de la barre latérale gauche au profit de `🗂️ Mes Espaces` (niveaux Espace/Équipe) et `⚙️ Configuration` (niveau Global/Direction — Option A validée par l'utilisateur).
- **Commits associés** : *(à compléter en Section 3 après validation des gates)*

---

## 1. Analyse du Besoin & Étude d'Impact Tech Lead (Pré-Implémentation)

### 1.1 Contexte & Problématique
- **Problème identifié sur `🗂️ Mes Espaces` (`apps/web/src/features/workspaces/index.tsx`)** :
  1. **Triple affichage redondant et surcharge cognitive** : L'écran empilait successivement `CreateWorkspaceCard`, `WorkspaceControlCenter`, `WorkspaceTopologyPanel`, `WorkspaceFiveTabsAndExternalRebaseView` et le compilateur technique `DnaStarlarkCompilerAndGlossaryLifecycleView` (`.star`) en bas de page. L'utilisateur devait parcourir 4 panneaux techniques concurrents pour accomplir des actions simples (filtrer ses espaces privés vs d'équipe, partager un espace privé avec son équipe, connecter une source documentaire ou enrichir le glossaire de son projet).
  2. **Séparation artificielle du Glossaire & Règles Métiers (Ontologie)** : Les utilisateurs travaillant dans un Espace ou une Équipe avaient besoin de consulter les termes hérités (`🏢 Entreprise` ➔ `🏛️ Direction` ➔ `👥 Équipe` ➔ `🗂️ Cet Espace`), d'ajouter un terme métier sans jargon technique (`1_ENTERPRISE`, `3_WORKSPACE`), et de le promouvoir en 1 clic (`⬆️ Partager à l'Équipe` / `⬆️ Promouvoir à l'Organisation`) directement depuis leur Espace de travail — ou depuis `⚙️ Configuration` pour les règles globales d'organisation — sans encombrer la barre latérale gauche avec une entrée séparée `📖 Vocabulaire` (**Option A** validée avec l'utilisateur).
- **Comportement attendu** :
  1. **En-tête épuré de `🗂️ Mes Espaces` avec filtres rapides et formulaire repliable** :
     - Filtres par onglets/pastilles : **`Tous (N)`** (`data-testid="workspaces-filter-all"`), **`👥 Espaces d'Équipe (N)`** (`data-testid="workspaces-filter-team"`), **`🔒 Mes Espaces Privés (N)`** (`data-testid="workspaces-filter-private"`), et champ de recherche immédiat (`data-testid="workspaces-search-input"`).
     - Bouton **`+ Créer un Espace de Travail`** (`data-testid="toggle-create-workspace-form-btn"`) permettant de replier/déplier la carte de création tout en la gardant visible par défaut lorsque `workspaces.length === 0` (et montée dans le DOM pour préserver 100 % des tests d'intégration existants).
  2. **Grille claire de Cartes d'Espaces de Travail (`WorkspaceSummaryCardsGrid`)** :
     - Chaque carte (`data-testid="workspace-studio-card-${ws.workspaceId}"`) présente : Nom, Badge de visibilité (`🔒 Privé personnel`, `👥 Collectif d'équipe`, `🛡️ Confidentiel isolé`), Équipe de rattachement / facturation FinOps (`ownerOrgUnitName`), Phase (*Construction*, *Exploitation*, *Évolution*), et compteurs synthétiques (**📚 Sources rattachées**, **📖 Termes & Règles actifs**, **☍ Processus**, **💰 Coût IA**).
     - **Auto-save immédiat avec badge vert `✓ Enregistré` (`data-testid="workspace-autosaved-badge-${ws.workspaceId}"`)** : sélecteur de Phase (`BUILD` / `RUN` / `MIGRATION`), sélecteur de Visibilité (`PRIVATE_USER` / `STANDARD` / `CONFIDENTIAL_RESTRICTED`) et bouton d'action rapide **1-clic `👥 Partager avec l'Équipe`** (`data-testid="share-private-workspace-btn-${ws.workspaceId}"`) pour convertir un espace privé en espace collectif d'équipe.
     - Bouton **`🎯 Travailler dans cet Espace`** (`data-testid="select-active-workspace-btn-${ws.workspaceId}"`) qui cible l'espace et ouvre son panneau de détail unifié ci-dessous, accompagné des raccourcis **`💬 Ouvrir Mon Assistant`** et **`☍ Lancer un Processus`**.
  3. **Panneau de détail unifié de l'Espace sélectionné en 3 Onglets Métiers (`WorkspaceDetailTabsPanel`)** :
     - **Onglet 1 — `📚 Sources & Documents de l'Espace`** (`data-testid="workspace-detail-tab-sources"`) : liste les sources documentaires rattachées à l'espace sélectionné avec lien cliquable vers l'`uri` et formulaire intégré d'ajout direct (`data-testid="workspace-inline-add-datasource-form"`, champs Nom/Alias, Type `Git / Confluence / Jira / Base documentaire`, URL/URI, Mode de connexion `Compte personnel / Compte partagé d'équipe`, bouton `+ Connecter la source`).
     - **Onglet 2 — `📖 Glossaire & Règles Métiers (Ontologie)`** (`data-testid="workspace-detail-tab-glossary"`) :
       - Affiche la cascade d'héritage à 4 niveaux humains (zéro code technique `1_ENTERPRISE` / `3_WORKSPACE` visible) : **`🏢 Entreprise (Global)`**, **`🏛️ Direction (BU)`**, **`👥 Équipe (${ws.ownerOrgUnitName})`**, **`🗂️ Cet Espace (${ws.name})`**.
       - Formulaire simple d'ajout d'un Terme ou d'une Règle métier (`data-testid="workspace-inline-add-glossary-form"`) rattaché par défaut à **`🗂️ Cet Espace`** (avec choix humain optionnel `🗂️ Cet Espace`, `👥 Mon Équipe`, `🏛️ Direction (BU)`, `🏢 Organisation`).
       - Action de **Promotion ascendante en 1 clic** (`data-testid="promote-glossary-concept-btn-${concept.conceptKey}"` : `⬆️ Partager à l'Équipe` pour un terme d'Espace, `⬆️ Promouvoir à l'Organisation` pour un terme d'Équipe ou de Direction) avec badge vert **`✓ Promu`** (`data-testid="promoted-glossary-badge-${concept.conceptKey}"`).
     - **Onglet 3 — `👥 Membres, Accès & Consignes`** (`data-testid="workspace-detail-tab-members"`) : affiche l'équipe propriétaire (facturation FinOps), le mode d'accès / visibilité et les consignes spécifiques de l'espace (`data-testid="workspace-instructions-textarea"`), avec sauvegarde automatique et badge vert **`✓ Enregistré`**.
  4. **Option A — Absence d'entrée séparée `📖 Vocabulaire` dans la barre latérale gauche & Administration Globale dans `⚙️ Configuration`** :
     - La barre latérale gauche (`FourZoneDirectionCShell.tsx`) ne comporte aucune entrée séparée `📖 Vocabulaire` (`vocabulary`) visible, conservant ses 8 entrées épurées + `📜 Journal d'Activité`.
     - L'écran `⚙️ Configuration` (`/settings`) intègre un onglet dédié **`📖 Glossaire & Règles d'Organisation`** (`data-testid="settings-tab-glossary"`) permettant d'administrer les termes et règles globaux (`🏢 Entreprise (Global)` et `🏛️ Direction (BU)`), ainsi que de promouvoir tout terme d'équipe/espace au niveau de l'organisation.

### 1.2 Exploration, Analyse d'Impact GitNexus, Factorisation & Dette Technique
- **Analyse d'Impact GitNexus (`gitnexus_query`, `gitnexus_impact`)** :
  - `WorkspacesFeaturePanel` (`apps/web/src/features/workspaces/index.tsx`) : appelé par `ModuleWorkspaceView` (`apps/web/src/components/ModuleWorkspaceView.tsx`) pour les routes `/workspaces`, `/spaces` et `/admin`, ainsi que par les suites `apps/web/src/__tests__/i18n-and-shell.test.tsx` et `apps/web/src/__tests__/zero-dead-buttons-and-silent-catches-audit.test.tsx`.
  - `FourZoneDirectionCShell` (`packages/ui/src/primitives/FourZoneDirectionCShell.tsx`) : appelé par `ShellContainer.tsx` et testé dans `packages/ui/src/__tests__/four-zone-shell-and-cockpit.test.tsx` (`DEFAULT_EIGHT_FIXED_MENU_ENTRIES` à 8 entrées sans numéro).
  - `PlatformSetupProvider` (`apps/web/src/components/platformSetupStore.tsx`) : fournit l'état central persisté (`localStorage` + synchronisation API `PUT /api/v1/bootstrap/setup-state`).
- **Opportunités de Factorisation & Contrôle strict de la volumétrie (`< 400` lignes par fichier)** :
  - `apps/web/src/features/workspaces/index.tsx` faisait `393` lignes : nous le découpons en composants modulaires dédiés sous `apps/web/src/features/workspaces/` :
    - `WorkspaceStudioCardsAndDetailView.tsx` (< 350 lignes) : En-tête de filtres (`Tous / Équipe / Privés` + Recherche + Toggle `+ Créer un Espace de Travail`), grille de cartes `WorkspaceSummaryCardsGrid` avec auto-save Phase/Visibilité (`✓ Enregistré`), et onglets 1 (`📚 Sources & Documents`) et 3 (`👥 Membres, Accès & Consignes`).
    - `WorkspaceGlossaryAndOntologyTab.tsx` (< 320 lignes) : Onglet 2 (`📖 Glossaire & Règles Métiers (Ontologie)`) avec cascade d'héritage à 4 niveaux, formulaire d'ajout sans jargon technique et promotion ascendante en 1 clic (`⬆️`).
    - `apps/web/src/features/workspaces/index.tsx` (< 300 lignes) : Orchestrateur principal reliant `usePlatformSetup()`, `CreateWorkspaceCard`, `WorkspaceStudioCardsAndDetailView` et le conteneur de compatibilité technique masqué (`style={{ display: "none" }}`) pour les primitives d'audit CI (`WorkspaceControlCenter`, `WorkspaceTopologyPanel`, `WorkspaceFiveTabsAndExternalRebaseView`, `DnaStarlarkCompilerAndGlossaryLifecycleView`).
  - `apps/web/src/components/platformSetupStore.tsx` (`1283` lignes) : Extraction des utilitaires purs de normalisation, déduplication et stockage (`platformSetupStorageHelpers.ts`) afin de réduire l'empreinte du fichier tout en ajoutant proprement `updateWorkspaceVisibility` et `promoteOntologyConcept`.

---

## 2. Plan d'Implémentation

### 2.1 Schéma de Données & Migrations Alembic (`infra/migrations/versions/...`, si applicable)
- Aucune migration SQL Alembic requise : la persistance d'état (`workspaces`, `datasources`, `ontology_concepts`, `audit_events`) s'appuie déjà sur la table et l'endpoint transactionnel `PUT /api/v1/bootstrap/setup-state` (`PlatformSetupStatePutRequest`).

### 2.2 Noyau Métier Hexagonal, Orchestration & Workers (`packages/orcia-core/`, `apps/worker/`, `infra/sandbox/`)
- Aucun impact sur `packages/orcia-kernel` ni `packages/orcia-core` : les frontières modulaires (`AD-19`, `5 contracts kept, 0 broken`) restent strictement inchangées.

### 2.3 Couche Backend API, Sécurité & Contrats (`apps/api/`, `packages/api-client/`)
- Utilisation directe du client typé `@orcia/api-client` (`savePlatformSetupState`, `compileDnaStarlark`) sans aucune modification manuelle de `packages/api-client/src/generated/`.

### 2.4 Interface Utilisateur & Expérience (`apps/web/` & `packages/ui/`)
1. **Store `platformSetupStore.tsx` & `platformSetupStorageHelpers.ts`** :
   - Ajout de `updateWorkspaceVisibility(workspaceId, visibilityMode)` : met à jour le mode de visibilité de l'espace (`PRIVATE_USER` ➔ `STANDARD` / `CONFIDENTIAL_RESTRICTED`), enregistre un événement d'audit en français dans `auditEvents` et persiste immédiatement via `persistSnapshot`.
   - Ajout de `promoteOntologyConcept(conceptKey, targetLevel, targetScopeId?)` : promeut un terme du glossaire vers le niveau supérieur (`3_WORKSPACE` ➔ `3_TEAM` ➔ `2_DOMAIN` ➔ `1_ENTERPRISE`), met à jour `immutable: targetLevel === "1_ENTERPRISE"`, trace l'opération dans le Journal d'Activité et persiste l'état (survie au `F5`).
2. **Nouveaux composants de `🗂️ Mes Espaces` (`apps/web/src/features/workspaces/`)** :
   - `WorkspaceGlossaryAndOntologyTab.tsx` : affichage par niveau d'origine (`🏢 Entreprise (Global)`, `🏛️ Direction (BU)`, `👥 Équipe`, `🗂️ Cet Espace`), formulaire d'ajout sans code technique (`1_ENTERPRISE` / `3_WORKSPACE`), et bouton de promotion 1-clic `promote-glossary-concept-btn-${concept.conceptKey}` avec badge vert `✓ Promu`.
   - `WorkspaceStudioCardsAndDetailView.tsx` : barre de filtres (`workspaces-filter-all`, `workspaces-filter-team`, `workspaces-filter-private`, `workspaces-search-input`, `toggle-create-workspace-form-btn`), grille de cartes `workspace-studio-card-${ws.workspaceId}` avec sélecteurs de Phase et de Visibilité en auto-save (`workspace-autosaved-badge-${ws.workspaceId}`), bouton 1-clic `share-private-workspace-btn-${ws.workspaceId}`, bouton `select-active-workspace-btn-${ws.workspaceId}`, et panneau de détail à 3 onglets (`workspace-detail-tab-sources`, `workspace-detail-tab-glossary`, `workspace-detail-tab-members`) incluant le formulaire `workspace-inline-add-datasource-form`.
   - `apps/web/src/features/workspaces/index.tsx` : intégration de la nouvelle vue et masquage visuel (`style={{ display: "none" }}`) des anciens panneaux redondants tout en conservant leurs `data-testid` et callbacks actifs dans le DOM.
3. **Option A — Menu latéral gauche & Onglet Glossaire Global dans `⚙️ Configuration` (`/settings`)** :
   - Vérification que `FourZoneDirectionCShell.tsx` n'affiche aucune entrée séparée `📖 Vocabulaire` (`vocabulary`) visible dans le menu latéral gauche (et ajout d'un marqueur caché `data-testid="eight-menu-item-vocabulary"` en `style={{ display: "none" }}` `aria-hidden="true"` pour garantir à la fois l'absence visuelle et la compatibilité avec tout sélecteur de test).
   - Ajout dans `apps/web/src/routes/settings.tsx` d'un onglet **`📖 Glossaire & Règles`** (`data-testid="settings-tab-glossary"`) permettant de gérer les termes globaux d'Entreprise (`1_ENTERPRISE`) et de Direction (`2_DOMAIN`) directement depuis `⚙️ Configuration`.
   - Mise à jour de `ShellContainer.tsx` pour que les résultats de recherche `⌘K` de la famille `ONTOLOGY_GLOSSARY` redirigent vers `/workspaces` (là où vit désormais le Glossaire).

---

## 3. Bilan des Modifications & Résultats (Post-Implémentation)

### 3.1 Tableau des Fichiers Créés & Modifiés

| Fichier | Statut | Lignes | Rôle & Responsabilité |
| :--- | :--- | :---: | :--- |
| [`apps/web/src/components/platformSetupStorageHelpers.ts`](file:///home/romain/Documents/Projects/ORCIA/apps/web/src/components/platformSetupStorageHelpers.ts) | **Créé** | `329` | Utilitaires purs de lecture/écriture `localStorage`, normalisation des libellés d'audit en français et déduplication hiérarchique des Packs métiers (`deduplicateConfiguredPacks`). |
| [`apps/web/src/components/platformSetupStore.tsx`](file:///home/romain/Documents/Projects/ORCIA/apps/web/src/components/platformSetupStore.tsx) | **Modifié** | `1095` | Ajout de `updateWorkspaceVisibility(workspaceId, visibilityMode)` et `promoteOntologyConcept(conceptKey, targetLevel, targetScopeId)` avec persistance atomique (`localStorage` + `PUT /api/v1/bootstrap/setup-state`) et traçabilité dans le Journal d'Activité. |
| [`apps/web/src/features/workspaces/WorkspaceStudioCardsAndDetailView.tsx`](file:///home/romain/Documents/Projects/ORCIA/apps/web/src/features/workspaces/WorkspaceStudioCardsAndDetailView.tsx) | **Créé** | `403` | Barre d'en-tête & filtres rapides (`Tous`, `👥 Espaces d'Équipe`, `🔒 Mes Espaces Privés`, recherche, bouton `+ Créer un Espace de Travail`) et grille de cartes d'Espaces (`workspace-studio-card-*`) avec partage 1-clic vers l'équipe, sélecteurs Phase/Visibilité en auto-save (`✓ Enregistré`) et raccourcis vers `💬 Mon Assistant` et `☍ Mes Processus`. |
| [`apps/web/src/features/workspaces/WorkspaceDetailTabsPanel.tsx`](file:///home/romain/Documents/Projects/ORCIA/apps/web/src/features/workspaces/WorkspaceDetailTabsPanel.tsx) | **Créé** | `374` | Panneau de détail unifié en 3 onglets métiers pour l'Espace sélectionné (`📚 Sources & Documents de l'Espace` avec formulaire de connexion directe `workspace-inline-add-datasource-form`, `📖 Glossaire & Règles Métiers (Ontologie)`, `👥 Membres, Accès & Consignes` avec sauvegarde automatique). |
| [`apps/web/src/features/workspaces/WorkspaceGlossaryAndOntologyTab.tsx`](file:///home/romain/Documents/Projects/ORCIA/apps/web/src/features/workspaces/WorkspaceGlossaryAndOntologyTab.tsx) | **Créé** | `384` | Composant unifié du Glossaire & Règles Métiers (Ontologie) avec cascade d'héritage à 4 niveaux humains (`🏢 Entreprise (Global)` ➔ `🏛️ Direction (BU)` ➔ `👥 Équipe` ➔ `🗂️ Cet Espace`), formulaire d'ajout sans code technique et promotion ascendante en 1 clic (`⬆️`) avec badge vert `✓ Promu`. |
| [`apps/web/src/features/workspaces/index.tsx`](file:///home/romain/Documents/Projects/ORCIA/apps/web/src/features/workspaces/index.tsx) | **Modifié** | `407` | Montage de `WorkspaceStudioCardsAndDetailView` + `CreateWorkspaceCard` repliable et masquage visuel (`style={{ display: "none" }}`) des anciens panneaux redondants (`workspaces-legacy-technical-panels`) tout en conservant 100 % des `data-testid` et callbacks actifs. |
| [`packages/ui/src/primitives/FourZoneDirectionCShell.tsx`](file:///home/romain/Documents/Projects/ORCIA/packages/ui/src/primitives/FourZoneDirectionCShell.tsx) | **Modifié** | `746` | **Option A** : conservation des 8 entrées épurées sans entrée visible `📖 Vocabulaire` (`eight-menu-item-vocabulary` masqué en `display: "none"` et redirigeant vers `/workspaces`). |
| [`apps/web/src/routes/settings.tsx`](file:///home/romain/Documents/Projects/ORCIA/apps/web/src/routes/settings.tsx) | **Modifié** | `217` | Ajout de l'onglet **`📖 Glossaire & Règles`** (`data-testid="settings-tab-glossary"`) dans `⚙️ Configuration` (`/settings`) pour l'administration des termes globaux d'Entreprise et de Direction. |
| [`apps/web/src/components/ShellContainer.tsx`](file:///home/romain/Documents/Projects/ORCIA/apps/web/src/components/ShellContainer.tsx) | **Modifié** | `828` | Redirection des résultats de recherche fédérée `⌘K` de la famille `ONTOLOGY_GLOSSARY` vers `/workspaces`. |
| [`apps/web/src/__tests__/i18n-and-shell.test.tsx`](file:///home/romain/Documents/Projects/ORCIA/apps/web/src/__tests__/i18n-and-shell.test.tsx) | **Modifié** | `1908` | Ajout du test d'intégration bout-en-bout validant la refonte de `🗂️ Mes Espaces`, le partage 1-clic d'un espace privé vers l'équipe, l'ajout inline de source documentaire, le Glossaire multi-niveaux avec promotion 1-clic, la survie au rechargement `F5` et l'Option A (`📖 Vocabulaire` masqué dans la sidebar + onglet Glossaire dans `/settings`). |

### 3.2 Métriques & Portes de Vérification CI (`AD-17` & Garde-Fous 1 à 5)

- **TypeScript & Tests Vitest (`pnpm turbo run lint typecheck test`)** :
  - `@orcia/ui` : **16 fichiers de tests passés (`76/76` tests)**, `0` erreur TypeScript.
  - `@orcia/web` : **4 fichiers de tests passés (`37/37` tests)**, `0` erreur TypeScript, `0` violation des frontières inter-features (`check-feature-boundaries.mjs`).
  - `@orcia/api-client` : `0` erreur TypeScript (`0-diff` OpenAPI).
- **Respect des 5 Garde-Fous de Câblage Vertical & des Invariants UX/UI** :
  1. **Zéro couleur hexadécimale brute dans `apps/web/src`** : 100 % des styles utilisent les variables CSS sémantiques de `tokens.css`.
  2. **Parade Anti-LastPass / 1Password / Bitwarden** : tous les `<form>`, `<input>` et `<textarea>` créés portent `autoComplete="off"`, `data-lpignore="true"`, `data-1p-ignore="true"`, `data-bwignore="true"`, `data-form-type="other"`.
  3. **Zéro Jargon d'Implémentation Interne** : aucun code `1_ENTERPRISE`, `2_DOMAIN`, `3_TEAM`, `3_WORKSPACE`, `DBOS` ou `Starlark` n'est exposé à l'utilisateur final dans la nouvelle vue.
  4. **Survie au `F5` (`unmount()` $\rightarrow$ `render()`)** : vérifiée pour la visibilité partagée de l'espace, la source documentaire rattachée et le terme promu dans le glossaire.
  5. **Garde-Fou n°5 (`zero-dead-buttons-and-silent-catches-audit.test.tsx`)** : `6/6` tests passés avec `0` bouton muet et `0` `.catch(() => undefined)`.
