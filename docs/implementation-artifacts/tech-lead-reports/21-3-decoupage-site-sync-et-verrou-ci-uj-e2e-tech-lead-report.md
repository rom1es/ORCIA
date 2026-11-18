# Story 21.3 — Refactoring Modulaire de `sync_site_catalog.py` (`< 350` Lignes) & Verrouillage CI Bloquant `CAP ↔ UJ ↔ Spec E2E` (`pnpm site:check`)

- **Date** : 2026-11-18
- **Story / Clé Sprint** : `21-3-refactoring-sync-site-catalog-et-verrou-ci-cap-uj-spec-e2e-site-check` (`Epic 21`)
- **Capacité(s)** : `none (hygiène/outillage CI)` — classification : `hygiène` (`GEMINI.md` §5)
- **Auteur / Contexte** : Tech Lead (`Amelia`) & Ingénieur Plateforme (`Karim`) — Story 21.3 (`FR-1`..`FR-36`, `AD-17`, `NFR-TEST-1`, `GEMINI.md` § Policy & §5). Découper `infra/scripts/sync_site_catalog.py` (`883` lignes) sous `< 350` lignes par fichier, implémenter le verrou CI bloquant `CAP ↔ UJ ↔ Spec E2E` dans `infra/scripts/uj_e2e_coverage.py` intégré à `infra/scripts/capabilities_registry.py` (`run_registry_check` / `pnpm site:check`), et assainir `docs/product/capabilities.yaml` (`e2e_backlog_story` + bascule à `verification: docs` des capacités `feature` dépourvues de spec E2E fonctionnelle hors `11-*`).
- **Commits associés** : Branche `feat/epic-21-user-journeys-e2e-db-audit` (`21.3-impl` + `21.3-test`).

---

## 1. Analyse du Besoin & Étude d'Impact Tech Lead (Pré-Implémentation)

### 1.1 Contexte & Problématique
- **Problématique** :
  1. `infra/scripts/sync_site_catalog.py` atteint `883` lignes (très au-delà du seuil de `300–400` lignes de `GEMINI.md`), mêlant introspection du dépôt, génération du manifeste TypeScript et rendu HTML/CSS/JS du site vitrine autonome (`docs/site-catalog/index.html`).
  2. `infra/scripts/capabilities_registry.py` (`178` lignes) vérifie le schéma `kind`, `uj`, `db_tables` (Story 21.1), mais ne bloque pas encore en CI (`pnpm site:check`) :
     - les `UJ-xx` absents du PRD (`docs/planning-artifacts/prds/prd-ORCIA-2026-10-24/prd.md`) ou les `UJ-1`..`UJ-20` sans capacité `kind: feature` ;
     - les capacités `live` `kind: feature` ne référençant qu'un smoke test `11-*` (`11-screens-smoke-without-server-errors.spec.ts`) ou aucun test E2E fonctionnel (`apps/web/e2e/*.spec.ts`), sans exemption transitoire explicite (`e2e_backlog_story` ou `e2e_remediation_ref`) ;
     - les déclarations `verification: runtime` sans spec E2E fonctionnelle active, avec exemption backlog/remédiation, ou avec un échec dans `playwright-results.json`.
  3. Plusieurs capacités `kind: feature` de `docs/product/capabilities.yaml` portent actuellement `verification: runtime` sur la base exclusive de tests unitaires/intégration ou du smoke `11-*`, sans spec E2E fonctionnelle dédiée.
- **Comportement attendu vs actuel** :
  - `infra/scripts/sync_site_catalog.py` et ses sous-modules extraits (`_site_repo_parsers.py`, `_site_html_renderer.py`, `_site_html_template.py`) doivent chacun rester `< 350` lignes tout en préservant les ré-exports utilisés par les tests (`parse_active_routes`, `build_manifest_data`, etc.) et la conformité `0-diff` de `orciaSiteManifest.ts` et `docs/site-catalog/index.html`.
  - `run_registry_check()` doit intégrer `infra/scripts/uj_e2e_coverage.py` (`< 250` lignes) et bloquer tout écart `CAP ↔ UJ ↔ Spec E2E`.
  - Si des compteurs UJ/E2E (`userJourneysCount`, `coveredUserJourneysCount`, `e2eCoveredCapabilitiesCount`) sont ajoutés à `manifest["stats"]`, `OrciaShowcaseManifestStats` (`packages/ui/src/primitives/OrciaProductShowcaseSiteView.tsx`) doit exposer ces champs optionnels pour maintenir `pnpm typecheck` à `0` erreur.

