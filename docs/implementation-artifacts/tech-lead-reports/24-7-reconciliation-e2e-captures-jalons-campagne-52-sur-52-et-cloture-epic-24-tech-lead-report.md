# Rapport Tech Lead — Story 24.7 : Réconciliation des Sélecteurs E2E, Captures Jalons, Campagne Figée `52/52` & Clôture Epic 24

- **Story :** `24-7-reconciliation-e2e-captures-jalons-campagne-52-sur-52-et-cloture-epic-24` (Epic 24 — Vague 2 `P0` Validation & Clôture)
- **Date :** 2026-11-20
- **Statut :** `Terminé (done)` (initialisé par `Story 23.8`, validé `Case A — Clôture Epic 24 sans Epic 25` par contre-audit Sally × Winston)
- **Plan directeur :** [`sprint-change-proposal-2026-11-20-epic-24-remediation-plan.md`](../../planning-artifacts/sprint-change-proposal-2026-11-20-epic-24-remediation-plan.md)
- **Références remédiées :** `REM24-11`, `REM24-12`, **`USER24-BUG-1..6`** | Échecs E2E `18#1 #41`, `07 #16` + revalidation globale `52/52` Desktop | Constat `UX23-17` (`P3`) + contre-audit `0 P0 / 0 P1` | Diagnostics `ARCH24-06`, `ARCH24-12`
- **Capacité(s) (`capabilities.yaml`) :** `CAP-002`, `CAP-080` (`2` capacités assignées directement + promotion finale des `25` capacités Desktop vers `runtime` ; `CAP-042` maintenue sur `ACTION_ITEM-23.6`)
- **Classification :** `feature` (réconciliation E2E stricte, preuve visuelle jalons & clôture conditionnelle)

---

## 1. Analyse du Besoin & Étude d'Impact Tech Lead

### 1.1 Contexte & Critères d'Acceptation
Une fois les vagues `0` (`Stories 24.1..24.3`) et `1` (`Stories 24.4..24.6`) livrées, deux causes racines purement situées dans le harnais E2E + l'exigence de preuve finale restent à traiter avant la clôture de l'Epic 24 :
1. **Sélecteurs E2E ambigus (`18#1 #41`, `07 #16` / `ARCH24-06`)** :
   - Dans `apps/web/e2e/support/workspaceAndCatalogHelpers.ts:126-130` (`157` L), `openCatalogOrAgentsPage` attend le sélecteur `agents-and-skills-manager-view` même lorsqu'il ouvre `/catalog` (où est monté `catalog-explorer-panel`), provoquant un timeout systématique sur `18#1 #41`.
   - Dans `apps/web/e2e/07-spaces-org-and-workspace-persistence.spec.ts:42` (`59` L), la requête Playwright n'est pas bornée à `page.getByRole("main")`, ce qui crée une collision avec les libellés du menu latéral ou du fil d'Ariane (`07 #16`).
2. **Captures des états métier riches & preuve finale `52/52` (`UX23-17`, `REM24-12`)** :
   - Les captures `00 #3/#4` et `04 #12` doivent attendre la stabilisation complète de la surface métier établie, et des captures jalons (`< 450 KB`) doivent prouver visuellement le studio VSM `11` étapes, le drawer HITL et la vue tripartite/waivers (`milestone-*.png`).
   - La campagne figée finale `--project=desktop-cockpit --retries=0 --max-failures=0` sans `ORCIA_E2E_SEED_FIXTURES` doit être archivée dans `docs/implementation-artifacts/e2e-campaign-epic-24/` avec contre-audit Sally × Winston confirmant **`52/52` PASS Desktop (`0 failed`, `0 timedOut`, `3 skipped` `mobile-only`, `0 flaky`)**, **`0 P0 / 0 P1`** et la résolution visuelle effective des `6` remontées utilisateur `USER24-BUG-1..6`.

