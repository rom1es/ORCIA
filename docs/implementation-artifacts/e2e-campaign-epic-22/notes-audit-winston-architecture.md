# 🏗️ Audit Croisé Architecture & Vérité PostgreSQL 18 — Campagne E2E Epic 22 (Winston / Story 22.9)

- **Auditeur** : 🏗️ **Winston** (System Architect — `bmad-agent-architect`)
- **Périmètre** : Diagnostic architectural des causes racines de la campagne E2E Epic 22 (`feat/epic-22-remediation-pg18-direction-c`, commit `a1bb059`), confrontation aux constats visuels de 🎨 **Sally** ([`notes-audit-sally-ux.md`](./notes-audit-sally-ux.md)), arbitrages d'interface et ordonnancement topologique pour l'**Epic 23**.
- **Référentiels appliqués** :
  - [`ARCHITECTURE-SPINE.md`](../../planning-artifacts/architecture/architecture-ORCIA-2026-10-24/ARCHITECTURE-SPINE.md) (`AD-1`..`AD-24`)
  - [`sprint-change-proposal-2026-11-18-epic-22-remediation-plan.md`](../../planning-artifacts/sprint-change-proposal-2026-11-18-epic-22-remediation-plan.md)
  - [`bilan-execution-tests-e2e-epic-22.md`](./bilan-execution-tests-e2e-epic-22.md) & [`playwright-results.json`](./playwright-results.json)
  - [`notes-audit-sally-ux.md`](./notes-audit-sally-ux.md) & captures dans `./screenshots/`
  - Invariants d'architecture et politique de triggers append-only de [`GEMINI.md`](../../../GEMINI.md)

---

## 1. Synthèse exécutive & Chiffres de vérité PostgreSQL 18

🏗️ La campagne Epic 22 (`110` scénarios planifiés : `55` `desktop-cockpit` + `55` `mobile-companion`, durée `432 047 ms` / `7,20 min`) démontre un **paradoxe de maturité PostgreSQL 18** :

1. **Preuve positive (`#1`–`#10`)** : les corrections de l'Epic 22 ont éliminé les échecs de persistance PG18 observés en Epic 21 sur les dossiers de Mon Assistant (`#8`, `#9` PASS dans `assistant_folders`) et sur le workflow *Human-Led* (`#10` PASS dans `human_anchor_signatures`, `step_executions`, `blackboard_snapshots`).
2. **Révélation de la panne latente (`#10` → `#11`–`#110`)** : dès que le scénario `#10` (`03-human-led-anchor-and-arbitration.spec.ts`) a réellement inséré des lignes dans `step_executions` et `blackboard_snapshots`, le script de remise à zéro Jour 0 (`resetDay0()`) s'est heurté à la contrainte `ON DELETE RESTRICT` de `blackboard_snapshots`, provoquant **`87` échecs en cascade** (`43` desktop + `44` mobile) et masquant **`100 %` du Mobile Companion (`0 / 55` PASS)** ainsi que toutes les specs `04` à `21` et `shell.spec.ts`.
3. **Preuve du durcissement Fail-Closed (`#3`, `#4`, `#7`)** : après purge de `ORCIA_E2E_SEED_FIXTURES`, la pile E2E (`ORCIA_ENV="e2e"`) rejette légitimement en `HTTP 401` les requêtes anonymes de smoke API (`#3`, `#4`) et a révélé un oubli critique d'en-tête `Authorization: Bearer` dans le client SSE `streamAssistantTurnSse` (`#7`, plus le même défaut latent dans `useReflexiveExecutionController.ts` et le défaut inverse d'absence d'auth sur `/api/v1/events/stream`).

| Catégorie | Scénarios | Causes racines architecturales (`ARCH23-*`) |
| --- | ---: | --- |
| **Succès (`passed`)** | **7** (`#1`, `#2`, `#5`, `#6`, `#8`, `#9`, `#10`) | Persistance PG18 réelle prouvée, mais défauts résiduels Shell/Aide/Accostage/Cockpit/Modale (`ARCH23-04`..`ARCH23-08`) |
| **Échecs `HTTP 401` directs** | **3** (`#3`, `#4`, `#7`) | Requêtes E2E anonymes Jour 0 (`ARCH23-02`) + client SSE sans `Authorization: Bearer` (`ARCH23-03`) |
| **Échecs cascade `resetDay0()`** | **87** (`#11`–`#110` hors skips) | `DELETE FROM step_executions` bloqué par FK `ON DELETE RESTRICT` + triggers append-only (`ARCH23-01`), masquant `04`–`21` & Mobile (`ARCH23-10`) |
| **Ignorés (`skipped` viewport)** | **13** (`2` desktop, `11` mobile) | Gardes `test.skip` attendus sur viewport non ciblé |

---

## 2. Diagnostic architectural des causes racines (`ARCH23-01`..`ARCH23-10`)

### `ARCH23-01` (`P0`) — Collision entre `09_reset_db_first_boot.py` (`DELETE FROM`) et les contraintes `ON DELETE RESTRICT` + triggers append-only

