# Rapport Tech Lead — Story 24.2 : Déclencheurs UUIDv7 sans Collision, Waivers `await`, ADN Starlark PG18 & Purge `default-ws`

- **Story :** `24-2-triggers-uuidv7-sans-collision-waivers-await-adn-pg18-et-fin-default-ws` (Epic 24 — Vague 0 `P0/P1`)
- **Date :** 2026-11-20
- **Statut :** `Terminé (`done`)` (implémenté & validé 5 couches `AD-17`)
- **Plan directeur :** [`sprint-change-proposal-2026-11-20-epic-24-remediation-plan.md`](../../planning-artifacts/sprint-change-proposal-2026-11-20-epic-24-remediation-plan.md)
- **Références remédiées :** `REM24-03`, `REM24-04`, **`USER24-BUG-6`** | Échecs E2E `20#2 #49`, `17#3 #40` | Constat `UX23-06` (`P1`) | Diagnostics `ARCH24-03`, `ARCH24-04`
- **Capacité(s) (`capabilities.yaml`) :** `CAP-010`, `CAP-011`, `CAP-081`, `CAP-084`, `CAP-180`, `CAP-201` (`6` capacités Desktop `failed_e2e`)
- **Classification :** `feature` (intégrité UUIDv7, persistance PG18 & hygiène Jour 0)

---

## 1. Analyse du Besoin & Étude d'Impact Tech Lead

### 1.1 Contexte & Critères d'Acceptation
Deux échecs structurants bloquent la création séquentielle d'automatisations et la gouvernance d'espace :
1. **Collision UUIDv7 sur triggers séquentiels (`20#2 #49` / `ARCH24-03`)** : dans `packages/orcia-core/src/orcia_core/orchestration/_triggers_lifecycle_ops.py:46-47`, la clé auto-générée vaut `f"trg-{tid[:8]}"`. Or les `8` premiers caractères hexadécimaux d'un `UUIDv7` encodent les `32` bits MSB de l'horodatage (`65,5 s` de granularité), provoquant une collision immédiate lors de deux créations séquentielles dans la même fenêtre temporelle. Par ailleurs, `WorkflowTriggersModal` ne permet pas la saisie optionnelle d'un `trigger_key`.
2. **Waivers non attendus, ADN Starlark volatil & résidus `"default-ws"` (`17#3 #40` / `ARCH24-04` / `UX23-06`)** :
   - Dans `WorkspaceDnaAndWaiversSection.tsx` (`277` L), les appels `registerWorkspaceExceptionWaiver` et `compileDnaStarlark` ne sont pas `await` correctement avec état `submitting` et rafraîchissement depuis PG18 ; lorsque `0` espace existe, la section ne doit jamais être montée avec des identifiants factices.
   - `DnaStarlarkAndGlossaryLifecycleService` garde en RAM les mécanismes Starlark signés sans les persister durablement en PG18 (`dependencies/workspace_and_packs.py`).
   - Des fallbacks factices `"default-ws"`, `"ws-claims-alpha"`, `"ws-mon-compte"` subsistent dans le code applicatif/UI en contradiction avec la vérité terrain Jour 0 (`workspaces/index.tsx:176-184` monte `<WorkspaceDnaAndWaiversSection>` même si `targetWorkspace === null`, affichant `default-ws` à `0` espace — **`USER24-BUG-6`**).
   - De plus, `packages/ui/src/primitives/WorkspaceFiveTabsAndExternalRebaseView.tsx:148-276` ne branche jamais son panneau principal sur `activeTab`, affichant en permanence `2. DOCUMENTS & SOURCES` même lorsque l'onglet `5. Membres & Équipe` est sélectionné (`USER24-BUG-6`).

