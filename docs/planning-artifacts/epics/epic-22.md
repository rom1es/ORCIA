## Epic 22: Remédiation E2E Vérité PostgreSQL 18, Portails & Shell Direction C, Purge Jargon, Gardes CI, Assainissement Fail-Closed, Campagne Intégrale & Initialisation Epic 23 (`Stories 22.1`..`22.10` + `22.8a`)

Résoudre de manière ordonnée et définitive les **`34` chantiers de l'audit croisé Sally × Winston (`REM-01` .. `REM-34`)** et les **`47` scénarios E2E en échec ou timeout (`14 / 24` specs)** identifiés à l'issue de la campagne Epic 21, afin d'éliminer tout silo mémoire RAM (« Dual-Stack »), restaurer la conformité Direction C (`8` menus, Mobile Companion `< 768px`, aide contextuelle dynamique sans jargon ni faux exemples, Cockpit `<= 3` blocs), verrouiller la non-régression par `5` gardes CI automatisées + `4` verrous anti-faux-positifs + `100 %` d'assertions `SELECT` PostgreSQL 18 sur les `55` blocs `test(...)` E2E avec purge `ORCIA_E2E_SEED_FIXTURES` et relecture à froid PG18 (`22.8`), assainir *Fail-Closed* `vitest.setup.ts`, valider le Composition Root `create_app()` sans `dependency_overrides` ni `app.state.*` manuel et activer la CI GitHub Actions complète à `5` couches (`22.8a`), exécuter la campagne intégrale `e2e-campaign-epic-22` avec captures PNG finales, bilan factuel, audit croisé **Sally × Winston** et mise à jour honnête de `capabilities.yaml` (`22.9`), puis produire les rapports Tech Lead individuels, le plan de correction global et l'initialisation complète de l'**Epic 23** pour traiter tout reliquat ou amélioration (`22.10`).

> **Référentiel directeur :** `docs/planning-artifacts/sprint-change-proposal-2026-11-18-epic-22-remediation-plan.md` — chaque Story dispose de son rapport Tech Lead pré-implémentation individuel dans `docs/implementation-artifacts/tech-lead-reports/22-1-*` .. `22-10-*` (y compris `22-8a-*` et le rapport d'analyse des causes racines `2026-11-18-rca-epic-21-enrichissement-22-8-et-story-22-8a-tech-lead-report.md`).

### Story 22.1: Socle Identité UUIDv7 Workspaces, Permissions `PLATFORM_ADMIN` & Fin du Mode Dégradé `marc` / Bypass PG (`REM-01`, `REM-02`, `REM-07`)

As a Administrateur Plateforme, Chef d'Équipe & Développeur (`Karim`, `Marc`, `Amelia`),
I want unifier l'identité des espaces de travail sur l'`UUIDv7` réel retourné par PostgreSQL 18 avec propagation exacte du `slug`, corriger l'évaluation `MatrixPermissionEvaluator` afin qu'un `PLATFORM_ADMIN` ne soit pas rétrogradé à tort en `READ_ONLY_OBSERVER` (`HTTP 403`) sur ses nouveaux espaces `STANDARD`, et purger l'identité `"marc"` codée en dur ainsi que le drapeau `ORCIA_DISABLE_PG_BOOTSTRAP_SYNC`,
So that toute création d'espace, rattachement de source, évaluation de Gate ou exécution réflexive persiste en PostgreSQL 18 avec son identifiant canonique sans jamais recevoir de faux rejet `403`/`404` ni masquer d'erreur (`FR-3`, `FR-21`, `FR-23`, `FR-28`, `AD-1`, `AD-6`, `AD-19`, `UJ-5`, `UJ-6`, `UJ-9`, `UJ-14`, `UJ-17`, `UJ-18`).

**Dépendances :** Vague 0 (socle transverse prioritaire). Précède Stories `22.3`, `22.4`, `22.5`.
**REM couverts :** `REM-01`, `REM-02`, `REM-07`.
**CAP ancrées (`failed_e2e`) :** `CAP-011`, `CAP-022`, `CAP-050`, `CAP-067`, `CAP-072`, `CAP-076`, `CAP-080`, `CAP-180`.
**Fichiers impactés :** `apps/web/src/components/platformSetupStore.tsx`, `apps/web/src/features/cockpit/*`, `packages/orcia-core/src/orcia_core/permissions/evaluator.py`, `packages/orcia-core/src/orcia_core/bootstrap/_internal/sql_platform_setup_relational_sync.py`, `apps/api/src/orcia_api/routers/*`, `apps/api/src/orcia_api/dependencies/portal_and_assistant.py`.

**Acceptance Criteria:**

**Given** un utilisateur qui crée une BU, une équipe et un espace (ex. `slug: 'espace-e2e-compta'`) depuis l'UI ou l'API
**When** `POST /api/v1/workspaces` et `platformSetupStore.createWorkspace` s'exécutent
**Then** aucun identifiant synthétique `"ws-1"` / `"ws-${len+1}"` ni `.catch(() => undefined)` n'est utilisé : l'API retourne l'`UUIDv7` PostgreSQL 18 et persiste exactement `input.slug` dans `workspaces` (`SELECT id, slug FROM workspaces` retrouve l'espace après `F5`), et le rattachement d'une source `SOURCE_CODE` (`/api/v1/workspaces/{uuid}/datasources`) persiste dans `workspace_datasources` sans `404` ni contournement `ws-\d+`.

**Given** un `PLATFORM_ADMIN` agissant sur un espace `STANDARD` fraîchement créé (sans header `X-Orcia-Access-Mode: READ_ONLY_OBSERVER`)
**When** il appelle `POST /api/v1/gates/deterministic/evaluate` ou `POST /api/v1/executions/reflexive`
**Then** un `WorkspaceMembershipEntity` propriétaire est enregistré pour le créateur/admin sur l'UUID réel PG18, `MatrixPermissionEvaluator.resolve_workspace_access` maintient un accès contributeur/admin autorisé (n'appliquant `READ_ONLY_OBSERVER` que sur `CONFIDENTIAL_RESTRICTED` sans délégation ou sur header explicite), et les requêtes réussissent (`HTTP 200`/`201`) tout en conservant `403 ERR_OBSERVER_MODE_READ_ONLY` pour un véritable observateur.

**Given** le Cockpit, le Composition Root et les routeurs FastAPI
**When** l'application démarre en dehors des harnais de tests unitaires
**Then** `CockpitHumanLedGovernanceSection` et `cockpit/index.tsx` utilisent exclusivement l'identité JWT session issue de `useAuthSessionStore` (`0` occurrence `"marc"`), `get_accostage_service` lit `orcia_env`/`bootstrap_token` depuis les settings injectés, et `ORCIA_DISABLE_PG_BOOTSTRAP_SYNC` est totalement supprimé des routeurs (`HTTP 503` fail-fast si PG18 absent).

---

