# Story 9.3 — Recherche Fédérée & Contextuelle `⌘K` à 2 Vitesses (*Zero Layout Shift*, 3 Portées, 7 Familles & Deep-Linking Auto-Focus)

- **Date** : 2026-10-31
- **Story / Clé Sprint** : `9-3-recherche-fédérée-contextuelle-cmd-k-à-2-vitesses-zero-layout` (`Epic 9`)
- **Auteur / Contexte** : Implémentation du moteur de recherche fédérée et contextuelle à 2 vitesses (`GET /api/v1/search`, filtré par `PermissionGuard` `AD-21`) et du composant `@orcia/ui` `TopHeaderSearchCommand` (`680px × max 480px`) avec 3 pilules de portée (`📍 Cet écran`, `📦 Cet Espace`, `🌐 Tous mes Espaces`), 7 familles, Vitesse 1 lexicale (`< 30 ms`, `0 $`) verrouillée en tête + Vitesse 2 sémantique (`halfvec(1024)` + `RRF`, cache Redis `300 s` `search:v2:<ws>:<sha256>`) ajoutée exclusivement en bas avec badge `✨ Passage proche` (*Zero Layout Shift*), et Deep-Linking Auto-Focus (`Principe A.2`, `AD-8`, `AD-19`, `AD-21`, Composant 17).
- **Commits associés** : `Story 9.3`

---

## 1. Analyse du Besoin & Étude d'Impact Tech Lead (Pré-Implémentation)

### 1.1 Contexte & Problématique
- Une recherche universelle `⌘K` classique souffre de deux défauts majeurs en entreprise :
  1. Si elle lance un appel d'embedding vectoriel à chaque frappe, les coûts et la latence explosent ;
  2. Si les résultats vectoriels asynchrones réordonnent toute la liste au moment où l'utilisateur appuie sur `Entrée ↵`, ils provoquent un saut visuel (*Layout Shift*) faisant cliquer sur le mauvais élément.
- La solution d'ORCIA (`Principe A.2`, Composant 17 `top-header-search-command`) découple strictement :
  - **Vitesse 1 (`As-You-Type`, `< 30 ms`, `0 $`, `debounce 80 ms`)** : recherche lexicale (`PostgreSQL tsvector` + trigrammes / préfixes `UNION ALL`) groupée selon les **7 familles** et **verrouillée en tête** de chaque catégorie ;
  - **Vitesse 2 (`Pause 450 ms`, uniquement si $\ge 3$ mots ou clic sur `✨ Recherche sémantique`)** : recherche hybride `halfvec(1024)` HNSW + `RRF` (`AD-8`) cachée `5 min` (`300 s`) dans Redis par `(workspace_id, sha256(query_norm))`, dont les résultats (`✨ Passage proche`) sont **ajoutés exclusivement en bas** de chaque catégorie sans jamais déplacer l'index de sélection clavier (`↑`/`↓`).

### 1.2 Exploration, Analyse d'Impact GitNexus, Factorisation & Dette Technique
- **Analyse d'Impact GitNexus (`gitnexus_query`, `gitnexus_impact` sur `repo: "ORCIA"`)** :
  - `HybridRagService` (`packages/orcia-core/src/orcia_core/rag/hybrid_rag_service.py`) : `risk: LOW`, `impactedCount: 5`.
- **Opportunités de Factorisation & Contrôle de Volumétrie (`< 300 lignes`)** :
  - Création de `packages/orcia-core/src/orcia_core/rag/two_speed_search.py` (`< 260 lignes`) implémentant `TwoSpeedFederatedSearchService` (filtrage RBAC `PermissionGuard` `AD-21`, Vitesse 1 `0 $`, Vitesse 2 vectorielle + cache Redis `300 s`, déduplication Speed 1 vs Speed 2, et requête SQL `UNION ALL` PostgreSQL 18).
  - Création de la primitive `@orcia/ui` `TopHeaderSearchCommand.tsx` (`< 280 lignes`) implémentant la modale `680px × max 480px`, les 3 pilules de portée (`SCREEN`, `WORKSPACE`, `ALL_WORKSPACES`), la préservation de l'élément actif au clavier lors de l'arrivée de la Vitesse 2 (*Zero Layout Shift*), `Entrée ↵` (Deep-Linking + Auto-Focus `2 s` ou ouverture directe de la Colonne `❓` pour `HELP_ACTIONS`), `⌘+Entrée` (aperçu latéral droit), et le pied `💬 Poser la question « ... » à Mon Assistant →`.

