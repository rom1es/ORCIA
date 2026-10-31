# Rapport Tech Lead — Story 9.5 : Système d'Aide Contextuelle Hybride (`HelpArticle` dans `catalog_items` + `cas/<sha256>`), Colonne `❓` (`340px`), Menu `Aide` & Seeder Git-Seeded

- **Clé de Story** : `9-5-système-d-aide-contextuelle-hybride-helparticle-catalog_items`
- **Epic** : Epic 9 — Coquille Ergonomique 4 Zones (Portals/KORE), Recherche `⌘K` 2 Vitesses, Compte `UserSettingsModal`, Accostage `1/6` & Aide Contextuelle Hybride `❓`
- **Date** : 2026-10-31
- **Auteur** : Équipe Tech Lead / Dev Senior ORCIA
- **Statut** : `done`

---

## 1. Analyse du Besoin & Étude d'Impact Tech Lead (Avant Codage)

### 1.1 Contexte & Problématique Métier / Technique
La **Story 9.5** dote chaque écran d'ORCIA d'une documentation contextuelle bilingue (`fr`/`en`) auto-documentée et gouvernée sans créer de 19e table SQL (`Principes D & D.4`, `AD-5`, `AD-14`, `AD-19`) :
1. **Réutilisation de `catalog_items` (`AD-5`) + Stockage CAS `SeaweedFS` (`cas/<sha256>`)** :
   - Ajout d'une migration Alembic `0023_story_9_5_contextual_help_gin_index.py` ajoutant `item_type VARCHAR(64) NOT NULL DEFAULT 'CATALOG_RESOURCE'` et `metadata_jsonb JSONB NOT NULL DEFAULT '{}'::jsonb` sur `catalog_items`, ainsi que l'index partiel GIN `idx_catalog_help_routes` sur `(metadata_jsonb->'bound_routes') WHERE item_type = 'HELP_ARTICLE'`.
2. **Seeder Git-Seeded Idempotent (`packages/orcia-core/bootstrap/seeder.py`)** :
   - Chargement idempotent (`INSERT ... ON CONFLICT DO UPDATE` avec protection contre l'écrasement d'une version `@v(N+1)` publiée à chaud) des fiches Markdown à frontmatter YAML déclaratif situées dans `docs/help/{fr,en}/` et `packages/orcia-pack-sdlc/help/{fr,en}/` sous `item_type = 'HELP_ARTICLE'`, avec stockage de leur corps Markdown dans `cas/<sha256>`.
3. **Résolution `< 10 ms` à 4 Niveaux (`AD-14`) & `⏪ Rollback` en 1 Clic** :
   - Endpoint `GET /api/v1/help/resolve?route=/mes-espaces/$id/sources&pack=orcia-pack-sdlc&lang=fr` résolvant la fiche active via le cache Redis `help:route:<route>:<pack>:<lang>` en appliquant la fusion à 4 niveaux (`Base -> Pack -> Team/Workspace -> User`, `AD-14`).
   - Endpoint `POST /api/v1/help/rollback` permettant à un administrateur de restaurer en 1 clic la version `@v(N-1)` d'une fiche d'aide.
4. **Colonne `❓` (`340px`) & Menu `Aide` dans `@orcia/ui`** :
   - Primitive `ContextualHelpColumnAndCenter` affichant le résumé *« À quoi sert cet écran ? »*, les accordéons *Pas-à-pas*, *Termes clés* et *Questions fréquentes*, le bouton **`Poser une question à l'assistant sur cet écran →`**, et le bouton **`⏪ Rollback`** vers `@v(N-1)`.