### Story 22.2: Portals Modales `OrciaDialog`, Compilation Tailwind v4, Purge `display: none`, Découplage `/catalog`/`/agents`/`/help`, Bouton Invitation & Alignement `data-testid`/Contrats (`REM-03`, `REM-04`, `REM-05`, `REM-06`, `REM-16`, `REM-24`, `REM-25`)

As a Utilisateur, Administrateur & QA (`Karim`, `Alice`, `Sally`),
I want unifier 100 % des modales derrière `<OrciaDialog>` (`DialogPrimitive.Portal`) avec Tailwind CSS v4 compilé et footer sticky, purger les `4` wrappers `style={{ display: "none" }}`, découpler `/catalog`, `/agents` et `/help`, exposer explicitement le bouton d'invitation sur `/organization` et aligner les `data-testid` et le payload `plaintext_value`,
So that aucune modale ne soit coupée par Zone 4 ou le bord bas d'écran, qu'aucun doublon DOM ni panneau caché ne bloque les parcours utilisateur et que les contrats UI/API soient rigoureusement alignés (`FR-1`, `FR-20`, `FR-21`, `FR-31`, `FR-32`, `FR-34`, `FR-35`, `AD-22`, `UJ-5`, `UJ-9`, `UJ-13`..`UJ-20`).

**Dépendances :** Vague 0. Complémentaire à `Story 22.1`.
**REM couverts :** `REM-03`, `REM-04`, `REM-05`, `REM-06`, `REM-16`, `REM-24`, `REM-25`.
**CAP ancrées (`failed_e2e`) :** `CAP-001`, `CAP-002`, `CAP-010`, `CAP-041`, `CAP-051`, `CAP-052`, `CAP-053`, `CAP-054`, `CAP-058`, `CAP-063`, `CAP-064`, `CAP-066`, `CAP-069`, `CAP-081`, `CAP-082`, `CAP-084`, `CAP-092`, `CAP-140`, `CAP-190`, `CAP-200`, `CAP-203`.
**Fichiers impactés :** `apps/web/vite.config.ts`, `packages/ui/src/styles/tokens.css`, `packages/ui/src/primitives/{RadixDesignSystemPrimitives,UserSettingsModalDialog,AiModelConfigModal,FourZoneSidebarRail}.tsx`, `apps/web/src/router.tsx`, `apps/web/src/components/{ShellContainer,SettingsOrganizationUnitsBlock}.tsx`, `apps/web/src/features/{catalog,workspaces,inbox}/index.tsx`, `apps/web/src/routes/{help,settingsAiModelsPresets}.ts*`, `WorkflowStudioHeaderBar.tsx`, `apps/web/e2e/20-process-studio-v2-finops-and-log-sink.spec.ts`.

**Acceptance Criteria:**

**Given** `apps/web/vite.config.ts` et `packages/ui`
**When** n'importe quelle modale (`UserSettingsModalDialog`, `FirstBootAdminSetupModal`, `AiModelConfigModal`, `UpstreamChallengeRewindModal`) s'ouvre sur Desktop `1440×900` ou Mobile `390×844`
**Then** `@tailwindcss/vite` compile les classes utilitaires (`@source "../../packages/ui/src"`), les tokens `--z-overlay: 1000` / `--z-dialog: 1010` s'appliquent, la modale monte via `OrciaDialog` (`DialogPrimitive.Portal` dans `document.body`) au-dessus de Zone 4 (`four-zone-contextual-help-column`), son corps défile dans `max-height: min(90vh, 760px)` avec un footer sticky visible (`Annuler` / `Enregistrer`), et `AiModelConfigModal` n'affiche aucune erreur de clé API avant saisie/soumission.

**Given** les vues `/catalog`, `/agents`, `/spaces`, `/workspaces/$wsId` et `/help`
**When** l'utilisateur navigue vers chacune de ces routes
**Then** les `4` wrappers `style={{ display: "none" }}` (`features/catalog`, `features/workspaces`, `InboxAuxiliaryPanels`, `FourZoneSidebarRail`) sont supprimés ; `/catalog` affiche `CatalogExplorerPanel` visible (`catalog-explorer-panel`) ; `/agents` onglet MCP ne monte qu'**une seule** instance de `RemoteServiceTestBenchAndMcpExposureView` ; `/workspaces/$wsId` affiche `DnaStarlarkCompilerAndGlossaryLifecycleView` visible dans son onglet et persiste les waivers (`workspace_exception_waivers`) en PG18 ; et `/help` masque `<ShellContextualHelpColumn>` dans Zone 4 (`1` seule instance `contextual-help-hybrid-panel`), ouvre `help-accordion-steps-content` sur mobile et applique `pl-5` sur les puces.

**Given** l'écran `/organization`, la modale Modèles IA, le Studio V2 et le test `20-process-studio` #2
**When** l'utilisateur ou le test accède à ces contrôles
**Then** `open-invite-org-user-modal-btn` est toujours rendu sur `/organization` (invitation racine autorisée ou état explicite), `settingsAiModelsPresets.ts` expose `llm-provider-preset-ollama`, `WorkflowStudioHeaderBar.tsx` expose `studio-view-mode-whatif` (avec libellés distincts), et `20-process-studio` #2 envoie `SecretInputPayload.plaintext_value` conforme au contrat OpenAPI (`HTTP 201`).

---

### Story 22.3: Persistance PG18 Assistant (`assistant_folders`), Notifications (`task_notifications`, `/inbox`, SSE) & Permission Broker (`permission_broker_tickets`, fallback `git://*`) (`REM-08`, `REM-10`, `REM-13`)

As a Utilisateur, Collaborateur d'Équipe & Développeur (`Nadia`, `Lucas`, `Marc`),
I want persister en PostgreSQL 18 les dossiers collaboratifs de Mon Assistant (sans fuite de prompt interne `[LAYER_5_*]`), les notifications d'équipe + baux de ressources (`task_notifications`, `resource_leases`) couplés au SSE `< 500 ms` sur `/inbox`, et les tickets du Permission Broker (`permission_broker_tickets`) avec politique socle fallback pour `git://*`,
So that toute création de dossier, prise en charge multi-acteurs et interception d'accès survive au redémarrage de l'API et au `F5` (`FR-2`, `FR-22`, `FR-33`, `AD-1`, `AD-4`, `AD-6`, `NFR-PERF-2`, `NFR-REL-1`, `UJ-4`, `UJ-7`, `UJ-14`, `UJ-17`).

**Dépendances :** Dépend de `Story 22.1` et `Story 22.2`.
**REM couverts :** `REM-08`, `REM-10`, `REM-13`.
**CAP ancrées (`failed_e2e`) :** `CAP-003`, `CAP-040`, `CAP-043`, `CAP-070`, `CAP-071`, `CAP-073`, `CAP-074`, `CAP-075`.
**Fichiers impactés :** `packages/orcia-core/src/orcia_core/orchestration/{assistant_folders_and_sharing,_internal/sql_assistant_folders,_internal/sql_task_notifications}.py`, `packages/orcia-core/src/orcia_core/permissions/{broker,seeds,_internal/sql_permission_broker}.py`, `apps/api/src/orcia_api/dependencies/{core_and_lifespan,portal_and_assistant}.py`, `apps/api/src/orcia_api/routers/{assistant_workspace_folders,inbox_and_leases,permission_broker}.py`.

