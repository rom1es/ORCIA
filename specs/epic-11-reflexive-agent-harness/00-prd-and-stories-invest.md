---
epic_id: EPIC-11
title: "Orchestration Non-Déterministe Réflexive (Assistant, Agents & Processus Dynamiques) vs Orchestration Déterministe (Processus DBOS)"
version: "2.0.0"
status: READY_FOR_BUILD
owner: "Core Platform & AI Runtime Team"
target_pi: "PI-13"
dependencies:
  - EPIC-01 (Permission Broker & Catalogue Fédéré)
  - EPIC-03 (Moteur DBOS pour Processus Déterministes, Write-Preview 3.4, Gates 3.5)
  - EPIC-09 (ORCIA Process Studio v2)
  - EPIC-10 (packages/orcia-connectors & Packs Déclaratifs packs/<domaine>/)
---

# 1. Product Requirements Document (PRD) — Dualité d'Orchestration Non-Déterministe (Antigravity) et Déterministe (DBOS)

## 1.1. Principe Directeur : Quel moteur orchestre quoi dans ORCIA ?
Il est essentiel de ne pas sur-utiliser **DBOS** là où l'intelligence doit rester fluide, émergente et exploratoire. L'architecture d'ORCIA repose donc sur **deux moteurs d'orchestration complémentaires** selon l'objet manipulé :

| Brique Fonctionnelle ORCIA | Mode d'Orchestration | Moteur d'Exécution (`packages/orcia-core`) | Justification & Comportement |
| :--- | :--- | :--- | :--- |
| **1. Mon Assistant** | **100 % Non-Déterministe** | `ReflexiveAsyncRuntime` *(Sans DBOS)* | L'assistant découpe dynamiquement la question à la volée (`Think -> Act -> Observe`), explore les fichiers par tranches `#L1-200` et répond en streaming SSE ultra-rapide sans créer de transactions SQL DBOS à chaque pensée. |
| **2. Les Agents LLM** | **100 % Non-Déterministe** | `ReflexiveAsyncRuntime` *(Sans DBOS)* | Un agent est autonome dans son raisonnement interne : il choisit dynamiquement quels outils de lecture, *Skills* ou vérifications (`Check ...`) enchaîner jusqu'à produire son livrable. |
| **3. Mes Processus (Mode A : Dynamique / Agentique)** | **Non-Déterministe** | `ReflexiveProcessPlanner` *(Sans DBOS)* | Processus piloté par l'objectif (comme dans l'écran express d'ORCIA ou une tâche complexe confiée à Antigravity) : le planificateur réflexif découpe et adapte dynamiquement la liste des étapes et agents à mobiliser en temps réel. |
| **4. Mes Processus (Mode B : Gouverné / Machine à états)** | **Déterministe** | `DBOS Durable Engine` *(PostgreSQL)* | Processus d'entreprise formel à graphe d'étapes figé, conçu pour durer plusieurs jours/semaines avec checkpoints SQL durables, comités humains, SLAs et boucles de retour strictes. *(Conformément au Principe 7 de l'ADR-02, lorsqu'une étape DBOS appelle un Agent, l'agent s'exécute en interne via le `ReflexiveAsyncRuntime` non-déterministe).* |

---

## 1.2. Fonctionnement du Moteur Non-Déterministe (`ReflexiveAsyncRuntime` — Style Antigravity)
Pour **Mon Assistant**, les **Agents** et les **Processus Non-Déterministes**, ORCIA exécute une boucle asynchrone légère en mémoire (`asyncio` + journal de session *append-only* + streaming **Redis SSE**) qui reproduit exactement le mécanisme d'**Antigravity** :

1. **Découpage et re-planification dynamique à chaque tour (`Think`) :**
   * Face à une demande (ex. *« go pour les 2 points dans une branche git dédiée »*), l'orchestrateur non-déterministe ne suit aucun rail pré-programmé.
   * Il émet une réflexion courte (`Thought for 13s ›`), formule une intention de phase (`Checking git worktrees and running dev servers`) et décide dynamiquement de la prochaine micro-action.
2. **Introspection d'environnement et lecture chirurgicale (`Act & Observe`) :**
   * L'agent invoque de lui-même les 4 primitives chirurgicales de `packages/orcia-connectors` :
     * `check_resource_state` $\rightarrow$ `Check git status and current branch ›`
     * `outline_resource_structure` $\rightarrow$ Squelette des titres Markdown, clés YAML ou AST code.
     * `search_workspace_snippets` $\rightarrow$ Recherche hybride `pgvector` + regex.
     * `inspect_resource_lines` $\rightarrow$ `Analyzed capabilities.yaml #L1-200` puis `#L200-561`.
3. **Gouvernance maintenue même en mode Non-Déterministe :**
   * Bien que non orchestré par DBOS, le `ReflexiveAsyncRuntime` applique systématiquement le **Permission Broker** (contrôle des scopes RBAC/MCP), la **Write-Preview Gate** (validation humaine obligatoire avant toute écriture externe), le **plafond de tours/tokens** lié au niveau d'effort (`Rapide`, `Équilibré`, `Approfondi`) et l'exécution optionnelle des **Gates** sur le livrable final.

---

# 2. Découpage en User Stories (Format Spec-Kit / SAFe / INVEST)

