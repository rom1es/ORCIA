# Rapport Tech Lead — Story 24.5 : Identité Accostage Cockpit, Synchronisation Navigation Zone 4 & Cohérence Jour 0

- **Story :** `24-5-identite-accostage-cockpit-sync-navigation-zone4-et-coherence-jour0` (Epic 24 — Vague 1 `P1/P2`)
- **Date :** 2026-11-20
- **Statut :** `Terminé (`done`)`
- **Plan directeur :** [`sprint-change-proposal-2026-11-20-epic-24-remediation-plan.md`](../../planning-artifacts/sprint-change-proposal-2026-11-20-epic-24-remediation-plan.md)
- **Références remédiées :** `REM24-08`, **`USER24-BUG-2`** | Constats `UX23-07` (`P1`), `UX23-09` (`P1`), `UX23-15` (`P2`) | Diagnostic `ARCH24-09`
- **Capacité(s) (`capabilities.yaml`) :** `CAP-050`, `CAP-067` (`2` capacités Desktop `failed_e2e` — plus protection de non-régression sur `CAP-005`, `CAP-060`, `CAP-061`, `CAP-064`, `CAP-068` déjà `runtime`)
- **Classification :** `ux` (identité cockpit Jour 0, routage Zone 4, fil d'Ariane & verrouillage pré-admin)

---

## 1. Analyse du Besoin & Étude d'Impact Tech Lead

### 1.1 Contexte & Critères d'Acceptation
Plusieurs défauts d'orientation utilisateur et d'incohérence Jour 0 (`P1`/`P2`) persistent dans la coquille Direction C et les garde-fous d'amorçage :
1. **Identité `platformAdmin` fausse dans Accostage (`UX23-07`)** : `apps/web/src/features/cockpit/index.tsx:207-209` passe `authDisplayName` comme `platformAdmin` à `ProgressiveDay0AccostageService` / composant d'accostage, attribuant le rôle d'administrateur plateforme à tout utilisateur non-admin. De plus, les jalons d'accostage affichés ne sont pas filtrés selon les permissions effectives du rôle.
2. **Navigation, Zone 4 & fil d'Ariane désynchronisés (`UX23-09`, `ARCH24-09`)** :
   - `/inbox` ne dispose pas d'entrée dédiée dans `_contextualHelpSections.ts:242` (`docs/help/{fr,en}/inbox.md` absents), ce qui empêche la Zone 4 de refléter fidèlement la route.
   - `/showcase` ne met pas `help` en surbrillance dans la barre latérale (`shellPresets.ts` `310` L).
   - `/organization` dépend d'un parent masqué `Configuration` dans le fil d'Ariane, et `[Espace]` n'est pas injecté dynamiquement dans `buildShellBreadcrumbItems` ; le fil d'Ariane `/spaces` est dupliqué avec un pied de page pack actif redondant ; `/settings` déborde ses `6` onglets sur deux lignes.
3. **Cohérence Jour 0 & modale admin (`UX23-15`, `ARCH24-09`)** : `Mes Espaces` n'est pas verrouillé uniformément au Jour 0 tant que l'administrateur initial n'a pas été configuré, et `FirstBootAdminSetupModal.tsx` (`262` L) ne rend pas suffisamment explicite le caractère non fermable / bloquant du premier amorçage.

4. **Lien cassé sur jalon « 1. Compte Admin » (`USER24-BUG-2`)** : dans `packages/orcia-core/src/orcia_core/bootstrap/progressive_accostage.py:55-61` et `apps/web/src/components/platformSetupAccostage.ts:91-97`, le jalon `first-admin` (`1. Compte Admin`) pointe sur `"/welcome-setup"`, une route inexistante dans `apps/web/src/router.tsx`, provoquant l'affichage de `Not Found` au clic depuis le Cockpit. Il faut corriger cette cible vers `"/profile"` post-admin (`"/cockpit"` au Jour 0 pré-admin) et vérifier que chacun des 6 jalons pointe vers une route réelle de `router.tsx`.

**Critères d'acceptation :** affichage exact de l'administrateur plateforme réel (jamais `authDisplayName` d'un utilisateur standard), filtrage backend + UI des jalons Accostage selon les permissions, navigation valide sans `Not Found` au clic sur `1. Compte Admin` et les 6 jalons (`USER24-BUG-2`), aide Zone 4 dédiée pour `/inbox` (`fr`/`en`), fil d'Ariane propre sur `/organization`, `/spaces` et `[Espace]`, `6` onglets `/settings` sur `1` ligne, et verrouillage uniforme `Mes Espaces` pré-admin.

### 1.2 Analyse d'Impact GitNexus (`repo: "/home/romain/Documents/Projects/ORCIA"`)
- `ProgressiveDay0AccostageService` (`packages/orcia-core/src/orcia_core/bootstrap/progressive_accostage.py`) : `impactedCount: 261`, `risk: "CRITICAL"`, `epistemic: "exact"` (`direct: 242`, `d=2: 19`, `processes_affected: 32`, `modules_affected: 20`).
- `ContextualHelpResolutionService` (`packages/orcia-core/src/orcia_core/catalog/contextual_help.py:74`) : `ambiguous` (`totalCandidates: 4`, `maxImpactedCount: 261`, `maxRisk: "CRITICAL"`, `direct: 242`).
- Inspection directe : `apps/web/src/components/shellPresets.ts` (`310` L), `apps/web/src/components/_contextualHelpSections.ts` (`272` L), `apps/web/src/components/ShellContainer.tsx` (`378` L), `apps/web/src/features/cockpit/index.tsx` (`272` L) et `FirstBootAdminSetupModal.tsx` (`262` L).

### 1.3 Opportunités de Factorisation & Contrôle de Volumétrie (`< 350` L)
- **Découpage obligatoire `ShellContainer.tsx` (`378` L > `350` L)** : extraire la construction du fil d'Ariane (`buildShellBreadcrumbItems` + contexte `[Espace]`) et le câblage de Zone 4 dans des modules/hooks dédiés sous `apps/web/src/components/` afin de descendre `ShellContainer.tsx` sous `< 280` L.
- **Unification des slugs d'aide Zone 4** : aligner `_contextualHelpSections.ts` avec `ContextualHelpResolutionService` pour garantir un mapping déterministe route $\rightarrow$ `docs/help/{fr,en}/<route>.md`.

---

## 2. Plan d'Implémentation

### 2.1 Couche Données & Migrations Alembic / PostgreSQL 18
- Aucune migration de schéma PG18 nécessaire ; réutilisation des tables d'identité / bootstrap et du catalogue d'articles d'aide existants (`catalog_items`). Vérifier que `ProgressiveDay0AccostageService` relit l'administrateur initial depuis PG18 et que les nouveaux articles `docs/help/{fr,en}/inbox.md` sont indexés proprement au seed/sync.

### 2.2 Noyau Hexagonal (`orcia-kernel` / `orcia-core`) & Workers
1. Étendre `ProgressiveDay0AccostageService` (`progressive_accostage.py`) afin de retourner distinctement l'identité réelle du `platform_admin` configuré (et non l'utilisateur courant par défaut) ainsi que la liste des jalons autorisés selon les permissions du rôle courant.
2. Enregistrer la route `/inbox` dans `ContextualHelpResolutionService` (`contextual_help.py`) et créer `docs/help/fr/inbox.md` + `docs/help/en/inbox.md` conformes aux 4 blocs `DESIGN.md`.

### 2.3 Backend FastAPI (`apps/api`) & Contrat OpenAPI (`packages/api-client`)
1. Vérifier les champs de réponse du statut d'accostage et d'aide contextuelle (`platform_admin_display_name`, `visible_milestones`, `inbox` help key) dans `apps/api/src/orcia_api/schemas/` et `portal_and_help.py`.
2. Régénérer `@orcia/api-client` (`0-diff`) si de nouveaux champs typés sont ajoutés à la réponse Accostage.

### 2.4 Interface SPA Vite + TanStack Router & Design System (`@orcia/ui` / `apps/web`)
1. Corriger `progressive_accostage.py:55-61`, `platformSetupAccostage.ts:91-97` et `apps/web/src/features/cockpit/index.tsx:207-209` : remplacer la route inexistante `"/welcome-setup"` de `1. Compte Admin` par `"/profile"` post-admin (`"/cockpit"` au Jour 0 pré-admin) et valider que les `6` jalons correspondent tous à des routes de `router.tsx` (`USER24-BUG-2`), transmettre `platformAdmin` issu de l'API (jamais `authDisplayName`), et masquer/filtrer les jalons d'accostage incompatibles avec le rôle connecté (`UX23-07`).
2. Ajouter l'entrée dédiée `/inbox` dans `apps/web/src/components/_contextualHelpSections.ts:242`, mettre `help` en surbrillance dans `shellPresets.ts` (`310` L) sur `/showcase`, détacher `/organization` du parent caché `Configuration`, injecter `[Espace]` dans `buildShellBreadcrumbItems` et supprimer le breadcrumb dupliqué sur `/spaces` ainsi que le pied pack actif dupliqué (`UX23-09`, `UX23-15`).
3. Uniformiser la barre d'onglets `/settings` pour afficher ses `6` onglets sur `1` seule ligne en `1440×900`, verrouiller `Mes Espaces` de façon cohérente avant création de l'admin Jour 0, et expliciter le statut obligatoire non fermable de `FirstBootAdminSetupModal.tsx` (`262` L).
4. Découper `ShellContainer.tsx` (`378` L $\rightarrow$ `< 280` L).

### 2.5 Stratégie de Vérification & 5 Couches de Tests (`AD-17`)
- **Couche 1 (Unitaire >= 90 %)** : tests `ProgressiveDay0AccostageService` (rôle non-admin ne reçoit jamais son propre nom en `platform_admin` et jalons filtrés par permissions) + résolution `/inbox` dans `ContextualHelpResolutionService`.
- **Couche 2 (Intégration `testcontainers` PG18 réel)** : vérification endpoint d'accostage avec utilisateur standard vs `platform_admin` et résolution `GET` aide contextuelle `/inbox` (`fr`/`en`).
- **Couche 3 (Composants React / Vitest)** : tests `ShellContainer` / `shellPresets` / `buildShellBreadcrumbItems` (`/organization`, `/spaces` sans doublon, `/showcase` surbrillance `help`, `[Espace]`, `/settings` 6 onglets), test Vitest validant que les 6 jalons `buildUnifiedAccostageMilestones` pointent vers des routes existantes dans `router.tsx` (`USER24-BUG-2`), `FirstBootAdminSetupModal` et verrouillage `Mes Espaces` pré-admin.
- **Couche 4 (E2E Playwright ciblé)** : `00-smoke`, `01` (clic explicite sur `1. Compte Admin` sans `Not Found` `USER24-BUG-2`), `02` (Jour 0), `04` (Accostage), `07-spaces-org-and-workspace-persistence.spec.ts` (en coordination avec `24-7`) et `/inbox` Zone 4.
- **Couche 5 (Statique & Sécurité)** : `ruff`, `mypy --strict`, `lint-imports`, `pnpm turbo run lint typecheck test`, `pnpm site:check`.

---

## 3. Bilan des Modifications & Résultats

> **Statut :** `Terminé (`done`)` — Validée sur les 5 couches `AD-17` avec re-indexation GitNexus (`npx gitnexus analyze` + `gitnexus_detect_changes`), suite Vitest complète, intégration PG18/Redis `testcontainers`, Playwright Desktop (`--retries=0`) et synchronisation `pnpm site:sync && pnpm site:check`.

### 3.1 Tableau synthétique des fichiers développés et modifiés

| Fichier / Composant | Modification réalisée | Statut |
|---|---|---|
| `packages/orcia-core/src/orcia_core/bootstrap/{progressive_accostage.py,__init__.py,_internal/sql_first_user_guard.py}` | Remplacement `"/welcome-setup"` $\rightarrow$ `"/profile"` sur `first-admin` (`ACCOSTAGE_SIX_MILESTONES`, `USER24-BUG-2`), ajout `AccostageVisibleMilestone` & `is_accostage_milestone_accessible`, exposition `platform_admin_display_name` & `visible_milestones` filtrés par rôle, filtre strict `AND platform_role = 'PLATFORM_ADMIN'` dans `get_first_platform_admin_from_postgres18` | `Terminé` |
| `apps/api/src/orcia_api/{schemas/bootstrap.py,routers/bootstrap_accostage.py}` & `packages/api-client/` | Ajout `AccostageMilestoneItem`, `platform_admin_display_name` et `visible_milestones` sur `AccostageStatusResponse`, résolution optionnelle `_resolve_optional_caller_role`, régénération OpenAPI (`0-diff`) & client TypeScript | `Terminé` |
| `packages/orcia-core/src/orcia_core/catalog/{contextual_help.py,contextual_help_resolver.py}` & `docs/help/{fr,en}/{inbox,assistant}.md` | Fiches dédiées `/inbox` (`help-base-inbox-{fr,en}` conformes 4 blocs `DESIGN.md`), retrait de `- /inbox` dans `docs/help/{fr,en}/assistant.md`, priorité stricte `/inbox` $\rightarrow$ `help-base-inbox-*` (exclusion `help-base-assistant-*`) | `Terminé` |
| `apps/web/src/components/{_contextualHelpSections.ts,_contextualHelpSectionsEn.ts,contextualHelpCatalog.ts}` | Mapping autonome `/inbox` FR/EN dans `SECTIONS_BY_ROUTE_{FR,EN}`, `normalizeCanonicalHelpRoute` et `contextualHelpCatalog.ts` | `Terminé` |
| `apps/web/src/components/{platformSetupHydration.ts,platformSetupAccostage.ts}`, `packages/ui/src/primitives/ProgressiveDay0AccostageBanner.tsx` & `apps/web/src/features/cockpit/index.tsx` | Route cible `first-admin` $\rightarrow$ `summary.adminCreated ? "/profile" : "/cockpit"`, filtrage UI des jalons selon `roles`, `readOnlyObserver` et `visibleMilestoneKeys`, ajout `canConfigurePlatform` (masque Étape 2 pour non-admins), transmission stricte du `platformAdmin` réel (`accostageCounts?.platformAdminDisplayName ?? platformAdmin?.displayName ?? null`, jamais `authDisplayName`) | `Terminé` |
| `apps/web/src/components/{ShellContainer.tsx,shellPresets.ts,shellBreadcrumbBuilders.ts,shellBreadcrumbAndScope.ts,ShellSidebarFooter.tsx,shellZone4HelpWiring.tsx}` | Découpage `ShellContainer.tsx` (`378` L $\rightarrow$ `269` L) via `shellBreadcrumbBuilders.ts` (`179` L), `shellBreadcrumbAndScope.ts` (`199` L), `shellZone4HelpWiring.tsx` (`106` L) et `ShellSidebarFooter.tsx` (`89` L) ; `/showcase` active `help`, `/organization` détaché si `Configuration` masquée, injection `[Espace]` sur routes scopées, Zone 4 `/inbox` dédiée | `Terminé` |
| `apps/web/src/features/workspaces/WorkspaceStudioCardsAndDetailView.tsx`, `apps/web/src/routes/{SettingsPacksSection.tsx,settings.tsx}`, `FirstBootAdminSetupModal.tsx`, `FourZoneSidebarRail.tsx`, `tokens-shell.css` | Suppression breadcrumb dupliqué `workspace-sources-breadcrumb` et pied `pack-row-*` ; `6` boutons `/settings` en `flexWrap: "nowrap"` sur `1` ligne ; `FirstBootAdminSetupModal` sans bouton `Fermer` (`hideHeaderCloseButton={true}`) + `first-boot-admin-mandatory-badge` ; verrouillage uniforme `Mes Espaces` & entrées désactivées au Jour 0 | `Terminé` |
| Suites QA 5 couches (`tests/unit/test_story_24_5_accostage_and_inbox_help.py`, `tests/integration/test_story_24_5_accostage_and_inbox_help_postgres18.py`, `apps/web/src/__tests__/story-24-5-accostage-routes-navigation-and-day0.test.tsx`, `day0-modal-*`, `story-18-1-*`, `i18n-and-shell.test.tsx`, `four-zone-shell-and-cockpit.test.tsx`, `apps/web/e2e/{01,15,21,shell}.spec.ts`) | Vérification contrat 6 jalons vs `router.tsx` (`USER24-BUG-2`), identité `platformAdmin` & filtrage permissions par rôle (`PLATFORM_ADMIN`, `BU_LEAD`, `TEAM_LEAD`, `CONTRIBUTOR`, `SECOPS`, `READ_ONLY_OBSERVER`), résolution `/inbox` PG18, navigation `/showcase`, `/organization`, `[Espace]`, `/settings` 1 ligne, et verrouillage Jour 0 | `Terminé` |

### 3.2 Résultats chiffrés, couverture & validation 5 couches (`AD-17`)

- **Couches 1a & 2 (Python unitaire + intégration PG18/Redis `testcontainers` sur `create_app()` sans `dependency_overrides`)** :
  - `.venv/bin/pytest -o addopts="" --import-mode=importlib tests/unit/test_story_24_5_accostage_and_inbox_help.py tests/unit/test_epic_9_story_9_2_accostage_and_first_user.py tests/unit/test_contextual_help_route_resolution.py tests/unit/test_epic_9_story_9_5_contextual_help.py tests/unit/test_gemini_argon_provider_adapter.py tests/integration/test_story_24_5_accostage_and_inbox_help_postgres18.py tests/integration/test_contextual_help_and_accostage_postgres18.py --cov=orcia_core.bootstrap.progressive_accostage --cov=orcia_core.bootstrap._internal.sql_first_user_guard --cov=orcia_core.catalog.contextual_help --cov=orcia_core.catalog.contextual_help_resolver --cov=orcia_api.routers.bootstrap_accostage --cov-report=term-missing --cov-fail-under=90` $\rightarrow$ **`82 passed`**, couverture combinée **`91.17 %`** (`progressive_accostage.py` `99 %`, `sql_first_user_guard.py` `98 %`, `contextual_help_resolver.py` `98 %`, `contextual_help.py` `95 %`, `bootstrap_accostage.py` `78 %`).
  - Relance unitaire post-annotations secrets : `.venv/bin/pytest tests/unit/test_story_24_5_accostage_and_inbox_help.py -q` $\rightarrow$ **`14 passed`**.
- **Statique Python, Architecture & Sécurité** :
  - `.venv/bin/ruff check .` : **PASS** (`All checks passed!`) ; `.venv/bin/ruff format --check .` : **PASS** (`1313 files already formatted`).
  - `.venv/bin/mypy --strict packages/orcia-core packages/orcia-connectors apps/api apps/worker` : **PASS** (`Success: no issues found in 574 source files`).
  - `.venv/bin/lint-imports` : **PASS** (`Contracts: 5 kept, 0 broken`, `617 files`).
  - `.venv/bin/python scripts/export_openapi.py --check` : **PASS** (`0-diff`).
  - `.venv/bin/pre-commit run detect-secrets --files ...` (tous les fichiers Story 24.5) : **Passed**.
- **Couche 1b (Vitest & TypeScript Monorepo)** :
  - `pnpm turbo run lint typecheck test` : **PASS (`9 successful, 9 total`)** — `@orcia/api-client`: `3 files / 20 tests` ; `@orcia/ui`: `33 files / 131 tests` ; `@orcia/web`: `60 files / 237 tests` (dont `story-24-5-accostage-routes-navigation-and-day0.test.tsx`, `e2e-testids-sync-audit.test.ts` et les 4 suites ajustées).
- **Couche 5 (Playwright E2E réel `--project=desktop-cockpit --retries=0`, `ORCIA_E2E_CAMPAIGN_DIR=/tmp/orcia-e2e-story-24-5`)** :
  - `pnpm --filter @orcia/web exec playwright test shell.spec.ts 00-stack-smoke.spec.ts 01-day0-boot-and-f5-persistence.spec.ts 02-assistant-streaming-and-folders.spec.ts 04-multi-actor-claim-sse.spec.ts 15-organization-iam-secops-inbox-and-observer.spec.ts 21-assistant-citations-v5-audit-help-showcase.spec.ts --project=desktop-cockpit --retries=0` $\rightarrow$ **`21 passed` (`0 failed`, `4.0m`)** — inclut clic réel sur `accostage-milestone-first-admin` vers `/profile` (`USER24-BUG-2`), `Mes Espaces` verrouillé au Jour 0, modale admin non fermable, `/inbox` Zone 4 dédiée, `/showcase` $\rightarrow$ `eight-menu-item-help` actif et 6 onglets `/settings` sur 1 ligne.
- **GitNexus & Documentation / Gouvernance** :
  - `npx gitnexus analyze` : `41,172 nodes | 186,753 edges | 704 clusters | 1492 flows`.
  - `gitnexus_detect_changes(repo: "/home/romain/Documents/Projects/ORCIA", scope: "all")` : `changed_count: 20`, `changed_files: 37`, `affected_count: 1492`, `risk_level: "critical"`.
  - `scripts/check_implementation_docs.py`, `lint_spine.py`, `pnpm site:sync && pnpm site:check` et `tests/unit/test_epic23_to_epic24_traceability.py` validés.
