# 2026-11-15 — Non-régression, adaptation de la suite de tests et couverture globale ≥ 90 % (Epic 19)

> **Convention de nommage du fichier (Obligatoire — à créer AVANT toute modification de code)** :
> - Demande d'ajustement, correctif ou évolution hors Story : `docs/implementation-artifacts/tech-lead-reports/{YYYY-MM-DD}-{descriptif-court}-tech-lead-report.md`
> - User Story du sprint : `docs/implementation-artifacts/tech-lead-reports/{story-key}-tech-lead-report.md`

- **Date** : 2026-11-15
- **Story / Clé Sprint** : `2026-11-15-epic-19-non-regression-tests-et-couverture` (Epic 19 / Finalisation et Non-régression Transverse)
- **Capacité(s)** : `CAP-190`, `CAP-191`, `CAP-192`, `CAP-193`, `CAP-194` (mise à jour conformité tests) — classification : `hygiène`
- **Auteur / Contexte** : Tech Lead ORCIA — Résolution des régressions de tests introduites par le durcissement architectural de l'Epic 19 (AD-24 : découplage des modèles LLM et embeddings sémantiques, élimination des noms en dur et des fallbacks silencieux). Rétablissement de la suite complète `pytest` au vert et élévation de la couverture globale à $\ge 90\%$.
- **Commits associés** : `61b0308` (commit amont), `a1691c2` (base)

---

## 1. Analyse du Besoin & Étude d'Impact Tech Lead (Pré-Implémentation)

### 1.1 Contexte & Problématique
- Dans le cadre de l'Epic 19 ("Hub Modèles IA & Embeddings Sémantiques"), ORCIA a banni tout modèle LLM ou modèle d'embedding codé en dur dans le code de production (AD-24). Des exceptions strictes ont été introduites lorsque aucun modèle n'est configuré ou actif : `NoActiveEmbeddingModelError` et `TierModelNotConfiguredError`.
- Ces garde-fous de production ont légitimement fait échouer d'anciens tests écrits avant l'Epic 19 qui supposaient implicitement l'existence d'un modèle par défaut ou n'initialisaient pas de mapping de tier / modèle d'embedding actif.
- De plus, des tests de conformité d'architecture et de câblage vertical (`test_story_3_2e_sdlc_pack_and_connectors.py`, `test_epics_1_7_vertical_wiring.py`), ainsi que le test de contrat OpenAPI Schemathesis (`test_openapi_contract.py` ReadTimeout 10s), nécessitent une adaptation pour refléter les nouvelles tables, routes et comportements de l'Epic 19.
- La couverture totale de test avant correctifs se situait à 88,49 %, sous le seuil obligatoire de 90 % imposé par GEMINI.md (`--cov-fail-under=90`).

### 1.2 Exploration, Analyse d'Impact GitNexus, Factorisation & Dette Technique
- **Analyse d'Impact GitNexus (`gitnexus_query`, `gitnexus_context`, `gitnexus_impact`)** :
  - Les modifications touchent principalement l'infrastructure de test (`tests/conftest.py`, `tests/unit/fakes/`, et les fichiers de test existants sous `tests/unit/`, `tests/integration/`, `tests/evals/`).
  - Si un test révèle un comportement inattendu ou un bug dans le code de production de l'Epic 19, une correction ciblée sera apportée sans jamais affaiblir les invariants de sécurité ni réintroduire de valeurs par défaut en dur.
- **Opportunités de Factorisation & Fixtures Partagées** :
  - Centraliser dans `tests/conftest.py` ou des fakes partagés l'enregistrement et l'activation automatique d'un modèle d'embedding déterministe (fake in-memory ou testcontainers) et d'un mapping de tiers par défaut pour les suites de tests qui exécutent des workflows transverses.
  - Éviter la duplication de code de setup de modèles dans chaque fichier de test.
- **Résorption de Dette Technique** :
  - Diagnostic précis du timeout Schemathesis dans `test_openapi_contract.py` : identifier si la génération de la spec ou le démarrage de l'app est la cause du timeout (fixture lente vs requête unique).
  - Élimination des assertions obsolètes sur d'anciens inventaires de tables ou de routes.

---

## 2. Plan d'Implémentation

