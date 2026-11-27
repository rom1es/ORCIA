## Epic 1: Amorçage Gouverné de l'Organisation, Onboarding Autonome d'Équipe (`TEAM_LEAD`), Catalogue Fédéré & Permission Broker connecté à Jira

Permettre aux Ingénieurs Plateforme, Chefs d'Équipe (`TEAM_LEAD`) et Membres d'équipe (`Karim UJ-9`, `Marc UJ-5`, `Nadia UJ-4`, `Lucas UJ-7`) de disposer du socle opérationnel d'ORCIA, d'initialiser l'organisation dès le Jour 0 et d'embarquer chaque équipe et ses différentes solutions logicielles (`Workspaces`) en autonomie via les workflows système gouvernés, de publier et résoudre à la volée des ressources fédérées (`db://`, `git://`, `nexus://`, `confluence://`, `jira://`, packs BMAD) avec cache CAS `SHA-256`, surcharges à 4 niveaux et 5 permissions dissociées, et de débloquer tout refus d'accès (`401/403`) grâce au *Permission Broker* connecté à Jira.

### Story 1.1: Amorçage du Monorepo Hybride, Coquille UI Direction C (7 Modules) & Socle de Tests à 5 Couches

As a Ingénieur Plateforme (`Karim, UJ-9`),
I want initialiser le monorepo hybride TypeScript/Python, l'infrastructure conteneurisée (PostgreSQL 18 + pgvector, Redis 7.4, MinIO), la génération automatique du client OpenAPI 3.1, la coquille visuelle Direction C à 7 modules et le harnais de tests à 5 couches,
So that toute l'équipe dispose d'une fondation typée de bout en bout, observable et testée unitairement à $\ge 90\%$ avant de développer les briques métiers (`AR-1`, `AR-2`, `UX-DR1`, `UX-DR2`, `NFR-OBS-1`, `NFR-TEST-1`).

**Acceptance Criteria:**

**Given** un environnement de développement vierge disposant de `Node.js 24.0`, `pnpm 10.6`, `Python 3.12.9`, `uv 0.13.5` et `Docker Compose`
**When** l'ingénieur exécute la commande d'initialisation et de démarrage du monorepo (`pnpm install && uv sync && docker compose up -d`)
**Then** le workspace démarre `apps/web` (Next.js `16.4`, React `19.1`, Tailwind `4.3`, `shadcn/ui`), `apps/api` (FastAPI `0.143`), `apps/worker` (Dramatiq `2.2`), `packages/orcia-core` (squelette hexagonal des 8 domaines) et les conteneurs **PostgreSQL `18.0` + `pgvector 0.8.7`**, **Redis `7.4.2`** et **MinIO**
**And** la génération `openapi-typescript` produit `packages/api-client` avec `0 diff` depuis les schémas Pydantic v2 de `packages/orcia-core/schemas`, et toute erreur API retourne une enveloppe **RFC 9457 Problem Details** corrélée par `trace_id` OpenTelemetry (`structlog` / `pino`).

**Given** l'utilisateur qui ouvre `apps/web` sur un écran Desktop (`>= 1280px`) ou Laptop (`768px - 1279px`)
**When** la coquille applicative Direction C est rendue
**Then** les tokens CSS (`#0F172A` Sidebar, `#F8FAFC` Surface, `#2563EB` Primary, `#6D28D9` Human-Led Violet, `#D97706` Arbitration Amber, `#059669` Gate Emerald, `#0284C7` Ontology Cyan, `#DC2626` Stale Crimson) et les polices (`Inter`, `Instrument Serif`, `JetBrains Mono`) sont appliqués (`UX-DR1`)
**And** la grille à 3 colonnes affiche la *Global Sidebar Navigation* (`235px` dépliée / `68px` repliée via `[`) avec les 7 entrées du Menu Global, l'*Espace Central* (`1fr`) et le *Dock Persistant Agent Assistant & Permission Broker* (`360px`, repliable via `]`) (`UX-DR2`)
**And** la CI exécute avec succès les 5 couches de tests (`pytest` + `hypothesis`, `Vitest`, `testcontainers-python` sur vrais PG18/Redis/MinIO, `Schemathesis` et `@playwright/test`) avec une couverture unitaire $\ge 90\%$ (`AD-17`, `NFR-TEST-1`).

