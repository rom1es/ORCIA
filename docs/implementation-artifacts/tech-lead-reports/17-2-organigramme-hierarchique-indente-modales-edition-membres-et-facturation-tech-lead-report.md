# Rapport Tech Lead — Story 17.2 : Organigramme Hiérarchique Indenté, Modales d'Édition / Membres / Facturation & Suppression Sécurisée

- **Clé de Story / Slug** : `17-2-organigramme-hierarchique-indente-modales-edition-membres-et-facturation`
- **Date** : `2026-11-11`
- **Épopée** : `Epic 17 — Refonte Configuration, Identités & Habilitations (IAM), Organigramme Multi-Niveaux & Shell`
- **Capacité(s) (`docs/product/capabilities.yaml`)** : `CAP-051` (*Administration & gouvernance organisationnelle : BU, Équipes, Règles RBAC*), `CAP-067` (*Organigramme hiérarchique multi-niveaux `BU → Sous-BU / Pôle → Équipe`, CRUD `/api/v1/org-units`, modales d'édition/membres/facturation & suppression sécurisée HTTP 409*) — classification : **`feature`**
- **Statut** : `done` (Sections 1 & 2 rédigées avant modification du code applicatif ; Section 3 complétée après passage des 5 couches `AD-17`)

---

## 1. Analyse du Besoin & Étude d'Impact Tech Lead

### 1.1 Synthèse Critique de la User Story & Cadrage Produit
La **Story 17.2** refond intégralement la gestion de l'organigramme dans **`Configuration › Organisation`** (`/settings`, onglet `Organisation`) ainsi que sa persistance verticale PostgreSQL 18 (`/api/v1/org-units`) selon les décisions verrouillées lors du cadrage produit (`FR22`, `FR23`, `UX-DR1`) :
1. **CA-17.2.1 — Arbre hiérarchique visuel indenté & pédagogie BU / Pôle / Équipe / Espace** :
   - Remplacer l'ancienne liste plate par un arbre hiérarchique indenté multi-niveaux (`Direction / BU` racine $\rightarrow$ `Pôle / Sous-BU` enfant $\rightarrow$ `Équipe` rattachée à une BU ou un Pôle), affichant sur chaque nœud son badge de type, son identifiant court (`slug`), son responsable (`lead_user_id` le cas échéant), le compteur de membres (`0 membre`, `1 membre`, `N membres`), le compteur d'espaces rattachés (`0 espace`, `1 espace`, `N espaces`) et l'état d'imputation FinOps (`billing_enabled`).
   - Ajouter un encart pédagogique concis distinguant **Direction / BU & Pôle** (structure hiérarchique de pilotage), **Équipe** (collectif humain & imputation FinOps) et **Espace** (cadre de travail métier/produit rattaché à une équipe, administré dans **`Mes Espaces`** avec lien/bouton direct vers `/workspaces`).
2. **CA-17.2.2 — Modales dédiées de Création, Édition et Gestion des Membres & Purge des contrôles personnels** :
   - Purger de l'administration globale `Organisation` tout contrôle personnel propre au compte connecté (`admin-team-membership-summary-badge`, `org-unit-attach-admin-checkbox`, boutons *« Retirer mon rattachement / + Rattacher mon compte »*), tout en conservant `toggleAdminTeamMembership` et `memberTeamIds` dans `platformSetupStore.tsx` pour la compatibilité des assistants Jour 0.
   - Remplacer le formulaire inline par **3 modales RGAA dédiées** (`RgaaModalDialog`) :
     1. **`CreateOrgUnitModal`** (`+ Nouvelle unité`) : sélecteur de type (`Direction / BU` ou `Équipe`), champ large `Nom`, champ large `Identifiant court (optionnel)` sur sa propre ligne/colonne (zéro placeholder tronqué), **sélecteur `Unité parente` visible pour tous les types** (pour `Équipe` : présélectionne automatiquement la **première BU existante** dès qu'au moins une BU existe ; pour `BU` : propose `Racine — Direction de premier niveau` ou le rattachement sous une BU existante pour modéliser un Pôle / Sous-Direction), case `Activer l'imputation FinOps` (`billing_enabled`) et champ optionnel `Responsable` (`lead_user_id`).
     2. **`EditOrgUnitModal`** (`Modifier`) : renommage (`name`), changement d'`Unité parente` (`parent_id` filtrant le nœud lui-même et ses descendants pour empêcher tout cycle, et interdisant le rattachement d'une `BU` sous une `TEAM`), et bascule `billing_enabled`, câblée sur `PATCH /api/v1/org-units/{id}`.
     3. **`ManageOrgUnitMembersModal`** (`Membres`) : désignation/modification du responsable (`lead_user_id` : `BU_LEAD` / `TEAM_LEAD`) et ajout/retrait des membres (`member_user_ids`), câblée sur `PATCH /api/v1/org-units/{id}`.
3. **CA-17.2.3 — Suppression sécurisée (`HTTP 409 ERR_ORG_UNIT_NOT_EMPTY`) & bouton rouge `.orcia-ds-btn-danger`** :
   - Remplacer le bouton texte neutre par un bouton `.orcia-ds-btn-danger` ouvrant **`ConfirmDeleteOrgUnitModal`**.
   - Si l'unité possède au moins une sous-unité enfant (`parent_id == org_unit_id`) ou un espace de travail rattaché (`workspaces.owner_org_unit_id == org_unit_id`), bloquer la suppression côté UI avec un message explicite **et** rejeter côté serveur `DELETE /api/v1/org-units/{id}` avec **`HTTP 409 Conflict` (`ERR_ORG_UNIT_NOT_EMPTY`)** au format RFC 9457 Problem Details détaillant le nombre d'éléments enfants / espaces à déplacer ou supprimer d'abord.
   - Si l'unité est vide mais a `billing_enabled == true`, afficher un avertissement FinOps explicite avant confirmation définitive.
   - Toute mutation (`POST`, `PATCH`, `DELETE`) applique la garde `READ_ONLY_OBSERVER` / `OBSERVER` (`HTTP 403 ERR_OBSERVER_MODE_READ_ONLY`) et le verrouillage RBAC côté UI (`canMutate`).

### 1.2 Analyse d'Impact GitNexus (Rayon d'Explosion)
Exécutée sur le graphe d'indexation ORCIA (`repo: "ORCIA"`) :
- **`MatrixPermissionEvaluator`** (`packages/orcia-core/src/orcia_core/permissions/evaluator.py:L34-300`) : `8` modules entrants dans `orcia_core` (`catalog`, `orchestration`, `permissions/broker.py`, `permissions/service.py`). Les méthodes `get_ancestor_org_unit_ids` et `get_descendant_org_unit_ids` parcourent déjà récursivement `parent_id` quel que soit le nombre de niveaux (`BU → Sous-BU → TEAM`) ! Enrichir `OrgUnitNode` avec des valeurs par défaut rétrocompatibles (`billing_enabled: bool = True`, `lead_user_id: str | None = None`, `member_user_ids: tuple[str, ...] = ()`) préserve `100 %` des appelants existants.
- **`sync_relational_tables_on_postgres18`** (`packages/orcia-core/src/orcia_core/bootstrap/_internal/sql_platform_setup_relational_sync.py`) : `impactedCount = 42`, risque `MEDIUM` (`5` processus affectés). **Anomalie identifiée lors de l'audit** : le tri `sorted(org_units, key=lambda u: 0 if level == "BU" else 1)` ne triait pas topologiquement une `Sous-BU` par rapport à sa `BU` parente et rabattait silencieusement `parent_id` sur `ROOT_ORG_UNIT_ID` si l'enfant précédait son parent. De même, `_reconcile_org_units_on_load` dans `sql_platform_setup_store.py` omettait `billingEnabled`, `leadUserId` et `memberUserIds`. Ces deux points ont été corrigés.
- **`SettingsOrganizationUnitsBlock`** (`apps/web/src/routes/SettingsOrganizationUnitsBlock.tsx`) : appelé par `apps/web/src/routes/settings.tsx` et couvert par `story-17-1-settings-5-tabs-and-rbac.test.tsx`, `i18n-and-shell.test.tsx` et `apps/web/e2e/support/orgAndWorkspace.ts` / `11-screens-smoke-without-server-errors.spec.ts`.

### 1.3 Opportunités de Factorisation & Contrôle de Volumétrie (`<= 400` lignes)
- **Découpage modulaire Frontend (`apps/web/src/features/admin/organization/`)** : au lieu d'alourdir `SettingsOrganizationUnitsBlock.tsx` (`399` lignes) ou `platformSetupStore.tsx`, la fonctionnalité est découpée dans la tranche `admin` existante (`AD-19` feature-slice isolation) en `6` petits modules dédiés (`138` à `243` lignes chacun) :
  1. `orgTreeHelpers.ts` : construction pure de l'arbre DFS indenté (`depth`), détection des descendants (anti-cycle) et compteurs.
  2. `orgUnitsApiBridge.ts` : pont typé `@orcia/api-client` (`listOrgUnits`, `createOrgUnit`, `updateOrgUnit`, `deleteOrgUnit`) + normalisation `OrgUnitResponse` $\leftrightarrow$ `ConfiguredOrgUnit` et extraction propre des messages RFC 9457 Problem Details.
  3. `CreateOrgUnitModal.tsx` : modale RGAA de création (`BU`, `Sous-BU`, `TEAM`).
  4. `EditOrgUnitModal.tsx` : modale RGAA d'édition (`name`, `parent_id`, `billing_enabled`).
  5. `ManageOrgUnitMembersModal.tsx` : modale RGAA de gouvernance du responsable et des membres (`lead_user_id`, `member_user_ids`).
  6. `ConfirmDeleteOrgUnitModal.tsx` : modale RGAA de suppression sécurisée (`.orcia-ds-btn-danger`, blocage non-vide, alerte FinOps).
- **Découpage Backend & Pureté Hexagonale (`AD-1` / `AD-19`)** :
  - `packages/orcia-core/src/orcia_core/permissions/org_hierarchy.py` (`289` lignes, `0` import framework/SQL) : invariants purs du domaine (validation parent `BU`/`TEAM`, détection de cycle sur graphe `parent_id`, tri topologique multi-niveaux, garde de suppression non-vide).
  - `packages/orcia-core/src/orcia_core/bootstrap/_internal/sql_org_units.py` (`362` lignes) : persistance PostgreSQL 18 asynchrone sans requête `N+1` (`LEFT JOIN` agrégé sur `workspaces`) co-localisée avec `sql_platform_setup_relational_sync.py` et ré-exportée via `orcia_core.bootstrap`, préservant `100 %` de pureté sans SQLAlchemy dans `orcia_core.permissions`.
  - `apps/api/src/orcia_api/routers/org_units.py` (`396` lignes) : routeur FastAPI dédié `/api/v1/org-units`.

---

## 2. Plan d'Implémentation

### 2.1 Migration de Schéma PostgreSQL 18 (`infra/migrations/versions/`)
- Créer la révision incrémentale réversible `infra/migrations/versions/20261111_1702_story_17_2_org_units_billing_and_members.py` (`revision = "20261111_1702"`, `down_revision = "20261108_0910"`, SQL brut via `op.execute(sa.text(...))`, zéro import ORM) ajoutant sur `org_units` :
  - `billing_enabled BOOLEAN NOT NULL DEFAULT TRUE`
  - `lead_user_id VARCHAR(128) NULL`
  - `member_user_ids_jsonb JSONB NOT NULL DEFAULT '[]'::jsonb`

### 2.2 Noyau Hexagonal (`packages/orcia-core`)
- **`orcia_core/permissions/errors.py` & `orcia_api/errors/registry.py`** : ajouter et enregistrer `OrgUnitDuplicateSlugError` (`HTTP 409 ERR_ORG_UNIT_DUPLICATE_SLUG`), `OrgUnitInvalidParentKindError` (`HTTP 422 ERR_ORG_UNIT_INVALID_PARENT_KIND`), `OrgUnitHierarchyCycleError` (`HTTP 422 ERR_ORG_UNIT_HIERARCHY_CYCLE`) et `OrgUnitNotEmptyError` (`HTTP 409 ERR_ORG_UNIT_NOT_EMPTY`) avec traductions `fr` et `en`.
- **`orcia_core/permissions/models.py` & `org_hierarchy.py`** : enrichir `OrgUnitNode` (`billing_enabled`, `lead_user_id`, `member_user_ids`), implémenter la validation anti-cycle, l'interdiction de rattacher une `BU` sous une `TEAM`, le tri topologique multi-niveaux et les méthodes CRUD en mémoire dans `MatrixPermissionEvaluator`.
- **`orcia_core/bootstrap/_internal/sql_org_units.py`** : implémenter `list_org_units_from_postgres18` (`LEFT JOIN` agrégé sur `workspaces` sans `N+1`), `create_org_unit_on_postgres18` (`UUIDv7`), `update_org_unit_on_postgres18` et `delete_org_unit_on_postgres18` (`409 ERR_ORG_UNIT_NOT_EMPTY` si sous-unités ou espaces rattachés), plus la synchronisation cohérente du snapshot `platform_setup_state_v1`.
- **`orcia_core/bootstrap/_internal/sql_platform_setup_relational_sync.py` & `sql_platform_setup_store.py`** : remplacer le tri binaire `BU/TEAM` par `sort_org_unit_dicts_topologically` (`BU → Sous-BU → TEAM`) et propager `billing_enabled`, `lead_user_id` et `member_user_ids_jsonb` dans les deux sens.

### 2.3 Backend FastAPI & SDK OpenAPI 3.1 (`apps/api` & `packages/api-client`)
- **`apps/api/src/orcia_api/schemas/auth_and_org.py`** : définir `OrgUnitResponse`, `OrgUnitsListResponse`, `OrgUnitCreateRequest`, `OrgUnitPatchRequest` et `OrgUnitDeleteResponse`.
- **`apps/api/src/orcia_api/routers/org_units.py`** (inclus dans `org_and_workspaces.py`) : exposer `GET /api/v1/org-units`, `POST /api/v1/org-units`, `PATCH /api/v1/org-units/{org_unit_id}` et `DELETE /api/v1/org-units/{org_unit_id}` avec garde `ObserverModeReadOnlyError` (`HTTP 403`), validation de hiérarchie (`HTTP 422`), protection non-vide (`HTTP 409`) et mise à jour synchronisée de `MatrixPermissionEvaluator` + PostgreSQL 18.
- **Régénération SDK (`0-diff`)** : exécuter `.venv/bin/python scripts/export_openapi.py` et exposer `listOrgUnits`, `createOrgUnit`, `updateOrgUnit` et `deleteOrgUnit` dans `packages/api-client/src/domains/authAndShell.ts` et `catalogAndPermissions.ts`.

### 2.4 Interface SPA Direction C (`apps/web`)
- **`apps/web/src/i18n/locales/admin_and_studio_labels.ts`** : ajouter la section bilingue `fr` / `en` complète pour l'encart pédagogique, l'arbre hiérarchique et les 4 modales (zéro chaîne codée en dur en JSX).
- **`apps/web/src/features/admin/organization/*` & `SettingsOrganizationUnitsBlock.tsx` / `SettingsOrganizationUnitRow.tsx`** :
  - Encart pédagogique distinguant `Direction / BU & Pôle`, `Équipe` et `Espace` + bouton de navigation directe vers `/workspaces`.
  - Hydratation `GET /api/v1/org-units` au montage (survie complète au `F5`) et synchronisation avec `platformSetupStore`.
  - Arbre visuel indenté multi-niveaux, badges Direction C (zéro hex brut, zéro violet `#6D28D9`), purge totale des contrôles personnels et intégration des 4 modales RGAA (`CreateOrgUnitModal`, `EditOrgUnitModal`, `ManageOrgUnitMembersModal`, `ConfirmDeleteOrgUnitModal`) avec attributs anti-LastPass sur 100 % des `<form>` et `<input>`.

---

## 3. Bilan des Modifications & Résultats

### 3.1 Fichiers Créés & Modifiés (Volumétrie Maîtrisée `<= 400` lignes sur les modules Story 17.2)

| Fichier | Nature | Rôle & Responsabilité |
|---|---|---|
| `infra/migrations/versions/20261111_1702_story_17_2_org_units_billing_and_members.py` | Créé (`47` l.) | Migration Alembic réversible (`upgrade` / `downgrade`) ajoutant `billing_enabled`, `lead_user_id` et `member_user_ids_jsonb` sur `org_units`. |
| `packages/orcia-core/src/orcia_core/permissions/org_hierarchy.py` | Créé (`289` l.) | Invariants purs du domaine (`0` import SQL/framework) : normalisation slug/membres, UUIDv7, anti-cycle multi-niveaux, validation `BU`/`TEAM`, garde suppression non-vide et tri DFS/topologique. |
| `packages/orcia-core/src/orcia_core/bootstrap/_internal/sql_org_units.py` | Créé (`362` l.) | Persistance PostgreSQL 18 asynchrone sans `N+1` (`LEFT JOIN` sur `workspaces`) + synchronisation atomique `platform_setup_state_v1`. |
| `packages/orcia-core/src/orcia_core/bootstrap/_internal/sql_platform_setup_relational_sync.py` & `sql_platform_setup_store.py` | Modifié | Tri topologique multi-niveaux `BU → Sous-BU → TEAM` et réconciliation bidirectionnelle `billing_enabled`, `lead_user_id`, `member_user_ids_jsonb`. |
| `packages/orcia-core/src/orcia_core/permissions/{models,evaluator,errors,__init__}.py` | Modifié | Enrichissement `OrgUnitNode`, CRUD mémoire `MatrixPermissionEvaluator`, erreurs typées `ERR_ORG_UNIT_*`. |
| `apps/api/src/orcia_api/routers/org_units.py` & `schemas/auth_and_org.py` & `errors/registry.py` | Créé (`396` l.) / Modifié | Endpoints `GET/POST/PATCH/DELETE /api/v1/org-units`, gardes RBAC / `READ_ONLY_OBSERVER` (`403`) et mappage RFC 9457 (`409` / `422` `fr`/`en`). |
| `packages/api-client/openapi.json` & `src/generated/*` & `src/domains/{authAndShell,catalogAndPermissions}.ts` | Généré / Modifié | SDK OpenAPI 3.1 régénéré (`0-diff`) exposant `listOrgUnits`, `createOrgUnit`, `updateOrgUnit`, `deleteOrgUnit`. |
| `apps/web/src/features/admin/organization/{orgTreeHelpers.ts,orgUnitsApiBridge.ts,CreateOrgUnitModal.tsx,EditOrgUnitModal.tsx,ManageOrgUnitMembersModal.tsx,ConfirmDeleteOrgUnitModal.tsx}` | Créé (`6` fichiers, `138`–`243` l.) | Construction de l'arbre DFS indenté, pont `@orcia/api-client` + extraction RFC 9457, et 4 modales RGAA avec anti-LastPass complet. |
| `apps/web/src/routes/SettingsOrganizationUnitsBlock.tsx` (`399` l.) & `SettingsOrganizationUnitRow.tsx` (`218` l.) & `settings.tsx` | Modifié | Encart pédagogique `BU / Équipe / Espace` + CTA `/workspaces`, arbre indenté multi-niveaux, purge des contrôles personnels et câblage complet des 4 modales + `F5`. |
| `tests/unit/test_story_17_2_org_hierarchy.py` (`386` l.), `tests/integration/api/test_story_17_2_org_units_hierarchy_postgres18.py` (`290` l.), `apps/web/src/__tests__/story-17-2-org-hierarchy-and-modals.test.tsx` (`382` l.) | Créé | Couverture unitaire Python, intégration verticale `testcontainers` PostgreSQL 18 (avec `upgrade` $\rightarrow$ `downgrade` $\rightarrow$ `upgrade`) et tests UI Vitest + survie `F5`. |

### 3.2 Validation des 5 Couches de Tests `AD-17` & Gates Anti-Régression

1. **Analyse Statique, Pureté Hexagonale & Frontières `AD-19`** :
   - `.venv/bin/ruff check .` & `.venv/bin/ruff format --check .` : **`0` erreur sur `666` fichiers**.
   - `.venv/bin/lint-imports` : **`5/5` contrats respectés (`0` cycle, `0` import interdit sur `306` modules)**.
   - `.venv/bin/mypy --strict packages/orcia-core packages/orcia-connectors apps/api apps/worker` : **`Success: no issues found in 271 source files`**.
   - `tests/unit/test_permissions_and_auth.py::test_hexagonal_purity_permissions_package` & `tests/unit/test_codebase_architectural_anti_patterns_audit.py` : **`100 %` PASS (`0` import `sqlalchemy`/`fastapi` dans `orcia_core.permissions`)**.
2. **Couche 1 & Couche 2 (`AD-17`) — Tests Unitaires & Intégration Verticale HTTP $\rightarrow$ PostgreSQL 18 (`testcontainers`)** :
   - `test_story_17_2_org_hierarchy.py` + `test_story_17_2_org_units_hierarchy_postgres18.py` : **PASS (`100 %`)**, vérifiant sur conteneur réel `pgvector/pgvector:pg18` la réversibilité Alembic `20261111_1702`, l'arbre 3 niveaux `BU → Sous-BU → TEAM`, les `SELECT` SQL directs (`billing_enabled`, `lead_user_id`, `member_user_ids_jsonb`), les rejets `422` (`ERR_ORG_UNIT_INVALID_PARENT_KIND`, `ERR_ORG_UNIT_HIERARCHY_CYCLE`), `409` (`ERR_ORG_UNIT_DUPLICATE_SLUG`, `ERR_ORG_UNIT_NOT_EMPTY`), et `403` (`ERR_OBSERVER_MODE_READ_ONLY`, `ERR_SCOPE_ACCESS_DENIED`).
   - **Couverture mesurée** (`--cov-fail-under=90`) : **`94.76 %`** global (`org_hierarchy.py` : **`97 %`**, `sql_org_units.py` : **`96 %`**, `org_units.py` : **`91 %`**).
3. **Couche 3 (`AD-17`) — Contrat OpenAPI 3.1 `0-diff` & Fuzzing Schemathesis** :
   - `.venv/bin/python scripts/export_openapi.py` : **`0-diff`**.
   - `.venv/bin/pytest tests/contract/test_openapi_contract.py` : **`2/2` PASS**.
4. **Couche 4 (`AD-17`) — Frontend TypeScript, Design System `@orcia/ui`, Isolation Feature-Slice & Survie `F5`** :
   - `pnpm turbo run lint typecheck test` : **`9/9` tâches Turbo vertes, `11/11` fichiers Vitest (`60/60` tests PASS)** incluant `story-17-2-org-hierarchy-and-modals.test.tsx`, `i18n-and-shell.test.tsx`, `zero-dead-buttons-and-silent-catches-audit.test.tsx` et `design-system-look-and-feel-isolation.test.tsx`.
5. **Registre des Capacités, Synchronisation `/showcase` & Spine Lint** :
   - `CAP-067` mis à jour dans `docs/product/capabilities.yaml`, `sprint-status.yaml` basculé à `done` pour `17-2` (`ready-for-dev` pour `17-3`), `pnpm site:sync && pnpm site:check` et `lint_spine.py` validés avec **`0` anomalie**.
