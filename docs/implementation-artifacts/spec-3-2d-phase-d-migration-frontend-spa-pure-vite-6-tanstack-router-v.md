# Spécification Technique — Story 3.2d : Phase D — Migration Frontend SPA Pure `Vite 6 + TanStack Router v1`, Intégration `TanStack Query v5` / `Tailwind v4` / `@xyflow/react v12` / `openapi-fetch` & Découpage par Fonctionnalité `features/<domaine>/`

## 1. Contexte et Objectifs

En parallèle des `Story 3.2b` et `Story 3.2c` (`C7`, `depends_on: [ARCH-P3, ARCH-M3]`), cette story migre l'application web `apps/web` de Next.js App Router vers une SPA pure **`Vite 6 + TanStack Router v1`** (`P8`, `OQ-02`), intègre `@tanstack/react-query`, `tailwindcss`, `@xyflow/react` et `openapi-fetch`, génère le client OpenAPI 3.1 découpé par domaine dans `packages/api-client/src/generated/`, et organise `apps/web/src/` en routes minces (`src/routes/`) et modules fonctionnels isolés (`src/features/<domaine>/`, `M11`, `AD-19`).

## 2. Périmètre Technique

1. **Migration SPA Pure `Vite 6 + TanStack Router v1` (`apps/web`)** :
   - Remplacement de `next` dans `apps/web/package.json` par `vite ^6.4.1`, `@vitejs/plugin-react ^4.5.2`, `@tanstack/react-router ^1.166.2`, `@tanstack/router-plugin ^1.166.2`, `@tanstack/react-query ^5.90.0`, `tailwindcss ^4.3.0`, `@xyflow/react ^12.12.0` et `openapi-fetch ^0.17.0`.
   - Création de `apps/web/index.html`, `apps/web/vite.config.ts`, `apps/web/src/main.tsx` et `apps/web/src/router.tsx`.
   - Conversion des 10 fichiers de routes existants (`apps/web/src/app/`) vers `apps/web/src/routes/` (`__root.tsx`, `index.tsx`, `cockpit.tsx`, `inbox.tsx`, `catalog.tsx`, `ontology.tsx`, `gates.tsx`, `finops.tsx`, `workspaces.tsx`, `bootstrap.tsx`) utilisant `createRootRouteWithContext<{ queryClient: QueryClient }>()` avec `validateSearch` typé et `loader` déclaratif.
2. **Découpage Modulaire par Fonctionnalité (`apps/web/src/features/<domaine>/`, `M11`, `AD-19`)** :
   - Création des modules autonomes `cockpit`, `inbox`, `catalog`, `ontology`, `gates`, `finops`, `admin` et `workspaces` sous `apps/web/src/features/<domaine>/`.
   - Factorisation de `apps/web/src/components/ShellContainer.tsx` via `apps/web/src/components/shellPresets.ts` et `apps/web/src/components/navigationAdapter.ts` (`< 220` lignes par fichier).
   - Garde-fou d'isolation inter-features (règle de lint/vérification statique interdisant tout import direct entre `features/<domaine_A>/` et `features/<domaine_B>/`) et vérification stricte de `@orcia/ui` (zéro import de `@tanstack/react-router`, `next/*` ou `@orcia/api-client`).
3. **SDK OpenAPI 3.1 Découpé par Domaine (`packages/api-client`)** :
   - Enrichissement de `scripts/export_openapi.py` pour générer les modules de schémas par domaine sous `packages/api-client/src/generated/{auth,bootstrap,catalog,navigation,ontology,orchestration,permissions,workspaces}.ts` en plus de `schema.ts` (`0-diff` gate).
   - Intégration d'`openapi-fetch` (`createOrciaOpenApiFetchClient`) et découpage de `packages/api-client/src/index.ts` en sous-modules par domaine (`packages/api-client/src/domains/*.ts`).
