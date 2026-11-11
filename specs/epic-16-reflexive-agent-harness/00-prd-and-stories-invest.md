---
epic_id: EPIC-16
title: "Orchestration Réflexive (Mon Assistant, Mes Agents & Processus Pilotés par l'Objectif) et Articulation avec les Processus Pilotés par les Jalons"
version: "2.1.0"
status: IN_PROGRESS
owner: "Core Platform & AI Runtime Team"
target_pi: "PI-16"
replaces_draft_spec: "specs/epic-11-reflexive-agent-harness/ (renumérotée en EPIC-16 suite à l'attribution d'EPIC-11..15)"
dependencies:
  - EPIC-01 (Permission Broker & Catalogue Fédéré)
  - EPIC-03 (Moteur Durable PostgreSQL, Write-Preview 3.4, Gates 3.5)
  - EPIC-10 & EPIC-12 (Mon Assistant 2 modes Standard/Approfondi, Shell 4 Zones Direction C, Zéro Jargon Technique)
  - EPIC-14 (ORCIA Process Studio v2 — 5 Blocs Control-M, Claim-Check S3, Gates Auto-Heal 3x)
  - EPIC-15 (packages/orcia-connectors & Packs Déclaratifs packs/<domaine>/)
---

# 1. Product Requirements Document (PRD) — Dualité d'Orchestration Réflexive et par Jalons (`EPIC-16`, `CAP-160`)

## 1.1. Principe Directeur : Quel moteur orchestre quoi dans ORCIA ?
L'architecture d'ORCIA repose sur **deux moteurs d'orchestration complémentaires** strictement isolés derrière des ports hexagonaux (`AD-19`, `AD-20`) et présentés aux utilisateurs en **langage 100 % métier (zéro terme technique en UI ou dans l'aide)** :

| Brique Fonctionnelle ORCIA | Libellé Utilisateur (`fr` / `en`) | Moteur d'Exécution (`packages/orcia-core`) | Justification & Comportement |
| :--- | :--- | :--- | :--- |
| **1. Mon Assistant** | *(Transparent — aucun bandeau moteur)* | `NonDeterministicReflexiveRuntime` *(asyncio pur + SSE, sans DBOS)* | L'assistant découpe dynamiquement la question (`Think -> Act -> Observe`), explore les fichiers par tranches `#L1-200` et répond en vrai streaming SSE (`thinking_delta` + `token_delta`) selon **2 modes uniques** : `Standard` et `Approfondi`. |
| **2. Mes Agents** | *(Transparent)* | `NonDeterministicReflexiveRuntime` *(asyncio pur + SSE, sans DBOS)* | Un agent choisit dynamiquement quels outils de lecture chirurgicale, *Skills* ou vérifications enchaîner jusqu'à produire son livrable. |
| **3. Mes Processus (Mode A)** | **Processus piloté par l'objectif (adaptatif)** / *Goal-driven process (adaptive)* | `NonDeterministicReflexiveRuntime` (`allow_sub_agent_delegation=True`) + `GatePipelineExecutor` | Vous fixez le résultat attendu, le contrat de sortie et les agents mobilisables ; l'enchaînement des recherches s'adapte aux éléments découverts, puis le livrable passe par les Gates et la validation humaine. |
| **4. Mes Processus (Mode B)** | **Processus piloté par les jalons (étapes garanties)** / *Milestone-driven process (guaranteed steps)* | `run_bounded_workflow_v2` *(DBOS Durable Engine sur PostgreSQL 18)* | Vous fixez l'ordre précis des étapes, les validations humaines attendues et les boucles de reprise sur toute la durée du dossier. Lorsqu'une sous-étape invoque un Agent (`agent_executor`), celui-ci exécute sa boucle réflexive en interne et renvoie son `ClaimCheckPointer` final. |

---

## 1.2. Décisions Architecturales & UX Verrouillées (Revue Contradictoire Winston × Sally)
1. **Zéro Jargon Technique côté UI et Aide** : Aucun terme technique (`DBOS`, `asyncio`, `SQL`, `Redis`, `SSE`, `Claim-Check`, `déterministe`, `non-déterministe`) n'apparaît dans l'interface, les badges ou les infobulles `ⓘ`.
2. **Deux Modes d'Effort Cognitif Uniques** : Unification stricte sur **`Standard`** (`EffortLevel.LOW` / `DEFAULT` : plafond court `4` tours / `8 000` tokens, trace compacte) et **`Approfondi`** (`EffortLevel.HIGH` : plafond `25` tours / `48 000` tokens, trace chirurgicale complète).
3. **Séparation Nette des Actions d'Interruption** :
   - Bouton **`■ Arrêter`** : annulation immédiate de l'exécution (`0` token supplémentaire consommé).
   - Action **`Synthétiser maintenant`** dans le pied de la trace active : lève `force_final = True` pour que l'agent cesse d'explorer et rédige immédiatement sa réponse à partir des éléments déjà lus.
