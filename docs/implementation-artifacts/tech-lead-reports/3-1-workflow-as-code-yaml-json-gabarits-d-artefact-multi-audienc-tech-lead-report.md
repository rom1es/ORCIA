# Story 3.1 — Workflow-as-Code YAML/JSON (`SUB_WORKFLOW <= 3` & Criticité), Gabarits d'Artefact Multi-Audience, Discipline `Intention -> Code` & Épinglage Récursif `run-lock.json`

- **Date** : 2026-10-27
- **Story / Clé Sprint** : `3-1-workflow-as-code-yaml-json-gabarits-d-artefact-multi-audienc` (`Epic 3`)
- **Auteur / Contexte** : Validation déterministe de manifestes *Workflow-as-Code* YAML/JSON avec numéros de lignes exacts (`FR-11`), classification de criticité et régimes d'exécution (`FR-29`, `AD-18`), imbrication fractale de sous-workflows sans cycle jusqu'à `nesting_depth <= 3` (`FR-30`, `AD-18`), discipline `Intention -> Code` vs `mode: brownfield_bootstrap` (`FR-13`), compilateur dual de Gabarits d'Artefact Multi-Audience (`FR-12`) et épinglage cryptographique récursif `run-lock.json` (`FR-15`, `AD-5`, `AD-14`).
- **Commits associés** : `En cours (Story 3.1)`

---

## 1. Analyse du Besoin & Étude d'Impact Tech Lead (Pré-Implémentation)

### 1.1 Contexte & Problématique
- Dans ORCIA, les processus d'ingénierie et métiers combinent désormais des étapes interactives (`INTERACTIVE_COACHING`), des exécutions en tâche de fond (`BACKGROUND_FAST_PATH`) et des exécutions autonomes sous contrat (`AUTONOMOUS_CONTRACT`), ainsi que des étapes composites `SUB_WORKFLOW` invocables jusqu'à une profondeur maximale de `3` (`AD-18`, `FR-29`, `FR-30`).
- Sans validation statique rigoureuse au moment de l'enregistrement d'un manifeste YAML/JSON :
  1. Un workflow critique (`HIGH_CRITICAL`) pourrait être configuré par erreur en autonomie complète sans Gate humaine (`ERR_CRITICAL_WORKFLOW_REQUIRES_HUMAN_GATE`).
  2. Un workflow d'ingénierie logicielle pourrait modifier du code sans étape préalable de déclaration d'intention validée (`ERR_INTENTION_BEFORE_CODE_REQUIRED`) ou effectuer de la rétro-documentation sauvage sans déclarer `mode: brownfield_bootstrap`.
  3. Des sous-workflows imbriqués pourraient former un cycle (`A -> B -> A`) ou dépasser la profondeur maximale de `3` (`ERR_SUB_WORKFLOW_CYCLE_DETECTED`, `ERR_SUB_WORKFLOW_MAX_DEPTH_EXCEEDED`).
- De plus, l'instanciation d'un `Workflow Run` doit figer de manière immuable dans `run_lock_manifests` (`run-lock.json`) non seulement les sources (`git://`, `confluence://`, `jira://`, `db://`, `nexus://`) et les 4 couches de surcharges (`Base -> Team -> Workspace -> User`), mais aussi le `kb_snapshot_hash` et l'arbre récursif des sous-workflows (`sub_workflow_locks`).

### 1.2 Exploration, Analyse d'Impact GitNexus, Factorisation & Dette Technique
- **Analyse d'Impact GitNexus (`gitnexus_query`, `gitnexus_context`, `gitnexus_impact`)** :
  - `FourLayerOverrideMerger` (`packages/orcia-core/src/orcia_core/catalog/override_merger.py`) : `risk: LOW`, `5` appelants (`catalog/service.py`, `catalog/bmad_adapter.py`, `bootstrap/engine.py`).
  - `RunLockManifest` & `WorkflowDefinitionEntity` (`packages/orcia-core/src/orcia_core/catalog/models.py`) : `risk: MEDIUM`, `11` fichiers dépendants. Pour préserver à 100 % la compatibilité ascendante des tests Epic 1 et Epic 2, les nouveaux champs de `RunLockManifest` (`kb_snapshot_hash`, `sub_workflow_locks`) et de `WorkflowDefinitionEntity` (`criticality`, `execution_regime`, `tie_break_policy`, `workflow_mode`) utilisent des valeurs par défaut rétro-compatibles.
  - `OntologyHierarchyResolver` (`packages/orcia-core/src/orcia_core/ontology/resolver.py`) : `risk: LOW`, réutilisé directement par le compilateur de Gabarits d'Artefact Multi-Audience pour typer le JSON Schema formel à partir des concepts résolus des 4 niveaux d'Ontologie (`AD-7`, `FR-12`).
