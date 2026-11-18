# Story 22.6 — Coquille Direction C `8` Entrées, Mobile Companion `< 768px`, Aide Contextuelle Dynamique par Route (`docs/help/`) & Cockpit `<= 3` Blocs

> **Convention de nommage du fichier (Obligatoire — à créer AVANT toute modification de code)** :
> - User Story du sprint : `docs/implementation-artifacts/tech-lead-reports/{story-key}-tech-lead-report.md`

- **Date** : 2026-11-18
- **Story / Clé Sprint** : `22-6-coquille-direction-c-8-entrees-mobile-companion-aide-dynamique-et-cockpit` (`Epic 22` — Vague 2)
- **Capacité(s)** : `CAP-068` (ancrage principal `failed_e2e` sur `22-6`) ; remise en conformité Direction C & Mobile sur `CAP-042`, `CAP-060`, `CAP-061`, `CAP-064`, `CAP-065`, `CAP-067`, `CAP-071`, `CAP-074`, `CAP-075`, `CAP-200`, `CAP-203` — classification : `ux`
- **Auteur / Contexte** : `bmad-architect-worker` (initialisation pré-implémentation Story 21.9) — Résolution des chantiers **`REM-17`**, **`REM-18`**, **`REM-19`**, **`REM-20`** et **`REM-21`** (`synthese-remediation-sally-winston-epic-21.md`, `UX-COCKPIT-DAY0-01`). Couvre `FR-1`, `FR-3`, `FR-23`, `FR-28`, `FR-32`, `FR-33`, `UX-DR1`, `UX-DR2`, `UX-DR13`, `UX-DR16`, `NFR-A11Y-1`, `UJ-8`, `UJ-13`, `UJ-14`, `UJ-17`, `UJ-20`.
- **Commits associés** : `En attente d'implémentation (initialisé sur 575cf4a)`

---

## 1. Analyse du Besoin & Étude d'Impact Tech Lead (Pré-Implémentation)

### 1.1 Contexte & Problématique
- **Mobile Companion `< 768 px` non câblé & débordements masqués par `overflow-x: hidden` (`REM-17`, `REM-18`)** :
  - `MobileCompanionView.tsx` possède **`0` import dans `apps/web/src/`**. En `390×844`, `FourZoneDirectionCShell` continue de rendre la sidebar icônes (`~72 px`) et une `TopHeaderBar` éclatée sur 4 lignes.
  - `tokens.css:944-953` applique `overflow-x: hidden; max-width: 100vw;` sur `html, body`, masquant les débordements flagrants (`<select>` sur `/activity`, bouton `Ouvrir Mon Assistant →` coupé sur `/cockpit`, carte admin coupée sur `/configuration`) devant `05-mobile-companion` et `12-finops` faussement verts (`PASSED`).
  - Sur `/assistant` mobile (`02-assistant` `PASSED` faussement vert), la réponse assistant générée est invisible dans le viewport et la zone de saisie éclate sur `4` étages.
- **Aide Contextuelle droite figée sur `@1.1.0` + faux exemples `Chef1` / `aqwZSX` (`REM-19`)** :
  - `ShellContextualHelpColumn.tsx:55` appelle `pack="core"` ; faute de fiche seedée pour chaque route, `contextual_help.py:675-681` retombe sur `docs/help/fr/spaces-sources.md @1.1.0` (« Connecter et synchroniser... ») sur quasi toutes les routes (`/assistant`, `/processes`, `/finops`, `/profile`, `/ontology`, `/help`), et `_contextualHelpSections.ts:139,185` expose `Chef1` et `aqwZSX`.
- **Dérive Sidebar `11` entrées vs `8` (`DESIGN.md`), double sélecteur & Breadcrumb (`REM-20`)** :
  - `FourZoneSidebarRail.tsx:107-198` et `ShellSidebarFooter.tsx:55-66` affichent `11` entrées (`Coûts & Activité`, `Documentation`, `Glossaire`, `Mon Organisation`, `Journal d'Activité`) au lieu des `8` entrées de `DESIGN.md` (`Cockpit`, `Mon Assistant`, `Mes Processus`, `Mes Agents`, `Mes Espaces`, `FinOps`, `Configuration`, `Aide`).
  - `shellPresets.ts:88,96` laisse `Cockpit` actif sur `/profile` et `/help`. `TopHeaderBar` n'a qu'un dropdown plat sans fil d'Ariane et sans double sélecteur empilé `Équipe / BU` + `Espace`.
