# Rapport d'Analyse & d'Implémentation Tech Lead — Story 12.1 : Bascule de `apps/web` sur le Shell 4 Zones Direction C (`FourZoneDirectionCShell`), Navigation 8 Entrées Fixes, Unification CSS (`tokens.css`) & Cockpit Épuré (Epic 9)

> **Statut** : `DONE`
> **Date** : `2026-10-31`
> **Auteur** : Tech Lead / Senior Dev Agent (avec **Sally** UX Designer & **Winston** System Architect)
> **Références** : [`epics.md` (Story 12.1)](../../planning-artifacts/epics.md#L1374-L1393) · [`ARCHITECTURE-SPINE.md`](../../planning-artifacts/architecture/architecture-ORCIA-2026-10-24/ARCHITECTURE-SPINE.md) · [`DESIGN.md`](../../planning-artifacts/ux-designs/ux-ORCIA-2026-10-24/DESIGN.md) · [`EXPERIENCE.md`](../../planning-artifacts/ux-designs/ux-ORCIA-2026-10-24/EXPERIENCE.md)

---

## 1. Analyse du Besoin & Étude d'Impact Tech Lead (Avant Codage)

### 1.1 Contexte Fonctionnel & Problématique
Lors du démarrage de `apps/web`, l'utilisateur voyait encore l'ancien Shell à 3 zones (`<AppShell />`) avec son dock droit figé (*« Agent Assistant & Permission Broker »*), la barre basse mobile (`Inbox | Arbitrage/Chat | Briefing`) et les anciens blocs empilés dans le Cockpit, ainsi que des boutons non stylés car les alias CSS et classes utilitaires des primitives des Epics 9–11 n'étaient pas déclarés dans `packages/ui/src/styles/tokens.css`.

La **Story 12.1** réalise la bascule du Composition Root Frontend (`apps/web`) vers le **Shell 4 Zones Direction C (`FourZoneDirectionCShell`)** :
1. **Unification CSS (`packages/ui/src/styles/tokens.css`)** : définition de tous les alias de jetons sémantiques Direction C (`--color-bg-canvas`, `--color-bg-surface`, `--color-bg-elevated`, `--color-surface-elevated`, `--color-surface-base`, `--color-surface-muted`, `--color-border-subtle`, `--color-text-primary`, `--color-text-secondary`, `--color-action-primary`, `--color-action-primary-subtle`, `--color-accent-primary`, `--color-state-verified`, `--color-state-warning`, `--color-state-danger`, `--color-status-success`, `--color-status-warning`, `--color-status-danger`) et des classes utilitaires de mise en page pour un rendu impeccable sans aucun hexadécimal hors de `tokens.css`.
2. **Bascule de `ShellContainer.tsx` sur `FourZoneDirectionCShell`** :
   - Suppression du montage de l'ancien `<AppShell />` (disparition du dock droit figé et de la barre du bas) ;
   - Montage de `FourZoneDirectionCShell` avec la barre `52px` (`TopHeaderSearchCommand` `⌘K` en modale + `UserAccountDropdownAndSettingsModal` pour le menu Compte/Paramètres), les **8 entrées fixes** dans le rail gauche (`Cockpit`, `Mon Assistant`, `Mes Processus`, `Mes Agents`, `Mes Espaces`, `FinOps`, `Configuration`, `Aide`) + les liens de navigation du périmètre, et la colonne d'aide contextuelle `❓` (`340px`) peuplée par `ContextualHelpColumnAndCenter`.
3. **Routes des 8 entrées dans `apps/web/src/router.tsx` & Cockpit épuré (`apps/web/src/features/cockpit/index.tsx`)** :
   - Ajout du support des chemins des 8 entrées (`/assistant`, `/processes`, `/agents`, `/spaces`, `/configuration`, `/help`) dans `router.tsx` et `shellPresets.ts` ;
   - Épuration de `CockpitFeaturePanel` pour mettre en avant `StreamlinedCockpitView` et `ProgressiveDay0AccostageBanner`.

### 1.2 Analyse d'Impact GitNexus
- **`gitnexus_impact({target: "ShellContainer", direction: "upstream", repo: "ORCIA"})`** : appelé par `apps/web/src/routes/__root.tsx` et `apps/web/src/__tests__/i18n-and-shell.test.tsx`.
- **`gitnexus_impact({target: "CockpitFeaturePanel", direction: "upstream", repo: "ORCIA"})`** : appelé par `apps/web/src/components/ModuleWorkspaceView.tsx`.

---

## 2. Plan d'Implémentation

### 2.1 Design System (`packages/ui`)
- Enrichissement de [`packages/ui/src/styles/tokens.css`](../../../../packages/ui/src/styles/tokens.css) avec les variables sémantiques Direction C et les classes utilitaires de layout/typographie/boutons.
- Enrichissement optionnel de [`FourZoneDirectionCShell.tsx`](../../../../packages/ui/src/primitives/FourZoneDirectionCShell.tsx) avec un slot `helpColumnContent?: React.ReactNode` et `headerRightSlot?: React.ReactNode` pour injecter `ContextualHelpColumnAndCenter` et `UserAccountDropdownAndSettingsModal`.

### 2.2 Portail SPA (`apps/web`)
- Mise à jour de [`ShellContainer.tsx`](../../../../apps/web/src/components/ShellContainer.tsx), [`shellPresets.ts`](../../../../apps/web/src/components/shellPresets.ts), [`router.tsx`](../../../../apps/web/src/router.tsx) et [`features/cockpit/index.tsx`](../../../../apps/web/src/features/cockpit/index.tsx).

---

## 3. Bilan des Modifications & Résultats

| Fichier | Action | Rôle |
| :--- | :--- | :--- |
| `packages/ui/src/styles/tokens.css` | Modifié | Alias sémantiques Direction C & classes utilitaires de mise en page |
| `packages/ui/src/primitives/FourZoneDirectionCShell.tsx` | Modifié | Support des slots `helpColumnContent` et `headerUserControl` |
| `apps/web/src/components/ShellContainer.tsx` | Modifié | Montage de `FourZoneDirectionCShell`, `TopHeaderSearchCommand`, `UserAccountDropdownAndSettingsModal` et `ContextualHelpColumnAndCenter` |
| `apps/web/src/components/shellPresets.ts` | Modifié | Résolution des 8 routes du menu Direction C |
| `apps/web/src/router.tsx` | Modifié | Enregistrement des routes `/assistant`, `/processes`, `/agents`, `/spaces`, `/configuration`, `/help` |
| `apps/web/src/features/cockpit/index.tsx` | Modifié | Intégration de `ProgressiveDay0AccostageBanner` + `StreamlinedCockpitView` |
