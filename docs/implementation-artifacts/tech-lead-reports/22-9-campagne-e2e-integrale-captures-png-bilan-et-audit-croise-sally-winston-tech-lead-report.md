# Story 22.9 — Campagne E2E Intégrale Vérité PostgreSQL 18, Captures PNG Finales (Succès & Échecs), Bilan & Audit Croisé Sally × Winston

> **Convention de nommage du fichier (Obligatoire — à créer AVANT toute modification de code)** :
> - User Story du sprint : `docs/implementation-artifacts/tech-lead-reports/{story-key}-tech-lead-report.md`

- **Date** : 2026-11-18
- **Story / Clé Sprint** : `22-9-campagne-e2e-integrale-captures-png-bilan-et-audit-croise-sally-winston` (`Epic 22` — Vague 4 / Campagne Intégrale & Audit Croisé)
- **Capacité(s)** : Vérification runtime réelle de `100 %` des `65` capacités (`62` `feature` + `3` `foundation`, `CAP-001`..`CAP-203`) dans `docs/product/capabilities.yaml` — classification : `hygiène`
- **Auteur / Contexte** : `22.0-init` (Pré-implémentation Story 22.9, mise à jour suite ajout Story `22.8a`) — Exécution de la campagne Playwright complète post-remédiation Epic 22 (`22.1`..`22.8` + `22.8a`) sans retry ni maquillage (`--retries=0 --max-failures=0 --timeout=35000`) et avec purge `ORCIA_E2E_SEED_FIXTURES` + relecture à froid PG18 (`reloadColdFromPg`), archivage des captures PNG dans `docs/implementation-artifacts/e2e-campaign-epic-22/`, rédaction du bilan factuel, audit croisé **Sally (UX) × Winston (Architecture)** et mise à jour honnête de `docs/product/capabilities.yaml` (`AD-17`, `NFR-TEST-1`, `GEMINI.md` §5).
- **Commits associés** : `En attente d'implémentation (initialisé en 22.0)`

---

## 1. Analyse du Besoin & Étude d'Impact Tech Lead (Pré-Implémentation)

### 1.1 Contexte & Problématique
- **Séparation propre entre outillage CI (`22.8`), assainissement Fail-Closed & CI (`22.8a`), et exécution de campagne / audit (`22.9`)** :
  - À l'issue des Stories `22.8` et `22.8a`, les `5` gardes CI initiales + les `4` verrous anti-faux-positifs (sync `data-testid`, `typedApiRequest.ts`, purge `ORCIA_E2E_SEED_FIXTURES` + `reloadColdFromPg` via `/api/v1/_e2e/evict-memory-caches`, réécriture `<RouterProvider>` de `zero-dead-buttons` + sonde `[role="alert"]`) sont actifs, `vitest.setup.ts` est assaini *Fail-Closed* contre `openapi.json`, le Composition Root `create_app()` est vérifié sans `dependency_overrides` sur PG18 réel, les `55` blocs `test(...)` (`110` scénarios Desktop `1440×900` et Mobile `390×844`) disposent d'assertions `SELECT` PostgreSQL 18 effectives (`test_e2e_sql_coverage_audit.py`), et `apps/web/e2e/support/e2eCaptureFixture.ts` supporte `ORCIA_E2E_CAMPAIGN_DIR`.
  - Il faut maintenant exécuter la **campagne intégrale sans retry ni arrêt anticipé** sur pile réelle (`PostgreSQL 18 + pgvector`, `Redis 7.4`, Alembic `head`, FastAPI + cassette LLM `0 $`, SPA Vite) et diriger toutes les sorties vers un répertoire neuf **`docs/implementation-artifacts/e2e-campaign-epic-22/`** afin de préserver intégralement les preuves historiques de `e2e-campaign-epic-21/`.
- **Vérité absolue sans maquillage ni angle mort** :
  - Aucun `test.skip` ou `test.fixme` destiné à masquer un échec ne doit subsister.
  - Les captures PNG d'état final doivent être produites pour **100 % des scénarios exécutés (succès comme échecs)**, accompagnées de `manifest.jsonl` et `playwright-results.json`.
  - L'audit visuel de **Sally (UX/UI Direction C)** et l'audit architectural de **Winston (`AD-1..AD-24`)** doivent inspecter non seulement les échecs éventuels mais aussi les captures `PASSED` pour détecter toute dégradation résiduelle ou opportunité d'amélioration.
  - `docs/product/capabilities.yaml` ne doit promouvoir à `verification: runtime` que les capacités dont **100 % des specs associées ont réussi** ; toute capacité encore touchée par un échec reste/passe honnêtement à `verification: failed_e2e`.

