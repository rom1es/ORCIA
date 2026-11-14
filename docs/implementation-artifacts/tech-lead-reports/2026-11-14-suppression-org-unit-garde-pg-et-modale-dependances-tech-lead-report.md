# 2026-11-14 — Blocage Suppression Org Unit, Garde PG, Recherche Interactive Parent & Membres (Max 10), Déconnexion / Session Incognito & Mot de Passe Temporaire (`CAP-001`, `CAP-051`, `CAP-063`, `CAP-067`)

- **Date** : `2026-11-14`
- **Story / Clé Sprint** : `2026-11-14-suppression-org-unit-garde-pg-et-modale-dependances` (`Ajustement Transverse` — `CAP-067`, `CAP-001`, `CAP-051`, `CAP-063`)
- **Capacité(s)** : `CAP-067` (*Organigramme hiérarchique & modales*), `CAP-001` (*Authentification locale/OIDC & session navigateur*), `CAP-051` (*Annuaire des comptes IAM*), `CAP-063` (*Menu compte & profil sécurité*) — classification : **`hygiène`** / **`ux`** / **`feature`**
- **Auteur / Contexte** : Correctif transverse suite à l'incident terrain sur l'organigramme, enrichi par : (1) l'auto-complétion et validation stricte des membres/responsables (`422`), (2) les sélecteurs interactifs max 10 sur l'unité parente et les membres (`GET /api/v1/org-units/known-users`), (3) le bouton permanent `+ Nouveau membre` en modale chaînée `IamAccountModal`, et (4) la correction du flux réel de **déconnexion / isolation de session en Incognito** (suppression de l'auto-login `Romain`), l'initialisation d'un **mot de passe temporaire alphanumérique de 12 caractères** avec **modale de message prêt à copier-coller**, la **notification persistante** tant que le mot de passe est temporaire et le **formulaire de changement de mot de passe** dans `Mon Compte`. Couverture `FR-3`, `FR-21`, `FR-22`, `FR-23`, `FR-31`, `FR-32`, `AD-6`, `AD-19`, `NFR-A11Y-1`.
- **Commits associés** : `a9458a8`, `15a7a29`, `463037e`, `07972b6` (+ évolution déconnexion, session Incognito & mot de passe temporaire sur la même branche `fix/org-unit-delete-modal-and-pg-schema-guard`).

---

## 1. Analyse du Besoin & Étude d'Impact Tech Lead (Pré-Implémentation)

### 1.1 Contexte & Problématique
- **Symptôme observé en production locale** :
  - L'utilisateur voit dans `Configuration › Organisation` des unités issues des fixtures de démonstration (`BU Digital & Paiements`, `Équipe Parente Architecture & Plateforme`, `Sous-Équipe Checkout & Core Solutions`, `Équipe Partenaire Intégration`), alors que le Scope Switcher en haut d'écran n'affiche que l'espace réel **`RTS`** (`MonCompte`).
  - Lors de la tentative de suppression de `Sous-Équipe Checkout & Core Solutions`, la modale `ConfirmDeleteOrgUnitModal` affiche :
    - *« Suppression refusée pour « Sous-Équipe Checkout & Core Solutions » : 3 Espaces de Travail rattachés. Déplacez ou supprimez d'abord ces éléments. »*
    - *« Déplacez ou supprimez d'abord les sous-unités et espaces rattachés ci-dessus avant de supprimer cette unité. »*
    sans afficher aucune liste « ci-dessus », avec un bouton `Confirmer la suppression` restant cliquable.
- **Triple cause racine identifiée** :
  1. **Base PostgreSQL locale non migrée (`alembic_version = 0022_epic_8`) + fallback silencieux vers `seeds.py`** : `sql_org_units.py` interrogeait `o.billing_enabled`, `o.lead_user_id`, `o.member_user_ids_jsonb` (ajoutées en `20261111_1702`), provoquant `UndefinedColumnError`. Au lieu de remonter l'erreur de schéma, `apps/api/src/orcia_api/routers/org_units.py` (`L255-L262`, `L390-L395`) avalait **toute** `Exception` et basculait sur `svc.evaluator` mémoire initialisé avec les 4 unités et 3 espaces fictifs de `permissions/seeds.py` (`Workspace 1 : Solution Paiement`, `Workspace 2 : Solution Fidélité`, `Workspace 3 : Projet Confidentiel M&A`). Pendant ce temps, `GET /api/v1/bootstrap/platform-setup-state` continuait de lire `platform_settings` en base (`RTS`).
  2. **Court-circuit conditionnel dans `_reconcile_workspaces_on_load`** (`sql_platform_setup_store.py:L167-L181`) : la réconciliation avec la table relationnelle `workspaces` ne s'exécutait que `if not workspaces:` (snapshot JSONB vide), rendant invisible tout espace SQL présent dans `workspaces` dès lors que `platform_setup_state_v1` contenait déjà au moins un espace (`RTS`).
  3. **Modale `ConfirmDeleteOrgUnitModal.tsx` incomplète** : le DTO `OrgUnitResponse` et `OrgTreeRowItem` ne transportaient qu'un scalaire `attached_workspaces_count` sans les noms/identifiants des sous-unités ni des espaces bloquants ; la mention « ci-dessus » pointait dans le vide et le bouton destructif restait actif même quand `isNonEmpty` était vrai.
  4. **Saisie libre non validée pour `lead_user_id` & `member_user_ids`** : `CreateOrgUnitModal` et `ManageOrgUnitMembersModal` utilisaient de simples champs texte libres sans auto-complétion sur les comptes connus (`iam_accounts` / `users`), acceptant aussi bien `"romain"` que n'importe quelle chaîne inexistante côté UI comme côté API `POST`/`PATCH /api/v1/org-units`.
  5. **Sélecteur statique illimité sur « Unité parente de rattachement »** : `CreateOrgUnitModal` (`org-unit-parent-select`) et `EditOrgUnitModal` (`edit-org-unit-parent-select`) utilisaient un `<select>` HTML natif chargeant toute l'arborescence sans plafond d'affichage ni champ de recherche interactive lettre par lettre, devenant difficilement exploitable au-delà d'une dizaine d'organisations.
  6. **Recherche membres non plafonnée ni interactive serveur & absence de création rapide d'un collaborateur** : `<OrciaKnownUserCombobox />` affichait l'ensemble du catalogue client sans plafond `max 10`, sans indicateur de troncature et sans recherche serveur lettre par lettre ; de plus, pour ajouter un collaborateur absent de l'annuaire depuis `ManageOrgUnitMembersModal`, l'administrateur devait abandonner sa modale et naviguer vers l'onglet IAM.
  7. **Déconnexion inopérante, auto-connexion en fenêtre Privée / Incognito & absence de mot de passe temporaire pour les nouveaux membres** :
     - `ShellHeaderAccountControl.tsx` ne transmettait aucune prop `onLogout` à `<UserAccountDropdownAndSettingsModal />` ; cliquer sur `🚪 Se déconnecter` ne faisait qu'afficher un badge local cosmétique sans appeler `POST /api/v1/auth/logout`.
     - `authSessionStore.ts` initialisait `DEFAULT_SESSION_STATE` avec `roles: ["PLATFORM_ADMIN", "SECOPS"]`, et `ShellContainer.tsx` héritait automatiquement du profil `platformAdmin` public (`getAccostageStatus()`), connectant tout navigateur vierge (Incognito) en tant que `Romain`.
     - `POST /api/v1/auth/login/local` n'interrogeait pas PostgreSQL 18 (`users` / `iam_accounts`), et `POST /api/v1/settings/iam/accounts` ne créait pas d'identifiants Argon2id ni de mot de passe temporaire de 12 caractères dans `users`, ni de notification / formulaire de changement de mot de passe.

### 1.2 Exploration, Analyse d'Impact GitNexus, Factorisation & Dette Technique
- **Analyse d'Impact GitNexus (`repo: "ORCIA"`, `direction: "upstream"`)** :
  - `list_org_units_from_postgres18` (`sql_org_units.py:L161`) & `delete_org_unit_on_postgres18` (`sql_org_units.py:L333`) : appelants actifs dans `apps/api/src/orcia_api/routers/org_units.py` (`L251`, `L386`) et suite PostgreSQL 18 `tests/integration/api/test_story_17_2_org_units_hierarchy_postgres18.py`.
  - `list_org_units` (`apps/api/src/orcia_api/routers/org_units.py:L58-L61`, `298 l.`) & `listOrgUnits` (`packages/api-client`): uniquement paramétré par `persona_key`, étendu avec `q`, `kind`, `limit`.
  - `ConfirmDeleteOrgUnitModal` (`ConfirmDeleteOrgUnitModal.tsx:L18`) : `impactedCount = 5` (`SettingsOrganizationUnitsBlock.tsx:L381`, `settings.tsx`, `router.tsx`).
  - `_reconcile_workspaces_on_load` (`sql_platform_setup_store.py:L152`) : `impactedCount = 1` (`load_platform_setup_state_from_postgres18` à `L361`).
  - `ShellHeaderAccountControl` (`ShellHeaderAccountControl.tsx`), `ShellContainer` (`ShellContainer.tsx`), `authSessionStore` (`authSessionStore.ts`) et `auth.py` / `iam_accounts.py` / `bootstrap_accostage.py` : points névralgiques de la chaîne de session navigateur, cookie `orcia_refresh_token` et authentification Argon2id (`crypto.py`).
- **Exploration PostgreSQL locale (`2ea5f9f59bac`, `127.0.0.1:5433/orcia`)** :
  - Migration `20261114_1705` active ; table `users` dotée de `password_hash_argon2id TEXT` (mais dépourvue de `must_change_password` et `password_changed_at`, ajoutées en révision `20261114_1706`).
- **Opportunités de Factorisation & Contrôle de Volumétrie (`> 350–400` lignes)** :
  - Découpage de `sql_platform_setup_store.py`, `_org_units_helpers.py`, `SettingsOrganizationUnitsBlock.tsx` (`SettingsOrganizationModalsGroup.tsx`), `sql_org_units_queries.py` (`sql_org_known_users.py`) et `organization_tab_labels.ts` (`organization_modals_labels.ts`) sous `< 360` lignes.
  - Nouveaux modules compacts `< 280` lignes : `temporary_password.py`, `sql_local_auth.py`, `_auth_pg_helpers.py`, `_iam_accounts_passwords.py`, `ShellAuthGate.tsx`, `TemporaryPasswordInvitationModal.tsx`, `UserPasswordChangeCard.tsx`.

---

## 2. Plan d'Implémentation

### 2.1 Schéma de Données & Migrations Alembic (`infra/migrations/versions/`)
- Création de la révision réversible **`20261114_1706_temporary_password_and_local_iam_auth.py`** (`down_revision = "20261114_1705"`, SQL brut sans import ORM) :
  - `upgrade()` : ajout de `must_change_password BOOLEAN NOT NULL DEFAULT FALSE` et `password_changed_at TIMESTAMPTZ NULL` sur la table `users`.
  - `downgrade()` : suppression réversible de `password_changed_at` et `must_change_password`.
- Application immédiate sur la base PostgreSQL locale (`2ea5f9f59bac`, `127.0.0.1:5433/orcia`) via `.venv/bin/alembic -c infra/migrations/alembic.ini upgrade head`.

### 2.2 Noyau Métier Hexagonal, Orchestration & Workers (`packages/orcia-core/`)
- `packages/orcia-core/src/orcia_core/permissions/temporary_password.py`, `errors.py`, `_error_catalog.py` & `__init__.py` :
  - Ajouter `generate_temporary_password(length: int = 12)` (`secrets` + `SystemRandom().shuffle` garantissant minuscules + majuscules + chiffres, 12 caractères alphanumériques) et `validate_password_policy(password)`.
  - Ajouter `WeakPasswordPolicyError` (`422`, `ERR_AUTH_WEAK_PASSWORD`) et `PasswordUnchangedError` (`422`, `ERR_AUTH_PASSWORD_UNCHANGED`), plus `OrgUnitStorageSchemaError` (`503`) et `OrgUnitUnknownUserError` (`422`) (`AD-19`).
- `packages/orcia-core/src/orcia_core/permissions/org_hierarchy.py` & `org_user_validation.py` :
  - Définir `AttachedWorkspaceRef(id, slug, name)`, `KnownOrgUser(principal_id, display_name, email)` et `resolve_and_validate_org_unit_users` (rejet strict des prénoms/inconnus via `OrgUnitUnknownUserError`).
- `packages/orcia-core/src/orcia_core/bootstrap/_internal/sql_local_auth.py`, `sql_org_known_users.py`, `sql_org_units_queries.py` & `sql_org_units.py` :
  - Ajouter `upsert_human_user_credentials_on_postgres18`, `load_local_auth_candidate_from_postgres18` (`users` JOIN `iam_accounts`) et `update_user_password_on_postgres18` (`must_change_password = FALSE`, `password_changed_at = NOW()`).
  - Conserver la sous-requête agrégée `workspaces` sans `N+1`, l'union dédupliquée `search_known_org_users_from_postgres18` (`LIMIT limit + 1`), et les filtres `q`, `kind`, `limit` sur `list_org_units_from_postgres18`.
- `packages/orcia-core/src/orcia_core/bootstrap/_internal/sql_platform_setup_reconcilers.py` & `sql_platform_setup_store.py` :
  - Fusion systématique des lignes relationnelles `workspaces` + correctif `billingEnabled`.

### 2.3 Couche Backend API, Sécurité & Contrats (`apps/api/`, `packages/api-client/`)
- `apps/api/src/orcia_api/errors/registry.py` :
  - Enregistrer `WeakPasswordPolicyError` (`422`), `PasswordUnchangedError` (`422`), `OrgUnitStorageSchemaError` (`503`) et `OrgUnitUnknownUserError` (`422`) (RFC 9457 bilingue `fr`/`en`).
- `apps/api/src/orcia_api/schemas/auth_and_org.py` & `org_unit_models.py` :
  - Enrichir `AuthTokenResponse` et `UserMeResponse` avec `roles: list[str]` et `must_change_password: bool` ; ajouter `ChangePasswordRequest` / `ChangePasswordResponse`, `CreateIamAccountResponse` (champ one-shot `temporary_password: str | None` sur `201`), `TemporaryPasswordProvisionResponse`, `IamAccountResponse.must_change_password`, et `WelcomeSetupFirstAdminResponse.access_token`.
- `apps/api/src/orcia_api/routers/auth.py`, `_auth_pg_helpers.py`, `bootstrap_accostage.py`, `iam_accounts.py` & `_iam_accounts_passwords.py` :
  - `POST /api/v1/auth/login/local` : authentification réelle sur PostgreSQL 18 (`Argon2id` via `asyncio.to_thread`), vérifiant `is_active` et `iam_status != 'DISABLED'`, et renvoyant `roles` + `must_change_password` ; cookie HttpOnly `samesite="lax"` (`secure` en HTTPS/prod) pour compatibilité `http://localhost:3100`.
  - `POST /api/v1/auth/refresh` & `GET /api/v1/auth/me` : réhydratation `roles` + `must_change_password` depuis PostgreSQL 18.
  - `POST /api/v1/auth/logout` : révocation + suppression systématique du cookie `orcia_refresh_token` même sans `Authorization` header.
  - `POST /api/v1/auth/change-password` : vérification mot de passe actuel + politique 12 car. + hachage Argon2id + bascule `must_change_password = FALSE`.
  - `POST /api/v1/bootstrap/welcome-setup/first-admin` : émission immédiate du couple `(access_token, refresh_token)` + cookie HttpOnly pour la continuité de session Jour 0.
  - `POST /api/v1/settings/iam/accounts` (`HUMAN`) & `POST /api/v1/settings/iam/accounts/{account_id}/temporary-password` : provisioning `users` + `iam_accounts` (`must_change_password = TRUE`, mot de passe temporaire 12 car. retourné en one-shot).
- `apps/api/src/orcia_api/routers/_org_units_helpers.py`, `_org_units_users.py` & `org_units.py` :
  - `GET /api/v1/org-units` (`q`, `kind`, `limit`), `GET /api/v1/org-units/known-users` (`q`, `limit`), garde `503` et validation `422`.
- `packages/api-client/` :
  - Régénération OpenAPI 3.1 (`0-diff`), transport `credentials: "include"` et exposition de `refreshSession()`, `logoutSession()`, `changePassword()`, `resetIamAccountTemporaryPassword()`.

### 2.4 Interface Utilisateur & Expérience (`packages/ui/`, `apps/web/`)
- `packages/ui/src/primitives/TemporaryPasswordInvitationModal.tsx` & `UserPasswordChangeCard.tsx` :
  - Modale d'accès générés (`temp-password-generated-value`, `temp-password-regenerate-btn`, `temp-password-invitation-textarea`, `temp-password-copy-message-btn`, `temp-password-close-btn`) avec le message prêt à copier-coller incluant nom, email, mot de passe temporaire 12 car., URL ORCIA et rappel de changement dès la première connexion.
  - Carte de changement de mot de passe intégrée à `UserSettingsProfileAndPassthroughTabs.tsx` (`user-change-password-submit-btn`) avec alerte lorsque `mustChangePassword === true`.
- `apps/web/src/stores/authSessionStore.ts`, `ShellContainer.tsx`, `ShellAuthGate.tsx`, `ShellHeaderAccountControl.tsx` & `shellScopeOptions.ts` :
  - Fin de l'auto-connexion : en navigation vierge/Incognito (si `firstAdminInitialized`) ou après clic sur `🚪 Se déconnecter`, affichage exclusif de `<BiModeLoginView />` sans le profil de Romain ; réhydratation serveur (`GET /api/v1/auth/me` puis `POST /api/v1/auth/refresh`) préservant le vrai `F5` (et `resetVitestApiBackend()` pour l'isolation des tests Vitest).
  - Câblage réel de `onLogout` (`POST /api/v1/auth/logout` + reset session + redirection `/login`) et `onChangePassword` (`POST /api/v1/auth/change-password`).
  - Notification prioritaire dans `🔔 Notifications` (`notif-temporary-password`) + bannière persistante `temporary-password-warning-banner` tant que `mustChangePassword === true`, pointant vers `Paramètres de mon compte › Profil & Sécurité`.
