# 2026-11-05 — Dialogue Sally (UX/UI) & Winston (Architecte) : Refonte & Épuration de l'Écran d'Habilitations IAM (`/settings` — Organisation & Habilitations)

> **Convention de nommage du fichier (Obligatoire — créé AVANT toute modification de code)** :
> - Demande d'ajustement, correctif ou évolution hors Story : `docs/implementation-artifacts/tech-lead-reports/2026-11-05-dialogue-sally-winston-correction-ecran-habilitations-iam-tech-lead-report.md`

- **Date** : 2026-11-05
- **Story / Clé Sprint** : `2026-11-05-dialogue-sally-winston-correction-ecran-habilitations-iam` (`Post-Epic 12` / `Ajustement UX/UI & Architecture IAM`)
- **Auteur / Contexte** : Binôme **Sally (`bmad-agent-ux-designer`)** & **Winston (`bmad-agent-architect`)** — Résolution des 6 anomalies UX/UI et d'architecture relevées par l'utilisateur sur la section `2. Attribuer et Gérer les Règles d'Habilitation` de l'écran `/settings` (`Organisation & Habilitations`), respect strict des 11 règles fondamentales UX/UI et des 3 règles de Microcopy Centrée Utilisateur & Aide Contextuelle Ciblée (`ⓘ`), et découpage modulaire `< 400 lignes`.
- **Commits associés** : `d11d89a`

---

## 1. Analyse du Besoin & Étude d'Impact Tech Lead (Pré-Implémentation)

### 1.1 Contexte, Problématique & Dialogue Structuré entre Sally (UX/UI) et Winston (Architecte)

Sur l'écran **`Configuration de la Plateforme & Organisation` (`/settings`, onglet `Organisation & Habilitations`)**, l'utilisateur a soulevé 6 anomalies majeures à partir d'une capture d'écran réelle de la section **`2. Attribuer et Gérer les Règles d'Habilitation`**.

Voici le dialogue d'analyse et de décision entre **🎨 Sally (UX Designer & UI Specialist)** et **🏛️ Winston (System Architect & Technical Design Leader)** répondant point par point aux observations de l'utilisateur :

---

#### Point 1 — Grisage de la section « 2. Attribuer et Gérer les Règles d'Habilitation » tant qu'aucune organisation (BU ou Espace) n'est connue en base de données

- **🎨 Sally (UX/UI)** :
  > « Sur la capture d'écran, la section 1 indique *"Aucune unité d'organisation (BU ou Espace) configurée"*, mais la section 2 juste en dessous laisse tous ses champs actifs ! Du coup, l'utilisateur tente de créer une règle d'accès alors que la structure de l'entreprise est encore vierge. Selon nos **Règles UX #2 (Simplicité / Loi de Hick)** et **#4 (Feedback immédiat)**, tant qu'aucune Direction (BU) ni aucun Espace de travail n'existe (`orgUnits.length === 0 && workspaces.length === 0`), tous les contrôles de la section 2 doivent être **grisés (`disabled`)** avec une indication visuelle claire (`data-testid="rbac-grants-disabled-no-org-hint"`) : *"Créez d'abord au moins une Direction (BU) ou un Espace dans la section 1 ci-dessus avant de pouvoir attribuer des règles d'habilitation."* Dès que la première unité est créée en base, la section 2 se déverrouille instantanément. »
- **🏛️ Winston (Architecte)** :
  > « Du point de vue du modèle de domaine IAM (`AD-21`), un `RolePermissionGrant` rattaché à un arbre d'organisation vide n'a aucun sens opérationnel au Jour 0. Je valide le verrouillage réactif piloté par `const hasNoKnownOrganization = orgUnits.length === 0 && workspaces.length === 0;` synchronisé avec PostgreSQL 18 via `usePlatformSetup()`. Nous appliquons `disabled={hasNoKnownOrganization}` sur `rbac-subject-type-select`, `rbac-subject-input`, le sélecteur de périmètre cible, `rbac-effect-select`, toutes les cases à cocher `rbac-verb-checkbox-*` et le bouton `create-rbac-grant-btn`. »