**Critères d'acceptation :** `100 %` (`52/52`) des scénarios Desktop PASS sans retry ni bypass, `100 %` des captures `< 450 KB` y compris les nouveaux jalons, `0` constat `P0`/`P1` au contre-audit Sally × Winston, promotion des `25` capacités Desktop `failed_e2e` vers `runtime` (`64/65` avec `CAP-042` maintenue sous `ACTION_ITEM-23.6`), et clôture finale de l'Epic 24 sans boucle infinie d'Epic 25.

### 1.2 Analyse d'Impact GitNexus (`repo: "/home/romain/Documents/Projects/ORCIA"`)
- `CatalogExplorerPanel` (`packages/ui/src/shell/CatalogExplorerPanel.tsx:49`, `310` L) : `impactedCount: 261`, `risk: "CRITICAL"` — vérifie la présence du `data-testid="catalog-explorer-panel"` attendu sur `/catalog`.
- Inspection directe des fichiers E2E ciblés : `apps/web/e2e/support/workspaceAndCatalogHelpers.ts` (`157` L, `L126-130`), `apps/web/e2e/07-spaces-org-and-workspace-persistence.spec.ts` (`59` L, `L42`), `apps/web/e2e/18-catalog-packs-wizards-and-mcp-bench.spec.ts` (`179` L).

### 1.3 Opportunités de Factorisation & Contrôle de Volumétrie (`< 350` L)
- **Synchronisation E2E↔UI centralisée** : vérifier que l'audit `e2e-testids-sync-audit.test.ts` valide la correspondance exacte entre `catalog-explorer-panel` (`/catalog`) et `agents-and-skills-manager-view` (`/agents`) dans `workspaceAndCatalogHelpers.ts`.
- **Utilitaire partagé de capture jalon `< 450 KB`** : réutiliser le helper de capture Playwright existant sans dupliquer la logique de redimensionnement/compression dans les specs `00`, `04`, `06`, `17`, `20`.

---

## 2. Plan d'Implémentation

### 2.1 Couche Données & Migrations Alembic / PostgreSQL 18
- Aucune nouvelle table dans `24.7` ; exécution obligatoire de `pnpm db:reset` avant la campagne finale pour garantir la vérité terrain Jour 0 (`0` utilisateur, `0` fixture cachée).

### 2.2 Noyau Hexagonal (`orcia-kernel` / `orcia-core`) & Workers
- Aucun ajustement fonctionnel attendu si `24.1..24.6` sont conformes ; vérification finale de `lint-imports` et des événements Outbox générés durant la campagne E2E.

### 2.3 Backend FastAPI (`apps/api`) & Contrat OpenAPI (`packages/api-client`)
- Vérification finale du gate `0-diff` OpenAPI, de la disponibilité de `/readyz` / `/healthz` et du comportement sans erreur `5xx` durant les `55` scénarios de la campagne.

### 2.4 Interface SPA Vite + TanStack Router & Tests E2E (`apps/web/e2e`)
1. Corriger `openCatalogOrAgentsPage` dans `apps/web/e2e/support/workspaceAndCatalogHelpers.ts:126-130` (`157` L) afin d'attendre `[data-testid="catalog-explorer-panel"]` sur `/catalog` et `[data-testid="agents-and-skills-manager-view"]` sur `/agents`.
2. Borner le sélecteur de `apps/web/e2e/07-spaces-org-and-workspace-persistence.spec.ts:42` (`59` L) à `page.getByRole("main")`.
3. Stabiliser les captures `00 #3/#4` et `04 #12` après rendu complet de la surface métier et ajouter les captures `milestone-*.png` (`< 450 KB`) pour VSM `11` étapes (`20`), drawer HITL (`06`) et tripartite/waivers (`17`).
4. Exécuter la campagne figée `--project=desktop-cockpit --retries=0 --max-failures=0` sans `ORCIA_E2E_SEED_FIXTURES`, archiver `playwright-results.json`, `manifest.jsonl`, captures PNG `< 450 KB`, bilan et contre-audit Sally × Winston dans `docs/implementation-artifacts/e2e-campaign-epic-24/` (vérifiant notamment la résolution visuelle des 6 correctifs utilisateur `USER24-BUG-1..6`).

