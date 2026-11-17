# Story 7.1 — Contrat d'Autonomie Signé (`autonomy_contracts`), Identité Service-Principal Scopée, Modale Studio V2 & Régime `AUTONOMOUS_CONTRACT`

- **Date** : 2026-11-17
- **Story / Clé Sprint** : `7-1-contrat-d-autonomie-signé-identité-service-principal-scopée` (`Epic 7`)
- **Capacité(s)** : `CAP-201` (existant dans `docs/product/capabilities.yaml`, passage de `planned` à `partial`) — classification : `feature`
- **Auteur / Contexte** : Implémentation du socle d'exécution autonome sous contrat (`FR-5`, `FR-22`, `FR-29`, `AD-3`, `AD-6`, `AD-18`, `AD-19`, `AD-21`, `NFR-SEC-4`) sans co-signature `SECOPS`, sous double garde noyau et avec intégration dans Process Studio V2 (`/processes/studio/$workflowId`).
- **Commits associés** : *(en cours d'implémentation — géré par le coordinateur)*

---

## 1. Analyse du Besoin & Étude d'Impact Tech Lead (Pré-Implémentation)

### 1.1 Contexte & Problématique
- Les processus répétitifs, analytiques (`UJ-11`) ou documentaires (`packs/orcia-docs/workflows/generate-and-attach-help`, classé `LOW_NON_CRITICAL`) ne disposent pas encore d'un contrat d'autonomie persistant ni d'un mécanisme d'émission automatique de `SignedApprovalToken` scopé au périmètre d'un compte de service (`SERVICE_PRINCIPAL`) actif dans `iam_accounts`.
- **Comportement attendu** :
  - Tout passage en régime `AUTONOMOUS_CONTRACT` sur un workflow `LOW_NON_CRITICAL` ou `STANDARD` exige un contrat actif signé dans `autonomy_contracts` par un `TEAM_LEAD`, `BU_LEAD` (ou `PLATFORM_ADMIN`) habilité sur le périmètre — **sans co-signature `SECOPS`** (`AD-3`, `AD-6`, `AD-18`).
  - Les workflows `HIGH_CRITICAL` sont formellement rejetés (`HTTP 422 ERR_CRITICAL_WORKFLOW_REQUIRES_HUMAN_GATE`).
  - Double garde noyau : (1) le `SERVICE_PRINCIPAL` sélectionné doit être `ACTIVE` et rattaché au périmètre de l'Espace dans `iam_accounts`, (2) l'invariant de confinement `allowed_write_actions ⊆ Droits(Signataire) ∩ Droits(SERVICE_PRINCIPAL)` doit être satisfait (`HTTP 403 ERR_CONTRACT_PRIVILEGE_ESCALATION` sinon).
  - La signature, la révocation et toute escalade autonome émettent des événements Outbox (`AutonomousContractSigned`, `AutonomousContractRevoked`, `AutonomousEscalated`) vers `domain_events_outbox` et le journal immuable `audit_ledger`.
  - Lors d'un Run autonome (`AUTONOMOUS_CONTRACT`), si toutes les Gates déterministes (dont `validate_help_article`) et agentiques (`agentic_score >= 0.85`, `fact_verification >= 0.90`, `0` conflit d'ontologie, `0` `[STALE_WARNING]`) passent, le `PermissionBroker` délivre un `SignedApprovalToken` autonome scopé aux seules actions autorisées et clôture le Run en `COMMITTED_AUTONOMOUS` ; sinon le Run suspend toute écriture et passe en `PAUSED_AUTONOMOUS_ESCALATION`.
  - L'interface Process Studio V2 (`/processes/studio/$workflowId`) intègre la modale `AutonomyContractModal` (`OrciaDialog`, zéro hexadécimal brut, zéro `<svg>` inline, zéro jargon technique) directement dans l'en-tête découpé de `WorkflowFiveBlocksCanvas.tsx` et supprime le composant orphelin `WorkflowTopGovernanceBar.tsx`.

