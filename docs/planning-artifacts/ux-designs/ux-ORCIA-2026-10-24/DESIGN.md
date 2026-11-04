---
name: ORCIA
title: ORCIA — Visual Identity & Design System (Direction C : Enterprise Adaptive Hybrid)
status: draft
created: 2026-10-24
updated: 2026-10-30
description: Plateforme d'exécution de processus d'entreprise et personnels "Human-Led, Agent-Accelerated". Basée sur shadcn/ui (Radix + Tailwind CSS) avec l'architecture visuelle Direction C Sobriété (Sidebar Gauche à Double Sélecteur Organigramme + TopHeaderBar Contextualisée avec Fil d'Ariane & Recherche + Espace Central Épuré + Colonne d'Aide Contextuelle Intégrée à Droite).
colors:
  sidebar-bg: '#FFFFFF'
  sidebar-foreground: '#0F172A'
  sidebar-muted: '#64748B'
  sidebar-border: '#E2E8F0'
  sidebar-active-bg: '#EFF6FF'
  sidebar-active-fg: '#2563EB'
  background: '#EAF2FB'
  surface: '#FFFFFF'
  dock-bg: '#FFFFFF'
  foreground: '#0F172A'
  muted-foreground: '#475569'
  border: '#E2E8F0'
  primary: '#2563EB'
  primary-foreground: '#FFFFFF'
  primary-dark: '#6366F1'
  human-led: '#6D28D9'
  human-led-bg: '#F5F3FF'
  arbitration-amber: '#D97706'
  arbitration-bg: '#FFFBEB'
  gate-pass: '#059669'
  gate-pass-bg: '#ECFDF5'
  ontology-cyan: '#0284C7'
  ontology-bg: '#F0F9FF'
  stale-danger: '#DC2626'
  stale-bg: '#FEF2F2'
typography:
  sans:
    fontFamily: 'Inter, Geist Sans, system-ui, sans-serif'
    fontSize: 13.5px
    lineHeight: '1.5'
  display:
    fontFamily: 'Inter, Geist Sans, system-ui, sans-serif'
    fontSize: 22px
    fontWeight: '700'
    lineHeight: '1.25'
  mono:
    fontFamily: 'JetBrains Mono, Geist Mono, monospace'
    fontSize: 12px
rounded:
  sm: 6px
  md: 10px
  lg: 14px
  full: 9999px
spacing:
  sidebar-expanded: 240px
  sidebar-collapsed: 72px
  dock-width: 340px
components:
  sidebar-nav-item-active:
    background: '{colors.sidebar-active-bg}'
    foreground: '{colors.sidebar-active-fg}'
    radius: '{rounded.md}'
  human-led-anchor-card:
    background: '{colors.human-led-bg}'
    border: '1px solid {colors.human-led}'
    borderLeft: '4px solid {colors.human-led}'
    radius: '{rounded.lg}'
  arbitration-tiebreak-card:
    background: '{colors.arbitration-bg}'
    border: '1px solid {colors.arbitration-amber}'
    borderLeft: '4px solid {colors.arbitration-amber}'
    radius: '{rounded.lg}'
  review-briefing-grid:
    background: '{colors.surface}'
    border: '1px solid {colors.border}'
    radius: '{rounded.lg}'
  uri-badge:
    fontFamily: '{typography.mono.fontFamily}'
    radius: '{rounded.sm}'
---

## Brand & Style

