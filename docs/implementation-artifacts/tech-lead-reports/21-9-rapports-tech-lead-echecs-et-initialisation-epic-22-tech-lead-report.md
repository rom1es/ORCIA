# Story 21.9 — Analyse GitNexus, Rapports Tech Lead Pré-Implémentation, Plan Directeur & Initialisation de l'Epic 22

> **Convention de nommage du fichier (Obligatoire — à créer AVANT toute modification de code)** :
> - User Story du sprint : `docs/implementation-artifacts/tech-lead-reports/{story-key}-tech-lead-report.md`

- **Date** : 2026-11-18
- **Story / Clé Sprint** : `21-9-analyse-gitnexus-rapports-tech-lead-plan-directeur-et-initialisation-epic-22` (`Epic 21`)
- **Capacité(s)** : `none (gouvernance documentaire & planification Epic 22 — couvre le plan de retour au vert des 51 capacités failed_e2e de CAP-001..CAP-203)` — classification : `doc`
- **Auteur / Contexte** : `bmad-architect-worker` (`21.9-impl`, Architecte & Tech Lead BMAD) — Consolidation de l'audit croisé Sally × Winston (`synthese-remediation-sally-winston-epic-21.md`, `REM-01`..`REM-34`), du bilan E2E PostgreSQL 18 (`bilan-execution-tests-e2e-epic-21.md`, `playwright-results.json`, `47` échecs/timeouts sur `14/24` specs), analyse d'impact MCP GitNexus, rédaction des `8` rapports Tech Lead individuels (`22-1`..`22-8`), plan directeur (`sprint-change-proposal-2026-11-18-epic-22-remediation-plan.md`) et initialisation complète de l'**Epic 22** dans `epics.md`, `sprint-status.yaml` et `capabilities.yaml` (`AD-17`, `NFR-TEST-1`, `GEMINI.md` § Policy).
- **Commits associés** : `575cf4a` (socle Story 21.8) — clôture Story 21.9 & Epic 21 (`done`)

---

## 1. Analyse du Besoin & Étude d'Impact Tech Lead (Pré-Implémentation)

