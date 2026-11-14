# 2026-11-14 — Blocage Suppression Unité d'Organisation, Garde Schéma PostgreSQL, Modale de Dépendances & Auto-complétion / Validation Stricte des Membres Connus (`CAP-067`)

- **Date** : `2026-11-14`
- **Story / Clé Sprint** : `2026-11-14-suppression-org-unit-garde-pg-et-modale-dependances` (`Ajustement Transverse` — `CAP-067` / post-`Story 17.2`)
- **Capacité(s)** : `CAP-067` (*Organigramme hiérarchique multi-niveaux (BU / Sous-BU / Équipe), modales d'édition/membres/facturation, espaces privés et sélecteur de contexte*) — classification : **`hygiène`** / **`ux`**
- **Auteur / Contexte** : Correctif transverse suite à l'incident terrain sur « Sous-Équipe Checkout & Core Solutions » impossible à supprimer (`3 Espaces de Travail rattachés` fantômes absents du Scope Switcher et de l'écran `/workspaces`), enrichi par l'auto-complétion des membres/responsables déjà connus (`iam_accounts` $\cup$ `users`) et le rejet strict (`HTTP 422 ERR_ORG_UNIT_UNKNOWN_USER`) de tout utilisateur inconnu. Couverture des exigences `FR-3`, `FR-22`, `FR-23`, `AD-19`, `NFR-A11Y-1` et des garde-fous anti-pannes silencieuses (`GEMINI.md`).
- **Commits associés** : `a9458a8` (+ évolution auto-complétion & validation stricte utilisateurs connus sur la même branche `fix/org-unit-delete-modal-and-pg-schema-guard`).

---

## 1. Analyse du Besoin & Étude d'Impact Tech Lead (Pré-Implémentation)

### 1.1 Contexte & Problématique
- **Symptôme observé en production locale** :
  - L'utilisateur voit dans `Configuration › Organisation` des unités issues des fixtures de démonstration (`BU Digital & Paiements`, `Équipe Parente Architecture & Plateforme`, `Sous-Équipe Checkout & Core Solutions`, `Équipe Partenaire Intégration`), alors que le Scope Switcher en haut d'écran n'affiche que l'espace réel **`RTS`** (`MonCompte`).
  - Lors de la tentative de suppression de `Sous-Équipe Checkout & Core Solutions`, la modale `ConfirmDeleteOrgUnitModal` affiche :
    - *« Suppression refusée pour « Sous-Équipe Checkout & Core Solutions » : 3 Espaces de Travail rattachés. Déplacez ou supprimez d'abord ces éléments. »*
    - *« Déplacez ou supprimez d'abord les sous-unités et espaces rattachés ci-dessus avant de supprimer cette unité. »*
    sans afficher aucune liste « ci-dessus », avec un bouton `Confirmer la suppression` restant cliquable.
