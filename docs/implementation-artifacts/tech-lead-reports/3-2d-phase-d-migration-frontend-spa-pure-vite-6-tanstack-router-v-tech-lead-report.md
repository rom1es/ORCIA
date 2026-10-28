# Rapport Tech Lead — Analyse & Implémentation : `3-2d-phase-d-migration-frontend-spa-pure-vite-6-tanstack-router-v`

- **Story Key** : `3-2d-phase-d-migration-frontend-spa-pure-vite-6-tanstack-router-v`
- **Titre de l'US / Évolution** : Phase D — Migration Frontend SPA Pure `Vite 6 + TanStack Router v1`, Intégration `TanStack Query v5` / `Tailwind v4` / `@xyflow/react v12` / `openapi-fetch` & Découpage par Fonctionnalité `features/<domaine>/`
- **Epic** : Epic 3 : Orchestration du Cockpit, Ancrages Humains, Gouvernance des Gates & Boîte de Notifications Unifiée (`ARCH-P8`, `M11`, `C7`)
- **Date** : `2026-10-28`
- **Auteur** : `Antigravity (Tech Lead / Senior Dev Agent)`
- **Statut** : `DONE`

---

## 1. Analyse du Besoin & Étude d'Impact Tech Lead (Pré-Implémentation)

### 1.1 Contexte Métier & Problématique
Dans le cadre de l'architecture hybride ORCIA (`AD-1`, `AD-15`, `AD-19`, `P8`, `M11`, `OQ-02`, `C7`), l'interface web (`apps/web`) est un cockpit B2B authentifié qui dialogue exclusivement avec l'API Python `FastAPI` REST (`OpenAPI 3.1`) et `Server-Sent Events (SSE)`. L'utilisation historique de Next.js App Router imposait un serveur Node.js/RSC superflu en production, des risques de buffering SSE, des frictions d'hydratation sur `@xyflow/react` et l'absence de découpage modulaire par domaine (`src/features/<domaine>/`).

### 1.2 Analyse d'Impact Architecturale & GitNexus
- **Symboles et flux impactés (`gitnexus_context`, `gitnexus_impact`)** :
  - `ShellContainer` (`apps/web/src/components/ShellContainer.tsx`) : risque `LOW` (`1` appelant `RootLayout`), dépendait de `next/navigation` (`usePathname`, `useRouter`).
  - `ModuleWorkspaceView` (`apps/web/src/components/ModuleWorkspaceView.tsx`) : risque `CRITICAL` (`9` routes appelantes dans `apps/web/src/app/*/page.tsx`).
- **Conformité aux Décisions d'Architecture (`ARCHITECTURE-SPINE.md`)** :
  - `AD-1` : SPA pure `Vite 6 + TanStack Router v1` (`createRootRouteWithContext<{ queryClient: QueryClient }>()`, `validateSearch` typé, `loader` déclaratif), client OpenAPI 3.1 découpé par domaine (`packages/api-client/src/generated/<domaine>.ts` + `openapi-fetch`).
  - `AD-19` & `M11` : Découpage par fonctionnalité `apps/web/src/features/<domaine>/` (`cockpit`, `inbox`, `catalog`, `ontology`, `gates`, `finops`, `admin`, `workspaces`) avec interdiction stricte d'imports croisés inter-features et isolation de `@orcia/ui`.
- **Conformité UX/UI (`DESIGN.md` & `EXPERIENCE.md` — Direction C)** :
  - Conservation intégrale des 11 règles fondamentales UX/UI, de l'isolation de `@orcia/ui` (zéro import de `@tanstack/react-router`, `next/*` ou `@orcia/api-client`), du français par défaut (`fr`) et de l'absence de couleurs hexadécimales en dur dans `apps/web/src`.

