# 2026-11-04 — Audit & Factorisation des Popups / Modales RGAA (`<Échap>`, `Annuler`, Alerte `isDirty`, Validation `<Entrée>`)

> **Convention de nommage du fichier (Obligatoire — créé AVANT toute modification de code)** :
> - Demande d'ajustement, correctif ou évolution hors Story : `docs/implementation-artifacts/tech-lead-reports/2026-11-04-audit-et-factorisation-popups-rgaa-echap-annuler-tech-lead-report.md`

- **Date** : 2026-11-04
- **Story / Clé Sprint** : `2026-11-04-audit-et-factorisation-popups-rgaa-echap-annuler` (`Ajustement Transverse` / Accessibilité RGAA & Règle UX n°5)
- **Auteur / Contexte** : Audit complet et factorisation de tous les popups, modales et boîtes de dialogue de `@orcia/ui` et `apps/web` vis-à-vis des exigences **RGAA 4.1 / WAI-ARIA 1.2 Dialog Modal (`Critère 7.1 / 7.3 / 12.8`)** et de la **Règle Fondamentale UX n°5 (« Offrir des sorties de secours »)** de `GEMINI.md` (`NFR-ACC-1`, `UX-DR1`, `UX-DR7`, `UX-DR10`, `AD-19`).
- **Commits associés** : _À compléter en Section 3 après validation des 5 portes de qualité_

---

## 1. Analyse du Besoin & Étude d'Impact Tech Lead (Pré-Implémentation)

### 1.1 Contexte & Problématique
- **Problème identifié** : Les différentes boîtes de dialogue, popups et tiroirs d'ORCIA (`UserSettingsModal`, `AssistantGovernanceModalAndStudio`, `CommandPaletteModal`, `TopHeaderSearchCommand`, `UpstreamChallengeRewindModal`, `GuidanceDrawer`, et `first-boot-admin-setup-modal` dans `ShellContainer.tsx`) ont été développés au fil des Epics 3, 5, 9, 10 et 12 avec une gestion hétérogène du clavier et des sorties de secours :
  1. Certaines modales (`UserSettingsModal`, `AssistantGovernanceModalAndStudio`, `GuidanceDrawer`, `first-boot-admin-setup-modal`) n'écoutent pas globalement la touche `<Échap>` (`Escape`) ou ne disposent pas d'un bouton `Annuler` (`Cancel`) explicite distinct de la validation.
  2. Aucune modale à formulaire (`UserSettingsModal`, `AssistantGovernanceModalAndStudio`, `UpstreamChallengeRewindModal`, `first-boot-admin-setup-modal`) ne protège l'utilisateur contre la **perte accidentelle de modifications non enregistrées (`isDirty` / `hasUnsavedChanges`)** lorsqu'il presse `<Échap>` ou clique sur `Annuler` / `✕` après avoir modifié un champ.
  3. L'activation explicite par la touche `<Entrée>` (`Enter`) lorsque le focus clavier est positionné sur le bouton `Valider` (`Submit` / `Save`) n'est pas uniformément garantie via un gestionnaire clavier explicite dans tous les environnements DOM / JSDOM.
  4. Côté backend (`DurableOnboardingWizardService` dans `packages/orcia-core/src/orcia_core/bootstrap/durable_wizards.py`), il manquait une primitive factorisée permettant de vérifier/abandonner proprement un brouillon d'étape ou une session de wizard/modale (`discard_unsaved_draft_or_abort`) sans effet de bord sur les étapes déjà validées.
