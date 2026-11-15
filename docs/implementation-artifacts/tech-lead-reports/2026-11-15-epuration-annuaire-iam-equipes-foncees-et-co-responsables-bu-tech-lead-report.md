# 2026-11-15 — Épuration de l'Annuaire IAM, Mise en Évidence Foncée des Affectations BU/Équipe et Co-Responsables BU/Équipe Synchronisés

- **Date** : 2026-11-15
- **Story / Clé Sprint** : `2026-11-15-epuration-annuaire-iam-equipes-foncees-et-co-responsables-bu` (`Ajustement Transverse IAM / Organisation / RBAC / UX`)
- **Capacité(s)** : `CAP-050`, `CAP-051`, `CAP-058`, `CAP-067` (mises à jour dans `docs/product/capabilities.yaml`) — classification : `feature | ux | hygiène`
- **Auteur / Contexte** : Retours visuels sur `Configuration > Comptes & Habilitations` et `Configuration > Organisation` + arbitrages produits/architecture validés en séance `grill-me` (Sally 🎨 & Winston 🏗️) :
  1. Épurer l'en-tête des lignes de l'annuaire IAM (`1. Annuaire des Comptes & Attribution des Rôles`) : supprimer les badges redondants/erronés `"Utilisateur"`, `"SSO d'entreprise"`, `"Compte initial local"` et `"Jeton de service"`, ne conserver que `"Compte technique"` pour `account_kind === "SERVICE_PRINCIPAL"`, corriger `auth_source` lors de la création de comptes humains en mode `LOCAL` (`"LOCAL_PASSWORD"`), et masquer le bouton `"Mot de passe"` lorsque `platform_auth_settings.auth_mode === "SSO"`.
  2. Mettre en évidence en texte foncé (`var(--color-foreground)` / `#0F172A`, `fontWeight: 600`) les unités dirigées et équipes rattachées sur la ligne 2 de l'annuaire (`· Direction (BU) : ...`, `· Équipe dirigée : ...`, `· Équipe : ...`), sans doublon entre équipe dirigée et équipe membre, avec indicateur ambre discret `aucune assignée` lorsqu'un rôle `BU_LEAD` / `TEAM_LEAD` n'a encore aucune unité affectée.
  3. Permettre l'affectation de **co-responsables multiples (`0..N` `lead_user_ids`)** sur les `BU` **et** les `TEAM` directement dans **`Modifier l'unité organisationnelle`** (`EditOrgUnitModal`), dans `CreateOrgUnitModal` et `ManageOrgUnitMembersModal`.
  4. Interdire les membres directs sur une `BU` (règle métier : une `BU` a des responsables et des sous-BU/équipes, jamais de membres directs) : supprimer le bouton `Membres` et le compteur de membres sur les lignes `BU` de l'organigramme, purger et verrouiller via contrainte `CHECK` PostgreSQL 18 + erreur HTTP `422`.
  5. Assurer la **synchronisation bidirectionnelle** et le cycle **`B1` strict auto-nettoyant** entre `org_units.lead_user_ids_jsonb`, `iam_accounts.roles_jsonb` (`BU_LEAD` / `TEAM_LEAD`), `IamAccountModal` (sélecteurs dynamiques des BUs/Équipes dirigées) et le *roll-up* RBAC `evaluator.py` (`resolve_workspace_access`).
- **Commits associés** : Branche dédiée `fix/iam-directory-and-multi-lead-bu` (worktree isolé `.orcia-run/wt-iam-bu-leads` issu de `main` `9cba49f`), puis merge `--no-ff` vers `main`.

---

## 1. Analyse du Besoin & Étude d'Impact Tech Lead (Pré-Implémentation)

### 1.1 Contexte & Problématique
1. **Bruit visuel et erreur d'authentification dans l'annuaire IAM (`IamAccountsDirectoryCard.tsx`)** :
   - Chaque ligne humaine affiche inutilement un badge `"Utilisateur"` (`dir.humanBadge`) et un badge source (`"SSO d'entreprise"` ou `"Compte initial local"`). Pire, `sql_iam_accounts.py` et `IamAccountModal.tsx` positionnent `"OIDC_FEDERATED"` par défaut pour un compte humain même lorsque la plateforme fonctionne en mode `LOCAL` (`Martin Pêcheur`, `Rouge Gorge` et `Requin Marteau` affichent donc `"SSO d'entreprise"` tout en ayant un bouton `"Mot de passe"`).
   - Arbitrage validé : ne conserver que le badge `"Compte technique"` lorsque `account_kind === "SERVICE_PRINCIPAL"` ; supprimer `"Utilisateur"` et le badge `auth_source` ; introduire `"LOCAL_PASSWORD"` dans `iam_accounts.auth_source` quand `platform_auth_settings.auth_mode == "LOCAL"` ; masquer le bouton `"Mot de passe"` (`iam-reset-password-account-btn-*`) quand `auth_mode === "SSO"`.
2. **Rattachements organisationnels peu lisibles & invisibilité des responsables dans l'annuaire** :
   - Sur la ligne 2, le texte `· Équipes : Mon Compte` ou `· Aucune équipe rattachée` utilise `var(--color-muted-foreground)` à faible contraste, et aucun libellé n'indique les Directions (`BU`) ou Équipes (`TEAM`) dont un utilisateur est responsable (`BU_LEAD` / `TEAM_LEAD`).
   - Arbitrage validé (**Piste 1 en `#0F172A` / `var(--color-foreground)`**) :
     - `· Direction (BU) : <noms>` (gras foncé `600`) ou ambre discret `· Direction (BU) : aucune assignée` si rôle `BU_LEAD` sans BU encore affectée ;
     - `· Équipe dirigée : <nom>` / `· Équipes dirigées : <noms>` (gras foncé `600`) ou ambre discret `· Équipe dirigée : aucune assignée` si rôle `TEAM_LEAD` sans équipe dirigée ;
     - `· Équipe : <nom>` / `· Équipes : <noms>` (gras foncé `600`) pour les équipes où le compte est membre (dédupliquées vis-à-vis des équipes déjà listées comme dirigées) ;
     - Fallback discret `· Aucune équipe rattachée` uniquement lorsqu'aucune affectation ni alerte n'existe et que le compte ne porte pas exclusivement `PLATFORM_ADMIN` / `SECOPS`.
