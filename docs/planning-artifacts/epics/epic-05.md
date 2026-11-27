## Epic 5: Centre de Notifications Temps Réel (`< 500ms`), Supervision Multi-Runs, Centre de Pilotage Unifié Multi-Niveaux des Workspaces (`/workspaces`) & Expérience Mobile Companion

Permettre aux Administrateurs Plateforme (`Karim UJ-9`), Directeurs de BU (`Claire UJ-8`), Chefs d'Équipe (`Marc UJ-5`) et Contributeurs multi-projets (`Nadia UJ-4`) de trier leurs notifications personnelles et d'équipe dans **🔔 2. Boîte & Mes Runs**, de prendre en charge (*Claim*) atomiquement une notification d'équipe avec verrou de présence temps réel (`< 500ms` via SSE), de superviser simultanément plusieurs *Workflow Runs* avec séparation stricte entre *Consultation seule (`READ_ONLY_OBSERVER`)* et *Contributeur (`CONTRIBUTOR_ACTION_REQUIRED`)*, de piloter et d'administrer de manière consolidée (*Roll-up* & *Drill-down* via le sélecteur de périmètre **`⌘W`**) l'ensemble des **Workspaces, Instances de Workflow Runs, Sources (`N × git://`, `N × jira://`, `N × confluence://`, `db://`, `nexus://`), Agents/Workflows/Surcharges et Équipes** depuis le **Centre de Pilotage Unifié Multi-Niveaux (`/workspaces` & `/workspaces/[workspaceId]` à 4 onglets)**, de piloter l'interface au clavier (`⌘K`, `⌘W`, `g c`..`g w`, `Alt + ↑/↓`), et de traiter leurs arbitrages et validations urgentes en déplacement grâce à l'interface **Mobile Companion** à 3 onglets conforme WCAG 2.2 AA.

### Story 5.1: Centre de Notifications Unifié (Individuel & Équipe), Prise en Charge Atomique (`Claim`) & Verrou de Présence SSE `< 500 ms`

As a Product Manager ou Lead Multi-Projets (`Nadia, UJ-4`),
I want consulter dans une boîte unifiée mes notifications personnelles et d'équipe, les filtrer par portée/type, et prendre en charge (`Claim`) atomiquement une notification d'équipe avec diffusion SSE en `< 500 ms`,
So that deux membres d'une même équipe ne travaillent jamais en doublon ni ne soumettent des validations contradictoires sur la même étape (`FR-2`, `AD-4`, `AD-19`, `UX-DR9`, `UX-DR11`, `NFR-PERF-2`).

**Acceptance Criteria:**

**Given** la migration Alembic créant la table `task_notifications` (référençant `step_execution_id`, `target_team_id`, `target_user_id`, `claimed_by_user_id`), l'abonné Outbox `notifications` consommant `domain_events_outbox` (`AD-19`), ainsi que le broker SSE `/api/v1/events/stream` branché sur Redis Pub/Sub `channel:workspace:{ws_id}`
**When** une étape requiert une action humaine (*Gate Humaine*, *Arbitrage Humain*, *Challenge Humain*, *Alerte Habilitation / Obsolescence*)
**Then** la notification apparaît instantanément dans **🔔 2. Boîte & Mes Runs** (`g i`, `apps/web/src/features/inbox/`), filtrable par portée (*À moi*, *À mon équipe*) et par type, et incrémente le badge compteur ambre sur la Sidebar (`FR-2`, `UX-DR2`).

**Given** une notification d'équipe affichant le composant **`Presence & Claim Pill` (`presence-claim-pill`, `UX-DR9`)** à deux coéquipiers connectés simultanément (`Nadia` et `Thomas`)
**When** `Nadia` clique sur `Prendre (Claim)` (`POST /api/v1/tasks/{task_id}/claim` ou `POST /api/v1/runs/{run_id}/steps/{step_id}/claim`)
**Then** l'API acquiert le verrou atomique Redis `SET lock:step:{step_execution_id} {user_id} NX EX 900`, persiste `claimed_by_user_id` en base et publie `task.claim.locked` sur Redis Pub/Sub (`AD-4`)
**And** en `< 500 ms` (`NFR-PERF-2`), l'interface de `Nadia` affiche `🔒 Pris par vous` et celle de `Thomas` passe en état `CLAIMED_BY_PEER` (opacité `85%`, pastille émeraude `🔒 En cours : Nadia`, avec possibilité de *Force Unclaim* après 15 minutes d'inactivité, `UX-DR9`, `UX-DR11`)
**And** `lint-imports` passe à `0` violation et les tests d'intégration (`testcontainers` Redis + PG18 sous concurrence) et E2E multi-navigateurs (`@playwright/test` à 2 contextes simultanés) valident l'atomicité du verrou et la latence `< 500 ms` (`AD-17`, `AD-19`).

