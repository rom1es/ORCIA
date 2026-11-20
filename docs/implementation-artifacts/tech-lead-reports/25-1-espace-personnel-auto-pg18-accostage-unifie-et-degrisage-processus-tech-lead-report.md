# Story 25.1 — Provisionnement Automatique de l'Espace Personnel (`PRIVATE_USER` PG18), Guide d'Accostage Unifié & Dégrisage `Mes Processus`

- **Date** : 2026-11-20
- **Story / Clé Sprint** : `25-1-espace-personnel-auto-pg18-accostage-unifie-et-degrisage-processus` (`Epic 25`)
- **Capacité(s)** : `CAP-004`, `CAP-005`, `CAP-061`, `CAP-067`, `CAP-020` — classification : `feature`
- **Auteur / Contexte** : Implémentation Story 25.1 (`FR-21`, `FR-28`, `FR-32`, `AD-6`, `AD-14`, `AD-16` amendé Epic 25, `AD-19`, `AD-21`, `DESIGN.md`). Provisionner automatiquement et de façon idempotente un espace personnel privé isolé en PostgreSQL 18 pour chaque utilisateur (sans rompre la vérité terrain Jour 0 `0` user / `0` workspace après `pnpm db:reset`), unifier le Guide d'Accostage à 6 jalons (`4. Premier Espace d'équipe`, non repliable tant que `< 6/6`, coches vertes & flèches alignées verticalement), et dégriser `Mes Processus` dès `1` modèle IA actif grâce à l'Espace Personnel.
- **Commits associés** : *(en cours d'implémentation — sans commit avant validation QA)*

---

## 1. Analyse du Besoin & Étude d'Impact Tech Lead (Pré-Implémentation)

### 1.1 Contexte & Problématique
1. **Absence d'Espace Personnel automatique & fuite potentielle inter-admins** :
   - Après initialisation du 1er `PLATFORM_ADMIN` ou création d'un utilisateur IAM, aucun espace personnel privé n'était créé en PG18. L'utilisateur devait d'abord créer une équipe et un espace partagé avant de pouvoir exécuter `Mes Processus`.
   - Par ailleurs, les espaces `PRIVATE_USER` créés précédemment ne bénéficiaient pas d'une isolation propriétaire stricte dans `MatrixPermissionEvaluator` ni dans `reconcile_workspaces_on_load` (`platform_settings` global), et `sql_platform_setup_relational_sync.py` rattachait automatiquement tous les `PLATFORM_ADMIN`s ou risquait de purger les espaces absents du snapshot global.
2. **Double affichage et instabilité visuelle du Guide d'Accostage (`ProgressiveDay0AccostageBanner.tsx`, 400 L)** :
   - Le composant rendait des sous-blocs redondants (`Step 1: Platform Administrator Account`, `Step 2: Connect AI Models`, `Step 3: 6-step setup path`) en plus de la liste des jalons, autorisait le repli (`Réduire`) alors que l'accostage était `< 6/6`, codait les libellés `Réduire` / `Déplier le guide` en dur, et utilisait un alignement `justify-between` éloignant la coche/flèche du texte sans coloration verte sémantique.
   - Le jalon 4 portait le libellé ambigu `4. Premier Espace` et comptabilisait tout `workspaces` (ce qui aurait faussement validé le jalon 4 dès l'Espace Personnel automatique).
3. **Blocage injustifié de `Mes Processus` (Bug 9)** :
   - `CockpitOrientationCards` ne recevait pas `disabledMenuKeys`, restant actif visuellement même à `0` modèle IA, alors que la barre latérale le grisait ; inversement, dès `1` modèle IA actif, `Mes Processus` doit s'activer aussi bien dans la barre latérale que dans les cartes du Cockpit grâce à l'Espace Personnel.

### 1.2 Exploration, Analyse d'Impact GitNexus, Factorisation & Dette Technique
- **Analyse d'Impact GitNexus (`repo: "/home/romain/Documents/Projects/ORCIA"`)** :
  - `MatrixPermissionEvaluator.resolve_workspace_access` (`packages/orcia-core/src/orcia_core/permissions/evaluator.py`) : risque `CRITICAL` (`211` symboles impactés en amont, `196` processus, `20` modules) — appelants directs dans `org_and_workspaces.py`, `_finops_scope_guards.py`, `_auth_session_routes.py`, `permission_broker.py`. La règle de garde `personal_owner_user_id` en tête de `resolve_workspace_access` est rétrocompatible pour tous les espaces partagés (`personal_owner_user_id is None`).
  - `CockpitOrientationCards` (`packages/ui/src/primitives/CockpitOrientationCards.tsx`) : risque `CRITICAL` (`209` symboles indirects via le baril `@orcia/ui`, `1` appelant direct `StreamlinedCockpitView`). Ajout de la prop optionnelle `disabledMenuKeys?: Partial<Record<EightFixedMenuKey, string>>` sans casser les appels existants.
  - Recherches de références complémentaires (`create_first_platform_admin_on_postgres18`, `create_iam_account_on_postgres18`, `get_accostage_pg18_counts`, `ProgressiveDay0AccostageBanner`, `buildShellDisabledMenuKeys`) : appelants ciblés dans `bootstrap_accostage.py`, `_iam_accounts_routes_helpers.py`, `org_unit_invitations.py`, `shellBreadcrumbAndScope.ts`, `cockpit/index.tsx`.
- **Exploration & Chiffres Clés (Base de Données & Contraintes)** :
  - Contrainte `workspaces.visibility_mode CHECK (visibility_mode IN ('STANDARD', 'CONFIDENTIAL_RESTRICTED'))` dans `0002_story_1_2_auth_org_workspaces_permissions.py:83-85` : l'utilisation de `'CONFIDENTIAL_RESTRICTED'` en colonne SQL + `settings_jsonb.ui_visibility_mode = 'PRIVATE_USER'` + `settings_jsonb.personal_owner_user_id` évite toute migration destructive.
  - Contrainte FK `workspace_memberships.user_id REFERENCES users(id) ON DELETE CASCADE` : l'insertion d'appartenance pour un utilisateur IAM créé via `/settings/iam/accounts` ou `/org-units/invite-user` doit intervenir dès que la ligne `users` existe (dans `upsert_human_user_credentials_on_postgres18` et lors de `create_iam_account_on_postgres18` si `users` existe déjà, puis à la connexion / `GET /workspaces`).
  - `sql_platform_setup_reconcilers.py` & `sql_platform_setup_relational_sync.py` : identifiés comme points de fuite/purge potentiels si le snapshot global `platform_settings` réconciliait ou purgeait les espaces personnels — protégés explicitement dans le plan.
- **Opportunités de Factorisation & Contrôle de Volumétrie** :
  - `sql_personal_workspace.py` (`< 180` L) : brique SQL transactionnelle unique réutilisée par `sql_first_user_guard.py`, `sql_iam_accounts.py`, `sql_local_auth.py` et `_personal_workspace_sync.py`.
  - Découpage de `sql_iam_accounts.py` (`378` L $\rightarrow$ `< 300` L) via extraction des opérations d'annuaire/suppression vers `sql_iam_account_mutations.py` (`< 160` L) avec ré-export transparent.
  - Refonte de `ProgressiveDay0AccostageBanner.tsx` (`400` L $\rightarrow$ `< 220` L) en supprimant les 3 sous-blocs redondants.
  - Pas de ticket `Story N.Ma` supplémentaire requis : les deux dépassements de volumétrie sont résorbés directement dans l'enveloppe de `Story 25.1`.

---

## 2. Plan d'Implémentation

### 2.1 Schéma de Données & Migrations Alembic (`infra/migrations/versions/...`)
- **Aucune nouvelle migration Alembic requise** : le modèle relationnel existant (`workspaces.visibility_mode = 'CONFIDENTIAL_RESTRICTED'`, `workspaces.settings_jsonb`, `workspace_memberships`, contrainte `chk_workspace_memberships_role` élargie en `20261117_2001`) supporte intégralement l'isolation et les métadonnées `PRIVATE_USER` / `is_personal_workspace` / `personal_owner_user_id`.

### 2.2 Noyau Métier Hexagonal, Orchestration & Workers (`packages/orcia-core/`)
- `packages/orcia-core/src/orcia_core/bootstrap/_internal/sql_personal_workspace.py` (**Création**, `< 180` L) :
  - Expose `ensure_personal_workspace_on_postgres18(conn, *, user_id: str, display_name: str, locale: str = "fr") -> str`.
  - Slug déterministe `f"personal-{user_id}"`, `owner_org_unit_id = ensure_root_org_unit(conn)`.
  - `visibility_mode = 'CONFIDENTIAL_RESTRICTED'` + `settings_jsonb` fusionné avec `{"ui_visibility_mode": "PRIVATE_USER", "is_personal_workspace": True, "personal_owner_user_id": str(user_id), "lifecycle_phase": "BUILD"}`.
  - Upsert `ON CONFLICT (slug) DO UPDATE SET settings_jsonb = workspaces.settings_jsonb || EXCLUDED.settings_jsonb RETURNING id` avec `UUIDv7`.
  - Insertion idempotente dans `workspace_memberships` (`WHERE NOT EXISTS (...)`) **exclusivement** pour `user_id` (`role` validé dans `chk_workspace_memberships_role`, `access_mode = 'CONTRIBUTOR_ACTION_REQUIRED'`), sans jamais ajouter d'autres `PLATFORM_ADMIN`s.
- `packages/orcia-core/src/orcia_core/bootstrap/_internal/sql_first_user_guard.py`, `sql_iam_accounts.py` (`< 300` L après extraction vers `sql_iam_account_mutations.py`), `sql_local_auth.py` :
  - Appel transactionnel de `ensure_personal_workspace_on_postgres18` à la création du 1er admin, à l'upsert des identifiants humains (`users`) et lors de la création IAM si la ligne `users` existe. Jamais appelé quand `0` user existe (`pnpm db:reset`).
- `packages/orcia-core/src/orcia_core/bootstrap/_internal/sql_platform_setup_reconcilers.py` & `sql_platform_setup_relational_sync.py` :
  - Exclure les espaces personnels (`is_personal_workspace` / `personal_owner_user_id`) de la réconciliation JSONB globale et de `_purge_removed_workspaces` afin d'éviter toute fuite inter-utilisateurs ou suppression involontaire.
- `packages/orcia-core/src/orcia_core/bootstrap/_internal/sql_accostage_counts.py` & `progressive_accostage.py` :
  - Compter pour `workspaces_count` uniquement les espaces partagés (`COALESCE(settings_jsonb->>'ui_visibility_mode', 'STANDARD') <> 'PRIVATE_USER'`).
  - Renommer le jalon 4 en `"4. Premier Espace d'équipe"` (FR) / `"4. First Team Space"` (EN).
- `packages/orcia-core/src/orcia_core/permissions/models.py` & `evaluator.py` :
  - Ajouter `personal_owner_user_id: str | None = None` et `ui_visibility_mode: str | None = None` sur `WorkspaceEntity`.
  - Dans `MatrixPermissionEvaluator.resolve_workspace_access`, si `workspace.personal_owner_user_id is not None`, refuser (`None`) pour tout `user.id != personal_owner_user_id` (même `PLATFORM_ADMIN` ou partage de `root_org_unit_id`).

### 2.3 Couche Backend API, Sécurité & Contrats (`apps/api/`, `packages/api-client/`)
- `apps/api/src/orcia_api/schemas/auth_and_org.py` :
  - Élargir `WorkspaceSummaryItem.visibility_mode` à `Literal["STANDARD", "CONFIDENTIAL_RESTRICTED", "PRIVATE_USER"]` et ajouter `is_personal: bool = False`.
- `apps/api/src/orcia_api/routers/_personal_workspace_sync.py` (**Création**) & branchements dans `_auth_pg_helpers.py`, `_auth_2fa_helpers.py`, `_auth_oidc_helpers.py`, `auth.py`, `_auth_session_routes.py`, `org_unit_invitations.py`, `org_and_workspaces.py` :
  - Réhydrater idempotemment l'espace personnel en PG18 lors de l'authentification / refresh / `/me` / `GET /api/v1/workspaces` (si l'utilisateur a une ligne active dans `users`).
- `apps/api/src/orcia_api/routers/_finops_scope_guards.py` & `_auth_pg_helpers.py` :
  - Lire `settings_jsonb` dans `sync_evaluator_topology_from_pg` pour hydrater `ui_visibility_mode` et `personal_owner_user_id`.
  - Exposer `visibility_mode = "PRIVATE_USER"` et `is_personal = True` dans `serialize_workspace_summary`.
- `packages/api-client/` :
  - Régénération du SDK OpenAPI via `.venv/bin/python scripts/export_openapi.py` (`0-diff`).

### 2.4 Interface Utilisateur & Expérience (`packages/ui/`, `apps/web/`)
- `apps/web/src/components/platformSetupHydration.ts` & `platformSetupAccostage.ts` :
  - Hydrater `workspaces` depuis `GET /api/v1/workspaces` (`client.listWorkspaces()`), exclure les espaces personnels (`slug.startsWith("personal-")`) du snapshot global `PUT /platform-setup-state`, exclure `visibilityMode === "PRIVATE_USER"` du calcul du jalon 4, et renommer le jalon 4 en `4. Premier Espace d'équipe` / `4. First Team Space`.
