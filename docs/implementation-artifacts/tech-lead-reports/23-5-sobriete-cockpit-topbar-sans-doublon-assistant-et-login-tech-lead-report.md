# Story 23.5 — Sobriété Cockpit (`<= 3` Blocs), `TopHeaderBar` Sans Doublon/Troncature, Épuration `/assistant` & `/login` et Captures `#10`

- **Date** : 2026-11-19 (clôture 2026-11-20)
- **Story / Clé Sprint** : `23-5-sobriete-cockpit-topbar-sans-doublon-assistant-et-login` (`Epic 23` — Vague 1 `P1`–`P3`)
- **Capacité(s)** : `CAP-001`, `CAP-023`, `CAP-041`, `CAP-062`, `CAP-070`, `CAP-072`, `CAP-073`, `CAP-190` — classification : `feature` + `ux` (`REM23-09`, `REM23-10`, `REM23-11`, `REM23-12` / `ARCH23-06`..`ARCH23-09`, `P1-UX-3`, `P2-UX-8`..`P2-UX-11`, `P3-UX-12`)
- **Auteur / Contexte** : `22.10-impl` (pré-implémentation) $\rightarrow$ `23.5-impl` / `23.5-test` / `23.5-validate` (`APPROVED` Round 2). Aligne la hiérarchie visuelle Direction C : ramène `/cockpit` à `<= 3` blocs visuels, supprime le sélecteur d'espace dupliqué dans `TopHeaderBar` (cause des troncatures à `1440px`), place le logo `ORCIA` en Zone 1 (`DESIGN.md` §2.1), sécurise la recherche fédérée multi-tenant + cache Speed 2, épure `/assistant` et `/login`, et garantit les captures jalons sur `/login`, `HumanLedAnchorCard` (`#6D28D9`) et `ArbitrationTieBreakCard` (`#D97706`).
- **Commits associés** : `feat/epic-23-remediation-pg18-sse-direction-c` (commit atomique Story 23.5 — `done`, validé `APPROVED` par `23.5-validate`)

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

> **Statut** : `done` — Validé **`APPROVED`** (Round 2) par `23.5-validate` (code, sécurité multi-tenant / cache Speed 2 et `10` captures PNG Desktop régénérées incluant les `3` jalons `/login`, `#6D28D9` et `#D97706`). Dette technique mineure non bloquante enregistrée sous `ACTION_ITEM-23.5` (`P3`) dans `docs/implementation-artifacts/sprint-status.yaml`.

