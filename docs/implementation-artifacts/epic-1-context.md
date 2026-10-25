# Epic 1 Context: Amorçage Gouverné de l'Organisation, Onboarding Autonome d'Équipe (`TEAM_LEAD`), Catalogue Fédéré & Permission Broker connecté à Jira

<!-- Compiled from planning artifacts. Edit freely. Regenerate with compile-epic-context if planning docs change. -->

## Goal

Fournir aux Ingénieurs Plateforme, Chefs d'Équipe (`TEAM_LEAD`) et Membres d'équipe le socle opérationnel d'ORCIA (monorepo hybride TypeScript/Python, infrastructure conteneurisée PostgreSQL 18 + `pgvector`, Redis 7.4 et MinIO, authentification hybride bi-mode OIDC + Locale Argon2id/TOTP, arbre hiérarchique d'équipes `OrgUnit` découplé des `Workspaces` de solutions logicielles multi-sources, et coquille UI Direction C à 7 modules), afin d'initialiser l'organisation dès le Jour 0, d'embarquer chaque équipe et ses solutions logicielles en autonomie via les workflows système gouvernés (`init-organization`, `init-workspace`, `init-datasource`, `init-user`), de publier/résoudre à la volée des ressources fédérées (`db://`, `N × git://`, `nexus://`, `N × confluence://`, `N × jira://`, packs BMAD) avec cache CAS `SHA-256`, surcharges à 4 niveaux et 5 permissions dissociées, et de débloquer tout refus d'accès (`401/403`) grâce au *Permission Broker* connecté à Jira.

## Stories

- Story 1.1: Amorçage du Monorepo Hybride, Coquille UI Direction C (7 Modules) & Socle de Tests à 5 Couches
- Story 1.2: Authentification Hybride Bi-Mode (OIDC & Locale), Arbre Hiérarchique d'Équipes (`OrgUnit`) découplé des Espaces Solutions Multi-Sources (`Workspaces`), Rôle `TEAM_LEAD` & 5 Permissions Dissociées
- Story 1.3: Catalogue Fédéré Multi-Sources (`N × git://`, `N × jira://`, `N × confluence://`, `db://`, `nexus://`), Cache CAS `SHA-256`, Surcharges à 4 Niveaux (`Base → Team → Workspace → User`) & Adaptateur BMAD
- Story 1.4: Exécution Passthrough / Service Principal & Permission Broker IA connecté à Jira
- Story 1.5: Workflows Système d'Amorçage Gouverné Jour 0 & Onboarding Autonome d'Équipe et Multi-Workspaces Multi-Sources par le Chef d'Équipe (`init-organization`, `init-workspace`, `init-datasource`, `init-user`)

## Requirements & Constraints

- **Monorepo Hybride & Contrats Typés** : Orchestration `pnpm 10.6` + `Turborepo 2.4` côté TypeScript (`Node.js 24+`) et environnement virtuel Python `.venv` (`Python 3.12+`) pour `packages/ui` (`@orcia/ui` — librairie Design System Direction C isolée : tokens CSS sémantiques et composants UX/UI purs), `apps/web` (Next.js `16.4`, React `19.1`, Tailwind CSS `4.3`, dictionnaire `i18n` typé `fr`/`en` consommant `@orcia/ui`), `apps/api` (FastAPI `0.143`), `apps/worker` (Dramatiq `2.2`), `packages/orcia-core` (noyau hexagonal à 8 domaines bornés : `orchestration`, `blackboard`, `catalog`, `ontology`, `rag`, `gates`, `permissions`, `audit_finops`) et `packages/api-client` (SDK généré automatiquement depuis Pydantic v2 / OpenAPI 3.1 avec `0-diff`).
- **Observabilité & Enveloppe d'Erreur Unique** : Journalisation JSON structurée (`structlog` côté Python, `pino` côté Node.js) propageant `trace_id` W3C OpenTelemetry, `workspace_id`, `run_id` et `step_id`. Toute erreur API retourne une enveloppe **RFC 9457 Problem Details** (`application/problem+json`) localisée selon `Accept-Language` (`fr` par défaut, `en` supporté) avec `error_code` invariant.
- **Authentification Primaire Bi-Mode & Modèle Organisationnel** : Support simultané du SSO d'entreprise (`OIDC / OAuth 2.1`) et de l'authentification locale autonome (`Email + Argon2id + MFA TOTP optionnel`) sur sessions JWT `15 min` + Refresh Token `HttpOnly` révocable en Redis. Découplage entre l'arbre hiérarchique d'équipes `org_units` (`Entreprise -> BU -> Tribu/Équipe Parente -> Sous-Équipe`) et les `workspaces` (chacun représentant une solution logicielle pouvant rattacher `N × git://`, `N × jira://`, `N × confluence://`, `db://`, `nexus://` via `workspace_datasources`).
- **Catalogue Fédéré, Surcharges à 4 Niveaux & 5 Permissions Dissociées** : Résolution à la volée des URI vers le cache content-addressable MinIO (`cas/<sha256>`, `< 50 ms` sur cache chaud), fusion déclarative déterministe à 4 niveaux (`1. Base -> 2. Standards d'Équipe TEAM -> 3. Solution WORKSPACE -> 4. Utilisateur USER`), import sans perte de packs BMAD (`BmadSkillPackAdapter`), et séparation des 5 permissions (`DISCOVER`, `EXECUTE`, `READ_SOURCE`, `EDIT`, `ADMIN`) protégeant les prompts/codes en boîte noire (`HTTP 403 ERR_READ_SOURCE_DENIED`).
- **Exécution Passthrough & Permission Broker** : Exécution par défaut avec l'identité déléguée de l'utilisateur déclencheur (secrets chiffrés en `AES-256-GCM`), interception de tout `HTTP 401/403` par `PermissionBrokerService` qui consulte la KB d'habilitations et fournit le rôle requis, l'approbateur et le lien pré-rempli de demande d'accès dans Jira.
- **Stratégie de Tests à 5 Couches & Couverture $\ge 90\%$** : Couverture unitaire minimale de `>= 90%` sur `packages/orcia-core`, tests d'intégration sur vrais conteneurs éphémères (`testcontainers-python` : PostgreSQL 18 + `pgvector`, Redis 7.4, MinIO — aucun mock SQLite/Redis), contrat OpenAPI `0-diff` + `Schemathesis`, cassettes IA `DeterministicCassetteLLM`, et tests E2E `@playwright/test`.

