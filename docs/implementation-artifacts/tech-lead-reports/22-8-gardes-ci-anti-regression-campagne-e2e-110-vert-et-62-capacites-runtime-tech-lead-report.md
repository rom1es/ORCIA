# Story 22.8 — Activation des 5 Gardes CI Anti-Régression, Campagne E2E `110/110` Vert sous `< 35s` & Passage `62/62` `verification: runtime`

> **Convention de nommage du fichier (Obligatoire — à créer AVANT toute modification de code)** :
> - User Story du sprint : `docs/implementation-artifacts/tech-lead-reports/{story-key}-tech-lead-report.md`

- **Date** : 2026-11-18
- **Story / Clé Sprint** : `22-8-gardes-ci-anti-regression-campagne-e2e-110-vert-et-62-capacites-runtime` (`Epic 22` — Vague 3 / Clôture)
- **Capacité(s)** : `CAP-100` (hygiène CI transverse) & promotion finale **`62/62` `feature` (`CAP-001`..`CAP-203`) à `verification: runtime`** dans `docs/product/capabilities.yaml` — classification : `hygiène`
- **Auteur / Contexte** : `bmad-architect-worker` (initialisation pré-implémentation Story 21.9) — Résolution des chantiers **`REM-33`** et **`REM-34`** (`synthese-remediation-sally-winston-epic-21.md`, `notes-audit-winston-architecture.md` § 3.5). Couvre `AD-17`, `NFR-TEST-1`, `NFR-PERF-1`, `NFR-A11Y-1`, `GEMINI.md` §5.
- **Commits associés** : `En attente d'implémentation (initialisé sur 575cf4a)`

---

## 1. Analyse du Besoin & Étude d'Impact Tech Lead (Pré-Implémentation)

### 1.1 Contexte & Problématique
- **Budget temps E2E sur parcours multi-étapes (`REM-33`)** :
  - `14-auth` #2 (Desktop + Mobile) et `16-ai-models` #2 (Desktop) atteignaient le plafond `35 000 ms` principalement à cause de l'obstruction Zone 4 sur `UserSettingsModalDialog` et de séquences d'attentes cumulées. Après `REM-03` (`22-2`), il faut re-mesurer et optimiser les parcours sous `< 35 s` avec marge confortable (`< 20 s` visé).
- **Absence des 5 gardes automatisées anti-régression (`REM-34`)** :
  - L'audit Epic 21 a montré que plusieurs défauts majeurs (`PASSED` faussement verts) passaient la CI actuelle :
    1. Fuites de jargon technique dans les dictionnaires `i18n`, `_contextualHelpSections.ts` et `docs/help/`.
    2. Montage toxique de panneaux cachés via `style={{ display: "none" }}` (permettant à `zero-dead-buttons` de rester vert malgré des écrans vides/dupliqués).
    3. Utilisation de classes Tailwind v4 non compilées (`tokens.css` sans `@tailwindcss/vite`).
    4. Fuites de balises internes `[LAYER_5_*]` dans les schémas/streams UI et maintien du drapeau `ORCIA_DISABLE_PG_BOOTSTRAP_SYNC`.
    5. Débordements mobiles masqués par `overflow-x: hidden` sur `html/body` (faux positifs `scrollWidth <= innerWidth` sur `05-mobile-companion` et `12-finops`) et superposition de Zone 4 sur les modales.
- **Critère de sortie de l'Epic 22** :
  - Exécuter l'intégralité de la campagne Playwright (`--retries=0 --max-failures=0 --timeout=35000`) avec **`0` échec (`unexpected: 0`, `flaky: 0`, `110/110` scénarios nominaux + captures PNG vérifiées)**, puis promouvoir **100 % des `62` capacités `feature`** (`CAP-001`..`CAP-203`) à `verification: runtime` (`0` `e2e_remediation_ref` résiduel) sous contrôle bloquant `pnpm site:sync && pnpm site:check`.

### 1.2 Exploration, Analyse d'Impact GitNexus, Factorisation & Dette Technique
- **Périmètre des 5 Gardes CI** :
  1. `apps/web/src/__tests__/anti-jargon-and-secrets-ui-audit.test.ts` (scan `i18n/locales/*.ts`, `_contextualHelpSections.ts`, `packages/ui/src/**`, `docs/help/**/*.md`, `packs/**/help/**/*.md`).
  2. `apps/web/src/__tests__/no-hidden-legacy-panels-audit.test.ts` (interdiction `display: none` / `className="hidden"` sur panneaux métier + vérification que chaque `role="dialog"` passe par `Portal`).
  3. `apps/web/src/__tests__/css-class-integrity-audit.test.ts` (vérification `@tailwindcss/vite` + cohérence classes `tokens.css`).
  4. `tests/unit/test_no_raw_enum_codes_in_ui_streams.py` (zéro `[LAYER_5_*]` ou code brut dans les champs UI des schémas/streams + interdiction `ORCIA_DISABLE_PG_BOOTSTRAP_SYNC` hors tests unitaires).
  5. `apps/web/e2e/support/layoutGeometryAssertions.ts` (helper Playwright géométrique `rect.right <= window.innerWidth + 1` & `elementFromPoint` sur modales ouvertes).
