# 2026-11-18 — Correctifs Revue d'Architecture (`VALIDATE`) Epic 20

- **Date** : 2026-11-18
- **Story / Clé Sprint** : `2026-11-18-epic-20-validate-fixes` (`Epic 20` / `Correctifs VALIDATE`)
- **Capacité(s)** : `CAP-010`, `CAP-030`, `CAP-034`, `CAP-036`, `CAP-202` — classification : `hygiène` / `feature`
- **Auteur / Contexte** : Résorption intégrale des 10 findings (`3 BLOCKING`, `4 MAJOR`, `3 MINOR`) issus de la revue d'architecture finale (`VALIDATE`) sur l'Epic 20 (`Stories 20.1, 20.2, 20.3, 20.4`), incluant isolation stricte ontologique L1–L4 (`AD-7`, `AD-19`), sécurité IAM/Audit (`AD-6`, `AD-21`), découpage volumétrique `<= 350` L et conformité i18n `@orcia/ui`.
- **Commits associés** : *en cours d'implémentation*

---

## 1. Analyse du Besoin & Étude d'Impact Tech Lead (Pré-Implémentation)

### 1.1 Contexte & Problématique
La revue d'architecture finale (`VALIDATE`) sur l'Epic 20 a identifié **10 écarts** répartis sur trois niveaux de sévérité :
1. **`BLOCKING-1` (`Story 20.2`)** : `concept_key` non scopé (`slugifyGlossaryConceptKey` global par terme) + `SQL_FIND_CONCEPT_FOR_UPSERT` pouvant matcher et écraser/rétrograder un concept existant d'un autre niveau/périmètre (`1_ENTERPRISE` ou autre BU) au lieu de lever `HTTP 409 ERR_ONTOLOGY_CONFLICT`.
2. **`BLOCKING-2` (`Story 20.2`)** : Injection arbitraire possible de `target_scope_id` à la création de promotion (`resolve_next_promotion_target` faisait confiance à `explicit_target_scope_id`), `GET /api/v1/ontology-rag/state` non filtré/non authentifié, et `POST /api/v1/ontology-rag/ontology/promote` (`promote_concept`) vérifiant uniquement le rôle sans confiner `target_scope_id` au périmètre dirigé.
3. **`BLOCKING-3` (`Story 20.1`)** : `GET /api/v1/settings/iam/accounts` accessible à tout utilisateur authentifié au lieu d'être restreint à `PLATFORM_ADMIN` / `SECOPS` (`403` pour `BU_LEAD`, `TEAM_LEAD`, `CONTRIBUTOR`, `OBSERVER`).
4. **`MAJOR-4` (`Story 20.2`)** : `can_read_ontology_item` fail-open (`ws is None -> True`) au niveau `4_WORKSPACE`/`3_WORKSPACE`, et écriture erronée de `workspace_id` dans `audit_ledger.org_unit_id` par `record_ontology_audit_event_pg`.
5. **`MAJOR-5` (`Story 20.2`)** : Contournements de façade domaine (`evaluator._memberships  # noqa: SLF001` et imports directs `orcia_core.ontology._internal.*` dans les routeurs API).
6. **`MAJOR-6` (`Story 20.1`)** : `_finops_auth_guards.py` utilisait `elif org_scope.direct_led_team_ids:` excluant les équipes externes dirigées lorsqu'un utilisateur est également `BU_LEAD` sur une autre BU (remplacement par l'union `governed_bu_ids | direct_led_team_ids`).
7. **`MAJOR-7` (`Story 20.1 / 20.2`)** : Volumétrie `> 400` L sur `SettingsOrganizationUnitsBlock.tsx` (`476` L) et `OntologyAndKbExplorerPanel.tsx` (`410` L), et absence d'accès UI `SECOPS` à `Configuration > Comptes & Habilitations` (`/settings?tab=iam`).
8. **`MINOR-8` (`Story 20.2 / 20.3`)** : `WorkspaceGlossaryAndOntologyTab.tsx` devinait `scopeId` depuis `orgUnits` au lieu d'utiliser `writableScopes` backend ; ternaires `isFr ? ... : ...` codés en dur dans `@orcia/ui` (`UserSettingsProfileAndPassthroughTabs.tsx`, `UserSettingsPassthroughTab.tsx`) ; faux fallback `setPassthroughTested(true)` dans `UserSettingsModalDialog.tsx`.
9. **`MINOR-9` (`Story 20.2`)** : IDs statiques factices (`scope-bu-digital`, `scope-subteam-checkout`, `scope-team-core`, `ws-solution-paiement`) dans `_ontology_promotions_handlers.py`.
10. **`MINOR-10` (`Story 20.4`)** : Prise en compte uniquement de `unit_type == "BU"` au lieu de `("BU", "TRIBE")` dans `_sql_user_profile_orgs.py`.