- **Cockpit Loi de Hick `> 3` blocs, bug `Accostage` post-admin & `"LOCK TABLE users IN EXCLUSIVE MODE"` (`REM-21`)** :
  - `CockpitFeaturePanel` empile `6` blocs ; `ProgressiveDay0AccostageBanner.tsx:66,176-245` initialise `adminCreated = false` en `useState` (laisse *Étape 1* ouverte après création admin), coche *Étape 2* avec `0` `org_units`, affiche littéralement `"LOCK TABLE users IN EXCLUSIVE MODE"` (`L243`) et `1/5` sans le mot `Accostage`, tout en empilant les cartes violet/ambre longues directement sur le Cockpit.
- **Captures PNG illustrant ces défauts (y compris sur écrans `PASSED`)** :
  - `01-day0-boot` Mobile (`TopHeaderBar` cassée, sidebar gauche, bouton coupé) : [PNG](../e2e-campaign-epic-21/screenshots/01-day0-boot-and-f5-persistence/mobile-companion--le-premier-administrateur-cree-survit-a-un-f5-sans-localstorage-rehydratation-postgresql--passed.png)
  - `02-assistant` Mobile (réponse invisible + 4 étages saisie) : [PNG](../e2e-campaign-epic-21/screenshots/02-assistant-streaming-and-folders/mobile-companion--un-tour-d-assistant-traverse-le-navigateur-l-api-et-la-cassette-llm-0-et-affiche-une-rep--passed.png)
  - `05-mobile-companion` Mobile (`/configuration` ouvert sans bannière Desktop-only) : [PNG](../e2e-campaign-epic-21/screenshots/05-mobile-companion-and-rgaa/mobile-companion--aucun-debordement-horizontal-sur-mobile-une-fois-la-plateforme-initialisee--passed.png)
  - `12-finops` Mobile (`<select>` sortant à droite sur `/activity`) : [PNG](../e2e-campaign-epic-21/screenshots/12-finops-and-audit-provenance/mobile-companion--mobile-finops-et-activity-s-affichent-sans-debordement-horizontal-ni-erreur-serveur--passed.png)
  - `14-auth` #1 (`/organization` `Chef1`/`aqwZSX`) : [PNG](../e2e-campaign-epic-21/screenshots/14-auth-2fa-account-and-profile/desktop-cockpit--mot-de-passe-temporaire-d-un-compte-invite-force-le-renouvellement-et-persiste-dans-user--timedOut.png)
  - `11-screens-smoke` #1 (`/profile` avec `Cockpit` actif) : [PNG](../e2e-campaign-epic-21/screenshots/11-screens-smoke-without-server-errors/desktop-cockpit--chaque-ecran-authentifie-se-charge-au-jour-0-sans-erreur-http-4xx-5xx-ni-banniere-d-erre--passed.png)
  - `shell` #1 Desktop (11 menus + 6 blocs Cockpit) : [PNG](../e2e-campaign-epic-21/screenshots/shell/desktop-cockpit--presente-les-4-zones-masque-parametres-tant-qu-aucun-platform-admin-n-est-connecte-et-l---passed.png)

### 1.2 Exploration, Analyse d'Impact GitNexus, Factorisation & Dette Technique
- **Analyse d'Impact GitNexus (`repo: "/home/romain/Documents/Projects/ORCIA"`)** :
  - `FourZoneDirectionCShell` (`packages/ui/src/primitives/FourZoneDirectionCShell.tsx:137-339`) : **`impactedCount: 281`**, risque **`CRITICAL`** (`direct: 118`, `d=2: 122`, `d=3: 41`, `processes_affected: 33`).
  - `MobileCompanionView` (`packages/ui/src/primitives/MobileCompanionView.tsx`) : **`0` import dans `apps/web/src/`** (composant prêt dans `@orcia/ui` mais jamais branché).
