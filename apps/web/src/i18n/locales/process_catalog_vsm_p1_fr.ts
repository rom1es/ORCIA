import type { ProcessCatalogVsmPart1Dictionary } from "./process_catalog_vsm_labels";

export const PROCESS_CATALOG_VSM_P1_FR: ProcessCatalogVsmPart1Dictionary = {
  title: "De l’idée à la production",
  subtitle: "Le workflow agentique de Mon Compte",
  knowledgeBase: {
    title: "Socle de connaissance",
    description:
      "Une source unique, tenue à jour, projetée selon celui qui la lit, humain ou agent. Aujourd’hui la connaissance est éclatée entre huit endroits, dont un seul fait autorité : le code.",
  },
  phases: {
    "01": { name: "Émergence & cadrage", goal: "Du besoin aux spécifications", deliverables_summary: "4 étapes" },
    "02": { name: "Priorisation & engagement", goal: "De l’étude au PI engagé", deliverables_summary: "2 étapes" },
    "03": { name: "Réalisation", goal: "Du code à l’US validée", deliverables_summary: "3 étapes" },
    "04": { name: "Livraison", goal: "De la release à la mise en service", deliverables_summary: "2 étapes" },
  },
  steps: {
    "01": {
      title: "Funnel",
      actor_label: "Rovo",
      status_badge: "Agentifié",
      summary: "Le sous-agent **Qualification** définit le qui, le quoi, le pourquoi et le périmètre du besoin.",
      deliverable: "Un besoin qualifié : qui, quoi, pourquoi, périmètre, validé par le PO / PM",
      attention_point:
        "Le titre est le seul champ obligatoire. Le rattachement à un epic est recommandé, il dit dans quel chantier le sujet s’inscrit, mais rien ne l’impose. Ni architecte, ni PI cible à ce stade.",
      today: {
        actors: "Le PO / PM, à la main",
        activities:
          "Le PO / PM crée le ticket dans Jira. Le titre est le seul champ obligatoire. · Le rattachement à un epic est recommandé, mais rien ne l’impose.",
        deliverable: "Un ticket avec son titre, une coquille",
        pain_points: "Aucune, le ticket peut rester une coquille",
      },
      tomorrow: {
        actors:
          "Le sous-agent **Qualification** définit le qui, le quoi, le pourquoi et le périmètre, en allant chercher le contexte dans Confluence, Jira ou sur le web. Le PO / PM valide le bloc STATUT : QUALIFIÉ.",
        activities:
          "Le PO / PM décrit son besoin à l’Orchestrateur Produit. · L’orchestrateur confie la qualification au sous-agent, qui cherche le contexte dans Confluence, Jira ou sur le web, lit les documents fournis et repère les parties prenantes. · Le sous-agent formule le qui, le quoi, le pourquoi et le périmètre. L’orchestrateur restitue sa réponse sans la modifier. · Le PO / PM corrige ou complète, tant que le bloc n’est pas validé. · Le PO / PM valide le bloc STATUT : QUALIFIÉ. Sans cette validation, l’orchestrateur ne passe pas à la suite.",
        deliverable: "Un besoin qualifié : qui, quoi, pourquoi, périmètre, validé par le PO / PM",
        gains: "Le PO / PM valide le bloc STATUT : QUALIFIÉ",
      },
      passage_point: null,
      detail_tabs: {
        agent_sub_steps: {
          qualification: {
            name: "Qualification du besoin",
            shortLabel: "Qualification",
            trigger: "Départ systématique",
            role: "Définit le qui, le quoi, le pourquoi et le périmètre.",
            output: "Le besoin qualifié",
            humanCheck: "STATUT : QUALIFIÉ",
          },
        },
        human_ai_interactions: {
          initiative: "Un besoin exploré, issu de la discovery",
          humanValidation:
            "Le PO / PM valide le bloc STATUT : QUALIFIÉ ; sans cette validation, l’agent ne passe pas à la rédaction du PRD",
        },
        delegation_note: "Les contrôles du recueil du besoin portent sur le PRD : ils sont décrits à l’étape 02.",
        complements_and_missing: [
          "Le titre est le seul champ obligatoire. Le rattachement à un epic est recommandé, il dit dans quel chantier le sujet s’inscrit, mais rien ne l’impose. Ni architecte, ni PI cible à ce stade.",
        ],
        guardrails: [
          "L’IA est un outil de réflexion et un assistant. L’humain est le maître de chacune des actions.",
          "Le PO / PM valide le bloc STATUT : QUALIFIÉ ; sans cette validation, l’agent ne passe pas à la rédaction du PRD",
        ],
      },
    },
    "02": {
      title: "En revue",
      actor_label: "Rovo",
      status_badge: "Étape 1 du POC",
      summary: "**Rédaction PRD** rédige le PRD, puis **Création Jira** crée le ticket Feature dans MCIA.",
      deliverable:
        "Le ticket Feature, qui est le PRD : au gabarit, avec KPI, critères d’acceptation, WSJF et effort, sans doublon et prêt pour le comité d’accueil",
      attention_point:
        "**Le ticket Feature est le PRD** : c’est ici qu’il se rédige, au niveau suffisant pour décider en comité, le reste étant finalisé à l’étape 04. Les trois champs sont distincts dans Jira, donc extractibles. C’est aussi ici que le périmètre a tendance à gonfler sans que rien ne le signale, et que le PI cible se pose au plus tôt.",
      today: {
        actors: "Le PO / PM. Format libre.",
        activities:
          "Le PO / PM rédige la description, les hypothèses de bénéfices et les critères d’acceptation, en format libre. · Il va chercher les inputs UX, juridiques et métier. · Le sujet passe ensuite au comité d’accueil des demandes.",
        deliverable: "Le ticket Feature, qui est le PRD : description, hypothèses de bénéfices, critères d’acceptation",
        pain_points: "Comité d’accueil des demandes : métier, technique, managers build et run, PO, architectes",
      },
      tomorrow: {
        actors:
          "Le sous-agent **Rédaction PRD** rédige le PRD Light : KPI, critères d’acceptation, WSJF, effort. Une fois le bloc STATUT : PRD VALIDÉ, le sous-agent **Création Jira** cherche les doublons et crée la Feature dans MCIA, après prévisualisation.",
        activities:
          "Après la validation du bloc QUALIFIÉ, l’orchestrateur confie la rédaction au sous-agent. Il cherche des modèles de PRD et des KPI existants, lit la qualification validée et rédige le PRD Light : KPI, critères d’acceptation, WSJF, effort. · L’orchestrateur restitue le PRD sans le modifier. · Le PO / PM valide le bloc STATUT : PRD VALIDÉ. · Le sous-agent cherche les doublons, cible le projet MCIA et les champs requis par le comité, puis prépare le ticket Feature. · Le PO / PM valide la prévisualisation : le ticket Feature est créé. · Le sujet passe ensuite au comité d’accueil des demandes.",
        deliverable:
          "Le ticket Feature, qui est le PRD : au gabarit, avec KPI, critères d’acceptation, WSJF et effort, sans doublon et prêt pour le comité d’accueil",
        gains: "Le PO / PM valide le PRD et la Feature, puis le comité d’accueil décide",
      },
      passage_point: {
        decision: "Comité d’accueil des demandes",
        question:
          "Le besoin rédigé est pitché devant métier, technique, managers build et run, PO et architectes. En sortie, les architectes prennent le relais, ou le sujet retourne en revue.",
        possible_outcomes: [
          "Retour vers Étape 02 (corrections)",
          "Retour vers Étape 01 (corrections)",
          "Validation & passage à l'étape suivante",
        ],
      },
      detail_tabs: {
        agent_sub_steps: {
          prd: {
            name: "Rédaction PRD",
            shortLabel: "PRD",
            trigger: "Après validation du bloc STATUT : QUALIFIÉ",
            role: "Rédige le PRD Light : KPI, critères d’acceptation, WSJF, effort.",
            output: "Le contenu du PRD, validé par le PO / PM",
            humanCheck: "STATUT : PRD VALIDÉ",
          },
          jira: {
            name: "Création Jira",
            shortLabel: "Jira",
            trigger: "Après validation du bloc STATUT : PRD VALIDÉ",
            role: "Recherche les doublons et crée la Feature dans le projet MCIA.",
            output: "Le ticket Feature, qui est le PRD, créé dans le projet MCIA",
            humanCheck: "Prévisualisation validée, puis création du ticket",
          },
        },
        human_ai_interactions: {
          initiative: "Le ticket, et les inputs à aller chercher : UX, juridique, métier",
          humanValidation:
            "Le PO / PM valide le bloc STATUT : PRD VALIDÉ, puis la prévisualisation de la Feature ; le comité d’accueil des demandes décide ensuite",
        },
        deterministic_gates: {
          "det-02-1": {
            name: "Script de contrôle des champs",
            short_label: "Script : caractères par champ",
            status: "hypothese",
            verifies_description: "Contrôle le nombre de caractères de chaque champ du ticket Feature.",
            on_ko_behavior: "À préciser.",
          },
        },
        non_deterministic_gates: {
          "ndet-02-1": {
            name: "Agent challenger du PRD",
            short_label: "Agent challenger du PRD",
            status: "hypothese",
            verifies_description: "Vient challenger le PRD sur le fond.",
            hypothesis_note:
              "Hypothèse à confirmer : s’appuyer sur les questions métier que pose l’agent d’étude d’architecture pour améliorer le besoin.",
            on_ko_behavior: "À préciser.",
          },
        },
        complements_and_missing: [
          "**Le ticket Feature est le PRD** : c’est ici qu’il se rédige, au niveau suffisant pour décider en comité, le reste étant finalisé à l’étape 04. Les trois champs sont distincts dans Jira, donc extractibles. C’est aussi ici que le périmètre a tendance à gonfler sans que rien ne le signale, et que le PI cible se pose au plus tôt.",
        ],
        guardrails: [
          "L’IA est un outil de réflexion et un assistant. L’humain est le maître de chacune des actions.",
          "Le PO / PM valide le bloc STATUT : PRD VALIDÉ, puis la prévisualisation de la Feature ; le comité d’accueil des demandes décide ensuite",
        ],
      },
    },
    "03": {
      title: "Cadrage d’architecture",
      actor_label: "GitHub Copilot",
      status_badge: "Étape 3 du POC",
      summary:
        "L’architecte construit l’étude avec l’agent, outil de réflexion : l’agent questionne, propose et rédige, l’architecte arbitre.",
      deliverable:
        "Le dossier d’étude (DE) au gabarit, construit avec l’architecte : solution, relevé de décisions, diagrammes Mermaid, impacts en taille T-shirt, questions encore ouvertes",
      attention_point:
        "« Cadrage » désigne ici **le cadrage d’architecture**, et rien d’autre : le terme est connoté dans l’équipe. En sortie, deux instances distinctes : la restitution à l’équipe, systématique, et le comité d’architecture, dont le déclenchement dépend de l’impact du changement.",
      today: {
        actors: "L’architecte référent. Rendu variable selon l’archi, sans estimation.",
        activities:
          "L’architecte référent rédige le dossier d’étude dans Confluence. Le rendu varie selon l’architecte, sans estimation. · Il restitue l’étude à l’équipe, puis la porte en comité d’architecture si l’impact le demande.",
        deliverable: "Le dossier d’étude, dans Confluence",
        pain_points:
          "Restitution d’équipe systématique, puis comité d’architecture selon l’impact du changement. RSSI si le sujet est sensible.",
      },
      tomorrow: {
        actors:
          "L’architecte construit l’étude avec l’agent **CRL Étude d’architecture**, qui lui sert d’outil de réflexion : l’agent rassemble l’existant, pose les questions que les sources ne tranchent pas, propose des options et rédige. L’architecte arbitre à chaque étape et reste l’auteur de l’étude.",
        activities:
          "L’architecte lance l’agent avec la clé du ticket Feature. · L’agent lit le ticket et le socle de connaissance, vérifie dans le code, Confluence et les études existantes, puis analyse l’impact. · Il pose en un seul questionnaire ce que les sources ne disent pas, en commençant par les éléments hors socle. · L’architecte répond au questionnaire. · Point de validation 1 : l’architecte confirme ou corrige la compréhension du besoin et de l’existant. · L’agent conçoit la solution. Si le choix n’est pas tranché, il propose 2 ou 3 options et une recommandation. · Point de validation 2 : l’architecte choisit la solution. · L’agent rédige le dossier d’étude bloc par bloc, et s’arrête après chacun. · Après chaque bloc, l’architecte valide, corrige ou complète. Un bloc validé est figé. · L’agent contrôle le dossier en 14 points et rend compte. · L’architecte relit et complète : l’étude reste la sienne.",
        deliverable:
          "Le dossier d’étude (DE) au gabarit, construit avec l’architecte : solution, relevé de décisions, diagrammes Mermaid, impacts en taille T-shirt, questions encore ouvertes",
        gains: "L’architecte arbitre à chaque point d’étape, puis restitution et comité",
      },
      passage_point: null,
      detail_tabs: {
        agent_sub_steps: {
          comprendre: {
            name: "Comprendre le besoin et l’existant",
            shortLabel: "Comprendre",
            trigger: "Mode « générer », avec une clé ou une URL de ticket",
            role: "Lit le ticket et le socle en entier, analyse l’impact, vérifie dans le code, puis pose en un seul questionnaire ce que les sources ne disent pas.",
            output: "Sa compréhension du besoin, de l’existant impacté et des lacunes",
            humanCheck: "Point de validation 1",
          },
          concevoir: {
            name: "Concevoir la solution",
            shortLabel: "Concevoir",
            trigger: "Après accord sur la compréhension",
            role: "Conçoit à partir de l’existant. Si le choix n’est pas tranché, propose 2 ou 3 options et une recommandation. Décide et justifie la stack.",
            output: "La solution retenue, ou les options et la recommandation",
            humanCheck: "Point de validation 2",
          },
          rediger: {
            name: "Rédiger par blocs",
            shortLabel: "Rédiger",
            trigger: "Après le choix de la solution",
            role: "Rédige le DE en six blocs, du contexte aux impacts, et s’arrête après chacun.",
            output: "Le DE, bloc par bloc",
            humanCheck: "Validation de chaque bloc",
          },
          controler: {
            name: "Contrôler et rendre compte",
            shortLabel: "Contrôler",
            trigger: "Après le dernier bloc",
            role: "Vérifie le fichier en 14 points (sources, décisions, stack, diagrammes, sommaire, impacts), puis rend compte.",
            output: "Le DE et le compte rendu : choix de stack, décisions à justifier, questions ouvertes",
            humanCheck: "L’architecte relit et complète : l’étude reste la sienne",
          },
        },
        human_ai_interactions: {
          initiative: "Le ticket Feature (le PRD), le socle de connaissance CRL, le code de crl-back et crl-front, les études existantes",
          humanValidation:
            "L’architecte arbitre à chaque point d’étape : sa compréhension du besoin, le choix de la solution, chaque bloc rédigé. Viennent ensuite la restitution d’équipe et le comité d’architecture.",
        },
        non_deterministic_gates: {
          "ndet-03-1": {
            name: "Agent contradicteur",
            short_label: "Agent contradicteur",
            status: "ajouter",
            verifies_description: "Relit l’étude générée en position contradictoire et en relève les faiblesses.",
            hypothesis_note: null,
            on_ko_behavior: "Ses objections reviennent à l’agent CRL Étude d’architecture, qui améliore l’étude ; l’architecte arbitre.",
          },
          "ndet-03-2": {
            name: "Contrôle final en 14 points",
            short_label: "Contrôle final de l’agent",
            status: "place",
            verifies_description: "L’agent vérifie lui-même le DE : sources, décisions, stack, diagrammes, sommaire, impacts.",
            hypothesis_note: null,
            on_ko_behavior: "L’agent corrige ; une correction qui touche un bloc déjà validé est soumise à l’architecte.",
          },
        },
        complements_and_missing: [
          "« Cadrage » désigne ici **le cadrage d’architecture**, et rien d’autre : le terme est connoté dans l’équipe. En sortie, deux instances distinctes : la restitution à l’équipe, systématique, et le comité d’architecture, dont le déclenchement dépend de l’impact du changement.",
        ],
        guardrails: [
          "L’IA est un outil de réflexion et un assistant. L’humain est le maître de chacune des actions.",
          "L’architecte arbitre à chaque point d’étape : sa compréhension du besoin, le choix de la solution, chaque bloc rédigé. Viennent ensuite la restitution d’équipe et le comité d’architecture.",
        ],
      },
    },
  },
};
