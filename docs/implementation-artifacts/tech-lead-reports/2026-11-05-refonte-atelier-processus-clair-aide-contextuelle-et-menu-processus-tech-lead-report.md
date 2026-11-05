# 2026-11-05 — Dialogue Sally (UX/UI) & Winston (Architecte) : Refonte de l'Atelier de Processus, Clarification Métier, Aide Contextuelle (`ⓘ`) & Accès Direct dans `☍ Mes Processus` (`/processes`)

> **Convention de nommage du fichier (Obligatoire — créé AVANT toute modification de code)** :
> - Demande d'ajustement, correctif ou évolution hors Story : `docs/implementation-artifacts/tech-lead-reports/2026-11-05-refonte-atelier-processus-clair-aide-contextuelle-et-menu-processus-tech-lead-report.md`

- **Date** : 2026-11-05
- **Story / Clé Sprint** : `2026-11-05-refonte-atelier-processus-clair-aide-contextuelle-et-menu-processus` (`Post-Epic 12` / `Ajustement UX/UI & Architecture Processus`)
- **Auteur / Contexte** : Binôme **Sally (`bmad-agent-ux-designer`)** & **Winston (`bmad-agent-architect`)** — Résolution du retour utilisateur sur l'onglet « Atelier de Processus » (`/settings` vs `/processes`), suppression intégrale du jargon anglais et des compteurs cryptiques (`PUBLISHED`, `DRAFT`, `TRASH`, `ACTIVE_RUNS`, `PAUSED_ARBITRATION`, `(0p / 0s)`, `e3b0c44298fc`), ajout des icônes d'aide contextuelle `ⓘ` (`ContextualInfoTriggerButton`) et montage de l'atelier simplifié directement dans `☍ Mes Processus` (`/processes`).
- **Commits associés** : `en cours`

---

## 1. Analyse du Besoin & Étude d'Impact Tech Lead (Pré-Implémentation)

### 1.1 Contexte, Problématique & Dialogue Structuré entre Sally (UX/UI) et Winston (Architecte)

L'utilisateur a transmis une capture d'écran de l'onglet **`Atelier de Processus`** dans **`Configuration de la Plateforme & Organisation` (`/settings`)** et a formulé le constat suivant :
> *« Je ne comprends pas à quoi sert cet écran ? Est-ce l'écran pour construire des nouveaux workflows ? Si oui, pourquoi n'est-il pas dans Processus ? Pas d'aide avec icône i rond. Trop d'informations à saisir sans explication. Trop abscons. »*

Voici le dialogue d'analyse et de conception entre **🎨 Sally (`bmad-agent-ux-designer`)** et **🏛️ Winston (`bmad-agent-architect`)** répondant point par point aux questions légitimes de l'utilisateur :

---

#### Question 1 — « À quoi sert cet écran ? Est-ce l'écran pour construire de nouveaux workflows ? Si oui, pourquoi n'est-il pas dans Processus ? »

- **🏛️ Winston (System Architect)** :
  > « L'utilisateur met le doigt sur une incohérence historique d'architecture de navigation entre l'Epic 8 et les Epics 9/12 :
  > 1. Lors de la Story 8.5 (`Epic 8`), le menu latéral à 8 entrées n'existait pas encore sous sa forme définitive et l'éditeur de modèles de processus avait été logé dans le 5e onglet de `/settings` (`Atelier de Processus`).
  > 2. Puis, lors des Epics 9 et 12, nous avons introduit l'entrée de menu dédiée **`☍ Mes Processus`** (`/processes`, rendue par `GatesFeaturePanel` dans `apps/web/src/features/gates/index.tsx`), mais celle-ci n'affichait qu'un bandeau vide renvoyant vers `/settings` ainsi que les outils avancés de Packs Métiers !
  > **Résultat** : un utilisateur qui souhaite créer, consulter ou lancer ses processus métiers clique naturellement sur **`☍ Mes Processus`** (`/processes`) et ne trouve pas l'atelier de création de processus, tandis que `/settings` héberge un formulaire technique isolé. »
