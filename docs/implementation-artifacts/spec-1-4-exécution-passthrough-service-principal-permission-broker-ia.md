---
title: 'Story 1.4: Exécution Passthrough / Service Principal & Permission Broker IA connecté à Jira'
type: 'feature'
created: '2026-10-25'
status: 'done'
route: 'dispatch'
baseline_commit: '42e87e7bfa8ecd0b330b6e89be62cef270c5f9c4' # pragma: allowlist secret
review_loop_iteration: 1
context:
  - '{project-root}/AGENTS.md'
  - '{project-root}/docs/implementation-artifacts/epic-1-context.md'
---

<frozen-after-approval reason="human-owned intent — do not modify unless human renegotiates">

## Intent

**Problem:** ORCIA doit garantir que chaque résolution ou exécution sur une source externe (`git://`, `nexus://`, `confluence://`, `jira://`, `db://` ou client MCP) s'exécute par défaut avec l'identité déléguée de l'utilisateur (`execution_identity: passthrough`) sans élévation de privilèges (*Confused Deputy* via un `service_principal` non approuvé), et qu'en cas de refus d'accès (`HTTP 401/403` ou permission `EXECUTE` manquante), le `PermissionBrokerService` intercepte l'erreur, consulte la Base de Connaissances d'Habilitations (fichiers Markdown à frontmatter YAML `uri_pattern`, `required_role`, `approver_team`, `request_url_template`, `sla_hours`), retourne une enveloppe RFC 9457 enrichie de `permission_broker_hint`, et ouvre automatiquement le **Dock Agent Concierge & Permission Broker** à droite avec une carte ambre (`#D97706`, `UX-DR11`) présentant la source, le rôle manquant, l'approbateur, le SLA, le lien de demande d'accès pré-remplie dans **Atlassian Jira** et le bouton *Mettre en pause / Rejouer l'étape* (`FR-22`).

