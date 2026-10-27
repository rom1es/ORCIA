# Cadre d'Exigences & Plan de Recherche (OQ-02 : Architecture Frontend `apps/web`)

## 1. Décision Instruite (`OQ-02`)
Choisir l'architecture et le framework Frontend pour `apps/web` dans le monorepo hybride **ORCIA** (`Next.js 15/16 App Router en mode Client-First UI/SPA` vs `Vite 6 + TanStack Router` vs `React Router v7 en mode SPA/Framework`), sachant que :
- Le backend **FastAPI (`apps/api`)** porte déjà 100 % de la logique métier, l'authentification OIDC/Locale, le contrôle RBAC (`RunAccessGuard`), le proxy CAS (`/api/v1/cas/*`), le contrat **OpenAPI 3.1** (`openapi-typescript` + `openapi-fetch`) et le flux temps réel **Server-Sent Events (`/api/v1/events/stream`)**.
- Le socle `@orcia/ui` (`packages/ui`) est déjà isolé de `next/*` et `@orcia/api-client`.
- **16 items / 12 stories** sont déjà livrés avec `apps/web` sous `Next.js ^15.2.0` (`App Router`, `React 19.1.0`, `Vitest ^3.0.0`, `Playwright ^1.51.0`), où les pages de routes (`apps/web/src/app/...`) sont de minces coquilles qui montent des composants clients (`"use client"`, `ModuleWorkspaceView`).

## 2. Exigences & Grille de Sélection (`Select` Shape)

### Portes éliminatoires (Hard Gates)
1. **Compatibilité React 19.1 + TypeScript 5.8 + Tailwind CSS 4 + `@xyflow/react` 12 + TanStack Query v5 + Zustand v5**.
2. **Zéro double backend / zéro duplication de logique métier** : consommation directe d'`openapi-fetch` et du flux SSE FastAPI (`/api/v1/events/stream` `< 500ms`).
3. **Isolation stricte du Design System `@orcia/ui`** (`packages/ui`) et support de la **Direction C** (Desktop Cockpit `1440x900` + Mobile Companion `390x844`).
4. **Déploiement auto-hébergé / conteneurisé simple** (Docker / Kubernetes on-prem ou cloud, sans dépendance propriétaire Vercel).

### Critères pondérés (Total = 100 %)
| Critère | Poids | Description |
| :--- | :---: | :--- |
| **C1. Adéquation au pattern Client-First / Cockpit Temps Réel (SSE + Canvas `@xyflow/react` + TanStack Query)** | **25 %** | Absence de friction RSC/SSR inutile, comportement déterministe du routage client, gestion d'état d'URL typé (filtres Centre de Pilotage `/workspaces`, onglets, sélection de Run/Step), et latence de navigation entre les 7 modules. |
| **C2. Vélocité DX, Temps de Build/HMR & Simplicité Opérationnelle en Monorepo (`Turborepo` + `pnpm`)** | **20 %** | Temps de démarrage à froid, HMR, vitesse de build CI, empreinte mémoire/CPU du serveur en conteneur Docker (ou simple service de fichiers statiques), absence de pièges de cache serveur. |
| **C3. Coût de Migration & Risque sur le Code Existant (`apps/web` à mi-parcours)** | **20 %** | Effort réel pour migrer (ou conserver) les routes existantes d'`apps/web`, les tests unitaires `Vitest` et les tests E2E `Playwright` déjà en place après 16 items livrés. |
| **C4. Sécurité Applicative & Surface d'Attaque** | **15 %** | Surface d'exposition CVE (ex. vulnérabilités middleware/RSC côté serveur vs bundle SPA statique + API FastAPI), gestion des cookies `HttpOnly` / CORS / proxy vers FastAPI. |
| **C5. Santé de l'Écosystème & Pérennité à 3–5 ans (2025–2026)** | **20 %** | Maturité en production en 2025–2026, dynamique communautaire, gouvernance open-source et coût de sortie (*exit cost*). |

## 3. Candidats Finalistes Évalués
1. **Candidat A — `Next.js 15/16 App Router` en mode strictement *Client-First UI/SPA*** (statu quo encadré : RSC limités aux layouts/shells, zéro Server Action mutante, `output: "standalone"` ou export statique/SPA).
2. **Candidat B — `Vite 6 + TanStack Router v1`** (SPA pure 100 % type-safe sur les paramètres d'URL et de recherche, couplée nativement à `@tanstack/react-query`).
3. **Candidat C — `React Router v7` (ex-Remix) en mode SPA (`ssr: false`)** avec Vite 6.

## 4. Topologie de Fan-Out (`preset = standard`, `subagents = 3`)
- **Sous-agent 1 (`d1-architecture-dx-performance`)** : Comparaison technique 2025–2026 de Next.js 15/16 (App Router pour cockpits/dashboards SPA avec backend externe Python/FastAPI) vs Vite 6 + TanStack Router vs React Router v7 SPA (build, HMR, mémoire, friction RSC, retour d'expérience à 6–12 mois).
- **Sous-agent 2 (`d2-routing-state-realtime-sse`)** : Capacités de routage typé (search params, loaders couplés à TanStack Query, `@xyflow/react`, flux SSE temps réel, gestion auth OIDC/cookies avec backend FastAPI séparé).
- **Sous-agent 3 (`d3-security-ops-migration-ecosystem`)** : Surface de sécurité (CVE Next.js 2025 vs SPA Vite), coût d'hébergement Docker/K8s auto-hébergé, santé d'écosystème 2025–2026 et coût de migration d'une application Next.js App Router Client-First vers Vite + TanStack Router.
