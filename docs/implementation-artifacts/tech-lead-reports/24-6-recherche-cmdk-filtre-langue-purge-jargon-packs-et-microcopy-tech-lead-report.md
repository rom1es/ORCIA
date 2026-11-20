# Rapport Tech Lead — Story 24.6 : Recherche `Cmd+K` Filtrée par Langue, Purge du Jargon, Compteurs Packs & Microcopy

- **Story :** `24-6-recherche-cmdk-filtre-langue-purge-jargon-packs-et-microcopy` (Epic 24 — Vague 1 `P1–P3`)
- **Date :** 2026-11-20
- **Statut :** `En attente d'implémentation` (initialisé par `Story 23.8`)
- **Plan directeur :** [`sprint-change-proposal-2026-11-20-epic-24-remediation-plan.md`](../../planning-artifacts/sprint-change-proposal-2026-11-20-epic-24-remediation-plan.md)
- **Références remédiées :** `REM24-09`, `REM24-10` | Constats `UX23-05` (`P1`), `UX23-08` (`P1`), `UX23-10` (`P1`), `UX23-11` (`P2`), `UX23-12` (`P2`), `UX23-16` (`P3`) | Diagnostics `ARCH24-10`, `ARCH24-11`
- **Capacité(s) (`capabilities.yaml`) :** `CAP-056`, `CAP-057` (`2` capacités Desktop `failed_e2e`)
- **Classification :** `ux` (filtrage multilingue SQL, zéro jargon i18n, accessibilité & troncatures `1440×900`)

---

## 1. Analyse du Besoin & Étude d'Impact Tech Lead

### 1.1 Contexte & Critères d'Acceptation
La passe critique sur `58` captures révèle plusieurs défauts linguistiques, de jargon technique brut et de présentation sur `1440×900` :
1. **Recherche fédérée `Cmd+K` multilingue non filtrée & icône emoji (`UX23-05`, `ARCH24-10`)** : `load_federated_search_candidates_pg18` (`sql_federated_search.py:51-329`) renvoie des articles `HELP_ARTICLE` dans toutes les langues sans filtrer `ci.lang = locale`, polluant la palette française avec des résultats anglais et réciproquement. Par ailleurs, `TopHeaderSearchCommand.tsx` (`338` L) utilise un émoji rouge `❓` au lieu d'une icône vectorielle `OrciaIcon` blanche cohérente.
2. **Fuite de jargon technique brut & Markdown non rendu (`UX23-08`, `UX23-11`, `UX23-12`)** :
   - Des valeurs techniques brutes fuient directement à l'écran : `PENDING`, `RUNNING`, `PAUSE_AND_ESCALATE`, `OPT_A_*`, `1_NETWORK_TLS_ANTI_SSRF..4_HOT_DRY_RUN`, `COMPLETED`, `PASS`, `HTTP 403`, `(AD-24.7)`, `PostgreSQL 18`, `< 15 s`, `0.5 ms`, `depth=0/1`, ainsi qu'un `0` nu dans `CatalogExplorerPanel.tsx:149`.
   - `PermissionBrokerCard` affiche du Markdown brut et des URIs encodés sans décodage ni composant `FormattedMarkdownContent`.
   - Les articles `docs/help/fr/` contiennent des scories `` `@` `` et des notations internes `L4 → L1` au lieu de termes métier clairs.
3. **Compteurs `/settings/packs`, pluriels, troncatures `1440×900` & microcopy (`UX23-10`, `UX23-12`, `UX23-16`)** :
   - Sur `/settings/packs`, la grille `5` compteurs affiche des valeurs incohérentes (ex. `4 Compétences` mal alignées), et la pluralisation applique le pluriel à `n = 0` ou `n = 1` (`n <= 1` doit rester au singulier).
   - Des libellés connecteurs/agents restent bruts ; `StudioCopilotSidebar` (`291` L), `/spaces` et `IamSecopsExceptionForm.tsx` (`403` L) présentent des troncatures sur viewport `1440×900`.
   - Finitions microcopy `UX23-16` : dédoublonnage `/ontology`, `/showcase` en `4` onglets sans fuite de chemin fichier interne, `/wizards`, suppression du double espace `Mes  Espaces`, orthographe `paliers`, casse homogène `Cassette`, précision FinOps `0.002 €`.

**Critères d'acceptation :** filtre `ci.lang = locale` garanti en SQL PG18, icône `OrciaIcon` dans `Cmd+K`, `0` enum technique ou URI brut exposé sans traduction i18n `fr`/`en`, grille `5` compteurs `/settings/packs` juste et singulier `n <= 1`, `0` troncature à `1440×900` sur les vues ciblées.