### 1.1 Contexte & Problématique
- La campagne E2E intégrale de la **Story 21.8** (`--retries=0 --max-failures=0 --timeout=35000`) sur la pile PostgreSQL 18 + pgvector (`orcia_e2e`) et Redis 7.4 (`575cf4a`) a produit `110 / 110` captures PNG et révélé un état exact sans maquillage :
  - **Scénarios Playwright (`playwright-results.json`)** : `110` planifiés (`55` Desktop `1440×900` + `55` Mobile `390×844`), `47` `expected` (`passed`), `16` `skipped` (gardes viewport), **`47` `unexpected`** (`36` `failed` + `11` `timedOut`), `0` `flaky`.
  - **Couverture par specs (`24`)** : `10` specs `100 % PASS`, **`14` specs avec `>= 1` échec ou timeout** (`02`, `03`, `04`, `06`, `07`, `13`, `14`, `15`, `16`, `17`, `18`, `19`, `20`, `21`).
  - **Synthèse croisée Sally × Winston** : **`34` chantiers exhaustifs (`REM-01` .. `REM-34`)** répartis en `4` vagues (`Vague 0` à `Vague 3`), incluant aussi les non-conformités UX/UI masquées sur les écrans `PASSED` (Mobile Companion non câblé avec `overflow-x: hidden`, sidebar `11` entrées au lieu de `8`, aide contextuelle droite figée sur `@1.1.0` avec `Chef1`/`aqwZSX`, fuites de jargon technique, pastilles `(!)` rouges dans les boutons bleus).
  - **Registre des capacités (`docs/product/capabilities.yaml`)** : sur `65` capacités (`3` `foundation` + `62` `feature`), `11` capacités `feature` sont à `verification: runtime` et **`51` capacités `feature` sont à `verification: failed_e2e`** avec `e2e_remediation_ref: "epic-22"` générique (ainsi qu'un décalage YAML cosmétique après des commentaires de section sur `CAP-011`, `CAP-024`, `CAP-033`, `CAP-058`, `CAP-069`, `CAP-074`, `CAP-180`, `CAP-190`).
- **Problème à résoudre en Story 21.9** : transformer cette masse de constats hétérogènes en un **plan d'exécution topologique sans chevauchement (`8` Stories `22.1`..`22.8`)**, doté pour chaque Story d'un **rapport Tech Lead pré-implémentation** conforme à `TECH-LEAD-REPORT-TEMPLATE.md`, d'un **Plan Directeur de traçabilité totale** et d'un rattachement nominatif de `100 %` des `47` échecs E2E, `34` `REM-*` et `51` `CAP-*` en `failed_e2e`.
- **Contraintes `ARCHITECTURE-SPINE.md` & `GEMINI.md`** :
  - Respect strict du monolithe modulaire `AD-19` (`lint-imports`), du Composition Root unique `AD-1` (aucun singleton `_DEFAULT_*` ni contournement `ORCIA_DISABLE_PG_BOOTSTRAP_SYNC`), du Design System isolé `@orcia/ui` (`AD-22`, Direction C `8` entrées, zéro `#hex` hors `tokens.css`), de la pyramide `AD-17` (5 couches + sécurité, `>= 90 %` de couverture) et du périmètre documentaire strict de `bmad-architect-worker` (aucune édition de code applicatif dans cette passe `21.9-impl`).

### 1.2 Exploration, Analyse d'Impact GitNexus, Factorisation & Dette Technique
- **Analyse d'Impact GitNexus (`gitnexus_query`, `gitnexus_context`, `gitnexus_impact` sur `repo: "/home/romain/Documents/Projects/ORCIA"`)** :
  *(Note factuelle d'index : GitNexus signale `staleness: behind (11 commitsBehind HEAD)` — la topologie d'appels ci-dessous est exacte pour l'état indexé `epistemic: exact` et complétée par inspection des documents d'audit `575cf4a` ; un `npx gitnexus analyze` sera exécuté en début d'Epic 22.)*

| Symbole ciblé | Fichier / Localisation | Résultat `gitnexus_context` / `gitnexus_impact({direction: "upstream"})` | Niveau de risque & Enseignement architectural |
| :--- | :--- | :--- | :--- |
| `MatrixPermissionEvaluator` | `packages/orcia-core/src/orcia_core/permissions/evaluator.py` (`L51-361`) | `impactedCount: 18` (`direct: 9`, `d=2: 5`, `d=3: 4`), `epistemic: exact` | **`MEDIUM`** — Importé par `catalog`, `orchestration` (`control_center`, `run_lock_service`, `seeds`), `permissions` (`broker`, `service`), `bootstrap`. |
| `resolve_workspace_access` | `packages/orcia-core/src/orcia_core/permissions/evaluator.py` | `impactedCount: 287` (`direct: 122`, `d=2: 124`, `d=3: 41`, `processes_affected: 33`, `modules_affected: 18`), `epistemic: exact` | **`CRITICAL`** — Point de bascule RBAC central ; toute règle `PLATFORM_ADMIN` vs `READ_ONLY_OBSERVER` impacte 33 flux API (`catalog`, `challenge_and_replay`, `org_units`, `orchestration`, `gates`, `executions_trace`). |
| `createWorkspace` | `apps/web/src/components/platformSetupStore.tsx` (`L839-888`) | `impactedCount: 358` (`direct: 182`, `d=2: 135`, `d=3: 41`, `processes_affected: 51`, `modules_affected: 20`) | **`CRITICAL`** — La génération `"ws-N"` et la perte de `slug` se propagent vers toutes les routes espaces, sources, ADN et FinOps. |
| `OrciaDialog` | `packages/ui/src/primitives/RadixDesignSystemPrimitives.tsx` (`L86-126`) | `impactedCount: 281` (`direct: 118`, `d=2: 122`, `d=3: 41`, `processes_affected: 33`, `modules_affected: 18`) | **`CRITICAL`** — Primitive Portal Radix canonique de `@orcia/ui` ; sa refonte flex (`header + body scrollable + footer sticky`) et ses tokens `--z-dialog` sécurisent 100 % des modales. |
| `UserSettingsModalDialog` | `packages/ui/src/primitives/UserSettingsModalDialog.tsx` (`L71-278`) | `impactedCount: 366` (`direct: 188`, `d=2: 137`, `d=3: 41`, `processes_affected: 51`) | **`CRITICAL`** — Actuellement sans `DialogPrimitive.Portal` et dépendant de classes Tailwind v4 non compilées (`.z-50`, `.h-[580px]`, `.max-w-[820px]`). |
| `FourZoneDirectionCShell` | `packages/ui/src/primitives/FourZoneDirectionCShell.tsx` (`L137-339`) | `impactedCount: 281` (`direct: 118`, `d=2: 122`, `d=3: 41`, `processes_affected: 33`) | **`CRITICAL`** — Coquille maîtresse de toute la SPA : gère les 4 zones, Zone 4 `sticky`, les 8 entrées, le responsive `< 768 px` et le masquage de Zone 4 sur `/help`. |
| `UpstreamChallengeRewindModal` | `packages/ui/src/primitives/UpstreamChallengeRewindModal.tsx` (`L75-440`) | `impactedCount: 281` au graphe global mais **`0` import applicatif** dans `apps/web/src/` | **`CRITICAL` (orphelin UI)** — Composant exporté par `@orcia/ui` mais jamais monté ni câblé dans le Cockpit / Vue Fokus. |
| `AssistantFoldersAndSharingService` | `packages/orcia-core/src/orcia_core/orchestration/assistant_folders_and_sharing.py` (`L170-601`) | `impactedCount: 0` via arêtes directes de classe (`UNKNOWN` — résolu via `Depends` FastAPI dans `portal_and_assistant.py`) | **`HIGH` (silo RAM)** — `_folders`/`_threads` en `dict` RAM sans `AsyncEngine` et fuite `[LAYER_5_FOLDER_CONTINUITY ...]` dans le DTO renvoyé. |
| `UnifiedNotificationAndClaimService` | `packages/orcia-core/src/orcia_core/orchestration/notifications_and_claims.py` (`L38-440`) | `impactedCount: 2` (`orchestration/__init__.py`, `control_center.py`), `epistemic: exact` | **`LOW` (couplage)** / **`P0` (silo RAM)** — Instancié sans PG18 dans `core_and_lifespan.py:219-234`. |
| `PermissionBrokerService` | `packages/orcia-core/src/orcia_core/permissions/broker.py` (`L52-257`) | `impactedCount: 8` (`direct: 3`: `bootstrap/__init__.py`, `bootstrap/engine.py`, `permissions/__init__.py`; `processes_affected: 117`, `modules_affected: 20`) | **`CRITICAL`** — `_tickets` en RAM et `resolve_matching_policy` levant `404` faute de politique socle `git://*`. |
| `AdaptiveHumanGateService` | `packages/orcia-core/src/orcia_core/gates/human.py` (`L161-438`) | `impactedCount: 11` (`direct: 2`: `gates/__init__.py`, `deterministic.py`; `d=2: 4`, `d=3: 5`), `epistemic: exact` | **`LOW`** — Isolé derrière `bootstrap_svc.gate_service`, facilement injectable avec `SqlGateEvaluationRepository` PG18. |
| `DurableOnboardingWizardService` | `packages/orcia-core/src/orcia_core/bootstrap/durable_wizards.py` (`L136-297`) | `impactedCount: 1` (`bootstrap/__init__.py`), `epistemic: exact` | **`LOW`** — Remplacement transparent du dict mémoire par `wizard_sessions` PG18 + câblage `@orcia/api-client` dans `routes/wizards.tsx`. |
| `restore_help_article_and_rollback_run_sql` | `packages/orcia-core/src/orcia_core/orchestration/_internal/_sql_autonomous_rollback.py` (`L22-185`) | `impactedCount: 281` (`direct: 118`, `processes_affected: 33`) | **`CRITICAL`** — `UPDATE workflow_runs SET status = 'ROLLED_BACK' WHERE id = :run_id` sans `AND status <> 'KILL_SWITCH_STOPPED'` écrase l'arrêt d'urgence en PG18. |

- **Exploration & Chiffres Clés** :
  - `14 / 24` specs E2E en échec (`47` cas `unexpected` = `36` `failed` + `11` `timedOut`, `100 %` avec capture PNG).
  - `16` échecs directs de persistance PG18 (`0` ligne trouvée par `SELECT` sur `assistant_folders`, `human_anchor_signatures`, `task_notifications`, `gate_evaluations`, `workspaces`, `workflow_runs`, `workspace_datasources`, `declarative_pack_bundles`).
  - `20` échecs/timeouts UI (Portals/Tailwind, `4` wrappers `display: none`, `/catalog` vs `/agents`, `/help` dupliqué, `data-testid` désynchronisés, bouton invitation absent).
  - `8` rejets HTTP inattendus (`404` Permission Broker, `403` Gates & Réflexif, `422` Triggers `SecretInputPayload`).
  - `51 / 62` capacités `feature` en `failed_e2e` (`11` en `runtime`, `3` `foundation` en `runtime`).
- **Opportunités de Factorisation & Résorption de Dette Technique** :
  - Factoriser 100 % des modales sur une primitive unique `OrciaDialog` (`DialogPrimitive.Portal`) avec 3 zones flex (`header / body scrollable / footer sticky`).
  - Factoriser le résolveur d'identité/appartenance Workspace sur l'`UUIDv7` réel PG18 (suppression définitive de `"ws-1"` et de tous les contournements `ws-\d+`).
  - Découper les composants dépassant `300–400` lignes lors des vagues `22-2` à `22-7` (ex. `platformSetupStore.tsx`, `FourZoneDirectionCShell.tsx`, `features/workspaces/index.tsx`, `features/catalog/index.tsx`, `features/cockpit/index.tsx`).
  - Aucun nouveau code applicatif écrit dans Story 21.9 : toute l'implémentation est structurée en **8 Stories `22.1`..`22.8`** dans `epics.md` et `sprint-status.yaml`.

---

## 2. Plan d'Implémentation (Story 21.9 — Gouvernance Documentaire & Initialisation Epic 22)

### 2.1 Schéma de Données & Migrations Alembic (`infra/migrations/versions/`)
- Aucune migration Alembic appliquée en Story 21.9 (`doc` uniquement). Les tables PG18 ciblées par l'Epic 22 (`workspaces`, `workspace_memberships`, `workspace_datasources`, `assistant_folders`, `assistant_threads`, `assistant_folder_shares`, `task_notifications`, `resource_leases`, `permission_broker_tickets`, `permission_broker_policies`, `human_anchor_signatures`, `upstream_challenges`, `run_lock_manifests`, `gate_evaluations`, `chunk_approvals`, `declarative_pack_bundles`, `wizard_sessions`, `workflow_runs`) existent déjà dans le schéma courant (`0001`..`20261117_*`) et sont documentées dans les rapports `22-1` à `22-5`.

### 2.2 Noyau Métier Hexagonal, Orchestration & Workers (`packages/orcia-core/`, `apps/worker/`)
- Planification exacte des adaptateurs et services à raccorder dans les rapports `22-1`, `22-3`, `22-4` et `22-5` :
  - `22-1` : `MatrixPermissionEvaluator`, `_bootstrap_evaluator_sync.py`, purge `ORCIA_DISABLE_PG_BOOTSTRAP_SYNC`.
  - `22-3` : adaptateurs SQL PG18 pour `AssistantFoldersAndSharingService` (et retrait fuite `LAYER_5`), `SqlTaskNotificationRepository` + `SqlResourceLeaseRepository`, `SqlPermissionBrokerRepository` + politique fallback `git://*`.
  - `22-4` : initialisation `dbos_uow` dans `core_and_lifespan.py`, extension `sql_repository.py` (`human_anchor_signatures`, `upstream_challenges`, `run_lock_manifests`), `SqlGateEvaluationRepository`, garde `AND status <> 'KILL_SWITCH_STOPPED'` dans `_sql_autonomous_rollback.py`.
  - `22-5` : upsert `declarative_pack_bundles` au bootstrap/export et persistance `wizard_sessions` dans `DurableOnboardingWizardService`.

### 2.3 Couche Backend API, Sécurité & Contrats (`apps/api/`, `packages/api-client/`)
- Planification détaillée dans `22-1`..`22-8` : suppression des contournements `ws-\d+`, exposition propre des DTO sans balise prompt interne, unification `SecretInputPayload.plaintext_value` avec `@orcia/api-client`, traduction systématique des erreurs RFC 9457 et garde CI Python `test_no_raw_enum_codes_in_ui_streams.py`.

### 2.4 Interface Utilisateur & Expérience (`packages/ui/`, `apps/web/`)
- Planification détaillée dans `22-2`, `22-6`, `22-7`, `22-8` :
  - `22-2` : activation `@tailwindcss/vite`, Portals `OrciaDialog`, purge `display: none`, découplage `/catalog` vs `/agents` et Zone 4 sur `/help`, action invitation `/organization`, alignement `data-testid` (`llm-provider-preset-ollama`, `studio-view-mode-whatif`).
  - `22-6` : Sidebar `8` entrées (`DESIGN.md`), Double Sélecteur + Breadcrumb, Mobile Companion `< 768 px`, catalogue `docs/help/{fr,en}/*.md` dynamique par route sans `Chef1`/`aqwZSX`, Cockpit `<= 3` blocs sans `LOCK TABLE...`.
  - `22-7` : compteurs `0` masqués, modales `+ Nouveau...`, bannières RFC 9457 actionnables, grilles `4-col`/`2×2`, studio V2, devise `€` / dates FR, retrait `(!)` des boutons primaires et purge intégrale du jargon `i18n`/SSE.

### 2.5 Analyse d'Impact sur la Pyramide des Tests (`AD-17` & Artefacts Story 21.9)
- **Production documentaire (`21.9-impl`)** :
  1. `docs/implementation-artifacts/tech-lead-reports/21-9-rapports-tech-lead-echecs-et-initialisation-epic-22-tech-lead-report.md` (présent rapport).
  2. `8` rapports Tech Lead pré-implémentation : `docs/implementation-artifacts/tech-lead-reports/22-1-*.md` .. `22-8-*.md`.
  3. Plan Directeur Global : `docs/planning-artifacts/sprint-change-proposal-2026-11-18-epic-22-remediation-plan.md` (avec `3` matrices exhaustives de traçabilité : `14` specs / `47` cas $\rightarrow$ `REM-*` $\rightarrow$ `22.k` ; `REM-01..REM-34` $\rightarrow$ `22.k` ; `51 CAP-*` `failed_e2e` $\rightarrow$ `22.k`).
  4. Mise à jour de `docs/planning-artifacts/epics.md` (`Epic 22` + `Stories 22.1..22.8` avec `Given/When/Then`), `docs/implementation-artifacts/sprint-status.yaml`, `docs/product/capabilities.yaml` (`0` `"epic-22"` générique résiduel) et `docs/implementation-artifacts/tech-lead-reports/README.md`.
- **Vérification automatique (`21.9-test`)** :
  - Création de `tests/unit/test_epic21_to_epic22_traceability.py` vérifiant à `100 %` l'absence de tout `REM-*`, spec en échec, ou `CAP-*` `failed_e2e` orphelin, la présence des `8` rapports et la cohérence `epics.md` ↔ `sprint-status.yaml` ↔ `capabilities.yaml`.
  - Exécution de `.venv/bin/pytest tests/unit/test_epic21_to_epic22_traceability.py`, `.venv/bin/ruff check tests/unit/test_epic21_to_epic22_traceability.py`, `pnpm site:sync`, `pnpm site:check` et complétion de la Section 3 ci-dessous.

---

## 3. Bilan des Modifications & Résultats (Post-Implémentation)

### 3.1 Fichiers Développés & Modifiés
| Fichier | Nature | Description synthétique |
| :--- | :--- | :--- |
| `docs/implementation-artifacts/tech-lead-reports/21-9-rapports-tech-lead-echecs-et-initialisation-epic-22-tech-lead-report.md` | Création | Rapport Tech Lead de la Story 21.9 (`21.9-impl` Sections 1–2 ; `21.9-test` Section 3) |
| `docs/implementation-artifacts/tech-lead-reports/22-1-*.md` .. `22-8-*.md` | Création (×8) | `8` rapports Tech Lead pré-implémentation individuels de l'Epic 22 |
| `docs/planning-artifacts/sprint-change-proposal-2026-11-18-epic-22-remediation-plan.md` | Création | Plan directeur par vagues + 3 matrices de traçabilité 100 % vérifiables |
| `docs/planning-artifacts/epics.md` | Modification | Ajout `Epic 22` et `Stories 22.1..22.8` (`Given/When/Then`) + `Epic List` & `FR Coverage Map` |
| `docs/implementation-artifacts/sprint-status.yaml` | Modification | Ajout `epic-22` + `22-1..22-8` (`ready-for-dev`), puis clôture `21-9: done` et `epic-21: done` (`last_updated: 11-18-2026 11:18`) |
| `docs/product/capabilities.yaml` | Modification | Remplacement des `51` `e2e_remediation_ref: "epic-22"` par les clés exactes `22-k-<slug>` (`0` `"epic-22"` résiduel) |
| `docs/implementation-artifacts/tech-lead-reports/README.md` | Modification | Indexation et mise à jour des rapports `21-9` et `22-1`..`22-8` |
| `tests/unit/test_epic21_to_epic22_traceability.py` | Création (`21.9-test`) | Suite de traçabilité (`168` lignes, `5` tests unitaires sans trace `epic`/`story`/`ac`/`uj` dans les noms `def test_*`) vérifiant les livrables (`110` lignes `manifest.jsonl`), `14/14` specs en échec, `34/34` `REM-01..REM-34`, `51/51` `CAP-*` `failed_e2e` et `8/8` clés `22-*` |
| `apps/web/src/generated/orciaSiteManifest.ts` & `docs/site-catalog/index.html` | Régénération | Synchronisation finale `pnpm site:sync` (`180` rapports, `28` routes, `133` primitives UI, `65/65` capacités live) |

### 3.2 Résultats Chiffrés, Métriques & Qualité
- **Traçabilité & Registre (`pytest`)** : `.venv/bin/pytest tests/unit/test_epic21_to_epic22_traceability.py tests/unit/test_uj_e2e_coverage_gate.py tests/unit/test_capabilities_registry.py tests/unit/test_uj_prd_experience_consistency.py tests/unit/test_e2e_query_db_readonly.py tests/unit/test_site_catalog_sync.py` $\rightarrow$ **`75 passed` en `3.14 s`** (`0` échec).
- **Synchronisation site & registre (`pnpm site:sync && pnpm site:check`)** : **`0` erreur** — `180` rapports Tech Lead indexés, `28` routes actives, `133` primitives `@orcia/ui`, `65/65` capacités live (`14` vérifiées `runtime` dont `11` `feature` + `3` `foundation`, `51` en `failed_e2e` toutes rattachées aux clés `22-*`), `62/62` E2E fonctionnels, `20/20` User Journeys couverts.
- **Qualité statique Python & Architecture** :
  - `.venv/bin/ruff check ...` : **`All checks passed!`** (`0` erreur)
  - `.venv/bin/ruff format --check ...` : **`24 files already formatted`** (`0` écart)
  - `MYPYPATH=infra/scripts:infra/scripts/e2e .venv/bin/mypy --strict infra/scripts/*.py infra/scripts/e2e/query_db.py` : **`Success: no issues found in 8 source files`**
  - `.venv/bin/lint-imports` : **`Contracts: 5 kept, 0 broken`** (`561 files, 4002 dependencies`)
  - `.venv/bin/python .agent/skills/bmad-architecture/scripts/lint_spine.py --workspace docs/planning-artifacts/architecture/architecture-ORCIA-2026-10-24` : **`"ok": true, "total_findings": 0`**
  - `.venv/bin/detect-secrets-hook --baseline .secrets.baseline tests/unit/test_epic21_to_epic22_traceability.py` : **`0` secret détecté** (code `0`)
  - `gitnexus:detect_changes(repo="/home/romain/Documents/Projects/ORCIA", scope="all")` : **`risk_level: "low"`, `changed_count: 0`, `affected_count: 0`, `changed_files: 4`**
- **Monorepo TypeScript (`pnpm turbo run lint typecheck test`)** : **`9 successful, 9 total`** en `30.523s` (dont `@orcia/web`: `38` test files, `153 passed`; `@orcia/api-client`: `2` test files, `13 passed`; `@orcia/ui`: cache hit vert).

### 3.3 Validation & Procédure de Test sur Toute la Pyramide (`AD-17`)
- **Couche 1 (Unitaires & Gouvernance)** : `75 passed` sur la suite de traçabilité `Epic 21 -> Epic 22`, couverture UJ/E2E, registre des capacités, cohérence PRD/EXPERIENCE, `query_db` lecture seule et synchronisation `/showcase`, complétés par `pnpm turbo run lint typecheck test` (`9/9` tâches vertes).
- **Couches 2, 3, 4 & Sécurité** : aucune modification de code applicatif Python/TypeScript dans la Story 21.9 (`doc` + test unitaire de traçabilité uniquement) ; intégrité architecture/contrats validée à `0` défaut via `lint-imports` (`5/5`), `lint_spine.py` (`0` finding), `mypy --strict` (`0` erreur) et `detect-secrets-hook` (`0` finding).
- **Couche 5 (Playwright E2E)** : campagne de référence `Story 21.8` archivée (`playwright-results.json`, `manifest.jsonl` `110` entrées, `110/110` PNG, `47` échecs/timeouts sur `14` specs intégralement rattachés aux Stories `22.1..22.8`). Clôture officielle de `21-9` et `epic-21` à `done` dans `sprint-status.yaml`, suivie de `pnpm site:sync && pnpm site:check` (`0` erreur).
