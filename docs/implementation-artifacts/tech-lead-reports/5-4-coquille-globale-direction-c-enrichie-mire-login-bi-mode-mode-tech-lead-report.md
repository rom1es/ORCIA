# Story 5.4 — Coquille Globale Direction C Enrichie (Mire /login Bi-Mode, Mode Rail Collapsible, Header Santé DBOS/Outbox & Accueil Anti-Empty-State Scopé)

- **Date** : 2026-10-30
- **Story / Clé Sprint** : `5-4-coquille-globale-direction-c-enrichie-mire-login-bi-mode-mode` (`Epic 5`)
- **Auteur / Contexte** : Implémentation de la mire `/login` bi-mode (SSO OIDC PKCE primaire + accordéon secondaire Argon2id/TOTP + erreurs RFC 9457 + guard `beforeLoad`), de la Sidebar repliable en Mode Rail (`240px <-> 72px`, raccourci `[`, badge `orcia-pack-sdlc`), du `TopHeaderBar` (Workspace/Pack + Sprint actif + santé `DBOS/PG18` et `Outbox`), et de l'accueil Anti-Empty-State (`/`) avec `<SprintContextWidget />` et `<ScopedPromptBox />` (`FR-1`, `AD-15`, `AD-19`, `AD-21`, `UX-DR1`, `UX-DR2`).
- **Commits associés** : `working-tree`

---

## 1. Analyse du Besoin & Étude d'Impact Tech Lead (Pré-Implémentation)

### 1.1 Contexte & Problématique
- L'arrivée quotidienne dans ORCIA doit éviter l'effet « page blanche » (Anti-Empty-State) tout en séparant clairement l'authentification SSO d'Entreprise de l'administration locale de secours, et en rendant immédiatement visibles l'état de santé de l'orchestrateur (`DBOS/PG18`, `Outbox`) et le périmètre documentaire RAG interrogé.

### 1.2 Factorisation & Contrôle de Volumétrie
- 5 primitives modulaires `< 250` lignes créées dans `@orcia/ui` (`packages/ui/src/primitives/`) :
  - `BiModeLoginView.tsx` (`233` lignes)
  - `CollapsibleAppRail.tsx` (`120` lignes)
  - `TopHeaderBar.tsx` (`97` lignes)
  - `SprintContextWidget.tsx` (`98` lignes)
  - `ScopedPromptBox.tsx` (`182` lignes)

---

## 2. Plan d'Implémentation

### 2.1 Mire `/login` Bi-Mode & Guard TanStack Router (`apps/web/src/routes/login.tsx` & `routes/index.tsx`)
- Bouton primaire **SSO d'Entreprise (OIDC PKCE)**.
- Accordéon secondaire replié par défaut (*« Connexion locale / Administrateur de secours »*) avec champs email, mot de passe Argon2id et code TOTP 2FA + bannière d'erreur structurée **RFC 9457** (`errorCode`, `detail`, `traceId`).
- Guard `beforeLoad` sur `/` redirigeant vers `/login` lorsque `search.auth === "unauthenticated"`.

### 2.2 Mode Rail Collapsible, TopHeaderBar & Accueil Anti-Empty-State
- `<CollapsibleAppRail />` : bascule `240px <-> 72px` via clic ou touche `[`, badge `orcia-pack-sdlc` en pied et pastilles temps réel.
- `<TopHeaderBar />` : sélecteur Workspace/Pack + Sprint/PI actif + pastilles de santé `DBOS/PG18` et `Outbox (DLQ=0)`.
- `<SprintContextWidget />` : synthèse du Sprint actif et CTA 1-clic *« Auditer les risques du sprint / lot avec l'IA »*.
- `<ScopedPromptBox />` : sélection explicite des sources RAG autorisées (`Permission Broker`) et du Tier cognitif (`TIER_1_FAST`, `TIER_2_STANDARD`, `TIER_3_DEEP`).

---

## 3. Bilan des Modifications & Résultats (Post-Implémentation)

### 3.1 Fichiers Développés & Modifiés
| Fichier | Nature | Description synthétique |
| :--- | :--- | :--- |
| `packages/ui/src/primitives/BiModeLoginView.tsx` | Création | Mire `/login` bi-mode (SSO OIDC + accordéon Argon2id/TOTP + RFC 9457) |
| `packages/ui/src/primitives/CollapsibleAppRail.tsx` | Création | Sidebar repliable `240px <-> 72px` (`[`) + badge `orcia-pack-sdlc` |
| `packages/ui/src/primitives/TopHeaderBar.tsx` | Création | Barre supérieure Workspace/Pack, Sprint actif & santé DBOS/Outbox |
| `packages/ui/src/primitives/SprintContextWidget.tsx` | Création | Widget Sprint actif avec audit IA des risques en 1 clic |
| `packages/ui/src/primitives/ScopedPromptBox.tsx` | Création | Boîte de prompt scopée aux sources RAG autorisées & Tier cognitif |
| `apps/web/src/routes/login.tsx` | Création | Route TanStack Router `/login` |
| `apps/web/src/routes/index.tsx` | Modification | Accueil Anti-Empty-State & guard `beforeLoad` |

### 3.2 Résultats Chiffrés, Métriques & Qualité
- **Tests Vitest `@orcia/ui` & `@orcia/web`** : `31 passed` (`22` dans `@orcia/ui` + `9` dans `@orcia/web`).
