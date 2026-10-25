---
name: ORCIA
title: ORCIA — Visual Identity & Design System (Direction C : Enterprise Adaptive Hybrid)
status: final
created: 2026-10-24
updated: 2026-10-24
description: Plateforme d'exécution de processus d'entreprise et personnels "Human-Led, Agent-Accelerated". Basée sur shadcn/ui (Radix + Tailwind CSS) avec l'architecture visuelle Direction C (Menu Latéral Sombre Explicite + Espace Central Haut-Contraste + Dock Agent Assistant Persistant).
colors:
  sidebar-bg: '#0F172A'
  sidebar-foreground: '#F8FAFC'
  sidebar-muted: '#94A3B8'
  sidebar-border: '#1E293B'
  background: '#F8FAFC'
  surface: '#FFFFFF'
  dock-bg: '#F1F5F9'
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
    fontFamily: 'Instrument Serif, Georgia, serif'
    fontSize: 22px
    fontWeight: '700'
    lineHeight: '1.25'
  mono:
    fontFamily: 'JetBrains Mono, Geist Mono, monospace'
    fontSize: 12px
rounded:
  sm: 5px
  md: 8px
  lg: 10px
  full: 9999px
spacing:
  sidebar-expanded: 235px
  sidebar-collapsed: 68px
  dock-width: 360px
components:
  sidebar-nav-item-active:
    background: '{colors.primary}'
    foreground: '{colors.primary-foreground}'
    radius: '{rounded.md}'
  human-led-anchor-card:
    background: '{colors.human-led-bg}'
    border: '1px solid {colors.human-led}'
    borderLeft: '4px solid {colors.human-led}'
    radius: '{rounded.md}'
  arbitration-tiebreak-card:
    background: '{colors.arbitration-bg}'
    border: '1px solid {colors.arbitration-amber}'
    borderLeft: '4px solid {colors.arbitration-amber}'
    radius: '{rounded.md}'
  review-briefing-grid:
    background: '{colors.surface}'
    border: '1px solid {colors.border}'
    radius: '{rounded.md}'
  uri-badge:
    fontFamily: '{typography.mono.fontFamily}'
    radius: '{rounded.sm}'
---

## Brand & Style

**ORCIA** incarne la posture **"Human-Led, Agent-Accelerated"** à travers la **Direction C (Hybride Entreprise Haut-Contraste)**. Son identité visuelle combine trois sensations immédiates :
1. **Autorité & Orientation (Sidebar Sombre `#0F172A`)** : Un repère stable à gauche qui affiche clairement les **7 Modules Globaux** d'ORCIA et leurs badges d'activité temps réel, repliable en icônes seules (`68px`) lorsque l'utilisateur souhaite maximiser sa surface de travail.
2. **Clarté Cognitive & Lisibilité Documentaire (Espace Central Clair `#F8FAFC` / `#FFFFFF`)** : Une surface calme et lumineuse pensée pour la lecture sans fatigue des **Briefings de Revue**, la rédaction réfléchie des **Ancrages Humains Obligatoires** et la **Validation par Découpage** des **Artefacts** volumineux (avec un thème Dark Slate `#0B0F17` commutable pour les sessions de développement nocturnes ou techniques).
3. **Co-présence Intelligente (Dock Agent Assistant `#F1F5F9` / `#FFFFFF`)** : Un espace conversationnel toujours accessible, au centre dans le module *1. Cockpit*, ou ancré à droite (`360px`) dans les modules *2 à 7*.

ORCIA hérite des fondations de **shadcn/ui (Radix UI + Tailwind CSS)**. Ce document spécifie uniquement la couche identitaire et les composants cognitifs propres à ORCIA.

## Colors

Chaque couleur sémantique d'ORCIA possède une signification stricte liée à la gouvernance humano-agentique — aucune couleur d'accent n'est utilisée à titre purement décoratif :

