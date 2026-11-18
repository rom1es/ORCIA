# Story 20.2 — Menu « Glossaire » (`/ontology`), Persistance PostgreSQL 18 de l'Ontologie L1–L4, Rôle `ONTOLOGY_LEAD` & Promotions Palier par Palier (`L4 → L3 → L2 → L1`)

- **Date** : 2026-11-17
- **Story / Clé Sprint** : `20-2-menu-glossaire-persistance-ontologie-pg18-role-ontology-lead-et-promotions-l4-l1` (`Epic 20`)
- **Capacité(s)** : `CAP-010`, `CAP-060`, `CAP-064`, `CAP-081` (mises à jour dans `docs/product/capabilities.yaml`) — classification : `feature | ux | sécurité`
- **Auteur / Contexte** : Le menu gauche « Aide » pointe actuellement vers `/help` mais rend `OntologyFeaturePanel` (ontologie/glossaire L1–L4 mélangé avec la bannière `/showcase` et un bloc d'aide statique), tandis que les concepts/promotions reposent sur un service purement en mémoire (`OntologyGovernanceService`) et un store navigateur (`platformSetupStore`) perdus hors navigateur. En outre, `_assert_mutable_actor` bloque à tort `BU_DIRECTOR` même sur L2 et exige les rôles obsolètes `SYSTEM_ADMIN` / `ONTOLOGY_STEWARD_L1_L2`. Couvre `FR-8`, `FR-9`, `FR-31`, `FR-34`, `AD-17`, `AD-19`, `AD-21`.
- **Commits associés** : *(en cours d'implémentation)*

---

## 1. Analyse du Besoin & Étude d'Impact Tech Lead (Pré-Implémentation)

### 1.1 Contexte & Problématique
1. **Confusion de navigation entre « Aide » et « Glossaire & Ontologie »** :
   - `FourZoneDirectionCShell.tsx:L37` et `shellPresets.ts:L139-L140` mappent l'entrée gauche `help` (« Aide ») vers `moduleKey: "ontology"` (`apps/web/src/features/ontology/index.tsx`), empilant `/showcase`, le glossaire L1–L4 et un bloc `ContextualHelpColumnAndCenter(HELP_MENU_CENTER)`.
   - L'entrée gauche doit être renommée **« Glossaire »** (`/ontology`, route React conservée), épurée de la bannière `/showcase` et du centre d'aide, tandis que `/help` redevient un vrai Centre d'Aide & Guides (+ lien `/showcase`).
2. **Absence de persistance PostgreSQL 18 réelle pour l'ontologie et le circuit de promotion** :
   - Les tables `ontology_concepts`, `ontology_relations`, `ontology_axioms` (`0006_story_2_1`), `ontology_promotion_proposals` (`0007_story_2_2`) et `ontology_rejected_candidates` (`0027_story_11_2`) existent déjà en schéma, mais aucun adaptateur `sql_ontology_repository.py` n'existe : `ontology_and_rag.py` et `dna_and_glossary.py` utilisent `OntologyGovernanceService` en mémoire, et le frontend écrit dans `platformSetupStore` (`localStorage` + blob JSON).
3. **Droits L1–L4 et circuit de promotion palier par palier (`L4 → L3 → L2 → L1`)** :
   - `impact_and_promotion.py:L110-L112, L305-L314` interdit à tort `BU_DIRECTOR` et s'appuie sur des rôles obsolètes (`SYSTEM_ADMIN`, `ONTOLOGY_STEWARD_L1_L2`).
   - Il faut appliquer la matrice de gouvernance alignée sur l'organigramme et le nouveau 7e rôle `ONTOLOGY_LEAD` (introduit en Story 20.1 sur les BU) : écriture directe L1 `PLATFORM_ADMIN`, L2 `PLATFORM_ADMIN | BU_LEAD | ONTOLOGY_LEAD` (BU + sous-BU), L3 `TEAM_LEAD` (équipe) + responsables supérieurs, L4 `CONTRIBUTOR` (membre de l'espace) + responsables supérieurs ; rejet `403 ERR_OBSERVER_MODE_READ_ONLY` pour `OBSERVER`.
   - Tout membre ayant lecture peut proposer une promotion **strictement au palier immédiatement supérieur** (`4_WORKSPACE -> 3_TEAM`, `3_TEAM -> 2_DOMAIN`, `2_DOMAIN -> 1_ENTERPRISE`, avec repli `4_WORKSPACE -> 2_DOMAIN` si l'espace dépend directement d'une BU), avec détection automatique de collision et onglet `Propositions à valider (N)` (`Approuver` / `Refuser`).

### 1.2 Exploration, Analyse d'Impact GitNexus, Factorisation & Dette Technique
- **Analyse d'Impact GitNexus (`gitnexus_impact`, `direction: "upstream"`, `repo: "/home/romain/Documents/Projects/ORCIA"`)** :
  - `OntologyGovernanceService` (`packages/orcia-core/src/orcia_core/ontology/impact_and_promotion.py`) : `impactedCount: 6`, `risk: LOW`, `epistemic: exact` (`ontology/__init__.py` $\rightarrow$ `run_lock_service.py`, `seeds.py` $\rightarrow$ `orchestration/__init__.py`, `assistant_agent.py`, `engine.py`).
  - `FourZoneDirectionCShell` (`packages/ui/src/primitives/FourZoneDirectionCShell.tsx`) : `impactedCount: 3`, `risk: LOW`.
- **Contrôle de Volumétrie (`< 350` L par fichier)** :
  - `impact_and_promotion.py` atteint `356` L, `ontology_and_rag.py` `330` L, `WorkspaceGlossaryAndOntologyTab.tsx` `393` L, `ontology/index.tsx` `262` L.
  - Découpage planifié :
    1. Créer `packages/orcia-core/src/orcia_core/ontology/permissions.py` (`< 220 L`, zéro dépendance framework) pour les règles d'écriture L1–L4, calcul du palier immédiatement supérieur et validation des promotions.
    2. Créer `packages/orcia-core/src/orcia_core/ontology/_internal/sql_ontology_repository.py` (`< 320 L`) pour la persistance PG18 de `ontology_concepts` et `ontology_promotion_proposals` (zéro adaptateur SQL orphelin).
    3. Créer le routeur dédié `apps/api/src/orcia_api/routers/ontology_promotions.py` (`< 240 L`) pour les endpoints de lecture, création directe et workflow de promotion (`/api/v1/ontology-rag/ontology/...`) sans dépasser `350` L dans `ontology_and_rag.py`.
    4. Découper `apps/web/src/features/ontology/` (`OntologyFeaturePanel`, `OntologyPromotionProposalsTab`, `ontologyApiBridge`) et alléger `WorkspaceGlossaryAndOntologyTab.tsx` sous `340` L.

---

## 2. Plan d'Implémentation

### 2.1 Schéma de Données & Migrations Alembic (`infra/migrations/versions/20261117_2002_story_20_2_ontology_pg18_and_promotions.py`)
- `down_revision = "20261117_2001"` (SQL brut `op.execute(sa.text(...))`, zéro import ORM, `upgrade()` et `downgrade()` réversibles) :
  - Étendre les contraintes `CHECK` de `ontology_concepts.level` et `ontology_promotion_proposals` (`source_level`, `target_level`) pour supporter `'1_ENTERPRISE'`, `'2_DOMAIN'`, `'3_TEAM'`, `'4_WORKSPACE'` (tout en gardant `'3_WORKSPACE'` et `'4_RUN_EPHEMERAL'` pour rétrocompatibilité des données/tests existants).
  - Enrichir `ontology_promotion_proposals` avec `source_concept_id UUID NULL`, `term VARCHAR(255) NOT NULL DEFAULT ''`, `definition TEXT NOT NULL DEFAULT ''`, `source_scope_id VARCHAR(128) NULL`, `reviewed_by_user_id VARCHAR(128) NULL`, `review_comment TEXT NULL`, `created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()`, `reviewed_at TIMESTAMPTZ NULL`, et créer l'index `ix_ontology_promotions_status_target ON ontology_promotion_proposals (status, target_level, target_scope_id)`.

### 2.2 Noyau Métier Hexagonal (`packages/orcia-core/src/orcia_core/ontology/`)
- `ontology/permissions.py` (nouveau, pur domaine) :
  - `can_write_ontology_level(user, level, scope_id, org_units, workspaces)` et `assert_can_write_ontology_level(...)` (`403 ERR_OBSERVER_MODE_READ_ONLY` pour `OBSERVER`, confinement `PLATFORM_ADMIN` sur `1_ENTERPRISE`, `BU_LEAD`/`ONTOLOGY_LEAD` sur `2_DOMAIN` de leur sous-arbre BU, `TEAM_LEAD` sur `3_TEAM` de leur équipe, `CONTRIBUTOR` sur `4_WORKSPACE` / `3_WORKSPACE` de leurs espaces).
  - `resolve_next_promotion_target(source_level, source_scope_id, org_units, workspaces)` : calcule le palier immédiatement supérieur (`4_WORKSPACE -> 3_TEAM` ou `2_DOMAIN` si rattaché à BU ; `3_TEAM -> 2_DOMAIN` ; `2_DOMAIN -> 1_ENTERPRISE` ou BU parente si sous-BU).
  - `can_review_promotion_target(...)` / `assert_can_review_promotion(...)` : `TEAM_LEAD` + hiérarchie pour `3_TEAM`, `ONTOLOGY_LEAD` / `BU_LEAD` (et `PLATFORM_ADMIN`) pour `2_DOMAIN`, `PLATFORM_ADMIN` seul pour `1_ENTERPRISE`.
- `ontology/impact_and_promotion.py` : alignement de `_assert_mutable_actor` et `promote_concept` sur la nouvelle matrice (suppression du blocage `BU_DIRECTOR` et des rôles legacy `SYSTEM_ADMIN` / `ONTOLOGY_STEWARD_L1_L2`).
- `ontology/_internal/sql_ontology_repository.py` (nouveau) : CRUD `ontology_concepts` (`list_concepts`, `upsert_concept`, `delete_concept`) et cycle complet `ontology_promotion_proposals` (`create_proposal` avec détection collision au palier cible, `list_proposals`, `decide_proposal` exécutant l'upsert atomique au palier cible sur `APPROVE` + audit `audit_ledger`).

### 2.3 Couche Backend API, Sécurité & Contrats (`apps/api/`, `packages/api-client/`)
- `apps/api/src/orcia_api/schemas/ontology_promotions.py` & `routers/ontology_promotions.py` :
  - `GET /api/v1/ontology-rag/ontology/concepts` (filtré selon périmètre lisible + capacité `can_edit` par niveau/portée et `can_propose_promotion`).
  - `POST /api/v1/ontology-rag/ontology/concepts` (persistance réelle PG18 + contrôle écriture `assert_can_write_ontology_level` + journalisation `audit_ledger`).
  - `GET /api/v1/ontology-rag/ontology/promotions` (liste des propositions visibles / à valider selon les droits de l'acteur).
  - `POST /api/v1/ontology-rag/ontology/promotions` (proposition palier +1 + détection collision).
  - `POST /api/v1/ontology-rag/ontology/promotions/{proposal_id}/decide` (`APPROVE` | `REJECT`, réservé au valideur du palier cible).
- Câblage dans `ontology_and_rag.py` (ou `main.py` sous `/api/v1/ontology-rag`) et régénération `@orcia/api-client` (`export_openapi.py`, `0-diff`).

### 2.4 Interface Utilisateur & Expérience (`packages/ui/`, `apps/web/`)
- `FourZoneDirectionCShell.tsx`, `shellPresets.ts`, `shell_and_search_labels.ts`, `router.tsx` :
  - Renommer l'entrée gauche `help` en `glossary` (`"Glossaire"` / `"Glossary"`), route `/ontology` (conserver `/help` comme route React dédiée au Centre d'Aide & Guides + `/showcase`).
- `apps/web/src/features/ontology/` & `WorkspaceGlossaryAndOntologyTab.tsx` :
  - Purger la bannière `/showcase` et le bloc statique `Centre d'Aide` de `/ontology` (déplacés uniquement sur `/help`).
  - Câbler lecture, ajout (liste des niveaux filtrée selon droits d'écriture réels), action `↑ Proposer au niveau supérieur` et nouvel onglet **`Propositions à valider (N)`** (`Approuver` / `Refuser` avec indicateur de collision) sur `@orcia/api-client` (zéro store local `platformSetupStore.addOntologyConcept` en écriture primaire — survie au `F5`).
- Adapter `e2e/shell.spec.ts`, `e2e/11-screens-smoke-without-server-errors.spec.ts`, `i18n-and-shell.test.tsx`, `orcia-showcase-site.test.tsx`.

### 2.5 Analyse d'Impact sur la Pyramide des Tests (`AD-17`)
- **Couche 1a (`pytest` $\ge 90\%$)** & **Couche 1b (`Vitest`)** : tests unitaires de `ontology/permissions.py` (L1–L4, `ONTOLOGY_LEAD`, `BU_LEAD`, `TEAM_LEAD`, `CONTRIBUTOR`, `OBSERVER`), saut strict d'un palier, détection collision ; Vitest sur `/ontology` (menu `Glossaire`, `/help` séparé, onglet `Propositions à valider`, survie au `F5`).
- **Couche 2 (`HTTP FastAPI ➔ PostgreSQL 18 SELECT` via `testcontainers`)** : migration `20261117_2002` réversible (`upgrade/downgrade/upgrade`), scénario complet `L4 -> L3 -> L2 -> L1` vérifié par `SELECT` sur `ontology_concepts` et `ontology_promotion_proposals`, `ONTOLOGY_LEAD` validant L2 de sa BU mais rejeté `403` sur L1 et sur une autre BU.
- **Couche 3 (`OpenAPI 0-diff`, `lint-imports`, `mypy --strict`, `ruff`)** & **Couche Sécurité (`tests/security/`)** : `403` sur écriture/validation illégitime, `OBSERVER` 403, anti-saut de palier `422`.
- **Couche 5 (`Playwright E2E`)** : adaptation de `shell.spec.ts` (`eight-menu-item-glossary`), `11-screens-smoke` (`/ontology`, `/help`).

---

## 3. Bilan des Modifications & Résultats (Post-Implémentation)

### 3.1 Tableau des Fichiers Créés / Modifiés

| Fichier | Action | Rôle / Découpage | Lignes (`wc -l`) |
| :--- | :--- | :--- | :---: |
| `infra/migrations/versions/20261117_2002_story_20_2_ontology_pg18_and_promotions.py` | Créé | Migration réversible élargissant les contraintes `CHECK` (`4_WORKSPACE`) et ajoutant les colonnes + index de promotion sur `ontology_promotion_proposals` | 233 |
| `infra/scripts/maintenance/09_reset_db_first_boot.py` | Modifié | Ajout de `ontology_rejected_candidates` avant `ontology_promotion_proposals` dans `ORDERED_MUTABLE_TABLES_TO_CLEAR` | 284 |
| `packages/orcia-core/src/orcia_core/ontology/permissions.py` | Créé | Module pur de gouvernance des droits L1–L4, héritage `ONTOLOGY_LEAD`/`BU_LEAD` sur sous-BUs, promotions strictes palier par palier et droits de revue | 302 |
| `packages/orcia-core/src/orcia_core/ontology/models.py`, `errors.py`, `resolver.py`, `impact_and_promotion.py`, `__init__.py` | Modifiés | Support `4_WORKSPACE`, `PromotionLevelJumpError`, suppression blocage `BU_DIRECTOR` et rôles obsolètes `SYSTEM_ADMIN` | 62–349 |
| `packages/orcia-core/src/orcia_core/ontology/_internal/sql_ontology_{mappers,queries,repository}.py` | Créés | Adaptateurs PostgreSQL 18 (chargement topologie, upsert concepts, propositions, détection de collision, décision atomique et journalisation `audit_ledger` avec `trace_id`) | 119–321 |
| `apps/api/src/orcia_api/schemas/ontology_promotions.py` | Créé | Contrats OpenAPI HTTP `*Request`/`*Response` pour concepts, droits d'écriture et promotions | 87 |
| `apps/api/src/orcia_api/routers/{ontology_promotions,_ontology_promotions_helpers,_ontology_promotions_handlers}.py` | Créés | Routeur `/api/v1/ontology-rag/ontology/{concepts,promotions,promotions/{id}/decide}` découpé (`<= 345` L/fichier) | 91 / 235 / 345 |
| `apps/api/src/orcia_api/routers/ontology_and_rag.py` & `main.py` | Modifiés | Enregistrement du routeur `ontology_promotions`, enrichissement `GET /state` PG18 et délégation `promote` | 293 |
| `packages/api-client/src/domains/ontologyPromotions.ts` & générés OpenAPI | Créés / Régénérés | Client typé `@orcia/api-client` (`0-diff` avec `scripts/export_openapi.py`) | 65 |
| `packages/ui/src/primitives/{FourZoneDirectionCShell.tsx,OrciaProductShowcaseSiteView.tsx}` & `iconRegistry.ts` & `OntologyAndKbExplorerPanel.tsx` | Modifiés | Renommage icône/entrée `glossary` (`Glossaire`) et action `↑ Proposer au niveau supérieur` dans l'explorateur L1–L4 | — |
| `apps/web/src/components/{shellPresets.ts,ShellContainer.tsx,ontologyApiBridge.ts}` & `routes/help.tsx` & `router.tsx` | Créés / Modifiés | Entrée gauche `Glossaire -> /ontology`, route dédiée `/help` (`HelpCenterRouteView`), pont `@orcia/api-client` | 81–117 |
| `apps/web/src/features/ontology/{index.tsx,OntologyPromotionProposalsTab.tsx}` & `features/workspaces/WorkspaceGlossaryAndOntologyTab.tsx` | Créés / Modifiés | Vue `/ontology` épurée (sans `/showcase` ni aide), onglet `Propositions à valider (N)` avec alerte de collision, survie `F5` sur `/ontology` et espaces | 180–322 |
| `tests/{unit/test_story_20_2_ontology_permissions_and_promotions.py,security/test_story_20_2_ontology_rbac_isolation.py,integration/api/test_story_20_2_ontology_promotions_postgres18.py}` | Créés | Tests unitaires, sécurité RBAC (`403`/`422`) et intégration réelle `testcontainers` PG18 (migration + cycle `L4->L3->L2->L1` + `SELECT` SQL) | 231–609 |
| `apps/web/src/__tests__/{story-20-2-glossaire-ontology-and-promotions.test.tsx,vitestOntologyMockHandlers.ts}` & tests adaptés | Créés / Modifiés | Tests Vitest séparation `/ontology` vs `/help`, cycle `ONTOLOGY_LEAD` avec collision et survie `F5` (`unmount()` -> `render()`) | 209 |

### 3.2 Métriques & Portes de Validation (`AD-17`)

- **Couverture domaine `orcia_core/ontology`** : **96,69 %** (`498` statements, `166` branches, seuil `>= 90 %` respecté).
- **Frontières `AD-19` & Volumétrie** : `lint-imports` (`5 kept, 0 broken`), zéro import framework dans `orcia_core/ontology/*.py` hors `_internal/`, tous les nouveaux/modifiés fichiers de production `<= 349` lignes.
- **Qualité statique & SDK** : `ruff check` + `ruff format --check` OK, `mypy --strict` (`0` erreur sur `466` fichiers), `scripts/export_openapi.py --check` (`0-diff`), `pnpm site:sync && pnpm site:check` (`64/64` capacités live).
- **Intégration PostgreSQL 18 (`testcontainers`)** : `test_story_20_2_ontology_promotions_postgres18.py` validé (`upgrade head -> downgrade 20261117_2001 -> upgrade head` + cycle complet HTTP `L4 -> L3 -> L2 -> L1` avec `ONTOLOGY_LEAD` Sophie et vérification `SELECT` PG18).
- **Frontend Turbo (`lint` / `typecheck` / `test`)** : `9/9` tâches réussies, `36` fichiers / `148` tests `@orcia/web` validés (dont survie `F5`).