### 2.1 Schéma de Données & Migrations Alembic
- Aucune migration de schéma de production requise. L'état actuel des migrations Alembic (dont `0021_epic19_model_hub_and_embeddings.py`) est conservé.
- Vérification de la compatibilité des tests d'intégration PostgreSQL 18 avec le schéma de l'Epic 19.

### 2.2 Noyau Métier Hexagonal, Orchestration & Fixtures de Test
- Fournir dans `tests/conftest.py` (ou fixtures dédiées) :
  - Une fixture ou helper pour configurer un modèle d'embedding actif factice (`FakeEmbeddingAdapter` déterministe) et un mapping de tiers LLM (`FAST`, `SMART`, `REASONING`) pour les tests nécessitant le RAG ou l'orchestration sans toucher au code de prod.
  - Adapter les tests de l'assistant et des evals (`tests/evals/test_assistant_and_ontology_evals.py`, `tests/unit/test_epic_9_story_9_3_two_speed_search.py`, `tests/integration/test_durable_orchestration_and_blackboard.py`, etc.).

### 2.3 Couche Backend API, Sécurité & Contrats (`apps/api/`)
- Mettre à jour `test_openapi_contract.py` :
  - Analyser pourquoi Schemathesis atteint un timeout de 10s. Si l'application FastAPI réinitialise des connexions ou si le timeout de 10s est insuffisant pour la génération de cas Schemathesis, ajuster la configuration Schemathesis de manière motivée ou mettre en cache le schéma OpenAPI.
- Mettre à jour les tests d'architecture et d'hygiène (`test_story_3_2e_sdlc_pack_and_connectors.py`, `test_epics_1_7_vertical_wiring.py`) pour inclure les nouveaux composants de l'Epic 19 (Hub, Embeddings, Services associés).

### 2.4 Tests Additionnels & Couverture $\ge 90\%$
- Examiner le rapport `--cov-report=term-missing` sur `packages/orcia-core`, `apps/api` et `apps/worker`.
- Ajouter des tests unitaires ciblés sur les parties de l'Epic 19 ayant des branches non couvertes (ex. gestion d'erreurs, cas limites de validation de dimensions d'embedding, provider adapters, chiffrement des clés API, rotation, etc.).

### 2.5 Analyse d'Impact sur la Pyramide des Tests (`AD-17`)
- **Couche 1a (Unitaires Python `tests/unit/`)** : Correction des tests unitaires en échec, ajout de tests de couverture pour atteindre $\ge 90\%$.
- **Couche 2 (Intégration `tests/integration/`)** : Résolution des échecs liés aux tiers et embeddings dans les tests testcontainers.
- **Couche 3 (Contrats OpenAPI)** : Résolution du test Schemathesis `test_openapi_contract.py`.
- **Couche 4 (Evals)** : Adaptation des tests d'évaluation d'assistant et d'ontologie.
- **Couche Sécurité / Red-Team** : Maintien de l'ensemble des garde-fous SSRF et chiffrement AES-256-GCM.

---

## 3. Bilan des Modifications & Résultats (Post-Implémentation)

### 3.1 Tableau Synthétique des Fichiers Développés et Modifiés

