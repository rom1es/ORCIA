# Story 17.4 — Onglet `Connecteurs & SSO` (Socle), Enrichissement de `👤 Mon Compte` (`Passthrough` par Connecteur) & Synchronisation RAG dans `Mes Espaces › Sources` avec Repli sur Membre Référent

- **Date** : 2026-11-11
- **Story / Clé Sprint** : `17-4-connecteurs-sso-socle-mon-compte-passthrough-et-repli-referent-rag` (`Epic 17` — ultime User Story clôturant l'Epic 17)
- **Capacité(s)** : `CAP-003`, `CAP-054`, `CAP-063`, `CAP-080` — classification : `feature`
- **Auteur / Contexte** : Résolution complète de la confusion structurelle entre les **Connecteurs d'Entreprise & SSO du Socle** (`/settings` › onglet 4 `Connecteurs & SSO`), les **Jetons personnels `Passthrough` par outil** (`👤 Mon Compte` › `Mes Connexions Outils`) garantissant l'attribution nominative des actions Jira/Git, et les **Sources documentaires d'Espace** (`Mes Espaces › Sources`) dotées d'un choix explicite d'identité de synchronisation RAG lecture seule (`SERVICE_ACCOUNT` vs `TEAM_REFERENT_USER` avec bascule automatique en pause `PAUSED_REFERENT_RENEWAL_REQUIRED`). Exigences couvertes : `FR-21`, `FR-22`, `FR-31`, `FR-32`, `FR-34`, `AD-6`, `AD-19`, `AD-21`, `NFR-SEC-4`.
- **Commits associés** : _À compléter en Section 3 après validation des portes CI_

---

## 1. Analyse du Besoin & Étude d'Impact Tech Lead (Pré-Implémentation)

### 1.1 Contexte & Problématique
- **Anomalies structurelles identifiées lors de l'audit Epic 17 (Décisions #8, #9, #10, #11)** :
  1. **Pollution de `workspaces[0]` et faux secret dans `/settings`** : `SettingsSecondaryTabsSection.tsx` utilisait un `<SecretField />` purement éphémère en `useState` (perdu au `F5`) et appelait `registerDatasource({ workspaceName: workspaces[0]?.name })`, injectant une source projet parasite dans le premier espace au lieu d'enregistrer une instance d'outil d'entreprise au niveau Socle.
  2. **Modale `👤 Mon Compte` incomplète** : `UserSettingsModalTabs.tsx` affichait uniquement deux lignes statiques dans `Profil & Sécurité` (sans équipes de facturation FinOps en lecture) et un simple bouton local `Tester ma connexion` dans `Mes Connexions aux Outils` au lieu d'un jeton personnel chiffré `AES-256-GCM` par Connecteur d'entreprise (1 fois par outil Jira/GitLab/Confluence, jamais 1 fois par source) ni ouverture directe sur un onglet cible depuis la bannière *Cold-Start*.
  3. **Absence de repli pragmatique pour l'indexation RAG sans Compte de service DSI** : `WorkspaceDetailTabsPanel.tsx` ne distinguait pas l'identité d'indexation lecture seule (`Compte de service` vs `Membre référent de l'équipe`) et ne détectait pas le départ d'équipe, la désactivation du compte ou la révocation du jeton du référent (`PAUSED_REFERENT_RENEWAL_REQUIRED`).
- **Invariants non négociables (`ARCHITECTURE-SPINE.md` & `GEMINI.md`)** :
  - **Étanchéité `AD-21` Write-Only + `AES-256-GCM`** (`PassthroughVaultCipher`) : aucun secret administrateur (`encrypted_admin_secret`) ni jeton utilisateur (`encrypted_token`) n'est jamais retourné en clair ; seul `SecretStatus` (`{ configured, fingerprint: "sha256:<8-hex>", updated_at }`) est exposé.
  - **Garde-fou anti-SSRF obligatoire** : validation stricte de `base_url` rejetant `169.254.169.254`, `169.254.0.0/16`, `fe80::/10`, `metadata.google.internal`, `100.100.100.200` avec `HTTP 422 ERR_UNSAFE_CONNECTOR_ENDPOINT_URL` (RFC 9457) tout en autorisant `.local` et `.internal` (`https://gitlab.ds3c.internal`).
  - **Pureté `@orcia/ui` & `orcia_core.permissions`** : zéro import `@orcia/api-client` / `@tanstack/react-router` dans `packages/ui`, zéro import SQL/FastAPI dans `orcia_core.permissions`, et zéro fichier `> 350–400` lignes.

### 1.2 Exploration, Analyse d'Impact GitNexus, Factorisation & Dette Technique
- **Analyse d'Impact GitNexus (`gitnexus_query`, `gitnexus_context`, `gitnexus_impact`)** :
  - `gitnexus_impact({target: "UserAccountDropdownAndSettingsModal", direction: "upstream"})` : `impactedCount: 3`, risque `LOW` (`InnerShellContainer` $\rightarrow$ `ShellContainer` $\rightarrow$ `RootLayoutComponent`). L'ajout de props optionnelles contrôlées (`activeTab` / `onActiveTabChange`, `accountProfile`, `passthroughConnectors`, `onSavePassthroughToken`, `onRevokePassthroughToken`) préserve `100 %` de rétrocompatibilité avec les tests unitaires `@orcia/ui` existants.
  - `gitnexus_context({name: "WorkspaceDetailTabsPanel"})` : `1` appelant direct (`WorkspaceStudioCardsAndDetailView.tsx`), processus `proc_207_workspacestudiocards`.
  - `gitnexus_impact({target: "PassthroughVaultCipher", direction: "upstream"})` : réutilisé par `AuthAndOrganizationService`, `PermissionBrokerService` et `EnvelopeVaultSecretProvider` — primitive cryptographique canonique `AES-256-GCM` HKDF-SHA256 déjà éprouvée.
- **Exploration Schéma PostgreSQL 18 (`0002` & `0013`)** :
  - La table `workspace_datasources` (`0002`) possède `id UUID PK`, `workspace_id UUID FK workspaces(id)`, `alias VARCHAR(128)`, `scheme VARCHAR(32) FK connector_schemes(scheme)` (`0013`), `uri TEXT`, `role VARCHAR(64)`, `execution_identity VARCHAR(32)` (`passthrough | service_principal`), `freshness_ttl_days INT` et `UNIQUE (workspace_id, alias)`.
  - La migration `20261111_1704` étend `workspace_datasources` de manière additive et réversible avec `connector_id UUID NULL REFERENCES enterprise_connectors(id) ON DELETE SET NULL`, `sync_identity_mode VARCHAR(32) NOT NULL DEFAULT 'SERVICE_ACCOUNT'`, `service_account_id VARCHAR(128) NULL`, `referent_user_id VARCHAR(128) NULL`.
- **Opportunités de Factorisation & Contrôle de Volumétrie (`< 350` lignes)** :
  - Découpage proactif des fichiers proches du plafond avant ajout fonctionnel :
    - `packages/ui/src/primitives/UserAccountDropdownAndSettingsModal.tsx` (`393` l.) $\rightarrow$ extraction des types/constantes dans `UserAccountDropdownTypes.ts` (`~135` l.) + composant principal (`~270` l.).
    - `packages/ui/src/primitives/UserSettingsModalTabs.tsx` (`304` l.) $\rightarrow$ extraction des onglets Profil & Passthrough dans `UserSettingsProfileAndPassthroughTabs.tsx` (`~220` l.) + `UserSettingsModalTabs.tsx` (`~195` l.).
    - `apps/web/src/components/ShellContainer.tsx` (`384` l.) $\rightarrow$ extraction du contrôle d'en-tête connecté à `@orcia/api-client` dans `ShellHeaderAccountControl.tsx` (`~170` l.), ramenant `ShellContainer.tsx` sous `355` lignes.
    - `apps/web/src/features/workspaces/WorkspaceDetailTabsPanel.tsx` (`375` l.) $\rightarrow$ extraction de l'onglet `SOURCES` dans `WorkspaceSourcesRagTab.tsx` (`~310` l.), ramenant `WorkspaceDetailTabsPanel.tsx` sous `190` lignes.
    - `SettingsSecondaryTabsSection.tsx` délègue à `apps/web/src/features/admin/connectors/EnterpriseConnectorsSettingsSection.tsx` + `EnterpriseConnectorModal.tsx` (`< 320` l. chacun).

---

## 2. Plan d'Implémentation

### 2.1 Schéma de Données & Migrations Alembic (`infra/migrations/versions/20261111_1704_story_17_4_connectors_passthrough_and_rag_referent.py`)
- Révision `20261111_1704` (`down_revision = "20261111_1703"`), SQL brut pur (`op.execute(sa.text(...))`), zéro import ORM :
  1. Création de `enterprise_connectors` (`UUIDv7` PK, `connector_kind` `GITLAB | JIRA | CONFLUENCE | OIDC_SSO | S3_OBJECT_STORE`, `name`, `base_url`, `auth_mode` `OAUTH2_PASSTHROUGH | PERSONAL_ACCESS_TOKEN | OIDC_FEDERATION | SERVICE_SECRET`, `encrypted_admin_secret`, `admin_secret_fingerprint`, `admin_secret_updated_at`, `enabled`, `created_at`, `updated_at`) + index `idx_enterprise_connectors_kind_enabled`.
  2. Création de `user_connector_passthrough_tokens` (`UUIDv7` PK, `user_id`, `connector_id FK ON DELETE CASCADE`, `external_author_login`, `encrypted_token`, `secret_fingerprint`, `status`, `updated_at`, `UNIQUE (user_id, connector_id)`) + index `idx_user_connector_passthrough_user`.
  3. Extension de `workspace_datasources` (`connector_id`, `sync_identity_mode`, `service_account_id`, `referent_user_id`) + index `idx_workspace_datasources_connector_id`.
  4. `downgrade()` complet supprimant dans l'ordre inverse les index/colonnes de `workspace_datasources`, `user_connector_passthrough_tokens` et `enterprise_connectors`.

### 2.2 Noyau Métier Hexagonal (`packages/orcia-core/`)
- `packages/orcia-core/src/orcia_core/permissions/errors.py` : ajout de `UnsafeConnectorEndpointUrlError` (`HTTP 422 ERR_UNSAFE_CONNECTOR_ENDPOINT_URL`) bilingue FR/EN enregistré dans `PERMISSIONS_ERROR_CATALOG` et `apps/api/src/orcia_api/errors/registry.py`.
- `packages/orcia-core/src/orcia_core/permissions/enterprise_connectors.py` (domaine pur `0` SQL / `0` FastAPI) :
  - `validate_safe_connector_base_url` (anti-SSRF strict sur métadonnées Cloud/link-local, autorise `.local` / `.internal`).
  - `compute_secret_fingerprint`, `pack_encrypted_secret` / `unpack_encrypted_secret` via `PassthroughVaultCipher` (`AES-256-GCM`).
  - `evaluate_datasource_sync_health` calculant de manière déterministe `ACTIVE` vs `PAUSED_REFERENT_RENEWAL_REQUIRED` (`REFERENT_LEFT_TEAM` | `REFERENT_ACCOUNT_DISABLED` | `REFERENT_TOKEN_MISSING`).
  - `EnterpriseConnectorsGovernanceService` pour le mode en mémoire hors PG (`ORCIA_DISABLE_PG_BOOTSTRAP_SYNC=1`) et les tests unitaires rapides.
- `packages/orcia-core/src/orcia_core/bootstrap/_internal/sql_enterprise_connectors.py` & `sql_workspace_datasources.py` :
  - Adaptateurs PostgreSQL 18 asynchrones sans requête `N+1`, chiffrant les secrets via `PassthroughVaultCipher` avant `INSERT/UPDATE`, résolvant les équipes de facturation (`org_units`) pour `/users/me/account-profile` et calculant dynamiquement `sync_status` + `sync_status_reason` à la lecture/écriture des sources d'espace.

### 2.3 Couche Backend API, Sécurité & Contrats (`apps/api/`, `packages/api-client/`)
- `apps/api/src/orcia_api/schemas/enterprise_connectors.py` (enregistré dans `SCHEMA_DOMAIN_MODULES` de `scripts/export_openapi.py`).
- `apps/api/src/orcia_api/routers/enterprise_connectors.py` :
  - `GET / POST / PATCH / DELETE /api/v1/settings/connectors` (mutations réservées `PLATFORM_ADMIN` / `SECOPS`, `403 ERR_OBSERVER_MODE_READ_ONLY` en mode observateur).
  - `GET /api/v1/users/me/account-profile`
  - `GET /api/v1/users/me/passthrough-tokens`
  - `PUT / DELETE /api/v1/users/me/passthrough-tokens/{connector_id}` (`403 ERR_OBSERVER_MODE_READ_ONLY` en mode observateur).
- `apps/api/src/orcia_api/routers/workspace_datasources.py` :
  - `GET / POST /api/v1/workspaces/{workspace_id}/datasources`
  - `PATCH /api/v1/workspaces/{workspace_id}/datasources/{datasource_id}`
- Régénération `0-diff` de `packages/api-client/openapi.json` et `packages/api-client/src/generated/` + méthodes typées dans `packages/api-client/src/domains/catalogAndPermissions.ts`.

### 2.4 Interface Utilisateur & Expérience (`packages/ui/` & `apps/web/`)
- **Onglet `Connecteurs & SSO`** (`apps/web/src/features/admin/connectors/EnterpriseConnectorsSettingsSection.tsx` + `EnterpriseConnectorModal.tsx`) : suppression définitive de la pollution de `workspaces[0]`, CRUD complet en PostgreSQL 18 (survie au `F5`), badge Write-Only `SecretStatus` (`sha256:<8-hex>` ou mention Passthrough sans secret admin), bouton `.orcia-ds-btn-danger` de suppression et affichage explicite des erreurs RFC 9457 (`422` SSRF / `403` Observer).
- **Modale `👤 Mon Compte`** (`packages/ui/src/primitives/UserSettingsProfileAndPassthroughTabs.tsx` + `apps/web/src/components/ShellHeaderAccountControl.tsx` + `authSessionStore.ts` `openUserSettingsModalAtTab`) :
  - Onglet `Profil & Sécurité` : identité réelle, badges des rôles actifs et section lecture seule **« Mes équipes & rattachements FinOps »**.
  - Onglet `Mes Connexions aux Outils` : connecteurs d'entreprise du socle, explication de l'attribution nominative Jira/Git, saisie `@login` externe + jeton personnel Write-Only (`PUT`) et révocation (`DELETE`) persistés au `F5`.
- **`Mes Espaces › Sources`** (`apps/web/src/features/workspaces/WorkspaceSourcesRagTab.tsx`) :
  - Bannière douce *Cold-Start* 1-clic ouvrant directement `👤 Mon Compte › Mes Connexions aux Outils` (`PASSTHROUGH_SOURCES`).
  - Choix explicite d'identité de synchronisation RAG entre `Compte de service (recommandé)` (`SERVICE_ACCOUNT`) et `Membre référent de l'équipe (repli sans compte de service)` (`TEAM_REFERENT_USER`).
  - Badge `Synchronisation active` vs badge ambre **`Synchronisation en pause — Référent à renouveler`** (`PAUSED_REFERENT_RENEWAL_REQUIRED`) + action rapide `Renouveler le référent` (`PATCH`) et rappel du filtrage `Passthrough` du lecteur courant sur `[S1]`.

### 2.5 Analyse d'Impact sur la Pyramide des Tests (`AD-17` — Couches 1 à 5 + Sécurité)
- **Couche 1a (Unitaires Python)** : `tests/unit/test_story_17_4_connectors_passthrough_and_rag_referent.py` (anti-SSRF, `AES-256-GCM` & secret canari absent des DTO, machine d'état `sync_status` sur départ d'équipe / compte désactivé / jeton révoqué).
- **Couche 1b (Unitaires/Composants TS `Vitest`)** : `apps/web/src/__tests__/story-17-4-connectors-account-passthrough-and-rag-referent.test.tsx` + `zero-dead-buttons-and-silent-catches-audit.test.tsx` + `design-system-look-and-feel-isolation.test.tsx`.
- **Couche 2 (Intégration Verticale `HTTP FastAPI ➔ PostgreSQL 18`)** : `tests/integration/api/test_story_17_4_connectors_passthrough_and_rag_referent_postgres18.py` (`upgrade -> downgrade 20261111_1703 -> upgrade`, `0` pollution `workspaces`, SSRF `422`, Observer `403`, chiffrement `AES-256-GCM` en SQL, cycle `ACTIVE -> PAUSED_REFERENT_RENEWAL_REQUIRED -> ACTIVE`).
- **Couche 3 (Contrats OpenAPI 3.1 `0-diff` & `lint-imports`)** : `scripts/export_openapi.py --check`, `tests/contract/test_openapi_contract.py`, `.venv/bin/lint-imports`.
- **Couche Sécurité** : `tests/security/test_api_security_baseline.py` + assertions secret canari et anti-SSRF.

---

## 3. Bilan des Modifications & Résultats (Post-Implémentation)

### 3.1 Fichiers Développés & Modifiés
| Fichier | Nature | Description synthétique |
| :--- | :--- | :--- |
| `infra/migrations/versions/20261111_1704_story_17_4_connectors_passthrough_and_rag_referent.py` | Création | Migration Alembic bidirectionnelle créant les tables `enterprise_connectors`, `user_connector_credentials` et étendant `workspace_datasources` avec `sync_identity_type`, `referent_user_id`, `sync_status`, `sync_status_reason`. |
| `packages/orcia-core/src/orcia_core/permissions/errors.py` | Modification | Ajout de l'erreur `UnsafeConnectorEndpointUrlError` (`HTTP 422 ERR_UNSAFE_CONNECTOR_ENDPOINT_URL`). |
| `packages/orcia-core/src/orcia_core/permissions/enterprise_connectors.py` | Création | Modèle de domaine pur, chiffrement `PassthroughVaultCipher` (AES-256-GCM), validation anti-SSRF `validate_safe_connector_base_url`, machine d'état RAG `evaluate_datasource_sync_health`. |
| `packages/orcia-core/src/orcia_core/bootstrap/_internal/sql_enterprise_connectors.py` | Création | Adaptateur PostgreSQL 18 asynchrone pour les connecteurs d'entreprise, les jetons passthrough et le profil utilisateur. |
| `packages/orcia-core/src/orcia_core/bootstrap/_internal/sql_workspace_datasources.py` | Création | Adaptateur PostgreSQL 18 pour les sources d'espace avec calcul dynamique de santé du référent RAG. |
| `packages/orcia-core/src/orcia_core/bootstrap/__init__.py` | Modification | Export des adaptateurs SQL et types associés. |
| `apps/api/src/orcia_api/schemas/enterprise_connectors.py` | Création | Schémas de transport Pydantic v2 pour les connecteurs, le passthrough utilisateur et les datasources d'espace. |
| `apps/api/src/orcia_api/routers/enterprise_connectors.py` | Création | Routeurs FastAPI pour `/api/v1/settings/connectors`, `/api/v1/users/me/account-profile` et `/api/v1/users/me/passthrough-tokens`. |
| `apps/api/src/orcia_api/routers/workspace_datasources.py` | Création | Routeur FastAPI pour `/api/v1/workspaces/{workspace_id}/datasources`. |
| `apps/api/src/orcia_api/errors/registry.py` | Modification | Enregistrement de `UnsafeConnectorEndpointUrlError`. |
| `apps/api/src/orcia_api/main.py` | Modification | Montage des routeurs `enterprise_connectors` et `workspace_datasources`. |
| `scripts/export_openapi.py` | Modification | Ajout du domaine `enterprise_connectors` aux modules de schéma OpenAPI. |
| `packages/api-client/openapi.json` | Modification | Schéma OpenAPI 3.1 synchronisé (`0-diff`). |
| `packages/api-client/src/generated/schema.ts` | Modification | Types TypeScript OpenAPI régénérés. |
| `packages/api-client/src/generated/enterprise_connectors.ts` | Création | Client OpenAPI généré pour le domaine `enterprise_connectors`. |
| `packages/api-client/src/domains/catalogAndPermissions.ts` | Modification | Méthodes typées du client API pour les connecteurs d'entreprise, passthrough et sources d'espace. |
| `packages/ui/src/primitives/UserAccountDropdownTypes.ts` | Création | Types et énumération des onglets `Mon Compte` (`PROFILE_FINOPS`, `PASSTHROUGH_SOURCES`). |
| `packages/ui/src/primitives/UserSettingsProfileAndPassthroughTabs.tsx` | Création | Composants des onglets `Mon Compte` avec rattachements FinOps et jetons Write-Only anti-LastPass. |
| `packages/ui/src/primitives/UserSettingsModalDialog.tsx` | Modification | Intégration des onglets `Mon Compte` et suppression des onglets obsolètes. |
| `packages/ui/src/primitives/UserSettingsModalTabs.tsx` | Modification | Adaptation des onglets du profil utilisateur. |
| `packages/ui/src/primitives/UserAccountDropdownAndSettingsModal.tsx` | Modification | Support du deep-linking vers un onglet spécifique (`initialTab`). |
| `packages/ui/src/index.ts` | Modification | Export des nouveaux composants et types de compte utilisateur. |
| `apps/web/src/features/admin/connectors/EnterpriseConnectorsSettingsSection.tsx` | Création | Vue de gestion des connecteurs socle dans `/settings` (CRUD complet PostgreSQL 18, badges Write-Only, anti-SSRF). |
| `apps/web/src/features/admin/connectors/EnterpriseConnectorModal.tsx` | Création | Modale de création/édition d'un connecteur d'entreprise. |
| `apps/web/src/features/workspaces/WorkspaceSourcesRagTab.tsx` | Création | Onglet Sources RAG avec choix d'identité (Service Account vs Membre Référent) et alerte de repli `PAUSED_REFERENT_RENEWAL_REQUIRED`. |
| `apps/web/src/features/workspaces/WorkspaceDetailTabsPanel.tsx` | Modification | Câblage de `WorkspaceSourcesRagTab` dans la vue détail d'espace. |
| `apps/web/src/components/ShellHeaderAccountControl.tsx` | Création | Contrôle du compte utilisateur dans le header avec bouton d'ouverture directe de la modale `Mon Compte`. |
| `apps/web/src/components/ShellContainer.tsx` | Modification | Intégration du composant de compte utilisateur et gestion d'état centralisée. |
| `apps/web/src/stores/authSessionStore.ts` | Modification | Ajout de l'action `openUserSettingsModalAtTab` pour le deep-linking inter-écrans. |
| `apps/web/src/routes/SettingsSecondaryTabsSection.tsx` | Modification | Intégration de `EnterpriseConnectorsSettingsSection` dans l'onglet Connecteurs & SSO. |
| `apps/web/src/routes/SettingsOrganizationUnitRow.tsx` | Modification | Remplacement de `aria-hidden` par `role="presentation"` sur les glyphes de structure d'arbre. |
| `apps/web/src/__tests__/story-17-4-connectors-account-passthrough-and-rag-referent.test.tsx` | Création | 3 tests Vitest dédiés (F5 survival, passthrough Write-Only, alerte RAG référent). |
| `apps/web/src/__tests__/vitestConnectorsMockHandlers.ts` | Création | Handlers de mock MSW/fetch pour les routes connecteurs, passthrough et sources d'espace. |
| `tests/unit/test_story_17_4_connectors_passthrough_and_rag_referent.py` | Création | Tests unitaires Python (anti-SSRF, AES-256-GCM, machine d'état de santé du référent). |
| `tests/integration/api/test_story_17_4_connectors_passthrough_and_rag_referent_postgres18.py` | Création | Tests d'intégration verticale HTTP ➔ PostgreSQL 18 (cycle migration Alembic, persistance, sécurité). |

### 3.2 Résultats Chiffrés, Métriques & Qualité
- **Couverture de tests** :
  - Python (unit + integration + anti-patterns) : 21 tests passés, 100% au vert.
  - Vitest (@orcia/ui + @orcia/web) : 100% des tests passés (77 tests UI, 66 tests Web dont les 3 tests 17.4 et les 26 tests de `i18n-and-shell.test.tsx`).
- **Qualité statique & Architecture** :
  - `ruff check .` : `All checks passed!`
  - `ruff format --check .` : `688 files already formatted`
  - `mypy --strict packages/orcia-core packages/orcia-connectors apps/api apps/worker` : `Success: no issues found in 285 source files`
  - `lint-imports` : `5 contracts kept, 0 broken`
  - `test_openapi_contract.py` : `2 passed` (0-diff garanti)
  - `turbo run lint typecheck test` : `Tasks: 9 successful, 9 total` (100% au vert)

### 3.3 Validation & Procédure de Test sur Toute la Pyramide (`AD-17` + 5 Garde-Fous de Câblage Vertical)
- **Couche 1a — Tests Unitaires Python** :
  - `validate_safe_connector_base_url` : bloque les adresses link-local / métadonnées cloud (`169.254.169.254`, `metadata.google.internal`) et valide les URI internes légitimes.
  - `PassthroughVaultCipher` : vérifie le chiffrement AES-256-GCM, l'absence de secret en clair dans les logs ou DTO, et le calcul de fingerprint SHA-256 tronqué.
  - `evaluate_datasource_sync_health` : vérifie la transition déterministe vers `PAUSED_REFERENT_RENEWAL_REQUIRED` sur départ de l'équipe, désactivation de compte ou jeton révoqué.
- **Couche 1b — Tests Composants TS (`Vitest`)** :
  - `story-17-4-connectors-account-passthrough-and-rag-referent.test.tsx` : vérifie la survie au rafraîchissement F5 (`unmount` + `render`), la saisie et masquage des jetons Write-Only anti-LastPass, et l'affichage de l'alerte RAG avec bouton de renouvellement.
  - `zero-dead-buttons-and-silent-catches-audit.test.tsx` : vérifie l'absence de bouton muet ou de callback silencieux.
- **Couche 2 — Intégration Verticale `HTTP ➔ PostgreSQL 18`** :
  - `test_story_17_4_connectors_passthrough_and_rag_referent_postgres18.py` : teste l'aller-retour complet migration Alembic `upgrade -> downgrade -> upgrade`, l'absence de pollution de `workspaces`, le rejet SSRF en HTTP 422, le rejet observateur en HTTP 403, et la persistance réelle en base PostgreSQL 18.
- **Couche 3 — Contrats API & Frontières Monolithiques** :
  - Schéma OpenAPI 3.1 validé avec 0 écart via `test_openapi_contract.py`.
  - Règles d'importation unilatérale `AD-19` et `AD-20` vérifiées par `lint-imports`.
- **Couche Sécurité** :
  - Anti-SSRF strict sur les URL de connecteurs.
  - Masquage intégral des secrets (zéro type="password" hors `BiModeLoginView.tsx`, attributs anti-password-manager complets).
  - Contrôle d'accès RBAC et mode lecture seule observateur (`ERR_OBSERVER_MODE_READ_ONLY`).