- **🎨 Sally (UX Designer & UI Specialist)** :
  > « Selon nos **Règles Fondamentales UX #1 (Centrer sur l'utilisateur)** et **#2 (Simplicité — 1 module = 1 intention claire)** :
  > - **L'endroit naturel pour concevoir et gérer ses processus est `☍ Mes Processus` (`/processes`)** ! Nous y plaçons directement en tête d'écran le nouveau composant unifié et limpide **`SimplifiedProcessBuilderSection`**.
  > - Et dans **`Configuration` (`/settings`, onglet `Atelier de Processus`)**, nous affichons ce même composant simplifié précédé d'un bandeau d'orientation clair avec un bouton d'accès direct **`Ouvrir dans ☍ Mes Processus`** (`navigateToRoute("/processes")`), ce qui guide immédiatement l'utilisateur tout en préservant 100 % de compatibilité avec les parcours existants. »

---

#### Question 2 — « Pourquoi cet écran était-il si abscons (trop d'informations sans explication, anglais brut, compteurs incompréhensibles) ? »

- **🎨 Sally (UX Designer & UI Specialist)** :
  > « Sur la capture d'écran de l'utilisateur, l'ancien assemblage (`WorkflowTopGovernanceBar` + formulaire brut + `LayersInspectorPopover`) violait nos **3 Règles Impératives de Microcopy Centrée Utilisateur** :
  > 1. **Des badges d'état en anglais majuscule brut** : `PUBLISHED 0`, `DRAFT 0`, `TRASH 0`, `ACTIVE_RUNS 0`, `PAUSED_ARBITRATION 0`, `ON` — incompréhensibles pour un utilisateur métier francophone.
  > 2. **Des compteurs et empreintes cryptiques** : `e3b0c44298fc` (un bout de hash SHA-256 à vide !) et `(0p / 0s)` (censé signifier "0 paramètre / 0 section").
  > 3. **Du jargon technique d'implémentation** : *"Clé du workflow"*, *"Paramètres requis (csv)"*, *"Sections Markdown (csv)"*, *"Pré-prompt système du workflow"*, *"Inspecteur de Couches du Sous-Workflow"*.
  > 4. **Aucune hiérarchie ni explication** : 5 champs juxtaposés sur une même ligne sans `<label>` explicite, obligeant l'utilisateur à deviner ce qu'il doit saisir.
  >
  > **Notre refonte UX/UI dans `SimplifiedProcessBuilderSection.tsx`** :
  > - **Zéro badge anglais ni compteur cryptique** : nous remplaçons la barre technique par des compteurs synthétiques en français clair : **`Publiés`**, **`Brouillons`**, et un sélecteur de statut lisible (**`Brouillon (en préparation)`** / **`Publié (prêt à l'emploi)`**).
  > - **Un parcours guidé en 3 étapes numérotées et auto-porteuses (< 2 secondes)** :
  >   - **Étape 1 — Identité du processus** : **Nom du processus** (ex. *« Revue de contrat fournisseur »*) avec génération automatique de l'identifiant technique (`workflow-key-input` pré-rempli automatiquement à partir du titre ou modifiable librement).
  >   - **Étape 2 — Objectif et instructions données aux agents** (`workflow-preprompt-textarea`, accompagné de son icône **`ⓘ`** `workflows-instructions`) : décrire simplement en langage naturel ce que le processus doit accomplir.
  >   - **Étape 3 — Informations au lancement et structure du livrable (optionnel)** (`workflow-params-input` = *Informations demandées au lancement*, `workflow-sections-input` = *Rubriques attendues dans le document final*, accompagné de son icône **`ⓘ`** `workflows-deliverable-contract`).
  > - **Les 3 grandes étapes types du processus** (avec icône **`ⓘ`** `workflows-steps-layers` et boutons **`Actif` / `Ignoré`** en français) :
  >   1. *1. Collecte des documents et du contexte*
  >   2. *2. Analyse par les agents et vérification croisée*
  >   3. *3. Validation humaine finale du livrable*
  > - **La liste claire des processus enregistrés** juste en dessous, affichant le titre, le statut (`Publié` / `Brouillon`), les rubriques attendues et les étapes actives. »

---

#### Question 3 — « Pas d'aide avec icône `ⓘ` rond »