- **Triple cause racine identifiée** :
  1. **Base PostgreSQL locale non migrée (`alembic_version = 0022_epic_8`) + fallback silencieux vers `seeds.py`** : `sql_org_units.py` interrogeait `o.billing_enabled`, `o.lead_user_id`, `o.member_user_ids_jsonb` (ajoutées en `20261111_1702`), provoquant `UndefinedColumnError`. Au lieu de remonter l'erreur de schéma, `apps/api/src/orcia_api/routers/org_units.py` (`L255-L262`, `L390-L395`) avalait **toute** `Exception` et basculait sur `svc.evaluator` mémoire initialisé avec les 4 unités et 3 espaces fictifs de `permissions/seeds.py` (`Workspace 1 : Solution Paiement`, `Workspace 2 : Solution Fidélité`, `Workspace 3 : Projet Confidentiel M&A`). Pendant ce temps, `GET /api/v1/bootstrap/platform-setup-state` continuait de lire `platform_settings` en base (`RTS`).
  2. **Court-circuit conditionnel dans `_reconcile_workspaces_on_load`** (`sql_platform_setup_store.py:L167-L181`) : la réconciliation avec la table relationnelle `workspaces` ne s'exécutait que `if not workspaces:` (snapshot JSONB vide), rendant invisible tout espace SQL présent dans `workspaces` dès lors que `platform_setup_state_v1` contenait déjà au moins un espace (`RTS`).
  3. **Modale `ConfirmDeleteOrgUnitModal.tsx` incomplète** : le DTO `OrgUnitResponse` et `OrgTreeRowItem` ne transportaient qu'un scalaire `attached_workspaces_count` sans les noms/identifiants des sous-unités ni des espaces bloquants ; la mention « ci-dessus » pointait dans le vide et le bouton destructif restait actif même quand `isNonEmpty` était vrai.
  4. **Saisie libre non validée pour `lead_user_id` & `member_user_ids`** : `CreateOrgUnitModal` et `ManageOrgUnitMembersModal` utilisaient de simples champs texte libres sans auto-complétion sur les comptes connus (`iam_accounts` / `users`), acceptant aussi bien `"romain"` que n'importe quelle chaîne inexistante côté UI comme côté API `POST`/`PATCH /api/v1/org-units`.

### 1.2 Exploration, Analyse d'Impact GitNexus, Factorisation & Dette Technique
- **Analyse d'Impact GitNexus (`repo: "ORCIA"`, `direction: "upstream"`)** :
  - `list_org_units_from_postgres18` (`sql_org_units.py:L161`) & `delete_org_unit_on_postgres18` (`sql_org_units.py:L333`) : appelants actifs dans `apps/api/src/orcia_api/routers/org_units.py` (`L251`, `L386`) et suite PostgreSQL 18 `tests/integration/api/test_story_17_2_org_units_hierarchy_postgres18.py`.
  - `ConfirmDeleteOrgUnitModal` (`ConfirmDeleteOrgUnitModal.tsx:L18`) : `impactedCount = 5` (`SettingsOrganizationUnitsBlock.tsx:L381`, `settings.tsx`, `router.tsx`).
  - `_reconcile_workspaces_on_load` (`sql_platform_setup_store.py:L152`) : `impactedCount = 1` (`load_platform_setup_state_from_postgres18` à `L361`).
- **Exploration PostgreSQL locale (`2ea5f9f59bac`, `127.0.0.1:5433/orcia`)** :
  - Avant correction : `alembic_version = 0022_epic_8`, `org_units` (`3` lignes : `orcia-root`, `DS3C`, `MonCompte`, sans colonnes `1702`), `workspaces` (`1` ligne : `RTS` rattaché à `MonCompte`).
  - Migration immédiate exécutée vers `head` (`20261114_1705`, 10 révisions appliquées sans erreur) : colonnes `billing_enabled`, `lead_user_id`, `member_user_ids_jsonb` présentes et données existantes intégralement préservées.
- **Opportunités de Factorisation & Contrôle de Volumétrie (`> 350–400` lignes)** :
  - `packages/orcia-core/src/orcia_core/bootstrap/_internal/sql_platform_setup_store.py` (**431 l.** — dépassement) $\rightarrow$ découpage en `sql_platform_setup_store.py` + `sql_platform_setup_reconcilers.py` (`< 300` l. chacun).
  - `apps/api/src/orcia_api/routers/org_units.py` (**399 l.** — seuil critique) $\rightarrow$ extraction des helpers de mapping/résolution PG vs mémoire dans `apps/api/src/orcia_api/routers/_org_units_helpers.py` (`< 280` l. chacun).
  - `apps/web/src/routes/SettingsOrganizationUnitsBlock.tsx` (**398 l.** — seuil critique) $\rightarrow$ extraction de l'encart pédagogique dans `apps/web/src/features/admin/organization/OrgPedagogicalCallout.tsx` (`< 300` l. chacun).
  - `packages/orcia-core/src/orcia_core/bootstrap/_internal/sql_org_units.py` (**361 l.** — élevé) $\rightarrow$ extraction des requêtes de lecture et mapping SQL dans `packages/orcia-core/src/orcia_core/bootstrap/_internal/sql_org_units_queries.py` (`< 300` l. chacun).

