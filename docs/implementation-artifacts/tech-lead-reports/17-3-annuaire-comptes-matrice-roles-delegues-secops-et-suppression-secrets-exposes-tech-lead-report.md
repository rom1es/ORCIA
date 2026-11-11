# Story 17.3 — Annuaire des Comptes dès le Jour 0, Modèle Simplifié à 6 Rôles Délégués (`PLATFORM_ADMIN`, `SECOPS`, `BU_LEAD`, `TEAM_LEAD`, `CONTRIBUTOR`, `OBSERVER`), Suppression de « Lire / Voir les secrets » & Tiroir d'Isolation `SECOPS`

- **Date** : `2026-11-11`
- **Story / Clé Sprint** : `17-3-annuaire-comptes-matrice-roles-delegues-secops-et-suppression-secrets-exposes` (`Epic 17 — Refonte Configuration, Identités & Habilitations (IAM), Organigramme Multi-Niveaux & Shell`)
- **Capacité(s)** : `CAP-050` (*Modèle d'habilitations RBAC/ABAC à 6 verbes, matrice des 6 rôles délégués & exceptions granulaires*), `CAP-051` (*Écran Comptes & Habilitations IAM : Annuaire Jour 0, Comptes de service, Anti-Lockout & Tiroir d'isolation SECOPS*) — classification : **`feature`**
- **Auteur / Contexte** : Refonte complète de la gouvernance des comptes et des habilitations dans `/settings` (`Comptes & Habilitations`), couvrant `FR-21`, `FR-22`, `FR-28`, `FR-31`, `AD-1`, `AD-6`, `AD-12`, `AD-17`, `AD-19`, `AD-21` et `UX-DR1` (Direction C).
- **Commits associés** : *(complété en Section 3)*

---

## 1. Analyse du Besoin & Étude d'Impact Tech Lead (Pré-Implémentation)

### 1.1 Contexte & Problématique
- **Constats d'audit résolus par la Story 17.3 (`cadrage-refonte-configuration-iam-et-shell.md` — Décisions #1, #2, #6, #7)** :
  1. **Absence d'Annuaire des Comptes dans `/settings`** : le compte administrateur initial créé au Jour 0 (`welcome-setup` / `platformAdmin`) n'apparaissait dans aucun écran d'administration, et il était impossible d'inventorier ou d'administrer les comptes humains (locaux / OIDC fédérés) et les `Comptes de service` (`SERVICE_PRINCIPAL`), leurs rôles officiels et leurs équipes de rattachement.
  2. **Libellé toxique « Lire / Voir les secrets » & invisibilité des droits natifs** : l'ancien écran assimilait le verbe `read` à *« Lire / Voir les secrets »* en contradiction frontale avec `AD-6` / `AD-21` (secrets `100 %` **Write-Only**, jamais relisibles en clair par aucun rôle) et masquait la matrice des droits natifs accordés par chacun des 6 rôles officiels (`PLATFORM_ADMIN`, `SECOPS`, `BU_LEAD`, `TEAM_LEAD`, `CONTRIBUTOR`, `OBSERVER`).
  3. **Formulaire manuel d'habilitations sujet aux erreurs et à l'escalade** : l'éditeur inline exposait par défaut un `<input>` texte libre (`TEAM_LEAD`, `Chef1`), pré-sélectionnait `Plateforme entière` (`GLOBAL`), proposait une case `Tous` cochant `grant` d'un seul clic, permettait de cocher `Exécuter` sans `Consulter`, et plaçait le bouton `+ Ajouter la règle` au milieu du formulaire avant même les cases d'habilitations.