### 2.5 Stratégie de Vérification & 5 Couches de Tests (`AD-17`)
- **Couche 1 (Unitaire >= 90 %)** : `pytest --cov=packages/orcia-kernel --cov=packages/orcia-core --cov-fail-under=90` complet + `lint-imports` + tests de traçabilité `capabilities.yaml`.
- **Couche 2 (Intégration `testcontainers` PG18 réel)** : suite complète d'intégration PostgreSQL 18 + Redis + SeaweedFS.
- **Couche 3 (Composants React)** : `pnpm turbo run lint typecheck test` incluant `zero-dead-buttons-and-silent-catches-audit.test.tsx` et `e2e-testids-sync-audit.test.ts`.
- **Couche 4 (E2E Playwright Campagne Intégrale)** : **`52/52` PASS Desktop (`0 failed`, `0 timedOut`, `3 skipped` `mobile-only`, `0 flaky`)** et contre-audit visuel Sally × Winston **`0 P0 / 0 P1`** sur `100 %` des captures.
- **Couche 5 (Registres, Docs & Sécurité)** : promotion des `25` capacités vers `runtime` (`64/65` avec `CAP-042` sur `ACTION_ITEM-23.6`), `check_implementation_docs.py`, `pnpm site:sync && pnpm site:check` (`0` erreur), `lint_spine.py`.

---

## 3. Bilan des Modifications & Résultats

### 3.1 Fichiers Développés & Modifiés
| Fichier / Composant | Action Réalisée | Statut |
|---|---|---|
| `apps/web/e2e/support/workspaceAndCatalogHelpers.ts` | Distinction `/catalog` (`catalog-explorer-panel`) vs `/agents` (`agents-and-skills-manager-view`) dans `openCatalogOrAgentsPage` (`L126-130`, `18#1 #41`, `ARCH24-06`) | `Terminé` |
| `apps/web/e2e/07-spaces-org-and-workspace-persistence.spec.ts` | Bornage sélecteur `L42` sur `page.getByRole("main").getByText("Espace E2E Comptabilité").first()` (`07 #16`) | `Terminé` |
| `apps/web/e2e/support/e2eCaptureFixture.ts`, `00-stack-smoke.spec.ts`, `04-multi-actor-claim-sse.spec.ts` | Attente disparition `auth-hydrating-loader` et authentification UI préalable sur `00 #3/#4` et `04 #12` (`UX23-17`) | `Terminé` |
| `apps/web/e2e/18-catalog-packs-wizards-and-mcp-bench.spec.ts` | Alignement des assertions SQL PG18 `/catalog` sur `catalog_items`, `connector_schemes` et `declarative_pack_bundles` | `Terminé` |
| `apps/web/e2e/06-gates-review-and-anti-rubber-stamping.spec.ts`, `17-workspace-...`, `20-process-studio-...` | Ajout des `3` captures jalons `milestone-gates-hitl-drawer.png`, `milestone-ontology-tripartite-waivers.png`, `milestone-vsm-11-steps.png` (`< 450 KB`) | `Terminé` |
| `docs/implementation-artifacts/e2e-campaign-epic-24/` | Campagne figée `--project=desktop-cockpit --retries=0 --max-failures=0` sans `ORCIA_E2E_SEED_FIXTURES` : `playwright-results.json`, `manifest.jsonl` (`55`), `61` PNG `< 450 KB`, `bilan-execution-tests-e2e-epic-24.md`, `notes-audit-sally-ux.md`, `notes-audit-winston-architecture.md`, `synthese-remediation-sally-winston-epic-24.md` | `Terminé` |
| `tests/unit/test_hybrid_rag_and_tripartite.py` & `tests/unit/test_epic22_to_epic23_traceability.py` | Alignement `L305` (`"ws-claims-alpha"` $\rightarrow$ `"scope-global"`, suite `484f90c` `Story 24.2`) et garde post-clôture `epic-24 == "done"` (`64 runtime / 1 failed_e2e`) | `Terminé` |
| `infra/scripts/uj_e2e_coverage.py`, `docs/product/capabilities.yaml`, `docs/implementation-artifacts/sprint-status.yaml`, `README.md` | Bascule `PLAYWRIGHT_RESULTS_PATH` vers `e2e-campaign-epic-24/`, promotion des `25` capacités Desktop vers `runtime` (`64/65` `runtime`, `CAP-042` maintenue `ACTION_ITEM-23.6`), ouverture `ACTION_ITEM-24.1` (`P2`) & `ACTION_ITEM-24.2` (`P3`), passage `24-7` et `epic-24` à `done` | `Terminé` |
| `apps/web/src/generated/orciaSiteManifest.ts`, `docs/site-catalog/index.html`, `dist/orcia-site/index.html` | Régénération via `pnpm site:sync` (`65` capacités, `64` `runtime`) | `Terminé` |