- **Exploration & Chiffres Clés (Base de Données / Conteneurs / Benchmark)** :
  - Les révisions Alembic `0001` à `0009` sont en place. La table `workflow_definitions` a été créée en `0003_story_1_3` : la révision `0010_story_3_1` l'enrichit (`ALTER TABLE workflow_definitions ADD COLUMN ...`) avec `criticality`, `execution_regime`, `tie_break_policy` et `workflow_mode`, et crée les 3 nouvelles tables `workflow_triggers`, `workflow_runs` (avec contraintes `CHECK (nesting_depth >= 0 AND nesting_depth <= 3)` et `UNIQUE (trigger_id, trigger_idempotency_key)`) et `run_lock_manifests`.
- **Opportunités de Factorisation & Résorption de Dette Technique Naissante** :
  - Réutilisation de `FourLayerOverrideMerger`, `FederatedUriResolver` (`cas/<sha256>`) et `OntologyHierarchyResolver` sans aucune duplication.
  - Découpage modulaire strict de `packages/orcia-core/src/orcia_core/orchestration/` en 4 fichiers spécialisés (`< 300 lignes` chacun) : `models.py`, `yaml_validator.py`, `template_compiler.py`, `run_lock_service.py`.
  - Extraction du composant UI `WorkflowStudioSection.tsx` dans `@orcia/ui` afin de maintenir `CatalogExplorerPanel.tsx` sous la barre des 350 lignes.

---

## 2. Plan d'Implémentation

### 2.1 Schéma de Données & Migrations Alembic (`infra/migrations/versions/...`, si applicable)
- `infra/migrations/versions/0010_story_3_1_workflow_runs_triggers_and_run_lock.py` :
  - Extension de `workflow_definitions` : ajout des colonnes `criticality` (`LOW_NON_CRITICAL | STANDARD | HIGH_CRITICAL`), `execution_regime` (`INTERACTIVE_COACHING | BACKGROUND_FAST_PATH | AUTONOMOUS_CONTRACT`), `tie_break_policy` (`ONTOLOGY_AXIOM_FIRST | DEFER_AND_CONTINUE_WITH_ASSUMPTION | PAUSE_AND_ESCALATE`) et `workflow_mode` (`standard | brownfield_bootstrap`).
  - Création de `workflow_triggers` (`UUIDv7` PK, `trigger_type`, `cron_expr`, `webhook_secret_vault_ref`, `event_filter_jsonb`, `cooldown_window_seconds`, `service_principal_id`, `max_runs_per_hour`, `max_daily_cost_usd`, `max_consecutive_failures`, `post_hoc_sampling_rate`, `contract_signature_id`, `status`).
  - Création de `workflow_runs` (`UUIDv7` PK, `parent_run_id`, `parent_step_execution_id`, `root_run_id`, `nesting_depth CHECK (nesting_depth >= 0 AND nesting_depth <= 3)`, `execution_regime`, `criticality`, `trigger_id`, `trigger_idempotency_key`, `UNIQUE (trigger_id, trigger_idempotency_key)`).
  - Création de `run_lock_manifests` (`run_id` PK/FK vers `workflow_runs(id)`, `manifest_jsonb`, `overrides_sha256`, `kb_snapshot_hash`, `manifest_sha256`, `locked_at`).
  - Réversibilité complète vérifiée via `downgrade()` et `upgrade()` sur PostgreSQL 18 (`testcontainers`).

### 2.2 Noyau Métier Hexagonal, Orchestration & Workers (`packages/orcia-core/`, `apps/worker/`, `infra/sandbox/`)
- `packages/orcia-core/src/orcia_core/orchestration/models.py` :
  - Modèles immutables `@dataclass(frozen=True, slots=True)` : `WorkflowStepSpec`, `WorkflowAsCodeDefinition`, `WorkflowValidationFinding`, `WorkflowValidationReport`, `ArtifactTemplateSectionSpec`, `ArtifactTemplateDefinition`, `CompiledArtifactTemplate`, `SubWorkflowLockEntry`, `WorkflowRunEntity`.