**Acceptance Criteria:**

**Given** un utilisateur créant un dossier ou une note épinglée dans `/assistant`
**When** `POST /api/v1/assistant/folders` s'exécute puis que l'API redémarre et le navigateur exécute `F5`
**Then** l'adaptateur SQLAlchemy Asyncio écrit et relit dans `assistant_folders`, `assistant_threads` et `assistant_folder_shares` (`SELECT` PG18 retrouve le dossier), et la balise `[LAYER_5_FOLDER_CONTINUITY ...]` reste confinée à l'assemblage interne `AssistantHarness` sans jamais apparaître dans `pinned_notes` ni dans l'UI.

**Given** deux acteurs `A` et `B` sur `/inbox` ou `POST /api/v1/tasks/{id}/claim`
**When** `A` prend en charge une notification d'équipe puis `B` tente la même action
**Then** `SqlTaskNotificationRepository` et `SqlResourceLeaseRepository` persistent l'état `CLAIMED` dans `task_notifications` et `resource_leases` en PG18 tout en maintenant le verrou Redis `SET NX` et la diffusion SSE `< 500 ms`, `B` reçoit `HTTP 409`, et `/inbox` affiche la boîte de réception réelle sans redirection erronée vers `/assistant`.

**Given** un accès refusé ou testé via `POST /api/v1/permissions/broker/check-access` avec `target_uri: "git://gitlab.internal/platform/infra-core"`
**When** le `PermissionBrokerService` évalue la requête
**Then** la politique fallback configurable (`git://*`, `jira://*`, `confluence://*`) ou la fiche `workspace_datasources` est résolue (`HTTP 200`, zéro `404`), un ticket est persisté dans `permission_broker_tickets` (`SELECT` PG18 `>= 1` ligne) et l'UI affiche la carte ambre de procédure (`UX-DR11`) avec lien Jira et action de replay.

---

### Story 22.4: Persistance PG18 Orchestration (`dbos_uow`, `human_anchor_signatures`, `upstream_challenges`, `run_lock_manifests`), Gates (`gate_evaluations`, `chunk_approvals`) & Garde `KILL_SWITCH_STOPPED` (`REM-09`, `REM-11`, `REM-12`)

As a Tech Lead, Architecte, Valideur & Superviseur (`Yanis`, `Antoine`, `Claire`, `Sophie`),
I want initialiser `app.state.dbos_uow` et persister dans PostgreSQL 18 les ancres humaines (`human_anchor_signatures`), challenges amont (`upstream_challenges`), verrous de version (`run_lock_manifests`), évaluations de Gates (`gate_evaluations`, `chunk_approvals`), monter `<UpstreamChallengeRewindModal>` avec séparation stricte `/gates` vs `/processes`, et protéger `KILL_SWITCH_STOPPED` dans `_sql_autonomous_rollback.py`,
So that tout cycle d'orchestration durable, contestation What-If, validation par découpage et arrêt d'urgence survive au redémarrage de l'API et au `F5` avec une traçabilité SQL complète (`FR-4`..`FR-7`, `FR-14`..`FR-19`, `FR-29`, `AD-2`, `AD-3`, `AD-7`, `AD-11`, `AD-18`, `UJ-1`..`UJ-3`, `UJ-5`, `UJ-6`, `UJ-11`, `UJ-12`).

**Dépendances :** Dépend de `Story 22.1` et `Story 22.2`.
**REM couverts :** `REM-09`, `REM-11`, `REM-12`.
**CAP ancrées (`failed_e2e`) :** `CAP-020`, `CAP-021`, `CAP-023`, `CAP-024`, `CAP-030`, `CAP-031`, `CAP-032`, `CAP-033`, `CAP-201`.
**Fichiers impactés :** `apps/api/src/orcia_api/dependencies/core_and_lifespan.py`, `apps/api/src/orcia_api/routers/{orchestration,blackboard_and_engine,challenge_and_replay,gates,human_gates}.py`, `packages/orcia-core/src/orcia_core/orchestration/_internal/{sql_repository,_sql_autonomous_rollback}.py`, `packages/orcia-core/src/orcia_core/gates/_internal/sql_gate_repository.py`, `apps/web/src/features/{cockpit,gates}/*`.

**Acceptance Criteria:**

**Given** un run instancié depuis le Cockpit puis signé sur une ancre violette (`>= 30` car.) et contesté via `<UpstreamChallengeRewindModal>`
**When** les mutations `POST /anchors/sign`, `POST /challenges` et `POST /replay` s'exécutent puis la page est rechargée (`F5`)
**Then** `app.state.dbos_uow` est initialisé dans `core_and_lifespan.py`, `human_anchor_signatures`, `run_lock_manifests`, `workflow_runs`, `step_executions`, `blackboard_snapshots` (append-only `ACTIVE`/`SUPERSEDED`) et `upstream_challenges` contiennent les lignes persistées en PG18, `get_orchestration_state` relit depuis PG18, et `UpstreamChallengeRewindModal` est monté et interactif (`upstream-challenge-reason-input` visible).

**Given** une Gate Déterministe, Agentique ou Humaine ouverte sur `/gates`
**When** le valideur inspecte le Briefing 4 blocs, approuve les sections par découpage (`chunk_approvals`) avec contrôle `< 15 s`, ou déclenche l'action Jira Staged puis rafraîchit (`F5`)
**Then** `/gates` affiche la vue dédiée aux Gates (sans empiler `Mes Processus` ni son formulaire permanent), et `SqlGateEvaluationRepository` persiste les évaluations et approbations dans `gate_evaluations` et `chunk_approvals` en PG18.

**Given** un run autonome arrêté d'urgence (`KILL_SWITCH_STOPPED`) et un second run audité post-hoc (`invalidate-and-restore`)
**When** `restore_help_article_and_rollback_run_sql` (`_sql_autonomous_rollback.py`) s'exécute
**Then** la clause `AND status <> 'KILL_SWITCH_STOPPED'` interdit l'écrasement d'un run stoppé par kill-switch, et le `SELECT status FROM workflow_runs WHERE status = 'KILL_SWITCH_STOPPED'` après `F5` retrouve bien la ligne arrêtée.

---

### Story 22.5: Persistance PG18 Packs Déclaratifs (`declarative_pack_bundles`) & Parcours Wizards Durables (`wizard_sessions`) (`REM-14`, `REM-15`)

