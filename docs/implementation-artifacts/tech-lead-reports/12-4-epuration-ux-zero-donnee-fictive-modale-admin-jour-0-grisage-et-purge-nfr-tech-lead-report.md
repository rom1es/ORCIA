# [Story 12.4 — Épuration UX « Zéro Donnée Fictive », Modale de Création du Compte Administrateur au 1er Démarrage, Grisage des Fonctionnalités Non Configurées, Nettoyage de la Sidebar & Purge des Libellés NFR]

- **Date** : 2026-10-31
- **Story / Clé Sprint** : `12-4-epuration-ux-zero-donnee-fictive-modale-admin-jour-0-grisage-et-purge-nfr` (`Epic 12`)
- **Auteur / Contexte** : Sally (UX Designer) & Amelia (Senior Dev) — Application stricte des 11 règles fondamentales UX/UI (`EXPERIENCE.md`, `DESIGN.md`) suite à la revue visuelle du portail SPA (`apps/web`).
- **Commits associés** : `Story 12.4`

---

## 1. Analyse du Besoin & Étude d'Impact Tech Lead (Pré-Implémentation)

### 1.1 Contexte & Problématique
Lors de l'inspection du portail SPA (`apps/web`), 7 écarts par rapport au credo **« Partir d'une interface vide »** et aux **6 Règles Fondamentales de l'UX** (Centrer sur l'utilisateur, Loi de Hick / Minimalisme) ont été identifiés :
1. **Absence de modale de création du compte Administrateur au 1er démarrage** : L'application démarrait directement sur le Cockpit avec un profil fictif pré-connecté (`Administrateur / Tech Lead · [SECURITY_COMPLIANCE]`, `operateur@orcia.io`) et un mini-formulaire `karim@orcia.io` noyé dans la page.
2. **Données fictives pré-chargées** : L'écran `Mon Assistant` (`/assistant`), `Mes Espaces` (`/workspaces`), `Mes Agents` (`/agents`) et `Mes Processus` (`/processes`) embarquaient des constantes de démonstration (`PAY-142 · Exemption 3DS Frictionless TRA`, `SEPA`, `PSD2`, `ADR-019`, `check_tra_threshold.star`, `payments-agent/v1`).
3. **Fonctionnalités non configurées laissées actives** : Les entrées de navigation et actions nécessitant un modèle IA ou un Espace de travail étaient cliquables à vide au lieu d'être grisées (`disabled`).
4. **Doublon du sélecteur de langue dans la `TopHeaderBar`** : Un bouton `🌐 Langue (FR)` (`shell-locale-toggle`) figurait dans la barre supérieure alors que la bascule de langue est intégrée au menu de l'utilisateur à droite.
5. **Textes NFR et jargon d'architecture exposés dans l'UI** : Les dictionnaires `fr.ts`, `en.ts` et `epic5..11_labels.ts` affichaient des métriques NFR (`< 500ms`, `0 ms`, `< 30 ms`, `< 50 ms`, `< 2 ms`, `< 5 s`, `< 100 ms`, `< 1,2 s`), des tailles en pixels (`340px`, `420px`, `280px`, `720px × max 600px`) et des codes internes (`Couche 5`, `Mode A — 3 onglets`, `AD-*`, `UX-DR*`, `LOCK TABLE users`, `POST /api/v1/auth/logout → /login`).
6. **Pied de Sidebar gauche encombré** : Le bas du menu latéral gauche affichait 3 boutons hérités (`sidebarModuleShortcuts`) ainsi qu'un sélecteur `Pack Métier actif (orcia-pack-sdlc@1.0.0)` hors contexte.
7. **Terminologie « Casquette métier » et intitulé Administrateur** : L'administrateur de la plateforme n'est pas un « Tech Lead », et le sélecteur dans le menu utilisateur doit porter le terme **« Rôle »** (`Role` en anglais) avec des intitulés humains lisibles.

### 1.2 Exploration, Analyse d'Impact GitNexus, Factorisation & Dette Technique
- **Analyse d'Impact GitNexus (`gitnexus_query`, `gitnexus_impact` sur `repo: "ORCIA"`)** :
  - `FourZoneDirectionCShell` (`packages/ui/src/primitives/FourZoneDirectionCShell.tsx`) : `risk: CRITICAL` (utilisé par `ShellContainer.tsx` et `epic9-shell-and-cockpit.test.tsx`).
  - `UserAccountDropdownAndSettingsModal` (`packages/ui/src/primitives/UserAccountDropdownAndSettingsModal.tsx`) : `risk: CRITICAL` (`621` lignes $\rightarrow$ dépasse le seuil de `300–400` lignes de la politique Tech Lead).
  - `ShellContainer` (`apps/web/src/components/ShellContainer.tsx`) : point d'entrée du layout racine `__root.tsx`.
