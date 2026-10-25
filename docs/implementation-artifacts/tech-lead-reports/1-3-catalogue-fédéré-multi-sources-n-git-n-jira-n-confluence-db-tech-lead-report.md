# Rapport d'Analyse & d'Implémentation Tech Lead — Story 1.3 : Catalogue Fédéré Multi-Sources (`N × git://`, `N × jira://`, `N × confluence://`, `db://`, `nexus://`), Cache CAS `SHA-256`, Surcharges à 4 Niveaux (`Base → Team → Workspace → User`) & Adaptateur BMAD

- **Clé de la Story** : `1-3-catalogue-fédéré-multi-sources-n-git-n-jira-n-confluence-db`
- **Epic parent** : `Epic 1 — Amorçage Gouverné de l'Organisation, Onboarding Autonome d'Équipe (TEAM_LEAD), Catalogue Fédéré & Permission Broker connecté à Jira`
- **Date** : `2026-10-25`
- **Auteur** : `Tech Lead Agent (Antigravity)`
- **Statut** : `done`
- **Commits associés** : `Enregistré en fin de Story 1.3`

---

## 1. Analyse du Besoin & Étude d'Impact Tech Lead (Pré-Implémentation)

### 1.1. Contexte & Problématique Métier / Technique
La **Story 1.3** (`FR-20`, `FR-21`, `AD-5`, `AD-14`, `AR-5`, `UX-DR8`, `NFR-PERF-3`) construit le moteur du **Catalogue Fédéré Multi-Sources** d'ORCIA :
1. **Enregistrement et cycle de publication hiérarchique (`FR-21`)** : Les ressources (`workflow`, `agent`, `skill`, `template`, `datasource`) sont référencées par leur URI canonique (`db://`, `git://`, `nexus://`, `confluence://<space>/<page>@v<N>`, `jira://<project>/<issue>`, `orcia://`) et promues à travers le cycle `DRAFT -> SHARED_WORKSPACE -> SHARED_TEAM -> SHARED_BU -> PENDING_APPROVAL -> PUBLISHED_ORG`.
2. **Résolution à la volée vers le Cache Immuable CAS `SHA-256` (`AD-5`, `NFR-PERF-3`)** : Le `FederatedUriResolver` télécharge ou extrait la ressource à la première demande, vérifie/calcule son empreinte `SHA-256`, la persiste de manière immuable sous la clé `cas/<sha256>` (en mémoire + adaptateur compatible MinIO/S3 via `ObjectStoragePortProtocol`), et sert tout appel ultérieur sur cache chaud en `< 50 ms`.
3. **Fusion Déclarative Déterministe à 4 Niveaux & Épinglage `run-lock.json` (`AD-5`, `AD-14`)** : Le `FourLayerOverrideMerger` fusionne sans muter la ressource de base les 4 couches (`1. Base -> 2. Team [Arbre Équipe Parente -> Sous-Équipe] -> 3. Workspace [Solution Multi-Sources] -> 4. User`) : écrasement des scalaires, concaténation dédupliquée des listes (`datasources`, `rules`, `facts`), et fusion par clé `code` des lentilles d'évaluation (`lenses`), puis génère le manifeste immuable `run-lock.json` contenant le vecteur complet des triplets `(alias, uri, resolved_version, sha256)` de toutes les sources du Workspace.
4. **Adaptateur Natif de Packs de Skills BMAD (`BmadSkillPackAdapter`, `AR-5`, `AD-14`)** : Importe et convertit sans perte un répertoire ou descripteur de skill BMAD (`SKILL.md` + `customize.toml` + `steps/*.md`) référencé via `git://` ou `nexus://` en une `WorkflowDefinitionEntity` exécutable ORCIA.
5. **Interface Utilisateur Direction C (`UX-DR8`)** : Composant pur `FederatedUriBadge` (`uri-badge`, police `JetBrains Mono 12px`, `rounded-sm`, distinguant visuellement `git://` en ambre, `nexus://` en bleu cobalt, `db://` en vert émeraude, `confluence://`, `jira://`, `orcia://`, les permissions effectives `DISCOVER`/`EXECUTE`/`🔒 Source masquée` et le `SHA-256` tronqué) et vue du module **📦 3. Catalogue Fédéré** (`CatalogExplorerPanel`) dans `@orcia/ui` et `apps/web` (`i18n` `fr`/`en`).

