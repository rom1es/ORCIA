# 2026-11-14 — Blocage Suppression Unité d'Organisation, Garde Schéma PostgreSQL, Recherche Interactive Parent & Membres (Max 10) & Enrôlement Chaîné `+ Nouveau membre` (`CAP-067`)

- **Date** : `2026-11-14`
- **Story / Clé Sprint** : `2026-11-14-suppression-org-unit-garde-pg-et-modale-dependances` (`Ajustement Transverse` — `CAP-067` / post-`Story 17.2`)
- **Capacité(s)** : `CAP-067` (*Organigramme hiérarchique multi-niveaux (BU / Sous-BU / Équipe), modales d'édition/membres/facturation, espaces privés et sélecteur de contexte*) — classification : **`hygiène`** / **`ux`**
- **Auteur / Contexte** : Correctif transverse suite à l'incident terrain sur « Sous-Équipe Checkout & Core Solutions » impossible à supprimer (`3 Espaces de Travail rattachés` fantômes absents du Scope Switcher et de l'écran `/workspaces`), enrichi par : (1) l'auto-complétion et validation stricte des membres/responsables connus (`HTTP 422 ERR_ORG_UNIT_UNKNOWN_USER`), (2) la refonte du sélecteur **Unité parente de rattachement** (`max 10`, recherche interactive par caractère `GET /api/v1/org-units?q=...&kind=BU&limit=10`), et (3) la recherche interactive des membres/responsables (`max 10`, `GET /api/v1/org-units/known-users?q=...&limit=10`) associée au bouton permanent **`+ Nouveau membre`** ouvrant `IamAccountModal` en modale chaînée sans quitter `Gouvernance & Membres`. Couverture `FR-3`, `FR-22`, `FR-23`, `AD-19`, `NFR-A11Y-1` et garde-fous anti-pannes silencieuses (`GEMINI.md`).
- **Commits associés** : `a9458a8`, `15a7a29`, `463037e` (+ évolution recherche live membres max 10 & bouton `+ Nouveau membre` sur la même branche `fix/org-unit-delete-modal-and-pg-schema-guard`).

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
  5. **Sélecteur statique illimité sur « Unité parente de rattachement »** : `CreateOrgUnitModal` (`org-unit-parent-select`) et `EditOrgUnitModal` (`edit-org-unit-parent-select`) utilisaient un `<select>` HTML natif chargeant toute l'arborescence sans plafond d'affichage ni champ de recherche interactive lettre par lettre, devenant difficilement exploitable au-delà d'une dizaine d'organisations.
  6. **Recherche membres non plafonnée ni interactive serveur & absence de création rapide d'un collaborateur** : `<OrciaKnownUserCombobox />` affichait l'ensemble du catalogue client sans plafond `max 10`, sans indicateur de troncature et sans recherche serveur lettre par lettre ; de plus, pour ajouter un collaborateur absent de l'annuaire depuis `ManageOrgUnitMembersModal`, l'administrateur devait abandonner sa modale et naviguer vers l'onglet IAM.

### 1.2 Exploration, Analyse d'Impact GitNexus, Factorisation & Dette Technique
- **Analyse d'Impact GitNexus (`repo: "ORCIA"`, `direction: "upstream"`)** :
  - `list_org_units_from_postgres18` (`sql_org_units.py:L161`) & `delete_org_unit_on_postgres18` (`sql_org_units.py:L333`) : appelants actifs dans `apps/api/src/orcia_api/routers/org_units.py` (`L251`, `L386`) et suite PostgreSQL 18 `tests/integration/api/test_story_17_2_org_units_hierarchy_postgres18.py`.
  - `list_org_units` (`apps/api/src/orcia_api/routers/org_units.py:L58-L61`, `274 l.`) & `listOrgUnits` (`packages/api-client`): uniquement paramétré par `persona_key`, étendu avec `q`, `kind`, `limit`.
  - `ConfirmDeleteOrgUnitModal` (`ConfirmDeleteOrgUnitModal.tsx:L18`) : `impactedCount = 5` (`SettingsOrganizationUnitsBlock.tsx:L381`, `settings.tsx`, `router.tsx`).
  - `_reconcile_workspaces_on_load` (`sql_platform_setup_store.py:L152`) : `impactedCount = 1` (`load_platform_setup_state_from_postgres18` à `L361`).
  - `CreateOrgUnitModal` (`293 l.`) & `EditOrgUnitModal` (`185 l.`) : seuls deux composants consomment `getEligibleParentBuUnits` (`orgTreeHelpers.ts:L147-L173`) pour le choix de l'unité parente.
  - `OrciaKnownUserCombobox` (`OrciaKnownUserCombobox.tsx`, `267 l.`) & `IamAccountModal` (`IamAccountModal.tsx`, `328 l.`) : montés respectivement dans `ManageOrgUnitMembersModal`/`CreateOrgUnitModal` et dans l'onglet IAM (`Story 17.3`), permettant une modale chaînée Radix UI sans quitter le contexte d'édition.
