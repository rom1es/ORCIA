# Story 1.2 : Authentification Hybride Bi-Mode (OIDC & Locale), Arbre Hiérarchique d'Équipes (`OrgUnit`) découplé des Espaces Solutions Multi-Sources (`Workspaces`), Rôle `TEAM_LEAD` & 5 Permissions Dissociées

- **Story / Clé** : `1-2-authentification-hybride-bi-mode-oidc-locale-arbre-hiérarchi`
- **Date** : `2026-10-25`
- **Auteur / Rôle** : `Tech Lead / Dev Senior Agent — Équipe ORCIA`
- **Contexte métier & Objectif** : Authentifier les utilisateurs via SSO d'Entreprise (`OIDC / OAuth 2.1`) ou via Authentification Locale autonome (`Email + Argon2id + MFA TOTP optionnel`), modéliser l'arbre hiérarchique d'équipes (`org_units` : `Entreprise -> BU -> Tribu/Équipe Parente -> Sous-Équipe`) découplé des `workspaces` (chacun représentant une solution logicielle agrégeant `1..N` dépôts `git://`, projets `jira://`, espaces `confluence://`, schémas `db://` et registres `nexus://` via `workspace_datasources`), gérer le coffre d'identité *Passthrough* chiffré en **AES-256-GCM** et appliquer le moteur matriciel des **5 permissions dissociées** (`DISCOVER`, `EXECUTE`, `READ_SOURCE`, `EDIT`, `ADMIN`) ainsi que le garde `ScopeAccessGuard` (`FR-21`, `AD-6`, `AD-14`, `NFR-SEC-4`).
- **Décisions d'Architecture & Références** : `AD-1`, `AD-6`, `AD-14`, `AD-17`, `FR-21`, `UX-DR2`, `UX-DR11`, `NFR-SEC-4`
- **Commits associés** : `À renseigner en Section 3 après implémentation`

---

## 1. Analyse du Besoin & Étude d'Impact Tech Lead (Avant Implémentation)

### 1.1 Contexte & Problématique
- **Problème ou opportunité métier / technique** : La Story 1.1 a livré le monorepo hybride, la coquille Direction C (`@orcia/ui`) et la topologie de navigation statique de démonstration (`/api/v1/navigation/shell`). Pour permettre aux équipes de travailler de manière isolée sur leurs différentes solutions logicielles (`Workspaces`) tout en permettant aux responsables d'équipes parentes / BU d'exercer une supervision consolidée (*Roll-up* en `READ_ONLY_OBSERVER` + FinOps) et de partager des agents/workflows en boîte noire (`DISCOVER` + `EXECUTE` sans `READ_SOURCE`), la plateforme doit disposer de son modèle relationnel organisationnel complet, d'une authentification bi-mode (`OIDC` + `Locale Argon2id/TOTP`), d'un coffre de secrets *Passthrough* (`AES-256-GCM`) et d'un moteur d'autorisation matricielle pur dans `packages/orcia-core/permissions`.
- **Comportement actuel vs Comportement attendu** :
  - *Actuel* : `/api/v1/navigation/shell` retourne un arbre `ScopeNode` statique de 4 nœuds sans contexte utilisateur authentifié, et aucune table d'identité, d'arbre `org_units`, de `workspaces`, de `workspace_datasources` ou d'ACL du catalogue n'existe encore dans PostgreSQL 18.
  - *Attendu* :
    1. Migration Alembic `0002_story_1_2_auth_org_workspaces_permissions.py` créant les 8 tables `UUIDv7` (`org_units`, `users`, `transverse_groups`, `workspaces`, `workspace_datasources`, `workspace_memberships`, `workspace_invitations`, `user_passthrough_credentials`, `catalog_acl_entries`) avec contraintes d'intégrité et index B-Tree.
    2. Authentification bi-mode (`POST /api/v1/auth/login/local`, `POST /api/v1/auth/login/oidc`, `POST /api/v1/auth/refresh`, `POST /api/v1/auth/logout`, `GET /api/v1/auth/me`) émettant un jeton d'accès JWT court (`15 min`) + Refresh Token `HttpOnly / Secure / SameSite=Strict` révocable dans Redis.
    3. Moteur pur `packages/orcia-core/permissions` évaluant :
       - l'héritage ascendant (*Roll-up*) le long de `org_units` : un responsable (`BU_DIRECTOR` / `TEAM_LEAD`) d'une unité parente reçoit automatiquement `READ_ONLY_OBSERVER` et l'agrégation FinOps sur les Workspaces des sous-équipes filles, **sauf** si le Workspace est en `visibility_mode: CONFIDENTIAL_RESTRICTED`,
       - l'isolation stricte entre `Workspace 1` et `Workspace 2` d'une même équipe (y compris pour une équipe partenaire invitée sur `Workspace 1`),
       - l'héritage descendant des 5 permissions dissociées (`DISCOVER`, `EXECUTE`, `READ_SOURCE`, `EDIT`, `ADMIN`) sur une ressource `SHARED_TEAM` / `SHARED_BU` avec masquage boîte noire (`🔒 Source masquée`, `HTTP 403 ERR_READ_SOURCE_DENIED` si `READ_SOURCE` est absent),
       - le chiffrement/déchiffrement `AES-256-GCM` avec clé dérivée par utilisateur (`HKDF-SHA256`) pour `user_passthrough_credentials`.
    4. Garde `ScopeAccessGuard` côté FastAPI protégeant les routes de mutation (`HTTP 403 ERR_OBSERVER_MODE_READ_ONLY` en mode observateur) et filtrant les entrées non autorisées du Menu Global à 7 modules dans `/api/v1/navigation/shell` et dans `@orcia/ui` / `apps/web`.