---

#### Point 2 — Pourquoi y avait-il un champ texte libre à côté de « Sur quoi ? » et suppression de cette redondance

- **🏛️ Winston (Architecte)** :
  > « Expliquons franchement pourquoi ce champ texte (`rbac-scope-input`) existait à côté de la liste déroulante (`rbac-scope-preset-select`) : lors du prototypage initial de la Story 8.1/8.3, quand aucune unité d'organisation n'était encore créée, la liste déroulante était masquée et un `<input type="text">` servait de rustine pour taper manuellement un identifiant de périmètre (`GLOBAL` ou un slug). Ensuite, quand des BU/Espaces ont été ajoutés, la liste déroulante est apparue **à côté** de l'input texte au lieu de le remplacer ! Résultat : l'utilisateur voit une liste déroulante déjà positionnée sur `GLOBAL` et un champ texte libre à droite où il a légitimement tapé `?????` en se demandant ce qu'on attendait de lui. »
- **🎨 Sally (UX/UI)** :
  > « C'est l'exemple typique d'une dette d'interface qui viole la **Loi de Hick (1 champ = 1 intention)**. Puisque la section 2 n'est désormais active que lorsqu'au moins une organisation (BU ou Espace) existe en base, l'utilisateur ne doit **jamais** avoir à taper un slug technique au clavier ! Nous remplaçons le couple bancal `(select + input texte)` par **un unique sélecteur déroulant clair** sous **`Sur quoi ? (Périmètre cible)`** proposant :
  > - `Plateforme entière` (valeur `GLOBAL`)
  > - chaque Direction (BU) connue en base (`Direction (BU) : <Nom>`)
  > - chaque Espace connu en base (`Espace : <Nom>`) »

---

#### Point 3 — Concurrence directe entre « Action principale » (`rbac-verb-select`) et « Habilitations à attribuer : » (`rbac-verbs-checkbox-group`)

- **🎨 Sally (UX/UI)** :
  > « Regardons la capture : sur la première ligne du formulaire, il y a une liste déroulante **"Action principale : Exécuter / Utiliser"**, et juste en dessous une barre de cases à cocher **"Habilitations à attribuer : [x] Tous [x] Créer [x] Lire..."**. Les deux contrôles modifient la même liste de verbes et se contredisent visuellement : si je choisis "Exécuter" en haut mais que je coche "Tous" en bas, quelle est mon action principale ? Aucune ! C'est un vestige d'avant l'ajout de la sélection multiple par cases à cocher.
  > **Décision UX** : Nous **supprimons purement et simplement** la liste déroulante *"Action principale"* (`rbac-verb-select`). Il ne reste qu'un seul endroit unique, visuel et immédiat pour choisir les droits accordés : le groupe de cases à cocher **"Habilitations à attribuer :"** (`Tous`, `Créer`, `Lire / Voir les secrets`, `Modifier`, `Supprimer`, `Exécuter / Utiliser`, `Déléguer des droits`). »
- **🏛️ Winston (Architecte)** :
  > « En supprimant `grantVerb` et `rbac-verb-select`, l'état du formulaire dépend exclusivement de `grantSelectedVerbs: readonly UiPermissionVerb[]` (initialisé par défaut à `["execute"]`). Si aucune case n'est cochée, le bouton d'ajout est désactivé. C'est plus simple, sans état dupliqué ni effet de bord. »

---

#### Point 4 — Éradication des termes anglais entre parenthèses dans l'interface française

