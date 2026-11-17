/**
 * Localized labels for FinOps Governance Dashboard (`Story 6.2`, `Direction C`).
 *
 * Strict anti-jargon enforcement:
 * - No 'Rubber-Stamping' (use 'Validations expéditives' / 'Quick-pass approvals')
 * - No 'Pattern Drift' (use 'Écarts d'architecture' / 'Architecture deviations')
 * - No '_meta.usage' (use 'Télémétrie déclarée par le service')
 * - No 'CIRCUIT_OPEN' (use 'Connecteur suspendu' / 'Connector suspended')
 * - No 'PAUSED_BUDGET_EXCEEDED' (use 'En pause · Plafond atteint' / 'Paused · Budget exceeded')
 * - No 'PAUSED_MAX_RETRIES' (use 'En pause · Tentatives max atteintes' / 'Paused · Max retries reached')
 * - No raw latency or database names in user-facing French text
 */

import type { HumanMasteryLabels, RemoteServicesTabLabels } from "@orcia/ui";
import {
  HUMAN_MASTERY_EN_LABELS,
  HUMAN_MASTERY_FR_LABELS,
} from "./finops_human_mastery_labels";
import {
  REMOTE_SERVICES_EN_LABELS,
  REMOTE_SERVICES_FR_LABELS,
} from "./finops_remote_labels";

export interface FinopsDictionarySection {
  finops: {
    pageTitle: string;
    pageSubtitle: string;
    infoButtonAriaLabel: string;
    scopeSelector: {
      currentWorkspace: string;
      currentTeam: string;
      entirePlatform: string;
    };
    configureBudgetButton: string;
    emptyStateText: string;
    kpis: {
      consolidatedCostTitle: string;
      verifiedInternalSubtitle: string;
      reportedExternalSubtitle: string;
      tokensTitle: string;
      internalTokensSubtitle: string;
      remoteTokensSubtitle: string;
      externalCallsTitle: string;
      externalUnitsSubtitle: string;
      savingsTitle: string;
      activeBreakersBadge: string;
      pausedRunsBadge: string;
    };
    tabs: {
      processes: string;
      tiers: string;
      externalServices: string;
      cognitiveGovernance: string;
    };
    processesTable: {
      title: string;
      workflowCol: string;
      runsCol: string;
      setupCostCol: string;
      runCostCol: string;
      humanTimeCol: string;
      totalCostCol: string;
      ttmCol: string;
      statusCol: string;
      actionsCol: string;
      pausedBadgeBudget: string;
      pausedBadgeRetries: string;
      activeBadge: string;
      overrideButton: string;
    };
    tiersTable: {
      title: string;
      tierCol: string;
      effortCol: string;
      invocationsCol: string;
      inputTokensCol: string;
      outputTokensCol: string;
      totalTokensCol: string;
      costCol: string;
    };
    modals: {
      budgetTitle: string;
      budgetDescription: string;
      monthlyLimitLabel: string;
      warningThresholdLabel: string;
      hardStopLabel: string;
      scopeLabel: string;
      scopeGlobalLabel: string;
      scopeBuLabel: string;
      scopeTeamLabel: string;
      scopeWorkspaceLabel: string;
      saveButton: string;
      cancelButton: string;
      overrideTitle: string;
      overrideDescription: string;
      overrideAmountLabel: string;
      overrideReasonLabel: string;
      overrideSubmitButton: string;
    };
    remoteServices: RemoteServicesTabLabels;
    humanMastery: HumanMasteryLabels;
  };
}

export const FINOPS_FR_LABELS: FinopsDictionarySection = {
  finops: {
    pageTitle: "FinOps et Gouvernance Économique",
    pageSubtitle:
      "Pilotez l'équation économique de vos processus, suivez la consommation des modèles et connecteurs distants, et maîtrisez la réversibilité humaine.",
    infoButtonAriaLabel: "Comprendre le tableau de bord FinOps et l'équation économique",
    scopeSelector: {
      currentWorkspace: "Cet Espace",
      currentTeam: "Cette Équipe ou Division",
      entirePlatform: "Plateforme entière",
    },
    configureBudgetButton: "+ Configurer un plafond",
    emptyStateText:
      "Aucune consommation n'a encore été enregistrée sur ce périmètre. Les coûts et métriques apparaîtront dès la première exécution d'un processus ou du banc de test.",
    kpis: {
      consolidatedCostTitle: "COÛT CONSOLIDÉ",
      verifiedInternalSubtitle: "Coût interne vérifié",
      reportedExternalSubtitle: "Coût externe déclaré",
      tokensTitle: "TOKENS LLM",
      internalTokensSubtitle: "modèles internes",
      remoteTokensSubtitle: "agents distants",
      externalCallsTitle: "APPELS ET UNITÉS EXTERNES",
      externalUnitsSubtitle: "unités d'outils distants",
      savingsTitle: "ÉCONOMIES ET COUPE-CIRCUITS",
      activeBreakersBadge: "coupe-circuit actif",
      pausedRunsBadge: "exécutions en pause",
    },
    tabs: {
      processes: "Vue d'ensemble et Processus",
      tiers: "Par Modèle et Niveau d'effort",
      externalServices: "Services et Agents externes",
      cognitiveGovernance: "Maîtrise humaine et Qualité",
    },
    processesTable: {
      title: "Processus et Équation Économique",
      workflowCol: "Processus",
      runsCol: "Exécutions",
      setupCostCol: "Setup amorti",
      runCostCol: "Coût d'exécution",
      humanTimeCol: "Temps humain valorisé",
      totalCostCol: "Coût complet",
      ttmCol: "Écart de délai",
      statusCol: "Statut",
      actionsCol: "Actions",
      pausedBadgeBudget: "En pause · Plafond atteint",
      pausedBadgeRetries: "En pause · Tentatives max atteintes",
      activeBadge: "Opérationnel",
      overrideButton: "Accorder une rallonge budgétaire",
    },
    tiersTable: {
      title: "Consommation par Tier Cognitif et Effort",
      tierCol: "Tier cognitif",
      effortCol: "Niveau d'effort",
      invocationsCol: "Invocations",
      inputTokensCol: "Tokens en entrée",
      outputTokensCol: "Tokens en sortie",
      totalTokensCol: "Tokens totaux",
      costCol: "Coût consolidé",
    },
    modals: {
      budgetTitle: "Configurer un plafond budgétaire",
      budgetDescription:
        "Définissez le plafond mensuel et les seuils d'alerte préventive et de blocage pour ce périmètre.",
      monthlyLimitLabel: "Plafond mensuel en dollars",
      warningThresholdLabel: "Seuil d'alerte préventive en pourcentage",
      hardStopLabel: "Plafond d'arrêt bloquant en pourcentage",
      scopeLabel: "Périmètre d'application",
      scopeGlobalLabel: "Plateforme entière",
      scopeBuLabel: "Direction",
      scopeTeamLabel: "Équipe",
      scopeWorkspaceLabel: "Espace",
      saveButton: "Enregistrer le plafond",
      cancelButton: "Annuler",
      overrideTitle: "Accorder une rallonge budgétaire",
      overrideDescription:
        "Augmentez le plafond de l'exécution suspendue pour permettre la reprise immédiate du processus.",
      overrideAmountLabel: "Montant de l'extension en dollars",
      overrideReasonLabel: "Justification de la rallonge",
      overrideSubmitButton: "Valider la reprise",
    },
    remoteServices: REMOTE_SERVICES_FR_LABELS,
    humanMastery: HUMAN_MASTERY_FR_LABELS,
  },
};

