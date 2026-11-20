# Rapport Tech Lead — Story 24.4 : Refonte CSS Tailwind v4 Layering, Modales `OrciaDialog`, Contraste RGAA Sombre & Shell Direction C

- **Story :** `24-4-refonte-css-tailwind-tokens-modales-rgaa-contraste-onglets-et-shell` (Epic 24 — Vague 1 `P1–P3` UX / CSS)
- **Date :** 2026-11-20
- **Statut :** `En attente d'implémentation` (initialisé par `Story 23.8`)
- **Plan directeur :** [`sprint-change-proposal-2026-11-20-epic-24-remediation-plan.md`](../../planning-artifacts/sprint-change-proposal-2026-11-20-epic-24-remediation-plan.md)
- **Références remédiées :** `REM24-07`, **`USER24-BUG-1`**, **`USER24-BUG-4A`**, **`USER24-BUG-4B`**, **`USER24-BUG-5`** | Constats `UX23-02` (`P1`), `UX23-03` (`P1`), `UX23-04` (`P1`), `UX23-13` (`P2`), `UX23-14` (`P2`), `UX23-16` (double scroll) | Diagnostics `ARCH24-08`, `ARCH24-11`
- **Capacité(s) (`capabilities.yaml`) :** `none (hygiène/ux transverse Direction C — protège les capacités runtime et failed_e2e sur les vues CAP-060, CAP-063, CAP-090, CAP-200 avant la campagne 24.7)`
- **Classification :** `ux` (cascade CSS Tailwind v4, RGAA AA, modales & géométrie shell)

---

## 1. Analyse du Besoin & Étude d'Impact Tech Lead

### 1.1 Contexte & Critères d'Acceptation
L'audit visuel de Sally sur `58` captures (`notes-audit-sally-ux.md`) couplé à la fiche RCA Tailwind v4 de Winston (`notes-audit-winston-architecture.md` `ARCH24-08`) identifie une régression CSS majeure affectant la mise en page Direction C et le contraste :
1. **Ordre d'import inversé & collisions non-layerées (`UX23-02`, `UX23-04`, `UX23-13`, `UX23-14`, `ARCH24-08`)** : `apps/web/src/main.tsx:1-2` charge `virtual:orcia-tailwind.css` avant ou en conflit avec des classes utilitaires manuelles non encadrées (`@layer utilities` absent dans `packages/ui/src/styles/tokens.css`, `1 266` L), notamment `.flex-col` et `.grid-cols-1` qui écrasent `md:flex-row` et `sm:grid-cols-2 xl:grid-cols-4` (`FinopsKpiStrip`, cartes KPI `0`, formulaires d'authentification et en-tête `/finops` `Journal d'Activité →`).
2. **Modale Agent débordante (`UX23-03`)** : `AgentDetailAndSandboxModal.tsx` (`318` L) n'utilise pas la primitive `OrciaDialog`, manque de `max-h-[82vh]` + corps scrollable + pied de page sticky et tronque le `@slug`.
3. **Transition et contraste RGAA sombre (`UX23-04`, `UX23-13`, `ARCH24-11`)** : un fondu de `150ms` sur les onglets crée des clignotements en navigation clavier/E2E ; `FinopsScopePills` diverge dans sa gestion `[aria-selected="true"]` ; en thème sombre, `--color-sidebar-active-fg` échoue au ratio WCAG `>= 4.5:1`.
4. **Bande `#EAF2FB` & scroll vertical hors écran de travail (`UX23-14`, `UX23-16`, `USER24-BUG-1`)** : `FourZoneDirectionCShell.tsx` (`348` L) laisse apparaître une bande vide `#EAF2FB` et permet au scroll vertical de la fenêtre (`document.documentElement.scrollHeight > window.innerHeight`) de descendre plus bas que l'écran de travail ; le bandeau `Accostage` ne se compacte pas automatiquement lorsque des runs ou décisions existent déjà. Un test systématique doit être ajouté au patrimoine des tests (Vitest + Playwright) pour bloquer toute régression de scroll vertical externe Desktop.
5. **Modale `Personnalisation` en onglets horizontaux & menu Compte unifié (`USER24-BUG-4A`, `USER24-BUG-4B`, `UX23-02`)** :
   - La modale `UserSettingsModalDialog.tsx` affiche une liste verticale en haut à gauche avec un vide de ~220 px (`UX23-02`) et le panneau principal en dessous ; elle doit passer en mode **onglets horizontaux** `.orcia-ds-tabs` / `.orcia-ds-tab` (`aria-orientation="horizontal"`) comme dans « Mes Espaces » (`USER24-BUG-4A`, remplaçant l'arbitrage initial à 2 colonnes de `REM24-07`).
   - Dans le menu Compte en bas à gauche (`SidebarAccountPopover.tsx`), `Personnalisation` et `Paramètres` ouvrent la même modale : supprimer l'entrée doublon `Paramètres` (`account-popover-settings-btn`) pour ne conserver que `Personnalisation` (`USER24-BUG-4B`).
6. **`Clés IDE & MCP` — affichage unique réel & libellé clair (`USER24-BUG-5`)** :
   - Dans `useSidebarAccountSettings.ts`, `lastIssuedPlaintext` n'est jamais réinitialisé à `null` lors de la fermeture ou du changement d'onglet de la modale, si bien que la bannière « Copiez cette clé maintenant : elle ne sera plus jamais affichée » réapparaît à chaque réouverture.
   - Dans `UserSettingsMcpTokensTab.tsx` (`L40-42,L236-241`), le libellé `"IDE MCP (SPACE · default) · pat_mcp_... /api/v1/mcp/spaces/default · 60 RPM"` est confus ; il faut utiliser des libellés français lisibles sans repli `"default"` ni mention technique `60 RPM` collée au préfixe.

**Critères d'acceptation :** zéro écrasement des classes responsives Tailwind v4 (`md:flex-row`, `sm:grid-cols-2 xl:grid-cols-4`), `AgentDetailAndSandboxModal` portée sur `OrciaDialog`, ratio WCAG `>= 4.5:1` mesuré sur tous les tokens actifs dark/light, verrouillage strict `document.documentElement.scrollHeight <= window.innerHeight + 1` sur Desktop (`0` bande `#EAF2FB`, `0` scroll sous l'écran de travail, test systématique Vitest + Playwright), `UserSettingsModalDialog` en onglets horizontaux `.orcia-ds-tabs`, menu Compte sans doublon `Paramètres`, et bannière secret `Clés IDE & MCP` effacée dès fermeture de la modale avec libellés français clairs.

