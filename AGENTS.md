<!-- bmad:context -->
<!-- Verified 2026-10-27 against 420a171. Managed by bmad-project-context; edits inside this block are replaced on refresh. Keep anything you want preserved outside the markers. -->

## ORCIA

Orchestration of Processes, Context, and Intelligent Agents — hybrid TypeScript (`pnpm 10.6` + `Turborepo 2.4`, `Vite 6.4` + `TanStack Router 1.166` SPA, `React 19.1`, `Tailwind CSS 4.3`) and Python (`3.12+` in `.venv/` across a 4-package `uv 0.13.5` workspace: `packages/orcia-kernel`, `packages/orcia-core`, `apps/api`, `apps/worker`; `FastAPI 0.143`, `DBOS Transact 2.14` + `Dramatiq 2.1`, `SQLAlchemy 2.1` Asyncio, `PostgreSQL 18.0` + `pgvector 0.8.7`, `Redis 7.4`, `SeaweedFS 4.17`) modular monolith. Planning lives in `docs/planning-artifacts/`, sprint tracking in `docs/implementation-artifacts/sprint-status.yaml`, and Tech Lead implementation reports in `docs/implementation-artifacts/tech-lead-reports/`.

## Policy

- Always use the project virtual environment `/home/romain/Documents/Projects/ORCIA/.venv` (`.venv/bin/python`, `.venv/bin/pytest`, `.venv/bin/ruff`, `.venv/bin/mypy`, `.venv/bin/alembic`, `.venv/bin/lint-imports`) for every Python command; never use system `python3` or global `pip`/`pytest`.
- Before implementing any User Story or evolution, act as a Tech Lead / Senior Dev: study the US, run a GitNexus impact analysis (`gitnexus_query`, `gitnexus_context`, `gitnexus_impact`), check for code factorization opportunities (`DRY` / shared primitives), split any file approaching `300–400` lines, and proactively add dedicated technical debt / refactoring tickets (`Story N.Ma` in `docs/planning-artifacts/epics.md` + `docs/implementation-artifacts/sprint-status.yaml` or entries under `action_items:` in `sprint-status.yaml`).
- For every User Story or significant evolution, generate and maintain a permanent Tech Lead Analysis & Implementation Report at `docs/implementation-artifacts/tech-lead-reports/{story-key}-tech-lead-report.md` following `docs/implementation-artifacts/TECH-LEAD-REPORT-TEMPLATE.md`.
- Enforce strict TDD (`Red → Green → Refactor`) with a mandatory minimum unit test coverage of `>= 90%` (`--cov-fail-under=90`) and all 5 testing layers (`AD-17`) before marking any Story `review` or `done`.
- Never mock PostgreSQL (with SQLite) or Redis in integration tests; always run against real ephemeral containers via `testcontainers-python` (PostgreSQL 18 + `pgvector`, Redis 7.4, SeaweedFS S3) and use `DeterministicCassetteLLM` (`0 $` external LLM calls in CI).
- Enforce unidirectional modular monolith boundaries (`AD-19`, verified by `.venv/bin/lint-imports`): `orcia_kernel` $\leftarrow$ `orcia_core` domains $\leftarrow$ `orcia_api` / `orcia_worker`, with zero circular dependencies between domain modules (`blackboard`, `catalog`, `permissions`, `orchestration`, `ontology`, `audit_finops`, `identity`, `bootstrap`), zero cross-domain `_internal` imports (`orcia_core.<domaine>._internal`), and zero framework/SDK imports (`fastapi`, `sqlalchemy`, `dbos`, `dramatiq`, `redis`, `litellm`, `docling`, `wasmtime`) inside `orcia_kernel`, `orcia_core/domain`, or `orcia_core/ports`.
- Keep HTTP/OpenAPI transport schemas (`*Request`, `*Response`) exclusively in `apps/api/src/orcia_api/schemas/<domaine>.py` — never inside `packages/orcia-core` — and define domain errors per bounded context in `packages/orcia-core/src/orcia_core/<domaine>/errors.py` inheriting from `orcia_kernel.errors.OrciaDomainError` (no central `domain/exceptions.py` catch-all).
- Wire all services and concrete adapters exclusively in the application Composition Root (`lifespan` + `Depends(get_*_service)` in `apps/api/src/orcia_api/dependencies.py` and `apps/worker`); never instantiate `_DEFAULT_*_SERVICE` singletons at module import time, and keep `InMemory*` stores exclusively under `tests/unit/fakes/`.
- Route non-blocking cross-domain side effects (`StepCompleted`, `ArtifactProduced`, `GateEvaluated`, `RunTerminated`, `HumanArbitrationRequested`) through the transactional PostgreSQL Outbox table `domain_events_outbox` (`orcia_kernel.events`); reserve synchronous cross-domain calls strictly for blocking workflow decisions (`permissions`, `gates`, human arbitration).
- Never hand-edit `packages/api-client/src/generated/` or write untyped `fetch()` in `apps/web`; regenerate the domain-sharded OpenAPI 3.1 SDK from FastAPI/Pydantic v2 (`0-diff` gate).
- Never add a third-party dependency outside `ARCHITECTURE-SPINE.md` without updating the spine and passing `.venv/bin/python .agent/skills/bmad-architecture/scripts/lint_spine.py --workspace docs/planning-artifacts/architecture/architecture-ORCIA-2026-10-24` (`0 findings`).
- Never leave orphan `TODO` or `FIXME` comments in code; every `TODO(key)` must reference an active story key or `action_items` entry in `docs/implementation-artifacts/sprint-status.yaml`.