As a Administrateur Plateforme & Concepteur de Packs (`Karim`, `Marc`),
I want synchroniser les manifests YAML dans `declarative_pack_bundles` au démarrage et à l'export dans `packs.py`, et raccorder intégralement `/wizards` (`DurableOnboardingWizardService` + `routes/wizards.tsx` via `@orcia/api-client`) à `wizard_sessions` tout en supprimant la triple numérotation et `sdlc_tech_lead`,
So that les bundles de packs déclaratifs et la progression des wizards survivent au redémarrage et au `F5` avec une ergonomie propre au-dessus de la ligne de flottaison (`FR-11`, `FR-28`, `FR-31`, `FR-34`, `FR-35`, `AD-1`, `AD-20`, `NFR-REL-1`, `UJ-19`).

**Dépendances :** Dépend de `Story 22.1` et `Story 22.2`.
**REM couverts :** `REM-14`, `REM-15`.
**CAP ancrées (`failed_e2e`) :** `CAP-055`, `CAP-056`, `CAP-057`, `CAP-150`.
**Fichiers impactés :** `packages/orcia-core/src/orcia_core/bootstrap/{durable_wizards,_internal/sql_wizard_sessions,_internal/sql_declarative_packs}.py`, `apps/api/src/orcia_api/dependencies/core_and_lifespan.py`, `apps/api/src/orcia_api/routers/{packs,studio_and_wizards}.py`, `apps/web/src/routes/wizards.tsx`, `packages/ui/src/primitives/DurableWizardRunnerView.tsx`.

**Acceptance Criteria:**

**Given** le démarrage du serveur FastAPI et la page `/settings/packs`
**When** les packs `packs/<domaine>/pack.yaml` sont chargés ou exportés en ZIP (`packs.py`)
**Then** un upsert idempotent (`INSERT ... ON CONFLICT DO UPDATE`) persiste les bundles et empreintes `SHA-256` dans `declarative_pack_bundles` (`SELECT COUNT(*) FROM declarative_pack_bundles >= 1` après `F5`).

**Given** l'utilisateur ouvrant `/wizards` et avançant/reculant dans un parcours guidé jusqu'à l'achèvement
**When** il interagit avec les étapes puis recharge la page (`F5`)
**Then** `routes/wizards.tsx` appelle `@orcia/api-client` (`GET`/`POST /api/v1/wizards/*`) sans état `useState` purement local, `DurableOnboardingWizardService` lit/écrit dans `wizard_sessions` PG18, `wizard-completed-badge` s'affiche après `F5`, l'identifiant brut `sdlc_tech_lead` est remplacé par son libellé métier traduit, la triple numérotation `1. #1/5 1.` est supprimée, et l'étape active apparaît au-dessus de la ligne de flottaison.

---

### Story 22.6: Coquille Direction C `8` Entrées, Mobile Companion `< 768px`, Aide Contextuelle Dynamique par Route (`docs/help/`) & Cockpit `<= 3` Blocs (`REM-17`, `REM-18`, `REM-19`, `REM-20`, `REM-21`)

As a Utilisateur Desktop & Mobile Companion (`Claire`, `Nadia`, `Marc`, `Sally`),
I want aligner la coquille sur les `8` entrées de `DESIGN.md` avec Double Sélecteur + Fil d'Ariane et état actif exact, câbler le `MobileCompanionView` (`< 768px`) avec barre basse `3` onglets + réponse SSE visible et fin des faux positifs `overflow-x: hidden`, servir une aide contextuelle dynamique par route sans `Chef1`/`aqwZSX`, et ramener le Cockpit à `<= 3` blocs réhydratés depuis PG18 sans `"LOCK TABLE..."`,
So that l'expérience globale Desktop et Mobile soit conforme à Direction C (`DESIGN.md` / `EXPERIENCE.md`) sur 100 % des écrans, y compris ceux précédemment `PASSED` (`FR-1`, `FR-3`, `FR-28`, `FR-32`, `FR-33`, `UX-DR1`, `UX-DR2`, `UX-DR13`, `UX-DR16`, `NFR-A11Y-1`, `UJ-8`, `UJ-13`, `UJ-14`, `UJ-17`, `UJ-20`).

**Dépendances :** Dépend de `Stories 22.1`..`22.5`.
**REM couverts :** `REM-17`, `REM-18`, `REM-19`, `REM-20`, `REM-21`.
**CAP ancrées (`failed_e2e`) :** `CAP-068` (+ conformité transverse `CAP-042`, `CAP-060`, `CAP-061`, `CAP-064`, `CAP-065`, `CAP-067`, `CAP-071`, `CAP-074`, `CAP-075`, `CAP-200`, `CAP-203`).
**Fichiers impactés :** `packages/ui/src/primitives/{FourZoneDirectionCShell,FourZoneSidebarRail,FourZoneTopHeaderSection,MobileCompanionView,ProgressiveDay0AccostageBanner,StreamlinedCockpitView,AssistantSpeedSelectorAndStreamView}.tsx`, `packages/ui/src/styles/tokens.css`, `apps/web/src/components/{ShellContextualHelpColumn,_contextualHelpSections,shellPresets,shellScopeOptions}.ts*`, `packages/orcia-core/src/orcia_core/catalog/contextual_help.py`, `docs/help/{fr,en}/*.md`.

**Acceptance Criteria:**

**Given** un viewport Mobile (`390×844`, `< 768px`)
**When** `FourZoneDirectionCShell` rend la coquille via `useResponsiveBreakpoint()`
**Then** la sidebar rail gauche disparaît au profit d'une barre basse fixe à `3` onglets (`Cockpit`, `Mon Assistant / Arbitrage`, `Décisions`), la `TopHeaderBar` tient sur `1` ligne (`min-w-0`), les routes Desktop-only (`/settings`, `/organization`, `/processes/studio/*`) affichent la bannière dédiée, aucun `<select>` ou bouton ne déborde hors de `390px` (y compris `/activity` et `/cockpit`), et dans `/assistant` la réponse streamée reste visible au-dessus d'un compositeur à `2` lignes propres.

**Given** la navigation Desktop dans `FourZoneSidebarRail` et `FourZoneTopHeaderSection`
**When** l'utilisateur parcourt les écrans (`Cockpit`, `/profile`, `/help`, `/finops`, `/spaces`, `/settings`)
**Then** la sidebar affiche strictement les `8` entrées de `DESIGN.md` (`Cockpit`, `Mon Assistant`, `Mes Processus`, `Mes Agents`, `Mes Espaces`, `FinOps`, `Configuration`, `Aide`), le Double Sélecteur empilé (`Équipe / BU` + `Espace`) figure en tête de sidebar, le Breadcrumb cliquable figure dans `TopHeaderBar`, et `Cockpit` n'est plus surligné à tort sur `/profile` ou `/help`.

**Given** la colonne droite d'aide contextuelle (`340px`) et le Cockpit post-admin
**When** l'utilisateur change de route ou clique sur un bouton `ⓘ`, ou observe le Cockpit après création de `Alice Admin E2E`
**Then** `contextual_help.py` et `docs/help/{fr,en}/*.md` servent une fiche dédiée à la route active (format 4 sections, zéro `Chef1`/`aqwZSX`, zéro blocage sur `@1.1.0`), `ProgressiveDay0AccostageBanner` reflète fidèlement PG18 (`Étape 1` cochée/repliée après création admin, `Étape 2` décochée si `0` `org_units`, libellé explicite `Accostage X/5`, zéro `"LOCK TABLE users IN EXCLUSIVE MODE"`), et le Cockpit ne dépasse pas `3` blocs majeurs.

