# 2026-11-14 — Blocage Suppression Unité d'Organisation, Garde Schéma PostgreSQL & Modale de Dépendances (`CAP-067`)

- **Date** : `2026-11-14`
- **Story / Clé Sprint** : `2026-11-14-suppression-org-unit-garde-pg-et-modale-dependances` (`Ajustement Transverse` — `CAP-067` / post-`Story 17.2`)
- **Capacité(s)** : `CAP-067` (*Organigramme hiérarchique multi-niveaux (BU / Sous-BU / Équipe), modales d'édition/membres/facturation, espaces privés et sélecteur de contexte*) — classification : **`hygiène`** / **`ux`**
- **Auteur / Contexte** : Correctif transverse suite à l'incident terrain sur « Sous-Équipe Checkout & Core Solutions » impossible à supprimer (`3 Espaces de Travail rattachés` fantômes absents du Scope Switcher et de l'écran `/workspaces`). Couverture des exigences `FR-3`, `FR-22`, `FR-23`, `AD-19`, `NFR-A11Y-1` et des garde-fous anti-pannes silencieuses (`GEMINI.md`).
- **Commits associés** : Modifications validées et prêtes dans le working tree sur la branche `fix/org-unit-delete-modal-and-pg-schema-guard` (prêtes pour commit et revue finale).

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
- `packages/orcia-core/src/orcia_core/permissions/errors.py` & `__init__.py` :
  - Ajouter `OrgUnitStorageSchemaError` héritant de `OrciaDomainError` (code stable `ERR_ORG_STORAGE_SCHEMA_OUTDATED`, statut HTTP `503`) sans import framework SQLAlchemy/FastAPI (`AD-19`).
- `packages/orcia-core/src/orcia_core/permissions/org_hierarchy.py` :
  - Définir `AttachedWorkspaceRef(id: str, slug: str, name: str)` et enrichir `OrgUnitSummary` avec `attached_workspaces: tuple[AttachedWorkspaceRef, ...] = ()`.
- `packages/orcia-core/src/orcia_core/bootstrap/_internal/sql_org_units_queries.py` & `sql_org_units.py` :
  - Enrichir la sous-requête agrégée `LEFT JOIN` sur `workspaces` avec `COALESCE(ws.attached_ws_json, '[]'::jsonb)` calculée via `jsonb_agg(jsonb_build_object('id', w.id::text, 'slug', w.slug, 'name', w.name) ORDER BY w.name)` — zéro requête `N+1`.
- `packages/orcia-core/src/orcia_core/bootstrap/_internal/sql_platform_setup_reconcilers.py` & `sql_platform_setup_store.py` :
  - Supprimer le court-circuit `if not workspaces:` dans `reconcile_workspaces_on_load` afin de fusionner systématiquement les lignes relationnelles `workspaces` dans l'état retourné (matching dédupliqué par `workspaceId` / `slug` normalisé).