### 1.2 Exploration, Analyse d'Impact GitNexus, Factorisation & Dette Technique
- **Analyse d'Impact GitNexus (`gitnexus_impact` & `gitnexus_query`, `repo: "/home/romain/Documents/Projects/ORCIA"`)** :
  - `WorkflowFiveBlocksCanvas` (`apps/web/src/features/processes/studio/WorkflowFiveBlocksCanvas.tsx`, **785 lignes**) : `impactedCount: 692`, `risk: CRITICAL` (d=1: 491, d=2: 155, d=3: 46, 149 processus). Dépasse largement le seuil de `300–400` lignes -> découpage préalable en sous-composants `< 350` lignes (`StudioWorkflowHeaderBar.tsx`, `StudioFiveBlocksGrid.tsx`).
  - `WorkflowTopGovernanceBar` (`packages/ui/src/primitives/WorkflowTopGovernanceBar.tsx`) : `impactedCount: 213`, `risk: CRITICAL` dans le graphe global, mais **0 consommateur applicatif réel** dans `apps/web` (`grep` : uniquement exporté dans `packages/ui/src/index.ts` et testé dans `packages/ui/src/__tests__/admin-and-studio-primitives.test.tsx`). Suppression sûre après nettoyage de l'export et du test unitaire associé.
  - `SignedApprovalToken` (`packages/orcia-connectors/src/orcia_connectors/protocol.py`) : `impactedCount: 13`, `risk: MEDIUM` (9 imports directs dans `orcia_connectors/adapters/*`, `bounded_workflow_v2.py`, `codegraph_tool_runner.py`). L'ajout de `SignedApprovalToken.issue_autonomous(...)` en méthode de classe additive conserve 100 % la compatibilité des 13 dépendants existants.
  - `ConnectorInvoker` (`packages/orcia-core/src/orcia_core/permissions/connector_invoker.py`) : `impactedCount: 9`, `risk: LOW` (2 imports directs : `litellm_adapter.py`, `orchestration/connector_invoker.py`).
  - `audit_finops` (`AuditLedgerOutboxSubscriber`, `AUDITABLE_EVENT_TYPES`, `map_domain_event_to_ledger_entry`) : `AUDITABLE_EVENT_TYPES` ne liste pas encore `AutonomousContractSigned`, `AutonomousContractRevoked` ni `AutonomousEscalated`. Il faut les ajouter avec résumés métier FR et purge de secrets (`scrub_sensitive_dict`).
- **Exploration & Constats Clés du Codebase** :
  - **Contrainte `test_hexagonal_purity_permissions_package`** (`tests/unit/test_permissions_and_auth.py:L37`) : `packages/orcia-core/src/orcia_core/permissions/**` interdit tout import `sqlalchemy`, `fastapi`, `dramatiq`, `redis`, `litellm`. De plus, `import-linter` Contrat 2 interdit à `orcia_core.permissions` (couche 4) d'importer `audit_finops` (couche 2) ou `orchestration` (couche 1), et Contrat 4 interdit à `orcia_core` d'importer `orcia_connectors`.
    - *Décision architecturale* : la logique domaine pure et les ports (`AutonomyContract`, `SignAutonomyContractCommand`, `AutonomyContractRepositoryPort`, `AutonomyContractService`) vivent dans `orcia_core.permissions.autonomy_contracts` (`0` SQL/SDK) ; l'adaptateur PostgreSQL 18 (`sql_autonomy_contracts.py`) vit dans `orcia_core.bootstrap._internal` (couche 1, au même titre que `sql_iam_accounts.py` et `sql_iam_grants.py`) et publie dans `domain_events_outbox` + pont optionnel `AuditLedgerSinkPort` injecté au Composition Root.
  - **Contrainte `test_core_domain_isolation.py`** : 0 mot-clé métier SDLC (`jira`, `confluence`, `git_branch`, `wsjf`, `rovo`, `copilot`, `safe`, `prd`) dans `workflows|packs|storage|kernel|orchestration|gates` de `orcia_core`. Tous les exemples et tests noyau utilisent des noms neutres (`catalog_item`, `document_publish`, `help_article`).
  - **Alembic `head` réel** : `20261117_0605` (`20261117_0605_epic6_review_adaptive_gate_policy_check.py`). Dernière contrainte `workflow_runs.status` : `20261116_0602` (`INITIALIZED`, `RUNNING`, `WAITING_FOR_HUMAN_ARBITRATION`, `WAITING_FOR_HUMAN_GATE`, `PAUSED_CIRCUIT_BREAKER`, `PAUSED_BUDGET_EXCEEDED`, `PAUSED_MAX_RETRIES`, `COMPLETED`, `FAILED`, `ROLLED_BACK`). Dernière contrainte `domain_events_outbox.event_type` : `20261116_0601` (19 types dont `StepCompleted` ... `ConnectorCircuitTripped`).