- **Comportement cible verrouillé (`CA-17.3.1`, `CA-17.3.2`, `CA-17.3.3`)** :
  - **Section 1 — Annuaire des Comptes** (`GET/POST/PATCH/DELETE /api/v1/settings/iam/accounts`) synchronisant de manière idempotente dès le Jour 0 l'administrateur initial avec cumul par défaut `["PLATFORM_ADMIN", "SECOPS"]`, gérant les comptes `HUMAN` et `SERVICE_PRINCIPAL` via une modale RGAA à sélecteur fermé des 6 rôles, synchronisant les rattachements aux équipes (`org_units.member_user_ids_jsonb`), et appliquant de façon déterministe l'invariant **Anti-Lockout** (`HTTP 422 ERR_ADMIN_LOCKOUT_PREVENTED` si une modification ou suppression laissait `0` compte `ACTIVE` détenant `PLATFORM_ADMIN`, tout en autorisant le transfert de `SECOPS` vers un compte RSSI tiers).
  - **Section 2 — Matrice Native des 6 Rôles Délégués** (`GET /api/v1/settings/iam/role-matrix`) enrichie de `BU_LEAD`, affichant clairement le périmètre naturel et les droits par famille de ressources, avec éradication totale de *« Lire / Voir les secrets »* dans tout le dépôt au profit de **`Consulter les ressources`** et bandeau d'étanchéité `AD-21`.
  - **Section 3 — Tiroir Replié « Exceptions de Sécurité & Isolation (`SECOPS`) »** (`GET/POST/DELETE /api/v1/settings/iam/grants` avec `resource_kind` et `effect` incluant `INHERITANCE_BLOCK`), replié par défaut, réservé en écriture au rôle `SECOPS`, doté exclusivement de sélecteurs fermés, d'un périmètre restreint par défaut (alerte ambre sur `Plateforme entière`), de l'auto-maintien de `read` dès qu'un verbe d'action est coché, sans case `Tous`, et avec bouton de soumission en bas à droite.

### 1.2 Exploration, Analyse d'Impact GitNexus, Factorisation & Dette Technique
- **Analyse d'Impact GitNexus (`gitnexus_query`, `gitnexus_context`, `gitnexus_impact` sur `/home/romain/Documents/Projects/ORCIA`)** :
  - `HierarchicalRbacService` (`packages/orcia-core/src/orcia_core/permissions/hierarchical_rbac.py`) : `impactedCount = 4`, risque `LOW` (`1` appelant direct hors tests : `apps/api/src/orcia_api/dependencies/orchestration_and_settings.py` $\rightarrow$ `settings_and_studio.py`). L'ajout de `resource_kind: GrantResourceKind = "ALL"` et le support de `effect = "INHERITANCE_BLOCK"` restent `100 %` rétrocompatibles avec les tests Epic 8 (`test_epic_8_settings_rbac_llm_studio_and_wizards.py`).
  - `SettingsIamOrganizationSection` (`apps/web/src/routes/SettingsIamOrganizationSection.tsx`) : `impactedCount = 5`, risque `LOW` (`1` appelant direct : `SettingsHubView` dans `apps/web/src/routes/settings.tsx`, plus `i18n-and-shell.test.tsx`).
  - `delegate_rbac_grants` (`apps/api/src/orcia_api/routers/settings_and_studio.py`) : `impactedCount = 0` statique, vérifié par `grep` dans `tests/unit/test_epic_8_settings_rbac_llm_studio_and_wizards.py`.
- **Exploration SQL & Contraintes PostgreSQL 18 identifiées** :
  - Dans `0022_epic_8_settings_rbac_llm_tiers_and_wizards.py`, la colonne `role_permission_grants.effect` était typée `VARCHAR(16)` avec `CHECK (effect IN ('ALLOW', 'DENY'))`, alors que `'INHERITANCE_BLOCK'` mesure `17` caractères. La migration `20261111_1703` élargit proprement `effect` en `VARCHAR(32)`, étend la contrainte `CHECK` à `('ALLOW', 'DENY', 'INHERITANCE_BLOCK')`, ajoute `resource_kind VARCHAR(32) NOT NULL DEFAULT 'ALL'` et met à jour la contrainte d'unicité de manière intégralement réversible dans `downgrade()`.
  - Dans `apps/api/src/orcia_api/errors/registry.py`, `AdminLockoutPreventedError` (`422`) et `GrantEscalationForbiddenError` (`403`) n'étaient pas encore listés explicitement dans `DOMAIN_ERROR_CLASSES` ; ils y sont ajoutés avec `InvalidIamRoleError` (`422 ERR_IAM_INVALID_ROLE`) et `DuplicateIamPrincipalError` (`409 ERR_IAM_DUPLICATE_PRINCIPAL`).