- `packages/orcia-core/src/orcia_core/orchestration/yaml_validator.py` :
  - Parseur YAML/JSON instrumenté (`yaml.SafeLoader` avec suivi des numéros de lignes exacts par clé/item) et validateur DAG vérifiant :
    1. La syntaxe et les types des champs (`steps`, `step_type`, `criticality`, `execution_regime`, `tie_break_policy`, `max_agent_retries`).
    2. L'interdiction de `criticality == "HIGH_CRITICAL"` avec `execution_regime == "AUTONOMOUS_CONTRACT"` (`CriticalWorkflowRequiresHumanGateError`, `ERR_CRITICAL_WORKFLOW_REQUIRES_HUMAN_GATE`).
    3. La discipline `Intention -> Code` (`FR-13`) : toute étape `writes_code=True` doit posséder un ancêtre dans le DAG avec `declares_intention=True` en mode `standard` (`IntentionBeforeCodeRequiredError`, `ERR_INTENTION_BEFORE_CODE_REQUIRED`), et toute étape `reverse_doc_from_code=True` requiert `mode: brownfield_bootstrap`.
    4. La détection de cycles dans le DAG d'étapes ainsi que dans le graphe d'appels `SUB_WORKFLOW` (`SubWorkflowCycleDetectedError`, `ERR_SUB_WORKFLOW_CYCLE_DETECTED`) et le respect de `nesting_depth <= 3` (`SubWorkflowMaxDepthExceededError`, `ERR_SUB_WORKFLOW_MAX_DEPTH_EXCEEDED`).
- `packages/orcia-core/src/orcia_core/orchestration/template_compiler.py` :
  - `MultiAudienceTemplateCompiler` compilant simultanément :
    1. La vue documentaire Markdown pour le Canvas humain (interpolation déterministe `{{ variable }}`, balisage des sections `human_authored_required` et découpage en chunks cognitifs $\le 800$ mots).
    2. Le contrat formel JSON Schema (Draft 2020-12) enrichi par les schémas `expected_schema` et définitions des concepts de l'Ontologie active (`ResolvedOntologySnapshot`).
- `packages/orcia-core/src/orcia_core/orchestration/run_lock_service.py` :
  - `WorkflowOrchestrationSetupService` orchestrant l'enregistrement des manifestes validés, la compilation de gabarits et l'instanciation de `Workflow Run` avec résolution récursive des `sub_workflow_locks`, calcul du `kb_snapshot_hash` et persistance du `RunLockManifest` immuable.

### 2.3 Couche Backend API, Sécurité & Contrats (`apps/api/`, `packages/api-client/`)
- `apps/api/src/orcia_api/routers/orchestration.py` :
  - `GET /api/v1/orchestration/state` : état consolidé des workflows déclaratifs, gabarits multi-audiences et runs épinglés.
  - `POST /api/v1/orchestration/workflows/validate` : validation d'un manifeste YAML/JSON avec rapport détaillé par ligne.
  - `POST /api/v1/orchestration/workflows/register` : enregistrement d'un workflow validé (`ScopeAccessGuard` rejetant `OBSERVER` avec `HTTP 403 ERR_OBSERVER_MODE_READ_ONLY`).
  - `POST /api/v1/orchestration/templates/compile` : compilation duale d'un gabarit d'artefact multi-audience.
  - `POST /api/v1/orchestration/runs/instantiate` : instanciation d'un `Workflow Run` et génération du `run-lock.json` récursif.
- `packages/api-client/` :
  - Régénération du SDK TypeScript OpenAPI 3.1 (`0-diff` vérifié).

### 2.4 Interface Utilisateur & Expérience (`apps/web/`)
- `packages/ui/src/shell/WorkflowStudioSection.tsx` & `packages/ui/src/shell/CatalogExplorerPanel.tsx` :
  - Ajout de la section Studio Workflow-as-Code (`workflow-studio-section`), de l'aperçu Gabarit Multi-Audience (`multi-audience-template-preview` : bascule Vue Humaine Markdown / Vue Agent JSON Schema) et de l'arbre récursif `sub_workflow_locks` dans l'inspecteur `run-lock.json`, en utilisant exclusivement les tokens CSS Direction C (`tokens.css`) et les dictionnaires i18n `fr`/`en`.

---

## 3. Bilan des Modifications & Résultats (Post-Implémentation)

### 3.1 Récapitulatif des Fichiers Créés et Modifiés

