# 2026-11-15 — Blocage LastPass Combobox/Modales, Modale « Matrice des 6 Rôles », Synchronisation Rôle SecOps (`iam_accounts` ↔ Session/RBAC) & Hiérarchie Visuelle Unité (`BGPN` / `StatusBadge`)

- **Date** : 2026-11-15
- **Story / Clé Sprint** : `2026-11-15-anti-lastpass-matrice-roles-modale-sync-secops-et-hierarchie-bu` (`Ajustement Transverse IAM / UX / Sécurité RBAC`)
- **Capacité(s)** : `CAP-050`, `CAP-051`, `CAP-058` — classification : `ux | hygiène | feature`
- **Auteur / Contexte** : Retours utilisateur + arbitrages UX validés (Sally 🎨 & Winston 📐) suite à l'usage réel des écrans `Configuration > Organisation` et `Configuration > Comptes & Habilitations` :
  1. Empêcher LastPass et les extensions de gestionnaires de mots de passe de se déclencher sur les champs de recherche d'utilisateur/responsable/collaborateur et les modales Organisation/IAM.
  2. Désencombrer `Comptes & Habilitations` en transformant le bloc documentaire statique « Matrice des 6 Rôles Officiels de la Plateforme » en **modale d'aide à la demande** (`Voir la matrice des 6 rôles` depuis l'annuaire et la modale d'attribution de compte, Choix A1 validé), ne laissant que 2 blocs opérationnels sur la page.
  3. Corriger le blocage en consultation seule de `Exceptions & Isolation de Périmètre (SecOps)` lorsqu'un utilisateur détient le rôle `SECOPS` dans `iam_accounts` (`Romain Esnault` : `['PLATFORM_ADMIN', 'SECOPS']` en base, mais session/RBAC restreints à `PLATFORM_ADMIN`).
  4. Re-hiérarchiser la ligne d'unité organisationnelle (`Structure de l'Organisation`) en mettant en valeur le nom (`BGPN`) plutôt que son type (`Direction / BU`) et son responsable via un `StatusBadge` `cobalt` pastel et un badge responsable `neutral` (Choix A2 validé).
- **Commits associés** : *En cours d'implémentation locale*

---

## 1. Analyse du Besoin & Étude d'Impact Tech Lead (Pré-Implémentation)

### 1.1 Contexte & Problématique
1. **Point 1 — Menu LastPass sur la recherche de membre / responsable** :
   - Sur `OrciaKnownUserCombobox` (`Créer une unité organisationnelle`, `Membres d'une unité`), malgré `autoComplete="off"` et `data-lpignore="true"`, LastPass sur `localhost` affiche sa liste d'identifiants mémorisés (`tom1@gmail.com`, `resnault`).
   - Causes techniques observées : `<input type="text">` sans attribut `name` explicite, placeholders contenant les mots déclencheurs `"Identifiant"`, `"e-mail"` et l'exemple `claire.martin@entreprise.fr`, plus injection Shadow DOM (`data-lastpass-infield`, `data-lastpass-root`) non ciblée par la règle CSS historique `tokens.css:L946-L955`.
2. **Point 2 — Bloc documentaire « 2. Matrice des 6 Rôles Officiels » (Choix A1 validé)** :
   - `IamNativeRoleMatrixCard` est 100 % statique/documentaire (aucune mutation ni saisie) mais repousse tout en bas de page la section opérationnelle `Exceptions & Isolation de Périmètre (SecOps)`.
   - Solution retenue : déplacement dans une modale accessible à la demande (`IamRoleMatrixReferenceModal`), déclenchable depuis un bouton secondaire dans l'en-tête de `1. Annuaire des Comptes` et directement dans `IamAccountModal`, afin que la page ne conserve que `1. Annuaire des Comptes & Attribution des Rôles` et `2. Exceptions & Isolation de Périmètre (Avancé — SecOps)`.
