# Spécification Technique — Story 5.4 (`5-4-coquille-globale-direction-c-enrichie-mire-login-bi-mode-mode`)

## 1. Périmètre & Exigences Couvertes
- **User Story** : `5-4-coquille-globale-direction-c-enrichie-mire-login-bi-mode-mode`
- **Exigences fonctionnelles & architecturales** : `FR-1`, `AD-15`, `AD-19`, `AD-21`, `UX-DR1`, `UX-DR2`.
- **Composants livrés** :
  1. **Mire d'Authentification Bi-Mode (`/login`, `packages/ui/src/primitives/BiModeLoginView.tsx` & `apps/web/src/routes/login.tsx`)** :
     - Action primaire : bouton **SSO d'Entreprise (OIDC PKCE)**.
     - Action secondaire repliée par défaut (*« Connexion locale / Administrateur de secours »*) : formulaire email + mot de passe Argon2id + code TOTP 2FA avec affichage structuré des erreurs **RFC 9457 Problem Details** (`trace_id`, `error_code`, message localisé FR/EN).
     - Guard `beforeLoad` TanStack Router redirigeant vers `/login` lorsque l'utilisateur n'est pas authentifié.
  2. **Sidebar Repliable en Mode Rail & Header Santé (`packages/ui/src/primitives/CollapsibleAppRail.tsx` & `TopHeaderBar.tsx`)** :
     - `<CollapsibleAppRail />` : bascule fluide entre mode étendu (`240px`) et **Mode Rail (`72px`)** via bouton ou raccourci `[`, affichage en pied du badge du **Pack Métier actif** (`orcia-pack-sdlc`) et des pastilles temps réel (actions requises, santé Outbox).
     - `<TopHeaderBar />` : sélecteur Workspace/Pack couplé au Sprint/PI actif + pastilles de santé `DBOS/PG18` et `Outbox DLQ`.
  3. **Tableau de Bord d'Accueil Anti-Empty-State (`/`, `packages/ui/src/primitives/SprintContextWidget.tsx` & `ScopedPromptBox.tsx`)** :
     - `<SprintContextWidget />` : synthèse du Sprint/Lot actif avec CTA 1-clic *« Auditer les risques du sprint / lot avec l'IA »*.
     - `<ScopedPromptBox />` : sélection explicite du périmètre de sources RAG autorisées (filtrées par le *Permission Broker*) et du Tier cognitif (`Tier 1 Fast`, `Tier 2 Standard`, `Tier 3 Deep Reasoning`) avant envoi à l'Agent Assistant.