## Where things are

- Architecture Spine (19 locked ADs & stack versions): `docs/planning-artifacts/architecture/architecture-ORCIA-2026-10-24/ARCHITECTURE-SPINE.md`
- Detailed Architecture & Core ERD (18 tables including `workspace_datasources` & `domain_events_outbox`): `docs/planning-artifacts/architecture/architecture-ORCIA-2026-10-24/architecture.md`
- Stack Review, Modularity Analysis & Sprint Change Proposal: `docs/planning-artifacts/research/stack-review-2026-10-27.md`, `docs/planning-artifacts/research/modularity-analysis-2026-10-27.md`, and `docs/planning-artifacts/sprint-change-proposal-2026-10-27.md`
- PRD (33 FRs, 13 NFRs, 12 UJs): `docs/planning-artifacts/prds/prd-ORCIA-2026-10-24/prd.md`
- UX Design Tokens & Experience (Direction C, 16 UX-DRs): `docs/planning-artifacts/ux-designs/ux-ORCIA-2026-10-24/DESIGN.md` and `EXPERIENCE.md`
- Epics & 33 User Stories (`status: final`, 7 Epics): `docs/planning-artifacts/epics.md`
- Sprint Tracking File: `docs/implementation-artifacts/sprint-status.yaml`
- Tech Lead Report Template: `docs/implementation-artifacts/TECH-LEAD-REPORT-TEMPLATE.md`
- Tech Lead Reports Directory: `docs/implementation-artifacts/tech-lead-reports/`

## Running and verifying

- Python commands must run through `.venv/bin/`: `.venv/bin/ruff check .`, `.venv/bin/ruff format --check .`, `.venv/bin/mypy --strict packages/orcia-kernel packages/orcia-core apps/api apps/worker`, `.venv/bin/lint-imports`, `.venv/bin/pytest --cov=packages/orcia-kernel --cov=packages/orcia-core --cov-fail-under=90`.
- TypeScript commands run via `pnpm`: `pnpm turbo run lint typecheck test`.
- Architecture spine lint: `.venv/bin/python .agent/skills/bmad-architecture/scripts/lint_spine.py --workspace docs/planning-artifacts/architecture/architecture-ORCIA-2026-10-24`.
- GitNexus index refresh: `npx gitnexus analyze` (run after structural changes and before `gitnexus_detect_changes()`).

## Conventions that differ from defaults

