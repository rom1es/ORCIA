---
document_type: UX_SPECIFICATION_AND_ASCII_WIREFRAMES
epic_id: EPIC-11
version: "2.0.0"
target_app: "apps/web (React 19, Tailwind CSS, Radix UI) & packages/ui"
---

# Spécifications UX/UI & Maquettes ASCII (v2) — Orchestration Non-Déterministe vs Déterministe (DBOS)

Ce document présente les **4 écrans clés** illustrant comment l'orchestration non-déterministe (style Antigravity) anime nativement **Mon Assistant**, **Mes Agents** et les **Processus Non-Déterministes**, tandis que **DBOS** reste sélectionnable pour les **Processus Déterministes**.

---

## ÉCRAN 1 : « Mon Assistant » & « Mes Agents » — Orchestration 100 % Non-Déterministe en Direct (`/assistant`)

Ici, aucun workflow DBOS n'est impliqué. Le `ReflexiveAsyncRuntime` découpe dynamiquement la question en micro-étapes d'introspection (`Thought`, `Check`, `Analyzed #L1-200`) diffusées en direct par SSE.

```text
+----------------------------------------------------------------------------------------------------------------------+
| [ORCIA]  Espace : [ Pack SDLC · Mon Compte v ]   Interlocuteur : [ 🤖 Assistant / @CRL-Archi ]   Effort : [Approfondi]|
| Moteur : [⚡ Orchestration Non-Déterministe Réflexive (Sans DBOS)]                                                   |
+----------------------------------------------------------------------------------------------------------------------+
| [≡] |  CONVERSATION ACTIVE                                                        | 📄 INSPECTEUR DE SOURCE          |
|     |-----------------------------------------------------------------------------|----------------------------------|
|  🏠 |                                                                             | Fichier : capabilities.yaml      |
| >💬 |  +-----------------------------------------------------------------------+  | Source  : catalog://git/crl-back |
|  📁 |  | 👤 go pour les 2 points dans une branche git dédiée                   |  | Plage   : Lignes #L200-561  [✕]  |
|  🔀 |  +-----------------------------------------------------------------------+  |----------------------------------|
|  🤖 |                                                                             |  199 |     max_attempts: 3       |
|  🛡️ |  Checking git worktrees and running dev servers ⌄                           | >200 | capabilities:             |
|  ⚙️ |                                                                             | >201 |   revocation_check:       |
|     |    Thought for 13s ›                                                        | >202 |     mode: strict_crl      |
|     |                                                                             | >203 |     timeout_ms: 1500      |
|     |    Check git status and current branch ›                                    | >204 |     fallback: deny        |
|     |                                                                             | >205 |   certificate_parse:      |
|     |    Analyzed  M↓ TECH-LEAD-REPORT-TEMPLATE.md #L1-101                        | >206 |     x509_version: 3       |
|     |                                                                             |  ... | ...                       |
|     |    Analyzed  Y  capabilities.yaml #L1-200                                   | >559 |   audit_trail:            |
|     |                                                                             | >560 |     append_only: true     |
|     |    Analyzed  Y  capabilities.yaml #L200-561  ◄── [Cliqué : ouvert à droite] | >561 |     hash_algo: sha256     |
|     |                                                                             |----------------------------------|
|     |    Thought for 9s ›                                                         | [📋 Copier la plage #L200-561]   |
|     |                                                                             | [🔗 Ouvrir dans Git]             |
|     |    Check git branches and recent commits ›                                  |                                  |
|     |                                                                             |                                  |
|     |    Thought for 9s ›                                                         |                                  |
|     |                                                                             |                                  |
|     |    Check modification timestamps of working tree files ›                    |                                  |
|     |                                                                             |                                  |
|     |    Thought for 7s ›                                                         |                                  |
|     |                                                                             |                                  |
|     |    Check git worktrees and running dev servers ›                            |                                  |
|     |                                                                             |                                  |
|     |    ◌ Working... (Planification dynamique · 3 120 tokens)   [⏹️ Arrêter]     |                                  |
|     |-----------------------------------------------------------------------------|                                  |
|     | [ Sources : Toutes les sources v ] [ @Appeler un Agent ] [ /Compétence ]    |                                  |
|     | [ Posez une question ou demandez une action...                        ] [↑] |                                  |
+----------------------------------------------------------------------------------------------------------------------+
```

---

## ÉCRAN 2 : Choix du Mode d'Orchestration dans « Mes Processus » (Non-Déterministe vs Déterministe DBOS)

Dans l'écran **Mes Processus** (`/processes` et `/processes/studio/$workflowId`), le créateur choisit explicitement si son processus est **Non-Déterministe (Agentique)** ou **Déterministe (DBOS)** :

