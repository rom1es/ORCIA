# Story 21.5 — Nouvelles Specs E2E Lot A (`14` à `16`) : Auth/2FA/Compte/Profil, Mon Organisation/IAM/SecOps/Inbox & Hub Modèles IA/Réindexation/Connecteurs/Permission Broker

- **Date** : 2026-11-18
- **Story / Clé Sprint** : `21-5-nouvelles-specs-e2e-lot-a-auth-2fa-mon-organisation-inbox-et-hub-ia-broker` (`Epic 21` — Lot A, sous-agent `21.5-impl` + sous-agent `21.5-test`)
- **Capacité(s)** : `CAP-001, CAP-003, CAP-040, CAP-041, CAP-043, CAP-050, CAP-051, CAP-052, CAP-053, CAP-054, CAP-058, CAP-063, CAP-065, CAP-067, CAP-069, CAP-190, CAP-203` — classification : `feature` (couverture E2E Playwright `UJ-4, UJ-7, UJ-13, UJ-14, UJ-15, UJ-16` et assertions `SELECT` PostgreSQL 18)
- **Auteur / Contexte** : Sous-agent `21.5-impl` (préparation des helpers réutilisables `authAndOrgHelpers.ts`, audit exhaustif des `data-testid` / routeurs / schémas PG18, mise à jour du registre `capabilities.yaml`). Exigence : `FR-2`, `FR-3`, `FR-21`, `FR-22`, `FR-31`, `FR-32`, `AD-17` Couche 5.
- **Commits associés** : En attente (après exécution de `21.5-test`)

---

## 1. Analyse du Besoin & Étude d'Impact Tech Lead (Pré-Implémentation)

### 1.1 Contexte & Problématique
- L'Epic 21 vise la couverture E2E Playwright réelle (`orcia_e2e` PostgreSQL 18 + `e2eCaptureFixture` + vrai `F5` après `localStorage.clear()`/`sessionStorage.clear()` + assertions `SELECT` PostgreSQL 18) de l'ensemble des `UJ-1..UJ-20`.
- Les 13 capacités du Lot A (`CAP-001, CAP-003, CAP-041, CAP-043, CAP-051, CAP-052, CAP-053, CAP-054, CAP-058, CAP-063, CAP-069, CAP-190, CAP-203`) portent actuellement `e2e_backlog_story: "21-5"` et `verification: docs` dans `docs/product/capabilities.yaml`. Elles doivent être couvertes par 3 nouvelles specs Playwright :
  - **Spec 14** (`apps/web/e2e/14-auth-2fa-account-and-profile.spec.ts`) : `@uj UJ-13, UJ-16` | `@cap CAP-001, CAP-058, CAP-063, CAP-069`
  - **Spec 15** (`apps/web/e2e/15-organization-iam-secops-inbox-and-observer.spec.ts`) : `@uj UJ-4, UJ-14` | `@cap CAP-040, CAP-041, CAP-043, CAP-050, CAP-051, CAP-065, CAP-067, CAP-203`
  - **Spec 16** (`apps/web/e2e/16-ai-models-reindex-connectors-and-broker.spec.ts`) : `@uj UJ-7, UJ-15` | `@cap CAP-003, CAP-052, CAP-053, CAP-054, CAP-190`
- Le périmètre de `21.5-impl` consiste à vérifier la disponibilité des sélecteurs `data-testid`, des routeurs backend et des tables/colonnes PostgreSQL 18 exactes, à créer le helper réutilisable `apps/web/e2e/support/authAndOrgHelpers.ts` (`< 220` lignes) sans dupliquer `day0.ts`/`firstAdmin.ts`/`orgAndWorkspace.ts`, et à préparer `docs/product/capabilities.yaml` sans écrire les `.spec.ts` `14..16` (confiés à `21.5-test`) ni modifier la logique métier.

