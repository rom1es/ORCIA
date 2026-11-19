# Story 23.5 — Sobriété Cockpit (`<= 3` Blocs), `TopHeaderBar` Sans Doublon/Troncature, Épuration `/assistant` & `/login` et Captures `#10`

- **Date** : 2026-11-19
- **Story / Clé Sprint** : `23-5-sobriete-cockpit-topbar-sans-doublon-assistant-et-login` (`Epic 23` — Vague 1 `P1`–`P3`)
- **Capacité(s)** : `CAP-001`, `CAP-023`, `CAP-041`, `CAP-062`, `CAP-070`, `CAP-072`, `CAP-073`, `CAP-190` — classification : `feature` + `ux` (`REM23-09`, `REM23-10`, `REM23-11`, `REM23-12` / `ARCH23-06`..`ARCH23-09`, `P1-UX-3`, `P2-UX-8`..`P2-UX-11`, `P3-UX-12`)
- **Auteur / Contexte** : `22.10-impl` (Sally × Winston — pré-implémentation Epic 23). Aligne la hiérarchie visuelle Direction C : ramène `/cockpit` à `<= 3` blocs visuels, supprime le sélecteur d'espace dupliqué dans `TopHeaderBar` (cause des troncatures à `1440px`), place le logo `ORCIA` en Zone 1 (`DESIGN.md` §2.1), épure `/assistant` et `/login`, et garantit les captures de preuve sur `HumanLedAnchorCard` (`#6D28D9`) et `ArbitrationTieBreakCard` (`#D97706`).
- **Commits associés** : `En attente d'implémentation (initialisé par Story 22.10)`

---

## 1. Analyse du Besoin & Étude d'Impact Tech Lead (Pré-Implémentation)

