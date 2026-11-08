# 2026-11-08 — Vague P1 : Correctifs `BUG-E2E-05` & `BUG-E2E-06`, Socle Radix UI `@orcia/ui` (`UX-DS-RADIX-01`) et Clôture `CAP-ACT-1`

> **Convention de nommage du fichier (Obligatoire — créé AVANT toute modification de code)** :
> `docs/implementation-artifacts/tech-lead-reports/2026-11-08-bugs-p1-e2e-et-socle-radix-ui-tech-lead-report.md`

- **Date** : 2026-11-08
- **Story / Clé Sprint** : `2026-11-08-bugs-p1-e2e-et-socle-radix-ui` (`Epic 13` — Actions `BUG-E2E-05`, `BUG-E2E-06`, `UX-DS-RADIX-01`, `CAP-ACT-1`)
- **Capacité(s)** : `CAP-032`, `CAP-033`, `CAP-062`, `CAP-066`, `CAP-100` (mises à jour dans `docs/product/capabilities.yaml` avec promotion en `verification: runtime`) — classification : `feature | ux | hygiène`
- **Auteur / Contexte** : Traitement sur branche dédiée `fix/p1-bugs-and-radix-ui` de la vague P1 :
  1. `BUG-E2E-05` : Montage de `CognitiveReviewBriefingGrid` (Briefing 4 blocs, Bloc 4 ambre) et `ChunkValidationCard` (Validation par découpage + garde-fou anti-rubber-stamping `< 15 s` sur `> 1 000` mots + exécution des actions Jira staged après Gate) dans `/gates` (`/processes`) avec réhydratation `F5` via `GET /api/v1/gates/human/evaluations` et activation de la spec Playwright `06-gates-review-and-anti-rubber-stamping.spec.ts`.
  2. `BUG-E2E-06` : Correction de la recherche fédérée `⌘K` Vitesse 2 (`GET /api/v1/search`), alignement des portées (`SCREEN | WORKSPACE | ALL_WORKSPACES` + alias `GLOBAL`/`CONTEXTUAL`), suppression de la donnée fictive `localSemanticHit` et du `.catch` silencieux dans `ShellContainer.tsx`, ajout d'une bannière d'erreur explicite dans `TopHeaderSearchCommand`, et retrait de `test.fail` dans `10-command-palette-search.spec.ts`.
  3. `UX-DS-RADIX-01` : Intégration des primitives `@radix-ui/react-tabs`, `@radix-ui/react-dialog`, `@radix-ui/react-select`, `@radix-ui/react-dropdown-menu`, `@radix-ui/react-tooltip` et `@radix-ui/react-switch` dans `@orcia/ui` (`AD-22`), découpage modulaire de `DesignSystemControls.tsx` (`< 300` lignes) et navigation clavier RGAA 4.1 (`ArrowLeft`/`ArrowRight`/`Home`/`End`, roving `tabIndex`, `aria-controls`, `Escape`).
  4. `CAP-ACT-1` : Exposition complète du registre `docs/product/capabilities.yaml` dans le manifeste `/showcase` (`OrciaProductShowcaseSiteView`, `sync_site_catalog.py`) et promotion en `verification: runtime` des capacités validées par la suite E2E Playwright bi-serveur.
- **Commits associés** : _À compléter en Section 3 après validation._

---

## 1. Analyse du Besoin & Étude d'Impact Tech Lead (Pré-Implémentation)

