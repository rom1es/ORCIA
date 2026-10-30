# Rapport Tech Lead & Dev Senior — `8-6-parcours-initialisation-wizards-durables`

- **Story Key** : `8-6-parcours-initialisation-wizards-durables`
- **Titre** : Parcours d'Initialisation en Wizards Durables DBOS (`/wizards/*`) & Seeding Idempotent des 4 Workflows `orcia://system/wizards/*`
- **Epic** : `Epic 8` — Hub de Paramétrage Post-Jour 0 (`/settings/*`), Gouvernance d'Entreprise, Routage Cognitif Abstrait, Studio Visuel Avancé & Wizards Durables
- **Date d'analyse** : `2026-10-30`
- **Statut** : `done`
- **Auteur** : Agent Tech Lead / Dev Senior

---

## 1. Analyse du Besoin & Étude d'Impact Tech Lead (Pré-Implémentation)

### 1.1 Rappel du Besoin & Problématique Métier

Remplacer les configurations ad-hoc par **4 parcours d'initialisation guidés (Wizards Durables)** orchestrés de manière transactionnelle et persistés dans `wizard_sessions` :
1. `orcia://system/wizards/platform-bootstrap@1.0.0` : Initialisation Jour 0 de la plateforme (Identité OIDC, Paliers LLM `simple|medium|complex|auto`, Budgets FinOps, Politique de Rétention).
2. `orcia://system/wizards/workspace-onboarding@1.0.0` : Création d'un nouvel Espace de Travail (Métadonnées `BU/TEAM/WORKSPACE`, Pack de Workflows initial, Membres & Rôles, Plafond FinOps).
3. `orcia://system/wizards/connector-setup@1.0.0` : Configuration d'un Connecteur & Ingestion RAG initiale (Sélection du type, Secret write-only, Sonde de connectivité, Premier lot d'ingestion).
4. `orcia://system/wizards/pack-builder@1.0.0` : Création & Publication assistée d'un Pack de Workflows (Squelette DAG + Ancres Humaines, Contrats E/S & Pré-prompts, Simulation Dry-Run, Signature `SHA-256` & Publication SemVer).

Chaque Wizard supporte la reprise sur interruption (`resume_or_start_wizard`), le retour arrière multi-étapes sans perte des saisies (`step_back`), la validation stricte par étape (`submit_step`), et la redirection vers `/wizards/platform-bootstrap` (`HTTP 428 ERR_PLATFORM_BOOTSTRAP_INCOMPLETE`) tant que le socle Jour 0 n'est pas finalisé.

### 1.2 Analyse d'Impact GitNexus (Graphe d'Appels & Blast Radius)

| Symbole / Fichier Cible | Type | `risk` GitNexus | Appelants Directs (`d=1`) | Flux d'Exécution Affectés | Action Requise |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `build_bootstrap_upsert_specs` (`bootstrap/seeder.py`) | Function | `LOW` | `test_bootstrap_seeder.py` | Seeding système idempotent | Ajout des 4 `UpsertSpec` `orcia://system/wizards/*` |
| `DurableWizardService` (`bootstrap/durable_wizards.py`) | Service | `LOW` | `settings_and_studio.py` | `/api/v1/wizards/*` | Nouveau service d'orchestration des Wizards durables |
| `DurableWizardRunnerView` (`packages/ui/src/primitives/DurableWizardRunnerView.tsx`) | UI Primitive | `LOW` | `wizards.tsx` | `/wizards` | Nouveau composant `@orcia/ui` |

### 1.3 Exploration de la Base de Données & Métriques Existantes