- **Opportunités de Factorisation & Résorption de Dette Technique** :
  - **Doublon détecté (`bounded_workflow_v2.py`)** : `packages/orcia-connectors/src/orcia_connectors/bounded_workflow_v2.py` et `apps/worker/src/orcia_worker/workflows/bounded_workflow_v2.py` sont strictement identiques (`diff` vide). La logique d'exécution `AUTONOMOUS_CONTRACT` sera factorisée dans `packages/orcia-connectors/src/orcia_connectors/autonomous_runner.py` et ré-exportée proprement afin d'éviter la dérive.
  - **Découpage de `WorkflowFiveBlocksCanvas.tsx` (`785` l.)** : extraction immédiate de `StudioWorkflowHeaderBar.tsx` et `StudioFiveBlocksGrid.tsx` (`< 350` l. chacun) avant ajout du bouton et de la modale « Contrat d'autonomie ».

---

## 2. Plan d'Implémentation

### 2.1 Schéma de Données & Migrations Alembic (`infra/migrations/versions/`)
- **`infra/migrations/versions/20261117_0701_story_7_1_autonomy_contracts_and_run_statuses.py`** (`down_revision = "20261117_0605"`, SQL brut réversible) :
  1. Création de la table `autonomy_contracts` (`id` UUID PK, `workspace_id`, `workflow_id`, `workflow_version`, `workflow_sha256`, `criticality` CHECK `('LOW_NON_CRITICAL', 'STANDARD')`, `service_principal_id` FK `iam_accounts(id) ON DELETE RESTRICT`, `allowed_read_sources_jsonb`, `allowed_write_actions_jsonb`, `max_cost_per_run_usd > 0`, `tie_break_policy`, `post_hoc_sampling_rate` `0.10..0.20`, `status` `('ACTIVE', 'REVOKED', 'SUPERSEDED')`, `signed_by_user_id`, `signed_by_role` `('TEAM_LEAD', 'BU_LEAD', 'PLATFORM_ADMIN')`, `signature_sha256`, `signed_at`, `revoked_at`, `revoked_by_user_id`), index partiel unique `uq_autonomy_contracts_active_wf ON (workspace_id, workflow_id) WHERE status = 'ACTIVE'` et index `idx_autonomy_contracts_sp ON (service_principal_id)`.
  2. Élargissement du `CHECK` `workflow_runs.status` en préservant les 10 statuts existants et en ajoutant `'PAUSED_AUTONOMOUS_ESCALATION'` et `'COMMITTED_AUTONOMOUS'`.
  3. Élargissement du `CHECK` `domain_events_outbox.event_type` en préservant les 19 types existants et en ajoutant `'AutonomousContractSigned'`, `'AutonomousContractRevoked'` et `'AutonomousEscalated'`.
- **`infra/scripts/maintenance/09_reset_db_first_boot.py`** : ajout de `"autonomy_contracts"` avant `"iam_accounts"` dans `ORDERED_MUTABLE_TABLES_TO_CLEAR`.