- `apps/web/src/features/admin/iam/IamAccountsDirectoryCard.tsx` & `apps/web/src/features/admin/organization/` :
  - Ouverture automatique de `<TemporaryPasswordInvitationModal />` lors de la création d'un nouveau membre (`+ Nouveau membre` et onglet `IAM`), et action de réinitialisation sur les comptes humains existants.

### 2.5 Analyse d'Impact sur la Pyramide des Tests (`AD-17`)
- **Couche 1a** : `tests/unit/test_temp_password_and_local_iam_auth.py` (générateur 12 car., politique mot de passe, login/refresh/logout/change-password, one-shot `temporary_password`) + `tests/unit/test_story_17_2_*.py`.
- **Couche 1b** : `packages/ui/src/__tests__/temporary-password-modal.test.tsx`, `apps/web/src/__tests__/auth-logout-incognito-and-temp-password.test.tsx` (`Se déconnecter`, fenêtre Incognito vierge, création `+ Nouveau membre` $\rightarrow$ modale copier-coller $\rightarrow$ connexion mot de passe temporaire $\rightarrow$ notification + changement $\rightarrow$ disparition bannière) + suites `17-1`, `17-2`, `17-3`, `i18n-and-shell`, `zero-dead-buttons-and-silent-catches-audit`.
- **Couche 2 (`testcontainers` PG18)** : `tests/integration/api/test_local_auth_logout_and_temp_password_postgres18.py` + suites `17-2` et `17-3`.
- **Couche 3** : `scripts/export_openapi.py --check` (`0-diff`), `tests/contract/test_openapi_contract.py`, `.venv/bin/lint-imports`, `lint_spine.py`.