export const FINOPS_EN_LABELS: FinopsDictionarySection = {
  finops: {
    pageTitle: "FinOps and Economic Governance",
    pageSubtitle:
      "Monitor your complete process economic equation, track model and remote connector usage, and maintain human reversibility.",
    infoButtonAriaLabel: "Learn about the FinOps dashboard and economic equation",
    scopeSelector: {
      currentWorkspace: "This Workspace",
      currentTeam: "This Team or Business Unit",
      entirePlatform: "Entire Platform",
    },
    configureBudgetButton: "+ Configure Budget Ceiling",
    emptyStateText:
      "No usage has been recorded in this scope yet. Costs and metrics will appear upon the first workflow execution or test bench run.",
    kpis: {
      consolidatedCostTitle: "CONSOLIDATED COST",
      verifiedInternalSubtitle: "Verified internal cost",
      reportedExternalSubtitle: "Reported external cost",
      tokensTitle: "LLM TOKENS",
      internalTokensSubtitle: "internal models",
      remoteTokensSubtitle: "remote agents",
      externalCallsTitle: "EXTERNAL CALLS AND UNITS",
      externalUnitsSubtitle: "remote tool units",
      savingsTitle: "SAVINGS AND CIRCUIT BREAKERS",
      activeBreakersBadge: "active circuit breakers",
      pausedRunsBadge: "paused runs",
    },
    tabs: {
      processes: "Overview and Processes",
      tiers: "By Model and Effort Level",
      externalServices: "External Services and Agents",
      cognitiveGovernance: "Human Mastery and Quality",
    },
    processesTable: {
      title: "Processes and Economic Equation",
      workflowCol: "Process",
      runsCol: "Executions",
      setupCostCol: "Amortized Setup",
      runCostCol: "Run Cost",
      humanTimeCol: "Valorized Human Time",
      totalCostCol: "Complete Cost",
      ttmCol: "TTM Reduction",
      statusCol: "Status",
      actionsCol: "Actions",
      pausedBadgeBudget: "Paused · Budget exceeded",
      pausedBadgeRetries: "Paused · Max retries reached",
      activeBadge: "Operational",
      overrideButton: "Grant budget extension",
    },
    tiersTable: {
      title: "Usage by Cognitive Tier and Effort",
      tierCol: "Cognitive Tier",
      effortCol: "Effort Level",
      invocationsCol: "Invocations",
      inputTokensCol: "Input Tokens",
      outputTokensCol: "Output Tokens",
      totalTokensCol: "Total Tokens",
      costCol: "Consolidated Cost",
    },
    modals: {
      budgetTitle: "Configure Budget Ceiling",
      budgetDescription:
        "Define monthly spending caps, preventive warning, and hard-stop pause thresholds for this scope.",
      monthlyLimitLabel: "Monthly ceiling in USD",
      warningThresholdLabel: "Preventive warning threshold percentage",
      hardStopLabel: "Hard stop threshold percentage",
      scopeLabel: "Target Scope",
      scopeGlobalLabel: "Entire platform",
      scopeBuLabel: "Business unit",
      scopeTeamLabel: "Team",
      scopeWorkspaceLabel: "Workspace",
      saveButton: "Save Budget Ceiling",
      cancelButton: "Cancel",
      overrideTitle: "Grant Budget Extension",
      overrideDescription:
        "Extend the budget ceiling of the paused execution to resume workflow processing immediately.",
      overrideAmountLabel: "Extension amount in USD",
      overrideReasonLabel: "Business justification",
      overrideSubmitButton: "Approve and Resume",
    },
    remoteServices: REMOTE_SERVICES_EN_LABELS,
    humanMastery: HUMAN_MASTERY_EN_LABELS,
  },
};