### 1.1 Contexte & Problématique
- **Preuves E2E & Constats visuels (`notes-audit-sally-ux.md`, `notes-audit-winston-architecture.md`)** :
  1. **Surcharge du Cockpit (`REM23-09` / `P1-UX-3`, `ARCH23-06`)** :
     - Sur [`#5` (`01-day0-boot`)](../e2e-campaign-epic-22/screenshots/01-day0-boot-and-f5-persistence/desktop-cockpit--le-premier-administrateur-cree-survit-a-un-f5-sans-localstorage-rehydratation-postgresql--passed.png) et [`#10` (`03-human-led`)](../e2e-campaign-epic-22/screenshots/03-human-led-anchor-and-arbitration/desktop-cockpit--signature-de-l-ancrage-violet-30-car-rejet-agent-422-arbitrage-motive-et-survie-au-f5--passed.png), `/cockpit` empile `6` à `7` cartes (`1303px`–`1362px` de hauteur > `900px`) entre `cockpit/index.tsx#L186-L293`, `StreamlinedCockpitView.tsx#L150-L258`, `CockpitRunsSection.tsx#L41-L235` et `CockpitHumanLedGovernanceSection.tsx#L233-L383` (monté à vide sous la ligne de flottaison, formulaire anonyme de lancement rapide tout en bas en `#10`, redondance vers `Mon Assistant`).
  2. **Doublon `TopHeaderBar`, troncatures `1440px`, logo Zone 1, Loader & `/login` (`REM23-10` / `P2-UX-9`, `P2-UX-10`, `ARCH23-07`)** :
     - Dans [`FourZoneTopHeaderSection.tsx#L85-L153`](../../../packages/ui/src/primitives/FourZoneTopHeaderSection.tsx#L85-L153), le bouton `topbar-fixed-workspace-selector` (`max-w-[240px]`, `L128-L153`) duplique le Double Sélecteur de `Zone 1` (`FourZoneSidebarRail.tsx#L112-L173`), provoquant les troncatures `Espace : Plateforme Globale O...` et `Rechercher dans cet Espace ou partout (... ⌘K` sur `#5`, `#8`, `#9`, `#10`.
     - Le logo `ORCIA` réside en Zone 2 (`L85`) au lieu de la tête de Zone 1 (`DESIGN.md` §2.1) ; `buildShellBreadcrumbItems` (`shellPresets.ts#L178-L200`) omet l'unité `Équipe / Direction` ; l'écran de chargement [`#1`](../e2e-campaign-epic-22/screenshots/00-stack-smoke/desktop-cockpit--l-api-fastapi-repond-via-le-proxy-vite-navigateur-vite-fastapi--passed.png) (`ShellHydratingLoaderView`, `ShellContainer.tsx#L180-L182`) n'affiche qu'un texte nu ; et la mire `/login` ([`#11` cascade](../e2e-campaign-epic-22/screenshots/04-multi-actor-claim-sse/desktop-cockpit--a-prend-en-charge-une-tache-b-est-refuse-409-et-un-nouveau-flux-sse-rejoue-l-evenement-5--failed.png)) manque de logo ORCIA et d'un bouton œil afficher/masquer le mot de passe.
  3. **Épuration `/assistant` & jargon (`REM23-11` / `P2-UX-8`, `P2-UX-11`, `ARCH23-08`)** :
     - Sur [`#8`](../e2e-campaign-epic-22/screenshots/02-assistant-streaming-and-folders/desktop-cockpit--un-dossier-cree-dans-un-espace-est-rehydrate-depuis-l-api-apres-un-vrai-f5-cache-navigat--passed.png) et [`#9`](../e2e-campaign-epic-22/screenshots/02-assistant-streaming-and-folders/desktop-cockpit--un-dossier-survit-au-redemarrage-de-l-api-persistance-postgresql--passed.png), `ModuleWorkspaceView.tsx#L60-L101` exclut déjà `cockpit`, `catalog` et `finops` de sa carte d'en-tête mais **pas** `inbox` (`/assistant`) ; `SavedConversationsAndThreadView.tsx#L44-L100` affiche des compteurs `(0)` et mélange `orcia-ds-btn` et classes Tailwind brutes ; `fr.ts` expose `embedding` (*Modèle d'embedding sémantique requis*) et `Assistant ORCIA (Processus standard)` ; et le contraste du bouton d'envoi `➤` est faible.
  4. **Preuves visuelles `03-human-led-anchor-and-arbitration.spec.ts` (`REM23-12` / `P3-UX-12`, `ARCH23-09`)** :
     - Le test `#10` ([`PNG final`](../e2e-campaign-epic-22/screenshots/03-human-led-anchor-and-arbitration/desktop-cockpit--signature-de-l-ancrage-violet-30-car-rejet-agent-422-arbitrage-motive-et-survie-au-f5--passed.png)) retourne sur `/cockpit` avant la capture `afterEach`, masquant `HumanLedAnchorCard` (`#6D28D9`) et `ArbitrationTieBreakCard` (`#D97706`).

### 1.2 Exploration, Analyse d'Impact GitNexus, Factorisation & Dette Technique
- **Analyse d'Impact GitNexus (`repo: "/home/romain/Documents/Projects/ORCIA"`)** :
  - `FourZoneTopHeaderSection` (`packages/ui/src/primitives/FourZoneTopHeaderSection.tsx:L32-L291`) : `impactedCount: 127`, `risk: "CRITICAL"`, `epistemic: "exact"`, `direct: 87`, `d=2: 33`, `d=3: 7`, `processes_affected: 138`, `modules_affected: 18`.
  - `ModuleWorkspaceView` (`apps/web/src/components/ModuleWorkspaceView.tsx:L23-L120`) : `impactedCount: 150`, `risk: "CRITICAL"`, `epistemic: "exact"`, `direct: 108`, `d=2: 35`, `d=3: 7`, `processes_affected: 143`, `modules_affected: 20` *(note index GitNexus : le uid du nœud contexte présentait une dérive `2 commitsBehind` ; fichier vérifié directement sur `L1-L120`)*.
  - `CockpitFeaturePanel` (`apps/web/src/features/cockpit/index.tsx`) : `impactedCount: 127`, `risk: "CRITICAL"`, `epistemic: "exact"`, `direct: 87`, `d=2: 33`, `d=3: 7`, `processes_affected: 138`, `modules_affected: 18`.
  - `CockpitHumanLedGovernanceSection` (`apps/web/src/features/cockpit/CockpitHumanLedGovernanceSection.tsx:L1-L383`) : nœud touché par la dérive d'index ; vérifié par lecture directe (`L230-L383`).
