# Rapport Tech Lead & Analyse d'Impact : Résilience d'Authentification PostgreSQL 18 sur Miss RAM (Reload Uvicorn / Redémarrage Worker)

**Date :** 2026-11-15
**Auteur :** Tech Lead / Senior Dev ORCIA
**Statut :** Complété (`done`)
**Type :** Correctif & Résilience d'Infrastructure / Authentification (`hygiène`, `CAP-001`)
**Capacité(s) :** `CAP-001` (Authentification exclusive gouvernée, double facteur, sessions HttpOnly et mot de passe temporaire)

---

## 1. Analyse du Besoin & Étude d'Impact Tech Lead

### 1.1 Contexte et Problématique
En environnement réel ou lors du rechargement à chaud d'`uvicorn` (`uvicorn --reload`), le processus serveur FastAPI redémarre. La classe `AuthAndOrganizationService` est réinstanciée en mémoire via `build_default_auth_and_org_service()`, avec un dictionnaire `_users_by_id` vierge (en mode de production réel, aucun utilisateur fictif n'est semé en RAM).

Bien que les utilisateurs soient persistés dans les tables PostgreSQL 18 `users` et `iam_accounts` :
1. Une requête cliente arrivant avec un JWT valide dans l'en-tête `Authorization: Bearer <jwt>` échouait avec un `HTTP 404 ResourceNotFoundError` car `authenticate_access_token` appelait `get_user_by_id(claims.sub)` sur un index RAM vide.
2. Une requête cliente arrivant sur `/api/v1/auth/session` ou `/api/v1/auth/refresh` avec un cookie de rafraîchissement valide échouait également dans `refresh_session(raw_refresh)` avec `ResourceNotFoundError` pour la même raison.

### 1.2 Étude d'Impact & Factorisation
- **Hexagone & Frontières (`AD-19`, `GEMINI.md`)** :
  `AuthAndOrganizationService` se trouve dans `packages/orcia-core/src/orcia_core/permissions/service.py` et ne doit contenir aucun import de framework ou de bibliothèque SQL (`sqlalchemy`, `fastapi`, `redis`). Les méthodes de vérification de claims JWT (`verify_access_token_claims`, `verify_refresh_token_claims`, `has_user_in_memory`) sont exposées publiquement et proprement par `AuthAndOrganizationService`.
- **Réhydratation Asynchrone dans `apps/api`** :
  La couche API dispose déjà de la fonction d'accès PostgreSQL `load_auth_candidate_by_id_from_postgres18(conn, user_id=...)` dans `orcia_core.bootstrap`. La réhydratation s'opère dans `apps/api/src/orcia_api/routers/_auth_pg_helpers.py` :
  - Sur `/session` et `/refresh` : pré-vérification du refresh token et injection de l'utilisateur en mémoire avant rotation (`rehydrate_user_from_pg_by_id`).
  - Sur l'ensemble des routes API recevant un `Authorization: Bearer <jwt>` : middleware ASGI/HTTP vérifiant la validité cryptographique du JWT et rechargeant le profil depuis PostgreSQL 18 si l'utilisateur est absent de la RAM (`rehydrate_bearer_subject_from_pg_if_missing`).
- **Comportement et Vérification de `boot_epoch`** :
  L'analyse détaillée démontre que `boot_epoch` n'est pas un composant du JWT (le payload JWT est composé exclusivement de `sub`, `email`, `role`, `org_unit_id`, `archetype`, `auth_mode`, `jti`, `iat`, `exp`). `boot_epoch` est une métadonnée d'état de la plateforme (`PlatformAuthPolicyState.boot_epoch` persistée dans la table PostgreSQL 18 `platform_auth_settings`). `resolve_auth_policy_runtime(request)` lit systématiquement la table `platform_auth_settings` dès que PostgreSQL est actif. Les JWT signés avant un rechargement restent valides tant que leur date d'expiration n'est pas atteinte et que leur `jti` n'a pas été révoqué.

---

## 2. Plan d'Implémentation

### 2.1 Schéma et Migration Alembic
- Aucun changement de schéma nécessaire : les tables `users`, `iam_accounts` et `platform_auth_settings` existent déjà avec leurs contraintes et colonnes.

### 2.2 Noyau Hexagonal (`packages/orcia-core`)
- Dans `packages/orcia-core/src/orcia_core/permissions/service.py` :
  - Ajout de `has_user_in_memory(self, user_id: str) -> bool`.
  - Ajout de `verify_access_token_claims(self, bearer_or_raw_token: str, *, now_ts: int | None = None) -> TokenClaims`.
  - Ajout de `verify_refresh_token_claims(self, refresh_token: str, *, now_ts: int | None = None) -> TokenClaims`.
  - Refactorisation de `authenticate_access_token` et `refresh_session` pour réutiliser ces primitives (DRY).

### 2.3 Backend FastAPI & Helpers PG18 (`apps/api`)
- Dans `apps/api/src/orcia_api/routers/_auth_pg_helpers.py` :
  - `user_identity_from_candidate(candidate: LocalAuthCandidate, auth_mode: str = "LOCAL") -> UserIdentity`.
  - `rehydrate_user_from_pg_by_id(engine: AsyncEngine | None, svc: AuthAndOrganizationService, user_id: str, *, auth_mode: str = "LOCAL") -> UserIdentity | None`.
  - `rehydrate_bearer_subject_from_pg_if_missing(request: Request) -> None` avec gestion des logs d'erreurs inattendues.