### 1.2 Analyse d'Impact GitNexus (`repo: "/home/romain/Documents/Projects/ORCIA"`)
- `packages/ui/src/primitives/FourZoneDirectionCShell.tsx` (`348` L), `packages/ui/src/components/AgentDetailAndSandboxModal.tsx` (`318` L), `packages/ui/src/primitives/UserSettingsModalDialog.tsx` (`295` L), `packages/ui/src/primitives/finops/FinopsKpiStrip.tsx` (`195` L), `FinopsGovernanceDashboardView.tsx` (`289` L), `apps/web/src/features/finops/index.tsx` (`399` L) et `apps/web/src/main.tsx` (`32` L) ont été inspectés directement avec vérification des frontières `@orcia/ui` (zéro import `@tanstack/react-router` ou `@orcia/api-client`).
- La feuille `packages/ui/src/styles/tokens.css` (`1 266` L) impacte l'ensemble des composants `@orcia/ui` et toutes les routes SPA `apps/web`.

### 1.3 Opportunités de Factorisation & Contrôle de Volumétrie (`< 350` L)
- **Découpage obligatoire `packages/ui/src/styles/tokens.css` (`1 266` L >> seuil `400` L)** : scinder en partials CSS importés proprement (`tokens-palette.css`, `tokens-dark.css`, `components-shell.css`, et suppression des classes utilitaires manuelles redondantes au profit de `@orcia/ui` Tailwind v4 ou `@layer utilities`) afin que chaque fichier reste `< 350` L.
- **Découpage / allègement `apps/web/src/features/finops/index.tsx` (`399` L)** et **harmonisation sur `OrciaDialog`** : réutiliser le composant `OrciaDialog` existant dans `@orcia/ui` au lieu d'entretenir un wrapper modal spécifique dans `AgentDetailAndSandboxModal`.

---

## 2. Plan d'Implémentation

### 2.1 Couche Données & Migrations Alembic / PostgreSQL 18
- Aucune migration PostgreSQL 18 requise dans cette Story (périmètre CSS, Design System `@orcia/ui` et coquille SPA ; intégrité des tables et migrations existantes vérifiée sans modification).