- **Contraintes spécifiques (Hexagone, Performance, Sécurité RBAC, append-only)** :
  - `packages/orcia-core/domain` et `packages/orcia-core/ports` (ainsi que la logique pure de `packages/orcia-core/permissions`) ne doivent importer aucun framework (`fastapi`, `sqlalchemy`, `dramatiq`, `redis`, `litellm`).
  - `packages/ui` (`@orcia/ui`) reste strictement isolé (`0` import `next/*`, `zustand`, `@orcia/api-client`, `0` couleur hex hors `tokens.css`).
  - Support `i18n` complet (`fr` par défaut, `en` supporté) pour les nouveaux codes d'erreur RFC 9457 (`ERR_AUTH_INVALID_CREDENTIALS`, `ERR_AUTH_MFA_INVALID`, `ERR_AUTH_TOKEN_REVOKED`, `ERR_SCOPE_ACCESS_DENIED`) et pour le sélecteur de profil / gouvernance dans `apps/web`.

### 1.2 Analyse d'Impact GitNexus & Volumétrie du Codebase
- **Symboles et flux impactés (`gitnexus_query` / `gitnexus_context` / `gitnexus_impact`)** :
  - `gitnexus_query({repo: "ORCIA", search_query: "permissions shell navigation exceptions seeder"})` : identifie les 3 points d'extension préparés en Story 1.1 : `packages/orcia-core/src/orcia_core/domain/exceptions.py`, `packages/orcia-core/src/orcia_core/schemas/shell.py` et `apps/api/src/orcia_api/routers/shell.py`.
  - `gitnexus_impact({repo: "ORCIA", target: "get_shell_navigation", direction: "upstream"})` : `risk: UNKNOWN` (confirmé par recherche textuelle : appelé via HTTP par `packages/api-client/src/index.ts` et testé dans `tests/unit/test_orcia_core_and_api.py` et `tests/contract/test_openapi_contract.py`). L'ajout de paramètres optionnels rétrocompatibles (`scope_id`, en-tête `Authorization` optionnel avec repli sur le profil de démonstration par défaut lorsque non fourni) préserve 100 % des tests existants tout en activant le filtrage RBAC dynamique.
  - `gitnexus_impact({repo: "ORCIA", target: "OrciaDomainError", direction: "upstream"})` : `risk: UNKNOWN` (confirmé par recherche textuelle : utilisé dans `apps/api/src/orcia_api/middleware/trace_and_error.py` et `tests/unit/test_orcia_core_and_api.py`).
- **Exploration Base de Données & Chiffres Clés** :
  - Base PostgreSQL 18 + `pgvector` actuelle : révision `0001_story_1_1` (`vector` extension + fonction trigger `orcia_prevent_append_only_mutation()`).
  - La révision `0002_story_1_2` ajoute 9 tables relationnelles à clés primaires `UUIDv7` (`org_units`, `users`, `transverse_groups`, `user_transverse_groups`, `workspaces`, `workspace_datasources`, `workspace_memberships`, `workspace_invitations`, `user_passthrough_credentials`, `catalog_acl_entries`).