- **Tables PostgreSQL 18 concernées** : `catalog_items` (`HELP_ARTICLE`), `kb_chunks`, `platform_settings`, `users`, `org_units`, `workspaces`, `user_preferences`.
- **Opportunités de Factorisation & Volumétrie** :
  - Extraire `useResponsiveBreakpoint()` dans `@orcia/ui` pour unifier `DESKTOP >= 1280px` / `LAPTOP 768..1279px` / `MOBILE < 768px`.
  - Conserver `FourZoneDirectionCShell.tsx` sous `< 350` lignes en déléguant le rendu Mobile `< 768px` à `MobileCompanionView` + `MobileBottomTabBar`.
  - Gérer le seeder d'articles d'aide `docs/help/{fr,en}/*.md` via `bootstrap/seeder.py` + `ContextualHelpResolutionService` sans dupliquer les résolveurs par route.

---

## 2. Plan d'Implémentation

### 2.1 Schéma de Données & Migrations Alembic (`infra/migrations/versions/`)
- Aucune nouvelle table requise (`catalog_items` avec `idx_catalog_help_routes` de `0023` existe déjà). Mettre à jour les seeds/articles Markdown `docs/help/{fr,en}/*.md` chargés idempotemment en PG18 (`item_type = 'HELP_ARTICLE'`).

### 2.2 Noyau Métier Hexagonal, Orchestration & Workers (`packages/orcia-core/`, `apps/worker/`)
- `packages/orcia-core/src/orcia_core/catalog/contextual_help.py` (`REM-19`) :
  - Supprimer le repli arbitraire sur le premier article du pool (`spaces-sources.md @1.1.0`) lorsque la route ne correspond pas.
  - Résoudre par correspondance exacte de route (`/cockpit`, `/assistant`, `/processes`, `/agents`, `/spaces`, `/workspaces`, `/finops`, `/activity`, `/settings`, `/organization`, `/profile`, `/ontology`, `/gates`, `/help`) ou renvoyer un article dédié `module-overview` contextualisé.
- Enrichir `docs/help/{fr,en}/*.md` pour couvrir **100 % des routes canoniques** au format strict (*À quoi sert cet écran / En N gestes / Un exemple réel / Ce qui coince souvent*), sans jamais contenir `Chef1` ou `aqwZSX`.

### 2.3 Couche Backend API, Sécurité & Contrats (`apps/api/`, `packages/api-client/`)
- `apps/api/src/orcia_api/routers/portal_and_help.py` & `bootstrap_accostage.py` :
  - Exposer la fiche d'aide contextualisée via `GET /api/v1/help/resolve?route=...&lang=...` (avec invalidation Redis `help:route:*`).
  - Retourner l'état réel d'accostage depuis PostgreSQL 18 (`admin_created: users_count > 0`, `org_units_count`, `workspaces_count`, `models_count`) pour alimenter `ProgressiveDay0AccostageBanner`.

### 2.4 Interface Utilisateur & Expérience (`packages/ui/`, `apps/web/`)
- **Mobile Companion `< 768 px` (`REM-17`, `REM-18`)** :
  - Brancher `useResponsiveBreakpoint()` dans `FourZoneDirectionCShell.tsx` : en `< 768 px`, masquer `FourZoneSidebarRail`, condenser `FourZoneTopHeaderSection` sur 1 ligne (`min-w-0`), monter `MobileCompanionView` avec barre basse fixe 3 onglets (`Cockpit`, `Assistant / Arbitrage`, `Décisions`), et afficher la bannière « Fonctionnalité réservée au poste Desktop » sur `/settings`, `/organization` et `/processes/studio/*`.
  - Corriger `tokens.css` (`max-width: 100%` sur `<select>`, boutons, cartes) pour supprimer les débordements masqués par `overflow-x: hidden`.
  - Dans `/assistant` mobile (`AssistantSpeedSelectorAndStreamView.tsx`), garantir le scroll automatique vers la réponse SSE (`min-h-0 flex-1 overflow-y-auto`) et aligner le compositeur mobile sur 2 lignes propres.
- **Aide Dynamique (`REM-19`)** :
  - Dans `ShellContextualHelpColumn.tsx`, passer la `route` courante et `sectionId` au résolveur ; purger `Chef1` et `aqwZSX` de `_contextualHelpSections.ts` ; faire réagir tout clic sur `ⓘ` en focalisant la section cible.
