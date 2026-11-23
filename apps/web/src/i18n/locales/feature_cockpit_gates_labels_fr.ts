import type { FeatureCockpitGatesDictionary } from "./feature_cockpit_gates_labels";

export const FEATURE_COCKPIT_GATES_FR: FeatureCockpitGatesDictionary = {
  cockpit: {
    workflowPreviewNodes: {
      intentRouter: "1. Analyse d'intention",
      queryPlanner: "2. Planification & Ontologie",
      parallelFanOut: "3. Collecte parallèle",
      criticalTriage: "4. Contrôle & Axiomes",
      profileSynthesizer: "5. Synthèse adaptée au profil",
    },
    runsSection: {
      emptyTitle: "Aucun Espace de Travail ni processus en cours",
      emptyDescription:
        "Créez votre premier Espace de Travail pour lancer vos processus, utiliser Mon Assistant et suivre vos validations.",
      createWorkspaceCta: "+ Créer un Espace de Travail",
      assistantOptionLabel: "Assistant ORCIA",
      runTitlePlaceholder: "Intitulé de l'exécution...",
      startProcessBtn: "Démarrer le processus",
    },
    stepStatus: {
      pending: "En attente",
      running: "En cours",
      completed: "Validé",
      staleNeedsReview: "À revalider",
      waitingHumanAnchor: "Ancrage humain requis",
      waitingHumanArbitration: "Arbitrage requis",
      pausedHumanGate: "Validation humaine requise",
    },
    stepKeyLabels: {
      "frame-architecture-intent": "Cadrage de l'intention d'architecture",
      "delegate-remediation-subworkflow": "Sous-processus de correction",
      "post-deploy-verification": "Vérification post-déploiement",
      "step-architecture-gate": "Validation d'architecture",
      "inbox-review-step": "Relecture en boîte de réception",
    },
    upstreamChallenge: {
      defaultSummary:
        "Simulation d'impact : réévaluation ciblée depuis l'intention d'architecture sans reconsommer l'amont.",
      defaultPreviewReason:
        "La règle métier amont contredit le contrat API partenaire v3 (fenêtre max 15 min).",
      staleReplayTemplate:
        "Alerte d'obsolescence : rejeu ciblé exécuté depuis « {stepKey} » — les livrables aval liés ont été marqués à revalider.",
      openModalBtn: "Ouvrir la modale d'impact",
      defaultStaleBanner:
        "Alerte d'obsolescence : rejeu amont détecté — les livrables aval liés sont marqués à revalider.",
    },
    onboardingChecklist: {
      title: "Guide de Mise en Route de la Plateforme",
      subtitle:
        "Configurez chaque étape depuis les écrans dédiés ou lancez un assistant guidé pas à pas.",
      guidedAssistantsBtn: "Assistants Guidés",
      statusConfigured: "Configuré",
      statusToConfigure: "À configurer",
    },
  },
  gates: {
    panel: {
      activeScopeLabel: "Périmètre de validation actif :",
      emptyTitle: "Aucune étape de validation en attente actuellement",
      emptyDescription:
        "Les contrôles automatiques, revues croisées et étapes de validation humaine s'affichent ici lors de l'exécution d'un processus.",
      openProcessesBtn: "Ouvrir Mes Processus",
    },
    headerCard: {
      title: "Revue Humaine Adaptative (Synthèse en 4 Points & Validation par Section)",
      gatePrefix: "Point de contrôle",
      statusPendingReview: "Validation humaine requise",
      statusPassed: "Validé",
      jiraStaged: "Préparée (en attente)",
      jiraExecuted: "Exécutée",
      prepareReviewBtn: "Préparer une revue humaine (4 blocs + Jira)",
    },
    humanReview: {
      defaultExecutiveSummary: "Synthèse exécutive de l'étape soumise à validation humaine.",
      step1AlignmentTemplate: "Alignement Étape 1 : {status}",
      alignmentAligned: "Conforme",
      alignmentConflict: "Conflit",
      totalVolumeTemplate: "Volume total : {count} mots",
      loadErrorFallback: "Erreur de chargement des validations",
      loadErrorBannerTemplate: "⚠️ Impossible de charger les revues humaines ({msg}).",
      openReviewSuccess: "✅ Briefing de revue 4 blocs et découpage par sections prêts pour validation.",
      openReviewErrorFallback: "Erreur d'ouverture de revue",
      inspectHypothesesSuccess: "✅ Point 4 (Hypothèses Retenues) marqué comme relu.",
      inspectHypothesesErrorFallback: "Erreur d'inspection",
      chunkStatusLabels: {
        APPROVED: "Approuvée",
        CO_EDITED: "Co-éditée",
        CHALLENGED: "Contestée",
        PENDING: "En attente",
      },
      chunkUpdatedTemplate: "✅ Section mise à jour ({status}).",
      chunkErrorFallback: "Erreur sur la section",
      finalizeSuccess: "✅ Validation humaine enregistrée et action Jira en attente exécutée.",
      finalizeErrorFallback: "Erreur de finalisation de la validation",
      defaultChallengeReason: "Demande de précision sur l'alignement amont.",
      seedPhrase:
        "Vérification croisée de conformité architecturale, traçabilité du verrouillage et validation des axiomes ontologiques L1-L4.",
      seedDecisions: [
        "Validation du contrat de service et enregistrement sécurisé.",
        "Exécution différée des transitions Jira après validation humaine.",
      ],
      seedHypotheses: [
        "H1 : Les transitions Jira PAYBUILD-101 restent en attente jusqu'à la validation finale.",
        "H2 : L'empreinte de validation couvre toute modification humaine de section.",
      ],
      seedSec1Title: "Section 1 — Architecture & Frontières Hexagonales",
      seedSec1Prefix: "Section 1 : Architecture modulaire et séparation des ports",
      seedSec2Title: "Section 2 — Sécurité & Actions Jira Pré-Validées",
      seedSec2Prefix: "Section 2 : Contrôle d'accès et exécution Jira conditionnelle",
      seedJiraSummary: "Soumettre PAYBUILD-101 en revue dès validation de la revue humaine",
    },
    challengeModal: {
      defaultSummary:
        "Simulation d'impact : réévaluation ciblée de la section contestée sans retraiter l'amont validé.",
      challengeSubmittedBanner: "⚠️ Contestation amont enregistrée et transmise pour révision.",
      replayBannerTemplate: "Alerte d'obsolescence : rejeu déclenché depuis « {stepKey} ».",
      errorContextLabel: "Rejeu du processus",
    },
    docProcess: {
      cardTitle: "📚 Processus du Pack ORCIA — Génération de la Documentation ORCIA",
      cardDescription:
        "Génère, vérifie et met à jour les guides fonctionnels par écran (FR/EN), la FAQ d'architecture et le site de documentation d'ORCIA en 4 étapes.",
      badgeLabel: "📦 Pack Documentation ORCIA · Agent : @Rédacteur-Documentation-Orcia",
      runBtn: "▶️ Lancer la génération de la documentation ORCIA",
      loadInBuilderBtn: "✏️ Charger dans l'Atelier de Processus",
      stepsSummaryTitle: "Bilan des 4 étapes exécutées :",
      stepCompletedBadge: "✓ Terminé",
      publishSuccessBanner:
        "✅ Processus « Génération de la Documentation ORCIA » publié et exécuté avec succès en 4 étapes.",
      localValidationFallback: "Validation locale appliquée",
      publishWithDetailTemplate:
        "✅ Processus « Génération de la Documentation ORCIA » exécuté en 4 étapes ({detail}).",
      loadedInBuilderBanner:
        "✏️ Modèle « Génération de la Documentation ORCIA » chargé dans l'Atelier de Processus pour personnalisation.",
      steps: [
        {
          stepNumber: 1,
          title: "Étape 1 — Inventaire du dépôt ORCIA",
          agentHandle: "@Rédacteur-Documentation-Orcia",
          summary:
            "20 écrans, 16 composants d'interface, fiches d'aide bilingues, FAQ d'architecture et rapports techniques recensés.",
        },
        {
          stepNumber: 2,
          title: "Étape 2 — Génération & Enrichissement des Guides et de la FAQ",
          agentHandle: "@Rédacteur-Documentation-Orcia & @Architecte-Métier-Pack",
          summary:
            "Sections obligatoires structurées : Objectif, Guide Fonctionnel par Écran, Architecture & Modèle Métier, Questions Fréquentes (FAQ).",
        },
        {
          stepNumber: 3,
          title: "Étape 3 — Contrôle Qualité Déterministe (validate_help_article)",
          agentHandle: "@Certificateur-Sécurité-et-Sandbox",
          summary:
            "Routes liées vérifiées, sections obligatoires présentes et absence totale de secrets ou de jargon interne confirmée.",
        },
        {
          stepNumber: 4,
          title: "Étape 4 — Publication & Rattachement à Chaud (/showcase & docs/help/)",
          agentHandle: "@Rédacteur-Documentation-Orcia",
          summary:
            "Récapitulatif complet des documents générés/vérifiés publié dans les guides bilingues et synchronisé avec la vitrine.",
        },
      ],
      workflowTitle:
        "Processus 6 — Générer et Synchroniser la Documentation Complète d'ORCIA (Guides Écrans, FAQ Architecture & Catalogue)",
      workflowPrePrompt:
        "Recenser les écrans et parcours d'ORCIA, rédiger et synchroniser les guides fonctionnels par écran (FR/EN) et la FAQ d'architecture, contrôler la conformité documentaire, puis publier les fiches d'aide et le catalogue.",
      workflowLayers: [
        {
          layerId: "layer-doc-inventory",
          label: "1. Inventaire du dépôt ORCIA (20 écrans, guides FR/EN, FAQ & rapports)",
          zone: "inputs",
          orderIndex: 1,
          enabled: true,
        },
        {
          layerId: "layer-doc-authoring",
          label:
            "2. Génération & enrichissement des guides et de la FAQ (@Rédacteur-Documentation-Orcia & @Architecte-Métier-Pack)",
          zone: "capabilities",
          orderIndex: 2,
          enabled: true,
        },
        {
          layerId: "layer-doc-validation",
          label: "3. Contrôle qualité déterministe (routes liées, sections obligatoires, zéro secret ni jargon)",
          zone: "capabilities",
          orderIndex: 3,
          enabled: true,
        },
        {
          layerId: "layer-doc-publish",
          label: "4. Publication & rattachement à chaud (guides FR/EN & vitrine de documentation)",
          zone: "deliverables",
          orderIndex: 4,
          enabled: true,
        },
      ],
      generatedMarkdown: [
        "# Documentation Complète d'ORCIA — Guides Écrans, Architecture & FAQ",
        "",
        "## Objectif",
        "Fournir un référentiel unifié et à jour couvrant l'ensemble des écrans d'ORCIA, le modèle métier d'organisation et les réponses aux questions fréquentes.",
        "",
        "## Guide Fonctionnel par Écran",
        "- **Cockpit** : Superviser les processus en cours, les arbitrages humains en attente et l'avancement des espaces.",
        "- **Mon Assistant** : Dialoguer avec l'assistant IA, choisir le niveau de réflexion et classer ses échanges par dossiers.",
        "- **Mes Espaces** : Gérer les sources documentaires, les règles métiers, le glossaire et les livrables d'un projet.",
        "- **Mes Agents & Mes Processus** : Configurer les agents spécialisés, leurs compétences et les processus gouvernés.",
        "- **Administration & Journal d'Activité** : Administrer les habilitations, l'authentification, les modèles IA, les connecteurs et la traçabilité.",
        "",
        "## Architecture & Modèle Métier",
        "- **Directions (BU) & Équipes de facturation** : L'Équipe regroupe les utilisateurs et porte le rattachement budgétaire des appels IA.",
        "- **Espaces de Travail** : Chaque espace (collectif, privé personnel ou confidentiel) est rattaché à une équipe et hérite des règles de l'organisation.",
        "",
        "## Questions Fréquentes (FAQ)",
        "- **Quelle est la différence entre une Équipe et un Espace de travail ?** L'Équipe porte les membres et le budget, tandis que l'Espace de travail isole les documents, le glossaire et les livrables d'un projet.",
        "- **Comment mettre à jour l'aide contextuelle d'un écran ?** Lancez en 1 clic le processus « Génération de la Documentation ORCIA » depuis `☍ Mes Processus`.",
      ].join("\n"),
    },
  },
};
