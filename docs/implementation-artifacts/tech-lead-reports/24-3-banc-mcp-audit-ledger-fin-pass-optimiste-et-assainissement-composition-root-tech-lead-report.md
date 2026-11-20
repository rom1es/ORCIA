# Rapport Tech Lead — Story 24.3 : Banc de Test MCP, Audit Ledger, Fin du PASS Optimiste & Assainissement Composition Root

- **Story :** `24-3-banc-mcp-audit-ledger-fin-pass-optimiste-et-assainissement-composition-root` (Epic 24 — Vague 0 `P0/P1`)
- **Date :** 2026-11-20
- **Statut :** `En attente d'implémentation` (initialisé par `Story 23.8`)
- **Plan directeur :** [`sprint-change-proposal-2026-11-20-epic-24-remediation-plan.md`](../../planning-artifacts/sprint-change-proposal-2026-11-20-epic-24-remediation-plan.md)
- **Références remédiées :** `REM24-05`, `REM24-06` | Échec E2E `18#5 #45` | Constat `UX23-08` (étapes banc MCP) | Diagnostics `ARCH24-05`, `ARCH24-07`, `ARCH24-12`
- **Capacité(s) (`capabilities.yaml`) :** `CAP-055`, `CAP-082`, `CAP-092`, `CAP-150`, `CAP-200` (`5` capacités Desktop `failed_e2e`)
- **Classification :** `feature` (vérité HTTP, traçabilité append-only & assainissement DI/Redis)

---

## 1. Analyse du Besoin & Étude d'Impact Tech Lead

### 1.1 Contexte & Critères d'Acceptation
Le scénario `18#5 #45` (`18-catalog-packs-wizards-and-mcp-bench.spec.ts`) échoue sur deux falsifications symétriques UI ↔ Backend, aggravées par des résidus de caches en mémoire :
1. **PASS optimiste synchrone & exposition MCP volatil (`ARCH24-05`)** : `useCatalogRemoteTestBench.ts` (`171` L) positionne un statut `PASS` optimiste avant la réponse HTTP réelle, tandis que `RemoteServiceTestBenchAndGovernedMcpService` (`remote_test_bench_and_mcp_exposure.py` `440` L) stocke `_exposed_agents` et `_pat_tokens` en RAM et que `handleToggleMcp` / `handleActivateRemoteService` ne persistent pas leurs mutations via `PUT /api/v1/mcp/exposure`.
2. **Désynchronisation contrat `audit_ledger` (`ARCH24-07`)** : la requête attendue par la gouvernance/test (`WHERE event_type = 'ADMIN_CONNECTION_TEST'`) diverge du schéma/projection réel (`AuditLedgerOutboxSubscriber` / `audit_ledger`), provoquant un défaut de traçabilité append-only lors des tests de connexion.
3. **Résidus Composition Root & RAM (`ARCH24-12` / `REM24-06`)** : `TwoSpeedFederatedSearchService._speed2_cache` reste en RAM par worker ; `PacksRegistryPage.tsx` (`381` L) et `cockpit/index.tsx:113` (`wfKey`) conservent des branchements partiels ou statuts statiques hors API réelle.

**Critères d'acceptation :** suppression complète du `PASS` optimiste (statut en attente jusqu'à HTTP `200`, erreur visible `[role="alert"]` sur échec), persistance PG18 des expositions MCP et jetons PAT, écriture idempotente et vérifiée dans `audit_ledger` (`ADMIN_CONNECTION_TEST`), migration `_speed2_cache` vers Redis `300s` cloisonné par contexte, et `18#5 #45` PASS.

