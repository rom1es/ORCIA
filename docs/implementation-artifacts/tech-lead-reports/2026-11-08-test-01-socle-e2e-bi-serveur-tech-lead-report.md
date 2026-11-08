# 2026-11-08 — TEST-01 : socle E2E bi-serveur Playwright (FastAPI + Vite + PG18/Redis éphémères)

- **Date** : 2026-11-08
- **Story / Clé Sprint** : `2026-11-08-test-01-socle-e2e-bi-serveur` (`Ajustement Transverse` — tests, `Epic 13`, ticket `TEST-01`)
- **Capacité(s)** : `none (hygiène/NFR)` — classification `hygiène` ; débloque la promotion `docs → runtime` des capacités (`CAP-ACT-5`, `TEST-04..06`)
- **Auteur / Contexte** : audit pyramide `AD-17` : un seul `webServer` (Vite) dans `apps/web/playwright.config.ts`, aucun backend ni PostgreSQL 18 → aucun vrai parcours `Navigateur → Vite → api-client → FastAPI → PG18`.
- **Branche dédiée** : `test/e2e-bi-server-foundation`
- **Commits associés** : à renseigner.

---

## 1. Analyse du Besoin & Étude d'Impact Tech Lead (Pré-Implémentation)

### 1.1 Contexte & Problématique
- Le proxy Vite (`/api` → `ORCIA_API_HOST:ORCIA_API_PORT`, défaut `127.0.0.1:8000`) existe déjà ; il manque le serveur FastAPI et une base dédiée.
- **Risque critique** : `infra/scripts/maintenance/09_reset_db_first_boot.py --apply` vide les tables mutables de la base résolue par `resolve_database_url()`. Lancé avec le `.env` de développement (`POSTGRES_PORT=5433`), il **effacerait la base de dev**. Le socle doit donc : (a) ne jamais lire le `.env` de dev (`ORCIA_ENV_FILE` vers un fichier inexistant — `load_orcia_env` ne charge rien et l'environnement explicite prime, `override=False`), (b) refuser tout reset si l'URL n'est pas celle d'une base E2E éphémère (garde-fou testé).
- Les ports de dev (API `8000`, web `3100`, PG `5433`, Redis `6380`) sont occupés par l'environnement local : le socle utilise des ports dédiés (API `8100`, web `3101`) et des ports de conteneurs aléatoires.
- Le parallélisme Playwright (`fullyParallel`) est incompatible avec une base partagée remise à zéro : `workers: 1`.

### 1.2 Exploration, Impact GitNexus, Factorisation & Dette
- **GitNexus** : aucun symbole `orcia_core` / `orcia_api` / `apps/web` modifié (outillage `infra/` + config Playwright + specs) → impact applicatif nul.
- **Factorisation** : réutilisation de `resolve_database_url`, de l'`alembic.ini` existant, de `09_reset_db_first_boot.py` (appelé tel quel) et de `DeterministicCassetteLLM` via `ORCIA_USE_CASSETTE_LLM=true` ; images identiques à `tests/integration/` (`pgvector/pgvector:pg18`, `redis:7.4-alpine`).
- **Logique pure testable** (TDD) isolée dans `infra/scripts/e2e/e2e_stack_config.py` : construction de l'environnement isolé, garde-fou de sécurité, fichier d'état ; l'orchestration (conteneurs, uvicorn) dans `e2e_stack.py`.
- **Volumétrie** : chaque fichier < 200 lignes.
- **Dette / tickets** : intégration CI de `pnpm e2e` — aucun `.github/workflows` dans le dépôt → ajouté à `TEST-01b` (open) ; `TEST-02` (shell.spec obsolète) reste séparé.

---

## 2. Plan d'Implémentation

### 2.1 Alembic — aucune nouvelle migration ; `alembic upgrade head` exécuté sur la base éphémère.
### 2.2 Noyau hexagonal & workers — non applicable.
### 2.3 Outillage
- `infra/scripts/e2e/e2e_stack_config.py` : `build_api_env`, `is_isolated_e2e_database_url`, `write_state`/`read_state`.
- `infra/scripts/e2e/e2e_stack.py` : démarre PG18 + Redis (testcontainers), migre, écrit l'état, lance `uvicorn orcia_api.main:create_app --factory` sur `127.0.0.1:8100`, nettoie à `SIGTERM`/`SIGINT`.
- `infra/scripts/e2e/reset_day0.py` : lit l'état, refuse si base non isolée, exécute `09_reset_db_first_boot.py --apply` avec l'environnement isolé.
- Tests : `tests/unit/test_e2e_stack_config.py` (rouge → vert).
### 2.4 Interface / E2E
- `apps/web/playwright.config.ts` : `webServer: [API stack, Vite]`, ports dédiés, `reuseExistingServer: false`, `workers: 1`, timeout 180 s.
- `apps/web/e2e/support/day0.ts` : `resetDay0()` (appelle `reset_day0.py`).
- `apps/web/e2e/00-stack-smoke.spec.ts` : santé de l'API via le proxy Vite + modale Jour 0 après reset.
- `.gitignore` : fichier d'état `.orcia-run/` déjà ignoré (utilisé).

---

## 3. Bilan des Modifications & Résultats (Post-Implémentation)

### 3.1 Fichiers
| Fichier | Nature | Description |
| :--- | :--- | :--- |
| `infra/scripts/e2e/e2e_stack_config.py` | Création | Environnement isolé (`.env` de dev jamais lu, cassette LLM, secrets de test), garde-fou `is_isolated_e2e_database_url`, fichier d'état |
| `infra/scripts/e2e/e2e_stack.py` | Création | PG18 `pgvector` + Redis 7.4 éphémères (testcontainers), `alembic upgrade head`, FastAPI `:8100`, teardown sur SIGTERM |
| `infra/scripts/e2e/reset_day0.py` | Création | Reset Jour 0 via `09_reset_db_first_boot.py --apply`, refusé hors base E2E |
| `apps/web/playwright.config.ts` | Modification | `webServer[]` (stack + Vite `:3101`), `workers: 1`, `reuseExistingServer: false`, `gracefulShutdown: SIGTERM` |
| `apps/web/e2e/support/day0.ts` | Création | Helper `resetDay0()` |
| `apps/web/e2e/00-stack-smoke.spec.ts` | Création | Santé API via proxy Vite + modale Jour 0 après reset |
| `tests/unit/test_e2e_stack_config.py` | Création | 10 tests (TDD rouge → vert) |

### 3.2 Résultats
- `pnpm e2e` : 4/4 specs de fumée vertes (`desktop-cockpit` + `mobile-companion`), ~28 s ; `pytest` 10/10 ; `ruff` et `mypy --strict` verts.
- **Isolation vérifiée** : base `orcia_e2e` sur port aléatoire ; conteneurs et fichier d'état supprimés après le run ; la base de dev (`orcia-postgres:5433`) n'est jamais touchée.
- **Incident corrigé** : sans `gracefulShutdown`, Playwright tue la pile en SIGKILL → conteneurs et état orphelins ; corrigé (SIGTERM, 30 s) et reverifié.
- **Hors périmètre** : `e2e/shell.spec.ts` (obsolète, sélecteurs pré-Epic 12) échoue toujours → `TEST-02` ; CI (aucun `.github/workflows`) → `TEST-01b`.
- `gitnexus_detect_changes` non exécuté (aucun symbole applicatif touché) ; couverture 90 % non applicable (outillage `infra/`).