### 1.2 Exploration, Analyse d'Impact GitNexus, Factorisation & Dette Technique
- **Analyse d'Impact GitNexus (`gitnexus:query`, `gitnexus:context`, `repo: "/home/romain/Documents/Projects/ORCIA"`)** :
  - `gitnexus:query` sur `PlatformAuthSettingsCard UserSettingsModalDialog OrganizationPageView AiModelsMasterTable` et `gitnexus:context` sur `SettingsHubView` (`apps/web/src/routes/settings.tsx:L31-258`) : `SettingsHubView` est monté par `SettingsRouteComponent` (`router.tsx`) et orchestre les 5 onglets (`SettingsIamOrganizationSection`, `SettingsAuthenticationSection`, `SettingsAiModelsSection`, `SettingsPacksSection`, `SettingsSecondaryTabsSection`).
  - L'audit des composants `@orcia/ui` et `apps/web/src/features/` montre que **tous** les écrans du Lot A possèdent déjà des attributs `data-testid` stables et complets — aucune modification de `@orcia/ui` ou `apps/web/src` n'est nécessaire.
- **Exploration & Constats Critiques sur le Câblage Réel (UI / API / PG18)** :
  1. **Spec 14 (Auth / 2FA / Mon Compte / `/profile`) — 100 % câblé PostgreSQL 18** :
     - `users`, `iam_accounts`, `platform_auth_settings`, `auth_login_challenges`, `user_preferences`, `user_mcp_tokens`, `audit_ledger` sont tous persistés en PG18 via `auth_settings.py`, `_auth_session_routes.py`, `user_account_settings.py`, `user_profile.py`, `iam_accounts.py`.
  2. **Spec 15 (Organisation / IAM / SecOps / Notifications / `/activity` / Observer `403`) — Écarts importants à noter** :
     - **Noms réels des tables PG18** : la table des exceptions SecOps est **`role_permission_grants`** (et non `iam_secops_exceptions`) ; la table des notifications est **`task_notifications`** (et non `inbox_notifications`).
     - **`org_units`, `iam_accounts`, `role_permission_grants`, `audit_ledger` (avec `org_unit_id`)** : persistés en PG18 (`org_units.py`, `iam_accounts.py`, `settings_and_studio.py`, `audit_ledger.py`).
     - **Notifications / `/inbox`** : la route `/inbox` (`apps/web/src/routes/inbox.tsx`) monte `ModuleWorkspaceView` → `InboxFeaturePanel` (workspace Assistant `assistant-*`), tandis que le tiroir de notifications du shell (`FourZoneNotificationsDrawer`) est alimenté par `buildShellNotificationItems(...)` dans `ShellContainer.tsx` (données dérivées du setup/runs, pas de `/api/v1/inbox/notifications`). Côté API, `UnifiedNotificationAndClaimService` (`core_and_lifespan.py:L219`) est encore un service en mémoire (`_notifications: dict[...]` amorcé si `ORCIA_E2E_SEED_FIXTURES=1`) qui n'écrit pas dans `task_notifications` PG18 (déjà observé dans `04-multi-actor-claim-sse.spec.ts` / `BUG-E2E-04`).
  3. **Spec 16 (Hub Modèles IA / Réindexation / Connecteurs / Passthrough / Permission Broker) — Écarts importants à noter** :
     - **`workspace_llm_tier_mappings`, `rag_reindexing_jobs`, `enterprise_connectors`, `user_connector_passthrough_tokens`** : 100 % câblés PG18 (`ai_models_hub.py`, `_ai_models_test_and_reindex_routes.py`, `enterprise_connectors.py`, `_auth_passthrough_routes.py`).
     - **Colonne `permission_broker_tickets.request_url`** : la colonne `jira_request_url` a été supprimée par la migration `0020_story_4_4_access_request_channel_contract.py` et remplacée par **`request_url`**.
     - **Câblage `PermissionBroker`** : `PermissionBrokerService` (`apps/api/src/orcia_api/routers/permission_broker.py` → `core_and_lifespan.py:L172`) fonctionne en mémoire (`build_default_permission_broker_service`), sans écriture dynamique dans `permission_broker_tickets` PG18 lors des appels `/api/v1/permissions/broker/check-access`. De plus, `PermissionBrokerCard` (`packages/ui/src/shell/PermissionBrokerCard.tsx`) était monté dans `AppShell`/`AssistantDock`, mais `ShellContainer.tsx` utilise `FourZoneDirectionCShell` sans y monter `PermissionBrokerCard`. Ces écarts doivent être documentés sans `test.skip` lors de la vérification API/UI par `21.5-test`.
