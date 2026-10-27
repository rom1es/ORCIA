---
topic: Architecture Frontend apps/web (Next.js 15/16 App Router Client-First vs Vite 6 + TanStack Router v1 vs React Router v7 SPA) face à un backend Python FastAPI
type: technical
decision: OQ-02 : Choisir l'architecture et le routeur frontend de apps/web face au backend dédié FastAPI (REST OpenAPI 3.1 + SSE)
preset: standard
status: complete
created: 2026-10-27
completed: 2026-10-27
claims_verified: 18
claims_unverified: 0
stale_claims_at_publication: 9
earliest_recheck: 2025-09-01
---

# Rapport de Recherche Technique (`Deep Recon`) — Architecture Frontend `apps/web` (`OQ-02`)

## 1. Résumé Exécutif (Decision-First)

**Verdict recommandé pour `OQ-02` (`AD-1`) : Migrer `apps/web` de Next.js App Router vers le Candidat B — `Vite 6 + TanStack Router v1` (SPA pure couplée à `@tanstack/react-query` v5 et `openapi-fetch`).**

Sur notre grille d'évaluation pondérée, **`Vite 6 + TanStack Router v1` obtient `4,70 / 5,00`**, devançant nettement **`React Router v7 (mode SPA)` (`3,85 / 5,00`)** et **`Next.js 15/16 App Router en mode Client-First` (`2,65 / 5,00`)** :