3. **Point 3 — Blocage SecOps malgré attribution dans l'annuaire** :
   - Vérification directe PostgreSQL locale (`users` + `iam_accounts`) : `Romain Esnault` a `users.platform_role = 'PLATFORM_ADMIN'` et `iam_accounts.roles_jsonb = ['PLATFORM_ADMIN', 'SECOPS']`.
   - Triple désynchronisation détectée :
     1. *Écriture IAM vs cache session backend* : `PATCH /api/v1/settings/iam/accounts/{id}` (`iam_accounts.py` -> `sql_iam_accounts.py`) met à jour `iam_accounts.roles_jsonb` sans resynchroniser `UserIdentity` dans `AuthAndOrganizationService` en mémoire.
     2. *Jointure SQL & Moteur RBAC* : `load_local_auth_candidate_from_postgres18` / `load_auth_candidate_by_id_from_postgres18` (`sql_local_auth.py`) joignent uniquement `LOWER(i.email) = LOWER(u.email)` (manquant `principal_id`) et **surtout**, côté moteur RBAC `HierarchicalRbacService.delegate_grant` (`hierarchical_rbac.py:L268-L272`), `delegator_roles` n'inspecte que `delegator.platform_role` et `delegator.human_profile_archetype`, ignorant `delegator.roles` (`iam_accounts.roles_jsonb`) !
     3. *Frontend* : `SettingsIamOrganizationSection.tsx` vérifie uniquement `useAuthSessionStore` (`roles` / `activeHat`) et ne relance pas `hydrateSession({ force: true })` après édition de l'annuaire.
4. **Point 4 — Type `Direction / BU` écrasant le nom `BGPN` (Choix A2 validé)** :
   - Dans `SettingsOrganizationUnitRow.tsx`, les badges `Direction / BU` (`org-unit-kind-badge-*`) et `Responsable : ...` (`org-unit-lead-badge-*`) utilisent `StatusBadge` avec `tone="cobalt"`. Or dans `StatusBadge.tsx:L20-L24`, `cobalt` est le seul ton plein à fond bleu primaire `#2563EB` (identique au CTA `+ Nouvelle unité`), éclipsant visuellement `<strong>BGPN</strong>`.

### 1.2 Exploration, Analyse d'Impact GitNexus, Factorisation & Dette Technique
- **Analyse d'Impact GitNexus (`gitnexus_impact`, `repo: "/home/romain/Documents/Projects/ORCIA"`, `direction: "upstream"`)** :
  - `OrciaKnownUserCombobox` (`packages/ui/src/primitives/OrciaKnownUserCombobox.tsx`) : `542` symboles impactés (`379` directs `d=1`, `143` processus, `20` modules — risque `CRITICAL`). Audit confirmé dans `story-17-2-org-hierarchy-and-modals.test.tsx` : tous les tests ciblent `getByTestId(...)`, aucun n'utilise `getByRole('combobox')`, donc la bascule `type="search"` est sans rupture.
  - `rehydrate_user_from_pg_by_id` (`apps/api/src/orcia_api/routers/_auth_pg_helpers.py`) : `322` symboles impactés (`176` directs — risque `CRITICAL`). Factorisation d'un helper dédié `sync_auth_service_user_by_email_from_pg` sans modifier le contrat des appelants existants.
  - `StatusBadge` (`packages/ui/src/primitives/StatusBadge.tsx`) et `IamNativeRoleMatrixCard` (`apps/web/src/features/admin/iam/IamNativeRoleMatrixCard.tsx`) : modification purement visuelle / déplacement dans un composant modale réutilisable ; zéro assertion CSS cassée dans `story-17-2` ni `story-17-3`.