- All database primary keys use `UUIDv7` (`uuid-utils`), never `SERIAL` or `UUIDv4`.
- All schema evolutions go through incremental, immutable Alembic revisions in `infra/migrations/versions/` (with tested `upgrade()` and `downgrade()`); never edit a revision from a completed story, and never import application ORM models inside an Alembic migration — use raw SQL (`op.execute(sa.text(...))`) following the `Expand → Backfill SQL → Contract` pattern.
- Reference/system seed data (`orcia://system/bootstrap/*`, `assistant-agent` DAG, default Human Profile archetypes) uses idempotent upserts (`INSERT ... ON CONFLICT DO UPDATE`) in `packages/orcia-core/bootstrap/seeder.py`, and operational data transformations or backfills outside schema migrations live in `infra/scripts/maintenance/XX_*.py` with a mandatory `--dry-run` mode (default rollback unless `--apply` is passed) and batched idempotent transactions.
- Tables `audit_ledger` and `blackboard_snapshots` are strictly append-only (protected by PostgreSQL `BEFORE UPDATE OR DELETE RAISE EXCEPTION` triggers); never disable these triggers in migrations or maintenance scripts — draft artifacts live in `step_executions.draft_artifact_jsonb` and intermediate reasoning in `step_executions.step_memlog_jsonb`.
- Every API error returns an `application/problem+json` envelope (**RFC 9457 Problem Details**) carrying the W3C OpenTelemetry `trace_id`.
- Every mutation endpoint enforces `RunAccessGuard` / `ScopeAccessGuard` (`GLOBAL | BU | TEAM | WORKSPACE`) and rejects `READ_ONLY_OBSERVER` with `HTTP 403 ERR_OBSERVER_MODE_READ_ONLY`.
- All UX/UI components and Direction C semantic CSS tokens (`DESIGN.md`) MUST live in the dedicated Design System library `packages/ui` (`@orcia/ui`), isolated from `apps/web` routing, feature modules (`apps/web/src/features/<domaine>/`), stores, and API calls (`packages/ui` must never import `@tanstack/react-router`, `next/*`, or `@orcia/api-client`); never use raw hex colors outside `packages/ui/src/styles/tokens.css`, and reserve Violet `#6D28D9` (`human-led-violet`) exclusively for `HumanLedAnchorCard` (`human_authored_required: true`).
- All user-facing UI labels, microcopy, and documentation artifacts default to **French (`fr`)**, backed by the typed zero-dependency `i18n` dictionary (`apps/web/src/i18n/locales/{fr,en}.ts`, injected as typed props into `@orcia/ui` components) and localized RFC 9457 error catalogs (`Accept-Language` resolution with invariant `error_code`) — never hardcode raw user-facing strings directly inside JSX components.

## Known pitfalls

- Never run blocking calls (`time.sleep`, `requests`, synchronous disk I/O, or synchronous `subprocess.run`) inside FastAPI's `asyncio` event loop or execute SQL queries inside Python `for` loops (`N+1`); use `selectinload`/`joinedload` or bounded recursive CTEs (`WITH RECURSIVE ... WHERE depth <= 2`).
- `DBOS Transact` steps and `Dramatiq` workers (`apps/worker`) may retry on transient failures — every workflow step, Outbox consumer, and actor must be idempotent and never duplicate `audit_ledger`, `blackboard_snapshots`, or `domain_events_outbox` rows.
- Never copy or extend the 3 legacy circular dependencies (`packages/orcia-core/src/orcia_core/blackboard/models.py:L15` $\leftrightarrow$ `orchestration/engine.py:L17-26`, `catalog/service.py:L14` $\leftrightarrow$ `bootstrap/workflows.py:L21`, `permissions/broker.py:L14` $\leftrightarrow$ `bootstrap/workflows.py:L29`) or the 3 import-time router singletons (`apps/api/src/orcia_api/routers/auth.py:L25`, `catalog.py:L27`, `orchestration.py:L39`) scheduled for removal in `Story 3.2a`.
- Always scope every GitNexus MCP tool call and resource lookup explicitly to `repo: "ORCIA"` (`gitnexus://repo/ORCIA/...` or `--repo .`) and never call `list_repos` or inspect other repositories registered in the user's global `~/.gitnexus/registry.json`.

<!-- /bmad:context -->

---

# Protocole Tech Lead / Dev Senior & Rapport Pérenne d'Implémentation

Pour chaque User Story (`Story N.M`) ou évolution du projet **ORCIA**, l'agent agit en tant que **Tech Lead / Dev Senior** selon le cycle obligatoire en 3 temps ci-dessous :

## 1. Étude Préalable d'Impact, Factorisation & Dette Technique (Avant Codage)
1. **Étude critique de l'US** : Vérifier les critères d'acceptation (`epics.md`), les décisions d'architecture (`ARCHITECTURE-SPINE.md`, `architecture.md`) et les spécifications UX (`DESIGN.md`, `EXPERIENCE.md`).
2. **Analyse d'impact GitNexus** : Exécuter `gitnexus_query`, `gitnexus_context` et `gitnexus_impact({target, direction: "upstream"})` sur les symboles existants touchés.
3. **Opportunités de factorisation & contrôle de volumétrie** :
   - Identifier toute brique réutilisable dans `packages/orcia-kernel`, `packages/orcia-core`, `packages/api-client`, `apps/api` ou `apps/web` afin d'éviter toute duplication.
   - Si un fichier touché approche ou dépasse **300–400 lignes** (ou cumule plusieurs responsabilités), planifier son découpage immédiat.
