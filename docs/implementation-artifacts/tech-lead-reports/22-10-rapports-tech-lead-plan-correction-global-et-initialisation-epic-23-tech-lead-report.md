# Story 22.10 — Rapports Tech Lead Individuels pour Tests en Échec & Plan Sally × Winston, Plan de Correction Global & Initialisation Epic 23

> **Convention de nommage du fichier (Obligatoire — à créer AVANT toute modification de code)** :
> - User Story du sprint : `docs/implementation-artifacts/tech-lead-reports/{story-key}-tech-lead-report.md`

- **Date** : 2026-11-19
- **Story / Clé Sprint** : `22-10-rapports-tech-lead-plan-correction-global-et-initialisation-epic-23` (`Epic 22` — Clôture & Initialisation `Epic 23`)
- **Capacité(s)** : `none (gouvernance documentaire & planification Epic 23 — rattache les 62 capacités failed_e2e résiduelles et les 13 chantiers REM23-01..REM23-13 issus de e2e-campaign-epic-22)` — classification : `doc`
- **Auteur / Contexte** : `22.10-impl` (`bmad-architect-worker`) + `22.10-test` (`bmad-dev-worker`) — Consolidation post-campagne Epic 22 (`bilan-execution-tests-e2e-epic-22.md`, `synthese-remediation-sally-winston-epic-22.md`), analyse d'impact MCP GitNexus (`repo: "/home/romain/Documents/Projects/ORCIA"`), rédaction des `6` rapports Tech Lead individuels (`23-1-...` à `23-6-...`), plan de correction global (`sprint-change-proposal-2026-11-18-epic-23-remediation-plan.md`), initialisation complète de l'**Epic 23** dans `epics.md`, `sprint-status.yaml` et `capabilities.yaml`, suite de traçabilité `tests/unit/test_epic22_to_epic23_traceability.py`, validation complète de la pyramide `AD-17` et clôture de `Story 22.10` / `Epic 22`.
- **Commits associés** : `feat/epic-22-remediation-pg18-direction-c` (suite de `20d6684`, commit de clôture `Story 22.10` / `Epic 22`)

---

## 1. Analyse du Besoin & Étude d'Impact Tech Lead (Pré-Implémentation)

### 1.1 Contexte & Problématique
- **Exploitation rigoureuse des constats de `Story 22.9`** :
  - Une fois la campagne intégrale Epic 22 exécutée (`docs/implementation-artifacts/e2e-campaign-epic-22/`) et l'audit croisé **Sally × Winston** achevé (`synthese-remediation-sally-winston-epic-22.md`), il convient de transformer de façon systématique et traçable **100 % des tests E2E en échec résiduel** et **100 % des points d'amélioration UX/Architecture Sally × Winston** en un plan d'action structuré pour l'**Epic 23**.
- **Obligations du Protocole Tech Lead (`GEMINI.md`)** :
  - Chaque lot cohérent de correction ou d'amélioration (`Story 23.1`..`Story 23.N`) doit disposer **avant tout codage** de son **Rapport Tech Lead pré-implémentation individuel** (`docs/implementation-artifacts/tech-lead-reports/23-k-...-tech-lead-report.md`) conforme à `TECH-LEAD-REPORT-TEMPLATE.md`, basé sur une étude d'impact GitNexus réelle (`repo: "ORCIA"`).
  - Un **Plan de Correction Global** (`docs/planning-artifacts/sprint-change-proposal-2026-11-18-epic-23-remediation-plan.md`) doit relier explicitement chaque test en échec, chaque item Sally × Winston et chaque capacité `failed_e2e` résiduelle à une Story `23.k` et son rapport Tech Lead.
  - Aucune capacité `failed_e2e` ne peut conserver un `e2e_remediation_ref` générique ou obsolète (`"epic-22"` / clé `22-*` clôturée) : toutes les références résiduelles pointent vers une clé exacte `23-k-...` présente dans `sprint-status.yaml` et dotée d'un rapport Tech Lead.