- **Contrôle de volumétrie des fichiers (`seuil 300–400 lignes`)** :
  - Tous les fichiers existants font entre `5` et `245` lignes (`GlobalSidebar.tsx` : `244` lignes, `AppShell.tsx` : `245` lignes, `exceptions.py` : `230` lignes).
  - Pour éviter que `packages/orcia-core/src/orcia_core/permissions/` ou `apps/api/src/orcia_api/routers/` ne dépassent `250` lignes par fichier, le domaine `permissions` est découpé dès la création en 4 modules spécialisés de $< 220$ lignes :
    - `permissions/models.py` (entités de domaine pures : `OrgUnitNode`, `WorkspaceEntity`, `WorkspaceDatasourceEntity`, `UserIdentity`, `CatalogAclEntry`, enums des rôles et des 5 permissions),
    - `permissions/crypto.py` (`Argon2idPasswordHasher`, `TotpVerifier`, `PassthroughVaultCipher` en `AES-256-GCM` + `HKDF-SHA256`, et jetons JWT/Refresh signés `HMAC-SHA256`),
    - `permissions/evaluator.py` (`MatrixPermissionEvaluator` : résolution de l'arbre `org_units`, *Roll-up* ascendant `READ_ONLY_OBSERVER` + FinOps avec blocage `CONFIDENTIAL_RESTRICTED`, isolation inter-Workspaces et héritage descendant des 5 permissions `DISCOVER`, `EXECUTE`, `READ_SOURCE`, `EDIT`, `ADMIN` avec levée de `ReadSourceDeniedError`),
    - `permissions/service.py` (`AuthAndOrganizationService` + magasin de sessions révocables en mémoire/Redis).

### 1.3 Opportunités de Factorisation & Dette Technique Identifiée
- **Factorisations réalisées (`DRY` / Primitives partagées)** :
  - Réutilisation de `generate_uuid7_str` (`packages/orcia-core/domain/identifiers.py`) pour toutes les entités `OrgUnit`, `Workspace`, `WorkspaceDatasource`, `User` et `CatalogAclEntry`.
  - Réutilisation du catalogue `ERROR_CATALOG` (`packages/orcia-core/domain/exceptions.py`) et du middleware RFC 9457 (`apps/api/src/orcia_api/middleware/trace_and_error.py`) pour toutes les erreurs d'authentification et d'autorisation (`HTTP 401`/`403`) en `fr` et `en`.
  - Réutilisation de `UpsertSpec` (`packages/orcia-core/bootstrap/seeder.py`) pour l'amorçage idempotent de l'arbre d'organisation de référence (`Entreprise -> BU -> Équipe Parente -> Sous-Équipe` et ses 2 Workspaces multi-sources `Workspace 1 : Solution Paiement` et `Workspace 2 : Solution Fidélité`).
- **Refactoring pré-Story exécuté immédiatement (Étape 0)** :
  - _Aucun fichier existant ne dépasse 245 lignes ; aucune dette structurelle préexistante._
- **Tickets de dette technique / refactoring créés (`sprint-status.yaml` / `epics.md`)** :
  - _Aucun ticket de dette supplémentaire requis ; toutes les exigences de la Story 1.2 sont couvertes sans compromis._

---

## 2. Plan d'Implémentation

### 2.1 Schéma de Données, Migrations Alembic & Scripts de Données
- **Migration Alembic (`infra/migrations/versions/0002_story_1_2_auth_org_workspaces_permissions.py`)** :
  - Tables créées en SQL brut (`op.execute(sa.text(...))`) avec clés primaires `UUID` (`UUIDv7`) :
    1. `org_units` (`id`, `slug UNIQUE`, `name`, `unit_type CHECK (ENTERPRISE|BU|TRIBE|TEAM|SUB_TEAM)`, `parent_id FK -> org_units.id`, `created_at`). Index B-Tree sur `parent_id`.
    2. `users` (`id`, `email UNIQUE`, `display_name`, `auth_mode CHECK (OIDC|LOCAL|HYBRID)`, `oidc_subject UNIQUE NULL`, `password_hash_argon2id NULL`, `totp_secret_encrypted NULL`, `totp_enabled BOOL`, `human_profile_archetype`, `platform_role CHECK (PLATFORM_ADMIN|BU_DIRECTOR|TEAM_LEAD|CONTRIBUTOR|GATE_REVIEWER|ONTOLOGY_STEWARD_L3|OBSERVER)`, `primary_org_unit_id FK -> org_units.id`, `is_active BOOL`, `created_at`).
    3. `transverse_groups` (`id`, `slug UNIQUE`, `name`, `description`, `created_at`) et table de liaison `user_transverse_groups` (`user_id`, `group_id`, PK composite).
    4. `workspaces` (`id`, `slug UNIQUE`, `name`, `owner_org_unit_id FK -> org_units.id`, `visibility_mode CHECK (STANDARD|CONFIDENTIAL_RESTRICTED)`, `settings_jsonb JSONB`, `finops_cost_usd NUMERIC(12,4)`, `created_at`). Index B-Tree sur `owner_org_unit_id`.
    5. `workspace_datasources` (`id`, `workspace_id FK -> workspaces.id ON DELETE CASCADE`, `alias`, `scheme CHECK (git|jira|confluence|db|nexus)`, `uri`, `role`, `execution_identity CHECK (passthrough|service_principal)`, `freshness_ttl_days INT`, `created_at`, `UNIQUE(workspace_id, alias)`). Index B-Tree sur `workspace_id`.
    6. `workspace_memberships` (`id`, `workspace_id FK -> workspaces.id ON DELETE CASCADE`, `user_id FK -> users.id ON DELETE CASCADE NULL`, `invited_org_unit_id FK -> org_units.id ON DELETE CASCADE NULL`, `role CHECK (TEAM_LEAD|CONTRIBUTOR|GATE_REVIEWER|ONTOLOGY_STEWARD_L3|OBSERVER)`, `access_mode CHECK (CONTRIBUTOR_ACTION_REQUIRED|READ_ONLY_OBSERVER)`, `created_at`).
    7. `workspace_invitations` (`id`, `workspace_id FK -> workspaces.id ON DELETE CASCADE`, `email`, `assigned_role`, `assigned_archetype`, `token_sha256 UNIQUE`, `expires_at`, `accepted_at NULL`, `created_at`).
    8. `user_passthrough_credentials` (`id`, `user_id FK -> users.id ON DELETE CASCADE`, `connector_scheme CHECK (git|jira|confluence|db|nexus)`, `target_host`, `ciphertext_b64 TEXT`, `nonce_b64 TEXT`, `key_version INT`, `created_at`, `UNIQUE(user_id, connector_scheme, target_host)`).
    9. `catalog_acl_entries` (`id`, `resource_uri`, `visibility_scope CHECK (DRAFT|SHARED_WORKSPACE|SHARED_TEAM|SHARED_BU|PUBLISHED_ORG)`, `owner_org_unit_id FK -> org_units.id`, `owner_workspace_id FK -> workspaces.id NULL`, `grantee_org_unit_id FK -> org_units.id NULL`, `grantee_workspace_id FK -> workspaces.id NULL`, `can_discover BOOL`, `can_execute BOOL`, `can_read_source BOOL`, `can_edit BOOL`, `can_admin BOOL`, `system_prompt_secret TEXT NULL`, `created_at`).
  - `downgrade()` : suppression ordonnée des tables créées en `0002` sans toucher aux objets de `0001`.
- **Seeder & Script de Maintenance (`infra/scripts/maintenance/01_backfill_default_org_tree.py`)** :
  - Seeder idempotent dans `packages/orcia-core/bootstrap/seeder.py` et script de maintenance `01_backfill_default_org_tree.py` supportant `--dry-run` (rollback par défaut) et `--apply` pour vérifier/peupler l'arbre `org_units` et les Workspaces de référence.

### 2.2 Noyau Hexagonal, Algorithmes & Workers (`packages/orcia-core/`, `apps/worker/`)
- **Domaine & Exceptions (`packages/orcia-core/src/orcia_core/domain/exceptions.py`)** :
  - Ajout des codes d'erreur localisés `fr`/`en` : `ERR_AUTH_INVALID_CREDENTIALS` (`401`), `ERR_AUTH_MFA_INVALID` (`401`), `ERR_AUTH_TOKEN_REVOKED` (`401`), `ERR_SCOPE_ACCESS_DENIED` (`403`) en complément de `ERR_OBSERVER_MODE_READ_ONLY` (`403`) et `ERR_READ_SOURCE_DENIED` (`403`).
- **Cryptographie & Authentification Bi-Mode (`packages/orcia-core/src/orcia_core/permissions/crypto.py`)** :
  - `Argon2idPasswordHasher` (via `argon2-cffi` déjà présent dans `.venv`).
  - `TotpManager` (RFC 6238 HMAC-SHA1 à 6 chiffres, stdlib `hmac`/`hashlib`/`base64`).
  - `PassthroughVaultCipher` : chiffrement authentifié **AES-256-GCM** (via `pycryptodome` `Crypto.Cipher.AES` déjà présent dans `.venv`) avec dérivation de clé par `(master_key, user_id)` via HMAC-SHA256 (HKDF), nonce aléatoire de 96 bits (`12` octets) et tag d'authentification de 128 bits (`16` octets) vérifié au déchiffrement (`NFR-SEC-4`).
  - `JwtSessionManager` : émission et vérification de JWT d'accès courts (`15 min`, `900 s`) et Refresh Tokens signés avec identifiant `jti` (`UUIDv7`) révocable en Redis.
- **Évaluateur Matriciel RBAC, Roll-up & 5 Permissions Dissociées (`packages/orcia-core/src/orcia_core/permissions/evaluator.py`)** :
  - Calcul de l'arbre `org_units` (ancêtres et descendants d'une unité organisationnelle).
  - Résolution des `Workspaces` accessibles pour un utilisateur :
    - Membre direct (`TEAM_LEAD`, `CONTRIBUTOR`, etc.) sur son Workspace : accès complet aux `N × git://`, `N × jira://`, `N × confluence://` du `Workspace 1` et isolation stricte vis-à-vis du `Workspace 2`.
    - Équipe partenaire invitée sur `Workspace 1` (`invited_org_unit_id`) : accès strictement limité à `Workspace 1`, visibilité `0` sur `Workspace 2`.
    - Responsable d'équipe parente / Tribu / BU (`BU_DIRECTOR` ou `TEAM_LEAD` d'un `org_unit` ancêtre de `workspace.owner_org_unit_id`) : héritage ascendant (*Roll-up*) donnant automatiquement accès en `READ_ONLY_OBSERVER` et agrégation FinOps (`finops_cost_usd`) sur tous les Workspaces des sous-équipes filles, **à l'exception** des Workspaces marqués `CONFIDENTIAL_RESTRICTED` (dont le contenu métier et les runs sont masqués sauf habilitation explicite).
  - Évaluation des **5 permissions dissociées** (`DISCOVER`, `EXECUTE`, `READ_SOURCE`, `EDIT`, `ADMIN`) sur une ressource du catalogue :
    - Une ressource publiée en `SHARED_TEAM` ou `SHARED_BU` par une équipe parente avec `DISCOVER=True, EXECUTE=True, READ_SOURCE=False` est automatiquement découvrable et exécutable par héritage descendant dans tous les Workspaces des sous-équipes filles.
    - L'inspection de la ressource retourne `source_masked: True` (`🔒 Source masquée`), et tout appel demandant le code/prompt source (`require_read_source=True`) lève `ReadSourceDeniedError` (`HTTP 403 ERR_READ_SOURCE_DENIED`).
  - Filtrage des 7 modules du Menu Global selon le rôle (`OBSERVER` / `CONTRIBUTOR` n'ont pas accès au module `7. Administration` `/workspaces` réservé aux `PLATFORM_ADMIN`, `BU_DIRECTOR`, `TEAM_LEAD`, tandis que côté API toute tentative d'accès non autorisé lève `HTTP 403`).