---

## 2. Plan d'Implémentation

### 2.1 Schéma de Données & Migrations Alembic (`infra/migrations/versions/`)
- Aucune nouvelle révision Alembic requise (les colonnes de `org_units` et `workspaces` existent déjà dans `20261111_1702`).
- Opération d'exploitation appliquée sur la base locale : `.venv/bin/alembic -c infra/migrations/alembic.ini upgrade head` (`0022_epic_8` $\rightarrow$ `20261114_1705`).

### 2.2 Noyau Métier Hexagonal, Orchestration & Workers (`packages/orcia-core/`)
- `packages/orcia-core/src/orcia_core/permissions/errors.py`, `_error_catalog.py` & `__init__.py` :
  - Ajouter `OrgUnitStorageSchemaError` (`503`, `ERR_ORG_STORAGE_SCHEMA_OUTDATED`) et `OrgUnitUnknownUserError` (`422`, `ERR_ORG_UNIT_UNKNOWN_USER`) héritant de `OrciaDomainError` sans import framework SQLAlchemy/FastAPI (`AD-19`).
- `packages/orcia-core/src/orcia_core/permissions/org_hierarchy.py` :
  - Définir `AttachedWorkspaceRef(id, slug, name)` et `KnownOrgUser(principal_id, display_name, email)` ; enrichir `OrgUnitSummary` avec `attached_workspaces`.
  - Implémenter la fonction pure `resolve_and_validate_org_unit_users(lead_user_id, member_user_ids, known_users)` normalisant tout `principal_id` / `email` connu actif vers son `principal_id` canonique et rejetant tout identifiant inconnu (y compris un prénom libre sans correspondance identifiant) via `OrgUnitUnknownUserError`.
- `packages/orcia-core/src/orcia_core/bootstrap/_internal/sql_org_units_queries.py` & `sql_org_units.py` :
  - Enrichir la sous-requête agrégée `LEFT JOIN` sur `workspaces` avec `COALESCE(ws.attached_ws_json, '[]'::jsonb)` calculée via `jsonb_agg(...)` — zéro requête `N+1`.
  - Ajouter `load_known_org_users_from_postgres18(conn)` (`iam_accounts` `account_kind = 'HUMAN' AND status <> 'DISABLED'` $\cup$ `users` `is_active = TRUE`) et exécuter `resolve_and_validate_org_unit_users` lors de `create_org_unit_on_postgres18` et `update_org_unit_on_postgres18`.
- `packages/orcia-core/src/orcia_core/bootstrap/_internal/sql_platform_setup_reconcilers.py` & `sql_platform_setup_store.py` :
  - Supprimer le court-circuit `if not workspaces:` dans `reconcile_workspaces_on_load` afin de fusionner systématiquement les lignes relationnelles `workspaces` dans l'état retourné (matching dédupliqué par `workspaceId` / `slug` normalisé).

### 2.3 Couche Backend API, Sécurité & Contrats (`apps/api/`, `packages/api-client/`)
- `apps/api/src/orcia_api/errors/registry.py` :
  - Enregistrer `OrgUnitStorageSchemaError` (`503`, `ERR_ORG_STORAGE_SCHEMA_OUTDATED`) et `OrgUnitUnknownUserError` (`422`, `ERR_ORG_UNIT_UNKNOWN_USER`, messages `fr`/`en` RFC 9457).
- `apps/api/src/orcia_api/schemas/auth_and_org.py` :
  - Ajouter `AttachedWorkspaceRefResponse` (`id`, `slug`, `name`), `KnownOrgUserResponse` (`principal_id`, `display_name`, `email`), `OrgUnitResponse.attached_workspaces` et `OrgUnitsListResponse.known_users`.
