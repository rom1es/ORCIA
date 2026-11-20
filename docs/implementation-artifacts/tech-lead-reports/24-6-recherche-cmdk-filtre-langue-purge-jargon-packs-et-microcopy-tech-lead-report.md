# Rapport Tech Lead — Story 24.6 : Recherche `Cmd+K` Filtrée par Langue, Purge du Jargon, Compteurs Packs & Microcopy

- **Story :** `24-6-recherche-cmdk-filtre-langue-purge-jargon-packs-et-microcopy` (Epic 24 — Vague 1 `P1–P3`)
- **Date :** 2026-11-20
- **Statut :** `Terminé (`done`)`
- **Plan directeur :** [`sprint-change-proposal-2026-11-20-epic-24-remediation-plan.md`](../../planning-artifacts/sprint-change-proposal-2026-11-20-epic-24-remediation-plan.md)
- **Références remédiées :** `REM24-09`, `REM24-10`, **`USER24-BUG-3`** | Constats `UX23-05` (`P1`), `UX23-08` (`P1`), `UX23-10` (`P1`), `UX23-11` (`P2`), `UX23-12` (`P2`), `UX23-16` (`P3`) | Diagnostics `ARCH24-10`, `ARCH24-11`
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
   - **Markdown brut affiché dans `/help` et Zone 4 (`USER24-BUG-3`)** : `packages/ui/src/primitives/ContextualHelpSharedBlocks.tsx:145,160-162,182-184,197-199` (« À quoi sert cet écran », « En N gestes », « Un exemple réel », « Ce qui coince souvent ») et `ContextualHelpSectionsAndFooter.tsx:45,54,111` (« Comment procéder pas à pas », « Repères & notions utiles », « Questions fréquentes », sections ciblées) affichent les chaînes Markdown brutes (`**gras**`, `` `ⓘ` ``) sans invoquer `renderInlineMarkdownNodes` / `FormattedMarkdownContent`.
3. **Compteurs `/settings/packs`, pluriels, troncatures `1440×900` & microcopy (`UX23-10`, `UX23-12`, `UX23-16`)** :
   - Sur `/settings/packs`, la grille `5` compteurs affiche des valeurs incohérentes (ex. `4 Compétences` mal alignées), et la pluralisation applique le pluriel à `n = 0` ou `n = 1` (`n <= 1` doit rester au singulier).
   - Des libellés connecteurs/agents restent bruts ; `StudioCopilotSidebar` (`291` L), `/spaces` et `IamSecopsExceptionForm.tsx` (`403` L) présentent des troncatures sur viewport `1440×900`.
   - Finitions microcopy `UX23-16` : dédoublonnage `/ontology`, `/showcase` en `4` onglets sans fuite de chemin fichier interne, `/wizards`, suppression du double espace `Mes  Espaces`, orthographe `paliers`, casse homogène `Cassette`, précision FinOps `0.002 €`.

**Critères d'acceptation :** filtre `ci.lang = locale` garanti en SQL PG18, icône `OrciaIcon` dans `Cmd+K`, rendu HTML propre (zéro `**` ou backtick brut visible) dans tous les blocs de `/help` et Zone 4 (`USER24-BUG-3`), `0` enum technique ou URI brut exposé sans traduction i18n `fr`/`en`, grille `5` compteurs `/settings/packs` juste et singulier `n <= 1`, `0` troncature à `1440×900` sur les vues ciblées.

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
   - Dans `ContextualHelpSharedBlocks.tsx` (`summaryWhatFor`, `stepByStepItems`, `realExampleText`, `pitfalls` / « Ce qui coince souvent ») et `ContextualHelpSectionsAndFooter.tsx` (`HelpAccordionSection` pour « Comment procéder pas à pas », « Repères & notions utiles », « Questions fréquentes », et `HelpTargetedSectionsList`), appliquer `renderInlineMarkdownNodes` / `FormattedMarkdownContent` pour formater `**gras**`, `*italique*` et `` `code` `` en HTML (`USER24-BUG-3`).
   - Remplacer le `0` nu dans `CatalogExplorerPanel.tsx:149` par un badge/mention lisible (« Aucun … »).
