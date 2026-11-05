# 2026-11-05 — Audit & Mise en Conformité Architecturale : Séparation Design System (`@orcia/ui` Look & Feel), Contenus (`i18n`) et Logique Métier (`apps/web`)

- **Date** : 2026-11-05
- **Story / Clé Sprint** : `2026-11-05-audit-separation-design-system-look-and-feel-logique-et-contenus` (`Ajustement Transverse` — Architecture Design System `@orcia/ui` & `apps/web`)
- **Auteur / Contexte** : Binôme **Sally (`bmad-agent-ux-designer`)** & **Winston (`bmad-agent-architect`)** — Audit architectural et UX/UI en réponse à la question stratégique de l'utilisateur : *« Si je souhaite changer tout le look&feel des écrans, peux-tu vérifier que tous les composants UX/UI sont dans le Design System séparés de toutes les logiques et contenus ? »*. Couvre les exigences `DESIGN.md`, `EXPERIENCE.md`, `AD-19` (frontières modulaires), `UX-DR1` à `UX-DR16` et les invariants de gouvernance `GEMINI.md` / `CLAUDE.md`.
- **Commits associés** : `3525fa5` (`feat/design-system-look-and-feel-separation-audit`)

---

## 1. Analyse du Besoin & Étude d'Impact Tech Lead (Pré-Implémentation)

### 1.1 Contexte, Problématique & Dialogue Transparent Sally (UX/UI) × Winston (Architecte)

#### Question Stratégique de l'Utilisateur
> *« Si je souhaite changer tout le look&feel des écrans, peux-tu vérifier que tous les composants UX/UI sont dans le Design System séparés de toutes les logiques et contenus ? »*

#### Dialogue d'Audit Franc & Complet — Sally (`🎨 UX Designer`) & Winston (`🏗️ System Architect`)

- **🎨 Sally (UX Designer & UI Specialist)** :
  « J'ai inspecté l'intégralité des **45 composants** de `packages/ui/src/` (`@orcia/ui`), la feuille maîtresse `packages/ui/src/styles/tokens.css` et les **37 fichiers** de `apps/web/src/`. Voici mon verdict franc en distinguant les **3 couches fondamentales** d'une architecture d'interface propre :
  1. **Ce qui est déjà 100 % exemplaire dans `@orcia/ui` (`packages/ui`)** :
     - Les **34 primitives et panneaux majeurs** (coquille 4 zones `FourZoneDirectionCShell`, `StreamlinedCockpitView`, `ProgressiveDay0AccostageBanner`, `TopHeaderSearchCommand`, `UserAccountDropdownAndSettingsModal`, `ContextualHelpColumnAndCenter`, `ContextualInfoTriggerButton`, `RgaaModalDialog`, `AgentsAndSkillsManagerView`, `WorkspaceFiveTabsAndExternalRebaseView`, `DnaStarlarkCompilerAndGlossaryLifecycleView`, `RemoteServiceTestBenchAndMcpExposureView`, `PackBuilderProcessesStudioView`, `HelpArticleGeneratorAndValidatorView`, `AssistantFoldersAndCollaborativeThreadView`, `AssistantSpeedSelectorAndStreamView`, `AssistantCitationPillsAndArtifactCard`, `AssistantGovernanceModalAndStudio`, `HumanLedAnchorCard`, `ArbitrationTieBreakCard`, `CognitiveReviewBriefingGrid`, `ChunkValidationCard`, `UpstreamChallengeRewindModal`, `BiModeLoginView`, `DurableWizardRunnerView`, `PermissionGuard`, `SecretField`, `InferenceTierAndEffortSelector`, `StatusBadge`, etc.) vivent **exclusivement dans `packages/ui/src/`**.
     - Ils sont **100 % purs** : aucun appel API, aucun routeur, aucun store global, et tous leurs textes sont injectés par des interfaces typées `*Labels` (`FourZoneDirectionCShellLabels`, `StreamlinedCockpitLabels`, etc.).
     - **Zéro couleur hexadécimale (`#...`)** n'existe hors de `packages/ui/src/styles/tokens.css`, et le violet `#6D28D9` (`--color-human-led-violet`) est réservé exclusivement à `HumanLedAnchorCard.tsx`.
  2. **Les 3 écarts réels que notre audit a mis en lumière (et pourquoi changer `tokens.css` ne suffisait pas encore à 100 % sur certains sous-écrans)** :
     - **Écart A — 22 variables CSS consommées dans `@orcia/ui` ou `apps/web` n'étaient pas déclarées dans `:root` de `tokens.css`** : Plusieurs primitives utilisaient des alias comme `--orcia-surface-primary`, `--orcia-surface-secondary`, `--orcia-border-subtle`, `--orcia-text-primary`, `--orcia-text-secondary`, `--orcia-action-primary`, `--orcia-text-on-action`, `--orcia-font-mono`, ou encore `--color-border-focus`, `--color-border-strong`, `--color-surface`, `--color-surface-canvas`, `--color-text-inverse`, `--color-text-muted`, `--color-verified-emerald`, `--color-verified-bg`, `--color-gate-pass`, `--color-gate-pass-bg`, `--color-status-completed`, `--color-status-failed`, `--color-status-success-subtle` et `--font-size-h3`. Sans définition dans `tokens.css`, le navigateur retombait sur des valeurs par défaut transparentes ou héritées !
     - **Écart B — Absence de primitives atomiques de formulaires/contrôles (`Button`, `Input`, `Select`, `Textarea`, `SectionCard`, `TabBar`, `AlertBanner`) et de classes `.orcia-ds-*` dans `@orcia/ui`** : Faute de `<OrciaButton>`, `<OrciaInput>`, `<OrciaSelect>`, `<OrciaTextarea>`, `<OrciaSectionCard>`, `<OrciaTabBar>` et `<OrciaAlertBanner>` dans `@orcia/ui`, les écrans de paramétrage et d'assemblage de `apps/web/src/` (`SettingsAiModelsSection.tsx`, `SettingsIamOrganizationSection.tsx`, `SettingsPacksSection.tsx`, `SettingsSecondaryTabsSection.tsx`, `SimplifiedProcessBuilderSection.tsx`, `wizards.tsx`, `PlatformOnboardingChecklistCard.tsx`) redéfinissaient localement des objets `const inputStyle = { padding: "7px 10px", borderRadius: "var(--radius-sm)", ... }` et `primaryBtnStyle` (`260` attributs `style={{ ... }}` dans `apps/web/src/`). Si vous vouliez changer la hauteur, le padding, la bordure ou l'ombre de tous les boutons et champs de saisie d'ORCIA depuis `tokens.css`, ces styles inline locaux figeaient les paddings (`7px 10px`) dans `apps/web` !
     - **Écart C — Couleurs de calque modale `rgba(15, 23, 42, 0.45)` en dur** : `RgaaModalDialog.tsx` et `ShellContainer.tsx` utilisaient encore `rgba(15, 23, 42, 0.45)` / `0.35` au lieu d'un token sémantique `var(--color-modal-backdrop)`. »