### 2.3 Couche Backend FastAPI, Middlewares & Contrats OpenAPI (`apps/api/`, `packages/api-client/`)
- **Schémas Pydantic v2 (`packages/orcia-core/src/orcia_core/schemas/auth_and_org.py` & `shell.py`)** :
  - Modèles typés `LocalLoginRequest`, `OidcLoginRequest`, `AuthTokenResponse`, `UserMeResponse`, `OrgUnitTreeItem`, `WorkspaceDatasourceItem`, `WorkspaceSummaryItem`, `CatalogResourceInspectionResponse`, `PassthroughSecretStoreRequest`, `PassthroughSecretMetadataResponse`.
  - Enrichissement rétrocompatible de `HumanProfileBadge` (ajout de `role`, `org_unit_id`, `org_unit_name` avec valeurs par défaut).
- **Routes FastAPI (`apps/api/src/orcia_api/routers/auth.py`, `org_and_workspaces.py`, `shell.py`) & Garde `ScopeAccessGuard`** :
  - `POST /api/v1/auth/login/local` (Email + Argon2id + TOTP optionnel) & `POST /api/v1/auth/login/oidc` (échange de jeton/claims OIDC) : émettent le JWT `15 min` et déposent le cookie `orcia_refresh_token` (`HttpOnly; Secure; SameSite=Strict; Path=/api/v1/auth`).
  - `POST /api/v1/auth/refresh` & `POST /api/v1/auth/logout` : rotation / révocation immédiate du `jti` dans Redis (ou store en mémoire partagé si Redis non configuré).
  - `GET /api/v1/auth/me` : retourne le *Profil Humain* complet (`archetype_key`, `platform_role`, arbre `org_units`, liste des `workspaces` accessibles avec leurs `datasources` `N × git://`, `N × jira://`, `N × confluence://`, et les 7 modules filtrés par RBAC).
  - `GET /api/v1/workspaces` (vue consolidée avec *Roll-up* FinOps et isolation `CONFIDENTIAL_RESTRICTED`), `POST /api/v1/workspaces/{workspace_id}/mutations/check` (protégé par `ScopeAccessGuard`, rejetant `READ_ONLY_OBSERVER` avec `HTTP 403 ERR_OBSERVER_MODE_READ_ONLY`), `GET /api/v1/catalog/resources/{resource_id}/inspect` et `GET /api/v1/catalog/resources/{resource_id}/source` (levant `HTTP 403 ERR_READ_SOURCE_DENIED` si `READ_SOURCE` est absent), et `POST /api/v1/auth/passthrough-credentials` (stockage chiffré `AES-256-GCM`).
  - Régénération `0-diff` de `packages/api-client/openapi.json` et `packages/api-client/src/generated/schema.ts`.

