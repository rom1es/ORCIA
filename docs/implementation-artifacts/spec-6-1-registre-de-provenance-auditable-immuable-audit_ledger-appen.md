---
story_key: "6-1-registre-de-provenance-auditable-immuable-audit_ledger-appen"
status: "ready-for-dev"
epic: "epic-6"
title: "Story 6.1 : Registre de Provenance Auditable Immuable (audit_ledger Append-Only), Traçabilité des Tests à Chaud (ADMIN_CONNECTION_TEST) & Export de Conformité JSON/Markdown"
date: "2026-11-16"
authors:
  - "Winston (bmad-agent-architect 🏗️)"
  - "Sally (bmad-agent-ux-designer 🎨)"
capabilities:
  - "CAP-065"
  - "CAP-200"
---

# Spécification d'Implémentation — Story 6.1 : Registre de Provenance Auditable Immuable (`audit_ledger` Append-Only), Traçabilité des Tests à Chaud (`ADMIN_CONNECTION_TEST`) & Export de Conformité JSON/Markdown

- **Story Key** : `6-1-registre-de-provenance-auditable-immuable-audit_ledger-appen`
- **Epic** : Epic 6 — Gouvernance Exécutive, Provenance Auditable Immuable, FinOps Consolidé & Réversibilité Humaine
- **Capacités rattachées** : `CAP-065` (Rebasage pérenne de la source `/activity` vers `audit_ledger`), `CAP-200` (Socle de traçabilité FinOps)
- **Références architecturales** : `FR-25`, `AD-12`, `AD-17`, `AD-19`, `AD-21`, `AD-23`, `NFR-SEC-3`, `NFR-SEC-4`, `Principe M.2`, `CAP-ACT-3`

---

## 1. Intent & Boundaries

### 1.1 Problem & Approach
L'audit du codebase réalisé dans le cadre de `CAP-ACT-3` démontre que la table `audit_ledger` n'existe pas en base de données et que l'écran `/activity` (`CAP-065`) s'appuie sur une structure en mémoire volatile (`platformSetupStore.auditEvents`), sans garantie d'immuabilité réglementaire ni persistance après redémarrage.
Cette story crée la table `audit_ledger` dans PostgreSQL 18, protégée par un trigger d'immuabilité absolue `BEFORE UPDATE OR DELETE RAISE EXCEPTION` (`NFR-SEC-3`), et met en place un abonné Outbox idempotent (`orcia_core/audit_finops`) qui consomme les événements d'orchestration (`StepCompleted`, `GateEvaluated`, `ArtifactProduced`, `RunTerminated`, `SettingsChanged`, `AdminConnectionTested`).
Elle prend en charge la traçabilité des essais à chaud d'administrateurs sous `actor_type: ADMIN_CONNECTION_TEST` (`run_id: None`), expose les routes API paginées et d'export scellé (`JSON`/`Markdown`), découpe `ActivityLogExplorerView.tsx` pour préserver le seuil `< 350` lignes tout en maintenant 100 % des `data-testid` existants, et rebase la route `apps/web/src/routes/activity.tsx` sur l'API PostgreSQL avec survie au rechargement (`F5`).

### 1.2 Boundaries & Constraints
- **Toujours (`Always`)** :
  - Générer les clés primaires `audit_ledger.id` en `UUIDv7` via `uuid-utils`.
  - Protéger la table `audit_ledger` par le trigger PostgreSQL 18 `prevent_audit_ledger_mutation` interdisant formellement tout `UPDATE` ou `DELETE` (`NFR-SEC-3`).
  - Garantir l'idempotence stricte à l'ingestion Outbox par contrainte d'unicité sur `source_event_id` (`ON CONFLICT (source_event_id) DO NOTHING`).
  - Sanctuariser `audit_ledger` contre toute suppression dans `infra/scripts/maintenance/09_reset_db_first_boot.py` (inscrite dans `PROTECTED_TABLES`).
  - Isoler les essais du banc de test sous `actor_type = 'ADMIN_CONNECTION_TEST'` avec `run_id = NULL` pour ne jamais polluer les budgets de production des Espaces.
  - Filtrer et scrubber tout secret ou canari (`DEC-SEC-01`, `NFR-SEC-4`) avant écriture dans `metadata_jsonb`.
  - Conserver 100 % des attributs `data-testid="activity-log-*"` lors du découpage de `ActivityLogExplorerView.tsx`.