### 1.2 Exploration, Analyse d'Impact GitNexus, Factorisation & Dette Technique
- **Composants du harnais et du registre impactés** :
  - `apps/web/e2e/support/e2eCaptureFixture.ts` : piloté par `ORCIA_E2E_CAMPAIGN_DIR=docs/implementation-artifacts/e2e-campaign-epic-22` (écriture de `manifest.jsonl` et `screenshots/<spec>/<project>--<test>--<status>.png`).
  - `infra/scripts/uj_e2e_coverage.py` (`PLAYWRIGHT_RESULTS_PATH`, `load_failed_e2e_specs`, `check_uj_e2e_coverage`) : vérifie la cohérence entre `playwright-results.json` et `docs/product/capabilities.yaml` lors de `pnpm site:check`.
  - `docs/implementation-artifacts/e2e-campaign-epic-21/*` : conservé intact comme base comparative (évolution `47 passed / 47 failed+timedOut` $\rightarrow$ bilan Epic 22).
- **Contraintes de volumétrie & hygiène** :
  - Aucun changement de code métier applicatif dans `Story 22.9` (sauf mise à jour éventuelle du chemin `PLAYWRIGHT_RESULTS_PATH` dans `uj_e2e_coverage.py` pour pointer sur `e2e-campaign-epic-22/playwright-results.json` et mise à jour de `capabilities.yaml` + synchronisation vitrine).
  - Les correctifs pour tout échec ou amélioration découvert pendant `22.9` sont planifiés et cadrés dans `Story 22.10` (`Epic 23`), sans bricolage hors périmètre.

---

## 2. Plan d'Implémentation

### 2.1 Schéma de Données & Migrations Alembic (`infra/migrations/versions/`)
- Aucune migration Alembic dans `Story 22.9`. Avant le lancement de la campagne E2E, la base éphémère `orcia_e2e` est réinitialisée proprement (`alembic upgrade head` + état Jour 0 à `0` utilisateur).

### 2.2 Noyau Métier Hexagonal, Orchestration & Workers (`packages/orcia-core/`, `apps/worker/`)
- Aucune modification de code métier dans `Story 22.9`. Les éventuelles violations `AD-1`..`AD-24`, fuites RAM, incohérences d'événements Outbox ou erreurs SQL observées durant la campagne sont consignées dans `notes-audit-winston-architecture.md` et `synthese-remediation-sally-winston-epic-22.md`.

### 2.3 Couche Backend API, Sécurité & Contrats (`apps/api/`, `packages/api-client/`)
- Aucune modification d'endpoint dans `Story 22.9`. Le serveur FastAPI est lancé avec la configuration PG18/Redis réelle et les traces logs/erreurs HTTP (`4xx`/`5xx`) sont exploitées dans `bilan-execution-tests-e2e-epic-22.md` et `notes-audit-winston-architecture.md`.

### 2.4 Livrables Campagne E2E, Audit Croisé & Registre (`docs/`, `infra/scripts/`)
1. **Exécution Playwright intégrale (`ORCIA_E2E_CAMPAIGN_DIR=docs/implementation-artifacts/e2e-campaign-epic-22`)** :
   - Lancement des `24` specs (`00..21` + `shell.spec.ts`) sur `desktop-cockpit` (`1440×900`) et `mobile-companion` (`390×844`) avec `--retries=0 --max-failures=0 --timeout=35000` et reporter JSON vers `docs/implementation-artifacts/e2e-campaign-epic-22/playwright-results.json`.
   - Archivage de `manifest.jsonl` (`110` entrées) et de toutes les captures PNG sous `docs/implementation-artifacts/e2e-campaign-epic-22/screenshots/**/*.png`.
