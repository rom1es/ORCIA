# Story 23.2 — Transport SSE Authentifié Unifié (`createRequestSse`), Alignement `00-stack-smoke` (#3/#4) & Diagnostic `401` Session Expirée (`P0-UX-1`)

- **Date** : 2026-11-19
- **Story / Clé Sprint** : `23-2-transport-sse-authentifie-createrequestsse-smoke-00-et-diagnostic-401` (`Epic 23` — Vague 0 `P0`)
- **Capacité(s)** : `CAP-004`, `CAP-040`, `CAP-071`, `CAP-074`, `CAP-075`, `CAP-160` — classification : `feature` + `ux` + `hygiène` (`REM23-02`, `REM23-03`, `REM23-04` / `ARCH23-02`, `ARCH23-03`, `P0-UX-1`, `P2-UX-11`)
- **Auteur / Contexte** : `22.10-impl` (Winston × Sally — pré-implémentation Epic 23). Corrige les **`3` échecs directs `HTTP 401`** mesurés avant la cascade `resetDay0()` (`00-stack-smoke` #3/#4, `02-assistant` #7), élimine les deux failles sœurs sur `/trace-stream` (`12-epic16`) et `/events/stream` (`04-multi-actor`), et remplace l'erreur trompeuse accusant le modèle IA sur `HTTP 401` par un bandeau critique actionnable (`Se reconnecter →`).
- **Commits associés** : `En attente d'implémentation (initialisé par Story 22.10)`

---

## 1. Analyse du Besoin & Étude d'Impact Tech Lead (Pré-Implémentation)

### 1.1 Contexte & Problématique
- **Preuves E2E & Captures (`e2e-campaign-epic-22`)** :
  1. **`00-stack-smoke.spec.ts` #3 & #4 (`REM23-02` / `ARCH23-02`)** : sous `ORCIA_ENV="e2e"` (`e2e_stack_config.py#L76`), `PERSONA_IMPERSONATION_ENVIRONMENTS` interdit l'impersonation ; les requêtes directes `apiGet(request, "/api/v1/sources/inspect-lines...")` (`L34-L70`) et `apiPost(request, "/api/v1/executions/reflexive")` (`L72-L141`) lancées juste après `resetDay0()` (`0` utilisateur, aucun `token` Bearer) reçoivent légitimement **`HTTP 401`** au lieu de `200`.
     - Captures : [`#3 failed.png`](../e2e-campaign-epic-22/screenshots/00-stack-smoke/desktop-cockpit--story-16-1-l-inspection-chirurgicale-l1-40-retourne-40-lignes-badge-y-et-bloque-en-rfc-9--failed.png), [`#4 failed.png`](../e2e-campaign-epic-22/screenshots/00-stack-smoke/desktop-cockpit--story-16-2-moteur-reflexif-asyncio-survie-f5-waiting-write-preview-approbation-writeprev--failed.png).
  2. **`02-assistant-streaming-and-folders.spec.ts` #7 (`REM23-03` / `ARCH23-03`)** : alors que `#8` et `#9` (REST via `createRequestJson`) réussissent avec `Authorization: Bearer`, `streamAssistantTurnSse` (`packages/api-client/src/domains/bootstrapAndOntology.ts#L358-L370`) appelle `fetch` directement sans `defaultAccessTokenProvider?.()`, déclenchant **`HTTP 401`** sur `POST /api/v1/assistant/three-speed/stream` (`assistant_workspace.py#L230-L245`, `CurrentUserDep`).
     - Bug frère identifié en audit statique : `apps/web/src/features/shared/useReflexiveExecutionController.ts#L127-L131` appelle également `fetch(streamUrl)` sans `Bearer` sur `GET /api/v1/executions/{execution_id}/trace-stream` (`executions_trace.py#L212`, `resolve_request_user`).
     - Faille symétrique : `apps/web/src/components/useWorkspaceEventsSse.ts#L31-L32` (`79` L) utilise `new EventSource("/api/v1/events/stream?...")` (sans en-tête `Bearer`) vers `apps/api/src/orcia_api/routers/inbox_and_leases.py#L267-L286` qui omet `resolve_request_user` et `_enforce_inbox_workspace_guard`.
  3. **Diagnostic UX critique (`REM23-04` / `P0-UX-1`, `P2-UX-11`)** : sur `HTTP 401` dans `#7`, `useAssistantStreamingTurn.ts#L315-L328` affiche dans un bandeau ambre :
     `⚠ Impossible d'obtenir une réponse de Mon Assistant (HTTP 401 Unauthorized). Vérifiez que le modèle IA configuré est bien démarré.`
     — accusant à tort le fournisseur IA, exposant un code HTTP brut, n'offrant aucun bouton `Se reconnecter →`, et présentant un contraste ambre faible ([`#7 failed.png`](../e2e-campaign-epic-22/screenshots/02-assistant-streaming-and-folders/desktop-cockpit--un-tour-d-assistant-traverse-le-navigateur-l-api-et-la-cassette-llm-0-et-affiche-une-rep--failed.png)).

### 1.2 Exploration, Analyse d'Impact GitNexus, Factorisation & Dette Technique
- **Analyse d'Impact GitNexus (`repo: "/home/romain/Documents/Projects/ORCIA"`)** :
  - `useAssistantStreamingTurn` (`apps/web/src/features/inbox/useAssistantStreamingTurn.ts`) : `impactedCount: 549`, `risk: "CRITICAL"`, `epistemic: "exact"`, `direct: 340`, `d=2: 163`, `d=3: 46`, `processes_affected: 175`, `modules_affected: 20`.
  - `resolve_request_user` (`apps/api/src/orcia_api/dependencies.py` / auth helpers) : `impactedCount: 127`, `risk: "CRITICAL"`, `epistemic: "exact"`, `direct: 87`, `d=2: 33`, `d=3: 7`, `processes_affected: 138`, `modules_affected: 18`.
  - `streamAssistantTurnSse`, `createRequestJson`, `useReflexiveExecutionController`, `useWorkspaceEventsSse` : impactés par la dérive d'index GitNexus (`commitsBehind: 2`, nœuds fichier / pointeurs `0` callers `UNKNOWN`) ; traçage complet réalisé par inspection directe (`read_file`) des call sites dans `packages/api-client/src/helpers.ts`, `bootstrapAndOntology.ts`, `useReflexiveExecutionController.ts`, `useWorkspaceEventsSse.ts` et `inbox_and_leases.py`.
- **Factorisation DRY & Contrôle de Volumétrie (`> 300–400` L)** :
  - **Découpage obligatoire de `packages/api-client/src/domains/bootstrapAndOntology.ts` (`472` lignes > `400` L)** : extraire le domaine SSE / streaming de l'assistant dans `packages/api-client/src/domains/assistantStreaming.ts` (`< 200` L) et réexporter depuis `domains/index.ts` sans casser la surface publique de `@orcia/api-client`.
  - **Factorisation unique `createRequestSse(options)` dans `packages/api-client/src/helpers.ts`** : reproduire exactement la mécanique de `createRequestJson` (`L78-L130` : injection `defaultAccessTokenProvider?.()`, `options.baseUrl`, `credentials: "include"`, `Accept-Language`, rafraîchissement *single-flight* sur `401` si un `refresh` cookie existe, parsing `application/problem+json` → `OrciaProblemError`).

---

## 2. Plan d'Implémentation

### 2.1 Schéma de Données & Migrations Alembic (`infra/migrations/versions/`)
- Aucune migration PostgreSQL 18 requise en Story 23.2.

### 2.2 Noyau Métier, Garde-fous Auth & SSE (`packages/orcia-core/`)
- Conserver `ORCIA_ENV="e2e"` strictement *fail-closed* dans `packages/orcia-core/src/orcia_core/permissions/service.py#L100-L109,L197-L202` (`PERSONA_IMPERSONATION_ENVIRONMENTS = frozenset({"local", "test"})`) — **aucun** assouplissement ni contournement de sécurité.

### 2.3 Couche Backend API, Sécurité & Contrats (`apps/api/`, `packages/api-client/`)
1. **`apps/api/src/orcia_api/routers/inbox_and_leases.py#L267-L295` (`GET /api/v1/events/stream`)** :
   - Protéger l'endpoint SSE par `resolve_request_user` et `_enforce_inbox_workspace_guard` (rejet `HTTP 401` en l'absence de jeton Bearer valide sous `ORCIA_ENV="e2e"` / prod, et vérification d'appartenance au workspace ciblé `403` si hors périmètre).
   - Vérifier la réactivité `< 500 ms` des événements SSE publiés après mutation / claim.
2. **`packages/api-client/src/helpers.ts` (`createRequestSse`)** :
   - Créer `createRequestSse(options)` (`method`, `path`, `body`, `headers`, `signal`, `token`) injectant `Authorization: Bearer ...` via `defaultAccessTokenProvider?.()` (ou `options.token`), `credentials: "include"`, `Accept: "text/event-stream"`, `Accept-Language`.
   - Sur `!response.ok`, parser l'enveloppe RFC 9457 (`application/problem+json`) en `OrciaProblemError` (avec tentative unique de refresh session sur `401` cohérente avec `createRequestJson`), sans jamais masquer les erreurs derrière un `catch` silencieux.
   - Ajouter `streamReflexiveExecutionTraceSse` pour `GET /api/v1/executions/{execution_id}/trace-stream` et migrer `streamAssistantTurnSse` dans le fichier scindé `domains/assistantStreaming.ts` (`bootstrapAndOntology.ts` ramené `< 350` L).
   - Synchroniser `pnpm --filter @orcia/api-client generate` (`0-diff` OpenAPI).

### 2.4 Interface Utilisateur & Expérience (`apps/web/`, `packages/ui/`)
1. **Migration SSE dans `apps/web`** :
   - [`apps/web/src/features/shared/useReflexiveExecutionController.ts#L127-L131`](../../../apps/web/src/features/shared/useReflexiveExecutionController.ts#L127-L131) : remplacer `fetch(streamUrl)` brut par `streamReflexiveExecutionTraceSse` (`@orcia/api-client`).
   - [`apps/web/src/components/useWorkspaceEventsSse.ts#L31-L32`](../../../apps/web/src/components/useWorkspaceEventsSse.ts#L31-L32) : remplacer `new EventSource(...)` par un flux `fetch` + `ReadableStream` via `createRequestSse` (`AbortController`, reconnexion bornée avec backoff sur erreurs transitoires, arrêt et alerte sur `401`/`403`).
2. **Correction UX `P0-UX-1` / `P2-UX-11` dans `useAssistantStreamingTurn.ts#L315-L328` & `fr.ts`/`en.ts`** :
   - Inspecter `OrciaProblemError` (`status` / `error_code`) :
     - Si `status === 401 || status === 403` : afficher une alerte critique (`role="alert"`, variante erreur `stale-danger` contraste WCAG AA `>= 4,5:1`) en français métier sans code HTTP brut (*« Votre session a expiré ou doit être renouvelée pour continuer la conversation. »*) + bouton d'action **`Se reconnecter →`** pointant vers `/login`.
     - Réserver le message d'indisponibilité du service IA aux codes `502`/`503`/`504` ou pannes réseau de fournisseur, avec action contextuelle adaptée.
3. **Alignement E2E `apps/web/e2e/00-stack-smoke.spec.ts#L34-L141` (`#3` & `#4`)** :
   - Dans `#3` (`Story 16.1`) et `#4` (`Story 16.2`), vérifier explicitement que l'appel anonyme Jour 0 reçoit **`HTTP 401`** (preuve *fail-closed* `ORCIA_ENV="e2e"`), puis créer/authentifier le premier administrateur (`createFirstAdminAndGetBearerToken` / `createFirstAdminViaUi`) et passer `{ token }` aux appels `apiGet` / `apiPost` + flux SSE authentifiés.

### 2.5 Analyse d'Impact sur la Pyramide des Tests (`AD-17` — Couches 1 à 5 + Sécurité, Obligatoire)
- **Couche 1a (Python) & Couche 1b (Vitest TS)** :
  - Tests `@orcia/api-client` sur `createRequestSse` (injection `Bearer`, `Accept-Language`, refresh `401`, levée `OrciaProblemError`).
  - Tests `@orcia/web` (`useAssistantStreamingTurn`, `useReflexiveExecutionController`, `useWorkspaceEventsSse`) vérifiant le rendu `role="alert"` avec bouton `Se reconnecter →` sur `401` (zéro accusation modèle IA, zéro HTTP code brut) et `503` sur panne IA.
- **Couche 2 (Intégration Verticale PG18 `tests/integration/`)** :
  - Test Composition Root `create_app()` : `GET /api/v1/events/stream` rejette `401` sans `Bearer`, `403` hors workspace, et diffuse les événements `< 500 ms` avec un jeton valide ; `POST /api/v1/assistant/three-speed/stream` avec `DeterministicCassetteLLM`.
- **Couche Sécurité (`tests/security/`)** :
  - Vérification *fail-closed* de `/api/v1/events/stream`, `/api/v1/sources/inspect-lines` et `/api/v1/executions/reflexive` sous `ORCIA_ENV="e2e"`.
- **Couche 5 (E2E Playwright ciblé)** :
  - `00-stack-smoke.spec.ts` (`#1`–`#4`), `02-assistant-streaming-and-folders.spec.ts` (`#7`–`#9`), `04-multi-actor-claim-sse.spec.ts` et `12-epic16-reflexive-trace-and-line-inspector.spec.ts` 100 % verts en Desktop + Mobile (`> 0` vérifié avec `23.1`).

---

## 3. Bilan des Modifications & Résultats (Post-Implémentation)

### 3.1 Fichiers Développés & Modifiés
| Fichier | Nature (Création / Modification / Refactoring) | Description synthétique |
| :--- | :--- | :--- |
| `packages/api-client/src/helpers.ts` | Modification | Ajout de `createRequestSse`, `registerDefaultAccessTokenRefreshedHandler` et d'un verrou *single-flight* partagé sur `POST /api/v1/auth/refresh` (`createRequestJson` / `createRequestBinary` / `createRequestSse`) : injection `Authorization: Bearer`, `Accept-Language`, `Accept: text/event-stream`, `credentials: "include"`, tentative unique de refresh session sur `401` sans boucle infinie ni tempête concurrente, parsing RFC 9457 (`OrciaProblemError`). |
| `packages/api-client/src/domains/bootstrapAndOntology.ts` + `assistantStreaming.ts` + `index.ts` + `openapi.json` | Refactoring / Création | Extraction du domaine SSE/streaming dans `assistantStreaming.ts` (`streamAssistantTurnSse`, `streamReflexiveExecutionTraceSse`, `streamWorkspaceEventsSse`) ; export public via `index.ts` et resynchronisation OpenAPI. |
| `apps/api/src/orcia_api/routers/inbox_and_leases.py` + `workspace_leases.py` | Refactoring / Modification | Extraction des endpoints `/resource-leases/*` dans `workspace_leases.py` ; protection de `GET /api/v1/events/stream` par `resolve_request_user`, `sync_evaluator_topology_from_pg` et `_enforce_inbox_workspace_guard` (`401` anonyme sous `ORCIA_ENV="e2e"`, `403` hors périmètre). |
| `apps/web/src/components/{useWorkspaceEventsSse.ts,OrciaRootErrorBoundary.tsx,useShellAutonomousSupervision.ts,platformSetupGovernanceActions.ts}`, `main.tsx`, `stores/authSessionStore.ts` | Modification / Création | Remplacement de `EventSource` par `streamWorkspaceEventsSse` (`createRequestSse` + Bearer + backoff borné + arrêt sur `401`/`403`) sans avortement lors de la rotation `accessToken`, branchement `registerDefaultAccessTokenRefreshedHandler`, garde `platformSetupGovernanceActions`, et extraction de `OrciaRootErrorBoundary` (`role="alert"`, `data-testid="orcia-root-error-boundary"`). |
| `apps/web/src/features/shared/useReflexiveExecutionController.ts` | Modification | Remplacement de `fetch(streamUrl)` brut par `streamReflexiveExecutionTraceSse` (`createRequestSse` + Bearer). |
| `apps/web/src/features/inbox/{assistantBackgroundStreamStore.ts,useAssistantStreamingTurn.ts,useInboxPanelController.ts,index.tsx}` + `i18n/locales/assistant_labels.ts` | Modification | Classification `classifyAssistantStreamError` (`401`/`403` → `auth_expired` sans code HTTP brut ni accusation LLM ; `502`/`503`/`504`/réseau → `ai_unavailable`) et câblage `onReconnect` (reset session + navigation `/login`). |
| `packages/ui/src/{index.ts,primitives/AssistantActiveStreamContent.tsx,AssistantSpeedSelectorAndStreamView.tsx,AssistantSpeedSelectorTypes.ts}` | Modification | Bandeau critique `role="alert"` (`data-testid="assistant-error-banner"`, `.orcia-ds-alert-error`) et bouton `assistant-error-reconnect-btn` (`Se reconnecter →`). |
| `apps/web/e2e/{00-stack-smoke.spec.ts,04-multi-actor-claim-sse.spec.ts,support/firstAdmin.ts}` + `src/__tests__/setup/assistantAndInboxMockHandlers.ts` | Modification | Alignement *fail-closed* `00-stack-smoke` (`401` anonyme vérifié avant création admin + appels Bearer) et `04-multi-actor-claim-sse` (`openSseStream` authentifié Bearer + preuve `401` anonyme) + `docs/product/capabilities.yaml`. |
| `packages/api-client/src/__tests__/request-sse.test.ts`, `packages/ui/src/__tests__/story-23-2-assistant-error-banner.test.tsx`, `apps/web/src/__tests__/{story-23-2-sse-auth-and-error-banner.test.tsx,i18n-and-shell.test.tsx}` | Création / Modification | Couche 1b : tests `createRequestSse` (Bearer, `Accept-Language`, verrou *single-flight* partagé `/auth/refresh` sur `401` + reset échec, `OrciaProblemError`), alerte UI `401`/`503`, survie `useWorkspaceEventsSse` au refresh token, `OrciaRootErrorBoundary`, `useReflexiveExecutionController` et navigation `/login`. |
| `tests/integration/test_story_23_2_sse_auth_and_streams_pg18.py`, `tests/security/test_story_23_2_sse_e2e_fail_closed.py`, `tests/unit/test_story_5_1_notifications_claim_and_resource_leases.py` | Création / Modification | Couche 2 (`testcontainers` PG18 + Redis + vrai `create_app()` sans override sous `ORCIA_ENV="e2e"`) & Couche Sécurité & Couche 1a : `401`/`403`/`200 text/event-stream` sur `/events/stream` (y compris mode `live=True` et fallback sync) et `/assistant/three-speed/stream` (`DeterministicCassetteLLM`), gardes `READ_ONLY_OBSERVER` (`X-Orcia-Access-Mode` & `ROLLUP_PARENT`), `POST /tasks/{id}/release` + preuves SQL PG18. |

### 3.2 Résultats Chiffrés, Métriques & Qualité
- **Pyramide TS (`pnpm turbo run lint typecheck test --concurrency=2`)** : **`9/9` tâches vertes** (`329` tests / `82` fichiers) :
  - `@orcia/api-client` : **`20/20` passed** (`3` fichiers dont `request-sse.test.ts` `7/7`).
  - `@orcia/ui` : **`112/112` passed** (`27` fichiers dont `story-23-2-assistant-error-banner.test.tsx` `2/2`).
  - `@orcia/web` : **`197/197` passed** (`52` fichiers dont `story-23-2-sse-auth-and-error-banner.test.tsx` `7/7` et les 5 audits `zero-dead-buttons-and-silent-catches-audit`, `e2e-testids-sync-audit`, `anti-jargon-and-secrets-ui-audit`, `css-class-integrity-audit`, `vitest-transport-fail-closed-openapi`).
- **Qualité statique & Architecture Python (`AD-19`)** :
  - `.venv/bin/ruff check . && .venv/bin/ruff format --check .` : **`0` erreur**, `1257` fichiers formatés.
  - `.venv/bin/mypy --strict packages/orcia-core packages/orcia-connectors apps/api apps/worker` : **`0` erreur** (`551` fichiers source).
  - `.venv/bin/lint-imports` : **`5` contrats conservés, `0` brisé** (`597` fichiers, `4289` dépendances).
  - `.venv/bin/python scripts/export_openapi.py --check` : **`0-diff`** (`openapi.json` synchronisé).
- **Couverture ciblée (`COVERAGE_CORE=ctrace`, `test_story_5_1` `-k "not test_alembic_0021"` + `test_story_23_2_sse_auth_and_streams_pg18.py`)** :
  - `apps/api/src/orcia_api/routers/inbox_and_leases.py` : **`100 %`** (`108` stmts, `0` miss, `20` branches, `0` partial).
  - `apps/api/src/orcia_api/routers/workspace_leases.py` : **`100 %`** (`28` stmts, `0` miss).
  - Total combiné : **`100.00 %`** (`136` stmts, `0` miss ; `--cov-fail-under=90` vert, `5 passed, 1 deselected` — `test_alembic_0021_story_5_1_migration_on_real_postgres18` pré-existant reste exclu sous instrumentation Python 3.12 / SQLAlchemy `2.1` `_cache_key_cy.py:196`).
- **Traçabilité & Registre Python** :
  - `tests/unit/test_epic22_to_epic23_traceability.py`, `tests/unit/test_capabilities_registry.py`, `tests/security/test_story_23_2_sse_e2e_fail_closed.py` : **`21/21` passed**.

### 3.3 Validation & Procédure de Test sur Toute la Pyramide (`AD-17` + 5 Garde-Fous de Câblage Vertical)
- **Couche 1a & Audits AST Python** :
  - `tests/unit/test_codebase_architectural_anti_patterns_audit.py` + `test_assistant_and_rag_routes_require_rag_guard_audit.py` : **`7/7` passed**.
  - `tests/unit/test_integration_no_manual_app_state_audit.py` + `test_zero_orphan_sql_adapters_audit.py` + `test_e2e_sql_coverage_audit.py` : **`4/4` passed**.
- **Couche 2 (Intégration PG18/Redis Composition Root sans override) & Couche Sécurité (`ORCIA_ENV="e2e"`)** :
  - `tests/integration/test_story_23_2_sse_auth_and_streams_pg18.py` + `tests/security/test_story_23_2_sse_e2e_fail_closed.py` + `tests/unit/test_story_5_1_notifications_claim_and_resource_leases.py -k "not test_alembic_0021"` : **`5/5` passed** (`100.00 %` couv.) ; avec `tests/security/test_story_22_3_security_guards.py` : **`6/6` passed** sur le tir combiné.
- **Couche 5 — Chaîne Canari E2E Obligatoire (`ORCIA_E2E_CAMPAIGN_DIR=/tmp/orcia-e2e-canary-23-2`, `--retries=0 --timeout=35000`, `0` fixture cachée)** :
  - `00-stack-smoke.spec.ts` (`#1`–`#4`, `desktop-cockpit` + `mobile-companion`) : **`8/8` passed**.
  - `01-day0-boot-and-f5-persistence.spec.ts` (`desktop-cockpit` + `mobile-companion`) : **`4/4` passed**.
  - `02-assistant-streaming-and-folders.spec.ts` (`desktop-cockpit` + `mobile-companion`) : **`6/6` passed** (y compris le tour d'assistant SSE `DeterministicCassetteLLM` `#7`, zéro écran blanc après refresh token *single-flight*).
  - `03-human-led-anchor-and-arbitration.spec.ts` (`desktop-cockpit` + `mobile-companion`) : **`2/2` passed**.
  - `04-multi-actor-claim-sse.spec.ts` : **`2/2` passed** (`desktop-cockpit`), **`2` skipped** (`mobile-companion` skip attendu).
  - `12-epic16-reflexive-trace-and-line-inspector.spec.ts` : **`1/1` passed** (`desktop-cockpit`) ; **`1` failed** pré-existant (`timedOut` sur budget `35s`, `36.1s`) en `mobile-companion` sur `L28-29` (`ensureCentralWorkspaceVisibleOnMobile` attend `getByTestId('four-zone-sidebar')` alors que `FourZoneSidebarRail` (`four-zone-sidebar`) n'est monté que sous `!isMobile` dans `FourZoneDirectionCShell.tsx:L254` — hors périmètre SSE `23.2`, reporté pour priorisation ultérieure en `Story 23.6`).
  - Total Chaîne Canari (`26` cas) : **`23 passed`, `2 skipped`, `1 failed` (`mobile-companion` `12-epic16`)**, `26` captures PNG générées dans `/tmp/orcia-e2e-canary-23-2/screenshots/` (dont `23` `passed`, `2` `skipped`, `1` `timedOut`).