### 3.1 Fichiers Développés & Modifiés (Round 1 + Round 2)
| Fichier | Nature (Création / Modification / Refactoring) | Description synthétique |
| :--- | :--- | :--- |
| `packages/orcia-core/src/orcia_core/rag/_internal/sql_federated_search.py`, `two_speed_search.py`, `__init__.py` | Création / Modification | Chargeur SQL PG18 fédéré multi-sources (`catalog_items`, `workflow_definitions_v2`, `declarative_pack_bundles`, `workspaces`, `assistant_folders`) avec filtrage multi-tenant (`user_id`, `user_role`, `primary_org_unit_id`), mode *fail-closed* anonyme et isolation du cache Speed 2 (`_speed2_cache`) par `user_id`/`user_role`. |
| `apps/api/src/orcia_api/routers/portal_and_help.py` | Modification | Propagation de `user.id`, `user.platform_role` et `user.primary_org_unit_id` vers `load_federated_search_candidates_pg18` et `TwoSpeedFederatedSearchService.execute_search` (`0-diff` OpenAPI). |
| `packages/ui/src/primitives/{CockpitOrientationCards,CockpitDecisionsCard}.tsx` & `StreamlinedCockpitView.tsx` | Création / Refactoring | Découpage modulaire du Cockpit en `<= 3` blocs visuels stricts (`Accostage`, `Décisions`, `Accès rapides`). |
| `packages/ui/src/primitives/{FourZoneSidebarRail,FourZoneTopHeaderSection,FourZoneDirectionCShell,SidebarAccountPopover,BiModeLoginView,UserProfileOverviewPage}.tsx` | Modification | Logo `ORCIA` (`sidebar-brand-logo`) en tête de Zone 1, masquage Desktop de `topbar-fixed-workspace-selector` lorsque la sidebar est ouverte (`isMobile \|\| railCollapsed`), `login-brand-header` + `OrciaPasswordInput` (`maskMode="password"`, bouton œil) sur `/login` et état `profile-kpis-loading` sur `/profile`. |
| `apps/web/src/features/cockpit/{useCockpitGovernanceController.ts,index.tsx,CockpitHumanLedGovernanceSection.tsx,CockpitRunsSection.tsx}` | Création / Refactoring | Extraction de `useCockpitGovernanceController` et montage conditionnel de `cockpit-human-led-governance-section` (masquée à `0` run, affichée dès qu'un run/état de gouvernance existe). |
| `apps/web/src/components/{ModuleWorkspaceView,ShellContainer,ShellContainerModals,ShellAuthFallbackView,ShellContextualHelpColumn,ShellFederatedSearchModal}.tsx`, `shellPresets.ts`, `agentsAndSkillsBridgeStore.ts` | Modification | Exclusion en-tête sur `"inbox"`, fil d'Ariane complet `ORCIA > [Équipe] > Module` (`buildShellBreadcrumbItems`), non-ouverture modale Jour 0 sur `/showcase`, loader enrichi `ShellHydratingLoaderView` et pont `orcia:assistant-prefill`. |
| `apps/web/src/features/inbox/{InboxDisabledBanner.tsx,inboxCitationHelpers.ts,index.tsx,InboxAuxiliaryPanels.tsx,SavedConversationsAndThreadView.tsx,useInboxPanelController.ts}` | Création / Modification | Masquage compteurs `(0)`, pré-remplissage `orcia:assistant-prefill`, transmission `citationCardPreview`, masquage `@draft` redondant, boutons unifiés `orcia-ds-btn` et contraste WCAG AA du bouton d'envoi. |
| `apps/web/src/i18n/locales/{assistant_labels,inbox_and_cockpit_labels,shell_and_search_labels}.ts` & `docs/help/{fr,en}/{assistant,showcase}.md` | Modification | Remplacement de `"embedding"` / `"Processus standard"`, placeholder court `Rechercher… (⌘K)` et mise à jour des fiches d'aide FR/EN. |
| `tests/integration/api/test_story_23_5_federated_search_postgres18.py`, `tests/unit/test_story_23_5_search_coverage.py` | Création | Tests `testcontainers` `pgvector/pgvector:pg18` sur `create_app()` réel sans `dependency_overrides` (5 tables PG18, Speed 1/Speed 2, test négatif d'isolation multi-utilisateurs `PRIVATE` / `PRIVATE_USER` / `_speed2_cache`) et couverture unitaire des branches de visibilité. |
| `packages/ui/src/__tests__/{story-23-5-sobriety-and-login-brand,four-zone-shell-and-cockpit}.test.tsx` & `apps/web/src/__tests__/{story-23-5-sobriety-and-citations-wiring,direction-c-shell-mobile-companion-and-dynamic-help,i18n-and-shell,orchestration-rewind-modal-and-gates-view,story-19-6-*,story-20-1-*,story-22-3-*}.test.tsx` | Création / Modification | Couverture Vitest complète (`BiModeLoginView`, `FourZoneSidebarRail`, `FourZoneTopHeaderSection`, `CockpitFeaturePanel`, `ModuleWorkspaceView`, `orcia:assistant-prefill`, fil d'Ariane `ORCIA > [Équipe] > Module`, non-régression `story-20-1`). |
| `apps/web/e2e/{02-assistant-streaming-and-folders,03-human-led-anchor-and-arbitration,11-screens-smoke-without-server-errors,14-auth-2fa-account-and-profile}.spec.ts`, `apps/web/e2e/support/e2eCaptureFixture.ts` | Modification | Support `captureMilestoneScreenshot` et captures jalons `/login` (`milestone-login-screen-and-password-eye.png`), ancrage violet `#6D28D9` (`milestone-human-led-anchor-violet.png`) et arbitrage ambre `#D97706` (`milestone-arbitration-tiebreak-amber.png`), synchronisation KPIs profil et sélecteurs dossiers. |

### 3.2 Résultats Chiffrés, Métriques & Qualité
- **Pytest Unitaires (Couche 1)** : `.venv/bin/pytest tests/unit/ -q` $\rightarrow$ **`794 passed`** (`100 %`, exit 0).
- **Couverture Recherche Fédérée & Intégration PG18 Réel (`test_story_23_5_federated_search_postgres18.py`, `test_contextual_help_and_accostage_postgres18.py` + unitaires RAG)** : **`14 passed`** sur Composition Root réel `create_app()` (`pgvector/pgvector:pg18`, sans `dependency_overrides`, incluant isolation multi-utilisateurs) :
  - `packages/orcia-core/src/orcia_core/rag/_internal/sql_federated_search.py` : **`100 %`** (`14 stmts, 0 miss, 6 branches, 0 brpart`).
  - `packages/orcia-core/src/orcia_core/rag/two_speed_search.py` : **`100 %`** (`59 stmts, 0 miss`).
  - `apps/api/src/orcia_api/routers/portal_and_help.py` : **`98 %`** (`55 stmts, 0 miss, 6 branches, 1 brpart: 104->113`).
- **Turbo JS/TS (Lint + Typecheck + Vitest)** : `pnpm turbo run lint typecheck test --force --concurrency=2` $\rightarrow$ **`9/9` tâches réussies** (`@orcia/api-client` **`20 passed`**, `@orcia/ui` **`124 passed`**, `@orcia/web` **`210 passed`**).
- **Gates Statiques, Architecture & Catalogue** :
  - `.venv/bin/ruff check` (`All checks passed!`) & `.venv/bin/ruff format --check` (`853 files already formatted`).
  - `.venv/bin/mypy --strict packages/orcia-core packages/orcia-connectors apps/api apps/worker` (`Success: no issues found in 552 source files`).
  - `.venv/bin/lint-imports` (`Contracts: 5 kept, 0 broken.` — `598` fichiers, `4295` dépendances).
  - `.venv/bin/python scripts/export_openapi.py --check` (`0-diff`).
  - `.venv/bin/python .agent/skills/bmad-architecture/scripts/lint_spine.py` (`0` finding).
  - `pnpm site:sync && pnpm site:check` & `scripts/check_implementation_docs.py` verts (`docs/product/capabilities.yaml` conservé intact jusqu'à `Story 23.7`).

### 3.3 Validation & Procédure de Test sur Toute la Pyramide (`AD-17` + 5 Garde-Fous de Câblage Vertical)
- **Chaîne Canari Desktop (`--project=desktop-cockpit --retries=0 --timeout=35000`, sans `ORCIA_E2E_SEED_FIXTURES`)** sur les `10` specs de la Story 23.5 (`00`, `01`, `02`, `03`, `09`, `10`, `11`, `14`, `21`, `shell`) : **`24 passed, 0 failed, 0 skipped`** (`4.8m`), avec `26` PNG vérifiés dont les `3` jalons `/login` (`milestone-login-screen-and-password-eye.png`), `#6D28D9` (`milestone-human-led-anchor-violet.png`) et `#D97706` (`milestone-arbitration-tiebreak-amber.png`).
- **Revue `23.5-validate` (Round 2)** : verdict **`APPROVED`** (code, sécurité multi-tenant / cache Speed 2 et inspection visuelle des `10` PNG Desktop régénérés).
- **Synchronisation GitNexus** : `npx gitnexus analyze` exécuté après commit atomique sur `feat/epic-23-remediation-pg18-sse-direction-c`.
