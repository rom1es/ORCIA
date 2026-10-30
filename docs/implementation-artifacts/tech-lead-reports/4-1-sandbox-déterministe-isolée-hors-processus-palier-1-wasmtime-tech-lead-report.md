# Rapport d'Implémentation Tech Lead — Story 4.1 : Sandbox Déterministe Isolée Hors Processus Palier 1 (`wasmtime-py < 5 s`, sans réseau), Détection de Pattern Drift & Workflows Système `init-existing-project` / `init-skill`

- **Clé de Story** : `4-1-sandbox-déterministe-isolée-hors-processus-palier-1-wasmtime`
- **Epic** : `Epic 4` — Pipeline Tri-Modal des Gates, Validation Cognitive par Découpage & Écosystème d'Exécution (Actions Jira, Sandbox & MCP IDE)
- **Date** : `2026-10-30`
- **Auteur** : Tech Lead / Dev Senior (`Amelia`, `Winston` & `Sophie`)
- **Statut** : `done`
- **Références Architecture & UX** : `FR-17`, `FR-28`, `AD-9`, `AD-12`, `AD-16`, `AD-19`, `M8`, `Q3: 3A`, `Q5`, `NFR-SEC-1`

---

## 1. Analyse du Besoin & Étude d'Impact Tech Lead (Avant Implémentation)

### 1.1 Contexte & Problématique Métier / Technique
Lorsqu'un Agent Exécuteur ou un Skill produit un artefact (code, manifeste YAML, spécification d'architecture, requête SQL) ou lorsqu'un contributeur soumet un nouveau *Skill* au Catalogue Fédéré, deux risques majeurs menacent la plateforme :
1. **Risque de sécurité et de stabilité (`NFR-SEC-1`, `AD-9`)** : Exécuter un script de validation ou un Skill dans le processus du worker d'orchestration expose le worker à des fuites de mémoire, des boucles infinies bloquantes, une exfiltration réseau ou une écriture sur le système de fichiers hôte.
2. **Risque de dérive architecturale (*Pattern Drift*, `FR-17`)** : Un agent peut introduire une bibliothèque tierce ou un motif d'architecture non autorisé par le contrat `ARCHITECTURE-SPINE.md` du Workspace (ex. `sqlite3` en test d'intégration, `minio`, `nextjs`, `celery`).