- **Jamais (`Never`)** :
  - Ne jamais exécuter de requête `UPDATE` ou `DELETE` sur `audit_ledger`, ni désactiver le trigger d'immuabilité dans les migrations de production.
  - Ne jamais importer `orcia_core.orchestration`, `orcia_core.bootstrap` ou `orcia_core.gates` dans `orcia_core.audit_finops` (violation `AD-19 Contract 2`).
  - Ne jamais logger ni persister de jetons d'accès ou clés d'API en clair dans `summary` ou `metadata_jsonb`.
  - Ne jamais utiliser de mock SQLite ou de store en mémoire pour valider les tests d'intégration Couche 2.

### 1.3 I/O & Edge-Case Matrix

| Contexte / Événement | Entrée / Paramètre | Résultat Attendu | Code Erreur / Comportement |
| :--- | :--- | :--- | :--- |
| Ingestion Outbox standard | `StepCompleted` avec `event_id` | Insertion d'une ligne dans `audit_ledger` avec hashes SHA-256 et CAS SeaweedFS | `201 Created` équivalent SQL |
| Doublon d'événement Outbox | `StepCompleted` avec même `source_event_id` | Aucun doublon inséré, accusé de réception immédiat | `ON CONFLICT DO NOTHING` (Idempotence) |
| Essai banc de test administrateur | `AdminConnectionTested` depuis `mcp_and_test_bench.py` | Ligne insérée avec `actor_type: 'ADMIN_CONNECTION_TEST'`, `run_id: NULL` | Zéro imputation au budget d'Espace |
| Tentative d'altération SQL | `UPDATE audit_ledger SET summary = 'hack'` | Échec immédiat de la transaction | `ERR_AUDIT_LEDGER_IMMUTABLE` (Trigger PG18) |
| Tentative de suppression SQL | `DELETE FROM audit_ledger WHERE id = '...'` | Échec immédiat de la transaction | `ERR_AUDIT_LEDGER_IMMUTABLE` (Trigger PG18) |
| Rechargement navigateur `F5` | Consultation de `/activity` | Données réhydratées depuis `GET /api/v1/audit/ledger` | Survie au rechargement sans perte |
| Export de conformité inconnu | `GET /api/v1/audit/ledger/unknown-run-id/export` | Envelope RFC 9457 `404 Not Found` | `ERR_AUDIT_RUN_NOT_FOUND` |

---

## 2. Acceptance Criteria (Given / When / Then)

### Critère 1 : Immuabilité Absolue & Schéma Relationnel (`AD-12`, `NFR-SEC-3`)
- **Given** la migration Alembic `20261116_0601_story_6_1_audit_ledger_append_only.py` appliquée sur PostgreSQL 18 (succédant à `20261115_2359`),
- **When** une requête SQL `UPDATE` ou `DELETE` est tentée sur la table `audit_ledger`,
- **Then** le trigger PostgreSQL `prevent_audit_ledger_mutation` lève immédiatement une exception `ERR_AUDIT_LEDGER_IMMUTABLE`, annulant la transaction sans modifier la table.

### Critère 2 : Ingestion Outbox Asynchrone Idempotente (`AD-19`, `NFR-SEC-4`)
- **Given** des événements déposés dans `domain_events_outbox` (`StepCompleted`, `GateEvaluated`, `ArtifactProduced`, `RunTerminated`, `SettingsChanged`, `AdminConnectionTested`),
- **When** l'abonné `AuditLedgerOutboxSubscriber` traite le flux d'événements,
- **Then** il insère chaque entrée dans `audit_ledger` avec horodatage UTC ISO-8601, les empreintes SHA-256 du contrat de workflow, du pré-prompt système et de l'état `run_lock.json`, ainsi que les références CAS SeaweedFS,
- **And** en cas de retry ou rejeu de l'Outbox, la contrainte d'unicité `source_event_id` absorbe les doublons sans erreur (`ON CONFLICT DO NOTHING`),
- **And** aucun secret ni canari n'est persisté en clair dans `metadata_jsonb` (`DEC-SEC-01`).

### Critère 3 : Traçabilité Isolée des Tests à Chaud (`ADMIN_CONNECTION_TEST`, Principe M.2)
- **Given** un administrateur testant un modèle IA ou un connecteur MCP depuis le banc de test (`/api/v1/settings/connectors/test-and-discover` ou `/api/v1/ai-models-hub/test-endpoint`),
- **When** le test s'exécute avec succès ou échec,
- **Then** un événement `AdminConnectionTested` est émis dans l'Outbox,
- **And** l'entrée est inscrite dans `audit_ledger` avec `actor_type: 'ADMIN_CONNECTION_TEST'`, `run_id: NULL` et `actor_id: user.id`, sans impacter les budgets de production.

