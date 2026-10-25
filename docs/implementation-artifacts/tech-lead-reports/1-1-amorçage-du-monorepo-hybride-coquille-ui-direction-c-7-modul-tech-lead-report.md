# Story 1.1 — Amorçage du Monorepo Hybride, Coquille UI Direction C (7 Modules) & Socle de Tests à 5 Couches

- **Date** : 2026-10-25
- **Story / Clé Sprint** : `1-1-amorçage-du-monorepo-hybride-coquille-ui-direction-c-7-modul` (`Epic 1`)
- **Auteur / Contexte** : Amorçage Greenfield du monorepo hybride TypeScript/Python d'ORCIA, de l'infrastructure conteneurisée (PostgreSQL 18 + `pgvector`, Redis 7.4, MinIO), du pipeline de génération OpenAPI 3.1 `0-diff`, de la coquille applicative Direction C à 3 colonnes et 7 modules (`DESIGN.md`, `EXPERIENCE.md`), et du harnais de tests à 5 couches (`AR-1`, `AR-2`, `AD-1`, `AD-17`, `UX-DR1`, `UX-DR2`, `NFR-OBS-1`, `NFR-TEST-1`).
- **Commits associés** : _À compléter après validation et commit final_

---

## 1. Analyse du Besoin & Étude d'Impact Tech Lead (Pré-Implémentation)

### 1.1 Contexte & Problématique
- **Problème résolu** : Avant de pouvoir implémenter l'authentification bi-mode (`Story 1.2`), le Catalogue Fédéré (`Story 1.3`) ou l'Ontologie à 4 niveaux (`Epic 2`), l'équipe d'ingénierie a besoin d'une fondation monorepo unifiée garantissant par construction :
  1. l'isolation hexagonale stricte de `packages/orcia-core` (zéro couplage framework dans `domain/` et `ports/`),
  2. la synchronisation automatique sans dérive (`0-diff`) entre les schémas Pydantic v2 (`packages/orcia-core/schemas` + `apps/api`) et le client TypeScript (`packages/api-client`),
  3. l'observabilité bout-en-bout (`structlog` / `pino` avec propagation W3C `trace_id` et enveloppes d'erreur **RFC 9457 Problem Details**),
  4. la coquille visuelle **Direction C ("Obsidian Cockpit & Daylight Studio")** à 3 colonnes adaptatives, Sélecteur de Périmètre Hiérarchique (`⌘W`) et Menu Global à 7 modules,
  5. le harnais de tests à 5 couches (`AD-17`) avec seuil bloquant $\ge 90\%$.
- **Comportement attendu vs actuel** : Le dépôt contient actuellement uniquement les artefacts de planification (`docs/`), la configuration BMad (`_bmad/`, `.agent/`), `AGENTS.md` et `.venv/`. L'objectif est d'établir l'intégralité de l'arborescence exécutable et testée.
- **Contraintes `ARCHITECTURE-SPINE.md`** : Respect strict des versions et frontières `AD-1` à `AD-17`, clés primaires `UUIDv7`, zéro couleur hexadécimale en dur dans les composants TSX, et fichiers maintenus sous `300–400` lignes.

### 1.2 Exploration, Analyse d'Impact GitNexus, Factorisation & Dette Technique
- **Analyse d'Impact GitNexus (`gitnexus_query` sur `repo: "ORCIA"`)** :
  - L'index initial (`541 nodes | 699 edges`) couvre uniquement la documentation et les scripts `_bmad`. Aucun symbole de code applicatif existant n'est impacté en amont (`blast radius = 0` sur du code existant, création Greenfield).