- **Opportunités de Factorisation & Résorption de Dette de Volumétrie (`<= 350–400` lignes)** :
  - **Découpage de `hierarchical_rbac.py` (`469` lignes $\rightarrow$ `< 340` lignes)** : extraction des types RBAC et de `DEFAULT_ROLE_PERMISSION_MATRIX` dans `packages/orcia-core/src/orcia_core/permissions/role_matrix.py` (`< 240` lignes) et des invariants d'annuaire / anti-lockout dans `packages/orcia-core/src/orcia_core/permissions/iam_accounts.py` (`< 260` lignes), `100 %` purs Python (zéro import SQL/framework).
  - **Découpage de `settings_and_studio.py` (`531` lignes $\rightarrow$ `< 350` lignes)** : extraction des routes Studio & Wizards durables vers `apps/api/src/orcia_api/routers/studio_and_wizards.py` (`< 160` lignes) et création du routeur dédié `apps/api/src/orcia_api/routers/iam_accounts.py` (`< 300` lignes) + schémas dédiés `apps/api/src/orcia_api/schemas/iam_accounts.py` (`< 160` lignes).
  - **Découpage de `admin_and_studio_labels.ts` (`497` lignes $\rightarrow$ `< 320` lignes)** : extraction des dictionnaires `organizationTab` et `iamTab` dans des sous-modules typés dédiés sous `apps/web/src/i18n/locales/`.
  - **Découpage Frontend `apps/web/src/features/admin/iam/`** : 5 modules ciblés `< 320` lignes (`iamApiBridge.ts`, `IamAccountsDirectoryCard.tsx`, `IamAccountModal.tsx`, `IamNativeRoleMatrixCard.tsx`, `IamSecopsExceptionsDrawer.tsx`) orchestrés par `SettingsIamOrganizationSection.tsx` (`< 220` lignes).

---

## 2. Plan d'Implémentation

### 2.1 Schéma de Données & Migrations Alembic (`infra/migrations/versions/`)
- `infra/migrations/versions/20261111_1703_story_17_3_iam_accounts_and_grant_resource_kind.py` (`revision = "20261111_1703"`, `down_revision = "20261111_1702"`, SQL brut `op.execute(sa.text(...))`, zéro import ORM) :
  - Création de la table `iam_accounts` : clé primaire `id UUID` (`UUIDv7`), `principal_id VARCHAR(128) UNIQUE NOT NULL`, `display_name VARCHAR(160) NOT NULL`, `email VARCHAR(255) NULL`, `account_kind VARCHAR(32) NOT NULL CHECK (account_kind IN ('HUMAN', 'SERVICE_PRINCIPAL'))`, `auth_source VARCHAR(32) NOT NULL CHECK (auth_source IN ('LOCAL_BOOTSTRAP', 'OIDC_FEDERATED', 'SERVICE_TOKEN'))`, `roles_jsonb JSONB NOT NULL DEFAULT '[]'::jsonb`, `team_ids_jsonb JSONB NOT NULL DEFAULT '[]'::jsonb`, `status VARCHAR(32) NOT NULL DEFAULT 'ACTIVE' CHECK (status IN ('ACTIVE', 'INVITED', 'DISABLED'))`, `created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()`, `updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()`, et index `idx_iam_accounts_kind_status`.
  - Évolution réversible de `role_permission_grants` : ajout de `resource_kind VARCHAR(32) NOT NULL DEFAULT 'ALL' CHECK (resource_kind IN ('ALL', 'WORKFLOW', 'AGENT', 'DATASOURCE', 'CONNECTOR'))`, passage de `effect` en `VARCHAR(32)` acceptant `'INHERITANCE_BLOCK'`, mise à jour de la contrainte d'unicité `(subject_type, subject_id, scope_path, resource_kind, verb, effect)` et restauration exacte dans `downgrade()`.

### 2.2 Noyau Métier Hexagonal (`packages/orcia-core/`)
- `packages/orcia-core/src/orcia_core/permissions/iam_accounts.py` :
  - Ensemble fermé `VALID_IAM_ROLES = ("PLATFORM_ADMIN", "SECOPS", "BU_LEAD", "TEAM_LEAD", "CONTRIBUTOR", "OBSERVER")`, entité immuable `IamAccountRecord`, validation stricte `validate_iam_roles` (`422 ERR_IAM_INVALID_ROLE`), garde déterministe `assert_anti_lockout_on_accounts` (`422 ERR_ADMIN_LOCKOUT_PREVENTED` dès que le nombre de comptes `ACTIVE` détenant `PLATFORM_ADMIN` tomberait à `0`), et service domaine `IamAccountsGovernanceService`.
