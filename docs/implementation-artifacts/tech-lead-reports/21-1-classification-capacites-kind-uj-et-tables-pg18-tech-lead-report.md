# Story 21.1 — Classification des 65 Capacités (`kind: feature | foundation`, `e2e_exempt_reason`, `uj`, `db_tables`, `read_only_surface`) & Validation de Schéma dans `capabilities_registry.py`

- **Date** : 2026-11-18
- **Story / Clé Sprint** : `21-1-classification-65-capacites-feature-foundation-et-schema-capabilities-yaml` (`Epic 21`)
- **Capacité(s)** : `none (hygiène/gouvernance registre)` — classification : `hygiène` (`GEMINI.md` §5)
- **Auteur / Contexte** : Product Manager (`John`) & Tech Lead (`Amelia`) — Story 21.1 (`FR-1`..`FR-36`, `AD-17`, `NFR-TEST-1`). Classifier exhaustivement les `65` capacités de `docs/product/capabilities.yaml` en `kind: feature` (`62`) vs `kind: foundation` (`3`) avec justification `e2e_exempt_reason`, rattachement `uj: [UJ-1..UJ-20]` et cibles SQL réelles `db_tables` (ou `read_only_surface: true`), puis verrouiller ce schéma dans `infra/scripts/capabilities_registry.py`.
- **Commits associés** : Branche `feat/epic-21-user-journeys-e2e-db-audit` (vérification complète effectuée par `21.1-test`, prêt pour commit)

---

## 1. Analyse du Besoin & Étude d'Impact Tech Lead (Pré-Implémentation)

### 1.1 Contexte & Problématique
- **Problématique** : `docs/product/capabilities.yaml` recense `65` capacités (`CAP-001`..`CAP-203`) mais ne distingue pas encore les capacités métier testables bout-en-bout (`kind: feature`) des fondations transverses d'architecture/hygiène/observabilité (`kind: foundation`), ni ne déclare les User Journeys (`UJ-1`..`UJ-20`) et les tables PostgreSQL 18 cibles pour la vérité terrain E2E.
- **Comportement attendu vs actuel** :
  - Actuellement : `validate_registry()` vérifie uniquement `id`, `title`, `origin`, `origin_ref`, `status`, `tests` (existence sur disque), `verification: runtime` et `fr` (`FR-1`..`FR-36`).
  - Attendu : chaque capacité déclare `kind: feature | foundation` ; les `3` fondations (`CAP-006`, `CAP-100`, `CAP-202`) portent `e2e_exempt_reason` ; les `62` capacités `feature` déclarent `uj: [UJ-1..UJ-20]` et soit `db_tables: [...]` (noms exacts issus des migrations Alembic), soit `read_only_surface: true` pour les surfaces exclusivement en lecture.
- **Contraintes d'architecture** : `infra/scripts/capabilities_registry.py` doit rester sous `< 250` lignes (actuellement `136` lignes), préserver la rétrocompatibilité des signatures (`validate_registry`, `check_coverage`, `capability_test_stats`, `run_registry_check`) appelées par `infra/scripts/sync_site_catalog.py` et `tests/unit/test_capabilities_registry.py`. Note : la validation croisée exacte des `UJ` contre `prd.md` est portée par la Story 21.3 une fois que la Story 21.2 aura rédigé `UJ-13`..`UJ-20` ; en Story 21.1, `validate_registry()` valide le format `UJ-1`..`UJ-99`.

### 1.2 Exploration, Analyse d'Impact GitNexus, Factorisation & Dette Technique
- **Analyse d'Impact GitNexus (`gitnexus_query`, `gitnexus_context`, `gitnexus_impact` sur `/home/romain/Documents/Projects/ORCIA`)** :
  - `node .gitnexus/run.cjs` a échoué dans l'environnement `pnpm dlx` (`ERR_INVALID_ARG_TYPE`), l'analyse a donc été conduite via les outils MCP GitNexus (`query`, `context`, `impact` avec `repo: "/home/romain/Documents/Projects/ORCIA"`) complétée par introspection `grep` du dépôt.
  - Fichiers/symboles impactés : `infra/scripts/capabilities_registry.py` (`validate_registry`, `run_registry_check`, `load_registry`, `capability_test_stats`) et `tests/unit/test_capabilities_registry.py`.
  - Appelants directs (`upstream`) : `infra/scripts/sync_site_catalog.py` (lignes 250, 828, 831 : `load_registry`, `run_registry_check`, `capability_test_stats`) et `tests/unit/test_capabilities_registry.py` (chargement dynamique via `importlib.util`). Risque d'impact applicatif nul (outil de gouvernance CI uniquement) ; risque de rupture ciblé sur le helper `_cap()` de `tests/unit/test_capabilities_registry.py` qui devra fournir les champs `kind`/`uj`/`db_tables` (traité par le sous-agent `21.1-test`).