- **Opportunités de Factorisation & Contrôle de Volumétrie** :
  - Création d'un seul helper factorisé `apps/web/e2e/support/authAndOrgHelpers.ts` (`< 220` lignes) qui réutilise `createFirstAdminViaUi` / `E2E_ADMIN` (`firstAdmin.ts`) et `createBuAndTeamViaUi` (`orgAndWorkspace.ts`) sans duplication.
  - Pas de dette technique supplémentaire à créer ici ; les écarts SQL/UI relevés sur `task_notifications` et `PermissionBroker` seront consolidés lors de l'audit Story 21.8.

---

## 2. Plan d'Implémentation

### 2.1 Schéma de Données & Migrations Alembic (`infra/migrations/versions/...`)
- Aucune migration Alembic requise (Story 21.5 porte exclusivement sur le harnais et les tests E2E Playwright Lot A).
- Tables PostgreSQL 18 vérifiées dans `infra/migrations/versions/` pour les assertions `SELECT` :
  - Spec 14 : `users` (`0002`, `20261114_1706`, `20261117_2001`), `iam_accounts` (`20261111_1703`, `20261115_1902`), `platform_auth_settings` & `auth_login_challenges` (`20261115_1901`), `user_preferences` & `user_mcp_tokens` (`20261117_2003`), `audit_ledger` (`20261116_0601`).
  - Spec 15 : `org_units` (`0002`, `20261111_1702`, `20261115_1902`, `20261117_2001`), `iam_accounts`, `role_permission_grants` (`0022`, `20261111_1703`), `audit_ledger` (`org_unit_id`, `20261117_2001`), `task_notifications` (`0021`).
  - Spec 16 : `workspace_llm_tier_mappings` (`0022`, `20261114_1705`, `20261115_2105`), `rag_reindexing_jobs` & `rag_reindexing_pending_ingestions` (`20261115_2307`), `enterprise_connectors` & `user_connector_passthrough_tokens` (`20261111_1704`, `20261114_1801`, `20261115_1901`), `user_passthrough_credentials` (`0002`, `0013`, `0014`), `permission_broker_policies` & `permission_broker_tickets` (`0004`, `0013`, `0014`, `0019`, `0020`).

### 2.2 Noyau Métier Hexagonal, Orchestration & Workers (`packages/orcia-core/`, `apps/worker/`)
- Aucune modification du noyau métier (`21.5-impl` préserve strictement la logique existante).

### 2.3 Couche Backend API, Sécurité & Contrats (`apps/api/`, `packages/api-client/`)
- Aucune modification backend API ou OpenAPI requise.
- Routes ciblées par les specs `14..16` :
  - `/api/v1/auth/*` (`login/local`, `2fa/verify`, `refresh`, `logout`, `change-password`, `public-config`), `/api/v1/settings/authentication`, `/api/v1/users/me/{preferences,mcp-tokens,profile-summary,account-profile}` ;
  - `/api/v1/org-units`, `/api/v1/org-units/invite-user`, `/api/v1/settings/iam/{accounts,grants,role-matrix}`, `/api/v1/audit/ledger`, `/api/v1/inbox/notifications` ;
  - `/api/v1/settings/ai-models/*` (`discover`, `mappings`, `mappings/{id}/test`, `reindex-status`, `reindex-embeddings`), `/api/v1/settings/connectors`, `/api/v1/users/me/passthrough`, `/api/v1/permissions/broker/*`.

