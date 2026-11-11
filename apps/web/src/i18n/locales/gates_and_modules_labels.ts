import type {
  ChunkValidationCardLabels,
  CognitiveReviewBriefingLabels,
  UiModuleKey,
  UpstreamChallengeModalLabels,
} from "@orcia/ui";
import type { InboxAndClaimsCopy, ModulePageCopy } from "../types";

export interface GatesAndModulesDictionarySection {
  readonly modulePages: Record<UiModuleKey, ModulePageCopy>;
  readonly upstreamChallengeModal: UpstreamChallengeModalLabels;
  readonly humanGates: {
    readonly briefing: CognitiveReviewBriefingLabels;
    readonly chunkValidation: ChunkValidationCardLabels;
  };
  readonly inboxAndClaims: InboxAndClaimsCopy;
}

export const GATES_AND_MODULES_FR_LABELS: GatesAndModulesDictionarySection = {
  modulePages: {
    cockpit: {
      subtitle: "Votre tableau de bord des décisions et actions prioritaires",
      description:
        "Suivez vos processus en cours, rédigez les cadrages attendus et tranchez les points d'arbitrage.",
      uriBadgeExample: "Cockpit",
    },
    inbox: {
      subtitle: "Votre assistant conversationnel appuyé sur vos sources",
      description:
        "Posez vos questions, explorez vos dossiers thématiques et préparez vos livrables avec citations vérifiées.",
      uriBadgeExample: "Mon Assistant",
    },
    catalog: {
      subtitle: "Répertoire des agents, compétences et services connectés",
      description:
        "Consultez, testez et configurez les agents spécialisés et les outils mis à disposition de vos espaces.",
      uriBadgeExample: "Agents & Compétences",
    },
    ontology: {
      subtitle: "Glossaire métier partagé et base documentaire",
      description:
        "Gérez les termes métier de votre organisation et surveillez la fraîcheur de vos documents de référence.",
      uriBadgeExample: "Connaissances",
    },
    gates: {
      subtitle: "Conception des processus et suivi des étapes de validation",
      description:
        "Créez vos processus métiers, vérifiez les contrôles de qualité et validez les livrables étape par étape.",
      uriBadgeExample: "Processus",
    },
    finops: {
      subtitle: "Suivi des coûts d'utilisation et journal d'activité",
      description:
        "Consultez la consommation par espace et par étape ainsi que l'historique complet des décisions validées.",
      uriBadgeExample: "Coûts & Activité",
    },
    admin: {
      subtitle: "Gestion de vos espaces de travail, sources et règles métiers",
      description:
        "Organisez vos espaces, rattachez vos sources documentaires et gérez le glossaire et les règles de vos équipes.",
      uriBadgeExample: "Mes Espaces",
    },
    bootstrap: {
      subtitle: "Parcours guidés de configuration initiale",
      description:
        "Configurez pas à pas votre organisation, vos premiers espaces de travail et vos connexions aux outils.",
      uriBadgeExample: "Configuration",
    },
  },
  upstreamChallengeModal: {
    modalTitle: "Signaler une Correction sur une Étape Précédente",
    modalSubtitle:
      "Indiquez l'élément à ajuster dans une étape précédente, visualisez les étapes suivantes concernées et relancez uniquement ce qui doit être mis à jour.",
    targetStepLabel: "Étape précédente concernée",
    sectionKeyLabel: "Section ou règle à ajuster",
    reasonLabel: "Motif de la demande de correction (minimum 10 caractères)",
    reasonPlaceholder: "Expliquez l'écart ou la précision à apporter sur l'étape précédente...",
    whatIfTitle: "Aperçu des éléments qui seront mis à jour",
    invalidatedStepsLabel: "Étapes suivantes à recalculer",
    invalidatedSectionsLabel: "Sections de livrables impactées",
    invalidatedAxiomsLabel: "Règles métier concernées",
    preservedStepsLabel: "Étapes antérieures conservées sans retraitement",
    translatedSummaryLabel: "Explication adaptée pour le responsable de l'étape précédente",
    submitChallengeCta: "Envoyer la demande de correction",
    replayStepCta: "Relancer à partir de cette étape",
    closeCta: "Fermer",
    challengeSubmittedFeedback: "Demande de correction transmise au responsable de l'étape ✓",
    replayTriggeredFeedback: "Relance effectuée à partir de l'étape sélectionnée ✓",
  },
  humanGates: {
    briefing: {
      gridTitle: "Synthèse de Relecture avant Validation (4 Points Clés)",
      block1Title: "1. Résumé Exécutif",
      block2Title: "2. Points Clés & Vérifications Croisées",
      block3Title: "3. Décisions Proposées",
      block4Title: "4. Hypothèses Retenues",
      inspectHypothesesButtonLabel: "Confirmer la lecture des hypothèses",
      hypothesesInspectedBadgeLabel: "Hypothèses relues",
      hypothesesPendingBadgeLabel: "Relecture requise (Point 4)",
    },
    chunkValidation: {
      sectionListTitle: "Validation Section par Section",
      keyboardNavHint: "Raccourci clavier : Alt + ↑ / ↓",
      approveSectionLabel: "Valider la section",
      coEditSectionLabel: "Modifier la section",
      challengeSectionLabel: "Demander une correction en amont",
      finalizeGateButtonLabel: "Confirmer la validation finale",
      pendingSectionsNotice:
        "Chaque section obligatoire ainsi que le Point 4 (Hypothèses Retenues) doivent être vérifiés avant la validation finale.",
      guardModalTitle: "Confirmation de Relecture Attentive",
      guardModalDescription:
        "Vous avez validé ce document très rapidement. Merci de confirmer que vous avez bien pris connaissance des hypothèses retenues.",
      guardConfirmCheckboxLabel:
        "Je confirme avoir vérifié les hypothèses retenues et les sections importantes",
      guardConfirmButtonLabel: "Confirmer et enregistrer ma validation",
      guardCancelButtonLabel: "Reprendre la lecture",
    },
  },
  inboxAndClaims: {
    filterAllLabel: "Toutes les demandes",
    filterPersonalLabel: "Qui me sont destinées",
    filterTeamLabel: "Pour mon équipe",
    amberCounterPrefix: "Actions en attente :",
    contributorSectionTitle: "Actions Requises de Votre Part",
    observerSectionTitle: "En Suivi — Consultation Seule",
    observerBannerText:
      "👁️ Mode Consultation Seule — Vous suivez cette exécution sans pouvoir la modifier",
    presencePill: {
      claimActionLabel: "Prendre en charge",
      claimedByMeBadge: "🔒 Pris en charge par vous",
      claimedByPeerPrefix: "🔒 Pris en charge par :",
      releaseActionLabel: "Libérer",
      forceUnclaimActionLabel: "Reprendre la main (après 15 min)",
      readOnlyObserverNotice: "Consultation seule",
      sseLatencyPrefix: "Synchronisation :",
    },
  },
};