### 1.2 Exploration, Analyse d'Impact GitNexus, Factorisation & Dette Technique
- **Symboles impactés** :
  - Backend : `SQL_FIND_CONCEPT_FOR_UPSERT`, `upsert_concept_pg`, `record_ontology_audit_event_pg`, `can_read_ontology_item`, `resolve_next_promotion_target`, `OntologyGovernanceService.promote_concept`, `get_ontology_and_rag_state`, `promote_ontology_proposal`, `list_iam_accounts`, `enforce_audit_read_access`, `MatrixPermissionEvaluator`, `load_user_identity_and_orgs`.
  - Frontend : `ontologyApiBridge.ts`, `OntologyFeaturePanel`, `WorkspaceGlossaryAndOntologyTab.tsx`, `settingsRbacResolver.ts`, `ShellContainer.tsx`, `SettingsOrganizationUnitsBlock.tsx`, `OntologyAndKbExplorerPanel.tsx`, `UserSettingsProfileAndPassthroughTabs.tsx`, `UserSettingsPassthroughTab.tsx`, `UserSettingsModalDialog.tsx`, `shell_and_search_labels.ts`.
- **Factorisation & Découpage** :
  - Extraction de `useOrgUnitsBlockActions.ts` hors de `SettingsOrganizationUnitsBlock.tsx` (`476` L $\rightarrow$ `< 250` L).
  - Extraction de `OntologyTripartiteAndStaleSection.tsx` hors de `OntologyAndKbExplorerPanel.tsx` (`410` L $\rightarrow$ `< 290` L).
  - Introduction de `OntologyScopeConflictError(OntologyConflictError)` (`http_status = 409`, `error_code = "ERR_ONTOLOGY_CONFLICT"`) pour préserver la compatibilité `422` sur les axiomes immuables tout en garantissant `HTTP 409 Conflict` sur les collisions inter-périmètres.
  - Exposition propre des adaptateurs PG18 ontologie via la façade `orcia_core.ontology` (`__all__`) et méthode publique `MatrixPermissionEvaluator.list_memberships()`.

---

## 2. Plan d'Implémentation

### 2.1 Schéma de Données & Migrations Alembic (`infra/migrations/versions/`)
- Aucune nouvelle migration requise : les tables `ontology_concepts`, `ontology_promotion_proposals`, `audit_ledger`, `iam_accounts` et `org_units` disposent déjà des colonnes nécessaires ; les correctifs portent sur la sémantique des requêtes (`COALESCE(scope_id, '')`, `workspace_id` vs `org_unit_id` dans `audit_ledger`) et la conformité `TRIBE`.

### 2.2 Noyau Métier Hexagonal, Orchestration & Workers (`packages/orcia-core/`)
- `packages/orcia-core/src/orcia_core/ontology/errors.py` : ajout de `OntologyScopeConflictError(OntologyConflictError)` (`http_status=409`, `error_code="ERR_ONTOLOGY_CONFLICT"`).
- `packages/orcia-core/src/orcia_core/ontology/_internal/sql_ontology_queries.py` & `sql_ontology_repository.py` : sélection de `(id, concept_key, level, scope_id)`, idempotence `(LOWER(canonical_term), level, COALESCE(scope_id, ''))`, rejet `409` sur collision inter-périmètres, et dissociation stricte `workspace_id` / `org_unit_id` dans `record_ontology_audit_event_pg`.
- `packages/orcia-core/src/orcia_core/ontology/permissions.py` : fail-closed (`ws is None -> False`) + lecture héritée sur `ws.owner_org_unit_id` / BU ancêtre dans `can_read_ontology_item`, et résolution canonique stricte + rejet `403` si `explicit_target_scope_id != canonical_scope_id` dans `resolve_next_promotion_target`.
- `packages/orcia-core/src/orcia_core/ontology/impact_and_promotion.py` : confinement périmétrique sur `OntologyGovernanceService.promote_concept` et `upsert_concept`, plus méthode publique `save_proposal`.
- `packages/orcia-core/src/orcia_core/ontology/__init__.py` : exposition façade publique du repository PG18 et loader topologie.
- `packages/orcia-core/src/orcia_core/permissions/evaluator.py` : ajout de `list_memberships()`.
- `packages/orcia-core/src/orcia_core/audit_finops/_internal/_sql_user_profile_orgs.py` : inclusion `unit_type in ("BU", "TRIBE")`.

