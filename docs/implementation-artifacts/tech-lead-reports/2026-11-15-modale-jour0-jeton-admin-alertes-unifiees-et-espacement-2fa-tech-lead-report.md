# 2026-11-15 — Correction Modale Jour 0, Jeton Bearer Admin (`ERR_AUTH_REQUIRED`), Consolidation Design System des Alertes (`OrciaAlertBanner`), Espacement 2FA & Action Item Cockpit Jour 0

- **Date** : 2026-11-15
- **Story / Clé Sprint** : `2026-11-15-modale-jour0-jeton-admin-alertes-unifiees-et-espacement-2fa` (`Ajustement Transverse Auth / UX / Design System`)
- **Capacité(s)** : `CAP-001`, `CAP-004`, `CAP-051`, `CAP-054`, `CAP-058`, `CAP-060` — classification : `ux | hygiène | feature`
- **Auteur / Contexte** : Demandes utilisateur post-merge `ef8e2bc` (avec intervention UX Sally 🎨 et revue Tech Lead) :
  1. Corriger la largeur plein écran (`100 %`) de la modale Jour 0 (`FirstBootAdminSetupModal`) après `pnpm db:reset` et éviter le double formulaire `/login` en arrière-plan.
  2. Archiver la capture de référence du Cockpit Jour 0 et créer un `action_item` dédié (`UX-COCKPIT-DAY0-01`) pour sa refonte complète ultérieure (sans toucher au Cockpit dans cette passe).
  3. Expliquer et corriger l'erreur `Connectez-vous pour accéder à cette ressource.` (`ERR_AUTH_REQUIRED`) visible dans `Configuration` (`Organisation`, `Comptes & Habilitations`, `Authentification`, `Connecteurs`) et dans `Cockpit` alors que l'utilisateur est déjà connecté en `PLATFORM_ADMIN` (`Romain Esnault`), puis unifier les 3 styles d'alertes divergents autour de `<OrciaAlertBanner />` (`@orcia/ui`).
  4. Corriger l'espacement insuffisant du groupe `Code de vérification à 6 chiffres (mode Local)` dans l'onglet `Authentification` (`PlatformAuthSettingsCard`).
- **Commits associés** : *Modifications locales non encore commitées (prêtes pour revue/commit)*

---

## 1. Analyse du Besoin & Étude d'Impact Tech Lead (Pré-Implémentation)

### 1.1 Contexte & Problématique
1. **Point 1 — Modale Jour 0 trop large (`FirstBootAdminSetupModal`)** :
   - Sur `http://localhost:3100/login` après `pnpm db:reset`, la modale `first-boot-admin-setup-modal` occupe `100 %` de la largeur du viewport.
   - Cause racine : `apps/web/vite.config.ts` n'utilise pas de compilateur Tailwind JIT ; toutes les classes utilitaires sont déclarées statiquement dans `packages/ui/src/styles/tokens.css`. Or `FirstBootAdminSetupModal.tsx` applique `className="w-full max-w-md rounded-xl border p-6 shadow-xl space-y-4"`, mais `.max-w-md` (et `.max-w-lg`, `.p-6`) sont absentes de `tokens.css`. Seule `.w-full { width: 100%; }` s'applique, étirant la boîte sur toute la largeur. De plus, lorsqu'on arrive sur `/login` au Jour 0, `LoginScreenView` rend le formulaire `/login` derrière la modale.