### 1.1 Contexte & Problématique
- **`BUG-E2E-05` (`CAP-032`, `FR-6`, `FR-19`, `AD-11`, `UX-DR4`, `UX-DR5`, `UX-DR10`)** :
  - *Comportement actuel* : Les composants `@orcia/ui` `CognitiveReviewBriefingGrid` et `ChunkValidationCard` ainsi que les endpoints `POST /api/v1/gates/human/*` existent, mais ne sont montés dans aucun écran de `apps/web`, et aucun endpoint `GET /api/v1/gates/human/evaluations` ne permet de réhydrater l'état après un `F5`. La spec `apps/web/e2e/06-gates-review-and-anti-rubber-stamping.spec.ts` est en `test.fixme`.
  - *Comportement attendu* : Monter une section dédiée `GatesAdaptiveHumanReviewSection` dans `/gates` (`/processes`), câblée à `@orcia/api-client` (`listHumanGateEvaluations`, `evaluateHumanGate`, `inspectHumanGateHypotheses`, `decideHumanGateChunk`, `finalizeHumanGate`, `stageJiraWorkflowAction`, `commitStagedJiraAction`), permettant d'inspecter le Bloc 4 (`Hypothèses Retenues`), d'approuver/co-éditer chaque section, de déclencher le garde-fou anti-rubber-stamping (`< 15 s` sur `> 1 000` mots), d'exécuter les actions Jira staged au passage de la Gate et de survivre à un vrai `F5`.
- **`BUG-E2E-06` (`CAP-062`, `FR-32`, `AD-8`, `AD-21`)** :
  - *Comportement actuel* : `ShellContainer.runFederatedSpeed2Search` appelle `client.searchFederated(trimmed, "GLOBAL", workspaces[0]?.workspaceId ?? null, pathname ?? "/spaces")`. Or `GET /api/v1/search` (`portal_and_help.py`) n'accepte que `scope: Literal["SCREEN", "WORKSPACE", "ALL_WORKSPACES"]`, ce qui provoque une erreur `HTTP 422`. De plus, `ShellContainer.tsx` avale l'erreur dans `.catch(() => { setSpeed2Hits([localSemanticHit]); })` et affiche un résultat fictif fabriqué côté client (violation du Garde-Fou n°5 et de la politique zéro donnée fictive).
  - *Comportement attendu* : Aligner les portées entre `ShellContainer`, `@orcia/api-client` et `GET /api/v1/search` (`force_semantic=true` lors du clic sur `cmdk-trigger-speed2-btn`, `workspace_id` optionnel au Jour 0), supprimer `localSemanticHit`, afficher une bannière d'erreur explicite (`cmdk-speed2-error-banner`) si l'API échoue, et retirer `test.fail` dans `10-command-palette-search.spec.ts`.
- **`UX-DS-RADIX-01` (`AD-22`)** :
  - *Comportement actuel* : `packages/ui/package.json` ne déclare pas encore les primitives `@radix-ui/react-*` et `OrciaTabBar` dans `DesignSystemControls.tsx` (329 lignes) utilise de simples `<button role="tab">` sans gestion native du roving `tabIndex` ni navigation clavier `ArrowLeft`/`ArrowRight`/`Home`/`End`.
  - *Comportement attendu* : Installer `@radix-ui/react-tabs`, `@radix-ui/react-dialog`, `@radix-ui/react-select`, `@radix-ui/react-dropdown-menu`, `@radix-ui/react-tooltip` et `@radix-ui/react-switch` dans `packages/ui`, scinder `DesignSystemControls.tsx` (`< 300` lignes) en extrayant `RadixDesignSystemPrimitives.tsx` (`OrciaTabBar`, `OrciaDialog`, `OrciaRadixSelect`, `OrciaDropdownMenu`, `OrciaTooltip`, `OrciaSwitch`), conserver 100 % du stylage dans `tokens.css` (`.orcia-ds-*`) et la parade anti-LastPass par défaut.
- **`CAP-ACT-1` (`CAP-066`)** :
  - *Comportement actuel* : `infra/scripts/sync_site_catalog.py` calcule déjà `capabilitiesCount`, `liveCapabilitiesCount` et `verifiedCapabilitiesCount`, mais `OrciaProductShowcaseSiteView` n'affiche pas encore le compteur ni la synthèse des capacités vérifiées à l'exécution (`verification: runtime`), et seules 4 capacités sur 54 `live` sont marquées `verification: runtime`.
  - *Comportement attendu* : Exposer la synthèse du registre des capacités dans `/showcase` et promouvoir en `verification: runtime` toutes les capacités dont les parcours E2E Playwright (`01` à `11` + `shell.spec.ts`) sont exécutés et verts.