export const GATES_AND_MODULES_EN_LABELS: GatesAndModulesDictionarySection = {
  modulePages: {
    cockpit: {
      subtitle: "Your dashboard for priority decisions and actions",
      description:
        "Monitor active processes, write required framing inputs, and resolve pending decisions.",
      uriBadgeExample: "Cockpit",
    },
    inbox: {
      subtitle: "Your conversational assistant grounded in your sources",
      description:
        "Ask questions, organize topic folders, and draft deliverables with verified citations.",
      uriBadgeExample: "My Assistant",
    },
    catalog: {
      subtitle: "Directory of agents, skills, and connected services",
      description:
        "Browse, test, and configure specialized agents and tools available to your workspaces.",
      uriBadgeExample: "Agents & Skills",
    },
    ontology: {
      subtitle: "Shared business glossary and knowledge base",
      description:
        "Manage your organization's business terms and monitor the freshness of reference documents.",
      uriBadgeExample: "Knowledge",
    },
    gates: {
      subtitle: "Process design and review checkpoint tracking",
      description:
        "Build business processes, verify quality checks, and review deliverables step by step.",
      uriBadgeExample: "Processes",
    },
    finops: {
      subtitle: "Usage cost tracking and activity log",
      description:
        "Track usage by workspace and step, and review the complete history of validated decisions.",
      uriBadgeExample: "Costs & Activity",
    },
    admin: {
      subtitle: "Manage your workspaces, sources, and business rules",
      description:
        "Organize workspaces, connect document sources, and manage your team glossary and rules.",
      uriBadgeExample: "My Spaces",
    },
    bootstrap: {
      subtitle: "Guided initial setup workflows",
      description:
        "Configure your organization, initial workspaces, and tool connections step by step.",
      uriBadgeExample: "Setup",
    },
  },
  upstreamChallengeModal: {
    modalTitle: "Request a Correction on a Previous Step",
    modalSubtitle:
      "Point out what needs adjustment in an earlier step, preview which subsequent steps are affected, and restart only what needs updating.",
    targetStepLabel: "Previous step concerned",
    sectionKeyLabel: "Section or rule to adjust",
    reasonLabel: "Reason for the correction request (at least 10 characters)",
    reasonPlaceholder: "Explain the discrepancy or clarification needed on the previous step...",
    whatIfTitle: "Preview of items that will be updated",
    invalidatedStepsLabel: "Subsequent steps to recalculate",
    invalidatedSectionsLabel: "Impacted deliverable sections",
    invalidatedAxiomsLabel: "Related business rules",
    preservedStepsLabel: "Earlier steps preserved without reprocessing",
    translatedSummaryLabel: "Adapted explanation for the previous step owner",
    submitChallengeCta: "Send correction request",
    replayStepCta: "Restart from this step",
    closeCta: "Close",
    challengeSubmittedFeedback: "Correction request sent to the step owner ✓",
    replayTriggeredFeedback: "Restart completed from the selected step ✓",
  },
  humanGates: {
    briefing: {
      gridTitle: "Pre-Approval Review Summary (4 Key Points)",
      block1Title: "1. Executive Summary",
      block2Title: "2. Key Points & Cross-Checks",
      block3Title: "3. Proposed Decisions",
      block4Title: "4. Retained Assumptions",
      inspectHypothesesButtonLabel: "Confirm reading of assumptions",
      hypothesesInspectedBadgeLabel: "Assumptions reviewed",
      hypothesesPendingBadgeLabel: "Review required (Point 4)",
    },
    chunkValidation: {
      sectionListTitle: "Section-by-Section Review",
      keyboardNavHint: "Keyboard shortcut: Alt + ↑ / ↓",
      approveSectionLabel: "Approve section",
      coEditSectionLabel: "Edit section",
      challengeSectionLabel: "Request upstream correction",
      finalizeGateButtonLabel: "Confirm final approval",
      pendingSectionsNotice:
        "Every required section as well as Point 4 (Retained Assumptions) must be checked before final approval.",
      guardModalTitle: "Careful Review Confirmation",
      guardModalDescription:
        "You approved this document very quickly. Please confirm that you have carefully reviewed the retained assumptions.",
      guardConfirmCheckboxLabel:
        "I confirm I have reviewed the retained assumptions and key sections",
      guardConfirmButtonLabel: "Confirm and record my approval",
      guardCancelButtonLabel: "Resume reading",
    },
  },
  inboxAndClaims: {
    filterAllLabel: "All requests",
    filterPersonalLabel: "Assigned to me",
    filterTeamLabel: "For my team",
    amberCounterPrefix: "Pending actions:",
    contributorSectionTitle: "Actions Required from You",
    observerSectionTitle: "Following — Read-Only",
    observerBannerText:
      "👁️ Read-Only Mode — You are following this execution without edit permissions",
    presencePill: {
      claimActionLabel: "Take ownership",
      claimedByMeBadge: "🔒 Handled by you",
      claimedByPeerPrefix: "🔒 Handled by:",
      releaseActionLabel: "Release",
      forceUnclaimActionLabel: "Take over (after 15 min)",
      readOnlyObserverNotice: "Read-only",
      sseLatencyPrefix: "Sync:",
    },
  },
};