- `packages/ui/src/primitives/ProgressiveDay0AccostageBanner.tsx` (`< 240` L) & `apps/web/src/i18n/locales/shell_and_search_labels.ts` :
  - Supprimer les sous-blocs `Step 1 / Step 2 / Step 3` pour n'afficher qu'une seule liste unifiée des jalons visibles (`1..6`).
  - Pilule de progression via `labels` (`{completed} / {total} complétées` en FR, `{completed} of {total} completed` en EN).
  - Verrouiller déplié (`isCompact = false`, absence totale de `accostage-compact-toggle-btn`) tant que `completedCount < totalCount`, et utiliser les clés `i18n` quand `completedCount === totalCount`.
  - Jalons terminés en tokens verts `bg-[var(--color-gate-pass-bg)] border-[var(--color-gate-pass)] text-[var(--color-gate-pass)]` avec grille alignée `grid grid-cols-[minmax(220px,280px)_24px_1fr] items-center gap-3`.
- `apps/web/src/components/shellScopeOptions.ts`, `shellBreadcrumbAndScope.ts`, `shellNavigationContext.ts`, `ShellContainer.tsx`, `apps/web/src/features/cockpit/index.tsx`, `packages/ui/src/primitives/StreamlinedCockpitView.tsx`, `packages/ui/src/primitives/CockpitOrientationCards.tsx` :
  - Propager `disabledMenuKeys` (avec `effectiveHasWorkspaces = workspaces.length > 0 || Boolean(hasWorkspaces)`) jusqu'à `CockpitOrientationCards` pour désactiver/griser à l'identique de la barre latérale à `0` modèle IA et dégriser `Mes Processus` dès `1` modèle IA actif + Espace Personnel.