### 2.4 Interface Utilisateur Next.js Direction C & Composants Cognitifs (`packages/ui`, `apps/web/`)
- **Design System (`packages/ui` / `@orcia/ui`)** :
  - `GlobalSidebar.tsx` : filtrage automatique des entrées de modules où `module.enabled === false` (masquage des modules non autorisés par RBAC) et affichage enrichi du badge de *Profil Humain* en pied de barre (Archétype, Rôle RBAC, unité d'équipe et mode d'accès).
  - Nouveau composant pur `WorkspaceTopologyPanel.tsx` dans `packages/ui/src/shell/WorkspaceTopologyPanel.tsx` : affiche l'arbre hiérarchique d'équipes (`org_units`), l'isolation des Workspaces multi-sources (`N × git://`, `N × jira://`, `N × confluence://`), le badge d'agrégation FinOps en *Roll-up* pour les équipes parentes, l'état des ressources héritées (`DISCOVER` + `EXECUTE` avec badge `🔒 Source masquée` lorsque `READ_SOURCE` est absent) et un sélecteur de persona RBAC (`Karim — PLATFORM_ADMIN`, `Claire — BU_DIRECTOR`, `Marc — TEAM_LEAD`, `Nadia — CONTRIBUTOR`, `Partenaire Externe`) permettant de tester interactivement le filtrage RBAC de la Sidebar et le mode `READ_ONLY_OBSERVER`.