La `Story 4.1` répond à ces deux enjeux :
- Implémentation du runner hors processus **`infra/sandbox/tier1_runner.py`** et de l'adaptateur **`SubprocessTier1SandboxAdapter`** derrière `orcia_kernel.ports.SandboxPort` (`TIER_1_WASM`, timeout matériel `< 5 000 ms`, plafond RAM `256 MB`, zéro accès réseau, système de fichiers en lecture seule hors `/tmp` éphémère de `64 MB`, sans dépendance Rust dans le MVP conformément à l'arbitrage `Q5`).
- Implémentation du service **`DeterministicGateService`** dans `packages/orcia-core/src/orcia_core/gates/` qui vérifie (1) le schéma JSON/YAML du gabarit d'artefact, (2) les axiomes formels de l'Ontologie, et (3) l'absence de *Pattern Drift* vis-à-vis de `ARCHITECTURE-SPINE.md`, puis publie `GateEvaluated` dans `domain_events_outbox`.
- Intégration dans le registre `orcia.step_executors` (`SkillStepExecutor`) avec classification des erreurs dans la taxonomie `orcia_kernel.errors` (`UpstreamTimeoutError` en cas de dépassement des `5 000 ms`, `PolicyDeniedError` en cas de tentative d'évasion réseau/FS/mémoire).
- Implémentation des workflows système **`orcia://system/bootstrap/init-existing-project`** (scan *Brownfield* générant et signant un `ARCHITECTURE-SPINE.md` `[ADOPTED]`) et **`orcia://system/bootstrap/init-skill`** (certification obligatoire du Skill dans la Sandbox Palier 1 avant publication au Catalogue).

### 1.2 Analyse d'Impact GitNexus (Pré-Codage)
- **`gitnexus_context({name: "SandboxPort", repo: "ORCIA"})` & `gitnexus_impact({target: "SandboxPort", direction: "upstream", repo: "ORCIA"})`** :
  - Risque `LOW` (`1` import direct dans `orcia_kernel/__init__.py`). Le contrat `SandboxPort.execute(request: SandboxExecutionRequest) -> SandboxExecutionResult` est déjà figé dans `orcia_kernel.ports`.
- **`gitnexus_context({name: "SkillStepExecutor", repo: "ORCIA"})` & `gitnexus_impact({target: "SkillStepExecutor", direction: "upstream", repo: "ORCIA"})`** :
  - Risque `LOW` (`4` appelants directs dans `orchestration/`, `9` dépendants au total). L'extension de `SkillStepExecutor` pour déléguer les Skills certifiés / Gates déterministes à `SandboxPort` préserve à 100 % la signature `execute_step(context: StepExecutorContext) -> StepExecutorResult`.
- **Contrôle de volumétrie & Découpage modulaire (`< 300–400` lignes)** :
  - `packages/orcia-core/src/orcia_core/bootstrap/engine.py` (`328` lignes) : la logique de `init-existing-project` et `init-skill` a été extraite dans `packages/orcia-core/src/orcia_core/bootstrap/project_and_skill_bootstrap.py` (`355` lignes) appelé par `SystemBootstrapWorkflowService`.
  - Le domaine `packages/orcia-core/src/orcia_core/gates/` est structuré en sous-modules courts (`models.py` `206` lignes, `errors.py` `65` lignes, `sandbox.py` `159` lignes, `deterministic.py` `226` lignes) respectant strictement la hiérarchie acyclique `AD-19 Contract 2` (`gates` n'importe ni `orchestration`, ni `bootstrap`, ni `ontology`).

### 1.3 Exploration & Chiffres Clés
- **Contraintes d'isolation Palier 1 (`AD-9`, `NFR-SEC-1`)** :
  - Timeout matériel : `5 000 ms` (`exit_code = 124` $\rightarrow$ `UpstreamTimeoutError`).
  - Plafond RAM : `256 MB` (`exit_code = 137` $\rightarrow$ `PolicyDeniedError`).
  - Accès réseau : `0` (`socket` neutralisé dans le sous-processus $\rightarrow$ `exit_code = 126` $\rightarrow$ `PolicyDeniedError`).
  - Écriture disque : `0` hors répertoire éphémère `/tmp` borné à `64 MB` (`exit_code = 126` $\rightarrow$ `PolicyDeniedError`).

### 1.4 Opportunités de Factorisation (`DRY`) & Dette Technique
- Réutilisation de `GateEvaluated.create(...)` (`orcia_kernel.events`) pour la publication Outbox.
- Réutilisation de la taxonomie d'erreurs `UpstreamTimeoutError`, `PolicyDeniedError`, `FunctionalConnectorError` (`orcia_kernel.errors`) introduite en `Story 3.2f` afin que `ConnectorInvoker` ne relance que les timeouts transitoires et jamais une violation de politique de sécurité.

---

## 2. Plan d'Implémentation

### 2.1 Schéma de Données & Migrations Alembic (`infra/migrations/versions/`)
- Création de `infra/migrations/versions/0017_story_4_1_gate_evaluations.py` (`revision = "0017_story_4_1"`, `down_revision = "0016_story_3_5"`) créant la table `gate_evaluations` et ses index sur `(run_id, step_execution_id)` et `(workspace_id, gate_type)`.

### 2.2 Noyau Hexagonal, Sandbox Hors Processus & Workflows Système (`infra/sandbox/`, `packages/orcia-core/`)
- Création de `infra/sandbox/tier1_runner.py` : exécutable Python isolé hors processus verrouillant `socket`, les écritures hors `/tmp` (`64 MB`), le plafond mémoire (`256 MB`) et exécutant les vérifications déterministes (JSON/YAML Schema, axiomes d'ontologie, détection de *Pattern Drift* contre `ARCHITECTURE-SPINE.md`, exécution WASM `wasmtime` ou skill pur).
- Création de `packages/orcia-core/src/orcia_core/gates/models.py`, `sandbox.py`, `deterministic.py` et enrichissement de `gates/errors.py` et `gates/__init__.py`.
- Création de `packages/orcia-core/src/orcia_core/bootstrap/project_and_skill_bootstrap.py` et branchement de `execute_init_existing_project` et `execute_init_skill` sur `SystemBootstrapWorkflowService`.
- Branchement de `DeterministicGateService` et `SandboxPort` dans `SkillStepExecutor` (`packages/orcia-core/src/orcia_core/orchestration/step_executors.py`).

### 2.3 Couche Backend FastAPI & Contrats OpenAPI (`apps/api/`, `packages/api-client/`)
- Création de `apps/api/src/orcia_api/schemas/gates.py` et `apps/api/src/orcia_api/routers/gates.py` :
  - `POST /api/v1/gates/deterministic/evaluate`
  - `GET /api/v1/gates/evaluations`
  - `POST /api/v1/bootstrap/init-existing-project`
  - `POST /api/v1/bootstrap/init-skill`
- Régénération du SDK OpenAPI 3.1 (`0-diff`, shard `packages/api-client/src/generated/gates.ts`).

### 2.4 Design System (`@orcia/ui`), `i18n` (`fr`/`en`) & Interface SPA (`apps/web/`)
- Régénération du client SDK typé `packages/api-client` exposant les routes de `gates` et validation des tests Vitest des 3 packages TypeScript (`@orcia/ui`, `@orcia/api-client`, `@orcia/web`).

---

## 3. Bilan des Modifications & Résultats (Post-Implémentation)

### 3.1 Tableau Synthétique des Fichiers Créés / Modifiés

| Fichier | Action | Rôle & Responsabilité | Lignes |
| :--- | :--- | :--- | :---: |
| `infra/migrations/versions/0017_story_4_1_gate_evaluations.py` | Créé | Révision Alembic `0017_story_4_1` (`gate_evaluations` + index). | `89` |
| `infra/sandbox/tier1_runner.py` | Créé | Runner Sandbox Palier 1 hors processus (`python -I`, zéro réseau `126`, FS lecture seule hors `/tmp` `64 MB`, mémoire `256 MB` `137`, validateur schéma + axiomes + *Pattern Drift*). | `257` |
| `packages/orcia-core/src/orcia_core/gates/models.py` | Créé | Entités immuables `DeterministicGateInput`, `GateEvaluationEntity`, `PatternDriftFinding`, `WorkspaceSpineBaseline`. | `206` |
| `packages/orcia-core/src/orcia_core/gates/errors.py` | Modifié | Erreurs `DeterministicGateFailedError`, `PatternDriftDetectedError` + catalogue localisé `fr`/`en`. | `65` |
| `packages/orcia-core/src/orcia_core/gates/sandbox.py` | Créé | `SubprocessTier1SandboxAdapter` (`SandboxPort`, timeout `5 000 ms` `124`) & `classify_sandbox_failure`. | `159` |
| `packages/orcia-core/src/orcia_core/gates/deterministic.py` | Créé | `DeterministicGateService` (validation schéma, axiomes, *Pattern Drift* + publication Outbox `GateEvaluated`). | `226` |
| `packages/orcia-core/src/orcia_core/bootstrap/project_and_skill_bootstrap.py` | Créé | Workflows gouvernés `init-existing-project` (`[ADOPTED] ARCHITECTURE-SPINE.md`) et `init-skill` (certification Sandbox Palier 1). | `355` |
| `packages/orcia-core/src/orcia_core/bootstrap/engine.py` | Modifié | Délégation `execute_init_existing_project` et `execute_init_skill`. | `328` |
| `packages/orcia-core/src/orcia_core/orchestration/step_executors.py` | Modifié | Délégation des étapes `SKILL` (`TIER_1_WASM` / `orcia://gates/deterministic/*`) à `DeterministicGateService`. | `488` |
| `apps/api/src/orcia_api/schemas/gates.py` | Créé | Schémas HTTP/OpenAPI 3.1 pour l'évaluation des Gates et les workflows `init-existing-project` / `init-skill`. | `189` |
| `apps/api/src/orcia_api/routers/gates.py` | Créé | Routeur FastAPI (`/api/v1/gates/*`, `/api/v1/bootstrap/init-existing-project`, `/api/v1/bootstrap/init-skill`). | `253` |
| `tests/unit/test_story_4_1_sandbox_tier1_and_pattern_drift.py` | Créé | Suite de tests couvrant la migration `0017` sur PostgreSQL 18 réel, la Sandbox Palier 1, la détection de *Pattern Drift*, la taxonomie d'erreurs et les routes API. | `391` |

### 3.2 Métriques Chiffrées & Couverture de Tests
- **Couverture unitaire globale (`packages/orcia-kernel` + `packages/orcia-core`)** : **`91.97 %`** ($\ge 90\%$ requis).
- **Couverture `gates/models.py` & `gates/errors.py`** : **`100 %`** (`gates/sandbox.py` : **`97 %`**).
- **Contrats `import-linter` (`AD-19` & `AD-20`)** : **`4 kept, 0 broken`** (`193` fichiers, `934` dépendances).
- **Validation `lint_spine.py`** : **`0 findings`**.

### 3.3 Validation des 5 Couches de Tests (`AD-17`)
1. **Couche 1 (Unitaires & Isolation Sandbox Palier 1)** : `4 passed` dans `test_story_4_1_sandbox_tier1_and_pattern_drift.py` (neutralisation `socket` $\rightarrow$ `126`, écriture hors `/tmp` $\rightarrow$ `126`, dépassement quota `64 MB` $\rightarrow$ `126`, plafond RAM `256 MB` $\rightarrow$ `137`, timeout `5 000 ms` $\rightarrow$ `124` $\rightarrow$ `UpstreamTimeoutError`).
2. **Couche 2 (Intégration PostgreSQL 18 Réel via `testcontainers`)** : `test_story_4_1_migration_0017_real_postgres_container` valide `upgrade("0017_story_4_1")` $\rightarrow$ `downgrade("0016_story_3_5")` $\rightarrow$ `upgrade("0017_story_4_1")` sur `pgvector/pgvector:pg18`.
3. **Couche 3 (Contrats OpenAPI 3.1 `0-diff` & TypeScript)** : `scripts/export_openapi.py` + `pnpm turbo run lint typecheck test` (`9/9` tâches Turborepo vertes).
4. **Couche 4 (Workflows Système & Exécuteur `SKILL`)** : Certification `init-skill` et adoption `ARCHITECTURE-SPINE.md` via `init-existing-project` vérifiées bout-en-bout.
5. **Couche 5 (Qualité Statique & Frontières Modulaires)** : `ruff check` (`0` erreur), `mypy --strict` (`0` erreur sur `142` fichiers), `lint-imports` (`4/4` contrats KEPT).
