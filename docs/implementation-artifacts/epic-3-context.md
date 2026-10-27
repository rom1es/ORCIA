# Epic 3 Context: Cockpit "Human-Led", Agent Assistant Adaptatif, Moteur d'Orchestration Durable & Sous-Workflows Fractals (`SUB_WORKFLOW <= 3`)

<!-- Compiled from planning artifacts. Edit freely. Regenerate with compile-epic-context if planning docs change. -->

## Goal

Permettre aux utilisateurs de définir et exécuter des processus métier et d'ingénierie gouvernés via Workflow-as-Code (YAML/JSON) et gabarits d'artefact multi-audiences, d'interagir avec l'Agent Concierge (`assistant-agent`) dans la Zone 2 du Cockpit Split-Screen en mode Coaching Maïeutique, Mode Tâche de Fond ou Exécution Autonome sous Contrat (`AUTONOMOUS_CONTRACT`), et de piloter des exécutions durables (`Workflow Run` et sous-workflows fractals `SUB_WORKFLOW <= 3`) adossées à un manifeste `run-lock.json` immuable et un Blackboard versionné avec ancres humaines obligatoires, synthèse d'arbitrage, téléportation de source et replay transactionnel (*Fork*).

## Stories

- Story 3.1: Workflow-as-Code YAML/JSON (`SUB_WORKFLOW <= 3` & Criticité), Gabarits d'Artefact Multi-Audience, Discipline `Intention -> Code` & Épinglage Récursif `run-lock.json`
- Story 3.2: Agent Assistant Adaptatif (`assistant-agent`), Routage d'Intention Dynamique, Mode Tâche de Fond & Arbitrage par Défaut (`tie_break_policy`)
- Story 3.3: Ancres Humaines Obligatoires (`human_authored_required`), Synthèse d'Arbitrage, Chunking Cognitif & Détecteur *Rubber-Stamping*
- Story 3.4: Moteur d'Exécution Durable de DAG (`SUB_WORKFLOW <= 3`), Blackboard Versionné Isolé, Reprise après Crash & Coupe-Circuits
- Story 3.5: Cockpit Split-Screen (Zones 1, 2 & 3), Téléportation de Source (`< 1 s`), Replay Transactionnel (*Fork*) & Badge Exécution Autonome (`UX-DR17`)

## Requirements & Constraints

- **Validation Workflow-as-Code (`FR-11`, `FR-13`, `FR-29`, `FR-30`)** : Validation déterministe de la syntaxe YAML/JSON avec rapport du numéro de ligne exact et du code d'erreur. Rejet de tout workflow `criticality: HIGH_CRITICAL` combiné à `execution_regime: AUTONOMOUS_CONTRACT` (`ERR_CRITICAL_WORKFLOW_REQUIRES_HUMAN_GATE`). Discipline `Intention -> Code` obligatoire en mode nominal (`ERR_INTENTION_BEFORE_CODE_REQUIRED`), sauf déclaration explicite `mode: brownfield_bootstrap`. Détection de cycle et profondeur maximale d'imbrication `nesting_depth <= 3` sur les étapes `SUB_WORKFLOW` (`ERR_SUB_WORKFLOW_CYCLE_DETECTED`, `ERR_SUB_WORKFLOW_MAX_DEPTH_EXCEEDED`).
- **Gabarits d'Artefact Multi-Audience (`FR-12`)** : Compilation duale d'une même définition en vue documentaire humaine (Markdown structuré avec interpolation de variables, sections obligatoires, marqueurs `human_authored_required` et bornes de chunking cognitif) et en schéma formel JSON/YAML typé contre l'Ontologie à 4 niveaux pour les étapes agentes en aval.
- **Épinglage Immuable & Récursif `run-lock.json` (`FR-15`, `FR-30`)** : À l'instanciation d'un `Workflow Run`, figeage de toutes les versions d'artefacts (`db://`, `git://`, `nexus://`, `confluence://`, `jira://`), des 4 couches d'overrides (`Base -> Team -> Workspace -> User`), du hash `kb_snapshot_hash` et des manifestes imbriqués `sub_workflow_locks` dans un manifeste immuable signé `manifest_sha256`.
- **Souveraineté Humaine & Gouvernance Cognitive (`FR-3..7`)** : Verrouillage `HTTP 422 ERR_HUMAN_ANCHOR_MISSING` sur toute section `human_authored_required: true` non rédigée/signée par un humain ; suspension `WAITING_FOR_HUMAN_ARBITRATION` ou application de `tie_break_policy` en régime autonome ; chunking cognitif (`500–800 mots` max par volet) ; détection du *Rubber-Stamping* (`dwell_time_ms` insuffisant).
- **Exécution Durable & Coupe-Circuits (`FR-16`)** : Reprise idempotente après crash worker sans perte d'état ni doublon dans `blackboard_snapshots` ou `audit_ledger` ; détection d'impasse sémantique, de boucle d'échec répétée et de dépassement de budget tokens/coût (`PAUSED_CIRCUIT_BREAKER`).

## Technical Decisions

- **Noyau Hexagonal Pur (`packages/orcia-core`)** : Aucun import `fastapi`, `sqlalchemy`, `dramatiq`, `redis` ou `litellm` dans `domain/` et `ports/`.
- **Tables PostgreSQL 18 (`UUIDv7`)** : `workflow_definitions`, `workflow_triggers`, `workflow_runs` (`CHECK (nesting_depth >= 0 AND nesting_depth <= 3)`, `UNIQUE (trigger_id, trigger_idempotency_key)`), `run_lock_manifests`, `blackboard_snapshots` (*Append-Only*), `step_executions` (`draft_artifact_jsonb`, `step_memlog_jsonb`), `human_anchor_signatures`.
- **Sécurité & Contrats API** : Gardes `RunAccessGuard` / `ScopeAccessGuard` rejetant `READ_ONLY_OBSERVER` avec `HTTP 403 ERR_OBSERVER_MODE_READ_ONLY` sur toute mutation ; enveloppes d'erreur **RFC 9457 Problem Details** avec `trace_id` OpenTelemetry ; génération `0-diff` du SDK `@orcia/api-client`.

## UX & Interaction Patterns

- **Direction C — Adaptive Editorial Command** : Tokens CSS sémantiques dans `@orcia/ui` (`packages/ui/src/styles/tokens.css`), zéro hexadécimal en dur dans les composants.
- **Exclusivité Sémantique des Couleurs** : Le Violet `#6D28D9` (`human-led-violet`) est strictement réservé à `HumanLedAnchorCard` (`human_authored_required: true`). Les runs et étapes autonomes utilisent exclusivement le Cyan/Cobalt `#0284C7` (`AutonomousExecutionBadge`, `UX-DR17`).
- **Localisation Française (`fr`) par défaut** : Dictionnaires i18n typés (`apps/web/src/i18n/locales/{fr,en}.ts`), accessibilité WCAG 2.2 AA (Couleur + Icône + Libellé explicite).

## Cross-Story Dependencies

- **Story 3.1** établit les schémas SQL (`workflow_definitions`, `workflow_triggers`, `workflow_runs`, `run_lock_manifests`), le validateur DAG Workflow-as-Code, le compilateur de gabarits multi-audiences et le service d'épinglage `run-lock.json` utilisés par **Stories 3.2, 3.3, 3.4 et 3.5** ainsi que par **Epic 7**.
