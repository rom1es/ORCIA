# Story 6.1 — Registre de Provenance Auditable Immuable (audit_ledger Append-Only), Traçabilité des Tests à Chaud (ADMIN_CONNECTION_TEST) & Export de Conformité JSON/Markdown

> **Convention de nommage du fichier (Obligatoire — créé AVANT toute modification de code applicatif)** :
> - User Story du sprint : `docs/implementation-artifacts/tech-lead-reports/6-1-registre-de-provenance-auditable-immuable-audit_ledger-appen-tech-lead-report.md`

- **Date** : 2026-11-16
- **Story / Clé Sprint** : `6-1-registre-de-provenance-auditable-immuable-audit_ledger-appen` (`Epic 6`)
- **Capacité(s)** : `CAP-065` (rebasage de la source de `/activity`), `CAP-200` (registre append-only et provenance FinOps) — classification : `feature` (voir `AGENTS.md` §5 et `capabilities.yaml`)
- **Auteur / Contexte** : Winston (`bmad-agent-architect` 🏗️) & Sally (`bmad-agent-ux-designer` 🎨). Création du registre de provenance auditable immuable `audit_ledger` dans PostgreSQL 18, protégé par un trigger interdisant tout `UPDATE` ou `DELETE` (`NFR-SEC-3`). Ingestion asynchrone Outbox (`orcia_core/audit_finops`), traçabilité des essais à chaud (`ADMIN_CONNECTION_TEST`), génération des dossiers de conformité légale (`JSON`/`Markdown`), découpage d'`ActivityLogExplorerView.tsx` (< 350 lignes, préservation 100 % des `data-testid`), et raccordement pérenne de `/activity` avec survie au rechargement (`F5`). Couvre `FR-25`, `AD-12`, `AD-17`, `AD-19`, `AD-21`, `AD-23`, `NFR-SEC-3`, `NFR-SEC-4`, `Principe M.2` et `CAP-ACT-3`.
- **Commits associés** : `pending-implementation`

---

## 1. Analyse du Besoin & Étude d'Impact Tech Lead (Pré-Implémentation)

### 1.1 Contexte & Problématique
Le diagnostic mené le 2026-11-08 (`CAP-ACT-3`) a révélé qu'aucune migration Alembic ne crée la table `audit_ledger`, que le package `packages/orcia-core/src/orcia_core/audit_finops/` ne comporte qu'`errors.py` et que l'écran `/activity` (`CAP-065`) s'alimente actuellement sur `platformSetupStore.auditEvents`, une structure en mémoire issue du snapshot d'accostage (`bootstrap_accostage.py`).
Or, les exigences réglementaires (AI Act, DORA, NIS 2) et de gouvernance interne (`Sophie UJ-6`, `Claire UJ-8`) imposent :
1. Une immuabilité mathématique et technique absolue du journal d'audit : aucune suppression ni mise à jour ne doit être admise, même par un super-administrateur ou via le client SQL.
2. Une ingestion asynchrone par bus Outbox (`domain_events_outbox`), découplée des transactions du moteur d'orchestration, avec idempotence garantie (`source_event_id UNIQUE`).
3. La traçabilité exhaustive de la provenance de chaque livrable : modèle LLM invoqué, niveau de prompt, condensats SHA-256 du contrat de workflow et de `run_lock.json`, et références CAS SeaweedFS des chunks injectés.
4. L'isolation des essais de connectivité et tests à chaud d'administrateurs sous `actor_type: ADMIN_CONNECTION_TEST` (`run_id: None`), évitant toute pollution des budgets de production d'Espaces.
5. La capacité d'exporter un dossier de conformité certifié scellé en format JSON ou Markdown attestant de l'intégrité de la chaîne de confiance.