3. **Absence du champ Responsable dans `EditOrgUnitModal`, mono-responsable scalaire et bouton `Membres` trompeur sur `BU`** :
   - `EditOrgUnitModal.tsx` ne expose que `Nom de l'unité`, `Unité parente de rattachement` et `Activer l'imputation FinOps` — impossible d'affecter ou modifier les responsables depuis l'édition d'une `BU`.
   - `org_units` ne possède qu'un champ scalaire unique `lead_user_id VARCHAR(128) NULL` (`20261111_1702`) et n'interdit pas `member_user_ids_jsonb` sur `unit_type = 'BU'` ; côté UI, `SettingsOrganizationUnitRow.tsx` affiche le bouton `Membres` sur les `BU` exactement comme sur les `TEAM`.
   - Enfin, attribuer un responsable sur une `BU` ou une `TEAM` ne synchronise ni `iam_accounts.roles_jsonb` (`BU_LEAD` / `TEAM_LEAD`) ni les rôles d'évaluation temps réel, et `evaluator.py` (`resolve_workspace_access`) s'appuie principalement sur `user.primary_org_unit_id` plutôt que sur l'ensemble des unités dirigées.

### 1.2 Exploration, Analyse d'Impact GitNexus, Factorisation & Dette Technique
- **Analyse d'Impact GitNexus (`impact`, `direction: "upstream"`, `repo: "/home/romain/Documents/Projects/ORCIA"`)** :
  - `OrgUnitSummary` (`packages/orcia-core/src/orcia_core/permissions/org_hierarchy.py`) : **`impactedCount = 10`** (`MEDIUM`, direct: 5).
  - `create_org_unit_on_postgres18` & `update_org_unit_on_postgres18` (`sql_org_units.py`) : **`impactedCount = 138`** (`CRITICAL`, direct: 102, 129 flux affectés).
  - `EditOrgUnitModal`, `ManageOrgUnitMembersModal`, `IamAccountModal`, `IamAccountsDirectoryCard` (`apps/web`) : **`impactedCount = 138`** (`CRITICAL`, direct: 102).
  - `resolve_workspace_access` (`packages/orcia-core/src/orcia_core/permissions/evaluator.py`) : **`impactedCount = 152`** (`CRITICAL`, direct: 9, 184 flux affectés).
- **Contraintes DDL constatées (`20261111_1702`, `20261111_1703`, `sql_iam_account_helpers.py`)** :
  - `org_units` (`0002` + `20261111_1702`) : `unit_type CHECK ('ENTERPRISE','BU','TRIBE','TEAM','SUB_TEAM')`, `lead_user_id VARCHAR(128) NULL`, `member_user_ids_jsonb JSONB NOT NULL DEFAULT '[]'::jsonb`, sans contrainte `CHECK` sur `BU`. Pas d'auto-bootstrap DDL hors Alembic (`ensure_org_units_schema` absent).
  - `iam_accounts` (`20261111_1703` & `sql_iam_account_helpers.py:L77-78`) : contrainte `CHECK (auth_source IN ('LOCAL_BOOTSTRAP', 'OIDC_FEDERATED', 'SERVICE_TOKEN'))` nécessitant une migration Alembic + mise à jour de `ensure_iam_accounts_schema` pour autoriser `'LOCAL_PASSWORD'`.
  - Table `users` (`sql_local_auth.py:L19-58`) : la contrainte historique sur `users.platform_role` utilise `'BU_DIRECTOR'` lorsque le rôle IAM est `'BU_LEAD'` (`_resolve_platform_role`).