### 2.3 Couche Backend API, Sécurité & Contrats (`apps/api/`, `packages/api-client/`)
- `apps/api/src/orcia_api/errors/registry.py` : enregistrement de `OntologyScopeConflictError` (`409`).
- `apps/api/src/orcia_api/routers/iam_accounts.py` & `_iam_accounts_passwords.py` : garde `PLATFORM_ADMIN` / `SECOPS` sur `GET /api/v1/settings/iam/accounts`.
- `apps/api/src/orcia_api/routers/_finops_auth_guards.py` : union `governed_bu_ids | direct_led_team_ids` et workspaces associés.
- `apps/api/src/orcia_api/routers/ontology_and_rag.py`, `_ontology_promotions_handlers.py`, `_ontology_promotions_helpers.py` : suppression des imports `_internal.*` et accès `_memberships`, authentification + filtrage lecture sur `GET /ontology-rag/state`, confinement `POST /ontology-rag/ontology/promote`, hiérarchie dynamique `OntologyHierarchyResolver`, et audit `workspace_id`/`org_unit_id` exact.

### 2.4 Interface Utilisateur & Expérience (`packages/ui/`, `apps/web/`)
- `apps/web/src/components/ontologyApiBridge.ts`, `apps/web/src/features/ontology/index.tsx`, `apps/web/src/features/workspaces/WorkspaceGlossaryAndOntologyTab.tsx` : génération `slugifyScopedConceptKey(term, level, scopeId)` (`<= 120` car.) et utilisation des `writableScopes` retournés par le backend.
- `apps/web/src/stores/settingsRbacResolver.ts`, `authSessionStore.ts`, `ShellContainer.tsx`, `shellPresets.ts` : accès `SECOPS` à `Configuration > Comptes & Habilitations` (`visibleTabs: ["iam"]`, `canMutate: true`).
- Découpage volumétrique `SettingsOrganizationUnitsBlock.tsx` (`useOrgUnitsBlockActions.ts`) et `OntologyAndKbExplorerPanel.tsx` (`OntologyTripartiteAndStaleSection.tsx`) sous `320` L.
- `packages/ui/src/primitives/UserAccountDropdownTypes.ts`, `UserSettingsProfileAndPassthroughTabs.tsx`, `UserSettingsPassthroughTab.tsx`, `UserSettingsModalDialog.tsx`, `apps/web/src/i18n/locales/shell_and_search_labels.ts` : suppression des ternaires `isFr ? ... : ...` en dur via props `labels`, et suppression du faux fallback `setPassthroughTested(true)`.

### 2.5 Analyse d'Impact sur la Pyramide des Tests (`AD-17` — Couches 1 à 5 + Sécurité, Obligatoire)
- **Couche 1a & 1b** : ajout/mise à jour des tests unitaires Python (`test_story_20_1_org_delegation_and_audit_scope.py`, `test_story_20_2_ontology_permissions_and_promotions.py`, `test_story_20_4_profile_streaks_and_assistant_usage.py`, `test_story_17_3_iam_accounts_and_role_matrix.py`, `test_story_3_2a_modular_monolith_kernel.py`) et TS Vitest (`story-17-1-settings-5-tabs-and-rbac.test.tsx`, `platform-auth-modes-2fa-and-settings-f5.test.tsx`, `story-20-2-glossaire-ontology-and-promotions.test.tsx`, `i18n-and-shell.test.tsx`, `vitestOntologyMockHandlers.ts`).
- **Couche 2 (`testcontainers` PG18)** : validation des 6 suites d'intégration PG18 + assertion SQL sur `audit_ledger.workspace_id` / `org_unit_id` et blocage collision `409 Conflict` sur `ontology_concepts`.
- **Couche 3** : `export_openapi.py --check`, `lint-imports`, `lint_spine.py`.
- **Couche Sécurité** : tests d'isolation `409` écrasement inter-périmètres, `403` injection `target_scope_id`, `403` `GET /settings/iam/accounts` pour non-admin/SecOps, `403` `promote` cross-BU, et filtrage `GET /ontology-rag/state`.

