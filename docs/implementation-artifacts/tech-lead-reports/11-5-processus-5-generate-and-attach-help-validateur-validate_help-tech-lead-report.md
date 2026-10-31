# Rapport d'Analyse & d'Implémentation Tech Lead — Story 11.5 : Processus 5 `generate-and-attach-help`, Validateur Déterministe `validate_help_article` (Palier 1 `< 5 s`) & Rattachement à Chaud / Export Git

> **Statut** : `DONE`
> **Date** : `2026-10-31`
> **Auteur** : Tech Lead / Senior Dev Agent
> **Références** : [`epics.md` (Story 11.5)](../../planning-artifacts/epics.md#L1350-L1369) · [`ARCHITECTURE-SPINE.md`](../../planning-artifacts/architecture/architecture-ORCIA-2026-10-24/ARCHITECTURE-SPINE.md) · [`DESIGN.md`](../../planning-artifacts/ux-designs/ux-ORCIA-2026-10-24/DESIGN.md) · [`EXPERIENCE.md`](../../planning-artifacts/ux-designs/ux-ORCIA-2026-10-24/EXPERIENCE.md)

---

## 1. Analyse du Besoin & Étude d'Impact Tech Lead (Avant Codage)

### 1.1 Contexte Fonctionnel & Problématique
Pour garantir qu'aucune nouvelle fonctionnalité ni aucun nouveau Pack Métier ne soit livré sans son aide contextuelle à jour (`Principe D.4`, `AD-5`, `AD-9`, `AD-18`, `AD-19`, `AD-20`), la **Story 11.5** implémente le **Processus 5 (`orcia://pack-builder/workflows/generate-and-attach-help`)** de `packages/orcia-pack-builder` :
1. **Rédaction bilingue (`fr`/`en`) par `@Rédacteur-Documentation-Orcia` (Étape 2)** :
   - Génère la fiche Markdown `HelpArticle` en français et en anglais avec un frontmatter YAML déclaratif complet (`id`, `version`, `bound_routes`, `pack_id`, `roles_allowed`, `glossary_terms`, `related_workflows`) et les 3 sections obligatoires munies d'ancres `#`.
2. **Gate Déterministe `validate_help_article` en Sandbox Palier 1 `< 5 s` (Étape 3)** :
   - Vérifie automatiquement :
     1. Que chaque route de `bound_routes` existe dans l'arbre TanStack Router ou dans le manifeste du Pack ;
     2. Qu'aucun composant UI inexistant dans `@orcia/ui` n'est cité et que les **3 sections obligatoires** (`## 1. À quoi sert cet écran ?` / `## 1. What is this screen for?`, `## 2. Comment faire (Pas-à-pas)` / `## 2. How to use (Step-by-step)`, `## 3. Questions fréquentes & Dépannage` / `## 3. Frequently Asked Questions & Troubleshooting`) ainsi que les ancres `#` sont présentes ;
     3. Que les termes de `glossary_terms` sont alignés avec le Glossaire actif et qu'**aucun secret ou token** (`pat_mcp_*`, `sk-*`, `secret://`, clés privées PEM, jetons JWT) ne figure dans le texte (`0` fuite).
3. **Rattachement à Chaud `< 100 ms` & Export Git (Étape 4)** :
   - Persiste atomiquement la fiche dans `catalog_items` (`item_type = "HELP_ARTICLE"`, `authority_role = "REFERENCE"`) + `cas/<sha256>` (`SeaweedFS` / S3 CAS) ;
   - Indexe son vecteur `halfvec(1024)` + `tsvector` dans `document_chunks` avec `authority_role = "REFERENCE"` ;
   - Invalide le cache Redis `help:route:*` pour un affichage immédiat en `< 100 ms` dans la Colonne `❓` (`340px`), le menu `Aide` et la recherche `⌘K` ;
   - Exporte les fichiers `.md` bilingues vers `docs/help/{fr,en}/` ou `packages/orcia-pack-{slug}/help/{fr,en}/`.

### 1.2 Analyse d'Impact GitNexus
- **Requête `gitnexus_query({query: "ContextualHelpResolutionService parse_declarative_help_markdown build_help_redis_cache_key validate_help_article", repo: "ORCIA"})`** :
  - Identifie `packages/orcia-core/src/orcia_core/catalog/contextual_help.py` (`Story 9.5`) et `packages/orcia-core/src/orcia_core/orchestration/pack_builder_processes.py` (`Story 11.4`).
- **Analyse `gitnexus_impact({target: "parse_declarative_help_markdown", direction: "upstream", repo: "ORCIA"})`** :
  - Risque `LOW` (`2` appelants dans `ContextualHelpResolutionService`).

### 1.3 Opportunités de Factorisation & Contrôle de Volumétrie
- Création d'un module dédié `packages/orcia-core/src/orcia_core/orchestration/help_generator_and_validator.py` (< 390 lignes) réutilisant `build_help_redis_cache_key` de `orcia_core.catalog.contextual_help` et exposé également via `packages/orcia-pack-builder`.

---

## 2. Plan d'Implémentation

### 2.1 Noyau Hexagonal (`packages/orcia-core` & `packages/orcia-pack-builder`)
- Module [`help_generator_and_validator.py`](../../../../packages/orcia-core/src/orcia_core/orchestration/help_generator_and_validator.py) :
  - `HelpArticleDeterministicValidator` (`validate_help_article`) exécutant en `< 5 s` les 3 contrôles déterministes (routes connues, composants `@orcia/ui` valides + 3 sections obligatoires + ancres `#`, alignement `glossary_terms` + scan `0` secret/token).
  - `HelpGenerationAndHotAttachmentService` (`generate_and_attach_help`) générant le couple bilingue (`fr`/`en`), validant via `validate_help_article`, persistant dans `catalog_items` + `cas/<sha256>`, invalidant `help:route:*` en `< 100 ms` et exportant les fichiers `.md` vers `docs/help/{fr,en}/` ou `packages/orcia-pack-{slug}/help/{fr,en}/`.

### 2.2 Backend FastAPI (`apps/api`)
- Extension de [`epic11_pack_builder.py` (schemas)](../../../../apps/api/src/orcia_api/schemas/epic11_pack_builder.py) et [`epic11_pack_builder.py` (router)](../../../../apps/api/src/orcia_api/routers/epic11_pack_builder.py) avec :
  - `POST /api/v1/pack-builder/processes/validate-help-article`
  - `POST /api/v1/pack-builder/processes/generate-and-attach-help`

### 2.3 Interface SPA Direction C (`@orcia/ui`)
- Primitive [`HelpArticleGeneratorAndValidatorView.tsx`](../../../../packages/ui/src/primitives/HelpArticleGeneratorAndValidatorView.tsx) affichant le statut des 3 vérifications déterministes (`Routes`, `Composants @orcia/ui & 3 Sections`, `Glossaire & 0 Secret`), l'aperçu bilingue `FR`/`EN`, la latence de rattachement `< 100 ms` et les chemins Git exportés.

---

## 3. Bilan des Modifications & Résultats (Après Implémentation)

### 3.1 Fichiers Créés / Modifiés
| Fichier | Nature | Rôle |
| :--- | :--- | :--- |
| `packages/orcia-core/src/orcia_core/orchestration/help_generator_and_validator.py` | Créé | Processus 5 `generate-and-attach-help` & Gate `validate_help_article` (`< 5 s`) |
| `packages/orcia-pack-builder/src/orcia_pack_builder/__init__.py` | Modifié | Ré-export du Processus 5 et de `validate_help_article` |
| `apps/api/src/orcia_api/schemas/epic11_pack_builder.py` | Modifié | Schémas HTTP/OpenAPI Pydantic v2 Story 11.5 |
| `apps/api/src/orcia_api/routers/epic11_pack_builder.py` | Modifié | Endpoints FastAPI Processus 5 (`validate-help-article`, `generate-and-attach-help`) |
| `packages/ui/src/primitives/HelpArticleGeneratorAndValidatorView.tsx` | Créé | Primitive Direction C pour le Processus 5 (`HelpArticle` & `validate_help_article`) |
| `tests/unit/test_epic_11_story_11_5_help_generator_and_validator.py` | Créé | Tests unitaires Processus 5, validateur déterministe & API |
| `tests/integration/test_story_11_5_help_hot_attach_postgres18_redis_s3.py` | Créé | Test d'intégration réel PostgreSQL 18 + Redis 7.4 + S3 CAS (`testcontainers`) |

### 3.2 Validation des 5 Couches de Tests (`AD-17`) & Frontières (`AD-19` / `AD-20`)
- `.venv/bin/ruff check .` & `.venv/bin/ruff format --check .` : `0` erreur.
- `.venv/bin/mypy --strict packages/orcia-kernel packages/orcia-core packages/orcia-pack-sdlc packages/orcia-pack-builder apps/api apps/worker` : `0` erreur.
- `.venv/bin/lint-imports` : `5 contracts kept, 0 broken`.
- `.venv/bin/pytest tests/unit/test_epic_11_story_11_5_help_generator_and_validator.py tests/integration/test_story_11_5_help_hot_attach_postgres18_redis_s3.py` : 100 % verts.
- `pnpm turbo run lint typecheck test` : 100 % verts.