- `apps/api/src/orcia_api/routers/_org_units_helpers.py`, `_org_units_users.py` & `org_units.py` :
  - Distinguer connectivité indisponible (`OSError`/`TimeoutError`) vs erreur SQL de schéma (`ProgrammingError` $\rightarrow$ `HTTP 503`).
  - Hydrater `known_users` sur `GET /api/v1/org-units` et appliquer `resolve_and_validate_org_unit_users` sur `POST`/`PATCH /api/v1/org-units` (PostgreSQL et fallback mémoire).
- **Clean-up base locale** : aligner `ds3c.lead_user_id` de `'romain'` vers `'romain.esnault@gmail.com'` dans `2ea5f9f59bac`.
- `packages/api-client/` :
  - Régénérer le SDK OpenAPI 3.1 via `.venv/bin/python scripts/export_openapi.py` et contrôler le `0-diff` (`--check`).

### 2.4 Interface Utilisateur & Expérience (`apps/web/`)
- `apps/web/src/i18n/locales/organization_tab_labels.ts` :
  - Ajouter les libellés bilingues `fr`/`en` pour la liste des dépendances bloquantes (sous-unités enfants, espaces rattachés, bouton direct `Gérer les espaces rattachés`) et supprimer la mention incohérente « ci-dessus ».
