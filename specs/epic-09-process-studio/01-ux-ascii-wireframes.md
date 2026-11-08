---
document_type: UX_SPECIFICATION_AND_ASCII_WIREFRAMES
epic_id: EPIC-09
version: "2.0.0"
target_app: "apps/web (React 19, TanStack Router, Tailwind CSS, Radix UI)"
---

# Spécification UX/UI & Wireframes ASCII (v2) — Divulgation Progressive

Pour éliminer toute surcharge cognitive (Arbitrage n°3), l'interface sépare nettement **deux niveaux d'usage** :
1. **La gouvernance métier & Chaîne de Valeur (`/processes` & `/processes/vsm/$vsmId`)** : Cartographie de bout en bout, comparaison *Aujourd'hui vs Avec les agents*, boucles de retour et lancement de workflows unitaires.
2. **L'atelier d'ingénierie d'un Workflow Borné (`/processes/studio/$workflowId`)** : Interface à 5 blocs façon **BMC Control-M** + Co-pilote à gauche + modes `Design | Test What-If | YAML` (sans le popup redondant `COUCHES` de KORE).

---

## ÉCRAN 1 : Hub « Mes Processus » — Chaînes de Valeur (VSM) & Workflows Unitaires (`/processes`)

```text
+----------------------------------------------------------------------------------------------------------------------+
| [ORCIA]  Espace : [ Pack SDLC · Mon Compte v ]   Santé : [● DBOS OK] [● S3 OK]         Rôle : [Archi / Write] [Romain]|
+----------------------------------------------------------------------------------------------------------------------+
| [≡] |  MES PROCESSUS & CHAÎNES DE VALEUR                                                  [+ Nouveau Workflow Express]|
|     |  Explorez la chaîne de valeur de l'équipe ou exécutez directement un workflow agentique unitaire.              |
|  🏠 |                                                                                                                |
|  💬 |  +----------------------------------------------------------------------------------------------------------+  |
|  📁 |  | 🗺️ CHAÎNE DE VALEUR DE L'ÉQUIPE (MACRO-CARTOGRAPHIE VSM)                                                 |  |
| >🔀 |  |----------------------------------------------------------------------------------------------------------|  |
|  🤖 |  | De l'idée à la production · Le workflow agentique de Mon Compte (Pack : orcia-pack-sdlc)                 |  |
|  🛡️ |  | 4 Temps · 11 Étapes (dont 6 augmentées par IA) · 5 Points de passage humains ◆ · 8 Boucles de retour ↩   |  |
|  ⚙️ |  |                                                                                                          |  |
|     |  |   [01 Funnel]──►[02 En revue]──►◆──►[03 Archi]──►[04 Exigences]──►◆──►[05 Prio]──►[06 US]──►◆──►[08 Dev] |  |
|     |  |                       ▲         :         ▲                       :                   ▲     :            |  |
|     |  |                       +=========+         +=======================+                   +=====+            |  |
|     |  |                                                                                                          |  |
|     |  | [ 🗺️ Ouvrir la Carte Interactive (Aujourd'hui / Avec Agents / Comparer) ]     [ 🎬 Lancer Présentation ] |  |
|     |  +----------------------------------------------------------------------------------------------------------+  |
|     |                                                                                                                |
|     |  WORKFLOWS EXÉCUTABLES UNITAIRES (MOTEUR DURABLE DBOS)                                                         |
|     |  Filtres : [● Publiés (3)]  ( Brouillons (1) )  ( Exécutions actives (2 · 🔶 1 Anchor Card) )                  |
|     |                                                                                                                |
|     |  +--------------------------------------+ +--------------------------------------+ +-------------------------+ |
|     |  | ● WF-01 · Qualification & PRD  [v1.0]| | ● WF-03 · Étude d'Archi CRL    [v1.2]| | ● WF-06 · Découpe US    | |
|     |  | Rattachement : Étapes 01 & 02 VSM    | | Rattachement : Étape 03 VSM          | | Rattachement : Étape 06 | |
|     |  | Mode : [🤖 Natif ORCIA + MCP Jira]   | | Mode : [🤖 Natif ORCIA / 🔌 IDE Gate]| | Mode : [🤖 Natif ORCIA] | |
|     |  |--------------------------------------| |--------------------------------------| |-------------------------| |
|     |  | 3 sous-étapes DBOS · 2 Jalons ◆      | | 4 sous-étapes DBOS · 3 Jalons ◆      | | 5 sous-étapes · 4 Jalons| |
|     |  | Gates : 1 Déterm. · 1 Challenger IA  | | Gates : 1 Déterm. · 2 Hunters IA     | | Gates : 1 Déterm · 1 IA | |
|     |  |                                      | |                                      | |                         | |
|     |  | [▷ Exécuter] [✏️ Studio (Fork Draft)]| | [▷ Exécuter] [✏️ Studio (Fork Draft)]| | [▷ Exécuter] [✏️ Studio]| |
|     |  +--------------------------------------+ +--------------------------------------+ +-------------------------+ |
+----------------------------------------------------------------------------------------------------------------------+
```

