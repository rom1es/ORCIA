import type { FinopsDictionarySection } from "./finops_labels";
import {
  HUMAN_MASTERY_FR_LABELS,
} from "./finops_human_mastery_labels";
import {
  REMOTE_SERVICES_FR_LABELS,
} from "./finops_remote_labels";

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
    tabsAriaLabel: "Onglets de gouvernance FinOps",
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
      emptyProcessesText: "Aucun processus actif sur ce périmètre.",
    },
    tiersTable: {
      title: "Consommation par Niveau de Modèle et Effort",
      tierCol: "Niveau de modèle",
      effortCol: "Niveau d'effort",
      invocationsCol: "Invocations",
      inputTokensCol: "Tokens en entrée",
      outputTokensCol: "Tokens en sortie",
      totalTokensCol: "Tokens totaux",
      costCol: "Coût consolidé",
      emptyTiersText: "Aucune donnée de modèle ou niveau d'effort enregistrée.",
      tierLabels: {
        simple: "Rapide",
        standard: "Standard",
        reasoning: "Raisonnement approfondi",
        embedding: "Indexation vectorielle",
      },
      effortLabels: {
        low: "Léger",
        medium: "Modéré",
        high: "Approfondi",
        max: "Maximum",
      },
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