- **Opportunités de Factorisation dès la Fondation (`DRY` / Primitives Partagées)** :
  1. **Générateur `UUIDv7` & Types d'Identifiants Typés (`packages/orcia-core/src/orcia_core/domain/identifiers.py`)** : Factoriser dès la `Story 1.1` la génération et la validation des identifiants `UUIDv7` monotones pour éviter que chaque domaine (`permissions`, `catalog`, `ontology`, `orchestration`) ne réimplémente sa propre logique d'ID.
  2. **Enveloppe RFC 9457 Problem Details & Exceptions Domaine (`packages/orcia-core/src/orcia_core/schemas/problem_details.py` & `domain/exceptions.py`)** : Centraliser la hiérarchie d'exceptions métier (`OrciaDomainError`, `ObserverModeReadOnlyError`, `HumanAnchorRequiredError`, `ReadSourceDeniedError`) et leur sérialisation RFC 9457 corrélée au `trace_id` W3C OpenTelemetry.
  3. **Harnais `DeterministicCassetteLLM` (`packages/orcia-core/src/orcia_core/ports/llm_port.py` & `testing/cassette_llm.py`)** : Fournir dès la `Story 1.1` le port `LlmGatewayPort` et son implémentation déterministe par cassettes JSON/SHA-256 pour que toutes les Stories des Epics 1 à 6 puissent tester leurs interactions IA à `0 $` en CI.
  4. **Fonction Trigger PostgreSQL *Append-Only* (`infra/migrations/versions/0001_story_1_1_foundation_extensions.py`)** : Créer dès la révision Alembic `0001` l'extension `vector` (`pgvector`) et la fonction PL/pgSQL réutilisable `orcia_prevent_append_only_mutation()` que `blackboard_snapshots` (`Story 3.2`) et `audit_ledger` (`Story 6.1`) brancheront en une ligne.
  5. **Architecture `i18n` *Zero-Debt* Typée de Bout en Bout (`apps/web/src/i18n/` & `packages/orcia-core/src/orcia_core/domain/exceptions.py`)** : Structurer dès la `Story 1.1` un dictionnaire TypeScript strictement typé (`locales/fr.ts` par défaut + `locales/en.ts`, zéro dépendance externe hors Spine, zéro chaîne littérale UI en dur dans le JSX) et un catalogue d'erreurs RFC 9457 localisable (`Accept-Language: fr|en` avec `error_code` machine invariant).
  6. **Librairie Design System Dédiée `packages/ui` (`@orcia/ui`)** : Isoler l'intégralité des Design Tokens CSS sémantiques Direction C (`packages/ui/src/styles/tokens.css`), des primitives accessibles (`StatusBadge`, `HumanLedAnchorCard`) et des composants de coquille UX/UI (`AppShell`, `GlobalSidebar`, `ScopeSwitcher`, `ConciergeDock`) dans un package autonome `@orcia/ui` découplé de `next/*`, `zustand` et `@orcia/api-client`. C'est le pendant frontend exact de l'architecture hexagonale de `packages/orcia-core`.