### 2.2 Noyau Métier Hexagonal, Orchestration & Workers
- **`packages/orcia-core/src/orcia_core/kernel/_governance_events.py` & `kernel/events.py`** : événements immuables `AutonomousContractSigned`, `AutonomousContractRevoked`, `AutonomousEscalated`.
- **`packages/orcia-core/src/orcia_core/permissions/errors.py` & `_error_catalog.py`** : erreurs `CriticalWorkflowRequiresHumanGateError` (422), `AutonomyContractNotFoundError` (404), `ServicePrincipalInvalidForContractError` (422), `ContractPrivilegeEscalationError` (403), `AutonomyContractSignForbiddenError` (403) avec copies FR/EN.
- **`packages/orcia-core/src/orcia_core/permissions/autonomy_contracts.py` (`< 280` l.)** : entités `AutonomyContract`, `SignAutonomyContractCommand`, `AutonomyContractRepositoryPort`, et `AutonomyContractService` appliquant la signature unique (`TEAM_LEAD` | `BU_LEAD` | `PLATFORM_ADMIN`, rejet `OBSERVER` 403), le rejet `HIGH_CRITICAL` (422), la validation `SERVICE_PRINCIPAL` actif sur le périmètre et l'invariant `allowed_write_actions ⊆ Droits(Signataire) ∩ Droits(SERVICE_PRINCIPAL)` (403).
- **`packages/orcia-core/src/orcia_core/bootstrap/_internal/sql_autonomy_contracts.py` (`< 300` l.)** : adaptateur PostgreSQL 18 (`SqlAutonomyContractRepository`) + écriture transactionnelle Outbox (`domain_events_outbox`) + relais optionnel vers `AuditLedgerSinkPort`.
- **`packages/orcia-core/src/orcia_core/audit_finops/outbox_subscriber.py`** : prise en charge des 3 nouveaux événements dans `AUDITABLE_EVENT_TYPES` et `_build_event_summary`.
- **`packages/orcia-connectors/src/orcia_connectors/protocol.py` & `autonomous_runner.py` & `bounded_workflow_v2.py`** :
  - `SignedApprovalToken.issue_autonomous(...)` avec `preview_id = f"autonomous:{contract_id}:{run_id}:{action_key}"` et `approver_user_id = f"sp:{service_principal_id}"`, validé par `verify_signed_approval_token(...)`.
  - Exécution `AUTONOMOUS_CONTRACT` vérifiant contrat `ACTIVE` non révoqué à chaque frontière d'étape, `criticality != HIGH_CRITICAL`, Gates déterministes (`PASS`, dont `validate_help_article`) et agentiques (`agentic_score >= 0.85`, `fact_verification >= 0.90`, `0` conflit d'ontologie, `0` `[STALE_WARNING]`), exécution via `ConnectorInvoker` (`execute`, `SecretRef` via `SecretProviderPort`) -> `COMMITTED_AUTONOMOUS` ou suspension `PAUSED_AUTONOMOUS_ESCALATION` + `AutonomousEscalated`.

### 2.3 Couche Backend API, Sécurité & Contrats (`apps/api/`, `packages/api-client/`)
- **`apps/api/src/orcia_api/schemas/autonomy_contracts.py`** : modèles Request/Response Pydantic v2 enregistrés dans `SCHEMA_DOMAIN_MODULES` de `scripts/export_openapi.py`.
- **`apps/api/src/orcia_api/routers/autonomy_contracts.py` (`< 280` l.)** :
  - `GET /api/v1/workspaces/{workspace_id}/workflows/{workflow_id}/autonomy-contract`
  - `POST /api/v1/workspaces/{workspace_id}/workflows/{workflow_id}/autonomy-contract` (`201`)
  - `POST /api/v1/workspaces/{workspace_id}/workflows/{workflow_id}/autonomy-contract/revoke` (`200`)
  - `POST /api/v1/workspaces/{workspace_id}/workflows/{workflow_id}/runs/autonomous` (`201`)
- **`apps/api/src/orcia_api/dependencies/`**, **`errors/registry.py`**, **`main.py`** : câblage Composition Root (`get_autonomy_contract_service`), enregistrement des 5 nouvelles erreurs RFC 9457 et inclusion du routeur.
- Régénération OpenAPI 3.1 et `@orcia/api-client` (`export_openapi.py` + `--check`).

### 2.4 Interface Utilisateur & Expérience (`packages/ui/`, `apps/web/`)
- Découpage de `WorkflowFiveBlocksCanvas.tsx` en `StudioWorkflowHeaderBar.tsx` et `StudioFiveBlocksGrid.tsx` (`< 350` l.).
- Suppression de `packages/ui/src/primitives/WorkflowTopGovernanceBar.tsx`, de son export dans `packages/ui/src/index.ts`, et nettoyage du test unitaire associé.
- Création de `packages/ui/src/primitives/AutonomyContractModal.tsx` (`< 320` l.) basé sur `OrciaDialog` : sélecteur fermé des comptes de service actifs de l'Espace, sélection des sources de lecture et actions d'écriture autorisées, plafond budgétaire (attributs anti-LastPass), règle en cas d'ambiguïté en français métier, `<ContextualInfoTriggerButton />` (`ⓘ`), `<OrciaIcon />`, `0` `#hex`, `0` jargon technique.
- Câblage vertical dans `WorkflowFiveBlocksCanvas.tsx` / `StudioWorkflowHeaderBar.tsx` via `@orcia/api-client` (`GET` au montage, `POST` signature/révocation), traductions dans `apps/web/src/i18n/locales/{fr,en}.ts`, mise à jour de `zero-dead-buttons-and-silent-catches-audit.test.tsx`.