---

### Story 22.7: Finitions UX/UI (Compteurs `0`/Modales, Erreurs RFC 9457 Actionnables, Grilles, Studio V2, Assistant/`⌘K`, Devise `€`/Dates FR, Contraste `(!)`) & Purge Intégrale du Jargon Technique (`REM-22`, `REM-23`, `REM-26`, `REM-27`, `REM-28`, `REM-29`, `REM-30`, `REM-31`, `REM-32`)

As a Utilisateur Métier, Auditeur & Responsable UX (`Sally`, `Claire`, `Yanis`),
I want masquer les compteurs à `0` et convertir les formulaires permanents en modales `+ Nouveau...`, afficher des bannières RFC 9457 actionnables sur toute erreur HTTP, purger intégralement le jargon technique et les constantes brutes de l'UI/SSE, unifier l'affichage sur `€` et les dates FR, corriger les grilles `/finops`/`/profile`/`/ontology`/Studio/`/agents` MCP/`/assistant`/`⌘K`, et retirer les pastilles rouges `(!)` des boutons primaires bleus,
So that chaque écran d'ORCIA atteigne un niveau irréprochable d'ergonomie, de contraste WCAG 2.2 AA et de langage métier sans aucun terme d'implémentation (`FR-25`, `FR-26`, `FR-32..FR-36`, `NFR-A11Y-1`, `NFR-OBS-1`, `UX-DR1`, `UX-DR11`, `UX-DR12`, `UJ-1`..`UJ-20`).

**Dépendances :** Dépend de `Story 22.6`.
**REM couverts :** `REM-22`, `REM-23`, `REM-26`, `REM-27`, `REM-28`, `REM-29`, `REM-30`, `REM-31`, `REM-32`.
**CAP impactées (transverse UX) :** `CAP-002`, `CAP-003`, `CAP-010`, `CAP-023`, `CAP-030`, `CAP-051`, `CAP-052`, `CAP-054`, `CAP-060`, `CAP-062`, `CAP-065`, `CAP-069`, `CAP-073`, `CAP-075`, `CAP-080`, `CAP-082`, `CAP-083`, `CAP-090`, `CAP-091`, `CAP-100`, `CAP-140`, `CAP-150`, `CAP-160`, `CAP-200`, `CAP-201`.
**Fichiers impactés :** `apps/web/src/i18n/locales/*.ts`, `packs/*/help/**/*.md`, `packages/ui/src/primitives/{AssistantThinkingSubWindow,WorkflowStudioHeaderBar,StudioCopilotSidebar,RemoteServiceTestBenchAndMcpExposureView,FinopsGovernanceDashboardView,UserProfileOverviewPage,CommandPaletteModal,AgentExecutionTrace}.tsx`, `packages/ui/src/components/DisabledButtonAlertIndicator.tsx`, `apps/web/src/features/*`.

**Acceptance Criteria:**

**Given** les vues `/processes`, `/gates`, `/agents`, `/spaces`, `/profile` et toute mutation `@orcia/api-client` en erreur (`403`/`404`/`422`)
**When** les collections sont vides (`total === 0`) ou qu'une requête échoue côté API
**Then** les badges/compteurs `0` sont masqués, la création de processus ou d'espace passe par une modale `<OrciaDialog>` (`+ Nouveau processus` / `+ Nouvel espace`), et toute erreur HTTP déclenche `<OrciaAlertBanner>` traduite depuis le RFC 9457 en français métier actionnable (zéro échec silencieux).

**Given** les dictionnaires `i18n`, `packs/*/help/**/*.md`, `AssistantThinkingSubWindow` et `AgentExecutionTrace`
**When** l'utilisateur parcourt l'ensemble de l'application (y compris les traces réflexives `12-epic16`, l'arbitrage `19-orchestration`, `/settings/packs`, `/finops`, `/ontology` et `/spaces`)
**Then** aucune constante brute ou jargon interne (`SYNTHESIS_READY`, `OAUTH2_PASSTHROUGH`, `TECH_LEAD`, `IMMUTABLE`, `PAUSE_AND_ESCALATE`, `OPT_A_*`, `OPT_B_*`, `PENDING`, `Vitesse 2 (450 ms)`, `DeclarativePackLoader`, `orcia-connectors`, `WritePreviewCard`, `packs/<domaine>/`, `Tier cognitif`, `Guardrails`, `Dry-Run`, `AES-256-GCM`, `1024-dim RAG`, `demande_source`, `(published)`/`(draft)`, `[STALE_WARNING]`, routes brutes) n'apparaît à l'écran ; toutes les sommes utilisent `€` et toutes les dates utilisent `Intl.DateTimeFormat(locale)` (`jj/mm/aaaa`).

**Given** les grilles, Studio V2, `/agents` MCP, `/assistant`, `⌘K` et les boutons primaires désactivés
**When** ils sont rendus sur `1440×900`
**Then** `/finops` (`4` KPIs + onglets 1 ligne), `/profile` (`2×2` ou `4×1`) et `/ontology` (`2×2`) sont équilibrés ; Studio V2 supprime le doublon de version et le débordement de `Demander` ; `/agents` MCP supprime le vide gauche ; `+ Nouvelle conversation` est stylé en bouton secondaire, le pavé central est déporté vers `ⓘ`, `⌘K` masque les sections vides ; les titres numérotés et `||` doubles sont retirés ; et `DisabledButtonAlertIndicator` retire la pastille rouge `(!)` des boutons bleus et de l'onglet actif sidebar tout en évitant les troncatures abusives.

---

### Story 22.8: Activation des `5` Gardes CI Anti-Régression + `4` Verrous Anti-Faux-Positifs, Purge `ORCIA_E2E_SEED_FIXTURES` & Relecture à Froid PG18, Couverture `100 %` Assertions SQL sur `55` Blocs `test(...)`, Paramétrage `ORCIA_E2E_CAMPAIGN_DIR` & Budget `< 35s` (`REM-33`, `REM-34`)

