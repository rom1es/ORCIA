# 2026-11-08 — TEST-01b : workflow CI GitHub Actions pour `pnpm e2e`

- **Date** : 2026-11-08
- **Story / Clé Sprint** : `2026-11-08-test-01b-workflow-ci-e2e` (`Ajustement Transverse` — tests/CI, `Epic 13`, ticket `TEST-01b`)
- **Capacité(s)** : `none (hygiène/NFR)` — classification `hygiène`
- **Branche dédiée** : `test/e2e-coverage-plan`

---

## 1. Analyse du Besoin & Étude d'Impact Tech Lead (Pré-Implémentation)
- Aucun `.github/workflows` dans le dépôt : la suite E2E (`TEST-01…06`) ne tournait que localement.
- La pile E2E démarre ses conteneurs via testcontainers (`infra/scripts/e2e/e2e_stack.py`) : le runner doit fournir Docker (`ubuntu-latest` le fournit).
- Impact GitNexus : nul (fichier CI). Aucun code applicatif touché.

## 2. Plan d'Implémentation
- `.github/workflows/e2e.yml` : checkout, `uv sync --all-packages --extra dev` (crée `.venv/` attendu par la pile), pnpm/Node 22, `playwright install --with-deps chromium`, pré-chargement `pgvector/pgvector:pg18` + `redis:7.4-alpine`, `pnpm e2e`, upload `playwright-report` / `test-results`.

## 3. Bilan des Modifications & Résultats (Post-Implémentation)
- Fichier créé, YAML valide (`yaml.safe_load`).
- **Non vérifié en conditions réelles** : un workflow GitHub Actions ne peut pas être exécuté depuis cet environnement ; première exécution à observer sur la prochaine PR (risques : `uv sync` sans l'extra attendu, durée > 30 min, `--with-deps`). Ticket laissé en `review`.
- Autres jobs (lint, pytest, `site:check`) non inclus — hors périmètre du ticket.
