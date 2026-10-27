---
title: 'Story 3.2a: Phase A — Socle du Monolithe Modulaire (packages/orcia-kernel), Workspace uv à 4 Packages, Rupture des 3 Cycles, Découplage schemas/ & <domaine>/errors.py, Point d''Assemblage Unique & Garde-Fou import-linter'
type: 'feature'
created: '2026-10-27'
status: 'done'
route: 'dispatch'
baseline_commit: '16703ba' # pragma: allowlist secret
review_loop_iteration: 1
context:
  - '{project-root}/AGENTS.md'
  - '{project-root}/docs/implementation-artifacts/epic-3-context.md'
  - '{project-root}/docs/planning-artifacts/sprint-change-proposal-2026-10-27.md'
---

<frozen-after-approval reason="human-owned intent — do not modify unless human renegotiates">

## Intent

**Problem:** Le dépôt Python regroupe aujourd'hui `packages/orcia-core`, `apps/api` et `apps/worker` dans un unique `pyproject.toml` sans vérification mécanique des frontières architecturales (`E4`). L'analyse GitNexus a identifié un point chaud `CRITICAL` sur `orcia_core/domain/exceptions.py` (59 dépendants directs), 3 cycles de dépendances entre domaines métier (`blackboard ↔ orchestration`, `catalog ↔ bootstrap`, `permissions ↔ bootstrap`), 10 fichiers de schémas HTTP (`orcia_core/schemas/`, `2 060` lignes) couplés au noyau métier, et 3 singletons d'import (`_DEFAULT_*_SERVICE`) dans les routeurs FastAPI (`E2`, `M1..M5`).

**Approach:** Extraire le package noyau `packages/orcia-kernel` (`orcia_kernel` : `ids.py`, `enums.py`, `errors.py`, `events.py`, `ports.py` incluant `OutboxRelayPort` et `BlackboardPort`), structurer le workspace `uv` à 4 packages (`packages/orcia-kernel`, `packages/orcia-core`, `apps/api`, `apps/worker`), rompre les 3 cycles inter-domaines (`catalog/seeds.py`, `permissions/seeds.py`, `orcia_kernel.enums`), déplacer les 10 fichiers de DTOs HTTP dans `apps/api/src/orcia_api/schemas/`, éclater les exceptions métier par domaine dans `<domaine>/errors.py` avec un registre HTTP RFC 9457 centralisé dans `apps/api/src/orcia_api/errors/registry.py`, isoler les stores `InMemory*` dans `tests/unit/fakes/`, supprimer les 3 singletons `_DEFAULT_*_SERVICE` au profit d'un point d'assemblage unique (`lifespan` + `apps/api/src/orcia_api/dependencies.py`), et verrouiller l'ensemble via `import-linter` (`lint-imports` à `0` violation).

## Boundaries & Constraints

**Always:**
- Garantir que `packages/orcia-kernel` (`orcia_kernel`) n'importe aucun domaine de `orcia_core` ni aucun framework (`fastapi`, `sqlalchemy`, `dramatiq`, `dbos`, `redis`, `litellm`).
- Éliminer les 3 cycles inter-domaines (`blackboard ↔ orchestration`, `catalog ↔ bootstrap`, `permissions ↔ bootstrap`).
- Déplacer les 10 fichiers de schémas HTTP vers `apps/api/src/orcia_api/schemas/` et définir les erreurs métier dans `packages/orcia-core/src/orcia_core/<domaine>/errors.py` héritant de `orcia_kernel.errors.OrciaDomainError`.
- Câbler tous les services dans le Composition Root (`lifespan` dans `apps/api/src/orcia_api/main.py` et `Depends(get_*_service)` dans `apps/api/src/orcia_api/dependencies.py`), sans singleton `_DEFAULT_*_SERVICE` instancié à l'import dans les routeurs.
- Isoler les implémentations `InMemory*` dans `tests/unit/fakes/`.
- Faire passer `.venv/bin/lint-imports` (`import-linter`) avec `0` contrat cassé.

**Never:**
- Ne jamais importer `orcia_api` ou `orcia_worker` depuis `orcia_core` ou `orcia_kernel`.
- Ne jamais laisser de cycle entre domaines pairs de `orcia_core`.
- Ne jamais casser les routes OpenAPI 3.1 ni les tests unitaires existants des Stories `1.1..3.2`.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Vérification `import-linter` (`lint-imports`) | Graphe d'imports complet (`orcia_kernel`, `orcia_core`, `orcia_api`, `orcia_worker`) | `0 broken contracts` sur les 4 contrats (`layers`, `domain_cycles`, `internal_encapsulation`, `forbidden_frameworks`) | Échec bloquant (`exit code != 0`) en cas d'import interdit |
| Résolution d'erreur RFC 9457 par domaine | Exception `<domaine>/errors.py` levée dans un service métier | `apps/api/src/orcia_api/errors/registry.py` et `trace_and_error.py` produisent l'enveloppe `application/problem+json` localisée (`fr`/`en`) avec `trace_id` | Fallback `500 ERR_INTERNAL_SERVER_ERROR` si erreur inconnue |
| Point d'assemblage FastAPI (`lifespan` + `Depends`) | Requête HTTP sur `/api/v1/auth/*`, `/api/v1/catalog/*`, `/api/v1/orchestration/*` | Services résolus depuis `request.app.state` via `orcia_api.dependencies.get_*_service` (`0` singleton `_DEFAULT_*_SERVICE` dans les routeurs) | Initialisation paresseuse sûre sur `app.state` si appelé hors lifespan |
| Primitives `orcia_kernel` (`ids`, `enums`, `events`, `ports`, `errors`) | Appel de `new_uuid7_str()`, `compute_bytes_sha256()`, création d'événements Outbox immuables (`StepCompleted`, etc.) | Génération UUIDv7 monotone, hachage SHA-256 déterministe, événements figés sérialisables | `OrciaDomainError` typée |

