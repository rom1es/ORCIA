# Rapport Tech Lead — Correction Erreur Ouverture `/login` (`ERR_RESOURCE_NOT_FOUND`), Suppression Bruit `401 /api/v1/auth/refresh` & Durcissement Gardes E2E (`4xx`/`5xx`/Alertes)

- **Référence** : `2026-11-15-correction-erreur-ouverture-login-session-anonyme-et-gardes-e2e`
- **Date** : `2026-11-15`
- **Statut** : `done` (Sections 1, 2 et 3 complétées ; validations backend, TypeScript/Vitest, Playwright E2E, GitNexus et démon `:8000` vérifiées)
- **Capacité(s)** : `CAP-001` (Auth / `/login` & session), `CAP-058` (Coquille / E2E smoke)
- **Classification** : `hygiène` + `ux`

---

## 1. Analyse du Besoin & Étude d'Impact Tech Lead

### 1.1 Constat et Causes Racines
1. **Ouverture immédiate de `/login` sur une bannière d'erreur rouge `Impossible de vous connecter · ERR_RESOURCE_NOT_FOUND`** :
   - **Démon `uvicorn` local obsolète (`PID 9355` sur `:8000`)** : `scripts/manage.py` lançait `uvicorn` sans `--reload` et sans contrôle `alembic upgrade head`. Après ajout de `GET /api/v1/auth/public-config`, Vite (`:3100`) servait le nouveau code frontend pendant que `:8000` répondait `404` -> `ERR_RESOURCE_NOT_FOUND` (confirmé dans `.orcia-run/api.log`).
   - **Confusion d'état UI au montage (`apps/web/src/components/LoginScreenView.tsx:L108-127`)** : le `catch` de l'appel technique `getPublicAuthConfig()` appelait `setLoginError(toProblemError(err))`, affichant la bannière « Impossible de vous connecter » avant toute saisie utilisateur.
   - **Risque `/api/api/v1/...` dans `resolveWebApiBaseUrl()` (`apps/web/src/stores/authSessionStore.ts:L41-48`)** : un éventuel `VITE_ORCIA_API_BASE_URL=/api` concaténé avec des chemins déjà préfixés `/api/v1/...` produirait également un `404 ERR_RESOURCE_NOT_FOUND`.
2. **Alerte serveur `[WebServer] {"error_code": "ERR_AUTH_INVALID_CREDENTIALS", "status": 401, "path": "/api/v1/auth/refresh"}` dans les logs E2E** :
   - Au chargement initial anonyme (sans cookie HttpOnly `orcia_refresh_token`), `hydrateSession()` (`authSessionStore.ts:L225`) invoquait directement `POST /api/v1/auth/refresh`, provoquant systématiquement un `HTTP 401` journalisé en `warning` (`api.problem_details`) par `trace_and_error.py`, alors qu'en tests Vitest ce routeur était mocké en `HTTP 200`.
3. **Pourquoi les tests E2E Playwright n'ont pas bloqué ces erreurs** :
   - Aucun des 13 fichiers `apps/web/e2e/*.spec.ts` ne visitait `/login` (`11-screens-smoke-without-server-errors.spec.ts` ne testait que 7 routes déjà authentifiées).
   - `watchApiServerErrors` (`apps/web/e2e/support/apiErrors.ts:L7`) ne filtrait que `res.status() >= 500`, ignorant tous les `4xx` (`401`, `403`, `404`, `422`), et aucune assertion globale ne vérifiait l'absence de `pageerror` ou de `[role="alert"]` d'erreur sur ouverture de page.
4. **Course critique de redirection `/login` pendant l'hydratation sur lien profond (`ShellContainer.tsx` + `firstAdmin.ts`)** :
   - Lors de la mise à feu du smoke test E2E sur `/cockpit` après création de l'admin Jour 0, `ShellContainer.tsx` déclenchait `dispatchNavigation("/login")` dans `useEffect` dès que `platformAdmin` était présent en cache `localStorage` et `isAuthenticated === false`, **sans attendre** `!isHydrating && !(isInitialLoading && !isAuthenticated)`. Parallèlement, `createFirstAdminViaUi` rendait la main avant le retour HTTP `200` (`Set-Cookie: orcia_refresh_token`) de `POST /api/v1/bootstrap/welcome-setup/first-admin`.