- `packages/orcia-core/src/orcia_core/permissions/role_matrix.py` & `hierarchical_rbac.py` :
  - `DEFAULT_ROLE_PERMISSION_MATRIX` couvrant les **6 rôles officiels** (dont `BU_LEAD`) avec `natural_scope`, `native_verbs`, `resource_permissions` (`workflows`, `agents`, `datasources`, `connectors`, `org_units`, `iam_exceptions`) et `secret_visibility = "WRITE_ONLY_NEVER_READABLE"`.
  - Support dans `RolePermissionGrant` et `HierarchicalRbacService` de `resource_kind` (`ALL | WORKFLOW | AGENT | DATASOURCE | CONNECTOR`) et de `effect = "INHERITANCE_BLOCK"` (activant automatiquement `inheritance_block = True`).
- `packages/orcia-core/src/orcia_core/bootstrap/_internal/sql_iam_accounts.py` (exporté par `orcia_core.bootstrap`) :
  - Synchronisation idempotente Jour 0 de l'administrateur initial (`users` / `platform_setup_state_v1` / fallback `admin@orcia.local`) avec cumul initial `["PLATFORM_ADMIN", "SECOPS"]`, CRUD transactionnel PostgreSQL 18 sur `iam_accounts` avec synchronisation de `org_units.member_user_ids_jsonb` pour `team_ids`, et persistance PostgreSQL 18 des exceptions `role_permission_grants`.

### 2.3 Couche Backend API, Sécurité & Contrats (`apps/api/`, `packages/api-client/`)
- `apps/api/src/orcia_api/schemas/iam_accounts.py` & `schemas/settings_and_studio.py` :
  - Schémas Pydantic v2 `IamAccountResponse`, `IamAccountsListResponse`, `IamAccountCreateRequest`, `IamAccountPatchRequest`, `IamAccountDeleteResponse`, `RoleMatrixEntryResponse`, `RoleMatrixResponse` et extension rétrocompatible de `DelegateGrantRequest` / `RolePermissionGrantResponse` (`resource_kind`, `effect` avec `INHERITANCE_BLOCK`).
- `apps/api/src/orcia_api/routers/iam_accounts.py` & `settings_and_studio.py` :
  - Endpoints `GET/POST/PATCH/DELETE /api/v1/settings/iam/accounts`, `GET /api/v1/settings/iam/role-matrix`, et `GET/POST/DELETE /api/v1/settings/iam/grants`.
  - Gardes `READ_ONLY_OBSERVER` (`HTTP 403 ERR_OBSERVER_MODE_READ_ONLY`), contrôle d'accès RBAC (`403 ERR_SCOPE_ACCESS_DENIED`), enveloppes RFC 9457 Problem Details (`422 ERR_ADMIN_LOCKOUT_PREVENTED`, `422 ERR_IAM_INVALID_ROLE`, `409 ERR_IAM_DUPLICATE_PRINCIPAL`).
- `packages/api-client/` :
  - Régénération `0-diff` via `.venv/bin/python scripts/export_openapi.py` et exposition des méthodes typées dans `packages/api-client/src/domains/catalogAndPermissions.ts`.

### 2.4 Interface Utilisateur & Expérience (`apps/web/`)
- Éradication complète de `"Lire / Voir les secrets"` / `"Read / View secrets"` dans `apps/web` (`admin_and_studio_labels.ts`, `iam_accounts_labels.ts`, `SettingsIamOrganizationSection.tsx`, `contextualHelpCatalog.ts`) au profit de **`Consulter les ressources`** / **`Read & view resources`** et du bandeau d'étanchéité `AD-21`.
- Création dans `apps/web/src/features/admin/iam/` des 5 modules Direction C (`iamApiBridge.ts`, `IamAccountsDirectoryCard.tsx`, `IamAccountModal.tsx`, `IamNativeRoleMatrixCard.tsx`, `IamSecopsExceptionsDrawer.tsx`) utilisant exclusivement les tokens CSS de `tokens.css` (zéro couleur hexadécimale, zéro violet `#6D28D9`), les composants `@orcia/ui` (`OrciaDialog`, `OrciaAlertBanner`, `StatusBadge`), les attributs anti-LastPass et la réhydratation `GET` au montage garantissant la survie au `F5`.