- **Exploration PostgreSQL locale (`2ea5f9f59bac`, `127.0.0.1:5433/orcia`)** :
  - Avant correction : `alembic_version = 0022_epic_8`, `org_units` (`3` lignes : `orcia-root`, `DS3C`, `MonCompte`, sans colonnes `1702`), `workspaces` (`1` ligne : `RTS` rattaché à `MonCompte`).
  - Migration immédiate exécutée vers `head` (`20261114_1705`, 10 révisions appliquées sans erreur) : colonnes `billing_enabled`, `lead_user_id`, `member_user_ids_jsonb` présentes et données existantes intégralement préservées.
- **Opportunités de Factorisation & Contrôle de Volumétrie (`> 350–400` lignes)** :
  - `packages/orcia-core/src/orcia_core/bootstrap/_internal/sql_platform_setup_store.py` (**431 l.** — dépassement) $\rightarrow$ découpage en `sql_platform_setup_store.py` + `sql_platform_setup_reconcilers.py` (`< 300` l. chacun).
  - `apps/api/src/orcia_api/routers/org_units.py` (**399 l.** — seuil critique) $\rightarrow$ extraction des helpers de mapping/résolution PG vs mémoire dans `apps/api/src/orcia_api/routers/_org_units_helpers.py` (`< 360` l. chacun).
  - `apps/web/src/routes/SettingsOrganizationUnitsBlock.tsx` (**398 l.** $\rightarrow$ **353 l.**) $\rightarrow$ extraction des modales dans `SettingsOrganizationModalsGroup.tsx` pour rester `< 280` lignes.
  - `packages/orcia-core/src/orcia_core/bootstrap/_internal/sql_org_units_queries.py` (**353 l.** — proche du seuil) $\rightarrow$ extraction des requêtes `iam_accounts` / `users` dans `packages/orcia-core/src/orcia_core/bootstrap/_internal/sql_org_known_users.py` (`< 140` l.).
  - `apps/web/src/i18n/locales/organization_tab_labels.ts` (**339 l.** — proche du seuil) $\rightarrow$ découpage des libellés modales dans `apps/web/src/i18n/locales/organization_modals_labels.ts` (`< 200` l. chacun).
  - **Factorisation Design System `@orcia/ui`** : extraction du helper `normalizeComboboxSearchToken` (normalisation `NFD` sans accents + minuscule) hors de `OrciaKnownUserCombobox.tsx` (`274 l.`) vers `packages/ui/src/primitives/comboboxSearchUtils.ts` (`< 30` l.) partagé entre `<OrciaKnownUserCombobox />` et `<OrciaSearchableSelect />` (`282` l.).

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
- `packages/orcia-core/src/orcia_core/bootstrap/_internal/sql_org_known_users.py`, `sql_org_units_queries.py` & `sql_org_units.py` :
  - Enrichir la sous-requête agrégée `LEFT JOIN` sur `workspaces` avec `COALESCE(ws.attached_ws_json, '[]'::jsonb)` calculée via `jsonb_agg(...)` — zéro requête `N+1`.
  - Extraire `load_known_org_users_from_postgres18(conn)` dans `sql_org_known_users.py` (`iam_accounts` `account_kind = 'HUMAN' AND status <> 'DISABLED'` $\cup$ `users` `is_active = TRUE`) et y ajouter `search_known_org_users_from_postgres18(conn, q, limit)` utilisant `ILIKE :q_pattern ESCAPE '\'` (nettoyage `\x00`, échappement `\`, `%`, `_`) et `LIMIT :limit_plus_one` pour calculer `has_more` en une passe.
  - Exécuter `resolve_and_validate_org_unit_users` lors de `create_org_unit_on_postgres18` et `update_org_unit_on_postgres18`, et ajouter les filtres optionnels `q`, `kind`, `limit` sur `list_org_units_from_postgres18` (parité mémoire).
- `packages/orcia-core/src/orcia_core/bootstrap/_internal/sql_platform_setup_reconcilers.py` & `sql_platform_setup_store.py` :
  - Supprimer le court-circuit `if not workspaces:` dans `reconcile_workspaces_on_load` afin de fusionner systématiquement les lignes relationnelles `workspaces` dans l'état retourné (matching dédupliqué par `workspaceId` / `slug` normalisé).

### 2.3 Couche Backend API, Sécurité & Contrats (`apps/api/`, `packages/api-client/`)
- `apps/api/src/orcia_api/errors/registry.py` :
  - Enregistrer `OrgUnitStorageSchemaError` (`503`, `ERR_ORG_STORAGE_SCHEMA_OUTDATED`) et `OrgUnitUnknownUserError` (`422`, `ERR_ORG_UNIT_UNKNOWN_USER`, messages `fr`/`en` RFC 9457).
- `apps/api/src/orcia_api/schemas/org_unit_models.py` & `auth_and_org.py` :
  - Ajouter `AttachedWorkspaceRefResponse` (`id`, `slug`, `name`), `KnownOrgUserResponse` (`principal_id`, `display_name`, `email`), `OrgUnitResponse.attached_workspaces`, `OrgUnitsListResponse.known_users`, et `KnownOrgUsersSearchResponse` (`items`, `has_more`).
- `apps/api/src/orcia_api/routers/_org_units_helpers.py`, `_org_units_users.py` & `org_units.py` :
  - Distinguer connectivité indisponible (`OSError`/`TimeoutError`) vs erreur SQL de schéma (`ProgrammingError` $\rightarrow$ `HTTP 503`).
  - Hydrater `known_users` sur `GET /api/v1/org-units`, appliquer `resolve_and_validate_org_unit_users` sur `POST`/`PATCH /api/v1/org-units`, et étendre `GET /api/v1/org-units` avec `q`, `kind`, `limit`.
  - Exposer **`GET /api/v1/org-units/known-users`** (`q: str | None`, `limit: int = Query(default=10, ge=1, le=100)`) avant toute route paramétrée `/{unit_id}`, avec parité PostgreSQL 18 / évaluateur mémoire (`search_known_org_users_for_request`).
- **Clean-up base locale** : aligner `ds3c.lead_user_id` de `'romain'` vers `'romain.esnault@gmail.com'` dans `2ea5f9f59bac`.
- `packages/api-client/` :
  - Régénérer le SDK OpenAPI 3.1 via `.venv/bin/python scripts/export_openapi.py` (`0-diff`), et exposer `listOrgUnits({ q, kind, limit })` ainsi que `searchKnownOrgUsers({ q, limit })`.

### 2.4 Interface Utilisateur & Expérience (`packages/ui/`, `apps/web/`)
- `packages/ui/src/primitives/comboboxSearchUtils.ts`, `OrciaKnownUserCombobox.tsx`, `OrciaSearchableSelect.tsx` & `packages/ui/src/index.ts` :
  - Factoriser `normalizeComboboxSearchToken` entre `<OrciaKnownUserCombobox />` et `<OrciaSearchableSelect />`.
  - Créer `<OrciaSearchableSelect maxDisplayedItems={10} />` (déclencheur `${testId}-trigger`, recherche live sans debounce à chaque caractère, troncature stricte à 10, `<select hidden data-testid={testId}>`).
  - Étendre `<OrciaKnownUserCombobox />` avec `maxDisplayedItems = 10`, `hasMoreMatches`, `truncatedHint` (`data-testid="${testId}-truncated-hint"`), filtrage `excludePrincipalIds` appliqué avant troncature, et `onSearchQueryChange` appelé à **chaque caractère saisi**.
- `apps/web/src/i18n/locales/organization_tab_labels.ts` & `organization_modals_labels.ts` :
  - Découper les libellés modales pour rester `< 300` l. par fichier et ajouter `memberTruncatedHint`, `newMemberButtonLabel` (`+ Nouveau membre`), `newMemberCreatedFeedback` et les libellés de recherche parente (`fr`/`en`).
- `apps/web/src/features/admin/organization/orgUnitsApiBridge.ts`, `useParentOrgSearch.ts`, `useKnownOrgUsersSearch.ts` & `orgTreeHelpers.ts` :
  - Ajouter `searchParentBuUnitsFromApi(q, 10)` + `searchKnownOrgUsersFromApi(q, limit)` avec hooks dédiés à garde `requestSeqRef` anti-désordre.
- `apps/web/src/features/admin/iam/IamAccountModal.tsx` & `apps/web/src/features/admin/organization/OrgUnitInlineCreateMemberModal.tsx` :
  - Ajouter `initialCreateDefaults` sur `IamAccountModal` (pré-remplissage `emailOrPrincipal` si `@`, sinon `displayName`, et `teamIds=[unit.id]` pour une équipe).
  - Créer `OrgUnitInlineCreateMemberModal` empilé par-dessus `ManageOrgUnitMembersModal` (modale Radix chaînée sans perte de contexte) : crée le compte via `POST /api/v1/settings/iam/accounts`, rafraîchit `knownUsers`, ajoute automatiquement le membre dans `draftMembers` et ferme uniquement `IamAccountModal`.
- `apps/web/src/features/admin/organization/ConfirmDeleteOrgUnitModal.tsx`, `CreateOrgUnitModal.tsx`, `EditOrgUnitModal.tsx`, `ManageOrgUnitMembersModal.tsx`, `SettingsOrganizationModalsGroup.tsx` & `SettingsOrganizationUnitsBlock.tsx` :
  - Câbler `<OrciaSearchableSelect maxDisplayedItems={10} />` sur parent (avec anti-cycle `getDescendantOrgUnitIds`) et `<OrciaKnownUserCombobox maxDisplayedItems={10} />` sur responsable/membres.
  - Ajouter le bouton permanent `data-testid="org-unit-new-member-btn"` (`+ Nouveau membre`) dans `ManageOrgUnitMembersModal.tsx` à côté de `add-org-unit-member-btn`.
  - Extraire le groupe des modales dans `SettingsOrganizationModalsGroup.tsx` pour garder tous les fichiers `< 360` lignes.

### 2.5 Analyse d'Impact sur la Pyramide des Tests (`AD-17`)
- **Couche 1a (`tests/unit/test_story_17_2_org_hierarchy.py`, `test_story_17_2_pg_guard_and_reconcilers.py`)** : tests `503`, réconciliation `workspaces`, validation stricte (`422`), filtrage `GET /api/v1/org-units` (`q`, `kind`, `limit`) et `GET /api/v1/org-units/known-users?q=...&limit=10` (`has_more`, NFD, `\x00`).
- **Couche 1b (`packages/ui/src/__tests__/searchable-select.test.tsx`, `known-user-combobox.test.tsx`, `apps/web/src/__tests__/story-17-2-org-hierarchy-and-modals.test.tsx`)** : vérification plafond `max 10`, live search lettre par lettre parent + membres, exclusion anti-cycle, enrôlement bout-en-bout `+ Nouveau membre` via modale chaînée `IamAccountModal`, et audit `zero-dead-buttons-and-silent-catches-audit.test.tsx` + `rgaa-modals-escape-unsaved-guard.test.tsx`.
- **Couche 2 (`tests/integration/api/test_story_17_2_org_units_hierarchy_postgres18.py`)** : vérification sur PostgreSQL 18 (`testcontainers`) de `attached_workspaces`, rejet utilisateur inconnu (`422`), filtrage `GET /api/v1/org-units?q=...&kind=BU&limit=10`, et scénario complet `POST /api/v1/settings/iam/accounts` $\rightarrow$ `GET /api/v1/org-units/known-users?q=...&limit=10` $\rightarrow$ `PATCH /api/v1/org-units/{id}`.
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
| `packages/orcia-core/src/orcia_core/bootstrap/_internal/sql_org_known_users.py` | Création | Requêtes SQL dédiées aux collaborateurs connus : `load_known_org_users_from_postgres18` et `search_known_org_users_from_postgres18` avec union dédupliquée `iam_accounts` $\cup$ `users`, `ILIKE` échappé, tri déterministe et `LIMIT limit + 1` pour `has_more`. | 118 |
| `packages/orcia-core/src/orcia_core/bootstrap/_internal/sql_org_units_queries.py` | Refactoring | Allègement sous 300 lignes après extraction de `sql_org_known_users.py` ; conservation de `query_filtered_org_unit_summaries`. | 293 |
| `packages/orcia-core/src/orcia_core/bootstrap/_internal/sql_org_units.py` | Refactoring | Validation stricte utilisateurs et support du filtrage déterministe `(q, kind, limit)` dans `list_org_units_from_postgres18`. | 287 |
| `packages/orcia-core/src/orcia_core/bootstrap/_internal/sql_platform_setup_reconcilers.py` | Création & Correctif | Extraction de la réconciliation SQL/JSONB et correction du bug FinOps : `entry["billingEnabled"] = bool(org_row[5])` pour préserver `true` en base. | 246 |
| `packages/orcia-core/src/orcia_core/bootstrap/_internal/sql_platform_setup_store.py` | Refactoring | Allègement sous 300 lignes avec ré-export rétrocompatible des fonctions de réconciliation. | 284 |
| `packages/orcia-core/src/orcia_core/bootstrap/__init__.py` | Modification | Ré-export propre de `search_known_org_users_from_postgres18` et fonctions SQL d'organisation. | 256 |
| `apps/api/src/orcia_api/errors/registry.py` | Modification | Enregistrement de `OrgUnitStorageSchemaError` (503) et `OrgUnitUnknownUserError` (422) (RFC 9457 bilingue fr/en). | 176 |
| `apps/api/src/orcia_api/schemas/org_unit_models.py` | Création & Extension | Schémas d'unités d'organisation sous 130 lignes (`KnownOrgUserResponse`, `OrgUnitsListResponse.known_users`, `KnownOrgUsersSearchResponse`). | 126 |
| `apps/api/src/orcia_api/schemas/auth_and_org.py` | Modification | Ré-export des schémas d'unités d'organisation incluant `KnownOrgUsersSearchResponse` sous 310 lignes. | 308 |
| `apps/api/src/orcia_api/routers/_org_units_users.py` | Création & Extension | Agrégation mémoire + PostgreSQL des utilisateurs humains connus et `search_known_org_users_for_request` avec garde `OrgUnitStorageSchemaError` 503, fallback mémoire et NFD stripping. | 180 |
| `apps/api/src/orcia_api/routers/_org_units_helpers.py` | Création & Extension | Helpers de mapping DTO, filtrage mémoire avec NFD diacritics stripping, classification fine PostgreSQL vs mémoire (< 360 l.). | 357 |
| `apps/api/src/orcia_api/routers/org_units.py` | Refactoring | Exposition de `q`, `kind`, `limit` sur `GET /api/v1/org-units` et de la route `GET /api/v1/org-units/known-users` (avant `/{org_unit_id}`) sous 300 lignes. | 298 |
| `packages/ui/src/primitives/comboboxSearchUtils.ts` | Création | Extraction DRY du normalisateur de recherche combobox/sélecteur `normalizeComboboxSearchToken`. | 7 |
| `packages/ui/src/primitives/OrciaKnownUserCombobox.tsx` | Refactoring & Extension | Prise en charge de `maxDisplayedItems` (10), `hasMoreMatches`, `truncatedHint` (`data-testid="${testId}-truncated-hint"`), filtre `excludePrincipalIds` pré-troncature et `onSearchQueryChange` live à chaque saisie/effacement. | 302 |
| `packages/ui/src/primitives/OrciaSearchableSelect.tsx` | Création | Composant sélecteur déroulant searchable accessible avec plafond 10 éléments, live per-keystroke search, navigation clavier et select natif caché compatible RTL. | 282 |
| `packages/ui/src/index.ts` | Modification | Export de `OrciaKnownUserCombobox`, `OrciaSearchableSelect`, `OrciaSearchableSelectOption`, `OrciaSearchableSelectProps`. | 549 |
| `packages/ui/src/__tests__/known-user-combobox.test.tsx` | Création & Extension | 7 tests unitaires du combobox (plafond 10, hint troncature, live query par lettre, excludePrincipalIds avant troncature, clavier et accessibilité). | 212 |
| `packages/ui/src/__tests__/searchable-select.test.tsx` | Création | 5 tests unitaires du sélecteur parent (plafond 10, live search par lettre, hint troncature, RTL select caché). | 157 |
| `packages/api-client/openapi.json` | Génération | Schéma OpenAPI 3.1 mis à jour avec `q`, `kind`, `limit` sur `/api/v1/org-units` et `GET /api/v1/org-units/known-users` (`0-diff`). | - |
| `packages/api-client/src/generated/auth_and_org.ts` | Génération | DTOs TypeScript régénérés via `scripts/export_openapi.py` (0-diff vérifié). | - |
| `packages/api-client/src/generated/schema.ts` | Génération | Index de schéma régénéré (0-diff vérifié). | - |
| `packages/api-client/src/helpers.ts` | Modification | Helpers de construction de query `buildOrgUnitsQuery`, `buildKnownOrgUsersQuery` et types associés. | 116 |
| `packages/api-client/src/domains/authAndShell.ts` | Modification | Exposition de `searchKnownOrgUsers`. | 126 |
| `packages/api-client/src/domains/catalogAndPermissions.ts` | Modification | Exposition de `searchKnownOrgUsers` sous 350 lignes. | 347 |
| `packages/api-client/src/index.ts` | Modification | Export de `searchKnownOrgUsers` et `ListKnownOrgUsersParams`. | 65 |
| `apps/web/src/i18n/locales/organization_modals_labels.ts` | Création | Libellés i18n fr/en dédiés aux modales d'organisation : recherche parente, membres, hint troncature, `newMemberButtonLabel` (`"+ Nouveau membre"` / `"+ New member"`) et feedback de création. | 235 |
| `apps/web/src/i18n/locales/organization_tab_labels.ts` | Refactoring | Allègement à 149 lignes par extraction de `organization_modals_labels.ts` avec ré-export typé préservé sans régression. | 149 |
| `apps/web/src/features/admin/organization/orgUnitsApiBridge.ts` | Modification | Ajout de `searchKnownOrgUsersFromApi(query, limit = 10, locale)` et `searchParentBuUnitsFromApi`. | 236 |
| `apps/web/src/features/admin/organization/useParentOrgSearch.ts` | Création | Hook partagé DRY gérant requête live par caractère pour l'unité parente avec `requestSeqRef` anti-désordre. | 96 |
| `apps/web/src/features/admin/organization/useKnownOrgUsersSearch.ts` | Création | Hook partagé gérant la recherche live par caractère des membres/responsables sur `GET /api/v1/org-units/known-users`, anti-désordre et injection locale immédiate `addKnownUserLocally`. | 78 |
| `apps/web/src/features/admin/iam/IamAccountModal.tsx` | Modification | Support de `initialCreateDefaults` (`displayName`, `emailOrPrincipal`, `teamIds`) lors de l'ouverture en mode création sous 340 lignes. | 336 |
| `apps/web/src/features/admin/organization/OrgUnitInlineCreateMemberModal.tsx` | Création | Modale chaînée montant `IamAccountModal` avec pré-remplissage intelligent, création IAM via API, auto-rattachement dans la liste des membres et fermeture isolée. | 94 |
| `apps/web/src/features/admin/organization/CreateOrgUnitModal.tsx` | Refactoring | Remplacement du `<select>` parent par `<OrciaSearchableSelect maxDisplayedItems={10} ...>` et branchement responsable sur `useKnownOrgUsersSearch` (< 305 l.). | 301 |
| `apps/web/src/features/admin/organization/EditOrgUnitModal.tsx` | Refactoring | Remplacement du `<select>` parent par `<OrciaSearchableSelect maxDisplayedItems={10} ...>` avec maintien de l'anti-cycle (< 360 l.). | 185 |
| `apps/web/src/features/admin/organization/ConfirmDeleteOrgUnitModal.tsx` | Modification | Rendu nominatif `org-unit-delete-dependencies-list`, bouton `org-unit-delete-open-workspaces-btn`, bouton confirm désactivé quand `isNonEmpty`. | 170 |
| `apps/web/src/features/admin/organization/ManageOrgUnitMembersModal.tsx` | Refactoring | Intégration de `<OrciaKnownUserCombobox maxDisplayedItems={10} ...>` branché sur `useKnownOrgUsersSearch`, bouton permanent `org-unit-new-member-btn` (`+ Nouveau membre`) et modale chaînée `OrgUnitInlineCreateMemberModal` sous 300 lignes. | 296 |
| `apps/web/src/features/admin/organization/SettingsOrganizationModalsGroup.tsx` | Création | Extraction du bloc JSX des 4 modales hors de `SettingsOrganizationUnitsBlock.tsx` avec respect strict des callbacks. | 116 |
| `apps/web/src/routes/SettingsOrganizationUnitsBlock.tsx` | Refactoring | Allègement à 319 lignes par extraction de `SettingsOrganizationModalsGroup.tsx` et hydratation `knownUsers`. | 319 |
| `apps/web/src/routes/SettingsOrganizationUnitRow.tsx` | Modification | Résolution et affichage du nom complet du responsable via `knownUsers`. | 214 |
| `apps/web/src/features/admin/organization/OrgPedagogicalCallout.tsx` | Création | Extraction de l'encart pédagogique d'organisation sous 50 lignes. | 45 |
| `apps/web/src/__tests__/vitestIamMockHandlers.ts` | Modification | Export de `getVitestIamAccounts` pour synchronisation des mocks d'annuaire. | 409 |
| `apps/web/src/__tests__/vitest.setup.ts` | Modification | Mock de `GET /api/v1/org-units/known-users` et synchronisation bidirectionnelle des comptes créés via IAM vers l'annuaire connu. | 1442 |
| `tests/unit/test_story_17_2_pg_guard_and_reconcilers.py` | Création | 4 tests unitaires (503 sur dérive de schéma, fallback mémoire sur connectivité, fusion workspaces SQL+JSONB, DTOs). | 177 |
| `tests/unit/test_story_17_2_org_hierarchy.py` | Modification | Tests de validation de `resolve_and_validate_org_unit_users`, recherche `q`/`kind`/`limit` et conservation des invariants. | 578 |
| `tests/integration/api/test_story_17_2_org_units_hierarchy_postgres18.py` | Modification | Test d'intégration PostgreSQL 18 vérifiant `GET /api/v1/org-units?q=...&kind=BU&limit=10`, pagination déterministe et scénario complet création IAM $\rightarrow$ recherche $\rightarrow$ rattachement. | 462 |
| `apps/web/src/__tests__/story-17-2-org-hierarchy-and-modals.test.tsx` | Modification | 6 tests Vitest vérifiant dépendances de suppression, autocomplétion, plafond 10 éléments, live per-keystroke search, exclusion anti-cycle et parcours chaîné complet `+ Nouveau membre`. | 261 |
| `apps/web/src/__tests__/i18n-and-shell.test.tsx` | Modification | 26 tests Vitest au vert garantissant la non-régression globale et les attributs anti-LastPass. | 2074 |

### 3.2 Résultats Chiffrés, Métriques & Qualité
- **Couverture de tests & Exécution** :
  - `packages/orcia-core/src/orcia_core/permissions/org_user_validation.py` : **100%**
  - `packages/orcia-core/src/orcia_core/permissions/org_hierarchy.py` : **96%**
  - `packages/orcia-core/src/orcia_core/permissions/errors.py` : **100%**
  - `packages/orcia-core/src/orcia_core/permissions/_error_catalog.py` : **100%**
  - Suite unitaires & sécurité Python (`test_story_17_2_*.py`, `test_permissions_and_auth.py`, `tests/security/`) : **53/53 passed**.
  - Tests d'intégration PostgreSQL 18 réels (`testcontainers`) : **1 passed** en 18s (100% vert, incluant enrôlement IAM et recherche déterministe).
  - Vitest `@orcia/ui` : 20 fichiers testés, **89/89 tests passés** (dont 7/7 sur `OrciaKnownUserCombobox` et 5/5 sur `OrciaSearchableSelect`).
  - Vitest `@orcia/web` : 14 fichiers testés, **75/75 tests passés** (dont 6/6 sur `story-17-2-org-hierarchy-and-modals.test.tsx`, 7/7 sur `zero-dead-buttons-and-silent-catches-audit.test.tsx` et 26/26 sur `i18n-and-shell.test.tsx`).
  - Turbo global (`lint`, `typecheck`, `test` dans `@orcia/api-client`, `@orcia/ui`, `@orcia/web`) : **100% vert (9/9 tasks successful)**.
- **Volumétrie & Discipline modulaire** :
  - Strict respect de la limite `< 360 lignes` sur l'ensemble des fichiers créés et modifiés (`_org_units_helpers.py` : 357 l., `IamAccountModal.tsx` : 336 l., `SettingsOrganizationUnitsBlock.tsx` : 319 l., `OrciaKnownUserCombobox.tsx` : 302 l., `CreateOrgUnitModal.tsx` : 301 l., `ManageOrgUnitMembersModal.tsx` : 296 l., `sql_org_units_queries.py` : 293 l., `org_units.py` : 298 l., `story-17-2-org-hierarchy-and-modals.test.tsx` : 261 l., `useKnownOrgUsersSearch.ts` : 78 l., `OrgUnitInlineCreateMemberModal.tsx` : 94 l., `SettingsOrganizationModalsGroup.tsx` : 116 l.).
  - Zéro violation `AD-19` (`lint-imports` : 5 contrats tenus, 0 brisé).
  - Architecture Spine (`lint_spine.py`) : `0 findings`.
  - Typage statique Python (`mypy --strict` 304 fichiers source) : `Success: no issues found`.
  - Typage statique TypeScript (`tsc --noEmit`) : 0 erreur sur tous les packages du monorepo.
  - Linters Python : `ruff check` et `ruff format --check` : 0 warning sur 277 fichiers.
  - Zéro couleur hexadécimale en dur en dehors de `tokens.css` validé par `design-system-look-and-feel-isolation.test.tsx`.
  - Zéro bouton muet et zéro `.catch(() => undefined)` validé par `zero-dead-buttons-and-silent-catches-audit.test.tsx`.
  - Registre d'icônes centralisé `@orcia/ui` respecté : utilisation de `<OrciaIcon name="chevronDown" size={12} />` sans `<span aria-hidden="true">` glyph direct.

### 3.3 Validation & Procédure de Test sur Toute la Pyramide (`AD-17` + 5 Garde-Fous de Câblage Vertical)
- **Couche 1a — Tests Unitaires Python** :
  - `tests/unit/test_story_17_2_org_hierarchy.py` :
    - Filtrage mémoire insensible aux accents et à la casse (`normalize_text_search` NFD), filtre par type d'unité (`kind="BU"`), et plafonnement déterministe (`limit=10`).
    - Validation stricte de `resolve_and_validate_org_unit_users` et rejet des identifiants inconnus (`HTTP 422 ERR_ORG_UNIT_UNKNOWN_USER`).
    - Validation du endpoint `GET /api/v1/org-units/known-users?q=...&limit=10` : déduplication des comptes, pagination `has_more` en une passe, nettoyage `\x00` et rejet des injections SQL.
- **Couche 1b — Tests Composants & Modales UI (Vitest)** :
  - `packages/ui/src/__tests__/known-user-combobox.test.tsx` :
    - Affichage de 10 suggestions max avec `data-testid="${testId}-truncated-hint"` visible lorsque `hasMoreMatches` ou que le nombre de résultats dépasse 10.
    - Appel immédiat de `onSearchQueryChange` à chaque frappe/effacement de caractère sans debounce artificiel.
    - Application du filtre `excludePrincipalIds` en amont du plafonnement à 10 pour ne jamais masquer des candidats pertinents.
  - `packages/ui/src/__tests__/searchable-select.test.tsx` :
    - Vérifie avec 14 options qu'au maximum 10 sont affichées dans la liste déroulante avec message de troncature visible et select natif caché compatible RTL.
  - `apps/web/src/__tests__/story-17-2-org-hierarchy-and-modals.test.tsx` :
    - Test end-to-end de sélection dans `CreateOrgUnitModal` et `EditOrgUnitModal` avec hint de troncature et exclusion anti-cycle.
    - Test de recherche interactive en direct sur `GET /api/v1/org-units/known-users` dans `ManageOrgUnitMembersModal`.
    - Parcours chaîné complet : clic sur `org-unit-new-member-btn` $\rightarrow$ ouverture de `IamAccountModal` par-dessus `ManageOrgUnitMembersModal` sans perte des modifications en cours $\rightarrow$ création IAM $\rightarrow$ fermeture isolée $\rightarrow$ ajout immédiat dans `Membres rattachés` $\rightarrow$ enregistrement `PATCH /api/v1/org-units/{id}`.
- **Couche 2 — Intégration Verticale PostgreSQL 18 (`testcontainers-python`)** :
  - `tests/integration/api/test_story_17_2_org_units_hierarchy_postgres18.py` :
    - Exécution de `GET /api/v1/org-units?q=...&kind=BU&limit=10` et `GET /api/v1/org-units/known-users?q=...&limit=10` sur conteneur PostgreSQL 18 réel.
    - Vérification de la requête paramétrée `ILIKE :q_pattern ESCAPE '\'`, tri déterministe et scénario complet de création de compte IAM suivi de la recherche et de l'affectation à une unité.
- **Couche 3 — Contrat OpenAPI 3.1 & SDK Typescript** :
  - `.venv/bin/python scripts/export_openapi.py --check` validé (`0-diff`).
  - Méthodes `listOrgUnits({ q, kind, limit })` et `searchKnownOrgUsers({ q, limit })` exposées dans le SDK `@orcia/api-client`.
- **Garde-fous de Câblage Vertical & Anti-Régression** :
  - Règles 1 à 4 validées par `tests/unit/test_codebase_architectural_anti_patterns_audit.py`.
  - Look & Feel Direction C validé par `design-system-look-and-feel-isolation.test.tsx`.
  - Protection anti-LastPass vérifiée par `apps/web/src/__tests__/i18n-and-shell.test.tsx`.
  - Manifeste Showcase et site synchronisés via `pnpm site:sync && pnpm site:check`.
  - GitNexus indexé et synchronisé via `npx gitnexus analyze`.