### 1.2 Exploration, Analyse d'Impact GitNexus, Factorisation & Dette Technique
- **Analyse d'Impact GitNexus (`gitnexus_impact`)** :
  - `AdaptiveHumanGateService` (`packages/orcia-core/src/orcia_core/gates/human.py`) : `impactedCount = 11`, `risk = LOW` (`d=1`: `gates/__init__.py`, `gates/deterministic.py`).
  - `execute_two_speed_federated_search` (`apps/api/src/orcia_api/routers/portal_and_help.py`) : `impactedCount = 0` côté Python (`risk = LOW`), appelé via HTTP par `packages/api-client/src/domains/bootstrapAndOntology.ts` (`searchFederated`).
  - `OrciaTabBar` (`packages/ui/src/primitives/DesignSystemControls.tsx`) : `impactedCount = 3`, `risk = LOW` (`d=1`: `OrciaProductShowcaseSiteView`).
  - `CognitiveReviewBriefingGrid` & `ChunkValidationCard` (`packages/ui/src/primitives/`) : `impactedCount = 0` dans `apps/web` (confirme `BUG-E2E-05`).
- **Opportunités de Factorisation & Contrôle de Volumétrie (`< 300–400` lignes)** :
  - `packages/ui/src/primitives/DesignSystemControls.tsx` fait 329 lignes : découpage en `DesignSystemControls.tsx` (`~200` lignes) + `RadixDesignSystemPrimitives.tsx` (`~260` lignes).
  - `apps/web/src/features/gates/index.tsx` fait 303 lignes : extraction de la revue humaine de Gate dans `apps/web/src/features/gates/GatesAdaptiveHumanReviewSection.tsx` (`~280` lignes) pour maintenir chaque fichier sous le seuil de 300–400 lignes.

---

## 2. Plan d'Implémentation

### 2.1 Schéma de Données & Migrations Alembic
- Aucune nouvelle migration Alembic requise (les tables `gate_evaluations`, `chunk_approvals` de la migration `0018` sont déjà en place).

### 2.2 Noyau Métier Hexagonal (`packages/orcia-core/`)
- `packages/orcia-core/src/orcia_core/rag/two_speed_search.py` :
  - Enrichir `DEFAULT_SEARCH_CANDIDATES` pour couvrir les 7 familles de recherche (notamment `AGENTS_SKILLS`, `DELIVERABLES_ARTIFACTS`, `SOURCES_SNIPPETS`, `GLOSSARY_RULES`) et supporter gracieusement un `active_workspace_id` vide ou global au Jour 0.

### 2.3 Couche Backend API & Contrats (`apps/api/`, `packages/api-client/`)
- `apps/api/src/orcia_api/schemas/human_gates.py` & `apps/api/src/orcia_api/routers/human_gates.py` :
  - Ajouter `HumanGateEvaluationListResponse` et l'endpoint `GET /api/v1/gates/human/evaluations` (filtrable par `workspace_id`) pour réhydrater les évaluations de Gate humaine au chargement et après `F5`.
- `apps/api/src/orcia_api/schemas/jira_and_mcp.py` & `apps/api/src/orcia_api/routers/jira_and_mcp.py` :
  - Ajouter `StagedJiraActionListResponse` et `GET /api/v1/jira/actions/staged` pour réhydrater les actions Jira préparées/exécutées après `F5`.
- `apps/api/src/orcia_api/routers/portal_and_help.py` :
  - Dans `GET /api/v1/search`, accepter `scope: Literal["SCREEN", "WORKSPACE", "ALL_WORKSPACES", "GLOBAL", "CONTEXTUAL"] = Query(default="ALL_WORKSPACES")`, normaliser `"GLOBAL" -> "ALL_WORKSPACES"` et `"CONTEXTUAL" -> "WORKSPACE"`, et rendre `workspace_id` optionnel (`default=""`).
