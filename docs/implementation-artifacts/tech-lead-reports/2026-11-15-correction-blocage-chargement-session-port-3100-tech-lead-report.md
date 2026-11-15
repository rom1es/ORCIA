# 2026-11-15 — Correction du Blocage « Chargement de la session... » sur le Port 3100 & Routage Login / Day-0

- **Date** : 2026-11-15
- **Story / Clé Sprint** : `2026-11-15-correction-blocage-chargement-session-port-3100` (`Ajustement Transverse` — `main` post-`ec88587`)
- **Capacité(s)** : `CAP-001` (existant dans `docs/product/capabilities.yaml`, complété par `CAP-058` / `CAP-004`) — classification : `hygiène | ux`
- **Auteur / Contexte** : Résolution du blocage en page blanche « Chargement de la session... » observé au démarrage navigateur sur `http://localhost:3100` (session normale ou Incognito) suite à l'introduction de `isHydrating: true` sans déclencheur applicatif, accompagnée de la suppression de l'enveloppement `FourZoneDirectionCShell` sur `/login`, de la suppression du `baseUrl` cross-origin codé en dur dans `login.tsx` et de la garde single-flight anti-React StrictMode sur `POST /api/v1/auth/refresh` (`FR-21`, `FR-28`, `FR-32`).
- **Commits associés** : `en cours`

---

## 1. Analyse du Besoin & Étude d'Impact Tech Lead (Pré-Implémentation)

### 1.1 Contexte & Problématique
- **Symptôme observé** : L'ouverture d'`http://localhost:3100` en navigateur réel reste bloquée indéfiniment sur un écran blanc affichant `Chargement de la session...`.
- **Causes racines identifiées** :
  1. **Absence totale d'appel à `hydrateSession()`** : dans `apps/web/src/stores/authSessionStore.ts`, `getInitialSessionState()` initialise `isHydrating: true` dès que `isVitest` est faux (navigateur réel). Or aucune composante (`ShellContainer.tsx`, `useShellContainerState.ts`, `__root.tsx`, `main.tsx`) n'appelle `hydrateSession()`. `ShellContainer.tsx` rend donc en permanence `<div data-testid="auth-hydrating-loader">Chargement de la session...</div>`.
  2. **Risque de double appel concurrent sous React 19 `<StrictMode>`** : sans déduplication single-flight dans `hydrateSession()`, un montage double en développement déclencherait deux requêtes simultanées vers `POST /api/v1/auth/refresh`, provoquant la rotation + révocation du jeton de rafraîchissement (`HTTP 401 ERR_AUTH_TOKEN_REVOKED`). De plus, sans timeout de sécurité, un backend indisponible bloquerait l'écran indéfiniment.
  3. **Divergence `baseUrl` cross-origin vs proxy Vite** : `apps/web/src/routes/login.tsx` utilise `baseUrl = "http://localhost:8000"` alors que `authSessionStore.ts` et `platformSetupStore.tsx` passent par `baseUrl = ""` (proxy Vite `/api` vers `127.0.0.1:8000`), créant un risque de désalignement du cookie `HttpOnly` `orcia_refresh_token` (`SameSite=Lax`).
  4. **Enveloppement et fallback incohérents dans `ShellContainer.tsx` / `__root.tsx`** :
     - Lorsque `!isAuthenticated && !isAdminModalOpen && pathname !== "/login"`, `ShellContainer.tsx` affichait une carte intermédiaire dont le bouton se contentait de faire `history.pushState` vers `/login` en ignorant les identifiants.
     - Sur `/login`, `ShellContainer.tsx` laissait rendre l'ensemble du `FourZoneDirectionCShell` (rail de navigation, 8 menus et barre d'en-tête) autour de l'écran de connexion.
     - Pendant l'amorçage asynchrone (`platformSetupStore`), la vérification initiale `getAccostageStatus()` doit être attendue avant de conclure entre l'écran de connexion et la modale d'admin Jour 0, puis la validation du First-Admin Jour 0 doit authentifier directement la session sans double connexion.