- **Opportunités de Factorisation & Résorption de Dette Technique Naissante** :
  - **Découpage de `UserAccountDropdownAndSettingsModal.tsx` (`621` lignes)** : extraction des 4 panneaux d'onglets de la modale dans `packages/ui/src/primitives/UserSettingsModalTabs.tsx` afin de ramener chaque fichier sous les `320` lignes.
  - **Optionnalité de `mechanism` dans `DnaStarlarkCompilerAndGlossaryLifecycleView`** : supporter `mechanism?: UiCompiledStarlarkMechanism | null` pour afficher un état vide propre lorsque `0` règle Starlark n'est configurée.

---

## 2. Plan d'Implémentation

### 2.1 Schéma de Données & Migrations Alembic
- Sans objet (évolution purement Frontend SPA `@orcia/ui` + `apps/web` et spécifications UX `EXPERIENCE.md`).

### 2.2 Noyau Métier Hexagonal & Workers
- Sans objet.

### 2.3 Couche Backend API, Sécurité & Contrats
- Sans objet (`0-diff` OpenAPI préservé).

### 2.4 Interface Utilisateur & Expérience (`packages/ui/` & `apps/web/`)
1. **`packages/ui/src/primitives/FourZoneDirectionCShell.tsx`** :
   - Ajout de `disabledMenuKeys?: Partial<Record<EightFixedMenuKey, string>>` pour griser (`disabled`, `aria-disabled="true"`, opacité réduite, icône `🔒` et `title` explicatif) les entrées de menu non accessibles faute de configuration.
   - Masquage par défaut du sélecteur `Pack Métier actif` en bas de la Sidebar (affiché uniquement si `showPackSelector={true}` est explicitement passé).
2. **`packages/ui/src/primitives/UserAccountDropdownAndSettingsModal.tsx` & `UserSettingsModalTabs.tsx`** :
   - Découpage modulaire (`< 320` lignes par fichier).
   - Remplacement de « Casquette métier » par **« Rôle »** (`Role` en anglais) avec des options lisibles (`Administrateur de la plateforme`, `Product Manager / Métier`, `Architecte`, `Tech Lead / Développeur`, `Sécurité & Conformité`) et affichage du libellé humain dans le bouton du Header.
   - Suppression du texte technique `POST /api/v1/auth/logout → /login` et des mentions NFR (`< 5 s`, `< 10 ms Redis`).
3. **`packages/ui/src/primitives/DnaStarlarkCompilerAndGlossaryLifecycleView.tsx` & `AssistantFoldersAndCollaborativeThreadView.tsx`** :
   - Support de l'état vide (`mechanism={null}`, `folders={[]}`) sans données fictives.
4. **`apps/web/src/components/platformSetupStore.tsx` & `ShellContainer.tsx`** :
   - Ajout de l'état `platformAdmin` et de la **Modale de 1er démarrage (`first-boot-admin-setup-modal`)** pour créer le compte **Administrateur de la plateforme** au premier lancement.
   - Retrait du bouton de langue `shell-locale-toggle` de la `TopHeaderBar`, retrait de `sidebarModuleShortcuts` et retrait du sélecteur de Pack de la Sidebar.
   - Calcul dynamique de `disabledMenuKeys` selon l'état de configuration (`llmTiers`, `workspaces`).
5. **`apps/web/src/features/{inbox,workspaces,catalog,gates,cockpit}/index.tsx` & `apps/web/src/i18n/locales/*.ts`** :
   - Purge de 100 % des données fictives (`PAY-142`, `SEPA`, `PSD2`, `ADR-019`, `check_tra_threshold.star`, `payments-agent/v1`).
   - Purge de tous les textes NFR (`< 500ms`, `0 ms`, `< 30 ms`, `< 50 ms`, `< 2 ms`, `< 5 s`, `< 100 ms`, `< 1,2 s`, `340px`, `420px`, `280px`, `720px`, `Couche 5`, `Mode A`, `AD-*`, `UX-DR*`, `LOCK TABLE users`).

---

## 3. Bilan des Modifications & Résultats (Post-Implémentation)