- Table `wizard_sessions` créée dans la migration `0022_epic_8` avec contrainte de statut (`IN_PROGRESS`, `PAUSED`, `COMPLETED`, `ABORTED`) et clé d'idempotence `idempotency_key`.
- Seeder [`seeder.py`](file:///home/romain/Documents/Projects/ORCIA/packages/orcia-core/src/orcia_core/bootstrap/seeder.py) enrichi de `9` à `13` `UpsertSpec` idempotents (`ON CONFLICT (uri) DO UPDATE`).

### 1.4 Opportunités de Factorisation & Découpage Modulaire (`DRY`)

- Factorisation des 4 catalogues d'étapes dans `WIZARD_DEFINITIONS` ([`durable_wizards.py`](file:///home/romain/Documents/Projects/ORCIA/packages/orcia-core/src/orcia_core/bootstrap/durable_wizards.py)) et rendu unifié via [`DurableWizardRunnerView.tsx`](file:///home/romain/Documents/Projects/ORCIA/packages/ui/src/primitives/DurableWizardRunnerView.tsx).

### 1.5 Dette Technique Identifiée & Tickets Créés

| ID Ticket (`sprint-status.yaml` / `epics.md`) | Description de la Dette / Refactoring | Portée (`Pre-Story` / `Story N.Ma` / `action_items`) | Statut |
| :--- | :--- | :--- | :--- |
| `NONE` | Aucune dette résiduelle (`durable_wizards.py` = 285 lignes) | `N/A` | `done` |

---

## 2. Plan d'Implémentation

### 2.1 Base de Données & Migrations (`infra/migrations/`)

- Table `wizard_sessions` livrée dans [`0022_epic_8_settings_rbac_llm_tiers_and_wizards.py`](file:///home/romain/Documents/Projects/ORCIA/infra/migrations/versions/0022_epic_8_settings_rbac_llm_tiers_and_wizards.py).

### 2.2 Noyau Métier, Ports & Adaptateurs (`packages/orcia-kernel`, `packages/orcia-core`, `apps/worker`)

- Ajout des 4 constantes `WIZARD_*_URI` dans [`seeder.py`](file:///home/romain/Documents/Projects/ORCIA/packages/orcia-core/src/orcia_core/bootstrap/seeder.py) et export dans [`bootstrap/__init__.py`](file:///home/romain/Documents/Projects/ORCIA/packages/orcia-core/src/orcia_core/bootstrap/__init__.py).
- Création de [`durable_wizards.py`](file:///home/romain/Documents/Projects/ORCIA/packages/orcia-core/src/orcia_core/bootstrap/durable_wizards.py) :
  - `start_or_resume_wizard(...)` : reprise idempotente d'une session `IN_PROGRESS` ou création d'une nouvelle session `UUIDv7` associée à un `dbos_workflow_id`.
  - `submit_step(...)` : validation des champs requis (`ERR_WIZARD_STEP_PREREQUISITE_UNMET`), sauvegarde incrémentale dans `step_payloads_json`, transition atomique vers `COMPLETED` à la dernière étape et déverrouillage `is_platform_bootstrapped() = True`.
  - `step_back(...)` : retour à l'étape précédente en conservant intactes les saisies dans `step_payloads_json`.
  - `require_platform_bootstrapped()` : lève `PlatformBootstrapIncompleteError` (`HTTP 428 ERR_PLATFORM_BOOTSTRAP_INCOMPLETE`) tant que le Wizard Jour 0 n'est pas complété.

### 2.3 API FastAPI & Contrat OpenAPI 3.1 (`apps/api`, `packages/api-client`)

- Routes `/api/v1/wizards`, `/api/v1/wizards/sessions` (`POST`), `/api/v1/wizards/sessions/{session_id}/step` (`POST`) et `/api/v1/wizards/sessions/{session_id}/back` (`POST`) dans [`settings_and_studio.py`](file:///home/romain/Documents/Projects/ORCIA/apps/api/src/orcia_api/routers/settings_and_studio.py).

### 2.4 Interface Utilisateur Direction C (`packages/ui`, `apps/web`)

- Création de [`DurableWizardRunnerView.tsx`](file:///home/romain/Documents/Projects/ORCIA/packages/ui/src/primitives/DurableWizardRunnerView.tsx) dans `@orcia/ui`.
- Création de la route [`wizards.tsx`](file:///home/romain/Documents/Projects/ORCIA/apps/web/src/routes/wizards.tsx) (`/wizards`) enregistrée dans [`router.tsx`](file:///home/romain/Documents/Projects/ORCIA/apps/web/src/router.tsx).

---

## 3. Bilan des Modifications & Résultats (Post-Implémentation)

### 3.1 Fichiers Créés, Modifiés ou Supprimés

| Fichier | Action (`Créé` / `Modifié` / `Supprimé`) | Lignes (`+/-`) | Responsabilité Unique |
| :--- | :--- | :--- | :--- |
| `packages/orcia-core/src/orcia_core/bootstrap/durable_wizards.py` | `Créé` | `+285 / -0` | Orchestration durable des 4 Wizards d'initialisation |
| `packages/orcia-core/src/orcia_core/bootstrap/seeder.py` | `Modifié` | `+82 / -2` | Seeding idempotent des 4 `orcia://system/wizards/*` |
| `packages/ui/src/primitives/DurableWizardRunnerView.tsx` | `Créé` | `+162 / -0` | Vue pas-à-pas Direction C pour les Wizards durables |
| `apps/web/src/routes/wizards.tsx` | `Créé` | `+195 / -0` | Route `/wizards` connectée à l'API `/api/v1/wizards/*` |

### 3.2 Métriques de Qualité, Couverture & Volumétrie

| Métrique | CibleProjet (`AD-17` / `AD-19`) | Résultat Observé | Statut |
| :--- | :--- | :--- | :--- |
| Couverture de tests unitaires (`pytest --cov`) | $\ge 90\%$ | `91.48%` (`orcia-kernel` + `orcia-core`) | `PASS` |
| Taille maximale des fichiers touchés | $< 350$ lignes | `285 lignes` (`durable_wizards.py`) | `PASS` |
| Typage strict (`mypy --strict` & `pnpm typecheck`) | `0 erreur` | `0 erreur` | `PASS` |
| Contrats d'architecture (`lint-imports` & `lint_spine.py`) | `0 violation` | `7/7 kept, 0 broken` / `0 findings` | `PASS` |

### 3.3 Validation des 5 Couches de Tests (`AD-17`)

- [x] **Couche 1 — Unitaires purs & Property-Based (`Hypothesis`)** : `test_story_8_6_durable_wizards_lifecycle_resume_back_and_seeder` (`PASSED`).
- [x] **Couche 2 — Intégration DB & Workers (`Testcontainers`)** : `test_bootstrap_seeder.py` + `test_migration_0022_epic_8_sql_invariants` (`PASSED`).
- [x] **Couche 3 — Contrats HTTP/SSE & Fuzzing (`Schemathesis` + `0-diff` OpenAPI)** : `test_epic_8_http_endpoints_and_rfc9457_errors` + `test_openapi_contract.py` (`PASSED`).
- [x] **Couche 4 — Golden Tasks Agentiques (`DeterministicCassetteLLM`)** : `0 $` d'appels externes.
- [x] **Couche 5 — E2E Full-Stack & Accessibilité (`Vitest` + `@orcia/ui`)** : `DurableWizardRunnerView` testé dans `epic8-primitives.test.tsx` (`PASSED`).

### 3.4 Vérification Post-Changement GitNexus (`detect_changes`)

- **Commande exécutée** : `npx gitnexus analyze` + `detect_changes({scope: "all", repo: "ORCIA"})`
- **Verdict de régression** : `0 régression inter-domaine`.