- **Volumétrie & Découpage (`> 300–400` L)** :
  - `apps/web/src/features/cockpit/CockpitHumanLedGovernanceSection.tsx` mesure **`383` lignes** : lors de son intégration dans les 3 blocs stricts de `/cockpit` / Vue Fokus, séparer les sous-vues (`HumanLedAnchorBlock` / `ArbitrationBlock`) pour rester sous `< 300` L.
  - Extraire un composant partagé de champ mot de passe avec bouton œil dans `packages/ui` afin d'éviter la duplication entre `FirstBootAdminSetupModal` (`Story 23.4`) et `BiModeLoginView` (`Story 23.5`).

---

## 2. Plan d'Implémentation

### 2.1 Schéma de Données & Migrations Alembic (`infra/migrations/versions/`)
- Aucune migration PostgreSQL 18 requise en Story 23.5.

### 2.2 Noyau Métier Hexagonal (`packages/orcia-core/`)
- Vérifier qu'aucun libellé de catalogue système ou graine ne réinjecte `"embedding"` ou `"Processus standard"` en tant que jargon technique UI visible ; ajuster les traductions côté `i18n` et présentations UI.

### 2.3 Couche Backend API, Sécurité & Contrats (`apps/api/`, `packages/api-client/`)
- Aucune rupture OpenAPI : toutes les routes existantes restent inchangées (`0-diff` OpenAPI).

