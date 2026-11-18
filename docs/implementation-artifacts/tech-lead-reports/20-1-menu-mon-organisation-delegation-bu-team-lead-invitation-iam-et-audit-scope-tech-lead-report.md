# Story 20.1 — Menu « Mon Organisation » (`/organization`), Délégation `BU_LEAD` / `TEAM_LEAD`, Invitation IAM Scopée & Journal d'Activité Filtré par Périmètre

- **Date** : 2026-11-17
- **Story / Clé Sprint** : `20-1-menu-mon-organisation-delegation-bu-team-lead-invitation-iam-et-audit-scope` (`Epic 20`, résout `IAM-ORG-DELEGATION-01`)
- **Capacité(s)** : `CAP-050`, `CAP-051`, `CAP-058`, `CAP-065`, `CAP-067` (mises à jour dans `docs/product/capabilities.yaml`) — classification : `feature | ux | sécurité`
- **Auteur / Contexte** : Retours d'exploitation sur `Martin Pecheur` (`BU_LEAD`) et `pascal.lacdap@orcia.ia` (`TEAM_LEAD`) : impossibilité de gérer leur BU / sous-BUs / équipes / co-responsables / membres (menu `Configuration` masqué et `/settings` verrouillé en lecture seule), absence de contrôle de sous-arbre sur `/api/v1/org-units`, absence du rôle officiel `ONTOLOGY_LEAD` sur les BUs, impossibilité d'inviter un utilisateur dans son sous-arbre BU sans accès admin global, et exposition de `Plateforme entière` + fuite/masquage sur `/activity` (`audit_ledger`). Couvre `FR-21`, `FR-25`, `FR-31`, `FR-32`, `AD-17`, `AD-19`, `AD-21`.
- **Commits associés** : *(en cours d'implémentation)*

---

## 1. Analyse du Besoin & Étude d'Impact Tech Lead (Pré-Implémentation)

### 1.1 Contexte & Problématique
1. **Blocage complet de la gouvernance locale (`BU_LEAD` & `TEAM_LEAD`) côté Frontend** :
   - `ShellContainer.tsx:L256` masque l'entrée `configuration` pour tout non-`PLATFORM_ADMIN` et `settingsRbacResolver.ts:L34, L70-L102` force `SCOPED_LEAD_SETTINGS_TABS = []` et `isReadOnlyRestricted: true`.
   - Aucune entrée de menu dédiée « Mon Organisation » n'existe sous « Mes Espaces » ; `SettingsHubView` (`apps/web/src/routes/settings.tsx`) héberge l'onglet `organization` mais reste inaccessible aux `BU_LEAD` et `TEAM_LEAD`.
2. **Failles de confinement côté Backend (`/api/v1/org-units` & `/api/v1/settings/iam/accounts`)** :
   - `enforce_org_unit_mutation_access()` (`apps/api/src/orcia_api/routers/_org_units_helpers.py:L83-L102`) vérifie seulement l'appartenance à `ADMIN_MODULE_ALLOWED_ROLES` (`evaluator.py:L26-L28`) sans contrôler que l'unité cible ou `parent_id` relève du sous-arbre dirigé par l'utilisateur (`BU_LEAD`), ni restreindre un `TEAM_LEAD` à l'édition de ses seules équipes (nom, co-responsables, membres).
   - `sql_local_auth.py:L49-L57` mappe `BU_LEAD` vers `BU_DIRECTOR` mais `hydrate_user_identity_from_pg` (`_auth_pg_helpers.py:L236-L271`) ne réactualise pas `platform_role` lors des requêtes `/auth/me`.
   - L'invitation d'un nouveau compte humain par un `BU_LEAD` sans accès à l'onglet global `iam` ni risque d'escalade (`PLATFORM_ADMIN`/`SECOPS`) n'existe pas encore.
3. **Absence du 7e rôle officiel `ONTOLOGY_LEAD`** :
   - `role_matrix.py:L17-L24` et `users.platform_role` (`0002_story_1_2`) n'incluent pas `ONTOLOGY_LEAD` (ni `SECOPS`/`BU_LEAD` dans le `CHECK` SQL de `users.platform_role`), et `org_units` ne porte pas encore `ontology_lead_user_ids_jsonb`.
4. **Journal d'Activité (`/activity` & `audit_ledger`) non scopé** :
   - Côté UI, `buildActivityScopeOptions()` (`activityFormatters.ts:L101-L118`) ajoute systématiquement `Plateforme entière` (`scope-global`), présélectionnée dans `useShellContainerState.ts:L9`, pour tous les utilisateurs.
   - Côté Backend, `enforce_audit_read_access()` (`_finops_auth_guards.py:L151-L221`) n'accorde l'accès global qu'à `PLATFORM_ADMIN` (pas `SECOPS`) et `build_audit_ledger_where()` (`sql_audit_ledger_mappers.py:L159-L174`) filtre uniquement sur `workspace_id` en ignorant `org_unit_id` (masquant aux `BU_LEAD`/`TEAM_LEAD` les événements organisationnels sans espace). De plus, aucune mutation `org_units` ni `iam_accounts` n'est aujourd'hui écrite dans `audit_ledger`.

### 1.2 Exploration, Analyse d'Impact GitNexus, Factorisation & Dette Technique
- **Analyse d'Impact GitNexus (`gitnexus_impact`, `direction: "upstream"`, `repo: "/home/romain/Documents/Projects/ORCIA"`)** :
  - `FourZoneDirectionCShell` (`packages/ui/src/primitives/FourZoneDirectionCShell.tsx`) : `impactedCount: 3`, `risk: LOW`, `epistemic: exact` (`InnerShellContainer`, `ShellContainer`, `RootLayoutComponent`).
  - `SettingsHubView` (`apps/web/src/routes/settings.tsx`) : `impactedCount: 4`, `risk: LOW` (`router.tsx`, `settings.tsx`, `settingsAiModelsRoute.component`, `main.tsx`).
  - `enforce_org_unit_mutation_access` (`apps/api/src/orcia_api/routers/_org_units_helpers.py`) : `impactedCount: 3`, `risk: HIGH` (`create_org_unit`, `patch_org_unit`, `delete_org_unit` dans `org_units.py`).
  - `enforce_audit_read_access` (`apps/api/src/orcia_api/routers/_finops_auth_guards.py`) : `impactedCount: 3`, `risk: LOW` (`list_audit_ledger_entries`, `get_run_provenance_summary`, `export_run_provenance_dossier` dans `audit_ledger.py`).
- **Exploration & Contraintes SQL vérifiées** :
  - Alembic head unique actuel : `20261117_1601`.
  - `audit_ledger` (`20261116_0601`) : `event_type VARCHAR(64) NOT NULL` **sans contrainte `CHECK`** (trigger append-only `BEFORE UPDATE OR DELETE` uniquement) ; `org_unit_id UUID NULL` est déjà présent mais non indexé seul.
  - `users.platform_role` (`0002_story_1_2:L43-L53`) : contrainte `CHECK` fermée à élargir (`SECOPS`, `BU_LEAD`, `ONTOLOGY_LEAD`).
- **Opportunités de Factorisation & Contrôle de Volumétrie (`< 360` L par fichier)** :
  - Plusieurs fichiers ciblés dépassent ou approchent `350` L : `iam_accounts.py` (369 L), `evaluator.py` (354 L), `hierarchical_rbac.py` (485 L, `DEBT-RBAC-SPLIT-01`), `_org_units_helpers.py` (378 L), `sql_org_units_queries.py` (383 L), `ShellContainer.tsx` (372 L), `ActivityLogExplorerView.tsx` (337 L), `IamAccountModal.tsx` (331 L).
  - Découpage strict appliqué dès l'implémentation :
    1. Isoler la logique pure de délégation hiérarchique dans `packages/orcia-core/src/orcia_core/permissions/org_delegation.py` (`< 240 L`, zéro import framework/SQL).
    2. Isoler la synchronisation SQL des `ONTOLOGY_LEAD` dans `packages/orcia-core/src/orcia_core/bootstrap/_internal/sql_org_ontology_lead_sync.py` (`< 220 L`) au lieu d'alourdir `sql_org_iam_role_sync.py` (305 L) ou `sql_org_units_queries.py` (383 L).
    3. Créer le sous-routeur dédié `apps/api/src/orcia_api/routers/org_unit_invitations.py` (`< 220 L`) pour `POST /api/v1/org-units/invite-user` et extraire les helpers d'autorisation/audit d'unités dans `_org_units_delegation_helpers.py` (`< 200 L`) pour réduire `_org_units_helpers.py` sous `320 L`.
    4. Créer `apps/web/src/routes/organization.tsx` et `apps/web/src/features/admin/organization/InviteOrganizationUserModal.tsx` (`< 220 L`), et mettre à jour `IAM-ORG-DELEGATION-01` en `done` une fois vérifié.

---

## 2. Plan d'Implémentation

### 2.1 Schéma de Données & Migrations Alembic (`infra/migrations/versions/20261117_2001_story_20_1_ontology_leads_and_platform_roles.py`)
- `down_revision = "20261117_1601"` (SQL brut `op.execute(sa.text(...))`, zéro import ORM, `upgrade()` et `downgrade()` réversibles) :
  - Élargir les contraintes `CHECK` de `users.platform_role` (ainsi que `workspace_memberships.role` et `workspace_invitations.assigned_role` si présentes) pour ajouter `'SECOPS'`, `'BU_LEAD'`, `'ONTOLOGY_LEAD'`.
  - Ajouter `ontology_lead_user_ids_jsonb JSONB NOT NULL DEFAULT '[]'::jsonb` sur `org_units` avec contraintes `chk_org_units_ontology_leads_is_array` et `chk_org_units_ontology_leads_only_bu CHECK (unit_type = 'BU' OR ontology_lead_user_ids_jsonb = '[]'::jsonb)`.
  - Créer l'index partiel `ix_audit_ledger_org_unit_created_at ON audit_ledger (org_unit_id, created_at DESC) WHERE org_unit_id IS NOT NULL`.

### 2.2 Noyau Métier Hexagonal (`packages/orcia-core/`)
- `permissions/role_matrix.py` : ajout du 7e rôle officiel `ONTOLOGY_LEAD` (`"Référent Glossaire"` / `"Glossary Lead"`), matrice de permissions (`ontology_concepts` / `glossary_promotions` au scope `BU`).
- `permissions/models.py`, `permissions/org_hierarchy.py`, `permissions/iam_accounts.py` : extension `PlatformRole`, champs `ontology_lead_user_ids` (`OrgUnitNode`, `OrgUnitSummary`) et `ontology_led_bu_ids` (`IamAccountRecord`).
- `permissions/org_delegation.py` (nouveau) :
  - `compute_managed_org_scope(user, org_units)` et assertions `assert_can_create_org_unit`, `assert_can_update_org_unit`, `assert_can_delete_org_unit` (garde anti-auto-éviction `422 ERR_ORG_UNIT_LAST_LEAD_REMOVAL_FORBIDDEN`, interdiction `403 ERR_ORG_UNIT_ROOT_DELETE_FORBIDDEN` sur BU racine du `BU_LEAD`, confinement strict sous-arbre `BU_LEAD`, édition seule sur équipes dirigées pour `TEAM_LEAD`).
  - `assert_can_invite_org_user(...)` : invitation uniquement par `PLATFORM_ADMIN` / `BU_LEAD` sur unité du sous-arbre gouverné et rôles autorisés (`TEAM_MEMBER`, `TEAM_LEAD`, `BU_LEAD`, `ONTOLOGY_LEAD`), rejet `403 ERR_PRIVILEGE_ESCALATION_FORBIDDEN` sur `PLATFORM_ADMIN` / `SECOPS`.
- `permissions/errors.py` & `_error_catalog.py` : erreurs RFC 9457 bilingues FR/EN (`ERR_ORG_UNIT_SCOPE_FORBIDDEN`, `ERR_ORG_UNIT_ROOT_DELETE_FORBIDDEN`, `ERR_ORG_UNIT_LAST_LEAD_REMOVAL_FORBIDDEN`, `ERR_PRIVILEGE_ESCALATION_FORBIDDEN`).
- `bootstrap/_internal/sql_local_auth.py`, `sql_org_ontology_lead_sync.py`, `sql_org_units.py`, `sql_org_units_queries.py`, `sql_iam_accounts.py` : gestion complète `ONTOLOGY_LEAD` et sync bidirectionnelle B1 auto-nettoyante `org_units.ontology_lead_user_ids_jsonb ↔ iam_accounts.roles_jsonb`.
- `audit_finops/models.py`, `audit_finops/_internal/sql_audit_ledger_mappers.py`, `audit_finops/outbox_subscriber.py` : ajout de `allowed_org_unit_ids` dans `AuditLedgerFilterParams`, clause SQL `(workspace_id = ANY(:allowed_ws_ids) OR (workspace_id IS NULL AND org_unit_id = ANY(:allowed_ou_ids)))`, propagation `org_unit_id` dans `map_domain_event_to_ledger_entry`.

### 2.3 Couche Backend API, Sécurité & Contrats (`apps/api/`, `packages/api-client/`)
- `routers/_auth_pg_helpers.py` : `hydrate_user_identity_from_pg` réhydrate aussi `platform_role=candidate.platform_role` (sans incohérence `BU_DIRECTOR` vs `BU_LEAD`).
- `routers/org_units.py`, `_org_units_helpers.py`, `_org_units_delegation_helpers.py` : application de `org_delegation` sur `GET` (annotation `can_edit`, `can_create_child`, `can_delete`, `can_manage_members`, `can_manage_ontology_leads`, `can_invite_users`), `POST`, `PATCH`, `DELETE`, et écriture dans `SqlAuditLedgerService` (`ORG_UNIT_CREATED`, `ORG_UNIT_UPDATED`, `ORG_UNIT_DELETED` avec `org_unit_id`).
- `routers/org_unit_invitations.py` : nouvel endpoint `POST /api/v1/org-units/invite-user` (création compte `HUMAN` + mot de passe temporaire 12 car. si `LOCAL` + rattachement atomique à l'unité cible + resync `auth_svc`/`evaluator` + log `IAM_ACCOUNT_INVITED` dans `audit_ledger`).
- `routers/iam_accounts.py` & `_iam_accounts_passwords.py` : verrouillage de `/api/v1/settings/iam/accounts*` aux seuls `PLATFORM_ADMIN` et `SECOPS` (avec anti-escalade `SECOPS` ne pouvant attribuer `PLATFORM_ADMIN`), écriture dans `audit_ledger` (`IAM_ACCOUNT_CREATED/UPDATED/DELETED`), et propagation `ontology_led_bu_ids` sur les schémas `schemas/iam_accounts.py`.
- `routers/_finops_auth_guards.py` (`enforce_audit_read_access`) & `routers/audit_ledger.py` : filtrage différencié (`PLATFORM_ADMIN`/`SECOPS` global, `BU_LEAD` sous-arbre BU+équipes+espaces, `TEAM_LEAD` équipes+espaces, `CONTRIBUTOR`/`OBSERVER` espaces membres uniquement).
- Régénération SDK `@orcia/api-client` via `.venv/bin/python scripts/export_openapi.py` (`0-diff`).

### 2.4 Interface Utilisateur & Expérience (`packages/ui/`, `apps/web/`)
- `packages/ui/src/primitives/FourZoneDirectionCShell.tsx` & `apps/web/src/i18n/locales/` : ajout de l'entrée menu gauche `organization` (`"Mon Organisation"` / `"My Organization"`, `/organization`) juste sous `spaces` (`"Mes Espaces"`), visible pour `PLATFORM_ADMIN`, `BU_LEAD`/`BU_DIRECTOR`, `TEAM_LEAD`.
- `apps/web/src/stores/settingsRbacResolver.ts` & `apps/web/src/routes/settings.tsx` : retrait de l'onglet `"organization"` de `ALL_SETTINGS_TABS` (5 onglets : `iam`, `authentication`, `models`, `connectors`, `packs` avec `iam` par défaut ; redirection propre de `/settings?tab=organization` vers `/organization`).
- `apps/web/src/routes/organization.tsx` & `apps/web/src/features/admin/organization/` : montage dédié sur `/organization`, pilotage par les capacités serveur `can_*`, ajout du sélecteur `Référents Glossaire` (`ontologyLeadUserIds`) sur les modales `BU` (`CreateOrgUnitModal`, `EditOrgUnitModal`) et d'une icône/badge sur `SettingsOrganizationUnitRow`, et modale `+ Inviter un utilisateur` (`InviteOrganizationUserModal` $\rightarrow$ `TemporaryPasswordInvitationModal`).
- `apps/web/src/routes/activity.tsx`, `activityFormatters.ts`, `useShellContainerState.ts` & `ActivityLogFiltersBar.tsx` : retrait total de `Plateforme entière` (`scope-global` / `ALL`) pour tout non-`PLATFORM_ADMIN` et non-`SECOPS`, avec présélection automatique du premier périmètre autorisé et libellés des nouveaux `event_type` `ORG_UNIT_*` / `IAM_ACCOUNT_*`.
- Adaptation de `story-17-1`, `story-17-2`, `story-17-3`, `i18n-and-shell` et `e2e/support/orgAndWorkspace.ts`.

### 2.5 Analyse d'Impact sur la Pyramide des Tests (`AD-17`)
- **Couche 1a (`pytest` $\ge 90\%$)** & **Couche 1b (`Vitest`)** : tests unitaires exhaustifs de `org_delegation`, `ONTOLOGY_LEAD` dans `role_matrix`/`iam_accounts`, filtrage `audit_ledger` par rôle, `organization.tsx` + `InviteOrganizationUserModal` + survie `F5` (`unmount()` + `render()`), filtrage `/activity`.
- **Couche 2 (`HTTP FastAPI ➔ PostgreSQL 18 SELECT` via `testcontainers`)** : réversibilité migration `20261117_2001`, parcours complet `Martin Pecheur` (`BU_LEAD` : crée sous-BU/équipe, ajoute co-responsable & `ONTOLOGY_LEAD`, invite utilisateur, consulte son audit sans voir d'autre BU ni supprimer sa BU racine), `pascal.lacdap@orcia.ia` (`TEAM_LEAD` : édite nom/membres/co-leads de son équipe, rejet `403` sur création/suppression), `CONTRIBUTOR` (`audit_ledger` borné à ses espaces).
- **Couche 3 (`OpenAPI 0-diff`, `lint-imports`, `mypy --strict`, `ruff`)** & **Couche Sécurité (`tests/security/`)** : anti-escalade (`PLATFORM_ADMIN`/`SECOPS`), confinement latéral inter-BU, `403 ERR_OBSERVER_MODE_READ_ONLY`.
- **Couche 5 (`Playwright E2E`)** : mise à jour de `support/orgAndWorkspace.ts` / `11-screens-smoke` vers `/organization`.

---

## 3. Bilan des Modifications & Résultats (Post-Implémentation)

### 3.1 Fichiers Développés & Modifiés
| Fichier | Nature | Description synthétique |
| :--- | :--- | :--- |
| `infra/migrations/versions/20261117_2001_story_20_1_ontology_leads_and_platform_roles.py` | Création | Migration SQL brute réversible (`down_revision = "20261117_1601"`) : élargissement `CHECK` (`SECOPS`, `BU_LEAD`, `ONTOLOGY_LEAD`), `org_units.ontology_lead_user_ids_jsonb` + contraintes `BU`, index partiel `ix_audit_ledger_org_unit_created_at` (`249` L). |
| `packages/orcia-core/src/orcia_core/permissions/{org_delegation,org_delegation_scope,org_delegation_invitations}.py` | Création | Domaine pur `AD-19` de délégation sous-arbre `BU_LEAD` / `TEAM_LEAD`, calcul des capacités par nœud (`can_*`), garde anti-éviction `422`, interdiction suppression BU racine `403`, et contrôle d'invitation scopée sans escalade (`166`, `228`, `106` L). |
| `packages/orcia-core/src/orcia_core/permissions/{role_matrix,models,org_hierarchy,iam_accounts,evaluator,errors,_error_catalog}.py` | Modification | 7e rôle officiel `ONTOLOGY_LEAD`, propagation `ontology_lead_user_ids` / `ontology_led_bu_ids`, erreurs RFC 9457 bilingues, uniformisation `BU_LEAD` / `BU_DIRECTOR`. |
| `packages/orcia-core/src/orcia_core/bootstrap/_internal/{sql_org_ontology_lead_sync,sql_org_units,sql_org_units_queries,sql_iam_accounts,sql_local_auth}.py` | Création / Modif. | Sync bidirectionnelle auto-nettoyante B1 (`org_units.ontology_lead_user_ids_jsonb ↔ iam_accounts.roles_jsonb`) et hydratation multi-rôles. |
| `packages/orcia-core/src/orcia_core/audit_finops/{models,outbox_subscriber,_internal/sql_audit_ledger_mappers}.py` | Modification | Filtrage SQL `audit_ledger` par `(allowed_workspace_ids, allowed_org_unit_ids, include_null_workspace)` et propagation `org_unit_id`. |
| `apps/api/src/orcia_api/routers/{org_unit_invitations,_org_units_delegation_helpers,_org_units_evaluator_ops,_org_units_audit,_org_units_helpers,org_units,iam_accounts,_iam_accounts_audit,_iam_accounts_routes_helpers,_iam_accounts_passwords,_auth_pg_helpers,_finops_auth_guards,audit_ledger}.py` | Création / Modif. | Endpoint `POST /api/v1/org-units/invite-user` (`293` L), confinement `org_units` + booléens `can_*`, verrouillage `iam_accounts` (`PLATFORM_ADMIN`/`SECOPS`), écriture `audit_ledger` avec `org_unit_id`, correction `hydrate_user_identity_from_pg` (`platform_role`), filtrage `enforce_audit_read_access` (tous fichiers `< 300` L). |
| `packages/api-client/` | Régénération | Contrat OpenAPI 3.1 `0-diff` et wrapper `inviteOrgUnitUser` dans `catalogAndPermissions.ts`. |
| `packages/ui/` & `apps/web/` | Création / Modif. | Entrée gauche `Mon Organisation` (`/organization`) sous `Mes Espaces`, `/settings` à 5 onglets (redirection `?tab=organization`), `InviteOrganizationUserModal` (`236` L), sélecteur `Référents Glossaire` sur BU, masquage de `Plateforme entière` / `ALL` sur `/activity` hors `PLATFORM_ADMIN`/`SECOPS`. |
| `tests/{unit,security,integration}/...` & `apps/web/src/__tests__/story-20-1-*` | Création / Modif. | Couverture complète des scénarios `Martin Pecheur BU_LEAD`, `pascal.lacdap@orcia.ia TEAM_LEAD`, `ONTOLOGY_LEAD`, isolation audit et survie `F5`. |

### 3.2 Résultats Chiffrés, Métriques & Qualité
- **Couverture de tests** : **96,93 %** sur les modules Story 20.1 (`org_delegation` `99 %`, `org_delegation_scope` `96 %`, `org_delegation_invitations` `100 %`, `role_matrix` `94 %`, `sql_audit_ledger_mappers` `99 %` ; `31` tests ciblés passés).
- **Qualité statique & Architecture** :
  - `ruff check .` & `ruff format --check .` : `0` erreur (`1077` fichiers formatés).
  - `mypy --strict packages/orcia-core/src apps/api/src apps/worker/src` : `0` erreur (`457` fichiers).
  - `lint-imports` : `5` contrats respectés, `0` violation (`540` fichiers analysés).
  - `lint_spine.py` : `"ok": true, "total_findings": 0`.
  - `export_openapi.py --check` : `0-diff`.
  - `pnpm site:check` : `64/64` capacités live couvertes, `0` erreur.

### 3.3 Validation sur la Pyramide des Tests (`AD-17`)
- **Couche 1a & 1b (`pytest` + `Vitest`)** : `tests/unit` & `tests/security` `100 %` verts ; `pnpm turbo run lint typecheck test` `9/9` tâches vertes (`35` fichiers / `146` tests `@orcia/web` dont `story-20-1-mon-organisation-and-scoped-activity.test.tsx` avec survie `F5`).
- **Couche 2 (`testcontainers` PostgreSQL 18)** : `4 passed` (`test_story_20_1_org_delegation_and_audit_postgres18.py`, `test_story_17_2`, `test_story_17_3`), incluant `alembic upgrade head -> downgrade 20261117_1601 -> upgrade head` et vérifications `HTTP ➔ SELECT PG18`.
- **Couche Sécurité (`tests/security/test_story_20_1_delegation_and_audit_isolation.py`)** : anti-escalade `PLATFORM_ADMIN`/`SECOPS`, confinement latéral inter-BU et rejet `OBSERVER` `403`.