- **🎨 Sally (UX/UI)** & **🏛️ Winston (Architecte)** :
  > « Conformément à la **Règle Impérative #3 (Zéro pavé explicatif dans l'espace de travail — Renvoi systématique par icône `ⓘ` `ContextualInfoTriggerButton` vers la colonne d'aide contextuelle droite)**, nous ajoutons **4 déclencheurs `ⓘ`** dans `SimplifiedProcessBuilderSection.tsx` et leurs sections correspondantes dans `apps/web/src/components/contextualHelpCatalog.ts` (disponibles à la fois sur `/settings` ET sur `/processes`) :
  > 1. `workflows-overview` (*À quoi sert l'Atelier de Processus ?*) à côté du titre principal ;
  > 2. `workflows-instructions` (*Comment rédiger l'objectif et les instructions du processus ?*) à côté de l'étape 2 ;
  > 3. `workflows-deliverable-contract` (*Informations d'entrée et rubriques du livrable final — optionnel*) à côté de l'étape 3 ;
  > 4. `workflows-steps-layers` (*Les 3 grandes étapes d'exécution d'un processus*) à côté du panneau des étapes clés. »

---

### 1.2 Exploration, Analyse d'Impact GitNexus, Factorisation & Dette Technique
- **Analyse d'Impact GitNexus (`gitnexus_query`, `gitnexus_context`, `gitnexus_impact` sur `repo: "/home/romain/Documents/Projects/ORCIA"`)** :
  - `GatesFeaturePanel` (`Function:apps/web/src/features/gates/index.tsx:GatesFeaturePanel`) :
    - `risk: LOW`, `impactedCount: 16` (`d=1` : `ModuleWorkspaceView.tsx` ; `d=2` : routes TanStack Router `/processes` et `/gates`).
  - `buildContextualHelpArticle` (`Function:apps/web/src/components/contextualHelpCatalog.ts:buildContextualHelpArticle`) :
    - `risk: LOW`, `impactedCount: 3` (`d=1` : `InnerShellContainer` dans `ShellContainer.tsx` ; `d=2` : `ShellContainer`).
- **Opportunités de Factorisation (`DRY`) & Contrôle de Volumétrie (`< 300–400 lignes`)** :
  - Création du composant partagé [`apps/web/src/components/SimplifiedProcessBuilderSection.tsx`](file:///home/romain/Documents/Projects/ORCIA/apps/web/src/components/SimplifiedProcessBuilderSection.tsx) (`< 300 lignes`) réutilisé à la fois dans `apps/web/src/features/gates/index.tsx` (`/processes`) et dans `apps/web/src/routes/SettingsSecondaryTabsSection.tsx` (`/settings`, branche `activeTab === "workflows"`).
  - Réduction simultanée de la taille de `SettingsSecondaryTabsSection.tsx` (suppression de 80 lignes de formulaire inline remplacées par l'appel à `<SimplifiedProcessBuilderSection />`).

---

## 2. Plan d'Implémentation

### 2.1 Schéma de Données & Migrations Alembic (`infra/migrations/versions/...`, si applicable)
- Aucune migration Alembic requise : la persistance PostgreSQL 18 des processus (`workflows` dans `platform_setup_state` + `catalog_items` via `upsertWorkflow` de `platformSetupStore.tsx`) est déjà câblée de bout en bout et survit au rechargement `F5`.

### 2.2 Noyau Métier Hexagonal, Orchestration & Workers (`packages/orcia-core/`, `apps/worker/`, `infra/sandbox/`)
- Aucun changement requis dans `packages/orcia-core` ou `apps/worker`.

### 2.3 Couche Backend API, Sécurité & Contrats (`apps/api/`, `packages/api-client/`)
- Aucun changement requis sur les contrats OpenAPI (`0-diff`).

### 2.4 Interface Utilisateur & Expérience (`apps/web/`)
1. **Création de [`apps/web/src/components/SimplifiedProcessBuilderSection.tsx`](file:///home/romain/Documents/Projects/ORCIA/apps/web/src/components/SimplifiedProcessBuilderSection.tsx)** (`< 300 lignes`) :
   - En-tête clair avec titre explicite, résumé en une phrase de la finalité de l'écran et bouton `ⓘ` (`contextual-info-trigger-workflows-overview`).
   - Bandeau optionnel (lorsqu'affiché depuis `/settings`) permettant de basculer en 1 clic vers `☍ Mes Processus` (`/processes`).
   - Compteurs synthétiques en français (`Publiés`, `Brouillons`) sans aucun badge anglais (`PUBLISHED`, `DRAFT`, `TRASH`, `ACTIVE_RUNS`, `PAUSED_ARBITRATION`, `(0p / 0s)`).
   - Formulaire guidé en 3 étapes (`data-testid="create-workflow-form"`) conservant tous les `data-testid` attendus (`workflow-title-input`, `workflow-key-input`, `workflow-preprompt-textarea`, `workflow-params-input`, `workflow-sections-input`, `save-workflow-btn`) avec génération automatique de l'identifiant si `workflow-key-input` est laissé vide.
   - Sélection claire des 3 grandes étapes d'exécution du processus avec bouton `ⓘ` (`contextual-info-trigger-workflows-steps-layers`) et états `Actif` / `Ignoré`.
   - Liste des processus enregistrés (`workflow-saved-list`) permettant de visualiser immédiatement chaque processus créé et de basculer son statut (`Brouillon` / `Publié`).
2. **Enrichissement de [`apps/web/src/components/contextualHelpCatalog.ts`](file:///home/romain/Documents/Projects/ORCIA/apps/web/src/components/contextualHelpCatalog.ts)** :
   - Ajout des 4 sections d'aide contextuelle (`workflows-overview`, `workflows-instructions`, `workflows-deliverable-contract`, `workflows-steps-layers`) en français et en anglais, accessibles aussi bien depuis `/settings` que depuis `/processes` (`☍ Mes Processus`).
3. **Montage dans [`apps/web/src/features/gates/index.tsx`](file:///home/romain/Documents/Projects/ORCIA/apps/web/src/features/gates/index.tsx) (`/processes`) et [`apps/web/src/routes/SettingsSecondaryTabsSection.tsx`](file:///home/romain/Documents/Projects/ORCIA/apps/web/src/routes/SettingsSecondaryTabsSection.tsx) (`/settings`)** :
   - Montage de `<SimplifiedProcessBuilderSection />` en haut de `GatesFeaturePanel` (`/processes`).
   - Remplacement du bloc `if (activeTab === "workflows")` (lignes 287–370 de `SettingsSecondaryTabsSection.tsx`) par `<SimplifiedProcessBuilderSection />`.
4. **Tests unitaires et d'intégration dans [`apps/web/src/__tests__/i18n-and-shell.test.tsx`](file:///home/romain/Documents/Projects/ORCIA/apps/web/src/__tests__/i18n-and-shell.test.tsx)** :
   - Vérification de la présence directe de l'Atelier de Processus dans `/processes` (`☍ Mes Processus`).
   - Vérification de l'absence totale des badges anglais bruts (`PUBLISHED`, `DRAFT`, `TRASH`, `ACTIVE_RUNS`, `PAUSED_ARBITRATION`, `(0p / 0s)`).
   - Vérification de l'ouverture de la colonne d'aide contextuelle à droite et du surlignage des sections `help-section-workflows-overview`, `help-section-workflows-instructions`, `help-section-workflows-deliverable-contract` et `help-section-workflows-steps-layers` au clic sur leurs boutons `ⓘ` respectifs.

---

## 3. Bilan des Modifications & Résultats (Post-Implémentation)

### 3.1 Fichiers Développés & Modifiés
| Fichier | Nature (Création / Modification / Refactoring) | Description synthétique |
| :--- | :--- | :--- |
| [`apps/web/src/components/SimplifiedProcessBuilderSection.tsx`](file:///home/romain/Documents/Projects/ORCIA/apps/web/src/components/SimplifiedProcessBuilderSection.tsx) | Création (`288 lignes`) | Composant unifié de création et gestion des processus métiers (`< 300 lignes`) : zéro badge anglais brut (`PUBLISHED`, `DRAFT`, `TRASH`, `ACTIVE_RUNS`, `PAUSED_ARBITRATION`, `(0p / 0s)`), parcours guidé en 3 étapes avec génération automatique de l'identifiant technique à partir du titre, sélection claire des 3 grandes étapes d'exécution (`✓ Étape active` / `Étape ignorée`), liste des processus enregistrés, et 4 déclencheurs d'aide contextuelle `ⓘ` (`workflows-overview`, `workflows-instructions`, `workflows-deliverable-contract`, `workflows-steps-layers`). |
| [`apps/web/src/features/gates/index.tsx`](file:///home/romain/Documents/Projects/ORCIA/apps/web/src/features/gates/index.tsx) | Modification (`116 lignes`) | Montage direct de `<SimplifiedProcessBuilderSection />` en tête de l'écran `☍ Mes Processus` (`/processes`) pour que l'utilisateur trouve immédiatement l'atelier de création et de gestion de ses processus dans le menu dédié. |
| [`apps/web/src/routes/SettingsSecondaryTabsSection.tsx`](file:///home/romain/Documents/Projects/ORCIA/apps/web/src/routes/SettingsSecondaryTabsSection.tsx) | Refactoring (`397 -> 342 lignes`) | Remplacement de l'ancien formulaire technique et des barres `WorkflowTopGovernanceBar` / `LayersInspectorPopover` dans la branche `if (activeTab === "workflows")` par `<SimplifiedProcessBuilderSection />`. |
| [`apps/web/src/components/contextualHelpCatalog.ts`](file:///home/romain/Documents/Projects/ORCIA/apps/web/src/components/contextualHelpCatalog.ts) | Modification (`392 lignes`) | Ajout des 4 sections d'aide contextuelle dédiées (`workflows-overview`, `workflows-instructions`, `workflows-deliverable-contract`, `workflows-steps-layers`) en français et en anglais, actives aussi bien sur `/processes` que sur `/settings`. |
| [`apps/web/src/__tests__/i18n-and-shell.test.tsx`](file:///home/romain/Documents/Projects/ORCIA/apps/web/src/__tests__/i18n-and-shell.test.tsx) | Modification (`926 lignes`) | Ajout des vérifications automatisées sur `/processes` : présence directe de l'atelier de processus, absence totale des badges anglais bruts et compteurs cryptiques, ouverture ciblée de la colonne d'aide contextuelle droite au clic sur les boutons `ⓘ`, et création d'un processus par simple saisie de son titre avec auto-génération de l'identifiant. |
| [`docs/implementation-artifacts/tech-lead-reports/README.md`](file:///home/romain/Documents/Projects/ORCIA/docs/implementation-artifacts/tech-lead-reports/README.md) | Modification | Référencement du rapport Tech Lead dans l'index général. |

### 3.2 Résultats Chiffrés, Métriques & Qualité
- **Volumétrie des fichiers (`< 400 lignes`)** :
  - `apps/web/src/components/SimplifiedProcessBuilderSection.tsx` : `288 lignes` (`< 300 lignes`)
  - `apps/web/src/features/gates/index.tsx` : `116 lignes`
  - `apps/web/src/routes/SettingsSecondaryTabsSection.tsx` : `342 lignes` (contre `397 lignes` avant intervention)
  - `apps/web/src/components/contextualHelpCatalog.ts` : `392 lignes` (`< 400 lignes`)
- **Qualité statique & Architecture** :
  - `pnpm turbo run lint typecheck test` : `9/9 tasks successful` (`18/18` tests Vitest dans `@orcia/web`, `8/8` dans `@orcia/api-client`, `34/34` dans `@orcia/ui`, `0 error` TypeScript, `0` violation de frontière inter-features).
  - `.venv/bin/ruff check .` & `.venv/bin/ruff format --check .` : `All checks passed! (515 files already formatted)`.
  - `.venv/bin/python .agent/skills/bmad-architecture/scripts/lint_spine.py` : `{"ok": true, "spine": "ARCHITECTURE-SPINE.md", "total_findings": 0}`.

### 3.3 Validation & Procédure de Test (5 Couches `AD-17` + 4 Garde-Fous de Câblage Vertical)
- **Couche 1 & 5 — Tests Unitaires, Intégration UI & Survie au `F5` (`Vitest`)** :
  - Vérification que l'Atelier de Processus (`settings-workflows-section`) est directement affiché en tête de `/processes` (`☍ Mes Processus`) ET dans `/settings` (onglet `Atelier de Processus`).
  - Vérification qu'aucun badge anglais brut ni compteur cryptique (`PUBLISHED 0`, `DRAFT 0`, `TRASH 0`, `ACTIVE_RUNS`, `PAUSED_ARBITRATION`, `(0p / 0s)`, `e3b0c44298fc`) n'apparaît dans l'interface.
  - Vérification que les boutons `ⓘ` (`contextual-info-trigger-workflows-overview`, `contextual-info-trigger-workflows-instructions`, `contextual-info-trigger-workflows-deliverable-contract`) ouvrent la colonne d'aide contextuelle à droite (`four-zone-contextual-help-column`) et activent la section explicative correspondante (`data-active="true"`).
  - Vérification de la création d'un processus en saisissant uniquement son titre (*« Revue de contrat fournisseur »*) avec génération automatique de la clé (`revue-de-contrat-fournisseur`) et de la survie complète au rechargement `F5` (`unmount()` $\rightarrow$ `render()`).

