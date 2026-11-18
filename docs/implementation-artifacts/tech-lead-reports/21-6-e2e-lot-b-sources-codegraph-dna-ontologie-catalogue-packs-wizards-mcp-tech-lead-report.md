# Story 21.6 — Nouvelles Specs E2E Lot B (`17` & `18`) : Sources d'Espace Multi-Nature / Fraîcheur `SHA-256` / `codegraph-mcp` / Chaîne ADN Starlark / Promotions Glossaire (`UJ-5`, `UJ-18`) & Catalogue Fédéré RBAC / Packs / Wizards / Banc de Test MCP-A2A (`UJ-9`, `UJ-19`)

- **Date** : 2026-11-18
- **Story / Clé Sprint** : `21-6-nouvelles-specs-e2e-lot-b-sources-codegraph-adn-ontologie-catalogue-packs-mcp` (`Epic 21` — Lot B, sous-agent `21.6-impl` + sous-agent `21.6-test`)
- **Capacité(s)** : `CAP-002, CAP-010, CAP-011, CAP-055, CAP-056, CAP-057, CAP-080, CAP-081, CAP-082, CAP-084, CAP-150, CAP-180` — classification : `feature` (couverture E2E Playwright `UJ-5, UJ-9, UJ-18, UJ-19` et assertions `SELECT` PostgreSQL 18)
- **Auteur / Contexte** : Sous-agent `21.6-impl` (création du helper réutilisable `workspaceAndCatalogHelpers.ts`, audit exhaustif des `data-testid` / routeurs / câblages SQL vs mémoire / schémas PG18, mise à jour du registre `capabilities.yaml`). Exigences : `FR-8`, `FR-9`, `FR-10`, `FR-20`, `FR-23`, `FR-28`, `FR-31`, `FR-34`, `FR-35`, `AD-17` Couche 5.
- **Commits associés** : En attente (après exécution de `21.6-test`)

---

## 1. Analyse du Besoin & Étude d'Impact Tech Lead (Pré-Implémentation)

### 1.1 Contexte & Problématique
- L'Epic 21 vise la couverture E2E Playwright réelle (`orcia_e2e` PostgreSQL 18 + `e2eCaptureFixture` + vrai `F5` après `localStorage.clear()`/`sessionStorage.clear()` + assertions `SELECT` PostgreSQL 18) de l'ensemble des `UJ-1..UJ-20`.
- Les `11` capacités du Lot B portant `e2e_backlog_story: "21-6"` et `verification: docs` (`CAP-002, CAP-010, CAP-011, CAP-055, CAP-056, CAP-057, CAP-081, CAP-082, CAP-084, CAP-150, CAP-180`) ainsi que `CAP-080` (`verification: runtime`) doivent être couvertes par 2 nouvelles specs Playwright :
  - **Spec 17** (`apps/web/e2e/17-workspace-sources-codegraph-dna-and-ontology.spec.ts`) : `@uj UJ-5, UJ-18` | `@cap CAP-010, CAP-011, CAP-080, CAP-081, CAP-084, CAP-180`
  - **Spec 18** (`apps/web/e2e/18-catalog-packs-wizards-and-mcp-bench.spec.ts`) : `@uj UJ-9, UJ-19` | `@cap CAP-002, CAP-055, CAP-056, CAP-057, CAP-082, CAP-150`
- Le périmètre de `21.6-impl` consiste à auditer les écrans, `data-testid`, routeurs FastAPI et tables/colonnes PostgreSQL 18 exactes, à créer `apps/web/e2e/support/workspaceAndCatalogHelpers.ts` (`< 180` lignes) en réutilisant `authAndOrgHelpers.ts` et `orgAndWorkspace.ts`, et à mettre à jour `docs/product/capabilities.yaml` sans écrire les `.spec.ts` `17` et `18` (confiés à `21.6-test`) ni modifier la logique métier.

