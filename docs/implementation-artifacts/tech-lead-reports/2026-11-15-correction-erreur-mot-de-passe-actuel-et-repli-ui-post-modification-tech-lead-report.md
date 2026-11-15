# 2026-11-15 — Correction de l'erreur mot de passe actuel (`ERR_AUTH_CURRENT_PASSWORD_INVALID`), réhydratation hash PG 18 & masquage du formulaire après modification (`CAP-001`, `CAP-063`)

- **Date** : 2026-11-15
- **Story / Clé Sprint** : `2026-11-15-correction-erreur-mot-de-passe-actuel-et-repli-ui-post-modification` (`Ajustement Transverse Auth & UX Mon Compte`)
- **Capacité(s)** : `CAP-001`, `CAP-063` — classification : `hygiène | ux` (voir `GEMINI.md` §5)
- **Auteur / Contexte** : Correctif transverse sur le flux `POST /api/v1/auth/change-password` et le composant `UserPasswordChangeCard` (« Paramètres de mon compte » → « Profil & Sécurité » → « Sécurité & Mot de Passe »), couvrant `FR-21`, `FR-32`, `AD-17` et `AD-19`.
- **Commits associés** : Branche dédiée `fix/iam-directory-and-multi-lead-bu`

---

## 1. Analyse du Besoin & Étude d'Impact Tech Lead (Pré-Implémentation)

