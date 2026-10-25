---
title: 'Story 1.5: Workflows Système d''Amorçage Gouverné Jour 0 & Onboarding Autonome d''Équipe et Multi-Workspaces Multi-Sources par le Chef d''Équipe (init-organization, init-workspace, init-datasource, init-user)'
type: 'feature'
created: '2026-10-25'
status: 'done'
route: 'dispatch'
baseline_commit: 'b1e16780b99cfa642a6bcba45b55cc16a34912f9' # pragma: allowlist secret
review_loop_iteration: 1
context:
  - '{project-root}/AGENTS.md'
  - '{project-root}/docs/implementation-artifacts/epic-1-context.md'
---

<frozen-after-approval reason="human-owned intent — do not modify unless human renegotiates">

## Intent

**Problem:** ORCIA doit fournir les workflows système pré-embarqués (`orcia://system/bootstrap/{init-organization,init-workspace,init-datasource,init-existing-project,init-skill,init-user}`) verrouillés par des Gates Déterministes bloquantes afin que : (1) aucune organisation ne démarre à froid (`init-organization`) sans configuration d'authentification/RBAC valide et sans qu'au moins **2 familles de modèles LLM distinctes** soient vérifiées par `ModelRouterService` (`AD-10`), (2) un Chef d'Équipe (`TEAM_LEAD`) puisse embarquer en autonomie (`init-workspace`) son équipe, ses sous-équipes et `1..N` Workspaces solutions (avec surcharges `TEAM`/`WORKSPACE`, Ontologies `3_TEAM`/`3_WORKSPACE` sans conflit avec N1/N2/`3_TEAM`, et invitations membres déclenchant automatiquement `init-user` à la première connexion pour lier leurs comptes Jira/Confluence/Git en `passthrough` `AES-256-GCM`), et (3) aucune source (`git://`, `confluence://`, `jira://`, `db://`, `nexus://`) ne soit publiée via `init-datasource` sans fiche *Permission Broker* rédigée et signée comme **Ancre Humaine** (`UX-DR3`, `#6D28D9`) ni `freshness_ttl_days` (`FR-28`, `AD-16`).