### 1.2 Exploration, Analyse d'Impact GitNexus, Factorisation & Dette Technique
- **Analyse d'Impact GitNexus (`gitnexus_query`, `gitnexus_context`, `gitnexus_impact`)** :
  - `hydrateSession` (`apps/web/src/stores/authSessionStore.ts:L188-L226`) : **0 appelant (`impactedCount: 0`)** dans tout le dépôt — confirmant l'absence complète de déclenchement au montage.
  - `useAuthSessionStore` (`apps/web/src/stores/authSessionStore.ts`) : **`impactedCount: 15`, `risk: CRITICAL`** (`direct: 6`, `3` processus impactés dont `InnerShellContainer`, `SettingsHubView`, `SettingsIamOrganizationSection`, `5` modules : `Components`, `Workspaces`, `Primitives`, `Iam`, `Routes`).
  - `ShellContainer` (`apps/web/src/components/ShellContainer.tsx:L336-L348`) : appelé directement par `RootLayoutComponent` dans `apps/web/src/routes/__root.tsx`, délègue à `PlatformSetupProvider` et `InnerShellContainer`.
- **Opportunités de factorisation & Contrôle de volumétrie** :
  - Extraire un helper partagé `resolveWebApiBaseUrl()` dans `apps/web/src/stores/authSessionStore.ts` (réutilisé par `login.tsx` et `authSessionStore.ts`) pour unifier `import.meta.env?.VITE_ORCIA_API_BASE_URL ?? ""` via le proxy Vite `/api`.
  - Conserver strictement `< 360` lignes sur `ShellContainer.tsx` (actuellement `348` lignes) et tous les fichiers modifiés, en s'appuyant si besoin sur `ShellContainerModals.tsx` / `useShellContainerState.ts`.
  - Aucun nouveau ticket de dette requis ; l'action reste ciblée et hygiénique sur la pile Frontend d'amorçage.

---

## 2. Plan d'Implémentation

### 2.1 Schéma de Données & Migrations Alembic (`infra/migrations/versions/...`)
- Aucune évolution de schéma requise (les migrations `20261114_1802` et `20261114_1706` restent inchangées).

### 2.2 Noyau Métier Hexagonal, Orchestration & Workers (`packages/orcia-core/`, `apps/worker/`)
- Aucune modification backend/core nécessaire : `POST /api/v1/auth/refresh`, `POST /api/v1/auth/login/local`, `GET /api/v1/auth/me` et `POST /api/v1/bootstrap/first-admin` émettent déjà les jetons JWT et le cookie `orcia_refresh_token`.

### 2.3 Couche Backend API, Sécurité & Contrats (`apps/api/`, `packages/api-client/`)
- Aucune modification d'API ou de schéma OpenAPI ; conservation du client `@orcia/api-client` avec `credentials: "include"` sur `baseUrl: ""` (same-origin via proxy Vite `/api`).

### 2.4 Interface Utilisateur & Expérience (`apps/web/`)
- **`apps/web/src/stores/authSessionStore.ts`** :
  - Export de `resolveWebApiBaseUrl()` renvoyant `""` par défaut (`import.meta.env?.VITE_ORCIA_API_BASE_URL ?? ""`).
  - Ajout d'un verrou single-flight `activeHydrationPromise` dans `hydrateSession(options?: { force?: boolean })` pour absorber les doubles montages `React.StrictMode` et éviter toute course critique sur la rotation de jeton.
  - Ajout d'un timeout de sécurité de `5000 ms` garantissant le passage systématique de `isHydrating` à `false` dans `finally` / `catch`.
- **`apps/web/src/components/platformSetupStore.tsx`** :
  - Exposition d'un indicateur `isInitialLoading` (actif durant l'interrogation initiale asynchrone de `getAccostageStatus()` hors Vitest synchrone) afin d'éviter d'afficher brièvement `/login` à la place de la modale First-Admin Jour 0.
  - Authentification immédiate de `useAuthSessionStore` à l'issue d'un `POST /api/v1/bootstrap/first-admin` réussi si l'API renvoie un `access_token` (ou via `hydrateSession({ force: true })`).