**Given** la Story `3.2f` livrée et l'action `DEC-CONC-01` (Avenant A2, `AD-4`)
**When** deux *Runs* concurrents tentent d'écrire sur la même ressource partagée (même `resource_uri`)
**Then** un seul obtient le bail `ResourceLeasePort` (bail PostgreSQL `resource_leases` + jeton de fencing monotone), l'écriture portant un jeton périmé est rejetée par le connecteur, l'acquisition multi-ressources suit l'ordre canonique par `resource_uri`, et une attente cyclique parent-enfant (`SUB_WORKFLOW`) est détectée et levée par délai d'expiration (tests sous concurrence `testcontainers` PG18).

### Story 5.2: Supervision Multi-Runs Dynamique (`< 1 s`), Sélecteur de Périmètre Hiérarchique (`⌘W`), Centre de Pilotage Unifié Multi-Niveaux des Workspaces (`/workspaces` à 4 Onglets), Séparation `READ_ONLY_OBSERVER` (`HTTP 403`) vs `CONTRIBUTOR_ACTION_REQUIRED` & Palette `⌘K`

As a Administrateur Plateforme (`Karim UJ-9`), Directrice de BU (`Claire UJ-8`), Chef d'Équipe (`Marc UJ-5`) ou Lead Multi-Projets (`Nadia UJ-4`),
I want superviser simultanément mes Workflow Runs actifs en distinguant ceux où une action est attendue (`Contributeur`) de ceux que je suis en `Consultation seule`, basculer de périmètre organisationnel (`🌐 Plateforme Globale → 🏢 BU → 👥 Équipe → 🗂️ Workspace`) via `⌘W` pour consulter et gérer dans un écran unifié (`/workspaces` & `/workspaces/[workspaceId]` à 4 onglets) l'ensemble des instances de runs, des sources dédiées/partagées (`N × git://`, `N × jira://`, `N × confluence://`, `db://`, `nexus://`), des agents/workflows/surcharges et des équipes selon mon niveau hiérarchique, basculer entre deux Runs en `< 1 s` via la palette `⌘K`, et être protégé en `HTTP 403` contre toute mutation accidentelle en mode Observateur,
So that je puisse piloter aussi bien un Workspace isolé qu'une Équipe, une BU entière ou la Plateforme Globale sans jamais interférer par erreur dans une étape qui ne m'est pas assignée (`FR-1`, `FR-3`, `AD-4`, `AD-14`, `AD-19`, `UX-DR2`, `UX-DR11`, `UX-DR13`, `NFR-PERF-1`).

**Acceptance Criteria:**

**Given** un utilisateur qui consulte **🔔 2. Boîte & Mes Runs** ou ouvre la palette de commandes universelle **`⌘K` / `Ctrl+K` (`UX-DR13`)**
**When** il visualise ses *Workflow Runs* ou recherche un Run / Workspace / concept d'Ontologie / item du Catalogue
**Then** la vue scinde clairement les Runs en **Actions Requises (`CONTRIBUTOR_ACTION_REQUIRED`)** en haut et **En Suivi (`READ_ONLY_OBSERVER`)** en bas (`FR-3`), les raccourcis clavier (`g c`, `g i`, `g f`, `g o`, `g g`, `g a`, `g s`, `g w`, `[`, `]`, `Alt + ↑/↓`) sont actifs, et le clic sur un Run charge son contexte complet dans le Cockpit en `< 1 s` (`NFR-PERF-1`).