- **Exploration & Chiffres Clés (Migrations Alembic PostgreSQL 18)** :
  - Extraction exhaustive des `CREATE TABLE` sur les `54` fichiers de `infra/migrations/versions/*.py` : **`74` tables PostgreSQL 18 réelles** recensées (`assistant_folder_shares`, `assistant_folders`, `assistant_threads`, `audit_ledger`, `auth_login_challenges`, `autonomous_post_hoc_audits`, `autonomy_contracts`, `blackboard_snapshots`, `catalog_acl_entries`, `catalog_items`, `chunk_approvals`, `claim_check_artifacts`, `code_graph_edges`, `connector_schemes`, `datasource_webhook_deliveries`, `declarative_pack_bundles`, `domain_events_outbox`, `enterprise_connectors`, `finops_budget_overrides`, `finops_connector_quotas`, `finops_scope_budgets`, `finops_workflow_baselines`, `gate_evaluations`, `human_anchor_signatures`, `human_arbitration_requests`, `iam_accounts`, `inference_attempts`, `kb_chunks`, `kb_documents`, `kb_stale_alerts`, `llm_model_endpoints`, `ontology_axioms`, `ontology_concepts`, `ontology_promotion_proposals`, `ontology_rejected_candidates`, `ontology_relations`, `org_units`, `permission_broker_policies`, `permission_broker_tickets`, `platform_auth_settings`, `platform_settings`, `rag_reindexing_jobs`, `rag_reindexing_pending_ingestions`, `reflexive_execution_sessions`, `resource_leases`, `role_permission_grants`, `run_lock_manifests`, `step_executions`, `system_bootstrap_runs`, `task_notifications`, `transverse_groups`, `trigger_webhook_deliveries`, `tripartite_trace_edges`, `upstream_challenges`, `user_connector_passthrough_tokens`, `user_mcp_tokens`, `user_onboarding_states`, `user_passthrough_credentials`, `user_preferences`, `user_transverse_groups`, `users`, `vsm_definitions_v2`, `wizard_sessions`, `workflow_definitions`, `workflow_definitions_v2`, `workflow_runs`, `workflow_triggers`, `workspace_customization_overrides`, `workspace_datasources`, `workspace_exception_waivers`, `workspace_invitations`, `workspace_llm_tier_mappings`, `workspace_memberships`, `workspaces`).
  - Inventaire de `docs/product/capabilities.yaml` : `65` entrées (`CAP-001`..`CAP-203`), dont `3` fondations (`CAP-006`, `CAP-100`, `CAP-202`) et `62` fonctionnalités métier (`kind: feature`).
- **Opportunités de Factorisation & Résorption de Dette Technique Naissante** :
  - Extraction d'un helper privé `_validate_kind_fields(cap_id, cap)` dans `infra/scripts/capabilities_registry.py` afin de maintenir `validate_registry()` lisible (complexité McCabe maîtrisée) et garder le module largement sous le plafond de `250` lignes.
  - Aucune dette technique nouvelle créée ; la dette de taille de `sync_site_catalog.py` (`883` lignes) est déjà planifiée en Story 21.3.

---

## 2. Plan d'Implémentation

### 2.1 Schéma de Données & Migrations Alembic (`infra/migrations/versions/...`)
- Non applicable : aucune table ni colonne PostgreSQL modifiée en Story 21.1 (audit en lecture seule des `74` tables existantes dans `infra/migrations/versions/*.py`).