- `packages/api-client/src/domains/epics1To7Operations.ts` & `bootstrapAndOntology.ts` :
  - Ajouter `listHumanGateEvaluations` et `listStagedJiraActions`.
  - Mettre à jour `searchFederated(query, scope, workspaceId, screenRoute, forceSemantic)` pour transmettre `force_semantic=true` et une portée valide.

### 2.4 Interface Utilisateur & Design System (`packages/ui/`, `apps/web/`)
- `packages/ui/package.json`, `packages/ui/src/primitives/RadixDesignSystemPrimitives.tsx`, `packages/ui/src/primitives/DesignSystemControls.tsx`, `packages/ui/src/styles/tokens.css` :
  - Installer `@radix-ui/react-tabs`, `@radix-ui/react-dialog`, `@radix-ui/react-select`, `@radix-ui/react-dropdown-menu`, `@radix-ui/react-tooltip`, `@radix-ui/react-switch`.
  - Implémenter `OrciaTabBar` sur `@radix-ui/react-tabs` (roving `tabIndex`, flèches clavier, `Home`/`End`, `aria-controls`), `OrciaDialog`, `OrciaRadixSelect`, `OrciaDropdownMenu`, `OrciaTooltip`, `OrciaSwitch` stylés par `.orcia-ds-*` dans `tokens.css`.
- `apps/web/src/features/gates/GatesAdaptiveHumanReviewSection.tsx` & `apps/web/src/features/gates/index.tsx` :
  - Monter `CognitiveReviewBriefingGrid` et `ChunkValidationCard` câblés à `@orcia/api-client` avec réhydratation `F5` et exécution des actions Jira staged après validation de la Gate.
- `apps/web/src/components/ShellContainer.tsx` & `packages/ui/src/primitives/TopHeaderSearchCommand.tsx` :
  - Supprimer `localSemanticHit`, propager `forceSemantic=true` et afficher `cmdk-speed2-error-banner` en cas d'erreur réseau/API.
- `packages/ui/src/primitives/OrciaProductShowcaseSiteView.tsx` & `infra/scripts/sync_site_catalog.py` :
  - Afficher le compteur des capacités (`verifiedCapabilitiesCount / liveCapabilitiesCount`) dans `/showcase` et le site statique.

### 2.5 Analyse d'Impact sur la Pyramide des Tests (`AD-17` — Couches 1 à 5 + Sécurité)
- **Couche 1a (Unitaires Python `tests/unit/`)** : `tests/unit/test_story_4_3_adaptive_human_gates.py`, `tests/unit/test_epic_9_story_9_3_two_speed_search.py`.
- **Couche 1b (Unitaires/Composants TS `Vitest`)** : `packages/ui/src/__tests__/radix-design-system-primitives.test.tsx`, `apps/web/src/__tests__/zero-dead-buttons-and-silent-catches-audit.test.tsx`.
- **Couche 2 (Intégration Verticale HTTP)** : Vérification des routes `GET /api/v1/gates/human/evaluations` et `GET /api/v1/search`.
- **Couche 3 (Contrats & Architecture)** : `lint-imports`, `lint_spine.py`, `pnpm site:check`.
- **Couche 4 & Sécurité** : `tests/evals/` et `tests/security/` (vérification `403 ERR_OBSERVER_MODE_READ_ONLY` et `401 ERR_AUTH_REQUIRED`).
- **Couche 5 (E2E Navigateur Playwright Bi-Serveur)** : `apps/web/e2e/06-gates-review-and-anti-rubber-stamping.spec.ts` (activation du `test.fixme`) et `apps/web/e2e/10-command-palette-search.spec.ts` (retrait de `test.fail`).

---

## 3. Bilan des Modifications & Résultats (Post-Implémentation)

### 3.1 Tableau Synthétique des Fichiers Développés & Modifiés

