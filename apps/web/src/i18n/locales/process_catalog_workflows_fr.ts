import type { ProcessCatalogWorkflowsDictionary } from "./process_catalog_packs_and_workflows_labels";

export const PROCESS_CATALOG_WORKFLOWS_FR: ProcessCatalogWorkflowsDictionary = {
  packs: {
    "orcia-pack-sdlc": {
      name: "Pack SDLC — Mon Compte (De l'idée à la production)",
      description:
        "Chaîne de valeur complète en 11 étapes et 4 phases avec 4 processus métiers guidés, 4 agents spécialisés, 4 compétences et 6 contrôles qualité.",
      connectorUsedFor: {
        "mcp:atlassian-jira": "Lecture demandes/Epics/US et écriture sous validation humaine préalable",
        "mcp:atlassian-confluence": "Socle de connaissance, PRD, Dossiers d'étude et fiches de MEP",
        "mcp:git-provider": "Arborescence du dépôt, branches, Pull Requests et Sas Externe (Étape 08)",
      },
    },
    "orcia-pack-docs": {
      name: "Pack Documentation & Aide Contextuelle ORCIA",
      description: "Pack déclaratif de génération et validation automatique de l'aide bilingue FR/EN.",
      connectorUsedFor: {
        "mcp:git-provider": "Lecture de l'arborescence et export documentaire",
      },
    },
  },
  workflows: {
    "wf-01-qualification-prd": {
      title: "Qualification de demande, Rédaction PRD & Création Feature Jira",
      triggerSourceLabels: ["Entrée Étape VSM 01, 02"],
      contractInputs: ["Demande initiale (expression du besoin ou ticket d'entrée)"],
      contractOutputs: ["# PRD", "## Contexte", "## Objectifs & KPI", "## Critères d'acceptation", "## WSJF"],
      contractExitCriteria: ["Contrôles automatiques validés (3 essais max)", "Validation humaine signée"],
      subSteps: {
        qualification: {
          name: "Qualification du besoin",
          short_label: "Qualification",
          trigger_condition_label: "Départ systématique",
          role_description: "Définit le qui, le quoi, le pourquoi et le périmètre.",
          output_description: "Le besoin qualifié",
          checkpoint_question: "validé par le PO / PM",
        },
        prd: {
          name: "Rédaction PRD",
          short_label: "PRD",
          trigger_condition_label: "Après validation du bloc STATUT : QUALIFIÉ",
          role_description: "Rédige le PRD Light : KPI, critères d’acceptation, WSJF, effort.",
          output_description: "Le contenu du PRD, validé par le PO / PM",
          checkpoint_question: "validé par le PO / PM",
        },
        jira: {
          name: "Création Jira",
          short_label: "Jira",
          trigger_condition_label: "Après validation du bloc STATUT : PRD VALIDÉ",
          role_description: "Recherche les doublons et crée la Feature dans le projet MCIA.",
          output_description: "Le ticket Feature, qui est le PRD, créé dans le projet MCIA",
          checkpoint_question: "Prévisualisation validée, puis création du ticket",
        },
      },
      deterministicGates: { "det-02-1": { name: "Script de contrôle des champs" } },
      probabilisticEvaluations: {
        "ndet-02-1": { name: "Agent challenger du PRD", rubric_ref: "Vient challenger le PRD sur le fond." },
      },
      guardrails: [
        "Ne jamais sauter une sous-étape sans validation humaine du bloc STATUT.",
        "Toujours exiger une prévisualisation avant création du ticket Feature dans Jira.",
      ],
    },
    "wf-03-etude-architecture": {
      title: "Étude de Cadrage d'Architecture (CRL-Étude-Archi — 4 sous-étapes)",
      triggerSourceLabels: ["Entrée Étape VSM 03"],
      contractInputs: ["prd_valide_uri (PRD validé en Comité d'accueil)"],
      contractOutputs: [
        "# Dossier d'Étude Architecture",
        "## Contexte & Exigences",
        "## Scénarios d'Architecture",
        "## Impacts Applicatifs",
        "## Sécurité & Résilience",
      ],
      contractExitCriteria: ["Contrôles automatiques validés (3 essais max)", "Validation humaine signée"],
      subSteps: {
        comprendre: {
          name: "Comprendre le besoin et l’existant",
          short_label: "Comprendre",
          trigger_condition_label: "Mode « générer », avec une clé ou une URL de ticket",
          role_description:
            "Lit le ticket et le socle en entier, analyse l’impact, vérifie dans le code, puis pose en un seul questionnaire ce que les sources ne disent pas.",
          output_description: "Sa compréhension du besoin, de l’existant impacté et des lacunes",
          checkpoint_question: "l’architecte confirme ou corrige la compréhension",
        },
        concevoir: {
          name: "Concevoir la solution",
          short_label: "Concevoir",
          trigger_condition_label: "Après accord sur la compréhension",
          role_description:
            "Conçoit à partir de l’existant. Si le choix n’est pas tranché, propose 2 ou 3 options et une recommandation. Décide et justifie la stack.",
          output_description: "La solution retenue, ou les options et la recommandation",
          checkpoint_question: "l’architecte choisit la solution",
        },
        rediger: {
          name: "Rédiger par blocs",
          short_label: "Rédiger",
          trigger_condition_label: "Après le choix de la solution",
          role_description: "Rédige le DE en six blocs, du contexte aux impacts, et s’arrête après chacun.",
          output_description: "Le DE, bloc par bloc",
          checkpoint_question: "l’architecte valide, corrige ou complète",
        },
        controler: {
          name: "Contrôler et rendre compte",
          short_label: "Contrôler",
          trigger_condition_label: "Après le dernier bloc",
          role_description:
            "Vérifie le fichier en 14 points (sources, décisions, stack, diagrammes, sommaire, impacts), puis rend compte.",
          output_description: "Le DE et le compte rendu : choix de stack, décisions à justifier, questions ouvertes",
          checkpoint_question: "L’architecte relit et complète : l’étude reste la sienne",
        },
      },
      deterministicGates: {},
      probabilisticEvaluations: {
        "ndet-03-1": {
          name: "Agent contradicteur",
          rubric_ref: "Relit l’étude générée en position contradictoire et en relève les faiblesses.",
        },
        "ndet-03-2": {
          name: "Contrôle final en 14 points",
          rubric_ref: "L’agent vérifie lui-même le DE : sources, décisions, stack, diagrammes, sommaire, impacts.",
        },
      },
      guardrails: [
        "L'architecte reste l'auteur souverain du Dossier d'Étude (DE).",
        "Toute affirmation sur l'existant est vérifiée dans le socle et le code.",
      ],
    },
    "wf-06-decoupe-us": {
      title: "Découpage en Epic & User Stories INVEST (5 sous-étapes)",
      triggerSourceLabels: ["Entrée Étape VSM 06"],
      contractInputs: ["feature_key (Clé de la Feature validée (PRD + DA))"],
      contractOutputs: ["# Découpage en User Stories", "## Epic", "## User Stories", "## Critères d'acceptation"],
      contractExitCriteria: ["Contrôles automatiques validés (3 essais max)", "Validation humaine signée"],
      subSteps: {
        analyse: {
          name: "Analyse",
          short_label: "Analyse",
          trigger_condition_label: "Dès qu’on lui donne la clé d’une Feature, ou pour reprendre l’analyse après des retours",
          role_description:
            "Lit la Feature, le PRD et l’étude d’architecture, en fait la synthèse et relève les zones d’ombre et les questions (R, C, Q).",
          output_description: "La synthèse et les questions",
          checkpoint_question: "le PO répond aux questions",
        },
        epic: {
          name: "Créateur d’Epic",
          short_label: "Epic",
          trigger_condition_label: "Une fois l’analyse validée et les réponses obtenues",
          role_description:
            "Cherche si un Epic existe déjà pour la Feature. Sinon, prépare sa création, sans parent, et le lie à la Feature.",
          output_description: "L’Epic prêt, lié à la Feature",
          checkpoint_question: "le PO confirme (« fait », « ok »)",
        },
        decoupe: {
          name: "Découpe US",
          short_label: "Découpe",
          trigger_condition_label: "Dès que l’Epic est prêt, ou pour réviser le plan ou les US",
          role_description:
            "Propose d’abord un plan de découpage, la liste des US. Après accord sur le plan, rédige chaque US selon le gabarit DoR / INVEST.",
          output_description: "Les US détaillées",
          checkpoint_question: "automatiquement, sans attendre",
        },
        controle: {
          name: "Contrôle",
          short_label: "Contrôle",
          trigger_condition_label: "Automatiquement après la rédaction des US, ou sur demande",
          role_description:
            "Évalue la qualité des US : INVEST, DoR, couverture du PRD. Rend un verdict OK ou KO, avec un tableau d’écarts si des corrections sont nécessaires.",
          output_description: "Le verdict et le tableau d’écarts",
          checkpoint_question: "validation explicite du PO",
        },
        creation: {
          name: "Création",
          short_label: "Création",
          trigger_condition_label: "Uniquement après validation explicite, suite à un contrôle OK",
          role_description: "Crée les Stories dans Jira avec l’Epic pour parent, puis lie les dépendances entre elles.",
          output_description: "Les Stories créées sous l’Epic, avec leurs dépendances",
          checkpoint_question: "Le PO confirme la création (« fait », « ok »)",
        },
      },
      deterministicGates: {},
      probabilisticEvaluations: {
        "ndet-06-1": {
          name: "Sous-agent Contrôle",
          rubric_ref: "Évalue les US : INVEST, DoR, couverture du PRD. Rend un verdict OK ou KO, avec un tableau d’écarts.",
        },
      },
      guardrails: [
        "Chaque User Story doit respecter la Definition of Ready (DoR) et le format Gherkin.",
        "Prévisualisation obligatoire avant création par lot dans Jira.",
      ],
    },
    "wf-08-dev-external-gate": {
      title: "Développement Assisté IDE & Sas de Contrôle Externe avant Revue du Dev",
      external_tool_label: "GitHub Copilot / Claude Code dans l'IDE",
      triggerSourceLabels: ["Entrée Étape VSM 08"],
      contractInputs: ["us_key (User Story prête (DoR) engagée dans le sprint)"],
      contractOutputs: ["# Rapport de Sas Externe PR"],
      contractExitCriteria: ["Contrôles automatiques validés (3 essais max)", "Validation humaine signée"],
      subSteps: {
        "expose-mcp-context": {
          name: "Exposition du Paquet de Contexte MCP à l'IDE",
          short_label: "Contexte MCP",
          trigger_condition_label: "Sélection de l'US par le développeur",
          role_description: "Assembler l'US, le DA, le PRD et les conventions d'équipe en bundle MCP.",
          instruction_prompt_or_ref: "Expose MCP context bundle for IDE assistant.",
          output_description: "Paquet de contexte MCP prêt pour l'IDE",
          checkpoint_question: "Contexte exposé",
        },
        "external-pr-gatekeeper": {
          name: "Sas de Contrôle ORCIA sur la Pull Request soumise",
          short_label: "Sas PR",
          trigger_condition_label: "Réception du webhook git:pr_opened",
          role_description: "Exécuter les contrôles automatiques et contradictoires sur le diff de la PR.",
          instruction_prompt_or_ref: "Vérifier l'alignement du diff PR avec les critères d'acceptation de l'US et le DA.",
          output_description: "Rapport d'audit pré-Revue du Dev",
          checkpoint_question: "Passage en Revue du Dev",
        },
      },
      deterministicGates: {
        "det-08-pr-contract": {
          name: "Contrat de conformité Pull Request & Tests",
          required_headings: ["# Rapport de Sas Externe PR"],
        },
      },
      probabilisticEvaluations: {
        "ndet-08-pr-hunter": {
          name: "Revue contradictoire d'alignement US / DA",
          rubric_ref: "Vérifie que l'implémentation respecte les scénarios retenus dans le DA et les critères Gherkin de l'US.",
        },
      },
      guardrails: [
        "Aucun merge automatique sans validation humaine en Revue du Dev.",
        "Exécution obligatoire des contrôles automatiques et contradictoires à l'ouverture de la PR.",
      ],
    },
    "wf-generate-orcia-documentation": {
      title: "Génération & Validation d'Article d'Aide Contextuelle ORCIA",
      reflexive_objective:
        "Explorer le contexte fonctionnel de l'écran cible, rédiger un article d'aide contextuelle bilingue FR/EN clair et sans jargon technique, puis vérifier toutes les sections obligatoires avant validation éditoriale.",
      triggerSourceLabels: ["Déclenchement manuel / API"],
      contractInputs: ["help_key (Clé d'aide contextuelle cible (ex: studio.five-blocks))"],
      contractOutputs: ["# ", "## Objectif", "## Étapes clés"],
      contractExitCriteria: ["Contrôles automatiques validés (3 essais max)", "Validation humaine signée"],
      subSteps: {
        "draft-bilingual-help": {
          name: "Rédaction bilingue FR/EN par @Redacteur-Documentation-Orcia",
          short_label: "Rédaction",
          trigger_condition_label: "Demande de génération d'aide",
          role_description: "Rédiger la fiche d'aide contextuelle structurée.",
          output_description: "Fiche Markdown FR/EN",
          checkpoint_question: "Validation éditoriale & rattachement",
        },
      },
      deterministicGates: {
        "det-docs-markdown": {
          name: "Contrat de structure d'aide contextuelle",
          required_headings: ["# ", "## Objectif", "## Étapes clés"],
        },
      },
      probabilisticEvaluations: {},
      guardrails: [
        "Toujours produire une version française et une version anglaise alignées.",
        "Ne jamais exposer d'identifiant confidentiel ou d'URL interne non gouvernée.",
      ],
    },
  },
};