### 2.2 Noyau Métier Hexagonal, Orchestration & Workers (`packages/orcia-core/`, `apps/worker/`, `infra/sandbox/`)
- Non applicable : le registre de gouvernance vit dans `docs/product/capabilities.yaml` et `infra/scripts/capabilities_registry.py`.
- `infra/scripts/capabilities_registry.py` (`< 250` lignes) :
  - Ajouter `KINDS = {"feature", "foundation"}` et `UJ_PATTERN = re.compile(r"UJ-[1-9]\d?")`.
  - Étendre `validate_registry()` via `_validate_kind_fields()` pour exiger `kind`, `e2e_exempt_reason` (si `foundation`), `uj` + (`db_tables` non vide OU `read_only_surface: true`) (si `feature`).
  - Préserver à l'identique les signatures publiques (`validate_registry`, `check_coverage`, `capability_test_stats`, `run_registry_check`).

### 2.3 Couche Backend API, Sécurité & Contrats (`apps/api/`, `packages/api-client/`)
- Non applicable : aucune route FastAPI ni schéma OpenAPI modifié.
- Mise à jour de `docs/product/capabilities.yaml` (`65` capacités) en conservant intacts les champs `tests:` et `verification:` existants :
  - `CAP-006`, `CAP-100`, `CAP-202` $\rightarrow$ `kind: foundation` + `e2e_exempt_reason`.
  - Les `62` autres capacités $\rightarrow$ `kind: feature` + `uj: [...]` aligné sur `UJ-1`..`UJ-20` + `db_tables: [...]` (uniquement parmi les `74` tables PG18 vérifiées) ou `read_only_surface: true` (`CAP-066`, `CAP-068`).

### 2.4 Interface Utilisateur & Expérience (`apps/web/`)
- Non applicable : aucune vue React ni composant `@orcia/ui` modifié en Story 21.1.
- La synchronisation du manifeste `/showcase` (`pnpm site:sync`) ne sera déclenchée qu'après mise à jour des tests unitaires par le sous-agent `21.1-test`.

### 2.5 Analyse d'Impact sur la Pyramide des Tests (`AD-17` — Couches 1 à 5 + Sécurité, Obligatoire)
- **Couche 1a (Unitaires Python `tests/unit/`) & Couche 1b (Unitaires/Composants TS `Vitest`)** : `tests/unit/test_capabilities_registry.py` (mis à jour et exécuté par le sous-agent `21.1-test` pour adapter `_cap()` et couvrir tous les cas nominaux et de rejet Story 21.1).
- **Couche 2 (Intégration Verticale `HTTP FastAPI ➔ PostgreSQL 18`)** : Non applicable (script CI statique).
- **Couche 3 (Contrats OpenAPI 3.1 `0-diff`, Schemathesis & `lint-imports`)** : Vérification `pnpm site:check` + `ruff check` + `mypy --strict infra/scripts/capabilities_registry.py` (exécutés par `21.1-test`).
- **Couche 4 (Evals IA)** : Non applicable.
- **Couche Sécurité / Red-Team** : Non applicable.
- **Couche 5 (E2E Playwright)** : Non applicable directement en 21.1 (Story 21.1 pose le socle de classement pour les Stories 21.4..21.8).

---

## 3. Bilan des Modifications & Résultats (Post-Implémentation)

