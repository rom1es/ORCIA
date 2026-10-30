
Voici le prompt consolidé et enrichi pour l'agent BMAD (profil Principal UX/UI Architect & Enterprise Design Lead avec posture contradictoire Anti-Consensus Club), intégrant l'ensemble des axes d'architecture de l'information, la gestion des habilitations, le hub de configuration et les parcours d'initialisation durables :

Markdown
Role: Principal UX/UI Architect & Enterprise Design Lead (Anti-Consensus Club)
Task: Comprehensive UI/UX Redesign, Navigation Architecture & Onboarding Journeys for ORCIA

Context:
ORCIA est une plateforme d'orchestration agentique d'entreprise articulée autour d'un Core agnostique (moteur durable DBOS / PostgreSQL, outbox, catalogue fédéré multi-sources, broker d'identités OIDC/RBAC) et de modules verticaux (packs métier, dont le MVP SDLC et de futurs packs RH/MCO)[cite: 1, 2].
Le socle technique frontend est une SPA pure basée sur Vite 6, TanStack Router et Tailwind/Radix[cite: 1, 2].
Nous devons refondre l'architecture de l'interface utilisateur pour intégrer la gouvernance d'accès (mode consultation stricte vs modification), la nouvelle mire d'authentification hybride, le commutateur de contexte de pack, un hub d'administration complet (anticipant l'Epic 8) ainsi que des assistants d'initialisation adaptés à différents profils[cite: 1, 2].

Objective:
Réaliser une revue critique et contradictoire de l'architecture de l'information actuelle (`docs/planning-artifacts/ux-designs/`) et produire les spécifications ergonomiques détaillées pour l'ensemble des parcours, écrans clés et comportements conditionnels[cite: 1, 2].

---

Instructions d'analyse et de conception :

1. Mire de Connexion & Authentification Hybride (`/login`)
- Concevoir le parcours d'entrée bi-mode (Story 1.2) : bouton SSO OIDC prioritaire (Keycloak / Entra ID) et accordéon/onglet d'authentification locale de secours pour l'administration système[cite: 1, 2].
- Définir les états de chargement, de redirection OIDC, d'expiration de session et de gestion des erreurs (compte désactivé, échec mTLS, rejet de jeton)[cite: 1, 2].

1. Layout Global & Zones Structurelles
- **Barre supérieure (Header / App Bar) :**
  * Sélecteur de Contexte / Espace de travail (*Workspace Switcher*) filtrant dynamiquement les packs actifs et autorisés pour l'utilisateur connecté (ex. Espace SDLC vs Espace RH)[cite: 1, 2].
  * Barre d'information & Indicateurs de santé système (connectivité PostgreSQL/DBOS, débit et état de la table Outbox, badge d'environnement PROD/STAGING)[cite: 1, 2].
  * Profil utilisateur avec affichage explicite des rôles actifs et bascule de thème.
- **Navigation Latérale (Sidebar) :**
  * Réorganiser l'arborescence entre les vues opérationnelles du pack actif (Backlog, Graphe ontologique, Workflows, Anchor Cards) et les rubriques transverses de la plateforme[cite: 1, 2].
  * Entrée dédiée au Hub de Paramétrage (`/settings/*`) avec sous-menus thématiques (IAM, Connecteurs, Fournisseurs IA, Packs, Studio Workflows, Audit)[cite: 1, 2].
  * Comportement rétractable (*collapsed mode*) avec infobulles contextuelles.

1. Panneau Principal & Modèle d'Habilitation (Lecture vs Modification)
- Établir le standard visuel transverse pour différencier les droits `read` et `write` (RBAC/ABAC) :
  * Matérialisation d'un écran en consultation stricte (auditeur/opérateur) : labels statiques, badges, inputs désactivés avec infobulle expliquant la permission manquante, suppression ou désactivation des boutons de soumission.
  * Emplacement et comportement des actions de modification (bouton d'édition global en en-tête, édition en ligne, barre d'actions flottante avec validation/annulation).
  * Traitement de sécurité sur les secrets : masquage systématique des tokens/clés (`••••••••`), bouton de révélation temporaire conditionné à une permission élevée, champ d'écrasement explicite et dialogue de confirmation destructive.

1. Hub de Configuration Transverse (`/settings/*` - Préfiguration Epic 8)
- Découper l'arbre des routes TanStack Router pour les 6 domaines de paramétrage :
  1. Sécurité & IAM (`/settings/iam`) : Arbre des rôles, groupes, Service Principals IA et scopes d'exécution[cite: 1, 2].
  2. Intégrations SI (`/settings/connectors`) : Catalogue fédéré Git, Jira, Confluence, bases de données, statut des crawls et indexations différentielles[cite: 1, 2].
  3. Politiques IA (`/settings/ai-models`) : Fournisseurs LLM, passerelles souveraines, quotas/budgets de tokens et règles de garde[cite: 1, 2].
  4. Registre des Packs (`/settings/packs`) : Découverte, activation modulaire, dépendances et configuration propre aux packs actifs[cite: 1, 2].
  5. Studio d'Orchestration (`/settings/workflows`) : Gabarits YAML/JSON, taxonomie des exécuteurs, règles de retries/timeouts DBOS et chaînage ordonné des gates (déterministes vs probabilistes)[cite: 1, 2].
  6. Audit & Supervision (`/settings/audit`) : Journalisation append-only PostgreSQL et rejeu des événements de la table Outbox[cite: 1, 2].

1. Parcours d'Initialisation Dédiés (*Bootstrapping Wizards & Zero Empty-State*)
- Spécifier les parcours guidés étape par étape pour 3 profils cibles :
  * **Parcours « Tech Lead / Équipe Software » (Pack SDLC) :** Connexion dépôt Git + projet Jira, détection/création du dossier `specs/`, calibration de la sévérité des agents de revue (*Blind Hunter*, *Edge Case Hunter*) et premier dry-run de validation ontologique[cite: 1, 2].
  * **Parcours « Responsable Métier / Opérations » (ex. Pack RH ou Achats) :** Sélection du gabarit de processus métier, raccordement des accès applicatifs (SIRH/ERP), paramétrage des seuils d'impact What-If et assignation des rôles arbitres pour les Anchor Cards[cite: 1, 2].
  * **Parcours « Administrateur Plateforme / Sécurité SI » (Socle Transverse) :** Fédération SSO OIDC d'entreprise, déclaration des clés de chiffrement et endpoints LLM, politiques de rétention d'audit DBOS[cite: 1, 2].
- **Exigences techniques transverses aux parcours :**
  * *Gestion de l'Empty-State :* Option d'injection d'un « Workspace Démo » pré-rempli (avec fausse spec, simulation What-If et Anchor Card fictive) pour éviter tout écran blanc à la première connexion[cite: 1, 2].
  * *Validation Fail-Fast :* Bouton de healthcheck direct (« Tester la connexion ») à chaque étape du wizard déclenchant un step déterministe sous DBOS avant validation[cite: 1, 2].
  * *Persistance Durable :* Sauvegarde de l'état d'avancement du wizard dans PostgreSQL (DBOS) pour permettre une reprise ultérieure sans perte de saisie[cite: 1, 2].

---

Format de sortie attendu :
1. **Architecture de l'information (Wireframe textuel / ASCII)** de la coquille globale (Header, Sidebar, Main Canvas), de la mire de connexion et d'un wizard type[cite: 1, 2].
2. **Arborescence formelle des routes TanStack Router** avec les gardes de permissions associés (`beforeLoad`) et la gestion des contextes de packs[cite: 1, 2].
3. **Design System & Patterns de composants :** Spécification du pattern d'autorisation UI (ex. composant `<PermissionGuard mode="read|write">`), du composant de gestion de secret et de la carte d'arbitrage (*Anchor Card*)[cite: 1, 2].
4. **Plan de migration documentaire :** Inventaire des fichiers à créer ou réviser dans `docs/planning-artifacts/ux-designs/` avant le lancement du développement de l'Epic 8[cite: 1, 2].


brief des écrans et un descriptif d'une opportunité pour améliorer ORCIA suite partage des screens shots d'un exemple de plateforme agentique


# Brief Écran 1 : Accueil & Dashboard KORE

## 1. Synthèse de l'Écran
* **Rôle principal :** Hub d'atterrissage (*Landing Page*) personnalisé combinant un point d'entrée conversationnel IA et un widget de suivi opérationnel de l'itération en cours[cite: 5].
* **Utilisateur cible :** Opérateur ou responsable de projet connecté à un espace d'équipe spécifique (`Équipe Mon Compte`)[cite: 5].

---

## 2. Décomposition de l'Interface

### Navigation Latérale (Sidebar Gauche)
* **Sélecteur de contexte :** Équipe active (`Équipe Mon Compte`) et profil utilisateur connecté[cite: 5].
* **Action principale :** Bouton `Nouvelle discussion` pour réinitialiser le fil de prompt[cite: 5].
* **Menu de navigation :**
  * **Espace général :** `Accueil`, `Discussions`[cite: 5].
  * **Administration :** Section dédiée `ADMINISTRATION` > `Administration`[cite: 5].
  * **Espace opérationnel (`MON ESPACE`) :** `Mes notes`, `Documents`, `Workflows`, `Produits`, `Incidents`, `Aide`[cite: 5].

### Zone Principale (Main Canvas)
* **Barre d'invite conversationnelle (*Prompt Box*) :**
  * Salutation contextuelle (*« Bon après-midi, Romain — Sur quoi avancez-vous ? »*)[cite: 5].
  * Sélecteur de périmètre RAG (*« Toutes les sources »*) et déclencheur d'ajouts de pièces jointes (`+`)[cite: 5].
* **Widget Opérationnel (*Sprint en cours*) :**
  * Indicateur d'itération SAFe / Agile (`IRCO - PI12_IT2 - Il reste 1 jour`)[cite: 5].
  * Métriques de suivi : progression globale (jauge circulaire à 0%), volume de tickets (`0/1 terminé`, `1 restant`) et vélocité[cite: 5].
  * Appel à l'action IA proactif : bouton `Analyser ce sprint avec Kore ↗`[cite: 5].
* **Accès Rapides (*Vos Espaces*) :**
  * Cartes de redirection directe vers les `Documents` (base documentaire indexée) et les `Workflows` (automatisations)[cite: 5].

---

## 3. Opportunités d'Amélioration & Transposition pour ORCIA

### A. Ancrage Contextuel du Sprint dès le Header
* **Constat :** L'assistant est immédiatement couplé au sprint Jira/Agile actif de l'équipe[cite: 5].
* **Opportunité ORCIA :** Dans le cadre du catalogue fédéré (Epic 1 / 1.3), lier automatiquement le *Workspace Switcher* à l'initiative, au PI ou au sprint en cours afin d'alimenter directement le graphe ontologique sans configuration manuelle par prompt[cite: 1, 5].

### B. Bouton d'Analyse Contextuelle en 1-Clic
* **Constat :** Présence d'un CTA dédié invitant l'agent à auditer le sprint[cite: 5].
* **Opportunité ORCIA :** Ajouter un déclencheur rapide pour lancer les agents de challenge (*Blind Hunter*, *Edge Case Hunter*) ou une simulation What-If (Story 3.5) sur le périmètre du sprint ou de la release (ex. *« Auditer les risques du lot »*)[cite: 1, 2, 5].