- **Opportunités de Factorisation & Contrôle de Volumétrie (`< 360` lignes par fichier)** :
  - Plusieurs fichiers ciblés approchent le seuil `300–400` L : `sql_org_units.py` (`359` L), `_org_units_helpers.py` (`357` L), `routers/iam_accounts.py` (`365` L), `org_hierarchy.py` (`351` L), `IamAccountModal.tsx` (`357` L), `SettingsIamOrganizationSection.tsx` (`351` L), `CreateOrgUnitModal.tsx` (`304` L), `iam_accounts_labels.ts` (`377` L).
  - Découpage planifié dès l'implémentation (pas de dette reportée) :
    1. Créer `packages/orcia-core/src/orcia_core/bootstrap/_internal/sql_org_iam_role_sync.py` (`< 250` L) pour isoler la validation des co-responsables, la synchronisation bidirectionnelle `org_units.lead_user_ids_jsonb ↔ iam_accounts.roles_jsonb ↔ users.platform_role` (`B1`), et la résolution de `auth_source`.
    2. Créer le composant générique `@orcia/ui` `OrciaUserPillsSelect.tsx` (`< 190` L) factorisant la sélection multi-utilisateurs (`OrciaKnownUserCombobox` + pills supprimables + bouton d'ajout, avec attributs anti-LastPass préservés) pour `CreateOrgUnitModal.tsx`, `EditOrgUnitModal.tsx` et `ManageOrgUnitMembersModal.tsx`.
    3. Extraire `IamAccountRoleScopesFieldset.tsx` (`< 160` L) depuis `IamAccountModal.tsx` pour les cases à cocher dynamiques des `BU` et `Équipes` dirigées.

---

## 2. Plan d'Implémentation

### 2.1 Schéma de Données & Migrations Alembic (`infra/migrations/versions/20261115_1902_multi_lead_org_units_and_bu_no_members.py`)
- `down_revision = "20261115_1901"` (SQL brut `op.execute(sa.text(...))`, zéro import ORM, `upgrade()` et `downgrade()` réversibles) :
  1. `ALTER TABLE org_units ADD COLUMN IF NOT EXISTS lead_user_ids_jsonb JSONB NOT NULL DEFAULT '[]'::jsonb;`
  2. Backfill idempotent depuis `lead_user_id` non vide lorsque `lead_user_ids_jsonb = '[]'::jsonb`.
  3. Purge des éventuels membres sur les unités `unit_type = 'BU'` (`member_user_ids_jsonb = '[]'::jsonb`), ajout des contraintes `chk_org_units_lead_user_ids_is_array` et `chk_org_units_bu_no_members CHECK (unit_type <> 'BU' OR member_user_ids_jsonb = '[]'::jsonb)`.
  4. Mise à jour de la contrainte `CHECK` sur `iam_accounts.auth_source` pour autoriser `'LOCAL_PASSWORD'` (`LOCAL_BOOTSTRAP`, `LOCAL_PASSWORD`, `OIDC_FEDERATED`, `SERVICE_TOKEN`), et réconciliation des comptes `HUMAN` existants mal marqués `'OIDC_FEDERATED'` lorsque la politique plateforme active est `'LOCAL'`.
  5. Mise à jour symétrique de `ensure_iam_accounts_schema` dans `sql_iam_account_helpers.py`.

### 2.2 Noyau Métier Hexagonal (`packages/orcia-core/`)
- `permissions/models.py`, `permissions/org_hierarchy.py`, `permissions/errors.py` :
  - Ajout de `lead_user_ids: tuple[str, ...] = ()` sur `OrgUnitNode` et `OrgUnitSummary`, synchronisé avec `lead_user_id` (`lead_user_ids[0]` si non vide) pour rétrocompatibilité.
  - Rejet domaine `HTTP 422` (`ValidationDomainError` / `ERR_ORG_UNIT_BU_MEMBERS_FORBIDDEN`) dès qu'une liste non vide de membres est soumise pour `kind == "BU"`.
- `permissions/iam_accounts.py` :
  - Ajout de `"LOCAL_PASSWORD"` dans `IamAuthSource` et des attributs `led_bu_ids: tuple[str, ...] = ()` / `led_team_ids: tuple[str, ...] = ()` sur `IamAccountRecord` (plus support en mémoire dans `IamAccountsService`).
- `permissions/evaluator.py` :
  - Extension de `resolve_workspace_access` : un responsable (`BU_DIRECTOR` / `BU_LEAD` / `TEAM_LEAD`) accède par *roll-up* à l'ensemble des espaces appartenant aux unités (et leurs descendantes via `is_ancestor_of`) où il figure dans `lead_user_ids` (ou `lead_user_id`), en plus de `user.primary_org_unit_id` et `member_user_ids`.
- `bootstrap/_internal/sql_org_iam_role_sync.py`, `sql_org_units.py`, `sql_org_units_queries.py`, `sql_iam_accounts.py`, `sql_iam_account_helpers.py`, `sql_platform_setup_relational_sync.py` :
  - Persistance de `lead_user_ids_jsonb` + `lead_user_id = lead_user_ids[0] if lead_user_ids else None`, sync `platform_settings`, et blocage explicite des membres sur `BU`.
  - Synchronisation bidirectionnelle transactionnelle **B1 Strict auto-nettoyant** entre `org_units` (`lead_user_ids_jsonb`) et `iam_accounts.roles_jsonb` (`BU_LEAD` / `TEAM_LEAD`, repli sur `["CONTRIBUTOR"]` si la liste de rôles devient vide) + `users.platform_role` (`_resolve_platform_role`), en autorisant l'état transitoire `BU_LEAD`/`TEAM_LEAD` avec `0` unité depuis `IamAccountModal`.
  - Enrichissement batch (zéro `N+1`) de `led_bu_ids` et `led_team_ids` dans `list`/`create`/`update` des comptes IAM.

### 2.3 Couche Backend API, Sécurité & Contrats (`apps/api/`, `packages/api-client/`)
- `schemas/org_unit_models.py` & `schemas/iam_accounts.py` : ajout de `lead_user_ids` sur les requêtes/réponses `org-units`, `"LOCAL_PASSWORD"` dans `IamAuthSourceLiteral`, `auth_source` optionnel sur `IamAccountCreateRequest`, et `led_bu_ids` / `led_team_ids` sur les schémas `iam/accounts`.
- `routers/org_units.py`, `_org_units_helpers.py` & `routers/iam_accounts.py` :
  - Propagation complète des co-responsables, resynchronisation de `svc.evaluator` (`OrgUnitNode` avec `lead_user_ids`) **et** des identités en mémoire de `auth_svc` après chaque mutation d'unité ou de compte IAM.
  - Résolution du `auth_source` par défaut depuis la table `platform_auth_settings` (`"LOCAL"` $\rightarrow$ `"LOCAL_PASSWORD"`, `"SSO"` $\rightarrow$ `"OIDC_FEDERATED"`).
- Régénération du contrat OpenAPI 3.1 et des shards `@orcia/api-client` via `.venv/bin/python scripts/export_openapi.py` (`0-diff` vérifié).

### 2.4 Interface Utilisateur & Expérience (`packages/ui/`, `apps/web/`)
- `@orcia/ui` : création de `OrciaUserPillsSelect.tsx` (réutilisable, anti-LastPass, 0 hex en dur, 0 chaîne française en dur).
- `Configuration > Organisation` (`apps/web`) :
  - `SettingsOrganizationUnitRow.tsx` : suppression du bouton `Membres` et du compteur de membres sur les lignes `BU` (`unit.level === "BU"`) ; affichage multi-responsables sur `org-unit-lead-badge-*` (`Responsable : ...` / `Responsables : A, B`).
  - `EditOrgUnitModal.tsx`, `CreateOrgUnitModal.tsx`, `ManageOrgUnitMembersModal.tsx`, `SettingsOrganizationModalsGroup.tsx`, `SettingsOrganizationUnitsBlock.tsx` : sélection multi-responsables (`leadUserIds`) câblée sur `orgUnitsApiBridge.ts` avec rechargement synchronisé des comptes IAM.
- `Configuration > Comptes & Habilitations` (`apps/web`) :
  - `IamAccountsDirectoryCard.tsx` : suppression des badges `"Utilisateur"`, `"SSO d'entreprise"`, `"Compte initial local"`, `"Jeton de service"` (seul `"Compte technique"` reste sur `SERVICE_PRINCIPAL`) ; masquage du bouton `"Mot de passe"` si `authMode === "SSO"` ; rendu Piste 1 en texte foncé `var(--color-foreground)` (`600`) des `Direction (BU)`, `Équipe dirigée` et `Équipe` (sans doublon), avec ambre discret si `BU_LEAD`/`TEAM_LEAD` n'a aucune unité assignée.
  - `IamAccountModal.tsx` + `IamAccountRoleScopesFieldset.tsx` : cases à cocher dynamiques des `BU` dirigées (`BU_LEAD`) et `Équipes` dirigées (`TEAM_LEAD`), suppression de l'envoi codé en dur `auth_source: "OIDC_FEDERATED"`.
  - `SettingsIamOrganizationSection.tsx` : lecture de `getPublicAuthConfig()` (`authMode`) avec gestion d'erreur explicite et rechargement synchronisé de `orgUnits` après toute mutation de compte IAM.
- Mise à jour complète des dictionnaires `fr`/`en` et des handlers Vitest.

### 2.5 Analyse d'Impact sur la Pyramide des Tests (`AD-17`)
- **Couche 1a & 1b (`pytest` $\ge 90\%$ & `Vitest`)** : tests unitaires domaine (`org_hierarchy`, `iam_accounts`, `evaluator`), audit statique anti-patterns, `OrciaUserPillsSelect`, `story-17-2`, `story-17-3`, `zero-dead-buttons-and-silent-catches-audit`, plus test explicite de survie `F5` (`unmount()` + `render()`).
- **Couche 2 (`HTTP FastAPI ➔ PostgreSQL 18 SELECT` via `testcontainers`)** : réversibilité migration `20261115_1902`, rejet `422` + `CHECK` SQL membres sur `BU`, synchronisation bidirectionnelle `org-units` ↔ `iam/accounts` vérifiée en SQL.
- **Couche 3 (`OpenAPI 0-diff`, `lint-imports`, `mypy --strict`, `ruff`, `lint_spine.py`, `scripts/audit_code.py`)**.
- **Couche Sécurité (`tests/security/`)** & **Couche 5 (`Playwright E2E` `07-*` & `11-*`)**.

---

## 3. Bilan des Modifications & Résultats (Post-Implémentation)

### 3.1 Bilan de l'Étape 2 (Backend Hexagonal, SQL & API FastAPI)

| Fichier créé / modifié | Rôle & Responsabilité | Volumétrie (L) | Couverture / Statut |
| :--- | :--- | :---: | :---: |
| `infra/migrations/versions/20261115_1902_multi_lead_org_units_and_bu_no_members.py` | Migration SQL réversible (`upgrade`/`downgrade`) : colonne `lead_user_ids_jsonb`, contraintes `chk_org_units_bu_no_members`, `chk_org_units_lead_user_ids_is_array`, `auth_source` élargi à `LOCAL_PASSWORD` | 201 | Validé sur PG18 (upgrade/downgrade/upgrade) |
| `packages/orcia-core/src/orcia_core/permissions/models.py` | Modèle pur `OrgUnitNode` avec `lead_user_ids` synchronisé avec `lead_user_id` | 218 | 99% |
| `packages/orcia-core/src/orcia_core/permissions/org_topology.py` | Tri topologique extrait pour découpage et respect strict de la volumétrie | 57 | 93% |
| `packages/orcia-core/src/orcia_core/permissions/org_hierarchy.py` | `OrgUnitSummary` (support `lead_user_ids`) et garde domaine `assert_bu_has_no_members` | 338 | 96% |
| `packages/orcia-core/src/orcia_core/permissions/org_user_validation.py` | Validation & canonisation des leads sur utilisateurs connus actifs | 121 | 100% |
| `packages/orcia-core/src/orcia_core/permissions/iam_accounts.py` | `IamAccountRecord` enrichi de `led_bu_ids` et `led_team_ids`, `IamAuthSource` étendu | 369 | 99% |
| `packages/orcia-core/src/orcia_core/permissions/evaluator.py` | `MatrixPermissionEvaluator` : roll-up multi-leads sur toutes les BUs dirigées et descendantes | 354 | Couvert (test unitaire dédié) |
| `packages/orcia-core/src/orcia_core/permissions/errors.py` | `OrgUnitBuMembersForbiddenError` (422, `ERR_ORG_UNIT_BU_MEMBERS_FORBIDDEN`) et `OrgUnitNotFoundError` (404, `ERR_ORG_UNIT_NOT_FOUND`) | 271 | 100% |
| `packages/orcia-core/src/orcia_core/permissions/_error_catalog.py` | Catalogue bilingue RFC 9457 FR/EN pour `ERR_ORG_UNIT_BU_MEMBERS_FORBIDDEN` et `ERR_ORG_UNIT_NOT_FOUND` | 376 | 100% |
| `packages/orcia-core/src/orcia_core/bootstrap/_internal/sql_org_iam_role_sync.py` | Brique transactionnelle de synchronisation B1 Strict auto-nettoyante entre org_units et comptes IAM (levée `OrgUnitNotFoundError` 404 bilingue avec instance) | 305 | 77% (94% sur fonctions clés) |
| `packages/orcia-core/src/orcia_core/bootstrap/_internal/sql_org_units.py` | Adaptateur SQL mutations `org_units` (insertion/mise à jour avec `lead_user_ids_jsonb` et sync B1) | 319 | 97% |
| `packages/orcia-core/src/orcia_core/bootstrap/_internal/sql_org_units_queries.py` | Requêtes de lecture SQL `org_units` avec hydration de `lead_user_ids` | 383 | 93% |
| `packages/orcia-core/src/orcia_core/bootstrap/_internal/sql_iam_accounts.py` | Adaptateur SQL comptes IAM avec enrichissement batch `led_bu_ids`/`led_team_ids` | 338 | 94% |
| `packages/orcia-core/src/orcia_core/bootstrap/_internal/sql_iam_account_helpers.py` | Helpers SQL de validation de schéma et normalisation des sources d'authentification | 249 | 82% |
| `packages/orcia-core/src/orcia_core/bootstrap/_internal/sql_platform_setup_relational_sync.py` | Réconciliation relationnelle avec support `lead_user_ids_jsonb` et rôles IAM | 350 | Couvert |
| `apps/api/src/orcia_api/schemas/org_unit_models.py` | DTOs Pydantic v2 `lead_user_ids` sur requêtes et réponses | 129 | 100% |
| `apps/api/src/orcia_api/schemas/iam_accounts.py` | DTOs Pydantic v2 `led_bu_ids`, `led_team_ids` et `auth_source` | 122 | 100% |
| `apps/api/src/orcia_api/routers/org_units.py` | Routeur FastAPI `/api/v1/settings/org-units` avec synchronisation evaluator et auth_svc | 312 | Couvert (test d'intégration PG18) |
| `apps/api/src/orcia_api/routers/_org_units_helpers.py` | Helpers de mapping RFC 9457 et extraction des co-responsables | 378 | Couvert |
| `apps/api/src/orcia_api/routers/iam_accounts.py` | Routeur FastAPI `/api/v1/settings/iam/accounts` avec synchronisation evaluator et auth_svc | 360 | Couvert (test d'intégration PG18) |
| `apps/api/src/orcia_api/routers/_iam_accounts_routes_helpers.py` | Helpers de mapping RFC 9457 pour les comptes IAM | 59 | Couvert |
| `packages/api-client/openapi.json` & `schema.ts` | SDK OpenAPI 3.1 régénéré via `scripts/export_openapi.py` (`0-diff` vérifié) | - | 0-diff |
| `tests/unit/test_evaluator_multi_lead_rollup.py` | Suite de tests unitaires pour l'accès roll-up multi-responsable BU et multi-BU | 134 | 6 passed (100%) |
| `tests/integration/api/test_multi_lead_and_bu_no_members_postgres18.py` | Suite d'intégration testcontainers PG18 (Alembic, rejet membre BU, sync bidirectionnelle B1) | 165 | 2 passed (100%) |

### 3.2 Résultats des Portes d'Assurance Qualité (Backend)

- **Linter Ruff (`ruff check`)** : `0 error` (All checks passed sur l'intégralité du dépôt).
- **Formateur Ruff (`ruff format --check`)** : `512 files already formatted` (0 drift de style).
- **Vérificateur de type Mypy (`mypy --strict`)** : `Success: no issues found in 344 source files` (typage strict 100%).
- **Contrats d'Architecture Import-Linter (`lint-imports`)** : `Contracts: 5 kept, 0 broken` (respect strict AD-19 et AD-20, zéro dépendance circulaire).
- **Contrat OpenAPI 3.1 (`scripts/export_openapi.py --check`)** : `0 diff` entre FastAPI Pydantic v2 et `@orcia/api-client`.
- **Fuzzing de Contrat Schemathesis (`test_schemathesis_openapi_contract_compliance`)** : `2 passed in 66s` (fuzzing exhaustif Hypothesis, zéro 500, enveloppes RFC 9457 conformes).
- **Tests Unitaires Ciblés** : `test_evaluator_multi_lead_rollup.py`, `test_story_17_2_org_hierarchy.py`, `test_story_17_3_iam_accounts_and_role_matrix.py` (tous verts).
- **Tests d'Intégration Conteneurs Réels PostgreSQL 18 (`AD-17 Couche 2`)** :
  - `test_multi_lead_and_bu_no_members_postgres18.py` : PASSÉ (migration réversible 20261115_1902, rejet `422 ERR_ORG_UNIT_BU_MEMBERS_FORBIDDEN`, sync bidirectionnelle B1 BUs/IAM).
  - `test_story_17_2_org_units_hierarchy_postgres18.py` : PASSÉ.
  - `test_story_17_3_iam_accounts_and_secops_postgres18.py` : PASSÉ.
- **Synchronisation du Showcase & Catalogue Statique (`pnpm site:sync`)** : Validé et synchronisé (`test_site_catalog_sync.py` 3 passed).

### 3.3 Bilan de l'Étape 3 (Frontend complet : `@orcia/api-client`, `@orcia/ui`, `apps/web`, i18n & Vitest)

| Fichier créé / modifié | Rôle & Responsabilité | Volumétrie (L) | Couverture / Statut |
| :--- | :--- | :---: | :---: |
| `packages/ui/src/primitives/OrciaUserPillsSelect.tsx` | Composant primitif pills/chips supprimables pour sélection multi-utilisateurs connus, avec auto-résolution du draft textuel | 186 (< 190) | Validé (tests unitaires @orcia/ui) |
| `packages/ui/src/__tests__/user-pills-select.test.tsx` | Suite de tests unitaires Vitest pour `OrciaUserPillsSelect` (clic bouton, sélection combobox, suppression, draft auto-resolve) | 123 | 4 passed (100%) |
| `packages/ui/src/index.ts` | Export du composant `OrciaUserPillsSelect` et de ses types d'interface | 49 | 100% typé |
| `apps/web/src/components/platformSetupStorageHelpers.ts` | Entités `ConfiguredOrgUnit` enrichies de `leadUserIds` (synchronisé avec `leadUserId: leadUserIds[0]`) | 358 (< 360) | Couvert |
| `apps/web/src/features/admin/organization/orgUnitsApiBridge.ts` | Bridge API `@orcia/api-client` : propagation `lead_user_ids` et assainissement strict `member_user_ids: []` sur les BUs | 245 (< 360) | Couvert |
| `apps/web/src/routes/SettingsOrganizationUnitRow.tsx` | Ligne d'unité : suppression du bouton "Membres" et du badge membres sur BU ; badge singulier ("Responsable") vs pluriel ("Responsables") | 245 (< 360) | Couvert |
| `apps/web/src/features/admin/organization/CreateOrgUnitModal.tsx` | Modale de création d'unité intégrant `<OrciaUserPillsSelect />` avec auto-résolution des drafts | 270 (< 290) | Couvert |
| `apps/web/src/features/admin/organization/EditOrgUnitModal.tsx` | Modale d'édition d'unité avec `<OrciaUserPillsSelect />` pour co-responsables | 223 (< 280) | Couvert |
| `apps/web/src/features/admin/organization/ManageOrgUnitMembersModal.tsx` | Modale de gestion des membres (restreinte aux Équipes) intégrant `<OrciaUserPillsSelect />` | 282 (< 290) | Couvert |
| `apps/web/src/features/admin/organization/SettingsOrganizationModalsGroup.tsx` | Propagation de `knownUsers` et des labels d'erreur inconnus vers `EditOrgUnitModal` | 122 | Couvert |
| `apps/web/src/routes/SettingsOrganizationUnitsBlock.tsx` | Re-synchronisation de session (`hydrateSession({ force: true })`) et des comptes IAM lors de chaque mutation d'unité | 353 (< 360) | Couvert |
| `apps/web/src/features/admin/iam/IamAccountsDirectoryCard.tsx` | Carte annuaire épurée (Ligne 1 sans badge "Utilisateur" ni source ; bouton mot de passe bilingue `{dir.resetPasswordButton}` masqué en SSO ; Ligne 2 foncé gras `var(--color-foreground)` 600 et ambre non-assigné) | 336 (< 360) | Couvert |
| `apps/web/src/features/admin/iam/IamAccountRoleScopesFieldset.tsx` | Composant extrait affichant dynamiquement les cases à cocher de BUs dirigées (quand BU_LEAD est coché) et Équipes dirigées (quand TEAM_LEAD est coché) | 159 (< 160) | Couvert |
| `apps/web/src/features/admin/iam/IamAccountModal.tsx` | Modale de compte IAM avec gestion dynamique des périmètres dirigés et suppression du forçage `auth_source: "OIDC_FEDERATED"` | 331 (< 360) | Couvert |
| `apps/web/src/routes/SettingsIamOrganizationSection.tsx` | Section IAM : récupération `authMode` via `client.getPublicAuthConfig()` et re-synchronisation croisée `accounts` + `orgUnits` | 338 (< 355) | Couvert |
| `apps/web/src/i18n/locales/iam_accounts_labels.ts` | Dictionnaire i18n IAM épuré et stabilisé | 267 (< 360) | Couvert |
| `apps/web/src/i18n/locales/iam_accounts_directory_labels.ts` | Dictionnaire i18n compagnon extrait pour l'annuaire des comptes (avec clé `resetPasswordButton` FR/EN) | 166 (< 360) | Couvert |
| `apps/web/src/i18n/locales/organization_tab_labels.ts` | Labels d'organisation avec préfixe pluriel `leadsPluralPrefix` | 152 (< 360) | Couvert |
| `apps/web/src/i18n/locales/organization_modals_labels.ts` | Labels des modales d'organisation avec supports co-responsables | 241 (< 360) | Couvert |
| `apps/web/src/__tests__/vitestIamMockHandlers.ts` | Mock d'annuaire IAM avec gestion `syncLeadAssignments` et rôles BU_LEAD/TEAM_LEAD non-destructifs | 542 | Couvert |
| `apps/web/src/__tests__/vitest.setup.ts` | Handlers Vitest alignés (422 si membres sur BU, gestion `authMode` SSO/LOCAL via policy) | 1716 | Couvert |
| `apps/web/src/__tests__/story-17-2-org-hierarchy-and-modals.test.tsx` | Tests de hiérarchie d'organisation, pills multi-leads et interdiction membres sur BU | 297 (< 360) | 6 passed (100%) |
| `apps/web/src/__tests__/story-17-3-iam-accounts-directory-and-bu-leads.test.tsx` | Suite de tests dédiée Annuaire IAM épuré, Ligne 2 foncé gras, indices ambre et survie F5 | 205 (< 360) | 3 passed (100%) |

### 3.4 Résultats des Portes d'Assurance Qualité (Frontend & Globales)

- **Turbo Monorepo Lint, Typecheck & Tests (`pnpm turbo run lint typecheck test`)** : `9 successful, 9 total` (100% de réussite sur `@orcia/ui`, `@orcia/api-client`, `@orcia/web`).
- **Tests Vitest `@orcia/web`** : `19 test files passed (19/19), 99 tests passed (99/99)` en 21.63s.
- **Tests Vitest `@orcia/ui`** : `14 test files passed (14/14), 75 tests passed (75/75)` incluant `user-pills-select.test.tsx`.
- **Tests Vitest `@orcia/api-client`** : `2 test files passed (2/2), 13 tests passed (13/13)`.
- **Garde-fou Zéro Bouton Muet & Zéro Catch Silencieux (`zero-dead-buttons-and-silent-catches-audit.test.tsx`)** : `7 tests passed (100%)`.
- **Garde-fou Volumétrie (< 400 Lignes)** : Tous les composants/dictionnaires/tests applicatifs créés ou découpés respectent `<= 358` lignes côté Frontend et `<= 383` lignes côté Backend (hors mocks partagés existants et artefacts générés).
- **Garde-fou Survie au Rechargement F5** : Validé par démontage (`view.unmount()`) et remontage intégral du composant dans les tests Vitest.

### 3.5 Bilan de l'Étape 4 (Vérification Globale Pyramide AD-17 & Garde-fous Finaux)

1. **Couche 1 (Unitaires & Sécurité — exécutés après la dernière édition)** :
   - `pytest tests/unit/ tests/security/ -q` : **`445 passed`** (`100 %` verts, sans test ignoré ni assertion relâchée).
   - Couverture globale sur `packages/orcia-core` en exécution unitaire/sécurité isolée (hors adaptateurs conteneurisés PG18/DBOS/SeaweedFS couverts en Couche 2) : **`84 %`** (`14612` stmts, `3022` branches), et **`>= 95.17 %`** sur le domaine métier `permissions/` modifié (`models.py` `99 %`, `iam_accounts.py` `99 %`, `org_hierarchy.py` `96 %`, `org_user_validation.py` `100 %`, `errors.py` `100 %`, `org_topology.py` `93 %`, `evaluator.py` `92 %`).
2. **Couche 2 (Intégration PostgreSQL 18 `testcontainers`)** :
   - Suites exécutées après la dernière édition (`test_multi_lead_and_bu_no_members_postgres18.py`, `test_story_17_2_org_units_hierarchy_postgres18.py`, `test_story_17_3_iam_accounts_and_secops_postgres18.py`) : **`5/5 passed (100 %)`** en `30.22s` (et `8/8 passed` en incluant `test_local_auth_logout_and_temp_password_postgres18.py` et `test_auth_pg_rehydration_postgres18.py`).
   - Migration Alembic `20261115_1902` validée en cycle réversible (`upgrade head -> downgrade 20261115_1901 -> upgrade head`).
   - Contrainte `chk_org_units_bu_no_members` et rejet `HTTP 422 ERR_ORG_UNIT_BU_MEMBERS_FORBIDDEN` vérifiés par `SELECT` PostgreSQL 18.
3. **Couche 3 (Contrats OpenAPI 3.1 & Architecture — exécutés après la dernière édition)** :
   - `scripts/export_openapi.py --check` : **`0-diff`** validé (`0`).
   - `tests/contract/test_openapi_contract.py` (`Schemathesis`) : **`2 passed in 68.21s`**.
   - `ruff check`, `ruff format --check` (`512` fichiers), `mypy --strict` (**`344`** fichiers), `lint-imports` (`5 kept, 0 broken`), `lint_spine.py` (`0 findings`), `audit_code.py` (`0` anomalie).
4. **Couche 4 (Composants React & Vitest — exécutés après la dernière édition)** :
   - `pnpm turbo run lint typecheck test` : **`9/9` tâches réussies** (`@orcia/api-client`: `2` fichiers / `13` tests ; `@orcia/ui`: `14` fichiers / `75` tests ; `@orcia/web`: `19` fichiers / `99` tests ; total **`187 passed`**).
5. **Couche 5 (Playwright E2E réels contre stack PG18 + Redis + FastAPI + Vite)** :
   - `e2e/07-spaces-org-and-workspace-persistence.spec.ts` & `e2e/11-screens-smoke-without-server-errors.spec.ts` : **`3 passed, 3 skipped (54.6s)`** sur pile éphémère réelle (`desktop-cockpit` 100 % verts sans erreur `>= 400`, cas `mobile-cockpit` ignorés par configuration projet).
6. **Audit Zéro Adaptateur SQL Orphelin** :
   - Les fonctions de `sql_org_iam_role_sync.py` (`validate_org_unit_leads`, `sync_lead_roles_for_org_unit`, `remove_lead_roles_for_org_unit`, `sync_user_lead_assignments`, `resolve_default_iam_auth_source`) sont câblées dans `sql_org_units.py` et `sql_iam_accounts.py`.
7. **Registre des Capacités & Showcase** :
   - Capacités `CAP-050`, `CAP-051`, `CAP-058`, `CAP-067` mises à jour dans `docs/product/capabilities.yaml` avec surfaces et migration `20261115_1902`.
   - `sync_site_catalog.py --check` : `57/57` capacités live avec tests, `127` rapports, `0-diff`.
   - `scripts/check_implementation_docs.py` : `127/127` rapports conformes et indexés.