### Story 1.2: Authentification Hybride Bi-Mode (OIDC & Locale), Arbre Hiérarchique d'Équipes (`OrgUnit`) découplé des Espaces Solutions Multi-Sources (`Workspaces`), Rôle `TEAM_LEAD` & 5 Permissions Dissociées

As a Administrateur Plateforme ou Chef d'Équipe (`Karim UJ-9`, `Marc UJ-5`, `Nadia UJ-4`),
I want authentifier les utilisateurs via SSO d'Entreprise (`OIDC / OAuth 2.1`) ou via Authentification Locale autonome (`Email + Argon2id + MFA TOTP`), modéliser un arbre hiérarchique d'équipes (`org_units` à $N$ niveaux : `Entreprise -> BU -> Tribu/Équipe Parente -> Sous-Équipe`) découplé des `Workspaces` représentant chacun une solution logicielle pouvant agréger **plusieurs dépôts `git://`, plusieurs projets `jira://` et plusieurs espaces `confluence://` dédiés**, et appliquer les 5 permissions dissociées (`DISCOVER`, `EXECUTE`, `READ_SOURCE`, `EDIT`, `ADMIN`),
So that chaque solution logicielle d'une équipe ait ses multiples sources (`N × git://`, `N × jira://`, `N × confluence://`) et artefacts isolés, que les équipes parentes disposent d'une supervision consolidée, et que les sous-équipes héritent des agents de leur équipe parente tout en protégeant les prompts/codes en boîte noire (`FR-21`, `AD-6`, `AD-14`, `NFR-SEC-4`).

**Acceptance Criteria:**