- **🎨 Sally (UX/UI)** :
  > « Notre **Règle Impérative #1 de Microcopy** interdit formellement la plomberie et les identifiants techniques anglais dans l'interface française. Or, l'écran affichait les enums du code entre parenthèses partout ! Voici le nettoyage intégral que nous appliquons en français :
  > 1. **Type de bénéficiaire** : `Rôle (ROLE)` $\rightarrow$ **`Rôle`** ; `Utilisateur (USER)` $\rightarrow$ **`Utilisateur`**.
  > 2. **Périmètre global** : `GLOBAL (Plateforme)` $\rightarrow$ **`Plateforme entière`**.
  > 3. **Effet de la règle** :
  >    - `Autoriser (ALLOW) — ...` $\rightarrow$ **`Autoriser — Accorde les actions cochées sur le périmètre choisi`**
  >    - `Interdire (DENY) — ...` $\rightarrow$ **`Interdire — Bloque explicitement ces actions (prioritaire sur toute autorisation)`**
  >    - `Couper l'héritage (INHERITANCE_BLOCK) — ...` $\rightarrow$ **`Isoler ce périmètre — N'applique pas les droits hérités de la Direction parente`**
  > 4. **Cases à cocher des 6 habilitations** : suppression totale de `(create)`, `(read)`, `(update)`, `(delete)`, `(execute)`, `(grant)` $\rightarrow$ **`Créer`**, **`Lire / Voir les secrets`**, **`Modifier`**, **`Supprimer`**, **`Exécuter / Utiliser`**, **`Déléguer des droits`**.
  > 5. **Liste des règles créées en bas** :
  >    - Au lieu de `Rôle (ROLE:Product Manager) → Périmètre cible : ...`, afficher **`Rôle : Product Manager → Périmètre cible : ...`** (avec le nom lisible du périmètre cible, ex. `Plateforme entière` ou le nom de la BU/Espace).
  >    - Au lieu du badge anglais brut `grant (ALLOW)`, afficher un badge en français : **`Déléguer des droits · Autorisé`** (ou `Interdit` / `Périmètre isolé`).
  > 6. **Section 1 (Création d'unité)** : remplacer `BU (Business Unit / Direction)` par **`Direction / Pôle (BU)`**. »

---

#### Point 5 — Explication claire de « Périmètre cible » + Icône d'aide contextuelle `ⓘ` dédiée (`iam-target-scope`)

- **🎨 Sally (UX/UI)** :
  > « L'utilisateur demande *"Que signifie Périmètre cible ?"*. Conformément à notre **Règle Impérative #3 (Zéro pavé explicatif dans l'espace de travail — Renvoi systématique par icône `ⓘ` vers la colonne d'aide contextuelle droite)** :
  > 1. Nous intitulons le champ **`Sur quoi ? (Périmètre cible)`** et plaçons juste à côté du libellé un bouton **`ⓘ` (`<ContextualInfoTriggerButton sectionId="iam-target-scope" ... />`)**.
  > 2. Au clic sur ce `ⓘ`, la colonne d'aide contextuelle à droite s'ouvre automatiquement et surligne la section **`help-section-iam-target-scope`** rédigée en français clair et sans jargon :
  >    *"Qu'est-ce que le Périmètre cible (« Sur quoi ? ») ? Le périmètre cible désigne l'endroit précis de votre organisation où s'applique la règle d'habilitation : soit toute la plateforme, soit une Direction (BU) entière et ses équipes, soit un seul Espace de travail (équipe/projet). Par exemple, donner un droit à « Product Manager » sur le périmètre cible « Espace : MonCompte » signifie que ce droit ne s'exercera que dans l'espace MonCompte, sans donner accès aux autres espaces de l'entreprise."* »

---

#### Point 6 — Contrôle de volumétrie (`< 400 lignes`) et découpage modulaire de `apps/web/src/routes/settings.tsx`

- **🏛️ Winston (Architecte)** :
  > « `apps/web/src/routes/settings.tsx` a atteint `1 450 lignes` en cumulant les 6 onglets de configuration dans un seul composant monolithique. Conformément à la politique Tech Lead (`GEMINI.md` — découpage systématique au-delà de `300–400 lignes`), nous extrayons :
  > - [`apps/web/src/routes/SettingsIamOrganizationSection.tsx`](file:///home/romain/Documents/Projects/ORCIA/apps/web/src/routes/SettingsIamOrganizationSection.tsx) (`< 360 lignes`) pour l'onglet 1 (`Organisation & Habilitations`),
  > - [`apps/web/src/routes/SettingsOtherTabsSection.tsx`](file:///home/romain/Documents/Projects/ORCIA/apps/web/src/routes/SettingsOtherTabsSection.tsx) (`< 380 lignes`) ou sous-composants par onglet afin que `settings.tsx` redescende sous la barre des `350 lignes`. »

---

### 1.2 Exploration, Analyse d'Impact GitNexus, Factorisation & Dette Technique
- **Analyse d'Impact GitNexus (`gitnexus_context`, `gitnexus_impact` sur `repo: "/home/romain/Documents/Projects/ORCIA"`)** :
  - `SettingsHubView` (`Function:apps/web/src/routes/settings.tsx:SettingsHubView`) :
    - `risk: LOW`, `impactedCount: 3` (`d=1`: `apps/web/src/routes/settings.tsx`, `apps/web/src/router.tsx` ; `d=2`: `apps/web/src/main.tsx`).
  - `buildContextualHelpArticle` (`Function:apps/web/src/components/contextualHelpCatalog.ts:buildContextualHelpArticle`) :
    - Appelé par `ShellContainer.tsx` pour alimenter la colonne d'aide contextuelle droite (`Zone 4`) et le centre d'aide (`/help`).
- **Opportunités de Factorisation & Résorption de Dette Technique** :
  - Extraction de `SettingsIamOrganizationSection.tsx` depuis `settings.tsx`, isolant toute la logique d'organisation (`BU` / `Espace`) et d'habilitations (`RBAC`) dans un composant dédié, lisible et maintenable (`< 360 lignes`).

---

## 2. Plan d'Implémentation

### 2.1 Schéma de Données & Migrations Alembic (`infra/migrations/versions/...`, si applicable)
- Aucune migration Alembic requise : la persistance PostgreSQL 18 de `orgUnits`, `workspaces` et `rbacGrants` (`GET/PUT /api/v1/bootstrap/platform-setup-state` + tables `org_units`, `workspaces`, `role_permission_grants`) est déjà en place et inchangée.

### 2.2 Noyau Métier Hexagonal, Orchestration & Workers (`packages/orcia-core/`, `apps/worker/`, `infra/sandbox/`)
- Aucun changement requis dans `packages/orcia-core` ou `apps/worker`.

### 2.3 Couche Backend API, Sécurité & Contrats (`apps/api/`, `packages/api-client/`)
- Aucun changement de contrat OpenAPI requis (`0-diff` préservé).

### 2.4 Interface Utilisateur & Expérience (`apps/web/`)
1. **Création de [`apps/web/src/routes/SettingsIamOrganizationSection.tsx`](file:///home/romain/Documents/Projects/ORCIA/apps/web/src/routes/SettingsIamOrganizationSection.tsx)** :
   - **Section 1 (`Structure de l'Organisation`)** :
     - Libellé français `Direction / Pôle (BU)` (au lieu de `BU (Business Unit / Direction)`).
   - **Section 2 (`2. Attribuer et Gérer les Règles d'Habilitation`)** :
     - Calcul de `const hasNoKnownOrganization = orgUnits.length === 0 && workspaces.length === 0;`.
     - Affichage d'un bandeau d'information `data-testid="rbac-grants-disabled-no-org-hint"` lorsque `hasNoKnownOrganization === true`, et application de `disabled={hasNoKnownOrganization}` (ainsi qu'une opacité visuelle `0.55`) sur tous les champs et boutons du formulaire.
     - Suppression de l'input texte redondant à côté de `Sur quoi ? (Périmètre cible)` : conservation d'un **unique `<select>`** (`data-testid="rbac-scope-select"`, avec alias compatible test `data-scope-selector="true"`) listant `Plateforme entière` (`GLOBAL`), les `orgUnits` (`Direction (BU) : ...` / `Espace : ...`) et les `workspaces` connus en base.
     - Ajout du bouton `ⓘ` `<ContextualInfoTriggerButton sectionId="iam-target-scope" ... />` immédiatement à côté du libellé `Sur quoi ? (Périmètre cible)`.
     - Suppression du sélecteur concurrent `Action principale` (`rbac-verb-select`) : sélection des droits exclusivement via le groupe de cases à cocher `Habilitations à attribuer :` (`rbac-verbs-checkbox-group`).
     - Purge de tous les termes anglais entre parenthèses en français (`Rôle`, `Utilisateur`, `Plateforme entière`, `Créer`, `Lire / Voir les secrets`, `Modifier`, `Supprimer`, `Exécuter / Utiliser`, `Déléguer des droits`, `Autoriser — ...`, `Interdire — ...`, `Isoler ce périmètre — ...`, et badges de règles en français `Exécuter / Utiliser · Autorisé`).
2. **Mise à jour de [`apps/web/src/components/contextualHelpCatalog.ts`](file:///home/romain/Documents/Projects/ORCIA/apps/web/src/components/contextualHelpCatalog.ts)** :
   - Ajout de la section `iam-target-scope` (*« Qu'est-ce que le Périmètre cible (« Sur quoi ? ») ? »*) dans `CONFIGURATION_SECTIONS_FR` et `CONFIGURATION_SECTIONS_EN`, et nettoyage des résidus d'identifiants techniques (`ROLE:Chef1`, `INHERITANCE_BLOCK`, `ALLOW`, `DENY`, `create, read...`) dans les textes français de l'aide contextuelle.
3. **Mise à jour de [`apps/web/src/__tests__/i18n-and-shell.test.tsx`](file:///home/romain/Documents/Projects/ORCIA/apps/web/src/__tests__/i18n-and-shell.test.tsx)** :
   - Vérification du grisage initial de la section 2 tant qu'aucune BU ni aucun Espace n'existe, puis de son déverrouillage dès la création d'une BU/Espace ;
   - Vérification de l'absence du champ texte redondant et du sélecteur concurrent « Action principale » ;
   - Vérification de l'absence totale des termes anglais entre parenthèses (`(ROLE)`, `(USER)`, `(ALLOW)`, `(DENY)`, `(INHERITANCE_BLOCK)`, `(create)`, `(read)`, `(update)`, `(delete)`, `(execute)`, `(grant)`) en français ;
   - Vérification de l'ouverture de l'aide contextuelle droite et de l'activation de `help-section-iam-target-scope` au clic sur `contextual-info-trigger-iam-target-scope`.

---

## 3. Bilan des Modifications & Résultats (Post-Implémentation)

### 3.1 Fichiers Développés & Modifiés
| Fichier | Nature (Création / Modification / Refactoring) | Description synthétique |
| :--- | :--- | :--- |
| [`apps/web/src/routes/settings.tsx`](file:///home/romain/Documents/Projects/ORCIA/apps/web/src/routes/settings.tsx) | Refactoring (`1 450 -> 188 lignes`) | Orchestrateur léger des 6 onglets de configuration déléguant l'onglet 1 à `SettingsIamOrganizationSection` et les onglets 2 à 6 à `SettingsSecondaryTabsSection`. |
| [`apps/web/src/routes/SettingsOrganizationUnitsBlock.tsx`](file:///home/romain/Documents/Projects/ORCIA/apps/web/src/routes/SettingsOrganizationUnitsBlock.tsx) | Création (`285 lignes`) | Section `1. Structure de l'Organisation (Directions / BU & Espaces)` extraite avec libellés français épurés (`Direction / Pôle (BU)`, `Plateforme entière`) et protection anti-suppression d'éléments rattachés. |
| [`apps/web/src/routes/SettingsIamOrganizationSection.tsx`](file:///home/romain/Documents/Projects/ORCIA/apps/web/src/routes/SettingsIamOrganizationSection.tsx) | Création (`365 lignes`) | Section `2. Attribuer et Gérer les Règles d'Habilitation` : grisage complet (`disabled={hasNoKnownOrganization}`) + message d'aide tant qu'aucune BU/Espace n'existe en base, suppression de l'input texte redondant (`rbac-scope-input`) au profit d'un unique sélecteur `Sur quoi ? (Périmètre cible)` accompagné de l'icône `ⓘ` (`sectionId="iam-target-scope"`), suppression du sélecteur concurrent `Action principale` (`rbac-verb-select`), et purge intégrale des termes anglais entre parenthèses en français. |
| [`apps/web/src/routes/SettingsSecondaryTabsSection.tsx`](file:///home/romain/Documents/Projects/ORCIA/apps/web/src/routes/SettingsSecondaryTabsSection.tsx) | Création (`396 lignes`) | Extraction modulaire des onglets `Modèles IA`, `Connecteurs`, `Packs Métiers`, `Atelier de Processus` et `Journal d'Audit` pour respecter la règle `< 400 lignes`. |
| [`apps/web/src/components/contextualHelpCatalog.ts`](file:///home/romain/Documents/Projects/ORCIA/apps/web/src/components/contextualHelpCatalog.ts) | Modification (`319 lignes`) | Ajout de la section d'aide contextuelle `iam-target-scope` (*« Qu'est-ce que le Périmètre cible (« Sur quoi ? ») ? »*) en FR et EN, et nettoyage des identifiants techniques anglais dans les textes français. |
| [`apps/web/src/__tests__/i18n-and-shell.test.tsx`](file:///home/romain/Documents/Projects/ORCIA/apps/web/src/__tests__/i18n-and-shell.test.tsx) | Modification | Vérification automatisée des 5 corrections UX/UI (grisage initial de la section 2 puis déverrouillage après création d'une BU, absence de `rbac-scope-input` et `rbac-verb-select`, zéro terme anglais entre parenthèses en FR, et ouverture de `help-section-iam-target-scope` au clic sur `contextual-info-trigger-iam-target-scope`). |

### 3.2 Résultats Chiffrés, Métriques & Qualité
- **Volumétrie des fichiers (`< 400 lignes`)** :
  - `apps/web/src/routes/settings.tsx` : `188 lignes` (contre `1 450 lignes` avant intervention)
  - `apps/web/src/routes/SettingsOrganizationUnitsBlock.tsx` : `285 lignes`
  - `apps/web/src/routes/SettingsIamOrganizationSection.tsx` : `365 lignes`
  - `apps/web/src/routes/SettingsSecondaryTabsSection.tsx` : `396 lignes`
  - `apps/web/src/components/contextualHelpCatalog.ts` : `319 lignes`
- **Qualité statique & Architecture** :
  - `pnpm turbo run lint typecheck test` : `9/9 tasks successful` (`18/18` tests Vitest dans `@orcia/web`, `0 error` TypeScript, `0` violation de frontière inter-features).
  - `ruff check .` & `ruff format --check .` : `All checks passed! (514 files already formatted)`.
  - `lint_spine.py` : `{"ok": true, "spine": "ARCHITECTURE-SPINE.md", "total_findings": 0}`.

### 3.3 Validation & Procédure de Test (5 Couches `AD-17` + 4 Garde-Fous de Câblage Vertical)
- **Couche 1 & 5 — Tests Unitaires, Intégration UI & Survie au `F5` (`Vitest`)** :
  - Validation du grisage initial (`disabled`) de tous les champs et boutons de la section `2. Attribuer et Gérer les Règles d'Habilitation` tant que `orgUnits.length === 0 && workspaces.length === 0`, et déverrouillage dynamique dès la création d'une BU ou d'un Espace.
  - Validation de la suppression de l'input texte redondant (`rbac-scope-input`) et du sélecteur concurrent (`rbac-verb-select`).
  - Validation de l'absence totale des termes anglais entre parenthèses (`(ROLE)`, `(USER)`, `(ALLOW)`, `(DENY)`, `(INHERITANCE_BLOCK)`, `(create)`, `(read)`, `(update)`, `(delete)`, `(execute)`, `(grant)`) en français.
  - Validation du clic sur l'icône `ⓘ` (`contextual-info-trigger-iam-target-scope`) qui ouvre la colonne d'aide contextuelle droite (`four-zone-contextual-help-column`) et active la section `help-section-iam-target-scope` (`data-active="true"`).
  - Validation de la survie au rechargement complet `F5` (`unmount()` $\rightarrow$ `render()`).

