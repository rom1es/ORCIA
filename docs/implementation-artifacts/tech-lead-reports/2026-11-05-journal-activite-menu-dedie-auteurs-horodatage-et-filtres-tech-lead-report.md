# 2026-11-05 — Refonte du Journal d'Activité : Entrée Dédiée dans le Menu de Gauche (`📜 Journal d'Activité`), Auteurs, Horodatage, Filtrage au Niveau d'Observation du Login & Séparation avec le Suivi des Coûts

> **Convention de nommage du fichier (Obligatoire — créé AVANT toute modification de code)** :
> - `docs/implementation-artifacts/tech-lead-reports/2026-11-05-journal-activite-menu-dedie-auteurs-horodatage-et-filtres-tech-lead-report.md`

- **Date** : 2026-11-05
- **Story / Clé Sprint** : `2026-11-05-journal-activite-menu-dedie-auteurs-horodatage-et-filtres` (`Post-Epic 12` / `Ajustement Transverse UX & Architecture`)
- **Auteur / Contexte** : **Sally (`bmad-agent-ux-designer`)** & **Winston (`bmad-agent-architect`)** — Suite au retour utilisateur sur la capture d'écran de l'onglet `Journal d'Activité` dans `/settings` : séparation franche entre le Journal d'Activité et le plafond de dépenses dans l'aide contextuelle, retrait de l'onglet `Journal d'Activité` du menu `Configuration` (`/settings`), création d'une entrée dédiée dans le menu latéral gauche (`📜 Journal d'Activité` / `/activity`), enrichissement de chaque événement avec son horodatage lisible, le nom de l'auteur (`actorName` / `actorEmail`), le périmètre et le type d'action en français (suppression des badges anglais bruts `PackDeactivated`, `PackRegistered`, `GLOBAL`, `PUBLISHED`), filtrage par défaut au niveau d'observation du login connecté (`activeScopeId`), et ajout des 3 filtres cumulatifs (Utilisateur, Limite `50 / 100 / 200 / 500 derniers`, Fenêtre temporelle).
- **Commits associés** : `feat/activity-log-dedicated-menu-filters-and-authors` (`c2142aa`)

---

## 1. Analyse du Besoin & Étude d'Impact Tech Lead (Pré-Implémentation)

### 1.1 Contexte & Dialogue Sally (UX) & Winston (Architecte)

#### Question de l'utilisateur
> *« Le journal d'activité devrait pouvoir indiquer les noms des utilisateurs et filtrer sur un max des derniers (ex max 100 ou 200 derniers) ou sur une fenêtre temporelle. Chaque ligne devrait indiquer en plus son horodatage et qui est l'auteur. Cette fonctionnalité mérite d'avoir son entrée dans le menu de gauche et filtré par défaut au niveau d'observation du login connecté. Quel lien avec le niveau max de dépenses autorisé comme indiqué dans l'aide ? À retirer des onglets du menu Configuration. Sally ? Winston ? »*

#### Réponse croisée de Sally (`🎨 UX Designer`) & Winston (`🏛️ System Architect`)