## Technical Decisions

- **Pureté Hexagonale Backend (`AD-1`) & Isolation Design System Frontend (`packages/ui`)** : Aucune importation de `fastapi`, `sqlalchemy`, `dramatiq`, `redis` ou `litellm` n'est autorisée dans `packages/orcia-core/domain` ni `packages/orcia-core/ports`. Symétriquement côté frontend, tous les composants UX/UI et les tokens CSS Direction C résident dans `packages/ui` (`@orcia/ui`) et n'importent jamais `next/*`, `zustand` ni `@orcia/api-client`.
- **Clés Primaires & Migrations (`Structural Seed`)** : Toutes les tables SQLAlchemy `2.1` Asyncio utilisent des clés primaires `UUIDv7` (`uuid-utils`). Les migrations Alembic (`infra/migrations/versions/`) sont créées de manière incrémentale par Story (*Just-In-Time*) avec `upgrade()` et `downgrade()` testés.
- **Chiffrement & Sécurité (`AD-6`, `AD-14`)** : Les jetons *Passthrough* sont chiffrés au repos en `AES-256-GCM`. L'héritage ascendant (*Roll-up*) donne aux responsables d'équipes parentes un accès `READ_ONLY_OBSERVER` sur les Workspaces des sous-équipes filles (sauf `visibility_mode: CONFIDENTIAL_RESTRICTED`).

## UX & Interaction Patterns

- **Direction C ("Obsidian Cockpit & Daylight Studio" dans `packages/ui`)** : Tokens CSS sémantiques obligatoires dans `packages/ui/src/styles/tokens.css` (`#0F172A` Sidebar, `#F8FAFC` Surface, `#2563EB` Primary Cobalt, `#6D28D9` Human-Led Violet réservé aux ancres humaines, `#D97706` Arbitration Amber, `#059669` Gate Emerald, `#0284C7` Ontology Cyan, `#DC2626` Stale Crimson) et polices `Inter`, `Instrument Serif` et `JetBrains Mono`.
- **Architecture Spatiale à 3 Colonnes Adaptatives (`@orcia/ui`)** :
  1. *Global Sidebar Navigation* (`235px` dépliée / `68px` repliée via `[`) intégrant en tête le **Sélecteur de Périmètre Hiérarchique (`⌘W` : `🌐 Plateforme Globale → 🏢 BU → 👥 Équipe → 🗂️ Workspace`)**, les 7 entrées du Menu Global filtrées par RBAC (*1. 💬 Cockpit & Chat*, *2. 🔔 Boîte & Mes Runs*, *3. 📦 Catalogue Fédéré*, *4. 🧬 Ontologie & KB*, *5. 🛡️ Gates & Habilitations*, *6. 📊 FinOps & Audit*, *7. ⚙️ Administration & Pilotage des Workspaces*) et le badge de *Profil Humain* en pied de barre.
  2. *Espace Central / Canvas* (`1fr`, min `640px`).
  3. *Dock Persistant Agent Concierge & Permission Broker* (`360px` à droite, repliable via `]`).
- **Composants Spécifiques Epic 1** : Badge monospace `Federated URI & RBAC Badge` (`uri-badge`) et carte ambre d'alerte d'habilitation dans le Dock Permission Broker. Toute l'interface utilisateur est servie via le dictionnaire `i18n` typé (`fr` par défaut, `en` supporté).

## Cross-Story Dependencies

- `Story 1.1` établit le monorepo, les conteneurs Docker Compose, le pipeline OpenAPI, la coquille UI Direction C et le harnais de tests à 5 couches requis par toutes les Stories suivantes.
- `Story 1.2` fournit l'authentification, le modèle `org_units` / `workspaces` / `workspace_datasources` et les 5 permissions du catalogue consommés par `Story 1.3`, `1.4` et `1.5`.
- `Story 1.3` et `Story 1.4` fournissent le résolveur d'URI fédérées (`cas/<sha256>`), la fusion de surcharges à 4 niveaux et le `PermissionBrokerService` orchestrés par les workflows système d'amorçage de la `Story 1.5`.