---

## ÉCRAN 2 : Vue Cartographie de Chaîne de Valeur (`/processes/vsm/$vsmId`) — Gouvernance & Comparaison

Cet écran est dédié à la lecture métier, à la comparaison `Aujourd'hui / Avec les agents / Comparer` et à l'inspection des 6 onglets (aucun bouton de code YAML ou de paramétrage bas niveau ne vient polluer cette vue).

```text
+----------------------------------------------------------------------------------------------------------------------+
| ← Retour Hub | 🗺️ De l'idée à la production | Vue : (Aujourd'hui) [● Avec les agents] (Comparer)                     |
| Aller à : [01 Émergence] [02 Priorisation] [03 Réalisation] [04 Livraison] | Zoom: [-] [100%] [+] [Affichage▾] [?]   |
| * Principe : 6 étapes sur 11 changent de producteur, aucune de décideur.                             [🎬 Présenter]  |
+----------------------------------------------------------------------------------------------------------------------+
|                                                                                                                      |
|  === 01 · ÉMERGENCE & CADRAGE (Du besoin aux spécifications) ======================================================  |
|                                                                                                                      |
|                  +==============================+                       +=================================+          |
|                  | 02                [POC][WF-01]|                       | 03                   [POC][WF-03]|          |
|                  | En revue (PRD & Feature)     |    Comité d'accueil   | Cadrage d'architecture          |          |
|  (Un besoin )    |------------------------------|         Humain        |---------------------------------|          |
|  (exploré   )───►| 🤖 WF-01 · Prod. & PRD       |           ◆           | 🤖 WF-03 · Étude d'archi CRL    |          |
|  (discovery )    | Sous-étape Rédaction PRD puis|─────────►/ \─────────►| L'architecte construit le DE    |──► ...   |
|                  | Création Feature avec preview|          \ /   validé | avec l'agent (options, 6 blocs).|          |
|                  | [Ouvrir Fiche] [✏️ Studio WF]|           v           | [Ouvrir Fiche]  [✏️ Studio WF]  |          |
|                  |------------------------------|           :           |---------------------------------|          |
|                  | 👤 Humains                   |           :           | 👤 Humains                      |          |
|                  | |PO/PM| valide le PRD,       |           :           | |Architecte| répond, arbitre,   |          |
|                  |         valide la Feature    |           :           |              valide chaque bloc |          |
|                  |------------------------------|           :           |---------------------------------|          |
|                  | Sortie                       |           :           | Sortie                          |          |
|                  | Ticket Feature au gabarit    |           :           | Dossier d'étude (DE) au gabarit |          |
|                  |------------------------------|           :           |---------------------------------|          |
|                  | Contrôles (Gates)            |           :           | Contrôles (Gates)               |          |
|                  | [☑️ Script: caractères/champ]|           :           | [☑️ Structure DE & Mermaid]     |          |
|                  | [✨ Agent challenger du PRD ]|           :           | [✨ Agent contradicteur Archi]  |          |
|                  +==============================+           :           +=================================+          |
|                                 ▲                           :                                                        |
|                                 +===========================+                                                        |
|                            ( ↩ Non validé : remarques renvoyées à l'étape 02 en mode corrections )                   |
+----------------------------------------------------------------------------------------------------------------------+
```

---

## ÉCRAN 3 : Studio de Conception d'un Workflow Exécutable (`/processes/studio/$workflowId`) — Architecture 5 Blocs Control-M

