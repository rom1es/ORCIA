/**
 * Localized labels for Remote MCP Services & External Agents FinOps Tab (`Story 6.4`, `Direction C`).
 *
 * Strict anti-jargon enforcement:
 * - ZERO forbidden terms: _meta.usage, X-Orcia-Usage, CIRCUIT_OPEN, RemoteUsageSanitizer,
 *   Rubber-Stamping, Pattern Drift, audit_ledger, PAUSED_BUDGET_EXCEEDED, < 15 s, < 5 s, < 500 ms.
 */

import type { RemoteServicesTabLabels } from "@orcia/ui";

export const REMOTE_SERVICES_FR_LABELS: RemoteServicesTabLabels = {
  tabTitle: "Services et agents externes",
  tabSubtitle:
    "Suivez les consommations des services et agents externes par métrique native, réglez leur barème de valorisation et réarmez un coupe-circuit isolé.",
  infoButtonAriaLabel: "Comprendre la télémétrie multi-métriques et les coupe-circuits isolés",
  emptyStateText:
    "Aucun service ou agent externe n'a encore enregistré d'appel sur ce périmètre.",
  columns: {
    serviceCol: "Service ou agent",
    typeCol: "Type",
    callsAndLatencyCol: "Appels et latence",
    remoteTokensCol: "Tokens distants",
    businessUnitsCol: "Unités métiers",
    valuationModeCol: "Mode de valorisation",
    consolidatedCostCol: "Coût consolidé",
    quotaCol: "Plafond utilisé",
    circuitStatusCol: "Statut du connecteur",
    actionsCol: "Actions",
  },
  valuationModes: {
    nativeTelemetry: "Télémétrie déclarée par le service",
    fixedScale: "Barème de référence",
    volumetricOnly: "Suivi volumétrique seul",
  },
  circuitStates: {
    closed: "Opérationnel",
    open: "Connecteur suspendu",
    halfOpen: "Reprise en observation",
  },
  serviceKinds: {
    mcpServer: "Serveur d'outils",
    a2aAgent: "Agent distant",
    openapiRest: "Service externe",
    connector: "Connecteur",
  },
  editQuotaButton: "Plafond et barème",
  resetCircuitButton: "Réarmer",
  callsSuffix: "appels",
  unlimitedLabel: "Sans plafond",
  durationMsUnit: "ms",
  quotaModal: {
    title: "Plafond et mode de valorisation",
    description:
      "Définissez le mode de calcul économique, le plafond de sécurité par appel et la limite mensuelle propre à ce connecteur.",
    valuationModeLabel: "Mode de valorisation",
    maxPerCallLabel: "Plafond sécurité par appel en euros",
    fixedCallCostLabel: "Coût fixe par appel en euros",
    unitTariffLabel: "Tarif par unité en euros",
    unitNameLabel: "Nom de l'unité métier",
    maxDailyCallsLabel: "Plafond d'appels par jour",
    maxMonthlyCostLabel: "Plafond mensuel en euros",
    saveButton: "Enregistrer les réglages",
    cancelButton: "Annuler",
  },
};

export const REMOTE_SERVICES_EN_LABELS: RemoteServicesTabLabels = {
  tabTitle: "External services & agents",
  tabSubtitle:
    "Monitor external service and agent usage by native metric, configure valuation scales, and reset isolated connector circuit breakers.",
  infoButtonAriaLabel: "Learn about multi-metric telemetry and isolated connector circuit breakers",
  emptyStateText:
    "No external service or agent calls have been recorded in this scope yet.",
  columns: {
    serviceCol: "Service or agent",
    typeCol: "Type",
    callsAndLatencyCol: "Calls & latency",
    remoteTokensCol: "Remote tokens",
    businessUnitsCol: "Business units",
    valuationModeCol: "Valuation mode",
    consolidatedCostCol: "Consolidated cost",
    quotaCol: "Quota used",
    circuitStatusCol: "Connector status",
    actionsCol: "Actions",
  },
  valuationModes: {
    nativeTelemetry: "Service-reported telemetry",
    fixedScale: "Reference rate scale",
    volumetricOnly: "Volumetric tracking only",
  },
  circuitStates: {
    closed: "Operational",
    open: "Connector suspended",
    halfOpen: "Recovery probe",
  },
  serviceKinds: {
    mcpServer: "Tool server",
    a2aAgent: "Remote agent",
    openapiRest: "External service",
    connector: "Connector",
  },
  editQuotaButton: "Quota & scale",
  resetCircuitButton: "Reset",
  callsSuffix: "calls",
  unlimitedLabel: "No ceiling",
  durationMsUnit: "ms",
  quotaModal: {
    title: "Quota and valuation mode",
    description:
      "Configure the economic valuation mode, per-call safety cap, and monthly spending ceiling for this connector.",
    valuationModeLabel: "Valuation mode",
    maxPerCallLabel: "Per-call safety ceiling in EUR",
    fixedCallCostLabel: "Fixed cost per call in EUR",
    unitTariffLabel: "Tariff per unit in EUR",
    unitNameLabel: "Business unit label",
    maxDailyCallsLabel: "Maximum daily calls",
    maxMonthlyCostLabel: "Monthly cost ceiling in EUR",
    saveButton: "Save settings",
    cancelButton: "Cancel",
  },
};