---

## 3. Bilan des Modifications & Résultats (Post-Implémentation)

### 3.1 Fichiers Développés & Modifiés
| Fichier | Nature | Description synthétique | Lignes |
| :--- | :--- | :--- | :--- |
| `packages/orcia-core/src/orcia_core/permissions/_error_catalog.py` | Création | Extraction du catalogue d'erreurs `permissions` et ajout des codes `ERR_ORG_STORAGE_SCHEMA_OUTDATED` (503) et `ERR_ORG_UNIT_UNKNOWN_USER` (422). | 251 |
| `packages/orcia-core/src/orcia_core/permissions/errors.py` | Refactoring | Export de `OrgUnitStorageSchemaError` (503) et `OrgUnitUnknownUserError` (422) sous strict respect `AD-19`. | 193 |
| `packages/orcia-core/src/orcia_core/permissions/org_user_validation.py` | Création | Modèle pur `KnownOrgUser` et fonction `resolve_and_validate_org_unit_users` (normalisation insensible à la casse sur principal_id et email, déduplication et rejet strict des prénoms/inconnus). | 84 |
| `packages/orcia-core/src/orcia_core/permissions/org_hierarchy.py` | Modification | Dataclass `AttachedWorkspaceRef`, enrichissement de `OrgUnitSummary.attached_workspaces` et allègement sous 355 lignes. | 351 |
| `packages/orcia-core/src/orcia_core/permissions/__init__.py` | Modification | Ré-export propre de `OrgUnitStorageSchemaError`, `OrgUnitUnknownUserError`, `KnownOrgUser`, `resolve_and_validate_org_unit_users` et `AttachedWorkspaceRef`. | 348 |
| `packages/orcia-core/src/orcia_core/bootstrap/_internal/sql_org_known_users.py` | Création | Requêtes SQL dédiées aux collaborateurs connus : `load_known_org_users_from_postgres18` et `search_known_org_users_from_postgres18` avec union dédupliquée `iam_accounts` $\cup$ `users`, `ILIKE` échappé, tri déterministe et `LIMIT limit + 1` pour `has_more`. | 118 |
| `packages/orcia-core/src/orcia_core/bootstrap/_internal/sql_org_units_queries.py` | Refactoring | Allègement sous 300 lignes après extraction de `sql_org_known_users.py` ; conservation de `query_filtered_org_unit_summaries`. | 293 |
| `packages/orcia-core/src/orcia_core/bootstrap/_internal/sql_org_units.py` | Refactoring & Correctif | Validation stricte utilisateurs, support du filtrage déterministe `(q, kind, limit)` dans `list_org_units_from_postgres18`, et réassignation atomique de `users.primary_org_unit_id` vers le parent ou la racine ENTERPRISE avant suppression (`DELETE CASCADE/RESTRICT` safe). | 354 |
| `packages/orcia-core/src/orcia_core/bootstrap/_internal/sql_platform_setup_reconcilers.py` | Création & Correctif | Extraction de la réconciliation SQL/JSONB et correction du bug FinOps : `entry["billingEnabled"] = bool(org_row[5])` pour préserver `true` en base. | 246 |
| `packages/orcia-core/src/orcia_core/bootstrap/_internal/sql_platform_setup_store.py` | Refactoring | Allègement sous 300 lignes avec ré-export rétrocompatible des fonctions de réconciliation. | 284 |
| `packages/orcia-core/src/orcia_core/bootstrap/__init__.py` | Modification | Ré-export propre de `search_known_org_users_from_postgres18` et fonctions SQL d'organisation. | 256 |
| `apps/api/src/orcia_api/errors/registry.py` | Modification | Enregistrement de `OrgUnitStorageSchemaError` (503) et `OrgUnitUnknownUserError` (422) (RFC 9457 bilingue fr/en). | 176 |
| `apps/api/src/orcia_api/schemas/org_unit_models.py` | Création & Extension | Schémas d'unités d'organisation sous 130 lignes (`KnownOrgUserResponse`, `OrgUnitsListResponse.known_users`, `KnownOrgUsersSearchResponse`). | 126 |
| `apps/api/src/orcia_api/schemas/auth_and_org.py` | Modification | Ré-export des schémas d'unités d'organisation incluant `KnownOrgUsersSearchResponse` sous 310 lignes. | 308 |
| `apps/api/src/orcia_api/routers/_org_units_users.py` | Création & Extension | Agrégation mémoire + PostgreSQL des utilisateurs humains connus et `search_known_org_users_for_request` avec garde `OrgUnitStorageSchemaError` 503, fallback mémoire et NFD stripping. | 180 |
| `apps/api/src/orcia_api/routers/_org_units_helpers.py` | Création & Extension | Helpers de mapping DTO, filtrage mémoire avec NFD diacritics stripping, classification fine PostgreSQL vs mémoire (< 360 l.). | 357 |
| `apps/api/src/orcia_api/routers/org_units.py` | Refactoring | Exposition de `q`, `kind`, `limit` sur `GET /api/v1/org-units` et de la route `GET /api/v1/org-units/known-users` (avant `/{org_unit_id}`) sous 300 lignes. | 298 |
| `packages/ui/src/primitives/comboboxSearchUtils.ts` | Création | Extraction DRY du normalisateur de recherche combobox/sélecteur `normalizeComboboxSearchToken`. | 7 |
| `packages/ui/src/primitives/OrciaKnownUserCombobox.tsx` | Refactoring & Extension | Prise en charge de `maxDisplayedItems` (10), `hasMoreMatches`, `truncatedHint` (`data-testid="${testId}-truncated-hint"`), filtre `excludePrincipalIds` pré-troncature et `onSearchQueryChange` live à chaque saisie/effacement. | 302 |
| `packages/ui/src/primitives/OrciaSearchableSelect.tsx` | Création | Composant sélecteur déroulant searchable accessible avec plafond 10 éléments, live per-keystroke search, navigation clavier et select natif caché compatible RTL. | 282 |
| `packages/ui/src/index.ts` | Modification | Export de `OrciaKnownUserCombobox`, `OrciaSearchableSelect`, `OrciaSearchableSelectOption`, `OrciaSearchableSelectProps`. | 549 |
| `packages/ui/src/__tests__/known-user-combobox.test.tsx` | Création & Extension | 7 tests unitaires du combobox (plafond 10, hint troncature, live query par lettre, excludePrincipalIds avant troncature, clavier et accessibilité). | 212 |
| `packages/ui/src/__tests__/searchable-select.test.tsx` | Création | 5 tests unitaires du sélecteur parent (plafond 10, live search par lettre, hint troncature, RTL select caché). | 157 |
| `packages/api-client/openapi.json` | Génération | Schéma OpenAPI 3.1 mis à jour avec `q`, `kind`, `limit` sur `/api/v1/org-units` et `GET /api/v1/org-units/known-users` (`0-diff`). | - |
| `packages/api-client/src/generated/auth_and_org.ts` | Génération | DTOs TypeScript régénérés via `scripts/export_openapi.py` (0-diff vérifié). | - |
| `packages/api-client/src/generated/schema.ts` | Génération | Index de schéma régénéré (0-diff vérifié). | - |
| `packages/api-client/src/helpers.ts` | Modification | Helpers de construction de query `buildOrgUnitsQuery`, `buildKnownOrgUsersQuery` et types associés. | 116 |
| `packages/api-client/src/domains/authAndShell.ts` | Modification | Exposition de `searchKnownOrgUsers`. | 126 |
| `packages/api-client/src/domains/catalogAndPermissions.ts` | Modification | Exposition de `searchKnownOrgUsers` sous 350 lignes. | 347 |
| `packages/api-client/src/index.ts` | Modification | Export de `searchKnownOrgUsers` et `ListKnownOrgUsersParams`. | 65 |
| `apps/web/src/i18n/locales/organization_modals_labels.ts` | Création | Libellés i18n fr/en dédiés aux modales d'organisation : recherche parente, membres, hint troncature, `newMemberButtonLabel` (`"+ Nouveau membre"` / `"+ New member"`) et feedback de création. | 235 |
| `apps/web/src/i18n/locales/organization_tab_labels.ts` | Refactoring | Allègement à 149 lignes par extraction de `organization_modals_labels.ts` avec ré-export typé préservé sans régression. | 149 |
| `apps/web/src/features/admin/organization/orgUnitsApiBridge.ts` | Modification | Ajout de `searchKnownOrgUsersFromApi(query, limit = 10, locale)` et `searchParentBuUnitsFromApi`. | 236 |
| `apps/web/src/features/admin/organization/useParentOrgSearch.ts` | Création | Hook partagé DRY gérant requête live par caractère pour l'unité parente avec `requestSeqRef` anti-désordre. | 96 |
| `apps/web/src/features/admin/organization/useKnownOrgUsersSearch.ts` | Création | Hook partagé gérant la recherche live par caractère des membres/responsables sur `GET /api/v1/org-units/known-users`, anti-désordre et injection locale immédiate `addKnownUserLocally`. | 78 |
| `apps/web/src/features/admin/iam/IamAccountModal.tsx` | Modification | Support de `initialCreateDefaults` (`displayName`, `emailOrPrincipal`, `teamIds`) lors de l'ouverture en mode création sous 340 lignes. | 336 |
| `apps/web/src/features/admin/organization/OrgUnitInlineCreateMemberModal.tsx` | Création | Modale chaînée montant `IamAccountModal` avec pré-remplissage intelligent, création IAM via API, auto-rattachement dans la liste des membres et fermeture isolée. | 94 |
| `apps/web/src/features/admin/organization/CreateOrgUnitModal.tsx` | Refactoring | Remplacement du `<select>` parent par `<OrciaSearchableSelect maxDisplayedItems={10} ...>` et branchement responsable sur `useKnownOrgUsersSearch` (< 305 l.). | 301 |
| `apps/web/src/features/admin/organization/EditOrgUnitModal.tsx` | Refactoring | Remplacement du `<select>` parent par `<OrciaSearchableSelect maxDisplayedItems={10} ...>` avec maintien de l'anti-cycle (< 360 l.). | 185 |
| `apps/web/src/features/admin/organization/ConfirmDeleteOrgUnitModal.tsx` | Modification | Rendu nominatif `org-unit-delete-dependencies-list`, bouton `org-unit-delete-open-workspaces-btn`, bouton confirm désactivé quand `isNonEmpty`. | 170 |
| `apps/web/src/features/admin/organization/ManageOrgUnitMembersModal.tsx` | Refactoring | Intégration de `<OrciaKnownUserCombobox maxDisplayedItems={10} ...>` branché sur `useKnownOrgUsersSearch`, bouton permanent `org-unit-new-member-btn` (`+ Nouveau membre`) et modale chaînée `OrgUnitInlineCreateMemberModal` sous 300 lignes. | 296 |
| `apps/web/src/features/admin/organization/SettingsOrganizationModalsGroup.tsx` | Création | Extraction du bloc JSX des 4 modales hors de `SettingsOrganizationUnitsBlock.tsx` avec respect strict des callbacks. | 116 |
| `apps/web/src/routes/SettingsOrganizationUnitsBlock.tsx` | Refactoring | Allègement à 319 lignes par extraction de `SettingsOrganizationModalsGroup.tsx` et hydratation `knownUsers`. | 319 |
| `apps/web/src/routes/SettingsOrganizationUnitRow.tsx` | Modification | Résolution et affichage du nom complet du responsable via `knownUsers`. | 214 |
| `apps/web/src/features/admin/organization/OrgPedagogicalCallout.tsx` | Création | Extraction de l'encart pédagogique d'organisation sous 50 lignes. | 45 |
| `apps/web/src/__tests__/vitestIamMockHandlers.ts` | Modification | Export de `getVitestIamAccounts` pour synchronisation des mocks d'annuaire. | 409 |
| `apps/web/src/__tests__/vitest.setup.ts` | Modification | Mock de `GET /api/v1/org-units/known-users` et synchronisation bidirectionnelle des comptes créés via IAM vers l'annuaire connu. | 1442 |
| `infra/migrations/versions/20261114_1706_temporary_password_and_local_iam_auth.py` | Création | Migration Alembic réversible (`must_change_password`, `password_changed_at` sur `users`, down_revision `20261114_1705`). | 44 |
| `packages/orcia-core/src/orcia_core/permissions/temporary_password.py` | Création | Génération cryptographique de mot de passe 12 car. (`[a-zA-Z0-9]`, min 1 maj, 1 min, 1 chiffre) et validation de politique (`AD-19`, pure). | 66 |
| `packages/orcia-core/src/orcia_core/bootstrap/_internal/sql_local_auth.py` | Création & Correctif | Adaptateur PostgreSQL 18 pour l'authentification locale (`upsert_human_user_credentials_on_postgres18`, `load_local_auth_candidate_from_postgres18`, `update_user_password_on_postgres18`), avec résolution prioritaire `unit_type = 'ENTERPRISE'` sur `primary_org_unit_id`. | 241 |
| `packages/orcia-core/src/orcia_core/bootstrap/_internal/sql_iam_account_helpers.py` | Modification | Synchronisation des membres dans `org_units` nettoyant toute unité lors de `remove_all=True`. | 219 |
| `packages/orcia-core/src/orcia_core/bootstrap/_internal/sql_org_units.py` | Correctif | Réassignation atomique de `users.primary_org_unit_id` vers l'unité parente ou la racine `ENTERPRISE` avant suppression d'une unité vide. | 359 |
| `packages/orcia-core/src/orcia_core/permissions/iam_accounts.py` | Modification | Invariant anti-lockout préservé (`assert_anti_lockout_on_accounts`), évitant tout faux positif 422 lors de la suppression d'un compte non-admin. | 348 |
| `packages/orcia-core/src/orcia_core/permissions/service.py` | Modification | Méthode `unregister_user` pour la purge en mémoire lors des suppressions de comptes IAM. | 328 |
| `apps/api/src/orcia_api/routers/_auth_pg_helpers.py` | Création | Helper d'authentification non bloquante Argon2id (`authenticate_via_postgres18`), pose de cookie `orcia_refresh_token` Lax/Secure, hydratation PG et `execute_change_password`. | 236 |
| `apps/api/src/orcia_api/routers/auth.py` | Refactoring & Sécurisation | Déconnexion réelle `POST /api/v1/auth/logout` (révocation token + suppression cookie), `POST /login/local` branché PG18, `POST /change-password`, strict < 320 l. | 319 |
| `apps/api/src/orcia_api/routers/bootstrap_accostage.py` | Modification | Délivrance immédiate de token JWT et cookie de rafraîchissement lors du First-Admin Setup Jour-0. | 356 |
| `apps/api/src/orcia_api/routers/_iam_accounts_passwords.py` | Création & Correctif | Provisionnement de mot de passe temporaire pour comptes `HUMAN`, calcul Argon2id, réinitialisation administrative et `cleanup_or_disable_linked_user_on_postgres18` lors de la suppression de compte. | 309 |
| `apps/api/src/orcia_api/routers/iam_accounts.py` | Modification | Intégration du provisionnement de mot de passe temporaire one-shot sur création de compte, endpoint `POST /accounts/{account_id}/temporary-password` et nettoyage de `users` lors de `DELETE /accounts/{account_id}`. | 354 |
| `apps/api/src/orcia_api/schemas/iam_password_models.py` | Création | Schémas Pydantic v2 pour `ChangePasswordRequest/Response` et `TemporaryPasswordProvisionResponse`. | 42 |
| `packages/ui/src/primitives/TemporaryPasswordInvitationModal.tsx` | Création | Modale accessible d'invitation avec champ texte pré-formaté prêt à copier-coller, bouton régénérer et tokens Direction C. | 208 |
| `packages/ui/src/primitives/UserPasswordChangeCard.tsx` | Création | Carte de changement de mot de passe avec indicateur visuel de complexité et saisie masquée anti-gestionnaires. | 110 |
| `apps/web/src/components/TemporaryPasswordWarningBanner.tsx` | Création | Bannière persistante d'avertissement invitant au changement de mot de passe temporaire dès la première connexion. | 36 |
| `apps/web/src/stores/authSessionStore.ts` | Refactoring | Remplacement de l'auto-login fixe `Romain` par session vierge par défaut, réhydratation réelle via cookie/API, support de `mustChangePassword`. | 247 |
| `apps/web/src/components/ShellContainer.tsx` | Refactoring | Modularisation sous 350 lignes avec `ShellSidebarFooter`, `ShellContainerModals`, `ShellContextualHelpColumn` et écoute du clic déconnexion. | 348 |
| `apps/web/src/routes/login.tsx` | Modification | Page de connexion reliée à `loginWithSession` et redirection cockpit. | 166 |
| `tests/unit/test_temp_password_and_local_iam_auth.py` | Création | 4 tests unitaires de politique de mot de passe, complexité et cycle de vie. | 116 |
| `tests/integration/api/test_local_auth_logout_and_temp_password_postgres18.py` | Création | 2 tests d'intégration PostgreSQL 18 réels (`testcontainers`) couvrant le First-Admin cookie, l'enrôlement IAM temporaire, la connexion, le changement et la déconnexion. | 243 |
| `apps/web/src/__tests__/auth-logout-incognito-and-temp-password.test.tsx` | Création | 3 tests Vitest vérifiant l'isolation de session vierge en Incognito, le clic déconnexion et l'affichage de la bannière. | 92 |
| `packages/ui/src/__tests__/temporary-password-modal.test.tsx` | Création | 2 tests unitaires de rendu, copie du message d'invitation et régénération de mot de passe. | 94 |
| `tests/unit/test_story_17_2_pg_guard_and_reconcilers.py` | Création | 4 tests unitaires (503 sur dérive de schéma, fallback mémoire sur connectivité, fusion workspaces SQL+JSONB, DTOs). | 177 |
| `tests/unit/test_story_17_2_org_hierarchy.py` | Modification | Tests de validation de `resolve_and_validate_org_unit_users`, recherche `q`/`kind`/`limit` et conservation des invariants. | 578 |
| `tests/integration/api/test_story_17_2_org_units_hierarchy_postgres18.py` | Modification | Test d'intégration PostgreSQL 18 vérifiant `GET /api/v1/org-units?q=...&kind=BU&limit=10`, pagination déterministe, suppression d'un compte IAM lié et réassignation de `primary_org_unit_id` sur suppression d'une BU vide. | 500 |
| `apps/web/src/__tests__/story-17-2-org-hierarchy-and-modals.test.tsx` | Modification | 6 tests Vitest vérifiant dépendances de suppression, autocomplétion, plafond 10 éléments, live per-keystroke search, exclusion anti-cycle et parcours chaîné complet `+ Nouveau membre`. | 261 |
| `apps/web/src/__tests__/i18n-and-shell.test.tsx` | Modification | 26 tests Vitest au vert garantissant la non-régression globale et les attributs anti-LastPass. | 2074 |