**Given** un utilisateur habilité (`PLATFORM_ADMIN`, `BU_DIRECTOR`, `TEAM_LEAD` ou Contributeur) qui utilise le **Sélecteur de Périmètre Hiérarchique (`⌘W` / `Ctrl+W`, `UX-DR2`, `UX-DR13`)** en tête de Sidebar et ouvre le **Centre de Pilotage Unifié des Workspaces (`/workspaces` ou `/workspaces/$workspaceId` sous `TanStack Router v1`, `apps/web/src/features/workspaces/`, `g w`)**
**When** il sélectionne une échelle (`🌐 Plateforme Globale`, `🏢 BU / Tribu`, `👥 Équipe / Sous-Équipe` ou `🗂️ Workspace Solution`) et navigue à travers les **4 onglets fractals** (`GET /api/v1/control-center/overview?scope_type=GLOBAL|BU|TEAM|WORKSPACE&scope_id={id}`)
**Then** l'écran consolide dynamiquement par *Roll-up* SQL (`WITH RECURSIVE org_tree`) et permet le *Drill-down* en 1 clic sur :
- **Onglet 1 (`▶️ Instances de Workflow Runs & Artefacts`)** : la liste temps réel (SSE) des *Workflow Runs* du périmètre filtré (statut, étape courante, mode `Coaching` vs `Fast-Path`, verrou *Claim*, actions requises, budget consommé, et lancement d'un nouveau Run ou *Replay*) ;
- **Onglet 2 (`🔌 Sources Dédiées & Partagées`)** : toutes les sources rattachées aux Workspaces et Équipes du périmètre (`N × git://`, `N × jira://`, `N × confluence://`, `db://`, `nexus://` de `workspace_datasources`), leur état d'indexation dans le *Graphe Tripartite*, les alertes `[STALE_WARNING]`, le bouton `+ Rattacher une source` (`init-datasource`) et le tiroir méthodologique **`<GuidanceDrawer />`** en 5 étapes ;
- **Onglet 3 (`🤖 Workflows, Agents & Surcharges 4 niveaux`)** : les *Workflows* et *Agents* actifs avec aperçu `@xyflow/react`, l'inspecteur des surcharges déclaratives (`1. Base -> 2. Équipe TEAM -> 3. Solution WORKSPACE -> 4. Utilisateur USER`) et le contrat `ARCHITECTURE-SPINE.md` ;
- **Onglet 4 (`👥 Équipes, Membres & Gouvernance`)** : l'arborescence `org_units`, les *Workspaces / Produits* rattachés qualifiés par leur phase de cycle de vie **`RUN | BUILD | MIGRATION`** (`<ProductLifecycleCard />`, adaptant dynamiquement les workflows suggérés), les membres invités (`init-user`), les délégations de Gates et la politique de visibilité (`STANDARD` vs `CONFIDENTIAL_RESTRICTED`, où le `PLATFORM_ADMIN` conserve la supervision technique/FinOps des espaces `CONFIDENTIAL_RESTRICTED` sans exposer leurs payloads métiers du *Blackboard* sauf habilitation explicite).

**Given** un utilisateur qui ouvre un *Workflow Run* avec le statut `READ_ONLY_OBSERVER` (y compris un Directeur de BU ou un Lead d'équipe parente en supervision *Roll-up*, ou une étape verrouillée par un pair `CLAIMED_BY_PEER`)
**When** le Cockpit affiche le Run ou qu'une requête `POST/PUT/PATCH/DELETE` de mutation d'étape/artefact/Gate est envoyée à l'API
**Then** l'interface affiche le bandeau supérieur `👁️ Mode Consultation Seule — Vous suivez ce Workflow Run en tant qu'Observateur` (`UX-DR11`) et désactive tous les boutons d'édition, d'arbitrage et d'approbation de Gate
**And** le middleware FastAPI `RunAccessGuard` vérifie en $O(1)$ le rôle et la détention de `lock:step:{step_execution_id}` et rejette toute tentative de mutation avec `HTTP 403 ERR_OBSERVER_MODE_READ_ONLY` (`FR-3`, `AD-4`)
**And** `lint-imports` passe à `0` violation et les tests unitaires (`pytest` sur `RunAccessGuard` et l'agrégation récursive `control-center/overview`, `Vitest` sur la palette `⌘K`, le sélecteur `⌘W` et les 4 onglets `/workspaces`), d'intégration (`testcontainers` PG18 + Redis) et E2E (`Playwright`) couvrent $\ge 90\%$ du périmètre (`AD-17`, `AD-19`).

### Story 5.3: Expérience Responsive à 3 Breakpoints, Interface Mobile Companion Restreinte (3 Onglets) & Conformité Accessibilité WCAG 2.2 AA

As a Contributeur ou Valideur en mobilité (`Nadia UJ-4`, `Hélène UJ-1`),
I want utiliser ORCIA sur Desktop (`>= 1280px`), Laptop (`768px - 1279px`) et sur Smartphone (`< 768px`) via l'interface Mobile Companion dédiée à 3 onglets (`🔔 Inbox`, `💬 Arbitrage/Chat`, `📄 Briefing`), avec une conformité WCAG 2.2 AA complète,
So that je puisse débloquer mon équipe en moins de 10 minutes depuis mon téléphone tout en étant protégé contre les manipulations lourdes inadaptées au mobile (`UX-DR16`, `NFR-A11Y-1`, `NFR-TEST-1`).

**Acceptance Criteria:**

**Given** un utilisateur qui accède à `apps/web` depuis un viewport **Mobile Companion (`< 768px`, ex. `390x844`)** (`UX-DR16`)
**When** l'application adapte sa mise en page
**Then** la grille à 3 colonnes est remplacée par une vue mono-colonne pilotée par une barre d'onglets basse à 3 entrées (`🔔 Inbox`, `💬 Arbitrage/Chat`, `📄 Briefing`) permettant de trier et *Claim* les notifications, trancher les *Arbitrages Humains* (`arbitration-tiebreak-card`), lire le *Briefing de Revue (4 blocs)*, approuver les sections par découpage et suivre les Runs en *Consultation seule*
**And** l'édition de manifestes YAML *Workflow-as-Code*, la co-édition lourde d'artefacts multi-pages et le module *7. Administration* sont explicitement bloqués sur mobile avec la bannière *"Fonctionnalité réservée au poste Desktop"* (`UX-DR16`).

**Given** l'ensemble des surfaces Desktop, Laptop et Mobile Companion d'ORCIA
**When** un audit d'accessibilité automatisé et clavier est exécuté (`NFR-A11Y-1`)
**Then** 100% des écrans respectent les ratios de contraste **WCAG 2.2 AA**, aucun état critique (*Ancrage Humain*, *Arbitrage*, *Gate*, `[STALE_WARNING]`) n'utilise la couleur seule (toujours **Couleur sémantique + Icône dédiée + Libellé textuel explicite** : `✍️ Ancrage Humain`, `⚖️ Arbitrage IA`, `🛡️ Gate`, `🚨 Obsolète`), et les régions `aria-live="polite"` annoncent les nouvelles notifications, les *Claims* SSE et le streaming de l'Agent Assistant
**And** la suite E2E `@playwright/test` s'exécute sur les viewports Desktop (`1440x900`) et Mobile (`390x844`) avec $\ge 90\%$ de couverture des composants UI.

### Story 5.4: Coquille Globale Direction C Enrichie (Mire `/login` Bi-Mode, Mode Rail Collapsible, Header Santé DBOS/Outbox & Accueil Anti-Empty-State Scopé)

As a Utilisateur authentifié ou Administrateur Plateforme (`Hélène UJ-1`, `Marc UJ-5`, `Karim UJ-9`),
I want disposer d'une mire de connexion `/login` bi-mode claire (SSO OIDC primaire + accordéon d'administration locale Argon2id/TOTP), d'une Sidebar repliable en Mode Rail (`68px`, `[`) affichant le Pack actif, d'une barre supérieure exposant la santé temps réel du moteur (`DBOS/PG18`, `Outbox DLQ`) et le Sprint/Lot actif, et d'un tableau de bord d'accueil Anti-Empty-State (`/`) proposant une boîte de prompt scopée aux sources RAG autorisées ainsi qu'un widget de Sprint actif avec audit IA en 1 clic,
So that la prise en main quotidienne soit immédiate sans page blanche ni surcharge cognitive (Loi de Hick) tout en rendant transparents le périmètre documentaire interrogé et la santé de l'orchestrateur (`FR-1`, `AD-15`, `AD-19`, `AD-21`, `UX-DR1`, `UX-DR2`).

**Acceptance Criteria:**

**Given** un utilisateur non authentifié accédant à une route protégée de `apps/web`
**When** le guard `beforeLoad` de TanStack Router intercepte la navigation
**Then** il redirige vers la route dédiée **`/login`** qui présente en action primaire le bouton **SSO d'Entreprise (OIDC PKCE)** et, dans un accordéon secondaire replié par défaut (*« Connexion locale / Administrateur de secours »*), le formulaire email + mot de passe Argon2id + code TOTP 2FA avec gestion typée des erreurs RFC 9457 (session expirée, compte désactivé, échec OIDC) (`AD-15`, `AD-21`).

**Given** un utilisateur connecté naviguant dans la coquille globale Direction C (`AppShell`)
**When** il actionne le bouton de repli ou le raccourci `[` sur la Sidebar gauche (`<CollapsibleAppRail />`) ou consulte l'en-tête (`TopHeaderBar`)
**Then** la Sidebar bascule fluidement entre le mode étendu (`240px`) et le **Mode Rail (`72px`)** (état persisté), affiche en pied le badge du **Pack Métier actif** (`orcia-pack-sdlc`) et les pastilles temps réel (actions requises, santé Outbox), tandis que le Header affiche le sélecteur Workspace/Pack couplé au Sprint/PI actif ainsi que les pastilles de santé `DBOS/PG18` et `Outbox` (`AD-21`).

**Given** un utilisateur qui arrive sur la page d'accueil `/`
**When** le tableau de bord d'accueil Anti-Empty-State est rendu
**Then** il affiche le **`<SprintContextWidget />`** du Sprint/Lot actif doté du CTA 1-clic *« Auditer les risques du sprint / lot avec l'IA »* ainsi que la **`<ScopedPromptBox />`** permettant de choisir explicitement le périmètre de sources RAG (filtré par le *Permission Broker*) et le Tier cognitif avant d'envoyer une requête à l'Agent Assistant
**And** `lint-imports` passe à `0` violation et les tests unitaires (`Vitest` sur `<CollapsibleAppRail />`, `<SprintContextWidget />`, `<ScopedPromptBox />` et `/login`) et E2E (`Playwright`) couvrent $\ge 90\%$ du périmètre (`AD-17`, `AD-19`).