### 2.5 Analyse d'Impact sur la Pyramide des Tests (`AD-17` — Couches 1 à 5 + Sécurité)
- **Couche 1a (Unitaires Python)** : `tests/unit/test_story_17_3_iam_accounts_and_role_matrix.py` + non-régression `test_permissions_and_auth.py` (dont `test_hexagonal_purity_permissions_package`) et `test_epic_8_settings_rbac_llm_studio_and_wizards.py`.
- **Couche 1b (Composants/Intégration UI Vitest)** : `apps/web/src/__tests__/story-17-3-iam-accounts-matrix-and-secops-drawer.test.tsx` + mise à jour de `i18n-and-shell.test.tsx` et passage de `zero-dead-buttons-and-silent-catches-audit.test.tsx` & `design-system-look-and-feel-isolation.test.tsx`.
- **Couche 2 (Intégration Verticale `HTTP FastAPI ➔ PostgreSQL 18` `testcontainers`)** : `tests/integration/api/test_story_17_3_iam_accounts_and_secops_postgres18.py` (cycle Alembic `upgrade -> downgrade -> upgrade`, `SELECT` SQL direct sur `iam_accounts`, `org_units` et `role_permission_grants`, anti-lockout `422`, rejet `403` observateur).
- **Couche 3 (Contrats OpenAPI 3.1 `0-diff` & `lint-imports`)** : `scripts/export_openapi.py --check`, `tests/contract/test_openapi_contract.py`, `.venv/bin/lint-imports`, `lint_spine.py`.
- **Couche Sécurité** : vérification de l'anti-lockout `422 ERR_ADMIN_LOCKOUT_PREVENTED`, du rejet `403 ERR_OBSERVER_MODE_READ_ONLY`, du verrouillage hors `SECOPS` du tiroir d'exceptions, et de l'absence totale de secrets exposés (`WRITE_ONLY_NEVER_READABLE`).

---

## 3. Bilan des Modifications & Résultats (Post-Implémentation)

### 3.1 Inventaire des Fichiers Créés / Modifiés (Tous `< 400` lignes)