- **Facteur de succès clé** : exécuter cette Story **uniquement après achèvement et validation des Stories `22.1` à `22.7`** afin que les 5 gardes passent immédiatement sans faux positifs et verrouillent définitivement le niveau de qualité.

---

## 2. Plan d'Implémentation

### 2.1 Schéma de Données & Migrations Alembic (`infra/migrations/versions/`)
- Vérification finale de la chaîne Alembic `0001` $\rightarrow$ `head` (test `upgrade()` / `downgrade()` + `pnpm db:reset` Jour 0 à `0` utilisateur).

### 2.2 Noyau Métier Hexagonal, Orchestration & Workers (`packages/orcia-core/`, `apps/worker/`)
- Garde CI Python `tests/unit/test_no_raw_enum_codes_in_ui_streams.py` vérifiant :
  - Absence totale d'occurrences de `ORCIA_DISABLE_PG_BOOTSTRAP_SYNC` dans `apps/` et `packages/` ;
  - Absence de marqueurs `[LAYER_5_*]` dans les DTOs / schémas UI de `apps/api/src/orcia_api/schemas/` et les adaptateurs de streaming SSE.

### 2.3 Couche Backend API, Sécurité & Contrats (`apps/api/`, `packages/api-client/`)
- Exécution complète de la couche 3 (`openapi-typescript` `0-diff`, `Schemathesis`, `lint-imports` `5 contracts kept, 0 broken`) et de la couche Sécurité (`tests/security/`).

### 2.4 Interface Utilisateur & Expérience (`packages/ui/`, `apps/web/`)
- Activation des `3` audits statiques Vitest (`anti-jargon-and-secrets-ui-audit.test.ts`, `no-hidden-legacy-panels-audit.test.ts`, `css-class-integrity-audit.test.ts`).
- Déploiement du helper Playwright `layoutGeometryAssertions.ts` dans `05-mobile-companion`, `12-finops`, `14-auth`, `16-ai-models` et les specs de modales/mobile (`rect.right <= window.innerWidth + 1`, `elementFromPoint` confirmant qu'aucune colonne sticky ne recouvre les boutons d'action d'une modale ouverte).
- Optimisation des séquences E2E `14-auth` #2 et `16-ai-models` #2 sous `< 35 s` (`REM-33`).

### 2.5 Analyse d'Impact sur la Pyramide des Tests (`AD-17` — Couches 1 à 5 + Sécurité, Obligatoire)
- **Couche 1a / 1b** : `.venv/bin/pytest --cov=packages/orcia-kernel --cov=packages/orcia-core --cov-fail-under=90` + `pnpm turbo run lint typecheck test`.
- **Couche 2 (`testcontainers` PG18 / Redis / SeaweedFS)** : suite d'intégration complète verte.
- **Couche 3 (`OpenAPI 0-diff`, `Schemathesis`, `lint-imports`, `lint_spine.py`)** : `0` anomalie.
- **Couche 4 (Evals `0 $`) & Couche Sécurité (`tests/security/`)** : `100 %` vert.
- **Couche 5 (Campagne Playwright Intégrale Epic 22)** :
  - Exécution avec `--retries=0 --max-failures=0 --timeout=35000` : **`0` `failed` / `0` `timedOut`** (`100 %` PASS sur les scénarios exécutés + `100 %` des `SELECT` PG18 validés + `100 %` des captures PNG vérifiées sans débordement).
  - Mise à jour de `docs/product/capabilities.yaml` : promotion des `51` capacités `failed_e2e` vers `verification: runtime` (`verified_at: "<date>"`), suppression des `e2e_remediation_ref`, puis `pnpm site:sync && pnpm site:check` (`62/62` `feature` + `3/3` `foundation` = `65/65` `runtime`).

---

## 3. Bilan des Modifications & Résultats (Post-Implémentation)

> *[En attente d'implémentation de la Story 22.8]*

### 3.1 Fichiers Développés & Modifiés
| Fichier | Nature (Création / Modification / Refactoring) | Description synthétique |
| :--- | :--- | :--- |
| `apps/web/src/__tests__/anti-jargon-and-secrets-ui-audit.test.ts` | Création | *[À compléter après implémentation]* |
| `apps/web/src/__tests__/no-hidden-legacy-panels-audit.test.ts` | Création | *[À compléter après implémentation]* |
| `apps/web/src/__tests__/css-class-integrity-audit.test.ts` | Création | *[À compléter après implémentation]* |
| `tests/unit/test_no_raw_enum_codes_in_ui_streams.py` | Création | *[À compléter après implémentation]* |
| `apps/web/e2e/support/layoutGeometryAssertions.ts` & `docs/product/capabilities.yaml` | Création / Modification | *[À compléter après implémentation]* |

### 3.2 Résultats Chiffrés, Métriques & Qualité
- **Couverture de tests** : *[$\ge 90\%$ requis à mesurer après implémentation]*
- **Campagne E2E finale** : *[Attendu `unexpected: 0`, `flaky: 0`, `62/62` `feature` `runtime`]*
- **Qualité statique & Architecture** : `ruff`, `mypy --strict`, `pnpm typecheck`, `lint-imports`, `lint_spine.py`, `pnpm site:check`, `gitnexus_detect_changes()` *[À compléter]*

### 3.3 Validation & Procédure de Test sur Toute la Pyramide (`AD-17`)
- *[À compléter après validation complète de l'Epic 22]*