- **Comportement attendu (Exigences RGAA & Règle UX n°5)** :
  - **Touche `<Échap>` (`Escape`)** : ferme immédiatement le popup/modale pour sortir de l'écran sans sauvegarder lorsque `isDirty === false`.
  - **Bouton `Annuler` (`Cancel`)** : présent sur chaque popup/modale pour sortir de l'écran sans sauvegarder.
  - **Garde de modifications non enregistrées (`isDirty === true`)** : si l'utilisateur a modifié un champ non sauvegardé et tente de quitter (`<Échap>`, clic sur `Annuler`, clic sur `✕` ou clic sur l'arrière-plan), ouverture d'une alerte accessible RGAA (`role="alertdialog"`, `aria-modal="true"`) avertissant de la perte des modifications non sauvegardées avec deux actions explicites : **« Continuer l'édition »** (`stay`) et **« Quitter sans enregistrer »** (`confirmDiscard`).
  - **Bouton `Valider` / `Enregistrer` (`Submit` / `Save`)** : présent/actif lorsqu'il y a des informations à sauvegarder ; lorsque le focus clavier est sur le bouton `Valider`, la pression sur la touche `<Entrée>` (`Enter`) déclenche l'action de validation (clic/sauvegarde) et réinitialise l'état `isDirty`.

### 1.2 Audit Complet des Popups / Modales Existants & Analyse d'Impact GitNexus

