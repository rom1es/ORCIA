# 2026-11-05 — Site Web de Présentation & Documentation Vivante d'ORCIA (3 Piliers Étanches, Human-Led, Double Barrière Anti-Hallucination & Synchronisation Automatique)

- **Date** : 2026-11-05
- **Story / Clé Sprint** : `2026-11-05-site-presentation-orcia-3-piliers-human-led-anti-hallucination-et-sync-auto` (`Post-Epic 12` / `Ajustement Transverse & Vitrine Vivante`)
- **Auteur / Contexte** : Binôme **Sally (`bmad-agent-ux-designer`)** & **Winston (`bmad-agent-architect`)** — Création du site web de présentation et de documentation vivante d'ORCIA intégré directement dans l'application (`/showcase` accessible en 1 clic depuis l'interface) et doublé d'un export HTML5/CSS/JS statique autonome (`docs/site-catalog/index.html` & `dist/orcia-site/index.html`), structuré en 3 espaces strictement séparés (Vision Macro Human-Led & Double Barrière Anti-Hallucination / Guide Fonctionnel des 6 Dispositifs & 9 Écrans / Architecture & Choix Techniques Sous le Capot) + un 4e onglet d'Historique Vivant synchronisé par `infra/scripts/sync_site_catalog.py` (`pnpm site:sync`).
- **Commits associés** : *(complété en Section 3 après vérification)*

---

## 1. Analyse du Besoin & Étude d'Impact Tech Lead (Pré-Implémentation)

### 1.1 Contexte, Dialogue Sally & Winston & Problématique
- **Dialogue de conception Sally (UX Designer) & Winston (System Architect)** :
  - **🎨 Sally (`bmad-agent-ux-designer`)** : *« Jusqu'ici, pour découvrir pourquoi ORCIA existe, comment le principe **Human-Led** protège l'auteur humain, comment la **Double Barrière Déterministe + Probabiliste** bloque l'effet boule de neige des hallucinations, et à quoi servent chacun des 9 écrans, il fallait parcourir des dizaines de documents Markdown. Pire : mélanger sur une même page la vision métier destinée aux décideurs/utilisateurs et la plomberie technique (`PostgreSQL 18`, `DBOS`, `Starlark`, `pgvector`) brouille la lecture. Nous devons construire une vitrine interactive claire avec **étanchéité éditoriale absolue** : les Espaces 1 (`Vision & Pilotage Humain`) et 2 (`Fonctionnalités & Écrans`) parlent exclusivement le langage humain et métier (zéro nom de base de données, de framework ou de moteur interne), tandis que l'Espace 3 (`Architecture & Choix Techniques`) ouvre le capot pour les architectes et ingénieurs en détaillant chaque mécanisme technique ! Et depuis l'écran `❓ Aide` ou la barre supérieure, un bouton 1-clic (`open-orcia-showcase-site-btn`) amène directement sur `/showcase`. »*
  - **🏗️ Winston (`bmad-agent-architect`)** : *« Et pour que ce site ne devienne jamais obsolète au fil des futures évolutions d'ORCIA, il ne doit pas reposer sur des chiffres figés à la main. Nous allons créer le générateur déterministe `infra/scripts/sync_site_catalog.py` (`pnpm site:sync` / `pnpm site:check`) qui introspecte en direct le dépôt (`ARCHITECTURE-SPINE.md`, `apps/web/src/routes/*.tsx`, `packages/ui/src/index.ts`, `packages/orcia-pack-*/pyproject.toml`, `infra/migrations/versions/*.py` et le tableau complet de `docs/implementation-artifacts/tech-lead-reports/README.md`). Il génère à la fois le manifeste TypeScript `apps/web/src/generated/orciaSiteManifest.ts` consommé par `/showcase` et le site HTML5 monopage 100 % autonome `docs/site-catalog/index.html` (ainsi que `dist/orcia-site/index.html`). Côté `@orcia/ui`, le composant `OrciaProductShowcaseSiteView.tsx` respectera les 4 invariants d'or (`design-system-look-and-feel-isolation.test.tsx`) : zéro import externe, zéro couleur hexadécimale en dur hors `tokens.css`, exclusivité de `--color-human-led-violet` préservée pour `HumanLedAnchorCard.tsx`, et attributs anti-LastPass complets sur le champ de filtre. »*

### 1.2 Exploration, Analyse d'Impact GitNexus, Factorisation & Dette Technique
- **Analyse d'Impact GitNexus (`gitnexus_impact` sur `/home/romain/Documents/Projects/ORCIA`)** :
  - `resolveModuleFromPathname` (`apps/web/src/components/shellPresets.ts`) : risque `LOW`, appelé par `ShellContainer.tsx` et `i18n-and-shell.test.tsx`. L'ajout de la résolution `/showcase` $\rightarrow$ `"ontology"` (et `"help"` dans `resolveEightMenuKeyFromModule`) garantit que la coquille 4 zones met en surbrillance l'entrée `❓ Aide` lorsqu'on visite `/showcase`.
  - `createOrciaRouter` (`apps/web/src/router.tsx`) : risque `LOW` (`impactedCount: 2`, appelé par `OrciaSpaApp` dans `main.tsx` et par les tests d'intégration Vitest). L'enregistrement de `showcaseRoute` (`/showcase`) étend l'arbre de routes sans impacter les routes existantes.
  - `OntologyFeaturePanel` (`apps/web/src/features/ontology/index.tsx`) : risque `LOW`, monté par `ModuleWorkspaceView` lorsque `moduleKey === "ontology"` (`/help` et `/ontology`). Nous y ajoutons une bannière d'accès en 1 clic (`data-testid="open-orcia-showcase-site-btn"`) vers `/showcase`, également accessible depuis `FourZoneDirectionCShell.tsx` / `ShellContainer.tsx`.
- **Contrôle de volumétrie & Invariants `@orcia/ui`** :
  - `apps/web/src/__tests__/i18n-and-shell.test.tsx` dépasse `1 400` lignes : pour éviter d'alourdir davantage ce fichier, nous créons une suite dédiée `apps/web/src/__tests__/orcia-showcase-site.test.tsx` côté Vitest et `tests/unit/test_site_catalog_sync.py` côté Pytest, tout en gardant un test de liaison dans `i18n-and-shell.test.tsx`.
  - Attention critique à l'Invariant 2 de `design-system-look-and-feel-isolation.test.tsx` :
    1. Aucun code hexadécimal (`#[0-9a-fA-F]{3,8}`) ne doit apparaître dans un fichier `.ts` ou `.tsx` de `packages/ui/src` ou `apps/web/src` (y compris dans `orciaSiteManifest.ts` et dans les textes descriptifs : écrire « identité visuelle Violette » sans littéral hexadécimal dans les `.ts`/`.tsx`).
    2. La sous-chaîne `--color-human-led-violet` est strictement réservée au fichier `HumanLedAnchorCard.tsx` : `OrciaProductShowcaseSiteView.tsx` utilisera `--color-human-led-bg` et `--color-primary-dark` / `--color-action-primary` pour ses encadrés.

---

## 2. Plan d'Implémentation

### 2.1 Schéma de Données & Migrations Alembic (`infra/migrations/versions/...`)
- Aucune nouvelle migration Alembic requise : le site de présentation et son manifeste sont générés statiquement par introspection déterministe des migrations existantes (`0001` à `0027`) et des artefacts du dépôt.

### 2.2 Générateur & Exporteur Statique (`infra/scripts/sync_site_catalog.py` & `package.json`)
- Création de `infra/scripts/sync_site_catalog.py` exécutable via `.venv/bin/python infra/scripts/sync_site_catalog.py` (`pnpm site:sync`) et `.venv/bin/python infra/scripts/sync_site_catalog.py --check` (`pnpm site:check`) :
  - Introspecte de manière déterministe :
    1. `ARCHITECTURE-SPINE.md` (table `## Stack` + décisions `### AD-*`),
    2. `apps/web/src/routes/*.tsx` et `apps/web/src/router.tsx` (routes déclarées),
    3. `packages/ui/src/index.ts` (composants exportés par `@orcia/ui`),
    4. `packages/orcia-pack-*/pyproject.toml` (Packs Métiers installés),
    5. `infra/migrations/versions/*.py` (migrations Alembic versionnées),
    6. `docs/implementation-artifacts/tech-lead-reports/README.md` (parsing complet du tableau Markdown des Rapports Tech Lead : date, story/phase, fichier, domaine, résumé).
  - Génère :
    1. `apps/web/src/generated/orciaSiteManifest.ts` (zéro littéral hexadécimal `#...` pour respecter l'Invariant 2 du test d'isolation Design System),
    2. `docs/site-catalog/index.html` (versionné dans Git) et `dist/orcia-site/index.html` : site HTML5/CSS/JS monopage 100 % autonome incluant les variables CSS Direction C, le sélecteur d'onglets interactif (Espaces 1, 2, 3, 4), la recherche instantanée et la bascule Clair/Sombre.
- Mise à jour de `package.json` (`site:sync`, `site:check`), `GEMINI.md` et `CLAUDE.md`.

### 2.3 Design System `@orcia/ui` (`packages/ui/src/primitives/OrciaProductShowcaseSiteView.tsx`)
- Création de la primitive pure `OrciaProductShowcaseSiteView` exportée dans `packages/ui/src/index.ts` :
  - **4 onglets strictement séparés** :
    - `data-testid="showcase-tab-macro"` $\rightarrow$ `data-testid="showcase-pillar-macro"` (*1. Vision & Pilotage Humain*) : Pourquoi ORCIA, Principe Fondateur Human-Led (Ancrages Humains, Anti-Validation Fantôme en 4 blocs, Arbitrage Humain systématique, Aucune modification sauvage), Double Barrière Anti-Hallucination & Anti-Propagation d'Erreurs (Effet boule de neige, Barrière n°1 Déterministe 100 % / 0 $, Barrière n°2 Probabiliste Croisée multi-familles à 5 angles, Barrière n°3 Remise en Cause Amont & Recalcul ciblé), Gouvernance par l'Organisation Réelle & Packs Métiers. **Zéro terme technique d'implémentation**.
    - `data-testid="showcase-tab-features"` $\rightarrow$ `data-testid="showcase-pillar-features"` (*2. Fonctionnalités & Écrans*) : Volet A (les 6 Dispositifs Concrets du Pilotage Humain et de la Fiabilité) + Volet B (les 9 Écrans du Menu d'ORCIA expliqués un par un avec bouton d'accès direct `onNavigateToRoute`). **Zéro terme technique d'implémentation SQL/Python/React**.
    - `data-testid="showcase-tab-architecture"` $\rightarrow$ `data-testid="showcase-pillar-architecture"` (*3. Architecture & Choix Techniques — Sous le Capot*) : 3.1 Monolithe Modulaire Hybride (`TypeScript` / `Python 3.12+`, `orcia-kernel`, `orcia-core`, `apps/api`, `apps/worker`, `lint-imports`), 3.2 Implémentation Technique des Garanties Human-Led (`SHA-256`, `human_anchor_signatures`, `AdaptiveHumanGateService`, `chunk_approvals`, Redis `SET lock:step:<id> NX EX 900`, `ExternalEditRebaser`), 3.3 Mécanismes Déterministes (`WorkflowYamlValidator`, `SubprocessTier1SandboxAdapter`, `Wasmtime`, `StarlarkMechanismSandbox` $O(n)$, `BimodalSandboxAdapter`, `AssistantCitationAndV5GuardService`), 3.4 Mécanismes Probabilistes Gouvernés (`AgenticGateService`, `CognitiveRouterService`, `PostgreSQL 18`, `pgvector` `halfvec(1024)`, `ts_rank_cd`, `RRF (k=60)`, `DBOS Transact`, `blackboard_snapshots`, `UpstreamChallengeAndReplayService`), 3.5 Sécurité, Cryptographie & Design System (`OIDC PKCE`, `Argon2id`, `EnvelopeVaultSecretProvider`, `PiiReversibleScrubber`, `@orcia/ui` `tokens.css`, `@orcia/api-client` OpenAPI 3.1 `0-diff`).
    - `data-testid="showcase-tab-changelog"` $\rightarrow$ `data-testid="showcase-pillar-changelog"` (*4. 🔄 Historique des Évolutions & Statistiques Vivantes*) : compteurs temps réel du dépôt, composants de la stack `ARCHITECTURE-SPINE.md`, filtre de recherche (avec attributs anti-LastPass complets) et chronologie complète des Rapports Tech Lead.

### 2.4 Route `/showcase`, Accès 1-Clic & Tests (`apps/web/src/routes/showcase.tsx`, `router.tsx`, `OntologyFeaturePanel.tsx`)
- Création de `apps/web/src/routes/showcase.tsx` assemblant `OrciaProductShowcaseSiteView` avec `ORCIA_SITE_MANIFEST` (`apps/web/src/generated/orciaSiteManifest.ts`) et la navigation `useShellNavigation()`.
- Enregistrement de `/showcase` dans `apps/web/src/router.tsx` et `apps/web/src/components/shellPresets.ts`.
- Ajout du bouton d'accès 1-clic `data-testid="open-orcia-showcase-site-btn"` dans `apps/web/src/features/ontology/index.tsx` (écran `❓ Aide`) et dans la barre supérieure de `FourZoneDirectionCShell.tsx`.
- Création des suites de tests `apps/web/src/__tests__/orcia-showcase-site.test.tsx` et `tests/unit/test_site_catalog_sync.py`.

---

## 3. Bilan des Modifications & Résultats (Post-Implémentation)

### 3.1 Fichiers Créés ou Modifiés

| Fichier | Nature | Rôle & Justification |
| :--- | :--- | :--- |
| `infra/scripts/sync_site_catalog.py` | Créé (`841` lignes) | Générateur déterministe sans dépendance externe (`pnpm site:sync` / `pnpm site:check`) : introspecte `ARCHITECTURE-SPINE.md`, `apps/web/src/routes/*.tsx`, `packages/ui/src/index.ts`, `packages/orcia-pack-*/pyproject.toml`, `infra/migrations/versions/*.py` et `docs/implementation-artifacts/tech-lead-reports/README.md`, puis génère `apps/web/src/generated/orciaSiteManifest.ts`, `docs/site-catalog/index.html` et `dist/orcia-site/index.html`. |
| `packages/ui/src/primitives/OrciaProductShowcaseSiteView.tsx` | Créé (`1 384` lignes) | Primitive pure `@orcia/ui` (Direction C) implémentant les 4 espaces strictement séparés (`showcase-pillar-macro`, `showcase-pillar-features`, `showcase-pillar-architecture`, `showcase-pillar-changelog`), conforme aux 4 invariants d'or (`design-system-look-and-feel-isolation.test.tsx`). |
| `packages/ui/src/index.ts` | Modifié | Export public de `OrciaProductShowcaseSiteView` et des types `OrciaShowcaseManifestData`, `OrciaProductShowcaseSiteViewProps`, `OrciaShowcasePillarKey`. |
| `apps/web/src/generated/orciaSiteManifest.ts` | Créé (généré) | Manifeste TypeScript généré par `pnpm site:sync` (`20` routes actives, `66` primitives `@orcia/ui`, `2` packs métiers, `27` migrations Alembic, `21` décisions AD, `40` composants de stack, `71` rapports Tech Lead). |
| `docs/site-catalog/index.html` & `dist/orcia-site/index.html` | Créés (générés) | Site web HTML5/CSS/JS monopage 100 % autonome (consultable via `file://` sans serveur) avec bascule Clair/Sombre, navigation par onglets entre les 4 espaces et recherche instantanée dans l'historique des évolutions. |
| `apps/web/src/routes/showcase.tsx` | Créé (`63` lignes) | Route TanStack Router `/showcase` connectant `OrciaProductShowcaseSiteView` à `ORCIA_SITE_MANIFEST`, `useShellNavigation()` et `useOrciaI18n()`. |
| `apps/web/src/router.tsx` & `apps/web/src/components/shellPresets.ts` | Modifiés | Enregistrement de `/showcase` dans l'arbre TanStack Router et résolution de `/showcase` vers le module `"ontology"` (`❓ Aide`). |
| `apps/web/src/features/ontology/index.tsx` & `apps/web/src/components/ShellContainer.tsx` | Modifiés | Ajout du bouton d'accès en 1 clic `data-testid="open-orcia-showcase-site-btn"` sur l'écran `❓ Aide` (`/help`) et dans la barre latérale du shell Direction C. |
| `apps/web/tsconfig.json` & `apps/web/vitest.config.ts` | Modifiés | Résolution directe vers `../../packages/ui/src/index.ts` et `../../packages/api-client/src/index.ts` pour garantir la compilation et les tests dans les worktrees isolés. |
| `package.json`, `GEMINI.md` & `CLAUDE.md` | Modifiés | Ajout des scripts `pnpm site:sync` et `pnpm site:check` et inscription de la règle d'auto-actualisation obligatoire dans les règles permanentes du projet. |
| `apps/web/src/__tests__/orcia-showcase-site.test.tsx` | Créé (`164` lignes) | Suite Vitest dédiée validant la navigation 1-clic `/help` $\rightarrow$ `/showcase`, l'étanchéité éditoriale stricte entre les Espaces 1/2 (zéro terme d'implémentation) et l'Espace 3 (tous les mécanismes techniques), ainsi que la recherche dans l'Espace 4. |
| `tests/unit/test_site_catalog_sync.py` | Créé (`95` lignes) | Suite Pytest validant l'introspection déterministe de `sync_site_catalog.py`, le mode `--check` (`exit 0`) et la parité structurelle + étanchéité éditoriale de `docs/site-catalog/index.html`. |

### 3.2 Validation des Portes de Qualité (`AD-17` & Invariants `@orcia/ui`)

1. **Synchronisation & Parité du Site (`pnpm site:sync` & `pnpm site:check`)** :
   - `.venv/bin/python infra/scripts/sync_site_catalog.py && .venv/bin/python infra/scripts/sync_site_catalog.py --check` $\rightarrow$ **`[site:check OK] Manifest (71 reports, 20 routes, 66 UI primitives) is in sync`** (`exit 0`).
2. **Tests Unitaires Python & Qualité Statique (`pytest`, `ruff`, `mypy`, `lint-imports`, `lint_spine.py`)** :
   - `.venv/bin/pytest tests/unit/test_site_catalog_sync.py -q` $\rightarrow$ **`3 passed`**.
   - `.venv/bin/ruff check . && .venv/bin/ruff format --check .` $\rightarrow$ **`All checks passed! 524 files already formatted`**.
   - `.venv/bin/mypy --strict packages/orcia-kernel packages/orcia-core apps/api apps/worker` $\rightarrow$ **`Success: no issues found in 209 source files`**.
   - `.venv/bin/lint-imports` $\rightarrow$ **`5 kept, 0 broken`**.
   - `.venv/bin/python .agent/skills/bmad-architecture/scripts/lint_spine.py --workspace docs/planning-artifacts/architecture/architecture-ORCIA-2026-10-24` $\rightarrow$ **`"ok": true, "total_findings": 0`**.
3. **Suite TypeScript / Vitest & Isolation Design System (`pnpm turbo run lint typecheck test --force`)** :
   - `9/9 tasks successful` (`@orcia/ui`, `@orcia/api-client`, `@orcia/web`).
   - `Test Files: 3 passed (3)` / `Tests: 28 passed (28)` incluant :
     - `design-system-look-and-feel-isolation.test.tsx` (`4/4` invariants d'or validés),
     - `orcia-showcase-site.test.tsx` (`2/2` tests d'étanchéité éditoriale et de navigation `/showcase` validés),
     - `i18n-and-shell.test.tsx` (`22/22` tests d'intégration shell et survie au `F5` validés).