3. **Packs, troncatures `1440×900` & microcopy** :
   - Corriger la grille `5` compteurs de `/settings/packs` (`PacksRegistryPage.tsx` découpé `< 280` L), appliquer la règle française de pluralisation (`n <= 1` $\rightarrow$ singulier) et humaniser les noms de connecteurs/agents.
   - Découper `IamSecopsExceptionForm.tsx` (`403` L $\rightarrow$ `< 250` L) et corriger les largeurs responsives de `StudioCopilotSidebar` (`291` L) et `/spaces` à `1440×900`.
   - Appliquer les finitions `UX23-16` : dédoublonnage `/ontology`, `/showcase` structuré en `4` onglets sans chemin fichier exposé, `/wizards`, suppression du double espace `Mes  Espaces`, `paliers`, casse `Cassette`, formatage FinOps `0.002 €`.

### 2.5 Stratégie de Vérification & 5 Couches de Tests (`AD-17`)
- **Couche 1 (Unitaire >= 90 %)** : tests SQL/domaine vérifiant l'exclusion stricte des `HELP_ARTICLE` d'une autre langue dans `sql_federated_search.py` et validation de la règle singulier `n <= 1` + mappers i18n `fr`/`en` complets.
- **Couche 2 (Intégration `testcontainers` PG18 réel)** : requête `GET` recherche fédérée `Cmd+K` avec `locale=fr` vs `locale=en` sur articles réels en PG18 (`0` fuite linguistique) et contrôle `portal_and_help.py`.
- **Couche 3 (Composants React / Vitest)** : tests sur `ContextualHelpSharedBlocks` & `ContextualHelpSectionsAndFooter` vérifiant le rendu HTML Markdown (`<strong>`, `<code>`, zéro `**` ou backtick brut visible dans « Ce qui coince souvent » et « Questions fréquentes », `USER24-BUG-3`), `TopHeaderSearchCommand` (`OrciaIcon` sans émoji `❓`), `PermissionBrokerCard` (rendu Markdown + URI décodé), `CatalogExplorerPanel` (absence de `0` nu), `PacksRegistryPage` (`5` compteurs justes, singulier `0`/`1`), `IamSecopsExceptionForm` et détection de jargon brut résiduel.
- **Couche 4 (E2E Playwright ciblé)** : vérification `/help` + Zone 4 (accordéons « Ce qui coince souvent » et « Questions fréquentes » dépliés sans `**` brut `USER24-BUG-3`) et `1440×900` sur `/settings/packs`, `/catalog`, `/ontology`, `/showcase`, `/wizards`, `/spaces`, `/finops` (`18-catalog-packs-wizards-and-mcp-bench.spec.ts` hors `18#1` résolu en `24-7`).
- **Couche 5 (Statique & Sécurité)** : `ruff`, `mypy --strict`, `lint-imports`, `pnpm turbo run lint typecheck test`, `pnpm site:check`.

---

## 3. Bilan des Modifications & Résultats

> **Statut :** `Terminé (`done`)` — Validation 5 couches `AD-17` complète, couverture Python combinée `97 %`, `pnpm turbo run lint typecheck test` `9/9`, Playwright E2E `14 passed, 1 skipped (mobile), 0 failed`, ré-indexation GitNexus et `pnpm site:sync && pnpm site:check` validés.

### 3.1 Tableau synthétique des fichiers modifiés et créés

