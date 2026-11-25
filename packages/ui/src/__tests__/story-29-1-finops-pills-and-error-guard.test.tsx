import { cleanup, render, screen } from "@testing-library/react";
import React from "react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { FinopsGovernanceDashboardView, type FinopsDashboardLabels } from "../index";

const TEST_LABELS: FinopsDashboardLabels = {
  pageTitle: "FinOps et Gouvernance Économique",
  pageSubtitle: "Suivi FinOps",
  infoButtonAriaLabel: "Aide",
  scopeSelector: {
    currentWorkspace: "Cet Espace",
    currentTeam: "Cette Équipe ou Division",
    entirePlatform: "Plateforme entière",
  },
  configureBudgetButton: "+ Configurer un plafond",
  emptyStateText: "Aucune consommation n'a encore été enregistrée sur ce périmètre.",
  kpis: {
    consolidatedCostTitle: "COÛT CONSOLIDÉ",
    verifiedInternalSubtitle: "interne",
    reportedExternalSubtitle: "externe",
    tokensTitle: "TOKENS LLM",
    internalTokensSubtitle: "internes",
    remoteTokensSubtitle: "distants",
    externalCallsTitle: "APPELS EXTERNES",
    externalUnitsSubtitle: "unités",
    savingsTitle: "ÉCONOMIES",
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
    title: "Processus",
    workflowCol: "Processus",
    runsCol: "Exécutions",
    setupCostCol: "Setup",
    runCostCol: "Coût",
    humanTimeCol: "Temps humain",
    totalCostCol: "Total",
    ttmCol: "Écart",
    statusCol: "Statut",
    actionsCol: "Actions",
    pausedBadgeBudget: "En pause",
    pausedBadgeRetries: "En pause",
    activeBadge: "Opérationnel",
    overrideButton: "Rallonge",
    emptyProcessesText: "Aucun processus actif.",
  },
  tiersTable: {
    title: "Modèles",
    tierCol: "Modèle",
    effortCol: "Effort",
    invocationsCol: "Invocations",
    inputTokensCol: "Entrée",
    outputTokensCol: "Sortie",
    totalTokensCol: "Total",
    costCol: "Coût",
    emptyTiersText: "Aucune donnée.",
  },
  modals: {
    budgetTitle: "Plafond",
    budgetDescription: "Définir",
    monthlyLimitLabel: "Plafond",
    warningThresholdLabel: "Alerte",
    hardStopLabel: "Arrêt",
    scopeLabel: "Périmètre",
    scopeGlobalLabel: "Plateforme entière",
    scopeBuLabel: "Direction",
    scopeTeamLabel: "Équipe",
    scopeWorkspaceLabel: "Espace",
    saveButton: "Enregistrer",
    cancelButton: "Annuler",
    overrideTitle: "Rallonge",
    overrideDescription: "Desc",
    overrideAmountLabel: "Montant",
    overrideReasonLabel: "Motif",
    overrideSubmitButton: "Valider",
  },
};

describe("Story 29.1 — FinOps Scope Pills & Error-vs-Empty Guard", () => {
  afterEach(() => {
    cleanup();
  });

  it("maps BU scopeType onto the Team/Division pill so exactly one pill has aria-selected=true and hides unauthorized pills", () => {
    render(
      <FinopsGovernanceDashboardView
        scopeType="BU"
        allowedScopes={["WORKSPACE", "TEAM"]}
        totalRuns={0}
        totalCostEur={0}
        verifiedInternalCostEur={0}
        reportedExternalCostEur={0}
        totalLlmTokens={0}
        internalTokens={0}
        remoteTokens={0}
        totalExternalCalls={0}
        processes={[]}
        tiers={[]}
        labels={TEST_LABELS}
        onScopeChange={vi.fn()}
      />,
    );

    const pills = screen.getByTestId("finops-scope-pills").querySelectorAll('[role="tab"]');
    const selectedPills = Array.from(pills).filter(
      (el) => el.getAttribute("aria-selected") === "true",
    );
    expect(selectedPills).toHaveLength(1);
    expect(screen.getByTestId("finops-scope-team").getAttribute("aria-selected")).toBe("true");
    expect(screen.queryByTestId("finops-scope-global")).toBeNull();
  });

  it("suppresses the empty consumption white card when error !== null", () => {
    render(
      <FinopsGovernanceDashboardView
        scopeType="TEAM"
        error="Accès au périmètre refusé"
        totalRuns={0}
        totalCostEur={0}
        verifiedInternalCostEur={0}
        reportedExternalCostEur={0}
        totalLlmTokens={0}
        internalTokens={0}
        remoteTokens={0}
        totalExternalCalls={0}
        processes={[]}
        tiers={[]}
        labels={TEST_LABELS}
      />,
    );

    expect(screen.queryByTestId("finops-empty-state")).toBeNull();
    expect(screen.queryByText(/Aucune consommation n'a encore été enregistrée/)).toBeNull();
  });
});