**Critères d'acceptation :** zéro collision `trigger_key` sur créations en rafale (`< 1 s`), `await` + `submitting` + rechargement PG18 sur waivers et ADN Starlark, persistance PG18 des mécanismes signés, `0` occurrence runtime de `"default-ws"` / `"ws-claims-alpha"` / `"ws-mon-compte"`, non-montage complet du panneau détail/ADN dans `/spaces` lorsque `0` espace existe, commutation réelle du contenu dans `WorkspaceFiveTabsAndExternalRebaseView` selon les 5 onglets (`activeTab`), et succès E2E `20#2 #49` + `17#3 #40`.

### 1.2 Analyse d'Impact GitNexus (`repo: "/home/romain/Documents/Projects/ORCIA"`)
- `TriggerDispatcherService` (`packages/orcia-core/src/orcia_core/orchestration/triggers_dispatcher.py`) : `impactedCount: 261`, `risk: "CRITICAL"`, `epistemic: "exact"` (`direct: 242`, `d=2: 19`, `processes_affected: 32`, `modules_affected: 20`). Inspection directe `_triggers_lifecycle_ops.py:36-67` (`261` L) confirmant `tid[:8]` aux lignes `46-47`.
- `DnaStarlarkAndGlossaryLifecycleService` (`packages/orcia-core/src/orcia_core/orchestration/dna_starlark_and_glossary_lifecycle.py:89-447`) : `impactedCount: 400`, `risk: "CRITICAL"`, `epistemic: "exact"` (`direct: 376`, `d=2: 22`, `d=3: 2`, `processes_affected: 83`, `modules_affected: 20`).
- Impact API (`gitnexus api_impact`) :
  - `apps/api/src/orcia_api/routers/workflow_triggers.py` (`8` routes HTTP).
  - `apps/api/src/orcia_api/routers/workspace_governance.py` (`7` routes HTTP) + `apps/api/src/orcia_api/dependencies/workspace_and_packs.py` (`189` L).

### 1.3 Opportunités de Factorisation & Contrôle de Volumétrie (`< 350` L)
- **Découpage obligatoire `dna_starlark_and_glossary_lifecycle.py` (`447` L > seuil `400` L)** : séparer le cycle de vie glossaire/ontologie de la compilation/persistance Starlark ADN en deux modules cohésifs `< 250` L (avec adaptateur SQL dédié sous `_internal/`).
- **Primitive commune `uuid_utils` suffixe entropique** : utiliser la partie aléatoire/finale d'UUIDv7 (`tid` complet ou `tid.replace("-", "")[-12:]`) ou un générateur d'identifiant court dans `orcia_kernel` afin d'éliminer tout tronquage sur MSB temporels dans le codebase.

---

## 2. Plan d'Implémentation

### 2.1 Couche Données & Migrations Alembic / PostgreSQL 18
1. Vérifier les colonnes actuelles de `ontology_relations` (`mechanism_payload_jsonb` ou table dédiée aux mécanismes Starlark signés) et des tables de waivers d'espace ; ajouter au besoin une révision Alembic `Expand` en SQL brut garantissant la persistance du payload Starlark compilé et signé par workspace en PG18.
2. Vérifier la contrainte d'unicité de `trigger_key` en base pour supporter soit la clé fournie par l'utilisateur (`409` RFC 9457 explicite si déjà prise), soit la clé auto-générée sans collision temporelle.
3. Mettre à jour `_first_boot_reset_guards.py` si une nouvelle table mutable est introduite.

### 2.2 Noyau Hexagonal (`orcia-kernel` / `orcia-core`) & Workers
1. Corriger `_triggers_lifecycle_ops.py:46-47` (`execute_create_trigger`) : générer `f"trg-{tid}"` ou `f"trg-{tid.replace('-', '')[-12:]}"` (jamais `tid[:8]`).
2. Découper `dna_starlark_and_glossary_lifecycle.py` (`447` L $\rightarrow$ `< 300` L par module) et persister les mécanismes Starlark compilés/signés en PG18 via port + adaptateur SQL injecté dans `dependencies/workspace_and_packs.py` (`189` L).
3. Purger toute référence ou fallback `"default-ws"`, `"ws-claims-alpha"` et `"ws-mon-compte"` du noyau et vérifier la gestion stricte des erreurs RFC 9457 (`ERR_WORKSPACE_REQUIRED` / `404` / `409`).