2. **Point 2 — Revue complète de l'écran Cockpit Jour 0 (à planifier ultérieurement)** :
   - Après création du premier Administrateur Plateforme, le Cockpit Jour 0 empile plus de 6 bandeaux/cartes (`Accostage 1/6` restant figé sur « Créer le compte Administrateur », raccourcis, état vide, cartes `HumanLedAnchorCard` violette et `ArbitrationTieBreakCard` ambre de démonstration, bannière d'erreur orange), ce qui contrevient à la sobriété Direction C de `DESIGN.md`.
   - Décision utilisateur : consigner immédiatement en `action_item` (`UX-COCKPIT-DAY0-01`) dans `docs/implementation-artifacts/sprint-status.yaml` avec la capture de référence stockée dans `docs/planning-artifacts/ux-designs/ux-ORCIA-2026-10-24/screenshots/`, sans modifier le code fonctionnel du Cockpit dans ce lot.
3. **Point 3 — `ERR_AUTH_REQUIRED` en étant déjà connecté `PLATFORM_ADMIN` + 3 styles d'alertes incompatibles** :
   - **Double cause racine de `ERR_AUTH_REQUIRED`** :
     - *Frontend* : `packages/api-client/src/helpers.ts` n'ajoute l'en-tête `Authorization: Bearer ...` que si `options.accessToken` est fourni. Avant le durcissement `36299c5`, l'impersonation dev masquait l'absence de jeton en basculant silencieusement sur le persona fictif `marc`. Désormais (`0` persona fictive), 8 ponts/composants `apps/web` (`orgUnitsApiBridge.ts`, `iamApiBridge.ts`, `SettingsAuthenticationSection.tsx`, `EnterpriseConnectorsSettingsSection.tsx`, `aiModelsApiBridge.ts`, `platformSetupStore.tsx`, `CockpitHumanLedGovernanceSection.tsx`, `GatesAdaptiveHumanReviewSection.tsx`) appellent `createOrciaApiClient(...)` sans passer `accessToken` depuis `useAuthSessionStore`, déclenchant systématiquement `HTTP 401 ERR_AUTH_REQUIRED` ; une course de montage peut également survenir avant la fin de `hydrateSession()` lors d'un `F5`.
     - *Backend* : `AuthAndOrganizationService` stocke les utilisateurs dans `self._users_by_id` en RAM. Avec `uvicorn --reload` (ou multi-worker), chaque rechargement réinitialise `_users_by_id` à `{}` alors que le compte (`Romain Esnault`) est persisté dans PostgreSQL `users` et que le navigateur possède un JWT valide (`access_token` / cookie `orcia_refresh_token`), provoquant `404 ResourceNotFoundError` / déconnexion silencieuse.
   - **Hétérogénéité des alertes** : `SettingsOrganizationUnitsBlock` rend un ton `amber` (orange) avec icône manuelle pour une erreur bloquante ; `IamAccountsDirectoryCard` rend `<OrciaAlertBanner tone="crimson">` sans icône ; `PlatformAuthSettingsCard` utilise un `<div>` custom blanc bordé rouge avec suffixe technique `(ERR_AUTH_REQUIRED)` collé ; `EnterpriseConnectorsSettingsSection` injecte des `rgba(...)` inline ; `BiModeLoginView` utilise un autre `<div>` ad-hoc.
4. **Point 4 — Espacement `Code de vérification à 6 chiffres (mode Local)` (Sally 🎨)** :
   - Dans `PlatformAuthSettingsCard.tsx`, la classe `space-y-5` sur le conteneur et `border-t pt-4` sur `auth-local-2fa-config` sont absentes de la feuille statique `tokens.css` (`margin-top: 0`, `padding-top: 0`), collant le filet et le titre majuscule directement sous les cartes `LOCAL` / `SSO`.

### 1.2 Exploration, Analyse d'Impact GitNexus, Factorisation & Dette Technique
- **Analyse d'Impact GitNexus (`repo: "ORCIA"`, `direction: "upstream"`)** :
  - `OrciaAlertBanner` (`packages/ui/src/primitives/DesignSystemControls.tsx:L287`) : `195` appelants directs (`d=1`), `234` total impacté (`CRITICAL`, `20` processus / `16` modules). Modification strictement rétrocompatible des props.
  - `createOrciaApiClient` (`packages/api-client/src/index.ts:L56`) & `createRequestJson` (`packages/api-client/src/helpers.ts:L69`) : `195` / `234` (`CRITICAL`). L'ajout d'un `registerDefaultAccessTokenProvider` sécurise centralement 100 % des appels `apps/web` sans dupliquer le câblage store dans chaque composant.
  - `resolve_request_user` (`apps/api/src/orcia_api/routers/_auth_token_issuer.py:L29`) : `195` / `234` (`CRITICAL`). Enrichi sans casser sa signature synchrone via un middleware/garde de réhydratation PostgreSQL en amont pour les JWT valides absents de la RAM.
- **Exploration & Volumétrie des fichiers ciblés (`< 350–400` lignes)** :
  - `ShellContainer.tsx` (`365` L) : modification ciblée mineure (zéro ajout inline massif ; maintien `four-zone-direction-c-shell` au Jour 0 pour conformité `e2e/shell.spec.ts`).
  - `PlatformAuthSettingsCard.tsx` (`388` L) : le remplacement des `<div>` d'alerte custom par `<OrciaAlertBanner>` allège le fichier tout en respectant `< 400` lignes.
  - `EnterpriseConnectorsSettingsSection.tsx` (`394` L) : la suppression des deux blocs `<div>` `rgba(...)` au profit de `<OrciaAlertBanner>` réduit la volumétrie sous `385` lignes et supprime les couleurs inline hors `tokens.css`.
  - Tous les autres fichiers ciblés (`FirstBootAdminSetupModal.tsx` `266` L, `DesignSystemControls.tsx` `304` L, `BiModeLoginView.tsx` `304` L, `helpers.ts` `116` L, `authSessionStore.ts` `299` L) sont sous `320` lignes.
- **Opportunités de Factorisation & Dette Technique** :
  - **DRY Auth Client** : `registerDefaultAccessTokenProvider` dans `@orcia/api-client` + garde `isHydrating` dans les sections consommatrices élimine définitivement la classe entière d'oublis de `accessToken`.
  - **DRY Alertes Design System** : Unification de toutes les alertes sur `<OrciaAlertBanner />` (`tokens.css` + `DesignSystemControls.tsx`) avec icône sémantique automatique, accent latéral `3px solid` Direction C, slot `title`, `code` monospace optionnel et `action`.
  - **Ticket de dette créé** : `UX-COCKPIT-DAY0-01` (`P1`) dans `docs/implementation-artifacts/sprint-status.yaml` avec archive visuelle `docs/planning-artifacts/ux-designs/ux-ORCIA-2026-10-24/screenshots/2026-11-15-cockpit-jour0-revue-ux-reference.jpg`.

---

## 2. Plan d'Implémentation

### 2.1 Schéma de Données & Migrations Alembic (`infra/migrations/versions/`)
- Aucune migration Alembic requise : les tables `users`, `platform_auth_settings`, `org_units`, `iam_accounts`, `enterprise_connectors` existent et contiennent déjà les colonnes nécessaires (`load_auth_candidate_by_id_from_postgres18` est déjà disponible dans `packages/orcia-core/src/orcia_core/bootstrap/_internal/sql_local_auth.py`).

### 2.2 Noyau Métier Hexagonal, Orchestration & Workers (`packages/orcia-core/`)
- Ajout sur `AuthAndOrganizationService` (`packages/orcia-core/src/orcia_core/permissions/service.py`) de méthodes publiques propres (`has_user_in_memory(user_id: str) -> bool`, `verify_access_token_claims(bearer_token: str) -> TokenClaims`) afin d'éviter tout accès externe à des attributs privés `_users_by_id` / `_jwt_manager` lors de la réhydratation PostgreSQL, tout en conservant `0` dépendance framework dans `orcia_core`.

### 2.3 Couche Backend API, Sécurité & Contrats (`apps/api/`, `packages/api-client/`)
- `apps/api/src/orcia_api/routers/_auth_pg_helpers.py` & `apps/api/src/orcia_api/main.py` :
  - Ajout d'un middleware ASGI asynchrone de réhydratation sur miss RAM (`rehydrate_authenticated_user_from_pg_middleware`) : si un appel porte `Authorization: Bearer <jwt>`, que le JWT passe la signature + `boot_epoch`, que l'utilisateur n'est pas en mémoire (`not auth_svc.has_user_in_memory(claims.sub)`) et qu'un moteur PostgreSQL est attaché (`app.state.db_engine`), chargement via `load_auth_candidate_by_id_from_postgres18` et enregistrement si `candidate.is_active` ; journalisation structurée `get_logger` sans `except Exception: pass` muet.
- `packages/api-client/src/helpers.ts` & `packages/api-client/src/index.ts` :
  - Ajout de `getAccessToken?: () => string | null | undefined` dans `OrciaApiClientOptions` et export de `registerDefaultAccessTokenProvider(...)`.

### 2.4 Interface Utilisateur & Expérience (`packages/ui/`, `apps/web/`)
- `packages/ui/src/styles/tokens.css` :
  - Déclaration des utilitaires statiques manquants (`.max-w-sm`, `.max-w-md`, `.max-w-lg`, `.max-w-xl`, `.max-w-2xl`, `.space-y-5`, `.space-y-6`, `.pt-3`, `.pt-4`, `.pt-5`, `.pt-6`, `.mt-5`, `.mt-6`, `.mb-4`, `.p-5`, `.p-6`, `.gap-5`, `.gap-6`) et refonte homogène de `.orcia-ds-alert*` (bordure `1px` + barre latérale `3px` Direction C, contraste thème clair/sombre).
- `packages/ui/src/primitives/DesignSystemControls.tsx` :
  - Enrichissement rétrocompatible de `<OrciaAlertBanner>` (`role` automatique `"alert"` pour `"crimson"` et `"status"` sinon, icône `<OrciaIcon />` sémantique automatique sauf `hideIcon`, `title`, `code`, `action`).
- `apps/web/src/components/FirstBootAdminSetupModal.tsx` & `apps/web/src/features/auth/LoginScreenView.tsx` :
  - Contrainte de largeur `max-w-lg` + `maxWidth: "min(520px, calc(100vw - 2rem))"` centrée pour la modale Jour 0 ; sur `/login` au Jour 0 (`platformAdmin === null`), suppression du formulaire de connexion en doublon derrière la modale (tout en conservant `FourZoneDirectionCShell` monté pour les invariants `e2e/shell.spec.ts`).
- `apps/web/src/stores/authSessionStore.ts` & écrans Settings / Cockpit / Gates :
  - Câblage `registerDefaultAccessTokenProvider(() => useAuthSessionStore.getState().accessToken)` ; attente de fin d'hydratation (`!isHydrating`) et réexécution propre lorsque `accessToken` devient disponible au `F5`.
  - Remplacement de tous les styles d'alerte hétérogènes (`SettingsOrganizationUnitsBlock.tsx` en `crimson`, `IamAccountsDirectoryCard.tsx`, `PlatformAuthSettingsCard.tsx`, `SettingsAuthenticationSection.tsx` sans suffixe `(ERR_...)` collé, `EnterpriseConnectorsSettingsSection.tsx` sans `rgba(...)`, `BiModeLoginView.tsx` en conservant `data-testid="login-rfc9457-error"`).
  - Dans `PlatformAuthSettingsCard.tsx`, respiration verticale (`space-y-6`, `mt-6 pt-5 border-t space-y-3`, titre espacé `mb-3`) pour `Code de vérification à 6 chiffres (mode Local)`.

### 2.5 Analyse d'Impact sur la Pyramide des Tests (`AD-17` — Couches 1 à 5 + Sécurité)
- **Couche 1a & 1b (`pytest` / `Vitest`)** :
  - Tests unitaires `@orcia/api-client` (`registerDefaultAccessTokenProvider`), `@orcia/ui` (`OrciaAlertBanner` 4 tons/rôles/icônes + espacement et alertes `PlatformAuthSettingsCard`), `@orcia/web` (largeur bornée `FirstBootAdminSetupModal` + envoi auto `Bearer` et survie `F5` sur Settings sans `ERR_AUTH_REQUIRED`), et unitaires Python sur `has_user_in_memory` / `verify_access_token_claims`.
- **Couche 2 (`HTTP FastAPI ➔ PostgreSQL 18` `testcontainers`)** :
  - Test d'intégration prouvant qu'après vidage RAM de `auth_svc` (simulation `uvicorn --reload`), un JWT valide pour un administrateur présent en table `users` réhydrate automatiquement l'utilisateur et renvoie `HTTP 200` sur `/api/v1/org-units` et `/api/v1/settings/authentication`.
- **Couche 3 (`OpenAPI 3.1`, `lint-imports`, `lint_spine.py`)** & **Couche Sécurité (`tests/security/`)** :
  - Aucune régression sur les tests anti-usurpation / révocation / `boot_epoch`.
- **Couche 5 (`Playwright E2E`)** :
  - Exécution de `e2e/shell.spec.ts`, `e2e/01-day0-boot-and-f5-persistence.spec.ts`, `e2e/11-screens-smoke-without-server-errors.spec.ts` sur la pile isolée sans toucher aux données locales de l'utilisateur.

---

## 3. Bilan des Modifications & Résultats (Post-Implémentation)

### 3.1 Tableau des Fichiers Créés et Modifiés

| Fichier | Type | Lignes | Description des modifications |
| :--- | :--- | :---: | :--- |
| `packages/ui/src/styles/tokens.css` | Modifié | 1014 | Ajout utilitaires statiques manquants (`.max-w-sm` à `2xl`, `.space-y-5/6`, `.gap-6`, `.px-5/6`, `.py-5/6`, `.pt-3/4/5/6`, `.mt-5/6`, `.mb-4`) + refonte homogène `.orcia-ds-alert*` (Direction C avec accent latéral `3px solid` et compatibilité clair/sombre). |
| `packages/ui/src/primitives/DesignSystemControls.tsx` | Modifié | 344 | Enrichissement 100% rétrocompatible de `OrciaAlertBanner` (4 tons, icônes automatiques `check`/`warning`/`cross`/`infoSymbol`, rôle auto `"alert"` vs `"status"`, slots `title`, `code`, `action`). |
| `packages/ui/src/primitives/PlatformAuthSettingsCard.tsx` | Modifié | 377 | Unification des alertes (`auth-smtp-status-badge`, `auth-save-feedback`), conteneur `space-y-6`, espacement 2FA `mt-6 pt-5 border-t space-y-3` avec titre `block mb-3`. Volumétrie maîtrisée (< 390 L). |
| `packages/ui/src/primitives/BiModeLoginView.tsx` | Modifié | 299 | Migration du bandeau d'erreur RFC 9457 custom vers `<OrciaAlertBanner tone="crimson" role="alert">` avec conservation de `data-testid="login-rfc9457-error"`. |
| `packages/api-client/src/helpers.ts` | Modifié | 129 | Ajout `getAccessToken?: () => string | null | undefined`, `registerDefaultAccessTokenProvider`, et injection dynamique d'en-tête `Authorization: Bearer <token>`. |
| `packages/api-client/src/index.ts` | Modifié | 71 | Export de `registerDefaultAccessTokenProvider`. |
| `apps/web/src/stores/authSessionStore.ts` | Modifié | 301 | Enregistrement au chargement de `registerDefaultAccessTokenProvider(() => useAuthSessionStore.getState().accessToken)`. |
| `apps/web/src/components/FirstBootAdminSetupModal.tsx` | Modifié | 268 | Contrainte de largeur bornée `max-w-lg` et `maxWidth: "min(520px, calc(100vw - 2rem))"` centrée. |
| `apps/web/src/components/LoginScreenView.tsx` | Modifié | 309 | Masquage du formulaire `/login` doublon lorsque `platformAdmin === null` au Jour 0. |
| `apps/web/src/routes/SettingsOrganizationUnitsBlock.tsx` | Modifié | 323 | Garde `!isHydrating` et migration de l'alerte vers `<OrciaAlertBanner tone="crimson" role="alert">`. |
| `apps/web/src/routes/SettingsIamOrganizationSection.tsx` | Modifié | 331 | Garde `!isHydrating` et réactivité au jeton d'accès au F5. |
| `apps/web/src/features/admin/auth/SettingsAuthenticationSection.tsx` | Modifié | 221 | Garde `!isHydrating`, suppression du suffixe `(${errorCode})` brut concaténé. |
| `apps/web/src/features/admin/connectors/EnterpriseConnectorsSettingsSection.tsx` | Modifié | 383 | Garde `!isHydrating` et remplacement des bandeaux `rgba(...)` par `<OrciaAlertBanner>`. Volumétrie allégée à 383 L (< 390 L). |
| `apps/web/src/routes/SettingsAiModelsSection.tsx` | Modifié | 364 | Garde `!isHydrating` et réactivité au jeton JWT au rechargement. |
| `apps/web/src/routes/SettingsAiModelsQuickForm.tsx` | Modifié | 365 | Migration du résultat de test vers `<OrciaAlertBanner>` avec conservation de `data-testid="llm-connection-test-result"` et `data-ok`. |
| `apps/web/src/features/cockpit/CockpitHumanLedGovernanceSection.tsx` | Modifié | 379 | Garde `!isHydrating` et bandeau d'erreur consolidé sur `<OrciaAlertBanner tone="crimson">`. |
| `apps/web/src/features/gates/GatesAdaptiveHumanReviewSection.tsx` | Modifié | 337 | Garde `!isHydrating` et réactivité au jeton JWT. |
| `packages/api-client/src/__tests__/default-access-token-provider.test.ts` | Créé | 134 | 5 tests unitaires vérifiant l'injection Bearer automatique, la priorité `options.accessToken`, et la désactivation. |
| `packages/ui/src/__tests__/alert-banner-and-auth-spacing.test.tsx` | Créé | 178 | 3 tests unitaires vérifiant les 4 tons, rôles ARIA, icônes automatiques, slot action et espacement Direction C `PlatformAuthSettingsCard`. |
| `apps/web/src/__tests__/day0-modal-and-settings-auth-token-wiring.test.tsx` | Créé | 209 | 3 tests vérifiant la largeur bornée Jour 0, l'absence de formulaire doublon sur `/login`, et l'envoi auto de `Authorization: Bearer` sur Settings. |
| `packages/orcia-core/src/orcia_core/permissions/service.py` | Modifié | 352 | Méthodes publiques `has_user_in_memory`, `verify_access_token_claims`, `verify_refresh_token_claims` et factorisation DRY sans accès privé. |
| `apps/api/src/orcia_api/routers/_auth_pg_helpers.py` | Modifié | 336 | `user_identity_from_candidate`, `rehydrate_user_from_pg_by_id` (via `engine.connect()` + garde coroutine), `rehydrate_bearer_subject_from_pg_if_missing`. |
| `apps/api/src/orcia_api/routers/_auth_session_routes.py` | Modifié | 237 | Pré-réhydratation PostgreSQL 18 dans `_rotate_refresh_and_hydrate` avant `svc.refresh_session` (`/session` et `/refresh`). |
| `apps/api/src/orcia_api/main.py` | Modifié | 154 | Middleware HTTP `bearer_auth_rehydration_middleware` dans le contexte W3C. |
| `tests/unit/test_auth_pg_rehydration_after_reload.py` | Créé | 218 | Tests unitaires (3 tests) de vérification claims JWT à cache RAM vide et réhydratation/désactivation PG 18. |
| `tests/integration/api/test_auth_pg_rehydration_postgres18.py` | Créé | 197 | Test vertical `testcontainers` PostgreSQL 18 vérifiant la survie `/auth/session`, `/org-units` et `/settings/authentication` après vidage RAM. |
| `docs/planning-artifacts/ux-designs/ux-ORCIA-2026-10-24/screenshots/2026-11-15-cockpit-jour0-revue-ux-reference.jpg` | Créé | — | Archive visuelle de référence pour la future revue UX du Cockpit Jour 0 (`UX-COCKPIT-DAY0-01`). |
| `docs/implementation-artifacts/sprint-status.yaml` | Modifié | — | Ajout de l'`action_item` `UX-COCKPIT-DAY0-01` (`P1`, `status: open`) sans modifier le code du Cockpit. |
| `docs/product/capabilities.yaml` & `docs/implementation-artifacts/tech-lead-reports/README.md` | Modifiés | — | Mise à jour `CAP-001`, `CAP-058`, `CAP-060` et indexation du rapport. |

### 3.2 Résultats des Vérifications Automatisées (5 Couches `AD-17`)

- **Typecheck & Linter Turbo** (`pnpm turbo run lint typecheck`) :
  - `Tasks: 9 successful, 9 total` (`@orcia/api-client`, `@orcia/ui`, `@orcia/web` — 0 erreur, 0 violation de frontières).
- **Tests Vitest Monorepo** (`pnpm turbo run test`) :
  - `@orcia/api-client` : 2 fichiers, 13/13 tests passés (**100 %**)
  - `@orcia/ui` : 22 fichiers, 94/94 tests passés (**100 %**)
  - `@orcia/web` : 18 fichiers, 95/95 tests passés (**100 %**)
  - Total : **42 fichiers de test, 202 tests passés avec succès**.
- **Qualité Statique, Architecture & Typage Python** :
  - `.venv/bin/ruff check packages apps tests infra` : `All checks passed!` (note : `scripts/audit_code.py` hors périmètre est non suivi)
  - `.venv/bin/ruff format --check packages apps tests infra` : `505 files already formatted`
  - `.venv/bin/lint-imports` : `Contracts: 5 kept, 0 broken` (`384 files, 2399 dependencies`)
  - `.venv/bin/mypy --strict packages/orcia-core packages/orcia-connectors apps/api apps/worker` : `Success: no issues found in 341 source files`
  - `lint_spine.py` : `{"ok": true, "total_findings": 0}`
- **Tests Python (Unitaires, Sécurité & Intégration Verticale PG18 `testcontainers`)** :
  - 9 suites d'authentification / sécurité / réhydratation PG18 (`test_auth_pg_rehydration_after_reload.py`, `test_platform_auth_policy_2fa_and_runtime_isolation.py`, `test_permissions_and_auth.py`, `test_smtp_otp_and_sql_auth_adapters.py`, `test_temp_password_and_local_iam_auth.py`, `test_api_security_baseline.py`, `test_auth_pg_rehydration_postgres18.py`, `test_platform_auth_modes_2fa_and_local_isolation_postgres18.py`, `test_local_auth_logout_and_temp_password_postgres18.py`) : **54 tests passés (100 %, `0` warning coroutine)** ; couverture ciblée : `main.py` **100 %**, `orcia_core/permissions/service.py` **95 %**.
  - Sur l'exécution globale `tests/unit tests/security tests/evals` : les 2 seuls échecs constatés concernent la dette préexistante documentée `DEBT-ORCH-VOCAB-01` (`test_ac_e2`, `test_ac_f2` ; couverture globale `orcia-core` à `85.35 %` sans `tests/integration/`).
- **Tests E2E Playwright (Pile Éphémère Isolée Ports `3101`/`8100`)** :
  - `e2e/shell.spec.ts`, `e2e/01-day0-boot-and-f5-persistence.spec.ts`, `e2e/11-screens-smoke-without-server-errors.spec.ts` : **13 passed, 3 skipped** (tests desktop-only ignorés sur mobile-companion), `0` erreur HTTP `4xx`/`5xx`, `0` bannière d'erreur inattendue.
- **GitNexus & Catalogue Showcase** :
  - `npx gitnexus analyze` (`25,426` nœuds, `44,317` arêtes, `389` clusters, `1 290` flux) et `gitnexus detect_changes` (`36` symboles modifiés sur `32` fichiers, `1 290` processus impactés).
  - `pnpm site:sync && pnpm site:check` : `57/57` capacités live référencent au moins un test, manifest et catalogue synchronisés.
- **Volumétrie & Règles Design System** :
  - `EnterpriseConnectorsSettingsSection.tsx` (`383` L) et `PlatformAuthSettingsCard.tsx` (`377` L) tous deux $< 390$ L.
  - Zéro import `@tanstack/react-router` ou `@orcia/api-client` dans `packages/ui`, zéro couleur hex/rgba hors `tokens.css`, violet `#6D28D9` exclusivement réservé à `HumanLedAnchorCard`, 100 % des `data-testid` préservés.
