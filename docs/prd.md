---
title: ORCIA (Orchestration of Processes, Context, and Intelligent Agents)
status: final
created: 2026-10-24
updated: 2026-10-24
---

# PRD: ORCIA (Orchestration of Processes, Context, and Intelligent Agents)

## 0. Document Purpose

Ce Product Requirements Document (PRD) définit les exigences fonctionnelles et non-fonctionnelles d'**ORCIA** pour son déploiement pilote en entreprise (avec comme premier cas d'usage de validation un cycle d'Ingénierie Logicielle / IT de bout en bout). Il s'adresse au Product Manager (John), à l'Architecte Système (Winston), à la Designer UX (Sally), à l'Ingénieure Dev (Amelia) ainsi qu'aux parties prenantes de gouvernance IT et Métier. Ce PRD s'appuie sur le [Product Brief](file:///home/romain/Documents/Projects/ORCIA/docs/planning-artifacts/product-brief.md) et applique une discipline terminologique stricte : chaque concept du domaine est défini une seule fois dans le **Glossaire (§3)** et utilisé sans synonyme dans l'ensemble du document.

---

## 1. Vision

**ORCIA** est une plateforme d'exécution de processus d'entreprise et personnels qui réconcilie la rigueur des moteurs de workflows gouvernés avec l'intelligence adaptative des agents IA, tout en garantissant que **l'humain conserve la maîtrise intellectuelle, la responsabilité décisionnelle et la compréhension durable de ses systèmes ("Human-Led, Agent-Accelerated")**.

L'accès par défaut à ORCIA s'effectue via une interface **Chat-First + Canvas** animée par un **Agent Assistant** qui s'adapte automatiquement au **Profil Humain** de son interlocuteur (Rôle, Business Unit, Habilitations et vocabulaire issu de l'**Ontologie**). Pour éviter le piège cognitif du "relecteur passif" (biais d'ancrage), ORCIA impose des **Ancrages Humains Obligatoires** sur les choix tactiques et stratégiques en amont de la génération IA, interdit tout choix arbitraire silencieux en cas d'options équivalentes (**Arbitrage Humain**), et outille la revue des **Artefacts** volumineux via un **Briefing de Revue** et une **Validation par Découpage**.

Pensée pour les organisations complexes, ORCIA fédère à la volée les ressources de l'entreprise (**Workflows**, **Agents Exécuteurs**, **Agents Évaluateurs**, **Skills**, **Gabarits d'Artefact**, **Bases de Connaissances** et **Ontologies**) depuis la base interne (`db://`), les dépôts de code (`git://`) ou les registres d'artefacts (`nexus://`) avec un cache local immuable garantissant la **Provenance Auditable**. La fiabilité de la chaîne est assurée par des **Gates** multi-niveaux (Déterministes, Agentiques Cross-Model et Humaines à politique adaptative), des **Contrôles Transverses d'Invariants** contre la dérive d'intention, la détection de **Pattern Drift**, et un **Permission Broker** guidant proactivement les utilisateurs dans l'obtention de leurs habilitations.

---

## 2. Target User

### 2.1 Jobs To Be Done (JTBD)

- **Fonctionnel (Exécution & Gouvernance de bout en bout)** : Permettre aux acteurs métiers et IT (PM, Architectes, Tech Leads, Développeurs, Auditeurs, Managers) d'exécuter des **Workflows** collaboratifs complexes mêlant **Agents Exécuteurs**, **Bases de Connaissances**, **Skills** et interventions humaines, tout en garantissant la conformité aux standards d'entreprise via des **Gates** et une **Ontologie** partagée.
- **Cognitif ("Human-Led, Agent-Accelerated")** : Maintenir la réflexion humaine (*Think*) au bon niveau grâce aux **Ancrages Humains Obligatoires**, à l'**Arbitrage Humain** sur options équivalentes, au **Briefing de Revue** et à la **Validation par Découpage**, en éliminant le biais d'ancrage et la fatigue de relecture.
- **Opérationnel (Multi-Workflows & Habilitations)** : Permettre à chaque collaborateur ou équipe de piloter simultanément plusieurs **Workflow Runs** dynamiques (en mode *Consultation* ou *Contributeur*) via un centre de notifications intelligent, et de résoudre immédiatement tout blocage d'accès grâce au **Permission Broker**.
- **Stratégique & FinOps** : Donner à la direction la visibilité complète sur le ROI budgétaire (Coût de Setup + Coût de Run vs TTM) et garantir la **Réversibilité Humaine** (absence de **Pattern Drift** et maintien de la maîtrise intellectuelle du système).

### 2.2 Non-Users (v1)

- Les systèmes temps-réel ultra-basse latence (micro-seconde / trading haute fréquence / automatisation industrielle embarquée) où la boucle agentique et humaine n'a pas de sens.
- Les utilisateurs cherchant un simple chatbot généraliste non gouverné, sans processus, sans **Ontologie** ni **Gates**.

### 2.3 Key User Journeys (UJ-1 à UJ-9)

*Récits complets avec protagonistes nommés illustrant les capacités d'ORCIA. Les exigences fonctionnelles (§4) référencent directement ces parcours (`Réalise UJ-X`).*

#### UJ-1. Hélène (Product Manager) analyse un nouveau besoin produit et co-construit le PRD de son évolution avec son Agent IA
- **Persona + contexte** : Hélène, Product Manager du produit *Paiement*, doit analyser une demande métier pour ajouter le remboursement instantané multi-devises avec garantie de taux pendant 48h, et rédiger le PRD de cette évolution.
- **Entry state** : Connectée sur l'interface **Chat-First + Canvas** d'ORCIA ; l'**Agent Assistant** reconnaît son **Profil Humain** (`Rôle: Product Manager`) et adapte son vocabulaire (orienté valeur métier, parcours client et règles de gestion via l'**Ontologie**).
- **Path** :
  1. Hélène démarre un nouveau **Workflow Run** d'évolution produit et expose le besoin initial dans le chat.
  2. Le **Step** 1 charge le **Gabarit d'Artefact** `PRD-Evolution` et présente à Hélène dans le **Canvas** les **Ancrages Humains Obligatoires** (`human_authored_required: true`) : *Problème utilisateur*, *Valeur métier attendue / KPI*, et *Risque à ne pas faire*. Hélène les rédige elle-même pour poser sa vision sans biais d'ancrage.
  3. L'**Agent Exécuteur** (Agent PM) interroge la **Base de Connaissances** produit et l'**Ontologie**, identifie les règles de gestion existantes impactées, dialogue avec Hélène pour préciser les cas limites, et lui soumet un **Arbitrage Humain** sur deux options de règle métier équivalentes.
  4. L'**Artefact** `PRD` est généré dans le **Blackboard**, validé par découpage par Hélène lors de la **Gate Humaine** du **Step** 1, et transmis au **Step** 2 (Architecture SI).
- **Climax** : Hélène a transformé un besoin brut en un `PRD` structuré et conforme à l'**Ontologie** de l'entreprise, tout en restant l'auteure des décisions stratégiques.
- **Resolution** : Le **Workflow Run** notifie l'Architecte SI (Antoine) pour l'analyse d'impact.
- **Edge case** : Si Hélène tente de sauter un **Ancrage Humain Obligatoire**, l'agent refuse de rédiger la justification métier à sa place et l'accompagne par des questions socratiques.

#### UJ-2. Antoine (Architecte SI) réalise l'analyse d'impact dans le SI, challenge la PM sur des règles métier complexes et rédige le Dossier d'Architecture pour le Tech Lead
- **Persona + contexte** : Antoine, Architecte SI, intervient au **Step** 2 du **Workflow Run** pour analyser l'impact du `PRD` d'Hélène sur le Système d'Information et produire le Dossier d'Architecture (`DAT`) à destination du Tech Lead.
- **Entry state** : Antoine ouvre le **Workflow Run** depuis ses notifications ; l'**Agent Assistant** adapte la restitution à son **Profil Humain** (`Rôle: Architecte SI`) et affiche le **Briefing de Revue** du `PRD` (*Résumé*, *Éléments clés*, *Décisions prises*, *Hypothèses retenues*).
- **Path** :
  1. Antoine mobilise son **Agent Exécuteur** (Agent Architecte) connecté aux **Bases de Connaissances** de cartographie du SI et à l'**Ontologie** pour évaluer les impacts applicatifs et les adhérences.
  2. L'analyse démontre que la règle métier *"Garantie de taux de change fixe pendant 48h sans couverture de trésorerie"* demandée dans le `PRD` imposerait la modification lourde de 3 systèmes centraux.
  3. Antoine déclenche dans ORCIA un **Challenge / Boucle de Rétroaction Amont** vers Hélène (PM) : l'agent traduit l'impact technique et budgétaire en langage métier via l'**Ontologie** et propose à Hélène une alternative viable (*Garantie de taux limitée à 15 minutes ou plafonnée à 500 €*).
  4. Hélène accepte et met à jour la règle dans le `PRD` (`v1.1` dans le **Blackboard**). Antoine renseigne ensuite ses **Ancrages Humains Obligatoires** d'architecture, co-rédige le **Dossier d'Architecture** selon son **Gabarit d'Artefact**, valide la **Gate Agentique** (avec **Contrôle Transverse d'Invariants** vis-à-vis du `PRD v1.1`) et transmet le dossier au Tech Lead.
- **Climax** : L'Architecte a pu challenger le besoin métier en amont avec des arguments factuels issus du SI, évitant des semaines de développements coûteux avant de rédiger un **Dossier d'Architecture** réaliste.
- **Resolution** : Le `PRD v1.1` et le `Dossier d'Architecture v1.0` sont verrouillés dans le **Blackboard** et passent au **Step** 3 (Tech Lead).