### 2.4 Interface Utilisateur & Expérience (`apps/web/`, `packages/ui/`)
1. **Cockpit `<= 3` Blocs Visuels Stricts (`cockpit/index.tsx`, `StreamlinedCockpitView.tsx`, `CockpitRunsSection.tsx`, `CockpitHumanLedGovernanceSection.tsx`)** :
   - Bloc 1 : **Accostage `X/6`** (masqué à `6/6` ou repliable).
   - Bloc 2 : **File des décisions humaines** (bandeau calme lorsque `0` décision ; affichage ciblé de `HumanLedAnchorCard` / `ArbitrationTieBreakCard` **uniquement** lorsqu'un run actif ou une décision l'exige, ou à l'ouverture d'un run — tout en préservant les points de montage attendus par `apps/web/e2e/03-human-led-anchor-and-arbitration.spec.ts#L41-L42` dès qu'un workspace est actif).
   - Bloc 3 : **Lancement & accès rapides consolidés** avec titre clair (`ⓘ`), fusionnant la barre d'accès assistant / processus / espace sans dupliquer plusieurs boutons vers `Mon Assistant` ni laisser un formulaire anonyme tout en bas.
2. **`TopHeaderBar`, Logo Zone 1, Breadcrumb, Loader & `/login` (`FourZoneTopHeaderSection.tsx`, `FourZoneSidebarRail.tsx`, `shellPresets.ts`, `ShellAuthFallbackView.tsx`, `BiModeLoginView.tsx`)** :
   - Supprimer `topbar-fixed-workspace-selector` (`L128-L153`) sur Desktop `>= 768px` (le Double Sélecteur en Zone 1 fait foi ; conserver l'accès compact uniquement sur mobile `< 768px` si nécessaire).
   - Déplacer la marque/logo cliquable `ORCIA` en tête de `Zone 1` (`FourZoneSidebarRail.tsx`, `DESIGN.md` §2.1).
   - Enrichir `buildShellBreadcrumbItems` (`shellPresets.ts#L178-L200`) avec l'équipe / direction active (`ORCIA > [Équipe] > Module`).
   - Raccourcir le placeholder de recherche à `Rechercher… (⌘K)`, élargir le bloc rôle en pied de sidebar pour éviter la troncature, enrichir `ShellHydratingLoaderView` (`ShellAuthFallbackView.tsx`) d'un logo + spinner discret, et ajouter logo `ORCIA` + bouton œil mot de passe sur `BiModeLoginView.tsx` (`/login`).
3. **Épuration `/assistant` & Microcopy (`ModuleWorkspaceView.tsx`, `SavedConversationsAndThreadView.tsx`, `AssistantSpeedSelectorAndStreamView.tsx`, `fr.ts`)** :
   - Exclure `"inbox"` dans `ModuleWorkspaceView.tsx#L60-L62` (en logeant `ⓘ` directement dans `AssistantTopToolbar`).
   - Masquer les compteurs `(0)` quand vides dans `SavedConversationsAndThreadView.tsx` — **attention E2E** : mettre à jour les 4 sélecteurs `/^Dossiers \(\d+\)$/` dans `apps/web/e2e/02-assistant-streaming-and-folders.spec.ts#L66,L81,L95,L105` pour qu'ils ciblent le `data-testid` stable ou `/^Dossiers/` (avec compteur optionnel).
   - Unifier tous les boutons de la barre d'assistant sur `orcia-ds-btn`, renforcer le contraste du bouton d'envoi `➤` (`>= 4,5:1` WCAG AA), et remplacer `"embedding"` par `"indexation sémantique"` ainsi que `"Processus standard"` par un libellé métier clair dans `fr.ts`.
4. **Preuves intermédiaires `#10` (`apps/web/e2e/03-human-led-anchor-and-arbitration.spec.ts`)** :
   - Attacher deux captures `testInfo.attach(...)` (ancrage violet `#6D28D9` `HumanLedAnchorCard` et arbitrage `#D97706` `ArbitrationTieBreakCard`) au fil du scénario sans allonger le budget temps `< 35 s`.

### 2.5 Analyse d'Impact sur la Pyramide des Tests (`AD-17` — Couches 1 à 5 + Sécurité, Obligatoire)
- **Couche 1b (`Vitest`)** : mise à jour et ajout d'assertions dans `packages/ui/src/__tests__/` et `apps/web/src/__tests__/` (`cockpit <= 3 blocs`, absence `topbar-fixed-workspace-selector` à `1440px`, bouton œil `/login`, exclusion en-tête `ModuleWorkspaceView` sur `inbox`, zéro `(0)`, zéro `"embedding"` dans `fr.ts`).
- **Couche 5 (E2E Playwright)** : `02-assistant-streaming-and-folders.spec.ts`, `03-human-led-anchor-and-arbitration.spec.ts` (avec captures attachées `HumanLedAnchorCard` + `ArbitrationTieBreakCard`), `10-command-palette-search.spec.ts`, `11-screens-smoke-without-server-errors.spec.ts` et `shell.spec.ts` verts Desktop + Mobile.

---

## 3. Bilan des Modifications & Résultats (Post-Implémentation)

> *[Pré-implémentation initialisée en Story 22.10 — à compléter après implémentation et validation de la Story 23.5]*

### 3.1 Fichiers Développés & Modifiés
| Fichier | Nature (Création / Modification / Refactoring) | Description synthétique |
| :--- | :--- | :--- |
| `apps/web/src/features/cockpit/*` & `packages/ui/src/primitives/StreamlinedCockpitView.tsx` | Refactoring / Modification | *[À compléter après implémentation Story 23.5]* |
| `packages/ui/src/primitives/{FourZoneTopHeaderSection,FourZoneSidebarRail,BiModeLoginView}.tsx` & `apps/web/src/components/{shellPresets,ShellAuthFallbackView}.ts*` | Modification | *[À compléter après implémentation Story 23.5]* |
| `apps/web/src/components/ModuleWorkspaceView.tsx`, `features/inbox/*`, `i18n/locales/fr.ts` | Modification | *[À compléter après implémentation Story 23.5]* |
| `apps/web/e2e/02-assistant-streaming-and-folders.spec.ts` & `03-human-led-anchor-and-arbitration.spec.ts` | Modification | *[À compléter après implémentation Story 23.5]* |

### 3.2 Résultats Chiffrés, Métriques & Qualité
- **Couverture de tests** : *[À compléter — $\ge 90\%$ requis]*
- **Qualité statique & Architecture** : `pnpm turbo run lint typecheck test`, `vite build`, `gitnexus_detect_changes()` *[À compléter]*

### 3.3 Validation & Procédure de Test sur Toute la Pyramide (`AD-17` + 5 Garde-Fous de Câblage Vertical)
- *[À compléter après validation `02-assistant`, `03-human-led`, `11-screens-smoke` et inspection visuelle des captures `#5`, `#8`, `#10`]*
