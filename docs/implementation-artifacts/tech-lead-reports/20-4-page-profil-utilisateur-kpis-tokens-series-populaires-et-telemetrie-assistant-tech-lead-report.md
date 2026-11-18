# Story 20.4 — Page Dédiée « Mon Profil » (`/profile`, Style ChatGPT : Identité, 4 KPIs Tokens/Séries & Éléments Populaires) & Télémétrie Tokens de `Mon Assistant`

- **Date** : 2026-11-17
- **Story / Clé Sprint** : `20-4-page-profil-utilisateur-kpis-tokens-series-populaires-et-telemetrie-assistant` (`Epic 20`, prépare `ACTION_ITEM-20.1`)
- **Capacité(s)** : `CAP-065`, `CAP-069` (nouvelle capacité à créer dans `docs/product/capabilities.yaml`) — classification : `feature | ux`
- **Auteur / Contexte** : Conception de la vue dédiée `Profil` (accessible depuis l'entrée `Profil` et l'en-tête du popup `Mon Compte` bas-gauche) sur le modèle ChatGPT fourni : identité/rôles/rattachements BU & Équipes, 4 KPIs (`Total des tokens`, `Pic de tokens`, `Série la plus longue`, `Série en cours`) et bloc `Agents, Processus & Outils populaires`, alimentés par PostgreSQL 18 (`audit_ledger`, `workflow_runs`, `step_executions`) et complétés par l'enregistrement effectif des tokens consommés dans `Mon Assistant`. La Heatmap 12 mois et le tableau Statistiques avancées sont différés dans `ACTION_ITEM-20.1` suite à l'arbitrage utilisateur. Couvre `FR-25`, `FR-32`, `AD-17`, `AD-19`.
- **Commits associés** : *(en cours d'implémentation)*

---

## 1. Analyse du Besoin & Étude d'Impact Tech Lead (Pré-Implémentation)

### 1.1 Contexte & Problématique
1. **Absence d'écran `Profil` personnel dans l'application** :
   - Aucune route `/profile` n'existe dans `apps/web/src/router.tsx`.
   - Aucun endpoint d'agrégation personnelle (`GET /api/v1/users/me/profile-summary`) n'existe : les requêtes FinOps (`sql_finops_dashboard.py`) agrègent par scope (`GLOBAL | BU | TEAM | WORKSPACE`), jamais par utilisateur (`actor_id` / `initiated_by_user_id`).
2. **Angles morts sur la consommation de tokens de `Mon Assistant`** :
   - `assistant_llm_providers.py:L56-L62, L145-L183, L276-L339` n'envoie pas `"stream_options": {"include_usage": True}` sur les flux OpenAI-compatible et n'extrait pas `usage` (`input_tokens`/`output_tokens`).
   - `assistant_background_turns.py` et `assistant_workspace.py` écrivent uniquement dans `PROMPT_TELEMETRY_LOG` en mémoire et n'insèrent jamais `ASSISTANT_TURN_COMPLETED` dans `audit_ledger`.

### 1.2 Exploration, Analyse d'Impact GitNexus, Factorisation & Dette Technique
- **Vérification des contraintes SQL (`audit_ledger`)** :
  - `audit_ledger.event_type` (`VARCHAR(64) NOT NULL`) n'a aucune contrainte `CHECK` en base ; `ASSISTANT_TURN_COMPLETED` s'insère directement via `SqlAuditLedgerService.record_entry` (table append-only protégée par trigger). Aucune migration Alembic supplémentaire requise pour Story 20.4.
- **Contrôle de Volumétrie (`< 350` L par fichier)** :
  - `assistant_workspace.py` fait déjà `391` L et `assistant_llm_providers.py` `343` L.
  - Découpage planifié :
    1. Créer un helper léger `apps/api/src/orcia_api/routers/_assistant_usage_telemetry.py` (`< 160 L`) pour normaliser l'extraction `usage` (réel ou repli déterministe `max(1, len(text) // 4)` marqué `usage_source: "estimated"`) et persister `ASSISTANT_TURN_COMPLETED` dans `SqlAuditLedgerService` sans alourdir `assistant_workspace.py` ni `assistant_background_turns.py`.
    2. Créer `packages/orcia-core/src/orcia_core/audit_finops/_internal/sql_user_profile_stats.py` (`< 240 L`) et `packages/orcia-core/src/orcia_core/audit_finops/user_profile_service.py` (`< 160 L`, calcul pur des séries de jours consécutifs `longest_streak_days` / `current_streak_days`).
    3. Créer `apps/api/src/orcia_api/routers/user_profile.py` (`< 160 L`) et `apps/api/src/orcia_api/schemas/user_profile.py` (`< 140 L`).
    4. Créer `packages/ui/src/primitives/UserProfileOverviewPage.tsx` (`< 240 L`) et `apps/web/src/routes/profile.tsx` (`< 160 L`).

---

## 2. Plan d'Implémentation

### 2.1 Schéma de Données & Migrations Alembic
- **Aucune nouvelle migration Alembic requise** : s'appuie sur `audit_ledger`, `workflow_runs`, `step_executions`, `org_units`, `iam_accounts` et `users`.

### 2.2 Noyau Métier Hexagonal (`packages/orcia-core/src/orcia_core/audit_finops/`)
- `user_profile_service.py` (pur domaine, 0 dépendance framework) :
  - `compute_activity_streaks(active_dates_desc, today)` : calcule `longest_streak_days` et `current_streak_days` (série active si `today` ou `today - 1 day` est actif).
  - Modèles `UserProfileSummary`, `PopularUsageItem` (`item_type: "AGENT" | "PROCESS" | "SKILL" | "TOOL"`, `item_key`, `title`, `usage_count`, `target_route`).
- `_internal/sql_user_profile_stats.py` :
  - Requêtes strictement confinées à `(actor_id = :user_id OR LOWER(actor_email) = LOWER(:user_email))` sur `audit_ledger` et `initiated_by_user_id = :user_id` sur `workflow_runs` + `step_executions` :
    - `total_tokens = SUM(input_tokens + output_tokens)`
    - `peak_daily_tokens = MAX(daily_sum)`
    - Dates distinctes d'activité UTC (`DATE(created_at AT TIME ZONE 'UTC')`) pour calcul des séries.
    - Top 5 `popular_items` agrégés depuis `step_executions` / `audit_ledger` (liste vide `[]` au Jour 0).

### 2.3 Couche Backend API, Sécurité & Contrats (`apps/api/`, `packages/api-client/`)
- `routers/assistant_llm_providers.py`, `routers/_assistant_usage_telemetry.py`, `assistant_background_turns.py`, `assistant_workspace.py` :
  - Activation de `"stream_options": {"include_usage": True}` sur streaming OpenAI-compatible + extraction `usage` / `usageMetadata` (avec fallback déterministe `estimated` si le fournisseur streamé n'émet pas `usage`).
  - Persistance asynchrone de `ASSISTANT_TURN_COMPLETED` dans `SqlAuditLedgerService` (`actor_type="HUMAN"`, `actor_id`, `actor_email`, `workspace_id`, `model_id`, `input_tokens`, `output_tokens`, `latency_ms`).
- `schemas/user_profile.py` & `routers/user_profile.py` (enregistré dans `main.py`) :
  - `GET /api/v1/users/me/profile-summary` (authentifié uniquement, jamais d'identité arbitrable par paramètre query : anti-IDOR par construction).
- Régénération SDK `@orcia/api-client` (`scripts/export_openapi.py`, `0-diff`).

### 2.4 Interface Utilisateur & Expérience (`packages/ui/`, `apps/web/`)
- `packages/ui/src/primitives/UserProfileOverviewPage.tsx` (Direction C, 0 `#hex` en dur, `i18n` en props) :
  - En-tête centré : Avatar initiales (`64px`), Nom complet, `@handle · email`, badges sobres BU / Équipes / Rôles, bouton `Modifier` ouvrant la modale Paramètres (`Compte & Sécurité`).
  - Grille 4 cartes KPI : `Total des tokens` · `Pic de tokens` · `Série la plus longue` · `Série en cours`.
  - Section `Agents, Processus & Outils populaires` (cartes cliquables vers `/agents` ou `/processes`, ou état vide sobre `0` donnée fictive).
  - Aucune Heatmap ni tableau Statistiques avancées (différés dans `ACTION_ITEM-20.1`).
- `apps/web/src/routes/profile.tsx` + `router.tsx` + `SidebarAccountPopover` (`Profil` et en-tête identité navigant vers `/profile`).

### 2.5 Analyse d'Impact sur la Pyramide des Tests (`AD-17`)
- **Couche 1a (`pytest` $\ge 90\%$)** & **Couche 1b (`Vitest`)** : tests unitaires de `compute_activity_streaks` (trous de dates, série active aujourd'hui vs hier, 0 activité Jour 0), extraction `usage` streaming/non-streaming et repli `estimated` ; Vitest sur `/profile` (4 KPIs, rattachements, éléments populaires, clic `Modifier` ouvrant la modale Paramètres, survie `F5`).
- **Couche 2 (`HTTP FastAPI ➔ PostgreSQL 18 SELECT` via `testcontainers`)** : insertion `ASSISTANT_TURN_COMPLETED` + runs workflows de deux utilisateurs A et B $\rightarrow$ `GET /api/v1/users/me/profile-summary` en tant que A ne compte strictement que les tokens, séries et éléments populaires de A (0 fuite des données de B).
- **Couche 3 (`OpenAPI 0-diff`, `lint-imports`, `mypy --strict`, `ruff`)** & **Couche Sécurité** : isolation stricte `GET /users/me/profile-summary` (`401` sans session).
- **Couche 5 (`Playwright E2E`)** : smoke `/profile` dans `11-screens-smoke-without-server-errors.spec.ts`.

---

## 3. Bilan des Modifications & Résultats (Post-Implémentation)

### 3.1 Fichiers Développés & Modifiés
| Fichier | Nature (Création / Modification / Refactoring) | Volumétrie (`wc -l`) | Description synthétique |
| :--- | :--- | :--- | :--- |
| `packages/orcia-core/src/orcia_core/audit_finops/user_profile_service.py` | Création | `165` L | Modèles domaine purs `UserProfileSummary`, `PopularUsageItem`, calcul pur `compute_activity_streaks`, `derive_user_handle`, `rank_popular_usage_items`, `empty_user_profile_summary` (0 import framework `AD-19`). |
| `packages/orcia-core/src/orcia_core/audit_finops/_internal/sql_user_profile_stats.py` | Création | `244` L | Agrégations PostgreSQL 18 strictement confinées à l'utilisateur connecté (`fetch_user_profile_summary_sql` : tokens, pic journalier, dates actives UTC, Top 5 `popular_items`). |
| `packages/orcia-core/src/orcia_core/audit_finops/_internal/_sql_user_profile_orgs.py` | Création | `139` L | Lecture PostgreSQL 18 des rôles IAM et rattachements BU/Équipes (`led_business_units`, `ontology_business_units`, `led_teams`, `member_teams`). |
| `packages/orcia-core/src/orcia_core/audit_finops/__init__.py` | Modification | `118` L | Export public des symboles `user_profile_service` et `fetch_user_profile_summary_sql`. |
| `apps/api/src/orcia_api/schemas/user_profile.py` | Création | `41` L | Schémas OpenAPI 3.1 `PopularUsageItemResponse` et `UserProfileSummaryResponse`. |
| `apps/api/src/orcia_api/routers/user_profile.py` | Création | `90` L | Endpoint `GET /api/v1/users/me/profile-summary` (anti-IDOR sans paramètre `user_id`, `401` sans session valide). |
| `apps/api/src/orcia_api/routers/_assistant_usage_telemetry.py` | Création | `152` L | Extraction `usage`/`usageMetadata`/`prompt_eval_count`, fallback déterministe `max(1, len // 4)` (`usage_source="estimated"`) et persistance idempotente `ASSISTANT_TURN_COMPLETED` dans `SqlAuditLedgerService`. |
| `apps/api/src/orcia_api/routers/_assistant_workspace_context.py` | Création | `144` L | Extraction contexte fil/dossier, `to_active_turn_response` et `record_non_stream_turn_telemetry` pour maintenir `assistant_workspace.py <= 355` L. |
| `apps/api/src/orcia_api/routers/assistant_llm_providers.py` | Modification | `352` L | Ajout `"stream_options": {"include_usage": True}` sur requêtes streaming OpenAI-compatible et extraction tokens non-streaming/streaming. |
| `apps/api/src/orcia_api/routers/assistant_llm_gemini_adapter.py` | Modification | `193` L | Extraction `build_anthropic_native_request_body` pour alléger `assistant_llm_providers.py`. |
| `apps/api/src/orcia_api/routers/assistant_background_turns.py` | Modification | `347` L | Persistance `ASSISTANT_TURN_COMPLETED` via `_finalize` à l'issue des tours streaming SSE (live et fallback). |
| `apps/api/src/orcia_api/routers/assistant_llm_bridge.py` | Modification | `349` L | Propagation `input_tokens`, `output_tokens`, `usage_source`, `user_email`, `user_display_name` et `audit_ledger_sink`. |
| `apps/api/src/orcia_api/routers/assistant_workspace.py` | Modification | `331` L | Câblage télémétrie `audit_ledger` sur `/three-speed/turn` et `/three-speed/stream`. |
| `apps/api/src/orcia_api/main.py` | Modification | `176` L | Montage de `user_profile_router`. |
| `scripts/export_openapi.py` & `packages/api-client/` | Modification / Régénération | — | Ajout de `"user_profile"` dans `SCHEMA_DOMAIN_MODULES`, régénération `openapi.json`, `generated/user_profile.ts`, wrapper `getUserProfileSummary` dans `authAndShell.ts`. |
| `packages/ui/src/primitives/UserProfileOverviewTypes.ts` | Création | `58` L | Contrats typés `UiUserProfileSummaryView`, `UiProfilePopularUsageItem`, `UserProfileOverviewLabels`. |
| `packages/ui/src/primitives/UserProfileOverviewPage.tsx` | Création | `194` L | Vue Profil style ChatGPT (avatar `64px`, `@handle · email`, badges rôles/BU/équipes, bouton `Modifier`, 4 KPIs, Top 5 populaires ou état vide Jour 0, 0 `#hex`, 0 texte en dur). |
| `packages/ui/src/index.ts` | Modification | `743` L | Export public de `UserProfileOverviewPage` et ses types. |
| `apps/web/src/i18n/locales/profile_overview_labels.ts`, `fr.ts`, `en.ts`, `types.ts` | Création / Modification | `65` L | Dictionnaires bilingues FR/EN `profileOverview`. |
| `apps/web/src/routes/profile.tsx` | Modification | `130` L | Remplacement du stub par `UserProfileRouteView` branché sur `GET /api/v1/users/me/profile-summary`, ouverture modale `ACCOUNT_SECURITY` sur `Modifier`, survie `F5`. |
| `apps/web/src/__tests__/story-20-4-profile-overview-and-f5.test.tsx`, `vitestUserSettingsMockHandlers.ts`, `zero-dead-buttons-and-silent-catches-audit.test.tsx`, `apps/web/e2e/11-screens-smoke-without-server-errors.spec.ts` | Création / Modification | — | Tests Vitest (`/profile`, 4 KPIs, `Modifier`, survie `F5`), audit anti-boutons-muets et smoke E2E `/profile`. |
| `tests/unit/test_story_20_4_profile_streaks_and_assistant_usage.py`, `tests/security/test_story_20_4_profile_isolation.py`, `tests/integration/api/test_story_20_4_profile_summary_postgres18.py` | Création | — | Tests unitaires (`100 %` couv.), sécurité (`401` / anti-IDOR) et intégration `testcontainers` PostgreSQL 18. |
| `docs/product/capabilities.yaml`, `docs/implementation-artifacts/tech-lead-reports/README.md` | Modification | — | Ajout de `CAP-069` (`live`, `runtime`) et indexation du rapport Tech Lead. |

### 3.2 Résultats Chiffrés, Métriques & Qualité
- **Couverture de tests** :
  - `packages/orcia-core/src/orcia_core/audit_finops/user_profile_service.py` : **`100%`** (`61` statements, `16` branches, `0` miss).
  - `apps/api/src/orcia_api/routers/_assistant_usage_telemetry.py` : **`100%`** (`58` statements, `26` branches, `0` miss).
  - Total ciblé Story 20.4 (`pytest --cov ... --cov-fail-under=90`) : **`100.00%`** (`7 passed`).
- **Qualité statique & Architecture** :
  - `.venv/bin/ruff check .` & `.venv/bin/ruff format --check .` : **`0` erreur / `All checks passed!`**
  - `.venv/bin/mypy --strict packages/orcia-core/src apps/api/src apps/worker/src` : **`Success: no issues found in 477 source files`**
  - `.venv/bin/lint-imports` : **`5 contracts kept, 0 broken`** (`AD-19` & `AD-20`)
  - `.venv/bin/python scripts/export_openapi.py --check` : **`0-diff` (`exit 0`)**
  - `.venv/bin/python .agent/skills/bmad-architecture/scripts/lint_spine.py` : **`ok: true, 0 findings`**
  - `.venv/bin/python scripts/check_implementation_docs.py` : **`162` rapports conformes**
  - `npx gitnexus analyze` + `gitnexus_detect_changes()` : **`34,144` nœuds, `59,623` arêtes, `1,471` flux** indexés sans régressions.

### 3.3 Validation & Procédure de Test sur Toute la Pyramide (`AD-17` + 5 Garde-Fous de Câblage Vertical)
- **Couche 1a & Sécurité (`pytest`)** : `.venv/bin/pytest -q tests/unit tests/security` $\rightarrow$ **`709` tests passés (`0` échec)**, incluant les tests unitaires des séries/extractions (`test_story_20_4_profile_streaks_and_assistant_usage.py`) et l'isolation `401` / anti-IDOR (`test_story_20_4_profile_isolation.py`).
- **Couche 1b (`pnpm turbo run lint typecheck test --force`)** : **`9/9` tâches réussies** (`@orcia/api-client`, `@orcia/ui` `103/103`, `@orcia/web` `153/153` incluant `story-20-4-profile-overview-and-f5.test.tsx` avec survie `F5` `unmount()`/`render()` et `zero-dead-buttons-and-silent-catches-audit.test.tsx`).
- **Couche 2 (`HTTP FastAPI ➔ PostgreSQL 18 SELECT` via `testcontainers`)** : `tests/integration/api/test_story_20_4_profile_summary_postgres18.py` $\rightarrow$ **`1 passed`** contre `pgvector/pgvector:pg18` (isolation stricte User A vs User B sur tokens, pic, séries, BU/Équipes, `popular_items` et insertion `ASSISTANT_TURN_COMPLETED` depuis `POST /api/v1/assistant/three-speed/turn` vérifiée par `SELECT` PG18).
- **Couche 3 & Documentation (`CAP-069`)** : `pnpm site:sync && pnpm site:check` $\rightarrow$ **`65/65` capacités live vérifiées (`0` sans test), `28` routes, `133` primitives UI synchronisées**.