**Approach:** Créer la révision Alembic `0005_story_1_5_system_bootstrap_workflows_and_onboarding.py` (`llm_model_endpoints`, `system_bootstrap_runs`, `user_onboarding_states` à clés `UUIDv7`), implémenter dans `packages/orcia-core/bootstrap/{models.py,engine.py}` le `ModelRouterService` (vérification d'orthogonalité $\ge 2$ familles LLM distinctes) et le `SystemBootstrapWorkflowService` (`init-organization`, `init-workspace`, `init-datasource`, `init-user`), exposer les routes FastAPI `/api/v1/bootstrap/*`, régénérer `packages/api-client` en `0-diff`, et livrer dans `@orcia/ui` (`packages/ui`) et `apps/web` le composant `BootstrapOnboardingPanel` intégrant la **`Human-Led Anchor Card` (`UX-DR3`, Violet `#6D28D9`)** dans **⚙️ 7. Administration & Pilotage des Workspaces** (`i18n` `fr`/`en`).

## Boundaries & Constraints

**Always:**
- Utiliser exclusivement `.venv/bin/` pour Python et maintenir `0` import `fastapi`, `sqlalchemy`, `dramatiq`, `redis` ou `litellm` dans `packages/orcia-core/domain`, `ports`, `permissions`, `catalog` et `bootstrap`.
- Créer la migration incrémentale `infra/migrations/versions/0005_story_1_5_system_bootstrap_workflows_and_onboarding.py` (`down_revision = "0004_story_1_4"`) en SQL brut avec clés `UUIDv7` et tester `upgrade -> downgrade -> upgrade` sur PostgreSQL 18 (`testcontainers`).
- En **Étape 0 (Pre-Story Refactoring)**, compacter `packages/orcia-core/src/orcia_core/bootstrap/catalog_seeds.py` et `packages/ui/src/shell/CatalogExplorerPanel.tsx` sous `285` lignes et maintenir tous les fichiers créés ou modifiés sous `280–300` lignes.
- Verrouiller `init-organization` par une Gate Déterministe exigeant une configuration Auth/RBAC valide et $\ge 2$ familles de modèles LLM distinctes actives et vérifiées dans `ModelRouterService` (`ModelOrthogonalityViolationError` `HTTP 422 ERR_MODEL_ORTHOGONALITY_VIOLATION` si $< 2$ familles).
- Verrouiller `init-datasource` par une Gate Déterministe rejetant la publication (`HTTP 422`) tant que (a) la fiche Markdown/YAML du *Permission Broker* n'est pas rédigée et signée comme **Ancre Humaine** (`human_anchor_justification` $\ge 30$ caractères non triviaux + `human_anchor_signature` + `human_anchor_author_id`, sinon `HumanAnchorRequiredError` `HTTP 422 ERR_HUMAN_ANCHOR_REQUIRED`) et (b) `freshness_ttl_days` n'est pas renseigné (`1 <= freshness_ttl_days <= 3650`, sinon `ValidationDomainError` `HTTP 422 ERR_VALIDATION_FAILED`).
- Réserver la couleur Violet `#6D28D9` (`--color-human-led-violet` / `--color-human-led-violet-bg` `#F5F3FF`) exclusivement à la `Human-Led Anchor Card` (`UX-DR3`, `human_authored_required: true`), sans aucun bouton *"Générer avec l'IA"* dans la carte.

**Never:**
- Ne jamais modifier les révisions Alembic `0001` à `0004` ni désactiver le trigger *Append-Only*.
- Ne jamais autoriser un `READ_ONLY_OBSERVER` (`OBSERVER` / `BU_DIRECTOR`) à exécuter un workflow de mutation `/api/v1/bootstrap/*` (`HTTP 403 ERR_OBSERVER_MODE_READ_ONLY`), ni un non-`PLATFORM_ADMIN` à exécuter `init-organization` (`HTTP 403 ERR_SCOPE_ACCESS_DENIED`).
- Ne jamais autoriser un terme d'Ontologie `3_WORKSPACE` ou `3_TEAM` dans `init-workspace` à redéfinir de manière contradictoire un terme canonique amont `1_ENTERPRISE` ou `2_DOMAIN` (`ValidationDomainError` `HTTP 422`).

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Amorçage Jour 0 `orcia://system/bootstrap/init-organization` (`AD-10`, `FR-28`) | Appel `POST /api/v1/bootstrap/init-organization` par un `PLATFORM_ADMIN` avec configuration Auth (`OIDC` et/ou `LOCAL`), mapping RBAC et liste d'endpoints LLM (`provider_slug`, `model_family`, `model_name`, `connectivity_verified`) | `ModelRouterService` vérifie qu'au moins **2 familles de modèles LLM distinctes** (`model_family`) ont `connectivity_verified=True` et `is_active=True`, valide la conf Auth/RBAC, amorce le catalogue socle et enregistre un `SystemBootstrapRunRecord(status="COMPLETED", gate_passed=True)` | Moins de 2 familles LLM distinctes connectées -> `ModelOrthogonalityViolationError` (`HTTP 422 ERR_MODEL_ORTHOGONALITY_VIOLATION`) ; Auth/RBAC vide -> `ValidationDomainError` (`HTTP 422`) ; appelant non `PLATFORM_ADMIN` -> `ScopeAccessDeniedError` (`HTTP 403`) |
| Onboarding autonome d'équipe & Multi-Workspaces `orcia://system/bootstrap/init-workspace` (`AD-14`, `FR-28`) | Appel `POST /api/v1/bootstrap/init-workspace` par un `TEAM_LEAD` (ou `PLATFORM_ADMIN`) définissant l'équipe (et sous-équipes), les standards `TEAM`, l'Ontologie `3_TEAM`, `1..N` Workspaces solutions (avec surcharges `WORKSPACE` et Ontologie `3_WORKSPACE`) et les invitations membres (`email`, `human_profile_archetype`, `role`) | Crée/met à jour les `OrgUnit`, les `1..N` `Workspaces`, les surcharges `TEAM` et `WORKSPACE`, valide l'absence de conflit ontologique avec N1/N2/`3_TEAM`, et crée pour chaque membre invité un état `UserOnboardingState(init_user_completed=False)` prêt pour `init-user` | Terme `3_WORKSPACE` en conflit avec N1/N2/`3_TEAM` ou liste de Workspaces vide -> `ValidationDomainError` (`HTTP 422`) ; appelant sans rôle `TEAM_LEAD` / `PLATFORM_ADMIN` -> `ScopeAccessDeniedError` (`HTTP 403`) |
| Déclenchement automatique `orcia://system/bootstrap/init-user` à la 1re connexion (`FR-28`, `NFR-SEC-4`) | Appel `POST /api/v1/bootstrap/init-user` (ou connexion initiale d'un membre invité) avec confirmation de `human_profile_archetype` et secrets `passthrough` (`git_token`, `jira_token`, `confluence_token`) | Chiffre chaque secret en `AES-256-GCM` via `PassthroughVaultCipher`, enregistre les `PassthroughCredentialRecord` dans `AuthAndOrganizationService` et `PermissionBrokerService`, et marque `UserOnboardingState(init_user_completed=True)` | Secret vide ou contenant des caractères de contrôle -> `ValidationDomainError` (`HTTP 422`) ; appelant `READ_ONLY_OBSERVER` -> `ObserverModeReadOnlyError` (`HTTP 403`) |
| Publication gouvernée Multi-Sources `orcia://system/bootstrap/init-datasource` (`AD-16`, `FR-28`, `UX-DR3`) | Appel `POST /api/v1/bootstrap/init-datasource` (répétable pour rattacher à un même Workspace plusieurs `git://`, plusieurs `confluence://` avec filtre CQL `space_key`/labels, et plusieurs `jira://` avec filtre JQL) accompagné de la fiche Markdown/YAML du *Permission Broker*, de la signature d'Ancre Humaine et de `freshness_ttl_days` | La Gate Déterministe vérifie l'Ancre Humaine (`human_anchor_justification` $\ge 30$ car. + `human_anchor_signature` + `human_anchor_author_id`) et `freshness_ttl_days` (`1..3650`), enregistre la politique dans `PermissionBrokerService`, rattache la source (`WorkspaceDatasourceEntity`) au Workspace sans écraser les autres sources du même schéma, et publie l'entrée dans le Catalogue Fédéré | Justification humaine $< 30$ car. ou signature manquante -> `HumanAnchorRequiredError` (`HTTP 422 ERR_HUMAN_ANCHOR_REQUIRED`) ; `freshness_ttl_days` manquant ou hors `1..3650` -> `ValidationDomainError` (`HTTP 422 ERR_VALIDATION_FAILED`) ; accès Workspace refusé -> `ScopeAccessDeniedError` (`HTTP 403`) |

</frozen-after-approval>

## Code Map

- `infra/migrations/versions/0005_story_1_5_system_bootstrap_workflows_and_onboarding.py` — Migration Alembic incrémentale `0005` (`down_revision = "0004_story_1_4"`) créant `llm_model_endpoints`, `system_bootstrap_runs` et `user_onboarding_states` (`UUIDv7`).
- `packages/orcia-core/src/orcia_core/bootstrap/workflow_bootstrap_seeds.py` & `packages/orcia-core/src/orcia_core/bootstrap/seeder.py` — Semences idempotentes des 6 workflows `orcia://system/bootstrap/*`, des 3 familles LLM orthogonales (`anthropic`, `openai`, `mistral`) et des exécutions initiales.
- `infra/scripts/maintenance/04_backfill_system_bootstrap.py` — Script de maintenance idempotent (`--dry-run` rollback par défaut, `--apply` commit).
- `packages/orcia-core/src/orcia_core/bootstrap/models.py` & `packages/orcia-core/src/orcia_core/bootstrap/engine.py` — `ModelRouterService` ($\ge 2$ familles LLM `AD-10`) et `SystemBootstrapWorkflowService` (`init-organization`, `init-workspace`, `init-datasource`, `init-user`).
- `packages/orcia-core/src/orcia_core/schemas/bootstrap.py` & `packages/orcia-core/src/orcia_core/schemas/__init__.py` — Schémas Pydantic v2 (`extra="forbid"`) pour `/api/v1/bootstrap/*`.
- `apps/api/src/orcia_api/routers/bootstrap.py` & `apps/api/src/orcia_api/main.py` — Routeur FastAPI `/api/v1/bootstrap/*`.
- `packages/api-client/` — Régénération OpenAPI 3.1 (`openapi.json`, `src/generated/schema.ts`, `src/index.ts`).
- `packages/ui/src/shell/BootstrapOnboardingPanel.tsx`, `packages/ui/src/shell/types.ts` & `packages/ui/src/index.ts` — Composant pur `@orcia/ui` d'amorçage Jour 0, d'onboarding autonome `TEAM_LEAD` multi-workspaces/multi-sources et **`Human-Led Anchor Card` (`UX-DR3`, `#6D28D9`)**.
- `apps/web/src/components/ModuleWorkspaceView.tsx`, `apps/web/src/components/workspaceFixtures.ts`, `apps/web/src/i18n/locales/fr.ts` & `apps/web/src/i18n/locales/en.ts` — Intégration dans **⚙️ 7. Administration & Pilotage des Workspaces** avec parité `i18n` `fr`/`en`.
- `tests/unit/test_system_bootstrap.py`, `tests/integration/test_real_containers.py` & `apps/web/e2e/shell.spec.ts` — Suite de tests à 5 couches (`AD-17`).

## Tasks & Acceptance

**Execution:**
- [x] Étape 0 (Contrôle de volumétrie `< 300` lignes) : compacter `packages/orcia-core/src/orcia_core/bootstrap/catalog_seeds.py` et `packages/ui/src/shell/CatalogExplorerPanel.tsx` sous `285` lignes.
- [x] `infra/migrations/versions/0005_story_1_5_system_bootstrap_workflows_and_onboarding.py`, `workflow_bootstrap_seeds.py` & `infra/scripts/maintenance/04_backfill_system_bootstrap.py` — Créer la révision `0005` (`llm_model_endpoints`, `system_bootstrap_runs`, `user_onboarding_states`), les semences des 6 workflows `orcia://system/bootstrap/*` et le script de backfill idempotent (`--dry-run` / `--apply`).
- [x] `packages/orcia-core/src/orcia_core/bootstrap/models.py` & `engine.py` — Implémenter `ModelRouterService` (vérification d'orthogonalité $\ge 2$ familles LLM `AD-10`) et `SystemBootstrapWorkflowService` (`init-organization`, `init-workspace`, `init-datasource` avec Gate Déterministe Ancre Humaine + `freshness_ttl_days`, et `init-user` avec liaison `passthrough` `AES-256-GCM`).
- [x] `apps/api/src/orcia_api/routers/bootstrap.py` & `packages/api-client/` — Exposer `/api/v1/bootstrap/state`, `/api/v1/bootstrap/init-organization`, `/api/v1/bootstrap/init-workspace`, `/api/v1/bootstrap/init-datasource` et `/api/v1/bootstrap/init-user`, puis régénérer `packages/api-client` en `0-diff` (en maintenant `packages/api-client/src/index.ts` sous `290` lignes).
- [x] `packages/ui/src/shell/BootstrapOnboardingPanel.tsx` & `apps/web/` — Implémenter `BootstrapOnboardingPanel` avec la `Human-Led Anchor Card` (`#6D28D9`, `UX-DR3`) dans le module **⚙️ 7. Administration** et les traductions `fr`/`en`.
- [x] `tests/unit/test_system_bootstrap.py`, `tests/integration/test_real_containers.py`, `packages/ui/src/__tests__/shell.test.tsx`, `packages/api-client/src/__tests__/client.test.ts` & `apps/web/e2e/shell.spec.ts` — Valider les 5 couches de tests avec couverture $\ge 90\%$ sur `packages/orcia-core`.

**Acceptance Criteria:**
- Given une nouvelle instance d'ORCIA dans **⚙️ 7. Administration**, when l'administrateur lance `orcia://system/bootstrap/init-organization`, then la Gate Déterministe bloque la validation tant que (1) la configuration d'authentification (OIDC et/ou Auth locale Argon2id) et le mapping RBAC ne sont pas valides et (2) `ModelRouterService` n'a pas vérifié avec succès la connectivité d'au moins **2 familles de modèles LLM distinctes** (`AD-10`), puis amorce le catalogue socle.
- Given un **Chef d'Équipe (`TEAM_LEAD`)** qui exécute `orcia://system/bootstrap/init-workspace` en self-service, when il configure son équipe (et sous-équipes), invite ses membres et crée un ou plusieurs **Workspaces (solutions logicielles)**, then il définit les standards `TEAM` et l'Ontologie `3_TEAM`, crée chaque Workspace avec sa surcharge `WORKSPACE` (`AD-14`), sa boîte de notifications et son Ontologie `3_WORKSPACE` (sans conflit avec N1/N2/`3_TEAM`), et pré-assigne à chaque membre invité son archétype de Profil Humain et ses rôles ; à la première connexion de chaque membre, `orcia://system/bootstrap/init-user` confirme son Profil Humain et lie ses comptes **Jira**, **Confluence** et **Git** en mode `passthrough` (`AES-256-GCM`).
- Given un Administrateur ou un **Chef d'Équipe (`TEAM_LEAD`)** qui exécute `orcia://system/bootstrap/init-datasource` à plusieurs reprises pour rattacher à un même Workspace plusieurs dépôts `git://`, plusieurs espaces `confluence://` (filtres CQL `space_key`/labels) et plusieurs projets `jira://` (filtres JQL), when il soumet chaque source pour publication, then la Gate Déterministe rejette la publication (`HTTP 422`) tant que (a) la fiche YAML/Markdown du *Permission Broker* n'a pas été rédigée et signée comme **Ancre Humaine** (`human_authored_required: true`, $\ge 30$ caractères) et (b) `freshness_ttl_days` n'est pas renseigné (`FR-28`, `AD-16`).

## Design Notes

- Pour maintenir chaque fichier sous `290` lignes, extraire au besoin les types/helpers d'API Client dans `packages/api-client/src/helpers.ts` si `packages/api-client/src/index.ts` approche `290` lignes.
- Dans `BootstrapOnboardingPanel.tsx`, la carte `Human-Led Anchor Card` (`data-testid="human-led-anchor-card"`) utilise exclusivement les variables CSS `var(--color-human-led-violet)` (`#6D28D9`) et `var(--color-human-led-violet-bg)` (`#F5F3FF`), verrouille le bouton de publication `init-datasource` tant que la justification humaine compte $< 30$ caractères ou que la signature est absente, et ne comporte aucun bouton d'auto-complétion IA (`UX-DR3`).

## Verification

**Commands:**
- `.venv/bin/ruff check . && .venv/bin/ruff format --check .` — expected: `0 errors`
- `.venv/bin/mypy --strict packages/orcia-core apps/api apps/worker` — expected: `Success: no issues found`
- `.venv/bin/pytest --cov=packages/orcia-core --cov-fail-under=90` — expected: `>= 90% coverage, all tests pass`
- `pnpm turbo run lint typecheck test` — expected: `0 errors, all unit tests pass`
- `pnpm --filter @orcia/web test:e2e` — expected: `Desktop & Mobile Playwright tests pass`
- `.venv/bin/python .agent/skills/bmad-architecture/scripts/lint_spine.py --workspace docs/planning-artifacts/architecture/architecture-ORCIA-2026-10-24` — expected: `0 findings`
- `.venv/bin/python scripts/check_implementation_docs.py` — expected: `0 errors`

## Review Log

| # | Lens | Finding | Disposition | Resolution |
|---|------|---------|-------------|------------|
| 1 | `edge-case-hunter` / `blind-hunter` | `execute_init_organization` n'exige pas une valeur nettoyée non vide pour `rbac_role_mappings["PLATFORM_ADMIN"]` et fusionne `llm_endpoints` avec les endpoints pré-semés au lieu de remplacer l'ensemble actif | `patch` | Valider `_clean(payload.rbac_role_mappings.get("PLATFORM_ADMIN", ""), ...)` et remplacer `self.model_router._endpoints = {ep.endpoint_key: ep for ep in payload.llm_endpoints}` |
| 2 | `edge-case-hunter` / `blind-hunter` / `verification-gap` | `execute_init_workspace` ignore une sous-équipe partielle (`subteam_slug` sans `subteam_name`), ne vérifie pas `enforce_scope_mutation_guard` sur un Workspace existant, duplique `ovr-team-*`/`ovr-ws-*` à chaque appel, ne persiste pas `team_ont` dans `_upstream_ontology`, n'enregistre pas l'adhésion Workspace du `TEAM_LEAD` créateur, et écrase `workspace_ids`/`init_user_completed` d'un membre existant | `patch` | Valider la paire `subteam_slug`/`subteam_name`, appliquer `enforce_scope_mutation_guard` sur `ex_ws`, dédupliquer `_overrides` par `override_key`, persister `self._upstream_ontology.update(team_ont)`, enregistrer l'adhésion du créateur + des invités et fusionner `workspace_ids` |
| 3 | `edge-case-hunter` / `blind-hunter` | `execute_init_datasource` ne nettoie pas `cql_filter`/`jql_filter`, ne vérifie pas la cohérence `pol.connector_scheme == payload.scheme` / `service_principal_allowed`, et n'expose pas `visibility_scope` (`SHARED_WORKSPACE | SHARED_TEAM`) | `patch` | Valider `_clean` sur `cql_filter`/`jql_filter`, vérifier la cohérence `pol.connector_scheme == payload.scheme` et `service_principal_allowed`, et supporter `visibility_scope` (`SHARED_WORKSPACE` ou `SHARED_TEAM`) |
| 4 | `edge-case-hunter` / `blind-hunter` / `verification-gap` | `execute_init_user` n'interdit pas à un non-admin de passer l'`user_email` d'un autre utilisateur, et `POST /api/v1/auth/passthrough-credentials` n'enregistre pas le secret dans `permission_broker_service` | `patch` | Vérifier `em == user.email.lower() or user.platform_role == "PLATFORM_ADMIN"` dans `execute_init_user` et appeler `permission_broker_service.register_passthrough_credential(record)` dans `routers/auth.py` |
| 5 | `verification-gap` / `edge-case-hunter` | `test_real_containers.py` a perdu l'assertion `SELECT COUNT(*) == 0` après `--dry-run`, et `test_system_bootstrap.py` / `test_permissions_and_auth.py` ne vérifient pas `resolve_effective_workflow` après `init-workspace` ni `check-access` après `init-user` / `passthrough-credentials` | `patch` | Restaurer l'assertion rollback `--dry-run` dans `test_real_containers.py` et ajouter les assertions `resolve_effective_workflow` et `check-access` dans `test_system_bootstrap.py` et `test_permissions_and_auth.py` |
