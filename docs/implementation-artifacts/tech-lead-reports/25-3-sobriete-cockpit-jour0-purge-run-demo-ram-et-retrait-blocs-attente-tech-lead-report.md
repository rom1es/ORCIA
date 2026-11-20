# Story 25.3 — Sobriété Cockpit Jour 0, Purge du Run Démo RAM (`marc.lead@orcia.io`) & Retrait des Blocs d'Attente à Vide

- **Date** : 2026-11-20
- **Story / Clé Sprint** : `25-3-sobriete-cockpit-jour0-purge-run-demo-ram-et-retrait-blocs-attente` (`Epic 25`)
- **Capacité(s)** : `CAP-005`, `CAP-023`, `CAP-060`, `CAP-100` — classification : `feature` / `ux` / `hygiène`
- **Auteur / Contexte** : Architecte (`Winston`), UX Designer (`Sally`) & Tech Lead — Purge définitive du run démo en mémoire RAM (`marc.lead@orcia.io` / `claims-engineering-delivery`), synchronisation stricte de `_runs_by_id` avec PostgreSQL 18, suppression de `DEFAULT_ARBITRATION_OPTIONS` et `DEFAULT_FALLBACK_WORKSPACE_ID` dans le Cockpit, affichage strictement conditionnel des cartes Human-Led (`HumanLedAnchorCard` / `ArbitrationTieBreakCard`) sur les seules actions réellement en attente en PG18, et suppression du bandeau `"Aucune décision en attente"` et du bloc `"Accès rapide à Mon Assistant"` (`AD-17`, `DESIGN.md`, `EXPERIENCE.md`).
- **Commits associés** : *(en cours d'implémentation)*

---

## 1. Analyse du Besoin & Étude d'Impact Tech Lead (Pré-Implémentation)

### 1.1 Contexte & Problématique
- **Comportement actuel** :
  1. `build_default_orchestration_setup_service()` dans `packages/orcia-core/src/orcia_core/orchestration/seeds.py` instancie en RAM un `WorkflowRunEntity` fictif attribué à `marc.lead@orcia.io` sur `orcia://workflows/claims-engineering-delivery` et `0192c4e0-0000-7000-8000-000000000201` (appelé au démarrage dans `core_and_lifespan.py` et lors de la création du 1er admin dans `bootstrap_accostage.py`).
  2. `hydrate_orchestration_runs_from_sql()` dans `apps/api/src/orcia_api/routers/_orchestration_sql_hydration.py` ajoute les lignes PostgreSQL 18 dans `svc._runs_by_id` sans purger les entrées RAM devenues obsolètes après un `pnpm db:reset` ou une suppression SQL.
  3. Côté Frontend (`apps/web/src/features/cockpit/`), `cockpitGovernanceHelpers.ts`, `useCockpitGovernanceController.ts` et `CockpitHumanLedGovernanceSection.tsx` embarquent les constantes fictives `DEFAULT_ARBITRATION_OPTIONS` (`"Option A — Taux Spot 15 min"`, `"Option B — Taux Bloqué 48h"`) et `DEFAULT_FALLBACK_WORKSPACE_ID`, montent systématiquement `<HumanLedAnchorCard>` et `<ArbitrationTieBreakCard>` dès qu'un run est détecté (même sans action humaine requise ou sans arbitrage réel en base), et conservent un bouton d'escalade factice alimenté par `DEFAULT_ARBITRATION_OPTIONS`.
  4. Côté `@orcia/ui` (`CockpitOrientationCards.tsx` / `StreamlinedCockpitView.tsx`), l'état à 0 décision affiche encore le bandeau `"Aucune décision en attente"` (`zeroDecisionsBanner`) et le bloc prompt rapide `"Accès rapide à Mon Assistant"` (`quickAssistantBox`).
- **Comportement attendu** :
  1. Zéro `WorkflowRunEntity` démo injecté en RAM au démarrage ou au bootstrap du 1er admin (`0` run par défaut).
  2. Synchronisation autoritative de `svc._runs_by_id` sur `workflow_runs` PostgreSQL 18 dans `hydrate_orchestration_runs_from_sql` (suppression immédiate de tout run absent de PG18).
  3. Exposition explicite des arbitrages en attente (`pending_arbitrations`) et signatures d'ancrage (`human_anchors`) persistés en PG18 sur `GET /api/v1/orchestration/runs/{run_id}/blackboard` pour éliminer tout fallback statique côté UI.
  4. Suppression intégrale de `DEFAULT_ARBITRATION_OPTIONS`, `DEFAULT_FALLBACK_WORKSPACE_ID` et `DEFAULT_WORKFLOW_URI` dans `apps/web/src/features/cockpit/`. Montage de `CockpitHumanLedGovernanceSection` uniquement lorsqu'un run actif réel en PG18 sur le périmètre courant requiert effectivement une ancre humaine non encore signée (`human_authored_required`) ou un arbitrage réel `WAITING_FOR_HUMAN_ARBITRATION` / `PENDING` (avec ses vraies options), et masquage automatique dès résolution en base.
  5. Retrait définitif du bandeau `"Aucune décision en attente"` / `"No pending decisions"` et du bloc `"Accès rapide à Mon Assistant"` / `"Quick access to My Assistant"` dans `CockpitOrientationCards.tsx` / `StreamlinedCockpitView.tsx` en conservant uniquement les 3 tuiles sobres (`Mon Assistant`, `Mes Processus`, `Mes Espaces`) et `<= 3` blocs à l'écran.

### 1.2 Exploration, Analyse d'Impact GitNexus, Factorisation & Dette Technique
- **Analyse d'Impact GitNexus (`gitnexus_context` & `gitnexus_impact` sur `/home/romain/Documents/Projects/ORCIA` + vérification exhaustive `git grep`)** :
  - Index GitNexus rafraîchi via `npx gitnexus analyze` (`42,315` nœuds, `231,692` arêtes, `717` clusters, `1,483` flux).
  - `build_default_orchestration_setup_service` (`packages/orcia-core/src/orcia_core/orchestration/seeds.py`) : appelé par `apps/api/src/orcia_api/dependencies/core_and_lifespan.py:250`, `apps/api/src/orcia_api/routers/bootstrap_accostage.py:248`, `apps/worker/src/orcia_worker/dbos_workflow_runner.py:57`, et dans les suites unitaires/evals (`test_durable_orchestration_and_blackboard.py`, `test_story_3_2b_persistence_dbos_otel.py`, `test_workflow_as_code_and_run_lock.py`, `test_orchestration_governance_gates_and_kill_switch_guard.py`, `test_story_3_3_assistant_agent_5_nodes_and_context_ports.py`, `test_assistant_and_ontology_evals.py`).
  - `hydrate_orchestration_runs_from_sql` (`apps/api/src/orcia_api/routers/_orchestration_sql_hydration.py`) : appelé par `apps/api/src/orcia_api/routers/orchestration.py:215` (`GET /api/v1/orchestration/state`) et réexporté par `orchestration_sql_wiring.py:322`.
  - `CockpitOrientationCards` (`packages/ui/src/primitives/CockpitOrientationCards.tsx`) : appelé uniquement par `StreamlinedCockpitView` (`packages/ui/src/primitives/StreamlinedCockpitView.tsx:112`). `StreamlinedCockpitView` est consommé par `CockpitFeaturePanel` (`apps/web/src/features/cockpit/index.tsx:235`).
  - `CockpitHumanLedGovernanceSection` (`apps/web/src/features/cockpit/CockpitHumanLedGovernanceSection.tsx`) : monté exclusivement par `CockpitFeaturePanel` (`apps/web/src/features/cockpit/index.tsx:276`).
  - Vérification `packages/orcia-core/src/orcia_core/permissions/_default_service.py` : `marc.lead@orcia.io` n'est injecté que sous `if seed_reference_personas:`, qui vaut `False` en runtime réel et `ORCIA_ENV=e2e` via `should_seed_test_personas_in_memory()`.
  - Vérification du badge `"Contexte actif"` : déjà purgé des composants UI de production lors de `Story 25.2` (confirmé par `git grep`).
- **Opportunités de Factorisation & Résorption de Dette Technique Naissante** :
  - `apps/api/src/orcia_api/routers/blackboard_and_engine.py` atteint `399` lignes (seuil `< 350` lignes) : découpage propre en extrayant les routes d'arbitrage / reprise / audit rapide dans `_blackboard_arbitration_routes.py` inclus sur `router` afin de maintenir chaque fichier `< 250` lignes tout en préservant `100 %` des routes et contrats OpenAPI.
  - Centralisation de la lecture SQL d'arbitrages/ancres dans `_orchestration_sql_hydration.py` (`read_sql_run_governance_if_available`) plutôt que de dupliquer des requêtes dans les routeurs.
  - `StreamlinedCockpitLabels` (`packages/ui/src/primitives/StreamlinedCockpitView.tsx`) : passage en optionnel des 4 champs supprimés de l'affichage (`zeroDecisionsBanner?`, `quickAssistantTitle?`, `quickAssistantPlaceholder?`, `quickAssistantCta?`) pour nettoyer `shell_and_search_labels.ts` sans casser la compilation `tsc --noEmit` des tests `@orcia/ui` avant leur mise à jour par le sous-agent QA.

---

## 2. Plan d'Implémentation

### 2.1 Schéma de Données & Migrations Alembic (`infra/migrations/versions/...`)
- Aucune migration Alembic requise : les tables `workflow_runs`, `step_executions`, `human_anchor_signatures` (`0015`), `human_arbitration_requests` (`0015`) et `blackboard_snapshots` existent déjà en PostgreSQL 18.

### 2.2 Noyau Métier Hexagonal, Orchestration & Workers (`packages/orcia-core/`, `apps/worker/`)
- `packages/orcia-core/src/orcia_core/orchestration/seeds.py` :
  - Supprimer l'instanciation fictive de `lead_user` (`marc.lead@orcia.io`) et l'appel `svc.instantiate_workflow_run(..., workflow_uri="orcia://workflows/claims-engineering-delivery", workspace_id="0192c4e0-0000-7000-8000-000000000201")` dans `build_default_orchestration_setup_service()`.
  - Le service démarre désormais à `0` run par défaut (`svc.runs == ()`).

### 2.3 Couche Backend API, Sécurité & Contrats (`apps/api/`, `packages/api-client/`)
- `apps/api/src/orcia_api/routers/bootstrap_accostage.py` :
  - Vérifier que `create_welcome_setup_first_admin()` (`L248`) réinitialise `app.state.orchestration_service` via `build_default_orchestration_setup_service(...)` à `0` run sans aucune réinjection démo.
- `apps/api/src/orcia_api/routers/_orchestration_sql_hydration.py` :
  - Dans `hydrate_orchestration_runs_from_sql()`, lorsque PG18 est connecté (`resolve_optional_dbos_uow(request)` non `None` et `list_workflow_runs_with_locks_sql(uow)` réussi), synchroniser exactement `svc._runs_by_id` et `svc._idempotency_index` avec les lignes PG18 en purgeant tout `run_id` absent de `sql_runs`.
  - Ajouter `read_sql_run_governance_if_available(request, svc, run_id)` retournant `(pending_arbitrations, human_anchors)` depuis PG18 (`list_human_arbitrations_sql` / `list_human_anchor_signatures_sql`) avec repli sur le service en mémoire uniquement hors PG18.
- `apps/api/src/orcia_api/schemas/blackboard.py` & `apps/api/src/orcia_api/routers/blackboard_and_engine.py` (+ `_blackboard_arbitration_routes.py`) :
  - Enrichir `RunBlackboardStateResponse` avec `pending_arbitrations: list[HumanArbitrationRequestSchemaItem]` et `human_anchors: list[HumanAnchorSignatureSchemaItem]` (valeurs par défaut `[]`) et alimenter ces champs dans `GET /api/v1/orchestration/runs/{run_id}/blackboard`.
  - Extraire les routes d'arbitrage, reprise et audit rapide dans `_blackboard_arbitration_routes.py` pour garder tous les fichiers `< 350` lignes.
- `packages/api-client/` :
  - Régénérer `openapi.json`, `src/generated/schema.ts` et les shards TS via `.venv/bin/python scripts/export_openapi.py` et vérifier `--check` (`0-diff`).

### 2.4 Interface Utilisateur & Expérience (`packages/ui/`, `apps/web/`)
- `packages/ui/src/primitives/CockpitOrientationCards.tsx` & `packages/ui/src/primitives/StreamlinedCockpitView.tsx` :
  - Retirer définitivement le bandeau `cockpit-zero-decisions-banner` (`"Aucune décision en attente"` / `"No pending decisions"`) et le bloc `cockpit-quick-assistant-box` (`"Accès rapide à Mon Assistant"` / `"Quick access to My Assistant"`).
  - Conserver uniquement les 3 tuiles raccourcis sobres (`Mon Assistant`, `Mes Processus`, `Mes Espaces`) respectant `disabledMenuKeys` et `onNavigateModule`.
- `apps/web/src/i18n/locales/shell_and_search_labels.ts` :
  - Retirer les 4 chaînes `zeroDecisionsBanner`, `quickAssistantTitle`, `quickAssistantPlaceholder`, `quickAssistantCta` (FR et EN).
- `apps/web/src/features/cockpit/cockpitGovernanceHelpers.ts` :
  - Supprimer intégralement `DEFAULT_ARBITRATION_OPTIONS`, `DEFAULT_FALLBACK_WORKSPACE_ID`, `DEFAULT_WORKFLOW_URI` et les titres codés en dur dans `formatOptionTitle`.
  - Ajouter une fonction pure d'analyse d'état réel `derivePendingGovernanceFromBlackboard(blackboard, workflow)` qui détermine :
    - s'il existe une étape `human_authored_required: true` non encore signée (`pendingAnchorStepKey`, `pendingAnchorSectionKey`, `pendingAnchorTitle`),
    - s'il existe une requête d'arbitrage en attente (`status === "PENDING"` dans `pending_arbitrations`, ou étape `WAITING_FOR_HUMAN_ARBITRATION` portant `options_matrix` réel avec `>= 2` options),
    - en retournant `hasPendingAction = Boolean(pendingAnchor || pendingArbitration)`.
- `apps/web/src/features/cockpit/useCockpitGovernanceController.ts` & `CockpitHumanLedGovernanceSection.tsx` & `apps/web/src/features/cockpit/index.tsx` :
  - Supprimer `handleRequestArbitration` / `ensureServerRun` / le bouton factice `cockpit-request-arbitration-btn`.
  - Dans `CockpitFeaturePanel` (`index.tsx`), interroger `GET /api/v1/orchestration/state` (filtré strictement sur les runs actifs non terminaux du périmètre courant) puis `GET /api/v1/orchestration/runs/{id}/blackboard` pour déterminer l'existence d'une action humaine réelle en attente (`pendingGovernanceRunId`).
  - Ne monter `<CockpitHumanLedGovernanceSection>` que si `pendingGovernanceRunId !== null`.
  - À l'intérieur de `CockpitHumanLedGovernanceSection`, n'afficher `<HumanLedAnchorCard>` que si une ancre requise est en attente, n'afficher `<ArbitrationTieBreakCard>` (avec les vraies options de l'API, sans fallback fictif) que si un arbitrage `PENDING` est en attente, et retourner `null` dès que tout est résolu en PG18.
  - Après signature d'ancre (`signHumanAnchor`) ou résolution d'arbitrage (`resolveHumanArbitration`), réhydrater immédiatement depuis PG18 et notifier le parent (`onGovernanceStateChanged`) afin de faire disparaître la carte résolue (ou toute la section si plus rien n'est en attente).

### 2.5 Analyse d'Impact sur la Pyramide des Tests (`AD-17` — Transmission au sous-agent QA indépendant)
- **Couche 1a (Unitaires Python `tests/unit/`)** :
  - `tests/unit/test_durable_orchestration_and_blackboard.py` (`L53, L104, L170, L200`) et `tests/unit/test_story_3_2b_persistence_dbos_otel.py` (`L335`) devront instancier explicitement un run dans les tests au lieu de supposer `svc.runs[0]` pré-peuplé.
- **Couche 1b (Frontend TS `Vitest`)** :
  - `packages/ui/src/__tests__/four-zone-shell-and-cockpit.test.tsx` (`L207-L210`) et `packages/ui/src/__tests__/story-23-5-sobriety-and-login-brand.test.tsx` (`L217-L221`) à adapter suite au retrait de `cockpit-zero-decisions-banner` et `cockpit-quick-assistant-box`.
  - `apps/web/src/__tests__/story-23-5-sobriety-and-citations-wiring.test.tsx` (`L120-L138`) à adapter aux nouveaux critères de montage conditionnel sur action humaine en attente.
- **Couche 2 (Intégration Verticale `HTTP ➔ PG18`) & Couche 3 (Contrats OpenAPI `0-diff`)** :
  - Vérification `scripts/export_openapi.py --check` (`0-diff`) et tests d'intégration `hydrate_orchestration_runs_from_sql` / `get_run_blackboard_state`.
- **Couche 5 (E2E Playwright `apps/web/e2e/`)** :
  - `apps/web/e2e/03-human-led-anchor-and-arbitration.spec.ts` (`L126` : bouton `cockpit-request-arbitration-btn` supprimé et disparition des cartes après résolution) et `apps/web/e2e/19-orchestration-whatif-replay-and-gates.spec.ts` (`L49-L64`) à aligner par le sous-agent QA.

---

## 3. Bilan des Modifications & Résultats (Post-Implémentation)

### 3.1 Fichiers Développés & Modifiés

| Fichier | Rôle / Nature de l'évolution |
| :--- | :--- |
| `packages/orcia-core/src/orcia_core/orchestration/seeds.py` | Purge du run démo RAM (`marc.lead@orcia.io` / `claims-engineering-delivery`) dans `build_default_orchestration_setup_service()` (`svc.runs == ()`). |
| `apps/api/src/orcia_api/routers/_orchestration_sql_hydration.py` | Synchronisation autoritative de `svc._runs_by_id` et `_idempotency_index` sur PostgreSQL 18 (purge des runs absents de PG18) + `read_sql_run_governance_if_available()`. |
| `apps/api/src/orcia_api/schemas/blackboard.py` | Ajout de `pending_arbitrations` et `human_anchors` à `RunBlackboardStateResponse`. |
| `apps/api/src/orcia_api/routers/blackboard_and_engine.py` | Alimentation de `pending_arbitrations` & `human_anchors` sur `GET /api/v1/orchestration/runs/{run_id}/blackboard` + découpage `< 250` lignes via `_blackboard_arbitration_routes.py`. |
| `apps/api/src/orcia_api/routers/_blackboard_arbitration_routes.py` | Sous-routeur extrait des routes d'arbitrage, reprise et audit rapide (`222` lignes). |
| `apps/api/src/orcia_api/routers/orchestration_sql_wiring.py` | Réexport de `read_sql_run_governance_if_available`. |
| `packages/api-client/openapi.json` & `src/generated/schema.ts` | Régénération SDK OpenAPI 3.1 (`0-diff`). |
| `packages/ui/src/primitives/CockpitOrientationCards.tsx` | Retrait définitif de `cockpit-zero-decisions-banner` et `cockpit-quick-assistant-box` ; conservation des 3 tuiles sobres (`Mon Assistant`, `Mes Processus`, `Mes Espaces`). |
| `packages/ui/src/primitives/StreamlinedCockpitView.tsx` | Retrait des 4 champs dépréciés dans `StreamlinedCockpitLabels` et `onOpenAssistant` dans `StreamlinedCockpitViewProps`. |
| `apps/web/src/i18n/locales/shell_and_search_labels.ts` | Retrait des chaînes `zeroDecisionsBanner`, `quickAssistantTitle`, `quickAssistantPlaceholder`, `quickAssistantCta` (FR/EN). |
| `apps/web/src/features/cockpit/cockpitGovernanceHelpers.ts` | Suppression de `DEFAULT_ARBITRATION_OPTIONS`, `DEFAULT_FALLBACK_WORKSPACE_ID` et `DEFAULT_WORKFLOW_URI` ; ajout de `derivePendingGovernanceFromBlackboard()`. |
| `apps/web/src/features/cockpit/useCockpitGovernanceController.ts` & `CockpitHumanLedGovernanceSection.tsx` & `index.tsx` | Montage strictement conditionnel des cartes Human-Led (`HumanLedAnchorCard` / `ArbitrationTieBreakCard`) sur les actions réelles en attente PG18, masquage dès résolution, et rattachement conditionnel de `CockpitUpstreamChallengePanel` sur run à ancrage signé ou alerte d'obsolescence. |
| `tests/unit/test_durable_orchestration_and_blackboard.py`, `test_story_3_2b_persistence_dbos_otel.py`, `test_workflow_as_code_and_run_lock.py`, `test_story_25_3_cockpit_zero_demo_run.py` | Alignement sur 0 run au démarrage et couverture unitaire Story 25.3 (`svc.runs == ()`, purge RAM, `pending_arbitrations`/`human_anchors`). |
| `tests/integration/api/test_story_25_3_orchestration_zero_demo_postgres18.py` | Intégration verticale `create_app()` PG18 + Redis (`testcontainers`, sans `dependency_overrides`), sécurité `403 ERR_OBSERVER_MODE_READ_ONLY`, `SELECT` PG18 et purge RAM après suppression SQL. |
| `packages/ui/src/__tests__/four-zone-shell-and-cockpit.test.tsx`, `story-23-5-sobriety-and-login-brand.test.tsx` | Adaptation Vitest `@orcia/ui` suite au retrait des blocs d'attente. |
| `apps/web/src/__tests__/setup/mockBackendState.ts`, `orchestrationRunsMockHandlers.ts`, `orchestration-rewind-modal-and-gates-view.test.tsx`, `story-23-5-sobriety-and-citations-wiring.test.tsx`, `story-25-3-cockpit-empty-vs-real-pending.test.tsx`, `anti-jargon-and-secrets-ui-audit.test.ts` | Réalignement harnais OpenAPI Vitest et suite `RouterProvider` réelle Story 25.3 (`0` bloc d'attente à vide, montage sélectif ancrage/arbitrage réels, disparition après résolution). |
| `apps/web/e2e/03-human-led-anchor-and-arbitration.spec.ts`, `19-orchestration-whatif-replay-and-gates.spec.ts`, `21-assistant-citations-v5-audit-help-showcase.spec.ts` | Validation E2E sobriété Jour 0, ancrage/arbitrage PG18 réel et disparition après F5, challenge What-If et Zone 4. |
| `docs/product/capabilities.yaml`, `docs/implementation-artifacts/sprint-status.yaml` | Enregistrement de `_blackboard_arbitration_routes.py` sous `CAP-023` et passage de `25-3` à `done`. |

### 3.2 Métriques, Couverture & Validation des 5 Couches `AD-17`

| Vérification | Périmètre | Résultat exact |
| :--- | :--- | :--- |
| **Analyse statique Python** | `.venv/bin/ruff check .`, `ruff format --check .` (`1332` fichiers), `mypy --strict` (`578` fichiers), `lint-imports` (`621` fichiers), `export_openapi.py --check`, `lint_spine.py` | **0 erreur** (`5/5` contrats `AD-19`/`AD-20` KEPT, `0-diff` OpenAPI 3.1, `0` finding spine) |
| **Couche 1a — Unitaires Python & Couverture** | `.venv/bin/pytest tests/unit tests/security tests/evals -ra` | **`1044 passed`** (0 failed) ; couverture ciblée Story 25.3 (`seeds.py` `93 %`, `blackboard_and_engine.py` `100 %`, `schemas/blackboard.py` `100 %`, `_orchestration_sql_hydration.py` `87 %`, `_blackboard_arbitration_routes.py` `86 %`) : **`94.07 %`** ($\ge 90\%$ PASS) |
| **Couche 2 & Sécurité — PG18 Réel (`testcontainers`)** | `tests/integration/api/test_story_25_3_orchestration_zero_demo_postgres18.py` sur `create_app()` sans `dependency_overrides` | **PASS** (`runs == []` Jour 0, cold restart PG18, `SELECT` `human_anchor_signatures` & `human_arbitration_requests`, purge RAM post-`DELETE`, rejet `403 ERR_OBSERVER_MODE_READ_ONLY`) |
| **Couche 1b — Frontend TS (`Turborepo` / `Vitest`)** | `pnpm turbo run lint typecheck test` (`@orcia/api-client`, `@orcia/ui`, `@orcia/web`) | **`9/9` tâches vertes** (`3/3` fichiers `@orcia/api-client`, `34/34` fichiers / `136/136` tests `@orcia/ui`, `64/64` fichiers / `251/251` tests `@orcia/web`) |
| **Couche 5 — E2E Playwright (`desktop-cockpit`)** | `shell.spec.ts`, `00-stack-smoke.spec.ts`, `01-day0-boot-and-f5-persistence.spec.ts`, `03-human-led-anchor-and-arbitration.spec.ts`, `19-orchestration-whatif-replay-and-gates.spec.ts`, `21-assistant-citations-v5-audit-help-showcase.spec.ts` | **`15 passed, 0 failed`** (pile éphémère PG18 + Redis `ORCIA_E2E_CAMPAIGN_DIR=/tmp/orcia-e2e-story-25-3`) |
| **GitNexus (`detect_changes` post-index)** | `npx gitnexus analyze` (`42,412` nœuds, `239,031` arêtes) + `detect_changes(scope: "all")` | `13` symboles modifiés détectés, `0` référence résiduelle à `DEFAULT_ARBITRATION_OPTIONS` / `Taux Spot 15 min` / `Taux Bloqué 48h` / `cockpit-zero-decisions-banner` / `cockpit-quick-assistant-box` / run démo `marc.lead@orcia.io` dans `packages/` et `apps/` (hors `tests/`). |
| **Catalogue Produit & Docs** | `sync_site_catalog.py --check` & `check_implementation_docs.py` | **0 erreur** |