### 1.2 Analyse d'Impact GitNexus (`repo: "/home/romain/Documents/Projects/ORCIA"`)
- `RemoteServiceTestBenchAndGovernedMcpService` (`packages/orcia-core/src/orcia_core/orchestration/remote_test_bench_and_mcp_exposure.py:111-440`) : `impactedCount: 261`, `risk: "CRITICAL"`, `epistemic: "exact"` (`direct: 242`, `d=2: 19`, `processes_affected: 32`, `modules_affected: 20`).
- `AuditLedgerOutboxSubscriber` (`packages/orcia-core/src/orcia_core/audit_finops/outbox_subscriber.py:242-264`) : `impactedCount: 261`, `risk: "CRITICAL"`, `epistemic: "exact"` (`direct: 242`, `d=2: 19`, `processes_affected: 32`, `modules_affected: 20`).
- `TwoSpeedFederatedSearchService` (`packages/orcia-core/src/orcia_core/rag/two_speed_search.py:171`) : `ambiguous` (`totalCandidates: 9`, candidat principal `L171` : `impactedCount: 261`, `risk: "CRITICAL"`, `direct: 242`).
- `runRemoteServiceTestBench` (`bootstrapAndOntology.ts:222`) : résolu dans l'index (`impactedCount: 0`, appel indirect via `useCatalogRemoteTestBench.ts:94`).
- Impact API (`gitnexus api_impact`) : `apps/api/src/orcia_api/routers/mcp_and_test_bench.py` (`236` L, `3` routes HTTP).

### 1.3 Opportunités de Factorisation & Contrôle de Volumétrie (`< 350` L)
- **Découpage obligatoire `remote_test_bench_and_mcp_exposure.py` (`440` L > seuil `400` L)** : séparer le banc de test distant (`RemoteServiceTestBenchService` + garde SSRF `is_safe_llm_endpoint_url`) de l'exposition gouvernée MCP (`McpExposureService` + adaptateur PG18) en deux modules `< 250` L.
- **Contrôle de `PacksRegistryPage.tsx` (`381` L)** : extraire la sous-vue des healthchecks API en préparation du travail complémentaire `24-6` sur les compteurs pour rester sous `< 300` L.
- **Clé de cache Redis unifiée** : factoriser la construction de clé dans `orcia_kernel` / `rag` (`user_id`, `role`, `workspace_id`, `scope`, `route`, `locale`) afin d'éviter toute fuite inter-tenant dans `TwoSpeedFederatedSearchService`.

---

## 2. Plan d'Implémentation

### 2.1 Couche Données & Migrations Alembic / PostgreSQL 18
1. Inspecter les tables existantes (`catalog_items`, `audit_ledger`, `domain_events_outbox`) ; si nécessaire, ajouter une révision Alembic `Expand` dédiée aux expositions MCP (`mcp_exposed_agents` / colonnes gouvernées + hash jeton PAT, jamais de secret en clair).
2. Aligner le contrat canonique `audit_ledger` sans modifier les triggers append-only (`BEFORE UPDATE OR DELETE RAISE EXCEPTION`) : conserver la structure append-only et vérifier les colonnes exactes (`event_type = 'ADMIN_CONNECTION_TEST'`, `actor_type`, `payload_jsonb`).
3. Enregistrer toute nouvelle table mutable dans `_first_boot_reset_guards.py` (tout en maintenant `audit_ledger` dans `APPEND_ONLY_TABLES`).

### 2.2 Noyau Hexagonal (`orcia-kernel` / `orcia-core`) & Workers
1. Découper `remote_test_bench_and_mcp_exposure.py` (`440` L $\rightarrow$ deux modules `< 250` L) et remplacer `_exposed_agents` / `_pat_tokens` RAM par une persistance PG18 stricte + hash SHA-256 / secret chiffré pour les jetons PAT.
2. Enregistrer l'événement `ADMIN_CONNECTION_TEST` via `domain_events_outbox` / `AuditLedgerOutboxSubscriber` (avec clé d'idempotence) de façon transactionnelle lors des exécutions du banc de test distant.
3. Migrer `TwoSpeedFederatedSearchService._speed2_cache` vers le client Redis `7.4` injecté (TTL `300s`, clé déterministe incluant `user_id`, `role`, `workspace_id`, `scope`, `route`, `locale`).

### 2.3 Backend FastAPI (`apps/api`) & Contrat OpenAPI (`packages/api-client`)
1. Vérifier `apps/api/src/orcia_api/routers/mcp_and_test_bench.py` (`3` routes) et le câblage dans `apps/api/src/orcia_api/dependencies/` (zéro instanciation au niveau module, `Audit` complet `dependencies/` pour `ARCH24-12`).
2. Aligner les schémas Pydantic v2 (`RemoteServiceTestBenchResult` / `McpExposureRequest` / `PacksHealthResponse`), exposer le statut réel des healthchecks pour `PacksRegistryPage`, et régénérer `@orcia/api-client` (`0-diff`).