| Fichier / Composant | Action Réalisée | Statut |
|---|---|---|
| `packages/orcia-core/src/orcia_core/rag/_internal/sql_federated_search.py` & `two_speed_search.py` | Ajout de `normalize_search_locale` (`fr-FR` $\rightarrow$ `fr`, `en-US` $\rightarrow$ `en`), filtre SQL `:locale` sur `HELP_ARTICLE` isolé de `CATALOG_RESOURCE` et clé Redis Speed-2 par locale | `Terminé` |
| `apps/api/src/orcia_api/routers/portal_and_help.py`, `packages/api-client/` & `ShellFederatedSearchModal.tsx` | Propagation `locale` (`query` / `Accept-Language` / locale SPA) dans `GET /api/v1/search` et régénération OpenAPI `0-diff` | `Terminé` |
| `packages/orcia-core/src/orcia_core/orchestration/{assistant_three_speed_router.py,notifications_and_claims.py}` | Majuscule `"Synthèse conforme pour ..."` et humanisation `_format_step_claim_title("inbox-review-step")` | `Terminé` |
| `packages/ui/src/primitives/{ContextualHelpSharedBlocks.tsx,ContextualHelpSectionsAndFooter.tsx}` & `docs/help/{fr,en}/*.md` | **`USER24-BUG-3`** : rendu HTML (`renderInlineMarkdownNodes`) sur tous les blocs/accordéons `/help` et Zone 4 (`0` `**` / backtick brut) ; purge `` `@` `` & `L4 → L1` | `Terminé` |
| `packages/ui/src/primitives/{TopHeaderSearchResultsPane.tsx,ArbitrationTieBreakCard.tsx,PresenceClaimPill.tsx,UpstreamChallenge*.tsx,OrciaProductShowcaseSiteView.tsx,finops/*}` | Icône `OrciaIcon` (`help`) sans `❓` dans `Cmd+K`, traductions `tieBreakPolicy` / options / `temps réel`, `/showcase` en `4` espaces sans chemin interne, micro-montants `0,002 €` | `Terminé` |
| `packages/ui/src/shell/{CatalogExplorerPanel.tsx,PermissionBrokerCard.tsx,WorkflowStudioSection.tsx,types.ts}` | Remplacement `0` nu & `0.4ms` / `NEXT_SCOPE`, `Niveau principal / 1 / 2`, `<FormattedMarkdownContent />` + `safeDecodeUri` (`catch (err: unknown)`), suppression `HTTP 403` / `Step` bruts | `Terminé` |
| `apps/web/src/features/admin/iam/{IamSecopsExceptionForm.tsx,IamSecopsScopeAndTargetFields.tsx,IamSecopsVerbsCheckboxes.tsx}` | Découpage `IamSecopsExceptionForm.tsx` (`403` $\rightarrow$ `203` L) via `IamSecopsScopeAndTargetFields.tsx` (`228` L) & `IamSecopsVerbsCheckboxes.tsx` (`85` L), `Plateforme entière (Global)` (`minWidth: 240px`) | `Terminé` |
| `apps/web/src/features/settings/packs/{PackCardItem.tsx,packDisplayFormatters.ts}` & `workspaces/WorkspaceStudioCardsAndDetailView.tsx` | Grille `5` compteurs packs (`105px` auto-fit), singulier `n <= 1` FR (`n === 1` EN), humanisation connecteurs/agents, anti-troncature `1440×900` (`StudioCopilotSidebar.tsx`, `/spaces`) | `Terminé` |
| `apps/web/src/features/{cockpit/*,gates/*,admin/ai-models/AiModelReindexPanel.tsx,inbox/*,ontology/index.tsx}`, `ModuleWorkspaceView.tsx`, `lib/formatters.ts`, `i18n/locales/*` | Purge intégrale `PENDING`/`RUNNING`/`OPT_A_*`/`COMPLETED`/`PASS`/`< 15 s`/`PostgreSQL 18`, dédoublonnage `Organisation (Global)`, `paliers`, espacement `Mes Espaces`, précision `0,002 €` | `Terminé` |
| Suites QA 5 couches (`tests/unit/test_story_24_6_cmdk_locale_and_microcopy.py`, `tests/integration/test_story_24_6_cmdk_locale_postgres18.py`, `packages/ui/src/__tests__/story-24-6-help-markdown-and-zero-jargon.test.tsx`, `apps/web/src/__tests__/story-24-6-packs-counters-microcopy-and-finops.test.tsx`, `apps/web/e2e/21-*.spec.ts` + 4 tests adaptés + `anti-jargon-and-secrets-ui-audit.test.ts`) | Vérification 5 couches `AD-17` : filtre SQL `:locale` PG18 + Redis Speed-2, rendu Markdown `/help` & Zone 4 (`USER24-BUG-3`), `0` jargon brut, `5` compteurs & singulier `n <= 1`, `0,002 €` | `Terminé` |

