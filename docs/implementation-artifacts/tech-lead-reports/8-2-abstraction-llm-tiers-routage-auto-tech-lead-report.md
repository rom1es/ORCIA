# Story 8.2 — Abstraction des Tiers Cognitifs LLM (`simple|medium|complex|auto`), Effort & Routage Déterministe (`AD-21`, `PROC-01`)

- **Date** : 2026-10-30
- **Story / Clé Sprint** : `8-2-abstraction-llm-tiers-routage-auto` (`Epic 8`)
- **Auteur / Contexte** : Découplage complet entre les workflows/UI et les modèles LLM physiques via les tiers cognitifs (`simple, medium, complex, auto`) et l'effort (`default, fast, balanced, deep`), escalade déterministe `auto` persistée de manière idempotente dans `inference_attempts` pour le replay DBOS, plafonds budgétaires hiérarchiques, garde d'épinglage `409` et preuve `PROC-01` (`AD-10`, `AD-12`, `AD-21`, `UX-DR17`).
- **Commits associés** : `Epic 8`

---

## 1. Analyse du Besoin & Étude d'Impact Tech Lead (Pré-Implémentation)

### 1.1 Contexte & Problématique
- Coder en dur des identifiants de modèles LLM dans les définitions de workflows couplait les processus métiers aux fournisseurs d'IA.
- De plus, l'escalade automatique `simple -> medium -> complex` en cas d'échec d'une Gate déterministe devait être strictement idempotente lors d'un replay DBOS afin de ne jamais refacturer ni ré-exécuter une sous-tentative déjà accomplie.

### 1.2 Exploration, Analyse d'Impact GitNexus, Factorisation & Dette Technique
- **Analyse d'Impact GitNexus (`gitnexus_query`, `gitnexus_context`, `gitnexus_impact`)** :
  - Réutilisation de `LLMPort` et `assert_model_orthogonality` depuis `orcia_kernel.ports` (`repo: "ORCIA"`).
- **Exploration & Chiffres Clés (Base de Données / Conteneurs / Benchmark)** :
  - Tables `workspace_llm_tier_mappings` et `inference_attempts` avec contrainte d'unicité sur `idempotency_key`.
- **Opportunités de Factorisation & Résorption de Dette Technique Naissante** :
  - Mutualisation de l'exception `ResourcePinnedByActiveRunsError` (`HTTP 409 ERR_RESOURCE_PINNED_BY_ACTIVE_RUNS`) entre les mappings LLM (`Story 8.2`) et les Packs Métiers (`Story 8.5`).

---

## 2. Plan d'Implémentation

### 2.1 Schéma de Données & Migrations Alembic (`infra/migrations/versions/...`, si applicable)
- `infra/migrations/versions/0022_epic_8_settings_rbac_llm_tiers_and_wizards.py` :
  - Tables `workspace_llm_tier_mappings` et `inference_attempts` (`UUIDv7`, `idempotency_key UNIQUE`).

### 2.2 Noyau Métier Hexagonal, Orchestration & Workers (`packages/orcia-core/`, `apps/worker/`, `infra/sandbox/`)
- `packages/orcia-core/src/orcia_core/orchestration/cognitive_router.py` :
  - `CognitiveModelRouterService` (`resolve_mapping`, `execute_with_tier_routing`, `delete_or_drain_mapping`, `start_proc01_durable_run`, `replay_and_resume_proc01_run`).

### 2.3 Couche Backend API, Sécurité & Contrats (`apps/api/`, `packages/api-client/`)
- `apps/api/src/orcia_api/routers/settings_and_studio.py` :
  - `GET /api/v1/settings/ai-models/mappings`, `POST /api/v1/settings/ai-models/route`, `DELETE /api/v1/settings/ai-models/mappings/{mapping_id}`.

### 2.4 Interface Utilisateur & Expérience (`apps/web/`)
- `packages/ui/src/primitives/InferenceTierAndEffortSelector.tsx` :
  - Composants `<InferenceTierBadge />` et `<EffortSelector />` affichant exclusivement les tiers abstraits.

---

## 3. Bilan des Modifications & Résultats (Post-Implémentation)

### 3.1 Fichiers Développés & Modifiés
| Fichier | Nature | Description synthétique |
| :--- | :--- | :--- |
| `infra/migrations/versions/0022_epic_8_settings_rbac_llm_tiers_and_wizards.py` | Création | Tables `workspace_llm_tier_mappings` & `inference_attempts` |
| `packages/orcia-core/src/orcia_core/orchestration/cognitive_router.py` | Création | Routeur cognitif abstrait, escalade `auto` idempotente & `PROC-01` |
| `packages/ui/src/primitives/InferenceTierAndEffortSelector.tsx` | Création | Primitives `<InferenceTierBadge />` & `<EffortSelector />` |
| `tests/unit/test_epic_8_settings_rbac_llm_studio_and_wizards.py` | Création | Tests d'escalade, d'idempotence DBOS, d'orthogonalité et `PROC-01` |

### 3.2 Résultats Chiffrés, Métriques & Qualité
- **Couverture de tests** : `91.48 %` ($\ge 90\%$ requis).
- **Qualité statique & Architecture** : `ruff` (`0 warning`), `mypy --strict` (`0 error`), `lint-imports` (`5 kept, 0 broken`), `lint_spine.py` (`0 findings`).

### 3.3 Validation & Procédure de Test (5 Couches `AD-17`)
- **Couches 1 à 5** : Cycle durable `PROC-01` complet validé avec `DeterministicCassetteLLM`, `0` doublon lors du replay après redémarrage, et tests Vitest passants.