### 3.1 Tableau Récapitulatif des Fichiers Créés / Modifiés
| Fichier | Nature | Description Technique |
| :--- | :--- | :--- |
| `docs/planning-artifacts/epics.md` | Modifié | Ajout de la **Story 12.4** dans l'Epic 12 (7 critères d'acceptation couvrant les 7 retours UX). |
| `docs/planning-artifacts/ux-designs/ux-ORCIA-2026-10-24/EXPERIENCE.md` | Modifié | Documentation des invariants UX : modale de création du compte Administrateur au 1er démarrage, zéro donnée fictive, grisage des fonctionnalités non configurées, suppression du sélecteur de Pack de la Sidebar, renommage en « Rôle » et interdiction d'exposer les métriques NFR dans l'UI. |
| `packages/ui/src/primitives/FourZoneDirectionCShell.tsx` | Modifié | Support de `disabledMenuKeys?: Partial<Record<EightFixedMenuKey, string>>` (`disabled`, `aria-disabled="true"`, opacité `0.45`, icône `🔒` et infobulle `title`) et masquage conditionnel du sélecteur de Pack (`Boolean(onSelectPack) && availablePacks.length > 0`). |
| `packages/ui/src/primitives/UserSettingsModalTabs.tsx` | Créé (`269` l.) | Extraction des 4 onglets de la modale « Mes paramètres » (`Profil & Apparence`, `Préférences de notifications`, `Sécurité & Clés API`, `Préférences Assistant IA`) et de la table `ROLE_DISPLAY_LABELS_FR` pour respecter la limite de volumétrie (`< 400` lignes). |
| `packages/ui/src/primitives/UserAccountDropdownAndSettingsModal.tsx` | Modifié (`372` l.) | Découpage modulaire (`621` $\rightarrow$ `372` lignes), remplacement de « Casquette métier » par **« Rôle »** (`Role` en anglais) avec options lisibles (`Administrateur de la plateforme`, `Product Manager / Métier`, `Architecte`, `Tech Lead / Développeur`, `Sécurité & Conformité`), retrait de `POST /api/v1/auth/logout → /login` et purge des mentions NFR. |
| `packages/ui/src/primitives/DnaStarlarkCompilerAndGlossaryLifecycleView.tsx` | Modifié | Rendre `mechanism?: UiCompiledStarlarkMechanism | null` optionnel avec état vide `dna-starlark-empty-state` lorsque `0` règle Starlark n'est compilée. |
| `packages/ui/src/primitives/ProgressiveDay0AccostageBanner.tsx` | Modifié | Remplacement des valeurs initiales fictives (`"karim@orcia.io"`, `"Karim Admin"`) par des champs vides (`""`). |
| `packages/ui/src/__tests__/epic9-shell-and-cockpit.test.tsx` | Modifié | Adaptation des assertions à la terminologie « Rôle » et aux libellés épurés de tout jargon NFR. |
| `apps/web/src/components/platformSetupStore.tsx` | Modifié | Ajout de `PlatformAdminAccount`, de l'état `platformAdmin: null` au 1er démarrage et de l'action `createPlatformAdmin`. |
| `apps/web/src/components/ShellContainer.tsx` | Modifié | Ajout de la modale de 1er démarrage (`data-testid="first-boot-admin-setup-modal"`), suppression du bouton `shell-locale-toggle` de la `TopHeaderBar`, suppression de `sidebarModuleShortcuts` et du sélecteur de Pack en bas de la Sidebar, et calcul dynamique de `disabledMenuKeys`. |
| `apps/web/src/components/shellPresets.ts` | Modifié | Purge de `DEFAULT_SEARCH_HITS` (`[]`), du profil fictif `operateur@orcia.io` (`Administrateur de la plateforme`) et des références `PAY-142` / `UX-DR*` / NFR dans l'aide contextuelle. |
| `apps/web/src/features/{inbox,workspaces,catalog,gates,ontology}/index.tsx` | Modifié | Purge intégrale des constantes fictives (`PAY-142`, `SEPA`, `PSD2`, `ADR-019`, `check_tra_threshold.star`, `payments-agent/v1`), grisage des actions tant que les prérequis ne sont pas configurés, et états vides propres. |
| `apps/web/src/i18n/locales/{fr,en,epic5_labels,epic9_labels,epic10_labels,epic11_labels}.ts` | Modifié | Purge intégrale des métriques NFR (`< 500ms`, `0 ms`, `< 30 ms`, `Pause 450 ms`, `< 50 ms`, `< 2 ms`, `< 5 s`, `< 100 ms`, `< 1,2 s`, `< 10 ms`, `< 1 s`, `< 15 s`), des dimensions pixels (`340px`, `420px`, `280px`, `720px`) et des codes internes (`Couche 4/5`, `Mode A`, `AD-*`, `UX-DR*`, `LOCK TABLE users`), avec parité récursive `fr`/`en` à 100 %. |
| `apps/web/src/__tests__/i18n-and-shell.test.tsx` | Modifié | Ajout des tests couvrant la modale Administrateur au 1er démarrage, le grisage dynamique des entrées de menu, l'absence du bouton de langue dans la `TopHeaderBar`, l'absence du sélecteur de Pack dans la Sidebar, le sélecteur « Rôle » et la non-régression zéro donnée fictive / zéro NFR. |

### 3.2 Validation & Métriques de Qualité
- **Tests & Qualité TypeScript (`pnpm turbo run lint typecheck test`)** : **9/9 tâches réussies**
  - `@orcia/ui` : `43/43` tests passés (`5` fichiers de test).
  - `@orcia/api-client` : `7/7` tests passés.
  - `@orcia/web` : `13/13` tests passés (incluant la vérification récursive 100 % `fr`/`en` et le parcours complet Jour 0 $\rightarrow$ Modale Administrateur $\rightarrow$ Déverrouillage progressif).
- **Conformité Architecture Spine (`lint_spine.py`)** : `PASSED (0 findings)`.
- **Analyse de Graphe GitNexus (`npx gitnexus analyze` + `detect_changes`)** : `changed_files: 22`, `changed_count: 116`, `affected_count: 12`, index à jour (`15 016` nœuds, `24 851` arêtes).