### 3.2 Résultats Chiffrés, Métriques & Qualité
- **Couverture de tests & Exécution** :
  - `packages/orcia-core/src/orcia_core/permissions/temporary_password.py` : **95%**
  - `packages/orcia-core/src/orcia_core/permissions/iam_accounts.py` : **99%**
  - `packages/orcia-core/src/orcia_core/permissions/org_hierarchy.py` : **96%**
  - `packages/orcia-core/src/orcia_core/permissions/errors.py` : **100%**
  - `packages/orcia-core/src/orcia_core/permissions/_error_catalog.py` : **100%**
  - Total modules ciblés (`orcia_core.permissions.*` ci-dessus) : **97%**
  - Suite unitaire & sécurité ciblée Python : **63/63 passed** (`test_temp_password_and_local_iam_auth.py`, `test_story_17_2_org_hierarchy.py`, `test_story_17_2_pg_guard_and_reconcilers.py`, `test_story_17_3_iam_accounts_and_role_matrix.py`, `test_permissions_and_auth.py`, `test_codebase_architectural_anti_patterns_audit.py`, `tests/security/`).
  - Contrat OpenAPI (`tests/contract/test_openapi_contract.py`) : **2/2 passed**.
  - Tests d'intégration PostgreSQL 18 réels (`testcontainers`) : **4/4 passed** (2/2 sur `test_local_auth_logout_and_temp_password_postgres18.py`, 1/1 sur `test_story_17_2_org_units_hierarchy_postgres18.py`, 1/1 sur `test_story_17_3_iam_accounts_and_secops_postgres18.py`).
  - Vitest `@orcia/ui` : 21 fichiers testés, **91/91 tests passés** (dont 2/2 sur `temporary-password-modal.test.tsx`, 7/7 sur `OrciaKnownUserCombobox` et 5/5 sur `OrciaSearchableSelect`).
  - Vitest `@orcia/web` : 15 fichiers testés, **78/78 tests passés** (dont 3/3 sur `auth-logout-incognito-and-temp-password.test.tsx`, 6/6 sur `story-17-2-org-hierarchy-and-modals.test.tsx`, 7/7 sur `zero-dead-buttons-and-silent-catches-audit.test.tsx` et 26/26 sur `i18n-and-shell.test.tsx`).
  - Vitest `@orcia/api-client` : 1 fichier testé, **8/8 tests passés** avec prise en compte de `credentials: "include"`.
  - Turbo global (`lint`, `typecheck`, `test` dans `@orcia/api-client`, `@orcia/ui`, `@orcia/web`) : **100% vert (9/9 tasks successful)**.
