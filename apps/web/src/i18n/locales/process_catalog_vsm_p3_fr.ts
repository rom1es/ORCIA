import type { ProcessCatalogVsmPart3Dictionary } from "./process_catalog_vsm_labels";

export const PROCESS_CATALOG_VSM_P3_FR: ProcessCatalogVsmPart3Dictionary = {
  steps: {
    "08": {
      title: "Développement",
      actor_label: "GitHub Copilot",
      status_badge: "Étape 5 du POC",
      summary: "Le code, puis une pull request, même sortie, même exigence",
      deliverable: "Le code, puis une pull request, même sortie, même exigence",
      attention_point:
        "Certaines tâches resteront hors de portée (provisionner une base, ouvrir un topic) et le POC met ces limites en exergue : **c’est un résultat attendu**.",
      today: {
        actors: "Le développeur assigné, en local",
        deliverable: "Le code, puis une pull request",
        pain_points: "Revue du Dev : un développeur qui n’a pas codé la tâche relit, jamais déléguée",
      },
      tomorrow: {
        actors: "Il développe ; le développeur pilote, corrige et assume.",
        deliverable: "Le code, puis une pull request, même sortie, même exigence",
        gains: "Revue du Dev : un développeur qui n’a pas codé la tâche relit, jamais déléguée",
      },
      passage_point: {
        decision: "Revue du Dev",
        question:
          "Un développeur qui n’a pas codé la tâche relit et autorise le merge. C’est la seule gate que le POC ne cherche pas à déplacer.",
        possible_outcomes: ["Retour vers Étape 08 (corrections)", "Validation & passage à l'étape suivante"],
      },
      detail_tabs: {
        agent_sub_steps: {},
        human_ai_interactions: {
          initiative: "Les US, l’étude, et les standards de l’équipe",
          humanValidation: "Revue du Dev : un développeur qui n’a pas codé la tâche relit, jamais déléguée",
        },
        complements_and_missing: [
          "Certaines tâches resteront hors de portée (provisionner une base, ouvrir un topic) et le POC met ces limites en exergue : **c’est un résultat attendu**.",
        ],
        guardrails: [
          "L’IA est un outil de réflexion et un assistant. L’humain est le maître de chacune des actions.",
          "Revue du Dev : un développeur qui n’a pas codé la tâche relit, jamais déléguée",
        ],
      },
    },
    "09": {
      title: "Recette",
      actor_label: "GitHub Copilot",
      status_badge: "Cas d’usage du POC",
      summary: "L’US validée, et une bibliothèque de tests qui s’enrichit d’elle-même",
      deliverable: "L’US validée, et une bibliothèque de tests qui s’enrichit d’elle-même",
      attention_point:
        "Le merge précède la validation métier : une US mergée entre dans la release avant que le QA et le PO ne l’aient validée. **Ce n’est pas un défaut d’outil, c’est un choix de flux**, mais il détermine où une gate a un effet réel. La génération des scénarios est un cas d’usage du POC.",
      today: {
        actors: "L’équipe QA, transverse aux équipes, déroule les scénarios",
        deliverable: "L’US validée, puis passée en attente de MEP",
        pain_points:
          "Test QA par l’équipe QA transverse, revue fonctionnelle par l’architecte, démo validée en comité BO & PM, puis PO review",
      },
      tomorrow: {
        actors: "Il génère les scénarios et, après chaque bug non couvert, le scénario manquant ; le QA exécute et arbitre.",
        deliverable: "L’US validée, et une bibliothèque de tests qui s’enrichit d’elle-même",
        gains:
          "Test QA par l’équipe QA transverse, revue fonctionnelle par l’architecte, démo validée en comité BO & PM, puis PO review",
      },
      passage_point: {
        decision: "PO review",
        question: "Validation fonctionnelle sur les critères d’acceptation, après le test QA sur l’environnement de recette.",
        possible_outcomes: [
          "Retour vers Étape 08 (corrections)",
          "Retour vers Étape 07 (corrections)",
          "Validation & passage à l'étape suivante",
        ],
      },
      detail_tabs: {
        agent_sub_steps: {},
        human_ai_interactions: {
          initiative: "Le package déployé en recette, et les scénarios de test",
          humanValidation:
            "Test QA par l’équipe QA transverse, revue fonctionnelle par l’architecte, démo validée en comité BO & PM, puis PO review",
        },
        complements_and_missing: [
          "Le merge précède la validation métier : une US mergée entre dans la release avant que le QA et le PO ne l’aient validée. **Ce n’est pas un défaut d’outil, c’est un choix de flux**, mais il détermine où une gate a un effet réel. La génération des scénarios est un cas d’usage du POC.",
        ],
        guardrails: [
          "L’IA est un outil de réflexion et un assistant. L’humain est le maître de chacune des actions.",
          "Test QA par l’équipe QA transverse, revue fonctionnelle par l’architecte, démo validée en comité BO & PM, puis PO review",
        ],
      },
    },
    "10": {
      title: "Déploiement",
      actor_label: "Rovo",
      status_badge: "Gouvernance Humaine",
      summary: "La même page, pré-remplie et contrôlée, en une fraction du temps",
      deliverable: "La même page, pré-remplie et contrôlée, en une fraction du temps",
      attention_point:
        "Tout ce qu’on y recopie (US, composants impactés, versions) **existe déjà dans Jira**. Le code freeze intervient environ trois semaines avant la MEP, et la recette est figée deux jours.",
      today: {
        actors: "Écrite à plusieurs mains dans Confluence, complétude vérifiée à l’œil",
        deliverable: "La page de déploiement, et la release figée au code freeze",
        pain_points: "Release manager et Ops : complétude de la page, puis code freeze",
      },
      tomorrow: {
        actors: "Il initialise la page depuis Jira ; l’humain ne complète que ce qui demande un jugement.",
        deliverable: "La même page, pré-remplie et contrôlée, en une fraction du temps",
        gains: "Release manager et Ops : complétude de la page, puis code freeze",
      },
      passage_point: {
        decision: "TNR, perf, intégration, pré-production",
        question:
          "Quatre environnements, un go/no-go à chaque passage. Tests de non-régression sur recette figée, tirs de charge, mise à disposition des SI partenaires, puis test de rollback.",
        possible_outcomes: [
          "Retour vers Étape 08 (corrections)",
          "Retour vers Étape 10 (corrections)",
          "Validation & passage à l'étape suivante",
        ],
      },
      detail_tabs: {
        agent_sub_steps: {},
        human_ai_interactions: {
          initiative: "Les US de la release, leurs composants, leurs versions",
          humanValidation: "Release manager et Ops : complétude de la page, puis code freeze",
        },
        complements_and_missing: [
          "Tout ce qu’on y recopie (US, composants impactés, versions) **existe déjà dans Jira**. Le code freeze intervient environ trois semaines avant la MEP, et la recette est figée deux jours.",
        ],
        guardrails: [
          "L’IA est un outil de réflexion et un assistant. L’humain est le maître de chacune des actions.",
          "Release manager et Ops : complétude de la page, puis code freeze",
        ],
      },
    },
    "11": {
      title: "MEP & mise en service",
      actor_label: "Humain / Équipe",
      status_badge: "Gouvernance Humaine",
      summary: "La fonctionnalité en production, puis la restitution de ce qu’elle a produit",
      deliverable: "La fonctionnalité en production, puis la restitution de ce qu’elle a produit",
      attention_point:
        "Une fonctionnalité peut être déployée désactivée puis activée par simple configuration à la date voulue, cela évite une mise en production dédiée. Une restitution suit la mise en service : c’est le moment où l’on regarde ce que la fonctionnalité a réellement produit, et **il n’existe aujourd’hui aucun temps de restitution des KPI au sein du train**.",
      today: {
        actors: "La system team, sur procédure fournie par les développeurs",
        deliverable: "La fonctionnalité en production, puis la restitution de ce qu’elle a produit",
        pain_points: "Go/no-go à chaque passage d’environnement : Ops, QA, SI partenaires",
      },
      tomorrow: {
        actors: "La system team, sur procédure fournie par les développeurs",
        deliverable: "La fonctionnalité en production, puis la restitution de ce qu’elle a produit",
        gains: "Go/no-go à chaque passage d’environnement : Ops, QA, SI partenaires",
      },
      passage_point: null,
      detail_tabs: {
        agent_sub_steps: {},
        human_ai_interactions: {
          initiative: "Le package validé, et la procédure d’activation",
          humanValidation: "Go/no-go à chaque passage d’environnement : Ops, QA, SI partenaires",
        },
        complements_and_missing: [
          "Une fonctionnalité peut être déployée désactivée puis activée par simple configuration à la date voulue, cela évite une mise en production dédiée. Une restitution suit la mise en service : c’est le moment où l’on regarde ce que la fonctionnalité a réellement produit, et **il n’existe aujourd’hui aucun temps de restitution des KPI au sein du train**.",
        ],
        guardrails: [
          "L’IA est un outil de réflexion et un assistant. L’humain est le maître de chacune des actions.",
          "Go/no-go à chaque passage d’environnement : Ops, QA, SI partenaires",
        ],
      },
    },
  },
  returnLoops: {
    "loop-02-to-02-0": {
      trigger_condition: "La demande n’est pas jugée prête : besoin flou, bénéfices non étayés, périmètre trop large.",
      reason: "Les questions du comité, les informations manquantes, les hypothèses de bénéfices à étayer, un éventuel redécoupage.",
      impact_summary:
        "Les remarques sont consignées dans la Feature. L’Orchestrateur Produit reprend au sous-agent Rédaction PRD, qui produit un PRD révisé répondant à chaque remarque et signale celles qui restent ouvertes. Le PO / PM valide de nouveau le bloc STATUT : PRD VALIDÉ avant de re-présenter.",
    },
    "loop-02-to-01-1": {
      trigger_condition: "La remarque remet en cause la qualification : qui, quoi, pourquoi ou périmètre. L’orchestrateur reprend alors au sous-agent Qualification.",
      reason: "La remarque remet en cause la qualification : qui, quoi, pourquoi ou périmètre. L’orchestrateur reprend alors au sous-agent Qualification.",
    },
    "loop-04-to-03-0": {
      trigger_condition: "L’étude fait émerger une problématique bloquante, ou le comité d’architecture rend un no-go.",
      reason: "Les points bloquants, les questions restées ouvertes, les scénarios à approfondir, les exigences du RSSI le cas échéant.",
      impact_summary:
        "Les remarques de la restitution et du comité sont rattachées au DE. L’architecte reprend l’étude avec l’agent en mode « corrections » : l’agent intègre chaque remarque, incrémente la version et liste les sections dépendantes à revoir, sans les modifier sans accord. Une section à repenser entièrement passe par le mode « section ». L’architecte arbitre chaque reprise avant le nouveau passage.",
    },
    "loop-04-to-04-1": {
      trigger_condition: "La remarque porte sur les exigences produit, pas sur l’architecture.",
      reason: "La remarque porte sur les exigences produit, pas sur l’architecture.",
    },
    "loop-04-to-02-2": {
      trigger_condition: "La remarque remet en cause le besoin lui-même.",
      reason: "La remarque remet en cause le besoin lui-même.",
    },
    "loop-06-to-06-0": {
      trigger_condition: "Les équipes ne s’engagent pas : découpage incomplet, dépendances non traitées.",
      reason: "Les dépendances relevées entre équipes, les US manquantes ou trop larges, les questions des équipes.",
      impact_summary:
        "Les remarques du PIP sont rattachées à la Feature. Le PO relance l’Agent US : la Découpe US révise le plan ou les US à partir des remarques, le Contrôle les vérifie de nouveau, et rien n’est créé sans validation. Le découpage révisé est prêt pour le PI suivant.",
    },
    "loop-06-to-04-1": {
      trigger_condition: "Les exigences ne suffisent pas pour découper.",
      reason: "Les exigences ne suffisent pas pour découper.",
    },
    "loop-08-to-08-0": {
      trigger_condition: "La revue demande des corrections.",
      reason: "Les commentaires de revue, ligne par ligne.",
      impact_summary:
        "Les commentaires de la pull request deviennent l’entrée de l’itération suivante de l’agent de développement. Le développeur pilote la correction, la revue reste humaine.",
    },
    "loop-09-to-08-0": {
      trigger_condition: "Le résultat ne répond pas aux critères d’acceptation.",
      reason: "Les écarts constatés, critère par critère.",
      impact_summary:
        "L’agent confronte le résultat aux critères et rédige les écarts. Selon leur nature, il propose de renvoyer vers le développement ou vers le refinement ; le PO confirme.",
    },
    "loop-09-to-07-1": {
      trigger_condition: "Le critère d’acceptation lui-même est ambigu ou incomplet.",
      reason: "Le critère d’acceptation lui-même est ambigu ou incomplet.",
    },
    "loop-10-to-08-0": {
      trigger_condition: "Une anomalie bloquante apparaît en non-régression, en charge, en intégration ou en pré-production.",
      reason: "L’anomalie, l’environnement concerné, le scénario qui l’a révélée.",
      impact_summary:
        "Le scénario qui a révélé l’anomalie rejoint la bibliothèque de tests ; la correction repart du développement avec ce scénario en entrée.",
    },
    "loop-10-to-10-1": {
      trigger_condition: "Le problème vient de la page de déploiement ou de la procédure, pas du code.",
      reason: "Le problème vient de la page de déploiement ou de la procédure, pas du code.",
    },
  },
  opportunities: {
    P1: {
      title: "Affiner le contenu d’une feature",
      description:
        "Normer ce qu’on attend d’une revue : description, hypothèses de bénéfices, critères d’acceptation. Les trois champs existent déjà dans Jira et sont extractibles, il manque un gabarit et un ordre de grandeur de ce qu’est une feature acceptable. — Débloque : La priorisation en aval, et l’entrée de toute la chaîne agentique : c’est le premier texte que l’agent lira.",
    },
    P2: {
      title: "Affiner le contenu d’une User Story",
      description:
        "Structurer les critères d’acceptation dans un format lisible par un agent, du type « étant donné, quand, alors », et en dériver les scénarios de recette. Concerne le refinement et la recette. — Débloque : La génération des scénarios de recette, le scénario manquant après un bug de production, et une PO review outillable.",
    },
    P3: {
      title: "Écrire automatiquement les User Stories",
      description:
        "Générer les US au gabarit à partir de l’étude d’architecture et du besoin, pour que le refinement devienne une relecture. — Débloque : La création directe des tickets sans copier-coller, et un contexte déjà branché (epics, Confluence, maquettes) qui évite de recharger le prompt à chaque fois.",
    },
  },
};