| Fichier | Action | Lignes | Rôle & Responsabilité |
| :--- | :--- | :--- | :--- |
| `packages/orcia-core/src/orcia_core/rag/two_speed_search.py` | Modifié | 275 | Tolérance d'un `active_workspace_id` vide / `scope-global` / `GLOBAL` au Jour 0 (`BUG-E2E-06`). |
| `packages/orcia-pack-sdlc/src/orcia_pack_sdlc/jira_actions.py` | Modifié | 360 | Ajout de `list_staged_actions(workspace_id)` pour la réhydratation `F5` des actions Jira (`BUG-E2E-05`). |
| `apps/api/src/orcia_api/routers/portal_and_help.py` | Modifié | 246 | Support de `scope` `GLOBAL` / `CONTEXTUAL` et `workspace_id` optionnel sur `GET /api/v1/search` (`BUG-E2E-06`). |
| `apps/api/src/orcia_api/schemas/human_gates.py` | Modifié | 147 | Ajout de `HumanGateEvaluationListResponse` (`BUG-E2E-05`). |
| `apps/api/src/orcia_api/routers/human_gates.py` | Modifié | 258 | Ajout de `GET /api/v1/gates/human/evaluations` et garde d'accès tolérante au `workspace_id` de revue (`BUG-E2E-05`). |
| `apps/api/src/orcia_api/schemas/jira_and_mcp.py` | Modifié | 259 | Ajout de `StagedJiraActionListResponse` (`BUG-E2E-05`). |
| `apps/api/src/orcia_api/routers/jira_and_mcp.py` | Modifié | 269 | Ajout de `GET /api/v1/jira/actions` (`BUG-E2E-05`). |
| `packages/api-client/src/domains/bootstrapAndOntology.ts` | Modifié | 306 | Propagation de `include_speed2=true&force_semantic=true` dans `searchFederated` (`BUG-E2E-06`). |
| `packages/api-client/src/domains/epics1To7Operations.ts` | Modifié | 384 | Ajout de `listHumanGateEvaluations` et `listStagedJiraActions` (`BUG-E2E-05`). |
| `packages/ui/package.json` | Modifié | 38 | Déclaration des 6 primitives `@radix-ui/react-*` conformes à `ARCHITECTURE-SPINE.md` (`UX-DS-RADIX-01`, `AD-22`). |
| `packages/ui/src/primitives/RadixDesignSystemPrimitives.tsx` | Créé | 286 | Primitives accessibles `OrciaTabBar`, `OrciaDialog`, `OrciaRadixSelect`, `OrciaDropdownMenu`, `OrciaTooltip`, `OrciaSwitch` (`UX-DS-RADIX-01`). |
| `packages/ui/src/primitives/DesignSystemControls.tsx` | Modifié | 304 | Découpage modulaire `< 310` lignes et ré-export des primitives Radix (`UX-DS-RADIX-01`). |
| `packages/ui/src/primitives/TopHeaderSearchCommand.tsx` | Modifié | 331 | Ajout de `speed2Error` (`cmdk-speed2-error-banner`) et `speed2Executed` (`cmdk-speed2-appended-group`) (`BUG-E2E-06`). |
| `packages/ui/src/primitives/OrciaProductShowcaseSiteView.tsx` | Modifié | 396 | Exposition de `verifiedCapabilitiesCount / liveCapabilitiesCount` (`showcase-stat-capabilities`) (`CAP-ACT-1`). |
| `packages/ui/src/__tests__/radix-design-system-primitives.test.tsx` | Créé | 109 | 4 tests unitaires Vitest vérifiant la conformité WAI-ARIA/RGAA 4.1 et l'anti-LastPass des primitives Radix (`UX-DS-RADIX-01`). |
| `apps/web/src/components/ShellContainer.tsx` | Modifié | 385 | Suppression de `localSemanticHit` fabriqué côté client, câblage de `speed2Error` et `speed2Executed` (`BUG-E2E-06`). |
| `apps/web/src/features/gates/GatesAdaptiveHumanReviewSection.tsx` | Créé | 329 | Section de Revue Humaine Adaptative : `CognitiveReviewBriefingGrid` (4 blocs), `ChunkValidationCard`, garde-fou `< 15 s`, actions Jira et survie au `F5` (`BUG-E2E-05`). |
| `apps/web/src/features/gates/index.tsx` | Modifié | 185 | Montage de `GatesAdaptiveHumanReviewSection` sur `/gates` et `/processes` (`BUG-E2E-05`). |
| `apps/web/e2e/06-gates-review-and-anti-rubber-stamping.spec.ts` | Modifié | 173 | Remplacement de `test.fixme` par le parcours E2E complet (4 blocs, découpage, `< 15 s` -> `422`, Jira `EXECUTED`, survie `F5`) (`BUG-E2E-05`). |
| `apps/web/e2e/10-command-palette-search.spec.ts` | Modifié | 54 | Retrait de `test.fail` et vérification du statut `200` + `cmdk-speed2-appended-group` (`BUG-E2E-06`). |
| `docs/product/capabilities.yaml` | Modifié | 956 | Promotion de `33/54` capacités `live` vers `verification: runtime` (`CAP-ACT-1`, `CAP-ACT-5`). |

