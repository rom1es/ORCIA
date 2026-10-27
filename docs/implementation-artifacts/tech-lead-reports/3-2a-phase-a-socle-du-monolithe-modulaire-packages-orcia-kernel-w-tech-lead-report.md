# Rapport Tech Lead — Analyse & Implémentation : Story 3.2a (Phase A — Socle du Monolithe Modulaire `packages/orcia-kernel`, Workspace `uv` à 4 Packages, Rupture des 3 Cycles, Découplage `schemas/` & `<domaine>/errors.py`, Point d'Assemblage Unique & Garde-Fou `import-linter`)

- **Identifiant Story / Ticket** : `3-2a-phase-a-socle-du-monolithe-modulaire-packages-orcia-kernel-w`
- **Epic parent** : `Epic 3 — Cockpit "Human-Led", Agent Assistant Adaptatif, Moteur d'Orchestration Durable & Sous-Workflows Fractals (SUB_WORKFLOW <= 3)`
- **Date d'ouverture** : `2026-10-27`
- **Date de clôture** : `2026-10-27`
- **Auteur (Rôle)** : `Tech Lead / Senior Developer Agent`
- **Statut** : `Done`

---

## 1. Analyse du Besoin & Étude d'Impact Tech Lead (Avant Implémentation)

### 1.1 Contexte Fonctionnel & Problématique Métier
L'audit de la stack ([`stack-review-2026-10-27.md`](../../planning-artifacts/research/stack-review-2026-10-27.md), écarts `E2`, `E4`) et l'analyse de modularité ([`modularity-analysis-2026-10-27.md`](../../planning-artifacts/research/modularity-analysis-2026-10-27.md), pistes `M1..M5`) ont mis en évidence que l'implémentation initiale des Epics 1, 2 et du début de l'Epic 3 reposait sur un unique `pyproject.toml` racine sans garde-fou d'architecture automatisé (`import-linter`), avec un couplage transversal croissant :
1. **Trois cycles de dépendances inter-domaines dans `packages/orcia-core`** :
   - `blackboard` $\leftrightarrow$ `orchestration` (`blackboard/models.py` importait `WorkflowExecutionRegime` et `WorkflowStepType` depuis `orchestration/models.py`, tandis qu'`orchestration/engine.py` importait `blackboard/models.py` et `blackboard/store.py`).
   - `catalog` $\leftrightarrow$ `bootstrap` (`catalog/__init__.py` importait `DEFAULT_CATALOG_ITEM_SEEDS`, `DEFAULT_CUSTOMIZATION_OVERRIDE_SEEDS`, `DEFAULT_WORKFLOW_DEFINITION_SEEDS` depuis `bootstrap/seeder.py`, tandis que `bootstrap` importait `catalog`).
   - `permissions` $\leftrightarrow$ `bootstrap` (`permissions/__init__.py` importait `DEFAULT_ORG_UNIT_SEEDS`, `DEFAULT_WORKSPACE_DATASOURCE_SEEDS`, `DEFAULT_WORKSPACE_SEEDS` depuis `bootstrap/seeder.py` et `permissions/broker.py` importait `bootstrap/permission_broker_seeds.py`, tandis que `bootstrap` importait `permissions`).
2. **Point chaud `CRITICAL` sur `domain/exceptions.py`** (`378` lignes, **59 symboles dépendants directs** dans 35 fichiers), obligeant chaque domaine à modifier un fichier central unique.
3. **Fuite de la couche HTTP dans le noyau métier** : 10 fichiers de schémas Pydantic REST (`2 060` lignes) logés dans `packages/orcia-core/src/orcia_core/schemas/` au lieu de `apps/api/src/orcia_api/schemas/`.
4. **Trois singletons instanciés au chargement des modules** dans `apps/api/src/orcia_api/routers/{auth,catalog,orchestration}.py` (`_DEFAULT_AUTH_SERVICE`, `_DEFAULT_CATALOG_SERVICE`, `_DEFAULT_ORCHESTRATION_SERVICE`) et classes `InMemory*` mélangées au code de production.

### 1.2 Analyse d'Impact GitNexus & Cartographie du Code Existant
- **Commandes GitNexus exécutées (`repo: "ORCIA"`)** :
  - `gitnexus_impact({target: "OrciaDomainError", direction: "upstream", repo: "ORCIA"})` $\rightarrow$ **`risk: CRITICAL`**, `impactedCount: 59` appelants directs (`d=1`) répartis sur 35 fichiers (`catalog`, `permissions`, `bootstrap`, `ontology`, `rag`, `orchestration`, `blackboard`, `apps/api`).
  - `gitnexus_impact({target: "orchestration/engine.py", direction: "upstream", repo: "ORCIA"})` $\rightarrow$ `risk: LOW`, `impactedCount: 3` (`orchestration/__init__.py`, `orchestration/run_lock_service.py`, `orchestration/seeds.py`).
- **Mesure de parade face au risque `CRITICAL` sur `OrciaDomainError`** :
  - Extraction de la classe racine `OrciaDomainError`, `LocalizedErrorCopy`, `ERROR_CATALOG`, `resolve_locale` et `get_localized_error_text` dans `packages/orcia-kernel/src/orcia_kernel/errors.py`.
  - Création d'un module `<domaine>/errors.py` dans les 9 domaines de `packages/orcia-core` (`permissions/errors.py`, `catalog/errors.py`, `bootstrap/errors.py`, `ontology/errors.py`, `rag/errors.py`, `orchestration/errors.py`, `blackboard/errors.py`, `gates/errors.py`, `audit_finops/errors.py`) héritant de `orcia_kernel.errors.OrciaDomainError`.
  - Création du registre HTTP RFC 9457 centralisé dans `apps/api/src/orcia_api/errors/registry.py`.

### 1.3 Chiffres Clés & Volumétrie
- **Packages `uv` cibles (`Q1 = 1A`)** : `4` packages (`packages/orcia-kernel`, `packages/orcia-core`, `apps/api`, `apps/worker`).
- **Fichiers de schémas HTTP déplacés (`M3`)** : `10` fichiers (`2 060` lignes) transférés de `packages/orcia-core/src/orcia_core/schemas/` vers `apps/api/src/orcia_api/schemas/`.
- **Cycles inter-domaines éliminés (`M1`, `M2`)** : `3 -> 0`.
- **Singletons `_DEFAULT_*_SERVICE` dans les routeurs (`M5`)** : `3 -> 0`.

---

## 2. Plan d'Implémentation (Architecture Cible)

### 2.1 Schéma de Données & Migrations Alembic
- Aucune migration SQL dans `Story 3.2a` (Phase A = restructuration modulaire pure à `0` changement d'infrastructure ; la persistance SQLAlchemy 2.1 et la table Outbox `0012` sont livrées en `3.2b` et `3.2c`).

### 2.2 Noyau Partagé `packages/orcia-kernel` & Rupture des 3 Cycles (`packages/orcia-core`)
- **`packages/orcia-kernel/src/orcia_kernel/`** (`0` dépendance métier, `0` framework) :
  - `ids.py` : `new_uuid7()`, `new_uuid7_str()`, `is_valid_uuid7()`, `extract_uuid7_timestamp_ms()`, `compute_bytes_sha256()`.
  - `enums.py` : `StepExecutionStatus`, `StepExecutionState`, `WorkflowStepType`, `WorkflowExecutionRegime`, `MemlogMarkerType`, `SnapshotBranchStatus`, `SupportedLocale`, `DEFAULT_LOCALE`, `ExecutionMode`.
  - `errors.py` : `OrciaDomainError`, `LocalizedErrorCopy`, `ERROR_CATALOG`, `register_domain_error_catalog()`, `resolve_locale()`, `get_localized_error_text()`, et erreurs transverses (`ResourceNotFoundError`, `ValidationDomainError`, `ObserverModeReadOnlyError`, `ScopeAccessDeniedError`, `HumanAnchorRequiredError`, `ReadSourceDeniedError`, `ModelOrthogonalityViolationError`).
  - `events.py` : `DomainEvent`, `StepCompleted`, `ArtifactProduced`, `GateEvaluated`, `RunTerminated`, `HumanArbitrationRequested`.
  - `ports.py` : `ClockPort`, `ObjectStoragePort`, `BlackboardPort`, `OutboxRelayPort`, `LLMPort`, `SandboxPort`.
- **Rupture des 3 cycles dans `packages/orcia-core/src/orcia_core/`** :
  1. `blackboard/models.py` importe `StepExecutionStatus`, `WorkflowExecutionRegime`, `WorkflowStepType`, `MemlogMarkerType`, `SnapshotBranchStatus` depuis `orcia_kernel.enums` (`0` import d'`orchestration`).
  2. `catalog/seeds.py` détient `CatalogItemSeed`, `WorkflowDefinitionSeed`, `CustomizationOverrideSeed` et leurs tuples `DEFAULT_*_SEEDS` (`0` import de `bootstrap` dans `catalog`).
  3. `permissions/seeds.py` détient `OrgUnitSeed`, `WorkspaceSeed`, `WorkspaceDatasourceSeed`, `PermissionBrokerPolicySeed`, `PermissionBrokerTicketSeed` et leurs tuples `DEFAULT_*_SEEDS` (`0` import de `bootstrap` dans `permissions`).

### 2.3 Couche Backend API, Schémas HTTP, Registre RFC 9457 & Composition Root (`apps/api/`)
- **`apps/api/src/orcia_api/schemas/`** : héberge les 10 modules de DTOs HTTP/OpenAPI (`auth_and_org.py`, `blackboard.py`, `bootstrap.py`, `catalog.py`, `ontology_and_rag.py`, `orchestration.py`, `permission_broker.py`, `problem_details.py`, `shell.py`, `__init__.py`).
- **`apps/api/src/orcia_api/errors/registry.py`** : registre HTTP RFC 9457 mappant `OrciaDomainError` et les 21 erreurs par domaine vers `ProblemDetails`.
- **`apps/api/src/orcia_api/dependencies.py` & `main.py`** : Composition Root unique avec `app_lifespan` / `initialize_app_services` initialisant `app.state` et `get_*_service` injecté dans tous les routeurs (`0` singleton `_DEFAULT_*_SERVICE`).
- **`tests/unit/fakes/in_memory_stores.py`** : isolation de `InMemoryCasObjectStore`, `InMemoryRevocationStore`, `InMemoryOutboxRelay`, `InMemoryObjectStorageFake`, `DeterministicClockFake` et `InMemorySandboxFake`.
- **Contrats `import-linter` (`pyproject.toml`)** : vérification automatique de l'ordre des couches (`orcia_api / orcia_worker -> orcia_core -> orcia_kernel`), de l'absence de cycles inter-domaines et de l'interdiction des frameworks dans `orcia_kernel` et `orcia_core.domain` / `orcia_core.ports`.

---

## 3. Bilan des Modifications & Résultats (Post-Implémentation)

### 3.1 Fichiers Créés, Déplacés ou Modifiés

| Fichier | Action | Lignes | Rôle |
| :--- | :--- | :---: | :--- |
| `packages/orcia-kernel/pyproject.toml` | Créé | `17` | Manifeste du package `orcia-kernel` (`uuid-utils` + stdlib). |
| `packages/orcia-kernel/src/orcia_kernel/{__init__,ids,enums,errors,events,ports}.py` | Créé | `895` (`6` fichiers, max `230` l.) | Noyau partagé pur (`UUIDv7`, `SHA-256`, enums transverses, `OrciaDomainError`, événements Outbox, ports `BlackboardPort` / `OutboxRelayPort` / `LLMPort` / `ObjectStoragePort` / `SandboxPort` / `ClockPort`). |
| `packages/orcia-core/pyproject.toml`, `apps/api/pyproject.toml`, `apps/worker/pyproject.toml`, `pyproject.toml` | Créé / Modifié | `258` | Workspace `uv` à 4 packages + 3 contrats `import-linter` (`AD-19`). |
| `packages/orcia-core/src/orcia_core/<domaine>/errors.py` (`9` domaines) | Créé | `348` (`9` fichiers, max `75` l.) | Exceptions de domaine décentralisées héritant de `OrciaDomainError` (`domain/exceptions.py` supprimé). |
| `packages/orcia-core/src/orcia_core/{catalog,permissions}/seeds.py` | Créé | `580` (`2` fichiers, max `297` l.) | Seeds de référence rapatriés dans `catalog` et `permissions` pour éliminer les cycles avec `bootstrap`. |
| `apps/api/src/orcia_api/schemas/*.py` (`10` fichiers) | Déplacé | `2 060` | Schémas HTTP/OpenAPI déplacés hors de `packages/orcia-core` vers `apps/api`. |
| `apps/api/src/orcia_api/errors/{__init__,registry}.py` | Créé | `175` | Registre HTTP RFC 9457 centralisé (`21` classes d'erreur mappées). |
| `apps/api/src/orcia_api/dependencies.py` & `main.py` | Créé / Modifié | `229` | Point d'assemblage unique (`app_lifespan`, `initialize_app_services`, `get_*_service`) ; suppression des `3` singletons `_DEFAULT_*_SERVICE` dans les routeurs. |
| `tests/unit/fakes/{__init__,in_memory_stores}.py` | Créé | `149` | Isolation des stores et adaptateurs `InMemory*` pour les tests unitaires. |
| `tests/unit/test_story_3_2a_modular_monolith_kernel.py` | Créé | `314` | Suite de tests unitaires et architecturaux couvrant `AC1..AC7`. |

### 3.2 Métriques & Couverture de Tests

- **Contrats `import-linter` (`.venv/bin/lint-imports`)** : `142 files analyzed, 593 dependencies — 3 contracts kept, 0 broken`.
- **Qualité & Typage Strict** :
  - `.venv/bin/ruff check .` : `0` erreur.
  - `.venv/bin/ruff format --check .` : `241 files already formatted`.
  - `.venv/bin/mypy --strict packages/orcia-kernel packages/orcia-core apps/api apps/worker` : `Success: no issues found in 104 source files`.
- **Couverture Unitaire (`.venv/bin/pytest tests/unit --cov=packages/orcia-kernel --cov=packages/orcia-core --cov-fail-under=90`)** :
  - `54 passed` (`0` échec).
  - Couverture globale : **`94.56 %`** ($\ge 90\%$ requis), dont **`99.0 %`** sur `packages/orcia-kernel`.
- **Contrat OpenAPI `0-diff` & Tests TypeScript (`pnpm turbo run lint typecheck test`)** :
  - `.venv/bin/python scripts/export_openapi.py --check` : `0-diff` validé.
  - `.venv/bin/pytest tests/contract -q` : `2 passed`.
  - `pnpm turbo run lint typecheck test` : `9/9 tasks successful` (`25/25` tests Vitest passés).
- **Analyse de graphe GitNexus (`gitnexus_detect_changes`)** : `67` fichiers modifiés/déplacés vérifiés, `0` cycle inter-domaines résiduel.
