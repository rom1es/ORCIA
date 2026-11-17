import type { TranslationDictionary } from "../types";

export const GATES_AND_INBOX_FR_LABELS: Pick<
  TranslationDictionary,
  "upstreamChallengeModal" | "humanGates" | "inboxAndClaims"
> = {
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

export const GATES_AND_INBOX_EN_LABELS: Pick<
  TranslationDictionary,
  "upstreamChallengeModal" | "humanGates" | "inboxAndClaims"
> = {
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