### 3.2 Résultats chiffrés, couverture & validation 5 couches (`AD-17`)

- **Couches 1a & 2 (Python unitaire + intégration PG18/Redis `testcontainers` sur `create_app()` sans `dependency_overrides`)** :
  - `.venv/bin/pytest tests/unit/test_story_24_6_cmdk_locale_and_microcopy.py tests/integration/test_story_24_6_cmdk_locale_postgres18.py -v` $\rightarrow$ **`7 passed` (`6` unit + `1` PG18/Redis)**.
  - Couverture combinée (`.venv/bin/coverage run` sur `test_story_24_6_*`, `test_story_23_5_search_coverage.py`, `test_epic_9_*`, `test_contextual_help_route_resolution.py`, `test_epic_10_story_10_2_*`, `test_story_5_*`, `test_story_22_3_*` unitaire + PG18) : **`97 %`** (`519` stmts, `--fail-under=90` **PASS**) — `sql_federated_search.py` `100 %`, `two_speed_search.py` `99 %`, `portal_and_help.py` `98 %`, `assistant_three_speed_router.py` `98 %`, `notifications_and_claims.py` `95 %`.
- **Statique Python, Architecture & Sécurité** :
  - `.venv/bin/ruff check .` : **PASS** (`All checks passed!`) ; `.venv/bin/ruff format --check .` : **PASS** (`1315 files already formatted`).
  - `.venv/bin/mypy --strict packages/orcia-core packages/orcia-connectors apps/api apps/worker` : **PASS** (`Success: no issues found in 574 source files`).
  - `.venv/bin/lint-imports` : **PASS** (`Contracts: 5 kept, 0 broken`, `617 files`).
  - `.venv/bin/python scripts/export_openapi.py --check` : **PASS** (`0-diff`).
  - `.venv/bin/pre-commit run detect-secrets --files ...` (tous les fichiers Story 24.6 modifiés et créés) : **Passed**.
- **Couche 1b (Vitest & TypeScript Monorepo)** :
  - `pnpm turbo run lint typecheck test` : **PASS (`9 successful, 9 total`)** — `@orcia/api-client`: `3 files / 20 tests` ; `@orcia/ui`: `34 files / 135 tests` ; `@orcia/web`: `61 files / 242 tests` (`0` erreur de typecheck/lint/test).
- **Couche 5 (Playwright E2E réel `--project=desktop-cockpit --retries=0`, `ORCIA_E2E_CAMPAIGN_DIR=/tmp/orcia-e2e-story-24-6`)** :
  - `e2e/03-human-led-anchor-and-arbitration.spec.ts e2e/04-multi-actor-claim-sse.spec.ts e2e/06-gates-review-and-anti-rubber-stamping.spec.ts e2e/09-pack-builder-and-contextual-help.spec.ts e2e/10-command-palette-search.spec.ts e2e/12-finops-and-audit-provenance.spec.ts e2e/21-assistant-citations-v5-audit-help-showcase.spec.ts` $\rightarrow$ **`10 passed, 1 skipped (mobile), 0 failed` (`2.5m`)** — inclut la vérification **`USER24-BUG-3`** (`0` `**` / backtick brut, présence `<strong>`/`<code>` sur `/help` accordéons dépliés et Zone 4).
  - `e2e/18-catalog-packs-wizards-and-mcp-bench.spec.ts --grep-invert "Explorateur du catalogue fédéré"` $\rightarrow$ **`4 passed, 0 failed` (`1.1m`)**.
- **GitNexus & Documentation / Gouvernance** :
  - `npx gitnexus analyze` : `41,330 nodes | 198,174 edges | 714 clusters | 1492 flows`.
  - `gitnexus_detect_changes(repo: "/home/romain/Documents/Projects/ORCIA", scope: "all")` : `changed_count: 31`, `affected_count: 1485`, `changed_files: 56`, `risk_level: "critical"`.
  - `scripts/check_implementation_docs.py`, `lint_spine.py`, `pnpm site:sync && pnpm site:check` et `tests/unit/test_epic23_to_epic24_traceability.py` validés.