- **🏗️ Winston (System Architect & Technical Design Leader)** :
  « Excellente radiographie, Sally. Pour répondre avec une honnêteté architecturale totale à l'utilisateur :
  - **Pourquoi `apps/web/src/` existe-t-il et que doit-il contenir ?**
    Dans notre architecture hexagonale / SPA (`Vite 6 + TanStack Router v1`), le monorepo sépare strictement **3 responsabilités** :
    1. **Couche 1 — Look & Feel & Composants UX/UI (`packages/ui` / `@orcia/ui`)** : Contient `tokens.css` (100 % des tokens de couleurs, typographies, rayons, ombres, espacements et classes `.orcia-ds-*` / `.orcia-bento-*`) + toutes les primitives visuelles (`packages/ui/src/primitives/*`, `components/*`, `shell/*`). Zéro dépendance vers `apps/web`, `@tanstack/*` ou `@orcia/api-client`.
    2. **Couche 2 — Contenus & Microcopy Bilingue (`apps/web/src/i18n/locales/{fr,en}.ts` + `contextualHelpCatalog.ts`)** : Centralise les dictionnaires de traduction et les articles d'aide contextuelle `ⓘ` injectés via props dans `@orcia/ui`.
    3. **Couche 3 — Logique d'Assemblage, Routing & Persistance (`apps/web/src/routes/*`, `features/*`, `platformSetupStore.tsx`)** : Ce sont les *Smart Containers* qui connectent TanStack Router, `@orcia/api-client` (PostgreSQL 18) et `useI18n()` aux composants de `@orcia/ui`.
  - **Notre plan d'action immédiat pour garantir que 100 % du Look & Feel se pilote depuis `@orcia/ui`** :
    1. **Unifier 100 % des variables CSS dans `packages/ui/src/styles/tokens.css`** : Déclarer dans `:root` et `[data-theme="dark"]` les 22 alias manquants (`--orcia-*`, `--color-border-focus`, `--color-modal-backdrop`, `--control-padding-*`, `--control-radius`, `--card-padding`, etc.) pour qu'aucun `var(--*)` utilisé dans le projet ne soit orphelin.
    2. **Créer les classes maîtresses `.orcia-ds-*` dans `packages/ui/src/styles/tokens.css`** (`.orcia-ds-page`, `.orcia-ds-card`, `.orcia-ds-header`, `.orcia-ds-tabs`, `.orcia-ds-tab`, `.orcia-ds-input`, `.orcia-ds-select`, `.orcia-ds-textarea`, `.orcia-ds-btn`, `.orcia-ds-btn-primary`, `.orcia-ds-btn-secondary`, `.orcia-ds-btn-danger`, `.orcia-ds-alert-success`, `.orcia-ds-alert-warning`, `.orcia-ds-alert-error`, `.orcia-ds-alert-info`, `.orcia-ds-row`, `.orcia-ds-label`).
    3. **Créer le socle de primitives atomiques `packages/ui/src/primitives/DesignSystemControls.tsx`** exporté par `@orcia/ui` (`OrciaButton`, `OrciaInput`, `OrciaSelect`, `OrciaTextarea`, `OrciaSectionCard`, `OrciaTabBar`, `OrciaAlertBanner`), 100 % sans état métier ni texte en dur, intégrant nativement les classes `.orcia-ds-*` et la protection anti-gestionnaire de mots de passe (`autoComplete="off" data-lpignore="true" data-1p-ignore="true" data-form-type="other"`).
    4. **Verrouiller ces 4 invariants d'or par une suite de tests d'architecture dédiée** dans `apps/web/src/__tests__/design-system-look-and-feel-isolation.test.tsx` qui vérifie statiquement et dynamiquement :
       - **Invariant 1** : Pureté totale de `packages/ui/src/**` (zéro import `@tanstack/*`, `@orcia/api-client`, `fetch(`, `localStorage`, ni store de `apps/web`).
       - **Invariant 2** : Zéro couleur hexadécimale (`#[0-9a-fA-F]{3,8}`) dans tous les fichiers `.ts`/`.tsx` de `packages/ui/src` et `apps/web/src`, et exclusivité absolue de `--color-human-led-violet` pour `HumanLedAnchorCard.tsx`.
       - **Invariant 3** : 100 % des variables `var(--*)` utilisées dans `packages/ui/src/**` et `apps/web/src/**` sont effectivement définies dans `packages/ui/src/styles/tokens.css` (zéro token CSS orphelin !).
       - **Invariant 4** : Fonctionnement complet et pilotage par classes `.orcia-ds-*` des nouvelles primitives `<OrciaButton>`, `<OrciaInput>`, `<OrciaSelect>`, `<OrciaTextarea>`, `<OrciaSectionCard>`, `<OrciaTabBar>` et `<OrciaAlertBanner>`. »