| Couche | Fichier | Action | Rôle & Garde-Fous |
| :--- | :--- | :--- | :--- |
| **Alembic (`SQL`)** | `infra/migrations/versions/20261111_1703_story_17_3_iam_accounts_and_grant_resource_kind.py` | Créé | Table `iam_accounts` (`UUIDv7`, `roles_jsonb`, `team_ids_jsonb`, `HUMAN \| SERVICE_PRINCIPAL`), extension `role_permission_grants` (`resource_kind`, `effect='INHERITANCE_BLOCK'`, index unique composite), `upgrade`/`downgrade` réversibles. |
| **Domaine (`orcia-core`)** | `packages/orcia-core/src/orcia_core/permissions/errors.py` | Modifié | Ajout de `InvalidIamRoleError` (`422 ERR_IAM_INVALID_ROLE`) et `DuplicateIamPrincipalError` (`409 ERR_IAM_DUPLICATE_PRINCIPAL`). |
| **Domaine (`orcia-core`)** | `packages/orcia-core/src/orcia_core/permissions/role_matrix.py` | Créé (`242` l.) | Jeu fermé de **6 rôles officiels** (`PLATFORM_ADMIN`, `SECOPS`, `BU_LEAD`, `TEAM_LEAD`, `CONTRIBUTOR`, `OBSERVER`), `DEFAULT_ROLE_PERMISSION_MATRIX` avec `secret_visibility = "WRITE_ONLY_NEVER_READABLE"`, `RolePermissionGrant` (`resource_kind`). |
| **Domaine (`orcia-core`)** | `packages/orcia-core/src/orcia_core/permissions/iam_accounts.py` | Créé (`342` l.) | `IamAccountsGovernanceService`, validation des 6 rôles, synchronisation Jour 0 (`["PLATFORM_ADMIN", "SECOPS"]`) et invariant déterministe anti-lockout (`assert_anti_lockout_on_accounts` -> `422 ERR_ADMIN_LOCKOUT_PREVENTED`). |
| **Domaine (`orcia-core`)** | `packages/orcia-core/src/orcia_core/permissions/hierarchical_rbac.py` | Modifié | Support de `resource_kind` (`ALL \| WORKFLOW \| AGENT \| DATASOURCE \| CONNECTOR`) et de `effect="INHERITANCE_BLOCK"` dans l'évaluation d'héritage RBAC. |
| **Persistance SQL 18** | `packages/orcia-core/src/orcia_core/bootstrap/_internal/sql_iam_account_helpers.py` | Créé (`221` l.) | DDL idempotent, mapping de lignes, résolution candidat Jour 0 (`users` / `platform_settings`), synchronisation `org_units.member_user_ids_jsonb`. |
| **Persistance SQL 18** | `packages/orcia-core/src/orcia_core/bootstrap/_internal/sql_iam_accounts.py` | Créé (`301` l.) | CRUD transactionnel PostgreSQL 18 (`SELECT ... FOR UPDATE` anti-lockout) sur `iam_accounts`. |
| **Persistance SQL 18** | `packages/orcia-core/src/orcia_core/bootstrap/_internal/sql_iam_grants.py` | Créé (`280` l.) | Persistance PostgreSQL 18 idempotente (`ON CONFLICT`) et suppression de `role_permission_grants` avec `resource_kind` et `INHERITANCE_BLOCK`. |
| **API FastAPI** | `apps/api/src/orcia_api/schemas/iam_accounts.py` & `schemas/settings_and_studio.py` | Créé / Modifié | Contrats Pydantic v2 (`IamAccountResponse`, `RoleMatrixResponse`, `DelegateGrantRequest` avec `resource_kind` et `INHERITANCE_BLOCK`). |
| **API FastAPI** | `apps/api/src/orcia_api/routers/iam_accounts.py`, `_settings_helpers.py`, `settings_and_studio.py`, `studio_and_wizards.py` | Créé / Découpé | Endpoints `GET/POST/PATCH/DELETE /api/v1/settings/iam/accounts`, `GET /api/v1/settings/iam/role-matrix`, `GET/POST/DELETE /api/v1/settings/iam/grants` + découpage sous `< 400` lignes. |
| **API FastAPI** | `apps/api/src/orcia_api/errors/registry.py`, `dependencies/`, `main.py` | Modifié | Enregistrement RFC 9457 (`422` / `409`), câblage `IamAccountsGovernanceService` dans le Composition Root. |
| **SDK OpenAPI 3.1** | `scripts/export_openapi.py`, `packages/api-client/src/generated/iam_accounts.ts`, `domains/catalogAndPermissions.ts` | Modifié / Généré | Shard OpenAPI `iam_accounts` (`0-diff`), méthodes clientes typées (`listIamAccounts`, `createIamAccount`, `updateIamAccount`, `deleteIamAccount`, `getIamRoleMatrix`, `listIamGrants`, `deleteIamGrant`). |
| **SPA Direction C** | `apps/web/src/features/admin/iam/{iamApiBridge.ts,IamAccountsDirectoryCard.tsx,IamAccountModal.tsx,IamNativeRoleMatrixCard.tsx,IamSecopsExceptionForm.tsx,IamSecopsExceptionsDrawer.tsx}` | Créés (`190–340` l.) | Hub `/settings?tab=iam` en 3 volets : Annuaire des Comptes + modale `OrciaDialog` (anti-LastPass), Matrice native des 6 rôles en lecture seule + bandeau `AD-21`, et Tiroir replié d'exceptions SecOps (`ALLOW` / `DENY` / `INHERITANCE_BLOCK`). |
| **SPA Routes & i18n** | `apps/web/src/routes/{SettingsIamOrganizationSection.tsx,SettingsIamGrantsList.tsx,settings.tsx}`, `i18n/locales/*.ts`, `contextualHelpCatalog.ts`, `platformSetupStore.tsx` | Modifiés / Créés | Éradication totale de `"Lire / Voir les secrets"` / `"Read / View secrets"` (`0` occurrence en production), parité FR/EN complète, réhydratation `GET` au montage (survie au `F5`). |
| **Registre & Sprint** | `docs/product/capabilities.yaml`, `docs/implementation-artifacts/sprint-status.yaml` | Modifiés | Mise à jour de `CAP-050`, `CAP-051`, `CAP-055`, `CAP-057` ; `17-3-...` passé à `done` et `17-4-...` à `ready-for-dev`. |
| **Tests (`AD-17`)** | `tests/unit/test_story_17_3_iam_accounts_and_role_matrix.py`, `tests/integration/api/test_story_17_3_iam_accounts_and_secops_postgres18.py`, `apps/web/src/__tests__/{vitestIamMockHandlers.ts,story-17-3-iam-accounts-matrix-and-secops-drawer.test.tsx,i18n-and-shell.test.tsx}` | Créés / Modifiés | Couverture complète des 5 couches `AD-17` et sécurité. |

