# Rapport Tech Lead — Politique d'Authentification Exclusive (`LOCAL` vs `SSO`), Double Facteur Configurable (`NONE | EMAIL_OTP | TOTP`), Visibilité Paramètres `PLATFORM_ADMIN` & Isolation Totale Instance Locale / Tests

- **Référence** : `2026-11-15-politique-authentification-exclusive-2fa-et-isolation-locale`
- **Date** : `2026-11-15`
- **Statut** : `done`
- **Capacité(s)** : `CAP-001` (Auth / `/login`), `CAP-054` (Connecteurs / `SMTP_MAIL`), `CAP-058` (Hub Paramètres `/settings` & onglet `Authentification` réservés `PLATFORM_ADMIN`), `CAP-060`, `CAP-100`
- **Classification** : `feature` + `hygiène` + `ux`

---

## 1. Analyse du Besoin & Étude d'Impact Tech Lead

### 1.1 Constat et Cause Racine
L'audit du flux de connexion (`/login`), des paramètres (`/settings`) et de l'amorçage serveur a mis en évidence 5 dérives structurelles :
1. **Bi-mode figé sur `/login` (`BiModeLoginView`)** : L'écran affiche systématiquement le bouton SSO organisationnel ET l'accordéon de connexion locale, avec le sous-titre générique « Connectez-vous avec le compte unique de votre organisation ou avec votre compte local ».
2. **Auto-connexion SSO factice sur « Marc »** : Le clic sur « Connexion avec le compte de l'organisation (SSO) » dans `apps/web/src/components/LoginScreenView.tsx` envoie en dur `{ oidc_subject: "oidc|marc-lead" }`, servi sans requête SQL par le singleton RAM `AuthAndOrganizationService` (`build_default_auth_and_org_service()` dans `core_and_lifespan.py`), lequel crée 5 personas fictifs (`Karim`, `Claire`, `Marc`, `Nadia`, `Partenaire`) au démarrage du vrai serveur FastAPI. L'absence de propagation de `platform_role` dans `LoginScreenView.tsx` rabat en plus `Marc` (`TEAM_LEAD`) sur le libellé UI `Contributeur`.
3. **Champ « Code de vérification à 6 chiffres » ambigu et non piloté** : Toujours affiché dans l'accordéon local sans explication sur son canal d'obtention (`EMAIL_OTP` vs `TOTP`), ignoré par le chemin PostgreSQL 18 réel (`authenticate_via_postgres18`), et seulement filtré côté client pour `"000000"`.
4. **Organisation et visibilité des Paramètres plateforme** : L'onglet est encore nommé « Connecteurs & SSO », il n'existe pas d'onglet dédié **« Authentification »**, et l'entrée de menu `Configuration` ainsi que `/settings` ne sont pas strictement cloisonnés aux seuls `PLATFORM_ADMIN`.
5. **Risque de pollution de l'instance locale** : Même si les tests d'intégration (`testcontainers`) et Playwright E2E (`e2e_stack.py`, ports `8100`/`3101`) s'exécutent déjà sur une base isolée, le démarrage local standard injecte les personas RAM et expose des scripts de seed (`pnpm db:seed`) sans verrou de confirmation ni invalidation `localStorage` lors d'un `pnpm db:reset`.

### 1.2 Décisions d'Architecture & Règles Métier Cibles
1. **Mode d'authentification exclusif (`LOCAL` ou `SSO`)** :
   - Persisté en PostgreSQL 18 dans la table singleton `platform_auth_settings` (`singleton_key = 'GLOBAL'`, défaut Jour 0 = `auth_mode = 'LOCAL'`, `two_factor_mode = 'NONE'`).
   - `/login` interroge `GET /api/v1/auth/public-config` (anonyme, ne divulgue aucun secret OIDC ni SMTP) et n'affiche **que** le formulaire configuré avec un sous-titre adapté (`FR`/`EN`).
   - Le backend rejette strictement toute tentative sur le mode désactivé (`HTTP 403 ERR_LOCAL_AUTH_DISABLED` ou `ERR_SSO_AUTH_DISABLED`). Un script CLI Break-Glass (`infra/scripts/maintenance/10_reset_auth_mode_local.py`) permet de revenir à `LOCAL + NONE` en cas de mauvaise configuration SSO.