### 2.3 Backend FastAPI (`apps/api`) & Contrat OpenAPI (`packages/api-client`)
1. Exposer le champ optionnel `trigger_key` sur le schéma de requête de création de trigger dans `apps/api/src/orcia_api/schemas/` (`workflow_triggers.py` `8` routes) et régénérer `@orcia/api-client` (`0-diff`).
2. Vérifier les endpoints `workspace_governance.py` (`7` routes) pour retourner la liste des waivers et l'état Starlark directement relus depuis PG18 (`Depends(...)` injecté depuis `dependencies/workspace_and_packs.py`).

### 2.4 Interface SPA Vite + TanStack Router & Design System (`@orcia/ui` / `apps/web`)
1. Exposer le champ optionnel `trigger_key` dans `WorkflowTriggersModal` avec validation et gestion d'erreur visible (`[role="alert"]`, `UX23-06`).
2. Dans `apps/web/src/features/workspaces/WorkspaceDnaAndWaiversSection.tsx` (`277` L), `workspaces/index.tsx` (`224` L) et `packages/ui/src/primitives/WorkspaceFiveTabsAndExternalRebaseView.tsx` (`278` L) :
   - Ajouter `await` + état `submitting` + rechargement PG18 immédiat sur `registerWorkspaceExceptionWaiver` et `compileDnaStarlark`.
   - Supprimer tout fallback `"default-ws"` (`L45`, UUID hardcodé `L194`) / `"ws-claims-alpha"` / `"ws-mon-compte"` ; ne jamais monter `WorkspaceDnaAndWaiversSection` dans `workspaces/index.tsx` lorsque `targetWorkspace === null` (`0` espace, afficher uniquement l'état vide guidant vers la création d'espace, **`USER24-BUG-6`**).
   - Brancher le rendu du panneau principal de `WorkspaceFiveTabsAndExternalRebaseView.tsx` sur `activeTab` (`OVERVIEW`, `DOCUMENTS_SOURCES`, `DELIVERABLES_ARTIFACTS`, `GLOSSARY_RULES`, `MEMBERS_TEAM`) afin que chaque onglet affiche son contenu propre (et non plus `2. DOCUMENTS & SOURCES` en permanence sous l'onglet 5).

### 2.5 Stratégie de Vérification & 5 Couches de Tests (`AD-17`)
- **Couche 1 (Unitaire >= 90 %)** : test de non-collision sur `1 000` créations de triggers dans la même milliseconde ; tests unitaires split `dna_starlark_and_glossary_lifecycle` et interdiction AST/grep `"default-ws"` en prod.
- **Couche 2 (Intégration `testcontainers` PG18 réel)** : création séquentielle de triggers et enregistrement waivers + ADN Starlark via `create_app()` réel $\rightarrow$ `SELECT` PG18 $\rightarrow$ relecture à froid.
- **Couche 3 (Composants React)** : test Vitest `WorkspaceDnaAndWaiversSection` (vérifiant l'attente `await`, l'état `submitting`, le non-montage si `0` workspace et l'affichage `[role="alert"]` sans catch silencieux).
- **Couche 4 (E2E Playwright ciblé)** : `20-process-studio-and-triggers.spec.ts` (`20#2 #49`) et `17-workspace-waivers-and-dna-starlark.spec.ts` (`17#3 #40`) avec rechargement `F5`.
- **Couche 5 (Statique & Sécurité)** : `ruff`, `mypy --strict`, `lint-imports`, `pnpm turbo run lint typecheck test`, `pnpm site:check`.

---

## 3. Bilan des Modifications & Résultats

> **Statut :** `Terminé (`done`)` — Implémentation complète, 5 couches `AD-17` validées (unitaires + `testcontainers` PG18/Redis 7.4 sans override + Vitest `<RouterProvider>` + Playwright E2E `5/5` `--retries=0`), ré-indexation GitNexus (`npx gitnexus analyze` + `gitnexus_detect_changes`) et synchronisation `pnpm site:sync && pnpm site:check` exécutées.

### 3.1 Tableau des Fichiers Créés & Modifiés

| Fichier / Composant | Action Réalisée | Statut |
|---|---|---|
| `infra/migrations/versions/20261120_2402_story_24_2_workspace_dna_mechanisms_pg18.py`, `infra/scripts/maintenance/_first_boot_reset_guards.py` | Révision Alembic `20261120_2402` (`workspace_dna_mechanisms` PG18 avec `UNIQUE (workspace_id, rule_id)`, index & `downgrade()` réversible) + purge Jour 0 dans `ORDERED_MUTABLE_TABLES_TO_CLEAR` | `Terminé` |
| `packages/orcia-core/src/orcia_core/orchestration/_triggers_lifecycle_ops.py`, `triggers_dispatcher.py` | Fix collision `tid[:8]` $\rightarrow$ `tid.replace("-", "")[-12:]` (bits aléatoires UUIDv7, zéro collision sur rafale) + `record_alert_delivery_async` (`trigger_webhook_deliveries`) | `Terminé` |
| `packages/orcia-core/src/orcia_core/orchestration/{_dna_starlark_models.py,_dna_starlark_compiler.py,_dna_glossary_ops.py,_internal/sql_dna_mechanisms.py,dna_starlark_and_glossary_lifecycle.py}` | Découpage `< 300` L de `dna_starlark_and_glossary_lifecycle.py` (`447` L $\rightarrow$ `5` modules) + port `StarlarkMechanismRepositoryPort` + `SqlStarlarkMechanismRepository` PG18 + `strict_sql` | `Terminé` |
| `packages/orcia-core/src/orcia_core/orchestration/{workspace_governance_and_rebaser.py,pack_builder_processes.py}`, `bootstrap/rag_seeds.py`, `rag/{__init__.py,two_speed_search.py}` | `strict_sql=False` waivers + purge intégrale `"default-ws"`, `"ws-claims-alpha"`, `"ws-mon-compte"` en production (`0` occurrence runtime) | `Terminé` |
| `packages/orcia-core/src/orcia_core/rag/_internal/{sql_state_queries.py,sql_rag_writes.py,sql_tripartite_writes.py,sql_repository.py}` | Round 3 PG18 RAG & Tripartite : lectures `list_documents_pg`/`list_tripartite_edges_pg`/`list_stale_alerts_pg` + écritures `upsert_document_bundle_pg` (`AD-24.7` vecteurs `NULL` sans modèle actif), `upsert_tripartite_edges_pg` & `upsert_stale_alert_pg` | `Terminé` |
| `apps/api/src/orcia_api/dependencies/workspace_and_packs.py`, `routers/{dna_and_glossary.py,workspace_governance.py,workflow_triggers.py,ontology_and_rag.py,ontology_rag_helpers.py,_ontology_promotions_helpers.py,settings_and_studio.py,workspace_datasources.py,portal_and_help.py,assistant_workspace_governance.py,assistant_llm_bridge.py}`, `schemas/{auth_and_org.py,ontology_and_rag.py}`, `packages/api-client/` | Câblage DI `SqlStarlarkMechanismRepository` + `strict_sql=True`, routes `GET/POST /dna-mechanisms/{compile,activate}`, slug dynamique `five-tabs`, dédup `POST /triggers/alerts`, persistance PG18 `rag/index-db-ddl`, `tripartite/audit-doc-vs-code`, `settings/connectors/ingest`, `datasources/{id}/sync`, purge workspaces fantômes dans `load_ontology_topology` PG18, et SDK OpenAPI 3.1 `0-diff` | `Terminé` |
| `packages/ui/src/primitives/{WorkspaceFiveTabsPanels.tsx,WorkspaceFiveTabsAndExternalRebaseView.tsx,DnaStarlarkCompilerAndGlossaryLifecycleView.tsx,WorkflowTriggersTypes.ts,WorkflowTriggersModal.tsx,WorkflowTriggerCard.tsx}`, `packages/ui/src/shell/{OntologyTripartiteAndStaleSection.tsx,OntologyAndKbExplorerPanel.tsx,types.ts}` | Fix `USER24-BUG-6` (split `280` L + commutation réelle des 5 onglets dont `MEMBERS_TEAM` $\rightarrow$ `workspace-members-panel`), `submitting` waivers/ADN, `trigger-create-key-input` & badge clé, formulaire `tripartite-audit-form` anti-LastPass visible à `0` concept | `Terminé` |
| `apps/web/src/features/workspaces/{index.tsx,WorkspaceDnaAndWaiversSection.tsx}`, `features/ontology/index.tsx`, `components/ontologyApiBridge.ts`, `features/processes/studio/{useWorkflowTriggers.ts,WorkflowFiveBlocksCanvas.tsx}`, `features/settings/packs/PacksRegistryPage.tsx`, `i18n/locales/{fr.ts,en.ts,workflow_triggers_labels.ts,governance_and_packs_labels.ts}`, `lib/formatRfc9457ErrorToBanner.ts` | Non-montage `WorkspaceDnaAndWaiversSection` à `0` espace + `await`/`submitting`/rechargement PG18 + fin `"default-ws"`/`"ws-mon-compte"`, `ERR_TRIGGER_DUPLICATE_KEY` (`[role="alert"]`), câblage `handleAuditDocVsCode` sur workspace réel + `GET /ontology-rag/state`, suppression `"PAY-142"` | `Terminé` |
| `tests/unit/test_story_24_2_triggers_dna_pg18.py`, `tests/integration/test_story_24_2_triggers_dna_waivers_postgres18.py`, `packages/ui/src/__tests__/story-24-2-five-tabs-and-triggers-modal.test.tsx`, `apps/web/src/__tests__/{story-24-2-spaces-day0-dna-waivers-and-triggers.test.tsx,vitestOntologyMockHandlers.ts,epics-14-15-process-studio-v2-and-declarative-packs.test.tsx,declarative-packs-and-durable-wizards-f5.test.tsx,i18n-and-shell.test.tsx,setup/*}`, `apps/web/e2e/17-workspace-sources-codegraph-dna-and-ontology.spec.ts` | Suite 5 couches `AD-17` : `1 000` triggers/ms, audit statique `"default-ws"`, handlers Vitest `dna-mechanisms`/`trigger_key 409`/`ontology-rag/state`/`audit-doc-vs-code`, tests `RouterProvider` & PG18 `testcontainers`, et E2E `17#3` (`SOURCE_CODE` + `tripartite-audit-form` + `reloadColdFromPg` + SQL PG18) | `Terminé` |

### 3.2 Synthèse des Vérifications `AD-17` (5 Couches) & GitNexus
- **Couche 1a (Unitaires Python & Audits) :**
  - `tests/unit/test_story_24_2_triggers_dna_pg18.py` + suites connexes (`test_story_7_2_triggers_and_self_trigger_guard.py`, `test_story_7_2_triggers_coverage.py`, `test_epic_11_story_11_2_dna_starlark_and_glossary.py`, `test_story_22_2_waivers_and_root_invitations.py`) : **`28 passed in 29.65s`** (`1 000` créations de triggers même ms avec `0` collision, `409 TriggerDuplicateKeyError`, split Starlark & 2-Pass glossary, `strict_sql=True` fail-closed, audit statique `0` occurrence `"default-ws"`/`"ws-claims-alpha"`/`"ws-mon-compte"` en prod, dédup `record_alert_delivery_async`, helpers `sql_rag_writes` / `sql_tripartite_writes`).
- **Couche 1b (Composants React Vitest sans `isJsdom`, `RouterProvider` réel) :**
  - `pnpm turbo run lint typecheck test` : **`9 successful, 9 total`** (`@orcia/web:test` **`57 passed (57)`, `225 passed (225)`**, `@orcia/ui:test` **`31` fichiers**, `@orcia/api-client:test` **`3` fichiers** — couvrant `story-24-2-five-tabs-and-triggers-modal.test.tsx`, `story-24-2-spaces-day0-dna-waivers-and-triggers.test.tsx` et `i18n-and-shell.test.tsx`).
- **Couche 2 (Intégration `testcontainers` PG18 + Redis 7.4 sur Composition Root `create_app()` sans override) :**
  - `tests/integration/test_story_24_2_triggers_dna_waivers_postgres18.py` : **`2 passed in 58.81s`** (`alembic upgrade 20261120_2402 -> downgrade 20261120_2401 -> upgrade head`, triggers séquentiels `LOG_SINK_ALERT` + `409 ERR_TRIGGER_DUPLICATE_KEY`, `POST /api/v1/triggers/alerts` `trigger_webhook_deliveries`, compilation/activation/évaluation ADN Starlark `workspace_dna_mechanisms`, waivers `workspace_exception_waivers`, `SOURCE_CODE` sync `AD-24.7` `COUNT(embedding) == 0`, `rag/index-db-ddl`, `tripartite/audit-doc-vs-code`, `evict-memory-caches`, `SELECT` direct PG18, relecture à froid sur 2e instance `create_app()`, et purge `09_reset_db_first_boot.py`).
  - Couverture combinée ciblée Story 24.2 (`unit` `28 passed` + `integration PG18` `2 passed`, `coverage combine --fail-under=90`) : **`90 %`** (`574` stmts, `44` miss, `138` branches — `_dna_starlark_models.py` `100 %`, `sql_state_queries.py` `100 %`, `_dna_glossary_ops.py` `99 %`, `dna_starlark_and_glossary_lifecycle.py` `99 %`, `sql_dna_mechanisms.py` `94 %`, `_dna_starlark_compiler.py` `93 %`, `_triggers_lifecycle_ops.py` `93 %`, `sql_tripartite_writes.py` `91 %`, `sql_rag_writes.py` `90 %`, `dna_and_glossary.py` `82 %`, `_ontology_promotions_helpers.py` `47 %` sur sous-ensemble Story 24.2).
- **Couche 3 (Statique, Contrats & Gouvernance) :**
  - `.venv/bin/ruff check .` (`All checks passed!`), `.venv/bin/ruff format --check .` (`1300 files already formatted`), `.venv/bin/mypy --strict packages/orcia-core packages/orcia-connectors apps/api apps/worker` (`Success: no issues found in 569 source files`), `.venv/bin/lint-imports` (`Contracts: 5 kept, 0 broken` sur `612` fichiers / `4406` dépendances), `.venv/bin/python scripts/export_openapi.py --check` (`0-diff`).
- **Couche 5 (Playwright E2E réel `--project=desktop-cockpit --retries=0`) :**
  - `ORCIA_E2E_CAMPAIGN_DIR=/tmp/orcia-e2e-story-24-2 pnpm --filter @orcia/web exec playwright test e2e/17-workspace-sources-codegraph-dna-and-ontology.spec.ts e2e/20-process-studio-v2-finops-and-log-sink.spec.ts --project=desktop-cockpit --retries=0` : **`5 passed (2.4m)` (`0 failed`)** — `17#1` (`21.0s`), `17#2` (`21.0s`), `17#3` (`25.0s`, `workspace_dna_mechanisms >= 1`, `workspace_exception_waivers`, `kb_documents >= 1`, `tripartite_trace_edges >= 1` & survie `reloadColdFromPg`), `20#1` (`25.1s`), `20#2` (`26.9s`, rafale `LOG_SINK_ALERT` sans collision + dédup).
- **GitNexus :** `npx gitnexus analyze` (`40,432` nœuds, `156,165` arêtes, `686` clusters, `1488` flows) & `gitnexus_detect_changes` (`repo: "/home/romain/Documents/Projects/ORCIA"`, `scope: "all"`) $\rightarrow$ `changed_count: 16`, `changed_files: 58`, `affected_count: 1488`, `risk_level: "critical"`.