Lorsqu'un concepteur (`workflows:write`) clique sur `[✏️ Studio WF]` sur le workflow **WF-01 (Qualification & PRD)** ou **WF-06 (Découpe US)**, il entre dans le Studio technique qui adopte la disposition claire à **5 blocs de BMC Control-M** couplée au **Co-pilote à gauche** et à l'ordonnancement de **Sous-Étapes Déterministes DBOS**.

```text
+----------------------------------------------------------------------------------------------------------------------+
| ← Hub | WF-01 · Qualification, PRD & Création Feature · [v1.1.0-draft]   | [● Design Mode] (▷ Test What-If) (YAML)   |
| Contrats globaux : [✨ Pré-prompt Système] [📋 Contrat d'Entrée/Sortie]  | [💾 Enregistrer Draft] [🚀 Publier v1.1.0]|
+-----------------------------------+----------------------------------------------------------------------------------+
| 🤖 CO-PILOTE STUDIO               |                                                                                  |
|-----------------------------------|            +--------------------------------------------------------+            |
| J'ai structuré WF-01 en 3         |            | 1. TRIGGERS & CONTRAT D'ENTRÉE                     [+] |            |
| sous-étapes déterministes DBOS.   |            |--------------------------------------------------------|            |
| Aucune transition n'est laissée   |            | • Manuel / API : `discovery_notes` (Texte / Document)  |            |
| au hasard d'un prompt LLM.        |            | • Reprise sur boucle retour : `committee_remarks`      |            |
|                                   |            | • Mode d'entrée : `generer` | `corrections`            |            |
| +-------------------------------+ |            +---------------------------o----------------------------+            |
| | 🧰 SUGGESTED TOOLBOXES (MCP)  | |                                        :                                         |
| | [+] SearchTool (Confluence)   | |                                        v                                         |
| | [+] ContentReadTool           | |   +------------------------------------o-------------------------------------+   |
| | [+] IssueSearchTool (JQL)     | |   | 2. SÉQUENCE DE SOUS-ÉTAPES DÉTERMINISTES DBOS (PIPELINE)             [+] |   |
| | [+] FieldSearchTool (Jira)    | |   | Mode d'exécution : [● 🤖 Natif ORCIA] (🔌 Sas Externe IDE/Rovo)          |   |
| +-------------------------------+ |   | Modèle : [Claude 3.5 Sonnet v] · Effort : [Équilibré v] · Quota : 16k tk |   |
| | 🧩 SUGGESTED SKILLS (PACK)    | |   |--------------------------------------------------------------------------|   |
| | [+] Calculateur Score WSJF    | |   |  +--------------------------------------------------------------------+  |   |
| | [+] Gabarit PRD Light         | |   |  | [👁️] Sous-étape 2.1 : Qualification du besoin          [Agent Step]|  |   |
| +-------------------------------+ |   |  |      Définit Qui, Quoi, Pourquoi, Périmètre depuis les sources.    |  |   |
| | 🛡️ SUGGESTED GATES (3.5)      | |   |  +---------------------------------│----------------------------------+  |   |
| | [+] Script: Longueur champs   | |   |                                    ▼                                     |   |
| | [+] Challenger PRD (Hunter)   | |   |         ◆ JALON DBOS #1 : Suspension `WAITING_HUMAN_CHECKPOINT`          |   |
| +-------------------------------+ |   |           Rôle : `product_owner` · Validation de la Qualification        |   |
|                                   |   |                                    │                                     |   |
| [👤 Vous]                         |   |                                    ▼                                     |   |
| Ajoute le Skill de calcul WSJF    |   |  +--------------------------------------------------------------------+  |   |
| sur la sous-étape 2 (Rédaction    |   |  | [👁️] Sous-étape 2.2 : Rédaction PRD Light              [Agent Step]|  |   |
| PRD) et exige une prévisualisation|   |  |      Rédige KPI, critères d'acceptation, WSJF et effort.           |  |   |
| avant la création dans Jira.      |   |  +---------------------------------│----------------------------------+  |   |
|                                   |   |                                    ▼                                     |   |
| [🤖 Co-pilote]                    |   |         ◆ JALON DBOS #2 : Suspension `WAITING_HUMAN_CHECKPOINT`          |   |
| C'est fait :                      |   |           Rôle : `product_owner` · Validation du PRD Light               |   |
| 1. Skill `wsjf-calculator` lié    |   |                                    │                                     |   |
|    au bloc SKILLS.                |   |                                    ▼                                     |   |
| 2. `write_preview_required: true` |   |  +--------------------------------------------------------------------+  |   |
|    activé sur la sous-étape 3.    |   |  | [👁️] Sous-étape 2.3 : Détection doublons & Création    [Agent+Tool]|  |   |
|                                   |   |  |      🔒 WRITE-PREVIEW GATE : Prévisualisation obligatoire avant API|  |   |
|-----------------------------------|   |  +--------------------------------------------------------------------+  |   |
| [Décrire une modification...    ] |   +------------------------------------o-------------------------------------+   |
|                                   |                                        :                                         |
|                                   |         +------------------------------+------------------------------+          |
|                                   |         :                              :                              :          |
|                                   |         v                              v                              v          |
|                                   |  +------o------------------+  +--------o-----------------+  +---------o--------+ |
|                                   |  | 3. TOOLBOX MCP      [+] |  | 4. SKILLS & SOCLE    [+] |  | 5. GATES (3.5)[+]| |
|                                   |  |-------------------------|  |--------------------------|  |------------------| |
|                                   |  | • SearchTool     [Read] |  | • Skill: Calcul WSJF     |  | 1. [☑️ Déterm.]  | |
|                                   |  | • IssueSearchJQL [Read] |  | • Skill: Gabarit PRD     |  |    Longueur chp  | |
|                                   |  | • CreateWorkItem        |  | • Socle: Modèles & KPI   |  |    (Auto-Heal 3x)| |
|                                   |  |   [🔒 Write + Preview]  |  | • Stockage: Claim-Check  |  | 2. [✨ Probab.]  | |
|                                   |  |                         |  |   SeaweedFS S3 (SHA-256) |  |    Challenger PRD| |
|                                   |  +-------------------------+  +--------------------------+  +------------------+ |
+-----------------------------------+----------------------------------------------------------------------------------+
```