### 2.4 Interface SPA Vite + TanStack Router & Design System (`@orcia/ui` / `apps/web`)
1. Dans `apps/web/src/features/catalog/useCatalogRemoteTestBench.ts` (`171` L) et `RemoteServiceTestBenchAndMcpExposureView.tsx` (`194` L) :
   - Supprimer le `PASS` optimiste synchrone ; afficher un état « Vérification en cours… » durant la promesse et ne passer à `Réussi` (ou `PASS` sur `data-status` technique si requis) qu'après réception effective HTTP `200`, ou basculer en alerte `[role="alert"]` sur erreur `>= 400`.
   - Câbler `handleToggleMcp` et `handleActivateRemoteService` sur `PUT /api/v1/mcp/exposure` via `@orcia/api-client` avec rechargement à froid depuis `GET`.
2. Brancher `PacksRegistryPage.tsx` (`381` L, extrait en sous-composants `< 300` L) sur les healthchecks API réels et corriger `apps/web/src/features/cockpit/index.tsx:113` pour utiliser le `wfKey` réel au lieu d'une valeur figée.

### 2.5 Stratégie de Vérification & 5 Couches de Tests (`AD-17`)
- **Couche 1 (Unitaire >= 90 %)** : tests unitaires split `remote_test_bench_and_mcp_exposure`, génération événement `ADMIN_CONNECTION_TEST` et clé de cache Redis multi-contexte.
- **Couche 2 (Intégration `testcontainers` PG18 + Redis réel)** : `create_app()` réel $\rightarrow$ exécution banc distant + `PUT /api/v1/mcp/exposure` $\rightarrow$ `SELECT` dans `audit_ledger` (`event_type = 'ADMIN_CONNECTION_TEST'`) + vérification persistance MCP après éviction cache + TTL Redis `300s`.
- **Couche 3 (Composants React)** : Vitest sur `useCatalogRemoteTestBench` & `RemoteServiceTestBenchAndMcpExposureView` prouvant l'absence de `PASS` tant que la promesse HTTP n'est pas résolue (`200`) et l'affichage `[role="alert"]` sur `502`/`422`.
- **Couche 4 (E2E Playwright ciblé)** : exécution de `18-catalog-packs-wizards-and-mcp-bench.spec.ts` (`18#5 #45`), rechargement `F5` vérifiant le maintien de l'exposition MCP.
- **Couche 5 (Statique & Sécurité)** : `ruff`, `mypy --strict`, `lint-imports`, vérification garde SSRF sur endpoints du banc distant, `pnpm turbo run lint typecheck test`, `pnpm site:check`.

---

## 3. Bilan des Modifications & Résultats

> **Statut :** `En attente d'implémentation` — Cette section sera complétée après implémentation, passage des 5 couches `AD-17`, ré-indexation GitNexus (`npx gitnexus analyze` + `gitnexus_detect_changes()`) et exécution de `pnpm site:sync`.

| Fichier / Composant | Action Prévue | Statut |
|---|---|---|
| `packages/orcia-core/.../orchestration/remote_test_bench_and_mcp_exposure.py` | Split `< 350` L + PG18 MCP exposure/PAT | `En attente d'implémentation` |
| `packages/orcia-core/.../audit_finops/outbox_subscriber.py` | Contrat `ADMIN_CONNECTION_TEST` `audit_ledger` | `En attente d'implémentation` |
| `packages/orcia-core/.../rag/two_speed_search.py` | Migration `_speed2_cache` vers Redis `300s` | `En attente d'implémentation` |
| `apps/api/src/orcia_api/{dependencies/,routers/mcp_and_test_bench.py}` | Assainissement Composition Root & DI | `En attente d'implémentation` |
| `apps/web/src/features/catalog/useCatalogRemoteTestBench.ts` + `@orcia/ui` | Fin `PASS` optimiste & `PUT /api/v1/mcp/exposure` | `En attente d'implémentation` |
| `apps/web/src/features/{settings/packs/PacksRegistryPage.tsx,cockpit/index.tsx}` | Healthchecks API réels & `wfKey` réel | `En attente d'implémentation` |