- **Sidebar `8` entrées, Double Sélecteur & Breadcrumb (`REM-20`)** :
  - Aligner `FourZoneSidebarRail.tsx`, `ShellSidebarFooter.tsx` et `shellPresets.ts` sur les **8 entrées `DESIGN.md`** (`Cockpit`, `Mon Assistant`, `Mes Processus`, `Mes Agents`, `Mes Espaces`, `FinOps`, `Configuration`, `Aide`).
  - Loger `Glossaire` dans `Mes Espaces` (et route dédiée accessible via sous-onglet/lien), `Mon Organisation` dans `Configuration` / sous-vue scopée et `Journal d'Activité` en onglet de `FinOps` + lien depuis `🔔 Notifications`.
  - Placer le Double Sélecteur empilé (`Équipe / BU` + `Espace`) en tête de sidebar et le Breadcrumb cliquable dans `FourZoneTopHeaderSection` ; ne plus surligner `Cockpit` sur `/profile` ou `/help`.
- **Cockpit `<= 3` blocs & Accostage réel (`REM-21`)** :
  - Piloter `ProgressiveDay0AccostageBanner.tsx` depuis l'état PG18 (`platformAdmin !== null` $\rightarrow$ Étape 1 validée/repliée ; `orgUnits.length > 0` $\rightarrow$ Étape 2), supprimer `"LOCK TABLE users IN EXCLUSIVE MODE"` (`L243`), afficher explicitement `Accostage X/5`, réduire le Cockpit à `<= 3` blocs et déporter les revues/arbitrages longs dans la Vue Fokus dédiée.

### 2.5 Analyse d'Impact sur la Pyramide des Tests (`AD-17` — Couches 1 à 5 + Sécurité, Obligatoire)
- **Couche 1a / 1b** : tests résolution `docs/help/` sur toutes les routes, tests `useResponsiveBreakpoint` (`< 768px` barre 3 onglets, redirection Desktop-only), tests `ProgressiveDay0AccostageBanner` post-admin, test Sidebar `8` entrées sans surlignage erroné sur `/profile`.
- **Couche 2 (`HTTP ➔ PG18`)** : `GET /api/v1/help/resolve` sur toutes les routes canoniques ; état d'accostage Jour 0 vs post-admin depuis PG18.
- **Couche 3 (`OpenAPI 0-diff`, `lint-imports`)** : conformité SDK et `0` hex en dur hors `tokens.css`.
- **Couche 5 (Playwright E2E)** : vérifications visuelles et géométriques sur `shell.spec.ts`, `01-day0-boot`, `02-assistant` mobile, `05-mobile-companion`, `11-screens-smoke`, `12-finops` mobile, `21-assistant` #2.

---

## 3. Bilan des Modifications & Résultats (Post-Implémentation)

> *[En attente d'implémentation de la Story 22.6]*

### 3.1 Fichiers Développés & Modifiés
| Fichier | Nature (Création / Modification / Refactoring) | Description synthétique |
| :--- | :--- | :--- |
| `docs/help/{fr,en}/*.md` & `contextual_help.py` | Création / Modification | *[À compléter après implémentation]* |
| `packages/ui/src/primitives/FourZoneDirectionCShell.tsx` & `MobileCompanionView.tsx` | Modification | *[À compléter après implémentation]* |
| `packages/ui/src/primitives/ProgressiveDay0AccostageBanner.tsx` & `FourZoneSidebarRail.tsx` | Modification | *[À compléter après implémentation]* |
| `apps/web/src/components/*` & `features/cockpit/*` | Modification | *[À compléter après implémentation]* |

### 3.2 Résultats Chiffrés, Métriques & Qualité
- **Couverture de tests** : *[$\ge 90\%$ requis à mesurer après implémentation]*
- **Qualité statique & Architecture** : `ruff`, `mypy --strict`, `pnpm typecheck`, `lint-imports`, `lint_spine.py`, `gitnexus_detect_changes()` *[À compléter]*

### 3.3 Validation & Procédure de Test sur Toute la Pyramide (`AD-17`)
- *[À compléter après exécution des 5 couches `AD-17` et Playwright Desktop/Mobile]*