### 3.2 Métriques de Qualité, Couverture (`>= 90 %`) & Validation des 5 Couches (`AD-17`)

- **Qualité Statique & Architecture Python** :
  - `ruff format --check .` : `678 files already formatted` (`0` écart).
  - `ruff check .` : `All checks passed!` (`0` erreur, y compris `TID251` et `E501`).
  - `mypy --strict packages/orcia-core packages/orcia-connectors apps/api apps/worker` : `Success: no issues found in 279 source files`.
  - `lint-imports` : `Contracts: 5 kept, 0 broken` (`314` fichiers, `1848` dépendances, zéro cycle, pureté hexagonale `orcia_core.permissions` respectée).
  - `lint_spine.py` : `ok: true, total_findings: 0`.
- **Couche 1a & Couche 2 (Pytest Unitaires + Audit Architectural + PostgreSQL 18 `testcontainers`)** :
  - `26 passed` (`test_story_17_3_iam_accounts_and_role_matrix.py`, `test_epic_8_settings_rbac_llm_studio_and_wizards.py`, `test_permissions_and_auth.py`, `test_codebase_architectural_anti_patterns_audit.py`, `test_story_17_3_iam_accounts_and_secops_postgres18.py` avec cycle Alembic `20261111_1703` `upgrade -> downgrade -> upgrade` et requêtes `SELECT` SQL directes sur `iam_accounts`, `org_units` et `role_permission_grants`).
  - **Couverture mesurée (`--cov-fail-under=90`)** : **`91.96 %`** au global (`iam_accounts.py` : `100 %`, `sql_iam_accounts.py` : `95 %`, `role_matrix.py` : `94 %`, `sql_iam_grants.py` : `86 %`, `sql_iam_account_helpers.py` : `82 %`).
- **Couche 3 (Contrats OpenAPI 3.1 `0-diff` & Fuzzing Schemathesis)** :
  - `scripts/export_openapi.py --check` : `0-diff`.
  - `pytest tests/contract/test_openapi_contract.py` : `2 passed` (`100 %`).
- **Couche 1b & Garde-Fous Frontend TypeScript (`pnpm turbo run lint typecheck test`)** :
  - `Tasks: 9 successful, 9 total` (`@orcia/ui`, `@orcia/api-client`, `@orcia/web` `lint` + `typecheck` + `test`).
  - `@orcia/web:test` : **`12/12` suites passées (`63/63` tests)** incluant `story-17-3-iam-accounts-matrix-and-secops-drawer.test.tsx` (`3/3`, survie au `F5` `unmount -> render`, séparation `SECOPS`, anti-lockout `422`, tiroir SecOps), `i18n-and-shell.test.tsx` (`26/26`), `design-system-look-and-feel-isolation.test.tsx` et `zero-dead-buttons-and-silent-catches-audit.test.tsx`.
- **Sécurité & Politique `AD-21` Zéro Secret Exposé** :
  - `0` occurrence de `"Lire / Voir les secrets"` ou `"Read / View secrets"` dans le code de production `apps/web` et `packages/ui`.
  - `secret_visibility_policy == "WRITE_ONLY_NEVER_READABLE"` appliqué de bout en bout.