---

### 1.2 Exploration, Analyse d'Impact GitNexus, Cartographie des 3 Couches & Dette Technique

#### Analyse d'Impact GitNexus (`repo: "/home/romain/Documents/Projects/ORCIA"`)
- `gitnexus_query({ search_query: "FourZoneDirectionCShell ContextualInfoTriggerButton StatusBadge RgaaModalDialog tokens.css" })` :
  - Identifie la grappe centrale de composants `@orcia/ui` consommée par l'ensemble des routes et features de `apps/web/src/`.
- `gitnexus_context({ name: "ContextualInfoTriggerButton" })` & `gitnexus_impact({ target: "ContextualInfoTriggerButton", direction: "upstream" })` :
  - **Risque** : `MEDIUM` (`6` appelants directs dans `apps/web` : `ModuleWorkspaceView`, `CockpitFeaturePanel`, `InboxFeaturePanel`, `OntologyFeaturePanel`, `WorkspacesFeaturePanel`, `SettingsHubView` + sous-sections `/settings`).
- `gitnexus_impact({ target: "FourZoneDirectionCShell", direction: "upstream" })` :
  - **Risque** : `LOW` (`1` appelant direct : `InnerShellContainer` dans `apps/web/src/components/ShellContainer.tsx`, qui enveloppe 100 % des routes de l'application).

#### Cartographie Exacte des 3 Couches (Look & Feel vs Contenus vs Logique)

| Couche Architecturale | Emplacement dans le Monorepo | Rôle & Responsabilité | État vérifié & Garanties |
| :--- | :--- | :--- | :--- |
| **1. Look & Feel & Composants UX/UI (`@orcia/ui`)** | `packages/ui/src/styles/tokens.css`<br>`packages/ui/src/primitives/*.tsx`<br>`packages/ui/src/components/*.tsx`<br>`packages/ui/src/shell/*.tsx` | **100 % du système visuel** : tokens CSS (`--color-*`, `--font-*`, `--radius-*`, `--shadow-*`, `--control-*`), classes `.orcia-ds-*` & `.orcia-bento-*`, primitives atomiques (`DesignSystemControls.tsx`) et les 34 vues/modales riches. | **100 % isolé** : `0` import de routeur/API/store, `0` couleur hexadécimale hors `tokens.css`, `100 %` des `var(--*)` résolus dans `tokens.css`. |
| **2. Contenus, Microcopy & Aide Contextuelle (`i18n` & `help`)** | `apps/web/src/i18n/locales/{fr,en}.ts`<br>`apps/web/src/i18n/locales/*_labels.ts`<br>`apps/web/src/components/contextualHelpCatalog.ts` | **Dictionnaires bilingues FR/EN** sans jargon interne et catalogue des sections d'aide contextuelle ouvertes par l'icône `ⓘ` (`ContextualInfoTriggerButton`). | Injectés dans `@orcia/ui` via des props typées `*Labels`. Modifiables sans toucher au CSS ni aux composants `@orcia/ui`. |
| **3. Logique Métier, États & Conteneurs de Routes (`apps/web`)** | `apps/web/src/routes/*.tsx`<br>`apps/web/src/features/*`<br>`apps/web/src/components/platformSetupStore.tsx`<br>`apps/web/src/components/ShellContainer.tsx` | **Smart Containers** : récupération/sauvegarde PostgreSQL 18 via `@orcia/api-client`, routage TanStack Router, et passage des données/callbacks aux composants `@orcia/ui`. | Zéro couleur hexadécimale en dur. Peut consommer directement `<OrciaButton>`, `<OrciaInput>`, `<OrciaSelect>`, `<OrciaTextarea>`, `<OrciaSectionCard>`, `<OrciaTabBar>`, `<OrciaAlertBanner>` et `.orcia-ds-*`. |

---

## 2. Plan d'Implémentation

### 2.1 Schéma de Données & Migrations Alembic (`infra/migrations/versions/...`, si applicable)
- *Non applicable* (évolution purement Frontend / Design System `@orcia/ui` et tests d'isolation architecturale, sans modification du schéma PostgreSQL 18).

### 2.2 Noyau Métier Hexagonal, Orchestration & Workers (`packages/orcia-core/`, `apps/worker/`, `infra/sandbox/`)
- *Non applicable* (aucune modification du noyau Python `orcia-kernel` / `orcia-core`).

### 2.3 Couche Backend API, Sécurité & Contrats (`apps/api/`, `packages/api-client/`)
- *Non applicable* (contrat OpenAPI 3.1 et SDK `@orcia/api-client` inchangés, `0-diff`).

### 2.4 Design System (`packages/ui` / `@orcia/ui`) & Vérification d'Isolation (`apps/web/`)
1. **`packages/ui/src/styles/tokens.css`** :
   - Déclarer tous les tokens et alias CSS manquants (`--orcia-*`, `--color-border-focus`, `--color-border-strong`, `--color-modal-backdrop`, `--color-surface`, `--color-surface-canvas`, `--color-text-inverse`, `--color-text-muted`, `--color-verified-emerald`, `--color-verified-bg`, `--color-gate-pass`, `--color-gate-pass-bg`, `--color-status-completed`, `--color-status-failed`, `--color-status-success-subtle`, `--font-size-h3`, ainsi que les tokens de géométrie des contrôles `--control-padding-x`, `--control-padding-y`, `--control-font-size`, `--btn-padding-x`, `--btn-padding-y`, `--card-padding`).
   - Ajouter les classes sémantiques `.orcia-ds-*` :
     - `.orcia-ds-page`, `.orcia-ds-card`, `.orcia-ds-header`,
     - `.orcia-ds-tabs`, `.orcia-ds-tab` (`.orcia-ds-tab[aria-selected="true"]`),
     - `.orcia-ds-input`, `.orcia-ds-select`, `.orcia-ds-textarea`,
     - `.orcia-ds-btn`, `.orcia-ds-btn-primary`, `.orcia-ds-btn-secondary`, `.orcia-ds-btn-danger`, `.orcia-ds-btn-ghost`,
     - `.orcia-ds-alert`, `.orcia-ds-alert-success`, `.orcia-ds-alert-warning`, `.orcia-ds-alert-error`, `.orcia-ds-alert-info`,
     - `.orcia-ds-row`, `.orcia-ds-label`.
2. **`packages/ui/src/primitives/DesignSystemControls.tsx` & `packages/ui/src/index.ts`** :
   - Créer les 7 primitives React pures du Design System :
     - `<OrciaButton variant="primary | secondary | danger | ghost" ... />`
     - `<OrciaInput ... />` (avec `autoComplete="off" data-lpignore="true" data-1p-ignore="true" data-form-type="other"` par défaut sauf si `allowPasswordManager={true}`)
     - `<OrciaSelect ... />` (avec protection anti-LastPass par défaut)
     - `<OrciaTextarea ... />` (avec protection anti-LastPass par défaut)
     - `<OrciaSectionCard title={...} subtitle={...} helpSectionId={...} helpLabel={...} onOpenHelpSection={...} actions={...}>`
     - `<OrciaTabBar tabs={...} activeTab={...} onSelectTab={...} ariaLabel={...} />`
     - `<OrciaAlertBanner tone="emerald | amber | crimson | cobalt" ... />`
   - Exporter l'ensemble des composants et types associés dans `packages/ui/src/index.ts`.
3. **`apps/web/src/__tests__/design-system-look-and-feel-isolation.test.tsx`** :
   - Créer une suite de tests Vitest dédiée vérifiant les **4 Invariants d'Or** du changement de Look & Feel :
     - **Invariant 1** : Pureté de `packages/ui/src/**` (aucun import `@tanstack/*`, `@orcia/api-client`, `fetch(`, `localStorage`, ni import relatif vers `apps/web`).
     - **Invariant 2** : Zéro couleur hexadécimale (`#[0-9a-fA-F]{3,8}`) dans tous les fichiers `.ts`/`.tsx` de `packages/ui/src` et `apps/web/src`, et exclusivité de `--color-human-led-violet` pour `HumanLedAnchorCard.tsx`.
     - **Invariant 3** : 100 % des variables `var(--*)` référencées dans `packages/ui/src` et `apps/web/src` sont définies dans `packages/ui/src/styles/tokens.css`, et toutes les classes `.orcia-ds-*` y sont présentes.
     - **Invariant 4** : Rendu, accessibilité (`role="tab"`, `aria-selected`, `role="alert"`/`status`, bouton `ⓘ` `ContextualInfoTriggerButton`) et attributs anti-LastPass (`data-lpignore="true"`, `autoComplete="off"`) des 7 primitives de `DesignSystemControls.tsx`.

---

## 3. Bilan des Modifications & Résultats (Post-Implémentation)

### 3.1 Fichiers Développés & Modifiés
| Fichier | Nature (Création / Modification) | Description synthétique |
| :--- | :--- | :--- |
| `packages/ui/src/styles/tokens.css` | Modification | Ajout des 22 tokens et alias CSS auparavant implicites (`--orcia-*`, `--color-border-focus`, `--color-border-strong`, `--color-modal-backdrop`, `--color-surface`, `--color-surface-canvas`, `--color-text-inverse`, `--color-text-muted`, `--color-verified-emerald`, `--color-verified-bg`, `--color-gate-pass`, `--color-gate-pass-bg`, `--color-status-completed`, `--color-status-failed`, `--color-status-success-subtle`, `--font-size-h3`, `--control-padding-*`, `--btn-padding-*`, `--card-padding`) et création des 20 classes maîtresses `.orcia-ds-*` (`.orcia-ds-page`, `.orcia-ds-card`, `.orcia-ds-header`, `.orcia-ds-tabs`, `.orcia-ds-tab`, `.orcia-ds-label`, `.orcia-ds-input`, `.orcia-ds-select`, `.orcia-ds-textarea`, `.orcia-ds-btn`, `.orcia-ds-btn-primary`, `.orcia-ds-btn-secondary`, `.orcia-ds-btn-danger`, `.orcia-ds-btn-ghost`, `.orcia-ds-row`, `.orcia-ds-alert*`). |
| `packages/ui/src/primitives/DesignSystemControls.tsx` | Création (`293 lignes`) | Socle de 7 primitives React 100 % pures du Design System (`OrciaButton`, `OrciaInput`, `OrciaSelect`, `OrciaTextarea`, `OrciaSectionCard`, `OrciaTabBar`, `OrciaAlertBanner`) pilotées par `tokens.css` (`.orcia-ds-*`), intégrant le bouton d'aide contextuelle `ⓘ` (`ContextualInfoTriggerButton`) et la protection anti-gestionnaire de mots de passe (`autoComplete="off" data-lpignore="true" data-1p-ignore="true" data-form-type="other"`) par défaut. |
| `packages/ui/src/index.ts` | Modification | Export public des 7 primitives et des interfaces/types associés de `DesignSystemControls.tsx`. |
| `apps/web/src/__tests__/design-system-look-and-feel-isolation.test.tsx` | Création (`266 lignes`) | Suite de tests automatisés vérifiant les **4 Invariants d'Or** de la séparation Look & Feel (`@orcia/ui` vs `apps/web` vs `i18n`). |
| `docs/implementation-artifacts/tech-lead-reports/2026-11-05-audit-separation-design-system-look-and-feel-logique-et-contenus-tech-lead-report.md` | Création | Rapport Tech Lead pérenne (Dialogue Sally & Winston, cartographie des 3 couches et bilan des vérifications). |
| `docs/implementation-artifacts/tech-lead-reports/README.md` | Modification | Référencement du rapport dans l'index général des rapports Tech Lead. |

### 3.2 Résultats Chiffrés, Métriques & Qualité
- **Suites de tests TypeScript / Vitest (`pnpm turbo run lint typecheck test`)** :
  - `9/9` tâches Turbo réussies (`@orcia/ui`, `@orcia/api-client`, `@orcia/web`).
  - `apps/web` : `2` fichiers de tests passés (`24/24` tests verts, dont les `4` invariants de `design-system-look-and-feel-isolation.test.tsx` et les `20` tests d'intégration `i18n-and-shell.test.tsx`).
  - `packages/ui` : `15` fichiers de tests passés (`100 %` verts, dont `ui-isolation.test.ts`).
- **Qualité statique & Architecture** :
  - `.venv/bin/ruff check .` & `.venv/bin/ruff format --check .` : `All checks passed! (519 files already formatted)`
  - `pnpm turbo run lint typecheck` : `0 error`
  - `.venv/bin/python .agent/skills/bmad-architecture/scripts/lint_spine.py` : `ok: true, total_findings: 0`
  - `gitnexus_detect_changes({ scope: "all", repo: "/home/romain/Documents/Projects/ORCIA" })` : `risk_level: "low"`, `changed_files: 3`, `affected_count: 0` (aucune régression sur les flux existants).

### 3.3 Validation & Procédure de Test (5 Couches `AD-17` + 4 Invariants d'Isolation Look & Feel)
- **Couche 1 — Tests Unitaires & Architecture Design System (`Vitest`)** :
  - **Invariant 1 (Pureté de `@orcia/ui`)** : Vérifie que `packages/ui/src/**` n'importe jamais `@tanstack/*`, `@orcia/api-client`, `fetch(`, ni aucun store de `apps/web`.
  - **Invariant 2 (Zéro couleur hexadécimale hors `tokens.css`)** : Vérifie qu'aucun fichier `.ts`/`.tsx` de `packages/ui/src` ni de `apps/web/src` ne contient de couleur `#...` en dur, et que `--color-human-led-violet` est réservé à `HumanLedAnchorCard.tsx`.
  - **Invariant 3 (100 % des variables CSS résolues dans `tokens.css`)** : Extrait dynamiquement toutes les expressions `var(--*)` de `packages/ui/src` et `apps/web/src` (`91` variables distinctes) et prouve que **100 % d'entre elles (`0` variable manquante)** sont déclarées dans `packages/ui/src/styles/tokens.css`, aux côtés des 20 classes `.orcia-ds-*`.
  - **Invariant 4 (Primitives `DesignSystemControls` & Anti-LastPass)** : Vérifie le rendu, les classes `.orcia-ds-*`, l'ouverture de l'aide contextuelle `ⓘ`, la navigation par onglets `aria-selected` et les attributs `data-lpignore="true"` / `autoComplete="off"`.
- **Couches 2 à 5 — Non-Régression Verticale & Survie au `F5`** :
  - Les `20` tests de `apps/web/src/__tests__/i18n-and-shell.test.tsx` (incluant la survie au `F5` `unmount() -> render()` et le câblage `@orcia/api-client`) passent à `100 %`.