### 1.2 Exploration, Analyse d'Impact GitNexus, Factorisation & Dette Technique
- **Analyse d'Impact GitNexus (`gitnexus_query`, `gitnexus_context`, `gitnexus_impact` sur `/home/romain/Documents/Projects/ORCIA`)** :
  - `gitnexus_context` / `gitnexus_impact` exécutés sur `infra/scripts/capabilities_registry.py` (`impactedCount: 4`, `risk: LOW`, `direct: 2`), `infra/scripts/sync_site_catalog.py` (`impactedCount: 0`, chargement dynamique via `importlib.util`), `ORCIA_SITE_MANIFEST` et `OrciaShowcaseManifestData` (`packages/ui/src/primitives/OrciaProductShowcaseSiteView.tsx`).
  - Appelants directs (`upstream`) vérifiés dans le dépôt :
    - `package.json` (`site:sync`, `site:check` $\rightarrow$ `infra/scripts/sync_site_catalog.py`) ;
    - `infra/scripts/capabilities_registry.py` (chargement dynamique de `sync_site_catalog.py` pour `parse_active_routes`) ;
    - `tests/unit/test_site_catalog_sync.py` (chargement dynamique de `sync_site_catalog.py` : `main(["--check"])`, `build_manifest_data()`) ;
    - `tests/unit/test_capabilities_registry.py` (chargement dynamique de `capabilities_registry.py` : `assert stats == {"live": 2, "with_tests": 1, "without_tests": ["CAP-002"]}` à la ligne 117) ;
    - `apps/web/src/routes/showcase.tsx` & `apps/web/src/__tests__/orcia-showcase-site.test.tsx` (consommation de `ORCIA_SITE_MANIFEST` typé par `OrciaShowcaseManifestData`).
  - Point d'attention critique identifié : les appels à `importlib.util.spec_from_file_location` dans `capabilities_registry.py`, `test_capabilities_registry.py` et `test_site_catalog_sync.py` n'ajoutent pas automatiquement `infra/scripts/` à `sys.path` ; `sync_site_catalog.py` et `capabilities_registry.py` doivent insérer `Path(__file__).resolve().parent` dans `sys.path` avant d'importer les modules frères. De plus, `capability_test_stats(data)` doit préserver son contrat par défaut à 3 clés (`live`, `with_tests`, `without_tests`) afin de ne pas casser `test_capabilities_registry.py` tout en exposant les statistiques enrichies `@uj`/`@cap` via un paramètre optionnel (`include_uj_e2e=True`).
- **Exploration & Inventaire de `docs/product/capabilities.yaml` (`65` capacités)** :
  - `3` fondations (`CAP-006`, `CAP-100`, `CAP-202`) exemptées E2E (`kind: foundation`).
  - `62` capacités `kind: feature` :
    - `26` disposent déjà d'au moins une spec E2E fonctionnelle dans `apps/web/e2e/` (hors `11-*`) ;
    - `36` sont dépourvues de spec E2E fonctionnelle dédiée (dont `CAP-001`, `CAP-002`, `CAP-010` ne citant que `11-screens-smoke-without-server-errors.spec.ts`) et doivent recevoir leur `e2e_backlog_story` cible (`"21-5"`, `"21-6"` ou `"21-7"` selon `epics.md`) ainsi que `verification: docs` lorsqu'elles portaient `verification: runtime`.
- **Opportunités de Factorisation & Contrôle de Volumétrie** :
  - Découpage strict sous `< 350` lignes par fichier : `_site_repo_parsers.py` (parsing Spine/routes/UI/packs/migrations/rapports + assainissement hexadécimal), `_site_html_template.py` (CSS/HTML statique & script JS autonome), `_site_html_renderer.py` (assemblage dynamique des cartes et tableaux HTML), `sync_site_catalog.py` (orchestration, ré-exports, génération JSON/TS/HTML et CLI `--check`), `uj_e2e_coverage.py` (`< 250` lignes, validation `CAP ↔ UJ ↔ Spec E2E` et parsing des en-têtes `/** @uj ... | @cap ... */`).

---

## 2. Plan d'Implémentation

### 2.1 Schéma de Données & Migrations Alembic (`infra/migrations/versions/...`)
- Non applicable : aucune table ni colonne PostgreSQL modifiée en Story 21.3.

