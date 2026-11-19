# Story 23.3 — Zone 4 (`Aide Contextuelle`) 100 % Fidèle à la Route, Blocs `DESIGN.md` Restaurés & Suppression de la Plomberie Interne

- **Date** : 2026-11-19
- **Story / Clé Sprint** : `23-3-zone-4-aide-contextuelle-fidele-a-la-route-et-4-blocs-design-md` (`Epic 23` — Vague 1 `P1`/`P2`)
- **Capacité(s)** : `CAP-064`, `CAP-068` — classification : `feature` + `ux` (`REM23-05` / `ARCH23-04`, `P1-UX-5`, `P2-UX-8`)
- **Auteur / Contexte** : `22.10-impl` (Sally × Winston — pré-implémentation Epic 23). Aligne la Zone 4 (`Aide Contextuelle`) sur l'écran actif (`/assistant` ≠ `/cockpit`), restaure nativement les `4` blocs prescrits par `DESIGN.md` (`À quoi sert cet écran`, `EN N GESTES`, encadré ambre `UN EXEMPLE RÉEL`, `CE QUI COINCE SOUVENT`), masque la plomberie interne (`@1.0.0`, `BASE → PACK → WORKSPACE (core)`) et signale clairement le défilement bas.
- **Commits associés** : `En attente d'implémentation (initialisé par Story 22.10)`

---

## 1. Analyse du Besoin & Étude d'Impact Tech Lead (Pré-Implémentation)

### 1.1 Contexte & Problématique
- **Preuves visuelles relevées par Sally (`notes-audit-sally-ux.md`, `P1-UX-5`, `P2-UX-8`)** :
  - Sur [`#2` (`00-stack-smoke`)](../e2e-campaign-epic-22/screenshots/00-stack-smoke/desktop-cockpit--apres-reset-jour-0-la-modale-de-premier-administrateur-est-presentee--passed.png) et [`#5` (`01-day0-boot`)](../e2e-campaign-epic-22/screenshots/01-day0-boot-and-f5-persistence/desktop-cockpit--le-premier-administrateur-cree-survit-a-un-f5-sans-localstorage-rehydratation-postgresql--passed.png) (`/cockpit`), Zone 4 affiche `Les 3 modes de réponse de Mon Assistant` dont les noms (`« Réponse rapide »`, `« Avec un agent »`, `« Analyse approfondie »`) contredisent en plus le sélecteur visible à l'écran (`Polyvalent · Standard`), et le bas de la colonne est coupé net même à `1362 px`.
  - Sur [`#7` (`02-assistant` fail)](../e2e-campaign-epic-22/screenshots/02-assistant-streaming-and-folders/desktop-cockpit--un-tour-d-assistant-traverse-le-navigateur-l-api-et-la-cassette-llm-0-et-affiche-une-rep--failed.png), [`#8` (`02-assistant` F5)](../e2e-campaign-epic-22/screenshots/02-assistant-streaming-and-folders/desktop-cockpit--un-dossier-cree-dans-un-espace-est-rehydrate-depuis-l-api-apres-un-vrai-f5-cache-navigat--passed.png) et [`#9` (`02-assistant` PG)](../e2e-campaign-epic-22/screenshots/02-assistant-streaming-and-folders/desktop-cockpit--un-dossier-survit-au-redemarrage-de-l-api-persistance-postgresql--passed.png) (`/assistant`), Zone 4 affiche encore la fiche du **Cockpit** (`ⓘ Décisions en attente et relectures : "Le Cockpit regroupe..."`) et expose `@1.0.0` + `Sources du guide : BASE → PACK → WORKSPACE (core)`.