### 2.3 Couche Backend API, Sécurité & Contrats (`apps/api/`, `packages/api-client/`)
- `apps/api/src/orcia_api/errors/registry.py` :
  - Enregistrer `OrgUnitStorageSchemaError` (`503`, `ERR_ORG_STORAGE_SCHEMA_OUTDATED`, enveloppe RFC 9457 bilingue `fr`/`en` expliquant qu'une migration de schéma PostgreSQL est requise).
- `apps/api/src/orcia_api/schemas/auth_and_org.py` :
  - Ajouter `AttachedWorkspaceRefResponse` (`id`, `slug`, `name`) et le champ `attached_workspaces: list[AttachedWorkspaceRefResponse] = Field(default_factory=list)` sur `OrgUnitResponse`.
- `apps/api/src/orcia_api/routers/_org_units_helpers.py` & `org_units.py` :
  - Remplacer le `except Exception:` aveugle par une distinction nette dans un helper partagé :
    - Connectivité PostgreSQL indisponible (`OSError`, `TimeoutError`, ou erreur pilote `InterfaceError` / `OperationalError` encapsulant une défaillance socket) ou `ORCIA_DISABLE_PG_BOOTSTRAP_SYNC=1` $\rightarrow$ fallback mémoire `svc.evaluator` préservé pour les tests unitaires hors conteneur ;
    - Erreur SQL de schéma/requête (`ProgrammingError`, `DBAPIError` post-connexion) $\rightarrow$ log `logger.error("org_units_pg_schema_error", ...)` et relance de `OrgUnitStorageSchemaError` (`HTTP 503`), empêchant toute injection de `seeds.py` sur une base active.
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
| `packages/orcia-core/src/orcia_core/permissions/_error_catalog.py` | Création | Extraction du catalogue d'erreurs `permissions` et ajout du code `ERR_ORG_STORAGE_SCHEMA_OUTDATED` (503). | 240 |
| `packages/orcia-core/src/orcia_core/permissions/errors.py` | Refactoring | Export de `OrgUnitStorageSchemaError(OrciaDomainError)` sous strict respect `AD-19`. | 184 |
| `packages/orcia-core/src/orcia_core/permissions/org_hierarchy.py` | Modification | Dataclass `AttachedWorkspaceRef`, enrichissement de `OrgUnitSummary.attached_workspaces` et mise à jour de `build_org_unit_summary` / `list_evaluator_org_unit_summaries`. | 351 |
| `packages/orcia-core/src/orcia_core/permissions/__init__.py` | Modification | Ré-export propre de `OrgUnitStorageSchemaError` et `AttachedWorkspaceRef`. | 341 |
| `packages/orcia-core/src/orcia_core/bootstrap/_internal/sql_org_units_queries.py` | Création | Extraction modulaire des requêtes SQL et helpers de lecture avec sous-requête `jsonb_agg` sur `workspaces` (zéro `N+1`). | 207 |
| `packages/orcia-core/src/orcia_core/bootstrap/_internal/sql_org_units.py` | Refactoring | Allègement sous 300 lignes en s'appuyant sur `sql_org_units_queries.py`. | 254 |
| `packages/orcia-core/src/orcia_core/bootstrap/_internal/sql_platform_setup_reconcilers.py` | Création | Extraction et refonte de la réconciliation SQL/JSONB: suppression du court-circuit `if not workspaces:` pour fusionner les espaces relationnels. | 246 |
| `packages/orcia-core/src/orcia_core/bootstrap/_internal/sql_platform_setup_store.py` | Refactoring | Allègement sous 300 lignes avec ré-export rétrocompatible des fonctions de réconciliation. | 284 |
| `apps/api/src/orcia_api/errors/registry.py` | Modification | Enregistrement de `OrgUnitStorageSchemaError` (503, RFC 9457 bilingue fr/en). | 174 |
| `apps/api/src/orcia_api/schemas/auth_and_org.py` | Modification | Modèle `AttachedWorkspaceRefResponse` et champ `attached_workspaces` sur `OrgUnitResponse`. | 357 |
| `apps/api/src/orcia_api/routers/_org_units_helpers.py` | Création | Helpers de mapping DTO avec `attached_workspaces`, synchro évaluateur et classification fine des erreurs PostgreSQL vs mémoire. | 316 |
| `apps/api/src/orcia_api/routers/org_units.py` | Refactoring | Découpage sous 280 lignes, classification stricte (503 sur `ProgrammingError` / dérive schéma, zéro fallback `seeds.py` silencieux). | 219 |
| `packages/api-client/openapi.json` | Génération | Schéma OpenAPI 3.1 mis à jour. | - |
| `packages/api-client/src/generated/auth_and_org.ts` | Génération | DTOs TypeScript régénérés (`AttachedWorkspaceRefResponse`, `OrgUnitResponse.attached_workspaces`). | - |
| `packages/api-client/src/generated/schema.ts` | Génération | Index de schéma régénéré (0-diff vérifié). | - |
| `apps/web/src/i18n/locales/organization_tab_labels.ts` | Modification | Clés i18n fr/en pour en-tête des dépendances, préfixes sous-unité/espace, action d'ouverture et texte d'aide cohérent. | 308 |
| `apps/web/src/components/platformSetupStorageHelpers.ts` | Modification | Types `AttachedWorkspaceRef` et `attachedWorkspaces` sur `ConfiguredOrgUnit`. | 345 |
| `apps/web/src/features/admin/organization/orgUnitsApiBridge.ts` | Modification | Propagation de `attachedWorkspaces` depuis `OrgUnitResponse`. | 134 |
| `apps/web/src/features/admin/organization/orgTreeHelpers.ts` | Modification | `OrgTreeRowItem` enrichi de `childUnits` et `attachedWorkspaces` (priorité API avec fallback store). | 211 |
| `apps/web/src/features/admin/organization/ConfirmDeleteOrgUnitModal.tsx` | Modification | Rendu nominatif `org-unit-delete-dependencies-list`, bouton `org-unit-delete-open-workspaces-btn`, bouton confirm désactivé quand `isNonEmpty`. | 170 |
| `apps/web/src/features/admin/organization/OrgPedagogicalCallout.tsx` | Création | Extraction de l'encart pédagogique d'organisation sous 50 lignes. | 45 |
| `apps/web/src/routes/SettingsOrganizationUnitsBlock.tsx` | Refactoring | Découpage sous 350 lignes, intégration de l'encart et passage de `onOpenWorkspaces` vers `/workspaces`. | 343 |
| `tests/unit/test_story_17_2_pg_guard_and_reconcilers.py` | Création | 4 tests unitaires (503 sur dérive de schéma, fallback mémoire sur connectivité, fusion workspaces SQL+JSONB, DTOs). | 177 |
| `tests/integration/api/test_story_17_2_org_units_hierarchy_postgres18.py` | Modification | Test d'intégration PostgreSQL 18 vérifiant l'hydratation de `attached_workspaces` depuis la base. | 288 |
| `apps/web/src/__tests__/story-17-2-org-hierarchy-and-modals.test.tsx` | Modification | 3 tests Vitest vérifiant la liste des dépendances, la désactivation du bouton confirm et le retour 409 concurrent. | 254 |
| `apps/web/src/__tests__/i18n-and-shell.test.tsx` | Modification | Adaptation des tests de blocage orphelin à la nouvelle modale désactivée et son bandeau. | 2074 |

### 3.2 Résultats Chiffrés, Métriques & Qualité
- **Couverture de tests** :
  - `packages/orcia-core/src/orcia_core/permissions/org_hierarchy.py` : **96%**
  - `packages/orcia-core/src/orcia_core/permissions/errors.py` : **100%**
  - `packages/orcia-core/src/orcia_core/permissions/_error_catalog.py` : **100%**
  - Suite ciblée `test_story_17_2_*.py` : 8 passed.
  - Tests d'intégration PostgreSQL 18 réels (`testcontainers`) : 1 passed en ~64s.
  - Tests contractuels OpenAPI & anti-patterns audit : 6 passed.
  - Vitest `@orcia/web` : 14 fichiers testés, 72/72 tests passés (`story-17-2`, `zero-dead-buttons-and-silent-catches-audit`, `i18n-and-shell`, etc.).
  - Turbo global (`lint`, `typecheck`, `test` dans les 3 packages web/ui/api-client) : **9/9 tâches réussies**.
- **Volumétrie & Discipline modulaire** :
  - Zéro fichier dépassant 360 lignes (tous les fichiers créés/refactorisés sont strictement `< 360` l., avec la plupart `< 300` l.).
  - Zéro violation `AD-19` (`lint-imports` : 5 contrats tenus, 0 brisé).
  - Architecture Spine (`lint_spine.py`) : `0 findings`.
  - Pas d'erreurs de typage statique (`mypy` 300 fichiers source : 0 erreur ; `tsc --noEmit` : 0 erreur).
  - Linters Python : `ruff check` et `ruff format --check` : 0 warning sur 720 fichiers.

### 3.3 Validation & Procédure de Test sur Toute la Pyramide (`AD-17` + 5 Garde-Fous de Câblage Vertical)
- **Couche 1a — Tests Unitaires Python** :
  - `tests/unit/test_story_17_2_pg_guard_and_reconcilers.py` :
    - `test_org_units_pg_schema_drift_raises_503_without_seeds_fallback` : valide le déclenchement de `HTTP 503 ERR_ORG_STORAGE_SCHEMA_OUTDATED` lors d'une dérive de schéma (`ProgrammingError`) sans jamais basculer silencieusement sur `seeds.py`.
    - `test_org_units_pg_connectivity_error_preserves_evaluator_fallback_in_test_mode` : valide le maintien du repli mémoire sur défaillance socket/réseau.
    - `test_reconcile_workspaces_on_load_merges_sql_workspaces_into_non_empty_jsonb` : valide la fusion sans doublon des espaces relationnels SQL même quand le snapshot JSONB contient déjà d'autres espaces.
    - `test_evaluator_org_unit_summaries_attaches_workspace_refs` : valide l'hydratation de `attached_workspaces: tuple[AttachedWorkspaceRef, ...]`.
- **Couche 1b — Tests Composants & Modales UI (Vitest)** :
  - `apps/web/src/__tests__/story-17-2-org-hierarchy-and-modals.test.tsx` :
    - Vérification du rendu nominatif de la liste `org-unit-delete-dependencies-list` détaillant chaque sous-unité et chaque espace rattaché.
    - Vérification que `confirm-delete-org-unit-btn-*` est désactivé (`disabled=true`) dès que `isNonEmpty` est vrai.
    - Vérification du bouton `org-unit-delete-open-workspaces-btn` redirigeant vers `/workspaces`.
    - Vérification de la gestion d'un conflit concurrent `HTTP 409` affichant `org-unit-delete-feedback`.
- **Couche 2 — Intégration Verticale PostgreSQL 18 (`testcontainers-python`)** :
  - `tests/integration/api/test_story_17_2_org_units_hierarchy_postgres18.py` :
    - Test réel contre conteneur PostgreSQL 18 : insertion relationnelle d'unités et d'espaces rattachés, requête HTTP `GET /api/v1/org-units`, validation que `attached_workspaces` contient les objets `{id, slug, name}` persistés en base sans requête SQL `N+1`.
- **Couche 3 — Contrat OpenAPI 3.1 & SDK Typescript** :
  - `.venv/bin/python scripts/export_openapi.py --check` validé (0-diff).
  - `packages/api-client/src/generated/auth_and_org.ts` synchronisé avec `AttachedWorkspaceRefResponse`.
- **Garde-fous de Câblage Vertical & Anti-Régression** :
  - Règle 1 à 4 validées par `tests/unit/test_codebase_architectural_anti_patterns_audit.py` (zéro appel bloquant dans l'event loop ASGI, zéro streaming factice, zéro couplage fournisseur en dur, zéro exception silencieuse dans les routeurs).
  - Zéro bouton muet validé par `apps/web/src/__tests__/zero-dead-buttons-and-silent-catches-audit.test.tsx`.