- **Contrôle de volumétrie (< 350–400 L par fichier)** :
  - `IamAccountsDirectoryCard.tsx` (`221` L), `SettingsIamOrganizationSection.tsx` (`331` L), `IamAccountModal.tsx` (`336` L), `SettingsOrganizationUnitRow.tsx` (`214` L), `_auth_pg_helpers.py` (`335` L), `iam_accounts.py` (`354` L), `sql_local_auth.py` (`298` L).
  - La modale de référence des 6 rôles est isolée dans un nouveau composant dédié (`IamRoleMatrixReferenceModal.tsx`, `< 120` L) plutôt que d'alourdir `SettingsIamOrganizationSection.tsx` au-delà de `360` lignes.

---

## 2. Plan d'Implémentation

### 2.1 Schéma de Données & Migrations Alembic (`infra/migrations/versions/`)
- Aucune migration Alembic requise : les colonnes `users.platform_role` et `iam_accounts.roles_jsonb` / `principal_id` / `email` existent déjà (`20261111_1703`).

### 2.2 Noyau Métier Hexagonal, Orchestration & Workers (`packages/orcia-core/`)
- `packages/orcia-core/src/orcia_core/bootstrap/_internal/sql_local_auth.py` :
  - Élargir la jointure SQL vers `iam_accounts` pour matcher `LOWER(i.email) = LOWER(u.email) OR LOWER(i.principal_id) = LOWER(u.email)` (via sous-requête / priorité stricte à 1 ligne active) afin de garantir l'alignement même si l'email IAM ou principal diffère légèrement.
- `packages/orcia-core/src/orcia_core/permissions/hierarchical_rbac.py` :
  - Factoriser un helper interne pur `_effective_identity_roles(user: UserIdentity) -> tuple[str, ...]` combinant `user.platform_role`, `*user.roles`, et `"SECOPS"` si `user.human_profile_archetype == "SECOPS"`, puis l'utiliser dans `resolve_effective_verbs` et `delegate_grant` afin qu'un utilisateur ayant reçu `SECOPS` (ou tout autre rôle officiel) dans `iam_accounts.roles_jsonb` dispose réellement des verbes et du droit d'éditer les exceptions SecOps côté API.

### 2.3 Couche Backend API, Sécurité & Contrats (`apps/api/`, `packages/api-client/`)
- `apps/api/src/orcia_api/routers/_auth_pg_helpers.py` & `apps/api/src/orcia_api/routers/iam_accounts.py` :
  - Ajouter `sync_auth_service_user_by_email_from_pg` (réutilisation de `load_local_auth_candidate_from_postgres18` + `user_identity_from_candidate` + `auth_svc.register_user`) et l'appeler après `POST`/`PATCH`/`DELETE /api/v1/settings/iam/accounts` pour synchroniser instantanément les rôles en RAM et dans `/api/v1/auth/session` / `/refresh` / `resolve_request_user`.
  - Dans `_auth_session_routes.py`, garantir que `hydrate_user_identity_from_pg` réenregistre l'identité hydratée dans `svc` sur `/session` et `/refresh`.

### 2.4 Interface Utilisateur & Expérience (`packages/ui/`, `apps/web/`)
- **Anti-LastPass** :
  - `packages/ui/src/styles/tokens.css` : normaliser `input[type="search"]` et étendre les sélecteurs anti-extensions (`[data-lastpass-infield]`, `[data-lastpass-root]`, `[id^="__lpform_"]`, `com-1password-button`).
  - `OrciaKnownUserCombobox.tsx`, `OrciaSearchableSelect.tsx`, `DesignSystemControls.tsx` (`OrciaInput`), `CreateOrgUnitModal.tsx`, `ManageOrgUnitMembersModal.tsx`, `IamAccountModal.tsx` : passer les combobox en `type="search"` avec `name` neutre de filtrage, sécuriser les attributs (`autoComplete`, `data-lpignore`, `data-1p-ignore`, `data-bwignore`, `data-protonpass-ignore`, `data-form-type="other"`) et supprimer les mots/motifs de login (`Identifiant`, `e-mail`, `@`) des placeholders de recherche dans `organization_modals_labels.ts` (`FR` & `EN`).