- **Causes racines identifiées par Winston (`ARCH23-04`)** :
  1. [`ShellContextualHelpColumn.tsx#L71`](../../../apps/web/src/components/ShellContextualHelpColumn.tsx#L71) **écrase** systématiquement les sections renvoyées par `GET /api/v1/help/resolve` avec `contextualHelpArticle.sections` issues de [`_contextualHelpSections.ts#L269-L301`](../../../apps/web/src/components/_contextualHelpSections.ts#L269-L301) (`GENERAL_SECTIONS_FR`, qui injecte `"cockpit-decisions"` et `"assistant-modes"` sur toutes les routes hors `/configuration`).
  2. [`ShellContextualHelpColumn.tsx#L40-L48`](../../../apps/web/src/components/ShellContextualHelpColumn.tsx#L40-L48) pré-remplit de façon optimiste `resolvedLayers = ["BASE", "PACK", "WORKSPACE"]` et `rollbackAvailable = true` avant résolution, et `L86-L88` avale silencieusement les erreurs (`catch {}` — expliquant la dérive entre `#7` et `#8`).
  3. [`contextual_help_loader.py#L17-L32,L75-L123`](../../../packages/orcia-core/src/orcia_core/catalog/contextual_help_loader.py#L17-L32) replie les rubriques existantes de `docs/help/fr/*.md` (`## Un exemple réel` et `## Ce qui coince souvent`) dans des accordéons génériques (`key_terms_items` et `faq_items` avec `openFaq = false` dans `ContextualHelpColumnAndCenter.tsx#L93`), empêchant l'affichage des 4 blocs `DESIGN.md`.
  4. [`FourZoneHelpAsideColumn.tsx#L31-L32`](../../../packages/ui/src/primitives/FourZoneHelpAsideColumn.tsx#L31-L32) applique `maxHeight: "calc(100vh - 52px)"` avec `overflowY: auto` sans aucun indicateur visuel de défilement en bas de panneau.

### 1.2 Exploration, Analyse d'Impact GitNexus, Factorisation & Dette Technique
- **Analyse d'Impact GitNexus (`repo: "/home/romain/Documents/Projects/ORCIA"`)** :
  - `ContextualHelpResolutionService` (`packages/orcia-core/src/orcia_core/catalog/contextual_help.py:L74-L378`) :
    - `impactedCount: 7`, `risk: "CRITICAL"`, `epistemic: "exact"`, `direct: 4` (`_autonomous_supervision_ops.py`, `_sql_autonomous_rollback.py`, `autonomous_supervision.py`, `help_generator_and_validator.py`), `d=2: 3` (`orchestration/__init__.py`, `_help_orcia_docs_workflow.py`, `sql_autonomous_supervision.py`), `modules_affected: 6`.
  - `ShellContextualHelpColumn` (`apps/web/src/components/ShellContextualHelpColumn.tsx:L23-L154`) :
    - `impactedCount: 121`, `risk: "CRITICAL"`, `epistemic: "exact"`, `direct: 1` (`InnerShellContainer`), `d=2: 87`, `d=3: 33`, `processes_affected: 195`, `modules_affected: 20`.
- **Volumétrie & Refactoring (`> 300–400` L)** :
  - `packages/ui/src/primitives/ContextualHelpColumnAndCenter.tsx` mesure **`394` lignes** (au seuil de `400` L). L'ajout des blocs structurés `EN N GESTES`, encadré ambre `UN EXEMPLE RÉEL` et `CE QUI COINCE SOUVENT` imposerait de dépasser `450` L : il doit être scindé en deux primitives (`ContextualHelpColumnView.tsx` et `HelpCenterCatalogView.tsx`, `< 260` L chacune) réexportées depuis `@orcia/ui`.

---

## 2. Plan d'Implémentation

### 2.1 Schéma de Données & Migrations Alembic (`infra/migrations/versions/`)
- Aucune migration PostgreSQL requise : `catalog_items` (`HELP_ARTICLE`) stocke déjà la charge JSON / Markdown ; l'enrichissement des champs DTO extraits à la lecture (`real_example_text`, `common_pitfalls_items`) se fait de manière rétrocompatible depuis `docs/help/{fr,en}/*.md` et les articles persistés.

### 2.2 Noyau Métier Hexagonal (`packages/orcia-core/`)
1. **`packages/orcia-core/src/orcia_core/catalog/contextual_help_loader.py`** :
   - Étendre `parse_declarative_help_markdown` (`L17-L32`, `L75-L123`) pour extraire explicitement les sections dédiées :
     - `purpose_summary` (`## À quoi sert cet écran`)
     - `steps_items` (`## En N gestes` / liste numérotée)
     - `real_example_text` (`## Un exemple réel` — distinct de `key_terms_items`)
     - `common_pitfalls_items` (`## Ce qui coince souvent` — distinct de `faq_items`)
   - Conserver la rétrocompatibilité sur tout article déjà stocké en base ne contenant pas encore ces sections dédiées (fallback structuré propre sans réinjection inter-routes).
2. **`docs/help/fr/assistant.md` & `docs/help/fr/cockpit.md` (+ `en/`)** :
   - Synchroniser la terminologie du sélecteur `/assistant` (`Standard` / `Approfondi`) et vérifier l'absence stricte de tout vocabulaire d'une autre route dans chaque guide.

### 2.3 Couche Backend API, Sécurité & Contrats (`apps/api/`, `packages/api-client/`)
1. **`apps/api/src/orcia_api/schemas/catalog.py` & `routers/portal_and_help.py#L121-L151`** :
   - Enrichir `HelpArticleSchemaItem` avec `real_example_text: str | None = None` et `common_pitfalls_items: list[str] = []` (en plus des sections typées de l'article résolu).
   - Vérifier que `GET /api/v1/help/resolve` retourne les sections et blocs exclusifs de la route demandée (`route=/assistant` != `/cockpit`).
   - Régénérer `@orcia/api-client` (`openapi-typescript` `0-diff`).

### 2.4 Interface Utilisateur & Expérience (`apps/web/`, `packages/ui/`)
1. **`apps/web/src/components/contextualHelpCatalog.ts` & `_contextualHelpSections.ts`** :
   - Supprimer l'export fourre-tout `GENERAL_SECTIONS_FR/EN` mélangé à toutes les routes ; organiser les secours locaux par route exacte (`SECTIONS_BY_ROUTE["/cockpit"]`, `SECTIONS_BY_ROUTE["/assistant"]`, etc.) alignés sur `docs/help/`.
2. **`apps/web/src/components/ShellContextualHelpColumn.tsx` (`154` L)** :
   - Supprimer l'écrasement `L71` (`sections: contextualHelpArticle.sections`) lorsque `/api/v1/help/resolve` fournit les données de la route ; ne plus initialiser `resolvedLayers = ["BASE", "PACK", "WORKSPACE"]` ni `rollbackAvailable = true` de façon optimiste (`L40-L48`) — utiliser l'état de chargement puis les couches réelles retournées.
   - Remplacer le `catch {}` silencieux (`L86-L88`) par un log structuré + état d'erreur discret non bloquant si le chargement d'aide échoue.
3. **`packages/ui/src/primitives/ContextualHelpColumnView.tsx` (scindé de `ContextualHelpColumnAndCenter.tsx`) & `FourZoneHelpAsideColumn.tsx`** :
   - Rendre nativement dans Zone 4 les `4` blocs `DESIGN.md` :
     1. `À quoi sert cet écran`
     2. `EN N GESTES` (étapes numérotées lisibles)
     3. Encadré ambre dédié `UN EXEMPLE RÉEL` (accessible, contraste WCAG AA `>= 4,5:1`)
     4. `CE QUI COINCE SOUVENT` (ouvert / consultable directement sans devoir deviner un accordéon fermé)
   - Masquer la plomberie technique (`@1.0.0`, `Sources du guide : BASE → PACK → WORKSPACE (core)`) derrière un tiroir « Détails techniques » visible uniquement aux utilisateurs disposant du rôle admin (`showTechnicalMetadata`), ou replié par défaut hors inspection admin.
   - Dans `FourZoneHelpAsideColumn.tsx#L31-L32`, ajouter un indicateur visuel de défilement en pied de colonne (dégradé subtil + libellé discret *« Défiler pour voir la suite ↓ »* masqué automatiquement lorsque le bas est atteint).

### 2.5 Analyse d'Impact sur la Pyramide des Tests (`AD-17` — Couches 1 à 5 + Sécurité, Obligatoire)
- **Couche 1a (Python `pytest`)** : tests unitaires de `parse_declarative_help_markdown` (`real_example_text`, `common_pitfalls_items`, conservation contenu `assistant.md` ≠ `cockpit.md`).
- **Couche 1b (`Vitest`)** : tests `@orcia/ui` + `@orcia/web` vérifiant sur `/assistant` l'absence totale de cartes `"Le Cockpit regroupe..."` et l'affichage des 4 blocs `DESIGN.md`, l'absence d'affichage `@1.0.0` / `BASE → PACK → WORKSPACE` en mode utilisateur standard, et l'état d'erreur propre si `/api/v1/help/resolve` échoue.
- **Couche 2 (`testcontainers` PG18)** : extension de `test_contextual_help_and_accostage_postgres18.py` vérifiant les nouveaux champs OpenAPI sur `GET /api/v1/help/resolve?route=/assistant` et `?route=/cockpit`.
- **Couche 3** : `openapi-typescript` `0-diff`, `Schemathesis`, `ruff`, `mypy --strict`, `pnpm turbo run lint typecheck test`.
- **Couche 5 (E2E)** : `09-pack-builder-and-contextual-help.spec.ts` et `21-assistant-citations-v5-audit-help-showcase.spec.ts` vérifiant la fidélité route-par-route de Zone 4 après `F5`.

---

## 3. Bilan des Modifications & Résultats (Post-Implémentation)

> *[Pré-implémentation initialisée en Story 22.10 — à compléter après implémentation et validation de la Story 23.3]*

### 3.1 Fichiers Développés & Modifiés
| Fichier | Nature (Création / Modification / Refactoring) | Description synthétique |
| :--- | :--- | :--- |
| `packages/orcia-core/src/orcia_core/catalog/contextual_help_loader.py` & `docs/help/{fr,en}/*.md` | Modification | *[À compléter après implémentation Story 23.3]* |
| `apps/api/src/orcia_api/schemas/catalog.py` & `routers/portal_and_help.py` | Modification | *[À compléter après implémentation Story 23.3]* |
| `apps/web/src/components/ShellContextualHelpColumn.tsx`, `contextualHelpCatalog.ts`, `_contextualHelpSections.ts` | Modification / Refactoring | *[À compléter après implémentation Story 23.3]* |
| `packages/ui/src/primitives/ContextualHelpColumnAndCenter.tsx` & `FourZoneHelpAsideColumn.tsx` | Refactoring / Modification | *[À compléter après implémentation Story 23.3]* |

### 3.2 Résultats Chiffrés, Métriques & Qualité
- **Couverture de tests** : *[À compléter — $\ge 90\%$ requis]*
- **Qualité statique & Architecture** : `ruff`, `mypy --strict`, `openapi-typescript` `0-diff`, `pnpm typecheck`, `gitnexus_detect_changes()` *[À compléter]*

### 3.3 Validation & Procédure de Test sur Toute la Pyramide (`AD-17` + 5 Garde-Fous de Câblage Vertical)
- *[À compléter après validation `09-pack-builder` et `21-assistant-citations`]*