### 2.2 Noyau Métier Hexagonal, Outillage CI & Gouvernance (`infra/scripts/`)
- `infra/scripts/_site_repo_parsers.py` (`< 350` L) :
  - Extraire `HEX_COLOR_RE`, `sanitize_no_hex_for_ts`, `clean_markdown_inline`, `parse_architecture_spine`, `parse_active_routes`, `parse_ui_primitives`, `parse_business_packs`, `parse_migrations`, `parse_tech_lead_reports`.
- `infra/scripts/_site_html_template.py` (`< 350` L) & `infra/scripts/_site_html_renderer.py` (`< 350` L) :
  - Séparer les constantes CSS/HTML/JS statiques (avec étanchéité éditoriale stricte entre Piliers 1, 2 et 3) de l'assemblage dynamique `_format_report_card_html` et `render_standalone_html(manifest)`.
- `infra/scripts/sync_site_catalog.py` (`< 350` L) :
  - Ré-exporter les parseurs et renderers extraits pour préserver la compatibilité des imports existants (`parse_active_routes`, `build_manifest_data`, `render_typescript_manifest`, `render_standalone_html`, `main`).
  - Alimenter `manifest["stats"]` avec `userJourneysCount`, `coveredUserJourneysCount`, `e2eCoveredCapabilitiesCount` via `capability_test_stats(..., include_uj_e2e=True)`.
- `infra/scripts/uj_e2e_coverage.py` (`< 250` L) :
  - `extract_prd_user_journeys(prd_path)` : extraction des titres `#### UJ-N.` dans `prd.md`.
  - `is_functional_e2e_spec(test_path)` : reconnaît `apps/web/e2e/*.spec.ts` en excluant explicitement les specs purement smoke `11-*` (`11-screens-smoke-without-server-errors.spec.ts`, etc.) et `support/`.
  - `parse_e2e_spec_headers(e2e_dir)` : parse les en-têtes `/** @uj ... | @cap ... */` (mono-ligne ou multi-lignes) des specs `apps/web/e2e/*.spec.ts`.
  - `load_failed_e2e_specs(results_path)` : lit `playwright-results.json` s'il existe et recense les fichiers `.spec.ts` en échec (`ok: false` ou statut `failed` / `timedOut` / `interrupted` / `unexpected`).
  - `summarize_uj_e2e_coverage(data, prd_path, e2e_dir)` : calcule les compteurs UJ et couverture E2E pour `capability_test_stats()` et le manifeste.
  - `check_uj_e2e_coverage(data, prd_path, e2e_dir, playwright_results_path, repo_root)` : implémente les 4 verrous bloquants de la Story 21.3.
- `infra/scripts/capabilities_registry.py` (`< 300` L) :
  - Accepter `VERIFICATIONS = {"docs", "runtime", "failed_e2e"}` et valider `e2e_backlog_story` (`{"21-5", "21-6", "21-7"}`) / `e2e_remediation_ref` dans `validate_registry()`.
  - Intégrer `check_uj_e2e_coverage()` dans `run_registry_check()`.
  - Alimenter `capability_test_stats()` via `parse_e2e_spec_headers()` et `summarize_uj_e2e_coverage()` lorsque `include_uj_e2e=True` (ou `e2e_dir` fourni), sans rompre le contrat par défaut à 3 clés.

### 2.3 Registre des Capacités (`docs/product/capabilities.yaml`) & Contrats
- Mettre à jour les `36` capacités `kind: feature` sans spec E2E fonctionnelle (hors `11-*`) dans `docs/product/capabilities.yaml` :
  - `"21-5"` (`12` capacités) : `CAP-001`, `CAP-003`, `CAP-041`, `CAP-043`, `CAP-051`, `CAP-052`, `CAP-053`, `CAP-054`, `CAP-058`, `CAP-063`, `CAP-069`, `CAP-190`, `CAP-203` (`13` capacités en comptant `CAP-041`/`CAP-043` + Auth/Org/Hub IA/Broker/Profil).
  - `"21-6"` (`11` capacités) : `CAP-002`, `CAP-010`, `CAP-011`, `CAP-055`, `CAP-056`, `CAP-057`, `CAP-081`, `CAP-082`, `CAP-084`, `CAP-150`, `CAP-180`.
  - `"21-7"` (`12` capacités) : `CAP-020`, `CAP-021`, `CAP-022`, `CAP-024`, `CAP-030`, `CAP-031`, `CAP-066`, `CAP-068`, `CAP-072`, `CAP-076`, `CAP-092`, `CAP-140`.
  - Basculer à `verification: docs` celles qui étaient marquées `verification: runtime` sans spec E2E fonctionnelle (tout en conservant intactes leurs entrées `tests:`).