### 2.5 Analyse d'Impact sur la Pyramide des Tests (`AD-17`)
- **Couche 1a (`tests/unit/test_story_7_1_autonomy_contracts.py`)** : `pytest` + `hypothesis` sur `Actions ⊆ Droits(Signataire) ∩ Droits(SERVICE_PRINCIPAL)`, rejet `422` `HIGH_CRITICAL`, signature unique sans `SECOPS`, `SignedApprovalToken.issue_autonomous`, exécution `COMMITTED_AUTONOMOUS` vs `PAUSED_AUTONOMOUS_ESCALATION` (dont `generate-and-attach-help` / `validate_help_article`), `test_core_domain_isolation.py`.
- **Couche 1b (`apps/web/src/__tests__/story-7-1-studio-autonomy-contract-modal-and-f5.test.tsx`)** : ouverture modale dans Studio V2, signature, révocation, survie au `F5` (`unmount()` -> `render()`), passage de `zero-dead-buttons-and-silent-catches-audit.test.tsx` et `design-system-look-and-feel-isolation.test.tsx`.
- **Couche 2 (`tests/integration/api/test_story_7_1_autonomy_contracts_postgres18.py`)** : migration Alembic `20261117_0701` (`upgrade` + `downgrade` + `upgrade`), `AsyncClient(app)` `HTTP ➔ PostgreSQL 18` + `SELECT` direct (`autonomy_contracts`, `workflow_runs`, `domain_events_outbox`, `audit_ledger`), et test de `09_reset_db_first_boot.py`.
- **Couche 3 & Sécurité (`tests/security/test_story_7_1_contract_confinement_and_secrets.py`)** : rejet `403 READ_ONLY_OBSERVER`, rejet `403` escalade de privilèges, `0` secret en clair, `export_openapi.py --check`, `lint-imports`.

---

## 3. Bilan des Modifications & Résultats (Post-Implémentation)

