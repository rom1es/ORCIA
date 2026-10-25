---
title: 'Story 1.1: Amorçage du Monorepo Hybride, Coquille UI Direction C (7 Modules) & Socle de Tests à 5 Couches'
type: 'feature'
created: '2026-10-25'
status: 'done'
route: 'dispatch'
baseline_commit: 'cf02b63358e933e77a641f26262410a39c0bc840' # pragma: allowlist secret
review_loop_iteration: 0
context:
  - '{project-root}/AGENTS.md'
  - '{project-root}/docs/implementation-artifacts/epic-1-context.md'
---

<frozen-after-approval reason="human-owned intent — do not modify unless human renegotiates">

## Intent

**Problem:** Le dépôt ORCIA ne contient actuellement que les artefacts de planification ; l'équipe ne dispose pas encore du monorepo hybride exécutable TypeScript/Python, de l'infrastructure conteneurisée, de la génération automatique du client OpenAPI 3.1, de la coquille visuelle Direction C à 7 modules, ni du harnais de tests à 5 couches.

**Approach:** Initialiser le monorepo hybride (`pnpm` + `Turborepo` côté TypeScript et `.venv` côté Python) comprenant `packages/orcia-core` (noyau hexagonal des 8 domaines, `UUIDv7`, `structlog`, `DeterministicCassetteLLM`), `apps/api` (FastAPI `0.143` avec enveloppe d'erreur RFC 9457 localisée et propagation `trace_id`), `apps/worker` (Dramatiq `2.2`), `packages/api-client` (SDK généré en `0-diff` depuis OpenAPI 3.1), `packages/ui` (`@orcia/ui` — librairie Design System dédiée regroupant les Design Tokens CSS Direction C et tous les composants UX/UI purs : `AppShell`, `GlobalSidebar`, `ScopeSwitcher`, `AssistantDock`, primitives), `apps/web` (Next.js App Router assemblant les 7 routes, le dictionnaire `i18n` `fr`/`en` et `@orcia/ui`), `infra/docker/docker-compose.yml` (PostgreSQL 18 + `pgvector`, Redis 7.4, MinIO), la révision Alembic `0001` et la suite de tests à 5 couches ($\ge 90\%$ de couverture).

## Boundaries & Constraints

**Always:**
- Exécuter toutes les commandes Python via `.venv/bin/` (`python`, `pytest`, `ruff`, `mypy`, `alembic`).
- Préserver la pureté hexagonale de `packages/orcia-core/src/orcia_core/domain` et `ports` (aucun import `fastapi`, `sqlalchemy`, `dramatiq`, `redis`, `litellm`).
- Localiser **tous** les composants UX/UI et tokens CSS Direction C dans la librairie Design System dédiée `packages/ui` (`@orcia/ui`), strictement découplée de `next/*` et de `@orcia/api-client` (composants contrôlés recevant leurs libellés `i18n` et callbacks par props typées).
- Retourner une enveloppe **RFC 9457 Problem Details** (`application/problem+json`) incluant un `error_code` machine invariant, le `trace_id` W3C OpenTelemetry et des messages `title`/`detail` localisés (`fr` par défaut, `en` supporté via `Accept-Language`).
- Utiliser exclusivement les tokens CSS sémantiques Direction C définis dans `packages/ui/src/styles/tokens.css` (zéro couleur hexadécimale en dur dans les composants `.tsx` ; réserver `#6D28D9` `human-led-violet` à `HumanLedAnchorCard`) et le dictionnaire `i18n` typé (`apps/web/src/i18n/locales/{fr,en}.ts`, français par défaut, zéro chaîne littérale UI en dur dans le JSX).
- Maintenir chaque fichier source sous `300–400` lignes et garantir une couverture unitaire $\ge 90\%$.

**Never:**
- Ne jamais éditer manuellement `packages/api-client/src/generated/`.
- Ne jamais importer `next/*`, `zustand` ou `@orcia/api-client` à l'intérieur de `packages/ui`.
- Ne jamais utiliser SQLite ou des mocks Redis pour les tests d'intégration de base de données (utiliser `testcontainers-python`).
- Ne jamais ajouter de dépendance tierce absente de `ARCHITECTURE-SPINE.md` (`lint_spine.py` doit retourner `0 findings`).

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Santé API & Propagation `trace_id` | `GET /api/v1/health` avec ou sans en-tête `traceparent` / `X-Trace-Id` | `HTTP 200` avec `status: "ok"`, `version`, et en-tête `X-Trace-Id` valide (32 hex) | N/A |
| Enveloppe d'erreur RFC 9457 & Localisation `i18n` | Requête sur route inexistante ou exception `OrciaDomainError` avec `Accept-Language: fr` ou `en` | `HTTP 403/404/422` `application/problem+json` contenant `type`, `title`/`detail` localisés (`Content-Language: fr\|en`), `status`, `error_code` invariant et `trace_id` | Corrélation `structlog` automatique avec `trace_id` ; repli sur `fr` si locale inconnue |
| Design System `@orcia/ui`, `i18n` & Raccourcis | Rendu `AppShell` (`@orcia/ui`) dans `apps/web` Desktop (`1440x900`), bascule locale `fr`/`en` et pression des touches `[`, `]` et `Ctrl+W`/`⌘W` | Affichage des 3 colonnes (`Sidebar 235px`, `Canvas 1fr`, `Dock 360px`), des 7 modules via le dictionnaire `i18n` (`fr` par défaut), repli Sidebar à `68px` via `[`, repli Dock via `]` et ouverture du Sélecteur de Périmètre `⌘W` | Ignorer `[` et `]` lorsque le focus est dans un champ `input`/`textarea` |
| Contrat OpenAPI `0-diff` | Exécution de `scripts/export_openapi.py` puis vérification de dérive | `packages/api-client/openapi.json` et `src/generated/schema.ts` synchronisés (`0 diff`) | Échec du test de contrat si le schéma diverge |

</frozen-after-approval>

## Code Map

- `package.json`, `pnpm-workspace.yaml`, `turbo.json`, `tsconfig.base.json` -- Configuration racine du monorepo TypeScript (`pnpm` + `Turborepo`).
- `pyproject.toml` -- Configuration racine Python (`.venv`, `ruff`, `mypy --strict`, `pytest`, `coverage >= 90%`).
- `infra/docker/docker-compose.yml` -- Conteneurs PostgreSQL 18 + `pgvector 0.8.7`, Redis `7.4.2` et MinIO.
- `infra/migrations/alembic.ini`, `infra/migrations/env.py`, `infra/migrations/versions/0001_story_1_1_foundation_extensions.py` -- Socle Alembic Asyncio, extension `vector` et trigger PostgreSQL *Append-Only* `orcia_prevent_append_only_mutation()`.
- `infra/scripts/maintenance/00_verify_db_invariants.py` -- Script de maintenance de référence avec mode `--dry-run` obligatoire.
- `packages/orcia-core/src/orcia_core/` -- Noyau hexagonal (8 domaines bornés, `domain/identifiers.py` `UUIDv7`, `domain/exceptions.py` avec catalogue `i18n` `fr`/`en`, `schemas/problem_details.py`, `schemas/shell.py`, `ports/llm_port.py`, `testing/cassette_llm.py`, `observability/logging.py`, `bootstrap/seeder.py`).
- `apps/api/src/orcia_api/` -- Application FastAPI (`main.py`, middleware `trace_id`, handler RFC 9457 localisé `Accept-Language`, routes `/api/v1/health` et `/api/v1/navigation/shell`, export OpenAPI 3.1).
- `apps/worker/src/orcia_worker/broker.py` -- Worker Dramatiq Redis et acteur idempotent `system_ping_actor`.
- `packages/api-client/` -- Client TypeScript généré depuis OpenAPI 3.1 (`openapi.json`, `src/generated/schema.ts`, `src/index.ts`).
- `packages/ui/` (`@orcia/ui`) -- Librairie Design System dédiée (`src/styles/tokens.css`, `src/primitives/StatusBadge.tsx`, `src/primitives/HumanLedAnchorCard.tsx`, `src/shell/AppShell.tsx`, `src/shell/GlobalSidebar.tsx`, `src/shell/ScopeSwitcher.tsx`, `src/shell/AssistantDock.tsx`, `src/index.ts`, tests unitaires Vitest d'isolation et de composants).
- `apps/web/` -- Application Next.js 16 assemblant `@orcia/ui`, le dictionnaire `i18n` (`src/i18n/{types.ts,index.tsx,locales/fr.ts,locales/en.ts}`) et les 7 routes modules (`src/app/`), avec tests Vitest & E2E Playwright.
- `docs/implementation-artifacts/tech-lead-reports/1-1-amorçage-du-monorepo-hybride-coquille-ui-direction-c-7-modul-tech-lead-report.md` -- Rapport pérenne Tech Lead (Sections 1 & 2 rédigées, Section 3 à finaliser après tests).

## Tasks & Acceptance

**Execution:**
- [x] `pyproject.toml`, `package.json`, `pnpm-workspace.yaml`, `turbo.json`, `tsconfig.base.json` -- Créer les manifestes racines du monorepo hybride et installer les dépendances dans `.venv` et `pnpm` -- Établir l'outillage d'exécution et de vérification (`AR-1`).
- [x] `infra/docker/docker-compose.yml`, `infra/migrations/`, `infra/scripts/maintenance/00_verify_db_invariants.py` -- Configurer PostgreSQL 18 + `pgvector`, Redis 7.4, MinIO, la migration Alembic `0001` (extension `vector` + trigger *Append-Only*) et le script de maintenance `--dry-run` -- Fournir l'infrastructure persistante et le socle de migrations (`AR-2`).
- [x] `packages/orcia-core/src/orcia_core/` -- Implémenter le squelette hexagonal des 8 domaines, `UUIDv7`, les exceptions métier avec catalogue `i18n` (`fr`/`en`), les contrats Pydantic v2 (`ProblemDetails`, `ShellNavigationResponse`), `structlog` + `trace_id`, `DeterministicCassetteLLM` et `seeder.py` -- Garantir la pureté du domaine et l'observabilité (`AD-1`, `AD-17`, `NFR-OBS-1`).
- [x] `apps/api/src/orcia_api/`, `apps/worker/src/orcia_worker/`, `packages/api-client/` -- Implémenter FastAPI (`/api/v1/health`, `/api/v1/navigation/shell`, middleware `trace_id`, handler RFC 9457 localisé `Accept-Language`), le worker Dramatiq et le générateur `0-diff` du SDK `packages/api-client` -- Assurer le contrat typé bout-en-bout (`AD-1`, `NFR-OBS-1`).
- [x] `packages/ui/` (`@orcia/ui`) & `apps/web/` -- Implémenter la librairie Design System isolée `packages/ui` (`tokens.css` Direction C, `AppShell`, `GlobalSidebar`, `ScopeSwitcher` `⌘W`, `AssistantDock`, `StatusBadge`, `HumanLedAnchorCard`, raccourcis `[` et `]`) puis l'intégrer dans `apps/web` avec le dictionnaire `i18n` typé (`fr`/`en`, défaut `fr`) et les 7 routes -- Livrer le Design System Direction C découplé et l'application web (`UX-DR1`, `UX-DR2`).
- [x] `tests/`, `packages/ui/src/__tests__/` & `apps/web/src/__tests__/` -- Implémenter et exécuter les 5 couches de tests (`pytest` + `hypothesis` $\ge 90\%$, `testcontainers` PG18/Redis/MinIO, contrat OpenAPI `0-diff` + `Schemathesis`, `DeterministicCassetteLLM`, `Vitest` sur `@orcia/ui` + `apps/web` incluant l'audit d'isolation et la parité `i18n` `fr`/`en` & `@playwright/test`), rafraîchir GitNexus et compléter la Section 3 du rapport Tech Lead -- Valider le socle à 100% (`AD-17`, `NFR-TEST-1`).

**Acceptance Criteria:**
- Given le monorepo initialisé, when on exécute `.venv/bin/ruff check .`, `.venv/bin/mypy --strict` et `.venv/bin/pytest --cov=packages/orcia-core --cov-fail-under=90`, then toutes les vérifications passent avec `0` erreur et une couverture $\ge 90\%$.
- Given les schémas Pydantic v2 de `apps/api`, when le script de génération OpenAPI est exécuté, then `packages/api-client` est généré avec `0 diff` et toute erreur API retourne une enveloppe RFC 9457 munie d'un `error_code` invariant, d'un `trace_id` W3C OpenTelemetry et de messages localisés (`fr` par défaut ou `en` via `Accept-Language`).
- Given la librairie Design System `packages/ui` (`@orcia/ui`) et l'application `apps/web`, when la coquille Direction C est rendue sur Desktop (`1440x900`) et Mobile (`390x844`), then `packages/ui` ne contient aucun import `next/*` ou `@orcia/api-client` ni couleur hexadécimale hors `tokens.css`, et le dictionnaire `i18n` typé (`fr`/`en` avec français par défaut), le Sélecteur de Périmètre `⌘W`, les 7 modules du Menu Global et le repli des panneaux latéraux (`[`, `]`) fonctionnent conformément à `UX-DR1` et `UX-DR2`.

## Implementation Notes

- Couverture unitaire `packages/orcia-core` : `99.22%` (`14/14` tests `pytest` passés incluant `hypothesis`, `testcontainers` PG18 + `pgvector` / Redis 7.4 / MinIO, `Schemathesis` et `DeterministicCassetteLLM`).
- Vérifications TypeScript (`pnpm turbo run lint typecheck test`) : `9/9` tâches Turborepo réussies (`10/10` tests `Vitest` sur `@orcia/api-client`, `@orcia/ui`, `@orcia/web`).
- Tests E2E Playwright (`pnpm --filter @orcia/web test:e2e`) : `2/2` projets réussis (`desktop-cockpit` `1440x900` et `mobile-companion` `390x844`).

## Spec Change Log

## Review Triage Log

| ID | Layer | Location | Verdict | Route | Evidence & Triage Decision |
|---|---|---|---|---|---|
| VG-1 | `verification-gap` | `packages/ui/src/__tests__/shell.test.tsx`, `apps/web/src/__tests__/i18n-and-shell.test.tsx` | `medium` | `patch` | Pre-verified gap: `onSelectModule` click and non-`/cockpit` pathname resolution (`resolveModuleFromPathname`) were not asserted in unit/E2E tests. |
| VG-2 | `verification-gap` | `apps/web/src/components/ShellContainer.tsx`, `apps/web/src/__tests__/i18n-and-shell.test.tsx` | `medium` | `patch` | Pre-verified gap: selecting a `READ_ONLY_OBSERVER` scope via `ScopeSwitcher` (`⌘W`) inside `ShellContainer` and verifying `sidebar-access-mode-badge` updates was not asserted. |
| VG-3 | `verification-gap` | `packages/api-client/src/__tests__/client.test.ts` | `medium` | `patch` | Pre-verified gap: `getShellNavigation` URL/query construction (`?scope_id=...` vs no query) and `200 OK` payload resolution were not asserted on `mockFetch`. |
| VG-4 | `verification-gap` | `packages/ui/src/__tests__/shell.test.tsx` | `medium` | `patch` | Pre-verified gap: `AssistantDock` prompt submission (`onSubmitAssistantPrompt` + input reset) and `mobile-tab-*` click state switching were not asserted. |
| VG-5 | `verification-gap` | `tests/unit/test_orcia_core_and_api.py` | `high` | `patch` | Pre-verified gap: `TraceContextMiddleware` extraction of W3C `traceparent` and `X-Workspace-Id` headers was unit-tested on helper functions but not via an HTTP request to `/api/v1/health`. |
| VG-6 | `verification-gap` | `tests/unit/test_orcia_core_and_api.py` | `medium` | `patch` | Pre-verified gap: `system_ping_actor` invocation did not assert state mutation on `default_ping_registry` and `configure_broker(use_stub=False)` was not exercised. |
| VG-7 | `verification-gap` | `tests/contract/test_openapi_contract.py`, `apps/api/src/orcia_api/routers/{health,shell}.py` | `high` | `patch` | Pre-verified gap: `_check_operation` in `test_schemathesis_openapi_contract_compliance` did not call `case.validate_response(response)`. |
| BH-1 / EC-3 | `blind-hunter`, `edge-case-hunter` | `packages/orcia-core/src/orcia_core/domain/exceptions.py:108-122` | `medium` | `patch` | Verified: `resolve_locale` iterated `Accept-Language` tokens without sorting by `;q=` quality weight or skipping `q=0`. |
| BH-2 / EC-1 / VG-O1 | `all` | `apps/api/src/orcia_api/middleware/trace_and_error.py:61-83,106-115` | `medium` | `patch` | Verified: `handle_domain_error` did not forward `exc.instance` to `build_problem_response`, overwriting custom domain error `instance` values with `request.url.path`. |
| BH-3 / EC-2 | `blind-hunter`, `edge-case-hunter` | `apps/api/src/orcia_api/middleware/trace_and_error.py:117-133` | `medium` | `patch` | Verified: `handle_http_exception` mapped non-403/404 4xx `StarletteHTTPException` to `ERR_INTERNAL_SERVER_ERROR` instead of a 4xx validation/client error code and dropped string `exc.detail`. |
| BH-4 | `blind-hunter` | `apps/api/src/orcia_api/middleware/trace_and_error.py:147-154` | `low` | `patch` | Verified: `handle_unexpected_error` did not log the underlying exception type/message before returning the 500 ProblemDetails response. |
| BH-5 / EC-5 / VG-O2 | `all` | `apps/web/src/components/ShellContainer.tsx:55-58` | `medium` | `patch` | Verified: `selectedModuleOverride` was not reset when `pathname` changed, which would leave `activeModuleKey` stale on browser Back/Forward navigation. |
| BH-6 / EC-6 | `blind-hunter`, `edge-case-hunter` | `apps/web/src/components/ModuleWorkspaceView.tsx:10` | `low` | `patch` | Verified: `useState(dictionary.humanAnchor.defaultValue)` kept the initial French default string when switching locale to English unless derived from `customAnchorText ?? dictionary.humanAnchor.defaultValue`. |
| BH-7 | `blind-hunter` | `apps/web/src/components/ShellContainer.tsx` | `false` | `reject` | Refuted: `apps/web` renders standalone in `next dev` / Playwright without requiring a separate live FastAPI process on port 8000; `@orcia/api-client` is verified by contract and client unit tests. |
| BH-8 / EC-8 / VG-O3 | `all` | `packages/ui/src/shell/AppShell.tsx`, `packages/ui/src/styles/tokens.css` | `medium` | `patch` | Verified: responsive CSS classes for `.orcia-app-shell` on `@media (max-width: 768px)` and `data-active-mobile-tab` attribute on `AppShell` prevent mobile horizontal overflow. |
| BH-9 | `blind-hunter` | `packages/ui/src/shell/AppShell.tsx:63-81` | `low` | `patch` | Verified: pressing `Escape` when `ScopeSwitcher` dialog is open did not close `scopeSwitcherOpen`. |
| BH-10 / EC-7 | `blind-hunter`, `edge-case-hunter` | `packages/api-client/src/index.ts:50-54` | `medium` | `patch` | Verified: `await response.json()` on a non-JSON error body throws `SyntaxError` instead of falling back to a synthetic `ProblemDetails` inside `OrciaProblemError`. |
| BH-11 | `blind-hunter` | `apps/web/playwright.config.ts:6-10` | `false` | `reject` | Refuted: `fs.existsSync(cachedChromePath) ? cachedChromePath : undefined` already falls back to `undefined` (Playwright default) when the local Linux cache path is absent. |
| BH-12 | `blind-hunter` | `apps/worker/src/orcia_worker/broker.py:65` | `low` | `patch` | Verified: defaulting `ORCIA_WORKER_STUB_BROKER` to `"0"` when `REDIS_URL` is set ensures production workers use `RedisBroker` automatically while unit tests without `REDIS_URL` use `StubBroker`. |
| BH-13 | `blind-hunter` | `packages/orcia-core/src/orcia_core/bootstrap/seeder.py:55-82` | `low` | `reject` | Rejected per low-severity rule: `UpsertSpec` explicitly separates `conflict_columns` and `value_columns` by contract. |
| EC-4 | `edge-case-hunter` | `packages/orcia-core/src/orcia_core/observability/logging.py:42-48` | `low` | `patch` | Verified: `resolve_or_create_trace_id` checked `trace_id != '0'*32` but did not reject all-zero `parent-id` (`match.group(2) != '0'*16`) per W3C Trace Context. |

## Verification

**Commands:**
- `.venv/bin/ruff check . && .venv/bin/ruff format --check .` -- expected: `0 errors`
- `.venv/bin/mypy --strict packages/orcia-core apps/api apps/worker` -- expected: `Success: no issues found`
- `.venv/bin/pytest --cov=packages/orcia-core --cov-fail-under=90` -- expected: `all tests pass, coverage >= 90%`
- `pnpm turbo run lint typecheck test` -- expected: `all packages (@orcia/api-client, @orcia/ui, @orcia/web) pass`
- `.venv/bin/python .agent/skills/bmad-architecture/scripts/lint_spine.py --workspace docs/planning-artifacts/architecture/architecture-ORCIA-2026-10-24` -- expected: `"ok": true, "total_findings": 0`