- `apps/web/src/features/admin/organization/orgUnitsApiBridge.ts` & `orgTreeHelpers.ts` :
  - Propager `attachedWorkspaces` depuis `OrgUnitResponse` et enrichir `OrgTreeRowItem` avec `childUnits` (noms/slugs des sous-unités) et `attachedWorkspaces` (avec repli sur la liste `workspaces` du store si le champ API n'est pas fourni en mode legacy).
- `apps/web/src/features/admin/organization/ConfirmDeleteOrgUnitModal.tsx` :
  - Rendre la liste nominative `data-testid="org-unit-delete-dependencies-list"` dans le panneau de blocage lorsque `isNonEmpty` est vrai (sous-unités + espaces rattachés).
  - Ajouter le bouton `data-testid="org-unit-delete-open-workspaces-btn"` qui ferme la modale et déclenche `onOpenWorkspaces` vers `/workspaces` lorsqu'au moins un espace bloque la suppression.
  - Désactiver le bouton destructif `confirm-delete-org-unit-btn-{unitId}` lorsque `isSubmitting || isNonEmpty`, tout en gardant la bannière `org-unit-delete-feedback` dans `SettingsOrganizationUnitsBlock.tsx` en cas de `HTTP 409` concurrent.
- `apps/web/src/features/admin/organization/OrgPedagogicalCallout.tsx` & `apps/web/src/routes/SettingsOrganizationUnitsBlock.tsx` :
  - Extraire l'encart pédagogique (`organization-pedagogical-callout`, `organization-open-workspaces-btn`) sous la barre des `300` lignes et câbler `onOpenWorkspaces` dans `ConfirmDeleteOrgUnitModal` (zéro callback optionnel oublié).
- `packages/ui/src/primitives/OrciaKnownUserCombobox.tsx`, `CreateOrgUnitModal.tsx`, `ManageOrgUnitMembersModal.tsx` & `SettingsOrganizationUnitRow.tsx` :
  - Ajouter le composant Design System `<OrciaKnownUserCombobox />` (`role="combobox"` / `role="listbox"`, filtrage par nom/email/identifiant, navigation clavier, zéro hex brut, anti-LastPass) et l'intégrer sur la saisie du responsable et l'ajout de membres avec blocage UI + message inline `data-testid="org-unit-unknown-user-error"` pour tout utilisateur inconnu.

### 2.5 Analyse d'Impact sur la Pyramide des Tests (`AD-17`)
- **Couche 1a (`tests/unit/test_story_17_2_org_hierarchy.py`)** : test de non-fallback `seeds.py` sur `ProgrammingError` (`HTTP 503 ERR_ORG_STORAGE_SCHEMA_OUTDATED`), test de réconciliation complète `workspaces` SQL + JSONB même lorsque `raw_workspaces` est non vide (`RTS` + autre espace SQL), et exposition `attached_workspaces`.
- **Couche 1b (`apps/web/src/__tests__/story-17-2-org-hierarchy-and-modals.test.tsx`)** : vérification de la liste nominative `org-unit-delete-dependencies-list`, du bouton de navigation `org-unit-delete-open-workspaces-btn`, de l'état `disabled` de `confirm-delete-org-unit-btn-*` quand non-vide, et du cas `409` concurrent affichant `org-unit-delete-feedback` + audit `zero-dead-buttons-and-silent-catches-audit.test.tsx`.
- **Couche 2 (`tests/integration/api/test_story_17_2_org_units_hierarchy_postgres18.py`)** : vérification sur PostgreSQL 18 (`testcontainers`) que `GET /api/v1/org-units` renvoie bien `attached_workspaces` (`id`, `slug`, `name`) des espaces SQL rattachés sans requête `N+1`.
- **Couche 3** : `scripts/export_openapi.py --check` (`0-diff`), `tests/contract/test_openapi_contract.py`, `.venv/bin/lint-imports`, `lint_spine.py`.
- **Couche Sécurité & Régression** : `tests/unit/test_codebase_architectural_anti_patterns_audit.py`, `tests/security/`, `pnpm turbo run lint typecheck test`.

---

## 3. Bilan des Modifications & Résultats (Post-Implémentation)

### 3.1 Fichiers Développés & Modifiés
| Fichier | Nature | Description synthétique | Lignes |
| :--- | :--- | :--- | :--- |
| `packages/orcia-core/src/orcia_core/permissions/_error_catalog.py` | Création | Extraction du catalogue d'erreurs `permissions` et ajout des codes `ERR_ORG_STORAGE_SCHEMA_OUTDATED` (503) et `ERR_ORG_UNIT_UNKNOWN_USER` (422). | 251 |
| `packages/orcia-core/src/orcia_core/permissions/errors.py` | Refactoring | Export de `OrgUnitStorageSchemaError` (503) et `OrgUnitUnknownUserError` (422) sous strict respect `AD-19`. | 193 |
| `packages/orcia-core/src/orcia_core/permissions/org_user_validation.py` | Création | Modèle pur `KnownOrgUser` et fonction `resolve_and_validate_org_unit_users` (normalisation insensible à la casse sur principal_id et email, déduplication et rejet strict des prénoms/inconnus). | 84 |
| `packages/orcia-core/src/orcia_core/permissions/org_hierarchy.py` | Modification | Dataclass `AttachedWorkspaceRef`, enrichissement de `OrgUnitSummary.attached_workspaces` et allègement sous 355 lignes. | 351 |
| `packages/orcia-core/src/orcia_core/permissions/__init__.py` | Modification | Ré-export propre de `OrgUnitStorageSchemaError`, `OrgUnitUnknownUserError`, `KnownOrgUser`, `resolve_and_validate_org_unit_users` et `AttachedWorkspaceRef`. | 348 |
| `packages/orcia-core/src/orcia_core/bootstrap/_internal/sql_org_units_queries.py` | Création | Extraction modulaire des requêtes SQL et `load_known_org_users_from_postgres18(conn)` (1 seule requête UNION ALL dédupliquée sans N+1). | 271 |
| `packages/orcia-core/src/orcia_core/bootstrap/_internal/sql_org_units.py` | Refactoring | Validation et normalisation stricte de `lead_user_id` et `member_user_ids` contre PostgreSQL 18. | 278 |
| `packages/orcia-core/src/orcia_core/bootstrap/_internal/sql_platform_setup_reconcilers.py` | Création & Correctif | Extraction de la réconciliation SQL/JSONB et correction du bug FinOps : `entry["billingEnabled"] = bool(org_row[5])` pour préserver `true` en base. | 246 |
| `packages/orcia-core/src/orcia_core/bootstrap/_internal/sql_platform_setup_store.py` | Refactoring | Allègement sous 300 lignes avec ré-export rétrocompatible des fonctions de réconciliation. | 284 |
| `apps/api/src/orcia_api/errors/registry.py` | Modification | Enregistrement de `OrgUnitStorageSchemaError` (503) et `OrgUnitUnknownUserError` (422) (RFC 9457 bilingue fr/en). | 176 |
| `apps/api/src/orcia_api/schemas/org_unit_models.py` | Création | Extraction des schémas d'unités d'organisation sous 120 lignes (`KnownOrgUserResponse`, `OrgUnitsListResponse.known_users`). | 116 |
| `apps/api/src/orcia_api/schemas/auth_and_org.py` | Modification | Ré-export des schémas d'unités d'organisation et allègement sous 310 lignes. | 306 |
| `apps/api/src/orcia_api/routers/_org_units_users.py` | Création | Agrégation mémoire + PostgreSQL des utilisateurs humains connus (`collect_known_org_users`, `serialize_known_users`, `validate_and_normalize_org_unit_users_in_request`). | 114 |
| `apps/api/src/orcia_api/routers/_org_units_helpers.py` | Création | Helpers de mapping DTO avec `attached_workspaces`, synchro évaluateur et classification fine des erreurs PostgreSQL vs mémoire. | 336 |
| `apps/api/src/orcia_api/routers/org_units.py` | Refactoring | Exposition de `known_users` sur `GET /api/v1/org-units` et validation stricte sur `POST` et `PATCH`. | 261 |
| `packages/ui/src/primitives/OrciaKnownUserCombobox.tsx` | Création | Composant combobox accessible RGAA avec autocomplétion insensible aux accents/casse, navigation clavier et attributs anti-LastPass. | 274 |
| `packages/ui/src/index.ts` | Modification | Export de `OrciaKnownUserCombobox`, `KnownUserOption` et types associés. | 258 |
| `packages/ui/src/__tests__/known-user-combobox.test.tsx` | Création | 5 tests unitaires du combobox d'autocomplétion. | 165 |
| `packages/api-client/openapi.json` | Génération | Schéma OpenAPI 3.1 mis à jour avec `KnownOrgUserResponse` et `OrgUnitsListResponse.known_users`. | - |
| `packages/api-client/src/generated/auth_and_org.ts` | Génération | DTOs TypeScript régénérés via `scripts/export_openapi.py` (0-diff vérifié). | - |
| `packages/api-client/src/generated/schema.ts` | Génération | Index de schéma régénéré (0-diff vérifié). | - |
| `apps/web/src/i18n/locales/organization_tab_labels.ts` | Modification | Clés i18n fr/en pour en-tête des dépendances, autocomplétion des membres, erreurs d'utilisateurs inconnus (`unknownUserError`, `noMatchingKnownUser`, `selectKnownUserHint`). | 321 |
| `apps/web/src/components/platformSetupStorageHelpers.ts` | Modification | Types `AttachedWorkspaceRef` et `attachedWorkspaces` sur `ConfiguredOrgUnit`. | 345 |
| `apps/web/src/features/admin/organization/orgUnitsApiBridge.ts` | Modification | Exposition de `knownUsers: readonly KnownUserOption[]` et helper pur `isKnownUserIdentifier`. | 162 |
| `apps/web/src/features/admin/organization/orgTreeHelpers.ts` | Modification | `OrgTreeRowItem` enrichi de `childUnits` et `attachedWorkspaces` (priorité API avec fallback store). | 211 |
| `apps/web/src/features/admin/organization/ConfirmDeleteOrgUnitModal.tsx` | Modification | Rendu nominatif `org-unit-delete-dependencies-list`, bouton `org-unit-delete-open-workspaces-btn`, bouton confirm désactivé quand `isNonEmpty`. | 170 |
| `apps/web/src/features/admin/organization/CreateOrgUnitModal.tsx` | Modification | Intégration de `<OrciaKnownUserCombobox />`, validation stricte à la soumission et affichage de `org-unit-unknown-user-error`. | 284 |
| `apps/web/src/features/admin/organization/ManageOrgUnitMembersModal.tsx` | Modification | Intégration de `<OrciaKnownUserCombobox />` pour responsable et membres avec exclusion des membres déjà ajoutés et validation stricte. | 311 |
| `apps/web/src/routes/SettingsOrganizationUnitRow.tsx` | Modification | Résolution et affichage du nom complet du responsable via `knownUsers`. | 214 |
| `apps/web/src/features/admin/organization/OrgPedagogicalCallout.tsx` | Création | Extraction de l'encart pédagogique d'organisation sous 50 lignes. | 45 |
| `apps/web/src/routes/SettingsOrganizationUnitsBlock.tsx` | Refactoring | Hydratation de `knownUsers` depuis l'API et transmission aux modales enfants (< 355 lignes). | 353 |
| `tests/unit/test_story_17_2_pg_guard_and_reconcilers.py` | Création | 4 tests unitaires (503 sur dérive de schéma, fallback mémoire sur connectivité, fusion workspaces SQL+JSONB, DTOs). | 177 |
| `tests/unit/test_story_17_2_org_hierarchy.py` | Modification | Tests de validation de `resolve_and_validate_org_unit_users`, rejet de `romain` et `inconnu@orcia.fr`. | 492 |
| `tests/integration/api/test_story_17_2_org_units_hierarchy_postgres18.py` | Modification | Test d'intégration PostgreSQL 18 vérifiant l'hydratation de `attached_workspaces`, le rejet 422 des inconnus/désactivés et le filtrage des `known_users` actifs. | 385 |
| `apps/web/src/__tests__/story-17-2-org-hierarchy-and-modals.test.tsx` | Modification | 4 tests Vitest vérifiant dépendances de suppression, autocomplétion des utilisateurs connus et blocage strict des inconnus (`org-unit-unknown-user-error`). | 299 |
| `apps/web/src/__tests__/i18n-and-shell.test.tsx` | Modification | 26 tests Vitest au vert garantissant la non-régression globale de la plateforme. | 2074 |

### 3.2 Résultats Chiffrés, Métriques & Qualité
- **Couverture de tests & Exécution** :
  - `packages/orcia-core/src/orcia_core/permissions/org_user_validation.py` : **100%**
  - `packages/orcia-core/src/orcia_core/permissions/org_hierarchy.py` : **96%**
  - `packages/orcia-core/src/orcia_core/permissions/errors.py` : **100%**
  - `packages/orcia-core/src/orcia_core/permissions/_error_catalog.py` : **100%**
  - Suite ciblée `test_story_17_2_*.py` : **11 passed**.
  - Tests d'intégration PostgreSQL 18 réels (`testcontainers`) : **1 passed** en 17s.
  - Tests contractuels OpenAPI & anti-patterns audit : **6 passed**.
  - Vitest `@orcia/ui` : 19 fichiers testés, **82/82 tests passés** (dont 5/5 sur `OrciaKnownUserCombobox`).
  - Vitest `@orcia/web` : 14 fichiers testés, **73/73 tests passés** (dont 4/4 sur `story-17-2-org-hierarchy-and-modals.test.tsx` et 26/26 sur `i18n-and-shell.test.tsx`).
  - Turbo global (`lint`, `typecheck`, `test` dans les 3 packages web/ui/api-client) : **9/9 tâches réussies**.
- **Volumétrie & Discipline modulaire** :
  - Zéro fichier dépassant 360 lignes (tous les fichiers créés/refactorisés sont strictement `< 355` lignes).
  - Zéro violation `AD-19` (`lint-imports` : 5 contrats tenus, 0 brisé).
  - Architecture Spine (`lint_spine.py`) : `0 findings`.
  - Typage statique Python (`mypy --strict` 303 fichiers source) : `Success: no issues found`.
  - Typage statique TypeScript (`tsc --noEmit`) : 0 erreur sur tous les packages.
  - Linters Python : `ruff check` et `ruff format --check` : 0 warning sur 723 fichiers.
  - Zéro couleur hexadécimale en dur en dehors de `tokens.css` validé par `design-system-look-and-feel-isolation.test.tsx`.
  - Zéro bouton muet et zéro `.catch(() => undefined)` validé par `zero-dead-buttons-and-silent-catches-audit.test.tsx`.
- **Résolution du Bug FinOps `billing_enabled`** :
  - Cause racine identifiée dans `sql_platform_setup_reconcilers.py` : `entry["billingEnabled"]` n'était valorisé que si `org_row[5] is False`, omettant la clé lors de la création d'une unité avec facturation FinOps active (`True`), provoquant un état `undefined` côté UI affiché comme `Sans imputation FinOps`.
  - Corrigé avec `if len(org_row) > 5 and org_row[5] is not None: entry["billingEnabled"] = bool(org_row[5])`.

### 3.3 Validation & Procédure de Test sur Toute la Pyramide (`AD-17` + 5 Garde-Fous de Câblage Vertical)
- **Couche 1a — Tests Unitaires Python** :
  - `tests/unit/test_story_17_2_org_hierarchy.py` :
    - `test_resolve_and_validate_org_unit_users` : teste la correspondance insensible à la casse sur `principal_id` et `email`, le rejet de saisies comme `"romain"` si seul l'email complet est connu, le rejet d'utilisateurs inconnus (`OrgUnitUnknownUserError`), la conservation de l'ordre et la déduplication des membres.
    - Tests de garde 503 et repli mémoire en mode test (`ORCIA_DISABLE_PG_BOOTSTRAP_SYNC=1`).
- **Couche 1b — Tests Composants & Modales UI (Vitest)** :
  - `packages/ui/src/__tests__/known-user-combobox.test.tsx` :
    - 5 tests RGAA validant le filtre insensible aux accents/casse, la sélection via `Enter` ou clic souris, le message d'absence de correspondance, l'exclusion des membres existants (`excludedPrincipalIds`) et les attributs anti-LastPass.
  - `apps/web/src/__tests__/story-17-2-org-hierarchy-and-modals.test.tsx` :
    - Vérification de l'autocomplétion des utilisateurs connus dans `CreateOrgUnitModal` et `ManageOrgUnitMembersModal`.
    - Vérification du blocage strict côté UI avec bandeau `org-unit-unknown-user-error` sans appel API lorsqu'un utilisateur inconnu est renseigné.
    - Vérification de la liste nominative des dépendances `org-unit-delete-dependencies-list` et de la désactivation du bouton de suppression.
- **Couche 2 — Intégration Verticale PostgreSQL 18 (`testcontainers-python`)** :
  - `tests/integration/api/test_story_17_2_org_units_hierarchy_postgres18.py` :
    - Vérification de la requête SQL `load_known_org_users_from_postgres18` sur `iam_accounts` $\cup$ `users` actifs.
    - Vérification du rejet `HTTP 422 ERR_ORG_UNIT_UNKNOWN_USER` pour les identifiants inconnus ou désactivés (`disabled.user@orcia.fr`).
    - Vérification de la normalisation et persistance des `principal_id` canoniques en base PostgreSQL 18.
- **Couche 3 — Contrat OpenAPI 3.1 & SDK Typescript** :
  - `.venv/bin/python scripts/export_openapi.py --check` validé (`0-diff`).
  - Schémas `KnownOrgUserResponse` et `OrgUnitsListResponse.known_users` exportés dans le SDK.
- **Garde-fous de Câblage Vertical & Anti-Régression** :
  - Règles 1 à 4 validées par `tests/unit/test_codebase_architectural_anti_patterns_audit.py`.
  - Look & Feel Direction C validé par `design-system-look-and-feel-isolation.test.tsx`.
  - Manifeste Showcase et site synchronisés via `pnpm site:sync && pnpm site:check`.