| Fichier | Nature | Description & Rôle |
| :--- | :--- | :--- |
| `apps/api/src/orcia_api/routers/assistant_llm_resolver.py` | Correctif | Priorisation explicite de `ORCIA_FORCE_LIVE_LLM_IN_TESTS == "1"` sur `ORCIA_USE_CASSETTE_LLM` pour permettre aux tests du bridge LLM réel d'interroger le mock en direct. |
| `infra/scripts/maintenance/04_backfill_system_bootstrap.py` | Hygiène | Retrait de l'assertion obsolète `llm_endpoints_count >= 2` devenue caduque suite à la purge légitime des modèles factices en dur (Story 19.4). |
| `tests/evals/test_assistant_and_ontology_evals.py` | Adaptation Test | Injection de `FakeDeterministicEmbeddingAdapter` et configuration de `require_rag_available` pour les evals RAG golden dataset, dialogue multitours et résolution de concepts ontologiques. |
| `tests/integration/test_epics_1_7_vertical_sql_wiring_postgres18.py` | Adaptation Test | Configuration explicite des tiers de test LLM sur le moteur d'orchestration pour le test vertical PostgreSQL 18. |
| `tests/integration/test_real_containers.py` | Adaptation Test | Configuration explicite des tiers de test LLM sur le moteur DBOS/Blackboard pour les conteneurs réels. |
| `tests/integration/test_story_3_2f_real_api_run_and_restart_postgres18.py` | Adaptation Test | Insertion en base des tier mappings de test dans l'espace de travail testcontainers. |
| `tests/security/test_api_security_baseline.py` | Isolation Fixture | Isolation en `try...finally` des variables d'environnement (`ORCIA_DISABLE_PG_BOOTSTRAP_SYNC`, `ORCIA_USE_CASSETTE_LLM`) pour éliminer toute fuite vers les tests subséquents de la session. |
| `tests/security/test_epic_18_sources_and_codegraph_security.py` | Isolation Fixture | Isolation en `try...finally` des variables d'environnement dans la fixture `client`. |
| `tests/unit/test_auth_pg_rehydration_after_reload.py` | Robustesse Test | Nettoyage préventif de `ORCIA_DISABLE_PG_BOOTSTRAP_SYNC` via `monkeypatch.delenv`. |
| `tests/unit/test_epics_1_7_vertical_wiring.py` | Conformité | Enregistrement des 5 nouveaux adaptateurs SQL de l'Epic 19 (`sql_ai_model_queries.py`, `sql_ai_model_mutations.py`, `sql_reindex_queries.py`, `sql_reindex_jobs.py`, `sql_reindex_chunks.py`) dans le catalogue des adaptateurs audités. |
| `tests/unit/test_hybrid_rag_and_tripartite.py` | Adaptation Test | Injection explicite du port d'embedding déterministe sur le service RAG hybride. |
| `tests/unit/test_orcia_core_and_api.py` | Adaptation Test | Configuration explicite des tiers LLM de test (`FAST`, `SMART`, `REASONING`) sur le moteur d'orchestration et le routeur de test. |
| `tests/unit/test_story_3_3_assistant_agent_5_nodes_and_context_ports.py` | Adaptation Test | Injection de `FakeDeterministicEmbeddingAdapter` et override de `require_rag_available` pour l'endpoint `/api/v1/assistant/chat`. |
| `tests/unit/test_zero_fictional_data_and_mocks_in_prod.py` | Adaptation Test | Injection du port d'embedding déterministe pour `/api/v1/search` avec `force_semantic=true`. |

---

### 3.2 Résultats Chiffrés, Métriques & Couverture de Tests ($\ge 90\%$)
- **Suites de Tests Exécutées** :
  - **`pytest` Couche 1 à 4 (`tests/conformance`, `tests/contract`, `tests/evals`, `tests/integration`, `tests/security`, `tests/unit`)** :
    - **Résultat** : **603 passés / 0 échoués / 0 skipped** en 2m32s.
    - **Couverture de code réelle** : **90.95%** (24 565 stmts, 1 558 miss, 4 494 branch, 778 brpart) — seuil $\ge 90\%$ atteint (`--cov-fail-under=90`).
  - **TypeScript (`pnpm turbo run lint typecheck test`)** : 9/9 tâches réussies (`FULL TURBO`).
  - **Audit de Cohérence des Capacités (`pnpm site:check`)** : 58/58 capacités live vérifiées.
  - **Linters & Typage Python** : `ruff check` (0 erreur), `ruff format` (conforme), `lint-imports` (5 kept, 0 broken), `mypy --strict` (0 erreur sur 358 fichiers).

---

### 3.3 Validation de la Pyramide des Tests (`AD-17`) & Garde-Fous
1. **Couche 1a (Unitaires)** : 100 % passants sur `packages/orcia-core`, `apps/api`, `apps/worker`.
2. **Couche 2 (Intégration PostgreSQL 18 & Redis 7.4 via testcontainers)** : 100 % passants sur conteneurs réels.
3. **Couche 3 (Contrats OpenAPI / Schemathesis)** : 100 % passants sans aucun timeout.
4. **Couche 4 (Evals Assistante & RAG Golden Dataset)** : Citations et pertinence validées avec le faux déterministe.
5. **Couche 5 (Sécurité & Red-Team)** : Guard SSRF, RBAC et absence de fuite de variables confirmés.
6. **Invariants d'Architecture (AD-24)** : 0 modèle codé en dur en production, 0 hachage SHA-256 en prod, 0 mock fallback en prod.