### 2.4 Interface Utilisateur & Expérience (`packages/ui/`, `apps/web/`, `docs/site-catalog/`)
- `packages/ui/src/primitives/OrciaProductShowcaseSiteView.tsx` : ajouter les propriétés optionnelles `userJourneysCount?: number`, `coveredUserJourneysCount?: number`, `e2eCoveredCapabilitiesCount?: number` à `OrciaShowcaseManifestStats`.
- Synchroniser `apps/web/src/generated/orciaSiteManifest.ts`, `docs/site-catalog/index.html` et `dist/orcia-site/index.html` via `.venv/bin/python infra/scripts/sync_site_catalog.py`.

### 2.5 Analyse d'Impact sur la Pyramide des Tests (`AD-17` — Prise en charge par `21.3-test`)
- **Couche 1a (Unitaires Python `tests/unit/`)** : `tests/unit/test_uj_e2e_coverage_gate.py` (à créer par `21.3-test`), `tests/unit/test_capabilities_registry.py`, `tests/unit/test_site_catalog_sync.py`, `tests/unit/test_uj_prd_experience_consistency.py`.
- **Couche 1b / Typecheck TS** : `pnpm typecheck` (`OrciaShowcaseManifestData`) et `apps/web/src/__tests__/orcia-showcase-site.test.tsx`.
- **Couche 3 (Qualité Statique & CI)** : `.venv/bin/ruff check infra/scripts`, `.venv/bin/ruff format --check infra/scripts`, `.venv/bin/mypy --strict infra/scripts`, `pnpm site:check`, `wc -l infra/scripts/*.py`.

---

## 3. Bilan des Modifications & Résultats (Post-Implémentation)

### 3.1 Fichiers Développés & Modifiés
| Fichier | Nature (Création / Modification / Refactoring) | Description synthétique |
| :--- | :--- | :--- |
| `infra/scripts/_site_repo_parsers.py` | Création (Extraction) | Parseurs Spine, routes SPA, primitives UI, packs, migrations Alembic, rapports Tech Lead et assainissement hexadécimal (`199` lignes `< 350`). |
| `infra/scripts/_site_html_styles.py` | Création (Extraction) | Feuille de style CSS autonome du catalogue statique (`177` lignes `< 350`). |
| `infra/scripts/_site_html_template.py` | Création (Extraction) | Gabarit HTML statique et script JS autonome des 4 piliers (`182` lignes `< 350`). |
| `infra/scripts/_site_html_renderer.py` | Création (Extraction) | Rendu dynamique HTML des cartes rapports et statistiques du site autonome (`170` lignes `< 350`). |
| `infra/scripts/sync_site_catalog.py` | Refactoring | Orchestrateur CLI `--check` / sync (`883` → `220` lignes `< 350`), ré-exports compatibilité et compteurs `UJ` / E2E dans `manifest["stats"]`. |
| `infra/scripts/uj_e2e_coverage.py` | Création | Verrou CI `CAP ↔ UJ ↔ Spec E2E` (`244` lignes `< 350`) : parsing `prd.md`, en-têtes `/** @uj ... \| @cap ... */`, exclusion smoke `11-*`, inspection `playwright-results.json`. |
| `infra/scripts/capabilities_registry.py` | Modification | Intégration de `check_uj_e2e_coverage` dans `run_registry_check()`, validation `e2e_backlog_story` / `e2e_remediation_ref` / `failed_e2e` et compteurs enrichis `capability_test_stats(..., include_uj_e2e=True)` (`233` lignes `< 350`). |
| `docs/product/capabilities.yaml` | Modification | Ajout de `e2e_backlog_story` (`21-5` / `21-6` / `21-7`) et passage à `verification: docs` des `36` capacités `feature` sans spec E2E fonctionnelle hors `11-*`. |
| `packages/ui/src/primitives/OrciaProductShowcaseSiteView.tsx` | Modification | Champs optionnels `userJourneysCount`, `coveredUserJourneysCount`, `e2eCoveredCapabilitiesCount` sur `OrciaShowcaseManifestStats`. |
| `apps/web/src/generated/orciaSiteManifest.ts` & `docs/site-catalog/index.html` | Régénération | Synchronisation `pnpm site:sync` (`166` rapports, `28` routes, `133` primitives UI, `65` capacités, `20/20` UJ, `26/62` E2E fonctionnels). |
| `tests/unit/test_uj_e2e_coverage_gate.py` | Création | Suite dédiée (`277` lignes `< 280`) : 4 cas de blocage CI, parsing `@uj`/`@cap`, `run_registry_check()` nominal & bloqué, contrôle taille `< 350` L des 7 scripts. |
| `tests/unit/test_capabilities_registry.py` & `tests/unit/test_site_catalog_sync.py` | Modification | Validation `e2e_backlog_story` / `e2e_remediation_ref` / `failed_e2e` et vérification des compteurs `userJourneysCount` / `coveredUserJourneysCount` / `e2eCoveredCapabilitiesCount`. |
| `docs/implementation-artifacts/tech-lead-reports/README.md` & `docs/implementation-artifacts/sprint-status.yaml` | Clôture | Indexation du rapport `21-3` et passage de la story `21-3` à `done`. |

