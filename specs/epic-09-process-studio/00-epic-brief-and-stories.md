---
epic_id: EPIC-09
title: "ORCIA Process Studio v2 — Cartographie VSM, Studio Agentique Déterministe & Gates Multi-Niveaux"
version: "2.0.0"
status: READY_FOR_BUILD
owner: "Product & Architecture Team"
target_pi: "PI-13"
dependencies:
  - EPIC-01 (IAM, Permission Broker & Catalogue Fédéré)
  - EPIC-02 (Ontologie Tripartite L1-L4)
  - EPIC-03 (Moteur DBOS, Exécuteurs 3.2f, Anchor Cards 3.4, What-If Sandbox 3.5)
  - EPIC-08 (Settings Hub & <PermissionGuard />)
---

# 1. Vision & Arbitrages Structurants (Post-Analyse Contradictoire)

Pour faire évoluer l'écran **« Mes Processus »** d'ORCIA sans créer une « usine à gaz BPM » rigide ni violer les invariants d'architecture (ADR-01 à ADR-10), l'**ORCIA Process Studio v2** repose sur **6 arbitrages fondamentaux** :

1. **Séparation entre Cartographie de Chaîne de Valeur (Macro-VSM) et Workflows Exécutables Bornés :**
   * La vue de bout en bout (comme les 11 étapes et 4 phases du POC *« De l'idée à la production »*) est modélisée comme une **Chaîne de Valeur (`ValueStreamMap`)** de gouvernance et d'alignement méthodologique (incluant les étapes purement humaines et les rituels physiques comme le PIP).
   * Chaque étape outillée de cette chaîne pointe vers un **Workflow DBOS Unitaire et Borné (`WorkflowDefinitionV2`)** (ex. *Workflow Qualification & PRD*, *Workflow Étude d'Architecture*, *Workflow Découpage US*). On n'enferme jamais 6 mois de cycle de vie SAFe dans une seule transaction SQL ouverte.
2. **Zéro « Agent Orchestrateur » lisant le chat (Respect strict ADR-01 & ADR-02) :**
   * Un LLM ne pilote jamais la transition d'une sous-étape à une autre en lisant une chaîne de texte (`STATUT : QUALIFIÉ`).
   * Les séquences multi-étapes (ex. *Qualification $\rightarrow$ PRD $\rightarrow$ Création Ticket*) sont orchestrées par une **Séquence Déterministe de Sous-Étapes DBOS (`DeterministicSubStep`)** dont les verrous de validation humaine sont gérés par la machine à états PostgreSQL.
3. **Divulgation Progressive UX (Sans collision EXEMPLE / Control-M / POC) :**
   * **Niveau Macro (Gouvernance & Consultation VSM) :** Reprend l'ergonomie du POC HTML (bascule `Aujourd'hui | Avec les agents | Comparer`, points de passage losanges, boucles de retour en pointillés orange, fiche à 6 onglets, mode Présentation).
   * **Niveau Micro (Conception & Exécution Technique d'un Workflow) :** Reprend l'ergonomie épurée à **5 blocs de BMC Control-M** (`Triggers`, `Steps & Agent Pipeline`, `Toolbox MCP`, `Gates Pipeline`, `Skills & Contract`) assistée par le **Co-pilote IA à gauche** et le commutateur `Design Mode | Test Mode (What-If) | YAML`. Le popup redondant `COUCHES` de EXEMPLE est supprimé.
4. **Étanchéité Absolue `orcia-core` vs `orcia-pack-*` :**
   * `packages/orcia-core` est 100 % agnostique : aucune mention de `Jira`, `Git`, `PRD`, `WSJF`, `SAFe`, `Rovo` ou `Copilot` n'existe dans ses schémas Pydantic. Tout typage métier passe par des URI génériques du Catalogue Fédéré (`catalog://{connector}/{entity_type}`) et des références de Pack (`pack://{pack_id}/...`).
   * Le seed complet du POC *« Mon Compte — De l'idée à la production »* est logé exclusivement dans `packages/orcia-pack-sdlc`.
5. **Clarification du Mode d'Exécution (`NATIVE_ORCIA` vs `EXTERNAL_DELEGATED_GATE`) :**
   * **`NATIVE_ORCIA` :** L'agent s'exécute sur le runtime ORCIA (`apps/worker` + LiteLLM + MCP + Sandbox). ORCIA maîtrise chaque sous-étape, chaque token et chaque appel d'outil.
   * **`EXTERNAL_DELEGATED_GATE` :** L'humain travaille dans un outil externe fermé (ex. GitHub Copilot dans l'IDE ou Rovo dans Atlassian). ORCIA n'invente pas une fausse orchestration du chat externe : il fournit le **Paquet de Contexte d'Entrée** et agit en **Sas de Contrôle (`Gatekeeper`)** sur le livrable déposé (PR Git, page Confluence, ticket Jira) en exécutant ses Gates déterministes et contradictoires avant le Point de Passage Humain.
6. **Pattern Claim-Check (SeaweedFS S3) & Idempotence Cyclique DBOS :**
   * Aucun contenu massif (livrable Markdown, code, Diff) ne transite dans les tables d'état DBOS/PostgreSQL (plafond strict $< 64\text{ Ko}$). Tout artefact est stocké dans **SeaweedFS (S3)** et référencé par un pointeur immuable `ClaimCheckPointer(s3_uri, sha256, byte_size)`.
   * Toute clé d'idempotence d'étape DBOS intègre le compteur d'itération `(run_id, step_id, iteration_index)` pour permettre les **boucles de retour (`REJECT_AND_LOOP`)** en mode `corrections` sans collision avec le cache de l'itération précédente.

---

# 2. Découpage en User Stories (Format INVEST / SAFe)

## Story 9.1 : Modèle Agnostique `orcia-core` (VSM + Workflows Bornés + Claim-Check) & Seed `orcia-pack-sdlc`
* **En tant qu'** Architecte Plateforme,
* **Je veux** séparer dans `orcia-core` le schéma de Chaîne de Valeur (`ValueStreamMapSpec`) et le schéma de Workflow Exécutable (`WorkflowDefinitionV2`) en utilisant des pointeurs S3 `ClaimCheckPointer` et des URI génériques `catalog://`, tout en fournissant le seed *« Mon Compte »* dans `orcia-pack-sdlc`,
* **Afin de** garantir une note de découplage Core/Pack de $5/5$ et d'éviter tout engorgement de PostgreSQL.
* **Critères d'Acceptation :**
  * **CA-9.1.1 (Zéro fuite SDLC dans Core) :** Aucun mot-clé métier SDLC (`jira`, `git`, `prd`, `wsjf`, `rovo`, `copilot`) n'apparaît dans `packages/orcia-core`. Un test d'architecture automatisé (`test_core_domain_isolation.py`) le vérifie à chaque build.
  * **CA-9.1.2 (Immuabilité & Fork Draft) :** Toute modification d'un workflow `PUBLISHED` crée une branche `vX.Y.Z-draft` sans impacter les exécutions DBOS actives.
  * **CA-9.1.3 (Claim-Check obligatoire) :** Tout livrable d'étape ou diff supérieur à $4\text{ Ko}$ est automatiquement persisté dans SeaweedFS avec calcul de son empreinte SHA-256 avant l'enregistrement du checkpoint DBOS.

## Story 9.2 : Vue Cartographie de Chaîne de Valeur (Macro-VSM) & Comparaison 3 États
* **En tant que** Product Owner, Architecte ou Auditeur (`workflows:read`),
* **Je veux** naviguer dans la carte horizontale de la chaîne de valeur (4 phases, 11 étapes, 5 points de passage losanges et boucles de retour en pointillés orange) avec bascule `Aujourd'hui | Avec les agents | Comparer` et mode `Présenter`,
* **Afin de** piloter la transformation métier, inspecter les 6 onglets de chaque étape et lancer ou rejoindre le workflow exécutable rattaché à une étape.
* **Critères d'Acceptation :**
  * **CA-9.2.1 (Commutateur 3 États en Consultation) :** Bascule fluide entre l'état manuel actuel, la cible agentique et la comparaison côte-à-côte prouvant que *« l'étape change de producteur, jamais de décideur »*.
  * **CA-9.2.2 (Boucles de retour SVG sans collision) :** Tracé dynamique des boucles de retour principales (tirets orange) et secondaires (pointillés) sous les cartes, avec surbrillance au survol du losange de passage.
  * **CA-9.2.3 (Pont VSM $\rightarrow$ Workflow Exécutable) :** Sur chaque carte d'étape outillée, un bouton permet d'ouvrir son Workflow dans le **Studio 5 Blocs** (si `workflows:write`) ou de lancer/suivre une exécution unitaire (si `workflows:trigger`).

## Story 9.3 : Studio de Conception de Workflow (5 Blocs Control-M + Co-pilote Gauche + Sous-Étapes DBOS)
* **En tant que** Concepteur de Processus (`workflows:write`),
* **Je veux** concevoir un workflow unitaire via un Co-pilote conversationnel à gauche et un canevas structuré en 5 blocs (`Triggers & Contract`, `Deterministic Sub-Steps Pipeline`, `Toolbox MCP`, `Gates Pipeline`, `Skills & Knowledge`),
* **Afin de** configurer visuellement des chaînes d'agents natifs ou délégués sans jamais écrire de logique de routage dans un prompt.
* **Critères d'Acceptation :**
  * **CA-9.3.1 (Co-pilote & Suggestions Catalogue) :** Le chat de gauche suggère dynamiquement les `Toolboxes MCP`, `Skills` et `Gates` du Pack actif ; un clic sur `[+]` les attache au bloc sélectionné.
  * **CA-9.3.2 (Séquence de Sous-Étapes Déterministes DBOS) :** Le bloc central permet d'enchaîner $N$ sous-étapes (ex. `1. Qualification` $\rightarrow$ `2. Rédaction PRD` $\rightarrow$ `3. Création Ticket`) séparées par des **Verrous d'État DBOS** (losange exigeant une validation humaine explicite ou rond `auto: true`), avec bouton de bypass unitaire (`enabled: false` $\rightarrow$ `SKIPPED`).
  * **CA-9.3.3 (Modes `NATIVE_ORCIA` vs `EXTERNAL_DELEGATED_GATE`) :** Chaque étape permet de choisir si l'agent est exécuté par ORCIA (sélection du Modèle LLM et du Niveau d'Effort `Rapide / Équilibré / Approfondi`) ou délégué à un outil externe avec sas de contrôle ORCIA en sortie.