---

## 3. Bilan des Modifications & Résultats (Post-Implémentation)

### 3.1 Tableau des Fichiers Créés / Modifiés

| Couche | Fichier | Action | Volumétrie / Notes |
| --- | --- | --- | --- |
| **Core Ontologie** | `packages/orcia-core/src/orcia_core/ontology/errors.py` | Modifié | Ajout `OntologyScopeConflictError` (`HTTP 409`, `ERR_ONTOLOGY_CONFLICT`) |
| **Core Ontologie** | `packages/orcia-core/src/orcia_core/ontology/_internal/sql_ontology_queries.py` | Modifié | `SQL_FIND_CONCEPT_FOR_UPSERT` (`COALESCE(scope_id, '')`) & `resolve_ontology_audit_scope_uuids` |
| **Core Ontologie** | `packages/orcia-core/src/orcia_core/ontology/_internal/sql_ontology_repository.py` | Modifié | `343` L ; collision inter-périmètres -> `409`, audit `workspace_id`/`org_unit_id` strict |
| **Core Ontologie** | `packages/orcia-core/src/orcia_core/ontology/permissions.py` | Modifié | `346` L ; fail-closed `4_WORKSPACE` (`ws is None -> False`), résolution canonique + rejet `403` `target_scope_id` |
| **Core Ontologie** | `packages/orcia-core/src/orcia_core/ontology/impact_and_promotion.py` | Modifié | Confinement périmétrique `promote_concept`, `upsert_concept` (`409`), méthode publique `save_proposal` |
| **Core Ontologie** | `packages/orcia-core/src/orcia_core/ontology/__init__.py` | Modifié | Façade publique repository PG18 & topologie (suppression imports `_internal` dans API) |
| **Core Permissions** | `packages/orcia-core/src/orcia_core/permissions/evaluator.py` | Modifié | Ajout `MatrixPermissionEvaluator.list_memberships()` |
| **Core Profil** | `packages/orcia-core/src/orcia_core/audit_finops/_internal/_sql_user_profile_orgs.py` | Modifié | Support `unit_type IN ("BU", "TRIBE")` |
| **API Erreurs** | `apps/api/src/orcia_api/errors/registry.py` | Modifié | Enregistrement `OntologyScopeConflictError` (`409`) |
| **API IAM** | `apps/api/src/orcia_api/routers/_iam_accounts_passwords.py` & `iam_accounts.py` | Modifié | Garde `PLATFORM_ADMIN` / `SECOPS` sur `GET /api/v1/settings/iam/accounts` |
| **API Audit** | `apps/api/src/orcia_api/routers/_finops_auth_guards.py` | Modifié | Union `governed_bu_ids \| direct_led_team_ids` + workspaces associés |
| **API Ontologie** | `apps/api/src/orcia_api/routers/ontology_and_rag.py`, `_ontology_promotions_handlers.py`, `_ontology_promotions_helpers.py` | Modifié | Auth + filtrage `GET /ontology-rag/state`, confinement `POST /ontology/promote`, hiérarchie dynamique, `349` L max, 0 `_internal` / `_memberships` |
| **UI `@orcia/ui`** | `packages/ui/src/shell/OntologyAndKbExplorerPanel.tsx` & `OntologyTripartiteAndStaleSection.tsx` | Modifié / Créé | Découpage `309` L / `138` L |
| **UI `@orcia/ui`** | `packages/ui/src/primitives/UserAccountDropdownTypes.ts`, `UserSettingsProfileAndPassthroughTabs.tsx`, `UserSettingsPassthroughTab.tsx`, `UserSettingsModalDialog.tsx` | Modifié | Labels `i18n` via props (0 ternaire `isFr`), suppression `setPassthroughTested(true)` factice |
| **Frontend `@orcia/web`** | `apps/web/src/components/ontologyApiBridge.ts`, `features/ontology/index.tsx`, `features/workspaces/WorkspaceGlossaryAndOntologyTab.tsx` | Modifié | `slugifyScopedConceptKey(term, level, scopeId)` (`<= 120` car.), `342` L, `writableScopes` backend |
| **Frontend `@orcia/web`** | `apps/web/src/routes/SettingsOrganizationUnitsBlock.tsx` & `useOrgUnitsBlockActions.ts` | Modifié / Créé | Découpage `214` L / `327` L |
| **Frontend `@orcia/web`** | `apps/web/src/stores/settingsRbacResolver.ts`, `authSessionStore.ts`, `components/ShellContainer.tsx`, `components/shellPresets.ts`, `i18n/locales/shell_and_search_labels.ts` | Modifié | Accès `SECOPS` à `Configuration > Comptes & Habilitations` + labels Passthrough FR/EN |
| **Backend / E2E** | `packages/orcia-core/src/orcia_core/testing/{cassette_llm.py,__init__.py}`, `apps/api/src/orcia_api/dependencies/portal_and_assistant.py` | Modifié | `DeterministicCassetteEmbedding(EmbeddingPort)` (`ORCIA_USE_CASSETTE_LLM=true`) après garde-fou `ERR_NO_ACTIVE_EMBEDDING_MODEL` |
| **Backend** | `apps/api/src/orcia_api/routers/{_bootstrap_evaluator_sync.py,bootstrap_accostage.py}` | Créé / Modifié | Sync `platformSetupStore` (`org_units`, `workspaces`) vers `auth_svc.evaluator` + reset `orchestration_service` lors de `create_welcome_setup_first_admin` |
| **Frontend `@orcia/web`** | `apps/web/src/features/cockpit/CockpitHumanLedGovernanceSection.tsx` | Modifié | Filtrage des runs cockpit sur `effectiveWorkspaceId` |
| **Tests** | `tests/unit/test_story_{17_3,20_1,20_2,20_4}_*.py`, `tests/security/test_story_{20_1,20_2}_*.py`, `tests/integration/api/test_story_20_2_ontology_promotions_postgres18.py`, `apps/web/src/__tests__/*`, `packages/ui/src/__tests__/userSettingsLabelsFixture.ts`, `apps/web/e2e/support/embeddingModel.ts`, `apps/web/e2e/{02,03,06,10,shell}*.spec.ts` | Modifié / Créé | Couverture non-régression, sécurité des 10 findings & alignement E2E Playwright Epic 19/20 |