2. **Double facteur configurable sur le mode `LOCAL` (`NONE` | `EMAIL_OTP` | `TOTP`)** :
   - **`NONE`** : authentification en 1 étape (e-mail + mot de passe uniquement, champ 6 chiffres masqué).
   - **`EMAIL_OTP`** : authentification en 2 étapes. À l'étape 1 valide, génération d'un code à 6 chiffres (`secrets.randbelow`), stockage haché (`SHA-256` + sel) dans `auth_login_challenges` (TTL `300s`, max 5 essais) et envoi via un connecteur `enterprise_connectors` actif de type **`SMTP_MAIL`** (`asyncio.to_thread` + `smtplib` sans bloquer l'event loop ASGI). L'étape 2 indique explicitement l'adresse e-mail masquée destinataire et propose le renvoi. Activation bloquée (`HTTP 422 ERR_AUTH_SMTP_CONNECTOR_REQUIRED`) tant qu'aucun connecteur `SMTP_MAIL` actif n'est configuré.
   - **`TOTP`** : authentification en 2 étapes (RFC 6238 via `TotpManager`). Si `users.totp_enabled == FALSE`, l'étape 2 passe en `TOTP_ENROLL` : génération d'un secret éphémère chiffré, affichage du lien `otpauth://` + clé Base32 formatée + bouton de copie + explication du renouvellement toutes les 30 secondes dans l'application d'authentification ; le premier code valide active `users.totp_enabled = TRUE` et enregistre `totp_secret_encrypted` en base. Les connexions suivantes passent en étape `TOTP`.
3. **Réorganisation `/settings` & Cloisonnement strict `PLATFORM_ADMIN`** :
   - Nouvel onglet **`Authentification`** (`?tab=authentication`) portant le sélecteur exclusif `LOCAL` vs `SSO`, le choix 2FA (`NONE | EMAIL_OTP | TOTP`) avec texte explicatif du canal, état/lien vers `Connecteurs` pour `SMTP_MAIL`, formulaire OIDC (`issuer_url`, `client_id`, `client_secret`, `scopes`, `redirect_uri`) protégé par garde-fou SSRF + bouton `Test OIDC` (`discover` via `request.app.state.http_client`).
   - Onglet « Connecteurs & SSO » renommé **`Connecteurs`** (`Connectors`), enrichi du type `SMTP_MAIL` (`smtp://` / `smtps://` autorisés uniquement pour `SMTP_MAIL` avec maintien du blocage SSRF métadonnées/link-local).
   - Le menu `Configuration` dans la barre latérale et l'accès administrateur `/settings` ne sont visibles et accessibles qu'aux détenteurs du rôle effectif `PLATFORM_ADMIN` (avec rejet strict `READ_ONLY_OBSERVER` `HTTP 403`).
4. **Isolation Définitive Runtime Local vs Tests** :
   - `build_default_auth_and_org_service(seed_reference_personas=should_seed_test_personas_in_memory())` : `0` persona fictif injecté en RAM lors du boot FastAPI standard ; personas conservés uniquement sous `PYTEST_CURRENT_TEST` ou `ORCIA_E2E_SEED_FIXTURES=1` / `ORCIA_SEED_TEST_PERSONAS=1`.
   - Suppression définitive du fallback `oidc|marc-lead` et du blocage factice `"000000"` dans `LoginScreenView.tsx`.
   - Renommage `pnpm db:seed` -> `pnpm db:seed:demo` et ajout du verrou `--confirm-demo-seed` sur les CLI de seed démo (sans casser les fonctions Python importées par `test_real_containers.py`).
   - Propagation de `boot_epoch` dans `GET /api/v1/bootstrap/status` et `GET /api/v1/auth/public-config`, réinitialisé par `pnpm db:reset`, afin d'invalider automatiquement les clés `localStorage` obsolètes du navigateur.

### 1.3 Volumétrie & Factorisation Planifiée
- Extraction des routes passthrough hors de `apps/api/src/orcia_api/routers/auth.py` (`321` lignes) vers `_auth_passthrough_routes.py` pour maintenir `auth.py < 260` lignes.
- Création de modules ciblés `< 300` lignes (`auth_policy.py`, `sql_auth_policy_and_challenges.py`, `smtp_otp_delivery.py`, `auth_settings.py`, `LoginTwoFactorStepPanel.tsx`, `PlatformAuthSettingsCard.tsx`, `SettingsAuthenticationSection.tsx`).
- Respect strict des frontières hexagonales `AD-19` (`lint-imports`) : zéro import `_internal` depuis `apps/api`, zéro SDK framework dans `orcia_core/permissions`, zéro import router/api-client dans `packages/ui`.

---

## 2. Plan d'Implémentation

### 2.1 Migrations Alembic (`infra/migrations/versions/`)
- Révision `20261115_1901_platform_auth_policy_and_email_otp.py` (chaînée sur `down_revision = "20261114_1706"`, SQL brut réversible `upgrade`/`downgrade`) :
  - Création de `platform_auth_settings` (contrainte singleton `UNIQUE`, `CHECK auth_mode IN ('LOCAL', 'SSO')`, `CHECK two_factor_mode IN ('NONE', 'EMAIL_OTP', 'TOTP')`, configuration OIDC + secret chiffré, `boot_epoch UUID NOT NULL`) avec insertion idempotente de la ligne `GLOBAL` par défaut (`LOCAL`, `NONE`).
  - Création de `auth_login_challenges` (`id UUID PRIMARY KEY`, `user_id` FK `users` `ON DELETE CASCADE`, `challenge_token_hash CHAR(64) UNIQUE`, `challenge_kind CHECK IN ('EMAIL_OTP', 'TOTP', 'TOTP_ENROLL')`, `otp_code_hash`, `pending_totp_secret_encrypted`, `masked_destination`, `attempts_count`, `max_attempts`, `expires_at`, `consumed_at`, index sur `user_id` et `expires_at`).
  - Altération de la contrainte `CHECK` sur `enterprise_connectors.connector_kind` pour ajouter `'SMTP_MAIL'`.

### 2.2 Noyau Hexagonal & Workers (`packages/orcia-core/`)
- Erreurs métier dans `orcia_core/permissions/errors.py` & `_error_catalog.py` (+ mapping RFC 9457 dans `apps/api/src/orcia_api/errors/registry.py`) : `LocalAuthDisabledByPolicyError` (`403`), `SsoAuthDisabledByPolicyError` (`403`), `SsoConfigurationIncompleteError` (`422`), `SmtpConnectorRequiredForEmailOtpError` (`422`), `InvalidOrExpiredLoginChallengeError` (`401`).
- Extension `enterprise_connectors.py` : ajout du type `SMTP_MAIL` et de `allow_smtp_schemes=True` dans `validate_safe_connector_base_url` tout en conservant le blocage SSRF (`169.254.0.0/16`, `fe80::/10`, `metadata.google.internal`, `100.100.100.200`).
- Nouveau module `orcia_core/permissions/auth_policy.py` : modèles de politique/challenge, validation de cohérence (`SSO` exige `issuer_url` + `client_id` + `redirect_uri` ; `EMAIL_OTP` exige un connecteur `SMTP_MAIL` actif), génération/vérification `EMAIL_OTP` par HMAC/SHA-256 à temps constant, masquage d'e-mail, formatage Base32 & URI `otpauth://`, store `InMemoryPlatformAuthPolicyStore`, réexportés dans `orcia_core/permissions/__init__.py`.
- Nouveaux modules `orcia_core/bootstrap/_internal/sql_auth_policy_and_challenges.py` & `smtp_otp_delivery.py` (réexportés proprement par `orcia_core/bootstrap/__init__.py` pour zéro violation `lint-imports`) : CRUD SQL asynchrone politique auth + challenges atomiques (consommation anti-rejeu) + activation TOTP utilisateur + livraison SMTP non bloquante et sink injectable pour tests.
- `_default_service.py` & maintenance scripts : paramètre `seed_reference_personas`, `09_reset_db_first_boot.py` réinitialisant `platform_auth_settings` et purgeant `auth_login_challenges`, nouveau script `10_reset_auth_mode_local.py`, et verrou `--confirm-demo-seed` sur les scripts de seed démo (`01`, `02`, `03`, `08`).

### 2.3 Backend FastAPI & SDK OpenAPI (`apps/api/`, `packages/api-client/`)
- `core_and_lifespan.py` : injection conditionnelle de `seed_reference_personas=should_seed_test_personas_in_memory()` et `app.state.otp_email_sink = None`.
- `schemas/auth_policy.py`, `schemas/auth_and_org.py`, `schemas/enterprise_connectors.py`, `schemas/bootstrap_accostage.py` + enregistrement dans `scripts/export_openapi.py`.
- `routers/auth_settings.py` (monté dans `main.py`) : `GET /api/v1/settings/authentication`, `PUT /api/v1/settings/authentication`, `POST /api/v1/settings/authentication/test-oidc` réservés strictement à `PLATFORM_ADMIN` (avec rejet `READ_ONLY_OBSERVER`).
- `routers/auth.py` + `_auth_pg_helpers.py` + extraction `_auth_passthrough_routes.py` :
  - `GET /api/v1/auth/public-config` (retourne `auth_mode`, `two_factor_mode`, `oidc_enabled`, `sso_label`, `boot_epoch`, sans secret).
  - `POST /api/v1/auth/login/local` : contrôle `auth_mode == 'LOCAL'`, vérifie mot de passe + selon `two_factor_mode` émet soit les tokens finaux, soit un challenge `EMAIL_OTP` / `TOTP` / `TOTP_ENROLL` (`requires_two_factor = True`, pas d'access_token prématuré).
  - `POST /api/v1/auth/login/verify-2fa` et `POST /api/v1/auth/login/resend-2fa` : validation atomique du challenge, activation `totp_enabled` en cas d'enrôlement initial, journalisation sécurité et émission JWT finale.
  - `GET /api/v1/auth/oidc/authorize` et `POST /api/v1/auth/oidc/callback` + garde `ERR_SSO_AUTH_DISABLED` sur `/login/oidc`.
- Régénération du SDK OpenAPI 3.1 (`scripts/export_openapi.py`) et wrappers typés dans `packages/api-client/src/domains/authAndShell.ts`, `catalogAndPermissions.ts`, `index.ts`.

### 2.4 Interface SPA Direction C & Design System (`packages/ui/`, `apps/web/`)
- `@orcia/ui` (`packages/ui`) :
  - `FourZoneSidebarRail` / `FourZoneDirectionCShell` : prop `hiddenMenuKeys` permettant de masquer complètement `configuration` aux non-`PLATFORM_ADMIN`.
  - `LoginTwoFactorStepPanel` + refonte `BiModeLoginView` : rendu exclusif `LOCAL` ou `SSO` (plus les deux simultanément), sous-titres explicites selon le mode, et étape 2 dédiée `EMAIL_OTP` / `TOTP` / `TOTP_ENROLL` sans jamais bloquer `"000000"` artificiellement ni coder de persona en dur.
  - `PlatformAuthSettingsCard` : carte Direction C pour le choix exclusif `LOCAL | SSO`, le choix 2FA `NONE | EMAIL_OTP | TOTP` avec explication du mode d'envoi/génération, indicateur/lien connecteur `SMTP_MAIL`, configuration OIDC et bouton `Test OIDC`.
- `apps/web` :
  - `settingsRbacResolver.ts` & `shellPresets.ts` & `authSessionStore.ts` & `ShellContainer.tsx` : isolement strict `PLATFORM_ADMIN` pour le menu `configuration`, l'onglet `authentication` et les paramètres de plateforme (non-admins sans menu `Configuration` et sans accès à la bascule de rôle `PLATFORM_ADMIN`).
  - `i18n` FR/EN : nouveau fichier `auth_settings_labels.ts`, renommage `Connecteurs & SSO` -> `Connecteurs`, ajout onglet `Authentification`, nouveaux libellés `/login` par mode.
  - `SettingsAuthenticationSection.tsx`, `routes/settings.tsx` (`?tab=authentication`), `EnterpriseConnectorsSettingsSection.tsx` & `EnterpriseConnectorModal.tsx` (`SMTP_MAIL`, titre « Connecteurs »).
  - `LoginScreenView.tsx` & `platformSetupStorageHelpers.ts` : chargement `/api/v1/auth/public-config`, purge définitive `oidc|marc-lead`, gestion complète du workflow 2 étapes (`EMAIL_OTP`, `TOTP`, `TOTP_ENROLL`), flux OIDC réel, et invalidation automatique du `localStorage` lors d'un changement de `boot_epoch` (`pnpm db:reset`).

### 2.5 Stratégie de Tests (`AD-17` 5 Couches & Sécurité)
- **Couche 1 (Unitaires ≥ 90%)** : `tests/unit/test_platform_auth_policy_2fa_and_runtime_isolation.py` + `apps/web/src/__tests__/platform-auth-modes-2fa-and-settings-f5.test.tsx` + mise à jour `story-17-1-settings-5-tabs-and-rbac.test.tsx` (avec test de survie au `F5` / `unmount` + `render`).
- **Couche 2 (Intégration PostgreSQL 18 `testcontainers`)** : `tests/integration/api/test_platform_auth_modes_2fa_and_local_isolation_postgres18.py` vérifiant persistence SQL `platform_auth_settings`, `auth_login_challenges`, `users.totp_enabled`, blocages `403`/`422`, enrôlement TOTP, flux EMAIL_OTP via sink SMTP, et `0` persona fictif en runtime réel.
- **Couche 3 (Contrat OpenAPI)** : `0-diff` sur `packages/api-client` + `tests/contract/`.
- **Couche 4 & 5 (E2E Playwright & Anti-Régression)** : vérification `01-day0-boot-and-f5-persistence.spec.ts`, `shell.spec.ts`, `11-screens-smoke-without-server-errors.spec.ts`, `zero-dead-buttons-and-silent-catches-audit.test.tsx` et tests de sécurité SSRF / RBAC / Observer / isolation cross-mode dans `tests/security/test_api_security_baseline.py`.

---

## 3. Bilan des Modifications & Résultats

### 3.1 Synthèse des Fichiers Créés & Modifiés
| Couche | Fichiers principaux (tous nouveaux modules `< 400` lignes) | Nature & Objet |
| :--- | :--- | :--- |
| **Migration SQL** | `infra/migrations/versions/20261115_1901_platform_auth_policy_and_email_otp.py` (184 l.) | Création `platform_auth_settings`, `auth_login_challenges` et extension `'SMTP_MAIL'` sur `enterprise_connectors` (`upgrade`/`downgrade` testés) |
| **Noyau & Ports** | `orcia_core/permissions/{auth_policy.py (336), errors.py (253), _error_catalog.py (353), enterprise_connectors.py (363), enterprise_connectors_crypto.py, _default_service.py (217), service.py (332), __init__.py}` | Politique exclusive `LOCAL \| SSO`, règles `NONE \| EMAIL_OTP \| TOTP`, garde SSRF (`smtp://` / `smtps://` restreint à `SMTP_MAIL`), `seed_reference_personas` |
| **Adaptateurs PG18 & SMTP** | `orcia_core/bootstrap/{__init__.py (310), _internal/sql_auth_policy.py (278), _internal/sql_login_challenges.py (242), _internal/smtp_otp_delivery.py (236), _internal/sql_enterprise_connectors.py, _internal/sql_local_auth.py (298)}` | Persistance singleton `platform_auth_settings`, challenges 2FA atomiques avec TTL/anti-rejeu, enrôlement `users.totp_enabled`, envoi SMTP non bloquant |
| **API FastAPI & OpenAPI** | `apps/api/src/orcia_api/{dependencies/core_and_lifespan.py (394), main.py (140), errors/registry.py (202), schemas/auth_policy.py, routers/auth.py (261), routers/auth_settings.py (145), routers/_auth_*.py, routers/enterprise_connectors.py, routers/bootstrap_accostage.py (371)}` + `packages/api-client/` | Endpoints `/auth/public-config`, `/login/local`, `/login/verify-2fa`, `/login/resend-2fa`, `/oidc/*`, `/settings/authentication*`, rejet `403` mode inactif & `PLATFORM_ADMIN` strict, SDK `0-diff` |
| **Design System `@orcia/ui`** | `packages/ui/src/primitives/{BiModeLoginView.tsx (304), LoginTwoFactorStepPanel.tsx (250), PlatformAuthSettingsCard.tsx (388), FourZoneDirectionCShell.tsx (325), FourZoneSidebarRail.tsx (222), UserAccountDropdown*.tsx}` | Rendu exclusif `LOCAL \| SSO`, écran 2FA explicite (`EMAIL_OTP`, `TOTP`, `TOTP_ENROLL`), panneau admin `Authentification`, `hiddenMenuKeys` |
| **SPA `@orcia/web`** | `apps/web/src/{components/LoginScreenView.tsx (285), components/ShellContainer.tsx (351), components/platformSetupStorageHelpers.ts (363), features/admin/auth/SettingsAuthenticationSection.tsx (214), features/admin/connectors/EnterpriseConnectorsSettingsSection.tsx (394), routes/settings.tsx (272), stores/authSessionStore.ts (293), stores/settingsRbacResolver.ts, i18n/locales/auth_settings_labels.ts}` | Suppression `oidc\|marc-lead` et `"000000"`, onglets `Authentification` & `Connecteurs`, masquage `Configuration` hors `PLATFORM_ADMIN`, invalidation `localStorage` sur `boot_epoch` |
| **Maintenance & Gouvernance** | `infra/scripts/maintenance/{01,02,03,08,09,10_reset_auth_mode_local.py (139)}`, `infra/scripts/sync_site_catalog.py`, `package.json`, `docs/product/capabilities.yaml`, `docs/implementation-artifacts/sprint-status.yaml` | Verrou `--confirm-demo-seed` (`pnpm db:seed:demo`), Break-Glass `pnpm db:auth:reset-local`, clôture `SITE-SYNC-PACKS-01` & traçage `DEBT-ORCH-VOCAB-01` |

### 3.2 Métriques de Couverture & Validation des 5 Couches `AD-17` + Sécurité
- **Qualité Statique & Frontières Architecturales** :
  - `.venv/bin/ruff format --check` (`503` fichiers formatés) & `.venv/bin/ruff check` : `All checks passed!`.
  - `.venv/bin/mypy --strict` (`341` fichiers source) : `Success: no issues found`.
  - `.venv/bin/lint-imports` : `Contracts: 5 kept, 0 broken`.
  - `lint_spine.py` : `{"ok": true, "total_findings": 0}` ; `scripts/export_openapi.py --check` : exit `0` (`0-diff`).
- **Couche 1 — Unitaires Python & TypeScript** :
  - **Couverture unitaire ciblée nouveaux modules auth/SMTP** : **`94.92%`** (`smtp_otp_delivery.py` `96%`, `sql_auth_policy.py` `97%`, `sql_login_challenges.py` `100%`, `auth_policy.py` `92%`, `10 passed`).
  - **Suite `tests/unit/`** : verte sur l'ensemble du périmètre hors **2 échecs préexistants hors scope** tracés dans `sprint-status.yaml` sous **`DEBT-ORCH-VOCAB-01`** (`test_story_3_2e_sdlc_pack_and_connectors.py:56` et `test_story_3_2f_step_executors_invoker_and_finance.py:93`, liés à des chaînes historiquement figées dans `packages/api-client/openapi.json` non modifiées). Résolution confirmée de `SITE-SYNC-PACKS-01` (`installedPacksCount: 2`).
  - **Vitest (`pnpm turbo run lint typecheck test`)** : `9/9` tâches vertes — `@orcia/ui` (`21` fichiers, `91` tests), `@orcia/api-client` (`1` fichier, `8` tests), `@orcia/web` (`17` fichiers, `90` tests dont `platform-auth-modes-2fa-and-settings-f5.test.tsx` avec test de survie au `F5` `unmount/render` et `zero-dead-buttons-and-silent-catches-audit.test.tsx`).
- **Couche 2 — Intégration Verticale PostgreSQL 18 (`testcontainers`)** :
  - `test_platform_auth_modes_2fa_and_local_isolation_postgres18.py`, `test_story_17_4_connectors_passthrough_and_rag_referent_postgres18.py`, `test_local_auth_logout_and_temp_password_postgres18.py`, `tests/integration/` — vérifications `HTTP -> SQL SELECT` et isolation runtime (`0` persona fictif hors `pytest`). **Couverture combinée unitaires + intégration PG18 : `90.07%`** (`--cov-fail-under=90` validé) ; puis relance dédiée `101 passed` (`test_story_17_4*` + `tests/security/`).
- **Couche 3 (Contrats OpenAPI 3.1) & Couche 4 (Évaluations / Sécurité)** :
  - `tests/contract/` (`2 passed`), `tests/evals/` & `tests/security/` (blocage `HTTP 403` mode désactivé, `PLATFORM_ADMIN` exclusif, anti-SSRF `SMTP_MAIL`/OIDC, `0` régression).
- **Couche 5 — E2E Navigateur Playwright & Vérité Terrain Jour 0** :
  - `pnpm --filter @orcia/web exec playwright test e2e/01-day0-boot-and-f5-persistence.spec.ts e2e/shell.spec.ts` (instance éphémère isolée `e2e_stack.py` `:8100`/`:3101`) : **`11 passed, 1 skipped`** (skip mobile standard sur raccourci clavier bureau `[`), prouvant le masquage strict de `Configuration` tant qu'aucun `PLATFORM_ADMIN` n'est connecté puis son affichage après création admin.
  - `pnpm db:reset` : `cleared_tables=60, remaining_users=0` (état Jour 0 `LOCAL + NONE` restauré) ; `10_reset_auth_mode_local.py --dry-run` validé.

### 3.3 Audit GitNexus (`impact` & `detect_changes`), Capacités & Catalogue (`/showcase`)
- **Indexation (`npx gitnexus analyze`)** : `25 275` nœuds, `43 886` arêtes, `384` clusters, `1 276` flux (ciblé explicitement sur le dépôt `ORCIA`).
- **`detect_changes(scope="all")`** : `changed_count: 196`, `affected_count: 726`, `changed_files: 66`.
- **Audit anti-orphelin (`impact` upstream + vérification d'appelants)** :
  - `resolve_auth_policy_runtime` : `impactedCount: 10` (`CRITICAL`, `10` routes directes `auth.py`, `auth_settings.py`, `bootstrap_accostage.py`) ; `validate_platform_auth_policy_update` : `impactedCount: 3`.
  - L'outil `impact` de GitNexus ne traversant pas les réexports Python via `orcia_core/bootstrap/__init__.py` (comportement vérifié à l'identique sur les adaptateurs historiques `list_enterprise_connectors_from_postgres18`), un contrôle `grep` et l'exécution PG18 confirment qu'aucun des nouveaux adaptateurs `_internal` n'est orphelin : `load_platform_auth_policy_from_postgres18` (`_auth_policy_runtime.py:93`), `update_platform_auth_policy_on_postgres18` (`auth_settings.py:72`), `create_login_second_factor_challenge_on_postgres18` (`_auth_2fa_helpers.py:137,171,189`) et `send_login_email_otp` (`_auth_2fa_helpers.py:145,321`).
- **Registre & Site** : `CAP-001`, `CAP-054`, `CAP-058`, `CAP-060`, `CAP-100` mis à jour dans `docs/product/capabilities.yaml` ; rapport indexé dans `README.md` ; `pnpm site:sync && pnpm site:check` exécuté avec succès (exit `0`).