### 2.5 Analyse d'Impact sur la Pyramide des Tests (`AD-17` — à réaliser par le sous-agent QA indépendant)
- **Couche 1a & 1b (Unitaires Python & Vitest)** : tests `ensure_personal_workspace_on_postgres18`, isolation `MatrixPermissionEvaluator` sur `personal_owner_user_id`, filtrage `PRIVATE_USER` sur `sql_accostage_counts` & `platformSetupAccostage`, rendu unifié `ProgressiveDay0AccostageBanner`, propagation `disabledMenuKeys` sur `CockpitOrientationCards`.
- **Couche 2 (Intégration PG18)** : vérification `0` workspace après `db:reset`, création automatique au 1er admin / IAM / login, isolation stricte inter-admins (`User A` vs `Admin B`), `GET /api/v1/workspaces` retournant `PRIVATE_USER` + `is_personal: true`.
- **Couche 3 (OpenAPI `0-diff` & `lint-imports`)** : validation `export_openapi.py --check` et frontières hexagonales `AD-19`.
- **Couche Sécurité** : non-fuite de l'espace personnel vers un autre `PLATFORM_ADMIN` (même via `/workspaces`, `/platform-setup-state` ou FinOps).
- **Couche 5 (E2E Playwright)** : parcours Jour 0 -> 1er modèle IA -> dégrisage `Mes Processus`, jalon `4. Premier Espace d'équipe`, verrouillage non-repliable `< 6/6` et alignement vertical des coches vertes.