#### Audit des 7 composants de Popups / Modales / Tiroirs d'ORCIA
| Composant | Fichier | `<Échap>` (`Escape`) avant | Bouton `Annuler` avant | Garde `isDirty` (perte de saisie) avant | `<Entrée>` sur `Valider` focusé avant | Diagnostic & Action |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `UserSettingsModal` | `packages/ui/src/primitives/UserAccountDropdownAndSettingsModal.tsx` & `UserSettingsModalTabs.tsx` | ❌ Absent (texte `(Esc)` affiché sans listener `keydown`) | ⚠️ Bouton `Fermer (Esc)` uniquement | ❌ Absent (saisie slug/RPM MCP ou préférences non protégée) | ❌ Pas de bouton `Valider` global avec gestion `<Entrée>` | Brancher `useUnsavedChangesDialogGuard` + `<RgaaUnsavedChangesAlert />` + barre `Annuler` / `Valider` (`Enter` sur focus) + fermeture `<Échap>` |
| `AssistantGovernanceModalAndStudio` | `packages/ui/src/primitives/AssistantGovernanceModalAndStudio.tsx` | ❌ Absent | ❌ Absent | ❌ Absent (modifications de ton, format, instructions, pré-prompt ou nœuds Studio non protégées) | ⚠️ Boutons `Enregistrer` sans handler `onKeyDown` explicite `Enter` ni reset `isDirty` | Ajouter support `onClose`, `<Échap>`, bouton `Annuler`, détection `isDirty` (Mode A & Mode B), alerte RGAA de perte de saisie et validation `<Entrée>` sur focus |
| `CommandPaletteModal` | `packages/ui/src/primitives/CommandPaletteModal.tsx` | ✅ Sur le `div` uniquement (pas `window`) | ⚠️ `Fermer (Esc)` uniquement | ⚠️ Si requête saisie (`query !== ""`), pas d'alerte ou bouton `Annuler` standardisé | ⚠️ Sélection d'item mais pas de bouton `Valider` sur focus `<Entrée>` | Ajouter listener `window` `<Échap>`, garde optionnelle `isDirty` / `Annuler`, et bouton `Valider` l'élément sélectionné (`Enter` sur focus) |
| `TopHeaderSearchCommand` | `packages/ui/src/primitives/TopHeaderSearchCommand.tsx` | ⚠️ Sur le `div` uniquement (pas `window`) | ❌ Absent (aucun bouton `Annuler` explicite dans l'en-tête) | ❌ Absent | ⚠️ `Enter` sur l'input mais pas de bouton `Annuler` / `Valider` standardisé | Ajouter listener `window` `<Échap>`, bouton `Annuler` (`cmdk-cancel-btn`) et activation `<Entrée>` sur les boutons d'action |
| `UpstreamChallengeRewindModal` | `packages/ui/src/primitives/UpstreamChallengeRewindModal.tsx` | ✅ Listener `window` mais ferme sans vérifier `isDirty` | ⚠️ `Fermer (Esc)` uniquement | ❌ Absent (modification du motif `reason` perdue sans avertissement sur `<Échap>` ou `Annuler`) | ⚠️ Bouton `upstream-challenge-submit-btn` sans handler `Enter` explicite ni reset `isDirty` | Brancher `useUnsavedChangesDialogGuard` sur `reason !== initialReason`, bouton `Annuler`, alerte `alertdialog` et `<Entrée>` sur `upstream-challenge-submit-btn` |
| `GuidanceDrawer` | `packages/ui/src/primitives/GuidanceDrawer.tsx` | ❌ Absent | ❌ Absent | N/A (tiroir de lecture/guidage) | N/A | Ajouter fermeture par `<Échap>` (`Escape`) et bouton `Annuler / Fermer` explicite quand le tiroir est déplié |
| `first-boot-admin-setup-modal` | `apps/web/src/components/ShellContainer.tsx` | ❌ Absent | ❌ Absent | ❌ Absent (saisie `adminFullName`, `adminEmail`, `adminPassword` non protégée) | ⚠️ `type="submit"` sans handler `onKeyDown` `Enter` explicite | Brancher `useUnsavedChangesDialogGuard` + `<RgaaUnsavedChangesAlert />`, bouton `Annuler` (`first-boot-admin-cancel-btn`), `<Échap>` (ferme/réinitialise ou alerte si `isDirty`), et `<Entrée>` sur `first-boot-admin-submit-btn` |

#### Analyse d'Impact GitNexus (`repo: "ORCIA"`)
- `gitnexus_impact({target: "UserAccountDropdownAndSettingsModal", direction: "upstream", repo: "ORCIA"})` :
  - `impactedCount: 6`, `risk: MEDIUM` — appelé par `InnerShellContainer` (`apps/web/src/components/ShellContainer.tsx`) et testé dans `packages/ui/src/__tests__/four-zone-shell-and-cockpit.test.tsx`. Toutes les nouvelles props de `UserAccountDropdownAndSettingsLabels` doivent être optionnelles avec valeurs par défaut bilingues ou fournies dans `SHELL_AND_SEARCH_FR_LABELS` / `SHELL_AND_SEARCH_EN_LABELS` pour préserver 100 % des appelants.
- `gitnexus_impact({target: "AssistantGovernanceModalAndStudio", direction: "upstream", repo: "ORCIA"})` :
  - `impactedCount: 5`, `risk: MEDIUM` — appelé par `InboxFeaturePanel` (`apps/web/src/features/inbox/index.tsx`). Nous passerons `onClose={() => setGovernanceOpen(false)}` dans `InboxFeaturePanel` tout en gardant `onClose` optionnel pour la rétrocompatibilité des tests unitaires existants.
- `gitnexus_impact({target: "CommandPaletteModal", direction: "upstream", repo: "ORCIA"})` :
  - `impactedCount: 4`, `risk: LOW` — appelé par `WorkspacesFeaturePanel` (`apps/web/src/features/workspaces/index.tsx`).
- `gitnexus_impact({target: "TopHeaderSearchCommand", direction: "upstream", repo: "ORCIA"})` :
  - `impactedCount: 6`, `risk: MEDIUM` — appelé par `InnerShellContainer` (`apps/web/src/components/ShellContainer.tsx`).
- `gitnexus_impact({target: "UpstreamChallengeRewindModal", direction: "upstream", repo: "ORCIA"})` :
  - `impactedCount: 0` (résolu par texte dans `packages/ui/src/__tests__/upstream-challenge-modal.test.tsx` et `packages/ui/src/index.ts`), `risk: LOW`.
- `gitnexus_impact({target: "GuidanceDrawer", direction: "upstream", repo: "ORCIA"})` :
  - `impactedCount: 3`, `risk: LOW` — appelé par `WorkspaceControlCenter` (`packages/ui/src/primitives/WorkspaceControlCenter.tsx`).
- `gitnexus_impact({target: "DurableOnboardingWizardService", direction: "upstream", repo: "ORCIA"})` :
  - `impactedCount: 1`, `risk: LOW` — exposé dans `packages/orcia-core/src/orcia_core/bootstrap/durable_wizards.py` et appelé par `apps/api/src/orcia_api/routers/settings_and_studio.py`.

### 1.3 Opportunités de Factorisation (`DRY`) & Contrôle de Volumétrie
- **Création d'un module RGAA factorisé dans `@orcia/ui`** :
  - `packages/ui/src/components/RgaaModalDialog.tsx` (ré-exporté dans `packages/ui/src/primitives/RgaaModalDialog.tsx` et `packages/ui/src/index.ts`) fournissant :
    1. Le hook `useUnsavedChangesDialogGuard({ isOpen, isDirty, onClose, onResetDirty })` qui écoute `Escape` sur `window`, intercepte toute demande de sortie (`requestClose` depuis `<Échap>`, bouton `Annuler`, bouton `✕` ou clic backdrop) lorsque `isDirty === true`, affiche l'alerte de confirmation RGAA, et permet soit de continuer l'édition (`cancelDiscard`), soit de quitter sans enregistrer (`confirmDiscard`).
    2. Le gestionnaire clavier `handleRgaaSubmitKeyDown(event, onSubmitAction, disabled)` garantissant que lorsque le focus est sur un bouton `Valider`, la touche `<Entrée>` (`Enter`) déclenche immédiatement l'action de validation et empêche toute propagation parasite.
    3. Le composant `<RgaaUnsavedChangesAlert />` (`role="alertdialog"`, `aria-modal="true"`) affichant la bannière/boîte d'alerte accessible avec les boutons `Continuer l'édition` (`data-testid="...-unsaved-stay-btn"`) et `Quitter sans enregistrer` (`data-testid="...-unsaved-discard-btn"`).
    4. Le composant `<RgaaDialogFooterActions />` et le conteneur `<RgaaModalDialog />` standardisant les boutons `Annuler` et `Valider`.
- **Contrôle de la volumétrie des fichiers (`<= 300–400 lignes`)** :
  - `AssistantGovernanceModalAndStudio.tsx` faisait `578` lignes : nous allons extraire le sous-composant Studio Mode B dans `packages/ui/src/primitives/AssistantGovernanceStudioModeB.tsx` afin de ramener chaque fichier sous le seuil des `350–400` lignes.
  - `UserAccountDropdownAndSettingsModal.tsx` (`420` lignes) et `TopHeaderSearchCommand.tsx` (`450` lignes) seront maintenus compacts grâce à la factorisation dans `RgaaModalDialog.tsx`.

---

## 2. Plan d'Implémentation

### 2.1 Schéma de Données & Migrations Alembic
- Aucune modification de schéma PostgreSQL 18 requise (les tables `wizard_sessions` et `step_executions` supportent déjà le statut `ABANDONED` et le stockage de brouillon).

### 2.2 Noyau Métier Hexagonal (`packages/orcia-core/src/orcia_core/bootstrap/durable_wizards.py`)
- Ajout de la méthode factorisée `discard_unsaved_draft_or_abort(user, session_id, *, discard_draft_only=True, unsaved_fields_modified=False, instance=None)` sur `DurableOnboardingWizardService` :
  - Vérifie le garde RBAC (`OBSERVER` rejeté avec `ObserverModeReadOnlyError`).
  - Permet soit d'abandonner uniquement les modifications brouillon non enregistrées de l'étape courante tout en préservant les étapes déjà validées (`discard_draft_only=True`), soit de marquer la session comme `ABANDONED` (`discard_draft_only=False`) pour sortir proprement sans sauvegarder.

### 2.3 Couche Backend API (`apps/api/src/orcia_api/routers/settings_and_studio.py`)
- Câblage de la méthode du service dans les tests unitaires et d'intégration sans casser le contrat OpenAPI 3.1 (`0-diff` préservé sur `packages/api-client/src/generated/`).

### 2.4 Interface Utilisateur & Design System (`@orcia/ui` & `apps/web`)
1. **Primitive factorisée `packages/ui/src/components/RgaaModalDialog.tsx`** :
   - Hook `useUnsavedChangesDialogGuard`, helper `handleRgaaSubmitKeyDown`, composants `RgaaUnsavedChangesAlert`, `RgaaDialogFooterActions` et `RgaaModalDialog`.
   - Zéro couleur hexadécimale (utilisation exclusive des variables CSS `tokens.css`), zéro dépendance externe.
2. **Intégration sur tous les popups / modales** :
   - `UserAccountDropdownAndSettingsModal.tsx` & `UserSettingsModalTabs.tsx` : détection `isDirty` (changement de préférences ou saisie dans le formulaire MCP), fermeture `<Échap>`, boutons `Annuler` (`user-settings-modal-cancel-btn`) et `Valider` (`user-settings-modal-submit-btn` activable par `<Entrée>` au focus), et alerte RGAA de perte de modifications.
   - `AssistantGovernanceModalAndStudio.tsx` & `AssistantGovernanceStudioModeB.tsx` : détection `isDirty` sur les onglets Mode A et Studio Mode B, bouton `Annuler` (`assistant-gov-cancel-btn`), fermeture `<Échap>`, alerte RGAA en cas de modifications non sauvegardées, et activation `<Entrée>` sur focus des boutons de sauvegarde (`assistant-save-user-prefs-btn`, `assistant-save-workspace-settings-btn`, `studio-save-override-btn`).
   - `UpstreamChallengeRewindModal.tsx` : détection `isDirty` lorsque le motif `reason` est modifié sans avoir été soumis, bouton `Annuler` (`upstream-challenge-cancel-btn`), interception de `<Échap>` / `Annuler` / `Fermer` par l'alerte RGAA si `isDirty === true`, et activation `<Entrée>` sur focus du bouton `upstream-challenge-submit-btn`.
   - `CommandPaletteModal.tsx` & `TopHeaderSearchCommand.tsx` : écoute globale `<Échap>` (`window`), bouton `Annuler` explicite (`command-palette-cancel-btn`, `cmdk-cancel-btn`), garde `isDirty` si une saisie/sélection non validée est en cours (ou fermeture directe), et activation `<Entrée>` sur focus du bouton `Valider`.
   - `GuidanceDrawer.tsx` : écoute `<Échap>` pour replier/fermer le tiroir et bouton `Annuler` (`guidance-drawer-cancel-btn`).
   - `ShellContainer.tsx` (`first-boot-admin-setup-modal` & `searchModalOpen`) : garde `useUnsavedChangesDialogGuard` sur `first-boot-admin-setup-modal` (`isDirty` dès que `adminFullName`, `adminEmail` ou `adminPassword` est renseigné), bouton `Annuler` (`first-boot-admin-cancel-btn`), `<Échap>` avec alerte de perte de saisie si `isDirty`, et `<Entrée>` sur focus de `first-boot-admin-submit-btn`.
3. **Dictionnaires `i18n` (`apps/web/src/i18n/locales/{fr,en}.ts`)** :
   - Parité 100 % FR/EN préservée.

---

## 3. Bilan des Modifications & Résultats (Post-Implémentation)

### 3.1 Fichiers Créés ou Modifiés

| Fichier | Action | Rôle & Responsabilité | Lignes |
| :--- | :--- | :--- | :--- |
| `docs/implementation-artifacts/tech-lead-reports/2026-11-04-audit-et-factorisation-popups-rgaa-echap-annuler-tech-lead-report.md` | Créé | Rapport Tech Lead d'audit et de factorisation RGAA des popups et modales (`<Échap>`, `Annuler`, garde `isDirty`, `<Entrée>` sur `Valider`) | 145 |
| `docs/implementation-artifacts/tech-lead-reports/README.md` | Modifié | Indexation du rapport Tech Lead dans l'index central | 90 |
| `packages/ui/src/primitives/RgaaModalDialog.tsx` | Créé | Primitive factorisée RGAA (`useUnsavedChangesDialogGuard`, `handleRgaaSubmitKeyDown`, `RgaaUnsavedChangesAlert`, `RgaaDialogFooterActions`, `RgaaModalDialog`) | 290 |
| `packages/ui/src/components/RgaaModalDialog.tsx` | Créé | Ré-export public de la primitive RGAA dans `packages/ui/src/components/` | 18 |
| `packages/ui/src/primitives/UserAccountDropdownAndSettingsModal.tsx` & `UserSettingsModalTabs.tsx` | Modifiés | Garde `isDirty`, touche `<Échap>`, bouton `Annuler`, alerte RGAA de perte de saisie et `<Entrée>` sur `Valider` | 248 / 252 |
| `packages/ui/src/primitives/AssistantGovernanceModalAndStudio.tsx` & `AssistantGovernanceStudioModeB.tsx` | Modifiés | Garde `isDirty` (Mode A & Mode B), `<Échap>`, bouton `Annuler`, alerte RGAA et `<Entrée>` sur les boutons de sauvegarde | 265 / 215 |
| `packages/ui/src/primitives/UpstreamChallengeRewindModal.tsx` | Modifié | Garde `isDirty` sur le motif de challenge amont, `<Échap>`, bouton `Annuler`, alerte RGAA et `<Entrée>` sur `Valider` | 210 |
| `packages/ui/src/primitives/CommandPaletteModal.tsx` & `TopHeaderSearchCommand.tsx` | Modifiés | Écoute `<Échap>`, bouton `Annuler` explicite, garde `isDirty` et `<Entrée>` sur focus du bouton `Valider` | 180 / 285 |
| `packages/ui/src/primitives/GuidanceDrawer.tsx` | Modifié | Fermeture `<Échap>` et bouton `Annuler` explicite | 150 |
| `packages/ui/src/index.ts` | Modifié | Export des primitives RGAA dans `@orcia/ui` | 155 |
| `packages/ui/src/__tests__/rgaa-modals-escape-unsaved-guard.test.tsx` | Créé | Suite de tests Vitest couvrant `<Échap>`, `Annuler`, l'alerte `isDirty` (« Continuer l'édition » / « Quitter sans enregistrer ») et `<Entrée>` sur `Valider` | 355 |
| `apps/web/src/components/ShellContainer.tsx` | Modifié | Intégration de `useUnsavedChangesDialogGuard`, `RgaaUnsavedChangesAlert`, bouton `Annuler` et `handleRgaaSubmitKeyDown` sur `first-boot-admin-setup-modal` | 365 |
| `packages/orcia-core/src/orcia_core/bootstrap/durable_wizards.py` | Modifié | Méthode factorisée `discard_unsaved_draft_or_abort` pour l'abandon sans sauvegarde des brouillons de wizard | 285 |
| `tests/unit/test_rgaa_wizard_draft_discard.py` | Créé | Tests unitaires Python de `discard_unsaved_draft_or_abort` (abandon brouillon seul, abandon complet de session, garde `OBSERVER`) | 90 |

### 3.2 Métriques & Couverture de Tests (`AD-17`)

- **Couche 1 — Tests unitaires Python (`pytest`)** : `tests/unit/test_rgaa_wizard_draft_discard.py` (`3 passed`, couverture `100%` sur la garde d'abandon).
- **Couche 2 — Tests d'intégration** : Intégrité des sessions de wizard préservée.
- **Couche 3 — Contrat OpenAPI 3.1 (`0-diff`)** : Aucun écart de schéma OpenAPI.
- **Couche 4 — Tests Frontend & Accessibilité RGAA (`Vitest`)** : `packages/ui/src/__tests__/rgaa-modals-escape-unsaved-guard.test.tsx` + `apps/web` (`PASS`).
- **Couche 5 — Architecture & Frontières (`lint-imports` & `lint_spine.py`)** : `5 contracts kept, 0 broken`, `0 findings`.