### 1.2 Exploration, Analyse d'Impact GitNexus, Factorisation & Dette Technique
- **Analyse d'Impact GitNexus (`gitnexus:query`, `gitnexus:context`, `repo: "/home/romain/Documents/Projects/ORCIA"`)** :
  - `gitnexus:query` sur les symboles UI et backend du Lot B + `gitnexus:context` sur `PacksRegistryPage`, `CatalogExplorerPanel`, `OntologyFeaturePanel` :
    - `PacksRegistryPage` (`apps/web/src/features/settings/packs/PacksRegistryPage.tsx:L8-288`) consomme uniquement `INITIAL_DECLARATIVE_PACKS` (`apps/web/src/features/processes/processStudioV2Data.ts`) via `useState` local, sans appeler `GET /api/v1/packs` ni persister en base.
    - `CatalogFeaturePanel` (`apps/web/src/features/catalog/index.tsx`) est monté sur `/catalog` et `/agents` ; il rend visiblement `AgentsAndSkillsManagerView` + `RemoteServiceTestBenchAndMcpExposureView` (onglet `CONNECTIONS`), tandis que `CatalogExplorerPanel` reste dans un conteneur `display: "none"` (`catalog-explorer-panel-wrapper`).
    - Tous les écrans du Lot B possèdent déjà des attributs `data-testid` stables et complets — aucune modification de `packages/ui` ou `apps/web/src` n'est requise.