---

## 2. Plan d'Implémentation

### 2.1 Noyau Métier (`packages/orcia-core/src/orcia_core/rag/two_speed_search.py`)
- Définition des 7 familles (`SearchFamilyKey`), des 3 portées (`SearchScopeMode`) et de `TwoSpeedFederatedSearchService`.
- Génération de la clé de cache Redis déterministe `search:v2:{workspace_id}:{sha256(query_norm)}` (TTL `300 s`).

### 2.2 Couche Backend FastAPI & Contrats OpenAPI (`apps/api/`)
- Ajout de `GET /api/v1/search` dans `apps/api/src/orcia_api/routers/epic2_ontology_and_rag.py` et des schémas `TwoSpeedSearchHitItem` / `TwoSpeedSearchResponse` dans `apps/api/src/orcia_api/schemas/ontology_and_rag.py`.
- Régénération du SDK OpenAPI 3.1 (`scripts/export_openapi.py` `0-diff`).

### 2.3 Design System (`@orcia/ui`) & Frontend (`apps/web/`)
- Création de `packages/ui/src/primitives/TopHeaderSearchCommand.tsx` et ajout des traductions `FR`/`EN` dans `apps/web/src/i18n/locales/epic9_labels.ts`.

---

## 3. Bilan des Modifications & Résultats (Post-Implémentation)

### 3.1 Fichiers Développés & Modifiés
| Fichier | Nature | Description synthétique |
| :--- | :--- | :--- |
| `packages/orcia-core/src/orcia_core/rag/two_speed_search.py` | Création | Service `TwoSpeedFederatedSearchService` (3 portées, 7 familles, Vitesse 1 `0 $`, Vitesse 2 vectorielle + cache Redis `300 s`, filtrage `PermissionGuard` `AD-21`) |
| `apps/api/src/orcia_api/schemas/ontology_and_rag.py` | Modification | Schémas OpenAPI `TwoSpeedSearchHitItem` et `TwoSpeedSearchResponse` |
| `apps/api/src/orcia_api/routers/epic2_ontology_and_rag.py` | Modification | Endpoint `GET /api/v1/search` |
| `packages/ui/src/primitives/TopHeaderSearchCommand.tsx` | Création | Modale `top-header-search-command` (`680px × max 480px`), *Zero Layout Shift*, Deep-Linking `Entrée ↵`, aperçu `⌘+Entrée` & transfert à `Mon Assistant` |
| `tests/unit/test_epic_9_story_9_3_two_speed_search.py` | Création | Tests unitaires, API et cache Redis de la recherche à 2 vitesses |

### 3.2 Résultats Chiffrés, Métriques & Qualité
- **Couverture de tests** : `>= 90 %` sur `two_speed_search.py` et `TopHeaderSearchCommand.tsx`.
- **Qualité statique & Architecture** :
  - `.venv/bin/ruff check .` & `.venv/bin/mypy --strict` : `0 error`
  - `.venv/bin/lint-imports` : `0 broken`
  - `pnpm turbo run lint typecheck test` : `0 error`

### 3.3 Validation & Procédure de Test (5 Couches `AD-17`)
- **Couche 1 (`pytest` + `Vitest`)** : Vérification des 3 portées (`SCREEN`, `WORKSPACE`, `ALL_WORKSPACES`), des 7 familles, du seuil $\ge 3$ mots pour la Vitesse 2, de l'ajout en bas sans déplacement de l'index clavier (*Zero Layout Shift*), du filtrage `PermissionGuard` (`AD-21`), du cache `search:v2:<ws>:<sha256>` (`TTL 300 s`) et du Deep-Linking Auto-Focus (`2000 ms` ou ouverture Colonne `❓`).
- **Couche 3 (`OpenAPI 0-diff`)** : `scripts/export_openapi.py --check` (`0 diff`).
