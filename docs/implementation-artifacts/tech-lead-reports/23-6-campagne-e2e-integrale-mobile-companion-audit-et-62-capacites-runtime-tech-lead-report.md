# Story 23.6 — Stabilisation Specs `04`–`21` & Mobile Companion (`390×844`) & Audit `100 %` Assertions SQL PostgreSQL 18 Effectives (`55/55` Blocs E2E) *(Reportée en `ACTION_ITEM-23.6`)*

> **Décision de gouvernance (`Step 2a Epic 23`, 2026-11-19 — RCA Epic 22)** :
> - **La `Story 23.6` et l'ensemble du périmètre Mobile Companion (`--project=mobile-companion`, `390×844`, `CAP-042` et assertions responsive mobile) sont explicitement déplacés vers `action_items:` (`ACTION_ITEM-23.6` dans `docs/implementation-artifacts/sprint-status.yaml`) pour priorisation ultérieure.**
> - L'audit SQL PG18 effectif (`55/55` blocs `test(...)`, zéro `SELECT 1`, zéro table alibi hors domaine) et le durcissement anti-Goodhart des 5 couches sont repris sur le chemin critique par la Story intercalaire **`Story 23.6a`** ([`23-6a-durcissement-anti-goodhart-gardes-openapi-ast-geometrie-et-reset-pg18-tech-lead-report.md`](./23-6a-durcissement-anti-goodhart-gardes-openapi-ast-geometrie-et-reset-pg18-tech-lead-report.md)).
> - La campagne Playwright E2E de **`Story 23.7`** et la clôture de **`Story 23.8`** portent désormais exclusivement sur **`--project=desktop-cockpit`** (`1440×900`, `24` specs / `55` scénarios Desktop dont `52` exécutés et `3` `mobile-only` skipped) : [`23-7-campagne-e2e-integrale-captures-png-bilan-et-audit-croise-sally-winston-tech-lead-report.md`](./23-7-campagne-e2e-integrale-captures-png-bilan-et-audit-croise-sally-winston-tech-lead-report.md) et [`23-8-rapports-tech-lead-plan-correction-global-et-initialisation-epic-24-tech-lead-report.md`](./23-8-rapports-tech-lead-plan-correction-global-et-initialisation-epic-24-tech-lead-report.md).
>
> *(Rappel historique `Step 0 Epic 23` : l'ancienne portée de la Story `23.6` avait préalablement été scindée en trois temps : `23.6` stabilisation/audit, `23.7` campagne figée, `23.8` clôture & Epic 24.)*

- **Date** : 2026-11-19
- **Story / Clé Sprint** : `23-6-campagne-e2e-integrale-mobile-companion-audit-et-62-capacites-runtime` *(Archivée / Déplacée en `action_items:` $\rightarrow$ `ACTION_ITEM-23.6`)*
- **Capacité(s)** : `CAP-002`, `CAP-010`, `CAP-042`, `CAP-043`, `CAP-050`, `CAP-051`, `CAP-052`, `CAP-053`, `CAP-055`, `CAP-056`, `CAP-057`, `CAP-058`, `CAP-063`, `CAP-066`, `CAP-067`, `CAP-069`, `CAP-076`, `CAP-080`, `CAP-081`, `CAP-083`, `CAP-084`, `CAP-090`, `CAP-091`, `CAP-092`, `CAP-150`, `CAP-180`, `CAP-203` *(préparation et stabilisation bout-en-bout de l'ensemble des `62` capacités `feature` + `3` `foundation` avant campagne figée en `Story 23.7`)* — classification : `feature` + `ux` (`REM23-13` / `ARCH23-10`, `P0-UX-2`)
- **Auteur / Contexte** : `22.10-impl` (Sally × Winston — pré-implémentation Epic 23), mis à jour `23.0-impl` (2026-11-19). Stabilise les parcours `04`–`21`, `shell.spec.ts` et Mobile Companion (`390×844`) post-Vagues 0 & 1 (`Stories 23.1`–`23.5`) sans retry ni fixture cachée (`ORCIA_E2E_SEED_FIXTURES` absent), résout tout écart fonctionnel ou responsive révélé après déblocage de `resetDay0()`, et réalise l'audit + renforcement des `100 %` assertions SQL PostgreSQL 18 effectives sur les `55` blocs `test(...)` E2E avant gel de la campagne en `Story 23.7`.
- **Commits associés** : `En attente d'implémentation (initialisé par Story 22.10, recadré Step 0 Epic 23)`

---

## 1. Analyse du Besoin & Étude d'Impact Tech Lead (Pré-Implémentation)

### 1.1 Contexte & Problématique
- **Angle mort massif constaté en Epic 22 (`bilan-execution-tests-e2e-epic-22.md`, `P0-UX-2`, `ARCH23-10`)** :
  - À cause de l'échec SQL en cascade de `resetDay0()` dès le scénario `#11`, **`20` specs complètes sur `24`** (`04-multi-actor-claim-sse.spec.ts` à `21-assistant-citations-v5-audit-help-showcase.spec.ts` et `shell.spec.ts`) ainsi que **100 % des `55` scénarios `mobile-companion` (`390×844`)** n'ont pas atteint le DOM applicatif authentifié (`0 / 55` PASS en mobile).
  - **Surfaces critiques restant à prouver sous `ORCIA_ENV="e2e"` sans `ORCIA_E2E_SEED_FIXTURES`** :
    1. **Mobile Companion (`390×844`)** : barre basse 3 onglets (`mobile-bottom-tab-bar`), bannière desktop-only sur `/configuration` et `/organization`, zéro overflow horizontal sur `/assistant`, `/spaces`, `/processes`, `/finops` (`05`, `12`, `13`, `14`, `shell`) — ex. [`#62` `02-assistant` mobile](../e2e-campaign-epic-22/screenshots/02-assistant-streaming-and-folders/mobile-companion--un-tour-d-assistant-traverse-le-navigateur-l-api-et-la-cassette-llm-0-et-affiche-une-rep--failed.png), [`#80` `12-finops` mobile](../e2e-campaign-epic-22/screenshots/12-finops-and-audit-provenance/mobile-companion--mobile-finops-et-activity-s-affichent-sans-debordement-horizontal-ni-erreur-serveur--failed.png), [`#99` `18-catalog` mobile](../e2e-campaign-epic-22/screenshots/18-catalog-packs-wizards-and-mcp-bench/mobile-companion--parcours-guide-d-initialisation-avec-retour-arriere-survit-a-f5-et-persiste-dans-wizard---failed.png), [`#107` `shell` mobile](../e2e-campaign-epic-22/screenshots/shell/mobile-companion--presente-les-4-zones-masque-parametres-tant-qu-aucun-platform-admin-n-est-connecte-et-l---failed.png), [`#110` modale Jour 0 mobile](../e2e-campaign-epic-22/screenshots/shell/mobile-companion--la-modale-jour-0-est-un-dialogue-accessible-qui-bloque-le-shell--failed.png).
    2. **Parcours métiers complets `04`–`21`** : SSE multi-acteurs `/api/v1/events/stream` (`04`), Gates & anti-rubber-stamping (`06`), Espaces/Org (`07`), Agents 6 blocs (`08`), Pack Builder (`09`), Palette `⌘K` (`10`), Smoke écrans (`11`), Trace réflexive `#L` / `/trace-stream` (`12-epic16`), FinOps/Audit (`12-finops`), Autonomie/Kill-Switch (`13`), Auth/2FA/Mon Compte/Profil (`14`), IAM/SecOps/`READ_ONLY_OBSERVER` (`15`), Modèles IA/SSRF/Réindexation/Broker (`16`), Sources/CodeGraph/ADN Starlark/Ontologie (`17`), Catalogue/Packs/Wizards/Banc MCP (`18`), Orchestration/What-If/Replay (`19`), Studio V2/Log Sink (`20`), Citations v5/Aide/`/showcase` (`21`).

### 1.2 Exploration, Analyse d'Impact GitNexus, Factorisation & Dette Technique
- **Précondition topologique bloquante (`REM23-13` / `synthese-remediation-sally-winston-epic-22.md`)** :
  - **Interdiction de lancer cette campagne globale avant clôture complète de la Vague 0 (`23.1`, `23.2`) et de la Vague 1 (`23.3`, `23.4`, `23.5`)**.
- **Gouvernance registre & scripts vérifiés** :
  - `infra/scripts/uj_e2e_coverage.py` lit `PLAYWRIGHT_RESULTS_PATH` (`docs/implementation-artifacts/e2e-campaign-epic-22/playwright-results.json` actuellement) pour croiser `capabilities.yaml`. Après la campagne Epic 23, `PLAYWRIGHT_RESULTS_PATH` devra pointer vers `docs/implementation-artifacts/e2e-campaign-epic-23/playwright-results.json`.
  - Tout fichier d'artefact archivé dans `docs/implementation-artifacts/e2e-campaign-epic-23/` doit rester strictement `< 450 KB` (`460 800` octets) pour respecter le hook `pre-commit`.

---

## 2. Plan d'Implémentation

### 2.1 Schéma de Données & Migrations Alembic (`infra/migrations/versions/`)
- Aucune migration planifiée a priori ; en cas d'anomalie SQL résiduelle découverte lors du déblocage des specs `04`–`21`, suivre strictement le protocole Alembic (`Expand -> Backfill SQL -> Contract`).

### 2.2 Noyau Métier, Backend & API (`packages/orcia-core/`, `apps/api/`)
- Résoudre sans contournement toute régression fonctionnelle ou timeout `< 35 s` éventuellement mis au jour dans les specs `04`–`21` ou `mobile-companion` après déblocage de `resetDay0()`.
- Vérifier que la pile `e2e_stack.py` tourne sans `ORCIA_E2E_SEED_FIXTURES` contre PostgreSQL 18 + `pgvector` et Redis 7.4 (`DeterministicCassetteLLM` `0 $`).

### 2.3 Gouvernance Documentaire, Registre & Vitrine (`infra/scripts/`, `docs/product/capabilities.yaml`)
1. **`infra/scripts/uj_e2e_coverage.py`** : basculer `PLAYWRIGHT_RESULTS_PATH` sur `docs/implementation-artifacts/e2e-campaign-epic-23/playwright-results.json`.
2. **`docs/product/capabilities.yaml`** :
   - Une fois `97 / 97` scénarios exécutés PASS (`0` échec, `0` timeout, `13` viewport skips attendus), passer les **`62 / 62` capacités `feature`** à `verification: runtime` (`verified_at: "<YYYY-MM-DD>"`) et supprimer les clés temporaires `e2e_remediation_ref`.
3. **Synchronisation Vitrine** : exécuter `pnpm site:sync && pnpm site:check` (`0` erreur).

### 2.4 Campagne Playwright Intégrale & Audit Visuel Sally (`apps/web/e2e/`, `docs/implementation-artifacts/e2e-campaign-epic-23/`)
1. Exécuter la campagne complète :
   `CI=1 ORCIA_E2E_CAMPAIGN_DIR=docs/implementation-artifacts/e2e-campaign-epic-23 PLAYWRIGHT_JSON_OUTPUT_NAME=.../e2e-campaign-epic-23/playwright-results.json timeout --kill-after=30s 2400s pnpm --filter @orcia/web exec playwright test --retries=0 --max-failures=0 --timeout=35000 --reporter=list,json`.
2. Archiver `playwright-results.json`, `manifest.jsonl`, `100 %` des captures PNG (`screenshots/`, taille `< 450 KB` par fichier), `bilan-execution-tests-e2e-epic-23.md`, et les audits visuels finaux **Sally (`Mobile Companion` + écrans `04`–`21` + captures `#10`) × Winston**.

### 2.5 Analyse d'Impact sur la Pyramide des Tests (`AD-17` — Couches 1 à 5 + Sécurité, Obligatoire)
- Exécution intégrale des **5 couches `AD-17`** avant clôture :
  - Couche 1a (`pytest --cov=packages/orcia-kernel --cov=packages/orcia-core --cov-fail-under=90`) & Couche 1b (`pnpm turbo run lint typecheck test`) ;
  - Couche 2 (`tests/integration/` `testcontainers` PG18 + Redis + SeaweedFS sans override) ;
  - Couche 3 (`openapi-typescript` `0-diff`, `Schemathesis`, `lint-imports`, `lint_spine.py`, `check_implementation_docs.py`, `site:check`) ;
  - Couche 4 (`tests/evals/` `DeterministicCassetteLLM`) & Couche Sécurité (`tests/security/`) ;
  - Couche 5 (`110` scénarios Playwright : `97 / 97` exécutés PASS, `0` failed, `0` timedOut, `13` viewport skips).

---

## 3. Bilan des Modifications & Résultats (Post-Implémentation)

> **[Statut : Déplacée vers `action_items:` (`ACTION_ITEM-23.6`, `status: open`, `priority: P2`) le 2026-11-19]**
> - La **Story `23.6`** et la **compatibilité Mobile Companion (`--project=mobile-companion`, `390×844`, `CAP-042`)** ont été retirées du `development_status:` de l'Epic 23 et déplacées vers **`ACTION_ITEM-23.6`** dans `docs/implementation-artifacts/sprint-status.yaml` pour priorisation ultérieure.
> - Les volets transverses de durcissement SQL PG18 effectif (`55/55` blocs E2E sans `SELECT 1` ni table hors domaine), de transport OpenAPI `security`, d'audits AST et de contrats géométriques Desktop Direction C sont exécutés dès l'Epic 23 via **`Story 23.6a`** (`23-6a-durcissement-anti-goodhart-gardes-openapi-ast-geometrie-et-reset-pg18`).
> - La vérification E2E Desktop (`--project=desktop-cockpit`, `1440×900`, `24` specs / `55` scénarios Desktop, `52` exécutés + `3` `mobile-only` skipped) est portée par **`Story 23.7`**.

### 3.1 Fichiers Développés & Modifiés
| Fichier | Nature (Création / Modification / Refactoring) | Description synthétique |
| :--- | :--- | :--- |
| `docs/implementation-artifacts/sprint-status.yaml` | Archive / Report | Story `23.6` déplacée vers `action_items:` (`ACTION_ITEM-23.6`) ; périmètre Mobile dépriorisé hors chemin critique Epic 23. |
| `docs/implementation-artifacts/tech-lead-reports/23-6a-...-tech-lead-report.md` | Relais Epic 23 | Reprend le verrouillage SQL PG18 domaine (`55/55` blocs) et les gardes anti-Goodhart avant `Story 23.7`. |

### 3.2 Résultats Chiffrés, Métriques & Qualité
- **Statut Epic 23** : **Reportée en `ACTION_ITEM-23.6`** (`story_ref: 23-6-campagne-e2e-integrale-mobile-companion-audit-et-62-capacites-runtime`, `CAP-042` maintenue `failed_e2e` en attendant la reprise Mobile Companion).
- **Relais actif** : `Story 23.6a` (`CAP-100`, `hygiène`) puis `Story 23.7` (`--project=desktop-cockpit`).

### 3.3 Validation & Procédure de Test sur Toute la Pyramide (`AD-17` + 5 Garde-Fous de Câblage Vertical)
- Reporté sous `ACTION_ITEM-23.6` pour la partie Mobile Companion (`390×844` / `CAP-042`) ; couverture Desktop `52/52` PASS reprise par `Story 23.6a` + `Story 23.7`.