- **Sidebar Slate (`#0F172A`)** : Fond permanent du menu de navigation global à 7 modules, isolant visuellement la navigation de la surface de travail.
- **Primary Cobalt (`#2563EB` Light / `#6366F1` Dark)** : Action principale, module actif dans la Sidebar, et indicateur de présence de l'**Agent Assistant**.
- **Human-Led Violet (`#6D28D9` / Fond `#F5F3FF`)** : Réservé exclusivement aux **Ancrages Humains Obligatoires** (`human_authored_required: true`). Dès que l'utilisateur voit une bordure violette, il sait que l'IA a l'interdiction de rédiger cette zone à sa place et que sa réflexion d'expert (*Think*) est attendue.
- **Arbitration & Challenge Amber (`#D97706` / Fond `#FFFBEB`)** : Indique une suspension du **Workflow Run** requérant une décision humaine : **Arbitrage Humain** sur options équivalentes, challenge inter-rôles (ex: Architecte $\rightarrow$ PM), ou suspicion de *Rubber-Stamping*.
- **Gate Pass Emerald (`#059669` / Fond `#ECFDF5`)** : Indique une **Gate** (Déterministe, Agentique Cross-Model ou Humaine) franchie avec succès, un verrou de présence pris en charge (*Claimed*), ou un cache `SHA-256` vérifié.
- **Ontology Cyan (`#0284C7` / Fond `#F0F9FF`)** : Identifie les concepts de l'**Ontologie Dynamique Multi-Niveaux** (badges de niveau 1 à 4, promotions sémantiques, traductions par **Profil Humain**).
- **Stale / Blocker Crimson (`#DC2626` / Fond `#FEF2F2`)** : Alerte d'obsolescence documentaire (`[STALE_WARNING]` sur une **Base de Connaissances**), échec de **Gate Déterministe** ou blocage d'habilitation intercepté par le **Permission Broker**.

## Typography

- **Interface & Conversation (`Inter` / `Geist Sans`, `13.5px`)** : Densité calibrée pour afficher côte à côte le menu, le **Canvas** et le **Dock Agent Assistant** sans troncature sur un écran portable 14" ou un moniteur externe.
- **Titres d'Artefacts & Livrables (`Instrument Serif` / `Georgia`, `22px`)** : Utilisé uniquement pour l'en-tête des **Artefacts** documentaires (`PRD`, `Dossier d'Architecture`) dans le **Canvas** afin de marquer visuellement la distinction entre le flux de discussion éphémère (sans-serif) et le livrable contractuel de référence (serif).
- **Provenance, URI & Code (`JetBrains Mono` / `Geist Mono`, `12px`)** : Obligatoire pour toutes les URI du **Catalogue Fédéré** (`db://`, `git://`, `nexus://`), les empreintes `SHA-256` et les logs de **Sandbox**.

## Layout & Spacing

L'architecture spatiale Desktop repose sur une grille fluide à **3 colonnes adaptatives** :
1. **Colonne Gauche — Sidebar du Menu Global (`235px` dépliée / `68px` repliée en icônes)** : Contient les 7 entrées du menu d'ORCIA, le bouton de repli `«` et le badge de **Profil Humain** en pied de barre.
2. **Colonne Centrale — Espace Principal / Canvas (`1fr`, min `640px`)** :
   - Dans le module **1. Cockpit & Chat**, l'espace central est partagé en Split-View entre la **Conversation principale** et le **Canvas d'Artefact/Gate**.
   - Dans les modules **2 à 7** (*Mes Runs, Catalogue Fédéré, Ontologie & KB, Gates & IAM, FinOps, Admin*), le module occupe tout l'espace central (`1fr`).
3. **Colonne Droite — Dock Persistant Agent Assistant & Permission Broker (`360px`, repliable)** : Présent dans les modules 2 à 7 pour permettre de piloter, filtrer ou résoudre un problème d'habilitation en langage naturel tout en travaillant sur le module central.

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

## Do's and Don'ts

| Do | Don't |
| :--- | :--- |
| Conserver les 7 entrées du Menu Global visibles dans la Sidebar gauche (avec filtrage RBAC) | Cacher la navigation globale uniquement derrière des commandes texte dans le chat |
| Utiliser le violet `{colors.human-led}` exclusivement pour les **Ancrages Humains Obligatoires** | Pré-remplir par IA un champ marqué `human_authored_required: true` ou y ajouter un bouton d'auto-complétion IA |
| Afficher systématiquement le **Briefing de Revue (4 blocs)** en haut du Canvas avant un **Artefact** volumineux | Afficher un document brut de 30 pages avec un unique bouton "Tout Approuver" en bas de page |
| Séparer visuellement les **Workflow Runs** en mode *Contributeur (Actions requises)* et *Consultation seule (Observateur)* | Laisser un utilisateur en mode *Consultation seule* cliquer sur des boutons d'édition qui échouent ensuite |
| Garder le **Dock Agent Assistant & Permission Broker** accessible à droite dans les modules 2 à 7 | Forcer l'utilisateur à quitter le Catalogue ou l'Ontologie pour revenir au Cockpit quand il a une question |
