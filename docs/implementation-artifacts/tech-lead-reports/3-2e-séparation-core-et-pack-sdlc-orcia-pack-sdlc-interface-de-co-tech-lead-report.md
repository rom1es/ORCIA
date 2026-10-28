# Rapport Tech Lead — Story 3.2e : Séparation Core et Pack SDLC (`orcia-pack-sdlc`), Interface de Connecteur Universelle (`ConnectorPort`) & Hygiène des Seeds

- **Story Key** : `3-2e-séparation-core-et-pack-sdlc-orcia-pack-sdlc-interface-de-co`
- **Epic** : Epic 3 — Moteur d'Exécution Durable, Gouvernance Adaptive & Résilience
- **Statut** : `done`
- **Date** : 2026-10-28
- **Auteur** : Agent Tech Lead / Senior Dev (Amelia)
- **Décisions d'Architecture liées** : `AD-20`, `AD-19`, `AD-5`, `AD-6`, `AD-8`, `AD-12`, `AD-13`, `AD-16`, `AD-17`
- **Action Items résolus** : `DEC-SEED-01`, `DEC-P0-01`, `DEC-P0-02`

---

## 1. Analyse du Besoin & Étude d'Impact Tech Lead (Avant Codage)

### 1.1 Contexte & Problématique Métier

L'audit d'architecture Avenant A2 (`DEC-SEED-01`, `DEC-P0-01`, `DEC-P0-02`, `AD-20`) a mis en évidence trois couplages structurels empêchant le noyau d'orchestration d'ORCIA d'opérer comme un moteur générique multi-métiers (Finance, Juridique, ERP SAP, Ops) :
1. **Hygiène des Seeds (`DEC-SEED-01` / `AC-E0`)** : Les manifestes YAML de démonstration (`DEFAULT_*_WORKFLOW_YAML`), le gabarit ADR (`DEFAULT_ADR_TEMPLATE_SEED`) et le peuplement du jeu de données RAG (`populate_rag_test_dataset`) résidaient encore dans `orcia_core.orchestration.seeds` et `orcia_core.rag` au lieu d'être centralisés dans `orcia_core.bootstrap`.
2. **Fuite de vocabulaire SDLC dans `orcia-kernel` et `orcia-core/orchestration` (`DEC-P0-01` / `AC-E1`, `AC-E2`)** : Les marqueurs `BUG_CODE_SUSPECTED` et `DOC_OBSOLETE_SUSPECTED` étaient figés dans `orcia_kernel.enums.MemlogMarkerType`, et la politique SDLC `FR-13` (`writes_code`, `declares_intention`, `reverse_doc_from_code`, `brownfield_bootstrap`) était codée en dur dans `orcia_core.orchestration.{yaml_loader,yaml_validator,engine}`.
3. **Schémas de connecteurs codés en dur (`DEC-P0-02` / `AC-E3`, `AC-E4`, `AC-E5`)** : Les schémas `git`, `jira`, `confluence`, `nexus` étaient verrouillés dans `ALLOWED_SCHEMES`, dans 4 `Literal` Python (`FederatedScheme`, `DatasourceScheme`, `BrokerConnectorScheme`, `KbDocumentEntity.source_scheme`) et dans 4 contraintes SQL `CHECK (... IN (...))` PostgreSQL (`workspace_datasources`, `user_passthrough_credentials`, `permission_broker_policies`, `permission_broker_tickets`), empêchant l'ajout d'un connecteur tiers (ex. `sap://`) sans modifier le cœur ni le schéma SQL.

### 1.2 Analyse d'Impact GitNexus (`repo: "ORCIA"`)

Conformément aux règles `AGENTS.md`, l'analyse d'impact GitNexus (`direction: "upstream"`, `repo: "ORCIA"`) a été exécutée avant toute édition :