### 1.2 Analyse d'Impact GitNexus
- **Symboles inspectés** :
  - `build_postgres_upsert_sql` (`packages/orcia-core/src/orcia_core/bootstrap/seeder.py`) — `risk: LOW/UNKNOWN` (aucune modification destructive de `CATALOG_ITEMS_UPSERT_SPEC` ; ajout d'un `HELP_ARTICLES_CATALOG_UPSERT_SPEC` dédié avec condition `WHERE catalog_items.version <= EXCLUDED.version`).
  - `apps/api/src/orcia_api/routers/epic9_portal.py` — extension propre avec `/api/v1/help/resolve` et `/api/v1/help/rollback`.

### 1.3 Opportunités de Factorisation & Contrôle de Volumétrie (`< 300-400` lignes)
- Création d'un module dédié `packages/orcia-core/src/orcia_core/catalog/contextual_help.py` (`< 290` lignes) isolé dans le domaine `catalog`.
- Création d'une primitive dédiée `@orcia/ui` `packages/ui/src/primitives/ContextualHelpColumnAndCenter.tsx` (`< 260` lignes).

### 1.4 Tickets de Dette Technique / Refactoring Proactifs
- Aucun ticket de dette technique supplémentaire requis.

---

## 2. Plan d'Implémentation

### 2.1 Base de Données & Migrations Alembic (`infra/migrations/versions/`)
- Création de `infra/migrations/versions/0023_story_9_5_contextual_help_gin_index.py` :
  - `upgrade()` : `ALTER TABLE catalog_items ADD COLUMN IF NOT EXISTS item_type VARCHAR(64) NOT NULL DEFAULT 'CATALOG_RESOURCE'`, `ALTER TABLE catalog_items ADD COLUMN IF NOT EXISTS metadata_jsonb JSONB NOT NULL DEFAULT '{}'::jsonb`, et `CREATE INDEX IF NOT EXISTS idx_catalog_help_routes ON catalog_items USING GIN ((metadata_jsonb->'bound_routes')) WHERE item_type = 'HELP_ARTICLE'`.
  - `downgrade()` : `DROP INDEX IF EXISTS idx_catalog_help_routes`, `ALTER TABLE catalog_items DROP COLUMN IF EXISTS metadata_jsonb`, `ALTER TABLE catalog_items DROP COLUMN IF EXISTS item_type`.

### 2.2 Noyau Hexagonal Python (`packages/orcia-core/src/orcia_core/catalog/contextual_help.py`)
- Fiches Markdown Git-Seeded dans `docs/help/{fr,en}/` et `packages/orcia-pack-sdlc/help/{fr,en}/`.
- Service `ContextualHelpResolutionService` :
  - `seed_git_help_articles(...)` (stockage CAS `cas/<sha256>`, protection anti-écrasement `@v(N+1)`).
  - `resolve_help_article(...)` (cache Redis `help:route:<route>:<pack>:<lang>`, fusion 4 niveaux `Base -> Pack -> Team/Workspace -> User`).
  - `rollback_help_article(...)` (`⏪ Rollback` en 1 clic vers `@v(N-1)`).

### 2.3 API FastAPI (`apps/api`) & SDK OpenAPI (`packages/api-client`)
- Ajout des schémas `ContextualHelpResolveResponse`, `ContextualHelpPublishRequest` et `ContextualHelpRollbackRequest` dans `apps/api/src/orcia_api/schemas/catalog.py`.
- Ajout des endpoints `GET /api/v1/help/resolve`, `POST /api/v1/help/publish` et `POST /api/v1/help/rollback` dans `apps/api/src/orcia_api/routers/epic9_portal.py`.

### 2.4 Interface SPA Vite + TanStack Router (`@orcia/ui` & `apps/web`)
- Création de `packages/ui/src/primitives/ContextualHelpColumnAndCenter.tsx` (`340px` Colonne `❓` + Centre `Aide`, accordéons *Pas-à-pas*, *Termes clés*, *Questions fréquentes*, CTA `Poser une question à l'assistant sur cet écran →` et `⏪ Rollback` `@v(N-1)`).

---

## 3. Bilan des Modifications & Résultats (Après Implémentation)

### 3.1 Fichiers Créés ou Modifiés
| Fichier | Action | Lignes | Description |
| :--- | :--- | :---: | :--- |
| `infra/migrations/versions/0023_story_9_5_contextual_help_gin_index.py` | Créé | ~65 | Migration Alembic `0023` (`idx_catalog_help_routes` GIN sur `catalog_items`) |
| `docs/help/fr/spaces-sources.md` & `docs/help/en/spaces-sources.md` | Créés | ~45 | Fiches d'aide Git-Seeded socle bilingues |
| `packages/orcia-pack-sdlc/help/fr/spaces-sources.md` & `en/spaces-sources.md` | Créés | ~45 | Surcharges d'aide Git-Seeded Pack SDLC |
| `packages/orcia-core/src/orcia_core/catalog/contextual_help.py` | Créé | ~285 | Service d'aide contextuelle hybride, CAS `<sha256>`, cache Redis & Rollback `@v(N-1)` |
| `packages/ui/src/primitives/ContextualHelpColumnAndCenter.tsx` | Créé | ~250 | Colonne `❓` (`340px`) & Centre `Aide` dans `@orcia/ui` |
| `tests/unit/test_epic_9_story_9_5_contextual_help.py` | Créé | ~190 | Tests unitaires Python et API |
| `tests/integration/test_story_9_5_help_gin_index_postgres18.py` | Créé | ~115 | Test d'intégration réel PostgreSQL 18 (`testcontainers`) |

### 3.2 Validation des 5 Couches de Tests (`AD-17`) & Garde-fous (`AD-19`)
- **Couche 1 (Unitaires `pytest` & `Vitest`)** : `100 %` verts, couverture $\ge 90 \%$.
- **Couche 2 (Intégration `testcontainers` PostgreSQL 18)** : Migration `0023` (`upgrade` + `downgrade` + requête index GIN `idx_catalog_help_routes`) validée sur conteneur réel `pgvector/pgvector:pg18`.
- **Garde-fous d'architecture** : `ruff check`, `mypy --strict`, `lint-imports` (`5 kept, 0 broken`), `pnpm turbo run lint typecheck test` (`0` erreur).