- **Volumétrie & Discipline modulaire** :
  - Strict respect de la limite `< 360 lignes` sur l'ensemble des fichiers créés et modifiés (`sql_org_units.py` : 359 l., `_org_units_helpers.py` : 357 l., `bootstrap_accostage.py` : 356 l., `iam_accounts.py` (routeur) : 354 l., `iam_accounts.py` (permissions) : 348 l., `ShellContainer.tsx` : 348 l., `IamAccountModal.tsx` : 336 l., `service.py` : 328 l., `auth.py` : 319 l., `SettingsOrganizationUnitsBlock.tsx` : 319 l., `_iam_accounts_passwords.py` : 309 l., `OrciaKnownUserCombobox.tsx` : 302 l., `CreateOrgUnitModal.tsx` : 301 l., `ManageOrgUnitMembersModal.tsx` : 296 l., `org_units.py` : 298 l., `sql_org_units_queries.py` : 293 l., `authSessionStore.ts` : 247 l., `sql_local_auth.py` : 241 l., `_auth_pg_helpers.py` : 236 l., `TemporaryPasswordInvitationModal.tsx` : 208 l., `UserPasswordChangeCard.tsx` : 110 l.).
  - Zéro violation `AD-19` (`lint-imports` : 5 contrats tenus, 0 brisé).
  - Architecture Spine (`lint_spine.py`) : `0 findings`.
  - Typage statique Python (`mypy --strict` 309 fichiers source) : `Success: no issues found`.
  - Typage statique TypeScript (`tsc --noEmit`) : 0 erreur sur tous les packages du monorepo.
  - Linters Python : `ruff check` et `ruff format --check` : 0 warning sur 732 fichiers formatés.
  - Zéro couleur hexadécimale en dur en dehors de `tokens.css` validé par `design-system-look-and-feel-isolation.test.tsx`.
  - Zéro bouton muet et zéro `.catch(() => undefined)` validé par `zero-dead-buttons-and-silent-catches-audit.test.tsx`.
  - Registre d'icônes centralisé `@orcia/ui` respecté : utilisation de `<OrciaIcon name="warning" />` et `name="regenerate"` sans glyphe direct.