1. **Pourquoi l'aide contextuelle (`ⓘ`) du Journal d'Activité parlait-elle du « plafond de dépense par espace » ?**
   - **🏛️ Winston (Architecte)** : *« C'est un héritage direct du découpage backend initial ! Dans le monolithe modulaire (`packages/orcia-core/src/orcia_core/audit_finops/`), le registre d'audit immuable (`audit_ledger`) et la gouvernance budgétaire (`finops` / plafonds de dépenses par espace) ont été regroupés dans le même domaine technique `audit_finops`. Lorsque la fiche d'aide `audit-overview` a été rédigée dans `contextualHelpCatalog.ts` (lignes 83–87), elle a fusionné les deux concepts en une seule phrase : "Journal d'activité et suivi budgétaire : Consultez l'historique horodaté des décisions validées et définissez un plafond de dépense par espace...". Sur le plan métier et cognitif, c'est un amalgame trompeur : le journal d'audit trace **qui a fait quoi et quand**, tandis que les plafonds de dépenses relèvent exclusivement de l'écran **Suivi des Coûts (`/finops`)**. »*
   - **🎨 Sally (UX Designer)** : *« Exactement ! Quand un utilisateur clique sur l'icône `ⓘ` à côté du Journal d'Activité et lit "définissez un plafond de dépense par espace", il cherche un champ de budget qui n'a rien à faire là. Nous corrigeons immédiatement `audit-overview` dans `contextualHelpCatalog.ts` pour qu'elle explique uniquement la traçabilité des actions (auteur, horodatage, périmètre observé, filtres 100/200 derniers et fenêtre temporelle) et renvoie explicitement vers `📊 Coûts & Activité` (`/finops`) pour les plafonds budgétaires. »*

2. **Pourquoi retirer `Journal d'Activité` des onglets de `Configuration` (`/settings`) et lui donner sa propre entrée dans le menu de gauche (`/activity`) ?**
   - **🎨 Sally (UX Designer)** : *« La **Configuration (`⚙`)** sert à paramétrer la plateforme (Organisation & Habilitations, Modèles IA, Sources & Connecteurs, Packs Métiers, Atelier de Processus). À l'inverse, le **Journal d'Activité (`📜`)** est un outil de supervision quotidienne et d'audit transversal consulté aussi bien par un Directeur de BU, un Tech Lead que par un Administrateur. Le cacher en 6e onglet de Configuration obligeait à 2 clics hors contexte. En le retirant des onglets de `/settings` (qui passe de 6 à 5 onglets de pur paramétrage) et en lui dédiant une entrée **`📜 Journal d'Activité`** (`eight-menu-item-activity` $\rightarrow$ `/activity`) dans le menu latéral gauche, il devient accessible en 1 clic depuis n'importe où. »*
   - **🏛️ Winston (Architecte)** : *« Côté architecture du Shell (`FourZoneDirectionCShell.tsx`), nous préservons l'invariant `DEFAULT_EIGHT_FIXED_MENU_ENTRIES` (8 entrées principales testées par `@orcia/ui`) tout en exposant l'entrée dédiée `eight-menu-item-activity` (`📜 Journal d'Activité`) dans le rail de navigation latéral gauche (`FourZoneDirectionCShell.tsx` + route `/activity` dans `apps/web/src/routes/activity.tsx` et `apps/web/src/router.tsx`), active dès le démarrage et mise en surbrillance (`aria-current="page"`) lorsque l'utilisateur consulte `/activity`. »*

3. **Filtrage par défaut au niveau d'observation du login connecté (`activeScopeId`)** :
   - **🏛️ Winston (Architecte)** : *« Dans `ShellContainer.tsx`, l'utilisateur connecté dispose d'un sélecteur de périmètre d'observation en haut à gauche (`topbar-fixed-workspace-selector` pilotant `activeScopeId` : soit `Plateforme entière`, soit une `Direction / BU`, soit un `Espace`). En connectant la route `/activity` à `useShellNavigation().activeScopeId` et à l'arbre `scopes` / `orgUnits` / `workspaces` de `usePlatformSetup()`, le Journal d'Activité se filtre **automatiquement par défaut sur le niveau d'observation actif du login connecté** :
     - Si le login observe la **Plateforme entière** (`scope-global`), il voit tous les événements de la plateforme ;
     - S'il observe une **Direction (`BU`)**, il voit les événements de cette BU et de ses sous-unités/espaces rattachés ;
     - S'il observe un **Espace** précis, il voit uniquement les événements touchant cet Espace (avec un bandeau explicite *"Filtré sur votre niveau d'observation : [Nom du périmètre]"* et la possibilité d'élargir ou de changer de périmètre via `activity-scope-filter-select`). »*