### Critère 4 : Dossier de Provenance & Export Scellé JSON/Markdown
- **Given** un auditeur habilité consultant `/activity` ou interrogeant l'API pour un Run terminé,
- **When** il appelle `GET /api/v1/audit/ledger/{run_id}/export?format=json` ou `format=md`,
- **Then** le système retourne le dossier complet de provenance attestant de l'alignement sur `run_lock_manifests.manifest_sha256` et certifiant qu'aucune ressource absente du lock n'a été exécutée.

### Critère 5 : Rebasage de `/activity`, Découpage UI & Survie au F5
- **Given** l'écran `/activity` (`apps/web/src/routes/activity.tsx`),
- **When** l'utilisateur navigue sur la page ou la rafraîchit (`F5`),
- **Then** les événements sont chargés via `@orcia/api-client` (`GET /api/v1/audit/ledger`),
- **And** le composant `ActivityLogExplorerView` conserve 100 % de ses `data-testid` existants après extraction de `ActivityLogFiltersBar.tsx` et `ActivityLogProvenanceExportBar.tsx` (< 350 lignes par fichier).

---

## 3. Code Map

```
ORCIA/
├── infra/
│   ├── migrations/versions/
│   │   └── 20261116_0601_story_6_1_audit_ledger_append_only.py  [CRÉATION - Migration Alembic]
│   └── scripts/maintenance/
│       └── 09_reset_db_first_boot.py                            [VÉRIFICATION - audit_ledger dans PROTECTED_TABLES]
├── packages/
│   ├── orcia-core/src/orcia_core/
│   │   ├── kernel/
│   │   │   ├── _finops_audit_events.py                          [CRÉATION - Extraction événements d'audit < 350 l.]
│   │   │   └── events.py                                        [MODIFICATION - Réexport finops audit events]
│   │   ├── ports/
│   │   │   └── finops_telemetry.py                              [CRÉATION - Protocoles et DTOs hexagonaux purs]
│   │   └── audit_finops/
│   │       ├── __init__.py                                      [MODIFICATION - Façade publique du domaine]
│   │       ├── models.py                                        [CRÉATION - DTOs & Entités du registre d'audit]
│   │       ├── outbox_subscriber.py                             [CRÉATION - Consommateur idempotent Outbox]
│   │       ├── provenance_exporter.py                           [CRÉATION - Générateur JSON/MD scellé]
│   │       └── _internal/
│   │           └── sql_audit_ledger.py                          [CRÉATION - Requêtes SQL asynchrones pures]
│   └── ui/src/
│       ├── index.ts                                             [MODIFICATION - Exports des briques d'audit]
│       └── primitives/
│           ├── ActivityLogExplorerView.tsx                      [REFACTORING - Vue allégée < 300 lignes]
│           ├── ActivityLogFiltersBar.tsx                        [CRÉATION - Barre de filtres extraite]
│           └── ActivityLogProvenanceExportBar.tsx               [CRÉATION - Barre d'export & provenance]
├── apps/
│   ├── worker/src/orcia_worker/
│   │   └── outbox_relay.py                                      [MODIFICATION - Ingestion audit_ledger]
│   ├── api/src/orcia_api/
│   │   ├── dependencies/
│   │   │   ├── __init__.py                                      [MODIFICATION - Export get_audit_ledger_service]
│   │   │   └── orchestration_and_settings.py                    [MODIFICATION - Provider get_audit_ledger_service]
│   │   ├── schemas/
│   │   │   └── audit_finops.py                                  [CRÉATION - Schémas Pydantic RFC 9457]
│   │   └── routers/
│   │       ├── audit_ledger.py                                  [CRÉATION - Router GET /api/v1/audit/ledger]
│   │       ├── mcp_and_test_bench.py                            [MODIFICATION - Émission AdminConnectionTested]
│   │       ├── ai_models_hub.py                                 [MODIFICATION - Émission AdminConnectionTested]
│   │       └── settings_and_studio.py                           [MODIFICATION - Émission SettingsChanged]
│   └── web/src/
│       └── routes/
│           └── activity.tsx                                     [MODIFICATION - Câblage GET /api/v1/audit/ledger]
└── tests/
    ├── unit/
    │   ├── test_story_6_1_audit_ledger_core.py                  [CRÉATION - Tests unitaires core & exporter]
    │   └── test_story_6_1_outbox_subscriber.py                  [CRÉATION - Tests scrubbing et idempotence]
    └── integration/
        └── test_story_6_1_audit_ledger_postgres18.py            [CRÉATION - Testcontainers PG18 + SeaweedFS]
```

---

## 4. Ordered Tasks (Dependencies First)

