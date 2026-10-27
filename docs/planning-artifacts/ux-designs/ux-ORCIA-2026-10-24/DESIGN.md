---
name: ORCIA
title: ORCIA — Visual Identity & Design System (Direction C : Enterprise Adaptive Hybrid)
status: final
created: 2026-10-24
updated: 2026-10-24
description: Plateforme d'exécution de processus d'entreprise et personnels "Human-Led, Agent-Accelerated". Basée sur shadcn/ui (Radix + Tailwind CSS) avec l'architecture visuelle Direction C (Menu Latéral Sombre Explicite + Espace Central Haut-Contraste + Dock Agent Assistant Persistant).
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
  dock-width: 360px
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

**ORCIA** incarne la posture **"Human-Led, Agent-Accelerated"** à travers la **Direction C Épurée (Clarté SaaS & Grille Bento)**. Inspirée des références [`imports/reference-layout-insidebox.png`](file:///home/romain/Documents/Projects/ORCIA/docs/planning-artifacts/ux-designs/ux-ORCIA-2026-10-24/imports/reference-layout-insidebox.png) et [`imports/reference-dropdown-menus.png`](file:///home/romain/Documents/Projects/ORCIA/docs/planning-artifacts/ux-designs/ux-ORCIA-2026-10-24/imports/reference-dropdown-menus.png), son identité visuelle combine quatre piliers :
1. **Panneau Latéral Gauche Clair & Respirant (`#FFFFFF`)** : Logo géométrique bleu + marque **ORCIA** cliquable en haut à gauche (retour à l'accueil), barre de recherche rapide intégrée (`🔍 Rechercher...`), et les **7 Modules Globaux** présentés avec une capsule active bleu tendre (`#EFF6FF` / texte `#2563EB`) et des pastilles rondes ambre (`#D97706`) pour les actions en attente.
2. **Barre Supérieure (Top Header Bar `#FFFFFF`) avec Icônes & Menu Déroulant Profil Riche** :
   - À gauche : navigation rapide par filtres de vue séparés par `|` (`Vue d'ensemble | Ancrage & Cockpit | Catalogue Fédéré | Workspaces & Équipes | Initialisation & Gates`).
   - À droite : icônes d'action directe (`💬` Agent Assistant, `🗂️` Périmètre `⌘W`, `🔔` Notifications, `🌐` Langue `FR/EN`) et **Avatar Utilisateur avec pastille de présence en ligne (`🟢`)** ouvrant un **Menu Déroulant Riche (`UserProfileDropdown`)** comportant le rôle/unité, les liens de gouvernance avec chevrons `›` et badges de raccourcis clavier (`⌘W`, `]`), le sélecteur rapide de Persona, le switch `🌙 Mode Sombre`, et une **jauge de consommation FinOps** avec barre de progression.
3. **Large Panneau Central avec Bandeau Hero & Grille Bento (`#EAF2FB` / Cartes `#FFFFFF`)** :
   - Un bandeau d'accueil personnalisé (*« Bonjour, {Prénom} ! »*) accompagné de **grands compteurs KPIs illustrés** (`Workflows Système`, `Workspaces Actifs`, `Budget FinOps`).
   - Une **Grille Bento 2 colonnes** sur fond doux bleuté (`#EAF2FB`) où chaque carte blanche (`#FFFFFF`, rayon `14px`, ombre légère) isole clairement un domaine métier.
4. **Co-présence Intelligente à la Demande (Tiroir Agent Assistant `#FFFFFF`)** : Accessible à droite (`360px`) via l'icône `💬` de la Top Bar ou le raccourci `]`, et s'ouvrant automatiquement en cas d'interception `403` par le **Permission Broker**.

### Les Règles Fondamentales de l'UI (Interface Utilisateur — 5 Piliers Invariants)

L'UI traduit l'UX en éléments visuels tangibles, esthétiques et fonctionnels. Tous les composants `@orcia/ui` (`packages/ui`) et écrans `apps/web` respectent impérativement ces **5 règles fondamentales** :

1. **Hiérarchie visuelle** : Guider l'œil en jouant sur les tailles, les contrastes, les espacements et les graisses de police (`400`, `500`, `600`, `700`) pour distinguer immédiatement l'important (titre de page, grands compteurs KPIs, action principale, alerte critique) du secondaire (métadonnées, descriptions complémentaires).
2. **Limitation des typographies (Maximum 2)** : Se restreindre strictement à **deux familles typographiques** pour conserver une lecture harmonieuse :
   - **Primaire (`Inter` / `Geist Sans`)** pour toute l'interface, les titres (`display`) et la lecture documentaire ;
   - **Secondaire (`JetBrains Mono` / `Geist Mono`)** réservée aux identifiants techniques, URI fédérées, hashes `SHA-256` et extraits de code.
3. **Cohérence graphique** : Utiliser un système de composants unifié dans `@orcia/ui` (boutons, cartes Bento `#FFFFFF`, badges, menus déroulants et modales au design strictement identique pour une même famille d'action à travers les 7 modules).
4. **Gestion des grilles (Grids)** : Structurer chaque page et panneau à l'aide de colonnes (`Bento Grid 2x2` responsive), de gouttières (`gap` sur échelle de `8px`/`16px`/`24px`) et de marges régulières pour aligner proprement tous les éléments.
5. **Contrastes et accessibilité (WCAG 2.2 AA)** : Garantir que toutes les combinaisons de couleurs de texte et de fond respectent les ratios de contraste normatifs (`>= 4.5:1` texte normal, `>= 3:1` grands titres et composants UI) pour être lisibles par tous, en mode clair comme en mode sombre.

ORCIA hérite des fondations de **shadcn/ui (Radix UI + Tailwind CSS)**. Ce document spécifie uniquement la couche identitaire et les composants cognitifs propres à ORCIA.

## Colors

Chaque couleur sémantique d'ORCIA possède une signification stricte liée à la gouvernance humano-agentique — aucune couleur d'accent n'est utilisée à titre purement décoratif :

- **Sidebar Crisp White (`#FFFFFF` / Bordure `#E2E8F0` / Capsule Active `#EFF6FF`)** : Fond clair et aéré du menu de navigation global à 7 modules, isolant visuellement la navigation de la surface de travail.
- **Bento Canvas Soft Sky (`#EAF2FB` Light / `#0B0F17` Dark)** : Fond doux du panneau central mettant en relief les cartes blanches `#FFFFFF`.
- **Primary Cobalt (`#2563EB` Light / `#6366F1` Dark)** : Action principale, module actif dans la Sidebar, bordure de focus du menu déroulant profil et indicateur de présence de l'**Agent Assistant**.
- **Human-Led Violet (`#6D28D9` / Fond `#F5F3FF`)** : Réservé exclusivement aux **Ancrages Humains Obligatoires** (`human_authored_required: true`). Dès que l'utilisateur voit une bordure violette, il sait que l'IA a l'interdiction de rédiger cette zone à sa place et que sa réflexion d'expert (*Think*) est attendue.
- **Arbitration & Challenge Amber (`#D97706` / Fond `#FFFBEB`)** : Indique une suspension du **Workflow Run** requérant une décision humaine : **Arbitrage Humain** sur options équivalentes, pastille de notification dans la Sidebar, ou suspicion de *Rubber-Stamping*.
- **Gate Pass Emerald (`#059669` / Fond `#ECFDF5`)** : Indique une **Gate** (Déterministe, Agentique Cross-Model ou Humaine) franchie avec succès, la pastille de présence en ligne sur l'avatar (`🟢`), un verrou de présence pris en charge (*Claimed*), ou un cache `SHA-256` vérifié.
- **Ontology Cyan (`#0284C7` / Fond `#F0F9FF`)** : Identifie les concepts de l'**Ontologie Dynamique Multi-Niveaux** (badges de niveau 1 à 4, promotions sémantiques, traductions par **Profil Humain**).
- **Stale / Blocker Crimson (`#DC2626` / Fond `#FEF2F2`)** : Alerte d'obsolescence documentaire (`[STALE_WARNING]` sur une **Base de Connaissances**), échec de **Gate Déterministe** ou blocage d'habilitation intercepté par le **Permission Broker**.

## Typography

Conformément à la règle fondamentale de **limitation à maximum deux typographies** :
- **Typographie Primaire — Interface, Titres & Lecture (`Inter` / `Geist Sans`)** :
  - Corps & Conversation (`13.5px`–`14px`, `line-height: 1.5`) : densité calibrée pour afficher côte à côte le menu, le **Canvas** et le **Dock Agent Assistant** sans troncature.
  - Titres de Modules, Salutation Hero & Compteurs KPI (`display`, `22px`–`28px`, `font-weight: 700`, `line-height: 1.25`, `letter-spacing: -0.02em`) : hiérarchie visuelle assurée par l'échelle typographique, la graisse et l'espacement (sans troisième police serif).
- **Typographie Secondaire — Provenance, URI & Code (`JetBrains Mono` / `Geist Mono`, `12px`)** : Obligatoire pour toutes les URI du **Catalogue Fédéré** (`db://`, `git://`, `nexus://`), les empreintes `SHA-256`, les pastilles de raccourcis clavier (`⌘W`, `⌘K`, `[`, `]`), les codes d'erreur RFC 9457 et les logs de **Sandbox**.

## Layout & Spacing

L'architecture spatiale Desktop repose sur une structure épurée inspirée d'*InsideBox* :
1. **Colonne Gauche — Sidebar du Menu Global (`240px` dépliée / `72px` repliée en icônes, `#FFFFFF`)** : Contient en haut le logo cliquable **ORCIA**, la barre de recherche rapide (`🔍 Search`), les 7 entrées du menu d'ORCIA avec capsules actives `#EFF6FF` et pastilles ambre, ainsi qu'un pied de barre compact.
2. **Zone Centrale Pleine Largeur (`1fr`, min `640px`)** composée de :
   - **Barre Supérieure (`Top Header Bar`, `#FFFFFF`, `64px`)** : Liens contextuels séparés par `|` à gauche ; barre d'icônes (`💬`, `🗂️`, `🔔`, `🌐`) et **Avatar Utilisateur + Menu Déroulant Riche (`UserProfileDropdown`)** à droite.
   - **Bandeau d'Accueil (`Hero Welcome Strip`, `#FFFFFF`)** : Message d'accueil personnalisé (*« Bonjour, Marc ! »*) à gauche et **grands compteurs KPIs** avec icônes à droite.
   - **Grille Bento Principale (`#EAF2FB`, padding `24px`, grille 2 colonnes `gap: 20px`)** : Cartes blanches `#FFFFFF` (`border-radius: 14px`) filtrables par onglet ou affichées en vue d'ensemble 2×2.
3. **Colonne Droite — Tiroir Agent Assistant & Permission Broker (`360px`, repliable via `💬` ou `]`)** : Permet de dialoguer avec l'Agent Assistant ou de traiter un ticket `PermissionBrokerCard` (ouverture automatique sur `PERMISSION_DENIED_STEP`).

Sur **Mobile Companion (`< 768px`)**, la grille à 3 colonnes cède la place à une vue mono-colonne pilotée par une barre d'onglets inférieure à 3 entrées (`🔔 Inbox`, `💬 Arbitrage/Chat`, `📄 Briefing`).

## Elevation & Depth

- Pas d'ombres portées lourdes sur la structure : la séparation entre la Sidebar (`#0F172A`), l'Espace Central (`#F8FAFC`) et le Dock IA (`#FFFFFF`) repose sur le contraste de surface et des bordures fines de `1px solid #E2E8F0` (`#1E293B` en mode sombre).
- Les cartes interactives (**Briefing de Revue**, cartes du **Catalogue Fédéré**, sections de **Validation par Découpage**) utilisent une élévation subtile `0 1px 3px rgba(15, 23, 42, 0.04)`.

## Shapes

- Rayons nets et professionnels : `rounded-sm` (`5px`) pour les badges d'URI (`git://`, `nexus://`, `db://`) et les boutons d'action rapide ; `rounded-md` (`8px`) pour les cartes d'**Ancrage Humain Obligatoire**, d'**Arbitrage Humain** et de **Découpage** ; `rounded-full` réservé aux pastilles de compteur de notifications et aux verrous de présence temps réel.

## Components

Au-delà des primitives héritées de `shadcn/ui` (`Button`, `Card`, `Badge`, `Tabs`, `Sheet`, `Command`, `Dialog`, `Toast`, `Tooltip`), ORCIA définit **7 composants identitaires** :

1. **Global Sidebar Navigation (`sidebar-nav-item`)** : Affiche les 7 modules avec icône, libellé explicite et pastilles d'état temps réel (compteur ambre pour les actions requises en *Contributeur*, pastille rouge `!` pour une alerte `[STALE_WARNING]` sur l'**Ontologie**/KB).
2. **Human-Led Anchor Card (`human-led-anchor-card`)** : Conteneur à bordure gauche violette (`4px solid #6D28D9`) avec en-tête explicite `✍️ ANCRAGE HUMAIN OBLIGATOIRE (human_authored_required: true)` et mention de l'auteur humain. Aucun bouton "Générer avec l'IA" n'est autorisé dans ce composant.
3. **Cognitive Review Briefing (`review-briefing-grid`)** : Grille $2 \times 2$ en tête de tout **Artefact** volumineux présentant immuablement : *1. Résumé Exécutif*, *2. Éléments Clés & Contrôle Transverse*, *3. Décisions Prises*, et *4. Hypothèses Retenues (Assumptions)* (avec bordure ambre sur le bloc 4 tant que les hypothèses n'ont pas été inspectées).
4. **Chunked Validation Card (`chunk-validation-card`)** : Carte représentant une section du **Gabarit d'Artefact** avec 3 actions directes : *Valider la section*, *Co-éditer*, ou *Challenger / Rewind amont*.
5. **Arbitration Tie-Break Matrix (`arbitration-tiebreak-card`)** : Carte ambre affichée dans le Chat et le Canvas lorsque l'**Agent Exécuteur** suspend son exécution face à des options équivalentes, présentant côte à côte chaque option, ses impacts SI/Métier et le bouton de décision.
6. **Federated URI & RBAC Badge (`uri-badge`)** : Composant monospace distinguant visuellement la source de vérité d'une ressource : ambre pour `git://`, bleu cobalt pour `nexus://`, vert émeraude pour `db://`, accompagné des droits effectifs (`DISCOVER`, `EXECUTE`, ` 🔒 Source masquée`) et du hash `SHA-256` tronqué.
7. **Presence & Claim Pill (`presence-claim-pill`)** : Indicateur temps réel sur les notifications d'équipe affichant soit le bouton d'action `Prendre (Claim)`, soit l'état verrouillé `🔒 En cours : [Prénom]`.
8. **Autonomous Execution Badge & Kill-Switch Bar (`autonomous-execution-badge`, `UX-DR17`)** : Badge distinctif en **Cyan/Cobalt (`#0284C7` / fond `#F0F9FF`)** — *sans jamais utiliser le Violet `#6D28D9` réservé exclusivement aux Ancrages Humains* — affichant `🤖 Exécuté sous Contrat d'Autonomie #{contract_id} — Déclencheur : {MANUAL | WEBHOOK | LOG_SINK_ALERT | CRON} — 0 intervention humaine en cours de run`, accompagné des sorties de secours explicites `🛑 Kill-Switch (Suspendre le Trigger & les Runs actifs)` et `⏪ Invalider & Rollback`.

## Do's and Don'ts

| Do | Don't |
| :--- | :--- |
| Conserver les 7 entrées du Menu Global visibles dans la Sidebar gauche (avec filtrage RBAC) | Cacher la navigation globale uniquement derrière des commandes texte dans le chat |
| Utiliser le violet `{colors.human-led}` exclusivement pour les **Ancrages Humains Obligatoires** | Pré-remplir par IA un champ marqué `human_authored_required: true` ou y ajouter un bouton d'auto-complétion IA |
| Signaler tout livrable produit en mode `AUTONOMOUS_CONTRACT` par le badge Cyan/Cobalt `AutonomousExecutionBadge` avec `🛑 Kill-Switch` et `⏪ Invalider & Rollback` | Faire passer un artefact généré sans humain pour un artefact relu par un expert humain ou utiliser le violet `human-led` sur un badge autonome |
| Afficher systématiquement le **Briefing de Revue (4 blocs)** en haut du Canvas avant un **Artefact** volumineux | Afficher un document brut de 30 pages avec un unique bouton "Tout Approuver" en bas de page |
| Séparer visuellement les **Workflow Runs** en mode *Contributeur (Actions requises)* et *Consultation seule (Observateur)* | Laisser un utilisateur en mode *Consultation seule* cliquer sur des boutons d'édition qui échouent ensuite |
| Garder le **Dock Agent Assistant & Permission Broker** accessible à droite dans les modules 2 à 7 | Forcer l'utilisateur à quitter le Catalogue ou l'Ontologie pour revenir au Cockpit quand il a une question |
