# Story 22.4 — Persistance PG18 Orchestration (`dbos_uow`, `human_anchor_signatures`, `upstream_challenges`, `run_lock_manifests`), Gates (`gate_evaluations`, `chunk_approvals`) & Garde `KILL_SWITCH_STOPPED`

> **Convention de nommage du fichier (Obligatoire — à créer AVANT toute modification de code)** :
> - User Story du sprint : `docs/implementation-artifacts/tech-lead-reports/{story-key}-tech-lead-report.md`

- **Date** : 2026-11-18
- **Story / Clé Sprint** : `22-4-persistance-pg18-orchestration-gates-et-garde-kill-switch` (`Epic 22` — Vague 1)
- **Capacité(s)** : `CAP-020`, `CAP-021`, `CAP-023`, `CAP-024`, `CAP-030`, `CAP-031`, `CAP-032`, `CAP-033`, `CAP-201` (ancrages `failed_e2e` sur `22-4`) — classification : `feature`
- **Auteur / Contexte** : `bmad-architect-worker` (initialisation pré-implémentation Story 21.9) — Résolution des chantiers **`REM-09`**, **`REM-11`** et **`REM-12`** (`synthese-remediation-sally-winston-epic-21.md`). Couvre `FR-4`, `FR-5`, `FR-6`, `FR-7`, `FR-11`, `FR-12`, `FR-14`, `FR-15`, `FR-16`, `FR-17`, `FR-18`, `FR-19`, `FR-24`, `FR-29`, `FR-30`, `AD-2`, `AD-3`, `AD-7`, `AD-9`, `AD-10`, `AD-11`, `AD-13`, `AD-18`, `UX-DR3`, `UX-DR4`, `UX-DR5`, `UX-DR6`, `UX-DR7`, `UX-DR10`, `UX-DR17`, `UJ-1`, `UJ-2`, `UJ-3`, `UJ-5`, `UJ-6`, `UJ-11`, `UJ-12`.
- **Commits associés** : `En attente d'implémentation (initialisé sur 575cf4a)`

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
- **Tables PostgreSQL 18 concernées** : `workflow_runs`, `step_executions`, `blackboard_snapshots` (append-only `BEFORE UPDATE OR DELETE RAISE EXCEPTION`), `run_lock_manifests`, `human_anchor_signatures` (`0015`), `human_arbitration_requests` (`0015`), `upstream_challenges` (`0016`), `gate_evaluations` (`0017`), `chunk_approvals` (`0018`), `autonomous_post_hoc_audits` (`20261117_*`), `domain_events_outbox` (`0012`).
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
- Monter `<UpstreamChallengeRewindModal>` dans la section Gouvernance / Vue Fokus de Revue (`CockpitHumanLedGovernanceSection.tsx` et `/gates`) via `@orcia/api-client`, avec `OrciaDialog` Portal, aperçu d'impact *What-If* et déclenchement du Replay Step N (`REM-09`).
- Séparer strictement `/gates` (`Briefing 4 blocs` + `ChunkValidationCard` + actions Jira Staged) de `/processes` (`Mes Processus`) afin que l'ouverture de `/gates` ne rende pas l'écran `Mes Processus` ni son formulaire géant (`REM-11`).

### 2.5 Analyse d'Impact sur la Pyramide des Tests (`AD-17` — Couches 1 à 5 + Sécurité, Obligatoire)
- **Couche 1a / 1b** : tests unitaires de la garde `status <> 'KILL_SWITCH_STOPPED'`, du calcul `chunk_approvals` / `< 15 s`, du montage `UpstreamChallengeRewindModal` et de la séparation `/gates`.
- **Couche 2 (`HTTP ➔ PG18`)** : `POST /anchors/sign` $\rightarrow$ `SELECT human_anchor_signatures` ; `POST /challenges` $\rightarrow$ `SELECT upstream_challenges` ; `POST /gates/human/...` $\rightarrow$ `SELECT gate_evaluations, chunk_approvals` ; `POST /emergency-stop` + `POST /invalidate-and-restore` $\rightarrow$ `SELECT workflow_runs` vérifiant le maintien de `KILL_SWITCH_STOPPED`.
- **Couche 3 (`OpenAPI 0-diff`, `lint-imports`)** : validation `5 contracts kept, 0 broken` et zéro fuite SQLAlchemy hors `_internal/`.
- **Couche 4 (Evals)** : orthogonalité modèle générateur/juge (`evaluator_model_family != executor_model_family`) sur `DeterministicCassetteLLM`.
- **Couche Sécurité** : rejet `422 ERR_HUMAN_ANCHOR_REQUIRED` pour identités agentiques, rejet `403 ERR_OBSERVER_MODE_READ_ONLY` sur mutations d'ancres/challenges/gates/kill-switch.
- **Couche 5 (Playwright E2E)** : passage au vert visé de `03-human-led`, `06-gates`, `13-epic-7` et `19-orchestration` (#1 & #2).

---

## 3. Bilan des Modifications & Résultats (Post-Implémentation)

> *[En attente d'implémentation de la Story 22.4]*

### 3.1 Fichiers Développés & Modifiés
| Fichier | Nature (Création / Modification / Refactoring) | Description synthétique |
| :--- | :--- | :--- |
| `packages/orcia-core/src/orcia_core/orchestration/_internal/_sql_autonomous_rollback.py` | Modification | *[À compléter après implémentation]* |
| `packages/orcia-core/src/orcia_core/gates/_internal/sql_gate_repository.py` | Création | *[À compléter après implémentation]* |
| `apps/api/src/orcia_api/dependencies/core_and_lifespan.py` & `routers/*` | Modification | *[À compléter après implémentation]* |
| `apps/web/src/features/cockpit/*` & `gates/*` | Modification | *[À compléter après implémentation]* |

### 3.2 Résultats Chiffrés, Métriques & Qualité
- **Couverture de tests** : *[$\ge 90\%$ requis à mesurer après implémentation]*
- **Qualité statique & Architecture** : `ruff`, `mypy --strict`, `pnpm typecheck`, `lint-imports`, `lint_spine.py`, `gitnexus_detect_changes()` *[À compléter]*

### 3.3 Validation & Procédure de Test sur Toute la Pyramide (`AD-17`)
- *[À compléter après exécution des 5 couches `AD-17` et Playwright Desktop/Mobile]*