</frozen-after-approval>

## Code Map

- `packages/orcia-kernel/pyproject.toml` & `packages/orcia-kernel/src/orcia_kernel/{__init__,ids,enums,errors,events,ports}.py` -- Noyau partagé minimal (`0` dépendance métier).
- `packages/orcia-core/pyproject.toml`, `apps/api/pyproject.toml`, `apps/worker/pyproject.toml`, `pyproject.toml` -- Workspace `uv` à 4 packages et configuration `import-linter`.
- `packages/orcia-core/src/orcia_core/{permissions,catalog,bootstrap,ontology,rag,orchestration,blackboard}/errors.py` -- Exceptions métier par domaine héritant de `orcia_kernel.errors.OrciaDomainError`.
- `packages/orcia-core/src/orcia_core/catalog/seeds.py` & `packages/orcia-core/src/orcia_core/permissions/seeds.py` -- Extraction des seeds pour rompre les cycles `catalog ↔ bootstrap` et `permissions ↔ bootstrap`.
- `apps/api/src/orcia_api/schemas/` -- Les 10 modules de schémas HTTP/OpenAPI déplacés hors de `orcia_core`.
- `apps/api/src/orcia_api/errors/registry.py` & `apps/api/src/orcia_api/dependencies.py` -- Registre HTTP RFC 9457 et Composition Root FastAPI.
- `tests/unit/fakes/in_memory_stores.py` -- Stores `InMemoryCasObjectStore` et `InMemoryRevocationStore` isolés pour les tests unitaires.
- `tests/unit/test_story_3_2a_modular_monolith_kernel.py` -- Suite de tests unitaires dédiée à la Story 3.2a (`orcia_kernel`, rupture des cycles, `lint-imports`, Composition Root, registre RFC 9457).

## Tasks & Acceptance

**Execution:**
- [ ] `packages/orcia-kernel/` -- Créer le package `orcia-kernel` (`ids.py`, `enums.py`, `errors.py`, `events.py`, `ports.py` avec `BlackboardPort`, `OutboxRelayPort`, `LLMPort`, `ObjectStoragePort`, `SandboxPort`, `ClockPort`).
- [ ] `pyproject.toml`, `packages/orcia-core/pyproject.toml`, `apps/api/pyproject.toml`, `apps/worker/pyproject.toml` -- Configurer le workspace `uv` à 4 packages, aligner les versions minimales (`P3`) et déclarer les contrats `import-linter` (`P4`).
- [ ] `packages/orcia-core/src/orcia_core/{catalog,permissions}/seeds.py` & `blackboard/models.py` -- Rompre les 3 cycles inter-domaines (`M1`, `M2`).
- [ ] `packages/orcia-core/src/orcia_core/<domaine>/errors.py` & `apps/api/src/orcia_api/errors/registry.py` -- Éclater `domain/exceptions.py` par domaine et centraliser le registre HTTP RFC 9457 (`M4`).
- [ ] `apps/api/src/orcia_api/schemas/` -- Déplacer les 10 fichiers de schémas HTTP depuis `packages/orcia-core/src/orcia_core/schemas/` vers `apps/api/src/orcia_api/schemas/` (`M3`).
- [ ] `apps/api/src/orcia_api/dependencies.py`, `main.py` & `tests/unit/fakes/` -- Supprimer les 3 singletons `_DEFAULT_*_SERVICE` dans les routeurs, câbler `lifespan` + `Depends(get_*_service)`, et isoler `InMemory*` dans `tests/unit/fakes/` (`M5`).
- [ ] `tests/unit/test_story_3_2a_modular_monolith_kernel.py` -- Vérifier par tests automatisés `orcia_kernel`, l'absence de cycles, `lint-imports` (`0` violation), le registre d'erreurs et la couverture $\ge 90\%$.

**Acceptance Criteria:**
- Given le workspace `uv` à 4 packages (`orcia-kernel`, `orcia-core`, `orcia-api`, `orcia-worker`), when `lint-imports` s'exécute, then l'ordre des couches (`orcia_kernel <- orcia_core <- orcia_api/orcia_worker`), l'absence des 3 cycles inter-domaines, l'encapsulation de `_internal/` et l'absence de frameworks dans `orcia_kernel` passent avec `0` violation.
- Given les schémas HTTP déplacés dans `apps/api/src/orcia_api/schemas/` et les erreurs dans `<domaine>/errors.py`, when l'API FastAPI démarre via `lifespan` et `dependencies.py`, then aucun routeur n'instancie de singleton `_DEFAULT_*_SERVICE` à l'import et le contrat OpenAPI 3.1 reste à `0 diff`.

## Verification

**Commands:**
- `.venv/bin/lint-imports` -- expected: `0 broken contracts`
- `.venv/bin/ruff check . && .venv/bin/ruff format --check .` -- expected: `0 errors`
- `.venv/bin/mypy --strict packages/orcia-kernel packages/orcia-core apps/api apps/worker` -- expected: `Success: no issues found`
- `.venv/bin/pytest --cov=packages/orcia-kernel --cov=packages/orcia-core --cov-fail-under=90` -- expected: `passed, coverage >= 90%`
- `pnpm turbo run lint typecheck test` -- expected: `0 errors`