### 3.2 Métriques & Portes de Vérification (`AD-17`)

- **Volumétrie (`wc -l`)** : `SettingsOrganizationUnitsBlock.tsx` (`214`), `useOrgUnitsBlockActions.ts` (`327`), `OntologyAndKbExplorerPanel.tsx` (`309`), `OntologyTripartiteAndStaleSection.tsx` (`138`), `permissions.py` (`346`), `sql_ontology_repository.py` (`343`), `_ontology_promotions_handlers.py` (`349`), `WorkspaceGlossaryAndOntologyTab.tsx` (`342`), `_bootstrap_evaluator_sync.py` (`126`).
- **Migrations locales PostgreSQL** :
  - `.venv/bin/alembic -c infra/migrations/alembic.ini upgrade head` : `exit 0` (`20261117_1601 -> 20261117_2001 -> 20261117_2002 -> 20261117_2003`).
- **Qualité statique & Architecture** :
  - `.venv/bin/ruff format --check .` : `1112 files already formatted` (`exit 0`).
  - `.venv/bin/ruff check .` : `All checks passed!` (`exit 0`).
  - `.venv/bin/mypy --strict packages/orcia-core/src apps/api/src apps/worker/src` : `Success: no issues found in 478 source files` (`exit 0`).
  - `.venv/bin/lint-imports` : `Contracts: 5 kept, 0 broken` (`exit 0`).
  - `.venv/bin/python scripts/export_openapi.py --check` : `exit 0` (`0-diff`).
  - `.venv/bin/python .agent/skills/bmad-architecture/scripts/lint_spine.py --workspace docs/planning-artifacts/architecture/architecture-ORCIA-2026-10-24` : `ok: true, total_findings: 0` (`exit 0`).