2. **Bilan Factuel & Audit Croisé Sally × Winston** :
   - `docs/implementation-artifacts/e2e-campaign-epic-22/bilan-execution-tests-e2e-epic-22.md` : inventaire chiffré exact (`passed`, `failed`, `timedOut`, `skipped`), comparaison avec Epic 21, matrice `CAP ↔ UJ ↔ Spec ↔ UI/F5/SQL`, causes racines des éventuels échecs résiduels et liens vers captures.
   - `docs/implementation-artifacts/e2e-campaign-epic-22/notes-audit-sally-ux.md` : revue visuelle complète des captures Desktop et Mobile (Direction C, contrastes WCAG, surcharge, lisibilité, langue FR).
   - `docs/implementation-artifacts/e2e-campaign-epic-22/notes-audit-winston-architecture.md` : revue architecturale (`AD-1`..`AD-24`, SQL PG18, latences, contrat API).
   - `docs/implementation-artifacts/e2e-campaign-epic-22/synthese-remediation-sally-winston-epic-22.md` : table de synthèse priorisée (`P0`..`P3`) de tous les échecs résiduels et améliorations recommandées pour l'Epic 23.
3. **Vérité Registre & Vitrine** :
   - Mise à jour de `infra/scripts/uj_e2e_coverage.py` (`PLAYWRIGHT_RESULTS_PATH`) si nécessaire pour pointer sur la campagne Epic 22.
   - Mise à jour honnête de `docs/product/capabilities.yaml` (`verification: runtime` pour les capacités 100 % vertes ; `verification: failed_e2e` pour toute capacité encore en échec).
   - Exécution de `pnpm site:sync && pnpm site:check`.

### 2.5 Analyse d'Impact sur la Pyramide des Tests (`AD-17`)
- **Couche 1a (`pytest`)** : `.venv/bin/pytest tests/unit/test_uj_e2e_coverage_gate.py tests/unit/test_capabilities_registry.py` — validation de la cohérence stricte `capabilities.yaml` ↔ `playwright-results.json` ↔ `prd.md`.
- **Couche 3 / Vitrine** : `pnpm site:sync && pnpm site:check` — validation `0` erreur sur les `65` capacités, `20/20` UJ, routes SPA et routeurs FastAPI.
- **Couche 5 (Playwright E2E)** : Exécution intégrale des `110` scénarios (`24` specs) sur pile PG18 + Redis 7.4 sans retry ni maquillage.

---

## 3. Bilan des Modifications & Résultats (Post-Implémentation)

> *[En attente d'implémentation de la Story 22.9]*

### 3.1 Fichiers Développés & Modifiés
| Fichier | Nature (Création / Modification / Refactoring) | Description synthétique |
| :--- | :--- | :--- |
| `docs/implementation-artifacts/e2e-campaign-epic-22/playwright-results.json` | Création | *[À compléter après campagne E2E Epic 22]* |
| `docs/implementation-artifacts/e2e-campaign-epic-22/manifest.jsonl` | Création | *[À compléter après campagne E2E Epic 22]* |
| `docs/implementation-artifacts/e2e-campaign-epic-22/screenshots/**/*.png` | Création | *[À compléter après campagne E2E Epic 22]* |
| `docs/implementation-artifacts/e2e-campaign-epic-22/bilan-execution-tests-e2e-epic-22.md` | Création | *[À compléter après campagne E2E Epic 22]* |
| `docs/implementation-artifacts/e2e-campaign-epic-22/notes-audit-sally-ux.md` | Création | *[À compléter après audit Sally]* |
| `docs/implementation-artifacts/e2e-campaign-epic-22/notes-audit-winston-architecture.md` | Création | *[À compléter après audit Winston]* |
| `docs/implementation-artifacts/e2e-campaign-epic-22/synthese-remediation-sally-winston-epic-22.md` | Création | *[À compléter après synthèse croisée]* |
| `docs/product/capabilities.yaml` | Modification | *[À compléter après mise à jour honnête post-campagne]* |

### 3.2 Résultats Chiffrés, Métriques & Qualité
- **Campagne E2E Epic 22 (`playwright-results.json` & `manifest.jsonl`)** : *[À compléter : `passed` / `failed` / `timedOut` / `skipped`, `110` captures PNG]*
- **Registre `docs/product/capabilities.yaml`** : *[À compléter : répartition `runtime` vs `failed_e2e`]*
- **Qualité statique & Architecture** : `pnpm site:sync && pnpm site:check`, `pytest` registre/UJ, `gitnexus_detect_changes()` *[À compléter]*

### 3.3 Validation & Procédure de Test sur Toute la Pyramide (`AD-17`)
- *[À compléter après exécution intégrale de la campagne E2E Epic 22 et audits Sally × Winston]*