## Story 11.1 : Les 4 Primitives d'Exploration Chirurgicale dans `packages/orcia-connectors`
* **En tant qu'** Assistant, Agent ou Processus Non-Déterministe,
* **Je veux** interroger n'importe quel connecteur du Catalogue Fédéré via 4 primitives de lecture chirurgicale (`check_state`, `outline_structure`, `search_snippets`, `inspect_lines`),
* **Afin d'** explorer activement les dépôts, documents et tickets par tranches de lignes (`#L1-200`) sans saturer ma fenêtre de contexte LLM.
* **Critères d'Acceptation (Given / When / Then) :**
  * **CA-11.1.1 (Lecture par plage de lignes `#Lstart-end`) :**
    * *Given* une ressource accessible via un connecteur (`git`, `confluence`, `jira`, `workspace_docs`),
    * *When* le runtime invoque `inspect_resource_lines(resource_uri, start_line=1, end_line=200)`,
    * *Then* il reçoit uniquement les lignes $1$ à $200$ numérotées et un badge normalisé `Analyzed {badge} {filename} #L1-200` (plafonné à $250$ lignes max par appel).
  * **CA-11.1.2 (Introspection d'état & Squelette) :**
    * *Given* un besoin de vérification préalable,
    * *When* le runtime invoque `check_resource_state` ou `outline_resource_structure`,
    * *Then* il reçoit l'état temps réel (`Check ... ›`) ou la table des matières avec les numéros de lignes en moins de $150\text{ ms}$.

---

## Story 11.2 : Moteur `ReflexiveAsyncRuntime` (Sans DBOS) pour l'Assistant et les Agents
* **En tant qu'** Architecte Plateforme,
* **Je veux** exécuter l'Assistant et les Agents sur un runtime asynchrone non-déterministe (`ReflexiveAsyncRuntime`) indépendant de DBOS,
* **Afin de** garantir une réactivité maximale en temps réel (zéro latence de transaction SQL par pensée) tout en respectant les bornes d'effort cognitif et la *Write-Preview Gate*.
* **Critères d'Acceptation :**
  * **CA-11.2.1 (Exécution 100 % asynchrone sans overhead DBOS) :**
    * *Given* une question posée dans **Mon Assistant** ou un appel direct à un **Agent**,
    * *When* la boucle `Think -> Act -> Observe` s'exécute,
    * *Then* elle tourne en mémoire via `asyncio`, diffuse chaque micro-étape sur Redis SSE en $< 30\text{ ms}$ et n'écrit aucune ligne dans les tables système de step DBOS. Une fois la boucle terminée, la trace complète et le livrable sont archivés en une seule opération via `ClaimCheckPointer` (SeaweedFS S3).
  * **CA-11.2.2 (Enchaînement libre en lecture, Write-Preview Gate en écriture) :**
    * *Given* la boucle non-déterministe de l'assistant ou d'un agent,
    * *When* l'action décidée est une lecture (`read_only: true`), *Then* elle s'enchaîne immédiatement ;
    * *When* l'action décidée est une écriture externe (`preview_write`), *Then* la boucle met son `asyncio.Event` / jeton de session en attente de la confirmation humaine sur la `WritePreviewCard`.

---

## Story 11.3 : Double Mode d'Orchestration dans « Mes Processus » (Processus Non-Déterministe vs Processus Déterministe DBOS)
* **En tant que** Concepteur de Processus (`workflows:write`),
* **Je veux** pouvoir choisir lors de la création ou de l'édition d'un Processus son mode d'orchestration : **Non-Déterministe (Planification Dynamique Agentique)** ou **Déterministe (Machine à états durable DBOS)**,
* **Afin d'** utiliser le mode dynamique souple pour les processus exploratoires/rapides et de réserver DBOS aux processus d'entreprise stricts à fort enjeu de conformité et d'attente longue.
* **Critères d'Acceptation :**
  * **CA-11.3.1 (Mode Processus Non-Déterministe — `NON_DETERMINISTIC_AGENTIC`) :**
    * *Given* un processus configuré en mode `Non-Déterministe` (avec un objectif, une équipe d'agents/skills autorisés et un gabarit de sortie),
    * *When* l'utilisateur le lance,
    * *Then* le `ReflexiveProcessPlanner` découpe dynamiquement le problème en étapes à la volée, mobilise les agents et outils nécessaires selon ses découvertes, puis soumet le livrable final aux Gates et à la validation humaine sans passer par un graphe DBOS figé.
  * **CA-11.3.2 (Mode Processus Déterministe — `DETERMINISTIC_DBOS`) :**
    * *Given* un processus configuré en mode `Déterministe (DBOS)`,
    * *When* l'utilisateur le lance,
    * *Then* DBOS orchestre strictement la séquence des étapes/sous-étapes, gère les checkpoints SQL durables et les boucles de retour. À l'intérieur d'une étape agentique DBOS, l'agent appelé exécute sa propre boucle non-déterministe via `ReflexiveAsyncRuntime` (Principe 7 de l'ADR-02).

---

## Story 11.4 : Composant UI `<AgentExecutionTrace />` & Inspecteur Chirurgical de Lignes (`#L1-200`)
* **En tant qu'** Utilisateur de **Mon Assistant**, de **Mes Agents** ou de **Mes Processus**,
* **Je veux** visualiser en temps réel la trace repliable d'Antigravity (`Checking ... ⌄`, `Thought for 13s ›`, `Check ... ›`, `Analyzed capabilities.yaml #L200-561`, `Working`) et ouvrir le fichier aux lignes exactes d'un simple clic,
* **Afin de** suivre la progression dynamique de l'orchestration non-déterministe et vérifier chaque source inspectée.
* **Critères d'Acceptation :**
  * **CA-11.4.1 :** Affichage temps réel via SSE des pensées dépliables, des vérifications d'état et des fichiers analysés avec bouton `[⏹️ Arrêter & Répondre maintenant]`.
  * **CA-11.4.2 :** Clic sur `#L200-561` ouvrant le volet `<SourceLineInspectorDrawer />` positionné et surligné sur les lignes $200$ à $561$.