- **Intégration `apps/web` & Dictionnaire `i18n` (`fr`/`en`)** :
  - Extension paritaire de `apps/web/src/i18n/locales/fr.ts` et `en.ts` (sections `authAndOrg`, personas, rôles, permissions dissociées).
  - Intégration dans `ShellContainer.tsx` et `ModuleWorkspaceView.tsx`.

---

## 3. Bilan des Modifications & Résultats (Post-Implémentation)

### 3.1 Fichiers Développés & Modifiés
| Fichier | Nature (Création / Modification / Refactoring) | Description synthétique |
| :--- | :--- | :--- |
| `infra/migrations/versions/0002_story_1_2_auth_org_workspaces_permissions.py` | Création (`242` lignes) | Révision Alembic `0002` en SQL brut (`op.execute(sa.text(...))`) créant les 10 tables `UUIDv7` (`org_units`, `users`, `transverse_groups`, `user_transverse_groups`, `workspaces`, `workspace_datasources`, `workspace_memberships`, `workspace_invitations`, `user_passthrough_credentials`, `catalog_acl_entries`) et leurs index B-Tree (`idx_org_units_parent_id`, `idx_workspaces_owner_org_unit_id`, `idx_workspace_datasources_workspace_id`, `idx_workspace_memberships_user_id`, `idx_workspace_memberships_invited_org_unit_id`, `idx_catalog_acl_entries_resource_id`). |
| `packages/orcia-core/src/orcia_core/bootstrap/seeder.py` | Modification (`286` lignes) | Enrichissement du seeder système avec l'arbre `org_units` (`ENTERPRISE -> BU -> TEAM -> SUB_TEAM`), les Workspaces de référence et leurs `UpsertSpec` idempotents (`ON CONFLICT DO UPDATE` avec `insert_only_columns=("id",)`). |
| `infra/scripts/maintenance/01_backfill_default_org_tree.py` | Création (`189` lignes) | Script de maintenance transactionnel supportant `--dry-run` (rollback par défaut) et `--apply` pour vérifier/peupler l'arbre `org_units` et les Workspaces multi-sources. |
| `packages/orcia-core/src/orcia_core/domain/exceptions.py` | Modification (`301` lignes) | Ajout des exceptions métier localisées (`fr`/`en`) : `InvalidCredentialsError` (`ERR_AUTH_INVALID_CREDENTIALS`, 401), `InvalidMfaCodeError` (`ERR_AUTH_MFA_INVALID`, 401), `RevokedTokenError` (`ERR_AUTH_TOKEN_REVOKED`, 401) et `ScopeAccessDeniedError` (`ERR_SCOPE_ACCESS_DENIED`, 403). |
| `packages/orcia-core/src/orcia_core/permissions/models.py` | Création (`185` lignes) | Modèles de domaine purs et immuables (`OrgUnitNode`, `WorkspaceEntity`, `WorkspaceDatasourceEntity`, `WorkspaceMembershipEntity`, `UserIdentity`, `CatalogAclEntry`, `EffectiveResourcePermissions`, `WorkspaceAccessSummary`, `PassthroughSecretRecord`). |
| `packages/orcia-core/src/orcia_core/permissions/crypto.py` | Création (`293` lignes) | `Argon2idPasswordHasher`, `TotpManager` (RFC 6238 HMAC-SHA1 à 6 chiffres), `PassthroughVaultCipher` (`AES-256-GCM` + dérivation `HKDF-SHA256` par utilisateur, nonce `96 bits`, tag `128 bits`) et `JwtSessionManager` (JWT `15 min` + Refresh Token `jti` `UUIDv7` révocable). |
| `packages/orcia-core/src/orcia_core/permissions/evaluator.py` | Création (`283` lignes) | `MatrixPermissionEvaluator` implémentant la résolution hiérarchique `org_units`, l'isolation stricte entre Workspaces et invitations partenaires, le *Roll-up* ascendant (`READ_ONLY_OBSERVER` + agrégation FinOps hors `CONFIDENTIAL_RESTRICTED`), l'évaluation des 5 permissions dissociées (`DISCOVER`, `EXECUTE`, `READ_SOURCE`, `EDIT`, `ADMIN`) avec boîte noire `ReadSourceDeniedError` et le filtrage RBAC des 7 modules. |
| `packages/orcia-core/src/orcia_core/permissions/service.py` | Création (`289` lignes) | `AuthAndOrganizationService` orchestrant l'authentification bi-mode (`local` / `oidc`), la rotation/révocation de Refresh Tokens (`jti` avec TTL monotone et verrou thread-safe), la topologie multi-personas (`Karim`, `Claire`, `Marc`, `Nadia`, `Partenaire`), l'inspection de ressources du catalogue et le coffre *Passthrough*. |
| `packages/orcia-core/src/orcia_core/schemas/auth_and_org.py` & `shell.py` | Création / Modification (`200` & `204` lignes) | Schémas Pydantic v2 (`LocalLoginRequest`, `OidcLoginRequest`, `AuthTokenResponse`, `UserMeResponse`, `WorkspacesListResponse`, `ScopeMutationCheckResponse`, `CatalogResourceInspectionResponse`, `CatalogResourceSourceResponse`, `PassthroughSecretStoreRequest`, `PassthroughSecretMetadataResponse`) et enrichissement rétrocompatible de `HumanProfileBadge`. |
| `apps/api/src/orcia_api/routers/auth.py`, `org_and_workspaces.py`, `shell.py` & `main.py` | Création / Modification (`277`, `147`, `116` & `41` lignes) | Endpoints `/api/v1/auth/{login/local,login/oidc,refresh,logout,me,passthrough-credentials}`, `/api/v1/workspaces`, `/api/v1/workspaces/{workspace_id}/mutations/check` (`ScopeAccessGuard`), `/api/v1/catalog/resources/{resource_id}/{inspect,source}` et `/api/v1/navigation/shell` (`?scope_id=...&persona_key=...`). |
| `packages/api-client/openapi.json`, `src/generated/schema.ts` & `src/index.ts` | Modification (`182` lignes dans `index.ts`) | Régénération `0-diff` du contrat OpenAPI 3.1 et ajout des méthodes typées (`loginLocal`, `loginOidc`, `refreshSession`, `logoutSession`, `getMe`, `getWorkspaces`, `checkWorkspaceMutation`, `inspectCatalogResource`, `getCatalogResourceSource`, `storePassthroughSecret`). |
| `packages/ui/src/shell/{types.ts,GlobalSidebar.tsx,WorkspaceTopologyPanel.tsx}` & `src/index.ts` | Création / Modification (`124`, `255` & `266` lignes) | Masquage dans `GlobalSidebar` des modules où `enabled === false`, affichage du rôle RBAC et de l'unité d'équipe dans le badge de *Profil Humain*, et création du composant pur `WorkspaceTopologyPanel` dans `@orcia/ui`. |
| `apps/web/src/i18n/{types.ts,locales/fr.ts,locales/en.ts}` & `src/components/{ShellContainer.tsx,ModuleWorkspaceView.tsx}` | Modification (`26`, `129`, `129`, `168` & `192` lignes) | Parité stricte des dictionnaires `fr`/`en` (section `authAndOrg`) et intégration du sélecteur de persona RBAC (`Karim`, `Claire`, `Marc`, `Nadia`, `Partenaire`) et de la topologie multi-Workspaces dans la coquille Direction C. |
| `tests/unit/test_permissions_and_auth.py`, `tests/integration/test_real_containers.py`, `packages/api-client/src/__tests__/client.test.ts`, `packages/ui/src/__tests__/shell.test.tsx`, `apps/web/src/__tests__/i18n-and-shell.test.tsx`, `apps/web/e2e/shell.spec.ts` | Création / Modification | Suite complète de tests sur les 5 couches (`AD-17`). |