**ORCIA** incarne la posture **"Human-Led, Agent-Accelerated"** à travers la **Direction C Sobriété (Architecture 4 Zones inspirée de EXEMPLE & Portals)**. Son identité visuelle repose sur quatre piliers complémentaires qui éliminent toute surcharge cognitive et tout jargon d'infrastructure :
1. **Colonne Gauche — Sidebar d'Organigramme & Menu Global (`240px` dépliée / `72px` repliée)** :
   - **En haut** : Marque **ORCIA** cliquable + **Double Sélecteur d'Organigramme Empilé** :
     - Sélecteur **`Équipe / BU`** (positionnement dans l'organisation)
     - Sélecteur **`Espace`** juste en dessous (périmètre opérationnel courant).
     - **Au centre** : Les **8 Entrées du Menu Principal** (*sans numérotation devant les libellés, et sans bouton « Nouvelle discussion » dans la sidebar, celui-ci résidant dans `Mon Assistant`*) :
     - **`Cockpit`** (Pilotage du périmètre actif, accostage à vide `1/6`, décisions attendues — maximum 3 blocs à l'écran)
     - **`Mon Assistant`** (Espace conversationnel IA avec boutons `+ Nouvelle discussion` et `⚙ Réglages de l'assistant`, 3 onglets `💬 Discussion active | 📁 Dossiers (N) | 🕘 Historique & Recherche`, citations vérifiées `[S1]`/`[G1]`/`[O1]` et sélecteur de vitesse `⚡ Standard / 🧠 Approfondi`)
     - **`Mes Processus`** (Workflows `Publiés | Brouillons | Exécutions & Décisions` en Vue Fokus de Revue + Studio)
     - **`Mes Agents`** (Carte n°1 `🤖 Assistant de l'Espace`, Agents interpellables au `@`, Skills de l'agent, Outils & Casquettes)
     - **`Mes Espaces`** (Structuré en 5 sous-onglets : `Accostage` | `Documents & Sources` | `Livrables & Artefacts` | `Glossaire` | `Membres & Paramètres de l'espace`)
     - **`FinOps`** (Visibilité et barre de portée `Cet Espace` | `Cette Équipe / BU` | `Socle Plateforme` strictement filtrées selon l'habilitation de l'utilisateur)
     - **`Configuration`** (Barre de portée : `Cet Espace` | `Cette Équipe / BU` | `Socle Plateforme` selon l'habilitation de l'utilisateur, avec badges d'héritage `Socle` et `Équipe`)
     - **`Aide`** (Centre d'aide par intention *« Que voulez-vous faire ? »* en $N$ gestes).
2. **Barre Supérieure (`TopHeaderBar` `#FFFFFF`, hauteur `56px`) Ultra-Sobre & Contextualisée** :
   - **À gauche** : **Fil d'Ariane cliquable (`Breadcrumb`)** situant en permanence l'utilisateur dans son organigramme et son écran (*ex. `BU Grand Public › Équipe Mon Compte › Espace Portail › Cockpit`*).
   - **À droite** : **Zone d'input de Recherche Contextuelle (`🔍 Rechercher dans ce périmètre...`)** permettant de retrouver instantanément tous les éléments accessibles à l'utilisateur, suivie des icônes sobres **`🔔 Notifications`** (*Ce qui a avancé*), **`❓ Aide contextuelle`** (ouvre/ferme la colonne d'aide à droite) et **`👤 Mon Profil`** (Compte/MFA, jetons personnels `Passthrough` et clés MCP IDE).
3. **Espace Central Épuré (Sobriété & Divulgation Progressive)** :
   - **Sur l'écran principal (`Cockpit`)** : **Maximum 3 blocs** (au démarrage à vide : la carte unique d'**Accostage guidé `1/6`** avec compteurs `0/0/0` masqués ; en régime actif : 3 compteurs sobres + la carte prioritaire du moment + les accès rapides).
   - **Sur les écrans métiers (`Mes Processus`, `Mes Agents`, `Mes Espaces`, `FinOps`, `Configuration`)** : Gabarit unifié **En-tête avec 1 phrase d'intention en langage courant + 3 à 4 compteurs KPI sobres (masqués tant que `total == 0`) + Filtres pilules + Tableau ou État vide pédagogique en 1 phrase**. Les formulaires de création ne sont jamais empilés en permanence sur l'écran : ils s'ouvrent dans une **Modale dédiée** au clic sur le bouton primaire (`+ Nouvel espace`, `+ Nouveau processus`, `+ Nouvel agent`...).
4. **Colonne Droite — Panneau d'Aide Contextuelle Intégré (`340px`, Ouvert par défaut tant que `total == 0`, Repliable via `❓`)** :
   - Ouverte automatiquement tant qu'un écran est vide afin d'accompagner l'initialisation (et repliée par défaut sur `< 1440px` dès que `total >= 1`), puis ouvrable/repliable à tout moment via le bouton `❓` de la `TopHeaderBar`.
   - Structurée invariablement en **4 sections pédagogiques** :
     - **Ce qui est attendu ici** (objectif de l'écran, temps estimé, rôle concerné)
     - **`EN N GESTES`** (étapes numérotées claires expliquant comment agir)
     - **`UN EXEMPLE RÉEL`** (encadré ambre concret illustrant un cas d'usage réel)
     - **`CE QUI COINCE SOUVENT`** (diagnostics immédiats des erreurs fréquentes).

### Les Règles Fondamentales de l'UI (Interface Utilisateur — 5 Piliers Invariants)

L'UI traduit l'UX en éléments visuels tangibles, esthétiques et fonctionnels. Tous les composants `@orcia/ui` (`packages/ui`) et écrans `apps/web` respectent impérativement ces **5 règles fondamentales** :

1. **Hiérarchie visuelle** : Guider l'œil en jouant sur les tailles, les contrastes, les espacements et les graisses de police (`400`, `500`, `600`, `700`) pour distinguer immédiatement l'important (titre de page, grands compteurs KPIs, action principale, alerte critique) du secondaire (métadonnées, descriptions complémentaires).
2. **Limitation des typographies (Maximum 2)** : Se restreindre strictement à **deux familles typographiques** pour conserver une lecture harmonieuse :
   - **Primaire (`Inter` / `Geist Sans`)** pour toute l'interface, les titres (`display`) et la lecture documentaire ;
   - **Secondaire (`JetBrains Mono` / `Geist Mono`)** réservée aux identifiants techniques, URI fédérées, hashes `SHA-256` et extraits de code.
3. **Cohérence graphique** : Utiliser un système de composants unifié dans `@orcia/ui` (boutons, cartes `#FFFFFF`, badges, menus déroulants et modales au design strictement identique pour une même famille d'action à travers les 8 entrées du menu).
4. **Gestion des grilles (Grids)** : Structurer chaque page et panneau à l'aide de colonnes régulières, de gouttières (`gap` sur échelle de `8px`/`16px`/`24px`) et de marges régulières pour aligner proprement tous les éléments.
5. **Contrastes et accessibilité (WCAG 2.2 AA)** : Garantir que toutes les combinaisons de couleurs de texte et de fond respectent les ratios de contraste normatifs (`>= 4.5:1` texte normal, `>= 3:1` grands titres et composants UI) pour être lisibles par tous, en mode clair comme en mode sombre.

### Microcopy Centrée Utilisateur & Déclencheur d'Aide Contextuelle Ciblée (`ⓘ` `ContextualInfoTriggerButton`)

- **Zéro jargon d'implémentation interne dans l'UI** : Les dictionnaires `i18n` (`fr`/`en`) et composants adoptent exclusivement le point de vue de l'utilisateur final. Toute référence interne (`DBOS`, `PostgreSQL 18`, `pgvector`, `halfvec`, `Outbox`, `Wasmtime`, `Starlark`, `Argon2id`, `OIDC PKCE`, `Passthrough`, `Tie-Break`, `Rubber-stamping`, `What-If`, `Verrou V1..V5`, `AD-*`, `RFC 9457`, constantes techniques brutes) est proscrite des écrans.
- **Intitulés auto-porteurs (< 2 secondes)** : Les titres, onglets, boutons et champs restent courts, explicites et immédiatement actionnables.
- **Zéro pavé explicatif dans l'écran central — Bouton `ⓘ` (`ContextualInfoTriggerButton`)** : Tout complément d'explication est déporté dans la **Colonne d'Aide Contextuelle à droite (`340px`)** et accessible via le composant `@orcia/ui` `<ContextualInfoTriggerButton sectionId="..." />` (pastille circulaire `18px × 18px` avec lettre `"i"`, classe `.orcia-info-trigger-btn`). Au clic, la colonne d'aide droite s'ouvre automatiquement et surligne la section explicative ciblée (`data-testid="help-section-${sectionId}"`, `data-active="true"`).

ORCIA hérite des fondations de **shadcn/ui (Radix UI + Tailwind CSS)**. Ce document spécifie uniquement la couche identitaire et les composants cognitifs propres à ORCIA.

## Colors

Chaque couleur sémantique d'ORCIA possède une signification stricte liée à la gouvernance humano-agentique — aucune couleur d'accent n'est utilisée à titre purement décoratif :

- **Sidebar Crisp White (`#FFFFFF` / Bordure `#E2E8F0` / Capsule Active `#EFF6FF`)** : Fond clair et aéré de la Sidebar d'organigramme et de navigation globale à 8 entrées, isolant visuellement la navigation de la surface de travail.
- **Canvas Background (`#EAF2FB` / `#F8FAFC` Light / `#0B0F17` Dark)** : Fond doux du panneau central mettant en relief les cartes blanches `#FFFFFF`.
- **Primary Cobalt (`#2563EB` Light / `#6366F1` Dark)** : Action principale, entrée active dans la Sidebar, sélecteur de portée actif et indicateur de présence de **`Mon Assistant`**.
- **Human-Led Violet (`#6D28D9` / Fond `#F5F3FF`)** : Réservé exclusivement aux **Ancrages Humains Obligatoires** (`human_authored_required: true`). Dès que l'utilisateur voit une bordure violette, il sait que l'IA a l'interdiction de rédiger cette zone à sa place et que sa réflexion d'expert (*Think*) est attendue.
- **Arbitration & Challenge Amber (`#D97706` / Fond `#FFFBEB`)** : Indique une suspension du **Workflow Run** requérant une décision humaine (**Arbitrage Humain**, suspicion de *Rubber-Stamping*, encadré *« Un exemple réel »* de l'aide contextuelle ou source expirée `[STALE_WARNING]`).
- **Gate Pass Emerald (`#059669` / Fond `#ECFDF5`)** : Indique une **Gate** (Déterministe, Agentique Cross-Model ou Humaine) franchie avec succès, une source **`RÉFÉRENCE`** vérifiée, un verrou de présence pris en charge (*Claimed*), ou un cache `SHA-256` valide.
- **Ontology Cyan (`#0284C7` / Fond `#F0F9FF`)** : Identifie les concepts et règles métiers du **Glossaire / Ontologie Dynamique Multi-Niveaux** (`[G1]`, badges d'origine `Socle`, `Équipe`, `Espace`, et badge `AutonomousExecutionBadge`).
- **Stale / Blocker Crimson (`#DC2626` / Fond `#FEF2F2`)** : Contradiction critique d'ontologie (`ONTOLOGY_CONFLICT`), coupe-circuit ouvert (`CIRCUIT_OPEN`), échec de **Gate Déterministe** ou blocage d'habilitation.

## Typography

Conformément à la règle fondamentale de **limitation à maximum deux typographies** :
- **Typographie Primaire — Interface, Titres & Lecture (`Inter` / `Geist Sans`)** :
  - Corps & Conversation (`13.5px`–`14px`, `line-height: 1.5`) : densité calibrée pour afficher côte à côte la Sidebar, l'Espace Central et la Colonne d'Aide Contextuelle `❓` sans troncature.
  - Titres d'Écrans & Compteurs KPI (`display`, `22px`–`28px`, `font-weight: 700`, `line-height: 1.25`, `letter-spacing: -0.02em`) : hiérarchie visuelle assurée par l'échelle typographique, la graisse et l'espacement (sans troisième police serif).
- **Typographie Secondaire — Provenance, URI & Code (`JetBrains Mono` / `Geist Mono`, `12px`)** : Obligatoire pour toutes les URI des Sources et du Coffre (`git://`, `confluence://`, `jira://`, `db://`, `orcia://`), les pastilles de citation (`[S1]`, `[G1]`, `[O1]`), les empreintes `SHA-256`, les pastilles de raccourcis clavier (`⌘W`, `⌘K`, `[`, `]`) et les codes d'erreur RFC 9457.

## Layout & Spacing

L'architecture spatiale Desktop repose sur la **Coquille 4 Zones (Direction C Sobriété — EXEMPLE + Portals)** :
1. **Zone 1 — Colonne Gauche (`240px` dépliée / `72px` repliée en icônes via `[`, `#FFFFFF`)** : Contient en haut la marque cliquable **ORCIA**, le **Double Sélecteur d'Organigramme Empilé** (`Équipe / BU` puis `Espace`), et les **8 entrées non numérotées du menu** (`Cockpit`, `Mon Assistant`, `Mes Processus`, `Mes Agents`, `Mes Espaces`, `FinOps`, `Configuration`, `Aide`).
2. **Zone 2 — Barre Supérieure (`TopHeaderBar`, `#FFFFFF`, hauteur `56px`)** : **Fil d'Ariane cliquable (`Breadcrumb`)** à gauche ; **Barre de Recherche Fédérée & Contextuelle (`🔍 Rechercher dans <Écran> ou partout (⌘K)...`, panneau flottant `680px × max 480px` à 3 portées et 7 familles d'éléments)**, **`🔔 Notifications`**, **`❓ Aide contextuelle`** et **`👤 Mon Profil`** à droite.
3. **Zone 3 — Espace Central Épuré (`1fr`, min `680px`, padding `24px`)** : Maximum 3 blocs sur le `Cockpit` ; gabarit unifié sur les écrans métiers (En-tête avec 1 phrase d'intention + 3–4 compteurs KPI masqués si `total == 0` + Filtres pilules + Liste ou État vide en 1 phrase + Création par Modale).
4. **Zone 4 — Colonne Droite d'Aide Contextuelle Intégrée (`340px`, `#FFFFFF`, repliable via `❓` ou `]`)** : Ouverte automatiquement tant que `total == 0` (et repliée par défaut sur `< 1440px` dès que `total >= 1`), structurée en 4 blocs (*Ce qui est attendu ici*, *En N gestes*, *Un exemple réel*, *Ce qui coince souvent*).

Sur **Mobile Companion (`< 768px`)**, la grille cède la place à une vue mono-colonne pilotée par une barre d'onglets inférieure à 3 entrées (`🧭 Cockpit`, `💬 Mon Assistant / Arbitrage`, `☍ Décisions`).

## Elevation & Depth

- Pas d'ombres portées lourdes sur la structure : la séparation entre la Sidebar (`#FFFFFF`), la `TopHeaderBar` (`#FFFFFF`), l'Espace Central (`#F8FAFC`/`#EAF2FB`) et la Colonne d'Aide Contextuelle (`#FFFFFF`) repose sur le contraste de surface et des bordures fines de `1px solid #E2E8F0` (`#1E293B` en mode sombre).
- Les cartes interactives (**Briefing de Revue**, cartes de **Sources**, de **Livrables** et de **Validation par Découpage**) utilisent une élévation subtile `0 1px 3px rgba(15, 23, 42, 0.04)`.

## Shapes

- Rayons nets et professionnels : `rounded-sm` (`6px`) pour les pastilles de citation (`[S1]`, `[G1]`, `[O1]`), les badges d'origine (`Socle`, `Équipe`, `Pack`) et les badges d'URI ; `rounded-md` (`10px`) et `rounded-lg` (`14px`) pour les cartes d'**Ancrage Humain Obligatoire**, d'**Arbitrage Humain** et de **Découpage** ; `rounded-full` réservé aux pilules de filtre et aux verrous de présence temps réel.

## Components

Au-delà des primitives héritées de `shadcn/ui` (`Button`, `Card`, `Badge`, `Tabs`, `Sheet`, `Command`, `Dialog`, `Toast`, `Tooltip`), ORCIA définit **19 composants identitaires** dans `@orcia/ui` :

1. **Stacked Org & Workspace Selector + Sidebar Navigation (`sidebar-nav-item`)** : Double sélecteur empilé (`Équipe / BU` + `Espace`) et 8 entrées de menu non numérotées avec mode Rail (`72px`, raccourci `[`).
2. **Human-Led Anchor Card (`human-led-anchor-card`)** : Conteneur à bordure gauche violette (`4px solid #6D28D9`) avec en-tête explicite `✍️ ANCRAGE HUMAIN OBLIGATOIRE (human_authored_required: true)` et mention de l'auteur humain. Aucun bouton "Générer avec l'IA" n'est autorisé dans ce composant.
3. **Cognitive Review Briefing (`review-briefing-grid`)** : Grille $2 \times 2$ en tête de tout **Artefact** volumineux dans la Vue Fokus de Revue (`Mes Processus › Exécutions & Décisions`) présentant : *1. Résumé Exécutif*, *2. Éléments Clés & Contrôle Transverse*, *3. Décisions Prises*, et *4. Hypothèses Retenues*.
4. **Chunked Validation Card (`chunk-validation-card`)** : Carte représentant une section du **Gabarit d'Artefact** (ou une **Action Externe Staged** avec son chemin cible et son `diff`) avec 3 actions directes : *Valider la section*, *Co-éditer*, ou *Challenger / Rewind amont*.
5. **Arbitration Tie-Break Matrix (`arbitration-tiebreak-card`)** : Carte ambre affichée sur la Carte Prioritaire du `Cockpit` et dans `Mes Processus › Exécutions & Décisions` lorsque l'exécution rencontre des options équivalentes.
6. **Federated URI & Access Mode Badge (`uri-badge`)** : Composant monospace affichant l'URI ou l'alias (`orcia://workspaces/<ws>/artifacts/<type>/<slug>@v<N>`), le rôle (`RÉFÉRENCE` vs `ACTIF`), le mode d'accès (`Lecture seule` vs `Lecture & Écriture`) et l'empreinte `SHA-256` tronquée.
7. **Presence & Claim Pill (`presence-claim-pill`)** : Indicateur temps réel (`AD-4`) affichant soit `Prendre en charge & Ouvrir la revue →`, soit l'état verrouillé `🔒 En cours : [Prénom]`.
8. **Autonomous Execution Badge & Kill-Switch Bar (`autonomous-execution-badge`, `UX-DR17`)** : Badge distinctif en **Cyan/Cobalt (`#0284C7` / fond `#F0F9FF`)** — *sans jamais utiliser le Violet `#6D28D9`* — accompagné des sorties de secours `🛑 Kill-Switch` et `⏪ Invalider & Rollback`.
9. **Declarative Permission Guard (`permission-guard`, `AD-21`)** : Enveloppe déclarative `@orcia/ui` (`verb: "create" | "read" | "update" | "delete" | "execute" | "grant"`, `fallbackMode: "passive-lock" | "disabled" | "hidden"`). Affiche `🔒 Non habilité` et le bouton *Demander l'accès* sans exposer la configuration secrète.
10. **Write-Only Secret Field (`secret-field`, `AD-21`)** : Champ de saisie de secret adossé à `SecretInput` (`keep | set | clear`) et `SecretStatus` (`configured`, `fingerprint: "sha256:8-hex"`), sans jamais pré-remplir de masque `••••••••`.
11. **Contextual Help Panel (`contextual-help-panel`)** : Colonne latérale droite (`340px`, ouverte automatiquement tant que `total == 0`, repliable via `❓`) structurée en 4 sections : *Ce qui est attendu ici*, *`EN N GESTES`*, *`UN EXEMPLE RÉEL`*, *`CE QUI COINCE SOUVENT`*.
12. **Scope Selector Bar & Inheritance Badge (`scope-selector-bar`)** : Barre de portée explicite en en-tête de `Configuration` et `FinOps` (`📦 Cet Espace` | `👥 Cette Équipe / BU` | `🌐 Socle Plateforme`) accompagnée des badges d'héritage `Socle` et `Équipe` (`lecture seule` / `🔒 Gelé`).
13. **Inline Deterministic Citation Pill & Source Preview Popover (`inline-citation-pill`, `Principe K.5`)** : Pastille interactive temps réel (`[S1 · Fichier:L120 · RÉFÉRENCE]`, `[G1 · Glossaire]`, `[O1 · Outil]`, ou `[S1 · 🔒 Source restreinte — Demander l'accès]` si le lecteur n'a pas `READ_SOURCE`) ouvrant au survol/clic l'extrait exact surligné et son statut de fraîcheur.
14. **Thematic Assistant Folder & Collaborative Share Modal (`assistant-folder-card`, `Principe K.6`)** : Carte de `📁 Dossier` dans `Mon Assistant` regroupant discussions, notes épinglées et brouillons avec sélecteur de visibilité (`🔒 Privé`, `👥 Collègues choisis` en lecture ou co-contribution sous `Passthrough` `AD-6`, `📦 Tout l'Espace`) et bouton `☍ Lancer un Processus à partir de ce dossier`.
15. **Glossary Candidate Card & What-If Impact Banner (`glossary-candidate-card`, `Principe L`)** : Carte de proposition dans `Mes Espaces › Glossaire › ✨ À valider (N)` affichant l'extrait source d'origine, le compteur d'occurrences, l'encadré de prévisualisation `ImpactSimulatorService` (`AD-7`) et les actions `✓ Accepter`, `✏️ Ajuster`, `✕ Écarter` et `↑ Proposer à l'équipe / BU`.
16. **Workflow Studio Top Governance Bar & Layers Inspector (`workflow-top-governance-bar`, `layers-inspector-popover`, `AD-21`)** : Barre d'outils supérieure du Studio (`Pré-prompt`, `Contrat`, `⚡ Déclencheurs`, `▷ Tester`, `Publier`) et inspecteur **`COUCHES · N`** (y compris sur les 5 nœuds de `Mon Assistant` entre les bornes `🔒 AssistantHarness` `AD-15`).
17. **Federated Contextual Search Popover (`top-header-search-command`, `Principe A.2`)** : Palette de recherche fédérée et d'accès rapide à 2 vitesses (`⌘K` / `Ctrl+K`, `680px × max 480px`) ancrée dans la `TopHeaderBar`, avec 3 pilules de portée (`📍 Cet écran` | `📦 Cet Espace` | `🌐 Tous mes Espaces`), recherche lexicale `< 30 ms` (`0 $`) verrouillée en tête et enrichissement sémantique `pgvector` à `450 ms` inséré en dessous sans saut visuel (*Zero Layout Shift*), pilules sur les 7 familles d'éléments et action de secours `💬 Poser la question à Mon Assistant →`.
18. **User Account Dropdown & Personal Settings Modal (`user-account-dropdown`, `user-settings-modal`, `Principe A.3`)** : Menu déroulant rapide (`280px`) au clic sur le login de la `TopHeaderBar` (identité, bascules 1-clic `🌓 Clair/Sombre` et `🌐 FR/EN` persistées en `0 ms` dans `localStorage` + sync API, bouton `🚪 Se déconnecter`) et modale dédiée **`⚙️ Paramètres de mon compte` (`720px`, 4 onglets sans doublon avec `Mon Assistant` : `🎨 Préférences & Affichage` avec lien croisé vers `⚙ Réglages de l'assistant`, `👤 Profil & Sécurité`, `🔗 Accès aux sources Passthrough`, `💻 Clés IDE & MCP`)** qui s'ouvre en fermant automatiquement le menu déroulant.
19. **Remote Service / Agent Test & Discovery Bench (`remote-service-test-bench`, `Principe M`)** : Banc de diagnostic isolé (`timeout 5 s`, `1 Mo` max, tracé `ADMIN_CONNECTION_TEST`) en 4 étapes intégré aux modales de déclaration des Serveurs MCP, Connecteurs et Agents distants (`1. Réseau/TLS/Anti-SSRF`, `2. Auth <SecretField /> ou état 🟠 En attente de jeton utilisateur Passthrough non bloquant`, `3. Découverte tools/list ou Agent Card avec écriture forcée en Action Staged`, `4. 💬 Essai rapide à chaud Dry-Run avec détection de la télémétrie FinOps _meta.usage`).

## Do's and Don'ts

| Do                                                                                                                                                                                                                                       | Don't                                                                                                                                                                                              |
| :--------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | :------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Conserver les **8 entrées non numérotées** visibles dans la Sidebar gauche (`Cockpit`, `Mon Assistant`, `Mes Processus`, `Mes Agents`, `Mes Espaces`, `FinOps`, `Configuration`, `Aide`) et utiliser exclusivement le terme **`Espace`** | Numéroter les entrées du menu, utiliser le terme « Produit » dans la navigation ou cacher le menu derrière des commandes chat                                                                      |
| Masquer automatiquement les compteurs KPI `0 / 0 / 0` et les pilules de filtre tant qu'un écran est vide (`total == 0`) et ouvrir par défaut la Colonne d'Aide `❓` à droite                                                              | Afficher une rangée de compteurs `0 / 0 / 0 / 0` sur un espace neuf ou empiler un formulaire de création en plein écran au lieu d'une **Modale**                                                   |
| Utiliser le violet `{colors.human-led}` (`#6D28D9`) exclusivement pour les **Ancrages Humains Obligatoires** (`human_authored_required: true`)                                                                                           | Pré-remplir par IA un champ marqué `human_authored_required: true` ou utiliser le violet sur un badge d'exécution autonome                                                                         |
| Ouvrir les revues de livrables (Briefing 4 blocs, découpage, Actions Staged) dans la **Vue Fokus de Revue (`Mes Processus › Exécutions & Décisions › Run #ID`)** sous verrou Redis (`AD-4`)                                              | Empiler un document de 30 pages directement à l'intérieur des 3 blocs du `Cockpit`                                                                                                                 |
| Résoudre chaque citation `[S1]`/`[G1]`/`[O1]` via la `citation_map` SSE et masquer l'extrait (`🔒 Source restreinte`) si le lecteur d'un `📁 Dossier` partagé n'a pas le droit `READ_SOURCE`                                               | Demander au LLM de recopier des URL brutes ou exposer un `snippet` d'une source restreinte à un co-lecteur non habilité                                                                            |
| Utiliser exclusivement `<SecretField />` (`SecretInput: keep \| set \| clear` + `SecretStatus` fingerprint) pour tout secret ou jeton `Passthrough`                                                                                      | Renvoyer un secret masqué `••••••••` dans un `input` contrôlé qui risquerait d'écraser le secret réel en base                                                                                      |
| Sélectionner un **Palier de modèle abstrait (`Rapide`, `Équilibré`, `Approfondi`)** dans le Studio et un mode de vitesse (`⚡ Standard` / `🧠 Approfondi`) dans `Mon Assistant`                                                            | Coder en dur des noms commerciaux de modèles LLM (`gpt-4o`, `claude-3-7-sonnet`) dans les nœuds d'un processus                                                                                     |
| Dans **`📊 FinOps`** (`AD-12`), distinguer le **Coût interne vérifié** du **Coût externe déclaré MCP** (borné par `RemoteUsageSanitizer`) et séparer les compteurs de **Tokens LLM** et d'**Appels / Unités MCP**                         | Additionner artificiellement des unités métiers externes (`pages OCR`, `crédits API`) avec des `tokens LLM` ou laisser un `_meta.usage` externe non borné bloquer les modèles internes de l'Espace |