**Given** la migration Alembic créant les tables `org_units` (arbre auto-référencé via `parent_id`), `workspaces` (`owner_org_unit_id`, `visibility_mode: STANDARD | CONFIDENTIAL_RESTRICTED`), `workspace_datasources` (relation `1..N` rattachant à un Workspace ses multiples dépôts `git://`, projets `jira://`, espaces `confluence://`, schémas `db://` et registres `nexus://` qualifiés par `alias` et `role`), `users`, `transverse_groups`, `workspace_memberships`, `workspace_invitations`, `user_passthrough_credentials` et `catalog_acl_entries` à clés primaires `UUIDv7`
**When** un utilisateur s'authentifie soit via **SSO `OIDC / OAuth 2.1`**, soit via le flux **Local autonome (`Email + Argon2id + TOTP optionnel`)** et appelle `/api/v1/auth/me`
**Then** une session JWT courte (`15 min`) + Refresh Token `HttpOnly / Secure / SameSite=Strict` révocable dans Redis est établie, son *Profil Humain* complet (Archétype, Rôle `PLATFORM_ADMIN` / `TEAM_LEAD` / `CONTRIBUTOR` / `GATE_REVIEWER` / `ONTOLOGY_STEWARD_L3` / `OBSERVER`, arbre d'équipes `org_units`, liste des `Workspaces` solutions accessibles) est affiché en pied de Sidebar (`UX-DR2`), et les entrées du Menu Global non autorisées sont masquées côté UI et protégées en `HTTP 403` côté API.

**Given** une équipe (ou sous-équipe) pilotée par un **Chef d'Équipe (`TEAM_LEAD`)** qui maintient plusieurs solutions logicielles (ex. `Workspace 1 : Solution Paiement` avec 3 dépôts `git://`, 2 projets `jira://` et 2 espaces `confluence://`, et `Workspace 2 : Solution Fidélité` avec ses propres sources)
**When** le `TEAM_LEAD` gère son équipe et ses `Workspaces`
**Then** l'ensemble des sources dédiées (`N × git://`, `N × jira://`, `N × confluence://`), les *Workflow Runs* et les *Artefacts* du `Workspace 1` sont strictement isolés de ceux du `Workspace 2` ; le responsable d'une **Équipe Parente / Tribu / BU** dispose automatiquement par héritage ascendant (*Roll-up*) d'un accès `READ_ONLY_OBSERVER` et d'une agrégation FinOps sur les Workspaces des sous-équipes filles (sauf si le Workspace est marqué `CONFIDENTIAL_RESTRICTED`) ; et une équipe partenaire invitée sur le `Workspace 1` n'a aucune visibilité sur le `Workspace 2` (`FR-21`, `AD-14`).

**Given** une ressource du Catalogue publiée en `SHARED_TEAM` ou `SHARED_BU` par une équipe parente avec `DISCOVER` et `EXECUTE` mais **sans** `READ_SOURCE`
**When** un membre d'une sous-équipe fille inspecte la ressource ou l'exécute dans l'un de ses `Workspaces`
**Then** la ressource est automatiquement découvrable et exécutable par héritage descendant dans tous les Workspaces des sous-équipes filles, mais son prompt système et ses scripts sources restent masqués (`🔒 Source masquée`, `HTTP 403 ERR_READ_SOURCE_DENIED`), et tout secret *Passthrough* (`user_passthrough_credentials`) est chiffré en **AES-256-GCM** (`NFR-SEC-4`), avec couverture $\ge 90\%$ sur `packages/orcia-core/permissions`.

### Story 1.3: Catalogue Fédéré Multi-Sources (`N × git://`, `N × jira://`, `N × confluence://`, `db://`, `nexus://`), Cache CAS `SHA-256`, Surcharges à 4 Niveaux (`Base → Team → Workspace → User`) & Adaptateur BMAD

As a Tech Lead ou Ingénieur Plateforme (`Marc UJ-5`, `Karim UJ-9`),
I want enregistrer des ressources par leur URI canonique dans le Catalogue Fédéré, les résoudre à la volée vers le cache immuable MinIO (`cas/<sha256>`), appliquer les surcharges déclaratives à 4 niveaux (`1. Base -> 2. Standards d'Équipe TEAM hiérarchique -> 3. Solution WORKSPACE multi-sources -> 4. Utilisateur USER`) et importer nativement des packs de skills BMAD,
So that une équipe mutualise ses conventions sur toutes ses solutions logicielles au niveau `TEAM` tout en configurant les multiples dépôts `git://`, projets `jira://` et espaces `confluence://` propres à chaque solution au niveau `WORKSPACE` avec une résolution `< 50 ms` (`FR-20`, `FR-21`, `AD-5`, `AD-14`, `AR-5`, `UX-DR8`, `NFR-PERF-3`).

**Acceptance Criteria:**

**Given** la migration Alembic créant les tables `workflow_definitions` (et `catalog_items`) et `workspace_customization_overrides` (`override_layer: TEAM | WORKSPACE | USER`), ainsi que le module **📦 3. Catalogue Fédéré** dans `apps/web`
**When** un utilisateur publie ou promeut une ressource à travers le cycle `DRAFT` $\rightarrow$ `SHARED_WORKSPACE` $\rightarrow$ `SHARED_TEAM` $\rightarrow$ `SHARED_BU` $\rightarrow$ `PENDING_APPROVAL` $\rightarrow$ `PUBLISHED_ORG` avec une URI `db://`, `git://`, `nexus://` (`.tar.gz`/`.zip`), `confluence://<space>/<page>@v<N>` ou `jira://<project>/<issue>`
**Then** le `FederatedUriResolver` télécharge la ressource à la première demande, vérifie ou calcule son empreinte `SHA-256`, la stocke de manière immuable dans MinIO sous `cas/<sha256>`, et toute résolution ultérieure du même hash répond en `< 50 ms` (`NFR-PERF-3`)
**And** chaque carte du Catalogue affiche le composant monospace **`Federated URI & RBAC Badge` (`uri-badge`, `UX-DR8`)** distinguant par couleur et icône la source (`git://`, `nexus://`, `db://`, `confluence://`, `jira://`), les droits effectifs et le hash `SHA-256` tronqué.

**Given** un workflow de base du catalogue et des surcharges déclaratives enregistrées dans `workspace_customization_overrides` aux niveaux `TEAM` (équipe parente / sous-équipe), `WORKSPACE` (mapping des `1..N` dépôts `git://`, `1..N` projets `jira://` et `1..N` espaces `confluence://` dédiés à la solution logicielle) et/ou `USER`
**When** le moteur résout la définition effective du workflow pour un *Run* lancé dans un *Workspace* donné
**Then** il applique la fusion déterministe à **4 niveaux (`1. Base -> 2. Team [Arbre Équipe Parente -> Sous-Équipe] -> 3. Workspace [Solution Multi-Sources] -> 4. User`)** : scalaires écrasés, listes de sources/règles/faits concaténées, lentilles fusionnées par `code`, sans modifier la ressource de base (`AD-14`), et épingle dans `run-lock.json` le vecteur complet des triplets `(alias, uri, resolved_version, sha256)` de toutes les sources du Workspace (`AD-5`)
**And** le `BmadSkillPackAdapter` importe et convertit sans perte un répertoire de skill BMAD (`SKILL.md` + `customize.toml` + `steps/*.md`) référencé via `git://` ou `nexus://` en définition exécutable ORCIA (`AR-5`), avec $\ge 90\%$ de couverture (`hypothesis` + `testcontainers` MinIO/PG18) sur `packages/orcia-core/catalog`.

### Story 1.4: Exécution Passthrough / Service Principal & Permission Broker IA connecté à Jira

As a Développeur ou Contributeur Métier (`Lucas UJ-7`, `Yanis UJ-3`),
I want que chaque résolution de ressource externe s'exécute par défaut avec mon identité déléguée (`Passthrough`) et qu'en cas de refus d'accès (`401/403`), le Permission Broker intercepte l'erreur et m'affiche la procédure d'obtention ainsi que le lien de demande d'accès pré-remplie dans Jira,
So that aucune élévation de privilèges (*Confused Deputy*) ne soit possible et qu'aucun blocage d'habilitation ne laisse l'utilisateur dans une impasse (`FR-22`, `AD-6`, `UX-DR11`).

**Acceptance Criteria:**

**Given** un connecteur externe (`git://`, `nexus://`, `confluence://`, `jira://`, `db://` ou client MCP) configuré par défaut en `execution_identity: passthrough` (ou en `service_principal` uniquement si explicitement approuvé par un Administrateur)
**When** une étape ou une action tente d'accéder à l'un des dépôts Git privés, l'une des pages Confluence restreintes ou l'un des projets/transitions de workflow Jira du Workspace pour lequel l'utilisateur courant ne possède pas le rôle requis (`HTTP 401/403`) ou la permission `EXECUTE`
**Then** le `PermissionBrokerService` intercepte l'exception, recherche le motif d'URI correspondant dans la Base de Connaissances d'Habilitations (fichiers Markdown à frontmatter YAML `uri_pattern`, `required_role`, `approver_team`, `request_url_template`, `sla_hours`), et retourne une enveloppe RFC 9457 enrichie du champ `permission_broker_hint`.

**Given** la réception de l'état `PERMISSION_DENIED_STEP` / `WAITING_FOR_PERMISSION` dans l'interface web
**When** l'utilisateur visualise l'étape bloquée dans le Cockpit ou le Catalogue
**Then** le **Dock Agent Assistant & Permission Broker** s'ouvre automatiquement à droite avec une carte ambre (`#D97706`, `UX-DR11`) présentant : (1) la source exacte (`git://`, `confluence://` ou `jira://`) et le droit ou rôle de projet Jira manquant, (2) l'équipe ou le responsable approbateur identifié et le SLA, (3) le bouton/lien ouvrant la demande d'accès pré-remplie dans **Atlassian Jira**, et (4) le bouton *Mettre en pause / Rejouer l'étape* (`FR-22`)
**And** les tests unitaires et d'intégration couvrent $\ge 90\%$ du `PermissionBrokerService` et vérifient le rendu du composant UI via Vitest / Playwright.

### Story 1.5: Workflows Système d'Amorçage Gouverné Jour 0 & Onboarding Autonome d'Équipe et Multi-Workspaces Multi-Sources par le Chef d'Équipe (`init-organization`, `init-workspace`, `init-datasource`, `init-user`)

As a Ingénieur Plateforme ou Chef d'Équipe (`Karim UJ-9`, `Marc UJ-5`, `Nadia UJ-4`),
I want exécuter les workflows système pré-embarqués (`orcia://system/bootstrap/*`) guidés par l'Agent Assistant et verrouillés par des Gates Déterministes bloquantes, permettant à un Chef d'Équipe (`TEAM_LEAD`) d'embarquer son équipe, ses sous-équipes et chacune de ses solutions logicielles (`Workspaces`) avec ses multiples sources dédiées (`N × git://`, `N × jira://`, `N × confluence://`) en totale autonomie,
So that aucune organisation ne démarre à froid sans modèles LLM orthogonaux configurés, qu'une équipe puisse configurer ses standards une fois et ouvrir autant de Workspaces que de solutions logicielles, et qu'aucune source (`db://`, `git://`, `nexus://`, `confluence://`, `jira://`) ne soit publiée sans fiche Permission Broker ni politique de fraîcheur (`FR-28`, `AD-16`).

**Acceptance Criteria:**

**Given** une nouvelle instance d'ORCIA dans **⚙️ 7. Administration**
**When** l'administrateur lance `orcia://system/bootstrap/init-organization`
**Then** la Gate Déterministe bloque la validation de l'organisation tant que (1) la configuration d'authentification (OIDC et/ou Auth locale Argon2id) et le mapping RBAC ne sont pas valides et (2) `ModelRouterService` (LiteLLM) n'a pas vérifié avec succès la connectivité d'au moins **2 familles de modèles LLM distinctes** (condition requise pour l'orthogonalité des Gates Agentiques `AD-10`), puis amorce le catalogue socle.

**Given** un **Chef d'Équipe (`TEAM_LEAD`)** qui exécute `orcia://system/bootstrap/init-workspace` en self-service
**When** il configure son équipe (et d'éventuelles sous-équipes), invite ses membres et crée un ou plusieurs **Workspaces (solutions logicielles)**
**Then** il définit les standards `TEAM` et l'*Ontologie* `3_TEAM` communs à l'équipe, crée chaque *Workspace* solution avec sa surcharge `WORKSPACE` (`AD-14`), sa boîte de notifications et son *Ontologie* `3_WORKSPACE` (sans conflit avec N1/N2/`3_TEAM`), et pré-assigne à chaque membre invité son archétype de **Profil Humain** et ses rôles d'exécution ; à la première connexion de chaque membre, `orcia://system/bootstrap/init-user` se déclenche automatiquement pour confirmer son *Profil Humain* et lier ses comptes **Jira**, **Confluence** et **Git** en mode *Passthrough* (OAuth 3LO / PAT chiffré AES-256-GCM).

**Given** un Administrateur ou un **Chef d'Équipe (`TEAM_LEAD`, dans un Workspace solution ou en portée `SHARED_TEAM`)** qui exécute `orcia://system/bootstrap/init-datasource` à plusieurs reprises pour rattacher à un même Workspace **plusieurs dépôts `git://`** (ex. `git:backend`, `git:frontend`, `git:infra`), **plusieurs espaces `confluence://`** (avec filtres CQL `space_key`/labels, ex. `confluence:specs`, `confluence:adr`) et **plusieurs projets `jira://`** (avec filtres JQL, ex. `jira:product`, `jira:secops`) dédiés à la solution
**When** il soumet chaque source pour publication et liaison (`workspace_datasources`)
**Then** la Gate Déterministe rejette la publication (`HTTP 422`) tant que (a) la fiche d'habilitation YAML/Markdown du *Permission Broker* n'a pas été rédigée et signée comme **Ancre Humaine** par le propriétaire de la source et (b) le paramètre `freshness_ttl_days` n'est pas renseigné (`FR-28`, `AD-16`), avec une couverture de tests $\ge 90\%$.