### 3.2 Résultats Chiffrés, Métriques & Qualité
- **Couverture de tests Python (`pytest --cov=packages/orcia-core --cov-fail-under=90`)** : **`>= 98 %`** global (`19 passed`), dont `100 %` sur `permissions/models.py`, `99 %` sur `permissions/crypto.py`, `99 %` sur `permissions/service.py`, `94 %` sur `permissions/evaluator.py` et `100 %` sur `schemas/auth_and_org.py`.
- **Tests Unitaires & Intégration TypeScript (`pnpm turbo run lint typecheck test`)** : **`9/9 tasks successful`** (`3` tests dans `@orcia/api-client`, `4` tests dans `@orcia/ui`, `4` tests dans `@orcia/web`).
- **Volumétrie des fichiers** : Tous les modules de `permissions/` et routes API respectent strictement la limite de 295 lignes (`permissions/crypto.py` à `293` lignes, `permissions/service.py` à `289` lignes, `seeder.py` à `286` lignes, `permissions/evaluator.py` à `283` lignes, `routers/auth.py` à `277` lignes).
- **Qualité statique & Architecture** :
  - `.venv/bin/ruff check . && .venv/bin/ruff format --check .` : `0 warning / 0 error` (`114 files already formatted`)
  - `.venv/bin/mypy --strict packages/orcia-core apps/api apps/worker` : `Success: no issues found in 40 source files`
  - `pnpm turbo run lint typecheck` : `0 error`
  - `.venv/bin/python .agent/skills/bmad-architecture/scripts/lint_spine.py --workspace docs/planning-artifacts/architecture/architecture-ORCIA-2026-10-24` : `{"ok": true, "total_findings": 0}`
  - `gitnexus_detect_changes()` : Index GitNexus reconstruit (`1,808 nodes | 2,563 edges | 35 clusters | 86 flows`) et `detect_changes(scope="all", repo="ORCIA")` exécuté (`26` fichiers modifiés correspondant exactement au périmètre de la Story 1.2).