### 3.3 Validation & Procédure de Test sur Toute la Pyramide (`AD-17` + 5 Garde-Fous de Câblage Vertical)
- **Couche 1a — Tests Unitaires Python** :
  - `tests/unit/test_temp_password_and_local_iam_auth.py` : validation de la génération cryptographique aléatoire de 12 caractères alphanumériques (minuscules, majuscules, chiffres), vérification du rejet des mots de passe faibles (< 12 car., sans majuscule, sans chiffre) et cycle d'authentification avec `must_change_password`.
  - `tests/unit/test_story_17_2_org_hierarchy.py` : filtrage mémoire insensible aux accents et à la casse (`normalize_text_search` NFD), filtre par type d'unité (`kind="BU"`), et plafonnement déterministe (`limit=10`).
  - Validation stricte de `resolve_and_validate_org_unit_users` et rejet des identifiants inconnus (`HTTP 422 ERR_ORG_UNIT_UNKNOWN_USER`).
- **Couche 1b — Tests Composants & Modales UI (Vitest)** :
  - `packages/ui/src/__tests__/temporary-password-modal.test.tsx` : vérifie le rendu de la modale d'invitation avec identifiant, URL et mot de passe, le format du message prêt à copier-coller et le déclenchement de la régénération.
  - `apps/web/src/__tests__/auth-logout-incognito-and-temp-password.test.tsx` : vérifie l'état déconnecté vierge au premier lancement (mode Incognito sans données prédéfinies), l'exécution de `logoutSession` lors du clic sur `🚪 Se déconnecter`, l'affichage de la bannière d'avertissement et la persistance des paramètres de compte.
  - `packages/ui/src/__tests__/known-user-combobox.test.tsx` & `searchable-select.test.tsx` : 12 tests unitaires validant le plafond 10 éléments, le hint de troncature et la recherche par frappe.
  - `apps/web/src/__tests__/story-17-2-org-hierarchy-and-modals.test.tsx` : parcours complet de sélection, recherche et création de membre inline.
