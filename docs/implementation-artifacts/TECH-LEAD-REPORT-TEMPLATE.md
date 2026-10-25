# [Story N.M — Nom de l'Implémentation / Fonctionnalité]

- **Date** : YYYY-MM-DD
- **Story / Clé Sprint** : `{story-key}` (`Epic N`)
- **Auteur / Contexte** : [Contexte métier, objectif principal, problème résolu, exigences `FR-*`, `NFR-*`, `AD-*`, `UX-DR*` couvertes]
- **Commits associés** : `hash1`, `hash2`

---

## 1. Analyse du Besoin & Étude d'Impact Tech Lead (Pré-Implémentation)

### 1.1 Contexte & Problématique
- [Description du problème ou de l'opportunité métier/technique]
- [Comportement attendu vs comportement actuel]
- [Impacts collatéraux ou contraintes spécifiques de `ARCHITECTURE-SPINE.md`]

### 1.2 Exploration, Analyse d'Impact GitNexus, Factorisation & Dette Technique
- **Analyse d'Impact GitNexus (`gitnexus_query`, `gitnexus_context`, `gitnexus_impact`)** :
  - [Symboles existants touchés, appelants directs (`upstream`), processus impactés, niveau de risque]
- **Exploration & Chiffres Clés (Base de Données / Conteneurs / Benchmark)** :
  - [Requêtes SQL / CTE ou scripts exploratoires exécutés]
  - [Volumétries constatées, cas limites identifiés, signaux faibles mesurés]
  - [Conclusions justifiant les choix techniques]
- **Opportunités de Factorisation & Résorption de Dette Technique Naissante** :
  - [Primitives partagées extraites ou réutilisées (`packages/orcia-core`, `packages/api-client`, composants UI)]
  - [Contrôle de volumétrie des fichiers (`> 300–400 lignes`) et découpages effectués]
  - [Tickets de dette technique / refactoring créés : `Story N.Ma` dans `epics.md` ou entrées `action_items` dans `sprint-status.yaml`]

---

## 2. Plan d'Implémentation

### 2.1 Schéma de Données & Migrations Alembic (`infra/migrations/versions/...`, si applicable)
- `infra/migrations/versions/XXXX_nom_migration.py` :
  - Tables, colonnes (`UUIDv7`), types, contraintes d'intégrité et triggers PostgreSQL 18 (ex. *Append-Only* `audit_ledger` / `blackboard_snapshots`).
  - Index B-Tree / GIN (`tsvector`) / HNSW (`pgvector halfvec(1024)`) / partiels créés et justification de performance.
  - Validation de la réversibilité (`upgrade()` et `downgrade()`).

### 2.2 Noyau Métier Hexagonal, Orchestration & Workers (`packages/orcia-core/`, `apps/worker/`, `infra/sandbox/`)
- `packages/orcia-core/<domaine>/...` :
  - Logique algorithmique, complexité (McCabe $\le 10$), structures de données et invariants du domaine (zéro dépendance framework dans `domain/` et `ports/`).
  - Règles d'isolation et garde-fous architecturaux (`AD-1` à `AD-17` : ex. immuabilité `run-lock.json`, ancres humaines `AD-3`, orthogonalité des modèles `AD-10`, sandbox `--unshare-net` `AD-9`).
- `apps/worker/...` :
  - Acteurs Dramatiq, garanties d'idempotence en cas de retry et gestion des erreurs.

### 2.3 Couche Backend API, Sécurité & Contrats (`apps/api/`, `packages/api-client/`)
- `apps/api/repositories/...` & `apps/api/services/...` :
  - Nouvelles fonctions, CTE récursives (`WITH RECURSIVE`), requêtes d'agrégation (zéro requête `N+1`), filtres multi-niveaux (`GLOBAL | BU | TEAM | WORKSPACE`), pagination et transaction `Unit of Work`.
- `apps/api/routers/...` & `apps/api/dependencies/...` :
  - Endpoints FastAPI exposés, gardes RBAC/ABAC (`RunAccessGuard`, rejet `HTTP 403` en mode `READ_ONLY_OBSERVER`), schémas Pydantic v2, enveloppes d'erreur **RFC 9457 Problem Details** et corrélation `trace_id` OpenTelemetry (`structlog`).
- `packages/api-client/` :
  - Régénération du SDK TypeScript via `openapi-typescript` (`0-diff` vérifié).

### 2.4 Interface Utilisateur & Expérience (`apps/web/`)
- Routes Next.js App Router (`apps/web/src/app/...`) et composants React 19 / `shadcn/ui` créés ou modifiés.
- Respect des Design Tokens Direction C (`DESIGN.md` — zéro hexadécimal en dur, exclusivité du violet `#6D28D9` pour `human-led-anchor-card`).
- Éléments interactifs : flux SSE temps réel (`< 500 ms`), graphe `@xyflow/react`, filtres, tris, badges (`uri-badge`, `presence-claim-pill`), palette `⌘K`, sélecteur de périmètre `⌘W`, gestion responsive 3 breakpoints (Desktop, Laptop, Mobile Companion) et conformité WCAG 2.2 AA (`aria-live="polite"`, Couleur + Icône + Libellé en français).

---

## 3. Bilan des Modifications & Résultats (Post-Implémentation)

### 3.1 Fichiers Développés & Modifiés
| Fichier | Nature (Création / Modification / Refactoring) | Description synthétique |
| :--- | :--- | :--- |
| `infra/migrations/...` | Création | ... |
| `packages/orcia-core/...` | Création / Modification | ... |
| `apps/api/...` | Création / Modification | ... |
| `apps/web/...` | Création / Modification | ... |

### 3.2 Résultats Chiffrés, Métriques & Qualité
- **Couverture de tests** : [Couverture unitaire `pytest` / `Vitest` obtenue ($\ge 90\%$ requis)]
- **Performances mesurées** : [Temps d'exécution des requêtes CTE (`< 15 ms`), RAG hybride (`< 50 ms`), diffusion SSE (`< 500 ms`), bascule UI (`< 1 s`)]
- **Qualité statique & Architecture** :
  - `ruff check` & `ruff format --check` : `0 warning`
  - `mypy --strict` & `pnpm typecheck` : `0 error`
  - `lint_spine.py` : `ok: true, 0 findings`
  - `gitnexus_detect_changes()` : [Périmètre vérifié et conforme]

### 3.3 Validation & Procédure de Test (5 Couches `AD-17`)
- **Couche 1 — Tests Unitaires & Propriétés (`pytest` + `hypothesis`, `Vitest`)** : [Détail des invariants testés]
- **Couche 2 — Tests d'Intégration (`testcontainers-python` : PostgreSQL 18 + `pgvector`, Redis 7.4, MinIO)** : [Vérification d'intégrité des données, triggers, verrous]
- **Couche 3 — Tests de Contrat API (`openapi-typescript` 0-diff + `Schemathesis`)** : [Validation des schémas et codes RFC 9457]
- **Couche 4 — Tests d'Orchestration IA (`DeterministicCassetteLLM`)** : [Validation déterministe des flux d'agents et Gates]
- **Couche 5 — Tests E2E & Accessibilité (`@playwright/test` Desktop `1440x900` & Mobile `390x844`)** : [Scénarios utilisateurs et cas limites validés]
