## Epic 23: Déblocage Reset PG18/Redis, Transport SSE Authentifié, Zone 4 & Accostage `X/6`, Sobriété Direction C, Durcissement Anti-Goodhart, Campagne Desktop `52/52` & Clôture Conditionnelle

Résoudre de manière définitive et vérifiable par PostgreSQL 18 les échecs E2E (`3` rejets `HTTP 401` directs + `87` cascades `resetDay0()`) répartis sur `24` specs ainsi que les `13` chantiers `REM23-01`..`REM23-13` (`12` défauts UX/UI Sally `P0-UX-1`..`P3-UX-12` + `10` défauts d'architecture Winston `ARCH23-01`..`ARCH23-10`) sur la séquence **`23.1`..`23.5` $\rightarrow$ `23.6a` $\rightarrow$ `23.7` $\rightarrow$ `23.8`**, avec report explicite de la **`Story 23.6` et de la compatibilité Mobile Companion (`--project=mobile-companion`, `390×844`, `CAP-042`) vers `ACTION_ITEM-23.6`** pour priorisation ultérieure. Durant l'Epic 23, chaque lot applique l'**Étape 0 Réconciliation E2E ↔ `DESIGN.md`** et la **Chaîne Canari Desktop Obligatoire**, suivis du **Tir de reconnaissance Desktop V0** en sortie de `23.6a`, de la campagne figée `--project=desktop-cockpit` (`24` specs / `55` scénarios Desktop) en `23.7` et d'une clôture directe sans `Epic 24` vide si `52/52` PASS Desktop et `0` écart `P0`/`P1` en `23.8`.

### Story 23.1: Déblocage `resetDay0()` (`TRUNCATE CASCADE` E2E Isolé `orcia_e2e`), Protection `connector_schemes` & Purge Redis `FLUSHDB` (`REM23-01` / `ARCH23-01`)

As a Ingénieur Plateforme & Mainteneur du Harnais E2E (`Winston`),
I want protéger `connector_schemes` dans `09_reset_db_first_boot.py` sans affaiblir aucun trigger append-only, et implémenter dans `infra/scripts/e2e/reset_day0.py` (sous garde bloquant `is_isolated_e2e_database_url` `orcia_e2e` uniquement) un `TRUNCATE TABLE ... RESTART IDENTITY CASCADE` excluant `alembic_version` et `connector_schemes` complété par un nettoyage `dbos.*`, un reset `platform_auth_settings` (`boot_epoch`), une éviction caches API et un `FLUSHDB` Redis (`state["redis_url"]`),
So that l'insertion réelle de lignes `step_executions`, `blackboard_snapshots` et `audit_ledger` par les tests E2E (tels que `#10`) ne provoque plus jamais de `RestrictViolationError` en cascade (`87` échecs `#11`–`#110`) tout en respectant strictement la politique `GEMINI.md` interdisant `DISABLE TRIGGER`.

**Dépendances :** Clôture de `Story 22.10`. Vague 0 (`P0`), bloque `Story 23.3`–`23.6`.
**CAP couvertes :** `CAP-003`, `CAP-011`, `CAP-020`, `CAP-021`, `CAP-022`, `CAP-024`, `CAP-030`, `CAP-031`, `CAP-032`, `CAP-033`, `CAP-054`, `CAP-065`, `CAP-082`, `CAP-140`, `CAP-200`, `CAP-201` (et déblocage des `87` échecs `beforeEach` `#11`–`#110`).
**Fichiers impactés :** `infra/scripts/maintenance/09_reset_db_first_boot.py`, `infra/scripts/e2e/reset_day0.py`, `apps/web/e2e/support/day0.ts`, `tests/unit/`, `tests/integration/`.
**Rapport Tech Lead :** `docs/implementation-artifacts/tech-lead-reports/23-1-reset-jour0-e2e-truncate-cascade-connector-schemes-et-redis-tech-lead-report.md`.

**Acceptance Criteria:**

**Given** une base `orcia_e2e` contenant des lignes dans `users`, `workflow_runs`, `step_executions`, `blackboard_snapshots` (protégée `BEFORE UPDATE OR DELETE ... FOR EACH ROW` + FK `ON DELETE RESTRICT`), `audit_ledger`, `connector_schemes` et des clés actives dans Redis (`help:*`, `lock:step:*`)
**When** `reset_day0.py` s'exécute après validation de `is_isolated_e2e_database_url(database_url)`
**Then** toutes les tables applicatives et append-only (hors `alembic_version` et `connector_schemes`) sont vidées via `TRUNCATE TABLE ... RESTART IDENTITY CASCADE`, `connector_schemes` reste peuplée, les triggers `trg_blackboard_snapshots_append_only` et `prevent_audit_ledger_mutation` demeurent actifs (`0` `DISABLE TRIGGER`), Redis est vidé par `FLUSHDB`, et un test `testcontainers` PG18 + Redis prouve `COUNT(*) == 0` sur `users`/`step_executions`/`blackboard_snapshots` et l'enchaînement vert `03-human-led` → `04-multi-actor` → `shell.spec.ts`.

**Given** une chaîne de connexion pointant hors de la base isolée `orcia_e2e` ou une invocation de `09_reset_db_first_boot.py`
**When** `reset_day0.py` ou `09_reset_db_first_boot.py` s'exécute
**Then** `reset_day0.py` refuse immédiatement l'exécution par `RuntimeError` hors `orcia_e2e`, et `09_reset_db_first_boot.py` préserve `connector_schemes` dans `PROTECTED_TABLES` sans jamais utiliser `TRUNCATE` sur les tables append-only ni `DISABLE TRIGGER`.

---

### Story 23.2: Transport SSE Authentifié `createRequestSse`, Alignement *Fail-Closed* `00-stack-smoke` (#3/#4) & Diagnostic `401` Session Expirée (`REM23-02`, `REM23-03`, `REM23-04`)

As a Utilisateur de `Mon Assistant` & Architecte Sécurité (`Sally` × `Winston`),
I want factoriser une primitive `createRequestSse` dans `packages/api-client/src/helpers.ts` (injectant `Authorization: Bearer`, `credentials: "include"`, `Accept-Language`, refresh `401` et parsing RFC 9457 `OrciaProblemError`, tout en scindant `bootstrapAndOntology.ts` > 400 L), migrer `streamAssistantTurnSse`, `useReflexiveExecutionController` (`/trace-stream`) et `useWorkspaceEventsSse` (`/events/stream`, protégé serveur par `resolve_request_user` + `_enforce_inbox_workspace_guard`), aligner `00-stack-smoke.spec.ts` #3/#4 sur `ORCIA_ENV="e2e"`, et corriger le message d'erreur `401` dans `useAssistantStreamingTurn.ts` (`P0-UX-1`),
So that les `3` échecs `HTTP 401` directs disparaissent sans relâcher la sécurité serveur, les flux `/trace-stream` et `/events/stream` soient authentifiés, et une session expirée affiche une alerte claire avec action `Se reconnecter →` au lieu d'accuser le modèle IA.

**Dépendances :** Aucun prérequis bloquant hors Vague 0 (parallélisable/séquentiel avec `Story 23.1`, avant Vague 1).
**CAP couvertes :** `CAP-004`, `CAP-040`, `CAP-071`, `CAP-074`, `CAP-075`, `CAP-160`.
**Fichiers impactés :** `packages/api-client/src/helpers.ts`, `packages/api-client/src/domains/bootstrapAndOntology.ts` (+ `assistantStreaming.ts`), `apps/api/src/orcia_api/routers/inbox_and_leases.py`, `apps/web/src/features/shared/useReflexiveExecutionController.ts`, `apps/web/src/components/useWorkspaceEventsSse.ts`, `apps/web/src/features/inbox/useAssistantStreamingTurn.ts`, `apps/web/src/i18n/locales/{fr,en}.ts`, `apps/web/e2e/00-stack-smoke.spec.ts`.
**Rapport Tech Lead :** `docs/implementation-artifacts/tech-lead-reports/23-2-transport-sse-authentifie-createrequestsse-smoke-00-et-diagnostic-401-tech-lead-report.md`.

**Acceptance Criteria:**

**Given** un utilisateur authentifié envoyant un message dans `Mon Assistant` ou suivant une trace réflexive `/trace-stream` / un flux `/events/stream`
**When** le client `@orcia/api-client` ouvre le flux SSE via `createRequestSse`
**Then** l'en-tête `Authorization: Bearer` et `Accept-Language` sont automatiquement transmis (test `02-assistant` #7 vert avec `DeterministicCassetteLLM`), `GET /api/v1/events/stream` rejette en `401` sans jeton et en `403` hors périmètre workspace, et `00-stack-smoke.spec.ts` #3/#4 vérifient explicitement le rejet `401` anonyme puis réussissent avec jeton premier admin.

**Given** un flux `Mon Assistant` recevant une erreur `OrciaProblemError` de statut `401` ou `403` vs `502`/`503`/`504`
**When** `useAssistantStreamingTurn` affiche le bandeau d'erreur (`role="alert"`)
**Then** un rejet `401`/`403` affiche un message métier FR/EN (*« Votre session a expiré ou doit être renouvelée pour continuer la conversation. »*, zéro code `HTTP 401`, zéro accusation du modèle IA, contraste WCAG AA `>= 4,5:1`) accompagné d'un CTA **`Se reconnecter →`** vers `/login`, tandis que le diagnostic d'indisponibilité IA reste réservé aux erreurs `502`/`503`/`504` / pannes réseau.

---

### Story 23.3: Zone 4 (`Aide Contextuelle`) 100 % Fidèle à la Route, Blocs `DESIGN.md` Restaurés & Suppression de la Plomberie Interne (`REM23-05`)

As a Utilisateur découvrant ORCIA sur `/cockpit`, `/assistant` ou les écrans métiers (`Sally`),
I want supprimer l'écrasement global `GENERAL_SECTIONS_FR` dans `ShellContextualHelpColumn.tsx:L71` (et le `catch {}` muet + init optimiste `["BASE","PACK","WORKSPACE"]`), étendre `contextual_help_loader.py` & `HelpArticleSchemaItem` (`real_example_text`, `common_pitfalls_items`) pour rendre nativement les `4` blocs prescrits par `DESIGN.md` (`À quoi sert cet écran`, `EN N GESTES`, encadré ambre `UN EXEMPLE RÉEL`, `CE QUI COINCE SOUVENT`), scinder `ContextualHelpColumnAndCenter.tsx` (`394` L), masquer la plomberie `@version` / `Sources du guide` aux non-admins et ajouter un indicateur visuel de scroll sur `FourZoneHelpAsideColumn.tsx`,
So that Zone 4 n'affiche plus jamais de fiches Cockpit sur `/assistant` ni de métadonnées internes brutes et présente l'aide structurée attendue par `DESIGN.md`.

**Dépendances :** Vague 0 (`Story 23.1`, `Story 23.2`).
**CAP couvertes :** `CAP-064`, `CAP-068`.
**Fichiers impactés :** `packages/orcia-core/src/orcia_core/catalog/contextual_help_loader.py`, `docs/help/{fr,en}/*.md`, `apps/api/src/orcia_api/schemas/catalog.py`, `apps/api/src/orcia_api/routers/portal_and_help.py`, `packages/api-client`, `apps/web/src/components/{ShellContextualHelpColumn,contextualHelpCatalog,_contextualHelpSections}.ts*`, `packages/ui/src/primitives/{ContextualHelpColumnAndCenter,FourZoneHelpAsideColumn}.tsx`.
**Rapport Tech Lead :** `docs/implementation-artifacts/tech-lead-reports/23-3-zone-4-aide-contextuelle-fidele-a-la-route-et-4-blocs-design-md-tech-lead-report.md`.

**Acceptance Criteria:**

**Given** un utilisateur naviguant vers `/assistant` puis `/cockpit` avec le panneau Zone 4 ouvert
**When** `/api/v1/help/resolve` retourne le guide Markdown de la route active
**Then** Zone 4 affiche exclusivement les sections de la route active (zéro carte `"Le Cockpit regroupe..."` sur `/assistant`, zéro incohérence avec `Polyvalent · Standard`), rend nativement `À quoi sert cet écran`, `EN N GESTES`, l'encadré ambre `UN EXEMPLE RÉEL` et `CE QUI COINCE SOUVENT`, masque `@version` / `Sources du guide : BASE...` hors tiroir technique admin, loge proprement toute erreur réseau sans `catch {}` silencieux, et affiche un repère de défilement si le contenu excède la hauteur.

---

### Story 23.4: Unification `Accostage X/6` PG18, Suppression des Fantômes Jour 0 (`AP`, `Notifications 4`) & Ergonomie Modale Premier Admin (`REM23-06`, `REM23-07`, `REM23-08`)

As a Premier Administrateur amorçant ORCIA au Jour 0 (`Sally` × `Winston`),
I want supprimer le split-brain backend (`{"first-admin"}` en dur dans `progressive_accostage.py:L146`) vs frontend (`/5` sans `adminCreated` dans `platformSetupStore.tsx`, `521` L à scinder) pour aligner toute la pile sur une source PG18 unique **`Accostage X/6`** (incluant `workspace_llm_tier_mappings`), supprimer le profil fantôme `AP` et `Notifications 4` lorsque `platformAdmin === null` (`0` utilisateur en base), homogénéiser les entrées verrouillées au Jour 0 tout en purgeant les `5` props mortes de `ShellContainer.tsx` (`403` L), et corriger `FirstBootAdminSetupModal.tsx` (zéro double `Annuler (Esc)`, placeholder vide + bouton œil, hiérarchie CTA `#2563EB`),
So that le parcours Jour 0 soit fidèle à la réalité PostgreSQL 18 sans identité fantôme, sans compteur dupliqué ni troncature, et doté d'une modale de premier démarrage irréprochable.

**Dépendances :** Vague 0 (`Story 23.1`, `Story 23.2`).
**CAP couvertes :** `CAP-005`, `CAP-060`, `CAP-061`.
**Fichiers impactés :** `packages/orcia-core/src/orcia_core/bootstrap/progressive_accostage.py`, `apps/web/src/components/{platformSetupStore,platformSetupAccostage,platformSetupHydration,ShellContainer,shellPresets,shellScopeOptions,FirstBootAdminSetupModal}.ts*`, `apps/web/src/features/cockpit/index.tsx`, `packages/ui/src/primitives/{ProgressiveDay0AccostageBanner,FourZoneSidebarRail,RadixDesignSystemPrimitives}.tsx`, `apps/web/src/i18n/locales/{fr,en}.ts`, `apps/web/e2e/shell.spec.ts`.
**Rapport Tech Lead :** `docs/implementation-artifacts/tech-lead-reports/23-4-unification-accostage-x-sur-6-fin-fantomes-jour0-et-modale-admin-tech-lead-report.md`.

**Acceptance Criteria:**

**Given** une plateforme fraîchement réinitialisée au Jour 0 (`0` utilisateur dans `users`)
**When** la SPA démarre et affiche la modale obligatoire `FirstBootAdminSetupModal`
**Then** aucun profil fantôme `AP` ni compteur `Notifications 4` n'apparaît dans la coquille, les entrées verrouillées portent un état désactivé uniforme et explicite (tout en respectant la garde RBAC de `Configuration` vérifiée par `shell.spec.ts`), la modale ne comporte ni double bouton `Annuler (Esc)` ni points noirs `••••••••••••` pré-remplis, dispose d'un bouton œil et d'un CTA primaire `#2563EB` net, et après création du premier admin + `F5`, un unique badge **`Accostage 1/6`** (puis `2/6` après modèle IA dans `workspace_llm_tier_mappings`) s'affiche sans doublon `1. Modèles IA` ni libellé tronqué.

---

### Story 23.5: Sobriété Cockpit (`<= 3` Blocs), `TopHeaderBar` Sans Doublon/Troncatures, Logo Zone 1, Épuration `/assistant` & `/login` et Preuves `#10` (`REM23-09`..`REM23-12`)

As a Utilisateur quotidien d'ORCIA sur Desktop (`1440×900`) & Auditeur UX (`Sally`),
I want ramener `/cockpit` à **`<= 3` blocs visuels** (montage conditionnel de `CockpitHumanLedGovernanceSection` lorsqu'une décision/run le requiert), supprimer `topbar-fixed-workspace-selector` dupliqué sur Desktop `>= 768px`, déplacer le logo `ORCIA` en tête de Zone 1 (`DESIGN.md` §2.1), inclure l'équipe dans `buildShellBreadcrumbItems`, raccourcir le placeholder de recherche à `Rechercher… (⌘K)`, doter le loader initial et `/login` du logo ORCIA + bouton œil, exclure `/assistant` (`inbox`) de la carte d'en-tête `ModuleWorkspaceView`, masquer les compteurs `(0)` (avec mise à jour `02-assistant.spec.ts`), unifier `orcia-ds-btn` + contraste `➤`, remplacer `"embedding"` par `"indexation sémantique"` dans `fr.ts`, et ajouter des captures intermédiaires sur `HumanLedAnchorCard`/`ArbitrationTieBreakCard` dans `03-human-led-anchor-and-arbitration.spec.ts`,
So that l'écran principal respecte la Loi de Hick sans aucune troncature à `1440px`, l'espace `/assistant` soit épuré de tout jargon et les cartes identitaires `#6D28D9`/`#D97706` soient auditables visuellement.

**Dépendances :** Vague 0 (`Story 23.1`, `Story 23.2`).
**CAP couvertes :** `CAP-001`, `CAP-023`, `CAP-041`, `CAP-062`, `CAP-070`, `CAP-072`, `CAP-073`, `CAP-190`.
**Fichiers impactés :** `apps/web/src/features/cockpit/{index,CockpitRunsSection,CockpitHumanLedGovernanceSection}.tsx`, `packages/ui/src/primitives/{StreamlinedCockpitView,FourZoneTopHeaderSection,FourZoneSidebarRail,BiModeLoginView,AssistantSpeedSelectorAndStreamView}.tsx`, `apps/web/src/components/{shellPresets,ShellAuthFallbackView,ModuleWorkspaceView}.ts*`, `apps/web/src/features/inbox/{index,SavedConversationsAndThreadView}.tsx`, `apps/web/src/i18n/locales/fr.ts`, `apps/web/e2e/{02-assistant-streaming-and-folders,03-human-led-anchor-and-arbitration}.spec.ts`.
**Rapport Tech Lead :** `docs/implementation-artifacts/tech-lead-reports/23-5-sobriete-cockpit-topbar-sans-doublon-assistant-et-login-tech-lead-report.md`.

**Acceptance Criteria:**

**Given** un utilisateur connecté naviguant sur `/cockpit`, `/assistant` et `/login` en résolution Desktop `1440×900`
**When** les composants Direction C mis à jour sont rendus
**Then** `/cockpit` présente au plus `3` blocs visuels distincts sans montage à vide au bas de la page, la `TopHeaderBar` ne contient plus `topbar-fixed-workspace-selector` ni aucune troncature sur le fil d'Ariane ou la recherche `Rechercher… (⌘K)`, le logo `ORCIA` figure en tête de Zone 1 et sur `/login` (avec bouton œil), `/assistant` n'affiche ni double carte d'en-tête ni compteur `(0)` ni terme `"embedding"` (sélecteurs `02-assistant.spec.ts` synchronisés), et `03-human-led-anchor-and-arbitration.spec.ts` attache les captures de preuve de `HumanLedAnchorCard` (`#6D28D9`) et `ArbitrationTieBreakCard` (`#D97706`).

---

### Story 23.6: Stabilisation Specs `04`–`21` & Mobile Companion (`390×844`) & Audit `100 %` Assertions SQL PostgreSQL 18 Effectives (`55/55` Blocs E2E) (`REM23-13` / `ARCH23-10`) *(Reportée en `ACTION_ITEM-23.6`)*

> **Décision de report (`Step 2a Epic 23`, 2026-11-19)** : La **Story `23.6`** ainsi que l'ensemble du périmètre de compatibilité/fonctionnement Mobile (`--project=mobile-companion`, `390×844`, `CAP-042` et assertions responsive mobile) sont **déplacés vers `action_items:` (`ACTION_ITEM-23.6` dans `docs/implementation-artifacts/sprint-status.yaml`)** pour priorisation ultérieure. Le durcissement SQL PG18 effectif (`55/55` blocs E2E sans `SELECT 1` ni table alibi) est repris dans **`Story 23.6a`**, et l'exécution E2E Desktop (`--project=desktop-cockpit`, `1440×900`, `24` specs / `55` scénarios Desktop) dans **`Story 23.7`**.

As a Architecte (`Winston`), UX Designer (`Sally`) & Tech Lead (`Amelia`),
I want stabiliser l'ensemble des parcours `04`–`21`, `shell.spec.ts` et `mobile-companion` (`390×844`) mis au jour après le déblocage de `resetDay0()` (`23.1`–`23.5`), et auditer puis renforcer chacun des `55` blocs `test(...)` E2E (`55/55` sur `24` specs) afin que chaque bloc exécute des vérifications effectives en base de données PostgreSQL 18 (`expectDbRowExists`, `expectDbRowCount`, `queryDbRows` ciblant les tables réelles du domaine testé — zéro assertion purement mémoire, zéro `SELECT 1` ou requête factice),
So that l'ensemble des `24` specs soit vert en Desktop comme en Mobile Companion et que la preuve SQL PostgreSQL 18 soit irréfutable avant le gel applicatif de la campagne intégrale en `Story 23.7` (`P0-UX-2`, `AD-17`, `GEMINI.md` §3).

**Statut Sprint :** Déplacée vers `action_items:` (`ACTION_ITEM-23.6`, `status: open`, `priority: P2`).
**Dépendances :** Clôture de `Stories 23.1`..`23.5` (reportée hors chemin critique Epic 23 via `ACTION_ITEM-23.6`).
**CAP couvertes :** `CAP-042` *(maintenue `failed_e2e` vers `ACTION_ITEM-23.6`)* ; les autres `CAP-*` Desktop sont vérifiées en `Story 23.7`.
**Rapport Tech Lead :** `docs/implementation-artifacts/tech-lead-reports/23-6-campagne-e2e-integrale-mobile-companion-audit-et-62-capacites-runtime-tech-lead-report.md`.

**Acceptance Criteria:**

**Given** le report explicite du périmètre Mobile Companion (`--project=mobile-companion`, `390×844`, `CAP-042`) vers `ACTION_ITEM-23.6`
**When** la priorisation ultérieure reprendra ce chantier Mobile Companion
**Then** les specs `04`–`21`, `shell.spec.ts` et `05-mobile-companion-and-rgaa.spec.ts` seront stabilisées sur `390×844` (barre basse 3 onglets, zéro overflow horizontal, bannière desktop-only sur `/configuration` et `/organization`) sans `ORCIA_E2E_SEED_FIXTURES` ni `test.skip` masquant un échec.

---

### Story 23.6a: Durcissement Anti-Goodhart : Gardes OpenAPI `security`, Audits AST (`catch` muets, Constantes Fantômes, SQL Domaine, Jargon), Contrats Géométriques Direction C & Reset PG18 Dynamique (`CAP-100`, `hygiène`)

As a Architecte (`Winston`), Tech Lead (`Amelia`) & UX Designer (`Sally`),
I want fermer les `4` failles de type « loi de Goodhart » identifiées par la RCA Epic 22 (1. introspection SQL dynamique `information_schema.tables` & `pg_constraint` dans `reset_day0.py` & `09_reset_db_first_boot.py` ; 2. enforcement de `operation.security` dans `vitestFetchTransport` + interdiction AST/ESLint de `fetch(` et `new EventSource(` hors `packages/api-client/src/helpers.ts` ; 3. détection AST des `catch` muets et constantes fantômes sur `100 %` de `apps/web/src/**`, durcissement AST de `test_e2e_sql_coverage_audit.py` interdisant `SELECT 1` et tables hors domaine sur les `55` blocs `test(...)` E2E, et regex structurelles anti-jargon ; 4. contrats géométriques & sobriété Direction C Desktop `1440×900` dans `layoutGeometryAssertions.ts` branchés sur `shell.spec.ts` et `11-screens-smoke-without-server-errors.spec.ts` + helper `captureMilestoneScreenshot`), puis valider la **Chaîne Canari Desktop Obligatoire** et le **Tir de reconnaissance Desktop V0** (`24` specs / `55` scénarios Desktop sous `--project=desktop-cockpit`),
So that aucun test unitaire, test Vitest, contrôle AST ou parcours E2E Desktop ne puisse plus produire de faux positif avant le gel de la campagne figée `Story 23.7` (`AD-17`, `AD-19`, `NFR-TEST-1`, `DESIGN.md`, `CAP-100`).

**Dépendances :** Clôture de `Stories 23.1`..`23.5` (et **Étape 0 Réconciliation E2E ↔ `DESIGN.md`**). Précède et bloque `Story 23.7`.
**CAP couvertes :** `CAP-100` (`hygiène`).
**Fichiers impactés :** `infra/scripts/e2e/reset_day0.py`, `infra/scripts/maintenance/09_reset_db_first_boot.py`, `tests/unit/test_e2e_reset_day0_guard.py`, `tests/integration/test_e2e_reset_day0_postgres18_and_redis.py`, `apps/web/src/__tests__/setup/{transportAndOpenApiValidator,openApiRequestValidator}.ts`, `apps/web/src/__tests__/{vitest-transport-fail-closed-openapi.test.ts,zero-dead-buttons-and-silent-catches-audit.test.tsx,anti-jargon-and-secrets-ui-audit.test.ts}`, `tests/unit/test_e2e_sql_coverage_audit.py`, `apps/web/e2e/support/{layoutGeometryAssertions,e2eCaptureFixture}.ts`, `apps/web/e2e/{shell,11-screens-smoke-without-server-errors}.spec.ts` (et mise à niveau de toute spec E2E présentant une requête SQL alibi).
**Rapport Tech Lead :** `docs/implementation-artifacts/tech-lead-reports/23-6a-durcissement-anti-goodhart-gardes-openapi-ast-geometrie-et-reset-pg18-tech-lead-report.md`.

**Acceptance Criteria:**

**Given** le harnais Reset Jour 0 (`reset_day0.py` & `09_reset_db_first_boot.py`) exécuté sur une base PostgreSQL 18 (`testcontainers`) + Redis 7.4
**When** l'introspection SQL dynamique interroge `information_schema.tables` (`public`, `dbos`) et `pg_constraint`
**Then** aucune table créée par Alembic n'est orpheline de la stratégie de purge/protection, zéro `DISABLE TRIGGER` n'est utilisé, les contraintes `ON DELETE RESTRICT` et triggers append-only (`audit_ledger`, `blackboard_snapshots`) demeurent intacts, Redis atteint `DBSIZE == 0`, et les seeds socles `connector_schemes` & `catalog_items` restent intacts.

**Given** le transport Vitest (`vitestFetchTransport` / `openApiRequestValidator.ts`) validé contre `packages/api-client/openapi.json` et le code source `apps/web/src/**` + `packages/api-client/src/domains/**`
**When** une requête est émise sans en-tête `Authorization: Bearer <non-vide>` vers une opération déclarant `security` dans `openapi.json`, ou lorsqu'un fichier applicatif appelle directement `fetch(` ou `new EventSource(`
**Then** `vitestFetchTransport` rejette immédiatement l'appel en `HTTP 401 application/problem+json` (prouvé dans `vitest-transport-fail-closed-openapi.test.ts`) et l'audit AST / ESLint échoue immédiatement sur tout contournement `fetch(` / `new EventSource(` hors `packages/api-client/src/helpers.ts`.

**Given** les gardes AST frontend (`apps/web/src/__tests__/`) et Python (`tests/unit/test_e2e_sql_coverage_audit.py`)
**When** les audits s'exécutent sur `100 %` de `apps/web/src/**`, `apps/web/src/i18n/locales/`, `docs/help/` et les `55` blocs `test(...)` des `24` specs `apps/web/e2e/*.spec.ts`
**Then** tout `catch {}` / `.catch(() => ...)` muet, toute constante fantôme (`DEFAULT_HUMAN_PROFILE`, `GENERAL_SECTIONS_*`, compteur d'accostage parallèle), toute chaîne jargon structurée (`\bHTTP\s+[45]\d\d\b`, `@\d+\.\d+\.\d+`, `\b[A-Z]{3,}\s*→\s*[A-Z]{3,}\b`, `\(Esc\)`, `SCREAMING_SNAKE_CASE` multi-segments), et toute requête SQL alibi (`SELECT 1` ou table hors domaine) est rejeté automatiquement, et `100 %` des `55` blocs E2E vérifient au moins une table PostgreSQL 18 du domaine métier.

**Given** les contrats géométriques Direction C (`layoutGeometryAssertions.ts`) et `captureMilestoneScreenshot` (`< 440 KB`) branchés sur `shell.spec.ts` et `11-screens-smoke-without-server-errors.spec.ts` sous `--project=desktop-cockpit` (`1440×900`)
**When** la **Chaîne Canari Desktop Obligatoire** puis le **Tir de reconnaissance Desktop V0** (`24` specs / `55` scénarios Desktop) s'exécutent
**Then** `/cockpit` affiche `<= 3` blocs, Zone 1 / Zone 2 / Accostage n'ont aucune troncature, `<= 1` sélecteur d'espace visible existe sur Desktop, `<= 1` bouton annuler/fermer apparaît par dialog, `0` `placeholder` contient `•`, Zone 4 change effectivement avec ses `4` blocs `DESIGN.md` sur `/cockpit -> /assistant -> /spaces`, et l'ensemble des 5 couches `AD-17` est `100 %` vert avant `Story 23.7`.

---

### Story 23.7: Campagne Playwright E2E Intégrale Desktop Epic 23 (`--project=desktop-cockpit`), Captures PNG d'État Final (`55/55`), Bilan Exhaustif & Audit Croisé Sally × Winston

As a UX Designer (`Sally`), Architecte (`Winston`) & Tech Lead (`Amelia`),
I want exécuter sans retouche de code applicatif l'intégralité de la campagne Playwright E2E **Desktop** (`--project=desktop-cockpit`, `1440×900`, `24` specs, `55` scénarios Desktop dont `52` exécutés et `3` `mobile-only` skipped, `--retries=0 --max-failures=0 --timeout=35000`, `0` `ORCIA_E2E_SEED_FIXTURES`) après validation `100 %` verte de `23.1`..`23.5` + `23.6a` sur les 5 couches `AD-17` et le Tir de reconnaissance Desktop V0 vers `docs/implementation-artifacts/e2e-campaign-epic-23/`, archiver `playwright-results.json`, `manifest.jsonl` et `100 %` des captures PNG d'état final (`55/55` Desktop, `< 450 KB` par fichier), rédiger le bilan exhaustif `bilan-execution-tests-e2e-epic-23.md`, conduire l'audit croisé **Sally (UX) × Winston (Architecture)** (`notes-audit-sally-ux.md`, `notes-audit-winston-architecture.md`, `synthese-remediation-sally-winston-epic-23.md`), basculer `PLAYWRIGHT_RESULTS_PATH` dans `infra/scripts/uj_e2e_coverage.py` et mettre à jour honnêtement `docs/product/capabilities.yaml` (en maintenant `CAP-042` Mobile Companion `failed_e2e` avec `e2e_remediation_ref: "ACTION_ITEM-23.6"`),
So that 100 % des User Journeys (`UJ-1`..`UJ-20`) et des capacités Desktop (`61/62` `feature` + `3/3` `foundation`) disposent d'une preuve runtime et visuelle irréfutable sans maquillage (`P0-UX-2`, `AD-17`, `NFR-TEST-1`, `GEMINI.md` §5).

**Dépendances :** Clôture complète à `100 %` vert sur les 5 couches `AD-17` de `Stories 23.1`..`23.5` et `Story 23.6a`. Précède `Story 23.8`.
**CAP couvertes :** Vérification runtime réelle sur Desktop de `61 / 62` capacités `feature` + `3 / 3` `foundation` (`CAP-001`..`CAP-203`), `CAP-042` restant `failed_e2e` vers `ACTION_ITEM-23.6`.
**Fichiers impactés :** `docs/implementation-artifacts/e2e-campaign-epic-23/playwright-results.json`, `docs/implementation-artifacts/e2e-campaign-epic-23/manifest.jsonl`, `docs/implementation-artifacts/e2e-campaign-epic-23/screenshots/**/*.png`, `docs/implementation-artifacts/e2e-campaign-epic-23/bilan-execution-tests-e2e-epic-23.md`, `docs/implementation-artifacts/e2e-campaign-epic-23/notes-audit-sally-ux.md`, `docs/implementation-artifacts/e2e-campaign-epic-23/notes-audit-winston-architecture.md`, `docs/implementation-artifacts/e2e-campaign-epic-23/synthese-remediation-sally-winston-epic-23.md`, `infra/scripts/uj_e2e_coverage.py`, `docs/product/capabilities.yaml`, `apps/web/src/generated/orciaSiteManifest.ts`, `docs/site-catalog/index.html`.
**Rapport Tech Lead :** `docs/implementation-artifacts/tech-lead-reports/23-7-campagne-e2e-integrale-captures-png-bilan-et-audit-croise-sally-winston-tech-lead-report.md`.

**Acceptance Criteria:**

**Given** les Stories `23.1`..`23.5` et `23.6a` clôturées à `100 %` vert sur les 5 couches `AD-17` et la pile `orcia_e2e` (PostgreSQL 18 + `pgvector`, Redis 7.4, FastAPI, SPA Vite, `DeterministicCassetteLLM` `0 $`, sans `ORCIA_E2E_SEED_FIXTURES`) prête pour une campagne figée
**When** la campagne Playwright intégrale Desktop (`--project=desktop-cockpit`, `24` specs, `55` scénarios Desktop `1440×900`, `--retries=0 --max-failures=0 --timeout=35000`) est exécutée sans aucune retouche de code vers `docs/implementation-artifacts/e2e-campaign-epic-23/`
**Then** tous les artefacts bruts sont archivés (`playwright-results.json`, `manifest.jsonl` à `55` entrées Desktop, `55/55` captures PNG d'état final sous `screenshots/**/*.png` avec taille `< 450 KB` par fichier), et `e2e-campaign-epic-22/` reste intact comme archive historique.

**Given** les artefacts bruts de `e2e-campaign-epic-23/`
**When** le bilan factuel et l'audit croisé **Sally × Winston** sont conduits sur les `55` scénarios Desktop (`52` exécutés + `3` `mobile-only` skipped)
**Then** `bilan-execution-tests-e2e-epic-23.md` inventorie exactement les résultats (`52` `passed` attendus, `0` `failed`, `0` `timedOut`, `3` `skipped` `mobile-only`, delta vs Epic 22), `notes-audit-sally-ux.md` évalue les captures PNG Desktop (Direction C, contrastes WCAG, lisibilité, langue FR), `notes-audit-winston-architecture.md` vérifie la conformité `AD-1`..`AD-24` & SQL PG18, et `synthese-remediation-sally-winston-epic-23.md` consigne tout échec résiduel ou écart `P0`/`P1` (ou confirme `0` écart `P0`/`P1`, en traçant `CAP-042` vers `ACTION_ITEM-23.6`).

**Given** les résultats réels de `docs/implementation-artifacts/e2e-campaign-epic-23/playwright-results.json`
**When** `PLAYWRIGHT_RESULTS_PATH` dans `infra/scripts/uj_e2e_coverage.py` bascule vers `e2e-campaign-epic-23/playwright-results.json`, que `docs/product/capabilities.yaml` est mis à jour et que `pnpm site:sync && pnpm site:check` s'exécute
**Then** toute capacité Desktop dont `100 %` des specs associées sont vertes passe à `verification: runtime` (`verified_at` à jour, `e2e_remediation_ref` supprimé), **`CAP-042` reste honnêtement en `verification: failed_e2e` avec `e2e_remediation_ref: "ACTION_ITEM-23.6"`**, toute autre capacité encore en échec éventuel reste en `failed_e2e`, et `pnpm site:check` ainsi que `tests/unit/test_uj_e2e_coverage_gate.py` passent à `0` erreur.

---

### Story 23.8: Clôture Epic 23, Bilan Conditionnel (`52/52` PASS Desktop & `0` `P0`/`P1` $\rightarrow$ Sans Epic 24 Vide) & Éventuelle Initialisation Epic 24

As a Tech Lead (`Amelia`) & Architecte (`Winston`),
I want évaluer la condition de sortie de `Story 23.7` sur `--project=desktop-cockpit` (`52/52` PASS Desktop et `0` écart `P0`/`P1` dans `synthese-remediation-sally-winston-epic-23.md`) afin de clôturer directement l'Epic 23 (`epic-23: done`) **sans créer d'Epic 24 artificiel vide** lorsque le nominal est atteint (avec `CAP-042` rattachée à `ACTION_ITEM-23.6`), et n'activer le workflow d'initialisation de l'**Epic 24** (rapports Tech Lead `24-1..24-K`, `sprint-change-proposal-2026-11-19-epic-24-remediation-plan.md`, `tests/unit/test_epic23_to_epic24_traceability.py`) **que si** un échec Desktop (`> 0`) ou un écart `P0`/`P1` (`> 0`) subsiste en `Story 23.7`,
So that l'Epic 23 se clôture proprement sans dette bureaucratique tout en garantissant `100 %` de traçabilité si un reliquat réel devait être traité en Epic 24 (`GEMINI.md` § Policy, `AD-17`).

**Dépendances :** Dépend de `Story 23.7`. Clôture l'Epic 23.
**CAP couvertes :** `none (gouvernance documentaire & clôture Epic 23 — rattache CAP-042 à ACTION_ITEM-23.6 et, uniquement si échec Desktop ou écart P0/P1 résiduel, initialise Epic 24)` — classification : `doc`.
**Fichiers impactés :** `docs/implementation-artifacts/sprint-status.yaml` (`23-8-...: done`, `epic-23: done`), `docs/implementation-artifacts/tech-lead-reports/23-8-...-tech-lead-report.md` (+ `README.md`), `docs/product/capabilities.yaml`, `tests/unit/test_epic22_to_epic23_traceability.py` *(et uniquement si reliquat `P0`/`P1` ou échec Desktop > 0 : `24-1..24-K`, `sprint-change-proposal-2026-11-19-epic-24-remediation-plan.md`, `epics.md` `Epic 24`, `test_epic23_to_epic24_traceability.py`)*.
**Rapport Tech Lead :** `docs/implementation-artifacts/tech-lead-reports/23-8-rapports-tech-lead-plan-correction-global-et-initialisation-epic-24-tech-lead-report.md`.

**Acceptance Criteria:**

**Given** la `Story 23.7` achevée avec **`52/52` PASS Desktop (`0` failed, `0` timedOut, `3` skipped `mobile-only`)** et **`0` écart `P0`/`P1`** dans `synthese-remediation-sally-winston-epic-23.md`
**When** `Story 23.8` vérifie la traçabilité finale et clôture l'Epic 23
**Then** `epic-23` passe à `done`, `CAP-042` reste proprement rattachée à `ACTION_ITEM-23.6`, **aucun Epic 24 artificiel vide n'est créé**, et `test_epic22_to_epic23_traceability.py`, `check_implementation_docs.py` ainsi que `pnpm site:sync && pnpm site:check` passent à `0` erreur.

**Given** un éventuel échec Desktop (`> 0`) ou écart `P0`/`P1` (`> 0`) constaté dans `bilan-execution-tests-e2e-epic-23.md` ou `synthese-remediation-sally-winston-epic-23.md`
**When** le Tech Lead exécute l'analyse d'impact GitNexus (`repo: "/home/romain/Documents/Projects/ORCIA"`) sur les symboles concernés
**Then** tous les constats sont regroupés en `K` lots cohérents (`Story 24.1`..`Story 24.K`) dotés chacun d'un rapport Tech Lead pré-implémentation (`24-1..24-K`), du plan directeur `sprint-change-proposal-2026-11-19-epic-24-remediation-plan.md`, de l'initialisation complète dans `epics.md`/`sprint-status.yaml`/`capabilities.yaml` et de `tests/unit/test_epic23_to_epic24_traceability.py`, avec `100 %` de traçabilité bidirectionnelle avant passage de `epic-23: done`.

---