### 1.2 Exploration, Analyse d'Impact GitNexus, Factorisation & Dette Technique
- **Analyse d'Impact GitNexus (`repo: "/home/romain/Documents/Projects/ORCIA"`, `staleness: "behind", commitsBehind: 2`)** :
  - `reset_database_to_first_boot` (`infra/scripts/maintenance/09_reset_db_first_boot.py:L124-225`) : `impactedCount: 127`, `risk: "CRITICAL"`, `epistemic: "exact"` (`direct: 87`, `d=2: 33`, `d=3: 7`, `processes_affected: 138`, `modules_affected: 18`) ; `reset_day0` non indexé comme symbole appelable, chaîne E2E vérifiée par lecture directe (`day0.ts:L12-18 -> reset_day0.py -> 09_reset_db_first_boot.py`).
  - `resolve_request_user` : `impactedCount: 127`, `risk: "CRITICAL"`, `epistemic: "exact"` (`direct: 87`, `d=2: 33`, `d=3: 7`, `processes_affected: 138`, `modules_affected: 18`).
  - `useAssistantStreamingTurn` (`useAssistantStreamingTurn.ts`) : `impactedCount: 549`, `risk: "CRITICAL"`, `epistemic: "exact"` (`direct: 340`, `d=2: 163`, `d=3: 46`, `processes_affected: 175`, `modules_affected: 20`).
  - `ContextualHelpResolutionService` (`contextual_help.py:L74-378`) : `impactedCount: 7`, `risk: "CRITICAL"`, `epistemic: "exact"` (`direct: 4` : `_autonomous_supervision_ops.py`, `_sql_autonomous_rollback.py`, `autonomous_supervision.py`, `help_generator_and_validator.py` ; `d=2: 3` : `orchestration/__init__.py`, `_help_orcia_docs_workflow.py`, `sql_autonomous_supervision.py` ; `modules_affected: 6`).
  - `ShellContextualHelpColumn` (`ShellContextualHelpColumn.tsx:L23-154`) : `impactedCount: 121`, `risk: "CRITICAL"`, `epistemic: "exact"` (`direct: 1` : `InnerShellContainer` ; `d=2: 87`, `d=3: 33`, `processes_affected: 195`, `modules_affected: 20`).
  - `ProgressiveDay0AccostageService` (`progressive_accostage.py:L130-335`) : `impactedCount: 590`, `risk: "CRITICAL"`, `epistemic: "exact"` (`direct: 3` entrants : `bootstrap/__init__.py`, `sql_first_user_guard.py` ; `d=2: 404`, `d=3: 183`, `processes_affected: 195`, `modules_affected: 20`).
  - `ProgressiveDay0AccostageBanner` (`ProgressiveDay0AccostageBanner.tsx`) : `impactedCount: 127`, `risk: "CRITICAL"`, `epistemic: "exact"` (`direct: 87`, `d=2: 33`, `d=3: 7`, `processes_affected: 138`, `modules_affected: 18`).
  - `InnerShellContainer` (`ShellContainer.tsx`) : `impactedCount: 131`, `risk: "CRITICAL"`, `epistemic: "exact"` (`direct: 91`, `d=2: 33`, `d=3: 7`, `processes_affected: 138`, `modules_affected: 20` ; `ShellContainer` comporte `6` homonymes dans l'index, max `impactedCount: 562`).
  - `FourZoneTopHeaderSection` (`L32-291`) : `impactedCount: 127`, `risk: "CRITICAL"`, `epistemic: "exact"` (`direct: 87`, `d=2: 33`, `d=3: 7`, `processes_affected: 138`, `modules_affected: 18`).
  - `ModuleWorkspaceView` (`ModuleWorkspaceView.tsx:L23-120`) : `impactedCount: 150`, `risk: "CRITICAL"`, `epistemic: "exact"` (`direct: 108`, `d=2: 35`, `d=3: 7`, `processes_affected: 143`, `modules_affected: 20` ; nœud contexte affecté par la dérive d'index, vérifié par lecture directe).
  - `CockpitFeaturePanel` (`features/cockpit/index.tsx`) : `impactedCount: 127`, `risk: "CRITICAL"`, `epistemic: "exact"` (`direct: 87`, `d=2: 33`, `d=3: 7`, `processes_affected: 138`, `modules_affected: 18`).
  - `streamAssistantTurnSse`, `createRequestJson`, `FirstBootAdminSetupModal`, `CockpitHumanLedGovernanceSection`, `useReflexiveExecutionController`, `useWorkspaceEventsSse` : touchés par le retard d'index GitNexus (`2 commitsBehind`, pointeurs corrompus / nœuds fichier uniquement `0` appelants `UNKNOWN`), intégralement compensé par inspection directe des sources (`read_file`) et consigné pour rafraîchissement (`npx gitnexus analyze`) lors de la clôture.
- **Découpage cohérent en `6` Stories (`23.1`..`23.6` sur `3` Vagues)** :
  - **Vague 0 (`P0`)** : `23-1` (`REM23-01` / `ARCH23-01`, `87` échecs cascade `resetDay0()`) + `23-2` (`REM23-02`, `REM23-03`, `REM23-04` / `ARCH23-02`, `ARCH23-03`, `P0-UX-1`, `3` échecs `401` directs).
  - **Vague 1 (`P1`–`P3`)** : `23-3` (`REM23-05` Zone 4 fidèle & `4` blocs `DESIGN.md`) + `23-4` (`REM23-06..08` Accostage `X/6`, fin fantômes Jour 0, Modale Admin) + `23-5` (`REM23-09..12` Cockpit `<= 3` blocs, `TopHeaderBar` sans doublon, `/assistant`, `/login`, captures `#10`).
  - **Vague 2 (`P0`)** : `23-6` (`REM23-13` campagne E2E intégrale `110/110` Desktop + Mobile Companion levant l'angle mort `0/55` & `04`–`21`, audit Sally, promotion `62/62` `runtime`).
- **Contrôle de volumétrie (`> 300–400` L) & opportunités DRY planifiés** :
  - Découpages planifiés dans les rapports individuels : `packages/api-client/src/domains/bootstrapAndOntology.ts` (`472` L, `Story 23.2` → extraction `assistantStreaming.ts`), `packages/ui/src/primitives/ContextualHelpColumnAndCenter.tsx` (`394` L, `Story 23.3`), `apps/web/src/components/platformSetupStore.tsx` (`521` L, `Story 23.4`) & `ShellContainer.tsx` (`403` L, `Story 23.4` + purge `5` props mortes), `apps/web/src/features/cockpit/CockpitHumanLedGovernanceSection.tsx` (`383` L, `Story 23.5`).
  - Factorisations DRY : `createRequestSse` dans `packages/api-client/src/helpers.ts` (`Story 23.2`), champ mot de passe avec œil partagé `@orcia/ui` entre `FirstBootAdminSetupModal` (`23.4`) et `BiModeLoginView` (`23.5`).
- **Verrou automatique de traçabilité** :
  - `tests/unit/test_epic22_to_epic23_traceability.py` (à créer et exécuter par `22.10-test` sur le modèle de `test_epic21_to_epic22_traceability.py`) garantissant `100 %` des `24` specs / `90` échecs E2E, `13/13` `REM23-*` (`12` Sally + `10` Winston) et `62/62` `CAP-*` `failed_e2e` couverts sans orphelin.

---

## 2. Plan d'Implémentation

### 2.1 Schéma de Données & Migrations Alembic (`infra/migrations/versions/`)
- Aucune migration Alembic appliquée en Story `22.10` (`doc` + test unitaire de traçabilité uniquement). Tout besoin éventuel de schéma issu de `22.9` est spécifié en Section 2.1 des rapports Tech Lead `23-1`..`23-N`.

### 2.2 Noyau Métier Hexagonal, Orchestration & Workers (`packages/orcia-core/`, `apps/worker/`)
- Aucune modification de code applicatif dans `Story 22.10`. Les lots backend/domaine/persistance identifiés en `22.9` sont spécifiés avec leurs contrats hexagonaux et invariants `AD-1`..`AD-24` dans les rapports `23-k-*`.

### 2.3 Couche Backend API, Sécurité & Contrats (`apps/api/`, `packages/api-client/`)
- Aucune modification d'endpoint dans `Story 22.10`. Les ajustements API/contenus/contrats OpenAPI nécessaires sont détaillés dans les rapports `23-k-*`.

### 2.4 Documentation Planification, Rapports Tech Lead & Initialisation Epic 23 (`docs/`)
1. **Rapports Tech Lead individuels (`23-1-...`..`23-N-...`)** :
   - Rédaction de `N` rapports conformes à `TECH-LEAD-REPORT-TEMPLATE.md` (Sections 1 & 2 complètes, Section 3 préparée avec les 3 titres obligatoires vérifiés par `scripts/check_implementation_docs.py`).
   - Enregistrement de tous les rapports `23-*` (et complétion Section 3 de `22.10`) dans `docs/implementation-artifacts/tech-lead-reports/README.md`.
2. **Plan de correction global (`docs/planning-artifacts/sprint-change-proposal-2026-11-18-epic-23-remediation-plan.md`)** :
   - Synthèse exécutive, graphe Mermaid d'ordonnancement topologique par vagues (`23.1` $\rightarrow$ `23.N`), matrices exhaustives de traçabilité (Échecs E2E Epic 22 $\rightarrow$ `23.k`, Items Sally × Winston $\rightarrow$ `23.k`, `CAP-*` `failed_e2e` $\rightarrow$ `23.k`).
3. **Initialisation `Epic 23` & Clôture `Epic 22`** :
   - `docs/planning-artifacts/epics.md` : ajout de `Epic 23` dans `FR Coverage Map`, `Epic List` et section détaillée `## Epic 23:` avec `### Story 23.1:`..`### Story 23.N:` (`Given/When/Then`).
   - `docs/implementation-artifacts/sprint-status.yaml` : ajout de `epic-23: backlog` + `23-1-...`..`23-N-...: ready-for-dev`, passage de `22-10-...: done` et `epic-22: done`.
   - `docs/product/capabilities.yaml` : mise à jour de tout éventuel `e2e_remediation_ref` résiduel vers les clés `23-k-...` exactes.

### 2.5 Analyse d'Impact sur la Pyramide des Tests (`AD-17`)
- **Couche 1a (`pytest`)** : création et exécution de `tests/unit/test_epic22_to_epic23_traceability.py` prouvant à `100 %` que chaque échec E2E de `e2e-campaign-epic-22/playwright-results.json`, chaque point d'amélioration de `synthese-remediation-sally-winston-epic-22.md` et chaque `CAP-*` en `failed_e2e` est relié à une Story `23.k` dans `epics.md`, `sprint-status.yaml` et son rapport Tech Lead indexé dans `README.md`.
- **Gouvernance documentaire & Vitrine** : `.venv/bin/python scripts/check_implementation_docs.py`, `pnpm site:sync && pnpm site:check`, `.venv/bin/ruff check/format`, `.venv/bin/lint-imports`, `.venv/bin/python .agent/skills/bmad-architecture/scripts/lint_spine.py`.

---

## 3. Bilan des Modifications & Résultats (Post-Implémentation)

### 3.1 Fichiers Développés & Modifiés
| Fichier | Nature (Création / Modification / Refactoring) | Description synthétique |
| :--- | :--- | :--- |
| `docs/implementation-artifacts/tech-lead-reports/23-1-reset-jour0-e2e-truncate-cascade-connector-schemes-et-redis-tech-lead-report.md` | Création (`22.10-impl`) | Rapport pré-implémentation Story 23.1 (`REM23-01` / `ARCH23-01`, `87` cascades `resetDay0()`) |
| `docs/implementation-artifacts/tech-lead-reports/23-2-transport-sse-authentifie-createrequestsse-smoke-00-et-diagnostic-401-tech-lead-report.md` | Création (`22.10-impl`) | Rapport pré-implémentation Story 23.2 (`REM23-02..04` / `ARCH23-02..03`, `P0-UX-1`, `3` `401` directs) |
| `docs/implementation-artifacts/tech-lead-reports/23-3-zone-4-aide-contextuelle-fidele-a-la-route-et-4-blocs-design-md-tech-lead-report.md` | Création (`22.10-impl`) | Rapport pré-implémentation Story 23.3 (`REM23-05` / `ARCH23-04`, `P1-UX-5`, `P2-UX-8`) |
| `docs/implementation-artifacts/tech-lead-reports/23-4-unification-accostage-x-sur-6-fin-fantomes-jour0-et-modale-admin-tech-lead-report.md` | Création (`22.10-impl`) | Rapport pré-implémentation Story 23.4 (`REM23-06..08` / `ARCH23-05`, `P1-UX-4,6,7`) |
| `docs/implementation-artifacts/tech-lead-reports/23-5-sobriete-cockpit-topbar-sans-doublon-assistant-et-login-tech-lead-report.md` | Création (`22.10-impl`) | Rapport pré-implémentation Story 23.5 (`REM23-09..12` / `ARCH23-06..09`, `P1-UX-3`, `P2-UX-8..11`, `P3-UX-12`) |
| `docs/implementation-artifacts/tech-lead-reports/23-6-campagne-e2e-integrale-mobile-companion-audit-et-62-capacites-runtime-tech-lead-report.md` | Création (`22.10-impl`) | Rapport pré-implémentation Story 23.6 (`REM23-13` / `ARCH23-10`, `P0-UX-2`, campagne `110/110` & `62/62` `runtime`) |
| `docs/implementation-artifacts/tech-lead-reports/README.md` | Modification (`22.10-impl` / `22.10-test`) | Enregistrement des `6` rapports `23-1..23-6` et clôture de l'entrée `Story 22.10` (`190` rapports indexés) |
| `docs/planning-artifacts/sprint-change-proposal-2026-11-18-epic-23-remediation-plan.md` | Création (`22.10-impl`) | Plan directeur global Epic 23 (`3` vagues, diagramme Mermaid, `3` matrices exhaustives `24` specs / `90` échecs / `13` `REM23` / `62` `CAP-*`) |
| `docs/planning-artifacts/epics.md` | Modification (`22.10-impl`) | Mise à jour `FR Coverage Map`, `Epic List` et ajout `Epic 23` (`Stories 23.1`..`23.6` `Given/When/Then`) |
| `docs/implementation-artifacts/sprint-status.yaml` | Modification (`22.10-impl` / `22.10-test`) | Passage `22-10-...: done` + `epic-22: done` et maintien `epic-23: backlog`, `23-1..23-6: ready-for-dev`, `epic-23-retrospective: optional` |
| `docs/product/capabilities.yaml` | Modification (`22.10-impl`) | Remplacement exact des `62` références `e2e_remediation_ref` (`"22-10-..."` → clés exactes `"23-1-..."`..`"23-6-..."`, `0` reliquat) |
| `tests/unit/test_epic22_to_epic23_traceability.py` | Création (`22.10-test`) | Suite automatisée (`5/5`) vérifiant les livrables `e2e-campaign-epic-22`, `110` PNG `< 450 KB`, `24/24` specs en échec, `13/13` `REM23-*`, `12/12` `P*-UX-*`, `10/10` `ARCH23-*`, `62/62` `CAP-*` `failed_e2e`, `epics.md`, `23-1..23-6` et `README.md` |
| `apps/web/src/generated/orciaSiteManifest.ts`, `docs/site-catalog/index.html` | Régénération (`pnpm site:sync`) | Synchronisation du manifeste produit/architecture (`190` rapports, `28` routes, `133` primitives UI, `65` capacités live) |

### 3.2 Résultats Chiffrés, Métriques & Qualité
- **Traçabilité `Epic 22 -> Epic 23` (`100 %`)** :
  - Livrables `docs/implementation-artifacts/e2e-campaign-epic-22/` : `6/6` documents présents et non vides + `110/110` entrées `manifest.jsonl` + `110/110` captures PNG présentes et `< 450 KB` (`max = 223 386 o`).
  - `24/24` specs E2E en échec (`90/90` cas `failed`), `13/13` chantiers `REM23-01..REM23-13` (`12/12` items Sally `P0-UX-1..P3-UX-12` + `10/10` items Winston `ARCH23-01..ARCH23-10`) et `62/62` capacités `failed_e2e` (`3/3` `foundation` en `runtime`) rattachés à `23-1..23-6` dans `sprint-change-proposal-2026-11-18-epic-23-remediation-plan.md`, `sprint-status.yaml`, `epics.md` et `tech-lead-reports/23-*-tech-lead-report.md` (`README.md`).
- **Couverture & Pyramide Python (`AD-17`)** :
  - Tests unitaires (`tests/unit`) : **`763 passed`** (dont `32 passed` sur traçabilité/couverture UJ/registre ; note : exécutés en deux lots sous `--cov` puis confirmés ciblés `4/4` sur `test_permission_broker.py` et `5/5` sur `test_story_7_0c_openshift_scc_kustomize_and_ready.py`).
  - Couches contrat (`2`), conformité (`11`), évals (`16`) & sécurité (`108`) : **`137 passed`**.
  - Couche intégration (`tests/integration`, conteneurs PG18 + Redis + S3/OpenSearch) : **`104 passed`** (`22 + 25 + 19 + 38` en 4 lots).
  - **Couverture combinée `packages/orcia-core`** : **`92.31 %`** (`23 410` instructions, `1 217` manquées, `5 302` branches, `798` partielles, `132` fichiers à `100 %`, seuil `--cov-fail-under=90` atteint).
- **Qualité Statique, Architecture & TypeScript** :
  - `.venv/bin/ruff check .` & `.venv/bin/ruff format --check .` : **`0` erreur** (`1 250` fichiers conformes).
  - `.venv/bin/mypy --strict packages/orcia-core apps/api apps/worker` : **`0` erreur** (`513` fichiers source).
  - `.venv/bin/lint-imports` : **`5 contracts kept, 0 broken`** (`596` fichiers, `4 279` dépendances).
  - `.venv/bin/python scripts/export_openapi.py --check` : **`0-diff`**.
  - `.venv/bin/python .agent/skills/bmad-architecture/scripts/lint_spine.py` : **`0 findings`**.
  - `.venv/bin/python scripts/check_implementation_docs.py` : **`190 / 190` rapports conformes et indexés**.
  - `pnpm site:sync && pnpm site:check` : **`0` erreur** (`65/65` capacités live, `62/62` E2E couverts, `20/20` UJ).
  - `pnpm turbo run lint typecheck test` : **`9/9` tâches vertes** (`@orcia/api-client`: `13/13`, `@orcia/ui`: `110/110`, `@orcia/web`: `190/190` = **`313/313` tests JS/TS**, `vite build` OK).

### 3.3 Validation & Procédure de Test sur Toute la Pyramide (`AD-17`)
- **Commandes exécutées & résultats** :
  1. `timeout --kill-after=5s 60s .venv/bin/pytest tests/unit/test_epic22_to_epic23_traceability.py tests/unit/test_epic21_to_epic22_traceability.py tests/unit/test_uj_e2e_coverage_gate.py tests/unit/test_capabilities_registry.py -v` $\rightarrow$ **`32 passed`** (`2.46s`).
  2. `.venv/bin/ruff check . && .venv/bin/ruff format --check .`, `.venv/bin/mypy --strict packages/orcia-core apps/api apps/worker`, `.venv/bin/lint-imports`, `scripts/export_openapi.py --check`, `lint_spine.py` $\rightarrow$ **`100 %` PASS**.
  3. Pyramide Python complète avec `--cov=packages/orcia-core --cov-append --cov-fail-under=90` : `763` unitaires + `137` contrat/conformité/évals/sécurité + `104` intégration PG18/Redis/S3 = **`1 004` tests Python PASS**, couverture combinée **`92.31 %`** (artefacts `.coverage*` nettoyés).
  4. `pnpm turbo run lint typecheck test` $\rightarrow$ **`9/9` tâches Turbo vertes** (`313/313` tests JS/TS).
  5. `.venv/bin/python scripts/check_implementation_docs.py` & `pnpm site:sync && pnpm site:check` $\rightarrow$ **`190/190` rapports**, **`0` erreur**.
  6. **GitNexus (`npx --yes gitnexus analyze --index-only` + `gitnexus_detect_changes({scope: "all", repo: "/home/romain/Documents/Projects/ORCIA"})`)** : index actualisé (`22 829` symboles / `37 304` nœuds, `69 962` arêtes, `652` clusters, `1 725` flux) ; `summary: {changed_count: 1, affected_count: 0, changed_files: 7, risk_level: "low"}`, seul symbole touché `ORCIA_SITE_MANIFEST` (`apps/web/src/generated/orciaSiteManifest.ts`), `0` processus impacté.
- **Clôture** : `22-10-rapports-tech-lead-plan-correction-global-et-initialisation-epic-23: done` et `epic-22: done` actés dans `sprint-status.yaml` (`epic-23: backlog`, `23-1..23-6: ready-for-dev`).