### 3.1 Fichiers Développés & Modifiés
| Fichier | Nature (Création / Modification / Refactoring) | Description synthétique |
| :--- | :--- | :--- |
| `docs/product/capabilities.yaml` | Modification | Classification exhaustive des `65` capacités (`CAP-001`..`CAP-203`) : `3` `kind: foundation` (`CAP-006`, `CAP-100`, `CAP-202`) avec `e2e_exempt_reason` et `62` `kind: feature` avec `uj` (`UJ-1`..`UJ-20`) et `db_tables` (parmi les `74` tables PG18 réelles) ou `read_only_surface: true` (`CAP-066`, `CAP-068`). |
| `infra/scripts/capabilities_registry.py` | Modification / Refactoring (`178` lignes) | Ajout de `KINDS`, `UJ_PATTERN` et extraction de `_validate_kind_fields()` appelée par `validate_registry()` en conservant les signatures publiques intactes. |
| `tests/unit/test_capabilities_registry.py` | Modification (`187` lignes) | Mise à jour du helper `_cap()` (`kind="feature"`, `uj=["UJ-1"]`, `db_tables=["users"]`) et ajout de `5` tests unitaires conformes à `docs/testing-strategy.md` §6 (cas réel `65` = `3` + `62`, rejet `kind`, `e2e_exempt_reason`, `uj`, `db_tables`/`read_only_surface`). |
| `docs/implementation-artifacts/sprint-status.yaml` | Modification | Passage de `21-1-classification-65-capacites-feature-foundation-et-schema-capabilities-yaml` à `done` et mise à jour de `last_updated` (`11-18-2026 08:56`). |
| `docs/implementation-artifacts/tech-lead-reports/README.md` | Modification | Enregistrement du rapport Story `21.1` dans l'index des rapports Tech Lead. |
| `docs/implementation-artifacts/tech-lead-reports/21-1-classification-capacites-kind-uj-et-tables-pg18-tech-lead-report.md` | Création | Rapport Tech Lead complet (Sections 1, 2 et 3). |
| `apps/web/src/generated/orciaSiteManifest.ts`, `docs/site-catalog/index.html`, `dist/orcia-site/index.html` | Modification (générés) | Artefacts du catalogue synchronisés par `pnpm site:sync`. |

### 3.2 Résultats Chiffrés, Métriques & Qualité
- **Registre des capacités (`docs/product/capabilities.yaml`)** : `65` capacités validées (`3` `foundation` + `62` `feature`, `65/65` `live` avec au moins un test référencé, `0` erreur).
- **Volumétrie maîtrisée** : `infra/scripts/capabilities_registry.py` (`178` lignes `< 250`) et `tests/unit/test_capabilities_registry.py` (`187` lignes `< 300`).
- **Tests unitaires Python (`pytest`)** :
  - `.venv/bin/pytest tests/unit/test_capabilities_registry.py tests/unit/test_site_catalog_sync.py` : `17 passed` (`14` tests dans `test_capabilities_registry.py`, `3` tests dans `test_site_catalog_sync.py`).
- **Qualité statique & Architecture** :
  - `.venv/bin/ruff check infra/scripts/capabilities_registry.py tests/unit/test_capabilities_registry.py` : `All checks passed!`
  - `.venv/bin/ruff format --check infra/scripts/capabilities_registry.py tests/unit/test_capabilities_registry.py` : `2 files already formatted`
  - `.venv/bin/mypy --strict infra/scripts/capabilities_registry.py` : `Success: no issues found in 1 source file`
  - `pnpm site:sync && pnpm site:check` : OK (`65/65` capacités `live`, `0` erreur de schéma ni de couverture routes/routeurs)
  - `node .gitnexus/run.cjs analyze --index-only && node .gitnexus/run.cjs detect-changes --scope all --repo .` : échec `ERR_INVALID_ARG_TYPE` dans le wrapper `pnpm dlx` (`node:v25.9.0`), complété par l'outil MCP `gitnexus:detect_changes` (`repo: "/home/romain/Documents/Projects/ORCIA"`, `scope: "all"`) : `risk_level: "low"`, `changed_count: 0`, `affected_count: 0`.

### 3.3 Validation & Procédure de Test sur Toute la Pyramide (`AD-17`)
- **Couche 1a — Tests Unitaires Python (`pytest`)** : `17 passed` sur `tests/unit/test_capabilities_registry.py` et `tests/unit/test_site_catalog_sync.py` (validation réelle des `65` capacités `3 + 62` et de tous les cas de rejet `kind`, `e2e_exempt_reason`, `uj`, `db_tables`/`read_only_surface`).
- **Couche 2 — Intégration Verticale `HTTP ➔ PostgreSQL 18`** : Non applicable (outillage statique de gouvernance CI).
- **Couche 3 — Contrats, Schémas & Gouvernance Statique** : `ruff check`, `ruff format --check`, `mypy --strict` et `pnpm site:sync && pnpm site:check` passés à `0` erreur.
- **Couche 4 — Orchestration IA & Evals Golden Dataset** : Non applicable.
- **Couche Sécurité / Red-Team** : Non applicable.
- **Couche 5 — E2E Navigateur Playwright** : Non applicable directement en Story 21.1 (les champs `kind`, `uj` et `db_tables` posent le socle des Stories 21.3..21.8).