### 1.2 Exploration, Analyse d'Impact GitNexus, Factorisation & Dette Technique
- **Analyse d'Impact GitNexus (`gitnexus_query`, `gitnexus_context`, `gitnexus_impact`)** :
  - `OutboxEventBus` (`apps/worker/src/orcia_worker/outbox_relay.py`) : impact amont $d=1$. Doit être étendu pour router les événements vers le consommateur `AuditLedgerOutboxSubscriber`.
  - `ActivityLogExplorerView` (`packages/ui/src/primitives/ActivityLogExplorerView.tsx`) : 525 lignes. Impact amont sur `apps/web/src/routes/activity.tsx`. Risque de régression sur les `data-testid` d'audit.
  - `mcp_and_test_bench.py` et `ai_models_hub.py` : points d'entrée du banc de test à chaud. Doivent publier `AdminConnectionTested` dans l'Outbox sans altérer le contrat de réponse existant.
  - `enforce_scope_mutation_guard` : non impacté directement en lecture sur `/audit/ledger`, mais requis sur les actions d'export ou replay.
- **Exploration & Volumétries Constatées** :
  - Remise à zéro Jour 0 (`pnpm db:reset`) : `audit_ledger` est déjà déclarée dans `PROTECTED_TABLES` (ligne 42 de `09_reset_db_first_boot.py`). Elle démarrera avec 0 ligne et le trigger actif.
  - Types d'événements Outbox : la contrainte CHECK sur `domain_events_outbox.event_type` compte 14 types. Elle sera élargie linéairement à 19 types pour accueillir les nouveaux événements d'audit et de coupe-circuits.
- **Opportunités de Factorisation & Résorption de Dette Technique Naissante** :
  - **Découpage de `events.py`** : le fichier `packages/orcia-core/src/orcia_core/kernel/events.py` approche 630 lignes. Extraction des événements d'audit dans `packages/orcia-core/src/orcia_core/kernel/_finops_audit_events.py` (< 350 lignes) et réexport dans `events.py`.
  - **Découpage de `ActivityLogExplorerView.tsx`** : extraction de `ActivityLogFiltersBar.tsx` (~160 lignes) et `ActivityLogProvenanceExportBar.tsx` (~120 lignes), réduisant la vue principale à ~250 lignes tout en maintenant strictement 100 % des `data-testid` existants (`activity-log-table`, `activity-log-filter-*`, etc.).
  - **Sanitisation anti-secrets (`DEC-SEC-01`, `NFR-SEC-4`)** : réutilisation de `scrub_sensitive_dict` d'`orcia_core.observability.logging` avant toute insertion dans `metadata_jsonb`.

---

## 2. Plan d'Implémentation