### 1.3 Chiffres Clés & Exploration de l'Existant (Avant Modification)
- **Routes Next.js existantes** : `10` fichiers sous `apps/web/src/app/` (`layout.tsx`, `page.tsx`, `cockpit/page.tsx`, `inbox/page.tsx`, `catalog/page.tsx`, `ontology/page.tsx`, `gates/page.tsx`, `finops/page.tsx`, `workspaces/page.tsx`, `bootstrap/page.tsx`).
- **Volumétrie des fichiers clés avant intervention** :
  - `packages/api-client/src/index.ts` : `346` lignes (dépassant le seuil de 300 lignes).
  - `apps/web/src/components/ShellContainer.tsx` : `323` lignes.
  - `apps/web/src/components/ModuleWorkspaceView.tsx` : `269` lignes (concentrant l'affichage des 8 modules).

### 1.4 Opportunités de Factorisation & Découpage (Contrôle de Volumétrie)
- **Factorisation & Découpage réalisés** :
  - Découpage de `packages/api-client/src/index.ts` (`346` lignes $\rightarrow$ `48` lignes) en `3` sous-modules métier (`domains/authAndShell.ts`, `domains/catalogAndPermissions.ts`, `domains/bootstrapAndOntology.ts`) et génération automatique de `9` shards OpenAPI par domaine dans `packages/api-client/src/generated/`.
  - Découpage de `apps/web/src/components/ShellContainer.tsx` (`323` lignes $\rightarrow$ `228` lignes) via `shellPresets.ts` (`115` lignes) et `navigationAdapter.tsx` (`41` lignes).
  - Découpage de `apps/web/src/components/ModuleWorkspaceView.tsx` (`269` lignes $\rightarrow$ `67` lignes) en `8` modules autonomes `apps/web/src/features/{cockpit,inbox,catalog,ontology,gates,finops,admin,workspaces}/index.tsx`.

### 1.5 Dette Technique Identifiée & Tickets Créés
- Le ticket `ARCH-P8` dans `docs/implementation-artifacts/sprint-status.yaml` est soldé (`done`).

---

## 2. Plan d'Implémentation

### 2.1 Base de Données & Migrations Alembic
- Sans objet (Story purement Frontend SPA & SDK OpenAPI 3.1 ; la base PostgreSQL 18 reste à la révision `0012_story_3_2c`).

### 2.2 Noyau Métier (`packages/orcia-core`) & Workers (`apps/worker`)
- Sans objet.

### 2.3 API Backend (`apps/api`) & Contrat OpenAPI (`packages/api-client`)
- Mise à jour de `scripts/export_openapi.py` pour générer les shards TypeScript par domaine (`auth_and_org.ts`, `blackboard.ts`, `bootstrap.ts`, `catalog.ts`, `ontology_and_rag.ts`, `orchestration.ts`, `permission_broker.ts`, `problem_details.ts`, `shell.ts`) dans `packages/api-client/src/generated/` et les vérifier en mode `--check` (`0-diff` gate).
- Ajout de `createOrciaOpenApiFetchClient` (`openapi-fetch ^0.17.0`) dans `packages/api-client/src/index.ts`.

### 2.4 Interface Web (`apps/web`) & Design System (`packages/ui`)
- Remplacement de Next.js par `vite ^6.4.1`, `@vitejs/plugin-react ^4.5.2`, `@tanstack/react-router ^1.166.2`, `@tanstack/router-plugin ^1.166.2`, `@tanstack/react-query ^5.90.0`, `tailwindcss ^4.3.0`, `@xyflow/react ^12.12.0` et `openapi-fetch ^0.17.0`.
- Création de `apps/web/index.html`, `apps/web/vite.config.ts`, `apps/web/src/main.tsx`, `apps/web/src/router.tsx` et des `10` fichiers de routes sous `apps/web/src/routes/`.
- Création de `apps/web/eslint.config.mjs` et `apps/web/scripts/check-feature-boundaries.mjs` interdisant tout import croisé entre `src/features/<domaine_A>/` et `src/features/<domaine_B>/`.

---

## 3. Bilan des Modifications & Résultats (Post-Implémentation)

### 3.1 Fichiers Créés, Modifiés ou Supprimés

| Fichier | Action (`Créé` / `Modifié` / `Supprimé`) | Lignes (Après) | Rôle & Justification |
| --- | --- | --- | --- |
| `scripts/export_openapi.py` | `Modifié` | `211` | Génération déterministe des `9` shards OpenAPI par domaine (`0-diff`). |
| `packages/api-client/src/index.ts` | `Modifié` | `48` | Client `openapi-fetch` + façade par domaine. |
| `packages/api-client/src/domains/*.ts` | `Créé` | `72 + 123 + 121` | Découpage du SDK client par domaine (`authAndShell`, `catalogAndPermissions`, `bootstrapAndOntology`). |
| `packages/api-client/src/generated/*.ts` | `Créé` | `9` shards | Shards TypeScript générés depuis `apps/api/src/orcia_api/schemas/`. |
| `apps/web/vite.config.ts` & `apps/web/index.html` | `Créé` | `32 + 16` | Configuration et point d'entrée HTML de la SPA Vite 6. |
| `apps/web/src/router.tsx` & `apps/web/src/main.tsx` | `Créé` | `51 + 26` | Arbre de routes TanStack Router v1 + contexte `QueryClient`. |
| `apps/web/src/routes/*.tsx` & `searchSchema.ts` | `Créé` | `11` fichiers | Routes typées (`__root`, `index`, `cockpit`, `inbox`, `catalog`, `ontology`, `gates`, `finops`, `workspaces`, `bootstrap`). |
| `apps/web/src/features/<domaine>/index.tsx` | `Créé` | `8` fichiers | Modules fonctionnels isolés (`cockpit`, `inbox`, `catalog`, `ontology`, `gates`, `finops`, `admin`, `workspaces`). |
| `apps/web/src/components/ShellContainer.tsx` | `Modifié` | `228` | Conteneur Shell découplé de Next.js (`shellPresets.ts` + `navigationAdapter.tsx`). |
| `apps/web/src/components/ModuleWorkspaceView.tsx` | `Modifié` | `67` | Dispatcheur mince vers les 8 modules `src/features/<domaine>/`. |
| `apps/web/scripts/check-feature-boundaries.mjs` | `Créé` | `67` | Vérification statique d'isolation inter-features en CI (`pnpm turbo run lint`). |
| `apps/web/src/app/**`, `next.config.ts`, `next-env.d.ts` | `Supprimé` | `0` | Suppression complète du runtime serveur Next.js App Router. |

### 3.2 Chiffres Clés & Métriques de Qualité (Après Implémentation)
- **Couverture de tests unitaires Python (`orcia-kernel` + `orcia-core`)** : **`92.86%`** (objectif $\ge 90\%$).
- **Tests Frontend (`Vitest` sur `@orcia/ui`, `@orcia/api-client`, `@orcia/web`)** : **`100%` passants** (`10/10` tâches Turborepo vertes : `lint`, `typecheck`, `test`, `build`).
- **Tests E2E Multi-Acteurs (`Playwright` Desktop `1440x900` + Mobile Companion `390x844`)** : **`2 passed` (`100%`)** sur le serveur Vite 6 + TanStack Router v1.
- **Nombre de fichiers $> 350$ lignes** : **`0`**.

### 3.3 Validation des 5 Couches de Tests (`AD-17`) & Gates CI
- [x] **Couche 1 — Tests Unitaires (`pytest` + `Vitest`)** : `100%` passants (`92.86% >= 90%`).
- [x] **Couche 2 — Tests d'Intégration (`testcontainers`)** : `100%` passants.
- [x] **Couche 3 — Tests de Contrat OpenAPI 3.1 (`0-diff` SDK + `Schemathesis`)** : `export_openapi.py --check` (`0 diff` sur `openapi.json`, `schema.ts` et les `9` shards de domaine).
- [x] **Couche 4 — Tests E2E Multi-Acteurs (`Playwright` Desktop `1440x900` + Mobile `390x844`)** : `2 passed` sur Vite 6 + TanStack Router v1.
- [x] **Couche 5 — Évaluation Déterministe des Gates & Sandbox** : `0` régression.
- [x] **Linters & Typage Strict (`ruff`, `mypy --strict`, `lint-imports`, `pnpm turbo run lint typecheck`)** : `0` erreur.
- [x] **Vérification GitNexus Post-Changement (`gitnexus_detect_changes`)** : exécutée et validée avant commit.

### 3.4 Décisions Techniques Prises en Cours d'Implémentation & Points d'Attention
- L'adaptateur `OrciaNavigationProvider` (`apps/web/src/components/navigationAdapter.tsx`) permet à `ShellContainer` d'utiliser nativement `useLocation` et `router.navigate` de TanStack Router v1 lorsqu'il est monté dans `<RouterProvider>`, tout en supportant un rendu isolé dans les tests unitaires de composants sans serveur ni routeur.