```text
+----------------------------------------------------------------------------------------------------------------------+
| [ORCIA]  Créer / Configurer un Processus Métier                                       Statut : [Brouillon v1.0-draft]|
+----------------------------------------------------------------------------------------------------------------------+
|                                                                                                                      |
|  CHOISISSEZ LE MODE D'ORCHESTRATION DE CE PROCESSUS :                                                                |
|                                                                                                                      |
|  +========================================================+ +------------------------------------------------------+ |
|  | [●] ⚡ PROCESSUS NON-DÉTERMINISTE (DYNAMIQUE / AGENT.) | | ( ) 🛡️ PROCESSUS DÉTERMINISTE (DURABLE / DBOS)       | |
|  |--------------------------------------------------------| |------------------------------------------------------| |
|  | • Moteur : `ReflexiveProcessPlanner` (Sans DBOS).      | | • Moteur : `DBOS Transact` (Machine à états SQL).    | |
|  | • Fonctionnement : Vous définissez l'objectif, le      | | • Fonctionnement : Vous fixez l'ordre exact des      | |
|  |   contrat de sortie et les agents/outils disponibles.  | |   étapes, les jalons de comité et les boucles de     | |
|  |   L'orchestrateur découpe et adapte dynamiquement      | |   retour. DBOS garantit la reprise sur plusieurs     | |
|  |   les étapes à la volée (comme Antigravity).           | |   semaines (Time-travel & checkpoints PostgreSQL).   | |
|  | • Idéal pour : Exploration, audit ad-hoc, génération   | | • Idéal pour : Processus réglementés, cycle SAFe,    | |
|  |   documentaire, analyse transverse rapide.             | |   comités d'architecture, onboarding RH multi-semaines| |
|  +========================================================+ +------------------------------------------------------+ |
|                                                                                                                      |
|  CONFIGURATION DU PROCESSUS NON-DÉTERMINISTE (MODE SÉLECTIONNÉ) :                                                    |
|  +----------------------------------------------------------------------------------------------------------------+  |
|  | 1. Nom du processus * : [ Audit et mise à jour de la documentation d'architecture                            ] |  |
|  | 2. Objectif & Intention confiés au Planificateur Non-Déterministe * :                                          |  |
|  |    [ Inspecte les derniers commits Git et les tickets Jira du sprint, détecte les écarts avec la doc         ] |  |
|  |    [ Confluence actuelle, vérifie les contrats d'API et prépare le brouillon de mise à jour sourcé.          ] |  |
|  |                                                                                                                |  |
|  | 3. Agents & Compétences mobilisables dynamiquement par le processus :                                          |  |
|  |    [🤖 @CRL-Étude-Architecture ×] [🤖 @Rédacteur-Documentation-Orcia ×] [🧩 diagrammes-mermaid ×] [+ Ajouter]  |  |
|  |                                                                                                                |  |
|  | 4. Garde-fous de sortie (Exécutés à la fin du plan dynamique avant remise à l'humain) :                        |  |
|  |    • Gates Déterministes : [☑️ Vérification des sections du Contrat]  [☑️ Syntaxe Mermaid]                     |  |
|  |    • Gates Probabilistes : [☑️ @Blind-Hunter (Seuil de risque : 0.70)]                                         |  |
|  |    • Écriture Externe    : [🔒 Write-Preview Gate obligatoire sur Confluence & Jira]                           |  |
|  +----------------------------------------------------------------------------------------------------------------+  |
|                                                                                  [▷ Tester] [💾 Enregistrer Processus]|
+----------------------------------------------------------------------------------------------------------------------+
```

---

## ÉCRAN 3 : Exécution d'un Processus Non-Déterministe vs Processus Déterministe DBOS

Lorsqu'un processus **Non-Déterministe** s'exécute, il construit son arbre d'étapes et de délégations d'agents à la volée sous les yeux de l'utilisateur :

```text
+----------------------------------------------------------------------------------------------------------------------+
| EXÉCUTION DU PROCESSUS : Audit et mise à jour doc d'archi     Mode : [⚡ Processus Non-Déterministe (Sans DBOS)]     |
+----------------------------------------------------------------------------------------------------------------------+
|  Dynamic Process Planning & Execution ⌄                                                                              |
|                                                                                                                      |
|    Thought for 8s ›  "Je vais d'abord inspecter les commits récents sur crl-back, puis lire la page Confluence..."   |
|                                                                                                                      |
|    Check recent commits on repository crl-back (branch main) ›                                                       |
|                                                                                                                      |
|    Analyzed  TS crl-back/src/controllers/cert.controller.ts #L1-145                                                  |
|                                                                                                                      |
|    Delegated to @CRL-Étude-Architecture : Analyse d'impact du nouveau endpoint /v2/revoke ⌄                          |
|      ├── Thought for 6s ›                                                                                            |
|      ├── Analyzed  Y  openapi-crl.yaml #L80-210                                                                      |
|      └── ✓ Synthèse d'impact produite (2 modifications de schéma détectées)                                          |
|                                                                                                                      |
|    Delegated to @Rédacteur-Documentation-Orcia : Mise à jour de la section 4 du dossier d'architecture ⌄             |
|      ├── Analyzed  M↓ doc-architecture-crl.md #L120-260                                                              |
|      └── ✓ Brouillon Markdown généré avec diagramme Mermaid mis à jour                                               |
|                                                                                                                      |
|  ───► Passage automatique dans le Pipeline de Gates de sortie :                                                      |
|       [🟢 Gate Déterministe : Contrat Markdown & Mermaid OK (18ms)]                                                  |
|       [🟢 Gate Contradictoire : @Blind-Hunter Score 0.15 < 0.70 OK]                                                  |
|                                                                                                                      |
|  +----------------------------------------------------------------------------------------------------------------+  |
|  | 👤 VALIDATION HUMAINE FINALE DU LIVRABLE (Diff Côte-à-Côte)                                                    |  |
|  | [👁️ Inspecter le Diff (#L120-260)]   [✅ Accepter & Publier sur Confluence]   [✏️ Amender]   [↩ Relancer]      |  |
|  +----------------------------------------------------------------------------------------------------------------+  |
+----------------------------------------------------------------------------------------------------------------------+
```
