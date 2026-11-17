import {
  FinopsGovernanceDashboardView,
  type FinopsDashboardLabels,
  type FinopsProcessRowData,
  type FinopsTierRowData,
} from "@orcia/ui";
import { act, cleanup, fireEvent, render, screen } from "@testing-library/react";
import React from "react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { ShellContainer } from "../components/ShellContainer";
import { FinopsFeaturePanel } from "../features/finops";
import { I18nProvider } from "../i18n";
import { FINOPS_FR_LABELS } from "../i18n/locales/finops_labels";

const MOCK_LABELS: FinopsDashboardLabels = FINOPS_FR_LABELS.finops;

const MOCK_PROCESSES: readonly FinopsProcessRowData[] = [
  {
    workflowId: "wf-doc-review",
    workflowTitle: "Revue documentaire automatisée",
    runsCount: 15,
    amortizedSetupCostEur: 12.0,
    runCostEur: 4.5,
    humanTimeCostEur: 0.0,
    totalCostEur: 16.5,
    ttmReductionPct: 35,
    activeBudgetOverride: false,
    pausedRunsCount: 1,
    pausedReason: "BUDGET",
    samplePausedRunId: "run-paused-01",
  },
];

const MOCK_TIERS: readonly FinopsTierRowData[] = [
  {
    inferenceTier: "simple",
    effort: "low",
    invocationsCount: 50,
    inputTokens: 100_000,
    outputTokens: 20_000,
    totalTokens: 120_000,
    costEur: 0.45,
  },
];

describe("Story 6.2 — Tableau de bord FinOps, KPI, Modales et Survie F5", () => {
  afterEach(() => {
    cleanup();
  });

  it("masque les 4 compteurs KPI et affiche l'état vide quand totalRuns == 0 et totalCost == 0", () => {
    render(
      <FinopsGovernanceDashboardView
        scopeType="GLOBAL"
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
        labels={MOCK_LABELS}
      />,
    );

    expect(screen.getByTestId("finops-empty-state")).toBeDefined();
    expect(screen.queryByTestId("finops-kpi-strip")).toBeNull();
  });

  it("affiche les 4 cartes KPI et les processus quand des exécutions sont comptabilisées", () => {
    render(
      <FinopsGovernanceDashboardView
        scopeType="GLOBAL"
        totalRuns={15}
        totalCostEur={16.5}
        verifiedInternalCostEur={15.0}
        reportedExternalCostEur={1.5}
        totalLlmTokens={120_000}
        internalTokens={100_000}
        remoteTokens={20_000}
        totalExternalCalls={10}
        cacheSavingsEur={2.5}
        activeCircuitBreakersCount={0}
        pausedRunsCount={1}
        processes={MOCK_PROCESSES}
        tiers={MOCK_TIERS}
        labels={MOCK_LABELS}
      />,
    );

    expect(screen.queryByTestId("finops-empty-state")).toBeNull();
    expect(screen.getByTestId("finops-kpi-strip")).toBeDefined();
    expect(screen.getByTestId("finops-kpi-consolidated-cost")).toBeDefined();
    expect(screen.getByTestId("finops-kpi-tokens")).toBeDefined();
    expect(screen.getByTestId("finops-kpi-external-calls")).toBeDefined();
    expect(screen.getByTestId("finops-kpi-savings")).toBeDefined();

    // Vérification du tableau de processus
    expect(screen.getByTestId("finops-processes-tab")).toBeDefined();
    expect(screen.getByTestId("finops-process-row-wf-doc-review")).toBeDefined();
    expect(screen.getByText("Revue documentaire automatisée")).toBeDefined();
  });

  it("ouvre la modale de configuration du plafond budgétaire et déclenche onSaveBudget", () => {
    const handleSaveBudget = vi.fn();

    render(
      <FinopsGovernanceDashboardView
        scopeType="GLOBAL"
        totalRuns={10}
        totalCostEur={50.0}
        verifiedInternalCostEur={45.0}
        reportedExternalCostEur={5.0}
        totalLlmTokens={50_000}
        internalTokens={40_000}
        remoteTokens={10_000}
        totalExternalCalls={5}
        processes={MOCK_PROCESSES}
        tiers={MOCK_TIERS}
        labels={MOCK_LABELS}
        onSaveBudget={handleSaveBudget}
      />,
    );

    // Clic sur le bouton de configuration
    const configBtn = screen.getByTestId("finops-configure-budget-btn");
    fireEvent.click(configBtn);

    // La modale doit être ouverte
    expect(screen.getByTestId("finops-budget-modal")).toBeDefined();

    // Remplissage du plafond
    const amountInput = screen.getByTestId("finops-budget-monthly-limit");
    fireEvent.change(amountInput, { target: { value: "300" } });

    // Soumission du formulaire
    fireEvent.submit(screen.getByTestId("finops-budget-form"));

    expect(handleSaveBudget).toHaveBeenCalledWith(
      "GLOBAL",
      null,
      300,
      80,
      100,
    );
  });

  it("ouvre la modale de déblocage budgétaire pour un processus suspendu et déclenche onSubmitOverride", () => {
    const handleSubmitOverride = vi.fn();

    render(
      <FinopsGovernanceDashboardView
        scopeType="GLOBAL"
        totalRuns={5}
        totalCostEur={20.0}
        verifiedInternalCostEur={18.0}
        reportedExternalCostEur={2.0}
        totalLlmTokens={20_000}
        internalTokens={15_000}
        remoteTokens={5_000}
        totalExternalCalls={2}
        processes={MOCK_PROCESSES}
        tiers={MOCK_TIERS}
        labels={MOCK_LABELS}
        onSubmitOverride={handleSubmitOverride}
      />,
    );

    // Clic sur le bouton de rallonge budgétaire
    const overrideBtn = screen.getByTestId("finops-override-btn-wf-doc-review");
    fireEvent.click(overrideBtn);

    // La modale doit être ouverte
    expect(screen.getByTestId("finops-override-modal")).toBeDefined();

    // Saisie du montant et motif
    const amountInput = screen.getByTestId("finops-override-amount-input");
    fireEvent.change(amountInput, { target: { value: "75" } });

    const reasonInput = screen.getByTestId("finops-override-reason-input");
    fireEvent.change(reasonInput, { target: { value: "Urgence comitologie" } });

    // Validation
    fireEvent.submit(screen.getByTestId("finops-override-form"));

    expect(handleSubmitOverride).toHaveBeenCalledWith(
      "run-paused-01",
      75,
      "Urgence comitologie",
    );
  });

  it("survit à un rechargement complet de page F5 (unmount -> render)", async () => {
    let unmountFn!: () => void;
    await act(async () => {
      const res = render(
        <I18nProvider initialLocale="fr">
          <ShellContainer>
            <FinopsFeaturePanel />
          </ShellContainer>
        </I18nProvider>,
      );
      unmountFn = res.unmount;
    });

    expect(screen.getByTestId("finops-feature-panel")).toBeDefined();

    // Simulation du rechargement complet de page (F5)
    await act(async () => {
      unmountFn();
    });

    await act(async () => {
      render(
        <I18nProvider initialLocale="fr">
          <ShellContainer>
            <FinopsFeaturePanel />
          </ShellContainer>
        </I18nProvider>,
      );
    });

    expect(screen.getByTestId("finops-feature-panel")).toBeDefined();
    expect(screen.getByTestId("finops-page-title")).toBeDefined();
  });
});