4. **Création proactive de tickets de dette technique / refactoring** :
   - Si le refactoring est court ($< 20\%$ de l'US), l'exécuter en **Étape 0 (Pre-Story Refactoring)** de l'US courante.
   - Si une dette technique naissante ou une refonte structurelle dépasse le cadre immédiat de l'US, **ajouter sans hésiter** :
     - soit une **Story intercalaire `Story N.Ma`** dans `docs/planning-artifacts/epics.md` et `docs/implementation-artifacts/sprint-status.yaml`,
     - soit un ticket dans la section `action_items:` de `docs/implementation-artifacts/sprint-status.yaml`.

## 2. Génération du Rapport Pérenne Tech Lead (`docs/implementation-artifacts/tech-lead-reports/`)
Chaque User Story ou fonctionnalité livrée doit produire un document pérenne dans **`docs/implementation-artifacts/tech-lead-reports/{story-key}-tech-lead-report.md`** basé sur le gabarit officiel [TECH-LEAD-REPORT-TEMPLATE.md](file:///home/romain/Documents/Projects/ORCIA/docs/implementation-artifacts/TECH-LEAD-REPORT-TEMPLATE.md) :
- **Section 1 (`Analyse du Besoin & Étude d'Impact Tech Lead`)** : rédigée **avant** l'implémentation (contexte, problématique, analyse GitNexus, chiffres clés / exploration DB, factorisations et tickets de dette créés).
- **Section 2 (`Plan d'Implémentation`)** : migrations Alembic (`2.1`), noyau hexagonal & workers (`2.2`), backend FastAPI & SDK OpenAPI (`2.3`), interface SPA Vite + TanStack Router Direction C (`2.4`).
- **Section 3 (`Bilan des Modifications & Résultats`)** : complétée **après** implémentation et passage des 5 couches de tests (tableau des fichiers créés/modifiés, métriques chiffrées & couverture $\ge 90\%$, validation des 5 couches `AD-17` et résultat de `gitnexus_detect_changes()`).

---

# Règles Fondamentales UX & UI (Invariants de Conception)

Toute conception, revue ou implémentation dans `@orcia/ui` (`packages/ui`) et `apps/web` doit appliquer strictement ces **11 règles fondamentales** ([`EXPERIENCE.md`](file:///home/romain/Documents/Projects/ORCIA/docs/planning-artifacts/ux-designs/ux-ORCIA-2026-10-24/EXPERIENCE.md) et [`DESIGN.md`](file:///home/romain/Documents/Projects/ORCIA/docs/planning-artifacts/ux-designs/ux-ORCIA-2026-10-24/DESIGN.md)) :

## 1. Les 6 Règles Fondamentales de l'UX (Expérience Utilisateur)
L'UX désigne le parcours, la fluidité et la logique de navigation du portail :
1. **Centrer sur l'utilisateur** : Concevoir pour les besoins réels des utilisateurs cibles (selon leur **Profil Humain**), jamais pour le goût personnel des équipes internes.
2. **Viser la simplicité (Loi de Hick / Minimalisme)** : Éliminer les éléments superflus pour éviter de surcharger l'utilisateur (1 module = 1 intention claire ; pas d'empilement de panneaux hors contexte).
3. **Respecter les standards du web** : Utiliser des schémas de navigation familiers (logo/identité en haut à gauche ramenant à l'accueil, en-tête et navigation structurés).
4. **Assurer un bon feedback** : Chaque action de l'utilisateur (clic, validation, erreur) doit entraîner une réponse visuelle ou textuelle immédiate.
5. **Offrir des sorties de secours** : L'utilisateur doit pouvoir annuler une action, fermer une modale/tiroir (`Escape`), replier un panneau ou revenir en arrière facilement.
6. **Optimiser la performance et le Mobile-First** : Privilégier la rapidité de chargement/rendu et penser d'abord l'affichage sur smartphone (Mobile Companion sans débordement).

## 2. Les 5 Règles Fondamentales de l'UI (Interface Utilisateur)
L'UI traduit l'UX en éléments visuels tangibles, esthétiques et fonctionnels :
1. **Hiérarchie visuelle** : Guider l'œil en jouant sur les tailles, les contrastes, les espacements et les graisses de police pour distinguer l'important du secondaire.
2. **Limitation des typographies (Max 2)** : Se restreindre à **maximum deux typographies** — une primaire (`Inter` / `Geist Sans` pour l'interface, les titres et la lecture) et une secondaire (`JetBrains Mono` / `Geist Mono` pour les URI, hashes et code) — afin de conserver une lecture harmonieuse.
3. **Cohérence graphique** : Utiliser un système de composants unifié dans `@orcia/ui` (boutons, cartes, badges au design strictement identique pour une même action).
4. **Gestion des grilles (Grids)** : Structurer la page à l'aide de colonnes, de gouttières (`gap`) et de marges régulières pour aligner proprement tous les éléments.
5. **Contrastes et accessibilité (WCAG AA)** : S'assurer que les couleurs de texte et de fond respectent les normes de contraste pour être lisibles par tous.

<!-- gitnexus:start -->
# GitNexus — Code Intelligence

This project is indexed by GitNexus as **ORCIA** (541 symbols, 699 relationships, 17 execution flows).

> Index stale? Run `node .gitnexus/run.cjs analyze --index-only` from the project root — it auto-selects an available runner. No `.gitnexus/run.cjs` yet? Bootstrap with `npx`, `bunx`, or `pnpm dlx` — e.g. `bunx gitnexus@latest analyze` (npm 11 npx crash; #1939).

## Always Do

- **MUST run impact before editing.** Use `impact({target: "symbolName", direction: "upstream"})` or `node .gitnexus/run.cjs impact "symbolName" --direction upstream --repo .`; report callers, processes, and risk. Never substitute grep for graph analysis.
- **MUST analyze graph changes before committing.** Use `detect_changes({scope: "all"})` (MCP) or `node .gitnexus/run.cjs detect-changes --scope all --repo .` (CLI fallback). `partial: true` or `truncated: true` is not a clean check — a zero means unseen, not unaffected; re-run it. For regression review: `detect_changes({scope: "compare", base_ref: "main"})` or `node .gitnexus/run.cjs detect-changes --scope compare --base-ref "main" --repo .`.
- MUST warn on HIGH/CRITICAL `risk` pre-edit; never use `riskSharedAxes` to waive a HIGH/CRITICAL `risk` warning. Compare File/symbol: MCP File omits axes; Graph-RAG expands File.
- **MUST treat `risk: UNKNOWN` as unresolved, not as low.** An empty caller set is not evidence the symbol is unused — it can also mean the callers are not resolvable by the index (plain-object property access, dynamic dispatch, cross-language calls). `impact` pairs `UNKNOWN` with a `riskNote` saying so. Confirm with a text search before treating the symbol as safe to change or delete; do not proceed on the strength of a zero.
- **MUST use `query({search_query: "concept"})` for concepts/flows, `context({name: "symbolName"})` for a named symbol, or `impact` for blast radius, on read-only callers, dependencies, imports, or execution flow.** Graph first; text search only for empty/`UNKNOWN`/literals.
- For security review, `explain({target: "fileOrSymbol"})` lists taint findings (source→sink flows; needs `analyze --pdg`).

## Never Do

- NEVER edit a function, class, or method before MCP/CLI impact analysis.
- NEVER ignore HIGH or CRITICAL risk warnings from impact analysis, and never read `UNKNOWN` as an all-clear — it means the walk could not answer, which is the one verdict that requires confirming by other means.
- NEVER rename symbols with find-and-replace — use `rename` which understands the call graph.
- NEVER commit before MCP/CLI graph change analysis.

## Resources

| Resource | Use for |
| --- | --- |
| `gitnexus://repo/ORCIA/context` | Codebase overview, check index freshness |
| `gitnexus://repo/ORCIA/clusters` | All functional areas |
| `gitnexus://repo/ORCIA/processes` | All execution flows |
| `gitnexus://repo/ORCIA/process/{name}` | Step-by-step execution trace |

## CLI

| Task | Read this skill file |
| --- | --- |
| Understand architecture / "How does X work?" | `.claude/skills/gitnexus-exploring/SKILL.md` |
| Blast radius / "What breaks if I change X?" | `.claude/skills/gitnexus-impact-analysis/SKILL.md` |
| Trace bugs / "Why is X failing?" | `.claude/skills/gitnexus-debugging/SKILL.md` |
| Rename / extract / split / refactor | `.claude/skills/gitnexus-refactoring/SKILL.md` |
| Tools, resources, schema reference | `.claude/skills/gitnexus-guide/SKILL.md` |
| Index, status, clean, wiki CLI commands | `.claude/skills/gitnexus-cli/SKILL.md` |

<!-- gitnexus:end -->