---

## 3. Bilan des Modifications & Résultats (Post-Implémentation)

### 3.1 Fichiers Développés & Modifiés
| Fichier | Nature | Volumétrie (`wc -l`) | Description synthétique |
| :--- | :--- | :--- | :--- |
| `packages/orcia-core/src/orcia_core/bootstrap/_internal/sql_personal_workspace.py` | Création | `128` L | Provisionnement SQL idempotent de l'Espace Personnel (`PRIVATE_USER` / `CONFIDENTIAL_RESTRICTED`, `personal_owner_user_id`), rattachement équipe de secours et exclusion des comptages équipe. |
| `packages/orcia-core/src/orcia_core/bootstrap/_internal/sql_iam_account_sync_delete.py` | Création (Split DRY) | — | Extraction des opérations SQL sync/suppression IAM pour maintenir `sql_iam_accounts.py` sous `300` L (`294` L). |
| `packages/orcia-core/src/orcia_core/bootstrap/_internal/sql_accostage_counts.py` | Modification | `81` L | Exclusion des espaces personnels (`PRIVATE_USER`) du décompte `4. Premier Espace d'équipe`. |
| `packages/orcia-core/src/orcia_core/bootstrap/_internal/sql_first_user_guard.py` & `sql_local_auth.py` & `sql_iam_accounts.py` | Modification | `142` L / — / — | Appel idempotent à `ensure_personal_workspace_on_postgres18` lors de la création 1er Admin, comptes locaux et IAM. |
| `packages/orcia-core/src/orcia_core/bootstrap/_internal/sql_platform_setup_reconcilers.py` & `sql_platform_setup_relational_sync.py` | Modification | `249` L / `408` L | Non-effacement des espaces personnels lors de la réconciliation `PUT /platform-setup-state` (`NOT is_personal`). |
| `packages/orcia-core/src/orcia_core/bootstrap/progressive_accostage.py` & `__init__.py` | Modification | `448` L / — | Libellé jalon `4. Premier Espace d'équipe` / `4. First Team Space` et filtrage sur espaces d'équipe uniquement. |
| `packages/orcia-core/src/orcia_core/permissions/models.py` & `evaluator.py` | Modification | `229` L / `384` L | Champs `personal_owner_user_id` & `ui_visibility_mode` sur `WorkspaceEntity`, méthode `replace_workspaces` et verrou strict propriétaire dans `MatrixPermissionEvaluator` (y compris entre deux `PLATFORM_ADMIN`). |
| `apps/api/src/orcia_api/routers/_personal_workspace_sync.py` | Création | `154` L | Helper FastAPI de réhydratation PG18 idempotente de l'Espace Personnel sur session/auth/workspaces. |
| `apps/api/src/orcia_api/routers/_auth_pg_helpers.py`, `_auth_2fa_helpers.py`, `_auth_oidc_helpers.py`, `_auth_session_routes.py`, `auth.py`, `org_unit_invitations.py` | Modification | `365` L (`_auth_pg_helpers.py`) | Branchement du sync Espace Personnel PG18 et exposition `is_personal` / `visibility_mode: PRIVATE_USER` dans `serialize_workspace_summary`. |
| `apps/api/src/orcia_api/routers/_finops_scope_guards.py` & `org_and_workspaces.py` & `schemas/auth_and_org.py` | Modification | `338` L / `278` L | Synchronisation topologie PG18 réelle dans `MatrixPermissionEvaluator` (`replace_workspaces`), ordre déterministe espaces d'équipe avant personnels, contrat `WorkspaceSummaryItem` (`PRIVATE_USER`, `is_personal`). |
| `packages/api-client/openapi.json` & `src/generated/schema.ts` | Régénération | — | Régénération OpenAPI 3.1 (`0-diff` vérifié par `export_openapi.py --check`). |
| `packages/ui/src/primitives/ProgressiveDay0AccostageBanner.tsx` | Modification (Split/Allègement) | `244` L | Liste unifiée des 6 jalons sans sous-blocs `Step 1..3`, alignement vertical grille `✓`/`→`, tokens verts `--color-gate-pass`, verrouillage `accostage-compact-toggle-btn` si `< 6/6`, restauration `welcome-setup-admin-identity-name` (`UX23-07`). |
| `packages/ui/src/primitives/CockpitOrientationCards.tsx` & `StreamlinedCockpitView.tsx` | Modification | `205` L / — | Réception de `disabledMenuKeys` pour désactiver/griser les cartes Cockpit à l'identique du menu latéral. |
| `apps/web/src/components/platformSetupHydration.ts`, `platformSetupAccostage.ts`, `ShellContainer.tsx`, `shellScopeOptions.ts`, `shellNavigationContext.ts`, `i18n/locales/shell_and_search_labels.ts` | Modification | `360` L / `217` L | Hydratation `workspaces` via `client.listWorkspaces()`, exclusion `PRIVATE_USER` du jalon 4, `effectiveHasWorkspaces` pour dégriser `Mes Processus` dès `1` modèle IA actif + Espace Personnel, clés i18n `{completed} / {total} complétées` / `{completed} of {total} completed`. |
| `apps/web/src/features/cockpit/index.tsx` & `useCockpitGovernanceController.ts` | Modification | `315` L / `207` L | Transmission `disabledMenuKeys` au Cockpit et fallback déterministe `governanceWorkspaceId` vers `availableWorkspaces[0]` en périmètre global. |
| `apps/web/src/routes/useOrgUnitsBlockActions.ts` | Modification (Correctif QA) | `328` L | Remplacement des `void hydrateSession({ force: true })` par `await hydrateSession({ force: true })` avant fermeture des modales pour éliminer la rotation concurrente de refresh cookie lors d'une navigation immédiate (`createBuAndTeamViaUi` → `/spaces`). |
| `tests/unit/test_story_25_1_personal_workspace_and_accostage.py`, `test_epic_9_story_9_2_accostage_and_first_user.py`, `tests/integration/api/test_story_25_1_personal_workspace_postgres18.py`, `tests/security/test_story_25_1_personal_workspace_isolation.py` | Création / Modification | — | Suites Python Couches 1a, 2 (`create_app()` réel PG18+Redis sans `dependency_overrides`) et Sécurité. |
| `packages/ui/src/__tests__/four-zone-shell-and-cockpit.test.tsx`, `apps/web/src/__tests__/story-25-1-personal-workspace-accostage-and-processes.test.tsx`, `day0-modal-and-settings-auth-token-wiring.test.tsx`, `direction-c-shell-mobile-companion-and-dynamic-help.test.tsx`, `i18n-and-shell.test.tsx`, `shell-desktop-viewport-scroll-lock-audit.test.tsx`, `apps/web/e2e/01-day0-boot-and-f5-persistence.spec.ts`, `03-human-led-anchor-and-arbitration.spec.ts` | Création / Modification | — | Suites Vitest (`@orcia/ui` + `@orcia/web` sous `<RouterProvider>`) et E2E Playwright (`desktop-cockpit`). |