### 1.2 Volumétrie & Décisions d'Architecture
- Conserver `POST /api/v1/auth/refresh` en `401` strict pour les renouvellements explicites, et exposer **`GET /api/v1/auth/session`** (`AuthSessionBootstrapResponse`, `200 OK`) pour l'amorçage silencieux du navigateur (retournant `{ authenticated: false, session: null }` et nettoyant un éventuel cookie obsolète post-`db:reset`).
- Isoler `LoginScreenView.tsx` pour que `getPublicAuthConfig()` utilise un repli sûr `LOCAL` (`console.warn`) sans déclencher `setLoginError`, tout en gardant `setLoginError` exclusif aux soumissions utilisateur.
- Normaliser `resolveWebApiBaseUrl()` contre un suffixe `/api` redondant.
- Activer un watcher E2E strict sur **`status >= 400` (`4xx` + `5xx`) + `pageerror` + bannières UI `[role="alert"]`** dans `shell.spec.ts` et `11-screens-smoke-without-server-errors.spec.ts` (en y ajoutant `/login`), puis activer `--reload` + `alembic upgrade head` dans `scripts/manage.py` et redémarrer l'instance locale `:8000`.
- Respect strict des seuils `< 400` lignes sur les modules modifiés (`auth_policy.py`, `_auth_session_routes.py`, `authAndShell.ts`, `authSessionStore.ts`, `LoginScreenView.tsx`, `apiErrors.ts`, `11-screens-smoke-without-server-errors.spec.ts`, `shell.spec.ts`).

---

## 2. Plan d'Implémentation

### 2.1 Migrations Alembic
- Aucune nouvelle table requise (`20261115_1901_platform_auth_policy_and_email_otp.py` existante) ; vérification et application de `alembic upgrade head` sur la base PostgreSQL locale.

### 2.2 Noyau Hexagonal & Runtime Local
- Aucun changement de domaine métier ; ajout de `--reload` (`--reload-dir`) et pré-check `alembic upgrade head` dans `scripts/manage.py` (`start_component("api")`, désactivable via `ORCIA_API_NO_RELOAD=1`) puis redémarrage de l'API sur `:8000`.

### 2.3 Backend FastAPI & SDK OpenAPI (`apps/api/`, `packages/api-client/`)
- `apps/api/src/orcia_api/schemas/auth_policy.py` : ajout de `AuthSessionBootstrapResponse` (`authenticated`, `session`, `trace_id`).
- `apps/api/src/orcia_api/routers/_auth_session_routes.py` : extraction d'un helper partagé de rotation refresh et ajout de `GET /api/v1/auth/session` (réponse `200 { authenticated: false, session: null }` sans cookie ni bruit `401` ; nettoyage de cookie périmé si `InvalidCredentialsError`).
- `packages/api-client/` : régénération OpenAPI 3.1 (`0-diff`) + méthode `getSessionBootstrap()` dans `src/domains/authAndShell.ts`.

### 2.4 Interface SPA Direction C (`apps/web/`)
- `apps/web/src/stores/authSessionStore.ts` : suppression d'un suffixe `/api` redondant dans `resolveWebApiBaseUrl()` et bascule de `hydrateSession()` sur `client.getSessionBootstrap()`.
- `apps/web/src/components/LoginScreenView.tsx` : suppression de `setLoginError(...)` dans le `catch` de `getPublicAuthConfig()` au montage.
- `apps/web/src/components/ShellContainer.tsx` : ajout du garde `!isHydrating && !(isInitialLoading && !isAuthenticated)` sur la redirection automatique vers `/login` pour préserver les chargements directs / `F5` sur `/cockpit`.
- `apps/web/src/__tests__/vitest.setup.ts` : support mock de `GET /api/v1/auth/session`.