### C. Scoping Explicite des Sources & Permissions
* **Constat :** Sélecteur déroulant intégré au prompt pour restreindre le corpus interrogé[cite: 5].
* **Opportunité ORCIA :** Permettre le filtrage dynamique des sources de vérité (Spec-Kit Markdown, tickets Jira, arborescence Git, documents métiers) tout en appliquant les contrôles d'accès stricts du *Permission Broker*[cite: 1, 5].

### D. Tableau de Bord Hybride anti-« Écran Blanc »
* **Constat :** L'accueil oriente l'utilisateur vers des actions concrètes et des métriques même en l'absence de prompt[cite: 5].
* **Opportunité ORCIA :** Dès l'initialisation, présenter sous le champ d'invite les workflows durables en cours sous DBOS, l'état des connecteurs et les éventuelles cartes d'arbitrage en attente d'action humaine (*Anchor Cards*, Story 3.4)[cite: 2, 5].
meme demande en format markdown avec l'image suivante

Markdown
# Brief Écran 2 : Sidebar Repliée & Mode Compact KORE

## 1. Synthèse de l'Écran
* **Rôle principal :** Déclinaison de l'interface en mode rétracté (*Collapsed Sidebar / Focus Mode*) visant à maximiser la surface utile du panneau principal tout en maintenant l'accès aux fonctionnalités clés via des repères iconographiques[cite: 6].
* **Composant mis en évidence :** Infobulle et contrôle d'extension latérale (*« Déployer »*) au survol de la barre de navigation réduite[cite: 6].

---

## 2. Décomposition de l'Interface