- **`apps/web/src/routes/login.tsx`** :
  - Remplacement du fallback `"http://localhost:8000"` par `resolveWebApiBaseUrl()`.
  - Export réutilisable du composant de connexion autonome pour montage direct sans coquille 4-zones.
- **`apps/web/src/components/ShellContainer.tsx`** (maintien `< 360` lignes) :
  - Appel automatique de `hydrateSession()` au montage lorsque `isHydrating` est vrai (`useEffect`).
  - Maintien du rendu autonome pour `/showcase`.
  - Attente propre sur `auth-hydrating-loader` tant que `isHydrating` ou l'état initial d'accostage non-authentifié est en cours.
  - Priorité au parcours First-Admin Jour 0 lorsque `!adminConfigured` (`isAdminModalOpen`).
  - Pour tout utilisateur non authentifié (hors Jour 0), rendu direct et autonome de `<LoginRouteComponent />` sans `FourZoneDirectionCShell` (suppression de l'écran intermédiaire muet) et synchronisation d'URL vers `/login` ; si authentifié sur `/login`, redirection propre vers `/`.

### 2.5 Analyse d'Impact sur la Pyramide des Tests (`AD-17` + 5 Garde-Fous)
- **Couche 1b (`Vitest` `@orcia/web` sans court-circuit `isJsdom`)** :
  - Extension de `apps/web/src/__tests__/auth-logout-incognito-and-temp-password.test.tsx` avec simulation explicite d'un démarrage navigateur réel (`isHydrating: true`, `UNAUTHENTICATED_SESSION_STATE`) :
    1. Démarrage Incognito (`refresh` ➔ `401`, `adminConfigured: true`) : présence initiale du loader, appel automatique de `/api/v1/auth/refresh`, disparition du loader, absence totale du shell 4 zones / `Romain`, soumission réelle du formulaire de connexion vers `/api/v1/auth/login/local` (same-origin) ouvrant le Cockpit.
    2. Rechargement authentifié sous `<React.StrictMode>` (`refresh` ➔ `200`) : un seul appel `POST /api/v1/auth/refresh` (single-flight vérifié), sortie du loader et restauration de session.
    3. Déconnexion (`🚪 Se déconnecter`) : retour immédiat à l'écran de connexion autonome sans barre latérale ni en-tête 4 zones.
  - Non-régression complète sur les 26 tests de `i18n-and-shell.test.tsx` et l'ensemble de `@orcia/ui`, `@orcia/api-client`, `@orcia/web` + audit anti-patterns Python (`test_codebase_architectural_anti_patterns_audit.py`).

---

## 3. Bilan des Modifications & Résultats (Post-Implémentation)

### 3.1 Fichiers Développés & Modifiés
| Fichier | Nature | Description synthétique | Lignes |
| :--- | :--- | :--- | :---: |
| `apps/web/src/stores/authSessionStore.ts` | Modification | Export de `resolveWebApiBaseUrl()`, verrou single-flight `activeHydrationPromise` anti-React `StrictMode`, timeout 5s et garantie `isHydrating = false` dans `finally`. | 285 |
| `apps/web/src/components/LoginScreenView.tsx` | Création | Vue de connexion autonome réutilisable décorrélée du routage racine (`onAuthenticated`, requêtes same-origin `/api` via Vite proxy). | 133 |
| `apps/web/src/routes/login.tsx` | Modification | Ré-export propre de `LoginRouteComponent` / `LoginScreenView` sans dépendance circulaire. | 17 |
| `apps/web/src/components/ShellAuthFallbackView.tsx` | Création | Composants dédiés `ShellHydratingLoaderView` (`auth-hydrating-loader`) et rendu d'écran de connexion autonome. | 26 |
| `apps/web/src/components/ShellContainer.tsx` | Modification | Déclenchement automatique de `hydrateSession()` au montage si `isHydrating`, bypass `/showcase`, priorité Jour 0, rendu autonome sans coquille 4-zones pour non-authentifiés & `/login`, redirection `/` après authentification. | 343 |
| `apps/web/src/components/platformSetupStore.tsx` | Modification | Exposition de `isInitialLoading` (timeout 5s) coordonnée avec `ShellContainer`, et authentification automatique du First-Admin Jour 0 après `POST /api/v1/bootstrap/first-admin`. | 1282 (legacy) |
| `apps/web/src/__tests__/vitest.setup.ts` | Modification | Helper `setVitestMockRefreshFails` permettant de simuler une absence de session ou un 401 sur `/api/v1/auth/refresh`. | 1530 |
| `apps/web/src/__tests__/auth-logout-incognito-and-temp-password.test.tsx` | Modification | 3 tests de régression simulant le démarrage navigateur réel (`isHydrating: true`), `React.StrictMode` single-flight et déconnexion vers écran login autonome. | 237 |
| `docs/product/capabilities.yaml` | Modification | Rattachement du rapport à `CAP-001` (`origin_ref`). | — |
| `docs/implementation-artifacts/tech-lead-reports/README.md` | Modification | Indexation du présent rapport Tech Lead. | — |

### 3.2 Résultats Chiffrés, Métriques & Qualité
- **Tests Vitest `@orcia/web`** : `16 passed (16 files)` | **`84 passed (84 tests)`**, dont :
  - `auth-logout-incognito-and-temp-password.test.tsx` : **6/6 passed** (démarrage navigateur réel depuis `isHydrating: true`, `StrictMode` single-flight unique, login same-origin, déconnexion sans coquille 4-zones)
  - `i18n-and-shell.test.tsx` : **26/26 passed**
  - `orcia-showcase-site.test.tsx` : **2/2 passed**
  - `zero-dead-buttons-and-silent-catches-audit.test.tsx` : **7/7 passed**
- **Monorepo Turborepo (`pnpm turbo run lint typecheck test`)** : **9/9 tasks successful**.
- **Qualité & Contrôles Architecture Python** :
  - `.venv/bin/pytest tests/unit/test_codebase_architectural_anti_patterns_audit.py -q` : **4/4 passed**.
  - `.venv/bin/ruff check . && .venv/bin/ruff format --check .` : **All checks passed** (`766` fichiers formatés).
  - `.venv/bin/lint-imports` : **5/5 contrats tenus, 0 brisé**.
  - `pnpm site:sync && pnpm site:check` : Manifest synchronisé et validé.
- **Volumétrie** : tous les fichiers applicatifs créés ou refactorisés (`authSessionStore.ts` 285 l., `LoginScreenView.tsx` 133 l., `login.tsx` 17 l., `ShellAuthFallbackView.tsx` 26 l., `ShellContainer.tsx` 343 l.) respectent strictement `< 360` lignes (le découpage progressif du store legacy `platformSetupStore.tsx` reste un sujet d'hygiène ultérieur).

### 3.3 Validation & Procédure de Test sur Toute la Pyramide (`AD-17` + 5 Garde-Fous)
- **Couche 1b — Vitest sans court-circuit `isJsdom` (`auth-logout-incognito-and-temp-password.test.tsx`)** :
  - Simulation d'un chargement navigateur non-Vitest (`isHydrating: true`, `UNAUTHENTICATED_SESSION_STATE`) : vérification du rendu initial du loader `Chargement de la session...`, de l'appel automatique à `POST /api/v1/auth/refresh`, de la disparition du loader après échec `401`, de l'absence du rail 4 zones / identité codée en dur, puis de la connexion via `/api/v1/auth/login/local` déverrouillant le Cockpit.
  - Simulation d'un rechargement sous `<React.StrictMode>` avec cookie valide (`200`) : vérification qu'un seul appel `POST /api/v1/auth/refresh` est émis (`activeHydrationPromise`) et que la session utilisateur est restaurée.
  - Simulation d'un clic sur `🚪 Se déconnecter` : appel `POST /api/v1/auth/logout` et retour immédiat à l'écran autonome de connexion.
- **Audit anti-patterns & catalogue** :
  - Zéro `http://localhost:8000` codé en dur côté front (`resolveWebApiBaseUrl()` pointe vers `""` + proxy Vite `/api`).
  - Synchronisation `pnpm site:sync && pnpm site:check` validée après mise à jour des rapports et capacités.