- **Tests Pytest Complets & Couverture (`AD-17` Couches 1–5 + Sécurité)** :
  - `.venv/bin/pytest --cov=packages/orcia-core --cov-report=term-missing --cov-fail-under=90 tests/unit tests/security tests/conformance tests/evals tests/integration` : **`816 passed` (`exit 0`, 0 failed, 0 skipped), couverture globale `packages/orcia-core` = `91.48%`** (`impact_and_promotion.py` `100%`, `sql_user_profile_stats.py` `97%`, `_sql_user_profile_orgs.py` `100%`, `sql_org_ontology_lead_sync.py` `100%`, `sql_ontology_repository.py` `98%`, `sql_ontology_queries.py` `100%`, `ontology/permissions.py` `96%`, `permissions/evaluator.py` `96%`, `user_profile_service.py` `100%`).
- **Tests d'Intégration PostgreSQL 18 (`testcontainers` ciblés Epic 20 / 17)** :
  - `.venv/bin/pytest -q tests/integration/api/test_story_20_*.py tests/integration/api/test_story_17_{2,3}_*.py` : **`7 passed` (`exit 0`)**.
- **Suite TypeScript (`pnpm turbo run lint typecheck test --force --concurrency=2`)** :
  - `Tasks: 9 successful, 9 total` (`@orcia/api-client`: `2 files / 13 tests passed`; `@orcia/ui`: `26 files / 110 tests passed`; `@orcia/web`: `38 files / 153 tests passed`).
- **GitNexus** :
  - `npx gitnexus analyze` : `34,313 nodes | 64,419 edges | 572 clusters | 1490 flows`.
  - `gitnexus_detect_changes` (epic 20 complet vs base) : `changed_count: 746, affected_count: 250, changed_files: 141, risk_level: critical`.

### 3.3 Validation & Procédure de Test sur Toute la Pyramide (`AD-17` — Couche 5 E2E)

- **Couche 5 — Tests E2E Navigateur Playwright Bi-Serveur (`pnpm e2e`, pile isolée `apps/web/e2e/` avec FastAPI + Vite + PostgreSQL 18 + Redis + SeaweedFS)** :
  - Commande exécutée : `pnpm e2e` (`playwright test --config=apps/web/e2e/playwright.config.ts`).
  - Résultat final : **`44 passed, 18 skipped, 0 failed` (`62` cas sur `desktop-cockpit` et `mobile-companion`, durée `5.3m`, `exit 0`)** — les `18` cas marqués `skipped` correspondent au projet `mobile-companion` sur les specs explicitement restreintes à `desktop-cockpit` par `test.skip(isMobileViewport, ...)` déjà en place avant Epic 20.
  - Ajustements effectués pour aligner les E2E avec Epic 19.6 / Epic 20 sans relâcher aucune assertion :
    - `apps/web/e2e/support/embeddingModel.ts` + `02-assistant-streaming-and-folders.spec.ts` & `10-command-palette-search.spec.ts` : configuration d'un modèle d'embedding `GLOBAL` actif avant sollicitation de `/assistant` et `/api/v1/search`, couplée à `DeterministicCassetteEmbedding` côté backend en mode `ORCIA_USE_CASSETTE_LLM=true`.
    - `03-human-led-anchor-and-arbitration.spec.ts` & `06-gates-review-and-anti-rubber-stamping.spec.ts` : création d'une BU + Espace de travail réel via `createOrgAndWorkspaceViaUi` (au lieu d'utiliser le seed `0201` en mode observateur) + synchronisation `platformSetupStore` $\rightarrow$ `auth_svc.evaluator` et filtrage des runs cockpit sur `effectiveWorkspaceId`.
    - `shell.spec.ts` (`mobile-companion`) : prise en compte des icônes repliées de la sidebar mobile (`aria-label` lorsque `viewportWidth < 768`).