- **Localisation exacte** :
  - Appelant E2E : [`apps/web/e2e/support/day0.ts`](../../../apps/web/e2e/support/day0.ts#L12-L18) → [`infra/scripts/e2e/reset_day0.py`](../../../infra/scripts/e2e/reset_day0.py#L23-L39)
  - Script SQL : [`infra/scripts/maintenance/09_reset_db_first_boot.py`](../../../infra/scripts/maintenance/09_reset_db_first_boot.py#L38-L108) et [`L137-L159`](../../../infra/scripts/maintenance/09_reset_db_first_boot.py#L137-L159)
  - Contraintes & triggers PG18 :
    - [`infra/migrations/versions/0011_story_3_2_step_executions_and_blackboard_snapshots.py`](../../../infra/migrations/versions/0011_story_3_2_step_executions_and_blackboard_snapshots.py#L90-L92) (`run_id REFERENCES workflow_runs(id) ON DELETE RESTRICT`, `step_execution_id REFERENCES step_executions(id) ON DELETE RESTRICT`, `parent_snapshot_id REFERENCES blackboard_snapshots(id) ON DELETE RESTRICT`) et [`L138-L142`](../../../infra/migrations/versions/0011_story_3_2_step_executions_and_blackboard_snapshots.py#L138-L142) (`trg_blackboard_snapshots_append_only` `BEFORE UPDATE OR DELETE ... FOR EACH ROW`)
    - [`infra/migrations/versions/20261116_0601_story_6_1_audit_ledger_append_only.py`](../../../infra/migrations/versions/20261116_0601_story_6_1_audit_ledger_append_only.py#L145-L153) (`prevent_audit_ledger_mutation` `BEFORE UPDATE OR DELETE ON audit_ledger FOR EACH ROW`)
    - [`infra/migrations/versions/0015_story_3_4_human_anchors_and_arbitration.py`](../../../infra/migrations/versions/0015_story_3_4_human_anchors_and_arbitration.py#L42) (`authored_by_user_id REFERENCES users(id) ON DELETE RESTRICT`)
    - [`infra/migrations/versions/0013_story_3_2e_connector_schemes_expand.py`](../../../infra/migrations/versions/0013_story_3_2e_connector_schemes_expand.py#L89) (plus `L108`, `L127`, `L146` : `ON DELETE RESTRICT` vers `connector_schemes(scheme)`)
  - Schéma DBOS hors `public` : [`packages/orcia-core/src/orcia_core/orchestration/_internal/dbos_engine.py`](../../../packages/orcia-core/src/orcia_core/orchestration/_internal/dbos_engine.py#L89-L109) et [`uow.py`](../../../packages/orcia-core/src/orcia_core/orchestration/_internal/uow.py#L70-L93) (`schema="dbos"`).

- **Mécanisme de panne** :
  1. `09_reset_db_first_boot.py` place `alembic_version`, `blackboard_snapshots` et `audit_ledger` dans `PROTECTED_TABLES` (`L38-44`), puis boucle avec `DELETE FROM {table_name}` sur `ORDERED_MUTABLE_TABLES_TO_CLEAR` (`L145-150`, dont `step_executions` en `L59` et `workflow_runs` en `L62`), suivi d'une boucle sur toute autre table `public` (`L153-158`).
  2. Dès que le test `#10` (`03-human-led-anchor-and-arbitration.spec.ts`) crée une exécution d'étape et signe l'ancrage humain en PG18, `blackboard_snapshots` contient au moins une ligne référençant `step_executions(id)` et `workflow_runs(id)` via `ON DELETE RESTRICT` (`0011:L90-91`).
  3. À l'appel suivant de `resetDay0()` (scénario `#11`), `DELETE FROM step_executions` viole immédiatement la FK `blackboard_snapshots_step_execution_id_fkey` (`RestrictViolationError`), annulant toute la transaction et laissant `Alice Admin E2E` en base pour les **87 scénarios suivants**.
  4. **Trois angles morts secondaires détectés dans ce mécanisme** :
     - **Table de référence `connector_schemes`** : absente de `PROTECTED_TABLES` et de `ORDERED_MUTABLE_TABLES_TO_CLEAR`, elle est donc ciblée par la boucle dynamique `L153-158` (`DELETE FROM connector_schemes`) alors que `00-stack-smoke.spec.ts:L64-68` exige sa présence après `resetDay0()`.
     - **Schéma `dbos` & Redis E2E** : `09_reset_db_first_boot.py:L141` n'inspecte que `schemaname = 'public'` (laissant d'éventuels checkpoints `dbos.*` résiduels), et `reset_day0.py` ne vide pas Redis (`help:*`, `speed2:*`, verrous `lock:step:*`) ni ne réinitialise `app.state.platform_setup_snapshot` dans le process FastAPI `uvicorn` maintenu vivant par `e2e_stack.py`.

- **Arbitrage architectural (respect impératif de `GEMINI.md` sur les triggers append-only)** :
  - **Règle bloquante** : `GEMINI.md` interdit strictement de désactiver (`ALTER TABLE ... DISABLE TRIGGER`) les triggers append-only `trg_blackboard_snapshots_append_only` et `prevent_audit_ledger_mutation` dans les migrations ou scripts de maintenance.
  - **Option A — `TRUNCATE TABLE ... RESTART IDENTITY CASCADE` exclusivement dans la pile E2E isolée (`reset_day0.py`)** :
    - *Propriété PostgreSQL 18 vérifiée* : les triggers de `0011:L138-142` et `20261116_0601:L148-152` sont déclarés `BEFORE UPDATE OR DELETE ... FOR EACH ROW` (et **non** `BEFORE TRUNCATE`). Un `TRUNCATE TABLE ... RESTART IDENTITY CASCADE` sur les tables transactionnelles/append-only (en **excluant** impérativement `alembic_version` et `connector_schemes`, et en réinitialisant `platform_auth_settings` + `boot_epoch` + `dbos.*` hors tables système DBOS si nécessaire) vide atomiquement `step_executions`, `workflow_runs`, `blackboard_snapshots` et `audit_ledger` sans jamais toucher ni désactiver aucun trigger.
    - *Garde-fou obligatoire* : **ne jamais** mettre ce `TRUNCATE` de tables append-only dans le script de maintenance partagé [`09_reset_db_first_boot.py`](../../../infra/scripts/maintenance/09_reset_db_first_boot.py) (qui doit rester sûr pour une base dev/staging en refusant ou en conservant les tables append-only intactes). Le cantonner strictement dans [`infra/scripts/e2e/reset_day0.py`](../../../infra/scripts/e2e/reset_day0.py) après vérification de [`is_isolated_e2e_database_url(state["database_url"])`](../../../infra/scripts/e2e/e2e_stack_config.py#L28) (`dbname == "orcia_e2e"`, hôte local, port non-dev), complété par un `FLUSHDB` sur `state["redis_url"]` et un bump de `boot_epoch`.
  - **Option B — Clonage instantané d'une base template (`orcia_e2e_template`) dans `e2e_stack.py`** :
    - *Avantage* : état Jour 0 bit-à-bit exact en `< 150 ms`.
    - *Inconvénient* : oblige `uvicorn` (`asyncpg` + `DBOS`) et tous ses pools de connexions à fermer/rouvrir à chaque `resetDay0()` (`DROP DATABASE ... WITH (FORCE)` tue les connexions FastAPI actives et déclenche des erreurs `Pool/ConnectionClosed` sur `app_lifespan`).
  - **Décision recommandée** : **Option A (`TRUNCATE ... RESTART IDENTITY CASCADE` ciblé sous garde `is_isolated_e2e_database_url` + `FLUSHDB` Redis dans `reset_day0.py`)** + ajout explicite de `"connector_schemes"` à `PROTECTED_TABLES` dans `09_reset_db_first_boot.py` et nettoyage sécurisé `if COUNT(*) == 0` / garde explicite dans la maintenance.

---

### `ARCH23-02` (`P0`) — Rejets `HTTP 401` sur `00-stack-smoke.spec.ts` `#3` et `#4` (désalignement tests vs durcissement `ORCIA_ENV="e2e"`)

- **Localisation exacte** :
  - Tests E2E : [`apps/web/e2e/00-stack-smoke.spec.ts`](../../../apps/web/e2e/00-stack-smoke.spec.ts#L34-L141) (`#3` `L34-70` `GET /api/v1/sources/inspect-lines`, `#4` `L72-141` `POST /api/v1/executions/reflexive` / `GET /api/v1/executions/{id}`)
  - Configuration E2E : [`infra/scripts/e2e/e2e_stack_config.py`](../../../infra/scripts/e2e/e2e_stack_config.py#L76) (`"ORCIA_ENV": "e2e"`)
  - Garde d'authentification :
    - [`apps/api/src/orcia_api/routers/sources_surgical.py`](../../../apps/api/src/orcia_api/routers/sources_surgical.py#L113) (`resolve_request_user`)
    - [`apps/api/src/orcia_api/routers/executions_trace.py`](../../../apps/api/src/orcia_api/routers/executions_trace.py#L90) (et `L190`, `L212` : `resolve_request_user`)
    - [`apps/api/src/orcia_api/routers/_auth_token_issuer.py`](../../../apps/api/src/orcia_api/routers/_auth_token_issuer.py#L29-L34)
    - [`packages/orcia-core/src/orcia_core/permissions/service.py`](../../../packages/orcia-core/src/orcia_core/permissions/service.py#L100-L109) et [`L197-L202`](../../../packages/orcia-core/src/orcia_core/permissions/service.py#L197-L202)

- **Mécanisme de panne** :
  - `00-stack-smoke.spec.ts` exécute `resetDay0()` dans `beforeEach` (`L8-10`), laissant `0` utilisateur en base, puis les tests `#3` et `#4` appellent directement `apiGet(request, ...)` / `apiPost(request, ...)` **sans `token` Bearer**.
  - Sous `ORCIA_ENV="e2e"`, `PERSONA_IMPERSONATION_ENVIRONMENTS = frozenset({"local", "test"})` interdit l'impersonation (`allow_persona_impersonation = False`), donc `resolve_user()` lève légitimement `AuthenticationRequiredError` (`HTTP 401`).

- **Arbitrage architectural** :
  - **Ne surtout pas** assouplir le backend (`ORCIA_ENV="e2e"` doit rester *fail-closed* identique à la production sur l'authentification).
  - **Correction E2E** : dans `00-stack-smoke.spec.ts` `#3` et `#4`, soit (a) **démontrer explicitement le rejet `401` anonyme** puis créer le premier admin (`createFirstAdminViaUi` ou helper partagé `createFirstAdminAndGetBearerToken`) et passer `{ token }` à `apiGet`/`apiPost`, soit (b) séparer un smoke anonyme (`/health`, rejet `401` sur `/api/v1/sources/inspect-lines` & `/api/v1/executions/reflexive`) des scénarios authentifiés `Story 16.1`/`16.2`.

---

### `ARCH23-03` (`P0`) — Oubli d'en-tête `Authorization: Bearer` dans les flux SSE `fetch` & Diagnostic trompeur sur `401` (`P0-UX-1`)

- **Localisation exacte** :
  - Bug actif `#7` : [`packages/api-client/src/domains/bootstrapAndOntology.ts`](../../../packages/api-client/src/domains/bootstrapAndOntology.ts#L358-L370) (`streamAssistantTurnSse`) vs [`apps/api/src/orcia_api/routers/assistant_workspace.py`](../../../apps/api/src/orcia_api/routers/assistant_workspace.py#L230-L245) (`user: CurrentUserDep`)
  - Transport de référence du SDK : [`packages/api-client/src/helpers.ts`](../../../packages/api-client/src/helpers.ts#L78-L130) (`createRequestJson` injecte `defaultAccessTokenProvider?.()`, `options.baseUrl`, `credentials: "include"`, `Accept-Language`, et lève `OrciaProblemError` RFC 9457)
  - **Bug frère latent (audit statique)** : [`apps/web/src/features/shared/useReflexiveExecutionController.ts`](../../../apps/web/src/features/shared/useReflexiveExecutionController.ts#L127-L131) appelle `fetch(streamUrl, ...)` en direct sans `Authorization: Bearer` sur `/api/v1/executions/{execution_id}/trace-stream` (protégé par `resolve_request_user` dans [`executions_trace.py`](../../../apps/api/src/orcia_api/routers/executions_trace.py#L212)) — ce bug cassera la spec `12-epic16` dès que `resetDay0()` sera débloqué !
  - **Gap sécurité symétrique** : [`apps/web/src/components/useWorkspaceEventsSse.ts`](../../../apps/web/src/components/useWorkspaceEventsSse.ts#L31-L32) utilise `new EventSource("/api/v1/events/stream?...")` (incapable d'envoyer un header `Authorization: Bearer`), tandis que [`apps/api/src/orcia_api/routers/inbox_and_leases.py`](../../../apps/api/src/orcia_api/routers/inbox_and_leases.py#L267-L286) n'appelle pas encore `resolve_request_user` ni `_enforce_inbox_workspace_guard`.
  - **Message d'erreur UX trompeur (`P0-UX-1`)** : [`apps/web/src/features/inbox/useAssistantStreamingTurn.ts`](../../../apps/web/src/features/inbox/useAssistantStreamingTurn.ts#L315-L328) :
    ```ts
    errorMessage: isFr
      ? `⚠️ Impossible d'obtenir une réponse de Mon Assistant (${detail}). Vérifiez que le modèle IA configuré est bien démarré.`
    ```

- **Mécanisme de panne (`#7`)** :
  - `configureActiveEmbeddingModelViaApi(page)` et `createFirstAdminViaUi(page)` authentifient correctement le navigateur (`authSessionStore.accessToken` enregistré via `registerDefaultAccessTokenProvider`).
  - Sur `/assistant`, les requêtes REST (`/folders`, `/overview` en `#8` et `#9`) passent par `createRequestJson` → en-tête `Authorization: Bearer ...` présent → `200 OK`.
  - Lors de l'envoi d'un message (`#7`), `streamAssistantTurnSse` court-circuite `createRequestJson` et appelle `globalThis.fetch("/api/v1/assistant/three-speed/stream", ...)` **sans `Authorization`**, provoquant un `HTTP 401` immédiat côté FastAPI (`resolve_request_user` ne lit que le header `Bearer`, jamais le cookie refresh `HttpOnly`), suivi du message erroné imputant la faute au modèle IA.

- **Contrat d'interface unifié recommandé (`AD-6` + RFC 9457)** :
  1. Factoriser une primitive unique `createRequestSse(options)` dans [`packages/api-client/src/helpers.ts`](../../../packages/api-client/src/helpers.ts) sur le modèle exact de `createRequestJson` (`options.baseUrl`, `options.fetchImpl`, `defaultAccessTokenProvider?.()`, `credentials: "include"`, `Accept-Language`, et sur `!response.ok` : parsing `application/problem+json` → `throw new OrciaProblemError(problem)` + rafraîchissement transparent sur `401` via refresh cookie si pertinent).
  2. Migrer `streamAssistantTurnSse` (`bootstrapAndOntology.ts`), le flux réflexif (`useReflexiveExecutionController.ts` → méthode SDK `streamReflexiveExecutionTraceSse`) et `useWorkspaceEventsSse.ts` sur ce transport `fetch + ReadableStream` authentifié, puis protéger `GET /api/v1/events/stream` par `resolve_request_user` + `_enforce_inbox_workspace_guard`.
  3. Dans `useAssistantStreamingTurn.ts:L315-328`, brancher sur `OrciaProblemError` (`err.problem.status` / `err.problem.error_code`) :
     - `401` / `403` → message métier session expirée/non autorisée (sans code HTTP brut) + action **`Se reconnecter →`** vers `/login` ;
     - `502` / `503` / `504` / timeout → message indisponibilité service IA + lien vers `Configuration › Modèles IA` (selon rôle).

---

### `ARCH23-04` (`P1`) — Zone 4 (`Aide Contextuelle`) désynchronisée et structure Markdown non rendue (`P1-UX-5`, `P2-UX-8`)

- **Localisation exacte** :
  - Écrasement des sections : [`apps/web/src/components/ShellContextualHelpColumn.tsx`](../../../apps/web/src/components/ShellContextualHelpColumn.tsx#L40-L89) (notamment `L71`: `sections: contextualHelpArticle.sections` et `L86-88`: `catch {}` silencieux)
  - Sections statiques mélangées : [`apps/web/src/components/contextualHelpCatalog.ts`](../../../apps/web/src/components/contextualHelpCatalog.ts#L99-L144) + [`apps/web/src/components/_contextualHelpSections.ts`](../../../apps/web/src/components/_contextualHelpSections.ts#L269-L301) (`GENERAL_SECTIONS_FR` injectant `"cockpit-decisions"` et `"assistant-modes"` sur **tous** les écrans hors `/configuration`)
  - Sources Markdown & parseur backend : [`docs/help/fr/assistant.md`](../../../docs/help/fr/assistant.md#L1-L32), [`docs/help/fr/cockpit.md`](../../../docs/help/fr/cockpit.md#L1-L32), [`packages/orcia-core/src/orcia_core/catalog/contextual_help_loader.py`](../../../packages/orcia-core/src/orcia_core/catalog/contextual_help_loader.py#L17-L32) et [`L75-L123`](../../../packages/orcia-core/src/orcia_core/catalog/contextual_help_loader.py#L75-L123)
  - Routeur : [`apps/api/src/orcia_api/routers/portal_and_help.py`](../../../apps/api/src/orcia_api/routers/portal_and_help.py#L121-L151)
  - Rendu & scroll : [`packages/ui/src/primitives/ContextualHelpColumnAndCenter.tsx`](../../../packages/ui/src/primitives/ContextualHelpColumnAndCenter.tsx#L175-L353) et [`FourZoneHelpAsideColumn.tsx`](../../../packages/ui/src/primitives/FourZoneHelpAsideColumn.tsx#L31-L32) (`maxHeight: "calc(100vh - 52px)"`)

- **Diagnostic exact des écarts observés par Sally** :
  1. **Fuite Cockpit ↔ Assistant** : même lorsque l'API `/api/v1/help/resolve?route=/assistant` répond avec le vrai guide `docs/help/fr/assistant.md` (`#8`, `#9`), `ShellContextualHelpColumn.tsx:L71` **ignore** le contenu structuré renvoyé et réinjecte `contextualHelpArticle.sections` (`GENERAL_SECTIONS_FR`), affichant la carte `ⓘ Décisions en attente et relectures ("Le Cockpit regroupe...")` sur `/assistant`, et `Les 3 modes de réponse de Mon Assistant` sur `/cockpit` (`#5`).
  2. **État initial optimiste & `catch {}` silencieux** : `ShellContextualHelpColumn.tsx:L40-48` initialise `resolvedLayers = ["BASE", "PACK", "WORKSPACE"]` et `rollbackAvailable = true` avant résolution, et son `catch {}` (`L86-88`) masque les erreurs réseau (expliquant la dérive `#7` `Mon Assistant @1.0.0` `BASE → PACK → WORKSPACE (core)` vs `#8` `Mon Assistant : questions, dossiers et citations vérifiées` `BASE (core)`).
  3. **Disparition des 4 blocs `DESIGN.md` (`EN N GESTES`, `UN EXEMPLE RÉEL`, `CE QUI COINCE SOUVENT`) et plomberie technique** :
     - Les fichiers `docs/help/fr/*.md` contiennent déjà exactement ces rubriques, mais `parse_declarative_help_markdown` (`contextual_help_loader.py:L21-27`) replie `## Un exemple réel` dans `key_terms_items` et `## Ce qui coince souvent` dans `faq_items`.
     - `ContextualHelpColumnAndCenter.tsx` affiche alors de simples accordéons génériques (avec `openFaq = false` par défaut en `L93`) et expose `@1.0.0` + `Sources du guide : BASE → PACK → WORKSPACE (core)` (`L178-197`) en tête de panneau.
  4. **Troncature basse sans repère de scroll** : `FourZoneHelpAsideColumn.tsx:L31` borne l'aside à `calc(100vh - 52px)` avec `overflowY: auto`, si bien que sur capture pleine page (`1303px`–`1362px`) comme à `900px`, le contenu déborde et est coupé net sans indicateur visuel.

- **Arbitrage & contrat cible** :
  - Supprimer `GENERAL_SECTIONS_FR/EN` en fourre-tout global : découper les sections par route (`SECTIONS_BY_ROUTE` ou `sections` retournées directement par l'article résolu via `/api/v1/help/resolve`).
  - Étendre le contrat DTO `HelpArticleSchemaItem` (ou parser explicitement `real_example_text` / `common_pitfalls_items` dans `contextual_help_loader.py`) pour rendre nativement les blocs `À quoi sert cet écran`, `En N gestes`, l'encadré ambre `Un exemple réel`, et `Ce qui coince souvent`, tout en masquant `@version` / `Sources du guide : BASE...` derrière un tiroir « Détails techniques » réservé aux admins.

---

### `ARCH23-05` (`P1`) — Modèle d'Accostage scindé (`X/5` vs `6` jalons), État fantôme Jour 0 & Modale Premier Admin (`P1-UX-4`, `P1-UX-6`, `P1-UX-7`)

- **Localisation exacte** :
  - Split-brain Accostage (`6` backend vs `5` frontend) :
    - Backend : [`packages/orcia-core/src/orcia_core/bootstrap/progressive_accostage.py`](../../../packages/orcia-core/src/orcia_core/bootstrap/progressive_accostage.py#L54-L97) (`ACCOSTAGE_SIX_MILESTONES`, 6 jalons) et [`L146`](../../../packages/orcia-core/src/orcia_core/bootstrap/progressive_accostage.py#L146) (`self._completed_keys = {"first-admin"}` pré-rempli en dur dans `__init__`!)
    - Frontend Store : [`apps/web/src/components/platformSetupStore.tsx`](../../../apps/web/src/components/platformSetupStore.tsx#L451-L466) (`completedSetupStepsCount` recalcule `/5` sans compter `adminCreated`) et [`platformSetupHydration.ts`](../../../apps/web/src/components/platformSetupHydration.ts#L145-L152) (`accostageCounts`)
    - Cockpit : [`apps/web/src/features/cockpit/index.tsx`](../../../apps/web/src/features/cockpit/index.tsx#L100-L140) (`milestones` démarre à `"1. Modèles IA"` dans le bloc `"Étape 3"`) et [`L181-L243`](../../../apps/web/src/features/cockpit/index.tsx#L181-L243) (badge `Accostage 0/5` dupliqué avec celui interne de [`ProgressiveDay0AccostageBanner.tsx`](../../../packages/ui/src/primitives/ProgressiveDay0AccostageBanner.tsx))
  - Fantômes Jour 0 pré-admin (`0` utilisateur en base) :
    - Profil fantôme `AP` : [`apps/web/src/components/ShellContainer.tsx`](../../../apps/web/src/components/ShellContainer.tsx#L119-L125) retombe sur [`DEFAULT_HUMAN_PROFILE`](../../../apps/web/src/components/shellPresets.ts#L26-L32) (`"Administrateur de la plateforme"`, `"PLATFORM_ADMIN"`) quand `platformAdmin === null` !
    - `Configuration` masquée (`7` entrées vs `8`) + désactivation asymétrique : [`ShellContainer.tsx`](../../../apps/web/src/components/ShellContainer.tsx#L263-L264) (`hiddenMenuKeys` masque `"configuration"`) et [`buildShellDisabledMenuKeys`](../../../apps/web/src/components/shellScopeOptions.ts#L189-L221) (ne désactive pas `spaces` quand `platformAdmin === null`).
    - `Notifications 4` dès le Jour 0 : [`buildShellNotificationItems`](../../../apps/web/src/components/shellScopeOptions.ts#L252-L336) émet 4 notifications synthétiques `SETUP_PREREQUISITE` même lorsque `platformAdmin === null` (`llmTiers`, `hasBillingTeam`, `orgUnits`, `workspaces`). De plus, `platformSetupHydration.ts:L191` lit `llmTiers` uniquement depuis `platform_setup_state`, ignorant `workspace_llm_tier_mappings` (`modelsCount > 0` dans `accostageCounts`!).
  - Modale Jour 0 (`P1-UX-4`) :
    - [`apps/web/src/components/FirstBootAdminSetupModal.tsx`](../../../apps/web/src/components/FirstBootAdminSetupModal.tsx#L105) passe `closeLabel={`${rgaaLabels.cancelCta} (Esc)`}` à [`OrciaDialog`](../../../packages/ui/src/primitives/RadixDesignSystemPrimitives.tsx#L125-L131) ET rend un deuxième bouton `first-boot-admin-cancel-btn` (`Annuler (Esc)`) en [`L221-L228`](../../../apps/web/src/components/FirstBootAdminSetupModal.tsx#L221-L228).
    - [`L193`](../../../apps/web/src/components/FirstBootAdminSetupModal.tsx#L193) définit `placeholder="••••••••••••"` sur un `<input type="text">` masqué par `WebkitTextSecurity: "disc"` (`L199`), créant l'illusion d'un mot de passe pré-rempli.
    - [`L233-L244`](../../../apps/web/src/components/FirstBootAdminSetupModal.tsx#L233-L244) applique `disabled={!canCreateAdmin}` sans distinction visuelle suffisante par rapport aux boutons secondaires.
  - Props mortes résiduelles Epic 21 → Epic 22 : [`ShellContainer.tsx`](../../../apps/web/src/components/ShellContainer.tsx#L202-L204) et [`L278-L287`](../../../apps/web/src/components/ShellContainer.tsx#L278-L287) passent encore `showOrganizationMenu`, `organizationMenuActive`, `activityMenuActive`, `onSelectOrganizationMenu`, `onSelectActivityMenu`, ignorées par `FourZoneDirectionCShell.tsx`.

- **Arbitrage architectural** :
  - **Source de vérité unique `Accostage` (`6` jalons ou `5` post-admin, mais cohérents Bout-en-Bout)** : aligner `progressive_accostage.py` (retirer le hardcode `{"first-admin"}` à `L146` ; le calculer depuis `COUNT(*) FROM users > 0`), `platformSetupStore.tsx` et `cockpit/index.tsx` sur une unique structure de jalons non redondante (`1. Compte Admin`, `2. Premier Modèle IA`, `3. Organisation`, `4. Premier Espace`, `5. Première Source`, `6. Premier Processus` → `X/6`, comme spécifié dans `DESIGN.md`), avec un seul badge `Accostage X/6` en en-tête de carte.
  - **Isolation d'état pré-admin (`platformAdmin === null`)** : ne rendre ni identité `AP`, ni `Notifications 4` dans `ShellContainer` tant que `platformAdmin === null` (0 utilisateur en PG18), et afficher les 8 entrées de menu verrouillées de façon homogène ou un shell Jour 0 dédié sous la modale non-fermable (supprimer les 2 boutons `Annuler (Esc)` sur la modale obligatoire de Jour 0, remplacer `••••••••••••` par un placeholder vide ou texte clair + bouton œil afficher/masquer).

---

### `ARCH23-06` (`P1`) — Surcharge du Cockpit (`6`–`7` blocs visuels vs règle `<= 3` max de `DESIGN.md`) (`P1-UX-3`)

- **Localisation exacte** :
  - [`apps/web/src/features/cockpit/index.tsx`](../../../apps/web/src/features/cockpit/index.tsx#L186-L293)
  - [`packages/ui/src/primitives/StreamlinedCockpitView.tsx`](../../../packages/ui/src/primitives/StreamlinedCockpitView.tsx#L150-L258)
  - [`apps/web/src/features/cockpit/CockpitRunsSection.tsx`](../../../apps/web/src/features/cockpit/CockpitRunsSection.tsx#L41-L235)
  - [`apps/web/src/features/cockpit/CockpitHumanLedGovernanceSection.tsx`](../../../apps/web/src/features/cockpit/CockpitHumanLedGovernanceSection.tsx#L233-L383)

- **Mécanisme de dérive** :
  - Bien que `cockpit/index.tsx` regroupe le DOM sous `2–3` balises `<section>`, visuellement **6 à 7 cartes empilées** s'affichent (`1303px`–`1362px` de hauteur sur `#5` et `#10`) : (1) bannière `Accostage` 3 colonnes, (2) bandeau `Aucune décision en attente`, (3) carte `Accès rapide à Mon Assistant`, (4) grille de 3 tuiles d'orientation, (5) `CockpitRunsSection` (état vide sans espace ou formulaire d'exécution rapide sans titre tout en bas en `#10`), (6) `CockpitHumanLedGovernanceSection` monté en permanence sous la ligne de flottaison `900px`.
- **Décision d'architecture UI** :
  - Ramener `/cockpit` à **3 blocs visuels distincts stricts** (`<= 3` Loi de Hick) :
    1. **Bloc 1 — Accostage** (masqué une fois terminé `6/6`, ou repliable) ;
    2. **Bloc 2 — File des décisions humaines** (`StreamlinedCockpitView` : bandeau calme si 0 décision, ou liste des décisions réelles + ouverture ciblée de `HumanLedAnchorCard` / `ArbitrationTieBreakCard` **uniquement lorsqu'une exécution attend une action** — ne plus monter `CockpitHumanLedGovernanceSection` en permanence à vide) ;
    3. **Bloc 3 — Lancement & accès rapides consolidés** (unifiant la barre d'accès assistant / processus / espace sans dupliquer 3 chemins vers `Mon Assistant`).

---

### `ARCH23-07` (`P2`) — Redondance `TopHeaderBar`, troncatures à `1440px`, emplacement du logo `ORCIA` et écran de chargement (`P2-UX-9`, `P2-UX-10`)

- **Localisation exacte** :
  - [`packages/ui/src/primitives/FourZoneTopHeaderSection.tsx`](../../../packages/ui/src/primitives/FourZoneTopHeaderSection.tsx#L85-L153) (`ORCIA` à `L85`, breadcrumb à `L87-126`, `topbar-fixed-workspace-selector` `max-w-[240px]` à `L128-153`)
  - [`apps/web/src/components/shellPresets.ts`](../../../apps/web/src/components/shellPresets.ts#L178-L200) (`buildShellBreadcrumbItems` n'inclut pas `Équipe / Direction`)
  - [`apps/web/src/components/ShellContainer.tsx`](../../../apps/web/src/components/ShellContainer.tsx#L180-L182) (`ShellHydratingLoaderView` en `#1`)

- **Constat & arbitrage** :
  - Maintenir à la fois le **Double Sélecteur** dans `Zone 1` (`FourZoneSidebarRail.tsx:L112-173`) **et** le bouton `topbar-fixed-workspace-selector` dans `Zone 2` (`FourZoneTopHeaderSection.tsx:L128-153`) vole `240px` à la `TopHeaderBar` à `1440px`, tronquant à la fois `Espace : Plateforme Globale O...` et le placeholder `Rechercher dans cet Espace ou partout (... ⌘K` (`#2`–`#10`).
  - **Décision** : supprimer `topbar-fixed-workspace-selector` de `Zone 2` (sauf sur mobile `< 768px` où la Sidebar est repliée) ou le convertir en badge passif compact, déplacer le logo `ORCIA` en tête de `Zone 1` (`DESIGN.md` §2.1), inclure l'unité/espace dans `buildShellBreadcrumbItems` (`ORCIA > [Équipe] > Cockpit`), raccourcir le placeholder de recherche à `Rechercher… (⌘K)`, et doter `ShellHydratingLoaderView` (`#1`) d'un logo ORCIA + indicateur de progression sobre.

---

### `ARCH23-08` (`P2`) — Redondance d'en-tête sur `/assistant`, compteurs `(0)` et jargon technique (`P2-UX-8`)

- **Localisation exacte** :
  - [`apps/web/src/components/ModuleWorkspaceView.tsx`](../../../apps/web/src/components/ModuleWorkspaceView.tsx#L60-L101) (masque la carte d'en-tête pour `cockpit`, `catalog`, `finops`, mais **pas** pour `inbox`/`assistant`)
  - [`apps/web/src/features/inbox/SavedConversationsAndThreadView.tsx`](../../../apps/web/src/features/inbox/SavedConversationsAndThreadView.tsx#L44-L100) (`Conversations sauvegardées (0)`, `Dossiers (0)`, mélange `orcia-ds-btn` + classes Tailwind brutes)
  - [`packages/ui/src/primitives/AssistantSpeedSelectorAndStreamView.tsx`](../../../packages/ui/src/primitives/AssistantSpeedSelectorAndStreamView.tsx#L257-L259) (`assistant-welcome-hero-title`)
  - [`apps/web/src/features/inbox/index.tsx`](../../../apps/web/src/features/inbox/index.tsx#L90-L96) (`AssistantNoEmbeddingBanner`)

- **Constat & arbitrage** :
  - Exclure `inbox` (mode `assistant`) de la carte d'en-tête redondante de `ModuleWorkspaceView.tsx:L60-62` (en déplaçant l'icône `ⓘ` dans `AssistantTopToolbar`), masquer les compteurs `(0)` quand vides (ou afficher un badge discret uniquement quand `> 0`), uniformiser les boutons de `AssistantTopToolbar` sur les classes `@orcia/ui` (`orcia-ds-btn`), et remplacer `"embedding"` par `"indexation sémantique"` dans les dictionnaires i18n `fr.ts`.

---

### `ARCH23-09` (`P3`) — Traçabilité visuelle de preuve dans `03-human-led-anchor-and-arbitration.spec.ts` (`P3-UX-12`)

- **Localisation exacte** : [`apps/web/e2e/03-human-led-anchor-and-arbitration.spec.ts`](../../../apps/web/e2e/03-human-led-anchor-and-arbitration.spec.ts#L39-L149)
- **Constat** : Le test `#10` revient sur `/cockpit` et achève la résolution avant la capture `afterEach`, si bien que le PNG final ne montre ni la carte violette `#6D28D9` (`HumanLedAnchorCard`) ni `ArbitrationTieBreakCard`. En Epic 23, sauvegarder une capture intermédiaire `testInfo.attach(...)` lors de l'étape d'ancrage violet et d'arbitrage permettra à Sally d'auditer ces composants identitaires sans ralentir la suite.

---

### `ARCH23-10` (`P0`) — `87` scénarios masqués (`0 / 55` Mobile Companion & `04`–`21` non prouvés en Epic 22) (`P0-UX-2`)

- **Localisation exacte** : `20` specs complètes bloquées dès `beforeEach` (`04-multi-actor-claim-sse.spec.ts` à `21-assistant-citations-v5-audit-help-showcase.spec.ts`, plus `shell.spec.ts`) et **l'intégralité du projet `mobile-companion`** (`44` échecs `beforeEach` + `11` skips sur `00`..`21` et `shell`).
- **Impact architectural** :
  - **Couverture réelle prouvée en Epic 22** : uniquement `users`, `assistant_folders`, `human_anchor_signatures`, `step_executions`, `blackboard_snapshots` sur `desktop-cockpit` (`#1`–`#10`).
  - **Surfaces critiques non encore prouvées sous `ORCIA_ENV=e2e` sans `ORCIA_E2E_SEED_FIXTURES`** :
    1. **Mobile Companion (`390×844`)** : barre basse à 3 onglets (`mobile-bottom-tab-bar`), bannière desktop-only sur `/configuration`, zéro overflow sur `/assistant`, `/spaces`, `/processes`, `/finops` (`05`, `12`, `13`, `14`, `shell`).
    2. **Flux temps réel & RBAC multi-acteurs** : SSE `/api/v1/events/stream` (`04`), `/api/v1/executions/{id}/trace-stream` (`12-epic16`, exposé à `ARCH23-03`), isolation SecOps / mode `READ_ONLY_OBSERVER` (`15`), Garde-fou SSRF & Permission Broker (`16`), Chaîne ADN Starlark / Ontologie (`17`), Catalogue / Wizards (`18`), Gates orthogonales / `ChunkedValidationCard` (`19`), Studio V2 / Autonomie (`20`), Citations v5 / Centre d'aide / `/showcase` (`21`).

---

## 3. Dialogue croisé UX ↔ Architecture (Sally ↔ Winston)

Le croisement entre le rapport visuel de Sally ([`notes-audit-sally-ux.md`](./notes-audit-sally-ux.md)) et l'inspection code montre d'abord une **divergence positive** par rapport à l'Epic 21 (sur Desktop `a1bb059`, les `8` menus non numérotés, le Double Sélecteur empilé, le Breadcrumb et la coche verte Étape 1 sont bien rendus), tout en confirmant **12 points d'alignement** dont la source est purement architecturale :

| ID Sally (`notes-audit-sally-ux.md`) | Diagnostic architectural Winston | Contrat / Arbitrage conjoint UX ↔ Tech |
| --- | --- | --- |
| **`P0-UX-1`** (Message `401` accusant le modèle IA + code HTTP brut + impasse) | **`ARCH23-03`** (`streamAssistantTurnSse` sans `Bearer`, `useAssistantStreamingTurn.ts:L324-326`) | 1) Migrer tout SSE sur `createRequestSse` (`Bearer` + `OrciaProblemError`) ; 2) Mapper `401/403` vers un bandeau `role="alert"` *« Session expirée »* avec CTA **`Se reconnecter →`**. |
| **`P0-UX-2`** (Angle mort total Mobile `0/55` & écrans `04`–`21`) | **`ARCH23-01`** (`resetDay0()` bloqué sur FK `ON DELETE RESTRICT`) + **`ARCH23-10`** | Débloquer `reset_day0.py` (`TRUNCATE ... RESTART IDENTITY CASCADE` en E2E isolé + `FLUSHDB` Redis) **en Vague 0** avant toute campagne UX. |
| **`P1-UX-3`** (Cockpit `6`–`7` blocs > `3` max, formulaire anonyme en `#10`) | **`ARCH23-06`** (`cockpit/index.tsx` + `StreamlinedCockpitView` + `CockpitRunsSection` + `CockpitHumanLedGovernanceSection`) | Limiter strictement à 3 blocs visuels : `1. Accostage`, `2. Décisions` (sans monter `CockpitHumanLedGovernanceSection` à vide), `3. Lancement & accès rapides fusionnés`. |
| **`P1-UX-4`** (Modale Jour 0 : double `Annuler (Esc)`, CTA faible, `••••••••••••••`) | **`ARCH23-05`** (`FirstBootAdminSetupModal.tsx:L105,L193,L221-244` + `OrciaDialog`) | Modale Jour 0 obligatoire **sans bouton Annuler/Esc** (uniquement croix accessible si `isDirty` ou aucune fermeture tant que 0 admin), placeholder clair sans points noirs, bouton œil + CTA `#2563EB` franc. |
| **`P1-UX-5`** (Zone 4 : fuite Cockpit ↔ Assistant, coupe en bas, 4 blocs `DESIGN.md` absents) | **`ARCH23-04`** (`ShellContextualHelpColumn.tsx:L71` écrase par `GENERAL_SECTIONS_FR`, `FourZoneHelpAsideColumn.tsx:L31`) | Supprimer l'écrasement `L71` ; servir les sections par route depuis `/api/v1/help/resolve` ; mapper `Un exemple réel` (encadré ambre) et `Ce qui coince souvent` en composants dédiés. |
| **`P1-UX-6`** (`Accostage 0/5` dupliqué et ignorant Étape 1, `1. Modèles IA` répété) | **`ARCH23-05`** (split-brain `ACCOSTAGE_SIX_MILESTONES` vs `/5` frontend + `self._completed_keys = {"first-admin"}`) | Source de vérité unique `X/6` calculée depuis PG18 (`users > 0` inclus), badge unique, libellés non tronqués. |
| **`P1-UX-7`** (Jour 0 pré-admin : profil fantôme `AP`, `Notifications 4`, `7` menus, `Mes Espaces` actif) | **`ARCH23-05`** (`DEFAULT_HUMAN_PROFILE` fallback `ShellContainer.tsx:L121`, `buildShellNotificationItems`, `hiddenMenuKeys`) | Ne rendre ni avatar `AP` ni notifications prérequis tant que `platformAdmin === null` ; verrouiller uniformément la navigation sous la modale Jour 0. |
| **`P2-UX-8`** (Jargon `embedding`, `BASE → PACK → WORKSPACE`, `@1.0.0`, `(Esc)`) | **`ARCH23-04`**, **`ARCH23-08`** (`ContextualHelpColumnAndCenter.tsx:L178-197`, `fr.ts`) | Remplacer `embedding` par `indexation sémantique`, `(Esc)` par `(Échap)`, masquer `@version` / `BASE → PACK → WORKSPACE` dans un accordéon technique admin-only. |
| **`P2-UX-9`** (Troncatures `TopHeaderBar` `1440px` : `Espace : Plateforme Globale O...`, `partout (... ⌘K`) | **`ARCH23-07`** (`topbar-fixed-workspace-selector` redondant dans `FourZoneTopHeaderSection.tsx:L128-153`) | Retirer le sélecteur d'espace dupliqué du header Desktop (le Double Sélecteur Zone 1 fait foi) et raccourcir le placeholder à `Rechercher… (⌘K)`. |
| **`P2-UX-10`** (Logo `ORCIA` dans Zone 2 vs Zone 1, Breadcrumb sans Équipe, `/login` & loader nu) | **`ARCH23-07`** (`FourZoneTopHeaderSection.tsx:L85`, `shellPresets.ts:L178-200`, `ShellHydratingLoaderView`) | Placer le logo `ORCIA` en tête de Zone 1 (`DESIGN.md` §2.1), enrichir le breadcrumb avec l'unité active, styler loader + `/login` avec marque ORCIA et bouton œil mot de passe. |
| **`P2-UX-11`** (Contrastes WCAG AA : états désactivés, alerte ambre, bouton `➤`) | **`ARCH23-08`** + tokens CSS (`packages/ui/src/styles/tokens.css`) | Auditer les ratios `>= 4,5:1` de `--color-state-warning` / texte ambre et des menus/boutons désactivés après passage sur tokens unifiés. |
| **`P3-UX-12`** (Preuve visuelle de `HumanLedAnchorCard` / `ArbitrationTieBreakCard` dans `#10`) | **`ARCH23-09`** (`03-human-led-anchor-and-arbitration.spec.ts`) | Attacher des captures Playwright intermédiaires aux jalons violet (`#6D28D9`) et arbitrage avant retour `/cockpit`. |

---

## 4. Plan d'ordonnancement topologique recommandé pour l'Epic 23

L'exécution de l'Epic 23 doit impérativement suivre **3 vagues strictement séquentielles** (ne pas passer à une campagne complète tant que la Vague 0 n'est pas verte, sinon les régressions restent masquées) :

### Vague 0 — Déblocage critique de la vérité PostgreSQL 18 & Authentification SSE (`P0`)
1. **Story 23.1 (`ARCH23-01`) — Reset Day-0 E2E compatible `ON DELETE RESTRICT` + append-only + Redis** :
   - Protéger `connector_schemes` dans `09_reset_db_first_boot.py` (conserver le script de maintenance strictement sûr hors E2E).
   - Dans `infra/scripts/e2e/reset_day0.py` (strictement gardé par `is_isolated_e2e_database_url` — `orcia_e2e` uniquement), exécuter `TRUNCATE TABLE ... RESTART IDENTITY CASCADE` sur les tables applicatives + append-only (`blackboard_snapshots`, `audit_ledger`, `step_executions`, `workflow_runs`, etc.) **hors** `alembic_version` et `connector_schemes`, réinitialiser `platform_auth_settings` (nouveau `boot_epoch`), nettoyer `dbos` si applicable, et exécuter `FLUSHDB` sur Redis (`state["redis_url"]`).
   - Ajouter un test d'intégration `testcontainers` PG18 dédiant la séquence : *insertion `step_executions` + `blackboard_snapshots` + `audit_ledger` → `reset_day0` → re-vérification `COUNT(*) == 0` sur `users`, `step_executions`, `blackboard_snapshots` et `COUNT(*) == 1` sur `connector_schemes`*.
2. **Story 23.2 (`ARCH23-02`, `ARCH23-03`) — Authentification SSE unifiée (`createRequestSse`) & alignement Smoke `00`** :
   - Introduire `createRequestSse` dans `packages/api-client/src/helpers.ts` (`Bearer` + `credentials: "include"` + `OrciaProblemError` + `Accept-Language`).
   - Basculer `streamAssistantTurnSse` (`bootstrapAndOntology.ts`), `useReflexiveExecutionController.ts` (`/trace-stream`) et `useWorkspaceEventsSse.ts` (`/api/v1/events/stream`) sur `createRequestSse` ; verrouiller `GET /api/v1/events/stream` par `resolve_request_user` + `_enforce_inbox_workspace_guard`.
   - Dans `useAssistantStreamingTurn.ts`, distinguer `401/403` (*session expirée* + CTA `Se reconnecter →`) des erreurs fournisseur IA (`502/503/504`).
   - Mettre à jour `00-stack-smoke.spec.ts` `#3` et `#4` pour vérifier le rejet anonyme `401` puis s'authentifier via premier admin avant les appels Story `16.1`/`16.2`.

### Vague 1 — Remédiation UX & Contrats Direction C (`P1` / `P2`)
3. **Story 23.3 (`ARCH23-04`) — Zone 4 Aide Contextuelle 100 % fidèle à la route & `DESIGN.md`** :
   - Supprimer `GENERAL_SECTIONS_FR/EN` et l'écrasement `ShellContextualHelpColumn.tsx:L71` ; rendre les sections du guide réel de la route active (`/assistant` ≠ `/cockpit`), restaurer `EN N GESTES`, `UN EXEMPLE RÉEL` (ambre), `CE QUI COINCE SOUVENT`, masquer la plomberie `@version` / `BASE → PACK` aux non-admins, et rendre le scroll visible.
4. **Story 23.4 (`ARCH23-05`) — Unification Accostage `X/6`, suppression des fantômes Jour 0 & Modale Premier Admin** :
   - Unifier `progressive_accostage.py` + `platformSetupStore.tsx` + `cockpit/index.tsx` sur la source de vérité PG18 `X/6` (sans hardcode `{"first-admin"}`), supprimer le profil fantôme `AP` et `Notifications 4` avant création d'admin, nettoyer les props mortes `ShellContainer.tsx`, corriger `FirstBootAdminSetupModal.tsx` (zéro double `Annuler (Esc)`, placeholder clair + bouton œil, hiérarchie CTA `#2563EB`).
5. **Story 23.5 (`ARCH23-06`, `ARCH23-07`, `ARCH23-08`, `ARCH23-09`) — Sobriété Cockpit (`<= 3` blocs), TopHeaderBar & `/assistant`** :
   - Réduire `/cockpit` à 3 blocs visuels stricts (ne monter `CockpitHumanLedGovernanceSection` qu'en présence d'un run en attente / déclenchement explicite), retirer `topbar-fixed-workspace-selector` dupliqué sur Desktop, placer le logo `ORCIA` en Zone 1, polir `/assistant` (suppression en-tête redondant `ModuleWorkspaceView` + compteurs `(0)` + jargon `embedding`), et ajouter les captures intermédiaires d'étape dans `03-human-led-anchor-and-arbitration.spec.ts`.

### Vague 2 — Preuve intégrale `110 / 110` Desktop + Mobile Companion (`ARCH23-10`)
6. **Story 23.6 — Campagne Playwright E2E intégrale Epic 23 (`00`..`21` + `shell`, Desktop + Mobile `390×844`)** :
   - Exécuter l'ensemble des `110` scénarios sans `ORCIA_E2E_SEED_FIXTURES` ni mock PG/Redis (`--retries=0`), avec objectif **`97 / 97` exécutés PASS (`0` échec, `13` skips viewport attendus)** et audit visuel complet par Sally de toutes les surfaces jusque-là masquées (`mobile-companion` `05`/`12`/`13`/`14`/`shell` et écrans métiers `04`–`21`), avant de réévaluer les statuts `capabilities.yaml`.