### 2.1 Schéma de Données & Migrations Alembic Linéaires
- Création de `infra/migrations/versions/20261116_0601_story_6_1_audit_ledger_append_only.py` (`down_revision = "20261115_2359"`) :
  - Table `audit_ledger` :
    - `id UUID PRIMARY KEY` (UUIDv7 via `uuid-utils`).
    - `source_event_id UUID UNIQUE NOT NULL` (idempotence Outbox).
    - `run_id UUID NULL REFERENCES workflow_runs(id) ON DELETE SET NULL` (nullable pour les tests d'administrateurs).
    - `root_run_id UUID NULL REFERENCES workflow_runs(id) ON DELETE SET NULL`.
    - `step_execution_id UUID NULL REFERENCES step_executions(id) ON DELETE SET NULL`.
    - `actor_type VARCHAR(64) NOT NULL` (`USER`, `SERVICE_PRINCIPAL`, `ADMIN_CONNECTION_TEST`, `AGENT_A2A`, `MCP_CLIENT`).
    - `actor_id VARCHAR(128) NOT NULL`, `actor_display_name VARCHAR(256) NULL`, `actor_email VARCHAR(256) NULL`.
    - `event_type VARCHAR(64) NOT NULL` (`StepCompleted`, `GateEvaluated`, `AdminConnectionTested`, `ArtifactProduced`, `RunTerminated`, `SettingsChanged`).
    - `summary TEXT NOT NULL`.
    - `model_id VARCHAR(128) NULL`, `inference_tier VARCHAR(32) NULL`, `effort VARCHAR(32) NULL`.
    - `input_tokens INTEGER NOT NULL DEFAULT 0`, `output_tokens INTEGER NOT NULL DEFAULT 0`.
    - `cost_usd NUMERIC(12, 6) NOT NULL DEFAULT 0.000000`.
    - `cost_source VARCHAR(32) NOT NULL DEFAULT 'INTERNAL_VERIFIED'`.
    - `native_metric_type VARCHAR(64) NULL`, `native_metric_value NUMERIC(16, 6) NULL`, `native_currency VARCHAR(8) NULL`.
    - `reported_by_remote BOOLEAN NOT NULL DEFAULT FALSE`.
    - `latency_ms INTEGER NOT NULL DEFAULT 0`.
    - `trace_id VARCHAR(64) NOT NULL`.
    - `run_lock_sha256 VARCHAR(64) NULL`, `pre_prompt_sha256 VARCHAR(64) NULL`, `workflow_contract_sha256 VARCHAR(64) NULL`.
    - `cas_references_jsonb JSONB NOT NULL DEFAULT '[]'::jsonb`.
    - `metadata_jsonb JSONB NOT NULL DEFAULT '{}'::jsonb`.
    - `created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()`.
  - Index :
    - `idx_audit_ledger_run_id` sur `run_id` (partiel `WHERE run_id IS NOT NULL`).
    - `idx_audit_ledger_root_run_id` sur `root_run_id` (partiel `WHERE root_run_id IS NOT NULL`).
    - `idx_audit_ledger_actor` sur `(actor_type, actor_id)`.
    - `idx_audit_ledger_created_at` sur `created_at DESC`.
    - `idx_audit_ledger_trace_id` sur `trace_id`.
  - Trigger PostgreSQL 18 d'immuabilité :
    - Fonction `fn_prevent_audit_ledger_mutation()` levant l'exception `ERR_AUDIT_LEDGER_IMMUTABLE`.
    - Trigger `prevent_audit_ledger_mutation` BEFORE UPDATE OR DELETE ON `audit_ledger`.
  - Élargissement de la contrainte CHECK sur `domain_events_outbox.event_type` pour inclure `'AdminConnectionTested'`, `'BudgetCircuitTripped'`, `'BudgetOverrideApproved'`, `'RemoteUsageAnomalyCapped'`, `'ConnectorCircuitTripped'`.

### 2.2 Noyau Métier Hexagonal, Orchestration & Workers
- **Contrats Hexagonaux Purs (`packages/orcia-core/src/orcia_core/ports/finops_telemetry.py`)** :
  - Définition de `AuditLedgerSinkPort` (protocole asynchrone pur) et `FinopsCostLedgerEntry` (DTO immuable).
  - Respect de `AD-19 Contract 2 & 3` : zéro framework, zéro dépendance circulaire.
- **Domaine `orcia_core/audit_finops/`** :
  - `models.py` : structures de données métier pour l'audit et la provenance.
  - `outbox_subscriber.py` : consommation des événements Outbox avec scrubbing strict (`DEC-SEC-01`) et insertion idempotente (`ON CONFLICT (source_event_id) DO NOTHING`).
  - `provenance_exporter.py` : construction de l'arbre chronologique de provenance attestant de l'alignement sur `run_lock_manifests.manifest_sha256` et des empreintes de contrats, sérialisé en JSON et Markdown.
  - `_internal/sql_audit_ledger.py` : requêtes SQL asynchrones sans ORM applicatif (`sa.text`).
- **Worker Dramatiq (`apps/worker/src/orcia_worker/outbox_relay.py`)** :
  - Intégration du relais Outbox pour persister chaque événement éligible dans `audit_ledger` de manière transactionnelle.
- **Points d'Émission API** :
  - Émission de `AdminConnectionTested` dans `apps/api/src/orcia_api/routers/mcp_and_test_bench.py` et `ai_models_hub.py` (`actor_type: ADMIN_CONNECTION_TEST`, `run_id: None`).
  - Émission de `SettingsChanged` dans `settings_and_studio.py`.

### 2.3 Couche Backend API, Sécurité & Contrats
- **Schémas RFC 9457 (`apps/api/src/orcia_api/schemas/audit_finops.py`)** :
  - `AuditLedgerEntryResponse`, `AuditLedgerPageResponse`, `AuditProvenanceSummaryResponse`, `AuditExportResponse`.
- **Routeur FastAPI (`apps/api/src/orcia_api/routers/audit_ledger.py`)** :
  - `GET /api/v1/audit/ledger` (pagination, filtres temporels, scope, type d'acteur et d'événement).
  - `GET /api/v1/audit/ledger/{run_id}/provenance` (résumé de provenance du run).
  - `GET /api/v1/audit/ledger/{run_id}/export?format=json|md` (dossier certifié de conformité).
- **Composition Root (`apps/api/src/orcia_api/dependencies/`)** :
  - Fournisseur de dépendance `get_audit_ledger_service` dans `orchestration_and_settings.py` et injection dans le routeur.
- **SDK OpenAPI Client (`packages/api-client/`)** :
  - Régénération automatique via `.venv/bin/python scripts/export_openapi.py` (`0-diff`).

### 2.4 Interface Utilisateur & Expérience (`apps/web/` & `@orcia/ui`)
- **Refactoring & Découpage `@orcia/ui`** :
  - `packages/ui/src/primitives/ActivityLogExplorerView.tsx` : allègement sous le seuil des 300 lignes.
  - `ActivityLogFiltersBar.tsx` : composant isolé pour les sélecteurs de date, de périmètre et de types d'événements.
  - `ActivityLogProvenanceExportBar.tsx` : tiroir et actions d'inspection de provenance et de téléchargement JSON/Markdown.
  - Préservation absolue de 100 % des `data-testid` existants (`activity-log-table`, etc.).
- **Câblage de `/activity` (`apps/web/src/routes/activity.tsx`)** :
  - Substitution de `platformSetupStore.auditEvents` par l'appel asynchrone `@orcia/api-client` (`GET /api/v1/audit/ledger`).
  - Survie au rechargement de page (`F5`) validée par test Vitest (`unmount()` + `render()`).

### 2.5 Analyse d'Impact sur la Pyramide des Tests (`AD-17`)
- **Couche 1a (Unitaires Python `tests/unit/`)** :
  - `test_story_6_1_audit_ledger_core.py` : validation des modèles, du formatage JSON/Markdown et de l'extraction de provenance.
  - `test_story_6_1_outbox_subscriber.py` : validation de l'idempotence et du scrubbing des secrets canaris (`DEC-SEC-01`).
- **Couche 1b (Composants TS `Vitest`)** :
  - Test de rendu de `ActivityLogExplorerView` avec données réelles, vérification des `data-testid` et test de survie au F5.
- **Couche 2 (Intégration Verticale `HTTP ➔ PostgreSQL 18` `tests/integration/`)** :
  - `test_story_6_1_audit_ledger_postgres18.py` sur conteneurs réels (`testcontainers-python` PostgreSQL 18 + SeaweedFS) :
    - Ingestion Outbox et vérification par requête `SELECT` en base.
    - Tentative d'exécution d'une commande SQL `UPDATE` puis `DELETE` sur `audit_ledger` et validation de la levée d'exception immédiate `ERR_AUDIT_LEDGER_IMMUTABLE`.
    - Vérification qu'aucun secret canari n'a fuité dans `metadata_jsonb`.
- **Couche 3 (Contrats OpenAPI & `lint-imports`)** :
  - Validation du `0-diff` SDK OpenAPI 3.1.
  - Validation de `lint-imports` (5 contrats validés, 0 violation, isolation stricte `audit_finops`).
- **Couche Sécurité / Red-Team** :
  - Vérification de l'étanchéité des secrets et du rejet des tentatives d'altération du registre.

---

## 3. Bilan des Modifications & Résultats (Post-Implémentation)

> *Section réservée à l'implémentation par le dev worker (`bmad-dev-worker` ⚡).*

### 3.1 Fichiers Développés & Modifiés
| Fichier | Nature (Création / Modification / Refactoring) | Description synthétique |
| :--- | :--- | :--- |
| `infra/migrations/versions/20261116_0601_story_6_1_audit_ledger_append_only.py` | Création | Migration Alembic pour `audit_ledger`, trigger d'immuabilité et CHECK élargi |
| `packages/orcia-core/src/orcia_core/kernel/events.py` | Refactorisation | Réexport centralisé et exhaustif (`__all__`) des familles d'événements découpées (< 60 lignes) |
| `packages/orcia-core/src/orcia_core/kernel/_events_base.py` | Création | Définition de base `DomainEvent` pure (< 50 lignes) |
| `packages/orcia-core/src/orcia_core/kernel/_orchestration_events.py` | Création | Sous-famille d'événements orchestration et steps (< 200 lignes) |
| `packages/orcia-core/src/orcia_core/kernel/_governance_events.py` | Création | Sous-famille d'événements gouvernance, packs et IAM (< 200 lignes) |
| `packages/orcia-core/src/orcia_core/kernel/_datasource_rag_events.py` | Création | Sous-famille d'événements sources de données et indexation (< 230 lignes) |
| `packages/orcia-core/src/orcia_core/kernel/_finops_audit_events.py` | Création | Sous-famille d'événements télémétrie FinOps et audit (< 220 lignes) |
| `packages/orcia-core/src/orcia_core/ports/finops_telemetry.py` | Création | Protocoles purs FinOps et télémétrie sans dépendance framework (< 120 lignes) |
| `packages/orcia-core/src/orcia_core/audit_finops/models.py` | Création | Modèle de domaine `AuditLedgerEntry` avec validation et conversion (< 140 lignes) |
| `packages/orcia-core/src/orcia_core/audit_finops/errors.py` | Création | Erreurs de domaine `AuditLedgerImmutableError`, `AuditRunNotFoundError` (< 50 lignes) |
| `packages/orcia-core/src/orcia_core/audit_finops/outbox_subscriber.py` | Création | Consommateur idempotent avec filtrage/scrubbing strict `DEC-SEC-01` (< 170 lignes) |
| `packages/orcia-core/src/orcia_core/audit_finops/provenance_exporter.py` | Création | Exportateur de provenance JSON et Markdown scellé (< 220 lignes) |
| `packages/orcia-core/src/orcia_core/audit_finops/_internal/sql_audit_ledger.py` | Création | Service SQL d'ingestion et requêtes d'exploration paginée (< 210 lignes) |
| `packages/orcia-core/src/orcia_core/audit_finops/_internal/sql_audit_ledger_mappers.py` | Création | Fonctions de parsing et sérialisation des lignes PostgreSQL (< 260 lignes) |
| `packages/orcia-core/src/orcia_core/audit_finops/__init__.py` | Création | Exports publics du domaine `audit_finops` (< 30 lignes) |
| `packages/ui/src/primitives/ActivityLogFiltersBar.tsx` | Création | Composant barre de filtres extrait (< 150 lignes) |
| `packages/ui/src/primitives/ActivityLogProvenanceExportBar.tsx` | Création | Composant export et inspection de provenance avec labels typés i18n (< 130 lignes) |
| `packages/ui/src/primitives/activityLogHelpers.ts` | Création | Types d'événements et filtres temporels/scope extraits (< 160 lignes) |
| `packages/ui/src/primitives/ActivityLogExplorerView.tsx` | Modification | Factorisation et intégration des deux barres, préservation 100% data-testid (< 335 lignes) |
| `packages/ui/src/index.ts` | Modification | Réexport des composants et types de filtres d'activité |
| `apps/worker/src/orcia_worker/outbox_relay.py` | Modification | Câblage de l'abonné Outbox vers `audit_ledger` (`_on_audit_finops`) |
| `apps/api/src/orcia_api/schemas/audit_finops.py` | Création | Schémas Pydantic RFC 9457 pour l'audit et la provenance |
| `apps/api/src/orcia_api/schemas/__init__.py` | Modification | Export des schémas `AuditLedgerEntrySchema`, `AuditProvenanceSummaryResponse`, `AuditExportResponse` |
| `apps/api/src/orcia_api/routers/audit_ledger.py` | Création | Routeur FastAPI `/api/v1/audit/ledger` (liste, provenance, export json/md) |
| `apps/api/src/orcia_api/routers/mcp_and_test_bench.py` | Modification | Émission Outbox de `AdminConnectionTested` lors des tests à chaud |
| `apps/api/src/orcia_api/routers/ai_models_hub.py` | Modification | Émission Outbox de `AdminConnectionTested` lors des tests à chaud |
| `apps/api/src/orcia_api/routers/settings_and_studio.py` | Modification | Enregistrement de `SettingsChanged` dans `audit_ledger` |
| `apps/api/src/orcia_api/dependencies/core_and_lifespan.py` | Modification | Exposition de `get_audit_ledger_service` et `get_provenance_exporter_service` |
| `apps/api/src/orcia_api/dependencies/orchestration_and_settings.py` | Modification | Exposition de `get_audit_ledger_service` et `get_provenance_exporter_service` |
| `apps/api/src/orcia_api/dependencies/__init__.py` | Modification | Réexport des services d'audit |
| `apps/api/src/orcia_api/main.py` | Modification | Montage du routeur `audit_ledger_router` |
| `packages/api-client/src/generated/` | Régénération | SDK OpenAPI 3.1 régénéré (`0-diff` gate) |
| `apps/web/src/routes/activityApiBridge.ts` | Création | Pont typé `@orcia/api-client` pour `/activity` |
| `apps/web/src/routes/activityFormatters.ts` | Création | Formatage timestamps, mappings d'événements et filtres scopes (< 160 lignes) |
| `apps/web/src/routes/ActivityProvenanceModal.tsx` | Création | Modale de visualisation du dossier de provenance certifié (< 80 lignes) |
| `apps/web/src/i18n/locales/activity_labels.ts` | Création | Dictionnaires FR et EN stricts pour `/activity` (< 150 lignes) |
| `apps/web/src/routes/activity.tsx` | Modification | Câblage exclusif sur `GET /api/v1/audit/ledger` (zéro fallback local), modale de provenance, export JSON/MD, survie F5 (< 180 lignes) |
| `tests/unit/test_story_6_1_audit_ledger_core.py` | Création | Tests unitaires modèles, migration réversible et export |
| `tests/unit/test_story_6_1_outbox_subscriber.py` | Création | Tests unitaires scrubbing `DEC-SEC-01`, mapping et outbox |
| `tests/unit/test_story_6_1_sql_audit_ledger.py` | Création | Tests unitaires de `SqlAuditLedgerService` et filtres |
| `tests/integration/api/test_story_6_1_audit_ledger_postgres18.py` | Création | Tests d'intégration réels sur `pgvector/pgvector:pg18` (trigger immutabilité, SELECT direct, exports) |
| `tests/security/test_story_6_1_canary_leak_and_scope_guard.py` | Création | Test sécurité absence de fuite canary |
| `apps/web/src/__tests__/story-6-1-activity-provenance-export-and-f5.test.tsx` | Création | Test Vitest écran `/activity`, inspection de provenance, export et survie au F5 |
| `docs/product/capabilities.yaml` | Modification | Mise à jour de `CAP-065` (`status: live`, tests rattachés) |

### 3.2 Résultats Chiffrés, Métriques & Qualité
- **Couverture de tests constatée** :
  - `packages/orcia-core/src/orcia_core/audit_finops` : **93.93 %** (33 tests passés avec les suites unitaires et sécurité, seuil minimal de 90 % largement dépassé).
- **Volumétrie & Découpage architectural** :
  - Tous les fichiers du périmètre sont strictement **< 350 lignes** (max 334 lignes sur `ActivityLogExplorerView.tsx`, 257 lignes sur `sql_audit_ledger_mappers.py`, 174 lignes sur `activity.tsx`, 59 lignes sur `events.py`).
- **Validation des tests d'intégration réels PostgreSQL 18** :
  - `tests/integration/api/test_story_6_1_audit_ledger_postgres18.py` : **3 passed** en 18.41s (trigger PostgreSQL `ERR_AUDIT_LEDGER_IMMUTABLE` vérifié sur UPDATE et DELETE, persistance et absence de fuite secrète, export JSON/MD certifié).
- **Validation Frontend Vitest & Suite Turborepo** :
  - `pnpm turbo run lint typecheck test` : **9/9 tasks successful** (3 cached, 37.1s).
  - `@orcia/web` : **26/26 test files passed, 118/118 tests passed**.
  - `@orcia/ui` : **25/25 test files passed, 107/107 tests passed**.
  - `@orcia/api-client` : **2/2 test files passed, 13/13 tests passed**.
  - `apps/web/src/__tests__/story-6-1-activity-provenance-export-and-f5.test.tsx` : **1 passed** (inspection de provenance, téléchargement, survie au F5 unmount/render).
  - `apps/web/src/__tests__/zero-dead-buttons-and-silent-catches-audit.test.tsx` : **7 passed** (0 dead buttons, 0 silent catches).
  - `apps/web/src/__tests__/i18n-and-shell.test.tsx` : **26 passed** (zéro jargon, 0 régression, parité stricte FR/EN).
  - `apps/web/src/__tests__/design-system-look-and-feel-isolation.test.tsx` : **4 passed** (0 variable CSS manquante, séparation stricte des tokens).
- **Qualité statique & Architecture** :
  - `ruff check .` & `ruff format --check .` : **All checks passed, 879 files already formatted**.
  - `mypy --strict packages/orcia-core packages/orcia-connectors apps/api apps/worker` : **Success: no issues found in 372 source files**.
  - `lint-imports` : **5 contracts kept, 0 broken**.
  - `test_openapi_contract.py` : **2 passed** (`0-diff` gate respecté).
  - `pnpm site:sync && pnpm site:check` : **59/59 capacités live vérifiées, 0 findings**.

### 3.3 Validation & Procédure de Test sur Toute la Pyramide (`AD-17`)
- **Couche 1a & 1b** : Modèles d'audit, déduplication et idempotence, scrubbing sensible `DEC-SEC-01`, survie au F5 prouvée par unmount/render.
- **Couche 2** : Rejet automatique des `UPDATE` et `DELETE` sur PostgreSQL 18 conteneurisé par le déclencheur `prevent_audit_ledger_mutation()`.
- **Couche 3** : Contrat d'interface OpenAPI 3.1 validé sans divergence via `test_openapi_contract.py`.
- **Couche Sécurité / Red-Team** : Absence totale de fuite de jetons ou clés secrètes canari dans le journal d'audit (`test_story_6_1_canary_leak_and_scope_guard.py` & `test_api_security_baseline.py`).
- **Couche 5** : Écran `/activity` direction C réhydraté, barre d'exportation de provenance, téléchargement des dossiers scellés JSON/Markdown.