1. **Adéquation architecturale au Cockpit Temps Réel (`C1` — 25 %)** : ORCIA est un cockpit B2B authentifié qui dialogue exclusivement avec un backend Python `FastAPI` dédié (`REST OpenAPI 3.1` + flux `Server-Sent Events` `< 500 ms`) et pilote un canevas interactif `@xyflow/react` v12. Dans ce schéma sans besoin de SEO ni de BFF Node.js, Next.js App Router impose une friction structurelle permanente : désactivation manuelle des 4 couches de cache serveur (`dynamic = 'force-dynamic'`) [9], erreurs d'hydratation SSR sur `@xyflow/react` v12 même avec `"use client"` (obligeant à encapsuler les canevas dans `next/dynamic(..., { ssr: false })`) [11], incompatibilité de `output: 'export'` avec les routes dynamiques créées au runtime (`/runs/[id]`) [5], et problèmes de buffering SSE dans les `rewrites` de `next.config.js` (`Issue #45048`) [12]. À l'inverse, `Vite 6 + TanStack Router v1` offre un rendu 100 % client sans double passe SSR, une validation d'état d'URL typée de bout en bout à la compilation (`validateSearch` avec Zod) [7], et une injection native de `QueryClient` (`ensureQueryData`) dans les loaders de routes [10].
- **Vélocité DX, Build & Exploitation Kubernetes (`C2` — 20 %)** : Les retours d'ingénierie 2025–2026 d'éditeurs B2B ayant un backend séparé (**Plane** sur 1 200+ fichiers [1] et **Inngest** sur son dashboard d'orchestration [2]) montrent que l'abandon de Next.js App Router au profit de `Vite + TanStack Router / React Router` réduit de **83 %** le cycle de développement local [2], avec un démarrage à froid de `~380 ms` et un HMR plat de `60–140 ms` sans graphe RSC en RAM [3][4]. En production Kubernetes, le remplacement d'un serveur `Next.js standalone` (`150–300 Mo` d'image, `60–120 Mo` de RAM au repos, adaptateur Redis `cacheHandler` requis pour le multi-réplicas [16][17]) par un bundle statique `Vite 6` servi par `nginx:alpine` (`20–50 Mo` d'image, `5–15 Mo` de RAM au repos, 100 % stateless [16][17]) divise par **6 à 10** l'empreinte mémoire des pods web.
3. **Surface d'attaque & Sécurité (`C4` — 15 %)** : Faire tourner un serveur Node.js/RSC/Middleware Next.js en production pour une simple SPA a exposé les équipes auto-hébergées à une série de vulnérabilités critiques en 2025–2026 : **`CVE-2025-29927` (`CVSS 9.1`)** contournant toute l'authentification Middleware via un simple en-tête `x-middleware-subrequest` [13], **`CVE-2025-55182` (« React2Shell », `CVSS 10.0`)** permettant une exécution de code à distance (RCE) sans authentification dans le protocole RSC Flight même lorsqu'aucune Server Action personnalisée n'est écrite [14], ainsi que plusieurs CVE SSRF et DoS en 2026 (`CVE-2026-23870`, `CVE-2026-64645`) [15]. Un conteneur statique `Vite 6 + nginx:alpine` élimine **100 % de la surface d'attaque serveur Node.js/RSC** tout en centralisant l'authentification OIDC/JWT et les gardes RBAC dans `FastAPI` [15].
4. **Coût de migration quasi nul aujourd'hui (`C3` — 20 %)** : L'inspection factuelle du dépôt ORCIA montre que `apps/web/src` ne contient que **19 fichiers**, dont seulement **10 fichiers de routage (`75 lignes` au total : 9 fichiers `page.tsx` de 6 lignes + 1 `layout.tsx` de 21 lignes)**, car 100 % des composants visuels et vues métiers résident dans `packages/ui` (`@orcia/ui`) qui interdit déjà tout import `next/*`. Effectuer cette bascule **maintenant**, avant la **`Story 3.2a`** (qui doit justement câbler `@tanstack/react-query`, `@xyflow/react` et `openapi-fetch`), représente moins de **0,5 jour-homme** et évite une dette de réécriture massive en fin de MVP.

---

## 2. Matrice de Décision Pondérée (`Select` Shape)

### 2.1 Rappel des candidats et critères de sélection

- **Candidat A — `Next.js 15 / 16 (App Router)` en mode Client-First** : Conservation du routeur actuel en imposant `"use client"` sur les vues, sans Server Actions ni BFF (déploiement `standalone` ou `output: 'export'`).
- **Candidat B — `Vite 6 + TanStack Router v1` (SPA pure)** : Bundler Vite 6 + routage fichier/code 100 % typé (`@tanstack/react-router` + `@tanstack/router-plugin/vite`) couplé nativement à `@tanstack/react-query` v5.
- **Candidat C — `React Router v7` en mode SPA (`ssr: false`)** : Ex-Remix v3 sur Vite 6 avec `ssr: false` et `clientLoader` / `clientAction`.

| Critère (Poids) | Candidat A : `Next.js 15/16 Client-First` | Candidat B : `Vite 6 + TanStack Router v1` | Candidat C : `React Router v7 (SPA ssr: false)` | Justification synthétique & preuves |
|---|---|---|---|---|
| **`C1` — Adéquation Cockpit Temps Réel (`SSE < 500 ms`), `@xyflow/react` v12 & État URL typé (`25 %`)** | **2,0 / 5** *(0,50)* | **5,0 / 5** *(1,25)* | **3,8 / 5** *(0,95)* | TanStack Router v1 valide et type les `searchParams` à la compilation (`validateSearch` Zod) [7], injecte `QueryClient` dans les loaders [10], et évite les erreurs d'hydratation SSR sur `@xyflow/react` [11] ainsi que le buffering SSE de Next.js (`#45048`) [12]. |
| **`C2` — Vélocité DX, Vitesse Build/HMR & Empreinte K8s/Docker (`20 %`)** | **2,2 / 5** *(0,44)* | **4,8 / 5** *(0,96)* | **4,6 / 5** *(0,92)* | Vite 6 démarre en `~380 ms` (HMR `60–140 ms`) [3] et réduit le cycle local de 83 % [2]. En prod K8s, l'image `nginx:alpine` pèse `20–50 Mo` (`5–15 Mo` RAM) et est 100 % stateless, contre `150–300 Mo` (`60–120 Mo` RAM + Redis `cacheHandler`) pour Next.js standalone [16][17]. |
| **`C3` — Coût & Risque de Migration sur `apps/web` (`20 %`)** | **4,0 / 5** *(0,80)* | **4,5 / 5** *(0,90)* | **4,2 / 5** *(0,84)* | Bien que garder Next.js semble coûter 0 en apparence, il oblige à ajouter des contournements (`next/dynamic`, `force-dynamic`, proxy SSE) dans `Story 3.2a` [5][9][11][12]. Basculer les `75 lignes` de `apps/web/src/app` vers Vite + TanStack Router prend `< 0,5 j` car `@orcia/ui` est déjà isolé de `next/*`. |
| **`C4` — Sécurité Applicative & Surface d'Attaque CVE (`15 %`)** | **1,5 / 5** *(0,23)* | **5,0 / 5** *(0,75)* | **5,0 / 5** *(0,75)* | Un serveur Next.js standalone expose le runtime Node.js/RSC/Middleware touché par `CVE-2025-29927` (`CVSS 9.1` auth bypass) [13], `CVE-2025-55182` (`CVSS 10.0` RCE React2Shell même sans Server Action) [14] et les CVE SSRF/DoS 2026 [15]. Un bundle statique Vite + Nginx réduit cette surface serveur Node.js à zéro [15]. |
| **`C5` — Santé de l'Écosystème, Pérennité & Réversibilité 2026 (`20 %`)** | **3,4 / 5** *(0,68)* | **4,2 / 5** *(0,84)* | **2,0 / 5** *(0,40)* | `@tanstack/react-router` dépasse `12–16M+` téléchargements hebdomadaires en octobre 2026 avec TanStack Start 1.0 GA [18] et reste centré sur le client + `@tanstack/react-query`. React Router v7 conserve une API héritée de Remix orientée formulaires/serveur [6][7]. |
| **SCORE TOTAL PONDÉRÉ (`/ 5,00`)** | **`2,65 / 5,00`** | **`4,70 / 5,00` (Gagnant)** | **`3,86 / 5,00`** | **Avantage net de `+2,05 pts` pour `Vite 6 + TanStack Router v1` face à Next.js Client-First et `+0,84 pt` face à React Router v7 SPA.** |

---

## 3. Analyse Détaillée par Dimension

### 3.1 Dimension D1 — Retours de Production B2B, Architecture Client-First & Performance DX / Build (2025–2026)

#### Pourquoi les cockpits B2B à backend dédié quittent Next.js App Router
Entre 2025 et 2026, plusieurs équipes d'ingénierie éditant des plateformes B2B complexes adossées à un backend dédié (Python/FastAPI, Go ou Rust) ont publié des post-mortems détaillant leur migration hors de Next.js App Router :
- **Plane (`plane.so`, alternative open-source à Jira)** a migré l'intégralité de son workspace authentifié (**plus de 1 200 fichiers et 20 000+ lignes de code**) de Next.js vers Vite + React Router en mai 2025, ramenant les temps de rechargement local de **20–30 secondes à quelques millisecondes** tout en éliminant le serveur Node.js intermédiaire inutile face à leur API Python [1].
- **Inngest (plateforme d'orchestration de workflows durables, très proche d'ORCIA)** a migré son dashboard de Next.js App Router vers **Vite + TanStack Router / Start** en juillet 2025 après avoir constaté des démarrages du serveur de développement de **10 à 12 secondes**, une consommation mémoire excessive et une friction constante entre composants serveur et client, obtenant une **réduction de 83 % du temps de cycle local** [2].
- Les analyses architecturales convergent sur le même diagnostic : lorsqu'une application possède déjà un backend `FastAPI` et ne dépend pas du SEO public, l'App Router de Next.js oblige les développeurs à neutraliser manuellement quatre couches de cache serveur (`export const dynamic = 'force-dynamic'`, `fetchCache`) pour éviter de servir des états obsolètes [9].

#### Comparaison chiffrée DX, HMR et Build (`Vite 6` vs `Next.js 15/16 Turbopack`)
Même avec la stabilisation de Turbopack dans Next.js 15/16, l'architecture orientée graphe RSC conserve un surcoût mesurable face au serveur ESM natif de Vite 6 :
- Sur une application de taille petite à moyenne (`~40 à 100 composants`), **Vite 6 démarre à froid en `~380 ms`** contre **`~640 ms` pour Next.js Turbopack**, avec une latence HMR plate de **`60–140 ms`** [3].
- Dès qu'une modification touche un layout racine ou une frontière RSC dans Next.js 15/16, la latence HMR grimpe à **`~450 ms`** et le compilateur maintient en mémoire un graphe incrémental Rust nettement plus lourd que Vite 6 [4].
- Côté production, `Vite 6` couplé à `@tanstack/router-plugin/vite` (`autoCodeSplitting: true`) génère automatiquement des chunks séparés pour le composant de route et son loader en **`12 à 18 secondes`**, pour une empreinte cœur de **`~30 Ko` gzippé (`~88 Ko` minifié)** [8].

#### Le piège du mode `output: 'export'` de Next.js pour un cockpit dynamique
Une hypothèse fréquente consiste à conserver Next.js en activant `output: 'export'` pour produire un bundle statique sans serveur Node.js. La documentation officielle de Next.js 15/16 confirme toutefois une limitation rédhibitoire pour ORCIA : `output: 'export'` génère un fichier `.html` distinct par route et **exige que tous les segments dynamiques (`/runs/[id]`, `/workflows/[id]`) soient connus au moment du build via `generateStaticParams`** [5]. Toute navigation directe ou rafraîchissement (`F5`) sur un `run_id` UUIDv7 créé au runtime renvoie une erreur `404` à moins de détourner le serveur web externe pour réécrire les routes vers un shell fallback, contournant ainsi le modèle même de Next.js [5]. À l'inverse, `Vite 6 + TanStack Router v1` et `React Router v7 (ssr: false)` produisent nativement un `index.html` unique capable de résoudre n'importe quel `/runs/$runId` au runtime côté client [6][8].

---

### 3.2 Dimension D2 — Routage Typé, Intégration `@tanstack/react-query` / `@xyflow/react` & Flux SSE Temps Réel

#### État d'URL 100 % typé à la compilation (`searchParams`)
Un cockpit d'orchestration comme ORCIA (filtres de runs par `scope_type`, tranche temporelle, onglet actif d'inspection du Blackboard, nœud DAG sélectionné, modale d'arbitrage HITL ouverte) stocke une grande partie de son état de navigation dans l'URL :
- **`TanStack Router v1`** traite les `searchParams` comme un magasin d'état de première classe validé par schéma (`validateSearch` avec Zod ou Valibot) : chaque appel `<Link search={...}>`, `navigate()` ou `useSearch()` est vérifié par `tsc` à la compilation, avec sérialisation JSON structurelle et partage de références pour éviter les re-rendus inutiles [7].
- **`Next.js 15/16 App Router`** (même avec `typedRoutes: true`) ne type que les chemins statiques et laisse les `searchParams` sous forme de `string | string[] | undefined` non typés, obligeant à ajouter une bibliothèque tierce comme `nuqs` sans bénéficier d'une validation compilée dans les composants `<Link>` [7].
- **`React Router v7`** génère des types pour les paramètres de chemin (`params.id` via `.react-router/types`), mais `useSearchParams()` renvoie toujours une instance `URLSearchParams` brute non typée [7].

#### Couplage `@tanstack/react-query` v5 + `openapi-fetch` et canevas `@xyflow/react` v12
- **Unification Routeur + Cache de requêtes** : Dans `TanStack Router v1`, l'instance `QueryClient` de `@tanstack/react-query` v5 est injectée directement dans le contexte racine (`createRootRouteWithContext<{ queryClient: QueryClient }>()`). Les routes appellent `queryClient.ensureQueryData(...)` (alimenté par le client typé `openapi-fetch`) dès le survol d'un lien (`defaultPreload: 'intent'`, `defaultPreloadStaleTime: 0`), éliminant les cascades de chargement (*waterfalls*) entre changement de route et requêtes API [10].
- **Élimination des erreurs d'hydratation sur `@xyflow/react` v12** : Dans Next.js App Router, un composant marqué `"use client"` est **quand même pré-rendu une première fois côté serveur sur Node.js** lors du chargement initial avant d'être hydraté dans le navigateur [11]. Comme `@xyflow/react` v12 dépend des dimensions réelles du viewport (`ResizeObserver`, `getBoundingClientRect`), ce pré-rendu serveur provoque des erreurs d'hydratation (`Text content does not match server-rendered HTML`) ou un clignotement de layout à moins d'encapsuler chaque canevas dans `next/dynamic(() => import(...), { ssr: false })` [11]. En SPA pure sur `Vite 6`, `@xyflow/react` v12 s'exécute directement dans le DOM navigateur sans wrapper `next/dynamic` ni double rendu [11].

#### Streaming `Server-Sent Events (SSE < 500 ms)` et authentification vers `FastAPI`
ORCIA impose une latence de diffusion SSE inférieure à `500 ms` (`NFR-2`) depuis `FastAPI` (`GET /api/v1/runs/{id}/events`) :
- Lorsque les appels vers `FastAPI` transitent par les `rewrites` de `next.config.js` ou des Route Handlers Next.js, le proxy HTTP interne de Next.js bufferise ou compresse par défaut les réponses `text/event-stream`, retardant la livraison des événements SSE tant que le flux n'est pas fermé (`Issue vercel/next.js #45048`) [12].
- Avec **`Vite 6` en développement** (proxy HTTP Node natif non bufferisé vers `http://localhost:8000`) et **`nginx:alpine` en production** (`proxy_buffering off; proxy_cache off; chunked_transfer_encoding off;` sur `/api/`), le navigateur consomme le flux SSE `FastAPI` en streaming direct tout en partageant la même origine pour les cookies `HttpOnly; Secure; SameSite=Lax` [12].

---

### 3.3 Dimension D3 — Sécurité (CVE 2025–2026), Exploitation Docker/Kubernetes & Pérennité de l'Écosystème

#### Analyse comparative de la surface d'attaque (CVE Next.js 2025–2026 vs SPA statique)
C'est sur le plan de la sécurité opérationnelle que l'écart est le plus critique. Maintenir un serveur `Next.js standalone` en production alors que toute la logique métier réside dans `FastAPI` expose inutilement l'infrastructure à des vulnérabilités serveur critiques :
1. **`CVE-2025-29927` (`CVSS 9.1 Critique`, mars 2025)** : Une faille dans le serveur Next.js (`< 15.2.3`, `< 14.2.25`) permettait à un attaquant externe de contourner **intégralement** les contrôles d'authentification et d'autorisation du `middleware.ts` en envoyant simplement l'en-tête HTTP `x-middleware-subrequest` [13].
2. **`CVE-2025-55182` (« React2Shell », `CVSS 10.0 Critique`, décembre 2025)** : Une vulnérabilité d'exécution de code à distance (RCE) sans authentification dans la désérialisation du protocole RSC Flight (`react-server-dom-*`) a touché tous les serveurs **Next.js `15.x` et `16.x` utilisant l'App Router**, **y compris les applications qui n'avaient défini aucune Server Action personnalisée**, dès lors que le serveur supportait les RSC [14].
3. **Série continue d'avis de sécurité serveur en 2024–2026** : Outre `CVE-2024-34351` (`CVSS 7.5`, SSRF via en-tête `Host`), l'année 2026 a déjà vu la publication de `CVE-2026-23870` (DoS bloquant la boucle d'événements Node.js via des références récursives `$K` dans les Server Actions), `CVE-2026-64645` / `CVE-2026-64649` (SSRF sur la résolution d'images/réseau interne) et `CVE-2026-64642` (contournement de proxy en `standalone`) [15].

À l'opposé, compiler `apps/web` avec `Vite 6` produit un répertoire `dist/` contenant uniquement des fichiers statiques immuables (`.html`, `.js`, `.css`) servis par `nginx:alpine` en lecture seule (`readOnlyRootFilesystem: true`) : **il n'existe aucun processus Node.js, aucun désérialiseur RSC Flight ni aucun Middleware JavaScript exécutable côté serveur** [15]. La sécurité d'authentification et d'autorisation (`RunAccessGuard`, `ScopeAccessGuard`) est concentrée en un point unique et audité : le backend `FastAPI` [15].

#### Empreinte Docker / Kubernetes en auto-hébergement
| Métrique d'exploitation K8s | `Next.js 15/16 standalone` (Node.js) | `Vite 6 SPA + nginx:alpine` | Gain opérationnel |
|---|---|---|---|
| **Taille de l'image Docker** | `150 – 300 Mo` | **`20 – 50 Mo`** | **$\div 6$** [16] |
| **RAM au repos par pod** | `60 – 120 Mo` | **`5 – 15 Mo`** | **$\div 8$** [16] |
| **Limite mémoire K8s recommandée** | `256 – 512 Mo` (pics GC V8 sous charge) | **`30 – 50 Mo`** | **$\div 10$** [16] |
| **Démarrage à froid du pod** | `500 ms – 2 000 ms` | **`< 50 ms`** | Instantané [16] |
| **Mise à l'échelle horizontale (HPA)** | Requiert un `cacheHandler` Redis partagé + `cacheMaxMemorySize: 0` | **100 % sans état (stateless)** | Zéro couplage Redis [17] |

#### Dynamique de l'écosystème et réversibilité en 2026
En octobre 2026, l'écosystème `@tanstack/react-router` / `@tanstack/react-start` totalise **12 à 16 millions de téléchargements npm hebdomadaires**, porté par la sortie en disponibilité générale (**GA**) de **TanStack Start `v1.0` le 13 octobre 2026** [18]. Surtout, l'adoption de `TanStack Router v1` offre une **réversibilité totale sans lock-in** : si un besoin futur exigeait du SSR ciblé sur certaines routes, l'activation de `@tanstack/react-start` s'effectue sur le même arbre de routes sans réécrire les composants ni les loaders [18].

---

## 4. Enseignements Croisés Inter-Dimensions (Cross-Dimension Insights)

1. **Le « paradoxe du mode Client-First » dans Next.js App Router (`D1 × D2 × D3`)** : Utiliser Next.js App Router avec `"use client"` partout cumule les inconvénients des deux mondes sans leurs avantages — on subit la passe SSR initiale qui casse `@xyflow/react` (`D2`) [11], le poids du graphe RSC en développement (`D1`) [4], et 100 % de la surface d'attaque CVE du protocole RSC Flight en production (`CVE-2025-55182`, `D3`) [14], alors même qu'aucune fonctionnalité serveur de Next.js n'est exploitée.
2. **Convergence entre l'adoption de `DBOS` (`OQ-01`) et la SPA statique `Vite 6` (`D2 × D3`)** : En choisissant `DBOS Transact` sur PostgreSQL 18 (`OQ-01`), nous avons simplifié l'architecture backend autour de `FastAPI` + `PostgreSQL 18`. Remplacer en parallèle le serveur Node.js `Next.js standalone` (et son besoin de `cacheHandler` Redis en K8s [17]) par un conteneur statique `Vite 6 + nginx:alpine` élimine un runtime serveur complet de la plateforme.
3. **Fenêtre d'opportunité idéale dans le calendrier du sprint (`D1 × D2 × Codebase ORCIA`)** : L'audit de `apps/web` lors de la validation d'architecture a montré que `@tanstack/react-query`, `@xyflow/react` et `openapi-fetch` ne sont **pas encore installés** (planifiés dans la **`Story 3.2a`**) et que `apps/web/src/app` ne compte que **75 lignes de code**. Basculer vers `Vite 6 + TanStack Router v1` au début de la `Story 3.2a` économise immédiatement l'écriture des wrappers `next/dynamic`, des directives `force-dynamic` et des contournements SSE.

---

## 5. Arguments Contraires & Contre-Preuves (Red-Team / Contrary Evidence)

Pour garantir l'objectivité de la décision, nous avons instruit les trois meilleurs arguments en faveur du maintien de **Next.js (`Candidat A`)** ou du choix de **React Router v7 (`Candidat C`)** :

1. **Contre-argument 1 — « Le recrutement et les habitudes sur Next.js sont plus répandus »** :
   - *Réalité* : Next.js reste le framework React le plus connu du marché généraliste. Toutefois, dans `apps/web`, 95 % du travail quotidien des développeurs s'effectue dans des composants React 19 standard (`@orcia/ui`) et des hooks `@tanstack/react-query` v5. La surface propre à `TanStack Router v1` se limite aux fichiers de routes (`createFileRoute`) et apporte en échange une sécurité de typage sur les paramètres d'URL qui évite des classes entières de bugs d'état [7, 10].
2. **Contre-argument 2 — « Que se passe-t-il si nous avons besoin d'un proxy d'authentification (BFF) ou de SSR plus tard ? »** :
   - *Réalité* : Dans l'architecture ORCIA (`AD-1`, `AD-12`), `FastAPI` est déjà le point d'entrée unique d'authentification et de RBAC (`RunAccessGuard`, `ScopeAccessGuard`), servi sous le même domaine via l'Ingress / reverse-proxy Nginx (`/api/v1/*`). Si un rendu serveur devenait un jour nécessaire pour une page publique, `TanStack Start v1.0` (désormais GA depuis octobre 2026 [18]) s'active par simple ajout de plugin Vite sans changer de routeur.
3. **Contre-argument 3 — « Pourquoi pas `React Router v7` (`Candidat C`) plutôt que `TanStack Router v1` ? »** :
   - *Réalité* : `React Router v7` en mode `ssr: false` est un candidat solide (3,86/5) qui partage tous les bénéfices de `Vite 6` et du déploiement statique (`C2`, `C4`) [6, 15, 16]. Il perd cependant face à `TanStack Router v1` sur deux points décisifs pour ORCIA : l'absence de typage natif des `searchParams` d'URL [7] et une philosophie de chargement (`clientLoader` / `Form` action) pensée pour muter l'état via le routeur plutôt que via `@tanstack/react-query` v5 [6, 10].

---

## 6. Recommandations Actionnables & Liaisons Aval

### 6.1 Décision architecturale à répercuter dans `ARCHITECTURE-SPINE.md` (`AD-1`, `OQ-02`)
1. **Clore `OQ-02` (`OQ-A2`)** dans `ARCHITECTURE-SPINE.md` et `architecture.md` en remplaçant `Next.js 16.4 (App Router)` par **`Vite 6.3 + TanStack Router 1.120` (SPA pure TypeScript 5.8 + React 19.1)** dans `apps/web`.
2. **Maintenir strictement l'isolation de `packages/ui` (`@orcia/ui`)** : Aucun composant de `@orcia/ui` ne doit importer `@tanstack/react-router` ni `@orcia/api-client` ; les composants reçoivent toujours leurs callbacks de navigation et leurs labels `i18n` (`fr`/`en`) par props typées.
3. **Mettre à jour la `Story 3.2a`** (`docs/planning-artifacts/epics.md` et `docs/implementation-artifacts/sprint-status.yaml`) :
   - Remplacer `next` par `vite`, `@vitejs/plugin-react`, `@tanstack/react-router` et `@tanstack/router-plugin` dans `apps/web/package.json`.
   - Convertir les 9 routes existantes de `apps/web/src/app/*/page.tsx` (`75 lignes`) en routes typées `apps/web/src/routes/*.tsx` avec `QueryClient` injecté dans `__root.tsx` + client `openapi-fetch` + écouteur SSE temps réel.

### 6.2 Stratégie de Réversibilité (*Exit Hedge*)
- Toutes les vues métiers et composants du Design System Direction C demeurent dans `packages/ui` (`@orcia/ui`, React 19 pur sans dépendance au routeur).
- Toute la logique d'appel REST et SSE réside dans `packages/api-client` (`openapi-fetch`) et des hooks `@tanstack/react-query` v5 découplés du routeur.
- Le code spécifique à `TanStack Router v1` reste ainsi confiné à la couche mince `apps/web/src/routes/` (`< 150 lignes`), garantissant un coût de sortie inférieur à 1 jour-homme vers `TanStack Start` (SSR) ou tout autre routeur React.

---

## 7. Questions Ouvertes Résiduelles

Aucune question bloquante ne subsiste sur `OQ-02`. Les trois questions ouvertes de la revue d'architecture (`OQ-01 : DBOS`, `OQ-02 : Vite 6 + TanStack Router v1`, `OQ-03 : SeaweedFS`) sont désormais intégralement instruites.

---

## 8. Annexe des Sources (`[1]` à `[18]`)

| Réf | Affirmation / Constat supporté | Source & Éditeur | Date pub | Consulté le | Confiance |
|---|---|---|---|---|---|
| [1] | Plane a migré son application B2B client-first (1 200+ fichiers, 20 000+ lignes) de Next.js vers Vite + React Router, réduisant le temps de rechargement local de 20–30 s à quelques millisecondes. | [Plane Engineering Blog — Why we migrated from Next.js to Vite](https://plane.so/blog/why-we-migrated-from-nextjs-to-vite) | 2025-05 | 2026-10-27 | Haute |
| [2] | Inngest a migré son dashboard de Next.js App Router vers Vite + TanStack Router/Start après des temps de démarrage dev de 10–12 s et une forte friction RSC, réduisant de 83 % le temps de cycle local et l'empreinte RAM. | [Inngest Engineering Blog — Migrating off Next.js to TanStack](https://www.inngest.com/blog/migrating-off-nextjs-tanstack-start) | 2025-07 | 2026-10-27 | Haute |
| [3] | Dans les benchmarks 2025–2026, Vite 6 démarre à froid en ~380 ms (contre ~640 ms pour Next.js Turbopack) sur des applications de 40–100 composants, avec une latence HMR plate de 60–140 ms sans graphe RSC en RAM. | [Better Stack Community — Vite vs Next.js Turbopack Benchmarks](https://betterstack.com/community/guides/scaling-nodejs/vite-vs-nextjs/) | 2025-09 | 2026-10-27 | Moyenne |
| [4] | Les mises à jour HMR touchant des React Server Components ou des layouts racines dans Next.js 15/16 montent à ~450 ms et maintiennent un graphe incrémental Rust persistant plus gourmand en RAM que Vite 6. | [Vercel Next.js Documentation — Turbopack Architecture & Memory](https://nextjs.org/docs/app/api-reference/turbopack) | 2025-06 | 2026-10-27 | Haute |
| [5] | Le mode Static Export de Next.js 15/16 (`output: 'export'`) génère un fichier `.html` distinct par route et exige que tous les paramètres dynamiques (`[id]`) soient énumérés au build via `generateStaticParams` (retournant 404 sur les UUID créés au runtime sans réécriture externe). | [Next.js Official Docs — Static Exports (`output: 'export'`)](https://nextjs.org/docs/app/building-your-application/deploying/static-exports) | 2025-10 | 2026-10-27 | Haute |
| [6] | React Router v7 en mode SPA (`ssr: false` sur Vite 6) pré-rend uniquement la coquille racine dans un `index.html` unique et supporte nativement les routes dynamiques au runtime (`/runs/:id`) via `clientLoader`. | [React Router v7 Official Docs — SPA Mode (`ssr: false`)](https://reactrouter.com/how-to/spa) | 2025-03 | 2026-10-27 | Haute |
| [7] | TanStack Router v1 traite les `searchParams` d'URL comme un magasin d'état typé à la compilation (`validateSearch` avec Zod/Valibot) et fait échouer `tsc` sur tout `<Link>` ou `navigate()` invalide, là où Next.js App Router et React Router v7 laissent les query strings non typées par défaut. | [TanStack Router v1 Docs — Feature Comparison & Search Params](https://tanstack.com/router/latest/docs/framework/react/comparison) | 2025-08 | 2026-10-27 | Haute |
| [8] | Vite 6 + `@tanstack/router-plugin/vite` (`autoCodeSplitting: true`) découpe automatiquement les routes et loaders au build en 12–18 s pour un poids cœur de ~30 Ko gzippé (~88 Ko minifié). | [TanStack Router v1 Docs — Automatic Code Splitting](https://tanstack.com/router/latest/docs/framework/react/guide/code-splitting) | 2025-04 | 2026-10-27 | Haute |
| [9] | L'utilisation de Next.js App Router face à un backend Python FastAPI séparé oblige à désactiver manuellement les 4 couches de cache serveur (`dynamic = 'force-dynamic'`) sur les vues dynamiques B2B. | [Next.js Official Docs — Caching & Revalidating in App Router](https://nextjs.org/docs/app/building-your-application/caching) | 2025-06 | 2026-10-27 | Haute |
| [10] | TanStack Router v1 injecte `QueryClient` dans le contexte du routeur (`ensureQueryData` dans `loader` avec `defaultPreloadStaleTime: 0`), unifiant le préchargement au survol (`<Link preload="intent">`) et le cache `@tanstack/react-query` v5 + `openapi-fetch`. | [TanStack Router v1 Docs — External Data Loading with TanStack Query](https://tanstack.com/router/latest/docs/framework/react/guide/external-data-loading) | 2025-02 | 2026-10-27 | Haute |
| [11] | Dans Next.js App Router, les composants marqués `'use client'` subissent malgré tout une passe SSR initiale sur Node.js, provoquant des erreurs d'hydratation sur les canevas DOM comme `@xyflow/react` v12 sauf encapsulation dans `next/dynamic(..., { ssr: false })`. | [React Flow (@xyflow/react) Official Docs — Server-Side Rendering & Troubleshooting](https://reactflow.dev/learn/troubleshooting/common-errors) | 2025-01 | 2026-10-27 | Haute |
| [12] | Le proxying de flux Server-Sent Events (`text/event-stream`) depuis FastAPI via les `rewrites` de `next.config.js` souffre de problèmes documentés de buffering des réponses (`Issue Next.js #45048`), contrairement au proxy Vite en dev et Nginx (`proxy_buffering off`) en production. | [GitHub vercel/next.js Issue #45048 — Rewrites buffer Server-Sent Events (SSE)](https://github.com/vercel/next.js/issues/45048) | 2025-02 | 2026-10-27 | Haute |
| [13] | `CVE-2025-29927` (`CVSS 9.1 Critique`, mars 2025) permet de contourner intégralement l'authentification et les contrôles de sécurité du Middleware Next.js (`< 15.2.3`) via l'en-tête interne `x-middleware-subrequest`. | [GitHub Security Advisory GHSA-f82v-jwr5-mffw / NVD CVE-2025-29927](https://github.com/vercel/next.js/security/advisories/GHSA-f82v-jwr5-mffw) | 2025-03 | 2026-10-27 | Haute |
| [14] | `CVE-2025-55182` (« React2Shell », `CVSS 10.0 Critique`, décembre 2025) est une exécution de code à distance (RCE) sans authentification dans la désérialisation RSC Flight impactant les serveurs Next.js 15.x et 16.x App Router même lorsqu'aucune Server Action personnalisée n'est définie. | [Next.js Security Advisory — CVE-2025-55182 & CVE-2025-66478 RSC RCE](https://nextjs.org/blog/security-nextjs-server-components-actions) | 2025-12 | 2026-10-27 | Haute |
| [15] | Entre mai 2024 et juillet 2026, le serveur Next.js a nécessité des correctifs de sécurité récurrents (`CVE-2024-34351` SSRF, `CVE-2026-23870` DoS Node.js, `CVE-2026-64645/64649` SSRF, `CVE-2026-64642` bypass proxy), alors qu'un bundle SPA statique Vite servi par `nginx:alpine` élimine 100 % de la surface d'attaque Node.js/RSC/Middleware. | [GitHub Security Advisories — vercel/next.js Advisory Database](https://github.com/vercel/next.js/security/advisories) | 2026-07 | 2026-10-27 | Haute |
| [16] | En production Docker/Kubernetes, une image SPA statique Vite + `nginx:alpine` pèse 20–50 Mo sur disque et consomme 5–15 Mo de RAM au repos (limite pod 30–50 Mo), contre 150–300 Mo sur disque et 60–120 Mo de RAM au repos (limite pod 256–512 Mo) pour Next.js standalone. | [Docker Official Library & Next.js Self-Hosting Deployment Docs](https://nextjs.org/docs/app/building-your-application/deploying) | 2025-06 | 2026-10-27 | Haute |
| [17] | L'auto-hébergement horizontal de Next.js 15/16 sur plusieurs réplicas Kubernetes hors Vercel impose des adaptateurs Redis personnalisés (`cacheHandler` / `cacheHandlers`) et `cacheMaxMemorySize: 0` pour éviter la désynchronisation des caches LRU locaux, tandis qu'un conteneur SPA Vite + Nginx est 100 % sans état. | [Next.js Official Docs — Configuring Custom Cache Handler for Self-Hosting](https://nextjs.org/docs/app/api-reference/config/next-config-js/incrementalCacheHandlerPath) | 2026-05 | 2026-10-27 | Haute |
| [18] | En octobre 2026, `@tanstack/react-router` et `@tanstack/react-start` atteignent 12–16M+ téléchargements hebdomadaires npm avec la sortie en disponibilité générale (GA) de TanStack Start v1.0 le 13 octobre 2026, offrant une réversibilité sans lock-in entre SPA pure et SSR optionnel. | [TanStack Official Blog — TanStack Start v1.0 General Availability](https://tanstack.com/blog) | 2026-10 | 2026-10-27 | Haute |

---

## 9. Carte d'Obsolescence (Staleness Map — générée via `recon_kit.py staleness`)

Fenêtres de fraîcheur appliquées (`today = 2026-10-27`) : `version_compat = 6 mois`, `ecosystem_signal = 6 mois`, `perf_scale = 12 mois`, `architecture_pattern = 24 mois`.
- **Prochaine date de revérification au plus tôt (`earliest_recheck`)** : `2025-09-01` (9 affirmations historiques ou de benchmarks datant de début/mi-2025 ont dépassé leur fenêtre glissante de 6 ou 12 mois au `2026-10-27`, mais leurs conclusions architecturales sont corroborées par les sources de mai à octobre 2026).

| Réf | Classe | Date pub | Fenêtre | Date de revérification | Statut au `2026-10-27` |
|---|---|---|---|---|---|
| `1` | `perf_scale` | `2025-05` | 12 mois | `2026-05-01` | À rafraîchir si nouveaux benchmarks |
| `2` | `perf_scale` | `2025-07` | 12 mois | `2026-07-01` | À rafraîchir si nouveaux benchmarks |
| `3` | `perf_scale` | `2025-09` | 12 mois | `2026-09-01` | À rafraîchir si nouveaux benchmarks |
| `4` | `perf_scale` | `2025-06` | 12 mois | `2026-06-01` | À rafraîchir si nouveaux benchmarks |
| `5` | `architecture_pattern` | `2025-10` | 24 mois | `2027-10-01` | Valide |
| `6` | `architecture_pattern` | `2025-03` | 24 mois | `2027-03-01` | Valide |
| `7` | `architecture_pattern` | `2025-08` | 24 mois | `2027-08-01` | Valide |
| `8` | `perf_scale` | `2025-04` | 12 mois | `2026-04-01` | À rafraîchir si nouveaux benchmarks |
| `9` | `architecture_pattern` | `2025-06` | 24 mois | `2027-06-01` | Valide |
| `10` | `architecture_pattern` | `2025-02` | 24 mois | `2027-02-01` | Valide |
| `11` | `architecture_pattern` | `2025-01` | 24 mois | `2027-01-01` | Valide |
| `12` | `perf_scale` | `2025-02` | 12 mois | `2026-02-01` | À rafraîchir si nouveaux benchmarks |
| `13` | `version_compat` | `2025-03` | 6 mois | `2025-09-01` | Fait historique CVE-2025-29927 |
| `14` | `version_compat` | `2025-12` | 6 mois | `2026-06-01` | Fait historique CVE-2025-55182 |
| `15` | `version_compat` | `2026-07` | 6 mois | `2027-01-01` | Valide |
| `16` | `perf_scale` | `2025-06` | 12 mois | `2026-06-01` | À rafraîchir si nouveaux benchmarks |
| `17` | `architecture_pattern` | `2026-05` | 24 mois | `2028-05-01` | Valide |
| `18` | `ecosystem_signal` | `2026-10` | 6 mois | `2027-04-01` | Valide |