- **Contrôle de Volumétrie & Découpage** :
  - Séparation franche entre `packages/ui` (composants visuels contrôlés `< 150` lignes chacun + tokens CSS + tests unitaires Vitest dédiés) et `apps/web` (routage App Router, `i18n`, connexion aux stores et à l'API).
- **Tickets de Dette Technique / Refactoring créés** :
  - Aucun ticket de dette technique (`0` dette à ce stade Greenfield ; dettes potentielles `i18n` et couplage UI/App neutralisées préventivement dès la Story 1.1).

---

## 2. Plan d'Implémentation

### 2.1 Schéma de Données & Migrations Alembic (`infra/migrations/`)
- `infra/docker/docker-compose.yml` :
  - Services `postgres` (`pgvector/pgvector:pg18`), `redis` (`redis:7.4.2-alpine`), `minio` (`minio/minio:latest`) avec healthchecks et volumes nommés.
- `infra/migrations/env.py` & `infra/migrations/versions/0001_story_1_1_foundation_extensions.py` :
  - Activation de `CREATE EXTENSION IF NOT EXISTS vector;`
  - Création de la fonction trigger PostgreSQL immuable `orcia_prevent_append_only_mutation()` (`RAISE EXCEPTION 'ERR_APPEND_ONLY_VIOLATION: table % is strictly append-only', TG_TABLE_NAME`).
  - Support complet de `upgrade()` et `downgrade()`.
- `infra/scripts/maintenance/00_verify_db_invariants.py` :
  - Script de maintenance de référence supportant `--dry-run` (rollback par défaut) et `--apply`.

### 2.2 Noyau Métier Hexagonal, Orchestration & Workers (`packages/orcia-core/`, `apps/worker/`)
- `packages/orcia-core/src/orcia_core/` :
  - Squelette des 8 domaines bornés (`orchestration`, `blackboard`, `catalog`, `ontology`, `rag`, `gates`, `permissions`, `audit_finops`).
  - `domain/identifiers.py` : Génération `new_uuid7()`, validation de version/monotonicité.
  - `domain/exceptions.py` : Exceptions typées du domaine avec `error_code` canonique invariant, statut HTTP cible et catalogue de messages localisés `fr`/`en`.
  - `ports/llm_port.py` & `testing/cassette_llm.py` : Port `LlmGatewayPort` et adaptateur `DeterministicCassetteLLM` pour la couche 4 de tests (`AD-17`).
  - `observability/logging.py` : Configuration `structlog` JSON et gestionnaire de contexte `trace_id` W3C OpenTelemetry (`workspace_id`, `run_id`, `step_id`).
  - `bootstrap/seeder.py` : Socle du seeder idempotent (`UpsertSpec`).
- `apps/worker/src/orcia_worker/broker.py` :
  - Configuration du broker Dramatiq Redis et acteur idempotent `system_ping_actor`.

### 2.3 Couche Backend API, Sécurité & Contrats (`apps/api/`, `packages/api-client/`)
- `apps/api/src/orcia_api/` :
  - `main.py` : Application FastAPI `0.143`, middleware OpenTelemetry `TraceContextMiddleware` (injectant `trace_id` dans `request.state` et l'en-tête `X-Trace-Id`), et gestionnaire d'exceptions global retournant une enveloppe **RFC 9457 Problem Details** (`application/problem+json`) localisée selon `Accept-Language` (`fr` par défaut, `en` supporté, avec en-tête `Content-Language`).
  - `routers/health.py` & `routers/shell.py` : Endpoints `GET /api/v1/health` et `GET /api/v1/navigation/shell` (retournant les 7 modules du Menu Global, l'arbre de périmètres `⌘W` et le résumé du *Profil Humain*).
  - `scripts/export_openapi.py` : Export déterministe du contrat OpenAPI 3.1 vers `packages/api-client/openapi.json` et génération TypeScript vers `packages/api-client/src/generated/schema.d.ts` + client typé `packages/api-client/src/index.ts`.

### 2.4 Librairie Design System (`packages/ui`) & Interface Applicative (`apps/web/`)
- `packages/ui/` (`@orcia/ui`) :
  - `src/styles/tokens.css` : Source unique des tokens CSS sémantiques Direction C (`--color-sidebar-bg: #0F172A`, `--color-surface-bg: #F8FAFC`, `--color-dock-bg: #F1F5F9`, `--color-primary-cobalt: #2563EB`, `--color-human-led-violet: #6D28D9`, `--color-arbitration-amber: #D97706`, `--color-gate-emerald: #059669`, `--color-ontology-cyan: #0284C7`, `--color-stale-crimson: #DC2626`) et polices `--font-sans` (`Inter`), `--font-serif` (`Instrument Serif`), `--font-mono` (`JetBrains Mono`).
  - `src/primitives/` : `StatusBadge.tsx`, `HumanLedAnchorCard.tsx` (seul composant autorisé à consommer `--color-human-led-violet`).
  - `src/shell/` :
    - `AppShell.tsx` : Grille Desktop à 3 colonnes adaptatives (`Sidebar 235px/68px` + `Canvas Central 1fr` + `Dock Agent Concierge & Permission Broker 360px`), écouteurs clavier `[` (repli Sidebar), `]` (repli Dock IA) et `⌘W` / `Ctrl+W` (ouverture du sélecteur de périmètre), et régions `aria-live="polite"`.
    - `GlobalSidebar.tsx` : Composant contrôlé affichant les 7 modules avec icônes, libellés injectés via props `labels`, badge compteur ambre d'actions *Contributeur*, badge rouge `!` (`[STALE_WARNING]`) et badge de *Profil Humain*.
    - `ScopeSwitcher.tsx` : Sélecteur hiérarchique (`🌐 Plateforme Globale → 🏢 BU / Tribu → 👥 Équipe → 🗂️ Workspace Solution`).
    - `ConciergeDock.tsx` : Dock persistant de l'Agent Concierge & Permission Broker.
- `apps/web/` (`@orcia/web`) :
  - `src/i18n/` (`types.ts`, `locales/fr.ts`, `locales/en.ts`, `index.tsx`) : Dictionnaire `i18n` typé (`TranslationDictionary`), `I18nProvider` (défaut `'fr'`) et hook `useI18n()`.
  - `src/app/` : Layout racine important `@orcia/ui/styles/tokens.css`, assemblant `AppShell` (`@orcia/ui`) avec `useI18n()`, et exposant les 7 routes modules.

---

## 3. Bilan des Modifications & Résultats (Post-Implémentation)

### 3.1 Fichiers Développés & Modifiés
| Fichier | Nature | Description synthétique |
| :--- | :--- | :--- |
| `pyproject.toml`, `package.json`, `pnpm-workspace.yaml`, `turbo.json`, `tsconfig.base.json` | Création | Manifestes racines du monorepo hybride (`pnpm 10.6` + `Turborepo` et `.venv` Python 3.12+ avec `ruff`, `mypy --strict`, `pytest`, `coverage >= 90%`). |
| `infra/docker/docker-compose.yml` | Création | Topologie conteneurisée PostgreSQL 18 + `pgvector`, Redis 7.4.2 et MinIO avec healthchecks et volumes nommés. |
| `infra/migrations/alembic.ini`, `infra/migrations/env.py`, `infra/migrations/versions/0001_story_1_1_foundation_extensions.py` | Création | Socle Alembic Asyncio, activation de `vector` (`pgvector`) et fonction trigger PostgreSQL *Append-Only* `orcia_prevent_append_only_mutation()`. |
| `infra/scripts/maintenance/00_verify_db_invariants.py` | Création | Script de maintenance de référence avec mode `--dry-run` (rollback par défaut) et `--apply`. |
| `packages/orcia-core/src/orcia_core/**` | Création | Noyau hexagonal des 8 domaines bornés, `domain/identifiers.py` (`UUIDv7`), `domain/exceptions.py` (catalogue `i18n` `fr`/`en`), `ports/llm_port.py`, `testing/cassette_llm.py`, `schemas/problem_details.py`, `schemas/shell.py`, `observability/logging.py`, `bootstrap/seeder.py`. |
| `apps/api/src/orcia_api/**`, `scripts/export_openapi.py` | Création | Application FastAPI (`/api/v1/health`, `/api/v1/navigation/shell`), `TraceContextMiddleware`, gestionnaire global RFC 9457 localisé (`Accept-Language: fr\|en`) et exporteur déterministe OpenAPI 3.1 (`0-diff`). |
| `apps/worker/src/orcia_worker/broker.py` | Création | Broker Dramatiq Redis et acteur idempotent `system_ping_actor` (`ProcessedPingRegistry`). |
| `packages/api-client/**` | Création | Schéma `openapi.json`, types générés `src/generated/schema.ts`, client typé `createOrciaApiClient` et erreur `OrciaProblemError`. |
| `packages/ui/**` (`@orcia/ui`) | Création | Librairie Design System Direction C isolée (`src/styles/tokens.css`, `StatusBadge.tsx`, `HumanLedAnchorCard.tsx`, `AppShell.tsx`, `GlobalSidebar.tsx`, `ScopeSwitcher.tsx`, `ConciergeDock.tsx` et tests Vitest). |
| `apps/web/**` (`@orcia/web`) | Création | Application Next.js App Router assemblant `@orcia/ui`, le dictionnaire `i18n` typé (`locales/fr.ts`, `locales/en.ts`, `I18nProvider`), les 7 routes modules (`/cockpit`, `/inbox`, `/catalog`, `/ontology`, `/gates`, `/finops`, `/workspaces`) et les tests Vitest + Playwright E2E. |
| `tests/unit/**`, `tests/integration/**`, `tests/contract/**` | Création | Suite de tests Python couvrant les couches 1, 2 (`testcontainers`), 3 (`0-diff` + `Schemathesis`) et 4 (`DeterministicCassetteLLM`). |

### 3.2 Résultats Chiffrés, Métriques & Qualité
- **Couverture de tests** :
  - `packages/orcia-core` (`pytest-cov`) : **`99.27%`** (`349` statements, `1` miss — seuil minimal exigé : `>= 90%`, `14` tests `pytest` passés).
  - Tests TypeScript (`Vitest` sur `@orcia/api-client`, `@orcia/ui`, `@orcia/web`) : **`13/13` tests unitaires passés** (`4` fichiers de tests).
- **Performances mesurées** :
  - Suite complète `pytest` (incluant démarrage des 3 conteneurs réels PostgreSQL 18 + `pgvector`, Redis 7.4 et MinIO) : `9.14 s`.
  - Pipeline `pnpm turbo run lint typecheck test` : `3.69 s`.
  - Suite E2E Playwright (`desktop-cockpit` + `mobile-companion`) : `5.1 s`.
- **Qualité statique & Architecture** :
  - `.venv/bin/ruff check .` & `.venv/bin/ruff format --check .` : `0 error / 96 files formatted`
  - `.venv/bin/mypy --strict packages/orcia-core apps/api apps/worker` : `Success: no issues found in 33 source files`
  - `pnpm turbo run lint typecheck test` : `9/9 tasks successful`
  - `.venv/bin/python .agent/skills/bmad-architecture/scripts/lint_spine.py` : `"ok": true, "total_findings": 0`
  - `gitnexus` (`analyze --index-only` + `detect_changes`) : Index rafraîchi (`1,175 nodes | 1,595 edges | 30 clusters | 38 flows`), `risk_level: "low"`, `affected_count: 0`.

### 3.3 Validation & Procédure de Test (5 Couches `AD-17`)
- **Couche 1 — Tests Unitaires & Propriétés (`pytest` + `hypothesis`, `Vitest`)** :
  - Pureté hexagonale AST (`domain/` et `ports/` n'importent aucun framework), génération/monotonicité `UUIDv7` (`hypothesis`), catalogue d'erreurs `i18n` (`fr`/`en`), `structlog` + `trace_id` W3C, `seeder.py`, endpoints FastAPI, idempotence Dramatiq, isolation `@orcia/ui` (zéro import `next/*`/`zustand`/`@orcia/api-client`, zéro hex hors `tokens.css`, exclusivité de `--color-human-led-violet` sur `HumanLedAnchorCard.tsx`) et parité récursive `fr.ts`/`en.ts`.
- **Couche 2 — Tests d'Intégration (`testcontainers-python` : PostgreSQL 18 + `pgvector`, Redis 7.4, MinIO)** :
  - Exécution réelle d'Alembic `0001_story_1_1` (`upgrade` $\rightarrow$ vérification de l'extension `vector(3)` et blocage effectif de `UPDATE`/`DELETE` par `orcia_prevent_append_only_mutation()` levant `ERR_APPEND_ONLY_VIOLATION` $\rightarrow$ `downgrade` $\rightarrow$ `upgrade`), validation du script `00_verify_db_invariants.py` (`--dry-run` et `--apply`), verrou atomique Redis `SET NX EX 900` et démarrage MinIO.
- **Couche 3 — Tests de Contrat API (`export_openapi.py --check` 0-diff + `Schemathesis`)** :
  - Synchronisation `0-diff` vérifiée entre FastAPI OpenAPI 3.1, `packages/api-client/openapi.json` et `packages/api-client/src/generated/schema.ts`, et fuzzing `Schemathesis` validant la conformité RFC 9457 (`application/problem+json` + `trace_id`).
- **Couche 4 — Tests d'Orchestration IA (`DeterministicCassetteLLM`)** :
  - Rejeu déterministe (`0 $` en CI) par empreinte `sha256:<64-hex>`, pause `WAITING_FOR_HUMAN_ARBITRATION` en mode `COACHING`, balise `[ASSUMPTION]` en mode `FAST_PATH` et rejet `ModelOrthogonalityViolationError` (`AD-10`) lorsque `evaluator_model_family == executor_model_family`.
- **Couche 5 — Tests E2E & Multi-Viewport (`@playwright/test` Desktop `1440x900` & Mobile `390x844`)** :
  - Rendu de la coquille Direction C à 3 colonnes et 7 modules en français par défaut, repli de la Sidebar via `[`, repli du Dock Concierge via `]`, bascule dynamique `FR -> EN` et barre d'onglets Mobile Companion.