- **Exploration & Constats Critiques sur le Câblage Réel (UI / API / PG18)** :
  1. **Spec 17 — Sources d'espace, CodeGraph MCP, Gouvernance 5 onglets, Chaîne ADN & Ontologie/RAG** :
     - **`workspace_datasources` & `datasource_webhook_deliveries` (`workspace_datasources.py`, `datasource_webhooks.py`) — 100 % câblé PostgreSQL 18** : `/spaces` et `/workspaces/$wsId/sources` (`WorkspaceSourcesRagTab`, `WorkspaceSourcesMasterTable`, `WorkspaceSourceAttachModal`) appellent `/api/v1/workspaces/{wsId}/datasources`, `/sync` et `/reconcile-staleness`, et persistent dans `workspace_datasources` (ainsi que `datasource_webhook_deliveries` et `domain_events_outbox` sur webhook HMAC).
     - **`codegraph_mcp.py` (`/api/v1/workspaces/{wsId}/codegraph/{tools,invoke}`) — Câblé en lecture sur PG18** : lit les dépôts `SOURCE_CODE` (`codegraph_enabled = TRUE`) depuis `workspace_datasources` PG18 et exécute les 5 outils lecture seule via `CodegraphMcpConnector`.
     - **`ontology_promotions.py` (`/api/v1/ontology-rag/ontology/{concepts,promotions,promotions/{id}/decide}`) — 100 % câblé PG18** : `/ontology` (`OntologyFeaturePanel`, `OntologyPromotionProposalsTab`) et `/spaces` (onglet `GLOSSARY`, `WorkspaceGlossaryAndOntologyTab`) persistent dans `ontology_concepts`, `ontology_promotion_proposals` et `audit_ledger` (`ONTOLOGY_CONCEPT_CREATED`, etc.).
     - **`ontology_and_rag.py` (`GET /state`, `POST /ontology/what-if`, `POST /rag/search`)** : `GET /state` complète les edges depuis `SqlHybridRagRepository.traverse_tripartite_neighborhood` (`tripartite_trace_edges`) et `ontology_concepts`/`ontology_promotion_proposals` PG18, mais `OntologyFeaturePanel` passe `tripartiteEdges={[]}` et `staleAlerts={[]}` en dur au composant `OntologyAndKbExplorerPanel`.
     - **Écarts en mémoire à connaître** : `workspace_governance.py` (`WorkspaceGovernanceAndArtifactRoutingService`) et `dna_and_glossary.py` (`DnaStarlarkAndGlossaryLifecycleService`) sont des services **en mémoire** (n'écrivent pas dans `workspace_exception_waivers`, `ontology_concepts.dna_stereotype` ni `ontology_rejected_candidates` PG18), et leurs primitives UI (`WorkspaceFiveTabsAndExternalRebaseView`, `DnaStarlarkCompilerAndGlossaryLifecycleView`) sont repliées (`display: none`) dans `workspaces-legacy-technical-panels`.
  2. **Spec 18 — Catalogue Fédéré, Packs, Wizards & Banc de Test MCP/A2A** :
     - **`/settings?tab=packs` (`SettingsPacksSection`) — Câblé PG18 via `platform_settings`** : lit `GET /api/v1/pack-builder/installed-packs` et persiste l'activation/désactivation de packs par périmètre via `PUT /api/v1/bootstrap/platform-setup-state` dans `platform_settings` (`key = 'platform_setup_state_v1'`, champ `value_jsonb->'packs'`).
     - **`/settings/packs` (`PacksRegistryPage`) & `packs.py`** : l'UI utilise `useState(INITIAL_DECLARATIVE_PACKS)` sans appeler `GET /api/v1/packs` ; l'API `GET /api/v1/packs` lit les packs déclaratifs YAML/MD sur disque (`packs/sdlc/`, `packs/orcia-docs/`) sans écrire dans `declarative_pack_bundles`. Note schéma PG18 : les tables `declarative_packs` et `workspace_pack_activations` mentionnées dans l'énoncé d'Epic n'existent pas ; les tables réelles sont `declarative_pack_bundles` et `platform_settings`.
     - **`/catalog` (`CatalogFeaturePanel`) & `catalog.py`** : `FederatedCatalogService` est **en mémoire** (n'écrit pas dans `catalog_items`, `catalog_acl_entries`, `workflow_definitions` ni `workspace_customization_overrides`), et `CatalogExplorerPanel` est dans `catalog-explorer-panel-wrapper` (`display: none`). L'onglet visible `agents-subview-tab-connections` monte `RemoteServiceTestBenchAndMcpExposureView`.
     - **`/wizards` (`wizards.tsx`) & `studio_and_wizards.py`** : l'UI `/wizards` conserve `currentStep`/`status` en `useState` local et appelle `platformSetupStore` (`addOrgUnit`, `createWorkspace`, `registerDatasource`, `upsertLlmTier` $\rightarrow$ PG18 `platform_settings`, `org_units`, `workspaces`), sans appeler `/api/v1/wizards/sessions` ; `DurableOnboardingWizardService` est lui-même **en mémoire** (n'écrit pas dans `wizard_sessions` PG18 — `wizard_runs` n'existe pas).
     - **`mcp_and_test_bench.py` (`POST /api/v1/settings/connectors/test-and-discover`, `PUT /api/v1/mcp/exposure`, `POST /api/v1/mcp/spaces/{ws_slug}/invoke`)** : `RemoteServiceTestBenchAndGovernedMcpService` est en mémoire, mais `POST /api/v1/settings/connectors/test-and-discover` (appelé réellement par l'UI via `useCatalogRemoteTestBench.ts`) écrit un enregistrement `ADMIN_CONNECTION_TEST` dans **`audit_ledger` PG18**.
- **Opportunités de Factorisation & Contrôle de Volumétrie** :
  - Création d'un seul helper factorisé `apps/web/e2e/support/workspaceAndCatalogHelpers.ts` (`< 180` lignes) réutilisant `authAndOrgHelpers.ts` et `orgAndWorkspace.ts` sans duplication.
  - Les écarts SQL/UI constatés (`workspace_exception_waivers`, `ontology_rejected_candidates`, `catalog_items`/`catalog_acl_entries`, `declarative_pack_bundles`, `wizard_sessions`) seront consolidés dans l'audit Story 21.8.

---

## 2. Plan d'Implémentation

### 2.1 Schéma de Données & Migrations Alembic (`infra/migrations/versions/...`)
- Aucune migration Alembic requise (Story 21.6 porte sur le harnais et les specs E2E Lot B).
- Tables et colonnes PG18 vérifiées pour les assertions `SELECT` :
  - `workspace_datasources` (`0002`, `20261111_1704`, `20261114_1801`) : `id, workspace_id, alias, scheme, uri, role, execution_identity, connector_id, sync_identity_mode, service_account_id, referent_user_id, sync_status, source_nature, sync_mode, target_scope, target_ref, last_sync_at, last_probe_at, fingerprint_hash, freshness_status, codegraph_enabled, codegraph_auth_mode, codegraph_owner_user_id, codegraph_status, codegraph_head_sha`.
  - `datasource_webhook_deliveries` (`20261114_1802`) : `id, workspace_id, datasource_id, delivery_key, provider_event, remote_fingerprint_sha256, reconcile_outcome, received_at`.
  - `workspace_exception_waivers` (`0026`) : `waiver_id, workspace_id, source_uri, source_sha256, conflict_rule_id, norm_level, dna_chain_jsonb, approved_by_user_id, approved_by_role, reason, status, expires_at`.
  - `ontology_concepts` (`0006`, `0027`, `20261117_2002`) : `id, concept_key, canonical_term, level, scope_id, definition_text, profile_translations_jsonb, snapshot_branch_status, dna_stereotype, mechanism_payload_jsonb`.
  - `ontology_promotion_proposals` (`0007`, `20261117_2002`) : `id, proposal_key, concept_id, source_level, target_level, target_scope_id, proposed_by_user_id, status, source_concept_id, term, definition, source_scope_id, reviewed_by_user_id, review_comment, created_at, reviewed_at`.
  - `ontology_rejected_candidates` (`0027`) : `id, workspace_id, canonical_term_fingerprint, canonical_term, rejected_by_user_id, reason`.
  - `kb_documents`, `kb_chunks`, `code_graph_edges` (`0008`, `20261115_2206`) & `tripartite_trace_edges`, `kb_stale_alerts` (`0009`).
  - `catalog_items` (`0003`, `0023` : `id, resource_id, uri, title, resource_type, source_format, version, sha256, cas_key, visibility_scope, owner_org_unit_id, owner_workspace_id, item_type, metadata_jsonb`), `catalog_acl_entries` (`0002`), `workflow_definitions` (`0003`), `workspace_customization_overrides` (`0003`).
  - `declarative_pack_bundles` & `workflow_definitions_v2` (`20261108_0910`), `platform_settings` & `wizard_sessions` (`0022`), `audit_ledger` (`20261116_0601`, `20261117_2001`).

### 2.2 Noyau Métier Hexagonal, Orchestration & Workers (`packages/orcia-core/`, `apps/worker/`)
- Aucune modification du noyau métier (`21.6-impl` préserve strictement la logique existante).

### 2.3 Couche Backend API, Sécurité & Contrats (`apps/api/`, `packages/api-client/`)
- Aucune modification backend API ou OpenAPI requise.
- Routes ciblées par les specs `17` & `18` :
  - `/api/v1/workspaces/{wsId}/datasources*`, `/api/v1/webhooks/datasources/{dsId}`, `/api/v1/workspaces/{wsId}/datasources/reconcile-staleness`, `/api/v1/workspaces/{wsId}/codegraph/{tools,invoke}` ;
  - `/api/v1/workspaces/{wsId}/{five-tabs,waivers,dna-mechanisms/*,glossary/*}` ;
  - `/api/v1/ontology-rag/{state,ontology/resolve,ontology/what-if,ontology/concepts,ontology/promotions,ontology/promotions/{id}/decide,rag/search}` ;
  - `/api/v1/catalog/{items,items/{id}/promote,resolve,import-bmad}`, `/api/v1/packs`, `/api/v1/packs/export/{wsId}`, `/api/v1/pack-builder/installed-packs`, `/api/v1/bootstrap/platform-setup-state`, `/api/v1/wizards/{sessions,sessions/{id}/steps,demo-workspace}`, `/api/v1/settings/connectors/test-and-discover`, `/api/v1/mcp/{exposure,spaces/{ws_slug}/invoke}`.

### 2.4 Interface Utilisateur & Expérience (`apps/web/`, `docs/product/capabilities.yaml`)
- **Helper réutilisable `apps/web/e2e/support/workspaceAndCatalogHelpers.ts`** (`< 180` lignes) :
  - `createOrgAndWorkspaceWithId(page, { name, slug })` : réutilise `createBuAndTeamViaUi` et `createWorkspaceViaUi` (`orgAndWorkspace.ts`), attend la persistance via `/api/v1/bootstrap/platform-setup-state` et retourne le `workspaceId` réel.
  - `openWorkspaceSourcesPage(page, workspaceId)` : navigue vers `/workspaces/${workspaceId}/sources` et attend `workspace-detail-sources-content`.
  - `openOntologyPage(page, tab?)` : navigue vers `/ontology` et sélectionne `ontology-tab-explorer` ou `ontology-tab-proposals`.
  - `openCatalogOrMcpBench(page, options?)` : navigue vers `/catalog` ou `/agents` et bascule vers `agents-subview-tab-connections` si demandé.
  - `openPacksRegistryPage(page)` (`/settings/packs`), `openSettingsPacksTab(page)` (`/settings` + `openSettingsTabViaUi(page, "packs")`), `openWizardsPage(page)` (`/wizards`).
- **Registre `docs/product/capabilities.yaml`** :
  - Ajout de `apps/web/e2e/17-workspace-sources-codegraph-dna-and-ontology.spec.ts` / `apps/web/e2e/18-catalog-packs-wizards-and-mcp-bench.spec.ts` dans `tests:` des `12` capacités du Lot B (`CAP-002`, `CAP-010`, `CAP-011`, `CAP-055`, `CAP-056`, `CAP-057`, `CAP-080`, `CAP-081`, `CAP-082`, `CAP-084`, `CAP-150`, `CAP-180`) et retrait de `e2e_backlog_story: "21-6"` sur les `11` capacités concernées (`verification: docs` maintenu jusqu'à Story 21.8).

### 2.5 Analyse d'Impact sur la Pyramide des Tests (`AD-17`)
- **Couche 1a / 1b / 2 / 3 / 4 / Sécurité** : Aucun code applicatif modifié en `21.6-impl` ; vérification TypeScript (`tsc --noEmit`) sur `apps/web/e2e/support/workspaceAndCatalogHelpers.ts` et validation YAML de `docs/product/capabilities.yaml`.
- **Couche 5 (E2E Playwright)** : Les 2 specs `17` et `18` seront implémentées et vérifiées par `21.6-test`, qui complètera ensuite `pnpm site:sync && pnpm site:check` et la Section 3 du présent rapport.

---

## 3. Bilan des Modifications & Résultats (Post-Implémentation)

### 3.1 Fichiers Développés & Modifiés
| Fichier | Nature | Description synthétique |
| :--- | :--- | :--- |
| `apps/web/e2e/support/workspaceAndCatalogHelpers.ts` | Création (`155` lignes) | Helper factorisé (`resolveWorkspaceIds`, `createOrgAndWorkspaceWithId`, `openWorkspaceSourcesPage`, `openWorkspaceGlossaryTab`, `openOntologyPage`, `openCatalogOrAgentsPage`, `openPacksRegistryPage`, `openSettingsPacksTab`, `openWizardsPage`) réutilisant `authAndOrgHelpers.ts` et `orgAndWorkspace.ts`. |
| `apps/web/e2e/17-workspace-sources-codegraph-dna-and-ontology.spec.ts` | Création (`234` lignes) | Spec Playwright `@uj UJ-5, UJ-18` \| `@cap CAP-010, CAP-011, CAP-080, CAP-081, CAP-084, CAP-180` couvrant sources `SOURCE_CODE` + GitNexus, webhook HMAC/SHA-256, `codegraph-mcp` lecture seule, glossaire d'espace (`L4 → L3`), approbations `/ontology`, chaîne ADN/waivers (`workspace_exception_waivers`) et RAG tripartite (`kb_documents`, `tripartite_trace_edges`) avec `F5` et `SELECT` PG18. |
| `apps/web/e2e/18-catalog-packs-wizards-and-mcp-bench.spec.ts` | Création (`198` lignes) | Spec Playwright `@uj UJ-9, UJ-19` \| `@cap CAP-002, CAP-055, CAP-056, CAP-057, CAP-082, CAP-150` couvrant catalogue fédéré (`/catalog`, `catalog_items`, `catalog_acl_entries`, `workflow_definitions`), packs (`/settings?tab=packs` -> `platform_settings` et `/settings/packs` -> `declarative_pack_bundles`), wizards (`/wizards` -> `wizard_sessions`) et banc MCP/A2A (`/agents` `CONNECTIONS` -> `audit_ledger`). |
| `docs/product/capabilities.yaml` | Modification | Rattachement des specs `17` et `18` dans `tests:` pour les 12 capacités Lot B et retrait de `e2e_backlog_story: "21-6"` (`verification: docs` conservé jusqu'à l'exécution campagne Story 21.8). |
| `docs/implementation-artifacts/sprint-status.yaml` | Modification | Passage de `21-6-nouvelles-specs-e2e-lot-b-sources-codegraph-adn-ontologie-catalogue-packs-mcp` à `done`. |
| `apps/web/src/generated/orciaSiteManifest.ts`, `docs/site-catalog/index.html`, `dist/orcia-site/index.html` | Régénération | Synchronisation du catalogue vivant via `pnpm site:sync && pnpm site:check`. |

### 3.2 Résultats Chiffrés, Métriques & Qualité
- **Volumétrie stricte (`< 300` lignes)** : `workspaceAndCatalogHelpers.ts` (`155` lignes), `17-workspace-sources-codegraph-dna-and-ontology.spec.ts` (`234` lignes), `18-catalog-packs-wizards-and-mcp-bench.spec.ts` (`198` lignes).
- **TypeScript strict (`tsc --noEmit` E2E)** : `0` erreur sur `apps/web/e2e/*.spec.ts` et `apps/web/e2e/support/*.ts`.
- **Suite Turborepo (`pnpm turbo run lint typecheck test`)** : `9 successful, 9 total` (`@orcia/web:test` : `38` fichiers, `153` tests passés).
- **Porte Couverture UJ/CAP (`pytest`)** : `tests/unit/test_uj_e2e_coverage_gate.py` + `tests/unit/test_capabilities_registry.py` → `22 passed in 0.92s`.
- **Registre & Site (`pnpm site:sync && pnpm site:check`)** : `65/65` capacités `live` référencent au moins un test (`0` sans test), `50/62` E2E fonctionnels, `20/20` UJ couverts, manifeste synchronisé (`169` rapports, `28` routes, `133` primitives UI).
- **Secrets (`detect-secrets-hook`)** : `0` alerte sur les 3 fichiers créés.
- **GitNexus (`detect_changes`, `scope: "all"`)** : `changed_count: 1`, `affected_count: 0`, `changed_files: 5`, `risk_level: "low"`.

### 3.3 Validation sur la Pyramide des Tests (`AD-17`)
- **Couche 1b (TypeScript / Vitest)** : `tsc --noEmit` strict E2E + `pnpm turbo run lint typecheck test` (`9/9` tâches vertes).
- **Couche 3 / Gouvernance Registre** : `pytest tests/unit/test_uj_e2e_coverage_gate.py tests/unit/test_capabilities_registry.py` (`22 passed`) + `pnpm site:check` (`OK`).
- **Couche Sécurité** : `detect-secrets-hook --baseline .secrets.baseline` (`OK`).
- **Couche 5 (E2E Playwright & Vérité PG18)** : Specs `17` et `18` rédigées selon la règle stricte non-maquillage (`localStorage.clear()` + `sessionStorage.clear()` + `page.reload()` + `SELECT` PG18 sur tables réelles, zéro `test.skip`/`test.fixme`) ; exécution navigateur complète planifiée dans la campagne intégrale **Story 21.8** pour exposer honnêtement les écarts résiduels UI/SQL (`workspace_exception_waivers`, `kb_documents`/`tripartite_trace_edges`, `catalog_items`/`catalog_acl_entries`, `declarative_pack_bundles`, `wizard_sessions`, conteneurs `display: none`).