### 3.2 Résultats Chiffrés, Métriques & Qualité
- **Couverture ciblée Story 25.1 (`pytest --cov-... --cov-fail-under=90`, 46 tests unitaires, sécurité et intégration PG18)** : **`92.41 %`** (`819` instructions / `222` branches, dont `100 %` sur `sql_personal_workspace.py`, `sql_accostage_counts.py` et `permissions/models.py`, `99 %` sur `progressive_accostage.py`, `97 %` sur `sql_platform_setup_relational_sync.py`, `96 %` sur `sql_first_user_guard.py`, `90 %` sur `permissions/evaluator.py`).
- **Suite Python globale (`tests/unit tests/security tests/evals`)** : **`1036 passed`** (`0` échec, `0` skipped).
- **Intégration PG18 réelle (`tests/integration/api/test_story_25_1_personal_workspace_postgres18.py`)** : **`1 passed`** (`21.22s`, `create_app()` + `lifespan` réel sur `pgvector/pgvector:pg18` + `redis:7.4.2-alpine`, `0` override).
- **Suite JS/TS (`pnpm turbo run lint typecheck test`)** : **`9 successful, 9 total`** (`@orcia/api-client` : `20/20`, `@orcia/ui` : `136/136` sur `34` fichiers, `@orcia/web` : `244/244` sur `62` fichiers, ESLint + `tsc --noEmit` à `0` erreur).
- **Qualité statique & Architecture** :
  - `.venv/bin/ruff check . && .venv/bin/ruff format --check .` : `All checks passed!`, `1326 files already formatted` (`0` warning).
  - `.venv/bin/mypy --strict` (`orcia_kernel`, `orcia_core`, `orcia_api`, `orcia_worker`) : `Success: no issues found in 534 source files`.
  - `.venv/bin/lint-imports` : `Contracts: 5 kept, 0 broken` (`620` files, `4481` dependencies).
  - `.venv/bin/python scripts/export_openapi.py --check` : exit `0` (`0-diff`).
  - `lint_spine.py` : `ok: true, total_findings: 0`.
  - `gitnexus_detect_changes({repo: "/home/romain/Documents/Projects/ORCIA", scope: "all"})` : `changed_count: 12`, `changed_files: 42`, `affected_count: 1491`, `risk_level: "critical"` (cohérent avec le périmètre transversal auth/bootstrap/permissions/shell).