### 3.2 Résultats Chiffrés, Métriques & Qualité
- **Volumétrie des scripts (`infra/scripts/*.py`)** : `sync_site_catalog.py` (`220` L), `_site_repo_parsers.py` (`199` L), `_site_html_renderer.py` (`170` L), `_site_html_styles.py` (`177` L), `_site_html_template.py` (`182` L), `uj_e2e_coverage.py` (`244` L), `capabilities_registry.py` (`233` L) — tous `< 350` lignes.
- **Couverture & suites ciblées** : `tests/unit/test_uj_e2e_coverage_gate.py`, `tests/unit/test_capabilities_registry.py`, `tests/unit/test_uj_prd_experience_consistency.py`, `tests/unit/test_site_catalog_sync.py` → `29 passed`.
- **Qualité statique & Architecture** :
  - `.venv/bin/ruff check infra/scripts tests/unit/test_uj_e2e_coverage_gate.py tests/unit/test_capabilities_registry.py tests/unit/test_site_catalog_sync.py` : `All checks passed!`
  - `.venv/bin/ruff format --check infra/scripts tests/unit/test_uj_e2e_coverage_gate.py` : `23 files already formatted`
  - `MYPYPATH=infra/scripts .venv/bin/mypy --strict infra/scripts/*.py` : `Success: no issues found in 7 source files`
  - `pnpm turbo run lint typecheck test` : `9 successful, 9 total` (`@orcia/api-client`: `13 passed`, `@orcia/ui`: `108 passed`, `@orcia/web`: `153 passed`, dont `orcia-showcase-site.test.tsx`)
  - `pnpm site:sync && pnpm site:check` : `[capabilities] 65/65 capacités live référencent au moins un test (0 sans test) · E2E fonctionnels: 26/62 · UJ: 20/20.` / `[site:check OK] Manifest (166 reports, 28 routes, 133 UI primitives) is in sync.`
  - `gitnexus:detect_changes` (`repo: "/home/romain/Documents/Projects/ORCIA"`) : `changed_count: 17`, `affected_count: 0`, `changed_files: 10`, `risk_level: "low"`.

### 3.3 Validation & Procédure de Test sur Toute la Pyramide (`AD-17` + Gouvernance Registre)
- **Couche 1a — Tests Unitaires Python (`pytest`)** : Vérification des 4 verrous bloquants (`UJ` absent du PRD, `UJ` sans capacité `feature`, `live` `feature` sous smoke `11-*` sans `e2e_backlog_story`/`e2e_remediation_ref`, `verification: runtime` sans spec fonctionnelle ou en échec dans `playwright-results.json`), parsing `/** @uj ... | @cap ... */`, `run_registry_check() == []` sur le dépôt réel et borne `< 350` lignes.
- **Couche 1b — Frontend TS (`Vitest`) & Typage (`tsc --noEmit`)** : `pnpm turbo run lint typecheck test` validé (`9/9` tâches, `0` erreur de type sur `OrciaShowcaseManifestData`).
- **Couche Transverse — Gouvernance Registre (`pnpm site:check`)** : Exécuté et vert après synchronisation finale (`0` écart `CAP ↔ UJ ↔ Spec E2E`).
- **Couches 2, 3, 4 & 5 (`PG18`, `OpenAPI`, `Evals`, `Playwright`)** : Non impactées directement par cette story d'outillage CI ; le verrou E2E prépare l'exécution des campagnes Stories `21.4` à `21.8`.
