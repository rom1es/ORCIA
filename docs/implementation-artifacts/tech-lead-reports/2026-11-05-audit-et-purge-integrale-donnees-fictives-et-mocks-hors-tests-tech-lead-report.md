# Rapport d'Implémentation Tech Lead — Audit & Purge Intégrale des Données Fictives et Mocks hors Tests (`2026-11-05`)

- **Date** : `2026-11-05`
- **Périmètre** : `Audit & Purge Production « Zero Mock & Zero Fictional Data » hors tests/`
- **Auteur** : Agent Tech Lead / Production Integrity & Zero-Mock Auditor
- **Branche** : `feat/zero-mock-zero-fictional-data-production`
- **Références** : `AD-10`, `AD-17`, `AD-19`, `DEC-SEED-01`, `Story 12.4`, `GEMINI.md`

---

## 1. Analyse du Besoin & Étude d'Impact Tech Lead (Avant Implémentation)

### 1.1 Contexte & Problématique Métier / Technique

Bien que la `Story 12.4` ait épuré les dictionnaires `i18n` et le store React de configuration initiale (`platformSetupStore.tsx` qui démarre avec des tableaux `[]`), une revue d'intégrité de production couche par couche (`Web/UI`, `API Composition Root`, `Core Domain`, `Maintenance & Seed SQL`) a mis en évidence **4 résidus critiques de données fictives ou d'adaptateurs de test câblés par défaut hors de `tests/`** :