### 3.2 Résultats Chiffrés, Métriques & Validation des 5 Couches (`AD-17`)

- **Couche 1a — Linters, Typage & Contrats Python** :
  - `.venv/bin/ruff check .` & `.venv/bin/ruff format --check .` : **100 % vert (`0` erreur)**.
  - `.venv/bin/mypy --strict packages/orcia-kernel packages/orcia-core apps/api apps/worker` : **Success: no issues found in 220 source files**.
  - `.venv/bin/lint-imports` : **5 contracts kept, 0 broken**.
  - `.venv/bin/python .agent/skills/bmad-architecture/scripts/lint_spine.py` : **0 findings**.
- **Couche 1b — Tests Unitaires & Composants TypeScript (`pnpm turbo run lint typecheck test`)** :
  - **9/9 tâches Turbo réussies** : `@orcia/api-client` (`8/8` tests), `@orcia/ui` (`17/17` fichiers, `72/72` tests dont `4` nouveaux tests Radix UI), `@orcia/web` (`7/7` fichiers, `48/48` tests dont l'audit `zero-dead-buttons-and-silent-catches-audit.test.tsx`).
- **Couche 2 — Intégration HTTP & Contrats OpenAPI (`0-diff`)** :
  - Régénération de `packages/api-client/openapi.json` et `packages/api-client/src/generated/schema.ts` via `.venv/bin/python scripts/export_openapi.py`.
  - Nouveaux tests HTTP dans `tests/unit/test_story_4_3_adaptive_human_gates.py` (`GET /api/v1/gates/human/evaluations`) et `tests/unit/test_story_4_4_jira_staged_actions_and_mcp.py` (`GET /api/v1/jira/actions`) : **13/13 passés**.
- **Couche 5 — E2E Navigateur Playwright Bi-Serveur (`apps/web/e2e/`)** :
  - `e2e/06-gates-review-and-anti-rubber-stamping.spec.ts` : **1 passed (`5.1s`)** — Briefing 4 blocs, inspection du Bloc 4, approbation et co-édition signée `SHA-256` par section, rejet `HTTP 422 ERR_RUBBER_STAMPING_GUARD_TRIGGERED` et ouverture de la modale anti-rubber-stamping sous `< 15 s`, confirmation explicite des hypothèses, exécution de l'action Jira `PAYBUILD-101` (`EXECUTED`) et survie complète au `F5` (`localStorage.clear()` + `page.reload()`).
  - `e2e/10-command-palette-search.spec.ts` : **2 passed (`6.1s`)** — Ouverture `Ctrl+K`, déclenchement de la recherche Vitesse 2 (`GET /api/v1/search` -> `200 OK`), affichage de `cmdk-speed2-appended-group` et absence de toute erreur serveur ou résultat fabriqué.
- **Analyse GitNexus Post-Implémentation (`gitnexus_detect_changes`)** :
  - `changed_files: 29`, `changed_count: 46`, `affected_count: 113` ; `0` adaptateur SQL orphelin, `0` dépendance circulaire.