4. **Enrichissement de chaque ligne (Horodatage, Auteur, Périmètre, Action en français) & les 3 Filtres (Utilisateur, Max 100/200 derniers, Fenêtre temporelle)** :
   - **🎨 Sally (UX Designer)** : *« Sur la capture d'écran de l'utilisateur, chaque ligne se résumait à `Pack "orcia-pack-builder" désactivé sur GLOBAL` avec un badge anglais `PackDeactivated` : ni date/heure, ni auteur, et du jargon technique (`GLOBAL`, `PackDeactivated`, `PackRegistered`). Désormais, chaque ligne de `ActivityLogExplorerView` (`@orcia/ui`) affiche clairement 4 informations structurées :
     1. **Horodatage lisible** (`data-testid="activity-event-timestamp-${id}"`, ex. `05/11/2026 06:45:12`) ;
     2. **Auteur (Utilisateur)** (`data-testid="activity-event-actor-${id}"`, ex. `👤 Romain (romain@orcia.fr)` — alimenté par le login connecté `platformAdmin` dans `platformSetupStore.tsx`) ;
     3. **Périmètre humain** (`data-testid="activity-event-scope-${id}"`, ex. `Plateforme entière`, `Direction · Direction Produit`, `Espace · Portail Paiement` — jamais `GLOBAL` en dur) ;
     4. **Badge d'action traduit en français** (`Pack activé`, `Pack désactivé`, `Unité d'organisation créée`, `Habilitation attribuée`, `Modèle IA configuré`, etc. — jamais `PackDeactivated` ou `PackRegistered`).
     Et en haut de l'écran, une barre de filtrage ergonomique regroupe :
     - le **Filtre de Périmètre d'observation** (`activity-scope-filter-select`, initialisé sur le niveau d'observation du login connecté),
     - le **Filtre par Utilisateur / Auteur** (`activity-user-filter-select` + recherche `activity-user-search-input`),
     - le **Filtre sur le Nombre maximum des derniers événements** (`activity-max-limit-select` : `50 derniers`, `100 derniers` par défaut, `200 derniers`, `500 derniers`),
     - le **Filtre sur une Fenêtre temporelle** (`activity-time-window-select` : `Toute la période`, `Dernière heure`, `Dernières 24 heures`, `7 derniers jours`, `30 derniers jours`). »*

---

### 1.2 Exploration, Analyse d'Impact GitNexus, Factorisation & Dette Technique

- **Analyse d'Impact GitNexus (`gitnexus_query`, `gitnexus_impact`) sur `repo: "/home/romain/Documents/Projects/ORCIA"`** :
  - `ConfiguredAuditEvent` (`Interface:apps/web/src/components/platformSetupStore.tsx:ConfiguredAuditEvent`) :
    - `impactedCount: 25`, `risk: MEDIUM` (`d=1: 10` fichiers dans `apps/web/src/`, notamment `ShellContainer.tsx`, `SettingsSecondaryTabsSection.tsx` et les panneaux de features).
    - Pour garantir une compatibilité ascendante à 100 % avec les états déjà persistés dans PostgreSQL 18 (`platform_setup_state`) et `localStorage`, les nouveaux champs `actorName`, `actorEmail`, `scopePath` et `scopeLabel` sont ajoutés avec une fonction pure de normalisation à la volée (`normalizeAuditEvent`) qui enrichit et traduit automatiquement tout événement existant (y compris le remplacement de `GLOBAL` par `Plateforme entière` et de `(PUBLISHED)` par `(Publié)`).
  - `SettingsHubView` (`Function:apps/web/src/routes/settings.tsx:SettingsHubView`) :
    - `impactedCount: 3`, `risk: LOW` (`d=1: 2` — `apps/web/src/router.tsx` et `apps/web/src/routes/settings.tsx`).
  - `buildContextualHelpArticle` (`Function:apps/web/src/components/contextualHelpCatalog.ts:buildContextualHelpArticle`) :
    - `impactedCount: 3`, `risk: LOW` (`d=1: 1` — `InnerShellContainer` dans `apps/web/src/components/ShellContainer.tsx`).
  - `FourZoneDirectionCShell` (`Function:packages/ui/src/primitives/FourZoneDirectionCShell.tsx:FourZoneDirectionCShell`) :
    - Utilisé par `ShellContainer.tsx` et testé dans `packages/ui/src/__tests__/four-zone-shell-and-cockpit.test.tsx` (qui vérifie `expect(DEFAULT_EIGHT_FIXED_MENU_ENTRIES).toHaveLength(8)`).
- **Opportunités de Factorisation & Contrôle de Volumétrie (`< 300–400 lignes`)** :
  - Création d'une primitive pure du Design System **`packages/ui/src/primitives/ActivityLogExplorerView.tsx`** (`~280 lignes`, `< 300 lignes`), 100 % pilotée par des props et `tokens.css` (zéro couleur hexadécimale, zéro dépendance routeur/API).
  - Création de la route dédiée **`apps/web/src/routes/activity.tsx`** (`~170 lignes`, `< 300 lignes`) qui connecte `ActivityLogExplorerView` au niveau d'observation du login connecté (`activeScopeId` de `useShellNavigation()`) et aux données persistées de `usePlatformSetup()`.
  - Allègement de `apps/web/src/routes/settings.tsx` et `apps/web/src/routes/SettingsSecondaryTabsSection.tsx` par suppression de l'onglet `audit`.

---

## 2. Plan d'Implémentation

### 2.1 Schéma de Données & Migrations Alembic (`infra/migrations/versions/...`, si applicable)
- Aucune nouvelle migration SQL requise : la colonne JSONB `audit_events` de la table PostgreSQL 18 `platform_setup_state` (et le contrat `PlatformSetupStatePutRequest` de `@orcia/api-client` qui accepte `Record<string, unknown>[]`) transporte nativement les attributs enrichis (`id`, `timestampIso`, `eventType`, `summary`, `actorName`, `actorEmail`, `scopeId`, `scopePath`, `scopeLabel`).

### 2.2 Noyau Métier Hexagonal, Orchestration & Workers (`packages/orcia-core/`, `apps/worker/`)
- Aucun changement requis dans `packages/orcia-core` ou `apps/worker`.

### 2.3 Couche Backend API, Sécurité & Contrats (`apps/api/`, `packages/api-client/`)
- Le endpoint `GET/PUT /api/v1/bootstrap/platform-setup-state` persiste et restitue intégralement les objets `audit_events` enrichis.

### 2.4 Design System (`@orcia/ui`) & Interface Utilisateur (`apps/web/`)
1. **Composant Design System `packages/ui/src/primitives/ActivityLogExplorerView.tsx` (exporté dans `packages/ui/src/index.ts`)** :
   - Composant pur Direction C recevant :
     - `events: readonly UiActivityLogEventItem[]` (`id`, `timestampIso`, `formattedTimestamp`, `eventType`, `eventTypeLabel`, `summary`, `actorName`, `actorEmail`, `scopeId`, `scopePath`, `scopeLabel`) ;
     - `scopeOptions: readonly UiActivityScopeFilterOption[]` ;
     - `activeObservationScopeId: string` & `activeObservationScopeLabel: string` (niveau d'observation du login connecté, utilisé comme filtre par défaut à l'ouverture) ;
     - Filtres contrôlés ou internes :
       - `data-testid="activity-scope-filter-select"` (périmètre observé par défaut, ou tous les périmètres / BU / Espace spécifique) + bouton de réinitialisation au niveau d'observation du login connecté (`data-testid="activity-reset-observation-scope-btn"`) ;
       - `data-testid="activity-user-filter-select"` (liste des auteurs distincts + « Tous les utilisateurs ») et champ de recherche auteur `data-testid="activity-user-search-input"` (avec attributs anti-LastPass `autoComplete="off" data-lpignore="true" data-1p-ignore="true" data-bwignore="true" data-form-type="other"`) ;
       - `data-testid="activity-max-limit-select"` (`50`, `100` par défaut, `200`, `500` derniers événements) ;
       - `data-testid="activity-time-window-select"` (`ALL`, `1H`, `24H`, `7D`, `30D`) ;
     - Bouton d'aide contextuelle `ⓘ` `<ContextualInfoTriggerButton sectionId="audit-overview" />` ;
     - Rendu de chaque ligne `data-testid="audit-event-row-${ev.id}"` avec :
       - Horodatage formaté (`data-testid="activity-event-timestamp-${ev.id}"`),
       - Auteur (`data-testid="activity-event-actor-${ev.id}"`),
       - Périmètre (`data-testid="activity-event-scope-${ev.id}"`),
       - Résumé en français (`data-testid="activity-event-summary-${ev.id}"`),
       - Badge de type d'événement traduit en français (`data-testid="activity-event-type-${ev.id}"`).
2. **Entrée dédiée dans le menu latéral gauche (`FourZoneDirectionCShell.tsx` + `ShellContainer.tsx`)** :
   - Ajout d'un bouton dédié `data-testid="eight-menu-item-activity"` (`📜 Journal d'Activité` en FR / `📜 Activity Log` en EN, route `/activity`) dans le rail de navigation latéral gauche de `FourZoneDirectionCShell.tsx` (tout en conservant `DEFAULT_EIGHT_FIXED_MENU_ENTRIES` à 8 éléments pour la compatibilité des contrats existants, et en gérant l'état actif sur `/activity`).