- **Modale Matrice des 6 Rôles (Choix A1)** :
  - Créer `apps/web/src/features/admin/iam/IamRoleMatrixReferenceModal.tsx` (`z-[60]`, `Escape` isolé, fermeture clic fond/bouton).
  - Retirer le rendu inline de `IamNativeRoleMatrixCard` dans `SettingsIamOrganizationSection.tsx`, renuméroter les exceptions en `2. Exceptions & Isolation de Périmètre (Avancé — SecOps)` dans `iam_accounts_labels.ts`, et câbler le bouton `Voir la matrice des 6 rôles` dans `IamAccountsDirectoryCard.tsx` et `IamAccountModal.tsx`.
- **Déverrouillage SecOps UI** :
  - Dans `apps/web/src/stores/authSessionStore.ts` (`hydrateSession({ force?: boolean })`) et `SettingsIamOrganizationSection.tsx`, forcer `hydrateSession({ force: true })` après mutation annuaire IAM et dériver `currentAccountRoles` depuis les comptes `ACTIVE` correspondant à l'utilisateur connecté.
- **Hiérarchie visuelle Unité (Choix A2)** :
  - `packages/ui/src/styles/tokens.css` & `packages/ui/src/primitives/StatusBadge.tsx` : passer `cobalt` en pastel (`--color-badge-cobalt-bg` / `-fg` / `-border`, clair & sombre).
  - `apps/web/src/routes/SettingsOrganizationUnitRow.tsx` : agrandir/renforcer le nom (`text-base font-semibold`, `data-testid="org-unit-name-{id}"`) et passer `org-unit-lead-badge-{id}` en `tone="neutral"`.

### 2.5 Analyse d'Impact sur la Pyramide des Tests (`AD-17`)
- **Couche 1a (`pytest`) & 1b (`Vitest`)** :
  - Tests `@orcia/ui` : attributs anti-LastPass `OrciaKnownUserCombobox` / `OrciaSearchableSelect` (`type="search"`, `name` neutre) et tokens pastel de `StatusBadge` (`cobalt`).
  - Tests `@orcia/web` (`story-17-3-iam-accounts-matrix-and-secops-drawer.test.tsx`, `story-17-2-org-hierarchy-and-modals.test.tsx`, `i18n-and-shell.test.tsx`, `zero-dead-buttons-and-silent-catches-audit.test.tsx`) : ouverture/fermeture de la modale Matrice depuis l'annuaire ET depuis `IamAccountModal`, déverrouillage immédiat de `2. Exceptions & Isolation SecOps` après ajout du rôle `SECOPS` + survie `F5`, mise en valeur `org-unit-name-*` et placeholders sans motif login.
  - Tests unitaires & PG18 `testcontainers` Python (`test_story_17_3_iam_accounts_and_role_matrix.py`, `test_story_17_3_iam_accounts_and_secops_postgres18.py`) : sync `iam_accounts` $\rightarrow$ `UserIdentity.roles` $\rightarrow$ `/auth/session` + délégation `POST /settings/iam/grants` avec rôle `SECOPS` issu de `iam_accounts`.
- **Couche 3 (`lint-imports`, `mypy`, `ruff`, `lint_spine.py`) & Couche 5 (`Playwright E2E`)** :
  - Exécution de `e2e/07-spaces-org-and-workspace-persistence.spec.ts` et `e2e/11-screens-smoke-without-server-errors.spec.ts` sur pile éphémère isolée (`3101`/`8100`).

---

## 3. Bilan des Modifications & Résultats (Post-Implémentation)

### 3.1 Inventaire des Fichiers Créés & Modifiés

