# Story 22.4 — Persistance PG18 Orchestration (`dbos_uow`, `human_anchor_signatures`, `upstream_challenges`, `run_lock_manifests`), Gates (`gate_evaluations`, `chunk_approvals`) & Garde `KILL_SWITCH_STOPPED`

> **Convention de nommage du fichier (Obligatoire — à créer AVANT toute modification de code)** :
> - User Story du sprint : `docs/implementation-artifacts/tech-lead-reports/{story-key}-tech-lead-report.md`

- **Date** : 2026-11-18
- **Story / Clé Sprint** : `22-4-persistance-pg18-orchestration-gates-et-garde-kill-switch` (`Epic 22` — Vague 1)
- **Capacité(s)** : `CAP-020`, `CAP-021`, `CAP-023`, `CAP-024`, `CAP-030`, `CAP-031`, `CAP-032`, `CAP-033`, `CAP-201` (ancrages `failed_e2e` sur `22-4`) — classification : `feature`
- **Auteur / Contexte** : `bmad-architect-worker` (initialisation pré-implémentation Story 21.9) — Résolution des chantiers **`REM-09`**, **`REM-11`** et **`REM-12`** (`synthese-remediation-sally-winston-epic-21.md`). Couvre `FR-4`, `FR-5`, `FR-6`, `FR-7`, `FR-11`, `FR-12`, `FR-14`, `FR-15`, `FR-16`, `FR-17`, `FR-18`, `FR-19`, `FR-24`, `FR-29`, `FR-30`, `AD-2`, `AD-3`, `AD-7`, `AD-9`, `AD-10`, `AD-11`, `AD-13`, `AD-18`, `UX-DR3`, `UX-DR4`, `UX-DR5`, `UX-DR6`, `UX-DR7`, `UX-DR10`, `UX-DR17`, `UJ-1`, `UJ-2`, `UJ-3`, `UJ-5`, `UJ-6`, `UJ-11`, `UJ-12`.
- **Commits associés** : `En cours de clôture (Commit A gouvernance RCA : fd5d146 ; Commit B Story 22.4 à la suite)`

---

## 1. Analyse du Besoin & Étude d'Impact Tech Lead (Pré-Implémentation)

### 1.1 Contexte & Problématique
- **Silo RAM Orchestration, `dbos_uow = None` & `UpstreamChallengeRewindModal` non monté (`REM-09`, `4` échecs)** :
  - `app.state.dbos_uow` et `app.state.dbos_datasource` ne sont jamais initialisés dans `core_and_lifespan.py` (`resolve_optional_dbos_uow` retourne `None`).
  - `blackboard_and_engine.py:164-196` (`sign_human_anchor`) passe `snapshot=None` à `sync_step_execution_and_snapshot_to_sql`, et `orcia_core/orchestration/_internal/sql_repository.py` n'a aucune méthode SQL pour persister ou relire `human_anchor_signatures`, `upstream_challenges` et `run_lock_manifests`.
  - `orchestration.py:203-220` (`get_orchestration_state`) lit exclusivement en RAM et `challenge_and_replay.py:132-158` (`submit_upstream_challenge`) n'écrit pas en PG18.
  - Côté UI, `UpstreamChallengeRewindModal` (`packages/ui`) n'est importé nulle part dans `apps/web/src/` (`upstream-challenge-reason-input` introuvable dans `19-orchestration` #1).
- **Silo RAM des Gates (`gate_evaluations` & `chunk_approvals`) + superposition `/gates` (`REM-11`, `3` échecs)** :
  - `routers/gates.py:117-121,171,357` et `routers/human_gates.py:105,129,169,195,229` délèguent intégralement à `bootstrap_svc.gate_service` / `human_service` en mémoire pure.
  - Visuellement dans `06-gates`, l'URL `/gates` rend la page `Mes Processus` et son formulaire géant permanent au lieu de la Vue Fokus / Briefing 4 blocs et validation par découpage.