| Symbole analysé | Niveau de risque GitNexus | Callers directs (`d=1`) | Impact total (symboles / processus) | Décision Tech Lead |
|---|---|---|---|---|
| `parse_federated_uri` (`catalog/cas_resolver.py`) | **`CRITICAL`** | 5 callers (`FederatedUriResolver.resolve`, `CatalogGovernanceService`, `WorkflowOrchestrationSetupService`) | 11 symboles, 7 processus | Préserver la signature exacte `parse_federated_uri(raw_uri: str) -> ParsedFederatedUri` et déléguer la validation du schéma à `is_registered_connector_scheme()` (`orcia_kernel.ports`). |
| `FederatedUriResolver` (`catalog/cas_resolver.py`) | **`MEDIUM`** | 11 callers | 15 symboles, 4 processus | Conserver la résolution déterministe CAS SHA-256 tout en déléguant le mode de résolution (`last_path_segment` vs `ref_or_latest`) aux `capabilities()` du `ConnectorPort`. |
| `WorkflowStepSpec` (`orchestration/models.py`) | **`MEDIUM`** | 9 callers | 10 symboles, 4 processus | Ajouter `tags: tuple[str, ...] = ()` et `policies: tuple[str, ...] = ()` en phase *Expand* tout en conservant les propriétés dérivées de compatibilité (`writes_code`, `declares_intention`, `reverse_doc_from_code`). |
| `DurableOrchestrationEngine` (`orchestration/engine.py`) | **`LOW`** | 3 callers | 3 symboles, 0 processus | Injecter `MemlogMarkerPluginProtocol` découvert via `entry_points(group="orcia.memlog_markers")`. |

### 1.3 Opportunités de Factorisation & Contrôle de Volumétrie (300–400 lignes)

- Tous les modules créés dans `packages/orcia-pack-sdlc/src/orcia_pack_sdlc/` respectent strictement le plafond de volumétrie : `__init__.py` (`44` lignes), `connectors.py` (`186` lignes), `policies.py` (`114` lignes), `markers.py` (`66` lignes), `formats_and_indexers.py` (`48` lignes).
- Le connecteur tiers de référence `tests/fixtures/plugins/orcia_connector_sap_fake/__init__.py` compte **`130` lignes** (sous la limite stricte `< 150` lignes de `AC-E4`).
- Le découpage de `orcia_core.orchestration.seeds` vers `orcia_core.bootstrap.orchestration_seeds` a ramené `orchestration/seeds.py` de `256` lignes à **`109` lignes**.

---

## 2. Plan d'Implémentation

### 2.1 Base de Données & Migrations Alembic (`infra/migrations/versions/`)
- **Révision `0013_story_3_2e_connector_schemes_expand.py` (Phase Expand)** :
  - Création de la table de référence `connector_schemes(id UUID PRIMARY KEY, scheme VARCHAR(32) UNIQUE NOT NULL, display_name VARCHAR(128) NOT NULL, pack_name VARCHAR(128) NOT NULL, is_active BOOLEAN NOT NULL DEFAULT TRUE, created_at TIMESTAMPTZ NOT NULL DEFAULT NOW())`.
  - Seed idempotent (`INSERT INTO connector_schemes ... ON CONFLICT (scheme) DO UPDATE`) des 3 schémas natifs (`orcia`, `db`, `mcp` — `pack_name = 'orcia-core'`) et des 4 schémas du pack SDLC (`git`, `jira`, `confluence`, `nexus` — `pack_name = 'orcia-pack-sdlc'`).
  - Ajout en 2 étapes sans verrouillage long (`ADD CONSTRAINT ... FOREIGN KEY (...) REFERENCES connector_schemes(scheme) ON DELETE RESTRICT NOT VALID` puis `VALIDATE CONSTRAINT`) sur `workspace_datasources.scheme`, `user_passthrough_credentials.connector_scheme`, `permission_broker_policies.connector_scheme` et `permission_broker_tickets.connector_scheme`.
- **Révision `0014_story_3_2e_drop_scheme_checks_contract.py` (Phase Contract)** :
  - Suppression (`DROP CONSTRAINT IF EXISTS`) des 4 contraintes `CHECK` figées (`ck_workspace_datasources_scheme`, `ck_user_passthrough_credentials_scheme`, `ck_permission_broker_policies_scheme`, `ck_permission_broker_tickets_scheme`) et restauration complète dans `downgrade()`.