## Story 9.4 : Pipeline Ordonné de Gates (Déterministes Auto-Heal 3x $\rightarrow$ Probabilistes) & Test Mode What-If
* **En tant que** Tech Lead / Responsable Qualité,
* **Je veux** empiler dans l'ordre strict les Gates déterministes (exécutées en sandbox avec auto-remédiation bornée à 3 essais) puis les Gates non-déterministes (Hunters contradictoires ou évaluateurs custom), et les tester en `Test Mode (What-If Sandbox)`,
* **Afin de** bloquer immédiatement les livrables non conformes à coût token nul avant de solliciter un agent reviewer ou un humain (ADR-06).
* **Critères d'Acceptation :**
  * **CA-9.4.1 (Ordre Inviolable & Auto-Heal) :** Le moteur exécute d'abord 100 % des `DeterministicControlSpec`. En cas d'échec en mode `NATIVE_ORCIA`, la sortie `stderr` est renvoyée à l'agent producteur jusqu'à `max_self_heal_retries` (défaut : $3$) avant d'interrompre le flux.
  * **CA-9.4.2 (Gates Probabilistes Conditionnées) :** Les agents contradictoires (*Blind Hunter*, *Edge Case Hunter*, *Challenger*) ne sont invoqués que si toutes les Gates déterministes ont réussi.
  * **CA-9.4.3 (Exécution Sandbox What-If) :** Le bouton `Test Mode` exécute le workflow dans une transaction isolée sans aucun appel `write` externe et affiche la matrice `ImpactAssessmentResult`.