### 1.2 Analyse d'Impact GitNexus (`repo: "/home/romain/Documents/Projects/ORCIA"`)
- `CatalogExplorerPanel` (`packages/ui/src/shell/CatalogExplorerPanel.tsx:49`, `310` L) : `impactedCount: 261`, `risk: "CRITICAL"`, `epistemic: "exact"` (`direct: 242`, `d=2: 19`, `processes_affected: 32`, `modules_affected: 20`).
- `load_federated_search_candidates_pg18` (`packages/orcia-core/src/orcia_core/rag/_internal/sql_federated_search.py:51-329`) : résolu dans l'index (`impactedCount: 0` en appel direct, appelé par `apps/api/src/orcia_api/routers/portal_and_help.py:106`).
- Impact API (`gitnexus api_impact`) : `apps/api/src/orcia_api/routers/portal_and_help.py` (`209` L, `4` routes HTTP).
- Inspection directe des fichiers volumineux : `PacksRegistryPage.tsx` (`381` L), `IamSecopsExceptionForm.tsx` (`403` L), `TopHeaderSearchCommand.tsx` (`338` L), `TopHeaderSearchResultsPane.tsx` (`172` L), `StudioCopilotSidebar.tsx` (`291` L).

### 1.3 Opportunités de Factorisation & Contrôle de Volumétrie (`< 350` L)
- **Découpage obligatoire `IamSecopsExceptionForm.tsx` (`403` L > seuil `400` L)** : scinder les sections du formulaire SecOps/waiver en deux sous-composants cohésifs `< 250` L et réduire les libellés larges responsables de la troncature `1440×900`.
- **Finalisation du découpage `PacksRegistryPage.tsx` (`381` L)** : isoler la grille des `5` compteurs et le panneau de détail du pack dans des sous-composants `< 250` L.
- **Dictionnaire centralisé des mappers UI d'enums** : regrouper les traductions d'étapes et statuts (`PENDING`, `RUNNING`, `PAUSE_AND_ESCALATE`, `OPT_A_*`, `1_NETWORK_TLS_ANTI_SSRF..4_HOT_DRY_RUN`, `COMPLETED`, `PASS`) dans `apps/web/src/i18n/locales/{fr,en}.ts` (injectés en props dans `@orcia/ui`) et réutiliser `FormattedMarkdownContent` dans `PermissionBrokerCard`.

---

## 2. Plan d'Implémentation

### 2.1 Couche Données & Migrations Alembic / PostgreSQL 18
- Aucune modification structurelle PG18 requise ; vérifier l'indexation de `lang` sur `catalog_items` (colonne `ci.lang`) et s'assurer que le seeder d'articles d'aide renseigne systématiquement `lang = 'fr' | 'en'`.

### 2.2 Noyau Hexagonal (`orcia-kernel` / `orcia-core`) & Workers
1. Mettre à jour `load_federated_search_candidates_pg18` (`sql_federated_search.py:51-329`) pour filtrer `HELP_ARTICLE` sur `ci.lang = :locale` (avec normalisation `fr-FR` $\rightarrow$ `fr`, fallback sûr et priorité exacte sur la locale active).
2. Nettoyer les articles Markdown `docs/help/fr/*.md` pour supprimer les artefacts `` `@` `` et la notation interne `L4 → L1`.

### 2.3 Backend FastAPI (`apps/api`) & Contrat OpenAPI (`packages/api-client`)
1. Propager explicitement la `locale` (résolue depuis `Accept-Language` / paramètre de requête / profil utilisateur) dans `apps/api/src/orcia_api/routers/portal_and_help.py:106` vers le service de recherche fédérée.
2. Vérifier que les compteurs retournés pour `/settings/packs` distinguent proprement packs, compétences (`4 Compétences` si 4 compétences actives), connecteurs et agents.

### 2.4 Interface SPA Vite + TanStack Router & Design System (`@orcia/ui` / `apps/web`)
1. **`Cmd+K` (`TopHeaderSearchCommand.tsx` `338` L & `TopHeaderSearchResultsPane.tsx` `172` L)** : remplacer l'émoji rouge `❓` par une icône vectorielle `OrciaIcon` blanche ; transmettre la locale active au client API.
2. **Zéro jargon & Markdown (`apps/web/src/i18n/locales/{fr,en}.ts`, `@orcia/ui`)** :
   - Traduire intégralement `PENDING`, `RUNNING`, `PAUSE_AND_ESCALATE`, `OPT_A_*`, `1_NETWORK_TLS_ANTI_SSRF..4_HOT_DRY_RUN`, `COMPLETED`, `PASS`, `HTTP 403`, `(AD-24.7)`, `PostgreSQL 18`, `< 15 s`, `0.5 ms`, `depth=0/1` via les dictionnaires i18n (tout en conservant les `data-status` techniques nécessaires aux assertions).
   - Rendre les conseils de `PermissionBrokerCard` via `FormattedMarkdownContent` et décoder proprement les URIs (`decodeURIComponent` sécurisé).
   - Remplacer le `0` nu dans `CatalogExplorerPanel.tsx:149` par un badge/mention lisible (« Aucun … »).