As a Tech Lead, Architecte & QA Automation (`Amelia`, `Winston`, `Sally`),
I want activer les `5` gardes automatisées anti-régression en CI (anti-jargon UI, interdiction `display: none`, intégrité CSS Tailwind + tokens Direction C / contraste WCAG AA, interdiction `[LAYER_5_*]` & `ORCIA_DISABLE_PG_BOOTSTRAP_SYNC`, contrôle géométrique Playwright Desktop/Mobile) **et** les `4` verrous anti-faux-positifs issus de la RCA Epic 21 (`e2e-testids-sync-audit.test.ts`, helper Playwright typé OpenAPI `typedApiRequest.ts` + garde statique `e2e-openapi-helper-audit.test.ts`, purge totale de `ORCIA_E2E_SEED_FIXTURES="1"` remplacée par création via API réelle + relecture à froid PostgreSQL 18 `reloadColdFromPg()` via `POST /api/v1/_e2e/evict-memory-caches` actif uniquement si `ORCIA_ENV == "e2e"`, réécriture anti-Goodhart de `zero-dead-buttons-and-silent-catches-audit.test.tsx` sous `<RouterProvider>` réel + sonde `[role="alert"]` anti-échec HTTP silencieux), généraliser les assertions `SELECT` PostgreSQL 18 effectives sur **100 % des `55` blocs `test(...)` E2E (`110` scénarios)** avec `test_e2e_sql_coverage_audit.py`, paramétrer `ORCIA_E2E_CAMPAIGN_DIR` (ciblant `e2e-campaign-epic-22`) dans le harnais, et optimiser les temps d'exécution E2E sous `< 35 s`,
So that aucun test Vitest ou Playwright ne puisse passer à tort sur des `data-testid` orphelins, des payloads non typés, des fixtures pré-injectées ou du cache RAM, tout en préparant `Story 22.8a` puis la campagne intégrale `Story 22.9` et `Story 22.10` (`AD-17`, `NFR-TEST-1`, `NFR-PERF-1`, `NFR-A11Y-1`). *(Note : l'assainissement Fail-Closed de `vitest.setup.ts`, le test Composition Root sans override et la CI GitHub Actions complète sont portés par `Story 22.8a`, la campagne E2E intégrale + captures PNG + audit Sally × Winston + `capabilities.yaml` par `Story 22.9`, et les rapports Tech Lead + initialisation Epic 23 par `Story 22.10`.)*

**Dépendances :** Dépend de `Stories 22.1`..`22.7`. Précède `Story 22.8a`.
**REM couverts :** `REM-33`, `REM-34`.
**CAP couvertes :** `CAP-100` (`hygiène` — durcissement CI, verrous anti-faux-positifs & couverture SQL E2E `100 %` préparant `22.8a` puis `22.9`).
**Fichiers impactés :** `apps/web/src/__tests__/anti-jargon-and-secrets-ui-audit.test.ts`, `apps/web/src/__tests__/no-hidden-legacy-panels-audit.test.ts`, `apps/web/src/__tests__/css-class-integrity-audit.test.ts`, `apps/web/src/__tests__/e2e-testids-sync-audit.test.ts`, `apps/web/src/__tests__/e2e-openapi-helper-audit.test.ts`, `apps/web/src/__tests__/zero-dead-buttons-and-silent-catches-audit.test.tsx`, `apps/web/e2e/support/{layoutGeometryAssertions,e2eCaptureFixture,typedApiRequest}.ts`, `apps/web/playwright.config.ts`, `apps/api/src/orcia_api/routers/` (`_e2e/evict-memory-caches` si `ORCIA_ENV == "e2e"`), `tests/unit/test_no_raw_enum_codes_in_ui_streams.py`, `tests/unit/test_e2e_sql_coverage_audit.py`, `apps/web/e2e/*.spec.ts` (assertions PG18 sur `55/55` blocs `test(...)` et budget `< 35 s`).

**Acceptance Criteria:**

**Given** les `5` gardes CI initiales + les `4` verrous anti-faux-positifs de la Story `22.8`
**When** `pnpm turbo run lint typecheck test` et `.venv/bin/pytest` s'exécutent
**Then** (1) `anti-jargon-and-secrets-ui-audit.test.ts` garantit `0` terme banni dans `i18n`, `_contextualHelpSections.ts`, `packages/ui/src` et `docs/help/` ; (2) `no-hidden-legacy-panels-audit.test.ts` garantit `0` `display: none` sur panneaux métier et `100 %` des `role="dialog"` via `Portal` ; (3) `css-class-integrity-audit.test.ts` vérifie la compilation CSS, la cohérence des tokens Direction C et l'absence de styles inline violant WCAG AA ; (4) `test_no_raw_enum_codes_in_ui_streams.py` garantit `0` `[LAYER_5_*]` dans les DTOs/streams et `0` `ORCIA_DISABLE_PG_BOOTSTRAP_SYNC` hors tests unitaires ; (5) `e2e-testids-sync-audit.test.ts` vérifie que `100 %` des `data-testid` ciblés dans `apps/web/e2e/*.spec.ts` existent dans `apps/web/src/` ou `packages/ui/src/` ; (6) `e2e-openapi-helper-audit.test.ts` interdit les appels `page.request.post/put/patch` bruts au profit de `typedApiRequest.ts` typé sur `packages/api-client` ; (7) `zero-dead-buttons-and-silent-catches-audit.test.tsx` monte les vues sous un `<RouterProvider>` réel sans court-circuit neutre et vérifie les boutons d'action interactifs ; et (8) `layoutGeometryAssertions.ts` vérifie `rect.right <= window.innerWidth + 1`, `elementFromPoint`, la sonde `[role="alert"]` sur toute réponse HTTP `>= 400`, et la conformité Direction C / WCAG AA.

**Given** les `24` specs Playwright (`55` blocs `test(...)` produisant `110` scénarios Desktop `1440×900` + Mobile `390×844`) et le test statique `tests/unit/test_e2e_sql_coverage_audit.py`
**When** l'audit de couverture SQL E2E, la purge `ORCIA_E2E_SEED_FIXTURES` et les ciblages `14-auth` / `16-ai-models` s'exécutent
**Then** `ORCIA_E2E_SEED_FIXTURES="1"` est totalement supprimé de `apps/web/playwright.config.ts` et `apps/web/e2e/`, les mutations E2E exécutent `reloadColdFromPg()` (appelant `POST /api/v1/_e2e/evict-memory-caches` actif uniquement lorsque `ORCIA_ENV == "e2e"` et renvoyant `404` sinon) suivi d'un rechargement de page confirmant la persistance froide PG18, **100 % des `55` blocs `test(...)` E2E (`55/55`)** exécutent au moins une assertion réelle `SELECT` PostgreSQL 18 (`queryPgCount`/`queryPgRows`) adaptée au domaine testé (`test_e2e_sql_coverage_audit.py`), `e2eCaptureFixture.ts` supporte `ORCIA_E2E_CAMPAIGN_DIR`, et les parcours lents (`14-auth` #2, `16-ai-models` #2) sont optimisés sous `< 35 s` (`REM-33`).

**Given** la pyramide Python + TypeScript validée après ces ajouts
**When** `.venv/bin/pytest`, `pnpm turbo run lint typecheck test`, `lint-imports` et `lint_spine.py` s'exécutent
**Then** toutes les vérifications unitaires, statiques et architecturales passent avec `>= 90 %` de couverture unitaire et `0` anomalie, débloquant `Story 22.8a` puis la campagne en `Story 22.9`.

---

### Story 22.8a: Assainissement Fail-Closed de `vitest.setup.ts`, Test Composition Root sans Override & CI GitHub Actions Complète

As a Architecte Plateforme, Tech Lead & DevOps (`Winston`, `Amelia`),
I want découper (`< 350` lignes) et convertir le harnais `apps/web/src/__tests__/vitest.setup.ts` en mode **Fail-Closed** validé dynamiquement contre `packages/api-client/openapi.json` (UUIDv7 stricts sur `format: "uuid"` rejetant `"ws-1"`, validation `required` et `additionalProperties: false`, suppression du fallback catch-all `return jsonResponse({})` au profit d'un rejet explicite), éliminer tout fallback silencieux en mémoire RAM dans `packages/orcia-core` et prouver par un nouveau test d'intégration Couche 2 (`tests/integration/test_composition_root_zero_ram_silo_postgres18.py`) que `create_app()` démarré **sans aucun `dependency_overrides` ni injection manuelle `app.state.*`** persiste et relit les données en PostgreSQL 18 (en nettoyant `app.state.dbos_uow = uow` dans `test_epics_1_7_vertical_sql_wiring_postgres18.py` et en verrouillant par les audits AST `test_integration_no_manual_app_state_audit.py` et `test_zero_orphan_sql_adapters_audit.py`), et déployer les workflows GitHub Actions complets (`.github/workflows/ci.yml` + `.github/workflows/e2e.yml` sharded en `4` shards `--retries=0`, couverture combinée `--cov=packages/orcia-core --cov-fail-under=90` et contrat Shift-Left),
So that aucune désynchronisation de schéma DTO Frontend/Backend, aucun silo RAM caché derrière un mock `app.state` en test d'intégration, ni aucune régression sur les couches `1..5` d'ORCIA ne puisse plus franchir une PR sans échec bloquant (`AD-17`, `AD-19`, `NFR-TEST-1`, `GEMINI.md` §3/§6).

**Dépendances :** Dépend de `Story 22.8` (et `Stories 22.1`..`22.7`). Précède `Story 22.9`.
**CAP couvertes :** Hygiène transverse CI/Testing & `AD-17` (`CAP-100` reste `foundation` / `live` / `runtime`).
**Fichiers impactés :** `apps/web/src/__tests__/vitest.setup.ts` (split `< 350` L + helpers modulaires sous `apps/web/src/__tests__/mocks/`), `packages/api-client/openapi.json`, `packages/orcia-core/src/orcia_core/**` (purge fallbacks RAM résiduels), `tests/integration/test_composition_root_zero_ram_silo_postgres18.py`, `tests/integration/test_epics_1_7_vertical_sql_wiring_postgres18.py`, `tests/unit/test_integration_no_manual_app_state_audit.py`, `tests/unit/test_zero_orphan_sql_adapters_audit.py`, `.github/workflows/ci.yml`, `.github/workflows/e2e.yml`, `docs/testing-strategy.md`.

**Acceptance Criteria:**

**Given** le fichier `apps/web/src/__tests__/vitest.setup.ts` découpé en modules `< 350` lignes adossés à `packages/api-client/openapi.json`
**When** un appel `@orcia/api-client` en test Vitest cible une route inexistante, un champ manquant (`required`), un champ inconnu (`additionalProperties: false`) ou un identifiant invalide comme `"ws-1"` sur un paramètre `format: "uuid"`
**Then** le harnais *Fail-Closed* lève une erreur explicite et fait échouer le test immédiatement (`0` fallback `return jsonResponse({})`), et `pnpm --filter @orcia/web test` + `typecheck` passent à `100 %` sans aucun faux négatif ni court-circuit `isJsdom`.

**Given** le Composition Root réel `create_app()` démarré contre `PostgreSQL 18 + Redis 7.4` (`testcontainers`) sans `app.dependency_overrides` ni injection manuelle `app.state.*`
**When** `tests/integration/test_composition_root_zero_ram_silo_postgres18.py`, `test_epics_1_7_vertical_sql_wiring_postgres18.py` (nettoyé de `app.state.dbos_uow = uow`) et les audits statiques `test_integration_no_manual_app_state_audit.py` + `test_zero_orphan_sql_adapters_audit.py` s'exécutent
**Then** tous les endpoints critiques persistent et relisent à froid depuis PostgreSQL 18 sans aucun silo RAM, `0` fichier dans `tests/integration/` n'injecte manuellement `app.state.*`, et `100 %` des adaptateurs SQL dans `_internal/sql_*.py` ont au moins un appelant actif hors `tests/`.

**Given** les workflows GitHub Actions `.github/workflows/ci.yml` et `.github/workflows/e2e.yml` (`4` shards Playwright `--retries=0`)
**When** la validation complète des workflows et la pyramide locale (`pytest` couverture combinée `--cov=packages/orcia-core --cov-fail-under=90`, `ruff`, `mypy --strict`, `lint-imports`, `pnpm turbo run lint typecheck test`, `lint_spine.py`, `pnpm site:check`) s'exécutent
**Then** la totalité des `5` couches `AD-17` et la couverture combinée `>= 90 %` passent, et la CI bloquante est opérationnelle avant le lancement de la campagne E2E intégrale en `Story 22.9`.

---

### Story 22.9: Campagne E2E Intégrale Vérité PostgreSQL 18, Captures PNG Finales (Succès & Échecs), Bilan & Audit Croisé Sally × Winston

As a UX Designer (`Sally`), Architecte (`Winston`) & Tech Lead (`Amelia`),
I want exécuter l'intégralité de la campagne Playwright E2E (`00..21` + `shell.spec.ts`, `110` scénarios Desktop `1440×900` et Mobile `390×844`) sans aucun retry ni arrêt anticipé (`--retries=0 --max-failures=0 --timeout=35000`) avec `ORCIA_E2E_CAMPAIGN_DIR=docs/implementation-artifacts/e2e-campaign-epic-22`, archiver toutes les captures PNG d'état final (succès et échecs), rédiger le bilan factuel d'exécution, mener l'audit croisé **Sally (UX) × Winston (Architecture)** sur l'ensemble des résultats et captures, et mettre à jour honnêtement `docs/product/capabilities.yaml`,
So that ORCIA dispose d'une preuve runtime exhaustive et vérifiable post-remédiation Epic 22 sur PostgreSQL 18 et identifie sans complaisance tout échec résiduel ou axe d'amélioration UX/Architecture (`AD-17`, `NFR-TEST-1`, `GEMINI.md` §5).

**Dépendances :** Dépend de `Story 22.8` et `Story 22.8a`. Précède `Story 22.10`.
**CAP couvertes :** Vérification runtime réelle de `100 %` des `65` capacités (`62` `feature` + `3` `foundation`, `CAP-001`..`CAP-203`) dans `docs/product/capabilities.yaml`.
**Fichiers impactés :** `docs/implementation-artifacts/e2e-campaign-epic-22/playwright-results.json`, `docs/implementation-artifacts/e2e-campaign-epic-22/manifest.jsonl`, `docs/implementation-artifacts/e2e-campaign-epic-22/screenshots/**/*.png`, `docs/implementation-artifacts/e2e-campaign-epic-22/bilan-execution-tests-e2e-epic-22.md`, `docs/implementation-artifacts/e2e-campaign-epic-22/notes-audit-sally-ux.md`, `docs/implementation-artifacts/e2e-campaign-epic-22/notes-audit-winston-architecture.md`, `docs/implementation-artifacts/e2e-campaign-epic-22/synthese-remediation-sally-winston-epic-22.md`, `docs/product/capabilities.yaml`, `infra/scripts/uj_e2e_coverage.py` (référentiel résultats campagne active).

**Acceptance Criteria:**

**Given** l'ensemble des `24` specs Playwright (`110` scénarios Desktop `1440×900` + Mobile `390×844`) configuré avec `ORCIA_E2E_CAMPAIGN_DIR=docs/implementation-artifacts/e2e-campaign-epic-22`
**When** la campagne E2E intégrale s'exécute contre PostgreSQL 18 + `pgvector` + Redis 7.4 avec `--retries=0 --max-failures=0 --timeout=35000`
**Then** la totalité des `24` specs s'exécute jusqu'au bout sans aucun `test.skip`/`test.fixme` masquant un échec, et tous les artefacts bruts sont archivés dans `docs/implementation-artifacts/e2e-campaign-epic-22/` : `playwright-results.json`, `manifest.jsonl` (`110` entrées) et `100 %` des captures PNG d'état final (succès comme échecs) sous `screenshots/`.

**Given** les artefacts bruts (`playwright-results.json`, `manifest.jsonl`, `screenshots/**/*.png`)
**When** le bilan et l'audit croisé **Sally × Winston** sont conduits
**Then** `bilan-execution-tests-e2e-epic-22.md` inventorie exactement les résultats (`passed`, `failed`, `timedOut`, `skipped`, assertions `F5` et `SELECT` PG18), `notes-audit-sally-ux.md` analyse les captures PNG Desktop/Mobile (ergonomie, surcharge, jargon, accessibilité), `notes-audit-winston-architecture.md` évalue la conformité `AD-1`..`AD-24`, et `synthese-remediation-sally-winston-epic-22.md` consolide chaque échec résiduel et chaque point d'amélioration priorisé (`P0`..`P3`) en chantiers structurés.

**Given** l'état réel observé dans `docs/implementation-artifacts/e2e-campaign-epic-22/playwright-results.json`
**When** `docs/product/capabilities.yaml` est mis à jour et validé par `pnpm site:sync && pnpm site:check`
**Then** toute capacité dont `100 %` des specs E2E associées sont vertes passe à `verification: runtime` (`verified_at` à jour, `e2e_remediation_ref` supprimé), tandis que toute capacité touchée par au moins un échec résiduel est honnêtement maintenue/marquée en `verification: failed_e2e` en vue de son traitement dans `Story 22.10` / `Epic 23`.

---

### Story 22.10: Rapports Tech Lead Individuels pour Tests en Échec & Plan Sally × Winston, Plan de Correction Global & Initialisation Epic 23

As a Tech Lead (`Amelia`) & Architecte (`Winston`),
I want conduire l'analyse d'impact GitNexus (`repo: "ORCIA"`) sur les constats issus de la campagne Epic 22, rédiger les Rapports Tech Lead individuels (`23-1-...` à `23-N-...`) pour chaque lot cohérent couvrant les tests E2E en échec et les points d'amélioration du plan Sally × Winston (`synthese-remediation-sally-winston-epic-22.md`), produire le plan de correction global `docs/planning-artifacts/sprint-change-proposal-2026-11-18-epic-23-remediation-plan.md`, et initialiser complètement l'**Epic 23** dans `epics.md`, `sprint-status.yaml` et `capabilities.yaml` avec un test automatique `tests/unit/test_epic22_to_epic23_traceability.py`,
So that chaque échec résiduel ou amélioration identifié à l'issue de l'Epic 22 démarre dans l'Epic 23 avec une traçabilité totale et zéro angle mort (`GEMINI.md` § Policy, `AD-17`).

**Dépendances :** Dépend de `Story 22.9`. Clôture l'Epic 22.
**CAP couvertes :** `none (gouvernance documentaire & planification Epic 23 — rattache toute capacité failed_e2e résiduelle et tout chantier Sally × Winston Epic 22)` — classification : `doc`.
**Fichiers impactés :** `docs/implementation-artifacts/tech-lead-reports/23-1-*.md` .. `23-N-*.md`, `docs/implementation-artifacts/tech-lead-reports/README.md`, `docs/planning-artifacts/sprint-change-proposal-2026-11-18-epic-23-remediation-plan.md`, `docs/planning-artifacts/epics.md` (ajout `Epic 23`), `docs/implementation-artifacts/sprint-status.yaml` (ajout `epic-23` + `23-1..23-N`, clôture `epic-22: done`), `docs/product/capabilities.yaml` (références `e2e_remediation_ref`), `tests/unit/test_epic22_to_epic23_traceability.py`.

**Acceptance Criteria:**

**Given** l'ensemble des tests E2E en échec de `bilan-execution-tests-e2e-epic-22.md` et des points d'amélioration du plan Sally × Winston (`synthese-remediation-sally-winston-epic-22.md`)
**When** le Tech Lead exécute l'analyse d'impact GitNexus (`gitnexus_query`, `gitnexus_context`, `gitnexus_impact` avec `repo: "ORCIA"`) sur les symboles et modules concernés
**Then** tous les échecs E2E résiduels et points d'amélioration Sally × Winston sont regroupés en `N` lots cohérents (`Story 23.1` à `Story 23.N`), chacun doté d'un Rapport Tech Lead pré-implémentation individuel (`docs/implementation-artifacts/tech-lead-reports/23-1-...-tech-lead-report.md` .. `23-N-...`) conforme à `TECH-LEAD-REPORT-TEMPLATE.md` et enregistré dans `docs/implementation-artifacts/tech-lead-reports/README.md`.

**Given** le plan de correction global `docs/planning-artifacts/sprint-change-proposal-2026-11-18-epic-23-remediation-plan.md`
**When** il consolide la feuille de route de l'Epic 23
**Then** il contient l'ordonnancement par vagues et les matrices complètes reliant chaque échec E2E résiduel, chaque point d'amélioration Sally × Winston et chaque éventuelle `CAP-*` en `failed_e2e` à une Story `23.k` et son rapport Tech Lead `23-k-*`.

**Given** l'initialisation complète de l'**Epic 23** dans `epics.md`, `sprint-status.yaml` et `capabilities.yaml`, ainsi que `tests/unit/test_epic22_to_epic23_traceability.py`
**When** `.venv/bin/pytest tests/unit/test_epic22_to_epic23_traceability.py`, `.venv/bin/python scripts/check_implementation_docs.py` et `pnpm site:sync && pnpm site:check` s'exécutent
**Then** `100 %` de traçabilité bidirectionnelle est prouvée (aucun échec E2E ni point Sally × Winston orphelin), `epic-22` passe à `done`, et `Epic 23` est prêt pour exécution immédiate.

---