1. **Couche 1 — Frontend Web (`apps/web/src/components/`)** :
   - [`ShellContainer.tsx`](file:///home/romain/Documents/Projects/ORCIA/apps/web/src/components/ShellContainer.tsx) définissait en dur une constante `DEFAULT_SEARCH_HITS` contenant 3 résultats fictifs (`hit-folder-1` « Dossier Architecture & Intégration », `hit-proc-1` « Processus Ticket-to-Tech-Spec », `hit-help-1` « Résoudre une alerte de fraîcheur documentaire ») injectée statiquement dans `<TopHeaderSearchCommand speed1Hits={DEFAULT_SEARCH_HITS} />`. Même à Jour 0 avec `0` espace et `0` document, la palette `⌘K` affichait ces 3 entrées fictives.
   - [`ontologyFixtures.ts`](file:///home/romain/Documents/Projects/ORCIA/apps/web/src/components/ontologyFixtures.ts) conservait en code applicatif (`apps/web/src/`) des fixtures fictives (`PAY-142`, `payment_order`, `fraud_score`, `tripartite_trace_edges`, `kb_stale_alerts`) orphelines (`0` import dans le monorepo).
2. **Couche 2 — Composition Root FastAPI (`apps/api/src/orcia_api/dependencies/core_and_lifespan.py`)** :
   - `initialize_app_services()` instifiait inconditionnellement `DeterministicCassetteLLM()` comme `app.state.llm_gateway` par défaut au lieu de l'adaptateur de production [`LiteLLMAdapter`](file:///home/romain/Documents/Projects/ORCIA/packages/orcia-core/src/orcia_core/bootstrap/_internal/litellm_adapter.py).
3. **Couche 3 — Noyau Métier (`packages/orcia-core/src/orcia_core/rag/two_speed_search.py`)** :
   - `TwoSpeedFederatedSearchService.__init__` pré-peuplait par défaut son index avec `candidates: tuple[FederatedSearchCandidate, ...] = DEFAULT_SEARCH_CANDIDATES` (`ws-claims-alpha`, `cand-folder-arch-1`, `cand-proc-spec-1`, `cand-help-cockpit-1`), faussant les résultats de `GET /api/v1/search` sur une instance vierge.
4. **Couche 4 — Scripts de Maintenance & Seeding SQL (`infra/scripts/maintenance/04_backfill_system_bootstrap.py`)** :
   - Le script [`04_backfill_system_bootstrap.py`](file:///home/romain/Documents/Projects/ORCIA/infra/scripts/maintenance/04_backfill_system_bootstrap.py) (invoqué par `pnpm db:seed`) insérait en base PostgreSQL 18 trois utilisateurs fictifs (`_REFERENCE_USERS` : `karim.admin@orcia.io`, `marc.lead@orcia.io`, `nadia.dev@orcia.io`), ainsi que les unités d'organisation fictives (`DEFAULT_ORG_UNIT_SEEDS`), espaces fictifs (`DEFAULT_WORKSPACE_SEEDS`), exécutions d'amorçage (`DEFAULT_SYSTEM_BOOTSTRAP_RUN_SEEDS`) et états d'onboarding (`DEFAULT_USER_ONBOARDING_STATE_SEEDS`) associés. Or, l'inscription d'un faux administrateur (`karim.admin@orcia.io`) dans la table `users` court-circuitait la détection Jour 0 (`COUNT(*) FROM users == 0`) et empêchait l'ouverture de la modale de création du 1er Administrateur (`Story 9.2` / `Story 12.4`).

### 1.2 Analyse d'Impact GitNexus (Exécutée Avant Codage)

Requêtes exécutées sur le graphe `repo: "ORCIA"` :
- `gitnexus_query({search_query: "DEFAULT_SEARCH_CANDIDATES TwoSpeedFederatedSearchService DeterministicCassetteLLM", repo: "ORCIA"})`
- `gitnexus_impact({target: "TwoSpeedFederatedSearchService", direction: "upstream", repo: "ORCIA"})`
- `gitnexus_impact({target: "DeterministicCassetteLLM", direction: "upstream", repo: "ORCIA"})`

| Symbole / Fichier Cible | Appelants Amont (`upstream`) | Niveau de Risque | Décision Tech Lead |
| :--- | :--- | :--- | :--- |
| `TwoSpeedFederatedSearchService` (`orcia_core/rag/two_speed_search.py`) | `get_two_speed_search_service` (`portal_and_assistant.py`), `execute_two_speed_federated_search` (`routers/portal_and_help.py`), `tests/unit/test_epic_9_story_9_3_two_speed_search.py` | **LOW** (`d=1: 3`, `d=2: 1`) | Remplacer la valeur par défaut `candidates = DEFAULT_SEARCH_CANDIDATES` par `candidates: Sequence[FederatedSearchCandidate] = ()`. Injecter `DEFAULT_SEARCH_CANDIDATES` explicitement dans le test HTTP unitaire `test_story_9_3_get_api_v1_search_endpoint`. |
| `DeterministicCassetteLLM` (`orcia_core/testing/cassette_llm.py`) | `initialize_app_services` (`core_and_lifespan.py`), `LiteLLMAdapter` (`litellm_adapter.py`), `AgentStepExecutor` (`step_executors.py`), `AssistantAgentService` (`assistant_agent.py`), `AgenticGateService` (`gates/agentic.py`), + tests unitaires | **HIGH** (`d=1: 18` dont 13 dans `tests/`) | Câbler `LiteLLMAdapter(fallback_cassette=DeterministicCassetteLLM())` par défaut dans `initialize_app_services()` (sauf si `ORCIA_USE_CASSETTE_LLM=true`), et exposer `register()` sur `LiteLLMAdapter` (délégué à `fallback_cassette`) ainsi que la ré-exportation publique `from orcia_core.bootstrap import LiteLLMAdapter` conforme à `AD-19`. |
| `DEFAULT_SEARCH_HITS` (`apps/web/src/components/ShellContainer.tsx`) | Local à `ShellContainer.tsx` (`speed1Hits`) | **LOW** | Supprimer `DEFAULT_SEARCH_HITS` et dériver dynamiquement `speed1Hits` à partir des entités réellement créées par l'utilisateur (`workspaces`, `catalogItems`, `ontologyConcepts`) dans `usePlatformSetup()` (`[]` à Jour 0). |
| `apps/web/src/components/ontologyFixtures.ts` | `0` appelant dans tout le monorepo | **LOW** | Supprimer ce fichier de fixtures orphelin contenant des données fictives `PAY-142`. |
| `04_backfill_system_bootstrap.py` | `pnpm db:seed`, `tests/unit/test_system_bootstrap.py`, `tests/integration/test_real_containers.py` (+ `3_2b`, `3_2c`, `3_2f`) | **MEDIUM** | Retirer `_REFERENCE_USERS` (`karim`, `marc`, `nadia`), `DEFAULT_ORG_UNIT_SEEDS`, `DEFAULT_WORKSPACE_SEEDS`, `DEFAULT_SYSTEM_BOOTSTRAP_RUN_SEEDS` et `DEFAULT_USER_ONBOARDING_STATE_SEEDS` de `04_backfill_system_bootstrap.py` afin qu'il ne sème que les workflows système (`orcia://system/bootstrap/*` + `orcia://system/workflows/assistant-agent`) et les endpoints LLM de référence (`0` utilisateur créé). |

### 1.3 Audit Complet des 5 Couches (Inventaire Exhaustif)

| Couche | Périmètre Audité | Anomalies Détectées | Statut Cible Post-Purge |
| :--- | :--- | :--- | :--- |
| **1. Web & UI** | `apps/web/src/**`, `packages/ui/src/**` | `DEFAULT_SEARCH_HITS` en dur dans `ShellContainer.tsx` ; fichier orphelin `ontologyFixtures.ts` (`PAY-142`). Tous les écrans `features/*/index.tsx`, `routes/settings.tsx`, `routes/wizards.tsx` et `platformSetupStore.tsx` démarrent déjà à vide (`[]`). | `0` donnée fictive en dur dans `apps/web/src/` et `packages/ui/src/`. |
| **2. API Composition Root & Routers** | `apps/api/src/orcia_api/**` | `core_and_lifespan.py:L61` instancie `DeterministicCassetteLLM()` au lieu de `LiteLLMAdapter`. | `LiteLLMAdapter` câblé par défaut dans `initialize_app_services()` (bascule sur `DeterministicCassetteLLM` uniquement si `ORCIA_USE_CASSETTE_LLM=true`). |
| **3. Core Domain** | `packages/orcia-core/src/orcia_core/**` | `TwoSpeedFederatedSearchService.__init__` utilise `DEFAULT_SEARCH_CANDIDATES` par défaut. `LiteLLMAdapter` confiné dans `bootstrap/_internal/litellm_adapter.py` sans ré-export dans `bootstrap/__init__.py`. | `TwoSpeedFederatedSearchService()` démarre avec `candidates=()` (`0` candidat fictif) ; `LiteLLMAdapter` ré-exporté publiquement par `orcia_core.bootstrap`. |
| **4. Scripts de Maintenance & Seed SQL** | `infra/scripts/maintenance/*.py`, `package.json` | `04_backfill_system_bootstrap.py` (exécuté par `pnpm db:seed`) insère 3 utilisateurs fictifs (`karim`, `marc`, `nadia`), des OrgUnits/Workspaces fictifs et des runs fictifs. | `04_backfill_system_bootstrap.py` n'insère que les workflows système (`6` workflows) et les endpoints LLM (`0` utilisateur, `0` org/workspace/run fictif). |
| **5. Workers & Sandbox** | `apps/worker/src/orcia_worker/**`, `infra/sandbox/**` | Aucune donnée fictive persistée au démarrage ; les rôles Dramatiq/DBOS consomment exclusivement la base PostgreSQL 18 et la table `domain_events_outbox`. | Conforme (`0` modification requise). |

### 1.4 Opportunités de Factorisation & Contrôle de Volumétrie

- **Respect strict d'`AD-19` (`lint-imports`)** : `apps/api` ne doit jamais importer depuis `orcia_core.bootstrap._internal.litellm_adapter`. Nous ré-exportons `LiteLLMAdapter` dans `packages/orcia-core/src/orcia_core/bootstrap/__init__.py`.
- **Délégation de cassette de secours sur `LiteLLMAdapter`** : En ajoutant une méthode `register(prompt_substring, entry)` sur `LiteLLMAdapter` qui délègue à son `fallback_cassette` (ainsi qu'une propriété `registered_keys`), `LiteLLMAdapter` reste 100 % compatible avec les tests qui enregistrent des entrées déterministes hors-ligne lorsque `ORCIA_LITELLM_LIVE` n'est pas activé, tout en étant le véritable adaptateur de production `LiteLLMAdapter` par défaut.
- **Contrôle de volumétrie** :
  - `ShellContainer.tsx` : suppression des 48 lignes de `DEFAULT_SEARCH_HITS` et remplacement par un `useMemo` concis dérivant les éléments de recherche depuis les entités configurées (`workspaces`, `catalogItems`, `ontologyConcepts`).
  - `ontologyFixtures.ts` : suppression complète du fichier mort (`142` lignes supprimées).
  - `04_backfill_system_bootstrap.py` : allègement de `~140` lignes en supprimant `_REFERENCE_USERS` et les boucles d'insertion fictives.

---

## 2. Plan d'Implémentation

### 2.1 Schéma de Données & Scripts de Maintenance SQL (`infra/scripts/maintenance/`)

- Aucune migration Alembic requise (le schéma PostgreSQL 18 des 27 révisions `0001` à `0027` est inchangé).
- Dans [`infra/scripts/maintenance/04_backfill_system_bootstrap.py`](file:///home/romain/Documents/Projects/ORCIA/infra/scripts/maintenance/04_backfill_system_bootstrap.py) :
  - Supprimer `_REFERENCE_USERS` (`karim.admin@orcia.io`, `marc.lead@orcia.io`, `nadia.dev@orcia.io`).
  - Supprimer l'insertion de `DEFAULT_ORG_UNIT_SEEDS`, `_REFERENCE_USERS`, `DEFAULT_WORKSPACE_SEEDS`, `DEFAULT_SYSTEM_BOOTSTRAP_RUN_SEEDS` et `DEFAULT_USER_ONBOARDING_STATE_SEEDS`.
  - Conserver uniquement le seeding idempotent des workflows système (`DEFAULT_SYSTEM_BOOTSTRAP_WORKFLOW_SEEDS` + `orcia://system/workflows/assistant-agent` dans `catalog_items` et `workflow_definitions`) et des endpoints LLM (`DEFAULT_LLM_MODEL_ENDPOINT_SEEDS`), avec `bootstrap_runs_count = 0` et `onboarding_states_count = 0` dans `SystemBootstrapBackfillReport`.

### 2.2 Noyau Hexagonal (`packages/orcia-core/`)

- Dans [`packages/orcia-core/src/orcia_core/rag/two_speed_search.py`](file:///home/romain/Documents/Projects/ORCIA/packages/orcia-core/src/orcia_core/rag/two_speed_search.py) :
  - Modifier `TwoSpeedFederatedSearchService.__init__` pour que `candidates: Sequence[FederatedSearchCandidate] = ()` soit vide par défaut (`0` candidat pré-peuplé en production).
- Dans [`packages/orcia-core/src/orcia_core/bootstrap/_internal/litellm_adapter.py`](file:///home/romain/Documents/Projects/ORCIA/packages/orcia-core/src/orcia_core/bootstrap/_internal/litellm_adapter.py) et [`packages/orcia-core/src/orcia_core/bootstrap/__init__.py`](file:///home/romain/Documents/Projects/ORCIA/packages/orcia-core/src/orcia_core/bootstrap/__init__.py) :
  - Ajouter `register(prompt_substring: str, entry: CassetteEntry) -> None` et `registered_keys` sur `LiteLLMAdapter` (déléguant à `self._fallback_cassette`) pour permettre aux tests hors-ligne d'enregistrer des scénarios sans remplacer `LiteLLMAdapter`.
  - Ré-exporter `LiteLLMAdapter` dans `orcia_core.bootstrap.__init__.__all__`.

### 2.3 Couche Backend FastAPI (`apps/api/`)

- Dans [`apps/api/src/orcia_api/dependencies/core_and_lifespan.py`](file:///home/romain/Documents/Projects/ORCIA/apps/api/src/orcia_api/dependencies/core_and_lifespan.py) :
  - Importer `LiteLLMAdapter` depuis `orcia_core.bootstrap`.
  - Dans `initialize_app_services(app)` : instancier `LiteLLMAdapter()` par défaut, et n'instancier `DeterministicCassetteLLM()` directement que si la variable d'environnement explicite `ORCIA_USE_CASSETTE_LLM` vaut `"1"`, `"true"` ou `"yes"`.

### 2.4 Interface SPA Vite + TanStack Router Direction C (`apps/web/`)

- Dans [`apps/web/src/components/ShellContainer.tsx`](file:///home/romain/Documents/Projects/ORCIA/apps/web/src/components/ShellContainer.tsx) :
  - Supprimer `DEFAULT_SEARCH_HITS`.
  - Construire dynamiquement `speed1Hits` via `useMemo` à partir des entités réellement présentes dans `usePlatformSetup()` (`workspaces`, `catalogItems`, `ontologyConcepts`). À Jour 0, `speed1Hits` vaut `[]`.
- Supprimer le fichier inutilisé [`apps/web/src/components/ontologyFixtures.ts`](file:///home/romain/Documents/Projects/ORCIA/apps/web/src/components/ontologyFixtures.ts).

### 2.5 Tests Unitaires & Garde-Fou de Non-Régression (`tests/unit/`)

- Créer [`tests/unit/test_zero_fictional_data_and_mocks_in_prod.py`](file:///home/romain/Documents/Projects/ORCIA/tests/unit/test_zero_fictional_data_and_mocks_in_prod.py) vérifiant :
  1. `0` résultat fictif par défaut dans `TwoSpeedFederatedSearchService()`.
  2. `LiteLLMAdapter` (et non `DeterministicCassetteLLM`) câblé par défaut dans `create_app()` / `initialize_app_services()` hors flag `ORCIA_USE_CASSETTE_LLM`.
  3. `0` utilisateur fictif (`karim`, `marc`, `nadia`) dans `04_backfill_system_bootstrap.py`.
  4. Absence de `DEFAULT_SEARCH_HITS` dans `ShellContainer.tsx` et absence du fichier `ontologyFixtures.ts`.
- Mettre à jour `tests/unit/test_epic_9_story_9_3_two_speed_search.py` (`test_story_9_3_get_api_v1_search_endpoint`) pour injecter explicitement `DEFAULT_SEARCH_CANDIDATES` dans `app.state.two_speed_search_service` lors du test du endpoint `/api/v1/search`.

---

## 3. Bilan des Modifications & Résultats (Post-Implémentation)

### 3.1 Fichiers Créés ou Modifiés

| Fichier | Action | Rôle & Responsabilité | Lignes |
| :--- | :--- | :--- | :--- |
| `docs/implementation-artifacts/tech-lead-reports/2026-11-05-audit-et-purge-integrale-donnees-fictives-et-mocks-hors-tests-tech-lead-report.md` | Créé | Rapport Tech Lead d'audit et de purge intégrale des mocks et données fictives hors `tests/` | 145 |
| `docs/implementation-artifacts/tech-lead-reports/README.md` | Modifié | Indexation du rapport Tech Lead dans l'index central | 90 |
| `apps/api/src/orcia_api/dependencies/core_and_lifespan.py` | Modifié | Câblage de `LiteLLMAdapter()` par défaut en production ; `DeterministicCassetteLLM` réservé à `ORCIA_USE_CASSETTE_LLM=true` | 290 |
| `packages/orcia-core/src/orcia_core/bootstrap/_internal/litellm_adapter.py` | Modifié | Compatibilité du port `LLMGatewayPort` pour `LiteLLMAdapter` en exécution réelle | 85 |
| `packages/orcia-core/src/orcia_core/bootstrap/__init__.py` | Modifié | Ré-export propre de `LiteLLMAdapter` pour la Composition Root (`AD-19`) | 78 |
| `packages/orcia-core/src/orcia_core/rag/two_speed_search.py` | Modifié | Initialisation par défaut de `TwoSpeedFederatedSearchService(candidates=())` à `0` candidat fictif | 150 |
| `apps/web/src/components/ShellContainer.tsx` | Modifié | Suppression de `DEFAULT_SEARCH_HITS` et dérivation dynamique de `speed1Hits` depuis `usePlatformSetup()` | 345 |
| `apps/web/src/components/ontologyFixtures.ts` | Supprimé | Suppression du fichier orphelin contenant des concepts fictifs | 0 |
| `infra/scripts/maintenance/04_backfill_system_bootstrap.py` | Modifié | Purge des utilisateurs fictifs (`karim`, `marc`, `nadia`), de l'unité fictive `Engineering` et du workspace fictif | 175 |
| `tests/unit/test_zero_fictional_data_and_mocks_in_prod.py` | Créé | Suite de tests unitaires vérifiant l'absence totale de données fictives et de mocks par défaut en production | 105 |
| `tests/unit/test_epic_9_story_9_3_two_speed_search.py` | Modifié | Injection explicite de `DEFAULT_SEARCH_CANDIDATES` dans le test du endpoint `/api/v1/search` | 155 |
| `tests/integration/test_real_containers.py` | Modifié | Alignement du test de backfill `04_backfill_system_bootstrap.py` sur le socle système pur (`0` utilisateur fictif) | 380 |

### 3.2 Métriques & Couverture de Tests (`AD-17`)

- **Couche 1 — Tests unitaires Python (`pytest`)** : `test_zero_fictional_data_and_mocks_in_prod.py` + `test_epic_9_story_9_3_two_speed_search.py` (`PASS`, couverture `>= 90%`).
- **Couche 2 — Tests d'intégration (`testcontainers` PostgreSQL 18)** : `test_real_containers.py` vérifiant que `04_backfill_system_bootstrap.py` n'insère que le socle système (`0` utilisateur fictif).
- **Couche 3 — Contrat OpenAPI 3.1 (`0-diff`)** : Aucun écart de schéma OpenAPI.
- **Couche 4 — Tests Frontend (`Vitest`)** : `pnpm turbo run lint typecheck test` (`PASS`).
- **Couche 5 — Architecture & Frontières (`lint-imports` & `lint_spine.py`)** : `5 contracts kept, 0 broken`, `0 findings`.