### 3.1 Fichiers Développés & Modifiés
| Fichier | Nature (Création / Modification / Refactoring) | Volumétrie | Description synthétique |
| :--- | :--- | :--- | :--- |
| `infra/migrations/versions/20261117_0701_story_7_1_autonomy_contracts_and_run_statuses.py` | Création | 250 l. | Migration Alembic réversible (`down_revision = "20261117_0605"`) : table `autonomy_contracts` (`ACTIVE`/`REVOKED`/`SUPERSEDED`, index partiel unique actif `(workspace_id, workflow_id)`), extension `CHECK` `workflow_runs.status` (`PAUSED_AUTONOMOUS_ESCALATION`, `COMMITTED_AUTONOMOUS`) & `domain_events_outbox.event_type` (`AutonomousContractSigned`, `AutonomousContractRevoked`, `AutonomousEscalated`). |
| `infra/scripts/maintenance/09_reset_db_first_boot.py` | Modification | 279 l. | Ajout de `"autonomy_contracts"` avant `"iam_accounts"` dans `ORDERED_MUTABLE_TABLES_TO_CLEAR`. |
| `packages/orcia-core/src/orcia_core/kernel/_governance_events.py`, `events.py`, `__init__.py` & `errors.py` | Modification | 329 / 374 l. | Événements `AutonomousContractSigned`, `AutonomousContractRevoked`, `AutonomousEscalated`, et erreur `CriticalWorkflowRequiresHumanGateError` (`422 ERR_CRITICAL_WORKFLOW_REQUIRES_HUMAN_GATE`) dédupliquée depuis `orchestration/errors.py`. |
| `packages/orcia-core/src/orcia_core/audit_finops/outbox_subscriber.py` | Modification | 221 l. | Prise en charge des 3 événements autonomes dans `AUDITABLE_EVENT_TYPES` et `_build_event_summary`. |
| `packages/orcia-core/src/orcia_core/permissions/_autonomy_confinement.py`, `autonomy_contracts.py`, `_error_catalog.py`, `errors.py`, `__init__.py` | Création / Modification | 193 / 377 / 315 l. | Domaine hexagonal pur sans SQL/SDK (`AutonomyContract`, `SignAutonomyContractCommand`, `AutonomyContractRepositoryPort`, `AutonomyContractService`), signature unique (`TEAM_LEAD`\|`BU_LEAD`\|`PLATFORM_ADMIN`, zéro `SECOPS`), double garde noyau (`SERVICE_PRINCIPAL` actif scopé + `Actions ⊆ Droits(Signataire) ∩ Droits(SERVICE_PRINCIPAL)`), erreurs RFC 9457 bilingues. |
| `packages/orcia-core/src/orcia_core/bootstrap/_internal/sql_autonomy_contracts.py` & `bootstrap/__init__.py` | Création / Modification | 367 l. | Adaptateur PostgreSQL 18 (`SqlAutonomyContractRepository`) + persistance transactionnelle Outbox + `audit_ledger` + `persist_autonomous_run_outcome_on_postgres18`. |
| `packages/orcia-core/src/orcia_core/orchestration/help_generator_and_validator.py` | Modification | — | Enregistrement de `"AutonomyContractModal"` dans `KNOWN_ORCIA_UI_COMPONENTS`. |
| `packages/orcia-connectors/src/orcia_connectors/protocol.py`, `autonomous_runner.py`, `__init__.py` & `apps/worker/src/orcia_worker/workflows/bounded_workflow_v2.py` | Création / Modification / Refactoring | 204 / 325 l. | Ajout `SignedApprovalToken.issue_autonomous(...)`, runner `execute_autonomous_contract_run` (`COMMITTED_AUTONOMOUS` vs `PAUSED_AUTONOMOUS_ESCALATION`, re-vérification de révocation à chaque étape, support `validate_help_article`), et déduplication du miroir worker `bounded_workflow_v2.py`. |
| `apps/api/src/orcia_api/schemas/autonomy_contracts.py`, `routers/autonomy_contracts.py`, `dependencies/*`, `errors/registry.py`, `main.py` & `scripts/export_openapi.py` | Création / Modification | 137 / 380 l. | Endpoints `/api/v1/workspaces/{workspace_id}/workflows/{workflow_id:path}/autonomy-contract` (`GET`/`POST`/`/revoke`) et `/runs/autonomous` (`POST`), Composition Root, registre RFC 9457, shard OpenAPI `0-diff` `autonomy_contracts`. |
| `packages/api-client/src/domains/autonomyContracts.ts`, `index.ts`, `generated/autonomy_contracts.ts` | Création / Modification | 81 l. | Client typé `@orcia/api-client` généré depuis OpenAPI 3.1 (`0-diff`). |
| `packages/ui/src/primitives/AutonomyContractModal.tsx`, `index.ts`, `admin-and-studio-primitives.test.tsx` *(suppression de `WorkflowTopGovernanceBar.tsx`)* | Création / Suppression | 351 l. | Modale `AutonomyContractModal` (`OrciaDialog`, `<OrciaIcon />`, `<ContextualInfoTriggerButton />`, attributs anti-LastPass, `0` `#hex`, `0` jargon technique) et suppression complète de l'orphelin `WorkflowTopGovernanceBar`. |
| `apps/web/src/features/processes/studio/` (`WorkflowFiveBlocksCanvas.tsx`, `useWorkflowAutonomyContract.ts`, `StudioWorkflowHeaderBar.tsx`, `StudioFiveBlocksGrid.tsx`, `StudioWhatIfPanel.tsx`), `i18n/locales/autonomy_contract_labels.ts`, `_contextualHelpSections.ts` | Création / Refactoring | 322 / 137 / 185 / 386 / 115 l. | Découpage modulaire de `WorkflowFiveBlocksCanvas.tsx` (`785 -> 322 l.`), hook `useWorkflowAutonomyContract.ts`, câblage vertical `@orcia/api-client`, dictionnaires FR/EN et aide contextuelle `autonomy-contract`. |
| `tests/unit/test_story_7_1_autonomy_contracts.py`, `tests/security/test_story_7_1_contract_confinement_and_secrets.py`, `tests/integration/api/test_story_7_1_autonomy_contracts_postgres18.py`, `apps/web/src/__tests__/story-7-1-studio-autonomy-contract-modal-and-f5.test.tsx` & `zero-dead-buttons-and-silent-catches-audit.test.tsx` | Création / Modification | 994 / 118 / 304 / 131 l. | Couverture complète des couches `AD-17` (unitaires + `hypothesis`, sécurité confinement/secrets/observer, `testcontainers` PG18 `HTTP -> SQL`, Vitest + survie `F5` `unmount -> render` + audit zéro bouton muet). |