---

## ÉCRAN 4 : Configuration du Mode « Sas Externe (`EXTERNAL_DELEGATED_GATE`) » (Ex: Étape 08 Dev ou Rovo/Copilot Externe)

Pour répondre à l'**Arbitrage n°5**, lorsqu'une équipe utilise un agent externe dans son IDE (GitHub Copilot / Claude Code) ou dans Atlassian Rovo, ORCIA affiche clairement son rôle de **Fournisseur de Contexte MCP + Sas de Contrôle (Gatekeeper)** sans feindre d'exécuter le LLM externe.

```text
+----------------------------------------------------------------------------------------------------------------------+
| Mode d'exécution du Workflow : (🤖 Exécution Native ORCIA)  [● 🔌 Sas Externe Délégué (IDE Copilot / Rovo / Webhook)]|
+----------------------------------------------------------------------------------------------------------------------+
|                                                                                                                      |
|  +-----------------------------------+      +-----------------------------------+      +--------------------------+  |
|  | 1. PAQUET DE CONTEXTE ORCIA (MCP) |      | 2. TRAVAIL EXTERNE (HORS ORCIA)   |      | 3. SAS DE GATES ORCIA    |  |
|  | Servi par ORCIA à l'outil externe | ===► | Exécuté par l'humain et son outil | ===► | Déclenché sur Webhook    |  |
|  |-----------------------------------|      |-----------------------------------|      |--------------------------|  |
|  | • US au gabarit DoR/INVEST        |      | • Outil : GitHub Copilot / IDE    |      | • Événement attendu :    |  |
|  | • Dossier d'Étude Archi (`DE.md`) |      | • Acteur : Développeur (pilote,   |      |   `git:pr_opened` ou     |  |
|  | • Standards d'équipe & Invariants |      |   corrige et assume le code)      |      |   dépôt artefact S3/Git  |  |
|  | • Exposition via serveur MCP ORCIA|      | • Aucune consommation token ORCIA |      | • Exécute Gates Déterm.  |  |
|  |   (`orcia://context/run/{run_id}`)|      |   pendant la phase d'édition IDE  |      |   + Hunters + Revue Dev ◆|  |
|  +-----------------------------------+      +-----------------------------------+      +--------------------------+  |
+----------------------------------------------------------------------------------------------------------------------+
```