### 2.4 Interface Utilisateur & Expérience (`apps/web/`, `docs/product/capabilities.yaml`)
- **Helper réutilisable `apps/web/e2e/support/authAndOrgHelpers.ts`** (`< 220` lignes) :
  - `getBearerTokenFromSession(page)` (via `POST /api/v1/auth/refresh` pour appels API authentifiés en parallèle des parcours UI) ;
  - `bootstrapAdminSession(page)` (réutilise `createFirstAdminViaUi` de `firstAdmin.ts`) ;
  - `loginLocalViaUi(page, { email, password, totpCode? })` sur `/login` (`BiModeLoginView`) ;
  - `openSettingsTabViaUi(page, tab)` (`iam`, `authentication`, `models`, `connectors`) ;
  - `openAccountPopover(page)` & `openUserSettingsTab(page, tab)` (`GENERAL`, `PERSONALIZATION`, `ACCOUNT_SECURITY`, `PASSTHROUGH_SOURCES`, `MCP_TOKENS`) ;
  - `createOrgUnitViaOrganizationUi(page, params)` & `inviteUserViaOrganizationUi(page, params)` sur `/organization`.
- **Registre `docs/product/capabilities.yaml`** :
  - Ajout des chemins `apps/web/e2e/14-auth-2fa-account-and-profile.spec.ts`, `apps/web/e2e/15-organization-iam-secops-inbox-and-observer.spec.ts`, `apps/web/e2e/16-ai-models-reindex-connectors-and-broker.spec.ts` dans `tests:` et retrait de `e2e_backlog_story: "21-5"` sur les 13 capacités du Lot A (`verification: docs` maintenu jusqu'à Story 21.8).

### 2.5 Analyse d'Impact sur la Pyramide des Tests (`AD-17`)
- **Couche 1a / 1b / 2 / 3 / 4 / Sécurité** : Aucun code applicatif modifié en `21.5-impl` ; vérification TypeScript (`tsc --noEmit`) sur `apps/web/e2e/support/authAndOrgHelpers.ts`.
- **Couche 5 (E2E Playwright)** : Les 3 specs `14`, `15`, `16` seront implémentées et vérifiées par `21.5-test`, qui complètera ensuite `pnpm site:sync && pnpm site:check` et la Section 3 du présent rapport.

---

## 3. Bilan des Modifications & Résultats (Post-Implémentation)

### 3.1 Fichiers Développés & Modifiés
| Fichier | Nature (Création / Modification / Refactoring) | Description synthétique |
| :--- | :--- | :--- |
| `apps/web/e2e/support/authAndOrgHelpers.ts` | Création + Correction (`21.5-impl` / `21.5-test`) | Helper partagé (`169` lignes) : `getBearerTokenFromSession`, `bootstrapAdminSession`, `loginLocalViaUi`, `logoutViaAccountPopover`, `openSettingsTabViaUi`, `openAccountPopover`, `openUserSettingsTab` (`IDE_MCP_KEYS`), `createOrgUnitViaOrganizationUi` (`org-unit-parent-select-trigger`), `inviteUserViaOrganizationUi`. |
| `apps/web/e2e/14-auth-2fa-account-and-profile.spec.ts` | Création | Spec Playwright (`262` lignes, `@uj UJ-13, UJ-16`) : politique auth/2FA (`TOTP` + enrôlement RFC 6238 / `EMAIL_OTP` / `NONE`), renouvellement mot de passe temporaire, popup Mon Compte 5 onglets, clé IDE/MCP `pat_mcp_*`, `/profile` (4 KPIs), survie `F5` + `SELECT` `platform_auth_settings`, `users`, `user_preferences`, `user_mcp_tokens`, `audit_ledger`. |
| `apps/web/e2e/15-organization-iam-secops-inbox-and-observer.spec.ts` | Création | Spec Playwright (`209` lignes, `@uj UJ-4, UJ-14`) : BU/Équipe + invitation scopée + délégation `BU_LEAD` + gardes `403`, annuaire IAM + matrice des rôles + tiroir SecOps (`role_permission_grants`), mode `READ_ONLY_OBSERVER` (`403 ERR_OBSERVER_MODE_READ_ONLY`), centre de notifications / `/inbox` + `SELECT` `task_notifications`, survie `F5` + `SELECT` `org_units`, `iam_accounts`, `audit_ledger` (`org_unit_id`). |
| `apps/web/e2e/16-ai-models-reindex-connectors-and-broker.spec.ts` | Création | Spec Playwright (`236` lignes, `@uj UJ-7, UJ-15`) : état Jour 0 sans embedding, champs vides, rejet SSRF (`169.254.169.254`), création/test Chat + Embedding `1024` via serveur HTTP local déterministe + réindexation, connecteur socle write-only + Passthrough, parcours Permission Broker (`permission-broker-card` & `permission_broker_tickets`), survie `F5` + `SELECT` PG18. |
| `docs/product/capabilities.yaml` | Modification | Rattachement des specs `14`, `15`, `16` aux `13` capacités du Lot A et retrait de `e2e_backlog_story: "21-5"`. |
| `apps/web/src/generated/orciaSiteManifest.ts` & `docs/site-catalog/index.html` | Régénération | Synchronisés par `pnpm site:sync && pnpm site:check`. |

### 3.2 Résultats Chiffrés, Métriques & Qualité
- **Volumétrie stricte (`< 300` lignes/spec)** : `14` (`262` L), `15` (`209` L), `16` (`236` L), `authAndOrgHelpers.ts` (`169` L).
- **TypeScript strict E2E** (`tsc --noEmit --strict` sur `e2e/*.spec.ts` et `e2e/support/*.ts`) : `0` erreur.
- **Turbo Monorepo** (`pnpm turbo run lint typecheck test`) : `9/9` tâches réussies (`@orcia/web:test` : `38` fichiers, `153` tests passés).
- **Gouvernance Capacités & UJ** :
  - `.venv/bin/pytest tests/unit/test_uj_e2e_coverage_gate.py` : `7 passed` (`0.36s`).
  - `pnpm site:sync && pnpm site:check` : `65/65` capacités live référencent un test, E2E fonctionnels `39/62`, UJ `20/20`, `0` dérive.
- **Sécurité secrets** (`.venv/bin/detect-secrets-hook --baseline .secrets.baseline`) : `0` secret non annoté.
- **Analyse d'impact GitNexus (`gitnexus:detect_changes`, `scope: "all"`)** : `changed_count: 1` (`ORCIA_SITE_MANIFEST`), `affected_count: 0`, `risk_level: "low"`.

### 3.3 Validation & Procédure de Test sur Toute la Pyramide (`AD-17` + 5 Garde-Fous de Câblage Vertical)
- **Couche 1b & Statique (`tsc`, `Vitest`, `Turbo`, `detect-secrets`)** : Validée à `100 %` sans modification du code applicatif.
- **Couche 3 (`site:check` & `test_uj_e2e_coverage_gate.py`)** : En-têtes `@uj`/`@cap`, absence des termes interdits (`epic`/`story`/`ac`/`uj`) dans les libellés `test.describe`/`test`, et couverture complète `CAP ↔ UJ ↔ Spec E2E` validés.
- **Couche 5 (Exécution Playwright complète sur `orcia_e2e`)** : Reportée à la campagne unifiée **Story 21.8**, qui capturera les échecs honnêtes anticipés sur `task_notifications` (service inbox en mémoire) et `permission-broker-card` / `permission_broker_tickets` (non monté dans `FourZoneDirectionCShell` et service broker en mémoire) pour traitement dans l'**Epic 22**.