4. **Pause `WritePreviewCard` avec *Stateless Suspend/Resume* survivant au `F5`** : Lorsqu'une écriture externe est demandée hors DBOS, le runtime sauvegarde un `ReflexiveSessionSnapshot` léger (JSONB/Redis, TTL `24h`), libère la coroutine ASGI et reprend proprement au tour suivant dès validation humaine du `SignedApprovalToken`.
5. **Sécurité Anti-*Confused Deputy* (`READ_SOURCE`) & Isolation Hexagonale** :
   - `orcia_core` n'importe jamais `orcia_connectors` (`SurgicalExplorerPort` & `BoundedWorkflowLauncherPort` dans `orcia_core/ports/`).
   - Toute inspection de lignes `#Lstart-end` vérifie l'appartenance de l'URI à l'Espace et l'habilitation `READ_SOURCE` de l'appelant (sinon état gouverné `🔒 Extrait protégé`).
   - La délégation inter-agents est bornée à `max_delegation_depth = 1` sur le budget de tokens partagé du processus parent.

---

# 2. Découpage en User Stories (`Story 16.1` à `Story 16.4`)

## Story 16.1 : Ports Hexagonaux & Les 4 Primitives d'Exploration Chirurgicale (`packages/orcia-connectors` & `/api/v1/sources/inspect-lines`)
* **En tant qu'** Assistant, Agent ou Processus piloté par l'objectif,
* **Je veux** interroger les sources autorisées de l'Espace via 4 primitives de lecture chirurgicale (`check_resource_state`, `outline_resource_structure`, `search_workspace_snippets`, `inspect_resource_lines`) derrière un port hexagonal pur `SurgicalExplorerPort`,
* **Afin d'** explorer les dépôts, documents et référentiels par tranches de lignes (`#L1-200`, max `250` lignes) sans saturer la fenêtre de contexte ni violer `READ_SOURCE` ni `lint-imports`.

## Story 16.2 : Moteur `NonDeterministicReflexiveRuntime` (`asyncio` pur, Vrai Streaming SSE & *Suspend/Resume* `WritePreviewCard` survivant au `F5`)
* **En tant qu'** Architecte Plateforme,
* **Je veux** exécuter l'Assistant, les Agents et les Processus pilotés par l'objectif sur `NonDeterministicReflexiveRuntime` (sans DBOS, avec vrai streaming SSE, 2 modes `Standard`/`Approfondi`, boutons séparés `Arrêter` vs `Synthétiser maintenant`, et *Suspend/Resume* sur `WritePreviewCard`),
* **Afin de** garantir une réactivité temps réel immédiate tout en préservant la survie au `F5`, la gouvernance d'écriture et l'archivage `ClaimCheckPointer`.

## Story 16.3 : Double Mode de Processus (« Piloté par l'objectif » vs « Piloté par les jalons »), `ProcessExecutionDispatcher` & Packs Déclaratifs
* **En tant que** Concepteur de Processus (`workflows:write`),
* **Je veux** choisir dans l'Atelier 5 Blocs (`Mes Processus`) entre **Processus piloté par l'objectif (adaptatif)** et **Processus piloté par les jalons (étapes garanties)** sans perdre ma configuration en brouillon,
* **Afin d'** adapter le mode de pilotage à la nature du dossier (`packs/orcia-docs/` en piloté par l'objectif par défaut ; `packs/sdlc/` en piloté par les jalons par défaut et commutable).

## Story 16.4 : Composants `@orcia/ui` `<AgentExecutionTrace />` & `<SourceLineInspectorDrawer />` et Intégration Bout-en-Bout (`Mon Assistant`, `Mes Agents`, `Mes Processus`)
* **En tant qu'** Utilisateur d'ORCIA,
* **Je veux** suivre en direct la trace repliable localisée (`fr`/`en`, zéro jargon technique) et inspecter d'un clic les lignes exactes `#Lstart-end` dans `<SourceLineInspectorDrawer />` (relié aux pastilles `[S1]`),
* **Afin de** vérifier instantanément chaque source consultée depuis `Mon Assistant`, `Mes Agents` et `Mes Processus`.