### 1.2. Analyse d'Impact GitNexus (`repo: "ORCIA"`)
- **Symboles analysés via `gitnexus_query` et `gitnexus_impact`** :
  - [`MatrixPermissionEvaluator`](file:///home/romain/Documents/Projects/ORCIA/packages/orcia-core/src/orcia_core/permissions/evaluator.py#L34-L283) (`evaluate_catalog_resource`) : Réutilisé directement pour calculer les 5 permissions dissociées (`DISCOVER`, `EXECUTE`, `READ_SOURCE`, `EDIT`, `ADMIN`) et l'état boîte noire (`source_masked`) sur chaque entrée du catalogue.
  - [`resolve_request_user`](file:///home/romain/Documents/Projects/ORCIA/apps/api/src/orcia_api/routers/auth.py#L52-L60) : Réutilisé dans le routeur `/api/v1/catalog/*` et `/api/v1/cas/*` pour identifier l'appelant et appliquer `ScopeAccessGuard` sur toute publication/promotion ou enregistrement de surcharge (`HTTP 403 ERR_OBSERVER_MODE_READ_ONLY`).
  - [`packages/orcia-core/src/orcia_core/catalog/__init__.py`](file:///home/romain/Documents/Projects/ORCIA/packages/orcia-core/src/orcia_core/catalog/__init__.py) : Contexte borné 3 actuellement réduit à `DOMAIN_NAME = "catalog"`, prêt à accueillir `models.py`, `cas_resolver.py`, `override_merger.py`, `bmad_adapter.py` et `service.py`.

### 1.3. Exploration de la Base de Données & Chiffres Clés
- **Révision Alembic existante** : `0002_story_1_2` (`org_units`, `users`, `transverse_groups`, `workspaces`, `workspace_datasources`, `workspace_memberships`, `workspace_invitations`, `user_passthrough_credentials`, `catalog_acl_entries`).
- **Nouvelle révision `0003_story_1_3_federated_catalog_overrides_and_run_lock.py`** :
  1. `catalog_items` (PK `UUIDv7`, `resource_id UNIQUE`, `uri`, `resource_type`, `source_format ('ORCIA'|'BMAD_PACK')`, `version`, `sha256`, `cas_key`, `visibility_scope`, `owner_org_unit_id`, `owner_workspace_id`).
  2. `workflow_definitions` (PK `UUIDv7`, `workspace_id`, `uri`, `version`, `source_format ('ORCIA'|'BMAD_PACK')`, `steps_schema_jsonb`, `adaptive_gate_policy`, `sha256`).
  3. `workspace_customization_overrides` (PK `UUIDv7`, `org_unit_id`, `workspace_id`, `user_id`, `target_uri`, `override_layer ('TEAM'|'WORKSPACE'|'USER')`, `override_manifest_jsonb`, `sha256`).

### 1.4. Opportunités de Factorisation & Contrôle de Volumétrie (`< 300` lignes)
- Découpage modulaire de `packages/orcia-core/src/orcia_core/catalog/` en 5 fichiers spécialisés (`<= 290` lignes chacun) :
  - `models.py` (`233` lignes) : Entités immuables (`ParsedFederatedUri`, `CatalogItemEntity`, `WorkflowDefinitionEntity`, `CustomizationOverrideEntity`, `RunLockSourceTriplet`, `RunLockManifest`, `BmadSkillPackDescriptor`).
  - `cas_resolver.py` (`<= 290` lignes) : Parseur d'URI fédérées (`db://`, `git://`, `nexus://`, `confluence://`, `jira://`, `orcia://`), port `CasObjectStoreProtocol` (adaptateur mémoire + adaptateur compatible MinIO/S3) et `FederatedUriResolver` (`cas/<sha256>`, latence `< 50 ms`).
  - `override_merger.py` (`286` lignes) : `FourLayerOverrideMerger` (`Base -> Team [Parent -> Sub-Team] -> Workspace -> User`) et générateur déterministe de `RunLockManifest` (`run-lock.json`).
  - `bmad_adapter.py` (`286` lignes) : `BmadSkillPackAdapter` convertissant un pack BMAD (`SKILL.md` YAML frontmatter + `customize.toml` + `steps/*.md`) en `WorkflowDefinitionEntity` sans perte.
  - `service.py` (`287` lignes) : `FederatedCatalogService` orchestrant le cycle de promotion (`DRAFT -> ... -> PUBLISHED_ORG`), la résolution CAS, la fusion 4 niveaux et l'import BMAD.
- **Découpage préventif d'`apps/web/src/components/ModuleWorkspaceView.tsx`** : Ce fichier atteignant `239` lignes en Story 1.2, les données et cartes de démonstration du Catalogue Fédéré (`FederatedUriBadge` + `CatalogExplorerPanel`) sont isolées dans `@orcia/ui` (`packages/ui/src/shell/FederatedUriBadge.tsx` et `CatalogExplorerPanel.tsx`) et `apps/web/src/components/workspaceFixtures.ts`.

### 1.5. Décisions de Dette Technique & Tickets Créés
- **Étape 0 (Pre-Story Refactoring)** : Extraction dans `packages/orcia-core/src/orcia_core/bootstrap/seeder.py` des semences de workflows et de surcharges 4 niveaux (`DEFAULT_CATALOG_ITEM_SEEDS`, `DEFAULT_OVERRIDE_SEEDS`) réutilisées par le script de maintenance `infra/scripts/maintenance/02_backfill_federated_catalog.py`.
- Aucun ticket de dette technique externe n'est requis.

---

## 2. Plan d'Implémentation

### 2.1. Base de Données, Migrations Alembic & Scripts de Maintenance (`AD-16`)
- Créer [0003_story_1_3_federated_catalog_overrides_and_run_lock.py](file:///home/romain/Documents/Projects/ORCIA/infra/migrations/versions/0003_story_1_3_federated_catalog_overrides_and_run_lock.py) (`down_revision = "0002_story_1_2"`) en SQL brut avec `upgrade()` et `downgrade()`.
- Enrichir [seeder.py](file:///home/romain/Documents/Projects/ORCIA/packages/orcia-core/src/orcia_core/bootstrap/seeder.py) et créer [02_backfill_federated_catalog.py](file:///home/romain/Documents/Projects/ORCIA/infra/scripts/maintenance/02_backfill_federated_catalog.py) (`--dry-run` par défaut, `--apply`).

### 2.2. Noyau Domaine Hexagonal (`packages/orcia-core/catalog`)
- Implémenter `models.py`, `cas_resolver.py`, `override_merger.py`, `bmad_adapter.py`, `service.py` et `__init__.py` avec `0` import externe interdit (`fastapi`, `sqlalchemy`, `dramatiq`, `redis`, `litellm`).

### 2.3. API FastAPI (`apps/api`) & Contrat OpenAPI (`packages/api-client`)
- Créer [catalog.py](file:///home/romain/Documents/Projects/ORCIA/packages/orcia-core/src/orcia_core/schemas/catalog.py) et [catalog.py](file:///home/romain/Documents/Projects/ORCIA/apps/api/src/orcia_api/routers/catalog.py) exposant :
  - `GET /api/v1/catalog/items` (liste filtrée par RBAC avec `uri`, `scheme`, `sha256_short`, `visibility_scope`, `granted_permissions`, `source_masked`).
  - `POST /api/v1/catalog/items/{resource_id}/promote` (promotion le long de `DRAFT -> SHARED_WORKSPACE -> SHARED_TEAM -> SHARED_BU -> PENDING_APPROVAL -> PUBLISHED_ORG`, protégée par `ScopeAccessGuard`).
  - `POST /api/v1/catalog/resolve` & `GET /api/v1/cas/{sha256}` (résolution à la volée vers `cas/<sha256>` en `< 50 ms` sur cache chaud).
  - `POST /api/v1/catalog/workflows/resolve-effective` (fusion 4 niveaux `Base -> Team -> Workspace -> User` + génération de `run-lock.json` avec les triplets `(alias, uri, resolved_version, sha256)`).
  - `POST /api/v1/catalog/bmad-packs/import` (conversion sans perte via `BmadSkillPackAdapter`, protégée contre `READ_ONLY_OBSERVER`).
- Régénérer `packages/api-client` en `0-diff` et exposer les méthodes typées dans `packages/api-client/src/index.ts`.

### 2.4. Interface Utilisateur Next.js 16 & Design System `@orcia/ui` (Direction C & `i18n` `fr`/`en`)
- Créer dans `packages/ui/src/shell/` le composant `FederatedUriBadge.tsx` (`data-testid="uri-badge"`, `UX-DR8`) et `CatalogExplorerPanel.tsx`, et les intégrer dans `apps/web` avec parité `i18n` `fr`/`en`.

---

## 3. Bilan des Modifications & Résultats (Post-Implémentation)

### 3.1. Fichiers Développés & Modifiés
| Fichier | Nature | Description synthétique |
| :--- | :--- | :--- |
| `infra/migrations/versions/0003_story_1_3_federated_catalog_overrides_and_run_lock.py` | Création | Révision Alembic `0003` (`down_revision = "0002_story_1_2"`) créant `catalog_items`, `workflow_definitions` et `workspace_customization_overrides` à clés `UUIDv7` avec tests `upgrade -> downgrade -> upgrade`. |
| `packages/orcia-core/src/orcia_core/bootstrap/{catalog_seeds.py,seeder.py}` | Création / Modification | Semences idempotentes (`DEFAULT_CATALOG_ITEM_SEEDS`, `DEFAULT_WORKFLOW_DEFINITION_SEEDS`, `DEFAULT_CUSTOMIZATION_OVERRIDE_SEEDS`) et générateurs SQL `INSERT ... ON CONFLICT DO UPDATE`. |
| `infra/scripts/maintenance/02_backfill_federated_catalog.py` | Création | Script de maintenance idempotent (`--dry-run` par défaut avec `ROLLBACK`, `--apply` avec `COMMIT` par lot) peuplant le catalogue fédéré, les workflows et les surcharges 4 niveaux (incluant la FK `user_id`). |
| `packages/orcia-core/src/orcia_core/catalog/{models.py,cas_resolver.py,override_merger.py,bmad_adapter.py,service.py,__init__.py}` | Création / Modification | Cœur hexagonal pur (`0` import externe interdit, chaque module `<= 290` lignes) : `parse_federated_uri`, `FederatedUriResolver` (`cas/<sha256>`, `< 50 ms`, `InMemoryCasObjectStore` + `S3CompatibleCasObjectStore`), `FourLayerOverrideMerger` (`Base -> Team -> Workspace -> User` + `run-lock.json`), `BmadSkillPackAdapter` (`SKILL.md` + `customize.toml` + `steps/*.md` + `.tar.gz`/`.zip`) et `FederatedCatalogService`. |
| `packages/orcia-core/src/orcia_core/permissions/evaluator.py` | Modification | Ajout de `upsert_catalog_acl`, `get_primary_catalog_acl` et prise en charge de la gouvernance `PENDING_APPROVAL` / découverte `PLATFORM_ADMIN` et `BU_DIRECTOR`. |
| `packages/orcia-core/src/orcia_core/schemas/{catalog.py,__init__.py}` | Création / Modification | Schémas Pydantic v2 stricts (`extra="forbid"`) avec contraintes regex OpenAPI 3.1 pour le Catalogue Fédéré, le CAS, la fusion 4 niveaux (`run-lock.json`) et l'import BMAD. |
| `apps/api/src/orcia_api/routers/catalog.py` & `apps/api/src/orcia_api/main.py` | Création / Modification | Routeur FastAPI (`290` lignes) `/api/v1/catalog/items`, `/api/v1/catalog/items/{resource_id}/promote`, `/api/v1/catalog/resolve`, `/api/v1/cas/{sha256}`, `/api/v1/catalog/workflows/resolve-effective`, `/api/v1/catalog/bmad-packs/import` protégé par `ScopeAccessGuard`. |
| `packages/api-client/{openapi.json,src/generated/schema.ts,src/index.ts,src/__tests__/client.test.ts}` | Modification | Régénération `0-diff` du schéma OpenAPI 3.1 et ajout des méthodes typées `listCatalogItems`, `promoteCatalogItem`, `resolveCatalogUri`, `getCasObject`, `resolveEffectiveWorkflow`, `importBmadSkillPack`. |
| `packages/ui/src/shell/{FederatedUriBadge.tsx,CatalogExplorerPanel.tsx,types.ts}`, `packages/ui/src/index.ts` & `packages/ui/src/__tests__/shell.test.tsx` | Création / Modification | Composants Direction C `FederatedUriBadge` (`data-testid="uri-badge"`, `UX-DR8`, monospace `JetBrains Mono 12px`, schémas colorés `git://` ambre, `nexus://` bleu cobalt, `db://` émeraude) et `CatalogExplorerPanel` isolés dans `@orcia/ui`. |
| `apps/web/src/{i18n/types.ts,i18n/locales/fr.ts,i18n/locales/en.ts,components/workspaceFixtures.ts,components/ModuleWorkspaceView.tsx,__tests__/i18n-and-shell.test.tsx}` & `apps/web/e2e/shell.spec.ts` | Création / Modification | Intégration du module **📦 3. Catalogue Fédéré** dans `apps/web` avec parité `100 %` du dictionnaire `i18n` (`fr`/`en`) et extraction de `workspaceFixtures.ts`. |
| `tests/unit/test_federated_catalog.py` & `tests/integration/test_real_containers.py` | Création / Modification | Tests unitaires et basés sur les propriétés (`hypothesis`) + tests d'intégration `testcontainers` (migration `0003` sur PostgreSQL 18 et écriture/lecture réelle `cas/<sha256>` dans MinIO). |

### 3.2. Résultats Chiffrés, Métriques & Qualité
- **Couverture de tests Python (`pytest --cov=packages/orcia-core --cov-fail-under=90`)** : **`>= 97 %`** global sur `packages/orcia-core` (`25 passed`), dont `100 %` sur `catalog/models.py`, `100 %` sur `catalog/override_merger.py`, `100 %` sur `catalog/__init__.py`, `>= 97 %` sur `catalog/bmad_adapter.py`, `>= 95 %` sur `catalog/cas_resolver.py`, `100 %` sur `bootstrap/catalog_seeds.py` et `100 %` sur `bootstrap/seeder.py`.
- **Couverture & tests TypeScript (`pnpm turbo run lint typecheck test`)** : **`9/9` tâches Turborepo réussies** (`@orcia/api-client` 5 tests, `@orcia/ui` 7 tests, `@orcia/web` 4 tests).
- **Performances mesurées (`NFR-PERF-3`)** : Résolution sur cache chaud `cas/<sha256>` mesurée à **`< 1 ms`** (exigence `< 50 ms`).
- **Qualité statique & Architecture** :
  - `.venv/bin/ruff check .` & `.venv/bin/ruff format --check .` : `0 erreur, 127 fichiers formatés`
  - `.venv/bin/mypy --strict packages/orcia-core apps/api apps/worker` : `Success: no issues found in 48 source files`
  - `.venv/bin/python .agent/skills/bmad-architecture/scripts/lint_spine.py` : `{"ok": true, "total_findings": 0}`
  - `npx gitnexus analyze` & `gitnexus_detect_changes()` : `2,449 nodes | 3,676 edges | 44 clusters | 143 flows`, `changed_files: 21`, `changed_count: 102`, `partial: false`.

### 3.3. Validation & Procédure de Test (5 Couches `AD-17`)
- **Couche 1 — Tests Unitaires & Propriétés (`pytest` + `hypothesis`, `Vitest`)** : Validation du parseur d'URI (`git://`, `nexus://`, `db://`, `confluence://`, `jira://`, `orcia://`), du cache `cas/<sha256>` (`< 50 ms`), de l'ordre déterministe de fusion à 4 niveaux (`1. Base -> 2. Team [Parent -> Sub-Team] -> 3. Workspace -> 4. User`) via `hypothesis`, de l'absence de mutation de la ressource de base, de l'adaptateur `BmadSkillPackAdapter` (`SKILL.md` + `customize.toml` + `steps/*.md` + `.tar.gz`/`.zip`) et des composants `@orcia/ui` (`FederatedUriBadge`, `CatalogExplorerPanel`).
- **Couche 2 — Tests d'Intégration (`testcontainers-python` : PostgreSQL 18 + `pgvector`, Redis 7.4, MinIO)** : Vérification du cycle complet `alembic upgrade head -> downgrade 0002_story_1_2 -> downgrade base -> upgrade head`, de l'idempotence de `02_backfill_federated_catalog.py` (`--dry-run` rollback puis `--apply` commit de 6 items catalogue, 1 workflow et 4 surcharges), et de l'écriture/lecture réelle d'un objet `cas/<sha256>` dans le conteneur éphémère MinIO.
- **Couche 3 — Tests de Contrat API (`openapi-typescript` 0-diff + `Schemathesis`)** : `test_openapi_client_zero_diff_gate` (`0 diff`) et fuzzing ASGI `Schemathesis` (`test_schemathesis_openapi_contract_compliance`) validant toutes les opérations OpenAPI 3.1 et les enveloppes RFC 9457 (`application/problem+json` + `trace_id`).
- **Couche 4 — Tests d'Orchestration IA (`DeterministicCassetteLLM`)** : Validation déterministe sans appel LLM externe (`0 $`).
- **Couche 5 — Tests E2E & Accessibilité (`@playwright/test` Desktop `1600x1000` & Mobile `390x844`)** : `2 passed (6.3s)` validant la navigation vers **📦 3. Catalogue Fédéré**, l'affichage des 6 badges `uri-badge` (`UX-DR8`), le filtrage par source `BMAD_PACK`, la résolution CAS `< 50 ms`, la fusion 4 niveaux + `run-lock.json`, le basculement `FR`/`EN` et `0` violation WCAG 2.1 AA (`@axe-core/playwright`).