### Sidebar Rétractée (Rail Iconographique Gauche)
* **Logo / Identité :** Icône compacte de la marque KORE en en-tête[cite: 6].
* **Contrôle d'expansion :** Bouton chevron interactif avec infobulle explicite `Déployer` permettant de restaurer la sidebar complète[cite: 6].
* **Avatar & Compte :** Badge compact de l'équipe active (`MC`)[cite: 6].
* **Actions et sections sous forme d'icônes :**
  * Icône `Nouvelle discussion` (crayon/bloc-notes)[cite: 6].
  * Icône `Accueil` surlignée par une bordure active jaune (état sélectionné)[cite: 6].
  * Icônes des modules : `Discussions` (bulle), `Administration` (bouclier/sécurité), `Notes`, `Documents`, `Workflows` (embranchement/flux), `Produits` (colis/pack), `Incidents` (alerte), `Aide` (point d'interrogation)[cite: 6].

### Zone Principale (Main Canvas)
* Conserve la vue d'accueil (champ d'invite, sélecteur de sources, widget d'avancement du sprint) en gagnant un espace horizontal significatif pour la lisibilité des données[cite: 6].

---

## 3. Opportunités d'Amélioration & Transposition pour ORCIA

### A. Implémentation d'un « Rail Mode » sous TanStack Router & Tailwind
* **Constat :** La sidebar s'efface élégamment pour laisser la priorité au contenu de travail sans perdre l'orientation globale[cite: 6].
* **Opportunité ORCIA :** Intégrer nativement un état `isCollapsed` persistant (stocké en `localStorage` ou dans l'état de session utilisateur) dans le layout global de la SPA[cite: 1, 2]. Pour ORCIA, ce mode est indispensable lors de la manipulation du graphe ontologique tripartite (Epic 2) ou de l'éditeur de workflows complexes afin d'éviter l'encombrement visuel[cite: 1, 2].

### B. Affichage Contextuel des Rôles et des Badges de Pack
* **Constat :** Le badge `MC` indique de manière minimale l'équipe courante[cite: 6].
* **Opportunité ORCIA :** Dans le rail compact d'ORCIA, afficher l'icône du **Pack actif** (ex. logo badge *SDLC*, *RH*, *MCO*) avec une infobulle (Radix Tooltip) indiquant le pack courant, les permissions effectives de l'utilisateur (`read` ou `write`) et un raccourci de bascule rapide d'espace[cite: 1, 2].

### C. Indicateurs Visuels d'Événements en Attente (*Anchor Cards*)
* **Constat :** Les icônes restent statiques en dehors de l'indicateur d'onglet actif[cite: 6].
* **Opportunité ORCIA :** Exploiter la sidebar réduite pour afficher des **pastilles de notification dynamiques (Badges d'alerte)** :
  * Un badge sur l'icône Workflows/Arbitrage signalant le nombre d'*Anchor Cards* en attente de décision humaine (Story 3.4)[cite: 2].
  * Un point d'état sur l'icône système reflétant la santé de la table Outbox et de la persistance DBOS[cite: 1, 2].
image suivante

Markdown
# Brief Écran 3 : Gestion Documentaire & Traitement des Données Personnelles (Page 4 du PDF)

## 1. Synthèse de l'Écran
* **Rôle principal :** Espace de téléversement et de gouvernance des documents partagés de l'équipe (`Documents Mon Compte`), intégrant un assistant méthodologique en volet latéral (*« Déposer un document, décider de ses données personnelles et vérifier qu'il répond »*)[cite: 7].
* **Fonctionnalité clé mise en avant :** Traitement de la conformité RGPD/confidentialité dès l'ingestion (classification C0-C2 vs C3, détection automatique des données personnelles et choix de pseudonymisation avant indexation)[cite: 7].

---

## 2. Décomposition de l'Interface

### Navigation Latérale (Sidebar Gauche)
* Reste déployée avec l'élément `Documents` actif sous la section `MON ESPACE`[cite: 7].

### Zone Principale (Gestion Documentaire)
* **En-tête contextuel :** Titre `Documents Mon Compte` avec sous-titre explicite (*« Tout ce qui alimente les réponses de Kore pour cette équipe »*)[cite: 7].
* **Zone de dépôt (Dropzone) :** Bouton/zone pour téléverser divers formats (PDF, Word, PowerPoint, Excel, texte, image, max 50 Mo)[cite: 7].
* **Compteurs de statut :**
  * `FICHIERS INDEXÉS : 0`[cite: 7]
  * `EN COURS : 0`[cite: 7]
* **État vide explicatif :** Message rassurant (*« Aucun fichier pour le moment — ni déposé par vous, ni partagé avec vous... »*)[cite: 7].

### Volet d'Assistance Latéral Droit (Guide Méthodologique en 5 Gestes)
* Estimation du temps de lecture/tâche (*« Environ 8 min »*)[cite: 7, 8].
* **Geste 1 — Déposer en choisissant classification et portée :** Niveaux de sécurité imposés (C0 à C2 acceptés, C3 refusé), portée privée (*Mes fichiers*) vs partagée (*Équipe*)[cite: 7].
* **Geste 2 — Décider des données personnelles détectées :** Pipeline de détection automatique des PII (noms, e-mails, téléphones, n° de sécurité sociale, secrets)[cite: 7]. Proposition d'arbitrage explicite : *Pseudonymiser* (remplacement par jetons), *Indexer tel quel* ou *Annuler*[cite: 7].
* **Geste 3 — Suivre le statut jusqu'à « Indexé »**[cite: 7].

---

## 3. Opportunités d'Amélioration & Transposition pour ORCIA

### A. Intégration Native d'une Gate de Confidentialité / RGPD (Story 3.5 & Core)
* **Constat :** KORE met l'ingestion en attente d'une décision humaine si des données sensibles ou des secrets sont détectés[cite: 7].
* **Opportunité ORCIA :** Rendre ce mécanisme complètement agnostique au sein d'ORCIA Core via le pipeline de **Gates déterministes** (Story 3.5)[cite: 2]. Lors de l'ingestion d'une source (Confluence, documents ou artefacts de spec), une règle de conformité PII/Secrets suspend l'indexation et génère une **Anchor Card** d'arbitrage (Story 3.4) pour valider la pseudonymisation ou le rejet avant persistance dans PostgreSQL/DBOS[cite: 1, 2, 7].

### B. Gouvernance par Portée et Niveau de Classification (C0 à C3)
* **Constat :** Les fichiers C3+ sont rejetés et la portée distingue strictement le privé de l'équipe[cite: 7].
* **Opportunité ORCIA :** Aligner le **Permission Broker** (Story 1.4) et le catalogue multi-sources (Story 1.3) pour associer des labels de classification formels aux nœuds de l'ontologie (Epic 2)[cite: 1, 2]. Un agent probabiliste exécuté par un Service Principal ne doit pouvoir requêter que les entités dont le niveau de classification correspond à son scope explicite[cite: 1, 2].

### C. Panneaux d'Aide Didactiques Intégrés (*Drawer / Sheet*)
* **Constat :** La présence d'un volet latéral détaillant la méthode pas-à-pas dédramatise les contraintes de sécurité pour l'utilisateur[cite: 7].
* **Opportunité ORCIA :** Intégrer dans les composants Radix/Tailwind de la SPA un composant de volet latéral contextuel (`<GuidanceDrawer />`)[cite: 1, 2] pour accompagner les utilisateurs dans le paramétrage des règles What-If, la rédaction de gabarits Spec-Kit ou le branchement de nouveaux connecteurs tiers[cite: 1, 2].
image suivante

Markdown
# Brief Écran 4 : Suite du Volet d'Aide & Vérification par Preuve (Page 5 du PDF)

## 1. Synthèse de l'Écran
* **Rôle principal :** Suite du volet d'assistance méthodologique pour la gestion documentaire, centré sur la validation fonctionnelle d'un dépôt (*« Vérifier qu'il répond »*), complété par une étude de cas concrète (*« Un exemple réel »*) et une alerte sur les pièges fréquents (*« Ce qui coince souvent »*)[cite: 8].
* **Principe clé mis en avant :** La prise en compte d'un document ne se décrète pas sur un simple statut technique : elle se prouve par une question de contrôle dans le chat (obligation de citation explicite de la source)[cite: 8].

---

## 2. Décomposition de l'Interface

### Volet Latéral (Focus sur l'Aide Pratique)
* **Geste 5 — Vérifier qu'il répond :**
  * Consigne méthodologique : poser dans le chat une question dont la réponse ne peut provenir que du document déposé[cite: 8].
  * Critère de réussite : le document doit être formellement cité dans la réponse de l'IA pour considérer l'ingestion comme opérationnelle[cite: 8].
  * Extension multimodale : mention de la description et de l'indexation des captures d'écran de pages Confluence lorsque le budget de l'équipe le permet[cite: 8].
* **Encadré « Un exemple réel » (*La note de cadrage qui manquait*) :**
  * Cas concret : téléversement de `cadrage-adresse-v3.2.pdf` (classification C2, portée Équipe)[cite: 8].
  * Détection de données personnelles : détection de deux adresses e-mail, choix de l'action `Pseudonymiser`[cite: 8].
  * Validation par l'usage : question posée dans le chat deux minutes plus tard, réponse confirmée avec citation de la source[cite: 8].
* **Section « Ce qui coince souvent » :**
  * Avertissement pragmatique sur les PDF scannés dépourvus de couche texte (problème récurrent d'ingestion RAG / OCR)[cite: 8].

---

## 3. Opportunités d'Amélioration & Transposition pour ORCIA

### A. Intégration du Test de Réciprocité dans les Parcours d'Initialisation (Story 1.5)
* **Constat :** L'interface encourage l'utilisateur à vérifier immédiatement que la source est exploitable via une question ciblée[cite: 8].
* **Opportunité ORCIA :** Dans le cadre des assistants d'initialisation (*bootstrapping wizards*), intégrer une étape de **test à blanc automatique (*Healthcheck RAG*)**[cite: 2]. Dès qu'une source (Confluence, Spec-Kit Markdown, tickets Jira) est indexée, le moteur exécute une micro-requête de validation déterministe sous DBOS confirmant que le graphe ontologique L1-L4 restitue bien les nœuds attendus avec leurs citations[cite: 1, 2].

### B. Traçabilité Stricte & Non-Répudiation des Citations
* **Constat :** Une réponse n'est réputée valide que si la source est formellement référencée[cite: 8].
* **Opportunité ORCIA :** Aligner cette exigence sur les **Anchor Cards** (Story 3.4) et l'audit trail append-only[cite: 1, 2] : lorsqu'un agent de revue (*Blind Hunter* ou *Edge Case Hunter*) émet une alerte critique, il doit obligatoirement ancrer sa justification sur un identifiant de spec, une ligne de code ou un ticket Jira précis, éliminant tout commentaire spéculatif sans source[cite: 1, 2].

### C. Gestion Proactive des Échecs d'Ingestion (OCR & Parsing)
* **Constat :** Les fichiers scannés sans texte génèrent des blocages fréquents[cite: 8].
* **Opportunité ORCIA :** Intégrer un linter d'ingestion immédiat côté backend. Si un artefact déposé contient zéro métadonnée exploitable ou souffre d'un format corrompu, la plateforme remonte une erreur bloquante explicite (*Fail-Fast*) avec recommandation corrective, sans encombrer la file d'attente d'indexation différentielle[cite: 1, 2].
image suivante

Markdown
# Brief Écran 5 : Hub de Gestion des Workflows - État Brouillon (Page 6 du PDF)

## 1. Synthèse de l'Écran
* **Rôle principal :** Console centrale de gestion, de publication et de suivi des chaînes d'automatisation de l'équipe (`Workflows Mon Compte`)[cite: 9].
* **Contexte & État affiché :** Présentation d'un catalogue comportant 1 workflow en cours de conception (état brouillon) sans aucun workflow encore publié ou exécuté en production[cite: 9].

---

## 2. Décomposition de l'Interface

### En-tête de Section & Compteurs de Métriques
* **Titre & Rôle :** `Workflows Mon Compte` — *« Gérez, publiez et suivez les workflows de l'équipe »*[cite: 9].
* **Actions globales d'en-tête :** Bouton `Exécutions` (historique des runs) et bouton primaire `+ Nouveau workflow`[cite: 9].
* **Cartouches d'indicateurs de volumétrie :**
  * `WORKFLOWS : 1` (total enregistré)[cite: 9].
  * `PUBLIÉS : 0`[cite: 9].
  * `BROUILLONS : 1`[cite: 9].
  * `EXÉCUTIONS ACTIVES : 0` (runs en direct)[cite: 9].

### Filtres d'Onglets & Moteur de Recherche
* **Segmentation par état :** Onglets `Publiés (0)`, `Brouillons (1)` (sélectionné par défaut), `Corbeille (0)`[cite: 9].
* **Champ de filtre textuel :** Barre de recherche rapide *« Rechercher un workflow... »*[cite: 9].

### Zone Principale (Contenu & Message Didactique)
* **Bandeau didactique d'état vide (*Guidance Banner*) :**
  * Explication de la règle métier : *« Aucun workflow publié. Un workflow enchaîne ce que vous refaites chaque semaine ; il reste en brouillon tant qu'il n'est pas publié, et c'est la publication qui le rend invocable depuis le chat. »*[cite: 9]
* **Bannière d'alerte OCR supérieure (reliquat de la page précédente) :**
  * Rappel de validation : rejet des pages blanches ou images sans texte (`0 caractère extrait`)[cite: 9].

---

## 3. Opportunités d'Amélioration & Transposition pour ORCIA

### A. Cycle de Vie Formel des Workflows-as-Code (Story 3.1 & Core)
* **Constat :** KORE formalise une frontière nette entre la conception (brouillon éditable) et la mise à disposition (publié / invocable)[cite: 9].
* **Opportunité ORCIA :** Dans le registre des workflows d'ORCIA, matérialiser ce cycle de vie avec versioning sémantique immuable (`Draft` $\rightarrow$ `Validated (What-If)` $\rightarrow$ `Published vX.Y.Z`)[cite: 1, 2]. Un workflow ne devient exécutable par le moteur DBOS en environnement nominal que s'il a passé avec succès une validation syntaxique et ontologique complète (Story 3.5)[cite: 1, 2].

### B. Métriques Opérationnelles & Supervision DBOS en Direct
* **Constat :** Les compteurs mettent immédiatement en avant les exécutions actives (`0`)[cite: 9].
* **Opportunité ORCIA :** Transposer ces indicateurs au moteur durable DBOS :
  * `Workflows enregistrés` (définitions YAML actives)[cite: 1, 2].
  * `Workflows en cours d'exécution` (instances DBOS non terminées)[cite: 1, 2].
  * `Workflows suspendus en attente d'arbitrage` (*Anchor Cards* actives, Story 3.4)[cite: 2].
  * Ce compteur de suspensions humaines offre un accès direct aux points de blocage pour les managers et tech leads[cite: 1, 2].

### C. Guidance Contextuelle sur les Règles de Publication
* **Constat :** Le texte sous les onglets clarifie la conséquence concrète d'une publication (rendre le workflow invocable dans le chat)[cite: 9].
* **Opportunité ORCIA :** Insérer des bannières pédagogiques similaires dans la SPA TanStack Router pour expliquer comment les workflows sont exposés : soit en déclenchement interactif (via la commande de prompt ou le panneau de commandes), soit via des webhooks/Service Principals (Story 1.4), soit via des événements Outbox (Story 3.2c)[cite: 1, 2].
image suivante

Markdown
# Brief Écran 6 : Vue Carte d'un Workflow en Brouillon (Page 7 du PDF)

## 1. Synthèse de l'Écran
* **Rôle principal :** Présentation sous forme de carte (*Workflow Card*) d'un workflow en cours d'élaboration au sein de l'onglet `Brouillons (1)`[cite: 10].
* **Composant mis en valeur :** Synthèse visuelle compacte de la chaîne de traitement (date, version, composition en étapes, mini-graphe) et actions de cycle de vie directes (`Publier`, `Modifier`)[cite: 10].

---

## 2. Décomposition de l'Interface

### Carte de Workflow Brouillon
* **Identité & Versioning :**
  * Indicateur d'état visuel : puce verte suivie du libellé `Brouillon du 15/10/2026 12:19` et de la mention de version `v1`[cite: 10].
  * Badge d'état à droite : `Brouillon`[cite: 10].
* **Aperçu Visuel du Graphe (*Mini-Map / Graph Preview*) :**
  * Miniature centrale stylisée matérialisant les nœuds et connexions du workflow (icônes des différents types d'étapes interconnectées)[cite: 10].
* **Métadonnées d'exécution :**
  * Compteur d'étapes : `7 étapes` avec pictogramme d'embranchement/flux[cite: 10].
  * Historique d'usage : mention explicite `Jamais exécuté`[cite: 10].
* **Actions Opérationnelles :**
  * Bouton d'action primaire : `Publier` (pour basculer le brouillon en production invocable)[cite: 10].
  * Bouton d'édition : `Modifier` (accès direct au canvas d'édition de graphe)[cite: 10].
  * Menu contextuel : bouton d'options secondaires `...` (dupliquer, exporter, supprimer vers la corbeille)[cite: 10].

---

## 3. Opportunités d'Amélioration & Transposition pour ORCIA

### A. Rendu Visuel des Pipeline Gates sur la Carte de Workflow
* **Constat :** KORE affiche le nombre d'étapes (`7 étapes`) et une miniature du graphe[cite: 10].
* **Opportunité ORCIA :** Enrichir cette carte avec la décomposition des types d'étapes propres à ORCIA (Story 3.2f) :
  * Décompte explicite : *X steps déterministes*, *Y steps agents LLM*, *Z gates de validation* (Story 3.5)[cite: 2].
  * Affichage d'un badge indiquant la posture de contrôle : par exemple `Gates : Mode Strict (Blind Hunter actif)` ou `Mode Permissif`[cite: 1, 2].

### B. Action de « Simulation à Blanc » (*Dry-Run What-If*) avant Publication
* **Constat :** L'interface propose directement de `Publier` sans étape formelle de validation préalable[cite: 10].
* **Opportunité ORCIA :** Introduire un bouton intermédiaire **« Tester l'impact (What-If) »** (Story 3.5)[cite: 2]. Avant d'autoriser la publication d'un workflow sous DBOS, l'utilisateur peut déclencher une simulation dans le bac à sable éphémère pour vérifier qu'aucune dépendance d'API n'est brisée, que les schémas d'I/O sont valides et qu'aucun dépassement de quota de tokens n'est prévisible[cite: 1, 2].

### C. Séparation des Droits sur la Carte (Lecture vs Modification)
* **Constat :** Les boutons `Publier` et `Modifier` sont visibles par défaut[cite: 10].
* **Opportunité ORCIA :** Conditionner l'affichage via le pattern de sécurité de l'Epic 8 :
  * Un utilisateur disposant du rôle `workflows:read` (auditeur/observateur) visualise la carte, le mini-graphe et les métadonnées, mais les boutons `Publier` et `Modifier` sont masqués ou remplacés par un bouton `Consulter le graphe (Lecture seule)`[cite: 1, 2].
  * Seul le rôle `workflows:write` ou `workflows:admin` accède aux actions d'édition et de publication[cite: 1, 2].
image suivante

Markdown
# Brief Écran 7 : Studio d'Édition de Workflow Visuel (Page 8 du PDF)

## 1. Synthèse de l'Écran
* **Rôle principal :** Éditeur graphique de graphe de workflow (*Workflow Canvas / Studio*), permettant de composer visuellement une séquence d'étapes d'ingénierie logicielle et de gouvernance[cite: 11].
* **Composants clés :** Panneau de bibliothèque d'outils et d'étapes à gauche, zone de modélisation centrale avec nœuds configurables, et barre d'actions de gouvernance supérieure (`Bibliothèque`, `Pré-prompt`, `Contrat`, `Déclencheurs`, `Tester`, `Publier`)[cite: 11].

---

## 2. Décomposition de l'Interface

### Barre Supérieure d'Édition & Gouvernance
* **Fil d'Ariane & Titre :** Retour vers `← Workflows` avec libellé éditable du draft (`Brouillon du 15/10/2026 12:19`)[cite: 11].
* **Outils transverses du workflow :**
  * `Bibliothèque (1)` : accès aux modèles et sous-graphes réutilisables[cite: 11].
  * `Pré-prompt` : injection d'un prompt système global appliqué à toutes les étapes IA du workflow[cite: 11, 18].
  * `Contrat` : définition formelle des schémas d'entrée/sortie et du livrable attendu[cite: 11, 19].
  * `Déclencheurs` : configuration des planifications et webhooks d'amorçage[cite: 11, 21].
  * Actions d'exécution : bouton secondaire `▷ Tester` et bouton primaire `Publier`[cite: 11].

### Palette Latérale Gauche (Outils & Briques Élémentaires)
* **Barre de recherche :** `Rechercher un outil...`[cite: 11].
* **Catégorie « ÉTAPES » (Objets Métier / Artefacts SDLC) :**
  * Badges d'artefacts déplaçables : `EPIC`, `Fonctionnalité`, `User story`, `Tech story`, `Analyse`, `Résumé`, `Décision`[cite: 11].
* **Catégorie « OPÉRATIONS » (Connecteurs & Actions Déterministes) :**
  * Actions Jira : `Jira - recherche`, `Jira - hiérarchie`[cite: 11].
  * Actions Confluence : `Confluence - lire une page`[cite: 11].
  * Actions GitLab : `GitLab - arborescence`, `GitLab - lire un fichier`[cite: 11].
  * Utilitaires de données : `Filtrer`, `Trier`[cite: 11].

### Canvas Central (Nœuds du Graphe)
* **Nœud « FEATURE / Fonctionnalité » :**
  * En-tête : badge de type `FEATURE`, champ de titre `Fonctionnalité`, icône corbeille (suppression)[cite: 11].
  * Sélecteur de modèle LLM : `Par défaut (équipe)`[cite: 11].
  * Sélecteur d'effort cognitif : `Effort par défaut`[cite: 11, 13].
  * Bouton d'accès aux réglages avancés : `Paramètres`[cite: 11].
* **Nœud « EPIC / EPIC » :**
  * Structure identique avec configuration dédiée pour la génération ou l'analyse d'une Epic[cite: 11].
* **Contrôles de Canvas (en bas à droite) :** Zoom (`100%`), boutons `+ / -`, centrage et affichage plein écran[cite: 11].

---

## 3. Opportunités d'Amélioration & Transposition pour ORCIA

### A. Représentation Graphique Bimodale : Déterministe vs Probabiliste (Story 3.2f)
* **Constat :** KORE mélange visuellement les artefacts conceptuels (`EPIC`, `User story`) et les opérations concrètes de connecteurs (`GitLab`, `Jira`) dans des styles de nœuds très proches[cite: 11].
* **Opportunité ORCIA :** Dans le canvas TanStack Router / React Flow d'ORCIA, formaliser une distinction visuelle stricte entre :
  * Les **Steps Déterministes** (`Program Executor` : icône d'outils, couleur solide, coût token nul)[cite: 2].
  * Les **Steps Probabilistes** (`Agent Executor` : badge de modèle LLM, jauge d'effort/budget tokens)[cite: 2].
  * Cette séparation clarifie immédiatement le coût et le déterminisme de la chaîne d'exécution[cite: 2].

### B. Intégration Visuelle des Gates Inter-Steps (Story 3.5)
* **Constat :** Les liens entre nœuds sont de simples flux séquentiels sans point de contrôle explicite visible[cite: 11].
* **Opportunité ORCIA :** Insérer sur chaque connecteur entre deux nœuds une **icône de Gate (porte de contrôle)** cliquable[cite: 2] :
  * Permet d'ajouter une ou plusieurs règles d'évaluation d'impact (validation de schéma OpenAPI, invariants ontologiques, ou agent contradictoire comme *Blind Hunter*)[cite: 1, 2].
  * Matérialiser l'embranchement conditionnel vers l'**Anchor Card** humaine (Story 3.4) directement sur le canvas si le risque dépasse le seuil défini[cite: 2].

### C. Synchronisation Bidirectionnelle « Canvas Graph ↔ YAML Spec-Kit » (Story 3.1)
* **Constat :** L'éditeur fonctionne uniquement en mode boîte noire visuelle[cite: 11].
* **Opportunité ORCIA :** Implémenter un mode bi-directionnel *« Split View (Graphique / Code YAML) »* fidèle à la philosophie *Documentation as Code* :
  * Toute manipulation sur le canvas met à jour le fichier YAML `Workflow-as-Code` conforme au schéma Pydantic d'ORCIA[cite: 1, 2].
  * Réciproquement, toute modification du YAML dans l'éditeur de texte recharge dynamiquement le graphe visuel[cite: 2].

### D. Contrôle d'Accès d'Édition sur le Studio (Epic 8)
* **Constat :** L'écran est d'emblée en mode écriture/modification[cite: 11].
* **Opportunité ORCIA :** Pour un profil auditeur ou observateur (`workflows:read`), verrouiller le canvas en mode navigation/inspection (nœuds non déplaçables, champs désactivés, boutons `Paramètres` ouvrant des fiches informatives en lecture seule, masquage de `Publier` et `Tester`)[cite: 1, 2].
image suivante

Markdown
# Brief Écran 8 : Sélection du Modèle LLM d'une Étape (Page 9 du PDF)

## 1. Synthèse de l'Écran
* **Rôle principal :** Configuration fine du moteur d'inférence (LLM) assigné à un nœud spécifique du workflow (`FEATURE Fonctionnalité`)[cite: 10].
* **Composant mis en valeur :** Menu déroulant contextuel proposant une sélection de modèles de fondation calibrés selon l'usage attendu (vitesse vs profondeur d'analyse vs spécialisation métier)[cite: 10].

---

## 2. Décomposition de l'Interface

### Nœud d'Étape (« FEATURE Fonctionnalité »)
* **Barre d'outils contextuelle supérieure :** Icônes de bascule d'affichage (vue formulaire vs vue couches/layers)[cite: 10].
* **En-tête du nœud :** Badge de type d'artefact `FEATURE`, champ de titre éditable `Fonctionnalité` et icône corbeille (suppression)[cite: 10].
* **Points d'ancrage (Ports de connexion) :** Connecteur d'entrée à gauche (gris) et connecteur de sortie à droite (bleu) matérialisant les flux d'entrées/sorties du graphe[cite: 10].

### Sélecteur Déroulant de Modèles (« Modèle »)
* **Option d'héritage :**
  * `Par défaut (équipe)` : hérite du modèle configuré au niveau du projet ou de l'espace de travail[cite: 10].
* **Options de modèles spécialisés avec qualificatifs d'usage :**
  * `Claude Haiku 5.5 (rapide)` : optimisé pour les tâches simples, rapides et à faible latence/coût[cite: 10].
  * `Claude Opus 5.5 (profond)` : réservé au raisonnement complexe, à l'analyse d'architecture ou aux décisions critiques[cite: 10].
  * `GPT 6.1 Sol (discovery, marché)` : étiqueté pour l'exploration, l'analyse concurrentielle et la découverte produit[cite: 10].

---

## 3. Opportunités d'Amélioration & Transposition pour ORCIA

### A. Qualification des Modèles par « Intent » et Gestion des Quotas (Story 3.2f & Epic 8)
* **Constat :** Les modèles sont qualifiés par des mentions explicites et pragmatiques (`rapide`, `profond`, `discovery, marché`) plutôt que par des noms de versions bruts[cite: 10].
* **Opportunité ORCIA :** Dans le panneau de configuration des steps probabilistes (`Agent Executor`)[cite: 2], proposer une sélection de modèles basée sur des **profils d'exécution d'entreprise** :
  * Profils clairs : *Économique / Linter* (modèles compacts), *Standard / Rédaction* (modèles intermédiaires), *Raisonnement Profond / Audit* (modèles avancés) ou *Souverain On-Premise* (modèles hébergés en interne).
  * Afficher dynamiquement le **coût estimé en tokens/crédits** et le quota restant de l'équipe pour responsabiliser le concepteur du workflow[cite: 1].

### B. Gouvernance des Modèles par Habilitations (RBAC / Permission Broker)
* **Constat :** Tout modèle de la liste déroulante semble sélectionnable librement[cite: 10].
* **Opportunité ORCIA :** Appliquer les politiques de l'Epic 8 (`/settings/ai-models`) :
  * Si l'équipe ou le rôle n'a pas le droit d'utiliser des modèles très coûteux (ex. modèles lourds sans quota autorisé), ces options apparaissent grisées avec une infobulle explicative (*« Nécessite le rôle ai:tier3 ou un budget débloqué »*).
  * En mode consultation stricte (`workflows:read`), le sélecteur est un simple badge statique non modifiable[cite: 1, 2].

### C. Couplage du Modèle avec les Gates Contradictoires (Story 3.5)
* **Constat :** Le choix du modèle ne concerne que la génération du contenu de l'étape[cite: 10].
* **Opportunité ORCIA :** Permettre de dissocier le modèle de **génération** (step nominal) du modèle de **contrôle** (gate probabiliste / agent contradictoire)[cite: 2] :
  * Pour éviter le biais d'auto-complaisance, imposer ou recommander qu'un agent de challenge (*Blind Hunter*) s'exécute sur une famille de modèle différente de celle ayant produit l'artefact (ex. génération avec un modèle de synthèse, audit contradictoire avec un modèle de raisonnement strict)[cite: 1, 2].
image suivante

Markdown
# Brief Écran 9 : Réglage du Niveau d'Effort Cognitif (Page 10 du PDF)

## 1. Synthèse de l'Écran
* **Rôle principal :** Paramétrage de la profondeur de calcul et du budget de réflexion (*Reasoning / Effort Level*) pour le nœud d'étape `FEATURE Fonctionnalité`[cite: 11].
* **Composant mis en valeur :** Menu déroulant contextuel proposant une graduation claire de l'intensité d'analyse attribuée à l'agent IA[cite: 11].

---

## 2. Décomposition de l'Interface

### Nœud d'Étape (« FEATURE Fonctionnalité »)
* **État du formulaire :**
  * Champ `Fonctionnalité` renseigné[cite: 11].
  * Sélecteur de modèle positionné sur `Par défaut (équipe)`[cite: 11].
* **Sélecteur déroulant « Effort » :**
  * `Effort par défaut` : applique la politique globale héritée du projet ou du workflow[cite: 11].
  * `Rapide` : exécution directe à faible coût, privilégiant la réactivité sans chaînes de pensée étendues[cite: 11].
  * `Équilibré` : compromis standard entre profondeur d'analyse et temps d'exécution[cite: 11].
  * `Approfondi` : allocation maximale de tokens de réflexion (*CoT / Extended Thinking*) pour explorer les dépendances, contraintes et cas limites[cite: 11].
* **Indication de parcours :** Mention textuelle inférieure *« Clic sur Paramètres : »* guidant vers l'étape de configuration suivante[cite: 11].

---

## 3. Opportunités d'Amélioration & Transposition pour ORCIA

### A. Formalisation des Paliers d'Effort dans le Schéma Workflow-as-Code (Story 3.1 & 3.2f)
* **Constat :** KORE propose une abstraction intuitive (`Rapide`, `Équilibré`, `Approfondi`) plutôt que d'exposer des paramètres bruts et techniques (comme `temperature` ou `max_thinking_tokens`)[cite: 11].
* **Opportunité ORCIA :** Normaliser ces niveaux dans le descripteur YAML d'un workflow (`effort: low | medium | high | reasoning_max`)[cite: 1, 2, 11]. Dans ORCIA, ces profils traduisent automatiquement les directives pour DBOS et l'exécuteur d'agent (`Agent Executor`) :
  * `Rapide` : température basse, absence de chaîne de pensée lourde, timeout DBOS court[cite: 1, 2, 11].
  * `Approfondi` : activation du mode réflexion multi-passes, temps d'exécution élargi avec checkpoints intermédiaires sous DBOS[cite: 1, 2, 11].

### B. Corrélation avec les Gates Probabilistes & Simulation What-If (Story 3.5)
* **Constat :** L'effort est défini isolément sans lien avec les risques de l'étape[cite: 11].
* **Opportunité ORCIA :** Lier dynamiquement le niveau d'effort recommandé aux règles de la **Gate d'impact**[cite: 2] :
  * Si une étape manipule des données sensibles ou des modifications d'architecture L1-L4 critiques, l'interface ORCIA peut imposer ou suggérer le mode `Approfondi`[cite: 1, 2, 11].
  * Réciproquement, la simulation *What-If* peut alerter l'utilisateur si une étape critique est configurée en mode `Rapide`, signalant un risque accru d'hallucination ou d'omission[cite: 2, 11].

### C. Gestion des Budgets d'Équipe et Habilitations (Epic 8)
* **Constat :** Le choix d'un effort élevé impacte directement les temps et coûts d'inférence[cite: 11].
* **Opportunité ORCIA :** Dans le module `/settings/ai-models` (Epic 8), permettre aux administrateurs de définir des plafonds d'effort par rôle (ex. restreindre le mode `Approfondi` aux rôles Architecte et Tech Lead) ou de bloquer le mode intensif lorsque le budget mensuel de tokens de l'équipe est dépassé[cite: 1, 11].
image suivante

Markdown
# Brief Écran 10 : Modale de Configuration des Instructions de l'Étape (Page 11 du PDF)

## 1. Synthèse de l'Écran
* **Rôle principal :** Modale de paramétrage fin de l'étape (`FEATURE Fonctionnalité`), ouverte suite au clic sur l'action `Paramètres`[cite: 11, 12].
* **Composant mis en valeur :** Dialogue modal permettant d'associer un modèle dédié et de saisir des instructions textuelles spécifiques pour piloter l'agent sur cette étape particulière[cite: 12].

---

## 2. Décomposition de l'Interface

### Modale « FEATURE Fonctionnalité »
* **En-tête :** Badge de type `FEATURE`, titre de l'étape `Fonctionnalité` et croix de fermeture `✕`[cite: 12].
* **Modèle de l'étape :** Menu déroulant affichant `Par défaut (équipe)`[cite: 12].
* **Modèles secondaires / complémentaires :** Menu déroulant avec placeholder `Choisir un modèle...`[cite: 12].
* **Zone de saisie des instructions (« Instruction ») :**
  * Zone de texte multiligne avec placeholder `Instruction (optionnel)...`[cite: 12].
  * Note explicative d'usage : *« Ajoutée à l'étape pour guider l'agent. »*[cite: 12]
* **Pied de modale :** Bouton d'action primaire `Enregistrer`[cite: 12].

---

## 3. Opportunités d'Amélioration & Transposition pour ORCIA

### A. Injection Déclarative des Instructions dans le Workflow-as-Code (Story 3.1 & 3.2f)
* **Constat :** KORE propose un champ texte libre pour consigner des instructions ad-hoc au niveau du nœud[cite: 12].
* **Opportunité ORCIA :** Dans ORCIA, standardiser cette configuration sous forme de directives déclaratives :
  * Possibilité de saisir soit un prompt textuel inline, soit une référence vers un fichier Markdown versionné (ex. `prompt_ref: "prompts/features/spec_generator.md"`).
  * Cette approche respecte le principe *Documentation-as-Code* tout en maintenant la modale accessible pour l'édition rapide.

### B. Contrôle d'Accès et Masquage selon les Droits (Epic 8)
* **Constat :** La modale s'ouvre par défaut en mode édition avec le bouton `Enregistrer` actif[cite: 12].
* **Opportunité ORCIA :** Appliquer le pattern `<PermissionGuard />` de l'Epic 8 :
  * En mode lecture (`workflows:read`), la zone d'instruction est affichée sous forme de bloc Markdown rendu en lecture seule, les sélecteurs de modèles sont désactivés et le bouton `Enregistrer` est masqué.
  * Seul un utilisateur disposant du rôle `workflows:write` peut modifier le prompt et valider les changements.

### C. Validation de Syntaxe et Détection de Variables dans les Instructions
* **Constat :** Le champ est une simple zone de texte sans assistance de saisie[cite: 12].
* **Opportunité ORCIA :** Intégrer un linter interactif avec auto-complétion des variables contextuelles d'ORCIA (ex. `{feature_id}`, `{actor}`, `{ontology_scope}`) afin d'éviter les erreurs de templating avant l'exécution durable sous DBOS.
image suivante

Markdown
# Brief Écran 11 : Vue des Couches de l'Étape (Page 12 du PDF)

## 1. Synthèse de l'Écran
* **Rôle principal :** Menu contextuel et inspecteur de couches (*Layers Inspector / Couches*), ouvert depuis l'icône de superposition présente dans la barre d'outils du nœud `FEATURE Fonctionnalité`[cite: 13].
* **Composant mis en valeur :** Volet compact listant les 7 sous-éléments, artefacts ou opérations constituant la pile de traitement interne de cette étape[cite: 13].

---

## 2. Décomposition de l'Interface

### Nœud d'Étape (« FEATURE Fonctionnalité »)
* **Barre d'outils contextuelle :** Bouton de bascule vers la vue calques/couches activé (contour noir mis en surbrillance)[cite: 13].
* **Composants d'arrière-plan :** Nœud de configuration avec titre, sélecteurs déroulants et connecteur de sortie bleu[cite: 13].

### Menu Flottant (« COUCHES · 7 »)
* **En-tête :** Libellé `COUCHES · 7` avec croix de fermeture `✕`[cite: 13].
* **Pile verticale ordonnée des couches :**
  1. `EPIC` (drapeau violet)[cite: 13].
  2. `Jira — recherche` (connecteur opérationnel / outil)[cite: 13].
  3. `EPIC` (drapeau violet)[cite: 13].
  4. `User story` (cible verte)[cite: 13].
  5. `Analyse` (loupe jaune)[cite: 13].
  6. `Résumé` (document texte noir)[cite: 13].
  7. `Fonctionnalité` (étoile/badge bleu)[cite: 13].

---

## 3. Opportunités d'Amélioration & Transposition pour ORCIA

### A. Représentation de la Hiérarchie et Composition des Sous-Étapes (Story 3.2f)
* **Constat :** KORE permet d'empiler plusieurs opérations et artefacts au sein d'un même conteneur visuel pour éviter de surcharger le graphe principal[cite: 13].
* **Opportunité ORCIA :** Adopter ce concept pour modéliser des **Macro-Steps (Sous-Workflows)** dans le moteur DBOS[cite: 1, 2] :
  * Un conteneur d'étape unique dans le canvas visuel peut encapsuler un pipeline complet (ex. *Récupération Jira $\rightarrow$ Analyse d'impact $\rightarrow$ Rédaction Spec Markdown*).
  * L'inspecteur de couches permet de visualiser et réordonner les micro-tâches internes sans éclater le graphe parent en dizaines de nœuds complexes.

### B. Distinction Visuelle des Entrées, Outils et Sorties dans la Pile
* **Constat :** La liste empile indifféremment des sources (`EPIC`), des outils déterministes (`Jira — recherche`) et des livrables finaux (`Résumé`, `Fonctionnalité`) sous un format uniforme[cite: 13].
* **Opportunité ORCIA :** Dans l'inspecteur d'ORCIA, structurer explicitement les couches en trois sections :
  * **Contexte d'entrée (Ontologie / Sources) :** Objets du graphe (ex. Epics parentes, contrats d'interface).
  * **Outils d'exécution (Capabilities) :** Connecteurs déterministes (CLI Git, requêtes Jira, linters).
  * **Artefacts produits (Deliverables) :** Spécifications Markdown, tickets générés ou rapports d'évaluation.

### C. Indicateurs d'État et Gates Internes aux Couches (Story 3.5)
* **Constat :** Les couches sont statiques et ne fournissent pas d'indicateur de validation ou de point d'arrêt[cite: 13].
* **Opportunité ORCIA :** Permettre de positionner une **Gate de contrôle** directement entre deux couches d'un même nœud :
  * Par exemple, insérer une vérification d'intégrité ontologique immédiatement après l'étape `Jira — recherche` avant de déclencher la couche d'analyse LLM, garantissant un échec rapide (*Fail-Fast*) au plus près de l'opération défaillante[cite: 2].
image suivante

Markdown
# Brief Écran 12 : Actions de Masquage et Suppression sur une Couche (Page 13 du PDF)

## 1. Synthèse de l'Écran
* **Rôle principal :** Gestion fine et manipulation contextuelle des couches au sein du menu flottant `COUCHES · 7` du nœud `FEATURE Fonctionnalité`[cite: 14].
* **Composant mis en valeur :** Survol interactif de la ligne `Jira — recherche` révélant deux actions unitaires de contrôle : l'icône de masquage/désactivation temporaire (œil barré) et l'icône de suppression définitive (corbeille)[cite: 14].

---

## 2. Décomposition de l'Interface

### Menu Contextuel Flottant (« COUCHES · 7 »)
* **État de la sélection :** La deuxième couche (`Jira — recherche`) est activement survolée et mise en évidence par un fond contrasté[cite: 14].
* **Actions contextuelles révélées au survol :**
  * **Icône œil barré (*Toggle Visibility / Disable*) :** Permet de désactiver ou masquer temporairement cette opération du flux d'exécution sans la supprimer de la définition[cite: 14].
  * **Icône corbeille (*Delete*) :** Permet de retirer définitivement la couche de la pile de traitement[cite: 14].
* **Autres éléments visibles dans la pile :** Les couches restantes (`EPIC`, `User story`, `Analyse`, `Résumé`, `Fonctionnalité`) demeurent en attente dans la liste ordonnée[cite: 14].

---

## 3. Opportunités d'Amélioration & Transposition pour ORCIA

### A. Désactivation Conditionnelle et « Bypass » d'une Étape dans DBOS (Story 3.2f)
* **Constat :** KORE propose un commutateur direct (œil barré) pour neutraliser une opération sans devoir la détruire et la recréer[cite: 14].
* **Opportunité ORCIA :** Transposer ce comportement dans la modélisation déclarative du workflow (`enabled: false` ou `condition: when_needed`) :
  * Permet d'ignorer temporairement un connecteur déterministe (par exemple une recherche Jira ou un crawl externe) lors des phases de prototypage ou de tests locaux, évitant ainsi des appels réseaux superflus.
  * Dans l'ordonnanceur DBOS, l'étape désactivée est logguée comme `SKIPPED` dans l'historique d'exécution tout en préservant l'intégrité de la séquence.

### B. Gouvernance et Droits de Modification Granulaires (Epic 8)
* **Constat :** Les actions de suppression et de désactivation sont immédiatement accessibles au survol[cite: 14].
* **Opportunité ORCIA :** Appliquer les contrôles RBAC/ABAC de l'Epic 8 :
  * Pour un utilisateur avec une habilitation en consultation seule (`workflows:read`), les icônes de corbeille et d'œil barré sont absentes ou verrouillées (tooltip : *« Droit workflows:write requis pour modifier la composition des couches »*).
  * En mode écriture, la suppression d'une étape impactant d'autres nœuds dépendants doit être précédée d'un avertissement ou d'une validation d'impact issue du bac à sable *What-If* (Story 3.5).

### C. Réordonnancement Interactif par Glisser-Déposer (*Drag-and-Drop*)
* **Constat :** La pile de couches suggère un ordre séquentiel vertical strict[cite: 14].
* **Opportunité ORCIA :** Intégrer une poignée de glissement (*drag handle*) sur chaque couche dans la SPA (TanStack Router + Radix) afin de réordonner visuellement la priorité des étapes (par exemple exécuter la recherche Jira avant l'injection de l'analyse ou inversement), avec mise à jour immédiate du schéma YAML sous-jacent.
image suivante

Markdown
# Brief Écran 13 : Panneau Latéral des Permissions, Ressources et Actions (Page 14 du PDF)

## 1. Synthèse de l'Écran
* **Rôle principal :** Volet de configuration des entrées/sorties et des autorisations d'outils rattaché à l'étape (`FEATURE Fonctionnalité`) ou au workflow global[cite: 15].
* **Composants mis en valeur :** Définition des documents de sortie autorisés, ciblage des ressources documentaires internes et attribution granulaire des droits de lecture/écriture sur les connecteurs d'entreprise (Confluence, Jira)[cite: 15].

---

## 2. Décomposition de l'Interface

### Volet Latéral Gauche de Paramétrage
* **Section « Document de sortie » :**
  * Sélecteur de format/destination avec bouton `Limiter`[cite: 15].
  * Exemples d'options : `Jira — brouillon de ticket`, `Confluence — brouillon de page`[cite: 15].
* **Section « RESSOURCES INTERNES » :**
  * Entrées de contexte documentaire : `Base de connaissances`, `Projet`[cite: 15].
* **Section « ACTIONS » (Permissions granulaires sur connecteurs) :**
  * **Confluence :** cases à cocher distinctes pour `Lire` et `Écrire`[cite: 15].
  * **Jira :** case à cocher pour `Lire` (et option d'écriture sous-jacente)[cite: 15].

### Arrière-plan (Rappel du Contexte)
* Présence superposée du menu des couches (`COUCHES · 7`) sur le nœud `FEATURE Fonctionnalité` au sein du canvas de workflow[cite: 15].

---

## 3. Opportunités d'Amélioration & Transposition pour ORCIA

### A. Principe du Moindre Privilège par Étape (Story 1.4 & Permission Broker)
* **Constat :** KORE propose une séparation explicite entre droits de consultation (`Lire`) et droits de modification (`Écrire`) sur chaque connecteur tiers pour limiter le champ d'action de l'agent[cite: 15].
* **Opportunité ORCIA :** Aligner cette configuration sur le **Permission Broker** d'ORCIA[cite: 2] :
  * Définir pour chaque `Agent Executor` (step probabiliste) un token de portée éphémère (*scoped execution token*)[cite: 2].
  * Si l'étape est paramétrée en lecture seule sur Jira/GitLab, toute tentative d'émission d'une mutation ou d'un appel d'API destructif est interceptée et bloquée par le moteur avant d'atteindre le réseau[cite: 1, 2].

### B. Encadrement Déclaratif des Artefacts de Sortie
* **Constat :** La section *Document de sortie* contraint la destination finale vers un brouillon supervisé (`Jira — brouillon de ticket`)[cite: 15].
* **Opportunité ORCIA :** Formaliser dans le schéma `Workflow-as-Code` le type d'artefact émis par le step (ex. *Markdown Spec-Kit L4*, *PR/MR Draft*, *Issue Jira en statut Draft*)[cite: 1, 2]. Couplé au bac à sable *What-If* (Story 3.5), cela garantit qu'aucun livrable n'est publié directement en production sans validation ou passage de Gate[cite: 2].

### C. Gestion des Droits UI sur le Panneau (Epic 8)
* **Constat :** Les cases à cocher `Lire` / `Écrire` permettent d'élargir les permissions de l'agent à la volée[cite: 15].
* **Opportunité ORCIA :** Dans l'Epic 8, restreindre l'attribution de droits `Écrire` aux seuls utilisateurs disposant eux-mêmes de la permission d'administration des connecteurs (`connectors:manage`)[cite: 1, 2]. Un utilisateur disposant uniquement de droits d'exécution ne peut pas accorder à un workflow des privilèges plus élevés que ses propres habilitations.
image suivante

Markdown
# Brief Écran 14 : Modale de Configuration du Pré-prompt IA (Page 15 du PDF)

## 1. Synthèse de l'Écran
* **Rôle principal :** Modale de saisie du **Pré-prompt IA** global rattaché à l'ensemble du workflow[cite: 18].
* **Composant mis en valeur :** Dialogue contextuel permettant d'injecter une consigne système transversale préalable, appliquée de façon systématique avant chaque étape d'exécution du graphe[cite: 18].

---

## 2. Décomposition de l'Interface

### Modale « Pré-prompt IA »
* **En-tête :** Icône étincelle/IA, titre `Pré-prompt IA` et croix de fermeture `✕`[cite: 18].
* **Description fonctionnelle :** Mention explicative *« Contexte ajouté avant chaque exécution du workflow. »*[cite: 18].
* **Zone de saisie textuelle :**
  * Champ de texte multiligne avec placeholder didactique : *« Ex. Réponds en français et cite les sources... »*[cite: 18].
  * Poignée de redimensionnement en bas à droite du conteneur de texte[cite: 18].
* **Pied de modale :** Bouton d'action primaire `Enregistrer`[cite: 18].
* **Arrière-plan :** Nœud de graphe (`EPIC`) et bouton d'action global `Publier` en fond grisé/flouté[cite: 18].

---

## 3. Opportunités d'Amélioration & Transposition pour ORCIA

### A. Modularité et « System Prompt as Code » (Story 3.1 & 3.2f)
* **Constat :** KORE propose une saisie textuelle libre globale dans une boîte modale simple[cite: 18].
* **Opportunité ORCIA :** Dans ORCIA, découpler et structurer cette injection système au sein du manifeste déclaratif (`Workflow-as-Code`) :
  * Permettre l'injection de directives par composition : consignes transverses d'entreprise (ex. règles RGPD, ton neutre, politique de sécurité interne) combinées à des consignes propres au workflow (ex. gabarit de spec technique ou d'arbitrage)[cite: 7].
  * Supporter le référencement direct d'un fichier Markdown versionné dans le dépôt (ex. `system_prompt_ref: "prompts/system/enterprise_guidelines.md"`) pour respecter la démarche *Documentation as Code*.

### B. Traçabilité et Auditabilité du Prompt dans DBOS (Stories 3.2b & 3.2c)
* **Constat :** La consigne globale s'applique sans trace visible de versioning ou d'impact immédiat[cite: 18].
* **Opportunité ORCIA :** Toute modification de ce pré-prompt doit être versionnée et enregistrée dans le checkpoint d'état immuable sous PostgreSQL/DBOS :
  * Garantir la reproductibilité stricte : deux exécutions d'un même workflow doivent garder en historique l'empreinte cryptographique exacte (SHA-256) du pré-prompt système utilisé lors de leur déclenchement.
  * Dans l'Outbox et l'audit trail de l'Epic 8, journaliser l'identité de l'auteur de chaque mise à jour du pré-prompt.

### C. Contrôle des Habilitations (RBAC / Permission Broker - Epic 8)
* **Constat :** Le champ est directement modifiable par quiconque ouvre la fenêtre[cite: 18].
* **Opportunité ORCIA :** Restreindre l'édition du pré-prompt via le composant `<PermissionGuard />` :
  * Pour un profil en consultation (`workflows:read`), afficher la consigne sous forme de bloc Markdown statique en lecture seule, avec masquage du bouton `Enregistrer`.
  * La modification (`workflows:write`) doit pouvoir être soumise à une Gate de validation préalable (vérifiant l'absence d'injonctions contradictoires ou de failles de sécurité de type *prompt injection*) avant publication définitive.
image suivante

Markdown
# Brief Écran 15 : Modale du Contrat de Workflow - Paramètres et Gabarit de Sortie (Page 16 du PDF)

## 1. Synthèse de l'Écran
* **Rôle principal :** Modale de définition formelle du **Contrat du workflow** accessible depuis l'action `Contrat` de la barre supérieure du studio[cite: 11, 19].
* **Principe clé mis en avant :** Cadrage strict des entrées attendues et de la structure du livrable pour garantir la reproductibilité et la comparabilité entre différentes exécutions (*« Ce qui rend deux exécutions comparables »*)[cite: 19].

---

## 2. Décomposition de l'Interface

### Modale « Contrat du workflow »
* **En-tête & Description :**
  * Icône de connecteurs / curseurs, titre `Contrat du workflow` et croix de fermeture `✕`[cite: 19].
  * Définition explicative : *« Ce qu'il attend en entrée, et la forme imposée de son livrable. C'est ce qui rend deux exécutions comparables. »*[cite: 19]

### Section « Paramètres » (Variables d'Entrée)
* **Bouton d'action :** `+ Ajouter` pour déclarer une nouvelle variable[cite: 19].
* **Consigne de templating :** *« Écrivez {nom} dans une instruction ou une configuration de nœud : la valeur y sera substituée au lancement. Sans valeur par défaut, le paramètre est requis et le workflow refuse de démarrer sans lui. »*[cite: 19]
* **État vide affiché :** Mention explicite *« Aucun paramètre : le workflow se lance tel quel. »*[cite: 19]

### Section « Gabarit de sortie » (Structure du Livrable)
* **Règle de restitution :** *« Les sections imposées au livrable. La synthèse finale les reprend telles quelles ; une section sans matière est signalée, jamais supprimée. »*[cite: 19]
* **Sections Markdown imposées au livrable :**
  * `## Synthèse`[cite: 19]
  * `## Avancement par EPIC`[cite: 19]
  * `## Risques`[cite: 19]
  * `## Décisions attendues`[cite: 19]

### Pied de Modale
* Bouton d'action primaire `Enregistrer`[cite: 19].

---

## 3. Opportunités d'Amélioration & Transposition pour ORCIA

### A. Formalisation de Schémas Stricts d'I/O (Pydantic / JSON Schema) (Story 3.1)
* **Constat :** KORE structure les paramètres en entrée et impose les sections du livrable de sortie sous forme de titres Markdown[cite: 19].
* **Opportunité ORCIA :** Dans ORCIA, adosser ce contrat à des schémas Pydantic / JSON Schema stricts dans le `Workflow-as-Code`[cite: 1, 2] :
  * Déclarer les inputs avec types, contraintes de validation et descriptions (ex. `feature_id: str`, `target_version: SemVer`).
  * Définir le gabarit de sortie comme un artefact ontologique ou un template Spec-Kit (OpenSpec) versionné dans le dépôt, garantissant l'intégrité des données avant injection dans la base PostgreSQL[cite: 1, 2].

### B. Contrôle d'Intégrité par Gate Déterministe au Runtime (Story 3.5)
* **Constat :** KORE signale si une section obligatoire manque de matière sans la supprimer[cite: 19].
* **Opportunité ORCIA :** Transformer cette vérification en une **Gate Déterministe de Conformité de Gabarit**[cite: 2] :
  * Si l'agent LLM omet une section obligatoire (ex. `## Risques` ou `## Décisions attendues`)[cite: 19], la Gate l'intercepte immédiatement.
  * Selon la sévérité configurée, le moteur déclenche soit un retry automatique avec consigne de correction, soit une suspension dans DBOS via une **Anchor Card** pour arbitrage humain (Story 3.4)[cite: 1, 2].

### C. Gestion des Droits sur le Contrat (Epic 8)
* **Constat :** La modale permet de redéfinir les paramètres et le gabarit de sortie du workflow[cite: 19].
* **Opportunité ORCIA :** Appliquer le contrôle d'accès RBAC :
  * Pour un profil en consultation (`workflows:read`), afficher les paramètres et le gabarit en lecture seule sans le bouton `+ Ajouter` ni le bouton `Enregistrer`[cite: 1, 2, 19].
  * La modification du contrat modifiant la signature publique du workflow, exiger le rôle `workflows:write` ou `workflows:admin` et journaliser l'opération dans la table Outbox pour notifier les consommateurs externes[cite: 1, 2].
image suivante

Markdown
# Brief Écran 16 : Ajout et Typage d'un Paramètre de Contrat (Page 17 du PDF)

## 1. Synthèse de l'Écran
* **Rôle principal :** Déclaration et configuration unitaire d'un paramètre d'entrée au sein de la modale `Contrat du workflow` suite au clic sur l'action `+ Ajouter`[cite: 20].
* **Composant mis en valeur :** Ligne de formulaire compacte permettant de définir le nom technique de la variable, sa description/placeholder, sa valeur par défaut optionnelle, son type de données ainsi qu'une action de suppression directe[cite: 20].

---

## 2. Décomposition de l'Interface

### Modale « Contrat du workflow »
* **En-tête & Description :**
  * Rappel du rôle d'uniformisation : *« Ce qu'il attend en entrée, et la forme imposée de son livrable. C'est ce qui rend deux exécutions comparables. »*[cite: 20].
* **Section « Paramètres » (Ligne d'attribut créée) :**
  * Consigne de substitution contextuelle : *« Écrivez {nom} dans une instruction ou une configuration de nœud : la valeur y sera substituée au lancement. Sans valeur par défaut, le paramètre est requis et le workflow refuse de démarrer sans lui. »*[cite: 20].
  * **Champ Nom technique :** `pi` (identifiant de variable injecté entre accolades)[cite: 20].
  * **Champ Libellé / Description :** `Program Increment ciblé` (aide à la saisie pour l'opérateur)[cite: 20].
  * **Champ Valeur par défaut :** `défaut (facultatif)` (placeholder)[cite: 20].
  * **Sélecteur de type :** Menu déroulant positionné sur `Texte`[cite: 20].
  * **Action de retrait :** Icône corbeille pour supprimer la variable déclarée[cite: 20].
* **Bouton d'ajout :** Bouton `+ Ajouter` actif pour insérer des paramètres additionnels[cite: 20].
* **Section inférieure :** Rappel de la zone `Gabarit de sortie`[cite: 20].

---

## 3. Opportunités d'Amélioration & Transposition pour ORCIA

### A. Typage Enrichi & Validation Stricte d'Ontologie (Story 3.1 & Core)
* **Constat :** KORE propose un typage textuel générique (`Texte`)[cite: 20].
* **Opportunité ORCIA :** Dans ORCIA, élargir le sélecteur de types aux primitives du Core et de l'Ontologie du SI[cite: 1, 2] :
  * Types scalaires standards : `String`, `Integer`, `Boolean`, `Enum`[cite: 20].
  * **Types ontologiques natifs :** `FeatureId`, `EpicKey`, `GitBranch`, `RepoRef`, `ServicePrincipal`[cite: 1, 2].
  * L'association d'un type ontologique permet au parseur Pydantic de vérifier instantanément dans PostgreSQL si l'entité référencée existe réellement avant d'engager les ressources du moteur d'exécution[cite: 1, 2].

### B. Inférence Automatique des Variables par Analyse Statique
* **Constat :** La variable doit être ajoutée manuellement après avoir été saisie sous forme `{nom}` dans les nœuds[cite: 20].
* **Opportunité ORCIA :** Intégrer une détection proactive : si l'utilisateur saisit `{epic_key}` ou `{sprint}` dans les instructions d'un step ou d'un prompt[cite: 12, 20], l'éditeur ORCIA propose automatiquement d'ajouter la variable correspondante au contrat d'entrée via une notification non bloquante.

### C. Contrôle RBAC sur la Déclaration du Contrat (Epic 8)
* **Constat :** Les champs de saisie et la corbeille sont directement modifiables[cite: 20].
* **Opportunité ORCIA :** Appliquer le composant `<PermissionGuard />` :
  * Pour le rôle `workflows:read`, rendre la ligne sous forme de tableau statique (badge `pi`, libellé, type et valeur par défaut en texte brut sans corbeille ni bouton d'ajout)[cite: 1, 2, 20].
  * Réserver l'édition aux détenteurs de `workflows:write`[cite: 1, 2].
image suivante

Markdown
# Brief Écran 17 : Configuration des Déclencheurs de Workflow (Page 18 du PDF)

## 1. Synthèse de l'Écran
* **Rôle principal :** Modale de configuration des **Déclencheurs** (*Triggers*), accessible depuis la barre d'outils supérieure du studio de workflow[cite: 11, 21].
* **Principe clé mis en avant :** Définition des conditions de démarrage autonome du workflow[cite: 21]. La modale combine une planification temporelle récurrente et des déclencheurs événementiels réactifs[cite: 21].

---

## 2. Décomposition de l'Interface

### Modale « Déclencheurs »
* **En-tête & Description :**
  * Icône éclair, titre `Déclencheurs` et bouton de fermeture `✕`[cite: 21].
  * Sous-titre fonctionnel : *« Choisissez quand ce workflow peut démarrer automatiquement. »*[cite: 21]

### Section « Planification » (Temporelle)
* **Boutons de périodicité :** `Aucune`, `Une fois`, `Chaque semaine`, `Intervalle` (actif / sélectionné en bleu foncé)[cite: 21].
* **Paliers de fréquence (pour « Intervalle ») :** `15 min`, `1 h`, `6 h` (sélectionné), `24 h`[cite: 21].
* **Texte explicatif dynamique :** *« Toutes les 6 h, à compter du dernier passage. »*[cite: 21]
* **Règle de sécurité affichée :** *« Seul un workflow publié démarre tout seul. Un PowerPoint attendu doit avoir son deck de référence (Contrat). »*[cite: 21]

### Section « Événements » (Réaction aux changements)
* **Cases à cocher événementielles :**
  * ☐ `Nouveau document indexé`[cite: 21]
  * ☐ `Source synchronisée`[cite: 21]

### Pied de Modale
* Bouton d'action principal `Enregistrer`[cite: 21].

---

## 3. Opportunités d'Amélioration & Transposition pour ORCIA

### A. Déclencheurs Événementiels pilotés par la Table Outbox (Story 3.2c)
* **Constat :** KORE propose deux déclencheurs génériques liés à la base documentaire (`Nouveau document indexé`, `Source synchronisée`)[cite: 21].
* **Opportunité ORCIA :** Dans ORCIA, coupler directement ces déclencheurs à l'**Outbox transactionnelle** et aux événements du domaine :
  * Déclencheurs liés au catalogue fédéré : `spec:created`, `spec:updated`, `jira:sprint_started`, `git:pr_opened`[cite: 1, 2].
  * Dès qu'un événement métier est validé dans PostgreSQL, le scheduler DBOS instancie de manière durable le workflow associé sans nécessiter de polling récurrent consommateur de ressources[cite: 1, 2].

### B. Planification Durable nativement gérée par DBOS
* **Constat :** La planification par intervalle (`15 min`, `1 h`, `6 h`, `24 h`) tourne comme un cron classique[cite: 21].
* **Opportunité ORCIA :** Exploiter les capacités de temporisation et de planification de **DBOS** :
  * Chaque déclencheur programmé bénéficie de la tolérance aux pannes native : en cas de redémarrage de l'instance ou de bascule de nœud, l'état du timer est conservé en base[cite: 1, 2].
  * Intégrer un mode d'alignement fin (ex. syntaxe Cron standardisée ou synchronisation avec le calendrier d'itérations SAFe / PI) pour déclencher automatiquement des audits de fin de sprint[cite: 5, 21].

### C. Contrôle RBAC sur l'Automatisation (Epic 8)
* **Constat :** Activer une automatisation toutes les 6 heures peut générer des coûts d'inférence LLM significatifs en production[cite: 21].
* **Opportunité ORCIA :** Restreindre l'activation des déclencheurs automatiques via le modèle d'habilitations de l'Epic 8 :
  * La modification des déclencheurs récurrents doit requérir la permission `workflows:triggers:manage` ou `workflows:write`[cite: 1, 2].
  * Pour un profil en consultation (`workflows:read`), la modale s'affiche en lecture seule (indicateurs statiques sans possibilité de basculer les boutons ni de cocher les événements)[cite: 1, 2, 21].
image suivante

Markdown
# Brief Écran 18 : Modale de Test Unitaire du Workflow (Page 19 du PDF)

## 1. Synthèse de l'Écran
* **Rôle principal :** Modale de déclenchement d'un test fonctionnel direct (*Dry-Run / Test Runner*), ouverte via le bouton `▷ Tester` de la barre supérieure du studio de workflow[cite: 11, 22].
* **Composant mis en valeur :** Dialogue modal simplifié permettant de soumettre une consigne ou une charge utile d'essai (*payload*) afin d'exécuter le workflow brouillon sans impacter l'état de production[cite: 22].

---

## 2. Décomposition de l'Interface

### Modale « Tester le workflow »
* **En-tête & Notification d'enregistrement :**
  * Titre explicite `Tester le workflow` et bouton de fermeture `✕`[cite: 22].
  * Avertissement contextuel de sauvegarde automatique : *« Le brouillon sera enregistré puis exécuté avec cette demande. »*[cite: 22]
* **Champ de saisie de la demande (« Demande ») :**
  * Zone de texte multiligne avec curseur actif[cite: 22].
  * Placeholder incitatif : *« Décrivez la demande à traiter par le workflow... »*[cite: 22]
* **Action d'amorçage :**
  * Bouton d'action primaire en pied de boîte : `▷ Lancer le test`[cite: 22].

---

## 3. Opportunités d'Amélioration & Transposition pour ORCIA

### A. Exécution Éphémère dans le Bac à Sable « What-If » (Story 3.5 & DBOS)
* **Constat :** KORE enregistre directement le brouillon courant et lance un test sans expliciter l'environnement d'isolation[cite: 22].
* **Opportunité ORCIA :** Coupler ce bouton de test au **moteur de simulation What-If** d'ORCIA[cite: 2] :
  * L'exécution s'opère dans un bac à sable transactionnel éphémère (*What-If Sandbox*) sous DBOS[cite: 2].
  * Tous les appels vers les connecteurs tiers (Jira, Git, Confluence) sont interceptés ou simulés en mode lecture stricte[cite: 1, 2, 15].
  * Aucun artefact n'est persisté en production tant que le test n'a pas été formellement validé par les Gates[cite: 2].

### B. Injection des Paramètres Structurés du Contrat
* **Constat :** L'écran propose une unique zone de texte libre générique (*« Demande »*), en contradiction relative avec la modale de contrat précédente qui formalisait des variables nommées (ex. `{pi}`)[cite: 20, 22].
* **Opportunité ORCIA :** Remplacer ou compléter le champ texte par un **formulaire dynamique généré à partir du contrat de workflow** (Story 3.1)[cite: 20] :
  * Si le contrat requiert `feature_id` ou `sprint_target`, afficher des inputs typés dédiés avec validation de schéma Pydantic avant envoi[cite: 1, 2, 20].
  * Proposer un sélecteur d'échantillons de test (*Presets / Fixtures*) issus de l'ontologie existante pour éviter la saisie manuelle répétitive[cite: 1, 2].

### C. Visualisation de l'Exécution Pas-à-Pas et des Gates
* **Constat :** Le dialogue se concentre uniquement sur le lancement sans montrer le retour d'exécution attendu[cite: 22].
* **Opportunité ORCIA :** Dès le clic sur `Lancer le test`, transformer le canvas du studio ou ouvrir un tiroir latéral affichant :
  * La progression pas-à-pas sous forme de télémétrie DBOS (statut des steps déterministes et probabilistes)[cite: 2].
  * L'état d'évaluation des **Gates** intermédiaires (vert / rouge)[cite: 2].
  * La génération simulée d'une **Anchor Card** si un arbitrage humain fictif est rencontré dans le flux de test[cite: 2].

### D. Contrôle d'Accès au Test (Epic 8)
* **Constat :** Le bouton de lancement de test consomme des ressources de calcul et de modèles d'inférence[cite: 10, 22].
* **Opportunité ORCIA :** Conditionner l'action `Lancer le test` à la permission `workflows:test` ou `workflows:write`[cite: 1, 2]. Pour un profil en lecture seule (`workflows:read`), le bouton est désactivé avec mention du quota restant ou de la permission requise[cite: 1, 2].
image suivante

Markdown
# Brief Écran 19 : Carte d'un Workflow Publié (Page 20 du PDF)

## 1. Synthèse de l'Écran
* **Rôle principal :** Présentation sous forme de carte d'un workflow ayant basculé avec succès dans l'état `Publié` au sein du catalogue d'équipe (`Workflows Mon Compte`)[cite: 23].
* **Composant mis en valeur :** Transition de statut de la carte : les compteurs passent à `PUBLIÉS : 1`, le workflow est classé dans l'onglet `Publiés 1` et le bouton d'action primaire devient `▷ Exécuter` (au lieu de `Publier`)[cite: 23].

---

## 2. Décomposition de l'Interface

### En-tête & Indicateurs de Volumétrie
* **Titre :** `Workflows Mon Compte` — *« Gérez, publiez et suivez les workflows de l'équipe »*[cite: 23].
* **Compteurs globaux :**
  * `WORKFLOWS : 1`[cite: 23]
  * `PUBLIÉS : 1` (mis en surbrillance avec badge de confirmation)[cite: 23]

### Onglets de Filtrage
* **Onglet actif :** `Publiés 1` sélectionné (versus `Brouillons 0`, `Corbeille 0`)[cite: 23].

### Carte du Workflow Publié
* **Identité & Version :**
  * Puce verte d'état avec mention `Brouillon du 15/10/2026 12:19` et version `v1`[cite: 23].
  * Badge d'état vert en haut à droite : `Publié`[cite: 23].
* **Miniature de Graphe (*Mini-Map Preview*) :**
  * Rendu miniature montrant les 8 étapes interconnectées avec leurs icônes fonctionnelles[cite: 23].
* **Métadonnées de composition :**
  * `8 étapes` (mise à jour par rapport aux 7 étapes du draft initial)[cite: 10, 23].
  * `Jamais exécuté`[cite: 23].
* **Actions Opérationnelles :**
  * Bouton d'action primaire : `▷ Exécuter` (lancement de la chaîne en production nominale)[cite: 23].
  * Bouton secondaire : `Modifier` (ouverture du studio de conception)[cite: 23].
  * Menu contextuel `...` pour les actions de gestion (duplication, archivage, révocation)[cite: 23].

---

## 3. Opportunités d'Amélioration & Transposition pour ORCIA

### A. Cycle de Vie et Déclenchement Nominal sous DBOS (Story 3.2b & Core)
* **Constat :** Le passage à l'état `Publié` active l'action `Exécuter` directe[cite: 23].
* **Opportunité ORCIA :** Lier l'action `Exécuter` au moteur d'orchestration durable **DBOS** :
  * Le clic instancie un workflow d'exécution avec un `workflow_id` unique et persistant dans PostgreSQL.
  * Ouvrir immédiatement un tiroir ou une page d'exécution affichant le suivi télémétrique en direct (progression des steps déterministes, appels LLM, et évaluation des Gates)[cite: 2].

### B. Gestion des Versions et Immuabilité des Workflows Publiés (Story 3.1)
* **Constat :** Le bouton `Modifier` reste présent directement sur la version publiée (`v1`)[cite: 23].
* **Opportunité ORCIA :** Appliquer une politique stricte d'**immuabilité des versions de production** :
  * Un workflow publié ne doit pas être altéré en place : le clic sur `Modifier` génère automatiquement un nouveau draft incrémental (`v1.1.0-draft` ou `v2.0.0-draft`), laissant la version `v1.0.0` active et disponible pour les consommateurs (API, Chat, Outbox)[cite: 1, 2].
  * Ce mécanisme garantit qu'aucune exécution en cours n'est corrompue par un changement de définition à chaud sous DBOS.

### C. Habilitations Granulaires d'Exécution vs Modification (Epic 8)
* **Constat :** Les boutons `Exécuter` et `Modifier` sont juxtaposés sans distinction de rôle[cite: 23].
* **Opportunité ORCIA :** Dissocier les permissions avec `<PermissionGuard />` :
  * Un utilisateur disposant du rôle `workflows:trigger` ou opérateur métier voit uniquement le bouton `Exécuter`.
  * Seul un détenteur du rôle `workflows:write` ou `workflows:admin` voit le bouton `Modifier` et le menu de gestion `...`[cite: 1, 2].
  * Pour un profil auditeur (`workflows:read`), le bouton principal devient `Consulter l'historique des runs`.
image suivante

Markdown
# Brief Écran 20 : Vue Catalogue des Produits de l'Équipe (Page 21 du PDF)

## 1. Synthèse de l'Écran
* **Rôle principal :** Hub de consultation des produits d'ingénierie et des applications sous la responsabilité de l'équipe (`Produits Mon Compte`)[cite: 24].
* **Contexte & Règle métier affichée :** Présentation en lecture seule des produits, de leurs sources rattachées, de leur état d'accostage (*onboarding* technique), de l'audit de leur kit développeur et du suivi de trajectoire de migration[cite: 24].

---

## 2. Décomposition de l'Interface

### En-tête de Section
* **Titre & Rôle :** `Produits Mon Compte`[cite: 24].
* **Descriptif fonctionnel :** *« Les produits de l'équipe, en lecture : leurs sources, leur accostage, l'audit de leur kit et, pour une migration, son suivi. »*[cite: 24]

### Fiche / Carte Produit (« Mon compte »)
* **Identifiant & Statuts d'exploitation :**
  * Nom du produit : `Mon compte`[cite: 24].
  * Badges d'état :
    * `RUN` (vert clair) : produit en exploitation nominale[cite: 24].
    * `PAR DÉFAUT` (gris) : produit principal attribué à l'espace de travail de l'équipe[cite: 24].
* **Description fonctionnelle :**
  * *« Existant en production : évolutions et corrections. »*[cite: 24]

---

## 3. Opportunités d'Amélioration & Transposition pour ORCIA

### A. Découplage Multi-Packs & Espaces Métier (Story 1.3 & Core)
* **Constat :** KORE associe des « Produits » logiciels à l'équipe avec un typage de cycle de vie (`RUN`, `BUILD`, `MIGRATION`)[cite: 24, 26].
* **Opportunité ORCIA :** Dans ORCIA, faire converger cette vue avec le **Registre des Packs & Contextes Métier** (Epic 8, `/settings/packs`)[cite: 1, 2] :
  * Un produit peut être rattaché au **Pack SDLC** (dépôts Git, backlog Jira, spécifications Spec-Kit)[cite: 1, 2], mais le même catalogue doit accueillir des contextes verticaux alternatifs (ex. initiatives du Pack RH ou applications du Pack MCO)[cite: 1, 2].
  * Le statut (`RUN`, `BUILD`, `MIGRATION`)[cite: 24, 26] doit conditionner dynamiquement les agents activés dans le graphe (ex. agents de refactorisation et tests de parité en mode *Migration*, agents de revue d'US et linting en mode *Run/Build*)[cite: 26, 27].

### B. Contrôle d'Accès Visuel & Mode Consultation Déclaré (Epic 8)
* **Constat :** L'en-tête explicite que la liste est présentée *« en lecture »*[cite: 24].
* **Opportunité ORCIA :** Formaliser ce statut de gouvernance via le composant `<PermissionGuard />` :
  * Afficher un badge d'habilitation discret en en-tête (`Habilitation : Consultation seule` vs `Gestionnaire de produit`)[cite: 1, 2].
  * Si l'utilisateur possède la permission `products:manage`, afficher un bouton d'action primaire `+ Nouveau Produit` ou `Démarrer une migration` pour déclarer un nouvel actif dans le catalogue fédéré (Story 1.3)[cite: 1, 30].

### C. Indicateurs de Santé Système et Couplage Ontologique (Epic 2)
* **Constat :** La carte actuelle est très textuelle et n'indique pas encore le volume de sources connectées sur cette vue de premier niveau[cite: 24].
* **Opportunité ORCIA :** Enrichir la carte d'aperçu d'ORCIA avec :
  * Le nombre d'entités ontologiques indexées dans PostgreSQL (L1 Domaines, L2 Features, L3 Scénarios, L4 Specs)[cite: 1, 2].
  * Un badge de santé de synchronisation (connectivité GitLab/Jira)[cite: 31, 32].
  * Un compteur des workflows durables DBOS actuellement rattachés à ce produit[cite: 1, 2].