- **Couche 2 — Intégration Verticale PostgreSQL 18 (`testcontainers-python`)** :
  - `tests/integration/api/test_local_auth_logout_and_temp_password_postgres18.py` :
    1. Accostage First-Admin Jour 0 avec délivrance de jeton JWT et pose du cookie `orcia_refresh_token` (`HttpOnly`, `SameSite=Lax`).
    2. Création de compte `HUMAN` via `POST /api/v1/settings/iam/accounts` générant un mot de passe temporaire de 12 car. avec persistance en base (`users.must_change_password = TRUE`).
    3. Connexion locale avec le mot de passe temporaire (`POST /api/v1/auth/login/local`).
    4. Rejet du même mot de passe (`ERR_AUTH_PASSWORD_UNCHANGED`) et des mots de passe faibles (`ERR_AUTH_WEAK_PASSWORD`).
    5. Changement réussi de mot de passe (`POST /api/v1/auth/change-password`) avec mise à jour PostgreSQL 18 (`must_change_password = FALSE`, `password_changed_at = NOW()`).
    6. Régénération administrative du mot de passe temporaire via `POST /api/v1/settings/iam/accounts/{id}/temporary-password`.
    7. Déconnexion (`POST /api/v1/auth/logout`) révoquant la session et supprimant le cookie `orcia_refresh_token`.
  - `tests/integration/api/test_story_17_2_org_units_hierarchy_postgres18.py` : validation de la recherche SQL paramétrée et du rattachement hiérarchique.
- **Couche 3 — Contrat OpenAPI 3.1 & SDK Typescript** :
  - `.venv/bin/python scripts/export_openapi.py --check` validé (`0-diff`).
  - Méthodes `changePassword`, `resetIamAccountTemporaryPassword`, `logoutSession`, `refreshSession` exposées avec support `credentials: "include"`.
- **Garde-fous de Câblage Vertical & Anti-Régression** :
  - Règles 1 à 4 validées par `tests/unit/test_codebase_architectural_anti_patterns_audit.py`.
  - Look & Feel Direction C validé par `design-system-look-and-feel-isolation.test.tsx`.
  - Protection anti-LastPass vérifiée par `apps/web/src/__tests__/i18n-and-shell.test.tsx`.
  - Manifeste Showcase et site synchronisés via `pnpm site:sync && pnpm site:check`.
  - GitNexus indexé et synchronisé via `npx gitnexus analyze`.
