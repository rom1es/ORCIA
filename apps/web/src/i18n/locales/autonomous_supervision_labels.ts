import type {
  AutonomousExecutionBadgeLabels,
  FinopsAutonomousGovernanceLabels,
} from "@orcia/ui";

export interface AutonomousSupervisionCopy {
  readonly panelTitle: string;
  readonly panelSubtitle: string;
  readonly emptyStateText: string;
  readonly loadErrorBanner: string;
  readonly emergencyStopSuccessBanner: string;
  readonly restoreSuccessBanner: string;
  readonly reviewValidatedBanner: string;
  readonly badge: AutonomousExecutionBadgeLabels;
  readonly finops: FinopsAutonomousGovernanceLabels;
}

export const AUTONOMOUS_SUPERVISION_FR_LABELS: AutonomousSupervisionCopy = {
  panelTitle: "Exécutions automatisées sous contrat",
  panelSubtitle:
    "Supervisez les processus exécutés automatiquement par un compte de service, déclenchez un arrêt d'urgence ou rétablissez une version précédente en un clic.",
  emptyStateText:
    "Aucune exécution automatisée sous contrat enregistrée pour cet espace pour le moment.",
  loadErrorBanner: "Impossible de charger les exécutions automatisées de cet espace.",
  emergencyStopSuccessBanner:
    "Arrêt d'urgence activé : l'exécution a été interrompue et le déclencheur associé a été mis en sécurité.",
  restoreSuccessBanner:
    "Version précédente rétablie avec succès et mise à jour immédiate de l'aide et du livrable.",
  reviewValidatedBanner: "Contrôle qualité par échantillonnage validé.",
  badge: {
    badgeLabel: "Automatisé sous contrat",
    triggerPrefix: "Déclencheur :",
    contractPrefix: "Contrat :",
    emergencyStopButton: "Arrêt d'urgence",
    invalidateAndRestoreButton: "Annuler et rétablir la version précédente",
    helpButtonLabel: "Comprendre la supervision des exécutions automatisées",
    statusLabels: {
      COMMITTED_AUTONOMOUS: "Exécution validée automatiquement",
      PAUSED_AUTONOMOUS_ESCALATION: "Suspendue · Décision humaine attendue",
      KILL_SWITCH_STOPPED: "Arrêt d'urgence activé",
      ROLLED_BACK: "Annulée · Version précédente rétablie",
      RUNNING: "En cours d'exécution",
      INITIALIZED: "Initialisée",
    },
  },
  finops: {
    sectionTitle: "Gouvernance des exécutions automatisées",
    sectionSubtitle:
      "Suivez le taux d'escalade vers l'équipe, la qualité vérifiée par échantillonnage et le gain moyen constaté.",
    infoButtonAriaLabel: "Comprendre les indicateurs d'exécution automatisée",
    escalationGauge: {
      title: "Taux d'escalade autonome",
      targetLabel: "cible < 20 %",
      statusHealthy: "Nominal",
      statusAlert: "Escalades fréquentes",
      subtitle: "Part des exécutions automatisées ayant demandé un arbitrage humain",
    },
    invalidationGauge: {
      title: "Taux d'annulation après contrôle",
      thresholdLabel: "seuil < 1 %",
      statusHealthy: "Qualité conforme",
      statusAlert: "Alerte qualité",
      subtitle: "Part des dossiers tirés au sort annulés et rétablis à la version précédente",
    },
    efficiencyGauge: {
      title: "Coût moyen & gain de délai",
      targetLabel: "par exécution automatisée",
      statusHealthy: "Actif",
      costPrefix: "Coût moyen :",
      gainPrefix: "Gain moyen :",
      minutesUnit: "min",
    },
    invalidationAlertBanner:
      "Le taux d'annulation après contrôle qualité atteint ou dépasse 1 % : vérifiez les règles du processus et son contrat d'autonomie.",
    samplesTitle: "Contrôle qualité par échantillonnage",
    samplesEmptyText: "Aucun dossier tiré au sort en attente de contrôle sur cette période.",
    validateSampleButton: "Valider ce dossier",
    invalidateAndRestoreButton: "Annuler et rétablir la version précédente",
    sampleStatusLabels: {
      PENDING_SAMPLE: "À contrôler par un expert",
      VALIDATED: "Validé lors du contrôle",
      INVALIDATED_ROLLED_BACK: "Annulé · Version précédente rétablie",
    },
  },
};

export const AUTONOMOUS_SUPERVISION_EN_LABELS: AutonomousSupervisionCopy = {
  panelTitle: "Contract-governed automated runs",
  panelSubtitle:
    "Monitor processes executed automatically under a service account, trigger an emergency stop, or restore the previous version in one click.",
  emptyStateText: "No contract-governed automated runs recorded for this workspace yet.",
  loadErrorBanner: "Unable to load automated runs for this workspace.",
  emergencyStopSuccessBanner:
    "Emergency stop activated: execution was halted and the linked trigger has been paused.",
  restoreSuccessBanner:
    "Previous version restored successfully with immediate refresh of help and deliverable.",
  reviewValidatedBanner: "Quality sampling check validated.",
  badge: {
    badgeLabel: "Automated under contract",
    triggerPrefix: "Trigger:",
    contractPrefix: "Contract:",
    emergencyStopButton: "Emergency stop",
    invalidateAndRestoreButton: "Cancel and restore previous version",
    helpButtonLabel: "Understand automated run supervision",
    statusLabels: {
      COMMITTED_AUTONOMOUS: "Automatically completed",
      PAUSED_AUTONOMOUS_ESCALATION: "Paused · Human decision required",
      KILL_SWITCH_STOPPED: "Emergency stop activated",
      ROLLED_BACK: "Cancelled · Previous version restored",
      RUNNING: "Running",
      INITIALIZED: "Initialized",
    },
  },
  finops: {
    sectionTitle: "Automated execution governance",
    sectionSubtitle:
      "Track team escalation rate, post-execution quality sampling, and average cost and time savings.",
    infoButtonAriaLabel: "Understand automated execution indicators",
    escalationGauge: {
      title: "Autonomous escalation rate",
      targetLabel: "target < 20%",
      statusHealthy: "Nominal",
      statusAlert: "Frequent escalations",
      subtitle: "Share of automated runs that paused for human arbitration",
    },
    invalidationGauge: {
      title: "Post-review cancellation rate",
      thresholdLabel: "threshold < 1%",
      statusHealthy: "Quality compliant",
      statusAlert: "Quality alert",
      subtitle: "Share of sampled runs cancelled and restored to the previous version",
    },
    efficiencyGauge: {
      title: "Average cost & time saved",
      targetLabel: "per automated run",
      statusHealthy: "Active",
      costPrefix: "Avg cost:",
      gainPrefix: "Avg time saved:",
      minutesUnit: "min",
    },
    invalidationAlertBanner:
      "The post-review cancellation rate reached or exceeded 1%: review process rules and its autonomy contract.",
    samplesTitle: "Quality sampling review",
    samplesEmptyText: "No sampled executions awaiting quality review in this window.",
    validateSampleButton: "Validate run",
    invalidateAndRestoreButton: "Cancel and restore previous version",
    sampleStatusLabels: {
      PENDING_SAMPLE: "Awaiting expert check",
      VALIDATED: "Validated in review",
      INVALIDATED_ROLLED_BACK: "Cancelled · Previous version restored",
    },
  },
};
