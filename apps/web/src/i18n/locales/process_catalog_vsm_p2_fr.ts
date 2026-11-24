import type { ProcessCatalogVsmPart2Dictionary } from "./process_catalog_vsm_labels";

export const PROCESS_CATALOG_VSM_P2_FR: ProcessCatalogVsmPart2Dictionary = {
  steps: {
    "04": {
      title: "Finalisation des exigences produit",
      actor_label: "Rovo",
      status_badge: "Gouvernance Humaine",
      summary: "Le PRD complet, les maquettes finalisées et les KPI d’observabilité",
      deliverable: "Le PRD complet, les maquettes finalisées et les KPI d’observabilité",
      attention_point:
        "Cette étape et le cadrage d’architecture s’alimentent mutuellement : l’architecte challenge le besoin, le métier le réexprime à la lumière de l’architecture. Les maquettes sont produites par l’équipe UX transverse, deux à trois jours par semaine pour Mon Compte, et doivent être finalisées avant « À prioriser ».",
      today: {
        actors: "Le PM, le PO et l’architecte, en ateliers. Beaucoup d’allers-retours, sans livrable normé.",
        deliverable: "Les livrables de spécification, à des niveaux de finition variables",
        pain_points: "À définir : le comité d’architecture valide l’étude, aucune instance ne valide aujourd’hui les exigences produit",
      },
      tomorrow: {
        actors: "Il complète le PRD au gabarit et signale ce qui manque, observabilité comprise ; l’équipe tranche.",
        deliverable: "Le PRD complet, les maquettes finalisées et les KPI d’observabilité",
        gains: "À définir : le comité d’architecture valide l’étude, aucune instance ne valide aujourd’hui les exigences produit",
      },
      passage_point: {
        decision: "Restitution d’équipe, comité d’architecture, RSSI",
        question:
          "Deux instances distinctes. La restitution d’équipe est systématique côté Mon Compte : l’architecte présente son étude à l’ensemble de l’équipe impliquée. Le comité d’architecture réunit les architectes de la branche, sans l’équipe produit, et n’est pas systématique : sans changement d’architecture il n’y a qu’une information, un changement mineur se traite en peer review, un changement impactant l’écosystème passe en comité et son no-go est bloquant. Le RSSI intervient selon la sensibilité.",
        possible_outcomes: [
          "Retour vers Étape 03 (corrections)",
          "Retour vers Étape 04 (corrections)",
          "Retour vers Étape 02 (corrections)",
          "Validation & passage à l'étape suivante",
        ],
      },
      detail_tabs: {
        agent_sub_steps: {},
        human_ai_interactions: {
          initiative: "Le PRD validé au comité d’accueil, et le dossier d’étude d’architecture",
          humanValidation: "À définir : le comité d’architecture valide l’étude, aucune instance ne valide aujourd’hui les exigences produit",
        },
        complements_and_missing: [
          "Cette étape et le cadrage d’architecture s’alimentent mutuellement : l’architecte challenge le besoin, le métier le réexprime à la lumière de l’architecture. Les maquettes sont produites par l’équipe UX transverse, deux à trois jours par semaine pour Mon Compte, et doivent être finalisées avant « À prioriser ».",
        ],
        guardrails: [
          "L’IA est un outil de réflexion et un assistant. L’humain est le maître de chacune des actions.",
          "À définir : le comité d’architecture valide l’étude, aucune instance ne valide aujourd’hui les exigences produit",
        ],
      },
    },
    "05": {
      title: "Éléments de priorisation",
      actor_label: "Humain / Équipe",
      status_badge: "Gouvernance Humaine",
      summary: "La valeur et l’effort déjà renseignés dans le ticket Feature, avec le WSJF calculé en 02, à confirmer",
      deliverable: "La valeur et l’effort déjà renseignés dans le ticket Feature, avec le WSJF calculé en 02, à confirmer",
      attention_point:
        "L’étape ne produit pas un ordre de passage, elle produit **les éléments qui permettent de prioriser**. La priorisation arbitre un rang, must, should ou could, et non un go. Une priorisation implicite existe déjà en amont : les architectes étudient pendant un PI ce qui sera réalisé au suivant. Les champs de scoring et leur formule existent déjà dans Jira.",
      today: {
        actors: "De proche en proche, sans instance dédiée. Champs de scoring inutilisés.",
        deliverable: "La complexité et la valeur, inégalement renseignées",
        pain_points: "La priorisation elle-même est processée par le train",
      },
      tomorrow: {
        actors:
          "Pas d’agent à cette étape. Le WSJF et l’effort arrivent déjà renseignés dans le ticket Feature, calculés par l’Orchestrateur Produit en 02 ; l’équipe les confirme et la priorisation reste humaine.",
        deliverable: "La valeur et l’effort déjà renseignés dans le ticket Feature, avec le WSJF calculé en 02, à confirmer",
        gains: "La priorisation elle-même est processée par le train",
      },
      passage_point: null,
      detail_tabs: {
        agent_sub_steps: {},
        human_ai_interactions: {
          initiative: "Les sujets actés, et leur estimation macro",
          humanValidation: "La priorisation elle-même est processée par le train",
        },
        complements_and_missing: [
          "L’étape ne produit pas un ordre de passage, elle produit **les éléments qui permettent de prioriser**. La priorisation arbitre un rang, must, should ou could, et non un go. Une priorisation implicite existe déjà en amont : les architectes étudient pendant un PI ce qui sera réalisé au suivant. Les champs de scoring et leur formule existent déjà dans Jira.",
        ],
        guardrails: [
          "L’IA est un outil de réflexion et un assistant. L’humain est le maître de chacune des actions.",
          "La priorisation elle-même est processée par le train",
        ],
      },
    },
    "06": {
      title: "Découpage en User Stories",
      actor_label: "Rovo",
      status_badge: "Étape 4 du POC",
      summary: "L’agent analyse, prépare l’Epic, découpe, contrôle puis crée les US ; le PO valide chaque transition.",
      deliverable:
        "Un Epic lié à la Feature, et des Stories au gabarit DoR / INVEST, contrôlées puis créées dans Jira sous l’Epic, avec leurs dépendances",
      attention_point:
        "Le découpage avant le PIP est conforme à SAFe : sans US, les équipes planifient des sorties de features. Il peut être perdu si la feature ne passe pas, mais c’est exceptionnel.",
      today: {
        actors: "PO et développeurs en refinement, en amont du PIP",
        activities:
          "Le PO et les développeurs découpent la feature en US en refinement, avant le PIP. · Les US sont rédigées, parfois estimées. · Le PIP engage ensuite les équipes.",
        deliverable: "Des US rédigées, parfois estimées",
        pain_points: "PIP : engagement des équipes du train, au deuxième jour",
      },
      tomorrow: {
        actors:
          "L’**Agent US** analyse la Feature, le PRD et l’étude, retrouve ou prépare l’Epic, propose un plan de découpage puis rédige les US au gabarit DoR / INVEST, les contrôle et les crée dans Jira. Le PO valide chaque transition.",
        activities:
          "Le PO donne à l’Agent US la clé de la Feature à découper. · Le sous-agent lit la Feature, le PRD et l’étude d’architecture, en fait la synthèse et relève les questions. · Le PO répond aux questions. · Le PO valide l’analyse. · Le sous-agent cherche un Epic existant pour la Feature. Sinon, il prépare sa création et le lie à la Feature. · Le PO confirme la création de l’Epic (« fait », « ok »). · Le sous-agent propose un plan de découpage, la liste des US. · Le PO valide le plan. · Le sous-agent rédige chaque US au gabarit DoR / INVEST. Le sous-agent Contrôle les évalue aussitôt et rend un verdict OK ou KO, avec un tableau d’écarts. · Après un contrôle OK, le PO valide explicitement (« je valide »). · Le sous-agent crée les Stories sous l’Epic et lie leurs dépendances. · Le PO confirme la création (« fait », « ok »).",
        deliverable:
          "Un Epic lié à la Feature, et des Stories au gabarit DoR / INVEST, contrôlées puis créées dans Jira sous l’Epic, avec leurs dépendances",
        gains: "Le PO valide chaque transition de l’agent, puis le PIP engage les équipes",
      },
      passage_point: {
        decision: "PIP, deux jours",
        question:
          "Une centaine de personnes, deux jours. Les dépendances entre équipes sont traitées, les US positionnées dans les itérations, et les features retenues passent à « Prêt » au deuxième jour.",
        possible_outcomes: [
          "Retour vers Étape 06 (corrections)",
          "Retour vers Étape 04 (corrections)",
          "Validation & passage à l'étape suivante",
        ],
      },
      detail_tabs: {
        agent_sub_steps: {
          analyse: {
            name: "Analyse",
            shortLabel: "Analyse",
            trigger: "Dès qu’on lui donne la clé d’une Feature, ou pour reprendre l’analyse après des retours",
            role: "Lit la Feature, le PRD et l’étude d’architecture, en fait la synthèse et relève les zones d’ombre et les questions (R, C, Q).",
            output: "La synthèse et les questions",
            humanCheck: "Analyse validée",
          },
          epic: {
            name: "Créateur d’Epic",
            shortLabel: "Epic",
            trigger: "Une fois l’analyse validée et les réponses obtenues",
            role: "Cherche si un Epic existe déjà pour la Feature. Sinon, prépare sa création, sans parent, et le lie à la Feature.",
            output: "L’Epic prêt, lié à la Feature",
            humanCheck: "Epic créé",
          },
          decoupe: {
            name: "Découpe US",
            shortLabel: "Découpe",
            trigger: "Dès que l’Epic est prêt, ou pour réviser le plan ou les US",
            role: "Propose d’abord un plan de découpage, la liste des US. Après accord sur le plan, rédige chaque US selon le gabarit DoR / INVEST.",
            output: "Les US détaillées",
            humanCheck: "Contrôle lancé",
          },
          controle: {
            name: "Contrôle",
            shortLabel: "Contrôle",
            trigger: "Automatiquement après la rédaction des US, ou sur demande",
            role: "Évalue la qualité des US : INVEST, DoR, couverture du PRD. Rend un verdict OK ou KO, avec un tableau d’écarts si des corrections sont nécessaires.",
            output: "Le verdict et le tableau d’écarts",
            humanCheck: "Contrôle OK, puis « je valide »",
          },
          creation: {
            name: "Création",
            shortLabel: "Création",
            trigger: "Uniquement après validation explicite, suite à un contrôle OK",
            role: "Crée les Stories dans Jira avec l’Epic pour parent, puis lie les dépendances entre elles.",
            output: "Les Stories créées sous l’Epic, avec leurs dépendances",
            humanCheck: "Le PO confirme la création (« fait », « ok »)",
          },
        },
        human_ai_interactions: {
          initiative: "La clé de la Feature : le ticket Feature (le PRD) et l’étude d’architecture",
          humanValidation:
            "Le PO valide l’analyse, le plan de découpage et le contrôle avant toute création dans Jira ; le PIP engage ensuite les équipes, au deuxième jour",
        },
        non_deterministic_gates: {
          "ndet-06-1": {
            name: "Sous-agent Contrôle",
            short_label: "Sous-agent Contrôle",
            status: "place",
            verifies_description:
              "Évalue les US : INVEST, DoR, couverture du PRD. Rend un verdict OK ou KO, avec un tableau d’écarts.",
            hypothesis_note: null,
            on_ko_behavior:
              "Le tableau d’écarts sert à réviser les US avec la Découpe US ; rien n’est créé sans contrôle OK et validation du PO.",
          },
        },
        complements_and_missing: [
          "Le découpage avant le PIP est conforme à SAFe : sans US, les équipes planifient des sorties de features. Il peut être perdu si la feature ne passe pas, mais c’est exceptionnel.",
        ],
        guardrails: [
          "L’IA est un outil de réflexion et un assistant. L’humain est le maître de chacune des actions.",
          "Le PO valide l’analyse, le plan de découpage et le contrôle avant toute création dans Jira ; le PIP engage ensuite les équipes, au deuxième jour",
        ],
      },
    },
    "07": {
      title: "Refinement US",
      actor_label: "Humain / Équipe",
      status_badge: "Gouvernance Humaine",
      summary: "Règles de gestion, scénarios de test, découpage en sous-tâches",
      deliverable: "Règles de gestion, scénarios de test, découpage en sous-tâches",
      attention_point:
        "C’est ici que se pose la question laissée ouverte par l’atelier : jusqu’où va l’UAT fonctionnelle du PO, et où commencent les cas limites de la QA. **Le rôle QA doit être présent à cette étape**, même lorsqu’il est porté par le PO : c’est là que la charge d’automatisation s’estime.",
      today: {
        actors: "PO et développeurs, en itération",
        deliverable: "Règles de gestion, scénarios de test, découpage en sous-tâches",
        pain_points:
          "Le PO et les développeurs, sur les statuts « à valider » et « à corriger ». Le rôle QA devrait y être : c’est ici que les scénarios se construisent.",
      },
      tomorrow: {
        actors:
          "Pas d’agent à cette étape. Les US arrivent déjà rédigées au gabarit DoR / INVEST par l’Agent US en 06 ; PO et développeurs les affinent en itération.",
        deliverable: "Règles de gestion, scénarios de test, découpage en sous-tâches",
        gains:
          "Le PO et les développeurs, sur les statuts « à valider » et « à corriger ». Le rôle QA devrait y être : c’est ici que les scénarios se construisent.",
      },
      passage_point: null,
      detail_tabs: {
        agent_sub_steps: {},
        human_ai_interactions: {
          initiative: "L’US issue du découpage, déjà au gabarit DoR / INVEST avec ses critères d’acceptation",
          humanValidation:
            "Le PO et les développeurs, sur les statuts « à valider » et « à corriger ». Le rôle QA devrait y être : c’est ici que les scénarios se construisent.",
        },
        complements_and_missing: [
          "C’est ici que se pose la question laissée ouverte par l’atelier : jusqu’où va l’UAT fonctionnelle du PO, et où commencent les cas limites de la QA. **Le rôle QA doit être présent à cette étape**, même lorsqu’il est porté par le PO : c’est là que la charge d’automatisation s’estime.",
        ],
        guardrails: [
          "L’IA est un outil de réflexion et un assistant. L’humain est le maître de chacune des actions.",
          "Le PO et les développeurs, sur les statuts « à valider » et « à corriger ». Le rôle QA devrait y être : c’est ici que les scénarios se construisent.",
        ],
      },
    },
  },
};