### Tâche 1 : Migration Alembic & Sanctuarisation PostgreSQL 18
- Créer `infra/migrations/versions/20261116_0601_story_6_1_audit_ledger_append_only.py` avec `down_revision = "20261115_2359"`.
- Définir la table `audit_ledger` avec toutes ses colonnes (UUIDv7, `NUMERIC(12, 6)`), contraintes CHECK, index partiels et la fonction/trigger `prevent_audit_ledger_mutation`.
- Mettre à jour `ck_domain_events_outbox_event_type` pour inclure les 5 nouveaux types d'événements outbox (`AdminConnectionTested`, etc.).
- Valider la présence de `audit_ledger` dans `PROTECTED_TABLES` de `infra/scripts/maintenance/09_reset_db_first_boot.py`.

### Tâche 2 : Ports Hexagonaux, Découpage Kernel & Événements Outbox
- Créer `packages/orcia-core/src/orcia_core/ports/finops_telemetry.py` (Protocoles purs `AuditLedgerSinkPort`, DTOs `FinopsCostLedgerEntry`).
- Créer `packages/orcia-core/src/orcia_core/kernel/_finops_audit_events.py` (< 350 lignes) pour isoler les événements d'audit et les réexporter dans `kernel/events.py`.

### Tâche 3 : Domaine Métier `orcia_core/audit_finops` & Requêtes SQL Asynchrones
- Définir les modèles dans `packages/orcia-core/src/orcia_core/audit_finops/models.py`.
- Développer `packages/orcia-core/src/orcia_core/audit_finops/_internal/sql_audit_ledger.py` avec requêtes `sa.text` d'insertion idempotente et sélection paginée.
- Développer `outbox_subscriber.py` avec liste blanche anti-secrets (`DEC-SEC-01`, `scrub_sensitive_dict`) garantissant zéro canari en base.
- Développer `provenance_exporter.py` pour produire les dossiers JSON et Markdown scellés avec vérification du hash `run_lock.json`.

### Tâche 4 : Intégration Worker & Points d'Émission API
- Câbler l'ingestion dans `apps/worker/src/orcia_worker/outbox_relay.py`.
- Émettre l'événement `AdminConnectionTested` lors des tests à chaud dans `mcp_and_test_bench.py` et `ai_models_hub.py` (`actor_type: ADMIN_CONNECTION_TEST`, `run_id: None`).
- Émettre l'événement `SettingsChanged` lors des modifications de paramètres dans `settings_and_studio.py`.

### Tâche 5 : Routeur FastAPI, Schémas RFC 9457 & OpenAPI SDK
- Définir les schémas Pydantic dans `apps/api/src/orcia_api/schemas/audit_finops.py`.
- Créer `apps/api/src/orcia_api/routers/audit_ledger.py` exposant `GET /api/v1/audit/ledger`, `GET /api/v1/audit/ledger/{run_id}/provenance` et `GET /api/v1/audit/ledger/{run_id}/export`.
- Injecter le service dans `apps/api/src/orcia_api/dependencies/orchestration_and_settings.py` et monter le routeur dans `main.py`.
- Exécuter `.venv/bin/python scripts/export_openapi.py` et vérifier le `0-diff` SDK `@orcia/api-client`.

### Tâche 6 : Découpage UI `@orcia/ui`, Câblage de `/activity` & Survie au F5
- Extraire `ActivityLogFiltersBar.tsx` et `ActivityLogProvenanceExportBar.tsx` de `ActivityLogExplorerView.tsx` en conservant 100 % des `data-testid` existants.
- Câbler `apps/web/src/routes/activity.tsx` sur `@orcia/api-client` (`GET /api/v1/audit/ledger`).
- Intégrer le tiroir d'inspection de la provenance et le téléchargement des exports JSON/Markdown.
- Ajouter un test Vitest démontrant la survie au rechargement de page (`unmount()` + `render()`).

### Tâche 7 : Pyramide des Tests `AD-17` & Vérifications Anti-Régression
- Couche 1a : Tests unitaires Python (`pytest tests/unit/test_story_6_1_*.py`) avec couverture $\ge 90\%$.
- Couche 1b : Tests composants Vitest (`pnpm --filter @orcia/ui test`, `pnpm --filter web test`).
- Couche 2 : Tests d'intégration `testcontainers` PostgreSQL 18 + SeaweedFS (`tests/integration/test_story_6_1_audit_ledger_postgres18.py`) vérifiant l'insertion réelle, le déclenchement de l'erreur sur tentative de `UPDATE`/`DELETE`, et l'absence de secret canari.
- Couche 3 : Vérification `lint-imports` (5 contrats validés, 0 violation) et `lint_spine.py`.