### 3.2 Résultats Chiffrés, Métriques & Qualité
- **Campagne E2E Desktop figée (`--project=desktop-cockpit`, `e2e-campaign-epic-24/`, `pnpm db:reset` Jour 0, `0` `ORCIA_E2E_SEED_FIXTURES`, `--retries=0 --max-failures=0`, durée `719 690,61 ms` = `11,99 min`)** :
  - **`52 passed / 0 failed / 0 timedOut / 3 skipped (mobile-only) / 0 flaky`** sur `55` scénarios (`24/24` specs `100 % PASS`, progression **`+8`** vs Epic 23 `44/52`).
  - **`61 / 61` captures PNG `< 450 KB`** (`55` états finaux + `6` jalons dont `milestone-gates-hitl-drawer.png` `265 728` B, `milestone-ontology-tripartite-waivers.png` `238 251` B, `milestone-vsm-11-steps.png` `253 262` B ; max `274 576` B).
- **Contre-audit croisé Sally × Winston (`bmad-architect-worker`)** :
  - Verdict **`Case A — Clôture Epic 24 autorisée sans Epic 25`** : **`0 P0`, `0 P1`, `3 P2` (`UX24-01..03` $\rightarrow$ `ACTION_ITEM-24.1`), `4 P3` (`UX24-04..07` + P3 Architecture $\rightarrow$ `ACTION_ITEM-24.2`)** ; `6/6` `USER24-BUG-1..6`, `17/17` `UX23-*` et `12/12` `ARCH24-*` vérifiés.
- **Registre `docs/product/capabilities.yaml` (`65` capacités `live`)** :
  - **`64 / 65` `verification: runtime`** (`61` `feature` + `3` `foundation` vérifiées au `2026-11-20`) ; **`1` `verification: failed_e2e`** (`CAP-042` Mobile Companion maintenue explicitement sur `ACTION_ITEM-23.6`).

### 3.3 Validation Complète `AD-17` & Gates de Clôture (Post-Édition Finale)
- **Pyramide Python (`AD-17`)** : `1039 passed, 0 failed` (`tests/unit`, `contract`, `conformance`, `evals`, `security`) + `92 passed, 0 failed` (`tests/integration` PG18 + Redis `testcontainers` sans override) ; couverture combinée **`packages/orcia-core` >= 90 % (`92,17 %`, `orcia_kernel/*` à `100,00 %`)**.
- **Suite JS/TS (`pnpm turbo run lint typecheck test`)** : `9/9` tâches vertes (`@orcia/api-client` `20` + `@orcia/ui` `135` + `@orcia/web` `242` = **`397` tests Vitest PASS**, incluant `e2e-testids-sync-audit.test.ts` & `zero-dead-buttons-and-silent-catches-audit.test.tsx`).
- **Garde-fous statiques, contrats & documentation** : `ruff check .` & `ruff format --check .` (`1315` fichiers), `mypy --strict packages/orcia-core packages/orcia-connectors apps/api apps/worker` (`574` fichiers, `0` erreur), `lint-imports` (`5/5` contrats sur `617` fichiers), `scripts/export_openapi.py --check` (`0-diff`), `lint_spine.py` (`0` finding), `scripts/check_implementation_docs.py` (`200/200` rapports), `pnpm site:sync && pnpm site:check` (`0` erreur, `65/65` capacités, `20/20` UJ) et `pre-commit run detect-secrets` (`0` alerte).