| Fichier | Action | Rôle & Responsabilité | Lignes |
|---|---|---|---|
| `infra/migrations/versions/0010_story_3_1_workflow_runs_triggers_and_run_lock.py` | Créé | Migration Alembic (`0010_story_3_1`) ajoutant les colonnes `AD-18` à `workflow_definitions` et créant `workflow_triggers`, `workflow_runs` et `run_lock_manifests`. | 183 |
| `packages/orcia-core/src/orcia_core/domain/exceptions.py` | Modifié | Ajout des exceptions RFC 9457 `CriticalWorkflowRequiresHumanGateError`, `IntentionBeforeCodeRequiredError`, `SubWorkflowMaxDepthExceededError`, `SubWorkflowCycleDetectedError`. | 298 |
| `packages/orcia-core/src/orcia_core/orchestration/models.py` | Créé | Modèles immuables du domaine d'orchestration (`WorkflowAsCodeDefinition`, `SubWorkflowLockEntry`, `RecursiveRunLockManifest`, `WorkflowRunEntity`). | 296 |
| `packages/orcia-core/src/orcia_core/orchestration/yaml_loader.py` | Créé | Chargeur YAML/JSON conservant les numéros de lignes exacts (`_LineTrackingLoader`) et parseur de step (`parse_single_step_spec`). | 237 |
| `packages/orcia-core/src/orcia_core/orchestration/yaml_validator.py` | Créé | Validateur DAG (`WorkflowAsCodeValidator`) vérifiant `HIGH_CRITICAL + AUTONOMOUS_CONTRACT`, `Intention -> Code` et `SUB_WORKFLOW <= 3` sans cycle. | 452 |
| `packages/orcia-core/src/orcia_core/orchestration/template_compiler.py` | Créé | Compilateur dual (`MultiAudienceTemplateCompiler`) Markdown Humain + JSON Schema Draft 2020-12 typé par l'Ontologie. | 246 |
| `packages/orcia-core/src/orcia_core/orchestration/run_lock_service.py` | Créé | Service d'orchestration (`WorkflowOrchestrationSetupService`) et épinglage récursif `run-lock.json`. | 417 |
| `packages/orcia-core/src/orcia_core/orchestration/seeds.py` | Créé | Manifestes YAML canoniques (profondeur 0, 1 et 2) et fabrique `build_default_orchestration_setup_service()`. | 201 |
| `packages/orcia-core/src/orcia_core/schemas/orchestration.py` | Créé | Schémas Pydantic v2 OpenAPI 3.1 pour la validation YAML, la compilation de gabarit et l'instanciation de Run. | 212 |
| `apps/api/src/orcia_api/routers/orchestration.py` | Créé | Routeur FastAPI `/api/v1/orchestration/*` protégé par `ScopeAccessGuard`. | 346 |
| `infra/scripts/maintenance/06_backfill_workflow_orchestration_and_locks.py` | Créé | Script de maintenance idempotent (`--dry-run` / `--apply`) pour les workflows, triggers et `run-lock.json` récursifs. | 253 |
| `packages/ui/src/shell/WorkflowStudioSection.tsx` | Créé | Composant UI Direction C du Studio Workflow-as-Code, Gabarit Multi-Audience et `sub_workflow_locks`. | 231 |
| `packages/ui/src/__tests__/workflow-studio.test.tsx` | Créé | Tests unitaires Vitest du composant `WorkflowStudioSection`. | 87 |
| `tests/unit/test_workflow_as_code_and_run_lock.py` | Créé | Tests unitaires et property-based (`hypothesis`) de la Story 3.1. | 341 |
| `tests/integration/test_real_containers.py` | Modifié | Validation PostgreSQL 18 réelle de la migration `0010_story_3_1` et du script `06_backfill_workflow_orchestration_and_locks.py`. | 348 |

### 3.2 Métriques de Qualité & Validation des 5 Couches (`AD-17`)
- **Couverture de tests unitaires & property-based (`packages/orcia-core`)** : **`96.06 %`** (seuil exigé $\ge 90\%$, `50 passed` sur la suite complète incluant `testcontainers`).
- **Qualité statique Python** : `.venv/bin/ruff check .` (`0 errors`), `.venv/bin/ruff format --check .` (`195 files formatted`), `.venv/bin/mypy --strict packages/orcia-core apps/api apps/worker` (`Success: no issues found in 79 source files`).
- **Contrat OpenAPI 3.1 & SDK TypeScript** : `.venv/bin/python scripts/export_openapi.py --check` (`0-diff`).
- **Qualité TypeScript / UI (`pnpm turbo run lint typecheck test`)** : `9/9 tasks successful` (`13 passed` dans `@orcia/ui`, `6 passed` dans `@orcia/api-client`, `6 passed` dans `@orcia/web`).
- **Architecture Spine Lint** : `lint_spine.py` $\rightarrow$ `ok: true, total_findings: 0`.
- **Analyse de graphe pré-commit (`gitnexus_detect_changes`)** : `changed_files: 24`, `changed_count: 134`, `affected_count: 5`, `risk_level: medium` — tous les callers affectés sont couverts et passent au vert.
