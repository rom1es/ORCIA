import type { WorkflowTriggersModalLabels } from "@orcia/ui";

export interface WorkflowTriggersStudioCopy {
  readonly openModalButton: string;
  readonly activeCountSuffix: string;
  readonly createdSuccessBanner: string;
  readonly updatedSuccessBanner: string;
  readonly deletedSuccessBanner: string;
  readonly firedSuccessBanner: string;
  readonly resetSuccessBanner: string;
  readonly loadErrorBanner: string;
  readonly modal: WorkflowTriggersModalLabels;
}

export const WORKFLOW_TRIGGERS_FR_LABELS: WorkflowTriggersStudioCopy = {
  openModalButton: "Déclencheurs",
  activeCountSuffix: "actif(s)",
  createdSuccessBanner: "Déclencheur enregistré et activé pour ce processus.",
  updatedSuccessBanner: "Paramètres du déclencheur mis à jour.",
  deletedSuccessBanner: "Déclencheur supprimé.",
  firedSuccessBanner: "Exécution autonome déclenchée avec succès.",
  resetSuccessBanner: "Déclencheur réactivé et protection réinitialisée.",
  loadErrorBanner: "Impossible de charger les déclencheurs de ce processus.",
  modal: {
    title: "Déclencheurs",
    description:
      "Configurez les déclenchements automatiques, planifiés ou par alerte dans le cadre du contrat d'autonomie.",
    helpButtonLabel: "Comprendre les déclencheurs automatiques",
    missingContractNotice:
      "Signez d'abord un contrat d'autonomie actif pour activer un déclencheur automatique sur ce processus.",
    emptyListHint: "Aucun déclencheur configuré pour le moment sur ce processus.",
    typeLabel: "Mode de déclenchement",
    triggerKeyLabel: "Identifiant unique du déclencheur (optionnel)",
    triggerKeyPlaceholder: "Ex : alerte-paiement-prod (généré automatiquement si vide)",
    typeOptions: {
      MANUAL_AUTONOMOUS: "Déclenchement manuel",
      WEBHOOK: "Événement externe (Webhook)",
      CRON: "Planification périodique",
      LOG_SINK_ALERT: "Alerte de journaux applicatifs",
      OUTBOX_EVENT: "Publication du processus",
    },
    statusLabels: {
      ACTIVE: "Actif",
      PAUSED: "En pause",
      CIRCUIT_OPEN: "Protection activée",
    },
    cronLabel: "Fréquence planifiée (5 champs)",
    cronPlaceholder: "0 * * * *",
    logServiceLabel: "Service applicatif surveillé",
    logServicePlaceholder: "api",
    cooldownLabel: "Délai anti-doublon (secondes)",
    maxRunsPerHourLabel: "Limite d'exécutions / heure",
    maxDailyCostLabel: "Plafond journalier (€)",
    autoHelpCheckboxLabel:
      "Mettre à jour automatiquement la fiche d'aide à chaque publication",
    webhookSecretFieldLabel: "Clé secrète de signature", // pragma: allowlist secret
    secretConfiguredBadge: "Clé enregistrée", // pragma: allowlist secret
    secretUnconfiguredBadge: "Aucune clé", // pragma: allowlist secret
    secretFingerprintPrefix: "Empreinte :", // pragma: allowlist secret
    secretReplaceCta: "Définir / remplacer", // pragma: allowlist secret
    secretCancelCta: "Annuler", // pragma: allowlist secret
    secretClearCta: "Effacer", // pragma: allowlist secret
    secretSaveCta: "Appliquer", // pragma: allowlist secret
    secretInputPlaceholder: "Saisir la nouvelle clé secrète", // pragma: allowlist secret
    createButton: "Ajouter le déclencheur",
    creatingButton: "Enregistrement...",
    fireNowButton: "Déclencher maintenant",
    resetCircuitButton: "Réactiver",
    pauseButton: "Mettre en pause",
    activateButton: "Activer",
    deleteButton: "Supprimer",
    closeButton: "Fermer",
    failuresPrefix: "Échecs :",
  },
};

export const WORKFLOW_TRIGGERS_EN_LABELS: WorkflowTriggersStudioCopy = {
  openModalButton: "Triggers",
  activeCountSuffix: "active",
  createdSuccessBanner: "Trigger saved and enabled for this process.",
  updatedSuccessBanner: "Trigger settings updated.",
  deletedSuccessBanner: "Trigger deleted.",
  firedSuccessBanner: "Autonomous run triggered successfully.",
  resetSuccessBanner: "Trigger re-enabled and protection counter reset.",
  loadErrorBanner: "Unable to load triggers for this process.",
  modal: {
    title: "Triggers",
    description:
      "Configure manual, scheduled, external event, or log-alert triggers governed by the autonomy contract.",
    helpButtonLabel: "Understand automated triggers",
    missingContractNotice:
      "Sign an active autonomy contract first before enabling automated triggers on this process.",
    emptyListHint: "No triggers configured on this process yet.",
    typeLabel: "Trigger mode",
    triggerKeyLabel: "Unique trigger identifier (optional)",
    triggerKeyPlaceholder: "e.g., prod-payment-alert (auto-generated if empty)",
    typeOptions: {
      MANUAL_AUTONOMOUS: "Manual launch",
      WEBHOOK: "External event (Webhook)",
      CRON: "Periodic schedule",
      LOG_SINK_ALERT: "Application log alert",
      OUTBOX_EVENT: "Process publication",
    },
    statusLabels: {
      ACTIVE: "Active",
      PAUSED: "Paused",
      CIRCUIT_OPEN: "Protection paused",
    },
    cronLabel: "Schedule expression (5 fields)",
    cronPlaceholder: "0 * * * *",
    logServiceLabel: "Monitored application service",
    logServicePlaceholder: "api",
    cooldownLabel: "Deduplication window (seconds)",
    maxRunsPerHourLabel: "Max runs / hour",
    maxDailyCostLabel: "Daily budget cap (€)",
    autoHelpCheckboxLabel: "Automatically update the help article on each publication",
    webhookSecretFieldLabel: "Signing secret key", // pragma: allowlist secret
    secretConfiguredBadge: "Key configured", // pragma: allowlist secret
    secretUnconfiguredBadge: "No key", // pragma: allowlist secret
    secretFingerprintPrefix: "Fingerprint:", // pragma: allowlist secret
    secretReplaceCta: "Set / replace", // pragma: allowlist secret
    secretCancelCta: "Cancel", // pragma: allowlist secret
    secretClearCta: "Clear", // pragma: allowlist secret
    secretSaveCta: "Apply", // pragma: allowlist secret
    secretInputPlaceholder: "Enter new secret key", // pragma: allowlist secret
    createButton: "Add trigger",
    creatingButton: "Saving...",
    fireNowButton: "Trigger now",
    resetCircuitButton: "Re-enable",
    pauseButton: "Pause",
    activateButton: "Enable",
    deleteButton: "Delete",
    closeButton: "Close",
    failuresPrefix: "Failures:",
  },
};