| Couche | Fichier | Nature | Rôle / Détail | Volumétrie |
| :--- | :--- | :--- | :--- | :--- |
| **Noyau (`orcia-core`)** | `packages/orcia-core/src/orcia_core/bootstrap/_internal/sql_local_auth.py` | Modifié | Jointure `LEFT JOIN LATERAL` `users ↔ iam_accounts` (`email` / `principal_id`) et déduplication `iam_roles_jsonb` lorsque `status` est `ACTIVE` | `318` L |
| **Noyau (`orcia-core`)** | `packages/orcia-core/src/orcia_core/permissions/hierarchical_rbac.py` | Modifié | Extraction du helper pur `_effective_identity_roles(user)` et câblage dans `resolve_effective_verbs` & `delegate_grant` (`DEBT-RBAC-SPLIT-01` ouvert) | `485` L |
| **API (`apps/api`)** | `apps/api/src/orcia_api/routers/_auth_pg_helpers.py` | Modifié | Ajout de `resolve_app_db_engine(request)`, `sync_auth_service_user_by_email_from_pg(...)` et resynchronisation RAM `auth_svc.register_user` dans `hydrate_user_identity_from_pg` | `377` L |
| **API (`apps/api`)** | `apps/api/src/orcia_api/routers/_auth_session_routes.py` | Modifié | Ré-enregistrement de l'identité hydratée en RAM lors de `_rotate_refresh_and_hydrate` (`/refresh`) | `238` L |
| **API (`apps/api`)** | `apps/api/src/orcia_api/routers/iam_accounts.py` | Modifié | Appel à `await sync_auth_service_user_by_email_from_pg` après `POST /accounts`, `PATCH /accounts/{id}` et `DELETE /accounts/{id}` | `365` L |
| **Design System (`@orcia/ui`)** | `packages/ui/src/styles/tokens.css` | Modifié | Tokens `--color-badge-cobalt-{bg,fg,border}` clair/sombre pastel, normalisation `input[type="search"]`, `.text-base`, `.orcia-ds-btn-sm`, masquage sélecteurs extensions (`[data-lpignore="true"]`, `[id^="__lpform_"]`, `com-1password-button`) | — |
| **Design System (`@orcia/ui`)** | `packages/ui/src/primitives/StatusBadge.tsx` | Modifié | Ton `cobalt` migré vers les CSS variables pastel sémantiques (`0` couleur hex/rgba en dur) | `78` L |
| **Design System (`@orcia/ui`)** | `packages/ui/src/primitives/OrciaKnownUserCombobox.tsx` | Modifié | Passage en `type="search"`, `name="orcia_directory_filter_q"` et attributs anti-autofill (`data-lpignore`, `data-1p-ignore`, `data-bwignore`, `data-protonpass-ignore`, `data-form-type="other"`) | `307` L |
| **Design System (`@orcia/ui`)** | `packages/ui/src/primitives/OrciaSearchableSelect.tsx` | Modifié | Passage en `type="search"`, `name="orcia_select_filter_q"` et attributs anti-autofill homogènes | `286` L |
| **Design System (`@orcia/ui`)** | `packages/ui/src/primitives/DesignSystemControls.tsx` | Modifié | Ajout `size="sm"` sur `OrciaButton` (`.orcia-ds-btn-sm`) et valeurs par défaut non-login anti-autofill sur `OrciaInput` (hors liste d'exception `LOGIN_AUTOCOMPLETE_TOKENS`) | `362` L |
| **Frontend (`apps/web`)** | `apps/web/src/i18n/locales/organization_modals_labels.ts` | Modifié | Libellés/placeholders neutres anti-LastPass FR/EN (`leadPlaceholder`, `addMemberPlaceholder`) | `235` L |
| **Frontend (`apps/web`)** | `apps/web/src/i18n/locales/iam_accounts_labels.ts` | Modifié | Libellés `openRoleMatrixCta` / `closeRoleMatrixCta`, retrait du préfixe `"2. "` de la matrice et renumérotation `secopsDrawer` en `2. Exceptions & Isolation de Périmètre (Avancé — SecOps)` | `377` L |
| **Frontend (`apps/web`)** | `apps/web/src/features/admin/iam/IamRoleMatrixReferenceModal.tsx` | **Créé** | Modale de référence accessible (`role="dialog"`, `z-[60]`, `Escape` isolé, `data-testid="iam-role-matrix-modal"`) encapsulant la matrice des 6 rôles | `96` L |
| **Frontend (`apps/web`)** | `apps/web/src/features/admin/iam/IamAccountsDirectoryCard.tsx` | Modifié | Bouton secondaire `iam-open-role-matrix-modal-btn` câblé sur `onOpenRoleMatrix` (prop obligatoire) | `234` L |
| **Frontend (`apps/web`)** | `apps/web/src/features/admin/iam/IamAccountModal.tsx` | Modifié | Lien/bouton `iam-modal-open-role-matrix-btn` vers la matrice en modale + `name` neutres (`iam_member_full_name`, `iam_member_directory_ref`) et attributs anti-autofill | `357` L |
| **Frontend (`apps/web`)** | `apps/web/src/features/admin/organization/CreateOrgUnitModal.tsx` | Modifié | Attributs neutres (`org_unit_title`, `org_unit_short_code`) et blocage extensions | `304` L |
| **Frontend (`apps/web`)** | `apps/web/src/features/admin/organization/EditOrgUnitModal.tsx` | Modifié | Attributs neutres et blocage extensions sur l'édition d'unité | `187` L |
| **Frontend (`apps/web`)** | `apps/web/src/features/admin/organization/OrgUnitInlineCreateMemberModal.tsx` | Modifié | Attributs neutres et blocage extensions sur la création rapide de membre | `167` L |
| **Frontend (`apps/web`)** | `apps/web/src/routes/SettingsOrganizationUnitRow.tsx` | Modifié | Mise en valeur typographique du nom (`<strong data-testid="org-unit-name-..." className="text-base font-semibold tracking-tight">`), badge responsable passé en `tone="neutral"`, badge type conservé en `tone="cobalt"` pastel | `220` L |
| **Frontend (`apps/web`)** | `apps/web/src/routes/SettingsIamOrganizationSection.tsx` | Modifié | Suppression de l'encart inline `IamNativeRoleMatrixCard`, montage de `IamRoleMatrixReferenceModal` et resynchronisation `hydrateSession({ force: true })` après mutation IAM | `351` L |
| **Frontend (`apps/web`)** | `apps/web/src/stores/authSessionStore.ts` | Modifié | Option `hydrateSession({ force?: boolean })` sans repasser `isHydrating: true` sur session authentifiée + résolution des rôles IAM actifs (`currentAccountRoles`) | `308` L |
| **Tests (Backend)** | `tests/unit/test_story_17_3_iam_accounts_and_role_matrix.py` | Modifié | Test unitaire `test_story_17_3_secops_delegation_authorized_via_iam_roles` | `444` L |
| **Tests (Backend PG18)** | `tests/integration/api/_story_17_3_fixtures.py` | **Créé** | Extraction des fixtures partagées `testcontainers` PostgreSQL 18 pour Story 17.3 | `115` L |
| **Tests (Backend PG18)** | `tests/integration/api/test_story_17_3_iam_accounts_and_secops_postgres18.py` | Modifié | Test vertical PG18 `test_iam_admin_secops_elevation_vertical_postgres18` (`HTTP -> SQL -> RAM -> delegate_grant`) | `393` L |
| **Tests (Frontend & Mocks)** | `packages/ui/src/__tests__/status-badge-and-anti-lastpass-inputs.test.tsx`, `apps/web/src/__tests__/vitest.setup.ts`, `apps/web/src/__tests__/vitestIamMockHandlers.ts`, `story-17-3-iam-accounts-matrix-and-secops-drawer.test.tsx`, `story-17-2-org-hierarchy-and-modals.test.tsx`, `i18n-and-shell.test.tsx` | Créé / Modifiés | Couverture Direction C pastel cobalt, attributs anti-LastPass, ouverture/fermeture modale matrice et mock session synchronisé sur `getVitestIamAccounts()` | `71` L (UI test) |
| **Gouvernance & Docs** | `docs/implementation-artifacts/sprint-status.yaml`, `docs/product/capabilities.yaml`, `docs/implementation-artifacts/tech-lead-reports/README.md` | Modifiés | Enregistrement `DEBT-RBAC-SPLIT-01`, mise à jour `CAP-050` / `CAP-051` / `CAP-058` et indexation du rapport | — |

### 3.2 Gouvernance Technique, Dette & Analyse GitNexus
- **Volumétrie & Arbitrage** : 19/20 fichiers applicatifs modifiés respectent le seuil `< 380` lignes ; `hierarchical_rbac.py` est passé de `450` L à `485` L (+35 L). Conformément à l'arbitrage validé, la modification reste chirurgicale et le ticket dédié **`DEBT-RBAC-SPLIT-01`** (`P2`, `epic-8`) a été ouvert dans [sprint-status.yaml](file:///home/romain/Documents/Projects/ORCIA/docs/implementation-artifacts/sprint-status.yaml).
- **Indexation & Impact GitNexus (`npx gitnexus analyze` + `gitnexus_detect_changes`)** :
  - Graphe réindexé (`Repository indexed successfully (43.8s)`) : **`25,474` nodes**, **`44,411` edges**, **`389` clusters**, **`1,293` flows**.
  - Scope `unstaged` sur `/home/romain/Documents/Projects/ORCIA` : `changed_count: 85` symboles, `affected_count: 31` flux impactés, `changed_files: 30`, `risk_level: "critical"` (incluant la chaîne critique Auth/IAM/RBAC).

### 3.3 Vérifications Automatisées (5 Couches `AD-17` & Portes Qualité)
- **Qualité & Architecture Python** :
  - `.venv/bin/ruff format --check packages apps tests` : **PASS** (`451 files already formatted`).
  - `.venv/bin/ruff check packages apps tests` : **PASS** (`All checks passed!`).
  - `.venv/bin/lint-imports` : **PASS** (`Contracts: 5 kept, 0 broken`).
  - `.venv/bin/mypy --strict packages/orcia-core packages/orcia-connectors apps/api apps/worker` : **PASS** (`Success: no issues found in 341 source files`).
  - `.venv/bin/python .agent/skills/bmad-architecture/scripts/lint_spine.py --workspace docs/planning-artifacts/architecture/architecture-ORCIA-2026-10-24` : **PASS** (`{"ok": true, "total_findings": 0}`).
  - `.venv/bin/pytest tests/unit/test_codebase_architectural_anti_patterns_audit.py -q` : **PASS** (`4 passed`).
- **Tests Unitaires, Intégration PG18 & Sécurité Backend** :
  - `.venv/bin/pytest tests/unit/test_story_17_3_iam_accounts_and_role_matrix.py tests/unit/test_epic_8_settings_rbac_llm_studio_and_wizards.py tests/unit/test_auth_pg_rehydration_after_reload.py tests/security/test_api_security_baseline.py tests/integration/api/test_story_17_3_iam_accounts_and_secops_postgres18.py tests/integration/api/test_auth_pg_rehydration_postgres18.py -q` : **PASS** (`50 passed in 37.13s`).
- **Frontend (`@orcia/ui` & `apps/web`) & E2E Playwright** :
  - `pnpm --filter @orcia/ui test` : **PASS** (`23/23` suites, `97/97` tests).
  - `pnpm --filter @orcia/web exec playwright test e2e/07-spaces-org-and-workspace-persistence.spec.ts e2e/11-screens-smoke-without-server-errors.spec.ts --reporter=list` : **PASS** (`3 passed, 3 skipped (51.0s)` — 3 cas desktop ignorés sur le projet `mobile-companion`).
  - `pnpm turbo run lint typecheck test` & synchronisation du catalogue vivant (`scripts/check_implementation_docs.py`, `pnpm site:sync`, `pnpm site:check`) : exécutés après la mise à jour finale des documents et du manifeste.