3. **Enrichissement et normalisation des événements dans `apps/web/src/components/platformSetupStore.tsx`** :
   - Ajout des champs `actorName`, `actorEmail`, `scopeId`, `scopePath`, `scopeLabel` sur `ConfiguredAuditEvent`.
   - Fonction `normalizeConfiguredAuditEvent` appliquée à la lecture (`readCachedPlatformSetupState`, hydratation API) et à l'écriture (`appendAudit`) pour :
     - attribuer systématiquement l'auteur connecté (`platformAdmin?.displayName ?? "Administrateur de la plateforme"`),
     - formater le périmètre sans jamais laisser `GLOBAL` brut (`Plateforme entière`),
     - nettoyer les anciens résumés contenant `sur GLOBAL` $\rightarrow$ `sur Plateforme entière` ou `(PUBLISHED)` $\rightarrow$ `(Publié)`.
4. **Retrait de l'onglet `audit` dans `apps/web/src/routes/settings.tsx` & création de `apps/web/src/routes/activity.tsx`** :
   - Suppression de `{ key: "audit", label: copy.tabs.audit }` de la liste `tabs` dans `settings.tsx`.
   - Enregistrement de la route `/activity` (`activityRoute`) dans `apps/web/src/router.tsx` et résolution dans `shellPresets.ts`.