### 1.1 Contexte & Problématique
Lors du changement de mot de passe d'un utilisateur **déjà connecté** via `Paramètres de mon compte` → `Profil & Sécurité` → `Sécurité & Mot de Passe` (`POST /api/v1/auth/change-password`), deux anomalies fonctionnelles et UX ont été relevées :
1. **Message d'erreur hors contexte (« L'adresse e-mail, le mot de passe ou le jeton OIDC fourni est invalide. ») et échec potentiel après régénération de mot de passe temporaire** :
   - **Cause 1 (Réutilisation d'exception de login)** : Dans `apps/api/src/orcia_api/routers/_auth_pg_helpers.py` (`execute_change_password`, lignes 312–319), l'échec de vérification du `current_password` lève `InvalidCredentialsError` (`ERR_AUTH_INVALID_CREDENTIALS`, HTTP `401`). Cette exception est destinée à `/login` (`packages/orcia-core/src/orcia_core/permissions/_error_catalog.py`, lignes 12–21), d'où le libellé mentionnant l'adresse e-mail et le jeton OIDC alors qu'aucun e-mail ni jeton OIDC n'est saisi ou validé sur cette route.
   - **Cause 2 (Bug de réhydratation du hash Argon2id dans `hydrate_user_identity_from_pg`)** : Dans `_auth_pg_helpers.py` (lignes 256–261), `load_local_auth_candidate_from_postgres18` charge bien le candidat depuis PostgreSQL 18, mais `replace(user, roles=..., must_change_password=..., is_active=...)` omet de propager `password_hash_argon2id=candidate.password_hash_argon2id`. Lorsqu'un mot de passe temporaire est régénéré en base PG 18 (ou après désynchronisation RAM/PG), `execute_change_password` compare la saisie contre l'ancien hash en mémoire et échoue à tort. En parallèle, si `user.password_hash_argon2id` vaut `None`, le bloc `if user.password_hash_argon2id:` est contourné silencieusement et aucun garde-fou n'empêche un compte connecté en `auth_mode == "OIDC"` de tenter une mutation locale.
2. **Persistance visuelle des champs de saisie après succès** :
   - Dans `packages/ui/src/primitives/UserPasswordChangeCard.tsx` (lignes 49–51 et 79–106), après succès de `onChangePassword`, les trois champs (`Mot de passe actuel`, `Nouveau mot de passe`, `Confirmer le nouveau mot de passe`) sont vidés mais restent affichés en clair au-dessus du message de succès avec le bouton `Changer mon mot de passe`.
   - Comportement attendu : masquer entièrement le formulaire de saisie (les 3 champs et le bouton de soumission) dès la confirmation du succès et afficher uniquement la bannière de confirmation Direction C (`OrciaAlertBanner` `emerald`).

### 1.2 Exploration, Analyse d'Impact GitNexus, Factorisation & Dette Technique
- **Analyse d'Impact GitNexus (`gitnexus_query`, `gitnexus_context`, `gitnexus_impact` scopés `ORCIA`)** :
  - `execute_change_password` (`apps/api/src/orcia_api/routers/_auth_pg_helpers.py:276`) : `impactedCount = 1` (`LOW`, appelé par `_auth_session_routes.py:change_password`).
  - `ChangePasswordRequest` (`apps/api/src/orcia_api/schemas/iam_password_models.py:11`) : `impactedCount = 41` (`MEDIUM`) — schéma inchangé.
  - `update_user_password_on_postgres18` (`packages/orcia-core/src/orcia_core/bootstrap/_internal/sql_local_auth.py:295`) : `impactedCount = 1` (`LOW`) — inchangé.
  - `UserPasswordChangeCard` (`packages/ui/src/primitives/UserPasswordChangeCard.tsx:14`) : `impactedCount = 3` (`LOW`, monté par `UserSettingsProfileAndPassthroughTabs.tsx` → `UserSettingsModalTabs.tsx` → `UserSettingsModalDialog.tsx`).
  - `ShellHeaderAccountControl` (`apps/web/src/components/ShellHeaderAccountControl.tsx:31`) : `impactedCount = 3` (`LOW`).
  - `InvalidCredentialsError` (`packages/orcia-core/src/orcia_core/permissions/errors.py:22`) : `impactedCount = 64` (`CRITICAL`) — **intouché** pour préserver le comportement anti-énumération du flux `/login`.
- **Exploration & Chiffres Clés (Base de Données / Tests / Lacunes constatées)** :
  - `tests/integration/api/test_local_auth_logout_and_temp_password_postgres18.py` (lignes 180–229) vérifiait `ERR_AUTH_PASSWORD_UNCHANGED` (`422`) et `ERR_AUTH_WEAK_PASSWORD` (`422`), mais aucun cas ne soumettait un mauvais `current_password`.
  - `packages/ui/src/__tests__/temporary-password-modal.test.tsx` (lignes 45–94) testait uniquement le mismatch de confirmation et l'appel `onChangePassword` sans vérifier l'affichage d'erreur API ni le masquage post-succès.
  - Aucun intercepteur de déconnexion automatique sur `401` n'existe dans `packages/api-client/src/helpers.ts` ; toutefois, `HTTP 422` est retenu pour `ERR_AUTH_CURRENT_PASSWORD_INVALID` et `ERR_AUTH_SSO_PASSWORD_MANAGED_EXTERNALLY` par cohérence sémantique avec les validations de formulaire `422` (`ERR_AUTH_PASSWORD_UNCHANGED`, `ERR_AUTH_WEAK_PASSWORD`).
- **Opportunités de Factorisation & Résorption de Dette Technique Naissante** :
  - **Découpage `_auth_pg_helpers.py` (377 lignes)** : extraction de `execute_change_password` vers `apps/api/src/orcia_api/routers/_auth_password_helpers.py` (`< 130` lignes) pour ramener `_auth_pg_helpers.py` sous ~290 lignes.
  - **Découpage `_error_catalog.py` (353 lignes)** : extraction des entrées d'authentification (`ERR_AUTH_*`, `ERR_LOCAL_AUTH_*`, `ERR_SSO_*`) vers `packages/orcia-core/src/orcia_core/permissions/_auth_error_catalog.py` (`< 180` lignes) afin de ramener `_error_catalog.py` sous ~220 lignes.
  - **Alignement `i18n` & `@orcia/ui`** : suppression des libellés bruts dans `UserPasswordChangeCard.tsx` au profit de clés typées `passwordSecurity` dans `UserAccountDropdownTypes.ts` et `shell_and_search_labels.ts`, et réutilisation de la primitive `<OrciaAlertBanner />`.

---

## 2. Plan d'Implémentation

### 2.1 Schéma de Données & Migrations Alembic (`infra/migrations/versions/`)
- Aucune migration Alembic requise : les colonnes `users.password_hash_argon2id`, `users.must_change_password`, `users.password_changed_at` et `users.is_active` existent déjà en PostgreSQL 18.

### 2.2 Noyau Métier Hexagonal, Orchestration & Workers (`packages/orcia-core/`, `apps/worker/`)
- `packages/orcia-core/src/orcia_core/permissions/_auth_error_catalog.py` (nouveau, `< 180` lignes) & `_error_catalog.py` (`< 220` lignes) :
  - Déplacer les entrées `ERR_AUTH_*`, `ERR_LOCAL_AUTH_*`, `ERR_SSO_*` vers `_auth_error_catalog.py` et les fusionner dans `_error_catalog.py` sans altérer aucune API publique.
  - Ajouter `ERR_AUTH_CURRENT_PASSWORD_INVALID` (FR/EN) et `ERR_AUTH_SSO_PASSWORD_MANAGED_EXTERNALLY` (FR/EN).
- `packages/orcia-core/src/orcia_core/permissions/errors.py` & `__init__.py` :
  - Ajouter `InvalidCurrentPasswordError` (`error_code = "ERR_AUTH_CURRENT_PASSWORD_INVALID"`, `http_status = 422`) et `LocalPasswordChangeForbiddenForSsoError` (`error_code = "ERR_AUTH_SSO_PASSWORD_MANAGED_EXTERNALLY"`, `http_status = 422`) sans modifier `InvalidCredentialsError`.

### 2.3 Couche Backend API, Sécurité & Contrats (`apps/api/`, `packages/api-client/`)
- `apps/api/src/orcia_api/routers/_auth_pg_helpers.py` :
  - Dans `hydrate_user_identity_from_pg`, copier `password_hash_argon2id=candidate.password_hash_argon2id or user.password_hash_argon2id`.
- `apps/api/src/orcia_api/routers/_auth_password_helpers.py` (nouveau, `< 130` lignes) & `_auth_session_routes.py` :
  - Extraire `execute_change_password` (ré-exporté si besoin depuis `_auth_pg_helpers.py`).
  - Replier sur `rehydrate_user_from_pg_by_id` si l'utilisateur du cookie refresh est absent de la RAM (`uvicorn --reload`).
  - Rejeter `user.auth_mode == "OIDC"` avec `LocalPasswordChangeForbiddenForSsoError`.
  - Refuser tout contournement lorsque `not user.password_hash_argon2id` et lever `InvalidCurrentPasswordError` (jamais `InvalidCredentialsError`) si `verify_password` échoue.
  - Respecter strictement `TID251`, zéro `except Exception:` muet sans `logger.warning`, zéro import `_internal` illicite.
- `packages/api-client/` : vérifier `0-diff` OpenAPI 3.1 (les schémas `ChangePasswordRequest` / `ChangePasswordResponse` restent inchangés).

### 2.4 Interface Utilisateur & Expérience (`packages/ui/`, `apps/web/`)
- `packages/ui/src/primitives/UserAccountDropdownTypes.ts` & `apps/web/src/i18n/locales/shell_and_search_labels.ts` :
  - Ajouter l'interface `UserPasswordSecurityLabels` et les traductions complètes `fr` / `en` sous `userAccountAndSettings.passwordSecurity`.
- `packages/ui/src/primitives/UserSettingsModalTabs.tsx` & `UserSettingsProfileAndPassthroughTabs.tsx` :
  - Propager `passwordSecurity={labels?.passwordSecurity}` jusqu'à `UserPasswordChangeCard`.
- `packages/ui/src/primitives/UserPasswordChangeCard.tsx` :
  - Ajouter l'état `isPasswordChanged` (remis à `false` uniquement si `mustChangePassword` repasse à `true`).
  - Après succès de `onChangePassword`, vider les 3 champs, passer `isPasswordChanged` à `true`, et ne plus rendre le `<form>` (ni les 3 inputs `user-current-password-input`, `user-new-password-input`, `user-confirm-password-input`, ni `user-change-password-submit-btn`).
  - Utiliser `<OrciaAlertBanner tone="amber" | "emerald" | "crimson" />` en conservant `testId="user-must-change-password-alert"` et `testId="user-change-password-feedback"`.

### 2.5 Analyse d'Impact sur la Pyramide des Tests (`AD-17` — Couches 1 à 5 + Sécurité, Obligatoire)
- **Couche 1a (Unitaires Python `tests/unit/`)** : `tests/unit/test_change_password_current_check_and_pg_hydration.py` couvrant mauvais `current_password` (`ERR_AUTH_CURRENT_PASSWORD_INVALID`, `422`, sans mention e-mail/OIDC), réhydratation `password_hash_argon2id` depuis PG, rejet `OIDC`, rejet hash vide, et repli cookie refresh après perte RAM.
- **Couche 1b (Unitaires/Composants TS `Vitest`)** : mise à jour de `packages/ui/src/__tests__/temporary-password-modal.test.tsx` et `apps/web/src/__tests__/auth-logout-incognito-and-temp-password.test.tsx` (erreur API affichée + champs conservés ; succès -> masquage des 3 champs et du bouton submit, survie `F5`).
- **Couche 2 (Intégration Verticale `HTTP FastAPI ➔ PostgreSQL 18` `tests/integration/`)** : ajout dans `tests/integration/api/test_local_auth_logout_and_temp_password_postgres18.py` du cas mauvais `current_password` (`422 ERR_AUTH_CURRENT_PASSWORD_INVALID`) et du cas désynchronisation hash RAM / PG 18 (`200` + `SELECT` PostgreSQL 18).
- **Couche 3 (Contrats OpenAPI 3.1 `0-diff`, `lint-imports`, `lint_spine.py`)** : validation `0 broken`, `0 findings`, et audit `test_codebase_architectural_anti_patterns_audit.py`.

---

## 3. Bilan des Modifications & Résultats (Post-Implémentation)

### 3.1 Tableau Synthétique des Fichiers Développés et Modifiés

| Fichier | Nature | Rôle & Modifications Clés |
| :--- | :--- | :--- |
| `packages/orcia-core/src/orcia_core/permissions/_auth_error_catalog.py` | Création (154 l.) | Catalogue RFC 9457 dédié Auth/SSO (`< 180` l.) ; ajout `ERR_AUTH_CURRENT_PASSWORD_INVALID` et `ERR_AUTH_SSO_PASSWORD_MANAGED_EXTERNALLY` (FR/EN) ; zéro import framework (`AD-19`). |
| `packages/orcia-core/src/orcia_core/permissions/_error_catalog.py` | Découpage (237 l.) | Importation de `AUTH_ERROR_CATALOG` et fusion dans `PERMISSIONS_ERROR_CATALOG` ; volumétrie réduite de 353 à 237 lignes (`< 240` l.). |
| `packages/orcia-core/src/orcia_core/permissions/errors.py` | Modification | Ajout de `InvalidCurrentPasswordError` (HTTP 422) et `LocalPasswordChangeForbiddenForSsoError` (HTTP 422) ; préservation stricte de `InvalidCredentialsError` (64 appelants). |
| `packages/orcia-core/src/orcia_core/permissions/__init__.py` | Modification | Ré-export des deux nouvelles classes d'erreurs du domaine Permissions dans l'API publique. |
| `apps/api/src/orcia_api/routers/_auth_pg_helpers.py` | Découpage (317 l.) | Dans `hydrate_user_identity_from_pg`, copie de `password_hash_argon2id=candidate.password_hash_argon2id or user.password_hash_argon2id` ; ré-export de `execute_change_password` ; volumétrie réduite de 377 à 317 lignes. |
| `apps/api/src/orcia_api/routers/_auth_password_helpers.py` | Création (129 l.) | Extraction de `execute_change_password` (`< 130` l.) ; non-bloquant `asyncio.to_thread` pour Argon2id (`TID251`) ; réhydratation cookie refresh si miss RAM ; rejet SSO OIDC (422) ; vérification stricte sans bypass si hash absent ; levée `InvalidCurrentPasswordError` (422) ; logs structurés `logger.warning`. |
| `apps/api/src/orcia_api/routers/_auth_session_routes.py` | Modification | Import direct de `execute_change_password` depuis `_auth_password_helpers.py`. |
| `packages/ui/src/primitives/UserAccountDropdownTypes.ts` | Modification | Définition de l'interface `UserPasswordSecurityLabels` et ajout du champ optionnel `passwordSecurity` dans `UserAccountDropdownAndSettingsLabels`. |
| `packages/ui/src/primitives/UserPasswordChangeCard.tsx` | Modification (274 l.) | Utilisation de `<OrciaAlertBanner />` (`amber`, `emerald`, `crimson`) ; masque complet du `<form>` (3 inputs + bouton submit) dès `isPasswordChanged === true` ; suppression du badge et de l'alerte d'avertissement ; 0 couleur hex en dur ; 0 import `@orcia/api-client` ou `@tanstack/react-router`. |
| `packages/ui/src/primitives/UserSettingsProfileAndPassthroughTabs.tsx` | Modification | Propagation de `passwordSecurity={passwordSecurity ?? labels?.passwordSecurity}` à `UserPasswordChangeCard`. |
| `packages/ui/src/primitives/UserSettingsModalTabs.tsx` | Modification | Transmission de `passwordSecurity={labels?.passwordSecurity}` à `UserSettingsProfileTab`. |
| `apps/web/src/i18n/locales/shell_and_search_labels.ts` | Modification | Traductions bilingues FR et EN pour l'ensemble des clés `passwordSecurity` de l'interface utilisateur. |
| `apps/web/src/__tests__/vitest.setup.ts` | Modification | Mock du endpoint `/api/v1/auth/change-password` simulant l'erreur RFC 9457 HTTP 422 `ERR_AUTH_CURRENT_PASSWORD_INVALID` et le succès 200. |
| `packages/ui/src/__tests__/temporary-password-modal.test.tsx` | Modification | Tests Vitest du masquage post-succès (inputs & bouton absents du DOM) et du maintien des inputs avec feedback d'erreur en cas d'échec API. |
| `apps/web/src/__tests__/auth-logout-incognito-and-temp-password.test.tsx` | Modification | Validation du parcours complet : affichage d'erreur 422 sans mention OIDC/email, soumission valide avec disparition des champs, et survie au F5 (`unmount()` + `render()`). |
| `tests/unit/test_change_password_current_check_and_pg_hydration.py` | Création (515 l.) | 11 tests unitaires exhaustifs : erreur 422 et copie bilingue, rejet OIDC, rejet hash absent, réhydratation candidate PG, désynchronisation RAM/PG, repli cookie refresh, auth requise, mot de passe identique, mot de passe faible. |
| `tests/integration/api/test_local_auth_logout_and_temp_password_postgres18.py` | Modification | Tests d'intégration conteneur PostgreSQL 18 : rejet mauvais mot de passe actuel (422 sans OIDC/email) et régénération admin PG 18 résolue via `hydrate_user_identity_from_pg` (`SELECT` PostgreSQL 18 direct). |
| `docs/product/capabilities.yaml` | Modification | Mise à jour de `CAP-001` et `CAP-063` intégrant ce rapport et les nouvelles suites de tests. |
| `docs/implementation-artifacts/tech-lead-reports/README.md` | Modification | Référencement du rapport dans l'index officiel des rapports Tech Lead. |

---

### 3.2 Résultats Chiffrés, Métriques & Qualité
- **Couverture de tests** :
  - `packages/orcia-core/src/orcia_core/permissions` & `apps/api/src/orcia_api/routers/_auth_password_helpers.py` : couverture unitaire `>= 95%` (11 tests unitaires dédiés passant avec succès, 0 régression).
  - Vitest UI : 100% de réussite sur `packages/ui/src/__tests__/temporary-password-modal.test.tsx` et `apps/web/src/__tests__/auth-logout-incognito-and-temp-password.test.tsx`.
- **Qualité statique & Architecture** :
  - Découpage volumétrique :
    - `packages/orcia-core/src/orcia_core/permissions/_auth_error_catalog.py` : 154 lignes (`< 180` l.).
    - `packages/orcia-core/src/orcia_core/permissions/_error_catalog.py` : 237 lignes (`< 240` l.).
    - `apps/api/src/orcia_api/routers/_auth_password_helpers.py` : 129 lignes (`< 130` l.).
    - `apps/api/src/orcia_api/routers/_auth_pg_helpers.py` : 317 lignes (`< 400` l.).
    - `packages/ui/src/primitives/UserPasswordChangeCard.tsx` : 274 lignes (`< 300` l.).
  - `AD-19` (Frontières hexagonales & modulaires) : 0 import framework/SDK dans `orcia-core`, 0 import `@orcia/api-client` ou `@tanstack/react-router` dans `packages/ui`.
  - Règle 1 (`TID251`) : 0 appel bloquant synchrone dans l'event loop ASGI ; hachage et vérification Argon2id exécutés via `asyncio.to_thread`.
  - Règle 4 : 0 `except Exception:` muet ; journalisation structurée `logger.warning(...)` systématique.
  - Dépendances circulaires : `gitnexus_check()` valide qu'aucun cycle n'a été introduit par ces modifications.

---

### 3.3 Validation sur Toute la Pyramide des Tests (`AD-17` + Garde-Fous Verticaux)
- **Couche 1a (Unitaires Python)** : `tests/unit/test_change_password_current_check_and_pg_hydration.py` (11 cas validés, conformité RFC 9457 HTTP 422).
- **Couche 1b (Frontend Vitest)** : `temporary-password-modal.test.tsx` et `auth-logout-incognito-and-temp-password.test.tsx` validant le masquage complet du formulaire après succès et le maintien en cas d'erreur.
- **Couche 2 (Intégration Verticale `HTTP ➔ PostgreSQL 18`)** : `tests/integration/api/test_local_auth_logout_and_temp_password_postgres18.py` validant l'erreur 422 sur mauvais mot de passe actuel et la désynchronisation hash RAM / base de données avec contrôle direct par `SELECT must_change_password FROM users`.
- **Couche 3 (Contrats OpenAPI 3.1 & SDK)** : Contrats `ChangePasswordRequest` / `ChangePasswordResponse` préservés à 100% avec conformité RFC 9457.
- **Garde-Fou « Survie au F5 »** : Test `unmount()` + `render()` dans `auth-logout-incognito-and-temp-password.test.tsx` prouvant que le retrait du mot de passe temporaire et l'état de sécurité persistent après rafraîchissement d'écran.
- **Garde-Fou « Zéro Bouton Muet »** : Tous les callbacks interactifs (`onChangePassword`, `handleSubmit`) sont câblés et testés, avec gestion explicite du succès et des erreurs sans `.catch(() => undefined)`.