### 3.3 Validation & Procédure de Test (5 Couches `AD-17`)
- **Couche 1 — Tests Unitaires & Propriétés (`pytest` + `hypothesis`, `Vitest`)** :
  - `tests/unit/test_permissions_and_auth.py` : test property-based `hypothesis` vérifiant sur des secrets et identifiants arbitraires que `PassthroughVaultCipher` (`AES-256-GCM` + `HKDF-SHA256`) produit des ciphertexts distincts à chaque chiffrement, restitue l'exact secret au déchiffrement pour le bon `user_id` et rejette tout déchiffrement croisé entre utilisateurs ou altération d'octet ; tests unitaires de `Argon2idPasswordHasher`, `TotpManager`, `JwtSessionManager`, `MatrixPermissionEvaluator` (isolation `Workspace 1` / `Workspace 2`, *Roll-up* `READ_ONLY_OBSERVER` + FinOps hors `CONFIDENTIAL_RESTRICTED`, invitation partenaire, boîte noire `DISCOVER + EXECUTE` sans `READ_SOURCE` levant `HTTP 403 ERR_READ_SOURCE_DENIED`), et `01_backfill_default_org_tree.py` (`--dry-run` et `--apply`).
  - `packages/ui/src/__tests__/shell.test.tsx` & `apps/web/src/__tests__/i18n-and-shell.test.tsx` : validation du masquage des modules `enabled: false` dans `GlobalSidebar`, de l'affichage du rôle et de l'unité dans le badge de *Profil Humain*, du composant `WorkspaceTopologyPanel` et de la bascule de persona RBAC (`Claire`, `Nadia`).
- **Couche 2 — Tests d'Intégration (`testcontainers-python` : PostgreSQL 18 + `pgvector`, Redis 7.4, MinIO)** :
  - `tests/integration/test_real_containers.py` : cycle complet `alembic upgrade head` (`0001` + `0002`) $\rightarrow$ vérification des 10 tables `UUIDv7` et de l'idempotence de `01_backfill_default_org_tree.py` (`--dry-run` rollback puis `--apply` commit) $\rightarrow$ `alembic downgrade 0001_story_1_1` $\rightarrow$ `alembic downgrade base` $\rightarrow$ `alembic upgrade head`, ainsi que la révocation atomique des Refresh Tokens (`jti`) dans un vrai conteneur **Redis 7.4**.
- **Couche 3 — Tests de Contrat API (`openapi-typescript` 0-diff + `Schemathesis`)** :
  - `tests/contract/test_openapi_contract.py` & `packages/api-client/src/__tests__/client.test.ts` : fuzzing `Schemathesis` sur l'ensemble des routes OpenAPI 3.1 (`/api/v1/health`, `/api/v1/navigation/shell`, `/api/v1/auth/*`, `/api/v1/workspaces/*`, `/api/v1/catalog/resources/*`) et vérification des enveloppes RFC 9457 (`ERR_AUTH_INVALID_CREDENTIALS`, `ERR_AUTH_MFA_INVALID`, `ERR_AUTH_TOKEN_REVOKED`, `ERR_OBSERVER_MODE_READ_ONLY`, `ERR_READ_SOURCE_DENIED`) avec `trace_id` W3C et localisation `Accept-Language: fr|en`.
- **Couche 4 — Tests d'Orchestration IA (`DeterministicCassetteLLM`)** :
  - `tests/unit/test_core_invariants.py` : rejeu déterministe `DeterministicCassetteLLM` à `0 $` en CI.
- **Couche 5 — Tests E2E & Accessibilité (`@playwright/test` Desktop `1440x900` & Mobile `390x844`)** :
  - `apps/web/e2e/shell.spec.ts` : validation sur les deux profils (`[desktop-cockpit]` et `[mobile-companion]`) de la coquille 3 colonnes, de la bascule de persona RBAC (`Nadia` masquant le module `7. Administration`, `Claire` activant la bannière `READ_ONLY_OBSERVER`), du panneau `WorkspaceTopologyPanel` (sources `git://`, `jira://`, `confluence://` et badge `🔒 Source masquée` / `🔒 Source masked`), des raccourcis clavier (`[`, `]`, `⌘W`) et de la bascule `FR` / `EN`.
