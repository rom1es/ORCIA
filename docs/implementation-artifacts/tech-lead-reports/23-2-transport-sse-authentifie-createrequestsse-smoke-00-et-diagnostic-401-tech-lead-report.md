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

> *[Pré-implémentation initialisée en Story 22.10 — à compléter après implémentation et validation de la Story 23.2]*

### 3.1 Fichiers Développés & Modifiés
| Fichier | Nature (Création / Modification / Refactoring) | Description synthétique |
| :--- | :--- | :--- |
| `packages/api-client/src/helpers.ts` | Modification | *[À compléter après implémentation Story 23.2]* |
| `packages/api-client/src/domains/bootstrapAndOntology.ts` + `assistantStreaming.ts` | Refactoring / Création | *[À compléter après implémentation Story 23.2]* |
| `apps/api/src/orcia_api/routers/inbox_and_leases.py` | Modification | *[À compléter après implémentation Story 23.2]* |
| `apps/web/src/features/shared/useReflexiveExecutionController.ts`, `components/useWorkspaceEventsSse.ts`, `features/inbox/useAssistantStreamingTurn.ts`, `e2e/00-stack-smoke.spec.ts` | Modification | *[À compléter après implémentation Story 23.2]* |

### 3.2 Résultats Chiffrés, Métriques & Qualité
- **Couverture de tests** : *[À compléter — $\ge 90\%$ requis]*
- **Qualité statique & Architecture** : `ruff`, `mypy --strict`, `pnpm turbo run lint typecheck test`, `openapi-typescript` `0-diff`, `gitnexus_detect_changes()` *[À compléter]*

### 3.3 Validation & Procédure de Test sur Toute la Pyramide (`AD-17` + 5 Garde-Fous de Câblage Vertical)
- *[À compléter après passage de `00-stack-smoke`, `02-assistant`, `04-multi-actor` et `12-epic16`]*