### 2.2 Noyau Hexagonal (`orcia-kernel` / `orcia-core`) & Workers
- Aucune modification du noyau Python (`packages/orcia-kernel`, `packages/orcia-core`) ; vérifier l'absence d'impact sur les contrats API et OpenAPI.

### 2.3 Backend FastAPI (`apps/api`) & Contrat OpenAPI (`packages/api-client`)
- Aucune modification d'endpoint API requise ; vérifier la cohérence des props typées attendues par `AgentDetailAndSandboxModal`, `FinopsGovernanceDashboardView` et `UserSettingsModalDialog` (`295` L).

### 2.4 Interface SPA Vite + TanStack Router & Design System (`@orcia/ui` / `apps/web`)
1. **`main.tsx` & `tokens.css` (`REM24-07` / `ARCH24-08`)** : charger `tokens.css` avant `virtual:orcia-tailwind.css` dans `apps/web/src/main.tsx:1-2` ; découper `packages/ui/src/styles/tokens.css` (`1 266` L $\rightarrow$ partials `< 350` L), supprimer les classes manuelles `.flex-col` / `.grid-cols-1` non layerées qui écrasent `md:flex-row` / `sm:grid-cols-2 xl:grid-cols-4`, et encapsuler tout utilitaire résiduel dans `@layer utilities`.
2. **Modale Agent (`UX23-03`)** : migrer `packages/ui/src/components/AgentDetailAndSandboxModal.tsx` (`318` L $\rightarrow$ `< 280` L) sur `OrciaDialog` avec `max-h-[82vh]`, contenu scrollable interne, footer sticky et affichage complet du `@slug`.
3. **Onglets & Contraste RGAA (`UX23-04`, `UX23-13`, `ARCH24-11`)** : retirer la transition `150ms` sur les changements d'onglets, unifier `[aria-selected="true"]` sur `FinopsScopePills` et les autres barres d'onglets, corriger `--color-sidebar-active-fg` en mode sombre pour atteindre `>= 4.5:1` (et contrôler tous les jetons d'état actif/hover sans couleur hex hors `tokens*.css`).
4. **Hauteur Shell, Verrouillage Scroll Desktop (`USER24-BUG-1`), Accostage & FinOps (`UX23-14`, `UX23-16`)** : verrouiller le viewport Desktop (`height: 100dvh; max-height: 100dvh; overflow: hidden;` sur `html, body, #root` et `FourZoneDirectionCShell` avec rangée centrale `flex-1 min-h-0 overflow-hidden` et colonnes internes `h-full min-h-0 overflow-y-auto`, supprimant `calc(100vh - 52px)` et `sticky top: 52px` sur Desktop) pour empêcher tout scroll vertical sous la coquille et éliminer la bande `#EAF2FB` ; compacter automatiquement `Accostage` lorsque des runs/décisions existent ; aligner `Journal d'Activité →` dans l'en-tête `/finops` (`apps/web/src/features/finops/index.tsx` allégé `< 320` L).
5. **Modale `UserSettingsModalDialog` en onglets horizontaux & Menu Compte (`USER24-BUG-4A`, `USER24-BUG-4B`, `UX23-02`)** :
   - Remplacer `<nav role="tablist" aria-orientation="vertical">` dans `UserSettingsModalDialog.tsx` par la barre horizontale `.orcia-ds-tabs` / `.orcia-ds-tab` (`aria-orientation="horizontal"`, `data-testid="user-settings-tabs"`, `data-testid="user-settings-tab-${tab.key}"`) suivie du panneau `<div role="tabpanel">` en dessous, comme dans « Mes Espaces » (`OrciaDialog` `max-w-3xl`).
   - Supprimer `account-popover-settings-btn` (`Paramètres`) de `SidebarAccountPopover.tsx` pour ne conserver que `account-popover-personalization-btn` (`Personnalisation`), et synchroniser `authAndOrgHelpers.ts`, `14-auth-*.spec.ts`, `story-20-3-*.test.tsx` et `e2e-testids-sync-audit.test.ts`.
6. **`Clés IDE & MCP` — reset secret & libellés lisibles (`USER24-BUG-5`)** :
   - Dans `apps/web/src/components/useSidebarAccountSettings.ts`, appeler `setLastIssuedPlaintext(null)` à la fermeture de la modale (`!modalOpen`) et lors du changement d'onglet hors `MCP_IDE_TOKENS`, et réinitialiser `copiedPlaintext` dans `UserSettingsMcpTokensTab.tsx`.
   - Dans `UserSettingsMcpTokensTab.tsx` et `_mcp_token_helpers.py`, remplacer `IDE MCP (SPACE · ${cleanSlug})` / `· 60 RPM` par des libellés français clairs (`Clé personnelle d'éditeur` ou `Clé d'accès éditeur — ${cleanSlug}`) en séparant visuellement titre, préfixe masqué et configuration JSON.

### 2.5 Stratégie de Vérification & 5 Couches de Tests (`AD-17`)
- **Couche 1 (Unitaire / Statique Python)** : conserver `pytest` vert (dont tests `_mcp_token_helpers.py`) et zéro hex hors `packages/ui/src/styles/`.
- **Couche 2 (Intégration PG18)** : smoke check de non-régression de la suite API existante.
- **Couche 3 (Composants React / Vitest + JSDOM/CSS)** :
  - Nouveau test systématique `apps/web/src/__tests__/shell-desktop-viewport-scroll-lock-audit.test.tsx` garantissant les règles CSS/DOM anti-scroll vertical du shell Desktop (`USER24-BUG-1`).
  - Tests `UserSettingsModalDialog` (`aria-orientation="horizontal"`, `.orcia-ds-tabs`, `USER24-BUG-4A`), `SidebarAccountPopover` (absence `account-popover-settings-btn`, `USER24-BUG-4B`), `useSidebarAccountSettings` / `UserSettingsMcpTokensTab` (`lastIssuedPlaintext` effacé à la fermeture/réouverture, zéro `IDE MCP (SPACE · default)` / `60 RPM`, `USER24-BUG-5`).
  - Tests de non-collision responsive (`FinopsKpiStrip`), contrat `OrciaDialog` dans `AgentDetailAndSandboxModal`, `[aria-selected="true"]` sur `FinopsScopePills`, ratio contraste `>= 4.5:1` sur `--color-sidebar-active-fg` dark/light, et audits `zero-dead-buttons-and-silent-catches-audit.test.tsx` / `e2e-testids-sync-audit.test.ts`.
- **Couche 4 (E2E Playwright ciblé)** :
  - Ajout de `assertNoDesktopVerticalPageOverflow` dans `apps/web/e2e/support/layoutGeometryAssertions.ts` appelé systématiquement dans `apps/web/e2e/shell.spec.ts` (vérifiant `scrollHeight <= innerHeight + 1`, `window.scrollTo(0, 99999)` $\rightarrow$ `scrollY === 0` et alignement `bottom === innerHeight`).
  - Vérification géométrique `1440×900` sur `shell.spec.ts`, `01`, `08`, `12`, `13`, `14` (onglets horizontaux, absence `account-popover-settings-btn`, disparition de `mcp-issued-plaintext-banner` à la réouverture), `16`.
- **Couche 5 (Statique & Build)** : `pnpm turbo run lint typecheck test`, `pnpm build` Vite (vérification de l'ordre des couches CSS dans le bundle produit), `pnpm site:check`.

---

## 3. Bilan des Modifications & Résultats

> **Statut :** `En attente d'implémentation` — Cette section sera complétée après implémentation, passage des 5 couches `AD-17`, ré-indexation GitNexus (`npx gitnexus analyze` + `gitnexus_detect_changes()`) et exécution de `pnpm site:sync`.

| Fichier / Composant | Action Prévue | Statut |
|---|---|---|
| `apps/web/src/main.tsx` | Ordre import `tokens.css` avant `virtual:orcia-tailwind.css` | `En attente d'implémentation` |
| `packages/ui/src/styles/tokens*.css` | Split `< 350` L, `@layer utilities`, contraste dark `--color-sidebar-active-fg` | `En attente d'implémentation` |
| `packages/ui/src/components/AgentDetailAndSandboxModal.tsx` | Migration sur `OrciaDialog` (`max-h-[82vh]`, slug complet) | `En attente d'implémentation` |
| `packages/ui/src/primitives/FourZoneDirectionCShell.tsx` | Suppression bande `#EAF2FB` & double scroll `< 900px` | `En attente d'implémentation` |
| `packages/ui/src/primitives/finops/*` & `apps/web/src/features/finops/index.tsx` | Onglets sans fade `150ms`, `[aria-selected="true"]`, alignement en-tête | `En attente d'implémentation` |