### 2.2 Noyau Hexagonal (`packages/orcia-kernel`, `packages/orcia-core`, `packages/orcia-pack-sdlc`)
- **`packages/orcia-kernel/src/orcia_kernel/ports.py`** : Définition de `ConnectorPort` (`capabilities() -> ConnectorCapabilities`, `fetch(uri) -> ConnectorFetchResult`, `invoke(action, payload, idempotency_key) -> ConnectorInvokeResult`, `health() -> ConnectorHealthStatus`, `map_error(exc) -> OrciaDomainError`) et du registre dynamique chargé via `importlib.metadata.entry_points(group="orcia.connectors")`.
- **`packages/orcia-kernel/src/orcia_kernel/enums.py`** : Remplacement du `Literal` figé `MemlogMarkerType` par un registre de marqueurs à espace de noms (`register_memlog_marker`, `is_valid_memlog_marker`, `normalize_memlog_marker`) pré-peuplé uniquement avec les 4 marqueurs génériques du noyau (`DECISION`, `ASSUMPTION`, `PROVENANCE_CITATION`, `DIVERGENCE_DETECTED`).
- **`packages/orcia-pack-sdlc`** : Création du 5e package `uv` du workspace déclarant les 5 groupes `entry_points` (`orcia.connectors`, `orcia.workflow_policies`, `orcia.memlog_markers`, `orcia.catalog_formats`, `orcia.rag_indexers`) et ajout du 4e contrat `import-linter` (`AD-20 Contract 4: orcia_kernel and orcia_core never import orcia_pack_sdlc`).
- **`packages/orcia-core/src/orcia_core/orchestration/`** : Généralisation de `WorkflowStepSpec` (`tags`, `policies`), validation des politiques via `WorkflowPolicyPluginProtocol` (`ERR_UNKNOWN_WORKFLOW_POLICY` / `UnknownWorkflowPolicyError` si une politique YAML n'est pas enregistrée), et délégation des marqueurs rapides à `MemlogMarkerPluginProtocol`.

### 2.3 Backend FastAPI & SDK OpenAPI (`apps/api`, `packages/api-client`)
- Ajout de `ERR_UNKNOWN_WORKFLOW_POLICY` (`HTTP 422 Unprocessable Entity`, RFC 9457 Problem Details FR/EN) dans `apps/api/src/orcia_api/errors/registry.py`.
- Exposition de `tags: list[str]` et `policies: list[str]` sur `WorkflowStepSpecSchemaItem` (`apps/api/src/orcia_api/schemas/orchestration.py`) et généralisation de `KbDocumentSchemaItem.source_scheme: str` (`schemas/ontology_and_rag.py`).
- Régénération `0-diff` du schéma OpenAPI 3.1 (`openapi/openapi.json`) et du SDK TypeScript (`packages/api-client/src/generated/schema.d.ts`).

### 2.4 Interface SPA (`apps/web`, `packages/ui`)
- Aucune régression sur les 8 modules `apps/web/src/features/<domaine>/` ni sur `@orcia/ui` ; passage intégral des tests Vitest et du garde-fou `check-feature-boundaries.mjs`.

---

## 3. Bilan des Modifications & Résultats (Après Implémentation)

### 3.1 Tableau des Fichiers Créés / Modifiés

| Fichier | Action | Rôle & Responsabilité | Lignes |
|---|---|---|---|
| `packages/orcia-pack-sdlc/pyproject.toml` | Créé | Manifeste du 5e package `uv` et déclaration des 5 groupes `entry_points` (`AD-20`) | 40 |
| `packages/orcia-pack-sdlc/src/orcia_pack_sdlc/__init__.py` | Créé | Façade publique `orcia_pack_sdlc` (`activate_sdlc_pack`) | 44 |
| `packages/orcia-pack-sdlc/src/orcia_pack_sdlc/connectors.py` | Créé | Adaptateurs `ConnectorPort` pour `git`, `jira`, `confluence`, `nexus` | 186 |
| `packages/orcia-pack-sdlc/src/orcia_pack_sdlc/policies.py` | Créé | Plugin `SdlcFr13WorkflowPolicyPlugin` (`FR-13`, `brownfield_bootstrap`) | 114 |
| `packages/orcia-pack-sdlc/src/orcia_pack_sdlc/markers.py` | Créé | Plugin `SdlcMemlogMarkerPlugin` (`sdlc.bug_code_suspected`, `sdlc.doc_obsolete_suspected`) | 66 |
| `packages/orcia-pack-sdlc/src/orcia_pack_sdlc/formats_and_indexers.py` | Créé | Entry points `bmad_pack` (`orcia.catalog_formats`) et indexeurs RAG SDLC (`orcia.rag_indexers`) | 48 |
| `packages/orcia-core/src/orcia_core/bootstrap/orchestration_seeds.py` | Créé | Manifestes YAML de référence et seed ADR déplacés hors d'`orchestration` (`AC-E0`) | 158 |
| `packages/orcia-core/src/orcia_core/bootstrap/rag_seeds.py` | Créé | Peuplement RAG de démonstration déplacé hors de `rag/__init__.py` (`AC-E0`) | 99 |
| `packages/orcia-kernel/src/orcia_kernel/ports.py` | Modifié | Contrat `ConnectorPort` et registre dynamique de schémas (`AC-E3`) | 316 |
| `packages/orcia-kernel/src/orcia_kernel/enums.py` | Modifié | Registre dynamique de marqueurs à espace de noms sans vocabulaire SDLC (`AC-E2`) | 159 |
| `infra/migrations/versions/0013_story_3_2e_connector_schemes_expand.py` | Créé | Migration Expand : table `connector_schemes`, upsert des 7 schémas, 4 FK `NOT VALID` + `VALIDATE` | 195 |
| `infra/migrations/versions/0014_story_3_2e_drop_scheme_checks_contract.py` | Créé | Migration Contract : suppression des 4 contraintes `CHECK` figées + `downgrade()` | 116 |
| `tests/fixtures/plugins/orcia_connector_sap_fake/__init__.py` | Créé | Connecteur tiers de référence `sap://` (`< 150` lignes, `0` fichier Core modifié, `AC-E4`) | 130 |
| `tests/conformance/connector_port/test_connector_conformance.py` | Créé | Suite de conformité `ConnectorPort` (`git`, `jira`, `confluence`, `nexus`, `sap`) | 159 |
| `tests/unit/test_story_3_2e_sdlc_pack_and_connectors.py` | Créé | Tests `AC-E1`, `AC-E2`, `AC-E5` (conteneur `PostgreSQL 18` réel avec lignes préexistantes) | 234 |

### 3.2 Validation des 5 Couches de Tests (`AD-17`) & Métriques de Qualité

| Couche / Gate | Commande exécutée | Résultat |
|---|---|---|
| **Contrats d'Architecture (`AD-19` & `AD-20`)** | `.venv/bin/lint-imports` | **4 kept, 0 broken** (171 fichiers, 739 dépendances) |
| **Zéro vocabulaire SDLC dans Kernel & Orchestration (`AC-E2`)** | `grep -rnIiE "writes_code\|BUG_CODE\|DOC_OBSOLETE\|brownfield\|confluence\|git://\|jira" packages/orcia-kernel packages/orcia-core/src/orcia_core/orchestration` | **0 ligne** |
| **Linter & Formatage Python** | `.venv/bin/ruff check . && .venv/bin/ruff format --check .` | **0 erreur** (287 fichiers) |
| **Typage Strict Python** | `.venv/bin/mypy --strict packages/orcia-kernel packages/orcia-core packages/orcia-pack-sdlc apps/api apps/worker` | **0 erreur** (127 fichiers sources) |
| **Couches 1, 2 & 3 (Unit, Conformance `ConnectorPort`, Alembic `0013`–`0014` sur PostgreSQL 18 réel)** | `.venv/bin/pytest tests/unit tests/conformance --cov=packages/orcia-kernel --cov=packages/orcia-core --cov=packages/orcia-pack-sdlc --cov-fail-under=90` | **74 passed**, couverture totale **`92.56%`** ($\ge 90\%$) |
| **Couches 4 & 5 (OpenAPI `0-diff`, SDK TS & SPA Vite/TanStack)** | `pnpm turbo run lint typecheck test` | **9/9 tâches réussies** (`@orcia/ui`, `@orcia/api-client`, `@orcia/web`) |
| **Validation Architecture Spine** | `.venv/bin/python .agent/skills/bmad-architecture/scripts/lint_spine.py --workspace docs/planning-artifacts/architecture/architecture-ORCIA-2026-10-24` | **PASS (0 findings)** |

### 3.3 Analyse post-implémentation GitNexus (`gitnexus_detect_changes`)

L'index GitNexus a été rafraîchi (`npx gitnexus analyze`) et `detect_changes` confirme l'isolation stricte entre `orcia_pack_sdlc`, `orcia_core` et `orcia_kernel` sans cycle ni régression sur les flux existants.