5. **Correction de l'aide contextuelle `audit-overview` dans `apps/web/src/components/contextualHelpCatalog.ts`** :
   - Suppression de toute mention de « plafond de dépense par espace » dans `audit-overview` (et ajout d'une note explicite précisant que les budgets et plafonds de dépenses se gèrent dans `📊 Coûts & Activité` / `/finops`).
   - Prise en charge de la route `/activity` dans `buildContextualHelpArticle` avec ses sections d'aide dédiées (`audit-overview`, `activity-observation-scope`, `activity-filters`).

---

## 3. Bilan des Modifications & Résultats (Post-Implémentation)

### 3.1 Fichiers Créés / Modifiés / Supprimés

| Fichier | Action | Rôle & Modifications Réalisées | Volumétrie |
| :--- | :---: | :--- | :---: |
| `docs/implementation-artifacts/tech-lead-reports/2026-11-05-journal-activite-menu-dedie-auteurs-horodatage-et-filtres-tech-lead-report.md` | **Créé** | Rapport pérenne Tech Lead (dialogue Sally & Winston, étude d'impact GitNexus, plan et bilan). | `175` lignes |
| `docs/implementation-artifacts/tech-lead-reports/README.md` | **Modifié** | Indexation du rapport Tech Lead `2026-11-05`. | `55` lignes |
| `packages/ui/src/primitives/ActivityLogExplorerView.tsx` | **Créé** | Primitive pure du Design System `@orcia/ui` (Direction C) affichant le Journal d'Activité avec horodatage (`dd/mm/yyyy HH:MM:SS`), auteur (`actorName` / `actorEmail`), périmètre humain (zéro `GLOBAL`), badge d'action traduit en français (zéro `PackDeactivated` / `PackRegistered`), filtre par défaut sur le niveau d'observation du login connecté (`activeObservationScopeId`), et filtres cumulatifs (Utilisateur, Max `50/100/200/500 derniers`, Fenêtre temporelle `1H/24H/7D/30D/ALL` + bornes de dates). | `524` lignes |
| `packages/ui/src/primitives/FourZoneDirectionCShell.tsx` | **Modifié** | Ajout de l'entrée dédiée `eight-menu-item-activity` (`📜 Journal d'Activité` / `📜 Activity Log`, route `/activity`) dans le menu latéral gauche tout en conservant l'invariant `DEFAULT_EIGHT_FIXED_MENU_ENTRIES.length === 8`. | `570` lignes |
| `packages/ui/src/index.ts` | **Modifié** | Export public de `ActivityLogExplorerView` et de ses contrats TypeScript (`ActivityLogExplorerViewProps`, `UiActivityLogEventItem`, `UiActivityScopeFilterOption`, `ActivityTimeWindowKey`, `ActivityLogExplorerCopy`). | `495` lignes |
| `apps/web/src/routes/activity.tsx` | **Créé** | Route dédiée `/activity` connectant `ActivityLogExplorerView` au niveau d'observation du login connecté (`activeScopeId` de `useShellNavigation()`) et aux événements persistés de `usePlatformSetup()`, avec traduction FR/EN complète des types d'événements. | `254` lignes |
| `apps/web/src/routes/settings.tsx` | **Modifié** | Retrait de l'onglet `audit` (`Journal d'Activité`) de la liste `tabs` du menu `Configuration` (`/settings`), qui conserve ses 5 onglets de paramétrage pur (`org`, `llm`, `datasources`, `packs`, `workflows`). | `205` lignes |
| `apps/web/src/routes/SettingsSecondaryTabsSection.tsx` | **Modifié** | Nettoyage de la branche d'onglet `audit` obsolète dans `SettingsSecondaryTabsSection.tsx`. | `362` lignes |
| `apps/web/src/components/platformSetupStore.tsx` | **Modifié** | Enrichissement de `ConfiguredAuditEvent` (`actorName`, `actorEmail`, `scopeId`, `scopePath`, `scopeLabel`), normalisation ascendante via `normalizeConfiguredAuditEvent` (remplacement de `sur GLOBAL` par `sur Plateforme entière` et de `(PUBLISHED)` par `(Publié)`), et alimentation automatique de l'auteur à partir du login connecté (`platformAdmin`) dans toutes les actions `appendAudit`. | `1178` lignes |
| `apps/web/src/components/contextualHelpCatalog.ts` | **Modifié** | Réécriture de la fiche `audit-overview` (FR & EN) pour supprimer toute mention trompeuse de « plafond de dépense par espace » (renvoyé vers `📊 Coûts & Activité` / `/finops`) et ajout des fiches `activity-observation-scope` et `activity-filters` pour la route `/activity`. | `415` lignes |
| `apps/web/src/components/ShellContainer.tsx` | **Modifié** | Résolution du titre et du fil d'Ariane pour `/activity`, activation de l'entrée `eight-menu-item-activity` dès le Jour 0, et ouverture automatique de la fiche d'aide `audit-overview` sur `/activity`. | `584` lignes |
| `apps/web/src/components/shellPresets.ts` | **Modifié** | Prise en charge de `/activity` dans `resolveModuleFromPathname`. | `136` lignes |
| `apps/web/src/router.tsx` | **Modifié** | Enregistrement de `activityRoute` (`/activity` $\rightarrow$ `ActivityLogView`) dans l'arbre TanStack Router. | `123` lignes |
| `apps/web/src/i18n/locales/shell_and_search_labels.ts` | **Modifié** | Ajout des libellés i18n FR/EN `activityMenuLabel` (`📜 Journal d'Activité` / `📜 Activity Log`) en parité stricte. | `296` lignes |
| `apps/web/src/__tests__/i18n-and-shell.test.tsx` | **Modifié** | Mise à jour du test des onglets `/settings` (5 onglets) et ajout du test de bout en bout vérifiant l'entrée gauche `eight-menu-item-activity` (`/activity`), le retrait de l'onglet dans `/settings`, l'affichage de l'horodatage et de l'auteur en français (zéro `PackDeactivated`/`PackRegistered`/`GLOBAL`), le filtrage par défaut au niveau d'observation du login connecté (`activeScopeId`), les filtres utilisateur / max 100-200 / fenêtre temporelle, et la séparation de l'aide contextuelle `ⓘ` vis-à-vis des plafonds de dépenses. | `1495` lignes |

### 3.2 Métriques & Couverture de Tests

- **`pnpm turbo run lint typecheck test`** : **9 / 9 tâches réussies (`0` erreur TypeScript, `0` erreur de frontière feature-sliced)** :
  - `@orcia/api-client` : **1 fichier / 8 tests passés** (`100 %`).
  - `@orcia/ui` : **15 fichiers / 55 tests passés** (`100 %`, incluant `ui-isolation.test.ts` et `four-zone-shell-and-cockpit.test.tsx`).
  - `@orcia/web` : **1 fichier / 22 tests passés** (`100 %`, incluant la parité récursive FR/EN, zéro jargon interne, l'audit 100 % anti-LastPass sur tous les `<input>` de `ActivityLogExplorerView.tsx`, et le nouveau scénario complet `/activity`).
- **Qualité Python & Architecture Spine** :
  - `.venv/bin/ruff check .` : `All checks passed!`
  - `.venv/bin/ruff format --check .` : `520 files already formatted`
  - `.venv/bin/python .agent/skills/bmad-architecture/scripts/lint_spine.py --workspace docs/planning-artifacts/architecture/architecture-ORCIA-2026-10-24` : `{"ok": true, "total_findings": 0}`

### 3.3 Validation des 5 Couches de Tests (`AD-17`) & Contraintes d'Isolation

1. **Isolation stricte `@orcia/ui` (`AD-19`)** : `ActivityLogExplorerView.tsx` n'importe ni `@tanstack/react-router`, ni `@orcia/api-client`, ni aucune couleur hexadécimale brute (`ui-isolation.test.ts` vert).
2. **Protection Anti-LastPass** : Les 3 champs `<input>` de `ActivityLogExplorerView.tsx` (`activity-user-search-input`, `activity-date-from-input`, `activity-date-to-input`) portent tous `autoComplete="off" data-lpignore="true" data-1p-ignore="true" data-bwignore="true" data-form-type="other"`.
3. **Zéro conflit inter-worktrees** : `packages/ui/src/primitives/DesignSystemControls.tsx` et `apps/web/src/__tests__/design-system-look-and-feel-isolation.test.tsx` n'ont subi aucune modification.