3. **Packs, troncatures `1440×900` & microcopy** :
   - Corriger la grille `5` compteurs de `/settings/packs` (`PacksRegistryPage.tsx` découpé `< 280` L), appliquer la règle française de pluralisation (`n <= 1` $\rightarrow$ singulier) et humaniser les noms de connecteurs/agents.
   - Découper `IamSecopsExceptionForm.tsx` (`403` L $\rightarrow$ `< 250` L) et corriger les largeurs responsives de `StudioCopilotSidebar` (`291` L) et `/spaces` à `1440×900`.
   - Appliquer les finitions `UX23-16` : dédoublonnage `/ontology`, `/showcase` structuré en `4` onglets sans chemin fichier exposé, `/wizards`, suppression du double espace `Mes  Espaces`, `paliers`, casse `Cassette`, formatage FinOps `0.002 €`.

### 2.5 Stratégie de Vérification & 5 Couches de Tests (`AD-17`)
- **Couche 1 (Unitaire >= 90 %)** : tests SQL/domaine vérifiant l'exclusion stricte des `HELP_ARTICLE` d'une autre langue dans `sql_federated_search.py` et validation de la règle singulier `n <= 1` + mappers i18n `fr`/`en` complets.
- **Couche 2 (Intégration `testcontainers` PG18 réel)** : requête `GET` recherche fédérée `Cmd+K` avec `locale=fr` vs `locale=en` sur articles réels en PG18 (`0` fuite linguistique) et contrôle `portal_and_help.py`.
- **Couche 3 (Composants React / Vitest)** : tests sur `TopHeaderSearchCommand` (`OrciaIcon` sans émoji `❓`), `PermissionBrokerCard` (rendu Markdown + URI décodé), `CatalogExplorerPanel` (absence de `0` nu), `PacksRegistryPage` (`5` compteurs justes, singulier `0`/`1`), `IamSecopsExceptionForm` et détection de jargon brut résiduel.
- **Couche 4 (E2E Playwright ciblé)** : vérification `1440×900` sur `/settings/packs`, `/catalog`, `/ontology`, `/showcase`, `/wizards`, `/spaces`, `/finops` (`18-catalog-packs-wizards-and-mcp-bench.spec.ts` hors `18#1` résolu en `24-7`).
- **Couche 5 (Statique & Sécurité)** : `ruff`, `mypy --strict`, `lint-imports`, `pnpm turbo run lint typecheck test`, `pnpm site:check`.

---

## 3. Bilan des Modifications & Résultats

> **Statut :** `En attente d'implémentation` — Cette section sera complétée après implémentation, passage des 5 couches `AD-17`, ré-indexation GitNexus (`npx gitnexus analyze` + `gitnexus_detect_changes()`) et exécution de `pnpm site:sync`.

| Fichier / Composant | Action Prévue | Statut |
|---|---|---|
| `packages/orcia-core/.../rag/_internal/sql_federated_search.py` | Filtre SQL `ci.lang = :locale` sur `HELP_ARTICLE` | `En attente d'implémentation` |
| `apps/api/src/orcia_api/routers/portal_and_help.py` | Propagation locale vers recherche fédérée | `En attente d'implémentation` |
| `packages/ui/src/primitives/TopHeaderSearchCommand.tsx` | Remplacement émoji `❓` par `OrciaIcon` blanc | `En attente d'implémentation` |
| `packages/ui/src/shell/CatalogExplorerPanel.tsx` & `PermissionBrokerCard` | Remplacement `0` nu (`L149`), `FormattedMarkdownContent`, URI | `En attente d'implémentation` |
| `apps/web/src/i18n/locales/{fr,en}.ts` & `docs/help/fr/*.md` | Purge enums/jargon, singulier `n <= 1`, précision FinOps | `En attente d'implémentation` |
| `PacksRegistryPage.tsx`, `IamSecopsExceptionForm.tsx`, `StudioCopilotSidebar.tsx` | Split `< 300` L, `5` compteurs packs & zéro troncature `1440×900` | `En attente d'implémentation` |
