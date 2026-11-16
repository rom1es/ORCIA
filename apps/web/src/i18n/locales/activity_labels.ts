import type { ActivityLogExplorerLabels, ActivityLogProvenanceLabels } from "@orcia/ui";

export interface ActivityProvenanceModalLabels {
  provenanceTitlePrefix: string;
  alignmentStatusLabel: string;
  conformingBadge: string;
  divergenceBadge: string;
  eventsCountLabel: string;
  totalTokensLabel: string;
  consolidatedCostLabel: string;
  closeModalAriaLabel: string;
}

export interface ActivityDictionarySection {
  activity: {
    explorer: ActivityLogExplorerLabels;
    provenanceExport: ActivityLogProvenanceLabels;
    provenanceModal: ActivityProvenanceModalLabels;
    ledgerNoticeTitle: string;
    connectedAdminFallback: string;
    entirePlatform: string;
    recordedAction: string;
    divisionPrefix: string;
    teamPrefix: string;
    privateSpacePrefix: string;
    spacePrefix: string;
  };
}

export const ACTIVITY_FR_LABELS: ActivityDictionarySection = {
  activity: {
    explorer: {
      pageTitle: "Journal d'Activité",
      pageSubtitle:
        "Consultez l'historique horodaté des actions réalisées sur la plateforme, filtré par défaut sur votre niveau d'observation actif.",
      infoButtonLabel:
        "Comprendre le journal d'activité, ses filtres et le filtrage sur votre niveau d'observation",
      observationScopeBannerPrefix: "Filtré sur votre niveau d'observation : ",
      resetToObservationScopeCta: "Revenir à mon niveau d'observation",
      scopeFilterLabel: "Périmètre observé",
      allScopesOptionLabel: "Tous les périmètres",
      userFilterLabel: "Utilisateur (Auteur)",
      allUsersOptionLabel: "Tous les utilisateurs",
      userSearchPlaceholder: "Filtrer par nom d'utilisateur...",
      maxLimitFilterLabel: "Nombre maximum d'événements",
      limit50Label: "50 derniers",
      limit100Label: "100 derniers",
      limit200Label: "200 derniers",
      limit500Label: "500 derniers",
      timeWindowFilterLabel: "Fenêtre temporelle",
      windowAllLabel: "Toute la période",
      window1hLabel: "Dernière heure",
      window24hLabel: "Dernières 24 heures",
      window7dLabel: "7 derniers jours",
      window30dLabel: "30 derniers jours",
      customDateFromLabel: "Du :",
      customDateToLabel: "Au :",
      resultsCounterPrefix: "Événements affichés :",
      emptyStateMessage: "Aucun événement enregistré sur ce périmètre.",
      actorPrefix: "Auteur",
      scopePrefix: "Périmètre",
      timestampPrefix: "Horodatage",
    },
    provenanceExport: {
      selectedRunPrefix: "Exécution sélectionnée :",
      inspectProvenanceAction: "Inspecter la provenance",
      exportJsonAction: "Export JSON certifié",
      exportMdAction: "Dossier Markdown",
    },
    provenanceModal: {
      provenanceTitlePrefix: "Dossier de provenance certifié — Exécution",
      alignmentStatusLabel: "Statut alignement :",
      conformingBadge: "✅ Conforme (100 % aligné)",
      divergenceBadge: "⚠️ Divergence détectée",
      eventsCountLabel: "Événements :",
      totalTokensLabel: "Tokens totaux :",
      consolidatedCostLabel: "Coût consolidé :",
      closeModalAriaLabel: "Fermer le dossier de provenance",
    },
    ledgerNoticeTitle: "Information registre d'audit",
    connectedAdminFallback: "Administrateur de la plateforme",
    entirePlatform: "Plateforme entière",
    recordedAction: "Action enregistrée",
    divisionPrefix: "Direction · ",
    teamPrefix: "Équipe · ",
    privateSpacePrefix: "Espace privé · ",
    spacePrefix: "Espace · ",
  },
};

export const ACTIVITY_EN_LABELS: ActivityDictionarySection = {
  activity: {
    explorer: {
      pageTitle: "Activity Log",
      pageSubtitle:
        "Review the timestamped history of actions performed across the platform, filtered by default to your active observation scope.",
      infoButtonLabel:
        "Understand the activity log, its filters, and observation scope filtering",
      observationScopeBannerPrefix: "Filtered to your observation scope: ",
      resetToObservationScopeCta: "Reset to my observation scope",
      scopeFilterLabel: "Observed scope",
      allScopesOptionLabel: "All scopes",
      userFilterLabel: "User (Author)",
      allUsersOptionLabel: "All users",
      userSearchPlaceholder: "Filter by user name...",
      maxLimitFilterLabel: "Maximum recent events",
      limit50Label: "Last 50",
      limit100Label: "Last 100",
      limit200Label: "Last 200",
      limit500Label: "Last 500",
      timeWindowFilterLabel: "Time window",
      windowAllLabel: "All time",
      window1hLabel: "Last hour",
      window24hLabel: "Last 24 hours",
      window7dLabel: "Last 7 days",
      window30dLabel: "Last 30 days",
      customDateFromLabel: "From:",
      customDateToLabel: "To:",
      resultsCounterPrefix: "Displayed events:",
      emptyStateMessage: "No activity event recorded on this scope.",
      actorPrefix: "Author",
      scopePrefix: "Scope",
      timestampPrefix: "Timestamp",
    },
    provenanceExport: {
      selectedRunPrefix: "Selected execution:",
      inspectProvenanceAction: "Inspect provenance",
      exportJsonAction: "Certified JSON export",
      exportMdAction: "Markdown dossier",
    },
    provenanceModal: {
      provenanceTitlePrefix: "Certified provenance dossier — Run",
      alignmentStatusLabel: "Alignment status:",
      conformingBadge: "✅ Conforming (100% aligned)",
      divergenceBadge: "⚠️ Divergence detected",
      eventsCountLabel: "Events:",
      totalTokensLabel: "Total tokens:",
      consolidatedCostLabel: "Consolidated cost:",
      closeModalAriaLabel: "Close provenance dossier",
    },
    ledgerNoticeTitle: "Audit ledger notice",
    connectedAdminFallback: "Platform Administrator",
    entirePlatform: "Entire Platform",
    recordedAction: "Recorded action",
    divisionPrefix: "Division · ",
    teamPrefix: "Team · ",
    privateSpacePrefix: "Private space · ",
    spacePrefix: "Space · ",
  },
};