### 2.5 Stratégie de Tests (`AD-17`) & Détection E2E Anti-Régression
- **Couche 1 (Unitaires Python & Vitest)** : `tests/unit/test_platform_auth_policy_2fa_and_runtime_isolation.py` (`GET /api/v1/auth/session` anonyme, stale cookie `path="/api/v1/auth"`, valid cookie vs `POST /refresh` `401`) ; `apps/web/src/__tests__/auth-logout-incognito-and-temp-password.test.tsx` (`resolveWebApiBaseUrl`, `hydrateSession` via `/api/v1/auth/session`, `/login` sans bannière en cas d'échec `public-config`, non-redirection de `/cockpit` pendant `isHydrating: true`).
- **Couche 5 (Playwright E2E)** : durcissement de `apps/web/e2e/support/apiErrors.ts` (`watchUnexpectedPageAndApiErrors` capturant tout `/api/*` en `status >= 400`, tout `pageerror`, plus `expectZeroVisibleErrorBanners`), synchronisation `createFirstAdminViaUi` sur `POST /api/v1/bootstrap/welcome-setup/first-admin` (`HTTP 200` + `Set-Cookie`), intégration dans `apps/web/e2e/shell.spec.ts` (`afterEach`) et dans `apps/web/e2e/11-screens-smoke-without-server-errors.spec.ts` avec nouveau scénario dédié `/login`.

---

## 3. Bilan des Modifications & Résultats

### 3.1 Inventaire des Fichiers Créés / Modifiés

| Couche | Fichier | Rôle de la Modification |
| --- | --- | --- |
| **Runtime CLI** | [`scripts/manage.py`](file:///home/romain/Documents/Projects/ORCIA/scripts/manage.py) | Activation `--reload` (avec `--reload-dir`, désactivable via `ORCIA_API_NO_RELOAD=1`) et pré-check automatique `.venv/bin/alembic -c infra/migrations/alembic.ini upgrade head` au démarrage `api`. |
| **Schémas API** | [`apps/api/src/orcia_api/schemas/auth_policy.py`](file:///home/romain/Documents/Projects/ORCIA/apps/api/src/orcia_api/schemas/auth_policy.py) | Ajout de `AuthSessionBootstrapResponse` (`authenticated`, `session`, `trace_id`). |
| **Routeur Auth** | [`apps/api/src/orcia_api/routers/_auth_session_routes.py`](file:///home/romain/Documents/Projects/ORCIA/apps/api/src/orcia_api/routers/_auth_session_routes.py) | Extraction de `_rotate_refresh_and_hydrate(...)` et exposition de `GET /api/v1/auth/session` (`200 { authenticated: false, session: null }` sans bruit `401`, purge cookie périmé `path="/api/v1/auth"`), tout en conservant `POST /api/v1/auth/refresh` en `401` strict. |
| **SDK OpenAPI** | [`packages/api-client/src/domains/authAndShell.ts`](file:///home/romain/Documents/Projects/ORCIA/packages/api-client/src/domains/authAndShell.ts) (+ `openapi.json`, `generated/`) | Régénération `0-diff` et ajout de `getSessionBootstrap(): Promise<AuthSessionBootstrapResponse>`. |
| **Store Auth SPA** | [`apps/web/src/stores/authSessionStore.ts`](file:///home/romain/Documents/Projects/ORCIA/apps/web/src/stores/authSessionStore.ts) | Normalisation anti-suffixe `/api` dans `resolveWebApiBaseUrl()` et bascule de `hydrateSession()` vers `client.getSessionBootstrap()`. |
| **UI Login** | [`apps/web/src/components/LoginScreenView.tsx`](file:///home/romain/Documents/Projects/ORCIA/apps/web/src/components/LoginScreenView.tsx) | Repli `console.warn` sans `setLoginError` en cas d'échec `getPublicAuthConfig()` au montage. |
| **Coquille SPA** | [`apps/web/src/components/ShellContainer.tsx`](file:///home/romain/Documents/Projects/ORCIA/apps/web/src/components/ShellContainer.tsx) | Garde `!isHydrating && !(isInitialLoading && !isAuthenticated)` sur le `useEffect` de redirection `/login`. |
| **Tests Python & SPA** | [`tests/unit/test_platform_auth_policy_2fa_and_runtime_isolation.py`](file:///home/romain/Documents/Projects/ORCIA/tests/unit/test_platform_auth_policy_2fa_and_runtime_isolation.py), [`apps/web/src/__tests__/vitest.setup.ts`](file:///home/romain/Documents/Projects/ORCIA/apps/web/src/__tests__/vitest.setup.ts), [`apps/web/src/__tests__/auth-logout-incognito-and-temp-password.test.tsx`](file:///home/romain/Documents/Projects/ORCIA/apps/web/src/__tests__/auth-logout-incognito-and-temp-password.test.tsx) | Couverture unitaire de `/api/v1/auth/session`, normalisation `/api`, montage `/login` sans alerte et non-redirection `/cockpit` pendant `isHydrating`. |
| **Gardes Playwright E2E** | [`apps/web/e2e/support/apiErrors.ts`](file:///home/romain/Documents/Projects/ORCIA/apps/web/e2e/support/apiErrors.ts), [`apps/web/e2e/support/firstAdmin.ts`](file:///home/romain/Documents/Projects/ORCIA/apps/web/e2e/support/firstAdmin.ts), [`apps/web/e2e/shell.spec.ts`](file:///home/romain/Documents/Projects/ORCIA/apps/web/e2e/shell.spec.ts), [`apps/web/e2e/11-screens-smoke-without-server-errors.spec.ts`](file:///home/romain/Documents/Projects/ORCIA/apps/web/e2e/11-screens-smoke-without-server-errors.spec.ts) | Capture stricte `HTTP >= 400` + `pageerror`, `expectZeroVisibleErrorBanners`, attente du `200` `welcome-setup/first-admin` dans `createFirstAdminViaUi` et scénario `/login` anonyme + reconnexion admin. |
| **Registre Capacités** | [`docs/product/capabilities.yaml`](file:///home/romain/Documents/Projects/ORCIA/docs/product/capabilities.yaml) | Mise à jour de `CAP-001` (`origin_ref` + ajout de `e2e/11-screens-smoke-without-server-errors.spec.ts` aux `tests`). |

### 3.2 Vérifications Exécutées & Métriques Observées

- **Python / Hygiène / Contrats** :
  - `.venv/bin/ruff format --check` (`504` fichiers + `scripts/manage.py`) : `OK`.
  - `.venv/bin/ruff check .`, `.venv/bin/mypy --strict` (`341` fichiers), `.venv/bin/lint-imports` (`5/5` contrats conservés), `lint_spine.py` (`0` alerte) : `OK`.
  - `.venv/bin/python scripts/export_openapi.py --check` : `OK` (`0-diff`).
  - Pytest ciblé (unitaires + sécurité + intégration PG18 `testcontainers`) : **`93 passed`** (`test_platform_auth_policy_2fa_and_runtime_isolation.py`, `tests/security/`, `tests/integration/api/test_platform_auth_modes_2fa_and_local_isolation_postgres18.py`) + **`2 passed`** en `tests/contract/`.
- **TypeScript (`pnpm turbo run lint typecheck test`)** :
  - **`9 successful, 9 total`** : `@orcia/ui` (`21` fichiers / `91` tests), `@orcia/api-client` (`1` fichier / `8` tests), `@orcia/web` (`17` fichiers / `92` tests).
- **Playwright E2E (`01-day0-boot-and-f5-persistence`, `shell`, `11-screens-smoke-without-server-errors`)** :
  - **`13 passed, 3 skipped (projet mobile-assistant pour specs desktop), 0 failed`** en `1.5m`, avec **zéro** avertissement `ERR_AUTH_INVALID_CREDENTIALS` sur `/api/v1/auth/refresh`, zéro `4xx`/`5xx`, zéro `pageerror` et zéro bannière d'erreur sur les 7 écrans et `/login`.
- **GitNexus & Runtime Local** :
  - `npx gitnexus analyze` (`25 319` nœuds, `44 013` arêtes, `1 286` flows) ; `impact` sur `_rotate_refresh_and_hydrate` (`impactedCount: 234`, `direct: 195`, `20` processus) et `getSessionBootstrap` (`0` arête directe car façade par spread objet, appelant vérifié dans `authSessionStore.ts:L230`) ; `detect_changes(scope="all")` : `123` symboles modifiés, `71` fichiers, `1 286` flux.
  - `.venv/bin/python scripts/manage.py restart api` sur `127.0.0.1:8000` (`pid=160136`, `--reload`, `alembic upgrade head` -> `20261115_1901 (head)`).