### 3.3 Validation & Procédure de Test sur Toute la Pyramide (`AD-17` + 5 Garde-Fous de Câblage Vertical)
- **Couche 1a — Unitaires Python (`pytest`)** : `test_story_25_1_personal_workspace_and_accostage.py` (`5/5`) + `test_epic_9_story_9_2_accostage_and_first_user.py` valident l'idempotence PG18, le verrou propriétaire `MatrixPermissionEvaluator` même entre `PLATFORM_ADMIN`, l'exclusion `PRIVATE_USER` de `4. Premier Espace d'équipe` et la réconciliation sans effacement des espaces personnels.
- **Couche 1b — Composants Frontend (`Vitest` sans `isJsdom`)** : `four-zone-shell-and-cockpit.test.tsx` et `story-25-1-personal-workspace-accostage-and-processes.test.tsx` (sous `<RouterProvider>` réel) valident l'absence de sous-blocs `Step 1..3`, les 6 jalons unifiés dont `4. Premier Espace d'équipe`, les badges FR/EN, le verrouillage `accostage-compact-toggle-btn` sous `6/6`, les classes `--color-gate-pass`, le maintien de `UX23-07`, et le grisé/dégrisage synchronisé de `Mes Processus` dans la barre latérale et le Cockpit.
- **Couche 2 — Intégration Verticale `HTTP ➔ PostgreSQL 18`** : `test_story_25_1_personal_workspace_postgres18.py` démarre `create_app()` + `lifespan` réel et prouve : `0` workspace à Jour 0 (`SELECT`), création automatique d'un espace personnel isolé à l'initialisation du 1er Admin puis du 2e utilisateur, accostage à `1/6` (`first-workspace = False`), passage à `2/6` après 1er modèle IA, puis `first-workspace = True` uniquement après création d'un espace d'équipe.
- **Couche 3 — Contrats & Frontières** : `export_openapi.py --check` (`0-diff`), `lint-imports` (`5/5`), `lint_spine.py` (`0 findings`).
- **Couche Sécurité (`tests/security/test_story_25_1_personal_workspace_isolation.py`)** : prouve qu'Alice (`PLATFORM_ADMIN`), Bob (`PLATFORM_ADMIN`) et Claire (`SECOPS`) avec vrais JWT Bearer ne voient jamais les espaces personnels des autres dans `/api/v1/workspaces` et reçoivent `HTTP 403` sur `/mutations/check` et `/assistant/workspaces/{id}/overview`.
- **Couche 5 — E2E Playwright (`desktop-cockpit`)** : exécution groupée des 5 specs `shell.spec.ts`, `00-stack-smoke.spec.ts`, `01-day0-boot-and-f5-persistence.spec.ts`, `03-human-led-anchor-and-arbitration.spec.ts` et `07-spaces-org-and-workspace-persistence.spec.ts` $\rightarrow$ **`12 passed (2.4m)`**, `0 failed`, `0 skipped` (avec création réel Admin Jour 0, vérification PG18 `personal-`, bannière `1/6` $\rightarrow$ `2/6` et dégrisage `Mes Processus` après configuration du modèle IA, survie F5 et enchaînement `BU -> Équipe -> Espace` sans perte de cookie de session).
