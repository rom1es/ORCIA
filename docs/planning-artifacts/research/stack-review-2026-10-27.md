# ORCIA : réévaluation de la stack technique (27/10/2026)

> Document d'entrée pour `bmad-architecture` et `bmad-correct-course`. Il complète [modularity-analysis-2026-10-27.md](./modularity-analysis-2026-10-27.md).

## 1. Écarts entre la spine et le code

| # | Constat | Preuve |
|---|---|---|
| E1 | Aucun adaptateur d'infrastructure réel : aucun import de `sqlalchemy`, `asyncpg`, `litellm`, `docling`, `wasmtime` ni `opentelemetry` dans `packages/` et `apps/` | Recherche des imports ; `ports/llm_port.py` ne définit que le port |
| E2 | Logique métier stockée en mémoire : environ 39 stockages `InMemory…` ou dictionnaires dans `orcia-core` | `packages/orcia-core/src` |
| E3 | 3 singletons créés au chargement des modules dans `apps/api` | `routers/orchestration.py:L39` (`_DEFAULT_ORCHESTRATION_SERVICE`) |
| E4 | Les 10 migrations Alembic existent, mais aucune couche d'accès aux données ne les utilise | `infra/migrations/versions/0001…0010` |
| E5 | Versions qui ont dérivé. Spine : Next `16.4.0`, Vitest `5.0.5`, Playwright `1.64.1`. `apps/web/package.json` : `^15.2`, `^3`, `^1.51`. `pyproject` : versions minimales basses (`fastapi>=0.115`, `dramatiq>=1.17`, `pydantic>=2.9`) | `package.json`, `pyproject.toml` |
| E6 | TanStack Query, Tailwind, `@xyflow/react` et `openapi-fetch` sont absents de `apps/web/package.json` | `apps/web/package.json` |
| E7 | La spine annonce un workspace `uv 0.13.5`. Le dépôt utilise un seul `pyproject` setuptools pour le noyau, l'API et le worker. La règle hexagonale n'est vérifiée par aucun outil. | `pyproject.toml` |
| E8 | OpenTelemetry n'est pas instrumenté | Recherche des imports |

Avancement : 16 stories terminées sur 39. Les engagements chiffrés (SSE < 500 ms, sandbox < 5 s, cache < 50 ms) n'ont jamais été vérifiés sur une intégration réelle.

## 2. Évaluation couche par couche

| Couche | Verdict | Point clé |
|---|---|---|
| Monorepo TS + Python, contrat OpenAPI (AD-1) | ✅ Garder | Frontières à faire vérifier par l'outillage |
| FastAPI + Pydantic v2 + noyau hexagonal | ✅ Garder | Aucun outil ne fait respecter la règle |
| **Dramatiq + moteur d'exécution durable maison (AD-2, AD-13, AD-18)** | 🔴 À réévaluer | Attentes de plusieurs semaines, minuteries, cron, webhooks sans doublon, sous-workflows ≤ 3, reprise : tout est réimplémenté à la main |
| PostgreSQL 18 + pgvector `halfvec` | ✅ Garder | Pas de BM25 natif ; coût des requêtes récursives pour le graphe tripartite |
| Redis 7.4 | 🟡 Garder | Peut devenir superflu selon le moteur durable retenu |
| **MinIO** | 🟠 À réévaluer | Évolution de l'édition communautaire depuis 2025, licence AGPL (à vérifier) |
| LiteLLM | 🟡 Garder derrière le port | Dépendance lourde qui évolue vite ; risque côté chaîne d'approvisionnement ; épingler la version |
| Docling | 🟡 Garder | Lourd : worker et file dédiés |
| **Sandbox Wasmtime + bubblewrap (AD-9)** | 🟠 Simplifier | Deux mécanismes ; *user namespaces* souvent désactivés sous Kubernetes ; compilateurs incompatibles avec WASM ; 5 s irréaliste |
| Next.js App Router | 🟡 Garder, côté client surtout | Risque de double backend avec FastAPI (voir la recherche `technical-frontend-spa-nextjs-vs-vite-tanstack-rou-2026-10-27`) |
| Tailwind 4, shadcn/Radix, xyflow, TanStack Query, Zustand | ✅ Garder | — |
| Tests en 5 couches (AD-17) | ✅ Garder | Prioriser les tests d'intégration |

## 3. Préconisations

| ID | Préconisation | AD concernés |
|---|---|---|
| **P1** | Squelette de bout en bout : adaptateurs SQLAlchemy et asyncpg réels, injection des services par FastAPI (`lifespan` et `Depends`) à la place des singletons, adaptateurs LiteLLM et cassette, un run persisté puis repris après redémarrage (proposé en `Story 3.1a`) | AD-1, AD-2 |
| **P2** | Comparer des moteurs d'exécution durable au moteur maison : DBOS, Temporal, Hatchet. Critères : AD-2, AD-13 et AD-18, compatibilité avec le Blackboard en ajout seul, relance à partir d'une étape (FR-16), versions figées, coût d'exploitation, licence, testabilité | AD-2, AD-13, AD-18 |
| **P3** | Réaligner les versions : workspace `uv` avec `uv.lock`, versions minimales égales à la spine, montée des versions du front, Renovate aligné sur la spine | Tableau des versions |
| **P4** | Faire respecter la règle hexagonale par l'outillage : un package `uv` par couche et `import-linter` en CI | AD-1, AGENTS.md |
| **P5** | Sandbox : WASM pour les règles déterministes ; conteneur isolé (gVisor ou Firecracker) ou binaire Rust séparé pour les linters et les tests ; un budget par type de contrôle | AD-9 |
| **P6** | Stockage objet : vérifier l'état de MinIO et choisir une alternative (SeaweedFS, Garage, S3) | Tableau des versions |
| **P7** | BM25 : choisir explicitement entre ParadeDB `pg_search` et `tsvector` | AD-8 |
| **P8** | Rôle de Next.js : simple interface sans backend propre, ou BFF ; ajouter les bibliothèques manquantes dans l'Epic UI | AD-1 |
| **P9** | Instrumentation OpenTelemetry (API et worker) dès P1 | AD-12, conventions |

## 4. Rust (option)
- **Candidats pertinents** : le sandbox-runner (binaire séparé intégrant Wasmtime, avec seccomp/landlock) et le moteur d'autorisations **Cedar** (moteur Rust existant, avec liaisons Python), à la place de `permissions/evaluator.py`.
- **Non pertinent** : API, orchestration, ontologie, RAG, empreintes CAS.
- **Règles** : mesurer d'abord, toujours derrière un port, de préférence en processus séparé (MCP ou gRPC).