- **Écrasement de `KILL_SWITCH_STOPPED` lors du rollback post-hoc (`REM-12`, `1` échec)** :
  - Dans `_sql_autonomous_rollback.py:44-48`, `restore_help_article_and_rollback_run_sql` exécute `UPDATE workflow_runs SET status = 'ROLLED_BACK' WHERE id = :run_id` **sans garde `AND status <> 'KILL_SWITCH_STOPPED'`** (à l'opposé de `sql_autonomous_supervision.py:202`). Dans `13-epic-7`, le kill-switch et le rollback post-hoc finissent par cibler le même `run_id`, effaçant `KILL_SWITCH_STOPPED` de `workflow_runs`!
- **Échecs E2E associés & captures PNG archivées (`8` échecs E2E)** :
  - `03-human-led-anchor-and-arbitration.spec.ts` (`2` fails Desktop + Mobile) : [Desktop](../e2e-campaign-epic-21/screenshots/03-human-led-anchor-and-arbitration/desktop-cockpit--signature-de-l-ancrage-violet-30-car-rejet-agent-422-arbitrage-motive-et-survie-au-f5--failed.png) · [Mobile](../e2e-campaign-epic-21/screenshots/03-human-led-anchor-and-arbitration/mobile-companion--signature-de-l-ancrage-violet-30-car-rejet-agent-422-arbitrage-motive-et-survie-au-f5--failed.png)
  - `06-gates-review-and-anti-rubber-stamping.spec.ts` (`1` fail Desktop) : [Desktop](../e2e-campaign-epic-21/screenshots/06-gates-review-and-anti-rubber-stamping/desktop-cockpit--inspection-du-bloc-4-approbation-par-decoupage-garde-fou-15-s-action-jira-et-survie-f5--failed.png)
  - `13-epic-7-autonomous-governance-and-supervision.spec.ts` (`1` fail Desktop) : [Desktop](../e2e-campaign-epic-21/screenshots/13-epic-7-autonomous-governance-and-supervision/desktop-cockpit--bureau-publication-v2-contrat-declencheur-supervision-processes-arret-d-urgence-f5-finop--failed.png)
  - `19-orchestration-whatif-replay-and-gates.spec.ts` (`4` fails : #1 Desktop/Mobile + #2 Desktop/Mobile) : [#1 Desktop](../e2e-campaign-epic-21/screenshots/19-orchestration-whatif-replay-and-gates/desktop-cockpit--instanciation-depuis-le-cockpit-ancrage-humain-contestation-amont-avec-reprise-et-survie--failed.png) · [#1 Mobile](../e2e-campaign-epic-21/screenshots/19-orchestration-whatif-replay-and-gates/mobile-companion--instanciation-depuis-le-cockpit-ancrage-humain-contestation-amont-avec-reprise-et-survie--failed.png) · [#2 Desktop](../e2e-campaign-epic-21/screenshots/19-orchestration-whatif-replay-and-gates/desktop-cockpit--validation-deterministe-sandbox-validation-agentique-orthogonale-revue-humaine-par-decou--failed.png) · [#2 Mobile](../e2e-campaign-epic-21/screenshots/19-orchestration-whatif-replay-and-gates/mobile-companion--validation-deterministe-sandbox-validation-agentique-orthogonale-revue-humaine-par-decou--failed.png)

### 1.2 Exploration, Analyse d'Impact GitNexus, Factorisation & Dette Technique
- **Analyse d'Impact GitNexus (`repo: "/home/romain/Documents/Projects/ORCIA"`)** :
  - `UpstreamChallengeRewindModal` (`packages/ui/src/primitives/UpstreamChallengeRewindModal.tsx:75-440`) : **`0` import applicatif** dans `apps/web/src/` (orphelin UI malgré `impactedCount: 281` au graphe de ré-export global `@orcia/ui`).
  - `AdaptiveHumanGateService` (`packages/orcia-core/src/orcia_core/gates/human.py:161-438`) : **`impactedCount: 11`**, risque **`LOW`** (`direct: 2`: `gates/__init__.py`, `deterministic.py` ; `d=2: 4`, `d=3: 5`).
  - `restore_help_article_and_rollback_run_sql` (`packages/orcia-core/src/orcia_core/orchestration/_internal/_sql_autonomous_rollback.py:22-185`) : **`impactedCount: 281`** (`direct: 118`, `processes_affected: 33`), risque **`CRITICAL`**.
- **Tables PostgreSQL 18 concernées** : `workflow_runs`, `step_executions`, `blackboard_snapshots` (append-only `BEFORE UPDATE OR DELETE RAISE EXCEPTION`), `run_lock_manifests`, `human_anchor_signatures` (`0015`), `human_arbitration_requests` (`0015`), `upstream_challenges` (`0016`), `gate_evaluations` (`0017`), `chunk_approvals` (`0018`, `0026`), `autonomous_post_hoc_audits` (`20261117_*`), `domain_events_outbox` (`0012`).
- **Précisions d'analyse pré-implémentation** :
  - `resolve_optional_dbos_uow` / `DbosSqlAlchemyUnitOfWork.from_engine` : `app_lifespan` initialise `app.state.dbos_uow` + `app.state.dbos_datasource` via `DbosSqlAlchemyUnitOfWork.create`, tandis que `initialize_app_services` et `resolve_optional_dbos_uow` assurent un repli immédiat via `DbosSqlAlchemyUnitOfWork.from_engine(db_engine)` si `app_lifespan` n'a pas été exécuté.
  - Intégrité référentielle PG18 : création/résolution idempotente des parents (`workspaces`, `workflow_definitions`, `workflow_runs`, `step_executions`, `users`) avant toute écriture dans `human_anchor_signatures`, `upstream_challenges`, `gate_evaluations` et `chunk_approvals` (y compris la FK `human_anchor_signature_id` lors des co-éditions `CO_EDIT`).
  - `_sql_autonomous_rollback.py` : lors d'un rollback post-hoc sur un run déjà stoppé d'urgence (`KILL_SWITCH_STOPPED`), la clause `AND status <> 'KILL_SWITCH_STOPPED'` bloque la mutation de `workflow_runs.status`, tout en lisant la ligne existante pour tracer `INVALIDATED_ROLLED_BACK` dans `autonomous_post_hoc_audits` et restaurer l'article `@v(N-1)` sans jamais écraser `KILL_SWITCH_STOPPED`.
- **Opportunités de Factorisation & Volumétrie** :
  - Centraliser les requêtes PG18 des ancres/challenges/manifests dans un sous-module `_internal/_sql_orchestration_governance.py` (`< 350` lignes) afin de ne pas gonfler `sql_repository.py`.
  - Créer un composant Vue Fokus / Revue dédié partagé entre `/gates` et la revue depuis `/cockpit` (`UpstreamChallengeRewindModal` + `CognitiveReviewBriefingGrid` + `ChunkValidationCard`).

---

## 2. Plan d'Implémentation

### 2.1 Schéma de Données & Migrations Alembic (`infra/migrations/versions/`)
- Toutes les tables cibles (`workflow_runs`, `step_executions`, `blackboard_snapshots`, `run_lock_manifests`, `human_anchor_signatures`, `human_arbitration_requests`, `upstream_challenges`, `gate_evaluations`, `chunk_approvals`, `autonomous_post_hoc_audits`) existent déjà.
- Respect strict du trigger *Append-Only* sur `blackboard_snapshots` et `audit_ledger` : les replay/rewind marquent l'ancienne branche `SUPERSEDED` sans jamais muter les snapshots `COMMITTED` antérieurs, ou utilisent la colonne prévue à cet effet selon l'invariant `AD-2`.

### 2.2 Noyau Métier Hexagonal, Orchestration & Workers (`packages/orcia-core/`, `apps/worker/`)
- **DBOS UoW & Orchestration PG18 (`REM-09`)** :
  - Étendre `orcia_core/orchestration/_internal/` pour persister et relire `human_anchor_signatures`, `human_arbitration_requests`, `upstream_challenges`, `run_lock_manifests`, `workflow_runs`, `step_executions` et `blackboard_snapshots`.
  - Garantir que `sign_human_anchor` écrit immédiatement en base dans la même Unit of Work sans attendre `snapshot != None`.
- **Gates PG18 (`REM-11`)** :
  - Implémenter `orcia_core/gates/_internal/sql_gate_repository.py` (`SqlGateEvaluationRepository`) pour `gate_evaluations` (déterministes, agentiques, humaines) et `chunk_approvals`, avec conservation de l'anti-rubber-stamping `< 15 s` et de l'exécution Jira Staged.
- **Garde `KILL_SWITCH_STOPPED` (`REM-12`)** :
  - Dans `_sql_autonomous_rollback.py:44-48`, ajouter `AND status <> 'KILL_SWITCH_STOPPED'` sur `UPDATE workflow_runs` (et tracer le statut de restauration d'artefact dans `autonomous_post_hoc_audits` sans jamais effacer `KILL_SWITCH_STOPPED`).

### 2.3 Couche Backend API, Sécurité & Contrats (`apps/api/`, `packages/api-client/`)
- `apps/api/src/orcia_api/dependencies/core_and_lifespan.py` : initialiser réellement `app.state.dbos_uow` / `AsyncSQLAlchemyDatasource` + `SqlGateEvaluationRepository` au démarrage FastAPI et injecter dans `orchestration.py`, `blackboard_and_engine.py`, `challenge_and_replay.py`, `gates.py` et `human_gates.py`.
- `GET /api/v1/orchestration/runs/{id}` (`get_orchestration_state`, `orchestration.py:203-220`) : relire depuis PG18 (survie totale au redémarrage API et au `F5`).
- `POST /api/v1/challenges` (`submit_upstream_challenge`, `challenge_and_replay.py:132-158`) : persister `upstream_challenges` + créer nouvelle branche `ACTIVE` de snapshots au replay.
- `13-epic-7` (`autonomous_supervision.py`) : s'assurer que le kill-switch et le rollback post-hoc ciblent des runs distincts sans collision d'état.

### 2.4 Interface Utilisateur & Expérience (`packages/ui/`, `apps/web/`)
- Monter `<UpstreamChallengeRewindModal>` dans la section Gouvernance / Vue Fokus de Revue (`CockpitHumanLedGovernanceSection.tsx` avec mode `inline` non bloquant afin de ne pas masquer `ArbitrationTieBreakCard`, et modale Radix Portal depuis `/gates` lors d'une contestation de section) via `@orcia/api-client`, avec aperçu d'impact *What-If* dynamique et déclenchement du Replay Step N (`REM-09`).
- Séparer strictement `/gates` (`GatesAdaptiveHumanReviewSection` : Briefing 4 blocs + `ChunkValidationCard` + actions Jira Staged + `UpstreamChallengeRewindModal`) de `/processes` (`Mes Processus`) : déplacer `OrciaDocumentationProcessCard`, `SimplifiedProcessBuilderSection`, `PackBuilderProcessesStudioView` et `HelpArticleGeneratorAndValidatorView` hors de `features/gates/index.tsx` vers `features/processes/ProcessStudioAndPackAuthoringSection.tsx` (monté sur `/settings/packs`) (`REM-11`).

### 2.5 Analyse d'Impact sur la Pyramide des Tests (`AD-17` — Couches 1 à 5 + Sécurité, Obligatoire)
- **Couche 1a / 1b** : tests unitaires de la garde `status <> 'KILL_SWITCH_STOPPED'`, du calcul `chunk_approvals` / `< 15 s`, du montage `UpstreamChallengeRewindModal` et de la séparation `/gates`.
- **Couche 2 (`HTTP ➔ PG18`)** : `POST /anchors/sign` $\rightarrow$ `SELECT human_anchor_signatures` ; `POST /challenges` $\rightarrow$ `SELECT upstream_challenges` ; `POST /gates/human/...` $\rightarrow$ `SELECT gate_evaluations, chunk_approvals` ; `POST /emergency-stop` + `POST /invalidate-and-restore` $\rightarrow$ `SELECT workflow_runs` vérifiant le maintien de `KILL_SWITCH_STOPPED`.
- **Couche 3 (`OpenAPI 0-diff`, `lint-imports`)** : validation `5 contracts kept, 0 broken` et zéro fuite SQLAlchemy hors `_internal/`.
- **Couche 4 (Evals)** : orthogonalité modèle générateur/juge (`evaluator_model_family != executor_model_family`) sur `DeterministicCassetteLLM`.
- **Couche Sécurité** : rejet `422 ERR_HUMAN_ANCHOR_REQUIRED` pour identités agentiques, rejet `403 ERR_OBSERVER_MODE_READ_ONLY` sur mutations d'ancres/challenges/gates/kill-switch.
- **Couche 5 (Playwright E2E)** : passage au vert visé de `03-human-led`, `06-gates`, `13-epic-7` et `19-orchestration` (#1 & #2).

---

## 3. Bilan des Modifications & Résultats (Post-Implémentation)

### 3.1 Fichiers Développés & Modifiés
| Fichier | Nature (Création / Modification / Refactoring) | Description synthétique |
| :--- | :--- | :--- |
| `packages/orcia-core/src/orcia_core/orchestration/_internal/uow.py` & `__init__.py` | Modification | Ajout `DbosSqlAlchemyUnitOfWork.from_engine` & ré-export des adaptateurs SQL d'ancres/arbitrages/challenges/runs. |
| `packages/orcia-core/src/orcia_core/orchestration/_internal/_sql_orchestration_governance.py` | Création | Persistance et relecture PG18 des `human_anchor_signatures`, `human_arbitration_requests`, `workflow_runs` & `run_lock_manifests`. |
| `packages/orcia-core/src/orcia_core/orchestration/_internal/_sql_orchestration_challenges.py` | Création | Persistance et relecture PG18 de `upstream_challenges` & synchronisation de statut `REPLAYED`. |
| `packages/orcia-core/src/orcia_core/orchestration/_internal/_sql_orchestration_parents.py` | Création | Résolution / création idempotente des parents FK (`org_units`, `workspaces`, `workflow_definitions`, `users`). |
| `packages/orcia-core/src/orcia_core/orchestration/_internal/_sql_autonomous_rollback.py` | Modification | Garde stricte `AND status <> 'KILL_SWITCH_STOPPED'` sur `UPDATE workflow_runs` lors du rollback post-hoc, avec préservation `autonomous_post_hoc_audits`. |
| `packages/orcia-core/src/orcia_core/orchestration/autonomous_supervision.py` & `_autonomous_supervision_ops.py` | Modification | Propagation du statut conservé `KILL_SWITCH_STOPPED` lors de `invalidate_and_restore` après arrêt d'urgence. |
| `packages/orcia-core/src/orcia_core/blackboard/store.py` | Modification | Ajout de `hydrate_snapshot` pour réhydratation à froid des snapshots `ACTIVE`/`SUPERSEDED` sans altérer l'append-only. |
| `packages/orcia-core/src/orcia_core/gates/_internal/sql_gate_repository.py`, `_sql_gate_human_queries.py`, `_sql_gate_mappers.py`, `_sql_gate_parents.py`, `__init__.py` | Création | `SqlGateEvaluationRepository` PG18 pour `gate_evaluations` (DETERMINISTIC/AGENTIC/HUMAN) et `chunk_approvals` (+ FK `human_anchor_signature_id`). |
| `packages/orcia-core/src/orcia_core/gates/human.py` & `deterministic.py` | Modification | Support réhydratation / chargement depuis `SqlGateEvaluationRepository`, conservation garde `< 15 s` & co-édition `CO_EDIT`. |
| `apps/api/src/orcia_api/dependencies/core_and_lifespan.py` & `_core_providers.py` | Modification | Initialisation réelle `app.state.dbos_uow` / `dbos_datasource` / `gate_repository` dans `app_lifespan` & `initialize_app_services` (0 singleton d'import). |
| `apps/api/src/orcia_api/routers/_orchestration_sql_hydration.py` & `_orchestration_sql_serializers.py` | Création | Helpers modulaires `< 130` L de réhydratation PG18 (`resolve_optional_dbos_uow`, `hydrate_orchestration_runs_from_sql`, `hydrate_run_from_sql_if_missing`). |
| `apps/api/src/orcia_api/routers/orchestration_sql_wiring.py`, `orchestration.py`, `blackboard_and_engine.py`, `challenge_and_replay.py`, `gates.py`, `human_gates.py` | Modification | Câblage PG18 complet des mutations et lectures (ancres, arbitrages, challenges/replays, runs, gates déterministes/agentiques/humaines). |
| `packages/ui/src/primitives/UpstreamChallengeRewindModal.tsx` | Modification | Support bimodal `inline` non bloquant et modale Radix Portal (`DialogPrimitive.Portal`) accessible RGAA. |
| `apps/web/src/features/cockpit/CockpitUpstreamChallengePanel.tsx`, `cockpitGovernanceHelpers.ts`, `CockpitHumanLedGovernanceSection.tsx`, `index.tsx` | Création / Modification | Montage de `UpstreamChallengeRewindModal` (inline + bouton Radix Portal) avec prévisualisation *What-If*, replay et réhydratation `[STALE_WARNING]` au `F5`. |
| `apps/web/src/features/gates/GatesAdaptiveHumanReviewSection.tsx`, `GatesChallengeModalSection.tsx`, `index.tsx` | Modification / Création | Séparation stricte de `/gates` (Briefing 4 blocs, découpage, Jira Staged, `GatesChallengeModalSection`) et extraction studio vers `ProcessStudioAndPackAuthoringSection.tsx` (`/settings/packs`). |
| `apps/web/src/features/processes/ProcessStudioAndPackAuthoringSection.tsx` & `apps/web/src/features/settings/packs/PacksRegistryPage.tsx` | Création / Modification | Déport des composants Studio/Packs/Help hors de `/gates` vers `/settings/packs`. |
| `tests/unit/test_orchestration_governance_gates_and_kill_switch_guard.py`, `tests/security/test_orchestration_and_gates_security_guards.py`, `tests/integration/test_orchestration_anchors_challenges_gates_postgres18.py`, `apps/web/src/__tests__/orchestration-rewind-modal-and-gates-view.test.tsx`, `i18n-and-shell.test.tsx`, `zero-dead-buttons-and-silent-catches-audit.test.tsx` | Création / Modification | Suites de tests orientées domaine (unitaires, sécurité `422`/`403`, intégration `create_app()` sans override sur PG18 réel, Vitest `<RouterProvider>` & modale Portal). |

### 3.2 Résultats Chiffrés, Métriques & Qualité
- **Couverture de tests Story `22.4` (unitaires + sécurité + intégration PG18)** : **`92 %`** (`1056` statements, `53` manqués, `256` branches, `--fail-under=90` passé — dont `_orchestration_sql_hydration.py` `100 %`, `challenge_and_replay.py` `100 %`, `human_gates.py` `99 %`, `sql_gate_repository.py` `98 %`, `autonomous_supervision.py` `98 %`, `_sql_autonomous_rollback.py` `96 %`, `_sql_gate_mappers.py` `96 %`, `_sql_gate_parents.py` `94 %`, `_sql_gate_human_queries.py` `93 %`, `gates/human.py` `91 %`, `_sql_orchestration_governance.py` `91 %`).
- **Tests Python** : **`826 passed`** (`tests/unit`, `tests/security`, `tests/evals`), **`8 passed`** sur `test_orchestration_governance_gates_and_kill_switch_guard.py`, **`1 passed`** sur `test_orchestration_and_gates_security_guards.py`, **`2 passed`** sur `tests/integration/test_orchestration_anchors_challenges_gates_postgres18.py` + `test_epics_1_7_vertical_sql_wiring_postgres18.py`.
- **Tests TypeScript / Vitest (`pnpm turbo run lint typecheck test`)** : **`9/9` tâches vertes** — `@orcia/ui` **`26/26` fichiers (`110/110` tests)**, `@orcia/api-client` **`2/2` fichiers (`13/13` tests)**, `@orcia/web` **`42/42` fichiers (`168/168` tests)** dont `orchestration-rewind-modal-and-gates-view.test.tsx` et `zero-dead-buttons-and-silent-catches-audit.test.tsx`.
- **Qualité statique & Architecture** :
  - `ruff check .` (`All checks passed!`) & `ruff format --check .` (`1185 files already formatted`).
  - `mypy --strict packages/orcia-core apps/api apps/worker` (`Success: no issues found in 504 source files`).
  - `lint-imports` (`5 contracts kept, 0 broken`).
  - `scripts/export_openapi.py --check` (`0-diff`).
  - `lint_spine.py` (`0 findings`, `ok: true`).
  - `pnpm site:sync && pnpm site:check` (`65/65` capacités live, `62/62` E2E, `20/20` UJ, `184` rapports conformes) & `scripts/check_implementation_docs.py` (`OK`).
  - `gitnexus_detect_changes({scope: "all", repo: "/home/romain/Documents/Projects/ORCIA"})` : `changed_count: 100`, `affected_count: 706`, `changed_files: 29`, `risk_level: "critical"` (impact attendu sur les flux d'orchestration et gates, couvert par la pyramide `AD-17`).

### 3.3 Validation & Procédure de Test sur Toute la Pyramide (`AD-17`)
- **Couche 1a / 1b (Unitaires & UI Vitest)** :
  - `timeout --kill-after=5s 45s .venv/bin/pytest tests/unit/test_orchestration_governance_gates_and_kill_switch_guard.py -v` (`8 passed`).
  - `pnpm turbo run lint typecheck test` (`110/110` `@orcia/ui`, `13/13` `@orcia/api-client`, `168/168` `@orcia/web` — montage Radix Portal `UpstreamChallengeRewindModal`, séparation `/gates` vs `/processes`, bannières RFC 9457 `[role="alert"]` sur HTTP `>= 400`, survie `F5`).
- **Couche 2 (`HTTP ➔ PG18` sur Composition Root réel sans override)** :
  - `timeout --kill-after=5s 180s .venv/bin/pytest tests/integration/test_orchestration_anchors_challenges_gates_postgres18.py tests/integration/test_epics_1_7_vertical_sql_wiring_postgres18.py -v` (`2 passed` — `create_app()` + `app.router.lifespan_context(app)` sans `dependency_overrides` ni `app.state.*`, `app.state.dbos_uow` et `app.state.gate_repository` initialisés, `SELECT` PG18 sur `workflow_runs`, `run_lock_manifests`, `human_anchor_signatures`, `upstream_challenges`, `blackboard_snapshots` append-only, `gate_evaluations`, `chunk_approvals`, préservation `KILL_SWITCH_STOPPED` et redémarrage à froid `app2`).
- **Couche 3 (Contrats & Architecture)** : `export_openapi.py --check` (`0-diff`), `lint-imports` (`5/5 kept`), `ruff`, `mypy --strict`, `lint_spine.py` (`0 findings`).
- **Couche Sécurité & Couche 4 (Evals)** : `test_orchestration_and_gates_security_guards.py` (`1 passed` — `422 ERR_HUMAN_ANCHOR_REQUIRED` pour `author_type="AGENT"`, `403 ERR_OBSERVER_MODE_READ_ONLY` sur toutes les mutations d'ancres/challenges/replays/gates/kill-switch) et `tests/unit tests/security tests/evals` (`826 passed`).
- **Couche 5 (Playwright E2E)** : Cohérence des `data-testid` et routes vérifiée sur `03-human-led-anchor-and-arbitration.spec.ts`, `06-gates-review-and-anti-rubber-stamping.spec.ts`, `13-epic-7-autonomous-governance-and-supervision.spec.ts` et `19-orchestration-whatif-replay-and-gates.spec.ts` (la campagne E2E intégrale sans retry `110/110` est exécutée en Vague 4 dans `Story 22.9`).