#### UJ-3. Yanis (Tech Lead / Dev Senior) détecte une incompatibilité d'API partenaire due à une documentation obsolète et déclenche une révision du besoin ou une demande partenaire
- **Persona + contexte** : Yanis, Tech Lead / Dev Senior, prend en charge le **Step** 3 pour analyser le `PRD` et le `Dossier d'Architecture` d'Antoine avant de lancer le développement.
- **Entry state** : Yanis ouvre le **Workflow Run** dans l'interface **Chat-First + Canvas** avec son **Agent Exécuteur** équipé de **Skills** d'inspection technique (**MCP** OpenAPI / **Sandbox**).
- **Path** :
  1. En confrontant le `Dossier d'Architecture` et le `PRD` avec le contrat OpenAPI réel du partenaire bancaire externe, Yanis et son agent découvrent qu'une règle métier nécessite une modification de l'API partenaire : la documentation présente dans la **Base de Connaissances** (utilisée aux **Steps** 1 et 2) n'était pas à jour ou a évolué depuis (`v3`), rendant l'appel incompatible.
  2. Le système lève une alerte d'obsolescence documentaire (*Knowledge Staleness Alert*) et bloque la progression.
  3. Yanis déclenche depuis la conversation une **Escalade d'Incompatibilité & Rewind** vers Antoine (Architecte) et Hélène (PM) en exposant l'**Arbitrage Humain** :
     - *Option A* : Revoir le besoin métier dans le `PRD` pour s'adapter à l'API partenaire actuelle.
     - *Option B* : Demander une évolution de l'API au partenaire externe (génération du cahier des charges partenaire et mise en pause versionnée du **Workflow Run**).
  4. L'équipe arbitre sur l'Option A pour le lot immédiat (et planifie l'Option B pour le lot suivant). Yanis met immédiatement à jour la documentation de l'API partenaire dans la **Base de Connaissances** et l'**Ontologie**.
- **Climax** : Une défaillance documentaire sur une API externe est détectée avant le codage, remonte proprement toute la chaîne (Tech Lead $\rightarrow$ Architecte $\rightarrow$ PM) et met à jour la **Base de Connaissances** pour éviter que l'erreur ne se reproduise.
- **Resolution** : Le **Workflow Run** rejoue de manière ciblée (*Replay*) l'ajustement du `PRD` et du `Dossier d'Architecture`, puis passe au codage.

#### UJ-4. Nadia (Lead Métier & Référente Conformité) traite ses notifications personnelles et d'équipe, suit plusieurs Workflows simultanés (Consultation vs Contribution) et débloque 3 runs
- **Persona + contexte** : Nadia supervise la conformité métier sur une douzaine de **Workflow Runs** qui s'exécutent simultanément et dynamiquement. Sur certains, elle est en **Consultation seule (Observatrice)** ; sur d'autres, elle ou son équipe est **Contributrice** et doit intervenir pour débloquer le flux.
- **Entry state** : Nadia se connecte à ORCIA ; l'interface **Chat-First + Canvas** affiche ses notifications entrantes (individuelles et adressées à son équipe *Conformité*).
- **Path** :
  1. L'**Agent Assistant** lui résume ses priorités et affiche dans le **Canvas** la vue multi-workflows scindée entre **"Actions Requises (Contributeur)"** et **"Workflows suivis (Consultation seule)"**.
  2. Nadia consulte d'abord l'avancement en temps réel de 2 **Workflow Runs** en mode *Consultation seule* (lecture de la progression des **Steps** et des **Briefings de Revue**, sans droit de modification).
  3. Elle bascule ensuite sur les 3 **Workflow Runs** qui requièrent son intervention (en prenant en charge / *Claim* une notification destinée à son équipe) :
     - *Run #1 (Question d'un Agent IA)* : elle répond directement dans le chat à une demande d'**Arbitrage Humain** d'un **Agent Exécuteur** sur un seuil réglementaire.
     - *Run #2 (Question d'un Humain)* : elle répond à la question d'Antoine (Architecte) et Yanis (Tech Lead) concernant l'impact CGV d'une modification de règle métier.
     - *Run #3 (Artefact à valider)* : elle ouvre la **Gate Humaine** d'un audit, parcourt le **Briefing de Revue** et valide l'**Artefact** par découpage dans le **Canvas**.
- **Climax** : En une seule session fluide, Nadia a surveillé ses processus en observation et débloqué 3 **Workflow Runs** parallèles (question IA, question humaine, validation d'**Artefact**) pour elle et son équipe.
- **Resolution** : Les 3 **Workflow Runs** reprennent instantanément leur exécution dynamique et les membres de l'équipe de Nadia voient que les notifications ont été traitées.
- **Edge case** : Si un collègue de son équipe ouvre la même notification d'équipe simultanément, un verrou de présence temps réel évite toute double saisie contradictoire.

#### UJ-5. Marc (Tech Lead) lance un Workflow d'ingénierie en posture "Human-Led", tranche une option d'implémentation équivalente et enrichit l'Ontologie
- **Persona + contexte** : Marc, Tech Lead d'une équipe produit, pilote un **Workflow** technique de conception et implémentation d'un microservice tout en veillant à ce que l'équipe garde la maîtrise du code.
- **Entry state** : Connecté sur **Chat-First + Canvas** avec le **Profil Humain** `Tech Lead`.
- **Path** :
  1. Marc lance le **Workflow** résolu depuis `git://...` et rédige les **Ancrages Humains Obligatoires** du **Gabarit d'Artefact** technique (*Principes de découpage* et *Stratégie de résilience*).
  2. Lorsque l'**Agent Exécuteur** rencontre deux implémentations équivalentes (Redis Lock vs PostgreSQL Advisory Lock), il suspend le **Step** et sollicite l'**Arbitrage Humain** de Marc dans le chat.
  3. Durant la conversation, l'agent extrait un nouveau concept métier/technique, l'enregistre dans l'**Ontologie** de niveau *Run (Niveau 4)* et propose à Marc une carte de promotion gouvernée vers l'**Ontologie** d'*Équipe (Niveau 3)*.
- **Climax** : L'**Artefact** technique et le code sont produits sans choix arbitraire silencieux de l'IA, et le patrimoine sémantique de l'équipe (**Ontologie**) s'enrichit en continu.
- **Resolution** : Le **Step** passe aux **Gates** de vérification.

#### UJ-6. Sophie (Auditrice SecOps) réalise une revue guidée par découpage après une Gate Agentique Cross-Model et Déterministe
- **Persona + contexte** : Sophie, ingénieure SecOps transverse, intervient sur les **Gates** de sécurité de multiples projets sans pouvoir relire manuellement chaque ligne de chaque livrable de 50 pages.
- **Entry state** : Connectée avec le **Profil Humain** `SecOps` ; ses **Gates Humaines** sont configurées avec une **Politique de Gate Adaptative**.
- **Path** :
  1. En amont, la **Gate Déterministe** a exécuté les tests et linters en **Sandbox**, validé le **Gabarit d'Artefact**, vérifié l'**Ontologie** et contrôlé l'absence de **Pattern Drift**.
  2. La **Gate Agentique** a fait auditer l'**Artefact** par un **Agent Évaluateur** utilisant un modèle distinct de l'**Agent Exécuteur** (**Orthogonalité des Modèles**), effectué le **Contrôle Transverse d'Invariants** contre le `PRD` initial, et généré le **Briefing de Revue**.
  3. Sophie ouvre la **Gate Humaine** dans le **Canvas** : elle consulte le **Briefing de Revue** (*Résumé*, *Éléments clés*, *Décisions prises*, *Hypothèses retenues*), examine l'**Artefact** via la **Validation par Découpage**, corrige une hypothèse en co-édition et accorde son Go.
- **Climax** : Une revue de sécurité hautement fiabilisée, concentrée sur les décisions critiques et protégée contre le *Rubber-Stamping*.
- **Resolution** : Le **Workflow Run** est autorisé à passer au déploiement.

#### UJ-7. Lucas (Développeur) résout un blocage d'habilitation grâce au Permission Broker et rejoue uniquement l'étape en échec (Replay)
- **Persona + contexte** : Lucas, développeur backend, exécute un **Step** de pré-déploiement faisant appel à un **Skill** dans `nexus://` et à un serveur **MCP** d'infrastructure.
- **Entry state** : Le **Workflow Run** s'exécute en mode *Passthrough* avec les habilitations de Lucas.
- **Path** :
  1. L'appel **MCP** échoue car Lucas ne possède pas l'habilitation sur l'environnement cible.
  2. Le **Permission Broker** intercepte le refus, interroge la **Base de Connaissances** des procédures d'habilitation de l'entreprise et explique précisément à Lucas dans le chat quelle demande soumettre, dans quelle application et auprès de quel valideur.
  3. Une fois l'habilitation obtenue, Lucas déclenche un **Replay** à partir du **Step** 3 uniquement (les **Steps** 1 et 2 restent acquis grâce au **Blackboard** et au *Version Pinning* `SHA-256`).
- **Climax** : Zéro temps perdu à chercher comment obtenir un droit d'accès dans l'entreprise, et zéro gaspillage FinOps grâce au **Replay** ciblé.
- **Resolution** : Le **Workflow Run** se termine avec une **Provenance Auditable** complète.

#### UJ-8. Claire (Directrice BU) pilote l'optimisation budgétaire (FinOps Setup + Run vs TTM) et la Réversibilité Humaine
- **Persona + contexte** : Claire dirige une Business Unit et doit arbitrer les budgets d'automatisation IA tout en s'assurant que ses équipes conservent la maîtrise intellectuelle de leur patrimoine logiciel.
- **Entry state** : Connectée à ORCIA ; l'**Agent Assistant** traduit automatiquement les indicateurs dans le vocabulaire exécutif de l'**Ontologie** *Entreprise/BU*.
- **Path** :
  1. Claire interroge l'**Agent Assistant** sur le bilan mensuel de sa BU.
  2. Le **Canvas** affiche la comparaison entre le coût de setup des **Workflows**, le coût FinOps des tokens en Run, l'économie budgétaire globale, le gain de TTM, ainsi que les métriques cognitives : ratio *Cadrage Human-Led vs Relecture*, alertes de *Rubber-Stamping* (validations humaines en moins de 10 secondes) et indice de **Pattern Drift** / **Réversibilité Humaine**.
- **Climax** : Claire dispose des preuves tangibles d'optimisation budgétaire pour financer la pérennisation du dispositif tout en détectant proactivement toute dérive de déresponsabilisation humaine.
- **Resolution** : Claire ajuste les budgets FinOps et demande une revue d'architecture sur un **Workflow** présentant un début de **Pattern Drift**.

#### UJ-9. Karim (Ingénieur Plateforme) publie et gouverne des Agents, Skills et Gabarits dans le Catalogue Fédéré (DB / Git / Nexus)
- **Persona + contexte** : Karim conçoit des **Agents Exécuteurs**, des **Skills** et des **Gabarits d'Artefact** mutualisés pour toute l'entreprise ou pour des départements spécifiques.
- **Entry state** : Karim a publié un bundle de **Skill** versionné dans Nexus (`nexus://...`) et un **Workflow** dans Git (`git://...`).
- **Path** :
  1. Karim enregistre les URI dans le **Catalogue Fédéré** d'ORCIA sans dupliquer les fichiers sources.
  2. Il configure les droits RBAC/ABAC granulaires : *Découverte & Exécution* pour toute l'entreprise, *Lecture du code/prompt* réservée au groupe `SecOps`, et *Édition* réservée à son équipe.
  3. Il fait passer la ressource par le cycle de publication gouverné (`Brouillon` $\rightarrow$ `Partagé Équipe` $\rightarrow$ `Publié Entreprise`).
- **Climax** : Mutualisation immédiate à l'échelle de l'entreprise avec protection de la propriété intellectuelle et garantie que les **Workflow Runs** en cours restent épinglés à leur version d'origine via le cache `SHA-256`.
- **Resolution** : Les nouvelles exécutions résolvent automatiquement la nouvelle version approuvée.

#### UJ-10. Arthur (Lead Métier / Tech Lead) co-conçoit avec l'Agent Assistant et exécute en tâche de fond un Workflow d'audit de conformité Documentation vs Codebase existante
- **Persona + contexte** : Arthur (Lead Métier / Tech Lead) craint que certaines règles métiers critiques soient mal implémentées dans une codebase existante (`git://...`) ou que la documentation de référence (**Base de Connaissances**) ne soit plus à jour. Il souhaite un audit croisé exhaustif sans bloquer sa journée.
- **Entry state** : Connecté à l'interface **Chat-First + Canvas** ; la documentation métier est indexée dans la **Base de Connaissances** et le dépôt Git est accessible via le **Catalogue Fédéré** (en mode *Passthrough*).
- **Path** :
  1. Arthur demande à l'**Agent Assistant** de lui proposer un **Workflow** pour comparer la documentation métier et la codebase existante.
  2. Le workflow de nœuds de l'**Agent Assistant** interroge le **Catalogue Fédéré** et l'**Ontologie**, puis génère dans le **Canvas** une proposition de **Workflow-as-Code** en 4 **Steps** (*1. Extraction des règles métiers documentées $\rightarrow$ 2. Scan AST/Code en Sandbox $\rightarrow$ 3. Confrontation croisée & Gate Agentique Orthogonale $\rightarrow$ 4. Rapport de divergence et d'arbitrage*).
  3. Arthur demande en langage naturel une modification (ex: cibler le module `billing/`, vérifier les tests unitaires existants et exiger un classement explicite entre *Suspicion de bug code* et *Suspicion de doc obsolète*). L'**Agent Assistant** met à jour le manifeste YAML et valide sa conformité via la **Gate Déterministe** de schéma (`FR-11`).
  4. Arthur demande à l'**Agent Assistant** d'enregistrer ce **Workflow** dans son **Workspace** et de le lancer immédiatement en tâche de fond (*Mode Fast-Path / Background Audit*). Il renseigne l'**Ancrage Humain Obligatoire** initial (périmètre et intention d'audit) et poursuit ses autres activités pendant que les workers exécutent le **Workflow Run** de manière asynchrone en accumulant les écarts et hypothèses (`[ASSUMPTION]`, `[BUG_CODE_SUSPECTED]`, `[DOC_OBSOLETE_SUSPECTED]`) sans interrompre les étapes intermédiaires.
- **Climax** : Dès la fin de l'exécution en tâche de fond, Arthur reçoit une notification temps réel (`< 500 ms`) dans son **Centre de Notifications** (`FR-2`). En un clic, il ouvre le rapport de comparaison dans le **Canvas**, structuré par un **Briefing de Revue** en 4 blocs (`FR-6`) et accompagné d'une **Validation par Découpage** où chaque écart détecté appelle son **Arbitrage Humain** (`Intention -> Code` : créer un correctif de code ou marquer la doc en `STALE_WARNING` `FR-23`).
- **Resolution** : Aucune règle métier erronée n'est transformée silencieusement en documentation, et Arthur arbitre en quelques minutes les actions correctives à lancer.

---

## 3. Glossary

*Les workflows aval (UX, Architecture, Epics/Stories, Implémentation) doivent utiliser ces termes exactement, sans synonyme.*

1. **Workflow** : Définition déclarative et versionnée d'un processus métier ou personnel composé d'un graphe ordonné de **Steps** séparés par des **Gates**, respectant par défaut la discipline `Intention -> Code` (la rétro-documentation `Code -> Doc` étant réservée à l'initialisation *Brownfield Bootstrap*).
2. **Workflow Run (ou Run)** : Instance d'exécution d'un **Workflow**, épinglée de manière immuable (*Version Pinning*) aux versions exactes (`SHA-256`) du **Workflow** et de toutes ses ressources fédérées.
3. **Step (Étape)** : Unité atomique de travail au sein d'un **Workflow**, exécutée par un **Agent Exécuteur**, un humain ou un script déterministe, lisant le contexte filtré du **Blackboard** et produisant un ou plusieurs **Artefacts**.
4. **Ancrage Humain Obligatoire (Human-Led Anchor)** : Section ou décision critique d'un **Step** ou d'un **Gabarit d'Artefact** marquée `human_authored_required: true` (ex: intention métier, risque à ne pas faire, découpage tactique, choix d'architecture) que l'IA a l'interdiction de pré-remplir afin d'éliminer le biais d'ancrage et de maintenir la réflexion humaine (*Think*) au bon niveau.
5. **Gate (Jalon)** : Point de contrôle obligatoire entre deux **Steps**. Plusieurs **Gates** peuvent être combinées entre deux **Steps** selon 3 typologies :
   - **Gate Déterministe** : Validation automatisée par script en **Sandbox**, vérification formelle du **Gabarit d'Artefact**, des axiomes de l'**Ontologie**, des tests/linters et détection de **Pattern Drift**.
   - **Gate Agentique** : Évaluation critique par un **Agent Évaluateur** indépendant (soumis à l'**Orthogonalité des Modèles**), vérifiant la conformité sémantique, exécutant le **Contrôle Transverse d'Invariants**, et générant le **Briefing de Revue**.
   - **Gate Humaine** : Validation Go/No-Go (globale ou par découpage) ou co-édition par un **Profil Humain** habilité, gouvernée par une **Politique de Gate Adaptative** (`mandatory_full`, `risk_or_exception_based`, ou `sampling`).
6. **Politique de Gate Adaptative** : Règle de déclenchement d'une **Gate Humaine** permettant d'éviter la saturation et la validation aveugle (*Rubber-Stamping*) : revue obligatoire à 100% (`mandatory_full`), revue déclenchée uniquement sur seuil de risque/exception/dérive (`risk_or_exception_based`), ou audit par échantillonnage statistique (`sampling`).
7. **Orthogonalité des Modèles (Cross-Model Evaluation)** : Contrainte de sécurité imposant que l'**Agent Évaluateur** d'une **Gate Agentique** utilise un modèle/fournisseur distinct de l'**Agent Exécuteur** et opère dans un contexte isolé (sans accès au brouillon de raisonnement interne de l'exécuteur).
8. **Contrôle Transverse d'Invariants (Cross-Step Alignment)** : Vérification effectuée lors d'une **Gate** à l'étape $N$ confrontant directement l'**Artefact** produit aux **Artefacts** fondateurs de haut niveau (ex: Étape 1 Intention / Architecture / **Ontologie**) afin d'empêcher l'amplification des dérives d'une étape à l'autre.
9. **Pattern Drift (Dérive des Patterns)** : Risque d'augmentation non maîtrisée de la variabilité des motifs de conception ou de code au fil des **Workflow Runs**, dégradant la dette de compréhension globale et la **Réversibilité Humaine**, détecté par les **Gates Déterministes** et **Gates Agentiques**.
10. **Réversibilité Humaine** : Capacité opérationnelle pour l'organisation de suspendre l'exécution agentique à tout moment tout en conservant la pleine compréhension intellectuelle et la maintenabilité humaine des **Artefacts** et du code produits.
11. **Agent Assistant** : Agent IA conversationnel d'accueil par défaut d'ORCIA dans l'interface **Chat-First + Canvas**, adaptant son langage, son niveau de synthèse et ses actions au **Profil Humain** de son interlocuteur via l'**Ontologie**.
12. **Agent Exécuteur** : Agent IA spécialisé assigné à la réalisation d'un **Step** ou à l'orchestration d'un **Workflow Run**.
13. **Agent Évaluateur** : Agent IA indépendant mandaté par une **Gate Agentique** pour auditer un **Artefact** et produire le **Briefing de Revue**.
14. **Profil Humain** : Identité organisationnelle complète d'un utilisateur combinant sa position hiérarchique (Organisation / BU / Équipe), ses groupes transverses (Rôles métiers), ses **Workspaces** et ses habilitations effectives.
15. **Artefact** : Livrable structuré produit par un **Step**, stocké et versionné dans le **Blackboard**, pouvant comporter une vue décisionnelle destinée à l'humain et une vue structurée destinée aux agents aval.
16. **Gabarit d'Artefact (Artifact Template)** : Contrat formel (squelette Markdown Jinja/Mustache et/ou JSON/YAML Schema ancré sur l'**Ontologie**) définissant les **Ancrages Humains Obligatoires**, la structure multi-audience attendue d'un **Artefact** et son découpage pour la revue humaine.
17. **Briefing de Revue** : Synthèse cognitive générée pour accompagner l'humain sur un **Artefact** volumineux, comprenant obligatoirement : *Résumé*, *Éléments clés*, *Décisions prises*, et *Hypothèses retenues (Assumptions)*.
18. **Arbitrage Humain (Tie-Break)** : Obligation pour un **Agent Exécuteur** de suspendre son action et de solliciter l'humain dans l'interface **Chat-First + Canvas** dès qu'il rencontre plusieurs options équivalentes non tranchées par une **Base de Connaissances** ou l'**Ontologie**.
19. **Blackboard** : Espace d'état typé par l'**Ontologie** et propre à chaque **Workflow Run**, assurant le passage de contexte sélectif et filtré entre les **Steps**.
20. **Ontologie (Ontologie Dynamique Multi-Niveaux)** : Modèle sémantique vivant structuré en 4 strates avec héritage (*1. Entreprise*, *2. Domaine/BU*, *3. Équipe/Workspace*, *4. Éphémère/Run*), enrichi au fil des conversations et de l'analyse des sources avec promotion gouvernée, et assurant 3 rôles : typage du **Blackboard**/Gabarits, traduction par **Profil Humain**, et contrôle aux **Gates**/RAG.
21. **Catalogue Fédéré** : Registre gouverné d'ORCIA référençant les métadonnées, les droits d'accès et les URI versionnées (`db://`, `git://`, `nexus://`) des ressources (**Workflows**, **Agents**, **Skills**, **Gabarits d'Artefact**, **Ontologies**, **Bases de Connaissances**), résolues à la volée avec un cache local immuable (`SHA-256`).
22. **Provenance Auditable** : Enregistrement immuable pour chaque **Step** et **Gate** des URI/hashes exacts des ressources fédérées, du modèle, des paramètres, du prompt assemblé, des extraits de **Bases de Connaissances**, des coûts FinOps et des décisions humaines, garantissant le Replay déterministe du contexte.
23. **Skill** : Capacité modulaire mobilisable par un agent ou un **Step** (bundle Markdown + scripts, outil **MCP**, connecteur HTTP/OpenAPI, ou script exécuté en **Sandbox**).
24. **Base de Connaissances (KB / Contexte)** : Source documentaire ou structurée consultée via RAG/GraphRAG guidé par l'**Ontologie** pour assister l'orchestration ou l'exécution d'un **Step**.
25. **Permission Broker** : Mécanisme et assistant IA qui vérifie les habilitations (*Passthrough* utilisateur ou *Service Principal* de l'agent) et qui, en cas de droit manquant, interroge le référentiel des procédures d'accès de l'entreprise pour indiquer à l'humain la marche à suivre exacte.


---

## 4. Features

*Chaque sous-section décrit un domaine fonctionnel cohérent suivi de ses exigences fonctionnelles numérotées globalement (`FR-1` à `FR-27`) avec des conséquences testables et des références explicites aux User Journeys (`UJ-1` à `UJ-9`) et aux termes du Glossaire (§3).*

### 4.1 Expérience "Chat-First + Canvas", Agent Assistant Adaptatif & Centre de Notifications Multi-Runs

**Description :** L'accès par défaut à ORCIA s'effectue via une interface hybride **Chat-First + Canvas** où l'**Agent Assistant** adapte en permanence son discours, son niveau de synthèse et son vocabulaire au **Profil Humain** connecté grâce à l'**Ontologie**. L'utilisateur y gère son **Centre de Notifications** personnel et d'équipe et supervise simultanément plusieurs **Workflow Runs** dynamiques en distinguant ceux où il est simple observateur (*Consultation seule*) et ceux où son intervention est requise (*Contributeur / Valideur*). Réalise `UJ-1`, `UJ-4`, `UJ-8`.

**Functional Requirements :**

#### FR-1 : Interface par défaut Chat-First + Canvas, Sélecteur de Périmètre Hiérarchique (`⌘W`), Menu Global (7 Modules) et adaptation de l'Agent Assistant au Profil Humain
L'utilisateur authentifié accède par défaut à l'interface **Chat-First + Canvas** où l'**Agent Assistant** adapte automatiquement ses réponses, les indicateurs affichés et la terminologie au **Profil Humain** (Rôle, Business Unit, Équipe, Habilitations) en s'appuyant sur l'**Ontologie**, tout en disposant en en-tête de barre latérale d'un **Sélecteur de Périmètre Hiérarchique (`⌘W` : `🌐 Plateforme Globale → 🏢 BU / Tribu → 👥 Équipe → 🗂️ Workspace Solution Logicielle`)** et d'un **Menu de Navigation Global** filtré selon ses habilitations RBAC donnant accès aux 7 espaces fonctionnels d'ORCIA : (1) *Cockpit & Conversation*, (2) *Boîte de Réception, Runs & Centre de Pilotage Workspaces*, (3) *Catalogue Fédéré*, (4) *Ontologie & Connaissances (KB)*, (5) *Gouvernance, Gates & Habilitations*, (6) *FinOps, Audit & Réversibilité*, et (7) *Administration & Connecteurs*. Réalise `UJ-1`, `UJ-2`, `UJ-4`, `UJ-8`, `UJ-9`.

**Consequences (testable) :**
- Lorsqu'un utilisateur avec le rôle `Directrice BU` (`UJ-8`) interroge un **Workflow Run**, l'**Agent Assistant** restitue les KPIs budgétaires, le TTM et les risques métier en utilisant les termes de l'**Ontologie** de niveau *Entreprise/BU*.
- Lorsqu'un utilisateur avec le rôle `Tech Lead` (`UJ-3`, `UJ-5`) interroge le même **Workflow Run**, l'**Agent Assistant** restitue les détails techniques, les schémas d'API, les logs de **Sandbox** et les termes de l'**Ontologie** de niveau *Équipe / Workspace*.
- Le **Sélecteur de Périmètre Hiérarchique (`⌘W`)** et le **Menu de Navigation Global** permettent de basculer à tout moment vers n'importe lequel des 7 modules ou de filtrer l'application sur l'entreprise entière (`PLATFORM_ADMIN`), une BU/Tribu (`BU_DIRECTOR`), une équipe (`TEAM_LEAD`) ou un **Workspace** précis dans le **Canvas** principal tout en conservant l'**Agent Assistant** contextuel accessible à côté.

#### FR-2 : Centre de Notifications Unifié (Individuel & Équipe) avec Prise en Charge (Claim) et Présence Temps Réel
L'utilisateur peut consulter et traiter dans une boîte de réception unifiée toutes les notifications qui lui sont destinées personnellement ou qui sont adressées à son équipe/groupe transverse, couvrant 3 types d'interventions : validation d'un **Artefact** à une **Gate Humaine**, réponse à une question d'un agent IA (**Arbitrage Humain**), et réponse à une question/challenge d'un humain. Réalise `UJ-4`.

**Consequences (testable) :**
- Les notifications sont filtrables par portée (*À moi*, *À mon équipe*) et par type (*Artefact à valider*, *Question Agent IA*, *Question Humaine*, *Alerte Habilitation / Obsolescence*).
- Lorsqu'un membre d'une équipe ouvre ou prend en charge (*Claim*) une notification d'équipe, le système applique un verrou de présence temps réel (`< 500 ms` via WebSocket/SSE) affichant aux autres membres de l'équipe *"En cours de traitement par [Utilisateur]"* et empêchant les validations concurrentes contradictoires.

#### FR-3 : Centre de Pilotage Unifié Multi-Niveaux des Workspaces (*Runs, Sources, Agents/Workflows, Équipes*), Supervision Multi-Workflows et Séparation Consultation vs Contribution
L'utilisateur dispose d'un **Centre de Pilotage Unifié des Workspaces (`/workspaces` et `/workspaces/[workspaceId]`)** structuré en **4 onglets consolidés** (*1. Instances de `Workflow Runs` & Artefacts*, *2. Sources dédiées & partagées `N × git://`, `N × jira://`, `N × confluence://`, `db://`, `nexus://`*, *3. Workflows, Agents & Surcharges à 4 niveaux `Base → Team → Workspace → User`*, et *4. Équipes, Membres & Gouvernance*), qui s'adapte de manière fractale (*Roll-up* ascendant et *Drill-down* descendant) au périmètre sélectionné (`⌘W`) et au **Profil Humain** :
- **Niveau Global (`🌐 Plateforme Globale` — `PLATFORM_ADMIN`, `UJ-9`)** : consultation et administration de 100 % des BU, équipes, sous-équipes, Workspaces, sources, agents/workflows et instances de `Workflow Runs` de la plateforme (les métadonnées techniques et FinOps des Workspaces `CONFIDENTIAL_RESTRICTED` restent visibles pour l'exploitation, mais le contenu métier de leur *Blackboard* est masqué sauf habilitation explicite).
- **Niveau Organisation / BU (`🏢 Ma BU / Tribu` — `BU_DIRECTOR` `UJ-8` ou Lead d'Équipe Parente)** : vue consolidée (*Roll-up*) de toutes les équipes, sous-équipes et Workspaces de son organisation (supervision de tous les `Workflow Runs` en mode **Consultation seule `READ_ONLY_OBSERVER`** hors `CONFIDENTIAL_RESTRICTED`, cartographie des sources et alertes `[STALE_WARNING]`, gestion des agents/workflows `SHARED_BU` / `SHARED_TEAM` et des surcharges d'équipe).
- **Niveau Équipe (`👥 Mon Équipe` — `TEAM_LEAD`) & Niveau Solution (`🗂️ Workspace` — Contributeurs `UJ-1..7`, `UJ-10`)** : gestion complète des Workspaces solutions de l'équipe, de leurs multiples sources (`git://`, `jira://`, `confluence://`), de leurs agents/workflows et surcharges `WORKSPACE`, et pilotage des `Workflow Runs` selon deux modes stricts : **Consultation seule (`READ_ONLY_OBSERVER`)** ou **Contributeur / Valideur (`CONTRIBUTOR_ACTION_REQUIRED`)**. Réalise `UJ-1` à `UJ-10`.

**Consequences (testable) :**
- En mode *Consultation seule* (y compris en supervision *Roll-up* par un Directeur de BU ou un Lead d'équipe parente), l'utilisateur visualise l'état d'avancement des **Steps** et **Gates** ainsi que les **Briefings de Revue** autorisés par ses habilitations, mais toute action de modification d'**Artefact**, de réponse d'arbitrage ou de passage de **Gate** est désactivée côté UI et rejetée avec `HTTP 403` côté API.
- Depuis les 4 onglets du **Centre de Pilotage Unifié (`/workspaces`)**, un `PLATFORM_ADMIN` (à l'échelle globale), un `BU_DIRECTOR` (à l'échelle de sa BU) ou un `TEAM_LEAD` (à l'échelle de son équipe et de ses Workspaces) peut filtrer, inspecter et gérer au même endroit les instances de **Workflow Runs**, les **Sources (`git://`, `jira://`, `confluence://`)**, les **Agents/Workflows (et leurs surcharges)** et les **Équipes/Membres** de son périmètre, et basculer en `< 1 s` dans le **Cockpit** d'un Run.

---

### 4.2 Posture "Human-Led", Ergonomie Cognitive & Boucles de Rétroaction Inter-Steps

**Description :** Pour préserver la responsabilité intellectuelle des experts humains ("maintenir le *Think* au bon niveau") et éviter le biais d'ancrage cognitif, ORCIA impose des **Ancrages Humains Obligatoires** en amont de la génération IA, interdit tout choix arbitraire silencieux en cas d'options équivalentes (**Arbitrage Humain**), outille la revue des **Artefacts** volumineux (**Briefing de Revue** et **Validation par Découpage**), et permet aux acteurs aval de challenger et faire évoluer les **Artefacts** amont. Réalise `UJ-1`, `UJ-2`, `UJ-3`, `UJ-5`, `UJ-6`.

**Functional Requirements :**

#### FR-4 : Ancrages Humains Obligatoires (Human-Led Anchors) anti-biais d'ancrage
Le concepteur d'un **Workflow** ou d'un **Gabarit d'Artefact** peut marquer certaines sections ou décisions critiques comme `human_authored_required: true` (ex: *Intention métier*, *Risque à ne pas faire*, *Découpage tactique*, *Principes d'architecture*) que l'agent IA a l'interdiction formelle de pré-remplir. Réalise `UJ-1`, `UJ-2`, `UJ-5`.

**Consequences (testable) :**
- Tant que les champs `human_authored_required: true` d'un **Step** ne sont pas rédigés et soumis par un humain habilité, l'**Agent Exécuteur** ne peut pas générer l'**Artefact** complet.
- Si l'utilisateur demande à l'agent de remplir le champ à sa place, l'agent refuse poliment et passe en mode questionnement socratique pour aider l'humain à formuler sa propre décision.
- La **Provenance Auditable** distingue explicitement les sections rédigées par l'humain des sections générées ou co-éditées avec l'IA.

#### FR-5 : Arbitrage Humain Systématique sur Options Équivalentes (No Silent Arbitrary Choice)
Lorsqu'un **Agent Exécuteur** rencontre au cours d'un **Step** au moins deux options techniques, fonctionnelles ou métier équivalentes qui ne sont pas départagées par l'**Ontologie**, la **Base de Connaissances** ou les **Ancrages Humains Obligatoires**, il suspend son exécution et sollicite un **Arbitrage Humain**. Réalise `UJ-1`, `UJ-3`, `UJ-4`, `UJ-5`.

**Consequences (testable) :**
- Le **Workflow Run** passe à l'état `WAITING_FOR_HUMAN_ARBITRATION` et émet une notification dans le **Centre de Notifications** (`FR-2`).
- L'agent présente dans le chat et le **Canvas** une matrice structurée des options équivalentes (description, avantages, inconvénients, impacts SI/FinOps, recommandation éventuelle).
- Le choix de l'humain est enregistré dans le **Blackboard** et dans la **Provenance Auditable**, et débloque immédiatement la suite du **Step**.

#### FR-6 : Briefing de Revue et Validation par Découpage pour les Artefacts volumineux
Lorsqu'un **Artefact** produit par un **Step** dépasse un seuil de taille configurable `[ASSUMPTION: > 1 500 mots ou > 3 sections de Gabarit]` ou est soumis à une **Gate Humaine**, le système présente automatiquement un **Briefing de Revue** et un mode de **Validation par Découpage** dans le **Canvas**. Réalise `UJ-1`, `UJ-2`, `UJ-4`, `UJ-6`.

**Consequences (testable) :**
- Le **Briefing de Revue** affiche obligatoirement 4 blocs distincts : *1. Résumé exécutif*, *2. Éléments clés*, *3. Décisions prises par l'agent*, et *4. Hypothèses retenues (Assumptions)*.
- Le mode **Validation par Découpage** segmente l'**Artefact** selon les sections de son **Gabarit d'Artefact** ; l'utilisateur peut approuver, commenter, co-éditer ou demander la régénération d'une section individuelle sans régénérer les sections déjà validées.

#### FR-7 : Challenge & Boucle de Rétroaction Inter-Steps avec Simulation d'Impact (Upstream Challenge, What-If Impact Preview & Rewind Loop)
Tout contributeur d'un **Step** aval (ex: Architecte au **Step** 2 dans `UJ-2`, ou Tech Lead au **Step** 3 dans `UJ-3`) peut émettre un challenge formel vers un **Step** amont (ex: PM au **Step** 1) lorsqu'une règle métier ou une spécification s'avère trop complexe, incohérente ou incompatible avec le SI ou une API partenaire, avec prévisualisation immédiate du graphe d'impact (*What-If*). Réalise `UJ-2`, `UJ-3`, `UJ-4`.

**Consequences (testable) :**
- L'acteur aval sélectionne la règle ou section de l'**Artefact** amont concernée et déclenche l'action *Challenger / Demander révision amont*.
- Le système calcule et affiche un **Aperçu de Simulation d'Impact (*What-If Impact Preview*)** listant exactement quels **Steps** aval, quelles sections d'**Artefacts** du **Blackboard** et quels axiomes de l'**Ontologie** seront invalidés ou devront être rejoués si la modification est acceptée, tandis que l'agent traduit l'impact technique/SI dans le vocabulaire du **Profil Humain** amont via l'**Ontologie** et crée une notification de type *Question/Challenge Humain* (`FR-2`).
- Après arbitrage (ex: révision de la règle métier dans le `PRD` ou demande d'évolution à un partenaire externe avec mise en pause du run), le **Blackboard** crée une nouvelle révision versionnée de l'**Artefact** amont (`v1.1`) et déclenche un **Replay** ciblé (`FR-16`) des seuls **Steps** aval impactés.

---

### 4.3 Ontologie Dynamique Multi-Niveaux

**Description :** L'**Ontologie** constitue la colonne vertébrale sémantique d'ORCIA. Structurée en 4 strates avec héritage, elle s'enrichit au fil des conversations et de l'analyse documentaire avec un mécanisme de promotion gouvernée, et agit simultanément sur le typage du **Blackboard**/Gabarits, la traduction par **Profil Humain** et le contrôle aux **Gates**/RAG. Réalise `UJ-1`, `UJ-2`, `UJ-5`, `UJ-8`.

**Functional Requirements :**

#### FR-8 : Structuration de l'Ontologie en 4 Niveaux (incluant Arbre d'Équipes & Espace Solution Workspace) avec Héritage et Alignement
Le système gère une **Ontologie** hiérarchisée en 4 niveaux : *Niveau 1 (Socle Entreprise)* $\rightarrow$ *Niveau 2 (Domaine / BU)* $\rightarrow$ *Niveau 3 (Niveau 3A : Équipe hiérarchique `Équipe Parente -> Sous-Équipe` commun à toutes les solutions de l'équipe $\rightarrow$ Niveau 3B : `Workspace` propre à une solution logicielle donnée)* $\rightarrow$ *Niveau 4 (Éphémère / Workflow Run)*, avec héritage des concepts, axiomes et correspondances terminologiques inter-niveaux. Réalise `UJ-1`, `UJ-2`, `UJ-5`, `UJ-8`.

**Consequences (testable) :**
- Un concept défini au *Niveau 1 (Entreprise)* ou au niveau d'une *Équipe parente (`3_TEAM`)* est automatiquement hérité par ses sous-équipes, par tous les *Workspaces (solutions logicielles)* de l'équipe et au *Niveau 4 (Run)*, et peut être spécialisé ou mappé à un synonyme local (ex: `"Actif Stratégique"` au Niveau 1 $\leftrightarrow$ `"Microservice Tier-1"` au Niveau 3 IT) sans contredire ses axiomes parents.
- Les définitions d'**Ontologie** des niveaux 1 à 3 sont versionnées et résolues via le **Catalogue Fédéré** (`db://`, `git://`, `nexus://`).

#### FR-9 : Extraction Ontologique en Temps Réel, Simulation d'Impact et Promotion Gouvernée
Au cours de la conversation avec l'humain ou de l'analyse des **Bases de Connaissances**, le système détecte les nouveaux concepts, synonymes, règles ou conflits sémantiques, les inscrit immédiatement au *Niveau 4 (Run)* et propose leur promotion gouvernée vers les niveaux supérieurs après simulation d'impact (*What-If*). Réalise `UJ-3`, `UJ-5`.

**Consequences (testable) :**
- Lorsqu'un terme métier inédit ou une ambiguïté est résolu en cours de **Workflow Run**, l'agent crée une entrée dans l'**Ontologie** *Run (Niveau 4)* et affiche une carte de proposition de promotion vers le *Niveau 3 (`3_WORKSPACE` de la solution ou `3_TEAM` de l'équipe)* ou *Niveau 2/1*.
- Avant toute promotion ou modification d'un concept/axiome aux *Niveaux 3, 2 ou 1*, le système exécute une **Simulation d'Impact Ontologique** identifiant tous les **Gabarits d'Artefact**, **Workflows** du **Catalogue Fédéré** et **Workflow Runs** actifs qui référencent ce concept.
- La promotion au *Niveau 3* est validée par le responsable d'équipe (`TEAM_LEAD` / Tech Lead / PM) ; la promotion aux *Niveaux 2 et 1* requiert une **Gate Humaine** de gouvernance dédiée.

#### FR-10 : Triple Exécution Active de l'Ontologie (Typage Blackboard/Gabarits, Traduction Profil, Contrôle Gates/RAG)
Lors de chaque **Workflow Run**, le moteur applique l'**Ontologie** active sur trois plans : (1) validation du typage des objets du **Blackboard** et des **Gabarits d'Artefact**, (2) traduction du vocabulaire par l'**Agent Assistant** selon le **Profil Humain**, et (3) expansion des requêtes RAG et vérification des axiomes lors des **Gates Déterministes** et **Gates Agentiques**. Réalise `UJ-1`, `UJ-2`, `UJ-6`, `UJ-8`.

**Consequences (testable) :**
- Si un **Artefact** produit viole un axiome ou utilise un terme banni/ambigu de l'**Ontologie** active, la **Gate Déterministe** ou **Gate Agentique** signale l'écart exact (concept, règle violée, ligne concernée) et bloque le passage.

---

### 4.4 Modélisation des Workflows, Gabarits d'Artefact Multi-Audience & Discipline `Intention -> Code`

**Description :** Les processus sont définis de manière déclarative (**Workflow-as-Code** en MVP) et s'appuient sur des **Gabarits d'Artefact** multi-audience (vue humaine vs vue agentique) en imposant la discipline du cycle `Intention -> Code`. Réalise `UJ-1`, `UJ-2`, `UJ-5`.

**Functional Requirements :**

#### FR-11 : Définition Déclarative Workflow-as-Code (YAML/JSON) et Composition Assistée par l'Agent Assistant
Les concepteurs peuvent définir un **Workflow** via un fichier déclaratif YAML/JSON validé par schéma, ou demander à l'**Agent Assistant** de composer et ajuster conversationnellement un manifeste **Workflow-as-Code** en assemblant les briques existantes du **Catalogue Fédéré** (**Steps**, **Agents Exécuteurs**, **Skills**, **Bases de Connaissances**, **Gabarits d'Artefact**, **Ancrages Humains Obligatoires**, **Gates** et routes de rétroaction) avant de l'enregistrer dans le **Workspace** et de l'exécuter (en mode interactif ou en tâche de fond). Réalise `UJ-1`, `UJ-5`, `UJ-9`, `UJ-10`.

**Consequences (testable) :**
- Toute définition YAML/JSON (écrite manuellement ou proposée/modifiée par l'**Agent Assistant**) invalide (référence d'URI manquante, cycle non borné sans condition de sortie, schéma de gate incomplet) est rejetée à l'enregistrement avec un rapport d'erreurs précis (ligne et règle).
- Lorsqu'un utilisateur demande à l'**Agent Assistant** (`UJ-10`) de proposer puis de modifier un **Workflow** (ex: audit Documentation vs Codebase), l'**Agent Assistant** affiche l'aperçu du graphe et le manifeste YAML mis à jour dans le **Canvas**, permet son enregistrement en portée `DRAFT` / `WORKSPACE` et son lancement asynchrone en tâche de fond.

#### FR-12 : Gabarits d'Artefact Multi-Audience (Humain vs Agent)
Chaque **Step** peut référencer un **Gabarit d'Artefact** combinant une structure Markdown (avec variables Jinja/Mustache et sections obligatoires pour la revue humaine et le découpage `FR-6`) et/ou un schéma formel (JSON Schema / YAML Schema typé par l'**Ontologie** pour la consommation par les **Steps** aval). Réalise `UJ-1`, `UJ-2`, `UJ-5`, `UJ-6`.

**Consequences (testable) :**
- L'**Artefact** généré expose à l'humain la vue documentaire lisible dans le **Canvas** tout en sérialisant dans le **Blackboard** les données structurées validées contre le JSON/YAML Schema pour le **Step** suivant.

#### FR-13 : Garantie de la Discipline `Intention -> Code`
Dans tout **Workflow** d'ingénierie logicielle en régime nominal, le moteur impose que toute modification du code source soit précédée d'une déclaration d'intention ou de la mise à jour validée de l'**Artefact** de spécification/architecture amont, suivie d'une **Gate** vérifiant le maintien en conformité entre la documentation produit et le codebase. Réalise `UJ-1`, `UJ-2`, `UJ-3`, `UJ-5`.

**Consequences (testable) :**
- Les **Workflows** de rétro-documentation (`Code -> Doc`) sont explicitement typés `mode: brownfield_bootstrap` et ne peuvent pas s'exécuter en chaîne continue sur les commits courants sans validation humaine d'intention, empêchant qu'un bug de code ne soit automatiquement documenté comme une fonctionnalité.

---

### 4.5 Moteur d'Orchestration, Blackboard, Version Pinning & Replay

**Description :** Le moteur d'orchestration exécute les **Workflow Runs** en mode Hybride (*Human-Led & Agent-Accelerated*), route les appels vers des LLMs Cloud ou Locaux, gère l'état partagé via le **Blackboard**, épingle de façon immuable les versions des ressources et permet le **Replay** partiel. Réalise `UJ-3`, `UJ-5`, `UJ-7`.

**Functional Requirements :**

#### FR-14 : Orchestration Hybride Multi-LLM Agnostique et Blackboard Filtré
Le moteur orchestre l'exécution séquentielle, parallèle ou conditionnelle des **Steps**, abstrait les fournisseurs de modèles (OpenAI, Anthropic, Google Gemini, Ollama, vLLM) et n'injecte dans le contexte de chaque **Step** que le sous-ensemble d'**Artefacts** du **Blackboard** explicitement déclaré en entrée de ce **Step**. Réalise `UJ-1`, `UJ-2`, `UJ-5`.

**Consequences (testable) :**
- Changer le modèle d'un **Agent Exécuteur** d'un fournisseur Cloud vers un modèle local Ollama/vLLM s'effectue uniquement par configuration sans modifier le code du **Workflow**.
- Un **Step** $N$ ne reçoit jamais dans son prompt les **Artefacts** des **Steps** $1..N-1$ qui ne figurent pas dans sa liste `inputs` déclarée (optimisation FinOps et confidentialité).

#### FR-15 : Version Pinning Immuable des Workflow Runs en cours
Au démarrage d'un **Workflow Run**, le moteur fige dans un manifeste de verrouillage (`run-lock.json`) les versions exactes et les empreintes cryptographiques `SHA-256` du **Workflow**, des **Agents**, des **Skills**, des **Gabarits d'Artefact** et de l'**Ontologie** résolus depuis `db://`, `git://` ou `nexus://`. Réalise `UJ-3`, `UJ-7`, `UJ-9`.

**Consequences (testable) :**
- Si un **Workflow Run** reste en pause pendant 10 jours sur une **Gate Humaine** ou en attente d'un partenaire externe (`UJ-3`) et qu'une nouvelle version du **Workflow** ou d'un **Agent** est publiée entre-temps, la reprise du **Workflow Run** utilise strictement les versions `SHA-256` figées dans son `run-lock.json` via le cache local immuable.

#### FR-16 : Replay Ciblé à partir du Step $N$ (Time-Travel Execution)
Un utilisateur habilité peut relancer un **Workflow Run** à partir d'un **Step** $N$ spécifique (en réutilisant l'état du **Blackboard** figé à la fin du **Step** $N-1$) suite à une résolution d'habilitation (`UJ-7`), à un ajustement d'**Artefact** amont (`UJ-2`, `UJ-3`) ou pour tester un paramètre/modèle alternatif. Réalise `UJ-2`, `UJ-3`, `UJ-7`.

**Consequences (testable) :**
- Lors d'un **Replay** à partir du **Step** 3, les **Steps** 1 et 2 ne sont pas ré-exécutés (0 token consommé sur les étapes 1 et 2), et le **Blackboard** crée une nouvelle branche/révision d'exécution traçant l'origine du **Replay**.

---

### 4.6 Système de Gates Multi-Critères, Orthogonalité des Modèles, Contrôles Transverses & Anti-Pattern Drift

**Description :** Entre deux **Steps**, ORCIA permet de chaîner plusieurs **Gates** (Déterministes, Agentiques et Humaines) avec des garanties actives de fiabilisation : exécution de scripts en **Sandbox**, **Orthogonalité des Modèles** (modèle relecteur $\neq$ modèle exécuteur), **Contrôle Transverse d'Invariants** contre l'effet téléphone arabe, détection de **Pattern Drift**, et **Politique de Gate Adaptative** anti-*Rubber-Stamping*. Réalise `UJ-2`, `UJ-3`, `UJ-6`, `UJ-8`.

**Functional Requirements :**

#### FR-17 : Gates Déterministes (Sandbox, Conformité Gabarit/Ontologie & Détection de Pattern Drift)
Une **Gate Déterministe** exécute de manière automatisée et reproductible : (1) la validation du schéma du **Gabarit d'Artefact** et des règles formelles de l'**Ontologie**, (2) des scripts de vérification, compilateurs, linters ou suites de tests en **Sandbox**, et (3) des règles d'analyse statique détectant le **Pattern Drift** (introduction de motifs ou dépendances non standards). Réalise `UJ-5`, `UJ-6`.

**Consequences (testable) :**
- Un code retour non nul (`exit code != 0`) ou une violation de schéma bloque immédiatement la transition vers le **Step** suivant ou la **Gate Humaine**, et renvoie le rapport d'erreur structuré.

#### FR-18 : Gates Agentiques avec Orthogonalité des Modèles, Vérification Atomique de Faits et Contrôle Transverse d'Invariants
Une **Gate Agentique** mandate un **Agent Évaluateur** indépendant (structuré en DAG de lentilles parallèles) pour auditer l'**Artefact** produit, décomposer et vérifier ses assertions factuelles contre les **Bases de Connaissances** et l'**Ontologie** (*Lentille `fact_verification`*), réaliser un **Contrôle Transverse d'Invariants** vis-à-vis des **Artefacts** fondateurs de haut niveau (ex: `PRD` du **Step** 1, Architecture du **Step** 2), et générer le **Briefing de Revue** (`FR-6`). Réalise `UJ-2`, `UJ-3`, `UJ-6`, `UJ-10`.

**Consequences (testable) :**
- **Application de l'Orthogonalité des Modèles** : le moteur vérifie par configuration que l'**Agent Évaluateur** utilise un modèle/fournisseur différent de l'**Agent Exécuteur** (ou lève une erreur de configuration si la contrainte `enforce_distinct_evaluator_model: true` est violée) et ne lui transmet jamais l'historique de raisonnement interne (*Chain-of-Thought* / brouillon) de l'**Agent Exécuteur**.
- **Vérification Atomique de Faits (`fact_verification`)** : la lentille décompose l'**Artefact** en assertions individuelles, confronte chacune à l'**Ontologie** et aux sources épinglées avec un score de confiance (`0..1`), et marque ou bloque toute affirmation non étayée sous le seuil configuré.
- **Contrôle Transverse d'Invariants** : même si le code du **Step** 4 est fidèle à la Story du **Step** 3, la **Gate Agentique** bloque ou alerte s'il contredit une exigence ou règle métier du `PRD` validé au **Step** 1.

#### FR-19 : Gates Humaines à Politique Adaptative et Garde-fou Anti-Rubber-Stamping
Chaque **Gate Humaine** est configurée selon une **Politique de Gate Adaptative** (`mandatory_full`, `risk_or_exception_based`, ou `sampling` à $X\%$) et intègre un mécanisme de protection contre la validation aveugle (*Rubber-Stamping*). Réalise `UJ-4`, `UJ-6`, `UJ-8`.

**Consequences (testable) :**
- En mode `risk_or_exception_based`, la **Gate Humaine** est automatiquement franchie si et seulement si la **Gate Déterministe** et la **Gate Agentique** précédentes retournent un score de risque inférieur au seuil défini et 0 anomalie de **Pattern Drift** ; dans le cas contraire, elle bloque et notifie le **Profil Humain** habilité.
- Si un valideur humain clique sur *Approuver* sur un **Artefact** volumineux en moins d'un temps minimal configurable `[ASSUMPTION: < 15 secondes]` sans avoir consulté le **Briefing de Revue** ni les sections découpées, l'interface demande une confirmation active (*"Confirmez-vous avoir vérifié les X hypothèses retenues ?"*) et incrémente le compteur de contre-métrique *Rubber-Stamping* (`SM-C1`).

---

### 4.7 Catalogue Fédéré (`db://`, `git://`, `nexus://`, `confluence://`, `jira://`), Hiérarchie d'Équipes, Workspaces Multi-Sources & Permission Broker

**Description :** ORCIA modélise fidèlement les organisations complexes en découplant l'**arbre hiérarchique d'équipes** (`Entreprise -> BU -> Tribu/Équipe Parente -> Sous-Équipe`) des **Workspaces de solutions logicielles** (permettant à une même équipe de maintenir plusieurs solutions logicielles isolées, et à **chaque Workspace de regrouper plusieurs dépôts `git://`, plusieurs projets `jira://` et plusieurs espaces `confluence://` dédiés** à cette solution), fédère à la volée les ressources sans duplication avec 4 strates de surcharge déclarative (`Base -> Équipe -> Workspace -> Utilisateur`), applique 5 permissions dissociées et accompagne les utilisateurs via le **Permission Broker**. Réalise `UJ-1` à `UJ-10`.

**Functional Requirements :**

#### FR-20 : Résolution à la Volée du Catalogue Fédéré (`db://`, `git://`, `nexus://`, `confluence://`, `jira://`), Surcharges à 4 Niveaux (`Base → Team → Workspace → User`) et Cache Local `SHA-256`
Le **Catalogue Fédéré** stocke uniquement les métadonnées, la gouvernance RBAC/ABAC et l'URI versionnée des ressources (**Workflows**, **Agents**, **Skills**, **Gabarits d'Artefact**, **Ontologies**, **Bases de Connaissances**), résout leur contenu à la volée depuis la DB d'ORCIA (`db://`), les dépôts Git (`git://`), les registres Nexus/Artifactory (`nexus://` bundles `.tar.gz`/`.zip`/OCI), les espaces **Confluence (`confluence://<space_key>/<page_id>@v<N>`)** ou les projets/tickets **Jira (`jira://<project_key>/<issue_key>`)** dans un cache local content-addressable (`SHA-256`), et applique une résolution de surcharge déclarative à **4 niveaux** : **`1. Définition de Base (Catalogue) → 2. Standards d'Équipe (`TEAM` hiérarchique) → 3. Configuration de la Solution (`WORKSPACE`) → 4. Préférences `USER`**. Réalise `UJ-1`, `UJ-3`, `UJ-5`, `UJ-7`, `UJ-9`, `UJ-10`.

**Consequences (testable) :**
- Lors de l'exécution d'un **Step** référençant `nexus://.../security-skill@2.1.0.tar.gz`, une ou plusieurs pages `confluence://...` ou des tickets/filtres `jira://...`, le moteur vérifie si le hash `SHA-256` (ou la révision exacte de chaque source) est présent dans le cache local ; sinon il télécharge le contenu, vérifie son intégrité cryptographique, l'extrait en cache immuable et l'exécute.
- Une équipe travaillant sur 3 solutions logicielles définit ses standards communs une seule fois au niveau **`2. TEAM`** (hérités automatiquement par ses sous-équipes et ses 3 Workspaces), puis surcharge au niveau **`3. WORKSPACE`** la liste des dépôts `git://` (`1..N`), des projets `jira://` (`1..N`) et des espaces `confluence://` (`1..N`) dédiés à chaque solution (qualifiés par alias/rôle logique, ex. `git:backend`, `git:frontend`, `jira:product`, `jira:secops`, `confluence:specs`, `confluence:architecture`).

#### FR-21 : Authentification Hybride (SSO OIDC & Locale), Hiérarchie d'Équipes (`OrgUnit`) découplée des Espaces Solutions Multi-Sources (`Workspaces`), Rôle `TEAM_LEAD` et 5 Permissions Dissociées du Catalogue
Le système authentifie les utilisateurs selon un modèle hybride bi-mode (**SSO d'Entreprise `OIDC / OAuth 2.1`** ET **Authentification Locale autonome `Email + Argon2id + MFA TOTP optionnel`** avec liens d'invitation signés, sur sessions JWT `15 min` + Refresh Token `HttpOnly` révocable en Redis), structure l'organisation selon trois axes combinables :
1. **Arbre Hiérarchique d'Unités Organisationnelles & d'Équipes (`org_units` à $N$ niveaux : `Entreprise -> BU -> Département/Tribu/Équipe Parente -> Sous-Équipe/Squad`)** portant les membres, leur **Chef d'Équipe (`TEAM_LEAD`)**, leurs standards `TEAM` et leurs actifs partagés ;
2. **Groupes transverses / Rôles métiers** (ex. Guilde Architectes, SecOps) ;
3. **Espaces Solutions (`Workspaces`)** : conteneurs opérationnels représentant chacun **une solution logicielle ou un produit** pouvant agréger **plusieurs dépôts `git://` dédiés** (ex. API backend, web frontend, contrats OpenAPI, IaC), **plusieurs projets/boards `jira://` dédiés** (ex. backlog produit, projet sécurité/ops) et **plusieurs espaces/arborescences `confluence://` dédiés** (ex. spécifications fonctionnelles, ADR d'architecture, runbooks), ainsi que ses schémas `db://`, son `ARCHITECTURE-SPINE.md`, ses **Workflow Runs** et ses **Artefacts**, où **une même Équipe peut posséder et travailler sur plusieurs Workspaces** et inviter une équipe partenaire sur un Workspace donné sans lui exposer ses autres Workspaces.
Sur chaque ressource du **Catalogue Fédéré**, le système dissocie 5 permissions (`DISCOVER`, `EXECUTE`, `READ_SOURCE`, `EDIT`, `ADMIN`) à travers un cycle de publication hiérarchique (`DRAFT` $\rightarrow$ `SHARED_WORKSPACE` $\rightarrow$ `SHARED_TEAM` $\rightarrow$ `SHARED_BU` $\rightarrow$ `PENDING_APPROVAL` $\rightarrow$ `PUBLISHED_ORG`). Réalise `UJ-4`, `UJ-5`, `UJ-8`, `UJ-9`.

**Consequences (testable) :**
- **Isolation par Solution (`Workspace`) & Supervision Hiérarchique Ascendante (*Roll-up*)** : Toutes les sources dédiées (`N x git://`, `N x jira://`, `N x confluence://`), les artefacts et le *Blackboard* d'un `Workspace A` (ex. *Solution Paiement*) sont strictement isolés du `Workspace B` (ex. *Solution Fidélité*) de la même équipe ; le responsable d'une **Équipe Parente / Tribu / BU** dispose par héritage ascendant d'une visibilité en **Consultation seule (`READ_ONLY_OBSERVER`)** et d'une consolidation FinOps sur les Workspaces de ses sous-équipes filles (sauf si un Workspace est marqué `CONFIDENTIAL_RESTRICTED`).
- **Héritage Descendant du Catalogue** : Un **Agent**, **Skill** ou **Workflow** publié en `SHARED_TEAM` ou `SHARED_BU` par une équipe parente est automatiquement découvrable (`DISCOVER`) et exécutable (`EXECUTE`) par toutes ses sous-équipes filles et dans tous les Workspaces de l'équipe ; s'il est publié sans `READ_SOURCE`, toute tentative d'afficher son prompt système ou ses scripts sources retourne `HTTP 403`.
- Un **Chef d'Équipe (`TEAM_LEAD`)** peut, en autonomie, créer des sous-équipes, créer et configurer plusieurs **Workspaces** (solutions logicielles) pour son équipe, rattacher à chaque Workspace autant de dépôts `git://`, projets `jira://` et espaces `confluence://` que nécessaire, inviter ses membres en leur attribuant leur **Profil Humain** et leurs rôles d'exécution, et déléguer temporairement ses validations de **Gates** lors d'une absence.

#### FR-22 : Modèle d'Habilitation à l'Exécution (Passthrough / Service Principal) et Permission Broker IA connecté à Jira
Lors d'un **Workflow Run**, chaque accès à une ressource, une **Base de Connaissances** (y compris les restrictions de pages sur chacun des espaces Confluence et les droits de projet/transition sur chacun des projets Jira du Workspace) ou un **Skill**/**MCP** s'exécute par défaut avec les habilitations de l'utilisateur déclencheur (*Passthrough* via liaison OAuth 2.0 `3LO` ou jeton `PAT` chiffré AES-256-GCM dans le coffre d'identité de l'utilisateur) ou via un *Service Principal* explicitement configuré ; en cas de refus d'accès, le **Permission Broker** interroge la **Base de Connaissances** des procédures d'habilitation de l'entreprise et guide l'humain (avec pré-remplissage du ticket de demande d'accès dans **Jira**). Réalise `UJ-7`.

**Consequences (testable) :**
- En cas d'erreur d'autorisation (`HTTP 401/403`, y compris lorsqu'un agent tente une lecture ou transition sur l'un des dépôts Git, espaces Confluence ou projets Jira du Workspace pour lequel l'utilisateur n'est pas habilité), le **Permission Broker** retourne dans le chat et la notification : (1) la source exacte (`git://`, `confluence://` ou `jira://`) et le rôle manquant, (2) la procédure ou le lien pré-rempli de création de ticket d'habilitation dans **Jira**, et (3) le responsable approbateur identifié, en mettant le **Step** en pause prête pour un **Replay** (`FR-16`).

---

### 4.8 Bases de Connaissances (Graphe Tripartite Multi-Sources Confluence ↔ Jira ↔ Git), Actions Jira Gouvernées, Skills, MCP Bidirectionnel & Sandbox

**Description :** Les agents et les **Steps** s'appuient sur des **Bases de Connaissances** pré-indexées de manière différenciée à l'échelle de chaque **Workspace** (fédérant ses **multiples espaces `confluence://`** et **multiples projets `jira://`** en découpage *Parent-Child*, et ses **multiples dépôts `git://`** en découpage syntaxique *AST + Graphe de Code*, tous reliés au sein d'un **Graphe Tripartite Multi-Sources `Confluence (1..N) ↔ Jira (1..N) ↔ Git (1..N)`**), interrogent et pilotent les workflows **Jira** (requêtes JQL multi-projets temps réel, création, modification et transitions de tickets stagées par les **Gates** avec routage vers le projet Jira cible + Webhooks bidirectionnels), exécutent des **Skills** en **Sandbox** isolée et opèrent via **MCP bidirectionnel**. Réalise `UJ-1` à `UJ-10`.

**Functional Requirements :**

#### FR-23 : Indexation Différenciée Multi-Sources (N × Confluence/Doc & N × Projets Jira en Parent-Child, N × Dépôts Code AST+Graphe, Schéma DB), Graphe Tripartite Unifié (`Confluence ↔ Jira ↔ Git`), Contrôle `data-freshness` et Alerte d'Obsolescence
Le système indexe de manière incrémentale (par delta `SHA-256` sur chaque dépôt Git, `page_version` sur chaque espace Confluence ou webhook `jira:issue_updated` sur chaque projet Jira rattaché au Workspace) et selon 3 régimes adaptés : (1) les **Bases de Connaissances** documentaires et tickets structurants (**multiples espaces Confluence `confluence://`** filtrés par espace/labels et **multiples projets Jira `jira://`** filtrés par JQL sur les Epics, Stories, Bugs et Post-mortems, ainsi que Markdown, PDF, OpenAPI) en découpage hiérarchique *Parent-Child* (`256-512` tokens indexés avec en-tête contextuel $\rightarrow$ `1024-2048` tokens injectés), (2) les **multiples Codebases (`git://`)** du Workspace en découpage syntaxique par symbole AST (`150-800` tokens) couplé à un *Code Knowledge Graph* inter-dépôts (`CALLS`, `IMPORTS`, `TESTED_BY`), et (3) uniquement le **schéma DDL** (0 ligne transactionnelle) pour `db://`, tous normalisés en vecteurs `halfvec(1024)` et reliés au sein d'un **Graphe Tripartite Multi-Sources `Confluence (DOCUMENTS) ↔ Jira (SPECIFIES / FIXES) ↔ Git (IMPLEMENTS_ISSUE)`** à l'échelle du Workspace. Il expose en outre la brique `data-freshness` et lève une **Alerte d'Obsolescence Documentaire (`STALE_WARNING`)** dès qu'une page Confluence/doc dépasse son `freshness_ttl_days` ou est contredite par un ticket Jira plus récent ou par l'un des dépôts de code du Workspace (`UJ-3`, `UJ-10`). Réalise `UJ-1`, `UJ-2`, `UJ-3`, `UJ-5`, `UJ-10`.

**Consequences (testable) :**
- L'enrôlement de plusieurs espaces **Confluence**, de plusieurs projets **Jira** et de plusieurs dépôts **Git** dans un même **Workspace** via `init-datasource` permet de qualifier chaque source par un alias/rôle logique, respecte les restrictions de lecture en mode *Passthrough* source par source, et extrait automatiquement les liens croisés entre tous les espaces Confluence, toutes les clés de tickets des différents projets Jira (`PAY-123`, `SEC-45`) et les commits/PRs des différents dépôts Git du Workspace.
- Lors d'un audit `UJ-10` (mono-dépôt ou multi-dépôts au sein du Workspace), si le code d'un dépôt diffère d'une page Confluence mais correspond à une évolution validée dans un ticket Jira lié plus récent, l'agent identifie la divergence comme `[DOC_OBSOLETE_SUSPECTED]` en citant le ticket Jira justificatif.
- Lorsqu'une **Alerte d'Obsolescence Documentaire** est déclenchée (`UJ-3`, `UJ-10`), le document est marqué `STALE_WARNING`, les **Workflow Runs** actifs dépendants sont signalés pour arbitrage (`FR-7`), et sa mise à jour permet un **Replay** ciblé (`FR-16`).

#### FR-24 : Actions & Transitions de Workflows Jira Gouvernées (Multi-Projets), Exécution des Skills (Sandbox Isolée) et Protocole MCP Bidirectionnel (Client & Serveur IDE)
Un **Step** ou une **Gate** peut : (1) interroger en temps réel via JQL l'ensemble des projets **Jira** rattachés au Workspace, préparer en brouillon (*Staged Action* soumise aux **Gates** en ciblant le projet Jira approprié par alias/composant ou le projet par défaut du Workspace) et exécuter la création de tickets (`create_issue`), la modification/commentaire (`update_issue`, `add_comment` avec lien de **Provenance Auditable**) et l'avancement des workflows **Jira** (`transition_issue` après vérification des transitions légales `GET /transitions` du projet cible), tout en recevant les Webhooks **Jira** (`jira:issue_updated`) de tous les projets liés pour déclencher ou réveiller un **Workflow Run** en pause (`UJ-3`) ; (2) invoquer des **Skills** (bundles Markdown+Scripts, *Client MCP* ou scripts en **Sandbox** isolée) ; et (3) exposer le **Serveur MCP gouverné d'ORCIA (`/api/v1/mcp`)** aux IDE externes (VS Code, Cursor, Claude Code, Antigravity) en mode *Passthrough*. Réalise `UJ-1`, `UJ-2`, `UJ-3`, `UJ-5`, `UJ-6`, `UJ-7`, `UJ-10`.

**Consequences (testable) :**
- Toute création, modification ou transition d'état d'un ticket **Jira** proposée par un agent exécuteur mentionne explicitement le `project_key` Jira cible parmi les projets rattachés au Workspace, est préparée en mode *Staged* dans le brouillon de l'étape (`Validation par Découpage` `FR-6`) et n'est appliquée dans Jira qu'après validation de la **Gate** associée (`AD-11`).
- Lorsqu'un ticket **Jira** externe bloquant un **Workflow Run** suspendu (`UJ-3`) passe au statut résolu (`Done`), le Webhook Jira notifie ORCIA en `< 500 ms` (SSE) et propose à l'utilisateur de lancer le **Replay** (`FR-16`).
- L'exécution d'un script en **Sandbox** est soumise à des limites strictes de CPU, mémoire, `timeout` (`< 5s`) et isolation réseau, et tout appel sur le **Serveur MCP (`/api/v1/mcp`)** respecte le mode *Passthrough*, le **Permission Broker** et l'interdiction d'écrire sur les sections `human_authored_required: true`.

---

### 4.9 Provenance Auditable, Observabilité, FinOps Complet (Setup + Run) & Réversibilité Humaine

**Description :** Plutôt que de poursuivre une idempotence textuelle illusoire sur des LLMs probabilistes, ORCIA garantit l'invariance structurelle et une **Provenance Auditable** à 100%, tout en offrant à la direction un pilotage FinOps complet (Setup + Run vs TTM) et des indicateurs de maintien de la maîtrise humaine (**Réversibilité Humaine**). Réalise `UJ-7`, `UJ-8`.

**Functional Requirements :**

#### FR-25 : Provenance Auditable Complète par Step et par Gate
Pour chaque **Step** et chaque **Gate** d'un **Workflow Run**, le système enregistre de manière immuable : les URI et hashes `SHA-256` des ressources fédérées, le fournisseur/modèle LLM et ses hyperparamètres, le prompt exact assemblé, les chunks de **Base de Connaissances** injectés, les appels **MCP**/**Skills**/mutations **Jira**, la durée, les tokens/coûts, et l'identité ainsi que le temps de revue des intervenants humains. Réalise `UJ-6`, `UJ-7`, `UJ-8`.

**Consequences (testable) :**
- Tout auditeur habilité peut inspecter ou exporter en JSON/Markdown la trace complète de provenance d'un **Workflow Run** et vérifier qu'aucune étape n'a utilisé une ressource non épinglée.

#### FR-26 : Comptabilité FinOps Complète (Coût de Setup + Coût de Run vs TTM) et Garde-fous Budgétaires
Le système comptabilise en temps réel les tokens et coûts d'inférence LLM ainsi que le temps de setup et de contribution humaine par **Step**, par **Workflow Run**, par **Workflow** et par Équipe/BU, et applique des plafonds budgétaires et des coupe-circuits anti-boucles infinies. Réalise `UJ-8`.

**Consequences (testable) :**
- Si un **Workflow Run** dépasse le plafond de coût (`max_cost_per_run`) ou le nombre maximal d'itérations de boucle entre deux **Steps**/Gates (`max_step_retries`), le moteur suspend immédiatement l'exécution et alerte le responsable du run.
- Le tableau de bord FinOps compare le coût complet (amortissement du Setup + Run tokens + temps humain) au gain de TTM par rapport à la baseline déclarée du processus.

#### FR-27 : Indicateurs d'Impact Cognitif, Anti-Rubber-Stamping et Indice de Réversibilité Humaine
Le système calcule et expose par **Workflow** et par Équipe/BU trois indicateurs de gouvernance humaine et technique : (1) le ratio *Temps de Cadrage Actif (`Human-Led Anchors` + `Arbitrages`) vs Temps de Simple Relecture*, (2) le taux de *Rubber-Stamping* aux **Gates Humaines**, et (3) l'indice de **Pattern Drift** / **Réversibilité Humaine**. Réalise `UJ-6`, `UJ-8`.

**Consequences (testable) :**
- Lorsqu'un **Workflow** présente un taux d'approbation aux **Gates Humaines** supérieur à `98%` avec un temps médian de revue inférieur au seuil minimal ou0 modification/commentaire sur une période donnée, le système génère une alerte de gouvernance recommandant soit de basculer la **Gate** en politique `risk_or_exception_based` / `sampling`, soit de renforcer les **Ancrages Humains Obligatoires**.

#### FR-28 : Workflows Système d'Initialisation, Onboarding Autonome d'Équipe & Multi-Workspaces Multi-Sources par le Chef d'Équipe (`TEAM_LEAD`) et Auto-Amorçage Gouverné (`orcia://system/bootstrap/*`)
Le système embarque nativement 6 **Workflows Système** d'initialisation guidés par l'**Agent Assistant** et validés par des **Gates Déterministes** bloquantes : (1) `init-organization` (SSO OIDC / Auth locale + RBAC, test d'au moins 2 familles de modèles LLM orthogonales, amorçage de l'**Ontologie** Niveau 1 et du catalogue socle), (2) `init-workspace` (exécutable en autonomie par un **Chef d'Équipe (`TEAM_LEAD`)** pour structurer son équipe/sous-équipes, inviter ses membres en leur pré-affectant leur **Profil Humain** et leurs rôles d'exécution, définir la surcharge standard d'équipe `TEAM` et l'**Ontologie** `3_TEAM`, puis créer un ou plusieurs **Workspaces (solutions logicielles)** rattachés à l'équipe avec leur surcharge `WORKSPACE` et leur **Ontologie** `3_WORKSPACE`), (3) `init-datasource` (enrôlement par un Admin ou par le **Chef d'Équipe** dans un **Workspace** ou en portée `SHARED_TEAM` de **multiples dépôts `git://`, multiples projets `jira://`, multiples espaces `confluence://`**, schémas `db://` et registres `nexus://` dédiés à la solution, avec alias logiques et filtres CQL/JQL de gouvernance), (4) `init-existing-project` (scan des dépôts existants d'un Workspace vers son contrat d'architecture de référence `ARCHITECTURE-SPINE.md` anti-**Pattern Drift**), (5) `init-skill` (certification en **Sandbox** `< 5s`), et (6) `init-user` (déclenché automatiquement au 1er login de chaque membre invité pour confirmer le **Profil Humain** pré-assigné par son Chef d'Équipe et lier ses comptes **Jira**, **Confluence** et **Git** en mode *Passthrough*). Réalise `UJ-1` à `UJ-10`.

**Consequences (testable) :**
- Aucune organisation ne peut activer de **Gates Agentiques** tant que `init-organization` n'a pas validé la disponibilité d'au moins deux familles de modèles distinctes.
- Un **Chef d'Équipe (`TEAM_LEAD`)** peut compléter en self-service l'onboarding de son équipe, créer plusieurs **Workspaces** correspondant aux différentes solutions logicielles de son équipe, connecter sur chaque Workspace **autant de dépôts `git://`, de projets `jira://` et d'espaces `confluence://` dédiés que la solution en comporte** via `init-datasource`, et inviter ses membres (`init-user` au 1er login) sans nécessiter l'intervention d'un Administrateur Plateforme.
- Aucune source de données fédérée ou **Base de Connaissances** (y compris chaque espace **Confluence** ou projet **Jira** rattaché au Workspace) ne peut être publiée dans le **Catalogue Fédéré** via `init-datasource` tant que sa fiche de procédure dans le **Permission Broker** (signée comme **Ancrage Humain Obligatoire**) et sa politique de fraîcheur (`freshness_ttl_days`) ne sont pas valides.

---

## 5. Non-Goals (Explicit)

Pour protéger la focalisation de l'équipe sur la valeur distinctive d'ORCIA, voici ce que le produit **ne fait pas** en v1 (MVP) :
- **Pas de recherche d'idempotence textuelle mot-à-mot des LLMs** : ORCIA ne tente pas de forcer deux exécutions d'un LLM à produire exactement la même chaîne de caractères au caractère près ; il garantit en revanche l'**Invariance Structurelle et Ontologique** (via les **Gabarits d'Artefact**, l'**Ontologie** et les **Gates Déterministes**) et la **Provenance Auditable** complète.
- **Pas de génération automatique continue `Code -> Doc` en production** : ORCIA n'utilise jamais le code nouvellement généré par l'IA comme unique source de vérité pour écraser la documentation produit sans validation d'intention amont (afin d'éviter de transformer des bugs en features documentées).
- **Pas d'entraînement ou de fine-tuning de modèles LLM propriétaires** : ORCIA orchestre et route des modèles existants (Cloud ou Locaux via Ollama/vLLM) enrichis par l'**Ontologie** et le RAG, mais n'est pas une plateforme MLOps d'entraînement de poids de modèles.
- **Pas de remplacement des outils ALM / Forges Git / Registres d'entreprise** : ORCIA s'intègre, fédère et orchestre `git://`, `nexus://`, `confluence://` et `jira://`, mais n'a pas vocation à remplacer GitLab/GitHub, Sonatype Nexus ni Atlassian Jira/Confluence pour l'hébergement natif des tickets, wikis, codes sources ou binaires.
- **Pas d'exécution en boîte noire 100% autonome sans garde-fous** : En MVP, aucun processus critique d'entreprise ne s'exécute sans **Ancrages Humains Obligatoires**, **Contrôles Transverses d'Invariants** et **Gates**.

---

## 6. MVP Scope

### 6.1 In Scope (Lot 1 — MVP & Pilote Ingénierie IT)

- **Interface Web "Chat-First + Canvas"** par défaut avec **Agent Assistant** adaptatif au **Profil Humain** (`FR-1`), **Centre de Notifications** individuel/équipe avec *Claim* et verrou de présence temps réel (`FR-2`), et suivi multi-runs *Consultation seule vs Contributeur* (`FR-3`).
- **Dispositif "Human-Led" & Ergonomie Cognitive** : **Ancrages Humains Obligatoires** (`FR-4`), **Arbitrage Humain** sur options équivalentes (`FR-5`), **Briefing de Revue** et **Validation par Découpage** (`FR-6`), et **Boucle de Challenge / Rétroaction Inter-Steps avec Simulation d'Impact (*What-If*)** (`FR-7`).
- **Ontologie Dynamique Multi-Niveaux** : 4 strates (`Entreprise -> BU -> Équipe -> Run`), extraction temps réel + simulation d'impact + promotion gouvernée, et les 3 rôles actifs (`FR-8`, `FR-9`, `FR-10`).
- **Conception Déclarative, Composition Assistée & Gabarits** : **Workflow-as-Code** YAML/JSON et assemblage/ajustement conversationnel de workflows par l'**Agent Assistant** (`FR-11`, `UJ-10`), **Gabarits d'Artefact** multi-audience Markdown/JSON Schema (`FR-12`) et discipline `Intention -> Code` (`FR-13`).
- **Moteur d'Orchestration Hybride & Exécution en Tâche de Fond** : Multi-LLM agnostique (OpenAI, Anthropic, Gemini, Ollama/vLLM), **Blackboard** filtré (`FR-14`), exécution bimodale (*Coaching* interactif vs *Fast-Path / Tâche de fond* avec arbitrage accumulé en fin de run `UJ-10`), **Version Pinning** `SHA-256` (`FR-15`) et **Replay** à partir du **Step** $N$ (`FR-16`).
- **Système de Gates Fiabilisé** : **Gates Déterministes** avec détection de **Pattern Drift** (`FR-17`), **Gates Agentiques** avec **Orthogonalité des Modèles**, **Vérification Atomique de Faits (`fact_verification`)** et **Contrôle Transverse d'Invariants** (`FR-18`), et **Gates Humaines** à **Politique de Gate Adaptative** + anti-*Rubber-Stamping* (`FR-19`).
- **Catalogue Fédéré, Authentification Hybride & Onboarding d'Équipe** : Résolution à la volée `db://`, `git://`, `nexus://`, `confluence://`, `jira://` avec cache local `SHA-256` (`FR-20`), authentification primaire bi-mode (`OIDC / OAuth 2.1` + locale `Argon2id / TOTP`), modèle RBAC/ABAC tri-dimensionnel avec rôle de **Chef d'Équipe (`TEAM_LEAD`)** pour l'onboarding autonome (`FR-21`, `FR-28`) et **Permission Broker** guidant l'humain via la KB des procédures d'accès et Jira (`FR-22`).
- **Écosystème d'Exécution, Graphe Tripartite & Actions Jira** : **Bases de Connaissances** avec indexation différenciée (**Confluence `confluence://`**, tickets **Jira `jira://`**, Markdown, PDF en *Parent-Child*, code `git://` en *AST + Code Graph*, vecteurs `halfvec(1024)`, **Graphe Tripartite `Confluence ↔ Jira ↔ Git`**), contrôle `data-freshness` et **Alerte d'Obsolescence Documentaire** (`FR-23`), lecture JQL temps réel + création/modification/transition de workflows **Jira** stagées par les **Gates** + Webhooks Jira, **Skills** Markdown+Scripts, **MCP Bidirectionnel (Client + Serveur IDE `/api/v1/mcp`)** et **Sandbox** d'exécution (`FR-24`).
- **Provenance, FinOps, Réversibilité & Amorçage** : **Provenance Auditable** complète (`FR-25`), comptabilité FinOps Setup + Run (`FR-26`), indicateurs cognitifs et de **Réversibilité Humaine** (`FR-27`), et 6 **Workflows Système** d'initialisation (`FR-28`), validés sur les parcours `UJ-1` à `UJ-10`.

### 6.2 Out of Scope for MVP (Différé aux Lots 2 et 3)

- **Éditeur Visuel Drag-and-Drop de création ex-nihilo de tous les Workflows métiers** *(Lot 2)* — En MVP, l'éditeur visuel de nœuds (`@xyflow/react`) est activé pour le workflow de l'**Agent Assistant** et la visualisation/inspection interactive des graphes dans le **Canvas**, tandis que la création de nouveaux workflows métiers s'effectue en **Workflow-as-Code** YAML/JSON ou par assemblage conversationnel assisté par l'**Agent Assistant** (`FR-11`, `UJ-10`).
- **Synthèse autonome de code d'agents ou de skills arbitraires sans briques du Catalogue** *(Lot 3)*.
- **Quorum complexe (ex: 2/3 architectes), Séparation stricte des tâches (SoD) automatisée, Confidentialité intra-processus (masquage d'étapes entre intervenants d'un même run), fédération SAML 2.0 patrimoniale et provisionnement SCIM 2.0 automatisé** *(Lot 2)* — Le MVP implémente déjà l'authentification **OIDC / OAuth 2.1**, l'authentification locale **Argon2id + TOTP**, les rôles/groupes/équipes, l'onboarding autonome par le **Chef d'Équipe (`TEAM_LEAD`)** et le **Permission Broker**.
- **Bases vectorielles externes dédiées (Qdrant/Neo4j GraphRAG distribué) et autres connecteurs bureautiques tiers hors Atlassian (SharePoint, Google Drive, ServiceNow)** *(Lots 2 & 3)* — Le MVP intègre nativement PostgreSQL `pgvector` (`halfvec(1024)`), `git://`, `nexus://`, `db://` ainsi que les connecteurs gouvernés **Confluence (`confluence://`)** et **Jira (`jira://`)**.
- **Signature cryptographique Cosign/SLSA des bundles et Marketplace inter-organisations** *(Lot 3)*.

---

## 7. Success Metrics

### Primary Metrics (Valeur Métier, Budgétaire & Qualité)

- **SM-1 (Optimisation Budgétaire Globale — Setup + Run)** : Réduction d'au moins **25% du coût complet de réalisation** (incluant l'amortissement du temps de setup du **Workflow**, le coût des tokens LLM et le temps humain de cadrage/revue) sur le cas d'usage pilote d'Ingénierie IT après 5 exécutions, par rapport au processus manuel de référence. Valide `FR-14`, `FR-16`, `FR-26`.
- **SM-2 (Détection Précoce des Incompatibilités & Dérives Amont)** : **100% des incompatibilités structurelles, d'Ontologie ou de contrat d'API répertoriées** sont interceptées avant la phase de codage/merge grâce aux **Contrôles Transverses d'Invariants**, à l'**Alerte d'Obsolescence Documentaire** et aux **Gates** (`UJ-2`, `UJ-3`). Valide `FR-7`, `FR-10`, `FR-17`, `FR-18`, `FR-23`.
- **SM-3 (Fluidité Multi-Workflows & Résolution d'Habilitation)** : Temps médian de prise en charge d'une notification bloquante (*Claim* $\rightarrow$ Décision d'arbitrage ou validation par découpage) **inférieur à 10 minutes**, et **100% des blocages d'habilitation** accompagnés d'une procédure d'obtention actionnable via le **Permission Broker**. Valide `FR-2`, `FR-3`, `FR-6`, `FR-22`.

### Secondary Metrics (Adoption & Mutualisation)

- **SM-4 (Mutualisation Fédérée & Capitalisation Ontologique)** : Au moins **60% des Agents, Skills et Gabarits d'Artefact** utilisés dans un nouveau **Workflow** d'équipe proviennent du **Catalogue Fédéré** (`db://`, `git://`, `nexus://`), et au moins **5 concepts ou règles métier** découverts en exécution (*Niveau 4 Run*) sont promus vers l'**Ontologie** d'Équipe ou de BU (*Niveaux 3 et 2*) durant le pilote. Valide `FR-8`, `FR-9`, `FR-20`, `FR-21`.
- **SM-5 (Réduction du Time-to-Market / Lead Time)** : Réduction de **30% du délai de bout en bout** entre l'expression du besoin PM (`UJ-1`) et la Pull Request validée prête au déploiement (`UJ-6`), sans dégradation de la qualité aux **Gates**. Valide `FR-1`, `FR-14`.

### Counter-Metrics (Garde-fous — Ce qu'il ne faut surtout pas optimiser au détriment de la maîtrise)

- **SM-C1 (Taux de Validation Aveugle / Rubber-Stamping Humain)** : Le taux d'approbation aux **Gates Humaines** sans ouverture du **Briefing de Revue**, sans commentaire/édition ou en moins de 15 secondes sur des **Artefacts** complexes doit rester **strictement inférieur à 5%**. *Pourquoi : Optimiser la vitesse de passage des Gates en transformant les experts en "tamponneurs" passifs détruit la sécurité et la gouvernance.* Contrebalance `SM-3` et `SM-5`. Valide `FR-4`, `FR-6`, `FR-19`, `FR-27`.
- **SM-C2 (Ratio Cadrage "Human-Led" vs Simple Relecture)** : La part du temps humain consacrée à la réflexion amont (**Ancrages Humains Obligatoires**, **Arbitrages Humains** sur options équivalentes et challenges d'architecture) ne doit jamais descendre sous **40% du temps humain total** investi dans le **Workflow Run**. *Pourquoi : Empêcher la dérive des experts du rôle de "concepteur/décideur" vers un rôle purement passif de "lecteur".* Contrebalance `SM-1` et `SM-5`. Valide `FR-4`, `FR-5`, `FR-27`.
- **SM-C3 (Indice de Pattern Drift & Dette de Compréhension Globale)** : Le taux de nouveaux motifs architecturaux ou dépendances non répertoriés dans l'**Ontologie** introduits par le code généré doit rester **égal à 0%** (sauf dérogation d'architecture explicitement signée à une **Gate Humaine**). *Pourquoi : Garantir la **Réversibilité Humaine** et éviter qu'une suite de PRs individuellement valides ne crée une codebase hétérogène imbitable.* Contrebalance `SM-5`. Valide `FR-13`, `FR-17`, `FR-18`, `FR-27`.

---

## 8. Open Questions (Résolues en Architecture)

1. **OQ-1 (Authentification aux dépôts Git, Nexus, Confluence et Jira privés en mode Passthrough vs Service Principal)** : *[RÉSOLU — AD-6]* Mode *Passthrough* OIDC/OAuth/PAT utilisateur par défaut ; mode *Service Principal* réservé aux étapes explicitement approuvées par un Administrateur (notamment pour les exécutions en tâche de fond avec traçabilité de l'initiateur humain).
2. **OQ-2 (Outil de ticketing / IAM cible pour le Permission Broker et le suivi des tâches)** : *[RÉSOLU — AD-5, AD-6, AD-8]* **Atlassian Jira (`jira://`)** est l'outil de ticketing cible (couplé à la KB Markdown/YAML des procédures d'habilitation).
3. **OQ-3 (Seuils d'échantillonnage et de risque par défaut des Gates Adaptatives)** : *[RÉSOLU — AD-11]* Seuil `sampling` à `20%` des runs conformes et score minimal `agentic_score >= 0.85` (avec `0` conflit d'ontologie et `0` alerte `[STALE_WARNING]`) pour le mode `risk_or_exception_based`.

---

## 9. Assumptions Index

- **A-1 (§4.2, FR-6)** : Un **Artefact** est considéré comme volumineux et déclenche obligatoirement le mode de **Validation par Découpage** au-delà de `1 500 mots` ou de `3 sections` définies dans son **Gabarit d'Artefact** (paramétrable par **Workflow**).
- **A-2 (§4.6, FR-19)** : Une validation humaine effectuée en moins de `15 secondes` sur un **Artefact** volumineux sans interaction avec le **Briefing de Revue** est qualifiée de suspicion de *Rubber-Stamping* et déclenche une demande de confirmation explicite.
- **A-3 (§4.7, FR-20)** : Les bundles hébergés sur Nexus (`nexus://`) pour le MVP seront au format archive standard (`.tar.gz` ou `.zip`) contenant un manifeste déclaratif `orcia-bundle.yaml` et son empreinte `SHA-256`.

---

## 10. Cross-Cutting Non-Functional Requirements (NFRs) & Guardrails

### 10.1 Sécurité, Isolation & Gouvernance des Données
- **NFR-SEC-1 (Isolation de la Sandbox)** : Toute exécution de script d'un **Skill** ou d'une **Gate Déterministe** doit tourner dans un environnement isolé (conteneur éphémère ou processus restreint sans privilèges root, avec système de fichiers éphémère limité au workspace du **Step** et liste blanche réseau).
- **NFR-SEC-2 (Souveraineté, Confidentialité & Pseudonymisation PII Réversible des Données LLM)** : Le routeur Multi-LLM doit permettre (1) d'interdire l'envoi de certains niveaux de classification de données (définis dans l'**Ontologie** ou la **Base de Connaissances**) vers des APIs Cloud externes en les routant exclusivement vers les modèles locaux/souverains (Ollama/vLLM), et (2) d'appliquer à la volée une **pseudonymisation PII réversible** (`anonymize_pii_reversible: true`) remplaçant les données personnelles ou secrets métiers par des jetons déterministes avant l'appel Cloud et les ré-hydratant localement au retour.
- **NFR-SEC-3 (Immuabilité de la Provenance)** : Les journaux de **Provenance Auditable** (`FR-25`) et les décisions de **Gates** sont en écriture seule (*Append-Only*) et horodatés cryptographiquement.

### 10.2 Performance & Réactivité de l'Interface Conversationnelle
- **NFR-PERF-1 (Temps de réponse UI & Streaming)** : Le premier token de réponse de l'**Agent Assistant** dans l'interface **Chat-First + Canvas** doit s'afficher en `< 1,5 s` (hors temps de raisonnement profond d'un **Step** complexe), et la bascule entre deux **Workflow Runs** depuis le **Centre de Notifications** doit s'effectuer en `< 1 s`.
- **NFR-PERF-2 (Performance du Cache Fédéré)** : Lorsqu'une ressource `git://` ou `nexus://` est déjà présente dans le cache local `SHA-256`, sa résolution au démarrage d'un **Step** doit prendre `< 50 ms`.

### 10.3 Fiabilité, Résilience & Processus Longs
- **NFR-REL-1 (Persistance des Workflows Longs)** : L'état complet d'un **Workflow Run** et de son **Blackboard** est persisté en base de données après chaque transition de **Step** ou de **Gate**, permettant à un **Workflow Run** de rester suspendu en attente d'une intervention humaine ou d'un partenaire externe (`UJ-3`) pendant plusieurs semaines et de survivre à un redémarrage complet du serveur ORCIA sans aucune perte d'état.