**Approach:** Créer la révision Alembic `0004_story_1_4_permission_broker_and_step_denials.py` (`permission_broker_policies`, `permission_broker_tickets` à clés `UUIDv7`), implémenter dans `packages/orcia-core/permissions/broker.py` le moteur `PermissionBrokerService` (garde-fou `passthrough` vs `service_principal`, parseur Markdown/YAML de la KB d'Habilitations, matching par `uri_pattern`, construction encodée du lien Jira pré-rempli, gestion du cycle `WAITING_FOR_PERMISSION -> PAUSED -> REPLAYED` / `GRANTED` et exceptions `PermissionBrokerDeniedError` / `ConfusedDeputyBlockedError`), exposer les routes FastAPI `/api/v1/permissions/broker/*`, régénérer `packages/api-client` en `0-diff`, et livrer dans `@orcia/ui` (`packages/ui`) et `apps/web` le composant `PermissionBrokerCard` (`UX-DR11`) intégré au `ConciergeDock` avec ouverture automatique sur `PERMISSION_DENIED_STEP` / `WAITING_FOR_PERMISSION` (`i18n` `fr`/`en`).

## Boundaries & Constraints

**Always:**
- Utiliser exclusivement `.venv/bin/` pour Python et maintenir `0` import `fastapi`, `sqlalchemy`, `dramatiq`, `redis` ou `litellm` dans `packages/orcia-core/domain`, `ports`, `permissions` et `catalog`.
- Créer la migration incrémentale `infra/migrations/versions/0004_story_1_4_permission_broker_and_step_denials.py` (`down_revision = "0003_story_1_3"`) en SQL brut avec clés `UUIDv7` et tester `upgrade -> downgrade -> upgrade` sur PostgreSQL 18 (`testcontainers`).
- Exécuter tout connecteur externe par défaut en `execution_identity: passthrough` et rejeter toute tentative d'exécution en `service_principal` non explicitement approuvée par un administrateur (`ConfusedDeputyBlockedError`, `HTTP 403 ERR_CONFUSED_DEPUTY_BLOCKED`).
- Intercepter tout refus d'accès (`HTTP 401/403` ou permission `EXECUTE` manquante) dans `PermissionBrokerService`, résoudre le motif `uri_pattern` dans la KB d'Habilitations, générer le lien Jira pré-rempli encodé via `urllib.parse.quote`, et renseigner `permission_broker_hint` dans l'enveloppe RFC 9457.
- Ouvrir automatiquement le Dock Agent Concierge & Permission Broker à droite (`dockCollapsed = false`) lors de la réception ou sélection d'un état `PERMISSION_DENIED_STEP` / `WAITING_FOR_PERMISSION` et afficher la carte ambre (`#D97706`, `UX-DR11`).
- Conserver l'isolation stricte de `packages/ui` (`@orcia/ui` sans `next/*`, `zustand`, `@orcia/api-client`, ni couleur hex hors `tokens.css`), la parité `100 %` du dictionnaire `i18n` (`fr`/`en`), et chaque fichier sous `280–300` lignes avec couverture unitaire $\ge 90\%$.

**Never:**
- Ne jamais modifier les révisions Alembic `0001`, `0002` et `0003` ni désactiver le trigger *Append-Only*.
- Ne jamais autoriser un `READ_ONLY_OBSERVER` (`OBSERVER` / `BU_DIRECTOR`) à importer une politique KB ou muter un ticket Permission Broker (`HTTP 403 ERR_OBSERVER_MODE_READ_ONLY`).
- Ne jamais interpoler des paramètres utilisateur bruts non encodés dans l'URL de demande d'accès Jira (`request_url_template`).

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Exécution `passthrough` vs `service_principal` (`AD-6`, `FR-22`) | Appel connecteur (`git://`, `confluence://`, `jira://`, `db://`, `nexus://`, `mcp://`) avec `execution_identity="passthrough"` (défaut) ou `"service_principal"` | En `passthrough` avec droit valide : exécution autorisée (`status="GRANTED"`). En `service_principal` : autorisé uniquement si la politique/connecteur a `service_principal_allowed=True` et `approved_by_admin_id` non vide | `service_principal` non approuvé -> `ConfusedDeputyBlockedError` (`HTTP 403 ERR_CONFUSED_DEPUTY_BLOCKED`) |
| Interception `401/403` par `PermissionBrokerService` & KB YAML/Markdown (`FR-22`) | Accès refusé (`simulated_upstream_status` `401`/`403` ou permission `EXECUTE` absente ou rôle externe manquant) sur une URI (ex. `git://github.enterprise/payments/checkout-core.git`, `confluence://PAY/Architecture-PCI@v4`, `jira://SECOPS/SEC-108`) | Recherche par `fnmatch` / préfixe du `uri_pattern` le plus spécifique dans la KB d'Habilitations, création d'un ticket `WAITING_FOR_PERMISSION` (`step_state="PERMISSION_DENIED_STEP"`), génération du lien Jira pré-rempli et enrichissement de `permission_broker_hint` dans l'enveloppe RFC 9457 | Si `raise_on_denied=True` -> lève `PermissionBrokerDeniedError` (`HTTP 403 ERR_PERMISSION_BROKER_INTERCEPTED` avec `permission_broker_hint`) ; si `raise_on_denied=False` -> retourne l'objet `PermissionCheckResponseSchema` avec le ticket créé |
| Import d'une fiche KB d'Habilitations Markdown à frontmatter YAML | Document Markdown débutant par `---\nuri_pattern: ...\nrequired_role: ...\napprover_team: ...\nrequest_url_template: ...\nsla_hours: 4\n---` + corps procédural | Parse et valide les 5 clés obligatoires (`uri_pattern`, `required_role`, `approver_team`, `request_url_template`, `sla_hours > 0`), enregistre la politique dans la KB | Frontmatter manquant, `sla_hours <= 0` ou `request_url_template` hors `https://` -> `ValidationDomainError` (`HTTP 422 ERR_VALIDATION_FAILED`) ; appelant `READ_ONLY_OBSERVER` -> `HTTP 403 ERR_OBSERVER_MODE_READ_ONLY` |
| Ouverture automatique du Dock Permission Broker & *Replay Step N* (`UX-DR11`, `FR-22`) | Réception/déclenchement de `PERMISSION_DENIED_STEP` / `WAITING_FOR_PERMISSION` dans l'UI | Le Dock droit se déplie automatiquement (`data-collapsed="false"`), affiche la `PermissionBrokerCard` ambre (`#D97706`) avec source, rôle manquant, équipe approbatrice, SLA, lien Jira pré-rempli et boutons *Mettre en pause* (`PAUSED`) / *Rejouer l'étape* (`REPLAYED` / `GRANTED`) | Action sur un `ticket_id` inexistant -> `HTTP 404 ERR_RESOURCE_NOT_FOUND` ; action en mode `READ_ONLY_OBSERVER` -> `HTTP 403 ERR_OBSERVER_MODE_READ_ONLY` |

</frozen-after-approval>

## Code Map

- `infra/migrations/versions/0004_story_1_4_permission_broker_and_step_denials.py` — Migration Alembic incrémentale `0004` (`down_revision = "0003_story_1_3"`) créant `permission_broker_policies` et `permission_broker_tickets` (`UUIDv7`).
- `packages/orcia-core/src/orcia_core/bootstrap/permission_broker_seeds.py` & `packages/orcia-core/src/orcia_core/bootstrap/seeder.py` — Semences idempotentes des politiques KB (`git://`, `confluence://`, `jira://`, `db://`, `nexus://`) et d'un ticket initial `PERMISSION_DENIED_STEP`.
- `infra/scripts/maintenance/03_backfill_permission_broker.py` — Script de maintenance idempotent (`--dry-run` rollback par défaut, `--apply` commit).
- `packages/orcia-core/src/orcia_core/domain/exceptions.py` & `packages/orcia-core/src/orcia_core/domain/__init__.py` — Ajout de `PermissionBrokerDeniedError` (`ERR_PERMISSION_BROKER_INTERCEPTED`, HTTP 403) et `ConfusedDeputyBlockedError` (`ERR_CONFUSED_DEPUTY_BLOCKED`, HTTP 403).
- `packages/orcia-core/src/orcia_core/permissions/broker.py` & `packages/orcia-core/src/orcia_core/permissions/__init__.py` — `PermissionBrokerPolicy`, `PermissionBrokerTicket`, `PermissionCheckOutcome`, `parse_permission_kb_markdown`, `PermissionBrokerService` et `build_default_permission_broker_service`.
- `packages/orcia-core/src/orcia_core/schemas/permission_broker.py` & `packages/orcia-core/src/orcia_core/schemas/__init__.py` — Schémas Pydantic v2 (`extra="forbid"`) pour `/api/v1/permissions/broker/*`.
- `apps/api/src/orcia_api/routers/permission_broker.py` & `apps/api/src/orcia_api/main.py` — Routeur FastAPI `/api/v1/permissions/broker/*`.
- `packages/api-client/` — Régénération OpenAPI 3.1 (`openapi.json`, `src/generated/schema.ts`, `src/index.ts`).
- `packages/ui/src/shell/PermissionBrokerCard.tsx`, `packages/ui/src/shell/ConciergeDock.tsx`, `packages/ui/src/shell/AppShell.tsx`, `packages/ui/src/shell/types.ts` & `packages/ui/src/index.ts` — Composant pur `@orcia/ui` `PermissionBrokerCard` (`UX-DR11`) et ouverture automatique du `ConciergeDock`.
- `apps/web/src/components/ShellContainer.tsx`, `apps/web/src/components/ModuleWorkspaceView.tsx`, `apps/web/src/components/workspaceFixtures.ts`, `apps/web/src/i18n/locales/fr.ts` & `apps/web/src/i18n/locales/en.ts` — Intégration UI dans le Dock et dans les modules (Cockpit, Catalogue, Gates & Habilitations) avec parité `i18n` `fr`/`en`.
- `tests/unit/test_permission_broker.py`, `tests/integration/test_real_containers.py` & `apps/web/e2e/shell.spec.ts` — Suite de tests à 5 couches (`AD-17`).

## Tasks & Acceptance

**Execution:**
- [x] `infra/migrations/versions/0004_story_1_4_permission_broker_and_step_denials.py` & `infra/scripts/maintenance/03_backfill_permission_broker.py` — Créer la révision `0004` (`permission_broker_policies`, `permission_broker_tickets`) et le script de backfill idempotent (`--dry-run` / `--apply`).
- [x] `packages/orcia-core/src/orcia_core/permissions/broker.py` & `domain/exceptions.py` — Implémenter `PermissionBrokerService`, le parseur Markdown/YAML (`uri_pattern`, `required_role`, `approver_team`, `request_url_template`, `sla_hours`), le garde-fou `passthrough` vs `service_principal`, la génération du lien Jira pré-rempli, l'enveloppe RFC 9457 avec `permission_broker_hint` et les actions `PAUSE` / `REPLAY` (`Replay Step N`).
- [x] `apps/api/src/orcia_api/routers/permission_broker.py` & `packages/api-client/` — Exposer `/api/v1/permissions/broker/state`, `/api/v1/permissions/broker/policies/import-markdown`, `/api/v1/permissions/broker/check-access` et `/api/v1/permissions/broker/tickets/{ticket_id}/action`, puis régénérer `packages/api-client` en `0-diff`.
- [x] `packages/ui/src/shell/PermissionBrokerCard.tsx`, `ConciergeDock.tsx`, `AppShell.tsx` & `apps/web/` — Implémenter la carte ambre `PermissionBrokerCard` (`UX-DR11`), l'ouverture automatique du Dock droit sur état `PERMISSION_DENIED_STEP` / `WAITING_FOR_PERMISSION`, le déclencheur de simulation dans le Cockpit/Catalogue/Gates, et les traductions `fr`/`en`.
- [x] `tests/unit/test_permission_broker.py`, `tests/integration/test_real_containers.py`, `packages/ui/src/__tests__/shell.test.tsx` & `apps/web/e2e/shell.spec.ts` — Valider les 5 couches de tests avec couverture $\ge 90\%$ sur `packages/orcia-core`.

**Acceptance Criteria:**
- Given un connecteur configuré en `execution_identity: passthrough` (ou `service_principal` uniquement si approuvé par un admin), when une étape tente d'accéder à un dépôt `git://`, une page `confluence://` ou un projet `jira://` sans le rôle requis (`401/403`) ou sans `EXECUTE`, then `PermissionBrokerService` intercepte l'exception, résout le `uri_pattern` dans la KB Markdown/YAML et retourne une enveloppe RFC 9457 enrichie de `permission_broker_hint` (et bloque tout `service_principal` non approuvé avec `HTTP 403 ERR_CONFUSED_DEPUTY_BLOCKED`).
- Given la réception ou sélection de l'état `PERMISSION_DENIED_STEP` / `WAITING_FOR_PERMISSION` dans l'interface web, when l'utilisateur visualise l'étape bloquée, then le **Dock Agent Concierge & Permission Broker** s'ouvre automatiquement à droite avec une carte ambre (`#D97706`, `UX-DR11`) présentant la source exacte et le rôle manquant, l'équipe approbatrice et le SLA, le lien de demande d'accès pré-remplie dans **Atlassian Jira**, et le bouton *Mettre en pause / Rejouer l'étape* (`FR-22`).
- Given la suite de tests à 5 couches (`AD-17`), when toutes les vérifications sont exécutées, then `pytest --cov=packages/orcia-core --cov-fail-under=90`, `testcontainers`, `Schemathesis`, `Vitest` et `@playwright/test` passent à 100 %.

## Design Notes

- Les fiches Markdown de la KB d'Habilitations supportent dès la Story 1.4 les métadonnées optionnelles `human_anchor_author_id`, `human_anchor_signature` et `freshness_ttl_days` dans leur frontmatter YAML afin d'être directement réutilisées par la Gate Déterministe `init-datasource` de la Story 1.5.
- Pour garantir la conformité `Schemathesis` sur les routes `/api/v1/permissions/broker/*`, rejeter tout caractère de contrôle ou octet nul dans les entrées textuelles avec `ValidationDomainError` (`HTTP 422`).

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
| 1 | `blind-hunter` | `broker.py` (527 lignes) et `exceptions.py` (333 lignes) dépassent la limite de 300 lignes par fichier | `patch` | Découper `broker.py` en `broker_models.py` (`< 260` lignes) + `broker.py` (`< 270` lignes) et compacter `exceptions.py` sous `295` lignes |
| 2 | `blind-hunter` / `edge-case-hunter` | `import_policy_markdown` accepte `service_principal_allowed: true` et `approved_by_admin_id` dans le frontmatter sans exiger `PLATFORM_ADMIN`, et n'applique pas les bornes Pydantic (`sla_hours <= 720`, `freshness_ttl_days <= 3650`, longueurs max) ni la déduplication par `uri_pattern` | `patch` | Exiger `user.platform_role == "PLATFORM_ADMIN"` pour `service_principal_allowed=True` (sinon `ConfusedDeputyBlockedError`), lier `approved_by_admin_id=user.id`, valider toutes les bornes dans `parse_permission_kb_markdown`, et dédupliquer `uri_pattern` en mémoire et en SQL |
| 3 | `blind-hunter` / `edge-case-hunter` / `verification-gap` | `GET /api/v1/permissions/broker/state` et `list_tickets` ne filtrent pas par accès Workspace de l'appelant ; `check_or_intercept_access` et `apply_ticket_action` ne vérifient pas systématiquement `_enforce_mutation_allowed` sur `target.workspace_id` ni la régression `REPLAYED/GRANTED -> PAUSED` | `patch` | Appliquer `resolve_workspace_access` et `_enforce_mutation_allowed(user, target.workspace_id or workspace_id)` sur `list_tickets`, `check_or_intercept_access` et `apply_ticket_action`, supporter la transition vers `GRANTED` et interdire `REPLAYED/GRANTED -> PAUSED` |
| 4 | `blind-hunter` | `resolve_matching_policy` retombe sur une politique du même schéma avec un chemin différent (`git://*/payments/*` pour `git://.../hr/payroll.git`), et `check_or_intercept_access` ignore les ACL par `resource_uri`, le coffre `PassthroughVaultCipher` et le contrôle de rôle quand `simulated_upstream_status=200` | `patch` | Ne matcher que via `fnmatchcase(target_uri, policy.uri_pattern)`, résoudre les ACL Catalogue par `resource_id` ou `resource_uri`, vérifier le rôle externe ou un secret `PassthroughVaultCipher` valide même si `simulated_upstream_status == 200` |
| 5 | `blind-hunter` | `PermissionBrokerCard.tsx` n'affiche pas `procedureMarkdown`, `workspaceFixtures.ts` et `permission_broker_tickets` omettent `procedure_markdown`, et le panneau simulateur est affiché sur tous les modules au lieu de `cockpit`, `catalog` et `gates` | `patch` | Rendre `procedureMarkdown` dans `PermissionBrokerCard.tsx`, ajouter `procedure_markdown` aux fixtures/seeds/migration `0004`, et restreindre `permission-broker-simulator-panel` aux modules `cockpit`, `catalog` et `gates` |
| 6 | `verification-gap` / `edge-case-hunter` | `getPermissionBrokerState` dans `packages/api-client/src/index.ts` n'accepte pas `workspaceId`, `client.test.ts` ne vérifie que `toHaveBeenCalledTimes(20)`, et `test_permission_broker.py` ne teste pas `simulated_upstream_status=None` avec `granted_external_roles`, la préservation d'`id` à l'upsert ni le filtrage `workspace_id` | `patch` | Ajouter `workspaceId?: string` à `getPermissionBrokerState`, asserter `toHaveBeenCalledWith(...)` dans `client.test.ts`, et ajouter les tests unitaires correspondants dans `test_permission_broker.py` |