### 3.2 Résultats Chiffrés, Métriques & Qualité
- **Couverture de tests** :
  - **96,58 %** sur les 4 modules Story 7.1 (`autonomy_contracts.py` **99 %**, `_autonomy_confinement.py` **99 %**, `autonomous_runner.py` **96 %**, `sql_autonomy_contracts.py` **89 %** — `9 passed in 46.97s`, seuil $\ge 90\%$).
  - **93,39 %** sur l'ensemble du domaine `orcia_core.permissions` (`pytest tests/unit tests/contract tests/conformance tests/security --cov=orcia_core.permissions --cov-fail-under=90` : `646 passed`, note : `1` échec préexistant non déterministe `HealthCheck.too_slow` sur `st.emails()` dans `tests/unit/test_permission_broker.py` hors périmètre qui passe en exécution ciblée `11 passed in 29.96s`).
- **Qualité statique & Architecture** :
  - `.venv/bin/ruff check .` & `.venv/bin/ruff format --check .` : `All checks passed!`, `966 files already formatted`.
  - `.venv/bin/mypy --strict packages/orcia-core packages/orcia-connectors apps/api apps/worker` : `Success: no issues found in 424 source files`.
  - `.venv/bin/lint-imports` : `Contracts: 5 kept, 0 broken` (`AD-19 Contracts 1..5`).
  - `.venv/bin/python scripts/export_openapi.py --check` : `0-diff` validé.
  - `pnpm site:sync && pnpm site:check` : `61/61` capacités live avec tests, manifeste synchronisé (`150` rapports, `26` routes, `119` primitives UI).
  - `npx gitnexus@latest analyze --index-only && npx gitnexus@latest detect-changes --scope all --repo .` : `29,602 nodes | 50,888 edges | 475 clusters | 1319 flows`, `Changes: 37 files, 72 symbols | Affected processes: 30 | Risk level: critical`.

### 3.3 Validation & Procédure de Test sur Toute la Pyramide (`AD-17`)
- **Couche 1a (Unitaires Python & `hypothesis`)** : `tests/unit/test_story_7_1_autonomy_contracts.py` (confinement `Actions ⊆ Droits(Signataire) ∩ Droits(SERVICE_PRINCIPAL)`, rejet `HIGH_CRITICAL`, signature unique sans `SECOPS`, `SignedApprovalToken.issue_autonomous`, escalades et exécution `COMMITTED_AUTONOMOUS` vs `PAUSED_AUTONOMOUS_ESCALATION`, `test_core_domain_isolation.py` vert).
- **Couche 1b (Frontend `Turborepo` / `Vitest`)** : `pnpm turbo run lint typecheck test` (`9/9 tasks successful` : `@orcia/api-client` 2 fichiers / 13 tests, `@orcia/ui` 25 fichiers, `@orcia/web` 30 fichiers / 129 tests dont `story-7-1-studio-autonomy-contract-modal-and-f5.test.tsx` avec survie `F5` `unmount()` $\rightarrow$ `render()`, `zero-dead-buttons-and-silent-catches-audit.test.tsx` et `design-system-look-and-feel-isolation.test.tsx`).
- **Couche 2 (Intégration `testcontainers` PostgreSQL 18)** : `.venv/bin/pytest tests/integration/api/test_story_7_1_autonomy_contracts_postgres18.py` (`1 passed in 20.42s`) validant Alembic `20261117_0701` (`upgrade head`, `downgrade -1`, `upgrade head`), l'insertion HTTP $\rightarrow$ SQL dans `autonomy_contracts`, `workflow_runs`, `domain_events_outbox` et `audit_ledger`, la révocation, et `09_reset_db_first_boot.py`.
- **Couche 3 (Contrat OpenAPI `0-diff`)** : régénération via `scripts/export_openapi.py` + contrôle `--check` (`exit 0`).
- **Couche Sécurité** : `tests/security/test_story_7_1_contract_confinement_and_secrets.py` (rejet `403 READ_ONLY_OBSERVER`, rejet `403` escalade privilèges, `0` fuite de secret dans tokens/Outbox/audit).