## Story 9.5 : Les 5 Dispositifs d'Interaction Humaine (HITL) & Boucles de Reprise Itératives
* **En tant qu'** Acteur Métier (PO, PM, Architecte, Dev, QA, RSSI),
* **Je veux** disposer d'interfaces d'interaction adaptées à chaque moment du workflow (Questionnaire structuré, Choix d'options, Jalon de sous-étape DBOS, Prévisualisation obligatoire avant écriture MCP, et Arbitrage Anchor Card à 4 actions avec routage de refus),
* **Afin de** rester l'unique décideur et auteur responsable des livrables.
* **Critères d'Acceptation :**
  * **CA-9.5.1 (Write-Preview Gate Obligatoire) :** Tout appel d'outil MCP mutatif (`create_item`, `update_document`, `open_pr`) est intercepté par le *Permission Broker* et mis en attente d'une confirmation humaine sur prévisualisation.
  * **CA-9.5.2 (Arbitrage Souverain à 4 Actions sur Diff S3) :** Sur une Anchor Card ou un Point de Passage, l'arbitre ayant pris en charge la carte (`Claim`) peut : `1. Accepter & Signer`, `2. Amender directement le Diff` (génère une nouvelle version S3 sans relancer l'IA), `3. Refuser & Choisir la boucle de retour`, ou `4. Suspendre le SLA`.
  * **CA-9.5.3 (Incrémentation d'itération sur Boucle de Retour) :** Lors d'un refus renvoyant vers une étape ou sous-étape amont, DBOS incrémente `iteration_index` ($i \leftarrow i + 1$) et injecte les remarques de l'arbitre à l'agent en mode `corrections`.