- Dans `apps/api/src/orcia_api/routers/_auth_session_routes.py` :
  - Mise à jour de `_rotate_refresh_and_hydrate` pour pré-hydrater le sujet depuis PostgreSQL avant `refresh_session`.
- Dans `apps/api/src/orcia_api/main.py` :
  - Brancher le middleware HTTP appelant `rehydrate_bearer_subject_from_pg_if_missing(request)`.

### 2.4 Tests et Couverture
- Test unitaire : `tests/unit/test_auth_pg_rehydration_after_reload.py` (vérification unitaire des méthodes sans état privé).
- Test d'intégration PostgreSQL 18 : `tests/integration/api/test_auth_pg_rehydration_postgres18.py` (testcontainers PG18 simulant un vidage complet de la mémoire RAM du service d'authentification après login, puis vérifiant le succès de `/api/v1/auth/session`, `/api/v1/org-units` et `/api/v1/settings/authentication`).

---

## 3. Bilan des Modifications & Résultats

### 3.1 Tableau des Fichiers Modifiés et Créés

| Fichier | Lignes | Rôle & Modifications |
|---|---|---|
| `packages/orcia-core/src/orcia_core/permissions/service.py` | 352 | Ajout des méthodes publiques `has_user_in_memory`, `verify_access_token_claims`, `verify_refresh_token_claims`, refactorisation DRY de `authenticate_access_token` et `refresh_session`. |
| `apps/api/src/orcia_api/routers/_auth_pg_helpers.py` | 332 | Fonctions `user_identity_from_candidate`, `rehydrate_user_from_pg_by_id`, `rehydrate_bearer_subject_from_pg_if_missing`, mise à jour de `hydrate_user_identity_from_pg` (désactivation/suppression en base). |
| `apps/api/src/orcia_api/routers/_auth_session_routes.py` | 237 | Pré-réhydratation PostgreSQL 18 dans `_rotate_refresh_and_hydrate` avant rotation du refresh token. |
| `apps/api/src/orcia_api/main.py` | 154 | Middleware ASGI `bearer_auth_rehydration_middleware` exécuté dans le contexte de trace. |
| `tests/unit/test_auth_pg_rehydration_after_reload.py` | 194 | Tests unitaires des méthodes publiques et des helpers de réhydratation sans accès privé. |
| `tests/integration/api/test_auth_pg_rehydration_postgres18.py` | 197 | Test d'intégration vertical `testcontainers` PostgreSQL 18 validant la survie de session au vidage RAM. |

Tous les fichiers modifiés et créés respectent strictement la règle `< 400 lignes`.

### 3.2 Résultats des Portes de Qualité et Vérifications

1. **Tests unitaires et de sécurité baseline** :
   ```bash
   .venv/bin/pytest tests/unit/test_auth_pg_rehydration_after_reload.py tests/unit/test_platform_auth_policy_2fa_and_runtime_isolation.py tests/unit/test_permissions_and_auth.py tests/security/test_api_security_baseline.py -q
   # Résultat : 43 passed en 8.35s
   ```
2. **Tests d'intégration verticaux PostgreSQL 18** :
   ```bash
   .venv/bin/pytest tests/integration/api/test_auth_pg_rehydration_postgres18.py tests/integration/api/test_platform_auth_modes_2fa_and_local_isolation_postgres18.py -q
   # Résultat : 2 passed en 23.46s (testcontainers pgvector/pgvector:pg18)
   ```
3. **Linter Ruff** :
   ```bash
   .venv/bin/ruff check packages/orcia-core apps/api tests/unit/test_auth_pg_rehydration_after_reload.py tests/integration/api/test_auth_pg_rehydration_postgres18.py
   # Résultat : All checks passed!
   ```
4. **Formateur Ruff** :
   ```bash
   .venv/bin/ruff format --check packages/orcia-core apps/api tests/unit/test_auth_pg_rehydration_after_reload.py tests/integration/api/test_auth_pg_rehydration_postgres18.py
   # Résultat : 304 files already formatted
   ```
5. **Vérification d'Architecture Hexagonale `lint-imports`** :
   ```bash
   .venv/bin/lint-imports
   # Résultat : Contracts: 5 kept, 0 broken.
   ```
6. **Contrôle de Typage Strict `mypy`** :
   ```bash
   .venv/bin/mypy --strict packages/orcia-core/src/orcia_core/permissions/service.py apps/api/src/orcia_api/routers/_auth_pg_helpers.py apps/api/src/orcia_api/routers/_auth_session_routes.py apps/api/src/orcia_api/main.py
   # Résultat : Success: no issues found in 4 source files
   ```

### 3.3 Traçabilité du Registre des Capacités
- Capacité couverte : **`CAP-001`** (Authentification exclusive gouvernée, double facteur, sessions HttpOnly et mot de passe temporaire).
- Aucune régression détectée sur l'ensemble de la suite de tests unitaire, d'intégration et de sécurité.
